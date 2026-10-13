"""Compare one completed 1+1 search with the retained 2+2 search; no rollout."""
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('retained_compare',
    HERE.parent/'runtime_pair2400_numericfix/compare.py')
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)
read = cmp.read


def main():
    output = HERE/'bounded_full_comparison.json'
    assert not output.exists(), 'Preserve completed comparison'
    plan = read(HERE/'bounded_full_benchmark_plan.json')
    assert plan['status'] == 'complete_pending_quality_and_time_comparison'
    assert plan['launches_consumed'] == 1
    for name, digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    before = read(HERE/'hot_full_comparison.json')['runs']['hot_lazy']
    after = cmp.inspect(HERE/'bounded_full', read(HERE/'bounded_full.execution.json'))
    policies = [deepcopy(x['policy']) for x in (before, after)]
    assert policies[0]['max_iterations'] == policies[0]['pfo_cap_options']['max_iterations'] == 2
    assert policies[1]['max_iterations'] == policies[1]['pfo_cap_options']['max_iterations'] == 1
    policies[1]['max_iterations'] = 2
    policies[1]['pfo_cap_options']['max_iterations'] = 2
    assert not cmp.difference(*policies), 'Unexpected search or physical policy change'
    a, b = [x['costs_and_constraints'] for x in (before, after)]
    assert abs(a['held_objective']-b['held_objective']) < 1e-7, 'Not a common physical initial command'
    delta = b['selected_objective']-a['selected_objective']
    fraction = delta/a['selected_objective']
    quality = b['selected_objective'] < b['held_objective'] and fraction <= plan['quality_gate']['selected_omega_ttt_within_baseline_fraction']
    timing = after['external_process_wall_sec'] <= plan['quality_gate']['full_process_seconds_max']
    result = dict(status='complete_comparison', quality_gate_pass=quality,
        full_time_target_met=timing, quality_and_time_pass=quality and timing,
        common_held_omega_veh_h=b['held_objective'],
        before_selected_omega_veh_h=a['selected_objective'],
        after_selected_omega_veh_h=b['selected_objective'],
        difference_selected_omega_veh_h=delta, difference_selected_percent=100*fraction,
        process_wall_before_sec=before['external_process_wall_sec'],
        process_wall_after_sec=after['external_process_wall_sec'],
        pfo_iterations_before=before['pfo_iterations'], pfo_iterations_after=after['pfo_iterations'],
        baseline_query_stats=before['query_stats'], candidate_query_stats=after['query_stats'],
        owner_costs_before=a['omega_partition']['costs'], owner_costs_after=b['omega_partition']['costs'],
        rm_before=before['selected_rm_by_block'], rm_after=after['selected_rm_by_block'],
        actuator_differences=cmp.difference(before['action_blocks'], after['action_blocks']),
        final_constraints=after['costs_and_constraints']['final_constraints'],
        candidate_run=after, new_predictions=0, native_runs=0,
        limitations=['Changed PFO and coordination iteration limits, not exact search equivalence.',
            'PFO-derived numeric NP/NUF budgets may change; initialization rule and physical constraints are unchanged.',
            'One saved2400s state with recorded competing workload; no native traffic benefit or convergence claim.'])
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','quality_gate_pass','full_time_target_met',
        'process_wall_after_sec','difference_selected_omega_veh_h','difference_selected_percent','candidate_query_stats')}))


if __name__ == '__main__':
    main()
