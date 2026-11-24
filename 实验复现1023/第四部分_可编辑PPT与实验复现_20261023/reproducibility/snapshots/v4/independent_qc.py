"""Checks independent expressions against cached matching. No performance-based tuning."""
from engine import *
rng=np.random.default_rng(529)
n=80;pad=13;shape=n+2*pad
tiles=rng.integers(0,6,(15,15),dtype=np.int8)
h=np.repeat(np.repeat(tiles,8,0),8,1)[:shape,:shape].copy();w=h.copy();valid=np.ones_like(h,bool)
hb=boundary(h,valid);wb=boundary(w,valid);hd=binary_dilation(hb,structure=CROSS);wd=binary_dilation(wb,structure=CROSS)
rr,cc=np.indices((n,n));rr=rr.ravel().astype(np.int32);cc=cc.ravel().astype(np.int32);wt=np.linspace(1,1.2,n)[rr]
hist,edge=surface_kernel(h,w,hb,wb,hd,wd,rr,cc,wt,V,pad)
p=np.full((6,14),.001)
for i in range(6):p[i,i]=1
p/=p.sum(1)[:,None];model={'p':p,'present':np.ones(6,bool)}
cache={'hist0':hist,'hist1':hist,'edges0':edge,'edges1':edge}
records=[]
for d in [np.array([[3,-2],[-4,1]]),np.zeros((2,2),int),np.array([[6,6],[-6,-6]])]:
 case={'d':d};z,ok,raw=case_surfaces(cache,case,model);pred=solve(z,ok,{'g1':0,'g2':0,'g3':0,'lam':0})
 # Boundary tolerance permits a one-pixel plateau; A1 need not prefer its center.
 assert np.all(np.linalg.norm(pred[1]+d,axis=1)<=1),(d,pred)
 assert np.all(pred[2:]==-d[None]),(d,pred)
 for t in range(2):
  for u in [[0,0],[-6,6],[2,-1]]:
   k=int(np.where((U==u).all(1))[0][0]);dr,dc=d[t]+u
   ih=h[rr+pad,cc+pad];iw=w[rr+pad+dr,cc+pad+dc]
   independent=np.bincount(ih.astype(int)*14+iw,weights=wt,minlength=84).reshape(6,14)
   assert np.allclose(independent,raw[t][0][k],rtol=0,atol=1e-9)
   hboundary=hb[rr+pad,cc+pad];wboundary=wb[rr+pad+dr,cc+pad+dc]
   rec=wt[hboundary&wd[rr+pad+dr,cc+pad+dc]].sum()/wt[hboundary].sum()
   prec=wt[wboundary&hd[rr+pad,cc+pad]].sum()/wt[wboundary].sum()
   f1=2*rec*prec/(rec+prec)
   assert abs(raw[t][2][k]-f1)<1e-12
 records.append({'injected':d,'A1_within_defined_one_pixel_tolerance':True,'A2_A3_exact':True,'independent_hist_and_boundary_scores_match':True})
dump(ROOT/'qc/independent_matching_checks.json',{'passed':True,'records':records,'no_real_scores_consulted':True})
print('Independent synthetic matching checks passed')
