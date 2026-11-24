from engine import *
import psutil,joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Cm,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def table_md(d,cols):
 def value(x):
  if isinstance(x,(float,np.floating)):return f'{x:.6g}' if np.isfinite(x) else 'NA'
  return str(x)
 return '\n'.join(['| '+' | '.join(map(str,cols))+' |','| '+' | '.join(['---']*len(cols))+' |']+['| '+' | '.join(value(r[c]) for c in cols)+' |' for _,r in d.iterrows()])
def boost(x,label):
 x=np.array(x,float);x=x[np.isfinite(x)];rng=np.random.default_rng(seed(20261022,label,'bootstrap'))
 b=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
 return {'n_blocks':len(x),'mean':float(x.mean()),'median':float(np.median(x)),'ci_low':float(np.quantile(b,.025)),'ci_high':float(np.quantile(b,.975)),'positive':int((x>0).sum()),'negative':int((x<0).sum()),'zero':int((x==0).sum())}
def summarize():
 a=pd.read_csv(ROOT/'test_alignment_metrics.csv');t=pd.read_csv(ROOT/'test_change_metrics.csv');ch=pd.read_csv(ROOT/'locked_choices.csv')
 joined=[];tasks=[]
 for k in range(4):
  j=a[a.candidate==k].copy();j['method']='A'+str(k);joined.append(j)
  z=t[t.candidate==k].copy();z['method']='A'+str(k);tasks.append(z)
 for name in ['single_best','basic','full']:
  cc=ch[ch.method==name][['site','case_id','chosen']]
  j=a.merge(cc,left_on=['site','case_id','candidate'],right_on=['site','case_id','chosen'],validate='one_to_one');j['method']=name;joined.append(j)
  z=t.merge(cc,left_on=['site','case_id','candidate'],right_on=['site','case_id','chosen'],validate='many_to_one');z['method']=name;tasks.append(z)
 best=a.sort_values(['E','candidate']).groupby(['site','case_id']).head(1);best=best.copy();best['method']='oracle';joined.append(best)
 z=t.merge(best[['site','case_id','candidate']],on=['site','case_id','candidate']);z['method']='oracle';tasks.append(z)
 allm=pd.concat(joined,ignore_index=True);allt=pd.concat(tasks,ignore_index=True)
 minimum=best[['site','case_id','E']].rename(columns={'E':'oracle_E'});allm=allm.merge(minimum,on=['site','case_id']);allm['regret']=allm.E-allm.oracle_E
 allm.to_csv(ROOT/'all_methods_alignment.csv',index=False,encoding='utf-8-sig');allt.to_csv(ROOT/'all_methods_tasks.csv',index=False,encoding='utf-8-sig')
 metrics=['E','E_m','within1','exact','regret'];fam=allm.groupby(['method','block','site','family'])[metrics].mean().reset_index();win=fam.groupby(['method','block','site'])[metrics].mean().reset_index();block=win.groupby(['method','block'])[metrics].mean().reset_index()
 family_summary=fam.groupby(['method','family'])[metrics].mean().reset_index();family_summary.to_csv(ROOT/'family_results.csv',index=False,encoding='utf-8-sig')
 block.to_csv(ROOT/'block_results.csv',index=False,encoding='utf-8-sig');summary=block.groupby('method')[metrics].mean().reset_index()
 g0=allm[allm.family=='G0'].groupby(['method','block']).nominal_modified.mean().groupby('method').mean();summary['G0_modification_rate']=summary.method.map(g0)
 summary.to_csv(ROOT/'method_summary.csv',index=False,encoding='utf-8-sig')
 wide=block.pivot(index='block',columns='method',values='E');contrasts=[]
 for other in ['single_best','basic','A0']:
  contrasts.append({'comparison':other+' minus full','metric':'E_pixels',**boost(wide[other]-wide.full,other)})
 # Primary task F1 excludes reference-empty windows for every method uniformly.
 valid=allt[allt.reference_km2>0];tf=valid.groupby(['method','event','block','site','family'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();tw=tf.groupby(['method','event','block','site'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();tb=tw.groupby(['method','event','block'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();ts=tb.groupby(['method','event'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();ts.to_csv(ROOT/'task_summary.csv',index=False,encoding='utf-8-sig')
 for event in ['change_union','expansion','contraction']:
  q=tb[tb.event==event].pivot(index='block',columns='method',values='F1').dropna(subset=['full','single_best'])
  if len(q):contrasts.append({'comparison':'full minus single_best','metric':event+'_F1',**boost(q.full-q.single_best,event)})
 co=pd.DataFrame(contrasts);co.to_csv(ROOT/'contrasts.csv',index=False,encoding='utf-8-sig');primary=contrasts[0];primary['meets_0_5_practical_criterion']=bool(primary['mean']>=.5 and primary['ci_low']>0)
 counts=ch.groupby(['method','chosen']).size().unstack(fill_value=0);counts.to_csv(ROOT/'strategy_choice_counts.csv',encoding='utf-8-sig')
 # Development CV reporting follows same within-window family weights.
 oof=pd.read_csv(ROOT/'development_oof.csv');oof['family']=oof.case_index.map(lambda i:'G0' if i==0 else 'G1' if i<=3 else 'G2');oof['gain']=oof.E_single-oof.E_chosen
 dev=oof.groupby(['method','fold','site','family']).gain.mean().groupby(['method','fold','site']).mean().reset_index();dev.to_csv(ROOT/'development_oof_window_effects.csv',index=False,encoding='utf-8-sig')
 cost=[]
 for kind in ['pilot','full']:
  for p in (ROOT/'cache'/kind).glob('*.json'):
   r=load(p);cost.append({'site':r['site'],'kind':kind,'seconds':r['seconds'],'cache_bytes':p.with_suffix('.npz').stat().st_size,'safe_pixels':r['safe_pixels'],'pilot_pixels':r['pilot_pixels'],'evaluation_pixels':r['evaluation_pixels']})
 pd.DataFrame(cost).to_csv(ROOT/'costs.csv',index=False,encoding='utf-8-sig')
 manifest=pd.read_csv(ROOT/'prediction_raster_manifest.csv');manifest['bytes']=manifest.file.map(lambda p:(ROOT/p).stat().st_size);sizes=manifest.groupby(['site','case_id','candidate']).bytes.sum().reset_index();sizes.to_csv(ROOT/'output_deployment_bytes.csv',index=False,encoding='utf-8-sig')
 # Source preservation: metadata and hashes of old artifacts, metadata for large inputs.
 before=load(ROOT/'protected_before.json');changes=[]
 for name,r in before.items():
  p=Path(name)
  if not p.exists():changes.append([name,'missing']);continue
  s=p.stat()
  if s.st_size!=r['bytes'] or s.st_mtime_ns!=r['mtime_ns']:changes.append([name,'size_or_mtime'])
  if 'sha256' in r and sha(p)!=r['sha256']:changes.append([name,'SHA256'])
 rawchanged=[]
 for k,r in cfg()['experiment3']['inputs'].items():
  st=Path(r['path']).stat()
  if st.st_size!=r['bytes'] or st.st_mtime_ns!=r['mtime_ns']:rawchanged.append(k)
 preservation={'protected_file_count':len(before),'changes':changes,'raw_input_state_changes':rawchanged};dump(ROOT/'source_preservation.json',preservation)
 assert not changes and not rawchanged
 # Frozen boundaries and split identity.
 b=joblib.load(ROOT/'models/final/bundle.joblib');sites=pd.read_csv(ROOT/'split_manifest.csv');assert not set(b['train_ids'])&set(sites[sites.phase=='test'].id)
 assert sha(ROOT/'models/final/bundle.joblib')==load(ROOT/'models_frozen.json')['model_sha256']
 assert sha(ROOT/'locked_choices.csv')==load(ROOT/'choices_frozen.json')['sha256']
 assert sha(ROOT/'locked_candidate_predictions.csv')==load(ROOT/'predictions_frozen.json')['sha256']
 report={'primary':primary,'single_best_candidate':b['single'],'final_candidate_parameters':b['params'],'test_windows':40,'test_blocks':20,'scenarios':280,'candidate_predictions':1120,'task_rows':3360,'all_choices_frozen_before_test_full_matching':True,'positive_reference_change_windows':int(t[(t.event=='change_union')&(t.reference_km2>0)].site.nunique()),'unique_output_tifs':len(manifest.file.unique()),'protected_files_unchanged':len(before),'data_issues_excluded':[],'no_test_parameter_retuning':True}
 dump(ROOT/'FINAL_RESULT.json',report)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
 fig,ax=plt.subplots(figsize=(9,4.5));x=wide.single_best-wide.full;ax.bar(np.arange(len(x)),x,color=np.where(x>=0,'#2b8c7d','#c84b4b'));ax.axhline(0,color='black',lw=.8);ax.axhline(.5,color='gray',ls='--',label='Planning threshold: 0.5 pixels');ax.set(xlabel='Spatial test block',ylabel='Single-best error minus selector error (pixels)',title='Held-out cross-product alignment: paired block effects');ax.legend();fig.tight_layout();fig.savefig(ROOT/'paired_block_effects.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4.5));pivot=family_summary.pivot(index='family',columns='method',values='E');pivot[['A0','single_best','basic','full','oracle']].plot.bar(ax=ax);ax.set(ylabel='Mean residual shift (native pixels)',title='Results by predeclared perturbation family');fig.tight_layout();fig.savefig(ROOT/'scenario_results.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,4));counts.reindex(['single_best','basic','full']).plot.bar(stacked=True,ax=ax);ax.set(xlabel='Selection method',ylabel='Test scenarios',title='Frozen strategy choices');fig.tight_layout();fig.savefig(ROOT/'strategy_choices.png',dpi=180);plt.close(fig)
 # Existing mechanism experiments: summarize rather than rerun/relabel.
 old=ROOT.parent/'实验独立复核_20261021/只读基线副本/results';c=pd.read_csv(old/'experiment_1/coupling.csv');c=c[c.group!='B2'];c['reference_fraction']=c.reference_km2/c.domain_km2
 c.groupby(['group','start_year','semantic','scale'])[['F1','IoU','reference_fraction','fp_km2','fn_km2','coverage']].mean().reset_index().to_csv(ROOT/'experiment1_existing_summary.csv',index=False,encoding='utf-8-sig')
 order=pd.read_csv(old/'experiment_2/order.csv');order=order[order.group!='B2'];order.groupby(['group','scale'])[['R_NC_count','R_NC_area','coverage','affected_km2']].mean().reset_index().to_csv(ROOT/'experiment2_existing_summary.csv',index=False,encoding='utf-8-sig')
 return report,summary,ts,co,family_summary,counts,pd.DataFrame(cost)

def report_files():
 report,summary,task,co,family,counts,cost=summarize();pr=report['primary'];passed=pr['meets_0_5_practical_criterion']
 outcome='达到预设主要成功标准' if passed else '未达到预设主要成功标准'
 figdir=ROOT
 text=f'''# v4跨产品对齐实验：执行与结果报告

日期：2026-10-22。实验已完成，原始数据、既有实验和论文未覆盖。

## 1. 主要判断

本次{outcome}。框架相对于开发阶段最佳固定候选A{report['single_best_candidate']}的平均残余位移误差降低为{pr['mean']:.6f}个原生像元，95%空间分区bootstrap区间为[{pr['ci_low']:.6f}，{pr['ci_high']:.6f}]。预设标准是点估计至少降低0.5像元且区间下限大于0。所有正值、负值和零值结果均保留，测试后没有改变参数、候选或主指标。

实验使用60个开发窗、40个新测试窗（20个空间分区），每窗7种预定情景，测试共280例；四个候选产生1120项两期对齐结果、3360项下游事件指标。

## 2. 实际实施

Han2010/2020与Wang2010/2020均参与计算。先恢复已知网格原点偏移；受控部分只对Wang像元内容施加隐藏的额外整数位移。保留两产品的实际类别差异，没有把Wang当作Han真值，也没有将类别一致性直接当作空间正确性。

候选为A0保持元数据对应、A1分期边界匹配、A2分期类别相容性匹配、A3两期联合匹配。开发阶段最终参数为{report['final_candidate_parameters']}。类别相容矩阵只由开发数据估计，原始类别标签不改写。

完整选择器和基础选择器采用深度2、每叶至少56行的相同模型容量；每窗最多7行，因此每叶至少来自8窗，已逐叶检查。5折空间开发验证中，每折完整重新估计类别关系、候选参数、缺失处理、最佳固定及选择器；训练与验证保持100km中心距离缓冲。

测试诊断→策略选择→候选完整输出→开放真值评价分别保存哈希和时间。选择模块仅读取诊断特征和冻结模型。未扰动原图与注入位移用于评估器，不输入选择模块。

## 3. 全部方法表现

E为两期残余位移欧氏长度的平均值，单位为原生像元坐标；E_m另按WGS84换算。within1表示两期均≤1像元，exact表示两期均精确恢复，regret为相对逐例最优候选的额外误差。先在各情景族内平均，再对三族等权，窗口内汇总后对空间分区等权。

{table_md(summary,['method','E','E_m','within1','exact','regret','G0_modification_rate'])}

oracle按位移误差选择候选，是该指标的事后下限参照，不能部署；其下游F1不是按F1另行择优的上限。G0_modification_rate为无新增扰动时相对名义位置发生修改的比例；原产品可能存在未知地物错位，因此不将这一比例直接解释为真实误改率。

## 4. 配对效应与条件依赖

{table_md(co,['comparison','metric','n_blocks','mean','ci_low','ci_high','positive','negative','zero'])}

位移效应为对照误差减完整选择器误差；F1效应为完整选择器减最佳固定。主要检验只针对预定的位移误差；其他结果是预定次要分析，不替换主结论。CI使用20个完整空间分区、10000次重采样；同窗的七个情景不当作七个独立样本。

当选择器与固定策略在全部测试例使用同一算法时，配对差和重采样区间均为0。这是本次相同输出的描述，不是证明两个策略在任意数据上总体等效。

{table_md(family[family.method.isin(['A0','single_best','basic','full','oracle'])],['method','family','E','within1','exact'])}

## 5. 下游变化信息保留

目标是Wang自身类别13（sand）的2010—2020成员变化，参考为未增加位移的Wang原生事件图。它不等同于Han四个SL细类的并集，也不是独立地表真值。主任务评价排除诊断读取范围及缓冲；各方法采用同一安全有效域。参考有变化的窗口共{report['positive_reference_change_windows']}个；无参考变化时统一不进入F1汇总，仍保留位移与误报记录。

{table_md(task[task.method.isin(['A0','single_best','basic','full','oracle'])],['method','event','F1','IoU','fp_km2','fn_km2'])}

## 6. 选择、自然应用与成本

{table_md(counts.reset_index(),['method']+list(counts.columns))}

完整选择器在280个测试情景中实际使用{int((counts.loc['full']>0).sum())}种候选，具体分布见上表。决策记录包含预测的四个误差、叶节点和被选策略。若始终选择开发最佳固定候选，其表现与该固定策略完全相同，不能称为已获得自适应收益。

本测试集上，最佳固定候选到事后oracle的平均误差间距为{float(summary.loc[summary.method=='single_best','E'].iloc[0]-summary.loc[summary.method=='oracle','E'].iloc[0]):.6f}像元。它小于预定0.5像元阈值时，表示本候选池在这些测试情景中即使每次都选到最优，也无法达到预定实际收益幅度。这一结果在测试后才能确认，不能事后下调阈值来宣称成功。

自然应用为G0。其所有候选的两期建议平移已保存，natural_pair_relations.csv保留各窗各候选六类×十四类的面积关系；利用locked_choices.csv中的G0实际选择可定位对应输出。原始类别不重标，原始文件不覆盖。自然场景没有独立真实位移，结果按建议对应和残余差异解释。

输出GeoTIFF按同窗、时期与最终像元偏移去重，共保存{report['unique_output_tifs']}幅分类图，并用prediction_raster_manifest.csv无损指向1120项候选的两期输出。去重是保存优化，单策略输出字节按其两份文件计算，不把共享压缩量当作算法收益。

诊断/全域缓存提取实测总耗时分别为{cost[cost.kind=='pilot'].seconds.sum():.1f}/{cost[cost.kind=='full'].seconds.sum():.1f}秒。运行采用六线程Numba加速，所有整数偏移充分统计被复用。各阶段实际峰值内存和耗时见stages/；该共享后端计时不能直接解释为某个候选的独立部署耗时。模型、矩阵、诊断和输出成本分别保存，不声称相同计算预算。

## 7. 核查与局限

构造检查覆盖已知位移恢复、独立逐位置直方图、双向边界F1、无信息回退、诊断与评价分离、抽样权重、叶节点窗口数与预测前冻结。A1的1像元边界容差可能形成满分平台，既定最小位移并列规则允许非零残余；未为提高精确率调整该规则。

结果另经独立核查：1120项几何误差逐项重算一致；固定地理顺序选出的4窗、每窗3个情景和4个候选，共48项保存栅格变化结果，以逐行面积计数独立重算，F1差小于10⁻¹²、混淆面积差小于10⁻⁸ km²。记录见qc/independent_result_audit.json。

源数据检查：{report['protected_files_unchanged']}个既有文件的大小、修改时间及相应哈希未变，四份大型源栅格状态未变。未对完整大型栅格重新全盘计算SHA256；实际读取的窗口另有哈希。

结论限于规定的整数平移、既有混合SL候选池及本候选算法。恢复的是新增扰动前的名义对应；原产品本身的分类与物理配准误差仍未通过独立真值核实。相同区域的多情景不提供额外空间样本量。

## 8. 前两个实验与论文处理

实验1/2不重选样、不改旧数值。已将原结果中的参考变化面积占比、FP/FN、覆盖率及非交换率两种口径整理为experiment1_existing_summary.csv和experiment2_existing_summary.csv。

4.5.4应据本报告实际结论编写：主要标准未达到时不得写成框架已改善策略选择；达到时也须限定候选池、扰动与参照性质。旧面积守恒、回读一致和直接差分一致保留在QC，不作为新增性能证据。

## 9. 文件导航

- FINAL_RESULT.json：主要判断及冻结信息。
- contrasts.csv／method_summary.csv／family_results.csv：主次效应、全部方法与情景族。
- locked_choices.csv：先于测试评价保存的实际选择和预测误差。
- locked_candidate_predictions.csv：全部候选建议变换。
- test_alignment_metrics.csv／test_change_metrics.csv：全部逐条件结果。
- prediction_raster_manifest.csv／outputs/：可重建所有候选的分类输出及评价mask。
- development_oof.csv／models/：开发交叉验证、最终矩阵、候选参数及选择树。
- source_preservation.json／qc/：原文件未覆盖检查与实现核验。
- costs.csv／output_deployment_bytes.csv／stages/：实际提取、保存与阶段资源记录。
'''
 (ROOT/'实验执行结果报告.md').write_text(text,encoding='utf8')
 d=Document();sec=d.sections[0];sec.top_margin=sec.bottom_margin=Cm(1.8);sec.left_margin=sec.right_margin=Cm(1.8)
 normal=d.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10.5);normal.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体')
 for name in ['Title','Heading 1','Heading 2']:
  d.styles[name].font.name='Calibri';d.styles[name].element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'黑体')
 lines=text.splitlines();i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|'):
   rr=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    vals=[x.strip() for x in lines[i].strip().strip('|').split('|')]
    if not all(set(x)<=set('-: ') for x in vals):rr.append(vals)
    i+=1
   tab=d.add_table(rows=0,cols=len(rr[0]));tab.style='Table Grid'
   for row in rr:
    for cell,val in zip(tab.add_row().cells,row):
     cell.text=val
     for p in cell.paragraphs:
      for run in p.runs:run.font.size=Pt(8)
   head=OxmlElement('w:tblHeader');tab.rows[0]._tr.get_or_add_trPr().append(head);continue
  if line.startswith('#'):
   count=len(line)-len(line.lstrip('#'));d.add_heading(line[count:].strip(),count-1)
  elif line.startswith('- '):d.add_paragraph(line[2:],style='List Bullet')
  else:d.add_paragraph(line)
  i+=1
 d.add_heading('结果图',1)
 for name in ['paired_block_effects.png','scenario_results.png','strategy_choices.png']:d.add_picture(str(ROOT/name),width=Cm(16))
 d.save(ROOT/'实验执行结果报告.docx')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':report_files()
