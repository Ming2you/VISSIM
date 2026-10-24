"""Compare initial AD sharing with the frozen serial continuous-model solve."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'diagnostics/sdmpc_initial_shared_20260922'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    solve=read(folder/'full_decision_v2/result.json')
    baseline=read(ROOT/'diagnostics/sdmpc_surrogate_reuse_20260922/full_decision_v1/result.json')
    jac=read(folder/'shared_h3_v2/comparison.json')
    audit=read(folder/'exact_audit_v1/result.json')
    selection=solve['selection'];q=solve['query'];derivatives=selection['tangent_derivatives']
    differences={key:max(float(np.max(abs(np.asarray(a[key])-np.asarray(b[key]))))
        for a,b in zip(derivatives,baseline['selection']['tangent_derivatives']))
        for key in ('costs','resources','cost_jacobian','resource_jacobian')}
    baseline_policy=baseline['policy'];expected_policy=dict(baseline_policy,initial_shared_prediction=True)
    config=ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json'
    checks=dict(completed=solve['completed'],same_saved_time=solve['sim_sec']==baseline['sim_sec']==900.,
        no_runtime_source_changes=not solve['source_changes'] and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
            for p,h in solve['source_sha256'].items()),
        only_initial_shared_policy_added=solve['policy']==expected_policy,
        previous_config_unchanged=hashlib.sha256(config.read_bytes()).hexdigest()=='5c708fcff3cdda8abc33ee35a65d35613153f49fe233b745b9ba0ddeeb289fe4',
        same_iteration_context=solve['iteration_context']==baseline['iteration_context'],
        isolated_derivative_unchanged=jac['pass_all'],
        same_used_derivatives=len(derivatives)==len(baseline['selection']['tangent_derivatives']) and max(differences.values())<=1e-7,
        same_objective=abs(selection['selected_objective']-baseline['selection']['selected_objective'])<=1e-8,
        model_feasible=solve['response']['feasible'],
        approximation_explicit=solve['response'].get('execution_model_evaluated') is False
            and selection.get('independent_ad_witness_performed') is False,
        no_false_audit_pass=bool(derivatives) and all(r['complete_primal_state_match'] is False
            and r['max_primal_state_error'] is None and r['primal_audit_performed'] is False for r in derivatives),
        same_model_anchors=all(max(abs(v) for v in r['anchor_correction_'+name])<=1e-8
            for r in derivatives for name in ('costs','resources')),
        initial_binding_proved=q['initial_scalar_rollouts_removed']==1 and bool(q['initial_target_binding'])
            and selection['nuf_initialization']['physical_commands_unchanged'],
        initial_derivative_used=bool(q['rows'][0]['consumed_derivative']) and q['rows'][0]['derivatives'],
        no_local_qp_rollouts=bool(selection['local_rows']) and all(r['traffic_rollouts']==0 for r in selection['local_rows']),
        five_rollouts=q['total_rollouts']==q['scalar_rollouts']+q['tangent_rollouts']
            ==sum(r['scalar_rollouts']+r['tangent_rollouts'] for r in q['rows'])==5,
        no_hidden_exact_or_witness_rollouts=q['exact_execution_rollouts']==q['independent_ad_witness_rollouts']==0,
        no_failed_batches=q['failed_batches']==q['failed_predictions_with_unknown_rollout_count']==0,
        closed=q['closed'] and not q['owned_workers_alive'],
        physical_commands_checked=not any(audit['command_differences'].values()),
        all_three_blocks_checked=audit['control_sequence']['all_actuator_and_step_constraints_checked'],
        exact_audit_recorded=audit['audit_completed'] and not audit['source_changes'],
        regression='Ran 152 tests' in (folder/'regression_v2.log').read_text() and '\nOK' in (folder/'regression_v2.log').read_text(),
        parameters='PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (folder/'full_decision_v2/progress.jsonl').read_text().splitlines()]
    result=dict(scope=__doc__,checks=checks,implementation_checks_all_pass=all(checks.values()),
        before_sec=baseline['wall_sec'],after_sec=solve['wall_sec'],
        reduction_percent=100*(1-solve['wall_sec']/baseline['wall_sec']),decision_150s_target_met=solve['wall_sec']<=150,
        before_rollouts=baseline['query']['total_rollouts'],after_rollouts=q['total_rollouts'],
        iteration_context=solve['iteration_context'],candidates=selection['candidates'],
        batch_times=[row for row in events if row['stage']=='sdmpc_surrogate_batch_done'],
        used_derivative_max_differences=differences,
        selected_physical_commands_equal=solve['response']['command_evidence']['ordered_rows']==baseline['response']['command_evidence']['ordered_rows'],
        selected_control_equal=solve['response']['control']==baseline['response']['control'],
        exact_model_audit_feasible=audit['exact_model_feasible'],exact_selected_cost=audit['selected_exact_cost'],
        exact_held_cost=audit['held_exact_cost'],surrogate_selected_cost=selection['selected_objective'],
        surrogate_held_cost=selection['held_objective'],rollout_breakdown=q,
        native_applied=False,native9000_completed=False,adopted_default=False,
        timing_scope='One measurement per whole solve; max two outer iterations per NP candidate, selected accepted two, not converged.')
    paths=['evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent_surrogate.py',
        'diagnostics/test_sdmpc_initial_shared.py','diagnostics/check_sdmpc_reverse.py',
        'diagnostics/check_sdmpc_full_decision.py','diagnostics/audit_sdmpc_surrogate.py',
        'diagnostics/finalize_sdmpc_initial_shared.py','docs/SDMPC_INITIAL_SHARED_20260922.md']
    manifest={}
    for name in paths:
        source=ROOT/name;target=folder/'final_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    result['source_sha256']=manifest
    with (folder/'summary.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rollout_breakdown','source_sha256')},indent=2))
    return 0 if result['implementation_checks_all_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
