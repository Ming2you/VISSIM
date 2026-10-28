# w1099_report2_add.py — w1099_report2.py 가 exec 로 읽는 덧붙임 표 T11–T15 (W1099_RULE_ADD1, 데이터 뒤 선언; 읽기만)
# 이름 공간: R, md, rep, tbl, A, f1, lv, SEEDS, ARMS, B900, to900, t8, OUT, NTB 를 report2 에서 씀.
S2 = {}
for a in ARMS:
    for s in SEEDS:
        S2[(a, s)] = json.load(open(os.path.join(OUT, 's2_%s%d.json' % (a, s)), encoding='utf-8'))
SCR = json.load(open(os.path.join(OUT, 'sc_readback.json'), encoding='utf-8'))


def nm(a):
    return 'V-A' if a == 'va' else ('NC3' if a == 'nc' else 'B')


# ---------------- T11: SG green seconds ----------------
md.append('## T11 SC1001·SC1002 SG 녹색 초 (900 s 칸) — B·V-A 는 readback 다시 짬(덮인 초), NC3 는 고정 신호 파일')
t11 = {}
for key, lab in (('1001_2', 'SC1001 SG2 (링크 127 차로 1·2, 동행 직진)'), ('1001_5', 'SC1001 SG5 (127 차로 3, 동행 좌회전)'),
                 ('1002_2', 'SC1002 SG2 (링크 30 차로 2·3)'), ('1002_5', 'SC1002 SG5 (링크 30 차로 4)')):
    sc, sg = key.split('_')
    nc = SCR['nc3_sig'][sc][sg]['per_300s']
    rows = []
    for s in SEEDS:
        for a in ('b', 'va'):
            d = SCR['%s%d' % (a, s)][key]
            g = to900(d['green_s_bin']); c = to900(d['covered_s_bin'])
            t11['%s|%s%d' % (key, a, s)] = {'green': g, 'covered': c}
            rows.append(['%s v3c3-s%d' % (nm(a), s)] + [('%.0f' % g[k]) if c[k] >= 899 else ('–' if c[k] == 0 else '%.0f(%.0f)' % (g[k], c[k])) for k in range(10)] + ['%.0f' % sum(g[1:])])
    rows.append(['NC3 (세 시드 같음)'] + ['%.0f' % (3 * nc)] * 10 + ['%.0f' % (27 * nc)])
    t11['%s|nc' % key] = 3 * nc
    md.append('**%s** (줄 끝 = 900–9,000 s 합)' % lab)
    tbl(['런'] + ['%d–%d' % b for b in B900] + ['900–9000 합'], rows)
rep['T11'] = t11
rep['T11_rows_bad'] = {k: v['rows_bad'] for k, v in SCR.items() if k != 'nc3_sig'}

# ---------------- T12: link 127 / 30 ----------------
md.append('## T12 링크 127·30 (SC1001 동행 접근로와 그 하류)')
t12 = {}
md.append('**T12a 링크 127 느린 체류 (veh·h), 차로 1 / 2 / 3, 900 s 칸** — B / NC3 / V-A')
for s in SEEDS:
    rows = []
    for a in ARMS:
        m = A(S2[(a, s)]['m127_slow'])  # (13,3,30)
        cells = []
        for k in range(10):
            v = m[:, :, 3 * k:3 * k + 3].sum(axis=(0, 2))
            cells.append('%.1f/%.1f/%.1f' % tuple(v))
        t12['127slow|%s%d' % (a, s)] = [m[:, :, 3 * k:3 * k + 3].sum(axis=(0, 2)).tolist() for k in range(10)]
        rows.append(['%s v3c3-s%d' % (nm(a), s)] + cells)
    tbl(['런'] + ['%d–%d' % b for b in B900], rows)
md.append('**T12b 링크 127 0–50 m 칸(10777 들어오는 곳) 차로 1·2 평균 속도 (km/h), 300 s 칸 셋을 900 s 로 묶음(체류 가중)** — 127 대기가 링크 129 로 넘어가는지')
for s in SEEDS:
    rows = []
    for a in ARMS:
        o = A(S2[(a, s)]['m127_occ'])[0, 0:2, :].sum(axis=0); sw = A(S2[(a, s)]['m127_spdw'])[0, 0:2, :].sum(axis=0)
        v = [(sw[3 * k:3 * k + 3].sum() / o[3 * k:3 * k + 3].sum()) if o[3 * k:3 * k + 3].sum() > 0 else float('nan') for k in range(10)]
        t12['127start_speed|%s%d' % (a, s)] = v
        rows.append(['%s v3c3-s%d' % (nm(a), s)] + ['%.0f' % z for z in v])
    tbl(['런'] + ['%d–%d' % b for b in B900], rows)
md.append('**T12c 링크 30 0–100 m 느린 체류 (veh·h, 900 s 칸)** — B / NC3 / V-A (SC1002 대기가 SC1001 출구까지 오는지)')
rows = []
for s in SEEDS:
    vals = []
    for a in ARMS:
        m = A(S2[(a, s)]['m30_slow'])[0:2].sum(axis=(0, 1))
        vals.append(to900(m))
        t12['30front_slow|%s%d' % (a, s)] = to900(m)
    rows.append(['v3c3-s%d' % s] + ['%.1f/%.1f/%.1f' % (vals[0][k], vals[1][k], vals[2][k]) for k in range(10)] + ['%.1f/%.1f/%.1f' % (sum(vals[0]), sum(vals[1]), sum(vals[2]))])
tbl(['시드'] + ['%d–%d' % b for b in B900] + ['합'], rows)
md.append('**T12d 본 링크 옮겨감 수 (대, 900 s 칸)** — B / NC3 / V-A')
for fk in ('2>127', '129>127', '127>30', '127>38', '127>39'):
    rows = []
    for s in SEEDS:
        vals = [to900(S2[(a, s)]['flows'][fk]) for a in ARMS]
        t12['%s|%d' % (fk, s)] = vals
        rows.append(['v3c3-s%d' % s] + ['%d/%d/%d' % (vals[0][k], vals[1][k], vals[2][k]) for k in range(10)] + ['%d/%d/%d' % (sum(vals[0]), sum(vals[1]), sum(vals[2]))])
    md.append('*%s*' % fk)
    tbl(['시드'] + ['%d–%d' % b for b in B900] + ['합'], rows)
md.append('**T12e 링크 2·10481·30 체류 (veh·h, 합)** — B / NC3 / V-A')
rows = []
for s in SEEDS:
    rows.append(['v3c3-s%d' % s] + ['%.1f/%.1f/%.1f' % tuple(sum(S2[(a, s)]['links'][L]['occ']) for a in ARMS) for L in ('2', '10481', '30', '38', '39')])
tbl(['시드', '링크 2', '10481', '30', '38', '39'], rows)
rep['T12'] = t12

# ---------------- T13: onset ----------------
TH = [('slow127', 100.0, '127 느림 ≥ 100'), ('l129_l1_slow150', 3.0, '129 차로1 느림 ≥ 3'), ('slow10491', 2.0, '10491 느림 ≥ 2'),
      ('l26_l1_slow_end', 5.0, '26 차로1 3,500+ 느림 ≥ 5'), ('l26_l1_slow_all', 150.0, '26 차로1 느림 합 ≥ 150'), ('l26_entr_slow', 25.0, '26 입구 느림 ≥ 25')]
md.append('## T13 처음 문턱을 넘은 150 s 구간 시작 T (s) · 넘은 구간 수 (900–8,850 s, 결정 구간 54개 안팎) — 문턱은 W1099_RULE_ADD1 §1')
t13 = {}
rows = []
for s in SEEDS:
    recs = t8[str(s)]
    for a in ARMS:
        cells = []
        for key, th, lab in TH:
            hit = [r['T'] for r in recs if r[a][key] >= th]
            t13['%s|%s%d' % (key, a, s)] = {'first': hit[0] if hit else None, 'n': len(hit), 'Ts': hit}
            cells.append('%s · %d' % (hit[0] if hit else '–', len(hit)))
        rows.append(['%s v3c3-s%d' % (nm(a), s)] + cells)
tbl(['런'] + [x[2] for x in TH], rows)
rep['T13'] = t13

# ---------------- T14: conservation ----------------
md.append('## T14 보존 점검: 누적 차(B − NC3, 대) — 넣은 1099 수 · 링크 26 나감 합(26→125·129·120) · 램프 합류(124→26), 900 s 끝마다')
t14 = {}
rows = []
for s in SEEDS:
    for lab, x, y in (('B − NC3', 'b', 'nc'), ('B − V-A', 'b', 'va')):
        ins = np.cumsum(A(to900(R[(x, s)]['entrance']['n_ins_bin'])) - A(to900(R[(y, s)]['entrance']['n_ins_bin'])))
        ex = np.zeros(10)
        for fk in ('26>125', '26>129', '26>120'):
            ex += A(to900(R[(x, s)]['flows'][fk])) - A(to900(R[(y, s)]['flows'][fk]))
        ex = np.cumsum(ex)
        rm = np.cumsum(A(to900(R[(x, s)]['flows']['124>26'])) - A(to900(R[(y, s)]['flows']['124>26'])))
        t14['%s|%d' % (lab, s)] = {'ins': ins.tolist(), 'exits': ex.tolist(), 'ramp': rm.tolist()}
        rows.append(['%s v3c3-s%d' % (lab, s)] + ['%+d / %+d / %+d' % (ins[k], ex[k], rm[k]) for k in range(10)])
tbl(['짝'] + ['≤%d' % b[1] for b in B900], rows)
rep['T14'] = t14

# ---------------- T15: lane-1 class composition 2700-4500 ----------------
md.append('## T15 링크 26 체류 부류별 차 (veh·h), 2,700–4,500 s, 차로 1 / 차로 2+3')
t15 = {}
names = R[('b', 31)]['class_names']
sel = [0, 3, 6, 9, 4, 7]
rows = []
for s in SEEDS:
    for lab, x, y in (('B − NC3', 'b', 'nc'), ('B − V-A', 'b', 'va')):
        cx = A(R[(x, s)]['l26_cls_lane_time'])[:, :, 9:15]; cy = A(R[(y, s)]['l26_cls_lane_time'])[:, :, 9:15]
        d1 = (cx[:, 0, :] - cy[:, 0, :]).sum(axis=1); d23 = (cx[:, 1:, :] - cy[:, 1:, :]).sum(axis=(1, 2))
        t15['%s|%d' % (lab, s)] = {'lane1': d1.tolist(), 'lane23': d23.tolist()}
        rows.append(['%s v3c3-s%d' % (lab, s)] + ['%s / %s' % (f1(d1[i]), f1(d23[i])) for i in sel] + ['%s / %s' % (f1(d1.sum()), f1(d23.sum()))])
tbl(['짝'] + [names[i] for i in sel] + ['합'], rows)
rep['T15'] = t15
