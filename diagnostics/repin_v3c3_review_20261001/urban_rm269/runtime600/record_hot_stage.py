import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def update(path,fields):
    data=json.loads(path.read_bytes());data.update(fields)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
update(HERE/'plan.json',dict(status='running_stock_geometry_validation',
    upgrade_diagnostic=dict(path='upgrade_replay',status='complete_sparse_record_count_only',
        scalar_events=197481,ad_events=197478,max_route_clock_amount_error=3.197442310920451e-14,
        quantitative_summary_differences=0,fix_retained_data_check='PASS',regression_tests=48,subtests=24),
    stock_geometry=dict(production_module='evaluation/controllers/sdmpc_stock_geometry.py',default=False,
        config='hot_config.json',option='adapter.sdmpc_stock_geometry_hotpath',
        parameter_check='PASS',tests=80,validation='hot_validation',
        maximum_predictions=2,maximum_ad_predictions=1,full_selections=0,
        source_freeze='hot_validation/prepared.json',comparison_script='compare_hot_pair.py'),
    next_after_selection='Wait for hot_validation owners to close; compare saved scalar/AD summaries,route-clock amounts,and all owner/resource/central-state Jacobians once. If equivalent, prepare one new unique complete lazy+hot-path decision with the same candidates/horizon/iteration limits and compare against existing cacheON. Do not rerun old failed lazy_full. Target600s is still unmet.'))
update(HERE.parent/'plan.json',dict(runtime600_latest=dict(status='running_stock_geometry_validation',
    plan=str(HERE/'plan.json'),target_seconds=600,goal_complete=False,
    verified_complete_baseline_seconds=2006.4634451,
    full_failed_attempt_retained=True,record_comparison_bug_fixed=True,
    new_native_runs=0,additional_coefficient_fits=0)))
with (HERE.parent/'README.md').open('a',encoding='utf8') as file:
    file.write('''

### Runtime600: 기록 개수 원인 확인·계산 가속 검증 중 (2026-10-09)

- 실패한 정확한 후보의 scalar/AD 비교에서는 197481 대 197478개의 기록 수만 달랐다. 시간·경로별 차량/유출/진입량 차이는 최대3.197e-14이며 다른 정량 요약은 일치했다. `runtime600/upgrade_replay/comparison.json`과 `fix_validation.json`에 보존했다. 기록 개수만 별도 진단으로 남기고 TTT·모든 경로 유량·수용량·제약 검사는 유지한다.48시험/24하위시험 통과.
- 기본OFF 옵션 `adapter.sdmpc_stock_geometry_hotpath`을 추가했다.128항 이상의 긴AD 재고 합산은 같은 덧셈 순서와 미분 기록으로 계산하고, 고정 수용 기하는 물리 상태 밖에서 재사용한다. 공유차로 차량보존 검사는 모두 수행하되 검사에만 쓰이는 미분 기록은 만들지 않는다. 차로·경로·미소cohort를 삭제하거나 합치지 않는다.
- 원형과 생산 코드80시험 및 설정 검사 통과. `runtime600/hot_validation`에서 동일 후보의 scalar/AD 각1회를 보존하며 모든 주체 비용·NP/NUF·중앙 물리상태 Jacobian을 비교 중이다. 기존native·450초 지평·후보수·계수 유지.10분 달성은 미확인이며 목표는 미완료다.
''')
print('Hot-path validation and unfinished600s target recorded')
