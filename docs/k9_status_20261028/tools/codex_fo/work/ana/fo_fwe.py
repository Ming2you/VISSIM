# -*- coding: utf-8 -*-
"""fo_fwe.py - FO FW_E decomposition rows (COMPARE_RULE_FO s5; 2026-10-27 KST, D-K9-113). Read-only, caches only (no FZP).

Same definitions and the same code as the FW_E decomposition (PRE_FWE c7cc0e6c..., FWE_DECOMP r2 7f58ab3e...):
the pure functions are imported from the pinned tools fwe_r2.py / fwe_r3.py / fwe_synth.py / fwe_r1.py / tails.py /
fwe_analyze.py; the per-pair blocks of fwe_r2.main and fwe_r3.main and the row blocks of fwe_synth.build are copied
here unchanged except the arm/pair names (they cannot be called directly: fwe_r3.main writes its fixed output file).
Arms (per seed v3c3-s31/s41/s43): NC3, V-A, B (existing caches, pinned below) and X (= FO in 'run' mode; = B in 'selftest').
Pairs: X-NC3 (rows like P-B), B-X and X-VA (rows like P-BVA: the R3-type fields are the difference of the two NC3-based
pairs, the R2-type fields are the direct pair, exactly as fwe_synth/fwe_r2 made P-BVA).
Fields: RF1-RF11 + WITH (PRE_FWE s6.2), per arm RF4 (readback GREEN only), RF9, RF10;
DA1 cells 5-9 (c05-c09, 100 m bin centre) d(1) per 900 s and 900 s-end (fwe_r2_after rule); DA2 per arm head minutes at
4,300 m and cells 5-9 congested minutes (fwe_r1.r1_arm rule); DA3 per FW_E meter: count of 900 s windows (from 900 s) with
tight share >= 0.30 and merge d <= -60 veh/h (pair X-NC3); DA4 per FW_E meter per 900 s window: merge d / arm / base (veh/h),
meter mean GREEN, tight share, meter-side stock d (connector + approach, veh.h) (vf_extra2 columns).
selftest (X := B) must reproduce: FWE_REF_C1.json P-B (as X-NC3) and P-BVA (as X-VA), all-zero B-X, R2_after.json P-B DA1,
R1_nc.json NC3 head 4300 m / cells 5-9 minutes (DA2), VERIFY_EXTRA2.json P-B rows (DA4).
usage: python -B fo_fwe.py selftest <out.json> | python -B fo_fwe.py run <out.json>
"""
import copy, csv, hashlib, importlib.util, json, os, sys, time

sys.dont_write_bytecode = True
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
CW = SP + '/codex_handoff/work'
FW = SP + '/codex_handoff/fo/work'
H = 'D:/VISSIM_handoff/20261024'
FO_RUNS = 'D:/VISSIM_runs/20261028_codex_fo_v3c3'
SEEDS = (31, 41, 43)
METERS = ('10639', '10681', '10490', '10484')
RM = {m: 'RM_C' + m for m in METERS}
EXITS = ('10643', '10682', '10481', '10483')
ZONES5 = ('U', 'B1', 'M', 'B2', 'D')
CELLS59 = ['c05', 'c06', 'c07', 'c08', 'c09']
PINS = {
    FD + '/PRE_FWE.md': 'c7cc0e6cc629da156b3ada7278af0fd95a0be4bf80d86ac6532b09e21656ce94',
    FD + '/tools/fwe_r1.py': '658828903f3abe361484b90edd2f8f3a7f63bb23c64c8b8567002cdea1769d93',
    FD + '/tools/fwe_r2.py': '59017c86ff6d640bf72709a13ed88790ca0deb2785ba8da0a3d18df1c1218850',
    FD + '/tools/fwe_r3.py': '34d5945af208ec780ae8f598d2ce2d2a34194f4d52cd46076fd0cc7509287cb8',
    FD + '/tools/fwe_synth.py': '92904e95444b2b18e3745f5ba7d7b9e2dbc2a13064bcb3ad1e5680e244e97245',
    FD + '/tools/fwe_meter_ldp.py': 'f8a076fb26531d9d6352c118d5eef49bebb98e9348f09ff89ba957fef2362ef7',
    FD + '/tools/fwe_npz_bins.py': 'a560206faf0d2bca7747be39279d53b0d9edc2e85222dcccf811ffdaabfc3747',
    SP + '/rmcause/o1o4/work/tails.py': 'cb6c0bd4407fbaad8b403ccc34fc2bcfb1f9b9af318a67ee963b120a8bfb5569',
    SP + '/rmcause/phys/fwe_analyze.py': '5c055dd44b0ae8be6ca4907186e0ba8f25afb8626c3adfc097a5135c918e3aaf',
    SP + '/rmcause/phys/fwe_scan.py': '0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7',
    SP + '/vsl_v3c3/tools/vsl_metrics.py': '160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c',
    SP + '/vsl_v3c3/out/cell/nc3_s31.json': '6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53',
    H + '/derived/omega_membership_exact.json': 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473',
    FD + '/out/inventory.json': 'f51abd202cef209d1b1b5e79b4d3eb4ea13661fe9e0d2ec7d68bd8c5467c94e6',
    CW + '/omega/omega701_recount.py': '5b7826f65c58a883c2dc4a3eccd6de92563bb12f812dd0d6579be8a42c92a5ac',
}
# existing arm caches (read 2026-10-27, pinned; NC3 / V-A / B of v3c3-s31/s41/s43 only)
CACHE = {
    ('NC3', 31): dict(fwe=(SP + '/rmcause/phys/scan/nc_s31.json', '352bddd3a28671575b7671ef1f013c816aa1c163ebd77bd320f452306abe00db'),
                      first=(CW + '/vhr_b/scan_out/first_nc3_s31.json', 'e1da8eb8573cb5ad71115207f603e8dc17b8fc53533fe7fe8f5fd857cd56435d'),
                      vhr=(CW + '/vhr_b/scan_out/nc3_s31.json', 'f3fe787cda213504c203bfe66bca2289436e6067e046c59d5095a656905db62d')),
    ('NC3', 41): dict(fwe=(SP + '/rmcause/phys/scan/nc_s41.json', '65051df07d65bbde5a287dc959481b2043a3e70f93104aad5b862dd32d811cd4'),
                      first=(CW + '/vhr_b/scan_out/first_nc3_s41.json', '976312123967429592aba33c2430fdd2387e9b92da5815b109544bbc8f30a521'),
                      vhr=(CW + '/vhr_b/scan_out/nc3_s41.json', '1ae351a866612dac5bb4b7b6d1c60ed13bd88b7a27760ba4017805952fe52a47')),
    ('NC3', 43): dict(fwe=(SP + '/rmcause/phys/scan/nc_s43.json', '7afd43e8ed482fa60ae5cf5736f4b6e38b07f9844fc3737ec22f372441b2a843'),
                      first=(CW + '/vhr_b/scan_out/first_nc3_s43.json', 'ebcf0b5b2aeff843c3911744c9d29b9311970e16f9f475074c4c52e86fbc8369'),
                      vhr=(CW + '/vhr_b/scan_out/nc3_s43.json', 'fb90d49b5b95349c25bd1feddf65fbbd71bfcb28861467339284935ae795a793')),
    ('VA', 31): dict(fwe=(SP + '/rmcause/phys/scan/va_s31.json', 'd6f693aeaa6deb6784b955f547ff9f64fe9d429c6996af2fb6eada83c68f95a5'),
                     first=(CW + '/vhr_b/scan_out/first_va_s31.json', 'ec8d62954cf39962bee3158014c8e4960597c73f7d22b69d76b8260ffd5d4c90'),
                     vhr=(CW + '/vhr_b/scan_out/va_s31.json', '4f41f5fa53e159fc59dca76e67eac7c632b9bfe39873cb0ee7dcc773a0c3e237'),
                     meter=(SP + '/c_port/readback/out/cycles_va31.csv', '349ea4ca9e2e786aa6c2956d1d111ded545be3a838bc4576cab00fff4b2ad07f', 'va31'),
                     action='D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/action_sdmpc31_v3c3_k92va_s31.csv'),
    ('VA', 41): dict(fwe=(SP + '/rmcause/phys/scan/va_s41.json', 'b2782698f83435e4ce7a0f7e601f2b749694df079b6be68b36d7fcf1ae633c1a'),
                     first=(CW + '/vhr_b/scan_out/first_va_s41.json', '73215ae37ed4a625d71a2779b6803814c6ad0ccb79ab613e6f7b6745ec848565'),
                     vhr=(CW + '/vhr_b/scan_out/va_s41.json', '6eb1dd0aa24951a2275cad998778d1dbe40b26024831ccb21163e3ba1a4ddd80'),
                     meter=(SP + '/c_port/readback/out/cycles_va41.csv', 'aa22b0ff82c482663e7812d44e553e7b1abfd5b3f0a322db0ad5dfdb9b78fee9', 'va41'),
                     action='D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/action_sdmpc31_v3c3_k92va_s41.csv'),
    ('VA', 43): dict(fwe=(SP + '/rmcause/phys/scan/va_s43.json', '9035a75c7efc5ab8d02eaefa92c7b1ced5a4923757b85a600af128b34ccba23c'),
                     first=(CW + '/vhr_b/scan_out/first_va_s43.json', '48f584773c418914e8f16a623e1bce4a33760eb95f98917e22f295ad40698fcd'),
                     vhr=(CW + '/vhr_b/scan_out/va_s43.json', '561b673e3b851f4cd76a9add4fe221b590ac870d5d76cfec544da738425e5a4f'),
                     meter=(SP + '/c_port/readback/out/cycles_va43.csv', '0549d85a3440d5d5053e87e0d755c566f7f41de768d31637a5a1dcdb3c80e0e6', 'va43'),
                     action='D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/action_sdmpc31_v3c3_k92va_s43.csv'),
    ('B', 31): dict(fwe=(FD + '/out/heavy/b_s31.json', 'dd7865a72839e26032f5f33989b5718659f248198ab4125835752463884cc65c'),
                    first=(CW + '/vhr_b/scan_out/first_j1_s31.json', '52a9164dba2ebaaa6a4deeaffcfed2c9144bae8a73f9f3c9d0bebc2f3a8b4960'),
                    vhr=(CW + '/vhr_b/scan_out/j1_s31.json', '4d5e94b0037f60d257a20d181c7a1c156bbf2bebf49b284fa81f99bcdad87838'),
                    meter=(SP + '/c_port/readback/out/cycles_b31.csv', 'baff504fae3710af67c07f7421a13395f914820e6d8bec5762ae2c8b2b713be7', 'b31'),
                    action='D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/action_sdmpc31_sdmpc9000_s31.csv'),
    ('B', 41): dict(fwe=(FD + '/out/heavy/b_s41.json', 'c4a0df26cf2f5005d09e0a47861432fb4b768436d14e73dd26c141e57e5ce1ff'),
                    first=(CW + '/vhr_b/scan_out/first_j1_s41.json', '298979aa7ded01195f3d2c99029292f889e9b48b801167dd1a172efd33631517'),
                    vhr=(CW + '/vhr_b/scan_out/j1_s41.json', '9a4d7cd3cb9e14db8868dac86acfc3fb9b0129052b0d78e9815843fdc3ff5baf'),
                    meter=(SP + '/c_port/readback/out/cycles_b41.csv', '6d9d9da5dcd2a9d591fa5425ea9b15bca71b2c9e5e616a1dd8e87a499f974e88', 'b41'),
                    action='D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/action_sdmpc31_sdmpc9000_s41.csv'),
    ('B', 43): dict(fwe=(FD + '/out/heavy/b_s43.json', '0aa431d2fede54685cdabbff1f2b8b85f08000d3a47cb977912152ab16412d3d'),
                    first=(CW + '/vhr_b/scan_out/first_j1_s43.json', 'cc16b867943a35cfda8af7d30185145bb9e9eada651bfa3b4cf1d4c41f846cca'),
                    vhr=(CW + '/vhr_b/scan_out/j1_s43.json', '93253733953a033f2c7c84bfcda051b93d7e1c1e0a3ac974e4134d33f9771b15'),
                    meter=(SP + '/c_port/readback/out/cycles_b43.csv', '2439f754844ee3efca4d66c999f564d5f5d4398e884f8c5a823a72b5d92b7593', 'b43'),
                    action='D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/action_sdmpc31_sdmpc9000_s43.csv'),
}
REFS = {  # selftest references (FWE_DECOMP r2 / VERIFY_FWE pins)
    'ref': (FD + '/out/FWE_REF_C1.json', 'ce39344bfbbe1b7c0b7d88ba129791b1772d551dad0ab74a0d8d2c36a90febc4'),
    'after': (FD + '/out/R2_after.json', 'b25c30ad753dec7520ad7828f1cbba1703aa38317a6434a256c496307719ebb9'),
    'r1': (FD + '/out/R1_nc.json', 'd2dc870be1546d5518a2ab8e75415e1736cd5e21f8bbcf65bec3d846809537ac'),
    'extra2': (FD + '/verify/out/VERIFY_EXTRA2.json', '29e49a519181e07fb76fd361e8194ae23a07e53e08645edaadb8b5f9af234e19'),
}


def fo_arm(s):
    """FO caches made by the FO analysis steps (COMPARE_RULE_FO s7): sha recorded at use, ties checked in load_arm."""
    return dict(fwe=(FW + '/ana/fwe/fo_s%d.json' % s, None), first=(CW + '/vhr_fo/scan_out/first_j1_s%d.json' % s, None),
                vhr=(CW + '/vhr_fo/scan_out/j1_s%d.json' % s, None),
                meter=(FW + '/ana/readback/cycles_fo%d.csv' % s, None, 'fo%d' % s),
                action=FO_RUNS + '/s%d/sdmpc/action_sdmpc31_sdmpc9000_s%d.csv' % (s, s),
                fzp=FO_RUNS + '/s%d/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_001.fzp' % (s, s))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def pinned(p, want=None):
    want = want or PINS.get(p)
    got = sha(p)
    if want is not None and got != want:
        raise SystemExit('PIN MISMATCH %s %s != %s' % (p, got, want))
    return got


def jload(p, want=None):
    pinned(p, want)
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def load_module(name, p):
    pinned(p)
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def roundtrip(o):
    return json.loads(json.dumps(o, ensure_ascii=False, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))


# ---------------------------------------------------------------- modules (pinned)
for _p in PINS:
    pinned(_p)
R1M = load_module('fwe_r1', FD + '/tools/fwe_r1.py')
R2M = load_module('fwe_r2', FD + '/tools/fwe_r2.py')
R3M = load_module('fwe_r3', FD + '/tools/fwe_r3.py')
SY = load_module('fwe_synth', FD + '/tools/fwe_synth.py')
TL = load_module('tails', SP + '/rmcause/o1o4/work/tails.py')
FA = load_module('fwe_analyze', SP + '/rmcause/phys/fwe_analyze.py')
FS = load_module('fwe_scan', SP + '/rmcause/phys/fwe_scan.py')
O701 = set(map(str, jload(H + '/derived/omega_membership_exact.json')['inside_links']))
O701_INT = set(int(x) for x in O701)
CB = jload(SP + '/vsl_v3c3/out/cell/nc3_s31.json')['cell_bounds_m']
Z5 = [(k.split('_')[0], a, e) for k, (a, e) in FA.ZONES.items()]   # fwe_r2.main
ZB5 = R2M.zone_bins(108, Z5)
_cells = {}
for _b in range(108):
    _cells.setdefault(R2M.cell_of((_b + 0.5) * 100.0, CB), []).append(_b)
CELLG = {k: v for k, v in {'c%02d' % i: _cells.get(i, []) for i in range(len(CB) - 1)}.items() if v}


def load_arm(arm, s, spec):
    a = {'arm': arm, 'seed': s, 'files': {}}
    for k in ('fwe', 'first', 'vhr'):
        p, want = spec[k]
        a[k] = jload(p, want)
        a['files'][k] = {'path': p, 'sha256': sha(p)}
    if spec.get('meter'):
        p, want, tag = spec['meter']
        pinned(p, want)
        a['files']['meter'] = {'path': p, 'sha256': sha(p), 'run_tag': tag}
        a['meter_spec'] = {'meter': ('rb', p, tag)}
    if spec.get('action'):
        a['files']['action'] = {'path': spec['action'], 'sha256': sha(spec['action'])}
    # tie: vhr scan and fwe_scan of the same FZP (sha inside both caches)
    a['tie'] = {'vhr_fzp_sha256': a['vhr'].get('file_sha256'), 'fwe_fzp_sha256': a['fwe'].get('fzp_sha256')}
    a['tie']['same_fzp'] = a['tie']['vhr_fzp_sha256'] == a['tie']['fwe_fzp_sha256'] is not None
    if spec.get('fzp'):
        a['tie']['run_fzp_path'] = spec['fzp']
        a['tie']['vhr_path_is_run_fzp'] = a['vhr'].get('path', '').replace('\\', '/').lower() == spec['fzp'].lower()
        a['tie']['first_vehicles'] = a['first'].get('vehicles')
    a['fw'] = R3M.fwe_windows(a['fwe'], 9000)
    return a


# ---------------------------------------------------------------- R2-type pair (fwe_r2.main pair block, parts all w/o links)
def r2_pair(pid, X, Y):
    D = {'x': {'vhr': X['vhr'], 'first': X['first']}, 'y': {'vhr': Y['vhr'], 'first': Y['first']}}
    p = dict(id=pid, x='x', y='y', net='v3c3', seed=X['seed'])
    P = {'pair': pid, 'x': X['arm'], 'y': Y['arm'], 'nw300': 30}
    P['R2a'] = {f: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} for f, d in R2M.r2a(p, D, O701).items()}
    fx, fy = X['fwe'], Y['fwe']
    z5 = R2M.diff_zone(R2M.fwe_agg(fx, ZB5, 5, 30), R2M.fwe_agg(fy, ZB5, 5, 30))
    P['R2c'] = {'zones5': z5}
    d1 = [sum(z5[z]['d_veh_h'][w] for z in z5) for w in range(30)]
    P['R2f'] = R2M.time_shape(d1)
    P['R2f']['d1_per_300s'] = [round(v, 4) for v in d1]
    P['R2d'] = R2M.diff_zone(R2M.fwe_agg(fx, CELLG, 15, 10), R2M.fwe_agg(fy, CELLG, 15, 10))
    return roundtrip(P)


# ---------------------------------------------------------------- R3-type pair (fwe_r3.main pair block, v3c3, W = 9000)
def meters_of(a):
    if 'meter_spec' not in a:
        return None, {'kind': 'none', 'note': '기록 없음(미터 readback 없음)'}
    cy, prov = R3M.meter_cycles(a['meter_spec'], None, 9000)
    return cy, prov


def r3_pair(A_, B_):
    r = R3M.r
    W, nwin = 9000, 30
    res = dict(arm=A_['arm'], base_phys=B_['arm'], W=W, form='ours_9000', seed=A_['seed'])
    ta = R3M.totals_from_vhr(A_['vhr'], 'ours_9000', O701_INT)
    tb = R3M.totals_from_vhr(B_['vhr'], 'ours_9000', O701_INT)
    tot = {x: ta[x] - tb[x] for x in ta}
    fb = B_['first']
    tot['U'] = R3M.S_int(fb, W) - R3M.S_int(A_['first'], W)
    tot['u1098'] = R3M.S_int(fb, W, {'74'}) - R3M.S_int(A_['first'], W, {'74'})
    tot['u1099'] = R3M.S_int(fb, W, {'26'}) - R3M.S_int(A_['first'], W, {'26'})
    tot['A4'] = tot['A4a'] + tot['U']
    tot['outa'] = tot['A4'] - tot['O701']
    tot['outb'] = tot['A4a'] - tot['O701']
    tot['O701_minus_L19'] = tot['O701'] - tot['L19']
    res['totals'] = {x: (r(v) if isinstance(v, float) else v) for x, v in tot.items()}
    fa, fbw = A_['fw'], B_['fw']
    d1 = [fa['chain'][k] - fbw['chain'][k] for k in range(nwin)]
    dz = {z: [fa['zones'][z][k] - fbw['zones'][z][k] for k in range(nwin)] for z in R3M.ZONES}
    gt = R3M.gain_times(d1)
    res['d1_win'] = [r(x) for x in d1]
    res['d1_zone_win'] = {z: [r(x) for x in v] for z, v in dz.items()}
    res['gain'] = {x: (r(v) if isinstance(v, float) else ([r(y) for y in v] if isinstance(v, list) else v)) for x, v in gt.items()}
    res['merge_vph'] = {r_: dict(arm=[x * 12 for x in fa['merge'][r_]], base=[x * 12 for x in fbw['merge'][r_]],
                                 d=[(fa['merge'][r_][k] - fbw['merge'][r_][k]) * 12 for k in range(nwin)]) for r_ in R3M.ENTRY_CONN}
    rd = {}
    for r_ in R3M.ENTRY_CONN:
        rr = {}
        for q in ('conn_stock', 'conn_q', 'from_stock', 'from_q'):
            rr[q] = dict(arm=[r(x, 4) for x in fa[q][r_]], base=[r(x, 4) for x in fbw[q][r_]],
                         d=[r(fa[q][r_][k] - fbw[q][r_][k], 4) for k in range(nwin)], d_total=r(sum(fa[q][r_]) - sum(fbw[q][r_])))
        rr['ramp_qmax'] = dict(arm=fa['ramp_qmax'][r_], base=fbw['ramp_qmax'][r_])
        rr['meter_side_total_d'] = r(sum(fa['conn_stock'][r_]) + sum(fa['from_stock'][r_]) - sum(fbw['conn_stock'][r_]) - sum(fbw['from_stock'][r_]))
        rr['meter_side_q_total_d'] = r(sum(fa['conn_q'][r_]) + sum(fa['from_q'][r_]) - sum(fbw['conn_q'][r_]) - sum(fbw['from_q'][r_]))
        rd[r_] = rr
    res['ramp'] = rd
    res['exit'] = {o: dict(d=[r(fa['off_stock'][o][k] - fbw['off_stock'][o][k], 4) for k in range(nwin)],
                           d_total=r(sum(fa['off_stock'][o]) - sum(fbw['off_stock'][o]))) for o in R3M.EXIT_CONN}
    wa, sa = R3M.first_cum_area(A_['first'], W)
    wb, sb = R3M.first_cum_area(fb, W)
    dwin = [wb[k] - wa[k] for k in range(nwin)]
    dU = R3M.S_int(fb, W, {'74'}) - R3M.S_int(A_['first'], W, {'74'})
    res['u1098_win'] = [r(x, 4) for x in dwin]
    res['u1098_sum'] = r(sum(dwin), 4)
    res['u1098_dU'] = r(dU, 4)
    res['S6_ok'] = abs(sum(dwin) - dU) <= 0.05
    cy, prov = meters_of(A_)
    ms = {m: R3M.meter_summary(cy.get(m), W) for m in list(R3M.FWE_METERS) + list(R3M.FWW_METERS)} if cy is not None else None
    res['meter_arm'] = {m: ms.get(m) for m in R3M.FWE_METERS} if ms else prov
    res['meter_cycles_arm'] = {m: cy.get(m) for m in R3M.FWE_METERS} if cy is not None else None
    tf = {}
    for m in R3M.FWE_METERS:
        mm = res['meter_arm'].get(m) if isinstance(res['meter_arm'], dict) and m in res['meter_arm'] else None
        t10 = mm['T_tight10'] if mm else None
        if mm is None:
            tf[m] = '미터 기록 없음'
        elif t10 is None:
            tf[m] = '조임 없음'
        else:
            tf[m] = dict(T_tight10=t10, a_minus=(None if gt['T_gain_a'] is None else gt['T_gain_a'] - t10),
                         b_minus=(None if gt['T_gain_b'] is None else gt['T_gain_b'] - t10))
    res['timing'] = tf
    return roundtrip(res)


# ---------------------------------------------------------------- rows (fwe_synth.build row blocks)
def r1(x, nd=1):
    return SY.r1(x, nd)


def row_arm(p2, p3, arm_key, spills, vsl):
    """fwe_synth.build 'else' branch (pair arm - NC3)."""
    g9, vsub, ramp_d300 = SY.group900, SY.vsub, SY.ramp_d300
    row = {}
    row['RF1'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S7']), 'codex_8100': r1(p2['R2a']['codex_8100']['S7'])}
    row['RF2'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S19']), 'codex_8100': r1(p2['R2a']['codex_8100']['S19'])}
    row['RF3'] = {z: [r1(x) for x in g9(p2['R2c']['zones5'][z]['d_veh_h'])] for z in ZONES5}
    row['WITH'] = {f: {k: r1(p2['R2a'][f][k]) for k in ('O701', 'A4', 'outa', 'outb')} for f in ('ours_9000', 'codex_8100')}
    row['RF11'] = {'T_gain_a_s': p2['R2f']['T_gain_a_s'], 'T_gain_b_s': p2['R2f']['T_gain_b_s'], 'T_half_s': p2['R2f']['T_half_s'],
                   'cum_d1_900_end': r1(p2['R2f']['final_cum_900_end'])}
    row['RF5'] = {m: {'d': [r1(x, 0) for x in g9(p3['merge_vph'][m]['d'], 'mean')],
                      'arm': [r1(x, 0) for x in g9(p3['merge_vph'][m]['arm'], 'mean')]} for m in METERS}
    row['RF6'] = {}
    for m in METERS:
        st, q = ramp_d300(p3['ramp'][m])
        row['RF6'][m] = {'stock_d': r1(p3['ramp'][m]['meter_side_total_d']), 'queue_d': r1(p3['ramp'][m]['meter_side_q_total_d']),
                         'stock_d_900': [r1(x) for x in g9(st)],
                         'qmax_arm_base': [max(p3['ramp'][m]['ramp_qmax']['arm'][3:]), max(p3['ramp'][m]['ramp_qmax']['base'][3:])]}
    row['RF7'] = {'total': r1(p3['u1098_sum']), 'w900': [r1(x) for x in g9(p3['u1098_win'])]}
    row['RF8'] = {e: r1(p3['exit'][e]['d_total']) for e in EXITS}
    rf4 = {}
    for m in METERS:
        ma = p3['meter_arm'].get(RM[m]) if isinstance(p3['meter_arm'], dict) else None
        if not isinstance(ma, dict) or 'n_cycles' not in ma:
            rf4[m] = {'state': '기록 없음'}
        else:
            rf4[m] = {'n_tight10': ma['n_tight10'], 'n_cycles': ma['n_cycles'], 'T_tight10': ma['T_tight10'], 'T_tight6': ma['T_tight6'],
                      'green_hist': ma['green_hist'], 'mean_green': r1(ma.get('green_seconds_total', 0) / ma['n_cycles'], 2)}
    row['RF4'] = rf4
    row['RF9'] = {'arm_B1': spills[arm_key]['b1_spill_min_lt4500'], 'arm_M': spills[arm_key]['m_spill_min_lt6800'],
                  'NC3_B1': spills['NC3']['b1_spill_min_lt4500'], 'NC3_M': spills['NC3']['m_spill_min_lt6800'],
                  'arm_B1_tail_min_m': spills[arm_key]['b1_tail_min_m'], 'arm_B2_tail_min_m': spills[arm_key]['b2_tail_min_m']}
    row['RF10'] = {'n_decisions_lt110': len(vsl[arm_key]['decisions_lt110']), 'times_s': vsl[arm_key]['decisions_lt110']} if vsl.get(arm_key) else {'n_decisions_lt110': None}
    row['RF11']['T_gain_minus_T_tight10'] = p3['timing']
    return row


def row_diff(p2, pA, pB, armA, armB, spills, tA):
    """fwe_synth.build 'P-BVA' branch: A - B = (A - NC3) - (B - NC3) for the R3-type fields; R2-type fields from p2."""
    g9, vsub, ramp_d300 = SY.group900, SY.vsub, SY.ramp_d300
    row = {}
    row['RF1'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S7']), 'codex_8100': r1(p2['R2a']['codex_8100']['S7'])}
    row['RF2'] = {'ours_9000': r1(p2['R2a']['ours_9000']['S19']), 'codex_8100': r1(p2['R2a']['codex_8100']['S19'])}
    row['RF3'] = {z: [r1(x) for x in g9(p2['R2c']['zones5'][z]['d_veh_h'])] for z in ZONES5}
    row['WITH'] = {f: {k: r1(p2['R2a'][f][k]) for k in ('O701', 'A4', 'outa', 'outb')} for f in ('ours_9000', 'codex_8100')}
    row['RF11'] = {'T_gain_a_s': p2['R2f']['T_gain_a_s'], 'T_gain_b_s': p2['R2f']['T_gain_b_s'], 'T_half_s': p2['R2f']['T_half_s'],
                   'cum_d1_900_end': r1(p2['R2f']['final_cum_900_end'])}
    A, Bq = pA, pB
    row['RF5'] = {m: [r1(x, 0) for x in g9(vsub(A['merge_vph'][m]['arm'], Bq['merge_vph'][m]['arm']), 'mean')] for m in METERS}
    row['RF6'] = {}
    for m in METERS:
        sa, qa = ramp_d300(A['ramp'][m])
        sb, qb = ramp_d300(Bq['ramp'][m])
        row['RF6'][m] = {'stock_d': r1(sum(sa) - sum(sb)), 'queue_d': r1(sum(qa) - sum(qb)), 'stock_d_900': [r1(x) for x in g9(vsub(sa, sb))]}
    u = vsub(A['u1098_win'], Bq['u1098_win'])
    row['RF7'] = {'total': r1(sum(u)), 'w900': [r1(x) for x in g9(u)]}
    row['RF8'] = {e: r1(A['exit'][e]['d_total'] - Bq['exit'][e]['d_total']) for e in EXITS}
    row['RF4'] = '%s 팔 값 대 %s 팔 값을 나란히(arms 칸)' % (armA, armB)
    row['RF9'] = {'B1_d': spills[armA]['b1_spill_min_lt4500'] - spills[armB]['b1_spill_min_lt4500'],
                  'M_d': spills[armA]['m_spill_min_lt6800'] - spills[armB]['m_spill_min_lt6800']}
    row['RF10'] = '%s 대 %s 결정 수(arms 칸)' % (armA, armB)
    row['RF11']['T_gain_minus_T_tight10_A'] = {m: (None if p2['R2f']['T_gain_a_s'] is None or tA.get(m) is None else p2['R2f']['T_gain_a_s'] - tA[m]) for m in METERS}
    row['how'] = '[계산] 같은 시드 (%s − NC3) − (%s − NC3) (R3 칸), R2 칸은 직접 짝' % (armA, armB)
    return row


# ---------------------------------------------------------------- DA fields
def da1(p2):
    nw = len(p2['R2d']['c05']['d_veh_h'])
    per = [sum(p2['R2d'][c]['d_veh_h'][w] for c in CELLS59) for w in range(nw)]
    piece = sum(per[1:])
    d1 = p2['R2f']['final_cum_900_end']
    return {'cells5_9_per_900s': [round(v, 3) for v in per], 'cells5_9_900_end': round(piece, 3), 'd1_900_end': d1, 'd1_rest': round(d1 - piece, 3)}


def da2(a):
    zones5 = list(FA.ZONES.items())
    zones7 = R1M.zones7_from_vsl_metrics(SP + '/vsl_v3c3/tools/vsl_metrics.py')
    res = R1M.r1_arm(a['fwe'], FA, TL, FS.CHAIN, zones5, zones7, CB)
    hm = {h['x_m']: h['minutes'] for h in res['R1e_heads']}
    cells = sum((res['R1c_cells'].get(str(c)) or {}).get('cong_minutes_all_windows', 0) for c in range(5, 10))
    return {'head_4300_minutes': hm.get(4300, 0), 'cells5_9_cong_minutes': cells}


def da34(p3):
    cy = p3.get('meter_cycles_arm')
    out3, out4 = {}, {}
    for m in METERS:
        mv = p3['merge_vph'][m]
        st, _ = SY.ramp_d300(p3['ramp'][m])
        cyc = (cy or {}).get(RM[m]) or []
        rows, n3 = {}, 0
        for w9 in range(1, 10):
            ks = range(3 * w9, 3 * w9 + 3)
            d = sum(mv['d'][k] for k in ks) / 3.0
            arm = sum(mv['arm'][k] for k in ks) / 3.0
            base = sum(mv['base'][k] for k in ks) / 3.0
            cs = [g for c, g in cyc if 900 * w9 <= c < 900 * (w9 + 1)]
            g = (sum(cs) / len(cs)) if cs else None
            tight = (sum(1 for x in cs if x < 10) / len(cs)) if cs else None
            sd = sum(st[k] for k in ks)
            rows[str(900 * w9)] = {'d': round(d), 'arm': round(arm), 'base': round(base), 'g': None if g is None else round(g, 2),
                                   'tight': None if tight is None else round(tight, 2), 'stock_d': round(sd, 2)}
            if tight is not None and tight >= 0.30 and d <= -60.0:
                n3 += 1
        out3[m] = n3
        out4[m] = rows
    return out3, out4


# ---------------------------------------------------------------- main
def build(mode):
    t0 = time.time()
    out = {'tool': os.path.abspath(__file__).replace('\\', '/'), 'tool_sha256': sha(os.path.abspath(__file__)), 'mode': mode,
           'made_kst': time.strftime('%Y-%m-%d %H:%M:%S'), 'pins': PINS, 'arms': {}, 'rows': {}, 'DA': {}, 'stops': []}
    for s in SEEDS:
        A = {}
        for arm in ('NC3', 'VA', 'B'):
            A[arm] = load_arm(arm, s, CACHE[(arm, s)])
        A['X'] = load_arm('X', s, CACHE[('B', s)] if mode == 'selftest' else fo_arm(s))
        for k, a in A.items():
            if not a['tie']['same_fzp']:
                out['stops'].append('v3c3-s%d arm %s: vhr and fwe_scan caches are not of the same FZP' % (s, k))
            if k == 'X' and mode == 'run' and not a['tie'].get('vhr_path_is_run_fzp'):
                out['stops'].append('v3c3-s%d FO vhr cache is not of the FO run FZP' % s)
        spills = {k: SY.spill_from_scan(TL, a['fwe']) for k, a in A.items()}
        vsl = {k: R3M.vsl_decisions(a['files']['action']['path'], 9000) for k, a in A.items() if 'action' in a['files']}
        p3 = {k: r3_pair(A[k], A['NC3']) for k in ('X', 'B', 'VA')}
        p2 = {'X-NC3': r2_pair('X-NC3', A['X'], A['NC3']), 'B-X': r2_pair('B-X', A['B'], A['X']), 'X-VA': r2_pair('X-VA', A['X'], A['VA'])}
        tX = {m: ((p3['X']['meter_arm'] or {}).get(RM[m]) or {}).get('T_tight10') if isinstance(p3['X']['meter_arm'], dict) else None for m in METERS}
        tB = {m: ((p3['B']['meter_arm'] or {}).get(RM[m]) or {}).get('T_tight10') if isinstance(p3['B']['meter_arm'], dict) else None for m in METERS}
        rows = {'X-NC3': row_arm(p2['X-NC3'], p3['X'], 'X', spills, vsl),
                'B-X': row_diff(p2['B-X'], p3['B'], p3['X'], 'B', 'X', spills, tB),
                'X-VA': row_diff(p2['X-VA'], p3['X'], p3['VA'], 'X', 'VA', spills, tX)}
        armrows = {}
        for k in ('X', 'B', 'VA'):
            rf4 = row_arm(p2['X-NC3'], p3[k], k, spills, vsl)['RF4'] if k != 'X' else rows['X-NC3']['RF4']
            armrows[k] = {'RF4': rf4, 'RF9': {'B1': spills[k]['b1_spill_min_lt4500'], 'M': spills[k]['m_spill_min_lt6800']},
                          'RF10': ({'n_decisions_lt110': len(vsl[k]['decisions_lt110']), 'times_s': vsl[k]['decisions_lt110']} if k in vsl else None)}
        armrows['NC3'] = {'RF4': '기록 없음(v3c3 NC3: 미터 LDP·readback 없음)', 'RF9': {'B1': spills['NC3']['b1_spill_min_lt4500'], 'M': spills['NC3']['m_spill_min_lt6800']}}
        da3, da4 = da34(p3['X'])
        out['rows']['v3c3-s%d' % s] = rows
        out['arms']['v3c3-s%d' % s] = {'files': {k: a['files'] for k, a in A.items()}, 'ties': {k: a['tie'] for k, a in A.items()}, 'per_arm': armrows}
        out['DA']['v3c3-s%d' % s] = {'DA1': {k: da1(p2[k]) for k in p2}, 'DA2': {k: da2(A[k]) for k in ('X', 'NC3', 'B', 'VA')},
                                    'DA3': da3, 'DA4': da4, 'DA3_rule': 'tight >= 0.30 and merge d <= -60 veh/h, 900 s windows from 900 s, pair X-NC3'}
        out['S6_ok'] = out.get('S6_ok', True) and all(p3[k]['S6_ok'] for k in p3)
    out['seconds'] = round(time.time() - t0, 1)
    return out


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) <= 1e-9
    return a == b


def zero_like(x):
    if isinstance(x, dict):
        return all(zero_like(v) for v in x.values())
    if isinstance(x, list):
        return all(zero_like(v) for v in x)
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return x == 0
    return True


def selftest(out):
    ref = jload(*REFS['ref'])['ref']['seeds']
    after = jload(*REFS['after'])['pairs']
    r1j = jload(*REFS['r1'])
    ex2 = jload(*REFS['extra2'])
    chk = {}
    fields_arm = ('RF1', 'RF2', 'RF3', 'WITH', 'RF5', 'RF6', 'RF7', 'RF8', 'RF4', 'RF9', 'RF10')
    fields_diff = ('RF1', 'RF2', 'RF3', 'WITH', 'RF5', 'RF6', 'RF7', 'RF8', 'RF9')
    for s in SEEDS:
        k = 'v3c3-s%d' % s
        rows = out['rows'][k]
        for f in fields_arm:
            chk['%s X-NC3 == REF P-B %s' % (k, f)] = same(rows['X-NC3'][f], ref[k]['P-B'][f])
        for f in ('T_gain_a_s', 'T_gain_b_s', 'T_half_s', 'cum_d1_900_end', 'T_gain_minus_T_tight10'):
            chk['%s X-NC3 == REF P-B RF11.%s' % (k, f)] = same(rows['X-NC3']['RF11'][f], ref[k]['P-B']['RF11'][f])
        for f in fields_diff:
            chk['%s X-VA == REF P-BVA %s' % (k, f)] = same(rows['X-VA'][f], ref[k]['P-BVA'][f])
        for f in ('T_gain_a_s', 'T_gain_b_s', 'T_half_s', 'cum_d1_900_end'):
            chk['%s X-VA == REF P-BVA RF11.%s' % (k, f)] = same(rows['X-VA']['RF11'][f], ref[k]['P-BVA']['RF11'][f])
        chk['%s X-VA RF11 T_gain-T_tight10 == REF P-BVA' % k] = same({m: v for m, v in rows['X-VA']['RF11']['T_gain_minus_T_tight10_A'].items()},
                                                                     ref[k]['P-BVA']['RF11']['T_gain_minus_T_tight10_B'])
        bx = rows['B-X']
        chk['%s B-X all zero' % k] = all(zero_like(bx[f]) for f in fields_diff) and bx['RF11']['T_gain_a_s'] is None
        a = after['P-B|%s' % k]
        d1 = out['DA'][k]['DA1']['X-NC3']
        chk['%s DA1 == R2_after P-B' % k] = (same(d1['cells5_9_per_900s'], a['cells5_9_per_900s']) and same(d1['cells5_9_900_end'], a['cells5_9_900_end'])
                                             and same(d1['d1_900_end'], a['d1_900_end']) and same(d1['d1_rest'], a['d1_rest']))
        r1a = r1j['arms'][k]['R1']
        hm = {h['x_m']: h['minutes'] for h in r1a['R1e_heads']}
        cells = sum((r1a['R1c_cells'].get(str(c)) or {}).get('cong_minutes_all_windows', 0) for c in range(5, 10))
        chk['%s DA2 NC3 == R1' % k] = out['DA'][k]['DA2']['NC3'] == {'head_4300_minutes': hm.get(4300, 0), 'cells5_9_cong_minutes': cells}
        e = ex2['P-B|s%d' % s]
        mine = out['DA'][k]['DA4']
        diffs = []
        for m in METERS:
            for w, rr in e[m].items():
                got = mine[m].get(w)
                if got is None:
                    diffs.append((m, w, 'missing'))
                    continue
                for f in ('d', 'arm', 'base', 'g', 'tight'):
                    if rr[f] != got[f]:
                        diffs.append((m, w, f, rr[f], got[f]))
                if abs(rr['stock_d'] - got['stock_d']) > 0.011:
                    diffs.append((m, w, 'stock_d', rr['stock_d'], got['stock_d']))
        chk['%s DA4 == VERIFY_EXTRA2 P-B' % k] = not diffs
        if diffs:
            out.setdefault('selftest_da4_diffs', {})[k] = diffs[:20]
    out['selftest'] = {'checks': chk, 'n': len(chk), 'n_false': sum(1 for v in chk.values() if not v),
                       'refs': {k: {'path': p, 'sha256': w} for k, (p, w) in REFS.items()}}
    out['selftest']['pass'] = out['selftest']['n_false'] == 0 and not out['stops']
    return out


def main():
    mode, outp = sys.argv[1], sys.argv[2]
    if mode not in ('selftest', 'run'):
        raise SystemExit(__doc__)
    out = build(mode)
    if mode == 'selftest':
        out = selftest(out)
    with open(outp + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(outp + '.tmp', outp)
    if mode == 'selftest':
        st = out['selftest']
        print('SELFTEST pass=%s checks=%d false=%d stops=%d sec=%s' % (st['pass'], st['n'], st['n_false'], len(out['stops']), out['seconds']))
        for k, v in st['checks'].items():
            if not v:
                print('  FALSE', k)
    else:
        print('FO_FWE done stops=%d sec=%s' % (len(out['stops']), out['seconds']))
        for x in out['stops']:
            print('  STOP', x)


if __name__ == '__main__':
    main()
