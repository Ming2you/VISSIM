# -*- coding: utf-8 -*-
"""O4: per-movement inflow into SC1004_W_out (model, closest tangent record) vs VISSIM link-68 entries by
feeder connector, same windows [T, T+450]. Reads o1o4 outputs only. Writes o1o4/out/o4_wout.json."""
import json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS = ['va_s31', 'va_s41', 'va_s43', 'j1_s31r', 'j1_s41', 'j1_s43']
RAMPS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
MOV = {'E (SC1004_E_SC1005_to_W + E_SC107_to_W)': (('movement:SC1004_E_SC1005_to_W', 'movement:SC1004_E_SC107_to_W'), (10629, 52)),
       'N (SC1004_N_SC1003_to_W)': (('movement:SC1004_N_SC1003_to_W',), (10625, 46)),
       'S (SC1004_S_to_W)': (('movement:SC1004_S_to_W',), (10633,))}


def main():
    below_normal()
    acc = {k: {'model': [], 'vissim': [], 'ratio': []} for k in MOV}
    for tag in TAGS:
        M2 = json.load(open(os.path.join(BASE, 'model', 'model2_%s.json' % tag), encoding='utf-8'))
        SP = json.load(open(os.path.join(BASE, 'fzp', '%s_split.json' % tag), encoding='utf-8'))
        ent = SP['entries']['68']
        for rec in M2['records']:
            w0, w1 = rec['window']
            if w1 > 9000.0:
                continue
            dur = w1 - w0
            best, bd = None, None
            for td in rec['tds']:
                if any(td['pred_veh'].get(k) is None for k in RAMPS):
                    continue
                dd = sum(abs(td['pred_veh'][k] - rec['final_pred_veh'][k]) for k in RAMPS)
                if bd is None or dd < bd:
                    best, bd = td, dd
            if best is None:
                continue
            for name, (keys, prevs) in MOV.items():
                mval = sum(best['flows'].get(k, 0.0) for k in keys) * 3600.0 / dur
                vval = sum(1 for t, p in ent if w0 + 0.1 < t <= w1 + 0.1 and p in prevs) * 3600.0 / dur
                acc[name]['model'].append(mval)
                acc[name]['vissim'].append(vval)
                if vval:
                    acc[name]['ratio'].append(mval / vval)
    out = {k: {kk: {'n': len(vv), 'median': statistics.median(vv), 'min': min(vv), 'max': max(vv)} for kk, vv in v.items() if vv}
           for k, v in acc.items()}
    json.dump(out, open(os.path.join(BASE, 'out', 'o4_wout.json'), 'w', encoding='utf-8'), indent=1)
    for k, v in out.items():
        print(k, {kk: {a: round(b, 3) for a, b in vv.items()} for kk, vv in v.items()})


if __name__ == '__main__':
    main()
