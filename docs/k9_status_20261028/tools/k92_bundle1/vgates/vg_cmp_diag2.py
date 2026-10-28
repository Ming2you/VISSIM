"""VerifyGates post-data diagnosis D1b (disclosed): replay_manifest raw_sha256/replay and obs150 derived
inputs/raw_sha256 = sha256 of the canonical JSON (sort_keys, separators , :, ensure_ascii False, allow_nan False; the
form written in obs150_contract.py:93-100) of that side's state_<T>.json['obs150'] object, and that object differs
between the two sides only in strings holding the output root.  Booleans only.
    python -B vg_cmp_diag2.py --dest <json>
"""
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vglib as V
OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
SIDES = {'orig': OK2 / 'k92t', 'rerun': OK2 / 'vg2t'}
CASES = {'J': ('jb', 'replays/000900', 900), 'F': ('f_b1', 'replays/s43/001050', 1050)}
def canon_sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf-8')).hexdigest()
def swap(x):
    if isinstance(x, dict):
        return {swap(k): swap(v) for k, v in x.items()}
    if isinstance(x, list):
        return [swap(v) for v in x]
    if isinstance(x, str):
        return x.replace('k92_b1\vg2t', 'k92_b1\k92t').replace('k92_b1/vg2t', 'k92_b1/k92t')
    return x
ap = argparse.ArgumentParser(); ap.add_argument('--dest', required=True); a = ap.parse_args()
res = {}
for key, (arm, rep, T) in CASES.items():
    row, objs = {}, {}
    for s, root in SIDES.items():
        st = V.rjson(root / arm / rep / ('state_%06d.json' % T))
        objs[s] = st['obs150']
        man = V.rjson(root / arm / rep / 'replay_manifest.json')
        der = V.rjson(root / arm / rep / 'obs150' / ('derived_%06d.json' % T))
        h = canon_sha(st['obs150'])
        row[s] = {'manifest_raw_replay_is_canon_obs150': man['raw_sha256']['replay'] == h,
                  'derived_raw_is_canon_obs150': der['inputs']['raw_sha256'] == h}
    row['obs150_equal_after_swap'] = objs['orig'] == swap(objs['rerun'])
    row['obs150_raw_equal'] = objs['orig'] == objs['rerun']
    res[key] = row
V.wjson(a.dest, res)
print('VG_CMP_DIAG2', json.dumps(res))
