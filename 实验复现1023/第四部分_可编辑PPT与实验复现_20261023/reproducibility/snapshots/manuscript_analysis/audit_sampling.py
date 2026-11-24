"""Reconstruct geometry-only sampling in a new directory; never run original writers."""
from pathlib import Path
import os,importlib.util,json,hashlib
proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj)
import pandas as pd,numpy as np
from pyproj import Geod,Transformer
R=Path(__file__).resolve().parent;B=R.parent;OUT=R/'sampling_audit';OUT.mkdir(exist_ok=True)
old=B/'实验独立复核_20261021/只读基线副本'
allc=pd.read_csv(old/'selection/candidates.csv');c=allc[allc.reason=='eligible'].sort_values(['row','col']).copy();s=pd.read_csv(old/'selection/selected_regions.csv')
params=json.loads((old/'parameters/frozen_parameters.json').read_text(encoding='utf8'))
actual=pd.read_csv(B/'experiment_v4_runtime/split_manifest.csv');new=pd.read_csv(B/'experiment_ablation_v5_runtime/new_sites.csv')
G=Geod(ellps='WGS84');tr=Transformer.from_crs(4326,6933,always_xy=True)
def block(x,y):
 a,b=tr.transform(x,y);return int(a//200000),int(b//200000)
def distance(a,b):return G.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2]
historical=list(zip(s.lon,s.lat))+[(params['B2']['lon'],params['B2']['lat'])]
oldblocks={block(x,y) for x,y in historical}
c['block']=[block(x,y) for x,y in zip(c.lon,c.lat)]
c['min_old_km']=[min(G.inv(x,y,a,b)[2]/1000 for a,b in historical) for x,y in zip(c.lon,c.lat)]
q=c[(c.min_old_km>=100)&~c.block.isin(oldblocks)].copy();possible=[]
for bid,d in q.groupby('block'):
 rows=d.to_dict('records');pairs=[(a,b) for i,a in enumerate(rows) for b in rows[i+1:] if distance(a,b)>=50000]
 if pairs:possible.append((bid,pairs))
rng=np.random.default_rng(20261021);test=[];blocks=[]
for idx in rng.permutation(len(possible)):
 bid,pairs=possible[idx];allowed=[pair for pair in pairs if all(distance(a,b)>=50000 for a in pair for b in test)]
 if not allowed:continue
 test.extend(allowed[int(rng.integers(len(allowed)))]);blocks.append(bid)
 if len(blocks)==20:break
devpool=[a for a in c.to_dict('records') if a['id'] not in set(s.id) and a['block'] not in set(blocks) and min(distance(a,v) for v in test)>=100000]
dev=[];prior=s.to_dict('records')
while len(dev)<36:
 ranked=[]
 for a in devpool:
  if a['id'] in {v['id'] for v in dev}:continue
  v=min(distance(a,b) for b in prior+dev)
  if v>=50000:ranked.append((v,a))
 ranked.sort(key=lambda x:(-x[0],x[1]['row'],x[1]['col']));dev.append(ranked[0][1])
assert {x['id'] for x in test}==set(actual[actual.phase=='test'].id)
assert {x['id'] for x in dev}==set(actual[(actual.phase=='development')&~actual.id.isin(s.id)].id)
relaxed=allc[(allc.coverage>=.95)&(allc.pSL>=.05)&(allc.pSL<=.95)&(allc.pOthers>=.05)].copy()
relaxed['block']=[str(block(x,y)) for x,y in zip(relaxed.lon,relaxed.lat)]
newblocks=relaxed[~relaxed.block.isin(actual.block)].copy()
newblocks['min_old_km']=[min(G.inv(x,y,a.lon,a.lat)[2]/1000 for a in actual.itertuples()) for x,y in zip(newblocks.lon,newblocks.lat)]
ext=newblocks[newblocks.min_old_km>=100].sort_values(['row','col']);assert ext.id.tolist()==new.id.tolist()
def min_between(a,b):return min(distance(x,y)/1000 for x in a.to_dict('records') for y in b.to_dict('records'))
testdf=actual[actual.phase=='test'];devdf=actual[actual.phase=='development']
cohorts=[('High',s[s.group=='High']),('Low',s[s.group=='Low']),('Development extension',actual[(actual.phase=='development')&~actual.id.isin(s.id)]),('Spatial test',testdf),('Low-SL extrapolation',new)]
rows=[]
for label,d in cohorts:
 z=d[['id','row','col','lon','lat']].merge(allc[['id','pSL','pOthers','H_SL','coverage']],on='id',validate='one_to_one');z['cohort']=label;rows.append(z)
combined=pd.concat(rows,ignore_index=True);assert len(combined)==163 and combined.id.nunique()==163
combined.to_csv(OUT/'all_163_windows_roles.csv',index=False,encoding='utf-8-sig')
stats=combined.groupby('cohort').agg(n=('id','size'),SL_min=('pSL','min'),SL_max=('pSL','max'),H_min=('H_SL','min'),H_max=('H_SL','max'))
stats.to_csv(OUT/'cohort_summary.csv',encoding='utf-8-sig')
report=dict(source_pool=5782,mixed_pool=len(c),test_candidates=len(q),test_pair_capable_blocks=len(possible),test_windows=len(test),test_blocks=len(blocks),development_extension_candidates=len(devpool),development_extension_windows=len(dev),development_total=60,relaxed_composition_pool=len(relaxed),unseen_block_candidates=len(newblocks),extrapolation_windows=len(ext),extrapolation_blocks=ext.block.nunique(),actual_extrapolation_SL_range=[float(ext.pSL.min()),float(ext.pSL.max())],min_test_development_km=min_between(testdf,devdf),min_extrapolation_prior100_km=float(ext.min_old_km.min()),test_and_development_exactly_reproduced=True,extrapolation_exactly_reproduced=True,performance_data_used=False)
(OUT/'sampling_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2));print(stats)
