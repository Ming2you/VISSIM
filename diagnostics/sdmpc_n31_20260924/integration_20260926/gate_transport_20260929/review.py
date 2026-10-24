"""Review completed gate transport forecasts; no simulation or refitting."""
from pathlib import Path
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
I=HERE.parent
ROOT=I.parents[2]
pins={}


def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    target=HERE/'review.json'
    assert not target.exists(), 'Preserve completed review'
    original_cfg=read(I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_full_config.json')
    future_cfg=read(HERE/'candidate_full_config.json')
    assert future_cfg['urban']['ramp'].pop('native_gate_travel') is True
    assert future_cfg==original_cfg
    before=read(I/'closedloop_recorded2700_lever450_rm_pair_s47_cell23_v4/summary.json')
    future=read(I/'closedloop_recorded2700_lever450_gate_future_s47_v1/summary.json')
    native=read(I/'native_rm_observation2700_writerfix_v3/analysis/summary.json')
    audit=read(I/'closedloop_recorded2700_lever450_rm_pair_s47_cell23_v4/ramp_response_audit.json')
    assert native['counterfactual_valid'] and native['paired_prefix_exact']
    ramps=[]
    for arm,case in (('hold','held_actual'),('release','release_actual')):
        assert before['results'][case]['commands']==future['results'][case]['commands']
        for ramp,old in before['results'][case]['ramps'].items():
            actual=audit['arms'][arm][ramp]['actual']
            new=future['results'][case]['ramps'][ramp]
            assert abs(new['residual'])<1e-7
            assert actual['initial_stock']+new['arrival']-new['merge']==new['final_stock'] or abs(
                actual['initial_stock']+new['arrival']-new['merge']-new['final_stock'])<1e-7
            ramps.append(dict(arm=arm,ramp=ramp,actual=actual,before=old,candidate=new))
    error={}
    for label in ('before','candidate'):
        error[label]={metric:sum(abs(row[label][metric]-row['actual'][metric]) for row in ramps)/len(ramps)
                      for metric in ('arrival','merge','final_stock')}
    deltas={}
    for name,model in (('before',before),('candidate',future)):
        hold=model['results']['held_actual'];release=model['results']['release_actual']
        deltas[name]=dict(omega=release['ttt_omega_veh_h']-hold['ttt_omega_veh_h'],
            tracked_outside=release['tracked_outside_residence_veh_h']-hold['tracked_outside_residence_veh_h'])
    deltas['actual']=dict(omega=native['delta_TTT_veh_h'],outside=native['delta_outside_Omega_residence_veh_h'])
    reach=[]
    for folder in ('closedloop_recorded2700_select_check_rm_pair_s47_cell23_v2',
                   'closedloop_recorded4500_select_check_local_cell23_v1'):
        a=read(I/folder/'summary.json');b=read(I/(folder+'_reachability_v1')/'summary.json')
        for case in a['results']:
            assert a['results'][case]['commands']==b['results'][case]['commands']
            assert all(abs(r['residual'])<1e-7 for r in b['results'][case]['ramps'].values())
        reach.append(dict(source=folder,before_delta=a['results']['selected']['ttt_omega_veh_h']-a['results']['held_actual']['ttt_omega_veh_h'],
            after_delta=b['results']['selected']['ttt_omega_veh_h']-b['results']['held_actual']['ttt_omega_veh_h']))
    cases=[]
    for folder in ('closedloop_recorded2700_lever450_gate_future_s47_v1',
                   'closedloop_recorded4500_lever450_gate_future_s29_v1',
                   'closedloop_recorded6000_lever450_gate_future_s29_v1'):
        model=read(I/folder/'summary.json');runtime=read(I/folder/'runtime.json')
        assert model['future_observation_inputs'] is False and model['optimizer_iterations']==0
        for case,row in model['results'].items():
            assert row['validation']['all_actuator_and_step_constraints_checked']
            assert all(abs(r['residual'])<1e-7 for r in row['ramps'].values())
            account=row['gate_future_final_accounting']
            assert 0<=account['arrived_veh']<=account['admitted_veh']+1e-7<=account['desired_veh']+2e-7
            cases.append(dict(source=folder,case=case,start_sec=model['start_sec'],
                wall_sec=row['wall_sec'],omega=row['ttt_omega_veh_h'],
                delays={k:v['delay_steps'] for k,v in runtime['gate_future_travel']['timings'].items()},
                gate_accounting=account,ramps=row['ramps']))
    assert len(cases)==4
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    parity=read(HERE/'strict_native_parity.json')
    core=ROOT/'evaluation/controllers/physical_ramp_branches.py'
    assert hashlib.sha256(core.read_bytes()).hexdigest()==parity['new_core_sha256']
    report=dict(reachability_only=reach,matched_s47_ramps=ramps,ramp_mean_absolute_error=error,
        rm10484_release_delta=deltas,future_transport_cases=cases,strict_native_parity=parity,
        future_transport_default_enabled=False,new_native_runs=0,new_forecasts=8,optimizer_iterations=0,
        fitted_parameters=0,fzp_scans=0,stop_unchanged=True,gain_qualified=False,
        limitations=['Two seed29 held-command cases prove execution and conservation only, not matched native accuracy.',
                     'Native future selected city+RM commands have not been replayed under the transport candidate.',
                     'Initial committed routes remain unknown within reachable alternatives; their timing remains unchanged.',
                     'RM10484 ranking remains correct but its loss magnitude is underpredicted; no VSL efficacy claim.'],
        source_sha256={**pins,str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(error=error,deltas=deltas,reachability_only=reach,new_forecasts=8,new_native_runs=0)))


if __name__=='__main__':main()
