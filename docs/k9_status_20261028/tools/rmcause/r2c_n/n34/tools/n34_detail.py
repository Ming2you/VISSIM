# -*- coding: utf-8 -*-
"""N34 follow-up (read-only): details from n34/out/n34_analysis.json and scan JSONs. Prints only."""
import collections
import json
import os
import statistics as st

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
A = json.load(open(os.path.join(OUT, 'n34_analysis.json'), encoding='utf-8'))
rows = A['n3']['rows']


def med(x):
    x = [v for v in x if v is not None]
    return round(st.median(x), 2) if x else None


def mean(x):
    x = [v for v in x if v is not None]
    return round(sum(x) / len(x), 2) if x else None


def ssum(rs, k):
    return sum(r[k] for r in rs)


print('R_m - S3_0: median', med([r['resid_model'] - r['S3_0_vis'] for r in rows]), 'mean', mean([r['resid_model'] - r['S3_0_vis'] for r in rows]))
print('S3_0 obsframe - FZP: median', med([r['init3_obsframe'] - r['S3_0_vis'] for r in rows]),
      'max abs', max(abs(r['init3_obsframe'] - r['S3_0_vis']) for r in rows))
print('E - E3 mean', mean([r['E_vis'] - r['E3_vis'] for r in rows]), 'S0-S1 mean', mean([r['S3_0_vis'] - r['S3_1_vis'] for r in rows]))
print('v10490_far / (FZP prev150 entries*24): median', med([r['v10490_far'] / (r['E_prev150_vis'] * 24.0) for r in rows if r['E_prev150_vis']]))
print('beta / FZP prev150 share I3/I32: median', med([r['beta_onE'] / (r['I3_prev150_vis'] / r['I32_prev150_vis']) for r in rows if r['I3_prev150_vis']]))
print('gate_v_implied / (G/450*3600): median', med([r['gate_v_implied'] / (r['G_model'] / 450.0 * 3600.0) for r in rows]))
est = [(r['I3_vis'] / 450.0) * (r['tt_ins_to_10490_median_s'] - 34.0) for r in rows if r['tt_ins_to_10490_median_s'] is not None]
print('pipeline estimate q3*(tt-34): mean', mean(est), 'median', med(est), '| d_total mean', mean([r['d_total'] for r in rows]),
      'd_resid mean', mean([r['d_resid'] for r in rows]))
print('sum A / sum E', round(ssum(rows, 'A_model') / ssum(rows, 'E_vis'), 3))
print('sum betaG / sum I3', round(sum(r['beta_onE'] * r['G_model'] for r in rows) / ssum(rows, 'I3_vis'), 3),
      'sum G / sum I32', round(ssum(rows, 'G_model') / ssum(rows, 'I32_vis'), 3))
print('sum resid_m', round(ssum(rows, 'resid_model'), 1), 'sum S3_0', ssum(rows, 'S3_0_vis'), 'sum S3_1', ssum(rows, 'S3_1_vis'),
      'sum resid_vis', ssum(rows, 'resid_vis'), 'n', len(rows))
print('sum A-E', round(ssum(rows, 'd_total'), 1), 'sum d_new', round(ssum(rows, 'd_new'), 1), 'sum d_new_gate', round(ssum(rows, 'd_new_gate'), 1),
      'sum d_new_share', round(ssum(rows, 'd_new_share'), 1), 'sum d_resid', round(ssum(rows, 'd_resid'), 1), 'sum A', round(ssum(rows, 'A_model'), 1), 'sum E', ssum(rows, 'E_vis'))
print()
for name, a, b in (('900-1650', 900, 1650), ('1800-3450', 1800, 3450), ('3600-5250', 3600, 5250), ('5400-7050', 5400, 7050), ('7200-8550', 7200, 8550)):
    sub = [r for r in rows if a <= r['T'] <= b]
    print(name, 'n', len(sub), 'A/E', round(ssum(sub, 'A_model') / ssum(sub, 'E_vis'), 3),
          'A', mean([r['A_model'] for r in sub]), 'E', mean([r['E_vis'] for r in sub]), 'G/I', round(ssum(sub, 'G_model') / ssum(sub, 'I32_vis'), 3),
          'bG/I3', round(sum(r['beta_onE'] * r['G_model'] for r in sub) / ssum(sub, 'I3_vis'), 3),
          'Rm', mean([r['resid_model'] for r in sub]), 'S0', mean([r['S3_0_vis'] for r in sub]), 'S1', mean([r['S3_1_vis'] for r in sub]),
          'dtot', mean([r['d_total'] for r in sub]), 'dnew', mean([r['d_new'] for r in sub]), 'dres', mean([r['d_resid'] for r in sub]),
          'tt', med([r['tt_ins_to_10490_median_s'] for r in sub]), 'slow_r3', mean([r['slow_r3_mean_vis'] for r in sub]),
          'slow_r1_32', mean([r['slow_r1_on32_mean_vis'] for r in sub]), 'beta', mean([r['beta_onE'] for r in sub]),
          'betatot', mean([r['beta_total'] for r in sub]), 'L10491', mean([r['L10491_129_vis'] for r in sub]),
          'onW A/M', mean([r['A_onW_model'] for r in sub]), mean([r['M_onW_model'] for r in sub]), 'E10482', mean([r['E10482_vis'] for r in sub]),
          'r1132_129', mean([r['r1132_on129_mean'] for r in sub]), 'slow129', mean([r['slow129_all_mean'] for r in sub]))
for t in ('va_s31', 'va_s41', 'va_s43'):
    sub = [r for r in rows if r['run'] == t]
    print(t, 'A/E sum', round(ssum(sub, 'A_model') / ssum(sub, 'E_vis'), 3), 'median ratio', med([r['ratio_A_E'] for r in sub]),
          'd_total mean', mean([r['d_total'] for r in sub]), 'd_new', mean([r['d_new'] for r in sub]), 'd_resid', mean([r['d_resid'] for r in sub]),
          'Rm', mean([r['resid_model'] for r in sub]), 'S0', mean([r['S3_0_vis'] for r in sub]), 'S1', mean([r['S3_1_vis'] for r in sub]),
          'tt', med([r['tt_ins_to_10490_median_s'] for r in sub]))
for t in ('va_s31', 'va_s41', 'va_s43', 'rm_s41'):
    S = json.load(open(os.path.join(OUT, 'scan_%s.json' % t), encoding='utf-8'))
    c, c2, c3 = collections.Counter(), collections.Counter(), collections.Counter()
    for k, a, b, tg, n in S['trans']:
        if b == 10490:
            c[(a, tg)] += n
        if a == 129:
            c2[(b, tg)] += n
        if a == 32:
            c3[(b, tg)] += n
    tags = collections.Counter(v[1] for v in S['veh32'])
    print(t, 'into10490', dict(c), '| from129', dict(c2), '| from32', dict(c3), '| veh32 tags', dict(tags), 'ins32', sum(S['ins32'].values()))
print()
B = A['n4']['blocks']
for key in sorted(A['n4']['table']):
    t = A['n4']['table'][key]
    if t['primary'] or t['secondary']:
        print(key, 'by lane', {ln: (v['n'], v['median'], v['min'], v['max']) for ln, v in t['primary_by_lane'].items()}, 'runs', t['primary_runs'],
              'secondary', t['secondary'] and (t['secondary']['n'], t['secondary']['median'], t['secondary']['min'], t['secondary']['max']))
for m in (10490, 10484, 10681, 10639):
    for run in ('rm_s31', 'rm_s41'):
        pr = [(b['T'], b['lane'], b['green'], int(b['cross'])) for b in B if b['run'] == run and b['meter'] == m and b['primary']]
        print(run, m, 'primary (T,lane,g,veh/150s):', pr)
for m in (10639, 10681, 10490, 10484):
    for g in range(2, 11):
        for ln in (1, 2):
            sub = [b for b in B if b['run'].startswith('rm') and b['meter'] == m and b['green'] == g and b['lane'] == ln]
            if not sub:
                continue
            print('qf', m, 'g', g, 'lane', ln, 'n', len(sub), 'q30', sum(1 for b in sub if b['q_frames'] == 30), 'q24', sum(1 for b in sub if b['q_frames'] >= 24),
                  'B', sum(1 for b in sub if b['B']), 'med_qf', st.median([b['q_frames'] for b in sub]), 'all_med_rate', st.median([b['rate_lane'] for b in sub]),
                  'pre', round(st.mean([b['pre_mean'] for b in sub]), 1), 'post_slow', round(st.mean([b['post_slow_mean'] for b in sub]), 1),
                  'store', round(sub[0]['post_store'], 1))
for m in (10480, 10482, 10646, 10644, 10639, 10681, 10490, 10484):
    for src in ('rm', 'va'):
        sub = [b for b in B if b['run'].startswith(src) and b['meter'] == m and b['green'] == 10]
        if sub:
            print('g10', src, m, 'n', len(sub), 'q30', sum(1 for b in sub if b['q_frames'] == 30), 'q24', sum(1 for b in sub if b['q_frames'] >= 24),
                  'max_qf', max(b['q_frames'] for b in sub), 'max_rate', max(b['rate_lane'] for b in sub), 'med_rate', st.median([b['rate_lane'] for b in sub]),
                  'max pre', round(max(b['pre_mean'] for b in sub), 1))
