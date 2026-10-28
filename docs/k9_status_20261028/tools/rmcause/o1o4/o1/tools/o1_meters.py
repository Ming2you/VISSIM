r"""O1 step 3: rule-RM meter commands actually written (decision_<T>.json audit, rule_history), the native readback
check (fixed_validation.json actual_green_windows from the meter SC LDP files) and the event file, per seed.
python -B o1_meters.py -> o1o4/o1/out/o1_meters.json, o1_meters_per_decision.csv.  Read only; small files."""
import csv
import glob
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'out')
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
SC_OF = {'RM_C10480': 9101, 'RM_C10482': 9102, 'RM_C10646': 9103, 'RM_C10644': 9104, 'RM_C10639': 9105,
         'RM_C10681': 9106, 'RM_C10490': 9107, 'RM_C10484': 9108}
FWE = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def runs(xs):
    """longest run of consecutive decisions (T step 150) in sorted list xs -> (len, start, end)"""
    best, cur, start = (0, None, None), 0, None
    prev = None
    for t in xs:
        if prev is not None and t == prev + 150:
            cur += 1
        else:
            cur, start = 1, t
        if cur > best[0]:
            best = (cur, start, t)
        prev = t
    return best


def main():
    os.makedirs(OUT, exist_ok=True)
    res, rows = {}, []
    for s in (31, 41):
        rd = os.path.join(ROOT, 's%d_v3c3rm' % s, 'run')
        files = sorted(glob.glob(os.path.join(rd, 'decision_[0-9]*.json')), key=lambda p: int(os.path.basename(p)[9:-5]))
        dec = []
        for p in files:
            with io.open(p, encoding='ascii') as f:
                d = json.load(f)
            dec.append(d)
        Ts = [d['sec'] for d in dec]
        per_meter = {}
        for m in SC_OF:
            g = [(d['sec'], d['meters'][m]['green_sec']) for d in dec]
            tight = [T for T, x in g if x < 10]
            r = runs(tight)
            occ = [(d['sec'], d['observations'][m]['occupancy_pct']) for d in dec]
            per_meter[m] = {
                'sc': SC_OF[m], 'fw': 'FW_E' if m in FWE else 'FW_W',
                'decisions': len(g), 'n_green_lt10': len(tight), 'first_T_lt10': tight[0] if tight else None,
                'last_T_lt10': tight[-1] if tight else None, 'longest_run_lt10': {'n': r[0], 'from_T': r[1], 'to_T': r[2]},
                'min_green': min(x for _, x in g), 'green_hist': {str(k): sum(1 for _, x in g if x == k) for k in range(0, 11)},
                'restricted_green_sec_total': sum((10 - x) * 15 for _, x in g),  # red seconds added vs open, per 150 s
                'n_occ_gt15': sum(1 for _, o in occ if o > 15.0), 'max_occ': max(o for _, o in occ),
                'max_occ_T': max(occ, key=lambda z: z[1])[0],
                'greens_by_T': {str(T): x for T, x in g}}
        for d in dec:
            for m in SC_OF:
                a, o = d['meters'][m], d['observations'][m]
                rows.append([s, d['sec'], m, SC_OF[m], 'FW_E' if m in FWE else 'FW_W', a['green_sec'], a['previous_green'],
                             round(a['raw_request_vph'], 1), round(a['bounded_request_vph'], 1), round(a['next_request_vph'], 1),
                             round(o['occupancy_pct'], 2), round(o['flow_vph_per_lane'], 1), round(o['speed_kph'], 1)])
        vsl_events = sum(1 for d in dec for e in d['events'] if e[1] == 'vsl')
        meter_events = sum(1 for d in dec for e in d['events'] if e[1] == 'meter')
        # native readback windows
        fv_p = os.path.join(rd, 'fixed_validation.json')
        with io.open(fv_p, encoding='utf-8-sig') as f:
            fv = json.load(f)
        win = fv.get('actual_green_windows', [])
        mism = []
        for w in win:
            exp = (w['end'] - w['start']) * w['green_sec_per10'] / 10.0
            if abs(w['observed_green_seconds'] - exp) > 1e-9:
                mism.append(w)
        cmd_by = {(SC_OF[m], T): per_meter[m]['greens_by_T'][str(T)] for m in SC_OF for T in Ts}
        win_cmd_mismatch = [w for w in win if cmd_by.get((int(w['sc']), int(w['start']))) != w['green_sec_per10']]
        # events file
        ev_p = os.path.join(rd, 'fixed_events.csv')
        kinds = {}
        with io.open(ev_p, encoding='ascii') as f:
            for r in csv.DictReader(f):
                kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
        with io.open(os.path.join(rd, 'rule_history.json'), encoding='ascii') as f:
            hist = json.load(f)
        fails = glob.glob(os.path.join(rd, 'decision_failure_*'))
        res['s%d' % s] = {
            'run_dir': rd, 'n_decisions': len(dec), 'T_first': Ts[0], 'T_last': Ts[-1],
            'T_contiguous': Ts == list(range(Ts[0], Ts[-1] + 1, 150)), 'arm_field': sorted(set(d['arm'] for d in dec)),
            'vsl_events_written': vsl_events, 'meter_events_written': meter_events,
            'decision_failure_files': [os.path.basename(p) for p in fails],
            'fixed_validation': {'path': fv_p, 'sha256': sha(fv_p), 'passed': fv.get('passed'),
                                 'event_readbacks': fv.get('event_readbacks'),
                                 'native_meter_samples_checked': fv.get('native_meter_samples_checked'),
                                 'untargeted_snapshot_same': fv.get('untargeted_snapshot_sha256_before') == fv.get('untargeted_snapshot_sha256_after'),
                                 'windows': len(win), 'windows_observed_ne_command': len(mism),
                                 'windows_command_ne_decision': len(win_cmd_mismatch)},
            'fixed_events': {'path': ev_p, 'sha256': sha(ev_p), 'rows_by_kind': kinds},
            'rule_history_final': hist, 'per_meter': per_meter,
            'any_fwe_lt10_T': sorted({T for m in FWE for T in Ts if per_meter[m]['greens_by_T'][str(T)] < 10}),
            'any_fww_lt10_T': sorted({T for m in SC_OF if m not in FWE for T in Ts if per_meter[m]['greens_by_T'][str(T)] < 10})}
    with io.open(os.path.join(OUT, 'o1_meters.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    with io.open(os.path.join(OUT, 'o1_meters_per_decision.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['seed', 'T', 'meter', 'sc', 'fw', 'green_sec', 'previous_green', 'raw_request_vph', 'bounded_request_vph',
                    'next_request_vph', 'occupancy_pct', 'flow_vph_per_lane', 'speed_kph'])
        w.writerows(rows)
    for s, r in res.items():
        print(s, r['n_decisions'], r['T_first'], r['T_last'], r['T_contiguous'], r['arm_field'], 'vsl_ev', r['vsl_events_written'],
              'meter_ev', r['meter_events_written'], r['fixed_validation'], r['fixed_events']['rows_by_kind'], r['decision_failure_files'])
        for m, p in r['per_meter'].items():
            print('  ', m, p['fw'], 'n<10', p['n_green_lt10'], 'first', p['first_T_lt10'], 'last', p['last_T_lt10'],
                  'run', p['longest_run_lt10'], 'min', p['min_green'], 'hist', {k: v for k, v in p['green_hist'].items() if v},
                  'occ>15', p['n_occ_gt15'], 'maxocc', round(p['max_occ'], 1), p['max_occ_T'])


if __name__ == '__main__':
    main()
