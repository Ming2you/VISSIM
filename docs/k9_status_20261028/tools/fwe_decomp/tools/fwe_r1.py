# -*- coding: utf-8 -*-
"""R1 - uncontrolled FW_E congestion regime (PRE_FWE.md section 5.1, r1 sha256 c7cc0e6c...). 2026-10-27 KST, D-K9-106.

Usage:  python -B fwe_r1.py run     -> FD/out/R1_nc.json and FD/out/R1_nc.json.sha256
The pure functions below are imported by FD/selftest/test_fwe_r1.py (synthetic data).

Reads only existing caches (fwe_scan JSON, vhr link integrals, plant cell bounds), the provenance files and
FD/out/inventory.json. Opens no FZP, starts no VISSIM. Every input is sha256-pinned; a changed input stops the run.
Rules come from the pinned existing tools: congested bin / zone onset / bottleneck head / delay = fwe_analyze.py
(imported), spill tails = tails.py (imported), seven zones = vsl_metrics.py:56, cell bounds = vsl_cell_scan output.
Interpretations fixed before data: LOG.md 16:45 (1)-(6).
"""
import ast, hashlib, importlib.util, json, os, sys, time

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
CW = SP + '/codex_handoff/work'
SCAN = SP + '/rmcause/phys/scan'

PINS = {
    FD + '/PRE_FWE.md': 'c7cc0e6cc629da156b3ada7278af0fd95a0be4bf80d86ac6532b09e21656ce94',
    FD + '/out/inventory.json': 'f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6',
    SP + '/rmcause/phys/fwe_analyze.py': '5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf',
    SP + '/rmcause/phys/fwe_scan.py': '0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7',
    SP + '/rmcause/o1o4/work/tails.py': 'cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569',
    SP + '/vsl_v3c3/tools/vsl_metrics.py': '160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c',
    SP + '/vsl_v3c3/out/cell/nc3_s31.json': '6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53',
    SCAN + '/nc_s31.json': '352bddd3a28671575b7671ef1f013c816aa1c163ebd77bd320f452306abe00db',
    SCAN + '/nc_s41.json': '65051df07d65bbde5a287dc959481b2043a3e70f93104aad5b862dd32d811cd4',
    SCAN + '/nc_s43.json': '7afd43e8ed482fa60ae5cf5736f4b6e38b07f9844fc3737ec22f372441b2a843',
    SCAN + '/cf_s29_none.json': 'd5113843de6fe23f630e06bf820ad6fb39f66d534192c5a6c1601e045eed133c',
    CW + '/vhr/scan_out/nc3_s31.json': '160e619d5831f105f4b8b15224b57ab7bf1ab3f56f7d3af4810e98fae540f54a',
    CW + '/vhr/scan_out/nc3_s41.json': '4983b9b4f8099b1b722d3bbd0e2f83dbefa12b0901b7265939ac175c1b900e68',
    CW + '/vhr/scan_out/nc3_s43.json': '8725a1c66171675124425b4db6ec9ad4b2ebdcdc16dfbbd03a490006d4156048',
    CW + '/vhr/scan_out/lnc.json': '0f666f4f952f2f15d826e2cf46af2ab67d09de68345477846b2532b72ce9683f',
    CW + '/vhr/scan_out/nc_raw.json': 'c5d5eaae592b64641bbaa767fd94c0bf098b5311113790d357471a7782f0d5c8',
    CW + '/vhr/vhr_scan.py': 'a19942b8358b353329c30818c59b63cc88ff4b65e8b3dfa291de89e4c1de1865',
}

# arm key (network prefix + seed) -> inventory arm label, network, provenance seed, fwe_scan tag, vhr tag
ARMS = [
    ('v3c3-s31', 'NC3', 'v3c3', 31, 'nc_s31', 'nc3_s31'),
    ('v3c3-s41', 'NC3', 'v3c3', 41, 'nc_s41', 'nc3_s41'),
    ('v3c3-s43', 'NC3', 'v3c3', 43, 'nc_s43', 'nc3_s43'),
    ('64cf-s29 LNC', 'LNC', '64cf', 29, 'cf_s29_none', 'lnc'),
]
R1A_ONLY = [('64cf-s29 codex NC', 'codex NC', '64cf', 29, None, 'nc_raw')]   # link integrals only (PRE 5.0)

FWE7 = ['74', '10699', '2', '10613', '119', '10702', '24']          # (1), PRE section 2
RAMPS = ['10639', '10681', '10490', '10484']
OFFS = ['10643', '10682', '10481', '10483']
KC = 15.0            # density threshold veh/km/lane (fwe_analyze.py:56 literal)
W300 = 5             # 60 s windows per 300 s window
N300 = 30            # 300 s windows in [0, 9000)
HEAD_LANE_MIN = 10   # heads with >= 10 minutes get the lane read-out (PRE R1-e)

# INV_PHYSICS.md:91-93, 96 (read 2026-10-27 16:4x, s47/s53 lines never read): S-7 targets
S7_EXPECT = {
    'v3c3-s31': {'b1_tail_min_m': 4600, 'b1_tail_min_at_s': 2520, 'b1_spill_min_lt4500': 0, 'b2_tail_min_m': 7000, 'm_spill_min_lt6800': 0},
    'v3c3-s41': {'b1_tail_min_m': 4500, 'b1_tail_min_at_s': 3960, 'b1_spill_min_lt4500': 0, 'b2_tail_min_m': 5600, 'm_spill_min_lt6800': 12},
    'v3c3-s43': {'b1_tail_min_m': 4400, 'b1_tail_min_at_s': 1500, 'b1_spill_min_lt4500': 2, 'b2_tail_min_m': 6600, 'm_spill_min_lt6800': 3},
    '64cf-s29 LNC': {'b1_tail_min_m': 3300, 'b1_tail_min_at_s': 5160, 'b1_spill_min_lt4500': 62, 'b2_tail_min_m': 3800, 'm_spill_min_lt6800': 19},
}
# INV_PHYSICS.md:64-66 (section 3.1 table; extra check declared LOG 16:45 (5), report only)
X31_EXPECT = {
    'v3c3-s31': {'B1_4200_5300': (1080, 113), 'B2_6800_7900': (2280, 34), 'M_5300_6800': (None, 0), 'heads': {5000: 49, 7600: 13}},
    'v3c3-s41': {'B1_4200_5300': (1200, 118), 'B2_6800_7900': (1380, 61), 'M_5300_6800': (2160, 48), 'heads': {5000: 37, 4300: 34, 7600: 28}},
    'v3c3-s43': {'B1_4200_5300': (1020, 113), 'B2_6800_7900': (1200, 53), 'M_5300_6800': (2940, 23), 'heads': {5000: 30, 7600: 24, 4300: 15}},
}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def pinned(p):
    s = sha(p)
    if p in PINS and s != PINS[p]:
        raise SystemExit('pinned input changed: %s (%s)' % (p, s))
    return s


def jload(p):
    pinned(p)
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def load_module(name, p):
    pinned(p)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def zones7_from_vsl_metrics(p):
    pinned(p)
    with open(p, encoding='utf-8') as f:
        line = f.read().splitlines()[55]          # vsl_metrics.py:56
    if not line.startswith('ZONES = '):
        raise SystemExit('vsl_metrics.py:56 is not the ZONES line')
    return [(n, float(a), float(e)) for n, a, e in ast.literal_eval(line[len('ZONES = '):])]


# ---------------------------------------------------------------- pure functions (selftest imports these)

def grids(d, A):
    """speed V, density K, congested flag per [w][b] with fwe_analyze.cell (same as analyse())."""
    nb, nw = d['nb'], d['nw']
    V = [[None] * nb for _ in range(nw)]
    cong = [[False] * nb for _ in range(nw)]
    for w in range(nw):
        for b in range(nb):
            v, k = A.cell(d, w, b)
            V[w][b] = v
            cong[w][b] = (v is not None and v < A.VCONG and k > KC)
    return V, cong


def centre(b, bin_m=100.0):
    return (b + 0.5) * bin_m


def chain_link(x, chain):
    """chain link whose offset is the largest <= x (chain = fwe_scan CHAIN)."""
    best = None
    for l, off, _ in chain:
        if off <= x:
            best = l
    return best


def cell_of(x, bounds):
    """0-based plant cell: bounds[c] <= x < bounds[c+1]; x at/after the end -> last cell."""
    n = len(bounds) - 1
    for c in range(n):
        if bounds[c] <= x < bounds[c + 1]:
            return c
    return n - 1 if x >= bounds[-1] else None


def zone_bins(nb, a, e, bin_m=100.0):
    return [b for b in range(nb) if a <= centre(b, bin_m) < e]


def onset(cong, bs, need):
    """first window w with >= need congested bins of bs in w and w+1 (fwe_analyze.py:63-67 with need=2)."""
    nw = len(cong)
    for w in range(nw - 1):
        if sum(cong[w][b] for b in bs) >= need and sum(cong[w + 1][b] for b in bs) >= need:
            return w
    return None


def heads_by_window(V, cong, vfree):
    """{w: [b, ...]} bottleneck heads: congested bin whose two downstream bins have speed >= vfree (fwe_analyze.py:84-89)."""
    out = {}
    nw, nb = len(cong), len(cong[0])
    for w in range(nw):
        for b in range(nb - 2):
            if cong[w][b] and V[w][b + 1] is not None and V[w][b + 2] is not None and V[w][b + 1] >= vfree and V[w][b + 2] >= vfree:
                out.setdefault(w, []).append(b)
    return out


def head_lane(d, b, wins, bin_m=100.0):
    """lane mean speeds over lane bins for chain [x-300, x+100) (x = b*bin_m) and the windows wins (LOG 16:45 (3))."""
    x0, x1 = d['lane_x0'], d['lane_x1']
    nlb = len(d['lN'][0])
    want = [b - 3, b - 2, b - 1, b]
    lbs = []
    for bb in want:
        xs = bb * bin_m
        if x0 <= xs < x1:
            lb = int((xs - x0) // bin_m)
            if 0 <= lb < nlb:
                lbs.append(lb)
    if not lbs:
        return {'status': 'no_lane_bins', 'lane_bins_used': 0}
    N = [0, 0, 0, 0]
    S = [0.0, 0.0, 0.0, 0.0]
    for w in wins:
        for lb in lbs:
            for i in range(4):
                N[i] += d['lN'][w][lb][i]
                S[i] += d['lV'][w][lb][i]
    sp = [round(S[i] / N[i], 2) if N[i] else None for i in range(4)]
    cand = [(sp[i], i + 1) for i in range(4) if sp[i] is not None]
    low = min(cand)[1] if cand else None
    return {'status': 'full' if len(lbs) == 4 else 'partial', 'lane_bins_used': len(lbs),
            'lane_x_from_m': x0 + min(lbs) * bin_m, 'lane_x_to_m': x0 + (max(lbs) + 1) * bin_m,
            'lane_mean_speed_kmh': {str(i + 1): sp[i] for i in range(4)},
            'lane_vehicle_frames': {str(i + 1): N[i] for i in range(4)}, 'lowest_speed_lane': low}


def per300(arr60, n300=N300):
    return [sum(arr60[k * W300:(k + 1) * W300]) for k in range(n300)]


def zone_series(d, V, cong, bs, vref):
    """per 300 s: vehicle-frames, speed sum, veh-h, mean speed, congested minutes, delay(vref) veh-h."""
    nw = d['nw']
    vf = [sum(d['gN'][w][b] for b in bs) for w in range(nw)]
    vs = [sum(d['gV'][w][b] for b in bs) for w in range(nw)]
    cm = [1 if any(cong[w][b] for b in bs) else 0 for w in range(nw)]
    dl = [sum(d['gN'][w][b] * max(0.0, 1.0 - (V[w][b] or 0.0) / vref) for b in bs) for w in range(nw)]
    VF, VS, CM, DL = per300(vf), per300(vs), per300(cm), per300(dl)
    return {
        'vehicle_frames_300': VF, 'speed_sum_300': [round(x, 3) for x in VS],
        'veh_h_300': [round(x * 5.0 / 3600.0, 4) for x in VF],
        'mean_speed_kmh_300': [round(VS[k] / VF[k], 3) if VF[k] else None for k in range(N300)],
        'cong_minutes_300': CM, 'delay_veh_h_300': [round(x * 5.0 / 3600.0, 4) for x in DL],
        'veh_h_0_9000': round(sum(VF) * 5.0 / 3600.0, 4),
        'mean_speed_kmh_0_9000': round(sum(VS) / sum(VF), 3) if sum(VF) else None,
        'cong_minutes_all_windows': sum(cm), 'cong_bin_minutes': sum(1 for w in range(nw) for b in bs if cong[w][b]),
        'delay_veh_h_0_9000': round(sum(DL) * 5.0 / 3600.0, 4),
        'vf_windows_ge_9000': sum(vf[N300 * W300:]),
    }


def rate300(arr60):
    """veh/h per 300 s window from per-60 s counts."""
    return [round(x * 3600.0 / 300.0, 1) for x in per300(arr60)]


def tails_extra(t):
    """first/last spill windows and B2 tail minimum time from tails.tails() lists (same min rule as tails.summary)."""
    b2 = [(w, x) for w, x in enumerate(t['b2_tail_m']) if x is not None]
    b2min = min(b2, key=lambda p: (p[1], p[0])) if b2 else None
    b1s = [w for w, x in enumerate(t['b1_tail_m']) if x is not None and x < 4500]
    ms = [w for w, x in enumerate(t['b2_tail_m']) if x is not None and x < 6800]
    return {'b2_tail_min_at_s': b2min[0] * 60 if b2min else None,
            'b1_spill_first_s': b1s[0] * 60 if b1s else None, 'b1_spill_last_end_s': b1s[-1] * 60 + 60 if b1s else None,
            'm_spill_first_s': ms[0] * 60 if ms else None, 'm_spill_last_end_s': ms[-1] * 60 + 60 if ms else None,
            'b1_spill_minutes_300': [sum(1 for w in b1s if k * W300 <= w < (k + 1) * W300) for k in range(N300)],
            'm_spill_minutes_300': [sum(1 for w in ms if k * W300 <= w < (k + 1) * W300) for k in range(N300)]}


def fwe7_sum(integrals, form):
    I = integrals[form]
    return sum(I.get(l, 0.0) for l in FWE7)


def r1_arm(d, A, T, chain, zones5, zones7, bounds):
    """R1-b..g for one fwe_scan dict d."""
    if abs(d['bin_m'] - 100.0) > 1e-9 or abs(d['win_s'] - 60.0) > 1e-9:
        raise SystemExit('unexpected fwe_scan grid')
    nb, nw = d['nb'], d['nw']
    V, cong = grids(d, A)
    ncell = len(bounds) - 1
    bin_cell = [cell_of(centre(b), bounds) for b in range(nb)]
    bin_link = [chain_link(centre(b), chain) for b in range(nb)]
    zb5 = {z: zone_bins(nb, a, e) for z, (a, e) in zones5}
    zb7 = {z: zone_bins(nb, a, e) for z, a, e in zones7}
    cellb = {c: [b for b in range(nb) if bin_cell[b] == c] for c in range(ncell)}
    hw = heads_by_window(V, cong, A.VFREE)

    def heads_at(w, bs=None):
        out = []
        for b in hw.get(w, []):
            out.append({'x_m': int(b * 100), 'cell': bin_cell[b], 'link': bin_link[b], 'in_set': (bs is not None and b in bs)})
        return out

    res = {'R1b_R1c_zones5': {}, 'R1b_R1c_zones7': {}, 'R1c_cells': {}, 'R1d_onset': {'zones5': {}, 'zones7': {}, 'cells': {}}}
    for key, zb in (('R1b_R1c_zones5', zb5), ('R1b_R1c_zones7', zb7)):
        for z, bs in zb.items():
            res[key][z] = zone_series(d, V, cong, bs, A.VREF)
            res[key][z]['bins'] = [bs[0] * 100, bs[-1] * 100 + 100] if bs else None
            w = onset(cong, bs, 2)
            res['R1d_onset']['zones5' if key.endswith('5') else 'zones7'][z] = {
                'onset_s': w * 60 if w is not None else None, 'heads_in_onset_window': heads_at(w, set(bs)) if w is not None else []}
    for c, bs in cellb.items():
        s = zone_series(d, V, cong, bs, A.VREF) if bs else None
        res['R1c_cells'][str(c)] = None if s is None else {
            'x_m': [bounds[c], bounds[c + 1]], 'bins': len(bs), 'cong_minutes_all_windows': s['cong_minutes_all_windows'],
            'cong_minutes_300': s['cong_minutes_300'], 'veh_h_0_9000': s['veh_h_0_9000'], 'mean_speed_kmh_0_9000': s['mean_speed_kmh_0_9000'],
            'veh_h_300': s['veh_h_300'], 'mean_speed_kmh_300': s['mean_speed_kmh_300']}
        w = onset(cong, bs, 1) if bs else None
        res['R1d_onset']['cells'][str(c)] = {'onset_s': w * 60 if w is not None else None,
                                             'heads_in_onset_window': heads_at(w, set(bs)) if w is not None else []}
    # R1-e heads
    hmin, hfirst, hlast, hwins = {}, {}, {}, {}
    for w in sorted(hw):
        for b in hw[w]:
            hmin[b] = hmin.get(b, 0) + 1
            hfirst.setdefault(b, w * 60)
            hlast[b] = w * 60 + 60
            hwins.setdefault(b, []).append(w)
    heads = []
    for b in sorted(hmin, key=lambda bb: (-hmin[bb], bb)):
        z5 = [z for z, bs in zb5.items() if b in bs]
        z7 = [z for z, bs in zb7.items() if b in bs]
        h = {'x_m': int(b * 100), 'minutes': hmin[b], 'first_s': hfirst[b], 'last_end_s': hlast[b],
             'link': bin_link[b], 'cell': bin_cell[b], 'zone5': z5[0] if z5 else None, 'zone7': z7[0] if z7 else None,
             'minutes_300': [sum(1 for w in hwins[b] if k * W300 <= w < (k + 1) * W300) for k in range(N300)]}
        if hmin[b] >= HEAD_LANE_MIN:
            h['lane'] = head_lane(d, b, hwins[b])
        heads.append(h)
    res['R1e_heads'] = heads
    # R1-f tails
    t = T.tails(d)
    s = T.summary(d)
    res['R1f_tails'] = {k: s[k] for k in ('b1_tail_min_m', 'b1_tail_min_at_s', 'b1_spill_min_lt4500', 'b2_tail_min_m', 'm_spill_min_lt6800')}
    res['R1f_tails'].update(tails_extra(t))
    res['R1f_tails']['b1_tail_m_60s'] = t['b1_tail_m']
    res['R1f_tails']['b2_tail_m_60s'] = t['b2_tail_m']
    # R1-g ramps / off-ramps / entry / delay (analyse() + per 300 s)
    an = A.analyse(d)
    g = {'analyse_ramp_veh_h': an['ramp_veh_h'], 'analyse_ramp_queued_veh_h': an['ramp_queued_veh_h'],
         'analyse_offramp_queued_veh_h': an['offramp_queued_veh_h'], 'analyse_ins_total': an['ins_total'],
         'analyse_zone_delay_vref108': {z: v['delay_veh_h_vref108'] for z, v in an['zones'].items()},
         'analyse_delay_total_vref108': an['delay_total_vref108'], 'ramps': {}, 'offramps': {}}
    for rm in RAMPS:
        st = [a + b for a, b in zip(d['conn_stock'][rm], d['from_stock'][rm])]
        qq = [a + b for a, b in zip(d['conn_q'][rm], d['from_q'][rm])]
        g['ramps'][rm] = {'merge_veh_per_h_300': rate300(d['merge'][rm]), 'merge_count_0_9000': sum(per300(d['merge'][rm])),
                          'stock_veh_h_300': [round(x * 5.0 / 3600.0, 4) for x in per300(st)],
                          'queued_veh_h_300': [round(x * 5.0 / 3600.0, 4) for x in per300(qq)],
                          'stock_veh_h_0_9000': round(sum(per300(st)) * 5.0 / 3600.0, 4),
                          'queued_veh_h_0_9000': round(sum(per300(qq)) * 5.0 / 3600.0, 4)}
    for o in OFFS:
        g['offramps'][o] = {'queued_veh_h_300': [round(x * 5.0 / 3600.0, 4) for x in per300(d['off_q'][o])],
                            'queued_veh_h_0_9000': round(sum(per300(d['off_q'][o])) * 5.0 / 3600.0, 4)}
    g['ins_74_veh_per_h_300'] = rate300(d['ins'])
    g['ins_74_count_0_9000'] = sum(per300(d['ins']))
    res['R1g'] = g
    # cross-checks against analyse() (same rules; report only)
    chk = {}
    for z, v in an['zones'].items():
        mine = res['R1b_R1c_zones5'][z]
        chk[z] = {'cong_minutes_any_equal': v['cong_minutes_any'] == mine['cong_minutes_all_windows'],
                  'onset_equal': v['onset_s'] == res['R1d_onset']['zones5'][z]['onset_s'],
                  'veh_h_diff': round(v['veh_h'] - (mine['veh_h_0_9000'] + mine['vf_windows_ge_9000'] * 5.0 / 3600.0), 3),
                  'delay_diff': round(v['delay_veh_h_vref108'] - mine['delay_veh_h_0_9000'], 3)}
    top = {int(k): v for k, v in an['bottleneck_heads_minutes'].items()}
    mineh = {h['x_m']: h['minutes'] for h in heads}
    chk['heads_top12_equal'] = all(mineh.get(x) == m for x, m in top.items())
    res['check_vs_analyse'] = chk
    res['_analyse_zones'] = {z: {'onset_s': v['onset_s'], 'cong_minutes_any': v['cong_minutes_any'], 'cong_km_h': v['cong_km_h'],
                                 'veh_h': v['veh_h'], 'last_cong_end_s': v['last_cong_end_s']} for z, v in an['zones'].items()}
    res['_analyse_heads_top12'] = an['bottleneck_heads_minutes']
    res['chain_vehicle_frames_0_9000'] = sum(sum(d['gN'][w]) for w in range(N300 * W300))
    res['chain_veh_h_bin_0_9000'] = round(res['chain_vehicle_frames_0_9000'] * 5.0 / 3600.0, 4)
    res['chain_veh_h_5s_scan'] = d['chain_veh_h_5s']
    res['frames_per_60s_first_last'] = [d['frames'][0], d['frames'][N300 * W300 - 1], d['frames'][-1]]
    return res


# ---------------------------------------------------------------- run

def provenance_ok(run, seed):
    p = run['provenance']['path'].replace('\\', '/')
    s = sha(p)
    with open(p, 'rb') as f:
        js = json.loads(f.read().decode('utf-8-sig'))
    return {'path': p, 'sha256': s, 'sha_equals_inventory': s == run['provenance']['sha256'],
            'seed': js.get('seed'), 'seed_equals_expected': js.get('seed') == seed}


def main_run():
    t0 = time.time()
    for p in PINS:
        pinned(p)
    inv = jload(FD + '/out/inventory.json')
    A = load_module('fwe_analyze', SP + '/rmcause/phys/fwe_analyze.py')
    T = load_module('tails', SP + '/rmcause/o1o4/work/tails.py')
    S = load_module('fwe_scan', SP + '/rmcause/phys/fwe_scan.py')
    zones5 = list(A.ZONES.items())
    zones7 = zones7_from_vsl_metrics(SP + '/vsl_v3c3/tools/vsl_metrics.py')
    bounds = jload(SP + '/vsl_v3c3/out/cell/nc3_s31.json')['cell_bounds_m']
    if len(bounds) != 32:
        raise SystemExit('expected 32 cell bounds')
    out = {'tool': 'fwe_r1.py', 'tool_sha256': sha(os.path.abspath(__file__)), 'pre_fwe_sha256': PINS[FD + '/PRE_FWE.md'],
           'started_kst': time.strftime('%Y-%m-%d %H:%M:%S'), 'inputs_sha256': {p: PINS[p] for p in PINS},
           'definitions': {'zones5': zones5, 'zones7': zones7, 'cell_bounds_m': bounds, 'fwe7': FWE7, 'chain': S.CHAIN,
                           'vcong': A.VCONG, 'kcong': KC, 'vfree_head': A.VFREE, 'vref_delay': A.VREF,
                           'windows_300': [[k * 300, k * 300 + 300] for k in range(N300)], 'cell_index': '0-based',
                           'lane_rule': 'LOG.md 16:45 (3)', 'onset_heads_rule': 'LOG.md 16:45 (2)'},
           'arms': {}, 'R1a': {}, 'stops': [], 'S7': {}, 'extra_check_inv31': {}}
    invmap = {(r['arm'], r['net'], r['provenance']['seed']): r for r in inv['runs']}
    vhr = {}
    for key, arm, net, seed, scan_tag, vhr_tag in ARMS + R1A_ONLY:
        run = invmap.get((arm, net, seed))
        if run is None:
            raise SystemExit('inventory row missing: %s' % key)
        prov = provenance_ok(run, seed)
        fzp = run['fzp']['path'].replace('\\', '/')
        cached = run['fzp_sha256_cached']
        ok = prov['sha_equals_inventory'] and prov['seed_equals_expected'] and len(set(cached)) == 1
        v = jload(CW + '/vhr/scan_out/%s.json' % vhr_tag)
        vok = v['file_sha256'] in cached and v['path'].replace('\\', '/') == fzp
        rec = {'arm': arm, 'net': net, 'seed_expected': seed, 'provenance': prov, 'fzp': fzp, 'fzp_sha256': cached[0],
               'vhr_file': CW + '/vhr/scan_out/%s.json' % vhr_tag, 'vhr_fzp_sha_ok': vok}
        if not (ok and vok):
            out['stops'].append({'arm': key, 'rule': 'S-2/S-1', 'detail': rec})
            out['arms'][key] = rec
            continue
        I = v['integrals']
        out['R1a'][key] = {'fwe7_ours_9000': round(fwe7_sum(I, 'ours_9000'), 4), 'fwe7_codex_8100': round(fwe7_sum(I, 'codex_8100'), 4),
                           'per_link_ours_9000': {l: round(I['ours_9000'].get(l, 0.0), 4) for l in FWE7},
                           'per_link_codex_8100': {l: round(I['codex_8100'].get(l, 0.0), 4) for l in FWE7}}
        vhr[key] = I
        if scan_tag is not None:
            d = jload(SCAN + '/%s.json' % scan_tag)
            sok = d['fzp_sha256'] in cached and d['fzp'].replace('\\', '/') == fzp
            rec['fwe_scan_file'] = SCAN + '/%s.json' % scan_tag
            rec['fwe_scan_fzp_sha_ok'] = sok
            if not sok:
                out['stops'].append({'arm': key, 'rule': 'S-1', 'detail': 'fwe_scan fzp sha/path differs'})
                out['arms'][key] = rec
                continue
            r = r1_arm(d, A, T, S.CHAIN, zones5, zones7, bounds)
            rec['R1'] = r
            rec['check_chain_bin_vs_fwe7_ours_9000'] = round(r['chain_veh_h_bin_0_9000'] - out['R1a'][key]['fwe7_ours_9000'], 4)
            # S-7
            exp = S7_EXPECT[key]
            got = {k: r['R1f_tails'][k] for k in exp}
            out['S7'][key] = {'expected_INV_PHYSICS': exp, 'got': got, 'equal': got == exp}
            if got != exp:
                out['stops'].append({'arm': key, 'rule': 'S-7', 'detail': {'expected': exp, 'got': got}})
            if key in X31_EXPECT:
                e = X31_EXPECT[key]
                cmp = {}
                for z in ('B1_4200_5300', 'B2_6800_7900', 'M_5300_6800'):
                    g = (r['R1d_onset']['zones5'][z]['onset_s'], r['R1b_R1c_zones5'][z]['cong_minutes_all_windows'])
                    cmp[z] = {'expected': list(e[z]), 'got': list(g), 'equal': tuple(g) == e[z]}
                hm = {h['x_m']: h['minutes'] for h in r['R1e_heads']}
                cmp['heads'] = {str(x): {'expected': m, 'got': hm.get(x), 'equal': hm.get(x) == m} for x, m in e['heads'].items()}
                out['extra_check_inv31'][key] = cmp
        out['arms'][key] = rec
    if '64cf-s29 LNC' in vhr and '64cf-s29 codex NC' in vhr:
        a, b = vhr['64cf-s29 LNC'], vhr['64cf-s29 codex NC']
        mx = 0.0
        for form in ('ours_9000', 'codex_8100'):
            for l in set(a[form]) | set(b[form]):
                mx = max(mx, abs(a[form].get(l, 0.0) - b[form].get(l, 0.0)))
        out['R1a_check_lnc_vs_codex_nc_max_abs_link_diff'] = mx
    out['elapsed_s'] = round(time.time() - t0, 1)
    os.makedirs(FD + '/out', exist_ok=True)
    p = FD + '/out/R1_nc.json'
    with open(p + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(p + '.tmp', p)
    with open(p + '.sha256', 'w', encoding='utf-8') as f:
        f.write('%s *R1_nc.json\n' % sha(p))
    print('R1 done', out['elapsed_s'], 's; stops:', len(out['stops']), '; S7:', {k: v['equal'] for k, v in out['S7'].items()})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        main_run()
    else:
        print(__doc__)
