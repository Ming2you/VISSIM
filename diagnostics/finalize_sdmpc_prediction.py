"""Final frozen-state and whole-decision traffic prediction qualification."""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.sdmpc_json_records import json_records


def main():
    folder=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'diagnostics/sdmpc_prediction_20260922'
    baseline=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'diagnostics/sdmpc_speed_20260922/full_decision_v1'
    jacobian_folder=sys.argv[3] if len(sys.argv)>3 else 'cached_h3_v2'
    base=pickle.loads((baseline/'result.pickle').read_bytes())
    current=pickle.loads((folder/'full_decision_v1/result.pickle').read_bytes())
    prior,new=base['selection'],current['selection']
    jac=json.loads((folder/jacobian_folder/'comparison.json').read_text())
    states_folder=sys.argv[4] if len(sys.argv)>4 else 'states_v1'
    states=json.loads((folder/states_folder/'comparison.json').read_text())
    old_command,new_command=[r['response']['command_evidence'] for r in (base,current)]
    fields=('ordered_rows','physical_rows','owner_physical_sha256','owner_model_vectors','owner_model_sha256')
    changed=[k for k in old_command['provenance'].keys()|new_command['provenance'].keys()
             if old_command['provenance'].get(k)!=new_command['provenance'].get(k)]
    matrices=[{k:float(np.max(abs(np.asarray(a[k])-np.asarray(b[k]))))
        for k in ('costs','resources','cost_jacobian','resource_jacobian')}
        for a,b in zip(prior['tangent_derivatives'],new['tangent_derivatives'])]
    sequence=current['response']['control_sequence']
    option=states.get('option','prediction_cache')
    old_policy,new_policy=[dict(r['policy']) for r in (base,current)]
    prior_enabled=[old_policy.pop(name,False) for name in option.split(',')]
    current_enabled=[new_policy.pop(name,False) for name in option.split(',')]
    checks=dict(completed=current['completed'],baseline_completed=base['completed'],
        only_tested_policy_changed=old_policy==new_policy and all(v is False for v in prior_enabled)
            and all(v is True for v in current_enabled),
        same_saved_time=base['sim_sec']==current['sim_sec'],feasible=current['response']['feasible'],
        no_source_changes=not current['source_changes'],
        current_sources_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
                                    for p,h in current['source_sha256'].items()),
        jacobian_qualified=jac['pass_all'],cache_on_off_full_states_exact=states['pass_all'],
        final_action_exact=vars(base['response']['control'])==vars(current['response']['control']),
        physical_commands_exact=all(old_command[k]==new_command[k] for k in fields),
        only_source_provenance_changed=set(changed)<={'binding_sha256','context_fingerprint'},
        candidate_outcomes_exact=prior['candidates']==new['candidates'],
        quantity_constraints_exact=prior['final_constraints']==new['final_constraints'],
        cost_exact=prior['selected_objective']==new['selected_objective'],
        all_jacobians_match=(len(prior['tangent_derivatives'])==len(new['tangent_derivatives'])
            and bool(matrices) and all(max(m.values())<=1e-7 for m in matrices)),
        full_states_match=all(r['complete_primal_state_match'] and not r['fallback_reasons']
            and len(r['ad_axes'])==231 for r in new['tangent_derivatives']),
        first_block_only=sequence['blocks']==3 and sequence['applied_block']==0 and sequence['all_actuator_and_step_constraints_checked'],
        workers_closed=current['query']['closed'] and not current['query']['owned_workers_alive'])
    overlaps=[r['initial_prediction_overlap'] for r in new['tangent_derivatives'] if 'initial_prediction_overlap' in r]
    if current['policy'].get('initial_derivative_overlap'):
        checks['exact_initial_overlap_used']=(len(overlaps)==1 and overlaps[0]['full_request_exact']
            and overlaps[0]['reverse_workers']==current['policy']['derivative_workers']-1
            and overlaps[0]['ordinary_hold_queries_skipped']==0)
        checks['original_prediction_count_kept']=base['query']['endpoint_calls']==current['query']['endpoint_calls']
    trial_overlaps=new.get('trial_derivative_overlaps',[])
    trial_consumed=[r['trial_prediction_overlap'] for r in new['tangent_derivatives'] if 'trial_prediction_overlap' in r]
    if current['policy'].get('trial_derivative_overlap'):
        checks['trial_overlap_owned_and_qualified']=(bool(trial_overlaps) and all(
            r['all_joined'] and r['unused_qualified'] and r['max_numerical_workers']<=8
            and r['started_derivatives']==r['consumed_derivatives']+r['unused_derivatives']
            for r in trial_overlaps))
        checks['exact_trial_overlap_used']=(bool(trial_consumed) and all(
            r['full_request_exact'] and r['ordinary_trial_queries_skipped']==0 for r in trial_consumed)
            and len(trial_consumed)==sum(r['consumed_derivatives'] for r in trial_overlaps))
    report=dict(scope=__doc__,baseline=str(baseline),option=option,
        native_applied=False,checks=checks,pass_all=all(checks.values()),initial_prediction_overlaps=overlaps,
        trial_derivative_overlaps=trial_overlaps,trial_prediction_overlaps=trial_consumed,
        before_sec=base['wall_sec'],after_sec=current['wall_sec'],
        reduction_percent=100*(1-current['wall_sec']/base['wall_sec']),
        decision_150s_target_met=current['wall_sec']<=150,
        derivative_sec=[r['wall_sec_including_spawn'] for r in new['tangent_derivatives']],
        derivative_matrix_errors=matrices,query_wall_sec=current['query']['query_wall_sec'],
        changed_command_provenance=changed,query_predictions=current['query']['endpoint_calls'],
        candidates=new['candidates'],held_model_ttt=new['held_objective'],selected_model_ttt=new['selected_objective'],
        final_constraints=new['final_constraints'],converged=new['converged'])
    (folder/'qualification_summary.json').write_text(json.dumps(json_records(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='final_constraints'},indent=2))
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
