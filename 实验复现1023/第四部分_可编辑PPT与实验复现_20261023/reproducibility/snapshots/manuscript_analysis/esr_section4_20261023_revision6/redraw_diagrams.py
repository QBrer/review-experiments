from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyArrowPatch
from PIL import Image
R=Path(__file__).resolve().parent;B=R.parent
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
RED='#d59794';INK='#263640';GRAY='#708087';LIGHT='#fcfafa'
man=json.loads((R/'figure_manifest.json').read_text(encoding='utf8'))
def save(fig,name,sources):
 for ext in ['pdf','svg','png']:fig.savefig(R/'figures'/(name+'.'+ext),dpi=600,bbox_inches='tight',pad_inches=.08)
 with Image.open(R/'figures'/(name+'.png')) as im:
  size=im.size;im.convert('RGB').save(R/'figures'/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 fig.savefig(R/'preview'/(name+'.png'),dpi=160,bbox_inches='tight',pad_inches=.08);plt.close(fig)
 for i,row in enumerate(man):
  if row['figure']==name:man[i]=dict(figure=name,sources=sources,png_pixels=size,dpi=600,formats=['pdf','svg','png','tif']);break
def arrow(ax,a,b,dashed=False):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=11,lw=.85,color=GRAY,linestyle='--' if dashed else '-',zorder=2))

def workflow():
 fig,ax=plt.subplots(figsize=(7.4,6.5));ax.set(xlim=(0,10),ylim=(.80,9));ax.axis('off')
 # Two columns keep evidence/decision separate from the output, without duplicating
 # method definitions, numerical settings, or evaluation counts inside each box.
 ax.add_patch(Rectangle((.22,8.35),9.56,.50,facecolor='#f4f1ea',edgecolor='#c1b6a3',lw=.7))
 ax.text(5,8.60,'Scale and support: native pixels · paired years · retained class detail',ha='center',va='center',fontsize=9,color=INK)
 rows=[
 ('01','Task definition','Han–Wang correspondence\nWang sand change','Position and change targets'),
 ('02','Mismatch diagnosis','Grid · boundaries · class systems\nCross-date position differences','Fixed domain and retained labels'),
 ('03','Cross-dimensional constraints','Spatial + semantic evidence\nSoft temporal linkage','Scored correction candidates'),
 ('04','Strategy organization','Sequential preparation\nJoint two-date solution','Two corrections + aligned Wang'),
 ('05','Validation','Known shifts + native events\nSpatially separated evaluation','Recovery, preservation and increments')]
 for i,(number,title,inputs,outputs) in enumerate(rows):
  y=6.95-i*1.46;h=1.13
  ax.add_patch(Rectangle((.22,y),9.56,h,facecolor=LIGHT,edgecolor=RED,lw=.85,linestyle=(0,(7,5))))
  # Header tabs reproduce the reference's restrained outline motif.
  width={'Task definition':2.75,'Mismatch diagnosis':3.45,'Cross-dimensional constraints':4.80,'Strategy organization':3.90,'Validation':2.45}[title]
  ax.add_patch(Rectangle((.46,y+h-.14),width,.36,facecolor='white',edgecolor=RED,lw=.85,zorder=3))
  ax.text(.62,y+h+.04,number+'  '+title,va='center',ha='left',fontsize=9.5,weight='bold',color=INK,zorder=4)
  ax.text(2.65,y+.48,inputs,ha='center',va='center',fontsize=9,linespacing=1.5,color=INK)
  arrow(ax,(5.08,y+.48),(5.92,y+.48))
  ax.text(7.82,y+.48,outputs,ha='center',va='center',fontsize=8.8,color=INK)
  if i<4:arrow(ax,(9.40,y-.035),(9.40,y-.25))
 save(fig,'Fig4_7',['Original section 4 five-stage framework and implemented Han–Wang workflow; no new experiment'])

def sampling():
 fig=plt.figure(figsize=(7.6,7.0));gs=fig.add_gridspec(2,2,height_ratios=[1.14,1],hspace=.27,wspace=.28)
 ax=fig.add_subplot(gs[0,:]);ax.axis('off');ax.set(xlim=(0,10),ylim=(0,5.2));ax.set_title('a  Sample selection from 5,782 complete windows',loc='left',pad=12)
 def band(y,h,title,w):
  ax.add_patch(Rectangle((.03,y),9.94,h,facecolor=LIGHT,edgecolor=RED,linestyle=(0,(7,5)),lw=.85))
  ax.add_patch(Rectangle((.20,y+h-.13),w,.34,facecolor='white',edgecolor=RED,lw=.8,zorder=3));ax.text(.36,y+h+.04,title,fontsize=9,weight='bold',va='center',zorder=4,color=INK)
 def node(x,y,title,body):
  ax.text(x,y,title,fontsize=9.3,weight='bold',ha='center',va='center',color=INK)
  ax.text(x,y-.36,body,fontsize=8.5,ha='center',va='top',linespacing=1.5,color=INK)
 band(2.65,2.10,'Mixed-SL pool: 714 eligible windows',5.15)
 ax.text(5,4.38,'Coverage ≥95% · SL 20–80% · Others ≥10%',fontsize=8.5,ha='center',color=GRAY)
 node(1.65,3.88,'24 mechanism windows','12 Low + 12 High\nEntropy tails; maximin spacing')
 node(5.00,3.88,'40 spatial-test windows','258 spatial candidates\n20 new blocks × 2 windows')
 node(8.35,3.88,'36 added development','277 buffered candidates\nMaximin from the original 24')
 arrow(ax,(3.08,3.55),(3.56,3.55));arrow(ax,(6.43,3.55),(6.91,3.55))
 ax.text(5,2.38,'60 development = 24 + 36;  prior 100 = 60 development + 40 test',ha='center',fontsize=8.5,color=INK)
 band(.22,1.66,'Spatial extrapolation',3.15)
 node(1.65,1.33,'1,406 broader candidates','SL 5–95%; Others ≥5%\nCommon coverage ≥95%')
 node(5.00,1.33,'118 in unused blocks','Exclude blocks occupied\nby the prior 100 windows')
 node(8.35,1.33,'63 in 14 new blocks','≥100 km from prior centers\nAll eligible windows retained')
 arrow(ax,(3.08,1.00),(3.56,1.00));arrow(ax,(6.43,1.00),(6.91,1.00))
 arrow(ax,(5,2.18),(5,1.98),True)
 # Quantitative panels remain based on exactly the same data as the preceding version.
 old=B/'实验独立复核_20261021/只读基线副本';c=pd.read_csv(old/'selection/candidates.csv');c=c[c.reason=='eligible'];q1,q3=c.H_SL.quantile([.25,.75]);bx=fig.add_subplot(gs[1,0])
 bx.hist(c.H_SL,bins=np.linspace(0,2,31),color='#bbc4c8',edgecolor='white',lw=.4);bx.axvspan(0,q1,color='#277bb6',alpha=.09);bx.axvspan(q3,2,color='#ce4936',alpha=.09)
 for v,color,lab in [(q1,'#277bb6',f'Q25 = {q1:.3f}\nLow: 179'),(q3,'#ce4936',f'Q75 = {q3:.3f}\nHigh: 179')]:
  bx.axvline(v,color=color,ls='--',lw=1);bx.text(v+.025,bx.get_ylim()[1]*.95,lab,color=color,va='top',fontsize=7.7)
 bx.set(xlabel='Within-SL entropy (bits)',ylabel='Eligible-window count',xlim=(0,2));bx.set_title('b  Mechanism strata',loc='left')
 cohorts=pd.read_csv(R/'sampling_audit/all_163_windows_roles.csv');cx=fig.add_subplot(gs[1,1]);groups=['Low','High','Development extension','Spatial test','Low-SL extrapolation'];colors=['#277bb6','#ce4936','#888888','#d89621','#19977d']
 for i,(g,color) in enumerate(zip(groups,colors)):
  v=cohorts[cohorts.cohort==g].pSL.to_numpy()*100;cx.boxplot([v],positions=[i],widths=.5,showfliers=False,patch_artist=True,boxprops={'facecolor':color+'25','edgecolor':color},medianprops={'color':'black'},whiskerprops={'color':color},capprops={'color':color});cx.scatter(i+np.random.default_rng(82+i).uniform(-.15,.15,len(v)),v,s=9,color=color,alpha=.7,lw=0)
 cx.set(xticks=range(5),xticklabels=['Low\n12','High\n12','Dev.+\n36','Test\n40','Extrap.\n63'],ylabel='SL area fraction in 2020 (%)',ylim=(0,85));cx.grid(axis='y',alpha=.2,lw=.5);cx.set_title('c  Composition of all sets',loc='left')
 save(fig,'Fig4_3',[str(R/'sampling_audit/sampling_audit.json'),str(R/'sampling_audit/all_163_windows_roles.csv'),str(old/'selection/candidates.csv')])

workflow();sampling();(R/'figure_manifest.json').write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf8');print('Redrew workflow and sample-selection layout')
