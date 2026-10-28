# g1_tables.py - format gate1_summary.json into Markdown tables for GATE1.md (no new numbers: copies values, rounds for
# display, and lists differences already in the summary). Written after the replay data (formatting only, disclosed).
# usage: python -B g1_tables.py <gate1_summary.json> <out.md>
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
R = {x.get('label'): x for x in d['replays']}
IDS = ['g1R1', 'g1R2', 'g1R3', 'g1R4']
NAME = {'g1R1': 'R1 V-A v3c3-s31 · B 설정', 'g1R2': 'R2 V-A v3c3-s41 · B 설정', 'g1R3': 'R3 V-A v3c3-s43 · B 설정',
        'g1R4': 'R4 V-A v3c3-s31 · 그룹키 설정'}
out = []


def f1(x):
    return '–' if x is None else ('%.1f' % x)


out.append('### T1 재생 넷: 끝남·예외·벽시계\n')
out.append('| 재생 | 종료 | 예외 | `[경고]` 줄 | 래퍼 벽시계 (s) | budget wall (s) | budget CPU (s) | output_completed | 진행 줄 | CPU 평균 % (큐 길이) | 통과 조건 |')
out.append('|---|---:|---|---:|---:|---:|---:|---|---:|---|---|')
for i in IDS:
    x = R.get(i, {})
    g = x.get('gate', {})
    out.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s (%s) | %s |' % (
        NAME[i], x.get('exit'), x.get('exception') or '없음', x.get('stderr_warning_lines'), f1(x.get('wall_sec')),
        f1(x.get('budget_wall_sec')), f1(x.get('budget_cpu_sec')), x.get('budget_output_completed'), x.get('progress_lines'),
        x.get('cpu_total_pct_mean'), x.get('cpu_queue_len_mean'),
        '넷 모두 만족' if g.get('pass') else 'FAIL: ' + ', '.join(k for k in ('finished', 'no_exception', 'wall_le_1500') if not g.get(k))))
out.append('\n### T2 명령 CSV·VSL·유지\n')
out.append('| 재생 | 행 수 (kind 별) | CSV sha256 앞 16 | VSL 속도 집합 (행) | `controller_status` | `sdmpc_state` | 유령 별칭 언급 | 유지·오류 파일 |')
out.append('|---|---|---|---|---|---|---:|---|')
for i in IDS:
    x = R.get(i, {})
    out.append('| %s | %s %s | `%s` | %s (%s) | %s | %s | %s | %s |' % (
        NAME[i], x.get('csv_rows'), json.dumps(x.get('csv_rows_by_kind'), ensure_ascii=False), (x.get('csv_sha256') or '')[:16],
        ','.join(x.get('vsl_speeds') or []), x.get('vsl_rows'), x.get('controller_status'), x.get('sdmpc_state_present'),
        x.get('phantom_alias_mentions'), ', '.join(x.get('hold_or_error_files') or []) or '없음'))
out.append('\n### T3 미터 명령 (rate_vph / green_sec)\n')
ids = sorted({k for i in IDS for k in (R.get(i, {}).get('meter_rows') or {})})
out.append('| 미터 | ' + ' | '.join(NAME[i].split(' ')[0] + ' ' + NAME[i].split(' ')[2] for i in IDS) + ' |')
out.append('|---' + '|---' * len(IDS) + '|')
for m in ids:
    cells = []
    for i in IDS:
        v = (R.get(i, {}).get('meter_rows') or {}).get(m)
        cells.append('%s / %s' % (v['rate_vph'], v['green_sec']) if v else '–')
    out.append('| %s | %s |' % (m, ' | '.join(cells)))
out.append('\n### T4 신호 명령 (p1/p2/p3/p4 녹색 s, offset s)\n')
sids = sorted({k for i in IDS for k in (R.get(i, {}).get('signal_rows') or {})}, key=lambda s: (len(s), s))
out.append('| 신호 | ' + ' | '.join(NAME[i].split(' ')[0] + ' ' + NAME[i].split(' ')[2] for i in IDS) + ' |')
out.append('|---' + '|---' * len(IDS) + '|')
for s in sids:
    cells = []
    for i in IDS:
        v = (R.get(i, {}).get('signal_rows') or {}).get(s)
        cells.append(('%s/%s/%s/%s, %s' % (v['p1_green'], v['p2_green'], v['p3_green'], v['p4_green'], v['offset'])) if v else '–')
    out.append('| %s | %s |' % (s, ' | '.join(cells)))
out.append('\n### T5 램프 도착 예측 메타데이터·선택 스칼라\n')
keys = sorted({k for i in IDS for k in (R.get(i, {}).get('forecast') or {})})
out.append('| 칸 | ' + ' | '.join(NAME[i].split(' ')[0] for i in IDS) + ' |')
out.append('|---' + '|---' * len(IDS) + '|')
for k in keys:
    out.append('| `%s` | %s |' % (k, ' | '.join(str((R.get(i, {}).get('forecast') or {}).get(k, '–')) for i in IDS)))
for k in ('held_objective', 'warm_start_objective', 'selected_objective', 'prediction_ttt_reduction', 'selection_status'):
    out.append('| selection `%s` | %s |' % (k, ' | '.join(str((R.get(i, {}).get('selection') or {}).get(k, '–')) for i in IDS)))
out.append('| `decision_wall_sec` 메타 | %s |' % ' | '.join(str(R.get(i, {}).get('decision_wall_sec_meta')) for i in IDS))
out.append('\n### T6 R1 대 R4 (같은 상태, 램프 도착 예측 객체만 다름)\n')
for p in d.get('pairs', []):
    c = p['csv']
    out.append('- CSV 바이트 같음: %s. 행 %s 대 %s, 한쪽만 있는 키 %s/%s.' % (p['csv_bytes_equal'], c['rows_a'], c['rows_b'], c['keys_only_a'], c['keys_only_b']))
    out.append('- kind 별 다른 행: %s' % json.dumps(c['differing_rows_by_kind'], ensure_ascii=False))
    out.append('- 다른 행 id: %s' % json.dumps(c['differing_ids'], ensure_ascii=False))
    out.append('- 칸별 최대 |차|: %s' % json.dumps({k: round(v, 6) for k, v in c['max_abs_diff'].items()}, ensure_ascii=False))
out.append('\n### T7 러너 사전 점검\n')
out.append('| 점검 | 종료 | FREEZE_VERIFIED | 망 sha | 유지 env | 튜닝 sha | freeze 핀 | plant 핀 | 검지표 핀 | seed·9000·wu-link | 빈 RW 값 | env 키 | 래퍼 벽시계 (s) | provenance sha256 앞 16 | 모두 참 |')
out.append('|---|---:|---|---|---|---|---|---|---|---|---|---:|---:|---|---|')
for p in d['preflights']:
    c = p.get('checks', {})
    out.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | `%s` | %s |' % (
        p['label'], p.get('runner_exit'), c.get('freeze_verified'), c.get('network_sha'), c.get('hold_policy_env'), c.get('tuning_sha'),
        c.get('freeze_pin'), c.get('plant_manifest_pin'), c.get('detector_pin'),
        bool(c.get('seed') and c.get('sim_period_9000') and c.get('controller_wu_link')), ','.join(p.get('env_empty_values') or []),
        p.get('env_keys'), p.get('wall_sec'), (p.get('provenance_sha256') or '')[:16], p.get('pass')))
out.append('\n- 재생 뒤 FRZ_B0 freeze verify: %s' % json.dumps(d.get('freeze_verify_after'), ensure_ascii=False))
out.append('- 요약 도구의 관문 칸: %s' % json.dumps(d.get('gate1'), ensure_ascii=False))
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('ok', len(out))
