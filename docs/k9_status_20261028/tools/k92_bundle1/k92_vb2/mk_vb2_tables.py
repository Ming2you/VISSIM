"""V-B rerun (amendment 33) report table formatter -- session helper, NOT a judge tool, never committed.

Reads the finished V-B files under VBR (= OK2/vb2): stage records, ZI judge files, judge/*.json, recalc/recalc.json,
the per-decision done records and the 58 hook folders (names; `pid` / `argv0` of loaded_*.json; `pid` / `time_ns` /
`seq` of cand.json), and writes Markdown tables plus a small JSON summary.  It decides nothing: every PASS / true /
false shown is copied from the driver's files.  The only things it counts itself are report-only items of amendment 33
section 8-5 / 6.5 (hook folder names: loaded files, tokens, same-PID token groups, time_ns overlap) and the
action_token comparison with the STOP r1 list of 11 paths (amendment 33 section 9).

    python -B mk_vb2_tables.py <VBR> <out.md> <out_summary.json>
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

R1_PATHS = [
    '/metadata/joint_leader_selection/budget_initialization/reference_action_token',
    '/metadata/joint_leader_selection/control_sequence/plan_action_token',
    '/metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token',
    '/metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token',
    '/metadata/joint_leader_selection/surrogate_query/rows[*]/action_token',
    '/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/'
    'initialization/reference_action_token',
    '/metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token',
    '/metadata/joint_leader_selection/trial_rows[*]/action_token',
]
TOK = r'[0-9]+_[0-9]+_[0-9a-f]{16}'
RE_LOADED = re.compile(r'^loaded_(%s)\.json$' % TOK)
RE_CAND = re.compile(r'^c_(%s)_([0-9]{4,})$' % TOK)
RE_ERR = re.compile(r'^hook_error_(%s)\.txt$' % TOK)
RE_SERR = re.compile(r'^hook_setup_error_((%s)|[0-9]+_notoken)\.txt$' % TOK)
RE_OLD = re.compile(r'^(loaded_[0-9]+\.json|c_[0-9]+_[0-9]{4}|hook_error_[0-9]+\.txt|hook_setup_error_[0-9]+\.txt)$')
CHAINS = [('VB-41w', 'vb41w', [1, 150, 300, 450, 600, 750, 900, 1050], [1, 150, 300, 450, 600, 750, 900, 1050]),
          ('VB-31', 'vb31', list(range(3000, 4501, 150)), [3000, 3150]),
          ('VB-43', 'vb43', list(range(3000, 4501, 150)), [3000, 3150]),
          ('VB-41', 'vb41', list(range(3000, 4501, 150)), [3000, 3150])]
CLOSED_P = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
                r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1/a32decl/vb_closed_leaves.json')
STAGES = ('V0', 'snap_s43_vb2_v0', 'V1', 'V2', 'V3', 'snap_s44_vb2_zi', 'V4', 'V5', 'snap_s45_vb2_off', 'V6', 'V7', 'V8',
          'V9', 'snap_s46_vb2_end', 'V10')


def j(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def sh(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def f(x, nd=2):
    if x is None:
        return '없음'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, float):
        return ('%.' + str(nd) + 'f') % x
    return str(x)


def hook_folder_summary(d):
    """Report-only name summary of one hook folder (amendment 33 sections 6.5 / 8-5)."""
    d = Path(d)
    if not d.is_dir():
        return {'present': False}
    names = sorted(p.name for p in d.iterdir())
    loaded, cands, errs, serrs, old, other = {}, {}, [], [], [], []
    for n in names:
        p = d / n
        m = RE_LOADED.match(n)
        if m and p.is_file():
            doc = j(p) or {}
            loaded[m.group(1)] = {'pid': doc.get('pid'), 'argv0': doc.get('argv0')}
            continue
        m = RE_CAND.match(n)
        if m and p.is_dir():
            c = j(p / 'cand.json') or {}
            inner = sorted(q.name for q in p.iterdir())
            cands.setdefault(m.group(1), []).append({'seq': int(m.group(2)), 'pid': c.get('pid'),
                                                     'time_ns': c.get('time_ns'), 'inner': inner})
            continue
        if RE_ERR.match(n):
            errs.append(n)
            continue
        if RE_SERR.match(n):
            serrs.append(n)
            continue
        if RE_OLD.match(n):
            old.append(n)
            continue
        other.append(n)
    toks = sorted(set(loaded) | set(cands))
    by_pid = {}
    for t in toks:
        by_pid.setdefault(int(t.split('_')[0]), []).append(t)
    groups = {pid: ts for pid, ts in by_pid.items() if len(ts) >= 2}
    overlap = []
    for pid, ts in groups.items():
        iv = []
        for t in ts:
            tn = [c['time_ns'] for c in cands.get(t, []) if isinstance(c.get('time_ns'), int)]
            if tn:
                iv.append((min(tn), max(tn), t))
        iv.sort()
        for (a0, a1, ta), (b0, b1, tb) in zip(iv, iv[1:]):
            if b0 <= a1:
                overlap.append([pid, ta, tb])
    pair_ok = all(t in loaded for t in cands)
    pid_ok = all(loaded[t]['pid'] == int(t.split('_')[0]) for t in loaded) and all(
        c['pid'] == int(t.split('_')[0]) for t in cands for c in cands[t])
    seq_ok = all(sorted(c['seq'] for c in cs) == list(range(1, len(cs) + 1)) for cs in cands.values())
    inner_ok = all(('cand.json' in c['inner'] and 'k92_record.json' in c['inner']
                    and set(c['inner']) <= {'cand.json', 'k92_record.json', 'k92_series.npz'})
                   for cs in cands.values() for c in cs)
    return {'present': True, 'n_names': len(names), 'n_loaded': len(loaded),
            'n_adapter_loaded': sum(1 for v in loaded.values() if v['argv0'] == 'vissim_stackelberg_adapter.py'),
            'n_tokens': len(toks), 'n_tokens_with_candidates': len(cands),
            'n_candidates': sum(len(v) for v in cands.values()), 'n_hook_error': len(errs),
            'n_hook_setup_error': len(serrs), 'n_old_form': len(old), 'n_other_names': len(other),
            'other_names': other[:10], 'n_distinct_pids': len(by_pid), 'same_pid_groups': len(groups),
            'same_pid_extra_tokens': sum(len(v) - 1 for v in groups.values()),
            'same_pid_group_pids': sorted(groups), 'same_pid_time_overlap': overlap,
            'pair_loaded_for_every_candidate_token': pair_ok, 'pid_matches_token': pid_ok,
            'seq_contiguous_from_1': seq_ok, 'candidate_folder_files_ok': inner_ok}


CLOSED = None


def main(vbr, out, out_json):
    global CLOSED
    CLOSED = j(CLOSED_P)
    V = Path(vbr)
    L = []
    w = L.append
    summ = {'vbr': str(V)}
    # ------------------------------------------------------------------ stages
    w('### 단계 기록 (`VBR/stages/*.json`)')
    w('')
    w('| 단계 | 기록 | sha256 앞 16자 |')
    w('|---|---|---|')
    st = {}
    for name in STAGES:
        p = V / 'stages' / ('%s.json' % name)
        st[name] = sh(p) if p.is_file() else None
        w('| %s | %s | %s |' % (name, '있음 (PASS 기록)' if p.is_file() else '없음',
                                ('`%s`' % st[name][:16]) if st[name] else '–'))
    stops = sorted(p.name for p in V.glob('STOP_vb_*.json'))
    w('')
    w('- STOP 파일: %s' % (', '.join(stops) if stops else '없음'))
    w('')
    summ['stages'] = st
    summ['stop_files'] = stops
    # ------------------------------------------------------------------ ZI
    w('### ZI 세 칸 (`VBR/zi/<칸>/zi_judge.json`)')
    w('')
    w('| 칸 | (z1) | (z2) CSV 같음 | (z3) KC 결과 넷 | (z4) 진행 기록 | (z5) 벽시계 잎만 | (z6) 끔에 훅 파일 0 | '
      '(z7) 훅 무결성·고르기 | 칸 결과 |')
    w('|---|---|---|---|---|---|---|---|---|')
    zis = {}
    for cell in ('z1_off', 'z1_b1', 'z2_b1'):
        d = j(V / 'zi' / cell / 'zi_judge.json') or {}
        zis[cell] = d
        c = d.get('checks') or {}
        zj = d.get('zi_judge') or {}
        w('| %s | %s | %s | %s | %s | %s | %s | %s, `%s` | %s |' % (
            cell, f(c.get('z1')), f(c.get('z2')), zj.get('compare_verdict'), f(c.get('z4')), f(c.get('z5')),
            f(c.get('z6')), f(c.get('z7')), (d.get('z7') or {}).get('status'),
            'PASS' if d.get('pass') else ('없음' if not d else '거짓')))
    w('')
    w('훅 비용 (보고만)')
    w('')
    w('| 칸 | 훅 끔 벽시계 (s) | 훅 켬 벽시계 (s) | 켬/끔 비 | 후보 수 | 맞는 후보 | 훅 안 시간 합 (s) | 후보 파일 합 (MB) | '
      '`loaded` 파일 수 |')
    w('|---|---|---|---|---|---|---|---|---|')
    for cell, d in zis.items():
        r = d.get('report_only') or {}
        w('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            cell, f(r.get('wall_off_sec'), 1), f(r.get('wall_on_sec'), 1), f(r.get('wall_on_over_off'), 3),
            r.get('n_candidates'), r.get('n_match'), f(r.get('hook_sec_total'), 1),
            f((r.get('candidate_bytes') or 0) / 1e6, 1), r.get('n_loaded')))
    w('')
    for cell, d in zis.items():
        zj = d.get('zi_judge') or {}
        w('- %s: 두 출력 JSON의 차이 잎 %s개, 벽시계 이름 경로 %s개, 그 밖 %s개.' % (
            cell, zj.get('n_diff_leaves'), len(zj.get('wallclock_paths') or []), len(zj.get('other_diffs') or [])))
    z1 = ((zis.get('z1_off') or {}).get('report_only') or {}).get('off_vs_record') or {}
    w('- z1_off 훅 끔 출력 대 RR 기록(보고만): 결과 넷 %s, HARD %s, 미분류 %s, 허용 수 %s.' % (
        z1.get('verdict'), z1.get('hard_verdict'), z1.get('unclassified_n'), z1.get('allowed_counts')))
    w('')
    summ['zi'] = {k: {'pass': v.get('pass'), 'checks': v.get('checks'),
                      'ratio': (v.get('report_only') or {}).get('wall_on_over_off')} for k, v in zis.items()}
    # ------------------------------------------------------------------ VB-I1
    i1 = j(V / 'judge' / 'vb_i1.json') or {}
    w('### VB-I1 판정 4결정 (`VBR/judge/vb_i1.json`)')
    w('')
    w('| 사슬·T | 결과 넷 | HARD | 미분류 | 허용 수 | A_K92 줄 | D5 뿌리 점검 | 칸 결과 |')
    w('|---|---|---|---|---|---|---|---|')
    for k, v in (i1.get('VB_I1') or {}).items():
        rep = v.get('report') or {}
        w('| %s | **%s** | %s | %s | %s | %s | %s | %s |' % (
            k, v.get('verdict'), v.get('hard_verdict'), rep.get('unclassified_n'), rep.get('allowed_counts'),
            v.get('a_k92_rows'), f(v.get('d5_root_check')), 'PASS' if v.get('pass') else '거짓'))
    w('')
    w('- VB-I1 4결정 모두 PASS: %s. OFF 14결정 VB-I2: %s, VB-I7: %s.' % (
        f(i1.get('VB_I1_pass')), f(i1.get('VB_I2_off_ok')), f(i1.get('VB_I7_off_ok'))))
    w('')
    summ['vb_i1'] = {k: {'verdict': v.get('verdict'), 'hard': v.get('hard_verdict'),
                         'uncl': (v.get('report') or {}).get('unclassified_n'), 'pass': v.get('pass')}
                     for k, v in (i1.get('VB_I1') or {}).items()}
    summ['vb_i1_pass'] = i1.get('VB_I1_pass')
    # ------------------------------------------------------------------ report-only
    ro = j(V / 'judge' / 'vb_reportonly.json') or {}
    w('### 보고 전용 10결정 (`VBR/judge/vb_reportonly.json`; 판정 아님, D-K9-62·66)')
    w('')
    w('| 사슬 | T (직전 T) | 꼴 | 결과 넷(참고) | CSV 같음 | 목록 안 HARD / 목록의 HARD | 목록 안 미분류 경로 | '
      '**목록 밖 경로 수** (잎 수) | 그중 `action_token` 꼴 | 목록 밖 HARD | 잘림 | 보이지 않은 목록 잎 |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|')
    a_n, b_n, b_leaves, c_n = 0, 0, 0, 0
    tok_union, nontok = set(), []
    per = {}
    for k, v in (ro.get('decisions') or {}).items():
        vw = v.get('view') or {}
        outs = vw.get('outside_unclassified') or []
        oh = vw.get('outside_hard') or []
        leaves = sum(int(x.get('count') or 0) for x in outs)
        tok = [x for x in outs if 'action_token' in str(x.get('path') or '').lower()]
        non = [x for x in outs if 'action_token' not in str(x.get('path') or '').lower()]
        on = vw.get('outside_n')
        if isinstance(on, int) and on > 0:
            a_n += 1
        b_n += on if isinstance(on, int) else 0
        b_leaves += leaves
        c_n += len(tok)
        tok_union |= {str(x.get('path')).lower() for x in tok}
        for x in non:
            nontok.append([v.get('chain'), v.get('T'), x.get('path'), x.get('kind'), x.get('why'), x.get('count')])
        for x in oh:
            nontok.append([v.get('chain'), v.get('T'), 'HARD %s %s' % (x.get('group'), x.get('path')), 'hard', None,
                           None])
        n_hard_list = len({x['path'] for x in CLOSED['types'].get(v.get('dtype'), {}).get('leaves', []) if x['hard']})             if CLOSED and v.get('dtype') else None
        per[k] = {'outside_n': on, 'leaves': leaves, 'tok': len(tok), 'nontok': len(non), 'hard': len(oh),
                  'csv_same': vw.get('h1_csv_same'), 'sentence': vw.get('sentence'), 'incomplete': vw.get('incomplete')}
        w('| %s | %s (%s) | %s | %s | %s | %d / %s | %d | **%s** (%d) | %d | %d | %s | %d |' % (
            v.get('chain'), v.get('T'), v.get('prev_T'), v.get('dtype'), vw.get('verdict_reference_only'),
            f(vw.get('h1_csv_same')), len(vw.get('in_list_hard') or []), n_hard_list,
            len(vw.get('in_list_unclassified') or []), on if on is not None else '셀 수 없음', leaves, len(tok),
            len(oh), ', '.join(vw.get('truncated') or []) or '없음', len(vw.get('listed_not_seen') or [])))
    w('')
    for k, v in (ro.get('decisions') or {}).items():
        w('- %s T=%s: %s' % (v.get('chain'), v.get('T'), (v.get('view') or {}).get('sentence')))
    w('')
    r1 = {p.lower() for p in R1_PATHS}
    same = sorted(tok_union & r1)
    new = sorted(tok_union - r1)
    gone = sorted(r1 - tok_union)
    w('- 목록 밖 `action_token` 꼴 경로(서로 다른 것) %d개. STOP 판 r1의 11경로와 견주면: 같은 경로 %d개, 이번에 새로 보인 '
      '경로 %d개, 이번에 보이지 않은 경로 %d개.' % (len(tok_union), len(same), len(new), len(gone)))
    if new:
        w('  - 새로 보인 경로: %s' % '; '.join('`%s`' % p for p in new))
    if gone:
        w('  - 보이지 않은 경로: %s' % '; '.join('`%s`' % p for p in gone))
    w('- `action_token` 꼴이 아닌 목록 밖 차이: %d건%s' % (
        len(nontok), '' if not nontok else ' — ' + '; '.join('**%s T=%s %s (%s, %s, %s)**' % tuple(x) for x in nontok)))
    w('')
    summ['reportonly'] = {'a_decisions': a_n, 'b_paths_total': b_n, 'b_leaves_total': b_leaves,
                          'c_action_token_paths_total': c_n, 'action_token_distinct': len(tok_union),
                          'vs_r1_same': len(same), 'vs_r1_new': new, 'vs_r1_gone': gone, 'non_action_token': nontok,
                          'per_decision': per}
    # ------------------------------------------------------------------ OFF rows
    w('### VB-I2·VB-I7 — OFF 14결정 (`VBR/judge/vb_i1.json` `/off_rows`)')
    w('')
    w('| 사슬 | T | VB-I2 | VB-I7 | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |')
    w('|---|---|---|---|---|---|---|')
    for r in i1.get('off_rows') or []:
        w('| %s | %s | %s | %s | %s | %s / %s | %s |' % (
            r.get('chain'), r.get('T'), f((r.get('VB_I2') or {}).get('ok')), f((r.get('VB_I7') or {}).get('ok')),
            r.get('select_status'), r.get('n_candidates'), r.get('n_match'), f(r.get('hook_sec_total'), 1)))
    w('')
    # ------------------------------------------------------------------ VB-I (55)
    vi = j(V / 'judge' / 'vb_i.json') or {}
    rc = j(V / 'recalc' / 'recalc.json') or {}
    w('### VB-I2–VB-I7 (55결정; `VBR/judge/vb_i.json`, VB-I5 = `VBR/recalc/recalc.json`)')
    w('')
    w('| 점검 | 결과 |')
    w('|---|---|')
    for k in ('VB_I2_ok', 'VB_I3_ok', 'VB_I4_ok', 'VB_I6_ok', 'VB_I7_ok'):
        w('| %s | %s |' % (k[:-3].replace('_', '-'), f(vi.get(k)) if vi else '없음'))
    w('| VB-I5 (재계산 같음) | %s |' % (f(rc.get('equal')) if rc else '없음'))
    w('')
    if vi:
        w('- SDMPC 결정의 고르기 상태 개수: %s. `selected`가 아닌 SDMPC 결정: %s.' % (
            vi.get('select_counts_sdmpc'), vi.get('not_selected_sdmpc') or '없음'))
        for ch, v in (vi.get('VB_I6') or {}).items():
            w('- VB-I6 %s: 결정마다 키 하나·이름 맞음 %s, 값 줄지 않음 %s%s; 값 %s' % (
                ch, f(all(r.get('n_keys') == 1 and r.get('name_ok') for r in v.get('rows') or [])),
                f(v.get('non_decreasing')),
                (', T=150 값 = T=1 값 = s %s' % f(v.get('t150_eq_t1_eq_seed'))) if 't150_eq_t1_eq_seed' in v else '',
                [f(r.get('value'), 4) for r in v.get('rows') or []]))
        w('')
        w('| 사슬 | 팔 | T | VB-I2 | VB-I7 | SDMPC | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |')
        w('|---|---|---|---|---|---|---|---|---|')
        for r in vi.get('rows') or []:
            w('| %s | %s | %s | %s | %s | %s | %s | %s / %s | %s |' % (
                r.get('chain'), r.get('arm'), r.get('T'), f((r.get('VB_I2') or {}).get('ok')),
                f((r.get('VB_I7') or {}).get('ok')), f(r.get('sdmpc_active')), r.get('select_status'),
                r.get('n_candidates'), r.get('n_match'), f(r.get('hook_sec_total'), 1)))
        w('')
    if rc:
        w('- 재계산기 요약 키: %s' % sorted(k for k in rc if not isinstance(rc[k], (dict, list)))[:20])
        w('')
    summ['vb_i'] = {k: vi.get(k) for k in ('VB_I2_ok', 'VB_I3_ok', 'VB_I4_ok', 'VB_I6_ok', 'VB_I7_ok', 'ok',
                                            'select_counts_sdmpc', 'not_selected_sdmpc')} if vi else None
    summ['vb_i5'] = rc.get('equal') if rc else None
    # ------------------------------------------------------------------ hook folder names (report only)
    folders = []
    for name, key, times, offt in CHAINS:
        for arm, ts in (('off', offt), ('b1', times)):
            for T in ts:
                folders.append(('%s %s T=%d' % (name, arm, T), V / 'chain' / ('%s_%s' % (key, arm)) / 'hook' / ('t%06d' % T)))
    for cell in ('z1_off', 'z1_b1', 'z2_b1'):
        folders.append(('ZI %s' % cell, V / 'zi' / cell / 'hook_on'))
    hs = [(lab, hook_folder_summary(p)) for lab, p in folders]
    present = [(lab, h) for lab, h in hs if h.get('present')]
    tot = lambda k: sum(h[k] for _, h in present)  # noqa: E731
    w('### 훅 폴더 이름 요약 (보고만; 보충 33 §8-5)')
    w('')
    w('- 훅 폴더 %d/%d개 있음. `loaded` 파일 합 %d, 서로 다른 토큰 합 %d(후보가 있는 토큰 %d), 후보 폴더 합 %d.' % (
        len(present), len(hs), tot('n_loaded'), tot('n_tokens'), tot('n_tokens_with_candidates'), tot('n_candidates')))
    w('- 이름 꼴: 옛 꼴 이름 %d, 그 밖의 이름 %d, `hook_error_*` %d, `hook_setup_error_*` %d.' % (
        tot('n_old_form'), tot('n_other_names'), tot('n_hook_error'), tot('n_hook_setup_error')))
    w('- 같은 PID를 둘 이상의 토큰이 받은 묶음(= 한 폴더 안 PID 재사용): 폴더 %d개에서 묶음 %d개(더 생긴 토큰 %d). '
      '그 묶음들의 후보 `time_ns` 구간 겹침 %d건.' % (
          sum(1 for _, h in present if h['same_pid_groups']), tot('same_pid_groups'), tot('same_pid_extra_tokens'),
          sum(len(h['same_pid_time_overlap']) for _, h in present)))
    w('- 이 표의 짝 점검(참고, 판정은 VerifyVB): 모든 후보 토큰에 `loaded` 있음 %s, PID = 토큰 첫 조각 %s, 순번 1부터 이어짐 %s, '
      '후보 폴더 안 파일 꼴 %s, 어댑터 `loaded` 폴더마다 하나 %s.' % (
          f(all(h['pair_loaded_for_every_candidate_token'] for _, h in present)),
          f(all(h['pid_matches_token'] for _, h in present)), f(all(h['seq_contiguous_from_1'] for _, h in present)),
          f(all(h['candidate_folder_files_ok'] for _, h in present)),
          f(all(h['n_adapter_loaded'] == 1 for _, h in present))))
    w('')
    w('| 훅 폴더 | `loaded` | 토큰 (후보 있음) | 후보 | 같은 PID 묶음 (더 생긴 토큰) | 겹침 |')
    w('|---|---|---|---|---|---|')
    for lab, h in present:
        w('| %s | %d | %d (%d) | %d | %d (%d) | %d |' % (
            lab, h['n_loaded'], h['n_tokens'], h['n_tokens_with_candidates'], h['n_candidates'], h['same_pid_groups'],
            h['same_pid_extra_tokens'], len(h['same_pid_time_overlap'])))
    w('')
    summ['hook_names'] = {'folders_present': len(present), 'folders_expected': len(hs),
                          'loaded': tot('n_loaded') if present else 0, 'tokens': tot('n_tokens') if present else 0,
                          'candidates': tot('n_candidates') if present else 0,
                          'old_form': tot('n_old_form') if present else 0,
                          'other_names': tot('n_other_names') if present else 0,
                          'errors': (tot('n_hook_error') + tot('n_hook_setup_error')) if present else 0,
                          'same_pid_groups': tot('same_pid_groups') if present else 0,
                          'same_pid_extra_tokens': tot('same_pid_extra_tokens') if present else 0,
                          'overlaps': sum(len(h['same_pid_time_overlap']) for _, h in present),
                          'folders_with_reuse': [lab for lab, h in present if h['same_pid_groups']],
                          'per_folder': {lab: h for lab, h in present}}
    # ------------------------------------------------------------------ wall clock of chain decisions
    w('### 사슬 결정 벽시계 (구동기 `done` 기록, 보고만)')
    w('')
    w('| 사슬 | 팔 | 결정 수 | 벽시계 합 (h) | 최소 (s) | 최대 (s) |')
    w('|---|---|---|---|---|---|')
    walls = {}
    for name, key, times, offt in CHAINS:
        for arm, ts in (('off', offt), ('b1', times)):
            ws = []
            for T in ts:
                d = j(V / 'chain' / ('%s_%s' % (key, arm)) / 'done' / ('t%06d.json' % T)) or {}
                if isinstance(d.get('wall_sec'), (int, float)):
                    ws.append(float(d['wall_sec']))
            walls['%s/%s' % (name, arm)] = ws
            w('| %s | %s | %d | %s | %s | %s |' % (name, arm, len(ws), f(sum(ws) / 3600.0, 2) if ws else '없음',
                                                   f(min(ws), 1) if ws else '없음', f(max(ws), 1) if ws else '없음'))
    w('')
    summ['walls'] = {k: {'n': len(v), 'sum_h': sum(v) / 3600.0 if v else None} for k, v in walls.items()}
    # ------------------------------------------------------------------ VB-M
    vm = j(V / 'judge' / 'vb_m.json') or {}
    rows = vm.get('rows') or []
    chains = vm.get('chains') or []
    if rows:
        for name, key, times, offt in CHAINS:
            w('#### %s — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)' % name)
            w('')
            w('| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | '
              'E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | '
              '벽시계 (s) | 고르기 |')
            w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
            rs = sorted([r for r in rows if r['chain'] == name],
                        key=lambda r: (r['T'], {'B1': 0, 'OFF': 1, 'REC': 2}[r['side']]))
            for r in rs:
                w('| %s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | %s/%s | %s | %s | '
                  '%s | %s |' % (
                      r['T'], r['side'], f(r['p2'], 2), f(r['p3'], 2), f(r['p4'], 2), f(r['floor'], 4),
                      f(r['seed_binding'], 1), f(r['groups_carried'], 0), f(r['groups_updated'], 0),
                      f(r['chain_T450'], 2), f(r['chain_max_450'], 2), f(r['w_bound_ratio'], 3),
                      f(r['e_out_over_220'], 3), f(r['outw'], 2), f(r['feed4'], 2), f(r['feed4_ratio'], 3),
                      f(r['omega'], 2), f(r['phantom_end'], 2), f(r['warm_gt_held']), f(r['selected_gt_held']),
                      r.get('selection_status') or '없음',
                      f(r.get('csv_same_as_rec')) if r['side'] != 'REC' else '–',
                      f(r['wall_run_sec'] if r['side'] != 'REC' else r.get('decision_wall_sec'), 0),
                      r.get('select_status') or (r.get('none_reason') or '–')))
            w('')
            w('| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb '
              '키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |')
            w('|---|---|---|---|---|---|---|---|---|---|---|')
            for c in [c for c in chains if c['chain'] == name]:
                w('| %s | %s | %s (%s) | %s | %s | %s | %s / %s | %s / %s | %s | %s | %s |' % (
                    c['side'], c['n'], c['n_p3_le_24_5'], f(c['first_T_p3_le_24_5']), c['n_deltas'],
                    c['sign_changes'], f(c['mean_abs_dp3'], 2), c['n_k92_w'], c['n_k92_hb'], c['n_warm_gt_held'],
                    c['n_selected_gt_held'], f(c['first_T_csv_differs']) if c['side'] != 'REC' else '–',
                    c['selection_status_counts'], c['n_select_selected'] if c['side'] != 'REC' else '–'))
            w('')
            if name == 'VB-41w':
                b = [r for r in rs if r['side'] == 'B1']
                w('- VB-41w B1 하한 = max(기록 하한, s): %s' % ['T=%s %s' % (r['T'], f(r.get('floor_eq_max_rec_seed')))
                                                            for r in b])
                w('')
    summ['vb_m_present'] = bool(rows)
    text = '\n'.join(L) + '\n'
    Path(out).write_text(text, encoding='utf-8', newline='\n')
    Path(out_json).write_text(json.dumps(summ, ensure_ascii=False, indent=1, default=str), encoding='utf-8',
                              newline='\n')
    print('tables', len(L), 'lines; stops', stops, '; vb_m rows', len(rows))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
