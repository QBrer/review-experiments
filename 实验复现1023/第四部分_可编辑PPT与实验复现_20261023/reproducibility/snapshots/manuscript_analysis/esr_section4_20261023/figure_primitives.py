from pathlib import Path
import os,importlib.util,json,hashlib
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from PIL import Image
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
FIG=ROOT/'figures';DATA=ROOT/'figure_data';FIG.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
OLD=BASE/'实验独立复核_20261021/只读基线副本';V5=BASE/'experiment_ablation_v5_runtime';V4=BASE/'experiment_v4_runtime'
plt.rcParams.update({'font.family':'Arial','font.size':9,'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'xtick.major.width':.7,'ytick.major.width':.7,'savefig.facecolor':'white'})
COL={'Low':'#377eb8','High':'#d55e00','fine6':'#377eb8','coarse3':'#d55e00','G':'#747474','GS':'#0072b2','GT':'#cc79a7','GST':'#009e73'}
manifest=[]
def save(fig,name,sources):
 for ext in ['pdf','svg','png']:fig.savefig(FIG/(name+'.'+ext),dpi=600,bbox_inches='tight',pad_inches=.07)
 im=Image.open(FIG/(name+'.png'));im.convert('RGB').save(FIG/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 manifest.append({'figure':name,'sources':sources,'png_pixels':im.size,'dpi':600,'formats':['pdf','svg','png','tif']});plt.close(fig)
def tag(ax,text):ax.text(0,1.04,text,transform=ax.transAxes,ha='left',va='bottom',fontweight='bold',fontsize=10)
def grid(ax):ax.grid(axis='y',color='#e7e7e7',lw=.5);ax.set_axisbelow(True)
def fig1():
 fig,ax=plt.subplots(figsize=(7.2,3.75));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
 def box(x,y,w,h,title,body,color='#eef4f6'):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',facecolor=color,edgecolor='#8a9ca8',linewidth=.8))
  ax.text(x+w/2,y+h-.055,title,ha='center',va='top',fontweight='bold',fontsize=9)
  ax.text(x+w/2,y+.09,body,ha='center',va='bottom',fontsize=8.2,linespacing=1.5)
 xs=np.linspace(.015,.815,5)
 content=[('Define task','Objects\nOutputs\nAcceptance criteria'),('Diagnose','Position\nObservation period\nClass definitions'),('Constrain','Dependencies\nCompatibility\nInformation needs'),('Organize','Sequential\nIterative\nJoint'),('Validate','Preservation\nCorrespondence\nFitness for use')]
 ax.text(.5,.965,'Scale and support determine the comparison level',ha='center',va='top',fontsize=10,color='#344e5c')
 for x,(t,b) in zip(xs,content):box(x,.42,.17,.40,t,b)
 for x in xs[:-1]:ax.add_patch(FancyArrowPatch((x+.18,.62),(x+.195,.62),arrowstyle='-|>',mutation_scale=10,lw=.9,color='#4b6472'))
 ax.plot([.9,.9,.3,.3],[.405,.31,.31,.405],color='#b17b4e',ls='--',lw=.9);ax.annotate('',xy=(.3,.405),xytext=(.3,.35),arrowprops={'arrowstyle':'-|>','color':'#b17b4e','lw':.8});ax.text(.6,.325,'Evidence-based feedback',ha='center',color='#986b43',fontsize=8.3)
 ax.add_patch(FancyBboxPatch((.02,.20),.96,.065,boxstyle='round,pad=.006',facecolor='#f4f1e9',edgecolor='#b8aa8f',lw=.7));ax.text(.5,.232,'Hierarchy awareness: objects, temporal processes and semantic levels',ha='center',va='center',fontsize=8.5)
 ax.text(.5,.075,'Outputs: aligned data + correspondences + validity conditions',ha='center',va='center',fontsize=9,fontweight='bold',color='#344e5c')
 save(fig,'Fig4_1',['conceptual synthesis of original section 4; not a data-derived plot'])
def fig2():
 proj=Path(importlib.util.find_spec('rasterio').origin).parent/'proj_data';os.environ['PROJ_DATA']=str(proj);os.environ['PROJ_LIB']=str(proj);os.environ['GDAL_PAM_ENABLED']='NO'
 import rasterio
 cfg=json.loads((V4/'frozen_parameters.json').read_text(encoding='utf-8'));path=cfg['experiment3']['inputs']['H2020']['path']
 with rasterio.open(path) as d:
  a=d.read(1,out_shape=(600,1420));extent=[d.bounds.left,d.bounds.right,d.bounds.bottom,d.bounds.top]
 prior=pd.read_csv(V4/'split_manifest.csv');new=pd.read_csv(V5/'new_sites.csv');original=pd.read_csv(OLD/'selection/selected_regions.csv');candidates=pd.read_csv(OLD/'selection/candidates.csv')
 groups=[('Development (60)',prior[prior.phase=='development'],'#377eb8','o'),('Prior evaluation (40)',prior[prior.phase=='test'],'#e69f00','s'),('Low-SL extrapolation (63)',new,'#009e73','^')]
 fig,(ax,bx)=plt.subplots(1,2,figsize=(7.2,3.7),gridspec_kw={'width_ratios':[2.1,1]},layout='constrained');background=np.ma.masked_where(a==0,np.ones_like(a));ax.imshow(background,extent=extent,cmap=matplotlib.colors.ListedColormap(['#eeeeec']),origin='upper',interpolation='nearest',aspect='auto')
 out=[]
 for j,(label,d,color,m) in enumerate(groups):
  ax.scatter(d.lon,d.lat,s=16,c=color,marker=m,lw=.3,edgecolor='white',label=label,zorder=3)
  vals=d[['id']].merge(candidates[['id','pSL']],on='id',validate='one_to_one');v=vals.pSL.to_numpy()*100
  bx.boxplot([v],positions=[j],widths=.48,showfliers=False,patch_artist=True,boxprops={'facecolor':color+'25','edgecolor':color},medianprops={'color':'black'},whiskerprops={'color':color},capprops={'color':color})
  jit=np.random.default_rng(142+j).uniform(-.16,.16,len(v));bx.scatter(j+jit,v,s=9,c=color,alpha=.65,lw=0)
  vals['cohort']=label;out.append(vals)
 ax.scatter(original.lon,original.lat,s=40,marker='D',facecolors='none',edgecolors='#333333',lw=.6,label='Mechanism subset (24)',zorder=4)
 ax.set(xlim=(87,127),ylim=(37,54),xlabel='Longitude (°E)',ylabel='Latitude (°N)');ax.legend(loc='lower left',frameon=True,facecolor='white',framealpha=.9,fontsize=6.8,handletextpad=.5);tag(ax,'a  Spatial design')
 bx.set(xticks=[0,1,2],xticklabels=['Develop.','Prior eval.','Extrapol.'],ylim=(0,85),ylabel='Han SL area fraction in 2020 (%)');bx.tick_params(axis='x',rotation=25);grid(bx);tag(bx,'b  Composition')
 pd.concat(out).to_csv(DATA/'Fig4_2_composition.csv',index=False,encoding='utf-8-sig')
 save(fig,'Fig4_2',[str(V4/'split_manifest.csv'),str(V5/'new_sites.csv'),str(OLD/'selection/candidates.csv'),path])
def fig3():
 d=pd.read_csv(OLD/'tables/Table_1_Coupling.csv');d=d[d.metric=='F1'].copy();d['loss']=1-d['mean'];d['loss_low']=1-d.ci_high;d['loss_high']=1-d.ci_low;d.to_csv(DATA/'Fig4_5_loss.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(2,3,figsize=(7.2,4.7),sharex=True,sharey=True,layout='constrained')
 for i,group in enumerate(['Low','High']):
  for j,year in enumerate([2015,2010,2000]):
   ax=axes[i,j]
   for sem,m,label in [('fine6','o','Six classes'),('coarse3','s','Three classes')]:
    q=d[(d.group==group)&(d.start_year==year)&(d.semantic==sem)].sort_values('scale')
    ax.plot(range(3),q.loss,color=COL[sem],marker=m,ms=4,lw=1.4,label=label);ax.fill_between(range(3),q.loss_low,q.loss_high,color=COL[sem],alpha=.12,lw=0)
   ax.set(xticks=[0,1,2],xticklabels=['3×3','10×10','30×30'],ylim=(0,.8),title=f'{group}: {year}–2020');grid(ax);tag(ax,chr(97+i*3+j))
   if j==0:ax.set_ylabel('Change-location loss (1 − F1)')
   if i==1:ax.set_xlabel('Spatial support (native pixels)')
 axes[0,0].legend(frameon=False,loc='upper left')
 save(fig,'Fig4_3',[str(OLD/'tables/Table_1_Coupling.csv')])
def fig4():
 o=pd.read_csv(OLD/'results/experiment_2/order.csv');o=o[o.group!='B2'];t=pd.read_csv(OLD/'tables/Table_2_Noncommutativity.csv');t=t[t.metric=='R_NC_count'];sel=pd.read_csv(OLD/'selection/selected_regions.csv')
 fig,axes=plt.subplots(1,3,figsize=(7.2,2.8),layout='constrained')
 for i,group in enumerate(['Low','High']):
  ax=axes[i];g=o[o.group==group]
  for sid,q in g.groupby('site'):
   q=q.sort_values('scale');ax.plot(range(3),100*q.R_NC_count,color=COL[group],alpha=.30,lw=.65)
  q=t[t.group==group].sort_values('scale');ax.errorbar(range(3),100*q['mean'],yerr=np.vstack([100*(q['mean']-q.ci_low),100*(q.ci_high-q['mean'])]),color=COL[group],marker='o',lw=1.7,ms=4,capsize=2)
  ax.set(xticks=[0,1,2],xticklabels=['3×3','10×10','30×30'],ylim=(-.2,11.3),title=group,xlabel='Spatial support');grid(ax);tag(ax,chr(97+i))
  if i==0:ax.set_ylabel('Non-commutative cells (%)')
 q=o[o.scale==30].merge(sel[['id','H_SL']],left_on='site',right_on='id');q.to_csv(DATA/'Fig4_4_entropy_order.csv',index=False,encoding='utf-8-sig')
 for group,m in [('Low','o'),('High','^')]:
  g=q[q.group==group];axes[2].scatter(g.H_SL,100*g.R_NC_count,c=COL[group],marker=m,s=24,label=group,edgecolors='white',lw=.4)
 axes[2].set(xlabel='Within-SL entropy (bits)',ylabel='Non-commutative cells (%)',ylim=(-.2,11.3),title='30×30 support');axes[2].legend(frameon=False);grid(axes[2]);tag(axes[2],'c')
 o.to_csv(DATA/'Fig4_4_window_rates.csv',index=False,encoding='utf-8-sig')
 save(fig,'Fig4_4',[str(OLD/'results/experiment_2/order.csv'),str(OLD/'tables/Table_2_Noncommutativity.csv'),str(OLD/'selection/selected_regions.csv')])
def block_task():
 t=pd.read_csv(V5/'task_metrics.csv');t=t[(t.dataset=='low_SL_extrapolation')&t.is_primary&(t.reference_km2>0)&(t.event=='change_union')]
 return t.groupby(['method','block','site','family']).F1.mean().groupby(['method','block','site']).mean().groupby(['method','block']).mean().reset_index()
def fig5():
 b=pd.read_csv(V5/'block_results.csv');b=b[(b.dataset=='low_SL_extrapolation')&(b.regime=='matched_primary')];t=block_task();co=pd.read_csv(V5/'paired_contrasts.csv');co=co[co.dataset=='low_SL_extrapolation'];co.to_csv(DATA/'Fig4_7_contrasts.csv',index=False,encoding='utf-8-sig');b.to_csv(DATA/'Fig4_7_block_error.csv',index=False,encoding='utf-8-sig');t.to_csv(DATA/'Fig4_7_block_F1.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(2,2,figsize=(7.2,5.3),layout='constrained');methods=['G','GS','GT','GST']
 for ax,data,key,ylabel,title in [(axes[0,0],b,'E','Residual shift (native pixels)','a  Alignment recovery'),(axes[0,1],t,'F1','Change F1','b  Change preservation')]:
  for i,m in enumerate(methods):
   v=data[data.method==m][key].to_numpy();jit=np.random.default_rng(i+42).uniform(-.16,.16,len(v));ax.scatter(i+jit,v,color=COL[m],s=15,alpha=.5,lw=0);ax.plot([i-.22,i+.22],[v.mean(),v.mean()],color=COL[m],lw=2.5);ax.scatter(i,v.mean(),marker='D',s=32,color=COL[m],edgecolors='black',lw=.4,zorder=5)
  ax.set(xticks=range(4),xticklabels=methods,ylabel=ylabel);grid(ax);tag(ax,title)
 axes[0,0].set_ylim(bottom=-.025);axes[0,1].set_ylim(.75,1.01)
 ax=axes[1,0];q=co[(co.regime=='matched_primary')&co.contrast.isin(['semantic_given_time','time_given_semantic'])].set_index('contrast').loc[['semantic_given_time','time_given_semantic']]
 ax.errorbar(q['mean'],[1,0],xerr=np.vstack([q['mean']-q.ci975_low,q.ci975_high-q['mean']]),fmt='o',color='#333333',capsize=3,ms=5);ax.axvline(0,color='#777777',lw=.8,ls='--');ax.set(yticks=[1,0],yticklabels=['Add semantics\n(GT − GST)','Add time\n(GS − GST)'],xlabel='Reduction in residual error (pixels)',ylim=(-.55,1.55));tag(ax,'c  Component effects (97.5% CI)');ax.grid(axis='x',color='#ededed',lw=.5)
 ax=axes[1,1];q=co[co.contrast=='full_vs_geometry'].set_index('regime').loc[['matched_primary','independently_calibrated']]
 ax.errorbar(q['mean'],[1,0],xerr=np.vstack([q['mean']-q.ci95_low,q.ci95_high-q['mean']]),fmt='s',color=COL['GST'],capsize=3,ms=5);ax.axvline(0,color='#777777',lw=.8,ls='--');ax.set(yticks=[1,0],yticklabels=['Common\nparameters','Separately\ncalibrated'],xlabel='G − GST residual error (pixels)',ylim=(-.55,1.55));tag(ax,'d  Parameter dependence (95% CI)');ax.grid(axis='x',color='#ededed',lw=.5)
 save(fig,'Fig4_5',[str(V5/'block_results.csv'),str(V5/'task_metrics.csv'),str(V5/'paired_contrasts.csv')])
def supplements():
 d=pd.read_csv(OLD/'results/review_multiscale_order/phase_all_scales.csv');q=d.groupby(['site','group','scale']).R_NC_count.agg(lambda x:100*(x.max()-x.min())).reset_index(name='range_pp');q.to_csv(DATA/'Fig4_6_phase_ranges_recheck.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(1,3,figsize=(7.2,2.7),layout='constrained')
 for ax,f in zip(axes,[3,10,30]):
  for i,g in enumerate(['Low','High']):
   v=q[(q.scale==f)&(q.group==g)].range_pp;ax.boxplot([v],positions=[i],widths=.45,showfliers=False,medianprops={'color':'black'});ax.scatter(i+np.random.default_rng(f+i).uniform(-.12,.12,len(v)),v,s=16,color=COL[g],alpha=.7)
  ax.set(xticks=[0,1],xticklabels=['Low','High'],title=f'{f}×{f}',ylabel='Phase range (percentage points)');grid(ax)
 save(fig,'FigS1',[str(OLD/'results/review_multiscale_order/phase_all_scales.csv')])
 d=pd.read_csv(V5/'all_common_parameter_results.csv');d=d[d.dataset=='low_SL_extrapolation'];d.to_csv(DATA/'FigS1_parameter_grid.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(2,4,figsize=(7.2,4.4),layout='constrained');keys=['G','GS','GT','GST','semantic_given_time','time_given_semantic','full_vs_G']
 d['full_vs_G']=d.G-d.GST
 for i,key in enumerate(keys):
  ax=axes.ravel()[i];mat=d.pivot(index='gamma',columns='lambda',values=key).sort_index().to_numpy();vmax=.27 if i<4 else .22;im=ax.imshow(mat,origin='lower',aspect='auto',cmap='YlGnBu' if i<4 else 'PuBuGn',vmin=0,vmax=vmax)
  for r in range(3):
   for c in range(4):ax.text(c,r,f'{mat[r,c]:.3f}',ha='center',va='center',fontsize=6.5,color='white' if mat[r,c]>.65*vmax else '#111111')
  ax.set(xticks=range(4),xticklabels=['0','.25','.5','1'],yticks=range(3),yticklabels=['0','.25','.5'],xlabel='Temporal penalty λ',ylabel='Shift penalty γ',title=key if i<4 else ['Add semantics','Add time','G − GST'][i-4])
 axes[1,3].axis('off');axes[1,3].text(.03,.9,'Top: residual error\nBottom: error reduction\n\nUnits: native pixels\n\nAll planned settings\nare shown.',va='top',fontsize=9)
 save(fig,'FigS2',[str(V5/'all_common_parameter_results.csv')])
 d=pd.read_csv(V5/'all_alignment_metrics.csv');d=d[(d.dataset=='low_SL_extrapolation')&d.is_primary];b=d.groupby(['method','block','site','family']).E.mean().groupby(['method','block','family']).mean().reset_index();b.to_csv(DATA/'FigS2_block_family.csv',index=False,encoding='utf-8-sig')
 fig,axes=plt.subplots(1,3,figsize=(7.2,2.9),sharey=True,layout='constrained')
 for ax,f,label in zip(axes,['G0','G1','G2'],['No added shift','Shared shift','Different shifts']):
  for i,m in enumerate(['G','GS','GT','GST']):
   v=b[(b.method==m)&(b.family==f)].E;ax.scatter(i+np.random.default_rng(i+42).uniform(-.14,.14,len(v)),v,c=COL[m],s=15,alpha=.55);ax.plot([i-.20,i+.20],[v.mean()]*2,color=COL[m],lw=2.5)
  ax.set(xticks=range(4),xticklabels=['G','GS','GT','GST'],title=label);grid(ax)
 axes[0].set_ylabel('Residual shift (native pixels)');save(fig,'FigS3',[str(V5/'all_alignment_metrics.csv')])
 d=pd.read_csv(V4/'method_summary.csv');counts=pd.read_csv(V4/'strategy_choice_counts.csv');co=pd.read_csv(V5/'paired_contrasts.csv');co=co[co.contrast=='full_vs_geometry'];fig,axes=plt.subplots(1,3,figsize=(7.2,2.9),layout='constrained')
 labels=['A0','A1','A2','A3','basic','full','oracle'];v=d.set_index('method').loc[labels].E
 axes[0].bar(range(len(labels)),v,color=['#999999']*3+['#009e73','#cccccc','#0072b2','#e69f00']);axes[0].set(xticks=range(len(labels)),xticklabels=labels,ylabel='Residual shift (pixels)');axes[0].tick_params(axis='x',rotation=45);tag(axes[0],'a  Prior 40 windows');grid(axes[0])
 axes[1].bar(['Basic','Full'],[280,280],color=['#aaaaaa','#0072b2']);axes[1].set(ylabel='Selections of A3',ylim=(0,310));tag(axes[1],'b  Strategy choices');grid(axes[1])
 labels2=[]
 for i,(dataset,regime) in enumerate([('old40_exploratory','matched_primary'),('old40_exploratory','independently_calibrated'),('low_SL_extrapolation','matched_primary'),('low_SL_extrapolation','independently_calibrated')]):
  r=co[(co.dataset==dataset)&(co.regime==regime)].iloc[0];axes[2].errorbar(r['mean'],3-i,xerr=[[r['mean']-r.ci95_low],[r.ci95_high-r['mean']]],fmt='o',color='#377eb8' if i<2 else '#009e73',capsize=2,ms=4);labels2.append(('Prior' if i<2 else 'New')+' / '+('common' if i%2==0 else 'calibrated'))
 axes[2].axvline(0,color='#777777',ls='--',lw=.7);axes[2].set(yticks=[3,2,1,0],yticklabels=labels2,xlabel='G − GST error (pixels)',ylim=(-.5,3.5));axes[2].tick_params(axis='y',labelsize=6.8);tag(axes[2],'c  Full-model comparisons')
 save(fig,'FigS4',[str(V4/'method_summary.csv'),str(V4/'strategy_choice_counts.csv'),str(V5/'paired_contrasts.csv')])
if __name__=='__main__':
 for fn in [fig1,fig2,fig3,fig4,fig5,supplements]:fn();print(fn.__name__+' done',flush=True)
 (ROOT/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
