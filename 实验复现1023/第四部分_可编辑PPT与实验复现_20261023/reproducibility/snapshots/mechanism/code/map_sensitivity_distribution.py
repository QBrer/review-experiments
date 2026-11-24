"""Map existing sensitivity candidates and selected regions, without extrapolation."""
from core import *
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle,Patch
from matplotlib.lines import Line2D
from matplotlib.collections import PatchCollection
from matplotlib.colors import ListedColormap
from rasterio.enums import Resampling

OUT=ROOT/'figures/sensitivity_definition'
def main():
    paths=[ROOT/'selection/candidates.csv',ROOT/'selection/thresholds.json',ROOT/'selection/selected_regions.csv']
    before={str(p):sha(p) for p in paths}
    candidates=pd.read_csv(paths[0]);q=load(paths[1]);selected=pd.read_csv(ROOT/'results/region_walkthrough_24/region_index.csv')
    e=candidates[candidates.reason=='eligible'].copy()
    e['stratum']=np.where(e.H_SL<=q['Q25'],'Low',np.where(e.H_SL>=q['Q75'],'High','Middle'))
    assert e.stratum.value_counts().to_dict()=={'Middle':356,'Low':179,'High':179}
    fontfile=Path('C:/Windows/Fonts/msyh.ttc')
    if fontfile.exists():font_manager.fontManager.addfont(str(fontfile));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(fontfile)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':11,'pdf.fonttype':42,'svg.fonttype':'none'})
    h=next(BASE.glob('A multi*/MPSDSL'))/'2020.tif'
    w=next(BASE.glob('Long-term*/MON_LULC'))/'2020.tif'
    with rasterio.open(h) as src:tr=src.transform
    with rasterio.open(w) as src:
        width=2400;height=round(width*src.height/src.width);a=src.read(1,out_shape=(height,width),resampling=Resampling.nearest);bounds=src.bounds
    coverage=(a>=1)&(a<=14)
    features=[]
    for r in e.itertuples():
        xy=[tr*(r.col,r.row),tr*(r.col+1200,r.row),tr*(r.col+1200,r.row+1200),tr*(r.col,r.row+1200),tr*(r.col,r.row)]
        features.append(dict(type='Feature',properties=dict(id=r.id,stratum=r.stratum,H_SL=r.H_SL,selected=r.id in set(selected.id)),geometry=dict(type='Polygon',coordinates=[xy])))
    dump(OUT/'敏感性分区候选窗口.geojson',dict(type='FeatureCollection',features=features))
    for lang in ['中文','English']:
        cn=lang=='中文';fig,ax=plt.subplots(figsize=(15,8.7),constrained_layout=True)
        ax.imshow(coverage.astype(np.uint8),extent=[bounds.left,bounds.right,bounds.bottom,bounds.top],origin='upper',cmap=ListedColormap(['white','#edf0ed']),vmin=0,vmax=1,interpolation='nearest',zorder=0)
        colors={'Middle':'#c6cbc8','Low':'#277bb6','High':'#d95336'}
        for group in ['Middle','Low','High']:
            patches=[]
            for r in e[e.stratum==group].itertuples():
                x0,y0=tr*(r.col,r.row);x1,y1=tr*(r.col+1200,r.row+1200);patches.append(Rectangle((x0,y1),x1-x0,y0-y1))
            ax.add_collection(PatchCollection(patches,facecolor=colors[group],edgecolor='white',linewidth=.22,alpha=.9,zorder=2))
        for r in selected.itertuples():
            ax.scatter(r.lon,r.lat,marker='o',s=42,facecolors='none',edgecolors='#202b35',linewidths=1.05,zorder=4)
            ax.annotate(r.display_id,(r.lon,r.lat),xytext=(5,5),textcoords='offset points',fontsize=8.5,color='#172a3a',zorder=5,
                bbox=dict(boxstyle='round,pad=.1',fc='white',ec='none',alpha=.80))
        ax.set(xlim=(87.5,126.5),ylim=(37.1,53.9),xlabel='经度（°E）' if cn else 'Longitude (°E)',ylabel='纬度（°N）' if cn else 'Latitude (°N)',title='蒙古高原研究覆盖区内的高、低敏感候选区域与实验样区' if cn else 'Sensitivity strata and experimental windows in the Mongolian Plateau study coverage')
        ax.set_aspect(1/np.cos(np.deg2rad(45)),adjustable='box');ax.grid(alpha=.18,zorder=1);ax.set_axisbelow(True)
        labels=[f'低敏感候选：179窗（H_SL ≤ {q["Q25"]:.6f}）',f'高敏感候选：179窗（H_SL ≥ {q["Q75"]:.6f}）','中间组：356窗（不进入两端比较）','已选样区：Low 12窗 + High 12窗','产品有效覆盖（示意背景）'] if cn else [f'Low:179 candidates (H_SL ≤ {q["Q25"]:.6f})',f'High:179 candidates (H_SL ≥ {q["Q75"]:.6f})','Middle:356 candidates (not sampled)','Selected:12 Low + 12 High windows','Product coverage (context)']
        handles=[Patch(facecolor=colors['Low'],label=labels[0]),Patch(facecolor=colors['High'],label=labels[1]),Patch(facecolor=colors['Middle'],label=labels[2]),Line2D([],[],marker='o',color='none',markeredgecolor='#202b35',markerfacecolor='none',label=labels[3]),Patch(facecolor='#edf0ed',label=labels[4])]
        ax.legend(handles=handles,loc='upper left',framealpha=.97,fontsize=9)
        ax.annotate('N',xy=(.966,.91),xytext=(.966,.78),xycoords='axes fraction',ha='center',fontsize=13,arrowprops=dict(arrowstyle='-|>',lw=1.6,color='#263748'))
        caption=('分组依据：2020年SL内部四细类的面积加权条件熵；矩形为真实1200×1200像元候选窗口。\n仅对符合筛选条件的窗口分组，其他位置不推定敏感等级；浅灰背景为产品覆盖，不是自然地理边界。' if cn else 'Strata use area-weighted within-SL entropy in2020; rectangles show actual1200×1200-pixel candidate windows.\nOnly eligible candidates are classified. The light background represents product coverage, not a physiographic boundary.')
        fig.text(.5,.005,caption,ha='center',va='bottom',fontsize=9,color='#485660');fig.get_layout_engine().set(rect=(0,.065,1,1))
        name='高低敏感区空间分布图_'+lang
        for ext in ['png','pdf','svg']:fig.savefig(OUT/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    (OUT/'高低敏感区分布图_图注.md').write_text('''# 高低敏感区空间分布图

建议置于4.5.1的分组规则说明之后，与熵阈值和组成图相邻。

中文图注：蒙古高原研究覆盖区内高、低敏感候选区域与实验样区的空间分布。蓝色和橙红色矩形分别表示按SL内部条件熵下、上四分位数识别的179个低敏感和179个高敏感候选窗口，灰色矩形表示356个中间组窗口。黑色圆圈标出最终选取的24个实验窗口，H01—H12、L01—L12按组内抽取顺序编号。每个矩形对应1200×1200个原始像元，浅灰背景为Wang2020有效产品覆盖。未通过候选筛选的位置没有赋予敏感性等级。

English caption: Spatial distribution of sensitivity strata and selected experimental windows within the Mongolian Plateau study coverage. Blue and orange-red rectangles denote179 low- and179 high-sensitivity candidates, defined by the lower and upper quartiles of within-SL entropy. Gray rectangles indicate356 middle-stratum windows. Black circles mark the24 selected experimental windows. Each rectangle represents1200×1200 native pixels; the pale background depicts valid Wang2020 product coverage. Locations outside the eligible candidate pool are not assigned a sensitivity class.

数据来源为已冻结候选池、阈值和样区名单；没有重新计算阈值、移动窗口或扩大分组至整片连续区域。产品背景仅作显示降采样。SVG中窗口轮廓、标记和文本为矢量元素，产品背景为嵌入栅格。
''',encoding='utf8')
    assert all(sha(p)==h for p,h in before.items())
    dump(OUT/'distribution_map_provenance.json',dict(time=now(),protected_sha256=before,counts={'Low':179,'High':179,'Middle':356,'selected':24},product_background=str(w),background_is_geographical_boundary=False,unsampled_excluded_locations_not_classified=True,source_data_unchanged=True))
    print('Distribution maps created in Chinese and English: PNG/PDF/SVG plus GeoJSON and captions.')
if __name__=='__main__':main()
