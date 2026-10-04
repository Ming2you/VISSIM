"""Verify completed selection and two independent execution-model responses."""
import hashlib
import json
from pathlib import Path

L=Path(__file__).resolve().parent
I=L.parent.parent
O=L/'physical_speed/selection47'
D=I/'closedloop_recorded2700_select_ps47v1'
E=I/'closedloop_recorded2700_select_check_ps47v1_resv3'
pins={}


def load(p):
    b=p.read_bytes();pins[str(p.resolve())]=hashlib.sha256(b).hexdigest()
    return json.loads(b)


def close(a,b):
    assert abs(a-b)<1e-7,(a,b)


assert not (O/'verification.json').exists()
protocol=load(O/'protocol.json')
for p,h in protocol['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
receipt=load(D/'summary.json')
for p,h in receipt['files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
joint=load(D/'unused_action.joint.json');selection=joint['selection']
assert joint['completed'] and selection['feasible']
assert not receipt['native_started']
assert joint['physical_response_cache']['closed']
binding=load(D/'unused_action.joint_written.json')
assert binding['written_command_binding_passed']
for key in ('action_json','action_csv'):
    x=binding[key];assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
actual=load(E/'summary.json')
assert not actual['native_started'] and not actual['future_observation_inputs']
assert actual['optimizer_iterations']==0 and set(actual['results'])=={'held_actual','selected'}
assert Path(actual['selected_path']).resolve()==(D/'unused_action.json').resolve()
q=load(O/'execution_quantities.json');assert [r['case'] for r in q]==['held_actual','selected']
old=load(I/'closedloop_recorded2700_lever450_trace10484_ps_ind47_20261001/held_actual.json')
held=actual['results']['held_actual'];chosen=actual['results']['selected']
for key in ('commands','ramps','cost_by_stock','outside_cost_by_stock','ttt_omega_veh_h','control_area'):
    assert old[key]==held[key],key
for r,row in zip(q,(held,chosen)):
    close(r['ttt'],row['ttt_omega_veh_h'])
    close(sum(row['cost_by_stock'].values()),row['ttt_omega_veh_h'])
    assert len(row['ramps'])==8 and max(abs(v['residual']) for v in row['ramps'].values())<1e-8
    assert r['resource']['feasible']
    for key in ('np','nuf'):
        assert r['resource'][key]['target']==selection['final_constraints'][key]['target']
        assert r['resource'][key]['tolerance']==selection['final_constraints'][key]['tolerance']
    assert len(r['resource']['net_inflow_veh_by_owner'])==17
    assert not r['resource']['nonowner_service_included_in_np']
    assert r['resource']['nuf_definition']=='predicted_accepted_mainline_merge'
    close(sum(v['merge'] for v in row['ramps'].values())*8,r['resource']['nuf']['actual'])
delta={k:chosen['cost_by_stock'].get(k,0)-held['cost_by_stock'].get(k,0)
    for k in held['cost_by_stock'].keys()|chosen['cost_by_stock'].keys()}
parts={k:delta['freeway:'+k] for k in ('FW_E','FW_W')}
parts['eight_on_ramps']=sum(v for k,v in delta.items() if k.startswith('ramp:'))
parts['other_Omega']=sum(delta.values())-sum(parts.values())
gain=chosen['ttt_omega_veh_h']-held['ttt_omega_veh_h']
close(sum(parts.values()),gain)
changes=[]
for a,b in zip(held['commands'],chosen['commands']):
    changes.append({kind:{key:dict(held=value,selected=b[kind][key]) for key,value in a[kind].items()
        if value!=b[kind][key]} for kind in ('meters','vsl','green_times','offsets')})
report=dict(status='diagnostic_selection_and_execution_model_check_complete',adopted=False,
    goal='ACTIVE/NOT_QUALIFIED',previous_turn='progress',current_turn='progress',native_runs=0,
    fit=0,fzp_scans=0,live_CTg_poll=0,push=0,controller_decisions=1,controller_wall_sec=joint['elapsed_sec'],
    solver=dict(converged=selection['converged'],status=selection['selection_status'],
        candidates=selection['candidates'],approximate_scalar_rollouts=joint['physical_response_cache']['scalar_rollouts'],
        approximate_tangent_rollouts=joint['physical_response_cache']['tangent_rollouts'],
        independent_AD_witness=selection['independent_ad_witness_performed']),
    execution_forecasts=2,controller_surrogate_delta=selection['selected_objective']-selection['held_objective'],
    execution_delta_Omega=gain,execution_delta_outside=chosen['tracked_outside_residence_veh_h']-held['tracked_outside_residence_veh_h'],
    execution_delta_combined=chosen['ttt_with_tracked_outside_veh_h']-held['ttt_with_tracked_outside_veh_h'],
    delta_cost_by_group=parts,commands=changes,resource_checks=q,
    ramp_merge_delta={k:chosen['ramps'][k]['merge']-v['merge'] for k,v in held['ramps'].items()},
    original_held_execution_reproduced_exactly=True,all8_ramp_mass_pass=True,writer_binding_pass=True,
    source_pins=pins,limitations=[
        'The aggregate improvement is primarily urban; mainline TTT rises. Do not attribute the full gain to RM or VSL.',
        'No native execution of this selected command; old native hold/release verifies a different fixed intervention.',
        'SameOmega objective retained; represented outside increases and is diagnostic only, not complete uninserted waiting.',
        'Solver reaches its existing2-iteration limit; not a converged equilibrium or exhaustive discrete lever optimum.',
        'All237 axes computed, but no new independent all-axis AD finite-difference witness; two scalar execution responses are not that witness.',
        'Physical NP/NUF resource checks use the real static LinkAgentWuFollower catalog on an unchanged copied config; no optimizer or global physics hook installed.'])
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('execution_delta_Omega','execution_delta_outside','execution_delta_combined','delta_cost_by_group','ramp_merge_delta')},indent=2))
