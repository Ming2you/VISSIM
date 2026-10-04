"""Horizon diagnostic from completed caches only; no model/FZP/native execution."""
import bisect
import csv
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
ROOT = R.parents[1]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def native_integral(path):
    PINS[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    ts = [float(r['sim_sec']) for r in rows]
    ns = [float(r['inside_vehicles']) for r in rows]
    cs = [float(r['ttt_veh_h_cumulative']) for r in rows]
    assert all(a < b for a, b in zip(ts, ts[1:]))
    for k in range(1, len(rows)):
        expected = (ns[k-1] + ns[k]) * .5 * (ts[k]-ts[k-1]) / 3600
        assert abs(cs[k]-cs[k-1]-expected) < 1e-8, (path, k)

    def at(t):
        k = bisect.bisect_right(ts, t) - 1
        assert 0 <= k < len(ts) and t <= ts[-1]
        if t == ts[k]:
            return cs[k]
        dt = ts[k+1]-ts[k]
        d = t-ts[k]
        return cs[k] + (ns[k]*d + .5*(ns[k+1]-ns[k])*d*d/dt)/3600
    return at


models = {}
specs = [
    (67, 'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent_trace81_path',
     's67_full_observation', {'release': 'release_actual', 'release_vsl90': 'release_vsl90_actual'}),
    (67, 'closedloop_recorded2700_budget_check_selected_vsl13_s67_response81',
     's67_selected_vsl78', {'selected': 'selected', 'vsl90': 'vsl90'}),
    (73, 'closedloop_recorded2700_lever450_s73_replication95',
     'replication_s73_95', {'release': 'release_actual', 'release_vsl90': 'release_vsl90_actual'}),
]
intervals = []
for seed, folder, native_folder, arms in specs:
    summary = read(I / folder / 'summary.json')
    for arm, key in arms.items():
        result = summary['results'][key]
        result = result.get('execution', result)
        blocks = result['executed_intervals']
        assert len(blocks) == 3
        assert abs(sum(b['ttt_omega_veh_h'] for b in blocks)-result['ttt_omega_veh_h']) < 1e-7
        models[(seed, arm)] = result
        integral = native_integral(R / native_folder / 'analysis' / arm / 'area_timeseries.csv')
        for b in blocks:
            assert b.get('future_observation_inputs', False) is False
            start, end = b['start_sec'], b['end_sec']
            assert end-start == 150
            actual = integral(end)-integral(start)
            predicted = b['ttt_omega_veh_h']
            intervals.append(dict(seed=seed, arm=arm, start_sec=start, end_sec=end,
                lead_start_sec=start-2700, lead_end_sec=end-2700,
                actual_ttt_veh_h=actual, predicted_ttt_veh_h=predicted,
                error_veh_h=predicted-actual, error_percent=100*(predicted-actual)/actual))

cells = []
for row in read(R / 's67_policy_response81/cell_errors.json'):
    cells.append(dict(seed=67, arm=row['case'], lead_sec=row['time_sec']-2700,
        cell=row['cell'], actual_stock=row['observed_stock'], predicted_stock=row['predicted_stock'],
        actual_speed=row['observed_speed_kmh'], predicted_speed=row['predicted_speed_kmh']))
for row in read(R / 'independent_s71_84/flow_assessment.json')['snapshots']:
    if row['road'] == 'FW_E' and row['time_sec'] > 2250:
        cells.append(dict(seed=71, arm=row['arm'], lead_sec=row['time_sec']-2250,
            cell=row['cell'], actual_stock=row['native_stock'], predicted_stock=row['predicted_stock'],
            actual_speed=row['native_speed_kmh'], predicted_speed=row['predicted_speed_kmh']))
for row in read(R / 'replication_s73_95/snapshot_errors95.json'):
    if row['time_sec'] <= 2700:
        continue
    state = next(b['physical_cell_states'][-1] for b in models[(73, row['arm'])]['executed_intervals']
                 if b['end_sec'] == row['time_sec'])
    assert abs(state['speed_kmh']['FW_E'][row['cell']]-row['predicted_speed_kmh']) < 1e-9
    cells.append(dict(seed=73, arm=row['arm'], lead_sec=row['time_sec']-2700,
        cell=row['cell'], actual_stock=row['actual_stock'],
        predicted_stock=state['vehicle_count']['FW_E'][row['cell']],
        actual_speed=row['actual_speed_kmh'], predicted_speed=row['predicted_speed_kmh']))
assert len(cells) == 930 and len({(r['seed'], r['arm']) for r in cells}) == 10
assert len({(r['seed'], r['arm'], r['lead_sec'], r['cell']) for r in cells}) == len(cells)

endpoint = []
for seed, arm in sorted({(r['seed'], r['arm']) for r in cells}):
    for lead in (150, 300, 450):
        subset = [r for r in cells if (r['seed'], r['arm'], r['lead_sec']) == (seed, arm, lead)]
        assert len(subset) == 31
        occupied = [r for r in subset if r['actual_stock'] > 0 and r['actual_speed'] is not None]
        errors = [r['predicted_speed']-r['actual_speed'] for r in occupied]
        endpoint.append(dict(seed=seed, arm=arm, lead_sec=lead, occupied_cells=len(occupied),
            speed_mae_kmh=statistics.mean(abs(e) for e in errors),
            speed_bias_kmh=statistics.mean(errors),
            vehicle_weighted_speed_mae_kmh=sum(abs(r['predicted_speed']-r['actual_speed'])*r['actual_stock']
                for r in occupied)/sum(r['actual_stock'] for r in occupied),
            stock_mae_veh_per_cell=statistics.mean(abs(r['predicted_stock']-r['actual_stock']) for r in subset),
            east_total_stock_error_veh=sum(r['predicted_stock']-r['actual_stock'] for r in subset)))

by_seed = []
for seed in (67, 71, 73):
    for lead in (150, 300, 450):
        subset = [r for r in endpoint if (r['seed'], r['lead_sec']) == (seed, lead)]
        by_seed.append(dict(seed=seed, lead_sec=lead, arms=len(subset), **{
            k: statistics.mean(r[k] for r in subset) for k in
            ('speed_mae_kmh', 'vehicle_weighted_speed_mae_kmh', 'stock_mae_veh_per_cell')}))
aggregate = []
for lead in (150, 300, 450):
    e = [r for r in endpoint if r['lead_sec'] == lead]
    ts = [r for r in intervals if r['lead_end_sec'] == lead]
    aggregate.append(dict(lead_sec=lead, arms=len(e),
        speed_mae_kmh=statistics.mean(r['speed_mae_kmh'] for r in e),
        speed_mae_min_kmh=min(r['speed_mae_kmh'] for r in e),
        speed_mae_max_kmh=max(r['speed_mae_kmh'] for r in e),
        vehicle_weighted_speed_mae_kmh=statistics.mean(r['vehicle_weighted_speed_mae_kmh'] for r in e),
        stock_mae_veh_per_cell=statistics.mean(r['stock_mae_veh_per_cell'] for r in e),
        ttt_interval_arms=len(ts), ttt_interval_mape_percent=statistics.mean(abs(r['error_percent']) for r in ts),
        ttt_interval_mean_signed_error_percent=statistics.mean(r['error_percent'] for r in ts)))
monotonic = []
for seed, arm in sorted({(r['seed'], r['arm']) for r in endpoint}):
    es = sorted((r for r in endpoint if (r['seed'], r['arm']) == (seed, arm)), key=lambda r:r['lead_sec'])
    monotonic.append(dict(seed=seed, arm=arm,
        speed_monotonic_increase=all(a['speed_mae_kmh'] < b['speed_mae_kmh'] for a,b in zip(es,es[1:])),
        stock_monotonic_increase=all(a['stock_mae_veh_per_cell'] < b['stock_mae_veh_per_cell'] for a,b in zip(es,es[1:])),
        speed450_above150=es[-1]['speed_mae_kmh'] > es[0]['speed_mae_kmh']))
pair_intervals = []
for seed, left, right in [(67,'release','release_vsl90'),(67,'selected','vsl90'),(73,'release','release_vsl90')]:
    for lead in (150,300,450):
        a = next(r for r in intervals if (r['seed'],r['arm'],r['lead_end_sec']) == (seed,left,lead))
        b = next(r for r in intervals if (r['seed'],r['arm'],r['lead_end_sec']) == (seed,right,lead))
        pair_intervals.append(dict(seed=seed, reference=left, candidate=right, lead_end_sec=lead,
            actual_delta_ttt_veh_h=b['actual_ttt_veh_h']-a['actual_ttt_veh_h'],
            predicted_delta_ttt_veh_h=b['predicted_ttt_veh_h']-a['predicted_ttt_veh_h']))

report = dict(status='COMPLETED_CACHE_ONLY_HORIZON_DIAGNOSTIC',
    definition='Endpoint east 31-cell speed MAE (occupied native cells only), stock MAE (all31); TTT is separate disjoint150s Omega residence, six arms with recorded interval ledger.',
    scope='10 arms, seeds67/71/73, three initial states; correlated policy arms are not10 independent replications. All are predictions conditioned on executed commands without future traffic observations. No new forecast/native/FZP scan/fitting.',
    limitation='Endpoint errors do not equal average error within first150s; seed71 interval-TTT ledger unavailable in inspected cache and excluded from TTT summary. Native5s stock trapezoid (held last4.9s) versus model integration retained.',
    aggregate=aggregate, by_seed=by_seed, endpoints=endpoint, intervals=intervals,
    pair_intervals=pair_intervals, monotonic_cases=monotonic,
    first150_largest_cell_errors=sorted([r for r in cells if r['lead_sec']==150 and r['actual_stock']>0],
        key=lambda r: abs(r['predicted_speed']-r['actual_speed']), reverse=True)[:15],
    source_sha256=PINS)
(HERE / 'assessment.json').write_text(json.dumps(report, indent=2, allow_nan=False),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('aggregate','by_seed','pair_intervals','monotonic_cases')},indent=2))
