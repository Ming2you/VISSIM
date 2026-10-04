"""Summarize K8 worker jobs: objective, Omega costs, block-end ramp/urban stocks, hook counters; pairwise deltas.
python -B an_jobs.py [--root R] [--out O] 2700 4950 1800   (reads <out>/out/<T>/jobs; writes <out>/out/an_jobs.json)"""
import glob
import json
import pickle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
_ap.add_argument('T', nargs='+', type=int, help='decision times (s)')
_args = _ap.parse_args()
c.apply(_args)

PAIRS = [('REF_scalar', 'REF_scalar_s1'), ('M2ALL_scalar', 'M2ALL_scalar_s1'), ('REF_scalar', 'REF_scalar_cap_s5'),
         ('REF_scalar', 'REF_scalar_cap_s9'), ('M2ALL_scalar', 'REF_scalar'), ('REF_ad', 'REF_ad_s3')]


def hooks(d):
    tot = {}
    by = {}
    for f in glob.glob(str(d / 'hook' / '*.json')):
        r = json.loads(Path(f).read_text(encoding='utf-8'))
        for k, v in r['counters'].items():
            tot[k] = tot.get(k, 0.0) + v
        for k, v in r['maxima'].items():
            tot['max:' + k] = max(tot.get('max:' + k, 0.0), v)
        for k, m in r['by_key'].items():
            for kk, v in m.items():
                by.setdefault(k, {})[kk] = by.setdefault(k, {}).get(kk, 0.0) + v
    return tot, by


def load(T, label):
    d = c.RESULTS / f'{T:06d}' / 'jobs' / label
    p = d / 'result.pickle'
    if not p.is_file():
        return None
    r = pickle.loads(p.read_bytes())
    r['_hooks'] = hooks(d)
    return r


out = {}
for T in _args.T:
    rec = {'jobs': {}, 'pairs': {}}
    labels = sorted(Path(x).name for x in glob.glob(str(c.RESULTS / f'{T:06d}' / 'jobs' / '*')))
    res = {lab: load(T, lab) for lab in labels}
    for lab, r in res.items():
        if r is None:
            continue
        h, by = r['_hooks']
        rec['jobs'][lab] = dict(objective=r.get('objective_veh_h'), error=bool(r.get('error')), patched=r.get('patched'),
                                wall=round(r.get('wall_sec', 0), 1),
                                hooks={k: v for k, v in h.items() if k.startswith(('S1', 'S2', 'S3', 'max:S', 'admit', 'finish_req', 'head_service_dual', 'ledger_transfer_dual'))},
                                by_key={k: v for k, v in by.items() if k.startswith(('S1', 'S3'))})
    for a, b in PAIRS:
        ra, rb = res.get(a), res.get(b)
        if not ra or not rb or ra.get('error') or rb.get('error'):
            continue
        pr = {}
        if ra.get('objective_veh_h') is not None and rb.get('objective_veh_h') is not None:
            pr['objective_a'] = ra['objective_veh_h']
            pr['objective_b'] = rb['objective_veh_h']
            pr['objective_delta'] = rb['objective_veh_h'] - ra['objective_veh_h']
        ca, cb = ra.get('costs') or [], rb.get('costs') or []
        if ca and cb:
            pr['cost_delta_by_owner'] = {i: round(y - x, 6) for i, (x, y) in enumerate(zip(ca, cb)) if abs(y - x) > 1e-9}
        sa, sb = (ra.get('summary') or {}).get('blocks'), (rb.get('summary') or {}).get('blocks')
        if sa and sb:
            blocks = []
            for ba, bb in zip(sa, sb):
                row = {'t': ba['time_sec'],
                       'ramp_queue_delta': {k: round(bb['ramp_queue'][k] - v, 4) for k, v in ba['ramp_queue'].items() if abs(bb['ramp_queue'][k] - v) > 1e-9},
                       'feeding_queue_delta': {k: round(bb['ramp_feeding_movement_queue'].get(k, 0) - v, 4) for k, v in ba['ramp_feeding_movement_queue'].items()
                                               if abs(bb['ramp_feeding_movement_queue'].get(k, 0) - v) > 1e-9},
                       'movement_queue_total_delta': round(bb['movement_queue_total'] - ba['movement_queue_total'], 4),
                       'storage_available_total_delta': round(bb['storage_available_total'] - ba['storage_available_total'], 4),
                       'origin_queue_delta': {k: round(bb['origin_queue'][k] - v, 4) for k, v in ba['origin_queue'].items() if abs(bb['origin_queue'][k] - v) > 1e-9},
                       'prehead_over_a': {k: round(v['prehead_over'], 3) for k, v in ba['ramp_buffers'].items() if v['prehead_over'] > 1e-9},
                       'prehead_over_b': {k: round(v['prehead_over'], 3) for k, v in bb['ramp_buffers'].items() if v['prehead_over'] > 1e-9},
                       'ledger_ttt_delta': (bb['ledger_ttt'] - ba['ledger_ttt']) if ba['ledger_ttt'] is not None else None}
                blocks.append(row)
            pr['blocks'] = blocks
        for key in ('cost_jacobian', 'resource_jacobian'):
            ja, jb = ra.get(key), rb.get(key)
            if ja is not None and jb is not None:
                import numpy as np
                A, B = np.asarray(ja), np.asarray(jb)
                if A.shape == B.shape:
                    D = B - A
                    pr[key] = dict(shape=list(A.shape), max_abs_delta=float(np.max(np.abs(D))), n_changed=int(np.sum(np.abs(D) > 1e-12)),
                                   total_grad_a_norm=float(np.linalg.norm(A.sum(axis=0))), total_grad_delta_norm=float(np.linalg.norm(D.sum(axis=0))),
                                   cols_changed=int(np.sum(np.any(np.abs(D) > 1e-12, axis=0))))
        rec['pairs'][f'{a}__vs__{b}'] = pr
    out[T] = rec
txt = json.dumps(out, indent=1, default=str)
(c.RESULTS / 'an_jobs.json').write_text(txt, encoding='utf-8')
print(txt[:12000])
