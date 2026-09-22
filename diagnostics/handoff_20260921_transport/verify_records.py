"""Verify delivered records without forecasts, native runs or evidence writes."""
from pathlib import Path
import contextlib
import io
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import (
    check_high_order_transport as h,
    matched_passage_response as p,
    verify_matched_cohort_outlet as c,
)
from diagnostics.handoff_20260921_matched_response.verify_records import sha, load, close

K = h.K


def main():
    # Reuse the completed cohort check while intercepting its exclusive report
    # write. Compare it to the original receipt rather than changing that file.
    reports = []
    def check_receipt(path, value):
        assert load(path) == value, str(path)
        reports.append(value)
    original_save = c.e.save
    try:
        c.e.save = check_receipt
        with contextlib.redirect_stdout(io.StringIO()):
            c.main()
    finally:
        c.e.save = original_save
    assert len(reports) == 1

    high = load(K / 'high_order_transport_v1/result.json')
    passage = load(K / 'matched_passage_response_v1/result.json')
    pins = 0
    for result in (high, passage):
        assert result['qualified'] is False and result['new_native_runs'] == 0
        for name, digest in result['source_pins'].items():
            path = ROOT / name
            candidates = [path]
            if path.name == 'downstream_spatial_rollout.py':
                candidates.append(K / 'target_acceleration_coupling_v1/source_before.py')
            assert any(sha(p) == digest for p in candidates), name
            pins += 1
    assert not high['production_adopted']
    observations = load(K / 'compact_lane_state_v1/states.json')
    inputs = load(K / 'downstream_spatial_rollout_v1/inputs.json')
    boundaries = load(K / 'downstream_boundary_probe_v1/boundaries.json')
    traces = balances = worse = 0
    for row in high['runs']:
        arm, start, kind, candidate = (row[k] for k in ('arm', 'start', 'boundary', 'reconstruction'))
        key = f'{arm}_{start}_lane_100m'
        path = (K / 'high_order_transport_v1' / f'{key}_{kind}.json' if candidate else
                K / 'downstream_spatial_horizon_v1' / f'{key}.json' if kind == 'history' else
                K / 'downstream_boundary_probe_v1' / f'{key}_observed_boundary.json')
        trace = load(path)
        assert [r['step'] for r in trace] == list(range(1, 151))
        for name, value in h.score(trace, observations, arm, start).items():
            close(value, row[name])
        initial = inputs[key]['inputs']
        stock0 = sum(map(sum, initial['n']))
        sequence = ([dict(arrivals=initial['arrivals'])] * 150 if kind == 'history' else
                    boundaries[key + '_observed_boundary']['sequence'])
        requested = 0.
        for frame, entry in zip(trace, sequence):
            requested += sum(entry['arrivals'])
            assert frame['queue'] >= -1e-9
            assert all(v['n'] >= -1e-9 and math.isfinite(v['v']) and v['v'] >= 0 for v in frame['cells'].values())
            close(sum(v['n'] for v in frame['cells'].values()) + frame['queue'] + frame['exits'], stock0 + requested)
            balances += 1
        if candidate:
            old = next(v for v in high['runs'] if not v['reconstruction'] and
                       (v['arm'], v['start'], v['boundary']) == (arm, start, kind))
            worse += row['speed_rmse'] > old['speed_rmse']
        traces += 1

    pairs = 0
    for seed, arms in passage['cases'].items():
        bank = {arm: load(K / 'matched_cohort_response_v1' / f's{seed}_{arm}.json')
                for arm in ('rm8', 'rm6', 'rm_ramp')}
        for arm, case in arms.items():
            assert len(case['pairs']) == case['matched_completed_passages']
            for row in case['pairs']:
                vid = str(row['vehicle'])
                assert bank['rm8']['cars'][vid]['initial_cell'] <= 12
                a = p.passage(bank['rm8']['cars'][vid], passage['points_m'])
                b = p.passage(bank[arm]['cars'][vid], passage['points_m'])
                assert a == row['baseline'] and b == row['controlled']
                for point in passage['points_m']:
                    close(b[point]['t'] - a[point]['t'], row['arrival_shifts_s'][point])
                    close(b[point]['v'] - a[point]['v'], row['speed_shifts_kmh'][point])
                names = list(passage['points_m'])
                for x, y in zip(names, names[1:]):
                    close(row['arrival_shifts_s'][y] - row['arrival_shifts_s'][x], row['travel_time_shifts_s'][x+'_'+y])
                pairs += 1
            for field in ('arrival_shifts_s', 'travel_time_shifts_s', 'speed_shifts_kmh'):
                for key, saved in case[field].items():
                    assert p.stats([v[field][key] for v in case['pairs']]) == saved
    assert (pins, traces, balances, worse, pairs) == (18, 24, 3600, 10, 900)
    print(json.dumps(dict(passed=True, qualified=False, cohort_and_outlet=reports[0],
        transport_and_passage_source_pins=pins, saved_local_traces=traces,
        local_mass_balances=balances, candidate_speed_worse_cases=worse,
        paired_completed_passages=pairs, forecasts_recomputed=False, native_started=False), indent=2))


if __name__ == '__main__':
    main()
