from ablation import *

def main():
 frozen=load(HERE/'ablation_frozen.json')
 assert sha(HERE/'ablation.py')==frozen['code_sha256']
 assert sha(OLD/'engine.py')==frozen['prior_engine_sha256']
 assert sha(HERE/'PROTOCOL.md')==frozen['protocol_sha256']
 assert sha(HERE/'class_model.json')==frozen['matrix_sha256']
 a=pd.read_csv(HERE/'all_alignment_metrics.csv');pred=pd.read_csv(HERE/'locked_predictions.csv')
 truth={r['case_id']:r for r in load(HERE/'evaluator/private_truth.json')}
 maxerr=0
 for r in a.itertuples():
  d=np.array(truth[r.case_id]['d']);u=np.array([[r.u2010_r,r.u2010_c],[r.u2020_r,r.u2020_c]])
  z=.5*(np.hypot(*(u[0]+d[0]))+np.hypot(*(u[1]+d[1])))
  maxerr=max(maxerr,abs(r.E-z))
 assert maxerr<1e-12
 # Under lambda=0 the presence of a disabled temporal term must not alter outputs.
 identities=[]
 keys=['site','case_id','gamma'];cols=['u2010_r','u2010_c','u2020_r','u2020_c']
 for left,right in [('G','GT'),('GS','GST')]:
  x=pred[(pred.method==left)&(pred['lambda']==0)][keys+cols]
  y=pred[(pred.method==right)&(pred['lambda']==0)][keys+cols]
  j=x.merge(y,on=keys,suffixes=('_a','_b'),validate='one_to_one');assert len(j)==len(x)
  assert all((j[c+'_a']==j[c+'_b']).all() for c in cols)
  identities.append({'left':left,'right':right,'rows':len(j),'exact_match':True})
 old=pd.read_csv(OLD/'locked_candidate_predictions.csv');old=old[old.candidate==3]
 current=pred[(pred.dataset=='old40_exploratory')&(pred.method=='GST')&pred.is_primary]
 j=current.merge(old,on=['site','case_id'],suffixes=('_new','_old'),validate='one_to_one');assert len(j)==280
 assert all((j[c+'_new']==j[c+'_old']).all() for c in cols)
 oldsites=pd.read_csv(OLD/'split_manifest.csv');newsites=pd.read_csv(HERE/'new_sites.csv')
 assert not set(newsites.block)&set(oldsites.block)
 dist=min(G.inv(r.lon,r.lat,o.lon,o.lat)[2] for r in newsites.itertuples() for o in oldsites.itertuples());assert dist>=100000
 # Four sites fixed by geographic order; no effect-based selection.
 sample=newsites.sort_values(['row','col']).iloc[[0,20,40,62]].to_dict('records')
 manifest=pd.read_csv(HERE/'raster_manifest.csv');tasks=pd.read_csv(HERE/'task_metrics.csv');ds=open_data();checks=[]
 for s in sample:
  data,valid,safe,rw,tr=read_site(s,ds);_,_,ev,_=masks(s['id'],safe)
  c0=data[2][PAD:PAD+N,PAD:PAD+N]==13;c1=data[3][PAD:PAD+N,PAD:PAD+N]==13;ref=c0!=c1
  for ci in [0,2,6]:
   case=cases(s['id'])[ci]
   for method in METHODS:
    rows=manifest[(manifest.site==s['id'])&(manifest.case_id==case['case_id'])&(manifest.method==method)&manifest.is_primary].sort_values('year')
    assert len(rows)==2
    arrays=[]
    for p in rows.file:
     with rasterio.open(HERE/p) as d:arrays.append(d.read(1))
    pr=(arrays[0]==13)!=(arrays[1]==13);w=np.broadcast_to(rw[:,None],ev.shape)
    tp=float(w[ev&pr&ref].sum());fp=float(w[ev&pr&~ref].sum());fn=float(w[ev&~pr&ref].sum());den=2*tp+fp+fn;F1=2*tp/den if den>0 else np.nan
    r=tasks[(tasks.site==s['id'])&(tasks.case_id==case['case_id'])&(tasks.method==method)&tasks.is_primary&(tasks.event=='change_union')].iloc[0]
    diff=abs(F1-r.F1) if np.isfinite(F1) else 0;assert diff<1e-12
    assert max(abs(tp/1e6-r.tp_km2),abs(fp/1e6-r.fp_km2),abs(fn/1e6-r.fn_km2))<1e-8
    checks.append({'site':s['id'],'case_id':case['case_id'],'method':method,'F1_difference':diff,'passed':True})
 for d in ds.values():d.close()
 dump(HERE/'qc/independent_result_audit.json',{'passed':True,'frozen_code_unchanged':True,'all_geometric_rows':len(a),'max_error_difference':maxerr,'lambda_zero_identities':identities,'GST_matches_v4_rows':280,'new_old_min_center_distance_m':dist,'saved_raster_checks':checks})
 print('AUDIT PASSED',len(a),'geometric rows;',len(checks),'raster task cases')
if __name__=='__main__':main()
