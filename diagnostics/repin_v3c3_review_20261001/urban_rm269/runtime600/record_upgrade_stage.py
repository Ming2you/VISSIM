"""Persist this bounded runtime diagnosis; no controller or native mutation."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def update(path,fields):
    data=json.loads(path.read_bytes())
    data.update(fields)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

update(HERE/'plan.json',dict(status='running_exact_trial_upgrade_diagnostic',
    lazy_failed_attempt=dict(path='lazy_full',external_process_wall_sec=531.7332968,
        completed_full_decision=False,error='Scalar/AD trial response changed: response/control_area/event_count',
        owners_closed=True,automatic_retry=False),
    upgrade_diagnostic=dict(path='upgrade_replay',maximum_predictions=2,full_selections=0,
        same_first_pfo_proposal_tokens_verified=True,existing_reference_ad_reused=True,
        reason='Determine whether record-count difference is tiny sparse events or physical response mismatch; retain full route/time amount evidence.'),
    candidate_microbench=dict(stock_tests_passed=31,geometry_tests_passed=7,
        stock_results='stock_microbenchmark.json',installed_in_production=False,
        note='Small sums slowed slightly; long sums1.26-1.84x faster. No full-speed claim.'),
    next_after_selection='Inspect retained exact scalar/AD trial responses and transfer groups before changing equality checks or starting another full selection. Then test bounded stock/geometry hot-path optimizations. Target600s remains unmet.'))
path=HERE.parent/'plan.json'
data=json.loads(path.read_bytes())
data['runtime600_latest']=dict(status='running_exact_trial_upgrade_diagnostic',
    plan=str(HERE/'plan.json'),full_benchmark_failed_preserved=True,
    error='Sparse event-count response comparison; physical cause pending retained pair',
    goal_complete=False,target_seconds=600,verified_complete_baseline_seconds=2006.4634451,
    native_runs_started=0,additional_coefficient_fits=0)
path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
with (HERE.parent/'README.md').open('a',encoding='utf8') as file:
    file.write('''

### Runtime600: 첫 lazy 전체선택 검사 중단 (2026-10-09)

- 전체 시도는531.733초에서 `response/control_area/event_count` 비교 오류로 종료됐다. 완료시간이나10분 달성으로 해석하지 않는다. 실패 자료와 소유 종료 영수증은 `runtime600/lazy_full*`에 보존했다.
- `docs/SDMPC_CONTINUOUS_DERIVATIVES_20260921.md`에 동일 유형의 sparse transfer 기록 개수 차이와 경로·시계별 이동량 검산 이력이 있다. 이번 원인도 그렇다고 단정하지 않고, 실패한 정확한 첫 PFO 후보를 기존 reference AD에서 재구성했다(세 후보 token 일치, 추가 최적화0회).
- `runtime600/upgrade_replay`에서 scalar/AD 각각1회만 보존 비교한다. 이동 기록 개수와 경로·시계별 실제 차량/유출/진입량을 모두 보존하며, 검사 완화나 전체선택 재시도를 먼저 하지 않는다.
- 실행 중인 native 큐·동결본·계수·450초 지평·후보수는 그대로다. 독립 stock합산 후보31시험과 고정 receiving기하 후보7시험 통과. 아직생산연결하지 않았다. 작은stock합산은 약간 느리고, 긴합산만1.26–1.84배 빨랐으므로 전체10분 성능의 증거가 아니다.
''')
print('Runtime diagnosis recorded;600s target incomplete')
