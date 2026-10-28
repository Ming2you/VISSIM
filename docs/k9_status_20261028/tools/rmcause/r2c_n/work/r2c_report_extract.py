"""Report helper (read only): pulls numbers already computed by r2c_metrics.py (out/r2c_metrics.json, r2c_bins300.csv,
r2c_zone300.csv) plus event counts from the two R1 run folders, for R2C_RESULT.md.  No new metric definitions:
2-seed means (PRE sec.4) and restricting-decision spans from the green strings only."""
import csv, io, json, os, sys
from collections import Counter
sys.dont_write_bytecode = True
R2C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(R2C, 'out')
m = json.load(io.open(os.path.join(OUT, 'r2c_metrics.json'), encoding='utf-8'))
res = {}
# 2-seed means of the window table rows
rows = ['M1', 'meterbound_FWE', 'meterbound:RM_C10681', 'onramp_FWE', 'onramp:RM_C10681', 'M2', 'fw_w_main',
        'unins_1099', 'unins_1098', 'M3', 'M3u', 'offramp', 'M4a', 'M4b', 'M4', 'OUT_a', 'OUT_b', 'meterbound_FWW']
res['mean2'] = {pk: {w: {k: round((m['pairs'][pk]['windows']['31'][k][w] + m['pairs'][pk]['windows']['41'][k][w]) / 2, 2)
                         for k in rows} for w in ('early_2700_4500', 'late_6300_8100', 'whole_900_9000')}
                for pk in m['pairs']}
# green strings -> restricting spans
def span(g):
    idx = [i for i, c in enumerate(g) if c != 'A']
    if not idx:
        return None
    return {'n': len(idx), 'first_T': 900 + 150 * idx[0], 'last_T': 900 + 150 * idx[-1],
            'min_g': min(int(g[i]) for i in idx),
            'late_6300_8100': g[36:48], 'early_2700_4500': g[12:24]}
res['spans'] = {}
for s in ('31', '41'):
    v = m['meters'][s]
    res['spans'][s] = {'r1_RM_C10681': span(v['RM_C10681_green_r1']), 'rm_RM_C10681': span(v['RM_C10681_green_rm']),
                       'r1_restricting': v['r1']['restricting_decisions'], 'rm_restricting': v['rm']['restricting_decisions'],
                       'rm_green_strings': v['rm']['green_string'], 'r1_meter_sets': v['r1']['decision_meter_sets'],
                       'r1_first_red': v['r1']['first_red_sec_by_sc'], 'rm_first_red': v['rm']['first_red_sec_by_sc'],
                       'r1_fixed_validation': v['r1']['fixed_validation'], 'r1_run_json': v['r1']['run_json']}
# event counts in R1 run folders
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
res['events'] = {}
for s in (31, 41):
    rd = os.path.join(ROOT, 's%d_v3c3rm10681' % s, 'run')
    c = Counter()
    with io.open(os.path.join(rd, 'fixed_events.csv'), encoding='ascii') as f:
        for r in csv.DictReader(f):
            c['%s|%s|%s' % (r['kind'], r['no'], r['value'])] += 1
    re_ = io.open(os.path.join(rd, 'rule_events.csv'), encoding='ascii').read().strip().splitlines()
    res['events'][str(s)] = {'fixed_events': dict(c), 'rule_events_lines': re_}
# 300 s bins, M1 and 10681 rows
b = list(csv.reader(io.open(os.path.join(OUT, 'r2c_bins300.csv'), encoding='utf-8')))
hdr, data = b[0], b[1:]
def col(pk, s, k):
    j = hdr.index('%s|s%s|%s' % (pk, s, k))
    return [float(r[j]) for r in data]
res['bins300_t'] = [int(r[0]) for r in data]
res['bins300'] = {k: {'%s|%s' % (pk, s): col(pk, s, k) for pk in ('R1-NC3', 'RM-NC3', 'VA-NC3', 'R1-RM', 'R1-VA')
                      for s in ('31', '41')} for k in ('M1', 'meterbound:RM_C10681', 'onramp:RM_C10681', 'unins_1099', 'M4')}
z = list(csv.reader(io.open(os.path.join(OUT, 'r2c_zone300.csv'), encoding='utf-8')))
zh, zd = z[0], z[1:]
res['zone300'] = {h: [r[j] for r in zd] for j, h in enumerate(zh) if j > 0 and ('seg5' in h or 'seg10' in h)}
json.dump(res, io.open(os.path.join(R2C, 'work', 'r2c_report_extract.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('ok')
