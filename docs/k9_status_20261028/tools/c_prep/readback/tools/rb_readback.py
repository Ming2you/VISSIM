# -*- coding: utf-8 -*-
"""rb_readback.py (c_port/readback, 2026-10-27 KST) - meter readback vs command, rule RB_RULE.md K0-K6. Read-only.

Usage: python -B rb_readback.py <out_dir> <tag>=<run_dir> [<tag>=<run_dir> ...]
  run_dir holds action_*.csv, runlog_*.txt and decisions_*/ (signal_readback.csv, action_<T>.csv).
Writes <out_dir>/readback.json and <out_dir>/cycles_<tag>.csv only.

Runner semantics used (read, FRZ_B1 vbs and V-A frozen c20aff1d vbs):
  RampStateAt(g, t): pos = t mod 10; g <= 0 -> RED; pos < g -> GREEN; pos < g + amber -> AMBER; else RED.
  Each stop t: post_step rows first (state held over [previous stop, t)), then writes (immediate rows, state from t).
Definitions (RB_RULE.md):
  g(t) = green_sec of the last action-CSV ramp_meter row of that SC with sim_sec <= t; E(t) = RampStateAt(g(t), t).
  S(t) = readback_state of the last readback row (file order) with sim_sec <= t, for integer t ([t, t+1)).
  observed second of a row: immediate t -> t ; post_step t -> t - 1.
  Control window seconds 900 <= s < 9000 (cycles c = 900, 910, ..., 8990).
"""
import bisect
import collections
import csv
import glob
import hashlib
import json
import math
import os
import re
import sys

SCS = list(range(9101, 9109))
CTRL0, CTRL1 = 900, 9000


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ramp_state(g, t, amber):
    pos = t % 10
    if g <= 0:
        return 'RED'
    if pos < g:
        return 'GREEN'
    if pos < g + amber:
        return 'AMBER'
    return 'RED'


def one(pattern):
    m = sorted(glob.glob(pattern))
    if len(m) != 1:
        raise SystemExit('expected one match for %s, got %d' % (pattern, len(m)))
    return m[0].replace('\\', '/')


def parse_meta(s):
    d = {}
    for part in (s or '').split(';'):
        if '=' in part:
            k, v = part.split('=', 1)
            d[k] = v
    return d


def analyse(tag, rd):
    o = {'run_dir': rd}
    act = one(rd + '/action_*.csv')
    runlog = one(rd + '/runlog_*.txt')
    ddir = one(rd + '/decisions_*')
    rbf = ddir + '/signal_readback.csv'
    o['files'] = {'action_csv': [act, sha256(act)], 'runlog': [runlog, sha256(runlog)], 'readback_csv': [rbf, sha256(rbf)]}
    # runlog settings
    amber = None
    scs_line = None
    with open(runlog, 'r', encoding='utf-8', errors='replace') as fh:
        for ln in fh:
            if ln.startswith('RAMP_AMBER_SEC=') and amber is None:
                amber = int(ln.strip().split('=', 1)[1])
            elif ln.startswith('RAMP_METER_SCS=') and scs_line is None:
                scs_line = ln.strip().split('=', 1)[1]
    o['runlog_RAMP_AMBER_SEC'] = amber
    o['runlog_RAMP_METER_SCS'] = scs_line
    if amber is None:
        raise SystemExit('no RAMP_AMBER_SEC in runlog')
    # commands (main action CSV)
    cmd = collections.defaultdict(list)          # sc -> [(T, g, rate, id, group_rate)]
    with open(act, newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh):
            if row['kind'] != 'ramp_meter':
                continue
            T = int(float(row['sim_sec']))
            sc = int(row['sc_no'])
            md = parse_meta(row.get('metadata'))
            cmd[sc].append((T, float(row['green_sec']), float(row['rate_vph']), row['id'],
                            float(md['group_rate_vph']) if 'group_rate_vph' in md else None))
    for sc in cmd:
        cmd[sc].sort(key=lambda x: x[0])
    sc_id = {sc: cmd[sc][0][3] for sc in cmd}
    o['sc_to_meter'] = {str(sc): sc_id[sc] for sc in sorted(sc_id)}
    # K0: command source cross-check vs decisions/action_<T>.csv, rate = 90 g, integer g
    k0 = {'rows': 0, 'match': 0, 'missing_decision_file': 0, 'rate_eq_90g': 0, 'nonint_green': 0, 'examples': []}
    dec_cache = {}
    for sc in sorted(cmd):
        for T, g, rate, mid, grp in cmd[sc]:
            k0['rows'] += 1
            if abs(rate - 90.0 * g) < 1e-6:
                k0['rate_eq_90g'] += 1
            if abs(g - round(g)) > 1e-9:
                k0['nonint_green'] += 1
            df = '%s/action_%06d.csv' % (ddir, T)
            if df not in dec_cache:
                if os.path.exists(df):
                    rows = {}
                    with open(df, newline='', encoding='utf-8', errors='replace') as fh:
                        for r in csv.DictReader(fh):
                            if r['kind'] == 'ramp_meter':
                                rows[int(r['sc_no'])] = (float(r['green_sec']), float(r['rate_vph']), r['id'])
                    dec_cache[df] = rows
                else:
                    dec_cache[df] = None
            rows = dec_cache[df]
            if rows is None:
                k0['missing_decision_file'] += 1
                continue
            d = rows.get(sc)
            if d is not None and abs(d[0] - g) < 1e-9 and abs(d[1] - rate) < 1e-6 and d[2] == mid:
                k0['match'] += 1
            elif len(k0['examples']) < 10:
                k0['examples'].append([sc, T, g, rate, d])
    o['K0_command_source'] = k0
    cmdT = {sc: [x[0] for x in cmd[sc]] for sc in cmd}

    def g_at(sc, t):
        i = bisect.bisect_right(cmdT[sc], t) - 1
        return cmd[sc][i][1] if i >= 0 else None

    # readback rows
    rows = collections.defaultdict(list)          # sc -> [(t, stage, req, rb, ok, fileidx)]
    n_all = 0
    with open(rbf, newline='', encoding='utf-8', errors='replace') as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            n_all += 1
            sc = int(row['sc_no'])
            if sc not in SCS:
                continue
            rows[sc].append((int(float(row['sim_sec'])), row['stage'], row['requested_state'].strip().upper(),
                             row['readback_state'].strip().upper(), row['ok'].strip(), i, int(row['sg_no'])))
    o['readback_rows_all_sc'] = n_all
    per = {}
    cyc_lines = []
    for sc in SCS:
        R = rows.get(sc, [])
        m = {'meter': sc_id.get(sc), 'rows': len(R), 'sg_values': sorted({r[6] for r in R})}
        # windows by observed second
        def obs_sec(r):
            return r[0] if r[1] == 'immediate' else r[0] - 1
        stages = collections.Counter()
        k1 = collections.Counter()
        k2 = collections.Counter()
        k2_ex = []
        for r in R:
            s = obs_sec(r)
            win = 'warm' if s < CTRL0 else ('ctrl' if s < CTRL1 else 'after')
            stages[(win, r[1])] += 1
            good1 = (r[2] == r[3] and r[4] == '1')
            k1[(win, r[1], good1)] += 1
            g = g_at(sc, s)
            if g is None:
                k2[(win, r[1], 'no_cmd')] += 1
                continue
            e = ramp_state(g, s, amber)
            good2 = (r[3] == e)
            k2[(win, r[1], good2)] += 1
            if not good2 and len(k2_ex) < 20:
                k2_ex.append([r[0], r[1], r[2], r[3], e, g])
        m['rows_by_window_stage'] = {'%s|%s' % k: v for k, v in sorted(stages.items())}
        m['K1_req_eq_rb_ok'] = {'%s|%s|%s' % k: v for k, v in sorted(k1.items())}
        m['K2_rb_eq_expected'] = {'%s|%s|%s' % k: v for k, v in sorted(k2.items())}
        m['K2_examples'] = k2_ex
        # timeline S(t)
        times = [r[0] for r in R]  # file order is time-sorted? check
        m['file_order_time_sorted'] = all(times[i] <= times[i + 1] for i in range(len(times) - 1))
        Rs = sorted(R, key=lambda r: (r[0], r[5]))
        ts = [r[0] for r in Rs]

        def S(t):
            i = bisect.bisect_right(ts, t) - 1
            return Rs[i][3] if i >= 0 else None
        # K3 cycles, K4 seconds
        n_cyc = 0
        cyc_match = 0
        cyc_mis = []
        g_hist = collections.Counter()
        sec_match = 0
        sec_n = 0
        for c in range(CTRL0, CTRL1, 10):
            g = g_at(sc, c)
            gcmd = sum(1 for p in range(10) if ramp_state(g, c + p, amber) == 'GREEN')
            states = [S(c + p) for p in range(10)]
            gobs = sum(1 for x in states if x == 'GREEN')
            n_cyc += 1
            g_hist[g] += 1
            ok = (gobs == gcmd)
            cyc_match += ok
            for p in range(10):
                sec_n += 1
                if states[p] == ramp_state(g_at(sc, c + p), c + p, amber):
                    sec_match += 1
            if not ok:
                cyc_mis.append([c, g, gcmd, gobs, ''.join((x or '-')[0] for x in states)])
            cyc_lines.append([tag, sc, sc_id.get(sc), c, g, gcmd, gobs, int(ok)])
        m['K3_cycles'] = n_cyc
        m['K3_cycle_match'] = cyc_match
        m['K3_cycle_mismatch_n'] = len(cyc_mis)
        m['K3_cycle_mismatch_examples'] = cyc_mis[:50]
        m['cmd_green_cycles'] = {str(int(k) if k == int(k) else k): v for k, v in sorted(g_hist.items())}
        m['K4_seconds'] = sec_n
        m['K4_second_match'] = sec_match
        # K5 write pairs in control window
        writes = [r for r in Rs if r[1] == 'immediate' and CTRL0 <= r[0] < CTRL1]
        imm_all = [r for r in Rs if r[1] == 'immediate']
        k5 = collections.Counter()
        k5_ex = []
        for w in writes:
            later = [r for r in imm_all if (r[0], r[5]) > (w[0], w[5])]
            tn = later[0][0] if later else CTRL1 + 1
            posts = [r for r in Rs if r[1] == 'post_step' and w[0] < r[0] <= tn]
            ok_w = (w[2] == w[3] and w[4] == '1')
            has_post = len(posts) > 0
            same = has_post and all(p[3] == w[3] for p in posts)
            k5[(ok_w, has_post, same)] += 1
            if not (ok_w and same) and len(k5_ex) < 20:
                k5_ex.append([w[0], w[2], w[3], w[4], tn, [(p[0], p[3]) for p in posts][:5]])
        m['K5_writes_ctrl'] = len(writes)
        m['K5_ok_and_post_same'] = k5[(True, True, True)]
        m['K5_breakdown'] = {'%s|%s|%s' % k: v for k, v in sorted(k5.items())}
        m['K5_examples'] = k5_ex
        m['K5_boundary_post_rows_ctrl'] = sum(1 for r in Rs if r[1] == 'post_step' and r[0] % 150 == 0 and CTRL0 < r[0] <= CTRL1)
        # K6 bracketed seconds
        obs = sorted(((obs_sec(r), r[5], r[3]) for r in R), key=lambda x: (x[0], x[1]))
        br = set()
        for a, b in zip(obs, obs[1:]):
            br.add(a[0])
            if a[2] == b[2]:
                for s in range(a[0], b[0] + 1):
                    br.add(s)
        if obs:
            br.add(obs[-1][0])
        m['K6_bracketed_seconds_ctrl'] = sum(1 for s in br if CTRL0 <= s < CTRL1)
        m['K6_observed_seconds_ctrl'] = len({x[0] for x in obs if CTRL0 <= x[0] < CTRL1})
        # warm-up summary
        m['warm_states'] = dict(collections.Counter(r[3] for r in R if obs_sec(r) < CTRL0))
        per[str(sc)] = m
    o['meters'] = per
    return o, cyc_lines


def main():
    out_dir = sys.argv[1]
    res = {'tool': 'rb_readback.py', 'runs': {}}
    for spec in sys.argv[2:]:
        tag, rd = spec.split('=', 1)
        o, lines = analyse(tag, rd.replace('\\', '/'))
        res['runs'][tag] = o
        cp = os.path.join(out_dir, 'cycles_%s.csv' % tag)
        with open(cp + '.tmp', 'w', newline='', encoding='utf-8') as g:
            w = csv.writer(g)
            w.writerow(['run', 'sc', 'meter', 'cycle_start', 'cmd_green_sec', 'cmd_green_count', 'obs_green_count', 'match'])
            w.writerows(lines)
        os.replace(cp + '.tmp', cp)
        tot = sum(m['K3_cycles'] for m in o['meters'].values())
        mat = sum(m['K3_cycle_match'] for m in o['meters'].values())
        print(tag, 'K3', mat, '/', tot, 'K0', o['K0_command_source']['match'], '/', o['K0_command_source']['rows'], flush=True)
    p = os.path.join(out_dir, 'readback.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(res, g, indent=1)
    os.replace(p + '.tmp', p)


if __name__ == '__main__':
    main()
