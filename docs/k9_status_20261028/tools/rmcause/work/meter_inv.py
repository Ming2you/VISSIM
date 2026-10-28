# -*- coding: utf-8 -*-
"""INV_OURS: read-only per-decision, per-meter extraction of the SDMPC meter pipeline.

Reads (read-only) decision files of V-A (K9-2 bundle 1) and J1 (K8) runs:
  decisions_<run>/action_*.joint.json, action_*.json, action_*.csv, signal_readback.csv,
  and the runner log <run>/action_<run>.csv.
Writes only into this script's folder: meter_rows.csv, meter_inv.json.
No VISSIM, no COM, no replay, no rollout.
"""
import csv, ctypes, glob, json, math, os, re, statistics, sys, time
from collections import Counter, defaultdict

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = {
    'VA:v3c3-s31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31',
    'VA:v3c3-s41': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41',
    'VA:v3c3-s43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43',
    'J1:v3c3-s31r': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31',
    'J1:v3c3-s41': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41',
    'J1:v3c3-s43': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43',
}
if len(sys.argv) > 1:
    RUNS = {k: v for k, v in RUNS.items() if any(a in k for a in sys.argv[1:])}
LANES = {'RM_C10482': 2, 'RM_C10681': 2}
TABLE = {'2': 0.71, '3': 0.99, '4': 1.44, '5': 1.89, '6': 2.34, '7': 2.79, '8': 3.24, '9': 3.69, '10': 4.2}
SC = {'RM_C10480': 9101, 'RM_C10482': 9102, 'RM_C10646': 9103, 'RM_C10644': 9104,
      'RM_C10639': 9105, 'RM_C10681': 9106, 'RM_C10490': 9107, 'RM_C10484': 9108}


def service(mid, g):
    return LANES.get(mid, 1) * TABLE[str(g)] * 360.0


def summ(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not xs:
        return None
    s = sorted(xs)
    return {'n': len(s), 'min': s[0], 'median': statistics.median(s), 'max': s[-1],
            'n_pos': sum(x > 1e-12 for x in s), 'n_neg': sum(x < -1e-12 for x in s),
            'n_zero': sum(abs(x) <= 1e-12 for x in s)}


rows_out = []
out = {'schema': 'inv-ours-meter/v1', 'runs': {}}
t0 = time.time()
for label, root in RUNS.items():
    name = os.path.basename(root)
    ddir = os.path.join(root, 'decisions_' + name)
    joints = sorted(glob.glob(os.path.join(ddir, 'action_*.joint.json')))
    actions = sorted(glob.glob(os.path.join(ddir, 'action_[0-9][0-9][0-9][0-9][0-9][0-9].json')))
    run = {'root': root, 'joint_files': len(joints), 'action_files': len(actions)}
    # --- per-decision selected greens (all 61 decisions incl. warm-up) ---
    selected = {}
    policy_seen = Counter()
    for f in actions:
        T = int(re.search(r'action_(\d+)\.json$', f).group(1))
        with open(f, encoding='utf-8-sig') as h:
            a = json.load(h)
        dg = a.get('diagnostics', {})
        g0 = {m: dg.get('rw_meter_green_' + m) for m in SC}
        seq = dg.get('sdmpc_prediction_sequence') or {}
        fut = []
        for blk in seq.get('future', []) or []:
            bd = blk.get('diagnostics', {}) or {}
            fut.append({m: bd.get('rw_meter_green_' + m) for m in SC})
        selected[T] = {'g0': g0, 'future': fut, 'ramp_metering': a.get('ramp_metering'),
                       'N_UF_star': a.get('N_UF_star'), 'controller': (a.get('metadata') or {}).get('controller')}
        del a
    # --- decision CSV written rows ---
    csvrows = {}
    for f in sorted(glob.glob(os.path.join(ddir, 'action_[0-9][0-9][0-9][0-9][0-9][0-9].csv'))):
        T = int(re.search(r'action_(\d+)\.csv$', f).group(1))
        with open(f, encoding='utf-8-sig', newline='') as h:
            for r in csv.DictReader(h):
                if r['kind'] == 'ramp_meter':
                    md = dict(kv.split('=', 1) for kv in r['metadata'].split(';') if '=' in kv)
                    csvrows[(T, r['id'])] = (float(r['rate_vph']), float(r['green_sec']), float(md.get('group_rate_vph', 'nan')))
    # --- runner log rows ---
    runner = Counter()
    runner_rows = 0
    rl = os.path.join(root, 'action_' + name + '.csv')
    with open(rl, encoding='utf-8-sig', newline='') as h:
        for r in csv.DictReader(h):
            if r['kind'] == 'ramp_meter':
                runner_rows += 1
                runner[(r['id'], r['rate_vph'], r['green_sec'], r['readback'])] += 1
    run['runner_meter_rows'] = runner_rows
    run['runner_meter_distinct'] = {'|'.join(k): v for k, v in sorted(runner.items())}
    # --- signal readback for meter SCs ---
    sb = Counter()
    sbf = os.path.join(ddir, 'signal_readback.csv')
    if os.path.isfile(sbf):
        with open(sbf, encoding='utf-8-sig', newline='') as h:
            for r in csv.DictReader(h):
                if r['sc_no'] in {str(v) for v in SC.values()}:
                    sb[(r['sc_no'], r['requested_state'], r['readback_state'], r['ok'], r['stage'])] += 1
    run['signal_readback_meter'] = {'|'.join(k): v for k, v in sorted(sb.items())}
    # --- joint.json decision layer ---
    agg = defaultdict(list)
    meta = Counter()
    nuf_res, np_res, dual_nonzero, raw_nuf, raw_np, prices_nonzero = [], [], 0, [], [], 0
    cand_status = Counter(); pfo_status = Counter()
    max_tighten = {}
    for f in joints:
        T = int(re.search(r'action_(\d+)\.joint\.json$', f).group(1))
        with open(f, encoding='utf-8') as h:
            d = json.load(h)
        sel = d['selection']
        pol = sel['policy']
        meta[('surrogate_reuse', pol.get('surrogate_reuse'))] += 1
        meta[('prediction_model', sel.get('prediction_model'))] += 1
        meta[('algorithm', sel.get('algorithm'))] += 1
        meta[('proximal', pol.get('proximal'))] += 1
        meta[('line_search_steps', pol.get('line_search_steps'))] += 1
        meta[('max_iterations', pol.get('max_iterations'))] += 1
        meta[('pfo_max_iterations', (pol.get('pfo_cap_options') or {}).get('max_iterations'))] += 1
        meta[('nuf_cap_margin', (pol.get('pfo_cap_options') or {}).get('nuf_cap_margin_veh_h'))] += 1
        prox = float(pol['proximal'])
        coords = sel['coordinates']
        owner_ix = defaultdict(list)
        for j, c in enumerate(coords):
            owner_ix[c['owner']].append(j)
        mcoords = {j: c for j, c in enumerate(coords) if c['kind'] == 'meter'}
        for j, c in mcoords.items():
            meta[('allowed', c['block'], tuple(c['allowed']), c['reference_value'])] += 1
        # PFO own-cost gradients
        pfo = sel.get('pfo_warm_start') or {}
        pfo_status[pfo.get('status')] += 1
        pfo_g = defaultdict(list)
        for lr in pfo.get('local_rows', []):
            if lr['owner'] not in ('FW_E', 'FW_W'):
                continue
            ix = owner_ix[lr['owner']]
            for k, j in enumerate(ix):
                if j in mcoords:
                    pfo_g[(mcoords[j]['key'], mcoords[j]['block'])].append(lr['own_gradient'][k])
        # central local rows
        cen = defaultdict(list)
        for lr in sel.get('local_rows', []):
            if lr['owner'] not in ('FW_E', 'FW_W'):
                continue
            ix = owner_ix[lr['owner']]
            for k, j in enumerate(ix):
                if j in mcoords:
                    own, ext, pr, st = (lr['own_gradient'][k], lr['externality_gradient'][k],
                                        lr['price_gradient'][k], lr['step'][k])
                    if pr != 0:
                        prices_nonzero += 1
                    cen[(mcoords[j]['key'], mcoords[j]['block'])].append((own, ext, pr, st, lr['iteration']))
        # derivative rows (AD)
        dmeth = Counter(); res_der = defaultdict(list)
        for g in sel.get('gradient_rows', []):
            if g['kind'] == 'meter':
                dmeth[g.get('derivative_method')] += 1
                res_der[(g['key'], g['block'])].append(g.get('resource_derivatives_scaled'))
        for k, v in dmeth.items():
            meta[('derivative_method', k)] += v
        # duals / resource residuals
        anyd = False
        for u in sel.get('iteration_dual_updates', []):
            rr = u.get('raw_residual_scaled') or [None, None]
            raw_np.append(rr[0] * 100.0 if rr[0] is not None else None)
            raw_nuf.append(rr[1] * 1000.0 if rr[1] is not None else None)
            if any(abs(x) > 0 for x in (u.get('after') or []) + (u.get('prices_used') or [])):
                anyd = True
        dual_nonzero += anyd
        for c in sel.get('candidates', []):
            cand_status[c.get('status')] += 1
        fc = sel.get('final_constraints') or {}
        nuf_res.append((fc.get('nuf') or {}).get('residual'))
        np_res.append((fc.get('np') or {}).get('residual'))
        bi = sel.get('budget_initialization') or {}
        acc = bi.get('accepted_rate_veh_h_by_ramp') or {}
        fin = ((fc.get('physical_ramp_merge') or {}).get('rate_veh_h_by_ramp')) or {}
        owner_of = {c['key']: c['owner'] for c in mcoords.values()}
        sel_rec = selected.get(T, {})
        for mid in SC:
            b0 = cen.get((mid, 0), [])
            pf0 = pfo_g.get((mid, 0), [])
            eff = [o + e + p for o, e, p, s, it in b0]
            steps0 = [s for o, e, p, s, it in b0]
            steps_all = [s for b in (0, 1, 2) for (o, e, p, s, it) in cen.get((mid, b), [])]
            pfo_all = [x for b in (0, 1, 2) for x in pfo_g.get((mid, b), [])]
            eff_all = [o + e + p for b in (0, 1, 2) for (o, e, p, s, it) in cen.get((mid, b), [])]
            fut = sel_rec.get('future', [])
            w = csvrows.get((T, mid), (None, None, None))
            row = {'run': label, 'T': T, 'meter': mid, 'owner': owner_of.get(mid), 'sc': SC[mid],
                   'ref_green_b0': next((c['reference_value'] for c in mcoords.values() if c['key'] == mid and c['block'] == 0), None),
                   'allowed_b0': ' '.join(str(x) for x in next((c['allowed'] for c in mcoords.values() if c['key'] == mid and c['block'] == 0), [])),
                   'pfo_own_g_b0_it0': pf0[0] if pf0 else None,
                   'pfo_own_g_b0_max': max(pf0) if pf0 else None,
                   'pfo_own_g_any_block_max': max(pfo_all) if pfo_all else None,
                   'cen_own_b0_it0': b0[0][0] if b0 else None,
                   'cen_ext_b0_it0': b0[0][1] if b0 else None,
                   'cen_price_b0_it0': b0[0][2] if b0 else None,
                   'cen_eff_b0_max': max(eff) if eff else None,
                   'cen_eff_b0_min': min(eff) if eff else None,
                   'cen_eff_any_block_max': max(eff_all) if eff_all else None,
                   'cen_step_b0_min': min(steps0) if steps0 else None,
                   'cen_step_b0_max': max(steps0) if steps0 else None,
                   'cen_step_any_absmax': max((abs(x) for x in steps_all), default=None),
                   'pred_merge_T_T450': acc.get(mid), 'pred_merge_final': fin.get(mid),
                   'svc_g10': service(mid, 10), 'svc_g9': service(mid, 9), 'svc_g8': service(mid, 8),
                   'sel_green_b0': (sel_rec.get('g0') or {}).get(mid),
                   'sel_green_b1': fut[0].get(mid) if len(fut) > 0 else None,
                   'sel_green_b2': fut[1].get(mid) if len(fut) > 1 else None,
                   'json_ramp_metering': (sel_rec.get('ramp_metering') or {}).get(mid),
                   'csv_rate_vph': w[0], 'csv_green_sec': w[1], 'csv_group_rate_vph': w[2]}
            rows_out.append(row)
            agg[(mid, 'pfo_own_b0')].extend(pf0)
            agg[(mid, 'pfo_own_all')].extend(pfo_all)
            agg[(mid, 'cen_eff_b0')].extend(eff)
            agg[(mid, 'cen_eff_all')].extend(eff_all)
            agg[(mid, 'cen_step_all')].extend(steps_all)
            agg[(mid, 'pred_merge')].append(acc.get(mid))
            for b in (0, 1, 2):
                for x in res_der.get((mid, b), []):
                    if x:
                        agg[(mid, 'dNUF_scaled_b%d' % b)].append(x[1])
                        agg[(mid, 'dNP_scaled_b%d' % b)].append(x[0])
        del d
    # decisions without joint (warm-up) still have selected greens / csv
    run['meta'] = {'|'.join(str(x) for x in k): v for k, v in sorted(meta.items(), key=lambda kv: str(kv[0]))}
    run['pfo_status'] = dict(pfo_status)
    run['central_candidate_status'] = dict(cand_status)
    run['final_nuf_residual'] = summ(nuf_res)
    run['final_np_residual'] = summ(np_res)
    run['raw_nuf_residual_veh_h_each_iteration'] = summ(raw_nuf)
    run['raw_np_residual_veh_each_iteration'] = summ(raw_np)
    run['decisions_with_nonzero_dual'] = dual_nonzero
    run['meter_price_gradient_nonzero_entries'] = prices_nonzero
    run['per_meter'] = {}
    for mid in SC:
        pm = {k[1]: summ(v) for k, v in agg.items() if k[0] == mid}
        pm['tighten_threshold_g'] = 0.5
        pm['n_pfo_own_gt_0.5'] = sum(x > 0.5 for x in agg[(mid, 'pfo_own_all')])
        pm['n_cen_eff_gt_0.5'] = sum(x > 0.5 for x in agg[(mid, 'cen_eff_all')])
        pm['n_step_le_-0.05'] = sum(x <= -0.05 for x in agg[(mid, 'cen_step_all')])
        pm['n_step_ge_+0.05'] = sum(x >= 0.05 for x in agg[(mid, 'cen_step_all')])
        pm['n_pred_merge_gt_svc_g9'] = sum((x or 0) > service(mid, 9) for x in agg[(mid, 'pred_merge')])
        pm['n_pred_merge_gt_svc_g8'] = sum((x or 0) > service(mid, 8) for x in agg[(mid, 'pred_merge')])
        sel_b = Counter()
        for T, s in selected.items():
            sel_b[('b0', (s.get('g0') or {}).get(mid))] += 1
            for i, fb in enumerate(s.get('future', [])):
                sel_b[('b%d' % (i + 1), fb.get(mid))] += 1
        pm['selected_green_counts'] = {'%s=%s' % k: v for k, v in sorted(sel_b.items(), key=str)}
        wr = Counter((v[0], v[1], v[2]) for (T, m), v in csvrows.items() if m == mid)
        pm['written_csv_counts'] = {'rate=%s|green=%s|group=%s' % k: v for k, v in wr.items()}
        run['per_meter'][mid] = pm
    out['runs'][label] = run
    print(label, len(joints), 'joint', len(actions), 'actions', round(time.time() - t0, 1), 's', flush=True)

out['elapsed_sec'] = time.time() - t0
tag = re.sub(r'[^A-Za-z0-9_-]', '-', '_'.join(sys.argv[1:])) if len(sys.argv) > 1 else 'all'
with open(os.path.join(HERE, 'meter_inv_%s.json' % tag), 'w', encoding='utf-8') as h:
    json.dump(out, h, ensure_ascii=False, indent=1, default=str)
with open(os.path.join(HERE, 'meter_rows_%s.csv' % tag), 'w', encoding='utf-8', newline='') as h:
    w = csv.DictWriter(h, fieldnames=list(rows_out[0].keys()))
    w.writeheader(); w.writerows(rows_out)
print('wrote', tag, round(time.time() - t0, 1))
