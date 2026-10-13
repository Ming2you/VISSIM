"""Review one completed decision and its full process wall, without rerunning."""
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

A=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())


def main():
    plan=read(A/'full_selection_plan.json')
    assert plan['status']=='complete_pending_review' and plan['launches_consumed']==1
    result=read(A/'full_selection_execution.json')
    closed=read(A/'full_selection_process_result.json')
    launch=read(A/'full_selection_launch.json')
    assert result['status']=='complete_pending_review' and closed['exit_code']==0
    wall=(datetime.fromisoformat(closed['ended'])-datetime.fromisoformat(launch['started'])).total_seconds()
    assert wall>=result['elapsed_seconds']
    for path,digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    spec=importlib.util.spec_from_file_location('retained_full_inspector',
        A.parent/'runtime_pair2400_numericfix/compare.py')
    cmp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cmp)
    run=cmp.inspect(A/'full2400_lane_offer',dict(status='complete_uncompared',exit_code=closed['exit_code'],
        external_process_wall_sec=wall))
    assert run['policy']['max_iterations']==run['policy']['pfo_cap_options']['max_iterations']==2
    c=run['costs_and_constraints']
    summary=dict(status='one_complete_decision_reviewed',
        process_wall_seconds=wall,full_time_target_met=wall<=600,
        held_omega_ttt_veh_h=c['held_objective'],selected_omega_ttt_veh_h=c['selected_objective'],
        predicted_delta_omega_veh_h=c['selected_objective']-c['held_objective'],
        physical_and_shared_feasible=True,three_block_actuator_checks=True,
        converged=run['converged'],selection_status=run['selection_status'],
        query_stats=run['query_stats'],selected_rm_by_block=run['selected_rm_by_block'],
        pfo_seconds=run['pfo_seconds'],sdmpc_after_pfo_seconds=run['sdmpc_after_pfo_seconds'],
        native_runs=0,source_pins_checked=True,complete_run=run,
        limits=['One full decision; competing frozen native workers. No matched-baseline speedup or8100s runtime claim.',
                'Selected cost is model Omega TTT, not measured native gain. All urban and RM actions may differ.',
                'Nonconverged feasible command is the best observed candidate, not a proven optimum.',
                'Ten-second transport covers68/connectors/lateral movement only; mainline and other urban clocks remain fine.',
                '3300s approach52 absolute stock direction remains wrong; no independent-seed or VSL-gain qualification.'])
    target=A/'full_selection_review.json'
    assert not target.exists(),'Reuse completed review'
    target.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    plan['status']='complete_reviewed';plan['review']=target.name
    (A/'full_selection_plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:summary[k] for k in ('status','process_wall_seconds','full_time_target_met',
        'held_omega_ttt_veh_h','selected_omega_ttt_veh_h','converged','query_stats')},indent=2))


if __name__=='__main__':main()
