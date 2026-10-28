# vhr_vsl.py - fresh audit of the joint decision JSONs (VSL gradients/steps, ramp forecast, meter audit, wall times).
import csv, glob, json, os, re, statistics
from collections import Counter

D = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
RL = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/runlog_sdmpc31_sdmpc8100_s29.txt'
OUT = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/vsl_out.json'
HALF = 0.5 * 10.0 / 110.0  # half a 10 km/h step in scaled units
res = {'per_decision': {}}
g_all = []; methods = Counter(); reasons = Counter(); stencils = Counter(); grad_rows_new = 0
for p in sorted(glob.glob(f'{D}/action_??????.json')):
    t = int(re.search(r'action_(\d{6})\.json$', p).group(1))
    d = json.load(open(p, encoding='utf-8'))
    md = d.get('metadata', {}); j = md.get('joint_leader_selection')
    vsl_out = sorted(set(v for k, v in (d.get('vsl') or {}).items()))
    rec = {'vsl_values': vsl_out, 'has_joint': j is not None,
           'forecast_total': md.get('forecast_ramp_arrival_total_vph'),
           'forecast_R': {k: md[k] for k in md if k.startswith('forecast_ramp_arrival_R_')}}
    if j is not None:
        axes = j['coordinates']
        gv = [r for r in j['gradient_rows'] if r.get('kind') == 'vsl']
        rec['vsl_grad_rows'] = len(gv)
        tot = [r['total'] for r in gv]
        rec['vsl_total_max'] = max(tot) if tot else None; rec['vsl_total_min'] = min(tot) if tot else None
        rec['n_ge_thr'] = sum(x >= HALF * 10.0 for x in tot)  # proximal 10: step -g/10 reaches -HALF when g >= 0.4545
        if 900 <= t <= 7950:
            grad_rows_new += len(gv); g_all += tot
            for r in gv:
                methods[r.get('derivative_method')] += 1; reasons[r.get('fallback_reason')] += 1
                stencils[str([round(x, 4) for x in (r.get('stencil') or [])])] += 1
        # local steps on VSL axes: g_eff = own + externality + price ; step
        vmax_step = 0.0; vmax_geff = None; vrow = None
        for lr in j['local_rows']:
            ix = [k for k, a in enumerate(axes) if a['owner'] == lr['owner']]
            for pos, k in enumerate(ix):
                if axes[k]['kind'] != 'vsl':
                    continue
                st = lr['step'][pos]; ge = lr['own_gradient'][pos] + lr['externality_gradient'][pos] + lr['price_gradient'][pos]
                if abs(st) > abs(vmax_step):
                    vmax_step = st; vrow = dict(cap=lr['cap'], iteration=lr['iteration'], owner=lr['owner'], key=axes[k]['key'], block=axes[k].get('block'),
                                                own=lr['own_gradient'][pos], ext=lr['externality_gradient'][pos], price=lr['price_gradient'][pos], step=st)
                if vmax_geff is None or ge > vmax_geff:
                    vmax_geff = ge
        rec['vsl_local_max_abs_step'] = vmax_step; rec['vsl_local_max_step_row'] = vrow; rec['vsl_local_max_geff'] = vmax_geff
        rec['trial_row_keys'] = sorted(j['trial_rows'][0].keys()) if j['trial_rows'] else []
        rec['selection_status'] = j.get('selection_status'); rec['converged'] = j.get('converged')
        rec['cand_status'] = [c.get('status') for c in j.get('candidates', [])]
        rec['prediction_ttt_reduction'] = j.get('prediction_ttt_reduction')
        rec['audit_performed'] = j.get('finite_neighbor_audit_performed')
        mna = j.get('meter_neighbor_audit') or {}
        rec['audit_selected'] = mna.get('selected'); rec['audit_n_candidates'] = len(mna.get('candidates') or [])
        sel = [c for c in (mna.get('candidates') or []) if c.get('name') == mna.get('selected') or c.get('label') == mna.get('selected') or c.get('id') == mna.get('selected')]
        rec['audit_selected_delta'] = [c.get('delta_veh_h') for c in sel]
        rec['audit_candidate_keys'] = sorted((mna.get('candidates') or [{}])[0].keys())
    res['per_decision'][t] = rec
    del d
new = [t for t in res['per_decision'] if 900 <= t <= 7950 and res['per_decision'][t]['has_joint']]
res['new_decisions'] = len(new)
res['vsl_rows_new'] = grad_rows_new
res['methods'] = dict(methods); res['reasons'] = dict(reasons); res['stencils'] = dict(stencils)
res['sign'] = dict(neg=sum(x < 0 for x in g_all), zero=sum(x == 0 for x in g_all), pos=sum(x > 0 for x in g_all),
                   pos_gt_1e9=sum(x > 1e-9 for x in g_all), max=max(g_all), min=min(g_all),
                   ge_0p4545=sum(x >= HALF * 10.0 for x in g_all), top5=sorted(g_all)[-6:])
res['vsl_outputs_all_110'] = all(r['vsl_values'] == [110.0] for r in res['per_decision'].values() if r['vsl_values'])
big = {t: r['vsl_local_max_abs_step'] for t, r in res['per_decision'].items() if r.get('vsl_local_max_abs_step') is not None and abs(r['vsl_local_max_abs_step']) >= HALF}
res['decisions_with_vsl_local_step_ge_half'] = big
res['vsl_local_step_abs_by_t'] = {t: round(r['vsl_local_max_abs_step'], 5) for t, r in res['per_decision'].items() if r.get('vsl_local_max_abs_step') is not None}
fc = {t: r['forecast_total'] for t, r in res['per_decision'].items() if t in new}
res['forecast_all_mult30'] = all(v is not None and abs(v / 30 - round(v / 30)) < 1e-9 for v in fc.values())
res['forecast_R_all_zero'] = all(all(x == 0 for x in r['forecast_R'].values()) for t, r in res['per_decision'].items() if t in new)
res['forecast_examples'] = {t: fc[t] for t in (900, 2250, 7950) if t in fc}
res['audit_performed_count'] = sum(1 for t in new if res['per_decision'][t]['audit_performed'])
res['audit_selected_counter'] = dict(Counter(res['per_decision'][t]['audit_selected'] for t in new))
res['selection_status'] = dict(Counter(res['per_decision'][t]['selection_status'] for t in new))
res['converged_true'] = sum(1 for t in new if res['per_decision'][t]['converged'])
pr = [res['per_decision'][t]['prediction_ttt_reduction'] for t in new]
res['pred_red'] = dict(mean=statistics.mean(pr), median=statistics.median(pr), min=min(pr), max=max(pr))
res['cand_status'] = dict(Counter(s for t in new for s in res['per_decision'][t]['cand_status']))
# wall times from runlog
w = {}
hold = []
for line in open(RL, encoding='utf-8', errors='replace'):
    m = re.match(r'CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([\d.]+) result=exit=(-?\d+)', line)
    if m:
        w[int(m.group(1))] = (float(m.group(2)), int(m.group(3)))
    if 'DECISION_HELD_PREVIOUS' in line or 'DECISION_FAILED' in line:
        hold.append(line.strip()[:200])
nw = [w[t][0] for t in w if 900 <= t <= 7950 and w[t][1] == 0]
res['wall'] = dict(n=len(nw), mean=statistics.mean(nw), median=statistics.median(nw), max=max(nw),
                   argmax=[t for t in w if w[t][0] == max(nw)], gt360=sum(x > 360 for x in nw), gt1800=sum(x > 1800 for x in nw),
                   sum=sum(nw), all49_sum=sum(w[t][0] for t in w if 900 <= t <= 8100), all49_n=sum(1 for t in w if 900 <= t <= 8100),
                   pre900_sum=sum(w[t][0] for t in w if t < 900), t6900=w.get(6900), t8100=w.get(8100))
res['hold_lines'] = hold[:10]
json.dump(res, open(OUT, 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k not in ('per_decision', 'vsl_local_step_abs_by_t')}, indent=0, default=str)[:6000])
