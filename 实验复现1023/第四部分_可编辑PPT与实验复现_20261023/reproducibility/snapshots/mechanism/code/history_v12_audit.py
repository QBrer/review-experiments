"""Independent history-only loss verification and QC figures; no test data."""
from core import *
from history_v12_decision import OUT,read_history
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    frozen=load(OUT/'decisions_frozen.json');p=load(OUT/'parameters.json')
    assert not frozen['primary_QC_passed'] and not frozen['test_data_opened']
    assert all(sha(path)==h for path,h in p['protected_sha256'].items())
    assert all(sha(OUT/path)==h for path,h in frozen['decisions_sha256'].items())
    ds={int(y):rasterio.open(path) for y,path in p['historical_inputs'].items()}
    sites=pd.read_csv(ROOT/'selection/selected_regions.csv')[['id','group','row','col']].to_dict('records');rng=np.random.default_rng(20261017);checked=0
    def choose(m):
        if m.sum()==0 or (abs(m-m.max())<=1e-10*m.sum()).sum()>1:return 255
        return int(m.argmax()+1)
    for s in sites:
        raw,v,tr,_=read_history(ds,s);w=weights(tr,v.shape[0]);native={y:LUT[a] for y,a in raw.items()}
        for f in [3,10,30]:
            z=np.load(OUT/'history'/s['id']/f'decisions_f{f}.npz');indices=rng.choice(z['total'].size,min(32,z['total'].size),replace=False)
            for flat in indices:
                i,j=divmod(int(flat),z['total'].shape[1]);sl=np.s_[i*f:(i+1)*f,j*f:(j+1)*f];vv=v[sl];ww=w[sl];mass=[]
                for year in [2000,2010]:mass.append(np.array([np.sum(ww[vv&(native[year][sl]==k)]) for k in [1,2,3]]))
                total=mass[0].sum()
                if total==0:continue
                labels=[choose(x) for x in mass];fine=(native[2000][sl]==2)!=(native[2010][sl]==2)
                loss=fine if 255 in labels else fine!=((labels[0]==2)!=(labels[1]==2))
                R=np.sum(ww[vv&loss])/total
                h=[]
                for m in mass:
                    probs=m/total;pos=probs>0;h.append(-np.sum(probs[pos]*np.log2(probs[pos])))
                assert np.isclose(R,z['R'][i,j],rtol=1e-10,atol=1e-12)
                assert np.isclose(max(h),z['H'][i,j],rtol=1e-10,atol=1e-12);checked+=1
    for s in ds.values():s.close()
    q=pd.read_csv(OUT/'history_qc.csv');nat=q[q.budget=='natural90'];gates=pd.read_csv(OUT/'qc_gate_results.csv')
    assert len(q)==24*3*5 and not q.duplicated(['site','scale','budget']).any()
    assert np.allclose(q.D,1-q.J,equal_nan=True)
    assert ((nat.fraction>=.05)&(nat.fraction<=.95)).all()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,3,figsize=(13,4.2),constrained_layout=True)
    for ax,f in zip(axes,[3,10,30]):
        for i,group in enumerate(['Low','High']):
            g=nat[(nat.scale==f)&(nat.group==group)];ax.scatter(np.full(len(g),i),g.D_norm,s=30,alpha=.7,color='#367bb4' if i==0 else '#d3683b')
            ax.plot([i-.18,i+.18],[g.D_norm.median()]*2,c='black',lw=2)
        ax.axhline(.1,c='gray',ls='--');ax.set(xticks=[0,1],xticklabels=['Low','High'],title=f'{f}x{f}: history-only natural budget',ylabel='Budget-normalized selection difference')
    fig.suptitle('v1.2 prerequisite QC: no 2010-2020 performance calculated')
    for ext in ['png','pdf']:fig.savefig(OUT/f'QC_natural_budget.{ext}',dpi=220,bbox_inches='tight')
    plt.close(fig)
    summary=q.groupby(['scale','budget','group']).agg(n=('site','size'),median_Dnorm=('D_norm','median'),median_J=('J','median'),median_rho=('spearman','median'),median_R_zero=('R_zero_fraction','median')).reset_index()
    write_csv(OUT/'qc_summary.csv',summary.to_dict('records'))
    from report_results import texttable
    appendix=f'''\n## 独立核验与结论边界\n\n另以逐块直接求和核验{checked}个历史单元的H和R，均与向量化实现一致。参数、全部72份历史决策数组及旧实验文件哈希核验通过。本次冻结预算都在5%—95%范围内，停止原因是策略区分度条件，而不是预算退化。\n\n{ texttable(summary[summary.budget=='natural90'],['scale','group','n','median_Dnorm','median_J','median_rho','median_R_zero']) }\n\n必须区分全排序的相关性与自然K处的集合重叠：即使评分不同，较大的K仍可能使所选集合接近。本次只按事先明确的D_norm门槛作执行决策，不将该门槛宣称为普适科学判据。没有新的未来F1、p值或Framework胜负结论；不能写成“Proposed再次无效”。固定预算历史QC完整保留，不根据其中的较好区分度改换主要预算。\n\n3×3、10×10的历史QC也未通过各自门槛，但停止未来评价的首要依据是30×30主门槛失败。B2未用于门槛判断，本轮没有开展B2的新评价。\n'''
    report=OUT/'HISTORY_QC_REPORT.md';report.write_text(report.read_text(encoding='utf8')+appendix,encoding='utf8')
    dump(OUT/'history_acceptance.json',dict(time=now(),passed=True,independent_cells_checked=checked,old_files_unchanged=True,decision_files_verified=72,test_data_opened=False,test_F1_computed=False,scientific_gate_passed=False,execution_status='STOPPED_PRIMARY_QC_FAILED'))
    print(f'Independent historical score audit passed: {checked} blocks. Test stage remains stopped.')
if __name__=='__main__':main()
