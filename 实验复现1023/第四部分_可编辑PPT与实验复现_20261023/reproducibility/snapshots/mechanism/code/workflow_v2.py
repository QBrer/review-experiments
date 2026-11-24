"""Frozen comparison of marginal-state and joint-transition aggregation."""
from core import *
from report_results import paired,describe,texttable
import pandas as pd
import matplotlib.pyplot as plt

OUT=ROOT/'results/experiment_3_workflow_v2'
def predict(a,b,v,w,f):
    mass=np.stack([blocks(w*(v&(a==i)&(b==j)),f) for i in [1,2,3] for j in [1,2,3]])
    cube=mass.reshape(3,3,*mass.shape[1:]);left=cube.sum(1);right=cube.sum(0)
    # Check marginals against separate state accumulation, rather than trusting reshape order.
    for i in range(3):
        assert np.allclose(left[i],blocks(w*(v&(a==i+1)),f),rtol=1e-12,atol=1e-6)
        assert np.allclose(right[i],blocks(w*(v&(b==i+1)),f),rtol=1e-12,atol=1e-6)
    first=unique_mode(left,[1,2,3]);last=unique_mode(right,[1,2,3])
    base=(3*(first.astype(int)-1)+last.astype(int)-1).astype(np.uint8)
    base[(first==255)|(last==255)]=255
    prop=unique_mode(mass,np.arange(9,dtype=np.uint8))
    total=mass.sum(0);assert np.isclose(total.sum(),area(v,w),rtol=1e-12)
    # These are mathematical properties, not independent scientific evidence of task benefit.
    ok=(base!=255)&(prop!=255)&(total>0)
    if ok.any():
        z=mass.reshape(9,-1);idx=np.flatnonzero(ok)
        assert np.all(z[prop.ravel()[idx],idx]+1e-6>=z[base.ravel()[idx],idx])
    return base,prop,total,mass
def decode(code):
    known=code!=255;a=(code//3+1).astype(np.uint8);b=(code%3+1).astype(np.uint8)
    a[~known]=255;b[~known]=255;return a,b,known
def events(a,b):
    return {'change':(a==2)!=(b==2),'expansion':(a!=2)&(b==2),'contraction':(a==2)&(b!=2)}
def tests():
    results=[]
    for label,counts in [('A',[25,35,30,10]),('B',[40,20,5,35])]:
        a=[];b=[]
        for (i,j),count in zip([(2,2),(2,3),(3,2),(3,3)],counts):a.extend([i]*count);b.extend([j]*count)
        a=np.array(a,np.uint8).reshape(10,10);b=np.array(b,np.uint8).reshape(10,10);v=np.ones((10,10),bool);w=np.ones((10,10))
        bs,ps,_,_=predict(a,b,v,w,10);values=[]
        for c in [bs,ps]:
            x,y,known=decode(expand(c,10));m=change_metrics(events(x,y)['change'],events(a,b)['change'],known,v,w);values.append(m['F1'])
        assert (values[1]>values[0]) if label=='A' else (values[1]<values[0]);results.append(dict(case=label,Baseline=values[0],Proposed=values[1]))
    for i in [1,2,3]:
        for j in [1,2,3]:
            a=np.full((6,6),i,np.uint8);b=np.full_like(a,j);v=np.ones_like(a,bool);w=np.ones_like(a,float)
            bs,ps,_,_=predict(a,b,v,w,3);assert (bs==3*(i-1)+j-1).all() and np.array_equal(bs,ps)
    z=predict(a,b,np.zeros_like(v),w,3);assert (z[0]==255).all() and (z[1]==255).all()
    assert unique_mode(np.array([[[1.]],[[1.]]]),[0,1])[0,0]==255
    dump(OUT/'preflight.json',dict(time=now(),passed=True,cases=results,checks=['9 homogeneous transitions','zero valid area','ties','joint marginals','opposite directions of F1 response']))

def freeze():
    path=OUT/'parameters.json'
    if path.exists():raise RuntimeError('Existing v2 run; refuse overwrite')
    h=next(BASE.glob('A multi*/MPSDSL'));selected=ROOT/'selection/selected_regions.csv'
    protected=[selected,ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/experiment_3/change.csv',ROOT/'results/experiment_3_budget/all_results.csv',ROOT/'results/experiment_3_history_v12/history_qc.csv']
    dump(path,dict(version='workflow-v2',frozen_at=now(),plan_sha256=sha(ROOT/'实验3重设计_v2_跨期关系优先与状态优先.md'),code_sha256=sha(__file__),protected={str(p):sha(p) for p in protected},
      inputs={str(y):dict(path=str(h/f'{y}.tif'),bytes=(h/f'{y}.tif').stat().st_size,mtime_ns=(h/f'{y}.tif').stat().st_mtime_ns) for y in [2010,2020]},
      primary=dict(years=[2010,2020],scale=30,task='binary SL membership change area-F1',comparisons=['High','Low'],test='two-sided exact paired sign-flip of mean difference',Holm_family=2),secondary_scales=[3,10],
      mask='Han2010 legal codes intersect Han2020 legal codes only',labels=[1,2,3],input_legal=[1,3,21,22,23,24],mapping={1:1,21:2,22:2,23:2,24:2,3:3},
      baseline='independent area modes then encode pair',proposed='unique area mode of nine native transitions',output='uint8 code3*(start-1)+(end-1), codes0..8, unknown255',tie_relative=1e-10,
      costs='one coarse uint8 code array + shared uint8 native mask + float64 row areas + byte-identical JSON; compressed cost separate',
      statistics=dict(unit='window',B2='descriptive only',bootstrap_replicates=10000,seed=20261017,min_pairs=5,zeros='retain; p1 if all zero',missing='NA with counts; no replacing or deleting windows',secondary='descriptive CI, no secondary p',group_contrast='bootstrap difference of group meanDelta, not difference of significance'),
      agreement_diagnostics='whole valid domain; unknown treated incorrect; separate joint-decidable mode-optimality QC; not main superiority evidence',
      zero_denominator='NA, not perfect',unknown_prediction='abstention; reference-positive pixels FN, coverage separately',no_fine_payload=True,no_outcome_selection=True,peak_memory='not measured',runtime='prediction wall time combines both algorithms, not an optimized speed comparison'))

def run():
    freeze();tests();p=load(OUT/'parameters.json');ds={int(y):rasterio.open(z['path']) for y,z in p['inputs'].items()};ref=ds[2020]
    sites=pd.read_csv(ROOT/'selection/selected_regions.csv')[['id','group','row','col']].to_dict('records')
    sites.append(dict(id='B2',group='B2',row=52983,col=78382))
    rows=[];diagnostics=[];checks=[];provenance=[];independent=0;rng=np.random.default_rng(20261017)
    import time
    for s in sites:
        sid=s['id'];n=1020 if sid=='B2' else 1200;tr=ref.window_transform(Window(int(s['col']),int(s['row']),n,n));raw={};positions={}
        for year,src in ds.items():
            assert src.crs==ref.crs and np.allclose(src.res,ref.res,rtol=1e-12,atol=0)
            c,r=(~src.transform)*(tr.c,tr.f);assert max(abs(c-round(c)),abs(r-round(r)))<1e-6
            rr,cc=int(round(r)),int(round(c));a=src.read(1,window=Window(cc,rr,n,n));assert a.shape==(n,n)
            assert set(np.unique(a)).issubset(set(FINE)|{0});raw[year]=a;positions[year]=[rr,cc]
        v=np.isin(raw[2010],FINE)&np.isin(raw[2020],FINE);assert v.any();w=weights(tr,n);a=LUT[raw[2010]];b=LUT[raw[2020]];refs=events(a,b);domain=area(v,w)
        provenance.append(dict(site=sid,group=s['group'],valid_pixels=int(v.sum()),domain_km2=domain/1e6,positions=json.dumps(positions),input_hashes=json.dumps({y:hashlib.sha256(z.tobytes()).hexdigest() for y,z in raw.items()})))
        for f in [30,3,10]:
            start=time.perf_counter();bs,ps,total,mass=predict(a,b,v,w,f);elapsed=time.perf_counter()-start
            # Independent per-block direct summation and mode selection.
            for flat in rng.choice(total.size,min(24,total.size),replace=False):
                i,j=divmod(int(flat),total.shape[1]);sl=np.s_[i*f:(i+1)*f,j*f:(j+1)*f]
                direct=np.array([np.sum(w[sl][v[sl]&(a[sl]==x)&(b[sl]==y)]) for x in [1,2,3] for y in [1,2,3]])
                assert np.allclose(direct,mass[:,i,j],rtol=1e-12,atol=1e-6)
                def winner(x,labels):
                    return 255 if x.sum()==0 or (abs(x-x.max())<=1e-10*x.sum()).sum()>1 else labels[int(x.argmax())]
                q=direct.reshape(3,3);u=winner(q.sum(1),[1,2,3]);vv=winner(q.sum(0),[1,2,3]);expected=255 if 255 in [u,vv] else 3*(u-1)+vv-1
                assert expected==bs[i,j] and winner(direct,list(range(9)))==ps[i,j];independent+=1
            ok=(bs!=255)&(ps!=255)&(total>0);diff=ok&(bs!=ps)
            diagnostics.append(dict(site=sid,group=s['group'],scale=f,n_joint=int(ok.sum()),n_disagree=int(diff.sum()),disagreement_count=ratio(diff.sum(),ok.sum()),disagreement_area=ratio(total[diff].sum(),total[ok].sum()),joint_coverage=ratio(total[ok].sum(),domain),combined_predict_seconds=elapsed))
            meta=dict(site=sid,scale=f,years=[2010,2020],transform=list(tr),CRS=str(ref.crs),code='3*(start-1)+(end-1); start,end in1..3',unknown=255,parameters_sha256=sha(OUT/'parameters.json'))
            costs=[]
            # Save both predictions before constructing performance metrics.
            for method,code in [('Baseline',bs),('Proposed',ps)]:
                dest=OUT/'artifacts'/sid/f'f{f}_{method}.npz';dest.parent.mkdir(parents=True,exist_ok=True)
                z=dict(transition_code=code,valid_mask=v.astype(np.uint8),row_area_m2=w[:,0].copy())
                np.savez_compressed(dest,**z);mp=dest.with_suffix('.json');dump(mp,meta)
                costs.append((sum(z.nbytes for z in z.values())+mp.stat().st_size,dest.stat().st_size+mp.stat().st_size,mp.read_bytes()))
            assert costs[0][0]==costs[1][0] and costs[0][2]==costs[1][2]
            checks.append(dict(site=sid,scale=f,equal_logical_bytes=True,logical_bytes=costs[0][0],Baseline_file_bytes=costs[0][1],Proposed_file_bytes=costs[1][1],metadata_identical=True,no_fine_pixels=True))
            for num,(method,code) in enumerate([('Baseline',bs),('Proposed',ps)]):
                x,y,known=decode(expand(code,f));pred=events(x,y)
                agreement=dict(start_agreement=area(v&known&(x==a),w)/domain,end_agreement=area(v&known&(y==b),w)/domain,transition_agreement=area(v&known&(x==a)&(y==b),w)/domain)
                for event in ['change','expansion','contraction']:
                    m=change_metrics(pred[event],refs[event],known,v,w)
                    rows.append(dict(site=sid,group=s['group'],scale=f,strategy=method,event=event,logical_bytes=costs[num][0],file_bytes=costs[num][1],**m,**agreement,omission=m['missed_change_rate'],commission=ratio(m['fp_km2'],m['predicted_km2'])))
            # Reload and verify saved output cost and exact code arrays.
            for num,(method,code) in enumerate([('Baseline',bs),('Proposed',ps)]):
                dest=OUT/'artifacts'/sid/f'f{f}_{method}.npz'
                with np.load(dest) as z:
                    assert np.array_equal(z['transition_code'],code)
                    assert sum(z[k].nbytes for k in z.files)+dest.with_suffix('.json').stat().st_size==costs[num][0]
        write_csv(OUT/'all_results.csv',rows);write_csv(OUT/'path_differences.csv',diagnostics);write_csv(OUT/'cost_checks.csv',checks);write_csv(OUT/'input_provenance.csv',provenance)
        print(f'Workflow v2 completed: {sid}',flush=True)
    for s in ds.values():s.close()
    assert len(rows)==450 and len(checks)==75
    assert all(sha(path)==h for path,h in p['protected'].items())
    dump(OUT/'calculation_complete.json',dict(time=now(),passed=True,independent_blocks_verified=independent,cost_pairs_verified=75,rows=450,old_files_unchanged=True))

def report():
    d=pd.read_csv(OUT/'all_results.csv');rng=np.random.default_rng(20261017);stats=[]
    for (group,f,event),g in d[d.group!='B2'].groupby(['group','scale','event']):
        for metric in ['F1','IoU','omission','commission','area_error_km2','coverage']:
            pv=g.pivot(index='site',columns='strategy',values=metric);delta=pv.Proposed-pv.Baseline;primary=f==30 and event=='change' and metric=='F1'
            stats.append(dict(group=group,scale=f,event=event,metric=metric,primary=primary,positive=int((delta>1e-12).sum()),negative=int((delta< -1e-12).sum()),equal=int((abs(delta)<=1e-12).sum()),missing_pairs=int(delta.isna().sum()),**paired(delta,rng,primary)))
    pri=[s for s in stats if s['primary']];pvals=np.array([r['p_raw'] if np.isfinite(r['p_raw']) else 1 for r in pri]);rank=np.argsort(pvals);adjust=np.minimum(1,np.maximum.accumulate(pvals[rank]*[2,1]))
    for i,j in enumerate(rank):pri[j]['p_Holm']=float(adjust[i]) if np.isfinite(pri[j]['p_raw']) else np.nan
    write_csv(OUT/'primary_tests.csv',pri);write_csv(OUT/'paired_statistics.csv',stats)
    summary=d.groupby(['group','scale','event','strategy']).agg(n=('site','size'),F1=('F1','mean'),IoU=('IoU','mean'),omission=('omission','mean'),commission=('commission','mean'),coverage=('coverage','mean'),reference_km2=('reference_km2','mean'),predicted_km2=('predicted_km2','mean'),start_agreement=('start_agreement','mean'),end_agreement=('end_agreement','mean'),transition_agreement=('transition_agreement','mean'),logical_bytes=('logical_bytes','mean'),file_bytes=('file_bytes','mean')).reset_index()
    write_csv(OUT/'summary.csv',summary.to_dict('records'))
    deltas={}
    for group in ['High','Low']:
        g=d[(d.group==group)&(d.scale==30)&(d.event=='change')].pivot(index='site',columns='strategy',values='F1');deltas[group]=(g.Proposed-g.Baseline).dropna().to_numpy()
    hi,lo=deltas['High'],deltas['Low'];boot=hi[rng.integers(0,len(hi),(10000,len(hi)))].mean(1)-lo[rng.integers(0,len(lo),(10000,len(lo)))].mean(1)
    contrast=dict(mean_difference=float(hi.mean()-lo.mean()),ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),secondary_descriptive=True)
    dump(OUT/'group_contrast.json',contrast)
    figdir=ROOT/'figures/experiment_3_workflow_v2';figdir.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True)
    for ax,group in zip(axes[:2],['Low','High']):
        g=d[(d.group==group)&(d.scale==30)&(d.event=='change')].pivot(index='site',columns='strategy',values='F1')
        for _,row in g.iterrows():ax.plot([0,1],[row.Baseline,row.Proposed],'-o',alpha=.6)
        ax.set(xticks=[0,1],xticklabels=['State-first','Transition-first'],ylabel='Area-weighted SL-change F1',title=group+' | 2010-2020, 30x30',ylim=(0,1))
    for group,color in [('Low','#377eb8'),('High','#d66539')]:
        g=pd.DataFrame(stats);g=g[(g.group==group)&(g.event=='change')&(g.metric=='F1')].sort_values('scale')
        axes[2].errorbar(g.scale,g['mean'],yerr=[g['mean']-g.ci_low,g.ci_high-g['mean']],label=group,color=color,marker='o',capsize=4)
    axes[2].axhline(0,c='gray',lw=1);axes[2].set(xlabel='Aggregation factor',ylabel='Paired F1 gain (Proposed - Baseline)',title='Window-bootstrap 95% CI',xticks=[3,10,30]);axes[2].legend()
    for ext in ['png','pdf']:fig.savefig(figdir/f'Figure_workflow_primary.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.3),constrained_layout=True)
    for ax,group in zip(axes,['Low','High']):
        g=summary[(summary.group==group)&(summary.scale==30)&(summary.event=='change')].set_index('strategy')
        x=np.arange(4)
        for shift,method,color in [(-.18,'Baseline','#377eb8'),(.18,'Proposed','#d66539')]:
            ax.bar(x+shift,g.loc[method,['start_agreement','end_agreement','transition_agreement','F1']].to_numpy(dtype=float),width=.36,label=method,color=color)
        ax.set(xticks=x,xticklabels=['Start-state','End-state','Joint transition','SL-change F1'],ylim=(0,1),title=group);ax.tick_params(axis='x',labelrotation=15);ax.legend()
    fig.suptitle('Agreement diagnostics are mode properties; SL-change F1 is the task endpoint')
    for ext in ['png','pdf']:fig.savefig(figdir/f'Figure_workflow_tradeoffs.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    primary_summary=summary[(summary.group!='B2')&(summary.scale==30)&(summary.event=='change')]
    verdict='未形成两个组均有正向显著收益的证据。' if not all(r['mean']>0 and r['p_Holm']<.05 for r in pri) else '两个组的同成本主要比较均有正向差异。'
    text=f'''# 实验3 v2：状态优先与跨期关系优先

完成时间（UTC）：{now()}。24个新窗及B2、3个尺度、两流程、3种变化事件已全部完成。原实验文件和选区哈希未变。

## 设计与公平性

Baseline独立选择两期三类面积众数，再编码转移；Proposed选择像元级9种转移的联合面积众数。两者输出相同的0—8转移码，255未确定。不存Fine像元、比例或转移概率。每输出同shape、uint8、同mask、行面积及相同JSON，75对逻辑成本完全相等；压缩文件大小另报。

仅Han2010/2020合法码交集为任务域。格网按地理坐标恢复，2010存在整数行偏移，无重采样。主要终点固定2010→2020、30×30、SL二值变化F1。3×3和10×10为次要，不替换主结论。

## 主结果

{texttable(primary_summary,['group','strategy','n','F1','IoU','omission','commission','coverage','logical_bytes','file_bytes'])}

{texttable(pd.DataFrame(pri),['group','n','mean','median','ci_low','ci_high','p_raw','p_Holm','positive','negative','equal'])}

{verdict}主要判断需要同时考虑效应大小、区间及方向，不能只看p值。两项双侧精确符号置换的p值作Holm校正，B2不参与。CI为10000次整窗配对bootstrap点区间。

## 多尺度与组间差异

{texttable(pd.DataFrame(stats).query("event=='change' and metric=='F1'"),['group','scale','mean','ci_low','ci_high','positive','negative','equal'])}

High平均ΔF1减Low平均ΔF1={contrast['mean_difference']:.8f}，描述性95%CI=[{contrast['ci_low']:.8f},{contrast['ci_high']:.8f}]；没有额外组间p值。方向事件、面积、coverage完整见all_results.csv。

## 必须保留的解释边界

联合众数在共同可判定格上最大化完整转移码一致面积，这是构造性质，不是独立任务有效性证据。边际众数分别最大化单期类别一致面积，同样是性质。两者的主要任务比较是未被直接优化的SL变化F1，不能以其他一致率的必然改善替代。

若Proposed改善，说明这个具体组织方式在这些输入上的任务适用性；若持平或变差，说明联合优势转移未保留更多目标SL变化，不能改权重或按结果挑尺度。任何结果都不能代表全部五步框架的普适有效性。

参考来自同源native产品，评价处理保真度而非外部地表精度。样区与时段已在此前版本查看，本版是新的事后研究假设与执行前冻结规则，不是独立盲测。比较也不是未来预测：两策略公平使用相同两期分类输入。

完整输出成本核验、1800个随机历史/当前输入块的独立算子核验（实际数量见calculation_complete.json）、面积与转移边际检查均通过。预测先保存后评价，参数与选区不因结果修改。耗时为两流程合计实现时间，峰值内存未测，不作计算效率优越性比较。
'''
    (OUT/'EXPERIMENT_3_WORKFLOW_REPORT.md').write_text(text,encoding='utf8')
    dump(OUT/'report_complete.json',dict(time=now(),primary=pri,group_contrast=contrast))
    print(json.dumps(clean(pri),indent=2),flush=True)
if __name__=='__main__':
    try:run();report()
    except Exception as e:
        dump(OUT/'error.json',dict(time=now(),error=repr(e)));raise
