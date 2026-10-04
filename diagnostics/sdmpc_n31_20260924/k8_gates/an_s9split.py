"""S9 delay change split: storages with no moving sample (-> nominal under the 85e rule) vs mixed storages.
python -B an_s9split.py [--root R] [--out O] 2700 4950 1800
(reads <out>/out/<T>/cap_base, cap_s9; writes <out>/out/an_s9split.json)"""
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
from src.models import urban_queue_model as uqm  # noqa: E402
out = {}
for T in _args.T:
    b = c.RESULTS / f'{T:06d}'
    tb = pickle.loads((b / 'cap_base' / 'template.pickle').read_bytes())
    t9 = pickle.loads((b / 'cap_s9' / 'template.pickle').read_bytes())
    cfg = tb['owned'][0].cfg
    sb, s9 = tb['owned'][1], t9['owned'][1]
    nominal = json.loads((b / 'cap_base' / 'capture.json').read_text(encoding='utf-8'))['projection']['S9_storages_to_nominal']
    rows = {'nominal': [0, 0, 0], 'mixed': [0, 0, 0]}
    occ_w = {'nominal': [0.0, 0.0], 'mixed': [0.0, 0.0]}
    for k in cfg.network.urban_link_storage_veh:
        d0 = uqm._link_delay_steps(sb, cfg, k)
        d1 = uqm._link_delay_steps(s9, cfg, k)
        if d0 == d1:
            continue
        g = 'nominal' if k in nominal else 'mixed'
        rows[g][0] += 1
        rows[g][1] += d0
        rows[g][2] += d1
    out[T] = {g: dict(storages=v[0], delay_steps_base=v[1], delay_steps_s9=v[2], delta=v[2] - v[1]) for g, v in rows.items()}
    out[T]['nominal_list'] = nominal
print(json.dumps(out, indent=1))
(c.RESULTS / 'an_s9split.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
