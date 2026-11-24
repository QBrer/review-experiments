"""Prospectively frozen same-payload-budget revision of experiment 3."""
from core import *
from report_results import paired, describe, texttable
import pandas as pd
import matplotlib.pyplot as plt

OUT=ROOT/'results/experiment_3_budget'
def rank_indices(score,valid):
    idx=np.flatnonzero(valid)
    return idx[np.lexsort((idx,-score.ravel()[idx]))]
def entropy(p):
    z=np.zeros_like(p);np.log2(p,out=z,where=p>0)
    return -(p*z).sum(0)
def pack(start,end,g0,g1,indices,v,w):
    n=v.shape[0];f=30;idx=np.sort(indices).astype(np.uint32)
    def patches(a):return a.reshape(n//f,f,n//f,f).transpose(0,2,1,3).reshape(-1,f,f)[idx]
    return dict(start=g0['coarse'],end=g1['coarse'],fine_indices=idx,fine_start=patches(start),fine_end=patches(end),valid_mask=v.astype(np.uint8),row_area_m2=w[:,0].copy())
def decode(z):
    x=expand(z['start'],30);y=expand(z['end'],30);width=x.shape[1]//30
    for i,k in enumerate(z['fine_indices']):
        r,c=divmod(int(k),width);sl=np.s_[r*30:(r+1)*30,c*30:(c+1)*30]
        x[sl]=z['fine_start'][i];y[sl]=z['fine_end'][i]
    return x,y
def freeze():
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/'frozen_budget_design.json'
    if p.exists():raise RuntimeError('Existing budget run: do not overwrite or retune')
    original=cfg();selection=load(ROOT/'selection/selection_frozen.json')
    assert sha(ROOT/'selection/selected_regions.csv')==selection['selected_sha256']
    protected=[ROOT/'parameters/frozen_parameters.json',ROOT/'selection/selected_regions.csv',ROOT/'results/experiment_1/coupling.csv',ROOT/'results/experiment_2/order.csv',ROOT/'results/experiment_3/change.csv']
    spec=dict(version='budget-E3-v1',frozen_at=now(),code_sha256=sha(__file__),protected_files={str(p):sha(p) for p in protected},
      conditions=dict(years=[2010,2020],scale=30,semantics='coarse3',windows='same frozen 12High+12Low; B2 descriptive only',mask=original['common_mask']),
      baseline='max over the two epochs of three-class area entropy; descending',proposed='1-min over the two epochs of maximum three-class area proportion; descending',
      primary_budget='K=count(valid blocks AND (P2010<0.90 OR P2020<0.90)); both methods select exactly K',
      secondary_budgets=[.1,.25,.5,.75],rounding='floor(B * number_of_positive_valid_area_blocks)',eligibility='positive valid-area blocks',ties='exact score ties: row-major block index ascending; no score tolerance',
      proposed_fixed_budgets='rank all valid cells, including purity>=0.90 when needed to fill budget',
      representation='identical two-epoch coarse uint8 labels + K uint32 row-major indices + two Kx30x30 uint8 native coarse3 payloads; invalid native positions=255',
      metadata='byte-identical JSON for paired outputs; strategy and scores recorded separately in audit tables, not inference payload',
      common_cost='full uint8 valid mask + float64 row area + common JSON charged to each method',
      logical_cost='sum array nbytes + metadata UTF8 bytes; exact equality asserted per pair; actual compressed bytes reported separately',
      reference='native binary SL change; internal, not independent ground truth',
      endpoints=['F1 primary binary change','IoU','omission=FN/reference-positive area','commission=FP/predicted-positive area','FP and FN area','coverage','fine cell fraction','fine valid area fraction','logical bytes','compressed bytes','index bytes','metadata bytes'],
      statistics=original['statistics'],primary_family='High and Low natural-budget paired F1 differences, two-sided exact sign-flip; Holm2; B2 excluded',
      background='Coarse-only and Full raw noncompeting; neither contributes primary tests',
      interpretation='post-original-study design revision; existing windows previously observed; no claim of fresh blind external validation')
    dump(p,spec)
    # Tests before any revised outcome evaluation.
    score=np.array([[.4,.4],[.9,.1]]);assert rank_indices(score,np.ones((2,2),bool)).tolist()==[2,0,1,3]
    assert np.isclose(entropy(np.array([[[.5]],[[.5]],[[0.]]]))[0,0],1)
    dump(OUT/'preflight.json',dict(time=now(),passed=True,checks=['stable row-major tie rule','entropy zero terms','positive-valid-cell eligibility specified']))

def run():
    freeze();ds=open_inputs();off=offsets(ds);p=cfg();rows=[];audits=[];checks=[]
    sites=pd.read_csv(ROOT/'selection/selected_regions.csv').to_dict('records')
    sites.append(dict(id='B2',group='B2',row=p['B2']['row'],col=p['B2']['col']))
    previous=pd.read_csv(ROOT/'results/experiment_3/change.csv')
    for site in sites:
        sid=site['id'];n=1020 if sid=='B2' else 1200;r=int(site['row']);c=int(site['col'])
        raw,v=read_window(ds,off,r,c,n);tr=ds['H2020'].window_transform(Window(c,r,n,n));w=weights(tr,n)
        native=[LUT[raw[f'H{y}']].copy() for y in [2010,2020]]
        for a in native:a[~v]=255
        gg=[aggregate(raw[f'H{y}'],v,w,30) for y in [2010,2020]];valid=gg[0]['total']>0;total=gg[0]['total'];N=int(valid.sum())
        purity=[g['p'].max(0) for g in gg];S=1-np.minimum(*purity);H=np.maximum(*[entropy(g['p']) for g in gg])
        orders={'Baseline':rank_indices(H,valid),'Proposed':rank_indices(S,valid)}
        natural=valid&((purity[0]<.90)|(purity[1]<.90));K0=int(natural.sum())
        assert set(orders['Proposed'][:K0])==set(np.flatnonzero(natural))
        for idx in np.flatnonzero(valid):
            i,j=divmod(int(idx),n//30)
            audits.append(dict(site=sid,group=site['group'],block_row=i,block_col=j,H_max=H[i,j],S=S[i,j],P2010=purity[0][i,j],P2020=purity[1][i,j],valid_area_m2=total[i,j],natural_candidate=bool(natural[i,j])))
        tasks=[('natural90',None,K0),('B10',.10,int(np.floor(.10*N))),('B25',.25,int(np.floor(.25*N))),('B50',.50,int(np.floor(.50*N))),('B75',.75,int(np.floor(.75*N)))]
        ref=(native[0]==2)!=(native[1]==2)
        for budget,B,K in tasks+[('coarse_only',0.,0),('full_raw',1.,N)]:
            pair=[];sets={m:set(order[:K]) for m,order in orders.items()}
            overlap=len(sets['Baseline']&sets['Proposed'])
            for method in (['Baseline','Proposed'] if budget not in ['coarse_only','full_raw'] else ['Reference']):
                chosen=orders['Baseline' if method=='Reference' else method][:K]
                z=pack(*native,*gg,chosen,v,w);a,b=decode(z)
                meta=dict(site=sid,budget=budget,K=K,grid_shape=[n,n],factor=30,years=[2010,2020],CRS='EPSG:4326',transform=list(tr),native_codes=[1,2,3],nodata=255,encoding='coarse+full fine patches, two epochs',design_sha256=sha(OUT/'frozen_budget_design.json'))
                # Full raw background stores only native labels; not hierarchical duplicated coarse labels.
                if budget=='full_raw':
                    assert np.array_equal(a,native[0]) and np.array_equal(b,native[1])
                    z=dict(start=native[0],end=native[1],valid_mask=v.astype(np.uint8),row_area_m2=w[:,0].copy());meta['encoding']='native3 full raw'
                path=OUT/'artifacts'/sid/f'{budget}_{method}.npz';path.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(path,**z);mp=path.with_suffix('.json');dump(mp,meta)
                logical=sum(x.nbytes for x in z.values())+mp.stat().st_size;actual=path.stat().st_size+mp.stat().st_size
                known=(a!=255)&(b!=255);m=change_metrics((a==2)!=(b==2),ref,known,v,w)
                idx=np.asarray(chosen,int);fm=np.zeros(valid.shape,bool);fm.ravel()[idx]=True
                record=dict(site=sid,group=site['group'],budget=budget,B=B,strategy=method,K=K,N=N,fine_fraction=K/N,fine_area_fraction=ratio(total[fm].sum(),total.sum()),logical_bytes=logical,file_bytes=actual,index_bytes=0 if budget=='full_raw' else z['fine_indices'].nbytes,metadata_bytes=mp.stat().st_size,mask_bytes=v.size,overlap_K=overlap,shared_selected_fraction=ratio(overlap,K),**m)
                record['omission']=m['missed_change_rate'];record['commission']=ratio(m['fp_km2'],m['predicted_km2'])
                rows.append(record);pair.append((logical,mp.read_bytes()))
                with np.load(path) as saved:
                    if budget=='full_raw':xa,xb=saved['start'],saved['end']
                    else:xa,xb=decode(saved)
                    assert np.array_equal(xa,a) and np.array_equal(xb,b)
                if budget=='natural90' and method=='Proposed':
                    old=previous[(previous.site==sid)&(previous.start_year==2010)&(previous.scale==30)&(previous.strategy=='Proposed')&(previous.event=='change')].iloc[0]
                    assert np.isclose(m['F1'],old.F1,equal_nan=True,rtol=1e-12)
            if len(pair)==2:
                assert pair[0]==pair[1]
                checks.append(dict(site=sid,budget=budget,K=K,logical_bytes=pair[0][0],metadata_identical=True,selected_overlap=overlap,same_indices=sets['Baseline']==sets['Proposed']))
        write_csv(OUT/'all_results.csv',rows);write_csv(OUT/'block_scores.csv',audits);write_csv(OUT/'budget_checks.csv',checks)
        print(f'{sid}: matched budgets complete; natural K={K0}/{N}',flush=True)
    for s in ds.values():s.close()
    assert len(rows)==25*12 and len(checks)==25*5
    spec=load(OUT/'frozen_budget_design.json')
    assert all(sha(path)==value for path,value in spec['protected_files'].items())
    dump(OUT/'calculation_complete.json',dict(time=now(),rows=len(rows),matched_pairs=len(checks),passed=True,original_outputs_unchanged=True))

def report():
    d=pd.read_csv(OUT/'all_results.csv');rng=np.random.default_rng(20261016);stats=[]
    for (group,budget),g in d[(d.group!='B2')&(d.strategy!='Reference')].groupby(['group','budget']):
        pv=g.pivot(index='site',columns='strategy',values='F1');delta=pv.Proposed-pv.Baseline
        stats.append(dict(group=group,budget=budget,primary=budget=='natural90',positive=int((delta>1e-12).sum()),negative=int((delta< -1e-12).sum()),equal=int((abs(delta)<=1e-12).sum()),**paired(delta,rng,budget=='natural90')))
    primary=[r for r in stats if r['primary']];ps=[r['p_raw'] if np.isfinite(r['p_raw']) else 1 for r in primary];idx=np.argsort(ps);running=0
    for i,j in enumerate(idx):running=max(running,ps[j]*(2-i));primary[j]['p_Holm']=min(1,running)
    write_csv(OUT/'paired_statistics.csv',stats);write_csv(OUT/'primary_tests.csv',primary)
    summary=d.groupby(['group','budget','strategy'],dropna=False).agg(n=('site','size'),F1=('F1','mean'),IoU=('IoU','mean'),omission=('omission','mean'),commission=('commission','mean'),coverage=('coverage','mean'),fine_fraction=('fine_fraction','mean'),logical_bytes=('logical_bytes','mean'),file_bytes=('file_bytes','mean'),shared_selected_fraction=('shared_selected_fraction','mean')).reset_index();write_csv(OUT/'summary.csv',summary.to_dict('records'))
    out=ROOT/'figures/experiment_3_budget';out.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(14,4.4),constrained_layout=True)
    for ax,group in zip(axes[:2],['Low','High']):
        g=d[(d.group==group)&(d.budget=='natural90')];pv=g.pivot(index='site',columns='strategy',values='F1')
        for _,r in pv.iterrows():ax.plot([0,1],[r.Baseline,r.Proposed],'-o',alpha=.6)
        ax.set(xticks=[0,1],xticklabels=['Entropy baseline','Purity proposed'],ylabel='Area-weighted change F1',title=group+' | matched natural budget')
    for i,group in enumerate(['Low','High']):
        g=d[(d.group==group)&(d.budget=='natural90')];pv=g.pivot(index='site',columns='strategy',values='F1');delta=pv.Proposed-pv.Baseline
        axes[2].scatter(np.full(len(delta),i),delta,s=24,alpha=.7)
    axes[2].axhline(0,c='gray',lw=1);axes[2].set(xticks=[0,1],xticklabels=['Low','High'],ylabel='Paired F1 difference',title='Proposed minus Baseline')
    for ext in ['png','pdf']:fig.savefig(out/f'Figure_3_budget_primary.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for col,group in enumerate(['Low','High']):
        for method,color in [('Baseline','#377eb8'),('Proposed','#e66a3c')]:
            g=d[(d.group==group)&d.budget.isin(['B10','B25','B50','B75'])&(d.strategy==method)].groupby('B').F1.mean()
            axes[0,col].plot(g.index*100,g.values,'o-',label=method,color=color)
        for budget,label,style in [('coarse_only','Coarse-only',':'),('full_raw','Full raw','--')]:
            value=d[(d.group==group)&(d.budget==budget)].F1.mean();axes[0,col].axhline(value,c='gray',ls=style,label=label)
        axes[0,col].set(title=group,xlabel='Fine-cell budget (%)',ylabel='Mean change F1');axes[0,col].legend(fontsize=8)
        g=pd.DataFrame(stats);g=g[(g.group==group)&(~g.primary)].set_index('budget').loc[['B10','B25','B50','B75']]
        axes[1,col].plot([10,25,50,75],g['mean'],'o-',c='#53428b');axes[1,col].fill_between([10,25,50,75],g.ci_low.to_numpy(),g.ci_high.to_numpy(),alpha=.2,color='#53428b');axes[1,col].axhline(0,c='gray',lw=1);axes[1,col].set(xlabel='Fine-cell budget (%)',ylabel='Mean paired F1 difference',title='Descriptive window-bootstrap 95% CI')
    for ext in ['png','pdf']:fig.savefig(out/f'Figure_3_budget_curves.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    # Spatial allocation comparison uses first frozen High window, not best outcome.
    sid=pd.read_csv(ROOT/'selection/selected_regions.csv').query("group=='High'").sort_values('selection_order').iloc[0].id
    fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
    masks=[]
    for ax,method in zip(axes[:2],['Baseline','Proposed']):
        z=np.load(OUT/'artifacts'/sid/f'natural90_{method}.npz');mask=np.zeros(z['start'].shape,np.uint8);mask.ravel()[z['fine_indices']]=1;masks.append(mask)
        ax.imshow(mask,vmin=0,vmax=1,cmap='Greens',interpolation='nearest');ax.set(title=method,xlabel='Coarse column',ylabel='Coarse row')
    axes[2].imshow(masks[1].astype(int)-masks[0],cmap='coolwarm',vmin=-1,vmax=1,interpolation='nearest');axes[2].set(title='Allocation difference (red: Proposed only)',xlabel='Coarse column',ylabel='Coarse row');fig.suptitle('First-selected High window | same K | '+sid)
    for ext in ['png','pdf']:fig.savefig(out/f'Figure_3_budget_allocation.{ext}',dpi=240,bbox_inches='tight')
    plt.close(fig)
    conclusion=[]
    for r in primary:
        conclusion.append(f"- {r['group']}: 平均ΔF1={r['mean']:.8f}，95%CI [{r['ci_low']:.8f}, {r['ci_high']:.8f}]，Holm p={r['p_Holm']:.8f}；正/负/零差窗口={r['positive']}/{r['negative']}/{r['equal']}。")
    text=f'''# 实验3修订：固定信息预算下的变化位置保留

本轮按用户提出的同预算设计独立登记后执行。原始不等信息量比较及实验1/2全部保留；本轮不是未查看历史结果的新盲测，仍使用已冻结的24窗，B2只描述。

## 主设计与公平性

2010→2020，30×30，三上位类。自然主预算K由任一期最大类别纯度<90%的格数确定。Baseline按两期三类熵的最大值排序；Proposed按1−两期最小优势纯度排序。所有有效格可参与固定预算排序，精确同分按行列顺序。

已核验25窗×5预算的125对输出：Fine格数量、数组类型、原始两期30×30负载、mask、索引和JSON元数据完全匹配，逻辑bytes严格相等。实际压缩bytes可能因内容不同而不同，见summary.csv。策略身份及诊断分数作为审计记录另存，不掺入推理数据成本。自然预算Proposed与前一实验的Proposed预测指标一致。

## 主终点结果

{chr(10).join(conclusion)}

{texttable(pd.DataFrame(primary),['group','n','mean','median','ci_low','ci_high','rank_biserial','p_raw','p_Holm','positive','negative','equal'])}

## 预算稳健性

{texttable(pd.DataFrame(stats).query('primary == False'),['group','budget','mean','ci_low','ci_high','positive','negative','equal'])}

10%、25%、50%、75%为预设次要预算，不计算新的次要p值、不替换自然预算主终点。预算为正有效面积格的数量比例，K向下取整。两组均逐窗配对，不以格子为独立样本。

## 解释边界

现在比较的差异仅来自同样数量的Fine信息放在哪里，故原来“恢复native就自然提高”的优势对两个竞争策略对称。若ΔF1接近0或为负，应报告纯度规则没有明显优于熵规则，不能再以相对Coarse-only的改善证明其竞争优势。

熵与最大纯度都是组成混合指标；当有效类别实际只有SL和Others时，二元熵与1−最大纯度单调对应，两个排序可能非常接近，甚至一致。三类共存时排序才可能明显分离。该机制应结合block_scores.csv与同预算选中集合重叠解释，不能把纯度规则自动称作更强任务理解。

两策略都使用两期输入，不使用参考误差决定细化。Proposed没有直接识别SL转移方向，所以结论仅限这个具体任务相关代理指标的分配效果。内部reference不证明外部地表精度；规则是在原实验结果已知后提出，需如实交代研究过程。

原0.49→0.976降级为Coarse-only到任务细化表达的可行性对比。Full raw为原始信息背景，两者不是新增竞争策略；主要比较始终只有同预算Baseline和Proposed。

## 文件

- frozen_budget_design.json：结果计算前冻结的设计和旧文件哈希。
- all_results.csv：全部300条结果，含B2及两个非竞争参考。
- block_scores.csv：逐格原始诊断分数和自然预算候选。
- budget_checks.csv：125对等预算与集合重叠核验。
- primary_tests.csv / paired_statistics.csv / summary.csv：检验与全部汇总。
- figures/experiment_3_budget（位于新方案根目录）：主终点、预算曲线和空间分配图，PNG/PDF。
'''
    (OUT/'EXPERIMENT_3_BUDGET_REPORT.md').write_text(text,encoding='utf8')
    dump(OUT/'report_complete.json',dict(time=now(),primary=primary))
    print(json.dumps(clean(primary),indent=2),flush=True)

if __name__=='__main__':
    try:run();report()
    except Exception as e:
        dump(OUT/'error.json',dict(time=now(),error=repr(e)));raise
