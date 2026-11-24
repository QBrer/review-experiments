"""Selection reads raw inputs only; never reads experiment outcome tables."""
from core import *
import csv

def main():
    freeze();p=cfg();ds=open_inputs();off=offsets(ds);ref=ds['H2020'];n=p['window_size']
    output=ROOT/'selection';output.mkdir(exist_ok=True)
    candpath=output/'candidates.csv'
    if (output/'selection_frozen.json').exists():
        print('Frozen selection exists; no reselection');return
    if not (output/'scan_complete.json').exists():
        rows=[];valid_rows=0;eligible=0
        # Every full Han2020-grid window appears in the audit, including rejected ones.
        for r in range(0,ref.height-n+1,n):
            tr=ref.window_transform(Window(0,r,n,n));w=weights(tr,n)
            for c in range(0,ref.width-n+1,n):
                lon,lat=ref.transform*(c+n/2,r+n/2)
                dist=GEOD.inv(lon,lat,p['B2']['lon'],p['B2']['lat'])[2]/1000
                rec=dict(id=f'r{r}_c{c}',row=r,col=c,lon=lon,lat=lat,B2_distance_km=dist,coverage=np.nan,pSL=np.nan,pOthers=np.nan,H_SL=np.nan,H_six=np.nan,max_SL_subclass=np.nan,reason='')
                if any(min(r+dr,c+dc)<0 or r+dr+n>ds[k].height or c+dc+n>ds[k].width for k,(dr,dc) in off.items()):rec['reason']='outside_common_extent'
                elif dist<p['B2_exclusion_km']:rec['reason']='B2_exclusion'
                else:
                    # Early coverage rejection is exact: an intersection cannot exceed any one mask.
                    arr={};v=np.ones((n,n),bool)
                    for k in ['H2020','W2020','H2000','H2010','H2015']:
                        dr,dc=off[k];a=ds[k].read(1,window=Window(c+dc,r+dr,n,n));arr[k]=a
                        v &= np.isin(a,FINE) if k.startswith('H') else (a>=1)&(a<=14)
                        if v.mean()<p['min_coverage']:
                            rec['reason']='coverage_below_95';rec['coverage_upper_bound']=float(v.mean());break
                    if not rec['reason']:
                        rec['coverage']=float(v.mean());valid_rows+=1
                        mass=np.array([area(v&(arr['H2020']==code),w) for code in FINE]);q=mass/mass.sum()
                        sl=q[1:5].sum();rec.update(pSL=sl,pOthers=q[5],H_six=float(-np.sum(q[q>0]*np.log2(q[q>0]))),max_SL_subclass=float(q[1:5].max()))
                        for code,z in zip(FINE,q):rec[f'p{code}']=float(z)
                        if not (.2<=sl<=.8):rec['reason']='SL_outside_20_80'
                        elif q[5]<.1:rec['reason']='Others_below_10'
                        else:
                            u=q[1:5]/sl;rec['H_SL']=float(-np.sum(u[u>0]*np.log2(u[u>0])));rec['reason']='eligible';eligible+=1
                rows.append(rec)
            write_csv(candpath,rows)
            print(f'row {r}/{ref.height}; candidates={len(rows)} coverage_pass={valid_rows} eligible={eligible}',flush=True)
        dump(output/'scan_complete.json',dict(time=now(),n_candidates=len(rows),n_eligible=eligible,excluded_trailing_rows=ref.height%n,excluded_trailing_columns=ref.width%n))
    import pandas as pd
    df=pd.read_csv(candpath);e=df[df.reason=='eligible'].sort_values(['row','col']).copy()
    if len(e)==0:raise RuntimeError('STOP: empty eligible pool')
    lo,hi=np.quantile(e.H_SL,[.25,.75],method='linear')
    dump(output/'thresholds.json',dict(time=now(),Q25=lo,Q75=hi,n=len(e),input_candidates_sha256=sha(candpath)))
    if lo==hi:raise RuntimeError('STOP: equal sensitivity quantiles')
    pools={'High':e[e.H_SL>=hi].to_dict('records'),'Low':e[e.H_SL<=lo].to_dict('records')}
    rng=np.random.default_rng(20261016);selected=[];trace=[]
    for turn in range(24):
        group=['High','Low'][turn%2];pool=pools[group];available=[]
        for a in pool:
            if any(a['id']==b['id'] for b in selected):continue
            d=min((GEOD.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2] for b in selected),default=float('inf'))
            if d>=50000:available.append((a,d))
        if not available:
            dump(output/'selection_failure.json',dict(time=now(),reason='insufficient distance-eligible candidates',turn=turn,group=group,selected=selected))
            raise RuntimeError('STOP: cannot select 12 per group without relaxing requirements')
        if turn<2:choice=int(rng.integers(len(available)))
        else:
            top=max(d for a,d in available);choice=next(i for i,(a,d) in enumerate(available) if abs(d-top)<=1e-6)
        a,d=available[choice];a=dict(a,group=group,selection_order=turn+1,min_distance_to_previous_km=d/1000);selected.append(a)
        trace.append(dict(turn=turn+1,group=group,n_available=len(available),chosen=a['id'],minimum_distance_m=d,selection='random first in group' if turn<2 else 'global maximin'))
    write_csv(output/'selected_regions.csv',selected);dump(output/'sampling_trace.json',trace)
    features=[]
    for a in selected:
        r,c=int(a['row']),int(a['col']);coords=[ref.transform*(c,r),ref.transform*(c+n,r),ref.transform*(c+n,r+n),ref.transform*(c,r+n),ref.transform*(c,r)]
        features.append(dict(type='Feature',properties=clean(a),geometry=dict(type='Polygon',coordinates=[coords])))
    dump(output/'selected_regions.geojson',dict(type='FeatureCollection',features=features))
    dump(output/'selection_frozen.json',dict(frozen_at=now(),parameters_sha256=sha(ROOT/'parameters/frozen_parameters.json'),candidates_sha256=sha(candpath),selected_sha256=sha(output/'selected_regions.csv'),thresholds_sha256=sha(output/'thresholds.json'),n_High=12,n_Low=12,no_new_outcomes_computed=True,selection_code_sha256=sha(__file__)))
    for s in ds.values():s.close()
    print('SELECTION FROZEN: 12 High + 12 Low',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        dump(ROOT/'qc/selection_error.json',dict(time=now(),error=repr(e),formal_experiments_started=False));raise
