"""Verify the follow-up delivery and saved accounting; no new model/native run."""
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def close(a, b):
    assert abs(a - b) < 1e-8, (a, b)


def main():
    previous = {r['path']: r for r in load(HERE / 'direct_files.json')['files']}
    update = {r['path']: r for r in load(HERE / 'followup_files.json')['files']}
    files = {**previous, **update}
    for name, row in files.items():
        p = ROOT / name
        assert p.stat().st_size == row['bytes'], name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256'], name

    identity = load(K / 'paired_response_identification_v1/result.json')
    protocol = load(K / 'matched_meter2550_v1/protocol.json')
    timing = load(K / 'marginal_boundary_timing_v1/result.json')
    pins = {**identity['source_pins'], **protocol['source_pins'], **timing['pins']}
    for name, digest in pins.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name

    replay = load(K / 'response_identification_validation_v1/result.json')
    assert replay['passed'] and replay['identification_forecasts_exact'] == 18
    assert replay['cutoff2550_full_forecasts_exact'] == 2
    assert replay['future_rows_removed']['port_events'] > 0
    pair = load(K / 'matched_meter2550_v1/result.json')
    assert pair['qualified'] is False and pair['exact_native_cutoff_payload']
    for values in pair['deltas'].values():
        close(sum(values[k] for k in ('mainline', 'on', 'off')), values['total'])

    records = {arm: load(K / 'marginal_boundary_timing_v1' / (arm + '.json'))
               for arm in ('rm8', 'rm_ramp')}
    assert records['rm8']['initial_ids'] == records['rm_ramp']['initial_ids']
    assert len(records['rm8']['initial_ids']) == 676
    steps = prefixes = 0
    for arm, record in records.items():
        trace = record['trace']
        assert [r['time_s'] for r in trace] == list(range(2550, 3001))
        events_by_time = Counter()
        for event in record['events']:
            assert event['sign'] in (-1, 1)
            events_by_time[event['time_s']] += event['sign']
        for before, after in zip(trace, trace[1:]):
            assert after['n'] - before['n'] == events_by_time[after['time_s']]
            steps += 1
        for end in (2700, 2850, 3000):
            rows = [r for r in trace if 2550 < r['time_s'] <= end]
            moments = Counter()
            for event in record['events']:
                if event['time_s'] <= end:
                    moments[event['kind']] += event['sign'] * (end - event['time_s'] + 1) / 3600
            saved = record['prefix'][str(end)]
            close(sum(r['n'] for r in rows) / 3600, saved['ttt_veh_h'])
            close(trace[0]['n'] * (end - 2550) / 3600 + sum(moments.values()), saved['ttt_veh_h'])
            for kind, value in moments.items():
                close(value, saved['moments'][kind])
            close(sum(r['initial_cohort_n'] for r in rows) / 3600, saved['initial_cohort_ttt'])
            close(saved['initial_cohort_ttt'] + saved['later_cohort_ttt'], saved['ttt_veh_h'])
            prefixes += 1
    for end, result in timing['prefix'].items():
        base = records['rm8']['prefix'][end]
        strong = records['rm_ramp']['prefix'][end]
        close(strong['ttt_veh_h'] - base['ttt_veh_h'], result['delta_ttt'])
        close(sum(result['signed_moment_differences'].values()), result['delta_ttt'])
    close(timing['prefix']['3000']['delta_ttt'], pair['deltas']['actual']['mainline'])
    assert timing['qualified'] is False
    print(json.dumps(dict(passed=True, direct_files_checked=len(files),
        updated_previous_files=sorted(previous.keys() & update.keys()),
        source_pins_checked=len(pins), saved_continuity_steps=steps,
        prefix_identities=prefixes, new_forecasts=0, new_native_runs=0,
        qualified=False, note='Delivery and accounting validation, not gain-prediction qualification.')))


if __name__ == '__main__':
    main()
