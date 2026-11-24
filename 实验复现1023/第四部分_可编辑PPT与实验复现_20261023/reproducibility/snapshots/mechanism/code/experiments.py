from core import *
import pandas as pd

def artifact(path,arrays,meta):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,**arrays);mp=path.with_suffix('.json');dump(mp,meta)
    return dict(raw_bytes=sum(a.nbytes for a in arrays.values())+mp.stat().st_size,file_bytes=path.stat().st_size+mp.stat().st_size)

def adaptive(g0,g1,a0,a1,f):
    refine=(g0['p'].max(0)<.90)|(g1['p'].max(0)<.90)
    refine &= g0['total']>0
    mask=expand(refine,f);x=expand(g0['coarse'],f);y=expand(g1['coarse'],f)
    x[mask]=a0[mask];y[mask]=a1[mask]
    return x,y,refine

def qc_tests():
    a=np.array([[21,21,22],[22,23,23],[3,3,3]],np.uint8);v=np.ones((3,3),bool);w=np.ones((3,3))
    g=aggregate(a,v,w,3)
    assert g['coarse'][0,0]==2 and g['spatial_then_semantic'][0,0]==3
    for c in FINE:
        z=aggregate(np.full((6,6),c,np.uint8),np.ones((6,6),bool),np.ones((6,6)),3)
        assert np.all(z['coarse']==LUT[c]) and np.array_equal(z['coarse'],z['spatial_then_semantic'])
    assert unique_mode(np.array([[[1.]],[[1.]],[[0.]]]),[1,2,3])[0,0]==255
    z=aggregate(a,np.zeros((3,3),bool),w,3);assert z['coarse'][0,0]==255
    vp=v.copy();vp[0,0]=False;z=aggregate(a,vp,w,3);assert z['total'].sum()==8 and z['mass'][1].sum()==1
    native=LUT[a];x,y,refine=adaptive(g,g,native,native,3);assert refine.all() and np.array_equal(x,native)
    fake={'coarse':np.array([[2]],np.uint8),'p':np.array([[[.1]],[[.9]],[[0.]]]),'total':np.array([[10.]])}
    _,_,r=adaptive(fake,fake,np.full((3,3),2,np.uint8),np.full((3,3),2,np.uint8),3);assert not r.any()
    m=change_metrics(np.zeros((3,3),bool),v,np.zeros_like(v),v,w);assert m['F1']==0 and m['fn_km2']==9/1e6 and m['coverage']==0
    assert np.isnan(change_metrics(np.zeros_like(v),np.zeros_like(v),v,v,w)['F1'])
    # Direct per-block independent weighted histograms verify vectorization and tie handling.
    rng=np.random.default_rng(87);a=rng.choice(FINE,(30,30));v=rng.random((30,30))>.1;w=np.broadcast_to(np.linspace(610,620,30)[:,None],v.shape)
    for f in [3,10,30]:
        g=aggregate(a,v,w,f)
        for i,j in np.ndindex(g['total'].shape):
            sl=np.s_[i*f:(i+1)*f,j*f:(j+1)*f]
            mass=np.bincount(a[sl].ravel(),weights=(w[sl]*v[sl]).ravel(),minlength=256)
            fine=mass[FINE];co=np.array([fine[0],fine[1:5].sum(),fine[5]])
            assert np.allclose(g['mass'][:,i,j],fine,rtol=1e-12)
            assert np.isclose(g['p'][1,i,j]*g['total'][i,j],co[1],rtol=1e-12)
    dump(ROOT/'qc/unit_checks.json',dict(time=now(),passed=True,tests=['noncommuting example','homogeneous classes','ties','empty cells','NoData exclusion','adaptive native reconstruction','90 percent boundary','abstention FN','empty-event NA','independent weighted histograms and conservation']))

def run():
    p=cfg();frozen=load(ROOT/'selection/selection_frozen.json')
    assert sha(ROOT/'parameters/frozen_parameters.json')==frozen['parameters_sha256']
    assert sha(ROOT/'selection/selected_regions.csv')==frozen['selected_sha256']
    qc_tests()
    dump(ROOT/'qc/experiment_start.json',dict(time=now(),parameters_sha256=frozen['parameters_sha256'],selection_sha256=sha(ROOT/'selection/selection_frozen.json'),code_sha256={n:sha(ROOT/'code'/n) for n in ['core.py','experiments.py']}))
    sites=pd.read_csv(ROOT/'selection/selected_regions.csv').to_dict('records')
    sites.append(dict(id='B2',row=p['B2']['row'],col=p['B2']['col'],group='B2',lon=p['B2']['lon'],lat=p['B2']['lat']))
    ds=open_inputs();off=offsets(ds);ref=ds['H2020']
    tables={k:[] for k in ['coupling','order','phase','area','change','cost','semantic_change','window_qc','transitions']}
    def save():
        locations={'coupling':'experiment_1','semantic_change':'experiment_1','order':'experiment_2','phase':'experiment_2','transitions':'experiment_2','area':'experiment_3','change':'experiment_3','cost':'experiment_3','window_qc':'qc'}
        for k,rows in tables.items():
            if rows:write_csv(ROOT/'results'/locations[k]/f'{k}.csv',rows)
    for site in sites:
        sid=site['id'];group=site['group'];n=1020 if sid=='B2' else 1200;r=int(site['row']);c=int(site['col'])
        raw,v=read_window(ds,off,r,c,n);tr=ref.window_transform(Window(c,r,n,n));w=weights(tr,n);domain=area(v,w)
        assert v.mean()>=.95
        native={y:LUT[raw[f'H{y}']].copy() for y in p['years']}
        for a in native.values():a[~v]=255
        base=dict(site=sid,group=group,window_pixels=n,valid_pixels=int(v.sum()),domain_km2=domain/1e6)
        hist={k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in raw.items()}
        tables['window_qc'].append(dict(**base,raw_window_sha256=json.dumps(hist),mask_sha256=hashlib.sha256(v.tobytes()).hexdigest(),lon=site['lon'],lat=site['lat']))
        common={'valid_mask':v.astype(np.uint8),'row_area_m2':w[:,0].copy()}
        metadata=dict(site=sid,transform=list(tr),CRS='EPSG:4326',parameter_sha256=frozen['parameters_sha256'],raw_sha256=hist)
        refSL=area(v&(native[2020]==2),w)
        wangmass={f'Wang{code}_fraction':area(v&(raw['W2020']==code),w)/domain for code in range(1,15)}
        tables['window_qc'][-1].update(wangmass)
        for year in [2015,2010,2000]:
            fine_ref=v&(raw[f'H{year}']!=raw['H2020']);coarse_ref=v&(native[year]!=native[2020])
            tables['semantic_change'].append(dict(**base,start_year=year,end_year=2020,fine_change_km2=area(fine_ref,w)/1e6,coarse_change_km2=area(coarse_ref,w)/1e6,legitimate_within_SL_change_removed_km2=area(fine_ref&~coarse_ref,w)/1e6))
        agg={f:{y:aggregate(raw[f'H{y}'],v,w,f) for y in p['years']} for f in p['scales']}
        native_costs={}
        for year in [2015,2010,2000]:
            native_costs[year]=artifact(ROOT/'results/experiment_3/artifacts'/sid/f'native_background_{year}_2020.npz',dict(**common,start=native[year],end=native[2020]),dict(**metadata,representation='native3 background, not a competing strategy',start_year=year,end_year=2020))
        for f in p['scales']:
            g20=agg[f][2020];total=g20['total'];co=g20['coarse'];sp=g20['spatial_then_semantic'];ok=(co!=255)&(sp!=255)&(total>0);diff=ok&(co!=sp)
            tables['order'].append(dict(**base,year=2020,scale=f,n_joint=int(ok.sum()),n_disagree=int(diff.sum()),R_NC_count=ratio(diff.sum(),ok.sum()),R_NC_area=ratio(total[diff].sum(),total[ok].sum()),affected_km2=total[diff].sum()/1e6,coverage=ratio(total[ok].sum(),domain),semantic_first_SL_lower_km2=total[co==2].sum()/1e6,spatial_first_SL_lower_km2=total[sp==2].sum()/1e6,SL_signed_difference_lower_km2=(total[co==2].sum()-total[sp==2].sum())/1e6,semantic_first_unknown_km2=total[co==255].sum()/1e6,spatial_first_unknown_km2=total[sp==255].sum()/1e6))
            for ca in [1,2,3]:
                for cb in [1,2,3]:
                    z=ok&(co==ca)&(sp==cb);tables['transitions'].append(dict(site=sid,group=group,scale=f,semantic_first=ca,spatial_first=cb,n=int(z.sum()),area_km2=total[z].sum()/1e6))
            for strategy in ['Baseline','Proposed']:
                if strategy=='Baseline':
                    low=float(total[co==2].sum());upper=low+float(total[co==255].sum());arr=dict(**common,labels=co)
                else:
                    low=float(np.sum(g20['p'][1]*total));upper=low;arr=dict(**common,SL_proportion=g20['p'][1].copy())
                e=max(abs(low-refSL),abs(upper-refSL));cost=artifact(ROOT/'results/experiment_3/artifacts'/sid/f'area_{strategy}_f{f}.npz',arr,dict(**metadata,task='SL_area',strategy=strategy,scale=f,year=2020))
                tables['area'].append(dict(**base,scale=f,strategy=strategy,year=2020,reference_km2=refSL/1e6,predicted_lower_km2=low/1e6,predicted_upper_km2=upper/1e6,absolute_error_km2=e/1e6,relative_error=ratio(e,refSL),bias_lower_km2=(low-refSL)/1e6,bias_upper_km2=(upper-refSL)/1e6,**cost))
                if strategy=='Proposed':assert np.isclose(low,refSL,rtol=1e-12,atol=1e-6)
            for year in [2015,2010,2000]:
                gs=agg[f][year]
                for level,key in [('fine6','fine'),('coarse3','coarse')]:
                    a=expand(gs[key],f);b=expand(g20[key],f);known=(a!=255)&(b!=255)
                    rr=(raw[f'H{year}']!=raw['H2020']) if level=='fine6' else native[year]!=native[2020]
                    tables['coupling'].append(dict(**base,start_year=year,end_year=2020,scale=f,semantic=level,**change_metrics(a!=b,rr,known,v,w)))
                for strategy in ['Baseline','Proposed']:
                    if strategy=='Baseline':
                        a=expand(gs['coarse'],f);b=expand(g20['coarse'],f);refine=np.zeros_like(co,bool)
                        arr=dict(**common,start=gs['coarse'],end=g20['coarse'])
                    else:
                        a,b,refine=adaptive(gs,g20,native[year],native[2020],f)
                        idx=np.flatnonzero(refine).astype(np.uint32)
                        def patches(x):return x.reshape(n//f,f,n//f,f).transpose(0,2,1,3).reshape(-1,f,f)[idx]
                        arr=dict(**common,start=gs['coarse'],end=g20['coarse'],refined_indices=idx,native_start=patches(native[year]),native_end=patches(native[2020]))
                        # Decode the serialized structure independently and check exact reconstruction.
                        for label,pred in [('start',a),('end',b)]:
                            decoded=expand(arr[label],f)
                            for k,index in enumerate(idx):
                                i,j=divmod(int(index),n//f);decoded[i*f:(i+1)*f,j*f:(j+1)*f]=arr['native_'+label][k]
                            assert np.array_equal(decoded,pred)
                    cost=artifact(ROOT/'results/experiment_3/artifacts'/sid/f'change_{year}_2020_{strategy}_f{f}.npz',arr,dict(**metadata,task='SL_change',strategy=strategy,scale=f,start_year=year,end_year=2020))
                    tables['cost'].append(dict(**base,start_year=year,scale=f,strategy=strategy,refined_area_fraction=ratio(total[refine].sum(),domain),refined_cell_fraction=float(refine.mean()),**cost,native_raw_bytes=native_costs[year]['raw_bytes'],native_file_bytes=native_costs[year]['file_bytes']))
                    known=(a!=255)&(b!=255)
                    for event in ['change','expansion','contraction']:
                        if event=='change':pr=(a==2)!=(b==2);rr=(native[year]==2)!=(native[2020]==2)
                        elif event=='expansion':pr=(a!=2)&(b==2);rr=(native[year]!=2)&(native[2020]==2)
                        else:pr=(a==2)&(b!=2);rr=(native[year]==2)&(native[2020]!=2)
                        tables['change'].append(dict(**base,start_year=year,end_year=2020,scale=f,strategy=strategy,event=event,**change_metrics(pr,rr,known,v,w)))
        # Phase evaluation: complete aggregation cells then a common interior clip.
        core=np.zeros_like(v);core[30:n-30,30:n-30]=True;core &= v
        for oy in [0,10,20]:
            for ox in [0,10,20]:
                h=(n-oy)//30*30;ww=(n-ox)//30*30;sl=np.s_[oy:oy+h,ox:ox+ww]
                g=aggregate(raw['H2020'][sl],v[sl],w[sl],30)
                overlap=blocks(w[sl]*core[sl],30);a=g['coarse'];b=g['spatial_then_semantic'];ok=(a!=255)&(b!=255)&(overlap>0);di=ok&(a!=b)
                assert np.isclose(overlap.sum(),area(core,w),rtol=1e-12)
                tables['phase'].append(dict(**base,scale=30,year=2020,offset_row=oy,offset_col=ox,core_start=30,core_end=n-30,n_joint=int(ok.sum()),n_disagree=int(di.sum()),R_NC_count=ratio(di.sum(),ok.sum()),R_NC_area=ratio(overlap[di].sum(),overlap[ok].sum()),coverage=ratio(overlap[ok].sum(),area(core,w))))
        save();print(f'Completed experiments and phases: {sid} ({group})',flush=True)
    for s in ds.values():s.close()
    assert len(tables['coupling'])==25*18 and len(tables['order'])==25*3 and len(tables['change'])==25*3*3*2*3
    dump(ROOT/'qc/experiments_complete.json',dict(time=now(),rows={k:len(v) for k,v in tables.items()},unit_checks_passed=True,selection_unchanged=sha(ROOT/'selection/selected_regions.csv')==frozen['selected_sha256']))

if __name__=='__main__':
    try:run()
    except Exception as e:
        dump(ROOT/'qc/experiment_error.json',dict(time=now(),error=repr(e)));raise
