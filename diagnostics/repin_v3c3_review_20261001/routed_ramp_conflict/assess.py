"""Compare the six bounded autonomous forecasts with saved native evidence."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parents[1]
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
C = R/'sc1001_connection'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    target = HERE/'assessment.json'
    if target.exists():
        raise FileExistsError(target)
    spec = importlib.util.spec_from_file_location('old_scorer', R/'sc1001_route_inventory_s47/assess.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    actual43 = read(R/'sc1001_route_inventory_s43/comparison.json')
    actual47 = read(R/'sc1001_route_inventory_s47/assessment.json')
    config = read(C/'candidate_route_inventory.json')
    config_hash = PINS[str(C/'candidate_route_inventory.json')]
    report = {}
    runtime_sec = 0.
    for seed, start, pairs in ((43, 2250, (('nc','held_actual'),('rm','rm'),('vsl','vsl'),('both','both'))),
                              (47, 2700, (('hold','held_actual'),('release','release_actual')))):
        old = read(I/f'closedloop_recorded{start}_lever450_sc1001_routed_history_s{seed}/summary.json')
        new = read(I/f'closedloop_recorded{start}_lever450_routed_gap{seed}_v1/summary.json')
        receipt = read(C/f'routed_gap{seed}_v1.json')
        assert receipt['candidate_config_sha256'] == config_hash
        cases = {}
        max_route = max_resource = max_ramp = 0.
        for index, (arm,key) in enumerate(pairs):
            a, b = old['results'][key], new['results'][key]
            assert a['commands'] == b['commands']
            assert a['physical_cell_states'][0] == b['physical_cell_states'][0]
            assert b['validation']['all_actuator_and_step_constraints_checked']
            runtime_sec += b['wall_sec']
            trace = read(C/f'routed_gap{seed}_v1_response_{index}.json.gz')
            previous = read(C/f'sc1001_routed_history_s{seed}_response_{index}.json.gz')
            assert trace['route_inventory_checks'][0] == previous['route_inventory_checks'][0]
            assert len(trace['quantities']['owners']) == 17
            max_resource = max(max_resource, trace['resource_max_exceedance'])
            for state in trace['route_inventory_checks']:
                max_route = max(max_route, max(x['max_cell_residual'] for x in state['roads'].values()))
            max_ramp = max(max_ramp, max(abs(x['residual']) for x in b['ramps'].values()))
            cases[arm] = dict(before=scorer.summarize(a), after=scorer.summarize(b),
                              ramp10681_before=a['ramps']['RM_C10681'],
                              ramp10681_after=b['ramps']['RM_C10681'])
        assert max(max_route,max_resource,max_ramp) < 1e-7
        ref = pairs[0][0]
        deltas = {arm: {mode: {k: row[mode][k]-cases[ref][mode][k] for k in row[mode]}
                       for mode in ('before','after')} for arm,row in cases.items() if arm != ref}
        for arm,d in deltas.items():
            d['native'] = (dict(omega=actual43['costs'][arm]['delta_vs_nc']['native_omega_veh_h'])
                           if seed == 43 else actual47['release_minus_hold']['native'])
        report[seed] = dict(cases=cases,deltas=deltas,
                           max_route_mass_residual_veh=max_route,
                           max_ramp_mass_residual_veh=max_ramp,
                           max_resource_exceedance_veh=max_resource)
        if seed == 43:
            report[seed]['rank'] = {mode: sorted(cases,key=lambda a:cases[a][mode]['omega'])
                                    for mode in ('before','after')}
            report[seed]['rank']['native'] = actual43['omega_rank']['native']
    source = ROOT/'evaluation/controllers/lane_ramp_runtime.py'
    PINS[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
    result = dict(status='CONSISTENCY_FIX_PASSES_BUT_GAIN_NOT_QUALIFIED',
                  forecasts=6,forecast_wall_seconds_sum=runtime_sec,optimizer_iterations=0,
                  new_native_runs=0,fzp_reads=0,coefficient_fit=0,autonomous=True,
                  future_native_inputs=False,default_route_option_enabled=False,
                  tests=dict(targeted_passed=5,existing_suite_passed=12,
                             existing_suite_missing_fixture_methods=9,
                             existing_suite_failure_or_error_events=11,existing_suite_all_passed=False),
                  seeds=report,source_pins=PINS,
                  limitations=['Historical before forecasts reused; no new VISSIM or independent seed.',
                               'Route sending is a demand-side conflicting-flow proxy, not accepted downstream flow.',
                               'Gap coefficients and lane mapping unchanged; routed AD/optimizer qualification not performed.',
                               'Current default SC105 candidate remains nonrouted and unchanged.',
                               'Native phase and total-network cost coverage limitations remain from source reports.'])
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],seconds=runtime_sec,
                         deltas={s:v['deltas'] for s,v in report.items()}),ensure_ascii=False))


if __name__ == '__main__':
    main()
