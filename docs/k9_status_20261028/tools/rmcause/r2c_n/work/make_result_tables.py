"""Builds the table blocks of R2C_RESULT.md from out/r2c_metrics.json, out/r2c_zone300.csv (read only).
Writes work/result_tables.md.  Same numbers and formatting as r2c_tables.md (%+.1f); no new metric."""
import csv, io, json, os, sys
sys.dont_write_bytecode = True
R2C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = json.load(io.open(os.path.join(R2C, 'out', 'r2c_metrics.json'), encoding='utf-8'))
PK = ('R1-NC3', 'RM-NC3', 'VA-NC3', 'R1-RM', 'R1-VA')
ROWS = (('M1', '**① FW_E 본선 7링크 (주 지표)**'), ('meterbound_FWE', 'FW_E 미터 대기 4개 합'),
        ('meterbound:RM_C10681', '  그중 RM_C10681 미터 대기'), ('onramp_FWE', 'FW_E 램프 구역 4개 합'),
        ('onramp:RM_C10681', '  그중 RM_C10681 램프 구역'), ('M2', '② 동측 국소 19링크'),
        ('fw_w_main', 'FW_W 본선'), ('unins_1099', '입력 1099 미삽입 (FW_W 머리)'),
        ('unins_1098', '입력 1098 미삽입 (FW_E 머리)'), ('M3', '③ Ω 635링크'), ('M3u', '③u Ω 안 도시'),
        ('offramp', '진출 램프 구역'), ('M4a', '④a 전체 링크'), ('M4b', '④b 미삽입 (UR2)'),
        ('M4', '**④ 전체 + 미삽입**'), ('OUT_a', '**Ω 밖 (a) = ④ − ③**'), ('OUT_b', 'Ω 밖 (b) = ④a − ③'),
        ('meterbound_FWW', 'FW_W 미터 대기 4개 합'))
L = []


def win_table(w):
    L.append('| 줄 | ' + ' | '.join('%s s%s' % (pk.replace('-', ' − '), s) for pk in PK for s in ('31', '41')) + ' |')
    L.append('|---|' + '---:|' * 10)
    for k, name in ROWS:
        L.append('| %s | %s |' % (name, ' | '.join('%+.1f' % m['pairs'][pk]['windows'][s][k][w] for pk in PK
                                                   for s in ('31', '41'))))
    L.append('')
    L.append('같은 창 NC3 ① 수준: s31 %.1f, s41 %.1f veh·h. 같은 창 R1 ① 수준: s31 %.1f, s41 %.1f veh·h.' % (
        m['pairs']['R1-NC3']['base_windows']['31']['M1'][w], m['pairs']['R1-NC3']['base_windows']['41']['M1'][w],
        m['pairs']['R1-NC3']['arm_windows']['31']['M1'][w], m['pairs']['R1-NC3']['arm_windows']['41']['M1'][w]))
    L.append('')


for w, title in (('late_6300_8100', '늦은 창 6,300–8,100 s'), ('early_2700_4500', '이른 창 2,700–4,500 s'),
                 ('whole_900_9000', '전체 900–9,000 s')):
    L.append('@@TABLE %s' % w)
    win_table(w)

# meter share
L.append('@@TABLE share')
L.append('| 시드 | 창 | a = R1 − NC3 | b = RM − NC3 | c = V-A − NC3 | a − b (= R1 − RM) | a − c (= R1 − V-A) | a / b | a / c |')
L.append('|---|---|---:|---:|---:|---:|---:|---:|---:|')
for s in ('31', '41'):
    for w, wn in (('early_2700_4500', '이른 2,700–4,500'), ('late_6300_8100', '늦은 6,300–8,100'),
                  ('whole_900_9000', '전체 900–9,000')):
        r = m['meter_share_M1'][s][w]
        f = lambda x: '비움' if x is None else '%+.2f' % x
        L.append('| s%s | %s | %+.2f | %+.2f | %+.2f | %+.2f | %+.2f | %s | %s |' % (
            s, wn, r['M1_R1-NC3'], r['M1_RM-NC3'], r['M1_VA-NC3'], r['M1_R1-RM'], r['M1_R1-VA'],
            f(r['ratio_(R1-NC3)/(RM-NC3)']), f(r['ratio_(R1-NC3)/(VA-NC3)'])))
L.append('')

# 300 s bins, M1 all pairs
T = m['bins300_start_sec']
L.append('@@TABLE bins_M1')
L.append('| 칸 시작 (s) | ' + ' | '.join('%s s%s' % (pk.replace('-', ' − '), s) for pk in PK for s in ('31', '41')) + ' |')
L.append('|---:|' + '---:|' * 10)
for j, t in enumerate(T):
    L.append('| %d | %s |' % (t, ' | '.join('%+.1f' % m['pairs'][pk]['bins300'][s]['M1'][j] for pk in PK for s in ('31', '41'))))
L.append('')

# 300 s bins, shifted waiting next to M1, per seed
for s in ('31', '41'):
    L.append('@@TABLE bins_shift_s%s' % s)
    cols = (('R1-NC3', 'M1', '① R1−NC3'), ('RM-NC3', 'M1', '① RM−NC3'), ('VA-NC3', 'M1', '① VA−NC3'),
            ('R1-NC3', 'meterbound:RM_C10681', '10681 대기 R1−NC3'), ('RM-NC3', 'meterbound:RM_C10681', '10681 대기 RM−NC3'),
            ('R1-NC3', 'fw_w_main', 'FW_W 본선 R1−NC3'), ('RM-NC3', 'fw_w_main', 'FW_W 본선 RM−NC3'),
            ('R1-NC3', 'unins_1099', '1099 R1−NC3'), ('RM-NC3', 'unins_1099', '1099 RM−NC3'),
            ('R1-NC3', 'M4', '④ R1−NC3'), ('RM-NC3', 'M4', '④ RM−NC3'),
            ('R1-NC3', 'OUT_a', 'Ω 밖 (a) R1−NC3'), ('RM-NC3', 'OUT_a', 'Ω 밖 (a) RM−NC3'))
    L.append('| 칸 시작 (s) | ' + ' | '.join(c[2] for c in cols) + ' |')
    L.append('|---:|' + '---:|' * len(cols))
    for j, t in enumerate(T):
        L.append('| %d | %s |' % (t, ' | '.join('%+.1f' % m['pairs'][pk]['bins300'][s][k][j] for pk, k, _ in cols)))
    L.append('')

# zone speeds + 10681 greens per 300 s bin
z = list(csv.reader(io.open(os.path.join(R2C, 'out', 'r2c_zone300.csv'), encoding='utf-8')))
zh, zd = z[0], z[1:]
for s in ('31', '41'):
    L.append('@@TABLE zone_s%s' % s)
    g1 = m['meters'][s]['RM_C10681_green_r1']
    g0 = m['meters'][s]['RM_C10681_green_rm']
    arms = ('nc3', 'r1', 'rm', 'va')
    L.append('| 칸 시작 (s) | g10681 R1 | g10681 RM | seg5 NC3 | seg5 R1 | seg5 RM | seg5 V-A | seg10 NC3 | seg10 R1 | seg10 RM | seg10 V-A |')
    L.append('|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|')
    for j, t in enumerate(T):
        i = (t - 900) // 150
        vals = []
        for seg in ('FW_E__seg5', 'FW_E__seg10'):
            for a in arms:
                vals.append(zd[j][zh.index('%s_s%s|%s' % (a, s, seg))] or '—')
        L.append('| %d | %s | %s | %s |' % (t, g1[i:i + 2], g0[i:i + 2], ' | '.join(vals)))
    L.append('')

# 2-seed means
L.append('@@TABLE mean2')
keys = (('M1', '①'), ('meterbound:RM_C10681', '10681 대기'), ('fw_w_main', 'FW_W 본선'), ('unins_1099', '1099 미삽입'),
        ('M3', '③ Ω'), ('M4', '④'), ('OUT_a', 'Ω 밖 (a)'))
L.append('| 비교 | 창 | ' + ' | '.join(n for _, n in keys) + ' |')
L.append('|---|---|' + '---:|' * len(keys))
for pk in PK:
    for w, wn in (('early_2700_4500', '이른'), ('late_6300_8100', '늦은'), ('whole_900_9000', '전체')):
        L.append('| %s | %s | %s |' % (pk.replace('-', ' − '), wn, ' | '.join(
            '%+.1f' % ((m['pairs'][pk]['windows']['31'][k][w] + m['pairs'][pk]['windows']['41'][k][w]) / 2) for k, _ in keys)))
L.append('')
io.open(os.path.join(R2C, 'work', 'result_tables.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
print('ok', len(L))
