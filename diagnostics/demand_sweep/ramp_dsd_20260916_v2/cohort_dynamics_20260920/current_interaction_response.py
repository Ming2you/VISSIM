"""Matched-row test: current native target versus geometric leader.

NC-only fitting, current/past features, future speeds as labels only. This is
conditional short response identification, not an autonomous plant or gain fit.
"""
from pathlib import Path
from collections import defaultdict, Counter
import bisect, hashlib, math, sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g
d = g.d
HORIZONS = (1, 5, 10)
MODES = ('history', 'geometry', 'target', 'geometry_state', 'target_state')


def keys(r, mode):
    root = tuple(r['base'])
    history = root + (r['history'],)
    if mode == 'history':
        return (history, root)
    subject = 'geometry' if mode.startswith('geometry') else 'target'
    paired = root + tuple(r[subject]) + (r['history'],)
    if mode.endswith('_state'):
        return (paired + tuple(r['current_state']), paired, history, root)
    return (paired, history, root)


def current_features(row, front, target, previous, density, shifts, params):
    # No future frame, future target, labels or later lane flags accepted here.
    x = shifts[row['link']] + row['pos']
    scale = params['stand_m'] + params['headway_s'] * row['v'] / 3.6
    gaps = {}
    for name, ahead in (('geometry', front), ('target', target)):
        gap = shifts[ahead['link']] + ahead['pos'] - ahead['length'] - x
        gaps[name] = (bisect.bisect_right((.5, 1., 2.), gap / scale),
                      bisect.bisect_right((-5., 5.), row['v'] - ahead['v']))
    target_gap = shifts[target['link']] + target['pos'] - target['length'] - x
    return dict(base=(bisect.bisect_right((30., 60., 90.), row['v']),
                      bisect.bisect_right((15., 30., 50.), density)),
        history=-1 if previous is None else bisect.bisect_right((-7.2, -1., 1., 7.2), row['v'] - previous['v']),
        **gaps, current_state=(row['interaction'], row['lane_change'],
                               int(target['lane'] != row['lane']), int(target_gap < 0)),
        target_is_geometric=row['target'] == front['vehicle'], target_gap_m=target_gap)


def records(frames, geometry, params, lo):
    shifts = {r['link']: r['offset_m'] for r in geometry['chains']['FW_E']}
    cells = {r['cell']: r for r in geometry['cells'] if r['road'] == 'FW_E'}
    bounds = [cells[c]['end_m'] for c in sorted(cells)]
    result = []
    counts = Counter()
    for t in range(lo, 2841):
        frame = frames[t]
        lanes = defaultdict(list)
        densities = Counter()
        addresses = {}
        for vid, row in frame.items():
            x = shifts[row['link']] + row['pos']
            cell = min(20, bisect.bisect_right(bounds, x))
            addresses[vid] = cell
            lanes[row['lane']].append((x, vid))
            densities[cell, row['lane']] += 1
        ahead = {}
        for order in lanes.values():
            order.sort()
            for (_, vid), (_, front) in zip(order, order[1:]):
                ahead[vid] = front
        for vid, row in frame.items():
            cell = addresses[vid]
            if cell < 15:
                continue
            counts['candidates'] += 1
            if vid not in ahead:
                counts['no_geometric_leader'] += 1
                continue
            front = frame[ahead[vid]]
            gap = shifts[front['link']] + front['pos'] - front['length'] - shifts[row['link']] - row['pos']
            if gap < 0:
                counts['geometric_projection_overlap'] += 1
                continue
            if row['target_type'] != 'Vehicle' or row['target'] not in frame:
                counts['native_vehicle_target_unobserved'] += 1
                continue
            if vid not in frames[t+1]:
                counts['next_second_censored'] += 1
                continue
            target = frame[row['target']]
            rec = current_features(row, front, target, frames[t-1].get(vid),
                                   densities[cell, row['lane']] / cells[cell]['length_km'], shifts, params)
            rec.update(time_s=t, vehicle=vid, cell=cell, current_speed=row['v'],
                labels={h: frames[t+h][vid]['v'] - row['v'] for h in HORIZONS if vid in frames[t+h]})
            result.append(rec)
            counts['retained'] += 1
            counts['native_target_negative_projected_gap'] += int(rec['target_gap_m'] < 0)
            counts['native_target_differs'] += int(not rec['target_is_geometric'])
    assert counts['candidates'] == sum(counts[k] for k in ('retained', 'no_geometric_leader', 'geometric_projection_overlap', 'native_vehicle_target_unobserved', 'next_second_censored'))
    return result, dict(counts)


def fit(rs):
    banks = {mode: [defaultdict(lambda: defaultdict(lambda: [0, 0.])) for _ in keys(rs[0], mode)] for mode in MODES}
    global_values = defaultdict(lambda: [0, 0.])
    n = 0
    for r in rs:
        if not 900 <= r['time_s'] <= 2090:
            continue
        n += 1
        for h, value in r['labels'].items():
            global_values[h][0] += 1
            global_values[h][1] += value
        for mode in MODES:
            for table, key in zip(banks[mode], keys(r, mode)):
                for h, value in r['labels'].items():
                    table[key][h][0] += 1
                    table[key][h][1] += value
    compiled = {mode: [{key: {h: (v[0], v[1]/v[0]) for h, v in entries.items()} for key, entries in table.items()}
                        for table in tables] for mode, tables in banks.items()}
    return compiled, {h: v[1]/v[0] for h, v in global_values.items()}, n


def predict(r, mode, h, model, means):
    for level, (table, key) in enumerate(zip(model[mode], keys(r, mode))):
        item = table.get(key, {}).get(h)
        if item and item[0] >= g.MIN_SUPPORT:
            return item[1], level
    return means[h], -1


def score(rs, model, means, lo, hi):
    selected = [r for r in rs if lo <= r['time_s'] and r['time_s'] + 10 <= hi]
    answer = {}
    for mode in MODES:
        result = {}
        for horizon in HORIZONS:
            total = bias = 0.
            fallback = Counter()
            grouped = defaultdict(list)
            difference = []
            count = 0
            for r in selected:
                if horizon not in r['labels']:
                    continue
                value, level = predict(r, mode, horizon, model, means)
                error = value - r['labels'][horizon]
                total += error * error
                bias += error
                count += 1
                fallback[level] += 1
                grouped[r['time_s'], r['cell']].append(error)
                if not r['target_is_geometric']:
                    difference.append(error)
            cohort_errors = [sum(v)/len(v) for v in grouped.values()]
            result[str(horizon)] = dict(n=count, rmse_kmh=math.sqrt(total/count), bias_kmh=bias/count,
                target_mismatch=dict(n=len(difference), rmse_kmh=math.sqrt(sum(x*x for x in difference)/len(difference)), bias_kmh=sum(difference)/len(difference)) if difference else {},
                cell_cohort=dict(n=len(cohort_errors), rmse_kmh=math.sqrt(sum(x*x for x in cohort_errors)/len(cohort_errors))),
                fallback_counts=dict(fallback))
        answer[mode] = result
    return answer


def main():
    out = d.HERE / 'current_interaction_response_v1'
    out.mkdir(exist_ok=False)
    gp = d.H / 'controller_response_s23_v1/none/geometry.json'
    geometry = d.e.load(gp)
    network = d.H / 'source_dsd/baseline.inpx'
    params = g.restart.native_parameters(network)
    source = d.HERE / 'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    frames, receipt = g.read(source, True, 899)
    nc, coverage = records(frames, geometry, params, 900)
    # Control/past records are used for scoring, never added to fitting.
    model, means, n = fit(nc)
    canary = {**nc[-1], 'labels': {h: 999999. for h in HORIZONS}}
    assert fit([r for r in nc if r['time_s'] <= 2090] + [canary]) == (model, means, n)
    features_canary = {**nc[len(nc)//2], 'labels': {h: -999999. for h in HORIZONS}, 'future_target': 123456}
    for mode in MODES:
        assert keys(features_canary, mode) == keys(nc[len(nc)//2], mode)
        for h in HORIZONS:
            assert predict(features_canary, mode, h, model, means) == predict(nc[len(nc)//2], mode, h, model, means)
    results = dict(nc_time_validation=score(nc, model, means, 2100, 2400), nc_control=score(nc, model, means, 2400, 2850))
    focused = [r for r in nc if r['cell'] == 16 and 2550 <= r['time_s'] < 2580]
    results['focused_cell16'] = score(focused, model, means, 2550, 2590)
    prefix = {t: frames[t] for t in (2399, 2400)}
    del frames
    print('NC_SCORED', n, {mode: results['nc_time_validation'][mode]['1']['rmse_kmh'] for mode in MODES}, flush=True)
    source_vsl = d.HERE / 'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp'
    frames, receipt_vsl = g.read(source_vsl, True, 2399)
    assert all(frames[t] == prefix[t] for t in prefix), 'Extended prefix differs before treatment'
    vsl, coverage_vsl = records(frames, geometry, params, 2400)
    results['vsl_control'] = score(vsl, model, means, 2400, 2850)
    del frames
    table = {mode: [[dict(key=list(key), targets={str(h): dict(n=value[0], mean=value[1]) for h, value in ys.items()})
                       for key, ys in bank.items()] for bank in banks] for mode, banks in model.items()}
    d.e.save(out / 'training_table.json', dict(models=table, global_mean=means, training_rows=n, cutoff_max_s=2090, label_max_s=2100))
    files = [Path(__file__), Path(g.__file__), gp, network, out / 'training_table.json']
    d.e.save(out / 'result.json', dict(status='CURRENT_NATIVE_TARGET_CONDITIONAL_IDENTIFICATION_NOT_QUALIFIED',
        scores=results, coverage=dict(none=coverage, vsl=coverage_vsl), training_rows=n,
        source_receipts=dict(none=receipt, vsl=receipt_vsl), extended_prefix_equal=[2399, 2400],
        canary_after_training_ignored=True, future_labels_and_target_not_features=True,
        pins={str(path.relative_to(d.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        limitations=['All five models fit exactly the same NC900..2090 records, labels through2100; inspected seed23 only.',
            'Both geometric leader and native Vehicle target must be observed; other objects and unobserved targets are excluded and counted.',
            'Negative projected native-target gap is retained in the lowest gap bin and separately flagged, never treated as a physical same-lane body overlap.',
            'Current native target/interaction/lane-change are measured at each cutoff, not predicted autonomously.',
            'Future lanes and interaction targets are not inputs. No RM target metadata exists in its9-column recording; none is fabricated.',
            'Conditional1/5/10s response identification is not450s gain, conservation, ranking or controller qualification.'],
        qualified=False, production_changes=0, new_native_runs=0))
    print('RESULT', {period: {mode: {h: round(row['rmse_kmh'], 3) for h, row in vals.items()} for mode, vals in modes.items()} for period, modes in results.items()}, flush=True)


if __name__ == '__main__':
    main()
