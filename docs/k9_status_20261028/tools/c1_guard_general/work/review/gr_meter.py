# -*- coding: utf-8 -*-
"""gr_meter.py — review add-on (2026-10-27 KST, data after, read-only, light): FW_E/FW_W meter trigger counts
under U for (a) pre-head lane only (r0 GG6 (가)) and (b) pre-head AND its approach lane both F (spill reached
the approach link; option (라)). Inputs: <run>.npz + segments.json only. Usage: python -B gr_meter.py <scan_dir> <out.json>"""
import hashlib, json, os, sys
import numpy as np
RUNS = ['%s_%s' % (a, s) for a in ['NC3', 'VSL', 'VA', 'B'] for s in ['s31', 's41', 's43']]
DEC = list(range(900, 8851, 150))
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
scan, out = sys.argv[1:3]
seg = json.loads(open(os.path.join(scan, 'segments.json'), 'rb').read().decode('utf-8'))['segments']
L = np.array([s['to_m'] - s['from_m'] for s in seg]); cap6 = L / 6.0
meters = sorted({s['meter'] for s in seg if s['kind'] in ('meter_prehead_lane', 'meter_approach_lane')})
road = {s['meter']: s['road'] for s in seg if 'meter' in s}
res = dict(tool_sha256=sha(__file__), segments_sha256=sha(os.path.join(scan, 'segments.json')), runs={})
for run in RUNS:
    z = np.load(os.path.join(scan, run + '.npz')); times = z['times']
    tix = {round(float(t), 1): k for k, t in enumerate(times)}
    Fi = np.array([tix[round(T + 0.1, 1)] for T in DEC])
    SP = ((z['flg'] & 2) > 0)[:, Fi]
    F = (z['cnt'].astype(float)[:, Fi] / cap6[:, None] >= 1.0 - 1e-9) | SP
    r = {}
    for m in meters:
        M = [i for i, s in enumerate(seg) if s.get('meter') == m and s['kind'] == 'meter_prehead_lane' and cap6[i] >= 2]
        A = [i for i, s in enumerate(seg) if s.get('meter') == m and s['kind'] == 'meter_approach_lane' and cap6[i] >= 2]
        fm = F[M].any(0) if M else np.zeros(len(DEC), bool)
        fa = F[A].any(0) if A else np.zeros(len(DEC), bool)
        r[m] = dict(road=road[m], prehead=int(fm.sum()), prehead_and_approach=int((fm & fa).sum()),
                    first_prehead=(DEC[int(np.argmax(fm))] if fm.any() else None),
                    first_both=(DEC[int(np.argmax(fm & fa))] if (fm & fa).any() else None))
    res['runs'][run] = r
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, sort_keys=True)
print(sha(out))
