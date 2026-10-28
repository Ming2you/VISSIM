"""Q-V3 report collector, r3 run (data after; mechanical only).  Reads the H2 job outputs (all plant_A states), their
jobcheck records, the queue .done records, decl/R3_MARKS.json and the L3 tables JSON; writes one JSON and markdown
fragments for QV3_REPORT.md r2.  No plant run, no new definition: every number is a field of probe.json /
jobcheck.json / job_summary.json / the tables JSON, or a difference already defined in PRE_VP_FIXED section 3.3
(J(ARM v) - J(ARM 110), J(ARM v) - J(REC scalar)), or a count / min / max of those fields.

The r3 reading of PRE_VP_R3 section 1.1 is applied to the tables tool's stop list: an entry
{"check": "R1_objective_bit_equal", "value": false} is an R1 bit REPORT (not a stop-rule hit) when the same state's
jobcheck has no hit and its R1 objective is within 1e-9 veh*h (jobcheck r1_objective_ok, or for a jobcheck written by
the r2 tool, |R1_objective_diff| <= 1e-9 from probe.json).  Every other entry is listed as a stop-rule hit.

    python -B qv3r3_collect.py <tables.json> <out.json> <out.md>
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import vp_common as C  # noqa: E402

ARMS = [110, 101, 100, 90]
TOL = 1e-9


def fmt(x, nd=3):
    if x is None:
        return '—'
    if isinstance(x, bool):
        return '참' if x else '거짓'
    if isinstance(x, int):
        return str(x)
    return ('%.' + str(nd) + 'f') % x


def sci(x):
    return '—' if x is None else ('%.1e' % x if x != 0 else '0')


def sha(p):
    p = Path(p)
    return C.sha256_file(p) if p.is_file() else None


def r1_obj_ok(ck, jc):
    """r3 R1 objective reading: jobcheck r1_objective_ok when present, else probe field, else the recorded diff."""
    if isinstance(jc.get('r1_objective_ok'), bool):
        return jc['r1_objective_ok'], 'jobcheck r3'
    if isinstance(ck.get('R1_objective_within_1e-9'), bool):
        return ck['R1_objective_within_1e-9'], 'probe r3 field'
    d = ck.get('R1_objective_diff')
    if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d):
        return False, 'no diff'
    return abs(d) <= TOL, 'probe diff (r2 jobcheck)'


def main():
    tab_path, out_json, out_md = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    tabs = C.read_json(tab_path) or {}
    states_decl = C.read_json(C.DECL / 'VP_STATES.json')
    decl = {(r['label'], int(r['T'])): r for r in states_decl['probe_A']}
    decl_B = {(r['label'], int(r['T'])): r for r in (states_decl.get('probe_B') or [])}
    marks = C.read_json(C.DECL / 'R3_MARKS.json') or {}
    mark_by_job = {m['job']: m for m in marks.get('marks') or []}
    ab = tabs.get('AB') or {}
    by = {(s['label'], s['T']): s for s in ab.get('states', [])}
    rows = []
    for jd in sorted((C.OUT / 'plant_A').iterdir()):
        if not jd.is_dir():
            continue
        probe = C.read_json(jd / 'probe.json') or {}
        jc = C.read_json(jd / 'jobcheck.json') or {}
        js = C.read_json(jd / 'job_summary.json') or {}
        st = (probe.get('spec') or {}).get('state') or {}
        label, T = st.get('label'), int(st.get('T', -1))
        tag = 'A_%s_T%06d' % (label, T)
        done = C.read_json(C.VP / 'logs' / 'plantA' / (tag + '.done')) or {}
        ev = probe.get('evaluations') or {}
        ck = probe.get('checks') or {}
        plans = probe.get('plans') or {}
        tok = {k: (v or {}).get('token') for k, v in plans.items()}
        J = {k: v.get('objective_veh_h') for k, v in ev.items()}
        ok3, how3 = r1_obj_ok(ck, jc)
        d = decl.get((label, T)) or {}
        db = decl_B.get((label, T)) or {}
        row = {'job': jd.name, 'queue_tag': tag, 'label': label, 'T': T, 'tag': st.get('tag'),
               'kind_declared': d.get('kind'),
               'written_fwe': {k: db.get(k) for k in ('written_fwe_T', 'written_fwe_T150', 'written_fwe_T300')},
               'done': done, 'exit_code': js.get('exit_code'), 'wall_sec': js.get('wall_sec'), 'killed': js.get('killed'),
               'action_written': js.get('action_written'), 'hook_files': js.get('hook_files'),
               'probe_sha256': sha(jd / 'probe.json'), 'jobcheck_sha256': sha(jd / 'jobcheck.json'),
               'job_summary_sha256': sha(jd / 'job_summary.json'),
               'jobcheck_hits': jc.get('hits'), 'jobcheck_form': 'r3' if 'r1_rule' in jc else 'r2',
               'hooks_ok': {k: v.get('ok') for k, v in (jc.get('hooks') or {}).items()},
               'R0_rec_token_equals_recorded': ck.get('R0_rec_token_equals_recorded'),
               'R1_objective_bit_equal': ck.get('R1_objective_bit_equal'),
               'R1_objective_diff': ck.get('R1_objective_diff'),
               'R1_objective_within_1e-9_probe': ck.get('R1_objective_within_1e-9'),
               'R1_objective_ok_r3': ok3, 'R1_objective_ok_r3_source': how3,
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
               'J': J, 'recorded_selected_objective': (probe.get('recorded') or {}).get('selected_objective'),
               'setup_sec': probe.get('setup_sec'), 'total_sec': probe.get('total_sec'),
               'price_receipt_committed': probe.get('price_receipt_committed'),
               'policy_sha256': probe.get('policy_sha256'),
               'probe_stop': probe.get('stop'), 'probe_errors': probe.get('errors'),
               'mark': (mark_by_job.get(tag) or {}).get('mark_ko')}
        rec = J.get('R2_REC_scalar')
        row['J_ARM_minus_REC_scalar'] = {str(v): (J['ARM%d_scalar' % v] - rec) if ('ARM%d_scalar' % v in J and rec is not None)
                                         else None for v in ARMS}
        row['J_EXEC_minus_REC_scalar'] = (J['EXEC_scalar'] - rec) if ('EXEC_scalar' in J and rec is not None) else None
        s = by.get((label, T)) or {}
        arms = s.get('arms') or {}
        row['arms'] = {v: {k: a.get(k) for k in ('J', 'dJ_vs_110', 'sign_vs_110', 'dJ_vs_REC', 'sign_vs_REC', 'd_cost_FW_E',
                                                 'd_cost_other', 'origin_queue_veh_h', 'd_origin_queue_veh_h')}
                       for v, a in arms.items()}
        row['dJ_101_minus_100'] = s.get('dJ_101_minus_100')
        row['exits'] = s.get('exits')
        bx = s.get('B_exec') or {}
        row['B_exec_zone_w450'] = {z: ((bx.get('w450') or {}).get('zones') or {}).get(z) for z in C.ZONE_ORDER} if bx else None
        ib = s.get('initial_bias') or {}
        izs = ib.get('zones') or {}
        sp = [abs(v.get('e_speed')) for v in izs.values() if isinstance(v.get('e_speed'), (int, float))]
        sk = [abs(v.get('e_stock')) for v in izs.values() if isinstance(v.get('e_stock'), (int, float))]
        row['initial_bias_max_abs'] = {'zone_speed': max(sp) if sp else None, 'zone_stock': max(sk) if sk else None,
                                       'frames': ib.get('frames')}
        rows.append(row)
    # stop list of the tables tool, split by the r3 reading (PRE_VP_R3 1.1)
    rowj = {r['job']: r for r in rows}
    bit_reports, hits = [], []
    for x in ab.get('stops') or []:
        r = rowj.get(x.get('job'))
        if (x.get('check') == 'R1_objective_bit_equal' and x.get('value') is False and r is not None
                and not (r['jobcheck_hits'] or []) and r['R1_objective_ok_r3'] is True and r['R1_costs_within_1e-9'] is True):
            bit_reports.append({'job': x['job'], 'R1_objective_diff': r['R1_objective_diff']})
        else:
            hits.append(x)
    # per-group spans (min / max of fields already in the tables)
    groups = {}
    for kind, tags in (('101', ('A2', 'A3')), ('110', ('A1', 'A4'))):
        g = [r for r in rows if r['tag'] in tags]
        gg = {'n_states': len(g)}
        for v in ('101', '100', '90'):
            fw = [r['arms'][v]['d_cost_FW_E'] for r in g if v in r['arms'] and r['arms'][v].get('d_cost_FW_E') is not None]
            ot = [r['arms'][v]['d_cost_other'] for r in g if v in r['arms'] and r['arms'][v].get('d_cost_other') is not None]
            oq = [r['arms'][v]['d_origin_queue_veh_h'] for r in g if v in r['arms']
                  and r['arms'][v].get('d_origin_queue_veh_h') is not None]
            gg[v] = {'d_cost_FW_E_range': [min(fw), max(fw)] if fw else None, 'n_FW_E_pos': sum(1 for x in fw if x > 0),
                     'd_cost_other_range': [min(ot), max(ot)] if ot else None, 'n_other_neg': sum(1 for x in ot if x < 0),
                     'd_origin_queue_range': [min(oq), max(oq)] if oq else None}
        d10 = [r['dJ_101_minus_100'] for r in g if r.get('dJ_101_minus_100') is not None]
        gg['dJ_101_minus_100_range'] = [min(d10), max(d10)] if d10 else None
        gg['n_dJ_101_minus_100_neg'] = sum(1 for x in d10 if x < 0)
        arm110rec = [r['J_ARM_minus_REC_scalar']['110'] for r in g if r['J_ARM_minus_REC_scalar'].get('110') is not None]
        gg['J_ARM110_minus_REC_range'] = [min(arm110rec), max(arm110rec)] if arm110rec else None
        gg['n_J_ARM110_minus_REC_neg_le_-0.01'] = sum(1 for x in arm110rec if x <= -0.01)
        groups[kind] = gg
    x1 = {}
    for r in rows:
        for lab, x in (r.get('exits') or {}).items():
            b = (x or {}).get('blocked_veh') or {}
            for o, v in b.items():
                x1.setdefault(lab, {}).setdefault(o, []).append(v)
    x1_max = {lab: {o: max(vs) for o, vs in d.items()} for lab, d in x1.items()}
    res = {'schema': 'qv3r3-collect/1', 'made_kst': C.kst(), 'tables_sha256': sha(tab_path),
           'collector_sha256': sha(__file__), 'states': rows, 'n_states': len(rows),
           'AB_stops_raw': ab.get('stops'), 'AB_stops_r3_bit_reports': bit_reports, 'AB_stops_r3_hits': hits,
           'AB_summary': ab.get('summary'), 'group_spans': groups, 'X1_max_over_states': x1_max,
           'R3_MARKS_sha256': sha(C.DECL / 'R3_MARKS.json')}
    C.write_json(out_json, res)
    # ---- markdown fragments
    L = ['### 점검 표 (상태별; R1 은 r3 규칙, 비트 같음은 보고만)', '',
         '| 상태 | T | 묶음 | 종료 | 벽시계 s | R0 | R1 목적 차 (veh·h) | R1 목적 ≤ 1e-9 | R1 목적 비트 | R1 비용 최대 차 | R2 − R1 | R3 | REPACK 토큰 = REC | 훅 | jobcheck 걸림 | 표시 |',
         '|---|---:|---|---:|---:|---|---:|---|---|---:|---:|---|---|---|---:|---|']
    for r in rows:
        hk = r['hooks_ok']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s |' % (
            r['label'], r['T'], r['tag'], r['exit_code'], fmt(r['wall_sec'], 0), fmt(r['R0_rec_token_equals_recorded']),
            sci(r['R1_objective_diff']), fmt(r['R1_objective_ok_r3']), fmt(r['R1_objective_bit_equal']),
            sci(r['R1_costs_max_abs_diff']), sci(r['R2_minus_R1']), fmt(r['R3_repack_bit_equal']),
            fmt(r['REPACK_token_equals_REC_token']), '%d/%d' % (sum(1 for v in hk.values() if v), len(hk)),
            len(r['jobcheck_hits'] or []), r['mark'] or ''))
    L.append('')
    L.append('### J(팔) − J(REC 스칼라) (veh·h / 450 s; 스칼라 경로끼리) 와 계획의 구역 머리 10 값')
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
    L.append('### 탐침 B: 구역 속도 w450 — plant · VISSIM (km/h, 실행 계획) 와 시작 편향 최대 |e|')
    L.append('')
    zs = ('B1', 'M1', 'VSa', "VS0'", 'VSb')
    L.append('| 상태 | T | 묶음 | ' + ' | '.join('%s plant · VISSIM' % z for z in zs) + ' | 시작 |e| 속도 · 재고 |')
    L.append('|---|---:|---|' + '---|' * len(zs) + '---|')
    for r in rows:
        zz = r.get('B_exec_zone_w450') or {}

        def pv(z):
            v = zz.get(z) or {}
            return '%s · %s' % (fmt((v.get('plant') or {}).get('speed'), 1), fmt((v.get('vissim') or {}).get('speed'), 1))
        ib = r['initial_bias_max_abs']
        L.append('| %s | %d | %s | %s | %s · %s |' % (r['label'], r['T'], r['tag'], ' | '.join(pv(z) for z in zs),
                                                   fmt(ib['zone_speed'], 1), fmt(ib['zone_stock'], 1)))
    L.append('')
    Path(out_md).write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('collected %d states; tables stops raw %d -> r3 bit reports %d, hits %d' % (
        len(rows), len(ab.get('stops') or []), len(bit_reports), len(hits)))


if __name__ == '__main__':
    main()
