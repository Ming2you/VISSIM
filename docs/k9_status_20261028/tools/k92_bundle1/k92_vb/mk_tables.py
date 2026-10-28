"""V-B report table formatter (session helper, not a judge tool).  Reads the finished V-B judge / stage files under
VBR and prints Markdown tables to stdout (or a file).  No judging, no recomputation beyond formatting.

    python -B mk_tables.py <VBR> <out.md>"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def j(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def f(x, nd=2):
    if x is None:
        return '없음'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, float):
        return ('%.' + str(nd) + 'f') % x
    return str(x)


def main(vbr, out):
    V = Path(vbr)
    L = []
    w = L.append
    # V0..V10
    w('### 단계 기록 (`VBR/stages/*.json`)')
    w('')
    w('| 단계 | 결과 | 기록 sha256 앞 16자 |')
    w('|---|---|---|')
    import hashlib
    for name in ('V0', 'snap_s38_vb_v0', 'V1', 'V2', 'V3', 'snap_s39_vb_zi', 'V4', 'V5', 'snap_s40_vb_off', 'V6', 'V7',
                 'V8', 'V9', 'snap_s41_vb_end', 'V10'):
        p = V / 'stages' / ('%s.json' % name)
        if p.is_file():
            w('| %s | PASS | `%s` |' % (name, hashlib.sha256(p.read_bytes()).hexdigest()[:16]))
        else:
            w('| %s | 없음 | – |' % name)
    w('')
    # ZI
    zi = j(V / 'zi' / 'zi.json') or {}
    w('### ZI 세 칸 (`VBR/zi/<칸>/zi_judge.json`)')
    w('')
    w('| 칸 | (z1) | (z2) CSV 같음 | (z3) KC 결과 넷 | (z4) 진행 기록 | (z5) 벽시계 잎만 | (z6) 끔에 훅 파일 0 | (z7) 훅 무결성·고르기 | 칸 결과 | 훅 켬/끔 벽시계 비 | 후보 수 | 맞는 후보 | 훅 시간 합 (s) | 후보 파일 합 (MB) |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for cell in ('z1_off', 'z1_b1', 'z2_b1'):
        d = j(V / 'zi' / cell / 'zi_judge.json') or {}
        c = d.get('checks') or {}
        r = d.get('report_only') or {}
        zj = d.get('zi_judge') or {}
        w('| %s | %s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s | %s | %s | %s |' % (
            cell, f(c.get('z1')), f(c.get('z2')), zj.get('compare_verdict'), f(c.get('z4')), f(c.get('z5')),
            f(c.get('z6')), f(c.get('z7')), (d.get('z7') or {}).get('status'), 'PASS' if d.get('pass') else 'STOP',
            f(r.get('wall_on_over_off'), 4), r.get('n_candidates'), r.get('n_match'), f(r.get('hook_sec_total'), 1),
            f((r.get('candidate_bytes') or 0) / 1e6, 1)))
    w('')
    for cell in ('z1_off', 'z1_b1', 'z2_b1'):
        d = j(V / 'zi' / cell / 'zi_judge.json') or {}
        zj = d.get('zi_judge') or {}
        w('- %s: 두 출력 JSON의 차이 잎 %s개, 모두 벽시계 이름 잎 %s경로(`%s` 등), 그 밖 %s개.' % (
            cell, zj.get('n_diff_leaves'), len(zj.get('wallclock_paths') or []),
            (zj.get('wallclock_paths') or ['-'])[0], len(zj.get('other_diffs') or [])))
    z1 = (j(V / 'zi' / 'z1_off' / 'zi_judge.json') or {}).get('report_only', {}).get('off_vs_record') or {}
    w('- z1_off 훅 끔 출력 대 RR 기록(보고만): 결과 넷 %s, HARD %s, 미분류 %s, 허용 수 %s.' % (
        z1.get('verdict'), z1.get('hard_verdict'), z1.get('unclassified_n'), z1.get('allowed_counts')))
    w('')
    # VB-I1
    i1 = j(V / 'judge' / 'vb_i1.json') or {}
    w('### VB-I1 판정 4결정 (`VBR/judge/vb_i1.json`)')
    w('')
    w('| 사슬·T | 결과 넷 | HARD | 미분류 수 | 허용 수 | A_K92 줄 | D5 뿌리 점검 |')
    w('|---|---|---|---|---|---|---|')
    for k, v in (i1.get('VB_I1') or {}).items():
        rep = v.get('report') or {}
        w('| %s | **%s** | %s | %s | %s | %s | %s |' % (k, v.get('verdict'), v.get('hard_verdict'),
                                                     rep.get('unclassified_n'), rep.get('allowed_counts'),
                                                     v.get('a_k92_rows'), f(v.get('d5_root_check'))))
    w('')
    ro = j(V / 'judge' / 'vb_reportonly.json') or {}
    w('### 보고 전용 10결정 (`VBR/judge/vb_reportonly.json`; 판정 아님)')
    w('')
    w('| 사슬 | T (직전) | 꼴 | 결과 넷(참고) | CSV 같음 | 목록 안 HARD / 목록 HARD | 목록 안 미분류 | **목록 밖 개수** | 잘림 | 보이지 않은 목록 잎 |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    for k, v in (ro.get('decisions') or {}).items():
        vw = v.get('view') or {}
        nh = len([x for x in (vw.get('in_list_hard') or [])])
        w('| %s | %s (%s) | %s | %s | %s | %d | %d | **%s** | %s | %s |' % (
            v.get('chain'), v.get('T'), v.get('prev_T'), v.get('dtype'), vw.get('verdict_reference_only'),
            f(vw.get('h1_csv_same')), nh, len(vw.get('in_list_unclassified') or []), vw.get('outside_n'),
            vw.get('truncated') or '–', len(vw.get('listed_not_seen') or [])))
    w('')
    for k, v in (ro.get('decisions') or {}).items():
        w('- %s T=%s: %s' % (v.get('chain'), v.get('T'), (v.get('view') or {}).get('sentence')))
    w('')
    # VB-I2..I7
    vi = j(V / 'judge' / 'vb_i.json') or {}
    w('### VB-I2–VB-I7 (`VBR/judge/vb_i.json`, 55결정)')
    w('')
    w('| 점검 | 결과 |')
    w('|---|---|')
    for k in ('VB_I2_ok', 'VB_I3_ok', 'VB_I4_ok', 'VB_I6_ok', 'VB_I7_ok'):
        w('| %s | %s |' % (k[:-3].replace('_', '-'), f(vi.get(k))))
    rc = j(V / 'recalc' / 'recalc.json') or {}
    w('| VB-I5 (재계산 같음) | %s (비교 %s칸, 다름 %s) |' % (f(rc.get('equal')), rc.get('n_compared'), rc.get('n_diff')))
    w('')
    w('- SDMPC 결정의 고르기 상태: %s. `selected`가 아닌 SDMPC 결정: %s.' % (
        vi.get('select_counts_sdmpc'), vi.get('not_selected_sdmpc') or '없음'))
    for ch, v in (vi.get('VB_I6') or {}).items():
        w('- VB-I6 %s: 결정마다 키 하나·이름 맞음 %s, 줄지 않음 %s%s; 값 %s' % (
            ch, f(all(r.get('n_keys') == 1 and r.get('name_ok') for r in v.get('rows') or [])),
            f(v.get('non_decreasing')),
            (', T=150 값 = T=1 값 = s %s' % f(v.get('t150_eq_t1_eq_seed'))) if 't150_eq_t1_eq_seed' in v else '',
            [f(r.get('value'), 4) for r in v.get('rows') or []]))
    w('')
    # VB-M
    vm = j(V / 'judge' / 'vb_m.json') or {}
    rows = vm.get('rows') or []
    chains = vm.get('chains') or []
    for ch in ('VB-41w', 'VB-31', 'VB-43', 'VB-41'):
        w('### %s — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리)' % ch)
        w('')
        w('| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름·갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω (selected_objective) | 유령 끝 | PFO>유지 / 고름>유지 | CSV=REC | 어댑터 벽시계 (s) | 고르기 |')
        w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        rs = sorted([r for r in rows if r['chain'] == ch], key=lambda r: (r['T'], {'B1': 0, 'OFF': 1, 'REC': 2}[r['side']]))
        for r in rs:
            w('| %s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s/%s | %s | %s | %s |' % (
                r['T'], r['side'], f(r['p2'], 1), f(r['p3'], 2), f(r['p4'], 1), f(r['floor'], 1),
                f(r['seed_binding'], 1), f(r['groups_carried'], 0), f(r['groups_updated'], 0), f(r['chain_T450'], 2),
                f(r['chain_max_450'], 2), f(r['w_bound_ratio'], 3), f(r['e_out_over_220'], 3), f(r['outw'], 2),
                f(r['feed4'], 2), f(r['feed4_ratio'], 3), f(r['omega'], 2), f(r['phantom_end'], 2),
                f(r['warm_gt_held']), f(r['selected_gt_held']), f(r.get('csv_same_as_rec')) if r['side'] != 'REC' else '–',
                f(r['wall_run_sec'], 0), r.get('select_status') or (r.get('none_reason') or '–')))
        w('')
        w('| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 Δ ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status |')
        w('|---|---|---|---|---|---|---|---|---|---|')
        for c in [c for c in chains if c['chain'] == ch]:
            w('| %s | %s | %s (%s) | %s | %s | %s | %s / %s | %s / %s | %s | %s |' % (
                c['side'], c['n'], c['n_p3_le_24_5'], f(c['first_T_p3_le_24_5']), c['n_deltas'], c['sign_changes'],
                f(c['mean_abs_dp3'], 2), c['n_k92_w'], c['n_k92_hb'], c['n_warm_gt_held'], c['n_selected_gt_held'],
                f(c['first_T_csv_differs']) if c['side'] != 'REC' else '–', c['selection_status_counts']))
        w('')
    text = '\n'.join(L) + '\n'
    Path(out).write_text(text, encoding='utf-8', newline='\n')
    print('MK_TABLES lines=%d' % len(L))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
