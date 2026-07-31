# P-Stack Flagship 재작성 컨텍스트 노트

작업 중 내린 결정과 근거를 시간순으로 기록한다. (다음 세션이 재도출 없이 이어받기 위함)

## 2026-07-31 조사 단계 (워크플로 wf_db2e0db9, 에이전트 5)

- **"PFO 5셀 전승"의 의미 확정**: 코드 상속이 아니라 성적(5셀 windowed TTT 5/5 승, 합계 −468.2).
  코드상 PFO 동작을 집행하는 경로는 SUP_PFO 감독자(공통 V 채점)가 별도로 존재. → 재작성은
  "MS_ADAPT + SUP_PFO 포함 flagship 전체 운영점" 이식으로 정의.
- **어댑터-flagship API 전수 호환 확인**: 12개 심볼 시그니처 일치. 유일 변화는
  DistributedCoordinator.solve의 optional leader_incumbent_obj (positional 호출 호환).
  NUF_PROJ 삭제 무영향(어댑터 참조 0건). → 어댑터 구조 자체는 재사용, 모드 추가 방식 채택.
- **P-stack이 어댑터에서 도달 불가함을 확인**: 어댑터 stackelberg 모드는 StackelbergMPCController
  (+ tuning에 따라 DistributedCoordinator follower). flagship 최종 클래스
  F1StackelbergWuMeteredController + SEG13 + 가격 채널 + per-step 러너 로직은 존재하지 않음.
- **MS_HOLD 함정**: 코드 기본 3 vs 플래그십 채택 5. 어댑터에는 5를 하드코딩(튜닝으로만 하향).
- **NASH_SMAX**: src 내부에서 env로만 소비(min(max_nash_iter,5) 하드캡 해제). cfg 승격은 NumSim 쪽
  기준선 변경이라 보류 — 어댑터가 모드 진입 시 os.environ으로 설정(1회 실행 프로세스라 안전).
- **플랜트 env 복사 금지 원칙**: run_job.sh의 VFREE 115/RHO_CRIT 31.5 등은 수치 플랜트 물리.
  VISSIM 예측모델은 VISSIM 캘리브레이션(v_free 120, rho_crit 30, cap 6900)이 기준.
  단 METANET 동역학 파라미터(tau/nu/kappa/delta_merge)는 flagship 예측 물리의 일부 —
  기존 audit_calibration 절차로 재적합하는 후속 작업 필요.
- **VSL box 비호환 발견**: flagship VSL_BOX=15는 10km/h 간격 메뉴 기준. vissimdsd 체인의
  vsl_set=[80,100,120](20 간격)에서 ±15 박스는 이웃을 못 담아 VSL 동결 → 기본 20으로 보정하고
  tuning 노출, A/B(vsl_active_steps)는 후속.
- **결정 주기 차이**: flagship 수치실험 180s vs real-world 60s. MS_THR(|Δρ| 스케일)·MS_HOLD(실시간
  길이)가 3배 어긋남. 1차 이식은 flagship 값 그대로(재현성 우선), 재보정 sweep은 후속.
- **19sc/15core 제외 결정**: F1WuFaithfulFollower가 19-SC(84 movements) urban을 처리할 수 있는지
  미검증 + dual-ring 플레이어↔SC 매핑 미확정(outputs/real_world_distributed_signal_todo_20260731.md).
  distributed 경로는 기존 DistributedCoordinator 유지, flagship화는 별도 타당성 검토 후.
- **사이드카 영속화 채택**: 어댑터는 결정 1회마다 재기동 → MS_ADAPT/FAR_GATE 래치·직전 밀도를
  out-action-json 옆 pstack_flagship_runtime.json에 저장. previous-action-json metadata 방식은
  액션 스키마 오염이라 기각.
- **post_guard 관계**: SUP_PFO가 같은 역할(더 나은 baseline 집행)의 flagship 정식 메커니즘이므로
  pstack-flagship 모드에서 post_guard PFO-fallback 기본 OFF. no-control 안전망 여부는 tuning으로.

## 2026-07-31 구현 단계

구현 에이전트가 어댑터·tuning·테스트를 작성한 직후 세션 한도로 중단 → 이후 검증은 직접 수행.

### 러너 원문 대조에서 plan.md와 달랐던 사실 (러너가 정답)

- **leader_search_mode = `grid`** (plan.md는 `continuous`라고 적었음). 러너 `build_cfg`(L76-84)가
  `"leader_search_mode": "grid"`를 명시 강제한다. default.yaml 기본이 continuous인 것과 무관하게
  플래그십 런은 grid로 돌았다. → 어댑터도 grid.
  부수 효과: BIAS_SAMPLE(Halton 상단 warp)은 continuous 샘플 경로에서만 발화하므로 grid에서는
  사실상 불활성. 러너와 동일하게 이식만 해 두고, tuning으로 continuous 전환 시 그대로 발화한다.
- **horizon_steps / control_horizon_steps = 3** (러너는 미설정 → default.yaml 3 유지).
  어댑터 base는 실시간 예산 때문에 1로 축소해 뒀으므로 flagship 층이 3으로 복원한다.
- **forecast 길이 = horizon_steps + max(0, leader_value_depth)** (러너 L1044).
  어댑터는 `cfg.mpc.horizon_steps`만 넘기고 있었다 → flagship 모드에서만 depth를 더한다.
  이걸 놓치면 leader value-depth rollout이 forecast 끝을 넘어 잘린다.
- **leader_value_depth=3**은 MPCConfig 정식 필드(state.py:358, 기본 0)이고 default.yaml에 없다.
  러너 L252-255가 "env 없고 cfg가 0이면 3"으로 채운다 → cfg override로 3 주입이 등가.
- **OPT12 2종(leader_skip_local_refinement / leader_rollout_early_stop)은 MPCConfig 필드가 아니다**
  (state.py grep 0건, stackelberg_mpc가 getattr로 소비). tuning JSON의 mpc 섹션에 넣으면
  `MPCConfig(**raw)` TypeError로 즉사하므로 반드시 cfg 생성 후 setattr.

### 확인된 전제 (조치 불요)

- `seg13_release_floor_frac=0.65` — δ=300/trust=0.20 짝의 선결조건(러너 L310-311 주석). run_job.sh에
  RELEASE_FLOOR env가 없는데, `WuFaithfulFollower.__init__`의 클래스 기본값이 이미 0.65라 자동 충족.
- SUP_PFO 인스턴스는 **segment_agents를 켜지 않는다** — 러너에서 SEG13 블록(L829)이 본 컨트롤러에만
  적용된 뒤 L944에서 PFO를 새로 만들기 때문(주석 L929-930이 의도 명시). 어댑터도 bare
  `WuFaithfulFollower(sup_cfg)`로 동일.
- SUP_PFO용 cfg 사본은 per-step 변형(FAR_GATE/MS_ADAPT) **이전** 스냅샷이어야 한다. 러너는 루프 밖
  1회 deepcopy, 어댑터는 매 결정마다 변형 전 deepcopy — 등가.
- `grid_reuse_process_pool=False`(어댑터) vs default.yaml `true`(러너 미설정) — 두 병렬 backend가
  모두 serial이라 프로세스 풀 경로가 호출되지 않아 거동 불변. 1회 실행 프로세스엔 False가 안전.

### 의도적 편차 (기록)

- **TERM_ZG=1 미이식**. 러너 주석(L636-638)은 이것이 "plant·**예측모델 동시 적용**"이라고 명시하므로
  순수 플랜트 env가 아니다. 그럼에도 이식하지 않는 이유: 어댑터의 기존 예측 보정 사슬
  (adapter_v1 → bnmask → crossgate_predcal의 audit_calibration 스케일)이 전부
  `terminal_zero_gradient=False` 상태에서 적합됐다. 지금 경계조건만 바꾸면 그 보정이 무효가 된다.
  → 후속 예측감사 재적합 때 A/B 항목으로 올린다.
- **seg13_vsl_box_kmh=20** (flagship 15). vissimdsd 체인의 vsl_set이 [80,100,120](20 간격)이라
  ±15 박스엔 이웃 후보가 안 들어와 VSL이 초기값에 동결된다. tuning으로 조정 가능.
- **플랜트 물리 env(VFREE/RHO_CRIT/TAU_H/NU_BASE/KAPPA/MERGE_DELTA/FW_BUFFER) 미이식** — FW_BUFFER는
  러너 주석이 "plant 전용(컨트롤러 무접촉)"으로 명시. 나머지는 VISSIM 캘리브레이션이 예측모델 기준.

### 구현 구조

- 신규 모드 `pstack-flagship`. 기존 모드 7종 + diagnostic 23종은 무접촉(분기 추가만).
- `flagship_config_overrides()` → build_config에 `flagship=True`일 때만 base와 calibration 사이에 삽입.
- `build_pstack_flagship_controller()` → env(NASH_SMAX) → cfg.mpc 동적 setattr → 인스턴스 속성.
- `run_pstack_flagship_decision()` → 사이드카 복원 → SUP cfg 스냅샷 → FAR_GATE → MS_ADAPT →
  **사이드카 저장(decide 이전)** → decide → SUP_PFO. 사이드카를 decide 전에 저장하는 이유는
  결정이 실패해 fallback_fixed로 빠져도 상태 전이 관측치(직전 밀도·래치)는 이어져야 하기 때문.
- 사이드카는 `out-action-json`과 같은 디렉터리의 `pstack_flagship_runtime.json`
  (= VBS의 decision_dir). 신규 모드에서만 생성된다.

### 검증 결과 (2026-07-31)

`scripts/test_pstack_flagship_adapter.py` **4/4 PASS** (anaconda3 Python 3.13.5, numpy 2.1.3).
실행 시 뜨는 leader_hinge/np_deadband/leader_mfd_far 카나리아 경고 3줄은 사전 이슈
(README "앞으로 해야 할 일" 5번, merge {4,6} 구 기하 튜닝) — 이번 변경과 무관.

합성 state 2회 결정 스모크에서 전 메커니즘 발화 확인:

| 항목 | 1회차 (ρ=15, 85kph) | 2회차 (ρ=35, 30kph) |
|---|---|---|
| MS_ADAPT | dmax 0 → latch 0 → 마찰 **0.013** | dmax 20 → latch **5** → 마찰 **0.0** |
| FAR_GATE | all_subcritical → **OFF** | capdrop 검출 → **ON** (stress 래치) |
| SUP_PFO | 발화, V_pstack 20.04 < V_pfo 20.48 → P-Stack 유지 | fargate ON → **감독자 OFF** |
| 미터링 | 1800 (=용량, 비혼잡) | **1500** (용량 미만 = 활성) |
| VSL | 120 (자유류) | **100** (최대 미만 = 활성) |

사이드카 연속성도 확인(1회차 first_step=1 → 2회차 0, ms_prev_rho·ms_latch·fargate_stress 전달).

**seg13_vsl_box_kmh A/B (동일 2스텝 시퀀스, box만 변경)**:

| box | 2회차 VSL | 2회차 미터링 |
|---|---|---|
| 15 (flagship 원값) | 120 → **120 (동결)** | 1500 |
| 20 (보정값) | 120 → **100 (활성)** | 1500 |

미터링이 양쪽 동일해 VSL 채널만 분리 검증됐다. flagship 15를 그대로 쓰면 VISSIM DSD 메뉴
(20 간격)에서 이웃 후보가 박스에 안 들어와 **VSL이 죽은 채널이 된다**는 가설이 실증됐다.
→ 20 채택 확정. 단 이는 "이웃 1칸이 후보에 들어온다"는 최소 조건일 뿐, 최적값은 아니다
(25 이상에서 2칸 이동 허용 시 거동은 미검증 — 후속 sweep 대상).
