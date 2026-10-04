"""lane_group_kinds: movement capacities by kind, base (default ['internal']) vs lgk capture (+boundary_in/out, off_ramp).
python -B an_lgk.py [--root R] [--out O] 2700   (reads <out>/out/<T>/cap_base, cap_lgk; writes <out>/out/<T>/an_lgk.json)"""
import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
_ap.add_argument('T', type=int, help='decision time (s)')
_args = _ap.parse_args()
c.apply(_args)
sys.path[:0] = [str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')]
T = _args.T
b = c.RESULTS / f'{T:06d}'
tb = pickle.loads((b / 'cap_base' / 'template.pickle').read_bytes())
cfg = tb['owned'][0].cfg
net = cfg.network
caps = dict(net.movement_capacity_by_movement_veh_h)
specs = net.urban_movements
kinds = Counter(str(s.get('kind', '')) for s in specs.values())
out = {'T': T, 'kinds': dict(kinds)}
by_kind = defaultdict(list)
for m, s in specs.items():
    by_kind[str(s.get('kind', ''))].append(caps.get(m))
out['cap_stats_base'] = {k: dict(n=len(v), n_206_per_lane=sum(1 for x in v if x is not None and abs((x % 206.5306) ) < 0.01 or (x is not None and abs(x - round(x / 206.5306) * 206.5306) < 0.01)),
                                 median=sorted(x for x in v if x is not None)[len(v) // 2] if v else None) for k, v in by_kind.items()}
p = b / 'cap_lgk' / 'template.pickle'
if p.is_file():
    tl = pickle.loads(p.read_bytes())
    cl = dict(tl['owned'][0].cfg.network.movement_capacity_by_movement_veh_h)
    changed = {m: (caps.get(m), cl.get(m), str(specs[m].get('kind')), str(specs[m].get('signal'))) for m in specs if caps.get(m) != cl.get(m)}
    out['changed_n'] = len(changed)
    out['changed_by_kind'] = dict(Counter(v[2] for v in changed.values()))
    out['changed_by_signal'] = dict(Counter(v[3] for v in changed.values()))
    out['changed_rows'] = sorted(([m, round(a or 0, 1), round(bb or 0, 1), k, sgn] for m, (a, bb, k, sgn) in changed.items()),
                                 key=lambda r: -abs(r[2] - r[1]))[:40]
    out['ratio_median'] = sorted((bb / a) for a, bb, k, sgn in changed.values() if a)[len(changed) // 2] if changed else None
    sb, sl = tb['owned'][1], tl['owned'][1]
    out['state_movement_queue_total_delta'] = sum(float(x) for x in sl.urban_movement_queue.values()) - sum(float(x) for x in sb.urban_movement_queue.values())
print(json.dumps(out, indent=1, default=str))
(b / 'an_lgk.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
