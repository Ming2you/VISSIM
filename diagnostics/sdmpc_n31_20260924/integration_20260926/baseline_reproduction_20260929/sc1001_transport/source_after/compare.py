"""Validate eight completed forecasts against pinned saved native observations."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
I=HERE.parents[1]
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(b)

pair=read(I/'baseline_reproduction_20260929/coupled_arrival_s47/comparison.json')
four=read(I/'sc1002_route_choice_20260929/comparison.json')['seed43']
folders={
 'seed47':('closedloop_recorded2700_lever450_trace10484_coupled_s47_v1',
           'closedloop_recorded2700_lever450_trace10484_transport_s47_v1'),
 'seed43':('closedloop_recorded2250_lever450_native1113_s43',
           'closedloop_recorded2250_lever450_trace10484_transport_s43_v1')}
result={};max_mass=0.
for seed,(oldfolder,newfolder) in folders.items():
    old=read(I/oldfolder/'summary.json');new=read(I/newfolder/'summary.json')
    assert old['start_sec']==new['start_sec'] and old['duration_sec']==new['duration_sec']==450
    assert new['future_observation_inputs'] is False and new['optimizer_iterations']==0 and not new['native_started']
    rows=[];costs=[]
    for key,d in new['results'].items():
        b=old['results'][key]
        assert b['commands']==d['commands'] and d['validation']['all_actuator_and_step_constraints_checked']
        assert d['executed_control_blocks']==[0,1,2]
        arm=('hold' if key=='held_actual' else 'release') if seed=='seed47' else ('nc' if key=='held_actual' else key)
        for ramp,v in d['ramps'].items():
            actual=(pair['arms'][arm]['ramps'][ramp]['actual'] if seed=='seed47' else
                    next(r['actual'] for r in four['ramps'] if r['arm']==arm and r['ramp']==ramp))
            max_mass=max(max_mass,abs(v['residual']))
            assert abs(v['residual'])<1e-7
            rows.append(dict(arm=arm,ramp=ramp,actual=actual,before=b['ramps'][ramp],after=v))
        actual_delta=(0. if key=='held_actual' else pair['actual_delta_omega']) if seed=='seed47' else next(c['actual_delta_omega'] for c in four['costs'] if c['case']==key)
        costs.append(dict(case=key,actual_delta_omega=actual_delta,
            before_delta_omega=b['ttt_omega_veh_h']-old['results']['held_actual']['ttt_omega_veh_h'],
            after_delta_omega=d['ttt_omega_veh_h']-new['results']['held_actual']['ttt_omega_veh_h'],
            before_omega=b['ttt_omega_veh_h'],after_omega=d['ttt_omega_veh_h'],
            before_outside=b['tracked_outside_residence_veh_h'],after_outside=d['tracked_outside_residence_veh_h'],
            after_cost_delta_by_stock={k:v-new['results']['held_actual']['cost_by_stock'].get(k,0.) for k,v in d['cost_by_stock'].items()}))
    result[seed]=dict(costs=costs,ramps=rows,
        mae={version:{metric:sum(abs(r[version][metric]-r['actual'][metric]) for r in rows)/len(rows)
                      for metric in ('arrival','merge','final_stock')} for version in ('before','after')})

disabled=read(I/'closedloop_recorded2700_lever450_trace10484_transport_disabled_s47/summary.json')
previous=read(I/'closedloop_recorded2700_lever450_trace10484_coupled_s47_v1/summary.json')
for key in previous['results']:
    a={k:v for k,v in previous['results'][key].items() if k!='wall_sec'}
    b={k:v for k,v in disabled['results'][key].items() if k!='wall_sec'}
    assert a==b, key
base=read(I/'sc1002_route_choice_20260929/candidate_config.json')
candidate=read(HERE/'candidate_config.json')
assert candidate['urban'].pop('sc1001_destination_travel')=={'initial_unknown':'reachable_native_prior'}
assert candidate==base
result.update(new_candidate_forecasts=6,disabled_regression_forecasts=2,new_native=0,
              default_physical_outputs_exact=True,config_only_travel_contract_changed=True,
              max_ramp_mass_residual=max_mass,commands_equal=True,fit=False,gain_qualified=False,
              source_pins=pins)
target=HERE/'comparison.json';assert not target.exists()
target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({s:{'mae':result[s]['mae'],'delta_costs':[{k:v for k,v in c.items() if 'delta_omega' in k or k=='case'} for c in result[s]['costs']]} for s in folders},ensure_ascii=False,indent=2))
