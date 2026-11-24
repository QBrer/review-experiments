from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm,Pt
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

def me(name,*children):
 n=OxmlElement('m:'+name)
 for c in children:n.append(c)
 return n
def mr(text,plain=False):
 r=me('r')
 if plain:
  pr=me('rPr');s=me('sty');s.set(qn('m:val'),'p');pr.append(s);r.append(pr)
 t=me('t');t.text=text;t.set(qn('xml:space'),'preserve');r.append(t);return r
def sub(base,index):return me('sSub',me('e',mr(base)),me('sub',mr(index)))
def ssub(node,index):return me('sSub',me('e',node),me('sub',mr(index)))
def sup(base,exp):return me('sSup',me('e',mr(base)),me('sup',mr(exp)))
def star_u(index):return me('sSubSup',me('e',mr('u')),me('sub',mr(index)),me('sup',mr('*')))
def hat_u(index):
 pr=me('accPr');ch=me('chr');ch.set(qn('m:val'),'̂');pr.append(ch);return ssub(me('acc',pr,me('e',mr('u'))),index)
def frac(top,bottom):return me('f',me('num',*top),me('den',*bottom))
def sigma(index,body,upper=None):
 pr=me('naryPr');ch=me('chr');ch.set(qn('m:val'),'∑');pr.append(ch)
 if upper is None:hide=me('supHide');hide.set(qn('m:val'),'1');pr.append(hide)
 return me('nary',pr,me('sub',mr(index)),me('sup',mr(upper or '')),me('e',*body))
def display(d,kind,number=None):
 if kind=='entropy':
  body=[sub('H','SL'),mr(' = −'),sigma('i=1',[sub('u','i'),mr(' '),ssub(mr('log',True),'2'),mr(' '),sub('u','i')],'4'),mr(',    '),sub('u','i'),mr(' = '),frac([sub('A','i')],[sub('A','SL')])];number=number or '4-4'
 elif kind=='f1':
  body=[sub('F','1'),mr(' = '),frac([mr('2'),sub('TP','A')],[mr('2'),sub('TP','A'),mr(' + '),sub('FP','A'),mr(' + '),sub('FN','A')]),mr(',    L = 1 − '),sub('F','1')];number=number or '4-5'
 elif kind=='decomposition':
  body=[sub('c','U'),mr(' = '),frac([mr('100%')],[mr('n')]),sigma('w=1',[frac([sub('SS','w,U')],[sub('SS','w,total')])],'n')];number=number or '4-6'
 elif kind=='noncommutativity':
  body=[sub('R','NC'),mr(' = '),frac([sub('N','diff')],[sub('N','joint')])];number=number or '4-7'
 elif kind=='objective':
  body=[mr('J = '),sigma('t',[sub('s','t'),mr('('),sub('u','t'),mr(')')]),mr(' − '),frac([mr('γ')],[mr('24')]),sigma('t',[mr('‖'),sub('u','t'),sub('‖','1')]),mr(' − '),sub('I','T'),frac([mr('λ')],[mr('12')]),mr('‖'),sub('u','2020'),mr(' − '),sub('u','2010'),sub('‖','1')];number=number or '4-8'
 elif kind=='residual':
  body=[mr('E = '),frac([mr('1')],[mr('2')]),sigma('t∈{2010,2020}',[mr('‖'),hat_u('t'),mr(' − '),star_u('t'),sub('‖','2')])];number=number or '4-9'
 elif kind=='injection':
  pr=me('accPr');ch=me('chr');ch.set(qn('m:val'),'̃');pr.append(ch);w=ssub(me('acc',pr,me('e',mr('W'))),'t')
  body=[w,mr('(r,c) = '),sub('W','t'),mr('(r + '),sub('d','r,t'),mr(', c + '),sub('d','c,t'),mr('),    '),star_u('t'),mr(' = −'),sub('d','t')];number=number or 'S1'
 else:raise ValueError(kind)
 # A borderless layout row keeps a genuine display equation centered while the
 # number remains ordinary, right-aligned Word text. Inline math shrinks fractions.
 table=d.add_table(rows=1,cols=3);table.autofit=False
 for col,width in zip(table.columns,[1.4,14.2,1.4]):col.width=Cm(width)
 for cell,width in zip(table.rows[0].cells,[1.4,14.2,1.4]):cell.width=Cm(width)
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','bottom','left','right','insideH','insideV']:
  n=OxmlElement('w:'+edge);n.set(qn('w:val'),'nil');borders.append(n)
 table._tbl.tblPr.append(borders)
 margins=OxmlElement('w:tblCellMar')
 for edge in ['top','bottom','left','right']:
  n=OxmlElement('w:'+edge);n.set(qn('w:w'),'0');n.set(qn('w:type'),'dxa');margins.append(n)
 table._tbl.tblPr.append(margins)
 no_split=OxmlElement('w:cantSplit');table.rows[0]._tr.get_or_add_trPr().append(no_split)
 for cell in table.rows[0].cells:
  cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
  p=cell.paragraphs[0];pf=p.paragraph_format;pf.first_line_indent=0;pf.space_before=Pt(6);pf.space_after=Pt(6);pf.line_spacing=1.15;pf.keep_with_next=True
 p=table.cell(0,1).paragraphs[0];p.alignment=1;p._p.append(me('oMathPara',me('oMath',*body)))
 numberp=table.cell(0,2).paragraphs[0];numberp.alignment=2;numberp.add_run('('+number+')')
 return p
