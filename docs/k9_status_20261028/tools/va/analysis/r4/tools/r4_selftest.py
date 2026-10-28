r"""V-A r4 self test on SYNTHETIC data only (no run data is read).  python -B r4_selftest.py
1. grid_bins == closed_form for first times on the 5 s frame grid (incl. t0 and t1 themselves).
2. First-observation identity: two synthetic runs with one arrival stream; brute-force integral of U_a - U_b on a 0.05 s
   grid (U = arrivals - first-observed) equals S_b - S_a from grid_bins.
3. r4_fzp_first.scan_path on a small synthetic FZP: 0.10 s row skipped, header by name, first frame/link, closed form.
4. vhr_sint (verified [0, W] formula) equals closed_form shifted to [0, W] on the same synthetic times.
5. va_common.label / stats reproduce two hand cases.
Writes AV/r4/selftest/selftest.json; last line ALL_OK or FAIL."""
import io
import json
import os
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4_common as RC  # noqa: E402
import r4_fzp_first as FZ  # noqa: E402
import r4_firstobs as FO  # noqa: E402
import numpy as np  # noqa: E402

V = RC.V
SELF = os.path.join(RC.R4, 'selftest')
res = {}


def ok(name, cond, info=None):
    res[name] = {'ok': bool(cond), 'info': info}
    print(name, 'ok' if cond else 'FAIL', info if info is not None else '')


def frames():
    return [round(RC.T0 + 5 * i, 1) for i in range(1799)]


def main():
    rnd = random.Random(20261026)
    fr = frames()
    # 1
    ft = [rnd.choice(fr) for _ in range(5000)] + [RC.T0, RC.T1, RC.T1]
    b = RC.grid_bins(ft)
    ok('1_grid_equals_closed_form', abs(b.sum() - RC.closed_form(ft)) < 1e-6, float(b.sum() - RC.closed_form(ft)))
    ok('1_bins_len', len(b) == RC.NB, len(b))
    # 2: one arrival stream, two insertion-delay patterns, first observation = first frame >= insertion
    arr = sorted(rnd.uniform(0.0, 8990.0) for _ in range(3000))

    def first_obs(delays):
        out = []
        for a, d in zip(arr, delays):
            t = a + d
            k = int(np.ceil((t - RC.T0) / 5.0 - 1e-12))
            k = max(k, 0)
            if k <= 1798:
                out.append(fr[k])
        return out
    fa = first_obs([rnd.expovariate(1 / 30.0) for _ in arr])
    fb = first_obs([rnd.expovariate(1 / 5.0) for _ in arr])
    g = np.arange(RC.T0 + 0.025, RC.T1, 0.05)
    A = np.searchsorted(np.asarray(arr), g, side='right')
    Ua = A - np.searchsorted(np.sort(fa), g, side='right')
    Ub = A - np.searchsorted(np.sort(fb), g, side='right')
    brute = float(np.sum(Ua - Ub) * 0.05 / 3600.0)
    fo = float(RC.grid_bins(fb).sum() - RC.grid_bins(fa).sum())
    ok('2_first_obs_identity', abs(brute - fo) < 1e-6, (brute, fo))
    # 3: synthetic FZP
    os.makedirs(SELF, exist_ok=True)
    p = os.path.join(SELF, 'synthetic.fzp')
    lines = ['$VISION', '* synthetic', '* ', '$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;TMINNETTOT',
             '0.10;1;90;1;1.1;0.10', '5.10;1;90;2;64.0;5.10', '5.10;2;26;1;60.7;5.00', '10.10;1;91;1;3.0;10.10',
             '10.10;2;26;1;90.0;10.00', '10.10;3;74;1;5.0;2.00', '15.10;3;74;1;55.0;7.00', '15.10;4;1220044500;1;9.0;1.0']
    with io.open(p, 'w', encoding='ascii', newline='\r\n') as h:
        h.write('\n'.join(lines) + '\n')
    z = FZ.scan_path(p, 'synthetic')
    want_cf = ((15.1 - 5.1) * 2 + (15.1 - 10.1) + 0.0) / 3600.0
    ok('3_fzp_scan', z['skipped_0p10_rows'] == 1 and z['vehicles'] == 4 and z['frames'] == 3 and z['first_frame_sec'] == 5.1
       and z['last_frame_sec'] == 15.1 and abs(z['closed_form_window_veh_h'] - want_cf) < 1e-12
       and z['hist_by_first_link_t10'] == {'90': {'51': 1}, '26': {'51': 1}, '74': {'101': 1}, '1220044500': {'151': 1}},
       {k: z[k] for k in ('skipped_0p10_rows', 'vehicles', 'frames', 'first_frame_sec', 'last_frame_sec',
                          'closed_form_window_veh_h', 'hist_by_first_link_t10')})
    # 4: vhr [0, W] formula vs closed form on [0, W]
    d = {'by_cat': {'x': {}}}
    for t in ft:
        k = str(int(round(t * 10)))
        d['by_cat']['x'][k] = d['by_cat']['x'].get(k, 0) + 1
    ok('4_vhr_sint', abs(FO.vhr_sint(d, 9000) - RC.closed_form(ft, 9000)) < 1e-6,
       (FO.vhr_sint(d, 9000), RC.closed_form(ft, 9000)))
    # 5: label and stats (r3 code)
    l1 = V.label({'M3': -10, 'M4': -5, 'OUT_a': 5, 'M4b': -1, 'REM': -1, 'REM_B': -1})
    l2 = V.label({'M3': -10, 'M4': -12, 'OUT_a': -2, 'M4b': 1, 'REM': -1, 'REM_B': -1})
    l3 = V.label({'M3': 0, 'M4': -12, 'OUT_a': -2, 'M4b': -1, 'REM': -1, 'REM_B': -1})
    ok('5_label', l1['N'] == V.LABEL_MOVED and l2['N'] == V.LABEL_SAME and l2['W_A'] == V.LABEL_MOVED and l3['N'] == V.LABEL_NA,
       (l1, l2, l3))
    st = V.stats([-1.0, -2.0, -3.0], [10.0, 10.0, 10.0])
    ok('5_stats', abs(st['mean'] + 2) < 1e-12 and abs(st['sd'] - 1) < 1e-12 and st['neg'] == 3 and abs(st['pct_of_nc'] + 20) < 1e-12
       and st['ci_excludes_0'] and abs(st['half90'] - 2.920 / np.sqrt(3)) < 1e-12, st)
    # 6: full r4_firstobs pipeline dry run with SYNTHETIC first-observation times (structure test only).
    #    Real r3 va_metrics.json / scan.json metadata / published vhr and Omega701 inputs are loaded as they are; every
    #    insertions[k].first_seen_times is replaced by random frame times before any value is computed, and the
    #    fzp_first files are synthesised from the same times.  Outputs go to AV/r4/selftest/out_dry (not AV/r4/out).
    if '--no-dry' not in sys.argv:
        dry = os.path.join(SELF, 'out_dry')
        os.makedirs(dry, exist_ok=True)
        real_load = FO.load

        def fake_load(preflight):
            M, scans, info, fz, vh, o701 = real_load(True)
            fz = {}
            r2 = random.Random(7)
            for tag, sc in scans.items():
                n = 0
                hist = {}
                tot = 0.0
                for k, v in sc['insertions'].items():
                    ts = sorted(r2.choice(fr) for _ in range(r2.randint(20, 120)))
                    v['first_seen_times'] = ts
                    n += len(ts)
                    lk = {'1098': '74', '1099': '26'}.get(k, 'x' + k)
                    for t in ts:
                        hist.setdefault(lk, {})
                        kk = str(int(round(t * 10)))
                        hist[lk][kk] = hist[lk].get(kk, 0) + 1
                        tot += RC.T1 - t
                sc['vehicles_seen'] = n
                fz[tag] = {'vehicles': n, 'frames': 1799, 'first_frame_sec': RC.T0, 'last_frame_sec': RC.T1,
                           'irregular_steps': 0, 'skipped_0p10_rows': 0, 'fzp_bytes': sc.get('fzp_bytes'),
                           'closed_form_window_veh_h': tot / 3600.0, 'hist_by_first_link_t10': hist}
            return M, scans, info, fz, vh, o701
        out_real = RC.OUT
        FO.load = fake_load
        RC.OUT = dry
        argv = sys.argv
        sys.argv = ['r4_firstobs.py']
        code = 0
        try:
            FO.main()
        except SystemExit as e:  # noqa: PERF203
            code = e.code
        finally:
            FO.load = real_load
            RC.OUT = out_real
            sys.argv = argv
        names = sorted(os.listdir(dry))
        T = RC.jload(os.path.join(dry, 'r4_tables.json')) if 'r4_tables.json' in names else {}
        ok('6_pipeline_dry_run', code in (0, None) and {'r4_firstobs.json', 'r4_cells.csv', 'r4_tables.json'} <= set(names)
           and len(T) >= 12 and not FO.STOPS, {'exit': code, 'files': names, 'tables': sorted(T), 'stops': FO.STOPS})
    allok = all(v['ok'] for v in res.values())
    RC.jdump({'results': res, 'all_ok': allok, 'script_sha256': V.sha(os.path.abspath(__file__))},
             os.path.join(SELF, 'selftest.json'))
    print('ALL_OK' if allok else 'FAIL')


if __name__ == '__main__':
    main()
