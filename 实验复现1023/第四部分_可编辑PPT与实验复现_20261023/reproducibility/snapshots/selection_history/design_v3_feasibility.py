"""Geometry-only design preflight. Does not read rasters or task performance tables."""
from pathlib import Path
import os,importlib.util,json,hashlib
proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj)
import pandas as pd,numpy as np
from pyproj import Transformer,Geod
ROOT=Path(__file__).resolve().parent.parent
B=ROOT/'实验独立复核_20261021/只读基线副本'
OUT=ROOT/'实验重设计_策略选择验证_v3';OUT.mkdir(exist_ok=True)
c=pd.read_csv(B/'selection/candidates.csv');c=c[c.reason=='eligible'].sort_values(['row','col']).copy()
s=pd.read_csv(B/'selection/selected_regions.csv')
p=json.loads((B/'parameters/frozen_parameters.json').read_text(encoding='utf-8'))
g=Geod(ellps='WGS84');tr=Transformer.from_crs(4326,6933,always_xy=True)
def block(lon,lat):
    x,y=tr.transform(lon,lat);return (int(np.floor(x/200000)),int(np.floor(y/200000)))
old=list(zip(s.lon,s.lat))+[(p['B2']['lon'],p['B2']['lat'])]
oldblocks={block(x,y) for x,y in old}
c['block']=[block(x,y) for x,y in zip(c.lon,c.lat)]
c['min_old_km']=[min(g.inv(x,y,ox,oy)[2]/1000 for ox,oy in old) for x,y in zip(c.lon,c.lat)]
q=c[(c.min_old_km>=100)&~c.block.isin(oldblocks)].copy()
possible=[]
for bid,d in q.groupby('block'):
    records=d.to_dict('records');pairs=[]
    for i,a in enumerate(records):
        for b in records[i+1:]:
            if g.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2]>=50000:pairs.append((a,b))
    if pairs:possible.append((bid,pairs))
rng=np.random.default_rng(20261021);selected=[];blocks=[];skipped=[]
for idx in rng.permutation(len(possible)):
    bid,pairs=possible[idx]
    allowed=[pair for pair in pairs if all(g.inv(x['lon'],x['lat'],y['lon'],y['lat'])[2]>=50000 for x in pair for y in selected)]
    if not allowed:skipped.append(str(bid));continue
    selected.extend(allowed[int(rng.integers(len(allowed)))]);blocks.append(bid)
    if len(blocks)==20:break
reserved=set(blocks);testids={x['id'] for x in selected}
dev=[]
for a in c.to_dict('records'):
    if a['id'] in set(s.id) or a['block'] in reserved:continue
    if min(g.inv(a['lon'],a['lat'],v['lon'],v['lat'])[2] for v in selected)<100000:continue
    dev.append(a)
newdev=[];prior=s.to_dict('records')
while len(newdev)<36:
    ranked=[]
    for a in dev:
        if a['id'] in {z['id'] for z in newdev}:continue
        d=min(g.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2] for b in prior+newdev)
        if d>=50000:ranked.append((d,a))
    if not ranked:break
    ranked.sort(key=lambda x:(-x[0],x[1]['row'],x[1]['col']));newdev.append(ranked[0][1])
rows=[]
for role,items in [('proposed_test',selected),('proposed_new_development',newdev)]:
    for a in items:rows.append({k:a[k] for k in ['id','row','col','lon','lat']}|dict(block=str(a['block']),role=role))
pd.DataFrame(rows).to_csv(OUT/'空间划分可行性_候选名单.csv',index=False,encoding='utf-8-sig')
record=dict(status='DESIGN_GEOMETRY_CHECK_ONLY_NOT_FROZEN',inputs=['selection/candidates.csv','selection/selected_regions.csv','parameters/frozen_parameters.json'],raster_or_new_performance_access=False,eligible_pool=714,far_from_old25_count=int((c.min_old_km>=100).sum()),strict_new_block_candidates=len(q),blocks_with_50km_pair=len(possible),proposed_test_blocks=len(blocks),proposed_test_windows=len(selected),proposed_new_development_windows=len(newdev),existing_development_windows=24,development_candidates_after_test_buffer=len(dev),geometry_skipped_blocks=skipped,seed=20261021,projection='EPSG:6933',tile_side_projected_m=200000,grid_origin_xy=[0,0],test_old_buffer_geodesic_m=100000,test_development_buffer_geodesic_m=100000,minimum_window_center_distance_m=50000,source_candidates_sha256=hashlib.sha256((B/'selection/candidates.csv').read_bytes()).hexdigest())
(OUT/'空间划分可行性.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
