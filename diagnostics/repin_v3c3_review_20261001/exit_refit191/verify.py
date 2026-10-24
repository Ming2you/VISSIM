"""Audit saved191 results only; no forecasts, fitting, or native execution."""
import json
import math
from pathlib import Path

import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
SOURCE = h.R / 'exit_spatial190/attempt2'


def leaves(value, path=()):
    if isinstance(value, dict):
        return {p: v for k, x in value.items() for p, v in leaves(x, path + (k,)).items()}
    return {path: value}


def main():
    proto = h.read(HERE / 'protocol.json')
    evaluations = h.read(HERE / 'evaluations.json')
    selections = h.read(HERE / 'selection_frozen.json')
    validation = h.read(HERE / 'validation.json')
    fixedrows = h.read(SOURCE / 'forecast/rows.json')
    original = h.read(h.R / 'lane_state132/eval_01/reference_config.json')
    keys = ('acceleration_sec', 'downstream_ge_local', 'downstream_lt_local')
    allowed = {('freeway', 'state_response', 'FW_E', 'cell_overrides', '20', group, key): axis
               for group, key, axis in [('relaxation', keys[0], 0), ('anticipation', keys[1], 1), ('anticipation', keys[2], 1)]}
    count = parity = pins = checks = 0
    maximum = courant = 0.
    score_table = []

    def exact(a, b):
        nonlocal checks, maximum
        error = abs(a - b)
        assert error < 1e-7, (a, b, error)
        checks += 1
        maximum = max(maximum, error)

    mapping = h.read(h.F / 'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    offsets = dict(zip(mapping['chain_links'], mapping['chain_offsets_m']))
    bounds = mapping['segment_bounds_m']
    midpoint = (bounds[20] + bounds[21]) / 2
    half = (bounds[21] - bounds[20]) / 2000
    raw = h.read(h.F / 'route_inventory/initial_raw.json')['vehicle_records']['records']
    native = {(p, g): [] for p in (0, 1) for g in (1, 2, 3)}
    for v in raw:
        if v['link_no'] not in offsets:
            continue
        x = offsets[v['link_no']] + v['position_m']
        if bounds[20] <= x < bounds[21]:
            native[int(x >= midpoint), v['lane_index']].append(v['speed_kph'])

    for e in evaluations:
        folder = Path(e['folder'])
        z = e['z']
        a, b = leaves(original), leaves(h.read(folder / 'reference_config.json'))
        assert a.keys() == b.keys()
        for path, old in a.items():
            if path in allowed:
                exact(b[path], old * z[allowed[path]])
            else:
                assert b[path] == old, path
        for name in ('executed_function_sources.json', 'spec.json', 'coefficients.json'):
            assert (folder / name).read_bytes() == (SOURCE / name).read_bytes()
        rows = [r for r in h.read(folder / 'forecast/rows.json') if r['horizon'] == 450]
        assert rows == e['rows']
        assert len(rows) == (1 if e['scope'] == 'parity' else 4)
        assert all(r['case'] == 's29_late' and r['conservation_max'] < 1e-7 for r in rows)
        assert h.losses(rows, z) == e['loss']
        count += len(rows)
        score_table.append(dict(structure=e['structure'], tag=e['tag'], z=z,
                                **{k: e['loss'][k] for k in ('absolute', 'local', 'response', 'objective')}))
        saved = h.read(folder / 'forecast/preservation.json')
        assert saved['hooks_restored'] and saved['protected_and_STOP']
        for path, digest in saved['input_sha256'].items():
            assert h.sha(path) == digest, path
            pins += 1
        for r in rows:
            filename = r['case'] + '_' + r['arm']
            if e['scope'] == 'parity':
                pred = h.read(folder / 'forecast' / e['structure'] / (filename + '.json.gz'))
                old = h.read(SOURCE / 'forecast' / e['structure'] / (filename + '.json.gz'))
                assert all(pred[k] == old[k] for k in ('cells', 'flows', 'ports', 'ramps'))
                parity += 1
            if e['structure'] != 'spatial':
                continue
            d = h.read(folder / 'forecast/spatial' / (filename + '_spatial.json.gz'))
            previous = {}
            for p, g in native:
                n = sum(d['initial']['stocks'][p][g-1].values())
                v = d['initial']['speeds'][p][g-1]
                exact(n, len(native[p, g]))
                if n:
                    exact(v, sum(native[p, g]) / n)
                previous[p, g] = n, v
            parts = {}
            for row in d['parts']:
                parts.setdefault(round(row['time_s'], 6), []).append(row)
            assert len(parts) == 450
            lanes = {(round(x['time_s'], 6), x['cell'], x['lane']): x for x in d['lanes']}
            junction = {round(x['time_s'] + 1, 6): x for x in d['junction']}
            for t, ps in sorted(parts.items()):
                assert len(ps) == 6
                for x in ps:
                    assert -1e-8 <= x['n_veh'] <= 180 * half + 1e-7
                    assert math.isfinite(x['v_kmh']) and x['v_kmh'] >= 0
                    courant = max(courant, previous[x['part'], x['lane']][1] / 3600 / half)
                internal = sum(x['internal_veh'] for x in ps if x['part'] == 0)
                delta = [sum(x['n_veh'] for x in ps if x['part'] == p) - sum(previous[p, g][0] for g in (1, 2, 3)) for p in (0, 1)]
                exact(delta[0], sum(lanes[t, 20, g]['mainline_in_veh'] for g in (1, 2, 3)) - internal)
                exact(delta[1], internal - sum(lanes[t, 20, g]['mainline_out_veh'] for g in (1, 2, 3)) - junction[t]['off_accepted_veh'])
                for g in (1, 2, 3):
                    pair = [x for x in ps if x['lane'] == g]
                    n = sum(x['n_veh'] for x in pair)
                    exact(n, lanes[t, 20, g]['n_veh'])
                    if n > 1e-9:
                        exact(sum(x['n_veh'] * x['v_kmh'] for x in pair) / n, lanes[t, 20, g]['v_kmh'])
                    exact(pair[0]['internal_veh'], pair[1]['internal_veh'])
                previous = {(x['part'], x['lane']): (x['n_veh'], x['v_kmh']) for x in ps}
            assert d['max_residual'] < 1e-7 and d['max_courant'] <= 1 + 1e-9

    for structure in ('baseline', 'spatial'):
        proposal = h.read(HERE / (structure + '_proposal.json'))
        J, r, step = map(np.array, (proposal['jacobian'], proposal['residual'], proposal['step']))
        grad = J.T @ (r + J @ step) + .05 * step
        assert np.max(np.abs(grad - proposal['gradient'])) < 1e-10
        assert np.max(np.abs(step)) <= .2 + 1e-10
        for x, g in zip(step, grad):
            assert (abs(x) < .2-1e-8 and abs(g) < 1e-7) or (x <= -.2+1e-8 and g >= -1e-7) or (x >= .2-1e-8 and g <= 1e-7)
        base = h.losses([r for r in fixedrows if r['case'] == 's29_late' and r['mode'] == structure and r['horizon'] == 450], [1., 1.])
        proposals = [e for e in evaluations if e['structure'] == structure and e['tag'] in ('full', 'half')]
        acceptable = [e for e in proposals if e['loss']['objective'] <= .95 * base['objective'] and e['loss']['response'] <= base['response'] + 1e-12]
        assert not acceptable
        assert selections[structure]['tag'] == 'fixed' and not selections[structure]['train_qualified']
        assert selections[structure]['z'] == [1., 1.]
        reused = [r for r in fixedrows if r['case'] != 's29_late' and r['mode'] == structure and r['horizon'] == 450]
        assert validation[structure]['rows'] == reused
        assert h.losses(reused, [1., 1.]) == validation[structure]['loss']
        assert not validation[structure]['passed']
    preservation = h.read(HERE / 'preservation.json')
    for path, digest in {**preservation['input_sha256'], **proto['protected_sha256'], proto['STOP']['path']: proto['STOP']['sha256']}.items():
        assert h.sha(path) == digest, path
        pins += 1
    oldpins = h.read(SOURCE / 'forecast/preservation.json')['input_sha256']
    runner = h.ROOT / 'diagnostics/repin_v3c3_review_20261001/state_lateral168/run.py'
    assert h.sha(HERE / 'runner_before191.py.txt') == oldpins[str(runner)]
    assert count == 34 and parity == 2 and courant <= 1 + 1e-9
    result = dict(status='pass', completed450=count, parity_four_tables=parity,
                  stock_moment_checks=checks, max_residual=maximum, max_courant=courant,
                  immutable_pin_checks=pins, changed_config_leaves_only=list(keys),
                  train_rejection_reproduced=True, validation_reused_not_refit=True,
                  previous190_runner_archived_exact=True, production_adopted=False)
    h.save(HERE / 'verification.json', result)
    h.save(HERE / 'score_table.json', score_table)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
