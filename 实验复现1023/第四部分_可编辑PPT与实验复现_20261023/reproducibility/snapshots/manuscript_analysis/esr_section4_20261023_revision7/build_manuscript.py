from document_layout import *
from equations import display

d=newdoc();body=[]
for i in range(87):
 if i==4:figure(d,'Fig4_1');continue
 if i==5 or 52<=i<=77:continue
 if i==51:
  table(d,THEORY[51],[THEORY.get(x,ORIG[x]) for x in range(52,57)],[[THEORY.get(x,ORIG[x]) for x in range(k,k+5)] for k in [57,62,67,72]]);caption(d,ORIG[77]);continue
 text=THEORY.get(i,ORIG[i]);body.append(text)
 if i in [14,16,18]:equation(d,ps[i]);continue
 para(d,text,'Heading 1' if i==0 else 'Heading 3' if re.match(r'^4\.\d\.\d\.',text) else 'Heading 2' if re.match(r'^4\.\d\.',text) else None)
for kind,text in BLOCKS:
 if kind=='fig':figure(d,text)
 elif kind=='eq':display(d,text)
 elif kind=='lead':
  p=para(d,text);p.paragraph_format.first_line_indent=0;p.paragraph_format.keep_with_next=True
  for run in p.runs:run.bold=True
  body.append(text)
 elif kind=='table':t=TABLES[text];table(d,t['caption'],t['headers'],t['rows'])
 else:para(d,text,'Heading 2' if kind=='h1' else 'Heading 3' if kind=='h2' else None);body.append(text)
para(d,'参考文献','Heading 1')
for i in range(335,480):
 p=para(d,ORIG[i]);p.paragraph_format.first_line_indent=0;p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_after=Pt(3)
 for run in p.runs:run.font.size=Pt(9)
main=OUT/'B_第四部分_五项批注修订稿.docx';d.save(main)
s=newdoc()
for kind,text in SUPPLEMENT:
 if kind=='fig':figure(s,text)
 elif kind=='eq':display(s,text)
 else:para(s,text,'Heading 1' if kind=='h0' else 'Heading 2' if kind=='h1' else None)
s.save(OUT/'S1_实现细节与补充比较.docx')

c=newdoc();para(c,'第四部分：五项批注修改与核查说明','Heading 1')
para(c,'本轮以revision6为基准，按作者五项PDF批注修改。图4.1直接使用本轮提供的图片；其余修改涉及公式与实验算子的对应、Wang图例、应用流程细节及误差相对降幅。')
table(c,'批注处理',['批注','修改与依据','核查结果'],[
['替换图4.1','原样置入作者提供的987×609 PNG，不改文字或结构。','PNG哈希与附件一致；PDF、SVG是原位图封装，不宣称可编辑矢量或600 dpi。'],
['非交换性与实验对应','保留式(4-1)—(4-3)，补充同一有效面积、六类到三类映射和近似并列规则；例子改为四个SL细类各15%。','检查core.py的aggregate、unique_mode及experiments.py的共同可判定分母；20000组非均匀类别面积检验式(4-3)与代码判定一致，另核并列、空格和具体例子。'],
['Wang类别编码含义','图4.2逐项显示1—14编码和完整英文名称。','依据Wang等原论文表2（PDF第5页），使用最终14类产品码表，而非样本阶段编码。'],
['图4.7内容不足','每个框架环节细化为输入／依据—操作—输出；加入13像元安全边界、169候选、联合搜索、开发参数及验证设置。','保留五环节和Times New Roman，增加细节但不增加未执行的反馈或选策机制。'],
['像元误差不直观','像元绝对差和原CI保留，同时报告相对比较基准的均值降幅。','全部百分比使用未舍入分区等权均值，非逐窗百分比平均；没有据点估计增设显著性结论。']])
para(c,'相对误差降幅','Heading 2')
table(c,'按未舍入均值计算',['参数条件／比较','基准→方法','平均误差相对变化'],[
['共同参数','G → GS','降低54.7%'],['共同参数','G → GT','降低19.2%'],['共同参数','G → GST','降低69.8%'],['共同参数，增加语义','GT → GST','降低62.7%'],['共同参数，增加时间','GS → GST','降低33.3%，原绝对差区间仍跨0'],['各方法独立校准','G → GST','降低65.0%，原绝对差区间仍跨0'],['共同参数，两期位移不同','G → GT','增加23.9%']])
para(c,'计算口径：以基准平均误差减去方法平均误差，再除以基准平均误差，换算为百分比。误差单位均为原生像元；百分比对应相同统计域及情景权重。各次比较的基准名称均在正文明确。完整未舍入值见figure_data/error_reduction_percentages.csv。')
para(c,'图例来源与保留内容','Heading 2')
para(c,'Wang等（2025），Long-term Land Cover Dataset of the Mongolian Plateau Based on Multi-source Data and Rich Sample Annotations，表2，第5页。https://www.nature.com/articles/s41597-025-05648-8.pdf 。类别编码及核查位置另存legend_verification.json，正文使用原参考文献编号[130]。')
para(c,'作者提供图4.1中的Hierarchical与其余文字原样保留，正文仍按层级感知机制说明其与顺序、迭代和联合组织方式的组合关系。图4.1在16.8 cm排版宽度下约149 dpi，未通过插值伪装为高分辨率。图4.2与图4.7重新绘制并提供可编辑SVG、矢量PDF及600 dpi位图。')
para(c,'原始三个公式的数学内容、145条参考文献、原实验结果及参数保持。A为相对revision6的原生修订，A0为相对原始1021稿的修订，B为干净稿。公式／算子、百分比、字体及修订核验分别见formula_operator_audit.json、final_audit.json及word_validation.json。旧稿和原输出不覆盖。')
c.save(OUT/'C_五项批注修改与核查说明.docx')

new=Document(main);math=new._element.xpath('//m:oMath');originalmath=orig._element.xpath('//m:oMath')
assert [E.tostring(x,method='c14n',exclusive=True) for x in math[:3]]==[E.tostring(x,method='c14n',exclusive=True) for x in originalmath]
assert len(math)==9 and len(new.inline_shapes)==8 and len(new.tables)==9
text=[p.text for p in new.paragraphs];assert text[text.index('参考文献')+1:]==[ORIG[i] for i in range(335,480)]
for needle in ['4.1指出','4.1指出'.replace('.','．'),'对应4.1','4.1 →','4.2 →','4.1—4.4 →']:assert needle not in ''.join(body)
record=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),original_equations_preserved=3,standalone_new_equations=6,total_main_equations=9,supplement_equations=1,references_preserved=145,main_figures=8,content_tables=3,borderless_equation_layout_rows=6,supplement_figures=3,text_characters_excluding_references=sum(map(len,body)),explicit_section_mapping_removed=True)
(ROOT/'manuscript_checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8');print(record)
