"""Audit completed V3 decision records only; no model, native or FZP imports.

Default outputs are decision_audit.json/csv/md beside this script. Existing
outputs are never overwritten; use --output-prefix for an independent rerun.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
RUN = 'codex_fid_cl9000_s13_v3'
KEY_TIMES = (900, 2400, 3150, 4500, 6300)
OWN_PAYOFF_SCOPE = ('Recorded owner cost including installed fixed prices; '
                    'neither pure Omega TTT nor an additive realized TTT gain')
FIELDS = {
    'selected_omega': '$.selected_diagnostics.joint_shared_response.objective_veh_h',
    'beta_seconds': '$.selected_price_field.context.beta_seconds',
    'held_quantity': '$.selection.actual_hold_validation.quantity_constraints',
    'held_response_token': '$.selection.actual_hold_validation.nuf_initialization.reference_response_token',
    'accepted_owner_payoff': '$.selected_diagnostics.joint_shared_response.search.accepted_updates[]',
    'candidate_rows': '$.selection.candidates[index in $.selection.attempted_indices]',
    'final_gap': '$.selected_diagnostics.joint_shared_response.per_owner',
    'selected_quantity': '$.selected_diagnostics.joint_shared_response.quantity_constraints',
    'selection_status': '$.selection.selection_status',
    'wall_sec': '$.decision_budget.wall_sec',
    'written_binding': 'action_<time>.joint_written.json: $.written_command_binding_passed',
}


def stats(values):
    return {'min': min(values), 'median': statistics.median(values),
            'max': max(values)} if values else None


def counts(values):
    return dict(collections.Counter(str(v) for v in values))


def quantity(q):
    return {kind: {key: q.get(kind, {}).get(key) for key in
                  ('actual', 'target', 'residual', 'violation', 'tolerance', 'satisfied')}
            for kind in ('np', 'nuf')}


def csv_commands(payload):
    rows = list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'))))
    return {
        'vsl': {r['dsd_no']: float(r['speed_kph']) for r in rows if r['kind'] == 'vsl'},
        'meter': {r['id']: [float(r['green_sec']), float(r['rate_vph'])]
                  for r in rows if r['kind'] == 'ramp_meter'},
        'green': {r['id']: [float(r[k]) for k in ('p1_green', 'p2_green', 'p3_green', 'p4_green')]
                  for r in rows if r['kind'] == 'signal'},
        'offset': {r['id']: float(r['offset']) for r in rows if r['kind'] == 'signal'},
    }, len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default=RUN)
    parser.add_argument('--start', type=int, default=900)
    parser.add_argument('--end', type=int, default=8700)
    parser.add_argument('--output-prefix', type=Path,
                        default=Path(__file__).with_name('decision_audit'))
    args = parser.parse_args()
    if args.run != RUN or args.start < 900 or args.end > 8700:
        raise ValueError('This bounded audit is specific to completed V3 decisions 900..8700')
    if args.start % 150 or args.end % 150 or args.end < args.start:
        raise ValueError('Expected ordered 150-second decision boundaries')
    paths = [args.output_prefix.with_suffix(s) for s in ('.json', '.csv', '.md')]
    if any(p.exists() for p in paths):
        raise FileExistsError('Use a fresh --output-prefix; original evidence is preserved')
    folder = ROOT / 'evaluation/runs' / args.run / ('decisions_' + args.run)
    pins = []

    def read(name, decode=True):
        path = folder / name
        payload = path.read_bytes()
        pins.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(payload),
                     'sha256': hashlib.sha256(payload).hexdigest()})
        return json.loads(payload.decode('utf-8-sig')) if decode else payload

    previous_csv, _ = csv_commands(read(f'action_{args.start-150:06d}.csv', False))
    decisions = []
    candidate_rows = []
    for sec in range(args.start, args.end + 1, 150):
        stem = f'action_{sec:06d}'
        joint = read(stem + '.joint.json')
        action = read(stem + '.json')
        csv_bytes = read(stem + '.csv', False)
        written = read(stem + '.joint_written.json')
        progress_bytes = read(stem + '.joint.progress.jsonl', False)
        progress = [json.loads(line) for line in progress_bytes.decode('utf-8-sig').splitlines() if line]
        selection = joint['selection']
        response = joint['selected_diagnostics']['joint_shared_response']
        if joint['completed'] is not True or joint['sim_sec'] != sec:
            raise ValueError(f'Not a completed matching decision: {sec}')
        beta = joint['selected_price_field']['context']['beta_seconds']
        if beta != 0.0:
            raise ValueError('A nonzero-beta objective cannot be labeled pure predicted TTT')
        selected = next(c for c in selection['candidates'] if c['index'] == selection['selected_index'])
        final_omega = response['objective_veh_h']
        if final_omega != joint['leader_objective'] or final_omega != selected['objective_veh_h']:
            raise ValueError('Selected Omega objective fields disagree')
        if final_omega != action['metadata']['leader_objective']:
            raise ValueError('Persisted action objective differs from joint selection')
        if written['action_csv']['sha256'] != hashlib.sha256(csv_bytes).hexdigest():
            raise ValueError('CSV differs from its written-command binding')
        if written['action_json']['sha256'] != pins[-4]['sha256']:
            raise ValueError('Action JSON differs from its written-command binding')
        commands, row_count = csv_commands(csv_bytes)
        changes = {}
        for field, values in commands.items():
            # Warmup CSV deliberately has no controlled signal rows. Do not
            # count the initial native-to-controlled transition as a measured
            # duration/offset change from those absent rows.
            old = previous_csv[field]
            changes[field] = (None if not old else
                              sorted(k for k in set(values) | set(old) if values.get(k) != old.get(k)))
        previous_csv = commands
        search = response.get('search', {})
        updates = [{k: update.get(k) for k in ('sweep', 'owner', 'from_cost', 'to_cost', 'gap')}
                   for update in search.get('accepted_updates', [])]
        final_owners = response['per_owner']
        search_owners = {owner for sweep in search.get('search_sweeps', [])
                         for owner, item in sweep.get('owners', {}).items()
                         if item.get('evaluations', 0) > 0}
        held = selection.get('actual_hold_validation', {})
        # The retained hold validation contains quantities and response tokens,
        # not an Omega objective. Owner prices / external secants cannot fill it.
        held_omega = held.get('objective_veh_h')
        if held_omega is not None:
            raise ValueError('New held-objective schema requires an explicit semantics review')
        attempted = []
        for index in selection['attempted_indices']:
            c = next(x for x in selection['candidates'] if x['index'] == index)
            init = c.get('initializer_evidence', {})
            row = {k: c.get(k) for k in ('index', 'target_np_veh', 'target_nuf_veh_h',
                   'meter_bank_index', 'status', 'objective_veh_h', 'elapsed_sec', 'evaluations')}
            row.update({'selected': index == selection['selected_index'],
                        'game_error': c.get('game_error'),
                        'initializer_quantity': quantity(init.get('quantity_constraints', {})),
                        'initializer_feasible': init.get('initializer_feasible'),
                        'candidate_feasibility_known': init.get('candidate_feasibility_known'),
                        'restoration_status': init.get('restoration_status'),
                        'leader_domain_infeasible': init.get('leader_domain_infeasible'),
                        'physical_meter_rows_token': c['physical_meter_rows_token'],
                        'grouped_meter_rates_veh_h': c['grouped_meter_rates_veh_h']})
            attempted.append(row)
            candidate_rows.append({'sim_sec': sec, **row})
        stage_counts = counts(r['stage'] for r in progress)
        starts = [{k: r[k] for k in ('elapsed_sec', 'index', 'target_np_veh', 'target_nuf_veh_h')}
                  for r in progress if r['stage'] == 'joint_leader_candidate_start']
        clock = joint['decision_budget']
        entry = {
            'sim_sec': sec, 'horizon_end_sec': sec + 450, 'beta_seconds': beta,
            'held_predicted_omega_ttt_veh_h': None,
            'selected_predicted_omega_ttt_veh_h': final_omega,
            'predicted_omega_ttt_gain_veh_h': None,
            'predicted_gain_status': 'missing_held_omega_objective_in_retained_records',
            'held_response_token': held.get('nuf_initialization', {}).get('reference_response_token'),
            'held_context_matches_final': held.get('nuf_initialization', {}).get('frozen_context_token') == response['frozen_context_token'],
            'held_feasible_under_inherited_np_target': held.get('feasible'),
            'held_quantity': quantity(held.get('quantity_constraints', {})),
            'selected_quantity': quantity(response['quantity_constraints']),
            'domain_count': selection['domain_count'],
            'attempted_indices': selection['attempted_indices'],
            'ranking_indices': selection['ranking_indices'],
            'selected_index': selection['selected_index'],
            'selected_np_cap_veh': selected['target_np_veh'],
            'selected_nuf_target_veh_h': selected['target_nuf_veh_h'],
            'selected_meter_bank_index': selected['meter_bank_index'],
            'candidate_status_counts': counts(c['status'] for c in selection['candidates']),
            'attempted_candidates': attempted,
            'unknown_candidates': len(selection['unknown_candidate_indices']),
            'selection_status': selection['selection_status'], 'selection_stop_reason': selection['stop_reason'],
            'selection_failure': selection['failure'], 'leader_optimum_certified': selection['leader_optimum_certified'],
            'leader_domain_infeasible': selection['leader_domain_infeasible'],
            'search_status': response['search_status'], 'game_error': response.get('error'),
            'accepted_owner_updates': updates, 'accepted_owner_payoff_scope': OWN_PAYOFF_SCOPE,
            'search_owners_visited': sorted(search_owners),
            'search_owner_evaluations': {owner: sum(sweep.get('owners', {}).get(owner, {}).get('evaluations', 0)
                for sweep in search.get('search_sweeps', [])) for owner in sorted(search_owners)},
            'final_gap_complete_owner_count': sum(v.get('complete') is True and v.get('gap') is not None
                                                  for v in final_owners.values()),
            'final_gap_owner_count': len(final_owners),
            'final_gap_owner_status_counts': counts(v.get('status') for v in final_owners.values()),
            'final_audit_evaluations': sum(v.get('evaluations', 0) for v in final_owners.values()),
            'maximum_finite_candidate_gap': response['maximum_finite_candidate_gap'],
            'final_check_complete': response['final_check_complete'],
            'finite_neighborhood_certified': response['finite_neighborhood_certified'],
            'whole_wall_sec': clock['wall_sec'], 'whole_unlimited_time': clock.get('unlimited_time'),
            'selected_candidate_wall_sec': selected['elapsed_sec'],
            'selected_final_check_reserve': selected.get('final_check_reserve'),
            'selected_response_scheduling': selected.get('response_scheduling'),
            'inclusive_clock_scopes': clock['inclusive_scopes'],
            'progress_candidate_starts': starts, 'progress_stage_counts': stage_counts,
            'csv_row_count': row_count, 'csv_changes_from_previous': changes,
            'vsl_speeds_kmh': sorted(set(commands['vsl'].values())),
            'meter_greens_sec': sorted({v[0] for v in commands['meter'].values()}),
            'written_command_binding_passed': written['written_command_binding_passed'],
            'native_execution_status': written['native_execution_status'],
            'reported_source_changes': joint['source_changes'],
            'source_joint': (folder / (stem + '.joint.json')).relative_to(ROOT).as_posix(),
        }
        decisions.append(entry)
    selected = [d for d in decisions]
    restoration = [c for c in candidate_rows if c['status'] == 'restoration_budget_stop']
    summary = {
        'completed_decisions': len(decisions), 'first_sec': args.start, 'last_sec': args.end,
        'comparable_held_to_selected_omega_pairs': 0,
        'predicted_omega_gain_aggregate': None,
        'warning': '450-second forecasts overlap; even available per-decision gains must not be summed as realized TTT savings',
        'selection_status_counts': counts(d['selection_status'] for d in decisions),
        'selected_np_counts': counts(d['selected_np_cap_veh'] for d in decisions),
        'selected_meter_bank_counts': counts(d['selected_meter_bank_index'] for d in decisions),
        'ranking_candidate_count': counts(len(d['ranking_indices']) for d in decisions),
        'attempted_candidate_status_counts': counts(c['status'] for c in candidate_rows),
        'restoration_stop_kind_counts': counts(c['restoration_status'] for c in restoration),
        'restoration_candidate_feasibility_known_counts': counts(c['candidate_feasibility_known'] for c in restoration),
        'restoration_initializer_np_satisfied_counts': counts(c['initializer_quantity']['np']['satisfied'] for c in restoration),
        'restoration_initializer_nuf_satisfied_counts': counts(c['initializer_quantity']['nuf']['satisfied'] for c in restoration),
        'restoration_initializer_np_actual_veh': stats([c['initializer_quantity']['np']['actual'] for c in restoration]),
        'domain_count': stats([d['domain_count'] for d in decisions]),
        'unknown_candidates': stats([d['unknown_candidates'] for d in decisions]),
        'accepted_update_count': counts(len(d['accepted_owner_updates']) for d in decisions),
        'accepted_owner_counts': counts(u['owner'] for d in decisions for u in d['accepted_owner_updates']),
        'accepted_own_payoff_gain_range': stats([u['gap'] for d in decisions for u in d['accepted_owner_updates']]),
        'accepted_own_payoff_scope': OWN_PAYOFF_SCOPE,
        'search_owner_coverage': counts(len(d['search_owners_visited']) for d in decisions),
        'final_gap_completed_owner_count': counts(d['final_gap_complete_owner_count'] for d in decisions),
        'final_check_complete_counts': counts(d['final_check_complete'] for d in decisions),
        'finite_neighborhood_certified_counts': counts(d['finite_neighborhood_certified'] for d in decisions),
        'leader_optimum_certified_counts': counts(d['leader_optimum_certified'] for d in decisions),
        'search_status_counts': counts(d['search_status'] for d in decisions),
        'whole_wall_sec': stats([d['whole_wall_sec'] for d in decisions]),
        'selected_candidate_wall_sec': stats([d['selected_candidate_wall_sec'] for d in decisions]),
        'csv_change_decisions': {k: sum(bool(d['csv_changes_from_previous'][k]) for d in decisions)
                                 for k in ('vsl', 'meter', 'green', 'offset')},
        'csv_change_comparable_decisions': {k: sum(d['csv_changes_from_previous'][k] is not None for d in decisions)
                                            for k in ('vsl', 'meter', 'green', 'offset')},
        'all_vsl_speeds_kmh': sorted({v for d in decisions for v in d['vsl_speeds_kmh']}),
        'all_meter_greens_sec': sorted({v for d in decisions for v in d['meter_greens_sec']}),
        'binding_pass_counts': counts(d['written_command_binding_passed'] for d in decisions),
        'native_execution_status_counts': counts(d['native_execution_status'] for d in decisions),
    }
    report = {'schema': 'v3-completed-decision-performance-audit/v1', 'run': args.run,
              'scope': 'Stored decision evidence only; no FZP, no model endpoint, no native execution, no causal attribution',
              'summary': summary, 'field_evidence': FIELDS, 'decisions': decisions,
              'key_decision_seconds': [sec for sec in KEY_TIMES if args.start <= sec <= args.end],
              'source_files': pins,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    flat = []
    for d in decisions:
        flat.append({k: d[k] for k in ('sim_sec', 'horizon_end_sec', 'beta_seconds',
            'held_predicted_omega_ttt_veh_h', 'selected_predicted_omega_ttt_veh_h',
            'predicted_omega_ttt_gain_veh_h', 'predicted_gain_status', 'domain_count',
            'selected_np_cap_veh', 'selected_nuf_target_veh_h', 'selected_meter_bank_index',
            'unknown_candidates', 'selection_status', 'selection_stop_reason', 'search_status',
            'final_gap_complete_owner_count', 'final_gap_owner_count', 'final_audit_evaluations',
            'maximum_finite_candidate_gap', 'whole_wall_sec', 'selected_candidate_wall_sec')})
        flat[-1].update({'accepted_owner': '|'.join(u['owner'] for u in d['accepted_owner_updates']),
                        'accepted_own_payoff_gaps_not_omega': '|'.join(str(u['gap']) for u in d['accepted_owner_updates']),
                        'attempted_indices': '|'.join(map(str, d['attempted_indices'])),
                        'ranking_candidate_count': len(d['ranking_indices']),
                        'held_np_actual_veh': d['held_quantity']['np']['actual'],
                        'selected_np_actual_veh': d['selected_quantity']['np']['actual'],
                        'selected_nuf_residual_veh_h': d['selected_quantity']['nuf']['residual'],
                        'changed_green_controllers': '|'.join(d['csv_changes_from_previous']['green'] or []),
                        'changed_offset_controllers': '|'.join(d['csv_changes_from_previous']['offset'] or [])})
    text = ['# V3 완료 53개 결정 기록 감사', '',
            f"대상은 `{args.run}`의 {args.start}–{args.end}초 완료 결정 {len(decisions)}개다. 다른 런과 seed를 섞지 않았다.", '',
            '선택된 명령의 450초 예측 Ω TTT는 저장돼 있다. 같은 상태에서 직전 명령을 유지했을 때의 Ω TTT는 보존된 hold validation·progress·action에 없어 전후 이득은 모든 행에서 null이다. 기록된 owner `from_cost/to_cost/gap`은 고정 가격을 포함한 개별 payoff이며 Ω TTT 차이로 사용하지 않았다. 450초 예측창은 겹치므로 합계도 실제 TTT 절감량이 아니다.', '',
            f"- 매 결정의 ranking 후보 수: {summary['ranking_candidate_count']}; 선택 NP: {summary['selected_np_counts']}; 선택 meter bank: {summary['selected_meter_bank_counts']}.",
            f"- 시도 후보 상태: {summary['attempted_candidate_status_counts']}. 복원 중단 사유: {summary['restoration_stop_kind_counts']}. 후보 가능성 unknown을 불가능 증명으로 바꾸지 않았다.",
            f"- 선택 응답의 owner 방문 수: {summary['search_owner_coverage']}; 최종 gap 완료 owner 수: {summary['final_gap_completed_owner_count']}. 최적성 인증은 없다.",
            f"- 실제 작성 CSV의 VSL 값: {summary['all_vsl_speeds_kmh']} km/h; 미터 녹색: {summary['all_meter_greens_sec']}초. 900초 이후 52회 비교에서 green {summary['csv_change_decisions']['green']}회, offset {summary['csv_change_decisions']['offset']}회 변경됐다.",
            f"- 전체 계산 시간 min/median/max: {summary['whole_wall_sec']}. 명령 파일 결합 기록은 {summary['binding_pass_counts']}; native 상태는 {summary['native_execution_status_counts']}로 완료 native 인증이 아니다.", '',
            '| 결정초 | 선택 Ω TTT [veh·h] | 유지 Ω TTT / 이득 | 채택 owner | 개별 payoff 감소 (Ω 아님) | NP 실제/상한 | 최종 gap | 전체 계산초 |',
            '|---:|---:|---|---|---:|---:|---|---:|']
    for d in decisions:
        if d['sim_sec'] not in KEY_TIMES:
            continue
        owner = ', '.join(u['owner'] for u in d['accepted_owner_updates'])
        gains = ', '.join(f"{u['gap']:.9f}" for u in d['accepted_owner_updates'])
        text.append(f"| {d['sim_sec']} | {d['selected_predicted_omega_ttt_veh_h']:.9f} | missing / null | {owner} | {gains} | {d['selected_quantity']['np']['actual']:.6f}/{d['selected_np_cap_veh']:.0f} | {d['final_gap_complete_owner_count']}/19, null | {d['whole_wall_sec']:.3f} |")
    text += ['', '정확한 필드 경로는 JSON의 `field_evidence`, 시각별 값·후보 인덱스·복원 제약은 `decisions`, 원본 SHA는 `source_files`에 있다. CSV는 53개 결정의 작은 표다.', '',
             '이 기록이 직접 입증하는 것은 좁은 관측 후보 선택과 미완료 최종 gap이다. 전체 실제 TTT의 0.57% 개선이 작은 원인을 이 자료만으로 특정하거나, 예측 Ω TTT도 좋아졌다고 단정하지 않는다.', '',
             '재현: 저장소 루트에서 `python -B diagnostics/performance_diagnosis_20260913/audit_decisions.py --output-prefix diagnostics/performance_diagnosis_20260913/recheck/decision_audit`. 원본 런의 위 작은 JSON/CSV/JSONL 파일이 필요하며 기존 결과는 덮어쓰지 않는다.', '']
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    with paths[0].open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')
    with paths[1].open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader(); writer.writerows(flat)
    with paths[2].open('x', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(text))
    print(json.dumps({'outputs': [str(p) for p in paths], 'summary': summary}, ensure_ascii=False))


if __name__ == '__main__':
    main()
