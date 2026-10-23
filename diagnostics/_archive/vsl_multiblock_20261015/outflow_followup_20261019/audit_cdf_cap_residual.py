"""Localize the remaining error using already-qualified caches, without forecasts."""
import collections
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path

A = Path(__file__).resolve().parent
O = A / 'cdf_cap_candidate'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def main():
    output = O / 'residual_localization.json'
    assert not output.exists()
    assessment = read(O / 'assessment.json')
    assert assessment['new_forecasts'] == 2
    qualified = read(A / 'interaction_response/completion.json')
    lane_endpoints = read(A / 'approach_lane_evidence.json')['rows']
    transport = read(A / 'interaction_response/native_cell18_transport.json')
    base_model = {r['name']: r for r in read(A.parent / 'matched_off2250_v3/summary.json')['results']}
    frames, lengths, transition_counts = {}, {}, {}
    for case in ('hold', 'single90', 'selected'):
        path = A / 'interaction_response' / (case + '_records.json.gz')
        data = read(path)
        assert PINS[str(path)] == qualified['cases'][case]['output_sha256']
        bounds = data['bounds_m']
        lengths = {cell: bounds[cell + 1] - bounds[cell] for cell in range(14, 19)}
        assert abs(lengths[18] - transport['length_m']) < 1e-9
        grouped, people = collections.defaultdict(list), collections.defaultdict(dict)
        times = sorted({r[0] for r in data['rows'] if r[0] >= 2250})
        for row in data['rows']:
            t, vehicle, cell, lane = row[:4]
            if t < 2250 or not 14 <= cell <= 18:
                continue
            assert lane in (1, 2, 3, 4)
            grouped[t, cell, lane].append(row)
            people[t][vehicle] = row
        points = {}
        for t in times:
            for cell in range(14, 19):
                for lane in (1, 2, 3, 4):
                    rows = grouped[t, cell, lane]
                    points[t, cell, lane] = dict(n=len(rows), speed=math.fsum(r[5] for r in rows) / len(rows) if rows else 0.,
                                                slow=sum(r[5] < 40 for r in rows))
        for r in lane_endpoints:
            if r['case'] == case:
                points[r['time_sec'], r['cell'], r['lane']] = dict(n=r['n'], speed=r['speed_mean'] or 0., slow=r['n_under40'])
        assert len({key[0] for key in points}) == 94
        frames[case] = points
        transitions = []
        for block in range(3):
            start, end = 2250 + block * 150, 2400 + block * 150
            retained = changed = entered = exited = 0
            for t0, t1 in zip(times, times[1:]):
                if not start <= t0 < t1 < end:
                    continue
                before, after = people[t0], people[t1]
                ids = before.keys() & after.keys()
                retained += len(ids)
                changed += sum(before[i][3] != after[i][3] for i in ids)
                entered += len(after.keys() - before.keys())
                exited += len(before.keys() - after.keys())
            transitions.append(dict(block=block, retained_pairs=retained, observed_lane_index_changes=changed,
                                    region_entries_between_samples=entered, region_exits_between_samples=exited))
        transition_counts[case] = transitions

    contrasts = []
    for case in ('single90', 'selected'):
        for block in range(3):
            start, end = 2250 + block * 150, 2400 + block * 150
            times = sorted({t for t, _, _ in frames['hold'] if start <= t <= end})
            for cell in range(14, 19):
                for lane in (1, 2, 3, 4):
                    values = []
                    empty = 0
                    for t in times:
                        x, y = frames['hold'][t, cell, lane], frames[case][t, cell, lane]
                        stock = (y['n'] - x['n']) * (x['speed'] + y['speed']) / 2
                        speed = (y['speed'] - x['speed']) * (x['n'] + y['n']) / 2
                        direct = y['n'] * y['speed'] - x['n'] * x['speed']
                        assert abs(stock + speed - direct) < 1e-9
                        values.append((stock, speed, direct, y['slow'] - x['slow']))
                        empty += x['n'] == 0 or y['n'] == 0
                    integrated = [math.fsum((a[k] + b[k]) * (t1-t0) / 2 for a,b,t0,t1 in zip(values, values[1:], times, times[1:])) for k in range(4)]
                    contrasts.append(dict(case=case, block=block, cell=cell, lane=lane,
                        transport_proxy_delta_veh=integrated[2]/(3.6*lengths[cell]),
                        symmetric_stock_term_veh=integrated[0]/(3.6*lengths[cell]),
                        symmetric_speed_term_veh=integrated[1]/(3.6*lengths[cell]),
                        slow_vehicle_seconds_delta=integrated[3], empty_endpoint_count=empty))
    for case in ('single90', 'selected'):
        for horizon in (150, 300, 450):
            calculated = math.fsum(r['transport_proxy_delta_veh'] for r in contrasts if r['case'] == case and r['cell'] == 18 and r['block'] < horizon/150)
            previous = next(r for r in transport['contrasts'] if r['case'] == case and r['horizon'] == horizon)
            assert abs(calculated - previous['transport_proxy_delta']) < 1e-8

    absolute = []
    for case in ('hold', 'single90', 'selected'):
        model = base_model['hold'] if case == 'hold' else read(O / (case + '_result.json'))
        for index, t in enumerate((2250, 2400, 2550, 2700)):
            for cell in range(14, 19):
                lanes = [frames[case][t, cell, lane] for lane in (1,2,3,4)]
                n = sum(r['n'] for r in lanes)
                native_v = math.fsum(r['n']*r['speed'] for r in lanes)/n if n else None
                snap = model['snapshots'][index]
                absolute.append(dict(case=case, time=t, cell=cell, native_n=n, model_n=snap['n']['FW_E'][cell],
                    native_speed=native_v, model_speed=snap['speed']['FW_E'][cell]))
    doc = dict(status='completed_cached_lane_transport_residual_localization',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        contrasts=contrasts, absolute_endpoint_comparison=absolute, observed_transitions=transition_counts,
        checks=dict(native_cell18_transport_parity=True, stock_speed_algebra=True, cache_hashes=True),
        limitations=['Nv/L is a cell transport proxy, not lane exit counts; the previous position-moment/off-exit correction remains necessary.',
          'Symmetric stock/speed terms are an exact descriptive product decomposition, not independent causal effects.',
          'Empty-lane speed is zero for the algebra; decompositions involving empty endpoints are flagged.',
          'Observed lane-index changes miss multiple changes between samples, omit vehicles leaving the region, and are not causal evidence by themselves.',
          'No future observed state is used as a model input; no calibration, new forecast, FZP scan, native or production edit.'],
        new_forecasts=0, new_fzp_scans=0, new_native=0, source_pins=PINS)
    output.write_text(json.dumps(doc, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({case: [dict(lane=lane, proxy=sum(r['transport_proxy_delta_veh'] for r in contrasts if r['case']==case and r['cell']==18 and r['lane']==lane),
        speed_term=sum(r['symmetric_speed_term_veh'] for r in contrasts if r['case']==case and r['cell']==18 and r['lane']==lane),
        stock_term=sum(r['symmetric_stock_term_veh'] for r in contrasts if r['case']==case and r['cell']==18 and r['lane']==lane)) for lane in (1,2,3,4)] for case in ('single90','selected')}, indent=2))


if __name__ == '__main__':
    main()
