"""Compare one geometry-derived correction to its frozen predecessor."""
from pathlib import Path
import hashlib
import gzip
import json

HERE=Path(__file__).resolve().parent
I=HERE.parents[2]
U=I.parents[2]
pins={}

def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

truth=read(I/'baseline_reproduction_20260929/sc1001_transport/comparison.json')
result={};max_mass=0.
for seed,at in ((47,2700),(43,2250)):
    old_dir=I/f'closedloop_recorded{at}_lever450_trace10484_transport_s{seed}_v1'
    new_dir=I/f'closedloop_recorded{at}_lever450_trace10484_peeloff10121_s{seed}_v1'
    old=read(old_dir/'summary.json');new=read(new_dir/'summary.json')
    assert old['start_sec']==new['start_sec']==at and old['duration_sec']==new['duration_sec']==450
    assert not new['future_observation_inputs'] and new['optimizer_iterations']==0 and not new['native_started']
    rows=[]
    for key,r in new['results'].items():
        b=old['results'][key]
        assert b['commands']==r['commands']
        assert r['validation']['all_actuator_and_step_constraints_checked'] and r['executed_control_blocks']==[0,1,2]
        max_mass=max(max_mass,max(abs(v['residual']) for v in r['ramps'].values()))
        assert max_mass<1e-7
        target='SC1001_N_SC2002_to_W_RAMP'
        traces=[]
        for folder in (old_dir,new_dir):
            p=folder/(key+'_RM_C10484_trace.json.gz');raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest()
            traces.append(json.loads(gzip.decompress(raw)))
        before,after=[x['incoming_movements'][target] for x in traces]
        expected=json.loads(json.dumps(before));expected['spec']['unsignalized']=True
        assert expected==after,'Only authority may change the traced movement contract'
        costs=next(v for v in truth[f'seed{seed}']['costs'] if v['case']==key)
        arm=('hold' if key=='held_actual' else 'release') if seed==47 else ('nc' if key=='held_actual' else key)
        native=next(v['actual'] for v in truth[f'seed{seed}']['ramps'] if v['arm']==arm and v['ramp']=='RM_C10484')
        rows.append(dict(case=key,actual_delta_omega=costs['actual_delta_omega'],
            before_delta_omega=b['ttt_omega_veh_h']-old['results']['held_actual']['ttt_omega_veh_h'],
            after_delta_omega=r['ttt_omega_veh_h']-new['results']['held_actual']['ttt_omega_veh_h'],
            before_omega=b['ttt_omega_veh_h'],after_omega=r['ttt_omega_veh_h'],
            before_outside=b['tracked_outside_residence_veh_h'],after_outside=r['tracked_outside_residence_veh_h'],
            ramp10484=dict(actual=native,before=b['ramps']['RM_C10484'],after=r['ramps']['RM_C10484']),
            before_N_flow=sum(v['vehicles'] for v in traces[0]['transfers'] if v['source']=='movement:'+target),
            after_N_flow=sum(v['vehicles'] for v in traces[1]['transfers'] if v['source']=='movement:'+target)))
    result[f'seed{seed}']=rows
base=read(I/'baseline_reproduction_20260929/sc1001_transport/candidate_config.json')
candidate=read(HERE/'candidate_config.json');path=candidate['urban']['movements']['physical_phase_authority']
candidate['urban']['movements']['physical_phase_authority']=base['urban']['movements']['physical_phase_authority']
assert candidate==base
authority=read(U/path);previous=read(U/base['urban']['movements']['physical_phase_authority'])
row=authority['unsignalized_movements'].pop('SC1001_N_SC2002_to_W_RAMP');assert authority==previous
result.update(new_forecasts=6,new_native=0,fit=False,gain_qualified=False,
              config_only_authority_changed=True,movement_capacity_unchanged=True,
              max_ramp_mass_residual=max_mass,source_pins=pins)
out=HERE/'comparison.json';assert not out.exists()
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({s:[{k:r[k] for k in ('case','actual_delta_omega','before_delta_omega','after_delta_omega','before_N_flow','after_N_flow')}
                     for r in result[s]] for s in ('seed47','seed43')},indent=2))
