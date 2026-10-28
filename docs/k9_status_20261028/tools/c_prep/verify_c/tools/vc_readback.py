# vc_readback.py -- independent recount (verify_c V1, V2). Read-only. No reuse of rb_*/w1099_* tools.
# V1: meter readback vs command per 10 s cycle, from write events (immediate rows) held until next write.
# V2: SC1001 SG2/SG5 green (and amber) seconds per window, B/V-A from readback immediate rows, NC3 from .sig program.
import csv, json, sys, os, re, collections, xml.etree.ElementTree as ET

OUT = sys.argv[1]
B = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s{s}/sdmpc'
VA = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{s}'
NC = 'D:/VISSIM_runs/20261001_v3c3/s{s}_v3c3nc/prepared/network/\uac1c\ud3ec\ub3d9 test-bed1001_n4dr150.sig'
METERS = [9101, 9102, 9103, 9104, 9105, 9106, 9107, 9108]
CTRL0, CTRL1 = 900, 9000

def paths(arm, s):
    if arm == 'B':
        root = B.format(s=s)
        return (f'{root}/decisions_sdmpc31_sdmpc9000_s{s}/signal_readback.csv',
                f'{root}/action_sdmpc31_sdmpc9000_s{s}.csv', f'{root}/decisions_sdmpc31_sdmpc9000_s{s}')
    root = VA.format(s=s)
    return (f'{root}/decisions_sdmpc31_v3c3_k92va_s{s}/signal_readback.csv',
            f'{root}/action_sdmpc31_v3c3_k92va_s{s}.csv', f'{root}/decisions_sdmpc31_v3c3_k92va_s{s}')

def read_rows(p):
    with open(p, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def held_series(events, t0, t1):
    """events: sorted list of (sec, state). state at integer second s = last event with sec <= s."""
    out = {}
    k = -1
    cur = None
    for s in range(t0, t1):
        while k + 1 < len(events) and events[k + 1][0] <= s:
            k += 1
            cur = events[k][1]
        out[s] = cur
    return out

def meter_check(arm, s):
    rb_p, cmd_p, dec_dir = paths(arm, s)
    rb = read_rows(rb_p)
    cmd = read_rows(cmd_p)
    res = {'readback_file': rb_p, 'command_file': cmd_p}
    mrows = [r for r in rb if r['sc_no'] and int(r['sc_no']) in METERS]
    res['meter_rows'] = len(mrows)
    res['meter_rows_req_eq_read_ok'] = sum(1 for r in mrows if r['requested_state'] == r['readback_state'] and r['ok'] == '1')
    res['meter_rows_stage'] = dict(collections.Counter(r['stage'] for r in mrows))
    # commands
    cm = collections.defaultdict(list)
    for r in cmd:
        if r['kind'] == 'ramp_meter':
            cm[int(r['sc_no'])].append((int(float(r['sim_sec'])), float(r['green_sec']), float(r['rate_vph'])))
    res['command_rows'] = sum(len(v) for v in cm.values())
    res['rate_eq_90g'] = sum(1 for v in cm.values() for (_, g, rt) in v if abs(rt - 90 * g) < 1e-6)
    # command source vs per-decision action_<T>.csv
    src_match = src_total = 0
    for sc, v in cm.items():
        for (t, g, rt) in v:
            p = os.path.join(dec_dir, 'action_%06d.csv' % t)
            if not os.path.isfile(p):
                continue
            for r in read_rows(p):
                if r['kind'] == 'ramp_meter' and r['sc_no'] and int(r['sc_no']) == sc:
                    src_total += 1
                    if abs(float(r['green_sec']) - g) < 1e-9 and abs(float(r['rate_vph']) - rt) < 1e-9:
                        src_match += 1
    res['command_source_match'] = [src_match, src_total]
    per = {}
    tot_cyc = tot_cyc_ok = 0
    tot_sec = tot_sec_ok = 0
    tot_writes = tot_post_ok = tot_post = 0
    for sc in METERS:
        rows = sorted([r for r in mrows if int(r['sc_no']) == sc], key=lambda r: (int(r['sim_sec']), r['stage'] != 'post_step'))
        imm = [(int(r['sim_sec']), r['readback_state']) for r in rows if r['stage'] == 'immediate']
        post = [(int(r['sim_sec']), r['readback_state']) for r in rows if r['stage'] == 'post_step']
        series = held_series(imm, 0, CTRL1)
        cmds = sorted(cm[sc])
        # commanded state per second, own implementation of 10 s cycle: green if (s mod 10) < g
        def g_at(t):
            g = None
            for (tc, gg, _) in cmds:
                if tc <= t: g = gg
                else: break
            return g
        cyc_ok = 0; mism = []
        dist = collections.Counter()
        sec_ok = 0
        for c in range(CTRL0, CTRL1, 10):
            g = g_at(c)
            dist[int(g)] += 1
            obs = sum(1 for s2 in range(c, c + 10) if series[s2] == 'GREEN')
            if obs == int(g): cyc_ok += 1
            else: mism.append((c, g, obs))
            for s2 in range(c, c + 10):
                exp = 'GREEN' if (s2 % 10) < g else 'RED'
                if series[s2] == exp: sec_ok += 1
        # post_step consistency: readback at post_step t equals last write strictly before t
        p_ok = 0
        for (t, st) in post:
            prev = [e for e in imm if e[0] < t]
            if prev and prev[-1][1] == st: p_ok += 1
        writes_ctrl = sum(1 for (t, _) in imm if CTRL0 <= t < CTRL1)
        per[sc] = {'cycles_ok': cyc_ok, 'cycles': len(range(CTRL0, CTRL1, 10)), 'mismatch_first5': mism[:5],
                   'green_dist': dict(sorted(dist.items())), 'seconds_ok': sec_ok, 'writes_ctrl': writes_ctrl,
                   'post_ok': p_ok, 'post_rows': len(post)}
        tot_cyc += len(range(CTRL0, CTRL1, 10)); tot_cyc_ok += cyc_ok
        tot_sec += CTRL1 - CTRL0; tot_sec_ok += sec_ok
        tot_writes += writes_ctrl; tot_post += len(post); tot_post_ok += p_ok
    res['per_meter'] = per
    res['totals'] = {'cycles_ok': tot_cyc_ok, 'cycles': tot_cyc, 'seconds_ok': tot_sec_ok, 'seconds': tot_sec,
                     'writes_ctrl': tot_writes, 'post_ok': tot_post_ok, 'post_rows': tot_post}
    return res

def sc1001_readback(arm, s, windows):
    rb_p, _, _ = paths(arm, s)
    rb = read_rows(rb_p)
    out = {}
    bad = 0
    for sg in (2, 5):
        rows = [r for r in rb if r['sc_no'] == '1001' and r['sg_no'] == str(sg)]
        bad += sum(1 for r in rows if r['requested_state'] != r['readback_state'] or r['ok'] != '1')
        imm = sorted((int(r['sim_sec']), r['readback_state']) for r in rows if r['stage'] == 'immediate')
        series = held_series(imm, 0, 9000)
        for (a, b) in windows:
            c = collections.Counter(series[t] for t in range(a, b))
            out[f'SG{sg}_{a}_{b}'] = {'GREEN': c.get('GREEN', 0), 'AMBER': c.get('AMBER', 0), 'RED': c.get('RED', 0), 'None': c.get(None, 0)}
    out['rows_bad'] = bad
    return out

def sc1001_sig(s, windows):
    p = NC.format(s=s)
    root = ET.parse(p).getroot()
    prog = [pr for pr in root.iter('prog') if pr.get('id') == '1'][0]
    cyc = int(prog.get('cycletime')) / 1000.0; off = int(prog.get('offset')) / 1000.0
    out = {'file': p, 'cycle': cyc, 'offset': off}
    for sg in (2, 5):
        el = [x for x in prog.iter('sg') if x.get('sg_id') == str(sg)][0]
        cmds = sorted((int(c.get('begin')) / 1000.0, c.get('display')) for c in el.iter('cmd'))
        amber = [int(fs.get('duration')) / 1000.0 for fs in el.iter('fixedstate') if fs.get('display') == '4']
        amber = amber[0] if amber else 0.0
        g_on = [b for b, d in cmds if d == '3'][0]; r_on = [b for b, d in cmds if d == '1'][0]
        # VISSIG sequence 7 (red-green-amber): amber occupies [r_on - amber, r_on) at the end of green
        def state(ct):
            gl = (r_on - g_on) % cyc
            x = (ct - g_on) % cyc
            if x < gl - amber: return 'GREEN'
            if x < gl: return 'AMBER'
            return 'RED'
        for (a, b) in windows:
            c = collections.Counter(state((t - off) % cyc) for t in range(a, b))
            out[f'SG{sg}_{a}_{b}'] = {'GREEN': c.get('GREEN', 0), 'AMBER': c.get('AMBER', 0), 'RED': c.get('RED', 0)}
        out[f'SG{sg}_cmds'] = cmds; out[f'SG{sg}_amber'] = amber
    return out

def lsa_warmup_b(s):
    """VISSIM signal-change log of the B run (native fixed time before 900 s): SC1001 SG2/SG5 lines, cycle-time of green/amber/red."""
    p = B.format(s=s) + f'/vissim_eval/sdmpc31_sdmpc9000_s{s}_001.lsa'
    rows = []
    with open(p, encoding='latin-1') as f:
        for line in f:
            parts = [x.strip() for x in line.split(';')]
            if len(parts) >= 5 and parts[2] == '1001' and parts[3] in ('2', '5'):
                try: rows.append((float(parts[0]), float(parts[1]), int(parts[3]), parts[4]))
                except ValueError: pass
    return {'file': p, 'rows_le_300': [r for r in rows if r[0] <= 300], 'last_time': max(r[0] for r in rows) if rows else None}

if __name__ == '__main__':
    res = {'V1': {}, 'V2': {}}
    for s in (43, 31, 41):
        res['V1'][f'B_s{s}'] = meter_check('B', s)
    res['V1']['VA_s43'] = meter_check('VA', 43)
    W = [(900, 2700), (2700, 4500), (900, 9000)]
    for s in (31, 41, 43):
        res['V2'][f'B_s{s}'] = sc1001_readback('B', s, W)
        res['V2'][f'VA_s{s}'] = sc1001_readback('VA', s, W)
        res['V2'][f'NC3_s{s}'] = sc1001_sig(s, W)
    res['V2']['B_s41_lsa_warmup'] = lsa_warmup_b(41)
    json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1, default=str)
    print('done', OUT)
