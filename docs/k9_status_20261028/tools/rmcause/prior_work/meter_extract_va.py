# -*- coding: utf-8 -*-
"""Lens METER: read-only extraction of SDMPC meter decision variables from V-A joint.json files (copy of j1/causes/meter_work/meter_extract.py, ROOT/RUNS/OUT changed only).

Reads only D:/VISSIM_runs/20261004_sdmpc31_k8/<run>/decisions_<run>/action_*.joint.json (read-only).
Writes only meter_extract.json next to this script.
"""
import ctypes, glob, json, math, os, re, statistics, sys, time
from collections import Counter, defaultdict

try:  # BELOW_NORMAL priority
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

ROOT = 'D:/VISSIM_runs/20261023_sdmpc31_k92'
RUNS = {'v3c3-s31': 'sdmpc31_v3c3_k92va_s31', 'v3c3-s41': 'sdmpc31_v3c3_k92va_s41', 'v3c3-s43': 'sdmpc31_v3c3_k92va_s43'}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meter_extract_va.json')
LANES = {'RM_C10482': 2, 'RM_C10681': 2}
TABLE = {'2': 0.71, '3': 0.99, '4': 1.44, '5': 1.89, '6': 2.34, '7': 2.79, '8': 3.24, '9': 3.69, '10': 4.2}


def service(mid, g):
    return LANES.get(mid, 1) * TABLE[str(g)] * 360.0 if g else 0.0


def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    s = sorted(xs)
    return {'n': len(s), 'min': s[0], 'median': statistics.median(s), 'max': s[-1],
            'n_pos_gt_1e-9': sum(x > 1e-9 for x in s), 'n_neg_lt_-1e-9': sum(x < -1e-9 for x in s),
            'n_abs_le_1e-9': sum(abs(x) <= 1e-9 for x in s)}


t0 = time.time()
out = {'schema': 'lens-meter-extract/v1', 'runs': {}}
for label, name in RUNS.items():
    files = sorted(glob.glob(os.path.join(ROOT, name, 'decisions_' + name, 'action_*.joint.json')))
    run = {'files': len(files), 'decisions': []}
    agg = defaultdict(list)          # (mid, block) -> list of total gradient (axis rows)
    agg_eff = defaultdict(list)      # (mid) -> own+external+price at block0 from local rows
    green_abs = []                   # |total| of block-0 signal green axes (comparison)
    allowed_sets = Counter()
    ref_values = Counter()
    proximal_vals, fd_vals, algo, prediction_model = Counter(), Counter(), Counter(), Counter()
    step_nonzero = 0
    step_ge_005 = 0
    step_rows = 0
    max_abs_meter_step = 0.0
    max_pos_eff = (-math.inf, None)
    accepted = defaultdict(list)
    accepted_final = defaultdict(list)
    exceed8 = Counter(); exceed4 = Counter(); exceed6 = Counter()
    prices_nonzero = 0
    for f in files:
        T = int(re.search(r'action_(\d+)\.joint\.json$', f).group(1))
        with open(f, encoding='utf-8') as h:
            d = json.load(h)
        sel = d['selection']
        algo[sel.get('algorithm')] += 1
        prediction_model[sel.get('prediction_model')] += 1
        pol = sel.get('policy', {})
        proximal_vals[pol.get('proximal')] += 1
        fd_vals[pol.get('fd_meter_green_sec')] += 1
        coords = sel['coordinates']
        for c in coords:
            if c['kind'] == 'meter':
                allowed_sets[(c['block'], tuple(c['allowed']))] += 1
                ref_values[c['reference_value']] += 1
        owner_ix = defaultdict(list)
        for j, c in enumerate(coords):
            owner_ix[c['owner']].append(j)
        for g in sel['gradient_rows']:
            if g['kind'] == 'meter':
                agg[(g['key'], g['block'])].append(g['total'])
            elif g['kind'] == 'green' and g.get('block') == 0:
                green_abs.append(abs(g['total']))
        for lr in sel['local_rows']:
            if lr['owner'] not in ('FW_E', 'FW_W'):
                continue
            ix = owner_ix[lr['owner']]
            if len(ix) != len(lr['step']):
                raise SystemExit('axis length mismatch %s %s' % (f, lr['owner']))
            step_rows += 1
            for k, j in enumerate(ix):
                c = coords[j]
                if c['kind'] != 'meter':
                    continue
                eff = lr['own_gradient'][k] + lr['externality_gradient'][k] + lr['price_gradient'][k]
                if lr['price_gradient'][k] != 0:
                    prices_nonzero += 1
                if c['block'] == 0:
                    agg_eff[c['key']].append(eff)
                    if eff > max_pos_eff[0]:
                        max_pos_eff = (eff, {'T': T, 'meter': c['key'], 'iteration': lr['iteration']})
                st = lr['step'][k]
                max_abs_meter_step = max(max_abs_meter_step, abs(st))
                if abs(st) > 1e-12:
                    step_nonzero += 1
                if abs(st) >= 0.05 - 1e-12:
                    step_ge_005 += 1
        bi = sel.get('budget_initialization', {}) or {}
        acc = bi.get('accepted_rate_veh_h_by_ramp', {}) or {}
        for mid, v in acc.items():
            accepted[mid].append(v)
            if v > service(mid, 8): exceed8[mid] += 1
            if v > service(mid, 6): exceed6[mid] += 1
            if v > service(mid, 4): exceed4[mid] += 1
        fc = (sel.get('final_constraints') or {}).get('physical_ramp_merge', {}) or {}
        for mid, v in (fc.get('rate_veh_h_by_ramp') or {}).items():
            accepted_final[mid].append(v)
        run['decisions'].append({'T': T, 'selected_objective': sel.get('selected_objective'),
                                 'held_objective': sel.get('held_objective'),
                                 'n_trials': len(sel.get('trial_rows', [])),
                                 'candidates': len(sel.get('candidates', []))})
        del d
    run['algorithm'] = dict(algo)
    run['prediction_model'] = dict(prediction_model)
    run['proximal'] = {str(k): v for k, v in proximal_vals.items()}
    run['fd_meter_green_sec'] = {str(k): v for k, v in fd_vals.items()}
    run['meter_allowed_sets'] = {'block%d:%s' % (b, list(a)): n for (b, a), n in sorted(allowed_sets.items())}
    run['meter_reference_values'] = {str(k): v for k, v in ref_values.items()}
    run['meter_total_gradient_by_block'] = {'%s|b%d' % k: summ(v) for k, v in sorted(agg.items())}
    run['meter_effective_gradient_block0_localrows'] = {k: summ(v) for k, v in sorted(agg_eff.items())}
    run['meter_effective_gradient_block0_all'] = summ([x for v in agg_eff.values() for x in v])
    run['max_positive_effective_gradient_block0'] = {'value': max_pos_eff[0], 'where': max_pos_eff[1]}
    run['signal_green_block0_abs_total_gradient'] = summ(green_abs)
    run['fw_local_rows'] = step_rows
    run['meter_steps_nonzero'] = step_nonzero
    run['meter_steps_ge_0.05'] = step_ge_005
    run['max_abs_meter_step'] = max_abs_meter_step
    run['meter_price_gradient_nonzero_entries'] = prices_nonzero
    run['accepted_rate_window_T_T450'] = {k: summ(v) for k, v in sorted(accepted.items())}
    run['accepted_rate_final_selected'] = {k: summ(v) for k, v in sorted(accepted_final.items())}
    run['service_ceiling_veh_h'] = {mid: {g: service(mid, int(g)) for g in ('4', '6', '8', '9', '10')}
                                    for mid in sorted(accepted)}
    run['decisions_accepted_gt_service_g8'] = dict(exceed8)
    run['decisions_accepted_gt_service_g6'] = dict(exceed6)
    run['decisions_accepted_gt_service_g4'] = dict(exceed4)
    out['runs'][label] = run
    print(label, len(files), 'files', round(time.time() - t0, 1), 's', flush=True)
out['elapsed_sec'] = time.time() - t0
with open(OUT, 'w', encoding='utf-8') as h:
    json.dump(out, h, ensure_ascii=False, indent=1)
print('wrote', OUT)
