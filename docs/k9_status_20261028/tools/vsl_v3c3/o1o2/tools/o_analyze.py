# -*- coding: utf-8 -*-
"""O1/O2 analysis (vsl_v3c3 o1o2, 2026-10-27 KST). Reads probe outputs and FZP frame scans; writes tables.
Rules: PRE_O1O2.md (pinned before any analysis run). Missing inputs -> "못 냄" rows, never guessed.
Usage: python -B o_analyze.py <O dir>
"""
import csv, json, math, os, sys

O = sys.argv[1]
OUT = os.path.join(O, 'out')
CP_OLD = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/vsl/out'
EPS_J = 0.01          # veh.h dead zone for the sign of a model objective difference
EPS_V = 0.5           # km/h dead zone for speed signs (VSL_OFFLINE section 3.4 rule)
ZONES = {'U': range(0, 8), 'B1': range(8, 14), 'M1': range(14, 16), 'VSa': range(16, 19), 'VSb': range(19, 26), 'D': range(26, 31)}
CELL_B = [0.0, 526.2879, 1052.5758, 1578.8638, 2105.1517, 2631.4396, 3157.7275, 3684.0155, 4210.3034, 4286.333,
          4542.5389, 4736.5913, 4894.3955, 5078.6373, 5262.8792, 5789.1672, 6315.4551, 6490.8844, 6666.3137, 6841.743,
          7041.7112, 7241.6793, 7334.5286, 7498.7905, 7663.0524, 7827.3143, 8320.0999, 8812.8855, 9305.6711, 9798.4567,
          10291.2424, 10784.028]
L_KM = [(b - a) / 1000.0 for a, b in zip(CELL_B, CELL_B[1:])]
O1_STATES = [('o1_a1_T001800', '64cf A1 T=1800', 'v3_a1_T001800'), ('o1_a1_T003600', '64cf A1 T=3600', 'v3_a1_T003600'),
             ('o1_cx_T001800', '64cf joint T=1800', 'v3_cx_T001800'), ('o1_cx_T004500', '64cf joint T=4500', 'v3_cx_T004500'),
             ('o1_b31_T001800', 'v3c3-s31 B T=1800', None), ('o1_b41_T001800', 'v3c3-s41 B T=1800', None),
             ('o1_b43_T001800', 'v3c3-s43 B T=1800', None), ('o1_b41_T003600', 'v3c3-s41 B T=3600', None),
             ('o1_b43_T003600', 'v3c3-s43 B T=3600', None)]
O2_T = [1800, 1950, 2100, 2250, 2400, 2550]
B_SRC = {'b31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31'}


def load(p):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def sgn(x, eps):
    if x is None:
        return None
    return '0' if abs(x) < eps else ('+' if x > 0 else '-')


def zone_speed(block, cells):
    num = sum((block['stock_veh'][i] or 0.0) * (block['speed_kmh'][i] or 0.0) for i in cells if block['speed_kmh'][i] is not None)
    den = sum(block['stock_veh'][i] for i in cells if block['speed_kmh'][i] is not None)
    return num / den if den > 1e-9 else None


def zone_stock(block, cells):
    return sum(block['stock_veh'][i] for i in cells)


def zone_flow(block, cells):
    return sum(block['flow_veh_h'][i] * L_KM[i] for i in cells) / sum(L_KM[i] for i in cells)


def all_blocks_mean(blocks, fn, cells):
    """time-weighted over the 3 blocks (450 s); speed weighted by stock."""
    bs = [blocks[k] for k in sorted(blocks, key=int)]
    if fn is zone_speed:
        num = sum(zone_speed(b, cells) * zone_stock(b, cells) * b['dt_sec'] for b in bs if zone_speed(b, cells) is not None)
        den = sum(zone_stock(b, cells) * b['dt_sec'] for b in bs if zone_speed(b, cells) is not None)
        return num / den if den > 1e-9 else None
    return sum(fn(b, cells) * b['dt_sec'] for b in bs) / sum(b['dt_sec'] for b in bs)


def own_cost_key(costs):
    for k in costs:
        if k == 'FW_E' or k.endswith('FW_E'):
            return k
    return None


# ------------------------------------------------------------------ O1
def o1():
    res = {}
    for label, name, old in O1_STATES:
        d = load(os.path.join(OUT, label + '.json'))
        if d is None:
            res[label] = {'name': name, 'status': '못 냄 (출력 없음)'}
            continue
        r = {'name': name, 'status': 'ok', 'errors': d.get('errors'), 'state_time_sec': d.get('state_time_sec'),
             'lane_group_roads': (d.get('geom') or {}).get('lane_group_roads'), 'zone_keys': d.get('zone_keys'),
             'original_params': {k: v for k, v in (d.get('original_params') or {}).items() if k in ('phi', 'rho_link')},
             'seed_plan_vsl_zone13': None, 'configs': {}}
        base = None
        for c in d.get('configs', []):
            vv = {v['label']: v for v in c.get('variants', [])}
            row = {'phi': c['phi'], 'rho_mult': c['rho_mult'], 'error': c.get('error'), 'wall_sec': c.get('wall_sec'),
                   'applied': c.get('applied')}
            J = {k: (v.get('objective_veh_h') if 'error' not in v else None) for k, v in vv.items()}
            row['J'] = J
            row['variant_errors'] = {k: v['error'] for k, v in vv.items() if 'error' in v}
            for v in ('v100', 'v90'):
                if J.get(v) is not None and J.get('v110') is not None:
                    row['dJ_' + v] = J[v] - J['v110']
                    row['sign_' + v] = sgn(row['dJ_' + v], EPS_J)
                    ck = own_cost_key(vv['v110'].get('costs') or {})
                    row['dOwn_' + v] = ((vv[v]['costs'][ck] - vv['v110']['costs'][ck]) if ck else None)
                    row['dSpeed_' + v] = {z: (lambda a, b: (a - b) if a is not None and b is not None else None)(
                        all_blocks_mean(vv[v]['blocks'], zone_speed, cells), all_blocks_mean(vv['v110']['blocks'], zone_speed, cells))
                        for z, cells in ZONES.items()}
                    row['dFlow_' + v] = {z: all_blocks_mean(vv[v]['blocks'], zone_flow, cells) - all_blocks_mean(vv['v110']['blocks'], zone_flow, cells)
                                         for z, cells in ZONES.items()}
            row['exceed_sec_cells16_25'] = {k: sum(v['exceed_rho_link_sec'][16:26]) for k, v in vv.items() if 'exceed_rho_link_sec' in v}
            row['exceed_sec_cells8_15'] = {k: sum(v['exceed_rho_link_sec'][8:16]) for k, v in vv.items() if 'exceed_rho_link_sec' in v}
            row['vsl_cells_v90'] = sorted(int(k) for k, s in (vv.get('v90', {}).get('vsl_by_cell') or {}).items() if any(x < 109.5 for x in s))
            row['ramp_rel_mean_v110'] = vv.get('v110', {}).get('ramp_rel_mean')
            row['ramp_rel_mean_v90'] = vv.get('v90', {}).get('ramp_rel_mean')
            row['speed_v110'] = {z: all_blocks_mean(vv['v110']['blocks'], zone_speed, cells) for z, cells in ZONES.items()} if 'v110' in vv and 'blocks' in vv['v110'] else None
            r['configs'][c['label']] = row
            if c['label'] == 'base':
                base = row
        if base is not None:
            for lab, row in r['configs'].items():
                for v in ('v100', 'v90'):
                    if row.get('sign_' + v) is not None and base.get('sign_' + v) is not None:
                        row['flip_' + v] = row['sign_' + v] != base['sign_' + v]
                        row['strict_flip_' + v] = {row['sign_' + v], base['sign_' + v]} == {'+', '-'}
            rep = r['configs'].get('base_repeat')
            if rep:
                r['determinism_max_abs_dJ'] = max(abs((rep['J'].get(k) or 0) - (base['J'].get(k) or 0)) for k in base['J'])
        if old:
            od = load(os.path.join(CP_OLD, old + '.json'))
            if od and base:
                ov = {v['label']: v.get('objective_veh_h') for v in od.get('variants', [])}
                r['regression_vs_vsl_offline'] = {
                    'old_J': {k: ov.get(k) for k in ('v110_all', 'v100_all', 'v90_all')},
                    'new_J': {k: base['J'].get(k) for k in ('v110', 'v100', 'v90')},
                    'old_dJ100': (ov['v100_all'] - ov['v110_all']) if ov.get('v100_all') is not None else None,
                    'old_dJ90': (ov['v90_all'] - ov['v110_all']) if ov.get('v90_all') is not None else None}
        res[label] = r
    return res


# ------------------------------------------------------------------ O2
def fzp_blocks(scan, T):
    """VISSIM blocks [T+150b, T+150(b+1)) from a frame scan: same keys as plant blocks."""
    if scan is None:
        return None
    out = {}
    for b in range(3):
        lo, hi = T + 150.0 * b, T + 150.0 * (b + 1)
        ks = [k for k, t in enumerate(scan['frames']) if lo <= t < hi]
        if len(ks) < 25:
            return None
        nf = len(ks)
        N = [sum(scan['N'][k][i] for k in ks) for i in range(31)]
        SV = [sum(scan['SV'][k][i] for k in ks) for i in range(31)]
        out[str(b)] = {'dt_sec': 150.0, 'n_frames': nf,
                       'stock_veh': [n / nf for n in N],
                       'speed_kmh': [(s / n) if n > 0 else None for s, n in zip(SV, N)],
                       'flow_veh_h': [s * 5.0 / (L_KM[i] * 5.0 * nf) for i, s in enumerate(SV)]}
    return out


def compare(plant, vis):
    """per block, per zone: plant - VISSIM for speed, stock, flow; plus per-cell speed error cells 14..25."""
    res = {}
    for b in ('0', '1', '2'):
        if b not in plant or b not in vis:
            continue
        pb, vb = plant[b], vis[b]
        z = {}
        for zn, cells in ZONES.items():
            ps, vs = zone_speed(pb, cells), zone_speed(vb, cells)
            z[zn] = {'speed_p': ps, 'speed_v': vs, 'e_speed': (ps - vs) if ps is not None and vs is not None else None,
                     'stock_p': zone_stock(pb, cells), 'stock_v': zone_stock(vb, cells),
                     'e_stock': zone_stock(pb, cells) - zone_stock(vb, cells),
                     'flow_p': zone_flow(pb, cells), 'flow_v': zone_flow(vb, cells),
                     'e_flow': zone_flow(pb, cells) - zone_flow(vb, cells)}
        cells = {}
        for i in range(14, 26):
            p, v = pb['speed_kmh'][i], vb['speed_kmh'][i]
            cells[str(i)] = {'p': p, 'v': v, 'e': (p - v) if p is not None and v is not None else None}
        res[b] = {'zones': z, 'cells': cells}
    return res


def meters_of(path):
    out = {}
    try:
        with open(path, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                if row['kind'] == 'ramp_meter':
                    out[row['id']] = (float(row['rate_vph']) if row['rate_vph'] else None, float(row['green_sec']) if row['green_sec'] else None)
    except Exception as e:
        return {'error': repr(e)}
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def o2():
    scans = {k: load(os.path.join(OUT, 'fzp', k + '.json')) for k in ('window_s29', 'off_s29', 'b31', 'b41', 'b43')}
    res = {'states': {}, 'summary': {}, 'scans_present': {k: v is not None for k, v in scans.items()}}
    for arm, scan_key, src in (('win', 'window_s29', 'window'), ('off', 'off_s29', 'off')):
        for T in O2_T:
            label = 'o2_%s_T%06d' % (arm, T)
            d = load(os.path.join(OUT, label + '.json'))
            vis = fzp_blocks(scans[scan_key], T)
            if d is None or vis is None or not d.get('configs'):
                res['states'][label] = {'status': '못 냄 (%s)' % ('probe 출력 없음' if d is None else 'FZP 스캔 없음')}
                continue
            vv = {v['label']: v for v in d['configs'][0]['variants']}
            seed, cf = vv.get('seed'), vv.get('v110' if arm == 'win' else 'v90')
            st = {'status': 'ok', 'seed_plan_vsl_zone': (seed or {}).get('plan_vsl_zone'), 'cf_plan_vsl_zone': (cf or {}).get('plan_vsl_zone'),
                  'J_seed': (seed or {}).get('objective_veh_h'), 'J_cf': (cf or {}).get('objective_veh_h'),
                  'fidelity': compare(seed['blocks'], vis) if seed and 'blocks' in seed else None}
            if seed and cf and 'blocks' in seed and 'blocks' in cf:
                on, offb = (seed, cf) if arm == 'win' else (cf, seed)
                st['plant_d90m110'] = {b: {zn: {'speed': (lambda a, c: (a - c) if a is not None and c is not None else None)(
                    zone_speed(on['blocks'][b], cells), zone_speed(offb['blocks'][b], cells)),
                    'flow': zone_flow(on['blocks'][b], cells) - zone_flow(offb['blocks'][b], cells),
                    'stock': zone_stock(on['blocks'][b], cells) - zone_stock(offb['blocks'][b], cells)}
                    for zn, cells in ZONES.items()} for b in ('0', '1', '2') if b in on['blocks'] and b in offb['blocks']}
                st['plant_dJ_90m110'] = on['objective_veh_h'] - offb['objective_veh_h']
            dec = 'D:/VISSIM_handoff/20261024/raw/%s/sdmpc/decisions_sdmpc31_sdmpc8100_s29' % src
            st['meters'] = {str(t): meters_of(dec + '/action_%06d.csv' % t) for t in (T - 150, T, T + 150, T + 300)}
            res['states'][label] = st
        # summary over the 6 T
        summ = {}
        for b in ('0', '1', '2'):
            for zn in ZONES:
                es = [res['states'].get('o2_%s_T%06d' % (arm, T), {}).get('fidelity', {}) for T in O2_T]
                e_speed = [e[b]['zones'][zn]['e_speed'] for e in es if e and b in e]
                e_stock = [e[b]['zones'][zn]['e_stock'] for e in es if e and b in e]
                e_flow = [e[b]['zones'][zn]['e_flow'] for e in es if e and b in e]
                summ['%s|%s' % (b, zn)] = {'n': len(e_speed), 'bias_speed': mean(e_speed), 'mae_speed': mean([abs(x) for x in e_speed if x is not None]),
                                          'bias_stock': mean(e_stock), 'mae_stock': mean([abs(x) for x in e_stock]),
                                          'bias_flow': mean(e_flow), 'mae_flow': mean([abs(x) for x in e_flow])}
        res['summary'][arm] = summ
    # VISSIM window - off at the same T and block (not a clean VSL pair)
    wo = {}
    for T in O2_T:
        vw, vo = fzp_blocks(scans['window_s29'], T), fzp_blocks(scans['off_s29'], T)
        if vw and vo:
            wo[str(T)] = {b: {zn: {'speed': (lambda a, c: (a - c) if a is not None and c is not None else None)(zone_speed(vw[b], cells), zone_speed(vo[b], cells)),
                                   'flow': zone_flow(vw[b], cells) - zone_flow(vo[b], cells),
                                   'stock': zone_stock(vw[b], cells) - zone_stock(vo[b], cells)}
                              for zn, cells in ZONES.items()} for b in ('0', '1', '2')}
    res['vissim_window_minus_off'] = wo
    # v3c3 B states: VSL-off fidelity (plant v110 of the base config vs the B run FZP)
    bres = {}
    for s in ('b31', 'b41', 'b43'):
        for T in (1800, 3600):
            label = 'o1_%s_T%06d' % (s, T)
            d = load(os.path.join(OUT, label + '.json'))
            vis = fzp_blocks(scans[s], T)
            if d is None or vis is None:
                bres[label] = {'status': '못 냄 (%s)' % ('probe 출력 없음' if d is None else 'FZP 스캔 없음')}
                continue
            base = [c for c in d.get('configs', []) if c['label'] == 'base']
            vv = {v['label']: v for v in base[0]['variants']} if base else {}
            if 'v110' not in vv or 'blocks' not in vv['v110']:
                bres[label] = {'status': '못 냄 (v110 없음)'}
                continue
            bres[label] = {'status': 'ok', 'fidelity': compare(vv['v110']['blocks'], vis),
                           'plant_d90m110': {b: {zn: {'speed': (lambda a, c: (a - c) if a is not None and c is not None else None)(
                               zone_speed(vv['v90']['blocks'][b], cells), zone_speed(vv['v110']['blocks'][b], cells)),
                               'flow': zone_flow(vv['v90']['blocks'][b], cells) - zone_flow(vv['v110']['blocks'][b], cells)}
                               for zn, cells in ZONES.items()} for b in ('0', '1', '2')} if 'v90' in vv and 'blocks' in vv['v90'] else None}
    res['v3c3_B_vsl_off_fidelity'] = bres
    # v3c3 VSL-only - NC3 (VISSIM) at the same T windows, if the scans exist
    vn = {}
    for s in ('31', '41', '43'):
        sv, sn = load(os.path.join(OUT, 'fzp', 'vsl_s%s.json' % s)), load(os.path.join(OUT, 'fzp', 'nc3_s%s.json' % s))
        for T in (1800, 3600):
            a, c = fzp_blocks(sv, T), fzp_blocks(sn, T)
            if a is None or c is None:
                vn['s%s_T%d' % (s, T)] = {'status': 'pending (VSL 런 FZP 스캔 없음)' if sv is None else ('못 냄' if c is None else 'pending')}
                continue
            vn['s%s_T%d' % (s, T)] = {'status': 'ok', 'd': {b: {zn: {'speed': (lambda x, y: (x - y) if x is not None and y is not None else None)(zone_speed(a[b], cells), zone_speed(c[b], cells)),
                                                                    'flow': zone_flow(a[b], cells) - zone_flow(c[b], cells)}
                                                               for zn, cells in ZONES.items()} for b in ('0', '1', '2')}}
    res['v3c3_vissim_vsl_minus_nc3'] = vn
    return res


def main():
    r = {'schema': 'vsl_v3c3_o1o2_tables/1', 'eps_J_veh_h': EPS_J, 'eps_speed_kmh': EPS_V, 'zones_cells': {k: [min(v), max(v)] for k, v in ZONES.items()},
         'o1': o1(), 'o2': o2()}
    tmp = os.path.join(OUT, 'o1o2_tables.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(OUT, 'o1o2_tables.json'))
    print('ok')


if __name__ == '__main__':
    main()
