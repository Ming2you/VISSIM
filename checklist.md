# 체크리스트 — 플랜트 충실도 검증 (2026-08-05 갱신)

## 현재 국면

**플랜트가 VISSIM 네트워크를 얼마나 정확히 모사하는지 확정한다.**
G6 채점도 캘리브레이션도 그 아래가 성립해야 의미가 있다. rollout 이 틀린 네트워크 위에서
돌면 lever 를 아무리 움직여도 해석이 불가능하다.

Codex 독립 감사를 요청해 둔 상태다 — [`PLANT_FIDELITY_AUDIT_REQUEST.md`](PLANT_FIDELITY_AUDIT_REQUEST.md).
결정 근거는 `context-notes.md`(시간순), 저장소 안내는 `README.md`.

**다음 국면 = P-Stack 컨트롤러 얹기.** 위가 끝나야 시작한다.
MPC 가 후보를 고르는 근거가 곧 G6 가 재는 그 서열이고, 서열이 틀린 축 위에서 폐루프를
돌리면 컨트롤러가 확신 있게 틀린 방향으로 민다.

---

## 대기 중

- [ ] **Codex 플랜트 충실도 감사 결과** — 산출 예정 `reports/plant_fidelity_audit.md`

---

## 열린 항목 (우선순위 순)

### P1 — 모사 정확도의 근간

- [ ] **모니터 26개 SC 가 항상 녹색.** movement 의 `phase=''` 이라
      `urban_queue_model._phase_green_fraction`(541행)이 1.0 을 반환한다.
      movement 1,422개 중 672개(47.8%), 관측 차량의 40.7% 가 여기 걸린다.
      최종 목표인 "통제 교차로 TTT 절감 대 인접 비통제 TTT 증가" 비교가 **원리적으로 막힌다** —
      인접이 빨간불이 없으면 증가분이 안 잡힌다.
      방향: 비통제 노드에 플랜트 fixed-time 시간표(phase + 고정 녹색 + offset)를 심되
      리더가 못 바꾸게 한다.
- [ ] **미드블록 offset 슬레이빙** (사용자 요청, 설계 확정·미구현).
      `offset(mid) = offset(상류 통제 신호) + 주행시간`, 녹색 배분은 고정(보행 현시 보호).
      재료는 다 있다 — `link_upstream`, 유도 길이 82.7 km, VBS 의 `sigOffset`·`RW_SIGNAL_SCS`.
      제약: 미드블록 주기가 간선과 같아야 한다(`major + minor` 합).
      미드블록 9개(배정 leg 가 한 축뿐인 SC): 18, 3, 10, 17, 9002, 9003, 2, 9001, 4.
- [x] **실시간 링크 속도 관측** (N3-1b, 2026-08-10). 앞 문장의 "VBS 가 안 내보낸다" 는 낡았다 —
      `link_speeds_kph` 는 이미 나오고 있었고, 막힌 곳은 **상태에 안 실리는 것**이었다.
      `TrafficState.urban_link_speed_kph` 신설 + 어댑터 반영 + `_link_delay_steps` 가 사용.
      관측이 없으면 전역 상수로 폴백해 기존과 비트 동일.
      - [ ] **남은 것 — vendor 재스냅샷.** 실런 기본 모델 저장소가 `vendor/NumSim-mine`
            (해시고정)이라 그쪽 `TrafficState` 에는 아직 필드가 없다. 어댑터는 `hasattr`
            가드로 조용히 건너뛴다. 재스냅샷 전까지 **실런에서는 여전히 전역 상수**다.
- [ ] **`boundary_in` 큐 122.7대를 목적함수에 넣을지** — 설계 판단.
      들어오는 차가 플레이어 approach 에 서 있는데 리더가 안 센다.
      넣으면 포착률 76.8 → 약 89%. 목적함수 정의 변경이라 G6 에 직접 영향.

### P2 — 컨트롤러가 돌기 위한 조건

- [ ] **H=1 지평 퇴행** — rho 0.4378, pairwise **0.000** (H=5/10/15 는 0.985/0.921/0.862).
      MPC 는 첫 구간만 집행하므로 폐루프를 좌우하는 지평이 바로 여기다.
      매크로 평균 0.8015 가 이 퇴행을 흡수하고 있다.
- [ ] **solve 시간이 제어주기를 넘는다** — v7 77.0s / v8 60.6s > 60s (v6 15SC 는 17.0s).
      프로파일: `_maybe_refresh_signal_prices` 가 **77%**(전역 롤아웃 83회),
      실제 MPC 는 23%. **후보 수를 줄이는 방향으로는 못 푼다** — 가격 갱신 주기가 레버.
      부수 여지: `_phase_green_fraction` 612만 회 호출 → (phase, step_idx) 메모이제이션은
      순수 항등이라 안전.

### P3 — 재채점

- [ ] **G6 전면 재채점.** 아래 넷이 쌓여 과거 점수와 비교 불가.
      ① 어댑터 투영(`storage_fraction=1.0`) ② `NS_AXIS` 정정(movement 20.4% phase 이동)
      ③ 램프 큐 램프별 정규화(압력 +42.9%) ④ 플랜트에 SC2001~2005 추가
- [ ] **G6 게이트가 FAIL** — `top_action_pairwise` 0.75 < 0.80
- [ ] **spillback F1 = 1.000 은 인공물** — TP=72, TN=FP=FN=0 상수 라벨이라 정보량 0.
      `shadow.py:255-271` 이 전부 음성일 때만 NOT_EVALUATED 를 내고 전부 양성이면 통과시킨다.
- [ ] **인접부 TTT 분해 배선** — `uncontrolled_node_movement_queue_veh` /
      `_storage_occupancy_veh` 가 정의만 있고 소비처가 0. P1 첫 항목과 한 묶음.

### P4 — 위생

- [ ] 테스트 스위트가 30분 timeout 에도 85%(250/289)에서 안 끝난다. 테스트당 평균 13초.
- [ ] 기존 테스트 실패 15개 — `test_forecast_awareness` 5, `test_constraints` 4,
      `test_post_analysis` 2, `test_segment_local_plant` 2, `test_demand_scenarios` 2.
      이번 작업과 무관함은 되돌리기로 확인했다.
- [ ] `.gitignore` 가 `*.err` 를 제외한다. 오늘 런 전멸의 원인을 찾은 게 그 파일이었다.
- [ ] G5 셀 게이트 임계가 플랜트 잡음 바닥 아래 (cell MAE 22.83 대 재현성 22.01)
- [ ] SC1004 역할 재분류 — F측 인터체인지인데 일반 도시부. 분류기가 커넥터 한 홉만 본다.

---

## 완료 (2026-08-10) — N4-3 / N4-4

### N4-3. N현시 녹색분율 배선

- [x] `evaluation/controllers/native_phase_green.py` 신설 — 실 `.sig` 의 SG 녹색창에서
      movement 별 native 배분(share)을 뽑는다. 분모는 축(=모델 phase)의 녹색 **합집합**이라
      share ∈ (0, 1] 이 구조적으로 보장된다(clamp fail-open 없음)
- [x] `install_monitor_fixed_signal_runtime_patch` 가 controlled 15 SC 도 컴파일 대상에
      넣는다 — 스케줄 26 → **41개**
- [x] phase 가 있는 movement 도 native 배분을 곱한다. 배분이 정확히 1.0 이면 표에 담지 않고
      **원본 호출을 그대로 반환** → N=2 비트동일이 구조적으로 성립
- [x] N=2 비트동일 — 합성 2현시 `.sig` 로 배분이 전부 1.0 임을 보이고,
      (g1, g2, offset, urban_step_index) 800점 격자에서 `==` 로 단언
- [x] SC1001 8개 SG 분율이 실측과 1e-9 이내 일치
      (WBL/EBL 24/150, EBT/WBT 45/150, NBL 29/150, SBT 40/150, SBL 18/150, NBT 51/150)
- [x] 미해결 명시 계상 — 조용히 통과시키지 않는다.
      실 config 698 movement 중 **scaled 229 / unit 165 / unresolved 304**
      (`no_signal_group_mapping` 282, `axis_mismatch` 22), 최소 배분 0.25
- [x] 되돌림 증명 — 곱셈을 빼면 `test_patched_path_applies_the_native_share_to_a_controlled_movement` FAIL

### N4-4. 조용한 폴백 제거 (fail-closed)

- [x] `MonitorFixedSignalPatchError` 신설. 네트워크 파일 부재 / 컴파일 예외 /
      monitor 노드 스케줄 부재 / 런타임 스케줄 None 네 곳이 전부 예외다
- [x] 정당한 "대상 없음"(uncontrolled·signals 공집합)만 `monitor_fixed_signal_patch_skip_reason`
      = `no_target_nodes` 로 건너뛴다
- [x] 되돌림 증명 — 네 게이트를 조용한 반환으로 되돌리면 fail-closed 테스트 4건 FAIL
- [x] 패치 대상 모듈 0개도 예외(무음 no-op 방지). 실 config 에서 5개 패치됨

### 남은 것 (N4-3 PASS 기준 미달)

- [ ] **unresolved 304건(43.6%)이 아직 2현시 원본으로 떨어진다.** N4-3 의 PASS 기준
      "native production 에서 scalar-cycle fallback 0" 은 아직 아니다. 원인은 신호두의
      `lane` 이 링크 단위라 한 접근로의 직진·좌회전이 같은 SG 집합으로 묶이고,
      경계 유입(`in_SC*_*`) 은 아예 링크 매핑이 없기 때문이다 — **N4-2 가 풀 몫**이다
- [ ] `axis_mismatch` 22건 — SC5 처럼 접근로 leg 가 NS 인데 신호두가 EB 계열 SG 를 가리킨다.
      모델 phase 배정 규칙과 실제 신호두 귀속이 어긋나는 실제 불일치다
- [ ] **모델 ↔ 플랜트 비대칭.** 러너는 controlled SC 를 여전히 이름 규칙 2현시로 구동한다
      (`run_real_world_stackelberg_controller.vbs:1298-1312 SignalStateForGroup`).
      즉 지금은 모델만 N현시 배분을 쓴다. 액추에이션 쪽은 **N4-5** 가 닫는다

---

## 완료 (2026-08-05)

### 분할·귀속

- [x] 링크를 **하류 첫 대상**으로 분할 귀속 — 신호 정지선 / 고속도로 / 종단.
      1,205 = 플레이어 957 + freeway 22 + 출구 226. 중복 0, 누락 0
- [x] **커넥터 포함** — VBS 가 urban 분모에 넣으므로. 커넥터를 그래프 **노드**로 넣어야
      BFS 가 안 끊긴다(안 그러면 836개가 전부 출구로 분류됨)
- [x] **상류 SC** 를 커넥터 그래프 역방향 BFS 로 직접 유도(`link_upstream`, 714/957).
      방위 조인은 63% 였다 — 인접표와 배정이 방위를 따로 계산해 굽은 링크에서 어긋남
- [x] 일반 링크 8개가 하류 고속도로인데 도시부 approach 로 세던 것 발견·수정

### 실측 유도

- [x] 저류 용량·길이를 기하에서 유도 — jam density **140.5 veh/km/lane**(정체 표본 177개 p90).
      저류 182개(내부 114 + 경계 68), 82.7 km. 인접표 94쌍과 대조 85개 일치
- [x] 램프 큐 상한을 커넥터 기하에서 유도 — 93.0~145.9 (상수 180 대체).
      `scripts/derive_ramp_queue_capacity.py` 신설
- [x] 램프 큐를 **램프별로 정규화** — 스칼라가 리더 압력항만이 아니라 팔로워 큐 상한 =
      물리를 지배하고 있었다. `NetworkConfig.ramp_queue_cap()` + 14군데 적용.
      매핑이 비면 스칼라 폴백이라 기존 비트 동일

### 라우팅·투영

- [x] `link_to_origins` 를 `SC{상류}_to_SC{owner}` 로 **권위 라우팅**.
      기존은 방위 4개 살포라 제어 가능한 approach queue 651대가 경계 sink 로 샜다
- [x] 어댑터 — movement 매핑 없는 링크의 큐분이 증발하던 것 회수(882개 링크, 1,415대)
- [x] 고속도로 본선(링크 2·26, 688대)이 도시부 저류로 유입되던 것 차단.
      `internal_link_members` 가 경로 기반이라 본선을 멤버로 넣고 있었다
- [x] 전 링크 관측 — `link_counts` 175 → **1,207개**. VBS 코드 변경 불필요(허용목록이 생성물)

### 모델 코어

- [x] **`NS_AXIS` 부호 반대** 정정 — 실측 축각으로 현행이 맞는 대각 leg 0개, 뒤집으면 76개.
      movement 287개(20.4%)가 phase 이동. 4방위 격자는 비트 동일
- [x] `scripts/verify_phase_axis_assignment.py` 신설 — 123/123 PASS,
      되돌리면 34.5% FAIL(회귀 검증까지 확인)

### 플랜트

- [x] 신규 SC2001~2005(UF13/14 북쪽) 반영 — active 37 → 42, 모델 41노드
- [x] 램프미터 신호두 램프 끝 이동(사용자) 확인 — 커넥터 ID 불변이라 설정 유효
- [x] 정적 경로 1157-3 복구(사용자) — 이것 하나로 시뮬이 시작 직후 중단·리셋되고 있었다

### 지표

- [x] 포착률 — 도시부 **76.8%**(목적함수) / 96.3%(투영), 고속도로 **100.0%**.
      경과 20.2 → 40.4 → 50.7 → 83.5 → 76.8 (마지막 하락은 네트워크 변경)
- [x] `verify_urban_topology_merge.py` 에 고속도로 포착률과 귀속 기준 분모 추가

### 문서·커밋

- [x] `PLANT_FIDELITY_AUDIT_REQUEST.md` 작성 — 감사 질문 15개, 미해결 10개, 우리가 틀린 방식 5개
- [x] `vendor/NumSim-mine/` 모델 소스 스냅샷 동봉 — 클론 하나로 감사 가능
- [x] `README.md` 갱신 — 구 8-seg 가상격자 서술이 현행인 것처럼 남아 오도하고 있었다
- [x] 커밋·푸시 (`pstack-flagship-controller`)

---

## 폐기 (이번 국면에서 불필요 판정)

- ~~램프 후보 재설계 (V3 후보셋, 그룹율 격자)~~ — 램프 수요는 충분하다.
  플랜트 온램프 유입 4,436 veh/h, 본선 감소는 오프램프 유출(6,681)이 더 크기 때문이었다.
- ~~"모델이 온램프 수요를 3.4배 과소추정"~~ — 재캘리브레이션으로 해소(rho +0.714, G5 링크 MAPE PASS)
- ~~도시부 route design 을 IC 방향으로 변경~~ — 위와 같은 이유로 불필요

---

## N4-5 / N4-6 (2026-08-10)

### N4-5 — action 스키마 N현시

- [x] `evaluation/controllers/signal_group_plan.py` — 축 녹색 시간의 단조 재매개화 (TDD 13/13)
- [x] `scripts/derive_signal_group_actuation_plan.py` — inpx supplyFile2 에서 계획 생산 (TDD 6/6)
- [x] `outputs/signal_group_actuation_plan_v3.json` — SG 136 / 창 118 / 영구적색 20 / 충돌쌍 312
- [x] `..._sgplan.vbs` — 기대 SG 집합·충돌 쌍을 config 로 (행이 자기 인증하지 않게)
- [x] 어댑터 `signal_group_action_rows` — 13열 헤더 불변, `kind=signal_sg` 행 (TDD 6/6)
- [x] 러너 — 계획 구동 / 전량 거부 / 이름 규칙 폴백 계상 (cscript 실행 TDD 8/8, 되돌림 증명 4)
- [x] 러너 시작 게이트 `ValidateSignalGroupPlanCoverage` — VISSIM SG 집합과 계약 완전 일치
- [x] 이벤트 스케줄러가 축 **안의** SG 경계에서도 멈추게 수정 (발견한 실제 버그)
- [ ] 실 런에서 `SIGNAL_NAME_RULE_FALLBACKS = 0` 확인 — **런 필요**
- [ ] core15n41 외 generated config 의 `_sgplan.vbs` 생성 — 필요할 때

#### N4-5 잔여 — 주기 분모 (2026-08-10)

- [x] 회계 조사 — 예산이 스칼라 주기에만 매여 있어 native 주기를 채우면 140/150/160/170 에서
      암흑시간 20/30/40/50 s, 100 에서는 두 현시 합 1.12 (`src/tests/test_cycle_green_budget_accounting.py`, 10/10)
- [x] `evaluation/controllers/plant_cycle.py` — 러너 원문에서 clearance 상수를 읽어 주기 식 단일화
- [x] 생산 tuning `lost_time = 10.0` — 모델 주기 = 플랜트 주기 (TDD 11/11, 되돌림 증명 4건 FAIL)
- [x] write clamp `[5,90]` 을 `plant_cycle` 단일 출처로, 리더 상자에서 더 이상 물지 않음
- [x] g/C 과대 **+1.667% → 0.000%** (실 캡처 액션 57/57 기준 +3.333% → 0.000%)
- [ ] `lost_time` 8 → 10 이 서비스율 -1.8% 로 TTT 에 미치는 영향 — **런 필요**
- [ ] 예산면 밖 진단 arm 의 주기 불일치 — 상류 `_phase_green_fraction` 설계 결정 필요
- [x] `cycle_length_by_signal` 은 **비운 채로 둔다** — native 는 제어 런에서 재생되지 않는다

### N4-6 — 신호 timing oracle (D-core)

- [x] `evaluation/controllers/signal_timing_oracle.py` — 게이트 10개 + valid-interval 계약 (TDD 20/20)
- [x] `scripts/verify_signal_timing_oracle.py` — 실 런 산출물 / 계획 단독 두 경로 (TDD 4/4)
- [x] run-free 판정: plan_self_conflict PASS · cycle_wrap PASS · quantization **FAIL 0.990 s**
- [x] transition_time_error 는 PASS 가 아니라 **BLOCKED** (readback 격자 1 s > 게이트 0.5 s)
- [x] 표본 0 을 "위반 0"으로 읽지 않게 fail-open 구멍 막음 (NOT_EVALUATED)
- [ ] readback 5개 게이트 — **실 런 필요** (`decisions/signal_readback.csv` + signal_sg 행이 있는 action 로그)
- [ ] 최소녹색 권위 결정 — `.sig` 의 intergreenmatrices 가 비어 있어 VISSIM 이 선언하지 않는다

### N4-7 — offset 승격 잠금 (D-offset-enable)

- [x] offset 현황 추적 — 모델 최적화(`urban_follower._offsets` / offset_price / joint_green_offset)
      부터 `control.offsets` → action CSV `offset` 열 → 러너 `sigOffset` → `FMod(simSec + offset, cycle)`
      까지. **잠금 이전에는 production 경로가 열려 있었다**
- [x] `evaluation/controllers/offset_promotion.py` — 삼중 잠금을 증거 산출물에서 판정 (TDD)
- [x] 어댑터 `write_action_csv(offset_writer=...)` 기본값 `intent_only` — 의도는 action JSON 에만
- [x] test-only writer — 격리 harness 가 config 로 선언, **강제 arm 만** 통과
- [x] 선언 없이 강제 arm 이 오면 0 으로 뭉개지 않고 런을 세운다 (`guard_forced_arm`)
- [x] 러너 두 번째 자물쇠 `RW_OFFSET_WRITER` + `OffsetPromotionRejectReason` — 전량 거부 (cscript TDD)
- [x] N9 행렬 `LEVER_STATUS/LEVER_WRITER["offset"]` 를 잠금 판정에서 **유도** (손으로 안 적는다)
- [ ] 증거 산출물 3개 — `outputs/offset_promotion_{d_core,n9_offset_effect,n8_4_runtime}.json`.
      D-core 가 BLOCKED 라 아직 하나도 못 만든다
- [ ] g6 offset arm(`diagnostic-signal-offset30/60`) 을 돌리려면 그 config 가 test-only 를 선언해야 한다

## N10 — 감사 게이트 (2026-08-10)

- [x] 상태 어휘에 `BLOCKED` 추가 — `NOT_EVALUATED` 보다 나쁘고 `--strict` 에서 exit 2
- [x] 게이트 범주표 `GATE_CATEGORIES` — 게이트 28개 전부 9개 범주에 분류, 미분류는 테스트가 잡는다
- [x] 신호 3개 — `signal_timing_canon` / `signal_actuation_plan` / `movement_signal_group_map`
- [x] 토폴로지 1개 — `canonical_topology` (정본 토폴로지의 `inpx_sha256` 이 감사 대상 망과 일치)
- [x] 질량 1개 — `mass_conservation` 을 투영 게이트에서 분리
- [x] 캘리브레이션 1개 — `stock_calibration` (N6 `validate_physical_stock_calibration.validate` 위임)
- [x] 짝동역학 2개 — `paired_dynamics` (N9-4 GATES 표) / `spillback_detection` (혼잡 표본 미달 = BLOCKED)
- [x] 순위 1개 — `gradient_ranking` (Spearman 0.70 / top pairwise 0.80 을 점추정·부트스트랩 하한 둘 다)
- [x] 승격 1개 — `promotion_readiness` (세 demand × holdout 시드, 저수요 면제는 spillback 만)
- [x] 되돌림 증명 2건 — 정본표 불일치 검사 제거 / 저수요 면제를 전 지표로 확대
- [ ] `stock_calibration` · `paired_dynamics` · `spillback_detection` · `gradient_ranking` ·
      `promotion_readiness` 를 실제로 판정 — **실 런 필요** (N5/N6/N9 산출물이 아직 없다)
- [ ] `signal_timing_canon` FAIL 해소 — SC5/6/11/12 에서 `signal_group_timing_v3.json` 의
      `.sig` 배정이 inpx supplyFile2 와 다르다. 표 생산자(`derive_signal_group_timing.py`)의 몫
- [ ] `run_plant_fidelity_matrix.ps1` 의 `--required-gate` 목록에 N10 게이트 편입 — 실 런 프로필이 정해진 뒤

## A — `state.demand` 계약 고정 (2026-08-11)

- [x] 세 필드 전수 추적 — 러너는 **지점당 평균**(vbs:2949-2953), 어댑터는 **원소당 값**(adapter:2813-2818)
- [x] freeway 도 같은 구조임을 확인 — 유입 2 vs 링크 2 라서 총량이 **우연히** 맞는다(배율 1.0000)
- [x] ramp 는 러너가 리터럴 0 (vbs:2123) + 실 캘리브레이션에 램프 예측 3경로 전부 없음 -> 도착 0
- [x] `boundary_out_links` 는 외생 도착으로 **안 쓰인다** — 주입 경로가 전부 `kind=="boundary_in"` origin
- [x] 다만 `stackelberg_mpc._forecast_demand_metadata` 가 전 키를 합산 -> 진단값만 2.0171배 부풀음
- [x] 계약 문서 `evaluation/controllers/demand_contract.md`
- [x] 검사 `tests/test_demand_contract.py` — 불변식 6 PASS(전부 되돌림 증명) + 알려진 불일치 2 FAIL
- [ ] 3.66배 해소 — **이번 회차 범위 밖**. 격자 재정렬(작업 B 후속)과 함께 결정한다

## B — 도시부 수요 게이트 앵커링 (2026-08-11)

- [x] 어디를 고칠지 결정 — **러너가 게이트별 벡터를 state 에 쓴다**(어댑터가 inpx 를 보지 않는다).
      근거: `scale`·역할 배수는 런타임에만 알 수 있고, state JSON 이 실 런의 유일한 계약면이다
- [x] 조인 대장 `evaluation/real_world_modi_inventory/urban_input_gate_map_20260811.csv`
      + 생성기 `scripts/derive_urban_input_gate_map.py` (이름 접미사 정본, 무명은 기하)
- [x] 러너 — `LoadUrbanInputGateMap` / `AddUrbanGateDemand` / `UrbanGateDemandJson`,
      state 에 `urban_volume_vph_by_gate` + `urban_unmapped_volume_vph` + `urban_internal_volume_vph`
- [x] 러너 fail-closed — 대장이 이 망의 유입을 하나도 모르면 `WScript.Quit 2` (스칼라 폴백 = 3.66배)
- [x] 어댑터 — `by_gate` 를 그대로 게이트값으로, `boundary_out` 은 0, 모르는 게이트는 `ValueError`
- [x] 도시부 주입 **3.6562배 → 0.8620배**(입구 기준). 모자란 0.1380 은 격자에 없는 입구 3곳
- [x] 진단 부풀림 2.0171배 소멸 (t=1800 s: 진단 합 == 주입 합 == 14,563.6 veh/h)
- [x] 검사 — 불변식 13 PASS + 생산자 cscript 2 + 생성기 9, 되돌림 증명 6건
- [x] dummy 10개(peak 2,226 veh/h)는 경계에서 완전히 빠짐 → `urban_internal_volume_vph` 로만 남음
- [ ] 입구 3곳(`SC1004_SW` 1,400 / `SC1004_SE` 849 / `SC13_S` 81) — 격자 재생성의 몫
- [ ] freeway 앵커링 — 지금은 유입 2 == 링크 2 라 총량이 맞지만 **방향 비대칭은 못 잡는다**(범위 밖)
