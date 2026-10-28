# -*- coding: utf-8 -*-
"""fwe_r4.py - D-K9-106 R4: codex split arms on 64cf-s29 (PRE_FWE §5.4, codex form [0, 8100]). 2026-10-27 KST.

Usage: python -B fwe_r4.py [key=path ...]   keys for the new heavy outputs (R3 turn's H4/H5):
       first_fw=<first-seen json of freeway_only>  first_urb=<first-seen json of urban_only>
       scan_urb=<fwe_scan json of urban_only>  lb_urb=<linkbin json of urban_only>  lb_fw=<linkbin json of freeway_only>
       first_fw_sha / first_urb_sha = FZP sha256 that the producing job verified for that first-seen file (no fzp field inside)
Reads only cached scan outputs, definition files, provenance files and meter LDP text files. Writes FD/out/R4_codex.json.
Rules: same-seed pairs only (64cf-s29); never subtracted from v3c3; GREEN-only meter seconds; urban = codex partition.
"""
import ast
import csv
import hashlib
import json
import os
import re
import sys
import time

sys.dont_write_bytecode = True
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
H = 'D:/VISSIM_handoff/20261024'
CW = SP + '/codex_handoff/work'
WEND = 8100.0
NW60 = 135            # 60 s windows inside [0, 8100)
NW300 = 27            # 300 s windows inside [0, 8100)
CYC0 = 900            # first meter cycle
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
LOCAL19 = FWE7 | {'10484', '10490', '10639', '10681', '10481', '10483', '10643', '10682', '129', '31', '68', '70'}
FWW3 = {'26', '10771', '120'}
ENTRY_SIDE = ['10639', '10681', '10490', '10484', '70', '68', '129', '31']
EXIT_SIDE = ['10643', '10682', '10481', '10483']
RAMPS = ['10639', '10681', '10490', '10484']
RAMP_FROM = {'10639': '70', '10681': '68', '10490': '129', '10484': '31'}
METERS = {'9101': 'RM_C10480', '9102': 'RM_C10482', '9103': 'RM_C10646', '9104': 'RM_C10644',
          '9105': 'RM_C10639', '9106': 'RM_C10681', '9107': 'RM_C10490', '9108': 'RM_C10484'}
FWE_METERS = ['9105', '9106', '9107', '9108']
FWW_METERS = ['9101', '9102', '9103', '9104']

# ---------------------------------------------------------------- pinned inputs (sha256 from FD/out/pins_existing.json / INVENTORY.md)
PIN = {
    SP + '/rmcause/phys/fwe_analyze.py': '5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf',
    SP + '/rmcause/o1o4/work/tails.py': 'cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569',
    SP + '/vsl_v3c3/tools/vsl_metrics.py': '160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c',
    CW + '/vhr/vhr_unins.py': 'fc233013623d797657c19e0efbb59b6ccad720a19a84e723491ad73a34337532',
    CW + '/rawcheck/rm_exec.py': '27f6402205d6c7cbd3524a44ee35632e19a90f681a10d21fffa3b5518dbb1c10',
    H + '/derived/omega_membership_exact.json': 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473',
    H + '/derived/reporting_partition.json': '3142f69c0502f6d9d12416b5b6131d57799bf8f2d17d207b4b0312e854f1dd2b',
    H + '/derived/metrics_0_8100.csv': 'a2757f7288ba3f0e0d91222c25d353c0f3f015af28e2f9ebdb594508e3cfc37a',
    H + '/derived/independent_fzp_counts.json': 'f55be7114af7b1d9049e7daee9748e667491dd486a07c1e92b6bc0aa010e09b4',
    H + '/derived/decision_greens.csv': '5f63309329ab26f1a7269b77ac9f1c964bfb2115fbcd4b18a455ff87086792e0',
    # vhr link integrals (codex_8100 used)
    CW + '/vhr/scan_out/nc_raw.json': 'c5d5eaae592b64641bbaa767fd94c0bf098b5311113790d357471a7782f0d5c8',
    CW + '/vhr/scan_out/joint.json': '771c0ffeb21cd037ffe075588387d673f6659789a12edd5b638847417e904f25',
    CW + '/vhr/scan_out/window.json': 'ae3558f6aabed0a7446432d21872b3885f02ea17a0e3e34812f710de35f7b266',
    CW + '/vhr/scan_out/off.json': 'a4407838e90d965e5e2e4cfa9b008b9f64561ba70c73b3532ac6e090f2ee0599',
    CW + '/vhr/scan_out/freeway_only.json': 'b3eb447174aca51c5a07e026d17952f07e14c46afc389cbbf5e063493f41ec3a',
    CW + '/vhr/scan_out/urban_only.json': '23278f7302436af775ab681b62abbb7273d73113902c94f7b40aaee51ea40564',
    CW + '/vhr/scan_out/lnc.json': '0f666f4f952f2f15d826e2cf46af2ab67d09de68345477846b2532b72ce9683f',
    # first-seen
    CW + '/vhr/scan_out/first_nc_raw.json': '2a1ea7fa303a69d294d234cdc4368dba75158cfb29a1fc3af761241a14735b45',
    CW + '/vhr/scan_out/first_joint.json': '259552528126b94625f5e877f70c1ed35d91811afbfa7313628a2510a496dfa7',
    CW + '/vhr/scan_out/first_window.json': 'e59c298b22881e0d3738af3a03e614cad3c951032fecfb9e6feab75107f0acad',
    CW + '/vhr/scan_out/first_off.json': 'c7b20fc4548bfc4f03f6c6a4c84ec2ea8077e42edb6bacba01d51535669c831a',
    CW + '/a1/full/firstseen/first_a1.json': 'fc1fb0253f643e8258969a89751468f3e58e17e037678e01b6a613876e14e3fc',
    CW + '/a1/full/firstseen/first_lnc.json': '8eefa931a343ab3918966834ca9c48f6cd8a6c03b455e8572856313e944f57ce',
    SP + '/c_port/vsl/out/first_vsl.json': 'ceb5f188fd41090e8288d5d07dcd89d1050cc38c5afc6459229f9b670a91bc77',
    # fwe_scan
    SP + '/rmcause/phys/scan/cf_s29_none.json': 'd5113843de6fe23f630e06bf820ad6fb39f66d534192c5a6c1601e045eed133c',
    SP + '/c_port/vsl/out/scan/cx_joint_s29.json': 'c2d2b8dc7a36315d4307429ebc3f931b746d958e4586eeb42071a87be2de8bb3',
    SP + '/c_port/vsl/out/scan/cx_window_s29.json': 'a7d8a926f6af679472a8cd2017b14e4fce95245be1454530511984bcacd0ea68',
    SP + '/c_port/vsl/out/scan/cx_off_s29.json': 'd13da72e196fb270c807241e8cd41ea4b5ce932b8e80cdaaa13bb9bde85e0e2b',
    SP + '/c_port/vsl/out/scan/cx_fwonly_s29.json': 'f01c1f65eb5c650c447f697701b1c628e777716d606ddbc441374d917a5fe342',
    SP + '/c_port/vsl/out/scan/a1_s29.json': '5f996c93076b439e026edf3e37d60c5279df88bd0cc585f68d620b3c2b357ad4',
    SP + '/rmcause/o1o4/scan/vsl_s29.json': '89793cf05fc3e52aa3381606dce2baa40f66ddef5306536ded651bb6c982d471',
    # linkbin
    SP + '/rmcause/o1o4/scan/lb_nc_s29.json': 'bc30ba31d693306014b276807be13a73fd4a4d740fee84a45c020d6d17a41ddd',
    SP + '/rmcause/o1o4/scan/lb_vsl_s29.json': '96220220eea4fa4ec51460d605fd53537de83f10061a77e743c55b897259dec4',
    # inventory (provenance sha, inpx sha)
    FD + '/out/inventory.json': 'f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6',
}
FZP_SHA = {   # INVENTORY.md §1 (cached FZP sha256)
    'nc': '1eaad57ff402963488e71dfd4440b6a9b6149249a4334430e51660e97d81a4d0',
    'joint': 'c0aa41bbdfc1cee4ac5d9531d555e317fac9dd208da52c751d8c449e1d2f0ac6',
    'window': 'ce2742b7f6934dda970dd8d3045683303cb716a0bb7d55f836f39b24f697a6c1',
    'off': '73a20cbb813152f0f79a7955c3fe68ee508bc32f365382a3ca0898245f8a63c9',
    'freeway_only': '05b45b03ed323ad67bef1271ebeb0a5df88a320cdd9a906fade801efa201cdc2',
    'urban_only': 'a8a4b4e2a681be36f0c89e908f6f13e837a75eb60870d887256c5935e4ca5b38',
    'a1': '9bf7c8c6f56099fb295cd5451377869fe9c73c0c725324ede74c4f3b7a31b6fb',
    'lnc': '9c097cc7e1f2840aea1cc61520a6302aa417b2925f33890fcde24c432e301f8b',
    'vsl': 'c874323fef14500d2232e314d512d3a745c35cecee9c9b253b8f25dfe5237200',
}
VHR_TAG = {'nc': 'nc_raw', 'joint': 'joint', 'window': 'window', 'off': 'off', 'freeway_only': 'freeway_only',
           'urban_only': 'urban_only', 'lnc': 'lnc'}
FIRST = {'nc': CW + '/vhr/scan_out/first_nc_raw.json', 'joint': CW + '/vhr/scan_out/first_joint.json',
         'window': CW + '/vhr/scan_out/first_window.json', 'off': CW + '/vhr/scan_out/first_off.json',
         'a1': CW + '/a1/full/firstseen/first_a1.json', 'lnc': CW + '/a1/full/firstseen/first_lnc.json',
         'vsl': SP + '/c_port/vsl/out/first_vsl.json'}
SCAN = {'lnc': SP + '/rmcause/phys/scan/cf_s29_none.json', 'joint': SP + '/c_port/vsl/out/scan/cx_joint_s29.json',
        'window': SP + '/c_port/vsl/out/scan/cx_window_s29.json', 'off': SP + '/c_port/vsl/out/scan/cx_off_s29.json',
        'freeway_only': SP + '/c_port/vsl/out/scan/cx_fwonly_s29.json', 'a1': SP + '/c_port/vsl/out/scan/a1_s29.json',
        'vsl': SP + '/rmcause/o1o4/scan/vsl_s29.json'}
LINKBIN = {'lnc': SP + '/rmcause/o1o4/scan/lb_nc_s29.json', 'vsl': SP + '/rmcause/o1o4/scan/lb_vsl_s29.json'}
LDP = {
    'nc': H + '/raw/nc/vissim_eval/sdmpc31_nc9000_s29_{sc}_001.ldp',
    'joint': H + '/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'window': H + '/raw/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'off': H + '/raw/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'freeway_only': H + '/raw/freeway_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'urban_only': H + '/raw/urban_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp',
    'lnc': 'D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_{sc}_001.ldp',
    'vsl': 'D:/VISSIM_runs/vsl_repro_s29/vsl/run/vissim_eval/vsl_seed29_vsl_{sc}_001.ldp',
}
A1_ACTION = 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/action_sdmpc31_sdmpc8100_s29.csv'
INV_ARM = {'nc': 'codex NC', 'joint': 'codex joint', 'window': 'codex window', 'off': 'codex off',
           'freeway_only': 'codex freeway_only', 'urban_only': 'codex urban_only', 'a1': 'A1', 'lnc': 'LNC', 'vsl': 'vsl_repro vsl'}
ARMS = ['joint', 'window', 'off', 'freeway_only', 'urban_only']
PAIR_NAME = {'joint': 'Q-joint', 'window': 'Q-window', 'off': 'Q-off', 'freeway_only': 'Q-fw', 'urban_only': 'Q-urb'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 22), b''):
            h.update(ch)
    return h.hexdigest()


def jl(p):
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


# ---------------------------------------------------------------- definitions
def zones7():
    """7 aux zones read from vsl_metrics.py:56 text (exact list)."""
    line = open(SP + '/vsl_v3c3/tools/vsl_metrics.py', encoding='utf-8').read().splitlines()[55]
    assert line.startswith('ZONES = ')
    return [(z, float(a), float(e)) for z, a, e in ast.literal_eval(line[len('ZONES = '):])]


def link_sets(mem, part):
    o701 = set(map(str, mem['inside_links']))
    on = {str(k): v for k, v in part['onramp_roads'].items()}
    off = set(map(str, part['offramp_links']))
    onE = {l for l in o701 if l not in FWE7 and l not in FWW3 and on.get(l) == 'FW_E'}
    onW = {l for l in o701 if l not in FWE7 and l not in FWW3 and on.get(l) == 'FW_W'}
    offr = {l for l in o701 if l not in FWE7 and l not in FWW3 and l not in on and l in off}
    urban = o701 - FWE7 - FWW3 - onE - onW - offr
    return {'O701': o701, 'FWE7': FWE7, 'LOCAL19': LOCAL19, 'FWW3': FWW3, 'onramps_E': onE, 'onramps_W': onW,
            'offramps701': offr, 'urban': urban}


def levels(I, S):
    out = {k: sum(v for l, v in I.items() if l in s) for k, s in S.items()}
    out['A4a'] = sum(I.values())
    out['link66'] = I.get('66', 0.0)
    return out


# ---------------------------------------------------------------- first-seen difference (= vhr_unins.py S_int / dU, copied)
def S_int(F, W, cat=None):
    tot = 0.0; n = 0
    for c, d in F['by_cat'].items():
        if cat is not None and c not in cat:
            continue
        for tt, k in d.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t); n += k
    return tot / 3600, n


def dU(Fa, Fb, W, cat=None):   # U_a - U_b
    return S_int(Fb, W, cat)[0] - S_int(Fa, W, cat)[0]


# ---------------------------------------------------------------- FW_E physics from fwe_scan (bin form, windows < 8100 s)
def bins_in(nb, a, e):
    return [b for b in range(nb) if a <= (b + 0.5) * 100 < e]


def zone_windows(d, zones):
    """per 300 s window: veh_h (vehicle-frames x 5 s) and mean speed; plus total [0, 8100)."""
    out = {}
    for z, a, e in zones:
        bs = bins_in(d['nb'], a, e)
        vh, sp = [], []
        for k in range(NW300):
            ws = range(5 * k, 5 * k + 5)
            n = sum(d['gN'][w][b] for w in ws for b in bs)
            v = sum(d['gV'][w][b] for w in ws for b in bs)
            vh.append(n * 5.0 / 3600.0); sp.append(v / n if n else None)
        n = sum(d['gN'][w][b] for w in range(NW60) for b in bs)
        v = sum(d['gV'][w][b] for w in range(NW60) for b in bs)
        out[z] = {'veh_h_300': vh, 'speed_300': sp, 'veh_h_total': n * 5.0 / 3600.0, 'speed_total': (v / n if n else None)}
    return out


def cong_grid(FA, d):
    nb = d['nb']
    G = []
    for w in range(NW60):
        row = []
        for b in range(nb):
            v, k = FA.cell(d, w, b)
            row.append(v is not None and v < FA.VCONG and k > 15)
        G.append(row)
    return G


def zone_cong_minutes(G, zones, nb):
    return {z: sum(1 for w in range(NW60) if any(G[w][b] for b in bins_in(nb, a, e))) for z, a, e in zones}


def spill(TL, d):
    t = TL.tails(d)
    b1 = [(w, x) for w, x in enumerate(t['b1_tail_m'][:NW60]) if x is not None]
    b2 = [(w, x) for w, x in enumerate(t['b2_tail_m'][:NW60]) if x is not None]
    b1m = min(b1, key=lambda p: (p[1], p[0])) if b1 else None
    b2m = min(b2, key=lambda p: (p[1], p[0])) if b2 else None
    return {'b1_spill_min_lt4500': sum(1 for _, x in b1 if x < 4500), 'm_spill_min_lt6800': sum(1 for _, x in b2 if x < 6800),
            'b1_tail_min_m': b1m[1] if b1m else None, 'b1_tail_min_at_s': b1m[0] * 60 if b1m else None,
            'b2_tail_min_m': b2m[1] if b2m else None, 'b2_tail_min_at_s': b2m[0] * 60 if b2m else None,
            'b1_spill_min_300': [sum(1 for w, x in b1 if 5 * k <= w < 5 * k + 5 and x < 4500) for k in range(NW300)],
            'm_spill_min_300': [sum(1 for w, x in b2 if 5 * k <= w < 5 * k + 5 and x < 6800) for k in range(NW300)]}


def spill_full(TL, d):
    s = TL.summary(d)
    return {k: s[k] for k in ('b1_tail_min_m', 'b1_tail_min_at_s', 'b1_spill_min_lt4500', 'b2_tail_min_m', 'm_spill_min_lt6800')}


def ramps(d):
    out = {}
    for r in RAMPS:
        m, st, q, qm = [], [], [], []
        for k in range(NW300):
            ws = range(5 * k, 5 * k + 5)
            m.append(sum(d['merge'][r][w] for w in ws) * 12.0)       # veh/h over 300 s
            st.append((sum(d['conn_stock'][r][w] for w in ws) + sum(d['from_stock'][r][w] for w in ws)) * 5.0 / 3600.0)
            q.append((sum(d['conn_q'][r][w] for w in ws) + sum(d['from_q'][r][w] for w in ws)) * 5.0 / 3600.0)
            qm.append(max(d['ramp_qmax'][r][w] for w in ws))
        out[r] = {'merge_vph_300': m, 'stock_veh_h_300': st, 'queued_veh_h_300': q, 'qmax_300': qm,
                  'merge_veh_900_8100': sum(d['merge'][r][w] for w in range(15, NW60)),
                  'stock_veh_h_total': sum(st), 'queued_veh_h_total': sum(q)}
    return out


def offramps(d):
    return {o: {'stock_veh_h_300': [sum(d['off_stock'][o][w] for w in range(5 * k, 5 * k + 5)) * 5.0 / 3600.0 for k in range(NW300)],
                'queued_veh_h_300': [sum(d['off_q'][o][w] for w in range(5 * k, 5 * k + 5)) * 5.0 / 3600.0 for k in range(NW300)]}
            for o in EXIT_SIDE}


def bin_sums(d):
    """chain (= ①) and ② vehicle-frames x 5 s for [0, 8100) - for S-4 (b) / S-8 and S-14."""
    ch = [sum(sum(d['gN'][w]) for w in range(5 * k, 5 * k + 5)) * 5.0 / 3600.0 for k in range(NW300)]
    ex = []
    for k in range(NW300):
        ws = range(5 * k, 5 * k + 5)
        s = 0
        for r in RAMPS:
            s += sum(d['conn_stock'][r][w] + d['from_stock'][r][w] for w in ws)
        for o in EXIT_SIDE:
            s += sum(d['off_stock'][o][w] for w in ws)
        ex.append(s * 5.0 / 3600.0)
    return {'fwe7_bin_300': ch, 'local19_bin_300': [a + b for a, b in zip(ch, ex)],
            'fwe7_bin_total': sum(ch), 'local19_bin_total': sum(ch) + sum(ex)}


def physics(FA, TL, d, Z5, Z7):
    G = cong_grid(FA, d)
    return {'tag': d['tag'], 'fzp': d['fzp'], 'fzp_sha256': d['fzp_sha256'], 'zones5': zone_windows(d, Z5), 'zones7': zone_windows(d, Z7),
            'cong_min5': zone_cong_minutes(G, Z5, d['nb']), 'spill': spill(TL, d), 'ramps': ramps(d), 'offramps': offramps(d),
            'bins': bin_sums(d), 'ins74_300': [sum(d['ins'][w] for w in range(5 * k, 5 * k + 5)) * 12.0 for k in range(NW300)]}


def sub(a, b):
    if a is None or b is None:
        return None
    return a - b


def dphys(A, B):
    out = {'zones5': {}, 'zones7': {}, 'ramps': {}, 'offramps': {}}
    for zk in ('zones5', 'zones7'):
        for z in A[zk]:
            x, y = A[zk][z], B[zk][z]
            out[zk][z] = {'d_veh_h_300': [p - q for p, q in zip(x['veh_h_300'], y['veh_h_300'])],
                          'd_speed_300': [sub(p, q) for p, q in zip(x['speed_300'], y['speed_300'])],
                          'd_veh_h_total': x['veh_h_total'] - y['veh_h_total'], 'd_speed_total': sub(x['speed_total'], y['speed_total'])}
    out['cong_min5'] = {z: A['cong_min5'][z] - B['cong_min5'][z] for z in A['cong_min5']}
    out['spill'] = {k: A['spill'][k] - B['spill'][k] for k in ('b1_spill_min_lt4500', 'm_spill_min_lt6800')}
    for r in RAMPS:
        x, y = A['ramps'][r], B['ramps'][r]
        out['ramps'][r] = {k + '_d': [p - q for p, q in zip(x[k], y[k])] for k in ('merge_vph_300', 'stock_veh_h_300', 'queued_veh_h_300', 'qmax_300')}
        out['ramps'][r]['merge_veh_900_8100_d'] = x['merge_veh_900_8100'] - y['merge_veh_900_8100']
        out['ramps'][r]['stock_veh_h_total_d'] = x['stock_veh_h_total'] - y['stock_veh_h_total']
        out['ramps'][r]['queued_veh_h_total_d'] = x['queued_veh_h_total'] - y['queued_veh_h_total']
    for o in EXIT_SIDE:
        x, y = A['offramps'][o], B['offramps'][o]
        out['offramps'][o] = {k + '_d': [p - q for p, q in zip(x[k], y[k])] for k in ('stock_veh_h_300', 'queued_veh_h_300')}
    out['bins'] = {'fwe7_d_300': [p - q for p, q in zip(A['bins']['fwe7_bin_300'], B['bins']['fwe7_bin_300'])],
                   'local19_d_300': [p - q for p, q in zip(A['bins']['local19_bin_300'], B['bins']['local19_bin_300'])]}
    out['S14_pre900_abs_local19'] = sum(abs(v) for v in out['bins']['local19_d_300'][:3])
    out['ins74_d_300'] = [p - q for p, q in zip(A['ins74_300'], B['ins74_300'])]
    return out


# ---------------------------------------------------------------- meters (LDP, GREEN = state 'I'; rm_exec.py:14-23 rule)
RX = re.compile(r'^\s*(\d+\.\d)\s+(\d+\.\d)(.*)$')


def ldp_states(path):
    g = {}
    with open(path, 'rb') as f:
        for raw in f:
            s = raw.decode('latin-1').rstrip('\r\n')
            m = RX.match(s)
            if m:
                g[float(m.group(1))] = m.group(3)[:1]
    return g


def green_cycles(g, t0=CYC0, t1=WEND):
    cyc = []
    c = t0
    while c < t1:
        cyc.append((int(c), sum(1 for k in range(10) if g.get(c + k + 1.0) == 'I')))
        c += 10
    return cyc


def meter_summary(cyc, cmds=None):
    tight10 = [c for c, n in cyc if n < 10]
    tight6 = [c for c, n in cyc if n <= 6]
    hist = {str(i): sum(1 for _, n in cyc if n == i) for i in range(11)}
    share = []
    for k in range(NW300):
        a = 300 * k
        cs = [n for c, n in cyc if a <= c < a + 300]
        share.append((sum(1 for n in cs if n < 10) / 30.0) if cs else None)
    out = {'n_cycles': len(cyc), 'n_tight10': len(tight10), 'n_tight6': len(tight6), 'T_tight10': tight10[0] if tight10 else None,
           'T_tight6': tight6[0] if tight6 else None, 'green_hist': hist, 'tight10_share_300': share,
           'green_sum_s': sum(n for _, n in cyc)}
    if cmds is not None:
        rows = []
        for T in sorted(cmds):
            if T < CYC0 or T >= WEND:
                continue
            cs = [n for c, n in cyc if T <= c < T + 150]
            mean = sum(cs) / len(cs) if cs else None
            rows.append((T, cmds[T], mean))
        mism = [r for r in rows if r[2] is None or abs(r[2] - r[1]) > 0.5]
        out['cmd'] = {'intervals': len(rows), 'cmd_lt10': sum(1 for r in rows if r[1] < 10), 'mismatch_gt0p5': len(mism),
                      'mismatch_examples': [(T, c, (round(m, 2) if m is not None else None)) for T, c, m in mism[:5]],
                      'cmd_min': min((r[1] for r in rows), default=None), 'cmd_mean': (sum(r[1] for r in rows) / len(rows)) if rows else None}
    return out


def load_cmds_greens(cond):
    out = {}
    for r in csv.DictReader(open(H + '/derived/decision_greens.csv', encoding='utf-8-sig')):
        if r['condition'] == cond and r['kind'] == 'ramp_meter':
            out.setdefault(r['id'], {})[float(r['sim_sec'])] = float(r['green_sec'])
    return out


def load_cmds_action(path):
    out = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        if r['kind'] == 'ramp_meter':
            out.setdefault(r['id'], {})[float(r['sim_sec'])] = float(r['green_sec'])
    return out


# ---------------------------------------------------------------- main
def main():
    t_start = time.time()
    extra = dict(a.split('=', 1) for a in sys.argv[1:])
    R = {'schema': 'fwe-r4/v1', 'made_kst': time.strftime('%Y-%m-%d %H:%M:%S'), 'tool': os.path.abspath(__file__),
         'tool_sha256': sha(os.path.abspath(__file__)), 'pre_fwe_sha256': sha(FD + '/PRE_FWE.md'), 'inputs': {}, 'checks': {},
         'stops': [], 'not_produced': []}
    # pins
    bad = {}
    for p, s in PIN.items():
        g = sha(p)
        R['inputs'][p] = g
        if g != s:
            bad[p] = g
    R['checks']['pins_ok'] = not bad
    if bad:
        R['stops'].append({'rule': 'pin', 'bad': bad})
        json.dump(R, open(FD + '/out/R4_codex.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        raise SystemExit('pinned input changed: %s' % bad)
    sys.path.insert(0, SP + '/rmcause/phys'); sys.path.insert(0, SP + '/rmcause/o1o4/work')
    import fwe_analyze as FA
    import tails as TL
    Z5 = [(k.split('_')[0], float(a), float(e)) for k, (a, e) in FA.ZONES.items()]
    Z7 = zones7()
    R['zones5'] = Z5; R['zones7'] = Z7
    # extra heavy outputs (R3 turn H4/H5)
    first = dict(FIRST); scan = dict(SCAN); lbin = dict(LINKBIN)
    heavy = {}
    for key, store, run in (('first_fw', first, 'freeway_only'), ('first_urb', first, 'urban_only'), ('scan_urb', scan, 'urban_only'),
                            ('lb_urb', lbin, 'urban_only'), ('lb_fw', lbin, 'freeway_only')):
        p = extra.get(key)
        if not p or not os.path.exists(p):
            heavy[key] = {'path': p, 'used': False, 'why': 'not given or missing'}
            continue
        d = jl(p)
        fz = d.get('fzp_sha256') or extra.get(key + '_sha')
        ok = fz == FZP_SHA[run]
        heavy[key] = {'path': p, 'file_sha256': sha(p), 'fzp_sha256': fz, 'expect': FZP_SHA[run], 'S1_ok': ok, 'used': ok,
                      'fzp_sha_source': 'inside file' if d.get('fzp_sha256') else 'producing job record (given)'}
        if ok:
            store[run] = p
            R['inputs'][p] = heavy[key]['file_sha256']
        else:
            R['stops'].append({'rule': 'S-1', 'key': key})
    R['heavy_inputs'] = heavy
    # ---- S-2 provenance seeds, network sha (inventory) and 895.1 s prefix
    inv = {r['arm']: r for r in jl(FD + '/out/inventory.json')['runs']}
    s2 = {}
    for run, arm in INV_ARM.items():
        r = inv[arm]
        pp = r['provenance']['path']
        pr = jl(pp)
        s2[run] = {'provenance': pp, 'provenance_sha256': sha(pp), 'inv_provenance_sha256': r['provenance']['sha256'], 'seed': pr.get('seed'),
                   'inpx_sha256': (r['inpx'] or {}).get('sha256') if isinstance(r.get('inpx'), dict) else None,
                   'fzp_sha_cached': r['fzp_sha256_cached']}
        s2[run]['ok'] = (s2[run]['seed'] == 29 and s2[run]['provenance_sha256'] == s2[run]['inv_provenance_sha256']
                         and (s2[run]['inpx_sha256'] is None or s2[run]['inpx_sha256'].startswith('64cf5f55'))
                         and FZP_SHA[run] in r['fzp_sha256_cached'])
    R['checks']['S2'] = s2
    if not all(v['ok'] for v in s2.values()):
        R['stops'].append({'rule': 'S-2', 'bad': [k for k, v in s2.items() if not v['ok']]})
    # ---- link integrals (codex_8100)
    mem = jl(H + '/derived/omega_membership_exact.json'); part = jl(H + '/derived/reporting_partition.json')
    S = link_sets(mem, part)
    R['link_set_sizes'] = {k: len(v) for k, v in S.items()}
    V = {}
    prefix = {}
    for run, tag in VHR_TAG.items():
        d = jl(CW + '/vhr/scan_out/%s.json' % tag)
        if d['file_sha256'] != FZP_SHA[run]:
            R['stops'].append({'rule': 'S-1', 'vhr': tag})
        V[run] = d['integrals']['codex_8100']
        prefix[run] = d['lf_sha_le_895_1']
    R['checks']['prefix_895_1_equal'] = {'values': prefix, 'all_equal': len(set(prefix.values())) == 1}
    L = {run: levels(I, S) for run, I in V.items()}
    R['levels_codex_8100'] = L
    # ---- S-5: codex tables and NC vs LNC
    ref = {}
    for row in csv.DictReader(open(H + '/derived/metrics_0_8100.csv', encoding='utf-8-sig')):
        ref[(row['condition'], row['metric'])] = float(row['veh_h'])
    ifc = jl(H + '/derived/independent_fzp_counts.json')
    s5 = {}
    for run in ['nc', 'joint', 'freeway_only', 'urban_only']:
        s5[run] = {'Omega701': L[run]['O701'] - ref[(run, 'Omega701')], 'FW_E_7': L[run]['FWE7'] - ref[(run, 'FW_E_7')],
                   'local_19': L[run]['LOCAL19'] - ref[(run, 'local_19')]}
        s5[run]['urban_roads (보고만)'] = L[run]['urban'] - ref[(run, 'urban_roads')]
        s5[run]['onramps_E (보고만)'] = L[run]['onramps_E'] - ref[(run, 'onramps_E')]
        s5[run]['offramps (보고만)'] = L[run]['offramps701'] - ref[(run, 'offramps')]
    for run in ['window', 'off']:
        s5[run] = {'Omega701': L[run]['O701'] - ifc[run]['Omega701'], 'FW_E_7': L[run]['FWE7'] - ifc[run]['FW_E_7'],
                   'local_19': L[run]['LOCAL19'] - ifc[run]['local_19']}
    keys = set(V['nc']) | set(V['lnc'])
    nc_lnc = max(abs(V['nc'].get(l, 0.0) - V['lnc'].get(l, 0.0)) for l in keys)
    s5_ok = all(abs(v) <= 0.01 for run in s5 for k, v in s5[run].items() if '보고만' not in k) and nc_lnc <= 1e-6
    R['checks']['S5'] = {'level_diffs': s5, 'nc_vs_lnc_link_max_abs': nc_lnc, 'ok': s5_ok}
    if not s5_ok:
        R['stops'].append({'rule': 'S-5'})
    # FW_W chain check against codex summary (report only)
    summ = jl(H + '/analysis/comparison/summary.json')['reporting_partition']['parts']
    R['inputs'][H + '/analysis/comparison/summary.json'] = sha(H + '/analysis/comparison/summary.json')
    R['checks']['fww3_vs_codex_summary'] = {run: L[run]['FWW3'] - summ[run]['FW_W'] for run in ['nc', 'joint', 'freeway_only', 'urban_only'] if run in summ}
    # ---- first-seen
    F = {}
    for run in ['nc', 'joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1', 'lnc', 'vsl']:
        if run in first:
            F[run] = jl(first[run])
    R['checks']['first74_le_8100'] = {run: S_int(f, WEND, {'74'})[1] for run, f in F.items()}
    R['checks']['first_lnc_eq_nc'] = ({c: dict(v) for c, v in F['lnc']['by_cat'].items()} == {c: dict(v) for c, v in F['nc']['by_cat'].items()}) if 'lnc' in F else None
    # ---- R4-a
    R4a = {}
    for arm in ARMS:
        x, y = L[arm], L['nc']
        d = {k: x[k] - y[k] for k in ('FWE7', 'LOCAL19', 'urban', 'O701', 'A4a', 'link66', 'FWW3', 'onramps_E', 'onramps_W', 'offramps701')}
        if arm in F:
            d['U'] = dU(F[arm], F['nc'], WEND)
            d['u1098'] = dU(F[arm], F['nc'], WEND, {'74'}); d['u1099'] = dU(F[arm], F['nc'], WEND, {'26'}); d['ucity'] = dU(F[arm], F['nc'], WEND, {'other'})
            d['A4'] = d['A4a'] + d['U']; d['outa701'] = d['A4'] - d['O701']
        else:
            d['U'] = d['u1098'] = d['u1099'] = d['ucity'] = d['A4'] = d['outa701'] = None
            R['not_produced'].append('R4-a %s: ④b·④·Ω 밖 (a) (첫 관측 없음)' % arm)
        d['outb701'] = d['A4a'] - d['O701']
        d['levels_arm'] = x
        R4a[PAIR_NAME[arm]] = d
    R4a['_nc_levels'] = L['nc']
    R['R4a'] = R4a
    # known-value check (HANDOFF_RESULTS r2 §1.1 joint - NC): first-seen -221.3 / +97.0 / -69.2 / -249.0
    R['checks']['joint_known'] = {k: R4a['Q-joint'][k] for k in ('U', 'u1098', 'u1099', 'ucity', 'O701', 'A4', 'outa701', 'outb701', 'FWE7', 'LOCAL19', 'urban')}
    # ---- R4-b physics
    P = {}
    for run, p in scan.items():
        d = jl(p)
        if d['fzp_sha256'] != FZP_SHA[run]:
            R['stops'].append({'rule': 'S-1', 'scan': p}); continue
        P[run] = physics(FA, TL, d, Z5, Z7)
        if run == 'lnc':
            P[run]['spill_full_0_9000'] = spill_full(TL, d)
    R['physics_levels'] = P
    R4b = {}
    for arm in ARMS:
        if arm in P:
            R4b[PAIR_NAME[arm]] = dphys(P[arm], P['lnc'])
        else:
            R['not_produced'].append('R4-b %s: fwe_scan 없음' % arm)
    R['R4b'] = R4b
    # S-4 (b) / S-8: codex-form totals vs bin-form sums (veh.h)
    s4 = {}
    for run in P:
        lv = L.get(run) if run in L else None
        if run == 'lnc':
            lv = L['lnc']
        if lv is None:
            continue
        s4[run] = {'FWE7_codex_minus_bin': lv['FWE7'] - P[run]['bins']['fwe7_bin_total'],
                   'LOCAL19_codex_minus_bin': lv['LOCAL19'] - P[run]['bins']['local19_bin_total']}
    R['checks']['S4b'] = {'diffs': s4, 'ok': all(abs(v) <= 1.0 for r in s4.values() for v in r.values())}
    if not R['checks']['S4b']['ok']:
        R['stops'].append({'rule': 'S-4(b)'})
    # linkbin cross-check of ramp stock / queue (300 s, vehicle-frames) and ① bin sums
    xc = {}
    for run, p in lbin.items():
        lb = jl(p)
        if lb['fzp_sha256'] != FZP_SHA[run] or run not in P:
            continue
        d = jl(scan[run])
        mx = 0; mxq = 0; mx1 = 0
        for k in range(NW300):
            for r in RAMPS:
                a = sum(d['conn_stock'][r][w] + d['from_stock'][r][w] for w in range(5 * k, 5 * k + 5))
                b = sum(lb['vf'].get(l, [0] * 60)[2 * k] + lb['vf'].get(l, [0] * 60)[2 * k + 1] for l in (r, RAMP_FROM[r]))
                qa = sum(d['conn_q'][r][w] + d['from_q'][r][w] for w in range(5 * k, 5 * k + 5))
                qb = sum(lb['qf'].get(l, [0] * 60)[2 * k] + lb['qf'].get(l, [0] * 60)[2 * k + 1] for l in (r, RAMP_FROM[r]))
                mx = max(mx, abs(a - b)); mxq = max(mxq, abs(qa - qb))
            c1 = sum(sum(d['gN'][w]) for w in range(5 * k, 5 * k + 5))
            c2 = sum(lb['vf'].get(l, [0] * 60)[2 * k] + lb['vf'].get(l, [0] * 60)[2 * k + 1] for l in FWE7)
            mx1 = max(mx1, abs(c1 - c2))
        xc[run] = {'ramp_stock_max_abs_vf': mx, 'ramp_queue_max_abs_vf': mxq, 'fwe7_max_abs_vf': mx1}
    R['checks']['linkbin_xcheck'] = xc
    # ---- R4-c meters
    cmdsrc = {run: load_cmds_greens(run) for run in ['nc', 'joint', 'window', 'off', 'freeway_only', 'urban_only']}
    cmdsrc['a1'] = load_cmds_action(A1_ACTION)
    R['inputs'][A1_ACTION] = sha(A1_ACTION)
    M = {}
    for run, pat in LDP.items():
        M[run] = {}
        for sc, mid in METERS.items():
            p = pat.format(sc=sc)
            g = ldp_states(p)
            cyc = green_cycles(g)
            cm = cmdsrc.get(run, {}).get(mid)
            M[run][mid] = meter_summary(cyc, cm)
            M[run][mid]['ldp'] = p; M[run][mid]['ldp_sha256'] = sha(p)
            M[run][mid]['cycles'] = cyc
            M[run][mid]['states_seen'] = sorted(set(g.values()))
    R['meters'] = M
    R['checks']['nc_ldp_eq_lnc_ldp'] = {mid: M['nc'][mid]['cycles'] == M['lnc'][mid]['cycles'] for mid in METERS.values()}
    # ---- R4-d A1 - joint (physics, meters computed; totals read from A1_RESULT r2)
    R4d = {'physics': dphys(P['a1'], P['joint']) if 'a1' in P and 'joint' in P else None,
           'U_first_seen': dU(F['a1'], F['joint'], WEND), 'u1098': dU(F['a1'], F['joint'], WEND, {'74'}),
           'u1099': dU(F['a1'], F['joint'], WEND, {'26'}), 'ucity': dU(F['a1'], F['joint'], WEND, {'other'})}
    R4d['A1_minus_LNC_U_first_seen'] = dU(F['a1'], F['lnc'], WEND)
    R4d['physics_A1_minus_LNC'] = dphys(P['a1'], P['lnc'])
    R['R4d'] = R4d
    # ---- Q-VSL64 (bin form from linkbin, [0, 8100) = bins 0..53)
    lbn, lbv = jl(LINKBIN['lnc']), jl(LINKBIN['vsl'])

    def lbsum(lb, s):
        return sum(sum(v[:54]) for l, v in lb['vf'].items() if l in s) * 5.0 / 3600.0

    def lball(lb):
        return sum(sum(v[:54]) for v in lb['vf'].values()) * 5.0 / 3600.0
    qv = {}
    for k in ('FWE7', 'LOCAL19', 'urban', 'O701', 'FWW3'):
        qv[k] = lbsum(lbv, S[k]) - lbsum(lbn, S[k])
    qv['A4a'] = lball(lbv) - lball(lbn)
    qv['link66'] = lbsum(lbv, {'66'}) - lbsum(lbn, {'66'})
    qv['U'] = dU(F['vsl'], F['lnc'], WEND); qv['u1098'] = dU(F['vsl'], F['lnc'], WEND, {'74'})
    qv['u1099'] = dU(F['vsl'], F['lnc'], WEND, {'26'}); qv['ucity'] = dU(F['vsl'], F['lnc'], WEND, {'other'})
    qv['A4'] = qv['A4a'] + qv['U']; qv['outa701'] = qv['A4'] - qv['O701']; qv['outb701'] = qv['A4a'] - qv['O701']
    qv['form'] = 'bin 꼴 (linkbin, t>=1.0, 150 s 칸 0..53, 사각형) + 첫 관측 차분'
    qv['physics'] = dphys(P['vsl'], P['lnc'])
    R['QVSL64'] = qv
    R['Qhist'] = 'not produced (선택 H13–H16 안 돌림)'
    R['seconds'] = round(time.time() - t_start, 1)
    out = FD + '/out/R4_codex.json'
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(R, g, ensure_ascii=False, indent=1)
    os.replace(out + '.tmp', out)
    print('R4 done', R['seconds'], 'stops', R['stops'], 'not_produced', R['not_produced'])


if __name__ == '__main__':
    main()
