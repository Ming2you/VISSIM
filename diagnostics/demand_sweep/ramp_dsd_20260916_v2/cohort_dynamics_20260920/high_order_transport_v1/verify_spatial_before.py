"""Read-only checks of delivered local transport records; no forecast/native run."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def close(a, b):
    assert math.isfinite(a) and math.isfinite(b) and abs(a-b) < 1e-8, (a, b)


def main():
    snapshots = [K / p for p in (
        'downstream_spatial_rollout_v1/source_before_calibration.txt',
        'downstream_spatial_calibration_v3/source_before_moment_transport.txt',
        'downstream_spatial_horizon_v1/source_before_boundary_probe.txt')]
    pins = 0
    for folder in ('paired_native_interaction_v1', 'downstream_spatial_rollout_v1',
                   'downstream_spatial_calibration_v3', 'downstream_spatial_moment_calibration_v1',
                   'local_interaction_spatial_validation_v1', 'downstream_spatial_horizon_v1',
                   'downstream_boundary_probe_v1'):
        for name, digest in load(K / folder / 'result.json')['source_pins'].items():
            p = ROOT / name
            candidates = [p] + (snapshots if p.name == 'downstream_spatial_rollout.py' else [])
            assert any(hashlib.sha256(v.read_bytes()).hexdigest() == digest for v in candidates), name
            pins += 1
    old = load(K / 'local_interaction_spatial_validation_v1/result.json')
    assert old['passed'] and old['original_traces_exact'] == 24 and old['fitted_traces_exact'] == 8
    pair = load(K / 'paired_native_interaction_v1/result.json')
    exposure = load(K / 'paired_native_interaction_v1/exposure.json')
    for target in pair['by_target']:
        for arm, saved in target['arms'].items():
            rows = [r for r in exposure if r['target'] == target['target'] and r['arm'] == arm]
            assert sorted({r['vehicle'] for r in rows}) == saved['subjects']
            assert len(rows) == saved['samples']
            assert sum(r['interaction'].startswith('Brake') for r in rows) == saved['brake_samples']
            close(sum(max(0., -r['delta_speed_kmh']) for r in rows), saved['actual_decel_kmh'])
    obs = load(K / 'compact_lane_state_v1/states.json')
    inputs = load(K / 'downstream_spatial_rollout_v1/inputs.json')
    horizon = load(K / 'downstream_spatial_horizon_v1/result.json')
    probe = load(K / 'downstream_boundary_probe_v1/result.json')
    boundaries = load(K / 'downstream_boundary_probe_v1/boundaries.json')
    assert horizon['qualified'] is False and probe['qualified'] is False
    assert not horizon['future_inputs_to_model'] and probe['status'] == 'FUTURE_BOUNDARY_ISOLATION_ONLY'
    prefixes = entry_checks = continuity = 0
    for saved in probe['runs']:
        arm, start, mode, kind = (saved[k] for k in ('arm', 'start', 'mode', 'kind'))
        key = f'{arm}_{start}_{mode}'
        initial = inputs[key]['inputs']
        folder = 'downstream_spatial_horizon_v1' if kind == 'history' else 'downstream_boundary_probe_v1'
        name = key if kind == 'history' else key + '_' + kind
        trace = load(K / folder / (name + '.json'))
        assert [r['step'] for r in trace] == list(range(1, 151))
        if kind == 'history':
            prefix = (K / 'downstream_spatial_rollout_v1' / (key + '.json') if mode == 'coarse'
                      else K / 'local_interaction_spatial_validation_v1' / (key + '_moment_only.json'))
            assert trace[:30] == load(prefix)
            prefixes += 1
            sequences = [dict(arrivals=initial['arrivals'])] * 150
        else:
            sequences = boundaries[name]['sequence']
            events = Counter(r['time_s'] for r in boundaries[name]['events'])
            assert len(sequences) == 150
            for j, row in enumerate(sequences):
                close(sum(row['arrivals']), obs[arm]['entry'][str(start+j+1)])
                close(sum(row['arrivals']), events[start+j+1])
                entry_checks += 1
        stock0 = sum(map(sum, initial['n']))
        requested = predicted = actual = 0.
        speed_errors, stock_errors = [], []
        for row, boundary in zip(trace, sequences):
            requested += sum(boundary['arrivals'])
            assert row['queue'] >= -1e-9
            close(sum(c['n'] for c in row['cells'].values()) + row['queue'] + row['exits'], stock0 + requested)
            continuity += 1
            for c, value in row['cells'].items():
                assert value['n'] >= -1e-9 and value['v'] >= 0
                observed = obs[arm]['states'][str(start+row['step'])][c]
                predicted += value['n']/3600
                actual += observed['n']/3600
                speed_errors.append(value['v']-observed['v'])
                stock_errors.append(value['n']-observed['n'])
        close(predicted, saved['predicted_ttt'])
        close(actual, saved['actual_ttt'])
        close(math.sqrt(sum(e*e for e in speed_errors)/len(speed_errors)), saved['speed_rmse'])
        close(sum(speed_errors)/len(speed_errors), saved['speed_bias'])
        close(sum(abs(e) for e in stock_errors)/len(stock_errors), saved['stock_mae'])
        close(max(r['queue'] for r in trace), saved['max_queue'])
        if kind == 'observed_boundary':
            assert saved['max_queue'] < 1e-9  # No unsupported queued entry-speed moment.
        if kind == 'history':
            h = next(r for r in horizon['runs'] if (r['arm'], r['start'], r['mode']) == (arm, start, mode))
            close(predicted, h['intervals'][-1]['predicted_local_ttt'])
            close(actual, h['intervals'][-1]['actual_local_ttt'])
            close(saved['speed_rmse'], h['intervals'][-1]['speed_rmse'])
    for row in probe['response']:
        select = lambda arm: next(r for r in probe['runs'] if all(r[k] == row[k] for k in ('start', 'mode', 'kind')) and r['arm'] == arm)
        a, b = select('none'), select('rm_ramp')
        close(b['predicted_ttt']-a['predicted_ttt'], row['predicted_delta_ttt'])
        close(b['actual_ttt']-a['actual_ttt'], row['actual_delta_ttt'])
    print(json.dumps(dict(passed=True, source_pins_checked=pins, prefixes_exact=prefixes,
        local_traces_checked=len(probe['runs']), continuity_steps=continuity,
        observed_boundary_counts_checked=entry_checks, new_forecasts=0, new_native_runs=0,
        qualified=False, note='Saved-record and delivery checks; gain calibration remains incomplete.')))


if __name__ == '__main__':
    main()
