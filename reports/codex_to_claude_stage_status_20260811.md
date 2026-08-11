# Codex -> Claude 구현 단계별 재검토 전달문

작성일: 2026-08-11  
대상 브랜치: `codex/plant-fidelity-v2-1`  
기준 HEAD: `7d5439584869468391b82b3dbf496ee4aea5a00e`

## 총평

Codex와 5개 서브에이전트가 `reports/codex_review_request_20260811.md`를 기준으로 읽기 전용 재검토를 했다. 결론부터 말하면, Claude가 잡은 큰 방향은 대체로 타당하다. 특히 **수요 계약과 boundary topology가 VISSIM 망과 어긋나 있다**는 진단은 현재 plant 충실도에서 가장 큰 P0로 봐야 한다.

다만 일부 PASS 주장은 "정적 계약/단위 테스트 기준 PASS"와 "live VISSIM evidence 기준 PASS"가 섞여 있다. 다음 작업에서는 `NOT_EVALUATED`를 PASS처럼 다루지 말고, live run 산출물이 필요한 항목은 명시적으로 남겨야 한다.

가장 중요한 원칙은 하나다.

> 이 plant는 MPC가 VISSIM run에 대해 action을 고르기 위한 rollout plant이므로, 수요, 신호, boundary, 상태 투영은 "모델 내부에서 그럴듯함"이 아니라 "VISSIM에서 실제로 쓰이는 경로"와 맞아야 한다.

## 우선순위 요약

1. **P0: demand/topology contract 확정**
   - `state.demand`가 지점 평균인지 총량인지 문서화하고 코드로 강제.
   - VISSIM 실제 외부 vehicle input 22개, dummy/internal input, model boundary gate를 기하적으로 대조.
   - 사용자 방침이 `plant == VISSIM 망`이므로 단순 `117/32` scale 보정보다는 boundary 격자 재정렬을 우선 검토.

2. **P0: short live evidence run**
   - `urban_demand_arrivals_veh`, freeway arrivals, `boundary_out` 비유입 여부, `signal_readback.csv`, runtime samples를 한 번에 확인.

3. **P0/P1: N4 signal readiness**
   - 282개 `synthetic_boundary_leg` 정책 확정.
   - 신호 readback/event timing, budget contract, offset 좌표계를 닫기.

4. **P1: N5/N6/N8/N9 순차 진행**
   - N5 parent runs는 topology/demand 고정 뒤 재봉인.
   - N6 calibration은 N5 sample이 기준을 만족한 뒤 진행.
   - N8 exact-FD/SPSA 하네스 작성 후 marginal price 비교.
   - N9는 H=1 development 216셀부터 열고, holdout seed 47은 plant freeze 전까지 열지 않기.

## 단계별 상태

### N0. 토폴로지 정합과 고정

**잘된 점**

- `topology_approval_v2_1.json`은 `status=PASS`, `reasons=[]`로 재생성되어 있다.
- runtime source, preflight, topology approval의 승인 사슬 자체는 동작한다.

**보완해야 할 점**

- N0의 PASS는 VISSIM vehicle input과 model boundary gate의 1:1 대응을 검사하지 않는다.
- 현재 `core15n41` config에는 `boundary_in_links=117`, `boundary_out_links=119`가 있고, 이 중 상당수가 VISSIM 실제 외부 유입과 직접 대응하지 않는다.
- `generate_real_world_distributed_players.py`는 남는 방위마다 synthetic boundary를 만들며, 이것이 N4/N5 문제로 이어진다.

**앞으로 작업 방향**

- N0 승인 조건에 "VISSIM external input -> model boundary gate" coverage gate를 추가한다.
- 실제 입구 22개, dummy/internal input, model boundary gate를 분리한 manifest를 만들고 승인 사슬에 포함한다.
- boundary 격자를 재정렬하면 `canonical_topology_v3`, `physical_stock_topology_v2_1`, `topology_approval_v2_1`, N5/N9 봉인을 전부 재생성한다.

### N1 / N1a / N1b. 차량단위 초기상태 투영

**잘된 점**

- validator는 `assigned_count`, `global_residual` 등 상태 투영 계약 필드를 갖고 있다.
- N1b를 runtime 계약 이후로 미룬 판단은 순서상 맞다.

**보완해야 할 점**

- 현재 사본의 감사 summary에서는 state observation/projection diagnostics가 `NOT_EVALUATED`다.
- `61/61` N1a 재현 산출물이 현재 evidence chain에 충분히 묶여 있지 않다.

**앞으로 작업 방향**

- topology/demand 수정 후 N1a projection 산출물을 재생성한다.
- 61개 snapshot의 assigned/unrepresented/clipping/residual을 evidence manifest에 연결한다.
- N8-4 runtime gate가 닫힌 뒤 N1b MPC capture 61회를 실행한다.

### N1.5. vendor 스냅샷 재앵커

**잘된 점**

- vendor anchor는 `e4bf4d0` 스냅샷을 가리키며, runtime/preflight/baseline 쪽 앵커 사실은 대체로 일치한다.
- production 경로의 `run_coupled_interval` 우회는 제거된 것으로 보인다.

**보완해야 할 점**

- "11개 상수가 모두 `e4bf4d0` 문자열"이라는 표현은 약간 부정확하다. 정확히는 11개 앵커 사실이 같은 `UPSTREAM_TREE.json` 스냅샷을 검증한다.
- `harness/g6/g6_core.py`에는 직접 `run_coupled_interval` 호출이 1곳 남아 있다.

**앞으로 작업 방향**

- 문서 표현을 "11 anchor facts"로 정정한다.
- `g6_core.py` 직접 호출은 endpoint 경유로 바꾸되, 먼저 동작 보존 비교를 한다.

### N2. substep 질량 장부

**잘된 점**

- `src.tests.test_global_mass_conservation` 스모크는 통과했다.
- 되돌림 증명 테스트도 존재한다.

**보완해야 할 점**

- 현재 cheap regression은 109개 시나리오가 아니라 대표 3개 시나리오 중심이다.
- `109 x 24`, 최대 residual `6.7e-12` 숫자는 현재 산출물만으로 봉인되어 있지 않다.
- live projection/mass gate는 아직 `NOT_EVALUATED`다.

**앞으로 작업 방향**

- 109개 전체 시나리오 x 24 step 질량 보존 산출물을 재생성하거나, 그 숫자를 주장하지 않도록 낮춘다.
- live run의 `projection_diagnostics`에서 mass conservation gate를 닫는다.
- off-ramp rejection이 reachable해졌을 때 질량 증발이 없는지 별도 회귀를 둔다.

### N3. 관측 확장

**잘된 점**

- N3-1/N3-2의 관측 확장 방향은 타당하다.
- 출구/램프/queue-tail 계열 관측을 별도 gate로 분리한 것은 좋다.

**보완해야 할 점**

- N3-3 램프 커넥터 상태는 이번 재검토에서 완전히 닫히지 않았다.
- 관측 확장이 N5/N9 live 산출물에 실제로 붙었는지는 아직 확인 필요하다.

**앞으로 작업 방향**

- short live run에서 link speed, queue-tail, ramp connector, exit coverage가 state JSON과 audit summary에 실제로 들어오는지 확인한다.
- N5/N9 실행 전 observation contract를 fail-closed로 둔다.

### N4. N현시 신호

**잘된 점**

- `.sig` 선택을 파일명 suffix가 아니라 INPX `signalController/@supplyFile2` 기준으로 바꾼 것은 맞다.
- 현재 산출물은 controlled 15 SC 기준 `SG=136`, conflicting/name-rule pairs `222`, native cycle `140/150/160/170`으로 확인된다.
- controlled run에서 native `.sig` cycle이 직접 재생되지 않는다는 판단은 타당하다. VBS가 모든 SG에 `ContrByCOM=True`를 걸고 합성 주기를 쓴다.
- offset promotion lock은 보수적으로 잠겨 있어 현재는 안전하다.

**보완해야 할 점**

- 282개 movement가 `synthetic_boundary_leg`로 미해결이며, 이 상태에서 `scalar-cycle fallback 0` PASS는 그대로 주장하기 어렵다.
- signal timing/readback/event timing은 live evidence가 없으면 PASS가 아니다.
- `lost_time=10`으로 모델-플랜트 주기를 맞췄지만 `green_min=20`, `green_max=92`, `effective_green_total=110`이면 `green_max=92`는 도달 불가능한 죽은 상한이다.
- N4-6의 0.99s quantization 숫자는 추가 산출물로 봉인해야 한다. 0.5s gate와 1s write/readback grid의 구조적 충돌은 맞다.
- offset 승격 시 모델은 p1-first, VISSIM plant는 major-first이며, 15개 중 14개가 `major_maps_to=p2`다.

**앞으로 작업 방향**

- 282개 synthetic boundary를 해소할지, 아니면 PASS 조건을 SG-mapped movement로 좁힐지 먼저 결정한다.
- action budget contract를 `cycle_length`, `lost_time`, `effective_green_total`, `green_min`, `green_max` 하나의 계약으로 정리한다.
- `signal_readback.csv` 기반 D-core를 돌려 event timing/readback을 닫는다.
- offset은 D-core, N8-4 runtime, N9 offset effect/ranking gate가 모두 PASS한 뒤에만 열고, `major_maps_to`별 p1/p2 부호 테스트를 먼저 실행한다.

### N5. 개발 데이터와 잡음 바닥

**잘된 점**

- N5를 실행하기 전에 demand/topology 결함을 찾은 것은 매우 중요하다.
- N9 holdout을 열기 전 development로 plant를 고치는 구조는 타당하다.

**보완해야 할 점**

- VBS는 urban/freeway vehicle input volume의 평균을 state demand로 쓴다.
- adapter는 그 scalar를 `boundary_in_links + boundary_out_links`에 복제한다. 실제 urban arrival는 주로 `boundary_in_links`가 먹으므로, `117/32 = 3.66x` 지시값 과대 주장은 구조적으로 맞다.
- 단, 하류 용량/게이팅 이후 accepted arrival가 실제로 3.66배인지는 live run의 `urban_demand_arrivals_veh` 없이는 단정하면 안 된다.
- "실제 입구 22개 중 only 5 aligned"는 독립 기하 산출물로 한 번 더 봉인해야 한다.
- 현재 sample 177이면 N6의 sample >= 200, saturated lane-group >= 30, CI half-width <= 10% 조건에 부족할 가능성이 크다.

**앞으로 작업 방향**

- `state.demand` contract를 먼저 확정한다: 지점 평균, 총량, role별 vector 중 무엇인지 결정.
- VISSIM vehicle input CSV와 model boundary를 좌표/방위/링크 연결로 대조해 aligned count를 봉인한다.
- topology/demand를 고친 뒤 short live run으로 commanded demand와 accepted arrivals를 비교한다.
- 그 다음에 N5 parent runs를 재봉인한다.

### N6. 캘리브레이션

**잘된 점**

- validator의 기준은 명확하다: sample 수, saturated lane-group, CI 반폭.

**보완해야 할 점**

- 현 자료 177 sample, CI 없음 상태로는 PASS를 주장하기 어렵다.
- N5가 demand/topology 결함을 가진 채 생성되면 N6 calibration 자체가 오염된다.

**앞으로 작업 방향**

- N5를 고친 plant 기준으로 다시 생성한다.
- N6 validator가 요구하는 표본 수와 lane-group coverage를 사전 계산한 뒤 실행한다.
- calibration/validation split이 섞이지 않도록 run manifest에 명시한다.

### N7. production MPC rollout endpoint

**잘된 점**

- vendor production 경로에서 endpoint 우회는 제거된 것으로 보인다.
- `rollout_endpoint` 테스트는 통과했다.

**보완해야 할 점**

- `harness/g6/g6_core.py`의 직접 `run_coupled_interval` 호출이 남아 있다.
- 재앵커 전 vendor 우회 상태에서 나온 기존 실험 결과는 새 plant 판정 근거로 쓰면 안 된다.

**앞으로 작업 방향**

- G6 harness 직접 호출을 endpoint 경유로 바꾸는 작업을 별도 작은 변경으로 처리한다.
- 바꾸기 전에 H-step 동일성, demand-from-state 동일성, objective 동일성을 비교한다.

### N8. marginal price와 런타임

**잘된 점**

- `eps_J_vissim`과 `eps_J_endpoint`를 분리해야 한다는 인식은 맞다.
- leader candidate 결과 정렬을 `selected_indices` 순서로 맞춘 방향은 타당하다.
- `stackelberg_wu_metered`에서 solve-level worker를 끄는 이유가 성능이 아니라 follower injection 보존이라는 진단은 맞다.

**보완해야 할 점**

- `eps_J_endpoint` 측정 하네스와 산출물이 아직 없다.
- exact-FD/SPSA decision equivalence는 아직 PASS 단계가 아니다.
- `incumbent_obj`는 thread/process 경로에서 seed 이후 payload에 고정되어, early termination이 worker 수에 따라 목적값/평가 깊이를 바꿀 수 있다.
- runtime 9.94/11.2와 11.0/12.9 숫자가 문서 사이에서 갈린다. 정본 run manifest와 log hash로 하나를 봉인해야 한다.

**앞으로 작업 방향**

- N8-1 전용 `eps_J_endpoint` 반복평가 하네스와 schema를 먼저 만든다.
- `eps_J_vissim`을 N8 endpoint noise로 넣으면 fail-closed하도록 막는다.
- exact-FD, SPSA, 단일 lever marginal price를 같은 material coordinate에서 비교한다.
- workers 0/1/2/5, early-stop on/off fixture를 만들어 `incumbent_obj` 병렬 결정성을 검증한다.
- solve-level parallel은 startup/audit gate에서 production 금지로 못박는다.

### N9. 짝지은 VISSIM 검증

**잘된 점**

- matrix seal은 `d397fa07d1c05692...`, 2160 cells, runnable 1620, offset BLOCKED 540으로 재현된다.
- H=1 development 216셀을 먼저 여는 전략은 타당하다.
- holdout seed 47을 plant freeze 전까지 열지 않는 원칙은 맞다.

**보완해야 할 점**

- demand/topology 결함이 남은 상태에서 N9를 돌리면 action ranking을 잘못 학습할 가능성이 크다.
- cell-outside parallelism은 비교적 안전하지만, solve-inside parallelism과 혼동하면 안 된다.

**앞으로 작업 방향**

- N0/N4/N5/N8 readiness가 닫힌 뒤 H=1 development 216셀만 먼저 실행한다.
- H=1이 맞지 않으면 H=3/5/10/15로 구제하지 않는다.
- H=1 통과 후 development 전체, plant freeze 후 holdout 순서로 간다.

### N10. 감사와 승격

**잘된 점**

- gate 수 확장, `BLOCKED` 상태 추가, `NOT_EVALUATED`를 PASS로 보지 않는 방향은 맞다.
- matrix runner에 새 required gates를 넘기도록 한 방향도 타당하다.
- `assignment_ties`를 질량 기준으로 재정의하고 관측 없으면 `NOT_EVALUATED`로 둔 것은 보수적이다.

**보완해야 할 점**

- 현재 summary는 `PASS 12 / FAIL 0 / NOT_EVALUATED 16`이고 promotion도 `NOT_EVALUATED`다. promotion-ready가 아니다.
- FAIL이 NE로 바뀌면 운영자가 blocker 심각도를 과소평가할 위험이 있다.
- `signal_com_readback`, `mass_conservation`, `runtime`은 실 런 산출물로 아직 닫히지 않았다.
- off-ramp를 BFS에서 제외하는 것은 근거가 있지만, stopline ownership과 같은 의미인지는 설계상 반론 가능하다.

**앞으로 작업 방향**

- N10 summary 상단에 `NE is not pass`와 `promotion blocked`를 더 눈에 띄게 유지한다.
- 새 required gates가 산출물 없이 NE로 조용히 지나가지 않게 strict mode를 계속 유지한다.
- N5/N9 live data가 넓어지면 남은 tie 27건이 다시 평가되는지 회귀를 둔다.

## 검증 중 확인한 테스트 상태

Codex가 읽기 전용으로 일부 스모크를 실행했다.

- PASS: `scripts.tests.test_run_plant_fidelity_matrix`, `scripts.tests.test_build_experiment_matrix_v3`, `scripts.tests.test_build_parent_run_spec`
- PASS: `scripts.tests.test_verify_runtime_source`, `scripts.tests.test_build_preflight_manifest`, `scripts.tests.test_update_numsim_snapshot`
- PASS: `src.tests.test_global_mass_conservation`, `src.tests.test_parallel_determinism`, `src.tests.test_rollout_endpoint`
- 미완/환경 이슈:
  - `tests.test_native_phase_green_share`는 `outputs/canonical_topology_v3.json` 누락으로 일부 실패.
  - `tests.test_offset_promotion_lock`의 CScript 실행은 Windows settings 접근 거부로 실패.

위 실패는 이번 문서 작성 중 코드 결함으로 단정하지 않았다. 다만 live evidence와 산출물 재생성이 아직 닫히지 않았다는 신호로 봐야 한다.

## Claude에게 권장하는 다음 커밋 단위

1. `demand_contract.md` 또는 schema로 state demand 의미를 고정하고, VBS/adapter 양쪽에 같은 용어를 적용.
2. VISSIM vehicle input과 model boundary gate의 geometry alignment 산출물 추가.
3. boundary topology 재정렬 또는 282 synthetic boundary 정책 확정.
4. short live run evidence collector 작성: arrivals, signal readback, runtime, projection diagnostics를 한 manifest에 묶기.
5. 그 evidence를 기준으로 N0/N4/N5/N10 재생성.
6. 이후 N8 endpoint noise + exact-FD/SPSA 하네스.
7. 마지막으로 N9 H=1 development 실행.

