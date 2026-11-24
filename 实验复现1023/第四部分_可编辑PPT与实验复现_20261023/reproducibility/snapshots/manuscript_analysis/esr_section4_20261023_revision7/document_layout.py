from pathlib import Path
import json,re,hashlib,shutil,zipfile
from copy import deepcopy
from lxml import etree as E
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from manuscript_content import ORIG,THEORY,BLOCKS,TABLES,CAPTIONS
from supplement_content import SUPPLEMENT
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent;SOURCE=BASE/'第四部分1021.docx'
OUT=ROOT/'documents';OUT.mkdir(exist_ok=True)
orig=Document(SOURCE);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
ps=orig._element.xpath('//w:body//w:p')
def newdoc():
 d=Document();s=d.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7);s.top_margin=s.bottom_margin=Cm(2);s.left_margin=s.right_margin=Cm(2)
 normal=d.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(11);normal.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体');normal.paragraph_format.line_spacing=1.3;normal.paragraph_format.space_after=Pt(5);normal.paragraph_format.first_line_indent=Cm(.74)
 for name,size in [('Heading 1',14),('Heading 2',12),('Heading 3',11.5)]:
  st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor(0,0,0);st.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'黑体');st.paragraph_format.space_before=Pt(10);st.paragraph_format.space_after=Pt(5);st.paragraph_format.keep_with_next=True;st.paragraph_format.first_line_indent=0
 foot=s.footer.paragraphs[0];foot.alignment=1;field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');foot._p.append(field)
 return d
def para(d,text,style=None):
 p=d.add_paragraph(style=style)
 # Typeset common mathematical subscripts in prose; retain literal source data in scripts.
 pattern=r'(?<![A-Za-z0-9_])(H_SL|A_SL|TP_A|FP_A|FN_A|SS_w,U|SS_w,total|N_diff|N_joint|R_NC|z_G|z_S|s_t|u_t|û_t|u\*_t|I_T|E_GT|E_GST|E_GS)(?![A-Za-z0-9_])'
 cursor=0
 for match in re.finditer(pattern,text):
  p.add_run(text[cursor:match.start()]);base,index=match.group().split('_',1)
  if base.endswith('*'):p.add_run(base[:-1]);p.add_run('*').font.superscript=True
  else:p.add_run(base)
  run=p.add_run(index);run.font.subscript=True;cursor=match.end()
 p.add_run(text[cursor:])
 if style:p.paragraph_format.first_line_indent=0
 if text.endswith('：'):p.paragraph_format.keep_with_next=True
 return p
def equation(d,element):
 cp=deepcopy(element);d._body._body.insert(len(d._body._body)-1,cp)
def caption(d,text):
 p=para(d,text);p.paragraph_format.first_line_indent=0;p.paragraph_format.line_spacing=1.1;p.paragraph_format.space_after=Pt(7)
 for r in p.runs:r.font.size=Pt(9)
 return p
def figure(d,name):
 p=d.add_paragraph();p.paragraph_format.first_line_indent=0;p.paragraph_format.keep_with_next=True;p.alignment=1
 p.add_run().add_picture(str(ROOT/'figures'/(name+'.png')),width=Cm(16.8))
 p._p.xpath('.//wp:docPr')[0].set('descr',CAPTIONS[name])
 caption(d,CAPTIONS[name])
def table(d,title,headers,rows):
 p=caption(d,title);p.paragraph_format.keep_with_next=True
 t=d.add_table(rows=1,cols=len(headers));t.autofit=True
 for cell,txt in zip(t.rows[0].cells,headers):cell.text=txt
 repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
 for row in rows:
  for cell,txt in zip(t.add_row().cells,row):cell.text=str(txt)
 for ri,row in enumerate(t.rows):
  trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
  for cell in row.cells:
   for p in cell.paragraphs:
    p.paragraph_format.first_line_indent=0;p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1.1
    p.paragraph_format.keep_with_next=ri<len(t.rows)-1
    for r in p.runs:r.font.size=Pt(9);r.bold=ri==0
   tcpr=cell._tc.get_or_add_tcPr();border=OxmlElement('w:tcBorders')
   for edge in ['top','bottom','left','right']:
    b=OxmlElement('w:'+edge);b.set(qn('w:val'),'single' if (ri==0 and edge in ['top','bottom']) or (ri==len(t.rows)-1 and edge=='bottom') else 'nil');b.set(qn('w:sz'),'6');border.append(b)
   tcpr.append(border)
 d.add_paragraph().paragraph_format.space_after=Pt(0)
 return t

