# VERIFY_NEXT: extract model ramp-merge prediction from SDMPC decision JSONs (read-only).
# Usage: python -B vn_model_extract.py <out.json> <tag>=<action_json> [...]
import sys, json, hashlib

RAMPS = ['RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
out = sys.argv[1]
res = {}
for arg in sys.argv[2:]:
    tag, path = arg.split('=', 1)
    raw = open(path, 'rb').read()
    d = json.loads(raw)
    js = d['metadata']['joint_leader_selection']
    fc = js['final_constraints']['physical_ramp_merge']
    final_rate = fc['rate_veh_h_by_ramp']
    best = None
    for i, td in enumerate(js['tangent_derivatives']):
        r = td['surrogate_prediction']['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']
        gap = abs(r['RM_C10681'] - final_rate['RM_C10681'])
        if best is None or gap < best[0]:
            best = (gap, i, td)
    gap, idx, td = best
    cp = td['surrogate_prediction']['central_physical']
    stocks = {}
    for n, v in zip(cp['names'], cp['values']):
        parts = n.split('/')
        if len(parts) >= 5 and parts[2] == 'ramp_queue' and parts[3] in RAMPS:
            stocks.setdefault(parts[3], {})[parts[1] + '/' + parts[4] + '/' + parts[5]] = v
    seen = set(); grads = {}
    for r in js['gradient_rows']:
        if r['kind'] != 'meter':
            continue
        key = (r['key'], r['block'])
        if key in seen:      # keep the first occurrence (first gradient pass)
            continue
        seen.add(key)
        grads[f"{r['key']}|b{r['block']}"] = {'own': r['own'], 'external': r['external'], 'total': r['total'],
                                              'res_scaled': r['resource_derivatives_scaled']}
    res[tag] = {
        'path': path, 'sha256': hashlib.sha256(raw).hexdigest(),
        'start_sec': fc['start_sec'], 'end_sec': fc['end_sec'],
        'final_rate_veh_h': {k: final_rate[k] for k in RAMPS},
        'final_veh': {k: fc['accepted_vehicles_by_ramp'][k] for k in RAMPS},
        'budget_init_rate': {k: js['budget_initialization']['accepted_rate_veh_h_by_ramp'].get(k) for k in RAMPS},
        'tangent_idx': idx, 'tangent_gap_10681_veh_h': gap,
        'model_ramp_stock_lower': stocks,
        'meter_grad_first_pass': grads,
        'meter_green_cmd': {k: d['ramp_metering'][k] for k in RAMPS},
        'n_gradient_rows': len(js['gradient_rows']),
    }
    print('OK', tag, fc['start_sec'], final_rate['RM_C10681'])
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
