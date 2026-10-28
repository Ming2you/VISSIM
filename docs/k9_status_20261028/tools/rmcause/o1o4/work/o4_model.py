# -*- coding: utf-8 -*-
"""O4 (2026-10-24 rmcause): read-only extraction of the SDMPC model's predicted on-ramp merge per decision.

Usage: python -B o4_model.py <tag> <run_root> <out_dir>

Per joint decision T (sdmpc-runtime-decision/v1), for RM_C10639 / RM_C10681 / RM_C10490 / RM_C10484:
- predicted merge over the recorded window (final_constraints.physical_ramp_merge, selected plan) and the PFO
  budget initialization rate (budget_initialization.accepted_rate_veh_h_by_ramp)
- model ramp stock at the block ends (tangent_derivatives[k].surrogate_prediction.central_physical
  'physical/<t>/ramp_queue/<ramp>/0/lower' = -stock) for the derivative record whose predicted merge equals the final one
- initial connector stock at T from the lane observation frame (the plant's initial cohorts, lane_plant_runtime.py:486-488)
- obs150 derived window counts at T (ramp_arrival and meter_head crossings, VISSIM [T-150, T])
- meter-axis derivatives: gradient_rows iteration 0 (dNUF/dz = resource_derivatives_scaled[1]*1000, own/external/total)
  and the per-cost-component column of the matched tangent record's cost_jacobian
Reads only. Writes <out_dir>/model_<tag>.json and .csv.
"""
import csv, glob, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

RAMPS = {'RM_C10639': 10639, 'RM_C10681': 10681, 'RM_C10490': 10490, 'RM_C10484': 10484}
HEAD = {10639: 314.83469380887993, 10681: 290.72003141146473, 10490: 272.60355928160652, 10484: 377.11076285480539}
MH = {'RM_C10639': ['90030897'], 'RM_C10681': ['90030898', '90030899'], 'RM_C10490': ['90030900'],
      'RM_C10484': ['90030901']}


def load_any(p):
    raw = open(p, 'rb').read()
    for enc in ('utf-8-sig', 'utf-16'):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            pass
    raise ValueError('undecodable ' + p)


def dig(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def main():
    below_normal()
    tag, root, out_dir = sys.argv[1], sys.argv[2].rstrip('/\\'), sys.argv[3]
    name = os.path.basename(root)
    ddir = os.path.join(root, 'decisions_' + name)
    t0 = time.time()
    rows, recs = [], []
    files = sorted(glob.glob(os.path.join(ddir, 'action_*.joint.json')))
    only = os.environ.get('O4_ONLY_T')
    if only:
        files = [f for f in files if f.endswith('action_%06d.joint.json' % int(only))]
    for jp in files:
        T = int(re.search(r'action_(\d+)\.joint\.json$', jp).group(1))
        d = json.load(open(jp, encoding='utf-8-sig'))
        sel = d['selection']
        prm = sel['final_constraints']['physical_ramp_merge']
        bi = sel.get('budget_initialization') or {}
        win = (prm['start_sec'], prm['end_sec'])
        tds = sel.get('tangent_derivatives') or []
        match = None
        for i, td in enumerate(tds):
            sp = dig(td, 'surrogate_prediction', 'quantities', 'predicted_ramp_merge', 'accepted_vehicles_by_ramp') or {}
            if sp and all(abs(sp.get(r, -1e9) - prm['accepted_vehicles_by_ramp'][r]) < 1e-9 for r in RAMPS):
                match = i
        queues, queues_anchor = {}, {}
        def q_from(td):
            out = {}
            cp = dig(td, 'surrogate_prediction', 'central_physical') or {}
            for n, v in zip(cp.get('names', []), cp.get('values', [])):
                m = re.match(r'physical/(\d+(?:\.\d+)?)/ramp_queue/(RM_C\d+)/0/lower$', n)
                if m and m.group(2) in RAMPS:
                    out.setdefault(m.group(2), {})[str(int(float(m.group(1))))] = -v
            return out
        if match is not None:
            queues = q_from(tds[match])
        if tds:
            queues_anchor = q_from(tds[0])
        co = sel['coordinates']
        n = len(co)
        gr = sel.get('gradient_rows') or []
        it0 = gr[:n] if len(gr) >= n else []
        cost_names = list((sel.get('omega_partition') or {}).get('costs', {}).keys())
        cj = tds[match]['cost_jacobian'] if match is not None else None
        cj0 = tds[0]['cost_jacobian'] if tds else None
        rj0 = tds[0]['resource_jacobian'] if tds else None
        grad = {}
        for j, c in enumerate(co):
            if c['kind'] != 'meter' or c['key'] not in RAMPS:
                continue
            g = {}
            if it0:
                r = it0[j]
                assert r['key'] == c['key'] and r['block'] == c['block']
                g.update(dNUF_dz_veh_h=r['resource_derivatives_scaled'][1] * 1000.0,
                         dNP_dz_scaled=r['resource_derivatives_scaled'][0],
                         own=r.get('own'), external=r.get('external'), total=r.get('total'),
                         method=r.get('derivative_method'), anchor_z=r.get('anchor_z'))
            if cj0 is not None and len(cj0) == len(cost_names):
                comp = {cost_names[k]: cj0[k][j] for k in range(len(cost_names))}
                g['cost_components_anchor'] = {k: v for k, v in comp.items() if abs(v) > 1e-12}
                g['cost_sum_anchor'] = sum(comp.values())
            if rj0 is not None:
                g['resource_jacobian_anchor'] = [rj0[0][j], rj0[1][j]]
            grad.setdefault(c['key'], {})[str(c['block'])] = g
        far = dig(d, 'physical_response_cache', 'warm_budget_binding', 'source_action', 'diagnostics',
                  '_control_area_written_meter_context', 'raw', 'local_observation', 'far_measurement',
                  'link_volume_veh_h') or {}
        # initial connector stock from the lane observation frame at T
        init = {}
        fp = os.path.join(ddir, 'lane_observations', 'frame_%06d.json' % T)
        if os.path.isfile(fp):
            fr = load_any(fp)
            for r, cno in RAMPS.items():
                vs = [v for v in fr['vehicles'] if int(v[1]) == cno]
                init[r] = {'total': len(vs), 'prehead': sum(1 for v in vs if v[3] < HEAD[cno]),
                           'posthead': sum(1 for v in vs if v[3] >= HEAD[cno]),
                           'slow15': sum(1 for v in vs if v[4] < 15.0),
                           'by_lane': {str(l): sum(1 for v in vs if int(v[2]) == l) for l in (1, 2)}}
        obs = {}
        dp = os.path.join(ddir, 'obs150', 'derived_%06d.json' % T)
        if os.path.isfile(dp):
            dv = load_any(dp)
            b = dv.get('boundaries', {})
            for r in RAMPS:
                obs[r] = {'ramp_arrival_cross': dig(b, 'ramp_arrival:' + r, 'cross'),
                          'meter_head_cross': sum((dig(b, 'meter_head:' + h, 'cross') or 0) for h in MH[r]),
                          'arrival_shares': (dv.get('ramp_arrival_shares') or {}).get(r),
                          'window': dv.get('window')}
        rec = {'T': T, 'window': win, 'match_td': match, 'n_td': len(tds),
               'pred_veh': {r: prm['accepted_vehicles_by_ramp'][r] for r in RAMPS},
               'pred_rate': {r: prm['rate_veh_h_by_ramp'][r] for r in RAMPS},
               'pfo_rate': {r: (bi.get('accepted_rate_veh_h_by_ramp') or {}).get(r) for r in RAMPS},
               'pfo_window': (bi.get('start_sec'), bi.get('end_sec')),
               'queues_selected': queues, 'queues_anchor': queues_anchor, 'grad': grad,
               'far_link_volume_veh_h': {str(c): far.get(str(c)) for c in RAMPS.values()},
               'init': init, 'obs150': obs, 'cost_names': cost_names}
        recs.append(rec)
        for r, cno in RAMPS.items():
            q = queues.get(r, {})
            ends = sorted(q, key=float)
            qend = q[ends[-1]] if ends else None
            i0 = (init.get(r) or {}).get('total')
            dur = win[1] - win[0]
            arr = (prm['accepted_vehicles_by_ramp'][r] + qend - i0) if (qend is not None and i0 is not None) else None
            g0 = (grad.get(r) or {}).get('0', {})
            rows.append({'run': tag, 'T': T, 'ramp': r, 'win_start': win[0], 'win_end': win[1],
                         'pred_veh': prm['accepted_vehicles_by_ramp'][r], 'pred_rate': prm['rate_veh_h_by_ramp'][r],
                         'pfo_rate': rec['pfo_rate'][r], 'init_stock': i0,
                         'init_posthead': (init.get(r) or {}).get('posthead'),
                         'q_b0': q.get(ends[0]) if ends else None, 'q_b1': q.get(ends[1]) if len(ends) > 1 else None,
                         'q_b2': qend, 'implied_arrival_veh': arr,
                         'implied_arrival_rate': arr * 3600.0 / dur if arr is not None else None,
                         'obs_arrival_prev150_rate': ((obs.get(r) or {}).get('ramp_arrival_cross') or 0) * 24.0 if obs.get(r) else None,
                         'obs_head_prev150_rate': ((obs.get(r) or {}).get('meter_head_cross') or 0) * 24.0 if obs.get(r) else None,
                         'far_link_volume': rec['far_link_volume_veh_h'][str(cno)],
                         'dNUF_dz_b0': g0.get('dNUF_dz_veh_h'), 'total_b0': g0.get('total'),
                         'dNUF_dz_b1': (grad.get(r) or {}).get('1', {}).get('dNUF_dz_veh_h'),
                         'dNUF_dz_b2': (grad.get(r) or {}).get('2', {}).get('dNUF_dz_veh_h'),
                         'total_b1': (grad.get(r) or {}).get('1', {}).get('total'),
                         'total_b2': (grad.get(r) or {}).get('2', {}).get('total')})
        del d
        print(tag, T, round(time.time() - t0, 1), flush=True)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'model_%s.json' % tag), 'w', encoding='utf-8') as h:
        json.dump({'tag': tag, 'root': root, 'records': recs, 'elapsed_s': time.time() - t0}, h)
    with open(os.path.join(out_dir, 'model_%s.csv' % tag), 'w', encoding='utf-8', newline='') as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print('wrote', tag, len(recs), round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
