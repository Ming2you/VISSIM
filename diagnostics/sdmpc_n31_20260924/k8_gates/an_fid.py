"""One-step (T+150) urban fidelity of the held prediction: base vs S5 / S9 projection variants against the observed
projection at T+150 (base capture of R-obs state T+150).
    python -B an_fid.py [--root R] [--out O] 1800 2700 4950   (reads <out>/out/<T>, <T+150>; writes <out>/out/an_fid.json)"""
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
sys.path[:0] = [str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')]
out = {}
for T in _args.T:
    tnext = pickle.loads((c.RESULTS / f'{T + 150:06d}' / 'cap_base' / 'template.pickle').read_bytes())
    cfg = tnext['owned'][0].cfg
    sn = tnext['owned'][1]
    cap = cfg.network.urban_link_storage_veh
    obs_q = {k: float(v) for k, v in sn.urban_movement_queue.items()}
    obs_occ = {k: float(cap[k]) - float(sn.urban_link_storage.get(k, cap[k])) for k in cap}
    rec = {}
    for lab in ('REF_scalar2' if T == 2700 else 'REF_scalar', 'REF_scalar_cap_s5', 'REF_scalar_cap_s9'):
        p = c.RESULTS / f'{T:06d}' / 'jobs' / lab / 'result.pickle'
        if not p.is_file():
            continue
        r = pickle.loads(p.read_bytes())
        b0 = r['summary']['blocks'][0]
        q = b0['movement_queue']
        occ = {k: float(cap[k]) - b0['storage_available'].get(k, cap[k]) for k in cap}
        eq = [q.get(k, 0.0) - v for k, v in obs_q.items()]
        eo = [occ[k] - v for k, v in obs_occ.items()]
        nz = [q.get(k, 0.0) - v for k, v in obs_q.items() if v > 0 or q.get(k, 0.0) > 0]
        rec[lab] = dict(t=b0['time_sec'], queue_mae=sum(map(abs, eq)) / len(eq), queue_mae_nonzero=sum(map(abs, nz)) / max(1, len(nz)),
                        queue_bias_total=sum(eq), storage_occ_mae=sum(map(abs, eo)) / len(eo), storage_occ_bias_total=sum(eo),
                        queue_plus_storage_bias=sum(eq) + sum(eo), n_mov=len(eq), n_sto=len(eo))
    out[T] = rec
print(json.dumps(out, indent=1))
(c.RESULTS / 'an_fid.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
