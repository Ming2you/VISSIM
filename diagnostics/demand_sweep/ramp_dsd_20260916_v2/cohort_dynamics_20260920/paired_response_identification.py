"""Paired flow-response identification, explicitly using oracle boundaries.

Tests whether a small delayed response can generalize across DEVELOPMENT seeds.
This is not an operational plant: future NC discharge and treated boundary
measurements are supplied. No controller reward, capacity gain or model edit.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
ARMS = ('rm_ramp', 'vsl', 'both')
SEEDS = (23, 33, 43)
START, END, STEP = 2400, 2850, 30
LAGS = 6


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def folders(seed):
    if seed == 23:
        bank = H / 'response_late_s23_v1'
        return bank, {'none': H / 'controller_response_s23_v1/none',
                      **{a: bank / 'observations' / a for a in ARMS}}
    bank = H / 'state_response_20260919/native_s33_v1' if seed == 33 else HERE / 'fresh_s43_v1'
    return bank, {a: bank / 'observations' / a for a in ('none', *ARMS)}


def read_case(folder):
    with (folder / 'cells_30s.csv').open(encoding='utf-8-sig', newline='') as f:
        cells = {(int(float(r['time_s'])), int(r['cell'])): r for r in csv.DictReader(f)
                 if r['road'] == 'FW_E' and START <= float(r['time_s']) <= END}
    with (folder / 'flows_30s.csv').open(encoding='utf-8-sig', newline='') as f:
        flows = {(int(float(r['window_end_s'])), int(r['cell'])): r for r in csv.DictReader(f)
                 if r['road'] == 'FW_E' and START < float(r['window_end_s']) <= END}
    times = list(range(START, END + 1, STEP))
    n = np.array([sum(float(cells[t, c]['n_veh']) for c in range(15, 21)) for t in times])
    v14 = np.array([float(cells[t, 14]['v_kmh']) for t in times])
    incoming = np.array([float(flows[t, 15]['upstream_crossings']) for t in times[1:]])
    outgoing = np.array([float(flows[t, 20]['terminal_exits_inferred']) for t in times[1:]])
    merge = np.array([float(flows[t, 13]['ramp_merges']) for t in times[1:]])
    for t in times[1:]:
        for c in range(15, 21):
            row = flows[t, c]
            for field in ['source_admissions', 'ramp_merges', 'off_departures',
                          'unexplained_entries', 'unexplained_losses', 'native_removals',
                          'conservation_residual_veh']:
                assert abs(float(row[field])) < 1e-10, (folder, t, c, field)
        assert float(flows[t, 14]['downstream_crossings']) == float(flows[t, 15]['upstream_crossings'])
    assert np.max(np.abs(np.diff(n) - incoming + outgoing)) < 1e-10
    return dict(n=n, v14=v14, incoming=incoming, outgoing=outgoing, merge=merge,
                initial=[cells[START, c] for c in range(21)])


def features(pair, mode):
    """Output interval i uses only earlier count intervals and current speed."""
    rows = []
    for i in range(15):
        row = []
        for lag in range(LAGS):
            count_index = i - lag - 1
            if mode == 'merge_counts':
                row.append(pair['delta_merge'][count_index] if count_index >= 0 else 0.)
            elif mode == 'entry_counts_and_speed':
                row.append(pair['delta_incoming'][count_index] if count_index >= 0 else 0.)
                speed_index = i - lag
                row.append(pair['delta_speed'][speed_index] if speed_index >= 0 else 0.)
            else:
                raise ValueError(mode)
        rows.append(row)
    return np.array(rows)


def fit(pairs, mode):
    X = np.concatenate([features(p, mode) for p in pairs])
    y = np.concatenate([p['delta_outgoing'] for p in pairs])
    # Fixed ridge strength, no search on test gain. No intercept: zero paired
    # input has zero predicted response. This is an identification restriction.
    scale = np.sqrt(np.mean(X**2, axis=0))
    scale = np.where(scale > 1e-12, scale, 1.)
    Z = X / scale
    beta = np.linalg.solve(Z.T @ Z + np.eye(Z.shape[1]), Z.T @ y) / scale
    return beta, dict(rows=len(y), rank=int(np.linalg.matrix_rank(X)), columns=X.shape[1],
                      coefficients=beta.tolist(), training_rmse=float(np.sqrt(np.mean((X @ beta - y)**2))))


def integrate(pair, response):
    """Conserved port-free regional inventory; future boundary inputs explicit."""
    base, actual = pair['base'], pair['actual']
    n = [float(base['n'][0])]
    out = []
    projections = []
    for i, delta in enumerate(response):
        requested = float(base['outgoing'][i] + delta)
        # No capacity bonus. This diagnostic has only nonnegative/available-
        # stock limits, not a calibrated downstream saturation law.
        accepted = min(max(0., requested), n[-1] + actual['incoming'][i])
        if abs(accepted - requested) > 1e-10:
            projections.append(dict(index=i, requested=requested, accepted=accepted))
        out.append(accepted)
        n.append(n[-1] + actual['incoming'][i] - accepted)
    n, out = np.array(n), np.array(out)
    assert np.max(np.abs(np.diff(n) - actual['incoming'] + out)) < 1e-8
    predicted_delta = n - base['n']
    actual_delta = actual['n'] - base['n']
    cost = lambda x: float(np.sum((x[:-1] + x[1:]) / 2) * STEP / 3600)
    return dict(actual_delta_ttt30=cost(actual_delta), predicted_delta_ttt30=cost(predicted_delta),
                delta_outflow_rmse=float(np.sqrt(np.mean((out - base['outgoing'] - pair['delta_outgoing'])**2))),
                delta_inventory_rmse=float(np.sqrt(np.mean((predicted_delta - actual_delta)**2))),
                predicted_terminal_count_change=float(np.sum(out - base['outgoing'])),
                actual_terminal_count_change=float(np.sum(pair['delta_outgoing'])),
                projections=projections, n=n.tolist(), terminal=out.tolist(),
                mass_residual_max=float(np.max(np.abs(np.diff(n) - actual['incoming'] + out))))


def main():
    out = HERE / 'paired_response_identification_v1'
    out.mkdir(exist_ok=False)
    pairs, pins, command_ref = [], {}, None
    for seed in SEEDS:
        bank, paths = folders(seed)
        protocol = load(bank / 'protocol.json')
        commands = {a: {k: protocol['candidate_bank'][a][k][:3] for k in ('green', 'vsl')} for a in ARMS}
        if command_ref is None:
            command_ref = commands
        assert commands == command_ref and protocol['dsd_ids'] == list(range(51, 59))
        records = {arm: read_case(folder) for arm, folder in paths.items()}
        base = records['none']
        for arm in ARMS:
            r = records[arm]
            assert r['initial'] == base['initial'], (seed, arm, 'initial state')
            pairs.append(dict(seed=seed, arm=arm, base=base, actual=r,
                              delta_incoming=r['incoming']-base['incoming'],
                              delta_outgoing=r['outgoing']-base['outgoing'],
                              delta_speed=r['v14']-base['v14'], delta_merge=r['merge']-base['merge']))
        for folder in paths.values():
            for name in ['cells_30s.csv', 'flows_30s.csv', 'geometry.json']:
                path = folder / name
                pins[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        pins[(bank / 'protocol.json').relative_to(ROOT).as_posix()] = hashlib.sha256((bank / 'protocol.json').read_bytes()).hexdigest()
    pins[Path(__file__).relative_to(ROOT).as_posix()] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    # Canary: neither an output label nor the current/future interval count
    # may influence an earlier output feature. Speed is known only at start.
    checks = 0
    for pair in pairs:
        for mode in ('merge_counts', 'entry_counts_and_speed'):
            original = features(pair, mode)
            for i in range(15):
                altered = {**pair, **{k: pair[k].copy() for k in ('delta_merge','delta_incoming','delta_speed','delta_outgoing')}}
                altered['delta_merge'][i:] += 1e6
                altered['delta_incoming'][i:] += 1e6
                altered['delta_speed'][i+1:] += 1e6
                altered['delta_outgoing'] += 1e6
                assert np.array_equal(features(altered, mode)[:i+1], original[:i+1])
                checks += 1
    result = {}
    for mode in ('merge_counts', 'entry_counts_and_speed'):
        folds = {}
        for held in SEEDS:
            train = [p for p in pairs if p['seed'] != held]
            beta, summary = fit(train, mode)
            tests = {}
            for pair in [p for p in pairs if p['seed'] == held]:
                tests[pair['arm']] = {'fitted': integrate(pair, features(pair, mode) @ beta),
                                     'zero_response': integrate(pair, np.zeros(15))}
            folds[str(held)] = dict(training=summary, tests=tests)
        result[mode] = folds
    payload = dict(status='ORACLE_BOUNDARY_RESPONSE_IDENTIFICATION_ONLY', qualified=False,
                   scope='FW_E port-free cells15..20,2400..2850s;30s trapezoid residence,not Omega/component total',
                   limitations=['Future measured NC terminal discharge is supplied in every rollout.',
                                'Actual treated entry counts/current upstream speeds are supplied as future interface inputs.',
                                'No saturation/within-region wave law: physical stock limits only.',
                                'All seeds23/33/43 were previously inspected; folds are development falsification,not fresh validation.',
                                'Three native seeds are insufficient for a precise expected treatment effect.'],
                   commands=command_ref, lags_30s=LAGS, fixed_ridge_penalty=1.,
                   feature_causality_canaries=checks, source_pins=pins, results=result,
                   new_native_runs=0, production_changes=0)
    (out / 'result.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    for mode, folds in result.items():
        print(mode, {seed: {arm: [round(v['fitted']['actual_delta_ttt30'],5),
                                    round(v['fitted']['predicted_delta_ttt30'],5),
                                    round(v['zero_response']['predicted_delta_ttt30'],5)]
                           for arm,v in fold['tests'].items()} for seed,fold in folds.items()}, flush=True)
    for path, pin in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == pin


if __name__ == '__main__':
    main()
