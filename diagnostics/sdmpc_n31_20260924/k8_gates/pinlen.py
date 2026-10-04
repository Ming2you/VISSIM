"""List referenced files (plant manifest pins + config strings) whose absolute path under the code root exceeds
259 chars (then K8_LONGPATH=1, set by k8common.base_env, is load-bearing).
    python -B pinlen.py [--root R]   (read only, stdout only)"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402
_ap = c.parser(__doc__)
c.apply(_ap.parse_args())
R = c.R
pat = re.compile(r'^(diagnostics|evaluation|outputs|network|plant|vendor|scripts|harness|tools|src|docs)[/\\]')
refs = set()
def walk(o):
    if isinstance(o, dict):
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
    elif isinstance(o, str) and pat.match(o):
        refs.add(o.replace(chr(92), '/').split(' ')[0] if o.endswith('.json network.urban_avg_vehicle_length_m') else o.replace(chr(92), '/'))
for f in ['diagnostics/sdmpc_n31_20260924/config_n31_v2.json', 'diagnostics/sdmpc_n31_20260924/plant_n31_v2.json',
          'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json']:
    walk(json.load(open(R / f, encoding='utf-8-sig')))
long_ = []
for r in sorted(refs):
    p = str(R / r)
    long_.append((len(p), r))
long_.sort(reverse=True)
for n, r in long_[:15]:
    print(n, r)
# any file in the copied tree under diagnostics/sdmpc_n31_20260924 or evaluation/controllers deeper than 259
import os
cnt = 0
for base in ['diagnostics/sdmpc_n31_20260924', 'evaluation/controllers', 'vendor', 'outputs', 'evaluation/real_world_modi_control_ver2_20260907',
             'evaluation/real_world_modi_control_ver2n21_20260907', 'evaluation/real_world_modi_inventory', 'evaluation/calibration']:
    for root, dirs, files in os.walk('\\\\?\\' + str(R / base)):
        for fn in files:
            full = os.path.join(root, fn)[4:]
            if len(full) > 259:
                cnt += 1
                if cnt < 10:
                    print('DEEP', len(full), full[len(str(R)) + 1:])
print('deep files', cnt)
