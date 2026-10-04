"""Compare projected initial states of capture variants (base vs s5 / s9) at one T.  python -B an_proj.py [--root R] [--out O] <T>
(reads <out>/out/<T>/cap_{base,s5,s9,s59}; writes <out>/out/<T>/an_proj.json)"""
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
_ap.add_argument('T', type=int, help='decision time (s)')
_args = _ap.parse_args()
c.apply(_args)
sys.path[:0] = [str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')]
T = _args.T
base = c.RESULTS / f'{T:06d}'


def load(v):
    p = base / f'cap_{v}' / 'template.pickle'
    if not p.is_file():
        return None
    return pickle.loads(p.read_bytes())


from src.models import urban_queue_model as uqm  # noqa: E402
out = {'T': T}
tb = load('base')
fb, sb, rb, _ = tb['owned']
cfg = fb.cfg
step0 = int(round(sb.time_sec))


def arrival_profile(state):
    prof = defaultdict(float)
    for link, d in state.urban_arrival_buffer.items():
        for step, n in d.items():
            prof[int(step) - step0] += float(n)
    return prof


def delays(state):
    return {k: uqm._link_delay_steps(state, cfg, k) for k in cfg.network.urban_link_storage_veh}


pb = arrival_profile(sb)
db = delays(sb)
out['base_arrival_total'] = sum(pb.values())
out['base_arrival_by_offset'] = {str(k): round(v, 3) for k, v in sorted(pb.items())}
for v in ('s5', 's9', 's59'):
    t = load(v)
    if t is None:
        continue
    f, s, r, _ = t['owned']
    rec = {}
    pv = arrival_profile(s)
    rec['arrival_total'] = sum(pv.values())
    rec['arrival_by_offset'] = {str(k): round(x, 3) for k, x in sorted(pv.items())}
    rec['arrival_delta_by_offset'] = {str(k): round(pv.get(k, 0.0) - pb.get(k, 0.0), 3) for k in sorted(set(pv) | set(pb))
                                      if abs(pv.get(k, 0.0) - pb.get(k, 0.0)) > 1e-9}
    dv = delays(s)
    ch = {k: (db[k], dv[k]) for k in db if db[k] != dv[k]}
    occ = {k: float(cfg.network.urban_link_storage_veh[k]) - float(sb.urban_link_storage.get(k, 0.0)) for k in db}
    rec['delay_changed_storages'] = len(ch)
    rec['delay_steps_sum_base'] = sum(db.values())
    rec['delay_steps_sum_variant'] = sum(dv.values())
    rec['delay_changed_top'] = sorted(([k, a, b, round(occ[k], 1)] for k, (a, b) in ch.items()), key=lambda x: -abs(x[2] - x[1]))[:15]
    sp_ch = {k: (float(sb.urban_link_speed_kph.get(k, float('nan'))), float(s.urban_link_speed_kph.get(k, float('nan'))))
             for k in set(sb.urban_link_speed_kph) | set(s.urban_link_speed_kph)
             if sb.urban_link_speed_kph.get(k) != s.urban_link_speed_kph.get(k)}
    rec['speed_changed_storages'] = len(sp_ch)
    rec['movement_queue_total_delta'] = sum(float(x) for x in s.urban_movement_queue.values()) - sum(float(x) for x in sb.urban_movement_queue.values())
    rec['storage_available_total_delta'] = sum(float(x) for x in s.urban_link_storage.values()) - sum(float(x) for x in sb.urban_link_storage.values())
    rec['ramp_queue_delta'] = {k: float(s.ramp_queue[k]) - float(sb.ramp_queue[k]) for k in sb.ramp_queue if float(s.ramp_queue[k]) != float(sb.ramp_queue[k])}
    cj = json.loads((base / f'cap_{v}' / 'capture.json').read_text(encoding='utf-8'))
    rec['capture_diag'] = cj.get('diag')
    rec['patched_sha256'] = cj.get('patched_sha256')
    out[v] = rec
print(json.dumps(out, indent=1, default=str)[:6000])
(base / 'an_proj.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
