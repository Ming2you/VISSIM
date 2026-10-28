# V1 (VSL_OFFLINE, data-after declaration): read codex-style SDMPC decision JSONs (read only)
# and extract every VSL-related plant/optimizer record: written VSL, secant gradient rows,
# local QP rows (own/ext/price gradient and step on VSL axes), PFO rows, trial rows,
# candidates, dual updates, objective summary. No model run. One JSON at a time.
# Usage: python -B v1_dec_vsl.py <out_json>
import json, glob, os, re, sys, time, csv, hashlib, ctypes, collections
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

RUNS = {
    'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
    'joint': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
    'freeway_only': 'D:/VISSIM_handoff/20261024/raw/freeway_only/sdmpc/decisions_sdmpc31_sdmpc8100_s29',
}
FIXED = {
    'a1': [1650, 1800, 1950, 3000, 3450, 3600, 3750, 3900, 4050, 4200, 4350, 4500, 4650],
    'joint': [1650, 1800, 1950, 3450, 3900, 4350, 4500, 4650],
}
STEP_THR = 0.5 * 10.0 / 110.0   # |z step| needed to round 110 -> 100


def csv_vsl(path):
    """Written VSL rows of an action CSV: {(id, dsd): speed}."""
    out = {}
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if row['kind'] == 'vsl':
                out[(row['id'], row['dsd_no'], row['link'], row['lane'])] = float(row['speed_kph'])
    return out


def freeway_only_times():
    D = RUNS['freeway_only']
    hit = []
    for f in sorted(glob.glob(D + '/action_*.csv')):
        t = int(re.search(r'action_(\d+)\.csv$', f).group(1))
        if t < 900:
            continue
        v = csv_vsl(f)
        if any(abs(s - 110.0) > 1e-9 for s in v.values()):
            hit.append(t)
    times = set()
    for t in hit:
        times.update((t - 150, t))
    return sorted(x for x in times if x >= 900), hit


def r6(x):
    return None if x is None else round(float(x), 6)


def extract(arm, T):
    D = RUNS[arm]
    f = f'{D}/action_{T:06d}.json'
    raw = open(f, 'rb').read()
    o = json.loads(raw)
    md = o.get('metadata', {})
    j = md.get('joint_leader_selection') or {}
    rec = dict(arm=arm, T=T, file=f, sha256=hashlib.sha256(raw).hexdigest(),
               controller_status=md.get('controller_status'))
    rec['vsl_written'] = {k: v for k, v in (o.get('vsl') or {}).items() if '__seg' in k or k in ('FW_E', 'FW_W')}
    rec['vsl_written_non110'] = {k: v for k, v in rec['vsl_written'].items() if abs(v - 110.0) > 1e-9}
    cpath = f'{D}/action_{T:06d}.csv'
    if os.path.exists(cpath):
        cv = csv_vsl(cpath)
        rec['csv_vsl_non110'] = sorted({(k[0], k[1], k[2], k[3], v) for k, v in cv.items() if abs(v - 110.0) > 1e-9})
    if not j:
        rec['no_joint_selection'] = True
        return rec
    axes = j.get('coordinates', [])
    n = len(axes)
    rec['n_axes'] = n
    vix = [i for i, a in enumerate(axes) if a['kind'] == 'vsl']
    rec['vsl_axes'] = [dict(i=i, owner=axes[i]['owner'], key=axes[i]['key'], block=axes[i].get('block'),
                            head=axes[i].get('head'), ref=axes[i].get('reference_value'),
                            allowed=axes[i].get('allowed')) for i in vix]
    # gradient rows: appended n per derivatives() call, in call order
    g = j.get('gradient_rows', [])
    rows = []
    for idx, r in enumerate(g):
        if r.get('kind') != 'vsl':
            continue
        rows.append(dict(call=idx // n if n else None, key=r['key'], owner=r['owner'], block=r.get('block'),
                         anchor_z=r6(r.get('anchor_z')), stencil=[r6(x) for x in (r.get('stencil') or [])] or None,
                         method=r.get('derivative_method'), reason=r.get('fallback_reason'),
                         own=r6(r.get('own')), external=r6(r.get('external')), total=r6(r.get('total')),
                         res=[r6(x) for x in r.get('resource_derivatives_scaled', [])],
                         # secant rows with stencil [lv, 0]: model Omega cost J(lower legal value) - J(anchor), veh.h
                         dJ_lower_minus_anchor=(r6(r['total'] * r['stencil'][0])
                                                if r.get('stencil') and r.get('total') is not None and abs(r['stencil'][1]) < 1e-12 else None)))
    rec['grad_vsl_rows'] = rows
    rec['grad_calls'] = (len(g) // n) if n else None
    # local QP rows for freeway owners
    owner_axes = collections.defaultdict(list)
    for i, a in enumerate(axes):
        owner_axes[a['owner']].append(i)
    lrows = []
    for r in j.get('local_rows', []):
        ow = r.get('owner')
        if ow not in ('FW_E', 'FW_W'):
            continue
        ix = owner_axes[ow]
        for pos, i in enumerate(ix):
            if axes[i]['kind'] != 'vsl':
                continue
            lrows.append(dict(cap=r6(r.get('cap')), iteration=r.get('iteration'), owner=ow, key=axes[i]['key'],
                              block=axes[i].get('block'),
                              own=r6(r['own_gradient'][pos]), ext=r6(r['externality_gradient'][pos]),
                              price=r6(r['price_gradient'][pos]), step=r6(r['step'][pos]),
                              success=r.get('success'),
                              rounds_to_lower=bool(r['step'][pos] <= -STEP_THR + 1e-12)))
    rec['local_vsl_rows'] = lrows
    # PFO warm start
    pfo = j.get('pfo_warm_start') or {}
    prow = []
    for r in pfo.get('local_rows', []):
        ow = r.get('owner')
        if ow not in ('FW_E', 'FW_W'):
            continue
        ix = owner_axes[ow]
        for pos, i in enumerate(ix):
            if axes[i]['kind'] != 'vsl':
                continue
            prow.append(dict(iteration=r.get('iteration'), owner=ow, key=axes[i]['key'], block=axes[i].get('block'),
                             own=r6(r['own_gradient'][pos])))
    rec['pfo'] = dict(status=pfo.get('status'), executed=pfo.get('executed_iterations'), accepted=pfo.get('accepted_iterations'),
                      initial_omega=r6(pfo.get('initial_omega_objective')), selected_omega=r6(pfo.get('selected_omega_objective')),
                      local_row_keys=sorted((pfo.get('local_rows') or [{}])[0].keys()) if pfo.get('local_rows') else [],
                      vsl_rows=prow,
                      trial_rows=[dict(iteration=t.get('iteration'), feasible=t.get('feasible'), owned=r6(t.get('owned_cost')),
                                       omega=r6(t.get('omega_cost'))) for t in pfo.get('trial_rows', [])])
    rec['trial_rows'] = [dict(cap=r6(t.get('cap')), iteration=t.get('iteration'), objective=r6(t.get('objective')),
                              feasible=t.get('feasible'), token=(t.get('action_token') or '')[:12]) for t in j.get('trial_rows', [])]
    rec['candidates'] = [{k: (r6(v) if isinstance(v, float) else v) for k, v in c.items()} for c in j.get('candidates', [])]
    rec['dual_updates'] = [dict(cap=r6(d.get('cap')), nuf=r6(d.get('nuf_target')), it=d.get('iteration'),
                                prices_used=[r6(x) for x in d.get('prices_used', [])],
                                after=[r6(x) for x in d.get('after', [])]) for d in j.get('iteration_dual_updates', [])]
    ps = j.get('price_state') or {}
    rec['prices_scaled'] = ps.get('prices_scaled')
    rec['next_prices_scaled'] = ps.get('next_prices_scaled')
    rec['objective'] = dict(held=r6(j.get('held_objective')), selected=r6(j.get('selected_objective')),
                            warm_start=r6(j.get('warm_start_objective')),
                            prediction_ttt_reduction=r6(j.get('prediction_ttt_reduction')))
    op = j.get('omega_partition') or {}
    rec['omega_costs_selected'] = {k: r6(v) for k, v in (op.get('costs') or {}).items() if k in ('FW_E', 'FW_W', 'PASSIVE_OMEGA')}
    na = j.get('meter_neighbor_audit') or {}
    rec['meter_audit_selected'] = na.get('selected')
    pol = j.get('policy') or {}
    rec['policy'] = {k: pol.get(k) for k in ('proximal', 'fd_vsl_kmh', 'vsl_activation_secant', 'line_search_steps',
                                             'objective_tolerance', 'max_iterations', 'control_blocks', 'fixed_vsl',
                                             'central_multiplier', 'budget_caps', 'dual_step')}
    seq = (o.get('diagnostics') or {}).get('sdmpc_prediction_sequence')
    if isinstance(seq, dict):
        blocks = seq.get('blocks') or seq.get('actions') or []
        vb = []
        for b in blocks if isinstance(blocks, list) else []:
            v = b.get('vsl') if isinstance(b, dict) else None
            if isinstance(v, dict):
                vb.append({k: x for k, x in v.items() if k.startswith('FW_E__seg1') or k in ('FW_E', 'FW_W')})
        rec['sequence_vsl_blocks'] = vb
        rec['sequence_keys'] = sorted(seq.keys())[:20]
    return rec


def main():
    out_path = sys.argv[1]
    t0 = time.time()
    fo_times, fo_hits = freeway_only_times()
    plan = [('a1', t) for t in FIXED['a1']] + [('joint', t) for t in FIXED['joint']] + [('freeway_only', t) for t in fo_times]
    res = dict(schema='vsl_offline_v1/1', step_threshold=STEP_THR, freeway_only_non110_times=fo_hits, plan=plan, decisions=[])
    for arm, T in plan:
        try:
            r = extract(arm, T)
        except Exception as e:  # recorded, not hidden
            r = dict(arm=arm, T=T, error=repr(e))
        res['decisions'].append(r)
        print(arm, T, 'non110', r.get('vsl_written_non110'), 'err', r.get('error'), round(time.time() - t0, 1), flush=True)
    tmp = out_path + '.tmp'
    json.dump(res, open(tmp, 'w', encoding='utf-8'), indent=1)
    os.replace(tmp, out_path)
    print('done', len(res['decisions']), round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
