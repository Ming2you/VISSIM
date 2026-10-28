# -*- coding: utf-8 -*-
"""fwe_r2.py - D-K9-106 R2 (PRE_FWE.md r1 c7cc0e6c §5.2, §7, §10): where and when the FW_E differences come from.

Usage: python -B fwe_r2.py [<out_json>]      (default FD/out/R2_pairs.json)
Reads only caches (vhr link integrals, first-seen, omega npz, linkbin json, fwe_scan json) and the definition files.
Never opens an FZP. Writes only <out_json>.

Cells computed (PRE §5.2): R2-a totals (d1, d2 in our form [0,9000] and codex form [0,8100]; Omega701, 4a, 4b, 4,
outside (a)(b) on the same row), R2-b link x 300 s (bin form), R2-c zone x 300 s (5 main + 7 aux zones; d veh*h,
d mean speed), R2-d cell x 900 s (31 cells), R2-e entry / exit side links, R2-f time shape (T_gain_a, T_gain_b, T_half).
Checks: S-2 (seed, network), S-3 (npz->bin vs linkbin on LNC), S-4 (a)(b), S-5 part (codex NC vs LNC), S-8, S-14,
reproduction of the PRE §4 / B_RESULTS / HANDOFF_RESULTS known values.
Seeds are never averaged; 64cf and v3c3 are never subtracted from each other.
"""
import glob
import hashlib
import importlib.util
import json
import os
import sys
import time

import numpy as np

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
CW = SP + '/codex_handoff/work'
FD = SP + '/fwe_decomp'
HD = 'D:/VISSIM_handoff/20261024'
PRE = FD + '/PRE_FWE.md'
PRE_SHA = 'c7cc0e6cc629da156b3ada7278af0fd95a0be4bf80d86ac6532b09e21656ce94'
INV = FD + '/out/inventory.json'
INV_SHA = 'f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6'
PIN = {   # existing files used here (sha256 = FD/out/pins_existing.json / inventory)
    SP + '/rmcause/phys/fwe_analyze.py': '5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf',
    CW + '/omega/omega701_recount.py': '5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac',
    HD + '/derived/omega_membership_exact.json': 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473',
    SP + '/vsl_v3c3/out/cell/nc3_s31.json': '6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53',
}
S7 = ['74', '10699', '2', '10613', '119', '10702', '24']
ENTRY = ['10639', '10681', '10490', '10484', '70', '68', '129', '31']
EXIT = ['10643', '10682', '10481', '10483']
S19 = S7 + ENTRY + EXIT
GROUPS = {'S7': S7, 'S19': S19, 'ENTRY': ENTRY, 'EXIT': EXIT}
ZONES7 = [('U', 0, 4200), ('B1', 4200, 5300), ('M1', 5300, 6300), ('Mu', 6300, 6700), ('VS0', 6700, 6800),
          ('B2', 6800, 8100), ('D', 8100, 10800)]          # = vsl_metrics.py:56
FRAME_S = 5.0
VH = FRAME_S / 3600.0
BIN150 = 150.0
NETS = {'v3c3': {'t_end': 9000.0, 'nw300': 30, 'nb150': 60, 'forms': [('ours_9000', 9000.0), ('codex_8100', 8100.0)]},
        '64cf': {'t_end': 8100.0, 'nw300': 27, 'nb150': 54, 'forms': [('codex_8100', 8100.0)]}}
ALLOWED_INPX = {'v3c3': {'3de889f0257d998b', '726af589bddb8c72', '51478c397b3a2570', '046303541667838f',
                         'e4953eaf8c8f983f', '94318d4d1c235fa8'},
                '64cf': {'64cf5f55fe9990f3', None}}   # PRE §3.1 (codex NC / LNC / vsl_repro: inpx not recorded)
HEAVY_DIRS = [FD + '/out/heavy', FD + '/out/heavy_r2']


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 22), b''):
            h.update(ch)
    return h.hexdigest()


def load_mod(path, name):
    want = PIN.get(path)
    if want is not None and sha(path) != want:
        raise SystemExit('pinned file changed: %s' % path)
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(m)
    return m


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------------------------------------ runs
def _run(arm_inv, net, seed, **kw):
    d = dict(arm_inv=arm_inv, net=net, seed=seed)
    d.update(kw)
    return d


RUNS = {}
for _s in (31, 41, 43):
    RUNS['nc3_s%d' % _s] = _run('NC3', 'v3c3', _s, label='NC3',
                                vhr=CW + '/vhr/scan_out/nc3_s%d.json' % _s, first=CW + '/vhr/scan_out/first_nc3_s%d.json' % _s,
                                bins=('npz', CW + '/omega/cache/nc3_s%d.npz' % _s), fwe=SP + '/rmcause/phys/scan/nc_s%d.json' % _s)
    RUNS['va_s%d' % _s] = _run('V-A', 'v3c3', _s, label='V-A',
                               vhr=CW + '/vhr/scan_out/va_s%d.json' % _s, first=CW + '/vhr/scan_out/first_va_s%d.json' % _s,
                               bins=('npz', CW + '/omega/cache/va_s%d.npz' % _s), fwe=SP + '/rmcause/phys/scan/va_s%d.json' % _s)
    RUNS['b_s%d' % _s] = _run('B', 'v3c3', _s, label='B',
                              vhr=CW + '/vhr_b/scan_out/j1_s%d.json' % _s, first=CW + '/vhr_b/scan_out/first_j1_s%d.json' % _s,
                              bins=('npz', CW + '/omega_b/cache/j1_s%d.npz' % _s), fwe=('find', 'fwe_scan'))
    RUNS['vsl_s%d' % _s] = _run('VSL', 'v3c3', _s, label='VSL',
                                vhr=SP + '/vsl_v3c3/out/vhr/vsl_s%d.json' % _s, first=SP + '/vsl_v3c3/out/vhr/first_vsl_s%d.json' % _s,
                                bins=('lb', FD + '/out/heavy_r2/lb_vsl_s%d.json' % _s), fwe=SP + '/vsl_v3c3/out/phys/vsl_s%d.json' % _s)
    RUNS['j1_s%d' % _s] = _run('J1(참고)', 'v3c3', _s, label='J1',
                               vhr=CW + '/vhr/scan_out/j1_s%d.json' % _s, first=CW + '/vhr/scan_out/first_j1_s%d.json' % _s,
                               bins=('npz', CW + '/omega/cache/j1_s%d.npz' % _s), fwe=SP + '/rmcause/phys/scan/j1_s%d.json' % _s)
# 64cf-s29: codex NC totals + first-seen from the codex NC FZP; link bins + fwe_scan from LNC (same simulation, PRE §3.1)
RUNS['nc64'] = _run('codex NC', '64cf', 29, label='codex NC', vhr=CW + '/vhr/scan_out/nc_raw.json',
                    first=CW + '/vhr/scan_out/first_nc_raw.json', bins=('npz', CW + '/omega/cache/lnc_64cf_s29.npz'),
                    fwe=SP + '/rmcause/phys/scan/cf_s29_none.json', arm_inv_bins='LNC')
RUNS['lnc'] = _run('LNC', '64cf', 29, label='LNC', vhr=CW + '/vhr/scan_out/lnc.json',
                   first=CW + '/a1/full/firstseen/first_lnc.json', bins=('npz', CW + '/omega/cache/lnc_64cf_s29.npz'),
                   fwe=SP + '/rmcause/phys/scan/cf_s29_none.json')
for _k, _a, _n in (('cx_joint', 'codex joint', 'joint'), ('cx_window', 'codex window', 'window'), ('cx_off', 'codex off', 'off')):
    RUNS[_k] = _run(_a, '64cf', 29, label=_a, vhr=CW + '/vhr/scan_out/%s.json' % _n, first=CW + '/vhr/scan_out/first_%s.json' % _n,
                    bins=('lb', FD + '/out/heavy_r2/lb_%s_s29.json' % _k), fwe=SP + '/c_port/vsl/out/scan/%s_s29.json' % _k)
RUNS['cx_fw'] = _run('codex freeway_only', '64cf', 29, label='codex freeway_only', vhr=CW + '/vhr/scan_out/freeway_only.json',
                     first=('find', 'first'), bins=('find', 'linkbin'), fwe=SP + '/c_port/vsl/out/scan/cx_fwonly_s29.json')
RUNS['cx_urb'] = _run('codex urban_only', '64cf', 29, label='codex urban_only', vhr=CW + '/vhr/scan_out/urban_only.json',
                      first=('find', 'first'), bins=('find', 'linkbin'), fwe=('find', 'fwe_scan'))
RUNS['a1'] = _run('A1', '64cf', 29, label='A1', vhr=None, first=CW + '/a1/full/firstseen/first_a1.json',
                  bins=('lb', FD + '/out/heavy_r2/lb_a1_s29.json'), fwe=SP + '/c_port/vsl/out/scan/a1_s29.json')
RUNS['vslr'] = _run('vsl_repro vsl', '64cf', 29, label='vsl_repro vsl', vhr=None, first=SP + '/c_port/vsl/out/first_vsl.json',
                    bins=('lb', SP + '/rmcause/o1o4/scan/lb_vsl_s29.json'), fwe=SP + '/rmcause/o1o4/scan/vsl_s29.json')

PAIRS = []
for _s in (31, 41, 43):
    PAIRS += [dict(id='P-VA', x='va_s%d' % _s, y='nc3_s%d' % _s, net='v3c3', seed=_s, parts='all', role='주'),
              dict(id='P-B', x='b_s%d' % _s, y='nc3_s%d' % _s, net='v3c3', seed=_s, parts='all', role='주'),
              dict(id='P-VSL', x='vsl_s%d' % _s, y='nc3_s%d' % _s, net='v3c3', seed=_s, parts='all', role='주(VSL 단서)'),
              dict(id='P-BVA', x='b_s%d' % _s, y='va_s%d' % _s, net='v3c3', seed=_s, parts='totals_zones', role='주(총합·구역만)'),
              dict(id='P-J1', x='j1_s%d' % _s, y='nc3_s%d' % _s, net='v3c3', seed=_s, parts='all', role='참고')]
for _id, _x in (('Q-joint', 'cx_joint'), ('Q-window', 'cx_window'), ('Q-off', 'cx_off'), ('Q-fw', 'cx_fw'), ('Q-urb', 'cx_urb')):
    PAIRS.append(dict(id=_id, x=_x, y='nc64', net='64cf', seed=29, parts='all', role='64cf 주'))
PAIRS += [dict(id='Q-A1', x='a1', y='lnc', net='64cf', seed=29, parts='all', role='참고(흔들림 잣대)', totals='read'),
          dict(id='Q-A1j', x='a1', y='cx_joint', net='64cf', seed=29, parts='all', role='참고(흔들림 잣대 A1 − joint)', totals='read'),
          dict(id='Q-VSL64', x='vslr', y='lnc', net='64cf', seed=29, parts='all', role='참고(bin 꼴)', totals='bin')]

# A1 totals: read, not recounted (PRE §5.4 source line). A1_RESULT.md:255-267, codex form 0-8100.
A1_READ = {'Q-A1': {'O701': -505.7, 'A4a': -464.1, 'U': -235.1, 'A4': -699.2, 'outa': -193.5, 'outb': 41.6, 'S7': -251.1, 'S19': -181.8},
           'Q-A1j': {'O701': -11.0, 'A4a': -15.1, 'U': -13.8, 'A4': -28.9, 'outa': -17.9, 'outb': -4.1, 'S7': 32.5, 'S19': -25.3}}
A1_READ_SRC = 'SP/codex_handoff/a1/A1_RESULT.md:255-267'

# Known values (read before data): PRE_FWE §4 (+ B_RESULTS.md:65-79, :92-100, HANDOFF_RESULTS.md:77-89). Seeds 31/41/43.
KNOWN = [
    ('PRE §4.1 / B_RESULTS:65-79', 'P-VA', 'ours_9000', {'O701': (-240.6, -421.7, -309.5), 'A4': (-373.9, -506.2, -356.4),
                                                           'outa': (-133.3, -84.5, -46.9), 'S7': (-12.3, -72.6, -5.3), 'S19': (-51.5, -187.1, -92.5)}),
    ('PRE §4.1 / B_RESULTS:65-79', 'P-B', 'ours_9000', {'O701': (-157.0, -523.4, -222.2), 'A4': (175.1, -230.6, -450.6),
                                                          'outa': (332.1, 292.9, -228.4), 'S7': (-37.3, -178.1, -88.9), 'S19': (28.2, -245.2, -34.7)}),
    ('PRE §4.1 / VSL_RESULTS:63-72', 'P-VSL', 'ours_9000', {'O701': (70.3, -162.0, -50.5), 'A4': (10.6, 68.6, -109.9),
                                                              'outa': (-59.8, 230.6, -59.4), 'S7': (36.1, -126.1, -8.0), 'S19': (67.8, -184.0, -45.3)}),
    ('B_RESULTS:65-79', 'P-BVA', 'ours_9000', {'O701': (83.6, -101.8, 87.3), 'A4': (549.1, 275.6, -94.3), 'outa': (465.5, 377.3, -181.6),
                                                 'S7': (-25.0, -105.5, -83.7), 'S19': (79.8, -58.1, 57.8)}),
    ('HANDOFF_RESULTS:77-89', 'P-VA', 'codex_8100', {'O701': (-207.7, -391.3, -286.7), 'A4': (-279.4, -474.3, -340.4),
                                                      'outa': (-71.7, -83.0, -53.7), 'S7': (-21.5, -66.7, -6.9), 'S19': (-59.5, -169.4, -92.1)}),
    ('HANDOFF_RESULTS:77-89', 'P-J1', 'codex_8100', {'O701': (333.5, -444.0, 144.4), 'A4': (113.0, -491.6, 104.7),
                                                      'outa': (-220.5, -47.6, -39.7), 'S7': (12.6, -160.1, -54.8), 'S19': (-19.0, -278.0, -130.9)}),
    ('B_RESULTS:92-100', 'P-B', 'codex_8100', {'O701': (-126.9, -464.0, -195.4), 'A4': (129.1, -258.0, -425.5),
                                                'outa': (256.1, 206.1, -230.1), 'S7': (-37.0, -172.5, -89.6)}),
    ('PRE §4.2 / HANDOFF_RESULTS:77-89', 'Q-joint', 'codex_8100', {'O701': (-494.7,), 'A4': (-670.3,), 'outa': (-175.6,),
                                                                     'S7': (-283.7,), 'S19': (-156.6,)}),
    ('PRE §4.2 bullet (HANDOFF_codex:226-233)', 'Q-window', 'codex_8100', {'S7': (-264.6,), 'S19': (-94.2,)}),
    ('PRE §4.2 bullet (HANDOFF_codex:226-233)', 'Q-off', 'codex_8100', {'S7': (-301.5,), 'S19': (-147.6,)}),
    ('PRE §4.2 bullet (HANDOFF_codex:226-233)', 'Q-fw', 'codex_8100', {'S7': (-351.8,), 'S19': (-130.1,)}),
    ('PRE §4.2 bullet (HANDOFF_codex:226-233)', 'Q-urb', 'codex_8100', {'S7': (721.4,), 'S19': (733.7,)}),
]


# ------------------------------------------------------------------------------------------------ source checks
def inv_index(inv):
    fz = {}
    caches = {}
    for r in inv['runs']:
        key = (r['arm'], int(r['provenance']['seed']))
        fz[key] = {'fzp': r['fzp']['path'], 'sha': (r['fzp_sha256_cached'] or [None])[0],
                   'inpx': (r['inpx'] or {}).get('sha256') if isinstance(r.get('inpx'), dict) else r.get('inpx'),
                   'seed_prov': int(r['provenance']['seed'])}
        for c in r['caches']:
            caches[os.path.normcase(os.path.normpath(c['file']))] = (key, c['file_sha256'], c['kind'])
    return fz, caches


R3_JOBS = FD + '/tools/jobs_r3_h1_h5.json'
R3_JOBS_SHA = 'a2a13531dbc7f04c5fd8b2680a1584a4b7db6606f5f193cdc6118504490e4b62'   # PINS_FWE_R3.sha256
R3_LOG = FD + '/logs/heavy/r3_h1_h5.log'


def find_r3_first(fzp_sha):
    """R3 queue (fwe_heavy.py): first-seen output has no sha inside; it is tied to the FZP by the same lock job, which
    logs 'SHA_OK <job>' only when every sha-carrying output of that job matched (else all outputs -> .REJECTED).
    Accept first_<tag>.json when: job spec (pinned) expects this sha and has a firstseen tool <tag>; the log has
    'TOOL_END <job> firstseen <tag> rc=0' and 'SHA_OK <job>' and no 'SHA_MISMATCH <job>'."""
    if not (os.path.exists(R3_JOBS) and os.path.exists(R3_LOG)) or sha(R3_JOBS) != R3_JOBS_SHA:
        return [], None
    spec = jload(R3_JOBS)
    log = open(R3_LOG, encoding='utf-8', errors='replace').read()
    for j in spec['jobs']:
        if j.get('expect_sha256') != fzp_sha:
            continue
        for t in j['tools']:
            if t['tool'] != 'firstseen':
                continue
            p = FD + '/out/heavy/first_%s.json' % t['tag']
            ok = (os.path.exists(p) and ('TOOL_END %s firstseen %s rc=0' % (j['job'], t['tag'])) in log
                  and ('SHA_OK %s ' % j['job']) in log and ('SHA_MISMATCH %s ' % j['job']) not in log)
            tie = {'r3_job': j['job'], 'r3_tag': t['tag'], 'r3_log': R3_LOG, 'r3_log_sha256': sha(R3_LOG),
                   'jobs_spec_sha256': R3_JOBS_SHA, 'rule': 'SHA_OK of the same lock job'}
            if ok:
                return [p], tie
    return [], None


def find_heavy(kind, fzp_sha):
    """R3 / R2 heavy outputs: find a file of this kind whose recorded FZP sha equals fzp_sha."""
    hits = []
    if kind == 'first':
        h, tie = find_r3_first(fzp_sha)
        if h:
            find_heavy.last_tie = tie
            return h
    for d in HEAVY_DIRS:
        for p in sorted(glob.glob(d + '/**/*.json', recursive=True)):
            n = p.replace('\\', '/')
            if '/rejected/' in n or '/_stage/' in n or n.endswith('status.json') or '.meta.' in n:
                continue
            try:
                j = jload(p)
            except (OSError, ValueError):
                continue
            if not isinstance(j, dict):
                continue
            if kind == 'fwe_scan' and 'gN' in j and j.get('fzp_sha256') == fzp_sha:
                hits.append(p)
            elif kind == 'linkbin' and j.get('schema') == 'w264-linkbin/v1' and j.get('fzp_sha256') == fzp_sha:
                hits.append(p)
            elif kind == 'first' and 'by_cat' in j:
                base = os.path.basename(p)[len('first_'):-len('.json')]
                for mp in glob.glob(os.path.join(os.path.dirname(p), '*%s*.meta.json' % base)):
                    try:
                        m = jload(mp)
                    except (OSError, ValueError):
                        continue
                    if m.get('fzp_sha256') == fzp_sha and os.path.normcase(os.path.normpath(m.get('output', p))) == \
                            os.path.normcase(os.path.normpath(p)):
                        hits.append(p)
    return hits


def resolve(run_key, kind, spec, fz, caches, log):
    r = RUNS[run_key]
    arm = r.get('arm_inv_bins', r['arm_inv']) if kind in ('bins', 'fwe') else r['arm_inv']
    exp = fz[(arm, r['seed'])]['sha']
    rec = {'run': run_key, 'kind': kind, 'expect_fzp_sha256': exp, 'inventory_arm': arm}
    if spec is None:
        rec.update(ok=False, why='no source')
        return None, rec
    if isinstance(spec, tuple) and spec[0] == 'find':
        find_heavy.last_tie = None
        hits = find_heavy(spec[1], exp)
        rec['found'] = hits
        if spec[1] == 'first':
            rec['tie'] = find_heavy.last_tie
        if not hits:
            rec.update(ok=False, why='heavy output not found (not yet made or S-1)')
            return None, rec
        path = hits[0]
        btype = 'lb' if spec[1] == 'linkbin' else None
    elif isinstance(spec, tuple):
        btype, path = spec
    else:
        btype, path = None, spec
    rec['path'] = path
    if not os.path.exists(path):
        rec.update(ok=False, why='missing')
        return None, rec
    fsha = sha(path)
    rec['file_sha256'] = fsha
    listed = caches.get(os.path.normcase(os.path.normpath(path)))
    inner = None
    if btype == 'npz':
        meta = path[:-4] + '.json'
        inner = jload(meta).get('fzp_sha256')
        rec['meta'] = meta
    elif path.endswith('.json') and kind != 'first':
        j = jload(path)
        inner = j.get('fzp_sha256') or j.get('file_sha256')
    elif kind == 'first' and isinstance(spec, tuple) and spec[0] == 'find':
        inner = exp     # matched through its meta file in find_heavy
    rec['fzp_sha256_inside'] = inner
    rec['inventory_listed'] = None if listed is None else {'arm_seed': list(listed[0]), 'sha256': listed[1]}
    ok = True
    if listed is not None:
        if listed[1] != fsha or listed[0] != (arm, r['seed']):
            ok = False
            rec['why'] = 'inventory cache sha/run mismatch'
    if inner is not None and inner != exp:
        ok = False
        rec['why'] = 'fzp sha inside != inventory (S-1)'
    if listed is None and inner is None:
        ok = False
        rec['why'] = 'no way to tie the cache to the FZP'
    rec['ok'] = ok
    return (path if ok else None), rec


# ------------------------------------------------------------------------------------------------ calculations
def first_sint(F, W, cats=None, a=0.0):
    """integral over [a, W] of I(t) (first-seen cumulative count) / 3600; = vhr_unins S_int when a = 0."""
    tot = 0.0
    for c, dd in F['by_cat'].items():
        if cats and c not in cats:
            continue
        for tt, k in dd.items():
            t = int(tt) / 10.0
            if t <= W:
                tot += k * (W - max(t, a))
    return tot / 3600.0


def dU(Fx, Fy, W, cats=None):    # U_x - U_y (vhr_unins dU rule)
    return first_sint(Fy, W, cats) - first_sint(Fx, W, cats)


def totals_from_integrals(I, O701):
    t = {g: sum(I.get(l, 0.0) for l in L) for g, L in GROUPS.items()}
    t['O701'] = sum(v for l, v in I.items() if l in O701)
    t['A4a'] = sum(I.values())
    return t


def totals_from_bins(vf, nb, O701):
    t = {g: sum(sum(vf.get(l, [0] * 60)[:nb]) for l in L) * VH for g, L in GROUPS.items()}
    t['O701'] = sum(sum(v[:nb]) for l, v in vf.items() if l in O701) * VH
    t['A4a'] = sum(sum(v[:nb]) for v in vf.values()) * VH
    return t


def r2a(pair, D, O701):
    x, y = pair['x'], pair['y']
    net = NETS[pair['net']]
    out = {}
    if pair.get('totals') == 'read':
        v = A1_READ[pair['id']]
        out['codex_8100'] = dict(v, source='[읽음] ' + A1_READ_SRC)
        return out
    if pair.get('totals') == 'bin':
        nb = 54
        tx = totals_from_bins(D[x]['vf'], nb, O701)
        ty = totals_from_bins(D[y]['vf'], nb, O701)
        d = {k: tx[k] - ty[k] for k in tx}
        d['U'] = dU(D[x]['first'], D[y]['first'], 8100.0)
        d['A4'] = d['A4a'] + d['U']
        d['outa'] = d['A4'] - d['O701']
        d['outb'] = d['A4a'] - d['O701']
        d['source'] = '[실행] bin 꼴 0-8100 (링크 x 150 s 사각형) + 첫 관측 차분'
        out['bin_8100'] = d
        return out
    for form, W in net['forms']:
        tx = totals_from_integrals(D[x]['vhr']['integrals'][form], O701)
        ty = totals_from_integrals(D[y]['vhr']['integrals'][form], O701)
        d = {k: tx[k] - ty[k] for k in tx}
        d['U'] = dU(D[x]['first'], D[y]['first'], W)
        d['A4'] = d['A4a'] + d['U']
        d['outa'] = d['A4'] - d['O701']
        d['outb'] = d['A4a'] - d['O701']
        d['source'] = '[실행] vhr 링크 적분 %s + 첫 관측 차분 [0, %d]' % (form, W)
        out[form] = d
    return out


def link_windows(vf, links, nw300):
    """bin form link x 300 s veh*h: window w = 150 s bins 2w, 2w+1."""
    res = {}
    for l in links:
        a = vf.get(l, [0] * 60)
        res[l] = [(a[2 * w] + a[2 * w + 1]) * VH for w in range(nw300)]
    return res


def zone_bins(nb, zones):
    zb = {}
    for z, a, e in zones:
        zb[z] = [b for b in range(nb) if a <= (b + 0.5) * 100.0 < e]
    return zb


def cell_of(x, cb):
    lo, hi = 0, len(cb) - 2
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if cb[mid] <= x:
            lo = mid
        else:
            hi = mid - 1
    return lo


def fwe_agg(d, groups, w60_per_win, nwin):
    """sum gN and gV of fwe_scan over bin groups and windows of w60_per_win 60 s windows."""
    gN = np.array(d['gN'], dtype=np.float64)
    gV = np.array(d['gV'], dtype=np.float64)
    out = {}
    for g, bs in groups.items():
        n = gN[:, bs].sum(1)
        v = gV[:, bs].sum(1)
        N = [float(n[w * w60_per_win:(w + 1) * w60_per_win].sum()) for w in range(nwin)]
        V = [float(v[w * w60_per_win:(w + 1) * w60_per_win].sum()) for w in range(nwin)]
        out[g] = (N, V)
    return out


def diff_zone(ax, ay):
    res = {}
    for g in ax:
        Nx, Vx = ax[g]
        Ny, Vy = ay[g]
        dvh = [(a - b) * VH for a, b in zip(Nx, Ny)]
        sx = [(V / N if N else None) for N, V in zip(Nx, Vx)]
        sy = [(V / N if N else None) for N, V in zip(Ny, Vy)]
        ds = [(a - b if (a is not None and b is not None) else None) for a, b in zip(sx, sy)]
        res[g] = {'d_veh_h': [round(v, 4) for v in dvh], 'd_speed_kmh': [None if v is None else round(v, 3) for v in ds],
                  'x_veh_h': [round(N * VH, 4) for N in Nx], 'y_veh_h': [round(N * VH, 4) for N in Ny],
                  'x_speed_kmh': [None if v is None else round(v, 3) for v in sx],
                  'y_speed_kmh': [None if v is None else round(v, 3) for v in sy]}
    return res


def time_shape(d1, t0w=3, a_thr=-2.0, b_thr=-5.0):
    """d1 = per 300 s window d(1) veh*h. Cumulative from window t0w (900 s)."""
    n = len(d1)
    cum = []
    c = 0.0
    for w in range(t0w, n):
        c += d1[w]
        cum.append(c)
    ta = next((w * 300 for w in range(t0w, n) if d1[w] <= a_thr), None)
    tb = None
    for i in range(len(cum)):
        if all(v <= b_thr for v in cum[i:]):
            tb = (i + t0w) * 300
            break
    final = cum[-1] if cum else 0.0
    th = None
    if final < 0:
        th = next(((i + t0w) * 300 for i, v in enumerate(cum) if v <= final / 2.0), None)
    return {'cum_from_900': [round(v, 4) for v in cum], 'final_cum_900_end': round(final, 4), 'T_gain_a_s': ta,
            'T_gain_b_s': tb, 'T_half_s': th, 'rule': 'a: first w>=900 s with d1<=-2.0; b: earliest w>=900 s from which '
            'cumulative (from 900 s) stays <=-5.0 to the end; half: first w with cumulative <= final/2 (final<0)'}


# ------------------------------------------------------------------------------------------------ main
def main():
    t_start = time.time()
    out_path = sys.argv[1] if len(sys.argv) > 1 else FD + '/out/R2_pairs.json'
    assert sha(PRE) == PRE_SHA, 'PRE_FWE changed'
    assert sha(INV) == INV_SHA, 'inventory changed'
    for p, s in PIN.items():
        assert sha(p) == s, 'pinned input changed: ' + p
    inv = jload(INV)
    fz, caches = inv_index(inv)
    FA = load_mod(SP + '/rmcause/phys/fwe_analyze.py', 'fwe_analyze')
    OM = load_mod(CW + '/omega/omega701_recount.py', 'omega701_recount')
    NB = load_mod(FD + '/tools/fwe_npz_bins.py', 'fwe_npz_bins')
    ZONES5 = [(k.split('_')[0], a, e) for k, (a, e) in FA.ZONES.items()]
    O701 = set(map(str, jload(HD + '/derived/omega_membership_exact.json')['inside_links']))
    CB = jload(SP + '/vsl_v3c3/out/cell/nc3_s31.json')['cell_bounds_m']
    res = {'tool': os.path.abspath(__file__).replace('\\', '/'), 'tool_sha256': sha(os.path.abspath(__file__)),
           'npz_bins_tool_sha256': sha(FD + '/tools/fwe_npz_bins.py'), 'pre_fwe_sha256': PRE_SHA,
           'made_kst': time.strftime('%Y-%m-%d %H:%M:%S KST'), 'units': 'veh*h; km/h; time = window start s',
           'definitions': {'S7 (①)': S7, 'S19 (②)': S19, 'ENTRY': ENTRY, 'EXIT': EXIT, 'zones5': ZONES5, 'zones7': ZONES7,
                           'cell_bounds_m': CB, 'O701_links': len(O701), 'bin_form': 't>=1.0 s, 150 s bins, vf*5/3600',
                           'windows': {'v3c3': '0-9000 s, 30 x 300 s', '64cf': '0-8100 s, 27 x 300 s'}},
           'sources': {}, 'checks': {}, 'pairs': {}, 'not_done': []}
    # ---- load runs
    D = {}
    needed = set()
    for p in PAIRS:
        needed.add(p['x'])
        needed.add(p['y'])
    for rk in sorted(needed):
        r = RUNS[rk]
        D[rk] = {}
        src = {}
        for kind in ('vhr', 'first', 'bins', 'fwe'):
            path, rec = resolve(rk, kind, r.get(kind), fz, caches, None)
            src[kind] = rec
            if path is None:
                continue
            if kind == 'bins':
                spec = r['bins']
                btype = spec[0] if spec[0] != 'find' else 'lb'
                if btype == 'npz':
                    b = NB.bins_from_npz(path)
                    D[rk]['vf'] = b['vf']
                    D[rk]['bins_frames'] = b['frames']
                    D[rk]['npz'] = path
                else:
                    j = jload(path)
                    D[rk]['vf'] = j['vf']
                    D[rk]['bins_frames'] = j['frames']
                    D[rk]['lb_n_vehicles'] = j.get('n_vehicles')
            else:
                D[rk][kind] = jload(path)
        res['sources'][rk] = src
    # ---- extra tie for first-seen files found through the R3 job log: vehicle count = sha-checked linkbin count
    tie = []
    for rk in sorted(D):
        if isinstance(RUNS[rk].get('first'), tuple) and 'first' in D[rk]:
            nf = D[rk]['first'].get('vehicles')
            nl = D[rk].get('lb_n_vehicles')
            ok = nf is not None and nf == nl
            tie.append({'run': rk, 'first_vehicles': nf, 'linkbin_n_vehicles': nl, 'equal': ok})
            if not ok:
                del D[rk]['first']
                res['sources'][rk]['first']['ok'] = False
                res['sources'][rk]['first']['why'] = 'vehicle count differs from the sha-checked linkbin of the same FZP'
    res['checks']['first_tie_r3'] = {'pass': all(t['equal'] for t in tie), 'rows': tie}
    # ---- S-2 seeds / network
    s2 = []
    for p in PAIRS:
        rx, ry = RUNS[p['x']], RUNS[p['y']]
        items = []
        for rr in (rx, ry):
            for arm in {rr['arm_inv'], rr.get('arm_inv_bins', rr['arm_inv'])}:
                f = fz[(arm, rr['seed'])]
                items.append((arm, f['seed_prov'], (f['inpx'] or None) and f['inpx'][:16]))
        seeds = {i[1] for i in items}
        nets_ok = all(i[2] in ALLOWED_INPX[p['net']] for i in items)
        s2.append({'pair': p['id'], 'seed': p['seed'], 'items': items, 'seed_ok': seeds == {p['seed']}, 'net_ok': nets_ok})
    res['checks']['S2'] = {'pass': all(c['seed_ok'] and c['net_ok'] for c in s2), 'rows': s2}
    # ---- S-3 LNC npz -> bin vs linkbin
    lb_nc = jload(SP + '/rmcause/o1o4/scan/lb_nc_s29.json')
    lnc_b = NB.bins_from_npz(CW + '/omega/cache/lnc_64cf_s29.npz')
    dd = NB.compare_vf(lnc_b['vf'], lb_nc['vf'])
    res['checks']['S3'] = {'pass': (not dd) and lnc_b['frames'] == lb_nc['frames'], 'n_diff_cells': len(dd),
                           'links_compared': len(set(lnc_b['vf']) | set(lb_nc['vf'])), 'first_diffs': dd[:10],
                           'lb_nc_s29_sha256': sha(SP + '/rmcause/o1o4/scan/lb_nc_s29.json')}
    # ---- S-5 part: codex NC vs LNC (link integrals codex_8100, first-seen)
    if 'nc64' in D and 'lnc' in D and 'vhr' in D['nc64'] and 'vhr' in D['lnc']:
        a = D['nc64']['vhr']['integrals']['codex_8100']
        b = D['lnc']['vhr']['integrals']['codex_8100']
        mx = max(abs(a.get(l, 0.0) - b.get(l, 0.0)) for l in set(a) | set(b))
        same_first = D['nc64']['first']['by_cat'] == D['lnc']['first']['by_cat']
        res['checks']['S5_nc_lnc'] = {'max_abs_link_diff_codex_8100': mx, 'first_seen_equal': same_first,
                                      'pass': mx <= 1e-6 and same_first}
    # ---- S-4 (a): npz runs, integrals re-derived from npz frames vs vhr
    s4a = []
    for rk in sorted(D):
        if 'npz' not in D[rk] or 'vhr' not in D[rk]:
            continue
        c = dict(np.load(D[rk]['npz']))
        links = [str(int(l)) for l in c['links'].tolist()]
        row = {'run': rk}
        for form, W, fn in (('ours_9000', 9000.0, OM.integ_ours), ('codex_8100', 8100.0, OM.integ_codex)):
            area, _ = fn(c, W)
            A = dict(zip(links, area.tolist()))
            I = D[rk]['vhr']['integrals'][form]
            for g in ('S7', 'S19'):
                row['%s_%s' % (form, g)] = sum(A.get(l, 0.0) for l in GROUPS[g]) - sum(I.get(l, 0.0) for l in GROUPS[g])
        row['max_abs'] = max(abs(v) for k, v in row.items() if k not in ('run',))
        row['pass'] = row['max_abs'] <= 0.001
        s4a.append(row)
    res['checks']['S4a'] = {'pass': all(r['pass'] for r in s4a), 'rows': s4a}
    # ---- S-4 (b): total (main form) - window sum (bin form) per run
    s4b = []
    for rk in sorted(D):
        r = RUNS[rk]
        if 'vf' not in D[rk] or 'vhr' not in D[rk]:
            continue
        net = NETS[r['net']]
        form = net['forms'][0][0]
        I = D[rk]['vhr']['integrals'][form]
        row = {'run': rk, 'form': form}
        for g in ('S7', 'S19', 'ENTRY', 'EXIT'):
            tot = sum(I.get(l, 0.0) for l in GROUPS[g])
            win = sum(sum(D[rk]['vf'].get(l, [0] * 60)[:net['nb150']]) for l in GROUPS[g]) * VH
            row[g] = {'total': round(tot, 4), 'window_sum': round(win, 4), 'total_minus_windows': round(tot - win, 4)}
        row['pass'] = all(abs(row[g]['total_minus_windows']) <= 1.0 for g in ('S7', 'S19'))
        s4b.append(row)
    res['checks']['S4b'] = {'pass': all(r['pass'] for r in s4b), 'rows': s4b}
    # ---- S-8: fwe_scan zone sum vs bin form (S7), and + ramp/off stocks vs S19
    s8 = []
    for rk in sorted(D):
        if 'fwe' not in D[rk] or 'vf' not in D[rk]:
            continue
        f = D[rk]['fwe']
        nw300 = NETS[RUNS[rk]['net']]['nw300']
        gN = np.array(f['gN'], dtype=np.int64)
        chain = [int(gN[5 * w:5 * w + 5].sum()) for w in range(nw300)]
        side = [0] * nw300
        for key in ('conn_stock', 'from_stock', 'off_stock'):
            for arr in f[key].values():
                for w in range(nw300):
                    side[w] += int(sum(arr[5 * w:5 * w + 5]))
        b7 = [sum(D[rk]['vf'].get(l, [0] * 60)[2 * w] + D[rk]['vf'].get(l, [0] * 60)[2 * w + 1] for l in S7) for w in range(nw300)]
        b19 = [sum(D[rk]['vf'].get(l, [0] * 60)[2 * w] + D[rk]['vf'].get(l, [0] * 60)[2 * w + 1] for l in S19) for w in range(nw300)]
        d7 = [a - b for a, b in zip(chain, b7)]
        d19 = [a + s - b for a, s, b in zip(chain, side, b19)]
        s8.append({'run': rk, 'S7_max_abs_vehframes': max(abs(v) for v in d7), 'S19_max_abs_vehframes': max(abs(v) for v in d19),
                   'S7_sum_vehframes': sum(d7), 'S19_sum_vehframes': sum(d19), 'equal': not any(d7) and not any(d19)})
    res['checks']['S8'] = {'all_equal': all(r['equal'] for r in s8), 'rows': s8, 'action': 'report only'}
    # ---- pairs
    nb108 = 108
    zb5 = zone_bins(nb108, ZONES5)
    zb7 = zone_bins(nb108, ZONES7)
    cells = {}
    for b in range(nb108):
        cells.setdefault(cell_of((b + 0.5) * 100.0, CB), []).append(b)
    cellg = {'c%02d' % i: cells.get(i, []) for i in range(len(CB) - 1)}
    res['definitions']['cell_bins'] = {k: v for k, v in cellg.items()}
    empty_cells = [k for k, v in cellg.items() if not v]
    res['definitions']['cells_without_bin_center'] = empty_cells
    cellg = {k: v for k, v in cellg.items() if v}
    s14 = []
    for p in PAIRS:
        x, y = p['x'], p['y']
        net = NETS[p['net']]
        key = '%s|%s-s%d' % (p['id'], p['net'], p['seed'])
        P = {'pair': p['id'], 'role': p['role'], 'net': p['net'], 'seed': p['seed'], 'x': x, 'y': y,
             'x_label': RUNS[x]['label'], 'y_label': RUNS[y]['label'], 'nw300': net['nw300']}
        miss = []
        # R2-a
        try:
            if p.get('totals') in ('read',) or (p.get('totals') == 'bin' and 'vf' in D[x] and 'vf' in D[y] and 'first' in D[x] and 'first' in D[y]) \
                    or ('vhr' in D[x] and 'vhr' in D[y] and 'first' in D[x] and 'first' in D[y]):
                P['R2a'] = {f: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} for f, d in r2a(p, D, O701).items()}
            else:
                miss.append('R2a')
        except KeyError as e:
            miss.append('R2a (%s)' % e)
        # R2-c zones, R2-f
        if 'fwe' in D[x] and 'fwe' in D[y]:
            fx, fy = D[x]['fwe'], D[y]['fwe']
            z5 = diff_zone(fwe_agg(fx, zb5, 5, net['nw300']), fwe_agg(fy, zb5, 5, net['nw300']))
            z7 = diff_zone(fwe_agg(fx, zb7, 5, net['nw300']), fwe_agg(fy, zb7, 5, net['nw300']))
            P['R2c'] = {'zones5': z5, 'zones7': z7}
            d1 = [sum(z5[z]['d_veh_h'][w] for z in z5) for w in range(net['nw300'])]
            P['R2f'] = time_shape(d1)
            P['R2f']['d1_per_300s'] = [round(v, 4) for v in d1]
            if p['parts'] == 'all':
                nw900 = net['nw300'] // 3
                P['R2d'] = diff_zone(fwe_agg(fx, cellg, 15, nw900), fwe_agg(fy, cellg, 15, nw900))
        else:
            miss.append('R2c/R2d/R2f (fwe_scan 없음)')
        # R2-b, R2-e
        if p['parts'] == 'all':
            if 'vf' in D[x] and 'vf' in D[y]:
                lx = link_windows(D[x]['vf'], S19, net['nw300'])
                ly = link_windows(D[y]['vf'], S19, net['nw300'])
                dl = {l: [round(a - b, 4) for a, b in zip(lx[l], ly[l])] for l in S19}
                P['R2b'] = {'d_link_300s': dl, 'x_link_300s': {l: [round(v, 4) for v in lx[l]] for l in S19},
                            'y_link_300s': {l: [round(v, 4) for v in ly[l]] for l in S19}}
                gsum = {g: [round(sum(dl[l][w] for l in L), 4) for w in range(net['nw300'])] for g, L in GROUPS.items()}
                P['R2e'] = {'group_d_300s': gsum,
                            'entry_links_total_900_end': {l: round(sum(dl[l][3:]), 4) for l in ENTRY},
                            'exit_links_total_900_end': {l: round(sum(dl[l][3:]), 4) for l in EXIT}}
                pre = sum(abs(dl[l][w]) for l in S19 for w in range(3))
                s14.append({'pair': key, 'pre900_S19_abs_sum': round(pre, 4), 'dagger': pre > 0.05})
                P['S14_dagger'] = pre > 0.05
                # reconciliation: window sum (bin) - total (main form)
                if 'R2a' in P:
                    form = list(P['R2a'].keys())[0]
                    rec = {}
                    for g in GROUPS:
                        tot = P['R2a'][form].get(g)
                        ws = sum(gsum[g])
                        rec[g] = {'window_sum_bin': round(ws, 4), 'total': tot, 'form': form,
                                  'total_minus_windows': None if tot is None else round(tot - ws, 4)}
                    P['reconcile'] = rec
            else:
                miss.append('R2b/R2e (링크 칸 없음)')
        P['not_done'] = miss
        if miss:
            res['not_done'].append({'pair': key, 'missing': miss})
        res['pairs'][key] = P
    res['checks']['S14'] = {'rows': s14, 'action': 'report only (dagger)'}
    # ---- reproduction of known values
    rep = []
    for src, pid, form, vals in KNOWN:
        for metric, tup in vals.items():
            seeds = (31, 41, 43) if len(tup) == 3 else (29,)
            for s, kv in zip(seeds, tup):
                key = '%s|%s-s%d' % (pid, 'v3c3' if s != 29 else '64cf', s)
                mine = res['pairs'].get(key, {}).get('R2a', {}).get(form, {}).get(metric)
                rep.append({'source': src, 'pair': key, 'form': form, 'metric': metric, 'known': kv,
                            'mine': None if mine is None else round(mine, 3),
                            'diff': None if mine is None else round(mine - kv, 3)})
    have = [r for r in rep if r['diff'] is not None]
    res['checks']['repro_known'] = {'n': len(rep), 'n_compared': len(have),
                                    'max_abs_diff': max((abs(r['diff']) for r in have), default=None),
                                    'pass_0p06': all(abs(r['diff']) <= 0.06 for r in have), 'rows': rep}
    res['seconds'] = round(time.time() - t_start, 1)
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False)
    os.replace(tmp, out_path)
    print('R2 done', out_path, 'pairs', len(res['pairs']), 'not_done', len(res['not_done']), 'sec', res['seconds'])
    print('checks', {k: (v.get('pass', v.get('all_equal'))) for k, v in res['checks'].items()})


if __name__ == '__main__':
    main()
