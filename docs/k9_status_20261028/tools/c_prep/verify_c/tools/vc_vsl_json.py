# vc_vsl_json.py -- independent read of VSL gradient/price/selection records in decision JSON (verify_c V4). Read-only.
import json, sys, os, glob, re, gc, time

A1 = 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
JT = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
A1_T = (1650, 1800, 1950, 3000, 3450, 3600, 3750, 3900, 4050, 4200, 4350, 4500, 4650)
JT_T = (1650, 1800, 1950, 3450, 3900, 4350, 4500, 4650)

def vsl_seg13(obj):
    """Return the seg13 speed in a control dict ('vsl' map), by key containing 'seg13' or 'S13'."""
    v = obj.get('vsl') if isinstance(obj, dict) else None
    if not isinstance(v, dict): return None
    return {k: val for k, val in v.items() if ('seg13' in k or k.endswith('S13'))}

def detail(path):
    d = json.load(open(path, encoding='utf-8'))
    m = d.get('metadata', {}); j = m.get('joint_leader_selection')
    r = {'file': os.path.basename(path), 'sim_sec': m.get('sim_sec'), 'has_jls': isinstance(j, dict)}
    r['applied_vsl_seg13'] = vsl_seg13(d)
    fut = (d.get('diagnostics', {}).get('sdmpc_prediction_sequence') or {}).get('future') or []
    r['plan_vsl_seg13_future'] = [vsl_seg13(x) for x in fut]
    if not isinstance(j, dict):
        return r
    g13 = [dict(block=x['block'], own=x['own'], external=x['external'], total=x['total'], method=x['derivative_method'],
                stencil=x['stencil']) for x in j['gradient_rows'] if x['kind'] == 'vsl' and x['key'] == 'FW_E__seg13']
    r['grad_seg13_rows'] = g13
    r['grad_vsl_pos_gt1e9'] = [(x['key'], x['block'], x['total']) for x in j['gradient_rows'] if x['kind'] == 'vsl' and x['total'] > 1e-9]
    coords = j['coordinates']
    loc = []
    pmax = 0.0
    for lr in j['local_rows']:
        own = lr['owner']; cs = [c for c in coords if c['owner'] == own]
        if len(cs) != len(lr['step']):
            loc.append({'owner': own, 'len_mismatch': [len(cs), len(lr['step'])]}); continue
        for c, st, pg, og, eg in zip(cs, lr['step'], lr['price_gradient'], lr['own_gradient'], lr['externality_gradient']):
            if c['kind'] == 'vsl':
                pmax = max(pmax, abs(pg))
                if c['key'] == 'FW_E__seg13':
                    loc.append({'cap': lr['cap'], 'iteration': lr['iteration'], 'block': c['block'], 'step': st,
                                'price_gradient': pg, 'own': og, 'ext': eg})
    r['local_seg13'] = loc
    r['local_vsl_price_grad_absmax'] = pmax
    big = []
    for lr in j['local_rows']:
        cs = [c for c in coords if c['owner'] == lr['owner']]
        if len(cs) != len(lr['step']): continue
        for c, st, pg in zip(cs, lr['step'], lr['price_gradient']):
            if c['kind'] == 'vsl' and abs(st) >= 0.04545:
                big.append((lr['cap'], lr['iteration'], c['key'], c['block'], round(st, 4), round(pg, 3)))
    r['local_vsl_steps_ge_one_notch'] = big
    pf = j.get('pfo_warm_start') or {}
    r['pfo'] = {'initial_omega_objective': pf.get('initial_omega_objective'), 'selected_omega_objective': pf.get('selected_omega_objective'),
                'trial_rows': [(t.get('iteration'), t.get('owned_cost'), t.get('omega_cost'), t.get('feasible')) for t in (pf.get('trial_rows') or [])]}
    r['candidates'] = [(c.get('np_cap'), c.get('nuf_target'), c.get('status'), c.get('objective'), c.get('feasible')) for c in j.get('candidates', [])]
    r['held_objective'] = j.get('held_objective'); r['selected_objective'] = j.get('selected_objective')
    ohc = j.get('original_held_candidate') or {}
    r['original_held_candidate'] = {k: ohc.get(k) for k in ('evaluated', 'selected', 'original_held_objective', 'objective', 'reference_source')}
    mna = j.get('meter_neighbor_audit') or {}
    r['meter_audit'] = {'baseline_objective': mna.get('baseline_objective'), 'selected': mna.get('selected'),
                        'best_candidates': sorted(((c.get('objective'), c.get('candidate')) for c in mna.get('candidates', []) if c.get('objective') is not None))[:3]}
    r['dual_updates'] = [(u.get('cap'), u.get('nuf_target'), u.get('iteration'), u.get('before'), u.get('after'), u.get('prices_used')) for u in j.get('iteration_dual_updates', [])]
    r['prices_scaled'] = (j.get('price_state') or {}).get('prices_scaled')
    r['policy_proximal'] = (j.get('policy') or {}).get('proximal'); r['policy_fd_vsl'] = (j.get('policy') or {}).get('fd_vsl_kmh')
    return r

def sweep(dirpath):
    files = sorted(glob.glob(dirpath + '/action_*.json'))
    files = [f for f in files if re.search(r'action_\d{6}\.json$', f)]
    res = {'n_files': len(files), 'decisions_with_jls': [], 'rows': 0, 'neg': 0, 'zero': 0, 'pos': 0, 'pos_gt1e9': [],
           'methods': {}, 'stencils': {}, 'min': None, 'max': None}
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        j = d.get('metadata', {}).get('joint_leader_selection')
        if isinstance(j, dict):
            T = d['metadata'].get('sim_sec'); res['decisions_with_jls'].append(T)
            for x in j['gradient_rows']:
                if x['kind'] != 'vsl': continue
                v = x['total']; res['rows'] += 1
                if v < 0: res['neg'] += 1
                elif v == 0: res['zero'] += 1
                else: res['pos'] += 1
                if v > 1e-9: res['pos_gt1e9'].append((T, x['key'], x['block'], v))
                res['methods'][x['derivative_method']] = res['methods'].get(x['derivative_method'], 0) + 1
                sk = json.dumps(x['stencil']); res['stencils'][sk] = res['stencils'].get(sk, 0) + 1
                res['min'] = v if res['min'] is None else min(res['min'], v)
                res['max'] = v if res['max'] is None else max(res['max'], v)
        del d; gc.collect()
    return res

if __name__ == '__main__':
    out = sys.argv[1]; t0 = time.time()
    R = {'A1': {}, 'joint': {}}
    for T in A1_T:
        R['A1'][T] = detail(f'{A1}/action_{T:06d}.json'); gc.collect()
    for T in JT_T:
        R['joint'][T] = detail(f'{JT}/action_{T:06d}.json'); gc.collect()
    R['joint_sweep'] = sweep(JT)
    R['sec'] = round(time.time() - t0, 1)
    json.dump(R, open(out, 'w', encoding='utf-8'), indent=1, default=str)
    print('done', R['sec'])
