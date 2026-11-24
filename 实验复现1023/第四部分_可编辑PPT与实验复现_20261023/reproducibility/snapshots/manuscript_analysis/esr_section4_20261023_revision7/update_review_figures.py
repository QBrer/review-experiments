from pathlib import Path
import json,base64,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Rectangle,FancyArrowPatch
from matplotlib.colors import ListedColormap,BoundaryNorm
from PIL import Image
import fitz
R=Path(__file__).resolve().parent;F=R/'figures';D=R/'figure_data';P=R/'preview'
plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
manifest=json.loads((R/'figure_manifest.json').read_text(encoding='utf8'))
def record(row):
 for i,x in enumerate(manifest):
  if x['figure']==row['figure']:manifest[i]=row;break
def save(fig,name,sources):
 for ext in ['pdf','svg','png']:fig.savefig(F/(name+'.'+ext),dpi=600,bbox_inches='tight',pad_inches=.08)
 with Image.open(F/(name+'.png')) as im:
  size=im.size;im.convert('RGB').save(F/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 fig.savefig(P/(name+'.png'),dpi=165,bbox_inches='tight',pad_inches=.08);plt.close(fig)
 record(dict(figure=name,sources=sources,png_pixels=size,dpi=600,formats=['pdf','svg','png','tif']))

def supplied_framework():
 png=F/'Fig4_1.png';raw=png.read_bytes()
 with Image.open(png) as im:
  w,h=im.size;dpi=w/(16.8/2.54);im.save(F/'Fig4_1.tif',compression='tiff_lzw',dpi=(dpi,dpi))
 doc=fitz.open();page=doc.new_page(width=16.8/2.54*72,height=(16.8/2.54*72)*h/w);page.insert_image(page.rect,stream=raw);doc.save(F/'Fig4_1.pdf');doc.close()
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><image width="{w}" height="{h}" xlink:href="data:image/png;base64,{base64.b64encode(raw).decode()}"/></svg>'
 (F/'Fig4_1.svg').write_text(svg,encoding='utf8')
 record(dict(figure='Fig4_1',sources=['User supplied codex-clipboard-c8a44cec-fe33-463d-8ad5-6142a89059d1.png'],png_pixels=[w,h],dpi=None,effective_dpi_at_16_8_cm=dpi,sha256=hashlib.sha256(raw).hexdigest(),formats=['pdf','svg','png','tif'],note='Original bitmap preserved. PDF/SVG wrap the original raster; not editable vector artwork. No claimed 600 dpi for this supplied image.'))

def product_map():
 z=np.load(D/'product_display_samples.npz');legend=pd.read_csv(R/'source_data/Wang_product_legend_verified.csv');coh=pd.read_csv(R/'sampling_audit/all_163_windows_roles.csv')
 fig=plt.figure(figsize=(7.6,7.3))
 a=fig.add_axes([.08,.72,.42,.23]);b=fig.add_axes([.57,.72,.42,.23]);la=fig.add_axes([.07,.51,.45,.16]);lb=fig.add_axes([.57,.55,.42,.12]);c=fig.add_axes([.13,.15,.80,.30]);la.axis('off');lb.axis('off')
 hc=['#dfa647','#eecb58','#a6bf70','#5fa48e','#287f7b','#dce3df'];wc=['#387b54','#77a35c','#b3ce90','#94ac7e','#dacb6f','#cdb18d','#69b0a5','#5893b4','#deb49d','#b77f8b','#c4c0b4','#e0c97f','#f0ca58','#d7e3e9']
 for ax,key,colors,codes,title in [(a,'W2020',wc,list(range(1,15)),'a  Wang 2020: land cover'),(b,'H2020',hc,[1,21,22,23,24,3],'b  Han 2020: desert and sandy land')]:
  raw=z[key];x=np.zeros(raw.shape,dtype='uint8')
  for i,code in enumerate(codes,1):x[raw==code]=i
  ax.imshow(np.ma.masked_where(x==0,x),extent=z[key+'_extent'],cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(.5,len(codes)+1.5),len(codes)),interpolation='nearest',rasterized=True)
  ax.set(xlim=(87,127),ylim=(37,54),xticks=[90,100,110,120],yticks=[38,42,46,50,54],xlabel='Longitude (°E)');ax.set_aspect(1/np.cos(np.deg2rad(45)));ax.set_title(title,loc='left',fontsize=9.5)
 a.set_ylabel('Latitude (°N)')
 # A dedicated legend region prevents the fourteen full labels from crowding the map.
 for i,row in enumerate(legend.itertuples()):
  col=i//7;rank=i%7;x=.04+col*.49;y=.96-rank*.14
  la.add_patch(Rectangle((x,y-.055),.045,.055,facecolor=wc[i],edgecolor='none'));la.text(x+.06,y-.027,f'{row.code}  {row.name}',va='center',fontsize=8)
 labels=['1  SD','21  SL21','22  SL22','23  SL23','24  SL24','3  Others']
 for i,(label,color) in enumerate(zip(labels,hc)):
  col=i//3;rank=i%3;x=.05+col*.5;y=.83-rank*.29;lb.add_patch(Rectangle((x,y-.065),.055,.065,facecolor=color,edgecolor='none'));lb.text(x+.075,y-.033,label,va='center',fontsize=8)
 raw=z['H2020'];c.imshow(np.ma.masked_where(raw==0,np.ones_like(raw)),extent=z['H2020_extent'],cmap=ListedColormap(['#eef0ed']),interpolation='nearest')
 settings=[('Development extension','#777777','o','Development extension (36)',False),('Spatial test','#d89621','s','Spatial test (40)',True),('Low-SL extrapolation','#19977d','^','Low-SL extrapolation (63)',True),('Low','#277bb6','s','Low-entropy mechanism set (12)',True),('High','#ce4936','o','High-entropy mechanism set (12)',True)]
 for group,color,marker,label,filled in settings:
  q=coh[coh.cohort==group];c.scatter(q.lon,q.lat,s=15 if group not in ['Low','High'] else 26,marker=marker,facecolors=color if filled else 'none',edgecolors='white' if filled else color,linewidths=.4,label=label,zorder=3)
 c.set(xlim=(87,127),ylim=(37,54),xlabel='Longitude (°E)',ylabel='Latitude (°N)');c.set_aspect(1/np.cos(np.deg2rad(45)));c.set_title('c  Sample windows by analytical role',loc='left');c.grid(alpha=.2,lw=.3)
 handles,labels=c.get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.53,-.008),ncol=2,frameon=False,fontsize=8,columnspacing=1.8)
 save(fig,'Fig4_2',[str(D/'product_display_samples.npz'),str(R/'sampling_audit/all_163_windows_roles.csv'),str(R/'source_data/Wang_product_legend_verified.csv'),'https://www.nature.com/articles/s41597-025-05648-8.pdf, Table 2'])

def application():
 fig,ax=plt.subplots(figsize=(7.6,8.3));ax.set(xlim=(0,12),ylim=(0,13));ax.axis('off');red='#d59794';ink='#24333d';gray='#6c7d85'
 ax.add_patch(Rectangle((.22,12.15),11.56,.62,facecolor='#f5f2ed',edgecolor='#c2b8a7',lw=.75));ax.text(6,12.46,'2010 / 2020 · Native support · Fixed valid domain · Source classes retained',ha='center',va='center',fontsize=9,color=ink)
 ax.text(2.05,11.83,'Input / diagnostic evidence',ha='center',fontsize=8.5,color=gray)
 ax.text(6,11.83,'Operation',ha='center',fontsize=8.5,color=gray)
 ax.text(10,11.83,'Output / verification target',ha='center',fontsize=8.5,color=gray)
 rows=[
 ('01  Define the task','Han anchor + Wang labels\nTwo common years','Set correspondence targets\nPreserve Wang sand events','Two dated correspondences\nTraceable change locations'),
 ('02  Diagnose mismatches','Grid origins and boundaries\nSix vs. fourteen classes','Restore known grid offsets\nUse a 13-pixel safety margin','Common valid support\nSeparate source labels'),
 ('03  Analyze constraints','Spatial boundaries\nClass co-occurrence\nCross-date shift relation','Boundary F1 + mean log P\nStandardize 169 shifts / date\nSoft temporal penalty','Spatial + semantic scores\nLinked correction pairs'),
 ('04  Organize alignment','60 development windows\nFrozen relation and parameters','Sequential preparation\nJoint search over 169 × 169 pairs\nCommon γ = 0.5, λ = 0.25','Two date-specific corrections\nWang labels on the Han grid'),
 ('05  Validate alignment','Evaluator: inverse shifts\nNative Wang event maps','G / GS / GT / GST contrasts\n63 windows in 14 new blocks\nIndependent calibration check','Residual error + change F1\nPaired effects and intervals')]
 for i,(title,left,mid,right) in enumerate(rows):
  y=9.65-i*2.18;h=1.84
  ax.add_patch(Rectangle((.22,y),11.56,h,facecolor='#fcfbfb',edgecolor=red,lw=.85,linestyle=(0,(7,5))))
  width=4.2 if i!=2 else 4.6
  ax.add_patch(Rectangle((.48,y+h-.15),width,.38,facecolor='white',edgecolor=red,lw=.85,zorder=3));ax.text(.65,y+h+.04,title,fontsize=10,weight='bold',va='center',color=ink,zorder=4)
  for x,text in [(2.0,left),(6.0,mid),(10.0,right)]:ax.text(x,y+.75,text,ha='center',va='center',fontsize=8.6,linespacing=1.65,color=ink)
  for x1,x2 in [(3.63,4.15),(7.87,8.38)]:ax.add_patch(FancyArrowPatch((x1,y+.75),(x2,y+.75),arrowstyle='-|>',mutation_scale=10,lw=.8,color=gray))
  if i<4:ax.add_patch(FancyArrowPatch((11.25,y-.04),(11.25,y-.27),arrowstyle='-|>',mutation_scale=10,lw=.8,color=gray))
 ax.text(6,.34,'Held-out references enter validation only; the diagram shows the executed workflow.',ha='center',fontsize=8,color=gray)
 save(fig,'Fig4_7',['Executed code: experiment_v4_runtime/engine.py; experiment_ablation_v5_runtime/ablation.py; original five-stage framework'])

supplied_framework();product_map();application();(R/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print('Updated Fig4_1, Fig4_2 and Fig4_7')
