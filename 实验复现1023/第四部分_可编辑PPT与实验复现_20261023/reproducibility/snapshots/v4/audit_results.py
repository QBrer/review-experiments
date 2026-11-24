from engine import *
import joblib
sites=pd.read_csv(ROOT/'split_manifest.csv');folds=load(ROOT/'fold_manifest.json');splitcheck=[]
for f in folds:
 train=sites[sites.id.isin(f['training'])];val=sites[sites.id.isin(f['validation'])]
 md=min(G.inv(a.lon,a.lat,b.lon,b.lat)[2] for a in train.itertuples() for b in val.itertuples());assert md>=100000
 assert not set(train.block)&set(val.block)
 splitcheck.append({'fold':f['fold'],'train':len(train),'validation':len(val),'minimum_center_distance_m':md})
train=sites[sites.phase=='development'];test=sites[sites.phase=='test'];md=min(G.inv(a.lon,a.lat,b.lon,b.lat)[2] for a in train.itertuples() for b in test.itertuples());assert md>=100000
b=joblib.load(ROOT/'models/final/bundle.joblib');assert not set(b['train_ids'])&set(test.id)
preds=pd.read_csv(ROOT/'locked_candidate_predictions.csv');obs=pd.read_csv(ROOT/'test_alignment_metrics.csv');task=pd.read_csv(ROOT/'test_change_metrics.csv');manifest=pd.read_csv(ROOT/'prediction_raster_manifest.csv');truth={x['case_id']:x for x in load(ROOT/'evaluator/private_truth_manifest.json')}
alignment_error=0
for r in obs.itertuples():
 d=np.array(truth[r.case_id]['d']);u=np.array([[r.u2010_r,r.u2010_c],[r.u2020_r,r.u2020_c]])
 manual=(np.hypot(*(u[0]+d[0]))+np.hypot(*(u[1]+d[1])))/2;alignment_error=max(alignment_error,abs(manual-r.E))
assert alignment_error<1e-12
ds=open_data();records=[]
# Geographically ordered fixed four examples; select one scenario of each family, all candidates.
for s in test.sort_values(['row','col']).iloc[[0,10,20,30]].to_dict('records'):
 data,valid,safe,rw,tr=read_site(s,ds);_,_,ev,_=masks(s['id'],safe)
 reference0=data[2][PAD:PAD+N,PAD:PAD+N]==13;reference1=data[3][PAD:PAD+N,PAD:PAD+N]==13;reference=reference0!=reference1
 for ci in [0,2,6]:
  c=cases(s['id'])[ci]
  for a in range(4):
   m=manifest[(manifest.site==s['id'])&(manifest.case_id==c['case_id'])&(manifest.candidate==a)].sort_values('year')
   arrays=[]
   for path in m.file:
    with rasterio.open(ROOT/path) as d:arrays.append(d.read(1))
   prediction=(arrays[0]==13)!=(arrays[1]==13)
   # Independent row counts times row areas, rather than per-pixel boolean weighted sum.
   tp=float(np.dot(np.count_nonzero(ev&prediction&reference,axis=1),rw));fp=float(np.dot(np.count_nonzero(ev&prediction&~reference,axis=1),rw));fn=float(np.dot(np.count_nonzero(ev&~prediction&reference,axis=1),rw));den=2*tp+fp+fn;f1=2*tp/den if den else np.nan
   row=task[(task.site==s['id'])&(task.case_id==c['case_id'])&(task.candidate==a)&(task.event=='change_union')].iloc[0]
   diff=abs(f1-row.F1) if np.isfinite(f1) else 0;assert diff<1e-12
   assert max(abs(tp/1e6-row.tp_km2),abs(fp/1e6-row.fp_km2),abs(fn/1e6-row.fn_km2))<1e-8
   records.append({'site':s['id'],'case_id':c['case_id'],'candidate':a,'F1_absolute_difference':diff,'passed':True})
for d in ds.values():d.close()
dump(ROOT/'qc/independent_result_audit.json',{'passed':True,'folds':splitcheck,'test_development_min_center_m':md,'alignment_rows_checked':len(obs),'max_geometric_error_difference':alignment_error,'saved_raster_task_cases_checked':len(records),'records':records,'raw_labels_repaired':False})
print('Independent result audit passed',len(obs),'geometric results;',len(records),'saved-raster task comparisons')
