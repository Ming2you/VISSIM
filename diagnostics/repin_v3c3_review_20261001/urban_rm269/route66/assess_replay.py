"""Assess the completed bounded pair, with physical stock and command checks."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
before=read(F/'lane_observations/frame_002400.json')
after=read(F/'lane_observations/frame_002550.json')
assert before['complete'] and after['complete']
initial={v[0]:v for v in before['vehicles'] if v[1]==66}
final={v[0]:v for v in after['vehicles'] if v[1]==66}
all_final={v[0] for v in after['vehicles']}
names={1:'SC1004_S_to_W',2:'SC1004_S_to_N_SC1003',3:'SC1004_S_to_E_SC1005'}
native_departures=dict.fromkeys(names.values(),0)
unknown_departures=0
for vid in initial.keys()-final.keys():
    v=initial[vid]
    if v[8]=='STATIC' and int(v[6])==1124:native_departures[names[int(v[7])]]+=1
    else:unknown_departures+=1
rows={};action_pins=set()
for arm in ('baseline','candidate'):
    folder=HERE/f'replay2400_{arm}'
    assert read(folder/'completion.json')['status']=='complete'
    result=read(folder/'link66.json')
    recorded=read(folder/'recorded_first_step.json')
    action_pins.add(recorded['recorded_action_sha256'])
    assert abs(result['local_balance_error_veh'])<1e-7
    assert abs(result['omega_ttt_veh_h']-recorded['ttt_omega_veh_h'])<1e-7
    result.pop('transfers')
    result['end_stock_error_veh']=result['end_approach_veh']-len(final)
    result['initial_departure_error_by_movement']={m:v-native_departures[m] for m,v in result['predicted_departures'].items()}
    rows[arm]=result
assert len(action_pins)==1
assert sum(rows['baseline']['initial']['queue'].values())+rows['baseline']['initial']['storage']==sum(rows['candidate']['initial']['queue'].values())+rows['candidate']['initial']['storage']
report=dict(status='completed_bounded_input_check',rows=rows,
    observed=dict(start_vehicles=len(initial),end_vehicles=len(final),initial_no_longer66=len(initial.keys()-final.keys()),
        initial_missing_in_next_frame=len(initial.keys()-all_final),initial_departures_by_known_route=native_departures,
        unknown_initial_departures=unknown_departures,new_end_inventory=len(final.keys()-initial.keys())),
    same_recorded_command_sha256=next(iter(action_pins)),
    scope='150s same-command discrete model before/after initial destination and native-prior correction. Different plant predictions, not different native control arms. No control-gain or whole-run performance claim.',
    native_runs=0,optimizer_runs=0,source_pins=pins)
(HERE/'replay_assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:report[k] for k in ('status','observed','rows')},ensure_ascii=False,indent=2))
