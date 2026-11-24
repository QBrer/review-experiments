from pathlib import Path
import re,hashlib,json
import sys
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(r'C:\Users\QBrer\OneDrive\桌面\数据对齐\1015\4.6-1015\第四部分1015_分区流程图修订稿 - 副本.docx')
MD=ROOT/'reports/4.5_正文.md'
SUFFIX=''
if '--spatial' in sys.argv:
    MD=ROOT/'reports/4.5_正文_空间图增强版.md'
    SUFFIX='_空间图增强版'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(doc,anchor,element):
    if anchor is not None:anchor.addprevious(element)
def render(doc,anchor=None):
    lines=MD.read_text(encoding='utf8').splitlines();i=0
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('|'):
            rows=[]
            while True:
                if not re.fullmatch(r'[|\s:\-]+',line):rows.append([x.strip() for x in line.strip('|').split('|')])
                if i>=len(lines) or not lines[i].strip().startswith('|'):break
                line=lines[i].strip();i+=1
            tab=doc.add_table(rows=1,cols=len(rows[0]));tab.style='Table Grid'
            for j,v in enumerate(rows[0]):tab.rows[0].cells[j].text=v
            for row in rows[1:]:
                cells=tab.add_row().cells
                for j,v in enumerate(row):cells[j].text=v
            for row in tab.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for run in p.runs:run.font.size=Pt(9)
            trpr=tab.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
            put(doc,anchor,tab._tbl);continue
        match=re.match(r'!\[(.*?)\]\((.*?)\)',line)
        if match:
            p=doc.add_paragraph();p.add_run().add_picture(str((MD.parent/match[2]).resolve()),width=Inches(6.1));put(doc,anchor,p._p);continue
        if line.startswith('### '):p=doc.add_paragraph(line[4:],style='Heading 3')
        elif line.startswith('## '):p=doc.add_paragraph(line[3:],style='Heading 2')
        else:
            p=doc.add_paragraph(line)
            if line.startswith(('Figure 4.','Table 4.')):
                p.paragraph_format.keep_with_next=line.startswith('Table')
                for r in p.runs:r.font.size=Pt(10)
        put(doc,anchor,p._p)

def main():
    before=digest(SOURCE)
    standalone=Document()
    style=standalone.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'),'宋体')
    standalone.sections[0].left_margin=Inches(.85);standalone.sections[0].right_margin=Inches(.85)
    render(standalone);out1=ROOT/'reports'/('4.5_正文_含图表'+SUFFIX+'.docx');standalone.save(out1)
    doc=Document(SOURCE)
    original_prefix=[p.text for p in doc.paragraphs[:57]]
    original_refs=[p.text for p in doc.paragraphs[58:]]
    target=next(p for p in doc.paragraphs if p.text.strip()=='4.5 实验')
    anchor=next(p._p for p in doc.paragraphs if p.text.strip()=='参考文献')
    target._p.getparent().remove(target._p)
    render(doc,anchor)
    out2=ROOT/'reports'/('第四部分_补入新4.5'+SUFFIX+'.docx');doc.save(out2)
    check=Document(out2)
    assert [p.text for p in check.paragraphs[:57]]==original_prefix
    pos=next(i for i,p in enumerate(check.paragraphs) if p.text.strip()=='参考文献')
    assert [p.text for p in check.paragraphs[pos:]]==original_refs
    assert sum(p.text.startswith('4.5.') for p in check.paragraphs)==5
    figure_count=7 if SUFFIX else 3
    assert len(check.inline_shapes)==len(Document(SOURCE).inline_shapes)+figure_count
    assert len(check.tables)==len(Document(SOURCE).tables)+3
    assert digest(SOURCE)==before
    result={'source':str(SOURCE),'source_sha256_before_and_after':before,'original_4_1_to_4_4_preserved':True,'references_preserved':True,'new_subsections':5,'inserted_figures':figure_count,'inserted_tables':3,'outputs':[str(out1),str(out2),str(MD)],'citation_policy':'existing manuscript [134] and [135] retained; no new external literature claims','figure_numbering':'4.2-4.4 and optional S1-S4; tables4.2-4.4'}
    (ROOT/'reports'/('4.5_交付核验'+SUFFIX+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(f'Verified: original unchanged, preceding text and references preserved, 5 subsections + {figure_count} figures + 3 tables.')
if __name__=='__main__':main()
