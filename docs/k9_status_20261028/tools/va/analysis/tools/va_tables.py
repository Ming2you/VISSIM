r"""V-A analysis step 6: markdown tables from <out>/va_metrics.json, va_local.json, va_control.json, va_followup.json.
python -B va_tables.py --profile va|selftest  ->  <out>/va_tables.json ({marker: markdown}).  Formatting only.
Rules kept here (amendment 34 sec.8.2 R8, sec.8.4 R12): every union-dependent column carries its union name; the
label cells use exactly the three fixed phrases; Omega (3) never appears without (4) and Omega outside (a) in the same
table; "관측된 차이" only where the 90 % CI excludes 0, with the number of rows and "보정 없음" given by the report."""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

S = ('31', '41', '43')
SN = {'31': 'v3c3-s31', '41': 'v3c3-s41', '43': 'v3c3-s43'}
ROWS = [('M1', '① fw_e_main 7링크'), ('M2', '② 동측 국소 19링크'), ('M3', '**③ Ω (635링크)**'), ('M3u', '③u urban_omega'),
        ('M4', '**④ 전체 + 미삽입**'), ('M4a', '④a 전체 링크 TTT (1,236)'), ('M4b', '④b 미삽입 (합집합, NC3 앵커)'),
        ('OUT_a', '**Ω 밖 (a) ④ − ③**'), ('OUT_b', 'Ω 밖 (b) ④a − ③ (링크만)'),
        ('REM', 'Ω 밖 (d) 차로변경 제거, 읽는 법 A (대)'), ('REM_B', 'Ω 밖 (d) 차로변경 제거, 읽는 법 B (대)')]
ROWS_X = ROWS + [('unins_1098', '④b 중 입력 1098'), ('unins_1099', '④b 중 입력 1099'), ('unins_other', '④b 중 그 밖 입력'),
                 ('x_off_receivers_shared', '(② 밖) 진출 수신 121·124·126·127')]
UDEP = ('M4', 'M4b', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
UNAME = {'U6VA': 'U6(V-A)', 'U9': 'U9', 'U6J1': 'U6(J1)'}


def f(x, nd=1, sign=False):
    if x is None:
        return '–'
    if isinstance(x, bool):
        return str(x)
    return ('%+.*f' % (nd, x)) if sign else ('%.*f' % (nd, x))


def nd_of(k):
    return 0 if k in ('REM', 'REM_B') else 1


def main():
    prof = V.profile_from_argv()
    V.require_pinned(prof, __file__)
    M = V.jload(os.path.join(prof.out, 'va_metrics.json'))
    L = V.jload(os.path.join(prof.out, 'va_local.json'))
    K = V.jload(os.path.join(prof.out, 'va_control.json'))
    F = V.jload(os.path.join(prof.out, 'va_followup.json'))
    P = M['pairs']
    T = {}

    def lvl(u, tag, k):
        return M['per_run']['%s|%s' % (u, tag)]['full'][k]
    # per-seed levels and the two paired differences, union per column (R8)
    for s in S:
        lines = ['| 지표 | NC3 [U6(V-A)] | V-A [U6(V-A)] | **d(V-A − NC3)** [U6(V-A)] | NC3 [U9] | J1 [U9] | V-A [U9] | '
                 'd(J1 − NC3) [U9] | **d(V-A − J1)** [U9] | J1 보고 값 d(J1 − NC3) [U6(J1)] |',
                 '|---|' + '---:|' * 10]
        for k, lab in ROWS_X:
            nd = nd_of(k)
            cells = [f(lvl('U6VA', 'nc3_s' + s, k), nd), f(lvl('U6VA', 'va_s' + s, k), nd),
                     f(P['A']['summary'][k]['per_seed'][s], nd, True),
                     f(lvl('U9', 'nc3_s' + s, k), nd), f(lvl('U9', 'j1_s' + s, k), nd), f(lvl('U9', 'va_s' + s, k), nd),
                     f(P['Bp']['summary'][k]['per_seed'][s], nd, True), f(P['B']['summary'][k]['per_seed'][s], nd, True),
                     f(P['J1R']['summary'][k]['per_seed'][s], nd, True)]
            lines.append('| %s%s | %s |' % (lab, '' if k in UDEP else ' (합집합 무관)', ' | '.join(cells)))
        s7v, s7j = M['s7_late']['va_s' + s], M['s7_late']['j1_s' + s]
        lines.append('| Ω 밖 (e) S7 늦은 보고 / jsonl 제거 기록 (대) | – | %d / %d | – | – | %d / %d | %d / %d | – | – | – |' % (
            s7v['late'], s7v['unique_removals'], s7j['late'], s7j['unique_removals'], s7v['late'], s7v['unique_removals']))
        rem = M['remains_by_run']
        lines.append('| Ω 밖 (f) 런 끝 remain (입력: 대) | %s | %s | – | %s | %s | %s | – | – | – |' % tuple(
            ', '.join('%s: %d' % kv for kv in sorted(rem[t].items(), key=lambda kv: int(kv[0]))) or '없음'
            for t in ('nc3_s' + s, 'va_s' + s, 'nc3_s' + s, 'j1_s' + s, 'va_s' + s)))
        T['LEVELS_S' + s] = '\n'.join(lines)
    # 3-seed summaries per pair
    for pk, title in (('A', 'd(V-A − NC3) [U6(V-A)]'), ('B', 'd(V-A − J1) [U9]'), ('Bp', 'd(J1 − NC3) [U9]'),
                      ('J1R', 'J1 보고 값 d(J1 − NC3) [U6(J1)]')):
        lines = ['| 지표 (%s) | d s31 | d s41 | d s43 | 평균 d | sd | 90 %% CI | 음/양 | 평균/NC %% | 시드별 d/NC %% | 잡음 참고 반폭 | CI 표시 |' % title,
                 '|---|---:|---:|---:|---:|---:|---|---|---:|---|---:|---|']
        for k, lab in ROWS_X:
            st = P[pk]['summary'][k]
            nd = nd_of(k)
            lines.append('| %s | %s | %s | %s | %s | %s | [%s, %s] | %d/%d | %s | %s | %s | %s |' % (
                lab, f(st['per_seed']['31'], nd, True), f(st['per_seed']['41'], nd, True), f(st['per_seed']['43'], nd, True),
                f(st['mean'], 1, True), f(st['sd'], 1), f(st['ci90'][0], 1, True), f(st['ci90'][1], 1, True), st['neg'],
                st['pos'], f(st['pct_of_nc'], 2, True), ' / '.join(f(x, 1, True) for x in st['per_seed_pct']),
                str(V.NOISE.get(k, ('', '–'))[1]), '관측된 차이' if st['ci_excludes_0'] else '0 포함'))
        T['SUMMARY_' + pk] = '\n'.join(lines)
    T['N_ROWS_SUMMARY'] = str(len(ROWS_X))
    # labels (sec.8.4), (A) on U6(V-A), (B) on U9
    for pk in ('A', 'B'):
        lines = ['| 대상 | d(③) | d(④) | d(④ − ③) | d(④b) | d(제거 A) | d(제거 B) | 읽는 법 N | 읽는 법 W (제거 A) | 읽는 법 W (제거 B) |',
                 '|---|---:|---:|---:|---:|---:|---:|---|---|---|']
        for s in S + ('mean',):
            g = ({k: P[pk]['summary'][k]['mean'] for k in ('M3', 'M4', 'OUT_a', 'M4b', 'REM', 'REM_B')} if s == 'mean'
                 else P[pk]['deltas'][s])
            lab = P[pk]['labels'][s]
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                '3시드 평균' if s == 'mean' else SN[s], f(g['M3'], 1, True), f(g['M4'], 1, True), f(g['OUT_a'], 1, True),
                f(g['M4b'], 1, True), f(g['REM'], 1, True), f(g['REM_B'], 1, True), lab['N'], lab['W_A'], lab['W_B']))
        T['LABELS_' + pk] = '\n'.join(lines)
    # Omega split (with 4, Omega outside (a), removals in the same table)
    names = [('fw_e_main', 'fw_e_main'), ('fw_w_main', 'fw_w_main'), ('onramp', 'onramp (Ω 안)'), ('offramp_inside', 'offramp (Ω 안)'),
             ('urban_omega', 'urban_omega'), ('outside_inside(=0)', 'outside (Ω 안, 0이어야 함)'), ('omega_total', '**합 = ③ Ω**')]
    for pk in ('A', 'B'):
        base = 'NC3' if pk == 'A' else 'J1'
        lines = ['| Ω 부품 (%s) | %s | 평균 d | 90 %% CI | 음/양 |' % (UNAME[P[pk]['union']], ' | '.join(
            '%s %s / V-A / d' % (SN[s], base) for s in S)), '|---|---|---|---|---:|---|---|']
        for k, nm in names:
            st = P[pk]['omega_split_summary'][k]
            lines.append('| %s | %s | %s | [%s, %s]%s | %d/%d |' % (
                nm, ' | '.join('%s / %s / %s' % (f(st['base'][s]), f(st['arm'][s]), f(st['per_seed'][s], 1, True)) for s in S),
                f(st['mean'], 1, True), f(st['ci90'][0], 1, True), f(st['ci90'][1], 1, True),
                ' 관측된 차이' if st['ci_excludes_0'] else '', st['neg'], st['pos']))
        for k, nm in (('M4', '(같은 표) ④ 전체 + 미삽입'), ('OUT_a', '(같은 표) Ω 밖 (a) ④ − ③'), ('M4b', '(같은 표) ④b 미삽입'),
                      ('REM', '(같은 표) 제거 읽는 법 A (대)'), ('REM_B', '(같은 표) 제거 읽는 법 B (대)')):
            st = P[pk]['summary'][k]
            nd = nd_of(k)
            lines.append('| %s | %s | %s | [%s, %s]%s | %d/%d |' % (
                nm, ' | '.join('%s / %s / %s' % (f(st['base'][s], nd), f(st['arm'][s], nd), f(st['per_seed'][s], nd, True)) for s in S),
                f(st['mean'], 1, True), f(st['ci90'][0], 1, True), f(st['ci90'][1], 1, True),
                ' 관측된 차이' if st['ci_excludes_0'] else '', st['neg'], st['pos']))
        T['SPLIT_' + pk] = '\n'.join(lines)
    # end state
    lines = ['| 런 | 끝 프레임 망 안 대수 | 끝 프레임 Ω 대수 | 본 차량 수 | 제거 (stage-1 영역별) | 제거 (소속: Ω 밖 / Ω 안) | 끝 remain (입력: 대) |',
             '|---|---:|---:|---:|---|---|---|']
    for s in S:
        for arm in ('nc3', 'j1', 'va'):
            e = M['per_run']['U9|%s_s%s' % (arm, s)]['end_state']
            lines.append('| %s %s | %d | %d | %d | %d (%s) | %d / %d | %s |' % (
                {'nc3': 'NC3', 'j1': 'J1', 'va': 'V-A'}[arm], SN[s], e['in_network_last_frame'], e['omega_last_frame'],
                e['vehicles_seen'], e['removals'], ', '.join('%s %d' % kv for kv in sorted(e['removals_by_region'].items(), key=lambda kv: -kv[1])),
                e['removals_membership']['outside_omega'], e['removals_membership']['inside_omega'],
                ', '.join('%s: %d' % kv for kv in e['remains'].items()) or '없음'))
    T['END_STATE'] = '\n'.join(lines)
    # uninserted by input per union
    for u, arms in (('U6VA', ('nc3', 'va')), ('U9', ('nc3', 'j1', 'va'))):
        ui = M['unins_by_input'][u]
        hdr = ' / '.join({'nc3': 'NC3', 'j1': 'J1', 'va': 'V-A'}[a] for a in arms)
        lines = ['| 입력 [%s] | 줄 선 런 | %s |' % (UNAME[u], ' | '.join('%s %s (끝 remain)' % (SN[s], hdr) for s in S)),
                 '|---|---|---|---|---|']
        for k in sorted(ui, key=int):
            cells = []
            for s in S:
                vals = [ui[k].get('%s_s%s' % (a, s)) for a in arms]
                cells.append('%s (%s)' % (' / '.join(f(v['veh_h_nc_anchor']) if v else '–' for v in vals),
                                          '→'.join(str(v['remain_err']) if v else '–' for v in vals)))
            lines.append('| %s | %s | %s |' % (k, ', '.join(ui[k]['queued_in']), ' | '.join(cells)))
        T['UNINS_' + u] = '\n'.join(lines)
    # cumulative d at checkpoints
    cps = [900, 1800, 3600, 5400, 7200, 9000]
    for pk in ('A', 'B'):
        bd = P[pk]['bins_delta']
        lines = ['| 지표 (%s) | 시드 | %s |' % (UNAME[P[pk]['union']], ' | '.join('누적 d ~%d s' % c for c in cps)),
                 '|---|---|' + '---:|' * len(cps)]
        for k, nm in (('M1', '①'), ('M3', '③ Ω'), ('M4', '④'), ('OUT_a', 'Ω 밖 (a)')):
            for s in S + ('mean',):
                arr = bd[k][s]
                lines.append('| %s | %s | %s |' % (nm, SN.get(s, '3시드 평균'), ' | '.join(f(sum(arr[:c // 150]), 1, True) for c in cps)))
        T['CUM_' + pk] = '\n'.join(lines)
    # pairing checks
    lines = ['| 짝 | 시드 | pairing_check ok | 첫 다른 프레임 (s) | 첫 다른 진입 (s) | 900 s 전 칸 최대 |d| |', '|---|---|---|---|---|---:|']
    for pk in ('A', 'B'):
        for s in S:
            p = P[pk]['pairing'][s]
            lines.append('| %s | %s | %s | %s | %s | %s |' % (pk, SN[s], p['ok'], p['first_divergent_frame_sec'],
                                                             p['first_divergent_entry_sec'], f(p['max_abs_pre900_delta'], 4)))
    T['PAIRING'] = '\n'.join(lines)
    # SC1001 EB local
    lab_l = [('occ_10491.P_1800_7200.mean', '10491 커넥터 대수 평균, (P) 1800–7200 s'), ('occ_10491.P_1800_7200.max', '10491 최대, (P)'),
             ('occ_10491.F_all.mean', '10491 평균, (F) 전체'), ('occ_10491.F_all.max', '10491 최대, (F)'),
             ('occ_127_lanes12.P_1800_7200.mean', '127 차로 1–2 평균, (P)'), ('occ_127_lanes12.P_1800_7200.max', '127 차로 1–2 최대, (P)'),
             ('occ_127_lanes12.F_all.mean', '127 차로 1–2 평균, (F)'), ('occ_127_lanes12.F_all.max', '127 차로 1–2 최대, (F)'),
             ('spill_FW_W.frac_peak', 'FW_W 역류 창 비율 (첨두 창)'), ('spill_FW_W.frac_all', 'FW_W 역류 창 비율 (900–9000 s)'),
             ('spill_FW_E.frac_peak', 'FW_E 역류 창 비율 (첨두 창)'), ('spill_FW_E.frac_all', 'FW_E 역류 창 비율 (900–9000 s)')]
    for pk in ('A', 'B'):
        base = 'NC3' if pk == 'A' else 'J1'
        lines = ['| 항목 | %s | d s31 / s41 / s43 | 평균 d | 90 %% CI |' % ' | '.join('%s %s / V-A' % (SN[s], base) for s in S),
                 '|---|---|---|---|---|---:|---|']
        for k, nm in lab_l:
            v = L['paired'][pk][k]
            nd = 3 if 'spill' in k else 1
            lines.append('| %s | %s | %s | %s | [%s, %s]%s |' % (
                nm, ' | '.join('%s / %s' % (f(b, nd), f(a, nd)) for b, a in zip(v['base'], v['arm'])),
                ' / '.join(f(x, nd, True) for x in v['per_seed']), f(v['mean'], nd, True), f(v['ci90'][0], nd, True),
                f(v['ci90'][1], nd, True), ' 관측된 차이' if v['ci_excludes_0'] else ''))
        T['SC1001_' + pk] = '\n'.join(lines)
    lines = ['| 런 | FW_W 사건 창 수 / 첫 사건 (s) | FW_E 사건 창 수 / 첫 사건 (s) |', '|---|---|---|']
    for s in S:
        for arm in ('nc3', 'j1', 'va'):
            r = L['runs']['%s_s%s' % (arm, s)]
            lines.append('| %s %s | %d / %s | %d / %s |' % ({'nc3': 'NC3', 'j1': 'J1', 'va': 'V-A'}[arm], SN[s],
                                                         r['spill_FW_W']['n_event_windows'], r['spill_FW_W']['first'],
                                                         r['spill_FW_E']['n_event_windows'], r['spill_FW_E']['first']))
    T['SC1001_EVENTS'] = '\n'.join(lines)
    # link 174 chain
    ch = F['link174_chain']
    lines = ['| 링크 | 종류 | 길이 (m) / 차로 | 영역 · Ω | %s |' % ' | '.join('%s NC3 / J1 / V-A (전체; 4350 s 뒤)' % SN[s] for s in S),
             '|---|---|---|---|---|---|---|']
    for li in ch['links']:
        l = str(li['link'])
        cells = []
        for s in S:
            v = [ch['link_vh'][l]['%s_s%s' % (a, s)] for a in ('nc3', 'j1', 'va')]
            cells.append('%s; %s' % (' / '.join(f(x['full']) for x in v), ' / '.join(f(x['from_4350']) for x in v)))
        lines.append('| %s | %s | %s / %d | %s · %s | %s |' % (l, '커넥터' if li['connector'] else '링크', f(li['length_m']), li['lanes'],
                                                         li['region'], 'Ω 안' if li['inside_omega'] else 'Ω 밖', ' | '.join(cells)))
    lines.append('| 174 FZP 프레임 대수 평균 / 최대 @ 시각 (전체) | | | | %s |' % ' | '.join(
        ' / '.join('%s / %s @ %s' % (f(ch['fzp_174']['%s_s%s' % (a, s)]['F_all']['mean']), f(ch['fzp_174']['%s_s%s' % (a, s)]['F_all']['max'], 0),
                                     f(ch['fzp_174']['%s_s%s' % (a, s)]['F_all'].get('max_t'), 1)) for a in ('nc3', 'j1', 'va')) for s in S))
    T['LINK174'] = '\n'.join(lines)
    # input 1083
    i = F['input_1083']
    lines = ['| 런 | 끝 remain | 삽입 수 | 재구성 지체 (NC3 앵커, veh·h) | 최대 큐 (대) @ 프레임 시각 (s) | 0 아래 자른 큐 차 > 10 첫 150 s 표본 (V-A − NC3 / V-A − J1) |',
             '|---|---:|---:|---:|---|---|']
    for s in S:
        for arm in ('nc3', 'j1', 'va'):
            r = i['runs']['%s_s%s' % (arm, s)]
            first = ('%s / %s' % (i['pairs']['A']['s' + s]['first_gt10_clipped_t'] or '없음',
                                  i['pairs']['B']['s' + s]['first_gt10_clipped_t'] or '없음')) if arm == 'va' else '–'
            lines.append('| %s %s | %d | %d | %s | %s @ %s | %s |' % ({'nc3': 'NC3', 'j1': 'J1', 'va': 'V-A'}[arm], SN[s], r['remain_err'],
                                                                 r['inserted'], f(r['delay_veh_h_nc3_anchor']), f(r['max_queue_frame']),
                                                                 f(r['max_queue_frame_t'], 0), first))
    lines.append('| ④b 중 입력 1083 몫 d: (A) [U6(V-A)] / (B) [U9] | %s | | | | |' % ' ; '.join(
        '%s %s / %s' % (SN[s], f(i['pairs']['A']['s' + s]['d4b_share_1083'], 1, True), f(i['pairs']['B']['s' + s]['d4b_share_1083'], 1, True)) for s in S))
    T['INPUT1083'] = '\n'.join(lines)
    lines = ['| 짝 | 시드 | 진입 수 차 칸 28– (4,200 s–) | 칸 0–27 합 | 칸 28– 합 |', '|---|---|---|---:|---:|']
    for pk in ('A', 'B'):
        for s in S:
            r = i['pairs'][pk]['s' + s]
            lines.append('| %s | %s | %s | %d | %d |' % (pk, SN[s], ', '.join(str(x) for x in r['entries_diff_from_bin28']),
                                                     r['entries_diff_sum_bins_0_27'], r['entries_diff_sum_from_bin28']))
    T['INPUT1083_ENTRIES'] = '\n'.join(lines)
    # SC109 east
    e = F['sc109_east']
    lines = ['| 링크 | 창 | %s | d(V-A − NC3) 평균 [90 %% CI] | d(V-A − J1) 평균 [90 %% CI] |' % ' | '.join(
        '%s NC3 / J1 / V-A' % SN[s] for s in S), '|---|---|---|---|---|---|---|']
    for li in e['links']:
        l = str(li['link'])
        for win in ('full', 'P_1800_7200'):
            a, b = e['paired']['A']['%s.link_vh.%s' % (l, win)], e['paired']['B']['%s.link_vh.%s' % (l, win)]
            lines.append('| %s (%s) | link_vh %s | %s | %s [%s, %s] | %s [%s, %s] |' % (
                l, 'Ω 안' if li['inside_omega'] else 'Ω 밖', win,
                ' | '.join(' / '.join(f(e['link_vh'][l]['%s_s%s' % (x, s)][win]) for x in ('nc3', 'j1', 'va')) for s in S),
                f(a['mean'], 1, True), f(a['ci90'][0], 1, True), f(a['ci90'][1], 1, True),
                f(b['mean'], 1, True), f(b['ci90'][0], 1, True), f(b['ci90'][1], 1, True)))
        for win in ('F_all', 'P_1800_7200'):
            lines.append('| %s | FZP 프레임 대수 평균 / 최대 (%s) | %s | | |' % (l, win, ' | '.join(
                ' / '.join('%s/%s' % (f(e['fzp'][l]['%s_s%s' % (x, s)][win]['mean']), f(e['fzp'][l]['%s_s%s' % (x, s)][win]['max'], 0))
                           for x in ('nc3', 'j1', 'va')) for s in S)))
    lines.append('| 모형 SC109_E_out | | %s | | |' % e['model_SC109_E_out'])
    T['SC109_EAST'] = '\n'.join(lines)
    # control side: SC109 p3, floor, holds, previous plan kept, wall
    R = K['runs']
    lines = ['| 항목 | %s |' % ' | '.join('%s J1 / V-A' % SN[s] for s in S), '|---|---|---|---|']

    def row(lab, fn):
        lines.append('| %s | %s |' % (lab, ' | '.join('%s / %s' % (fn(R['j1_s' + s]), fn(R['va_s' + s])) for s in S)))
    row('p3 ≤ 24.5 s 결정 수 (SDMPC 55 중)', lambda r: str(r['sc109_p3']['le_24_5_count']))
    row('p3 ≤ 24.5 s 첫 T', lambda r: str(r['sc109_p3']['first_T'] or '없음'))
    row('p3 ≤ 24.5 s 최장 연속 (결정)', lambda r: str(r['sc109_p3']['longest_run']))
    for ph in ('p2', 'p3', 'p4'):
        for w in ('all', 'T_ge_4350'):
            row('SC109 %s 지령 녹색 평균 / 최대 (s), %s' % (ph, w),
                lambda r, ph=ph, w=w: '%s/%s' % (f(r['sc109_p3'][ph][w].get('mean')), f(r['sc109_p3'][ph][w].get('max'))))
    T['SC109_P3'] = '\n'.join(lines)
    lines = ['| 항목 | %s |' % ' | '.join('%s J1 / V-A' % SN[s] for s in S), '|---|---|---|---|']
    row('하한 키 이름 수 / 키 있는 결정 수', lambda r: '%d/%d' % (len(r['floor_173_p4']['names']), r['floor_173_p4']['decisions_with_key']))
    row('하한 첫 T / 첫 값 / 최댓값', lambda r: '%s/%s/%s' % (r['floor_173_p4']['first_T'], f(r['floor_173_p4']['first_value']),
                                                          f(r['floor_173_p4']['max'])))
    row('하한이 줄어든 T (유지 뒤 따로)', lambda r: '%s (%s)' % (r['floor_173_p4']['fell_T'] or '없음', r['floor_173_p4']['fell_T_after_hold'] or '없음'))
    row('k92_hb_seed_binding = 1.0 결정 수', lambda r: str(r['floor_173_p4']['seed_binding_eq_1_count']))
    row('groups_carried 합 / groups_updated 합', lambda r: '%s/%s' % (f(r['floor_173_p4']['groups_carried_sum'], 0), f(r['floor_173_p4']['groups_updated_sum'], 0)))
    row('prior_discarded = 1.0 T', lambda r: str(r['floor_173_p4']['prior_discarded_eq_1_T']))
    row('k92_w / k92_hb 있는 결정 수', lambda r: '%d/%d' % (r['floor_173_p4']['k92_present']['k92_w'], r['floor_173_p4']['k92_present']['k92_hb']))
    T['FLOOR'] = '\n'.join(lines)
    lines = ['| 항목 | %s |' % ' | '.join('%s J1 / V-A' % SN[s] for s in S), '|---|---|---|---|']
    row('유지(예외) 횟수 / T', lambda r: '%d %s' % (r['holds']['count'], r['holds']['T']))
    row('직전 계획 유지 후보 (T ≥ 1,050, 유지 아님)', lambda r: str(r['previous_plan_kept']['candidates']))
    row('(가) green_times·offsets = T−150', lambda r: str(r['previous_plan_kept']['ga_same_green_offsets']))
    row('(나) 예측 시퀀스 없음', lambda r: str(r['previous_plan_kept']['na_no_prediction_sequence']))
    row('(다) selected repr = held repr', lambda r: str(r['previous_plan_kept']['da_selected_repr_eq_held']))
    row('셋 모두 / T', lambda r: '%d %s' % (r['previous_plan_kept']['all_three'], r['previous_plan_kept']['all_three_T']))
    row('selection_status (SDMPC)', lambda r: str(r['selection']['selection_status']))
    T['HOLD_PREV'] = '\n'.join(lines)
    lines = ['| 항목 | %s |' % ' | '.join('%s J1 / V-A' % SN[s] for s in S), '|---|---|---|---|']
    row('action JSON 수', lambda r: str(r['n_action_json']))
    row('런로그 DECISIONS_OK / FAILED / HELD', lambda r: '%s/%s/%s' % tuple((r['runlog_counters'].get(k) or ['줄 없음'])[-1]
                                                                          for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_ON_EXCEPTION')))
    row('결정 exit 코드', lambda r: str(r['exit_codes']))
    row('예열 벽시계 최소–최대 (s)', lambda r: '%s–%s' % (f(r['wall_warmup'].get('min')), f(r['wall_warmup'].get('max'))))
    row('SDMPC 벽시계 최소 / 중앙 / 평균 / 최대 (s)', lambda r: '%s/%s/%s/%s' % tuple(f(r['wall_sdmpc'].get(k)) for k in ('min', 'median', 'mean', 'max')))
    row('SDMPC 벽시계 합 (s) / 900 s 넘는 결정', lambda r: '%s/%d' % (f(r['wall_sdmpc'].get('sum'), 0), len(r['wall_sdmpc_gt900_T'])))
    row('런 벽시계 WATCHDOG_EXIT (s)', lambda r: str(r['run_wall_sec']))
    lines.append('| 비 V-A / J1 SDMPC 중앙 (G-K5 예산 %s, 보고만) | %s |' % (V.G_K5_BUDGET, ' | '.join(
        f(K['wall_ratio']['s' + s]['ratio'], 4) for s in S)))
    T['WALL'] = '\n'.join(lines)
    lines = ['| 항목 | %s |' % ' | '.join('%s J1 / V-A' % SN[s] for s in S), '|---|---|---|---|']
    row('미터 써진 rate (러너 로그)', lambda r: str(sorted({x for v in r['meter_written_rate_vph'].values() for x in v})))
    row('미터 써진 green (러너 로그)', lambda r: str(sorted({x for v in r['meter_written_green_sec'].values() for x in v})))
    row('미터 명령이 바뀐 결정 수', lambda r: str(r['meter_command_changed_decisions']))
    row('FW_E 110 미만 결정 비율 / 첫 T / 최장 연속', lambda r: '%s/%s/%s' % (f(r['vsl_stats']['FW_E']['frac_any_lt110'], 3),
                                                                   r['vsl_stats']['FW_E']['first_T'], r['vsl_stats']['FW_E']['longest_run_decisions']))
    row('FW_W 110 미만 결정 비율 / 첫 T / 최장 연속', lambda r: '%s/%s/%s' % (f(r['vsl_stats']['FW_W']['frac_any_lt110'], 3),
                                                                   r['vsl_stats']['FW_W']['first_T'], r['vsl_stats']['FW_W']['longest_run_decisions']))
    row('110 미만 구역 노출 (veh·km)', lambda r: str({k: round(v, 1) for k, v in r['vsl_stats']['exposure_veh_km'].items()}) or '{}')
    row('미래 블록 1 / 2 FW_E 110 미만 T', lambda r: '%s / %s' % (r['vsl_stats']['FW_E']['future_blocks']['fut1']['any_lt110_T'],
                                                              r['vsl_stats']['FW_E']['future_blocks']['fut2']['any_lt110_T']))
    row('VSL 써진 행 (속도: 행)', lambda r: str(r['vsl_written_speed_rows']))
    T['METER_VSL'] = '\n'.join(lines)
    # DESSPEED (V-A only), two readings
    lines = ['| 시드 | 읽는 법 | 명령 c | 표지 통과 n / 띠 안 비율 | 상류 관측 없음 n / 띠 안 비율 |', '|---|---|---|---|---|']
    for s in S:
        d = L['desspeed']['s' + s]['by_level']
        for reading in ('C_command', 'M_written'):
            for c in sorted(d.get(reading, {}), key=float):
                g = d[reading][c]
                sp, nu = g.get('sign_passed', {}), g.get('no_upstream_obs', {})
                lines.append('| %s | %s | %s | %s / %s | %s / %s |' % (SN[s], reading, c, sp.get('n', 0), f(sp.get('frac_in_band'), 4),
                                                                   nu.get('n', 0), f(nu.get('frac_in_band'), 4)))
    T['DESSPEED'] = '\n'.join(lines)
    V.jdump(T, os.path.join(prof.out, 'va_tables.json'))
    print('tables', len(T))


if __name__ == '__main__':
    main()
