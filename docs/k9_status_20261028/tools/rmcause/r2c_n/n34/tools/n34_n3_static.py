# -*- coding: utf-8 -*-
"""N34 follow-up written AFTER reading n34_analysis.json (post hoc, descriptive): N3 decomposition with the static
1136 share 2/9 in place of the runtime gate_onramp_beta, because (A - S3_0)/G stayed 0.216-0.222 whether the runtime
beta was < 0.18 or > 0.26. Reads n34/out/n34_analysis.json, writes n34/out/n34_n3_static.json."""
import json
import os
import statistics as st

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
rows = json.load(open(os.path.join(OUT, 'n34_analysis.json'), encoding='utf-8'))['n3']['rows']
B = 2.0 / 9.0
PER = (('all', 900, 8550), ('900-1650', 900, 1650), ('1800-3450', 1800, 3450), ('3600-5250', 3600, 5250),
       ('5400-7050', 5400, 7050), ('7200-8550', 7200, 8550))
res = {}
for name, a, b in PER:
    sub = [r for r in rows if a <= r['T'] <= b]
    n = len(sub)
    s = lambda f: sum(f(r) for r in sub)
    A = s(lambda r: r['A_model']); E = s(lambda r: r['E_vis']); E3 = s(lambda r: r['E3_vis'])
    G = s(lambda r: r['G_model']); I = s(lambda r: r['I32_vis']); I3 = s(lambda r: r['I3_vis'])
    S0 = s(lambda r: r['S3_0_vis']); S1 = s(lambda r: r['S3_1_vis'])
    Rm = A - B * G
    res[name] = {
        'n_windows': n, 'A_model': A, 'E_vis_129_to_10490': E, 'E3_vis_route1136_3': E3, 'routeless_or_other_entries': E - E3,
        'G_model': G, 'I32_vis': I, 'I3_vis': I3, 'S3_0': S0, 'S3_1': S1,
        'ratio_A_E': A / E, 'ratio_G_I32': G / I, 'share_vis_I3_I32': I3 / I, 'ratio_static_share': B / (I3 / I),
        'd_total': A - E, 'd_gate': B * (G - I), 'd_share': B * I - I3, 'd_resid': Rm - (E - I3),
        'resid_model_minus_S3_0': Rm - S0, 'per_window_mean': {
            'A': A / n, 'E': E / n, 'S3_0': S0 / n, 'S3_1': S1 / n, 'd_total': (A - E) / n, 'd_resid': (Rm - (E - I3)) / n,
            'routeless': (E - E3) / n},
        'tt_median_s': st.median([r['tt_ins_to_10490_median_s'] for r in sub if r['tt_ins_to_10490_median_s'] is not None]),
        'tt_p90_of_window_medians_s': sorted([r['tt_ins_to_10490_median_s'] for r in sub if r['tt_ins_to_10490_median_s'] is not None])[int(0.9 * (n - 1))],
    }
json.dump(res, open(os.path.join(OUT, 'n34_n3_static.json'), 'w', encoding='utf-8'), indent=1)
for k, v in res.items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items() if a != 'per_window_mean'},
          {a: round(b, 2) for a, b in v['per_window_mean'].items()})
