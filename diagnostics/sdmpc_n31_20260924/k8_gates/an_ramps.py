"""Ramp buffer geometry and initial stocks from captured templates (S1 context).  python -B an_ramps.py [--root R] [--out O] 2700 4950 1800   (reads <out>/out/<T>/cap_base; writes <out>/out/an_ramps.json)"""
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
res = {}
for T in _args.T:
    t = pickle.loads((c.RESULTS / f'{T:06d}' / 'cap_base' / 'template.pickle').read_bytes())
    f, st, ref, fc = t['owned']
    cfg = f.cfg
    rows = {}
    feeding = {}
    for m, spec in (cfg.network.urban_movements or {}).items():
        r = str(spec.get('ramp', '') or '')
        if r:
            feeding.setdefault(r, []).append(m)
    for name, b in st.lane_ramp_runtime.buffers.items():
        lanes = getattr(b, '_lane_buffers', None) or [b]
        up = sum(float(n) for x in lanes for _, n in x._upstream)
        head = sum(float(x._head_ready) for x in lanes)
        down = sum(float(n) for x in lanes for _, n in x._downstream)
        ready = sum(float(x._merge_ready) for x in lanes)
        rows[name] = dict(connector=b.connector_id, length_m=round(b.length_m, 1), head_pos_m=round(b.head_position_m, 1),
                          lanes=b.lanes, spacing_m=b.spacing_m, capacity_veh=round(b.capacity_veh, 1),
                          prehead_capacity_veh=round(b.head_position_m * b.lanes / b.spacing_m, 1),
                          posthead_capacity_veh=round((b.length_m - b.head_position_m) * b.lanes / b.spacing_m, 1),
                          stock_pre=round(up + head, 2), stock_post=round(down + ready, 2),
                          ramp_queue_cap=cfg.network.ramp_queue_cap(name) if hasattr(cfg.network, 'ramp_queue_cap') else None,
                          lane_resolved=hasattr(b, '_lane_buffers'),
                          feeding_movements=feeding.get(name, []),
                          feeding_queue_veh=round(sum(float(st.urban_movement_queue.get(m, 0.0)) for m in feeding.get(name, [])), 2),
                          service_green10_vph=cfg.network.physical_ramp_branches['ramps'][name]['service_by_green_veh_h'].get('10'),
                          service_green2_vph=cfg.network.physical_ramp_branches['ramps'][name]['service_by_green_veh_h'].get('2'))
    res[T] = rows
print(json.dumps(res, indent=1))
(c.RESULTS / 'an_ramps.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
