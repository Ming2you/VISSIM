import datetime, hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
plan = read(HERE/'plan.json')
results = []
for at in (2250,3300):
    path = HERE/f'state{at}/summary.json'
    data = read(path)
    assert data['status'] == 'complete' and len(data['results']) == 27
    for row in data['results']:
        assert row['physical_constraints'] and row['writer']
    cases = {row['name']:row for row in data['results']}
    keep = ['FW_E__seg13:90x1','FW_E__seg13:90x2','FW_E__seg13:90x3',
            'FW_E:adjacent:FW_E__seg10+FW_E__seg13:90x3','FW_E:all:90x3','all_roads:90x3']
    results.append(dict(at=at,predictions=27,summary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        seconds=sum(row['seconds'] for row in data['results']),
        beneficial=sum(row['delta_veh_h'] < -1e-7 for row in data['results'][1:]),
        neutral=sum(abs(row['delta_veh_h']) <= 1e-7 for row in data['results'][1:]),
        comparisons={name:cases[name]['delta_veh_h'] for name in keep}))
summary = dict(status='search_implemented_plant_response_not_calibrated', results=results,
    predictions=54,optimizer_runs=0,native_runs=0,tests_passed=18,parameters_check='PASS',
    source_installation=read(HERE/'search_installation.json'),
    limitations=[
        'Saved selected horizon plans, not the subsequently applied future commands; conditional predictions only.',
        'Exact plant stock/capacity and physical command checks passed; NP/NUF were unchanged but this probe is not a full SDMPC feasibility/selection validation.',
        '90 km/h is not assumed beneficial. No native multizone observation is available for these two states.',
        'Existing seed67/71 evidence demonstrates state-dependent recovery/stock-response errors, not a universal VSL bonus.',
        'Full selection and native deployment of the new opt-in audit remain unverified.'
    ],
    preparation_issues=[
        'Existing RM tests are pytest functions: initial unittest command found0 tests; actual pytest run passed18 tests.',
        'Parameter checker first invocation lacked required tuning argument; corrected invocation passed.'
    ])
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
plan.update(status=summary['status'],updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    completed=dict(saved_predictions=54,unit_and_regression_tests=18,parameter_check='PASS',
        aligned_cached_operating_points=15,full_optimizer_runs=0,new_native_runs=0),
    developer_source_modified=True,production_modified=False,
    search_config='E:/VISSIM_workspaces/vsl349_causal_20261011/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json',
    next_stage=dict(status='not_started',full_selection_budget=1,native_budget=1,retries=0,
        native_runtime='D:/VISSIM_runtime/20261015_vsl_multizone2250',
        native_results='D:/VISSIM_runs/20261015_vsl_multizone2250_s29',
        replay_reference='E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2',
        instructions='First qualify reuse of completed OFF2250 hold and single-zone90 causal arms. Both existing arms have identical prefix and confirmed physical DSD execution; do not rerun them. Prepare at most one new selected arm with FW_E__seg10 AND seg13 at90 in2250..2700, retaining the exact same prefix, city/RM and all other VSL commands as that old hold. Use canonical writer and run_pair.ps1 reuse_native_baseline, canonical freezer once, existing ownership/STOP/NoGlobalKill/MaxAttempts1/Startup300. Native run only if baseline proof and frozen manifest pass; preserve any failure, no retry. Source and frozen tree immutable while freezing/running. These controls differ from current saved-plan probes, so make at most3 new exact355 predictions (hold/single90/two-zone90) against the correctly qualified old OFF2250 inputs and these executed commands. Preserve optional459 offline observer distinction. After normal2700 completion AND exact owner exits, analyze one time with existing analyzer and caches at150/300/450. Native selected command is a conditional response experiment, not an autonomous policy benefit. If baseline cannot be reused, do not replace this with extra fresh runs; document the failed gate and stop new native dispatch. Separately execute at most one complete saved3300 SDMPC selection with the new opt-in audit, pinned development sources, explicit offline price initialization, receipt and no concurrent edits; verify25 candidate checks/caps/selected writer/objective/physical constraints and wall time. Do not call it converged unless evidenced.'),
    next='Read summary.json and next_stage. The54 forecasts and18 tests are complete: do not repeat. Continue the single bounded native preparation and one full selection validation; use outcomes to isolate plant response error before making any dynamics change. No fitted gain bonus, broad parameter search, future actual flow as forecast input, additional full network runs or push.')
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
lines=['# VSL 유지·다구역 반응 검증 — 2026-10-15','',
       '탐색 보완은 개발 소스에 구현했다. 동역학 보정과 새 기능의 native 채택은 아직 미완료다.',
       '', '90km/h를 2·3블록 유지하는 단일 구역과 인접/방향 전체 구역 조합을 최대25개 직접 검사한다. 각 성분이 따로 손해여도 조합은 검사한다. 기존 전체비용과 NP/NUF·액추에이터·물리 제약을 통과한 경우에만 선택한다. 기본값은 OFF이며 별도 설정에만 활성화했다.',
       '', '## 완료된 검증', '',
       '- 신규 VSL9개 + 기존 RM9개 시험 통과. 파라미터 검사 PASS.',
       '- 실제 저장2250/3300초 상태에서 각각27개, 총54개450초 예측 완료. 실제 좌표·신호 writer·RM 불변·차량보존 및 수용량 검사 통과.',
       '- 이 단계는 전체 최적화나 VISSIM 실행이 아니다. 예측 NP/NUF까지 통과한 의사결정으로 주장하지 않는다.',
       '', '|90 적용 방식|2250초 ΔΩ TTT|3300초 ΔΩ TTT|','|---|---:|---:|']
labels=['병목150초','병목300초','병목450초','동측 인접2구역450초','동측4구역450초','동서8구역450초']
for label,name in zip(labels,results[0]['comparisons']):
    lines.append(f"|{label}|{results[0]['comparisons'][name]:+.4f}|{results[1]['comparisons'][name]:+.4f}|")
lines += ['', '단위는 대·시간, 양수는 모델이 예측한 손해다. 같은 저장상태와 같은 신호/RM 계획에서 VSL만 바꿨다. 실제 VISSIM 효과는 아니다.',
          '', '## 동역학 판단과 다음 단계', '',
          '기존 인과 대조의 회복 오차는 상태에 따라 다르다. seed67의450초 병목 재고는 실제116/모델151.16대인 반면, seed71의VSL+RM300초는 실제145/모델103.62대·속도32.46/53.74km/h다. 그래서 VSL에 공통 이득계수를 붙이지 않았다. 내부 경계 실측 유량이 없는 캐시는 미확인으로 남겼다.',
          '', '완료된 OFF2250 hold·단일90 대조를 재사용할 수 있는지 검증하고, 같은 명령에서 인접2구역90의 추가 native 조건 최대1개만 준비한다. 새 탐색 경로의 전체 SDMPC 선택도 최대1회 검증한다. 세부 한도·중복 방지·실패 보존 규칙은 plan.json에 기록했다.',
          '', '기존 앱 보정 목표는 blocked·미완료라 새 목표 등록이 거절됐다. 완료로 바꾸지 않았으며 이 후속 계획과 자동화를 통해 계속 작업한다.']
(HERE/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(dict(predictions=54,results=results),indent=2))
