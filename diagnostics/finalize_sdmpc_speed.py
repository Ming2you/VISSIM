"""Compare completed speed work to the previous full offline decision."""
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
    folder=ROOT/'diagnostics/sdmpc_speed_20260922'
    base=pickle.loads((ROOT/'diagnostics/sdmpc_reverse_20260921/full_decision_v2/result.pickle').read_bytes())
    current=pickle.loads((folder/'full_decision_v1/result.pickle').read_bytes())
    prior,new=base['selection'],current['selection']
    jac=json.loads((folder/'fast_h3_v3/comparison.json').read_text())
    reuse=json.loads((folder/'reuse_eight_v1/report.json').read_text())
    sequence=current['response']['control_sequence']
    old_command=base['response']['command_evidence']
    new_command=current['response']['command_evidence']
    command_fields=('ordered_rows','physical_rows','owner_physical_sha256',
                    'owner_model_vectors','owner_model_sha256')
    changed_provenance=[k for k in old_command['provenance'].keys()|new_command['provenance'].keys()
                        if old_command['provenance'].get(k)!=new_command['provenance'].get(k)]
    matrices=[]
    for a,b in zip(prior['tangent_derivatives'],new['tangent_derivatives']):
        matrices.append({k:float(np.max(abs(np.asarray(a[k])-np.asarray(b[k]))))
                         for k in ('costs','resources','cost_jacobian','resource_jacobian')})
    checks=dict(completed=current['completed'],feasible=current['response']['feasible'],
        no_source_changes=not current['source_changes'],
        current_sources_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
                                    for p,h in current['source_sha256'].items()),
        jacobian_qualified=jac['pass_all'],response_reuse_qualified=reuse['pass_all'],
        final_action_exact=(vars(base['response']['control'])==vars(current['response']['control'])),
        physical_commands_exact=all(old_command[k]==new_command[k] for k in command_fields),
        command_provenance_only_source_identity_changed=(set(changed_provenance)<=
                                                       {'binding_sha256','context_fingerprint'}),
        candidate_outcomes_exact=prior['candidates']==new['candidates'],
        quantity_constraints_exact=prior['final_constraints']==new['final_constraints'],
        cost_exact=prior['selected_objective']==new['selected_objective'],
        all_jacobians_match=(len(prior['tangent_derivatives'])==len(new['tangent_derivatives'])
            and bool(matrices) and all(max(m.values())<=1e-7 for m in matrices)),
        full_states_match=all(r['complete_primal_state_match'] and not r['fallback_reasons']
                             and len(r['ad_axes'])==231 for r in new['tangent_derivatives']),
        first_block_only=(sequence['blocks']==3 and sequence['applied_block']==0
                          and sequence['all_actuator_and_step_constraints_checked']),
        workers_closed=current['query']['closed'] and not current['query']['owned_workers_alive'])
    report=dict(scope=__doc__,native_applied=False,checks=checks,pass_all=all(checks.values()),
        before_sec=base['wall_sec'],after_sec=current['wall_sec'],
        reduction_percent=100*(1-current['wall_sec']/base['wall_sec']),
        decision_150s_target_met=current['wall_sec']<=150,
        derivative_sec=[r['wall_sec_including_spawn'] for r in new['tangent_derivatives']],
        derivative_matrix_errors=matrices,query_wall_sec=current['query']['query_wall_sec'],
        changed_command_provenance=changed_provenance,
        query_predictions=current['query']['endpoint_calls'],
        cache=new.get('physical_response_cache'),candidates=new['candidates'],
        held_model_ttt=new['held_objective'],selected_model_ttt=new['selected_objective'],
        final_constraints=new['final_constraints'],converged=new['converged'])
    (folder/'qualification_summary.json').write_text(json.dumps(json_records(report),indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('cache','final_constraints')},indent=2))
    return 0 if report['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
