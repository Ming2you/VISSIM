"""Verify prediction overhead reduction without changing optimization work."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'diagnostics/sdmpc_stream_summary_20260922'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    solve=read(folder/'full_decision_v1/result.json')
    baseline=read(ROOT/'diagnostics/sdmpc_initial_shared_20260922/full_decision_v2/result.json')
    jac=read(folder/'hotpath_h3_v1/comparison.json')
    audit=read(folder/'exact_audit_v1/result.json')
    selection=solve['selection'];q=solve['query'];derivatives=selection['tangent_derivatives']
    old_derivatives=baseline['selection']['tangent_derivatives']
    differences={key:max(float(np.max(abs(np.asarray(a[key])-np.asarray(b[key]))))
        for a,b in zip(derivatives,old_derivatives))
        for key in ('costs','resources','cost_jacobian','resource_jacobian')}
    checks=dict(completed=solve['completed'],same_saved_time=solve['sim_sec']==baseline['sim_sec']==900.,
        no_source_changes=not solve['source_changes'] and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
            for p,h in solve['source_sha256'].items()),
        only_hotpath_policy_added=solve['policy']==dict(baseline['policy'],prediction_hotpath=True),
        same_iteration_context=solve['iteration_context']==baseline['iteration_context'],
        isolated_derivative_unchanged=jac['pass_all'],
        same_used_derivatives=len(derivatives)==len(old_derivatives) and max(differences.values())==0.,
        same_selected_control=solve['response']['control']==baseline['response']['control'],
        same_objectives=all(selection[k]==baseline['selection'][k] for k in ('held_objective','selected_objective')),
        all_model_checks_preserved=all(a['surrogate_prediction']['model_constraint_coverage']==b['surrogate_prediction']['model_constraint_coverage']
            and a['surrogate_prediction']['resource_summary']==b['surrogate_prediction']['resource_summary']
            for a,b in zip(derivatives,old_derivatives)),
        omitted_records_explicit=all(r['surrogate_prediction']['streamed_model_checks']['successful_records_retained'] is False
            and r['surrogate_prediction']['streamed_model_checks']['original_checks_performed'] is True for r in derivatives),
        same_tape_sizes=all(a['reverse_sweeps']['nodes']==b['reverse_sweeps']['nodes'] for a,b in zip(derivatives,old_derivatives)),
        model_feasible=solve['response']['feasible'],
        no_false_audit_pass=all(r['complete_primal_state_match'] is False and r['max_primal_state_error'] is None
            and r['primal_audit_performed'] is False for r in derivatives),
        same_local_qp_work=len(selection['local_rows'])==len(baseline['selection']['local_rows'])
            and all(r['traffic_rollouts']==0 for r in selection['local_rows']),
        same_five_rollouts=q['total_rollouts']==baseline['query']['total_rollouts']==5
            and q['scalar_rollouts']==2 and q['tangent_rollouts']==3,
        no_hidden_exact_or_witness_rollouts=q['exact_execution_rollouts']==q['independent_ad_witness_rollouts']==0,
        no_failed_batches=q['failed_batches']==q['failed_predictions_with_unknown_rollout_count']==0,
        workers_closed=q['closed'] and not q['owned_workers_alive'],
        original_model_feasible=audit['exact_model_feasible'],
        physical_commands_checked=not any(audit['command_differences'].values()),
        all_three_blocks_checked=audit['control_sequence']['all_actuator_and_step_constraints_checked'],
        exact_audit_completed=audit['audit_completed'] and not audit['source_changes'],
        regression='Ran 158 tests' in (folder/'regression_v1.log').read_text() and '\nOK' in (folder/'regression_v1.log').read_text(),
        parameters='PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (folder/'full_decision_v1/progress.jsonl').read_text().splitlines()]
    result=dict(scope=__doc__,checks=checks,all_checks_pass=all(checks.values()),
        before_sec=baseline['wall_sec'],after_sec=solve['wall_sec'],
        reduction_percent=100*(1-solve['wall_sec']/baseline['wall_sec']),decision_150s_target_met=solve['wall_sec']<=150,
        iteration_context=solve['iteration_context'],candidates=selection['candidates'],
        batch_times=[r for r in events if r['stage']=='sdmpc_surrogate_batch_done'],
        used_derivative_max_differences=differences,
        rollout_breakdown=q,exact_selected_cost=audit['selected_exact_cost'],exact_held_cost=audit['held_exact_cost'],
        surrogate_selected_cost=selection['selected_objective'],surrogate_held_cost=selection['held_objective'],
        native_applied=False,native9000_completed=False,adopted_default=False,
        timing_scope='One whole decision per version, max two outer iterations per NP candidate; selected accepted two, not converged.')
    paths=['evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent_worker.py',
        'evaluation/controllers/sdmpc_tangent_surrogate.py','evaluation/controllers/sdmpc_tangent_summary.py',
        'diagnostics/test_sdmpc_hotpath.py','diagnostics/check_sdmpc_reverse.py',
        'diagnostics/profile_sdmpc_current_ad.py','diagnostics/finalize_sdmpc_hotpath.py',
        'docs/SDMPC_PREDICTION_HOTPATH_20260922.md']
    manifest={}
    for name in paths:
        source=ROOT/name;target=folder/'final_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    result['source_sha256']=manifest
    with (folder/'summary.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rollout_breakdown','source_sha256')},indent=2))
    return 0 if result['all_checks_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
