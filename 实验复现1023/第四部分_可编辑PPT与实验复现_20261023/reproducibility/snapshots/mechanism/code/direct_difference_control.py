"""Same-input control for current task walkthrough; not a cross-product experiment."""
from core import *
from framework_walkthrough import tif
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.backends.backend_pdf import PdfPages

OUT=ROOT/'results/direct_difference_control'
FIG=ROOT/'figures/direct_difference_control'
def main():
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    reference=ROOT/'results/region_walkthrough_24';sel=pd.read_csv(reference/'region_index.csv')
    ds=open_inputs();off=offsets(ds)
    dump(OUT/'design.json',dict(time=now(),authorization='User correction: control must match experimental group',inputs=['Han2010','Han2020'],scope='same24 regions and five-input valid mask as current walkthrough',raw_difference='int16(Han2020)-int16(Han2010); diagnostic of original categorical-code changes',task_control='int8(isSL2020)-int8(isSL2010), isSL=original code in21..24',experimental_reference='saved region_walkthrough_24 native SL directional change',no_changes_to_framework=True,no_new_p_values=True))
    rows=[]
    with PdfPages(FIG/'24样区_直接差分与框架结果对照.pdf') as book:
        for s in sel.to_dict('records'):
            label=s['display_id'];raw,v=read_window(ds,off,int(s['row']),int(s['col']),1200);tr=ds['H2020'].window_transform(Window(s['col'],s['row'],1200,1200));w=weights(tr,1200)
            with rasterio.open(reference/'rasters'/label/'common_valid.tif') as d:assert np.array_equal(v,d.read(1).astype(bool))
            with rasterio.open(reference/'rasters'/label/'SL_directional_change_2010_2020.tif') as d:framework=d.read(1)
            delta=raw['H2020'].astype(np.int16)-raw['H2010'].astype(np.int16)
            sl0=np.isin(raw['H2010'],[21,22,23,24]);sl1=np.isin(raw['H2020'],[21,22,23,24]);taskdelta=sl1.astype(np.int16)-sl0.astype(np.int16)
            control=np.full(v.shape,255,np.uint8);control[v]=0;control[v&(taskdelta==1)]=1;control[v&(taskdelta==-1)]=2
            exact_difference=v&(control!=framework);raw_changed=v&(delta!=0);SL_changed=v&(taskdelta!=0)
            extra=raw_changed&~SL_changed;miss=SL_changed&~raw_changed
            internal=extra&sl0&sl1;other=extra&~sl0&~sl1
            assert not miss.any() and np.array_equal(extra,internal|other)
            rdir=OUT/'rasters'/label;rdir.mkdir(parents=True,exist_ok=True)
            delta[~v]=-32768;taskdelta[~v]=-32768
            tif(rdir/'raw_code_difference.tif',delta,tr,-32768);tif(rdir/'SL_membership_difference.tif',taskdelta,tr,-32768)
            tif(rdir/'direct_SL_change.tif',control,tr,255)
            z=np.full(v.shape,255,np.uint8);z[v]=exact_difference[v];tif(rdir/'control_framework_disagreement.tif',z,tr,255)
            z=np.full(v.shape,255,np.uint8);z[v]=(raw_changed!=SL_changed)[v];tif(rdir/'raw_change_SL_change_difference.tif',z,tr,255)
            row=dict(display_id=label,site=s['id'],group=s['group'],valid_pixels=int(v.sum()),domain_km2=area(v,w)/1e6,raw_code_changed_km2=area(raw_changed,w)/1e6,SL_changed_km2=area(SL_changed,w)/1e6,raw_extra_non_SL_change_km2=area(extra,w)/1e6,SL_subtype_change_km2=area(internal,w)/1e6,non_SL_internal_change_km2=area(other,w)/1e6,raw_missed_SL_change_km2=area(miss,w)/1e6,SL_control_framework_disagreement_pixels=int(exact_difference.sum()),SL_control_framework_disagreement_km2=area(exact_difference,w)/1e6,expansion_km2=area(v&(taskdelta==1),w)/1e6,contraction_km2=area(v&(taskdelta==-1),w)/1e6)
            rows.append(row)
            fig,axes=plt.subplots(2,3,figsize=(12,8),constrained_layout=True)
            def draw(ax,z,title,colors,maximum):
                ax.imshow(z,cmap=ListedColormap(colors),vmin=-.5,vmax=maximum+.5,extent=[0,1200,1200,0],interpolation='nearest');ax.set(title=title,xlabel='Native column',ylabel='Native row')
            direct_show=control.copy();direct_show[direct_show==255]=3;frame_show=framework.copy();frame_show[frame_show==255]=3
            diff_show=np.where(v,exact_difference.astype(np.uint8),2)
            draw(axes[0,0],direct_show,'(a) Direct SL-membership subtraction',['#efefea','#25849b','#bd4b57','white'],3)
            draw(axes[0,1],frame_show,'(b) Framework SL change',['#efefea','#25849b','#bd4b57','white'],3)
            draw(axes[0,2],diff_show,f'(c) Disagreement: {exact_difference.sum()} pixels',['#efefea','#df2438','#555555'],2)
            draw(axes[1,0],np.where(v,raw_changed,2),'(d) Any raw class-code change',['#efefea','#578d82','white'],2)
            draw(axes[1,1],np.where(v,SL_changed,2),'(e) SL-membership change',['#efefea','#578d82','white'],2)
            draw(axes[1,2],np.where(v,extra,2),'(f) Different event definitions',['#efefea','#df2438','#555555'],2)
            fig.legend(handles=[Patch(color=c,label=t) for c,t in [('#25849b','SL expansion'),('#bd4b57','SL contraction'),('#578d82','Changed'),('#df2438','Difference')]],loc='outside lower center',ncol=4)
            fig.suptitle(f'{label} | same Han2010/2020 input, extent and valid mask',fontsize=13)
            for ext in ['png','pdf']:fig.savefig(FIG/f'{label}_direct_subtraction_control.{ext}',dpi=210,bbox_inches='tight')
            book.savefig(fig,bbox_inches='tight');plt.close(fig)
            print('Direct-difference control: '+label,flush=True)
    for d in ds.values():d.close()
    write_csv(OUT/'all_regions.csv',rows)
    d=pd.DataFrame(rows);summary=d.groupby('group').mean(numeric_only=True).reset_index();write_csv(OUT/'group_means.csv',summary.to_dict('records'))
    from report_results import texttable
    report=f'''# 同输入像元差分对照

对照使用与当前框架运行示例一致的Han2010和Han2020、24个样区及共同有效mask。Wang仅保留在原mask构建中，不替换任一时期的任务影像。

## 对照定义

1. 原始码差分：d_raw=code2020−code2010，使用有符号int16避免uint8下溢。d_raw≠0仅表示类别编码变化，不能用正负判断SL扩张/收缩。
2. 同任务直接差分：先按输入类别定义识别SL成员（21—24），再d_SL=I_SL2020−I_SL2010；+1扩张、−1收缩、0成员关系未变。
3. 实验组使用已保存的框架native SL方向变化图，未为这次对照重新选择处理规则。

## 结果

{texttable(summary,['group','raw_code_changed_km2','SL_changed_km2','raw_extra_non_SL_change_km2','SL_control_framework_disagreement_pixels'])}

同任务直接差分与框架方向结果在全部24窗逐像元一致（差异总数={int(d.SL_control_framework_disagreement_pixels.sum())}）。这是对已完成空间对应和目标语义定义的输入执行同一SL判断的结果，不能作为方法优劣的统计证据。

原始码变化图则还包括SL子类转换及非SL内部转换。它与SL变化图的红色差异表达任务定义不同，不作为框架纠正了真实分类错误的证据。图上排为同任务对照与红色差异；下排帮助解释原始码差分与目标成员差分的区别。

每组表值为12窗面积均值（km²），不是面积百分比。完整值、原始差值与掩膜GeoTIFF均保存。未开展新的显著性检验。
'''
    (OUT/'DIRECT_DIFFERENCE_REPORT.md').write_text(report,encoding='utf8')
    dump(OUT/'complete.json',dict(time=now(),regions=24,SL_disagreement_pixels=int(d.SL_control_framework_disagreement_pixels.sum()),same_inputs_verified=True,mask_matches_saved_experimental_mask=True,raw_code_delta_dtype='int16',no_new_significance=True))
if __name__=='__main__':main()
