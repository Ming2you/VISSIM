"""Aggregate S3-wide hook files of one run directory; validate the read-only sweep against the reverse Jacobian.

    python -B an_s3.py <run_dir> [<reference result.pickle> | <reference full dir>]     -> <run_dir>/an_s3.json

K8-0b port of the scratch amend1/s3/tools/an_s3.py (sha256 6369c050539c79a6...); only this docstring differs, the computation
lines are byte-identical. <run_dir> is an s3run.py job or full folder (hook/hook_*.json; result.pickle for a job).
"""
import glob
import json
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

run = sys.argv[1]
ref = sys.argv[2] if len(sys.argv) > 2 else None
agg = defaultdict(lambda: defaultdict(float))
mx = defaultdict(float)
samples = {}
procs = []
validation = []
sweeps = []
for f in sorted(glob.glob(os.path.join(run, 'hook', 'hook_*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    procs.append({'pid': d['pid'], 'role': d['role'], 'final': d['final'], 'pending': d['pending_unevaluated_events'],
                  'jacobian_traces': d['counters'].get('jacobian_traces', 0), 'hook_errors': d['counters'].get('hook_errors', 0),
                  'errors': d['extra'].get('errors'), 'anchor_mismatch': d['extra'].get('anchor_mismatch'),
                  'tangent_install_seen': d['counters'].get('tangent_install_seen', 0)})
    for site, row in d['by_site'].items():
        for k, v in row.items():
            if k == 'patched':
                agg[site]['patched_procs'] += v
            else:
                agg[site][k] += v
    for k, v in d['max'].items():
        mx[k] = max(mx[k], v)
    for k, v in d['samples'].items():
        samples.setdefault(k, v[:3])
    for s in d['extra'].get('sweeps', []):
        sweeps.append({k: s[k] for k in ('nodes', 'axes', 'events', 'real_events', 'sec')})
        validation.append((d['pid'], s))

result = {'run': run, 'processes': procs, 'sweeps': sweeps}
# sweep validation: worker result Jacobian (cost rows + resource rows) . r == forward directional tangent at outputs
if ref is None and os.path.isfile(os.path.join(run, 'result.pickle')):
    res = pickle.load(open(os.path.join(run, 'result.pickle'), 'rb'))
    J = np.array(res['cost_jacobian'] + res['resource_jacobian'], dtype=np.float64)
    for pid, s in validation:
        r = np.random.default_rng(s['rng_seed']).standard_normal(s['axes'])
        jr = J @ r
        t = np.array(s['out_t'][:len(jr)])
        sc = np.array(s['out_s'][:len(jr)])
        err = np.abs(jr - t)
        result['sweep_validation'] = {'outputs': int(len(jr)), 'max_abs_err': float(err.max()),
                                      'max_rel_err_vs_bound': float((err / np.maximum(sc, 1e-300)).max()),
                                      'max_abs_Jr': float(np.abs(jr).max()), 'nonzero_rows': int((np.abs(jr) > 0).sum())}

table = {}
for site in sorted(agg):
    row = agg[site]
    table[site] = {k: (int(v) if float(v).is_integer() else v) for k, v in sorted(row.items())}
result['by_site'] = table
result['max'] = dict(mx)
result['samples'] = samples
result['totals'] = {k: sum(r.get(k, 0) for r in table.values()) for k in
                    ('ev_struct', 'ev_exact_nonzero', 'ev_exact_zero', 'ev_exact_cancellation_level', 'ev_unevaluated',
                     'drop_rdual0', 'drop_fdual', 'probe_exact_nonzero', 'probe_exact_zero',
                     'probe_exact_cancellation_level', 'probe_unevaluated')}
out = os.path.join(run, 'an_s3.json')
json.dump(result, open(out, 'w', encoding='utf-8'), indent=1)
print(json.dumps({'totals': result['totals'], 'sweeps': sweeps, 'validation': result.get('sweep_validation'),
                  'procs': len(procs), 'errors': [p for p in procs if p['hook_errors'] or p['errors'] or p['anchor_mismatch']]}))
