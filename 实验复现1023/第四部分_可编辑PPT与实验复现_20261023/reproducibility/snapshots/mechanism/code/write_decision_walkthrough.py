from core import *
import pandas as pd
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
import build_section45 as builder
from report_results import texttable

OUT=ROOT/'results/framework_decision_walkthrough'
def main():
    done=load(OUT/'complete.json');assert done['validated']
    area=pd.read_csv(OUT/'area_results.csv');metrics=pd.read_csv(OUT/'location_diagnostics.csv')
    def metric(label,f):return metrics[(metrics.display_id==label)&(metrics.scale==f)&(metrics.event=='change')].iloc[0]
    def av(label,rep,f):return area[(area.display_id==label)&(area.representation==rep)&(area.scale==f)].iloc[0]
    h=av('H01','native paired pixels',1);l=av('L01','native paired pixels',1)
    table='| 样区 | 表达/支持域 | SL2010 | SL2020 | 扩张 | 收缩 | 净变化 | 最大面积差（m²） |\n|---|---|---:|---:|---:|---:|---:|---:|\n'
    for label in ['H01','L01']:
        for f in [1,3,10,30]:
            r=av(label,'native paired pixels' if f==1 else 'composition + transition fractions',f)
            table+=f'| {label} | '+('原生像元配对' if f==1 else f'比例汇总 {f}×{f}')+f' | {r.SL2010_km2:.3f} | {r.SL2020_km2:.3f} | {r.expansion_km2:.3f} | {r.contraction_km2:.3f} | {r.net_change_km2:.3f} | {r.max_absolute_difference_m2:.2e} |\n'
    diagnostic='| 样区 | 支持域 | 变化F1 | 变化IoU | 可判定覆盖率 | 优势类SL2020面积下界（km²） |\n|---|---|---:|---:|---:|---:|\n'
    for label in ['H01','L01']:
        for f in [3,10,30]:
            r=metric(label,f);a=av(label,'dominant-label diagnostic (confirmed lower areas)',f)
            diagnostic+=f'| {label} | {f}×{f} | {r.F1:.4f} | {r.IoU:.4f} | {100*r.coverage:.3f}% | {a.SL2020_km2:.3f} |\n'
    body=f'''### 4.5.4 A task-oriented framework walkthrough

前两个实验说明了跨维耦合与操作顺序对处理结果的影响，本节进一步考察这些关系如何转化为实际决策。框架在同一批24个样区中处理2010—2020年的SL面积统计与变化位置识别，并以H01和L01展示运行记录。两项任务使用相同输入、时相和共同有效域，分别生成与其信息需求相适应的结果。

**任务定义。** 面积任务需要统计两期SL面积、扩张面积、收缩面积及净变化，位置任务需要确定这些转移发生在哪里。前者关注有效面积的完整保留，后者关注同一原始像元的跨期对应。因此，在处理开始时分别规定面积汇总与原生位置输出，而不先将所有数据转换成一种共同粗分辨率表达。

**失配诊断。** 核验发现，Han2010与Han2020的CRS和像元尺寸一致，但源文件网格原点相差119行。流程先根据地理坐标恢复各自索引，确认像元中心一致后读取相同窗口，再以合法类别交集建立共同有效域。语义诊断将四个SL细类映射到SL上位类，保留SD和Others；时间条件则明确为2010与2020的状态比较。由此，位置、类别含义与有效范围成为两项任务共同遵循的对应条件。

**跨维约束分析。** 单个优势类别不能保存格内全部类别面积，因此面积分支选择类别比例。这里进一步区分单期组成与跨期转移：两期SL比例可以得到单期面积和净变化，却不能唯一确定扩张与收缩总量。流程先在原生网格建立SL成员转移，再累计每个支持域内的扩张和收缩面积比例。位置分支则保留原生配对，避免在判断变化之前丢失局部对应。3×3、10×10和30×30优势类别图用于检查尺度造成的信息损失。

**策略组织。** 本例组合依赖驱动的顺序式处理与语义层级处理：先恢复共同空间索引和有效域，再建立统一SL表达及原生跨期关系，随后按任务分别输出组成/转移比例与位置图。面积结果由有效面积加权积分得到；位置结果将非SL→SL标为扩张、SL→非SL标为收缩，其余位置标为SL成员关系未变。图4.6展示原生任务输出与各尺度诊断图，表4.4记录从输入证据到具体选择的过程。

Table 4.4. Recorded decisions in the five-step framework walkthrough.

| 环节 | 检查对象或输入 | 实际发现与依据 | 处理选择 | 输出 |
|---|---|---|---|---|
| 任务定义 | SL面积、净变化、扩张/收缩及其位置 | 面积组成与空间位置的信息要求不同 | 分设面积和位置任务 | 任务合同与输出要求 |
| 失配诊断 | 两期元数据、合法编码、共同范围 | 网格原点相差119行；四个SL细类需层级合并 | 按坐标恢复索引，建立共同mask和SL映射 | 索引、mask、语义一致的两期分类 |
| 跨维约束 | 单期比例、跨期关系和支持域 | 单期组成不能确定扩张/收缩；粗格不能恢复格内位置 | 先建立原生转移，再分别保留比例和位置 | 信息依赖及表达规则 |
| 策略组织 | 统一后的两期像元 | 两任务共享准备过程，输出需求不同 | 面积汇总组成/转移比例，位置保留原生图 | 比例栅格、面积表、方向变化图 |
| 结果验证 | 守恒、收支、文件回读及尺度诊断 | 面积验证通过；粗图存在可量化的位置损失 | 保留所选任务输出；诊断图记录损失 | 检查日志、面积差、F1/IoU与覆盖 |

**任务输出。** H01的SL面积从{h.SL2010_km2:.3f} km²变为{h.SL2020_km2:.3f} km²，扩张{h.expansion_km2:.3f} km²、收缩{h.contraction_km2:.3f} km²，净变化为{h.net_change_km2:.3f} km²。L01两期面积为{l.SL2010_km2:.3f}和{l.SL2020_km2:.3f} km²，扩张{l.expansion_km2:.3f} km²、收缩{l.contraction_km2:.3f} km²，净变化为{l.net_change_km2:.3f} km²。表4.5同时列出三个支持域的实算结果；扩张和收缩由跨期转移比例汇总，而非由单期面积比例直接推断。

Table 4.5. Area-task outputs for H01 and L01. Areas are in km²; numerical differences are in m² relative to native paired-pixel accounting. Fractional summaries retain both single-date composition and paired-transition fractions.

{table}

**验证与反馈。** 24个样区均通过语义面积、比例积分、转移收支及栅格回读检查，最大面积数值差为{done['max_area_error_m2']:.2e} m²。位置诊断显示，同一输入的不同支持域不具有相同的信息保留能力（表4.6）。例如，H01的变化F1在3×3和30×30时分别为{metric('H01',3).F1:.4f}和{metric('H01',30).F1:.4f}，L01对应为{metric('L01',3).F1:.4f}和{metric('L01',30).F1:.4f}。这些指标说明损失发生在何种表达中，为保留原生位置这一任务选择提供具体记录。

Table 4.6. Scale diagnostics against native SL-membership change. The dominant-class area is the confirmed SL-area lower bound; unresolved coverage is reported separately. These diagnostics do not replace the selected native-location output.

{diagnostic}

![Figure 4.6](../figures/framework_decision_walkthrough/Figure_4_6_Task_change_and_supports.png)

Figure 4.6. Native SL expansion/contraction outputs and spatial-support diagnostics for H01 and L01. Columns show the native task result and results obtained by comparing dominant-class maps at3×3,10×10 and30×30 supports. Colors distinguish expansion, contraction and unchanged SL membership; gray indicates unresolved locations. All panels share the same extent.

反馈对应具体环节：面积收支若不一致，返回检查有效域、面积权重和转移汇总；位置输出若只保留粗格类别而不能满足原生定位要求，返回支持域与表达选择。本次面积检查通过，原生位置结果与独立SL成员差分逐像元一致，因此没有触发数值修复或阈值迭代。位置指标用于描述支持域损失，没有另设事后F1门槛。

直接像元差分在本例中承担核对作用。完成相同空间索引和SL成员定义后，d=I_SL,2020−I_SL,2010与框架方向图在24个样区一致；原始细类代码相减还包含SL内部变化，属于不同事件定义。框架提供的是这些判断的依据和执行记录，而不是把常规算术包装成另一种变化检测算法。

上述运行将“需要什么信息”落实为“保留什么表达”，再以实算输出检查处理是否符合要求。面积分支保存组成和转移质量，位置分支保存跨期空间对应，两个结果通过相同输入和面积收支联系起来。本节评价输入产品信息的保留与内部一致性，独立地表准确性需要另外的验证资料。

'''
    base=ROOT/'reports/4.5_三尺度顺序差异与同输入差分对照.md';old=base.read_text(encoding='utf8');begin=old.index('### 4.5.4');end=old.index('### 4.5.5')
    new=old[:begin]+body+old[end:]
    new=new.replace('类别比例图；最后是由这些对应关系计算的SL面积表','类别比例图；最后是由这些对应关系计算的SL面积表')
    assert new[:begin]==old[:begin]
    md=ROOT/'reports/4.5_任务决策与运行记录版.md';md.write_text(new,encoding='utf8')
    (ROOT/'reports/4.5.4_任务导向框架运行示例.md').write_text(body,encoding='utf8')
    builder.MD=md;original=Document(builder.SOURCE);sourcehash=sha(builder.SOURCE)
    for integrated in [False,True]:
        doc=Document(builder.SOURCE) if integrated else Document()
        if integrated:
            target=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验');target._p.getparent().remove(target._p);anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献')
        else:
            anchor=None;doc.styles['Normal'].font.name='Times New Roman';doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].element.rPr.rFonts.set(qn('w:eastAsia'),'宋体');doc.sections[0].left_margin=Inches(.85);doc.sections[0].right_margin=Inches(.85)
        builder.render(doc,anchor);dest=ROOT/'reports'/('第四部分_4.5.4任务决策与运行记录版.docx' if integrated else '4.5_任务决策与运行记录版.docx');doc.save(dest)
        check=Document(dest);assert len(check.tables)==(len(original.tables) if integrated else 0)+5
        if integrated:
            idx=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献')
            assert [p.text for p in check.paragraphs[:57]]==[p.text for p in original.paragraphs[:57]]
            assert [p.text for p in check.paragraphs[idx:]]==[p.text for p in original.paragraphs[58:]]
    builder.MD=ROOT/'reports/4.5.4_任务导向框架运行示例.md';doc=Document();builder.render(doc);doc.save(ROOT/'reports/4.5.4_任务导向框架运行示例.docx')
    assert sha(builder.SOURCE)==sourcehash
    dump(OUT/'paper_checks.json',dict(time=now(),passed=True,section451_to453_unchanged=True,source_unchanged=True,decision_table='4.4',area_table='4.5',scale_diagnostic_table='4.6',real_feedback_repair_claimed=False))
    report=f'''# 重做4.5.4：任务决策与运行记录

已对24个冻结窗口重新运行两个任务分支，共120条五步决策记录。原实验1、2未改，4.5.1—4.5.3文字与上一版完全一致。

关键补充：扩张/收缩总量必须从像元跨期转移汇总，不能只凭两期单独类别比例推断。本次为每窗每尺度输出五个比例波段：SL2010、SL2020、SL成员未变、扩张、收缩。面积按实际有效像元面积加权，保留三个尺度的实际误差。

任务A保留比例及其适用支持域，任务B保留原生位置；粗类别图作为支持域损失诊断。没有新竞争框架、没有调优评分、没有新p值，也没有虚构的反馈迭代。检查通过记录为通过；若违反信息保留要求，应回到具体表示步骤的建议与已实际执行的操作分开记录。

最大面积残差：{done['max_area_error_m2']:.9g} m²。全部面积和位置诊断见CSV；框架步骤、证据、选择和输出见five_step_decision_log.csv。
'''
    (OUT/'RUN_REPORT.md').write_text(report,encoding='utf8')
    print('4.5.4 rewritten with actual decisions, area tables, scale diagnostics; earlier sections preserved.')
if __name__=='__main__':main()
