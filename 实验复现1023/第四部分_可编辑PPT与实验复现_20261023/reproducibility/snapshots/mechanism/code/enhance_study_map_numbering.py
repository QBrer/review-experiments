from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Patch
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from rasterio.enums import Resampling
from docx import Document
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import re

OUT=ROOT/'figures/merged_1021';SOURCE=ROOT/'reports/4.5_1021用户稿_分布图与非交换图合并版.docx'
def main():
    source_hash=sha(SOURCE);sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv');e=pd.read_csv(ROOT/'selection/candidates.csv');e=e[e.reason=='eligible'].copy();q=load(ROOT/'selection/thresholds.json')
    e['group']=np.where(e.H_SL<=q['Q25'],'Low',np.where(e.H_SL>=q['Q75'],'High','Middle'))
    ds=open_inputs();tr=ds['H2020'].transform
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(16,13),constrained_layout=True);gs=fig.add_gridspec(2,2,height_ratios=[.65,1.35]);axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    palettes={'W2020':['39734C','86A65C','B6D19D','A0B38B','D7CA7F','D6B89A','67B5A6','5A91B5','DDBAA4','BC858A','C6C1B5','DFC888','E9C459','D5E0E8'],'H2020':['DFB15D','E8CF7F','B4C88F','81AF88','418676','DBE2DC']}
    for ax,key,codes,title in [(axes[0],'W2020',list(range(1,15)),'(a) Wang2020: land-cover context'),(axes[1],'H2020',[1,21,22,23,24,3],'(b) Han2020: sandy-land subclasses')]:
        src=ds[key];width=1800;ar=src.read(1,out_shape=(round(width*src.height/src.width),width),resampling=Resampling.nearest);z=np.full(ar.shape,len(codes),np.uint8)
        for i,c in enumerate(codes):z[ar==c]=i
        b=src.bounds;ax.imshow(z,cmap=ListedColormap(['#'+c for c in palettes[key]]+['white']),vmin=-.5,vmax=len(codes)+.5,extent=[b.left,b.right,b.bottom,b.top],interpolation='nearest')
        names=[str(x) for x in codes] if key=='W2020' else ['SD','SL21','SL22','SL23','SL24','Others']
        ax.legend(handles=[Patch(color='#'+c,label=l) for c,l in zip(palettes[key],names)],loc='upper left',fontsize=7,ncol=7 if key=='W2020' else 3)
        ax.set(title=title,xlim=(87.5,126.5),ylim=(37.1,53.9),xlabel='Longitude (°E)',ylabel='Latitude (°N)')
        if key=='W2020':cover=(ar>=1)&(ar<=14);wb=b
    ax=axes[2];ax.imshow(cover.astype(np.uint8),cmap=ListedColormap(['white','#f1f3f1']),vmin=0,vmax=1,extent=[wb.left,wb.right,wb.bottom,wb.top],interpolation='nearest')
    fills={'High':'#edc1b3','Low':'#b9d6e8','Middle':'#d3d8d5'};strong={'High':'#b8311d','Low':'#075795'}
    for group in ['Middle','Low','High']:
        rects=[]
        for r in e[e.group==group].itertuples():
            x,y=tr*(r.col,r.row);xx,yy=tr*(r.col+1200,r.row+1200);rects.append(Rectangle((x,yy),xx-x,y-yy))
        ax.add_collection(PatchCollection(rects,facecolor=fills[group],edgecolor='white',lw=.3,zorder=2))
    for r in sel.itertuples():
        color=strong[r.group];x,y=tr*(r.col,r.row);xx,yy=tr*(r.col+1200,r.row+1200)
        ax.add_patch(Rectangle((x,yy),xx-x,y-yy,facecolor='none',edgecolor='white',lw=3.1,zorder=5))
        ax.add_patch(Rectangle((x,yy),xx-x,y-yy,facecolor='none',edgecolor=color,lw=1.7,zorder=6))
        ax.scatter(r.lon,r.lat,s=95,marker='o' if r.group=='High' else 's',color=color,edgecolors='white',linewidths=1.15,zorder=7)
        ax.annotate(r.display_id,(r.lon,r.lat),xytext=(10,9),textcoords='offset points',fontsize=11.5,fontweight='bold',color=color,zorder=8,bbox=dict(boxstyle='round,pad=.22',facecolor='white',edgecolor=color,linewidth=.8,alpha=.98),arrowprops=dict(arrowstyle='-',color=color,lw=.7,shrinkA=0,shrinkB=7))
    handles=[Patch(facecolor=fills[g],label=f'{g} candidates: '+str((e.group==g).sum())) for g in ['Low','High','Middle']]
    handles +=[Line2D([],[],marker='o',ls='',markersize=9,color=strong['High'],markeredgecolor='white',label='Selected High: H01–H12'),Line2D([],[],marker='s',ls='',markersize=9,color=strong['Low'],markeredgecolor='white',label='Selected Low: L01–L12')]
    ax.legend(handles=handles,loc='upper left',fontsize=10,framealpha=.98)
    ax.set(title='(c) Sensitivity strata and selected experimental windows',xlim=(87.5,126.5),ylim=(37.1,53.9),xlabel='Longitude (°E)',ylabel='Latitude (°N)');ax.grid(alpha=.14);ax.set_axisbelow(True)
    fig.supxlabel('Light rectangles: candidate footprints. Dark outlined windows and labeled symbols: selected samples.\nSymbols are enlarged for visibility; outlined rectangles retain the true extent. Background shows product coverage.',fontsize=10)
    for ext in ['png','pdf','svg']:fig.savefig(OUT/f'Figure_4_2_Study_regions_emphasized.{ext}',dpi=300,bbox_inches='tight')
    plt.close(fig)
    for d in ds.values():d.close()
    doc=Document(SOURCE);old=Document(SOURCE);cap=next(p for p in doc.paragraphs if p.text.startswith('Figure 4.2a.'));el=cap._p.getprevious()
    while el is not None and not el.xpath('.//a:blip'):el=el.getprevious()
    assert el is not None;p=Paragraph(el,cap._parent)
    for child in list(el):
        if child.tag!=qn('w:pPr'):el.remove(child)
    p.add_run().add_picture(str(OUT/'Figure_4_2_Study_regions_emphasized.png'),width=Inches(6.6))
    cap.text='Figure 4.2a. Study products and sensitivity strata. Panels(a,b) show Wang2020 and Han2020. Panel(c) shows179 Low,179 High and356 middle-stratum candidates in pale colors. Selected windows use dark outlines, enlarged markers and labeled boxes: red circles for High and blue squares for Low. Outlines preserve actual footprints; marker sizes are enhanced for visibility. Background denotes product coverage.'
    mapping={'4.2a':'4.2','4.2b':'4.3','4.3':'4.4','4.4':'4.5','4.5a':'4.6','4.5b':'4.7','4.6':'4.8','4.7':'4.9'}
    for p in doc.paragraphs:
        t=p.text
        if t.startswith('Figure '):p.text=re.sub(r'^(Figure )(4\.\d+[ab]?)(\.)',lambda m:m[1]+mapping.get(m[2],m[2])+m[3],t)
        elif t.startswith('图4.5以各组首个'):
            p.text=t.replace('图4.5以各组首个','图4.6、图4.7以各组首个').replace('图4.5a','图4.6')
        elif '图4.' in t:p.text=re.sub(r'图(4\.\d+[ab]?)',lambda m:'图'+mapping.get(m[1],m[1]),t)
    # Cross-reference in the second order-map caption.
    for p in doc.paragraphs:
        if p.text.startswith('Figure 4.7.') and 'Figure 4.5a' in p.text:p.text=p.text.replace('Figure 4.5a','Figure 4.6')
    dest=ROOT/'reports/4.5_1021用户稿_样区突出与图号规范版.docx';doc.save(dest)
    check=Document(dest);caps=[p.text for p in check.paragraphs if p.text.startswith('Figure ')]
    assert [re.match(r'Figure (4\.\d+)\.',x)[1] for x in caps]==[f'4.{i}' for i in range(2,10)]
    assert len(check.inline_shapes)==len(old.inline_shapes)
    assert [[[c.text for c in row.cells] for row in t.rows] for t in check.tables]==[[[c.text for c in row.cells] for row in t.rows] for t in old.tables]
    assert sha(SOURCE)==source_hash
    dump(OUT/'sample_emphasis_and_renumbering.json',dict(time=now(),source_unchanged=True,selected_points=24,actual_footprints_preserved=True,marker_enlargement_display_only=True,renumbering=mapping,table_numbers_unchanged=True,caption_sequence=[f'4.{i}' for i in range(2,10)],output=str(dest)))
    print('Selected windows emphasized; eight figures renumbered consecutively4.2–4.9, tables unchanged.')
if __name__=='__main__':main()
