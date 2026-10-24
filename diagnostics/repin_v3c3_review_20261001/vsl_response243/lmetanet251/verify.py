"""Independent algebra, conservation and pairing audit of finished251 outputs."""
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    finished = h.read(HERE/'completion.json')
    assert finished['status'] == 'complete' and finished['forecasts450'] == 25
    protocol = h.read(HERE/'protocol.json'); pins = h.read(HERE/'pins.json')
    for p, digest in {**pins, **protocol['protected_sha256'], protocol['STOP']['path']:protocol['STOP']['sha256']}.items():
        assert h.sha(p) == digest, p
    evaluations = h.read(HERE/'evaluations.json'); selection = h.read(HERE/'selection_frozen.json')
    chosen = next(e for e in evaluations if e['tag'] == selection['tag'])
    val = next(e for e in evaluations if e.get('scope') == 'validation')
    assert chosen['z'] == val['z'] == selection['z']
    assert {r['case'] for e in evaluations if e.get('scope') == 'train' for r in e['rows']} == {'s67_late'}
    assert {r['case'] for r in val['rows']} == {'s29_late', 's43_early', 's61_late'}
    counts = dict(forecasts=0, baseline_tables=0, cell_balances=0, ramp_balances=0, off_balances=0,
                  friction_updates=0, lateral_matrices=0)
    maxima = dict(cell=0., ramp=0., off=0., friction=0., matrix=0., continuity=0.)
    effects = []; contrasts = []
    for e in evaluations:
        if e['tag'] != 'reused244_center':
            folder = HERE/e['tag']
            assert Path(h.read(folder/'setting.json')['manifest']).resolve() == (h.R/'lane_state132/eval_01/manifest.json').resolve()
            for p in (folder/'forecast/response243').glob('*.json.gz'):
                z = h.read(p); counts['forecasts'] += 1
                if e['z'] == [0., 0.]:
                    baseline = h.read(h.R/'queue_dynamics178/forecast/baseline'/p.name)
                    for key in ('cells', 'flows', 'ports', 'ramps'):
                        assert z[key] == baseline[key], (p, key)
                        counts['baseline_tables'] += 1
                n = {(round(r['time_s'], 6), r['cell']):r['n_veh'] for r in z['cells']}
                flows = {(round(r['window_end_s'], 6), r['cell']):r for r in z['flows']}
                for (end, cell), row in flows.items():
                    start = round(row['window_start_s'], 6)
                    if (start, cell) not in n: continue
                    incoming = flows[end, cell-1]['downstream_crossings'] if cell else 0.
                    residual = n[end, cell]-n[start, cell]-incoming-row['source_admissions']-row['ramp_merges']+row['off_departures']+row['downstream_crossings']+row['terminal_exits']
                    maxima['cell'] = max(maxima['cell'], abs(residual)); counts['cell_balances'] += 1
                for row in z['ramps']:
                    residual = row['end']['connector_veh']-row['start']['connector_veh']-row['admitted_arrivals_veh']+row['accepted_merge_veh']
                    maxima['ramp'] = max(maxima['ramp'], abs(residual)); counts['ramp_balances'] += 1
                before = {}
                for row in z['ports']:
                    key = row['connector']
                    if key in before:
                        old = before[key]
                        residual = row['n_veh']-old['n_veh']-(row['admitted_veh']-old['admitted_veh'])+(row['departed_veh']-old['departed_veh'])
                        maxima['off'] = max(maxima['off'], abs(residual)); counts['off_balances'] += 1
                    before[key] = row
                diag = z['diagnostics']['roads'][0]
                assert diag['negative_density_count'] == 0
                maxima['continuity'] = max(maxima['continuity'], diag['continuity_residual_max_veh'])
                groups = {}; matrices = {}
                for row in diag['joint_lane_region']['rows']:
                    a = row.get('friction251')
                    if a is None:
                        assert row['cell'] == 19
                        continue
                    assert [a['delta_in'], a['delta_out']] == e['z']
                    assert a['incoming'] >= 0 and a['outgoing'] >= 0
                    denominator = a['length_km']*(a['rho']+a['kappa'])
                    expected = a['speed']*(e['z'][0]*a['incoming']+e['z'][1]*a['outgoing'])/denominator
                    maxima['friction'] = max(maxima['friction'], abs(expected-a['loss']))
                    assert math.isfinite(a['loss']) and a['loss'] >= 0
                    assert row['v_kmh'] <= max(5., a['before']-a['loss'])+1e-9
                    assert abs(sum(a['matrix_in'])-a['incoming']) < 1e-12
                    assert abs(sum(a['matrix_out'])-a['outgoing']) < 1e-12
                    matrices.setdefault((row['time_s'], row['cell']), {})[row['lane']-1] = a
                    counts['friction_updates'] += 1
                    key = (row['cell'], row['lane'])
                    g = groups.setdefault(key, dict(steps=0, loss=0., incoming=0., outgoing=0., at_floor=0))
                    g['steps'] += 1; g['loss'] += a['loss']; g['incoming'] += a['incoming']; g['outgoing'] += a['outgoing']
                    g['at_floor'] += row['v_kmh'] <= 5.+1e-9
                for rows in matrices.values():
                    assert set(rows) == {0, 1, 2}
                    for a in range(3):
                        assert rows[a]['matrix_out'][a] == rows[a]['matrix_in'][a] == 0
                        for b in range(3):
                            maxima['matrix'] = max(maxima['matrix'], abs(rows[a]['matrix_out'][b]-rows[b]['matrix_in'][a]))
                    counts['lateral_matrices'] += 1
                effects.extend(dict(tag=e['tag'], record=p.name[:-8], cell=k[0], lane=k[1],
                                    mean_loss_per_step=g['loss']/g['steps'], **g) for k, g in groups.items())
        for case in sorted({r['case'] for r in e['rows']}):
            for t in (150, 450):
                by = {r['arm']:r for r in e['rows'] if r['case'] == case and r['horizon'] == t}
                for a, b in [('hold', 'release'), ('hold', 'hold_vsl90'), ('release', 'release_vsl90'), ('none', 'vsl')]:
                    if a not in by or b not in by: continue
                    keys = ('ttt', 'mainline_ttt', 'ramp_ttt', 'off_ttt', 'exits', 'end_n')
                    contrasts.append(dict(tag=e['tag'], case=case, horizon=t, change=b+'-'+a,
                        actual={k:by[b]['actual'][k]-by[a]['actual'][k] for k in keys},
                        predicted={k:by[b]['predicted'][k]-by[a]['predicted'][k] for k in keys}))
    assert counts['forecasts'] == 25 and counts['baseline_tables'] == 36
    assert counts['friction_updates'] == 25*450*6*3
    assert counts['lateral_matrices'] == 25*450*6
    assert max(maxima.values()) < 1e-7, maxima
    h.save(HERE/'contrasts.json', contrasts); h.save(HERE/'friction_effects.json', effects)
    result = dict(status='PASS', counts=counts, max_residual=maxima, source_STOP_preserved=True,
                  zero_coefficient_exact=True, qualification='Mechanical checks only, not accuracy/benefit qualification.',
                  continuity_scope='Independent cell check excludes first30s lacking initial vector in table; runtime continuity covers it.',
                  extra_forecasts=0, native=0, FZP=0, adopted=False)
    h.save(HERE/'verification.json', result); print(json.dumps(result))


if __name__ == '__main__':
    main()
