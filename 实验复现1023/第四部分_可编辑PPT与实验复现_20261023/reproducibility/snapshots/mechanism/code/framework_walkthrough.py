"""Single-case execution of five-step framework, no competing strategy or inference."""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

OUT=ROOT/'results/experiment_3_framework_walkthrough'
def tif(path,a,tr,nodata):
    if a.ndim==2:a=a[None]
    with rasterio.open(path,'w',driver='GTiff',height=a.shape[1],width=a.shape[2],count=a.shape[0],dtype=a.dtype,crs='EPSG:4326',transform=tr,nodata=nodata,compress='deflate',tiled=True) as d:d.write(a)
    with rasterio.open(path) as d:assert np.array_equal(d.read(),a)

def main():
    if (OUT/'run_complete.json').exists():raise RuntimeError('Completed example exists; preserve and version it')
    OUT.mkdir(parents=True,exist_ok=True)
    h=next(BASE.glob('A multi*/MPSDSL'))
    protected={str(x):sha(x) for x in [ROOT/'reports/4.5_正文.md',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/experiment_3_workflow_v2/all_results.csv']}
    policy=dict(created_at=now(),purpose='five-step procedural illustration only; third component of section4.5',case='B2 historical selected case, not independent validation',years=[2010,2020],window=dict(row_Han2020=52983,col_Han2020=78382,width=1020,height=1020),tasks={'area':'SL areas and net change, full-window and 30x30 support, retain proportions','location':'SL expansion/contraction locations on native grid; preserve native spatial detail'},mapping={1:'SD',21:'SL',22:'SL',23:'SL',24:'SL',3:'Others'},mask='Han2010 AND Han2020 legal codes',decision='area -> 30x30 three-class proportions; location -> native three-class dates and native directional change',acceptance='grid exact within1e-6 pixel; class-area conservation rtol1e-12; net balance atol1e-6m2; full valid coverage; roundtrip exact',no_comparator=True,no_p_values=True,no_accuracy_claim=True,no_refinement_threshold=True,protected_sha256=protected,code_sha256=sha(__file__))
    dump(OUT/'execution_policy.json',policy)
    ds={y:rasterio.open(h/f'{y}.tif') for y in [2010,2020]};ref=ds[2020];n=1020;tr=ref.window_transform(Window(78382,52983,n,n));raw={};metadata=[]
    for y,d in ds.items():
        c,r=(~d.transform)*(tr.c,tr.f);error=max(abs(c-round(c)),abs(r-round(r)));assert error<1e-6 and d.crs==ref.crs and np.allclose(d.res,ref.res,rtol=1e-12,atol=0)
        sr,sc=int(round(r)),int(round(c));a=d.read(1,window=Window(sc,sr,n,n));assert a.shape==(n,n)
        assert set(np.unique(a)).issubset(set(FINE)|{0});raw[y]=a
        metadata.append(dict(year=y,path=str(h/f'{y}.tif'),row=sr,col=sc,width=n,height=n,crs=str(d.crs),transform=list(d.transform),window_transform=list(d.window_transform(Window(sc,sr,n,n))),grid_residual_pixels=error,nodata=d.nodata,classes=np.unique(a).tolist(),window_sha256=hashlib.sha256(a.tobytes()).hexdigest()))
    v=np.isin(raw[2010],FINE)&np.isin(raw[2020],FINE);w=weights(tr,n);domain=area(v,w);native={y:LUT[a].copy() for y,a in raw.items()}
    for a in native.values():a[~v]=255
    dump(OUT/'input_metadata.json',metadata)
    (OUT/'rasters').mkdir(exist_ok=True);tif(OUT/'rasters/common_valid.tif',v.astype(np.uint8),tr,0)
    props={};taskrows=[];checks=[]
    for y in [2010,2020]:
        total=blocks(w*v,30);amount=np.stack([blocks(w*(v&(native[y]==c)),30) for c in [1,2,3]])
        props[y]=np.divide(amount,total[None],out=np.full_like(amount,-9999),where=total[None]>0)
        tif(OUT/'rasters'/f'classes_{y}.tif',native[y],tr,255)
        tif(OUT/'rasters'/f'proportions_{y}_f30.tif',props[y],tr*rasterio.Affine.scale(30,30),-9999)
        for c,name in [(1,'SD'),(2,'SL'),(3,'Others')]:
            src=area(v&(native[y]==c),w);out=float(np.sum(np.where(total>0,props[y][c-1]*total,0)))
            assert np.isclose(src,out,rtol=1e-12,atol=1e-6)
            taskrows.append(dict(year=y,class_name=name,native_area_km2=src/1e6,proportion_integrated_km2=out/1e6,absolute_difference_m2=abs(src-out)))
        # Semantic conservation checked independently from original fine codes.
        sl_fine=sum(area(v&(raw[y]==c),w) for c in [21,22,23,24]);sl_coarse=area(v&(native[y]==2),w)
        assert np.isclose(sl_fine,sl_coarse,rtol=1e-12,atol=1e-6)
        checks.append(dict(check='semantic_SL_area_conservation',year=y,passed=True,error_m2=abs(sl_fine-sl_coarse)))
    expansion=v&(native[2010]!=2)&(native[2020]==2);contraction=v&(native[2010]==2)&(native[2020]!=2)
    change=np.full((n,n),255,np.uint8);change[v]=0;change[expansion]=1;change[contraction]=2
    assert not (expansion&contraction).any()
    # SD<->Others is unchanged only with respect to SL membership, not all-class state.
    tif(OUT/'rasters/SL_directional_change_2010_2020.tif',change,tr,255)
    matrix=np.array([[area(v&(native[2010]==i)&(native[2020]==j),w) for j in [1,2,3]] for i in [1,2,3]])
    for i in range(3):
        assert np.isclose(matrix[i].sum(),area(v&(native[2010]==i+1),w),rtol=1e-12,atol=1e-6)
        assert np.isclose(matrix[:,i].sum(),area(v&(native[2020]==i+1),w),rtol=1e-12,atol=1e-6)
    ex=area(expansion,w);co=area(contraction,w);sl0=area(v&(native[2010]==2),w);sl1=area(v&(native[2020]==2),w)
    assert np.isclose(ex-co,sl1-sl0,rtol=1e-12,atol=1e-6)
    write_csv(OUT/'area_results.csv',taskrows);write_csv(OUT/'transition_matrix.csv',[dict(from_class=i+1,to_class=j+1,area_km2=matrix[i,j]/1e6) for i in range(3) for j in range(3)])
    result=dict(domain_km2=domain/1e6,valid_pixels=int(v.sum()),total_pixels=v.size,coverage=float(v.mean()),SL2010_km2=sl0/1e6,SL2020_km2=sl1/1e6,expansion_km2=ex/1e6,contraction_km2=co/1e6,change_union_km2=(ex+co)/1e6,net_change_km2=(sl1-sl0)/1e6,net_balance_error_m2=abs((ex-co)-(sl1-sl0)),area_preservation_max_error_m2=max(x['absolute_difference_m2'] for x in taskrows),support_cells=[34,34],native_cells=[1020,1020],classification_accuracy_evaluated=False)
    dump(OUT/'task_results.json',result)
    trace=[dict(step=1,name='Define the task',input='B2; Han2010/2020; SL definition',decision='separate composition totals from location-specific change',output='area and native-location task contracts'),dict(step=2,name='Diagnose mismatches',input='raster metadata and legal codes',decision='2010 source row differs by119; coordinate-aligned windows, no resampling; hierarchical mapping',output='input_metadata.json and common_valid.tif'),dict(step=3,name='Analyze constraints',input='task contracts; spatial support; temporal pair',decision='proportion sufficient for full-cell area; cannot infer within-cell change locations or gross turnover from proportions alone',output='task-specific representation rules'),dict(step=4,name='Organize alignment',input='common-mask mapped labels',decision='area branch: sum class areas then proportions; location branch: preserve native paired positions then SL event coding',output='30x30 proportions, native classes and directional changes'),dict(step=5,name='Validate alignment',input='outputs and source conservation identities',decision='grid, semantic mass, transition margins, expansion-contraction balance and raster roundtrip checked; no external truth',output='validation.json; residual uncertainty explicitly retained')]
    dump(OUT/'five_step_trace.json',trace)
    dump(OUT/'validation.json',dict(time=now(),passed=True,checks=checks+[{ 'check':z,'passed':True} for z in ['integer_grid_alignment','proportion_area_conservation','transition_margins','net_change_balance','event_disjointness','raster_exact_roundtrip']],interpretation='implementation consistency only; no external validation, no fitted accuracy thresholds'))
    fdir=ROOT/'figures/framework_walkthrough';fdir.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
    for ax,y in zip(axes[0,:2],[2010,2020]):
        z=native[y].astype(int)-1;z[native[y]==255]=3
        ax.imshow(z,cmap=ListedColormap(['#dca338','#4a9077','#efefea','white']),vmin=-.5,vmax=3.5,extent=[0,n,n,0],interpolation='nearest');ax.set_title(f'Native classes {y}')
    axes[0,2].axis('off');axes[0,2].text(.02,.94,'Tasks and representations\n\nArea: 34 x 34 proportion cells\n\nLocation: 1020 x 1020 labels\n\n2010 source row: '+str(metadata[0]['row'])+'\n2020 source row: '+str(metadata[1]['row'])+'\n\nNo comparative strategy\nNo accuracy inference',va='top',fontsize=11)
    for ax,y in zip(axes[1,:2],[2010,2020]):
        im=ax.imshow(props[y][1],vmin=0,vmax=1,cmap='YlGn',extent=[0,n,n,0],interpolation='nearest');ax.set_title(f'SL fraction {y} | 30x30 support')
    fig.colorbar(im,ax=axes[1,:2],shrink=.6,label='SL area fraction')
    z=change.copy();z[z==255]=3;axes[1,2].imshow(z,cmap=ListedColormap(['#efefea','#257e9a','#bd4b57','white']),vmin=-.5,vmax=3.5,extent=[0,n,n,0],interpolation='nearest');axes[1,2].set_title('Native SL directional change')
    for ax in [*axes[0,:2],*axes[1,:]]:ax.set(xlabel='Native column offset',ylabel='Native row offset')
    fig.legend(handles=[Patch(color=c,label=l) for c,l in [('#4a9077','SL'),('#dca338','SD'),('#efefea','Others / no SL change'),('#257e9a','SL expansion'),('#bd4b57','SL contraction')]],loc='outside lower center',ncol=5)
    for ext in ['png','pdf']:fig.savefig(fdir/f'Figure_4_4_Framework_walkthrough.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    for d in ds.values():d.close()
    assert all(sha(path)==val for path,val in protected.items())
    dump(OUT/'run_complete.json',dict(time=now(),passed=True,old_outputs_unchanged=True,source_data_read_only=True,results=result))
    print(json.dumps(clean(result),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
