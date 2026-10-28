# Build markdown table fragments for B_RUNS.md from work/b/b_run_summary_s<seed>.json and work/b/b_concurrency.json (read-only).
# usage: python -B b_runs_tables.py <out.md>
import json, sys
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/b'
S = (31, 41, 43)
D = {s: json.load(open(W + '/b_run_summary_s%d.json' % s, encoding='utf-8')) for s in S}
C = json.load(open(W + '/b_concurrency.json', encoding='utf-8'))
out = []


def f1(x):
    return '%.1f' % x


out.append('### T1. 결정 벽시계 (T ≥ 900, 제어 결정 55개; 단위 s)')
out.append('')
out.append('| 시드 | n | 평균 | 중앙 | p90 | 최소 | 최대 (T) | > 360 | > 1,500 | > 1,800 | > 2,400 | exit ≠ 0 | 유지 |')
out.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for s in S:
    w = D[s]['runlog']['wall_ge900']
    out.append('| v3c3-s%d | %d | %s | %s | %s | %s | %s (%s) | %d | %d | %d | %d | %d | %d |' % (
        s, w['n'], f1(w['mean']), f1(w['median']), f1(w['p90']), f1(w['min']), f1(w['max']), ','.join(str(t) for t in w['max_at']),
        w['gt360'], w['gt1500'], w['gt1800'], w['gt2400'], len(w['exit_nonzero']), len(D[s]['runlog']['held_previous'])))
out.append('')
out.append('### T2. 결정 벽시계와 동시 상황 (b_concurrency.json; 단위 s)')
out.append('')
out.append('| 시드 | 남의 VISSIM 있음: n · 평균 · 최대 | 없음: n · 평균 · 최대 | 모름: n · 평균 | 함께 돈 B 결정 수(시간 가중 평균): 평균 · 최소 · 최대 |')
out.append('|---|---|---|---|---|')
for s in S:
    m = C['summary']['s%d' % s]
    y, n, u, c = m['other_vissim_yes'], m['other_vissim_no'], m['other_vissim_unknown'], m['mean_concurrent_b']
    out.append('| v3c3-s%d | %d · %s · %s | %d · %s · %s | %d · %s | %s · %s · %s |' % (
        s, y['n'], f1(y['mean']), f1(y['max']), n['n'], f1(n['mean']), f1(n['max']), u['n'], f1(u['mean']), f1(c['mean']), f1(c['min']), f1(c['max'])))
out.append('')
out.append('### T3. 미터 명령 녹색(초) 분포 — 명령 CSV, T = 900–9,000 (55개 결정 시각). 칸 = 녹색:결정 수')
out.append('')
meters = sorted(D[31]['action_csv']['meter_rate_green_counts'])
out.append('| 미터 | ' + ' | '.join('v3c3-s%d' % s for s in S) + ' |')
out.append('|---|' + '---|' * len(S))
for mt in meters:
    cells = []
    for s in S:
        d = D[s]['action_csv']['meter_rate_green_counts'].get(mt, {})
        g = {}
        for k, v in d.items():
            rate, green = k.split('/')
            g[float(green)] = g.get(float(green), 0) + v
        cells.append(' · '.join('%g:%d' % (k, g[k]) for k in sorted(g)))
    out.append('| %s | %s |' % (mt, ' | '.join(cells)))
out.append('')
out.append('- 명령 CSV 의 rate_vph 는 모든 행에서 녹색 × 90 입니다(위 칸의 원래 키 `rate/green`).')
out.append('')
out.append('### T4. 결정 JSON 의 미터 rate(`rm_out`, dec_extract_b, T = 900–8,850, 54개) — 칸 = rate:결정 수')
out.append('')
out.append('| 미터 | ' + ' | '.join('v3c3-s%d' % s for s in S) + ' |')
out.append('|---|' + '---|' * len(S))
for mt in meters:
    cells = []
    for s in S:
        d = D[s]['dec_tool']['rm_out_counts'].get(mt, {})
        cells.append(' · '.join('%s:%d' % (k, d[k]) for k in sorted(d, key=float)))
    out.append('| %s | %s |' % (mt, ' | '.join(cells)))
out.append('')
out.append('### T5. 접두(≤ 895.1 s) 짝 점검 — vhr_scan_b `lf_sha_le_895_1`, a1_fzp_firstdiff_b')
out.append('')
out.append('| 시드 | B 접두 sha (행 수) | NC3 접두 sha (행 수) | B = NC3 | B = V-A | B 첫 프레임 · 0.1 s 행 | B−NC3 처음 다른 프레임 · 그 내용 | B−NC3 다른 프레임 중 ≤ 900 s | B−NC3 그다음 다른 프레임 | B−V-A 처음 다른 프레임 |')
out.append('|---|---|---|---|---|---|---|---|---|---|')
for s in S:
    p = D[s]['prefix_vhr']
    fz = {q['pair']: q for q in D[s]['fzp_firstdiff_tool']}
    full = json.load(open('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/rawcheck_b/s%d/fzp_firstdiff_s%d.json' % (s, s), encoding='utf-8'))
    blocks = {q['pair']: q['blocks'] for q in full['pairs']}
    bj = blocks['a1-joint']
    le900 = sum(v['frames_differing'] for k, v in bj.items() if int(k) < 900)
    nxt = min(int(k) for k in bj if int(k) >= 900)
    a = fz['a1-joint']; fd = a['first_diff']
    what = 'B 에만 %d대, NC3 에만 %d대, 다른 행 %d대, 링크 %s' % (fd['only_a'], fd['only_b'], fd['changed'], ','.join('%s×%d' % (l, n) for l, n in fd['links_top'][:3]))
    out.append('| v3c3-s%d | `%s…` (%d) | `%s…` (%d) | %s | %s | %s s · %s | %s s · %s | %d | 블록 %d–%d s 안 (%d 프레임) | %s s |' % (
        s, p['b_lf_sha_le_895_1'][:8], p['b_rows_le_895_1'], p['nc3_lf_sha_le_895_1'][:8], p['nc3_rows_le_895_1'],
        '같음' if p['equal_b_nc3'] else '다름', '같음' if p['equal_b_va'] else '다름', p['b_first_frame_s'], '있음' if p['b_has_0p1_frame'] else '없음',
        a['first_diff_t'], what, le900, nxt, nxt + 150, bj[str(nxt)]['frames_differing'], fz['a1-lnc']['first_diff_t']))
out.append('')
out.append('### T6. 런 끝 기록')
out.append('')
out.append('| 시드 | STAGE | SIM_SEC | DECISIONS_OK / FAILED / HELD_PREVIOUS / HELD_ON_EXCEPTION | 결정 줄 수 (워밍업 T<900 / 제어 T≥900) | 러너 종료 · 래퍼 벽시계 | native_status | 런 로그 .err | FZP 바이트 · 데이터 행 |')
out.append('|---|---|---|---|---|---|---|---|---|')
for s in S:
    r = D[s]['runlog']; w = D[s]['wrapper'].get('wrapper_run1_try1_end.json', {}); p = D[s]['prefix_vhr']
    out.append('| v3c3-s%d | %s | %s | %s / %s / %s / %s | %d (%d / %d) | %s · %s s | %s | %s B | %s · %s |' % (
        s, r['stage_lines'][-1], r['SIM_SEC'][0], r['DECISIONS_OK'][0], r['DECISIONS_FAILED'][0], r['DECISIONS_HELD_PREVIOUS'][0], r['DECISIONS_HELD_ON_EXCEPTION'][0],
        len(r['decisions']), len(r['warmup_decisions']), r['wall_ge900']['n'], w.get('runner_exit'), w.get('wall_sec'), D[s]['native_status']['stage'], r['runlog_err_bytes'],
        '-', p['b_rows_all']))
out.append('')
out.append('### T7. VISSIM .err (B `network/sdmpc31_sdmpc9000_s<s>_001.err` · NC3 `run/baseline_s<s>_v3c3nc_001.err`)')
out.append('')
out.append('| 시드 | B 줄 (Warning / Note) | NC3 줄 (Warning) | B 의 "Vehicle input … could not be finished completely" 줄 | NC3 의 같은 줄 | B network/VISSIG_Controller.dll.err 줄 |')
out.append('|---|---|---|---|---|---|')
for s in S:
    eb = D[s]['err_b']['network/sdmpc31_sdmpc9000_s%d_001.err' % s]
    en = D[s]['err_nc3']['baseline_s%d_v3c3nc_001.err' % s]
    vb = sum(n for t, m, n in eb['top'] if m.startswith('Vehicle input'))
    vn = sum(n for t, m, n in en['top'] if m.startswith('Vehicle input'))
    vc = D[s]['err_b'].get('network/VISSIG_Controller.dll.err', {}).get('lines')
    out.append('| v3c3-s%d | %d (%d / %d) | %d (%d) | %d | %d | %s |' % (s, eb['lines'], eb['types'].get('Warning', 0), eb['types'].get('Note', 0), en['lines'], en['types'].get('Warning', 0), vb, vn, vc))
out.append('')
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write('\n'.join(out) + '\n')
print('ok')
