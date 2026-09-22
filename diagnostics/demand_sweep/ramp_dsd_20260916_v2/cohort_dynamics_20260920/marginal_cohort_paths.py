"""Trace only the common initial mainline cohort in the matched RM pair.

Retrospective explanation, not a forecast. Never match newly generated IDs.
"""
from pathlib import Path
from collections import Counter, defaultdict
import bisect
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import marginal_boundary_timing as b


def extract(arm, geometry):
    m = b.m
    path = m.BANK / f'run_{arm}/vissim_eval/baseline_001.fzp'
    stamp = (path.stat().st_size, path.stat().st_mtime_ns)
    chain = {r['link']: r for r in geometry['chains']['FW_E']}
    ports = {r['connector']: r for r in geometry['boundaries']
             if r['road'] == 'FW_E' and r['kind'] in ('ramp', 'offramp')}
    bounds = [r['end_m'] for r in geometry['cells'] if r['road'] == 'FW_E']
    saved = m.e.load(b.HERE / 'marginal_boundary_timing_v1' / (arm + '.json'))
    ids = set(saved['initial_ids'])
    histories = defaultdict(list)
    aggregates = []
    first = None
    for t, frame in b.frames(path, set(chain) | set(ports)):
        if first is None:
            first = {v: r for v, r in frame.items() if v in ids}
        groups = defaultdict(list)
        for vid, row in frame.items():
            r = dict(row)
            if r['link'] in chain:
                r['x'] = chain[r['link']]['offset_m'] + r['pos']
                r['cell'] = min(20, max(0, bisect.bisect_right(bounds, r['x'])))
                groups[r['cell'], r['lane']].append((vid, r))
            else:
                r['cell'] = None
                r['x'] = None
            if vid in ids:
                histories[vid].append(dict(time_s=t, **r))
        for (cell, lane), vehicles in groups.items():
            ordered = sorted(vehicles, key=lambda v: v[1]['x'])
            for index, (vid, row) in enumerate(ordered):
                if vid in ids:
                    target = ordered[index + 1] if index + 1 < len(ordered) else None
                    histories[vid][-1]['next_in_same_cell_lane'] = (
                        dict(vehicle=target[0], front_spacing_m=target[1]['x'] - row['x'],
                             speed=target[1]['speed']) if target else None)
            if t > b.START:
                initial = [r for v, r in vehicles if v in ids]
                aggregates.append(dict(time_s=t, cell=cell, lane=lane, n=len(vehicles),
                    initial_n=len(initial), speed_sum=sum(r['speed'] for _, r in vehicles),
                    initial_speed_sum=sum(r['speed'] for r in initial),
                    stopped=sum(r['speed'] < 5 for _, r in vehicles),
                    initial_stopped=sum(r['speed'] < 5 for r in initial)))
    for vid in ids:
        n = sum(r['cell'] is not None and r['time_s'] > b.START for r in histories[vid])
        assert n == saved['initial_cohort_residence_s'][str(vid)], (arm, vid)
    assert stamp == (path.stat().st_size, path.stat().st_mtime_ns)
    return first, histories, aggregates, dict(path=str(path.relative_to(m.e.ROOT)), bytes=stamp[0], mtime_ns=stamp[1])


def main():
    m = b.m
    out = b.HERE / 'marginal_cohort_paths_v1'
    out.mkdir(exist_ok=False)
    geometry = m.e.load(m.BANK / 'observations/rm8/geometry.json')
    data = {a: extract(a, geometry) for a in m.ARMS}
    assert data['rm8'][0] == data['rm_ramp'][0]
    records, by_origin = [], defaultdict(lambda: Counter())
    for vid in sorted(data['rm8'][1]):
        modes = {}
        for arm in m.ARMS:
            trajectory = data[arm][1][vid]
            rows = [r for r in trajectory if r['cell'] is not None and r['time_s'] > b.START]
            initial = trajectory[0]
            crossings = {}
            for r in trajectory:
                if r['cell'] is not None:
                    crossings.setdefault(str(r['cell']), r['time_s'])
            modes[arm] = dict(residence_s=len(rows), stopped_s=sum(r['speed'] < 5 for r in rows),
                slow30_s=sum(r['speed'] < 30 for r in rows), cell_first_time=crossings,
                initial_cell=initial['cell'], initial_lane=initial['lane'], initial_speed=initial['speed'],
                final_row=trajectory[-1], by_cell=dict(Counter(r['cell'] for r in rows)))
        base = {r['time_s']: r for r in data['rm8'][1][vid]}
        strong = {r['time_s']: r for r in data['rm_ramp'][1][vid]}
        first_diff = None
        for t in sorted(base.keys() & strong.keys()):
            x, y = base[t], strong[t]
            if any(x[k] != y[k] for k in ('link', 'lane', 'pos', 'speed')):
                first_diff = dict(time_s=t, base=x, strong=y)
                break
        delta = modes['rm_ramp']['residence_s'] - modes['rm8']['residence_s']
        origin = modes['rm8']['initial_cell']
        by_origin[origin]['vehicles'] += 1
        by_origin[origin]['delta_residence_s'] += delta
        by_origin[origin]['delta_stopped_s'] += modes['rm_ramp']['stopped_s'] - modes['rm8']['stopped_s']
        records.append(dict(vehicle=vid, delta_residence_s=delta, first_difference=first_diff, arms=modes))
    aggregates = {}
    for arm in m.ARMS:
        rows = data[arm][2]
        summary = []
        for start in (2550, 2700, 2850):
            for cell in range(21):
                selected = [r for r in rows if start < r['time_s'] <= start + 150 and r['cell'] == cell]
                summary.append(dict(start_s=start, cell=cell,
                    **{key: sum(r[key] for r in selected) for key in ('n', 'initial_n', 'stopped', 'initial_stopped')}))
        aggregates[arm] = summary
        m.e.save(out / (arm + '_cell_lane_1s.json'), rows)
    contrasts = []
    for a, c in zip(aggregates['rm8'], aggregates['rm_ramp']):
        assert (a['start_s'], a['cell']) == (c['start_s'], c['cell'])
        contrasts.append(dict(start_s=a['start_s'], cell=a['cell'],
            delta_ttt=(c['n'] - a['n']) / 3600,
            delta_initial_ttt=(c['initial_n'] - a['initial_n']) / 3600,
            delta_stopped_s=c['stopped'] - a['stopped'],
            delta_initial_stopped_s=c['initial_stopped'] - a['initial_stopped']))
    earlier = m.e.load(b.HERE / 'marginal_boundary_timing_v1/result.json')
    assert abs(sum(r['delta_ttt'] for r in contrasts) - earlier['prefix']['3000']['delta_ttt']) < 1e-8
    assert abs(sum(r['delta_residence_s'] for r in records) / 3600 - earlier['prefix']['3000']['delta_initial_cohort']) < 1e-8
    ranked = sorted(records, key=lambda r: abs(r['delta_residence_s']), reverse=True)
    differing = sorted([r for r in records if r['first_difference']], key=lambda r: r['first_difference']['time_s'])
    examples = {r['vehicle'] for r in ranked[:5] + differing[:5]}
    m.e.save(out / 'examples.json', {str(vid): {a: data[a][1][vid] for a in m.ARMS} for vid in sorted(examples)})
    m.e.save(out / 'vehicles.json', records)
    files = [Path(__file__), Path(b.__file__), b.HERE / 'marginal_boundary_timing_v1/result.json',
             m.BANK / 'observations/rm8/geometry.json']
    result = dict(status='COMMON_INITIAL_COHORT_TRACE_NOT_QUALIFIED', qualified=False,
        initial_vehicles=len(records), by_initial_cell={str(k): dict(v) for k, v in by_origin.items()},
        cell_contrasts=contrasts, largest_residence_differences=ranked[:10], first_differences=differing[:5],
        receipts={a: data[a][3] for a in m.ARMS}, new_native_runs=0, production_changes=0,
        interpretation='Geometric next vehicle is only within same cell/lane, not native interaction target. Censored at3000s.',
        source_pins={str(p.relative_to(m.e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    m.e.save(out / 'result.json', result)
    print(json.dumps(dict(initial_vehicles=len(records), by_initial_cell=result['by_initial_cell'],
        first_differences=[dict(vehicle=r['vehicle'],time_s=r['first_difference']['time_s'],
            cell=r['first_difference']['base']['cell']) for r in differing[:5]],
        largest=[dict(vehicle=r['vehicle'],delta_s=r['delta_residence_s'],initial_cell=r['arms']['rm8']['initial_cell']) for r in ranked[:5]])))


if __name__ == '__main__':
    main()
