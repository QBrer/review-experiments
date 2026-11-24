from pathlib import Path
import sys,os,json,time,hashlib,shutil,traceback
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'experiment_v4_runtime'
sys.dont_write_bytecode=True
sys.path.insert(0,str(OLD));import engine as e
e.ROOT=HERE
os.environ['NUMBA_CACHE_DIR']=str(HERE/'numba_cache');os.environ['MPLCONFIGDIR']=str(HERE/'mplconfig')
from engine import *
import joblib,psutil
from pyproj import Transformer

METHODS=['G','GS','GT','GST'];GRIDS=[(float(g),float(l)) for l in [0,.25,.5,1] for g in [0,.25,.5]]
def cache(sid):
 p=OLD/'cache/full'/(sid+'.npz')
 if not p.exists():p=HERE/'cache/full'/(sid+'.npz')
 with np.load(p) as z:return {k:z[k] for k in z.files}
def joint_solve(z,ok,method,gamma,lam):
 sem=method in ['GS','GST'];temporal=method in ['GT','GST'];scores=[]
 for t in range(2):
  valid=ok[t].copy()
  if not sem:valid[1]=False
  if valid.any():s=z[t,valid].mean(0)-gamma*UNORM/24
  else:s=np.full(len(U),-np.inf);s[ZERO]=0
  scores.append(s)
 joint=scores[0][:,None]+scores[1][None,:]-(lam if temporal else 0)*DIST/12
 winners=np.argwhere(joint>=np.max(joint)-1e-12)
 ij=min(winners,key=lambda q:(int(UNORM[q[0]]+UNORM[q[1]]),*U[q[0]],*U[q[1]]))
 return np.array([U[ij[0]],U[ij[1]]])
def compute_surfaces(ids,model):
 out=[]
 for sid in ids:
  x=cache(sid)
  for ci,c in enumerate(cases(sid)):
   z,ok,_=case_surfaces(x,c,model);out.append((sid,ci,c,z,ok))
 return out
def error_one(u,c):return float(np.linalg.norm(u+np.array(c['d']),axis=1).mean())
def prepare():
 if (HERE/'frozen_parameters.json').exists():raise RuntimeError('Already prepared')
 oldcfg=load(OLD/'frozen_parameters.json');dump(HERE/'frozen_parameters.json',oldcfg)
 allold=pd.read_csv(OLD/'split_manifest.csv');c=pd.read_csv(HERE.parent/'实验独立复核_20261021/只读基线副本/selection/candidates.csv')
 c=c[(c.coverage>=.95)&(c.pSL>=.05)&(c.pSL<=.95)&(c.pOthers>=.05)].copy();tr=Transformer.from_crs(4326,6933,always_xy=True)
 c['block']=[str((int(tr.transform(x,y)[0]//200000),int(tr.transform(x,y)[1]//200000))) for x,y in zip(c.lon,c.lat)];c=c[~c.block.isin(allold.block)].copy()
 c['min_old_km']=[min(G.inv(x,y,a.lon,a.lat)[2]/1000 for a in allold.itertuples()) for x,y in zip(c.lon,c.lat)];c=c[c.min_old_km>=100].sort_values(['row','col']).copy()
 assert len(c)==63 and c.block.nunique()==14
 c['dataset']='low_SL_extrapolation';c.to_csv(HERE/'new_sites.csv',index=False,encoding='utf-8-sig')
 oldtest=allold[allold.phase=='test'].copy();oldtest['dataset']='old40_exploratory'
 pd.concat([oldtest,c],ignore_index=True).to_csv(HERE/'evaluation_sites.csv',index=False,encoding='utf-8-sig')
 # Metadata/coverage-only access before outcomes; no selection based on scores.
 ds=open_data();checks=[]
 for s in c.to_dict('records'):
  data,valid,safe,rw,tr0=read_site(s,ds);checks.append({'site':s['id'],'safe_coverage':float(safe.mean()),'passed':bool(safe.mean()>=.9)})
 for d in ds.values():d.close()
 pd.DataFrame(checks).to_csv(HERE/'preflight.csv',index=False,encoding='utf-8-sig');assert all(x['passed'] for x in checks)
 b=joblib.load(OLD/'models/final/bundle.joblib');dump(HERE/'class_model.json',b['class'])
 protected={}
 for base in [OLD,HERE.parent/'新实验总方案_v4_跨产品对齐_20261022']:
  for p in base.rglob('*'):
   if p.is_file():
    st=p.stat();protected[str(p)]={'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
    if p.suffix in ['.py','.md','.json','.csv','.joblib']:protected[str(p)]['sha256']=sha(p)
 dump(HERE/'protected_before.json',protected)
 frozen={'version':'ABLATION-V5-20261022','status':'FROZEN_BEFORE_NEW_MATCHING','primary_gamma':.5,'primary_lambda':.25,'methods':METHODS,'grid':GRIDS,'data':[{'set':'old40_exploratory','windows':40,'blocks':20},{'set':'low_SL_extrapolation','windows':63,'blocks':14}],'main_contrasts':['GT-GST','GS-GST'],'main_CI_level':.975,'bootstrap':10000,'protocol_sha256':sha(HERE/'PROTOCOL.md'),'split_sha256':sha(HERE/'evaluation_sites.csv'),'code_sha256':sha(__file__),'prior_engine_sha256':sha(OLD/'engine.py'),'matrix_sha256':sha(HERE/'class_model.json'),'no_new_test_outcomes_used':True}
 dump(HERE/'ablation_frozen.json',frozen)
 print('PREPARED 63 new windows,14 blocks; all safe coverage passed',flush=True)
def check():
 z=np.zeros((2,2,len(U)));ok=np.ones((2,2),bool)
 for t,target in enumerate([[2,-3],[-1,4]]):
  z[t,0]=-np.sum((U-target)**2,axis=1);z[t,1]=-.5*np.sum((U-target)**2,axis=1)
 for g,l in GRIDS:
  assert np.array_equal(joint_solve(z,ok,'G',g,0),joint_solve(z,ok,'GT',g,0))
  assert np.array_equal(joint_solve(z,ok,'GS',g,0),joint_solve(z,ok,'GST',g,0))
  q=z.copy();q[:,1]*=-300
  assert np.array_equal(joint_solve(z,ok,'G',g,l),joint_solve(q,ok,'G',g,l))
  assert np.array_equal(joint_solve(z,ok,'GT',g,l),joint_solve(q,ok,'GT',g,l))
  assert np.array_equal(joint_solve(z,ok,'GST',g,l),solve(z,ok,{'g1':0,'g2':0,'g3':g,'lam':l})[3])
 assert not joint_solve(z,np.zeros_like(ok),'GST',.5,.25).any()
 dump(HERE/'qc/operator_checks.json',{'passed':True,'checks':['lambda_zero_identity','no_semantic_uses_only_geometry','GST_equals_v4','no_information_zero']})
 print('Operator checks passed')
def calibrate():
 model=load(HERE/'class_model.json');model['p']=np.array(model['p']);model['present']=np.array(model['present'])
 sites=pd.read_csv(OLD/'split_manifest.csv');ids=sites[sites.phase=='development'].id.tolist();surfaces=compute_surfaces(ids,model);rows=[];chosen={}
 for method in METHODS:
  opts=GRIDS if method in ['GT','GST'] else [(g,0.) for g in [0.,.25,.5]]
  vals=[]
  for gamma,lam in opts:
   total=sum(error_one(joint_solve(z,ok,method,gamma,lam),c)*FAMILY_WEIGHT[ci]/len(ids) for sid,ci,c,z,ok in surfaces)
   r={'method':method,'gamma':gamma,'lambda':lam,'training_E':total};rows.append(r);vals.append(r)
  minimum=min(r['training_E'] for r in vals);best=next(r for r in vals if r['training_E']<=minimum+1e-12);chosen[method]=best
  print('CALIBRATED',method,best,flush=True)
 pd.DataFrame(rows).to_csv(HERE/'development_calibration.csv',index=False,encoding='utf-8-sig');dump(HERE/'calibrated_parameters.json',chosen)
 dump(HERE/'parameters_locked.json',{'time':time.strftime('%Y-%m-%d %H:%M:%S'),'sha256':sha(HERE/'calibrated_parameters.json'),'training_windows':60,'test_metrics_used':False})
def extract_new():
 sites=pd.read_csv(HERE/'new_sites.csv');ds=open_data()
 try:
  for i,s in enumerate(sites.to_dict('records')):
   p=HERE/'cache/full'/(s['id']+'.npz')
   if p.exists():continue
   r=extract(s,ds,'full');print('EXTRACT',i+1,'/',len(sites),s['id'],round(r['seconds'],2),flush=True)
 finally:
  for d in ds.values():d.close()
def predictions():
 assert sha(HERE/'calibrated_parameters.json')==load(HERE/'parameters_locked.json')['sha256']
 model=load(HERE/'class_model.json');model['p']=np.array(model['p']);model['present']=np.array(model['present']);cal=load(HERE/'calibrated_parameters.json');sites=pd.read_csv(HERE/'evaluation_sites.csv');rows=[];truth=[]
 for i,s in enumerate(sites.to_dict('records')):
  x=cache(s['id'])
  for ci,c in enumerate(cases(s['id'])):
   truth.append({'site':s['id'],'dataset':s['dataset'],'block':s['block'],'case_index':ci,**c});z,ok,_=case_surfaces(x,c,model)
   for method in METHODS:
    for gamma,lam in (GRIDS if method in ['GT','GST'] else [(g,0.) for g in [0.,.25,.5]]):
     u=joint_solve(z,ok,method,gamma,lam)
     main=(gamma==.5 and lam==(.25 if method in ['GT','GST'] else 0))
     tuned=gamma==cal[method]['gamma'] and lam==cal[method]['lambda']
     rows.append({'dataset':s['dataset'],'block':s['block'],'site':s['id'],'case_id':c['case_id'],'method':method,'gamma':gamma,'lambda':lam,'is_primary':main,'is_calibrated':tuned,'u2010_r':int(u[0,0]),'u2010_c':int(u[0,1]),'u2020_r':int(u[1,0]),'u2020_c':int(u[1,1])})
  print('PREDICT',i+1,s['id'],flush=True)
 pd.DataFrame(rows).to_csv(HERE/'locked_predictions.csv',index=False,encoding='utf-8-sig');dump(HERE/'evaluator/private_truth.json',truth)
 dump(HERE/'predictions_locked.json',{'time':time.strftime('%Y-%m-%d %H:%M:%S'),'rows':len(rows),'sha256':sha(HERE/'locked_predictions.csv'),'test_metrics_computed':False})
def task_metric(pr,ref,mask,rw):
 tp=float(np.dot(np.count_nonzero(mask&pr&ref,axis=1),rw));fp=float(np.dot(np.count_nonzero(mask&pr&~ref,axis=1),rw));fn=float(np.dot(np.count_nonzero(mask&~pr&ref,axis=1),rw));den=2*tp+fp+fn
 return {'F1':2*tp/den if den else np.nan,'IoU':tp/(tp+fp+fn) if tp+fp+fn else np.nan,'tp_km2':tp/1e6,'fp_km2':fp/1e6,'fn_km2':fn/1e6,'reference_km2':(tp+fn)/1e6,'coverage':1.}
def evaluate():
 assert sha(HERE/'locked_predictions.csv')==load(HERE/'predictions_locked.json')['sha256']
 preds=pd.read_csv(HERE/'locked_predictions.csv');truth={x['case_id']:x for x in load(HERE/'evaluator/private_truth.json')};sites=pd.read_csv(HERE/'evaluation_sites.csv');align=[];tasks=[];files=[];ds=open_data()
 for i,s in enumerate(sites.to_dict('records')):
  data,valid,safe,rw,tr=read_site(s,ds);_,_,ev,_=masks(s['id'],safe)
  center=lambda a,dr=0,dc=0:a[PAD+dr:PAD+dr+N,PAD+dc:PAD+dc+N]
  a=center(data[2])==13;b=center(data[3])==13;refs={'change_union':a!=b,'expansion':~a&b,'contraction':a&~b}
  saved={};arrays={};taskcache={};rows=preds[preds.site==s['id']]
  for r in rows.to_dict('records'):
   c=truth[r['case_id']];d=np.array(c['d']);u=np.array([[r['u2010_r'],r['u2010_c']],[r['u2020_r'],r['u2020_c']]]);res=d+u;err=np.linalg.norm(res,axis=1)
   base={**r,'family':c['family'],'m':c['m'],'case_index':c['case_index']};align.append({**base,'E':float(err.mean()),'within1':bool((err<=1).all()),'exact':bool((err==0).all()),'nominal_modified':bool((u!=0).any())})
   if not (r['is_primary'] or r['is_calibrated']):continue
   mapped=[]
   for t in range(2):
    dr,dc=map(int,res[t]);key=(t,dr,dc)
    if key not in saved:
     arr=center(data[t+2],dr,dc).copy();arr[~safe]=255;p=HERE/'outputs'/s['id']/f'W{[2010,2020][t]}_r{dr}_c{dc}.tif';write_tif(p,arr,tr);saved[key]=str(p.relative_to(HERE));arrays[key]=arr
    mapped.append(arrays[key]);files.append({**r,'year':[2010,2020][t],'file':saved[key]})
   pair=tuple(res.ravel())
   if pair not in taskcache:
    x=mapped[0]==13;y=mapped[1]==13;pr={'change_union':x!=y,'expansion':~x&y,'contraction':x&~y};taskcache[pair]={k:task_metric(pr[k],refs[k],ev,rw) for k in pr}
   for event,metrics0 in taskcache[pair].items():tasks.append({**base,'event':event,**metrics0})
  write_tif(HERE/'outputs'/s['id']/'evaluation_mask.tif',ev.astype(np.uint8),tr,0)
  print('EVALUATE',i+1,'/',len(sites),s['id'],'rasters',len(saved),flush=True)
 for d in ds.values():d.close()
 for name,rows in [('all_alignment_metrics',align),('task_metrics',tasks),('raster_manifest',files)]:pd.DataFrame(rows).to_csv(HERE/(name+'.csv'),index=False,encoding='utf-8-sig')
 dump(HERE/'evaluation_complete.json',{'alignment_rows':len(align),'task_rows':len(tasks),'windows':len(sites)})
def main(stage):
 if stage=='prepare':prepare();check()
 elif stage=='calibrate':calibrate()
 elif stage=='extract':extract_new()
 elif stage=='predict':predictions()
 elif stage=='evaluate':evaluate()
 else:raise ValueError(stage)
if __name__=='__main__':
 stage=sys.argv[1];t=time.time();rec={'stage':stage,'start':time.strftime('%Y-%m-%d %H:%M:%S'),'status':'running'};dump(HERE/'status.json',rec)
 try:
  main(stage);rec.update(status='complete',seconds=time.time()-t,memory=psutil.Process().memory_info()._asdict());dump(HERE/'status.json',rec);dump(HERE/'stages'/(stage+'.json'),rec)
 except Exception as ex:
  rec.update(status='failed',error=repr(ex),seconds=time.time()-t);dump(HERE/'status.json',rec);dump(HERE/'stages'/(stage+'.json'),rec);traceback.print_exc();raise
