from ablation import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Cm,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

CONTRASTS=[('semantic_given_time','GT','GST'),('time_given_semantic','GS','GST'),('full_vs_geometry','G','GST'),('semantic_without_time','G','GS'),('time_without_semantic','G','GT')]
def intervals(x,key):
 x=np.asarray(x,float);x=x[np.isfinite(x)]
 if not len(x):return {'n_blocks':0,'mean':np.nan,'ci95_low':np.nan,'ci95_high':np.nan,'ci975_low':np.nan,'ci975_high':np.nan}
 rng=np.random.default_rng(seed(20261022,'ablation_v5',key));boot=x[rng.integers(0,len(x),(10000,len(x)))].mean(1)
 q=np.quantile(boot,[.025,.975,.0125,.9875])
 return {'n_blocks':len(x),'mean':float(x.mean()),'median':float(np.median(x)),'ci95_low':float(q[0]),'ci95_high':float(q[1]),'ci975_low':float(q[2]),'ci975_high':float(q[3]),'positive':int((x>1e-12).sum()),'negative':int((x< -1e-12).sum()),'zero':int((abs(x)<=1e-12).sum())}
def summarize():
 a=pd.read_csv(HERE/'all_alignment_metrics.csv');t=pd.read_csv(HERE/'task_metrics.csv');summary=[];contrasts=[];blockrows=[];families=[];tasksums=[];taskcon=[]
 for regime,flag in [('matched_primary','is_primary'),('independently_calibrated','is_calibrated')]:
  q=a[a[flag]].copy();metrics=['E','within1','exact','nominal_modified']
  fam=q.groupby(['dataset','method','block','site','family'])[metrics].mean().reset_index();win=fam.groupby(['dataset','method','block','site'])[metrics].mean().reset_index();block=win.groupby(['dataset','method','block'])[metrics].mean().reset_index();block['regime']=regime;blockrows.append(block)
  ff=fam.groupby(['dataset','method','block','family'])[metrics].mean().groupby(['dataset','method','family']).mean().reset_index();ff['regime']=regime;families.append(ff)
  su=block.groupby(['dataset','method'])[metrics].mean().reset_index();su['regime']=regime;summary.append(su)
  for dataset,grp in block.groupby('dataset'):
   pv=grp.pivot(index='block',columns='method',values='E')
   for label,left,right in CONTRASTS:
    contrasts.append({'dataset':dataset,'regime':regime,'contrast':label,'direction':left+' minus '+right,'metric':'E_pixels',**intervals(pv[left]-pv[right],(dataset,regime,label))})
   interaction=(pv.GT-pv.GST)-(pv.G-pv.GS)
   contrasts.append({'dataset':dataset,'regime':regime,'contrast':'semantic_time_interaction','direction':'(GT-GST)-(G-GS)','metric':'E_pixels',**intervals(interaction,(dataset,regime,'interaction'))})
  qt=t[t[flag]&(t.reference_km2>0)].copy();tf=qt.groupby(['dataset','event','method','block','site','family'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();tw=tf.groupby(['dataset','event','method','block','site'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();tb=tw.groupby(['dataset','event','method','block'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();ts=tb.groupby(['dataset','event','method'])[['F1','IoU','fp_km2','fn_km2']].mean().reset_index();ts['regime']=regime;tasksums.append(ts)
  for (dataset,event),grp in tb.groupby(['dataset','event']):
   pv=grp.pivot(index='block',columns='method',values='F1')
   for label,left,right in CONTRASTS:
    good=pv[[left,right]].dropna();taskcon.append({'dataset':dataset,'regime':regime,'event':event,'contrast':label,'direction':right+' minus '+left,'metric':'F1',**intervals(good[right]-good[left],(dataset,regime,event,label))})
 su=pd.concat(summary);co=pd.DataFrame(contrasts);block=pd.concat(blockrows);fam=pd.concat(families);ts=pd.concat(tasksums);tc=pd.DataFrame(taskcon)
 for name,d in [('method_summary',su),('paired_contrasts',co),('block_results',block),('family_results',fam),('task_summary',ts),('task_contrasts',tc)]:d.to_csv(HERE/(name+'.csv'),index=False,encoding='utf-8-sig')
 # Full shared hyperparameter grid, all cells retained. Non-temporal groups repeated only as comparison entries.
 rows=[]
 for gamma,lam in GRIDS:
  q=a[(a.gamma==gamma)&(((a.method.isin(['GT','GST']))&(a['lambda']==lam))|((a.method.isin(['G','GS']))&(a['lambda']==0)))]
  b=q.groupby(['dataset','method','block','site','family']).E.mean().groupby(['dataset','method','block','site']).mean().groupby(['dataset','method','block']).mean().reset_index()
  for dataset,g in b.groupby('dataset'):
   pv=g.pivot(index='block',columns='method',values='E');r={'dataset':dataset,'gamma':gamma,'lambda':lam}
   r.update({m:float(pv[m].mean()) for m in METHODS});r.update({'semantic_given_time':float((pv.GT-pv.GST).mean()),'time_given_semantic':float((pv.GS-pv.GST).mean())});rows.append(r)
 sens=pd.DataFrame(rows);sens.to_csv(HERE/'all_common_parameter_results.csv',index=False,encoding='utf-8-sig')
 new=co[(co.dataset=='low_SL_extrapolation')&(co.regime=='matched_primary')&co.contrast.isin(['semantic_given_time','time_given_semantic'])]
 success=bool(len(new)==2 and (new.ci975_low>0).all())
 # Coverage of the task subset is common by reference, not by method outcome.
 validcounts=t[(t.is_primary)&(t.reference_km2>0)].groupby(['dataset','event']).agg(n_windows=('site','nunique'),n_blocks=('block','nunique')).reset_index();validcounts.to_csv(HERE/'task_valid_counts.csv',index=False,encoding='utf-8-sig')
 protected=load(HERE/'protected_before.json');changed=[]
 for p0,r in protected.items():
  p=Path(p0)
  if not p.exists():changed.append([p0,'missing']);continue
  st=p.stat()
  if st.st_size!=r['bytes'] or st.st_mtime_ns!=r['mtime_ns']:changed.append([p0,'metadata'])
  if 'sha256' in r and sha(p)!=r['sha256']:changed.append([p0,'sha256'])
 rawchanged=[]
 for k,r in cfg()['experiment3']['inputs'].items():
  st=Path(r['path']).stat()
  if st.st_size!=r['bytes'] or st.st_mtime_ns!=r['mtime_ns']:rawchanged.append(k)
 dump(HERE/'source_preservation.json',{'files':len(protected),'changes':changed,'large_input_state_changes':rawchanged});assert not changed and not rawchanged
 summary_final={'date':'2026-10-22','status':'COMPLETE','old_exploratory_windows':40,'old_blocks':20,'new_extrapolation_windows':63,'new_blocks':14,'primary_regime':'matched gamma0.5 lambda0.25','both_prespecified_increments_supported_97_5_CI':success,'new_primary_contrasts':new.to_dict('records'),'independent_calibration':load(HERE/'calibrated_parameters.json'),'geometric_rows':len(a),'task_rows':len(t),'source_files_unchanged':len(protected),'no_parameter_changes_after_new_results':True}
 dump(HERE/'FINAL_RESULT.json',summary_final)
 return summary_final,su,co,fam,ts,tc,sens,validcounts

def mdtable(d,cols):
 def fmt(x):return f'{x:.6g}' if isinstance(x,(float,np.floating)) and np.isfinite(x) else str(x)
 return '\n'.join(['| '+' | '.join(map(str,cols))+' |','| '+' | '.join(['---']*len(cols))+' |']+['| '+' | '.join(fmt(r[c]) for c in cols)+' |' for _,r in d.iterrows()])
def write_report():
 f,su,co,fam,ts,tc,sens,counts=summarize();new=su[(su.dataset=='low_SL_extrapolation')&(su.regime=='matched_primary')];old=su[(su.dataset=='old40_exploratory')&(su.regime=='matched_primary')]
 primary=co[(co.dataset=='low_SL_extrapolation')&(co.regime=='matched_primary')];secondary=co[(co.dataset=='low_SL_extrapolation')&(co.regime=='independently_calibrated')]
 semantic=primary[primary.contrast=='semantic_given_time'].iloc[0];temporal=primary[primary.contrast=='time_given_semantic'].iloc[0]
 judgment='两项预设增量均得到97.5%区间的正向支持' if f['both_prespecified_increments_supported_97_5_CI'] else '未得到两项预设增量均为正的支持'
 notes=[]
 for label,r in [('语义关系增量',semantic),('跨期约束增量',temporal)]:
  if r.ci975_low>0:meaning='区间支持正向增量'
  elif r.ci975_high<0:meaning='区间支持反向影响'
  else:meaning='区间包含0，方向证据不足'
  notes.append(f'{label}：误差降低{r["mean"]:.6f}像元，97.5%区间[{r.ci975_low:.6f}，{r.ci975_high:.6f}]；{meaning}。')
 text=f'''# v5公平消融与低SL占比外推验证：结果报告

日期：2026-10-22。原始数据、v4输出与旧论文保留。本轮未新增或训练选择器。

## 1. 结论

新外推验证{judgment}。

{notes[0]}

{notes[1]}

主比较固定所有组相同γ=0.5，时间项存在时使用同一λ=0.25。两个预设增量采用97.5%区间，避免从多个未校正比较中只挑有利结果。独立校准和全部共同参数网格作为补充，未用于替换主结论。

## 2. 数据与实验执行

原40窗、20空间分区已被查看，全部新消融结果标为探索性。经用户确认，另纳入63个新窗口、14个新空间分区，均距上一轮100窗中心至少100 km，且不在旧分区内。新窗口来自只按覆盖与组成筛选的更广候选域，实际SL占比约5%—20%，因此称低SL占比外推验证，不称原714候选池的新增同分布验证。

全部63窗的四输入和安全域预检通过，没有根据匹配表现删除或补样。每窗仍为7情景，原40与新63分别汇总，不把721情景当独立空间样本。几何统计共{f['geometric_rows']}行，主参数与独立校准制度的下游指标共{f['task_rows']}行。

## 3. 四组方法与公平控制

| 方法 | 空间边界 | 类别相容关系 | 跨期软约束 |
| --- | --- | --- | --- |
| G | 是 | 否 | 否 |
| GS | 是 | 是 | 否 |
| GT | 是 | 否 | 是 |
| GST | 是 | 是 | 是 |

四组调用同一目标求解器，保持相同输入、169个候选位移、mask、边界容差和并列规则。加入语义时，将有效空间/语义标准化得分平均，避免单纯增加得分项导致位移惩罚相对变弱。位移惩罚统一为γΣ||u_t||₁/24，时间项统一为λ||u_2020−u_2010||₁/12。

主参数沿用v4完整方法的开发校准值，不能视为与完整方法无关的中性最优点。因此，主消融识别的是该共同参数点下的组件增量；参数稳健性必须结合第5节的完整网格和各组独立校准结果判断。

Han—Wang类别相容矩阵固定来自原60个开发窗；不在新外推区重新估计。独立校准也仅使用原60窗，其结果为：{f['independent_calibration']}。四组调参采用同一适用网格，但有时间项的组参数更多，因此不声称调参成本相同。

## 4. 新外推验证的主结果

E为平均两期残余平移的原生像元长度；within1为两期均≤1像元的比例；exact为两期均精确恢复。每窗对三情景族等权，再区内等权、区间等权。

{mdtable(new,['method','E','within1','exact'])}

{mdtable(primary,['contrast','direction','mean','ci975_low','ci975_high','n_blocks','positive','negative','zero'])}

前两行分别为GT−GST（有时间约束时加入语义）及GS−GST（有语义关系时加入时间）。其他对比和交互为次要描述。正值表示加入相应组件后误差降低。

三个情景族的主参数结果如下。G0是不增加额外扰动，G1两期施加相同位移，G2两期施加不同位移；G0不表示原产品已被独立证实没有真实地物错位。

{mdtable(fam[(fam.dataset=='low_SL_extrapolation')&(fam.regime=='matched_primary')],['method','family','E','within1','exact'])}

## 5. 独立校准与共同参数敏感性

{mdtable(su[(su.dataset=='low_SL_extrapolation')&(su.regime=='independently_calibrated')],['method','E','within1','exact'])}

{mdtable(secondary,['contrast','mean','ci95_low','ci95_high'])}

独立校准下，参数本身不同，因此不能单独用这一表归因于某个组件。主归因依赖第4节的匹配参数对比。

尤其需要保留：各组独立校准后，完整GST相对G的误差收益95%区间为[{secondary[secondary.contrast=='full_vs_geometry'].ci95_low.iloc[0]:.6f}，{secondary[secondary.contrast=='full_vs_geometry'].ci95_high.iloc[0]:.6f}]；GS相对G的区间为[{secondary[secondary.contrast=='semantic_without_time'].ci95_low.iloc[0]:.6f}，{secondary[secondary.contrast=='semantic_without_time'].ci95_high.iloc[0]:.6f}]。区间若包含0，就不能宣称整体优越性在不同参数制度下都得到确认。有时间约束背景下的语义增量，应与这些比较分别表述。

{mdtable(sens[sens.dataset=='low_SL_extrapolation'],['gamma','lambda','G','GS','GT','GST','semantic_given_time','time_given_semantic'])}

以上网格完整保留，没有从测试网格挑最优参数。λ=0时G与GT、GS与GST逐项相同，不能把这些重复数值当作新增独立证据。

## 6. 下游变化信息保留

Wang类别13的变化并集、扩张、收缩相对未扰动Wang图评价。下表为新外推集、匹配参数制度；不是地表精度。

{mdtable(ts[(ts.dataset=='low_SL_extrapolation')&(ts.regime=='matched_primary')],['method','event','F1','IoU','fp_km2','fn_km2'])}

{mdtable(tc[(tc.dataset=='low_SL_extrapolation')&(tc.regime=='matched_primary')&tc.contrast.isin(['semantic_given_time','time_given_semantic'])],['event','contrast','mean','ci95_low','ci95_high','n_blocks'])}

{mdtable(counts,['dataset','event','n_windows','n_blocks'])}

零参考事件窗口按统一规则不进入对应F1汇总，仍保留几何误差与假变化面积；没有按方法各自删窗。不能用几何指标改善自动替代下游收益结论。

## 7. 原40窗的探索性结果

{mdtable(old,['method','E','within1','exact'])}

{mdtable(co[(co.dataset=='old40_exploratory')&(co.regime=='matched_primary')],['contrast','mean','ci95_low','ci95_high'])}

该集曾用于v4结果观察，因此这里提供机制探索和实现连续性，不作为新的独立确认样本。匹配参数GST与v4的A3在280个情景中建议位移完全一致，这是代码核对，不是新增性能证据。

## 8. 核查、原文件保护与论文解释

独立核查见qc/independent_result_audit.json：全表位移误差另式重算；λ=0恒等关系；主GST对v4的280项一致性；四个按地理顺序固定选出的新窗口、三个情景、四种方法共48项保存栅格事件核算；新旧中心距离及分区隔离。构造检查在新结果计算前完成。

受保护的{f['source_files_unchanged']}个旧文件状态与相应哈希保持，四份大型原始栅格大小和修改时间保持。未覆盖旧结果，没有根据外推成绩修改参数或主要结论规则。

若只有语义增量得到支持，应将贡献写为“跨产品类别关系为匹配提供额外信息”；若时间增量未得到支持，应报告其适用性有限或无明确增益，不把完整框架各环节一概称为有效。只有在相同参数消融和新空间数据上获得相应证据，才对具体组件作增益判断。

本轮不验证自适应策略选择，不能覆盖v4的零选策增益结论。受控位移恢复仍以名义共址为参照，独立地表位置和专题精度未验证。

## 9. 文件索引

- paired_contrasts.csv：原40与新63分别、匹配参数与独立校准分别的全部效应及区间。
- method_summary.csv／family_results.csv：方法均值与各情景族结果。
- all_common_parameter_results.csv：完整共同γ/λ网格。
- task_metrics.csv／task_summary.csv／task_contrasts.csv：逐情景及汇总的变化保真度。
- locked_predictions.csv／predictions_locked.json：评价前冻结的全部位移建议与哈希。
- raster_manifest.csv／outputs/：主参数及独立校准制度的栅格输出，按相同最终位移无损去重。
- development_calibration.csv／calibrated_parameters.json：原开发集参数选择记录。
- new_sites.csv／preflight.csv／ablation_frozen.json／PROTOCOL.md：新样区、预检和冻结规则。
- source_preservation.json／qc/：旧文件保护与独立检查。
'''
 (HERE/'公平消融实验结果报告.md').write_text(text,encoding='utf-8')
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
 fig,ax=plt.subplots(figsize=(8,4.5));new.set_index('method').E.reindex(METHODS).plot.bar(ax=ax,color=['#777777','#3a86a8','#d28b45','#338b6d']);ax.set(ylabel='Mean residual error (native pixels)',xlabel='',title='New low-SL extrapolation: matched penalties');fig.tight_layout();fig.savefig(HERE/'new_ablation_errors.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4.5));b=pd.read_csv(HERE/'block_results.csv');pv=b[(b.dataset=='low_SL_extrapolation')&(b.regime=='matched_primary')].pivot(index='block',columns='method',values='E');xx=np.arange(len(pv));ax.bar(xx-.18,pv.GT-pv.GST,.36,label='Semantic increment');ax.bar(xx+.18,pv.GS-pv.GST,.36,label='Temporal increment');ax.axhline(0,color='black',lw=.8);ax.set(xlabel='New spatial block',ylabel='Reduction in residual error (pixels)');ax.legend();fig.tight_layout();fig.savefig(HERE/'new_block_increments.png',dpi=180);plt.close(fig)
 doc=Document();sec=doc.sections[0];sec.top_margin=sec.bottom_margin=Cm(1.8);sec.left_margin=sec.right_margin=Cm(1.8)
 norm=doc.styles['Normal'];norm.font.name='Calibri';norm.font.size=Pt(10.5);norm.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体')
 for name in ['Title','Heading 1','Heading 2']:
  doc.styles[name].font.name='Calibri';doc.styles[name].element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'黑体')
 lines=text.splitlines();i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    vals=[x.strip() for x in lines[i].strip().strip('|').split('|')]
    if not all(set(x)<=set('-: ') for x in vals):rows.append(vals)
    i+=1
   tb=doc.add_table(rows=0,cols=len(rows[0]));tb.style='Table Grid'
   for row in rows:
    for cell,val in zip(tb.add_row().cells,row):
     cell.text=val
     for p in cell.paragraphs:
      for r in p.runs:r.font.size=Pt(8)
   repeat=OxmlElement('w:tblHeader');tb.rows[0]._tr.get_or_add_trPr().append(repeat)
   doc.add_paragraph()
   continue
  if line.startswith('#'):
   k=len(line)-len(line.lstrip('#'));doc.add_heading(line[k:].strip(),k-1)
  elif line.startswith('- '):doc.add_paragraph(line[2:],style='List Bullet')
  else:doc.add_paragraph(line)
  i+=1
 doc.add_heading('结果图',1)
 for file in ['new_ablation_errors.png','new_block_increments.png']:doc.add_picture(str(HERE/file),width=Cm(16))
 doc.save(HERE/'公平消融实验结果报告.docx')
 print(json.dumps(f,ensure_ascii=False,indent=2))
if __name__=='__main__':write_report()
