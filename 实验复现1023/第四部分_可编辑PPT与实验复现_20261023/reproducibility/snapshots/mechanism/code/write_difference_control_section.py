from core import *
import pandas as pd
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
import build_section45 as builder

def main():
    out=ROOT/'results/direct_difference_control';assert load(out/'complete.json')['regions']==24
    summary=pd.read_csv(out/'group_means.csv').set_index('group')
    source=ROOT/'reports/4.5_图件批注修订版.md';s=source.read_text(encoding='utf8')
    s=s.replace('第三部分运行同一批样区的任务流程，选取两组按抽取顺序编号的H01、L01展示输出。','第三部分运行同一批样区的任务流程，并增加同输入的像元差分对照，选取两组按抽取顺序编号的H01、L01展示输出。')
    extra='''为检查直接像元运算与任务表达的关系，在相同Han2010/2020输入、样区范围和有效域上设置差分对照。原始码差分为d_raw=code2020−code2010；目标成员差分为d_SL=I_SL,2020−I_SL,2010，其中SL成员由原始编码21—24确定。前者的非零值表示原分类体系中的类别变化，后者的+1、−1和0分别表示SL扩张、收缩和成员关系未变。全部差值采用有符号整数计算，避免无符号类别存储导致的数值回绕。

两种差分回答不同问题（表4.5）。原始码变化除了包含SL扩张和收缩，还包含SL内部子类转换及非SL类别之间的转换。统一到SL成员关系后，直接差分与框架输出在24个样区逐像元一致，方向差异数均为0。这说明，对空间与语义对应已经明确的输入，SL变化可以由简单差分实现；框架运行中的关键环节是明确比较对象、建立共同有效范围及保证两期标签具有一致的任务含义。图4.7上排给出同任务对照，下排展示原始码变化与SL成员变化之间的区别。

Table 4.5. Same-input subtraction control. Values are mean areas per window in each group (km²); the last column counts directional disagreements between direct SL-membership subtraction and the framework output.

| 区域 | 原始码变化面积 | SL成员变化面积 | 额外的非SL成员变化面积 | 同任务方向差异像元数 |
|---|---:|---:|---:|---:|
'''
    for group in ['Low','High']:
        r=summary.loc[group];extra+=f'| {group} | {r.raw_code_changed_km2:.3f} | {r.SL_changed_km2:.3f} | {r.raw_extra_non_SL_change_km2:.3f} | {int(r.SL_control_framework_disagreement_pixels)} |\n'
    extra+='''
![Figure 4.7](../figures/direct_difference_control/H01_direct_subtraction_control.png)

Figure 4.7. Direct subtraction control in H01 using the same Han2010/2020 inputs and valid domain as the framework. Upper row: direct SL-membership subtraction, framework directional change, and their disagreement. Lower row: any raw-code change, SL-membership change, and the difference between these event definitions. Red denotes disagreement; the empty upper-right panel records identical same-task outputs. Raw-code signs are not interpreted as SL expansion or contraction.

'''
    marker='### 4.5.5 Implications for multidimensional alignment';assert marker in s;s=s.replace(marker,extra+marker)
    md=ROOT/'reports/4.5_三尺度顺序差异与同输入差分对照.md';md.write_text(s,encoding='utf8');builder.MD=md
    original=Document(builder.SOURCE);source_hash=sha(builder.SOURCE)
    for whole in [False,True]:
        doc=Document(builder.SOURCE) if whole else Document()
        if whole:
            target=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验');target._p.getparent().remove(target._p);anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献')
        else:
            anchor=None;doc.styles['Normal'].font.name='Times New Roman';doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].element.rPr.rFonts.set(qn('w:eastAsia'),'宋体');doc.sections[0].left_margin=Inches(.85);doc.sections[0].right_margin=Inches(.85)
        builder.render(doc,anchor)
        dest=ROOT/'reports'/('第四部分_三尺度顺序差异与同输入差分对照版.docx' if whole else '4.5_三尺度顺序差异与同输入差分对照版.docx');doc.save(dest)
        check=Document(dest);assert len(check.inline_shapes)==(len(original.inline_shapes) if whole else 0)+7
        assert len(check.tables)==(len(original.tables) if whole else 0)+4
        if whole:
            refidx=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献')
            assert [p.text for p in check.paragraphs[:57]]==[p.text for p in original.paragraphs[:57]]
            assert [p.text for p in check.paragraphs[refidx:]]==[p.text for p in original.paragraphs[58:]]
    assert sha(builder.SOURCE)==source_hash
    dump(out/'manuscript_check.json',dict(time=now(),passed=True,source_unchanged=True,figures_added=7,tables_added=4,control_inputs='same Han2010/Han2020 as experiment',main_exp1_2_results_unchanged=True))
    print('Revised manuscript created; same-input subtraction explicitly distinguished from raw-code change.')
if __name__=='__main__':main()
