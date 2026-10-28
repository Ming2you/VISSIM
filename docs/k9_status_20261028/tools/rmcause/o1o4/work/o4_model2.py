# -*- coding: utf-8 -*-
"""O4 follow-up (2026-10-24): read-only extraction of the model's ramp-feeding flow counts per decision.

Usage: python -B o4_model2.py <tag> <run_root> <out_dir>
From the tangent record whose predicted merge equals the selected plan's (as in o4_model.py), reads
surrogate_prediction.control_area.flow_counts entries that feed or drain the four FW_E on-ramps' sources:
movement:SC1004_*_to_W (into SC1004_W_out, the 1135 choice link 68), legsplit:SC1004_W_out, tail_exit:SC1004_W_tail,
movement/arrival:SC1001_W_to_onE (-> RM_C10490), movement:SC1004_W_to_onE (-> RM_C10639), storage:shared_69->ramp:*,
legsplit:SC1001_W_out, movement:SC1001_*_to_W. Writes <out_dir>/model2_<tag>.json.
"""
import glob, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

RAMPS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
PAT = re.compile(r'^(movement:SC1004_[A-Z0-9_]+_to_W|movement:SC1004_W_to_onE|legsplit:SC100[14]_W_out|'
                 r'tail_exit:SC100[14]_W_tail|movement:SC1001_W_to_onE|arrival:SC1001_W_to_onE|'
                 r'movement:SC1001_[A-Z0-9_]+_to_W|storage:shared_69->ramp:.*|input:shared:shared_69|'
                 r'movement:SC1001_W_to_onW|arrival:SC1001_W_to_onW)$')


def main():
    below_normal()
    tag, root, out_dir = sys.argv[1], sys.argv[2].rstrip('/\\'), sys.argv[3]
    ddir = os.path.join(root, 'decisions_' + os.path.basename(root))
    t0 = time.time()
    recs = []
    for jp in sorted(glob.glob(os.path.join(ddir, 'action_*.joint.json'))):
        T = int(re.search(r'action_(\d+)\.joint\.json$', jp).group(1))
        d = json.load(open(jp, encoding='utf-8-sig'))
        sel = d['selection']
        prm = sel['final_constraints']['physical_ramp_merge']
        match = None
        for i, td in enumerate(sel.get('tangent_derivatives') or []):
            sp = (((td.get('surrogate_prediction') or {}).get('quantities') or {}).get('predicted_ramp_merge') or {}).get('accepted_vehicles_by_ramp') or {}
            if sp and all(abs(sp.get(r, -1e9) - prm['accepted_vehicles_by_ramp'][r]) < 1e-9 for r in RAMPS):
                match = i
        tdrows = []
        for i, td in enumerate(sel.get('tangent_derivatives') or []):
            spq = (td.get('surrogate_prediction') or {})
            pv = ((spq.get('quantities') or {}).get('predicted_ramp_merge') or {}).get('accepted_vehicles_by_ramp') or {}
            flows = (spq.get('control_area') or {}).get('flow_counts') or {}
            qq = {}
            cp = spq.get('central_physical') or {}
            for n, v in zip(cp.get('names', []), cp.get('values', [])):
                m = re.match(r'physical/(\d+(?:\.\d+)?)/ramp_queue/(RM_C\d+)/0/lower$', n)
                if m and m.group(2) in RAMPS:
                    qq.setdefault(m.group(2), {})[str(int(float(m.group(1))))] = -v
            tdrows.append({'index': i, 'pred_veh': {r: pv.get(r) for r in RAMPS}, 'queues': qq,
                           'flows': {k: v for k, v in flows.items() if PAT.match(k)}})
        recs.append({'T': T, 'window': [prm['start_sec'], prm['end_sec']], 'match_td': match,
                     'final_pred_veh': {r: prm['accepted_vehicles_by_ramp'][r] for r in RAMPS}, 'tds': tdrows})
        del d
    os.makedirs(out_dir, exist_ok=True)
    json.dump({'tag': tag, 'records': recs, 'elapsed_s': time.time() - t0},
              open(os.path.join(out_dir, 'model2_%s.json' % tag), 'w', encoding='utf-8'))
    print('wrote', tag, len(recs), round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
