from core import *
import pandas as pd

def main():
    p=cfg();freeze=load(ROOT/'selection/selection_frozen.json')
    assert sha(ROOT/'parameters/frozen_parameters.json')==freeze['parameters_sha256']
    assert sha(ROOT/'selection/selected_regions.csv')==freeze['selected_sha256']
    for item in p['input_files'].values():
        st=Path(item['path']).stat();assert st.st_size==item['bytes'] and st.st_mtime_ns==item['mtime_ns']
    change=pd.read_csv(ROOT/'results/experiment_3/change.csv');order=pd.read_csv(ROOT/'results/experiment_2/order.csv')
    assert len(change)==1350 and len(order)==75
    assert not change.duplicated(['site','start_year','scale','strategy','event']).any()
    assert not order.duplicated(['site','year','scale']).any()
    for metric in ['F1','IoU','coverage','precision','recall']:
        vals=change[metric].dropna();assert vals.between(-1e-12,1+1e-12).all()
    assert (order.n_disagree<=order.n_joint).all()
    for m in ['R_NC_count','R_NC_area']:assert order[m].between(0,1).all()
    independent_f1=2*change.tp_km2/(2*change.tp_km2+change.fp_km2+change.fn_km2)
    assert np.allclose(change.F1,independent_f1,equal_nan=True)
    # Verify all actual files and serialized payload costs against reported values.
    checked=0
    for table,task in [('cost','change'),('area','area')]:
        df=pd.read_csv(ROOT/f'results/experiment_3/{table}.csv')
        for row in df.itertuples():
            name=f'change_{row.start_year}_2020_{row.strategy}_f{row.scale}' if task=='change' else f'area_{row.strategy}_f{row.scale}'
            path=ROOT/'results/experiment_3/artifacts'/row.site/(name+'.npz');mp=path.with_suffix('.json')
            with np.load(path) as z:raw=sum(z[k].nbytes for k in z.files)+mp.stat().st_size
            assert raw==row.raw_bytes and path.stat().st_size+mp.stat().st_size==row.file_bytes
            checked+=1
    for i in [1,2,3]:
        assert list((ROOT/'figures').glob(f'Figure_{i}_*.png'))
        assert list((ROOT/'tables').glob(f'Table_{i}_*.csv'))
    assert '主要集中于High' in (ROOT/'reports/FINAL_RESULTS.md').read_text(encoding='utf8')
    dump(ROOT/'qc/final_acceptance.json',dict(time=now(),passed=True,unchanged_input_size_mtime=True,unchanged_frozen_parameters_and_selection=True,independent_F1_check=True,artifact_costs_verified=checked,formal_cases=25,primary_inference_windows=24))
    files=[]
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name!='delivery_manifest.json':
            files.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=sha(path)))
    dump(ROOT/'reports/delivery_manifest.json',dict(created_at=now(),files=files))
    print(f'Delivery passed: {checked} artifact costs independently verified; {len(files)} files hashed.')
if __name__=='__main__':main()
