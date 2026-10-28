# -*- coding: utf-8 -*-
"""N34: N4 per-meter per-green table from n34/out/n34_analysis.json blocks (definitions fixed in n34_analyze.py docstring).
Adds per-seed counts and vehicles per 10 s cycle. Writes n34/out/n34_n4_table.json."""
import json
import os
import statistics as st

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
B = json.load(open(os.path.join(OUT, 'n34_analysis.json'), encoding='utf-8'))['n4']['blocks']
TABLE = {2: 0.71, 3: 0.99, 4: 1.44, 5: 1.89, 6: 2.34, 7: 2.79, 8: 3.24, 9: 3.69, 10: 4.2}
LANES = {10639: 1, 10681: 2, 10490: 1, 10484: 1, 10480: 1, 10482: 2, 10646: 1, 10644: 1}
res = []
for m in (10639, 10681, 10490, 10484, 10480, 10482, 10646, 10644):
    for g in range(2, 11):
        for ln in range(1, LANES[m] + 1):
            for src in ('rm', 'va'):
                sub = [b for b in B if b['run'].startswith(src) and b['meter'] == m and b['green'] == g and b['lane'] == ln]
                if not sub:
                    continue
                pr = [b for b in sub if b['primary']]
                se = [b for b in sub if b['secondary']]
                tbl = 360.0 * TABLE[g]
                row = {'src': src, 'meter': m, 'green': g, 'lane': ln, 'n_blocks': len(sub),
                       'n_blocks_by_run': {r: sum(1 for b in sub if b['run'] == r) for r in sorted({b['run'] for b in sub})},
                       'n_primary': len(pr), 'primary_by_run': {r: sum(1 for b in pr if b['run'] == r) for r in sorted({b['run'] for b in pr})},
                       'n_secondary': len(se), 'n_queue30': sum(1 for b in sub if b['q_frames'] == 30),
                       'n_queue30_blocked': sum(1 for b in sub if b['q_frames'] == 30 and not b['B']),
                       'model_table_lane_veh_h': tbl, 'g90_lane_veh_h': 90.0 * g / LANES[m],
                       'all_median_veh_h': st.median([b['rate_lane'] for b in sub])}
                if pr:
                    v = [b['rate_lane'] for b in pr]
                    row.update(primary_median=st.median(v), primary_min=min(v), primary_max=max(v),
                               primary_veh_per_cycle=st.median(v) / 360.0, ratio_to_table=st.median(v) / tbl,
                               ratio_to_g90=st.median(v) / (90.0 * g / LANES[m]),
                               primary_blocks=[[b['run'], b['T'], int(b['cross'])] for b in pr])
                if se:
                    v = [b['rate_lane'] for b in se]
                    row.update(secondary_median=st.median(v), secondary_min=min(v), secondary_max=max(v))
                res.append(row)
json.dump(res, open(os.path.join(OUT, 'n34_n4_table.json'), 'w', encoding='utf-8'), indent=1)
for r in res:
    if r['n_primary'] or r['n_secondary'] or r['n_queue30']:
        print(r['src'], r['meter'], 'g', r['green'], 'lane', r['lane'], 'nb', r['n_blocks'], r['n_blocks_by_run'], 'prim', r['n_primary'], r['primary_by_run'],
              'med', r.get('primary_median'), '[', r.get('primary_min'), r.get('primary_max'), ']', 'vpc', r.get('primary_veh_per_cycle') and round(r['primary_veh_per_cycle'], 2),
              'tbl', round(r['model_table_lane_veh_h'], 1), 'ratio', r.get('ratio_to_table') and round(r['ratio_to_table'], 2),
              'g90r', r.get('ratio_to_g90') and round(r['ratio_to_g90'], 2), 'sec', r['n_secondary'], r.get('secondary_median'),
              'q30', r['n_queue30'], 'q30blk', r['n_queue30_blocked'], 'allmed', r['all_median_veh_h'])
