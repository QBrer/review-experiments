from pathlib import Path
import os,sys,json,hashlib,time,itertools
os.environ['GDAL_PAM_ENABLED']='NO'
import importlib.util
proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj)
ROOT=Path(__file__).resolve().parent
os.environ['NUMBA_CACHE_DIR']=str(ROOT/'numba_cache')
os.environ['MPLCONFIGDIR']=str(ROOT/'mplconfig')
import numpy as np,pandas as pd,rasterio
from rasterio.windows import Window
from scipy.ndimage import binary_dilation,minimum_filter
from numba import njit,prange,set_num_threads
from pyproj import Geod
set_num_threads(6)
G=Geod(ellps='WGS84');N=1200;PAD=13
H_CODES=np.array([1,21,22,23,24,3],np.uint8)
U=np.array(sorted(itertools.product(range(-6,7),repeat=2),key=lambda x:(abs(x[0])+abs(x[1]),x[0],x[1])),dtype=np.int16)
V=np.array(list(itertools.product(range(-12,13),repeat=2)),dtype=np.int16)
UNORM=np.abs(U).sum(1);DIST=np.abs(U[:,None,:]-U[None,:,:]).sum(2)
ZERO=int(np.where((U==0).all(1))[0][0]);FAMILY_WEIGHT=np.array([1/3]+[1/9]*6)
CROSS=np.array([[0,1,0],[1,1,1],[0,1,0]],bool)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for a in iter(lambda:f.read(2**20),b''):h.update(a)
 return h.hexdigest()
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item() if isinstance(x,np.generic) else str(x),allow_nan=True),encoding='utf8')
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def cfg():return load(ROOT/'frozen_parameters.json')
def seed(*args):return int.from_bytes(hashlib.sha256('|'.join(map(str,args)).encode()).digest()[:8],'little')
def cases(sid):
 rng=np.random.default_rng(seed(20261022,sid,'injection'));dirs=np.array([[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]])
 out=[{'family':'G0','m':0,'d':np.zeros((2,2),dtype=int)}]
 for family in ['G1','G2']:
  for m in [1,3,6]:
   j=int(rng.integers(8));k=j if family=='G1' else int(rng.choice([x for x in range(8) if x!=j]))
   out.append({'family':family,'m':m,'d':np.stack([dirs[j]*m,dirs[k]*m])})
 for i,c in enumerate(out):c['case_id']=hashlib.sha256(f'case-v4|{sid}|{i}'.encode()).hexdigest()[:20]
 return out
def open_data():return {k:rasterio.open(v['path'],'r') for k,v in cfg()['experiment3']['inputs'].items()}
def read_site(s,ds):
 data=[];meta=cfg()['experiment3']['inputs']
 for k in ['H2010','H2020','W2010','W2020']:
  dr,dc=meta[k]['offset_row_col'];x=ds[k].read(1,window=Window(int(s['col'])+dc-PAD,int(s['row'])+dr-PAD,N+2*PAD,N+2*PAD));assert x.shape==(N+2*PAD,)*2;data.append(x)
 tr=ds['H2020'].window_transform(Window(int(s['col']),int(s['row']),N,N))
 w=[]
 for i in range(N):
  x0,y0=tr*(0,i);x1,y1=tr*(1,i+1);w.append(abs(G.polygon_area_perimeter([x0,x1,x1,x0],[y0,y0,y1,y1])[0]))
 valid=[np.isin(a,H_CODES) if i<2 else (a>=1)&(a<=14) for i,a in enumerate(data)]
 core=lambda a:a[PAD:PAD+N,PAD:PAD+N]
 safe=core(valid[0])&core(valid[1])
 for v in valid[2:]:safe &= core(minimum_filter(v.astype(np.uint8),27,mode='constant',cval=0)).astype(bool)
 assert safe.mean()>=.9
 return data,valid,safe,np.array(w),tr
def masks(sid,safe):
 rng=np.random.default_rng(seed(20261021,sid,'pilot'));pilot=np.zeros((N,N),bool);pw=np.zeros((N,N),float);excluded=np.zeros((N,N),bool);coords=[]
 for by in range(5):
  for bx in range(5):
   good=[(i,j) for i in range(by*8,(by+1)*8) for j in range(bx*8,(bx+1)*8) if safe[i*30:(i+1)*30,j*30:(j+1)*30].any()]
   k=min(2,len(good))
   if not k:continue
   for ix in rng.choice(len(good),k,replace=False):
    i,j=good[int(ix)];r=i*30;c=j*30;pilot[r:r+30,c:c+30]=True;pw[r:r+30,c:c+30]=len(good)/k
    excluded[max(0,r-13):min(N,r+43),max(0,c-13):min(N,c+43)]=True
    coords.append({'row':r,'col':c,'stratum':[by,bx],'eligible':len(good),'chosen':k,'inverse_probability':len(good)/k})
 pilot &= safe;pw*=safe
 return pilot,pw,safe&~excluded,coords
def boundary(a,v):
 b=np.zeros_like(v)
 x=(a[1:]!=a[:-1])&v[1:]&v[:-1];b[1:]|=x;b[:-1]|=x
 x=(a[:,1:]!=a[:,:-1])&v[:,1:]&v[:,:-1];b[:,1:]|=x;b[:,:-1]|=x
 return b
@njit(parallel=True,cache=True)
def surface_kernel(h,w,hb,wb,hd,wd,rr,cc,weights,offsets,pad):
 ns=len(offsets);hist=np.zeros((ns,6,14));edges=np.zeros((ns,4))
 for k in prange(ns):
  dr,dc=offsets[k]
  for z in range(len(rr)):
   r=rr[z]+pad;c=cc[z]+pad;r1=r+dr;c1=c+dc;mass=weights[z]
   hj=h[r,c];wk=w[r1,c1]
   if hj<0 or wk<0:continue
   hist[k,hj,wk]+=mass
   if hb[r,c]:
    edges[k,0]+=mass
    if wd[r1,c1]:edges[k,2]+=mass
   if wb[r1,c1]:
    edges[k,1]+=mass
    if hd[r,c]:edges[k,3]+=mass
 return hist,edges
def extract(s,ds,kind):
 start=time.perf_counter();data,valid,safe,rw,tr=read_site(s,ds);pilot,pw,evalmask,coords=masks(s['id'],safe)
 mask=pilot if kind=='pilot' else safe;rr,cc=np.nonzero(mask);mass=rw[rr]*(pw[rr,cc] if kind=='pilot' else 1)
 result={};hlut=np.full(256,-1,np.int8);hlut[H_CODES]=np.arange(6,dtype=np.int8)
 for t in range(2):
  hi=hlut[data[t]];wi=data[t+2].astype(np.int16)-1;wi[~valid[t+2]]=-1
  hb=boundary(data[t],valid[t]);wb=boundary(data[t+2],valid[t+2]);hd=binary_dilation(hb,structure=CROSS);wd=binary_dilation(wb,structure=CROSS)
  hist,edges=surface_kernel(hi,wi,hb,wb,hd,wd,rr.astype(np.int32),cc.astype(np.int32),mass,V,PAD)
  result['hist'+str(t)]=hist;result['edges'+str(t)]=edges
 result['safe_coverage']=np.array(safe.mean());result['pilot_raw_changes']=np.zeros((7,2))
 for k,case in enumerate(cases(s['id'])):
  d=case['d'];hchange=data[0][rr+PAD,cc+PAD]!=data[1][rr+PAD,cc+PAD]
  wchange=data[2][rr+PAD+d[0,0],cc+PAD+d[0,1]]!=data[3][rr+PAD+d[1,0],cc+PAD+d[1,1]]
  result['pilot_raw_changes'][k]=[np.sum(mass*hchange)/mass.sum(),np.sum(mass*wchange)/mass.sum()]
 path=ROOT/'cache'/kind/(s['id']+'.npz');path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**result)
 metadata={'site':s['id'],'kind':kind,'seconds':time.perf_counter()-start,'safe_pixels':int(safe.sum()),'pilot_pixels':int(pilot.sum()),'evaluation_pixels':int(evalmask.sum()),'pilot_centers':coords,'source_window_sha256':{k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in zip(['H2010','H2020','W2010','W2020'],data)}}
 dump(path.with_suffix('.json'),metadata)
 return metadata
def read_cache(sid,kind):
 with np.load(ROOT/'cache'/kind/(sid+'.npz')) as z:return {k:z[k] for k in z.files}
def class_model(ids):
 rows=[]
 for sid in ids:
  x=read_cache(sid,'full')
  for t in range(2):
   h=x['hist'+str(t)][312];total=h.sum(1);rows.append(np.divide(h,total[:,None],out=np.full_like(h,np.nan),where=total[:,None]>0))
 a=np.array(rows);present=np.isfinite(a[:,:,0]).any(0);p=np.zeros((6,14))
 for j in range(6):
  p[j]=np.nanmean(a[:,j,:],axis=0) if present[j] else np.ones(14)/14
 p+=.001;p/=p.sum(1)[:,None]
 return {'p':p,'present':present}
def standardize(x,informative=True):
 std=float(np.std(x));ok=bool(informative and std>1e-12)
 return (x-x.mean())/std if ok else np.zeros_like(x),ok
def raw_scores(hist,edge,model):
 hp=hist.sum(2);counts=hp.sum(1)
 rec=np.divide(edge[:,2],edge[:,0],out=np.zeros(len(edge)),where=edge[:,0]>0)
 pre=np.divide(edge[:,3],edge[:,1],out=np.zeros(len(edge)),where=edge[:,1]>0)
 den=pre+rec;g=np.divide(2*pre*rec,den,out=np.zeros(len(edge)),where=den>0)
 means=np.divide(np.einsum('kij,ij->ki',hist,np.log(model['p'])),hp,out=np.zeros_like(hp),where=hp>0)
 valid=(hp>0)&np.array(model['present'])[None,:];s=np.divide((means*valid).sum(1),valid.sum(1),out=np.zeros(len(edge)),where=valid.sum(1)>0)
 return g,s,bool((edge[:,:2]>0).any()),bool(valid.any())
def case_surfaces(cache,case,model):
 z=[];oks=[];raw=[]
 for t in range(2):
  d=case['d'][t];ix=(U[:,0]+d[0]+12)*25+(U[:,1]+d[1]+12)
  hist=cache['hist'+str(t)][ix];edges=cache['edges'+str(t)][ix]
  g,s,gok,sok=raw_scores(hist,edges,model);zg,go=standardize(g,gok);zs,so=standardize(s,sok)
  z.append(np.stack([zg,zs]));oks.append([go,so]);raw.append((hist,edges,g,s))
 return np.array(z),np.array(oks),raw
def best(x):return int(np.flatnonzero(x>=x.max()-1e-12)[0])
def solve(z,ok,params):
 out=np.zeros((4,2,2),np.int16)
 for a,feature,gamma in [(1,0,params['g1']),(2,1,params['g2'])]:
  for t in range(2):
   if ok[t,feature]:out[a,t]=U[best(z[t,feature]-gamma*UNORM/12)]
 score=[]
 for t in range(2):
  if ok[t].any():score.append(z[t,ok[t]].mean(0)-params['g3']*UNORM/24)
  else:
   v=np.full(len(U),-np.inf);v[ZERO]=0;score.append(v)
 joint=score[0][:,None]+score[1][None,:]-params['lam']*DIST/12
 winners=np.argwhere(joint>=np.max(joint)-1e-12)
 chosen=min(winners,key=lambda ij:(int(UNORM[ij[0]]+UNORM[ij[1]]),*U[ij[0]],*U[ij[1]]))
 out[3]=[U[chosen[0]],U[chosen[1]]]
 return out
def error(pred,case):return np.sqrt(((pred+case['d'][None])**2).sum(2)).mean(1)
def entropy(p):
 p=p[p>0];return float(-(p*np.log2(p)).sum())
def peak(score):
 if np.std(score)<=1e-12:return [np.nan,np.nan]
 ix=best(score);far=np.max(np.abs(U-U[ix]),axis=1)>=2
 return [float(score[ix]-score[far].max()),float((score>=score.max()-.1*np.std(score)).mean())]
def features(cache,case,ci,model,params):
 z,ok,raw=case_surfaces(cache,case,model);pred=solve(z,ok,params);base=[];extra=[]
 for t in range(2):
  hist,edge,gs,ss=raw[t];h=hist[ZERO];total=h.sum();base += [entropy(h.sum(1)/total),entropy(h.sum(0)/total),float(edge[ZERO,0]/total),float(edge[ZERO,1]/total)]
 base+=[float(cache['safe_coverage'])]
 for t in range(2):base += peak(raw[t][2])+list(pred[1,t] if ok[t,0] else [np.nan,np.nan])
 delta=pred[1,1]-pred[1,0];base+=list(delta)+[float(abs(delta).sum()),float(np.linalg.norm(delta))]
 for t in range(2):extra += peak(raw[t][3])+list(pred[2,t] if ok[t,1] else [np.nan,np.nan])
 for t in range(2):
  hp=raw[t][0][ZERO].sum(1);p=hp/hp.sum();extra.append(float(sum(p[j]*entropy(model['p'][j]) for j in range(6))))
 for t in range(2):
  delta=pred[1,t]-pred[2,t];extra+=list(delta)+[float(abs(delta).sum())]
 extra.append(float(abs(pred[2,1]-pred[2,0]).sum()));extra+=list(cache['pilot_raw_changes'][ci])
 extra += [float(abs(pred[3]-pred[a]).sum()) for a in [1,2]]
 assert len(base)==21 and len(extra)==21
 return np.array(base+extra,float)
def write_tif(p,a,tr,nodata=255):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with rasterio.open(p,'w',driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,dtype='uint8',crs='EPSG:4326',transform=tr,nodata=nodata,compress='deflate',tiled=True) as d:d.write(a,1)
 with rasterio.open(p) as d:assert np.array_equal(d.read(1),a)
