"""Q-V3 report collector (data after; mechanical only).  Reads the H2 job outputs and the L3 tables, writes
runs/qv3_collect.json (+ .md fragments) for QV3_REPORT.md.  No plant run, no new definition: every number is a field
of probe.json / jobcheck.json / job_summary.json / vp_tables.json, or a difference already defined in PRE_VP_FIXED
section 3.3 (J(ARM v) - J(ARM 110), J(ARM v) - J(REC scalar)).

    python -B qv3_collect.py <vp_tables.json> <out.json> <out.md>
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vp_common as C  # noqa: E402

ARMS = [110, 101, 100, 90]


def fmt(x, nd=3):
    if x is None:
        return '—'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, int):
        return str(x)
    return ('%.' + str(nd) + 'f') % x


def main():
    tab_path, out_json, out_md = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    tabs = C.read_json(tab_path)
    states_decl = C.read_json(C.DECL / 'VP_STATES.json')
    kinds = {(r['label'], int(r['T'])): r for r in states_decl['probe_A']}
    rows = []
    for jd in sorted((C.OUT / 'plant_A').iterdir()):
        if not jd.is_dir():
            continue
        probe = C.read_json(jd / 'probe.json') or {}
        jc = C.read_json(jd / 'jobcheck.json') or {}
        js = C.read_json(jd / 'job_summary.json') or {}
        st = (probe.get('spec') or {}).get('state') or {}
        label, T = st.get('label'), int(st.get('T', -1))
        ev = probe.get('evaluations') or {}
        ck = probe.get('checks') or {}
        plans = probe.get('plans') or {}
        tok = {k: (v or {}).get('token') for k, v in plans.items()}
        J = {k: v.get('objective_veh_h') for k, v in ev.items()}
        row = {'job': jd.name, 'label': label, 'T': T, 'tag': st.get('tag'),
               'kind_declared': (kinds.get((label, T)) or {}).get('kind'),
               'exit_code': js.get('exit_code'), 'wall_sec': js.get('wall_sec'), 'killed': js.get('killed'),
               'action_written': js.get('action_written'), 'hook_files': js.get('hook_files'),
               'probe_sha256': C.sha256_file(jd / 'probe.json') if (jd / 'probe.json').is_file() else None,
               'jobcheck_sha256': C.sha256_file(jd / 'jobcheck.json') if (jd / 'jobcheck.json').is_file() else None,
               'job_summary_sha256': C.sha256_file(jd / 'job_summary.json') if (jd / 'job_summary.json').is_file() else None,
               'jobcheck_hits': jc.get('hits'), 'hooks_ok': {k: v.get('ok') for k, v in (jc.get('hooks') or {}).items()},
               'R0_rec_token_equals_recorded': ck.get('R0_rec_token_equals_recorded'),
               'R1_objective_bit_equal': ck.get('R1_objective_bit_equal'),
               'R1_objective_diff': ck.get('R1_objective_diff'),
               'R1_costs_same_keys': ck.get('R1_costs_same_keys'),
               'R1_costs_max_abs_diff': ck.get('R1_costs_max_abs_diff'),
               'R1_costs_within_1e-9': ck.get('R1_costs_within_1e-9'),
               'R2_minus_R1': ck.get('R2_minus_R1'),
               'R3_repack_bit_equal': ck.get('R3_repack_bit_equal'),
               'REPACK_token_equals_REC_token': (tok.get('REPACK') is not None and tok.get('REPACK') == tok.get('REC')),
               'ARM_token_equals_REC_token': {str(v): tok.get('ARM%d' % v) == tok.get('REC') for v in ARMS},
               'EXEC_token_equals_REC_token': tok.get('EXEC') == tok.get('REC'),
               'plan_vsl': {k: (v or {}).get('vsl') for k, v in plans.items()},
               'n_worker_runs': len(probe.get('runs') or []),
               'distinct_scalar_requests': len({r.get('request_sha256') for r in probe.get('runs') or []
                                                if r.get('batch') == 'SCALAR'}),
               'J': J, 'recorded_selected_objective': (probe.get('recorded') or {}).get('selected_objective'),
               'setup_sec': probe.get('setup_sec'), 'total_sec': probe.get('total_sec'),
               'price_receipt_committed': probe.get('price_receipt_committed'),
               'policy_sha256': probe.get('policy_sha256')}
        rec = J.get('R2_REC_scalar')
        row['J_ARM_minus_REC_scalar'] = {str(v): (J['ARM%d_scalar' % v] - rec) if ('ARM%d_scalar' % v in J and rec is not None)
                                         else None for v in ARMS}
        row['J_EXEC_minus_REC_scalar'] = (J['EXEC_scalar'] - rec) if ('EXEC_scalar' in J and rec is not None) else None
        rows.append(row)
    ab = (tabs or {}).get('AB') or {}
    by = {(s['label'], s['T']): s for s in ab.get('states', [])}
    for r in rows:
        s = by.get((r['label'], r['T'])) or {}
        arms = s.get('arms') or {}
        r['arms'] = {v: {k: a.get(k) for k in ('J', 'dJ_vs_110', 'sign_vs_110', 'dJ_vs_REC', 'sign_vs_REC', 'd_cost_FW_E',
                                               'd_cost_other', 'origin_queue_veh_h', 'd_origin_queue_veh_h')}
                     for v, a in arms.items()}
        r['dJ_101_minus_100'] = s.get('dJ_101_minus_100')
        r['exits'] = s.get('exits')
    res = {'schema': 'qv3-collect/1', 'made_kst': C.kst(), 'tables_sha256': C.sha256_file(tab_path),
           'collector_sha256': C.sha256_file(__file__), 'states': rows,
           'AB_stops': ab.get('stops'), 'AB_summary': ab.get('summary')}
    C.write_json(out_json, res)
    # ---- markdown fragments
    L = []
    L.append('### 점검 표 (상태별; 표 도구 밖 한 줄 대조 포함)')
    L.append('')
    L.append('| 상태 | T | 묶음 | 종료 | 벽시계 s | R0 | R1 목적 비트 | R1 비용 최대 차 | R2 − R1 | R3 | REPACK 토큰 = REC | 훅 6개 | 멈춤 걸림 |')
    L.append('|---|---:|---|---:|---:|---|---|---:|---:|---|---|---|---:|')
    for r in rows:
        hk = r['hooks_ok']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d |' % (
            r['label'], r['T'], r['tag'], r['exit_code'], fmt(r['wall_sec'], 0), fmt(r['R0_rec_token_equals_recorded']),
            fmt(r['R1_objective_bit_equal']), ('%.1e' % r['R1_costs_max_abs_diff']) if r['R1_costs_max_abs_diff'] is not None else '—',
            ('%.1e' % r['R2_minus_R1']) if r['R2_minus_R1'] is not None else '—', fmt(r['R3_repack_bit_equal']),
            fmt(r['REPACK_token_equals_REC_token']), '%d/%d' % (sum(1 for v in hk.values() if v), len(hk)),
            len(r['jobcheck_hits'] or [])))
    L.append('')
    L.append('### J(팔) − J(REC 스칼라) (veh·h / 450 s; 스칼라 경로끼리) 와 REC 계획의 구역 머리 10 값')
    L.append('')
    L.append('| 상태 | T | 묶음 | REC 머리10 (블록 0/1/2) | EXEC 머리10 | 110 | 101 | 100 | 90 | EXEC − REC |')
    L.append('|---|---:|---|---|---|---:|---:|---:|---:|---:|')
    for r in rows:
        def hv(name):
            v = (r['plan_vsl'] or {}).get(name) or []
            return '/'.join(','.join('%g' % x for x in (b.get('zone_head_10') or [])) for b in v)
        d = r['J_ARM_minus_REC_scalar']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], r['tag'], hv('REC'), hv('EXEC'), fmt(d['110']), fmt(d['101']), fmt(d['100']), fmt(d['90']),
            fmt(r['J_EXEC_minus_REC_scalar'])))
    L.append('')
    L.append('### 소유자 비용 차 (팔 − 110, veh·h / 450 s): FW_E · 나머지 합')
    L.append('')
    L.append('| 상태 | T | 묶음 | 101 FW_E · 나머지 | 100 FW_E · 나머지 | 90 FW_E · 나머지 | 입구대기 110 (veh·h) | Δ입구대기 101 · 100 · 90 |')
    L.append('|---|---:|---|---|---|---|---:|---|')
    for r in rows:
        a = r['arms']
        L.append('| %s | %d | %s | %s · %s | %s · %s | %s · %s | %s | %s · %s · %s |' % (
            r['label'], r['T'], r['tag'],
            fmt((a.get('101') or {}).get('d_cost_FW_E')), fmt((a.get('101') or {}).get('d_cost_other')),
            fmt((a.get('100') or {}).get('d_cost_FW_E')), fmt((a.get('100') or {}).get('d_cost_other')),
            fmt((a.get('90') or {}).get('d_cost_FW_E')), fmt((a.get('90') or {}).get('d_cost_other')),
            fmt((a.get('110') or {}).get('origin_queue_veh_h')),
            fmt((a.get('101') or {}).get('d_origin_queue_veh_h')), fmt((a.get('100') or {}).get('d_origin_queue_veh_h')),
            fmt((a.get('90') or {}).get('d_origin_queue_veh_h'))))
    L.append('')
    L.append('### 팔별 출구 막힘 X1 (veh, w450): 10481(셀 18) · 10483(셀 20)')
    L.append('')
    L.append('| 상태 | T | 묶음 | 110 | 101 | 100 | 90 | EXEC |')
    L.append('|---|---:|---|---|---|---|---|---|')
    for r in rows:
        ex = r.get('exits') or {}

        def xb(lab):
            x = ex.get(lab)
            if not x:
                return '못 냄'
            b = x.get('blocked_veh') or {}
            return '%s · %s' % (fmt(b.get('10481'), 1), fmt(b.get('10483'), 1))
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s |' % (
            r['label'], r['T'], r['tag'], xb('ARM110_scalar'), xb('ARM101_scalar'), xb('ARM100_scalar'),
            xb('ARM90_scalar'), xb('EXEC_scalar')))
    L.append('')
    Path(out_md).write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('collected %d states' % len(rows))


if __name__ == '__main__':
    main()
