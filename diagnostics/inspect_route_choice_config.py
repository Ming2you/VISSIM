from diagnostics.probe_model_area_integration import build_projected,ROOT
import json,os
os.environ['RW_MAINLINE_SG_ONLY']='1'
p=ROOT/'evaluation/runs/codex_area_beta0_retry_s13_20260910/decisions_codex_area_beta0_retry_s13_20260910'
cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json',p/'state_001200.json',p/'action_001050.json',fixture_inputs=False)
for target in ['SC1004_to_SC1005','SC1004_to_SC107']:
    print(target,'support',{key:values for key,values in detectors['link_to_origins'].items() if target in values})
    print('incoming',{key:sp for key,sp in cfg.network.urban_movements.items() if sp.get('receiving_link')==target})
print('metadata',[ (key,value) for key,value in metadata.items() if 'capacity' in key and isinstance(value,(str,float,int))])
print('globalcap',cfg.network.movement_capacity_veh_h)
