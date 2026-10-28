# -*- coding: utf-8 -*-
"""VSL-only (v3c3, DSD 63-66 -> 91 at 900 s) minus NC3 comparison tables. 2026-10-27 KST, vsl_v3c3 PRE_VSL.md section 6-7.

Usage:
  python -B vsl_metrics.py run        -> VS/out/vsl_metrics.json, VS/out/vsl_tables.md   (after the three runs and scans)
  python -B vsl_metrics.py selftest   -> VS/selftest/...  (before data: VSL slot := B runs for the Omega/vhr part and
                                         := NC3 for the FW_E physics/cell part; asserts the reproduction)
Reads only scan outputs, run receipts and membership files. Same-seed pairs VSL - NC3 for v3c3-s31, s41, s43; no
averaging over seeds; no verdict words. Formulas for the Omega part are those of vhr_v3c3_all_b.py (d91ded54...),
checked by the V6 reproduction of SP/codex_handoff/work/vhr_b/v3c3_all.json (f982fbff...) cells 'j1-nc3'.
"""
import csv, hashlib, importlib.util, json, math, os, sys

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
VS = SP + '/vsl_v3c3'
CW = SP + '/codex_handoff/work'
RR = 'D:/VISSIM_runs/20261027_vsl_v3c3'
OUTV = VS + '/out'          # VSL scans (vhr, phys, cell, firstdiff) and the run-mode tables
if os.environ.get('VSL_METRICS_TEST_ROOT'):   # run-mode plumbing test only: fake run tree + standin scans
    RR = os.environ['VSL_METRICS_TEST_ROOT'] + '/runs'
    OUTV = os.environ['VSL_METRICS_TEST_ROOT'] + '/out'
V3 = 'D:/VISSIM_runs/20261001_v3c3'
SEEDS = (31, 41, 43)
PINS = {
    CW + '/vhr_b/scan_out/nc3_s31.json': 'f3fe787cda213504c203bfe66bca2289436e6067e046c59d5095a656905db62d',
    CW + '/vhr_b/scan_out/nc3_s41.json': '1ae351a866612dac5bb4b7b6d1c60ed13bd88b7a27760ba4017805952fe52a47',
    CW + '/vhr_b/scan_out/nc3_s43.json': 'fb90d49b5b95349c25bd1feddf65fbbd71bfcb28861467339284935ae795a793',
    CW + '/vhr_b/scan_out/first_nc3_s31.json': 'e1da8eb8573cb5ad71115207f603e8dc17b8fc53533fe7fe8f5fd857cd56435d',
    CW + '/vhr_b/scan_out/first_nc3_s41.json': '976312123967429592aba33c2430fdd2387e9b92da5815b109544bbc8f30a521',
    CW + '/vhr_b/scan_out/first_nc3_s43.json': 'ebcf0b5b2aeff843c3911744c9d29b9311970e16f9f475074c4c52e86fbc8369',
    CW + '/vhr_b/scan_out/j1_s31.json': '4d5e94b0037f60d257a20d181c7a1c156bbf2bebf49b284fa81f99bcdad87838',
    CW + '/vhr_b/scan_out/j1_s41.json': '9a4d7cd3cb9e14db8868dac86acfc3fb9b0129052b0d78e9815843fdc3ff5baf',
    CW + '/vhr_b/scan_out/j1_s43.json': '93253733953a033f2c7c84bfcda051b93d7e1c1e0a3ac974e4134d33f9771b15',
    CW + '/vhr_b/scan_out/first_j1_s31.json': '52a9164dba2ebaaa6a4deeaffcfed2c9144bae8a73f9f3c9d0bebc2f3a8b4960',
    CW + '/vhr_b/scan_out/first_j1_s41.json': '298979aa7ded01195f3d2c99029292f889e9b48b801167dd1a172efd33631517',
    CW + '/vhr_b/scan_out/first_j1_s43.json': 'cc16b867943a35cfda8af7d30185145bb9e9eada651bfa3b4cf1d4c41f846cca',
    CW + '/vhr_b/v3c3_all.json': 'f982fbff497645c7155d53e9c272388e5136641f5bb9580bc8f3a8c606ba251a',
    SP + '/rmcause/phys/scan/nc_s31.json': '352bddd3a28671575b7671ef1f013c816aa1c163ebd77bd320f452306abe00db',
    SP + '/rmcause/phys/scan/nc_s41.json': '65051df07d65bbde5a287dc959481b2043a3e70f93104aad5b862dd32d811cd4',
    SP + '/rmcause/phys/scan/nc_s43.json': '7afd43e8ed482fa60ae5cf5736f4b6e38b07f9844fc3737ec22f372441b2a843',
    SP + '/rmcause/o1o4/work/tails.py': 'cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569',
    'D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json': 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473',
    'D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json': '4863f5ee5bae6dd47bd00d2adf4a437b9c5eed94f17d3af72fb647fdb31ade9d',
}
PINS.update({   # NC3 cell scans made before any VSL data (jobs_predata.json, 2026-10-27 10:34-10:36 KST)
    VS + '/out/cell/nc3_s31.json': '6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53',
    VS + '/out/cell/nc3_s41.json': '70ef1f26ab17b413b497281e6f051aaf23d88d2c828e198a5b093db10623038e',
    VS + '/out/cell/nc3_s43.json': 'a67a8751bcfa841c2d69e823523ea19bff39179ae384de8ae60fed3cb0e83abd'})
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
LOCAL19 = FWE7 | {'10484', '10490', '10639', '10681', '10481', '10483', '10643', '10682', '129', '31', '68', '70'}
FORMS = (('ours_9000', 9000), ('codex_8100', 8100))
ROWS = [('O635', 'Ω635'), ('O701', 'Ω701'), ('O701mO635', 'Ω701 − Ω635 (66링크)'), ('A4a', '④a 전체 링크'),
        ('U', '④b 미삽입 (첫 관측 차분)'), ('A4', '④ = ④a + ④b'), ('outa701', 'Ω 밖 (a) ④ − Ω701'), ('outb701', 'Ω 밖 (b) ④a − Ω701'),
        ('outa635', 'Ω 밖 (a) ④ − Ω635'), ('outb635', 'Ω 밖 (b) ④a − Ω635'), ('FWE7', '① FW_E 본선 7링크'), ('LOCAL19', '② 동측 국소 19링크'),
        ('u1098', '④b 중 입력 1098 (첫 링크 74)'), ('u1099', '④b 중 입력 1099 (첫 링크 26)'), ('ucity', '④b 중 도시 입력 (그 밖)')]
ZONES = [('U', 0, 4200), ('B1', 4200, 5300), ('M1', 5300, 6300), ('Mu', 6300, 6700), ('VS0', 6700, 6800), ('B2', 6800, 8100), ('D', 8100, 10800)]
WINDOWS = [(0, 900), (900, 1350), (1350, 1800), (1800, 2250), (2250, 2700), (2700, 3600), (3600, 4500), (4500, 6300),
           (6300, 8100), (8100, 9000), (900, 4500), (4500, 9000), (900, 9000)]
LINES = ['4200', '5300', '6300', '6800', '7300', '7700', '8500']
RAMPS = ['10639', '10681', '10490', '10484']
CELL_SETS = list(range(8, 15)) + list(range(16, 26))
CELL_B_M = [0.0, 526.2879, 1052.5758, 1578.8638, 2105.1517, 2631.4396, 3157.7275, 3684.0155, 4210.3034, 4286.333,
            4542.5389, 4736.5913, 4894.3955, 5078.6373, 5262.8792, 5789.1672, 6315.4551, 6490.8844, 6666.3137, 6841.743,
            7041.7112, 7241.6793, 7334.5286, 7498.7905, 7663.0524, 7827.3143, 8320.0999, 8812.8855, 9305.6711, 9798.4567,
            10291.2424, 10784.028]   # = vsl_cell_scan.py CELL_B
CELL_WINDOWS = [(900, 1350), (1350, 1800), (1800, 2250), (2250, 2700), (2700, 3600), (3600, 4500), (4500, 6300), (6300, 9000), (900, 9000)]


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def jload(p, pin=True):
    if pin and p in PINS and sha(p) != PINS[p]:
        raise SystemExit('pinned input changed: %s' % p)
    return json.load(open(p, encoding='utf-8-sig'))


def tails_mod():
    p = SP + '/rmcause/o1o4/work/tails.py'
    if sha(p) != PINS[p]:
        raise SystemExit('tails.py changed')
    spec = importlib.util.spec_from_file_location('tails', p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# ---------------- Omega / ④ (formulas of vhr_v3c3_all_b.py) ----------------
O701 = O635 = None


def members():
    global O701, O635
    if O701 is None:
        O701 = set(map(str, jload('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json')['inside_links']))
        O635 = set(map(str, jload('D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json')['inside_links']))


def link_sums(scan, form):
    members()
    I = scan['integrals'][form]
    return dict(O701=sum(v for l, v in I.items() if l in O701), O635=sum(v for l, v in I.items() if l in O635),
                FWE7=sum(v for l, v in I.items() if l in FWE7), LOCAL19=sum(v for l, v in I.items() if l in LOCAL19), A4a=sum(I.values()))


def Sint(first, W, cats=None):
    tot = 0.0; n = 0
    for c, dd in first['by_cat'].items():
        if cats and c not in cats:
            continue
        for tt, k in dd.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t); n += k
    return tot / 3600, n


def omega_pair(sa, fa, sb, fb):
    """a - b for one seed; sa/fa = scan and first-seen of the arm a, sb/fb of the reference b."""
    out = {}
    for form, W in FORMS:
        x, y = link_sums(sa, form), link_sums(sb, form)
        d = {k: x[k] - y[k] for k in x}
        d['O701mO635'] = d['O701'] - d['O635']
        d['U'] = Sint(fb, W)[0] - Sint(fa, W)[0]
        d['A4'] = d['A4a'] + d['U']
        d['outa701'] = d['A4'] - d['O701']; d['outb701'] = d['A4a'] - d['O701']
        d['outa635'] = d['A4'] - d['O635']; d['outb635'] = d['A4a'] - d['O635']
        d['u1098'] = Sint(fb, W, {'74'})[0] - Sint(fa, W, {'74'})[0]
        d['u1099'] = Sint(fb, W, {'26'})[0] - Sint(fa, W, {'26'})[0]
        d['ucity'] = Sint(fb, W, {'other'})[0] - Sint(fa, W, {'other'})[0]
        out[form] = {'diff': d, 'level_a': x, 'level_b': y,
                     'U_level_a': Sint(fa, W)[0], 'U_level_b': Sint(fb, W)[0]}
    out['arrivals_9000'] = {'a': Sint(fa, 9000)[1], 'b': Sint(fb, 9000)[1],
                            'a_by_cat': {c: Sint(fa, 9000, {c})[1] for c in ('74', '26', 'other')},
                            'b_by_cat': {c: Sint(fb, 9000, {c})[1] for c in ('74', '26', 'other')}}
    out['prefix_lf_sha_le_895_1_equal'] = (sa['lf_sha_le_895_1'] == sb['lf_sha_le_895_1'] and sa['rows_le_895_1'] == sb['rows_le_895_1'])
    return out


# ---------------- FW_E physics (fwe_scan + tails) ----------------
def wins(t0, t1):
    return [w for w in range(151) if t0 <= w * 60 < t1]


def zone_stats(d, ws, a, e):
    bs = [b for b in range(d['nb']) if a <= (b + 0.5) * 100 < e]
    n = sum(d['gN'][w][b] for w in ws for b in bs)
    v = sum(d['gV'][w][b] for w in ws for b in bs)
    return (v / n if n else None), n * 5.0 / 3600.0


def phys(d, T, t0, t1):
    ws = wins(t0, t1)
    hrs = (t1 - t0) / 3600.0
    out = {'zones': {}}
    for z, a, e in ZONES:
        s, vh = zone_stats(d, ws, a, e)
        out['zones'][z] = {'speed_kmh': s, 'veh_h': vh}
    out['flow_vph'] = {x: sum(d['cross'][x][w] for w in ws) / hrs for x in LINES}
    out['merge_vph'] = {r: sum(d['merge'][r][w] for w in ws) / hrs for r in RAMPS}
    out['ramp_queued_veh_h'] = {r: (sum(d['conn_q'][r][w] for w in ws) + sum(d['from_q'][r][w] for w in ws)) * 5.0 / 3600.0 for r in RAMPS}
    out['ins_74_vph'] = sum(d['ins'][w] for w in ws) / hrs
    lane = {}
    for g in range(4):
        n = v = 0.0
        for w in ws:
            for lb in range(len(d['lN'][0])):
                x = 3800 + (lb + 0.5) * 100
                if 6700 <= x < 8000:
                    n += d['lN'][w][lb][g]; v += d['lV'][w][lb][g]
        lane[str(g + 1)] = v / n if n else None
    out['lane_speed_6700_8000'] = lane
    b1 = [T['b1_tail_m'][w] for w in ws if T['b1_tail_m'][w] is not None]
    b2 = [T['b2_tail_m'][w] for w in ws if T['b2_tail_m'][w] is not None]
    out['b1_spill_min'] = sum(1 for x in b1 if x < 4500)
    out['m_spill_min'] = sum(1 for x in b2 if x < 6800)
    out['b1_tail_min_m'] = min(b1) if b1 else None
    out['b2_tail_min_m'] = min(b2) if b2 else None
    return out


def diff(a, b):
    if isinstance(a, dict):
        return {k: diff(a[k], b.get(k) if isinstance(b, dict) else None) for k in a}
    if a is None or b is None:
        return None
    return a - b


# ---------------- cells / VSL zone (vsl_cell_scan) ----------------
def cell_tab(c, t0, t1):
    bounds = c['cell_bounds_m']
    ws = [w for w in range(c['nw']) if t0 <= w * 60 < t1]
    T = (t1 - t0)
    out = {}
    for k in CELL_SETS:
        L = (bounds[k + 1] - bounds[k]) / 1000.0
        N = sum(c['cells'][w][k][g][0] for w in ws for g in range(4))
        SV = sum(c['cells'][w][k][g][1] for w in ws for g in range(4))
        NC = sum(c['cells'][w][k][g][3] for w in ws for g in range(4))
        lanes = 4 if k < 19 else 3
        out[str(k)] = {'speed_kmh': SV / N if N else None, 'flow_vph': SV * 5.0 / (L * T),
                       'density_veh_km_lane': N * 5.0 / (L * T) / lanes, 'share_des_89_93': NC / N if N else None,
                       'from_m': bounds[k], 'to_m': bounds[k + 1]}
    return out


def zone_tab(c, t0, t1):
    zw = [i for i in range(len(c['zone_sums'])) if t0 <= i * c['zone_win_s'] < t1]
    Nc = sum(c['zone_sums'][i][0] for i in zw); SVc = sum(c['zone_sums'][i][1] for i in zw)
    No = sum(c['zone_sums'][i][2] for i in zw); SVo = sum(c['zone_sums'][i][3] for i in zw)
    vt = sum(c['zone_vehicles_first_frame'][i][0] for i in zw); vc = sum(c['zone_vehicles_first_frame'][i][1] for i in zw)
    hist = {}
    for name in c['zone_speed_hist_cmd'][0]:
        hist[name] = sum(c['zone_speed_hist_cmd'][i][name] for i in zw)
    tot = sum(hist.values())
    return {'frames_des_89_93_share': Nc / (Nc + No) if (Nc + No) else None,
            'vehicles_first_zone_frame': vt, 'vehicles_des_89_93_share': vc / vt if vt else None,
            'speed_kmh_all': (SVc + SVo) / (Nc + No) if (Nc + No) else None,
            'speed_kmh_des_89_93': SVc / Nc if Nc else None, 'speed_kmh_other': SVo / No if No else None,
            'cmd_speed_hist_share': {k: (v / tot if tot else None) for k, v in hist.items()}, 'veh_h_zone': (Nc + No) * 5.0 / 3600.0}


# ---------------- run receipts ----------------
def pick_run(s):
    e2 = RR + '/_launcher/end_s%d_run2.json' % s
    if os.path.exists(e2) and json.load(open(e2, encoding='utf-8-sig')).get('status') == 'done':
        return RR + '/s%d/run_retry1' % s, 2
    return RR + '/s%d/run' % s, 1


def receipts(s, res):
    r = {'res': res}
    rj = json.load(open(res + '/run.json', encoding='utf-8-sig')) if os.path.exists(res + '/run.json') else None
    r['run_json'] = None if rj is None else {k: rj.get(k) for k in ('completed', 'exit_code', 'error', 'fixed_profile_validation_exit_code', 'started', 'finished', 'runner_sha256', 'prepared_sha256')}
    fv = json.load(open(res + '/fixed_validation.json', encoding='utf-8')) if os.path.exists(res + '/fixed_validation.json') else None
    r['fixed_validation'] = None if fv is None else {k: fv.get(k) for k in ('passed', 'event_readbacks', 'snapshot_addresses', 'error')}
    out = open(res + '/stdout.txt', encoding='utf-8', errors='replace').read() if os.path.exists(res + '/stdout.txt') else ''
    r['stdout_sim_done'] = 'STAGE=SIM_DONE' in out and 'SIM_SEC=9000' in out
    r['stdout_fixed_event_rows'] = [l for l in out.splitlines() if l.startswith('FIXED_EVENT_ROWS=')]
    writes, final = [], {}
    if os.path.exists(res + '/fixed_readback.csv'):
        for row in csv.DictReader(open(res + '/fixed_readback.csv', encoding='utf-8-sig', newline='')):
            if row['phase'] == 'write':
                writes.append(row)
            elif row['phase'] == 'final' and row['kind'] == 'vsl' and int(row['no']) in (63, 64, 65, 66):
                final[row['no'] + ':' + row['veh_class']] = row['actual']
    r['writes'] = len(writes)
    r['writes_exact'] = (sorted((w['time_s'], w['kind'], w['no'], w['veh_class'], w['expected'], w['actual'], w['ok']) for w in writes)
                         == sorted(('900', 'vsl', str(n), str(c), '91', '91', '1') for n in (63, 64, 65, 66) for c in (10, 20, 30, 70)))
    r['meter_writes'] = sum(1 for w in writes if w['kind'] == 'meter')
    r['final_dsd_63_66'] = sorted(set(final.values()))
    r['ok'] = bool(r['run_json'] and r['run_json']['completed'] is True and r['run_json']['exit_code'] == 0 and fv and fv.get('passed') is True
                   and r['stdout_sim_done'] and r['writes'] == 16 and r['writes_exact'] and r['meter_writes'] == 0 and r['final_dsd_63_66'] == ['91'])
    return r


# ---------------- V6: reproduce B cells with the same formulas ----------------
def v6_reproduce_b():
    ref = jload(CW + '/vhr_b/v3c3_all.json')
    mx = 0.0; n = 0; bad = []
    keymap = {'O701': 'O701', 'O635': 'O635', 'FWE7': 'FWE7', 'A4a': 'A4a', 'U': 'U', 'A4': 'A4', 'outa701': 'outa701',
              'outb701': 'outb701', 'outa635': 'outa635', 'u1098': 'u1098', 'u1099': 'u1099', 'ucity': 'ucity'}
    for s in SEEDS:
        P = omega_pair(jload(CW + '/vhr_b/scan_out/j1_s%d.json' % s), jload(CW + '/vhr_b/scan_out/first_j1_s%d.json' % s),
                       jload(CW + '/vhr_b/scan_out/nc3_s%d.json' % s), jload(CW + '/vhr_b/scan_out/first_nc3_s%d.json' % s))
        for c in ref['cells']:
            if c['pair'] != 'j1-nc3' or c['seed'] != s or c['form'] not in ('ours_9000', 'codex_8100') or c['metric'] not in keymap:
                continue
            mine = P[c['form']]['diff'][keymap[c['metric']]]
            dd = abs(round(mine, 3) - c['mine'])
            n += 1; mx = max(mx, dd)
            if dd > 1e-9:
                bad.append([c['form'], s, c['metric'], round(mine, 3), c['mine']])
    return {'cells_compared': n, 'max_abs_diff_after_round3': mx, 'mismatches': bad, 'ok': n == 72 and not bad}


# ---------------- formatting ----------------
def f1(x, sign=True):
    if x is None:
        return '없음'
    s = ('%+.1f' if sign else '%.1f') % x
    return s.replace('-', '−')


def f0(x, sign=True):
    if x is None:
        return '없음'
    s = ('%+.0f' if sign else '%.0f') % x
    return s.replace('-', '−')


def build(mode):
    tm = tails_mod()
    res = {'mode': mode, 'seeds': {}, 'pins_checked': True}
    if mode == 'run':
        outdir = OUTV
    else:
        outdir = VS + '/selftest'
    os.makedirs(outdir, exist_ok=True)
    res['V6_reproduce_B'] = v6_reproduce_b()
    if not res['V6_reproduce_B']['ok']:
        json.dump(res, open(outdir + '/vsl_metrics.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        raise SystemExit('STOP: V6 reproduction failed')
    for s in SEEDS:
        R = {}
        if mode == 'run':
            res_dir, attempt = pick_run(s)
            R['attempt'] = attempt
            R['receipts'] = receipts(s, res_dir)
            need = [OUTV + '/vhr/vsl_s%d.json' % s, OUTV + '/vhr/first_vsl_s%d.json' % s, OUTV + '/phys/vsl_s%d.json' % s,
                    OUTV + '/cell/vsl_s%d.json' % s, OUTV + '/firstdiff/firstdiff_s%d.json' % s]
            if not R['receipts']['ok'] or not all(os.path.exists(p) for p in need):
                R['unusable'] = ('run not usable (V1/V2 receipts)' if not R['receipts']['ok'] else
                                 'scan missing: ' + ','.join(os.path.basename(p) for p in need if not os.path.exists(p)))
                res['seeds'][str(s)] = R
                continue
            sa = jload(need[0], pin=False); fa = jload(need[1], pin=False)
            pa = jload(need[2], pin=False); ca = jload(need[3], pin=False)
            fd = jload(need[4], pin=False)
            R['V3_prefix'] = {'firstdiff_prefix_equal': fd['prefix_le_895_1']['equal'], 'first_diff': fd['first_diff'],
                              'frames_equal_before_s': fd['frames_equal_before_s']}
            for k, p in (('vhr', sa), ('phys', pa), ('cell', ca)):
                R.setdefault('fzp_sha256', {})[k] = p.get('file_sha256') or p.get('fzp_sha256')
        else:   # selftest standins
            sa = jload(CW + '/vhr_b/scan_out/j1_s%d.json' % s); fa = jload(CW + '/vhr_b/scan_out/first_j1_s%d.json' % s)
            pa = jload(SP + '/rmcause/phys/scan/nc_s%d.json' % s)
            ca = jload(VS + '/out/cell/nc3_s%d.json' % s)
            R['standin'] = 'Omega part: VSL slot = B run (j1) scans; physics/cell part: VSL slot = NC3 scans (all differences 0)'
        sb = jload(CW + '/vhr_b/scan_out/nc3_s%d.json' % s); fb = jload(CW + '/vhr_b/scan_out/first_nc3_s%d.json' % s)
        pb = jload(SP + '/rmcause/phys/scan/nc_s%d.json' % s)
        cb = jload(VS + '/out/cell/nc3_s%d.json' % s)
        R['omega'] = omega_pair(sa, fa, sb, fb)
        Ta, Tb = tm.tails(pa), tm.tails(pb)
        R['phys'] = {}
        for t0, t1 in WINDOWS:
            a, b = phys(pa, Ta, t0, t1), phys(pb, Tb, t0, t1)
            R['phys']['%d_%d' % (t0, t1)] = {'vsl': a, 'nc3': b, 'diff': diff(a, b)}
        R['cells'] = {}
        R['zone'] = {}
        for t0, t1 in CELL_WINDOWS:
            a, b = cell_tab(ca, t0, t1), cell_tab(cb, t0, t1)
            R['cells']['%d_%d' % (t0, t1)] = {'vsl': a, 'nc3': b, 'diff': diff(a, b)}
            za, zb = zone_tab(ca, t0, t1), zone_tab(cb, t0, t1)
            R['zone']['%d_%d' % (t0, t1)] = {'vsl': za, 'nc3': zb}
        res['seeds'][str(s)] = R
    if mode == 'selftest':
        chk = {}
        for s in SEEDS:
            R = res['seeds'][str(s)]
            z = all(abs(v) < 1e-9 for w in R['phys'].values() for v in flat(w['diff']) if v is not None)
            zc = all(abs(v) < 1e-9 for w in R['cells'].values() for v in flat(w['diff']) if v is not None)
            chk[str(s)] = {'phys_diff_all_zero': z, 'cell_diff_all_zero': zc}
        res['selftest_checks'] = chk
        res['selftest_ok'] = res['V6_reproduce_B']['ok'] and all(v['phys_diff_all_zero'] and v['cell_diff_all_zero'] for v in chk.values())
    json.dump(res, open(outdir + '/vsl_metrics.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(outdir + '/vsl_tables.md', 'w', encoding='utf-8').write(tables(res))
    print('written', outdir, 'V6', res['V6_reproduce_B']['ok'], res.get('selftest_ok'))
    return res


def flat(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from flat(v)
    else:
        yield x


def usable(res):
    return [s for s in SEEDS if 'unusable' not in res['seeds'][str(s)]]


def cellv(res, s, getter):
    if 'unusable' in res['seeds'][str(s)]:
        return '못 냄(' + res['seeds'][str(s)]['unusable'] + ')'
    return getter(res['seeds'][str(s)])


def tables(res):
    L = ['# vsl_v3c3 표 (도구 vsl_metrics.py, 모드 %s)' % res['mode'], '',
         '- 짝: VSL 단독 − NC3, 같은 시드. 시드 3: v3c3-s31·s41·s43. 시드끼리 평균 내지 않음. veh·h.',
         '- V6 B 칸 재현: %s (비교 %d칸, 최대 차 %.4f)' % (res['V6_reproduce_B']['ok'], res['V6_reproduce_B']['cells_compared'], res['V6_reproduce_B']['max_abs_diff_after_round3']), '']
    if res['mode'] == 'selftest':
        L.append('- **자체 시험 표: VSL 칸 = B 런(Ω 부분) / NC3(물리·셀 부분). 실제 VSL 숫자가 아님.**')
        L.append('')
    if res['mode'] == 'run':
        L += ['## V 유효성', '', '| 시드 | 시도 | run 완료 | 검증 통과 | VSL 쓰기 16·정확 | 미터 쓰기 | 끝 DSD 63–66 | 접두 ≤895.1 s 같음 | 첫 다른 행 (s) |', '|---|---:|---|---|---|---:|---|---|---|']
        for s in SEEDS:
            R = res['seeds'][str(s)]; rc = R['receipts']
            if 'unusable' in R:
                L.append('| v3c3-s%d | %d | %s | %s | %s·%s | %d | %s | 못 냄 | 못 냄 (%s) |' % (s, R['attempt'], rc['run_json'] and rc['run_json']['completed'],
                         rc['fixed_validation'] and rc['fixed_validation']['passed'], rc['writes'], rc['writes_exact'], rc['meter_writes'],
                         ','.join(rc['final_dsd_63_66']), R['unusable']))
                continue
            fdt = R['V3_prefix']['first_diff']
            L.append('| v3c3-s%d | %d | %s | %s | %s·%s | %d | %s | %s | %s |' % (s, R['attempt'], rc['run_json'] and rc['run_json']['completed'],
                     rc['fixed_validation'] and rc['fixed_validation']['passed'], rc['writes'], rc['writes_exact'], rc['meter_writes'],
                     ','.join(rc['final_dsd_63_66']), R['V3_prefix']['firstdiff_prefix_equal'], None if not fdt else fdt['time_a_s']))
        L.append('')
    for form, W in FORMS:
        L += ['## T1 Ω·④·Ω 밖 (꼴 %s, 첫 관측 ④b W = %d s)' % (form, W), '', '| 줄 | v3c3-s31 | v3c3-s41 | v3c3-s43 |', '|---|---:|---:|---:|']
        for key, name in ROWS:
            L.append('| %s | %s |' % (name, ' | '.join(cellv(res, s, lambda R: f1(R['omega'][form]['diff'][key])) for s in SEEDS)))
        L.append('')
    L += ['## T1b 도착 수 점검 (첫 관측 총수, 9,000 s)', '', '| 시드 | VSL | NC3 | VSL 74/26/그 밖 | NC3 74/26/그 밖 | 접두 lf_sha ≤895.1 같음 |', '|---|---:|---:|---|---|---|']
    for s in usable(res):
        a = res['seeds'][str(s)]['omega']['arrivals_9000']
        L.append('| v3c3-s%d | %d | %d | %s | %s | %s |' % (s, a['a'], a['b'], '/'.join(str(a['a_by_cat'][c]) for c in ('74', '26', 'other')),
                 '/'.join(str(a['b_by_cat'][c]) for c in ('74', '26', 'other')), res['seeds'][str(s)]['omega']['prefix_lf_sha_le_895_1_equal']))
    L.append('')
    L += ['## T2 FW_E 구역 Δ속도 km/h (VSL − NC3) · 번짐 분 Δ', '']
    for s in usable(res):
        L += ['### v3c3-s%d' % s, '', '| 창 s | ' + ' | '.join(z for z, _, _ in ZONES) + ' | q6800 | q7700 | B1 번짐 Δ분 | M 번짐 Δ분 | 삽입74 Δveh/h |',
              '|---|' + '---:|' * (len(ZONES) + 5)]
        for t0, t1 in WINDOWS:
            d = res['seeds'][str(s)]['phys']['%d_%d' % (t0, t1)]['diff']
            L.append('| %d–%d | %s | %s | %s | %s | %s | %s |' % (t0, t1, ' | '.join(f1(d['zones'][z]['speed_kmh']) for z, _, _ in ZONES),
                     f0(d['flow_vph']['6800']), f0(d['flow_vph']['7700']), f0(d['b1_spill_min']), f0(d['m_spill_min']), f0(d['ins_74_vph'])))
        L.append('')
    L += ['## T3 셀 속도 km/h (VSL / NC3 / Δ), 900–9,000 s', '', '| 셀 | 범위 m | ' + ' | '.join('s%d' % s for s in SEEDS) + ' |', '|---|---|' + '---|' * len(SEEDS)]
    for k in CELL_SETS:
        row = []
        for s in SEEDS:
            if 'unusable' in res['seeds'][str(s)]:
                row.append('못 냄'); continue
            c = res['seeds'][str(s)]['cells']['900_9000']
            row.append('%s / %s / %s' % (f1(c['vsl'][str(k)]['speed_kmh'], False), f1(c['nc3'][str(k)]['speed_kmh'], False), f1(c['diff'][str(k)]['speed_kmh'])))
        L.append('| %d | %.0f–%.0f | %s |' % (k, CELL_B_M[k], CELL_B_M[k + 1], ' | '.join(row)))
    L.append('')
    L += ['## T4 VSL 구역(6,733.2–8,090.8 m) 준수', '', '| 시드 | 창 s | 희망 89–93 프레임 몫 VSL / NC3 | 차량 몫 VSL | 실현 속도 희망 89–93 / 그 밖 / NC3 전체 | 희망 89–93 차 실현 >100 몫 |', '|---|---|---|---|---|---|']
    for s in usable(res):
        for t0, t1 in CELL_WINDOWS:
            z = res['seeds'][str(s)]['zone']['%d_%d' % (t0, t1)]
            a, b = z['vsl'], z['nc3']
            pct = lambda x: '없음' if x is None else '%.3f' % x
            L.append('| v3c3-s%d | %d–%d | %s / %s | %s | %s / %s / %s | %s |' % (s, t0, t1, pct(a['frames_des_89_93_share']), pct(b['frames_des_89_93_share']),
                     pct(a['vehicles_des_89_93_share']), f1(a['speed_kmh_des_89_93'], False), f1(a['speed_kmh_other'], False), f1(b['speed_kmh_all'], False),
                     pct(a['cmd_speed_hist_share'].get('ge100'))))
    L.append('')
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'run')
