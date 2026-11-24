from pathlib import Path
import importlib.util,json,os
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch,FancyBboxPatch,FancyArrowPatch
from matplotlib.lines import Line2D
from PIL import Image
R=Path(__file__).resolve().parent;B=R.parent
spec=importlib.util.spec_from_file_location('previous_figures',R/'figure_primitives.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
old.ROOT=R;old.FIG=R/'figures';old.DATA=R/'figure_data'
for p in [old.FIG,old.DATA,R/'preview']:p.mkdir(exist_ok=True)
manifest=[]
def save(fig,name,sources):
 for ext in ['pdf','svg','png']:fig.savefig(old.FIG/(name+'.'+ext),dpi=600,bbox_inches='tight',pad_inches=.08)
 with Image.open(old.FIG/(name+'.png')) as im:
  size=im.size;im.convert('RGB').save(old.FIG/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 fig.savefig(R/'preview'/(name+'.png'),dpi=150,bbox_inches='tight',pad_inches=.08)
 manifest.append(dict(figure=name,sources=sources,png_pixels=size,dpi=600,formats=['pdf','svg','png','tif']));plt.close(fig)
def map_save(fig,name,sources):
 mapping={'Fig4_1':'Fig4_1','Fig4_3':'Fig4_5','Fig4_5':'Fig4_7','FigS2':'FigS1','FigS3':'FigS2','FigS4':'FigS3'}
 if name in mapping:save(fig,mapping[name],sources)
 else:plt.close(fig)
old.save=map_save
OLD=old.OLD;V4=old.V4;V5=old.V5
def products():
 import importlib.util
 proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data';os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj);os.environ['GDAL_PAM_ENABLED']='NO'
 import rasterio
 cfg=json.loads((V4/'frozen_parameters.json').read_text(encoding='utf8'));arrays={}
 for key in ['W2020','H2020']:
  path=cfg['experiment3']['inputs'][key]['path']
  with rasterio.open(path) as d:
   width=1900;height=round(width*d.height/d.width);a=d.read(1,out_shape=(height,width));ext=[d.bounds.left,d.bounds.right,d.bounds.bottom,d.bounds.top]
   arrays[key]=(a,ext)
 np.savez_compressed(old.DATA/'product_display_samples.npz',**{k:v[0] for k,v in arrays.items()},**{k+'_extent':v[1] for k,v in arrays.items()})
 fig=plt.figure(figsize=(7.4,6.1));gs=fig.add_gridspec(2,2,height_ratios=[1,1.25],hspace=.47,wspace=.15)
 axs=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
 hc=['#dfa647','#eecb58','#a6bf70','#5fa48e','#287f7b','#dce3df'];wc=['#387b54','#77a35c','#b3ce90','#94ac7e','#dacb6f','#cdb18d','#69b0a5','#5893b4','#deb49d','#b77f8b','#c4c0b4','#e0c97f','#f0ca58','#d7e3e9']
 for ax,key,colors,codes,title in [(axs[0],'W2020',wc,list(range(1,15)),'a  Wang 2020: land cover'),(axs[1],'H2020',hc,[1,21,22,23,24,3],'b  Han 2020: desert and sandy land')]:
  a,ext=arrays[key];mapped=np.zeros(a.shape,dtype='uint8')
  for j,code in enumerate(codes,1):mapped[a==code]=j
  ax.imshow(np.ma.masked_where(mapped==0,mapped),extent=ext,cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(.5,len(codes)+1.5),len(codes)),interpolation='nearest',rasterized=True)
  ax.set(xlim=(87,127),ylim=(37,54),xticks=[90,100,110,120],yticks=[38,42,46,50,54],xlabel='Longitude (°E)');ax.set_aspect(1/np.cos(np.deg2rad(45)));ax.set_title(title,loc='left',fontsize=9)
  if key=='W2020':ax.set_ylabel('Latitude (°N)')
  labels=[str(c) for c in codes] if key=='W2020' else ['SD','SL21','SL22','SL23','SL24','Others']
  ax.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(colors,labels)],loc='upper center',bbox_to_anchor=(.5,-.27),ncol=7 if key=='W2020' else 3,fontsize=6.3,frameon=False,columnspacing=.7,handlelength=1,handletextpad=.3,borderpad=0)
 ax=axs[2];a,ext=arrays['H2020'];ax.imshow(np.ma.masked_where(a==0,np.ones_like(a)),extent=ext,cmap=ListedColormap(['#eef0ed']),interpolation='nearest')
 prior=pd.read_csv(V4/'split_manifest.csv');new=pd.read_csv(V5/'new_sites.csv');sel=pd.read_csv(OLD/'selection/selected_regions.csv')
 cohorts=[(prior[(prior.phase=='development')&~prior.id.isin(sel.id)],'#777777','o','Additional development (36)',False),(prior[prior.phase=='test'],'#d89621','s','Prior evaluation (40)',True),(new,'#19977d','^','Low-SL extrapolation (63)',True),(sel[sel.group=='Low'],'#277bb6','s','Mechanism Low (12)',True),(sel[sel.group=='High'],'#ce4936','o','Mechanism High (12)',True)]
 for data,color,m,label,filled in cohorts:
  ax.scatter(data.lon,data.lat,s=15 if 'Mechanism' not in label else 28,marker=m,facecolors=color if filled else 'none',edgecolors='white' if filled else color,linewidths=.35 if filled else .6,label=label,zorder=4 if 'Mechanism' in label else 3)
 ax.set(xlim=(87,127),ylim=(37,54),xlabel='Longitude (°E)',ylabel='Latitude (°N)');ax.set_aspect(1/np.cos(np.deg2rad(45)));ax.set_title('c  Experimental windows and spatial separation',loc='left',fontsize=9)
 ax.legend(loc='upper center',bbox_to_anchor=(.5,-.22),ncol=3,fontsize=7,frameon=False,columnspacing=1.2);ax.grid(lw=.3,alpha=.2)
 pd.concat([x.assign(cohort=l) for x,c,m,l,f in cohorts]).to_csv(old.DATA/'Fig4_2_sample_locations.csv',index=False,encoding='utf-8-sig')
 save(fig,'Fig4_2',[cfg['experiment3']['inputs'][k]['path'] for k in ['W2020','H2020']]+[str(V4/'split_manifest.csv'),str(V5/'new_sites.csv'),str(OLD/'selection/selected_regions.csv')])

def selection():
 cand=pd.read_csv(OLD/'selection/candidates.csv');c=cand[cand.reason=='eligible'];s=pd.read_csv(OLD/'selection/selected_regions.csv').sort_values(['group','selection_order'])
 q1,q3=c.H_SL.quantile([.25,.75]);assert len(c)==714
 fig=plt.figure(figsize=(7.4,6.4));gs=fig.add_gridspec(2,2,height_ratios=[.8,1.7],hspace=.30,wspace=.26)
 ax=fig.add_subplot(gs[0,:]);ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
 boxes=[(.005,'1  Screen candidates','5,782 windows: 1,200 × 1,200 pixels\nCommon coverage ≥95%\nSL: 20–80%; Others ≥10%\nSpatial exclusions → 714 eligible'),(.345,'2  Stratify composition','Within-SL entropy (bits)\nLow ≤Q25: 179; High ≥Q75: 179\nMiddle: 356\nOnly the two tails are sampled'),(.685,'3  Disperse and freeze','12 Low + 12 High windows\nRandom starts; seed 20261016\nAlternating maximin selection\n≥50 km required; 243 km achieved')]
 for x,title,body in boxes:
  ax.add_patch(FancyBboxPatch((x,.08),.30,.84,boxstyle='round,pad=.008',facecolor='#f2f5f6',edgecolor='#899ba5',lw=.8));ax.text(x+.15,.82,title,ha='center',va='top',fontsize=8.4,fontweight='bold');ax.text(x+.15,.58,body,ha='center',va='top',fontsize=7.1,linespacing=1.8)
 for x in [.315,.655]:ax.add_patch(FancyArrowPatch((x,.5),(x+.026,.5),arrowstyle='-|>',mutation_scale=12,color='#526776'))
 ax=fig.add_subplot(gs[1,0]);ax.hist(c.H_SL,bins=np.linspace(0,2,31),color='#b9c1c4',edgecolor='white',lw=.4);ax.axvspan(0,q1,color='#277bb6',alpha=.09);ax.axvspan(q3,2,color='#ce4936',alpha=.09)
 for val,color,label in [(q1,'#277bb6',f'Q25 = {q1:.3f}\nLow: 179'),(q3,'#ce4936',f'Q75 = {q3:.3f}\nHigh: 179')]:ax.axvline(val,color=color,ls='--',lw=1);ax.text(val+.02,ax.get_ylim()[1]*.95,label,color=color,va='top',fontsize=7.1)
 ax.set(xlabel='Within-SL entropy (bits)',ylabel='Eligible windows',xlim=(0,2));ax.set_title('a  Entropy strata',loc='left',fontsize=9)
 bx=fig.add_subplot(gs[1,1]);cols=['#eecb58','#a6bf70','#5fa48e','#287f7b'];left=np.zeros(len(s));labels=[('H' if g=='High' else 'L')+str(i+1).zfill(2) for g in ['High','Low'] for i in range(len(s[s.group==g]))];s['display_id']=labels
 for code,color in zip([21,22,23,24],cols):
  vals=s['p'+str(code)].to_numpy()/s.pSL.to_numpy();bx.barh(range(len(s)),vals,left=left,color=color,label='SL'+str(code),height=.8);left+=vals
 np.testing.assert_allclose(left,1,atol=1e-12)
 bx.set(yticks=range(len(s)),yticklabels=labels,xlim=(0,1),xlabel='Subclass fraction within SL');bx.invert_yaxis();bx.tick_params(axis='y',labelsize=6);bx.axhline(11.5,color='#888888',lw=.6);bx.set_title('b  Selected-window composition',loc='left',fontsize=9);bx.legend(loc='upper center',bbox_to_anchor=(.5,-.13),ncol=4,frameon=False,fontsize=6.5,columnspacing=.6,handlelength=1)
 c.to_csv(old.DATA/'Fig4_3_eligible_candidates.csv',index=False,encoding='utf-8-sig');s.to_csv(old.DATA/'Fig4_3_selected_composition.csv',index=False,encoding='utf-8-sig')
 save(fig,'Fig4_3',[str(OLD/'selection/candidates.csv'),str(OLD/'selection/selected_regions.csv')])

def contributions():
 d=pd.read_csv(old.DATA/'factor_decomposition_summary.csv')
 fig,(ax,bx)=plt.subplots(1,2,figsize=(7.4,3.0),gridspec_kw={'width_ratios':[1.15,1]},layout='constrained')
 terms=['S','T','M','Interactions'];colors=['#3c84af','#d9a23b','#8f74b7','#5c9986'];labels=['Spatial support (S)','Comparison interval (T)','Semantic level (M)','Interactions']
 for y,g in enumerate(['Low','High']):
  left=0
  for term,color in zip(terms,colors):
   v=d[(d.group==g)&(d.term==term)].share_mean.iloc[0];ax.barh(y,v,left=left,height=.48,color=color);ax.text(left+v/2,y,f'{v:.1f}',ha='center',va='center',fontsize=7.5,color='white' if term in ['S','M'] else '#172128');left+=v
 ax.set(yticks=[0,1],yticklabels=['Low','High'],xlim=(0,100),ylim=(-.65,1.65),xlabel='Within-window response variation (%)');ax.invert_yaxis();old.tag(ax,'a  Main effects and interactions');ax.legend(handles=[Patch(color=c,label=l) for c,l in zip(colors,labels)],loc='upper center',bbox_to_anchor=(.5,-.28),ncol=2,frameon=False,fontsize=7)
 for shift,g,color in [(-.12,'Low','#277bb6'),(.12,'High','#ce4936')]:
  q=d[(d.group==g)&d.term.isin(['S×T','S×M','T×M','S×T×M'])].set_index('term').loc[['S×T','S×M','T×M','S×T×M']]
  bx.errorbar(q.share_mean,np.arange(4)+shift,xerr=np.vstack([q.share_mean-q.ci_low,q.ci_high-q.share_mean]),fmt='o',ms=4,capsize=2,color=color,label=g)
 bx.set(yticks=range(4),yticklabels=['S × T','S × M','T × M','S × T × M'],xlabel='Interaction share (%)',xlim=(0,12));bx.invert_yaxis();bx.grid(axis='x',alpha=.2,lw=.5);old.tag(bx,'b  Interaction components');bx.legend(loc='lower right',frameon=False,fontsize=7)
 save(fig,'Fig4_4',[str(old.DATA/'factor_decomposition_by_window.csv'),str(old.DATA/'factor_decomposition_summary.csv')])

def supports():
 o=pd.read_csv(OLD/'results/experiment_2/order.csv');o=o[o.group.isin(['Low','High'])];t=pd.read_csv(OLD/'tables/Table_2_Noncommutativity.csv');t=t[t.metric=='R_NC_count'];sel=pd.read_csv(OLD/'selection/selected_regions.csv')
 phase=pd.read_csv(OLD/'results/review_multiscale_order/phase_all_scales.csv');phase=phase[phase.group.isin(['Low','High'])]
 q=phase.groupby(['site','group','scale']).R_NC_count.agg(lambda x:100*(x.max()-x.min())).reset_index(name='range_pp');q.to_csv(old.DATA/'Fig4_6_phase_ranges.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(2,3,figsize=(7.4,5.3),layout='constrained')
 for i,group in enumerate(['Low','High']):
  ax=axes[0,i]
  for sid,v in o[o.group==group].groupby('site'):v=v.sort_values('scale');ax.plot(range(3),100*v.R_NC_count,color=old.COL[group],alpha=.3,lw=.65)
  v=t[t.group==group].sort_values('scale');ax.errorbar(range(3),100*v['mean'],yerr=[100*(v['mean']-v.ci_low),100*(v.ci_high-v['mean'])],color=old.COL[group],marker='o',ms=4,lw=1.6,capsize=2)
  ax.set(xticks=range(3),xticklabels=['3×3','10×10','30×30'],ylim=(-.2,11.3),xlabel='Spatial support',title=group);old.grid(ax);old.tag(ax,chr(97+i))
 axes[0,0].set_ylabel('Disagreeing cells (%)')
 merged=o[o.scale==30].merge(sel[['id','H_SL']],left_on='site',right_on='id')
 for g,m in [('Low','o'),('High','^')]:
  z=merged[merged.group==g];axes[0,2].scatter(z.H_SL,100*z.R_NC_count,color=old.COL[g],marker=m,s=20,label=g)
 axes[0,2].set(xlabel='Within-SL entropy (bits)',ylabel='Disagreeing cells (%)',ylim=(-.2,11.3),title='30×30 support');axes[0,2].legend(fontsize=7,frameon=False);old.tag(axes[0,2],'c');old.grid(axes[0,2])
 for j,f in enumerate([3,10,30]):
  ax=axes[1,j]
  for i,g in enumerate(['Low','High']):
   v=q[(q.scale==f)&(q.group==g)].range_pp;ax.boxplot([v],positions=[i],widths=.45,showfliers=False,medianprops={'color':'black'});ax.scatter(i+np.random.default_rng(f+i).uniform(-.12,.12,len(v)),v,s=12,color=old.COL[g],alpha=.75)
  ax.set(xticks=[0,1],xticklabels=['Low','High'],title=f'{f}×{f} phase shifts',ylabel='Phase range (percentage points)');old.grid(ax);old.tag(ax,chr(100+j))
 save(fig,'Fig4_6',[str(OLD/'results/experiment_2/order.csv'),str(OLD/'tables/Table_2_Noncommutativity.csv'),str(OLD/'results/review_multiscale_order/phase_all_scales.csv')])

if __name__=='__main__':
 for fn in [old.fig1,products,selection,contributions,old.fig3,supports,old.fig5,old.supplements]:fn();print(fn.__name__+' done',flush=True)
 (R/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
