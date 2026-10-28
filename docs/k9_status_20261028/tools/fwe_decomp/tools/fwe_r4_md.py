# -*- coding: utf-8 -*-
"""fwe_r4_md.py - D-K9-106 R4 report writer. Every number comes from out/R4_codex.json or (marked [읽음]) A1_RESULT.md r2.
python -B fwe_r4_md.py  -> FD/R4_REPORT.md
"""
import hashlib, json, os, sys, time

sys.dont_write_bytecode = True
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
A1R = SP + '/codex_handoff/a1/A1_RESULT.md'
A1R_SHA = '0ef733fb2450c71925d6b2723c7446a7441d6bf5581a23d105d2523e095cc714'
PAIRS = ['Q-joint', 'Q-window', 'Q-off', 'Q-fw', 'Q-urb']
ARM = {'Q-joint': 'joint', 'Q-window': 'window', 'Q-off': 'off', 'Q-fw': 'freeway_only', 'Q-urb': 'urban_only'}
FWE_M = ['RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
FWW_M = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644']
RAMPS = ['10639', '10681', '10490', '10484']
EXITS = ['10643', '10682', '10481', '10483']
Z5 = ['U', 'B1', 'M', 'B2', 'D']
Z7 = ['U', 'B1', 'M1', 'Mu', 'VS0', 'B2', 'D']


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def f(v, nd=1, sign=True):
    if v is None:
        return '—'
    s = ('%+.' + str(nd) + 'f') % v if sign else ('%.' + str(nd) + 'f') % v
    if s in ('+0.0', '-0.0', '+0.00', '-0.00'):
        s = '0.0' if nd == 1 else '0.00'
    return s.replace('-', '−')


def win900(arr, mode='sum'):
    out = []
    for k in range(9):
        part = [x for x in arr[3 * k:3 * k + 3] if x is not None]
        if not part:
            out.append(None)
        elif mode == 'sum':
            out.append(sum(part))
        else:
            out.append(sum(part) / len(part))
    return out


def a1_table():
    if sha(A1R) != A1R_SHA:
        raise SystemExit('A1_RESULT changed')
    L = open(A1R, encoding='utf-8').read().splitlines()
    rows = {}
    for ln in L[254:276]:
        c = [x.strip() for x in ln.strip().strip('|').split('|')]
        if len(c) == 8:
            def num(s):
                s = s.replace('−', '-').replace('+', '').replace(',', '')
                try:
                    return float(s)
                except ValueError:
                    return None
            rows[c[0]] = {'A1-LNC': num(c[3]), 'joint-NC': num(c[6]), 'A1-joint': num(c[7])}
    return rows


def main():
    R = json.load(open(FD + '/out/R4_codex.json', encoding='utf-8'))
    rj_sha = sha(FD + '/out/R4_codex.json')
    A = a1_table()
    a1key = {'O701': 'Ω701', 'A4a': '④a 망 전체 링크', 'U': '④b 미삽입 (짝 차 = 첫 관측 차분)', 'A4': '④ = ④a + ④b',
             'outa701': 'Ω 밖 (a) Ω701 기준', 'outb701': 'Ω 밖 (b) Ω701 기준', 'FWE7': '① FW_E 본선 7링크', 'LOCAL19': '② 국소 19링크',
             'urban': '도시도로 (codex 분할)', 'link66': '링크 66', 'u1098': '④b 입력 1098 (FW_E 입구, 링크 74)',
             'u1099': '④b 입력 1099 (FW_W 입구, 링크 26)', 'ucity': '④b 도시 입력 합 (그 밖 링크)'}
    a4 = R['R4a']; P = R['physics_levels']; B = R['R4b']; M = R['meters']; C = R['checks']; D4 = R['R4d']; QV = R['QVSL64']
    have = {p: (ARM[p] in P) for p in PAIRS}
    o = []
    w = o.append
    w('# R4_REPORT — codex 분할 팔(64cf-s29) FW_E 분해 (D-K9-106 R4, %s KST)' % time.strftime('%Y-%m-%d %H:%M'))
    w('')
    w('- 무엇: `PRE_FWE.md` §5.4 R4 를 고정된 정의 그대로 셈한 결과입니다. 한 망(64cf)·한 시드(29)·조건마다 런 하나입니다. **v3c3 와 빼지 않습니다.** 판정 낱말은 쓰지 않습니다. 숫자는 모두 도구 출력(`out/R4_codex.json`)에서 채웠고, A1 총합 칸만 `A1_RESULT.md` r2 표에서 [읽음]으로 옮겼습니다.')
    w('- 근거 sha256: PRE_FWE `%s`, 도구 `tools/fwe_r4.py` `%s`, 이 글 도구 `tools/fwe_r4_md.py` `%s`, 출력 `out/R4_codex.json` `%s`, A1_RESULT r2 `%s`.' % (
        R['pre_fwe_sha256'], R['tool_sha256'], sha(os.path.abspath(__file__)), rj_sha, A1R_SHA))
    w('- 표시: **[실행]** 도구로 셈 · **[읽음]** 파일에서 옮김 · **[계산]** 이 글의 산술 · **[추론]** 시험하지 않은 판단.')
    w('- 이 차례에서 한 일: 캐시 JSON·정의 파일·provenance·미터 LDP(신호 상태 기록, 텍스트) 읽기. **FZP 를 직접 읽지 않았습니다.** 새 FZP 스캔(H4·H5)은 R3 차례가 공용 잠금 아래 돌린 출력을 FZP sha 를 다시 맞춘 뒤 썼습니다. VISSIM·COM·러너·동결·코드 변경·커밋 0. 봉인 시드·`sealed/` 0. kill 0.')
    w('')
    w('## 줄임말 (처음 한 번)')
    w('')
    w('- FW_E = 동측 고속도로, FW_W = 서측 고속도로. NC = 무제어 런. RM = 램프 미터. TSC = 도시 신호 제어. VSL = 가변 제한속도. LDP = VISSIM 신호 상태 초별 기록. FZP = VISSIM 차량 궤적 기록.')
    w('- ① = FW_E 본선 7링크(74·10699·2·10613·119·10702·24). ② = 동측 국소 19링크(① + 진입 커넥터 4 + 진출 커넥터 4 + 진입 접근 링크 4). 도시도로 = codex 분할(Ω701 − 양방향 본선 − 진입 커넥터 8 − Ω701 안 진출 커넥터). ④a = 망 전체 링크 체류. ④b = 미삽입 대기(첫 관측 차분). ④ = ④a + ④b. Ω 밖 (a) = ④ − Ω701, Ω 밖 (b) = ④a − Ω701.')
    w('- 팔(같은 64cf-s29): joint = RM+TSC+VSL 최적화. window = RM+TSC, seg13 시간창 VSL. off = RM+TSC, VSL 110 고정. freeway_only = VSL+RM, 자기 정보·고속도로 목적, 도시 native(100/90 VSL 도 골랐음 → 순수 RM 단독 아님). urban_only = TSC 만, VSL 110·미터 열림 [읽음 `SP/HANDOFF_codex_a49981ff.md:215-223`].')
    w('- 짝 이름: Q-joint = joint − NC, Q-window, Q-off, Q-fw = freeway_only − NC, Q-urb = urban_only − NC. NC 쪽: 링크 적분·첫 관측은 codex NC, 물리(fwe_scan)는 LNC(= 이 PC 의 64cf-s29 무제어, codex NC 와 같은 시뮬레이션). 미터는 codex NC 의 LDP.')
    w('- 구역(체인 m, 칸 가운데 기준): U 0–4,200 · B1 4,200–5,300 · M 5,300–6,800 · B2 6,800–7,900 · D 7,900–10,800. 보조 일곱 구역: U · B1 · M1 5,300–6,300 · Mu 6,300–6,700 · VS0 6,700–6,800 · B2 6,800–8,100 · D 8,100–10,800.')
    w('- 꼴: 총합 = codex 꼴 [0, 8100](빈 망에서 시작, 마지막 프레임 재고 유지). 구역·창 = bin 꼴(5 s 프레임 차량 수 × 5 s, 사각형). 두 꼴의 차는 양끝 프레임 몫뿐입니다(§1 S-4).')
    w('- "해석 단서" [읽음 PRE_FWE §5.4]: freeway_only 는 VSL 도 움직였고 목적·정보가 함께 달라 "미터 몫" 으로 읽지 않습니다. 팔 사이 차는 기구가 둘 이상 함께 달라진 한 시드 차입니다.')
    w('')
    # ---------------------------------------------------------------- 0
    w('## 0. 쉬운 요약')
    w('')
    jq = a4['Q-joint']
    w('1. [실행] 점검 통과: 시드는 9런 모두 provenance 29, 망은 결정 폴더가 있는 7런이 `64cf5f55…`. Ω701·①·② 수준이 codex 표와 최대 %.1e veh·h 안(S-5), codex NC 와 LNC 링크 적분 차 최대 %s(S-5). joint − NC 를 다시 내면 Ω701 %s, ④ %s, ① %s, ② %s, 도시도로 %s, ④b 1098 %s 로 HANDOFF_RESULTS r2 §1.1 과 같습니다.' % (
        max(abs(v) for r in C['S5']['level_diffs'].values() for k, v in r.items() if '보고만' not in k), C['S5']['nc_vs_lnc_link_max_abs'],
        f(jq['O701']), f(jq['A4']), f(jq['FWE7']), f(jq['LOCAL19']), f(jq['urban']), f(jq['u1098'])))
    rows = []
    for p in PAIRS:
        d = a4[p]
        rows.append('%s ① %s · ② %s · 도시도로 %s · Ω701 %s · ④ %s · Ω 밖 (a) %s' % (ARM[p], f(d['FWE7']), f(d['LOCAL19']), f(d['urban']), f(d['O701']), f(d['A4']), f(d['outa701'])))
    w('2. [실행] 팔 − NC (codex 꼴 0–8,100 s, veh·h): ' + ' / '.join(rows) + '. 전체 표는 §2.')
    zs = []
    for p in PAIRS:
        if have[p]:
            zs.append('%s: ' % ARM[p] + ', '.join('%s %s' % (z, f(B[p]['zones5'][z]['d_veh_h_total'])) for z in Z5))
    w('3. [실행] ① 차의 구역 나눔(bin 꼴): ' + ' / '.join(zs) + '. 제어 네 팔(joint·window·off·freeway_only)의 ① 감소는 B1·M 두 구역에 몰립니다 [계산 위 값].')
    sp = P['lnc']['spill']
    sp_txt = ', '.join('%s B1 %d·M %d' % (r, P[r]['spill']['b1_spill_min_lt4500'], P[r]['spill']['m_spill_min_lt6800']) for r in ['joint', 'window', 'off', 'freeway_only', 'urban_only'] if r in P)
    w('4. [실행] 번짐 분(0–8,100 s, 60 s 창 수): NC(LNC) B1 %d·M %d. 팔: %s.' % (sp['b1_spill_min_lt4500'], sp['m_spill_min_lt6800'], sp_txt))
    mt = []
    for r in ['joint', 'window', 'off', 'freeway_only', 'urban_only', 'nc']:
        mt.append('%s ' % ('codex NC' if r == 'nc' else r) + '/'.join('%d' % M[r][m]['n_tight10'] for m in FWE_M))
    w('5. [실행] FW_E 미터 넷(10639/10681/10490/10484)의 GREEN < 10 주기 수(900–8,100 s, 720 주기 중): ' + ' · '.join(mt) + '. 조인 팔은 모두 900 s 첫 주기부터 조였습니다. urban_only 와 NC 는 모든 주기 GREEN 10 입니다. LDP 와 명령(150 s 칸)의 차 > 0.5 s 칸은 모든 팔에서 0 입니다.')
    mg = []
    for p in PAIRS:
        if have[p]:
            mg.append('%s ' % ARM[p] + '/'.join('%+d' % B[p]['ramps'][r]['merge_veh_900_8100_d'] for r in RAMPS))
    w('6. [실행] 합류 대수 차(900–8,100 s, 10639/10681/10490/10484): ' + ' · '.join(mg).replace('-', '−') + '. 연결로+접근 링크 재고 차(veh·h): ' + ' · '.join(
        '%s ' % ARM[p] + '/'.join(f(B[p]['ramps'][r]['stock_veh_h_total_d']) for r in RAMPS) for p in PAIRS if have[p]) + '.')
    if have['Q-urb']:
        bu = B['Q-urb']
        pu = P['urban_only']
        w('7. [실행] urban_only(미터 열림 = 모든 주기 GREEN 10, VSL 110, 도시 신호만 제어)는 ① %s 이고, 구역으로는 %s 입니다. 번짐 분은 B1 %d·M %d(NC 62·19), B1 꼬리 최상류 %s m(%s s) 입니다. 합류 대수 차는 %s, 10643 진출 커넥터 재고 차는 %s veh·h 입니다(§7). 같은 팔의 도시도로는 %s 입니다.' % (
            f(a4['Q-urb']['FWE7']), ', '.join('%s %s' % (z, f(bu['zones5'][z]['d_veh_h_total'])) for z in Z5),
            pu['spill']['b1_spill_min_lt4500'], pu['spill']['m_spill_min_lt6800'], pu['spill']['b1_tail_min_m'], pu['spill']['b1_tail_min_at_s'],
            ', '.join('%s %+d' % (r, bu['ramps'][r]['merge_veh_900_8100_d']) for r in RAMPS).replace('-', '−'),
            f(sum(bu['offramps']['10643']['stock_veh_h_300_d'])), f(a4['Q-urb']['urban'])))
        fw = a4['Q-fw']
        w('7b. [실행] 감시 칸: freeway_only 는 ① %s 인데 FW_W 본선 %s, ④b 1099 %s 라서 Ω701 %s, ④ %s, Ω 밖 (a) %s 입니다. FW_W 는 개선 대상이 아니라 감시만 하므로 여기서는 숫자만 적습니다.' % (
            f(fw['FWE7']), f(fw['FWW3']), f(fw['u1099']), f(fw['O701']), f(fw['A4']), f(fw['outa701'])))
    else:
        w('7. urban_only 의 FW_E 물리(구역·번짐·합류)는 H4 출력이 없어 **못 냄** 입니다(§8).')
    w('8. [읽음 A1_RESULT r2 :255-276] 흔들림 잣대 A1 − joint(같은 시드·같은 코드, 수치 경로만 다름): Ω701 %s, ④ %s, ① %s, ② %s, 도시도로 %s. [실행] 같은 두 런의 구역 차: %s. 팔끼리의 차를 읽을 때 이 크기를 옆에 둡니다.' % (
        f(A['Ω701']['A1-joint']), f(A['④ = ④a + ④b']['A1-joint']), f(A['① FW_E 본선 7링크']['A1-joint']), f(A['② 국소 19링크']['A1-joint']),
        f(A['도시도로 (codex 분할)']['A1-joint']), ', '.join('%s %s' % (z, f(D4['physics']['zones5'][z]['d_veh_h_total'])) for z in Z5)))
    w('9. [추론] 나란히(빼지 않음): 64cf NC 는 B1 번짐 %d 분·M %d 분이고, PRE §4.3 이 적은 v3c3 NC3 는 B1 0/0/2 분·M 0/12/3 분입니다. 64cf 의 ① 감소가 몰린 B1·M 은 NC 에서 번짐이 컸던 곳입니다. v3c3 는 같은 구역의 번짐이 작습니다. 이것은 두 망의 무제어 상태를 나란히 둔 것이고, v3c3 에서 같은 기구가 같은 크기로 움직인다는 뜻이 아닙니다.' % (sp['b1_spill_min_lt4500'], sp['m_spill_min_lt6800']))
    w('')
    # ---------------------------------------------------------------- 1 checks
    w('## 1. 점검 (멈춤 규칙)')
    w('')
    w('| 규칙 | 내용 | 값 | 결과 |')
    w('|---|---|---|---|')
    s2 = C['S2']
    w('| S-2 | provenance 시드·망 | 시드 %s; inpx %s | %s |' % (', '.join('%s=%s' % (k, v['seed']) for k, v in s2.items()),
                                                         ', '.join('%s=%s' % (k, (v['inpx_sha256'] or '기록 없음')[:8]) for k, v in s2.items()), '통과' if all(v['ok'] for v in s2.values()) else '멈춤'))
    w('| S-2 보조 | 895.1 s 접두 LF 해시(vhr 스캔) | 7런 모두 같음 = %s | %s |' % (str(C['prefix_895_1_equal']['all_equal']), '통과' if C['prefix_895_1_equal']['all_equal'] else '확인'))
    w('| 같은 도착열 | 링크 74 첫 관측 수(≤ 8,100 s) | %s | 모두 같음 = %s |' % (', '.join('%s %d' % (k, v) for k, v in C['first74_le_8100'].items()), len(set(C['first74_le_8100'].values())) == 1))
    w('| S-5 | Ω701·①·② 수준 − codex 표(metrics_0_8100.csv, independent_fzp_counts.json) | 최대 |차| %.2e veh·h | %s |' % (
        max(abs(v) for r in C['S5']['level_diffs'].values() for k, v in r.items() if '보고만' not in k), '통과' if C['S5']['ok'] else '멈춤'))
    w('| S-5 | codex NC − LNC 링크 적분(codex 꼴 8100) | 링크별 최대 |차| %s | %s |' % (C['S5']['nc_vs_lnc_link_max_abs'], '통과' if C['S5']['nc_vs_lnc_link_max_abs'] <= 1e-6 else '멈춤'))
    w('| S-5 보조(보고만) | 도시도로·진입 E·진출 수준 − codex 표 | 최대 |차| %.2e | 보고 |' % max(abs(v) for r in C['S5']['level_diffs'].values() for k, v in r.items() if '보고만' in k))
    w('| 보고 | FW_W 본선 26·10771·120 − codex summary FW_W | 최대 |차| %.2e | 보고 |' % max(abs(v) for v in C['fww3_vs_codex_summary'].values()))
    s4 = C['S4b']['diffs']
    w('| S-4 (나) | codex 꼴 총합 − bin 꼴 합 (①, ②) | %s | %s |' % ('; '.join('%s %s/%s' % (k, f(v['FWE7_codex_minus_bin'], 2), f(v['LOCAL19_codex_minus_bin'], 2)) for k, v in s4.items()), '통과(≤ 1.0)' if C['S4b']['ok'] else '멈춤'))
    w('| S-8 | fwe_scan 체인 칸 합 = linkbin ① (300 s 칸, 차량-프레임) | %s | 보고 |' % '; '.join('%s 최대 차 %d' % (k, v['fwe7_max_abs_vf']) for k, v in C['linkbin_xcheck'].items()))
    w('| R3-d 대조 | fwe_scan 연결로+접근 재고·대기 = linkbin vf·qf (300 s 칸) | %s | 보고 |' % '; '.join('%s 재고 %d·대기 %d' % (k, v['ramp_stock_max_abs_vf'], v['ramp_queue_max_abs_vf']) for k, v in C['linkbin_xcheck'].items()))
    w('| S-14 | 900 s 전 창 ② |d| 합 | %s | 보고 |' % '; '.join('%s %s' % (p, f(B[p]['S14_pre900_abs_local19'], 3, False)) for p in PAIRS if have[p]))
    hv = R['heavy_inputs']
    def s1(v):
        if v.get('S1_ok'):
            return '일치(%s, %s)' % (v['fzp_sha256'][:8], v['fzp_sha_source'])
        if v.get('why'):
            return '안 받음'
        return '불일치'
    w('| S-1 | 새 스캔(H4·H5) 출력의 FZP sha256 = 목록 sha | %s | %s |' % ('; '.join('%s %s' % (k, s1(v)) for k, v in hv.items()),
                                                                 '멈춤' if any(s1(v) == '불일치' for v in hv.values()) else '통과'))
    w('| 멈춤 기록 | 도구가 적은 stops | %s | — |' % (json.dumps(R['stops'], ensure_ascii=False) if R['stops'] else '없음'))
    w('')
    w('- [실행] codex NC 와 LNC 의 미터 LDP 는 다릅니다: codex NC 는 FW_E·FW_W 미터 8개가 모든 주기 GREEN 10, LNC·vsl_repro 는 상태 칸이 빈칸뿐(`I` 0개)입니다(`checks/nc_ldp_eq_lnc_ldp` 모두 거짓). 두 런의 FZP 링크 적분은 같으므로(S-5) [추론] 빈칸(신호 꺼짐)과 GREEN 은 교통에 같은 몫이었습니다. GREEN 만 세는 규칙으로 LNC·vsl_repro 의 미터는 "GREEN 0" 이 되므로, **이 둘의 미터 칸은 "기록 없음(빈칸)" 으로 적고 조임으로 읽지 않습니다.** 64cf 짝의 NC 미터는 codex NC LDP 를 씁니다.')
    w('')
    # ---------------------------------------------------------------- 2 R4-a
    w('## 2. R4-a 팔별 짝 차 (codex 꼴 [0, 8100], veh·h)')
    w('')
    w('- 열: 다섯 Q 짝 [실행]. ‖ 오른쪽은 따로: Q-A1 = A1 − LNC, A1 − joint (총합은 [읽음 A1_RESULT r2 :255-276], 새로 세지 않음), Q-VSL64 = vsl_repro vsl − LNC (**bin 꼴**, 참고).')
    w('- ④b 는 첫 관측 차분(vhr_unins.py 규칙). 입력별 칸은 첫 관측 링크로 나눔(74 = 1098, 26 = 1099, 그 밖 = 도시). FW_W 본선·④b 1099 는 **감시 칸**입니다.')
    w('')
    rowsdef = [('FWE7', '① FW_E 본선 7링크'), ('LOCAL19', '② 동측 국소 19링크'), ('urban', '도시도로 (codex 분할)'), ('O701', 'Ω701'),
               ('A4a', '④a 망 전체 링크'), ('U', '④b 미삽입 (첫 관측 차분)'), ('u1098', '④b 중 입력 1098 (FW_E 입구)'), ('ucity', '④b 중 도시 입력'),
               ('A4', '④ = ④a + ④b'), ('outa701', 'Ω 밖 (a) ④ − Ω701'), ('outb701', 'Ω 밖 (b) ④a − Ω701'), ('link66', '링크 66'),
               ('FWW3', '감시: FW_W 본선 26·10771·120'), ('u1099', '감시: ④b 중 입력 1099 (FW_W 입구)')]
    w('| d (veh·h) | ' + ' | '.join(PAIRS) + ' | NC 수준 | ‖ Q-A1 [읽음] | A1 − joint [읽음] | Q-VSL64 (bin 꼴) |')
    w('|---|' + '---:|' * (len(PAIRS) + 4))
    nc = a4['_nc_levels']
    for k, name in rowsdef:
        ak = a1key.get(k)
        a1v = A.get(ak, {}) if ak else {}
        ncv = nc.get(k) if k in nc else None
        w('| %s | %s | %s | %s | %s | %s |' % (name, ' | '.join(f(a4[p].get(k)) for p in PAIRS), f(ncv, 1, False) if ncv is not None else '—',
                                             f(a1v.get('A1-LNC')) if a1v else '표에 없음', f(a1v.get('A1-joint')) if a1v else '표에 없음', f(QV.get(k))))
    w('')
    w('- [실행] 보조(같은 꼴): 진입 E 커넥터 4 %s, 진입 W 커넥터 4 %s, Ω701 안 진출 커넥터 6 %s (Q-joint … Q-urb 순서).' % (
        ' / '.join(f(a4[p]['onramps_E']) for p in PAIRS), ' / '.join(f(a4[p]['onramps_W']) for p in PAIRS), ' / '.join(f(a4[p]['offramps701']) for p in PAIRS)))
    w('- [실행] 같은 두 런의 첫 관측 차분을 이 도구로 다시 내면 A1 − joint ④b %s(A1_RESULT −13.8), A1 − LNC %s(A1_RESULT −235.1)입니다.' % (f(D4['U_first_seen'], 2), f(D4['A1_minus_LNC_U_first_seen'], 2)))
    w('- [계산] 표 안의 산술: ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω701, Ω 밖 (b) = ④a − Ω701 (도구가 같은 식으로 냄).')
    w('')
    # ---------------------------------------------------------------- 3 R4-b
    w('## 3. R4-b FW_E 물리 (팔 − NC(LNC), bin 꼴, 0–8,100 s)')
    w('')
    w('### 3.1 구역 총합: d veh·h 와 d 평균 속도 (km/h)')
    w('')
    runs_b = [p for p in PAIRS if have[p]] + ['A1 − joint', 'Q-VSL64']
    w('| 짝 | ' + ' | '.join('%s veh·h' % z for z in Z5) + ' | 구역 합 = ① bin 꼴 | ' + ' | '.join('%s 속도' % z for z in Z5) + ' |')
    w('|---|' + '---:|' * 11)
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('| %s | %s | %s | %s |' % (p, ' | '.join(f(d['zones5'][z]['d_veh_h_total']) for z in Z5), f(sum(d['bins']['fwe7_d_300'])),
                                     ' | '.join(f(d['zones5'][z]['d_speed_total']) for z in Z5)))
    w('| NC(LNC) 수준 | %s | %s | %s |' % (' | '.join(f(P['lnc']['zones5'][z]['veh_h_total'], 1, False) for z in Z5), f(P['lnc']['bins']['fwe7_bin_total'], 1, False),
                                           ' | '.join(f(P['lnc']['zones5'][z]['speed_total'], 1, False) for z in Z5)))
    w('')
    w('- 보조 일곱 구역 d veh·h:')
    w('')
    w('| 짝 | ' + ' | '.join(Z7) + ' |')
    w('|---|' + '---:|' * 7)
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('| %s | %s |' % (p, ' | '.join(f(d['zones7'][z]['d_veh_h_total']) for z in Z7)))
    w('')
    w('### 3.2 구역 d veh·h × 900 s 창 (JSON 은 300 s)')
    w('')
    hdr = ['%d–%d' % (900 * k, 900 * k + 900) for k in range(9)]
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('- %s' % p)
        w('')
        w('| 구역 | ' + ' | '.join(hdr) + ' |')
        w('|---|' + '---:|' * 9)
        for z in Z5:
            w('| %s | %s |' % (z, ' | '.join(f(v) for v in win900(d['zones5'][z]['d_veh_h_300']))))
        w('| ① 합 | %s |' % ' | '.join(f(v) for v in win900(d['bins']['fwe7_d_300'])))
        w('')
    w('### 3.3 번짐 분·혼잡 분 (0–8,100 s, 수준)')
    w('')
    w('| 런 | B1 번짐 분 | M 번짐 분 | B1 꼬리 최상류 m (시각 s) | B2 꼬리 최상류 m (시각 s) | 혼잡 분 U | B1 | M | B2 | D |')
    w('|---|---:|---:|---|---|---:|---:|---:|---:|---:|')
    for r in ['lnc', 'joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1', 'vsl']:
        if r not in P:
            w('| %s | 못 냄 | | | | | | | | |' % r); continue
        s = P[r]['spill']; c = P[r]['cong_min5']
        w('| %s | %d | %d | %s (%s) | %s (%s) | %s |' % ('NC(LNC)' if r == 'lnc' else ('vsl_repro vsl' if r == 'vsl' else r), s['b1_spill_min_lt4500'], s['m_spill_min_lt6800'],
                                                      s['b1_tail_min_m'], s['b1_tail_min_at_s'], s['b2_tail_min_m'], s['b2_tail_min_at_s'], ' | '.join(str(c[z]) for z in Z5)))
    w('')
    lf = P['lnc']['spill_full_0_9000']
    w('- [실행] LNC 0–9,000 s 전체로 다시 내면 B1 꼬리 %s m (%s s), B1 번짐 %s 분, B2 꼬리 %s m, M 번짐 %s 분이고, `INV_PHYSICS.md:96` 의 64cf-s29 NC 줄(3,300 (5,160 s) | 62 | 3,800 | 19)과 같습니다 [읽음 그 줄].' % (
        lf['b1_tail_min_m'], lf['b1_tail_min_at_s'], lf['b1_spill_min_lt4500'], lf['b2_tail_min_m'], lf['m_spill_min_lt6800']))
    w('')
    w('### 3.4 합류 유량 차 (veh/h, 900 s 창 평균) 와 합류 대수 차')
    w('')
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('- %s (900–8,100 s 합류 대수 차: %s)' % (p, ', '.join('%s %+d' % (r, d['ramps'][r]['merge_veh_900_8100_d']) for r in RAMPS).replace('-', '−')))
        w('')
        w('| 합류 | ' + ' | '.join(hdr) + ' |')
        w('|---|' + '---:|' * 9)
        for r in RAMPS:
            w('| %s | %s |' % (r, ' | '.join(f(v, 0) for v in win900(d['ramps'][r]['merge_vph_300_d'], 'mean'))))
        w('')
    w('### 3.5 연결로+접근 링크 재고·대기 차 (veh·h, 0–8,100 s 합) 와 창 최대 대기 대수')
    w('')
    w('| 짝 | ' + ' | '.join('%s 재고' % r for r in RAMPS) + ' | ' + ' | '.join('%s 대기(<15)' % r for r in RAMPS) + ' |')
    w('|---|' + '---:|' * 8)
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('| %s | %s | %s |' % (p, ' | '.join(f(d['ramps'][r]['stock_veh_h_total_d']) for r in RAMPS), ' | '.join(f(d['ramps'][r]['queued_veh_h_total_d']) for r in RAMPS)))
    w('')
    w('| 런 | ' + ' | '.join('%s 최대 대기 대수' % r for r in RAMPS) + ' |')
    w('|---|' + '---:|' * 4)
    for r in ['lnc', 'joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1', 'vsl']:
        if r in P:
            w('| %s | %s |' % (r, ' | '.join(str(max(P[r]['ramps'][x]['qmax_300'])) for x in RAMPS)))
    w('')
    # ---------------------------------------------------------------- 4 R4-c
    w('## 4. R4-c 미터 (LDP, GREEN 상태 초만, 10 s 주기 900–8,100 s = 720 주기)')
    w('')
    w('- 규칙 [읽음 `CW/rawcheck/rm_exec.py:14-23`, PRE §7.4]: 주기 [c, c+10) 의 c+1.0 … c+10.0 초 상태가 `I` 인 초 수. 노랑·적색·빈칸은 GREEN 아님. 명령 대조 = 150 s 결정 칸마다 명령 GREEN 초와 LDP 주기 평균의 차 > 0.5 s 인 칸 수(명령 원천: codex 팔·NC = `H/derived/decision_greens.csv`, A1 = 자기 action CSV).')
    w('')
    w('| 런 | 미터 | GREEN<10 주기 | GREEN≤6 주기 | T_tight10 s | T_tight6 s | GREEN 초 합 | GREEN 0–3 / 4–6 / 7–9 / 10 주기 | 명령 칸 · 명령<10 · 차>0.5 | 본 상태 글자 |')
    w('|---|---|---:|---:|---:|---:|---:|---|---|---|')
    for r in ['nc', 'joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1', 'lnc', 'vsl']:
        for m in FWE_M:
            x = M[r][m]
            h = x['green_hist']
            hb = '%d / %d / %d / %d' % (sum(h[str(i)] for i in range(0, 4)), sum(h[str(i)] for i in range(4, 7)), sum(h[str(i)] for i in range(7, 10)), h['10'])
            cm = x.get('cmd')
            cms = '%d · %d · %d' % (cm['intervals'], cm['cmd_lt10'], cm['mismatch_gt0p5']) if cm else '명령 없음'
            blank = x['states_seen'] == [' ']
            name = {'nc': 'codex NC', 'lnc': 'LNC', 'vsl': 'vsl_repro vsl'}.get(r, r)
            if blank:
                w('| %s | %s | 기록 없음(빈칸) | — | — | — | — | — | %s | 빈칸만 |' % (name, m, cms))
            else:
                w('| %s | %s | %d | %d | %s | %s | %d | %s | %s | %s |' % (name, m, x['n_tight10'], x['n_tight6'], x['T_tight10'] if x['T_tight10'] is not None else '조임 없음',
                                                                    x['T_tight6'] if x['T_tight6'] is not None else '조임 없음', x['green_sum_s'], hb, cms,
                                                                    ' '.join(repr(s) for s in x['states_seen'])))
    w('')
    w('- 900 s 창별 조인 주기 몫(GREEN < 10 주기 / 30 의 평균):')
    w('')
    w('| 런 · 미터 | ' + ' | '.join(hdr[1:]) + ' |')
    w('|---|' + '---:|' * 8)
    for r in ['joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1']:
        for m in FWE_M:
            sh = win900(M[r][m]['tight10_share_300'], 'mean')[1:]
            w('| %s · %s | %s |' % (r, m, ' | '.join(f(v, 2, False) for v in sh)))
    w('')
    w('- 감시 칸 FW_W 미터(GREEN<10 주기 수, 10480/10482/10646/10644): ' + ' · '.join('%s %s' % ({'nc': 'codex NC'}.get(r, r), '/'.join(
        ('빈칸' if M[r][m]['states_seen'] == [' '] else str(M[r][m]['n_tight10'])) for m in FWW_M)) for r in ['nc', 'joint', 'window', 'off', 'freeway_only', 'urban_only', 'a1', 'lnc', 'vsl']) + '.')
    w('')
    # ---------------------------------------------------------------- 5 R4-d
    w('## 5. R4-d 흔들림 잣대 A1 − joint')
    w('')
    w('- [읽음 A1_RESULT r2 :255-276] 총합 칸: ' + ', '.join('%s %s' % (k, f(v['A1-joint'])) for k, v in A.items()) + '.')
    w('- [읽음 A1_RESULT r2 §0-3·5] 두 런은 T = 1,200 s 결정부터 다르고, FZP 는 1,240.1 s 에 처음 갈립니다. 그 뒤 차는 두 단일 궤적의 차입니다.')
    dd = D4['physics']
    w('- [실행] 같은 두 런의 물리 차(§3 표의 "A1 − joint" 줄): ' + ('구역 %s; 번짐 분 B1 %s·M %s; 합류 대수 %s.' % (
        ', '.join('%s %s' % (z, f(dd['zones5'][z]['d_veh_h_total'])) for z in Z5), '%+d' % dd['spill']['b1_spill_min_lt4500'], '%+d' % dd['spill']['m_spill_min_lt6800'],
        ', '.join('%s %+d' % (r, dd['ramps'][r]['merge_veh_900_8100_d']) for r in RAMPS))).replace('-', '−'))
    w('- [실행] 미터: A1 과 joint 의 FW_E 미터 GREEN<10 주기 수 ' + ', '.join('%s %d/%d' % (m, M['a1'][m]['n_tight10'], M['joint'][m]['n_tight10']) for m in FWE_M) +
      '; GREEN 초 합 ' + ', '.join('%s %d/%d' % (m, M['a1'][m]['green_sum_s'], M['joint'][m]['green_sum_s']) for m in FWE_M) + ' (A1/joint).')
    w('')
    # ---------------------------------------------------------------- 6 R4-e
    w('## 6. R4-e 대조 (codex 표)')
    w('')
    w('| 런 | Ω701 차 | ①(FW_E_7) 차 | ②(local_19) 차 | 원천 |')
    w('|---|---:|---:|---:|---|')
    for r, v in C['S5']['level_diffs'].items():
        w(('| %s | %.2e | %.2e | %.2e | %s |' % (r, v['Omega701'], v['FW_E_7'], v['local_19'], 'metrics_0_8100.csv' if r in ('nc', 'joint', 'freeway_only', 'urban_only') else 'independent_fzp_counts.json')).replace('e-', 'e−').replace('| -', '| −'))
    w('')
    # ---------------------------------------------------------------- 7 after data
    w('## 7. 데이터 뒤 (PRE §5.4 목록 밖, 보고만 — 깃발·기준 줄에 쓰지 않음)')
    w('')
    w('- 진출 커넥터 재고 차 (veh·h, 0–8,100 s 합; PRE 에 정의는 있음(R1-g·R3-g·RF8) 이나 R4-b 목록 밖):')
    w('')
    w('| 짝 | ' + ' | '.join('%s 재고' % e for e in EXITS) + ' | ' + ' | '.join('%s 대기(<15)' % e for e in EXITS) + ' |')
    w('|---|' + '---:|' * 8)
    for p in runs_b:
        d = B[p] if p in B else (D4['physics'] if p == 'A1 − joint' else QV['physics'])
        w('| %s | %s | %s |' % (p, ' | '.join(f(sum(d['offramps'][e]['stock_veh_h_300_d'])) for e in EXITS), ' | '.join(f(sum(d['offramps'][e]['queued_veh_h_300_d'])) for e in EXITS)))
    w('')
    w('- [실행] NC(LNC) 진출 커넥터 재고 수준(veh·h): ' + ', '.join('%s %s' % (e, f(sum(P['lnc']['offramps'][e]['stock_veh_h_300']), 1, False)) for e in EXITS) + '.')
    w('- [계산] 팔끼리 ① 차를 표에서 읽으면(같은 NC 를 뺀 값끼리): ' + ', '.join('%s − joint %s' % (ARM[p], f(a4[p]['FWE7'] - a4['Q-joint']['FWE7'])) for p in PAIRS[1:]) +
      '. 같은 자리의 A1 − joint 는 ① %s 입니다 [읽음]. 이 차들은 기구가 둘 이상 함께 달라진 한 시드 차입니다.' % f(A['① FW_E 본선 7링크']['A1-joint']))
    w('')
    # ---------------------------------------------------------------- 8 open
    w('## 8. 못 낸 것·모름')
    w('')
    for x in R['not_produced']:
        w('- 못 냄: %s' % x)
    w('- 못 냄(선택): Q-hist(옛 ALINEA·VSL90 팔) — H13–H16 을 돌리지 않았습니다.')
    w('- [추론] 64cf 한 시드·조건마다 런 하나라 런 사이 흔들림은 A1 − joint 한 표본뿐입니다(PRE §12-1).')
    w('- [추론] 미터 LDP 는 신호 상태입니다. 그 GREEN 동안 차가 실제로 지났는지는 합류 유량(§3.4)으로만 봅니다(PRE §12-2).')
    w('- [추론] 진출 커넥터 재고 변화가 도시 신호 몫인지는 이 질문 밖입니다(PRE §12-3).')
    w('')
    w('## 9. 산출물')
    w('')
    w('- `out/R4_codex.json` sha256 `%s` (300 s 창 값·미터 주기 표·점검 모두 포함).' % rj_sha)
    w('- 입력 sha256 은 JSON `/inputs` 에 모두 있습니다(%d 파일).' % len(R['inputs']))
    open(FD + '/R4_REPORT.md', 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print('md written', len(o))


if __name__ == '__main__':
    main()
