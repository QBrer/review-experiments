from pathlib import Path
import os, json, hashlib, sys, platform, importlib.util
from datetime import datetime, timezone
_proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
if (_proj/'proj.db').exists():
    os.environ['PROJ_DATA']=str(_proj);os.environ['PROJ_LIB']=str(_proj)
import numpy as np
import rasterio
from rasterio.windows import Window
from pyproj import Geod

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
GEOD=Geod(ellps='WGS84')
FINE=np.array([1,21,22,23,24,3],dtype=np.uint8)
LUT=np.full(256,255,np.uint8);LUT[1]=1;LUT[21:25]=2;LUT[3]=3
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.ndarray): return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    if isinstance(x,Path):return str(x)
    return x
def dump(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(x),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
def load(path):return json.loads(Path(path).read_text(encoding='utf8'))
def cfg():return load(ROOT/'parameters/frozen_parameters.json')
def inputs():
    h=next(BASE.glob('A multi*/MPSDSL'));w=next(BASE.glob('Long-term*/MON_LULC'))
    return {**{f'H{y}':h/f'{y}.tif' for y in [2000,2010,2015,2020]},'W2020':w/'2020.tif'}
def open_inputs():return {k:rasterio.open(p) for k,p in inputs().items()}
def offsets(ds):
    ref=ds['H2020'];out={}
    for k,s in ds.items():
        assert s.crs==ref.crs and str(s.crs)=='EPSG:4326'
        assert s.transform.b==0 and s.transform.d==0
        assert np.allclose(s.res,ref.res,rtol=1e-12,atol=0)
        col,row=(~s.transform)*(ref.transform.c,ref.transform.f)
        assert max(abs(col-round(col)),abs(row-round(row)))<1e-6,(k,col,row)
        out[k]=(int(round(row)),int(round(col)))
    return out
def read_window(ds,off,row,col,n):
    arrays={}
    for k,s in ds.items():
        dr,dc=off[k];sr=row+dr;sc=col+dc
        if min(sr,sc)<0 or sr+n>s.height or sc+n>s.width:raise ValueError('window outside '+k)
        a=s.read(1,window=Window(sc,sr,n,n));assert a.shape==(n,n)
        arrays[k]=a
    v=np.ones((n,n),bool)
    for k,a in arrays.items():v &= np.isin(a,FINE) if k.startswith('H') else (a>=1)&(a<=14)
    return arrays,v
def rowareas(tr,n):
    a=[]
    for i in range(n):
        x0,y0=tr*(0,i);x1,y1=tr*(1,i+1)
        ar,_=GEOD.polygon_area_perimeter([x0,x1,x1,x0],[y0,y0,y1,y1]);a.append(abs(ar))
    return np.asarray(a)
def weights(tr,n):return np.broadcast_to(rowareas(tr,n)[:,None],(n,n))
def area(mask,w):return float(np.sum(np.count_nonzero(mask,axis=1)*w[:,0]))
def blocks(a,f):
    h,w=a.shape;assert h%f==0 and w%f==0
    return a.reshape(h//f,f,w//f,f).sum((1,3),dtype=np.float64)
def expand(a,f):return a.repeat(f,axis=0).repeat(f,axis=1)
def unique_mode(mass,codes):
    total=mass.sum(0);top=mass.max(0)
    tied=(np.abs(mass-top[None])<=1e-10*total[None]).sum(0)>1
    a=np.array(codes,np.uint8)[mass.argmax(0)];a[tied|(total<=0)]=255
    return a
def aggregate(a,v,w,f):
    m=np.stack([blocks(w*(v&(a==c)),f) for c in FINE])
    q=np.stack([m[0],m[1:5].sum(0),m[5]])
    t=m.sum(0);p=np.divide(q,t[None],out=np.zeros_like(q),where=t[None]>0)
    assert np.isclose(t.sum(),area(v,w),rtol=1e-12)
    fine=unique_mode(m,FINE);coarse=unique_mode(q,[1,2,3])
    return dict(fine=fine,coarse=coarse,spatial_then_semantic=LUT[fine],p=p,total=t,mass=m)
def ratio(n,d):return float(n/d) if d>0 else np.nan
def change_metrics(pred,reference,known,v,w):
    pred=pred&known&v;ref=reference&v
    tp=area(pred&ref,w);fp=area(pred&~ref,w);fn=area(ref&~pred,w)
    ra=area(ref,w);pa=area(pred,w);domain=area(v,w)
    return dict(tp_km2=tp/1e6,fp_km2=fp/1e6,fn_km2=fn/1e6,reference_km2=ra/1e6,predicted_km2=pa/1e6,
      area_bias_km2=(pa-ra)/1e6,area_error_km2=abs(pa-ra)/1e6,relative_area_error=ratio(abs(pa-ra),ra),
      precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),F1=ratio(2*tp,2*tp+fp+fn),IoU=ratio(tp,tp+fp+fn),
      false_change_rate=ratio(fp,domain-ra),missed_change_rate=ratio(fn,ra),coverage=ratio(area(known&v,w),domain),
      unknown_km2=area(v&~known,w)/1e6,empty_reference=ra==0,empty_prediction=pa==0)
def write_csv(p,rows):
    import pandas as pd
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(p,index=False,encoding='utf-8-sig')

def freeze():
    path=ROOT/'parameters/frozen_parameters.json'
    if path.exists():return
    ds=open_inputs();off=offsets(ds)
    p=dict(version='NEW-1.0',frozen_at=now(),plan_sha256=sha(ROOT/'新实验方案.md'),
      input_files={k:dict(path=str(inputs()[k]),bytes=inputs()[k].stat().st_size,mtime_ns=inputs()[k].stat().st_mtime_ns,shape=list(s.shape),crs=str(s.crs),transform=list(s.transform),nodata=s.nodata,offset_from_H2020=off[k]) for k,s in ds.items()},
      years=[2000,2010,2015,2020],scales=[3,10,30],window_size=1200,edge_policy='exclude incomplete 1200 windows; no padding',
      common_mask='intersection legal original codes in H2000,H2010,H2015,H2020,W2020; same mask in all experiments and composition',
      coverage='valid native pixel count / 1200^2',min_coverage=.95,legal_codes={'Han':FINE.tolist(),'Wang':list(range(1,15))},
      SL_range_inclusive=[.2,.8],Others_min_inclusive=.1,composition_weights='WGS84 valid area',
      B2=dict(row=52983,col=78382,size=1020,lon=(108.85856478183094+109.13344925877150)/2,lat=(38.86920402856759+39.14408850550816)/2,historical_rate=.1634734517721823),
      distance='WGS84 ellipsoidal geodesic between geometric window centers',B2_exclusion_km=100,min_center_distance_km=50,
      sensitivity=dict(metric='conditional SL entropy, log2',q=[.25,.75],quantile_method='linear',High='H_SL>=Q75',Low='H_SL<=Q25',equal_quantiles='STOP',no_outcome_access=True),
      sample=dict(n_per_group=12,seed=20261016,rng='numpy PCG64 default_rng',first_group='High',first_each_group='uniform random among distance-eligible sorted row/col candidates',subsequent='global maximin to all previously selected windows',distance_tie_tolerance_m=1e-6,tie_order='ascending row,col',failure='STOP without relaxation'),
      semantic_mapping={1:1,21:2,22:2,23:2,24:2,3:3},tie_relative_tolerance=1e-10,unresolved=255,
      experiment1=dict(start_years=[2015,2010,2000],end_year=2020,semantic_levels=['fine6','coarse3'],reference='native any-class change at corresponding semantic level',metrics_weight='area'),
      experiment2=dict(year=2020,primary_rate='cell-count',companion_rate='valid-area-weighted',phase_factor=30,phase_offsets=[0,10,20],phase_core='[30:n-30,30:n-30] on both axes; same for all phases',phase_cells='every positive core-overlap jointly decidable block counts once; area weighted by core overlap',baseline_phase=[0,0]),
      experiment3=dict(area_year=2020,start_years=[2015,2010,2000],end_year=2020,purity_threshold=.90,refinement='either epoch max coarse proportion < .90 => native in both',baseline='uniform coarse3 dominant label',area_proposed='SL proportion per block float64',reference='native SL binary; internal product preservation, not ground truth',no_group_access=True,
      primary=dict(start_year=2010,end_year=2020,scale=30,metric='area-weighted binary SL-change F1',comparisons=['High:Proposed-Baseline','Low:Proposed-Baseline'],correction='Holm family size2')),
      metrics=dict(change_weight='WGS84 valid area',NC_weights=['count','valid-area'],zero_denominators='NA, never perfect score',unknown_change='abstention; positive reference counted FN; report coverage',unknown_area='[L,L+unknown]; primary worst-case absolute deviation; signed bias interval',relative_area_denominator='reference SL area',area_primary='absolute km2; relative companion'),
      statistics=dict(unit='sample window; B2 excluded',test='two-sided exact paired sign-flip test of mean difference, enumerate all 2^n',effect='mean and median paired difference plus paired rank-biserial descriptive',bootstrap='paired whole-window percentile CI, 10000 replicates',seed=20261016,min_pairs=5,missing='complete finite pairs with n and missing reported; no replacement; NA remains in planned family as p=1 placeholder',secondary='descriptive estimates and window bootstrap CI only; no secondary p-values',all_zero='p=1 and effect=0'),
      storage=dict(format='np.savez_compressed + JSON metadata per task output',labels='uint8',proportions='float64',adaptive='coarse labels for both years, sorted uint32 flattened block indices, native uint8 fine payloads for both years',common='full uint8 valid mask and per-row float64 areas included and charged separately to every artifact',cost='sum array nbytes + metadata bytes; actual NPZ + JSON bytes; native three-class expression same accounting'),
      software=dict(python=sys.version,executable=sys.executable,numpy=np.__version__,rasterio=rasterio.__version__,gdal=rasterio.__gdal_version__,platform=platform.platform()))
    dump(path,p)
    dump(ROOT/'qc/grid_validation.json',dict(time=now(),passed=True,integer_offsets=off,no_resampling=True))
    for s in ds.values():s.close()
    print('Parameters frozen; grid offsets '+str(off),flush=True)
if __name__=='__main__':freeze()
