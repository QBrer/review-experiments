"""Rerun task branches and record actual decisions; no competing framework."""
from core import *
from framework_walkthrough import tif
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

OUT=ROOT/'results/framework_decision_walkthrough'
FIG=ROOT/'figures/framework_decision_walkthrough'
def main():
    if (OUT/'complete.json').exists():raise RuntimeError('Completed execution exists; preserve version')
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    protected={str(p):sha(p) for p in [ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv']}
    dump(OUT/'task_contract.json',dict(time=now(),status='new documented run on previously studied data, not blind preregistration',tasks={'A':'per-window SL areas at both epochs, expansion,contraction,net; preserve all valid area mass','B':'native-grid SL expansion/contraction positions'},data='Han2010/2020, same24 windows and five-input common valid mask',semantics='SL=21..24; SD1; Others3',support=[3,10,30],area_decision='single-date fractions plus paired-transition fractions; use30 for displayed storage representation',location_decision='native mapped pairs; coarsened labels are scale diagnostics, not replacement output',QC={'grid_tolerance_pixels':1e-6,'mass_rtol':1e-12,'mass_atol_m2':1e-6,'output_roundtrip':'exact','change_exclusivity':'expansion/contraction disjoint'},acceptance='task-defined information retention; no fitted F1 or p threshold',feedback='numeric or grid QC failure stops implicated step; no claim of actual iterative tuning',protected=protected))
    sel=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv');ds=open_inputs();off=offsets(ds)
    areas=[];metrics=[];traces=[];checks=[];examples={}
    for s in sel.to_dict('records'):
        label=s['display_id'];sid=s['id'];n=1200;raw,v=read_window(ds,off,int(s['row']),int(s['col']),n);tr=ds['H2020'].window_transform(Window(s['col'],s['row'],n,n));w=weights(tr,n);domain=area(v,w)
        a=LUT[raw['H2010']].copy();b=LUT[raw['H2020']].copy();a[~v]=255;b[~v]=255
        ex=v&(a!=2)&(b==2);co=v&(a==2)&(b!=2);changed=ex|co
        native=np.full(v.shape,255,np.uint8);native[v]=0;native[ex]=1;native[co]=2
        refs={'expansion':ex,'contraction':co,'change':changed}
        truth=dict(SL2010_km2=area(v&(a==2),w)/1e6,SL2020_km2=area(v&(b==2),w)/1e6,expansion_km2=area(ex,w)/1e6,contraction_km2=area(co,w)/1e6,change_union_km2=area(changed,w)/1e6)
        truth['net_change_km2']=truth['SL2020_km2']-truth['SL2010_km2']
        rowbase=dict(display_id=label,site=sid,group=s['group'],domain_km2=domain/1e6)
        areas.append(dict(**rowbase,representation='native paired pixels',scale=1,**truth,max_absolute_difference_m2=0))
        rdir=OUT/'rasters'/label;rdir.mkdir(parents=True,exist_ok=True);tif(rdir/'native_SL_change.tif',native,tr,255)
        # Independent set-membership subtraction uses original codes, not mapped labels.
        direct=np.isin(raw['H2020'],[21,22,23,24]).astype(np.int16)-np.isin(raw['H2010'],[21,22,23,24]).astype(np.int16)
        assert np.array_equal(v&(direct==1),ex) and np.array_equal(v&(direct==-1),co)
        assert not (ex&co).any()
        results={};maxerr=0.
        for f in [3,10,30]:
            ga=aggregate(raw['H2010'],v,w,f);gb=aggregate(raw['H2020'],v,w,f);total=ga['total']
            eventmass=np.stack([blocks(w*(v&~changed),f),blocks(w*ex,f),blocks(w*co,f)])
            ep=np.divide(eventmass,total[None],out=np.zeros_like(eventmass),where=total[None]>0)
            mass0=float((ga['p'][1]*total).sum());mass1=float((gb['p'][1]*total).sum());e=float((ep[1]*total).sum());c=float((ep[2]*total).sum())
            stats=dict(SL2010_km2=mass0/1e6,SL2020_km2=mass1/1e6,expansion_km2=e/1e6,contraction_km2=c/1e6,change_union_km2=(e+c)/1e6,net_change_km2=(mass1-mass0)/1e6)
            error=max(abs(stats[k]-truth[k])*1e6 for k in truth);assert error<1e-6;maxerr=max(maxerr,error)
            assert np.isclose(e-c,mass1-mass0,rtol=1e-12,atol=1e-6)
            areas.append(dict(**rowbase,representation='composition + transition fractions',scale=f,**stats,max_absolute_difference_m2=error))
            combined=np.stack([ga['p'][1],gb['p'][1],ep[0],ep[1],ep[2]]);combined[:,total<=0]=-9999
            path=rdir/f'task_fractions_f{f}.tif';tif(path,combined,tr*rasterio.Affine.scale(f,f),-9999)
            with rasterio.open(path,'r+') as d:
                for i,name in enumerate(['SL2010_fraction','SL2020_fraction','SL_unchanged_fraction','SL_expansion_fraction','SL_contraction_fraction'],1):d.set_band_description(i,name)
            x=expand(ga['coarse'],f);y=expand(gb['coarse'],f);known=(x!=255)&(y!=255)
            pred={'expansion':(x!=2)&(y==2),'contraction':(x==2)&(y!=2),'change':(x==2)!=(y==2)}
            image=np.full(v.shape,255,np.uint8);image[v&known]=0;image[v&known&pred['expansion']]=1;image[v&known&pred['contraction']]=2
            for event in refs:
                m=change_metrics(pred[event],refs[event],known,v,w);metrics.append(dict(**rowbase,scale=f,event=event,**m))
            lower0=float(total[ga['coarse']==2].sum());lower1=float(total[gb['coarse']==2].sum());unknown0=float(total[ga['coarse']==255].sum());unknown1=float(total[gb['coarse']==255].sum())
            areas.append(dict(**rowbase,representation='dominant-label diagnostic (confirmed lower areas)',scale=f,SL2010_km2=lower0/1e6,SL2020_km2=lower1/1e6,expansion_km2=area(v&known&pred['expansion'],w)/1e6,contraction_km2=area(v&known&pred['contraction'],w)/1e6,change_union_km2=area(v&known&pred['change'],w)/1e6,net_change_km2=(lower1-lower0)/1e6,unknown2010_km2=unknown0/1e6,unknown2020_km2=unknown1/1e6,max_absolute_difference_m2=np.nan))
            results[f]=image
        trace=[('1 Define task','SL area/gross turnover and native locations','Area mass and paired-location contracts differ','Two task branches specified','task_contract.json'),('2 Diagnose','CRS, transform, legal codes, shared mask','Han2010 row offset119 from Han2020; same centers after indexing','Use coordinate-derived windows; map21..24 toSL','grid offsets and input hashes'),('3 Analyze constraints','single-date composition versus paired transitions','Single-date fractions yield net area but not gross turnover or locations','Retain paired event fractions for expansion/contraction totals; native pairs for locations','representation rules'),('4 Organize','common indexed semantic labels','Area aggregation follows native correspondence; locations remain native','Sequential shared preparation + hierarchy-aware branches','native change and five-band fractions'),('5 Validate','mass, paired events, output files, diagnostic coarse maps','Conservation passed; coarse diagnostics quantify spatial losses','Keep fraction area output and native-location output; no numeric repair triggered','area_results.csv and location_diagnostics.csv')]
        for step,inp,evidence,decision,output in trace:traces.append(dict(display_id=label,step=step,input=inp,evidence=evidence,decision=decision,output=output))
        checks.append(dict(display_id=label,passed=True,coverage=float(v.mean()),max_area_difference_m2=maxerr,direct_SL_disagreement_pixels=0,source_window_hashes={k:hashlib.sha256(z.tobytes()).hexdigest() for k,z in raw.items()},repair_triggered=False))
        if label in ['H01','L01']:examples[label]=dict(native=native,scales=results,valid=v)
        print('Decision walkthrough: '+label,flush=True)
    write_csv(OUT/'area_results.csv',areas);write_csv(OUT/'location_diagnostics.csv',metrics);write_csv(OUT/'five_step_decision_log.csv',traces);dump(OUT/'validation.json',checks)
    a=pd.DataFrame(areas);m=pd.DataFrame(metrics)
    write_csv(OUT/'Table_4_5_Area_H01_L01.csv',a[(a.display_id.isin(['H01','L01']))&(a.representation!='dominant-label diagnostic (confirmed lower areas)')].to_dict('records'))
    write_csv(OUT/'Table_S_location_all_scales.csv',m[m.event=='change'].to_dict('records'))
    fig,axes=plt.subplots(2,4,figsize=(15,8),constrained_layout=True)
    for i,label in enumerate(['H01','L01']):
        for j,f in enumerate([1,3,10,30]):
            z=examples[label]['native'] if f==1 else examples[label]['scales'][f];z=np.where(z==255,3,z)
            axes[i,j].imshow(z,cmap=ListedColormap(['#efefea','#2084a0','#bd4d59','#555555']),vmin=-.5,vmax=3.5,extent=[0,1200,1200,0],interpolation='nearest')
            title=f'{label} | native task output' if f==1 else f'{label} | {f}x{f} diagnostic'
            if f!=1:
                row=m[(m.display_id==label)&(m.scale==f)&(m.event=='change')].iloc[0];title+=f'\nF1={row.F1:.3f}, coverage={row.coverage:.3f}'
            axes[i,j].set(title=title,xlabel='Native column',ylabel='Native row')
    fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#efefea','No SL membership change'),('#2084a0','Expansion'),('#bd4d59','Contraction'),('#555555','Unresolved')]],loc='outside lower center',ncol=4)
    for ext in ['png','pdf']:fig.savefig(FIG/f'Figure_4_6_Task_change_and_supports.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    for d in ds.values():d.close()
    assert all(sha(p)==h for p,h in protected.items())
    dump(OUT/'complete.json',dict(time=now(),regions=24,decision_rows=120,area_rows=len(areas),location_rows=len(metrics),validated=True,max_area_error_m2=max(c['max_area_difference_m2'] for c in checks),no_iterative_repair_executed=True,older_results_unchanged=True))
if __name__=='__main__':main()
