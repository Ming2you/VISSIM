# P-Stack 플랜트 구현 계획 v3 (경량판)

- 작성: 2026-08-07
- 대체 대상: `IMPLEMENTATION_PLAN.md` (v2.1)
- 상태: **채택됨 (2026-08-07)** — 이 문서가 활성 계획이다

---

# 후임 작업자에게 — 이 문서를 먼저 읽어라

**이 계획은 v2.1 보다 의도적으로 작다. 맥락 상실이나 누락이 아니다.**

`IMPLEMENTATION_PLAN.md`(v2.1)는 저장소에 남아 있고 앞으로도 남는다. 그러나 **활성 계획은 v3 다.**
v2.1 은 참조 문서이지 되돌아갈 목표가 아니다.

## 예상되는 실패 모드

새 세션이나 다른 에이전트가 두 문서를 나란히 놓고 보면 v2.1 이 더 철저해 보인다.
그래서 "누가 실수로 잘라냈구나" 로 읽고 원복하려는 충동이 생긴다.
**그 충동이 정확히 이 문서가 막으려는 것이다.**

v2.1 이 요구하는데 v3 에 없는 항목을 발견했다면, 그것은 **버그가 아니라 결정**이다.
결정의 근거는 아래에 있다. 근거를 읽고도 되살려야 한다고 판단되면, **사용자에게
"어떤 주장이 이것을 요구하는지" 를 제시하고 승인을 받아라.** 조용히 되살리지 마라.

## 왜 축소했는가

v2.1 은 두 가지를 동시에 추구한다.

| | 무엇 | 이 연구에 필요한가 |
|---|---|---|
| **A. 물리 충실도** | 플랜트가 VISSIM 을 옳게 투영하는가 | **필수** |
| **B. 증거 출처 관리** | 그 판정을 제3자가 원본 바이트에서 재현할 수 있는가 | 아니오 |

**A 가 필수인 이유.** 이 연구의 주장은 "내 제어기가 고정신호보다 TTT 를 X% 줄인다" 가 아니다.
Stackelberg marginal price 는 **미분의 부호와 순위**에 대한 주장이다. 총량이 10% 맞아도 기울기
부호가 뒤집히면 메커니즘 자체가 무너진다. 그리고 이미 실증됐다 —
**H=1 에서 rho 0.4378, top pairwise 0.000.** 총 통행시간 기준으로는 그럭저럭 보이던 플랜트가
기울기 순위에서는 무작위였다. 총량 지표만 보는 검증은 이 오류를 구조적으로 못 잡는다.
`spillback F1 = 1.000` 도 같은 부류였다 — 라벨이 전부 같아 정보량이 0인데 지표는 만점이었다.

**B 를 걷어낸 이유.** 불변 매니페스트, 해시 사슬, 재생 검증기, ACL 격리 staging, 서명 번들,
wave 폐기 프로토콜은 **규제 제출이나 이해상충이 있는 다자 검증**의 장치다.
학위논문·저널 심사는 이를 요구하지 않는다. 단일 연구자가 자기 실험을 돌리면서 자신을 상대로
ACL 을 거는 것은 방어 가치보다 비용이 크다.

**그리고 비용이 실제로 문제였다.** 2026-08 초 시점에서 이 저장소는 B1a 증거 배관을 여덟 라운드에
걸쳐 강화했다. 그동안 **플랜트는 실 데이터로 단 한 번도 돌지 않았다.** `outputs/` 에 토폴로지
산출물조차 없었다. 한 번도 열어 본 적 없는 문에 자물쇠를 계속 달고 있었던 것이다.
v2.2 생산자 두 개(약 3,500줄)를 더 써야 첫 실 런이 가능한 상태였고, 그 두 파일은 물리 검증에
아무것도 기여하지 않는다.

**v3 는 A 를 한 줄도 줄이지 않고 B 를 걷어낸다.**

## 무엇을 포기했는지 정확히

포기한 것은 하나다 — **"누군가 중간 산출물을 조용히 바꿨을 때 탐지된다"** 는 보장.
v3 에서도 설정과 시드로 재실행은 되지만 변조 탐지는 안 된다.

포기하지 않은 것 — 질량 보존, 정확 분할, 기울기 부호·순위 검증, H별 동적 게이트,
런타임 p95, 자기신고 PASS 금지. **논문의 주장이 서는 것은 전부 여기 있고 하나도 줄이지 않았다.**

## 되살리는 것이 옳은 경우

다음 중 하나에 해당하면 v2.1 요소를 되살려라. 그 외에는 되살리지 마라.

1. **주장이 바뀌었다.** 예를 들어 규제 제출이나 외부 감사가 목표가 되면 B 전체가 필요해진다.
2. **게이트가 경계선이다.** v3 가 줄인 표본(§간소화 항목)으로 판정이 임계 근처에 걸리면
   해당 표본만 v2.1 수준으로 복원한다. 다른 항목까지 함께 되돌리지 마라.
3. **여러 사람이 동시에 이 저장소를 수정한다.** 그때는 산출물 출처 추적이 실질적 가치를 갖는다.

"v2.1 이 더 엄격해서" 는 근거가 아니다.

## 원칙

1. **주장이 요구하는 것만 검증한다.** 기울기 부호·순위를 주장하므로 그 검증은 타협하지 않는다.
   출처 사슬은 주장의 일부가 아니다.
2. **증거는 사람이 읽을 수 있으면 된다.** JSON 산출물 + 설정 스냅샷 + 시드 기록으로 충분하다.
   불변 매니페스트, 해시 사슬, 사후 변조 탐지는 쓰지 않는다.
3. **사전 등록은 문서로 하고 봉인하지 않는다.** 임계치와 시드는 런 전에 이 문서에 적는다.
   ACL 격리, 서명 번들, wave 폐기 프로토콜은 쓰지 않는다.
4. **자기신고 PASS 는 계속 금지한다.** 이것만은 v2.1 그대로다. 지금까지 걸린 결함
   (spillback F1 인공물, 포착률 지표 혼동, `.sig` 오독)이 전부 이 부류였다.
5. **VISSIM 은 한 번에 하나만 실행한다.** 변경 없음.

## 유지되는 불변식

v2.1 의 물리·신호 불변식은 그대로 가져온다.

- 질량 보존 — stock 잔차 `<=1e-6 veh`, clipped-away mass 0
- 정확 분할 — 링크→player 귀속 100%, unresolved vehicle mass 0
- `unobservable_count = 0`, `external_source_count = 0` (잔차로 균형 맞추기 금지)
- 신호는 `(SC, SG번호)` 정확 매핑. 이름·NEMA 산술·45도 방위 fallback 을 production 에 쓰지 않는다
- 상태 어휘 `PASS / FAIL / NOT_EVALUATED / BLOCKED` 고정

---

# 단계

## N0. 토폴로지 정합과 고정 — P0

**지금 상태.** A1 차로 그래프(2,649 차로 / 커버리지 1.000), 경로 증명(339 경로 / 유량오차 1.1e-16),
A2 one-stock 토폴로지(7,275 stock / 7,418 edge / 전 게이트 0 위반)가 실 네트워크에서 컴파일되고 PASS 한다.

### N0-1. v2.2 필수 역할 제거

`plant/src/vissim_strict/run_evidence.py:94-95` 의 닫힌 필수 소스 역할 집합에
`post_run_artifact_producer`(`build_run_artifact_manifest_v2_2.py`)와
`live_replay_builder`(`build_projection_live_evidence_v2_2.py`)가 들어 있다(`:108-109` 경로 맵도 같다).
**v3 는 이 두 생산자를 만들지 않으므로 preflight 가 영원히 FAIL 한다.**

두 역할을 필수 집합에서 뺀다. 닫힌 역할 우주를 검증하는 테스트가 함께 바뀐다.

**PASS.** `build_preflight_manifest.py` 산출 `status=PASS`, reasons 0.
`RW_PYTHON_EXE` 를 정본 파이썬으로 고정한 상태에서 `verify_runtime_source.py` 도 PASS.

### N0-2. 커넥터 진입 엣지 위치 정합

컴파일러/검증기 불일치 35건을 닫는다. 커넥터 진입 엣지의 `from_position_m` 이
`.inpx` 저장값(6자리 반올림)이고 stock 경계는 좌표 계산값(전정밀도)이라 정확 일치에서 갈린다.
차이는 최대 4.96e-07 m 다.

수정 방향은 **컴파일러**다. 엣지의 `from_position_m` 을 자기가 떠나는 stock 의 경계값으로 맞춘다.
원시 커넥터 위치는 A1 그래프에 출처로 남는다. 검증기의 정확 일치 규율은 건드리지 않는다.

**고정 방법.** `topology_approval_v2_1.json` 승인 아티팩트를 만들지 않는다. 대신
`outputs/physical_stock_topology_v2_1.json` 의 SHA-256 한 줄을 `context-notes.md` 에 적고
이후 모든 실행이 그 값을 참조한다.

**산출물은 커밋하지 않는다.** 그래프 2.7 MB + 경로증명 8.9 MB + 토폴로지 30.7 MB = 42 MB 이고,
git 은 모든 판을 영구 보관하므로 재생성할 때마다 같은 크기가 이력에 쌓인다.
셋 다 `.inpx` 와 입력 3개(`link_player_assignment` / `intersection_adjacency8` /
`urban_storage_capacity`)에서 아래 명령으로 결정적으로 재생성된다. **해시가 정본이다.**

```powershell
$py = $env:RW_PYTHON_EXE
$inpx = "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
& $py -B scripts/build_vissim_lane_graph.py --inpx $inpx --output outputs/lane_route_graph_v2_1.json
& $py -B scripts/resolve_lane_routes.py --inpx $inpx --graph outputs/lane_route_graph_v2_1.json --output outputs/lane_route_proofs_v2_1.json
& $py -B scripts/compile_physical_stock_topology.py --graph outputs/lane_route_graph_v2_1.json --routes outputs/lane_route_proofs_v2_1.json --ownership outputs/link_player_assignment_20260805.json --adjacency outputs/intersection_adjacency8_20260805.json --capacity outputs/urban_storage_capacity_20260805.json --output outputs/physical_stock_topology_v2_1.json
```

**PASS.** `validate_physical_stock_topology` 구조 오류 0. 실네트워크 테스트 23/23.
재생성 결과의 SHA-256 이 `context-notes.md` 기록과 일치.

## N1. 차량단위 초기상태 투영 — P0

**목적.** VISSIM 을 한 순간 정지시켜 차량을 전부 긁고, A2 stock 위에 초기 상태를 확정한다.
MPC 롤아웃의 초기 조건이다.

**남기는 것.**
- `(run_id, sim_sec, veh_no)` 스냅샷 신원, 한 스냅샷 안 `veh_no` 중복 0
- 원시 `No/Lane/Pos/Speed` → A2 stock 배정, 배정 실패 0
- 루트 카운트 항등식 — `total_vehicles`, `stopped_vehicles` 가 records 에서 재유도한 값과 일치
- 링크별 카운트/정지 맵이 records 와 일치
- `unobservable_count = 0`, `external_source_count = 0`

**걷어내는 것.** 불변 run manifest, capture evidence sidecar, projection reference,
timing receipt, 이들의 해시 결속, `run-artifact-manifest-v2.2`, `projection-live-replay-v2.2`,
required-mode 워치독 경로.

**대체.** 스냅샷마다 `state_XXXXXX.json` 하나와 그 옆의 `projection_XXXXXX.json` 하나.
런 디렉터리에 `run_config.json`(설정 전문 + 시드 + VISSIM 버전 + git commit) 하나.

**실행.** 3600초 런 1회, 제어주기 60초 → 스냅샷 61회.

**PASS.** 61/61 스냅샷에서 배정 100%, 잔차 `<=1e-6 veh`, 위 항등식 전부 성립.

## N2. substep 질량 장부 — P0

v2.1 B-1 의 후반부. 스냅샷 사이 차량 이동을 복식부기로 기록한다.

```
closing_i = opening_i + accepted_external_i − sink_i + Σ_j F[j,i] − Σ_k F[i,k]
```

- 모든 내부 이동은 `transfer_id` 하나 · 출발 차변 하나 · 도착 대변 하나
- 출발/도착 transfer 다중집합 동일
- **post-update clipping 제거** — 받는 쪽·보내는 쪽 제약으로 흐름을 제한하고 거부량은 typed source stock 에 남긴다
- 단일 `TrafficState.total_physical_vehicles()`

**PASS.** stock/전역 잔차 `<=1e-6 veh`, transfer 다중집합 불일치 0, 중복/누락 transfer ID 0,
clipped-away mass 0, 강제 분기/합류/수용포화 fixture 에서 전 차량 보존.

## N3. 관측 확장 — P0/P1

### N3-1. 속도·큐꼬리·통행지체
VBS 와 어댑터가 이미 내보내는 `link_speeds_kph` 와 정지 대수를 lane-group 운동학에 연결한다.
관측 속도가 있으면 전역 평균속도를 쓰지 않는다. 0 속도는 0 지체가 아니다.
FIFO 주행 버퍼와 정지선 서비스를 분리한다.

**PASS.** 통행시간 중앙값 `<=5 s`, p95 `<=15 s`, 큐꼬리 MAE `<=20 m`, 동일 substep 도착 0.

### N3-2. 출구와 목적함수
출구 226개를 유한 `boundary_out` stock 으로 만든다. 목적함수 포함/제외는 **같은 물리 trace 에
다른 가중치만** 적용한다.

**PASS.** 출구 커버리지 226/226, 잔차 `<=1e-6`, 목적함수 모드 간 state/flow trace 동일,
목적함수 차이가 기록된 경계 기여분과 `<=1e-9` 일치.

### N3-3. 램프·유출램프·고속도로
물리적으로 독립인 커넥터/차로 큐를 합치지 않는다. **스칼라 램프 상한 fallback 을 production 에서 금지**하고
stock 별 상한을 쓴다. 합류의 모든 유입은 우선순위 규칙이 명시된 하나의 하류 수용 예산을 공유한다.
SC1004 역할 재분류(F측 인터체인지)를 포함한다.

**PASS.** 램프 커넥터 누락/중복 0, 합류/분기 재배치 0, 그룹 유량과 물리 유량 합 차이
`<=1e-9 veh/substep`, 고속도로 구간 gap/overlap 0 m, production fallback 0.

## N4. N현시 신호 — P0

### N4-1. SC별 고유 주기 (v2.1 X-1)
원본 network/SIG 를 바꾸지 않고 SC별 실제 주기를 `NetworkConfig` 에 넣는다. N4-2 의 선행조건이다.
150초 정규화 실험은 **이 계획에서 제외**한다(별도 과제).

### N4-2. movement / SG 매핑
`head lane → 커넥터 → 목적지 stock → movement` 추적. 키는 `(SC, SG번호)`.
정확 매핑이 없는 차량 질량은 항상 unresolved 이며 각도 fallback 으로 PASS 처리하지 않는다.
공용 차로(SC12)는 stock 하나와 movement 조합을 쓴다.

**PASS.** 정확 커버리지 100%, unresolved vehicle mass 0.

### N4-3. N현시 녹색분율
`_phase_green_fraction` 이 원시 타임라인의 부분 step 녹색을 적분한다. clearance 는 실제 SIG 를 쓴다.
**기존 N=2 경로는 bit-identical 유지.**

**PASS.** N=2 경로 bit-identical, SC별 주기 재구성 오차 0, native production 에서 scalar-cycle fallback 0.

### N4-4. monitor 26개 고정 타임라인
monitor node 를 "항상 녹색" 이 아니라 "고정 스케줄, 제어 불가" 로 재생한다.

**PASS.** monitor always-green movement 0, 영구적색 녹색분율 0, monitor 큐/저장이 물리적으로 갱신됨.

### N4-5. action 스키마 fail-closed
N현시 action 은 stage duration 또는 tangent 좌표를 가진다. 모델 state·action CSV·VBS config·readback 이
불일치하면 적용하지 않는다.

**PASS.** 부분 적용 0, request/readback 불일치 0, 공용차로 SG 제약 위반 0, 충돌 SG 동시녹색 0,
최소녹색/clearance 위반 0.

### N4-6. 신호 timing oracle (D-core) — P1

**v2.1 D 를 그대로 유지한다.** 이것은 증거 출처 관리가 아니라 **액추에이션 충실도**다.
명령한 신호가 VISSIM 에 실제로 그 시각에 들어갔는지를 검증한다. 여기가 틀리면 아래 모든
동적 검증이 엉뚱한 것을 측정한다.

`D-core` 가 검증하는 것.

- 예상 전이 대 **즉시 및 step 이후 COM readback**
- source offset 과 command lag, **양의 lag 부호**
- 주기 경계 처리와 SC별 고유 주기 (N4-1 의존)
- 충돌 SG 와 최소녹색

**green-only production release 는 D-core 뒤에 온다.** 즉 D-core 가 PASS 하기 전에는
녹색 레버조차 production 으로 내보내지 않는다.

**PASS.** 전이 시각 오차 `<=0.5 s`, request/readback 불일치 0, 명령 지연 부호 오류 0,
충돌 SG 동시녹색 0, 최소녹색/clearance 위반 0, 주기 wrap 경계 오류 0.

### N4-7. offset 승격 잠금 (D-offset-enable) — P1

offset 은 **삼중 잠금**이다. 하나라도 빠지면 production writer 를 열지 않는다.

```
D-offset-enable = D-core(같은 신호 profile + 같은 topology SHA-256)
                ∧ N9 offset 효과·순위 게이트
                ∧ N8-4 런타임 게이트
```

- D-core PASS 전까지 production writer 는 **`intent_only`** 다. 의도만 기록하고 COM 에 쓰지 않는다.
- D-core PASS 후에도 **격리된 시험 harness 의 test-only writer** 만 강제 offset arm 을 낼 수 있다.
  production writer 는 삼중 잠금이 모두 PASS 할 때 열린다.
- 승격되지 않은 profile 의 nonzero offset 기록은 **fail-closed 로 거부**한다.
- 주기 정규화 실험(150초 등)을 별도로 수행하더라도 그 결과는 **native offset 을 활성화하지 못한다.**

**PASS.** 미승격 profile 의 production offset write 0, `intent_only` 우회 0,
test-only writer 가 production 경로에 도달한 경우 0.

## N5. 개발 데이터와 잡음 바닥 — P0

VISSIM 을 순차 실행해 개발용 부모 런을 만든다. anchor `900/1500/2100/2700` 의 상태를 보존한다.

**부모 런 (v2.1 의 18개에서 축소)**

| 용도 | demand | seed | 개수 |
|---|---|---|---|
| training | 0.75, 1.0 | 13, 29 | 4 |
| congested | 1.25 | 13, 29 | 2 |
| holdout | 0.75, 1.0, 1.25 | 47 | 3 |

**총 9개.** SPSA 전용 seed 31 은 training 과 공유한다(별도 3개를 만들지 않는다).
인증 wave 3개 시드(47/59/71) 대신 holdout 단일 시드(47)를 쓴다.

**잡음 바닥.** 각 부모-anchor 에서 독립 `t=0` base replay 를 **20회** 실행해
`eps_J = max(1e-6 veh·h, max_{i,j}|J_base_i − J_base_j|)` 를 동결한다. **이 부분은 축소하지 않는다.**
이후 모든 "효과가 실재하는가" 판정의 기준선이기 때문이다.

**PASS.** 부모 9/9, anchor 완비, 누락/중복 0, base replay 부모-anchor 당 `>=20`,
training/holdout 시드 중복 0.

## N6. 캘리브레이션 — P1

`evaluation/calibration/physical_stock_calibration_v3.json` 에 run ID/split, 추정기, 표본 수,
차량 길이+정지간격 prior, 적합값, run-cluster bootstrap 95% CI, jam density, 램프/출구 저장·방류를 기록한다.

- jam density 는 `speed <= 3 kph`, 정지분율 `>= 0.5` 인 포화 lane-group 에서 robust fit
- 큐꼬리 관측이 있으면 고정 분율(0.35/0.50) 대신 관측 분해를 쓴다
- **적합은 training 시드에서만.** holdout 시드는 적합·임계선택·후보교체에 쓰지 않는다

**PASS.** split 중복 0, 포화 독립 lane-group `>=30`, 표본 `>=200`,
jam CI 반폭 `<= 추정값의 10%`, geometry prior 차이 `<=15%`, training 시드별 적합 차이 `<=15%`,
fallback 분율 사용 `<=10%`.

## N7. production MPC rollout endpoint — P0

순수 함수 `evaluate_price_point(state, previous, forecast, action_schedule, objective_spec)` 를 만들고
`stackelberg_mpc.py`, `stackelberg_wu_metered.py`, 어댑터의 실제 `decide_with_info` 경로에 통합한다.

- MPC 가 후보 생성·목적함수 비교·action 선택을 소유
- endpoint 는 상태 투영·제어독립 동역학·제약·레버 반응·목적함수 성분만 평가
- exact FD, SPSA, no-control replay 가 **전부 같은 endpoint 와 동결 파라미터**를 사용

**PASS.** 채널 커버리지 100%, endpoint 호출 수 = 후보 평가 수, 우회 호출 0,
one-step / H=3 통합 테스트 PASS.

## N8. marginal price 와 런타임 — P0

### N8-1. exact FD 대 SPSA 자격심사
FD 와 SPSA 가 하나의 production endpoint 를 호출한다. endpoint control, 목적함수 성분, feasibility,
종단 상태, 실현 섭동 폭이 동일하지 않으면 비교 자체가 FAIL 이다.

- `eps_g = 2·eps_J / realized_span` 으로 좌표 잡음 환산. 목적함수 단위 잡음을 기울기와 직접 비교하지 않는다
- 중앙차분을 `h` 와 `h/2` 에서 비교. `|g_h − g_h2| <= max(eps_g, 0.10·max(|g_h2|, eps_g))`
- 사전 등록 전진폭 — 녹색 `6 s`, VSL `10 km/h`, offset `C/8`, 램프미터 `max(300 veh/h, 0.20·capacity)`
- SPSA 쌍 개수 `k ∈ {8,16,32,64}`, state 당 독립 방향 batch **20개** (v2.1 의 30에서 축소)
- 좌표는 `|g_fd|·realized_span >= max(5·eps_J, 0.005·max(|J0|,1))` 일 때만 material

**PASS.** nRMSE 상한 `<=0.20`, 기울기 CI 전체 `0.90..1.10`, `|intercept| <= median(eps_g)`,
재료 부호 반전 0. 부호 오류 Clopper-Pearson 95% 상한 전체 `<=0.05` (재료 비교 `>=59`),
채널별 `<=0.10` (`>=29`).

### N8-2. 결정 동등성
기울기만 비교하지 않는다. holdout 상태 **18개** × 방향 seed 3개 = **54 twin** 에서
후보집합·순위·선택 action·제약·spillback 가드·미터 방류를 FD 와 SPSA 사이에 비교한다.
(v2.1 은 36 상태 × 3 = 108 twin.)

**PASS.** 상태·feasibility·안전 인증서·fallback 등급·리더 후보 54/54 정확 일치.
명령은 정확 일치 또는 선언된 양자화 1단계 이내, exact-FD 재채점 regret `< max(2·eps_J, 0.5%·|J_FD|)`.

### N8-3. 통합 rollout 스케줄러
녹색·미터·VSL·offset 의 독립 rollout 을 하나의 deadline-aware 스케줄러에 넣는다.
Windows spawn-safe worker, task timeout/cancel, 결정적 축약.

**PASS.** workers 0/1/2/5 에서 후보 목적함수/가격 차이 `<=1e-9`, 선택 action 정확 일치,
병렬 예외 뒤 조용한 직렬 재실행 0.

### N8-4. 런타임 계약
두 시계를 기록한다 — `decide_with_info` 내부 시간과, anchor 관측 스캔부터 검증된 COM readback 까지의
end-to-end. **운영 게이트는 end-to-end 만** 본다.

```
30초  목표 초과 이벤트
42초  어댑터/워커 프로세스만 종료 (VISSIM 은 paused/alive 유지)
 3초  fallback 생성·검증·적용·readback 예약
45초  최대
```

표본은 `demand × cold/warm` stratum 마다 **최소 50 attempt, 독립 VISSIM 런 최소 5개**
(v2.1 은 100 attempt / 10 런).

**PASS.** stratum 별 p95 `<=30 s`, 관측 최대 `<=45 s`, controller fallback `<5%`, timeout `<1%`,
조용한 fallback / 낡은 action / readback 실패 / 고아 워커 0.

## N9. 짝지은 VISSIM 검증 — P1

### N9-1. replay 신원
VISSIM 스냅샷 복원을 믿지 않고 모든 branch 를 `t=0` 부터 재실행한다.
플랜트와 VISSIM 이 동일한 schedule entry, 활성화 경계, 반열린 구간 `[start, end)` 를 쓴다.

런 키는 v2.1 의 21필드에서 축소한다.

```
(experiment_id, inpx_hash, topology_sha256, calibration_version,
 controller_version, demand, seed, anchor_sec, H, channel, lever_id,
 action_payload_hash, replicate)
```

### N9-2. 실험 행렬
demand `0.75/1.0/1.25`, 런 3,600초, warm-up 900초, anchor `900/1500/2100/2700`,
H `1/3/5/10/15`, 제어주기 60초. 기본은 레버 하나씩 low/base/high.

### N9-3. 집계
VISSIM 1초 관측을 보존하고 60초로 집계한다. `ΔJ(action) = J(action) − J(base)` 를 같은 prefix 에서 계산한다.
반복은 잡음만 추정하고 표본 수를 늘리지 않는다.
controlled 15 / monitor 26 / midblock 9 / boundary / ramp / freeway 를 분리한다.

### N9-4. 합격 게이트
**H=1 은 독립 게이트다.** 다른 H 로 구제하지 않는다.

| H | 게이트 |
|---:|---|
| 1 | 도시부 큐/저장 NMAE `<=15%`; 통행 중앙값/p95 `<=5/15 s`; 꼬리 MAE `<=20 m`; 속도 MAPE `<=10%`; count MAE `<=max(5 veh,10%)`; GEH `<=5` 인 행 `>=85%`; TTT APE `<=10%` |
| 3 | TTT APE `<=12%`; 종단 NMAE `<=20%`; 속도 MAPE `<=15%` |
| 5 | TTT APE `<=15%`; 종단 NMAE `<=20%` |
| 10 | TTT APE `<=18%`; 종단 NMAE `<=35%`; nonfinite/음수/clipping/질량 실패 0 |
| 15 | TTT APE `<=20%`; 종단 NMAE `<=35%` |

레버 효과는 `demand × H × 채널` 마다 재료 비교 **16개 이상** (v2.1 은 seed 축을 포함해 24).
`effect_NMAE <= 0.25`, signed bias `<=0.15`, **재료 부호 일치 100%**.

Spearman `>=0.70`, top pairwise `>=0.80` 을 점추정과 **부트스트랩 95% 하한 둘 다** 통과.

**spillback.** `(run_id, anchor, physical_stock_id)` episode 당 positive/negative 각 최대 하나로 센다.
혼잡 `demand × H × 채널` 마다 독립 positive/negative 각 **10개** (v2.1 은 20), F1 `>=0.80`,
발생/해소 중앙값 오차 `<=60 s`, p90 `<=120 s`. positive 가 5개 미만이면 spillback 게이트만 `NOT_EVALUATED`.

## N10. 감사와 승격 — P1

`audit_plant_fidelity.py` 에 신호·토폴로지·투영·질량·캘리브레이션·짝동역학·순위·런타임 게이트를 추가한다.
출처 게이트(매니페스트 해시 사슬, 아티팩트 변조 탐지)는 **추가하지 않는다.**

승격은 세 demand 의 holdout 시드에서 필수 게이트가 PASS 일 때만 가능하다.
저수요라고 spillback 외 지표를 면제하지 않는다.

**결함 수정 루프**

1. 실패 아티팩트와 최소 재현 테스트를 먼저 고정한다
2. 결함 하나를 수정하고 관련 단위 게이트를 실행한다
3. **단계 경계에서만** 독립 검토를 받는다 (v2.1 은 수정 라운드마다)
4. development 셀만 재실행한다
5. 마지막에 전체 회귀와 whole-branch 검토

동일 load-bearing finding 이 **3회** fix/review 에도 남으면 BLOCKED 로 판정한다 (v2.1 은 5회).

---

# 사전 등록 (런 전에 여기 적는다)

- **임계치** — 위 각 단계의 PASS 조건. 런 후 수정 금지
- **시드** — training `13, 29` / holdout `47`. holdout 은 N6 적합과 N8/N9 임계선택에 쓰지 않는다
- **전진폭** — 녹색 6 s, VSL 10 km/h, offset C/8, 램프미터 max(300 veh/h, 0.20·capacity)
- **H 축** — `1/3/5/10/15`. H=1 독립 게이트
- **잡음 바닥** — N5 의 20회 base replay 로 동결. 이후 재추정 금지

봉인·서명·ACL 격리는 하지 않는다. 이 문서의 git 이력이 사전 등록 증거다.

# 의존 순서

```
N0 ─ N1 ─ N2 ─ N3 ──────────────┐
N4-1 ─ N4-2..5 ─ N4-6(D-core) ──┼─ N7 ─ N8 ─ N9 ─ N10
N5 ─ N6 ────────────────────────┘                │
                                                 └─ N4-7 (offset 승격)
```

- N5(개발 데이터)는 N1~N4 가 끝나야 의미 있는 상태를 만든다. N6 은 N5 에 의존한다.
- N7 은 N2/N3/N4 의 플랜트를 요구한다. N8 은 N5 의 `eps_J` 와 N7 의 endpoint 를 요구한다.
- **N4-6(D-core)은 N7 앞에 온다.** 액추에이션이 검증되지 않은 상태로 production endpoint 를
  통합하면 이후 모든 동적 측정이 오염된다.
- **N4-7(offset 승격)은 마지막이다.** D-core · N9 효과/순위 · N8-4 런타임이 모두 PASS 해야 열린다.
  그전까지 offset writer 는 `intent_only` 로 남는다.

# 이 계획에서 다루지 않는 것

의도적으로 범위 밖이며, 필요해지면 **별도 과제**로 세운다.

- **150초 주기 정규화 실험** — 별도 `.inpx`/SIG/감사를 요구하고, 계획 스스로 그 결과가
  native plant·offset·controller 를 승격하지 못한다고 규정한다. 승격 경로에 기여하지 않는다.
- **증거 출처 관리 일체** — 서두의 표 B 항목 전부. 되살리는 조건은 서두에 적혀 있다.
