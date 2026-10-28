# -*- coding: utf-8 -*-
"""vf_extra.py - VERIFY_FWE extra claim checks on vf_compare / vf_meter outputs (light; no FZP).
Written and pinned at 18:0x KST AFTER the first vf_compare run on P-B v3c3-s31 (label: 데이터 뒤 for the check list,
the numbers come from the same pinned reducers). Claims checked (FWE_DECOMP.md r1 line refs):
  X1 :107  Q-joint ① 900 s windows 2,700-6,300 s = -49.2/-73.7/-81.6/-37.6 (sum -242.1), link 2 900-end -261.0
  X2 :28/:179  V-A 10639 merge diff within +-48 veh/h (900-9000, three seeds)
  X3 :26  "merge actually held mainly at 10639": B per-meter merge diffs 1,800-3,600 s
  X4 :30/:165/:176  windows where B 10639 merge diff > 0: meter mean GREEN / tight share in the same window, arm and NC level
  X5 :177  V-A s41 M diff 1,800-4,500 s = -7.9/-2.7/-0.2
  X6 :178  cell 5-9 900-end per arm (s41: V-A -63.1, B -63.4, VSL -50.0, J1 -63.0; s43: -13.0, -12.9, -11.5)
  X7 :29   B - V-A B1+B2 share in 1,800-3,600 s vs 900-end
  X8 :194  V-A merge diffs of all four meters within +-116 veh/h
Usage: python -B vf_extra.py <verify_dir>
"""
import hashlib
import json
import os
import sys

VD = sys.argv[1]
R = json.load(open(os.path.join(VD, 'out', 'VERIFY_NUMBERS.json'), encoding='utf-8'))
M = json.load(open(os.path.join(VD, 'out', 'meter.json'), encoding='utf-8'))
P = R['pairs']
X = {}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


q = P.get('Q-joint|s29')
if isinstance(q, dict):
    X['X1_d1_w900'] = {w: round(v, 2) for w, v in q['d1_w900'].items()}
    X['X1_sum_2700_6300'] = round(sum(q['d1_w900'][w] for w in ('2700', '3600', '4500', '5400')), 2)
    fz = os.path.join(VD, 'out', 'fzp')
    a = json.load(open(os.path.join(fz, 'cxj_s29.json'))); b = json.load(open(os.path.join(fz, 'cxnc_s29.json')))
    X['X1_link2_900_end'] = round((sum(a['b300_link']['2'][3:27]) - sum(b['b300_link']['2'][3:27])) * 5 / 3600, 2)
X['X2_VA_10639_maxabs'] = {}
X['X8_VA_all_maxabs'] = {}
for s in ('s31', 's41', 's43'):
    p = P['P-VA|' + s]
    X['X2_VA_10639_maxabs'][s] = max(abs(v) for v in p['merge_w900_vph']['10639'].values())
    X['X8_VA_all_maxabs'][s] = {c: max(abs(v) for v in p['merge_w900_vph'][c].values()) for c in p['merge_w900_vph']}
X['X3_B_merge_1800_3600'] = {s: {c: [round(P['P-B|' + s]['merge_w900_vph'][c][w]) for w in ('1800', '2700')] for c in ('10639', '10681', '10490', '10484')}
                             for s in ('s31', 's41', 's43')}
X['X4'] = {}
for pn, tag in (('P-B|s31', 'B_s31'), ('P-B|s41', 'B_s41'), ('P-B|s43', 'B_s43')):
    p = P[pn]; win = M['runs'][tag]['meters']['10639']['readback']['win900']
    X['X4'][pn] = {w: {'merge_diff': round(p['merge_w900_vph']['10639'][w]), 'arm': round(p['merge_arm_w900_vph']['10639'][w]),
                       'nc': round(p['merge_base_w900_vph']['10639'][w]), 'mean_green': round(win[w]['mean_green'], 2),
                       'tight_frac': round(win[w]['tight_frac'], 2), 'stock10639_like': None}
                   for w in p['merge_w900_vph']['10639'] if w in win}
X['X5_VA_s41_M'] = {w: round(P['P-VA|s41']['zone_w900']['M'][w], 2) for w in ('1800', '2700', '3600')}
X['X6_cell59'] = {k: round(v['cell59_center_900_end'], 2) for k, v in P.items() if isinstance(v, dict)}
X['X6_cell59_exact'] = {k: round(v['cell59_exact_900_end'], 2) for k, v in P.items() if isinstance(v, dict)}
X['X7'] = {}
for s in ('s31', 's41', 's43'):
    p = P['P-BVA|' + s]
    w = {k: p['zone_w900']['B1'][k] + p['zone_w900']['B2'][k] for k in p['zone_w900']['B1']}
    X['X7'][s] = {'w900': {k: round(v, 2) for k, v in w.items()}, 'sum_1800_3600': round(w['1800'] + w['2700'], 2),
                  'sum_1800_4500': round(w['1800'] + w['2700'] + w['3600'], 2), 'total_900_end': round(sum(w.values()), 2)}
X['inputs'] = {'VERIFY_NUMBERS.json': sha(os.path.join(VD, 'out', 'VERIFY_NUMBERS.json')), 'meter.json': sha(os.path.join(VD, 'out', 'meter.json'))}
X['tool_sha256'] = sha(os.path.abspath(__file__))
json.dump(X, open(os.path.join(VD, 'out', 'VERIFY_EXTRA.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(X, ensure_ascii=False, indent=0)[:6000])
