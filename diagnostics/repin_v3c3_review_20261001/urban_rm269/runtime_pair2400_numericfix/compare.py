"""Inspect two completed full selections; no optimizer, forecast or native run."""
from pathlib import Path
from copy import deepcopy
import csv
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
KEY = 'sdmpc_prediction_sequence'
FIELDS = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
          'offsets', 'inflow_outflow_allocation', 'diagnostics')


def read(path):
    return json.loads(path.read_bytes())


def difference(a, b, path='', *, atol=1e-7):
    """Return all semantic differences, without discarding small cap violations."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            where = path+'/'+str(key)
            if key not in a or key not in b:
                out.append(dict(path=where, reason='missing key'))
            else:
                out.extend(difference(a[key], b[key], where, atol=atol))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [dict(path=path, reason='different lengths')]
        return [item for i, (x, y) in enumerate(zip(a, b))
                for item in difference(x, y, path+'/'+str(i), atol=atol)]
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        if math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=atol):
            return []
    elif type(a) is type(b) and a == b:
        return []
    return [dict(path=path, off=a, on=b)]


def blocks(action):
    first = {k:deepcopy(action[k]) for k in FIELDS}
    sequence = first['diagnostics'].pop(KEY)
    assert sequence['schema'] == 'sdmpc-sequence/v1' and len(sequence['future']) == 2
    result = [first]
    for future in sequence['future']:
        block = {k:deepcopy(future[k]) for k in FIELDS}
        assert KEY not in block['diagnostics']
        block['N_P_star'], block['N_UF_star'] = first['N_P_star'], first['N_UF_star']
        result.append(block)
    return result


def physical_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as file:
        return [{k:v for k,v in row.items() if k != 'metadata'} for row in csv.DictReader(file)]


def inspect(directory, execution):
    done = read(directory/'completion.json')
    assert done['status'] == 'complete' and done['full_selection'] and not done['native_execution']
    assert execution['status'] == 'complete_uncompared' and execution['exit_code'] == 0
    joint = read(directory/'unused.joint.json')
    selection = joint['selection']
    assert joint['completed'] and selection['feasible'] and selection['final_constraints']['feasible']
    assert selection['control_sequence']['blocks'] == 3
    assert selection['control_sequence']['all_actuator_and_step_constraints_checked']
    assert selection['finite_neighbor_audit_performed']
    query = selection['surrogate_query']
    assert query['failed_batches'] == 0 and query['failed_predictions_with_unknown_rollout_count'] == 0
    assert abs(sum(selection['omega_partition']['costs'].values())-selection['selected_objective']) < 1e-7
    action, reference = read(directory/'unused.json'), read(directory/'reference.json')
    plan = blocks(action)
    for block in plan:
        for key, green in block['diagnostics'].items():
            if key.startswith('rw_meter_green_'):
                assert 2 <= green <= 10
    costs = {k:selection[k] for k in ('held_objective', 'selected_objective', 'omega_partition', 'final_constraints')}
    counts = {k:query[k] for k in ('requests', 'cache_hits', 'scalar_rollouts', 'tangent_rollouts', 'total_rollouts', 'endpoint_calls', 'failed_batches')}
    audit = selection['meter_neighbor_audit']
    return dict(action_blocks=plan, first_physical_csv=physical_csv(directory/'unused.csv'),
        costs_and_constraints=costs,
        converged=selection['converged'], selection_status=selection['selection_status'],
        query_stats=counts, query_rows=query['rows'], policy=selection['policy'],
        external_process_wall_sec=execution['external_process_wall_sec'],
        decision_wall_sec=joint['decision_budget']['wall_sec'],
        pfo_seconds=selection['pfo_warm_start']['seconds'],
        pfo_iterations=selection['pfo_warm_start']['executed_iterations'],
        sdmpc_after_pfo_seconds=selection['sdmpc_after_pfo_seconds'],
        meter_audit=audit,
        held_rm={k:v for k,v in reference['diagnostics'].items() if k.startswith('rw_meter_green_')},
        selected_rm_by_block=[{k:v for k,v in b['diagnostics'].items() if k.startswith('rw_meter_green_')} for b in plan])


def main():
    target = HERE/'comparison.json'
    assert not target.exists(), 'Preserve completed comparison'
    plan = read(HERE/'plan.json')
    assert plan['status'] == 'both_complete_equivalence_pending' and plan['launches_consumed'] == 2
    for name, digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    results = {mode:inspect(HERE/mode, read(HERE/(mode+'.execution.json')))
               for mode in ('cache_off', 'cache_on')}
    off, on = results.values()
    assert not off['policy']['response_cap_cache'] and on['policy']['response_cap_cache']
    policies = [deepcopy(x['policy']) for x in (off, on)]
    for policy in policies:
        policy.pop('response_cap_cache')
    comparisons = {
        'same_search_budget_and_policy': difference(*policies),
        'three_blocks': difference(off['action_blocks'], on['action_blocks']),
        'native_first_block_writer': difference(off['first_physical_csv'], on['first_physical_csv'], atol=0),
        'costs_owners_and_constraints': difference(off['costs_and_constraints'], on['costs_and_constraints']),
    }
    equivalent = not any(comparisons.values())
    result = dict(status='equivalent' if equivalent else 'differences_require_review',
        comparisons=comparisons, runs=results,
        speedup_ratio=off['external_process_wall_sec']/on['external_process_wall_sec'],
        process_wall_reduction_percent=100*(1-on['external_process_wall_sec']/off['external_process_wall_sec']),
        new_predictions=0, new_native_runs=0, objective='Omega701 TTT', horizon_sec=450,
        terminal_cost=False, at_sec=2400, comparison_repeats=1,
        limits=['One full decision per mode under recorded competing workload; no statistical or full9000s speedup claim.',
                'All three commands checked, but only block0 was written; no native replay in this benchmark.',
                'Nonconverged selections are best observed feasible commands, not proven optima.',
                'Nearly zero isolated native RM net cost was not fitted; complete controller gain remains a model prediction.'])
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','speedup_ratio','process_wall_reduction_percent')}))


if __name__ == '__main__':
    main()
