"""S7: which links carry the late-reported removals; are they freeway-chain / boundary / ramp links of the plant.
    python -B s7_links.py [--root R] [--robs D]
(plant geometry from <root>, obs150 err_*.jsonl from <robs>/decisions_<run>/obs150; read only, stdout only)"""
import collections
import glob
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
c.apply(_ap.parse_args())
ROOT = c.R
OBS = c.DEC / 'obs150'
g = json.load(open(ROOT / 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3c3_nc_20261001/observations/s31_v3c3nc_observations/geometry.json', encoding='utf-8'))
addr = g.get('addresses', {})
rows = []
for f in sorted(glob.glob(str(OBS / 'err_*.jsonl'))):
    T = int(Path(f).name[4:10])
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        r['_T'] = T
        rows.append(r)
rem = [r for r in rows if r['kind'] == 'lane_change_removal']
out = {}
for link, n in collections.Counter(str(r['link']) for r in rem).most_common():
    late = sum(1 for r in rem if str(r['link']) == link and r['time_sec'] <= r['_T'] - 150)
    out[link] = dict(removals=n, late=late, plant_address=addr.get(link))
print(json.dumps(out, indent=1))
print('geometry keys', list(g.keys())[:15])
det = json.load(open(ROOT / 'diagnostics/sdmpc_n31_20260924/obs150/obs150_install.json', encoding='utf-8')) if (ROOT / 'diagnostics/sdmpc_n31_20260924/obs150/obs150_install.json').is_file() else None
