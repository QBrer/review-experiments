from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;B=R.parent
sp=importlib.util.spec_from_file_location('previous_application',B/'esr_section4_20261023_revision5/manuscript_content.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
blocks=m.BLOCKS.copy()
replacement={
'将两套土地覆盖产品用于跨期分析':'跨产品对齐的方案由预期用途确定。本案例需要在Han网格上建立Wang的2010和2020年位置对应，并保留Wang的sand成员变化。输出包括两期校正和对应后的分类，评价同时关注位置恢复与变化位置保留。该任务要求同一地理位置在两期之间保持可追溯关系，也要求真实类别差异在处理后继续保留。因此，原生像元作为匹配与评价的基本支持域，两期分别输出校正，Wang的源类别及事件定义贯穿整个流程。',
'数据诊断决定了可比较范围':'失配诊断将需要协调的表达差异与需要保留的地表状态区分开。两产品存在已知网格索引差异，先依据地理坐标恢复名义对应，再利用共同合法区域及位移缓冲确定固定有效域；类别体系分别为六类和十四类，因此在开发样区估计跨产品语义相容关系，保留各自的类别定义。共同年份为同年产品配对提供时间基准，两期仍保留独立校正变量，以允许位置偏差不同。对应关系与类别状态由此分开处理，跨期类别改变不会因时间约束被强制抹平。',
'图4.7展示了这些条件':'比较层次同样取决于任务。变化位置评价需要保留原生网格上的事件分布，本案例固定原生支持域，并让所有约束组合使用相同安全域。跨产品语义对应以两套原始类别间的相容概率参与评分，不将不同产品的同名类别预设为等价。这使语义差异能够作为对应证据进入计算，同时保留两产品各自的信息含义。',
'空间信息由两产品分类边界':'空间、语义和时间约束共同作用于同一组位置候选。空间边界采用1像元容差下的双向面积加权F1；语义相容关系由60个开发窗的名义共址分布估计，先在各窗各期的Han类内按面积归一，再跨窗／期平均并作0.001平滑，候选得分为有信息Han类内平均对数概率的类间等权平均。两类得分分别在每期[−6,6]²的169个候选面内标准化，使空间形状与类别支持能够共同参与候选排序；时间约束进一步联系两期校正，进入联合目标：',
'为检验该工作流的实际效果':'结果验证沿用任务设定的两个准则：位置恢复检验对应本身，变化保留检验对应能否支持后续跨期分析。对Wang施加已知额外位移，同时保留两产品原有类别差异，构成无新增位移、两期相同位移及两期不同位移三类情景；后两类各包含1、3、6像元行列分量，共7个情景。注入方向从水平、垂直及对角方向固定抽样，真实位移不进入匹配输入。位置恢复误差定义为：',
'参数比较也影响对整体收益的判断':'验证结果能够指向需要复核的具体约束。语义增量支持保留跨产品类别关系参与评分；不同偏移情景中的误差增加则指向时间惩罚的适用性。各方法分别在开发集校准后，GST相对G的平均误差降低0.117像元，95%区间为[−0.007，0.284]（图4.8d），说明完整配置的相对表现还受到参数比较条件影响。共同参数下的组件增量与独立校准下的整体表现分别报告，为后续复核提供依据；评价数据未用于回调本轮参数。完整参数网格及分情景结果见图S1、S2。',
'支持域试验和跨产品试验从两个层面':'尺度与层级的选择决定后续处理还能使用哪些信息，策略组织则决定这些信息怎样进入对应计算。优势选择之前保留细类支持，能够维持上位类别汇总所需的面积依据；跨产品匹配保留源类别及位置索引，使语义相容性可以补充空间边界。坐标准备、关系估计和联合求解按依赖顺序衔接，再由位置误差及任务保真度评价结果，形成了从输入差异到具体处理选择的联系。',
'本研究的定量评价基于':'本研究的定量评价基于源产品变化信息保留和已知额外位移恢复，样本范围分别为机制样区和低SL占比外推区。跨产品案例实际检验了顺序准备与联合求解的组合，验证结果为约束复核提供依据；迭代更新及其自适应反馈收益尚需独立评价。真实地物配准、专题误差及年度合成时段差异需要外部参照检验，对于非刚性形变等输入还需相应扩展候选变换。'
}
out=[];seen=set()
for kind,text in blocks:
 for start,new in replacement.items():
  if kind=='p' and text.startswith(start):text=new;seen.add(start);break
 out.append((kind,text))
 if kind=='p' and text.startswith('比较层次同样取决于任务'):
  out.append(('p','图4.7按任务定义、失配诊断、跨维约束、策略组织和结果验证展示这一应用。策略组织采用顺序式与联合式的组合：先固定坐标、支持域和比较对象，再从开发集建立语义关系及参数，随后联合求解两期位置候选。前序步骤保留后续判定所需的类别与位置信息，跨维得分用于同一对应目标，最终在共同有效域评价校正及其任务后果。'))
assert seen==set(replacement)
source=(R/'manuscript_content.py').read_text(encoding='utf8');a=source.index('BLOCKS=[');b=source.index('\nTABLES=',a)
source=source[:a]+'BLOCKS=[\n'+'\n'.join(repr(x)+',' for x in out)+'\n]\n'+source[b:]
source+="\nCAPTIONS['Fig4_7']='图4.7. 多维对齐整合框架在Han—Wang跨产品任务中的具体实施。五个环节分别给出本案例的判断依据与输出；尺度、时间配对和类别表达共同限定比较层次。流程采用顺序准备与两期联合求解，已知位移及原生事件参照用于结果验证。'\n"
source+="CAPTIONS['Fig4_3']='图4.3. 样区选取与组成。（a）上部为714个混合SL候选中的机制、测试及补充开发样区，实线箭头表示选取次序及位置依赖；下部为1406个宽组成候选经新分区和距离筛选形成的外推集，虚线表示使用此前100窗的位置集合。（b）714窗的条件熵分布及四分位阈值。（c）五组入选窗的SL面积占比，点为窗口，箱体为四分位范围，中线为中位数，须线为1.5倍四分位距内的最远值。'\n"
(R/'manuscript_content.py').write_text(source,encoding='utf8')
audit=[
 dict(basis='Opening framework: task, diagnosis, constraints, organization, validation',implemented='Five-stage application figure and task-driven paragraph sequence',boundary='An application of the framework; no ablation of every conceptual stage'),
 dict(basis='4.1 Cross-dimensional consistency',implemented='Spatial boundary and semantic scores rank the same position candidates; temporal soft constraint links two dates while preserving state changes',boundary='Class compatibility is statistical, not ontology equivalence'),
 dict(basis='4.2 Scale and support',implemented='Native grid and fixed valid domain chosen for location-preservation task; six/fourteen class detail retained',boundary='No newly optimized support scale in the cross-product experiment'),
 dict(basis='4.3 Sequential, iterative, joint and hierarchy awareness',implemented='Sequential preparation plus joint two-date solution; comparison level fixed before matching',boundary='No iterative update executed; cross-product semantic matrix is not a hierarchy mapping'),
 dict(basis='4.4 Fidelity and external validity',implemented='Known-shift recovery and native event F1 with spatially separated evaluation',boundary='No independent ground truth for actual land-cover accuracy'),
 dict(basis='4.4 Feedback',implemented='Failures identify temporal-penalty conditions requiring review',boundary='Held-out results were not used to refit; no closed-loop improvement claimed')]
(R/'framework_alignment_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
print('Read and aligned full framework scope; original theory text remains unchanged.')
