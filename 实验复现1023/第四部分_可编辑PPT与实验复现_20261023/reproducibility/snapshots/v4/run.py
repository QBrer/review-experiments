import engine as e
from engine import *
import argparse,shutil,traceback,psutil
from scipy.spatial.distance import cdist
from sklearn.tree import DecisionTreeRegressor,export_text
from sklearn.impute import SimpleImputer
import joblib

def unit_checks():
 rng=np.random.default_rng(17);n=30;pad=13
 h=rng.integers(0,6,(n+2*pad,)*2,dtype=np.int8);w=h.copy();v=np.ones_like(h,bool)
 hb=boundary(h,v);wb=boundary(w,v);hd=binary_dilation(hb,structure=CROSS);wd=hd.copy()
 rr,cc=np.indices((n,n));rr=rr.ravel().astype(np.int32);cc=cc.ravel().astype(np.int32);wt=np.linspace(600,650,len(rr))
 hists,edges=surface_kernel(h,w,hb,wb,hd,wd,rr,cc,wt,np.array([[0,0],[3,-2]],np.int16),pad)
 for k,(dr,dc) in enumerate([[0,0],[3,-2]]):
  ids=h[rr+pad,cc+pad]*14+w[rr+pad+dr,cc+pad+dc]
  direct=np.bincount(ids,weights=wt,minlength=84).reshape(6,14)
  assert np.allclose(hists[k],direct,rtol=0,atol=1e-8)
 assert hists[0].trace()==wt.sum() or abs(hists[0].trace()-wt.sum())<1e-7
 z=np.zeros((2,2,169));ok=np.zeros((2,2),bool);params={'g1':0,'g2':0,'g3':0,'lam':0}
 assert not solve(z,ok,params).any()
 # Distinct targets must remain distinct when temporal penalty is zero.
 for t,target in enumerate([[2,-3],[-1,4]]):z[t,:,:]=-np.sum((U-target)**2,axis=1)
 pred=solve(z,np.ones((2,2),bool),params);assert np.array_equal(pred[3],[[2,-3],[-1,4]])
 # Score-surface translation is an exact representation of injected-array search.
 off=(3,-2);correct=np.array([-3,2]);uix=np.where((U==correct).all(1))[0][0]
 index=(U[:,0]+off[0]+12)*25+(U[:,1]+off[1]+12);assert index[uix]==312
 safe=np.ones((1200,1200),bool);pilot,pw,ev,coords=masks('unit',safe)
 assert len(coords)==50 and pilot.sum()==45000 and not np.any(pilot&ev)
 assert np.isclose(pw.sum(),1200**2)
 f=FAMILY_WEIGHT;assert np.isclose(f.sum(),1)
 dump(ROOT/'qc/unit_checks.json',{'passed':True,'checks':['independent weighted joint histogram','empty score fallback','joint independent optimum','injection inverse sign','fixed disjoint pilot evaluation','inverse inclusion weights','family weights']})

def freeze():
 if (ROOT/'frozen_parameters.json').exists():raise RuntimeError('Already frozen; use next stage')
 design=ROOT.parent/'新实验总方案_v4_跨产品对齐_20261022';c=load(design/'新实验总方案_v4_参数草案.json')
 assert sha(design/'新实验总方案_v4.md')==c['provenance']['design_sha256']
 assert sha(design/'开发与测试候选名单_100窗.csv')==c['provenance']['split_sha256']
 c['status']='FROZEN_FOR_EXECUTION';c['formal_execution_started']=True;c['authorized_date']='2026-10-22';c['implementation_sha256']=sha(ROOT/'IMPLEMENTATION.md')
 dump(ROOT/'frozen_parameters.json',c);shutil.copy2(design/'开发与测试候选名单_100窗.csv',ROOT/'split_manifest.csv');shutil.copy2(design/'新实验总方案_v4.md',ROOT/'design_snapshot.md')
 sites=pd.read_csv(ROOT/'split_manifest.csv');dev=sites[sites.phase=='development']
 groups=dev.block.unique().tolist();rng=np.random.default_rng(20261022);groups=[groups[i] for i in rng.permutation(len(groups))];bins=[[] for _ in range(5)];ns=np.zeros(5,int)
 for g in groups:
  i=int(ns.argmin());bins[i].append(g);ns[i]+=(dev.block==g).sum()
 folds=[]
 for i,b in enumerate(bins):
  val=dev[dev.block.isin(b)];train=dev[~dev.block.isin(b)];ids=[]
  for s in train.to_dict('records'):
   if min(G.inv(s['lon'],s['lat'],v['lon'],v['lat'])[2] for v in val.to_dict('records'))>=100000:ids.append(s['id'])
  folds.append({'fold':i,'training':ids,'validation':val.id.tolist()})
 dump(ROOT/'fold_manifest.json',folds)
 old={};roots=[ROOT.parent/'实验核查包_代码参数结果表_20261021',Path('E:/数据对齐实验数据2/新-实验方案')]
 for base in roots:
  for p in base.rglob('*'):
   if p.is_file():
    s=p.stat();old[str(p)]={'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
    if p.suffix.lower() in {'.py','.json','.csv','.md','.geojson'}:old[str(p)]['sha256']=sha(p)
 for p in [ROOT.parent/'第四部分1021.docx',*design.glob('*')]:
  if p.is_file():old[str(p)]={'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':sha(p)}
 dump(ROOT/'protected_before.json',old)
 truth=[]
 for s in sites.to_dict('records'):
  for k,x in enumerate(cases(s['id'])):truth.append({'site':s['id'],'phase':s['phase'],'case_index':k,**x})
 dump(ROOT/'evaluator/private_truth_manifest.json',truth)
 dump(ROOT/'environment.json',{'python':sys.executable,'numpy':np.__version__,'rasterio':rasterio.__version__,'threads':6,'rss':psutil.Process().memory_info().rss})
 dump(ROOT/'code_hashes.json',{p.name:sha(p) for p in ROOT.glob('*.py')})
 print('FROZEN',len(sites),'windows; fold training counts',[len(x['training']) for x in folds],flush=True)

def extract_stage(phase,kind):
 sites=pd.read_csv(ROOT/'split_manifest.csv');sites=sites[sites.phase==phase]
 if phase=='test' and kind=='full':assert (ROOT/'locked_choices.csv').exists()
 ds=open_data()
 try:
  for i,s in enumerate(sites.to_dict('records')):
   path=ROOT/'cache'/kind/(s['id']+'.npz')
   if path.exists():print('CACHE EXISTS',phase,kind,s['id'],flush=True);continue
   rec=extract(s,ds,kind);print(f'{phase} {kind} {i+1}/{len(sites)} {s["id"]} {rec["seconds"]:.1f}s',flush=True)
 finally:
  for d in ds.values():d.close()

def prepare_surfaces(ids,model,kind):
 out=[]
 for sid in ids:
  cache=read_cache(sid,kind)
  for ci,c in enumerate(cases(sid)):
   z,ok,_=case_surfaces(cache,c,model);out.append((sid,ci,c,z,ok))
 return out
def calibrate(ids,model):
 surf=prepare_surfaces(ids,model,'full');params={'g1':0,'g2':0,'g3':0,'lam':0};record=[]
 for a in [1,2,3]:
  besterr=float('inf');winner=None
  opts=[(l,g) for l in [0,.25,.5,1] for g in [0,.25,.5]] if a==3 else [(0,g) for g in [0,.25,.5]]
  for lam,g in opts:
   q=params.copy()
   if a==1:q['g1']=g
   if a==2:q['g2']=g
   if a==3:q.update(lam=lam,g3=g)
   total=0
   for sid,ci,c,z,ok in surf:total+=error(solve(z,ok,q),c)[a]*FAMILY_WEIGHT[ci]/len(ids)
   record.append({'candidate':a,'lambda':lam,'gamma':g,'training_mean_error':total})
   if total<besterr-1e-12:besterr=total;winner=q
  params=winner
 return params,record,surf
def dataset(ids,model,params,surf=None):
 rows=[];xs=[];ys=[];weights=[]
 if surf is None:surf=prepare_surfaces(ids,model,'full')
 cacheid=None
 for sid,ci,c,z,ok in surf:
  if sid!=cacheid:cache=read_cache(sid,'pilot');cacheid=sid
  x=features(cache,c,ci,model,params);pred=solve(z,ok,params)
  xs.append(x);ys.append(error(pred,c));weights.append(FAMILY_WEIGHT[ci]);rows.append({'site':sid,'case_index':ci,'case_id':c['case_id']})
 return np.array(xs),np.array(ys),np.array(weights),rows
def train_model(X,Y,wt,n):
 imputer=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True);xx=imputer.fit_transform(X[:,:n]);tree=DecisionTreeRegressor(max_depth=2,min_samples_leaf=56,criterion='squared_error',random_state=20261022)
 tree.fit(xx,Y,sample_weight=wt)
 return {'imputer':imputer,'tree':tree,'n':n}
def predict_model(m,X):
 xx=m['imputer'].transform(X[:,:m['n']]);pred=m['tree'].predict(xx);choice=np.array([np.flatnonzero(p<=p.min()+1e-12)[0] for p in pred]);leaf=m['tree'].apply(xx)
 return choice,pred,leaf
def fit(ids,name):
 model=class_model(ids);params,cal,surf=calibrate(ids,model);X,Y,wt,rows=dataset(ids,model,params,surf)
 means=np.average(Y,axis=0,weights=wt);single=int(np.flatnonzero(means<=means.min()+1e-12)[0]);bundle={'class':model,'params':params,'single':single,'train_ids':ids,'basic':None,'full':None}
 if len(ids)>=16:
  bundle.update(basic=train_model(X,Y,wt,21),full=train_model(X,Y,wt,42))
  for n in ['basic','full']:
   ch,pr,leaves=predict_model(bundle[n],X)
   for leaf in np.unique(leaves):assert len({rows[i]['site'] for i in np.where(leaves==leaf)[0]})>=8
 out=ROOT/'models'/name;out.mkdir(parents=True,exist_ok=True);joblib.dump(bundle,out/'bundle.joblib')
 dump(out/'parameters.json',{'training_windows':len(ids),'class':model,'params':params,'single_best':single,'training_candidate_errors':means,'calibration':cal})
 pd.DataFrame([dict(**r,**{f'x{i:02d}':x[i] for i in range(42)},**{f'E_A{i}':y[i] for i in range(4)}) for r,x,y in zip(rows,X,Y)]).to_csv(out/'training_records.csv',index=False,encoding='utf-8-sig')
 for n in ['basic','full']:
  if bundle[n]:(out/(n+'_tree.txt')).write_text(export_text(bundle[n]['tree']),encoding='utf8')
 return bundle
def train():
 folds=load(ROOT/'fold_manifest.json');oof=[]
 for f in folds:
  name='fold'+str(f['fold']);print('TRAIN',name,len(f['training']),flush=True);b=fit(f['training'],name)
  X,Y,wt,rows=dataset(f['validation'],b['class'],b['params'])
  for n in ['basic','full']:
   choices=predict_model(b[n],X)[0] if b[n] else np.full(len(X),b['single'])
   for r,y,ch in zip(rows,Y,choices):oof.append(dict(**r,fold=f['fold'],method=n,chosen=int(ch),E_chosen=y[ch],E_single=y[b['single']],**{f'E_A{k}':y[k] for k in range(4)}))
 pd.DataFrame(oof).to_csv(ROOT/'development_oof.csv',index=False,encoding='utf-8-sig')
 sites=pd.read_csv(ROOT/'split_manifest.csv');ids=sites[sites.phase=='development'].id.tolist();print('TRAIN final',len(ids),flush=True);fit(ids,'final')
 dump(ROOT/'models_frozen.json',{'time':time.strftime('%Y-%m-%d %H:%M:%S'),'model_sha256':sha(ROOT/'models/final/bundle.joblib'),'oof_sha256':sha(ROOT/'development_oof.csv'),'test_performance_accessed':False})

def test_features():
 b=joblib.load(ROOT/'models/final/bundle.joblib');sites=pd.read_csv(ROOT/'split_manifest.csv');rows=[]
 for sid in sites[sites.phase=='test'].id:
  cache=read_cache(sid,'pilot')
  for ci,c in enumerate(cases(sid)):
   x=features(cache,c,ci,b['class'],b['params']);rows.append({'site':sid,'case_id':c['case_id'],**{f'x{i:02d}':x[i] for i in range(42)}})
 pd.DataFrame(rows).to_csv(ROOT/'test_diagnostics.csv',index=False,encoding='utf-8-sig')
 dump(ROOT/'test_diagnostics_manifest.json',{'sha256':sha(ROOT/'test_diagnostics.csv'),'rows':len(rows),'contains_truth_or_full_scores':False})

def choose():
 # This function reads only frozen model and pilot feature table, never private truths or full caches.
 b=joblib.load(ROOT/'models/final/bundle.joblib');d=pd.read_csv(ROOT/'test_diagnostics.csv');X=d[[f'x{i:02d}' for i in range(42)]].to_numpy();rows=[]
 for name in ['basic','full']:
  if b[name]:ch,pred,leaf=predict_model(b[name],X)
  else:ch=np.full(len(X),b['single']);pred=np.full((len(X),4),np.nan);leaf=np.full(len(X),-1)
  for j,r in d.iterrows():rows.append({'site':r.site,'case_id':r.case_id,'method':name,'chosen':int(ch[j]),'leaf':int(leaf[j]),**{f'pred_E_A{k}':pred[j,k] for k in range(4)}})
 for _,r in d.iterrows():rows.append({'site':r.site,'case_id':r.case_id,'method':'single_best','chosen':b['single'],'leaf':-1})
 pd.DataFrame(rows).to_csv(ROOT/'locked_choices.csv',index=False,encoding='utf-8-sig')
 dump(ROOT/'choices_frozen.json',{'time':time.strftime('%Y-%m-%d %H:%M:%S'),'sha256':sha(ROOT/'locked_choices.csv'),'model_sha256':sha(ROOT/'models/final/bundle.joblib'),'test_truth_evaluated':False})
 print('LOCKED',len(rows),'choices before full test matching',flush=True)

def predictions():
 assert sha(ROOT/'locked_choices.csv')==load(ROOT/'choices_frozen.json')['sha256']
 b=joblib.load(ROOT/'models/final/bundle.joblib');sites=pd.read_csv(ROOT/'split_manifest.csv');rows=[]
 for s in sites[sites.phase=='test'].to_dict('records'):
  cache=read_cache(s['id'],'full')
  for ci,c in enumerate(cases(s['id'])):
   z,ok,_=case_surfaces(cache,c,b['class']);pred=solve(z,ok,b['params'])
   for a in range(4):rows.append({'site':s['id'],'case_id':c['case_id'],'candidate':a,'u2010_r':int(pred[a,0,0]),'u2010_c':int(pred[a,0,1]),'u2020_r':int(pred[a,1,0]),'u2020_c':int(pred[a,1,1])})
 pd.DataFrame(rows).to_csv(ROOT/'locked_candidate_predictions.csv',index=False,encoding='utf-8-sig')
 dump(ROOT/'predictions_frozen.json',{'time':time.strftime('%Y-%m-%d %H:%M:%S'),'sha256':sha(ROOT/'locked_candidate_predictions.csv'),'test_metrics_computed':False})
 print('PREDICTIONS LOCKED',len(rows),flush=True)

def metrics(pred,ref,mask,rw):
 w=np.broadcast_to(rw[:,None],mask.shape);tp=float(w[mask&pred&ref].sum());fp=float(w[mask&pred&~ref].sum());fn=float(w[mask&~pred&ref].sum());den=2*tp+fp+fn
 return {'tp_km2':tp/1e6,'fp_km2':fp/1e6,'fn_km2':fn/1e6,'reference_km2':float(w[mask&ref].sum()/1e6),'F1':2*tp/den if den>0 else np.nan,'IoU':tp/(tp+fp+fn) if tp+fp+fn>0 else np.nan,'coverage':1.0}
def evaluate():
 assert sha(ROOT/'locked_candidate_predictions.csv')==load(ROOT/'predictions_frozen.json')['sha256']
 preds=pd.read_csv(ROOT/'locked_candidate_predictions.csv');truth={x['case_id']:x for x in load(ROOT/'evaluator/private_truth_manifest.json')};sites=pd.read_csv(ROOT/'split_manifest.csv');ds=open_data();rows=[];task=[];raster_index=[];natural=[]
 for ni,s in enumerate(sites[sites.phase=='test'].to_dict('records')):
  data,valid,safe,rw,tr=read_site(s,ds);pilot,pw,ev,coords=masks(s['id'],safe)
  core=lambda a,dr=0,dc=0:a[PAD+dr:PAD+dr+N,PAD+dc:PAD+dc+N]
  r0=core(data[2])==13;r1=core(data[3])==13;refs={'change_union':r0!=r1,'expansion':~r0&r1,'contraction':r0&~r1}
  saved={};arrays={};shifts=preds[preds.site==s['id']]
  for r in shifts.to_dict('records'):
   case=truth[r['case_id']];d=np.array(case['d']);u=np.array([[r['u2010_r'],r['u2010_c']],[r['u2020_r'],r['u2020_c']]]);res=u+d
   # Save/re-read each exact output raster before computing its event scores.
   mapped=[]
   for t in range(2):
    dr,dc=map(int,res[t]);key=(t,dr,dc)
    if key not in saved:
     a=core(data[t+2],dr,dc).copy();a[~safe]=255;p=ROOT/'outputs'/s['id']/f'W{[2010,2020][t]}_r{dr}_c{dc}.tif';write_tif(p,a,tr);saved[key]=str(p.relative_to(ROOT));arrays[key]=a
    mapped.append(arrays[key]);raster_index.append({'site':s['id'],'case_id':r['case_id'],'candidate':r['candidate'],'year':[2010,2020][t],'file':saved[key]})
   err=np.linalg.norm(res,axis=1);meters=[]
   lon,lat=tr*(N/2,N/2)
   for dr,dc in res:
    x,y=tr*(N/2+int(dc),N/2+int(dr));meters.append(G.inv(lon,lat,x,y)[2])
   base={**r,'block':s['block'],'family':case['family'],'m':case['m'],'case_index':case['case_index']}
   rows.append({**base,'E':float(err.mean()),'E_m':float(np.mean(meters)),'within1':bool((err<=1).all()),'exact':bool((res==0).all()),'nominal_modified':bool((u!=0).any())})
   a=mapped[0]==13;b=mapped[1]==13;events={'change_union':a!=b,'expansion':~a&b,'contraction':a&~b}
   for event in events:task.append({**base,'event':event,**metrics(events[event],refs[event],ev,rw)})
   if case['family']=='G0':
    for t in range(2):
     h=core(data[t]);w=mapped[t];wt=np.broadcast_to(rw[:,None],safe.shape)
     for hc in H_CODES:
      for wc in range(1,15):natural.append({'site':s['id'],'candidate':r['candidate'],'year':[2010,2020][t],'Han_code':int(hc),'Wang_code':wc,'area_km2':float(wt[safe&(h==hc)&(w==wc)].sum()/1e6)})
  maskpath=ROOT/'outputs'/s['id']/'evaluation_mask.tif';write_tif(maskpath,ev.astype(np.uint8),tr,nodata=0)
  print('EVALUATED',ni+1,s['id'],'unique rasters',len(saved),flush=True)
 for d in ds.values():d.close()
 for name,data in [('test_alignment_metrics',rows),('test_change_metrics',task),('prediction_raster_manifest',raster_index),('natural_pair_relations',natural)]:pd.DataFrame(data).to_csv(ROOT/(name+'.csv'),index=False,encoding='utf-8-sig')
 dump(ROOT/'evaluation_complete.json',{'alignment_rows':len(rows),'change_rows':len(task),'source_preserved':True,'evaluator_truth_opened_after_predictions_frozen':True})

def main(stage):
 if stage=='prepare':unit_checks();freeze()
 elif stage=='development_extract':extract_stage('development','pilot');extract_stage('development','full')
 elif stage=='train':train()
 elif stage=='test_pilot':extract_stage('test','pilot');test_features()
 elif stage=='choose':choose()
 elif stage=='test_predict':extract_stage('test','full');predictions()
 elif stage=='evaluate':evaluate()
 else:raise ValueError(stage)
if __name__=='__main__':
 start=time.time();stage=sys.argv[1];rec={'stage':stage,'start':time.strftime('%Y-%m-%d %H:%M:%S'),'status':'running'};dump(ROOT/'status.json',rec)
 try:
  main(stage);rec.update(status='complete',seconds=time.time()-start,peak_working_set=psutil.Process().memory_info()._asdict());dump(ROOT/'stages'/(stage+'.json'),rec);dump(ROOT/'status.json',rec)
 except Exception as x:
  rec.update(status='failed',error=repr(x),seconds=time.time()-start);dump(ROOT/'stages'/(stage+'.json'),rec);dump(ROOT/'status.json',rec);traceback.print_exc();raise
