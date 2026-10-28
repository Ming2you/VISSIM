"""VERIFY_VP independent recompute (verifier tool, 2026-10-27 KST).  Read-only.  Does NOT import vp_analyze / vp_common
or any producer collect/extract script; definitions are re-implemented from PRE_VP_FIXED.md (33e71ac3...) sections
3.3, 4.2-4.3, 5.2-5.4 and PRE_VP_R3.md.

    python -B vv_recompute.py <out.json>

Inputs (raw outputs only): GT/out/plant_A/*/probe.json + hooks, GT/out/plant_P/*/probe.json + hooks + jobcheck.json,
GT/out/fzp_frames/VA_*.json, cell scans (GT/out/fzp_cell + the NC3/VSL scans declared in VP_FZP_SOURCES.json),
decl/VP_STATES.json (state list, labels and seeds from provenance fields, executed VSL per block).
Seeds/labels are taken from VP_STATES (provenance) only; job folders are located from label + T.
Output: one JSON with every recomputed number (no files written elsewhere)."""
import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
VP = SP / 'vsl_plant'
GT = Path(r'D:/VISSIM-merge/k8_gate_trees/vsl_plant')
OUT = GT / 'out'
BLIND = ('s47', 's37', 's59', 's61', 's67', 'sealed')

# zones on the 31 cells (PRE_VP_FIXED 0 / section 4.3)
Z = {'U': list(range(0, 8)), 'B1': list(range(8, 14)), 'M1': [14, 15], 'VSa': [16, 17, 18], "Mu'": [16, 17],
     "VS0'": [18], 'VSb': list(range(19, 26)), "B2'": list(range(19, 25)), 'D': list(range(26, 31)),
     'cell12': [12]}
LANES_VIS = [4] * 19 + [3] * 12      # PRE_VP_FIXED 1.1 (cells 0-18 four lanes, 19-30 three)
P1_METRICS = [('m1', 'VSa', 'speed'), ('m2', 'M1', 'speed'), ('m3', 'VSb', 'stock'), ('m4', 'VSb', 'speed'),
              ("m5", "VS0'", 'speed')]
CANDS = ['C1_vfree', 'C2_rhocrit', 'C3_merge', 'C4_lanedrop', 'C5_capdrop', 'C6_compliance', 'C7_initial',
         'C8_antic18', 'C9_lanedrop_both']


def load(p):
    s = str(p).lower().replace('\\', '/')
    for t in BLIND:
        if t in s:
            raise SystemExit('BLIND refuse %s' % p)
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def rng(xs):
    xs = [x for x in xs if x is not None]
    return [min(xs), max(xs)] if xs else None


# ------------------------------------------------------------------------------------------------ hooks
def hooks_of(jd):
    d = {}
    for f in sorted((jd / 'hooks').glob('vphook_*.json')):
        h = load(f)
        d.setdefault(h['request_sha256'], []).append(h)
    return d


def hook_for(probe, hooks, label):
    ev = probe['evaluations'][label]
    runs = [r for r in probe['runs'] if r['batch'] == ev['batch'] and r['action_token'] == ev['action_token']]
    reqs = sorted({r['request_sha256'] for r in runs})
    if len(reqs) != 1:
        raise ValueError('label %s maps to %d requests' % (label, len(reqs)))
    hs = hooks.get(reqs[0]) or []
    if not hs:
        raise ValueError('no hook for %s' % label)
    for h in hs[1:]:
        if h['blocks'] != hs[0]['blocks']:
            raise ValueError('two hooks of one request differ (%s)' % label)
    h = hs[0]
    if h.get('errors') or int(h['steps']) != 450:
        raise ValueError('hook not clean %s' % label)
    return h


def p_agg(h, blocks):
    n = [0.0] * 31
    nv = [0.0] * 31
    dt = 0.0
    oq = 0.0
    for b in blocks:
        B = h['blocks'][str(b)]
        dt += float(B['dt'])
        oq += float(B['oq_dt'])
        for c in range(31):
            n[c] += float(B['n_dt'][c])
            nv[c] += float(B['nv_dt'][c])
    return n, nv, dt, oq


def p_zone(h, blocks, cells):
    n, nv, dt, _ = p_agg(h, blocks)
    N = sum(n[c] for c in cells)
    NV = sum(nv[c] for c in cells)
    return {'stock': N / dt, 'speed': (NV / N) if N > 0 else None, 'vehh': N / 3600.0}


def p_exit_blocked(h, blocks):
    out = {}
    for b in blocks:
        for k, v in (h['blocks'][str(b)].get('exit_blocked_dt') or {}).items():
            out[k] = out.get(k, 0.0) + float(v) / 3600.0      # veh/h * s -> veh
    return out


# ------------------------------------------------------------------------------------------------ VISSIM frames
def v_zone(fr, T, blocks, cells):
    idx = []
    for i, t in enumerate(fr['frames']):
        for b in blocks:
            if T + 150 * b <= t < T + 150 * (b + 1):
                idx.append(i)
                break
    nf = len(idx)
    N = sum(fr['N'][i][c] for i in idx for c in cells)
    SV = sum(fr['SV'][i][c] for i in idx for c in cells)
    return {'stock': N / nf if nf else None, 'speed': (SV / N) if N > 0 else None, 'nf': nf}


def v_start(fr, T, cells):
    idx = [i for i, t in enumerate(fr['frames']) if abs(t - (T - 4.9)) < 1e-6 or abs(t - (T + 0.1)) < 1e-6]
    N = sum(fr['N'][i][c] for i in idx for c in cells)
    SV = sum(fr['SV'][i][c] for i in idx for c in cells)
    return {'stock': N / len(idx) if idx else None, 'speed': SV / N if N > 0 else None, 'nf': len(idx)}


def p_start(h, cells):
    ini = h['first']['initial']
    st = [float(ini['stock_veh'][c]) for c in cells]
    sp = [float(ini['speed_kmh'][c]) for c in cells]
    S = sum(st)
    return {'stock': S, 'speed': sum(a * b for a, b in zip(st, sp)) / S if S > 0 else None}


def e(p, v, q):
    if p.get(q) is None or v.get(q) is None:
        return None
    return p[q] - v[q]


# ------------------------------------------------------------------------------------------------ main parts
def probe_A(states, out):
    rows = []
    blocks_onoff = []
    for s in states['probe_A']:
        lab, T = s['label'], int(s['T'])
        jd = OUT / 'plant_A' / ('%s_T%06d' % (lab, T))
        pr = load(jd / 'probe.json')
        if pr['spec']['state']['label'] != lab or int(pr['spec']['state']['T']) != T:
            raise ValueError('spec/state mismatch %s %s' % (lab, T))
        hooks = hooks_of(jd)
        ev = pr['evaluations']
        J = {k: ev[k]['objective_veh_h'] for k in ev}
        C = {k: ev[k]['costs'] for k in ev}
        a110 = 'ARM110_scalar'
        r = {'label': lab, 'T': T, 'tag': s['tag'],
             'rec_head10': [b['zone_head_10'] for b in pr['plans']['REC']['vsl']],
             'exec_head10': [b['zone_head_10'] for b in pr['plans']['EXEC']['vsl']]}
        for v in (101, 100, 90):
            r['dJ%d' % v] = J['ARM%d_scalar' % v] - J[a110]
        r['dJ101_100'] = J['ARM101_scalar'] - J['ARM100_scalar']
        r['dFWE100'] = C['ARM100_scalar']['FW_E'] - C[a110]['FW_E']
        r['drest100'] = sum(C['ARM100_scalar'][k] - C[a110][k] for k in C[a110] if k != 'FW_E')
        r['J_minus_sumcosts_ARM100'] = J['ARM100_scalar'] - sum(C['ARM100_scalar'].values())
        r['ARM110_minus_REC'] = J[a110] - J['R2_REC_scalar']
        ck = pr['checks']
        r['R1_obj_diff'] = ck['R1_objective_diff']
        r['R1_obj_bit_equal'] = ck['R1_objective_bit_equal']
        r['R1_costs_max'] = ck['R1_costs_max_abs_diff']
        r['R1_obj_recomputed'] = ev['R1_REC_ad']['objective_veh_h'] - pr['recorded']['selected_objective']
        r['R1_costs_recomputed_max'] = max(abs(ev['R1_REC_ad']['costs'][k] - pr['recorded']['omega_costs'][k])
                                           for k in pr['recorded']['omega_costs'])
        r['R2_minus_R1'] = ev['R2_REC_scalar']['objective_veh_h'] - ev['R1_REC_ad']['objective_veh_h']
        r['R3_bit'] = (ev['R3_REPACK_scalar']['objective_veh_h'] == ev['R2_REC_scalar']['objective_veh_h']
                       and ev['R3_REPACK_scalar']['costs'] == ev['R2_REC_scalar']['costs'])
        r['repack_token_eq_rec'] = pr['plans']['REPACK']['token'] == pr['plans']['REC']['token']
        r['exit_code'] = pr.get('exit_code')
        jc = load(jd / 'jobcheck.json')
        r['jobcheck_hits'] = len(jc.get('hits') or [])
        r['jobcheck_r1_ok'] = jc.get('r1_objective_ok')
        # hooks
        H = {a: hook_for(pr, hooks, 'ARM%d_scalar' % a) for a in (110, 101, 100, 90)}
        H['EXEC'] = hook_for(pr, hooks, 'EXEC_scalar')
        W = [0, 1, 2]
        r['origin_queue_vehh'] = {a: p_agg(H[a], W)[3] / 3600.0 for a in (110, 101, 100, 90)}
        r['zone_vehh_d'] = {}
        for a in (100, 90, 101):
            r['zone_vehh_d'][a] = {z: p_zone(H[a], W, Z[z])['vehh'] - p_zone(H[110], W, Z[z])['vehh']
                                   for z in ('U', 'B1', 'M1', 'VSa', "VS0'", 'VSb', 'D')}
        r['resp100_speed'] = {z: p_zone(H[100], W, Z[z])['speed'] - p_zone(H[110], W, Z[z])['speed']
                              for z in ('M1', 'VSa', "VS0'", 'VSb', 'B1', 'D')}
        fr = load(OUT / 'fzp_frames' / ('VA_%s.json' % lab))
        r['exec_e_w450'] = {}
        for z in ('U', 'B1', 'cell12', 'M1', 'VSa', "VS0'", 'VSb', 'D', "Mu'", "B2'"):
            pz, vz = p_zone(H['EXEC'], W, Z[z]), v_zone(fr, T, W, Z[z])
            r['exec_e_w450'][z] = {'speed': e(pz, vz, 'speed'), 'stock': e(pz, vz, 'stock'),
                                   'p_speed': pz['speed'], 'v_speed': vz['speed'], 'nf': vz['nf']}
        # start bias
        r['start_e'] = {}
        for z in ('U', 'B1', 'M1', 'VSa', "Mu'", "VS0'", 'VSb', "B2'", 'D'):
            ps, vs = p_start(H['EXEC'], Z[z]), v_start(fr, T, Z[z])
            r['start_e'][z] = {'speed': e(ps, vs, 'speed'), 'stock': e(ps, vs, 'stock'), 'nf': vs['nf']}
        # per block on/off
        for b in (0, 1, 2):
            wr = s['written_fwe_T' + ('' if b == 0 else str(150 * b))]
            on = any(float(x) < 110.0 for vals in wr.values() for x in vals)
            row = {'label': lab, 'T': T, 'b': b, 'on': on}
            for z in ('B1', 'M1', 'VSa', "VS0'", 'VSb', 'D'):
                pz, vz = p_zone(H['EXEC'], [b], Z[z]), v_zone(fr, T, [b], Z[z])
                row[z] = e(pz, vz, 'speed')
                row['nf'] = vz['nf']
            blocks_onoff.append(row)
        # exit blocked (EXEC, w450)
        r['X1_exec'] = p_exit_blocked(H['EXEC'], W)
        r['X1_all_plans_max'] = max(max(p_exit_blocked(H[a], W).values() or [0.0]) for a in H)
        rows.append(r)
    out['A_rows'] = rows
    out['A_blocks'] = blocks_onoff
    # summaries
    S = {}
    def sgn(x):
        return 0 if abs(x) < 0.01 else (1 if x > 0 else -1)
    for bund, tags in (('VSL', ('A2', 'A3')), ('110', ('A1', 'A4'))):
        for arm in (100, 90, 101):
            xs = [r['dJ%d' % arm] for r in rows if r['tag'] in tags]
            S['sign_%s_%d' % (bund, arm)] = {'neg': sum(sgn(x) < 0 for x in xs), 'zero': sum(sgn(x) == 0 for x in xs),
                                             'pos': sum(sgn(x) > 0 for x in xs), 'range': rng(xs)}
    for arm in (101, 100, 90):
        xs = [r['dJ%d' % arm] for r in rows]
        S['dJ%d_all' % arm] = {'pos': sum(x > 0 for x in xs), 'neg': sum(x < 0 for x in xs), 'range': rng(xs)}
    xs = [r['dJ101_100'] for r in rows]
    S['dJ101_100_all'] = {'neg': sum(x < 0 for x in xs), 'range': rng(xs)}
    S['dFWE100_pos'] = sum(r['dFWE100'] > 0 for r in rows)
    vs = [r for r in rows if r['tag'] in ('A2', 'A3')]
    S['ARM110_minus_REC_VSLstates'] = [[r['label'], r['T'], r['ARM110_minus_REC']] for r in vs]
    S['ARM110_lt_REC_count_le_-0.01'] = sum(r['ARM110_minus_REC'] <= -0.01 for r in vs)
    S['origin_queue_max_abs_vehh'] = max(abs(v) for r in rows for v in r['origin_queue_vehh'].values())
    for arm in (100, 90):
        zs = {}
        for z in ('U', 'B1', 'M1', 'VSa', "VS0'", 'VSb', 'D'):
            xs = [r['zone_vehh_d'][arm][z] for r in rows]
            zs[z] = {'median': med(xs), 'range': rng(xs), 'pos': sum(x > 0 for x in xs)}
        S['zone_vehh_%d' % arm] = zs
    rv = {}
    for z in ('M1', 'VSa', "VS0'", 'VSb'):
        resp = [abs(r['resp100_speed'][z]) for r in rows]
        bias = [abs(r['exec_e_w450'][z]['speed']) for r in rows]
        ratio = [b / a if a > 0 else None for a, b in zip(resp, bias)]
        rv[z] = {'resp_median': med(resp), 'resp_range': rng(resp), 'bias_median': med(bias), 'bias_range': rng(bias),
                 'ratio_median': med(ratio), 'ratio_gt1': sum(1 for x in ratio if x is not None and x > 1)}
    S['resp_vs_bias'] = rv
    eb = {}
    for z in ('U', 'B1', 'cell12', 'M1', 'VSa', "VS0'", 'VSb', 'D'):
        xs = [r['exec_e_w450'][z]['speed'] for r in rows]
        eb[z] = {'range': rng(xs), 'pos': sum(x > 0 for x in xs), 'neg': sum(x < 0 for x in xs),
                 'zero_abs_lt_0.05': sum(abs(x) < 0.05 for x in xs)}
    S['exec_e_speed_w450_12'] = eb
    grp = {}
    for on in (True, False):
        bl = [b for b in blocks_onoff if b['on'] == on]
        grp['on' if on else 'off'] = {'n': len(bl), **{z: statistics.mean(b[z] for b in bl)
                                                     for z in ('B1', 'M1', 'VSa', "VS0'", 'VSb', 'D')}}
    S['block_groups'] = grp
    S['min_frames_per_block'] = min(b['nf'] for b in blocks_onoff)
    S['start_max_abs_speed'] = max(abs(r['start_e'][z]['speed']) for r in rows for z in r['start_e']
                                   if r['start_e'][z]['speed'] is not None)
    S['start_max_abs_stock'] = max(abs(r['start_e'][z]['stock']) for r in rows for z in r['start_e'])
    S['start_frames'] = sorted({r['start_e'][z]['nf'] for r in rows for z in r['start_e']})
    S['R1_obj_bit_diff_states'] = [[r['label'], r['T'], r['R1_obj_diff']] for r in rows if not r['R1_obj_bit_equal']]
    S['R1_obj_max_abs'] = max(abs(r['R1_obj_diff']) for r in rows)
    S['R1_costs_max'] = max(r['R1_costs_max'] for r in rows)
    S['R3_bit_all'] = sum(r['R3_bit'] for r in rows)
    S['repack_token_eq'] = sum(r['repack_token_eq_rec'] for r in rows)
    S['X1_max_all_plans'] = max(r['X1_all_plans_max'] for r in rows)
    S['exit0'] = sum(r['exit_code'] == 0 for r in rows)
    S['jobcheck_hits'] = sum(r['jobcheck_hits'] for r in rows)
    S['jobcheck_r1_ok'] = sum(r['jobcheck_r1_ok'] is True for r in rows)
    out['A_summary'] = S


def probe_P(states, out):
    rows = []
    for s in states['p1']:
        lab, T = s['label'], int(s['T'])
        jd = OUT / 'plant_P' / ('%s_T%06d' % (lab, T))
        pr = load(jd / 'probe.json')
        if pr['spec']['state']['label'] != lab or int(pr['spec']['state']['T']) != T:
            raise ValueError('spec/state mismatch %s %s' % (lab, T))
        hooks = hooks_of(jd)
        ev = pr['evaluations']
        fr = load(OUT / 'fzp_frames' / ('VA_%s.json' % lab))
        Hb = hook_for(pr, hooks, 'EXEC_scalar')
        r = {'label': lab, 'T': T, 'exit_code': pr.get('exit_code'),
             'exec_head10': [b['zone_head_10'] for b in pr['plans']['EXEC']['vsl']],
             'R1_obj_diff': pr['checks']['R1_objective_diff'], 'R1_obj_bit_equal': pr['checks']['R1_objective_bit_equal'],
             'R1_costs_max': pr['checks']['R1_costs_max_abs_diff'],
             'R3_bit': (ev['R3_REPACK_scalar']['objective_veh_h'] == ev['R2_REC_scalar']['objective_veh_h']
                        and ev['R3_REPACK_scalar']['costs'] == ev['R2_REC_scalar']['costs']),
             'null_bit': (ev['ABL_null']['objective_veh_h'] == ev['EXEC_scalar']['objective_veh_h']
                          and ev['ABL_null']['costs'] == ev['EXEC_scalar']['costs'])}
        jc = load(jd / 'jobcheck.json')
        r['jobcheck_hits'] = len(jc.get('hits') or [])
        r['reach_ok'] = sum(1 for k, v in (jc.get('hooks') or {}).items() if k.startswith('ABL_') and v.get('reach_ok') is True)
        r['reach_n'] = sum(1 for k in (jc.get('hooks') or {}) if k.startswith('ABL_'))
        W = [0, 1, 2]
        # base w450 all zones
        r['base'] = {}
        for z in ('U', 'B1', 'cell12', 'M1', 'VSa', "VS0'", 'VSb', 'D'):
            pz, vz = p_zone(Hb, W, Z[z]), v_zone(fr, T, W, Z[z])
            r['base'][z] = {'e_speed': e(pz, vz, 'speed'), 'e_stock': e(pz, vz, 'stock'), 'p_speed': pz['speed'],
                            'v_speed': vz['speed'], 'nf': vz['nf']}
        # metrics per candidate
        r['metrics'] = {}
        r['J_d'] = {}
        r['bit_equal_base'] = {}
        for c in ['null'] + CANDS:
            lab_c = 'ABL_' + c
            Hc = hook_for(pr, hooks, lab_c)
            win = [0] if c == 'C7_initial' else W
            mm = {}
            for mid, z, q in P1_METRICS:
                vz = v_zone(fr, T, win, Z[z])
                e0 = e(p_zone(Hb, win, Z[z]), vz, q)
                ec = e(p_zone(Hc, win, Z[z]), vz, q)
                mm[mid] = {'e0': e0, 'ec': ec}
            r['metrics'][c] = mm
            r['X1_all_max'] = max(r.get('X1_all_max', 0.0), max(p_exit_blocked(Hc, W).values() or [0.0]))
            r['J_d'][c] = ev[lab_c]['objective_veh_h'] - ev['EXEC_scalar']['objective_veh_h']
            r['bit_equal_base'][c] = (Hc['blocks'] == Hb['blocks'] and ev[lab_c]['objective_veh_h']
                                      == ev['EXEC_scalar']['objective_veh_h'] and ev[lab_c]['costs'] == ev['EXEC_scalar']['costs'])
        r['X1_base'] = p_exit_blocked(Hb, W)
        r['params_cells'] = {str(c): {k: Hb['first']['params']['segment_rows'][c][k]
                                      for k in ('v_free', 'rho_crit', 'metanet_a_m', 'segment_length_km')}
                             for c in range(31)}
        r['params_lanes'] = Hb['first']['params']['segment_lanes']
        r['phi_lane'] = Hb['first']['params']['freeway_lane_drop_phi']
        rows.append(r)
    out['P_rows'] = [{k: v for k, v in r.items() if k != 'params_cells'} for r in rows]
    # R table
    tab = {}
    for c in CANDS:
        tab[c] = {}
        for mid, z, q in P1_METRICS:
            thr = 1.0
            Rs = []
            for r in rows:
                m = r['metrics'][c][mid]
                if m['e0'] is None or m['ec'] is None or abs(m['e0']) < thr:
                    continue
                Rs.append(1.0 - abs(m['ec']) / abs(m['e0']))
            n = len(Rs)
            k = sum(1 for x in Rs if x >= 0.5)
            md = med(Rs)
            band = 'A' if md is not None and md >= 0.5 else ('B' if md is not None and 0.2 <= md < 0.5 else 'C')
            tab[c][mid] = {'n': n, 'n_ge_0.5': k, 'n_le_-0.2': sum(1 for x in Rs if x <= -0.2), 'median_R': md,
                           'min_R': min(Rs) if Rs else None, 'band': band,
                           'rule': bool(n >= 6 and k >= math.ceil(2 * n / 3) and md is not None and md >= 0.5),
                           'grows': bool(md is not None and md <= -0.2)}
        tab[c]['J_d'] = {'median': med([r['J_d'][c] for r in rows]), 'range': rng([r['J_d'][c] for r in rows])}
        tab[c]['bit_equal_base_states'] = sum(1 for r in rows if r['bit_equal_base'][c])
    out['P_Rtable'] = tab
    # residual after C9 / C4
    res = {}
    for c in ('C9_lanedrop_both', 'C4_lanedrop', 'C8_antic18'):
        res[c] = {mid: {'median_ec': med([r['metrics'][c][mid]['ec'] for r in rows]),
                        'range_ec': rng([r['metrics'][c][mid]['ec'] for r in rows])}
                  for mid in ('m1', 'm5', 'm2')}
    out['P_residual'] = res
    base = {}
    for z in ('U', 'B1', 'cell12', 'M1', 'VSa', "VS0'", 'VSb', 'D'):
        es = [r['base'][z]['e_speed'] for r in rows]
        et = [r['base'][z]['e_stock'] for r in rows]
        base[z] = {'e_speed_range': rng(es), 'e_speed_pos': sum(x > 0 for x in es), 'e_speed_neg': sum(x < 0 for x in es),
                   'e_stock_range': rng(et), 'e_stock_pos': sum(x > 0 for x in et), 'e_stock_neg': sum(x < 0 for x in et),
                   'p_speed_range': rng([r['base'][z]['p_speed'] for r in rows]),
                   'v_speed_range': rng([r['base'][z]['v_speed'] for r in rows])}
    out['P_base'] = base
    out['P_checks'] = {'exit0': sum(r['exit_code'] == 0 for r in rows), 'jobcheck_hits': sum(r['jobcheck_hits'] for r in rows),
                       'R1_obj_max_abs': max(abs(r['R1_obj_diff']) for r in rows),
                       'R1_obj_bit_diff': [[r['label'], r['T'], r['R1_obj_diff']] for r in rows if not r['R1_obj_bit_equal']],
                       'R1_costs_max': max(r['R1_costs_max'] for r in rows),
                       'R3_bit': sum(r['R3_bit'] for r in rows), 'null_bit': sum(r['null_bit'] for r in rows),
                       'reach_ok': sum(r['reach_ok'] for r in rows), 'reach_n': sum(r['reach_n'] for r in rows),
                       'X1_base_max': max(max(r['X1_base'].values() or [0.0]) for r in rows),
                       'X1_all_plans_max': max(r['X1_all_max'] for r in rows),
                       'exits_seen': sorted({k for r in rows for k in r['X1_base']}),
                       'phi_lane': sorted({r['phi_lane'] for r in rows})}
    return rows


def low_density(scan, cell, L_km, lanes, excl=None):
    ks, ss, ns = [], [], []
    for w in range(int(scan['nw'])):
        t0 = 60.0 * w
        if t0 < 900 or t0 + 60 > 9000 or int(scan['frames'][w]) != 12:
            continue
        if excl and t0 < excl[1] and t0 + 60 > excl[0]:
            continue
        N = sum(scan['cells'][w][cell][l][0] for l in range(4))
        SV = sum(scan['cells'][w][cell][l][1] for l in range(4))
        k = (N / 12.0) / (L_km * lanes)
        yield w, k, N, SV


def p1f(states, prow, out):
    src = load(VP / 'decl' / 'VP_FZP_SOURCES.json')
    runs = {r['label']: r for r in states['runs']}
    res = {}
    pooled = {c: ([], []) for c in range(8, 26)}
    for s in src['sources']:
        arm, seed = s['arm'], int(s['seed'])
        label = 'v3c3-s%d' % seed
        if arm in ('NC3', 'VSL'):
            path = s['cell_scan_reuse']
        else:
            path = OUT / 'fzp_cell' / ('%s_%s.json' % ('VA' if arm in ('VA', 'V-A') else arm, label))
        scan = load(path)
        CB = scan['cell_bounds_m']
        L = [(CB[i + 1] - CB[i]) / 1000.0 for i in range(31)]
        variants = [('all', None)]
        if arm in ('VA', 'V-A'):
            tl = runs[label]['T_low']
            variants.append(('exclVSL', (min(tl), max(tl) + 600)))
        for vname, excl in variants:
            d = {}
            for w, k, N, SV in low_density(scan, 18, L[18], LANES_VIS[18], excl):
                d.setdefault(w, {})[18] = (k, N, SV)
            for c in (16, 17):
                for w, k, N, SV in low_density(scan, c, L[c], LANES_VIS[c], excl):
                    if w in d:
                        d[w][c] = (k, N, SV)
            diffs_a = []   # all three cells low (k <= 12), each N > 0
            diffs_b = []   # cell 18 low only
            for w, cc in d.items():
                if 16 not in cc or 17 not in cc:
                    continue
                k18, N18, S18 = cc[18]
                if N18 <= 0 or cc[16][1] + cc[17][1] <= 0:
                    continue
                dv = S18 / N18 - (cc[16][2] + cc[17][2]) / (cc[16][1] + cc[17][1])
                if k18 <= 12:
                    diffs_b.append(dv)
                    if cc[16][0] <= 12 and cc[17][0] <= 12:
                        diffs_a.append(dv)
            res['%s_%s_%s' % (arm, label, vname)] = {'d18_1617_all3low_median': med(diffs_a), 'n_a': len(diffs_a),
                                                    'd18_1617_18low_median': med(diffs_b), 'n_b': len(diffs_b)}
        if arm == 'NC3':
            for c in range(8, 26):
                for w, k, N, SV in low_density(scan, c, L[c], LANES_VIS[c]):
                    if k <= 12 and N > 0:
                        pooled[c][0].append(k)
                        pooled[c][1].append(SV / N)
    out['P1F_cell18'] = res
    # plant FD at the NC3 low-density point
    pc = prow[0]['params_cells']
    same = all(r['params_cells'] == pc for r in prow)
    fd = {}
    for c in range(8, 26):
        ks, ss = pooled[c]
        if not ks:
            continue
        km, sm = statistics.median(ks), statistics.median(ss)
        p = pc[str(c)]
        V = float(p['v_free']) * math.exp(-((km / float(p['rho_crit'])) ** float(p['metanet_a_m'])) / float(p['metanet_a_m']))
        fd[c] = {'n': len(ks), 'k_med': km, 's_med': sm, 'fd_speed': V, 'fd_minus_vissim': V - sm,
                 'v_free': p['v_free'], 'rho_crit': p['rho_crit'], 'a': p['metanet_a_m']}
    out['P1P_fd'] = {'params_same_all_states': same, 'cells': fd,
                     'M1_mean_fd_minus_vissim': statistics.mean(fd[c]['fd_minus_vissim'] for c in (14, 15))}
    # compare with the C1 spec values (input generated by the producer)
    cmp = {}
    for r in states['p1']:
        sp = load(OUT / 'p1_specs' / ('spec_P_%s_T%06d.json' % (r['label'], int(r['T']))))
        for c, v in sp['ablations']['C1_vfree']['cells'].items():
            cc = int(c)
            if cc in fd:
                cmp.setdefault(c, set()).add((v['k_med'] == fd[cc]['k_med'], v['s_med'] == fd[cc]['s_med']))
    out['P1P_spec_C1_match'] = {c: sorted(list(x)) for c, x in cmp.items()}
    out['P1P_spec_C1_cells'] = sorted(int(c) for c in cmp)


def main():
    outp = Path(sys.argv[1])
    states = load(VP / 'decl' / 'VP_STATES.json')
    out = {'schema': 'vv-recompute/1', 'tool': 'vv_recompute.py'}
    probe_A(states, out)
    prow = probe_P(states, out)
    p1f(states, prow, out)
    # 21-state sign union (B1, cell12, D speed; B1 stock)
    A = out['A_rows']
    P = out['P_rows']
    u = {}
    for z in ('B1', 'cell12', 'D', 'M1', 'VSa', "VS0'", 'VSb', 'U'):
        xs = [r['exec_e_w450'][z]['speed'] for r in A] + [r['base'][z]['e_speed'] for r in P]
        u[z] = {'pos': sum(x > 0 for x in xs), 'neg': sum(x < 0 for x in xs), 'n': len(xs)}
    xs = [r['exec_e_w450']['B1']['stock'] for r in A] + [r['base']['B1']['e_stock'] for r in P]
    u['B1_stock'] = {'pos': sum(x > 0 for x in xs), 'neg': sum(x < 0 for x in xs), 'n': len(xs), 'range': rng(xs)}
    xs = [r['exec_e_w450']['D']['stock'] for r in A] + [r['base']['D']['e_stock'] for r in P]
    u['D_stock'] = {'pos': sum(x > 0 for x in xs), 'neg': sum(x < 0 for x in xs), 'n': len(xs), 'range': rng(xs)}
    out['union21'] = u
    tmp = outp.with_name(outp.name + '.tmp%d' % os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, outp)
    print('VV_RECOMPUTE done', outp)


if __name__ == '__main__':
    main()
