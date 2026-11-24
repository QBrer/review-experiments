"""Read metadata and legal-code coverage only. No matching, perturbation, or test scores."""
from pathlib import Path
import json,os,importlib.util,hashlib
proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj);os.environ['GDAL_PAM_ENABLED']='NO'
import rasterio
from rasterio.windows import Window
import numpy as np
import pandas as pd
from scipy.ndimage import minimum_filter
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'新实验总方案_v4_跨产品对齐_20261022';OUT.mkdir(exist_ok=True)
BASE=Path('E:/数据对齐实验数据2');h=next(BASE.glob('A multi*/MPSDSL'));w=next(BASE.glob('Long-term*/MON_LULC'))
paths={'H2010':h/'2010.tif','H2020':h/'2020.tif','W2010':w/'2010.tif','W2020':w/'2020.tif'}
ds={k:rasterio.open(p,'r') for k,p in paths.items()};ref=ds['H2020'];offs={};meta={}
for k,d in ds.items():
    cf,rf=(~d.transform)*(ref.transform.c,ref.transform.f);assert max(abs(cf-round(cf)),abs(rf-round(rf)))<1e-6
    offs[k]=(round(rf),round(cf));meta[k]={'path':str(paths[k]),'shape':list(d.shape),'transform':list(d.transform),'crs':str(d.crs),'offset_row_col':list(offs[k]),'bytes':paths[k].stat().st_size,'mtime_ns':paths[k].stat().st_mtime_ns}
old=pd.read_csv(ROOT/'实验独立复核_20261021/只读基线副本/selection/selected_regions.csv')[['id','row','col','lon','lat']];old['role']='existing_development'
new=pd.read_csv(ROOT/'实验重设计_策略选择验证_v3/空间划分可行性_候选名单.csv')
sites=pd.concat([old,new],ignore_index=True);rows=[];n=1200;pad=13
for s in sites.to_dict('records'):
    common=np.ones((n,n),bool);safe=np.ones((n,n),bool);ok=True
    for k,d in ds.items():
        dr,dc=offs[k];sr=int(s['row'])+dr-pad;sc=int(s['col'])+dc-pad
        if min(sr,sc)<0 or sr+n+2*pad>d.height or sc+n+2*pad>d.width:ok=False;break
        a=d.read(1,window=Window(sc,sr,n+2*pad,n+2*pad))
        valid=np.isin(a,[1,21,22,23,24,3]) if k.startswith('H') else (a>=1)&(a<=14)
        center=valid[pad:pad+n,pad:pad+n];common&=center
        if k.startswith('W'):
            eroded=minimum_filter(valid.astype(np.uint8),size=27,mode='constant',cval=0)[pad:pad+n,pad:pad+n].astype(bool);safe&=eroded
        else:safe&=center
    rows.append({'id':s['id'],'role':s['role'],'halo_available':ok,'four_input_coverage':float(common.mean()) if ok else None,'safe_domain_coverage':float(safe.mean()) if ok else None,'passes_safe_90_percent':bool(ok and safe.mean()>=.90)})
for d in ds.values():d.close()
df=pd.DataFrame(rows);df.to_csv(OUT/'四输入与安全有效域_预检.csv',index=False,encoding='utf-8-sig')
summary={'date':'2026-10-22','status':'DESIGN_PREFLIGHT_ONLY','raw_matching_or_performance_computed':False,'inputs':meta,'windows':len(df),'all_halo_available':bool(df.halo_available.all()),'all_safe_coverage_pass':bool(df.passes_safe_90_percent.all()),'min_four_input_coverage':float(df.four_input_coverage.min()),'min_safe_domain_coverage':float(df.safe_domain_coverage.min()),'counts_by_role':df.role.value_counts().to_dict(),'source_split_sha256':hashlib.sha256((ROOT/'实验重设计_策略选择验证_v3/空间划分可行性_候选名单.csv').read_bytes()).hexdigest()}
(OUT/'预检汇总.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
