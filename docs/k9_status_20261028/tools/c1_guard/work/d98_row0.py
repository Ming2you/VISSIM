# Read-only, data-after look: first-row (t_end T+1, stage urban) model_stock_veh difference Omega - OFF
# in the already-seen C1 probe plant jobs (v3c3-s31 T=1500) and its edge neighbours (k92_series 'edges').
import json, hashlib
import numpy as np
J = 'D:/VISSIM-merge/k8_gate_trees/c1/out/probe/plant/sa/jobs/%s/TL3_1500_SAF_OBS_H3/k92_series.npz'
out = {'inputs': {a: hashlib.sha256(open(J % a, 'rb').read()).hexdigest() for a in ('c1poff', 'c1pomega')}}
o = np.load(J % 'c1poff', allow_pickle=True); w = np.load(J % 'c1pomega', allow_pickle=True)
keys = [str(k) for k in o['keys']]
assert keys == [str(k) for k in w['keys']]
edges = [tuple(map(str, e)) for e in o['edges']]
out['edges_equal'] = edges == [tuple(map(str, e)) for e in w['edges']]
out['row0'] = {'t_end': float(o['t_end'][0]), 'stage': str(o['stage_names'][int(o['stage'][0])])}
d0 = w['model'][0] - o['model'][0]
KE = {keys[i]: float(d0[i]) for i in range(len(keys)) if abs(d0[i]) > 1e-12}
out['row0_diff'] = KE
N1 = set()
for a, b in edges:
    if a in KE: N1.add(b)
    if b in KE: N1.add(a)
out['N1_size'] = len(N1 - set(KE))
first = None
for r in range(o['model'].shape[0]):
    d = w['model'][r] - o['model'][r]
    s = {keys[i] for i in range(len(keys)) if abs(d[i]) > 1e-12}
    if s - (set(KE) | N1):
        first = {'row': r, 't_end': float(o['t_end'][r]), 'keys': sorted(s - (set(KE) | N1))[:10]}
        break
out['first_row_outside_KE_N1'] = first
print(json.dumps(out, ensure_ascii=False, indent=1))
