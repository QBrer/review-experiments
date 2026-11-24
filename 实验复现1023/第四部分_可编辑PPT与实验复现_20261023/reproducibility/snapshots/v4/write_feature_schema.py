from engine import *
basic=[]
for t in [2010,2020]:basic += [f'H{t}_entropy',f'W{t}_entropy',f'H{t}_boundary_area_fraction',f'W{t}_boundary_area_fraction']
basic+=['safe_coverage']
for t in [2010,2020]:basic += [f'A1_{t}_peak_prominence',f'A1_{t}_peak_width',f'A1_{t}_row_shift',f'A1_{t}_col_shift']
basic+=['A1_temporal_shift_diff_row','A1_temporal_shift_diff_col','A1_temporal_shift_diff_L1','A1_temporal_shift_diff_L2']
extra=[]
for t in [2010,2020]:extra += [f'A2_{t}_peak_prominence',f'A2_{t}_peak_width',f'A2_{t}_row_shift',f'A2_{t}_col_shift']
extra+=['semantic_conditional_entropy_2010','semantic_conditional_entropy_2020']
for t in [2010,2020]:extra += [f'A1_A2_shift_diff_{t}_row',f'A1_A2_shift_diff_{t}_col',f'A1_A2_shift_diff_{t}_L1']
extra+=['A2_temporal_shift_diff_L1','H_raw_class_change_fraction','W_raw_class_change_fraction','A3_A1_total_shift_diff_L1','A3_A2_total_shift_diff_L1']
assert len(basic)==21 and len(extra)==21
dump(ROOT/'feature_schema.json',{'basic':[{'column':f'x{i:02d}','name':s} for i,s in enumerate(basic)],'cross_dimensional':[{'column':f'x{i+21:02d}','name':s} for i,s in enumerate(extra)],'normalization':'matching surfaces ddof0; training median fill and missing indicators','test_metadata_not_features':['site','case_id','phase','block','injected_d','truth']})
print('Feature schema saved')
