# VISSIM Strict Hybrid Rollout Plant G0 설계 계약

- 문서 상태: `G0 approved` (`독립 gate review PASS`)
- 계약 버전: `vissim-strict-plant-g0/v3.0.0`
- 작성 기준일: `2026-07-31`
- 적용 범위: `Phase 0`부터 `Phase 5`까지의 topology compiler, hybrid plant, state projector, MPC bridge, shadow validation, 단계적 actuation
- 규범 용어: `MUST`는 필수, `SHOULD`는 원칙적 필수, `MAY`는 선택 구현을 뜻한다.

## 0. Precondition과 문서 우선순위

이 계약은 다음 저장소 지침을 확인한 뒤 작성했다.

- `AGENTS.md`
- `CLAUDE.md`

`AGENTS.md`가 major controller 또는 experiment 변경 전에 읽도록 요구하는 아래 문서는 현재 기준 branch에 존재하지 않는다.

- `docs/codex_implementation_spec.md`
- `docs/experiment_acceptance_criteria.md`
- `docs/agent_debate_protocol.md`
- `reports/claude_review_report.md`

따라서 이 계약은 누락된 문서를 임의로 대체하지 않는다. 해당 문서가 이후 추가되면 구현 담당자는 충돌 여부를 검토하고, 충돌이 있으면 코드를 변경하기 전에 이 계약을 새 버전으로 개정해야 한다. 현재 누락은 `Phase 0` 착수를 막지 않으며, 본 문서의 `G0` 계약과 아래 acceptance criteria를 임시 권위 기준으로 사용한다.

우선순위는 다음과 같다.

1. 사용자의 명시적 결정
2. 이 G0 계약의 최신 승인 버전
3. `AGENTS.md`와 `CLAUDE.md`
4. 정본 저장소의 기존 config와 코드 기본값

## 1. Source of Truth

### 1.1 Numerical-Sim

| 항목 | 계약값 |
|---|---|
| repository | `https://github.com/Ming2you/Numerical-Sim.git` |
| source branch | `flagship-ms-adapt-clean` |
| base commit | `7f1039378777feeff3b60ef2a9a17f182ed5c2dd` |
| implementation worktree | `C:\tmp\numerical-sim-strict-vissim` |
| implementation branch | `codex/strict-vissim-plant-20260731` |

모든 구현, 테스트, 검증 결과는 `base commit` 또는 그 후속 승인 commit을 명시해야 한다. 로컬의 다른 `Numerical-Sim` 복사본과 기존 adapter의 하드코딩된 경로는 정본으로 사용하면 안 된다.

### 1.2 VISSIM network

- 동역학 topology의 권위 입력은 최신 사용자 수정본 `modi.inpx`와 해당 network가 참조하는 signal program 파일(`.sig`)이다.
- VISSIM 참조 workspace는 별도 `Ming2you/VISSIM` checkout이며 경로는 실행 환경에서 명시한다.
- `modi.layx`는 camera, layout, label, visibility 등 시각화 정보이므로 canonical topology와 plant hash에서 `MUST` 제외한다.
- `Urban-Follower.xlsx`와 기존 UF mapping은 control authority와 검수용 metadata로만 사용한다. 물리 topology의 권위 원본이 아니다.
- compiler output은 입력 `modi.inpx`, 참조 `.sig`, control mapping 각각의 `SHA-256`을 기록해야 한다.

## 2. Canonical Units

plant 내부의 모든 계산과 public strict-plant schema는 SI 기반 canonical unit을 `MUST` 사용한다.

| 수량 | canonical key 예시 | 내부 단위 |
|---|---|---|
| 거리/길이/위치 | `length_m`, `position_m` | `m` |
| 시간 | `sim_time_sec`, `dt_sec` | `s` |
| 차량 수/queue | `vehicle_count_veh`, `queue_veh` | `veh` |
| 속도 | `speed_mps` | `m/s` |
| 유량/용량/수요 | `flow_vehps`, `capacity_vehps` | `veh/s` |
| 밀도 | `density_vehpmpl` | `veh/m/lane` |
| 비율/green fraction | `turn_ratio`, `green_fraction` | dimensionless |

### 2.1 Boundary conversion

VISSIM 또는 기존 METANET API 경계에서만 아래 변환을 허용한다.

```text
speed_mps             = speed_kph / 3.6
speed_kph             = speed_mps * 3.6
flow_vehps            = flow_vehph / 3600.0
flow_vehph            = flow_vehps * 3600.0
density_vehpmpl       = density_vehpkmpl / 1000.0
density_vehpkmpl      = density_vehpmpl * 1000.0
length_m              = length_km * 1000.0
length_km             = length_m / 1000.0
time_sec              = time_msec / 1000.0
time_msec             = time_sec * 1000.0
```

- 변환 함수는 boundary adapter에 집중시키고 함수명 또는 type metadata에 source/target unit을 드러내야 한다.
- unit 없는 scalar를 strict plant API에 전달하면 validation error로 처리한다.
- 내부 TTT 누적의 canonical 단위는 `veh*s`이며, 보고 단계에서만 `veh*h`로 나눈다.
- 부동소수점 비교 tolerance는 물리 acceptance와 numerical tolerance를 구분한다.

## 3. Time Contract

### 3.1 Master clock

- 모든 state, observation, action schedule, signal event는 VISSIM simulation 시작을 `0.0`으로 하는 절대 `sim_time_sec`를 `MUST` 사용한다.
- wall clock, controller process 시작시간, 배열 index를 simulation time 대신 사용하면 안 된다.
- interval은 원칙적으로 반개구간 `[start_time_sec, end_time_sec)`로 정의한다.
- 같은 timestamp의 event 적용 순서는 `plan activation -> signal transition -> boundary demand -> physical flow update -> observation/output`으로 고정한다.

### 3.2 Numerical grids

- urban reference kernel의 기본 `urban_dt_sec`는 `1.0 s`다.
- topology compiler는 모든 CTM cell과 wave speed에 대해 topology-aware CFL을 검증해야 한다.

```text
urban_dt_sec <= min(cell_length_m / free_flow_speed_mps,
                    cell_length_m / backward_wave_speed_mps)
```

- CFL을 만족하지 않으면 compiler 또는 plant initialization이 실패해야 한다. occupancy clamp로 숨기면 안 된다.
- 향후 성능 최적화를 위한 vectorized batch와 local subcycle은 `MAY` 허용한다. 단, 1초 reference kernel과 golden fixture 결과가 정해진 tolerance 안에서 같아야 한다.
- 매우 짧은 connector 또는 midblock 구간은 비현실적으로 짧은 CTM cell을 강제하지 않고 `vertical_queue` 또는 `flow_gate`로 표현할 수 있다. 이 축약은 원 구간의 `minimum_travel_time_sec > 0`와 `storage_veh > 0`를 보존해야 하며, 유입이 같은 step에 즉시 유출되는 zero-travel-time edge는 금지한다. travel-time buffer 또는 동등한 cumulative-flow 제약을 둔다.
- freeway METANET 기본 step은 config-derived `5-10 s` 범위다. 시작 default는 기존 정본과 호환되는 `10 s`이며, 도시부와의 coupling 시 정수비 subcycle 또는 정확한 flux accumulation을 사용한다.
- `control_interval_sec`, `prediction_horizon_steps`, `control_horizon_steps`는 하드코딩하지 않고 config에서 읽는다.
- `control_horizon_steps`는 strict schema에 명시한다. strict plant의 기본은 `1`이며 horizon 전체 move blocking을 뜻한다. 정본 legacy config 일부의 기본값은 `3`이지만 현재 controller가 이를 실제 다단 제어열로 사용하지 않는다는 사실을 compatibility metadata와 warning으로 기록한다. 구현 전까지 `3`을 다단 action sequence로 해석하면 안 된다.
- benchmark 최소 horizon은 `H=3`, 목표 benchmark는 `H=5`다. `H=5` 승격은 runtime과 VISSIM ranking 검증을 통과해야 하며, 통과 전 production default는 `H=3`이다.

### 3.3 Signal event overlap

- signal green, yellow, all-red 또는 stage interval이 numerical step 일부와만 겹치면 겹친 실제 시간만큼 capacity를 적분해야 한다.
- step 시작 시점의 boolean signal state를 전체 step에 복제하면 안 된다.

```text
effective_green_sec = measure(step_interval intersect green_intervals)
service_capacity_veh = saturation_flow_vehps * effective_green_sec
```

## 4. Signal Program과 Offset

### 4.1 Source program과 canonical SG timeline

실제 `.sig`에는 stage 또는 stage program이 없고 SG별 `cmd display/begin` 및 `fixedstate duration`만 존재할 수 있다. 따라서 canonical signal schedule의 기본 표현은 controller 아래 **SG별 periodic state-transition timeline**이다. stage는 source에 존재하고 완전히 검증된 경우에만 보조 metadata로 보존한다.

```yaml
signal_schedule:
  schedule_id: string
  controller_id: string
  source_program_id: string
  active_prog_no: int
  cycle_length_sec: float
  source_timeline_origin: raw_sig_command_t0
  source_phase_terms:
    switchpoint_sec: float
    sig_program_offset_sec: float
    controller_offset_sec: float
    provenance: {term: source_path_or_attribute}
  start_time_of_day_sec: float
  cycle_epoch_sec: float
  action_offset_lag_delta_sec: float
  sg_timelines:
    sg_id:
      permanent_red: bool
      intervals:
        - event_id: string
          start_sec: float
          end_sec: float
          display: GREEN | AMBER | RED
          source_kind: command | fixedstate | derived
  valid_from_sec: float
  activation_boundary_sec: float
  created_at_sim_time_sec: float
  source: fixed | controlled | derived
```

- 모든 `.sig` millisecond 값은 compiler boundary에서 `/ 1000.0`으로 초로 변환하고 원시 정수값과 provenance를 함께 보존한다.
- SG timeline은 반개구간 `[start_sec, end_sec)`으로 cycle 전체를 빈틈과 중복 없이 덮어야 하며 마지막 interval에서 첫 interval로 wrap-around한다.
- `fixedstate duration`은 signal sequence의 현재 `cmd display`에서 target `cmd display`까지 이르는 경로에 있는 fixed-duration state를 **target `cmd begin` 직전에 역방향으로 배치**해 명시적 periodic interval로 전개한다. 예를 들어 현재 GREEN이고 target RED의 `begin=65 s`, 경로상 AMBER의 `duration=3 s`이면 AMBER는 `[62,65)`, GREEN은 `62 s`까지다. 여러 fixed-duration state는 target에서 거꾸로 누적하고 cycle wrap-around에도 같은 알고리즘을 적용한다. 두 command 사이 시간이 필요한 fixed duration 합보다 짧으면 임의 축약하지 않고 validation error로 실패한다. cycle 전체가 red인 SG는 `permanent_red: true`로 표현한다.
- source가 생략한 display 구간을 임의 green으로 추론하면 안 된다. 검증 가능한 VISSIG semantics로 전개할 수 없으면 compiler가 실패한다.
- `EW/NS`, `major/minor`, 2-phase, `p1/p2` 고정 schema는 금지한다. control action은 SG별 green window 또는 검증된 named-program transformation이어야 한다.
- 하나의 SG가 여러 signal head와 물리 gate를 제어할 수 있다. SG clock은 하나지만 gate 위치, 저장공간, minimum travel time, downstream supply는 각각 보존한다.
- 각 SG timeline의 GREEN/AMBER/RED 상태, minimum green, clearance, conflict를 독립적으로 검증한다. controller event duration 합만으로 cycle coverage를 판정하면 안 된다.

### 4.2 Program 선택과 source phase normalization

- INPX controller의 `progNo`가 실행 시작 시 active `.sig` program을 선택한다. runtime program-switch command가 없다면 rollout horizon 동안 해당 program을 유지한다.
- runtime program 전환을 허용하려면 target `progNo`, `activation_boundary_sec`, 이전/새 program의 원자적 전환, COM readback을 모두 action에 명시해야 한다. 그 전에는 program 전환을 금지한다.
- `.sig cycletime`, `.sig switchpoint`, `.sig program offset`, INPX controller `offset`, runtime action lag는 서로 다른 필드로 보존하며 덮어쓰지 않는다.
- PTV semantics에 따라 signal program `offset`은 전체 signal plan을 지연한다. `switchpoint`는 다른 signal program으로 전환할 수 있는 시각이며 phase offset이 아니므로 절대 phase 식에 더하거나 빼지 않는다.
- canonical source origin은 active `.sig` program의 raw command timeline `t=0`이다. `cycle_epoch_sec=0`은 00:00:00의 cycle origin을 뜻한다. 일반 source phase는 다음 식으로 유일하게 정의한다.

```text
C = cycle_length_sec
source_phase_sec = mod(
    sim_time_sec
    + start_time_of_day_sec
    - cycle_epoch_sec
    - sig_program_offset_sec
    - controller_offset_sec,
    C
)
```

- 현재 `modi.inpx`의 simulation `startTm=0`, 모든 SC의 controller `offset=0`, active `progNo=1` 조건에서는 정확한 static source phase가 `mod(sim_time_sec - sig_program_offset_sec, C)`로 축약된다. 따라서 Phase 0 fixed-plan parser와 rollout은 이 current-network 식으로 구현할 수 있다.
- `switchpoint_sec`는 program-switch validation metadata로만 보존한다. `sig_program_offset_sec`, `controller_offset_sec`, `cycle_epoch_sec`, `start_time_of_day_sec`는 provenance와 함께 별도 보존하고 하나의 불투명 상수로 합치지 않는다.
- nonzero `controller_offset_sec`의 실제 COM 의미와 write/read 변환은 G3 controller별 readback fixture 전까지 actuation 계약으로 간주하지 않는다. nonzero 값을 가진 네트워크를 fixed-plan으로 읽을 때도 해당 fixture 또는 공식적으로 검증된 parser semantics가 필요하다.

### 4.3 Canonical runtime offset semantics와 COM NO-GO

strict plant 내부에서 action의 positive runtime offset은 기준 source timeline을 늦추는 `lag`로 고정한다. 이 값은 source program/controller offset과 합치지 않고 `action_offset_lag_delta_sec`로 별도 저장한다.

```text
canonical_phase_sec = mod(source_phase_sec - action_offset_lag_delta_sec, C)
```

`mod`는 음수 입력에도 `[0, C)`를 반환해야 한다. Phase 0 compiler는 controller별 source phase term과 변환 provenance를 산출한다. 정확한 COM writer 식은 G3의 controller별 VISSIG/COM write-read round-trip fixture로 확정한다.

**G3 round-trip fixture가 통과하기 전에는 runtime offset actuation을 반드시 disabled 상태로 둔다.** Phase 0 fixed-plan parser/rollout은 위 current-network static 식을 사용한다. G0는 plant 내부 lag semantics와 source normalization만 고정하며, 검증되지 않은 부호 반전이나 VBS의 `(t + offset) mod C` 식을 그대로 사용하지 않는다. Phase 5 offset actuation은 G3 및 G6 통과 전 `NO-GO`다.

### 4.4 Controlled/fixed 혼합 SC

- 같은 SC의 모든 SG는 native source clock을 공유한다.
- Phase 5 green-only 동안 `cycle_length_sec`, source epoch, source offset, INPX offset은 native 값으로 고정한다. action-enabled SG의 green windows만 conflict, minimum green, amber/all-red를 지키는 안전한 transformation으로 변경한다.
- fixed SG와 midblock SG는 native `.sig` clock과 timeline을 유지한다. controlled SG의 green 변경이 fixed SG와 conflict를 만들면 action은 infeasible이다.
- cycle/epoch/offset 변경과 parent-derived midblock은 **SC 전체 COM replay**가 구현되고 모든 SG의 원래/변경 timeline을 같은 clock에서 재생하며 G3/G6를 통과한 뒤에만 허용한다.
- 선택 SG만 별도 2현시 clock으로 구동하면서 같은 SC의 fixed SG를 native VISSIG에 남기는 방식은 금지한다.

### 4.5 Pending plan과 atomic activation

- 실행 중 생성된 새 계획은 즉시 현재 현시를 절단하지 않는다.
- 결정 시점 이후의 다음 canonical cycle boundary는 `b = min {t >= decision_time_sec | canonical source phase(t) = 0}`로 정의한다. `ActionSchedule.activation_boundary_sec`는 이 `b`이며 이전 plan의 minimum green, amber, all-red도 침범하지 않아야 한다. 안전조건을 만족하지 못하면 그다음 cycle boundary로 이월한다.
- 새 plan은 `pending_schedule_id`로 보관하고 integration step `[t0,t1]`가 `t0 < b <= t1`로 boundary를 통과할 때 controller 단위로 원자적으로 활성화한다. 이미 state time이 `b` 이상인데 pending plan이 아직 활성화되지 않았다면 첫 다음 step 시작에서 즉시 한 번 활성화한다. 정확한 floating-point equality에 의존하지 않으며 일부 SG만 먼저 전환하면 안 된다.
- activation 전에는 old plan이 계속 유효하며, activation 실패 시 old plan 또는 validated fixed plan으로 명시적으로 fallback한다.
- `valid_from_sec`는 command가 사용 가능한 최초 시간이고, `activation_boundary_sec`는 물리적으로 적용되는 시간이다. 두 값을 혼용하면 안 된다.

## 5. Canonical Topology Schema

compiler는 전체 VISSIM graph를 먼저 lossless하게 compile하고, rollout 때 control 영향권의 `influence_subgraph`를 선택한다. topology 밖으로 잘라낸 edge는 명시적 boundary condition이 되어야 하며 차량이 암묵적으로 생성되거나 사라지면 안 된다.

최상위 manifest의 최소 필드는 다음과 같다.

```yaml
strict_topology:
  schema_version: string
  compiler_version: string
  source:
    inpx_path: string
    inpx_sha256: string
    signal_programs_sha256: {program_id: sha256}
    control_mapping_sha256: string
  coordinate_system: string | null
  links: []
  lane_groups: []
  cells: []
  connectors: []
  movements: []
  signal_controllers: []
  signal_groups: []
  signal_gates: []
  schedules:
    fixed: []
    controlled: []
    derived: []
  routes: []
  boundaries: []
  freeway_interfaces: []
  observation_operators: []
  influence_subgraphs: []
```

### 5.1 Entity requirements

- `links`: VISSIM source ID, geometry, `length_m`, lane references, behavior/level metadata, speed prior, boundary/interface flag
- `lane_groups`: member lane IDs, longitudinal extent, shared downstream choices, shared signal gate, storage and model type
- `cells`: `cell_id`, `lane_group_id`, `ordered_index`, `length_m`, `lanes`, `model_type`, `upstream_cell_ids`, `downstream_cell_ids`, `storage_veh`, `minimum_travel_time_sec`, `delay_buffer_steps`. `ordered_index`는 lane group 안에서 0부터 시작해 연속적이어야 하며, upstream/downstream reference는 방향성과 연결 순서를 보존해야 한다. `minimum_travel_time_sec > 0`인 축약 cell/gate는 `delay_buffer_steps >= ceil(minimum_travel_time_sec / urban_dt_sec)`를 만족하고 같은 step 유입-유출을 금지한다.
- `connectors`: upstream/downstream lane-group references, geometry, lane mapping, merge/diverge metadata
- `movements`: source/target lane group, connector path, commodity/turn class, capacity, priority, `turn_ratio`
- `signal_gates`: physical stop-line position, controlled movement IDs, SC/SG IDs, source signal head IDs
- `schedules`: complete fixed, action-enabled controlled, future parent-derived plans
- `routes`: source routing decision/route IDs, ordered link or connector sequence, `rel_flow` prior, validity interval
- `boundaries`: source/sink type, demand/admitted-flow distinction, external queue ownership
- `freeway_interfaces`: urban/freeway ownership transfer edge와 sending/receiving coupling 규칙

모든 entity는 stable canonical ID와 원래 VISSIM object ID를 모두 가져야 한다. `schema_version`, source hash, compiler version이 다르면 topology cache를 재사용하면 안 된다.

### 5.2 Immutable PlantParameters

동역학 parameter는 topology나 runtime state에 암묵적으로 섞지 않고 immutable `PlantParameters`로 바인딩한다. public object는 `StrictPlant(topology, parameters)`이며 생성 뒤 topology와 parameters를 mutation할 수 없다.

```yaml
plant_parameters:
  schema_version: string
  topology_hash: sha256
  parameter_hash: sha256
  cell:
    cell_id:
      v_free_mps: float
      w_mps: float
      rho_jam_veh_per_m_lane: float
      q_max_vehps: float
  node_priorities: {movement_or_connector_id: float}
  saturation_flow_vehps: {movement_or_gate_id: float}
  startup_loss_sec: {signal_gate_id: float}
  provenance: {parameter_key: source_or_calibration_ref}
  uncertainty: {parameter_key: distribution_or_interval}
  calibration_version: string
```

- `v_free_mps`, `w_mps`, `rho_jam_veh_per_m_lane`, `q_max_vehps`, node priority, saturation flow, startup loss에는 모두 단위, provenance, uncertainty를 기록한다.
- parameter hash는 topology hash, schema version, canonical parameter payload를 포함한다. topology hash가 다른 parameter set을 로드하면 initialization이 실패한다.
- runtime rollout 중 parameter mutation은 금지한다. adaptive estimation 결과는 새 version과 새 `parameter_hash`를 가진 immutable snapshot으로 교체한다.

## 6. PlantState와 Observation

### 6.1 PlantState

`PlantState`는 특정 topology hash에 종속되며 최소 다음 구조를 갖는다.

```yaml
plant_state:
  schema_version: string
  topology_hash: sha256
  state_hash: sha256
  sim_time_sec: float
  stocks:
    stock_id:
      owner_kind: freeway_cell | freeway_origin_queue | urban_cell | travel_time_buffer | ramp_queue | ramp_storage | boundary_source_queue
      owner_id: string
      vehicle_count_veh: float
  freeway:
    density_vehpmpl: {cell_id: float}
    speed_mps: {cell_id: float}
    cell_stock_id: {cell_id: stock_id}
    origin_queue_stock_id: {origin_id: stock_id}
  urban:
    cell_stock_id: {cell_id: stock_id}
    commodity_fraction: {lane_group_id: {commodity_id: float}}
  connectors:
    cumulative_flow_veh: {movement_id: float}
  ramps:
    queue_stock_id: {ramp_id: stock_id}
    storage_stock_id: {ramp_id: stock_id}
  boundaries:
    source_queue_stock_id: {boundary_id: stock_id}
    cumulative_admitted_veh: {boundary_id: float}
  signals:
    active_schedule_id: {controller_id: string}
    pending_schedule_id: {controller_id: string | null}
    sg_state:
      sg_id:
        current_display: GREEN | AMBER | RED
        current_event_id: string
        event_elapsed_sec: float
        cycle_position_sec: float
  estimation:
    mode: vissim_oracle | detector_realistic
    covariance_ref: string | null
    freshness_sec: {operator_id: float}
    fallback_flags: [string]
```

- 모든 physical vehicle stock은 `stocks` registry에 정확히 한 번 등록한다. 모든 stock entry는 globally unique `stock_id`, `owner_kind`, `owner_id`, `vehicle_count_veh`를 필수로 가지며 `(owner_kind, owner_id)`도 유일해야 한다. freeway/urban/ramp/boundary 필드는 stock value를 복제하지 않고 해당 `stock_id`만 참조한다.
- physical vehicle state는 한 owner에만 속해야 한다. urban lane-group queue, queue tail, ramp occupancy view 등 derived view는 stock ID를 참조해 계산하며 별도 stock value를 저장하거나 질량합에 더하지 않는다.
- connector는 기본적으로 zero-storage transfer edge이며 occupancy stock을 갖지 않는다. 물리적 저장공간 또는 양의 최소 이동시간이 필요한 connector는 하나 이상의 explicit cell 또는 travel-time buffer로 모델링한다.
- shared lane은 하나의 physical queue를 유지하고 turn별 흐름은 `commodity_fraction`으로 표현한다.
- covariance는 sparse matrix, ensemble 또는 diagonal approximation일 수 있으나 표현 방식과 state ordering을 versioned metadata로 명시한다.

`PlantState.total_vehicle_inventory()`는 오직 `stocks` registry의 `vehicle_count_veh`를 stock ID별 정확히 한 번 합산한다.

```text
N_total = sum(stock.vehicle_count_veh for stock in stocks.values())
```

`cumulative_flow_veh`, lane-group queue derived view, queue tail, detector aggregates, commodity fractions는 stock이 아니며 `N_total`에 포함하지 않는다. derived view가 존재하지 않는 stock ID를 참조하거나 둘 이상의 owner가 같은 stock ID를 참조하거나 registry 밖의 vehicle count를 가지면 schema validation error다.

### 6.2 Observation modes

모든 projector 입력은 먼저 다음 versioned raw observation envelope로 검증한다.

```yaml
raw_observation:
  schema_version: string
  observation_id: string
  network_hash: sha256
  sim_time_sec: float
  captured_interval: {start_sec: float, end_sec: float}
  units: {field_name: canonical_or_source_unit}
  vehicles:
    - vehicle_id: string
      lane_id: string
      position_m: float
      speed_mps: float
      observed_at_sec: float
  detector_values:
    - detector_id: string
      operator_id: string
      measurement_kind: count | flow | speed | occupancy | queue_length | travel_time
      value: float
      unit: veh | veh_per_sec | m_per_sec | fraction | m | sec
      observed_at_sec: float
      interval_start_sec: float | null
      interval_end_sec: float | null
  signal_readback:
    - controller_id: string
      sg_id: string
      display: GREEN | AMBER | RED
      program_no: int
      cycle_position_sec: float | null
      unit: signal_display
      observed_at_sec: float
  boundary_values:
    - boundary_id: string
      measurement_kind: commanded_demand | admitted_flow | exited_flow | source_queue
      value: float
      unit: veh_per_sec | veh
      observed_at_sec: float
      interval_start_sec: float | null
      interval_end_sec: float | null
```

- timestamp는 master simulation clock과 일치해야 하며 미래 관측, 역행 timestamp, network hash mismatch를 거부한다.
- 같은 observation 안의 `vehicle_id`는 유일해야 한다. 중복 ID를 합산하거나 마지막 값으로 덮어쓰지 않고 observation 전체를 invalid 처리한다.
- 각 typed record의 ID는 topology/observation operator에 존재해야 하고 record timestamp는 envelope interval 안에 있어야 한다. unit metadata가 없거나 `measurement_kind`의 허용 unit과 payload가 불일치하면 projection을 거부한다.
- 동일 차량을 oracle vehicle row, detector aggregate, queue counter에서 동시에 stock으로 합산하면 안 된다. observation operator는 각 값이 stock constraint인지 보조 measurement인지 명시한다.

`project_observation`은 두 모드를 모두 지원하는 것이 최종 목표다.

1. `vissim_oracle`
   - VISSIM의 vehicle `Lane`, `Pos`, `Speed`, 가능하면 route/vehicle ID를 사용해 cell과 lane group에 직접 투영한다.
   - plant fidelity와 algorithm 검증을 위한 주된 개발 모드다.

2. `detector_realistic`
   - data collection, queue counter, travel-time, signal state, boundary count 등 현실적 관측만 사용한다.
   - conservation estimator, EnKF 또는 MHE 계열 추정기를 사용할 수 있다.
   - covariance, observation freshness, unobserved-state fallback을 반드시 출력한다.

관측 누락 또는 covariance 초과 시 해당 corridor/UF는 fixed schedule로 fallback할 수 있어야 한다. 두 mode는 같은 `PlantState` schema를 반환해야 하며 mode별 성능을 혼합 보고하면 안 된다.

## 7. ControlAction과 ActionSchedule

### 7.1 Authority

action-enabled UF는 정확히 다음 14개다.

```text
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16
```

- 위 UF의 mapping으로 명시된 SC/SG만 control authority를 가진다.
- UF `5, 11, 17, 18, 19`를 포함한 나머지 모든 SC/SG는 plant에 존재하되 fixed schedule로 rollout한다.
- action-enabled 여부와 plant 포함 여부를 혼동하면 안 된다.
- `Phase 5`의 midblock 검증 전까지 모든 midblock gate는 원래 `.sig` fixed schedule을 사용한다.
- 검증 통과 후에만 승인된 midblock을 parent schedule에서 deterministic하게 파생할 수 있다. midblock은 별도 MPC decision variable로 자동 추가하지 않는다.

### 7.2 Schema

기존 `ControlAction`의 green, offset, ramp metering, VSL, allocation 의미를 보존하되 strict plant boundary에서는 versioned `ActionSchedule`로 정규화한다.

```yaml
control_action:
  schema_version: string
  action_id: string
  topology_hash: sha256
  based_on_state_hash: sha256
  decision_time_sec: float
  valid_from_sec: float
  activation_boundary_sec: float
  valid_until_sec: float
  signal_plans: {controller_id: signal_schedule}
  ramp_metering_vehps: {ramp_id: float}
  vsl_mps: {segment_id: float}
  allocations: {movement_or_boundary_id: float}
  legacy_intent:
    N_P_star:
      value: float | null
      unit: veh
    N_UF_star:
      value: float | null
      unit: veh_per_hour | veh_per_control_interval
    extra_fields: {legacy_field_name: value}
  authority_ids: [string]

action_schedule:
  schedule_id: string
  control_interval_sec: float
  prediction_horizon_steps: int
  control_horizon_steps: int
  move_blocking: bool
  activation_boundary_sec: float
  entries:
    - start_time_sec: float
      end_time_sec: float
      action: control_action
```

- action은 absolute time interval에 바인딩한다.
- `topology_hash`, `based_on_state_hash`, authority, validity interval이 일치하지 않으면 적용을 거부한다.
- candidate가 한 action을 horizon 전체에 유지하는 move blocking과 다단 action sequence를 모두 표현할 수 있어야 한다.
- legacy `ControlAction`의 `N_P_star`, `N_UF_star`는 physical actuator가 아니라 leader intent metadata로 보존한다. `N_P_star`의 unit은 항상 `veh`다. `N_UF_star`는 `value`와 unit enum `veh_per_hour | veh_per_control_interval`을 함께 저장하고 legacy `cfg.leader.N_UF_star_unit`에 따라 해석·복원한다. strict action으로 변환했다가 legacy action으로 되돌릴 때 값, `None`, unit, identity가 손실되면 안 된다.
- legacy ramp metering/allocation flow의 `veh/h`는 strict boundary에서 `/3600`하여 `veh/s`로, strict에서 legacy로는 `*3600`하여 변환한다. legacy VSL의 `km/h`는 `/3.6`하여 `m/s`로, 역변환은 `*3.6`으로 수행한다.
- `legacy_to_strict()`와 `strict_to_legacy()`는 unit metadata를 검사하고 golden round-trip fixture에서 actuator field와 intent field를 모두 보존해야 한다.
- `activation_boundary_sec`는 각 signal plan의 값과 일치해야 하며 signal이 없는 action은 `valid_from_sec`와 같을 수 있다.

### 7.3 DemandSchedule

strict plant의 수요 입력은 versioned `DemandSchedule`로 정규화한다.

```yaml
demand_schedule:
  schema_version: string
  schedule_id: string
  topology_hash: sha256
  start_time_sec: float
  end_time_sec: float
  interval_sec: float
  global_incident_capacity_factor: float
  initial_source_queues_veh: {source_id: float}
  entries:
    - start_time_sec: float
      end_time_sec: float
      boundary_demand_vehps: {boundary_id: float}
      freeway_lane_loss:
        - segment_id: string
          lanes_closed: float
          start_time_sec: float
          end_time_sec: float
      incidents:
        - incident_id: string
          affected_entity_ids: [string]
          capacity_factor: float
          speed_factor: float
          start_time_sec: float
          end_time_sec: float
```

- demand interval은 반개구간이고 schedule 전체를 빈틈 없이 덮는다. boundary/source ID는 topology에 존재해야 한다.
- commanded boundary demand와 admitted flow, source queue는 구분한다. source queue 초기값은 schedule top-level `initial_source_queues_veh`에 한 번만 선언하며 interval entry에는 둘 수 없다. source queue의 stock owner는 `PlantState.boundaries.source_queue_stock_id`가 참조하는 registry entry다.
- legacy `DemandStep.incident_capacity_factor`는 top-level `global_incident_capacity_factor` scalar로 별도 보존해 무손실 round-trip한다. `incidents[]`는 이 scalar를 대체하지 않으며 추가적인 국소 사건만 표현한다.
- legacy `DemandStep`의 `veh/h` 값은 `/3600`해 `veh/s`로 변환하고 `freeway_lane_loss`, global incident scalar, local incident semantics를 손실 없이 보존한다. 역변환과 round-trip fixture를 제공한다.
- demand/action/topology의 시간 범위와 hash가 불일치하면 rollout을 시작하지 않는다.

## 8. Strict Plant API

```python
plant = StrictPlant(topology=topology, parameters=parameters)  # immutable

plant.project_observation(
    observation,
    previous_state=None,
    mode="vissim_oracle",
) -> PlantState

plant.rollout_batch(
    initial_state,
    action_schedules,
    demand_schedule,
    start_time_sec,
    horizon_sec,
    abort_above=None,
    subgraph_view=None,
) -> BatchRolloutResult

plant.advance_interval(
    state,
    committed_action,
    demand_schedule,
    end_time_sec,
    subgraph_view=None,
) -> StepResult

plant.step(
    state,
    action,
    demand,
    dt_sec,
    subgraph_view=None,
) -> StepResult
```

`StrictPlant.step()`, `advance_interval()`, `rollout_batch()`는 모두 pure function이다. 입력 state/action/demand/trajectory를 mutation하지 않고 새 result 객체를 반환한다. 성공한 step의 `next_state.sim_time_sec`는 정확히 `state.sim_time_sec + dt_sec`여야 하며 `advance_interval()`의 next state는 정확히 `end_time_sec`이어야 한다. 시간 증가는 strict kernel만 소유한다. 실패/invalid 상태에서는 입력 객체를 수정하지 않는다.

legacy `run_coupled_interval()` compatibility bridge만 기존 in-place mutation을 제공할 수 있다. bridge는 strict result를 legacy object에 한 번 복사하고, legacy caller가 시간을 추가 증가시키지 않도록 `time_owner: strict_kernel`을 명시한다. migration 기간의 double-step/time-freeze assertion을 필수로 둔다.

local Wu/follower rollout은 다른 물리 kernel을 만들지 않고 동일 strict kernel의 명시적 subgraph view를 사용한다.

```yaml
subgraph_view:
  subgraph_id: string
  topology_hash: sha256
  owned_state_ids: [string]
  frozen_boundary_trajectory_ref: string
  ownership_scope: [string]
  objective_scope: [string]
```

```yaml
frozen_boundary_trajectory:
  schema_version: string
  trajectory_id: string
  trajectory_hash: sha256
  topology_hash: sha256
  subgraph_id: string
  samples:
    - time_sec: float
      boundary_edges:
        boundary_edge_id:
          sending_vehps: float
          receiving_vehps: float
          demand_vehps: float
```

- `samples`는 `time_sec` 오름차순이며 duplicate timestamp가 없어야 하고 rollout interval 전체를 덮어야 한다. boundary edge는 subgraph cut에 존재해야 하며 내부 stock owner와 중복될 수 없다.
- resolver API는 `resolve_frozen_boundary_trajectory(ref, expected_topology_hash, expected_subgraph_id) -> FrozenBoundaryTrajectory`로 고정한다. resolver는 ID/hash/topology/subgraph 불일치, 시간 공백, 음수 flow를 거부하고 immutable trajectory를 반환한다.
- local objective는 범위를 제한할 수 있지만 물리 state transition과 parameter set은 global strict kernel과 동일해야 한다.

`StepResult`와 `BatchRolloutResult`의 status enum은 다음으로 고정한다.

```text
OK
INFEASIBLE
INVALID_INPUT
EARLY_ABORTED
TIMEOUT
PARTIAL
NUMERICAL_ERROR
```

- `OK`만 완전한 feasible result다.
- `EARLY_ABORTED`는 `abort_above`에 의한 정상 pruning이며 terminal state가 없을 수 있다.
- `PARTIAL`은 일부 candidate/interval만 완료된 상태로 actuation에 사용할 수 없다.
- status 외에 `reason_code`, `completed_horizon_sec`, `is_feasible`, `is_complete`를 명시한다.

`StepResult`는 최소한 다음을 보고한다.

- terminal 또는 next `PlantState`
- total/freeway/urban TTT
- queue, spillback, constraint penalty
- boundary and interface flows
- mass conservation residual
- infeasibility reason
- runtime과 early-abort 여부
- topology/state/action hash
- parameter/demand/subgraph hash 또는 ID

`BatchRolloutResult`는 입력 `action_schedules`와 동일한 순서와 길이의 `candidate_results[]`를 반드시 반환한다.

```yaml
batch_rollout_result:
  schema_version: string
  batch_status: OK | PARTIAL | INVALID_INPUT | TIMEOUT | NUMERICAL_ERROR
  selected_candidate_index: int | null
  fallback_required: bool
  candidate_results:
    - candidate_index: int
      action_hash: sha256
      status: OK | INFEASIBLE | INVALID_INPUT | EARLY_ABORTED | TIMEOUT | PARTIAL | NUMERICAL_ERROR
      is_feasible: bool
      total_cost: float | null
      terminal_state_hash: sha256 | null
      diagnostics: {string: value}
      error: {reason_code: string, message: string} | null
```

- 후보 순서는 completion order로 재정렬하지 않는다. 혼합 status batch는 최소 하나의 complete feasible candidate가 있으면 `batch_status=PARTIAL`일 수 있으나 선택은 complete feasible candidate 중 minimum `total_cost`, 동률이면 가장 낮은 input index로 결정한다.
- `EARLY_ABORTED`, `PARTIAL`, `TIMEOUT`, `INVALID_INPUT`, `NUMERICAL_ERROR`, `INFEASIBLE` 후보는 선택할 수 없다. 모든 후보가 실패하거나 infeasible이면 `selected_candidate_index=null`, `fallback_required=true`로 반환해 Section 10.2 fallback을 실행한다.

Stackelberg leader, freeway follower, urban follower, distributed candidate 평가, one-step audit, no-control replay는 동일 strict plant API와 동일 parameter set을 `MUST` 사용한다. audit만 새 plant를 쓰고 candidate selection은 기존 plant를 쓰는 이중 경로는 금지한다.

## 9. Physical and Schema Invariants

### 9.1 Mass conservation

모든 step과 rollout interval에 대해 다음을 검증한다.

```text
N_next = N_prev + external_admitted_in - external_exited_out
mass_residual_veh = N_next - N_prev - external_admitted_in + external_exited_out
```

- 내부 connector와 urban/freeway interface flow는 source에서 정확히 한 번 차감하고 target에 정확히 한 번 가산한다.
- source command demand와 실제 admitted flow를 구분하며, 미진입 수요는 source queue에 남긴다.
- 음수 state, storage 초과, CFL 위반을 clamp해서 차량을 삭제하거나 생성하면 안 된다.
- 이 규칙의 machine-readable invariant key는 `no_clamp_delete`이며 모든 kernel test와 rollout diagnostics에 포함한다.
- floating point tolerance 밖의 infeasible state는 명시적으로 실패 또는 fallback 처리한다.

### 9.2 Required invariants

- 모든 canonical ID는 유일하다.
- 모든 reference는 존재하고 type-compatible하다.
- `length_m > 0`, `dt_sec > 0`, capacity와 occupancy는 음수가 아니다.
- 각 diverge의 active `turn_ratio` 합은 `1 +/- 1e-6`이다. 미식별 잔여 비율은 명시적 sink 또는 `unknown` commodity로 보존한다.
- 각 SG의 periodic interval은 cycle 전체를 정확히 한 번 덮으며 overlap/gap이 없다. permanent-red SG도 RED interval로 cycle 전체를 덮는다.
- conflicting movement가 동시에 permissive/protected green이 되는 경우 conflict policy가 명시돼야 한다.
- action authority 밖 SC/SG에는 command를 생성하지 않는다.
- 모든 controlled movement에는 정확히 하나의 유효 gate schedule이 있어야 한다. 하나의 SG가 여러 physical gate를 제어하는 것은 허용한다.
- boundary와 freeway interface에서 단위 변환 round-trip test를 통과해야 한다.

## 10. Runtime, Hash, Timeout, Fallback

### 10.1 Identity and stale rejection

모든 identity hash는 `canonical-json/v1` serialization 후 UTF-8 byte sequence에 SHA-256을 적용한다.

- object key는 Unicode code point 기준 오름차순으로 정렬한다.
- ID로 식별되는 entity 배열은 canonical ID 오름차순으로 정렬한다. 시간 sequence와 geometry처럼 순서가 의미인 배열은 원래 의미 순서를 보존하며 schema가 해당 ordering rule을 명시한다.
- integer와 boolean은 JSON 표준 표현을 사용하고 string은 UTF-8 JSON escaping을 사용한다.
- float는 IEEE-754 binary64 finite 값만 허용한다. `NaN`, `Infinity`, `-Infinity`를 거부하고 `-0.0`은 `0.0`으로 정규화한다.
- float text는 `canonical-json/v1`이 정의한 shortest round-trip decimal representation을 사용하며 exponent는 소문자 `e`, 불필요한 `+`와 선행 0을 제거한다. serializer/version이 다르면 cache/hash를 공유하지 않는다.
- whitespace는 삽입하지 않는다. hash 대상 schema는 optional field의 생략과 explicit `null`을 구분한다.

`canonical-json/v1` 구현은 언어 독립 test vector를 반드시 제공한다. Python serializer와 VBS/.NET serializer는 아래 golden payload에서 byte-for-byte 동일한 UTF-8 bytes와 SHA-256을 출력해야 하며, 하나라도 다르면 cross-process cache, stale check, COM actuation을 사용할 수 없다.

```text
logical value: {"text":"offset","items":["x","y"],"a":1}
canonical UTF-8 text: {"a":1,"items":["x","y"],"text":"offset"}
UTF-8 byte length: 41
UTF-8 hex: 7b2261223a312c226974656d73223a5b2278222c2279225d2c2274657874223a226f6666736574227d
SHA-256: d0151c7e66c7fc710810597fa93b171e01f18e2b668d289b9f5b60d14930e45b
```

production schema마다 optional-null, Unicode, binary64 exponent, `-0.0` normalization, ordered/unordered array 사례를 포함한 추가 golden vector set을 version control에 두고 Python/VBS 양쪽 CI에서 실행한다.

이 규칙으로 다음 SHA-256을 계산한다.

- `network_hash`: topology schema, `modi.inpx`, `.sig`, control mapping의 유효 내용을 포함
- `state_hash`: `network_hash`, `sim_time_sec`, ordered dynamic state를 포함
- `action_hash`: action schema, `network_hash`, `based_on_state_hash`, validity interval, command payload를 포함

COM actuation 전에 다음을 모두 확인해야 한다.

- expected `network_hash` 일치
- `based_on_state_hash`가 현재 actuation state와 정확히 일치. 일반 actuation에서 ancestor hash 허용은 금지한다.
- `decision_time_sec <= current_sim_time_sec < valid_until_sec`
- `valid_from_sec`와 safe activation boundary 충족
- monotonic `action_id` 또는 `decision_sequence_no`

검증 실패, partial output, 이전 CSV 재사용은 stale action으로 거부하고 원인을 기록한다.

### 10.2 Runtime budget

초기 default budget은 다음과 같다.

| 항목 | default |
|---|---:|
| `decision_target_p50_sec` | `15` |
| `decision_target_p95_sec` | `30` |
| `decision_hard_timeout_sec` | `45` |

`control_interval_sec < 60`이면 hard timeout은 `0.75 * control_interval_sec` 이하로 축소한다. timeout은 candidate worker만 종료하고 VISSIM 전체 process를 불필요하게 종료하지 않아야 한다.

fallback 순서는 다음과 같다.

1. timeout 또는 invalid output 1회: 마지막 feasible action의 command payload를 복사하되 현재 state를 기준으로 새 action을 **재발급**한다. authority, signal safety, topology, current state에 대해 다시 validate하고 새 `action_id`, `action_hash`, `based_on_state_hash`, validity, activation boundary를 부여한다. 이전 state hash나 action hash를 그대로 허용하거나 validity만 연장하면 안 된다. 재검증 실패 시 즉시 fixed plan으로 전환한다.
2. 연속 2회 실패: 영향받은 corridor/UF를 validated fixed `.sig` plan으로 전환
3. network hash mismatch, signal conflict, mass invariant 위반: 즉시 fixed plan으로 전환하고 strict action 적용 금지
4. fallback과 복구는 event log, reason code, interval count로 기록

silent fallback은 금지한다.

## 11. Gate Acceptance Criteria

### G0: Contract

- canonical units, time, offset, schema, authority, source-of-truth가 본 문서로 승인됨
- unresolved item마다 non-blocking default와 empirical selection 절차가 있음
- 구현자는 이 계약 버전과 base commit을 기록함

### G1: Canonical extraction

- 최신 `modi.inpx`의 link/lane/connector/head/SG/route reference 해결률 `100%`
- dangling connector와 invalid lane reference `0`
- 모든 source file의 SHA-256 기록
- `layx` 변경이 `network_hash`를 바꾸지 않음
- 전체 graph compile 후 influence subgraph boundary의 vehicle ownership이 명시됨
- 모든 lane group에 ordered cell이 하나 이상 존재하고 `cell_id`, 길이, 차로 수, storage, upstream/downstream reference 검증 통과
- `PlantParameters`의 topology hash 일치, 필수 parameter/provenance/uncertainty 누락 `0`
- active `progNo`와 모든 `.sig` SG timeline을 millisecond 원본에서 초 단위로 lossless 전개하고 cycle coverage 오류 `0`

### G2: Physical kernel

- golden fixture의 내부 mass residual `<= 1e-6 veh/step`
- 음수 state, storage 초과, clamp-delete `0`
- 2-link pulse travel time, 70/30 diverge, merge priority, downstream blocking fixture 통과
- urban/freeway interface flow가 양쪽에서 동일함

### G3: Signal semantics

- event overlap 계산오차 `<= 0.5 s`
- conflicting green `0`
- min-green, yellow, all-red 위반 `0`
- controlled/fixed 혼합 SC와 동일 SG 다중 gate fixture 통과
- source phase의 `.sig program offset`, controller offset, cycle epoch provenance와 active `progNo` readback 일치. `switchpoint`는 program-switch metadata로만 검증하며 phase 식에 포함하지 않음
- SG별 GREEN/AMBER/RED timeline, wrap-around, fixedstate, permanent-red fixture 통과
- pending plan이 `activation_boundary_sec`에서 SC 단위로 원자적 전환되고 phase 절단 `0`
- positive offset lag와 controller별 VISSIM COM write-read round-trip fixture 통과. 이 항목 통과 전 offset writer와 Phase 5 offset actuation은 disabled

### G4: State projection

- `vissim_oracle`에서 vehicle ownership 중복/누락 `0`
- `detector_realistic`에서 covariance, freshness, fallback flag 누락 `0`
- initial total vehicle residual은 `max(5 veh, observed vehicles의 3%)` 이하
- shared lane의 physical queue를 turn별로 중복 계수하지 않음

### G5: Model selection and calibration

- Kashani/store-and-forward와 lane-group CTM/LTM을 동일 calibration/holdout 조건에서 비교
- seed, demand profile, control policy 단위 holdout 분리
- initial target: urban one-step queue/storage error `<= 25%`; promotion target `<= 15%`
- freeway mean-speed MAPE `<= 10%`, cell count MAE `<= max(5 veh, 10%)`
- 선택한 model과 parameter version, uncertainty 범위를 기록

### G6: VISSIM parity and ranking

- 동일 initial state, demand, fixed action의 1-step 및 `H=3/H=5` open-loop 비교 완료
- forced green/offset/VSL/ramp perturbation 포함
- spillback detection F1 `>= 0.80` 초기, release 목표 `>= 0.90`
- candidate objective의 VISSIM Spearman rank correlation `>= 0.70`
- top-action pairwise ordering agreement `>= 80%`

### G7: Shadow runtime

- 실제 actuation 없이 strict plant candidate와 runtime을 기록
- `H=3`에서 decision p95 `<= 30 s`, hard timeout `<= 45 s`
- fallback interval `< 5%`, silent fallback `0`
- stale action rejection과 last-feasible/fixed fallback fault-injection test 통과

### G8: Release and staged actuation

- no-control, fixed-time, 기존 controller regression을 동일 seed/demand로 실행
- COM readback 일치율 `100%`
- 선택하지 않은 UF/SG에 대한 COM command `0`
- green-only가 다중 seed에서 no-control/fixed 및 기존 controller 대비 비열화하지 않음
- green-only 동안 native cycle/epoch/offset과 fixed/midblock SG clock 불일치 `0`
- 이후 corridor offset, parent-derived midblock, VSL/ramp/urban 통합을 각각 독립 승격
- `AGENTS.md` completion rule에 필요한 unit test, smoke test, 동일 demand 비교와 control logging을 충족

## 12. Phase Promotion Rules

- 각 phase는 관련 gate의 evidence artifact와 독립 reviewer `PASS` 없이는 다음 phase의 production path를 활성화하면 안 된다.
- 실패 결과와 fixture는 삭제하지 않고 versioned output으로 보존한다.
- calibration 결과만 좋아지고 physical invariant 또는 ranking gate가 실패하면 승격하지 않는다.
- 기존 controller path는 `Phase 4` shadow 종료 전까지 default로 유지한다.
- `Phase 5` 활성화 순서는 `green-only -> corridor offset -> parent-derived midblock -> integrated VSL/ramp/urban`이다.
- offset은 `G3`, `G6`, green-only release를 모두 통과한 뒤에만 실제 actuation한다.
- parent-derived midblock은 별도의 progression 및 spillback fixture와 COM readback을 통과한 뒤에만 활성화한다.
- emergency rollback은 validated fixed `.sig` plan이며 network reload 없이 적용 가능해야 한다.

## 13. Empirically Selected Items and Non-blocking Defaults

아래 항목은 구현 전에 완전 확정할 수 없으므로 empirical selection 대상으로 남긴다. 각 default는 실험 전진을 위한 값이지 calibration 결과를 미리 정한 것이 아니다.

| 항목 | 상태 | non-blocking default | 선택 방법 |
|---|---|---|---|
| urban cell length | empirical | `20-50 m`, CFL 충족하는 가장 긴 cell | geometry와 pulse travel-time fixture |
| `urban_dt_sec` | contract default | `1.0 s` | 1초 reference 대비 batch/subcycle parity |
| METANET step | empirical within contract | `10 s` | `5 s` 대비 accuracy/runtime benchmark |
| prediction horizon | empirical | `H=3` production candidate, `H=5` target | ranking 개선과 p95 runtime 동시 비교 |
| control horizon | empirical | `1` with move blocking | multi-step sequence의 추가 편익 검증 |
| influence subgraph radius | empirical | controlled gate에서 horizon 내 free-flow reachability + spillback upstream closure | omitted-boundary sensitivity test |
| turning ratio | empirical | INPX static route `relFlow` prior | connector flow observation으로 보정 |
| saturation flow | empirical | `1800 veh/h/lane = 0.5 veh/s/lane` prior | queue-present green discharge 회귀 |
| jam density | empirical | vehicle length + standstill gap로 계산한 topology prior | occupancy/queue-tail holdout |
| backward wave speed | empirical | model family prior | spillback onset/time calibration |
| detector estimator | empirical | conservation projection + diagonal covariance | EnKF/MHE와 holdout 비교 |
| midblock schedule | fixed until promoted | original `.sig` | Phase 5 progression/ranking/COM 검증 후 parent-derived |
| timeout budget | operational | p95 `30 s`, hard `45 s` | target hardware shadow profile |

empirical parameter 선택은 training/calibration set에서 수행하고, 승인 여부는 분리된 seed, demand profile, action perturbation holdout에서 판단한다. 기준 미달 시 default를 조정할 수 있지만 schema, unit, mass conservation, offset 부호, authority 계약은 empirical tuning으로 변경할 수 없다.

## 14. Required Evidence and Change Control

각 artifact와 runtime log는 최소한 다음 metadata를 포함한다.

```yaml
contract_version: vissim-strict-plant-g0/v3.0.0
repo_commit: git-sha
network_hash: sha256
topology_schema_version: string
plant_parameter_version: string
parameter_hash: sha256
canonical_json_version: canonical-json/v1
observation_mode: vissim_oracle | detector_realistic
state_hash: sha256
action_hash: sha256 | null
demand_schedule_id: string | null
subgraph_id: string | null
seed: int | null
sim_time_sec: float
```

다음 변경은 contract version 또는 schema version 증가가 필요하다.

- canonical unit 또는 offset semantics 변경
- entity ownership 또는 mass accounting 변경
- action authority UF 목록 변경
- topology ID 생성 규칙 변경
- fixed/controlled/derived schedule 의미 변경
- public strict plant API의 호환되지 않는 변경

단순 parameter calibration은 contract를 변경하지 않지만 `plant_parameter_version`을 증가시켜야 한다.

## 15. References

- [PTV Vissim 2025: Defining signal programs](https://cgi.ptvgroup.com/vision-help/VISSIM_2025_ENG/Content/5_Netzbearbeiten/LSA_Editor_Signalprogramme_definieren.htm)
- [PTV Vissim 2025: Fixed-time signal control](https://cgi.ptvgroup.com/vision-help/VISSIM_2025_ENG/Content/5_Netzbearbeiten/LSASteuerungsverfahren_Festzeit.htm)

## 16. Change Log

### `v3.0.0` - 2026-07-31

- 두 차례의 독립 신호/시간축 및 state/API 검토에서 발견된 P0/P1을 반영한 뒤 최종 gate review `PASS`를 받았다.
- 문서 상태를 `G0 approved`로 승격하고 실제 정본 경로에 맞춰 `N_UF_star_unit` 소유자를 `cfg.leader`로 바로잡았다.

### `v3.0.0-candidate` - 2026-07-31

- 문서 상태를 `G0 candidate v3`로 변경하고 계약 버전을 `vissim-strict-plant-g0/v3.0.0-candidate`로 올렸다.
- `N_UF_star` value/unit enum과 `N_P_star=veh`, global incident scalar, top-level initial source queue의 legacy 무손실 round-trip 계약을 확정했다.
- globally unique stock registry와 derived-view reference-only 규칙, frozen boundary trajectory/resolver, pure batch/interval API, ordered candidate batch result와 fallback 규칙을 확정했다.
- raw observation을 detector/signal/boundary typed record로 닫고 Python/VBS 공통 canonical JSON golden bytes/hash를 추가했다.
- `fixedstate`를 target command 직전 역방향 배치하는 알고리즘과 wrap/error 규칙을 확정했다.
- PTV semantics에 따라 program offset은 전체 plan의 lag, switchpoint는 program-switch 시각으로 분리하고 이전 provisional switchpoint 합성식을 제거했다.
- 현재 network의 `startTm=0`, controller offset 0, `progNo=1`에 대한 exact fixed-plan phase 식과 일반 phase 식을 확정했다.
- runtime lag를 `action_offset_lag_delta_sec`로 분리하고 다음 canonical cycle boundary crossing에서 pending plan을 원자적으로 활성화하도록 확정했다.
- cell schema에 `minimum_travel_time_sec`, `delay_buffer_steps`를 추가하고 G3 readback 전 runtime offset actuation을 계속 `NO-GO`로 유지했다.
- signal semantics의 공식 PTV Vissim 2025 근거 링크를 추가했다.

### `v2.0.0-candidate` - 2026-07-31

- 문서 상태를 `G0 candidate v2`로 변경하고 독립 재검토 전 `NO-GO`를 명시했다.
- topology에 ordered `cells` schema를 추가하고 immutable `PlantParameters` 및 parameter hash 계약을 추가했다.
- strict/legacy `ControlAction` 왕복 변환, `N_P_star`/`N_UF_star` intent 보존, `veh/h`/`veh/s`와 `km/h`/`m/s` 변환을 확정했다.
- versioned `DemandSchedule`, lane-loss/incident, source queue, legacy `DemandStep` 왕복 계약을 추가했다.
- exclusive stock ownership과 `total_vehicle_inventory()`를 정의하고 queue를 derived view, connector를 zero-storage edge로 고정했다.
- strict `step()`을 pure function으로 고정하고 legacy bridge의 mutation/time ownership을 분리했다.
- 동일 kernel의 local follower subgraph view와 frozen boundary trajectory 계약을 추가했다.
- stale fallback을 현재 state 기준의 재발급/재검증 방식으로 변경하고 ancestor hash 재사용을 금지했다.
- `canonical-json/v1`, raw observation envelope, duplicate vehicle rejection, result status enum을 추가했다.
- stage가 없는 `.sig`를 지원하는 SG별 periodic timeline, millisecond conversion, active `progNo`, source phase normalization을 추가했다.
- positive offset을 plant 내부 lag로 고정하되 G3 COM round-trip 전 offset actuation을 disabled/NO-GO로 명시했다.
- mixed controlled/fixed SC의 Phase 5 green-only 규칙, SC 전체 COM replay 승격조건, atomic pending-plan activation을 추가했다.
- short vertical queue/gate가 양의 minimum travel time과 storage를 보존하도록 강화했다.
