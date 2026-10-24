"""Compare the changed search budget on the same aggregate model/state."""
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

A=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())


def main():
    plan=read(A/'bounded_selection_plan.json')
    assert plan['status']=='complete_pending_comparison' and plan['launches_consumed']==1
    closed=read(A/'bounded_process_result.json');launch=read(A/'bounded_launch.json')
    assert closed['exit_code']==0
    for path,digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    seconds=(datetime.fromisoformat(closed['ended'])-datetime.fromisoformat(launch['started'])).total_seconds()
    spec=importlib.util.spec_from_file_location('previous_full_inspector',
        A.parent/'runtime_pair2400_numericfix/compare.py')
    cmp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cmp)
    baseline=read(A/'full_selection_review.json')['complete_run']
    trial=cmp.inspect(A/'bounded2400_lane_offer',dict(status='complete_uncompared',exit_code=0,
        external_process_wall_sec=seconds))
    policies=[deepcopy(r['policy']) for r in (baseline,trial)]
    assert policies[0]['max_iterations']==policies[0]['pfo_cap_options']['max_iterations']==2
    assert policies[1]['max_iterations']==policies[1]['pfo_cap_options']['max_iterations']==1
    policies[1]['max_iterations']=policies[1]['pfo_cap_options']['max_iterations']=2
    assert not cmp.difference(*policies),'Unexpected policy change beyond iteration budget'
    before=baseline['costs_and_constraints'];after=trial['costs_and_constraints']
    assert abs(before['held_objective']-after['held_objective'])<1e-7,'Different common held cost'
    for field in ('reference.json','state.json'):
        left,right=[read(A/name/field) for name in ('full2400_lane_offer','bounded2400_lane_offer')]
        if field=='state.json':
            for k in ('time_sec','urban_link_storage','urban_movement_queue','ramp_queue'):
                assert left[k]==right[k],k
        else:
            assert not cmp.difference(left,right),'Different executable initial command'
    baseline_gain=before['held_objective']-before['selected_objective']
    trial_gain=after['held_objective']-after['selected_objective']
    result=dict(status='complete_changed_budget_comparison',
        before_seconds=baseline['external_process_wall_sec'],after_seconds=seconds,
        full_time_target_met=seconds<=600,original_held_omega_veh_h=after['held_objective'],
        before_selected_omega_veh_h=before['selected_objective'],
        after_selected_omega_veh_h=after['selected_objective'],
        selected_cost_increase_veh_h=after['selected_objective']-before['selected_objective'],
        baseline_gain_veh_h=baseline_gain,trial_gain_veh_h=trial_gain,
        fraction_of_baseline_model_gain_retained=trial_gain/baseline_gain if baseline_gain>0 else None,
        owner_cost_changes={k:after['omega_partition']['costs'][k]-v for k,v in before['omega_partition']['costs'].items()},
        actuator_changes=cmp.difference(baseline['action_blocks'],trial['action_blocks']),
        budget_initialization='Same PFO-plus-margin rule; numeric caps may differ because the achieved PFO trajectory differs.',
        same_model_and_initial_command=True,physical_and_shared_checks_pass=True,
        complete_run=trial,new_predictions=0,native_runs=0,production_adopted=False,
        limits=['Changed iteration budget, not an equivalent optimization algorithm run.',
                'Single saved state under competing native workload; does not qualify all decision times or native performance.',
                'Compare retained gain relative to the common held command, not just the small fraction of totalTTT.',
                'Nonconverged commands are best observed feasible; city-owner costs are not a complete physical urban-area partition.'])
    target=A/'bounded_selection_comparison.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    plan['status']='complete_compared';plan['result']=target.name
    (A/'bounded_selection_plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','after_seconds','full_time_target_met',
        'selected_cost_increase_veh_h','fraction_of_baseline_model_gain_retained')},indent=2))


if __name__=='__main__':main()
