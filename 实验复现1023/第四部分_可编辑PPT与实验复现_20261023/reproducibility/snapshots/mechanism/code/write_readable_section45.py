from core import *
import pandas as pd
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
import build_section45 as builder

OUT=ROOT/'results/region_walkthrough_24'
def main():
    assert load(OUT/'complete.json')['all_checks_passed']
    d=pd.read_csv(OUT/'task_results_24.csv').set_index('display_id');h=d.loc['H01'];l=d.loc['L01']
    md=ROOT/'reports/4.5_定稿修订_24样区与框架示例.md'
    text=f'''## 4.5 Case analysis of multidimensional alignment and task-oriented organization

本节以蒙古高原土地覆盖数据为例，分析时间、空间和语义条件如何影响数据对应，并展示任务要求如何进入对齐流程。前两个实验分别考察跨期变化表达的耦合效应与操作非交换性，第三部分按照图4.1的五步流程组织面积统计和变化位置识别。对齐最终形成具有共同空间参照、明确时相和一致类别含义的数据表达，供后续任务直接使用。

### 4.5.1 Data, study regions and alignment outputs

实验采用Han等[135]的蒙古高原沙漠与沙地分类数据，使用2000、2010、2015和2020年四个时相。其原始分类包含沙漠（SD）、四个沙地细类和其他地类（Others），四个沙地细类可汇总为沙地上位类（SL）。Wang等[134]的土地覆盖数据提供区域背景，并与Han数据共同限定有效覆盖范围。研究产品及样区分布见图4.2。

![Figure 4.2](../figures/region_atlas_24/Figure_4_2_Study_regions.png)

Figure 4.2. Study products and the24 experimental windows. Panels show Wang2020 land cover and Han2020 sandy-desert/sandy-land classes. H01–H12 and L01–L12 identify the high- and low-sensitivity windows, respectively; rectangles indicate their geographic footprints.

依据SL内部细类的混合程度，将研究区中的候选窗口分为高敏感区域（High）和低敏感区域（Low），分别抽取12个样区。每个窗口包含1200×1200个原始像元，共同有效覆盖比例不低于95%，SL有效面积占比为20%—80%，Others不少于10%。敏感性指标采用SL内部条件熵H_SL=−Σuᵢlog₂uᵢ，其中uᵢ为第i个SL细类占全部SL有效面积的比例。714个合格候选窗口的下、上四分位数分别为0.680559和1.144047 bit，低于或等于下四分位数的窗口进入Low候选池，高于或等于上四分位数的窗口进入High候选池。随后采用固定随机起点与空间最大最小距离规则抽取两组样区，实际最小中心间距为243 km。这里的敏感性特指语义层级合并的潜在敏感性，分组在计算操作分歧之前确定。完整候选记录、筛选条件和样区索引随复现材料保存。

输入处理以共同地理范围和像元中心为参照，核验各年份的CRS、网格原点和分辨率，恢复同一位置在各源栅格中的行列索引。有效域取四期Han与Wang2020合法类别像元的交集。各项计算按WGS84椭球像元面积加权；3×3、10×10和30×30表示空间支持域每边的原始像元数。所有年份和尺度均保留相同窗口边界。

本例的对齐产物由三个层次组成：首先是统一空间索引和SD/SL/Others语义表达的多时相分类图；其次是在不同支持域上的优势类别图和类别比例图；最后是由这些对应关系计算的SL面积表、跨期转移及扩张/收缩位置图。分类图回答“某位置属于什么类别”，比例图回答“一个支持域内各类占多少”，变化图回答“哪些位置发生了目标类别转移”。这些输出是对齐后的任务数据及其派生结果，本例不进行多源像元值融合。

表4.2列出三部分的安排。前两个实验以24个样区为统计单位，报告同窗配对差和10000次整窗重采样的95%置信区间。变化F1、IoU及面积指标使用有效面积权重；平票记为未确定并单独报告覆盖。第三部分运行同一批样区的任务流程，选取两组按抽取顺序编号的H01、L01展示输出。

Table 4.2. Experimental structure and task-oriented outputs.

| 内容 | 条件设置 | 主要输出 |
|---|---|---|
| 跨维耦合 | 3个时段×3个支持域×2个语义层级 | 变化表达损失及其随维度设置的变化 |
| 操作非交换性 | High/Low各12窗；2020年；3个支持域 | 路径分歧率、类别转移与受影响面积 |
| 框架运行示例 | 2010—2020；面积统计与变化位置识别 | 五步处理记录、类别比例、面积表和扩张/收缩图 |

### 4.5.2 Coupled effects on temporal-change representation

第一个实验固定2020年为终点，比较2015—2020、2010—2020和2000—2020三个时段，在每个时段设置三个空间支持域和六细类、三上位类两种语义表达，共18个条件。各条件以对应语义层级的原始变化图为参照，从而区分语义合并带来的事件定义变化与空间聚合造成的额外信息损失。

空间支持域扩大增加了变化位置损失，其增幅随语义层级和时段而改变（图4.3）。High组2010—2020年的六类表达中，平均1−F1从3×3时的0.207增至30×30时的0.363；三类表达则从0.284增至0.509。以同窗F1的“30×30减3×3”衡量尺度效应，再比较三类与六类的尺度效应，平均差为−0.0686，95%置信区间为[−0.1007，−0.0383]。Low组2015—2020年的对应差值为0.0024，区间为[−0.0068，0.0115]，表现出较弱的语义层级差异。

时间条件同样影响尺度响应。High组三类表达中，2000—2020年与2015—2020年的尺度效应之差为0.0451，95%置信区间为[0.0189，0.0707]。这些结果表明，空间概化对变化表达的影响需要结合比较时期和类别粒度解释。不同层级包含的变化事件、不同时间段的实际变化过程均参与这一关系。

![Figure 4.3](../figures/Figure_1_Coupling.png)

Figure 4.3. Change-location information loss under different temporal intervals, spatial supports and semantic levels. Values are window means of1−F1. Each semantic level is evaluated against its corresponding native-grid change reference.

### 4.5.3 Operational non-commutativity under semantic mixing

第二个实验比较2020年数据中的两条路径：先将SL细类合并后选择空间单元的优势类别，以及先选择细类优势后映射到上位类。非交换率定义为不同类别输出的格子数除以共同可判定格子数，并另行保留面积加权结果。

High组在三个支持域上的平均非交换率均高于Low组（表4.3；图4.4）。从3×3扩大至30×30，High组由0.777%增至4.843%，Low组由0.191%增至0.948%。两组尺度增幅之差为3.309个百分点，95%置信区间为[1.975，4.736]个百分点。SL内部多个细类共存时，合并会累计属于同一上位类别的面积，改变原有细类的优势排序；空间支持域扩大后，这种组成结构更可能影响输出类别。

Table 4.3. Mean cell-count non-commutativity rates across the24 windows.

| 区域类型 | 样区数 | 3×3 | 10×10 | 30×30 |
|---|---:|---:|---:|---:|
| Low | 12 | 0.191% | 0.547% | 0.948% |
| High | 12 | 0.777% | 2.636% | 4.843% |

30×30条件下进一步设置九种网格相位，在共同内部范围评价聚合起点的影响（图4.4b）。不同窗口的相位响应存在差异，表明类别组成与聚合边界共同决定顺序分歧。图4.4c同时展示选区使用的SL条件熵与随后计算的非交换率，说明组成指标与实际操作后果之间的联系。

![Figure 4.4](../figures/region_atlas_24/Figure_4_4_Noncommutativity_24.png)

Figure 4.4. Non-commutativity in high- and low-sensitivity regions. Left: window rates and group means across supports. Middle: within-window ranges across nine grid phases at factor30. Right: within-SL entropy and the observed factor-30 rate.

不同支持域上的类别图进一步展示了聚合改变空间表达的过程（图4.5）。四列使用相同区域与三类语义，原始图中的细碎斑块和狭窄边界在较大支持域上被优势类别替代。该图采用各组首个入选样区，完整24窗的2010、2020年对应图见附带多尺度图集，每窗均包含原始、3×3、10×10和30×30四种表达。

![Figure 4.5](../figures/region_atlas_24/Figure_4_5_Scale_examples.png)

Figure 4.5. Native and aggregated three-class maps of H01 and L01 in2020. All panels preserve the same geographic extent. Coarse labels are selected by valid-area dominance after semantic merging. Native-grid coordinates are used consistently across supports.

### 4.5.4 A task-oriented framework walkthrough

第三部分将上述跨维关系落实为图4.1的五步流程。任务是统计2010和2020年的SL面积，并识别两期之间SL扩张与收缩的位置。框架对24个样区执行相同处理，H01和L01用于展示任务输出（图4.6）。

任务定义首先明确面积与位置两种信息需求。面积统计关注各类在支持域内的组成，变化位置识别关注同一位置的跨期成员关系。因此，对齐输出既保留统一的三类多时相分类，也分别生成适合面积统计的比例图和适合位置分析的变化图。

失配诊断检查空间索引、时间关系和类别层级。两期Han产品的网格原点存在119行差异，需要根据地理坐标恢复对应窗口；确认像元中心一致后直接读取，不进行重采样。时间上比较2010与2020年的状态，保留实际类别转移；语义上将四个沙地细类合并为SL，形成两期一致的SD、SL、Others表达。共同有效域贯穿后续面积与位置计算。

约束分析确定信息保留方式：SL面积必须累计所有所属细类的贡献；完整支持域的类别比例可以恢复面积总量，但不能确定格内变化位置。由此，面积分支采用30×30像元支持域，输出40×40个三类比例单元；位置分支保持1200×1200原始网格的两期对应，并编码SL扩张、收缩和成员关系未变的位置。

对齐组织将共享处理与任务处理分开。两分支共享窗口恢复、有效域建立和语义映射，随后分别进行类别面积汇总和跨期位置比较。每一步保存输入索引、映射规则及输出，使面积表中的数值能够追溯到比例单元，使变化图中的位置能够追溯到两期原始分类（表4.4）。

Table 4.4. Five-step workflow and the resulting aligned data products.

| 环节 | 处理内容 | 对齐产物 |
|---|---|---|
| 任务定义 | 明确SL面积、净变化和扩张/收缩位置 | 任务对象、时期与输出要求 |
| 失配诊断 | 核验网格原点、像元对应、有效类别与时间关系 | 窗口索引、有效mask、类别映射 |
| 约束分析 | 区分组成保留与位置保留 | 支持域及任务表达规则 |
| 对齐组织 | 共享预处理后分别汇总面积和识别转移 | 多时相分类图、比例图、变化图与面积表 |
| 结果验证 | 检查语义面积、转移收支和输出回读 | 一致性记录及可追溯任务结果 |

H01的SL面积由2010年的{h.SL2010_km2:.3f} km²变为2020年的{h.SL2020_km2:.3f} km²，其中扩张{h.expansion_km2:.3f} km²、收缩{h.contraction_km2:.3f} km²，净变化为{h.net_change_km2:.3f} km²。L01对应的SL面积为{l.SL2010_km2:.3f}和{l.SL2020_km2:.3f} km²，扩张{l.expansion_km2:.3f} km²、收缩{l.contraction_km2:.3f} km²，净变化为{l.net_change_km2:.3f} km²。比例图提供面积组成，方向变化图揭示扩张和收缩的具体位置，两类结果共同描述了跨期变化。

![Figure 4.6](../figures/region_atlas_24/Figure_4_6_Task_outputs.png)

Figure 4.6. Task-oriented outputs for H01 and L01. The first two columns show SL proportions in2010 and2020 on30×30 supports; the last column shows native-grid SL expansion and contraction. Unchanged denotes unchanged SL membership.

结果验证覆盖24个样区。四个SL细类汇总后的面积与SL面积一致，类别比例积分恢复对应支持域的面积总量，扩张面积减去收缩面积等于两期SL面积之差；各项面积残差小于10⁻⁶ m²，输出栅格回读与写入数组一致。这样的验证把任务输出与输入对应关系连接起来，也使需要复核的问题能够定位到具体处理环节。

### 4.5.5 Implications for multidimensional alignment

两个机制实验表明，空间支持域、时间条件与语义层级共同影响地理信息的表达，类别合并和空间聚合的顺序也会改变结果。框架运行示例进一步说明，任务要求决定需要建立何种对应、保留哪些信息，以及采用什么输出表达。面积、类别与变化位置之间的联系通过共同网格、语义映射和跨期关系得到组织。

因此，本例的数据对齐不是以一张图像作为统一终点，而是形成一组相互关联的多时相分类、支持域组成和任务结果。原始产品的分类误差仍会传播至这些结果；本节主要分析处理过程的信息保留与一致性。框架将任务需求与处理依据显式连接，为后续统计、制图和变化分析提供可追溯的数据基础。
'''
    text=text.replace('the24','the 24').replace('in2020','in 2020').replace('in2010','in 2010').replace('and2020','and 2020').replace('factor30','factor 30').replace('on30','on 30')
    assert 'B2' not in text and 'Baseline' not in text and 'Supplementary spatial figures' not in text
    md.write_text(text,encoding='utf8');builder.MD=md
    doc=Document();style=doc.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(11);style.element.rPr.rFonts.set(qn('w:eastAsia'),'宋体')
    doc.sections[0].left_margin=Inches(.85);doc.sections[0].right_margin=Inches(.85)
    builder.render(doc);single=ROOT/'reports/4.5_24样区_多尺度图与框架示例版.docx';doc.save(single)
    src=builder.SOURCE;before=sha(src);doc=Document(src);prefix=[p.text for p in doc.paragraphs[:57]];refs=[p.text for p in doc.paragraphs[58:]]
    target=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验');target._p.getparent().remove(target._p);anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献');builder.render(doc,anchor)
    whole=ROOT/'reports/第四部分_24样区_框架示例整合版.docx';doc.save(whole)
    check=Document(whole);pos=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献')
    assert [p.text for p in check.paragraphs[:57]]==prefix and [p.text for p in check.paragraphs[pos:]]==refs and sha(src)==before
    assert len(check.inline_shapes)==len(Document(src).inline_shapes)+5
    # Preserve scientific numbers, while rewriting prose and removing the historical-case presentation.
    expected=['0.777%','4.843%','0.191%','0.948%','−0.0686','3.309']
    assert all(v in text for v in expected)
    dump(OUT/'paper_verification.json',dict(time=now(),source_unchanged=True,prior_sections_preserved=True,main_experiment_numbers_preserved=True,study_map_in_section451=True,no_historical_case_in_manuscript=True,figures=5,tables=3,example_regions=['H01','L01'],outputs=[str(md),str(single),str(whole)]))
    print('Revised paper saved:24 regions, study map in4.5.1, H01/L01 walkthrough,5 figures,3 tables.')
if __name__=='__main__':main()
