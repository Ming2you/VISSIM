"""Record completed finite calibration and evaluation; never launch a model."""
import datetime, hashlib, json
from pathlib import Path

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'refine15_regime_fit_v3'
def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')

def main():
    assert not (O/'decision.json').exists()
    fit = read(O/'selection.json')
    done = read(O/'completion.json')
    closure = read(A/'refine15_independent_closure.json')
    assert done['forecasts'] == 38
    assert closure['status'] == 'all_offline_jobs_completed_exit0'
    assert all(x['completion_summary_exists'] and x['exec_exit_code'] == 0 and not x['exact_owner_alive'] for x in closure['owners'])
    evaluation = read(A/'refine15_independent_assessment.json')
    summaries = [read(A/f'refine15_independent_s{s}/summary.json') for s in (67, 71)]
    assert sum(x['new_predictions'] for x in summaries) == 8
    sources = [O/'completion.json', O/'selection.json', O/'assessment.json', O/'README.md',
               A/'refine15_independent_assessment.json', A/'refine15_independent_closure.json',
               *[A/f'refine15_independent_s{s}/summary.json' for s in (67, 71)]]
    evidence = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    next_step = ('Reuse completed 38 calibration/development forecasts and 8 frozen independent forecasts. '
                 'Before any further fit, use saved per-cell trajectories and finite-difference probes to localize '
                 'baseline versus VSL-contrast residuals and coefficient sensitivity; assess whether cell15-only '
                 'parameters can address the error or neighboring/averaged speed dynamics dominate. '
                 'Do not widen bounds or fit evaluation signs blindly. No new native, full optimization, grid, '
                 'repetition of completed forecasts, production edit or push. Spatial calibration remains unresolved; '
                 'the nonconverged bounded candidate is not adopted. Goal ACTIVE/incomplete; automation PAUSED.')
    decision = dict(status='bounded_regime_fit_failed_independent_transfer_not_adopted',
        updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        current_goal_turn_classification='progress:completed 38 finite forecasts, two bounded updates and eight frozen independent predictions; nonuniform transfer measured',
        app_goal_status='active', automation_status='PAUSED', goal_complete=False, candidate_adopted=False,
        spatial_model_class_rejected=False, nonlinear_fit_converged=False,
        new_forecasts=46, training_development_forecasts=38, independent_forecasts=8, reused_forecasts=2,
        updates=2, new_native=0, remaining_native_budget=0, new_optimizer_runs=0, new_fzp_scans=0,
        production_edits=0, independent_from_fit=True, blind_validation_claimed=False,
        training_loss_reduction=1-fit['fitted']['data_loss']/fit['baseline']['data_loss'],
        parameter_tau_at_relative_lower_bound=True,
        max_route_balance=max(done['max_route_balance'],*[x['max_route_balance'] for x in summaries]),
        max_vsl_balance=max(done['max_vsl_balance'],*[x['max_vsl_balance'] for x in summaries]),
        independent_450=[x for x in evaluation['rows'] if x['horizon']==450], next=next_step, evidence=evidence)
    save(O/'decision.json', decision)
    for filename in ('plan.json', 'summary.json'):
        path = H/filename
        doc = read(path)
        doc['refinement_regime_fit_20261019'] = decision
        doc['next'] = next_step
        save(path, doc)
    path = H/'README.md'
    text = path.read_text(encoding='utf8')
    heading = '## 2026-10-19 정체·회복 포함 보정 및 독립 비교 완료'
    assert heading not in text
    path.write_text(text+'\n\n'+heading+'\n\n'
        '5개 계수의 제한된 갱신 두 번, 보정·개발38예측과 독립seed67/71의8예측을 완료했다. '
        '학습 오차는2.57% 줄었지만 독립 반응의 개선은 일관되지 않았다. seed67 통과량 변화는7.46→7.94대(실제+33), '
        'seed71은−11.60→−4.34대(실제−24)로 바뀌었다. 반응시간은 상대변화 하한에 닿았고 비선형 수렴을 확인하지 않았다. '
        '현재 계수는 미채택이며 보정된 공간 모델 자체의 기각이 아니다. '
        '[상세 보고서](outflow_followup_20261019/refine15_regime_fit_v3/README.md)와 같은 폴더decision.json이 최신 인계다. '
        '다음은 저장자료의 구간별 오차·민감도 분리이며, 완료 예측을 반복하지 않는다. 새native0·생산변경0·목표ACTIVE미완료.\n', encoding='utf8')
    print(json.dumps({k:decision[k] for k in ('status','new_forecasts','new_native','training_loss_reduction','max_route_balance','max_vsl_balance','goal_complete')}, indent=2))

if __name__ == '__main__':
    main()
