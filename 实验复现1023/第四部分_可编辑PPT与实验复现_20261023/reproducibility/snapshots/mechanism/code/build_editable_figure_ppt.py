from core import *
import pandas as pd
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.chart import XL_CHART_TYPE,XL_LEGEND_POSITION
from pptx.chart.data import CategoryChartData,XyChartData
from PIL import Image
import io

OUT=ROOT/'presentations';OUT.mkdir(exist_ok=True)
P=Presentation();P.slide_width=Inches(16);P.slide_height=Inches(9)
COL=['D9A03B','37866F','EAE9E4','555555'];audit=[]
def txt(s,text,x,y,w,h=.35,size=15,color='23364A',bold=False):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.word_wrap=True
    for i,line in enumerate(str(text).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.size=Pt(size);p.font.name='Arial';p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
    return sh
def rect(s,x,y,w,h,color,line=None):
    sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(color)
    if line:sh.line.color.rgb=RGBColor.from_string(line)
    else:sh.line.fill.background()
    return sh
def line(s,x,y,xx,yy,color='657487',width=1):
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x),Inches(y),Inches(xx),Inches(yy));sh.line.color.rgb=RGBColor.from_string(color);sh.line.width=Pt(width);return sh
def slide(title,source,mode):
    s=P.slides.add_slide(P.slide_layouts[6]);txt(s,title,.45,.2,15,.55,24,bold=True);line(s,.45,.87,15.5,.87,'D7E0E8')
    txt(s,mode,.45,8.55,15,.3,10,'627083');s.notes_slide.notes_text_frame.text='Source: '+source+'\nEditability: '+mode
    audit.append(dict(slide=len(P.slides),title=title,source=source,editability=mode));return s
def legend(s,labels,colors,x=.7,y=8.0):
    for i,(lab,col) in enumerate(zip(labels,colors)):rect(s,x+i*2.7,y,.18,.18,col);txt(s,lab,x+.26+i*2.7,y-.04,2.4,.35,12)
def map_panel(s,a,x,y,w,h,title,colors=COL,vector=False):
    txt(s,title,x,y-.34,w,.3,13,bold=True)
    if vector:
        # Same-color horizontal runs become native editable rectangles, no pixel resampling.
        group=s.shapes.add_group_shape();H,W=a.shape
        for r in range(H):
            start=0
            for c in range(1,W+1):
                if c==W or a[r,c]!=a[r,start]:
                    sh=group.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x+start/W*w),Inches(y+r/H*h),max(1,int(Inches((c-start)/W*w))),max(1,int(Inches(h/H))))
                    sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(colors[int(a[r,start])]);sh.line.fill.background();start=c
        group.name=title+' | editable cell runs'
    else:
        palette=np.array([tuple(bytes.fromhex(c)) for c in colors],np.uint8);im=Image.fromarray(palette[a]);bio=io.BytesIO();im.save(bio,format='PNG');bio.seek(0)
        sh=s.shapes.add_picture(bio,Inches(x),Inches(y),width=Inches(w),height=Inches(h));sh.name=title+' | exact categorical raster'
    for xx,yy,v in [(x,y+h,'0'),(x+w-.35,y+h,'1200')]:txt(s,v,xx,yy,.55,.2,9)
    txt(s,'Native-grid column / row offsets',x,y+h+.22,w,.25,10)
def coded(a):
    z=np.full(a.shape,3,np.uint8)
    for c in [1,2,3]:z[a==c]=c-1
    return z
def chartstyle(chart):
    chart.has_legend=True;chart.legend.position=XL_LEGEND_POSITION.BOTTOM
    chart.chart_style=10
    for ax in [chart.category_axis,chart.value_axis]:ax.tick_labels.font.size=Pt(10)

def main():
    s=slide('Figure 4.1 | Integrated alignment framework','Original manuscript Figure4.1','All boxes, text and connecting lines are editable PowerPoint objects.')
    rect(s,.7,1.2,14.5,1.05,'EDF3F7','A8BAC9')
    for x,t in [(1,'01  Define the task\nObjective and intended use'),(6,'Alignment objects\nPixels · entities · events · concepts'),(11,'Correspondence requirements\nRelations · acceptance criteria')]:txt(s,t,x,1.35,4.1,.8,17,bold=True)
    titles=['02  Diagnose mismatches','03  Analyze constraints','04  Organize alignment','05  Validate alignment']
    bodies=['Spatial\nPosition · geometry · topology\n\nTemporal\nTime · process stage\n\nSemantic\nConcepts · classes','Spatial ↔ Temporal ↔ Semantic\n\nCoupling\n\nDependencies · conflicts\n\nOperation order','Sequential — dependencies\n\nIterative — feedback\n\nJoint — shared constraints\n\nHierarchical — nested levels','Correspondence validity\n\nCross-dimensional consistency\n\nTask-specific fitness for use']
    for i in range(4):
        x=.7+i*3.75;rect(s,x,2.9,3.25,3.65,'F7F9FB','A8BAC9');txt(s,titles[i],x+.14,3.05,3,.65,17,bold=True);txt(s,bodies[i],x+.16,3.85,2.95,2.6,14)
        if i<3:line(s,x+3.25,4.5,x+3.68,4.5);txt(s,'→',x+3.27,4.22,.4,.4,22)
    line(s,1.1,2.25,1.1,2.85);txt(s,'Task-guided analysis',1.35,2.43,3,.3,12)
    line(s,13.5,6.6,13.5,7);line(s,13.5,7,5.7,7);line(s,5.7,7,5.7,6.6);txt(s,'Residual mismatches: refine constraints and strategy',5.5,7.05,8,.3,13,'A86736')
    rect(s,.7,7.65,14.5,.7,'E9F2F0','A8C3BB');txt(s,'Alignment outputs     |     Correspondences and aligned data',1,7.78,13,.35,17,bold=True)
    # Study maps: exact background images plus editable region markers and labels.
    sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv');ds=open_inputs()
    palettes={'W2020':['39734C','86A65C','B6D19D','A0B38B','D7CA7F','D6B89A','67B5A6','5A91B5','DDBAA4','BC858A','C6C1B5','DFC888','E9C459','D5E0E8'],'H2020':['DFB15D','E8CF7F','B4C88F','81AF88','418676','DBE2DC']}
    from rasterio.enums import Resampling
    for key,codes in [('W2020',list(range(1,15))),('H2020',[1,21,22,23,24,3])]:
        s=slide('Figure 4.2 | '+('Wang2020 land-cover context' if key=='W2020' else 'Han2020 and selected regions'),'Figure_4_2_Study_regions','Raster background retained; region outlines, markers, labels and legends are editable.')
        src=ds[key];a=src.read(1,out_shape=(800,1900),resampling=Resampling.nearest);z=np.full(a.shape,len(codes),np.uint8)
        for i,c in enumerate(codes):z[a==c]=i
        x,y,w,h=1.1,1.4,13.6,5.7;pal=palettes[key]+['FFFFFF'];map_panel(s,z,x,y,w,h,'',pal)
        b=src.bounds
        for r in sel.itertuples():
            px=x+(r.lon-b.left)/(b.right-b.left)*w;py=y+(b.top-r.lat)/(b.top-b.bottom)*h;color='B42A43' if r.group=='High' else '175FA2'
            sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(px-.035),Inches(py-.035),Inches(.07),Inches(.07));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor.from_string(color);sh.line.fill.background();txt(s,r.display_id,px+.05,py-.15,.6,.2,9,color)
        labels=[str(c) for c in codes] if key=='W2020' else ['SD','SL21','SL22','SL23','SL24','Others']
        for i,(lab,col) in enumerate(zip(labels,pal)):
            xx=.8+(i%7)*2.05;yy=7.65+(i//7)*.35;rect(s,xx,yy,.16,.16,col);txt(s,lab,xx+.22,yy-.04,1.7,.25,11)
        txt(s,'High: H01–H12    Low: L01–L12',1.1,1.0,10,.3,12)
        # Cover generic pixel tick labels: geographic bounds printed explicitly.
        rect(s,.9,7.1,14.3,.52,'FFFFFF');txt(s,f'Longitude {b.left:.2f}°E – {b.right:.2f}°E     Latitude {b.bottom:.2f}°N – {b.top:.2f}°N',1.1,7.18,13,.3,12)
    for d in ds.values():d.close()
    c=pd.read_csv(ROOT/'results/experiment_1/coupling.csv')
    s=slide('Figure 4.3 | Temporal–spatial–semantic coupling','results/experiment_1/coupling.csv','Heatmap cells, values, axis labels and color key are native editable shapes/text.')
    import matplotlib.cm as cm
    for i,g in enumerate(['Low','High']):
        for j,year in enumerate([2015,2010,2000]):
            x=.9+j*5;y=1.6+i*3.05;txt(s,f'{g}: {year}–2020',x,y-.5,4,.3,17,bold=True)
            v=c[(c.group==g)&(c.start_year==year)].groupby(['semantic','scale']).F1.mean()
            for rr,sem in enumerate(['fine6','coarse3']):
                txt(s,sem,x-.7,y+rr*.8,.7,.4,10)
                for cc,f in enumerate([3,10,30]):
                    val=1-v[sem,f];rgb=cm.magma(val)[:3];color=''.join(f'{round(q*255):02X}' for q in rgb);rect(s,x+cc*1.25,y+rr*.8,1.25,.8,color);txt(s,f'{val:.3f}',x+cc*1.25+.36,y+rr*.8+.22,.8,.35,17,'FFFFFF')
            for cc,f in enumerate([3,10,30]):txt(s,f'{f}×{f}',x+cc*1.25+.35,y+1.7,.9,.3,12)
    txt(s,'Values: mean (1 − area-weighted change F1), fixed range 0–1',.9,8.0,14,.3,14)
    order=pd.read_csv(ROOT/'results/experiment_2/order.csv');order=order[order.group.isin(['Low','High'])]
    s=slide('Figure 4.4a | Non-commutativity across spatial supports','results/experiment_2/order.csv','Native PowerPoint line chart with embedded worksheet: Edit Data changes values and lines.')
    data=CategoryChartData();data.categories=['3×3','10×10','30×30']
    groups=[]
    for sid,g in order.groupby('site'):data.add_series(sid,(g.set_index('scale').loc[[3,10,30],'R_NC_count']*100).tolist());groups.append(g.group.iloc[0])
    for group in ['Low','High']:data.add_series(group+' mean',(order[order.group==group].groupby('scale').R_NC_count.mean().reindex([3,10,30])*100).tolist())
    chart=s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS,Inches(.9),Inches(1.2),Inches(14),Inches(6.6),data).chart;chartstyle(chart);chart.has_legend=False
    for i,series in enumerate(chart.series):
        group=groups[i] if i<24 else ['Low','High'][i-24];color=('B9D1E4' if group=='Low' else 'EACABF') if i<24 else ('357BAB' if group=='Low' else 'D5643D');series.format.line.color.rgb=RGBColor.from_string(color);series.format.line.width=Pt(.7 if i<24 else 3)
    chart.value_axis.has_title=True;chart.value_axis.axis_title.text_frame.text='Non-commutative cells (%)';legend(s,['Low mean','High mean'],['357BAB','D5643D'])
    s=slide('Figure 4.4b | Mixing and non-commutativity at three supports','order.csv + region_index.csv','Three native PowerPoint XY charts; all points and underlying data editable.')
    for j,f in enumerate([3,10,30]):
        data=XyChartData();merged=order[order.scale==f].merge(sel[['id','H_SL']],left_on='site',right_on='id')
        for group in ['Low','High']:
            ss=data.add_series(group)
            for r in merged[merged.group==group].itertuples():ss.add_data_point(float(r.H_SL),float(r.R_NC_count*100))
        ch=s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER,Inches(.5+j*5.15),Inches(1.6),Inches(4.9),Inches(5.7),data).chart;chartstyle(ch);txt(s,f'{f}×{f} support',1+j*5.15,1.05,4,.35,18,bold=True)
    txt(s,'X: within-SL entropy (bits)     Y: non-commutative cells (%)',.8,7.8,14,.35,14)
    phase=pd.read_csv(ROOT/'results/review_multiscale_order/phase_all_scales.csv')
    s=slide('Figure 4.4b | Nine-phase range at three supports','results/review_multiscale_order/phase_all_scales.csv','Editable box/whisker shapes; quartiles use original window-level phase ranges. Data in notes.')
    for j,f in enumerate([3,10,30]):
        vals=[phase[(phase.scale==f)&(phase.group==g)].groupby('site').R_NC_count.agg(lambda x:100*(x.max()-x.min())).to_numpy() for g in ['Low','High']];maximum=max(np.max(v) for v in vals)*1.15
        x=.9+j*5.1;y=1.7;h=5.4;txt(s,f'{f}×{f} support',x,1.08,4,.35,18,bold=True);line(s,x,y,x,y+h);line(s,x,y+h,x+4,y+h)
        def Y(v):return y+h-h*v/maximum
        for tick in np.linspace(0,maximum,6):txt(s,f'{tick:.3g}',x-.55,Y(tick)-.1,.5,.25,10);line(s,x,Y(tick),x+4,Y(tick),'E3E8ED')
        for i,v in enumerate(vals):
            q1,med,q3=np.quantile(v,[.25,.5,.75]);iqr=q3-q1;lo=v[v>=q1-1.5*iqr].min();hi=v[v<=q3+1.5*iqr].max();xx=x+1.1+i*1.7
            line(s,xx,Y(lo),xx,Y(hi));line(s,xx-.23,Y(lo),xx+.23,Y(lo));line(s,xx-.23,Y(hi),xx+.23,Y(hi));rect(s,xx-.34,Y(q3),.68,max(.002,Y(q1)-Y(q3)),'FFFFFF','394C5E');line(s,xx-.34,Y(med),xx+.34,Y(med),'E2702D',2)
            for val in v[(v<lo)|(v>hi)]:sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(xx-.04),Inches(Y(val)-.04),Inches(.08),Inches(.08));sh.fill.background();sh.line.color.rgb=RGBColor(0,0,0)
            txt(s,['Low','High'][i],xx-.4,y+h+.15,.9,.3,13)
        s.notes_slide.notes_text_frame.text+=f'\nFactor{f} Low={vals[0].tolist()} High={vals[1].tolist()}'
    txt(s,'Y: across-phase range in percentage points; each group contains 12 windows.',.9,8,14,.3,13)
    for label in ['H01','L01']:
        for f in [3,10,30]:
            s=slide(f'Figure 4.5 | {label} — {f}×{f}: two orders and disagreement','results/review_multiscale_order/rasters/'+label,'30×30 cells are editable rectangle groups (ungroup to edit); 3/10 rasters preserve exact pixels. Labels/legends editable.')
            root=ROOT/'results/review_multiscale_order/rasters'/label
            for j,name in enumerate(['semantic_first','spatial_first','difference']):
                with rasterio.open(root/f'{name}_f{f}.tif') as src:a=src.read(1)
                z=coded(a) if j<2 else np.where(a==255,2,a).astype(np.uint8);pal=COL if j<2 else ['F1F1ED','DF2438','555555']
                map_panel(s,z,.7+j*5.15,1.8,4.65,4.65,['Semantic then spatial','Spatial then semantic','Red: disagreement'][j],pal,vector=f==30)
            legend(s,['SD','SL','Others','Disagreement','Unresolved'],['D9A03B','37866F','EAE9E4','DF2438','555555'],x=.7,y=7.8)
    # Figure4.6: exact maps regenerated from the already saved classification supports.
    for label in ['H01','L01']:
        s=slide('Figure 4.6 | '+label+' — task change and spatial supports','results/region_walkthrough_24/rasters/'+label,'Native/3/10 spatial maps are exact rasters;30×30 map is editable cell rectangles; text/legend editable.')
        root=ROOT/'results/region_walkthrough_24/rasters'/label
        with rasterio.open(root/'SL_directional_change_2010_2020.tif') as src:native=src.read(1)
        for j,f in enumerate([1,3,10,30]):
            if f==1:z=native
            else:
                with rasterio.open(root/f'classes_2010_f{f}.tif') as src:a=src.read(1)
                with rasterio.open(root/f'classes_2020_f{f}.tif') as src:b=src.read(1)
                z=np.zeros(a.shape,np.uint8);z[(a!=2)&(b==2)]=1;z[(a==2)&(b!=2)]=2;z[(a==255)|(b==255)]=255
            z=np.where(z==255,3,z).astype(np.uint8);map_panel(s,z,.6+j*3.9,2.1,3.6,3.6,'Native output' if f==1 else f'{f}×{f} diagnostic',['EFEFEA','2084A0','BD4D59','555555'],vector=f==30)
        legend(s,['No SL change','Expansion','Contraction','Unresolved'],['EFEFEA','2084A0','BD4D59','555555'],x=1,y=7.6)
    dest=OUT/'第四部分_全部图_可编辑版.pptx';P.save(dest)
    check=Presentation(dest);assert len(check.slides)==15
    charts=sum(sh.has_chart for sl in check.slides for sh in sl.shapes)
    assert charts==4
    dump(OUT/'editable_figures_manifest.json',dict(slides=audit,native_chart_count=charts,source_document='第四部分_任务决策与运行记录_恢复折线图.docx',all8_word_images_covered=True,limitations='Native-resolution categorical rasters are not millions of individual editable shapes; editable overlays and coarse-cell vector groups supplied.'))
    (OUT/'可编辑说明.md').write_text('''# PPT编辑说明

包含最新版完整第四部分的全部8张图，拆分为15页便于编辑。

- 图4.1：原生文本框、矩形和连线重建，可直接编辑。
- 图4.2：原始产品背景为栅格图片；24个样区标记、文字及图例可编辑。
- 图4.3：热图单元和数值均为PowerPoint原生形状/文字。
- 图4.4a：原生折线图，右键“编辑数据”修改工作表。
- 图4.4b：散点图为原生图表；箱线图为按数据构建的可编辑形状，逐窗数据记录在备注。
- 图4.5、4.6：30×30格网以分组矩形重建，取消组合后可编辑色块；更细尺度及原生栅格保留准确像元图片，文字、图例和版式独立可编辑。

栅格地理数据没有伪装成完全可编辑矢量，不能在PPT中将百万像元逐个编辑。对应GeoTIFF仍在结果目录，可在GIS中修改后替换面板图片。PPT数据均来自现有实验，不改变统计值。
''',encoding='utf8')
    print(str(dest));print('Slides',len(check.slides),'native charts',charts)
if __name__=='__main__':main()
