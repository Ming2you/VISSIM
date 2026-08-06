# 구현 작업지시서 v2.1 - VISSIM rollout plant 충실도 복구와 승격

작성 2026-08-05. 기준선 `cb3c44d170b7f818baae7af399fb65c93b6fb1e3`.

이 문서는 `PLANT_FIDELITY_AUDIT_REQUEST.md`, `reports/plant_fidelity_audit.md`, v2 계획,
Codex 검토와 세 독립 서브에이전트 검토를 통합한 실행 명세다. v2의 방향은 유지하되,
완료되지 않은 S0, 물리 stock의 정의, paired VISSIM future, SPSA parity와 runtime 계약을 다시 연다.

## 1. Plant의 목적과 시스템 경계

이 plant는 VISSIM의 개별 차량 궤적을 미시적으로 복제하기 위한 것이 아니다. 현재 VISSIM 상태와
향후 수요, 신호, 후보 lever를 받아 MPC가 실제로 집행할 첫 action을 올바르게 고를 수 있도록
60초에서 15분의 네트워크 미래를 예측하는 controller-independent surrogate다.

- **Adapter/VBS:** VISSIM 차량, 차로, 큐, 속도, 신호와 경계 상태를 plant 상태로 옮기고 선택된
  action을 VISSIM에 적용한다.
- **Rollout plant:** 동일 초기 상태에서 green, offset, VSL, ramp metering 후보가 도시부,
  freeway, ramp, exit와 spillback에 만드는 미래를 예측한다.
- **MPC/controller:** 동일 plant에 후보 action을 넣어 목적함수와 제약을 비교하고 action을 선택한다.
- **Paired-future harness:** 같은 seed, demand, prefix와 action에서 VISSIM future와 plant future를
  짝지어 plant를 승격 또는 기각한다.

합격은 궤적 일치가 아니라 다음 네 조건을 뜻한다.

1. 상태와 질량이 누락, 중복, clipping 없이 보존된다.
2. 신호와 action의 시간축 및 물리적 제약이 VISSIM과 같다.
3. 혼잡 전파와 lever 효과의 부호, 크기, action 순위가 VISSIM과 충분히 같다.
4. 실제 `decide_with_info`가 제어주기 안에 재현 가능하게 끝난다.

## 2. 전역 불변식과 판정 원칙

### 2.1 물리 불변식

- **한 차량은 한 physical stock에만 존재한다.** urban lane-group, ramp, off-ramp, freeway,
  boundary-out, 명시적 external stock 중 정확히 하나다.
- ownership, control authority, visibility, objective attribution은 stock의 별도 view다. 공유 포장면을
  player별 stock으로 복제하지 않는다.
- capacity는 sending/receiving flow를 제한한다. 초과 차량은 upstream 또는 overflow stock에 남으며
  `min(capacity, value)`로 삭제하지 않는다.
- queue, in-transit, movement composition은 같은 stock 내부의 분해다. 합계가 stock 질량과 일치해야 한다.
- objective에서 제외한 exit나 boundary도 물리 state, supply와 backpressure에서는 제거하지 않는다.

### 2.2 신호와 시간 불변식

- `.inpx`의 `signalController/@supplyFile2`만 SC-to-SIG 정본으로 사용한다.
- active program, program offset, controller offset, cycle epoch, action lag를 서로 다른 항으로 보존한다.
- SG의 raw millisecond timeline이 정본이다. stage는 SG timeline에서 유도하며 amber, all-red,
  intergreen을 버리지 않는다.
- 신호 head는 lane을 제어한다. 공용 차로의 movement를 서로 독립적인 물리 queue나 독립 SG처럼
  조작하지 않는다.
- native network 승격은 원본 SC별 cycle에서만 한다. 150초 정규화본은 별도 제어 실험이다.
- offset은 profile별 timing, readback와 paired-effect gate 전까지 production writer에서 비활성화한다.

### 2.3 증거와 재현성 불변식

- calibration은 seed 47 holdout을 보지 않고 동결한다. holdout으로 파라미터나 임계값을 고치면
  새 calibration version과 새 holdout이 필요하다.
- 모든 run은 network, SIG, signal reference, topology, calibration, mapping, adapter, NumSim,
  runner/VBS, Python/VISSIM version과 seed/demand/anchor/action hash를 가진다.
- 평균이 좋아도 demand, seed, H=1, lever 또는 핵심 교차로에서 반복 부호 반전이 있으면 실패다.
- `FAIL`은 nonzero exit로 전파한다. 필수 evidence가 없으면 `NOT_EVALUATED`; 필수 congested gate의
  `NOT_EVALUATED`는 promotion에서 `BLOCKED`다.
- 기존 `outputs/gates_*`와 commit 전 결과는 참고만 한다. 현재 hash로 재생성된 artifact만 판정한다.

### 2.4 모든 작업의 완료 계약

각 작업은 다음 일곱 항목을 모두 문서와 artifact에 남긴다.

`입력 및 hash / 구현 경로 / 실행 명령 / 출력 schema / 수치 판정 / 선행조건 / 중단조건`

"임계 미달", "추후 결정", "적절히 비교"처럼 값이나 책임 artifact가 없는 문장은 완료 기준이 아니다.

## S0R. 실행 기준선과 source identity 재개 - P0

v2의 S0 완료 표시는 취소한다. 현재 기준선은 `scripts/tests` 21/21 PASS, `tests` 9/10 PASS,
`plant/tests` 75/75 PASS로 총 105/106이다.
`tests/test_vissim_stackelberg_adapter_fidelity.py:75`가 snapshot `35a5c82`를 기대하지만 실제 vendor는
`0240ba8`이다. 이 상태에서 이후 동적 결과를 promotion evidence로 쓰지 않는다.

S0R은 S0R-1/2/3뿐 아니라 S1의 canonical signal reference, time-indexed active program과 SC12
공용-lane artifact가 하나의 provenance fingerprint에서 모두 PASS할 때만 닫힌다. subsection PASS는
S0R 완료가 아니다. compound closure 전에는 topology, dynamics, calibration, SPSA 또는 promotion run이
S0 완료를 인용할 수 없다.

### S0R-1. NumSim 정본, EOL과 import 계약

- production 기본 root는 bundled `vendor/NumSim-mine` commit `0240ba8`로 고정한다.
- `NUMSIM_REPO_ROOT` override는 snapshot commit, canonical Python-tree hash와 imported module 경로/hash가
  bundled 정본과 일치할 때만 허용한다.
- `.gitattributes`로 hashed source의 EOL을 선언한다. Git blob hash와 실제 실행 bytes hash를 모두 남긴다.
  서로 다른 EOL checkout의 raw SHA-256을 곧바로 source 불일치로 판정하지 않는다.
- `vendor/NumSim-mine/SNAPSHOT.md`를 adapter의 실제 import 정책과 일치시킨다.

`scripts/verify_runtime_source.py`는 **NEW** deliverable이다. strict mode는 bare `python` fallback을
금지하고 `RW_PYTHON_EXE`의 path/version/hash를 기록한다. 명령과 산출:

```powershell
$python = $env:RW_PYTHON_EXE
if (-not $python -or -not (Test-Path -LiteralPath $python)) { throw "RW_PYTHON_EXE is required" }
& $python -B scripts/verify_runtime_source.py --repo . --out outputs/runtime_source_v2_1.json
& $python -B -m unittest discover -s scripts/tests -v
& $python -B -m unittest discover -s tests -v
Push-Location plant
try { & $python -B -m unittest discover -s tests -v } finally { Pop-Location }
```

PASS: immutable baseline 106/106과 모든 **NEW** v2.1 unit/contract/spawn/fault-injection/integration test
실패 0, unexpected skip/discovery loss 0, imported external module 0, canonical tree mismatch 0,
snapshot mismatch 0, dirty tracked source 0, undeclared EOL 0. baseline과 added-test count를 분리 기록한다.

### S0R-2. strict runner와 run provenance v3

- auditor `--require-complete`와 runner `-Strict/-RequireComplete`는 **NEW CLI**다. `--help`/dry-run
  contract test 전에는 실행 가능하다고 판정하지 않는다.
- `scripts/run_plant_fidelity_matrix.ps1`와 새 paired runner는 auditor를 항상
  `--strict --require-complete`로 호출한다.
- `--strict`는 모든 FAIL, `--require-complete`는 해당 profile의 필수 NOT_EVALUATED에도 nonzero다.
- `preflight_manifest.json`에 exact import root, commit/tree/module hashes, network profile과 INPX hash,
  `supplyFile2`로 선택된 41개 SIG hash, signal reference, topology, calibration, mapping, runner/VBS와
  adapter hash, Python/VISSIM version을 기록하고 모든 case가 동일 preflight hash를 참조한다.

PASS: selected model SC 41, selected SIG 41, missing hash 0, run ID당 provenance fingerprint 1,
mixed provenance 0, failed gate인데 runner exit 0인 사례 0.

### S0R-3. 기준선 snapshot

fixed/no-control, demand 1.0, seed 13, 3,600초, warm-up 900초를 `-BaselineOnly`로 새 hash로 재생성한다.
`-BaselineOnly`는 **NEW CLI**이며 Cartesian matrix나 certification path를 열지 않는다. 각 run directory에 `.err`,
VBS config, state/action/readback JSON/CSV, stdout/stderr, wall-time profile을 보존한다.

정상 run 조건: `actual_sim_sec=3600`, anchor state 4개, action/readback pair 누락 0, COM 실패 0.
정적 경로 오류나 조기 종료 run의 COM 오류 수치는 신호 결함 근거로 쓰지 않는다.

## S1. 신호 정본, active program과 SC12 - P0

### S1-1. canonical signal reference

새 SIG parser를 만들지 않는다. `plant/src/vissim_strict/compiler.py`와
`plant/src/vissim_strict/signal_program.py`를 확장해 canonical artifact를 생성한다.

```powershell
& $python -B -m plant.src.vissim_strict.compiler network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output outputs/signal_reference_v2_1.json
```

artifact는 compiler version/hash, INPX hash, 41 SIG hash, SC/SG/head의 exact link-lane-pos,
connector의 시작 lane과 connector lane 수, destination, raw-ms timeline, clearance와 active program schedule을
포함한다. canonical JSON을 세 번 생성한 SHA-256이 같아야 한다.

PASS: reference resolution 100%, SG name mismatch 0, wrong-lane connector 0, timeline gap/overlap 0,
per-SC/program cycle reconstruction error 0 ms. 기존 `0.851`은 전체 stage-green 비율 regression으로만
보고하며 개별 SC 합격 임계로 쓰지 않는다.

### S1-2. active program과 exact timeline

- INPX `progNo`, `dailyProgLists`, runtime start time과 COM readback으로 시간별 program을 고정한다.
- 현재 network에서 program 1 가정이 맞는지 preflight와 1초 readback으로 재확인한다.
- `active_program: "0"` 같은 임의 fallback을 금지한다. 알 수 없으면 중단한다.
- raw `cycletime`, `switchpoint`, offset, command begin을 integer ms로 보존하고 half-open periodic interval을 쓴다.
- readback이 2 Hz 이상이면 event gate `<=0.5 s`; 1 Hz뿐이면 관측 가능한 `<=1.0 s`로 낮추고
  0.5초 gate는 `NOT_EVALUATED`로 남긴다.

PASS: active-program readback mismatch 0, SG transition 누락 0, 선택하지 않은 SG 조작 0,
min-green/conflict 위반 0.

### S1-3. SC12 공용 직진-좌회전 차로

기존 link-level reference와 "좌회전 전용" 해석은 모두 금지한다.

- EB connector `10241`은 2개 connector lane으로 source lane 1과 2의 직진을 받고, `10242`는 lane 2
  좌회전이다. head `50201`이 있는 `1220012103/2`는 직진+좌회전 공용이다.
- WB connector `10238`도 2개 connector lane으로 source lane 1과 2의 직진을 받고, `10240`은 lane 2
  좌회전이다. head `50601`이 있는 `1220013600/2`도 직진+좌회전 공용이다.
- lane 2의 물리 stock은 하나로 두고 route별 movement composition만 나눈다. EB lane-2 직진과 좌회전은
  모두 head 50201/SG5를 따르고 WB lane-2 두 movement는 head 50601/SG1을 따른다. lane-1 직진은
  각각 SG2/SG6을 독립적으로 따른다.
- 현재 fixed program에서 SG2=SG5, SG1=SG6 timeline이 같은지 세 program 모두 검증한다.
- 이 equality는 현재 profile의 stage-bundle 정책이지 물리 head 불변식이 아니다. production은 bundle을
  보존할 수 있다. SG2!=SG5 또는 SG1!=SG6을 허용하려면 conflict/min-green/readback을 다시 qualification한다.
  lane-2 직진과 좌회전에 서로 다른 indication을 주려는 경우에만 lane/head network를 별도 변경한다.

산출 `reports/sc12_shared_lane_resolution_v2_1.json`.
PASS: connector lane-range 재구성 정확, lane 2 stock duplicate 0, movement composition 합 1,
lane-2 movement가 lane-2 head 이외 SG에 매핑된 사례 0, 선언한 profile bundle 정책 위반 0.
이 gate 전에는 SC12 action ranking을 실행하지 않는다.

## A. lane-route graph와 physical stock topology - P0

### A-1. directed lane-route graph

`scripts/build_vissim_lane_graph.py`와 `scripts/resolve_lane_routes.py`를 신설하거나 기존 generator를
공통 모듈로 통합한다. hop-count/set BFS와 synthetic reverse edge를 production 경로에서 제거한다.

- connector의 from/to link, 시작 lane, connector lane 수와 lane 대응을 directed edge로 만든다.
- active static route와 `relFlow`, 물리 path length, 첫 downstream stopline/terminal 순으로 해소한다.
- 동일 terminal이 아니고 복수 경로가 실제로 존재하면 임의 최소 ID 대신 shared-route와 flow share를 남긴다.
- compass leg는 최종 connector/destination tangent에서 만든 보고용 metadata일 뿐 stock identity가 아니다.

산출 `outputs/vissim_lane_graph_v2_1.json`, `outputs/lane_route_proofs_v2_1.json`.
PASS: production unresolved 0, synthetic reverse edge 0, executable connector path coverage 100%,
flow-share 합 `1 +/- 1e-9`, 입력 순서 무작위 10회 canonical hash 동일.

### A-2. one-stock topology

`scripts/compile_physical_stock_topology.py`가 VISSIM `(link,lane,interval)`을 정확히 하나의 stock에 넣는다.
각 stock은 `members`, `kind`, `capacity`, upstream/downstream, `control_owner`, `visible_to`,
`objective_weights`, route evidence를 가진다. `link_owner`를 state key로 사용하지 않는다.

PASS: lane-interval missing/duplicate 0, ownership-attribution weight 합 `1 +/- 1e-9`, named objective
mode별 weight는 include stock이면 1, 명시적 exclude stock이면 0, agent mask나 iteration order에 따른
global stock mass 차이 `<=1e-9 veh`, 세 번의 artifact hash 동일.

## B. 상태 투영, 이동과 경계 stock - P0/P1

### B-1. projection ledger와 substep mass ledger

projection ledger는 scanned VISSIM 차량을 `(run_id,VehNo)`로 식별해 stock 하나에 매핑한다.
`N_unobservable`은 balancing residual이 아니며 source evidence가 있는 typed external/origin stock에 있어야 한다.
queue/in-transit/overflow 합이 stock 차량 수와 같고 ramp/mainline-origin을 포함한 단일
`TrafficState.total_physical_vehicles()`를 사용한다.

stock `i`와 substep마다
`closing_i = opening_i + accepted_external_i - sink_i + sum_j F[j,i] - sum_k F[i,k]`를 기록한다.
모든 internal transfer는 immutable `transfer_id`, source debit 하나, destination credit 하나, amount와
substep 하나를 가진다. source/destination transfer multiset이 동일해야 한다. global identity는 internal
flow를 넣지 않은 `N_close = N_open + accepted_external - sink_out`이다.

post-update clipping을 제거하고 receiving/sending 제약에서 흐름을 제한한다. 거부된 외부 유입은 typed
source/gate stock에 남긴다.

PASS: unique vehicle mapping과 explicit external coverage 100%, stock/global residual `<=1e-6 veh`,
transfer multiset mismatch 및 duplicate/missing transfer ID 0, clipped-away mass 0,
forced split/merge/full-receiver에서 전 차량 보존.

### B-2. observed speed, queue tail과 travel delay

VBS와 adapter는 이미 `link_speeds_kph`, stopped count와 queue tail을 내보낸다. 남은 일은 이를
lane-group `urban_stock_kinematics`에 넣고 rollout delay에 사용하는 것이다.

- positive-length movement는 같은 substep에 도착할 수 없다.
- observed speed가 있으면 global `urban_avg_speed_km_h`를 쓰지 않는다.
- missing speed는 stock/class prior와 fallback flag를 남긴다. zero speed는 zero delay가 아니다.
- FIFO in-transit buffer와 stopline queue service를 분리한다.

초기 gate: travel-time median error `<=10 s`, p95 `<=30 s`. promotion: median `<=5 s`, p95 `<=15 s`,
queue-tail MAE `<=20 m`, same-substep arrival 0.

### B-3. exit, boundary-out과 objective

226개 exit link를 유한 `boundary_out` stock으로 만든다. storage와 discharge capacity, upstream movement,
sink, opening/inflow/departure/closing, spillback을 가진다. objective include/exclude는 같은 물리 trace에
서로 다른 weight만 적용한다.

PASS: exit coverage 226/226, duplicate 0, exit mass residual `<=1e-6`, objective mode 간 state/flow trace
byte-identical, objective 차이가 기록된 boundary contribution과 `<=1e-9`로 일치.

external urban/freeway/ramp arrival은 첫 physical receiver가 수용한 만큼만 들어오며 거부량은 typed
origin/gate stock에 남는다. boundary-out stock은 실제 in-network exit-link storage까지만 포함하고,
VISSIM에 downstream bottleneck이 없으면 그 뒤 sink는 unbounded다.

### B-4. ramp, off-ramp와 freeway

- physically independent connector/lane queue를 합치지 않는다. 하나의 command group이 여러 stock을
  제어할 수는 있다.
- 각 ramp merge와 off-ramp diverge의 실제 chain coordinate/segment를 보존한다.
- scalar ramp cap fallback을 production에서 금지하고 per-stock cap을 모든 dynamics/coupling 경로에서 쓴다.
- freeway 100% count reconstruction은 상태 gate일 뿐 동역학 합격 근거가 아니다.

merge의 모든 sending flow는 priority rule이 명시된 하나의 downstream receiving budget을 공유한다.
diverge의 FIFO/non-FIFO route-class 규칙은 lane connectivity로 정하고, full off-ramp storage는 막힌 class에
대해서만 upstream으로 전파한다.

PASS: ramp connector missing/duplicate 0, merge/diverge relocation 0, group flow와 physical flow 합 차이
`<=1e-9 veh/substep`, freeway segment gap/overlap 0 m, production topology fallback 0.

behavior fixture는 full urban receiver, full freeway merge, full off-ramp, blocked physical exit와 rejected
external source를 포함한다. 각각 upstream queue 증가, downstream flow 감소, transfer-ledger 보존, clipping 0을
보여야 한다. promotion은 per-interface error를 gate하며 network-wide WAPE만으로 통과하지 않는다.

## C. N현시 모델, monitor schedule과 action contract - P0/P1

### C-1. movement, lane stock과 SG mapping

경로는 `head lane -> lane-range connector -> destination stock -> movement`까지 추적한다.
키는 `(SC,SG number)`이며 이름, NEMA 산술, 45도 방위 fallback을 production mapping에 쓰지 않는다.

- collection-only diagnostic artifact는 unresolved가 vehicle weight `>0.1%`인 개별 movement 또는 전체
  `>1.0%`이면 생성을 거부한다. promotion artifact는 exact coverage 100%, unresolved vehicle mass 0이다.
- 공용 lane은 stock 하나와 movement composition을 사용하고 head/stage coupling을 artifact에 명시한다.
- exact mapping이 없는 vehicle mass는 항상 unresolved이며 angle fallback으로 PASS 처리하지 않는다.

### C-2. monitor 26개 fixed timeline

monitor node는 항상 green이 아니라 "fixed schedule, controller immutable" 부류다. canonical SIG timeline,
offset, permanent-red와 cycle wrap을 재생한다. exact mapping 전 legacy union은 promotion 근거가 아니다.

PASS: monitor always-green movement 0, permanent-red green fraction 0, 모든 monitor schedule/hash 존재,
monitor queue/storage가 물리적으로 갱신됨.

### C-3. N-phase green fraction과 native per-SC cycle

`NetworkConfig`에 `cycle_length_by_signal`, canonical SG/stage timeline과 per-SC lookup을 넣는다.
`_phase_green_fraction`은 raw timeline의 부분 step green을 적분한다. clearance는 실제 SIG를 쓴다.

PASS: 기존 artifact가 없는 N=2 경로 bit-identical, `urban_step_index=None` cycle average 일치,
SC별 cycle reconstruction error 0, native production에서 scalar-cycle fallback 0.

### C-4. VBS/action schema와 fail-closed 적용

N-phase action은 stage durations 또는 tangent coordinates와 canonical artifact hash를 가진다. 모델 state,
action CSV, VBS config와 readback의 artifact hash가 다르면 적용하지 않는다. 소비자 Python/PS/VBS를 전수한다.

PASS: partial application 0, request/readback mismatch 0, shared-lane SG constraint 위반 0,
conflicting SG simultaneous green 0, min-green/clearance 위반 0.

## D. 신호 timing oracle와 offset promotion - P1

`D-core`는 expected transition과 immediate/post-step COM readback, source offset, command lag,
cycle-boundary, positive-lag sign, native per-SC cycle, conflict/min-green을 검증한다. green-only production
release는 D-core 뒤에 온다.

isolated certification harness만 D-core PASS 후 test-only writer로 forced offset arm을 낼 수 있다.
production writer는 그동안 `intent_only`다. `D-offset-enable`은 같은 profile/hash의 D-core,
J offset effect/ranking과 I runtime이 모두 PASS할 때만 production writer를 해제한다.

normalized-150s offset PASS는 native offset을 활성화하지 않는다. 미승격 profile의 nonzero offset write는
fail-closed로 거부한다.

## G. development data producer - P0

**NEW** `scripts/run_development_data_v2_1.ps1`가 calibration-development 6 parent와 SPSA
qualification-only 3 parent를 VISSIM에서 순차 실행한다. certification seed/root는 인자, ACL과 출력에서
금지한다. anchor 900/1500/2100/2700의 state/telemetry/action/readback hash를 보존하고 각
development parent/anchor에서 독립 `t=0` base replay를 최소 20회 실행한다.

```powershell
powershell -NoProfile -File scripts/run_development_data_v2_1.ps1 -Strict -RequireComplete -OutDir evaluation/runs/development_v2_1
```

산출은 `outputs/state_manifest_v2_1.json`, `outputs/development_pairs_v2_1.json`,
`outputs/calibration_development_manifest_v2_1.json`, `outputs/development_noise_v2_1.json`과
`development-campaign-v2.1` manifest다. noise는 stratum별
`eps_J=max(1e-6 veh*h,max_{i,j}|J_base_i-J_base_j|)`로 동결한다.
PASS: calibration parent 6/6, qualification-only parent 3/3, anchors complete, missing/duplicate/cross-role use 0,
base replay parent-anchor당 `>=20`, certification path access 0. repeat는 support를 늘리지 않는다.
이 artifact 없는 B/E/H/I/J consumer는 NOT_READY다.

## E. 물리 파라미터 calibration과 holdout - P1

### E-1. disjoint whole-run split과 one-shot certification

첫 promotion attempt의 physical parent run은 calibration-development 6개, SPSA qualification-only 3개,
sealed wave-A certification 9개로 총 18개다. qualification-only는 세 demand와 seed 31의 Cartesian
product이며 calibration/certification에 쓰지 않는다. fresh certification wave는 세 demand와 사전 등록
fresh seed 3개의 Cartesian product 9개다. S0 demand1.0/seed13 snapshot은 development parent와 같은 hash면
재사용할 수 있으나 별도 role/support로 중복 집계하지 않는다.

| 용도 | demand | seed |
|---|---|---|
| training | 0.75, 1.0 | 13, 29 |
| congested selection | 1.25 | 13, 29 |
| SPSA qualification only | 0.75, 1.0, 1.25 | 31 |
| certification wave A | 0.75, 1.0, 1.25 | 47, 59, 71 |

calibration/selection parent와 certification parent는 seed, run ID, telemetry, anchor와 future가 겹치지 않는다.
wave A를 열기 전에 source, topology, calibration, candidate set, perturbation, metric/threshold와 auditor code를
동결하고 hash한다. certification은 fitting, threshold 선택, candidate 교체 또는 defect loop에 쓰지 않는다.

scientific gate가 실패하면 wave A를 retire하고 diagnostic으로만 남긴다. 수정 후 재승격은 새 calibration
version과 사전 등록한 fresh seeds `83/97/109`를 요구한다. action 적용 전 infrastructure failure이며 outcome과
무관함이 입증된 경우만 동일 wave를 재실행할 수 있다. access log와 holdout-open time을 artifact에 기록한다.

fit process는 restricted identity/allowlist wrapper에서 development manifest만 받고 reserved certification
root를 ACL로 deny한다. denied-path probe와 access log가 0 read를 입증해야 한다.

wave를 열기 전 `certification_campaign_request`에 wave ID, expected Cartesian parent specification,
preregistered pair/request ID, demand/seed/config hash, E-cert, I-2, I-4, J, K와 release publisher의 exact
consumer/code hash를 봉인한다. 아직 존재하지 않는 runtime output hash를 claim하지 않는다.

orchestrator는 launch 전에 immutable run ID를 할당하고 정확히 9 request를 실행한 뒤 실제 telemetry/artifact
hash를 sealed campaign manifest에 기록한다. request-to-run linkage 9/9, config mismatch 0, missing actual hash 0,
unexpected run ID 0이어야 한다.

orchestrator는 certification input과 모든 intermediate result를 하나의 ACL-restricted staging root에 두고
등록 child process만 접근하게 한다. E-cert/I-2/I-4/J/K는 public `outputs/`나 `reports/`에 쓰지 않는다.
K까지 끝난 뒤 orchestrator가 signed exact-hash bundle 하나를 atomic publish하고 single release event를 남긴다.
이 한 campaign 안의 consumer들은 별도 scientific open이 아니다.

unregistered/post-release access, alternate output path, partial publish, consumer/code/hash 변경, scientific failure 뒤
rerun은 wave 전체를 retire한다. ACL logger는 staging input과 result tree의 read/write를 모두 기록한다.
infrastructure-only retry는 action 전/outcome-independent 예외를 만족하고 access log에 남아야 한다.

### E-2. 추정 대상과 artifact

`evaluation/calibration/physical_stock_calibration_v2_1.json`에 run IDs/split, estimator/version,
sample count, vehicle length+standstill geometry prior, fitted value, run-cluster bootstrap 95% CI,
stock lane-metres/capacity, jam density, fallback queue fraction, ramp/exit storage와 discharge를 기록한다.

- 직렬/병렬 storage는 lane connectivity와 merge evidence로 분리한다.
- jam density는 `speed<=3 kph`, stopped fraction `>=0.5`인 saturated lane-group에서 robust fit한다.
- queue-tail 관측이 있으면 0.35/0.50 fraction 대신 관측 분해를 쓴다.

PASS: split overlap 0, saturated independent lane-group `>=30`, samples `>=200`, jam CI half-width
`<=estimate의 10%`, geometry prior 차이 `<=15%` 또는 BLOCKED, training seed별 fit 차이 `<=15%`,
vehicle-weighted fallback fraction 사용 `<=10%`.

certification PASS는 추가로 physical-capacity exceedance가 stock-time의 `<=0.5%`이고 초과 질량 전량
upstream/overflow 보존, 관측 queue split MAE `<=max(2 veh,10%)` 및 signed bias `<=5%`, storage-fraction
CI half-width `<=10%`, ramp/boundary storage/discharge CI half-width `<=15%`, discharge WAPE `<=10%`,
signed bias `<=5%`를 요구한다. missing support/CI/run ID 또는 per-stock 실패는 BLOCKED다.

parent matrix PASS: calibration-development 6, qualification-only 3, wave-A certification 9,
unique demand-seed-role parent 18, expected Cartesian cell missing/duplicate 0, cross-role overlap/use 0.

## H. production MPC rollout endpoint 통합 - P0

감사 kernel을 따로 합격시키는 것으로는 충분하지 않다. **NEW**
`vendor/NumSim-mine/src/simulation/production_rollout.py`에 pure
`evaluate_price_point(state, previous, forecast, action_schedule, objective_spec)` endpoint를 만들고
`stackelberg_mpc.py`, `stackelberg_wu_metered.py`, adapter의 실제 `decide_with_info` 경로에 통합한다.
`plant/src/vissim_strict`는 계약/oracle로 유지하며 별도 승인 없이 runtime plant로 바꾸지 않는다.

- MPC가 feasible candidate 생성, objective 비교와 action 선택을 소유한다. endpoint는 state projection,
  controller-independent dynamics, constraints, lever response와 objective components만 평가한다.
- leader/follower scoring, exact FD, SPSA, no-control replay와 audit replay는 같은 endpoint와 frozen parameter를 쓴다.
- corrected underlying coupled dynamics 호출은 endpoint 내부에서만 허용한다. production candidate의 endpoint
  우회 direct `run_coupled_interval` 또는 audit-only kernel 호출은 0이어야 한다.
- endpoint가 candidate scoring에 사용한 exact `ActionSchedule`과 activation boundary를 반환하고 hash한다.

```powershell
& $python -B scripts/verify_production_rollout_path_v2_1.py --config evaluation/configs/real_world_modi_pstack_v8_urban36_budget_20260805.json --out outputs/production_rollout_path_v2_1.json
```

artifact `production-rollout-path-v2.1`은 모든 `decide_with_info` candidate의 endpoint/source, topology,
calibration, objective, action-schedule hash, objective components와 selected action을 기록한다.
PASS: green/VSL/meter/no-control과 eligible offset path coverage 100%, endpoint call 수=candidate evaluation 수,
bypass/audit-only call 0, action 선택은 controller에만 존재, one-step/H=3 production integration test PASS.

## I. marginal price, SPSA와 runtime - P0/P1

### I-0. qualification request producer

H=PASS의 exact endpoint/lever inventory와 G development states에서 **NEW**
`scripts/build_price_runtime_qualification_requests.py`가
`outputs/spsa_qualification_request_v2_1.json`과 `outputs/runtime_development_request_v2_1.json`을 만든다.
각 request는 state/schedule/objective/source hash, channel coordinate, H, direction seed, repeat와 expected count를
봉인한다. PASS: source state coverage 100%, expected request missing/duplicate 0, certification state/reference 0.

### I-1. exact FD와 SPSA qualification

FD와 SPSA는 하나의 pure production
`evaluate_price_point(state, previous, forecast, control, objective_spec)`를 호출한다. endpoint control,
objective components, feasibility, terminal state hash와 realized perturbation span이 byte-identical하지 않으면
비교 자체가 FAIL이다.

- qualification state마다 identical-control objective를 최소 20회 평가해
  `eps_J=max(q99(abs(J_r-J_1)),1e-9*max(abs(J_1),1))`를 구하고 coordinate noise를
  `eps_g=2*eps_J/realized_span`으로 환산한다. objective-unit noise를 gradient와 직접 비교하지 않는다.
- central FD를 `h`와 `h/2`에서 비교한다. 사전 등록 convergence tolerance 실패는 required coordinate의
  `INDETERMINATE/BLOCKED`다. tolerance는
  `abs(g_h-g_h2)<=max(eps_g,0.10*max(abs(g_h2),eps_g))`다.
- full-step `h`는 green `6 s`, VSL `10 km/h`, offset `C/8`, ramp meter
  `max(300 veh/h,0.20*capacity)`로 사전 등록한다. 두 estimator는 requested span이 아니라 bounded realized
  displacement로 나눈다.
- SPSA pair count `k={8,16,32,64}`, state당 independent direction batch 30개를 development/selection에
  사전 등록하고 모든 stratum을 통과하는 최소 k를 동결한다.
- SPSA qualification development state는 demand 3개, seeds `13/29/31`, anchors
  `900/1500/2100/2700`의 Cartesian product를 사용해 demand당 12 independent state cluster를 만든다.
  seed 31은 qualification 전용이며 certification에 재사용하지 않는다.
- 전체 최소 12 state cluster가 모든 demand, H, channel, free/congested와 active/inactive barrier regime을
  덮는다. 각 `channel x demand x H` stratum은 independent state cluster 최소 12와 nonempty material set을,
  channel별 material comparison은 최소 29개를 요구한다.
- nRMSE와 intercept 포함 regression은 `channel x demand x H`별 state-block bootstrap 95% CI로 계산한다.
  nRMSE는 `RMS(g_spsa-g_fd)/max(RMS(g_fd),median(eps_g))`다. upper limit `<=0.20`, slope CI 전체
  `0.90..1.10`, `abs(intercept)<=median(eps_g)`, 반복 material sign reversal 0을 요구한다.
- coordinate는 `abs(g_fd)*realized_span >= max(5*eps_J,0.005*max(abs(J0),1))`일 때만 material이다.
  required stratum이 support 미달이면 빈 remainder PASS가 아니라 BLOCKED다.
- exact sign bound는 state-direction batch당 사전 등록한 coordinate 하나만 독립 Bernoulli로 센다. 여러
  coordinate를 같은 SPSA pair에서 독립 표본처럼 세지 않는다. one-sided Clopper-Pearson 95% upper bound는
  overall `<=0.05`와 material independent comparison 최소 59개, channel별 `<=0.10`과 최소 29개다.
- N-stage signal은 deterministic Helmert `(N-1)` tangent basis를 쓰고 N=2/3/4/5/6 및 모든 active N을
  시험한다. bound-collapsed coordinate는 zero gradient가 아니라 ineligible이다.

raw 15-lever 표나 material remainder가 빈 결과는 qualification 근거가 아니다. k와 모든 threshold는
certification wave를 열기 전에 동결한다.

### I-2. production decision parity

gradient만 비교하지 않는다. sealed certification state 36개와 SPSA direction seed 3개, 총 108 twin에서
feasible candidate set, candidate objective/ranking, selected action, constraints/barrier, spillback guard,
meter release certification, status와 fallback class를 exact FD와 SPSA 사이에 비교한다. sidecar는 매 twin마다
reset한다.

PASS: controller status, feasibility, safety certificate, fallback class, leader candidate, guard와 meter
certification 108/108 exact match. command는 exact match 또는 선언한 quantization step 1개 이내이고 exact-FD
rescored regret가 `max(2*eps_J,0.5%*abs(J_FD))` 미만이어야 하며 모든 material runner-up ordering이 같다.
hash-bound artifact가 없으면 `price_spsa_enabled=True`를 startup에서 거부한다.

**NEW** command/artifact: `scripts/run_spsa_fd_parity.py`, `spsa_fd_parity.json`,
`production_decision_parity.jsonl`, `production_decision_parity_summary.json`.

### I-3. unified rollout scheduler

green만 별도 병렬화하지 말고 green, meter, VSL, offset의 독립 rollout을 하나의 deadline-aware scheduler에
넣는다. Windows spawn-safe worker, task timeout/cancel, deterministic reduction, fallback telemetry와
정확한 `_price_rollout_count`를 구현한다.

workers 0/1/2/5에서 candidate objective/price가 `<=1e-9`, selected action이 exact match여야 한다.
parallel 예외 뒤 silent serial 재실행은 금지한다. fallback은 reason, spent time, remaining budget을 남긴다.

### I-4. runtime 계약

현재 production H=3 한 건 `154.746 s`뿐이므로 45초 달성 주장은 **NO-GO**다. runtime은 두 clock을
동시에 기록한다: production `decide_with_info` entry-to-result와 anchor observation scan 시작부터 validated
COM action readback까지의 end-to-end다. operational gate는 end-to-end clock만 만족한다.

- adapter는 absolute monotonic deadline을 받는다. 30초 target-overrun event, 42초에 adapter/worker process
  tree만 terminate/recycle하고 VISSIM은 paused/alive로 유지하며 fallback 생성, 검증, 적용, readback에 3초를
  예약한다. cleanup/fallback도 45초 max 안이다.
- fallback은 last feasible command의 payload만 복사한 뒤 current observation에 새 `based_on_state_hash`,
  action ID/hash, validity와 activation boundary를 부여한다. COM 전 topology/profile hash, authority, current
  signal phase/min-green/conflict, actuator bounds, mass state, spillback guard와 safety certificate를 전부 다시
  검증한다. 하나라도 실패하면 즉시 validated native fixed plan을 선택한다. 두 연속 controller 실패는 fixed
  plan을 latch한다. old CSV/hash는 재사용하지 않고 생성/검증/적용/readback이 모두 45초 안이다.
- demand x certification seed x cold/warm stratum마다 최소 100 attempt와 독립 VISSIM run 최소 10개를
  random blocked order로 수집한다. target hardware, CPU/RAM/power/start method/load를 기록한다.
- controller success와 fallback latency를 분리한다. fast fallback은 성공 decision으로 세지 않고 timeout
  sample은 censor하지 않는다.

PASS: 각 stratum run-cluster 95% upper confidence limit p95 `<=30 s`, observed max `<=45 s`, controller
fallback `<5%`, timeout `<1%`, silent fallback/stale action/readback failure/orphan worker 0, fault-injection
recovery 100%. certification performance evidence의 fallback은 0이다.

## J. paired VISSIM future와 동적 검증 - P1/P2

### J-1. replay와 identity

VISSIM snapshot restore가 bit-valid하다는 별도 증거가 없으므로 모든 branch를 `t=0`부터 재실행한다.
canonical anchor에서 pre-action COM state를 capture/hash하고 H production endpoint에 candidate scoring에
사용한 exact `ActionSchedule`을 요청한다. plant와 VISSIM은 byte-identical schedule entries,
`activation_boundary_sec`, half-open `[start_time_sec,end_time_sec)`, move-blocking/walk와 restoration command를
사용한다. impulse-only schedule은 별도 diagnostic이며 held/multi-entry production schedule을 승격하지 못한다.

prefix는 schedule의 first effective transition 직전 state까지 동일해야 하며 첫 divergence는 그 transition
후 state다. signal safe-boundary가 늦으면 `anchor+1`을 강제하지 않고 schedule/readback의 실제 boundary를 쓴다.

canonical run key:

```text
(experiment_id, network_profile_hash, inpx_hash, signal_set_hash,
 active_program_schedule_hash, topology_hash, calibration_hash,
 adapter_hash, controller_hash, numsim_hash, demand, seed, anchor_sec, H,
 channel, lever_id, action_payload_hash, action_schedule_hash,
 first_effective_transition, valid_from_sec, valid_until_sec, replicate)
```

run manifest는 `based_on_state_hash`, request time, 모든 entry boundary, first/last effective transition,
restoration/readback와 parent-prefix hash를 포함한다. H는 한 physical branch가 여러 endpoint를 공급할 때도
endpoint dimension으로 남긴다. missing/early/late/partial/stale actuation은 window shift로 보정하지 않는다.
clock fixture는 anchor 900/2700과 모든 H에서 prefix, first affected state, entry boundary, final affected state,
restoration/readback와 `anchor+60*H` endpoint를 검사한다.

### J-2. 실험 행렬과 action epoch

- development diagnostics는 seed 13/29, promotion은 sealed wave의 `47/59/71`만 사용한다.
- demand `0.75/1.0/1.25`, run 3,600초, warm-up 900초
- anchors `900/1500/2100/2700`, H `1/3/5/10/15`, control interval 60초
- 현재 `control_horizon_steps=1, move_blocking=true`이면 candidate는
  `[anchor_sec,anchor_sec+60*H)`에 held되고 endpoint를 읽은 뒤 base로 복귀한다. production이 다른
  held/walked schedule을 내면 그 exact schedule이 정본이다.
- VISSIM은 한 번에 하나만 실행한다.
- 기본은 one-lever-at-a-time low/base/high이며 joint action은 별도 experiment ID다.

feasible low/high:

- green: canonical tangent basis에서 base 대비 `-10/+10 s`, min-green/clearance/cycle로 cap
- VSL: base 대비 `-10/+10 km/h`, actuator bounds로 cap
- ramp meter: base 대비 `-150/+150 veh/h`, actuator bounds로 cap
- offset certification arm: production writer와 분리된 test-only writer가 D-core timing/sign/readback PASS 후
  base 대비 `-10/+10 s`를 native cycle modulo로 적용한다. realized readback이 같은 valid-interval contract를
  입증하지 못하면 offset은 NOT_EVALUATED/BLOCKED이고 production writer는 `intent_only`로 남는다.

세 값이 distinct하지 않으면 해당 cell을 `NOT_EVALUATED`로 기록하고 더 작은 symmetric step을 한 번 시도한다.
값을 사후 조정하지 않고 request manifest에 exact value/hash를 먼저 봉인한다.

### J-3. 비교와 aggregation

VISSIM 1초 관측을 보존하고 60초 control interval로 집계한다. noise floor는 G에서 certification 전에
동결한 20회 independent `t=0` base replay의 conservative `eps_J`를 쓴다. action effect는 같은 prefix의
`Delta J(action)=J(action)-J(base)`로 계산하며 retries는 새 payload hash/run key를 가진다.

controlled 15, monitor 26, midblock 9,
boundary, ramp, freeway를 분리한다. count, queue, storage, speed, inflow/outflow, TTT, spillback
onset/release, actuator effect와 ranking을 비교한다.

모든 raw row는 demand, certification seed, anchor, H, channel, lever, entity, interval로 keyed한다. H=1은
독립 gate다. complete cell은 사전 등록한 feasible low/base/high를 모두 포함하며 mandatory arm 누락은
dropped row가 아니라 BLOCKED다. repeat는 noise만 추정하고 support를 늘리지 않는다. tie는 VISSIM effect가
`2*eps_J`와 `0.5%*max(abs(J_base),1 veh*h)` 모두 이하일 때만 `INDETERMINATE`다.

### J-4. 동적 합격 gate

`Initial acceptance`는 diagnostic이며 production 권한이 아니다. promotion은 initial과 promotion-only gate의
교집합이다. movement mapping은 exact coverage 100%, unresolved vehicle mass 0이어야 하고 native signal event
error `<=0.5 s`가 필요하다. 1 Hz-only profile은 이 gate가 BLOCKED다.

sealed wave를 열기 전 development initial gate는 H=1 urban queue/storage NMAE `<=25%`, count MAE
`<=max(5 veh,10%)`, freeway speed MAPE `<=10%`다. 하나라도 실패하면 certification을 열지 않는다.

metric 정의: `NMAE=sum(abs(pred-obs))/max(sum(obs),1 veh)`, zero-observation MAE `<=1 veh`, speed MAPE는
vehicle-weighted denominator `max(obs_speed,5 kph)`, TTT APE denominator `max(obs_TTT,1 veh*h)`다. 모든
absolute metric은 같은 denominator의 signed bias를 함께 gate하고 `abs(signed_bias)`가 해당 H의 absolute
metric limit를 넘으면 실패한다. flow signed bias는 항상 `<=10%`다.

| H | promotion gate |
|---:|---|
| 1 | urban queue/storage NMAE `<=15%`; travel median/p95 `<=5/15 s`; tail MAE `<=20 m`; freeway speed MAPE `<=10%`; count MAE `<=max(5 veh,10%)`; flow GEH `<=5`인 row `>=85%`, signed flow bias `<=10%`; TTT APE `<=10%` |
| 3 | TTT APE `<=12%`; terminal queue/storage NMAE `<=20%`; speed MAPE `<=15%`; count MAE `<=max(7.5 veh,15%)`; H1 flow gate 유지 |
| 5 | TTT APE `<=15%`; terminal queue/storage NMAE `<=20%`; speed MAPE `<=15%`; count MAE `<=max(7.5 veh,15%)`; H1 flow gate 유지 |
| 10 | TTT APE `<=18%`; terminal queue/storage NMAE `<=35%`; speed MAPE `<=20%`; count MAE `<=max(10 veh,20%)`; nonfinite/negative/clipping/mass failure 0 |
| 15 | TTT APE `<=20%`; terminal queue/storage NMAE `<=35%`; speed MAPE `<=20%`; count MAE `<=max(10 veh,20%)`; nonfinite/negative/clipping/mass failure 0 |

urban/ramp boundary flow WAPE `<=10%`, off-ramp WAPE `<=15%`를 별도 interface gate로 둔다.
lever effect는 `demand x H x channel x certification_seed`마다 material comparison 최소 24를 요구한다.
material은 `|Delta J_VISSIM|>max(2*eps_J,0.005*max(|J_base|,1 veh*h))`다.
`effect_NMAE=sum|Delta J_plant-Delta J_VISSIM|/max(sum|Delta J_VISSIM|,n*eps_J)<=0.25`,
absolute signed-effect bias `<=0.15`, material sign agreement 100%다. lever별 sign failure를 pooling하지 않는다.

같은 stratum에서 Spearman `>=0.70`과 top pairwise `>=0.80`은 point estimate와 parent-then-anchor cluster
bootstrap 95% lower confidence bound가 모두 통과해야 한다. H/demand/channel/lever/seed failure는 pooling으로
구제하지 않으며 각 seed가 trajectory limit의 1.25배를 넘으면 실패다.

spillback support는 `(run_id,anchor,physical_stock_id)` episode당 positive/negative 각 최대 하나로 센다.
mandatory congested `demand x H x channel x certification_seed x asset-class`마다 independent positive/negative 각 20,
F1 `>=0.80`, onset/release median absolute error `<=60 s`, p90 `<=120 s`다. H/demand/channel/seed/asset를
pooling하지 않는다. low demand positive가 5개 미만이면 spillback gate만 NOT_EVALUATED다.

## K. auditor, promotion과 반복 검증 - P2

`scripts/audit_plant_fidelity.py`에 source, signal, topology, projection, substep mass, calibration,
paired dynamics, action ranking, SPSA qualification와 runtime gate를 모두 추가한다.

promotion은 세 demand의 모든 certification seed에서 필수 gate가 PASS일 때만 가능하다. low demand는
spillback 이외 metric을 면제하지 않는다. machine state가 정본이며
`PASS=지지 가능`, `FAIL=불가`, `NOT_EVALUATED=미평가`, `BLOCKED=조건부/승격 불가`로 고정한다.
required non-PASS는 strict runner에서 모두 nonzero다.

결함 수정 loop:

1. failing artifact와 최소 재현 test를 먼저 고정한다.
2. 결함 하나를 수정하고 관련 static/unit gate를 실행한다.
3. 같은 영역의 독립 reviewer가 spec과 물리 불변식을 검토한다.
4. development paired cell만 재실행한다. opened certification wave의 scientific failure는 수정 loop에
   재사용하지 않고 retire한다. fresh certification seed wave를 사전 등록한다.
5. 마지막에 immutable baseline 106개와 모든 NEW test, strict full matrix, whole-branch review를 수행한다.

동일 load-bearing finding이 5회 fix/review에도 남으면 숨기지 않고 BLOCKED로 판정한다.

## X. native cycle과 150초 정규화 실험 분리

- **X-1 native per-SC cycle**은 C와 J/K의 선행조건이다. 원본 network/SIG를 바꾸지 않는다.
- **X-2 normalized-150s**는 별도 `.inpx`, SIG/reference hash, run directory, audit와
  `reports/network_change_*.md`를 가진다.
- 150초 program이 실제 존재하는 SC만 그 program을 쓴다. 나머지는 min-green/clearance를 지키는
  별도 network-design task다. program 목록을 추정하거나 SC107처럼 150초가 없는 예를 포함하지 않는다.
- normalized 결과는 native plant, native offset 또는 native controller를 승격하지 못한다.

## 실행 계약 매트릭스

아래 **NEW** path/flag는 먼저 CLI parser/dry-run test를 만든다. 모든 command는 `RW_PYTHON_EXE`로 실행하고
입력 hash 불일치, 필수 artifact 누락 또는 task-local gate 실패 시 즉시 nonzero로 중단한다.

| Task | inputs + hashes | implementation paths | command | artifact path + schema | numeric verdict | prerequisites + stop |
|---|---|---|---|---|---|---|
| S0R-1 | repo/vendor/EOL/Python | **NEW** source verifier, adapter/SNAPSHOT/tests | S0R-1의 네 명령 | `outputs/runtime_source_v2_1.json`, `runtime-source-v2.1`; test manifest | S0R-1 PASS 106/106 + NEW 0 fail | none; mismatch/test failure stop |
| S0R-2 | source/network/SIG/mapping | auditor/runner **NEW** flags | `powershell -NoProfile -File scripts/run_plant_fidelity_matrix.ps1 -Strict -RequireComplete -DryRun` | `outputs/preflight_manifest_v3.json`, `preflight-v3` | S0R-2 counts/hash/exit gate | S0R-1; CLI/dry-run failure stop |
| S0R-3 | fixed demand1.0/seed13 config | runner **NEW** `-BaselineOnly` | `powershell -NoProfile -File scripts/run_plant_fidelity_matrix.ps1 -Strict -RequireComplete -BaselineOnly` | `outputs/baseline_snapshot_v2_1.json`, `baseline-snapshot-v2.1` | exactly one complete 3600초 parent | S0R-2; seed/demand/path expansion stop |
| S1-1/2 | exact INPX + 41 SIG | strict compiler/signal parser/readback | `& $python -B -m plant.src.vissim_strict.compiler network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output outputs/signal_reference_v2_1.json` | `outputs/signal_reference_v2_1.json`, `signal-reference-v2.1` | S1-1/2 exact resolution/timeline/0.5초 gate | S0R-core; any required non-PASS stop |
| S1-3 | signal reference + SC12 | **NEW** shared-lane validator | `& $python -B scripts/validate_sc12_shared_lane.py --reference outputs/signal_reference_v2_1.json --out reports/sc12_shared_lane_resolution_v2_1.json` | report JSON, `sc12-shared-lane-v2.1` | S1-3 lane/head/composition/policy 0 error | S1-1/2; mismatch stop |
| A-1 graph | INPX/routes/roles | **NEW** lane graph builder | `& $python -B scripts/build_vissim_lane_graph.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --out outputs/vissim_lane_graph_v2_1.json` | graph JSON, `lane-graph-v2.1` | A-1 path coverage/order gate | S0R closure; synthetic/broken edge stop |
| A-1 routes | lane graph/routes | **NEW** route resolver | `& $python -B scripts/resolve_lane_routes.py --graph outputs/vissim_lane_graph_v2_1.json --out outputs/lane_route_proofs_v2_1.json` | proof JSON, `lane-route-proof-v2.1` | unresolved 0/share sum gate | A-1 graph; unresolved stop |
| A-2 | graph/proofs | **NEW** stock compiler | `& $python -B scripts/compile_physical_stock_topology.py --graph outputs/vissim_lane_graph_v2_1.json --routes outputs/lane_route_proofs_v2_1.json --out outputs/physical_stock_topology_v2_1.json` | topology JSON, `physical-stock-v2.1` | A-2 membership/objective/order gate | A-1; missing/duplicate stop |
| DEV-DATA | demands3; calibration seeds13/29 + qualification seed31; anchors4 | **NEW** development VISSIM runner/manifest builder | `powershell -NoProfile -File scripts/run_development_data_v2_1.ps1 -Strict -RequireComplete -OutDir evaluation/runs/development_v2_1` | state/development/calibration/noise JSON manifests, `development-campaign-v2.1` | calibration parents 6/6, qualification 3/3, base repeats `>=20`/parent-anchor, role overlap/cert access 0 | S0R/A/C observation contract; missing hash/anchor/role stop |
| B-1 | states/topology | adapter/state/models + **NEW** validator | `& $python -B scripts/validate_state_projection_v2_1.py --states outputs/state_manifest_v2_1.json --out outputs/projection_mass_v2_1.json` | projection/mass JSON, schemas `projection-v2.1`/`mass-ledger-v2.1` | B-1 vehicle/transfer/residual/clipping gate | A-2; any conservation failure stop |
| B-2 | kinematics/topology | adapter/urban model + **NEW** validator | `& $python -B scripts/validate_urban_kinematics.py --manifest outputs/development_pairs_v2_1.json --out outputs/urban_kinematics_v2_1.json` | JSON, `urban-kinematics-v2.1` | B-2 initial/promotion delay gates | B-1; zero-delay/fallback misuse stop |
| B-3/4 | boundary/ramp/freeway topology | adapter/models/coupling + **NEW** fixtures | `& $python -B scripts/validate_boundary_coupling_v2_1.py --topology outputs/physical_stock_topology_v2_1.json --out outputs/boundary_coupling_v2_1.json` | JSON, `boundary-coupling-v2.1` | B-3/4 coverage/flow/backpressure gates | B-1; fixture failure stop |
| C-1/2/3 | signal reference/topology | **NEW** phase generator/config/urban model | `& $python -B scripts/derive_signal_phase_spec.py --reference outputs/signal_reference_v2_1.json --topology outputs/physical_stock_topology_v2_1.json --out outputs/signal_phase_spec_v2_1.json` | JSON, `signal-phase-spec-v2.1` | mapping 100%, unresolved 0, cycle gate | S1+A-2; failure stop |
| C-4/D-core | phase spec/action/readback | Python/PS/VBS + **NEW** validator | `& $python -B scripts/validate_signal_action_contract_v2_1.py --spec outputs/signal_phase_spec_v2_1.json --out outputs/signal_action_contract_v2_1.json` | JSON, `signal-action-v2.1`/`D-core-v2.1` | C-4/D-core timing/conflict/readback gate | C; any partial/stale actuation stop |
| E-fit | development parents 6 only | **NEW** restricted wrapper + fitter | `powershell -NoProfile -File scripts/run_calibration_fit_isolated.ps1 -DevelopmentManifest outputs/calibration_development_manifest_v2_1.json -DeniedCertificationRoot evaluation/runs/.certification_staging/wave_A -Out evaluation/calibration/physical_stock_calibration_v2_1.json` | calibration + `outputs/calibration_fit_access_log_v2_1.json`, schemas `physical-calibration-v2.1`/`access-log-v2.1` | E fit/CI/prior/support PASS; cert reads 0 | DEV-DATA+A/B; readable cert path/access-log gap stop |
| H | frozen topology/signal/calibration + production config | **NEW** production endpoint; controller/adapter integration/verifier | H command | `outputs/production_rollout_path_v2_1.json`, `production-rollout-path-v2.1` | all candidate channels use one endpoint; bypass/audit-only call 0 | A/B/C/D-core/E-fit; hash/bypass/integration test failure stop |
| I-0 | H endpoint/lever inventory + DEV-DATA states/noise | **NEW** qualification request builder | `& $python -B scripts/build_price_runtime_qualification_requests.py --production-path outputs/production_rollout_path_v2_1.json --development outputs/development_campaign_v2_1.json --spsa-out outputs/spsa_qualification_request_v2_1.json --runtime-out outputs/runtime_development_request_v2_1.json` | request JSON schemas `spsa-request-v2.1`/`runtime-request-v2.1` | expected state/schedule/coordinate/repeat count complete; cert reference 0 | H+DEV-DATA; missing/duplicate/hash mismatch stop |
| I-1 | H production endpoint + development states | **NEW** SPSA qualification runner | `& $python -B scripts/run_spsa_fd_parity.py --mode qualify-development --manifest outputs/spsa_qualification_request_v2_1.json --out outputs/spsa_fd_parity_v2_1.json` | JSON, `spsa-parity-v2.1`, frozen k/threshold hash | I-1 support/CI/sign gates | I-0/H; failure keeps SPSA OFF |
| I-3 | development scheduler/fault/hardware | controller/adapter/VBS + **NEW** benchmark | `& $python -B scripts/benchmark_decision_runtime_v2_1.py --mode development-faults --manifest outputs/runtime_development_request_v2_1.json --out outputs/runtime_scheduler_qualification_v2_1.json` | JSON, `scheduler-qualification-v2.1` | worker parity/fault/deadline mechanism PASS | I-1; failure stop |
| CERT-PREP | frozen H/source/topology/calibration/candidate/auditor/I hashes | **NEW** campaign request builder | `& $python -B scripts/build_certification_campaign.py --production-path outputs/production_rollout_path_v2_1.json --calibration evaluation/calibration/physical_stock_calibration_v2_1.json --spsa outputs/spsa_fd_parity_v2_1.json --scheduler outputs/runtime_scheduler_qualification_v2_1.json --out outputs/certification_wave_A_request_v2_1.json` | request JSON, `certification-campaign-request-v2.1`, parent/pair/twin/runtime request IDs and consumer/code hashes | parents 9; paired children N; twins 108; each demand-seed-cold/warm runtime stratum attempts `>=100`, independent runs `>=10`; runtime output hash claim 0 | H+E-fit+I-1/I-3; missing/changeable request hash stop |
| CERT-WAVE | frozen request + seeds47/59/71 | **NEW** restricted one-shot orchestrator | `powershell -NoProfile -File scripts/run_certification_wave_v2_1.ps1 -Request outputs/certification_wave_A_request_v2_1.json -StagingRoot evaluation/runs/.certification_staging/wave_A` | restricted `$campaignStage\campaign_manifest_v2_1.json`, `certification-wave-v2.1`, run/artifact hashes and ACL log | expected-to-actual linkage N/N separately for parents, paired children, twins, runtime attempts/runs; mismatch/missing/unexpected/access 0 | CERT-PREP; inferred/missing evidence or access violation retires wave |
| E-cert | frozen calibration + staged campaign manifest | **NEW** registered read-only validator | `& $python -B scripts/validate_physical_stock_calibration.py --calibration evaluation/calibration/physical_stock_calibration_v2_1.json --certification-manifest $campaignStage\campaign_manifest_v2_1.json --out $campaignStage\results\physical_stock_calibration_certification_v2_1.json` | staged JSON, `physical-calibration-certification-v2.1` | E per-stock certification gates | CERT-WAVE embargo; alternate output/mutation/failure retires wave |
| I-2 | staged campaign decision twins | **NEW** registered parity analyzer | `& $python -B scripts/analyze_production_decision_parity.py --campaign-manifest $campaignStage\campaign_manifest_v2_1.json --out $campaignStage\results\production_decision_parity_v2_1.json` | staged JSON, `decision-parity-v2.1` | I-2 108/108 status/certificate/decision gate | CERT-WAVE embargo; alternate output/unregistered read stop |
| I-4 | staged campaign runtime attempts | **NEW** registered runtime analyzer | `& $python -B scripts/analyze_decision_runtime_v2_1.py --campaign-manifest $campaignStage\campaign_manifest_v2_1.json --out $campaignStage\results\runtime_v2_1.json` | staged JSON, `runtime-v2.1` with attempts/fallback/fault rows | I-4 p95 UCL/max/fallback/fault gate | CERT-WAVE embargo; missing/censored/alternate output FAIL |
| J | staged paired requests with exact H ActionSchedule | **NEW** registered t=0 VISSIM/plant campaign runner | `& $python -B scripts/run_paired_future_campaign_v2_1.py --request $campaignStage\requests\paired_future_requests_v2_1.json --out $campaignStage\results\paired_future_manifest_v2_1.json` | staged JSON, `paired-future-v2.1`, request/run/schedule/prefix linkages | every registered branch executed; J effect/trajectory/ranking/support gates | CERT-WAVE embargo; inferred/alternate/partial cell blocks |
| D-offset-enable | native profile disposition + D-core/J/I-4 | **NEW** issuer and adapter/VBS startup guard | `& $python -B scripts/issue_offset_enable_record_v2_1.py --profile-manifest outputs/preflight_manifest_v3.json --d-core outputs/signal_action_contract_v2_1.json --paired $campaignStage\results\paired_future_manifest_v2_1.json --runtime $campaignStage\results\runtime_v2_1.json --out $campaignStage\results\offset_enable_v2_1.json` | staged JSON `offset-enable-v2.1`, exact evidence/code/profile hashes | requested=false: disabled PASS; requested=true: same-profile native gates all PASS and enabled; stale/normalized/cross/NOT_EVALUATED stays intent_only | J+I-4; invalid evidence exits nonzero for enable request |
| K | all staged exact-hash results + offset disposition | registered auditor inside campaign | `& $python -B scripts/audit_plant_fidelity.py --campaign-root $campaignStage --paired-futures $campaignStage\results\paired_future_manifest_v2_1.json --json-out $campaignStage\results\plant_fidelity_evidence_manifest_v2_1.json --markdown-out $campaignStage\results\plant_fidelity_audit_v2_1.md --strict --require-complete` | staged evidence JSON `audit-v2.1`, Markdown and promotion verdict | every required machine state PASS/non-PASS recorded; requested offset requires enable PASS | E-cert+I-2+I-4+J+offset disposition; no pre-release public write |
| CERT-RELEASE | complete staged manifest/results/K verdict | **NEW** signed atomic publisher | `& $python -B scripts/publish_certification_bundle.py --staging-root $campaignStage --bundle-out outputs/certification_wave_A_release_bundle_v2_1.json --reports-out reports` | signed exact-hash bundle `certification-release-v2.1` plus post-release report copies | staged hash closure 100%, single release 1, partial publish 0 | K complete; ACL/publish/signature failure retires wave |
| X-2 | approved native design input | **NEW** normalized builder | `& $python -B scripts/build_normalized_cycle_profile.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --cycle-sec 150 --out network/experiments/modi_eval_rw_control_150s.inpx` | separate INPX/SIG/reference/change JSON `normalized-profile-v2.1` | X hash/profile isolation gates | S1; native artifact mixing stop |

CERT-WAVE orchestrator는 E-cert/I-2/I-4/J/K/CERT-RELEASE의 등록 command를 같은 restricted identity와
`$campaignStage` 안에서 호출한다. 외부 세션에는 K 종료 후 signed bundle과 검증된 report copy만 한 번
release한다. staging read/write ACL probe, alternate output path 또는 중간 result 접근은 wave를 retire한다.

모든 machine-readable artifact는 `schema_version`, `input_hashes`, `command_version`, `status`, `reasons`,
`sample_dimensions`, `units`, `downstream_consumers`를 필수 key로 가진다. Markdown은 JSON의 rendering일 뿐
gate 정본이 아니다. matrix의 numeric-verdict section은 해당 본문의 정확한 식과 임계를 그대로 구현한다.

## 의존성과 실행 순서

```text
S0R-core source/tests/strict provenance
  -> S1 canonical signals + active program + SC12 shared-lane contract
  -> S0R compound closure

S0R compound closure -> A-1 lane-route graph -> A-2 one-stock topology
A-2 -> B projection/conservation -> B boundaries/ramps/freeway -> E-fit frozen calibration
S1 + A-2 -> C native cycles + movement/SG mapping + monitor/action schema
S1 + C -> D-core timing/readback/sign/conflict and green-only release

A-2 + B + C + D-core + E-fit
  -> production controller-independent rollout endpoint/objective

production rollout endpoint/objective
  -> I-1 exact-FD/SPSA development qualification
  -> I-3 scheduler/fault development qualification

production endpoint + E-fit + I-1/I-3 + all frozen manifests/code hashes
  -> CERT-PREP -> CERT-WAVE one-shot embargoed campaign

CERT-WAVE -> E-cert + J native paired gates + I-2 decision parity + I-4 runtime evidence
E-cert + J + I-2 + I-4 + strict provenance
  -> K strict complete staged audit
  -> CERT-RELEASE signed atomic publish -> native MPC promotion

D-core + J offset-specific effect/ranking + I-4 runtime
  -> D-offset-enable for that exact profile only
X-2 normalized experiment -> separate report only
```

downstream command는 선행 artifact의 `status=PASS`와 exact input hash를 검사한다. prose상의 완료 표시는
unlock 조건이 아니다.

## 전체 Gate 요약

| 영역 | promotion 기준 |
|---|---|
| Source/reproducibility | immutable baseline 106/106 + 모든 NEW test, strict propagation, import/tree/hash/EOL mismatch 0 |
| Signal | active program/readback mismatch 0, exact timeline, native event 오차 `<=0.5 s` |
| SC12 | 공유 stock 1개, composition 보존, lane-head mapping/profile policy 위반 0 |
| Topology | executable path 100%, unresolved/synthetic/missing/duplicate 0, order hash 동일 |
| Projection/mass | initial/substep residual `<=1e-6 veh`, clipping loss 0 |
| Calibration/certification | whole-run split overlap 0, CI/prior/per-stock gate, one-shot sealed wave PASS |
| One/multi-step dynamics | J-4의 queue/count/speed/flow/TTT 기준 전부 PASS |
| Ranking/spillback | rho `>=0.70`, pairwise `>=0.80`, 반복 부호 반전 0, F1 `>=0.80` |
| SPSA | identical endpoint, nRMSE `<=0.20`, slope `0.90..1.10`, exact sign-error CI |
| Runtime | end-to-end H=3 p95 UCL `<=30 s`, max/deadline `<=45 s`, fallback/readback/fault gate PASS |

## v2 -> v2.1 binding 요구사항 추적표

| Binding # | normative section | command/artifact | 현재 상태 |
|---:|---|---|---|
| 1 | S0R compound closure | runtime source, 106 baseline + NEW tests, strict manifest | OPEN |
| 2 | S0R/S1 source, signal, SC12 | canonical reference, shared-lane report | OPEN |
| 3 | S1 active-program/time schedule | timeline/readback artifact | OPEN |
| 4 | A/C one-stock와 movement coverage | lane graph, topology, phase spec | OPEN |
| 5 | B-2 observed speed/delay evolution | kinematics tests/report | OPEN |
| 6 | B-3/B-4 finite boundary/backpressure | boundary/ramp/freeway fixtures | OPEN |
| 7 | E disjoint calibration/certification | frozen calibration, one-shot verdict/access log | OPEN |
| 8 | C-3/D/X native cycle/offset | D-core, profile offset-enable record | OPEN |
| 9 | J replay/action/run identity | paired request/manifest and clock fixtures | OPEN |
| 10 | B/J/K quantitative dynamics | per-stratum dynamic gate report | OPEN |
| 11 | I-1/I-2 exact FD/SPSA parity | estimator and 108-twin decision artifacts | OPEN |
| 12 | I-3/I-4 scheduler/runtime | scheduler/runtime/fallback/fault artifacts | OPEN |
| 13 | 실행 계약 매트릭스 | parser/dry-run + versioned artifacts | OPEN |
| 14 | dependency/K promotion | strict complete audit/promotion record | OPEN |

## 최종 산출물

- production controller-independent rollout implementation: one-stock projection/dynamics, native signal/cycle,
  lever response, finite boundaries/backpressure와 frozen-calibration loader의 exact source/hash
- unchanged production `decide_with_info` entry를 통한 MPC integration. MPC가 action을 선택하고 plant는
  candidate future만 평가한다.
- Python/PowerShell/VBS fail-closed action writer와 source/signal/topology/calibration/SPSA/runtime/offset의
  profile-scoped startup guard
- unit/integration/paired-future/runtime/fault tests와 production code-path evidence
- `reports/plant_fidelity_audit_v2_1.md`: final strict verdict. 기존
  `reports/plant_fidelity_audit.md`는 baseline input으로 보존한다.
- `reports/plant_fidelity_evidence_manifest_v2_1.json`: 결론별 file/line/command/run ID/hash
- canonical signal, topology, projection/mass, calibration, paired-future, SPSA/runtime artifact와 promotion record

P0/P1과 J/K가 끝나기 전에는 P-Stack 성능, 기존 G6 점수나 TTT 개선률로 plant를 정당화하지 않는다.
