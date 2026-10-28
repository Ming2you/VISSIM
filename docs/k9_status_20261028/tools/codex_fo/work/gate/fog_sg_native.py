# -*- coding: utf-8 -*-
"""fog_sg_native.py - FO gate G2 and run check V5 (2026-10-27 KST, D-K9-113). Read-only. No VISSIM, no COM.

Question: does the urban SG schedule that the FO controller writes by COM (the baseline plan, rewritten from 900 s every
150 s) give the SAME GREEN seconds as the native fixed-time programs that NC3 runs untouched? GREEN only (amber/red/off are
not compared). If not, FO - NC3 mixes a write effect into the freeway-control share (user rule: STOP and report).

Conventions (all fixed before any FO data):
  * signal_sg command row (action CSV): sc = col 3, sg = col 2, window = col 4, [start, end) = cols 7, 8, offset = col 11,
    cycle = col 13 (VBS SignalSgRowValid). An expected SG with no window row is permanent RED (VBS SignalGroupStateFromPlan).
  * COM clock (VBS SignalClockPosition, OBS150_FRAME_ADVANCE = 1): requested state at clock c is GREEN iff
    (c + offset + 1) mod cycle lies in a window. Observed frame t shows the request of clock t - 1 (codex native LDP check
    'primary_1s_post_step_at_t_uses_command_clock_t_minus_1'). So frame t is GREEN iff (t + offset) mod cycle in a window.
  * Native .lsa: lines 'simtime; cycletime; SC; SG; state; ...'; the state at frame t = the last event with time <= t
    (checked against LDP rows in the 64cf positive control). GREEN iff state word == 'green'.
  * LDP (64cf positive control only): row 't cyc states', SG state chars from column 12, 'I' = GREEN, '/' = amber,
    '.' = red; SG numbers from the vertical digit lines of the header.
  * Written SG set = the (sc, sg) pairs with urban (sc < 9000) rows in the run's signal_readback.csv (what the VBS actually
    wrote in that run); cross-listed with RW_SIGNAL_SG_EXPECTED of the sgplan VBS config. SGs never written stay native and
    are reported, not compared.

Modes:
  selftest64  codex 64cf-s29 freeway_only run (handoff copy): (i) command rule vs LDP for t in [1050, 8099] (validates the
              COM rule), (ii) .lsa vs LDP for t in [2, 899] (validates the .lsa rule), (iii) command rule vs .lsa native over
              [2, 899] (the 64cf analogue of G2). Report only.
  negb        B v3c3 record: B T=900 command (optimized plan) vs B .lsa native over [2, 899] (expected to differ). Report only.
  gate        G2: FO replay action_000900.csv of seed s vs B .lsa of the same seed over frames [2, 899], written set from the
              B readback of the same seed. PASS iff every written SG has 0 differing GREEN frames and every SC cycle in the
              rows equals the native cycle (from the .lsa cycletime wrap). One JSON per call.
  selftest64run  the 'run' rule on the codex 64cf-s29 freeway_only run (its readback vs its own .lsa native, [901, 8100]).
  run         V5 (after FO runs): FO run readback (immediate requested states) -> realized frames t in [901, 9000] vs the
              native program extended periodically from the B .lsa (same seed, frames [2, 899]) of the same network.
              PASS iff 0 differing GREEN frames for every written SG.
usage:
  python -B fog_sg_native.py selftest64 <out.json>
  python -B fog_sg_native.py negb <seed> <out.json>
  python -B fog_sg_native.py gate <seed> <fo_action_000900.csv> <out.json>
  python -B fog_sg_native.py run <seed> <fo_decisions_dir> <out.json>
  python -B fog_sg_native.py selftest64run <out.json>
"""
import csv, hashlib, json, os, re, sys

HO = 'D:/VISSIM_handoff/20261024/raw/freeway_only/sdmpc'
BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc'
SGPLAN_REL = 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/scenario/lane_native_b110_sgplan.vbs'
FRZ_B1 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410'
LSA_RE = re.compile(r'^\s*([0-9.]+);\s*([0-9.]+);\s*(\d+);\s*(\d+);\s*([A-Za-z]+)')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_plan(action_csv):
    """(sc, sg) -> {'windows': [(s, e)], 'offset': o, 'cycle': C}; plus the set of SCs with signal rows."""
    plan, sig = {}, {}
    with open(action_csv, newline='', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if not row or row[0] not in ('signal_sg', 'signal'):
                continue
            if row[0] == 'signal':
                sig[int(row[3])] = {'p': [row[7], row[8], row[9], row[10]], 'offset': float(row[11])}
                continue
            sc, sg, w = int(row[3]), int(row[2]), int(row[4])
            s, e, off, cyc = float(row[7]), float(row[8]), float(row[11]), float(row[13])
            d = plan.setdefault((sc, sg), {'windows': [], 'offset': off, 'cycle': cyc, 'rows': 0})
            if d['offset'] != off or d['cycle'] != cyc:
                raise SystemExit('inconsistent offset/cycle within SC %d SG %d' % (sc, sg))
            d['windows'].append((s, e))
            d['rows'] += 1
    return plan, sig


def com_green(plan_sg, t):
    if plan_sg is None:
        return False
    pos = (t + plan_sg['offset']) % plan_sg['cycle']
    return any(s <= pos < e for s, e in plan_sg['windows'])


def read_lsa(path):
    ev = {}
    cyc = {}
    with open(path, 'r', encoding='latin-1') as f:
        for line in f:
            m = LSA_RE.match(line)
            if not m:
                continue
            t, c, sc, sg, st = float(m.group(1)), float(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5).lower()
            ev.setdefault((sc, sg), []).append((t, st))
            cyc.setdefault(sc, []).append((t, c))
    for k in ev:
        ev[k].sort()
    return ev, cyc


def lsa_green(events, t):
    st = None
    for tt, s in events:
        if tt <= t + 1e-9:
            st = s
        else:
            break
    return st == 'green'


def lsa_green_frames(events, frames):
    out, i, st = set(), 0, None
    for t in frames:
        while i < len(events) and events[i][0] <= t + 1e-9:
            st = events[i][1]
            i += 1
        if st == 'green':
            out.add(t)
    return out


def native_cycle(cyc_events, horizon=899.0):
    """Cycle length and phase of the native program from (simtime, cycletime) pairs: C from the cycletime wrap, delta with
    cycletime = (simtime + delta) mod C. Returns (C, delta, consistent)."""
    pts = sorted((t, c) for t, c in cyc_events if t <= horizon)
    if len(pts) < 2:
        return None, None, False
    wraps = {}
    for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
        if c1 < c0 and t1 > t0:
            w = round((t1 - t0) - (c1 - c0), 6)
            wraps[w] = wraps.get(w, 0) + 1
    if not wraps:
        return None, None, False
    C = max(wraps, key=lambda w: (wraps[w], -w))
    delta = (pts[0][1] - pts[0][0]) % C

    def close(x, c):
        d = abs(x - c) % C
        return min(d, C - d) < 1e-6
    ok = all(close((t + delta) % C, c) for t, c in pts)
    return C, delta, ok


def read_ldp(path):
    lines = open(path, 'r', encoding='latin-1').read().splitlines()
    first = None
    for i, l in enumerate(lines):
        if re.match(r'^\s*\d+\.\d\s*\d+\.\d', l):
            first = i
            break
    hdr = [l for l in lines[:first] if l.strip()]
    digit_lines = []
    for l in reversed(hdr):
        seg = l[12:]
        if seg.strip() and re.fullmatch(r'[0-9 ]*', seg):
            digit_lines.insert(0, seg)
        else:
            break
    width = max(len(s) for s in digit_lines)
    labels = []
    for j in range(width):
        ds = ''.join(s[j] if j < len(s) else ' ' for s in digit_lines).strip()
        if ds:
            labels.append(int(ds))
    rows = {}
    for l in lines[first:]:
        if not re.match(r'^\s*\d+\.\d', l):
            continue
        t = float(l[0:7])
        rows[int(round(t))] = l[12:12 + len(labels)]
    return labels, rows


def written_set(readback_csv):
    ws = set()
    with open(readback_csv, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            sc = int(row['sc_no'])
            if sc < 9000:
                ws.add((sc, int(row['sg_no'])))
    return ws


def expected_groups(sgplan_vbs):
    lines = open(sgplan_vbs, 'r', encoding='latin-1').read().splitlines()
    value, on = '', False
    for l in lines:   # VBS literal continued with '" & _' line by line
        if not on and re.match(r'^\s*RW_SIGNAL_SG_EXPECTED\s*=', l):
            on = True
        if on:
            value += ''.join(re.findall(r'"([^"]*)"', l))
            if not l.rstrip().endswith('_'):
                break
    out = {}
    for tok in value.split(','):
        if tok.strip():
            sc, sg, n = tok.split(':')
            out[(int(sc), int(sg))] = int(n)
    return out


def compare(plan, ev, cyc, written, frames, label):
    """GREEN frames of the COM rule vs the .lsa native, per written SG."""
    per, bad = {}, 0
    scs = sorted({sc for sc, _ in written})
    cyc_rep = {}
    for sc in scs:
        C, delta, ok = native_cycle(cyc.get(sc, []))
        rows_c = sorted({v['cycle'] for (s, _), v in plan.items() if s == sc})
        cyc_rep[str(sc)] = {'native_cycle': C, 'native_delta': delta, 'native_consistent': ok, 'rows_cycle': rows_c,
                            'equal': ok and len(rows_c) <= 1 and (not rows_c or abs(rows_c[0] - C) < 1e-6)}
    for key in sorted(written):
        p = plan.get(key)
        com = {t for t in frames if com_green(p, t)}
        nat = lsa_green_frames(ev.get(key, []), frames)
        only_com, only_nat = sorted(com - nat), sorted(nat - com)
        per['%d:%d' % key] = {'windows': p['windows'] if p else [], 'offset': p['offset'] if p else None,
                              'com_green_frames': len(com), 'native_green_frames': len(nat),
                              'only_com': len(only_com), 'only_native': len(only_nat),
                              'examples_only_com': only_com[:5], 'examples_only_native': only_nat[:5]}
        bad += len(only_com) + len(only_nat)
    n_diff_sg = sum(1 for v in per.values() if v['only_com'] or v['only_native'])
    return {'label': label, 'frames': [frames[0], frames[-1]], 'written_sg': len(written), 'sg_with_difference': n_diff_sg,
            'differing_frames_total': bad, 'cycles': cyc_rep, 'cycles_equal': all(v['equal'] for v in cyc_rep.values()), 'per_sg': per}


def mode_selftest64(out):
    act = HO + '/action_sdmpc31_sdmpc8100_s29.csv'
    lsa = HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_001.lsa'
    rb = HO + '/decisions_sdmpc31_sdmpc8100_s29/signal_readback.csv'
    res = {'mode': 'selftest64', 'inputs': {p: sha(p) for p in (act, lsa, rb)}}
    # the T=900 plan (baseline in codex freeway_only) and the set of distinct plans over the run
    plans = {}
    with open(act, newline='', encoding='utf-8-sig') as f:
        rdr = csv.DictReader(f)
        rows_by_t = {}
        for row in rdr:
            if row['kind'] in ('signal_sg', 'signal'):
                rows_by_t.setdefault(int(float(row['sim_sec'])), []).append(row)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), '_sg64_%d.csv' % os.getpid())
    distinct = set()
    for T, rows in sorted(rows_by_t.items()):
        key = tuple(sorted((r['kind'], r['id'], r['p1_green'], r['p2_green'], r['offset'], r['green_sec']) for r in rows))
        distinct.add(key)
    T0 = min(rows_by_t)
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        for r in rows_by_t[T0]:
            w.writerow([r['kind'], r['id'], r['dsd_no'], r['sc_no'], r['link'], r['lane'], r['speed_kph'], r['p1_green'], r['p2_green'],
                        r['p3_green'], r['p4_green'], r['offset'], r['rate_vph'], r['green_sec'], ''])
    plan, sig = read_plan(tmp)
    os.remove(tmp)
    res['plan_first_T'] = T0
    res['distinct_signal_plans_over_run'] = len(distinct)
    ev, cyc = read_lsa(lsa)
    written = written_set(rb)
    res['written_sg'] = len(written)
    # (iii) G2 analogue on 64cf
    res['g2_analogue_64cf'] = compare(plan, ev, cyc, written, list(range(2, 900)), 'codex 64cf-s29 freeway_only baseline rows vs its .lsa native [2,899]')
    # (i), (ii) against the LDP
    rule_vs_ldp, lsa_vs_ldp = {}, {}
    scs = sorted({sc for sc, _ in written})
    for sc in scs:
        ldp = HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_%d_001.ldp' % sc
        if not os.path.exists(ldp):
            continue
        labels, rows = read_ldp(ldp)
        for j, sg in enumerate(labels):
            key = (sc, sg)
            if key not in written:
                continue
            d1 = [t for t in range(1050, 8100) if t in rows and ((rows[t][j] == 'I') != com_green(plan.get(key), t))]
            d2 = [t for t in range(2, 900) if t in rows and ((rows[t][j] == 'I') != lsa_green(ev.get(key, []), t))]
            rule_vs_ldp['%d:%d' % key] = {'n': len(d1), 'examples': d1[:5]}
            lsa_vs_ldp['%d:%d' % key] = {'n': len(d2), 'examples': d2[:5]}
    res['rule_vs_ldp_1050_8099'] = {'sg_checked': len(rule_vs_ldp), 'sg_with_difference': sum(1 for v in rule_vs_ldp.values() if v['n']),
                                    'differing_frames_total': sum(v['n'] for v in rule_vs_ldp.values()), 'per_sg': rule_vs_ldp}
    res['lsa_vs_ldp_2_899'] = {'sg_checked': len(lsa_vs_ldp), 'sg_with_difference': sum(1 for v in lsa_vs_ldp.values() if v['n']),
                               'differing_frames_total': sum(v['n'] for v in lsa_vs_ldp.values()), 'per_sg': lsa_vs_ldp}
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('SELFTEST64 distinct_plans=%d written=%d rule_vs_ldp diff_sg=%d frames=%d | lsa_vs_ldp diff_sg=%d frames=%d | g2_analogue diff_sg=%d frames=%d cycles_equal=%s' % (
        res['distinct_signal_plans_over_run'], res['written_sg'], res['rule_vs_ldp_1050_8099']['sg_with_difference'],
        res['rule_vs_ldp_1050_8099']['differing_frames_total'], res['lsa_vs_ldp_2_899']['sg_with_difference'],
        res['lsa_vs_ldp_2_899']['differing_frames_total'], res['g2_analogue_64cf']['sg_with_difference'],
        res['g2_analogue_64cf']['differing_frames_total'], res['g2_analogue_64cf']['cycles_equal']))
    return 0


def b_inputs(seed):
    run = BR % seed
    prov = json.load(open(run + '/run_provenance_sdmpc31_sdmpc9000_s%d.json' % seed, encoding='utf-8-sig'))
    if prov.get('seed') != seed:
        raise SystemExit('B provenance seed %s != %s' % (prov.get('seed'), seed))
    lsa = run + '/vissim_eval/sdmpc31_sdmpc9000_s%d_001.lsa' % seed
    rb = run + '/decisions_sdmpc31_sdmpc9000_s%d/signal_readback.csv' % seed
    return run, lsa, rb


def mode_negb(seed, out):
    run, lsa, rb = b_inputs(seed)
    act = run + '/decisions_sdmpc31_sdmpc9000_s%d/action_000900.csv' % seed
    plan, sig = read_plan(act)
    ev, cyc = read_lsa(lsa)
    written = written_set(rb)
    r = compare(plan, ev, cyc, written, list(range(2, 900)), 'B v3c3-s%d T=900 optimized rows vs B .lsa native [2,899] (negative control)' % seed)
    r['inputs'] = {p: sha(p) for p in (act, lsa, rb)}
    json.dump(r, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('NEGB s%d written=%d diff_sg=%d frames=%d cycles_equal=%s' % (seed, r['written_sg'], r['sg_with_difference'], r['differing_frames_total'], r['cycles_equal']))
    return 0


def mode_gate(seed, act, out, frz=None):
    run, lsa, rb = b_inputs(seed)
    plan, sig = read_plan(act)
    ev, cyc = read_lsa(lsa)
    written = written_set(rb)
    exp = expected_groups((frz or FRZ_B1) + '/' + SGPLAN_REL)
    r = compare(plan, ev, cyc, written, list(range(2, 900)), 'FO replay v3c3-s%d T=900 rows vs B .lsa native [2,899] (G2)' % seed)
    r['inputs'] = {p: sha(p) for p in (act, lsa, rb)}
    r['expected_groups'] = len(exp)
    r['expected_with_windows'] = sorted('%d:%d' % k for k, n in exp.items() if n > 0)
    r['written_not_expected'] = sorted('%d:%d' % k for k in written if k not in exp)
    r['expected_zero_window_written'] = sorted('%d:%d' % k for k, n in exp.items() if n == 0 and k in written)
    r['expected_not_written_native'] = sorted('%d:%d' % k for k in exp if k not in written)
    r['plan_sg_not_written'] = sorted('%d:%d' % k for k in plan if k not in written)
    r['pass'] = (r['differing_frames_total'] == 0 and r['cycles_equal'] and not r['written_not_expected'] and not r['plan_sg_not_written'])
    json.dump(r, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('G2 s%d pass=%s written=%d diff_sg=%d frames=%d cycles_equal=%s' % (seed, r['pass'], r['written_sg'], r['sg_with_difference'], r['differing_frames_total'], r['cycles_equal']))
    return 0


def mode_run(seed, dec, out, lsa=None, t_end=9000):
    if lsa is None:
        run, lsa, rb_b = b_inputs(seed)
    ev, cyc = read_lsa(lsa)
    rb = dec + '/signal_readback.csv'
    req = {}
    with open(rb, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            sc = int(row['sc_no'])
            if sc >= 9000 or row['stage'] != 'immediate':
                continue
            req.setdefault((sc, int(row['sg_no'])), []).append((int(float(row['sim_sec'])), row['requested_state'].upper()))
    for k in req:
        req[k].sort()
    frames = list(range(901, t_end + 1))
    per, bad = {}, 0
    nat_cache = {}
    for key in sorted(req):
        sc = key[0]
        if sc not in nat_cache:
            nat_cache[sc] = native_cycle(cyc.get(sc, []))
        C, delta, ok = nat_cache[sc]
        base = lsa_green_frames(ev.get(key, []), list(range(2, 900)))
        prog_green = {(t + delta) % C for t in base if t >= 2 + C} if ok else set()
        evs, i, st, diff = req[key], 0, None, []
        for t in frames:
            while i < len(evs) and evs[i][0] <= t - 1:
                st = evs[i][1]
                i += 1
            g_com = st == 'GREEN'
            g_nat = ((t + delta) % C) in prog_green if ok else None
            if g_com != g_nat:
                diff.append(t)
        per['%d:%d' % key] = {'n': len(diff), 'examples': diff[:5], 'native_cycle': C, 'native_ok': ok}
        bad += len(diff)
    r = {'mode': 'run', 'seed': seed, 'readback': rb, 'readback_sha256': sha(rb), 'lsa': lsa, 'lsa_sha256': sha(lsa),
         'written_sg': len(req), 'sg_with_difference': sum(1 for v in per.values() if v['n']), 'differing_frames_total': bad, 'per_sg': per}
    r['pass'] = bad == 0 and all(v['native_ok'] for v in per.values())
    json.dump(r, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('V5 s%d pass=%s written=%d diff_sg=%d frames=%d' % (seed, r['pass'], r['written_sg'], r['sg_with_difference'], bad))
    return 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'selftest64' and len(a) == 2:
        sys.exit(mode_selftest64(a[1]))
    if a and a[0] == 'negb' and len(a) == 3:
        sys.exit(mode_negb(int(a[1]), a[2]))
    if a and a[0] == 'gate' and len(a) in (4, 5):
        sys.exit(mode_gate(int(a[1]), a[2], a[3], a[4] if len(a) == 5 else None))
    if a and a[0] == 'run' and len(a) == 4:
        sys.exit(mode_run(int(a[1]), a[2], a[3]))
    if a and a[0] == 'selftest64run' and len(a) == 2:
        sys.exit(mode_run(29, HO + '/decisions_sdmpc31_sdmpc8100_s29', a[1], lsa=HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_001.lsa', t_end=8100))
    print(__doc__)
    sys.exit(2)
