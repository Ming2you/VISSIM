# N4-0 작업2 — 새 `.sig` 배선 · 신호 체인 재생성 · 주기 동일성

작업 1 이 쓴 dual-ring `.sig` 15개를 `.inpx` 에 물리고, 신호 체인을 통째로 재생성한 뒤,
모델 주기 항등식을 4현시 계약으로 옮긴 결과다. 실행한 명령과 실측만 적는다.

## 1. 배선 — 새 `.inpx`

생산자 `scripts/rewire_inpx_signal_programs.py`. 원본은 읽기만 하고 새 파일로 쓴다
(생산자 자신이 같은 경로를 `RewireError` 로 거부한다).

    network/real_world_gaepo_modi/modi_eval_rw_control_n4dr150_20260812.inpx

`ET` 왕복이 아니라 **바이트 수술**이다. `<signalController ...>` 시작 태그를 찾아 그 안의
`supplyFile2` 값 하나만 바꾼다. 그래서 파급을 diff 로 증명할 수 있다.

| 항목 | 값 |
| --- | --- |
| 다시 쓴 컨트롤러 | 15 / 50 |
| 줄 단위 diff | 15 줄 (그 줄들의 차이는 `_n4dr150` 삽입뿐) |
| 바이트 | 3,029,864 -> 3,029,984 (+120 = 15 x 8자) |
| 원본 sha256 | `f3ce390f281c2bd6…` — **불변** |
| 새 sha256 | `37f1cc1fcafbec5a…` |

SC 번호와 `.sig` 파일명 끝자리가 다른 넷(5·6·11·12)이 여기서 갈린다.

| SC | 1 | 5 | 6 | 11 | 12 | 101 | 105 | 107 | 108 | 109 | 1001~1005 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `.sig` stem | bed1 | bed7 | bed9 | bed3 | bed5 | bed101 | bed105 | bed107 | bed108 | bed109 | bed1001~1005 |

## 2. 감사 `canonical_topology` 파급

토폴로지는 빌드 산출물이라(`scripts/build_canonical_topology.py`) 새 망에서 다시 컴파일했다 —
`outputs/canonical_topology_n4dr150_20260812.json`.

옛 토폴로지와 top-level 키를 전수 대조하면 **다섯 개만** 다르다.

    schedules · signal_controllers · signal_reference · source · topology_hash

`links` · `connectors` · `movements` · `routes` · `observation_operators` · `vehicle_inputs` 는
바이트 동일하다. 개수도 그대로다 — links 448 · cells 5,844 · SC 50 · SG 440.

`schedules.fixed` 가 `.sig` 를 읽어 들고 있어서, 제어 15 SC 의 `cycle_length_sec` 가 여기서 바뀐다.

    이전  160·160·160·150·140·160·150·170·170·170·150·150·150·150·150
    이후  전부 150.0

## 3. 신호 체인 재생성

세 생산자를 새 망·새 토폴로지 위에서 다시 돌렸다(v3 정본은 덮어쓰지 않았다).

    derive_signal_group_timing      -> outputs/signal_group_timing_n4dr150_20260812.json
    derive_movement_signal_group_map-> outputs/movement_signal_group_map_n4dr150_20260812.json
    derive_signal_group_actuation_plan (--out-vbs)
                                    -> outputs/signal_group_actuation_plan_n4dr150_20260812.json
                                       evaluation/generated/signal_group_actuation_plan_n4dr150_20260812.vbs

| 생산자 | 결과 |
| --- | --- |
| timing | status=PASS · controllers 15 · groups 136 · unresolved 0 · **native cycles = [150.0]** |
| movement map | status=PASS · movements 698 · resolved 416 · unresolved 282 (전부 `synthetic_boundary_leg`) |
| actuation plan | status=PASS · controllers 15 · groups 136 · windows 118 · uncovered 0 · **never_green 20** · violations 0 |

never_green 20 = 작업 1 의 영구적색 20개(SC5 12 · SC107 2 · SC108 2 · SC109 4)와 정확히 일치한다.

계획의 현시 녹색 전/후 (초). p1 은 minor 배리어, p2 는 major 배리어다.

| SC | native 주기 | p1 | p2 | 창 |
| ---: | --- | --- | --- | --- |
| 1 | 160 → 150 | 83 → 75 | 68 → 63 | 8 |
| 5 | 160 → 150 | 104 → 97 | 102 → 101 | 14 |
| 6 | 160 → 150 | 69 → 64 | 82 → 74 | 8 |
| 11 | 150 → 150 | 71 → 71 | 67 → 67 | 8 |
| 12 | 140 → 150 | 69 → 74 | 59 → 64 | 8 |
| 101 | 160 → 150 | 83 → 75 | 71 → 63 | 8 |
| 105 | 150 → 150 | 69 → 69 | 69 → 69 | 8 |
| 107 | 170 → 150 | 28 → 25 | 136 → 116 | 6 |
| 108 | 170 → 150 | 35 → 31 | 129 → 110 | 6 |
| 109 | 170 → 150 | 20 → 20 | 144 → 121 | 4 |
| 1001 | 150 → 150 | 141 → 138 | 69 → 69 | 8 |
| 1002·1003·1005 | 150 → 150 | 72 → 69 | 69 → 69 | 8 |
| 1004 | 150 → 150 | 141 → 138 | 69 → 69 | 8 |

## 4. 현시 수 N 은 산출물에 **반영되지 않았다** — 확인된 사실

계획의 `phase_signal_groups` 는 재생성 뒤에도 **p1/p2 두 개**다. p3·p4 는 15 SC 전부에서 비어 있다.

    이전  {p1: n, p2: m, p3: 0, p4: 0}
    이후  {p1: n, p2: m, p3: 0, p4: 0}   ← 글자 하나 안 바뀜

원인은 `.sig` 가 아니라 **movement 의 `phase` 문자열**이다.
`derive_movement_signal_group_map.derive_signal_group_phase` 는 `(SC,SG) -> 현시` 를
그 SG 의 신호두가 붙은 링크를 origin 으로 잡는 movement 들의 `phase` 에서 받아온다
(폴백은 SG 이름 규칙 `_phase_from_signal_group_name`, EB/WB→p2 · NB/SB→p1). 그 `phase` 를
만드는 것은 모델 config 이고, 모델이 2현시인 한 값은 `SC{n}_p1` / `_p2` 두 개뿐이다.

모델이 2현시인 이유는 `vendor/NumSim-mine` 스냅샷(upstream `e4bf4d01`)이 2현시이기 때문이다.
컨트롤러 여섯 곳이 리터럴로 두 현시를 쓴다.

    distributed_coordinator.py:1255-1256   green_times[f"{signal}_p1"] / _p2 = eff - p1
    structured_grid.py:42-43               같음
    rollout_endpoint.py:135-136            같음
    centralized_mpc.py:179-180             같음
    wu_faithful_follower.py:4476           같음
    distributed_coordinator.py:3066-3067   같음

상류 `NumSim-mine` 은 이미 4현시다(`MODEL_PHASES = (p1,p2,p3,p4)`, `cycle_length 150`,
`lost_time 12`, `green_max 78`). **vendor 재스냅샷이 이 작업의 범위 밖**이므로 계획을
4현시로 유도할 수 없다.

## 5. 주기 동일성 — 무엇을 바꿨고 무엇이 남았나

### 바꾼 것

`evaluation/controllers/plant_cycle.py` 에서 전이 수 리터럴 `2` 를 지웠다.

    이전  RUNNER_CLEARANCE_TRANSITIONS_PER_CYCLE = 2
          plant_lost_time_sec()          -> 6.0 고정
          plant_cycle_sec(p1, p2)        -> 두 축만

    이후  plant_lost_time_sec(N)         -> N x 3   (N=4 → 12, N=3 → 9, N=2 → 6)
          plant_cycle_sec({p1..p4})      -> 러너 `SignalCycleFromPhases` 와 같은 식
          plan_live_phase_counts(plan)   -> SC별 N (러너의 `LivePhaseCount`)
          model_effective_green_sec(net, N) -> cycle - N x 3
          green_box_residual_sec(net, N) -> green_min x (N-1) + green_max - eff

러너 `run_real_world_stackelberg_controller.vbs:800` 은 **이미** 현시 수만큼 물고 있었다
(`PhaseGreenSum + LivePhaseCount x (AMBER+ALL_RED)`). 2 를 박아 두고 있던 것은 이쪽이다.

`scripts/generate_real_world_distributed_players.green_budget_contract` 도 같이 옮겼다.

    green_max = cycle - lost - (N-1) x green_min     (구: cycle - lost - green_min)
    cycle_length 를 계약에 추가                       (vendor 120 대 상류 150 갈림 제거)

config 는 원본을 덮어쓰지 않고 새로 만들었다.

    evaluation/configs/real_world_modi_pstack_distributed_core15n4dr150_20260812.json
        extends real_world_modi_pstack_distributed_core15n41_20260805.json
        network { cycle_length 150.0, lost_time 12.0, green_max 78.0 }

부모와 나란히 세워 대조하면 `NetworkConfig` 필드 중 다른 것은 정확히 그 셋뿐이다
(`test_the_budget_config_only_moves_the_four_green_budget_scalars`). 승격 후보 둘
(`…core15n41gated/ungated_20260811.json`)도 같은 값으로 맞췄다.

    이전  cycle 120 · lost 10 · green_min 20 · green_max 90 · eff 110
    이후  cycle 150 · lost 12 · green_min 20 · green_max 78 · eff 138
          20 x 3 + 78 == 138 ✓   138 + 12 == 150 ✓   쓰기 클램프 [5, 90] 안 ✓

### 남은 것 — `PlanPhaseCountTests` 가 빨간불로 든다

모델은 4현시가 됐는데 계획이 2현시라, 러너가 합성하는 주기는 150 이 아니라 **144** 다.

    모델   138 + 4 x 3 = 150
    플랜트 138 + 2 x 3 = 144        15 SC 전부에서 gap = -6.0 s

`test_every_controlled_sc_replays_the_model_cycle` 이 SC별 N 으로 재서 그 −6.0 을 15개 다
찍어 낸다. 이 검사가 4절의 vendor 벽에 그대로 걸려 있다.

**그리고 계획이 4현시가 되어도 3 SC 는 남는다.** 실 `.sig` 에서 SC107·108·109 는 N=3 이라
예산이 141 s 여야 150 이 나오는데, 모델의 `effective_green_total` 은 스칼라 138 하나다.

    N=4  eff 138 + 12 = 150 ✓
    N=3  eff 138 +  9 = 147 ✗   (141 + 9 = 150 이어야 한다)

스칼라 하나로 138 과 141 을 같이 담을 수 없다. `lost_time_by_signal` 같은 상류 필드가
있어야 닫힌다 — `cycle_length_by_signal` 로는 안 된다(그쪽은 분모만 바꾸고 예산은 못 바꾼다).

## 6. 감사 게이트 — 전/후

임시 경로에 냈다. `reports/` 정본은 안 건드렸다.

    outputs/audit_n4dr150_20260812/before_manifest.json · before_summary.md
    outputs/audit_n4dr150_20260812/after_manifest.json  · after_summary.md

| | PASS | FAIL | BLOCKED | NOT_EVALUATED |
| --- | ---: | ---: | ---: | ---: |
| 전 (원본 망 · v3 산출물) | 12 | 0 | 0 | 16 |
| 후 (새 망 · 새 산출물) | 11 | 0 | 0 | 17 |

게이트 28개를 전수 대조하면 **바뀐 것은 하나뿐**이다.

    vissim_error_log   PASS -> NOT_EVALUATED   "VISSIM .err file was not available"

새 `.inpx` 를 VISSIM 에서 한 번도 안 열었기 때문이다(`<network>.err` 이 없다). 충실도
후퇴가 아니라 **미검증**이다. `canonical_topology` 는 전·후 모두 PASS 이고 개수도 같다 —
`inpx_sha256` 이 새 망과 맞는 토폴로지를 줬으므로 배선이 감사를 깨지 않는다.

## 7. 테스트

| 스위트 | 전 | 후 |
| --- | --- | --- |
| `tests/` | 189 tests, FAILED (failures=16) | **197 tests, FAILED (failures=12)** |
| `scripts/tests/` | OK | **626 tests, OK** |
| `plant/tests` (cwd=plant, PYTHONPATH=repo) | 132 OK | **132 tests, OK** |
| `NumSim-mine` 4현시·예산 | — | **29 tests, OK** (`test_four_phase_model`, `test_cycle_green_budget_accounting`) |

`tests/` 잔여 12건의 내역.

    test_demand_contract                 7   수요 0.862배 — 이번 범위 밖 (안 늘렸다)
    test_native_phase_axis_composition   4   축 방위 — 4절·8절 참조
    test_model_plant_cycle_identity      1   PlanPhaseCountTests (5절). 닫힌 5건을 대신한다

## 8. 축 방위 4건은 **소멸하지 않았다** — 실측

"4현시가 되면 축 개념이 없어진다" 를 재생성 산출물로 확인했다. 안 없어졌다.

    v3        SC1001 p1 {2,3,4,5,7,8}  p2 {1,6}
    n4dr150   SC1001 p1 {2,3,4,5,7,8}  p2 {1,6}     ← 동일
    (SC1004 도 같다)

4절의 이유 그대로다 — 축이 사라지려면 movement `phase` 가 4값이어야 하고, 그건 vendor 가
2현시인 동안 불가능하다. 그래서 네 건을 지우지 않고 두되, 무엇이 막고 있는지를 테스트
docstring 에 실측으로 적었다.

대신 새 프로그램 위에서 같은 축을 다시 재는 검사를 넣었다(`ForwardDualRingAxisTests`).

| | 주기 | p1(NS) | p2(EW) | 합집합 | 동시녹색 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 원본 `.sig` | 150 | 72.0 | 69.0 | 141.0 | 0.0 |
| 새 `.sig` | 150 | 69.0 | 69.0 | 138.0 | 0.0 |

138 = 150 − 4×3 이다. 옛 141 은 청산이 셋이던 값이고, 새 프로그램은 배리어 안에 현시
경계가 하나씩 더 생겨 네 번 문다. 두 축은 새 프로그램에서도 안 겹친다 — 축이 사라진 게
아니라 **배리어가 각각 두 현시로 쪼개졌을 뿐**이고, 그 쪼갬이 아직 모델까지 안 올라왔다.

## 9. 확인 못 한 것

1. **VISSIM 을 안 띄웠다.** 새 `.inpx` 도 새 `.sig` 도 COM 으로 로드해 보지 않았다.
   작업 1 의 `<sc checkSum>` 미검증이 그대로 남아 있고, 여기에 감사 `vissim_error_log`
   NOT_EVALUATED 가 더해졌다.
2. **실런을 안 돌렸다.** 새 배선은 어떤 실행 스크립트에도 안 물려 있다. production
   `.ps1` 의 `$Network` · `$Tuning` · `RW_SIGNAL_SG_PLAN` 은 여전히 옛 것을 가리킨다.
3. **교차로 간 연동(progression)** 은 안 쟀다. `offset` 을 원본 값 그대로 뒀다.
