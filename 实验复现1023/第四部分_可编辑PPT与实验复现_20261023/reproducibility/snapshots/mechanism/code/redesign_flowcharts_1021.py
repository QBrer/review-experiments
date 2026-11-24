"""Rebuild three workflow diagrams as matching vector figures and editable PPT shapes.
Edit the user's 1021 DOCX in a new file; preserve their paragraph/table content.
"""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyArrowPatch
from matplotlib import font_manager
from pptx import Presentation
from pptx.util import Inches,Pt as PPt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement as PX
from docx import Document
from docx.shared import Inches as DI,Pt
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import hashlib,re,json

SOURCE=Path(r'C:\Users\QBrer\OneDrive\桌面\数据对齐\1019\4.5_敏感性分组说明与全文润色版1021.docx')
OUT=ROOT/'figures/flowcharts_1021';OUT.mkdir(parents=True,exist_ok=True)
PRES=Presentation();PRES.slide_width=Inches(16);PRES.slide_height=Inches(12)
ACCENT='CE8580';DARK='253746';BG='FCFAF9';NODE='FFFFFF';MUTED='566775'
fontfile=Path('C:/Windows/Fonts/msyh.ttc');font_manager.fontManager.addfont(str(fontfile));CJK=font_manager.FontProperties(fname=str(fontfile)).get_name()
plt.rcParams.update({'font.family':[CJK,'DejaVu Sans'],'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'none'})

class Diagram:
    def __init__(self,name,h):self.name=name;self.w=16;self.h=h;self.items=[]
    def text(self,x,y,w,h,text,size=13,bold=False,color=DARK,align='center'):
        for old,new in [('Han2020','Han 2020'),('Han2010','Han 2010'),('SL20','SL 20'),('12High+12Low','12 High + 12 Low'),('pair2010 with2020','pair 2010 with 2020'),('offset:119','offset: 119'),('Semantic:21','Semantic: 21'),('on3×3 /10×10 /30×30','on 3×3 / 10×10 / 30×30'),('across24','across 24')]:
            text=text.replace(old,new)
        self.items.append(dict(kind='text',x=x,y=y,w=w,h=h,text=text,size=size,bold=bold,color=color,align=align))
    def box(self,x,y,w,h,text='',size=13,fill=NODE,dash=True,bold=False):
        self.items.append(dict(kind='box',x=x,y=y,w=w,h=h,fill=fill,dash=dash))
        if text:self.text(x+.08,y+.04,w-.16,h-.08,text,size,bold)
    def stage(self,y,h,label,tabw):
        self.box(.38,y,15.24,h,fill=BG,dash=True)
        self.box(.65,y-.19,tabw,.48,label,size=14,fill=NODE,dash=False,bold=True)
    def arrow(self,pts,dash=False,color=DARK,label=None):
        self.items.append(dict(kind='arrow',pts=pts,dash=dash,color=color))
        if label:
            x,y,w,t=label;self.text(x,y,w,.3,t,10,color=color)
    def mpl(self,ax):
        ax.set(xlim=(0,self.w),ylim=(self.h,0));ax.axis('off')
        for o in self.items:
            if o['kind']=='box':ax.add_patch(Rectangle((o['x'],o['y']),o['w'],o['h'],facecolor='#'+o['fill'],edgecolor='#'+ACCENT,lw=1,linestyle=(0,(7,4)) if o['dash'] else '-'))
            elif o['kind']=='text':
                ax.text(o['x']+(o['w']/2 if o['align']=='center' else 0),o['y']+o['h']/2,o['text'],ha=o['align'],va='center',fontsize=o['size'],weight='bold' if o['bold'] else 'normal',color='#'+o['color'],linespacing=1.35)
            else:
                pts=o['pts']
                for a,b in zip(pts[:-2],pts[1:-1]):ax.plot([a[0],b[0]],[a[1],b[1]],c='#'+o['color'],lw=1.15,ls='--' if o['dash'] else '-')
                ax.add_patch(FancyArrowPatch(pts[-2],pts[-1],arrowstyle='-|>',mutation_scale=12,lw=1.15,color='#'+o['color'],linestyle='--' if o['dash'] else '-',shrinkA=0,shrinkB=0))
    def save(self):
        fig,ax=plt.subplots(figsize=(16,self.h));fig.subplots_adjust(left=0,right=1,bottom=0,top=1);self.mpl(ax)
        for ext in ['png','pdf','svg']:fig.savefig(OUT/(self.name+'.'+ext),dpi=220,bbox_inches='tight',pad_inches=.06)
        plt.close(fig);self.ppt()
    def ppt(self):
        s=PRES.slides.add_slide(PRES.slide_layouts[6]);dy=(12-self.h)/2
        for o in self.items:
            if o['kind']=='box':
                sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(o['x']),Inches(o['y']+dy),Inches(o['w']),Inches(o['h']));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(o['fill']);sh.line.color.rgb=RGBColor.from_string(ACCENT);sh.line.width=PPt(1)
                if o['dash']:sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
            elif o['kind']=='text':
                sh=s.shapes.add_textbox(Inches(o['x']),Inches(o['y']+dy),Inches(o['w']),Inches(o['h']));tf=sh.text_frame;tf.word_wrap=True;tf.margin_left=tf.margin_right=Inches(.02);tf.margin_top=tf.margin_bottom=0;tf.vertical_anchor=MSO_ANCHOR.MIDDLE
                for i,t in enumerate(o['text'].split('\n')):
                    p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=t;p.alignment=PP_ALIGN.CENTER if o['align']=='center' else PP_ALIGN.LEFT;p.font.name='Microsoft YaHei';p.font.size=PPt(o['size']);p.font.bold=o['bold'];p.font.color.rgb=RGBColor.from_string(o['color'])
            else:
                for i,(a,b) in enumerate(zip(o['pts'][:-1],o['pts'][1:])):
                    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(a[0]),Inches(a[1]+dy),Inches(b[0]),Inches(b[1]+dy));sh.line.color.rgb=RGBColor.from_string(o['color']);sh.line.width=PPt(1.15)
                    if o['dash']:sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
                    if i==len(o['pts'])-2:
                        arrow=PX('a:tailEnd');arrow.set('type','triangle');sh.line._get_or_add_ln().append(arrow)
        s.notes_slide.notes_text_frame.text=self.name+' | Native editable boxes, text and connectors. Solid arrows: processing; dashed arrows: conditional feedback. No rasterized flowchart.'

def sampling(cn=False):
    d=Diagram('Figure_4_2b_sampling_flow_'+('CN' if cn else 'EN'),7.2)
    d.stage(.5,1.7,'01  候选窗口构建与筛选' if cn else '01  Candidate construction and screening',4.6 if cn else 5.4)
    labels=['Han 2020原始网格\n1200×1200像元窗口','5,782个完整窗口\n共同空间范围检查','有效覆盖≥95%\nSL 20%—80%；Others≥10%','714个合格窗口\n保留筛选与排除记录'] if cn else ['Han2020 native grid\n1,200×1,200-pixel windows','5,782 complete windows\nSpatial eligibility checks','Valid coverage≥95%\nSL20–80%; Others≥10%','714 eligible windows\nRecorded exclusions']
    for i,t in enumerate(labels):d.box(.75+i*3.8,1.1,3.25,.80,t,12)
    for i in range(3):d.arrow([(4.0+i*3.8,1.50),(4.55+i*3.8,1.50)])
    d.arrow([(13.8,2.2),(13.8,2.56),(.53,2.56),(.53,3.97),(.75,3.97)])
    d.stage(2.95,1.75,'02  敏感性指标与分层' if cn else '02  Sensitivity measurement and stratification',4.6 if cn else 6.0)
    labels=['SL内部四细类面积比例\nuᵢ=Aᵢ/A_SL；H=−Σuᵢlog₂uᵢ','线性插值四分位数\nQ25=0.680559\nQ75=1.144047','Low：H≤Q25，179窗\n中间组：356窗\nHigh：H≥Q75，179窗'] if cn else ['Within-SL subclass fractions\nuᵢ=Aᵢ/A_SL; H=−Σuᵢlog₂uᵢ','Linearly interpolated quartiles\nQ25=0.680559\nQ75=1.144047','Low: H≤Q25,179 windows\nMiddle:356 windows\nHigh: H≥Q75,179 windows']
    for x,w,t in zip([.75,5.35,10.4],[3.9,4.25,4.45],labels):d.box(x,3.52,w,.90,t,12)
    d.arrow([(4.65,3.97),(5.35,3.97)]);d.arrow([(9.60,3.97),(10.4,3.97)])
    d.arrow([(13.8,4.7),(13.8,5.03),(.53,5.03),(.53,6.33),(.75,6.33)],label=(7,4.78,5,'仅High/Low进入抽样' if cn else 'Only High/Low enter selection'))
    d.stage(5.45,1.5,'03  空间分散抽样与冻结' if cn else '03  Spatially dispersed selection and freezing',4.8 if cn else 6.2)
    labels=['两组分别随机起点\nseed=20261016','两组交替最大最小距离选择\n距所有已选窗口≥50km','High12窗＋Low12窗\n冻结名单、阈值与抽样轨迹'] if cn else ['Random start in each group\nseed=20261016','Alternate global maximin selection\n≥50km from all selected centers','12High+12Low windows\nFreeze list, thresholds and trace']
    for x,w,t in zip([.75,5.35,10.4],[3.9,4.25,4.45],labels):d.box(x,5.97,w,.72,t,12)
    d.arrow([(4.65,6.33),(5.35,6.33)]);d.arrow([(9.60,6.33),(10.4,6.33)])
    return d

def framework(cn=False):
    d=Diagram('Figure_4_1_Integrated_framework_'+('CN' if cn else 'EN'),11.8)
    titles=['01  定义任务','02  诊断失配','03  分析跨维约束','04  组织对齐','05  验证对齐与交付'] if cn else ['01  Define the task','02  Diagnose mismatches','03  Analyze cross-dimensional constraints','04  Organize alignment','05  Validate alignment and deliver outputs']
    ys=[.45,2.55,4.65,6.75,8.85]
    for i,y in enumerate(ys):d.stage(y,1.65 if i<4 else 2.35,titles[i],4.0 if cn else [3.8,4.7,6.7,4.5,6.9][i])
    rows=[['研究目标与用途','对齐对象\n像元／实体／事件／概念','对应要求与验收条件'],['空间\n位置、几何、拓扑','时间\n时相、过程阶段、有效期','语义\n类别、概念与层级'],['空间—时间—语义耦合','尺度与支持域\n信息保留要求','依赖、冲突与操作顺序'],['顺序式\n前置依赖','迭代式\n证据反馈','联合式\n共同约束','层级式\n嵌套表达']] if cn else [['Objective and intended use','Alignment objects\nPixels / entities / events / concepts','Correspondence requirements\nAcceptance criteria'],['Spatial\nPosition / geometry / topology','Temporal\nTime / process stage / validity','Semantic\nClasses / concepts / hierarchies'],['Spatial–temporal–semantic coupling','Scale and support\nInformation-retention requirements','Dependencies, conflicts\nand operation order'],['Sequential\nDependencies','Iterative\nFeedback','Joint\nShared constraints','Hierarchical\nNested levels']]
    for i,row in enumerate(rows):
        y=ys[i]+.58
        if len(row)==3:
            for x,t in zip([.8,5.65,10.5],row):d.box(x,y,4.2,.78,t,13)
            if i in [0,2]:
                for x in [5,9.85]:d.arrow([(x,y+.39),(x+.65,y+.39)])
        else:
            for x,t in zip([.8,4.55,8.3,12.05],row):d.box(x,y,3.1,.76,t,13)
            d.text(3,ys[i]+1.35,10,.24,'组织方式可组合，层级关系可贯穿各方式' if cn else 'Modes can be combined; hierarchy can support each mode',11,color=MUTED)
        if i<3:d.arrow([(8,ys[i]+1.65),(8,ys[i+1]+.56)])
    d.arrow([(8,8.40),(8,9.42)])
    labels=['对应有效性','跨维一致性','任务适用性'] if cn else ['Correspondence validity','Cross-dimensional consistency','Task-specific fitness for use']
    for x,t in zip([.8,5.65,10.5],labels):d.box(x,9.44,4.2,.54,t,13)
    d.box(3.0,10.39,10,.55,'对应关系与对齐数据／有效条件／未匹配与不确定性记录' if cn else 'Correspondences and aligned data / validity conditions / unresolved cases',12,fill='F0F4F3',dash=False)
    d.arrow([(8,10.00),(8,10.39)])
    d.arrow([(14.7,9.70),(15.90,9.70),(15.90,5.75),(14.7,5.75)],dash=True,color='A36A53')
    d.text(.9,11.35,14,.3,'虚线反馈：存在剩余失配时，复核约束与策略' if cn else 'Dashed feedback: revisit constraints and strategy when residual mismatches require revision',11,color='A36A53')
    return d

def walkthrough(cn=False):
    d=Diagram('Figure_4_6_Task_walkthrough_'+('CN' if cn else 'EN'),11.8)
    labels=['01  定义任务：同一输入，两类需求','02  诊断：共同空间、时间与语义条件','03  约束：面积组成与位置关系分别保留','04  组织：共享准备后形成任务分支','05  验证：检查结果并定位复核环节'] if cn else ['01  Define two tasks for the same inputs','02  Diagnose spatial, temporal and semantic conditions','03  Analyze the information required by each task','04  Organize shared preparation and task branches','05  Validate outputs and locate any required revision']
    for i,y in enumerate([.45,2.55,4.65,6.75,8.85]):d.stage(y,1.65 if i<4 else 2.4,labels[i],6.8 if cn else [6.8,9,8.4,8.7,8.7][i])
    d.box(.8,1.07,4,.75,'Han2010／2020\n24窗及共同有效域' if cn else 'Han2010 /2020\n24 windows and a common valid domain',12)
    d.box(6,1.07,4,.75,'任务A：面积统计\n两期面积、扩张、收缩、净变化' if cn else 'Task A: area accounting\nDated areas, gross and net change',12)
    d.box(10.9,1.07,3.8,.75,'任务B：变化位置\n原生网格上的扩张／收缩' if cn else 'Task B: change locations\nNative-grid expansion / contraction',12)
    d.arrow([(4.8,1.44),(6,1.44)])
    d.arrow([(5.35,1.44),(5.35,2.00),(10.65,2.00),(10.65,1.44),(10.9,1.44)])
    d.arrow([(14.7,2.10),(15.30,2.10),(15.30,3.52),(14.7,3.52)])
    diagnostics=['空间：按坐标恢复索引\n2010原点相差119行','时间：配对2010与2020\n保留真实产品状态差异','语义：21—24→SL\n保留SD与Others'] if cn else ['Spatial: coordinate-based indexing\n2010 origin offset:119 rows','Temporal: pair2010 with2020\nRetain product-state transitions','Semantic:21–24→SL\nKeep SD and Others']
    for x,t in zip([.8,5.65,10.5],diagnostics):d.box(x,3.13,4.2,.78,t,12)
    d.arrow([(8,4.20),(8,4.40),(.53,4.40),(.53,5.63),(.8,5.63)])
    d.arrow([(8,4.40),(15.30,4.40),(15.30,5.63),(14.7,5.63)])
    d.box(.8,5.24,6.65,.78,'面积：单期组成＋跨期转移比例\n先建立原生转移，再按支持域汇总' if cn else 'Area: composition + paired-transition fractions\nEstablish native transitions before aggregation',12)
    d.box(8.05,5.24,6.65,.78,'位置：保留同一像元的跨期对应\n优势类别不能恢复格内变化位置' if cn else 'Location: retain native pixel correspondence\nDominant labels do not retain within-cell locations',12)
    d.arrow([(4.3,6.30),(4.3,6.45),(.53,6.45),(.53,7.73),(.8,7.73)])
    d.arrow([(11.65,6.30),(11.65,7.34)])
    d.box(.8,7.34,6.65,.78,'面积输出：3×3／10×10／30×30比例\n有效面积加权→面积与变化统计表' if cn else 'Area output: fractions on3×3 /10×10 /30×30 supports\nValid-area weighting→area and turnover tables',12)
    d.box(8.05,7.34,6.65,.78,'位置输出：原生SL扩张／收缩图\n粗尺度结果另作位置损失诊断' if cn else 'Location output: native SL expansion / contraction\nCoarse-support maps retained for loss diagnostics',12)
    d.arrow([(4.3,8.40),(4.3,8.55),(.53,8.55),(.53,9.81),(.8,9.81)])
    d.arrow([(11.65,8.40),(11.65,9.45)])
    d.box(.8,9.45,6.65,.72,'面积核验：语义守恒、比例积分、转移收支\n24窗最大残差2.27×10⁻⁷m²' if cn else 'Area checks: semantic mass, integration, transition balance\nMaximum residual:2.27×10⁻⁷m² across24 windows',11)
    d.box(8.05,9.45,6.65,.72,'位置核验：SL成员差分逐像元一致\nF1／IoU／覆盖率记录粗化损失' if cn else 'Location checks: exact SL-membership subtraction\nF1 / IoU / coverage describe coarse-support loss',11)
    d.box(3.15,10.55,9.7,.47,'交付：比例栅格、方向变化图、任务表与决策记录' if cn else 'Deliver: fraction grids, directional change maps, task tables and decision records',12,fill='F0F4F3',dash=False)
    d.arrow([(4.3,10.17),(4.3,10.55)]);d.arrow([(11.65,10.17),(11.65,10.55)])
    d.arrow([(14.7,9.8),(15.9,9.8),(15.9,5.63),(14.7,5.63)],dash=True,color='A36A53')
    d.text(.9,11.42,14,.25,'条件反馈：若检查失败，返回对应步骤；本次未触发数值修复' if cn else 'Conditional feedback only: return to the implicated step if checks fail; no numerical repair was triggered in this run',10,color='A36A53')
    return d

def combined_sampling(d):
    e=pd.read_csv(ROOT/'selection/candidates.csv');e=e[e.reason=='eligible'];q=load(ROOT/'selection/thresholds.json');sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv').sort_values('display_id')
    fig=plt.figure(figsize=(16,16),constrained_layout=True);gs=fig.add_gridspec(2,2,height_ratios=[.90,1]);d.mpl(fig.add_subplot(gs[0,:]));ax=fig.add_subplot(gs[1,0]);bars=fig.add_subplot(gs[1,1])
    lo,hi=q['Q25'],q['Q75'];ax.hist(e.H_SL,bins=np.linspace(0,2,31),color='#aeb8bb',edgecolor='white');ax.axvspan(0,lo,color='#377eb8',alpha=.13);ax.axvspan(hi,2,color='#d56546',alpha=.13)
    for v,col,label in [(lo,'#377eb8',f'Q25={lo:.6f}\nLow:179'),(hi,'#d56546',f'Q75={hi:.6f}\nHigh:179')]:ax.axvline(v,c=col,ls='--');ax.text(v+.02,ax.get_ylim()[1]*.92,label,va='top',color=col,fontsize=11)
    ax.plot(sel[sel.group=='Low'].H_SL,np.full(12,-1.5),'|',c='#377eb8',ms=10);ax.plot(sel[sel.group=='High'].H_SL,np.full(12,-3.5),'|',c='#d56546',ms=10);ax.set(xlim=(0,2),xlabel='Within-SL entropy (bits)',ylabel='Candidate-window count',title='(a) Entropy thresholds in the eligible pool')
    x=np.array([[getattr(r,'p'+str(k))/r.pSL for k in [21,22,23,24]] for r in sel.itertuples()]);base=np.zeros(24)
    for i,col in enumerate(['#edc85c','#a6c275','#5aa589','#287c77']):bars.barh(range(24),x[:,i],left=base,color=col,label='SL'+str(i+21));base+=x[:,i]
    bars.set(yticks=range(24),yticklabels=sel.display_id,xlim=(0,1),xlabel='Subclass fraction within SL',title='(b) Composition of the24 selected windows');bars.invert_yaxis();bars.axhline(11.5,c='#777777',lw=.8);bars.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,-.08))
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'Figure_4_2b_sampling_full_EN.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)

def replace_image(paragraph,path,width):
    for c in list(paragraph._p):
        if c.tag!=qn('w:pPr'):paragraph._p.remove(c)
    paragraph.add_run().add_picture(str(path),width=DI(width))
def insert_after(paragraph,text='',style=None):
    el=OxmlElement('w:p');paragraph._p.addnext(el);p=Paragraph(el,paragraph._parent)
    if style:p.style=style
    if text:p.add_run(text)
    return p

def main():
    source_hash=sha(SOURCE);doc=Document(SOURCE)
    body_before=[p.text for p in doc.paragraphs];tables_before=[[ [c.text for c in row.cells] for row in t.rows] for t in doc.tables]
    # Save a true snapshot after exclusive lock has been released; replaces the failed empty read snapshot.
    (ROOT/'reports/1021用户稿_只读快照.docx').write_bytes(SOURCE.read_bytes())
    for cn in [False,True]:
        for d in [framework(cn),sampling(cn),walkthrough(cn)]:d.save()
    combined_sampling(sampling(False))
    ppt=ROOT/'presentations/1021三类流程图_分阶段分区_可编辑.pptx';ppt.parent.mkdir(exist_ok=True);PRES.save(ppt)
    titles={
        '4.5':'4.5 Multidimensional Alignment: Experiments and Framework Application',
        '4.5.1':'4.5.1 Data and Sampling Design',
        '4.5.2':'4.5.2 Spatio-temporal-semantic Coupling',
        '4.5.3':'4.5.3 Non-commutativity of Alignment Operations',
        '4.5.4':'4.5.4 Task-oriented Framework Application',
        '4.5.5':'4.5.5 Synthesis and Implications'}
    changes=[]
    for p in doc.paragraphs:
        if p.style.name.startswith('Heading'):
            key=p.text.split(' ',1)[0]
            if key in titles:changes.append({'old':p.text,'new':titles[key]});p.text=titles[key]
        # Convert literal markdown bold markers into real Word formatting; wording unchanged.
        elif p.text.startswith('**'):
            text=p.text;m=re.match(r'^\*\*(.+?)\*\*(.*)$',text)
            if m:
                p.clear();p.add_run(m.group(1)).bold=True;p.add_run(m.group(2))
    cap=next(p for p in doc.paragraphs if p.text.startswith('Figure 4.2b.'))
    prev=cap._p.getprevious()
    while prev is not None and not prev.xpath('.//a:blip'):prev=prev.getprevious()
    assert prev is not None;replace_image(Paragraph(prev,cap._parent),OUT/'Figure_4_2b_sampling_full_EN.png',6.6)
    cap.text='Figure 4.2b. Sensitivity-based sampling. Dashed stage boundaries organize candidate screening, entropy-based stratification and spatial selection; solid arrows indicate processing dependencies. Panel(a) shows the original quartile thresholds and panel(b) the subclass composition of the24 selected windows.'
    intro=next(p for p in doc.paragraphs if p.text.startswith('前两个实验说明，统一网格和类别以后'))
    for p in doc.paragraphs:
        if p.text.startswith('Figure 4.6.'):p.text=p.text.replace('Figure 4.6.','Figure 4.7.',1)
        elif '图4.6展示' in p.text:p.text=p.text.replace('图4.6展示','图4.7展示')
    intro.text=intro.text+' 图4.6将共享准备、两条任务分支及验证反馈对应到五个环节。'
    pic=insert_after(intro);pic.add_run().add_picture(str(OUT/'Figure_4_6_Task_walkthrough_EN.png'),width=DI(6.6))
    capnew=insert_after(pic,'Figure 4.6. Task-oriented framework application. The area branch retains single-date composition and paired-transition fractions; the location branch retains native pixel correspondence. Dashed feedback denotes a conditional return when a check fails, rather than an iteration executed in this case.')
    for r in capnew.runs:r.font.size=Pt(10)
    # Ensure figures fit portrait text area; long diagrams are capped by page height as well as width.
    maxheight=8.2
    for sh in doc.inline_shapes:
        if sh.height/914400>maxheight:
            ratio=(maxheight*914400)/sh.height;sh.width=int(sh.width*ratio);sh.height=int(sh.height*ratio)
    output=ROOT/'reports/4.5_1021用户稿_流程图与标题优化版.docx';doc.save(output)
    new=Document(output)
    assert len(new.inline_shapes)==len(Document(SOURCE).inline_shapes)+1
    assert [[[c.text for c in row.cells] for row in t.rows] for t in new.tables]==tables_before
    # All scientific prose is preserved, except the declared introduction/caption additions and bold markup.
    allowed=lambda t:t.startswith(('4.5','Figure 4.2b.','前两个实验说明，统一网格和类别以后'))
    clean=lambda t:t.replace('**','').replace('Figure 4.6. Native','Figure 4.7. Native').replace('图4.6展示','图4.7展示')
    remaining=[clean(p.text) for p in new.paragraphs]
    for t in body_before:
        if t and not allowed(t):assert clean(t) in remaining,t
    assert '[129]' in '\n'.join(remaining) and '[130]' in '\n'.join(remaining)
    assert sha(SOURCE)==source_hash
    check=Presentation(ppt);assert len(check.slides)==6 and all(not any(sh.shape_type==13 for sh in sl.shapes) for sl in check.slides)
    dump(OUT/'verification.json',dict(time=now(),source=str(SOURCE),source_hash=source_hash,source_unchanged=True,user_citation_numbers_preserved=True,all_table_cells_preserved=True,headings=changes,word_images_before=8,word_images_after=9,ppt_slides=6,ppt_all_flowchart_objects_editable=True,figure41='Standalone replacement figure; input document contains section4.5 only',outputs=[str(output),str(ppt)]))
    (OUT/'修改说明.md').write_text('''# 1021稿流程图与标题优化

直接基于用户提供的1021稿修改，保留[129]/[130]和全部表格数据。原文件只读，新稿保存于reports。

图4.2b：重排上方流程为候选筛选、敏感性分层、空间抽样三阶段；下方实际阈值分布与样区组成继续保留。

图4.6：在4.5.4新增五步任务运行流程，区分共享条件、面积分支和位置分支；条件反馈使用虚线并注明未实际触发数值修复。原图4.6变化结果保留并顺延为图4.7，正文引用同步调整。

图4.1：提供独立的整体框架替换图，仍保留原五步结构及顺序/迭代/联合/层级方式。用户文件仅含4.5，故未将4.1插入错误章节。

三个流程各提供英文/中文PNG、PDF、SVG，以及6页原生可编辑PPT。示例的分区边框和标题标签用于组织图示，不照搬其算法、循环或背景网格。

新小标题：Data and Sampling Design；Spatio-temporal-semantic Coupling；Non-commutativity of Alignment Operations；Task-oriented Framework Application；Synthesis and Implications。

流程图的所有矩形、标签及连线均为PPT原生对象。图4.2b完整统计图以原始表重绘，实验数据和抽样规则未变。
''',encoding='utf8')
    print('User1021 document updated in new copy. Six editable flowchart slides and three bilingual diagram sets generated.')
if __name__=='__main__':main()
