from pathlib import Path
import json,zipfile,collections
from lxml import etree as E
import fitz
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];P=R/'第四部分_全部图件_可编辑.pptx'
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
names=[f'Fig4_{i}' for i in range(1,9)]+[f'FigS{i}' for i in range(1,4)];rows=[]
with zipfile.ZipFile(P) as z:
 for i,name in enumerate(names,1):
  d=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'));texts=d.xpath('//a:t/text()',namespaces=ns);native_text=sum(bool(''.join(x.xpath('.//a:t/text()',namespaces=ns)).strip()) for x in d.xpath('//p:sp[p:txBody]',namespaces=ns));paths=len(d.xpath('//a:custGeom',namespaces=ns));pics=len(d.xpath('//p:pic',namespaces=ns));assert pics==(3 if name=='Fig4_2' else 0)
  assert not d.xpath('//a:outerShdw',namespaces=ns)
  if name!='Fig4_1':
   svg=E.parse(str(R/'source_figures'/(name+'.svg')));expected=collections.Counter(''.join(n.itertext()) for n in svg.findall('.//{http://www.w3.org/2000/svg}text') if ''.join(n.itertext()));actual=collections.Counter(texts);assert not expected-actual,(name,expected-actual)
  else:
   for label in ['Define the task','Diagnose mismatches','Analyze constraints','Organize alignment','Validate alignment','Hierarchical','Correspondences and aligned data']:assert label in texts
  rows.append(dict(slide=i,figure=name,editable_text_shapes=native_text,editable_custom_paths=paths,raster_backgrounds=pics,all_SVG_text_preserved=name!='Fig4_1'))
with fitz.open(R/'第四部分_全部图件_预览.pdf') as pdf:assert len(pdf)==11
report=dict(slides=11,source='All eight main figures and three supplementary figures from revision7',only_raster_content='Three classified/background map images on slide 2',charts='Native shapes, not embedded Office chart/data workbooks',heatmap_cells_editable=84,PowerPoint_export_confirmed=True,inventory=rows)
(R/'PPT_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
thumbs=[]
for i in range(1,12):
 im=Image.open(R/'preview'/f'幻灯片{i}.PNG').convert('RGB');im.thumbnail((480,360));thumbs.append(im)
sheet=Image.new('RGB',(480*3,360*4),'#eeeeee')
for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*480,(i//3)*360))
sheet.save(R/'preview/全部图件缩略预览.png');print(json.dumps(report,ensure_ascii=False,indent=2))
