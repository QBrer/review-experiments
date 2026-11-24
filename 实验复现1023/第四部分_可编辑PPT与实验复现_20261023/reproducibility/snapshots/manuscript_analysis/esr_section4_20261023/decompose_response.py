"""Descriptive orthogonal decomposition of the existing balanced 3 x 3 x 2 design.
No rerunning experiments or modifying original outputs. Factors are equally weighted.
"""
from pathlib import Path
from itertools import combinations
import json,hashlib
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;B=R.parent
O=R/'figure_data';O.mkdir(exist_ok=True)
source=B/'实验独立复核_20261021/只读基线副本/results/experiment_1/coupling.csv'
d=pd.read_csv(source);d=d[d.group.isin(['High','Low'])].copy()
levels=[[3,10,30],[2000,2010,2015],['fine6','coarse3']]
index=pd.MultiIndex.from_product(levels,names=['scale','start_year','semantic'])
names=['S','T','M'];subsets=[s for k in range(1,4) for s in combinations(range(3),k)]
records=[];maxerr=0.
for (group,site),q in d.groupby(['group','site']):
 y=(1-q.set_index(['scale','start_year','semantic']).F1.reindex(index)).to_numpy().reshape(3,3,2)
 assert np.isfinite(y).all() and len(q)==18
 effects={():np.full((1,1,1),y.mean())}
 for subset in subsets:
  avg=y.mean(axis=tuple(i for i in range(3) if i not in subset),keepdims=True) if len(subset)<3 else y.copy()
  effect=avg.copy()
  for prev,val in effects.items():
   if set(prev).issubset(subset):effect=effect-val
  effects[subset]=effect
 total=float(((y-y.mean())**2).sum());ss=[]
 for subset in subsets:
  term='×'.join(names[i] for i in subset);value=float(np.broadcast_to(effects[subset],y.shape).ravel()@np.broadcast_to(effects[subset],y.shape).ravel());ss.append(value)
  records.append(dict(group=group,site=site,term=term,ss=value,total_ss=total,share=100*value/total))
 err=abs(sum(ss)-total);maxerr=max(maxerr,err);assert err<1e-12
 # Independently verify through a full orthonormal Kronecker contrast basis.
 def basis(n):
  from scipy.linalg import helmert
  return np.vstack([np.ones(n)/np.sqrt(n),helmert(n,full=False)])
 coef=np.einsum('ai,bj,ck,ijk->abc',basis(3),basis(3),basis(2),y)
 for subset,value in zip(subsets,ss):
  inds=[list(range(1,n)) if axis in subset else [0] for axis,n in enumerate(y.shape)]
  np.testing.assert_allclose(np.sum(coef[np.ix_(*inds)]**2),value,rtol=1e-10,atol=1e-12)
out=pd.DataFrame(records);out.to_csv(O/'factor_decomposition_by_window.csv',index=False,encoding='utf-8-sig')
terms=['×'.join(names[i] for i in s) for s in subsets];summ=[]
for group in ['Low','High','All']:
 q=out if group=='All' else out[out.group==group]
 mat=q.pivot(index='site',columns='term',values='ss')[terms].to_numpy()
 total=q.groupby('site').total_ss.first().reindex(q.pivot(index='site',columns='term',values='ss').index).to_numpy()
 rng=np.random.default_rng(20261023);ix=rng.integers(len(mat),size=(10000,len(mat)))
 # Report equal-window averages of within-window proportions, avoiding domination by
 # windows with high total response variance. Bootstrap is descriptive, no p values.
 shares=100*mat/total[:,None];rep=shares[ix].mean(axis=1)
 for j,term in enumerate(terms):
  summ.append(dict(group=group,term=term,n=len(mat),share_mean=shares[:,j].mean(),ci_low=np.quantile(rep[:,j],.025),ci_high=np.quantile(rep[:,j],.975)))
 interaction=shares[:,3:].sum(axis=1);ri=interaction[ix].mean(axis=1)
 summ.append(dict(group=group,term='Interactions',n=len(mat),share_mean=interaction.mean(),ci_low=np.quantile(ri,.025),ci_high=np.quantile(ri,.975)))
summary=pd.DataFrame(summ);summary.to_csv(O/'factor_decomposition_summary.csv',index=False,encoding='utf-8-sig')
record={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'windows':24,'conditions_per_window':18,'response':'1-F1; semantic levels use their own native change reference','aggregation':'equal-window mean of within-window SS proportions','factor_levels':{'S':levels[0],'T':levels[1],'M':levels[2]},'max_SS_closure_error':maxerr,'independent_Helmert_basis_check':True,'bootstrap':'10000 whole-window draws; seed 20261023; descriptive pointwise 95% intervals','interpretation':'Design-specific response variation; not causal importance or accuracy improvement.'}
(R/'decomposition_audit.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(summary.to_string(index=False))
