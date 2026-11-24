"""Convert Matplotlib SVG primitives to native PowerPoint paths and text boxes.
Raster land-cover backgrounds remain pictures. Heat-map cells are rebuilt as shapes.
The supplied Figure 4.1 is rebuilt manually from the user's reference image.
"""
from pathlib import Path
import re,math,io,base64,json
import numpy as np
from lxml import etree as E
from PIL import Image,ImageFont
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.oxml.xmlchemy import OxmlElement
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR

R=Path(__file__).resolve().parents[1];SRC=R/'source_figures';OUT=R/'第四部分_全部图件_可编辑.pptx'
NS='http://www.w3.org/2000/svg';XL='{http://www.w3.org/1999/xlink}href'
prs=Presentation();prs.slide_width=Inches(13.333333);prs.slide_height=Inches(10)
stats=[];warnings=[]
def el(tag,**attrs):
 n=OxmlElement(tag)
 for k,v in attrs.items():n.set(k,str(v))
 return n
def color(s):
 if s=='white':s='#ffffff'
 if s=='black':s='#000000'
 if len(s)==4 and s[0]=='#':s='#'+''.join(c*2 for c in s[1:])
 return s.lstrip('#').upper()
def fill_xml(parent,key,c,alpha=1):
 n=el('a:'+key)
 if c=='none':n=el('a:noFill')
 else:
  node=el('a:srgbClr',val=color(c))
  if alpha<1:node.append(el('a:alpha',val=round(alpha*100000)))
  n.append(node)
 parent.append(n)
def parse_style(s):return dict(x.split(':',1) for x in (t.strip() for t in s.split(';')) if ':' in x)
def style(node,inherited):
 st=inherited.copy();st.update({k.strip():v.strip() for k,v in parse_style(node.get('style','')).items()})
 for k in ['fill','stroke','opacity','fill-opacity','stroke-opacity','stroke-width','stroke-dasharray','font-size','font-family','text-anchor']:
  if k in node.attrib:st[k]=node.get(k)
 return st
def matrix(s):
 out=np.eye(3)
 for typ,nums in re.findall(r'(\w+)\s*\(([^)]*)\)',s):
  v=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',nums)));m=np.eye(3)
  if typ=='translate':m[0,2]=v[0];m[1,2]=v[1] if len(v)>1 else 0
  elif typ=='scale':m[0,0]=v[0];m[1,1]=v[1] if len(v)>1 else v[0]
  elif typ=='rotate':
   a=math.radians(v[0]);m[:2,:2]=[[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]
   if len(v)==3:
    t=np.eye(3);t[:2,2]=v[1:];u=np.eye(3);u[:2,2]=-np.array(v[1:]);m=t@m@u
  elif typ=='matrix':m=np.array([[v[0],v[2],v[4]],[v[1],v[3],v[5]],[0,0,1]])
  else:raise ValueError(typ)
  out=out@m
 return out
def path_commands(d):
 tok=re.findall(r'[MLCQZmlcqz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',d);out=[];i=0;cmd=None;cur=np.zeros(2);start=cur.copy()
 while i<len(tok):
  if tok[i].isalpha():cmd=tok[i];i+=1
  kind=cmd.upper()
  if kind=='Z':out.append(('Z',[]));cur=start.copy();cmd=None;continue
  n={'M':2,'L':2,'C':6,'Q':4}[kind];v=np.array(list(map(float,tok[i:i+n]))).reshape(-1,2);i+=n
  if cmd.islower():v+=cur
  cur=v[-1].copy()
  if kind=='M':start=cur.copy();cmd='l' if cmd.islower() else 'L'
  out.append((kind,v))
 return out

class Converter:
 def __init__(self,slide,name):
  self.slide=slide;self.name=name;self.root=E.parse(str(SRC/(name+'.svg'))).getroot();self.defs={x.get('id'):x for x in self.root.iter() if x.get('id')};vb=list(map(float,self.root.get('viewBox').split()))
  self.scale=min(12.6*72/vb[2],8.95*72/vb[3]);self.ox=(13.333333*72-self.scale*vb[2])/2;self.oy=.70*72+(8.95*72-self.scale*vb[3])/2
  self.rootm=np.array([[self.scale,0,self.ox],[0,self.scale,self.oy],[0,0,1]])
  self.count={'paths':0,'texts':0,'raster_backgrounds':0,'editable_heatmap_cells':0}
 def path(self,commands,M,st,name='Vector element'):
  transformed=[];allp=[]
  for cmd,pts in commands:
   if len(pts):
    points=np.array([M@np.array([x,y,1]) for x,y in pts])[:,:2];allp.extend(points)
   else:points=[]
   transformed.append((cmd,points))
  if not allp:return
  a=np.array(allp);lo=a.min(0);hi=a.max(0);w,h=np.maximum(hi-lo,.001)
  shape=self.slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Pt(lo[0]),Pt(lo[1]),Pt(w),Pt(h));shape.name=name
  sp=shape._element.spPr
  for node in list(sp):
   if E.QName(node).localname!='xfrm':sp.remove(node)
  geom=el('a:custGeom')
  for tag in ['avLst','gdLst','ahLst','cxnLst']:geom.append(el('a:'+tag))
  geom.append(el('a:rect',l='0',t='0',r='r',b='b'));lst=el('a:pathLst');pp=el('a:path',w=round(w*12700),h=round(h*12700),fill='norm' if st.get('fill','#000000')!='none' else 'none',stroke='1' if st.get('stroke','none')!='none' else '0')
  for cmd,pts in transformed:
   nn=el({'M':'a:moveTo','L':'a:lnTo','C':'a:cubicBezTo','Q':'a:quadBezTo','Z':'a:close'}[cmd])
   for x,y in pts:nn.append(el('a:pt',x=round((x-lo[0])*12700),y=round((y-lo[1])*12700)))
   pp.append(nn)
  lst.append(pp);geom.append(lst);sp.append(geom)
  op=float(st.get('opacity',1));fill_xml(sp,'solidFill',st.get('fill','#000000'),op*float(st.get('fill-opacity',1)))
  stroke=st.get('stroke','none');width=float(st.get('stroke-width',1))*np.linalg.norm(M[:2,0]);ln=el('a:ln',w=max(1,round(width*12700)),cap='rnd' if st.get('stroke-linecap')=='round' else 'flat')
  fill_xml(ln,'solidFill',stroke,op*float(st.get('stroke-opacity',1)))
  if st.get('stroke-dasharray') not in [None,'none']:
   dash=el('a:custDash');v=[float(x) for x in re.split('[ ,]+',st['stroke-dasharray']) if x];v=v if len(v)%2==0 else v*2
   sw=float(st.get('stroke-width',1))
   for j in range(0,len(v),2):dash.append(el('a:ds',d=max(1,round(v[j]/sw*100000)),sp=max(1,round(v[j+1]/sw*100000))))
   ln.append(dash)
  ln.append(el('a:round'));sp.append(ln);self.count['paths']+=1
 def text(self,node,M,st):
  value=''.join(node.itertext());raw=st.get('font','');fs=float(re.search(r'([\d.]+)px',raw).group(1)) if 'px' in raw else float(st.get('font-size',9));font='Times New Roman' if 'Times New Roman' in raw else 'Arial';bold='700' in raw or 'bold' in raw;italic='italic' in raw
  fn=('times' if font=='Times New Roman' else 'arial')+('bi' if bold and italic else 'bd' if bold else 'i' if italic else '')+'.ttf'
  if font=='Times New Roman' and bold:fn='timesbi.ttf' if italic else 'timesbd.ttf'
  try:pil=ImageFont.truetype('C:/Windows/Fonts/'+fn,round(fs*100));width=pil.getlength(value)/100
  except Exception:width=len(value)*fs*.55
  x=float(node.get('x',0));y=float(node.get('y',0));anchor=st.get('text-anchor','start');w=width+fs*.45;h=fs*1.25
  left=x-(width/2 if anchor=='middle' else width if anchor=='end' else 0);top=y-fs*(.91 if font=='Arial' else .89)
  center=M@np.array([left+w/2,top+h/2,1]);scale=np.linalg.norm(M[:2,0]);w*=scale;h*=scale
  sh=self.slide.shapes.add_textbox(Pt(center[0]-w/2),Pt(center[1]-h/2),Pt(w),Pt(h));sh.name='Text: '+value[:60];sh.rotation=math.degrees(math.atan2(M[1,0],M[0,0]))%360
  tf=sh.text_frame;tf.clear();tf.word_wrap=False;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0;tf.vertical_anchor=MSO_ANCHOR.TOP
  pp=tf.paragraphs[0];pp.space_before=Pt(0);pp.space_after=Pt(0);pp.line_spacing=1.0;run=pp.add_run();run.text=value;run.font.name=font;run.font.size=Pt(fs*scale);run.font.bold=bold;run.font.italic=italic;run.font.color.rgb=RGBColor.from_string(color(st.get('fill','#000000')))
  self.count['texts']+=1
 def image(self,node,M,st):
  x,y,w,h=[float(node.get(k,0)) for k in ['x','y','width','height']];raw=base64.b64decode(node.get(XL).split(',',1)[1]);im=Image.open(io.BytesIO(raw))
  if self.name=='FigS1':
   # The original imshow layer is a 3 by 4 matrix. Rebuild cells, not a picture.
   rgb=im.convert('RGB')
   for row in range(3):
    for col in range(4):
     c=rgb.getpixel((round((col+.5)*rgb.width/4),round((row+.5)*rgb.height/3)));xx=x+col*w/4;yy=y+row*h/3
     pts=np.array([[xx,yy],[xx+w/4,yy],[xx+w/4,yy+h/3],[xx,yy+h/3]])
     self.path([('M',pts[:1]),('L',pts[1:2]),('L',pts[2:3]),('L',pts[3:]),('Z',[])],M,{'fill':'#%02x%02x%02x'%c,'stroke':'none'},f'Editable heatmap cell {row+1},{col+1}');self.count['editable_heatmap_cells']+=1
  else:
   corners=np.array([M@np.array([xx,yy,1]) for xx,yy in [(x,y),(x+w,y+h)]]);lo=corners[:,:2].min(0);hi=corners[:,:2].max(0)
   sh=self.slide.shapes.add_picture(io.BytesIO(raw),Pt(lo[0]),Pt(lo[1]),Pt(hi[0]-lo[0]),Pt(hi[1]-lo[1]));sh.name='Raster land-cover background';xf=sh._element.spPr.xfrm
   if M[0,0]<0:xf.set('flipH','1')
   if M[1,1]<0:xf.set('flipV','1')
   self.count['raster_backgrounds']+=1
 def visit(self,node,M,st,from_use=False):
  tag=E.QName(node).localname
  if tag in ['defs','metadata','style','clipPath'] and not from_use:return
  M=M@matrix(node.get('transform',''));st=style(node,st)
  if tag=='use':
   target=self.defs[node.get(XL).lstrip('#')];T=np.eye(3);T[:2,2]=[float(node.get('x',0)),float(node.get('y',0))];self.visit(target,M@T,st,True)
  elif tag=='path':self.path(path_commands(node.get('d','')),M,st)
  elif tag=='text':self.text(node,M,st)
  elif tag=='image':self.image(node,M,st)
  else:
   for child in node:
    if isinstance(child.tag,str):self.visit(child,M,st)
 def render(self):self.visit(self.root,self.rootm,{'fill':'#000000','stroke':'none'});return self.count

def basic_text(slide,x,y,w,h,text,size=16,bold=False,color0='#17232d',font='Arial',italic=False,align=None):
 sh=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0;tf.word_wrap=False
 for i,line in enumerate(text.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_after=Pt(0);p.line_spacing=1.05
  if align is not None:p.alignment=align
  r=p.add_run();r.text=line;r.font.name=font;r.font.size=Pt(size);r.font.bold=bold;r.font.italic=italic;r.font.color.rgb=RGBColor.from_string(color(color0))
 return sh
def original_framework(slide):
 # Coordinates traced in the supplied 987 x 609 reference, keeping its exact wording.
 scale=min(12.6/987,8.95/609);ox=(13.333333-987*scale)/2;oy=.70+(8.95-609*scale)/2
 def txt(x,y,w,text,size=16,bold=False,c='#17232d',italic=False):return basic_text(slide,ox+x*scale,oy+y*scale,w*scale,52*scale,text,size*scale*72,bold,c,italic=italic)
 def line(x1,y1,x2,y2,arrow=False,dash=False,c='#28557a',width=.8):
  sh=slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(ox+x1*scale),Inches(oy+y1*scale),Inches(ox+x2*scale),Inches(oy+y2*scale));sh.line.color.rgb=RGBColor.from_string(color(c));sh.line.width=Pt(width*scale*72)
  ln=sh._element.spPr.get_or_add_ln()
  if arrow:ln.append(el('a:tailEnd',type='triangle',w='sm',len='sm'))
  if dash:ln.append(el('a:prstDash',val='dash'))
  return sh
 from pptx.enum.text import PP_ALIGN
 gray='#a7afb7';muted='#586471'
 txt(32,4,40,'01',20,True,gray);txt(73,4,400,'Define the task',20,True);txt(73,45,600,'Objects · Intended use · Acceptance criteria',16,c=muted)
 for yy in [80,453,525]:line(33,yy,955,yy,c='#69747d',width=.6)
 line(79,81,79,112,True)
 for x,n,title in [(32,'02','Diagnose mismatches'),(341,'03','Analyze constraints'),(669,'04','Organize alignment')]:txt(x,128,40,n,20,True,gray);txt(x+42,128,300,title,20,True)
 for y,title,sub in [(188,'Spatial','Position · geometry · topology'),(247,'Temporal','Time · process stage'),(306,'Semantic','Concepts · classes')]:txt(56,y,220,title,18,True);txt(56,y+27,240,sub,14,c=muted)
 centers=[(475,207,'Spatial'),(402,311,'Temporal'),(548,311,'Semantic')]
 for x,y,lab in centers:
  sh=slide.shapes.add_shape(MSO_SHAPE.OVAL,Inches(ox+(x-27)*scale),Inches(oy+(y-27)*scale),Inches(54*scale),Inches(54*scale));sh.fill.solid();sh.fill.fore_color.rgb=RGBColor(255,255,255);sh.line.color.rgb=RGBColor.from_string('26333F');sh.line.width=Pt(scale*72*1.15)
  basic_text(slide,ox+(x-26)*scale,oy+(y-7)*scale,52*scale,20*scale,lab,10*scale*72,True,align=PP_ALIGN.CENTER)
 for pts in [(458,231,420,285),(492,231,530,285),(432,311,519,311)]:
  sh=line(*pts,arrow=True);sh._element.spPr.get_or_add_ln().append(el('a:headEnd',type='triangle',w='sm',len='sm'))
 txt(447,264,100,'Coupling',14);txt(398,357,200,'Dependencies · Conflicts',14,c=muted);txt(427,376,140,'Operation order',14,c=muted)
 for y,title,sub in [(187,'Sequential','Dependencies'),(229,'Iterative','Feedback'),(271,'Joint','Shared constraints'),(313,'Hierarchical','Nested levels')]:txt(686,y,130,title,16,True);txt(809,y,160,sub,14,c=muted)
 txt(686,373,280,'Strategies may be combined',14,c=muted,italic=True)
 line(282,254,325,254,True);line(609,254,651,254,True);line(919,400,919,449,True)
 txt(56,414,390,'If criteria are not met: revise constraints or strategy',13,c='#28557a',italic=True)
 line(855,453,855,419,dash=True);line(855,419,475,419,dash=True);line(475,419,475,399,True,True);line(753,419,753,399,True,True)
 txt(32,474,40,'05',20,True,gray);txt(74,474,250,'Validate alignment',20,True)
 txt(328,473,190,'Correspondence\nvalidity',14);txt(527,473,190,'Cross-dimensional\nconsistency',14);txt(733,473,200,'Task-specific\nfitness for use',14)
 line(494,526,494,549,True);txt(325,560,500,'Correspondences and aligned data',20,True);txt(299,591,650,'Validity conditions · Partial / unmatched cases · Residual uncertainty',13,c=muted)
 return {'texts':sum(s.has_text_frame for s in slide.shapes),'paths':sum(not s.has_text_frame for s in slide.shapes),'raster_backgrounds':0,'manual_reconstruction':True}

titles={'Fig4_1':'整合框架','Fig4_2':'研究产品与样区','Fig4_3':'样区选取与组成','Fig4_4':'响应贡献与交互','Fig4_5':'变化位置损失','Fig4_6':'支持域与相位','Fig4_7':'跨产品应用流程','Fig4_8':'框架效果与约束增量','FigS1':'共同参数敏感性','FigS2':'分情景结果','FigS3':'先行策略选择'}
for name,title in titles.items():
 slide=prs.slides.add_slide(prs.slide_layouts[6]);basic_text(slide,.30,.16,12.6,.32,name.replace('_','.')+'  '+title,size=15,bold=True,font='Microsoft YaHei',color0='#5b6570')
 before=len(slide.shapes);counts=original_framework(slide) if name=='Fig4_1' else Converter(slide,name).render()
 body=list(slide.shapes)[before:];group=slide.shapes.add_group_shape(body);group.name=name+' editable artwork (ungroup to edit individual objects)'
 slide.notes_slide.notes_text_frame.text=f'{name}: source from revision7. Native PowerPoint text and custom vector shapes. Ungroup artwork to edit. Data tables are included in editable_figures/data. Raster land-cover backgrounds remain pictures; FigS1 heat-map cells rebuilt as shapes. Figure 4.1 manually reconstructed from supplied image.'
 stats.append(dict(figure=name,slide=len(prs.slides),**counts));print(name,counts,flush=True)
 # Remove theme shape effects so Office cannot add default shadows to the paths.
for slide in prs.slides:
 for node in slide._element.xpath('.//p:sp | .//p:cxnSp | .//p:pic'):
  for st in list(node):
   if E.QName(st).localname=='style':node.remove(st)
  for sp in node.findall('{http://schemas.openxmlformats.org/presentationml/2006/main}spPr'):
   for ef in list(sp):
    if E.QName(ef).localname in ['effectLst','effectDag']:sp.remove(ef)
   sp.append(el('a:effectLst'))
prs.save(OUT);(R/'editability_inventory.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8');print(OUT)
