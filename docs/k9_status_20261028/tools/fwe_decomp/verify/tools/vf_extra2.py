# -*- coding: utf-8 -*-
"""vf_extra2.py - VERIFY_FWE: meter GREEN vs merge level, per 900 s window, for every FW_E meter of B (x3) and codex joint.
Pinned 18:03 KST before the codex joint / NC reducer outputs existed (데이터 뒤 for the B part: chosen after P-B s31).
Question checked: where FWE_DECOMP / R3 say the merge "was released" (풀렸다), was the meter GREEN raised in that window,
or did the arm stay at its metered rate while the base (NC) merge fell?
Columns per window: merge diff (veh/h), arm level, base level, meter mean GREEN, share of cycles GREEN<10,
ramp stock diff of that meter (connector + approach, veh.h, bin form).
Usage: python -B vf_extra2.py <verify_dir>
"""
import hashlib
import json
import os
import sys

VD = sys.argv[1]
R = json.load(open(os.path.join(VD, 'out', 'VERIFY_NUMBERS.json'), encoding='utf-8'))
M = json.load(open(os.path.join(VD, 'out', 'meter.json'), encoding='utf-8'))
FZ = os.path.join(VD, 'out', 'fzp')
ONR = {'10639': '70', '10681': '68', '10490': '129', '10484': '31'}
X = {}
for pn, tag, a, b, nb in (('P-B|s31', 'B_s31', 'b_s31', 'nc_s31', 30), ('P-B|s41', 'B_s41', 'b_s41', 'nc_s41', 30),
                          ('P-B|s43', 'B_s43', 'b_s43', 'nc_s43', 30), ('Q-joint|s29', 'CXJ_s29', 'cxj_s29', 'cxnc_s29', 27)):
    p = R['pairs'].get(pn)
    if not isinstance(p, dict):
        continue
    da = json.load(open(os.path.join(FZ, a + '.json'))); db = json.load(open(os.path.join(FZ, b + '.json')))
    out = {}
    for c, f in ONR.items():
        win = M['runs'][tag]['meters'][c]['readback']['win900']
        rows = {}
        for w in p['merge_w900_vph'][c]:
            b0 = int(w) // 300
            st = sum(sum(da['b300_link'][l][b0:min(b0 + 3, nb)]) - sum(db['b300_link'][l][b0:min(b0 + 3, nb)]) for l in (c, f)) * 5 / 3600
            rows[w] = {'d': round(p['merge_w900_vph'][c][w]), 'arm': round(p['merge_arm_w900_vph'][c][w]), 'base': round(p['merge_base_w900_vph'][c][w]),
                       'g': (round(win[w]['mean_green'], 2) if w in win else None), 'tight': (round(win[w]['tight_frac'], 2) if w in win else None),
                       'stock_d': round(st, 2)}
        out[c] = rows
    X[pn] = out
X['inputs'] = {k: hashlib.sha256(open(os.path.join(VD, 'out', k), 'rb').read()).hexdigest() for k in ('VERIFY_NUMBERS.json', 'meter.json')}
X['tool_sha256'] = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
json.dump(X, open(os.path.join(VD, 'out', 'VERIFY_EXTRA2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for pn, v in X.items():
    if pn in ('inputs', 'tool_sha256'):
        continue
    for c, rows in v.items():
        print(pn, c, ' | '.join('%s:%+d(%d/%d) g%.1f t%.2f s%+.1f' % (w, r['d'], r['arm'], r['base'], r['g'] or -1, r['tight'] or -1, r['stock_d']) for w, r in rows.items()))
