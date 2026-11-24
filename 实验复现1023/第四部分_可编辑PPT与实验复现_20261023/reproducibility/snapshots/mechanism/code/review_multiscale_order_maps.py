from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages
from framework_walkthrough import tif

OUT=ROOT/'results/review_multiscale_order'
FIG=ROOT/'figures/review_multiscale_order'
def main():
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv').sort_values('selection_order')
    old=pd.read_csv(ROOT/'results/experiment_2/order.csv');ds=open_inputs();off=offsets(ds)
    protected={str(p):sha(p) for p in [ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/experiment_2/phase.csv']}
    dump(OUT/'design.json',dict(time=now(),purpose='User-requested three-scale order and red disagreement maps; extend descriptive phase visualization to3/10',years=[2020],scales=[3,10,30],phase_rule='0,floor(f/3),floor(2f/3) both axes',common_core='[30:n-30) all scales and phases',no_new_significance=True,protected=protected))
    stats=[];phases=[]
    with PdfPages(FIG/'24样区_三尺度_两种顺序与红色差异.pdf') as book:
        for s in sel.to_dict('records'):
            label=s['display_id'];sid=s['id'];n=1200;raw,v=read_window(ds,off,int(s['row']),int(s['col']),n);tr=ds['H2020'].window_transform(Window(s['col'],s['row'],n,n));w=weights(tr,n)
            fig,axes=plt.subplots(3,3,figsize=(12,12),constrained_layout=True)
            rdir=OUT/'rasters'/label;rdir.mkdir(parents=True,exist_ok=True)
            for i,f in enumerate([3,10,30]):
                g=aggregate(raw['H2020'],v,w,f);a=g['coarse'];b=g['spatial_then_semantic'];ok=(a!=255)&(b!=255)&(g['total']>0);different=ok&(a!=b)
                prior=old[(old.site==sid)&(old.scale==f)].iloc[0]
                assert int(ok.sum())==prior.n_joint and int(different.sum())==prior.n_disagree
                for j,(z,title) in enumerate([(a,'Semantic then spatial'),(b,'Spatial then semantic')]):
                    display=np.full(z.shape,3,np.uint8)
                    for c in [1,2,3]:display[z==c]=c-1
                    axes[i,j].imshow(display,cmap=ListedColormap(['#d9a03b','#37866f','#eae9e4','white']),vmin=-.5,vmax=3.5,extent=[0,n,n,0],interpolation='nearest');axes[i,j].set_title(f'{f}x{f} | {title}',fontsize=10)
                diff=np.full(a.shape,255,np.uint8);diff[ok]=0;diff[different]=1
                display=np.where(diff==255,2,diff)
                axes[i,2].imshow(display,cmap=ListedColormap(['#f1f1ed','#d52436','#555555']),vmin=-.5,vmax=2.5,extent=[0,n,n,0],interpolation='nearest')
                axes[i,2].set_title(f'Difference: {100*different.sum()/ok.sum():.3f}%',fontsize=10)
                for ax in axes[i]:ax.set(xlabel='Native column',ylabel='Native row')
                for name,z in [('semantic_first',a),('spatial_first',b),('difference',diff)]:tif(rdir/f'{name}_f{f}.tif',z,tr*rasterio.Affine.scale(f,f),255)
                stats.append(dict(display_id=label,site=sid,group=s['group'],scale=f,n_joint=int(ok.sum()),n_disagreement=int(different.sum()),rate=float(different.sum()/ok.sum())))
                core=np.zeros_like(v);core[30:n-30,30:n-30]=True;core &= v
                for oy in [0,f//3,2*f//3]:
                    for ox in [0,f//3,2*f//3]:
                        h=(n-oy)//f*f;ww=(n-ox)//f*f;sl=np.s_[oy:oy+h,ox:ox+ww];pg=aggregate(raw['H2020'][sl],v[sl],w[sl],f)
                        overlap=blocks(w[sl]*core[sl],f);pa=pg['coarse'];pb=pg['spatial_then_semantic'];joint=(pa!=255)&(pb!=255)&(overlap>0);df=joint&(pa!=pb)
                        assert np.isclose(overlap.sum(),area(core,w),rtol=1e-12)
                        phases.append(dict(site=sid,group=s['group'],scale=f,oy=oy,ox=ox,R_NC_count=ratio(df.sum(),joint.sum()),R_NC_area=ratio(overlap[df].sum(),overlap[joint].sum())))
            fig.suptitle(f'{label} | 2020 | identical extent and semantic classes',fontsize=14)
            fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#d9a03b','SD'),('#37866f','SL'),('#eae9e4','Others'),('#d52436','Disagreement'),('#555555','Not jointly decidable')]],loc='outside lower center',ncol=5)
            for ext in ['png','pdf']:fig.savefig(FIG/f'{label}_three_scales_order_difference.{ext}',dpi=220,bbox_inches='tight')
            book.savefig(fig,bbox_inches='tight');plt.close(fig)
            print('Order comparison completed: '+label,flush=True)
    write_csv(OUT/'map_statistics.csv',stats);write_csv(OUT/'phase_all_scales.csv',phases)
    phases=pd.DataFrame(phases);fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    for j,f in enumerate([3,10,30]):
        joined=old[(old.scale==f)&old.group.isin(['High','Low'])].merge(sel[['id','H_SL']],left_on='site',right_on='id')
        for group,color in [('Low','#357bab'),('High','#d5643d')]:
            g=joined[joined.group==group];axes[0,j].scatter(g.H_SL,100*g.R_NC_count,label=group,color=color)
        axes[0,j].set(title=f'{f}x{f} support',xlabel='Within-SL entropy (bits)',ylabel='Non-commutative cells (%)');axes[0,j].legend()
        vals=[phases[(phases.scale==f)&(phases.group==g)].groupby('site').R_NC_count.agg(lambda x:100*(x.max()-x.min())).values for g in ['Low','High']]
        axes[1,j].boxplot(vals,labels=['Low','High']);axes[1,j].set(ylabel='Nine-phase range (percentage points)',title=f'{f}x{f}: common evaluation core')
    for ext in ['png','pdf']:fig.savefig(FIG/f'Figure_4_4_All_scales.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    for s in ds.values():s.close()
    assert all(sha(path)==h for path,h in protected.items())
    dump(OUT/'complete.json',dict(time=now(),regions=24,scales=[3,10,30],map_panels=216,phase_rows=len(phases),main_rates_match_original=True,no_significance_tests=True,old_files_unchanged=True))
if __name__=='__main__':main()
