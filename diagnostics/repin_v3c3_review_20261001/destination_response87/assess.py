"""Judge finished conditional diagnostics; never rerun or promote the model."""
import ast
import hashlib
import json
import math
from pathlib import Path

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def transfers(row):
    return [r for block in row['executed_intervals'] for r in block['transfers']]


def flow(row):
    result=dict(source=0.,merge=0.,off=0.,terminal=0.)
    for r in transfers(row):
        source,target=r['source'] or '',r['target'] or ''
        if target=='freeway:FW_E':
            if source=='origin:FW_E':result['source']+=r['vehicles']
            elif source.startswith('merge_pending:'):result['merge']+=r['vehicles']
        elif source=='freeway:FW_E':
            if target.startswith('storage:'):result['off']+=r['vehicles']
            elif target=='external:terminal:FW_E':result['terminal']+=r['vehicles']
    return result


def result(rows):
    held,vsl=rows
    x,y=flow(held),flow(vsl)
    return dict(delta_omega=vsl['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
        delta_east=vsl['cost_by_stock']['freeway:FW_E']-held['cost_by_stock']['freeway:FW_E'],
        delta_outside=vsl['tracked_outside_residence_veh_h']-held['tracked_outside_residence_veh_h'],
        delta_by_stock={k:v-held['cost_by_stock'][k] for k,v in vsl['cost_by_stock'].items()},
        east_flow_delta={k:y[k]-x[k] for k in x},east_flows=[x,y])


def main():
    assert not (D/'assessment.json').exists(), 'Preserve finished diagnostic'
    run=D/'attempt2'
    p=load(run/'protocol.json');status=load(run/'status.json')
    assert status['phase']=='complete_pending_assessment'
    assert status['stats']['calls']==2 and status['stats']['steps']==1800
    assert status['stats']['ramp_queries']==status['stats']['physical_updates']==900
    for path,h in p['input_pins'].items():assert sha(Path(path))==h,path
    for path,h in p['production_pins'].items():assert sha(Path(path))==h,path
    assert sha(Path(p['old_stop']['path']))==p['old_stop']['sha256']
    old=I/'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path'
    new=Path(status['output']);names=('release_actual','release_vsl90_actual')
    a,b=([load(folder/(name+'.json')) for name in names] for folder in (old,new))
    witnesses=load(run/'witness.json');steps=load(run/'steps.json')
    assert len(steps)==1800 and len(witnesses)==2
    worst=0.;port_worst=0.
    for idx,(reference,diagnostic) in enumerate(zip(a,b)):
        assert diagnostic['future_observation_inputs'] and not diagnostic['conditional_diagnostic']['autonomous']
        assert all(v['future_observation_inputs'] for v in diagnostic['executed_intervals'])
        assert diagnostic['commands']==reference['commands']
        assert diagnostic['physical_cell_states'][0]==reference['physical_cell_states'][0]
        assert diagnostic['executed_control_blocks']==[0,1,2]
        assert diagnostic['validation']['all_actuator_and_step_constraints_checked']
        assert abs(sum(diagnostic['cost_by_stock'].values())-diagnostic['ttt_omega_veh_h'])<1e-7
        first,last=witnesses[idx]['stocks'][0]['stock'],witnesses[idx]['stocks'][-1]['stock']
        for key in first.keys()|last.keys():
            delta=math.fsum(r['vehicles'] for r in transfers(diagnostic) if r['target']==key)-math.fsum(r['vehicles'] for r in transfers(diagnostic) if r['source']==key)
            worst=max(worst,abs(last.get(key,0)-first.get(key,0)-delta))
        assert witnesses[idx]['resource_max']<1e-7
        for block in diagnostic['executed_intervals']:
            assert len(block['ramps'])==len(block['offramps'])==8
            for row in block['ramps'].values():
                port_worst=max(port_worst,abs(row['initial_stock']+row['arrival']-row['merge']-row['final_stock']))
            for row in block['offramps'].values():
                port_worst=max(port_worst,abs(row['initial_stock']+row['arrival']-row['drain']-row['final_stock']))
        current=[s for s in steps if s['arm']==('release','release_vsl90')[idx]]
        for caller in ('evaluation.controllers.lane_ramp_runtime','evaluation.controllers.area_freeway_accounting'):
            assert [s['time_sec'] for s in current if s['caller']==caller]==list(range(2700,3150))
        assert all(abs(s['conditional_target_veh']+s['conditional_through_veh']-s['total_requested_veh'])<1e-10 for s in current)
    assert worst<1e-7 and port_worst<1e-7,(worst,port_worst)
    base,conditional=result(a),result(b)
    native=load(D.parent/'s67_full_observation/response_assessment76.json')
    actual_cost=native['actual_delta_omega_veh_h']
    actual_terminal=native['arms']['release_vsl90']['mainline']['FW_E']['actual']['terminal']-native['arms']['release']['mainline']['FW_E']['actual']['terminal']
    checks={}
    for key,truth,x,y in [('omega',actual_cost,base['delta_omega'],conditional['delta_omega']),
                        ('terminal',actual_terminal,base['east_flow_delta']['terminal'],conditional['east_flow_delta']['terminal'])]:
        e0,e1=abs(x-truth),abs(y-truth)
        checks[key]=dict(actual=truth,baseline=x,conditional=y,error_reduction_fraction=1-e1/e0,
            passes_diagnostic_screen=e1<=.8*e0)
    old_functions={n.name:ast.dump(n) for n in ast.parse((D/'assess.before.py.txt').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    current_functions={n.name:ast.dump(n) for n in ast.parse((D.parent/'vsl_current_cells16_20/assess.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    assert all(current_functions[k]==v for k,v in old_functions.items())
    report=dict(status='complete_conditional_diagnostic',baseline=base,conditional=conditional,checks=checks,
        screen_passed=all(r['passes_diagnostic_screen'] for r in checks.values()),
        goal='ACTIVE / NOT_QUALIFIED',adopted=False,future_observation_inputs=True,
        autonomous_validation=False,successful_conditional_rollouts=2,failed_count_check_after_rollout=1,
        total_conditional_rollouts=3,new_native=0,fitting=0,fzp_scan=0,
        forecast_compute_seconds=sum(r['wall_sec'] for r in b),stock_residual_max=worst,
        port_residual_max=port_worst,resource_max=max(w['resource_max'] for w in witnesses),
        original_functions_unchanged=len(old_functions),production_unchanged=True,STOP_unchanged=True,
        limitations=['Sparse150s observed ratios held constant; not dense true local boundary velocities.',
            'Same total sending at a given state; subsequent predicted stock/speed and total discharge can change.',
            'Only10483 destination partition changed. Other geometry, class travel time and within-lane sharing remain approximations.',
            'Even improvement here would not qualify autonomous response, derivatives, SDMPC or a9000 run.'],
        input_pins={str(folder/(name+'.json')):sha(folder/(name+'.json')) for folder in (old,new) for name in names})
    (D/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','checks','stock_residual_max','port_residual_max','forecast_compute_seconds')},ensure_ascii=False))


if __name__=='__main__':
    main()
