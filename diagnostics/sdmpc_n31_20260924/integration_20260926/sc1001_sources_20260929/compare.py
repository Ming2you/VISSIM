"""Compare the completed head join candidate; no fitting or native execution."""
from pathlib import Path
from collections import defaultdict
import gzip
import hashlib
import json

HERE = Path(__file__).resolve().parent
I = HERE.parent
pins = {}

def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)

def mean_errors(rows):
    return {v: {k: sum(abs(r[v][k]-r['actual'][k]) for r in rows)/len(rows)
                for k in ('arrival', 'merge', 'final_stock')}
            for v in ('before', 'after')}

assert not (HERE/'comparison.json').exists()
prior = read(I/'direct_exit10483_20260929/comparison.json')
paths = {
    'seed43': ('closedloop_recorded2250_lever450_direct10483_enabled_s43',
               'closedloop_recorded2250_lever450_trace10484_head10119_s43_v2'),
    'seed47': ('closedloop_recorded2700_select_check_direct10483_enabled_s47_v2',
               'closedloop_recorded2700_select_check_head10119_s47'),
}
report = {}
for seed, (oldpath, newpath) in paths.items():
    old = read(I/oldpath/'summary.json')['results']
    new = read(I/newpath/'summary.json')['results']
    rows = []
    residuals = []
    for row in prior[seed]['ramps']:
        key = 'held_actual' if row['arm'] in ('nc', 'hold') else row['arm']
        assert old[key]['commands'] == new[key]['commands']
        ramp = new[key]['ramps'][row['ramp']]
        residuals.append(abs(ramp['residual']))
        assert residuals[-1] < 1e-7
        rows.append(dict(arm=row['arm'], ramp=row['ramp'], actual=row['actual'],
                         before=old[key]['ramps'][row['ramp']], after=ramp))
    costs = []
    for key, result in new.items():
        alias = result['direct_exit_final_accounting']
        assert alias['plan'] is None
        assert abs(alias['received']-alias['departed']-sum(alias['cohorts'].values())) < 1e-7
        native_delta = (next(r['native_delta'] for r in prior[seed]['costs']
                       if r['arm'] == ('nc' if key == 'held_actual' else key))
                       if seed == 'seed43' else
                       (0.0 if key == 'held_actual' else prior[seed]['native_delta']))
        costs.append(dict(case=key, native_delta_omega_veh_h=native_delta,
            before_delta_omega_veh_h=old[key]['ttt_omega_veh_h']-old['held_actual']['ttt_omega_veh_h'],
            after_delta_omega_veh_h=result['ttt_omega_veh_h']-new['held_actual']['ttt_omega_veh_h'],
            before_omega_veh_h=old[key]['ttt_omega_veh_h'],
            after_omega_veh_h=result['ttt_omega_veh_h'],
            after_tracked_outside_veh_h=result['tracked_outside_residence_veh_h']))
    runtime = read(I/newpath/'runtime.json')
    report[seed] = dict(costs=costs, ramp_mae=mean_errors(rows), ramps=rows,
        maximum_ramp_balance_residual_veh=max(residuals),
        resource_10119=runtime['head_resources']['observations']['10119'],
        capacity_10119_veh_h=runtime['metadata']['head_resource_final_rate_10119'])

transfers = {}
for label, dirname in [('before', 'closedloop_recorded2250_lever450_trace10484_source_trace_s43_v2'),
                       ('after', paths['seed43'][1])]:
    path = I/dirname/'held_actual_RM_C10484_trace.json.gz'
    data = path.read_bytes(); pins[str(path)] = hashlib.sha256(data).hexdigest()
    trace = json.loads(gzip.decompress(data))
    sums = defaultdict(float)
    for row in trace['transfers']:
        if row['stage'] == 'urban':
            sums[(row['source'], row['target'])] += row['vehicles']
    transfers[label] = [dict(source=s, target=t, vehicles=v) for (s,t),v in sums.items()]
report['urban_transfers_seed43'] = transfers
report['seed47']['native_whole_network_plus_uninserted_delta_veh_h'] = prior['seed47']['native_total_with_uninserted_delta']
report.update(new_candidate_forecasts=6, trace_only_baseline_forecasts=4,
              coefficient_fit=False, native_runs=0, future_observation_inputs=False,
              commands_unchanged=True, gain_calibration_complete=False, source_pins=pins)
(HERE/'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
print(json.dumps({k: {n:v for n,v in report[k].items() if n not in ('ramps',)}
                  for k in ('seed43','seed47')}, ensure_ascii=False))
