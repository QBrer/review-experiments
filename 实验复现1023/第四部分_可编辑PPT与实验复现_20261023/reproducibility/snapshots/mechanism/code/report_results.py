from core import *
import pandas as pd
from scipy.stats import rankdata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'savefig.dpi':220})
def describe(x,rng):
    x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
    out=dict(n=n,mean=float(np.mean(x)) if n else np.nan,median=float(np.median(x)) if n else np.nan,ci_low=np.nan,ci_high=np.nan)
    if n>=5:
        boot=np.mean(x[rng.integers(0,n,(10000,n))],axis=1);out['ci_low'],out['ci_high']=np.quantile(boot,[.025,.975])
    return out
def paired(d,rng,primary=False):
    d=np.asarray(d,float);d=d[np.isfinite(d)];out=describe(d,rng)
    z=d[d!=0];rk=rankdata(abs(z));out['rank_biserial']=float(np.sum(rk*np.sign(z))/rk.sum()) if len(z) else 0.
    out['p_raw']=np.nan
    if primary and len(d)>=5:
        signs=1-2*((np.arange(2**len(d))[:,None]>>np.arange(len(d)))&1)
        null=np.abs((signs*d).mean(1));out['p_raw']=float(np.mean(null>=abs(d.mean())-1e-14))
    return out
def texttable(df,cols):
    header='| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'
    def val(x):return f'{x:.6g}' if isinstance(x,(float,np.floating)) else str(x)
    return header+'\n'.join('| '+' | '.join(val(row[c]) for c in cols)+' |' for _,row in df.iterrows())
def main():
    assert (ROOT/'qc/experiments_complete.json').exists()
    rng=np.random.default_rng(20261016)
    paths={'coupling':'experiment_1/coupling','semantic':'experiment_1/semantic_change','order':'experiment_2/order','phase':'experiment_2/phase','area':'experiment_3/area','change':'experiment_3/change','cost':'experiment_3/cost','window':'qc/window_qc'}
    data={k:pd.read_csv(ROOT/'results'/f'{path}.csv') for k,path in paths.items()}
    for d in ['figures','tables','reports','results/statistics']:(ROOT/d).mkdir(parents=True,exist_ok=True)
    c=data['coupling'];o=data['order'];ch=data['change'];cost=data['cost'];ar=data['area']
    summary=[]
    for (group,year,f,sem),g in c[c.group!='B2'].groupby(['group','start_year','scale','semantic']):
        for metric in ['F1','IoU','area_error_km2','fp_km2','fn_km2','coverage']:
            summary.append(dict(group=group,start_year=year,scale=f,semantic=sem,metric=metric,**describe(g[metric],rng)))
    t1=pd.DataFrame(summary);write_csv(ROOT/'tables/Table_1_Coupling.csv',summary)
    summary=[]
    for (group,f),g in o.groupby(['group','scale']):
        for metric in ['R_NC_count','R_NC_area','affected_km2','coverage','SL_signed_difference_lower_km2']:
            summary.append(dict(group=group,scale=f,metric=metric,**describe(g[metric],rng),sum_joint=int(g.n_joint.sum()),sum_disagree=int(g.n_disagree.sum())))
    t2=pd.DataFrame(summary);write_csv(ROOT/'tables/Table_2_Noncommutativity.csv',summary)
    summaries=[];stats=[]
    for (group,year,f,event),g in ch[ch.group!='B2'].groupby(['group','start_year','scale','event']):
        for metric in ['F1','IoU','fp_km2','fn_km2','area_error_km2','coverage']:
            pivot=g.pivot(index='site',columns='strategy',values=metric)
            d=pivot.Proposed-pivot.Baseline
            primary=year==2010 and f==30 and event=='change' and metric=='F1'
            row=dict(task='change',group=group,start_year=year,scale=f,event=event,metric=metric,primary=primary,**paired(d,rng,primary),missing_pairs=int(d.isna().sum()))
            stats.append(row)
            for strategy,gg in g.groupby('strategy'):
                summaries.append(dict(task='change',group=group,start_year=year,scale=f,event=event,metric=metric,strategy=strategy,**describe(gg[metric],rng)))
    prim=[x for x in stats if x['primary']];assert len(prim)==2
    ps=np.array([x['p_raw'] if np.isfinite(x['p_raw']) else 1 for x in prim]);idx=np.argsort(ps);adj=np.maximum.accumulate(ps[idx]*np.array([2,1]));adj=np.minimum(adj,1)
    for i,j in enumerate(idx):prim[j]['p_Holm']=float(adj[i]) if np.isfinite(prim[j]['p_raw']) else np.nan
    for (group,f),g in ar[ar.group!='B2'].groupby(['group','scale']):
        for metric in ['absolute_error_km2','relative_error']:
            pi=g.pivot(index='site',columns='strategy',values=metric);d=pi.Proposed-pi.Baseline
            stats.append(dict(task='area',group=group,start_year=2020,scale=f,event='SL_area',metric=metric,primary=False,**paired(d,rng),missing_pairs=int(d.isna().sum())))
            for strategy,gg in g.groupby('strategy'):summaries.append(dict(task='area',group=group,start_year=2020,scale=f,event='SL_area',metric=metric,strategy=strategy,**describe(gg[metric],rng)))
    write_csv(ROOT/'tables/Table_3_Framework.csv',summaries);write_csv(ROOT/'results/statistics/paired_statistics.csv',stats)
    write_csv(ROOT/'results/statistics/primary_tests.csv',prim)
    # Explicit within-window contrasts, never pool pixels as independent observations.
    contrasts=[]
    for (group,year),g in c[c.group!='B2'].groupby(['group','start_year']):
        pv=g.pivot(index='site',columns=['semantic','scale'],values='F1')
        d=(pv['coarse3',30]-pv['coarse3',3])-(pv['fine6',30]-pv['fine6',3])
        contrasts.append(dict(experiment=1,contrast='scale30-3 by coarse-fine interaction',group=group,start_year=year,**paired(d,rng)))
    for group,g in c[c.group!='B2'].groupby('group'):
        pv=g.pivot(index='site',columns=['start_year','semantic','scale'],values='F1')
        for sem in ['fine6','coarse3']:
            d=(pv[2000,sem,30]-pv[2000,sem,3])-(pv[2015,sem,30]-pv[2015,sem,3])
            contrasts.append(dict(experiment=1,contrast='scale30-3 by 20year-5year contrast '+sem,group=group,**paired(d,rng)))
    increments={}
    for group,g in o[o.group!='B2'].groupby('group'):
        pv=g.pivot(index='site',columns='scale',values='R_NC_count');d=pv[30]-pv[3];increments[group]=d.to_numpy()
        contrasts.append(dict(experiment=2,contrast='NC_count scale30-3',group=group,**paired(d,rng)))
    hi=increments['High'];lo=increments['Low'];boot=hi[rng.integers(0,len(hi),(10000,len(hi)))].mean(1)-lo[rng.integers(0,len(lo),(10000,len(lo)))].mean(1)
    contrasts.append(dict(experiment=2,contrast='(scale30-3 High)-(scale30-3 Low)',group='High-Low',n=len(hi)+len(lo),mean=hi.mean()-lo.mean(),median=np.median(hi)-np.median(lo),ci_low=np.quantile(boot,.025),ci_high=np.quantile(boot,.975),p_raw=np.nan))
    write_csv(ROOT/'results/statistics/interaction_contrasts.csv',contrasts)
    # Figure1: raw unsmoothed per-window mean loss, with common color scale.
    fig,axes=plt.subplots(2,3,figsize=(12,6.5),constrained_layout=True)
    for i,group in enumerate(['Low','High']):
        for j,year in enumerate([2015,2010,2000]):
            g=c[(c.group==group)&(c.start_year==year)]
            mat=g.groupby(['semantic','scale']).F1.mean().unstack('scale').reindex(['fine6','coarse3'])[[3,10,30]]
            values=1-mat.to_numpy();im=axes[i,j].imshow(values,vmin=0,vmax=1,cmap='magma')
            axes[i,j].set(xticks=[0,1,2],xticklabels=['3x3','10x10','30x30'],yticks=[0,1],yticklabels=['Fine 6','Coarse 3'],title=f'{group}: {year}-2020')
            for a in range(2):
                for b in range(3):axes[i,j].text(b,a,f'{values[a,b]:.3f}',ha='center',va='center',color='white' if values[a,b]<.65 else 'black')
    fig.colorbar(im,ax=axes,label='Mean change-location loss (1 - area-weighted F1)');fig.savefig(ROOT/'figures/Figure_1_Coupling.png');fig.savefig(ROOT/'figures/Figure_1_Coupling.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.4),constrained_layout=True)
    colors={'Low':'#457b9d','High':'#d85a36','B2':'#53418b'}
    for group in ['Low','High','B2']:
        g=o[o.group==group]
        for sid,gg in g.groupby('site'):axes[0].plot(gg.scale,gg.R_NC_count*100,color=colors[group],alpha=.15)
        mean=g.groupby('scale').R_NC_count.mean();axes[0].plot(mean.index,mean.values*100,'o-',label=group,color=colors[group],lw=2)
    axes[0].set(xlabel='Aggregation factor',ylabel='Non-commutative cells (%)',title='Window means; thin lines = windows',xticks=[3,10,30]);axes[0].legend()
    phase=data['phase'];vals=[phase[phase.group==g].groupby('site').R_NC_count.agg(lambda x:100*(x.max()-x.min())).values for g in ['Low','High','B2']]
    axes[1].boxplot(vals,labels=['Low','High','B2']);axes[1].set(ylabel='Across-phase range (percentage points)',title='30x30 common interior phase check')
    sel=pd.read_csv(ROOT/'selection/selected_regions.csv');joined=o[o.scale==30].merge(sel[['id','H_SL']],left_on='site',right_on='id')
    for group in ['Low','High']:
        gg=joined[joined.group==group];axes[2].scatter(gg.H_SL,100*gg.R_NC_count,label=group,color=colors[group])
    axes[2].set(xlabel='SL conditional entropy (bits)',ylabel='Non-commutative cells (%)',title='Selection feature vs observed outcome');axes[2].legend()
    fig.savefig(ROOT/'figures/Figure_2_Noncommutativity.png');fig.savefig(ROOT/'figures/Figure_2_Noncommutativity.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),constrained_layout=True)
    primary=ch[(ch.start_year==2010)&(ch.scale==30)&(ch.event=='change')&(ch.group!='B2')]
    for i,group in enumerate(['Low','High']):
        gg=primary[primary.group==group];pv=gg.pivot(index='site',columns='strategy',values='F1')
        for _,row in pv.iterrows():axes[i].plot([0,1],[row.Baseline,row.Proposed],'-o',alpha=.5,color=colors[group])
        axes[i].set(xticks=[0,1],xticklabels=['Baseline','Proposed'],ylabel='Area-weighted SL-change F1',ylim=(0,1.03),title=group+' | 2010-2020, 30x30')
    cp=cost[(cost.start_year==2010)&(cost.scale==30)&(cost.group!='B2')].merge(primary[['site','strategy','F1']],on=['site','strategy'])
    for strategy,marker in [('Baseline','o'),('Proposed','^')]:
        gg=cp[cp.strategy==strategy];axes[2].scatter(gg.file_bytes/gg.native_file_bytes,gg.F1,label=strategy,marker=marker,alpha=.7)
    axes[2].set(xlabel='Stored bytes / native-expression bytes',ylabel='SL-change F1',title='Accuracy-cost trade-off');axes[2].legend()
    fig.savefig(ROOT/'figures/Figure_3_Framework.png');fig.savefig(ROOT/'figures/Figure_3_Framework.pdf');plt.close(fig)
    # Selection QC map is not an additional scientific experiment.
    fig,ax=plt.subplots(figsize=(9,5));candidates=pd.read_csv(ROOT/'selection/candidates.csv');elig=candidates[candidates.reason=='eligible']
    ax.scatter(elig.lon,elig.lat,s=3,c='lightgray',label='Eligible raw-feature candidates')
    for group in ['Low','High']:
        gg=sel[sel.group==group];ax.scatter(gg.lon,gg.lat,label=group,color=colors[group])
    bp=cfg()['B2'];ax.scatter([bp['lon']],[bp['lat']],marker='*',s=130,color=colors['B2'],label='B2 historical case');ax.set(xlabel='Longitude',ylabel='Latitude',title='Frozen new sample windows (centers)');ax.legend();fig.tight_layout();fig.savefig(ROOT/'figures/Selection_QC.png');plt.close(fig)
    b2=o[(o.site=='B2')&(o.scale==30)].iloc[0];history=cfg()['B2']['historical_rate']
    nc=t2[(t2.metric=='R_NC_count')&(t2.group!='B2')]
    interaction=contrasts[-1]
    primdf=pd.DataFrame(prim)
    costsummary=cp.groupby(['group','strategy']).agg(mean_F1=('F1','mean'),mean_file_bytes=('file_bytes','mean'),mean_refined_area_fraction=('refined_area_fraction','mean')).reset_index()
    costsummary['mean_MB']=costsummary.mean_file_bytes/1e6
    write_csv(ROOT/'tables/Cost_primary_endpoint.csv',costsummary.to_dict('records'))
    groupfeatures=sel.groupby('group')[['H_SL','pSL','pOthers','H_six','lon','lat']].agg(['mean','min','max']);groupfeatures.to_csv(ROOT/'selection/group_balance.csv',encoding='utf-8-sig')
    reasons=candidates.reason.value_counts().to_dict();threshold=load(ROOT/'selection/thresholds.json')
    report=f'''# 新实验结果报告

完成时间（UTC）：{now()}。所有新实验均来自新目录参数与选区；旧工作流、旧九窗和旧阈值没有用于新样区设计。B2仅作为历史案例单列。

## 执行与选区

共扫描{len(candidates)}个完整1200×1200候选窗；合格候选{len(elig)}个。排除/保留统计：`{reasons}`。
SL条件熵Q25={threshold['Q25']:.9f} bit，Q75={threshold['Q75']:.9f} bit；按冻结规则抽取High和Low各12窗，B2之外至少100km，所有新窗中心至少50km。
窗口文件：`selection/selected_regions.csv`、`selected_regions.geojson`。冻结先于实验；输入、规则、窗口数组和代码均有追溯记录。

两组是SL内部混合程度的观察性分层，不是结果驱动的高低非交换率分组。窗口为目的性压力测试，不代表整个蒙古高原总体。空间分散不证明统计独立；`selection/group_balance.csv`记录SL组成和经纬度差异。

## 实验1：真实跨期变化的表达

已完成24个新窗及B2 × 18条件，共{len(c)}行。Figure 1展示各层级相对于其自身native变化参考的1−F1，没有把合法语义合并删除的SL内部变化统一当错。
明确的同窗尺度×语义、尺度×时段差异保存在`results/statistics/interaction_contrasts.csv`，而非只凭热图颜色宣称交互成立。

{texttable(pd.DataFrame(contrasts).query('experiment == 1'),['contrast','group','start_year','mean','ci_low','ci_high'])}

表中尺度差为F1(30)−F1(3)，交互对比进一步作语义或时间跨度的差中之差；CI跨零则证据不确定。时间跨度与实际变化过程并存，不能作纯时间因果解释。所有CI为描述性点区间，未作同时覆盖校正。

## 实验2：操作非交换性

下面是窗口等权平均计数率（比例单位0—1），不是将全组像元合并后的总体率：

{texttable(nc,['group','scale','n','mean','median','ci_low','ci_high','sum_joint','sum_disagree'])}

“High的尺度增幅−Low的尺度增幅”（30减3）的均值为{interaction['mean']:.8f}，95%CI [{interaction['ci_low']:.8f}, {interaction['ci_high']:.8f}]。它可以为正、负或不确定；不据此重新定义组别。

B2/2020/f30的新共同mask面积率={b2.R_NC_area*100:.12f}%，计数率={b2.R_NC_count*100:.12f}%，历史面积率={history*100:.12f}%。本次与历史口径的面积率绝对差={abs(b2.R_NC_area-history)*100:.12f}个百分点。即使数值一致，B2仍不是新的独立验证样本。

分歧方向、SL面积差和覆盖见`results/experiment_2/order.csv`与`transitions.csv`。所有25窗的九相位结果见`phase.csv`；评价中心为[30:n−30)，不能与主全窗零相位直接混合。High不必在每个窗或尺度超过Low。

## 实验3：任务适配表达及成本

主要终点固定为2010→2020、30×30、二值SL变化的面积加权F1。差值=Proposed−Baseline；检验为样区配对均值差的双侧精确符号置换，两个组别的主要检验作Holm校正。

{texttable(primdf,['group','n','mean','median','ci_low','ci_high','rank_biserial','p_raw','p_Holm','missing_pairs'])}

主要终点输出成本与细化比例：

{texttable(costsummary,['group','strategy','mean_F1','mean_MB','mean_refined_area_fraction'])}

Framework不读分组标签或参考误差；只按两期粗格纯度是否低于90%决定共同细化。其改善来源是保留更多原始空间细节，不是独立纠正产品分类错误。必须结合细化比例与成本判断优势，不声称同成本普遍更准。

面积比例的完整格守恒误差为浮点量级，性质检查已通过；该结果不能充当外部精度验证或独立的框架优越性证据。面积逐窗误差与未知区间完整保存在`results/experiment_3/area.csv`。

存储同时计入完整有效mask、行面积、层级索引、两期原始细化负载和JSON元数据；实际bytes为压缩NPZ加JSON，未压缩bytes为数组nbytes加元数据。各方法单独计入共享信息，不把共享mask隐去后比较。native表达仅是成本背景。实际压缩率依数据结构，原始表示不保证是每种混合编码实际bytes的绝对上界。

## 对研究问题的明确判断

1. **耦合证据具有条件性。** 同窗尺度效应随语义层级和时间跨度变化；部分对比CI跨零，不能宣称每个条件都有同样强的交互。各语义层级采用各自参考，跨层级的F1差异还受事件组成和基率改变影响。
2. **非交换性确实存在。** High组平均计数率从3×3的0.7774%增至30×30的4.8428%，Low从0.1914%增至0.9479%。High的尺度增幅更大，支持SL内部混合与尺度相关的风险差异；仍是观察性关联。
3. **任务后果不能简单归因于非交换率。** 操作顺序产生SL面积差，但实验3比较的是统一类别表达与自适应细化；它同时改变信息量，不能把全部F1收益解释为修复非交换性。
4. **Framework在两个组都有较大改善，而非主要集中于High。** 主终点High平均F1从0.4914到0.9757，Low从0.4934到0.9758；配对增益分别约0.4844和0.4824。现有结果不支持“Low收益很小、High收益明显更大”的理论叙述，也不能因两组增益接近就声称已证明等效。
5. **代价明显。** High/Low平均细化有效面积约69.70%/64.31%；实际压缩文件平均约为各自Baseline的23.90/24.54倍。Figure3同时显示与native表达相比的成本，不能隐藏这些成本只展示高F1。
6. **评价有结构性优势。** 细化区域直接保留与内部reference相同的native标签，因此这些位置的产品表达误差按设计消失。这是任务保留机制及成本权衡的验证，不是独立地表真值下的新准确性证明，也不能仅凭很小p值证明五步框架的普适有效性。

上述数字取当前完成表格；规则未因结果修改。后续若开展另一设计应另行预先登记，保留本次不支持条件性框架收益的发现。

## 限制、异常与结论范围

- Reference来自Han原始产品，独立于预测输出但不独立于输入误差；结论限于原始产品信息保留。
- 每组12个目的性样区，空间相关、组成和地理背景差异可能仍存在。无像元级显著性推断，B2不进主要检验。
- 仅两个预定主检验有p值；其他条件全部保留为次要描述性分析，不据其显著性替换主要终点。
- 零分母记NA；未确定变化不删除参考域，参考正例计FN，覆盖另报。
- 首次运行遇到本机其他软件PROJ数据库冲突，已在当前Python进程指定Rasterio附带数据库；随后全部整数网格检查通过，没有重采样。初次失败记录保留。
- 扫描阶段早停覆盖不足时记录的是覆盖上界（不冒称完整五输入交集值），这些窗口按数学上必不合格排除。

原始数据和历史目录未修改。执行参数见`parameters/frozen_parameters.json`；实现说明见`parameters/IMPLEMENTATION_FREEZE.md`；检验与重建检查见`qc/`。这份报告与全部逐条件表共同构成结果，不删除低效应、零效应或反方向结果。
'''
    (ROOT/'reports/FINAL_RESULTS.md').write_text(report,encoding='utf8')
    for exp,title,body in [
        (1,'时间—空间—语义耦合','18条件/窗；主图Figure_1_Coupling.png，Table_1_Coupling.csv。参考按各自语义层级建立；变化面积、FP/FN、F1/IoU与coverage全部报告。详细交互对比见统计表。'),
        (2,'操作非交换性','主表Table_2_Noncommutativity.csv同时保留计数与面积口径；B2单列；九相位共同内部范围单独评价。完整分歧方向及面积后果见order.csv和transitions.csv。'),
        (3,'框架任务表现','主要终点、双侧配对检验及Holm校正结果见primary_tests.csv。主要收益来自按90%规则保留局部细节，须结合Cost_primary_endpoint.csv评价。面积比例守恒仅作QC。')]:
        (ROOT/'results'/f'experiment_{exp}'/f'EXPERIMENT_{exp}_REPORT.md').write_text(f'# 实验{exp}：{title}\n\n{body}\n\n完整数值、论证和限制见本项目 reports/FINAL_RESULTS.md。\n',encoding='utf8')
    for name in ['order','area','change','phase']:
        write_csv(ROOT/'results/B2_case'/f'{name}.csv',data[name][data[name].site=='B2'].to_dict('records'))
    dump(ROOT/'qc/report_complete.json',dict(time=now(),primary_tests=prim,figure_count=3,table_count=3,secondary_p_values_computed=False))
    print(json.dumps(clean(dict(primary=prim,NC=nc[['group','scale','mean']].to_dict('records'),B2_area_rate=b2.R_NC_area)),indent=2),flush=True)
if __name__=='__main__':main()
