"""Locate saved RM response error by conserved cell flows and matched clocks.

Read-only retrospective audit. The saved future-speed oracle is an error
isolation experiment, never a deployable forecast. No new simulation or fit.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, CASES
from collections import defaultdict
import hashlib
import json

HERE = Path(__file__).resolve().parent
START, END = 2400, 2850
CHANNELS = ('main_in', 'merge', 'off', 'main_out')


def native(folder, moments):
    states = {(int(r['time_s']), int(r['cell'])): float(r['n'])
              for r in moments['rows'] if r['lane'] == 'all' and START <= r['time_s'] <= END}
    # Every cell is occupied here; do not silently fill missing observations.
    assert len(states) == 46 * 21
    flows = {}
    for r in e.rows(folder / 'flows_30s.csv'):
        t, c = int(float(r['window_end_s'])), int(r['cell'])
        if r['road'] != 'FW_E' or not START < t <= END:
            continue
        assert all(float(r[k]) == 0 for k in
                   ('unexplained_entries', 'unexplained_losses', 'native_removals', 'conservation_residual_veh'))
        f = dict(main_in=float(r['source_admissions']) + float(r['upstream_crossings']),
                 merge=float(r['ramp_merges']), off=float(r['off_departures']),
                 main_out=float(r['downstream_crossings']) + float(r['terminal_exits_inferred']))
        assert states[t, c] == float(r['end_n_veh'])
        assert states[t-30, c] == float(r['start_n_veh'])
        assert states[t, c] - states[t-30, c] == f['main_in'] + f['merge'] - f['off'] - f['main_out']
        flows[t, c] = f
    assert len(flows) == 15 * 21
    return states, flows


def predicted(pred, initial):
    states = dict(initial)
    for r in pred['lane_groups']['FW_E']:
        key = int(r['time_s']), int(r['cell'])
        states[key] = states.get(key, 0.) + r['n_veh']
    assert len(states) == 46 * 21
    rows = {(int(r['window_end_s']), int(r['cell'])): r
            for r in pred['flows'] if r['road'] == 'FW_E'}
    flows = {}
    for (t, c), r in rows.items():
        f = dict(main_in=r['source_admissions'] if c == 0 else rows[t, c-1]['downstream_crossings'],
                 merge=r['ramp_merges'], off=r['off_departures'],
                 main_out=r['downstream_crossings'] + r['terminal_exits'])
        assert abs(states[t, c] - states[t-30, c] - f['main_in'] - f['merge'] + f['off'] + f['main_out']) < 1e-7
        flows[t, c] = f
    total = sum(n * 10/3600 for (t, c), n in states.items() if t > START)
    reported = next(r['model_residence_10s_veh_h'] for r in pred['diagnostics']['roads'] if r['road'] == 'FW_E')
    assert abs(total - reported) < 1e-7
    return states, flows


def contrast(nc, rm):
    ns, nf = nc
    rs, rf = rm
    assert {c: n for (t, c), n in ns.items() if t == START} == {c: n for (t, c), n in rs.items() if t == START}
    result = []
    for c in range(21):
        ds = {t: rs[t, c] - ns[t, c] for t in range(START, END+1, 10)}
        df = {t: {k: rf[t, c][k] - nf[t, c][k] for k in CHANNELS} for t in range(START+30, END+1, 30)}
        moments = {k: sum(row[k] * (END-t+30)/3600 * (1 if k in ('main_in', 'merge') else -1)
                          for t, row in df.items()) for k in CHANNELS}
        sampled_30 = sum(ds[t] * 30/3600 for t in range(START+30, END+1, 30))
        assert abs(sum(moments.values()) - sampled_30) < 1e-7
        result.append(dict(cell=c, delta_ttt_10s=sum(ds[t]*10/3600 for t in range(START+10, END+1, 10)),
                           delta_ttt_30s=sampled_30, delta_end_n=ds[END],
                           delta_flow_counts={k: sum(row[k] for row in df.values()) for k in CHANNELS},
                           signed_30s_interface_moments=moments,
                           delta_stock_10s=ds, delta_flows_30s=df))
    return result


def main():
    out = HERE / 'rm_transport_audit_v1'
    out.mkdir(exist_ok=False)
    inputs = [Path(__file__)]
    result = {}
    for seed in (23, 33):
        _, folder, bank, start = next(r for r in CASES if r[0] == seed)
        assert start == START
        modes = defaultdict(dict)
        for arm in ('none', 'rm_ramp'):
            obs = folder if arm == 'none' else bank / 'observations' / arm
            path = HERE / f'rm_moments_v1/s{seed}_{arm}.json'
            inputs.extend([path, obs/'flows_30s.csv'])
            modes['native'][arm] = native(obs, e.load(path))
            initial = {key: n for key, n in modes['native'][arm][0].items() if key[0] == START}
            for mode, path in (
                ('causal_saved', HERE/f'port_origin_split_qualification_v2/prediction_{seed}_{arm}.json'),
                ('future_speed_all', HERE/f'rm_speed_oracle_v1/prediction_s{seed}_all_{arm}.json'),
                ('future_speed_downstream', HERE/f'rm_speed_oracle_v1/prediction_s{seed}_downstream_{arm}.json')):
                inputs.append(path)
                modes[mode][arm] = predicted(e.load(path), initial)
        bymode = {m: contrast(a['none'], a['rm_ramp']) for m, a in modes.items()}
        geometry = e.ObservationData(folder).geometry
        cells = {c['cell']: c for c in geometry['cells'] if c['road'] == 'FW_E'}
        rows = []
        for c in range(21):
            observed = bymode['native'][c]
            row = dict(cell=c, start_m=cells[c]['start_m'], end_m=cells[c]['end_m'],
                       delta_ttt_10s={m: r[c]['delta_ttt_10s'] for m, r in bymode.items()},
                       delta_end_n={m: r[c]['delta_end_n'] for m, r in bymode.items()})
            row['causal_error'] = row['delta_ttt_10s']['causal_saved'] - observed['delta_ttt_10s']
            row['future_speed_error'] = row['delta_ttt_10s']['future_speed_all'] - observed['delta_ttt_10s']
            rows.append(row)
        result[str(seed)] = dict(cells=rows, details=bymode,
            delta_mainline_ttt_10s={m: sum(r['delta_ttt_10s'] for r in rows_) for m, rows_ in bymode.items()},
            largest_future_speed_errors=sorted(rows, key=lambda r: abs(r['future_speed_error']), reverse=True)[:6])
        print(seed, result[str(seed)]['delta_mainline_ttt_10s'], flush=True)
        for row in result[str(seed)]['largest_future_speed_errors']:
            print('cell', row['cell'], row['delta_ttt_10s'], flush=True)
    e.save(out/'result.json', dict(results=result,
        scope='Saved development cases; retrospective component cell transport audit, not calibration or qualification',
        clocks='Compare native and model10s end-frame residence;30s interface moments separately close30s sampling exactly. Neither is native1s TTT.',
        no_native_runs=True, no_core_changes=True,
        pins={str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}))


if __name__ == '__main__':
    main()
