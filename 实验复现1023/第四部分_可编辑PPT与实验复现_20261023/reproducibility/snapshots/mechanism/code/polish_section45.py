"""Explain original sampling and polish prose, without changing results."""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
import build_section45 as builder

FIG=ROOT/'figures/sensitivity_definition';FIG.mkdir(exist_ok=True)
def main():
    protected={str(p):sha(p) for p in [ROOT/'selection/candidates.csv',ROOT/'selection/selected_regions.csv',ROOT/'selection/thresholds.json',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv']}
    c=pd.read_csv(ROOT/'selection/candidates.csv');e=c[c.reason=='eligible'].copy();q=load(ROOT/'selection/thresholds.json');s=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv').sort_values('display_id')
    lo,hi=q['Q25'],q['Q75'];assert np.allclose(np.quantile(e.H_SL,[.25,.75]),[lo,hi])
    assert len(e[e.H_SL<=lo])==179 and len(e[e.H_SL>=hi])==179
    for r in s.itertuples():
        u=np.array([getattr(r,'p'+str(code)) for code in [21,22,23,24]])/r.pSL
        assert np.isclose(-sum(u[u>0]*np.log2(u[u>0])),r.H_SL,atol=1e-12)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig=plt.figure(figsize=(13,10),constrained_layout=True);gs=fig.add_gridspec(2,2,height_ratios=[.55,1]);ax=fig.add_subplot(gs[0,:]);ax.axis('off')
    texts=['5,782 full-grid windows\n1,200 × 1,200 native pixels','Coverage + composition\n+ preset spatial exclusions','714 eligible windows\nCompute within-SL entropy','179 Low / 179 High\n356 middle: not sampled','12 Low + 12 High\nSpatially spread selection']
    for i,t in enumerate(texts):
        x=.005+i*.2;ax.add_patch(FancyBboxPatch((x,.40),.18,.38,boxstyle='round,pad=0.007',fc='#eef3f6',ec='#839bac',transform=ax.transAxes));ax.text(x+.09,.59,t,ha='center',va='center',transform=ax.transAxes,fontsize=10)
        if i<4:ax.annotate('',xy=(x+.197,.59),xytext=(x+.183,.59),xycoords='axes fraction',arrowprops={'arrowstyle':'->','color':'#405060'})
    ax.text(.01,.2,'Eligibility: valid coverage ≥95%; 20% ≤ SL fraction ≤80%; Others ≥10%.\nEntropy is based on the four SL subclasses in 2020, not on non-commutativity or task performance.',transform=ax.transAxes,fontsize=11)
    hist=fig.add_subplot(gs[1,0]);bins=np.linspace(0,2,31);hist.hist(e.H_SL,bins=bins,color='#a9afb6',edgecolor='white')
    hist.axvspan(0,lo,color='#357bab',alpha=.16);hist.axvspan(hi,2,color='#d5643d',alpha=.16)
    for value,label,col in [(lo,f'Q25 = {lo:.6f}\nLow pool:179','#357bab'),(hi,f'Q75 = {hi:.6f}\nHigh pool:179','#d5643d')]:
        hist.axvline(value,color=col,ls='--');hist.text(value+.02,hist.get_ylim()[1]*.92,label,color=col,va='top',fontsize=10)
    hist.plot(s[s.group=='Low'].H_SL,np.full(12,-1.5),'|',color='#357bab',ms=12);hist.plot(s[s.group=='High'].H_SL,np.full(12,-3.5),'|',color='#d5643d',ms=12)
    hist.set(xlim=(0,2),xlabel='Within-SL conditional entropy (bits)',ylabel='Candidate window count',title='(a) Thresholds in the complete eligible pool')
    bars=fig.add_subplot(gs[1,1]);ordered=s.sort_values('display_id');u=np.array([[getattr(r,'p'+str(k))/r.pSL for k in [21,22,23,24]] for r in ordered.itertuples()]);bottom=np.zeros(24)
    colors=['#edc85c','#a6c275','#5aa589','#287c77']
    for i,k in enumerate([21,22,23,24]):bars.barh(np.arange(24),u[:,i],left=bottom,color=colors[i],label=f'SL{k}');bottom+=u[:,i]
    bars.set(yticks=np.arange(24),yticklabels=ordered.display_id,xlim=(0,1),xlabel='Subclass fraction within SL',title='(b) Composition of all24 selected windows');bars.invert_yaxis();bars.legend(ncol=4,loc='lower center',bbox_to_anchor=(.5,-.16),fontsize=8);bars.axhline(11.5,c='#586575',lw=1)
    for ext in ['png','pdf']:fig.savefig(FIG/f'Figure_4_2b_Sensitivity_definition.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    table=s[['display_id','id','group','lon','lat','coverage','pSL','pOthers','H_SL','p21','p22','p23','p24']].copy()
    for k in [21,22,23,24]:table[f'within_SL_{k}']=table[f'p{k}']/table.pSL
    table['threshold_rule']=np.where(table.group=='High',f'H_SL >= {hi:.15f}',f'H_SL <= {lo:.15f}')
    write_csv(FIG/'24样区分组依据与组成.csv',table.to_dict('records'))
    (ROOT/'reports/敏感区域划分_完整方法记录.md').write_text(f'''# 敏感区域划分：与实际选区代码一致的方法记录

本次仅说明既有分组，不重新选择样区。输入为2020年Han原始分类；共同有效域由四期Han及Wang2020的合法类别交集确定。共同有效覆盖率用像元数计算；类别组成和条件熵使用WGS84有效面积。

## 候选筛选

Han2020原点起的不重叠1200×1200完整窗口共5782个，尾部不足整窗不补齐。代码按顺序检查共同空间范围、预设空间排除、覆盖率、SL比例和Others比例，记录首个拒绝原因：

{c.reason.value_counts().to_string()}

预设空间排除指距原历史案例几何中心100km以内的候选窗，影响31窗。该条件保持在复现记录中，没有因正文不展示该案例而删除或改写。其他拒绝理由为共同范围之外49窗、覆盖不足2910窗、SL比例不在[20%,80%]内2058窗、Others不足10%20窗。714窗进入阈值计算。

## 指标与阈值

u_i=A(SL_i)/Σ_i A(SL_i)，H_SL=−Σ_i u_i log2(u_i)，零项取0。分母是SL总面积，不是整窗面积。四子类均分时H=2；只有一种SL子类时H=0。不是六类整体熵，也不是SL占比。

按714窗的H线性插值计算Q25={lo:.15f}、Q75={hi:.15f}。Low≤Q25共179窗；High≥Q75共179窗；中间356窗不进入两端对照，但保留在候选文件。

## 抽样

PCG64种子20261016；High先、Low后交替。每组第一个窗口在当时满足距已选窗口至少50km的候选中随机选取；后续选择距全部已选窗口的最小距离最大者。距离同分容差1e−6m，按行列升序。各取12窗，实际所有已选窗口间最小中心距约243km。不按结果补样或挑选。

H01至H12、L01至L12按组内入选顺序编号，不是按熵或非交换率排序。完整对应和四子类组成见figures/sensitivity_definition/24样区分组依据与组成.csv。

正文所称高/低敏感性是语义层级合并的潜在敏感性，采用原始SL混合度作为代理。实际操作顺序风险由实验2另行计算；分组不保证任何一个窗口的非交换率或任务误差一定较高/较低。
''',encoding='utf8')
    old=(ROOT/'reports/4.5_任务决策与运行记录_恢复折线图.md').read_text(encoding='utf8')
    # Keep quantitative tables intact while rewriting all explanatory prose.
    def table_after(caption):
        start=old.index('|',old.index(caption));end=old.find('\n\n',start);return old[start:end]
    tables={n:table_after(f'Table 4.{n}.') for n in [3,4,5,6]}
    text=f'''## 4.5 Case study of multidimensional alignment and task-oriented processing

本节用蒙古高原土地覆盖数据回答三个问题：改变空间支持域和类别层级，会怎样影响跨期变化的表达？语义合并与空间聚合的先后顺序，会不会得到不同的分类结果？面对面积统计和变化位置识别两项任务，应当保留什么信息、怎样安排处理步骤？前两个问题通过样区实验分析，第三个问题通过框架运行示例说明。

### 4.5.1 Data and sensitivity-based sampling

实验采用Han等[135]的蒙古高原沙漠与沙地分类数据，使用2000、2010、2015和2020年四个时相。原始类别包括沙漠（SD）、四个沙地细类及其他地类（Others）。四个沙地细类可合并为沙地上位类（SL），因此能够在同一数据上比较细类表达与上位类表达。Wang等[134]的土地覆盖数据用于限定共同有效覆盖范围和展示区域背景。两套产品及24个样区的位置见图4.2a。

![Figure 4.2a](../figures/region_atlas_24/Figure_4_2_Study_regions.png)

Figure 4.2a. Study products and selected windows. H01–H12 identify the high-sensitivity group and L01–L12 the low-sensitivity group. Rectangles show the window footprints.

**分组依据。** 本文所说的“敏感性”，指类别层级合并可能影响空间聚合结果的程度。若一个区域的SL主要由单个细类组成，合并前后其类别支持较集中；若多个SL细类共同占据面积，合并会累计这些分散的贡献，更有可能改变它们与其他类别之间的优势关系。因此，采用SL内部的细类混合程度作为选区指标，再通过实验2检验实际顺序差异。

具体使用2020年原始分类计算四个SL细类的面积比例。令Aᵢ为窗口内第i个SL细类的有效面积，A_SL为四个细类面积之和，则uᵢ=Aᵢ/A_SL，条件熵为H_SL=−Σᵢuᵢlog₂uᵢ，uᵢ=0的项取0。这里的分母是SL面积，而不是整个窗口面积：H_SL描述“沙地内部有多混合”，SL占比则描述“窗口内有多少沙地”。当SL全部来自一个细类时H_SL=0；四个细类各占SL面积的25%时H_SL=2 bit。相同SL总占比的两个窗口，也可以具有不同的H_SL。

**候选区与阈值。** 在Han2020网格上划分不重叠的1200×1200像元窗口，按预设空间范围与排除条件、共同有效覆盖率和类别组成筛选。窗口须有至少95%的共同有效像元，SL占有效面积的20%—80%，Others占比至少10%。这保证候选区包含足够的SL及其他类别，而不是将几乎没有沙地的区域与沙地区域直接比较。5782个完整窗口中，714个满足全部条件，完整排除记录见配套方法文件。

用这714个窗口的H_SL分布确定阈值：下四分位数为0.680559 bit，上四分位数为1.144047 bit。H_SL≤0.680559的179个窗口构成Low候选池，H_SL≥1.144047的179个窗口构成High候选池。两阈值之间的356个窗口保留在候选记录中，不进入高低两端的比较。图4.2b展示了筛选流程、阈值位置和最终样区的细类组成。

**各组抽取12个样区。** 先用固定随机种子20261016为两组分别确定起点，再交替从High和Low候选池选取距已选窗口最分散的窗口，即最大化到所有已选窗口的最小中心距离。每次选择要求距已选窗口至少50 km；最终24个窗口的实际最小中心距离约243 km。H01—H12、L01—L12按组内抽取顺序编号。阈值和样区名单均在计算非交换率之前确定，没有使用非交换率或任务表现选区。

![Figure 4.2b](../figures/sensitivity_definition/Figure_4_2b_Sensitivity_definition.png)

Figure 4.2b. Sensitivity-based sampling. The workflow shows candidate screening and spatial selection. Panel(a) locates the quartile thresholds in the714-window entropy distribution; short marks below the histogram indicate selected windows. Panel(b) shows the proportions of the four subclasses within SL for all24 selected windows. Middle-quartile candidates are not included in the two-group comparison.

| 项目 | Low：低敏感组 | High：高敏感组 |
|---|---|---|
| 分组指标 | SL内部四细类条件熵H_SL | 同左 |
| 阈值 | H_SL≤0.680559 bit | H_SL≥1.144047 bit |
| 候选窗口数 | 179 | 179 |
| 最终样区数 | 12 | 12 |
| 入选窗口H_SL范围 | 0.048521—0.655006 bit | 1.153732—1.843285 bit |
| 类别结构含义 | SL较集中于少数细类 | SL分散于多个细类 |

后续处理先按地理坐标核验各年份的像元对应，再取四期Han和Wang2020合法类别的交集作为共同有效域。面积按WGS84椭球像元面积加权。3×3、10×10和30×30均表示支持域每边的原始像元数，三个尺度覆盖相同的窗口范围。实验1和2以样区为统计单位；文中的95%置信区间通过10000次整窗重采样得到。

Table 4.2. Questions and outputs of the two experiments and the framework walkthrough.

| 内容 | 研究问题 | 设置与输出 |
|---|---|---|
| 实验1：跨维耦合 | 空间聚合的影响是否随时段和类别层级变化？ | 3个时段×3个支持域×2个语义层级；变化位置损失 |
| 实验2：非交换性 | 先合并类别还是先空间聚合，会不会改变结果？ | 两组各12窗、3个支持域；路径分歧及其空间分布 |
| 框架运行示例 | 不同任务需要保留什么信息，如何安排处理？ | 2010—2020；面积、位置两项任务及五步决策记录 |

### 4.5.2 How spatial support changes temporal-change representation

实验1固定2020年为终点，分别与2015、2010和2000年比较。在每个时段中，先按六细类或三上位类建立原始变化图，再在3×3、10×10和30×30支持域上分别形成两期优势类别图并检测变化。每个语义层级使用自己的原始变化图作为参照：例如，SL内部细类转换在六类任务中属于变化，合并为SL后则不属于上位类变化。

评价指标为面积加权F1，图4.3展示1−F1；数值越大，表示聚合后的变化位置与原始表达差异越大。图中每个数值先在各样区独立计算，再对组内12个样区等权平均。空间支持域扩大后，细碎变化更难在单个优势类别中保留，但损失的大小还取决于比较时段和语义层级。

以High组2010—2020年为例，六类任务的平均损失从3×3时的0.207增至30×30时的0.363，三类任务则从0.284增至0.509。进一步逐窗比较F1从3×3到30×30的下降量，三类表达比六类表达平均多下降0.0686，95%置信区间为[0.0383，0.1007]。这一差异并非所有条件下都同样明显：Low组2015—2020年的对应差异区间跨过0，未呈现明确的层级差别。

时间段也改变了空间聚合的影响。High组三类任务中，2000—2020年相对于2015—2020年的尺度响应差为0.0451，95%置信区间为[0.0189，0.0707]。这说明同样的空间处理放到不同跨期任务中，会保留不同程度的变化信息。其解释需要同时考虑时间段内的变化过程和所采用的类别定义。

![Figure 4.3](../figures/Figure_1_Coupling.png)

Figure 4.3. Mean change-location loss(1−F1) across temporal intervals, supports and semantic levels. Each level uses its corresponding native-grid change reference; larger values indicate greater loss of source-product change locations.

### 4.5.3 Why the order of semantic merging and spatial aggregation matters

实验2使用2020年分类，比较两条处理路径。第一条先把四个沙地细类合并为SL，再按有效面积选择粗格的优势类别；第二条先在六细类中选择优势类别，再把赢家映射到SD、SL或Others。若两条路径在同一粗格给出不同类别，该格记为顺序分歧。非交换率是分歧格数占共同可判定格数的比例；平票作为未确定状态另报。

High组的平均非交换率在三个尺度上均高于Low组（表4.3、图4.4a）。从3×3到30×30，High组由0.777%增加至4.843%，Low组由0.191%增加至0.948%。两组增幅相差3.309个百分点，95%置信区间为[1.975，4.736]个百分点。结果与分组所关注的机制一致：多个沙地细类单独参与优势选择时，各自贡献较小；合并为SL后，这些贡献相加，可能改变与其他类别之间的面积排序。

Table 4.3. Mean window-level non-commutativity rates.

{tables[3]}

![Figure 4.4a](../figures/review_multiscale_order/Figure_4_4a_Scale_trends.png)

Figure 4.4a. Non-commutativity across spatial supports. Thick lines show group means and thin lines show individual windows.

图4.4b上排将每个窗口的H_SL与实际非交换率对应，展示“用于分组的组成指标”与“随后观察到的操作差异”的关系。下排改变聚合起点，在每个尺度采用九种网格相位，并在共同内部范围计算非交换率的变化幅度。组成和支持域相同，格子边界的位置仍可能改变局部优势类别，因此相位响应作为补充结果单独报告。

![Figure 4.4b](../figures/review_multiscale_order/Figure_4_4_All_scales.png)

Figure 4.4b. Upper row: entropy and observed non-commutativity at each support. Lower row: within-window ranges across nine grid phases on a common interior domain.

图4.5以各组首个入选窗口H01和L01展示具体位置。每行分别对应3×3、10×10和30×30，前两列是两条路径的类别结果，末列以红色标记输出不一致的粗格。读者可以从分类图中检查哪些位置改变了类别，而不只比较一个总体百分比。

![Figure 4.5a](../figures/review_multiscale_order/H01_three_scales_order_difference.png)

Figure 4.5a. H01: semantic-first output, spatial-first output and disagreement at three supports. Red denotes unequal classes in jointly decidable cells; dark gray denotes unresolved comparison.

![Figure 4.5b](../figures/review_multiscale_order/L01_three_scales_order_difference.png)

Figure 4.5b. L01 under the same two processing orders, color scheme and spatial supports.

### 4.5.4 From task requirements to traceable processing decisions

前两个实验说明，统一网格和类别以后，仍需决定操作顺序及信息保留方式。第三部分用2010—2020年SL变化任务展示框架如何作出这些决定。框架在24个样区中执行相同流程，H01和L01用于展示记录与输出。

**先明确任务，再选择表达。** 面积任务需要两期SL面积，以及扩张、收缩和净变化总量；位置任务需要指出扩张和收缩发生在哪里。前者要求面积完整，后者要求保留原始位置。这一区别决定后续不能仅用一张统一粗分辨率分类图承担全部任务。

**诊断影响对应关系的输入差异。** 检查发现，Han2010与Han2020的坐标系和像元尺寸一致，但文件原点相差119行。流程按地理坐标恢复各自的窗口索引，使两期数组对应到同一位置，并建立共同有效域。随后将四个沙地细类合并到SL，形成一致的目标类别。两期类别不同保留为待分析的状态转移，而不是作为需要消除的失配。

**根据依赖关系保留信息。** 面积统计采用类别比例，因为一个优势类别无法保存格内全部组成。扩张和收缩总量还需要跨期配对：两期各自的SL比例只能确定净面积差，不能判断有多少位置发生了相反方向的转移。因此先在原始网格识别SL扩张、收缩，再将它们的面积比例汇总到相应支持域。位置任务直接保留这套原生配对，粗格类别只用于检查尺度造成的损失。

**组织两条任务分支。** 共同空间索引、有效域和语义映射是共享准备步骤。此后，面积分支输出两期SL比例和跨期转移比例，位置分支输出原始网格上的扩张/收缩图。前者回答“有多少”，后者回答“在哪里”。表4.4列出各步骤使用的证据、作出的选择和保存的记录。

Table 4.4. Evidence and decisions recorded during the framework walkthrough.

{tables[4]}

实际结果见表4.5。H01的SL面积由320.011 km²降至214.240 km²，扩张87.852 km²、收缩193.623 km²，净变化为−105.771 km²。L01的两期面积为400.307和338.821 km²，扩张61.566 km²、收缩123.053 km²，净变化为−61.487 km²。三个支持域均分别重新计算了组成和转移比例，其加权面积与原生像元统计一致；表中的残差记录浮点计算差异。

Table 4.5. Area outputs at native and aggregated supports. Areas are in km²; numerical residuals are in m². Expansion and contraction are integrated from paired-transition fractions.

{tables[5]}

**用任务要求检查输出。** 面积检查核对语义合并前后的SL总量、比例积分，以及“扩张减收缩”等于“终期面积减初期面积”的收支关系。24个样区的最大数值残差为2.27×10⁻⁷ m²。位置检查将不同支持域的变化图与原生变化图对应，记录F1、IoU和可判定覆盖率（表4.6）。H01的F1从3×3时的0.7286降至30×30时的0.5422，L01从0.7388降至0.5789。图4.6展示了这些损失的空间位置。

Table 4.6. Spatial-support diagnostics for SL-change locations. The last column gives confirmed SL area from dominant-class maps, not the area-preserving fractional output.

{tables[6]}

![Figure 4.6](../figures/framework_decision_walkthrough/Figure_4_6_Task_change_and_supports.png)

Figure 4.6. Native SL-change outputs and coarse-support diagnostics for H01 and L01. Columns show native,3×3,10×10 and30×30 results on the same extent. Colors distinguish expansion, contraction, unchanged SL membership and unresolved locations.

检查结果同时指向需要返回的步骤：面积收支不一致时复核有效域、面积权重和转移汇总；粗格位置输出不满足原生定位要求时，重新检查支持域和表达选择。本次面积检查通过，因此没有发生数值修复。位置任务采用原生网格，尺度诊断则保留为信息损失记录。

同输入的直接差分用于核对这一流程。先明确SL成员关系后，I_SL,2020−I_SL,2010与框架的扩张/收缩图在24个样区逐像元一致。原始细类代码相减还会包含SL内部转换，回答的是另一种类别变化问题。框架在此提供的是比较对象、处理依赖和验证依据的明确记录，使简单运算建立在可解释的数据对应之上。

### 4.5.5 Implications for the alignment framework

本案例将三个问题联系起来：空间支持域与类别层级共同改变变化表达；操作顺序影响聚合类别；任务要求进一步决定哪些组成和位置关系需要保留。对齐的输出因而是一组有共同参照的多时相分类、支持域比例、面积统计与变化位置图，而不是一张适用于所有分析的融合影像。

框架的运行示例说明了如何把处理选择与任务要求联系起来，并留下能够检查的依据。面积与位置任务使用相同输入，却选择不同表达；验证结果可以定位到需要复核的索引、语义映射或汇总步骤。本节反映原始产品信息在处理中的保留情况，源产品的分类误差仍会传递至最终结果。
'''
    text=text.replace('the714','the 714').replace('all24','all 24').replace('loss(1','loss (1').replace('native,3×3,10×10 and30×30','native, 3×3, 10×10 and 30×30')
    # Preserve numerical statements while simplifying jargon in table labels.
    text=text.replace('任务合同与输出要求','任务定义与输出要求').replace('共同mask','共同有效域').replace('索引、mask、语义一致的两期分类','索引、有效域、语义一致的两期分类')
    md=ROOT/'reports/4.5_敏感性分组说明与全文润色版.md';md.write_text(text,encoding='utf8');builder.MD=md
    source=Document(builder.SOURCE);sourcehash=sha(builder.SOURCE)
    for whole in [False,True]:
        doc=Document(builder.SOURCE) if whole else Document()
        if whole:
            p=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验');p._p.getparent().remove(p._p);anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献')
        else:
            anchor=None;doc.styles['Normal'].font.name='Times New Roman';doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].element.rPr.rFonts.set(qn('w:eastAsia'),'宋体');doc.sections[0].left_margin=Inches(.85);doc.sections[0].right_margin=Inches(.85)
        builder.render(doc,anchor);dest=ROOT/'reports'/('第四部分_敏感性分组说明与全文润色版.docx' if whole else '4.5_敏感性分组说明与全文润色版.docx');doc.save(dest)
        check=Document(dest);assert len(check.inline_shapes)==(len(source.inline_shapes) if whole else 0)+8
        if whole:
            idx=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献');assert [p.text for p in check.paragraphs[:57]]==[p.text for p in source.paragraphs[:57]];assert [p.text for p in check.paragraphs[idx:]]==[p.text for p in source.paragraphs[58:]]
    assert sha(builder.SOURCE)==sourcehash and all(sha(p)==h for p,h in protected.items())
    dump(FIG/'revision_checks.json',dict(time=now(),passed=True,thresholds_recomputed_equal=True,selected_subclass_entropy_verified=True,pools={'Low':179,'Middle':356,'High':179},selected=24,source_and_experiment_data_unchanged=True,main_figures=8,full_exclusion_details_preserved=True))
    print('Sampling illustration and fully polished section saved; numerical and source checks passed.')
if __name__=='__main__':main()
