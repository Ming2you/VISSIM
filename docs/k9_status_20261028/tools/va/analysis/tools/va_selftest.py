r"""Self-test of the V-A analysis tools on published J1 / NC3 data (amendment 34 sec.8.0-2): with the V-A arm set to
the J1 runs (--profile selftest), pair A (V-A - NC3 on U6(V-A)) must re-produce the J1 - NC3 tables of
SP/j1/analysis/J1_REPORT.md sec.3.1, 3.2, 3.3, 5, 7, 8.1 within the rounding shown there (|mine - shown| <=
0.5 x 10^-decimals, i.e. "0.1 반올림 안에서" for one-decimal cells), and pair B (V-A - J1) must be 0 everywhere.
Extra exact checks against the J1 tool outputs (an_metrics / an_local / an_followup / an_control JSON) and the
selftest scans against the J1 scans.  Read-only; writes <selftest out>/va_selftest.json and prints ALL_OK or the misses.
python -B va_selftest.py"""
import io
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

J1A = os.path.join(V.SP, 'j1', 'analysis')
NUM = re.compile(r'[-+]?\d+(?:\.\d+)?')
CHECKS = []


def check(name, ok, detail=''):
    CHECKS.append({'check': name, 'ok': bool(ok), 'detail': detail})


def nums(cells_text):
    out = []
    for m in NUM.finditer(cells_text):
        s = m.group(0)
        dec = len(s.split('.')[1]) if '.' in s else 0
        out.append((float(s), dec))
    return out


def cmp_row(name, shown_text, mine):
    shown = nums(shown_text)
    if len(shown) != len(mine):
        check(name, False, 'count shown %d mine %d | %s | %s' % (len(shown), len(mine), shown_text, mine))
        return
    bad = []
    for (v, dec), x in zip(shown, mine):
        if x is None or abs(v - x) > 0.5 * 10 ** (-dec) + 1e-9:
            bad.append((v, x))
    check(name, not bad, 'bad %s' % bad[:6] if bad else 'n=%d' % len(mine))


class Report(object):
    def __init__(self, path):
        self.lines = io.open(path, encoding='utf-8').read().splitlines()

    def section(self, heading_prefix):
        i0 = next(i for i, l in enumerate(self.lines) if l.startswith(heading_prefix))
        i1 = next((i for i in range(i0 + 1, len(self.lines)) if self.lines[i].startswith('#')), len(self.lines))
        return self.lines[i0:i1]

    @staticmethod
    def row(sec, label):
        hits = [l for l in sec if l.startswith('| ' + label + ' |')]
        if len(hits) != 1:
            raise SystemExit('row not unique: %r (%d)' % (label, len(hits)))
        cells = [c.strip() for c in hits[0].strip().strip('|').split('|')]
        return cells


def main():
    prof = V.Profile('selftest')
    out = prof.out
    M = V.jload(os.path.join(out, 'va_metrics.json'))
    L = V.jload(os.path.join(out, 'va_local.json'))
    K = V.jload(os.path.join(out, 'va_control.json'))
    F = V.jload(os.path.join(out, 'va_followup.json'))
    TB = V.jload(os.path.join(out, 'va_tables.json'))
    JM = V.jload(os.path.join(J1A, 'out', 'an_metrics.json'))
    JL = V.jload(os.path.join(J1A, 'out', 'an_local.json'))
    JF = V.jload(os.path.join(J1A, 'out', 'an_followup.json'))
    JK = V.jload(os.path.join(J1A, 'out', 'an_control.json'))
    R = Report(os.path.join(J1A, 'J1_REPORT.md'))
    S = ('31', '41', '43')
    A = M['pairs']['A']['summary']
    # ---- scans: selftest re-scan of the J1 runs == J1 scans (all keys but an / scan_sec / tag)
    for s in S:
        a = V.jload(os.path.join(prof.scans, 'va_s' + s, 'scan.json'))
        b = V.jload(os.path.join(V.J1_SCANS, 'j1_s' + s, 'scan.json'))
        keys = sorted((set(a) | set(b)) - {'an', 'scan_sec', 'tag'})
        diff = [k for k in keys if a.get(k) != b.get(k)]
        check('scan.s%s.equal_to_J1_scan' % s, not diff, 'diff keys %s' % diff)
        check('scan.s%s.shim_skipped_same' % s, a['an']['shim'] == b['an']['shim'], str((a['an']['shim'], b['an']['shim'])))
        ua = V.jload(os.path.join(prof.scans, 'va_s' + s, 'uninserted.json'))
        ub = V.jload(os.path.join(V.J1_SCANS, 'j1_s' + s, 'uninserted.json'))
        ua.pop('tag', None)
        ub.pop('tag', None)
        check('uninserted.s%s.equal_to_J1' % s, ua == ub)
    # ---- exact vs J1 an_metrics summary
    mx = 0.0
    for k in JM['summary']:
        for s in S:
            mx = max(mx, abs(A[k]['per_seed'][s] - JM['summary'][k]['per_seed'][s]), abs(A[k]['base'][s] - JM['summary'][k]['nc'][s]),
                     abs(A[k]['arm'][s] - JM['summary'][k]['j1'][s]))
        mx = max(mx, abs(A[k]['mean'] - JM['summary'][k]['mean']), abs(A[k]['sd'] - JM['summary'][k]['sd']))
    check('metrics.A_equals_J1_an_metrics_summary', mx < 1e-9, 'max abs %g' % mx)
    check('metrics.unions_equal_J1_union', M['unions']['U6VA'] == JM['union_inputs'] == M['unions']['U9'] == M['unions']['U6J1'])
    bmax = max(abs(v) for s in S for v in M['pairs']['B']['deltas'][s].values())
    check('metrics.B_zero', bmax == 0.0, 'max %g' % bmax)
    for pk in ('Bp', 'J1R'):
        dm = max(abs(M['pairs'][pk]['deltas'][s][k] - M['pairs']['A']['deltas'][s][k]) for s in S for k in M['pairs']['A']['deltas'][s])
        check('metrics.%s_equals_A' % pk, dm < 1e-9, 'max %g' % dm)
    for pk in ('A', 'B'):
        check('metrics.pairing_ok_%s' % pk, all(M['pairs'][pk]['pairing'][s]['ok'] for s in S))
        check('metrics.pre900_zero_%s' % pk, all(M['pairs'][pk]['pairing'][s]['max_abs_pre900_delta'] == 0.0 for s in S))
    # ---- J1_REPORT sec.3.1
    sec = R.section('### 3.1 ')
    rows31 = [('① fw_e_main 7링크', 'M1'), ('② 동측 국소 19링크', 'M2'), ('**③ Ω (635링크)**', 'M3'), ('③u urban_omega', 'M3u'),
              ('**④ 전체 + 미삽입**', 'M4'), ('④a 전체 링크 TTT (1,236)', 'M4a'), ('④b 미삽입 (12입력 합집합, NC 앵커)', 'M4b'),
              ('**Ω 밖 (a) ④ − ③** (veh·h)', 'OUT_a'), ('Ω 밖 (b) ④a − ③ (링크만, veh·h)', 'OUT_b'),
              ('**차로변경 제거, 읽는 법 A (`.err` 전체, 대)**', 'REM'), ('차로변경 제거, 읽는 법 B (Ω 밖 링크만, 대, 사후)', 'REM_B')]
    for lab, k in rows31:
        cells = R.row(sec, lab)
        mine = []
        for s in S:
            mine += [A[k]['base'][s], A[k]['arm'][s], A[k]['per_seed'][s]]
        cmp_row('report3.1.%s' % k, ' | '.join(cells[1:]), mine)
    cells = R.row(sec, 'S7 늦은 보고 (J1만, 대)')
    mine = []
    for s in S:
        mine += [M['s7_late']['va_s' + s]['late'], M['s7_late']['va_s' + s]['unique_removals']]
    cmp_row('report3.1.S7', ' | '.join(cells[1:]), mine)
    # ---- sec.3.2
    sec = R.section('### 3.2 ')
    rows32 = [('① fw_e_main 7링크', 'M1'), ('② 동측 국소 19링크', 'M2'), ('**③ Ω (635링크)**', 'M3'), ('③u urban_omega', 'M3u'),
              ('**④ 전체 + 미삽입**', 'M4'), ('④a 전체 링크 TTT (1,236)', 'M4a'), ('④b 미삽입 (12입력 합집합, NC 앵커)', 'M4b'),
              ('**Ω 밖 (a) ④ − ③** (veh·h)', 'OUT_a'), ('Ω 밖 (b) ④a − ③ (링크만, veh·h)', 'OUT_b'),
              ('**차로변경 제거, 읽는 법 A (대)**', 'REM'), ('④b 중 입력 1098 (FW_E 입구)', 'unins_1098'),
              ('④b 중 입력 1099 (FW_W 입구)', 'unins_1099'), ('④b 중 그 밖 10입력', 'unins_other'),
              ('(② 밖) 진출 수신 121·124·126·127', 'x_off_receivers_shared'),
              ('*(사후)* 차로변경 제거, 읽는 법 B (Ω 밖 링크만, 대)', 'REM_B')]
    for lab, k in rows32:
        cells = R.row(sec, lab)
        st = A[k]
        mine = [st['per_seed'][s] for s in S] + [st['mean'], st['sd'], st['ci90'][0], st['ci90'][1], st['neg'], st['pos'],
                                                 st['pct_of_nc']] + list(st['per_seed_pct'])
        noise = V.NOISE.get(k)
        if noise:
            mine.append(noise[1])
        cmp_row('report3.2.%s' % k, ' | '.join(cells[1:11]), mine)
        want = '관측된 차이' if st['ci_excludes_0'] else '0 포함'
        check('report3.2.%s.ci_label' % k, cells[11] == want, '%s vs %s' % (cells[11], want))
    # ---- sec.3.3 labels
    sec = R.section('### 3.3 ')
    for s, lab in (('31', 'v3c3-s31 (재실행)'), ('41', 'v3c3-s41'), ('43', 'v3c3-s43'), ('mean', '3시드 평균')):
        cells = R.row(sec, lab)
        g = ({k: A[k]['mean'] for k in ('M3', 'M4', 'OUT_a', 'M4b', 'REM', 'REM_B')} if s == 'mean'
             else M['pairs']['A']['deltas'][s])
        cmp_row('report3.3.%s.numbers' % s, ' | '.join(cells[1:7]), [g['M3'], g['M4'], g['OUT_a'], g['M4b'], g['REM'], g['REM_B']])
        lb = M['pairs']['A']['labels'][s]
        check('report3.3.%s.label_N' % s, cells[7] == lb['N'], '%s vs %s' % (cells[7], lb['N']))
        check('report3.3.%s.label_W' % s, cells[8] == lb['W_A'] == lb['W_B'], '%s vs %s/%s' % (cells[8], lb['W_A'], lb['W_B']))
    # ---- sec.5 input 1083
    sec = R.section('## 5. ')
    i = F['input_1083']
    for s, sl in (('31', 'v3c3-s31 (재실행)'), ('41', 'v3c3-s41'), ('43', 'v3c3-s43')):
        for arm, al in (('nc3', 'NC3'), ('va', 'J1')):
            cells = R.row(sec, '%s %s' % (al, sl))
            r = i['runs']['%s_s%s' % (arm, s)]
            cmp_row('report5.%s_s%s' % (arm, s), ' | '.join(cells[1:5]),
                    [r['remain_err'], r['inserted'], r['delay_veh_h_nc3_anchor'], r['max_queue_frame'], r['max_queue_frame_t']])
            if arm == 'va':
                ft = i['pairs']['A']['s' + s]['first_gt10_clipped_t']
                if cells[5] == '없음':
                    check('report5.first_gt10.s%s' % s, ft is None, str(ft))
                else:
                    cmp_row('report5.first_gt10.s%s' % s, cells[5], [ft])
    ch = F['link174_chain']
    for li in ch['links']:
        l = str(li['link'])
        cells = R.row(sec, l)
        cmp_row('report5.link%s.geometry' % l, cells[2], [li['length_m'], li['lanes']])
        mine = []
        for s in S:
            v = ch['link_vh'][l]
            mine += [v['nc3_s' + s]['full'], v['va_s' + s]['full'], v['nc3_s' + s]['from_4350'], v['va_s' + s]['from_4350']]
        cmp_row('report5.link%s.vh' % l, ' | '.join(cells[4:]), mine)
    # ---- sec.7 SC1001 EB local
    sec = R.section('## 7. ')
    lab_l = [('10491 커넥터 대수 평균, (P) 1800–7200 s', 'occ_10491.P_1800_7200.mean'),
             ('10491 커넥터 대수 최대, (P)', 'occ_10491.P_1800_7200.max'),
             ('10491 커넥터 대수 평균, (F) 전체', 'occ_10491.F_all.mean'), ('10491 커넥터 대수 최대, (F)', 'occ_10491.F_all.max'),
             ('127 차로 1–2 대수 평균, (P)', 'occ_127_lanes12.P_1800_7200.mean'), ('127 차로 1–2 대수 최대, (P)', 'occ_127_lanes12.P_1800_7200.max'),
             ('127 차로 1–2 대수 평균, (F)', 'occ_127_lanes12.F_all.mean'), ('127 차로 1–2 대수 최대, (F)', 'occ_127_lanes12.F_all.max'),
             ('FW_W 역류 창 비율 (F1 첨두 창)', 'spill_FW_W.frac_peak'), ('FW_W 역류 창 비율 (900–9000 s 창)', 'spill_FW_W.frac_all'),
             ('FW_E 역류 창 비율 (F1 첨두 창)', 'spill_FW_E.frac_peak')]
    for lab, k in lab_l:
        cells = R.row(sec, lab)
        v = L['paired']['A'][k]
        mine = []
        for b, a in zip(v['base'], v['arm']):
            mine += [b, a]
        mine += list(v['per_seed']) + [v['mean'], v['ci90'][0], v['ci90'][1]]
        cmp_row('report7.%s' % k, ' | '.join(cells[1:]), mine)
    ev = [l for l in sec if l.startswith('- FW_W 사건 창 수')][0]
    mine = []
    for s in S:
        for arm in ('nc3', 'va'):
            r = L['runs']['%s_s%s' % (arm, s)]['spill_FW_W']
            mine += [r['n_event_windows']] + ([r['first']] if r['first'] is not None else [])
    evt = re.sub(r'v3c3-s\d+|NC3|J1', ' ', ev.split(':', 1)[1])
    shown_vals = [v for v, _ in nums(evt)]
    check('report7.fw_w_events', shown_vals == [float(x) for x in mine], '%s vs %s' % (shown_vals, mine))
    # ---- sec.8.1 control (J1 = the selftest V-A arm)
    sec = R.section('### 8.1 ')
    KR = {s: K['runs']['va_s' + s] for s in S}

    def rowcmp(lab, fn):
        cells = R.row(sec, lab)
        mine = []
        for s in S:
            mine += fn(KR[s])
        cmp_row('report8.1.%s' % lab[:24], ' | '.join(cells[1:]), mine)
    rowcmp('action JSON 수 (예열 + SDMPC)', lambda r: [r['n_action_json'], len(r['warmup_T']), r['n_sdmpc']])
    rowcmp('런로그 `DECISIONS_OK` / `DECISIONS_FAILED`', lambda r: [float(r['runlog_counters']['DECISIONS_OK'][-1]),
                                                                  float(r['runlog_counters']['DECISIONS_FAILED'][-1])])
    rowcmp('런로그 유지 줄 (시도/유지/실패)', lambda r: [r['runlog_hold_lines'][k] for k in ('DECISION_HOLD_ATTEMPT', 'DECISION_HELD_ON_EXCEPTION ', 'DECISION_HOLD_FAILED')])
    rowcmp('결정 exit 코드', lambda r: [x for kv in sorted((int(k), v) for k, v in r['exit_codes'].items()) for x in kv])
    rowcmp('예열 결정 벽시계 최소–최대 (s)', lambda r: [r['wall_warmup']['min'], r['wall_warmup']['max']])
    rowcmp('SDMPC 결정 벽시계 최소 / 중앙 / 평균 / 최대 (s)', lambda r: [r['wall_sdmpc'][k] for k in ('min', 'median', 'mean', 'max')])
    rowcmp('SDMPC 결정 벽시계 합 (s) / 900 s 넘는 결정', lambda r: [r['wall_sdmpc']['sum'], len(r['wall_sdmpc_gt900_T'])])
    rowcmp('런 벽시계 (`WATCHDOG_EXIT wall_sec`)', lambda r: [r['run_wall_sec']])
    rowcmp('`k9_w1`·`k9_w2a`·`k9_f17b` 있음 (55 중)', lambda r: [r['k9_present'][k] for k in ('k9_w1', 'k9_w2a', 'k9_f17b')])
    cells = R.row(sec, '`selection_status` / converged / feasible')
    for j, s in enumerate(S):
        mine = ' / '.join(json.dumps(KR[s]['selection'][k]) for k in ('selection_status', 'converged', 'feasible'))
        check('report8.1.selection.s%s' % s, cells[1 + j] == mine, '%s vs %s' % (cells[1 + j], mine))
    cells = R.row(sec, '정지선 설치 점검 passed')
    for j, s in enumerate(S):
        check('report8.1.install.s%s' % s, cells[1 + j] == json.dumps(KR[s]['install_check']['passed']))
    for s in S:
        r = KR[s]
        rates = {k: v for m in r['meter_written_rate_vph'].values() for k, v in m.items()}
        greens = {k: v for m in r['meter_written_green_sec'].values() for k, v in m.items()}
        check('report8.1.meters.s%s' % s, len(r['meter_written_rate_vph']) == 8 and set(rates) == {'900.0'} and set(greens) == {'10.0'}
              and all(sum(m.values()) == 61 for m in r['meter_written_rate_vph'].values()), str((rates, greens)))
    cells = R.row(sec, '미터 action JSON `ramp_metering` 값')
    want = ', '.join('%s %s' % (m, list(v)[0]) for m, v in sorted(KR['31']['meter_json_values'].items()))
    check('report8.1.ramp_metering.s31', cells[1] == want, '%s vs %s' % (cells[1], want))
    rowcmp('VSL 써진 행 (러너 로그, 속도: 행)', lambda r: [x for k, v in sorted(r['vsl_written_speed_rows'].items(), key=lambda kv: float(kv[0]))
                                                       for x in (float(k), v)])
    # ---- exact vs J1 tool JSON (sec.8.2, sec.9, local)
    for s in S:
        a, b = KR[s]['vsl_stats'], JK['runs']['s' + s]['vsl_stats']
        for k in ('FW_E', 'FW_W'):
            for kk in ('dist_by_head', 'any_lt110_T', 'frac_any_lt110', 'first_T', 'longest_run_decisions', 'transitions', 'future_blocks'):
                check('control.vsl.s%s.%s.%s' % (s, k, kk), a[k][kk] == b[k][kk])
        check('control.vsl.s%s.exposure' % s, a['exposure_veh_km'] == b['exposure_veh_km'])
        for kk in ('objective_lt110_decisions', 'objective_110_decisions'):
            check('control.vsl.s%s.%s' % (s, kk), all(a[kk][x] == b[kk][x] for x in ('n', 'selected_objective', 'held_objective', 'selected_minus_held')))
        for kk in ('meter_json_values', 'meter_written_green_sec', 'meter_written_rate_vph', 'vsl_written_speed_rows', 'selection',
                   'install_check', 'k9_present', 'exit_codes', 'wall_warmup', 'wall_sdmpc', 'runlog_counters'):
            check('control.s%s.%s' % (s, kk), KR[s][kk] == JK['runs']['s' + s][kk])
        dC = L['desspeed']['s' + s]['by_level']['C_command']
        jC = JL['desspeed']['s' + s]['by_level']
        okC = all(dC[c][g]['n'] == jC[c][g]['n'] and dC[c][g]['in_band'] == jC[c][g]['in_band'] for c in jC for g in jC[c]) and set(dC) == set(jC)
        check('local.desspeed_C.s%s' % s, okC)
        jM = JF['desspeed_two_readings']['s' + s]
        dz = L['desspeed']['s' + s]['by_level_zone']
        okM = all(dz[rd][c][z][g]['n'] == jM[rd][c][z][g]['n'] and dz[rd][c][z][g]['in_band'] == jM[rd][c][z][g]['in_band']
                  for rd in jM for c in jM[rd] for z in jM[rd][c] for g in jM[rd][c][z])
        check('local.desspeed_CM_by_zone.s%s' % s, okM)
        for tag_v, tag_j in (('va_s' + s, 'j1_s' + s), ('nc3_s' + s, 'nc3_s' + s)):
            a, b = L['runs'][tag_v], JL['runs'][tag_j]
            check('local.%s.counts' % tag_v, all(a[k][w] == b[k][w] for k in ('occ_10491', 'occ_127_lanes12') for w in ('P_1800_7200', 'F_all'))
                  and all(a[k][x] == b[k][x] for k in ('spill_FW_W', 'spill_FW_E') for x in ('frac_all', 'frac_peak', 'n_event_windows', 'first'))
                  and a['n_frames'] == b['n_frames'] and a['rows'] == b['rows'] and a['skipped'] == b['skipped'])
    # tables built and B-tables zero
    check('tables.built', all(k in TB for k in ('LEVELS_S31', 'SUMMARY_A', 'SUMMARY_B', 'LABELS_A', 'LABELS_B', 'SPLIT_A', 'INPUT1083',
                                               'LINK174', 'SC109_EAST', 'SC109_P3', 'FLOOR', 'HOLD_PREV', 'WALL', 'METER_VSL', 'DESSPEED')))
    check('tables.no_forbidden_word', not any(w in v for v in TB.values() for w in ('개선', '이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌')))
    ok = all(c['ok'] for c in CHECKS)
    res = {'schema': 'k92-va-analysis-selftest/v1', 'all_ok': ok, 'n_checks': len(CHECKS), 'n_bad': sum(not c['ok'] for c in CHECKS),
           'checks': CHECKS, 'script_sha256': V.sha(os.path.abspath(__file__))}
    V.jdump(res, os.path.join(out, 'va_selftest.json'))
    for c in CHECKS:
        if not c['ok']:
            print('BAD', c['check'], c['detail'])
    print('CHECKS %d/%d' % (len(CHECKS) - res['n_bad'], len(CHECKS)))
    print('ALL_OK' if ok else 'NOT_OK')


if __name__ == '__main__':
    main()
