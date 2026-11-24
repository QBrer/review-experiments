"""History-only stage: opens Han2000/Han2010, never opens test rasters."""
from core import *
import pandas as pd
from scipy.stats import spearmanr
from budget_experiment3 import entropy,rank_indices

OUT=ROOT/'results/experiment_3_history_v12'
def freeze():
    if (OUT/'parameters.json').exists():raise RuntimeError('Existing frozen v1.2; refuse overwrite')
    p=load(ROOT/'parameters/experiment3_history_v12_draft.json')
    p.update(version='history-E3-v1.2',status='FROZEN',execution_allowed=True,frozen_at=now(),authorization='User requested execution of v1.2 draft including proposed QC gates',remaining_decisions=[])
    p['QC']['status']='FROZEN';p['statistics']['seed']=p['statistics'].pop('proposed_seed')
    p['protected_sha256']={str(q):sha(q) for q in [ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/experiment_3/change.csv',ROOT/'results/experiment_3_budget/all_results.csv']}
    p['history_code_sha256']=sha(__file__)
    p['historical_inputs']={str(y):str(next(BASE.glob('A multi*/MPSDSL'))/f'{y}.tif') for y in [2000,2010]}
    p['additional_implementation']={'all_history_validity_checks':'positive domain and exact registered grids; report coverage, do not add new exclusion threshold','test_aggregation':'use fixed V_test for both strategies; no reranking or K adjustment','same_K_representation':'retain selected full block payload even if test valid area is zero','fixed_budget_degenerate':'report reference only, no contrast when K is0 orN','precision':'float64 scoring, uint8 labels, uint32 indices','metadata':'same bytes for paired strategy payload; separate strategy provenance','result_directory':str(OUT)}
    dump(OUT/'parameters.json',p)
    dump(OUT/'input_access.json',dict(phase='history',opened_inputs=[],test_opened=False))
    return p
def read_history(ds,site):
    n=int(site.get('size',1200));r=int(site['row']);c=int(site['col']);ref=ds[2000]
    tr=ref.window_transform(Window(c,r,n,n));arrays={};origins={}
    for year,s in ds.items():
        assert s.crs==ref.crs and np.allclose(s.res,ref.res,rtol=1e-12,atol=0)
        col,row=(~s.transform)*(tr.c,tr.f);assert max(abs(col-round(col)),abs(row-round(row)))<1e-6
        sr,sc=int(round(row)),int(round(col));a=s.read(1,window=Window(sc,sr,n,n));assert a.shape==(n,n)
        assert set(np.unique(a)).issubset(set(FINE)|{0})
        arrays[year]=a;origins[year]=[sr,sc]
    v=np.isin(arrays[2000],FINE)&np.isin(arrays[2010],FINE)
    assert v.any();return arrays,v,tr,origins
def score(raw,v,w,f):
    g0=aggregate(raw[2000],v,w,f);g1=aggregate(raw[2010],v,w,f)
    a=LUT[raw[2000]];b=LUT[raw[2010]];fine=(a==2)!=(b==2)
    known=(g0['coarse']!=255)&(g1['coarse']!=255)
    coarse=(g0['coarse']==2)!=(g1['coarse']==2)
    # For abstention, only historical reference-positive positions count as missed.
    loss=np.where(expand(known,f),fine!=expand(coarse,f),fine)&v
    amount=blocks(w*loss,f);total=g0['total']
    R=np.divide(amount,total,out=np.zeros_like(total),where=total>0)
    H=np.maximum(entropy(g0['p']),entropy(g1['p']))
    nat=(total>0)&((g0['p'].max(0)<.90)|(g1['p'].max(0)<.90))
    return H,R,total,nat,known
def tests():
    # Equal historical marginals, distinct positional turnover: entropy cannot distinguish.
    a=np.array([[21,3],[21,3]],np.uint8);v=np.ones((2,2),bool);w=np.ones((2,2))
    H,R,_,_,known=score({2000:a,2010:a},v,w,2)
    H2,R2,_,_,_=score({2000:a,2010:np.fliplr(a)},v,w,2)
    assert np.array_equal(H,H2) and R[0,0]==0 and R2[0,0]==1 and not known.any()
    assert rank_indices(np.array([[0.,0.],[1.,0.]]),v).tolist()==[2,0,1,3]
    dump(OUT/'unit_checks.json',dict(passed=True,time=now(),checks=['equal entropy distinct history task loss','tie is abstention not nonSL','deterministic tied ranking']))
def process_site(ds,s,rows,manifest):
    sid=s['id'];raw,v,tr,origins=read_history(ds,s);n=v.shape[0];w=weights(tr,n)
    sitepath=OUT/'history'/sid;sitepath.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(sitepath/'historical_domain.npz',valid=v,row_area=w[:,0],transform=np.array(tr))
    dump(sitepath/'input_provenance.json',dict(site=sid,origins=origins,coverage=float(v.mean()),array_sha256={str(y):hashlib.sha256(a.tobytes()).hexdigest() for y,a in raw.items()},domain_sha256=hashlib.sha256(v.tobytes()).hexdigest()))
    for f in [30,3,10]:
        H,R,total,nat,known=score(raw,v,w,f);valid=total>0;N=int(valid.sum());K0=int(nat.sum())
        ranks={'Baseline':rank_indices(H,valid),'Proposed':rank_indices(R,valid)}
        rho=float(spearmanr(H[valid],R[valid]).statistic) if np.unique(H[valid]).size>1 and np.unique(R[valid]).size>1 else np.nan
        counts=np.unique(R[valid],return_counts=True)[1]
        z={'H':H,'R':R,'total':total,'natural':nat,'historical_known':known,'ranking_Baseline':ranks['Baseline'].astype(np.uint32),'ranking_Proposed':ranks['Proposed'].astype(np.uint32)}
        for budget,K in [('natural90',K0)]+[(f'B{int(B*100)}',int(np.floor(B*N))) for B in [.1,.25,.5,.75]]:
            a=np.sort(ranks['Baseline'][:K]).astype(np.uint32);b=np.sort(ranks['Proposed'][:K]).astype(np.uint32)
            z[budget+'_Baseline']=a;z[budget+'_Proposed']=b
            inter=len(np.intersect1d(a,b));union=2*K-inter
            cut=R.ravel()[ranks['Proposed'][K-1]] if K else np.nan
            rows.append(dict(site=sid,group=s['group'],scale=f,budget=budget,N=N,K=K,fraction=K/N,J=ratio(inter,union),D=ratio(2*(K-inter),union),D_norm=ratio(K-inter,min(K,N-K)),spearman=rho,intersection=inter,domain_coverage=float(v.mean()),R_zero_fraction=float((R[valid]==0).mean()),fine_R_zero=int((R.ravel()[b]==0).sum()),max_R_tie_fraction=float(counts.max()/N),cutoff_R=cut,cutoff_tie_count=int((R[valid]==cut).sum()) if K else 0,history_unresolved_fraction=ratio(total[~known].sum(),total.sum())))
        path=sitepath/f'decisions_f{f}.npz';np.savez_compressed(path,**z);manifest[str(path.relative_to(OUT))]=sha(path)
    print(f'History-only decisions complete: {sid}',flush=True)
def main():
    p=freeze();tests();ds={y:rasterio.open(path) for y,path in [(int(k),v) for k,v in p['historical_inputs'].items()]}
    dump(OUT/'input_access.json',dict(phase='history',opened_inputs=p['historical_inputs'],test_opened=False,time=now()))
    sites=pd.read_csv(ROOT/'selection/selected_regions.csv')[['id','group','row','col']].to_dict('records');rows=[];manifest={}
    for s in sites:
        process_site(ds,s,rows,manifest);write_csv(OUT/'history_qc.csv',rows)
    q=pd.DataFrame(rows);gates=[]
    for f in [30,3,10]:
        for group in ['High','Low']:
            a=q[(q.scale==f)&(q.group==group)&(q.budget=='natural90')]
            space=bool(a.fraction.between(.05,.95).all());distinct=int((a.D_norm>=.10).sum());median=float(a.D_norm.median());passed=space and distinct>=8 and median>=.10
            gates.append(dict(scale=f,group=group,n=len(a),all_budgets_5_to_95=space,min_fraction=float(a.fraction.min()),max_fraction=float(a.fraction.max()),n_Dnorm_ge_010=distinct,median_Dnorm=median,passed=passed))
    write_csv(OUT/'qc_gate_results.csv',gates)
    passed=[f for f in [30,3,10] if all(g['passed'] for g in gates if g['scale']==f)]
    primary_pass=30 in passed
    if primary_pass:
        bp=cfg()['B2'];process_site(ds,dict(id='B2',group='B2',row=bp['row'],col=bp['col'],size=1020),rows,manifest);write_csv(OUT/'history_qc.csv',rows)
    for d in ds.values():d.close()
    dump(OUT/'decisions_frozen.json',dict(time=now(),parameters_sha256=sha(OUT/'parameters.json'),decisions_sha256=manifest,primary_QC_passed=primary_pass,allowed_test_scales=passed if primary_pass else [],test_data_opened=False))
    status='READY_FOR_TEST' if primary_pass else 'STOPPED_PRIMARY_QC_FAILED'
    dump(OUT/'status.json',dict(time=now(),status=status,test_executed=False))
    from report_results import texttable
    msg=f'''# v1.2历史决策与区分度QC

状态：**{status}**。历史阶段仅打开Han2000和Han2010，没有读取2020或旧五输入mask；新评分没有访问旧F1。样区本身仍是既有、已查看的窗口，不作独立盲测宣称。

规则在评分前冻结：自然K/N须每窗位于[0.05,0.95]；每组至少8/12窗D_norm≥0.10且中位数≥0.10。30×30失败则整体停止测试，不以次要尺度替换。

{texttable(pd.DataFrame(gates),list(gates[0]))}

通过尺度：{passed}。实际允许测试尺度：{passed if primary_pass else []}。

J、D_norm、秩相关、评分并列、零损失选格及历史未知覆盖保存在history_qc.csv。全部历史分数、排名和预算索引保存在history/，哈希与冻结时间见decisions_frozen.json。

本阶段没有计算任何本版2010→2020 F1。若主门槛失败，失败本身是本版设计的结果，不调整阈值或删窗重试。
'''
    (OUT/'HISTORY_QC_REPORT.md').write_text(msg,encoding='utf8')
    print(json.dumps(clean(dict(status=status,gates=gates)),ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        dump(OUT/'history_error.json',dict(time=now(),error=repr(e),test_executed=False));raise
