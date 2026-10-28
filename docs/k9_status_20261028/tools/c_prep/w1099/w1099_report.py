# w1099_report.py — w1099_scan 출력 9개 + B·V-A 명령 CSV → 표 (W1099_RULE.md, 데이터 뒤 선언; 읽기만, 가벼움)
# 출력: out/report_tables.md, out/report.json
import os, json, csv, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
VB = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/verify_b/out'
SEEDS = (31, 41, 43)
ARMS = ('b', 'nc', 'va')
ACT = {
    ('b', 31): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/action_sdmpc31_sdmpc9000_s31.csv',
    ('b', 41): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/action_sdmpc31_sdmpc9000_s41.csv',
    ('b', 43): 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/action_sdmpc31_sdmpc9000_s43.csv',
    ('va', 31): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/action_sdmpc31_v3c3_k92va_s31.csv',
    ('va', 41): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/action_sdmpc31_v3c3_k92va_s41.csv',
    ('va', 43): 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/action_sdmpc31_v3c3_k92va_s43.csv',
}
NTB = 30
R = {}
for a in ARMS:
    for s in SEEDS:
        R[(a, s)] = json.load(open(os.path.join(OUT, '%s%d.json' % (a, s)), encoding='utf-8'))
md = []
rep = {}


def A(x):
    return np.asarray(x, dtype=float)


def f1(x):
    return '%+.1f' % x if abs(x) >= 0.05 else ('±0.0' if x == 0 else '%+.2f' % x)


def lv(x):
    return '%.1f' % x


def tbl(head, rows):
    md.append('| ' + ' | '.join(head) + ' |')
    md.append('|' + '|'.join(['---'] + ['---:'] * (len(head) - 1)) + '|')
    for r in rows:
        md.append('| ' + ' | '.join(str(c) for c in r) + ' |')
    md.append('')


PAIRS = (('b', 'nc', 'B − NC3'), ('va', 'nc', 'V-A − NC3'), ('b', 'va', 'B − V-A'))
B900 = [(0, 900), (900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 5400), (5400, 6300), (6300, 7200), (7200, 8100), (8100, 9000)]


def to900(v):
    v = A(v)
    return [float(v[3 * k:3 * k + 3].sum()) for k in range(10)]


# ---------------- checks ----------------
md.append('## 점검')
chk = {}
for a in ARMS:
    for s in SEEDS:
        vb = json.load(open(os.path.join(VB, '%s%d.json' % (a, s)), encoding='utf-8'))
        S_vb = vb['first_seen']['9000']['S_in1099']; n_vb = vb['first_seen']['9000']['n_in1099']
        S_me = R[(a, s)]['in1099']['S_W']; S_bins = sum(R[(a, s)]['in1099']['S_bins'])
        chk['%s%d' % (a, s)] = {'S_vb': S_vb, 'S_me': S_me, 'S_bins_sum': S_bins, 'n_vb': n_vb,
                                'n_me': R[(a, s)]['in1099']['n_first_le_W'],
                                'l26_total': R[(a, s)]['links']['26']['total'],
                                'l26_map_sum': float(A(R[(a, s)]['l26_occ']).sum())}
l26 = json.load(open(os.path.join(VB, 'link26.json'), encoding='utf-8'))
for k in ('b31', 'nc31', 'b41', 'nc41'):
    chk[k]['l26_vb'] = l26[k]['26']['total']
rows = []
for k, v in chk.items():
    rows.append([k, '%.3f' % v['S_vb'], '%.3f' % v['S_me'], '%.3f' % v['S_bins_sum'], v['n_vb'], v['n_me'], '%.3f' % v['l26_total'],
                 '%.3f' % v['l26_map_sum'], ('%.3f' % v['l26_vb']) if 'l26_vb' in v else '–'])
tbl(['런', 'S_1099 vb_scan', 'S_1099 이 도구', '300 s 칸 합', '수 vb', '수 이 도구', '링크 26 체류', '링크 26 지도 합', '링크 26 link26.json'], rows)
rep['checks'] = chk

# ---------------- T1: d4b 1099 by 900 s ----------------
md.append('## T1 ④b 중 입력 1099, 첫 관측 차분을 900 s 칸으로 (veh·h)')
t1 = {}
for x, y, lab in PAIRS:
    for s in SEEDS:
        d = A(R[(y, s)]['in1099']['S_bins']) - A(R[(x, s)]['in1099']['S_bins'])
        t1['%s|%d' % (lab, s)] = {'bins900': to900(d), 'sum': float(d.sum())}
rows = []
for lab in [p[2] for p in PAIRS]:
    for s in SEEDS:
        v = t1['%s|%d' % (lab, s)]
        rows.append([lab + ' v3c3-s%d' % s] + [f1(z) for z in v['bins900']] + [f1(v['sum'])])
tbl(['짝'] + ['%d–%d' % b for b in B900] + ['합'], rows)
rep['T1'] = t1

# cumulative insertion count gap at 900 s marks (vehicles): N_y(t) - N_x(t) = backlog of x minus backlog of y
md.append('## T1b 넣은 1099 차 누적 수의 차 (y − x, 대), 900 s 끝마다 — 같은 도착열 가정에서 x 의 남은 대기 차 수 − y 의')
rows = []
t1b = {}
for x, y, lab in PAIRS:
    for s in SEEDS:
        nx = np.cumsum(A(R[(x, s)]['entrance']['n_ins_bin'])); ny = np.cumsum(A(R[(y, s)]['entrance']['n_ins_bin']))
        g = (ny - nx)[2::3]
        t1b['%s|%d' % (lab, s)] = g.tolist()
        rows.append([lab + ' v3c3-s%d' % s] + ['%+d' % z for z in g])
tbl(['짝'] + ['≤%d' % b[1] for b in B900], rows)
rep['T1b'] = t1b

# ---------------- T2: entrance ----------------
md.append('## T2 입구(링크 26 첫 관측): 900 s 칸별 넣은 수 · 새 차 0 인 5 s 프레임 수 · 가장 긴 0 연속(s) · 첫 속도 평균(km/h)')
t2 = {}
rows = []
for s in SEEDS:
    for a in ARMS:
        e = R[(a, s)]['entrance']
        n = to900(e['n_ins_bin']); z = to900(e['zero_frames_bin'])
        lz = [max(e['longest_zero_run_frames_bin'][3 * k:3 * k + 3]) * 5 for k in range(10)]
        sp = to900(e['first_speed_sum_bin'])
        msp = [sp[k] / n[k] if n[k] else float('nan') for k in range(10)]
        t2['%s%d' % (a, s)] = {'n': n, 'zero': z, 'longest_s': lz, 'mean_first_speed': msp, 'top_runs': e['top_zero_runs'][:8]}
        rows.append(['%s v3c3-s%d' % (a.upper() if a != 'va' else 'V-A', s)] + ['%d / %d / %d / %.0f' % (n[k], z[k], lz[k], msp[k]) for k in range(10)])
tbl(['런'] + ['%d–%d' % b for b in B900], rows)
rep['T2'] = t2

# ---------------- T3: link 26 lane-1 maps ----------------
def l26(a, s, key):
    return A(R[(a, s)][key])  # (39,3,30)


def agg_pos500_time900(m):  # m (39,30) -> (8,10)
    out = np.zeros((8, 10))
    for p in range(39):
        pk = min(p // 5, 7)
        for k in range(10):
            out[pk, k] += m[p, 3 * k:3 * k + 3].sum()
    return out


md.append('## T3 링크 26 체류 차 (veh·h), 500 m × 900 s, 차로 1 / 차로 2+3')
t3 = {}
for x, y, lab in (('b', 'nc', 'B − NC3'), ('b', 'va', 'B − V-A')):
    for s in SEEDS:
        for lname, lsel in (('차로1', [0]), ('차로2+3', [1, 2])):
            mx = l26(x, s, 'l26_occ')[:, lsel, :].sum(axis=1); my = l26(y, s, 'l26_occ')[:, lsel, :].sum(axis=1)
            dd = agg_pos500_time900(mx - my)
            t3['%s|%d|%s' % (lab, s, lname)] = dd.tolist()
            md.append('**%s v3c3-s%d %s** (줄 = 위치 500 m 칸, 칸 = 900 s)' % (lab, s, lname))
            tbl(['위치'] + ['%d–%d' % b for b in B900] + ['합'],
                [['%d–%d' % (500 * p, 500 * (p + 1) if p < 7 else 3818)] + [f1(z) for z in dd[p]] + [f1(dd[p].sum())] for p in range(8)]
                + [['합'] + [f1(z) for z in dd.sum(axis=0)] + [f1(dd.sum())]])
rep['T3'] = t3

# lane-1 mean speed map, 500 m x 900 s, levels
md.append('## T3b 링크 26 차로 1 평균 속도 (km/h), 500 m × 900 s')
t3b = {}
for s in SEEDS:
    for a in ARMS:
        occ = l26(a, s, 'l26_occ')[:, 0, :]; sw = l26(a, s, 'l26_spdw')[:, 0, :]
        o5 = agg_pos500_time900(occ); s5 = agg_pos500_time900(sw)
        v = np.where(o5 > 0, s5 / np.where(o5 > 0, o5, 1), np.nan)
        t3b['%s%d' % (a, s)] = v.tolist()
        md.append('**%s v3c3-s%d**' % ('V-A' if a == 'va' else a.upper(), s))
        tbl(['위치'] + ['%d–%d' % b for b in B900], [['%d–%d' % (500 * p, 500 * (p + 1) if p < 7 else 3818)] + ['%.0f' % z for z in v[p]] for p in range(8)])
rep['T3b'] = t3b

# ---------------- T4: lane-1 queue tail (100 m x 300 s) ----------------
md.append('## T4 링크 26 차로 1 대기 꼬리 (300 s 칸; 3,600–3,700 m 칸부터 거슬러 평균 속도 < 40 km/h 가 이어진 가장 위 칸의 시작 m; "–" = 3,600 m 칸이 40 이상)')
t4 = {}
rows = []
for s in SEEDS:
    for a in ARMS:
        occ = l26(a, s, 'l26_occ')[:, 0, :]; sw = l26(a, s, 'l26_spdw')[:, 0, :]
        v = np.where(occ > 0, sw / np.where(occ > 0, occ, 1), 999.0)
        tails = []
        for k in range(NTB):
            if v[36, k] >= 40:
                tails.append(None)
                continue
            p = 36
            while p - 1 >= 0 and v[p - 1, k] < 40:
                p -= 1
            tails.append(p * 100)
        t4['%s%d' % (a, s)] = tails
        rows.append(['%s v3c3-s%d' % ('V-A' if a == 'va' else a.upper(), s)] + [('–' if z is None else str(z)) for z in tails])
tbl(['런'] + ['%d' % (300 * k) for k in range(NTB)], rows)
rep['T4'] = t4
# entrance-cell (0-100 m) lane speeds per 300 s
md.append('## T4b 링크 26 0–100 m 칸 평균 속도 (km/h), 차로 1/2/3, 300 s 칸 — 900 s 마다 셋째 칸만 적음 생략 없이 json 에')
t4b = {}
for s in SEEDS:
    for a in ARMS:
        occ = l26(a, s, 'l26_occ')[0]; sw = l26(a, s, 'l26_spdw')[0]
        t4b['%s%d' % (a, s)] = np.where(occ > 0, sw / np.where(occ > 0, occ, 1), np.nan).tolist()
rep['T4b'] = t4b
rows = []
for s in SEEDS:
    for a in ARMS:
        v = A(t4b['%s%d' % (a, s)])
        rows.append(['%s v3c3-s%d' % ('V-A' if a == 'va' else a.upper(), s)] + ['%.0f/%.0f/%.0f' % (v[0, k], v[1, k], v[2, k]) for k in range(0, NTB, 3)])
tbl(['런'] + ['%d–%d' % (300 * k, 300 * k + 300) for k in range(0, NTB, 3)], rows)

# ---------------- T5: class composition ----------------
md.append('## T5 링크 26 체류를 차 부류로 (veh·h): 차로 1 / 차로 2+3, 전체 [0, 9000] s')
t5 = {}
names = R[('b', 31)]['class_names']
rows = []
for s in SEEDS:
    for a in ARMS:
        c = A(R[(a, s)]['l26_cls_lane_time'])  # (12,3,30)
        l1 = c[:, 0, :].sum(axis=1); l23 = c[:, 1:, :].sum(axis=(1, 2))
        t5['%s%d' % (a, s)] = {'lane1': l1.tolist(), 'lane23': l23.tolist(), 'counts': R[(a, s)]['class_counts']}
for s in SEEDS:
    for a in ARMS:
        v = t5['%s%d' % (a, s)]
        rows.append(['%s v3c3-s%d' % ('V-A' if a == 'va' else a.upper(), s)] + ['%.1f / %.1f (%d)' % (v['lane1'][i], v['lane23'][i], v['counts'][i]) for i in range(12) if i in (0, 1, 3, 4, 6, 7, 9)])
tbl(['런'] + [names[i] for i in range(12) if i in (0, 1, 3, 4, 6, 7, 9)], rows)
rep['T5'] = t5
rep['class_names'] = names

# ---------------- T6: flows ----------------
md.append('## T6 본 링크 옮겨감 수 (대, 900 s 칸)')
t6 = {}
FL = ['26>125', '26>129', '26>120', '124>26', '32>129', '129>119', '129>127', '32>120', '124>125', '119>124']
for fk in FL:
    rows = []
    for s in SEEDS:
        for a in ARMS:
            v = to900(R[(a, s)]['flows'][fk])
            t6['%s|%s%d' % (fk, a, s)] = v
            rows.append(['%s v3c3-s%d' % ('V-A' if a == 'va' else a.upper(), s)] + ['%d' % z for z in v] + ['%d' % sum(v)])
    md.append('**%s**' % fk)
    tbl(['런'] + ['%d–%d' % b for b in B900] + ['합'], rows)
rep['T6'] = t6

# ---------------- T7: link occupancy series ----------------
md.append('## T7 링크·커넥터 체류 (veh·h, 900 s 칸) — 수준 B / NC3 / V-A, 그리고 느린 체류(< 10 km/h) B / NC3 / V-A')
t7 = {}
LK = ['10491', '129', '10490', '10777', '127', '124', '10480', '32', '10482', '10778', '125', '10479', '10771', '120', '119']
for L in LK:
    rows = []
    for s in SEEDS:
        lev = [to900(R[(a, s)]['links'][L]['occ']) for a in ARMS]
        slo = [to900(R[(a, s)]['links'][L]['slow']) for a in ARMS]
        t7['%s|%d' % (L, s)] = {'occ': lev, 'slow': slo}
        rows.append(['v3c3-s%d 체류' % s] + ['%s/%s/%s' % (lv(lev[0][k]), lv(lev[1][k]), lv(lev[2][k])) for k in range(10)] + ['%s/%s/%s' % (lv(sum(lev[0])), lv(sum(lev[1])), lv(sum(lev[2])))])
        rows.append(['v3c3-s%d 느림' % s] + ['%s/%s/%s' % (lv(slo[0][k]), lv(slo[1][k]), lv(slo[2][k])) for k in range(10)] + ['%s/%s/%s' % (lv(sum(slo[0])), lv(sum(slo[1])), lv(sum(slo[2])))])
    md.append('**링크 %s** (B/NC3/V-A)' % L)
    tbl(['시드'] + ['%d–%d' % b for b in B900] + ['합'], rows)
rep['T7'] = t7

# link 129 lane x pos (aggregate over time) and link 120 first 1 km
md.append('## T7b 링크 129 체류 (veh·h), 50 m 칸 × 차로, 전체 시간 — B / NC3 / V-A')
t7b = {}
for s in SEEDS:
    rows = []
    for p in range(7):
        cells = []
        for ln in range(3):
            vals = [A(R[(a, s)]['l129_occ'])[p, ln, :].sum() for a in ARMS]
            cells.append('%.1f/%.1f/%.1f' % tuple(vals))
        rows.append(['%d–%d' % (50 * p, 50 * p + 50)] + cells)
    t7b[str(s)] = {a: A(R[(a, s)]['l129_occ']).sum(axis=2).tolist() for a in ARMS}
    md.append('**v3c3-s%d**' % s)
    tbl(['위치 m', '차로 1', '차로 2', '차로 3'], rows)
rep['T7b'] = t7b
md.append('## T7c 링크 120 체류 (veh·h), 250 m 칸 0–1,000 m × 차로, 전체 시간 — B / NC3 / V-A')
for s in SEEDS:
    rows = []
    for p in range(4):
        cells = []
        for ln in range(4):
            vals = [A(R[(a, s)]['l120_occ'])[p, ln, :].sum() for a in ARMS]
            cells.append('%.1f/%.1f/%.1f' % tuple(vals))
        rows.append(['%d–%d' % (250 * p, 250 * p + 250)] + cells)
    md.append('**v3c3-s%d**' % s)
    tbl(['위치 m', '차로 1', '차로 2', '차로 3', '차로 4'], rows)

# ---------------- T8: meter commands vs states per 150 s decision ----------------
def meter_cmds(path):
    out = {}
    sc1001 = {}
    with open(path, newline='', encoding='utf-8', errors='replace') as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            if r['kind'] == 'ramp_meter' and r['id'] in ('RM_C10480', 'RM_C10482', 'RM_C10490', 'RM_C10646', 'RM_C10644'):
                out.setdefault(r['id'], {})[int(float(r['sim_sec']))] = float(r['green_sec'])
            if r['kind'] == 'signal_sg' and r['sc_no'] == '1001' and r['dsd_no'] in ('2', '5'):
                sc1001.setdefault('SG' + r['dsd_no'], {})[int(float(r['sim_sec']))] = float(r['p2_green']) - float(r['p1_green'])
    return out, sc1001


md.append('## T8 B 미터 명령(결정마다 녹색 s)과 같은 150 s 구간의 상태 (프레임 평균 대 수 / 구간 합)')
t8 = {}
for s in SEEDS:
    cm, sg = meter_cmds(ACT[('b', s)])
    cmv, sgv = meter_cmds(ACT[('va', s)])
    fs = {a: {k: A(v) for k, v in R[(a, s)]['frame_series'].items()} for a in ARMS}
    ft = A(R[('b', s)]['frame_times'])
    Ts = sorted(cm['RM_C10480'].keys())
    rows = []
    recs = []
    for T in Ts:
        if T < 900:
            continue
        m = (ft >= T) & (ft < T + 150)
        rec = {'T': T, 'g10480': cm['RM_C10480'][T], 'g10482': cm['RM_C10482'][T], 'g10490': cm['RM_C10490'][T],
               'sg2': sg.get('SG2', {}).get(T), 'sg5': sg.get('SG5', {}).get(T),
               'sg2_va': sgv.get('SG2', {}).get(T), 'sg5_va': sgv.get('SG5', {}).get(T)}
        for a in ARMS:
            f = fs[a]
            rec[a] = {
                'new1099': float(f['new1099'][m].sum()),
                'l26_l1_slow_end': float(f['l26_l1_slow_7'][m].mean()),
                'l26_l1_slow_all': float(sum(f['l26_l1_slow_%d' % k][m].mean() for k in range(8))),
                'l26_entr_slow': float(f['l26_entr_slow'][m].mean()),
                'l129_l1_slow150': float(f['l129_l1_slow150'][m].mean()),
                'l129_slow': float(f['l129_slow'][m].mean()),
                'n10490': float(f['10490_n'][m].mean()), 'slow10490': float(f['10490_slow'][m].mean()),
                'n10491': float(f['10491_n'][m].mean()), 'slow10491': float(f['10491_slow'][m].mean()),
                'n10480': float(f['10480_n'][m].mean()), 'n124': float(f['124_n'][m].mean()),
                'n127': float(f['127_n'][m].mean()), 'slow127': float(f['127_slow'][m].mean()),
                'l120_0_500_slow': float(f['l120_0_500_slow'][m].mean()),
            }
        recs.append(rec)
    t8[str(s)] = recs
    # correlation over decisions (B): g10490 vs next-interval 10490 slow; 10490 slow vs 10491 slow; 10491 slow vs l26 end slow
    def corr(x, y):
        x = A(x); y = A(y)
        if x.std() == 0 or y.std() == 0:
            return float('nan')
        return float(np.corrcoef(x, y)[0, 1])
    g = [r['g10490'] for r in recs]
    cc = {
        'g10490~slow10490': corr(g, [r['b']['slow10490'] for r in recs]),
        'g10490~l129_l1_slow150': corr(g, [r['b']['l129_l1_slow150'] for r in recs]),
        'l129_l1_slow150~slow10491': corr([r['b']['l129_l1_slow150'] for r in recs], [r['b']['slow10491'] for r in recs]),
        'slow10491~l26_l1_slow_end': corr([r['b']['slow10491'] for r in recs], [r['b']['l26_l1_slow_end'] for r in recs]),
        'l26_l1_slow_all~l26_entr_slow': corr([r['b']['l26_l1_slow_all'] for r in recs], [r['b']['l26_entr_slow'] for r in recs]),
        'g10480~l26_l1_slow_end': corr([r['g10480'] for r in recs], [r['b']['l26_l1_slow_end'] for r in recs]),
        'g10480~n10480': corr([r['g10480'] for r in recs], [r['b']['n10480'] for r in recs]),
        'sg2~slow127': corr([r['sg2'] for r in recs], [r['b']['slow127'] for r in recs]),
    }
    t8[str(s) + '_corr'] = cc
    md.append('**v3c3-s%d** (B 결정 %d개; 상관 %s)' % (s, len(recs), ', '.join('%s %.2f' % (k, v) for k, v in cc.items())))
    head = ['T', 'g10480', 'g10482', 'g10490', 'SG2 B/VA', 'B 10490 느림', 'B 129차로1≥150 느림', 'B 10491 느림', 'B 26차로1 3500+ 느림', 'B 26차로1 느림 합', 'B 입구 느림', 'B 새1099', 'NC3 10491 느림 / 26차로1 합 / 새1099', 'V-A 10491 느림 / 26차로1 합 / 새1099', 'B 127 느림 / NC3']
    rows = []
    for r in recs:
        rows.append([r['T'], '%.0f' % r['g10480'], '%.0f' % r['g10482'], '%.0f' % r['g10490'],
                     '%s/%s' % ('%.0f' % r['sg2'] if r['sg2'] is not None else '–', '%.0f' % r['sg2_va'] if r['sg2_va'] is not None else '–'),
                     '%.1f' % r['b']['slow10490'], '%.1f' % r['b']['l129_l1_slow150'], '%.1f' % r['b']['slow10491'],
                     '%.1f' % r['b']['l26_l1_slow_end'], '%.1f' % r['b']['l26_l1_slow_all'], '%.1f' % r['b']['l26_entr_slow'], '%.0f' % r['b']['new1099'],
                     '%.1f / %.1f / %.0f' % (r['nc']['slow10491'], r['nc']['l26_l1_slow_all'], r['nc']['new1099']),
                     '%.1f / %.1f / %.0f' % (r['va']['slow10491'], r['va']['l26_l1_slow_all'], r['va']['new1099']),
                     '%.1f / %.1f' % (r['b']['slow127'], r['nc']['slow127'])])
    tbl(head, rows)
rep['T8'] = t8

# ---------------- T9: 1099 link-26 dwell by exit class ----------------
md.append('## T9 1099 차의 링크 26 머문 시간 평균 (s), 출구 부류 × 들어온 900 s 칸 — B / NC3 / V-A')
t9 = {}
for s in SEEDS:
    rows = []
    for e in ('x125', 'x129', 'thru'):
        cells = []
        for k in range(10):
            vals = []
            for a in ARMS:
                d = R[(a, s)]['dwell26_1099_by_exit'][e]
                n = sum(d['n'][3 * k:3 * k + 3]); sm = sum(d['sum_s'][3 * k:3 * k + 3])
                vals.append(sm / n if n else float('nan'))
            cells.append('%.0f/%.0f/%.0f' % tuple(vals))
            t9['%d|%s|%d' % (s, e, k)] = vals
        rows.append([e] + cells)
    md.append('**v3c3-s%d**' % s)
    tbl(['출구'] + ['%d–%d' % b for b in B900], rows)
rep['T9'] = t9

# ramp vehicles
md.append('## T10 램프 10480 → 링크 26 합류 차: 수 · 첫 속도 평균 · 출구(x125/x129/통과/없음)')
rows = []
for s in SEEDS:
    for a in ARMS:
        r_ = R[(a, s)]['ramp_on26']
        n = sum(r_['n']); sp = sum(r_['first_speed_sum'])
        rows.append(['%s v3c3-s%d' % ('V-A' if a == 'va' else a.upper(), s), n, '%.1f' % (sp / n if n else float('nan')), '/'.join(str(z) for z in r_['exit_counts'])])
tbl(['런', '합류 수', '첫 속도', '출구'], rows)

with open(os.path.join(OUT, 'report_tables.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(md) + '\n')
with open(os.path.join(OUT, 'report.json'), 'w', encoding='utf-8') as fh:
    json.dump(rep, fh)
print('REPORT_DONE')
