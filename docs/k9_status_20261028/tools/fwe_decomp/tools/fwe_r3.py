# -*- coding: utf-8 -*-
"""fwe_r3.py - PRE_FWE section 5.3 R3 cells (meter GREEN cycles, first tightening, merge flows, ramp/approach stock,
entry wait 1098 by window, timing vs gain, cost location, VSL clue). D-K9-106, 2026-10-27 KST.

Reads only caches (fwe_scan JSON, readback cycle CSV, meter LDP, first-seen JSON, vhr link integrals, npz, linkbin,
run action CSV) and the R3 heavy outputs in FD/out/heavy. Writes only FD/out/R3_meters.json.
Definitions are PRE_FWE r1 (sha c7cc0e6c...) sections 5.3, 7.2-7.4 and 10 (S-2, S-4, S-6, S-8, S-14).
python -B fwe_r3.py
"""
import csv, hashlib, json, math, os, sys, time

FD = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/fwe_decomp'
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
CW = SP + '/codex_handoff/work'
H = 'D:/VISSIM_handoff/20261024'
HEAVY = FD + '/out/heavy'
sys.dont_write_bytecode = True
sys.path.insert(0, FD + '/tools')
import fwe_meter_ldp as ML  # noqa: E402

PRE_SHA = 'c7cc0e6cc629da156b3ada7278af0fd95a0be4bf80d86ac6532b09e21656ce94'
OMEGA_SHA = 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473'
S7 = {74, 10699, 2, 10613, 119, 10702, 24}
ENTRY_CONN = [10639, 10681, 10490, 10484]
APPROACH = {10639: 70, 10681: 68, 10490: 129, 10484: 31}
EXIT_CONN = [10643, 10682, 10481, 10483]
S19 = S7 | set(ENTRY_CONN) | set(APPROACH.values()) | set(EXIT_CONN)
LOCAL12 = ENTRY_CONN + [APPROACH[r] for r in ENTRY_CONN] + EXIT_CONN
ZONES = {'U': (0, 4200), 'B1': (4200, 5300), 'M': (5300, 6800), 'B2': (6800, 7900), 'D': (7900, 10800)}
FWE_METERS = {'RM_C10639': (9105, 10639), 'RM_C10681': (9106, 10681), 'RM_C10490': (9107, 10490), 'RM_C10484': (9108, 10484)}
FWW_METERS = {'RM_C10480': 9101, 'RM_C10482': 9102, 'RM_C10646': 9103, 'RM_C10644': 9104}
MERGE_ZONE = {10639: 'B1', 10681: 'B1', 10490: 'B2', 10484: 'B2'}  # PRE 6.1 C-RM (input only)
VFH = 5.0 / 3600.0


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ---------------------------------------------------------------- inventory / arms
INV = jload(FD + '/out/inventory.json')


def inv_run(arm, seed):
    for r in INV['runs']:
        if r['arm'] == arm and r['provenance']['seed'] == seed:
            return r
    raise KeyError((arm, seed))


def arm_specs():
    A = {}
    for s in (31, 41, 43):
        A[f'NC3-s{s}'] = dict(net='v3c3', inv=('NC3', s), fwe=f'{SP}/rmcause/phys/scan/nc_s{s}.json',
                              first=f'{CW}/vhr_b/scan_out/first_nc3_s{s}.json', vhr=f'{CW}/vhr_b/scan_out/nc3_s{s}.json',
                              npz=f'{CW}/omega/cache/nc3_s{s}.npz', meter=('none', 'v3c3 NC3: 미터 LDP·readback 없음(기록 없음)'))
        A[f'VA-s{s}'] = dict(net='v3c3', inv=('V-A', s), fwe=f'{SP}/rmcause/phys/scan/va_s{s}.json',
                             first=f'{CW}/vhr_b/scan_out/first_va_s{s}.json', vhr=f'{CW}/vhr_b/scan_out/va_s{s}.json',
                             npz=f'{CW}/omega/cache/va_s{s}.npz', meter=('rb', f'{SP}/c_port/readback/out/cycles_va{s}.csv', f'va{s}'))
        A[f'B-s{s}'] = dict(net='v3c3', inv=('B', s), fwe=f'{HEAVY}/b_s{s}.json',
                            first=f'{CW}/vhr_b/scan_out/first_j1_s{s}.json', vhr=f'{CW}/vhr_b/scan_out/j1_s{s}.json',
                            npz=f'{CW}/omega_b/cache/j1_s{s}.npz', meter=('rb', f'{SP}/c_port/readback/out/cycles_b{s}.csv', f'b{s}'))
        A[f'VSL-s{s}'] = dict(net='v3c3', inv=('VSL', s), fwe=f'{SP}/vsl_v3c3/out/phys/vsl_s{s}.json',
                              first=f'{SP}/vsl_v3c3/out/vhr/first_vsl_s{s}.json', vhr=f'{SP}/vsl_v3c3/out/vhr/vsl_s{s}.json',
                              npz=None, meter=('ldp',))
        A[f'J1-s{s}'] = dict(net='v3c3', inv=('J1(참고)', s), fwe=f'{SP}/rmcause/phys/scan/j1_s{s}.json',
                             first=f'{CW}/vhr/scan_out/first_j1_s{s}.json', vhr=f'{CW}/vhr/scan_out/j1_s{s}.json',
                             npz=f'{CW}/omega/cache/j1_s{s}.npz',
                             meter=('read', 'J1: 미터 LDP·readback 주기 표 없음. [읽음 SP/rmcause/METER_CAUSE.md:18] "61결정 × 미터 8개 내내 녹색 10"'))
    A['cxNC'] = dict(net='64cf', inv=('codex NC', 29), fwe=None, first=f'{CW}/vhr/scan_out/first_nc_raw.json',
                     vhr=f'{CW}/vhr/scan_out/nc_raw.json', npz=None, meter=('ldp',))
    A['LNC'] = dict(net='64cf', inv=('LNC', 29), fwe=f'{SP}/rmcause/phys/scan/cf_s29_none.json',
                    first=f'{CW}/a1/full/firstseen/first_lnc.json', vhr=f'{CW}/vhr/scan_out/lnc.json',
                    npz=f'{CW}/omega/cache/lnc_64cf_s29.npz', lb=f'{SP}/rmcause/o1o4/scan/lb_nc_s29.json', meter=('ldp',))
    for k, arm, fwe, first, vhr in (
            ('joint', 'codex joint', f'{SP}/c_port/vsl/out/scan/cx_joint_s29.json', f'{CW}/vhr/scan_out/first_joint.json', f'{CW}/vhr/scan_out/joint.json'),
            ('window', 'codex window', f'{SP}/c_port/vsl/out/scan/cx_window_s29.json', f'{CW}/vhr/scan_out/first_window.json', f'{CW}/vhr/scan_out/window.json'),
            ('off', 'codex off', f'{SP}/c_port/vsl/out/scan/cx_off_s29.json', f'{CW}/vhr/scan_out/first_off.json', f'{CW}/vhr/scan_out/off.json'),
            ('fw', 'codex freeway_only', f'{SP}/c_port/vsl/out/scan/cx_fwonly_s29.json', f'{HEAVY}/first_freeway_only.json', f'{CW}/vhr/scan_out/freeway_only.json'),
            ('urb', 'codex urban_only', f'{HEAVY}/cx_urban_s29.json', f'{HEAVY}/first_urban_only.json', f'{CW}/vhr/scan_out/urban_only.json')):
        A[k] = dict(net='64cf', inv=(arm, 29), fwe=fwe, first=first, vhr=vhr, npz=None, meter=('ldp',))
    A['A1'] = dict(net='64cf', inv=('A1', 29), fwe=f'{SP}/c_port/vsl/out/scan/a1_s29.json',
                   first=f'{CW}/a1/full/firstseen/first_a1.json', vhr=None, npz=None, meter=('ldp',))
    A['vsl64'] = dict(net='64cf', inv=('vsl_repro vsl', 29), fwe=f'{SP}/rmcause/o1o4/scan/vsl_s29.json',
                      first=f'{SP}/c_port/vsl/out/first_vsl.json', vhr=None, npz=None,
                      lb=f'{SP}/rmcause/o1o4/scan/lb_vsl_s29.json', meter=('ldp',))
    return A


# pair: (name, arm, base_phys, base_first, base_totals, W, group, totals_mode)
def pair_specs():
    P = []
    for s in (31, 41, 43):
        P.append(dict(name=f'P-VA v3c3-s{s}', arm=f'VA-s{s}', base=f'NC3-s{s}', bfirst=f'NC3-s{s}', btot=f'NC3-s{s}', W=9000, group='v3c3', form='ours_9000'))
        P.append(dict(name=f'P-B v3c3-s{s}', arm=f'B-s{s}', base=f'NC3-s{s}', bfirst=f'NC3-s{s}', btot=f'NC3-s{s}', W=9000, group='v3c3', form='ours_9000'))
        P.append(dict(name=f'P-VSL v3c3-s{s}', arm=f'VSL-s{s}', base=f'NC3-s{s}', bfirst=f'NC3-s{s}', btot=f'NC3-s{s}', W=9000, group='v3c3', form='ours_9000'))
        P.append(dict(name=f'P-J1 v3c3-s{s} (참고)', arm=f'J1-s{s}', base=f'NC3-s{s}', bfirst=f'NC3-s{s}', btot=f'NC3-s{s}', W=9000, group='v3c3-ref', form='ours_9000'))
    for k, nm in (('joint', 'Q-joint'), ('window', 'Q-window'), ('off', 'Q-off'), ('fw', 'Q-fw'), ('urb', 'Q-urb')):
        P.append(dict(name=f'{nm} 64cf-s29', arm=k, base='LNC', bfirst='cxNC', btot='cxNC', bmeter='cxNC', W=8100, group='64cf', form='codex_8100'))
    P.append(dict(name='Q-A1 (A1 − LNC) 64cf-s29 (참고)', arm='A1', base='LNC', bfirst='LNC', btot='read:A1-LNC', W=8100, group='64cf-ref', form='codex_8100'))
    P.append(dict(name='Q-A1 (A1 − joint) 64cf-s29 (참고)', arm='A1', base='joint', bfirst='joint', btot='read:A1-joint', W=8100, group='64cf-ref', form='codex_8100'))
    P.append(dict(name='Q-VSL64 (vsl_repro vsl − LNC) 64cf-s29 (참고, bin 꼴)', arm='vsl64', base='LNC', bfirst='LNC', btot='bin', W=8100, group='64cf-ref', form='bin_8100'))
    return P


# [읽음 CH/a1/A1_RESULT.md:255-276] totals for Q-A1 (not recounted, PRE 5.4)
A1_READ = {
    'read:A1-LNC': dict(O701=-505.7, A4a=-464.1, U=-235.1, A4=-699.2, outa=-193.5, outb=41.6, FWE7=-251.1, L19=-181.8, u1098=94.8,
                        src='CH/a1/A1_RESULT.md:255-276 (A1 − LNC 열)'),
    'read:A1-joint': dict(O701=-11.0, A4a=-15.1, U=-13.8, A4=-28.9, outa=-17.9, outb=-4.1, FWE7=32.5, L19=-25.3, u1098=-2.1,
                          src='CH/a1/A1_RESULT.md:255-276 (A1 − joint 열)'),
}

# [읽음] known pair values for reproduction checks (PRE_FWE section 4; tolerance 0.15 for 0.1-rounded table values)
KNOWN = {
    'P-VA': dict(O701=(-240.6, -421.7, -309.5), A4=(-373.9, -506.2, -356.4), outa=(-133.3, -84.5, -46.9), FWE7=(-12.3, -72.6, -5.3),
                 L19=(-51.5, -187.1, -92.5), u1098=(214.1, -0.9, 63.8)),
    'P-B': dict(O701=(-157.0, -523.4, -222.2), A4=(175.1, -230.6, -450.6), outa=(332.1, 292.9, -228.4), FWE7=(-37.3, -178.1, -88.9),
                L19=(28.2, -245.2, -34.7), u1098=(-25.5, -19.3, -113.5)),
    'P-VSL': dict(O701=(70.3, -162.0, -50.5), A4=(10.6, 68.6, -109.9), outa=(-59.8, 230.6, -59.4), FWE7=(36.1, -126.1, -8.0),
                  L19=(67.8, -184.0, -45.3), u1098=(-2.3, 89.0, -121.9)),
    'Q-joint': dict(O701=(-494.7,), A4=(-670.3,), outa=(-175.6,), FWE7=(-283.7,), L19=(-156.6,), u1098=(97.0,)),
    'Q-window': dict(FWE7=(-264.6,), L19=(-94.2,)), 'Q-off': dict(FWE7=(-301.5,), L19=(-147.6,)),
    'Q-fw': dict(FWE7=(-351.8,), L19=(-130.1,)), 'Q-urb': dict(FWE7=(721.4,), L19=(733.7,)),
}


# ---------------------------------------------------------------- per-arm loaders
def fwe_windows(d, W):
    """300 s windows of a fwe_scan dict: veh.h (bin form) for chain/zones/links, merge counts, ins, qmax, frames."""
    nwin = W // 300
    nb = d['nb']
    zb = {z: [b for b in range(nb) if a <= (b + 0.5) * d['bin_m'] < e] for z, (a, e) in ZONES.items()}
    out = dict(nwin=nwin, chain=[], zones={z: [] for z in ZONES}, frames=[], ins=[],
               merge={r: [] for r in ENTRY_CONN}, conn_stock={r: [] for r in ENTRY_CONN}, conn_q={r: [] for r in ENTRY_CONN},
               from_stock={r: [] for r in ENTRY_CONN}, from_q={r: [] for r in ENTRY_CONN}, ramp_qmax={r: [] for r in ENTRY_CONN},
               off_stock={o: [] for o in EXIT_CONN}, off_q={o: [] for o in EXIT_CONN})
    for k in range(nwin):
        ws = range(5 * k, 5 * k + 5)
        out['chain'].append(sum(sum(d['gN'][w]) for w in ws) * VFH)
        for z, bs in zb.items():
            out['zones'][z].append(sum(d['gN'][w][b] for w in ws for b in bs) * VFH)
        out['frames'].append(sum(d['frames'][w] for w in ws))
        out['ins'].append(sum(d['ins'][w] for w in ws))
        for r in ENTRY_CONN:
            s = str(r)
            out['merge'][r].append(sum(d['merge'][s][w] for w in ws))
            out['conn_stock'][r].append(sum(d['conn_stock'][s][w] for w in ws) * VFH)
            out['conn_q'][r].append(sum(d['conn_q'][s][w] for w in ws) * VFH)
            out['from_stock'][r].append(sum(d['from_stock'][s][w] for w in ws) * VFH)
            out['from_q'][r].append(sum(d['from_q'][s][w] for w in ws) * VFH)
            out['ramp_qmax'][r].append(max(d['ramp_qmax'][s][w] for w in ws))
        for o in EXIT_CONN:
            s = str(o)
            out['off_stock'][o].append(sum(d['off_stock'][s][w] for w in ws) * VFH)
            out['off_q'][o].append(sum(d['off_q'][s][w] for w in ws) * VFH)
    # pre-window rows must be absent beyond W: report frames after W (sanity)
    out['frames_after_W'] = sum(d['frames'][5 * nwin:])
    return out


def link_stock_windows(fw):
    """12 local links (2 minus 1) per 300 s window, veh.h, from fwe_scan stock arrays."""
    L = {}
    for r in ENTRY_CONN:
        L[r] = fw['conn_stock'][r]
        L[APPROACH[r]] = fw['from_stock'][r]
    for o in EXIT_CONN:
        L[o] = fw['off_stock'][o]
    return L


def first_cum_area(fs, W, cats=('74',)):
    """per 300 s window [a, b): integral of the first-seen cumulative count I(t) dt / 3600 (veh.h); + S_int(W)."""
    nwin = W // 300
    ev = []
    for c, dd in fs['by_cat'].items():
        if c not in cats:
            continue
        for tt, n in dd.items():
            ev.append((int(tt) / 10.0, n))
    win = [0.0] * nwin
    for t, n in ev:
        if t > W:
            continue
        for k in range(nwin):
            a, b = 300 * k, 300 * (k + 1)
            if t < b:
                win[k] += n * (b - max(a, t))
    win = [x / 3600.0 for x in win]
    s_int = sum(n * (W - t) for t, n in ev if t <= W) / 3600.0
    return win, s_int


def S_int(fs, W, cats=None):  # same rule as CW/vhr/vhr_unins.py:15-24 (re-implemented; that file writes on import)
    tot = 0.0
    for c, dd in fs['by_cat'].items():
        if cats is not None and c not in cats:
            continue
        for tt, k in dd.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t)
    return tot / 3600


def meter_cycles(spec, invrun, W):
    """{meter id: [(cycle_start, green)]} for FW_E and FW_W meters; plus provenance."""
    kind = spec['meter'][0]
    if kind == 'rb':
        path, run = spec['meter'][1], spec['meter'][2]
        res = {}
        with open(path, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if row['run'] != run:
                    raise ValueError(f'readback run column {row["run"]} != {run}')
                c = int(float(row['cycle_start']))
                if 900 <= c < W:
                    res.setdefault(row['meter'], []).append((c, int(row['obs_green_count'])))
        for m in res:
            res[m].sort()
        return res, dict(kind='readback obs_green_count', file=path, sha256=sha(path))
    if kind == 'ldp':
        res = {}
        files = {}
        for e in invrun['meter_ldp']:
            p = e['path']
            sc = int(p.rsplit('_', 2)[-2])
            m = ML.METERS[sc]
            got = sha(p)
            if got != e['sha256']:
                raise ValueError(f'LDP sha mismatch {p}')
            stt = ML.ldp_states(p)
            cy = ML.cycles_from_states(stt, 900, W)
            bl = ML.blank_per_cycle(stt, 900, W)
            miss = sum(x[2] for x in cy)
            res[m] = [(c, g) for c, g, _ in cy]
            files[m] = dict(path=p, sha256=got, missing_seconds=miss, blank_seconds=sum(b for _, b in bl),
                            all_blank=all(b == 10 for _, b in bl),
                            whole_file_states={k: sum(1 for v in stt.values() if v == k) for k in sorted(set(stt.values()))})
        return res, dict(kind='LDP state I (rm_exec rule)', files=files)
    return None, dict(kind=kind, note=spec['meter'][1])


def meter_summary(cy, W):
    nwin = W // 300
    if cy is None:
        return None
    t10 = next((c for c, g in cy if g < 10), None)
    t6 = next((c for c, g in cy if g <= 6), None)
    hist = {g: sum(1 for _, x in cy if x == g) for g in range(11)}
    win_frac = []
    win_mean = []
    for k in range(nwin):
        cs = [g for c, g in cy if 300 * k <= c < 300 * (k + 1)]
        win_frac.append(None if not cs else sum(1 for g in cs if g < 10) / 30.0)
        win_mean.append(None if not cs else sum(cs) / len(cs))
    return dict(n_cycles=len(cy), n_tight10=sum(1 for _, g in cy if g < 10), n_le6=sum(1 for _, g in cy if g <= 6),
                T_tight10=t10, T_tight6=t6, green_hist=hist, win_tight_frac=win_frac, win_mean_green=win_mean,
                green_seconds_total=sum(g for _, g in cy))


def gain_times(d1, t0w=3, thr_a=-2.0, thr_b=-5.0):
    """R2-f on per-window d1 list (index k = window start 300k). Returns dict with window starts (s)."""
    n = len(d1)
    ta = next((300 * k for k in range(t0w, n) if d1[k] <= thr_a), None)
    cum = []
    c = 0.0
    for k in range(t0w, n):
        c += d1[k]
        cum.append(c)
    tb = None
    for i in range(len(cum)):
        if all(x <= thr_b for x in cum[i:]):
            tb = 300 * (i + t0w)
            break
    final = cum[-1] if cum else 0.0
    th = None
    if final < 0:
        th = next((300 * (i + t0w) for i, x in enumerate(cum) if x <= final / 2.0), None)
    return dict(T_gain_a=ta, T_gain_b=tb, T_half=th, cum_d1_from_900=cum, final_cum=final)


def totals_from_vhr(vhr, form, O701):
    I = vhr['integrals'][form]
    return dict(O701=sum(v for l, v in I.items() if int(l) in O701), FWE7=sum(v for l, v in I.items() if int(l) in S7),
                L19=sum(v for l, v in I.items() if int(l) in S19), A4a=sum(I.values()))


def totals_from_lb(lb, W, O701):
    nb = int(W // lb['bin_s'])
    tot = {}
    for l, arr in lb['vf'].items():
        tot[int(l)] = sum(arr[:nb]) * VFH
    return dict(O701=sum(v for l, v in tot.items() if l in O701), FWE7=sum(v for l, v in tot.items() if l in S7),
                L19=sum(v for l, v in tot.items() if l in S19), A4a=sum(tot.values()))


def npz_check(npz_path, fw, W):
    """S-8 style (report only): npz bin form (t >= 1.0, frame-count x 5 s) per 300 s window for chain and 12 local links."""
    import numpy as np
    z = np.load(npz_path, allow_pickle=False)
    t = z['t']
    links = list(z['links'])
    M = z['M']
    keep = (t >= 1.0) & (t < W)
    nwin = W // 300
    col = {l: links.index(l) for l in (list(S7) + LOCAL12) if l in links}
    res = dict(max_abs_chain_win=0.0, max_abs_link_win=0.0, total_chain_npz=0.0, total_chain_fwe=sum(fw['chain']))
    L = link_stock_windows(fw)
    for k in range(nwin):
        m = keep & (t >= 300 * k) & (t < 300 * (k + 1))
        ch = sum(int(M[m, col[l]].sum()) for l in S7 if l in col) * VFH
        res['total_chain_npz'] += ch
        res['max_abs_chain_win'] = max(res['max_abs_chain_win'], abs(ch - fw['chain'][k]))
        for l in LOCAL12:
            v = int(M[m, col[l]].sum()) * VFH if l in col else 0.0
            res['max_abs_link_win'] = max(res['max_abs_link_win'], abs(v - L[l][k]))
    return res


def lb_check(lb, fw, W):
    nwin = W // 300
    res = dict(max_abs_chain_win=0.0, max_abs_link_win=0.0, max_abs_q_link_win=0.0)
    L = link_stock_windows(fw)
    Q = {}
    for r in ENTRY_CONN:
        Q[r] = fw['conn_q'][r]
        Q[APPROACH[r]] = fw['from_q'][r]
    for o in EXIT_CONN:
        Q[o] = fw['off_q'][o]
    for k in range(nwin):
        bs = (2 * k, 2 * k + 1)
        ch = sum(lb['vf'].get(str(l), [0] * 60)[b] for l in S7 for b in bs) * VFH
        res['max_abs_chain_win'] = max(res['max_abs_chain_win'], abs(ch - fw['chain'][k]))
        for l in LOCAL12:
            v = sum(lb['vf'].get(str(l), [0] * 60)[b] for b in bs) * VFH
            q = sum(lb['qf'].get(str(l), [0] * 60)[b] for b in bs) * VFH
            res['max_abs_link_win'] = max(res['max_abs_link_win'], abs(v - L[l][k]))
            res['max_abs_q_link_win'] = max(res['max_abs_q_link_win'], abs(q - Q[l][k]))
    return res


def vsl_decisions(action_csv, W):
    """R3-h: FW_E VSL rows with speed < 110 grouped by decision time (sim_sec)."""
    times = {}
    n_rows = 0
    n_fwe = 0
    with open(action_csv, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['kind'] != 'vsl' or not r['id'].startswith('RW_FW_E'):
                continue
            n_fwe += 1
            sp = float(r['speed_kph'])
            if sp < 110:
                n_rows += 1
                t = int(float(r['sim_sec']))
                times.setdefault(t, set()).add((r['id'], sp))
    dec = sorted(times)
    return dict(n_fwe_vsl_rows=n_fwe, n_rows_lt110=n_rows, decisions_lt110=dec,
                detail={t: sorted(f'{i}:{s:g}' for i, s in v) for t, v in times.items()})


def r(x, n=3):
    return None if x is None else round(x, n)


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    checks = dict(pre_sha=sha(FD + '/PRE_FWE.md'))
    if checks['pre_sha'] != PRE_SHA:
        raise SystemExit('PRE_FWE sha mismatch')
    om_path = H + '/derived/omega_membership_exact.json'
    if sha(om_path) != OMEGA_SHA:
        raise SystemExit('omega membership sha mismatch')
    O701 = set(int(x) for x in jload(om_path)['inside_links'])
    A = arm_specs()
    P = pair_specs()
    arms = {}
    missing = {}
    for k, s in A.items():
        inv = inv_run(*s['inv'])
        a = dict(key=k, net=s['net'], seed=inv['provenance']['seed'], prov_sha=inv['provenance']['sha256'],
                 inpx_sha=(inv.get('inpx') or {}).get('sha256'), fzp=inv['fzp']['path'], fzp_sha_inv=inv['fzp_sha256_cached'])
        if s['fwe']:
            if os.path.exists(s['fwe']):
                d = jload(s['fwe'])
                a['fwe_file'] = s['fwe']
                a['fwe_file_sha256'] = sha(s['fwe'])
                a['fwe_fzp_sha256'] = d['fzp_sha256']
                a['fwe_sha_ok'] = d['fzp_sha256'] in inv['fzp_sha256_cached']
                if not a['fwe_sha_ok']:
                    missing[k + ':fwe'] = 'S-1 FZP sha mismatch'
                else:
                    a['_fwd'] = d
            else:
                missing[k + ':fwe'] = 'file missing (heavy output not ready)'
        if s['first']:
            if os.path.exists(s['first']):
                a['_first'] = jload(s['first'])
                a['first_file'] = s['first']
                a['first_file_sha256'] = sha(s['first'])
            else:
                missing[k + ':first'] = 'file missing (heavy output not ready)'
        if s.get('vhr'):
            a['_vhr'] = jload(s['vhr'])
            a['vhr_file'] = s['vhr']
            a['vhr_file_sha256'] = sha(s['vhr'])
            if a['_vhr']['file_sha256'] not in inv['fzp_sha256_cached'] and inv['fzp_sha256_cached']:
                missing[k + ':vhr'] = 'vhr FZP sha mismatch'
        if s.get('lb'):
            a['_lb'] = jload(s['lb'])
            a['lb_file'] = s['lb']
            a['lb_file_sha256'] = sha(s['lb'])
        a['_spec'] = s
        a['_inv'] = inv
        arms[k] = a
    out = dict(tool='fwe_r3.py', tool_sha256=sha(__file__), meter_tool_sha256=sha(FD + '/tools/fwe_meter_ldp.py'),
               pre_fwe_sha256=PRE_SHA, started=time.strftime('%Y-%m-%d %H:%M:%S KST'), checks=checks, missing=missing,
               arms={}, pairs={})
    # per-arm: fwe windows (for both W used), meters, vsl decisions
    Ws = {'v3c3': 9000, '64cf': 8100}
    for k, a in arms.items():
        W = Ws[a['net']]
        rec = {x: a.get(x) for x in ('net', 'seed', 'prov_sha', 'inpx_sha', 'fzp', 'fzp_sha_inv', 'fwe_file', 'fwe_file_sha256',
                                      'fwe_fzp_sha256', 'fwe_sha_ok', 'first_file', 'first_file_sha256', 'vhr_file', 'vhr_file_sha256',
                                      'lb_file', 'lb_file_sha256') if a.get(x) is not None}
        if '_fwd' in a:
            a['_fw'] = fwe_windows(a['_fwd'], W)
            rec['frames_after_W'] = a['_fw']['frames_after_W']
            rec['fwe_windows'] = {kk: (vv if not isinstance(vv, dict) else {str(x): y for x, y in vv.items()})
                                  for kk, vv in a['_fw'].items() if kk not in ('nwin',)}
        cy, prov = meter_cycles(a['_spec'], a['_inv'], W)
        a['_cy'] = cy
        rec['meter_source'] = prov
        if cy is not None:
            rec['meters'] = {m: meter_summary(cy.get(m), W) for m in list(FWE_METERS) + list(FWW_METERS)}
            # data-after annotation (2026-10-27 R3): an LDP with blank state in every second records no SG state.
            for m, ms in rec['meters'].items():
                fi = (prov.get('files') or {}).get(m)
                if ms is not None and fi is not None and fi['all_blank']:
                    ms['state_none'] = True
                    ms['note'] = 'LDP 전 구간 빈칸(신호 상태 기록 없음): GREEN 규칙 값은 0 이지만 조임으로 읽지 않음 [데이터 뒤]'
            rec['meter_cycles'] = {m: cy.get(m) for m in list(FWE_METERS) + list(FWW_METERS)}
        act = (a['_inv'].get('action') or {}).get('path')
        if act and a['net'] == 'v3c3' and k.split('-')[0] in ('VA', 'B', 'J1'):
            rec['vsl_fwe'] = vsl_decisions(act, W)
            rec['vsl_fwe']['action_csv'] = act
            rec['vsl_fwe']['action_sha256'] = sha(act)
        # report-only cross-checks (S-8 style): fwe stock vs npz / linkbin
        if '_fw' in a and a['_spec'].get('npz') and os.path.exists(a['_spec']['npz']):
            rec['check_npz_vs_fwe'] = npz_check(a['_spec']['npz'], a['_fw'], W)
        if '_fw' in a and a.get('_lb') is not None:
            rec['check_linkbin_vs_fwe'] = lb_check(a['_lb'], a['_fw'], W)
        out['arms'][k] = rec
    # S-4 (b) per run: totals (form) - window sums of 1 and 2
    s4 = {}
    for k, a in arms.items():
        if '_fw' not in a:
            continue
        W = Ws[a['net']]
        form = 'ours_9000' if a['net'] == 'v3c3' else 'codex_8100'
        fw = a['_fw']
        w1 = sum(fw['chain'])
        L = link_stock_windows(fw)
        w2 = w1 + sum(sum(L[l]) for l in LOCAL12)
        if a.get('_vhr') is not None:
            tt = totals_from_vhr(a['_vhr'], form, O701)
        elif a.get('_lb') is not None:
            tt = totals_from_lb(a['_lb'], W, O701)
            form = 'bin_linkbin'
        elif k == 'A1':
            res_ = jload(f'{CW}/a1/full/scan/a1.json')['link_residence_veh_h']
            tt = dict(FWE7=sum(v for l, v in res_.items() if int(l) in S7), L19=sum(v for l, v in res_.items() if int(l) in S19))
            form = 'a1.json link_residence_veh_h (0-8100)'
        else:
            continue
        s4[k] = dict(form=form, d1=r(tt['FWE7'] - w1, 4), d2=r(tt['L19'] - w2, 4),
                     stop=abs(tt['FWE7'] - w1) > 1.0 or abs(tt['L19'] - w2) > 1.0)
    out['checks']['S4b_runs'] = s4
    # pairs
    for p in P:
        A_, B_ = arms[p['arm']], arms[p['base']]
        W = p['W']
        nwin = W // 300
        res = dict(arm=p['arm'], base_phys=p['base'], base_first=p['bfirst'], base_totals=p['btot'], W=W, group=p['group'], form=p['form'])
        # S-2 seeds
        seeds = {A_['seed'], B_['seed'], arms[p['bfirst']]['seed']}
        res['S2_seed_ok'] = len(seeds) == 1
        res['seed'] = A_['seed']
        if not res['S2_seed_ok']:
            res['stopped'] = 'S-2 seed mismatch'
            out['pairs'][p['name']] = res
            continue
        have_fw = '_fw' in A_ and '_fw' in B_
        s4stop = [x for x in (p['arm'], p['base']) if s4.get(x, {}).get('stop')]
        if s4stop:
            res['S4_stop_runs'] = s4stop
            have_fw = False
        have_first = '_first' in A_ and '_first' in arms[p['bfirst']]
        # ---- totals (R3-g inputs) ----
        tot = None
        if p['btot'].startswith('read:'):
            tot = dict(A1_READ[p['btot']])
            tot['how'] = '[읽음] ' + tot.pop('src')
        elif p['btot'] == 'bin':
            if have_first:
                ta, tb = totals_from_lb(A_['_lb'], W, O701), totals_from_lb(arms[p['base']]['_lb'], W, O701)
                tot = {x: ta[x] - tb[x] for x in ta}
                fb = arms[p['bfirst']]['_first']
                tot['U'] = S_int(fb, W) - S_int(A_['_first'], W)
                tot['u1098'] = S_int(fb, W, {'74'}) - S_int(A_['_first'], W, {'74'})
                tot['u1099'] = S_int(fb, W, {'26'}) - S_int(A_['_first'], W, {'26'})
                tot['how'] = '[실행] bin 꼴(linkbin vf, t<8100) + 첫 관측 차분'
        else:
            if have_first:
                ta = totals_from_vhr(A_['_vhr'], p['form'], O701)
                tb = totals_from_vhr(arms[p['btot']]['_vhr'], p['form'], O701)
                tot = {x: ta[x] - tb[x] for x in ta}
                fb = arms[p['bfirst']]['_first']
                tot['U'] = S_int(fb, W) - S_int(A_['_first'], W)
                tot['u1098'] = S_int(fb, W, {'74'}) - S_int(A_['_first'], W, {'74'})
                tot['u1099'] = S_int(fb, W, {'26'}) - S_int(A_['_first'], W, {'26'})
                tot['how'] = f"[실행] vhr 링크 적분 {p['form']} + 첫 관측 차분(vhr_unins 규칙)"
        if tot is not None and 'A4' not in tot:
            tot['A4'] = tot['A4a'] + tot['U']
            tot['outa'] = tot['A4'] - tot['O701']
            tot['outb'] = tot['A4a'] - tot['O701']
        if tot is not None:
            tot['O701_minus_L19'] = tot['O701'] - tot['L19']
            res['totals'] = {x: (r(v) if isinstance(v, float) else v) for x, v in tot.items()}
            kn = KNOWN.get(p['name'].split(' ')[0])
            if kn:
                idx = {31: 0, 41: 1, 43: 2, 29: 0}[res['seed']]
                res['known_check'] = {m: dict(mine=r(tot[m], 2), known=v[idx], diff=r(tot[m] - v[idx], 3), ok=abs(tot[m] - v[idx]) <= 0.15)
                                      for m, v in kn.items() if m in tot}
        else:
            res['totals'] = 'not produced (first-seen missing)'
        if not have_fw:
            res['windows'] = 'not produced (fwe_scan missing for arm or base)'
        else:
            fa, fb = A_['_fw'], B_['_fw']
            d1 = [fa['chain'][k] - fb['chain'][k] for k in range(nwin)]
            dz = {z: [fa['zones'][z][k] - fb['zones'][z][k] for k in range(nwin)] for z in ZONES}
            gt = gain_times(d1)
            G = [k for k in range(3, nwin) if d1[k] <= -2.0]
            res['d1_win'] = [r(x) for x in d1]
            res['d1_zone_win'] = {z: [r(x) for x in v] for z, v in dz.items()}
            res['gain'] = {x: (r(v) if isinstance(v, float) else ([r(y) for y in v] if isinstance(v, list) else v)) for x, v in gt.items()}
            res['G_windows'] = [300 * k for k in G]
            # S-14 report only: pre-900 local |d|
            La, Lb = link_stock_windows(fa), link_stock_windows(fb)
            pre = sum(abs(La[l][k] - Lb[l][k]) for l in LOCAL12 for k in range(3)) + sum(abs(d1[k]) for k in range(3))
            res['S14_pre900_abs_d_L19'] = r(pre, 4)
            res['S14_flag'] = pre > 0.05
            # S-4 (b): totals - window sums for 1 and 2 (per run), report and stop flag
            # ---- R3-c merge flows ----
            res['merge_vph'] = {r_: dict(arm=[x * 12 for x in fa['merge'][r_]], base=[x * 12 for x in fb['merge'][r_]],
                                         d=[(fa['merge'][r_][k] - fb['merge'][r_][k]) * 12 for k in range(nwin)]) for r_ in ENTRY_CONN}
            # ---- R3-d ramp/approach stock ----
            rd = {}
            for r_ in ENTRY_CONN:
                rr = {}
                for q in ('conn_stock', 'conn_q', 'from_stock', 'from_q'):
                    rr[q] = dict(arm=[r(x, 4) for x in fa[q][r_]], base=[r(x, 4) for x in fb[q][r_]],
                                 d=[r(fa[q][r_][k] - fb[q][r_][k], 4) for k in range(nwin)],
                                 d_total=r(sum(fa[q][r_]) - sum(fb[q][r_])))
                rr['ramp_qmax'] = dict(arm=fa['ramp_qmax'][r_], base=fb['ramp_qmax'][r_])
                rr['meter_side_total_d'] = r(sum(fa['conn_stock'][r_]) + sum(fa['from_stock'][r_]) - sum(fb['conn_stock'][r_]) - sum(fb['from_stock'][r_]))
                rr['meter_side_q_total_d'] = r(sum(fa['conn_q'][r_]) + sum(fa['from_q'][r_]) - sum(fb['conn_q'][r_]) - sum(fb['from_q'][r_]))
                rd[r_] = rr
            res['ramp'] = rd
            res['exit'] = {o: dict(d=[r(fa['off_stock'][o][k] - fb['off_stock'][o][k], 4) for k in range(nwin)],
                                   d_q=[r(fa['off_q'][o][k] - fb['off_q'][o][k], 4) for k in range(nwin)],
                                   d_total=r(sum(fa['off_stock'][o]) - sum(fb['off_stock'][o])),
                                   d_q_total=r(sum(fa['off_q'][o]) - sum(fb['off_q'][o])),
                                   d_pos_windows=[300 * k for k in range(nwin) if fa['off_stock'][o][k] - fb['off_stock'][o][k] > 0],
                                   d_pos_sum=r(sum(max(0.0, fa['off_stock'][o][k] - fb['off_stock'][o][k]) for k in range(nwin))))
                          for o in EXIT_CONN}
            res['ins74_vph'] = dict(arm=[x * 12 for x in fa['ins']], base=[x * 12 for x in fb['ins']],
                                    d=[(fa['ins'][k] - fb['ins'][k]) * 12 for k in range(nwin)])
            # ---- R3-g top-10 local link x window cells with d > 0 ----
            cells = []
            for l in LOCAL12:
                for k in range(nwin):
                    dv = La[l][k] - Lb[l][k]
                    if dv > 0:
                        cells.append((dv, l, 300 * k))
            cells.sort(key=lambda x: (-x[0], x[1], x[2]))
            res['cost_top10_local_cells'] = [dict(link=l, win_start=w, d=r(dv), side=('entry_conn' if l in ENTRY_CONN else ('approach' if l in APPROACH.values() else 'exit_conn')))
                                             for dv, l, w in cells[:10]]
            res['cost_local_pos_sum'] = r(sum(c[0] for c in cells))
            res['local_link_total_d'] = {l: r(sum(La[l]) - sum(Lb[l])) for l in LOCAL12}
            res['d_entry_side_win'] = [r(sum(La[l][k] - Lb[l][k] for l in ENTRY_CONN + [APPROACH[x] for x in ENTRY_CONN]), 4) for k in range(nwin)]
            res['d_exit_side_win'] = [r(sum(La[l][k] - Lb[l][k] for l in EXIT_CONN), 4) for k in range(nwin)]
            res['d2_bin_win'] = [r(d1[k] + res['d_entry_side_win'][k] + res['d_exit_side_win'][k], 4) for k in range(nwin)]
            # S-4 (b) per pair: totals - window sums (difference of runs) for 1 and 2
            if isinstance(res.get('totals'), dict) and p['btot'] != 'bin':
                s1 = sum(d1)
                s2 = s1 + sum(La[l][k] - Lb[l][k] for l in LOCAL12 for k in range(nwin))
                res['S4b_pair'] = dict(d1_total_minus_winsum=r(tot['FWE7'] - s1, 4), d2_total_minus_winsum=r(tot['L19'] - s2, 4),
                                       note='총합 꼴(' + p['form'] + ') − bin 꼴 창 합; 런별 값은 arms.*.S4b')
        # ---- R3-e entry wait 1098 by window ----
        if have_first:
            fa_, fb_ = A_['_first'], arms[p['bfirst']]['_first']
            wa, sa = first_cum_area(fa_, W)
            wb, sb = first_cum_area(fb_, W)
            dwin = [wb[k] - wa[k] for k in range(nwin)]
            dU = S_int(fb_, W, {'74'}) - S_int(fa_, W, {'74'})
            res['u1098_win'] = [r(x, 4) for x in dwin]
            res['u1098_sum'] = r(sum(dwin), 4)
            res['u1098_dU'] = r(dU, 4)
            res['S6_ok'] = abs(sum(dwin) - dU) <= 0.05
            res['u1098_pos_windows'] = [300 * k for k in range(nwin) if dwin[k] > 0]
            res['u1098_pos_sum'] = r(sum(x for x in dwin if x > 0))
        else:
            res['u1098_win'] = 'not produced (first-seen missing)'
        # ---- meters of the arm and base (R3-a, R3-b) and R3-f timing ----
        res['meter_arm'] = {m: (out['arms'][p['arm']].get('meters') or {}).get(m) for m in FWE_METERS} if out['arms'][p['arm']].get('meters') else out['arms'][p['arm']]['meter_source']
        bm = p.get('bmeter', p['base'])
        res['meter_base_source'] = bm
        res['meter_base'] = {m: (out['arms'][bm].get('meters') or {}).get(m) for m in FWE_METERS} if out['arms'][bm].get('meters') else out['arms'][bm]['meter_source']
        if have_fw:
            tf = {}
            for m in FWE_METERS:
                ms = res['meter_arm'].get(m) if isinstance(res['meter_arm'], dict) and m in res['meter_arm'] else None
                t10 = ms['T_tight10'] if ms else None
                if ms is not None and ms.get('state_none'):
                    tf[m] = '상태 기록 없음(LDP 빈칸) — 조임 아님 [데이터 뒤]'
                elif ms is None and A_['_spec']['meter'][0] == 'read':
                    tf[m] = '조임 없음 [읽음 SP/rmcause/METER_CAUSE.md:18]'
                elif ms is None:
                    tf[m] = '미터 기록 없음'
                elif t10 is None:
                    tf[m] = '조임 없음'
                else:
                    tf[m] = dict(T_tight10=t10, a_minus=(None if gt['T_gain_a'] is None else gt['T_gain_a'] - t10),
                                 b_minus=(None if gt['T_gain_b'] is None else gt['T_gain_b'] - t10))
            res['timing'] = tf
            # ---- section 6 inputs over G (no flags computed here) ----
            cyc = arms[p['arm']].get('_cy')
            g6 = dict(G_n=len(G))
            if G:
                gs = set(G)
                for m, (sc, conn) in FWE_METERS.items():
                    if (res['meter_arm'].get(m) or {}).get('state_none') if isinstance(res['meter_arm'], dict) else False:
                        g6[f'{m}_G_tight_frac'] = 'state_none'
                    elif cyc and cyc.get(m):
                        cs = [g for c, g in cyc[m] if (c // 300) in gs]
                        g6[f'{m}_G_tight_frac'] = r(sum(1 for g in cs if g < 10) / len(cs), 4) if cs else None
                    am = sum(fa['merge'][conn][k] for k in G) * 3600.0 / (300.0 * len(G))
                    bmv = sum(fb['merge'][conn][k] for k in G) * 3600.0 / (300.0 * len(G))
                    g6[f'merge_{conn}_G_vph_arm'] = r(am, 1)
                    g6[f'merge_{conn}_G_vph_base'] = r(bmv, 1)
                    g6[f'merge_{conn}_G_dvph'] = r(am - bmv, 1)
                    g6[f'd1_{MERGE_ZONE[conn]}_G'] = r(sum(dz[MERGE_ZONE[conn]][k] for k in G))
                for o in (10643, 10481):
                    g6[f'd_stock_{o}_G'] = r(sum(fa['off_stock'][o][k] - fb['off_stock'][o][k] for k in G))
                g6['d1_U_B1_G'] = r(sum(dz['U'][k] + dz['B1'][k] for k in G))
                g6['d1_M_B2_G'] = r(sum(dz['M'][k] + dz['B2'][k] for k in G))
                g6['d1_U_G'] = r(sum(dz['U'][k] for k in G))
                if have_first:
                    g6['d_u1098_G'] = r(sum(dwin[k] for k in G))
                vs = out['arms'][p['arm']].get('vsl_fwe')
                if vs is not None:
                    g6['vsl_lt110_decisions_overlapping_G'] = sum(1 for t in vs['decisions_lt110'] if any(300 * k < t + 150 and t < 300 * (k + 1) for k in G))
            res['sec6_inputs_over_G'] = g6
        out['pairs'][p['name']] = res
    out['vsl_notes'] = dict(
        B='110 고정 [읽음 PRE_FWE §5.3 R3-h; 확인 = arms.B-s*.vsl_fwe.n_rows_lt110]',
        VSL='v3c3 VSL 팔 = 900 s 부터 91 고정 [읽음 SP/vsl_v3c3/VSL_RESULTS.md §1.8, PRE_FWE §5.3 R3-h]',
        VA='arms.VA-s*.vsl_fwe (run action CSV kind=vsl, id RW_FW_E*, speed_kph<110)')
    ad = {}
    for k in ('joint', 'window', 'off', 'fw', 'urb', 'A1'):
        act = (arms[k]['_inv'].get('action') or {}).get('path')
        if act:
            v = vsl_decisions(act, 8100)
            v['action_csv'] = act
            v['action_sha256'] = sha(act)
            ad[k] = v
    out['after_data_vsl_fwe_64cf'] = dict(label='PRE 밖 추가(데이터 전 LOG 선언, 보고만): codex 팔의 FW_E VSL<110 결정', arms=ad)
    out['checks']['S6_all_ok'] = all(v.get('S6_ok', True) for v in out['pairs'].values() if isinstance(v, dict))
    out['elapsed_s'] = round(time.time() - t0, 1)
    tmp = FD + '/out/R3_meters.json.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    os.replace(tmp, FD + '/out/R3_meters.json')
    print('ok', out['elapsed_s'], 'missing', missing)


if __name__ == '__main__':
    main()
