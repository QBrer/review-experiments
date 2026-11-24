"""All 24 frozen regions: native/scaled maps and task outputs; no reselection."""
from core import *
from framework_walkthrough import tif
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch,Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from rasterio.enums import Resampling

OUT=ROOT/'results/region_walkthrough_24'
FIG=ROOT/'figures/region_atlas_24'
COLORS=['#d8a13d','#3b8a72','#e9e8e2','#ffffff']
def picture(ax,a,n,title):
    z=np.full(a.shape,3,np.uint8)
    for c in [1,2,3]:z[a==c]=c-1
    ax.imshow(z,extent=[0,n,n,0],origin='upper',interpolation='nearest',cmap=ListedColormap(COLORS),vmin=-.5,vmax=3.5)
    ax.set(title=title,xlabel='Native column',ylabel='Native row')
def legend(fig):
    fig.legend(handles=[Patch(facecolor=c,label=t) for c,t in zip(COLORS,['SD','SL','Others','Invalid / unresolved'])],loc='outside lower center',ncol=4)
def save(fig,name):
    for ext in ['png','pdf']:fig.savefig(FIG/f'{name}.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
def main():
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True);(FIG/'individual').mkdir(exist_ok=True)
    ds=open_inputs();off=offsets(ds);ref=ds['H2020'];sel=pd.read_csv(ROOT/'selection/selected_regions.csv').sort_values('selection_order').copy()
    for group,prefix in [('High','H'),('Low','L')]:sel.loc[sel.group==group,'display_id']=[f'{prefix}{i:02d}' for i in range(1,13)]
    write_csv(OUT/'region_index.csv',sel.to_dict('records'))
    protected={str(p):sha(p) for p in [ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv']}
    dump(OUT/'protocol.json',dict(created=now(),purpose='paper presentation and five-step task walkthrough within the existing24 selected regions',mask='same five-input common legal-code mask as Experiments1/2',years_for_display=[2010,2020],scales=[1,3,10,30],label_map={'1':'SD','2':'SL','3':'Others'},selection_sha256=sha(ROOT/'selection/selected_regions.csv'),illustrated_examples='H01 and L01, first selected in each group; no outcome selection',protected=protected))
    # Study products in section4.5.1, without an extra historical-case marker.
    fig,axes=plt.subplots(2,1,figsize=(13,11),constrained_layout=True)
    palettes={'W2020':['#39734c','#86a65c','#b6d19d','#a0b38b','#d7ca7f','#d6b89a','#67b5a6','#5a91b5','#ddbaa4','#bc858a','#c6c1b5','#dfc888','#e9c459','#d5e0e8'],'H2020':['#dfb15d','#e8cf7f','#b4c88f','#81af88','#418676','#dbe2dc']}
    for ax,key,title,codes in [(axes[0],'W2020','(a) Wang 2020: land-cover context',list(range(1,15))),(axes[1],'H2020','(b) Han 2020: sandy-desert and sandy-land classes',[1,21,22,23,24,3])]:
        src=ds[key];width=2400;height=round(width*src.height/src.width);a=src.read(1,out_shape=(height,width),resampling=Resampling.nearest);z=np.full(a.shape,len(codes),np.uint8)
        for i,c in enumerate(codes):z[a==c]=i
        palette=palettes[key];ax.imshow(z,extent=[src.bounds.left,src.bounds.right,src.bounds.bottom,src.bounds.top],cmap=ListedColormap(palette+['white']),vmin=-.5,vmax=len(codes)+.5,interpolation='nearest',alpha=.8)
        for s in sel.itertuples():
            color='#b42a43' if s.group=='High' else '#175fa2';x0,y0=ref.transform*(s.col,s.row);x1,y1=ref.transform*(s.col+1200,s.row+1200)
            ax.add_patch(Rectangle((x0,y1),x1-x0,y0-y1,fill=False,edgecolor=color,lw=.8));ax.scatter(s.lon,s.lat,s=13,color=color)
            ax.annotate(s.display_id,(s.lon,s.lat),xytext=(4,4),textcoords='offset points',fontsize=7,color=color)
        names=[str(c) for c in codes] if key=='W2020' else ['SD','SL21','SL22','SL23','SL24','Others']
        leg=ax.legend(handles=[Patch(color=c,label=t) for c,t in zip(palette,names)],loc='upper left',ncol=7,fontsize=7,title='Source class codes' if key=='W2020' else 'Source classes');ax.add_artist(leg)
        ax.legend(handles=[Patch(facecolor='none',edgecolor='#b42a43',label='High: H01-H12'),Patch(facecolor='none',edgecolor='#175fa2',label='Low: L01-L12')],loc='lower right',fontsize=8)
        ax.set(title=title,xlabel='Longitude (degrees E)',ylabel='Latitude (degrees N)',xlim=(87.5,126.3),ylim=(37.2,53.7))
    save(fig,'Figure_4_2_Study_regions')
    results=[];checks=[];examples={};index=[]
    with PdfPages(FIG/'All_24_regions_multiscale_atlas.pdf') as book:
        for s in sel.to_dict('records'):
            sid=s['id'];label=s['display_id'];n=1200;raw,v=read_window(ds,off,int(s['row']),int(s['col']),n);tr=ref.window_transform(Window(int(s['col']),int(s['row']),n,n));w=weights(tr,n)
            native={y:LUT[raw[f'H{y}']].copy() for y in [2010,2020]}
            for a in native.values():a[~v]=255
            rdir=OUT/'rasters'/label;rdir.mkdir(parents=True,exist_ok=True);agg={};areas={};maxerr=0.
            tif(rdir/'common_valid.tif',v.astype(np.uint8),tr,0)
            for y in [2010,2020]:
                tif(rdir/f'classes_{y}_native.tif',native[y],tr,255)
                areas[y]=area(v&(native[y]==2),w)
                for f in [3,10,30]:
                    g=aggregate(raw[f'H{y}'],v,w,f);agg[y,f]=g
                    tif(rdir/f'classes_{y}_f{f}.tif',g['coarse'],tr*rasterio.Affine.scale(f,f),255)
                    proportions=g['p'].copy();proportions[:,g['total']<=0]=-9999
                    tif(rdir/f'proportions_{y}_f{f}.tif',proportions,tr*rasterio.Affine.scale(f,f),-9999)
                    restored=float(np.sum(g['p'][1]*g['total']));err=abs(restored-areas[y]);maxerr=max(maxerr,err);assert np.isclose(restored,areas[y],rtol=1e-12,atol=1e-6)
            ex=v&(native[2010]!=2)&(native[2020]==2);co=v&(native[2010]==2)&(native[2020]!=2)
            change=np.full((n,n),255,np.uint8);change[v]=0;change[ex]=1;change[co]=2;tif(rdir/'SL_directional_change_2010_2020.tif',change,tr,255)
            e,c=area(ex,w),area(co,w);balance=abs(e-c-(areas[2020]-areas[2010]));assert balance<1e-6
            row=dict(display_id=label,site=sid,group=s['group'],coverage=float(v.mean()),domain_km2=area(v,w)/1e6,SL2010_km2=areas[2010]/1e6,SL2020_km2=areas[2020]/1e6,expansion_km2=e/1e6,contraction_km2=c/1e6,net_change_km2=(areas[2020]-areas[2010])/1e6,change_union_km2=(e+c)/1e6,area_max_error_m2=maxerr,balance_error_m2=balance)
            results.append(row);checks.append(dict(display_id=label,source_window_sha256={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in raw.items()},transform=list(tr),roundtrip_passed=True,conservation_passed=True))
            fig,axes=plt.subplots(2,4,figsize=(15,8),constrained_layout=True)
            for i,y in enumerate([2010,2020]):
                for j,f in enumerate([1,3,10,30]):picture(axes[i,j],native[y] if f==1 else agg[y,f]['coarse'],n,f'{y} | '+('Native (1x1)' if f==1 else f'{f}x{f} support'))
            legend(fig);fig.suptitle(f'{label} ({s["group"]}) | same extent, area-dominant classes | {s["lon"]:.3f} E, {s["lat"]:.3f} N',fontsize=13)
            for ext in ['png','pdf']:fig.savefig(FIG/'individual'/f'{label}_2010_2020_multiscale.{ext}',dpi=200,bbox_inches='tight')
            book.savefig(fig,bbox_inches='tight');plt.close(fig)
            index.append(dict(display_id=label,site=sid,png=f'individual/{label}_2010_2020_multiscale.png',pdf=f'individual/{label}_2010_2020_multiscale.pdf'))
            if label in ['H01','L01']:examples[label]=dict(native=native,agg=agg,change=change,results=row)
            print(f'Atlas and task outputs: {label}',flush=True)
    write_csv(OUT/'task_results_24.csv',results);dump(OUT/'raster_checks.json',checks);write_csv(FIG/'atlas_index.csv',index)
    fig,axes=plt.subplots(2,4,figsize=(15,8),constrained_layout=True)
    for i,label in enumerate(['H01','L01']):
        for j,f in enumerate([1,3,10,30]):picture(axes[i,j],examples[label]['native'][2020] if f==1 else examples[label]['agg'][2020,f]['coarse'],1200,label+' | '+('Native' if f==1 else f'{f}x{f}'))
    legend(fig);fig.suptitle('Same region and semantic classes across spatial supports | 2020');save(fig,'Figure_4_5_Scale_examples')
    fig,axes=plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
    for i,label in enumerate(['H01','L01']):
        for j,y in enumerate([2010,2020]):
            im=axes[i,j].imshow(examples[label]['agg'][y,30]['p'][1],cmap='YlGn',vmin=0,vmax=1,extent=[0,1200,1200,0],interpolation='nearest');axes[i,j].set_title(f'{label} | SL fraction {y} (30x30)')
        z=examples[label]['change'].copy();z[z==255]=3
        axes[i,2].imshow(z,cmap=ListedColormap(['#efefea','#24849a','#bd4b57','white']),vmin=-.5,vmax=3.5,extent=[0,1200,1200,0],interpolation='nearest');axes[i,2].set_title(f'{label} | native SL change')
    for ax in axes.flat:ax.set(xlabel='Native column',ylabel='Native row')
    fig.colorbar(im,ax=axes[:,:2],label='SL area fraction',shrink=.6)
    fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#efefea','No SL membership change'),('#24849a','SL expansion'),('#bd4b57','SL contraction')]],loc='outside lower center',ncol=3)
    fig.suptitle('Task-oriented outputs: class composition and change locations');save(fig,'Figure_4_6_Task_outputs')
    # Replot experiment2 with the24 selected regions only; values are unchanged.
    order=pd.read_csv(ROOT/'results/experiment_2/order.csv');order=order[order.group.isin(['Low','High'])]
    phase=pd.read_csv(ROOT/'results/experiment_2/phase.csv');phase=phase[phase.group.isin(['Low','High'])]
    fig,axes=plt.subplots(1,3,figsize=(14,4.4),constrained_layout=True)
    for group,color in [('Low','#357bab'),('High','#d5643d')]:
        g=order[order.group==group]
        for sid,gg in g.groupby('site'):axes[0].plot(gg.scale,100*gg.R_NC_count,color=color,alpha=.15)
        mean=g.groupby('scale').R_NC_count.mean();axes[0].plot(mean.index,100*mean.values,'o-',color=color,label=group)
        joined=g[g.scale==30].merge(sel[['id','H_SL']],left_on='site',right_on='id');axes[2].scatter(joined.H_SL,100*joined.R_NC_count,color=color,label=group)
    axes[0].set(xlabel='Aggregation factor',ylabel='Non-commutative cells (%)',xticks=[3,10,30]);axes[0].legend()
    values=[phase[phase.group==g].groupby('site').R_NC_count.agg(lambda x:100*(x.max()-x.min())).values for g in ['Low','High']]
    axes[1].boxplot(values,labels=['Low','High']);axes[1].set(ylabel='Phase range (percentage points)',title='30x30 support')
    axes[2].set(xlabel='Within-SL entropy (bits)',ylabel='Non-commutative cells (%)');axes[2].legend();save(fig,'Figure_4_4_Noncommutativity_24')
    # Human navigable full atlas index.
    lines=['# 24个样区多尺度分类图集','每页两行对应2010、2020；四列对应原始、3×3、10×10、30×30。所有面板保持同一地理范围和语义图例。','粗尺度图为语义合并后的有效面积优势类别图；比例图单独保存于对应GeoTIFF，不混称融合影像。','']
    for i in index:lines.append(f'- [{i["display_id"]} PNG]({i["png"]}) · [PDF]({i["pdf"]})')
    (FIG/'图集索引.md').write_text('\n\n'.join(lines),encoding='utf8')
    for d in ds.values():d.close()
    assert all(sha(p)==h for p,h in protected.items())
    dump(OUT/'complete.json',dict(time=now(),regions=24,pages=24,classification_panels=192,outputs_per_region=16,all_checks_passed=True,existing_scientific_results_unchanged=True,example_ids=['H01','L01']))
if __name__=='__main__':main()
