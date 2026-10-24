"""Reuse the validated seed47 native pair; compare two fixed450 predictions."""
import hashlib
import json
import sys
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
def option(name,default):
    return next((a.split('=',1)[1] for a in sys.argv[1:] if a.startswith('--'+name+'=')),default)
candidate_label=option('candidate-label','origin10490_ind47_20261001')
baseline_label=option('baseline-label','ps_ind47_20261001')
for label in (candidate_label,baseline_label):
    assert all(c.isalnum() or c in '_-' for c in label)
O=Path(option('output-dir',str(O))).resolve()
assert O.is_relative_to(L) and O.is_dir() and not (O/'independent47_verification.json').exists()
def read(p):return json.loads(p.read_bytes())
proof=read(L/'physical_speed/independent47/verification.json')
folder=I/('closedloop_recorded2700_lever450_trace10484_'+candidate_label)
summary=read(folder/'summary.json')
assert set(summary['results'])=={'held_actual','release_actual'}
assert not summary['native_started'] and not summary['future_observation_inputs'] and summary['optimizer_iterations']==0
receipt=read(folder/'fixed_replay_receipt.json')
assert receipt['observation_cutoff_sec']==2700 and receipt['future_states_used'] is False
for path,h in receipt['files'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
models={};counter={}
for label,source in (('before',I/('closedloop_recorded2700_lever450_trace10484_'+baseline_label)),('candidate',folder)):
    armdata={arm:read(source/f'{arm}.json') for arm in ('held_actual','release_actual')}
    for arm,row in armdata.items():
        assert row['validation']['all_actuator_and_step_constraints_checked']
        assert max(abs(x['residual']) for x in row['ramps'].values())<1e-8
        assert abs(sum(row['cost_by_stock'].values())-row['ttt_omega_veh_h'])<1e-8
        assert [c['meters']['RM_C10484'] for c in row['commands']]==([2.,2.,2.] if arm=='held_actual' else [4.,6.,8.])
        counter[label,arm]=row
    h,r=armdata['held_actual'],armdata['release_actual']
    assert h['physical_cell_states'][0]==r['physical_cell_states'][0]
    costs={k:r['cost_by_stock'].get(k,0.)-h['cost_by_stock'].get(k,0.)
           for k in r['cost_by_stock'].keys()|h['cost_by_stock'].keys()}
    parts={road:costs.get('freeway:'+road,0.) for road in ('FW_E','FW_W')}
    parts['ramps']=sum(v for k,v in costs.items() if k.startswith('ramp:'))
    parts['other_Omega']=sum(costs.values())-sum(parts.values())
    models[label]=dict(delta_omega=r['ttt_omega_veh_h']-h['ttt_omega_veh_h'],
        delta_outside=r['tracked_outside_residence_veh_h']-h['tracked_outside_residence_veh_h'],
        delta_by_group=parts,ramps={ramp:dict(hold=h['ramps'][ramp],release=r['ramps'][ramp],
        delta_merge=r['ramps'][ramp]['merge']-h['ramps'][ramp]['merge']) for ramp in h['ramps']})
for arm in ('held_actual','release_actual'):
    a,b=counter['before',arm],counter['candidate',arm]
    assert a['commands']==b['commands'] and a['physical_cell_states'][0]==b['physical_cell_states'][0]
native=proof['native_delta_omega'];target=proof['native_delta_by_group']['FW_E']
rank=all(models[m]['delta_omega']>0 and models[m]['delta_by_group']['FW_E']>0 for m in models) and native>0 and target>0
result=dict(status='independent_fixed_response_complete',adopted=False,ranking_preserved=rank,
    native_delta_omega=native,native_delta_by_group=proof['native_delta_by_group'],
    models=models,native10490={k:v['ramps']['RM_C10490'] for k,v in proof['native'].items()},
    native_ramps={k:v['ramps'] for k,v in proof['native'].items()},
    model_labels=dict(before=baseline_label,candidate=candidate_label),
    same_initial_state_and_commands=True,all8_conservation=True,writer_constraints_pass=True,
    forecast_count=2,optimizer_runs=0,native_runs=0,coefficients_fitted=0,
    limitations=['Tests the existing native10484 RM hold/release pair under the named model changes.',
        'No isolated10490 intervention, no VSL response or fullSDMPC derivative proof.',
        'Outside cost diagnostic only. Native future traffic inputs not used.'],
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        L/'physical_speed/independent47/verification.json',folder/'summary.json',folder/'fixed_replay_receipt.json')})
(O/'independent47_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(ranking_preserved=rank,native_delta_omega=native,
    models={k:{t:v[t] for t in ('delta_omega','delta_outside','delta_by_group')} for k,v in models.items()},
    native10490=result['native10490'],pred10490={k:v['ramps']['RM_C10490'] for k,v in models.items()}),ensure_ascii=False))
