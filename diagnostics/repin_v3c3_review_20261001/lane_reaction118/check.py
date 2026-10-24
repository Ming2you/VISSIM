"""Fixed-coefficient test of lane aggregation in stopped-stock reactions.

Only existing short-run caches are read. This is conditional one-step evidence,
not autonomous prediction or a calibrated VSL benefit. No production hooks.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / 'stop_population114'


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                       allow_nan=False) + '\n', encoding='utf-8')


def main():
    assert not (HERE / 'protocol.json').exists(), 'Reuse completed check; no retry grid'
    old = read(OLD / 'protocol.json')
    fit = read(OLD / 'macro_results.json')
    theta = next(x['coefficients'] for x in fit['fits'] if x['model'] == 'state')
    geometry = read(ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    cells = {x['cell']: x for x in geometry['cells'] if x['road'] == 'FW_E'}
    # Source19 includes connector10613, whose lane numbers already match119.
    # All selected boundaries are inside119; the4->3 transition18->19 is out.
    for i in (19, 20, 21):
        assert cells[i]['canonical_segment_lanes'] == 3
    assert [x['link'] for x in cells[19]['physical_pieces']] == [10613, 119]
    assert [x['link'] for x in cells[20]['physical_pieces']] == [119]
    assert [x['link'] for x in cells[21]['physical_pieces']] == [119]
    protocol = dict(
        purpose='Does averaging lanes erase conditional stop/restart response in10483 approach cells19/20?',
        prior='108 rejects delayed route alignment as the main explanation for observed aligned exit cohort;107 receiving failed autonomously;114/117 aggregate stopped closure failed.',
        distinction='Same114 equation and coefficients, applied per physical lane rather than cell mean. No new rates, transport, grid, or VSL-specific term.',
        theta=theta, scope='FW_E zero-based cells19/20; downstream20/21. All boundaries use the same3 lane numbering.',
        conditional='Current observed lane N/v/stopped fraction predicts next5s label. Next record is used only as outcome and to identify censored records, never as a feature.',
        exposure='Only current vehicles whose next mainline speed is known, including cross-cell and cross-lane moves. Missing labels censored, not assumed stopped.',
        budget=dict(fits=0, native=0, fzp_scans=0, autonomous=0, alternatives=1),
        gate='Both43 and67:150s net-onset RMSE improves>=20% vs aggregate; paired net-onset-delta error improves>=20%. Otherwise no autonomous extension or refit.',
        gain_qualified=False, core_pins=old['core_pins'], input_pins=old['input_pins'],
        coefficient_sha256=sha(OLD / 'macro_results.json'))
    save('protocol.json', protocol)
    for p, h in old['core_pins'].items():
        assert sha(p) == h
    rows = []
    audit = []
    for case, pin in old['input_pins'].items():
        p = ROOT / pin['path']
        assert sha(p) == pin['sha256']
        with gzip.open(p, 'rt', encoding='utf-8') as stream:
            frames = {float(k): v for k, v in json.load(stream)['frames'].items()}
        times = sorted(frames)
        total = missing = 0
        # Same first450s as prior autonomous gates, not all available later data.
        for t, tn in zip(times, times[1:]):
            if t >= times[0] + 450 - 1e-6:
                break
            assert abs(tn-t-5) < 1e-7
            current, nxt = frames[t], frames[tn]
            groups = {i: {k: r for k, r in current.items() if r[0] == i} for i in (19, 20, 21)}
            assert all(r[3] in (1, 2, 3) for g in groups.values() for r in g.values())

            def prediction(i, local, down, lanes, known):
                n, nd = len(local), len(down)
                free = old['v_free'][str(i)]
                v = sum(r[1] for r in local.values()) / n if n else free
                vd = sum(r[1] for r in down.values()) / nd if nd else old['v_free'][str(i+1)]
                rho = n / (cells[i]['length_km'] * lanes)
                rd = nd / (cells[i+1]['length_km'] * lanes)
                blocked = sum(r[1] < 5 for r in down.values()) / nd if nd else 0.
                pressure = (rho / old['critical'][str(i)]) * (blocked + max(v-vd, 0.) / free + rd / old['rho_max'])
                room = max(vd, 0.) / old['v_free'][str(i+1)] * max(1-rd / old['rho_max'], 0.)
                a, b = theta[0] * pressure, theta[1] * room
                f = -math.expm1(-5*(a+b)) / (a+b) if a+b else 5.
                stopped = sum(r[1] < 5 for r in known.values())
                return [(len(known)-stopped)*a*f, stopped*b*f]

            for i in (19, 20):
                local, down = groups[i], groups[i+1]
                known = {k: r for k, r in local.items() if k in nxt}
                total += len(local)
                missing += len(local)-len(known)
                actual = [sum(r[1] >= 5 and nxt[k][1] < 5 for k, r in known.items()),
                          sum(r[1] < 5 and nxt[k][1] >= 5 for k, r in known.items())]
                aggregate = prediction(i, local, down, 3, known)
                lane = [0., 0.]
                for g in (1, 2, 3):
                    v = prediction(i, {k:r for k,r in local.items() if r[3] == g},
                                   {k:r for k,r in down.items() if r[3] == g}, 1,
                                   {k:r for k,r in known.items() if r[3] == g})
                    lane = [x+y for x,y in zip(lane, v)]
                rows.append(dict(case=case, cell=i, time=t, window=int(round(t-times[0],6)//150),
                                 actual=actual, aggregate=aggregate, lane=lane))
        audit.append(dict(case=case, exposures=total, censored=missing, fraction=missing/total))
    windows = []
    for case in old['input_pins']:
        for w in range(3):
            selected = [x for x in rows if x['case'] == case and x['window'] == w]
            assert len(selected) == 60
            sums = {k: [sum(x[k][j] for x in selected) for j in (0,1)] for k in ('actual','aggregate','lane')}
            windows.append(dict(case=case, window=w, **sums, net={k:v[0]-v[1] for k,v in sums.items()}))
    scores = []
    for seed in ('29','43','67'):
        selected = [x for x in windows if x['case'].startswith(seed+'_')]
        arms = ('release','release_vsl90') if seed == '67' else ('none','vsl')
        pairs = []
        for w in range(3):
            a,b = [next(x for x in selected if x['case'] == seed+'_'+arm and x['window'] == w) for arm in arms]
            pairs.append(dict(window=w, **{k:b['net'][k]-a['net'][k] for k in ('actual','aggregate','lane')}))
        rmse = {k:math.sqrt(sum((r['net'][k]-r['net']['actual'])**2 for r in selected)/len(selected)) for k in ('aggregate','lane')}
        delta_rmse = {k:math.sqrt(sum((r[k]-r['actual'])**2 for r in pairs)/3) for k in ('aggregate','lane')}
        scores.append(dict(seed=seed, net_rmse=rmse, delta_rmse=delta_rmse, pairs=pairs,
                           passed=rmse['lane'] <= .8*rmse['aggregate'] and delta_rmse['lane'] <= .8*delta_rmse['aggregate']))
    passed = all(x['passed'] for x in scores if x['seed'] != '29')
    save('rows.json', rows)
    save('results.json', dict(audit=audit, windows=windows, scores=scores,
                             decision='CONDITIONAL_PASS_ONLY' if passed else 'REJECT_LANE_REACTION', gain_qualified=False))
    for p,h in old['core_pins'].items():
        assert sha(p) == h
    save('completion.json', dict(status='complete', decision='CONDITIONAL_PASS_ONLY' if passed else 'REJECT_LANE_REACTION',
                                 rows=len(rows), production_modified=False, core_pins_preserved=True,
                                 fits=0, forecasts=0, fzp_scans=0, native=0, gain_qualified=False))
    print(json.dumps(scores, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
