"""VERIFY_code-data: how strongly does the model's NUF (predicted accepted mainline merge) respond to meter green?
Reads gradient_rows[*].resource_derivatives_scaled (= dNUF/dz / 1000, sdmpc.py:731 A/scale) for every joint decision.
Read-only; writes verify_cd/out/nufjac_<tag>.json."""
import ctypes, glob, json, os, sys
from collections import defaultdict
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), 0x4000)
except Exception:
    pass
run, tag = sys.argv[1].rstrip('/\\'), sys.argv[2]
name = os.path.basename(run)
dec = os.path.join(run, 'decisions_' + name)
per_meter = defaultdict(list)   # (meter, block) -> [(abs A1*1000 veh/h per z, T, it)]
top_other = []
cap_rows = []
for jp in sorted(glob.glob(os.path.join(dec, 'action_*.joint.json'))):
    T = int(os.path.basename(jp)[7:13])
    j = json.load(open(jp, encoding='utf-8-sig'))
    s = j['selection']
    co = s['coordinates']; n = len(co)
    gr = s['gradient_rows']
    for it in range(len(gr) // n):
        rows = gr[it * n:(it + 1) * n]
        assert all(r['key'] == c['key'] and r['block'] == c['block'] and r['kind'] == c['kind'] for r, c in zip(rows, co))
        best_other = max((abs(r['resource_derivatives_scaled'][1]), r['owner'], r['kind'], r['key'], r['block']) for r in rows if r['kind'] != 'meter')
        top_other.append((T, it, best_other))
        for r in rows:
            if r['kind'] == 'meter':
                per_meter[(r['key'], r['block'])].append((r['resource_derivatives_scaled'][1] * 1000.0, T, it, r['total']))
    bi = s['budget_initialization']
    cap_rows.append(dict(T=T, achieved_nuf=bi['achieved_nuf_veh_h'], cap=bi['nuf_cap_veh_h'],
                         rate_by_ramp=bi.get('accepted_rate_veh_h_by_ramp')))
summary = {}
for (m, b), vals in sorted(per_meter.items()):
    mx = max(vals, key=lambda v: abs(v[0]))
    summary[f'{m}_block{b}'] = dict(n=len(vals), max_abs_dNUF_dz_veh_h=abs(mx[0]), at_T=mx[1], iteration=mx[2],
                                    total_grad_there=mx[3], n_abs_gt_1=sum(abs(v[0]) > 1.0 for v in vals))
summary['_largest_non_meter_A1_median_scaled'] = sorted(t[2][0] for t in top_other)[len(top_other) // 2]
summary['_largest_non_meter_examples'] = top_other[:5]
summary['_rm10490_rate_series'] = [(c['T'], (c['rate_by_ramp'] or {}).get('RM_C10490')) for c in cap_rows][:60]
json.dump(summary, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', f'nufjac_{tag}.json'), 'w'), indent=1, default=str)
for k, v in summary.items():
    if not k.startswith('_rm'):
        print(k, v)
