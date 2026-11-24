"""Additional descriptive figures only; no parameter tuning or new inference."""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch,Rectangle
from rasterio.enums import Resampling

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'savefig.dpi':240})
OUT=ROOT/'figures/additional';OUT.mkdir(exist_ok=True)
COLORS=['#ddaa39','#508f78','#f0f0eb','#ffffff']
def save(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight');fig.savefig(OUT/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def mapped_img(a):
    b=np.full(a.shape,3,np.uint8)
    for k in [1,2,3]:b[a==k]=k-1
    return b
def paint(ax,a,title,n):
    ax.imshow(mapped_img(a),cmap=ListedColormap(COLORS),vmin=-.5,vmax=3.5,origin='upper',extent=[0,n,n,0],interpolation='nearest')
    ax.set(title=title,xlabel='Native-grid column offset',ylabel='Native-grid row offset')
def main():
    selection=pd.read_csv(ROOT/'selection/selected_regions.csv').sort_values('selection_order')
    selection['display_id']=''
    for group,prefix in [('High','H'),('Low','L')]:
        ids=selection.index[selection.group==group]
        selection.loc[ids,'display_id']=[f'{prefix}{i:02d}' for i in range(1,len(ids)+1)]
    write_csv(OUT/'figure_region_labels.csv',selection.to_dict('records'))
    p=cfg();ds=open_inputs();off=offsets(ds)
    # Actual product overview; nearest-neighbor display is never an analytical resampling.
    fig,axes=plt.subplots(2,1,figsize=(13,11),constrained_layout=True)
    wc=['#2f7147','#839d50','#b7d29f','#a1b68d','#d4c978','#d6bca3','#65b9ad','#608eae','#e0bba8','#bf898f','#ccc2b2','#e4ca89','#eccb55','#d2dfeb']
    hn=['#dfb15d','#e8cf7f','#b4c88f','#81af88','#418676','#dbe2dc']
    for ax,key,title,palette,codes in [(axes[0],'W2020','(a) Wang 2020: land-cover context',wc,list(range(1,15))),(axes[1],'H2020','(b) Han 2020: sandy-desert / sandy-land product',hn,[1,21,22,23,24,3])]:
        src=ds[key];width=2200;height=round(width*src.height/src.width)
        ar=src.read(1,out_shape=(height,width),resampling=Resampling.nearest)
        idx=np.full(ar.shape,len(codes),np.uint8)
        for i,code in enumerate(codes):idx[ar==code]=i
        ax.imshow(idx,extent=[src.bounds.left,src.bounds.right,src.bounds.bottom,src.bounds.top],origin='upper',cmap=ListedColormap(palette+['white']),vmin=-.5,vmax=len(codes)+.5,interpolation='nearest',alpha=.77)
        for row in selection.itertuples():
            color='#af2541' if row.group=='High' else '#175caa';x0,y0=ds['H2020'].transform*(row.col,row.row);x1,y1=ds['H2020'].transform*(row.col+1200,row.row+1200)
            ax.add_patch(Rectangle((x0,y1),x1-x0,y0-y1,fill=False,edgecolor=color,lw=.9))
            ax.scatter(row.lon,row.lat,s=15,c=color,zorder=4)
            ax.annotate(row.display_id,(row.lon,row.lat),xytext=(4,4),textcoords='offset points',fontsize=7,color=color)
        ax.scatter(p['B2']['lon'],p['B2']['lat'],marker='*',s=110,c='#713d8f',edgecolors='white',lw=.6,zorder=5)
        ax.annotate('B2 (historical)',(p['B2']['lon'],p['B2']['lat']),xytext=(6,-12),textcoords='offset points',fontsize=8,color='#713d8f')
        ax.set(title=title,xlabel='Longitude (degrees E)',ylabel='Latitude (degrees N)',xlim=(87.5,126.3),ylim=(37.2,53.7))
        names=['SD','SL21','SL22','SL23','SL24','Others'] if key=='H2020' else [str(i) for i in codes]
        ax.legend(handles=[Patch(facecolor=c,label=t) for c,t in zip(palette,names)],loc='upper left',ncol=7,fontsize=7,title='Source class codes' if key=='W2020' else 'Source classes',framealpha=.95)
    fig.suptitle('Study products and frozen new windows: 12 High + 12 Low; B2 shown separately',fontsize=14)
    save(fig,'Figure_S1_Study_area_products')
    # Display first-selected window in each group, not highest outcome.
    cases=[dict(id='B2',group='Historical',row=p['B2']['row'],col=p['B2']['col'],size=1020,display_id='B2')]
    for group in ['High','Low']:
        a=selection[selection.group==group].iloc[0].to_dict();a['size']=1200;cases.append(a)
    stats=[];fig,axes=plt.subplots(3,3,figsize=(13,12),constrained_layout=True)
    for i,s in enumerate(cases):
        n=s['size'];raw,v=read_window(ds,off,int(s['row']),int(s['col']),n);tr=ds['H2020'].window_transform(Window(s['col'],s['row'],n,n));w=weights(tr,n)
        g=aggregate(raw['H2020'],v,w,30);a=g['coarse'];b=g['spatial_then_semantic'];ok=(a!=255)&(b!=255)&(g['total']>0);dif=ok&(a!=b)
        paint(axes[i,0],a,f"{s['display_id']} | semantic then spatial",n);paint(axes[i,1],b,'Spatial then semantic',n)
        di=np.full(a.shape,2,np.uint8);di[ok]=0;di[dif]=1
        axes[i,2].imshow(di,cmap=ListedColormap(['#f0f0eb','#b92e4d','#333333']),vmin=-.5,vmax=2.5,origin='upper',extent=[0,n,n,0],interpolation='nearest')
        rate=100*ratio(dif.sum(),ok.sum());axes[i,2].set(title=f'Disagreement: {rate:.3f}% of joint cells',xlabel='Native-grid column offset',ylabel='Native-grid row offset')
        stats.append(dict(display_id=s['display_id'],site=s['id'],selection='historical B2' if i==0 else 'first selected within group; no outcome ranking',n_joint=int(ok.sum()),n_disagreement=int(dif.sum()),R_NC_count=rate/100))
    fig.legend(handles=[Patch(color=c,label=t) for c,t in zip(COLORS,['SD','SL','Others','Unresolved'])]+[Patch(color='#b92e4d',label='Disagree'),Patch(color='#333333',label='Not jointly decidable')],loc='outside lower center',ncol=6)
    fig.suptitle('Spatial evidence of non-commutativity | 2020, 30x30 native pixels',fontsize=14)
    save(fig,'Figure_S2_Operation_order_maps');write_csv(OUT/'spatial_examples.csv',stats)
    # B2 detailed three panels in the style of user's example, full historical extent.
    s=cases[0];n=1020;raw,v=read_window(ds,off,s['row'],s['col'],n);tr=ds['H2020'].window_transform(Window(s['col'],s['row'],n,n));w=weights(tr,n);g=aggregate(raw['H2020'],v,w,30)
    a=g['coarse'];b=g['spatial_then_semantic'];ok=(a!=255)&(b!=255)&(g['total']>0);dif=ok&(a!=b)
    fig,ax=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True)
    paint(ax[0],a,'(a) Semantic then spatial',n);paint(ax[1],b,'(b) Spatial then semantic',n)
    d=np.full(a.shape,2,np.uint8);d[ok]=0;d[dif]=1
    ax[2].imshow(d,cmap=ListedColormap(['#f0f0eb','#b92e4d','#333333']),vmin=-.5,vmax=2.5,extent=[0,n,n,0],interpolation='nearest');ax[2].set(title='(c) Disagreement (189 / 1156 cells)',xlabel='Native-grid column offset',ylabel='Native-grid row offset')
    fig.legend(handles=[Patch(color=c,label=t) for c,t in zip(COLORS,['SD','SL','Others','Unresolved'])]+[Patch(color='#b92e4d',label='Disagreement')],loc='outside lower center',ncol=5)
    fig.suptitle('B2 historical case | 2020 | 30x30 support | full 1020x1020 window')
    save(fig,'Figure_S3_B2_Order_difference')
    # Decompose what the framework actually retains; uses saved primary-endpoint output.
    fig,axes=plt.subplots(2,3,figsize=(12.5,8.5),constrained_layout=True)
    zbase=np.load(ROOT/'results/experiment_3/artifacts/B2/change_2010_2020_Baseline_f30.npz')
    z=np.load(ROOT/'results/experiment_3/artifacts/B2/change_2010_2020_Proposed_f30.npz')
    native0=LUT[raw['H2010']];native1=LUT[raw['H2020']];ref=v&((native0==2)!=(native1==2))
    aa=expand(z['start'],30);bb=expand(z['end'],30);refined=np.zeros_like(v)
    for k,idx in enumerate(z['refined_indices']):
        r,c=divmod(int(idx),34);sl=np.s_[r*30:(r+1)*30,c*30:(c+1)*30]
        aa[sl]=z['native_start'][k];bb[sl]=z['native_end'][k];refined[sl]=True
    ba=expand(zbase['start'],30);bbas=expand(zbase['end'],30)
    pred0=v&(ba!=255)&(bbas!=255)&((ba==2)!=(bbas==2));pred1=v&(aa!=255)&(bb!=255)&((aa==2)!=(bb==2))
    for ax,m,title in zip(axes[0],[ref,pred0,pred1],['(a) Native internal reference','(b) Baseline change','(c) Proposed change']):
        ax.imshow(m,cmap=ListedColormap(['#f5f5f0','#278b83']),vmin=0,vmax=1,extent=[0,n,n,0],interpolation='nearest');ax.set_title(title)
    axes[1,0].imshow(refined&v,cmap=ListedColormap(['#f5f5f0','#ba8cce']),vmin=0,vmax=1,extent=[0,n,n,0],interpolation='nearest');axes[1,0].set_title('(d) Native detail retained')
    for ax,pred,title in [(axes[1,1],pred0,'(e) Baseline errors'),(axes[1,2],pred1,'(f) Proposed errors')]:
        error=np.zeros(v.shape,np.uint8);error[ref&~pred]=1;error[pred&~ref]=2;error[~v]=3
        ax.imshow(error,cmap=ListedColormap(['#f5f5f0','#bd344c','#3264ac','#333333']),vmin=-.5,vmax=3.5,extent=[0,n,n,0],interpolation='nearest');ax.set_title(title)
    for ax in axes.flat:ax.set(xlabel='Native-grid column offset',ylabel='Native-grid row offset')
    fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#278b83','Change'),('#ba8cce','Refined to native'),('#bd344c','Missed change'),('#3264ac','Extra change')]],loc='outside lower center',ncol=4)
    fig.suptitle('B2 | 2010-2020, factor 30: preservation mechanism, not external validation')
    save(fig,'Figure_S4_B2_Change_and_refinement')
    for s in ds.values():s.close()
    dump(OUT/'figure_provenance.json',dict(time=now(),parameters_sha256=sha(ROOT/'parameters/frozen_parameters.json'),selection_sha256=sha(ROOT/'selection/selected_regions.csv'),case_choice=stats,overview='nearest-neighbor display only; input full extent; no administrative boundary claimed',axes='local maps use original pixel coordinates, not fictitious equal-meter squares',new_outcome_selection=False))
    print('Four additional figures generated as PNG/PDF; labels and provenance saved.')
if __name__=='__main__':main()
