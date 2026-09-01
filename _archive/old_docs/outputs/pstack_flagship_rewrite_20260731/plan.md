# P-Stack Flagship 재작성 계획 (2026-07-31)

## 목표

VISSIM 어댑터(`evaluation/controllers/vissim_stackelberg_adapter.py`)에
NumSim-mine `flagship-ms-adapt-clean`(HEAD `7f10393`)의 최종 P-Stack
(**P-STACK-WU-FAITHFUL-ALLPRICE-JOINT**)을 신규 컨트롤러 모드 `pstack-flagship`으로 이식한다.

- 모델 저장소: `C:/Users/alsrj/Desktop/학술/찐찐막/Claude/NumSim-mine` (flagship-ms-adapt-clean)
- 정식 러너(기준 구현): `work/run_job.sh` → `work/run_claude_style_five_controller.py` (make_controller L244-316)
- 컨트롤러 클래스: `F1StackelbergWuMeteredController` (`src/controllers/f1_wu_faithful_follower.py:619-623`)

## 조사 결과 근거 (워크플로 wf_db2e0db9)

- 어댑터가 import하는 12개 심볼 전부 flagship에 존재·시그니처 호환 (유일 변화: `DistributedCoordinator.solve`의
  optional `leader_incumbent_obj` 추가 — 4-positional 호출 호환). NUF_PROJ 제거는 어댑터 무영향(참조 0건).
- 어댑터·src 라이브러리 모두 env-free. P-Stack env 훅(SEG13, METER_BOX, VSL_BOX, BOX_WALK, NP_PD_ITER,
  NP_BIAS, CROSS_OFF, FAR_GATE, FAR_STATE_AWARE, FAR_REAL_V, SUP_PFO, SUP_GATE, BIAS_SAMPLE/POW,
  MS_ADAPT/THR/HOLD/W)은 전부 실험 러너에서 cfg 필드 또는 controller 속성으로 번역된다. 예외:
  `NASH_SMAX`만 src 내부(env)에서 소비 (`wu_faithful_follower.py:3908-3912`, min(max_nash_iter,5) 하드캡 해제).

## 최종 P-Stack 구성 레시피 (이식 대상)

### cfg 정식 키 (build_config 단계에서 주입; base < flagship < calibration < tuning 순서)
- `mpc.leader_search_mode='continuous'`, `mpc.leader_candidate_count=49`
- `mpc.leader_value_depth=3` (러너 L244-255 — 필드/동적 여부는 구현 시 state.py 대조로 확정)
- `mpc.max_nash_iter=10` (+ 프로세스 내 `os.environ['NASH_SMAX']='10'`)
- `mpc.seg13_meter_box_veh_h=300.0` (METER_BOX)
- `mpc.seg13_vsl_box_kmh=20.0` (VSL_BOX; flagship 15는 10km/h 간격 메뉴 기준 → VISSIM DSD 20 간격 보정. tuning으로 조정 가능)
- `mpc.leader_rollout_box_walk=True`, `mpc.leader_rollout_box_walk_vg=True` (BOX_WALK/BOX_WALK_VG)
- `mpc.baseline_move_box=True` (BASELINE_BOX)
- `mpc.np_primal_dual_iters=4` (NP_PD_ITER), `mpc.np_bias_correction=True` (NP_BIAS)
- `mpc.leader_mfd_far_state_aware=True` (FAR_STATE_AWARE), `mpc.leader_mfd_far_real_speed=True` (FAR_REAL_V)
- `mpc.leader_bias_sample_pow=0.4` (BIAS_POW; 러너의 BIAS_SAMPLE 활성 방식 그대로 이식 — 구현 시 러너 L623-628 대조)
- `freeway_follower.vsl_smoothness_weight=0.0`, green/offset smoothness 0.1/0.1 (default.yaml 기본 유지)
- `freeway_follower.segment_metering_smoothness_weight`: MS_ADAPT가 per-step 주입 (아래)

### cfg.mpc 동적 속성 (dataclass 필드 아님 — 생성 후 setattr)
- `cfg.mpc.leader_skip_local_refinement=True`, `cfg.mpc.leader_rollout_early_stop=True` (OPT12;
  `stackelberg_mpc.py:910,2352` getattr 소비. tuning JSON의 mpc 섹션에 넣으면 MPCConfig(**raw) TypeError — 금지)

### controller / nash_solver 인스턴스 속성 (make_controller L244-316 이식)
- `nash_solver.segment_agents=True` (SEG13)
- `nash_solver.f1_spillback_weight=0.0`
- `nash_solver.joint_green_offset_enabled=True`, `nash_solver.ramp_offset_enabled=True`
- 가격 4채널 ON: `signal/metering/vsl/offset_price_enabled=True`, `offset_price_inner_iters=4`
- cross 2종 OFF: `green_offset_cross_price_enabled=False`, `vsl_meter_cross_price_enabled=False`
- `metering_price_delta_veh_h=300.0` + `metering_price_trust_frac=0.20` (반드시 짝)
- `price_hinge_enabled=False` (기본 유지)

### per-step 러너 로직 (어댑터에 이식 + 사이드카 영속화)
어댑터는 결정 1회마다 재기동되므로 스텝 간 상태를 사이드카 JSON
(`out-action-json 옆 pstack_flagship_runtime.json`)에 영속화한다.

1. **MS_ADAPT** (러너 L1020-1026, L1106-1116): 링크별 평균 밀도의 스텝 간 최대 변화 `_dmax > MS_THR(10)`이면
   래치를 `MS_HOLD(5)`스텝으로 세팅. 래치 중 `segment_metering_smoothness_weight=0.0`, 평시 `MS_W(0.013)`.
   첫 스텝(prev 없음)은 러너와 동일 동작(구현 시 대조). 기본값은 플래그십 채택값(thr10/**hold5**/w0.013 —
   코드 기본 hold3 아님)으로 하드코딩, tuning `adapter.flagship.ms_adapt`로만 조정.
2. **FAR_GATE=3** (러너 L1001-1099): 폐쇄 예보 OR capdrop 실측(실배출 < 0.95×용량, 히스테리시스 래치)로
   `cfg.mpc.leader_mfd_far_enabled` per-step 개폐. VISSIM엔 폐쇄 예보 입력이 없으므로 사실상 mode 2로
   동작함을 주석·문서에 명시.
3. **SUP_PFO=1 + SUP_GATE=fargate** (러너 L925-959, L1151-1176): far 게이트 OFF 스텝에서 링크-PFO 에뮬레이션
   해(cfg 사본: seg13 박스 None + baseline_move_box=True)를 같은 상태에서 계산, 공통 V(h스텝
   `run_coupled_interval` TTT + `mfd_far_cost_to_go`)로 채점해 승자 집행. far 게이트 ON 스텝은 감독자 OFF.
4. **post_guard 관계**: `pstack-flagship` 모드에서 `apply_post_guard_safety_evaluation`의 PFO-baseline 폴백은
   기본 OFF (SUP_PFO가 대체; 이중 개입 방지). ramp_release_guard·actuation guard(VISSIM 안전장치)는 유지.

### 유지·보존 (건드리지 않음)
- CLI 시그니처, state json 해석, action json/csv 스키마(phase-axis 매핑 포함), extends 로더,
  detector/control mapping 소비부, 예외 시 fallback_fixed, 기존 모드 전부(stackelberg, wu*, pfo, diagnostic-*)
- 캘리브레이션 파이프라인 5종(monkeypatch 포함) — flagship 모드에서도 동일 적용
- install_vissim_terminal_cost_objective — flagship 모드에도 동일 래핑(VISSIM측 터미널 보정)
- **플랜트 env 복사 금지**: run_job.sh의 VFREE/RHO_CRIT/TAU_H/NU_BASE/KAPPA/MERGE_DELTA/FW_BUFFER/TERM_ZG는
  수치실험 플랜트 물리. VISSIM에서는 캘리브레이션(v_free 120/rho_crit 30/cap 6900)이 예측모델 기준.

## 결정 사항 (가정)

| # | 결정 | 근거 |
|---|---|---|
| 1 | 신규 모드 추가(전면 리라이트 아님), 기존 계약 보존 | 기존 비교군·재현성 보존, surgical change |
| 2 | 대상: SC1 인터페이스 real-world + 8-seg (topology-agnostic 모드) | 19sc/15core는 F1 follower 수용성 미검증 + dual-ring 매핑 미확정 → 기존 DistributedCoordinator 유지 |
| 3 | SUP_PFO가 post_guard PFO-fallback 대체 | flagship 거동 기준, 이중 폴백 방지 |
| 4 | VSL box 기본 20 | vissimdsd 메뉴 [80,100,120] 20 간격에서 15면 VSL 동결 |
| 5 | MS_ADAPT 기본 thr10/hold5/w0.013 + tuning 노출 | 60s 주기 재보정(스케일 3배 차이)은 후속 A/B |
| 6 | repo-root 기본: `NUMSIM_REPO_ROOT` env 우선 → NumSim-mine 폴백 | TRLAB 경로는 이 머신에 없음 |
| 7 | NASH_SMAX=10을 모드 진입 시 프로세스 내 env 설정 | 1회 실행 프로세스라 부작용 없음 |

## 단계

1. **어댑터 수정** — DEFAULT_REPO_ROOT 교체, `pstack-flagship` 모드(컨트롤러 구성 + per-step 로직 + 사이드카), post_guard 게이트
2. **tuning JSON** — `evaluation/configs/real_world_modi_pstack_flagship_20260731.json` (vissimdsd 체인 extends) + 8-seg용 스모크 tuning
3. **검증 스크립트** — `scripts/test_pstack_flagship_adapter.py`: 구성 검증(속성 전수)·MS_ADAPT 래치 단위검증·합성 state 스모크(신규/기존 모드 회귀)
4. **실행 검증** — 테스트 전부 PASS + 기존 stackelberg 모드 무회귀 확인

## 후속 (이번 범위 밖)

- MS_ADAPT/FAR_GATE 파라미터 60s 주기 재보정 sweep, VSL box A/B (vsl_active_steps)
- flagship 예산(continuous/49/depth3)의 60s wall-time 실측, 초과 시 CAND/depth 하향 운영점
- 19sc/15core distributed 경로의 flagship화 타당성 검토
- repo 교체(0e07c1c→7f10393)에 따른 1-step 예측감사(audit_calibration) 재적합
