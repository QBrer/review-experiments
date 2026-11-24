from core import *
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
import build_section45 as builder

OUT=ROOT/'results/experiment_3_framework_walkthrough'
def main():
    r=load(OUT/'task_results.json');assert load(OUT/'run_complete.json')['passed']
    source=ROOT/'reports/4.5_正文.md';text=source.read_text(encoding='utf8')
    text=text.replace('三个实验依次检验跨期变化表达对空间支持域和语义粒度的敏感性、语义合并与空间聚合的非交换性，以及任务适配表达的信息保留效果。','前两个实验分别检验跨期变化表达对空间支持域和语义粒度的敏感性，以及语义合并与空间聚合的非交换性；第三部分以实际案例说明五步框架如何从任务要求组织对齐过程。')
    text=text.replace('有效域为四期Han与Wang2020合法类别像元的交集，所有策略在同一有效域上评价。','前两个实验的有效域为四期Han与Wang2020合法类别像元的交集；第三部分的单案例运行示例使用Han2010与Han2020合法类别像元的交集，并单独记录有效域。')
    old=text[text.index('三个实验使用同一批新样区'):text.index('Table 4.2.')]
    new='''前两个实验使用同一批24个新样区，第三部分单独使用B2展示框架运行过程（表4.2）。跨期变化参考直接由原始产品建立，六类与三类任务分别使用各自语义层级的类别变化，F1、IoU和面积均按有效面积计算。优势类别平票保留为未确定状态；非交换率排除不能共同判定的格子并另报覆盖，变化任务则保留完整参考域，将未确定位置上的参考变化计为漏检。前两个实验以样区为统计单位，95%置信区间采用10000次整窗重采样；同窗像元、尺度和时段不作为独立重复。第三部分仅记录任务决策、处理输出及内部一致性检查，不设置竞争方法或显著性检验。样区位置与产品覆盖见图S1。

'''
    text=text.replace(old,new)
    text=text.replace('Table 4.2. Design of the three case experiments.','Table 4.2. Design of two mechanism experiments and a framework walkthrough.')
    text=text.replace('| 任务适配表达 | 统一类别Baseline与任务导向Proposed；面积和变化位置任务 | 任务误差、配对F1差、细化比例与存储成本 |','| 框架运行示例 | B2；2010—2020；SL面积及变化位置任务 | 五步决策记录、任务输出、面积守恒与跨期收支检查 |')
    begin=text.index('### 4.5.4');end=text.index('### 4.5.5')
    subsection=f'''### 4.5.4 A task-oriented framework walkthrough

前两个实验说明，类别层级和空间支持域会改变跨期信息表达，操作顺序也可能改变优势类别。第三部分进一步展示这些认识如何进入具体处理流程。这里采用已核实位置和输入的B2作为运行案例，依次执行图4.1中的任务定义、失配诊断、约束分析、对齐组织和结果验证。B2是已知历史案例，不是用于证明框架优势的独立验证样本。本示例不比较其他框架，也不以高精度或显著差异作为目标。

任务定义首先区分两个用途。面积任务需要给出2010和2020年的SL面积及净变化，可在30×30原始像元支持域内保存类别组成；位置任务需要指出哪些原始像元发生SL扩张或收缩，因此必须保留两期相同位置的SL成员关系。两项任务使用同一1020×1020窗口和同一两期共同有效域，其面积为{r['domain_km2']:.3f} km²。净面积变化不能代替变化位置，也不能反映同时发生的扩张与收缩总量。

失配诊断从输入记录开始。两期Han数据的CRS与像元尺寸一致，但文件原点不同：B2在2020年的起始行、列为52983、78382，在2010年为53102、78382。直接照搬行列会将不同位置进行比较。处理过程根据同一地理窗口恢复对应索引，核验像元中心和分辨率后直接读取，未进行重采样。时间条件明确为2010—2020年产品状态的比较，不把两期类别不同直接当作待消除的失配。语义上将四个SL细类合并到SL，保留SD与Others；这一映射仅在Han体系内部使用，不假设与Wang类别严格等价。本窗两期全部{r['valid_pixels']:,}个原始像元均符合合法编码要求。

约束分析明确各项操作必须保留的信息。四个SL子类应先按有效面积累计，不能仅用其中一个优势细类代表SL总量。类别比例足以恢复完整支持域内的面积，但不能恢复各类在格内的位置；两期比例的差也不能唯一确定格内扩张与收缩的分布。因此，面积任务允许输出34×34个比例单元，而变化位置任务保留1020×1020原始网格上的三类标签。这里不以另设的纯度阈值决定局部细化，也不将两个任务强行压成同一种输出。

对齐组织据此形成两条任务分支（表4.4）。两者共享坐标核验、共同有效域及语义映射；面积分支按WGS84像元面积求和，输出SD、SL、Others三类比例及SL面积；位置分支保留原始像元配对，将非SL→SL记为扩张、SL→非SL记为收缩，其余有效位置记为SL成员关系未变。SD与Others之间的转换不属于该任务定义下的SL变化，但并不意味着所有土地覆盖状态都未变。两分支使用不同的信息保留方式，体现第4.3节讨论的任务要求对处理组织的约束。

Table 4.4. Execution trace of the five-step framework in B2. The checks assess procedural consistency, not comparative superiority.

| 环节 | 本例的判断 | 保存的记录或输出 |
|---|---|---|
| 任务定义 | 分开回答SL面积变化与SL变化位置 | 年份、目标类别、支持域和输出要求 |
| 失配诊断 | 两期源文件存在119行原点偏移；需保持真实跨期状态差异 | 输入元数据、精确窗口、合法类别及共同有效域 |
| 约束分析 | 面积需保留组成；位置需保留同一像元的跨期关系 | 比例表达与原始位置表达的适用边界 |
| 对齐组织 | 共享网格和语义处理，再按任务分支输出 | 30×30类别比例、原始三类图、扩张/收缩图 |
| 结果验证 | 核查网格、语义面积、转移边际及净变化收支 | 检查结果、计算误差和未验证事项 |

执行得到2010年SL面积{r['SL2010_km2']:.3f} km²，2020年为{r['SL2020_km2']:.3f} km²，净变化为{r['net_change_km2']:.3f} km²。位置分支识别出产品表达中的SL扩张{r['expansion_km2']:.3f} km²、收缩{r['contraction_km2']:.3f} km²，两者合计{r['change_union_km2']:.3f} km²（图4.4）。扩张与收缩同时存在，说明仅报告净减少量会遗漏变化的空间分布和总量。上述面积均描述输入分类产品，未通过独立地面资料确认。

结果验证分别检查对应关系、跨维一致性和任务输出。像元网格在数值容差内一致，语义合并前后的SL面积相等；三类转移矩阵的行、列面积分别等于两期类别面积；扩张减去收缩等于两期SL面积之差，数值残差小于10⁻⁶ m²。比例积分与原始类别面积的最大差亦小于10⁻⁶ m²，输出栅格重新读取后与写入数组一致。这些守恒和收支关系用于发现实现错误，不作为额外准确性或框架优越性的证据。本次未发现需要回退修正的内部一致性错误，因此未进行人为反复迭代；若检查失败，记录应指向需复核的窗口、映射或汇总步骤。

![Figure 4.4](../figures/framework_walkthrough/Figure_4_4_Framework_walkthrough.png)

Figure 4.4. Outputs of the task-oriented framework walkthrough in historical B2. Native three-class maps preserve spatial correspondence; factor-30 proportion maps support full-cell area accounting; the directional change map retains native SL expansion and contraction locations. Coordinates are native-grid pixel offsets. The panels illustrate task-specific outputs and consistency checks, not competing methods or external accuracy.

'''
    text=text[:begin]+subsection+text[end:]
    begin=text.index('### 4.5.5')
    text=text[:begin]+'''### 4.5.5 Implications and limits of the case study

前两个实验提供机制性证据：跨期变化表达对空间支持域和语义层级的响应并不独立，较强的SL内部混合也与较大的操作顺序差异相关。第三部分承担不同作用，展示如何将这些约束转换为任务定义、输入检查、信息保留选择和可追溯输出。面积与位置任务采用不同表达，是根据所需信息作出的处理安排，而不是从多个竞争结果中选择表现最好的方法。

运行示例说明了框架如何应用，但没有证明框架具有普遍或相对优势。内部一致性通过不等于源产品正确描述真实地表，保留原始位置也不意味着纠正了原始分类误差。B2是已被研究的历史案例，不能代替跨场景独立验证。框架在此的作用是使决策依据、输出适用范围和剩余不确定性明确可追溯；其比较有效性和外部地表准确性不由本示例推断。

## Supplementary spatial figures

![Figure S1](../figures/additional/Figure_S1_Study_area_products.png)

Figure S1. Product coverage and the frozen High/Low windows used in Experiments1 and2. B2 is shown separately as the historical walkthrough case. Display resampling is not used for numerical calculations.

![Figure S2](../figures/additional/Figure_S3_B2_Order_difference.png)

Figure S2. Semantic-first and spatial-first outputs and their disagreement in B2,2020,factor30. This supplementary mechanism illustration belongs to Experiment2, not a competing-method comparison in the framework walkthrough.
'''
    md=ROOT/'reports/4.5_前两实验保留_第三部分框架运行示例.md';md.write_text(text,encoding='utf8')
    original=source.read_text(encoding='utf8')
    a=original[original.index('### 4.5.2'):original.index('### 4.5.4')]
    b=text[text.index('### 4.5.2'):text.index('### 4.5.4')]
    assert a==b
    builder.MD=md
    doc=Document();style=doc.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(11);style.element.rPr.rFonts.set(qn('w:eastAsia'),'宋体')
    doc.sections[0].left_margin=Inches(.85);doc.sections[0].right_margin=Inches(.85)
    builder.render(doc);standalone=ROOT/'reports/4.5_第三部分框架运行示例版.docx';doc.save(standalone)
    orig=builder.SOURCE;before=sha(orig);src=Document(orig);prefix=[p.text for p in src.paragraphs[:57]];refs=[p.text for p in src.paragraphs[58:]]
    target=next(p for p in src.paragraphs if p.text.strip()=='4.5 实验');target._p.getparent().remove(target._p);anchor=next(p._p for p in src.paragraphs if p.text.strip()=='参考文献')
    builder.render(src,anchor);whole=ROOT/'reports/第四部分_实验1与2保留_实验3运行示例版.docx';src.save(whole)
    check=Document(whole);idx=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献')
    assert [p.text for p in check.paragraphs[:57]]==prefix and [p.text for p in check.paragraphs[idx:]]==refs and sha(orig)==before
    assert len(check.tables)==len(Document(orig).tables)+3
    assert len(check.inline_shapes)==len(Document(orig).inline_shapes)+5
    dump(OUT/'manuscript_verification.json',dict(time=now(),experiments1_2_text_identical=True,original_source_unchanged=True,prior_sections_and_references_preserved=True,inserted_figures=5,inserted_tables=3,outputs=[str(md),str(standalone),str(whole)],scope='Only third experiment converted to walkthrough; introduction,methods overview and conclusion adjusted for coherence'))
    note='''# 本次修订说明

用户明确要求：只将4.5第三个实验改为框架运行示例，前两个实验保留。

- 实验1与实验2正文、数值和主图保持不变，已做文本一致性断言。
- 第三部分为B2实际五步流程，不设置Baseline/Proposed竞争，不计算F1、p值或优越性。
- 重写第三部分并同步调整4.5开头、数据/统计范围、设计表及结论，删除不再适用的主要终点和比较检验表述。
- 使用两期原始Han重新运行；输入检查、任务决策、GeoTIFF输出与守恒验证均保存，不直接复制之前的比较结果。
- 面积分支采用30×30比例；位置分支因任务要求保留native位置。没有再引入90%细化阈值或评分优化。
- 原来所有比较实验、负向结果及旧论文版本完整保留。新示例不被描述为新的比较有效性证据；研究过程的改变不应在发表说明中伪装成从未进行过其他探索。

最新正文：4.5_第三部分框架运行示例版.docx。
完整第四部分：第四部分_实验1与2保留_实验3运行示例版.docx。
实际执行记录位于results/experiment_3_framework_walkthrough。
'''
    (ROOT/'reports/第三部分改为运行示例_修订说明.md').write_text(note,encoding='utf8')
    print('Section revised: experiments1/2 text identical, original manuscript unchanged; five figures, three tables.')
if __name__=='__main__':main()
