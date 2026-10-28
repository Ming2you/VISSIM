"""vsl_plant analysis (PRE_VP sections 3.5, 4.4, 5.4, 6).  Light: reads probe / hook / scan outputs only.

    python -B vp_analyze.py specs-a <out_dir>                  probe A/B job specs (no data)
    python -B vp_analyze.py p1-fzp <out.json>                  P1-F FZP profiles of the scans that exist (light)
    python -B vp_analyze.py p1-inputs <out_dir>                C1 / C7 inputs + P1 job specs (needs the FZP scans)
    python -B vp_analyze.py tables <out.json> <out.md>         all tables and stop-rule flags

Definitions (fixed before data, PRE_VP).  Cells = the 31 FW_E plant cells (CELL_B), zones = vp_common.ZONES.
  plant block b of a rollout from T: hook steps with T+150b <= t < T+150(b+1); per cell stock = n_dt/dt (veh),
      speed = nv_dt/n_dt (km/h, vehicle weighted), flow = q_dt/dt (veh/h, all lanes).
  VISSIM block b: FZP frames with T+150b <= t < T+150(b+1) (5 s frames, o2_fzp_cells.py); per cell stock = N/frames,
      speed = SV/N, flow = SV/(L*frames) (Edie).  Fewer than 25 frames per 150 s -> None.
  zone: stock = sum, speed = sum(n v)/sum(n) (plant) or SV/N (VISSIM), flow = length-weighted mean of cell flows.
  windows: 'b0','b1','b2', 'w300' = blocks 0-1, 'w450' = blocks 0-2.   bias e = plant - VISSIM.
  sign of a J difference: |d| < 0.01 veh*h -> 0.
  reduction R_c,m = 1 - |e_c|/|e_0| (e_0 = base EXEC bias); undefined when |e_0| < 1 km/h (speed) or < 1 veh
      (stock).  Window w450 for C1-C6, b0 for C7.
  pointing rule (candidate c, metric m): n_defined >= 6 and n(R >= 0.5) >= ceil(2/3 n_defined) and median R >= 0.5.
  low density (FZP 60 s windows with 900 <= t0, t0 + 60 <= 9000, 12 frames): k = (N/12)/(L*lanes) <= 12 veh/km/lane.
"""
import glob
import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

ARMS = [110, 101, 100, 90]
ABLATIONS = ['C1_vfree', 'C2_rhocrit', 'C3_merge', 'C4_lanedrop', 'C5_capdrop', 'C6_compliance', 'C7_initial']
FOCUS = C.FOCUS_CELLS
K_LOW = 12.0
WINDOWS = {'b0': [0], 'b1': [1], 'b2': [2], 'w300': [0, 1], 'w450': [0, 1, 2]}
METRICS = {'m1_VSa_speed': ('VSa', 'speed'), 'm2_M1_speed': ('M1', 'speed'), 'm3_VSb_stock': ('VSb', 'stock'),
           'm4_VSb_speed': ('VSb', 'speed'), "m5_VS0'_speed": ("VS0'", 'speed')}
LEN_KM = [(C.CELL_B[i + 1] - C.CELL_B[i]) / 1000.0 for i in range(C.N_CELL)]


def sign(d, eps=0.01):
    if d is None:
        return None
    return '0' if abs(d) < eps else ('+' if d > 0 else '-')


def diff(a, b):
    if a is None or b is None:
        return None
    return a - b


# ------------------------------------------------------------------------------------------------ plant side
def plant_cells(hook, blocks):
    n_dt = [0.0] * C.N_CELL
    nv_dt = [0.0] * C.N_CELL
    q_dt = [0.0] * C.N_CELL
    dt = 0.0
    for b in blocks:
        blk = hook['blocks'].get(str(b))
        if blk is None:
            return None
        for i in range(C.N_CELL):
            n_dt[i] += blk['n_dt'][i]
            nv_dt[i] += blk['nv_dt'][i]
            q_dt[i] += blk['q_dt'][i]
        dt += blk['dt']
    return {'stock': [x / dt for x in n_dt], 'speed': [(y / x) if x > 0 else None for x, y in zip(n_dt, nv_dt)],
            'flow': [x / dt for x in q_dt], 'n_dt': n_dt, 'nv_dt': nv_dt, 'dt': dt}


def zone_plant(cells, zone):
    if cells is None:
        return None
    idx = C.ZONES[zone]
    n = sum(cells['n_dt'][i] for i in idx)
    nv = sum(cells['nv_dt'][i] for i in idx)
    L = sum(LEN_KM[i] for i in idx)
    return {'stock': sum(cells['stock'][i] for i in idx), 'speed': nv / n if n > 0 else None,
            'flow': sum(cells['flow'][i] * LEN_KM[i] for i in idx) / L}


# ------------------------------------------------------------------------------------------------ VISSIM frames
def vissim_cells(scan, t_lo, t_hi):
    ks = [k for k, t in enumerate(scan['frames']) if t_lo <= t < t_hi]
    need = 25 * max(1, int(round((t_hi - t_lo) / 150.0)))
    if len(ks) < need:
        return None
    N = [0.0] * C.N_CELL
    SV = [0.0] * C.N_CELL
    for k in ks:
        for c in range(C.N_CELL):
            N[c] += scan['N'][k][c]
            SV[c] += scan['SV'][k][c]
    nfr = len(ks)
    return {'N': N, 'SV': SV, 'frames': nfr, 'stock': [n / nfr for n in N],
            'speed': [(s / n) if n > 0 else None for n, s in zip(N, SV)],
            'flow': [s / (LEN_KM[i] * nfr) for i, s in enumerate(SV)]}


def zone_vissim(vc, zone):
    if vc is None:
        return None
    idx = C.ZONES[zone]
    N = sum(vc['N'][i] for i in idx)
    SV = sum(vc['SV'][i] for i in idx)
    L = sum(LEN_KM[i] for i in idx)
    return {'stock': N / vc['frames'], 'speed': SV / N if N > 0 else None, 'flow': SV / (L * vc['frames'])}


def window_tables(p_by_w, v_by_w):
    rows = {}
    for w in WINDOWS:
        p, v = p_by_w.get(w), v_by_w.get(w)
        z = {}
        for zone in C.ZONE_ORDER:
            pz, vz = zone_plant(p, zone), zone_vissim(v, zone)
            z[zone] = {'plant': pz, 'vissim': vz,
                       'e': {q: diff((pz or {}).get(q), (vz or {}).get(q)) for q in ('speed', 'flow', 'stock')}}
        cells = {}
        for i in FOCUS:
            cells[str(i)] = {}
            for q in ('speed', 'flow', 'stock'):
                a = p[q][i] if p else None
                b = v[q][i] if v else None
                cells[str(i)][q] = {'plant': a, 'vissim': b, 'e': diff(a, b)}
        rows[w] = {'zones': z, 'cells': cells}
    return rows


def rollout_windows(hook, scan, T):
    p = {w: plant_cells(hook, bl) for w, bl in WINDOWS.items()}
    v = {w: (vissim_cells(scan, T + 150 * bl[0], T + 150 * (bl[-1] + 1)) if scan else None) for w, bl in WINDOWS.items()}
    return window_tables(p, v)


def initial_bias(hook, scan, T):
    ini = ((hook or {}).get('first') or {}).get('initial') or {}
    if not ini.get('stock_veh') or scan is None:
        return None
    ks = [k for k, t in enumerate(scan['frames']) if T - 5.5 < t <= T + 0.5]
    if not ks:
        return None
    N = [sum(scan['N'][k][c] for k in ks) for c in range(C.N_CELL)]
    SV = [sum(scan['SV'][k][c] for k in ks) for c in range(C.N_CELL)]
    out = {'frames': len(ks), 'cells': {}, 'zones': {}}
    for i in FOCUS:
        vs = SV[i] / N[i] if N[i] > 0 else None
        out['cells'][str(i)] = {'e_speed': diff(ini['speed_kmh'][i], vs), 'e_stock': ini['stock_veh'][i] - N[i] / len(ks)}
    for zone in C.ZONE_ORDER:
        idx = C.ZONES[zone]
        n_p = sum(ini['stock_veh'][i] for i in idx)
        sv_p = sum(ini['stock_veh'][i] * ini['speed_kmh'][i] for i in idx)
        n_v, sv_v = sum(N[i] for i in idx), sum(SV[i] for i in idx)
        out['zones'][zone] = {'e_speed': diff(sv_p / n_p if n_p > 0 else None, sv_v / n_v if n_v > 0 else None),
                              'e_stock': n_p - n_v / len(ks)}
    return out


# ------------------------------------------------------------------------------------------------ outputs
def job_dirs(kind):
    return sorted(Path(p) for p in glob.glob(str(C.OUT / ('plant_' + kind) / '*')) if os.path.isdir(p))


def hook_for(job_dir, probe, label):
    """Hook record of one evaluation: the worker request of its batch (vp_probe make_runner) whose action token is
    the evaluated one.  Byte-identical requests (same sha) may run in two processes; then every file must carry the
    same blocks and initial state, else 'ambiguous'."""
    ev = (probe.get('evaluations') or {}).get(label)
    if ev is None:
        return None, 'no evaluation'
    tok = ev['evaluated_action_token']
    reqs = sorted({r['request_sha256'] for r in probe.get('runs') or [] if r.get('batch') == ev.get('batch')
                   and r['action_token'] == tok and r['mode'] == ev['mode'] and r.get('request_sha256')})
    if len(reqs) != 1:
        return None, 'requests %d' % len(reqs)
    files = sorted(glob.glob(str(Path(job_dir) / 'hooks' / ('vphook_%s_*.json' % reqs[0][:16]))))
    if not files:
        return None, 'hook files 0'
    hooks = [C.read_json(f) for f in files]
    if any(h is None or h.get('request_sha256') != reqs[0] for h in hooks):
        return None, 'hook request sha differs'
    if any(h['blocks'] != hooks[0]['blocks'] or h.get('first') != hooks[0].get('first') for h in hooks[1:]):
        return None, 'ambiguous (%d files differ)' % len(files)
    return hooks[0], None


def hook_ok(hook, T):
    if hook is None:
        return False, 'missing'
    if hook.get('errors'):
        return False, 'errors %s' % hook['errors'][:2]
    if hook.get('steps') != 450 or hook.get('t_first') != float(T) or hook.get('t_last') != float(T + 449):
        return False, 'steps %s t %s..%s' % (hook.get('steps'), hook.get('t_first'), hook.get('t_last'))
    if any((hook['blocks'].get(str(b)) or {}).get('steps') != 150 for b in (0, 1, 2)):
        return False, 'block steps'
    if any(len(hook['blocks'][str(b)]['n_dt']) != C.N_CELL for b in (0, 1, 2)):
        return False, 'cells != 31'
    return True, None


def map_ok(hook):
    lens = (((hook or {}).get('first') or {}).get('params') or {}).get('lengths_km')
    if not lens or len(lens) != C.N_CELL:
        return False, 'plant lengths missing or not 31'
    cum = [0.0]
    for x in lens:
        cum.append(cum[-1] + x * 1000.0)
    worst = max(abs(a - b) for a, b in zip(cum, C.CELL_B))
    return worst <= 1.0, 'max boundary gap %.3f m' % worst


def frames_scan(label):
    return C.read_json(C.OUT / 'fzp_frames' / ('VA_%s.json' % label))


# ------------------------------------------------------------------------------------------------ probe A / B
def oq_veh_h(h):
    return sum(h['blocks'][str(b)]['oq_dt'] for b in (0, 1, 2)) / 3600.0 if h else None


def probe_ab():
    out = {'states': [], 'stops': []}
    for jd in job_dirs('A'):
        probe = C.read_json(jd / 'probe.json') or {}
        st = probe.get('spec', {}).get('state', {})
        T, label = int(st.get('T', -1)), st.get('label')
        row = {'job': jd.name, 'label': label, 'T': T, 'tag': st.get('tag'), 'checks': probe.get('checks'),
               'errors': probe.get('errors'), 'stop': probe.get('stop')}
        ev = probe.get('evaluations') or {}
        if probe.get('stop') or probe.get('errors'):
            out['stops'].append({'job': jd.name, 'stop': probe.get('stop'), 'errors': probe.get('errors')})
        ck = probe.get('checks') or {}
        for name in ('R1_objective_bit_equal', 'R1_costs_within_1e-9', 'R3_repack_bit_equal'):
            if ck.get(name) is not True:
                out['stops'].append({'job': jd.name, 'check': name, 'value': ck.get(name)})
        row['J'] = {lab: e['objective_veh_h'] for lab, e in ev.items()}
        hooks, hstat = {}, {}
        for lab in ['R2_REC_scalar', 'EXEC_scalar'] + ['ARM%d_scalar' % v for v in ARMS]:
            h, why = hook_for(jd, probe, lab)
            ok, why2 = hook_ok(h, T)
            hooks[lab] = h if ok else None
            hstat[lab] = {'ok': ok, 'why': why or why2}
            if not ok:
                out['stops'].append({'job': jd.name, 'hook': lab, 'why': why or why2})
        row['hook_status'] = hstat
        mok, mwhy = map_ok(hooks.get('R2_REC_scalar'))
        row['map'] = {'ok': mok, 'why': mwhy}
        if not mok:
            out['stops'].append({'job': jd.name, 'map': mwhy})
        base = 'ARM110_scalar'
        arms = {}
        for v in ARMS:
            lab = 'ARM%d_scalar' % v
            if lab not in ev or base not in ev or 'R2_REC_scalar' not in ev:
                continue
            e, e0 = ev[lab], ev[base]
            d110 = e['objective_veh_h'] - e0['objective_veh_h']
            drec = e['objective_veh_h'] - ev['R2_REC_scalar']['objective_veh_h']
            costs = {k: e['costs'][k] - e0['costs'][k] for k in e['costs']}
            h, h0 = hooks.get(lab), hooks.get(base)
            zones = {}
            for w in WINDOWS:
                pc = plant_cells(h, WINDOWS[w]) if h else None
                pc0 = plant_cells(h0, WINDOWS[w]) if h0 else None
                zones[w] = {}
                for zone in C.ZONE_ORDER:
                    a, b = zone_plant(pc, zone), zone_plant(pc0, zone)
                    dstock = diff((a or {}).get('stock'), (b or {}).get('stock'))
                    zones[w][zone] = {'speed': (a or {}).get('speed'), 'stock': (a or {}).get('stock'),
                                      'd_speed': diff((a or {}).get('speed'), (b or {}).get('speed')),
                                      'd_stock': dstock,
                                      'd_veh_h': None if dstock is None else dstock * 150.0 * len(WINDOWS[w]) / 3600.0}
            pcw, pcw0 = (plant_cells(h, WINDOWS['w450']) if h else None), (plant_cells(h0, WINDOWS['w450']) if h0 else None)
            cells_d = {str(i): diff(pcw['speed'][i], pcw0['speed'][i]) if (pcw and pcw0) else None for i in FOCUS}
            oq, oq0 = oq_veh_h(h), oq_veh_h(h0)
            arms[str(v)] = {'J': e['objective_veh_h'], 'dJ_vs_110': d110, 'sign_vs_110': sign(d110),
                            'dJ_vs_REC': drec, 'sign_vs_REC': sign(drec), 'd_costs_vs_110': costs,
                            'd_cost_FW_E': costs.get('FW_E'),
                            'd_cost_other': sum(x for k, x in costs.items() if k != 'FW_E'),
                            'origin_queue_veh_h': oq, 'd_origin_queue_veh_h': diff(oq, oq0), 'zones': zones,
                            'cells_w450_d_speed': cells_d}
        row['arms'] = arms
        if '101' in arms and '100' in arms:
            row['dJ_101_minus_100'] = arms['101']['J'] - arms['100']['J']
        scan = frames_scan(label) if label else None
        for lab, key in (('EXEC_scalar', 'B_exec'), ('R2_REC_scalar', 'B_rec')):
            h = hooks.get(lab)
            row[key] = rollout_windows(h, scan, T) if (h is not None and scan is not None) else None
        row['B_vissim_cells'] = {w: (vissim_cells(scan, T + 150 * bl[0], T + 150 * (bl[-1] + 1)) or {}).get('speed')
                                 for w, bl in WINDOWS.items()} if scan else None
        row['initial_bias'] = initial_bias(hooks.get('EXEC_scalar'), scan, T)
        out['states'].append(row)
    out['summary'] = summarise_ab(out['states'], (C.read_json(C.DECL / 'VP_STATES.json') or {}).get('probe_B'))
    return out


def block_vsl_on(written):
    """Executed VSL of one 150 s block from the written FW_E rows of its decision: True when any speed < 110."""
    if not written:
        return None
    return any(v < 110.0 for vs in written.values() for v in vs)


def summarise_ab(states, declared=None):
    """A2: dJ sign counts by the decision kind at T (tags A2/A3 = 101 decisions, A1/A4 = 110 decisions).
    B3: per 150 s block, pooled over states by the VSL actually executed in that block (written rows of decision
    T + 150 b): 'on' = 101 on zone head 10, 'off' = 110.  n counts blocks (blocks of one state are not independent)."""
    s = {'dJ_sign_counts': {}, 'B_block_pool': {}}
    for kind, tags in (('101', ('A2', 'A3')), ('110', ('A1', 'A4'))):
        rows = [r for r in states if r.get('tag') in tags]
        cnt = {}
        for v in (101, 100, 90):
            signs = [r['arms'].get(str(v), {}).get('sign_vs_110') for r in rows if r.get('arms')]
            vals = [r['arms'][str(v)]['dJ_vs_110'] for r in rows if r.get('arms') and str(v) in r['arms']]
            cnt[str(v)] = {k: signs.count(k) for k in ('-', '0', '+')}
            cnt[str(v)]['range'] = [min(vals), max(vals)] if vals else None
        s['dJ_sign_counts'][kind] = cnt
    decl = {(d['label'], int(d['T'])): d for d in (declared or [])}
    pool = {'on': {}, 'off': {}}
    for r in states:
        d = decl.get((r.get('label'), r.get('T')))
        if not d or not r.get('B_exec'):
            continue
        for b, key in ((0, 'written_fwe_T'), (1, 'written_fwe_T150'), (2, 'written_fwe_T300')):
            on = block_vsl_on(d.get(key))
            if on is None:
                continue
            g = pool['on' if on else 'off']
            for zone in C.ZONE_ORDER:
                for q in ('speed', 'flow', 'stock'):
                    e = r['B_exec']['b%d' % b]['zones'][zone]['e'][q]
                    if e is not None:
                        g.setdefault(zone, {}).setdefault(q, []).append(e)
    for grp, zs in pool.items():
        s['B_block_pool'][grp] = {zone: {q: {'n': len(es), 'mean_e': sum(es) / len(es),
                                             'mean_abs_e': sum(abs(x) for x in es) / len(es)}
                                         for q, es in qs.items()} for zone, qs in zs.items()}
    s['B_on_minus_off'] = {zone: {q: diff(((s['B_block_pool'].get('on') or {}).get(zone) or {}).get(q, {}).get('mean_e'),
                                          ((s['B_block_pool'].get('off') or {}).get(zone) or {}).get(q, {}).get('mean_e'))
                                  for q in ('speed', 'flow', 'stock')} for zone in C.ZONE_ORDER}
    return s


# ------------------------------------------------------------------------------------------------ P1: FZP side
def cell_scan_rows(scan):
    out = []
    win = float(scan['win_s'])
    for w in range(scan['nw']):
        t0 = w * win
        if t0 < 900.0 or t0 + win > 9000.0 or scan['frames'][w] != 12:
            continue
        cells = scan['cells'][w]
        row = {'t0': t0, 'N': [0.0] * C.N_CELL, 'SV': [0.0] * C.N_CELL,
               'lane_N': [[0.0] * 4 for _ in range(C.N_CELL)], 'lane_SV': [[0.0] * 4 for _ in range(C.N_CELL)]}
        for c in range(C.N_CELL):
            for li in range(4):
                n, sv = cells[c][li][0], cells[c][li][1]
                row['N'][c] += n
                row['SV'][c] += sv
                row['lane_N'][c][li] += n
                row['lane_SV'][c][li] += sv
        out.append(row)
    return out


def median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def p1_fzp_profile(scan, exclude=None):
    rows = cell_scan_rows(scan)
    if exclude:
        rows = [r for r in rows if not (exclude[0] <= r['t0'] < exclude[1])]
    prof = {}
    for i in FOCUS:
        L, lanes = LEN_KM[i], C.CELL_LANES[i]
        ks, ss, flows, cong, lane_s, dsub = [], [], [], 0, [[] for _ in range(4)], []
        for r in rows:
            n, sv = r['N'][i], r['SV'][i]
            k = (n / 12.0) / (L * lanes)
            flows.append((sv / (L * 12.0) / lanes, k))
            if n <= 0:
                continue
            spd = sv / n
            cong += spd < 60.0
            if k <= K_LOW:
                ks.append(k)
                ss.append(spd)
                for li in range(4):
                    if r['lane_N'][i][li] > 0:
                        lane_s[li].append(r['lane_SV'][i][li] / r['lane_N'][i][li])
                if i == 18:
                    n_mu = r['N'][16] + r['N'][17]
                    if n_mu > 0:
                        dsub.append(spd - (r['SV'][16] + r['SV'][17]) / n_mu)
        qmax = max(flows) if flows else (None, None)
        prof[str(i)] = {'low_n': len(ss), 'low_k_med': median(ks), 'low_speed_med': median(ss),
                        'qmax_per_lane': qmax[0], 'k_at_qmax': qmax[1], 'windows': len(rows),
                        'congested_share': (cong / len(rows)) if rows else None,
                        'low_lane_speed_med': [median(x) for x in lane_s]}
        if i == 18:
            prof['18']["low_VS0'_minus_Mu'_speed_med"] = median(dsub)
    return prof


def p1_fzp(src, states):
    out = {}
    lows = {r['label']: r['T_low'] for r in states['runs']}
    for s in src['sources']:
        path = s.get('cell_scan_reuse') or s.get('cell_scan_out')
        scan = C.read_json(path) if path else None
        if scan is None:
            out[s['label']] = None
            continue
        out[s['label']] = {'all': p1_fzp_profile(scan), 'scan_sha256': C.sha256_file(path)}
        if s['arm'] == 'VA':
            tl = lows['v3c3-s%d' % s['seed']]
            out[s['label']]['vsl_free'] = p1_fzp_profile(scan, exclude=(min(tl), max(tl) + 600.0))
    return out


def c1_inputs(src):
    """C1: pooled NC3 three seeds, cells 8-25: median low-density density and speed (>= 20 windows)."""
    pool = {str(i): {'k': [], 's': []} for i in FOCUS}
    shas = {}
    for s in src['sources']:
        if s['arm'] != 'NC3':
            continue
        path = s['cell_scan_reuse']
        shas[s['label']] = C.sha256_file(path)
        for r in cell_scan_rows(C.read_json(path)):
            for i in FOCUS:
                n, sv = r['N'][i], r['SV'][i]
                k = (n / 12.0) / (LEN_KM[i] * C.CELL_LANES[i])
                if n > 0 and k <= K_LOW:
                    pool[str(i)]['k'].append(k)
                    pool[str(i)]['s'].append(sv / n)
    cells = {i: {'k_med': statistics.median(d['k']), 's_med': statistics.median(d['s']), 'n': len(d['s'])}
             for i, d in pool.items() if len(d['s']) >= 20}
    return {'cells': cells, 'scan_sha256': shas}


def c7_inputs(label, T):
    scan = frames_scan(label)
    ks = [k for k, t in enumerate(scan['frames']) if T - 5.5 < t <= T + 0.5]
    cells = {}
    for i in FOCUS:
        N = sum(scan['N'][k][i] for k in ks)
        SV = sum(scan['SV'][k][i] for k in ks)
        if N > 0:
            cells[str(i)] = SV / N
    return {'cells': cells, 'frames': len(ks)}


def spec_common(mode, row):
    return {'mode': mode, 'owner': 'FW_E', 'zone_head': 10,
            'state': {'label': row['label'], 'T': int(row['T']), 'tag': row.get('tag', 'P1')}, 'max_parallel': 4}


def specs_a(out_dir):
    states = C.read_json(C.DECL / 'VP_STATES.json')
    out_dir = Path(out_dir)
    jobs = []
    for r in states['probe_A']:
        sp = spec_common('A', r)
        sp['arms'] = ARMS
        name = 'spec_A_%s_T%06d.json' % (r['label'], r['T'])
        C.write_json(out_dir / name, sp)
        jobs.append({'tag': 'A_%s_T%06d' % (r['label'], r['T']), 'kind': 'job', 'mode': 'A', 'run': r['run'],
                     'T': r['T'], 'spec': str(out_dir / name),
                     'dir': str(C.OUT / 'plant_A' / ('%s_T%06d' % (r['label'], r['T'])))})
    C.write_json(out_dir / 'jobs_A.json', {'name': 'plantA', 'jobs': jobs})
    print('specs A: %d' % len(jobs))


def p1_inputs(out_dir):
    states = C.read_json(C.DECL / 'VP_STATES.json')
    src = C.read_json(C.DECL / 'VP_FZP_SOURCES.json')
    out_dir = Path(out_dir)
    c1 = c1_inputs(src)
    rec = {'schema': 'vp-p1-inputs/1', 'made_kst': C.kst(), 'C1': c1, 'C7': {}}
    jobs = []
    for r in states['p1']:
        c7 = c7_inputs(r['label'], int(r['T']))
        rec['C7']['%s_T%06d' % (r['label'], r['T'])] = c7
        sp = spec_common('P', r)
        sp['ablations'] = {'C1_vfree': {'cells': {i: {'k_med': v['k_med'], 's_med': v['s_med']}
                                                  for i, v in c1['cells'].items()}},
                           'C2_rhocrit': {'mult': 1.2, 'cells': FOCUS},
                           'C3_merge': {}, 'C4_lanedrop': {}, 'C5_capdrop': {}, 'C6_compliance': {},
                           'C7_initial': {'cells': c7['cells']}}
        name = 'spec_P_%s_T%06d.json' % (r['label'], r['T'])
        C.write_json(out_dir / name, sp)
        jobs.append({'tag': 'P_%s_T%06d' % (r['label'], r['T']), 'kind': 'job', 'mode': 'P', 'run': r['run'],
                     'T': r['T'], 'spec': str(out_dir / name),
                     'dir': str(C.OUT / 'plant_P' / ('%s_T%06d' % (r['label'], r['T'])))})
    C.write_json(out_dir / 'p1_inputs.json', rec)
    C.write_json(out_dir / 'jobs_P.json', {'name': 'plantP', 'jobs': jobs})
    print('p1 inputs: C1 cells %d, P jobs %d' % (len(c1['cells']), len(jobs)))


# ------------------------------------------------------------------------------------------------ P1: plant side
def reach(applied, hook, name):
    """Worker-seen values (hook first.params / initial) against what the parent set."""
    if hook is None:
        return False, 'no hook'
    first = hook.get('first') or {}
    pr, ini = first.get('params') or {}, first.get('initial') or {}
    rows = pr.get('segment_rows') or []
    if name == 'null':
        return True, None
    if name in ('C1_vfree', 'C2_rhocrit'):
        key = 'v_free' if name == 'C1_vfree' else 'rho_crit'
        bad = [i for i, v in (applied.get('cells') or {}).items()
               if len(rows) <= int(i) or abs(float((rows[int(i)] or {}).get(key, float('nan'))) - v['new']) > 1e-9]
        return not bad, ('cells not seen: %s' % bad) if bad else None
    if name == 'C3_merge':
        return (pr.get('metanet_delta_merge') == 0.0
                and (pr.get('by_direction') or {}).get('metanet_delta_merge', 0.0) == 0.0), None
    if name == 'C4_lanedrop':
        return (pr.get('freeway_lane_drop_phi') == 0.0
                and (pr.get('by_direction') or {}).get('freeway_lane_drop_phi', 0.0) == 0.0), None
    if name == 'C5_capdrop':
        return pr.get('capacity_drop_discharge_phi') == 1.0 and pr.get('capacity_drop_anticipation') in (False, None), None
    if name == 'C6_compliance':
        return (not pr.get('vsl_fd_response_present')) and pr.get('vsl_transport') is None, None
    if name == 'C7_initial':
        bad = [i for i, v in (applied.get('cells') or {}).items()
               if abs(ini['speed_kmh'][int(i)] - v['new']) > 1e-9]
        return not bad, ('cells not seen: %s' % bad) if bad else None
    return False, 'unknown'


def p1_states():
    out = {'states': [], 'stops': []}
    for jd in job_dirs('P'):
        probe = C.read_json(jd / 'probe.json') or {}
        st = probe.get('spec', {}).get('state', {})
        T, label = int(st.get('T', -1)), st.get('label')
        row = {'job': jd.name, 'label': label, 'T': T, 'checks': probe.get('checks'), 'errors': probe.get('errors')}
        ck = probe.get('checks') or {}
        for name in ('R1_objective_bit_equal', 'R1_costs_within_1e-9', 'R3_repack_bit_equal', 'null_bit_equal'):
            if ck.get(name) is not True:
                out['stops'].append({'job': jd.name, 'check': name, 'value': ck.get(name)})
        if probe.get('errors') or probe.get('stop'):
            out['stops'].append({'job': jd.name, 'errors': probe.get('errors'), 'stop': probe.get('stop')})
        scan = frames_scan(label)
        base, why = hook_for(jd, probe, 'EXEC_scalar')
        ok, why2 = hook_ok(base, T)
        if not ok:
            out['stops'].append({'job': jd.name, 'hook': 'EXEC_scalar', 'why': why or why2})
            out['states'].append(row)
            continue
        mok, mwhy = map_ok(base)
        if not mok:
            out['stops'].append({'job': jd.name, 'map': mwhy})
        tabs0 = rollout_windows(base, scan, T)
        row['base'] = tabs0
        row['initial_bias'] = initial_bias(base, scan, T)
        row['params'] = (base.get('first') or {}).get('params')
        row['ablations'] = {}
        for name in ['null'] + ABLATIONS:
            lab = 'ABL_%s' % name
            h, why = hook_for(jd, probe, lab)
            ok, why2 = hook_ok(h, T)
            if not ok:
                out['stops'].append({'job': jd.name, 'hook': lab, 'why': why or why2})
                continue
            applied = (probe.get('ablations') or {}).get(lab) or {}
            rok, rwhy = reach(applied, h, name)
            if not rok:
                out['stops'].append({'job': jd.name, 'reach': lab, 'why': rwhy})
            tabs = rollout_windows(h, scan, T)
            ev = probe['evaluations'][lab]
            ident = (ev['objective_veh_h'] == probe['evaluations']['EXEC_scalar']['objective_veh_h']
                     and h['blocks'] == base['blocks'])
            m = {}
            for mname, (zone, q) in METRICS.items():
                w = 'b0' if name == 'C7_initial' else 'w450'
                e0, ec = tabs0[w]['zones'][zone]['e'][q], tabs[w]['zones'][zone]['e'][q]
                R = None if (e0 is None or ec is None or abs(e0) < 1.0) else 1.0 - abs(ec) / abs(e0)
                m[mname] = {'window': w, 'e_base': e0, 'e_ablated': ec, 'R': R}
            row['ablations'][name] = {'applied': applied, 'reach_ok': rok, 'bit_identical_to_base': ident,
                                      'dJ_vs_base': ev['objective_veh_h'] - probe['evaluations']['EXEC_scalar']['objective_veh_h'],
                                      'metrics': m}
        out['states'].append(row)
    out['summary'] = summarise_p1(out['states'])
    return out


def summarise_p1(states):
    s = {}
    for name in ABLATIONS:
        s[name] = {}
        for mname in METRICS:
            Rs = [r['ablations'][name]['metrics'][mname]['R'] for r in states
                  if (r.get('ablations') or {}).get(name) and r['ablations'][name]['metrics'][mname]['R'] is not None]
            n = len(Rs)
            n_hi = sum(1 for x in Rs if x >= 0.5)
            med = statistics.median(Rs) if Rs else None
            points = n >= 6 and n_hi >= math.ceil(2.0 * n / 3.0) and med is not None and med >= 0.5
            band = None if med is None else ('A' if med >= 0.5 else ('B' if med >= 0.2 else 'C'))
            s[name][mname] = {'n_defined': n, 'n_R_ge_0.5': n_hi, 'n_R_le_-0.2': sum(1 for x in Rs if x <= -0.2),
                              'median_R': med, 'band': band, 'points_to_term': points,
                              'n_bit_identical': sum(1 for r in states if (r.get('ablations') or {}).get(name)
                                                     and r['ablations'][name]['bit_identical_to_base'])}
    return s


def p1_params(p1, inputs):
    """P1-P: worker-seen FW_E parameters of the first P1 state with a base hook, cells 8-25, plus the plant FD
    speed at the VISSIM low-density median density (NC3 pooled) and the C1 replacement value."""
    st = next((r for r in p1.get('states', []) if r.get('params')), None)
    if st is None:
        return None
    pr = st['params']
    rows = pr.get('segment_rows') or []
    c1 = ((inputs or {}).get('C1') or {}).get('cells') or {}
    cells = {}
    for i in FOCUS:
        row = rows[i] if i < len(rows) else {}
        vf = row.get('v_free', pr.get('v_free'))
        rc = row.get('rho_crit', pr.get('rho_crit'))
        a = row.get('metanet_a_m', pr.get('metanet_a_m'))
        v = c1.get(str(i))
        fd = None
        repl = None
        if v and vf and rc and a:
            factor = math.exp(-(1.0 / a) * (v['k_med'] / rc) ** a)
            fd = vf * factor
            repl = v['s_med'] / factor
        cells[str(i)] = {'v_free': vf, 'rho_crit': rc, 'a_m': a, 'tau_h': row.get('metanet_tau_h'),
                         'nu': row.get('metanet_nu_km2_h'), 'kappa': row.get('metanet_kappa_veh_km_lane'),
                         'length_km': (pr.get('lengths_km') or [None] * 31)[i],
                         'lanes': (pr.get('segment_lanes') or [None] * 31)[i],
                         'vissim_k_med': (v or {}).get('k_med'), 'vissim_s_med': (v or {}).get('s_med'),
                         'plant_fd_speed_at_k_med': fd, 'C1_replacement_v_free': repl}
    scal = {k: pr.get(k) for k in ('freeway_lane_drop_phi', 'metanet_delta_merge', 'capacity_drop_discharge_phi',
                                   'capacity_drop_anticipation', 'alpha_vsl', 'rho_crit', 'v_free',
                                   'vsl_fd_response_present', 'hadi_present', 'terminal_zero_gradient')}
    scal['by_direction'] = pr.get('by_direction')
    scal['vsl_transport'] = pr.get('vsl_transport')
    scal['vsl_fd_response'] = pr.get('vsl_fd_response')
    return {'from_state': '%s_T%06d' % (st['label'], st['T']), 'scalars': scal, 'cells': cells}


# ------------------------------------------------------------------------------------------------ tables
def fmt(x, nd=2):
    if x is None:
        return '—'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, int):
        return str(x)
    return ('%.' + str(nd) + 'f') % x


def md_tables(res):
    L = ['# vsl_plant 표 (vp_analyze.py 가 만든 글자 그대로)', '']
    L.append('## 멈춤 규칙 걸림')
    for k in ('AB', 'P1'):
        st = (res.get(k) or {}).get('stops') or []
        L.append('- %s: %d건' % (k, len(st)))
        for x in st[:40]:
            L.append('  - `%s`' % json.dumps(x, ensure_ascii=False)[:300])
    L.append('')
    ab = res.get('AB') or {}
    L.append('## 표 A1 — 탐침 A: plant ΔJ (veh·h / 450 s), 기준 = 같은 상태의 VSL 110 팔')
    L.append('')
    L.append('| 상태 | T | 묶음 | R1 | R3 | ΔJ 101 | ΔJ 100 | ΔJ 90 | ΔJ(101−100) | ΔFW_E 비용 100 | Δ다른 owner 100 | Δ입구대기 100 |')
    L.append('|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|')
    for r in ab.get('states', []):
        a = r.get('arms') or {}
        ck = r.get('checks') or {}

        def g(v, key):
            return (a.get(str(v)) or {}).get(key)
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], r.get('tag'), fmt(ck.get('R1_objective_bit_equal')), fmt(ck.get('R3_repack_bit_equal')),
            fmt(g(101, 'dJ_vs_110'), 3), fmt(g(100, 'dJ_vs_110'), 3), fmt(g(90, 'dJ_vs_110'), 3),
            fmt(r.get('dJ_101_minus_100'), 3), fmt(g(100, 'd_cost_FW_E'), 3), fmt(g(100, 'd_cost_other'), 3),
            fmt(g(100, 'd_origin_queue_veh_h'), 3)))
    L.append('')
    sm = ab.get('summary') or {}
    L.append('## 표 A2 — ΔJ(팔 − 110) 부호 수 (|ΔJ| < 0.01 은 0)')
    L.append('')
    L.append('| 묶음 | 팔 | − | 0 | + | 범위 |')
    L.append('|---|---|---:|---:|---:|---|')
    for kind, cnt in (sm.get('dJ_sign_counts') or {}).items():
        for v, c in cnt.items():
            rg = c.get('range')
            L.append('| %s 상태 | %s | %d | %d | %d | %s |' % (kind, v, c['-'], c['0'], c['+'],
                                                           '—' if not rg else '%.3f ~ %.3f' % tuple(rg)))
    L.append('')
    L.append('## 표 A3 — 탐침 A: 구역 속도 차 (팔 − 110, km/h), w450')
    L.append('')
    L.append('| 상태 | T | 팔 | ' + ' | '.join(C.ZONE_ORDER) + ' |')
    L.append('|---|---:|---|' + '---:|' * len(C.ZONE_ORDER))
    for r in ab.get('states', []):
        for v in (101, 100, 90):
            z = ((r.get('arms') or {}).get(str(v)) or {}).get('zones', {}).get('w450', {})
            L.append('| %s | %d | %d | %s |' % (r['label'], r['T'], v,
                                                ' | '.join(fmt((z.get(k) or {}).get('d_speed')) for k in C.ZONE_ORDER)))
    L.append('')
    L.append('## 표 B1 — 탐침 B: 실행 계획 plant − V-A FZP, 구역 속도 편향 (km/h), b0 / b1 / b2 / w450')
    L.append('')
    L.append('| 상태 | T | 묶음 | ' + ' | '.join(C.ZONE_ORDER) + ' |')
    L.append('|---|---:|---|' + '---:|' * len(C.ZONE_ORDER))
    for r in ab.get('states', []):
        bx = r.get('B_exec')
        if not bx:
            continue
        L.append('| %s | %d | %s | %s |' % (r['label'], r['T'], r.get('tag'), ' | '.join(
            ' / '.join(fmt(bx[w]['zones'][z]['e']['speed'], 1) for w in ('b0', 'b1', 'b2', 'w450')) for z in C.ZONE_ORDER)))
    L.append('')
    L.append('## 표 B2 — 탐침 B: 재고 편향 (veh) · 흐름 편향 (veh/h), w450')
    L.append('')
    L.append('| 상태 | T | ' + ' | '.join(C.ZONE_ORDER) + ' |')
    L.append('|---|---:|' + '---:|' * len(C.ZONE_ORDER))
    for r in ab.get('states', []):
        bx = r.get('B_exec')
        if not bx:
            continue
        L.append('| %s | %d | %s |' % (r['label'], r['T'], ' | '.join(
            '%s · %s' % (fmt(bx['w450']['zones'][z]['e']['stock'], 1), fmt(bx['w450']['zones'][z]['e']['flow'], 0))
            for z in C.ZONE_ORDER)))
    L.append('')
    L.append('## 표 B3 — 탐침 B 요약: 150 s 블록을 실행된 VSL 로 나눠 모은 평균 편향 (블록 수 n; 한 상태의 블록끼리는 독립 아님)')
    L.append('')
    L.append('| 구역 | 양 | 켬(101): n | 켬: 평균 e | 켬: 평균 |e| | 끔(110): n | 끔: 평균 e | 끔: 평균 |e| | 켬 − 끔 |')
    L.append('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    bp = sm.get('B_block_pool') or {}
    for zone in C.ZONE_ORDER:
        for q in ('speed', 'stock', 'flow'):
            on = ((bp.get('on') or {}).get(zone) or {}).get(q) or {}
            off = ((bp.get('off') or {}).get(zone) or {}).get(q) or {}
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                zone, q, fmt(on.get('n')), fmt(on.get('mean_e'), 1), fmt(on.get('mean_abs_e'), 1), fmt(off.get('n')),
                fmt(off.get('mean_e'), 1), fmt(off.get('mean_abs_e'), 1),
                fmt(((sm.get('B_on_minus_off') or {}).get(zone) or {}).get(q), 1)))
    L.append('')
    L.append('## 표 B4 — 탐침 B: 셀 8–25 속도 편향 (km/h), w450')
    L.append('')
    L.append('| 상태 | T | ' + ' | '.join(str(i) for i in FOCUS) + ' |')
    L.append('|---|---:|' + '---:|' * len(FOCUS))
    for r in ab.get('states', []):
        bx = r.get('B_exec')
        if not bx:
            continue
        L.append('| %s | %d | %s |' % (r['label'], r['T'], ' | '.join(
            fmt(bx['w450']['cells'][str(i)]['speed']['e'], 1) for i in FOCUS)))
    L.append('')
    p1 = res.get('P1') or {}
    L.append('## 표 P1-F — FZP 저밀도(k ≤ 12 veh/km/차로) 중앙 속도 (km/h), 셀 8–25')
    L.append('')
    L.append('| 원천 | ' + ' | '.join(str(i) for i in FOCUS) + " | 셀18 − 셀16–17 |")
    L.append('|---|' + '---:|' * (len(FOCUS) + 1))
    for lab, prof in sorted((res.get('P1_FZP') or {}).items()):
        if not prof:
            continue
        a = prof['all']
        L.append('| %s | %s | %s |' % (lab, ' | '.join(fmt(a[str(i)]['low_speed_med'], 1) for i in FOCUS),
                                       fmt(a['18'].get("low_VS0'_minus_Mu'_speed_med"), 1)))
    L.append('')
    pp = res.get('P1_params') or {}
    L.append('## 표 P1-P — plant 매개변수(작업자가 본 값)와 VISSIM 저밀도 점, 셀 8–25 (%s)' % pp.get('from_state', '—'))
    L.append('')
    L.append('- 스칼라: `%s`' % json.dumps(pp.get('scalars'), ensure_ascii=False)[:600])
    L.append('')
    L.append('| 셀 | v_free | ρ_c | a | 차로 | VISSIM k 중앙 | VISSIM 속도 중앙 | plant FD 속도(같은 k) | C1 바꿀 v_free |')
    L.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for i in FOCUS:
        c = (pp.get('cells') or {}).get(str(i)) or {}
        L.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            i, fmt(c.get('v_free'), 1), fmt(c.get('rho_crit'), 1), fmt(c.get('a_m'), 2), fmt(c.get('lanes'), 1),
            fmt(c.get('vissim_k_med'), 1), fmt(c.get('vissim_s_med'), 1), fmt(c.get('plant_fd_speed_at_k_med'), 1),
            fmt(c.get('C1_replacement_v_free'), 1)))
    L.append('')
    L.append('## 표 P1-B — VSL 끔 상태 기준 편향 (실행 계획 plant − V-A FZP), w450 · 시작(T) 편향')
    L.append('')
    L.append("| 상태 | T | VSa 속도 | VS0' 속도 | M1 속도 | VSb 재고 | VSb 속도 | 시작 VSa 속도 | 시작 VSb 재고 |")
    L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for r in p1.get('states', []):
        b = r.get('base')
        if not b:
            continue
        z = b['w450']['zones']
        ib = (r.get('initial_bias') or {}).get('zones') or {}
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], fmt(z['VSa']['e']['speed'], 1), fmt(z["VS0'"]['e']['speed'], 1),
            fmt(z['M1']['e']['speed'], 1), fmt(z['VSb']['e']['stock'], 1), fmt(z['VSb']['e']['speed'], 1),
            fmt((ib.get('VSa') or {}).get('e_speed'), 1), fmt((ib.get('VSb') or {}).get('e_stock'), 1)))
    L.append('')
    L.append('## 표 P1-R — 항 빼기 줄임 비율 R 요약 (상태 9개; R = 1 − |e_절제|/|e_기준|)')
    L.append('')
    L.append('| 후보 | 지표 | 정의된 상태 | R ≥ 0.5 | R ≤ −0.2 | 중앙 R | 띠 | 가리킴 규칙 | 기준과 비트 같음 |')
    L.append('|---|---|---:|---:|---:|---:|---|---|---:|')
    for name, ms in (p1.get('summary') or {}).items():
        for mname, v in ms.items():
            L.append('| %s | %s | %d | %d | %d | %s | %s | %s | %d |' % (
                name, mname, v['n_defined'], v['n_R_ge_0.5'], v['n_R_le_-0.2'], fmt(v['median_R'], 2),
                v['band'] or '—', '충족' if v['points_to_term'] else '미충족', v['n_bit_identical']))
    L.append('')
    return '\n'.join(L) + '\n'


def tables(out_json, out_md):
    states = C.read_json(C.DECL / 'VP_STATES.json')
    src = C.read_json(C.DECL / 'VP_FZP_SOURCES.json')
    res = {'schema': 'vp-tables/1', 'made_kst': C.kst()}
    res['AB'] = probe_ab()
    res['P1_FZP'] = p1_fzp(src, states)
    res['P1'] = p1_states()
    res['P1_params'] = p1_params(res['P1'], C.read_json(C.OUT / 'p1_specs' / 'p1_inputs.json'))
    C.write_json(out_json, res)
    Path(out_md).write_text(md_tables(res), encoding='utf-8')
    print('tables: AB states %d stops %d, P1 states %d stops %d' % (
        len(res['AB']['states']), len(res['AB']['stops']), len(res['P1']['states']), len(res['P1']['stops'])))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'specs-a':
        specs_a(sys.argv[2])
    elif cmd == 'p1-fzp':
        res = p1_fzp(C.read_json(C.DECL / 'VP_FZP_SOURCES.json'), C.read_json(C.DECL / 'VP_STATES.json'))
        C.write_json(sys.argv[2], {'schema': 'vp-p1-fzp/1', 'made_kst': C.kst(), 'profiles': res})
        print('p1-fzp: %d sources with a scan' % sum(1 for v in res.values() if v))
    elif cmd == 'p1-inputs':
        p1_inputs(sys.argv[2])
    elif cmd == 'tables':
        tables(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit('unknown command ' + cmd)
