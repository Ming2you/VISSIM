# -*- coding: utf-8 -*-
"""N34 (2026-10-24): read-only extraction of the SDMPC model's SC1001-west-gate flows per V-A decision (N3).

Usage: python -B n34_model.py <tag> <run_root> <out.json>
Per action_<T>.joint.json with window end <= 9000 s:
- tangent record = the one whose predicted merge equals the selected plan for the four FW_E ramps; if none, the closest
  by summed |difference| (same rule as O4 o4_model.py / o4_wout.py)
- flow_counts (veh over the window) and passive_stocks_veh_h of that record whose key mentions SC1001, in_SC1001_W,
  OR_D_W, OR_D_E, RM_C10490 or RM_C10482
- runtime gate on-ramp shares (diagnostics gate_onramp_beta_*), far link volumes of connectors 10490, 10482, 10491, 129, 32
- lane observation frame at T: vehicle counts on links 32, 129, 127, 10490, 10482, 10491 by static route tag
Reads only. Writes only <out.json>.
"""
import glob
import json
import os
import re
import sys
import time

RAMPS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
PAT = re.compile(r'SC1001|in_SC1001_W|OR_D_W|OR_D_E|RM_C10490|RM_C10482')
LINKS = (32, 129, 127, 10490, 10482, 10491, 10778, 10777)


def dig(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def load_any(p):
    raw = open(p, 'rb').read()
    for enc in ('utf-8-sig', 'utf-16'):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            pass
    raise ValueError('undecodable ' + p)


def main():
    tag, root, out = sys.argv[1], sys.argv[2].rstrip('/\\'), sys.argv[3]
    ddir = os.path.join(root, 'decisions_' + os.path.basename(root))
    t0 = time.time()
    recs = []
    only = os.environ.get('N34_ONLY_T')
    for jp in sorted(glob.glob(os.path.join(ddir, 'action_*.joint.json'))):
        T = int(re.search(r'action_(\d+)\.joint\.json$', jp).group(1))
        if only and T != int(only):
            continue
        d = json.load(open(jp, encoding='utf-8-sig'))
        sel = d['selection']
        prm = sel['final_constraints']['physical_ramp_merge']
        w0, w1 = prm['start_sec'], prm['end_sec']
        if w1 > 9000.0:
            del d
            continue
        tds = sel.get('tangent_derivatives') or []
        best, bd, exact = None, None, False
        for i, td in enumerate(tds):
            sp = dig(td, 'surrogate_prediction', 'quantities', 'predicted_ramp_merge', 'accepted_vehicles_by_ramp') or {}
            if not sp or any(sp.get(r) is None for r in RAMPS):
                continue
            dd = sum(abs(sp[r] - prm['accepted_vehicles_by_ramp'][r]) for r in RAMPS)
            if bd is None or dd < bd or (dd == bd):
                best, bd = i, dd
        if best is not None:
            exact = bd < 1e-9 * 4
        td = tds[best] if best is not None else {}
        fc = dig(td, 'surrogate_prediction', 'control_area', 'flow_counts') or {}
        ps = dig(td, 'surrogate_prediction', 'sdmpc_omega_partition', 'passive_stocks_veh_h') or {}
        served = dig(td, 'surrogate_prediction', 'quantities', 'served_by_movement_veh') or {}
        diag = dig(d, 'physical_response_cache', 'warm_budget_binding', 'source_action', 'diagnostics') or \
            dig(sel, 'surrogate_query', 'warm_budget_binding', 'source_action', 'diagnostics') or {}
        betas = {k: v for k, v in diag.items() if k.startswith('gate_onramp_beta')}
        far = dig(diag, '_control_area_written_meter_context', 'raw', 'local_observation', 'far_measurement', 'link_volume_veh_h') or {}
        init = {}
        fp = os.path.join(ddir, 'lane_observations', 'frame_%06d.json' % T)
        if os.path.isfile(fp):
            fr = load_any(fp)
            for v in fr['vehicles']:
                ln = int(v[1])
                if ln in LINKS:
                    key = '%d|%s' % (ln, ('%d:%d' % (int(v[6]), int(v[7]))) if v[6] is not None and v[7] is not None else 'none')
                    init[key] = init.get(key, 0) + 1
        recs.append({'T': T, 'window': [w0, w1], 'td_index': best, 'td_exact': exact, 'td_sum_abs_diff_veh': bd,
                     'pred_veh': {r: prm['accepted_vehicles_by_ramp'][r] for r in RAMPS},
                     'flows': {k: v for k, v in fc.items() if PAT.search(k)},
                     'passive_veh_h': {k: v for k, v in ps.items() if PAT.search(k)},
                     'served': {k: v for k, v in served.items() if PAT.search(k)},
                     'betas': betas, 'far_link_volume_veh_h': {str(c): far.get(str(c)) for c in (10490, 10482, 10491, 129, 32, 127)},
                     'init_by_link_tag': init})
        del d
        print(tag, T, round(time.time() - t0, 1), flush=True)
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump({'tool': 'n34_model.py', 'tag': tag, 'root': root, 'records': recs, 'elapsed_s': time.time() - t0}, g)
    os.replace(tmp, out)
    print('wrote', tag, len(recs), round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
