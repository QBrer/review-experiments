"""Audit and manuscript update after the pre-frozen budget experiment."""
from core import *
import pandas as pd
from report_results import texttable
from docx import Document
from docx.shared import Inches

OUT=ROOT/'results/experiment_3_budget'
def main():
    assert (OUT/'calculation_complete.json').exists() and (OUT/'report_complete.json').exists()
    d=pd.read_csv(OUT/'all_results.csv');checks=pd.read_csv(OUT/'budget_checks.csv');scores=pd.read_csv(OUT/'block_scores.csv')
    assert len(d)==300 and len(checks)==125
    assert not d.duplicated(['site','budget','strategy']).any()
    checked=0
    for row in d.itertuples():
        p=OUT/'artifacts'/row.site/f'{row.budget}_{row.strategy}.npz';m=p.with_suffix('.json')
        with np.load(p) as z:
            assert sum(z[k].nbytes for k in z.files)+m.stat().st_size==row.logical_bytes
            if row.budget!='full_raw':
                assert len(z['fine_indices'])==row.K and z['fine_start'].shape==(row.K,30,30)
                assert len(np.unique(z['fine_indices']))==row.K
        assert p.stat().st_size+m.stat().st_size==row.file_bytes;checked+=1
    competition=d[d.strategy!='Reference']
    for _,g in competition.groupby(['site','budget']):
        assert len(g)==2 and g.K.nunique()==1 and g.logical_bytes.nunique()==1
    assert np.allclose(d.F1,2*d.tp_km2/(2*d.tp_km2+d.fp_km2+d.fn_km2),equal_nan=True)
    spec=load(OUT/'frozen_budget_design.json')
    assert all(sha(path)==value for path,value in spec['protected_files'].items())
    # Use saved native inputs from original experiment to characterize mechanism, never select outcomes.
    ds=open_inputs();off=offsets(ds);p=cfg();sites=pd.read_csv(ROOT/'selection/selected_regions.csv').to_dict('records')+[dict(id='B2',group='B2',row=p['B2']['row'],col=p['B2']['col'])];diag=[]
    for s in sites:
        n=1020 if s['id']=='B2' else 1200;raw,v=read_window(ds,off,int(s['row']),int(s['col']),n)
        three=[];sd=[]
        for year in [2010,2020]:
            a=LUT[raw[f'H{year}']];counts=np.stack([blocks(v&(a==c),30) for c in [1,2,3]])
            three.append((counts>0).sum(0)==3);sd.append(int((v&(a==1)).sum()))
        z=checks[(checks.site==s['id'])&(checks.budget=='natural90')].iloc[0]
        diag.append(dict(site=s['id'],group=s['group'],SD_native_pixels_2010=sd[0],SD_native_pixels_2020=sd[1],blocks_three_classes_either_year=int((three[0]|three[1]).sum()),natural_K=int(z.K),natural_overlap=int(z.selected_overlap),same_indices=bool(z.same_indices)))
    for s in ds.values():s.close()
    write_csv(OUT/'mechanism_diagnostics.csv',diag)
    primary=pd.read_csv(OUT/'primary_tests.csv');summary=pd.read_csv(OUT/'summary.csv');notes=[]
    for row in primary.itertuples():
        g=summary[(summary.group==row.group)&(summary.budget=='natural90')].set_index('strategy')
        notes.append(f"{row.group}组的平均F1分别为{g.loc['Baseline','F1']:.6f}和{g.loc['Proposed','F1']:.6f}，配对平均差为{row.mean:.8f}，95%置信区间为[{row.ci_low:.8f}，{row.ci_high:.8f}]，Holm校正p={row.p_Holm:.6f}。正、负及零差窗口分别为{row.positive}、{row.negative}和{row.equal}个。")
    same=checks[(checks.budget=='natural90')&(checks.site!='B2')].same_indices.sum()
    natural_difference=competition[competition.budget=='natural90'].pivot(index='site',columns='strategy',values='F1')
    positive=(natural_difference.Proposed-natural_difference.Baseline)>1e-12
    assess='结果未形成两个组均有明确正向优势的证据，不能据此宣称纯度规则普遍优于熵规则。' if not all((primary['mean']>0)&(primary.p_Holm<.05)) else '两个组的同预算比较均显示正向差异，但解释仍限于本规则和内部产品参考。'
    trows=[]
    for row in primary.itertuples():
        g=summary[(summary.group==row.group)&(summary.budget=='natural90')].set_index('strategy')
        trows.append({'Group':row.group,'Baseline F1':g.loc['Baseline','F1'],'Proposed F1':g.loc['Proposed','F1'],'Mean difference':row.mean,'CI low':row.ci_low,'CI high':row.ci_high,'Holm p':row.p_Holm})
    newtable='\n\nTable 4.4. Matched-budget primary endpoint,12 windows per stratum.\n\n'+texttable(pd.DataFrame(trows),list(trows[0]))+'\n\n'
    replacement='''### 4.5.4 Task-oriented allocation under matched information budgets

第三个实验进一步控制信息成本，以检验有限原始细节应分配到哪些位置，而不是仅比较粗表达与保留更多信息的表达。固定2010—2020年、30×30支持域与三类上位语义，两个竞争策略都保存相同的粗格标签、两期Fine负载、有效mask、行面积及块索引。每窗自然预算K由任一期最大类别占比低于90%的格数确定，预算规则在本轮结果计算前登记。Baseline按两期三类整体熵的最大值排序，Proposed按1减去两期最小优势纯度排序，各选前K格并同时保存两期原始像元。并列按行列顺序，不以参考误差选择位置。该修订在原实验结果已知后提出，使用原24窗作配对对照，不属于新的盲测。

两种策略逐窗严格匹配Fine格数与逻辑字节数，元数据采用相同结构与内容；实际压缩大小仍因标签和索引内容不同而异。这样，主要比较的差异来自同预算下的信息分配位置。主要终点为二值SL变化的面积加权F1，High与Low各进行一次样区配对双侧精确符号置换检验，并对两项检验作Holm校正。

'''+''.join(notes)+newtable+f'''

{assess}自然预算下，24个新窗口中有{int(same)}个窗口的两种策略Fine集合完全相同。这不是需要通过调参消除的异常，而是评分关系的结果：当局部仅有SL与Others时，二元熵与1减最大类别占比单调对应，取两期最大熵和两期最大不纯度可产生相同排序。三类共存时排序才可能分离。因此，纯度规则虽然使用跨期信息，却并不自动比整体熵提供更多针对SL变化位置的辨别能力。

另以10%、25%、50%和75%的Fine格预算作预先规定的次要分析，两个策略在各预算仍严格匹配K，不据曲线选择主预算或调整90%阈值。图4.4给出自然预算的配对比较，图S5给出预算曲线；Coarse-only与Full raw只作为信息量下限与原始参考背景，不参与主要竞争检验。

原不等信息量比较中的F1约0.49→0.976保留为粗表达至细化表达的可行性结果，不能再作为Framework竞争优势的主要证据。细化区域与native内部参考一致，使这类改善具有构造性优势。同预算实验消除了两竞争策略之间Fine数量不等的混杂，但reference仍不能检验真实地表精度；当前证据也仅评价两种具体评分规则，并不代表五步框架所有可能实现。

![Figure 4.4](../figures/experiment_3_budget/Figure_3_budget_primary.png)

Figure 4.4. Paired SL-change F1 at matched natural Fine-cell budgets,2010–2020,factor30. Baseline ranks cells by maximum three-class entropy across the two epochs; Proposed ranks by maximum impurity. Each pair has identical K and logical payload bytes. B2 is excluded from the group tests.

![Figure S5](../figures/experiment_3_budget/Figure_3_budget_curves.png)

Figure S5. Prespecified fixed-budget comparisons and paired F1 differences with descriptive window-bootstrap95% intervals. Coarse-only and Full raw are noncompeting reference representations; fixed-budget results do not replace the natural-budget primary endpoint.

'''
    text=(ROOT/'reports/4.5_正文_空间图增强版.md').read_text(encoding='utf8')
    begin=text.index('### 4.5.4');end=text.index('### 4.5.5')
    text=text[:begin]+replacement+text[end:]
    begin=text.index('### 4.5.5');end=text.index('## Supplementary spatial figures')
    text=text[:begin]+'''### 4.5.5 Implications for the integrated framework

实验1和实验2分别表明，跨期变化表达对空间与语义设置的响应具有条件性，SL内部混合也与操作顺序风险相关。实验3则进一步区分了保留更多原始信息的收益和同等预算下选择信息的价值：前者在原比较中明显，后者必须由修订后的竞争结果判断，不能由前者推出。

这一差别对应框架中的约束分析与结果验证。High/Low描述SL内部子类混合，熵与纯度评分描述三上位类的局部复杂性，两者不代表同一种任务风险。即便明确了SL变化位置任务，若评分没有引入比通用混合度更多的信息，任务导向标签本身也不会保证更有效的资源分配。因此，当前实验支持检查任务信息、表示成本和诊断指标之间的关系，而不支持无条件宣称任务导向规则更优。

所有结果均以原始产品为内部参考。目的性样区、空间相关及地理背景差异限制了泛化，修订设计也没有提供新盲测或外部地表精度证据。后续若改变评分或预算，应另行登记并保留本轮结果，不应针对已经看到的误差反复修改直到取得优势。

'''+text[end:]
    # Original S4 remains a feasibility illustration with an explicit historical label.
    text=text.replace('### Figure S4：变化参考、预测、细化位置与残余误差','### Figure S4：原不等信息量比较的可行性示例（非修订实验主证据）')
    md=ROOT/'reports/4.5_正文_同预算实验3版.md';md.write_text(text,encoding='utf8')
    # Build standalone revised section, using existing markdown renderer without changing old deliverables.
    import build_section45 as builder
    builder.MD=md
    doc=Document();builder.render(doc);doc.save(ROOT/'reports/4.5_正文_同预算实验3版.docx')
    old_source=builder.SOURCE;old_hash=sha(old_source);doc=Document(old_source)
    target=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验');target._p.getparent().remove(target._p)
    anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献');builder.render(doc,anchor)
    doc.save(ROOT/'reports/第四部分_同预算实验3修订版.docx');assert sha(old_source)==old_hash
    dump(OUT/'delivery_acceptance.json',dict(time=now(),passed=True,artifact_costs_verified=checked,matched_pairs=125,old_experiment_files_unchanged=True,natural_identical_masks_new_windows=int(same),new_manuscript=str(md)))
    print('Validated 300 outputs and 125 matched pairs; manuscript revision written.')
if __name__=='__main__':main()
