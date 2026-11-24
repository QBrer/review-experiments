"""Merge study/sensitivity maps and all noncommutativity panels; preserve source data."""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Rectangle
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from rasterio.enums import Resampling
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from pptx import Presentation
from pptx.util import Inches as PI,Pt as PPt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE,XL_LEGEND_POSITION
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.dml.color import RGBColor

OUT=ROOT/'figures/merged_1021';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'reports/4.5_1021用户稿_流程图与标题优化版.docx'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none'})
def save(fig,name):
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=260,bbox_inches='tight')
    plt.close(fig)
def mapaxes(ax):ax.set(xlim=(87.5,126.5),ylim=(37.1,53.9),xlabel='Longitude (°E)',ylabel='Latitude (°N)');ax.grid(alpha=.16);ax.set_axisbelow(True)
def main():
    protected={str(p):sha(p) for p in [SOURCE,ROOT/'selection/candidates.csv',ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/review_multiscale_order/phase_all_scales.csv']}
    sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv');cand=pd.read_csv(ROOT/'selection/candidates.csv');e=cand[cand.reason=='eligible'].copy();q=load(ROOT/'selection/thresholds.json')
    e['group']=np.where(e.H_SL<=q['Q25'],'Low',np.where(e.H_SL>=q['Q75'],'High','Middle'))
    ds=open_inputs();tr=ds['H2020'].transform
    fig=plt.figure(figsize=(16,12),constrained_layout=True);gs=fig.add_gridspec(2,2,height_ratios=[.7,1.2]);axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    palettes={'W2020':['39734C','86A65C','B6D19D','A0B38B','D7CA7F','D6B89A','67B5A6','5A91B5','DDBAA4','BC858A','C6C1B5','DFC888','E9C459','D5E0E8'],'H2020':['DFB15D','E8CF7F','B4C88F','81AF88','418676','DBE2DC']}
    for ax,key,codes,title in [(axes[0],'W2020',list(range(1,15)),'(a) Wang2020: land-cover context'),(axes[1],'H2020',[1,21,22,23,24,3],'(b) Han2020: sandy-land subclasses')]:
        src=ds[key];W=1800;H=round(W*src.height/src.width);a=src.read(1,out_shape=(H,W),resampling=Resampling.nearest);z=np.full(a.shape,len(codes),np.uint8)
        for i,c in enumerate(codes):z[a==c]=i
        bounds=src.bounds;ax.imshow(z,cmap=ListedColormap(['#'+c for c in palettes[key]]+['white']),vmin=-.5,vmax=len(codes)+.5,extent=[bounds.left,bounds.right,bounds.bottom,bounds.top],origin='upper',interpolation='nearest')
        mapaxes(ax);ax.set_title(title,loc='left',fontweight='bold');names=[str(c) for c in codes] if key=='W2020' else ['SD','SL21','SL22','SL23','SL24','Others']
        ax.legend(handles=[Patch(facecolor='#'+c,label=l) for c,l in zip(palettes[key],names)],loc='upper left',ncol=7 if key=='W2020' else 3,fontsize=7,framealpha=.95,title='Source class codes' if key=='W2020' else None)
        if key=='W2020':coverage=(a>=1)&(a<=14);wb=bounds
    ax=axes[2];ax.imshow(coverage.astype(np.uint8),cmap=ListedColormap(['white','#edf0ed']),vmin=0,vmax=1,extent=[wb.left,wb.right,wb.bottom,wb.top],origin='upper',interpolation='nearest')
    colors={'Low':'#277bb6','High':'#d95336','Middle':'#c6cbc8'}
    for group in ['Middle','Low','High']:
        patches=[]
        for r in e[e.group==group].itertuples():
            x,y=tr*(r.col,r.row);xx,yy=tr*(r.col+1200,r.row+1200);patches.append(Rectangle((x,yy),xx-x,y-yy))
        ax.add_collection(PatchCollection(patches,facecolor=colors[group],edgecolor='white',linewidth=.22))
    for r in sel.itertuples():
        ax.scatter(r.lon,r.lat,s=34,marker='o',facecolors='none',edgecolors='#253746',lw=1.1,zorder=4)
        ax.annotate(r.display_id,(r.lon,r.lat),xytext=(4,4),textcoords='offset points',fontsize=8,color='#253746',bbox=dict(fc='white',ec='none',alpha=.8,pad=.3))
    mapaxes(ax);ax.set_title('(c) Sensitivity candidates and selected experimental windows',loc='left',fontweight='bold')
    ax.legend(handles=[Patch(facecolor=colors['Low'],label='Low:179 candidates'),Patch(facecolor=colors['High'],label='High:179 candidates'),Patch(facecolor=colors['Middle'],label='Middle:356 candidates'),Line2D([],[],color='none',marker='o',markerfacecolor='none',markeredgecolor='#253746',label='Selected:12 Low +12 High')],loc='upper left',fontsize=9,framealpha=.96)
    fig.supxlabel('Candidate rectangles use the original window footprints; the background shows product coverage, not a physiographic boundary.',fontsize=9)
    save(fig,'Figure_4_2a_Products_and_sensitivity')
    for d in ds.values():d.close()
    order=pd.read_csv(ROOT/'results/experiment_2/order.csv');order=order[order.group.isin(['Low','High'])].merge(sel[['id','display_id','H_SL']],left_on='site',right_on='id')
    phase=pd.read_csv(ROOT/'results/review_multiscale_order/phase_all_scales.csv')
    exact=order.pivot(index=['group','display_id'],columns='scale',values='R_NC_count')*100;exact.columns=['3x3_percent','10x10_percent','30x30_percent'];exact.reset_index().to_csv(OUT/'Figure_4_4_逐样区数值.csv',index=False,encoding='utf-8-sig')
    fig=plt.figure(figsize=(17,15),constrained_layout=True);gs=fig.add_gridspec(3,6,height_ratios=[1.15,1,1]);lineaxes=[fig.add_subplot(gs[0,:3]),fig.add_subplot(gs[0,3:])]
    palette=['#0068b7','#b65b00','#267f2d','#c72c41','#8047a8','#795548','#b63b91','#4f5d67','#7e8100','#007f8b','#204786','#9a5d00'];markers=['o','s','^','D','v','P','X','<','>','h','p','*']
    for ax,group,panel in zip(lineaxes,['Low','High'],['a','b']):
        g=order[order.group==group];top=float(g.R_NC_count.max()*100);maxy=max(.25,top*1.20);ax.set_ylim(-.02*maxy,maxy)
        labels=[]
        for i,(label,gg) in enumerate(g.sort_values('display_id').groupby('display_id',sort=True)):
            gg=gg.sort_values('scale');vals=gg.R_NC_count.to_numpy()*100
            ax.plot([3,10,30],vals,ls='--',marker=markers[i],lw=1.35,ms=4.5,color=palette[i],alpha=1,zorder=2)
            labels.append(dict(label=label,val=vals[-1],color=palette[i]))
        mean=g.groupby('scale').R_NC_count.mean().reindex([3,10,30])*100
        ax.plot([3,10,30],mean,'k-o',lw=2.5,ms=6,label='Group mean',zorder=5)
        # Endpoint labels are vertically separated; leader lines retain true point positions.
        labels=sorted(labels,key=lambda r:r['val']);yp=np.array([r['val'] for r in labels]);gap=maxy*.055
        for i in range(1,len(yp)):yp[i]=max(yp[i],yp[i-1]+gap)
        if yp[-1]>maxy*.94:yp-=yp[-1]-maxy*.94
        if yp[0]<maxy*.015:yp=np.linspace(maxy*.015,maxy*.94,len(yp))
        for yy,r in zip(yp,labels):
            ax.annotate(f"{r['label']}  {r['val']:.3f}%",xy=(30,r['val']),xytext=(34,yy),fontsize=8,color=r['color'],va='center',arrowprops=dict(arrowstyle='-',color=r['color'],lw=.7))
        for x,y in zip([3,10,30],mean):ax.annotate(f'{y:.3f}%',(x,y),xytext=(0,10),textcoords='offset points',ha='center',fontsize=9,fontweight='bold',bbox=dict(fc='white',ec='none',alpha=.85,pad=.5))
        ax.set(xlim=(1,48),xticks=[3,10,30],xticklabels=['3×3','10×10','30×30'],xlabel='Spatial support (native pixels)',ylabel='Non-commutative cells (%)',title=f'({panel}) {group}: individual windows and mean');ax.grid(axis='y',alpha=.18);ax.legend(loc='upper left',fontsize=9)
    for j,f in enumerate([3,10,30]):
        ax=fig.add_subplot(gs[1,2*j:2*j+2])
        for group,color in [('Low','#277bb6'),('High','#d95336')]:
            g=order[(order.scale==f)&(order.group==group)];ax.scatter(g.H_SL,100*g.R_NC_count,label=group,color=color,s=33)
        ax.set(xlabel='Within-SL entropy (bits)',ylabel='Non-commutative cells (%)',title=f'({chr(99+j)}) {f}×{f}: composition and disagreement');ax.legend(fontsize=9)
        bx=fig.add_subplot(gs[2,2*j:2*j+2]);vals=[phase[(phase.scale==f)&(phase.group==g)].groupby('site').R_NC_count.agg(lambda x:100*(x.max()-x.min())).values for g in ['Low','High']]
        bx.boxplot(vals,labels=['Low','High'],patch_artist=False);bx.set(ylabel='Nine-phase range (percentage points)',title=f'({chr(102+j)}) {f}×{f}: phase sensitivity')
    fig.supxlabel('Dashed lines: individual windows; black solid lines: group means. Endpoint labels show 30×30 values.\nTop-panel y-axis ranges differ between groups. Exact values at all supports are supplied in the figure data table.',fontsize=10)
    save(fig,'Figure_4_4_Combined_dashed_windows')
    # A clean full-size numerical companion retains every point, not only endpoint labels.
    fig,axes=plt.subplots(1,2,figsize=(12,5.8),constrained_layout=True)
    for ax,group in zip(axes,['Low','High']):
        ax.axis('off');g=exact.loc[group].sort_index();rows=[[label]+[f'{v:.6f}' for v in row] for label,row in g.iterrows()]
        mean=order[order.group==group].groupby('scale').R_NC_count.mean().reindex([3,10,30])*100;rows.append(['Mean']+[f'{v:.6f}' for v in mean])
        tb=ax.table(cellText=rows,colLabels=['Window','3×3 (%)','10×10 (%)','30×30 (%)'],loc='center',cellLoc='center');tb.auto_set_font_size(False);tb.set_fontsize(11);tb.scale(1,1.8);ax.set_title(group,fontweight='bold')
    save(fig,'Figure_4_4_Window_value_table')
    edit_doc();editable_lines(order,exact)
    assert all(sha(path)==h for path,h in protected.items())
    dump(OUT/'validation.json',dict(time=now(),counts={'Low':179,'High':179,'Middle':356,'selected':24},line_series=24,values_exported=72,all_individual_lines_dashed_opaque=True,group_means_solid=True,original_data_and_doc_unchanged=True,protected=protected))
    print('Merged figures, per-window dashed lines and data table, editable line-chart PPT and revised Word completed.')

def replace_previous_image(cap,path):
    el=cap._p.getprevious()
    while el is not None and not el.xpath('.//a:blip'):el=el.getprevious()
    assert el is not None;p=Paragraph(el,cap._parent)
    for child in list(el):
        if child.tag!=qn('w:pPr'):el.remove(child)
    shape=p.add_run().add_picture(str(path),width=Inches(6.6))
    if shape.height/Inches(1)>8.0:
        ratio=Inches(8.0)/shape.height;shape.width=int(shape.width*ratio);shape.height=Inches(8.0)
def edit_doc():
    d=Document(SOURCE);original=Document(SOURCE)
    ca=next(p for p in d.paragraphs if p.text.startswith('Figure 4.2a.'));replace_previous_image(ca,OUT/'Figure_4_2a_Products_and_sensitivity.png')
    ca.text='Figure 4.2a. Study products, sensitivity candidates and selected windows. Panels(a) and(b) show Wang2020 and Han2020. Panel(c) maps179 Low,179 High and356 middle-stratum candidates; circles identify the24 selected windows. Candidate footprints retain the original1200×1200 grid. Unclassified background denotes product coverage only.'
    a=next(p for p in d.paragraphs if p.text.startswith('Figure 4.4a.'));replace_previous_image(a,OUT/'Figure_4_4_Combined_dashed_windows.png')
    a.text='Figure 4.4. Non-commutativity across supports, composition and grid phases. Panels(a,b): individual windows as opaque dashed lines, group means as black solid lines; endpoint labels give30×30 rates. Panels(c–e): within-SL entropy and disagreement at3×3,10×10 and30×30. Panels(f–h): nine-phase ranges. Top-panel vertical scales differ; exact values for all72 points accompany the figure.'
    b=next(p for p in d.paragraphs if p.text.startswith('Figure 4.4b.'));prev=b._p.getprevious()
    while prev is not None and not prev.xpath('.//a:blip'):prev=prev.getprevious()
    assert prev is not None;prev.getparent().remove(prev);b._p.getparent().remove(b._p)
    for p in d.paragraphs:
        t=p.text
        if '表4.3、图4.4a' in t:p.text=t.replace('表4.3、图4.4a','表4.3、图4.4（a、b）')
        elif t.startswith('图4.4b上排'):
            p.text='图4.4（a、b）以清晰虚线展示各样区在三个支持域上的数值，黑色实线表示组均值，右侧标签标明各样区的30×30非交换率。图4.4（c—e）将窗口的H_SL与三个尺度的非交换率对应；图4.4（f—h）报告九种网格相位在共同内部范围产生的变化幅度。每个样区的三尺度精确值另附数据表。'
    out=ROOT/'reports/4.5_1021用户稿_分布图与非交换图合并版.docx';d.save(out)
    check=Document(out);assert len(check.inline_shapes)==len(original.inline_shapes)-1
    assert [[[c.text for c in r.cells] for r in t.rows] for t in check.tables]==[[[c.text for c in r.cells] for r in t.rows] for t in original.tables]
    assert '[129]' in '\n'.join(p.text for p in check.paragraphs)

def editable_lines(order,exact):
    p=Presentation();p.slide_width=PI(16);p.slide_height=PI(9)
    for group in ['Low','High']:
        s=p.slides.add_slide(p.slide_layouts[6]);tf=s.shapes.add_textbox(PI(.5),PI(.2),PI(15),PI(.6)).text_frame;tf.text=group+' | Individual windows: dashed lines; mean: solid black';tf.paragraphs[0].font.size=PPt(23)
        cd=CategoryChartData();cd.categories=['3×3','10×10','30×30']
        g=order[order.group==group]
        for label,w in g.sort_values('display_id').groupby('display_id'):cd.add_series(label,(w.set_index('scale').loc[[3,10,30],'R_NC_count']*100).tolist())
        cd.add_series('Mean',(g.groupby('scale').R_NC_count.mean().reindex([3,10,30])*100).tolist())
        ch=s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS,PI(.6),PI(1),PI(9.5),PI(7),cd).chart;ch.has_legend=True;ch.legend.position=XL_LEGEND_POSITION.BOTTOM
        for i,series in enumerate(ch.series):
            if i<12:
                series.format.line.dash_style=MSO_LINE_DASH_STYLE.DASH;series.format.line.width=PPt(1.5)
                cols=['0068B7','B65B00','267F2D','C72C41','8047A8','795548','B63B91','4F5D67','7E8100','007F8B','204786','9A5D00'];series.format.line.color.rgb=RGBColor.from_string(cols[i])
            else:series.format.line.width=PPt(3);series.format.line.color.rgb=RGBColor(0,0,0)
        g=exact.loc[group].sort_index();table=s.shapes.add_table(14,4,PI(10.3),PI(1.25),PI(5.2),PI(6.5)).table
        values=[['Window','3×3 (%)','10×10 (%)','30×30 (%)']]+[[label]+[f'{v:.6f}' for v in row] for label,row in g.iterrows()]+[['Mean']+[f'{v:.6f}' for v in (order[order.group==group].groupby('scale').R_NC_count.mean().reindex([3,10,30])*100)]]
        for i,row in enumerate(values):
            for j,value in enumerate(row):table.cell(i,j).text=value
        for row in table.rows:
            for c in row.cells:
                for para in c.text_frame.paragraphs:para.font.size=PPt(12)
        s.notes_slide.notes_text_frame.text='Native editable chart and table; embedded workbook contains all original per-window percentages. No opacity applied to individual lines.'
    dest=ROOT/'presentations/图4.4_逐样区虚线与完整数值_可编辑.pptx';p.save(dest)

if __name__=='__main__':main()
