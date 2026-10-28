"""ReviewDeclare check 3b (read-only, light; replaces the aborted rev_c1_robs.py whose full V-A scan was ~10 GB of
JSON): do recorded actions carry metadata.sdmpc_state (the only case in which load_prices checks the policy token,
OU sdmpc.py:516-528)?  R-obs v3c3-s31/s43 (never s47): every T = 900..9000 step 150 (files ~0.4 MB).
V-A v3c3-s31/s41/s43: T in {900, 1050, 2700, 4950} only.  Prints counts and controller variants only.
"""
import json
import sys
from pathlib import Path

ROBS = {'robs_s31': Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31/decisions_sdmpc31_v3c3_nc_s31'),
        'robs_s43': Path('D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s43/decisions_sdmpc31_v3c3_nc_s43')}
VA = {'va_s31': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31'),
      'va_s41': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/decisions_sdmpc31_v3c3_k92va_s41'),
      'va_s43': Path('D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/decisions_sdmpc31_v3c3_k92va_s43')}


def scan(d, times):
    rows = {'files': 0, 'with_sdmpc_state': 0, 'variants': {}, 'times': list(times)}
    for T in times:
        p = d / ('action_%06d.json' % T)
        if not p.is_file():
            continue
        m = json.loads(p.read_text(encoding='utf-8-sig')).get('metadata', {})
        rows['files'] += 1
        rows['with_sdmpc_state'] += int('sdmpc_state' in m)
        v = str(m.get('controller_variant'))
        rows['variants'][v] = rows['variants'].get(v, 0) + 1
    return rows


out = {k: scan(d, range(900, 9001, 150)) for k, d in ROBS.items()}
out.update({k: scan(d, (900, 1050, 2700, 4950)) for k, d in VA.items()})
for v in out.values():
    v['times'] = [min(v['times']), max(v['times']), len(v['times'])]
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(out))
