# V3b (VSL_OFFLINE, data-after declaration): read V3 plant-probe outputs (VS/out/v3_<state>.json) and the
# recorded PFO initial objective (VS/out/v1_dec_vsl.json) and tabulate the plant response by cell/zone.
# Base for differences = variant 'v110_all' (FW_E seg13 = 110 in all three blocks). No model run.
import json, sys, os
VS = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/vsl/out'
STATES = [('a1_T001800', 'a1', 1800), ('a1_T003600', 'a1', 3600), ('cx_T001800', 'joint', 1800), ('cx_T004500', 'joint', 4500)]
ZONES = {'U_0_4200': (0, 4200), 'B1_4200_5300': (4200, 5300), 'M1_5300_6300': (5300, 6300),
         'VSa_6300_6800': (6300, 6800), 'VSb_6800_8100': (6800, 8100), 'D_8100_10800': (8100, 10800)}
NEAR0 = 0.5  # km/h: plant zone speed change below this is called ~0


def cells(geom):
    x, out = 0.0, []
    for i, L in enumerate(geom['lengths_km']):
        out.append((i, x * 1000, (x + L) * 1000, (x + L / 2) * 1000))
        x += L
    return out, x * 1000


def tmean(rows, key, i):
    # time-weighted mean over plant steps (dt = t_after - t)
    num = den = 0.0
    for r in rows:
        dt = r['t_after'] - r['t']
        x = r[key][i] if r.get(key) is not None else None
        if x is None:
            continue
        num += x * dt; den += dt
    return num / den if den else None


def zone_of(mid):
    for z, (a, e) in ZONES.items():
        if a <= mid < e:
            return z
    return None


def analyse(path, pfo_initial):
    d = json.load(open(path, encoding='utf-8'))
    res = {'state_time_sec': d.get('state_time_sec'), 'errors': d.get('errors'), 'setup_sec': d.get('setup_sec'),
           'total_sec': d.get('total_sec'), 'seed_vsl_axes_FW_E13': [a for a in d.get('seed_vsl_axes', []) if a['key'] == 'FW_E__seg13'],
           'config': d.get('config'), 'variants': {}}
    V = {v['label']: v for v in d['variants']}
    # a variant whose action token equals an earlier one was a cache hit (no plant steps recorded):
    # reuse that earlier variant's recorded steps (same action, same plant response).
    by_token = {}
    for v in d['variants']:
        if v.get('rows'):
            by_token.setdefault(v.get('token'), v)
    for v in d['variants']:
        if not v.get('rows') and v.get('token') in by_token and not v.get('error'):
            v['rows'] = by_token[v['token']]['rows']
            v['rows_from_cache_hit_of'] = by_token[v['token']]['label']
    seed = V.get('seed')
    res['seed_objective'] = seed.get('objective_veh_h') if seed else None
    res['recorded_pfo_initial'] = pfo_initial
    res['seed_minus_recorded'] = (seed['objective_veh_h'] - pfo_initial) if seed and seed.get('objective_veh_h') is not None and pfo_initial is not None else None
    geom = d.get('geom')
    if not geom:
        return res
    cl, total_m = cells(geom)
    res['cells'] = [dict(i=i, a_m=round(a, 1), e_m=round(e, 1), mid_m=round(m, 1), lanes=geom['lanes'][i], zone=zone_of(m)) for i, a, e, m in cl]
    res['chain_total_m'] = total_m
    res['ramp_cells'] = geom.get('ramps'); res['off_cells'] = geom.get('offramps')
    res['component_config'] = d.get('component_config')
    base = V.get('v110_all')
    for lab, v in V.items():
        if v.get('error') or not v.get('rows'):
            res['variants'][lab] = {'error': v.get('error'), 'n_rows': len(v.get('rows') or [])}
            continue
        rows = v['rows']
        lanes = geom['lanes']
        # the plant step end is the next step's start (state.time_sec is set by the caller before each
        # substep); the last step ends at the 450 s horizon (3 x 150 s blocks).
        for a, b in zip(rows, rows[1:]):
            a['t_after'] = b['t']
        rows[-1]['t_after'] = rows[0]['t'] + 450.0
        for r in rows:  # derived flow per cell (veh/h, all lanes) = k * v * lanes
            r['qd'] = [r['dens'][i] * r['spd'][i] * lanes[i] for i in range(len(r['dens']))]
        per = [dict(i=i, v=tmean(rows, 'spd', i), k=tmean(rows, 'dens', i), q=tmean(rows, 'qd', i)) for i, *_ in cl]
        rec = {'objective': v['objective_veh_h'], 'costs': v['costs'], 'n_rows': len(rows), 't0': rows[0]['t'], 't1': rows[-1]['t'],
               'vsl_by_cell': v.get('vsl_by_cell'), 'plan_vsl': v.get('plan_vsl'), 'cell_mean': per,
               'stock_veh_h': sum(sum(r['dens'][i] * geom['lengths_km'][i] * lanes[i] for i in range(len(lanes))) * (r['t_after'] - r['t']) / 3600.0 for r in rows),
               'origin_q_mean': sum(r['origin_q'] * (r['t_after'] - r['t']) for r in rows) / sum(r['t_after'] - r['t'] for r in rows),
               'ramp_rel_mean': {k: sum(r['ramp_rel'].get(k, 0) * (r['t_after'] - r['t']) for r in rows) / sum(r['t_after'] - r['t'] for r in rows) for k in rows[0]['ramp_rel']}}
        # zone means (length-weighted over cells, time mean)
        zm = {}
        for z in ZONES:
            ids = [c['i'] for c in res['cells'] if c['zone'] == z]
            if not ids:
                continue
            L = {c['i']: (c['e_m'] - c['a_m']) for c in res['cells']}
            w = sum(L[i] for i in ids)
            zm[z] = {'v': sum(per[i]['v'] * L[i] for i in ids) / w, 'k': sum(per[i]['k'] * L[i] for i in ids) / w,
                     'veh_h': sum(r['dens'][i] * L[i] / 1000.0 * lanes[i] * (r['t_after'] - r['t']) / 3600.0 for r in rows for i in ids)}
        rec['zones'] = zm
        # 150 s block zone speeds
        blocks = []
        for b in range(3):
            t0 = rows[0]['t'] + 150 * b
            rr = [r for r in rows if t0 <= r['t'] < t0 + 150]
            if rr:
                blocks.append({z: sum(tmean(rr, 'spd', c['i']) * (c['e_m'] - c['a_m']) for c in res['cells'] if c['zone'] == z) /
                                  max(1e-9, sum((c['e_m'] - c['a_m']) for c in res['cells'] if c['zone'] == z)) for z in zm})
        rec['block_zone_speed'] = blocks
        res['variants'][lab] = rec
    if base and 'v110_all' in res['variants'] and 'objective' in res['variants']['v110_all']:
        b = res['variants']['v110_all']
        for lab, rec in res['variants'].items():
            if 'objective' not in rec:
                continue
            rec['d_objective'] = rec['objective'] - b['objective']
            rec['d_costs'] = {k: rec['costs'][k] - b['costs'].get(k, 0.0) for k in rec['costs']}
            rec['d_costs_signals_sum'] = sum(v for k, v in rec['d_costs'].items() if k not in ('FW_E', 'FW_W', 'PASSIVE_OMEGA'))
            rec['d_cell'] = [dict(i=c['i'], dv=rec['cell_mean'][c['i']]['v'] - b['cell_mean'][c['i']]['v'],
                                  dk=rec['cell_mean'][c['i']]['k'] - b['cell_mean'][c['i']]['k'],
                                  dq=rec['cell_mean'][c['i']]['q'] - b['cell_mean'][c['i']]['q']) for c in res['cells']]
            rec['d_zone'] = {z: {'dv': rec['zones'][z]['v'] - b['zones'][z]['v'], 'dveh_h': rec['zones'][z]['veh_h'] - b['zones'][z]['veh_h']}
                             for z in rec['zones']}
            rec['d_zone_sign'] = {z: (0 if abs(x['dv']) < NEAR0 else (1 if x['dv'] > 0 else -1)) for z, x in rec['d_zone'].items()}
            rec['d_stock_veh_h'] = rec['stock_veh_h'] - b['stock_veh_h']
            rec['d_origin_q_mean'] = rec['origin_q_mean'] - b['origin_q_mean']
            rec['d_ramp_rel_mean'] = {k: rec['ramp_rel_mean'][k] - b['ramp_rel_mean'].get(k, 0.0) for k in rec['ramp_rel_mean']}
            rec['d_block_zone_speed'] = [{z: blk[z] - bb[z] for z in blk} for blk, bb in zip(rec['block_zone_speed'], b['block_zone_speed'])]
    return res


def main():
    v1 = json.load(open(VS + '/v1_dec_vsl.json', encoding='utf-8'))
    pfo = {(r['arm'], r['T']): (r.get('pfo') or {}).get('initial_omega') for r in v1['decisions']}
    out = {}
    lines = []
    for lab, arm, T in STATES:
        p = f'{VS}/v3_{lab}.json'
        if not os.path.exists(p):
            out[lab] = {'missing': p}
            continue
        r = analyse(p, pfo.get((arm, T)))
        out[lab] = r
        lines.append(f"## {lab} seed={r.get('seed_objective')} recorded_pfo_initial={r.get('recorded_pfo_initial')} diff={r.get('seed_minus_recorded')} errors={r.get('errors')} chain_m={r.get('chain_total_m')}")
        for v, rec in r['variants'].items():
            if 'd_objective' in rec:
                lines.append(f"  {v:11s} dJ={rec['d_objective']:+.4f} dFW_E={rec['d_costs'].get('FW_E', 0):+.4f} dFW_W={rec['d_costs'].get('FW_W', 0):+.4f} dPASS={rec['d_costs'].get('PASSIVE_OMEGA', 0):+.4f} dSIG={rec['d_costs_signals_sum']:+.4f} dstock={rec['d_stock_veh_h']:+.4f} dorig={rec['d_origin_q_mean']:+.3f}")
                lines.append('      dv ' + ' '.join(f"{z.split('_')[0]} {x['dv']:+.2f}" for z, x in rec['d_zone'].items()) +
                             ' | dvh ' + ' '.join(f"{z.split('_')[0]} {x['dveh_h']:+.4f}" for z, x in rec['d_zone'].items()))
            else:
                lines.append(f"  {v:11s} {rec}")
    json.dump(out, open(sys.argv[1] + '.json', 'w', encoding='utf-8'), indent=1)
    open(sys.argv[1] + '.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
