from pathlib import Path
import sys,os,importlib,shutil,json
W=Path(sys.argv[1]).resolve();STAGE=sys.argv[2]
os.environ['MPLBACKEND']='Agg';os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
os.environ['MPLCONFIGDIR']=str(W/'mplconfig')
def load_from(path,name):
 sys.path.insert(0,str(path));return importlib.import_module(name)
def mechanism_stats():
 path=W/'mechanism/code';r=load_from(path,'report_results');r.main()
def v5_stats():
 path=W/'experiment_ablation_v5_runtime';r=load_from(path,'report');r.summarize()
if STAGE=='selection':
 src=Path(__file__).resolve().parents[1]/'snapshots/manuscript_analysis/audit_sampling.py'
 s=src.read_text(encoding='utf8').replace("R=Path(__file__).resolve().parent;B=R.parent;OUT=R/'sampling_audit'","R=Path(W);B=R;OUT=R/'sampling_audit'")
 s=s.replace("old=B/'实验独立复核_20261021/只读基线副本'","old=B/'mechanism'")
 exec(compile(s,str(src),'exec'),{'__file__':str(src),'__name__':'__main__','W':str(W)})
elif STAGE=='statistics':
 mechanism_stats()
 src=Path(__file__).resolve().parents[1]/'snapshots/manuscript_analysis/esr_section4_20261023/decompose_response.py'
 s=src.read_text(encoding='utf8').replace('R=Path(__file__).resolve().parent;B=R.parent','R=Path(W);B=R')
 s=s.replace("B/'实验独立复核_20261021/只读基线副本/results/experiment_1/coupling.csv'","B/'mechanism/results/experiment_1/coupling.csv'")
 exec(compile(s,str(src),'exec'),{'__file__':str(src),'__name__':'__main__','W':str(W)})
 # Run v5 in a fresh interpreter to avoid colliding legacy module names.
 import subprocess
 subprocess.run([sys.executable,'-B',__file__,str(W),'v5-statistics'],check=True)
elif STAGE=='mechanism-statistics':mechanism_stats()
elif STAGE=='v5-statistics':v5_stats()
elif STAGE in ['cached-v4','raw-v4']:
 path=W/'experiment_v4_runtime';r=load_from(path,'run')
 if STAGE=='raw-v4':
  r.unit_checks();r.extract_stage('development','pilot');r.extract_stage('development','full')
 r.train()
 if STAGE=='raw-v4':r.extract_stage('test','pilot')
 r.test_features();r.choose()
 if STAGE=='raw-v4':r.extract_stage('test','full')
 r.predictions()
 if STAGE=='raw-v4':r.evaluate()
elif STAGE in ['cached-v5','raw-v5']:
 path=W/'experiment_ablation_v5_runtime';r=load_from(path,'ablation');import joblib
 # The relation model is re-estimated by v4 from the same development data.
 bundle=joblib.load(W/'experiment_v4_runtime/models/final/bundle.joblib');r.dump(path/'class_model.json',bundle['class']);r.check();r.calibrate()
 if STAGE=='raw-v5':r.extract_new()
 r.predictions()
 if STAGE=='raw-v5':r.evaluate()
elif STAGE=='raw-selection':
 path=W/'mechanism/code';r=load_from(path,'select_regions');r.main()
elif STAGE=='raw-mechanism':
 path=W/'mechanism/code';r=load_from(path,'experiments');r.run()
 q=importlib.import_module('review_multiscale_order_maps');q.main()
else:raise ValueError(STAGE)
print('STAGE COMPLETE',STAGE,flush=True)
