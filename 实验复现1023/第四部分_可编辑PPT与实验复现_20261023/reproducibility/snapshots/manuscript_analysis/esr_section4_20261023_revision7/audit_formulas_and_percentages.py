from pathlib import Path
import importlib.util,hashlib,json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent;B=R.parent;source=B/'实验独立复核_20261021/只读基线副本/code/core.py'
sp=importlib.util.spec_from_file_location('audited_core',source);core=importlib.util.module_from_spec(sp);sp.loader.exec_module(core)
rng=np.random.default_rng(271023)
# Nonuniform random fine-class masses: independently compare the two code paths
# with the mathematical necessary-and-sufficient condition in Eq. (4-3).
mass=rng.gamma(.7,1,(6,20000));q=np.vstack([mass[0],mass[1:5].sum(0),mass[5]])
fine=core.unique_mode(mass[...,None],core.FINE).ravel();coarse=core.unique_mode(q[...,None],[1,2,3]).ravel();mapped=core.LUT[fine]
known=(fine!=255)&(coarse!=255);p=mass/mass.sum(0);qp=np.vstack([p[0],p[1:5].sum(0),p[5]])
j=np.argmax(p,axis=0);upper=np.array([0,1,1,1,1,2])[j]
condition=np.array([all(qp[upper[n],n]>qp[k,n] for k in range(3) if k!=upper[n]) for n in range(len(j))])
assert np.array_equal(condition[known],(coarse==mapped)[known])
example=np.array([0,.15,.15,.15,.15,.40]);qe=np.array([example[0],example[1:5].sum(),example[5]])
assert core.unique_mode(example[:,None,None],core.FINE)[0,0]==3
assert core.unique_mode(qe[:,None,None],[1,2,3])[0,0]==2
assert core.unique_mode(np.array([.5,.5,0])[:,None,None],[1,2,3])[0,0]==255
assert core.unique_mode(np.array([.5,.5-5e-11,5e-11])[:,None,None],[1,2,3])[0,0]==255
assert core.unique_mode(np.zeros((3,1,1)),[1,2,3])[0,0]==255
audit=dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),mapping={1:1,21:2,22:2,23:2,24:2,3:3},equations_4_1_to_4_3='unchanged; consistent with aggregate and unique_mode',random_mass_cases=20000,condition_equivalence_on_jointly_determinate_cases=True,four_subclass_example={'fine_SL_each':.15,'Others':.4,'SD':0,'semantic_first':'SL','spatial_first':'Others'},tie_tolerance=1e-10,empty_and_near_tie_checks_passed=True,no_original_script_run=True)
(R/'formula_operator_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
summary=pd.read_csv(B/'experiment_ablation_v5_runtime/method_summary.csv');rows=[]
for regime,base,method in [('matched_primary','G','GS'),('matched_primary','G','GT'),('matched_primary','G','GST'),('matched_primary','GT','GST'),('matched_primary','GS','GST'),('independently_calibrated','G','GST')]:
 d=summary[(summary.dataset=='low_SL_extrapolation')&(summary.regime==regime)].set_index('method');b=float(d.loc[base,'E']);a=float(d.loc[method,'E']);rows.append(dict(regime=regime,scope='all families',baseline=base,method=method,baseline_mean_E=b,method_mean_E=a,absolute_reduction=b-a,relative_reduction_percent=100*(b-a)/b))
fam=pd.read_csv(B/'experiment_ablation_v5_runtime/family_results.csv');d=fam[(fam.dataset=='low_SL_extrapolation')&(fam.regime=='matched_primary')&(fam.family=='G2')].set_index('method');b=float(d.loc['G','E']);a=float(d.loc['GT','E'])
rows.append(dict(regime='matched_primary',scope='G2 different shifts',baseline='G',method='GT',baseline_mean_E=b,method_mean_E=a,absolute_reduction=b-a,relative_reduction_percent=100*(b-a)/b))
pd.DataFrame(rows).to_csv(R/'figure_data/error_reduction_percentages.csv',index=False,encoding='utf-8-sig')
legend=[(1,'Forest'),(2,'Shrub'),(3,'Meadow'),(4,'Real steppe'),(5,'Dry steppe'),(6,'Desert steppe'),(7,'Wetland'),(8,'Water'),(9,'Cropland'),(10,'Built-up land'),(11,'Barren land'),(12,'Desert'),(13,'Sand'),(14,'Ice')]
pd.DataFrame(legend,columns=['code','name']).to_csv(R/'source_data/Wang_product_legend_verified.csv',index=False,encoding='utf-8-sig')
(R/'legend_verification.json').write_text(json.dumps(dict(source='https://www.nature.com/articles/s41597-025-05648-8.pdf',location='Table 2, PDF page 5',doi='10.1038/s41597-025-05648-8',verified_codes=dict(legend),scope='Final 14-class product; not sample-stage label coding'),ensure_ascii=False,indent=2),encoding='utf8')
print(pd.DataFrame(rows).to_string(index=False));print('Operator audit passed')
