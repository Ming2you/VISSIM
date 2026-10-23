"""Preserve the assessed finite experiment and correct its interpretation."""
import datetime
import hashlib
import json
from pathlib import Path

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'refine_boundary_fit'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not (O / 'decision.json').exists()
    assessment = read(O / 'assessment.json')
    owner_path = A / 'refine_boundary_owner.json'
    owner = read(owner_path)
    assert owner['pid'] == 15112 and owner['exec_session'] == 13530
    assert owner['status'] == 'running_bounded_boundary_identification'
    assert sha(A / 'run_refine_boundary_fit.py') == owner['source_sha256']
    assert assessment['new_forecasts'] == 16
    assert not assessment['next_independent_comparison_warranted']
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    closure = dict(pid=15112, creation_utc=owner['creation_utc'], exec_session=13530,
        exec_exit_code=0, pid_present_after_exit=False,
        evidence='Existing exec session13530 returned exit0; subsequent Get-Process15112 found no process.',
        recorded_utc=stamp, source_sha256=owner['source_sha256'], process_termination_performed=False)
    save(O / 'owner_closure.json', closure)
    nxt = (
        'Reuse all completed forecasts. The boundary update improves baseline loss but worsens the VSL contrast; '
        'do not deploy it or repeat independent runs for this candidate. Before another parameter update, '
        'use saved matched trajectories, resource allocations and native observations to separate baseline '
        'state errors from the downstream outflow response mechanism and identify a nonduplicate hypothesis. '
        'Do not infer that calibrated spatial refinement is impossible or expand bounds merely to fit the sign. '
        'No new native, full optimization, grid, production edit or push. Goal ACTIVE/incomplete; automation PAUSED.'
    )
    correction = (
        'The quoted -28.9 to -29.4 vehicles came from the one-update five-parameter joint fit, '
        'not the initial fixed-parameter spatial split. That fit was not converged and lacked congested '
        'training coverage. The candidate was not adopted; calibrated spatial refinement was not ruled out.'
    )
    record = dict(status='boundary_update_improves_baseline_but_worsens_vsl_response_not_adopted',
        updated_utc=stamp, app_goal_status='active', automation_status='PAUSED', goal_complete=False,
        current_goal_turn_classification='progress:16 finite boundary-identification forecasts completed and assessed; annotation-stage attribution corrected',
        candidate_adopted=False, spatial_model_class_rejected=False,
        nonlinear_fit_converged=False, new_forecasts=16, reused_forecasts=3, updates=1,
        independent_new_forecasts=0, new_native=0, remaining_native_budget=0,
        production_edits=0, training_loss_reduction=assessment['training_loss_reduction'],
        development_response=assessment['development_response'],
        annotation_correction=correction, next=nxt)
    paths = [O / 'completion.json', O / 'selection.json', O / 'assessment.json', O / 'owner_closure.json',
             A / 'refine15_residual_audit.json', A / 'refine15_joint_fit/README.md']
    record['evidence'] = {str(p): sha(p) for p in paths}
    save(O / 'decision.json', record)
    owner.update(status='completed_exit0_assessed', closed_utc=stamp,
        completion=str(O / 'completion.json'), assessment=str(O / 'assessment.json'),
        closure=str(O / 'owner_closure.json'), next=nxt)
    save(owner_path, owner)
    for path in (H / 'plan.json', H / 'summary.json'):
        doc = read(path)
        doc.update(updated_utc=stamp, boundary_identification_20261019=record, next=nxt)
        save(path, doc)
    with (H / 'README.md').open('a', encoding='utf8') as stream:
        stream.write('\n\n## 2026-10-19 앞뒤 구간 반응계수의 제한적 보정 완료\n\n'
            '기존15번 분할 계수는 고정하고14·18번 구간의 반응시간/밀도차 반응4개 배율을 제한적으로 '
            '한 번 갱신했다.16예측 완료/3기준선 재사용/정상 소유종료이며 새로운 native·생산변경은0이다. '
            '학습 오차는7.28% 줄었으나450초 두 구역90 통과량 변화는−31.49→−34.19대(실제+31), '
            '재고 변화는+29.03→+31.52대(실제−30), ΩTTT 변화는+1.1051→+1.1397대·시간'
            '(실제−0.04583)로 바뀌었다. 이 후보는 미채택이며 추가 독립 예측을 하지 않았다. '
            '제한된 갱신의 결과로 공간 분할 모델 전체나 충분한 보정의 가능성을 기각하지 않는다.\n\n'
            '사용자가 인용한−28.9→−29.4대는 첫5계수 공동 보정 이후 수치다. 최초의 계수 고정 '
            '분할 시험과 혼동해 설명한 부분을 정정한다. 당시 보정은 한 번의 비수렴 갱신이고 '
            '정체 표본이 부족했으므로 충분한 보정이 끝났다는 근거가 없었다. '
            '최신 근거/후속 범위는 outflow_followup_20261019/refine_boundary_fit/decision.json. '
            '앱 목표 ACTIVE·미완료, 유한 자동확인 PAUSED.\n')
    print(json.dumps({k: v for k, v in record.items() if k not in ('evidence', 'development_response')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
