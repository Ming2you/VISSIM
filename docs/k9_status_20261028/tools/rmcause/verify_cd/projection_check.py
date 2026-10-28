"""VERIFY_code-data: resource projection (sdmpc.py:839, qp_bounds sdmpc_central.py:31-33) at decisions where
the NUF raw residual c + A@proposal was positive. Approximates the projection by the single binding NUF row
(minimum-norm shift -mu*A1, mu = (raw1-eps1)/||A1||^2), ignoring box/phase rows; reports meter shifts in seconds.
Read-only."""
import json, sys, os
import numpy as np

run, tag, times = sys.argv[1], sys.argv[2], [int(t) for t in sys.argv[3].split(',')]
name = os.path.basename(run.rstrip('/\\'))
dec = os.path.join(run, 'decisions_' + name)
out = {}
for T in times:
    j = json.load(open(os.path.join(dec, 'action_%06d.joint.json' % T), encoding='utf-8-sig'))
    s = j['selection']
    co = s['coordinates']
    n = len(co)
    gr = s['gradient_rows']
    iters = len(gr) // n
    owner_ix = {}
    for i, c in enumerate(co):
        owner_ix.setdefault(c['owner'], []).append(i)
    res = []
    for u in s['iteration_dual_updates']:
        it = u['iteration']
        rows = gr[it * n:(it + 1) * n] if iters > it else None
        if rows is None:
            continue
        keys_ok = all(r['owner'] == c['owner'] and r['kind'] == c['kind'] and r['key'] == c['key'] and r['block'] == c['block'] for r, c in zip(rows, co))
        A1 = np.array([r['resource_derivatives_scaled'][1] for r in rows])
        A0 = np.array([r['resource_derivatives_scaled'][0] for r in rows])
        prop = np.zeros(n)
        for r in s['local_rows']:
            if r['iteration'] != it:
                continue
            for pos, i in enumerate(owner_ix[r['owner']]):
                prop[i] = r['step'][pos]
        raw1 = u['raw_residual_scaled'][1]
        eps1 = 40.0 / 1000.0 if False else 1e-7 / 1000.0
        mu = max(0.0, raw1 - eps1) / float(A1 @ A1) if A1 @ A1 > 0 else float('nan')
        shift = -mu * A1
        meters = [(co[i]['key'], co[i]['block'], round(prop[i] * 10, 6), round(shift[i] * 10, 6), round((prop[i] + shift[i]) * 10, 6), round(A1[i], 6))
                  for i in range(n) if co[i]['kind'] == 'meter']
        big = sorted(((abs(A1[i]), co[i]['owner'], co[i]['kind'], co[i]['key'], co[i]['block']) for i in range(n)), reverse=True)[:8]
        res.append(dict(iteration=it, keys_aligned=keys_ok, raw=u['raw_residual_scaled'], A1_dot_prop=float(A1 @ prop),
                        A1_norm2=float(A1 @ A1), mu=mu, meter_prop_shift_total_sec=meters, largest_A1=big,
                        max_meter_tighten_sec=float(min(shift[i] * 10 for i in range(n) if co[i]['kind'] == 'meter'))))
    out[T] = res
    tr = s['trial_rows']
    out[str(T) + '_trials'] = [(t['cap'], t['iteration'], t['objective'], t['feasible'], t['action_token'][:12]) for t in tr]
    out[str(T) + '_candidates'] = s['candidates']
print(json.dumps(out, indent=1, default=str)[:12000])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', f'projection_{tag}.json'), 'w'), indent=1, default=str)
