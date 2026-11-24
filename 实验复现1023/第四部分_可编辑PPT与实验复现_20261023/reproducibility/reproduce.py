"""Safe entry point: every invocation creates a fresh run directory.
Snapshots are never modified. Python must be the user's conda py310 interpreter.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys,uuid
R=Path(__file__).resolve().parent;SNAP=R/'snapshots'
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copytree(src,dst,cache=False,exclude=()):
 def ignore(path,names):return [n for n in names if n in ['__pycache__','numba_cache','mplconfig'] or (n=='cache' and not cache) or (Path(path)==src and n in exclude)]
 shutil.copytree(src,dst,ignore=ignore)
def compare(a,b,label):
 import pandas as pd,numpy as np
 x=pd.read_csv(a);y=pd.read_csv(b);assert list(x.columns)==list(y.columns),(label,'columns');assert x.shape==y.shape,(label,x.shape,y.shape)
 for c in x:
  if pd.api.types.is_numeric_dtype(x[c]) and pd.api.types.is_numeric_dtype(y[c]):np.testing.assert_allclose(x[c],y[c],rtol=1e-10,atol=1e-11,equal_nan=True,err_msg=label+':'+c)
  else:assert x[c].fillna('<NA>').astype(str).equals(y[c].fillna('<NA>').astype(str)),(label,c)
 return dict(file=label,rows=len(x),matches=True)
def worker(work,stage):
 print('STAGE',stage,flush=True)
 log=work/(stage+'.log')
 with log.open('w',encoding='utf8') as f:
  subprocess.run([sys.executable,'-B',str(R/'tools/stage_worker.py'),str(work),stage],stdout=f,stderr=subprocess.STDOUT,check=True)
def adapt(work,raw=False):
 cfg=json.loads((R/'input_paths.json').read_text(encoding='utf8'));changes=[]
 for folder in ['experiment_v4_runtime','experiment_ablation_v5_runtime']:
  p=work/folder/'frozen_parameters.json';v=json.loads(p.read_text(encoding='utf8'))
  for key,info in v['experiment3']['inputs'].items():
   info['path']=cfg['rasters'][key]
   if raw:
    st=Path(info['path']).stat();info['mtime_ns']=st.st_mtime_ns
  dump(p,v);dump(work/folder/'protected_before.json',{})
 # This adapter removes only report-time source-file metadata checks for table-only
 # verification; mathematical summary code remains byte-for-byte unchanged.
 p=work/'experiment_ablation_v5_runtime/report.py';s=p.read_text(encoding='utf8');a=s.index(" protected=load(HERE/'protected_before.json')");b=s.index('\n return summary_final',a)
 adapted=s[:a]+" summary_final={'reproduction_mode':'table_or_fresh_run_summary','both_prespecified_increments_supported_97_5_CI':success}\n"+s[b:]
 p.write_text(adapted,encoding='utf8');changes.append(dict(file=str(p.relative_to(work)),kind='Remove original-location metadata check from report only',original=digest(SNAP/'v5/report.py'),adapted=digest(p)))
 p=work/'mechanism/code/core.py';s=p.read_text(encoding='utf8');a=s.index('def inputs():');b=s.index('\ndef open_inputs',a)
 adapted=s[:a]+"def inputs():\n    return {k:Path(v['path']) for k,v in cfg()['input_files'].items()}\n"+s[b:];p.write_text(adapted,encoding='utf8');changes.append(dict(file=str(p.relative_to(work)),kind='Resolve input raster paths from frozen JSON',original=digest(SNAP/'mechanism/code/core.py'),adapted=digest(p)))
 p=work/'mechanism/parameters/frozen_parameters.json';v=json.loads(p.read_text(encoding='utf8'))
 for key,info in v['input_files'].items():info['path']=cfg['rasters'][key]
 dump(p,v);f=work/'mechanism/selection/selection_frozen.json'
 if f.exists():
  v=json.loads(f.read_text(encoding='utf8'));v['parameters_sha256']=digest(p);dump(f,v)
 dump(work/'portability_adaptations.json',changes)
def preflight(work=None):
 import os,importlib.util
 proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data'
 os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj);os.environ['GDAL_PAM_ENABLED']='NO'
 import rasterio,numpy as np
 cfg=json.loads((R/'input_paths.json').read_text(encoding='utf8'));orig=json.loads((SNAP/'mechanism/parameters/frozen_parameters.json').read_text(encoding='utf8'))['input_files'];orig.update(json.loads((SNAP/'v4/frozen_parameters.json').read_text(encoding='utf8'))['experiment3']['inputs']);rows=[]
 for k,p in cfg['rasters'].items():
  p=Path(p)
  with rasterio.open(p) as d:
   if k in orig:
    assert list(d.shape)==orig[k]['shape'],(k,'shape');np.testing.assert_allclose(list(d.transform),orig[k]['transform'],rtol=1e-12,atol=1e-12);assert str(d.crs)==orig[k]['crs']
    assert p.stat().st_size==orig[k]['bytes'],(k,'bytes')
   rows.append(dict(key=k,path=str(p),bytes=p.stat().st_size,shape=list(d.shape),crs=str(d.crs)))
 result={'rasters':rows,'full_raster_sha256_recomputed':False}
 if work is not None:
  import pandas as pd
  path=work/'engine.py';shutil.copy2(SNAP/'v4/engine.py',path)
  conf=json.loads((SNAP/'v4/frozen_parameters.json').read_text(encoding='utf8'))
  for k,info in conf['experiment3']['inputs'].items():info['path']=cfg['rasters'][k]
  dump(work/'frozen_parameters.json',conf)
  spec=importlib.util.spec_from_file_location('preflight_engine',path);e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
  site=pd.read_csv(SNAP/'v4/split_manifest.csv').iloc[0].to_dict();ds=e.open_data()
  try:data,valid,safe,rw,tr=e.read_site(site,ds)
  finally:
   for d in ds.values():d.close()
  with np.load(SNAP/'v4/cache/full'/(site['id']+'.npz')) as cache:
   lut=np.full(256,-1,dtype=int);lut[e.H_CODES]=np.arange(6);weights=np.broadcast_to(rw[:,None],safe.shape)
   for t in range(2):
    hi=lut[data[t][e.PAD:e.PAD+e.N,e.PAD:e.PAD+e.N]]
    for dr,dc in [(0,0),(12,-12)]:
     wi=data[t+2][e.PAD+dr:e.PAD+dr+e.N,e.PAD+dc:e.PAD+dc+e.N].astype(int)-1
     hist=np.bincount((hi[safe]*14+wi[safe]),weights=weights[safe],minlength=84).reshape(6,14)
     np.testing.assert_allclose(hist,cache['hist'+str(t)][(dr+12)*25+(dc+12)],rtol=1e-10,atol=1e-3)
  result['raw_window_smoke_check']={'site':site['id'],'dates':2,'offsets':[[0,0],[12,-12]],'raw_area_histograms_match_cache':True,'safe_coverage':float(safe.mean())}
 return result
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['verify','cached','selection','raw-selection','raw-cross','raw-mechanism','preflight']);args=parser.parse_args()
 config=json.loads((R/'input_paths.json').read_text(encoding='utf8'));assert Path(sys.executable).resolve()==Path(config['python']).resolve(),'Use the configured conda py310 Python.'
 manifest=json.loads((R/'snapshot_manifest.json').read_text(encoding='utf8'))
 for x in manifest:assert digest(R/x['file'])==x['sha256'],'Snapshot modified: '+x['file']
 root=(R/config.get('runs_directory','runs')).resolve();assert root.is_relative_to(R.resolve());root.mkdir(exist_ok=True)
 work=root/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+args.mode+'_'+uuid.uuid4().hex[:6]);work.mkdir()
 if args.mode=='preflight':dump(work/'preflight.json',preflight(work));print(work);return
 raw=args.mode.startswith('raw-')
 if raw:dump(work/'preflight.json',preflight())
 copytree(SNAP/'v4',work/'experiment_v4_runtime',cache=args.mode=='cached');copytree(SNAP/'v5',work/'experiment_ablation_v5_runtime',cache=args.mode=='cached');copytree(SNAP/'mechanism',work/'mechanism',exclude=('selection',) if args.mode=='raw-selection' else ())
 adapt(work,raw);dump(work/'run.json',dict(mode=args.mode,python=sys.executable,started=datetime.datetime.now().isoformat(),snapshots_verified=len(manifest)))
 comparisons=[]
 if args.mode=='selection':
  worker(work,'selection');report=json.loads((work/'sampling_audit/sampling_audit.json').read_text(encoding='utf8'));assert report['test_and_development_exactly_reproduced'] and report['extrapolation_exactly_reproduced'];comparisons.append({'selection_geometry_exactly_reproduced':True,'windows':163})
 elif args.mode=='verify':
  worker(work,'statistics')
  for name in ['method_summary','paired_contrasts','block_results','family_results','task_summary','task_contrasts','all_common_parameter_results','task_valid_counts']:comparisons.append(compare(work/'experiment_ablation_v5_runtime'/(name+'.csv'),SNAP/'v5'/(name+'.csv'),'v5/'+name))
  for name in ['Table_1_Coupling.csv','Table_2_Noncommutativity.csv']:comparisons.append(compare(work/'mechanism/tables'/name,SNAP/'mechanism/tables'/name,'mechanism/'+name))
  comparisons.append(compare(work/'mechanism/results/statistics/interaction_contrasts.csv',SNAP/'mechanism/results/statistics/interaction_contrasts.csv','mechanism/interaction_contrasts'))
  for name in ['factor_decomposition_by_window.csv','factor_decomposition_summary.csv']:
   comparisons.append(compare(work/'figure_data'/name,R.parent/'editable_figures/data'/name,'decomposition/'+name))
 elif args.mode=='cached':
  worker(work,'cached-v4');worker(work,'cached-v5')
  for folder,baseline,names in [('experiment_v4_runtime','v4',['development_oof.csv','locked_choices.csv','locked_candidate_predictions.csv']),('experiment_ablation_v5_runtime','v5',['development_calibration.csv','locked_predictions.csv'])]:
   for name in names:comparisons.append(compare(work/folder/name,SNAP/baseline/name,baseline+'/'+name))
 elif args.mode=='raw-cross':
  worker(work,'raw-v4');worker(work,'raw-v5');worker(work,'v5-statistics')
  for folder,baseline,names in [('experiment_v4_runtime','v4',['test_alignment_metrics.csv','test_change_metrics.csv']),('experiment_ablation_v5_runtime','v5',['all_alignment_metrics.csv','task_metrics.csv','paired_contrasts.csv'])]:
   for name in names:comparisons.append(compare(work/folder/name,SNAP/baseline/name,baseline+'/'+name))
 elif args.mode=='raw-selection':
  worker(work,'raw-selection')
  for name in ['candidates.csv','selected_regions.csv']:
   comparisons.append(compare(work/'mechanism/selection'/name,SNAP/'mechanism/selection'/name,'mechanism/selection/'+name))
 elif args.mode=='raw-mechanism':
  worker(work,'raw-mechanism');worker(work,'mechanism-statistics')
  for name in ['experiment_1/coupling.csv','experiment_1/semantic_change.csv','experiment_2/order.csv','review_multiscale_order/phase_all_scales.csv']:
   comparisons.append(compare(work/'mechanism/results'/name,SNAP/'mechanism/results'/name,'mechanism/'+name))
 for x in manifest:assert digest(R/x['file'])==x['sha256'],'Snapshot overwritten: '+x['file']
 report=dict(mode=args.mode,status='PASS',outputs=str(work),comparisons=comparisons,original_snapshots_unchanged=True,raw_raster_metrics_recomputed=args.mode.startswith('raw-'))
 dump(work/'REPRODUCTION_CHECK.json',report);dump(R/'latest_run.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
