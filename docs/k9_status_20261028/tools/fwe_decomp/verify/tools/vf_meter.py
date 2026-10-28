# -*- coding: utf-8 -*-
"""vf_meter.py - VERIFY_FWE independent FW_E meter GREEN-second count (read-only). 2026-10-27 KST.

Sources per run (no FZP):
  readback  signal_readback.csv: per-second state = readback_state of the last 'immediate' row with sim_sec <= s
            (post_step rows are only used as a check: post_step at t must equal state(t-1)).
  command   run action CSV, kind=ramp_meter: green_sec of the last command with sim_sec <= cycle start.
  ldp       meter LDP (codex runs): state char of the record at c+1.0 ... c+10.0 ('I' = GREEN), rm_exec.py rule;
            alignment c+0.0 ... c+9.0 also counted as a sensitivity column.
GREEN only: yellow / red / blank are not green. Cycle = [c, c+10), c = 900, 910, ... < end.
Meter <-> SC mapping is read from the action CSV (id RM_C<conn> and sc_no), not assumed.
Usage: python -B vf_meter.py <out_json>
"""
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict

import numpy as np

FWE_CONN = ('10639', '10681', '10490', '10484')
RUNS = {
    'B_s31': ('D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc', 'sdmpc31_sdmpc9000_s31', 9000, None),
    'B_s41': ('D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc', 'sdmpc31_sdmpc9000_s41', 9000, None),
    'B_s43': ('D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc', 'sdmpc31_sdmpc9000_s43', 9000, None),
    'VA_s31': ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31', 'sdmpc31_v3c3_k92va_s31', 9000, None),
    'VA_s41': ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41', 'sdmpc31_v3c3_k92va_s41', 9000, None),
    'VA_s43': ('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43', 'sdmpc31_v3c3_k92va_s43', 9000, None),
    'CXJ_s29': ('D:/VISSIM_handoff/20261024/raw/joint/sdmpc', 'sdmpc31_sdmpc8100_s29', 8100,
                'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp'),
}
LDP_ONLY = {'CXNC_s29': ('D:/VISSIM_handoff/20261024/raw/nc/vissim_eval/sdmpc31_nc9000_s29_{sc}_001.ldp', 8100)}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def seed_of(root, stem):
    p = root + '/run_provenance_' + stem + '.json'
    return json.load(open(p, encoding='utf-8')).get('seed'), p, sha(p)


def cycles_summary(g, c0=900):
    g = np.asarray(g)
    cyc = c0 + 10 * np.arange(g.size)
    tight = g < 10
    out = {'n_cycles': int(g.size), 'n_tight10': int(tight.sum()), 'n_le6': int((g <= 6).sum()),
           'T_tight10': (int(cyc[tight][0]) if tight.any() else None),
           'T_tight6': (int(cyc[g <= 6][0]) if (g <= 6).any() else None),
           'mean_green': float(g.mean()), 'dist': {str(k): int(v) for k, v in zip(*np.unique(g, return_counts=True))}}
    # per 900 s window (cycles in [w, w+900)): tight fraction and mean green
    win = {}
    for w in range(c0, int(cyc[-1]) + 10, 900):
        m = (cyc >= w) & (cyc < w + 900)
        if m.any():
            win[str(w)] = {'tight_frac': float(tight[m].mean()), 'mean_green': float(g[m].mean()), 'n': int(m.sum())}
    out['win900'] = win
    # contiguous runs of tight cycles (first, last cycle start)
    runs = []; st = None
    for c, tt in zip(cyc, tight):
        if tt and st is None:
            st = c
        if not tt and st is not None:
            runs.append([int(st), int(c - 10)]); st = None
    if st is not None:
        runs.append([int(st), int(cyc[-1])])
    out['tight_runs_n'] = len(runs)
    out['tight_runs_first3'] = runs[:3]
    out['last_tight_cycle'] = (int(cyc[tight][-1]) if tight.any() else None)
    out['g'] = g.tolist()
    return out


def from_readback(path, scs, end):
    rows = defaultdict(list)
    chk = {'rows': 0, 'req_ne_read': 0, 'ok_ne_1': 0}
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['sc_no'] not in scs:
                continue
            chk['rows'] += 1
            if r['requested_state'] != r['readback_state']:
                chk['req_ne_read'] += 1
            if r['ok'] != '1':
                chk['ok_ne_1'] += 1
            rows[r['sc_no']].append((int(float(r['sim_sec'])), r['readback_state'], r['stage']))
    res = {}
    for sc in scs:
        imm = [(t, s) for t, s, st in rows[sc] if st == 'immediate']
        tw = np.array([t for t, _ in imm]); sw = [s for _, s in imm]
        secs = np.arange(0, end)
        idx = np.searchsorted(tw, secs, side='right') - 1
        state = np.array([sw[i] if i >= 0 else 'NONE' for i in idx])
        post = [(t, s) for t, s, st in rows[sc] if st == 'post_step']
        post_mis = sum(1 for t, s in post if 1 <= t <= end and state[t - 1] != s)
        green = (state == 'GREEN')
        g = [int(green[c:c + 10].sum()) for c in range(900, end, 10)]
        res[sc] = {'g': g, 'n_immediate': len(imm), 'n_post': len(post), 'post_mismatch': post_mis,
                   'states_seen': sorted(set(state.tolist()))}
    return res, chk


def from_commands(path, end):
    cmd = defaultdict(list); idmap = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r['kind'] != 'ramp_meter':
                continue
            idmap[r['sc_no']] = r['id']
            cmd[r['sc_no']].append((float(r['sim_sec']), float(r['green_sec'])))
    res = {}
    for sc, lst in cmd.items():
        lst.sort(key=lambda x: x[0])
        tw = np.array([a for a, _ in lst]); gw = [b for _, b in lst]
        g = []
        for c in range(900, end, 10):
            i = np.searchsorted(tw, c, side='right') - 1
            g.append(gw[i] if i >= 0 else None)
        res[sc] = g
    return res, idmap


def from_ldp(pattern, sc, end):
    st = {}
    for raw in open(pattern.format(sc=sc), 'rb'):
        s = raw.decode('latin-1').rstrip('\r\n')
        m = re.match(r'^\s*(\d+\.\d)\s+(\d+\.\d)(.*)$', s)
        if m:
            st[round(float(m.group(1)), 1)] = m.group(3)[:1]
    g1 = [sum(1 for k in range(1, 11) if st.get(round(c + k, 1)) == 'I') for c in range(900, end, 10)]
    g0 = [sum(1 for k in range(0, 10) if st.get(round(c + k, 1)) == 'I') for c in range(900, end, 10)]
    blank = sum(1 for c in range(900, end) if st.get(round(c + 1.0, 1), '') in ('', ' '))
    return g1, g0, blank, sha(pattern.format(sc=sc))


def main():
    out = {'tool_sha256': sha(__file__), 'runs': {}}
    for tag, (root, stem, end, ldp) in RUNS.items():
        seed, pp, ps = seed_of(root, stem)
        act = root + '/action_' + stem + '.csv'
        rb = root + '/decisions_' + stem + '/signal_readback.csv'
        cmds, idmap = from_commands(act, end)
        sc_of = {v.replace('RM_C', ''): k for k, v in idmap.items()}
        scs = [sc_of[c] for c in FWE_CONN]
        rbres, chk = from_readback(rb, set(scs), end)
        R = {'seed_provenance': seed, 'provenance': pp, 'provenance_sha256': ps, 'action_csv_sha256': sha(act),
             'readback_sha256': sha(rb), 'readback_checks': chk, 'sc_of_conn': {c: sc_of[c] for c in FWE_CONN}, 'meters': {}}
        for c in FWE_CONN:
            sc = sc_of[c]
            g_rb = rbres[sc]['g']
            m = {'readback': cycles_summary(g_rb), 'readback_post_mismatch': rbres[sc]['post_mismatch'],
                 'readback_states_seen': rbres[sc]['states_seen'],
                 'cmd_eq_readback_cycles': int(sum(1 for a, b in zip(cmds[sc], g_rb) if a is not None and int(round(a)) == b))}
            if ldp:
                g1, g0, blank, lsha = from_ldp(ldp, sc, end)
                m['ldp'] = cycles_summary(g1); m['ldp_alt_c0_9'] = cycles_summary(g0)
                m['ldp_eq_readback_cycles'] = int(sum(1 for a, b in zip(g1, g_rb) if a == b)); m['ldp_blank_s'] = blank; m['ldp_sha256'] = lsha
            for k in ('readback', 'ldp', 'ldp_alt_c0_9'):
                if k in m:
                    m[k].pop('g', None) if k != 'readback' else None
            R['meters'][c] = m
        out['runs'][tag] = R
    for tag, (pat, end) in LDP_ONLY.items():
        R = {'meters': {}}
        for c, sc in zip(FWE_CONN, ('9105', '9106', '9107', '9108')):
            g1, g0, blank, lsha = from_ldp(pat, sc, end)
            s = cycles_summary(g1); s.pop('g')
            R['meters'][c] = {'ldp': s, 'ldp_blank_s': blank, 'ldp_sha256': lsha, 'sc_assumed': sc}
        out['runs'][tag] = R
    json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
    print('DONE', list(out['runs']))


if __name__ == '__main__':
    main()
