"""ReviewDeclare check 3 (read-only, light): do recorded actions carry metadata.sdmpc_state (the only case in which
load_prices checks the policy token, OU sdmpc.py:516-528)?  R-obs v3c3-s31/s43 (never s47) and V-A v3c3-s31/s41/s43,
T = 900..9000 step 150.  Prints counts and controller variants only.
"""
import json
import sys
from pathlib import Path

RUNS = {'robs_s31': Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31/decisions_sdmpc31_v3c3_nc_s31'),
        'robs_s43': Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s43/decisions_sdmpc31_v3c3_nc_s43'),
        'va_s31': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31'),
        'va_s41': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/decisions_sdmpc31_v3c3_k92va_s41'),
        'va_s43': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/decisions_sdmpc31_v3c3_k92va_s43')}
out = {}
for name, d in RUNS.items():
    rows = {'files': 0, 'with_sdmpc_state': 0, 'variants': {}}
    for T in range(900, 9001, 150):
        p = d / ('action_%06d.json' % T)
        if not p.is_file():
            continue
        j = json.loads(p.read_text(encoding='utf-8-sig'))
        m = j.get('metadata', {})
        rows['files'] += 1
        rows['with_sdmpc_state'] += int('sdmpc_state' in m)
        v = str(m.get('controller_variant'))
        rows['variants'][v] = rows['variants'].get(v, 0) + 1
    out[name] = rows
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(out))
