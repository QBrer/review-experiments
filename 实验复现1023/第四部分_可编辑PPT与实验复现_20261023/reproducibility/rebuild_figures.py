"""Rebuild the 10 computed figures from included data; preserve the supplied Fig4.1.
Uses the original plotting function bodies, with only input/output path adapters.
All outputs go into a new directory. No raw rasters are required for display maps.
"""
from pathlib import Path
import ast,datetime,uuid,types,shutil,json,os
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,Rectangle,FancyBboxPatch,FancyArrowPatch
from matplotlib.colors import ListedColormap,BoundaryNorm
from PIL import Image
R0=Path(__file__).resolve().parent;SNAP=R0/'snapshots';ART=R0.parent/'editable_figures'
R=R0/'runs'/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_figures_'+uuid.uuid4().hex[:6]);R.mkdir(parents=True)
F=R/'figures';D=R/'figure_data';P=R/'preview'
for p in [F,D,P,R/'source_data',R/'sampling_audit']:p.mkdir()
for p in (ART/'data').iterdir():shutil.copy2(p,D/p.name)
shutil.copy2(ART/'data/Fig4_2_sample_locations.csv',R/'sampling_audit/all_163_windows_roles.csv')
legend=pd.DataFrame({'code':range(1,15),'name':['Forest','Shrub','Meadow','Real steppe','Dry steppe','Desert steppe','Wetland','Water','Cropland','Built-up land','Barren land','Desert','Sand','Ice']});legend.to_csv(R/'source_data/Wang_product_legend_verified.csv',index=False)
for ext in ['png','pdf','svg','tif']:shutil.copy2(ART/'source_figures'/('Fig4_1.'+ext),F/('Fig4_1.'+ext))
mapping={};manifest=[]
def save(fig,name,sources):
 name=mapping.get(name,name)
 if name is None:plt.close(fig);return
 for ext in ['png','pdf','svg']:fig.savefig(F/(name+'.'+ext),dpi=600,bbox_inches='tight',pad_inches=.08)
 with Image.open(F/(name+'.png')) as im:im.convert('RGB').save(F/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 fig.savefig(P/(name+'.png'),dpi=140,bbox_inches='tight');plt.close(fig);manifest.append(dict(figure=name,sources=sources))
def record(row):pass
old=types.SimpleNamespace(DATA=D,FIG=F,ROOT=R);old.COL={'Low':'#377eb8','High':'#d55e00','fine6':'#377eb8','coarse3':'#d55e00','G':'#747474','GS':'#0072b2','GT':'#cc79a7','GST':'#009e73'}
env=dict(globals());env.update(OLD=SNAP/'mechanism',V4=SNAP/'v4',V5=SNAP/'v5',DATA=D,FIG=F,ROOT=R,COL=old.COL,old=old)
def load_functions(path,names):
 text=path.read_text(encoding='utf8');tree=ast.parse(text);selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
 assert len(selected)==len(names),(path,names)
 for node in selected:
  source=ast.get_source_segment(text,node)
  source=source.replace("B/'实验独立复核_20261021/只读基线副本'","SNAP/'mechanism'")
  exec(compile(source,str(path),'exec'),env)
def fonts(family):plt.rcParams.update({'font.family':family,'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'xtick.major.width':.7,'ytick.major.width':.7})
load_functions(SNAP/'manuscript_analysis/esr_section4_20261022/make_figures.py',['tag','grid','fig3','block_task','fig5','supplements']);old.tag=env['tag'];old.grid=env['grid']
fonts('Times New Roman');load_functions(SNAP/'manuscript_analysis/esr_section4_20261023_revision7/update_review_figures.py',['product_map','application']);env['product_map']();env['application']()
load_functions(SNAP/'manuscript_analysis/esr_section4_20261023_revision6/redraw_diagrams.py',['arrow','sampling']);env.update(RED='#d59794',INK='#263640',GRAY='#708087',LIGHT='#fcfafa');env['sampling']()
fonts('Arial');load_functions(SNAP/'manuscript_analysis/esr_section4_20261023/make_figures.py',['contributions','supports']);env['contributions']();env['supports']()
mapping.update(Fig4_3='Fig4_5',Fig4_5='Fig4_8');env['fig3']();env['fig5']();mapping.clear();mapping.update(FigS1=None,FigS2='FigS1',FigS3='FigS2',FigS4='FigS3');env['supplements']()
assert len(manifest)==10 and len(list(F.glob('*.png')))==11
(R/'plot_rebuild_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(R,flush=True)
