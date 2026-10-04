# 종단비용 오프라인 연구 — 설계·타당성 정찰 (SDMPC-31, v3c1, plant 전용)

- 작성 2026-09-30. 이 문서는 **결과가 하나도 없는 상태에서** 쓴 사전 선언이다. 결과를 본 뒤 바꾸는 항목은 "사후 변경"으로 따로 적는다.
- 태그: [실행] 이 세션에서 돌려서 확인 / [읽음] 코드·파일을 읽어서 확인 / [추론] 근거는 있으나 직접 확인하지 못함.
- 줄 번호는 워크트리 W = `D:/VISSIM-merge/sim3-n31-termcost` (9ed2ef0) 기준이다.
- 이 단계에서 한 일: 코드 읽기, 기록된 재생 결과 읽기(읽기 전용), 이 파일 작성. **VISSIM·cscript 기동 없음, 무거운 계산 없음, W 코드 수정 없음.**

---

## 0. 결론

| 항목 | 판정 |
|---|---|
| 타당성 | **가능.** plant 코드는 고치지 않는다. 하네스 쪽 변경 네 가지면 된다(§3) [읽음] |
| 하드 블로커 | 없음. 남은 위험은 H=12(1800 s) 롤아웃이 한 번도 돌아본 적 없다는 것 하나다. 파일럿으로 먼저 확인한다(§4.8) [추론] |
| 후보 조정 | "S5 단독 80"은 뺀다. plant 가 S4·S5 를 같은 구역 머리(10)에서 읽어서 따로 줄 수 없다(§2.4). 대신 C10(FW_E 미터 4개 최소 + VSL 구역10 80)을 넣었다 |
| 검증 기준값 | R-obs 900 의 held(참조 행동) 목표 **354.9290103546391**, 선택 계획 **348.3666786204171** (§4.7). HYBRID_BUILD §2.2 가 "held 351.26" 이라 적은 것은 **PFO 웜스타트 값**이다. 참조 행동의 값은 354.93 이다 [실행: JSON 읽음] |
| 연산량 | 8 상태 × 20 후보 × 1800 s 스칼라 롤아웃 1회 ≈ 160회, 검증 롤아웃 ≈ 12회. 롤아웃당 시간은 파일럿에서 잰다. 450 s 스칼라 1회 기록은 60.4 s(프로세스 기동 포함) [실행: 진행 로그 읽음] |

---

## 1. 질문과 범위

- 질문: SDMPC-31 은 450 s(150 s × 3블록) 동안의 Ω TTT 를 최소화한다. 종단비용은 없다.
  - `sdmpc.py:203-207`: `control_area_beta_seconds != 0` 이면 거부한다 [읽음].
  - 450 s 가 끝나는 순간 램프에서 기다리는 차와 출구 100 m 앞의 차는 똑같이 누적을 멈춘다.
  - 그래서 "지금 비용, 나중 이득" 행동(본선 보호 미터링, 도시 방류)이 저평가될 수 있다.
- 묻는 것: 값싼 종단비용(Ω 를 빠져나갈 때까지 남은 자유류 시간)을 더하면, 450 s 목적함수가 **plant 자신의 장기 결과**가 선호하는 후보를 고르게 되는가.
- **범위 한계.** 이 연구는 plant 의 **자기 일관성**만 본다. "450 s 채점이 plant 의 1800 s 결과와 같은 순위를 내는가"를 묻는다. plant 가 VISSIM 을 맞게 예측하는지는 따로 다룰 질문(plant-fix 작업)이다. 알려진 plant 편향은 §6 에 적었다. 결론을 VISSIM 효과로 옮기지 않는다.

---

## 2. 코드 조사 결과

### 2.1 SDMPC 가 준비된 결정 상태에서 후보 하나를 채점하는 방식 [읽음]

1. **진입.** `vissim_stackelberg_adapter.py:13056` `run_joint_owner_decision` 이 `sdmpc.solve(controller, state, forecast, historical['previous'], …)` 를 부른다.
2. **예측기.** 튜닝이 `sdmpc: central-pfo-cap-v3` 이고 `sdmpc_surrogate_reuse: true` 다(`config_n31_v2.json` adapter).
   - 그래서 `sdmpc.py:572-583` 가 `SequenceCoordinates` 를 만들고, 요청 틀 `sdmpc_tangent.prepare_request(follower, state, forecast, reference, reference, coord, bootstrap)` 로 `sdmpc_tangent_surrogate.Query` 를 만든다.
   - 요청 틀은 `(follower, state, reference, forecast)` 와 `horizon = cfg.mpc.horizon_steps` 를 담는다(`sdmpc_tangent.py:21-36`).
   - 후보마다 `Query.evaluate` → 별도 프로세스 `sdmpc_tangent_worker.py` 를 띄운다(`sdmpc_tangent.py:44-73`). 스칼라 또는 역방향 AD 로 돈다.
3. **워커의 예측.** `sdmpc_tangent_worker.py:235-265 predict()` 가 한다.
   - 행동에 `sdmpc_prediction_sequence` 키가 있으면 `sdmpc_sequence.prediction_scope` 로 블록별 제어를 끼운다(`:243-245`).
   - `rollout_endpoint.evaluate_price_point(state, action, forecast, (), ObjectiveSpec(cfg, depth_override=request['horizon'], box_walk=False, score_mode='raw'), capture_response=True)` 를 부른다(`:247-249`).
   - 결과 상태 수가 horizon 과 다르면 예외를 낸다(`:250`).
   - 이어서 `omega_costs`(Ω 분할), NP/NUF 수량, 요약 `sdmpc_tangent_surrogate.prediction` 을 만든다(`:252-259`).
4. **블록.**
   - 키가 없는 단일 행동은 3블록에 복사된다. `sdmpc_sequence.py:28-33`: `[first.copy() for _ in range(count)]`. 키가 없으면 범위 없이 같은 제어로 굴러간다.
   - 3블록 계획은 `prediction_scope`(`sdmpc_sequence.py:63-99`)가 `coupling.run_coupled_interval` 을 가로채 블록 k 에 k번째 제어를 쓴다.
   - `enabled != 3 or horizon != enabled` 면 예외(`:74`), 블록을 모두 한 번씩 방문하지 않아도 예외(`:95-96`).
5. **450 s 뒤에 무엇이 남나 — 없다.**
   - `_rollout` 은 `forecast[:depth]` 만 돈다(`rollout_endpoint.py:186-190, 258`). SDMPC 의 depth = 3 이다.
   - 예보 길이 = `horizon_steps + leader_value_depth` = 3 + 0 (`adapter.py:13474-13485`, `evaluation/parameters.json:112`).
   - Ω 엔드포인트는 far 항을 끄고(`area_runtime.py:324-325, 351` `far_disabled`) 점수를 `ControlAreaObjective(beta=0).score` = TTT 로 둔다(`area_runtime.py:336-341`).
   - 450 s 뒤 상태의 재고는 목적함수에 **전혀** 들어가지 않는다.
6. **Ω TTT 누적.**
   - 후보마다 원장 재고를 복사해 새 `ModelAreaLedger` 를 만들고 누적값을 0으로 되돌린다(`area_runtime.py:313-323`).
   - 1 s 부분 스텝마다 `residence(keys, dt_h)` 가 `dt × Σ inside` 를 더한다(`control_area_objective.py:668-682`). 행에는 스탬프, `inside_veh`, 모든 재고의 `model_stock_veh` 가 함께 남는다.
   - 재고 키: `movement:`, `ramp:`, `origin:`, `storage:`, `freeway:`, `transit:` (`control_area_objective.py:197-237`).
   - 차량 이동은 `transfer(source, target, …, route_key)` 로 기록된다(`:603-666`). inside/outside 코호트를 비례 혼합으로 옮기고 `ttd_veh`·`entered_veh` 를 센다.
   - `AreaMetrics(ttt, ttd, entered)` 가 나온다(`:246-249, 583-584`). `omega_costs` 는 소유자별로 나누고 원장 합과 1e-10 안에서 같은지 검사한다(`sdmpc.py:261-284`).
   - 참고: 엔드포인트는 이미 출구 보상 점수 `candidate_scores` β∈{0, 60, 150, 300} s 를 계산해 둔다(`area_runtime.py:347-348`). 쓰이지는 않는다.
7. **"held" 가 무엇인가.**
   - cap 모드에서 `held_objective` = `pfo_initial` = 참조 행동을 AD 로 평가한 값이다(`sdmpc_pfo.py:36-38`, `sdmpc.py:981`).
   - 참조 = `prepare_held_actual_reference(historical)`, 즉 직전에 실제 적용된 명령이다(`sdmpc.py:558`, `physical_ramp_branches.py:306-322`). R-obs 에서는 무제어 명령이다.

### 2.2 450 s 를 넘겨 굴릴 수 있나, 경계 수요·도착 예보·도시 신호는 어떻게 이어지나 [읽음]

- **롤아웃 자체는 길이 제한이 없다.** `depth_override` 로 아무 H 나 줄 수 있다. 조건은 예보가 H 스텝 이상인 것뿐이다(`rollout_endpoint.py:188-190, 258`).
- **SDMPC 전용 가드** — 모두 하네스 쪽에서 피할 수 있다:
  - `sdmpc.py:542-543`: solve 안에서 450 s 강제. 하네스는 solve 를 우회한다.
  - `sdmpc_sequence.py:74, 95`: 3블록 전용. 하네스가 N블록 범위로 바꿔 낀다.
  - `sdmpc_tangent_worker.py:250`: `len(states) == request['horizon']`. 하네스가 horizon=H 를 넘긴다.
  - `sdmpc_aggregate.py:57-60, 38-40`: 경로 시간 칸의 끝을 `cfg.mpc.horizon_steps` 로 잡고, 넘으면 `Aggregate predictor clock/horizon mismatch` 를 낸다. **워커의 cfg 사본에서 `horizon_steps = H` 로 바꿔야 한다.** 칸은 첫 호출 때 지연 생성된다(`:65-74`). 상태에 `aggregate` 가 없는지 확인한다.
  - `lane_*`, `native_*`, 회랑 모듈에서 450 을 박아 둔 곳은 찾지 못했다(grep). 한 번도 H>3 으로 돌린 적은 없다 → 파일럿 관문(§4.8) [추론].
- **본선 수요.** A1 경계 재귀 `source_boundary.forecast` 는 블록을 순서대로 이어 가며 임의의 n_blocks 를 만든다. 앞 블록은 n_blocks 와 무관하게 같다(`source_boundary.py:37-59`). 채택률은 최근 관측률 `recent` 로 상한이 걸린다. 즉 **1800 s 내내 외생이고 후보와 무관하다.**
- **도시 경계·내부 입력.** 선언된 native 시간표의 구간 평균이다. 스텝마다 새로 뽑고, 마지막 행은 열린 구간이다(`native_demand_forecast.py:88-98`, `source_boundary.py:62-73`).
- **램프 도착 하한.** `local_ramp_arrival_forecast` 는 **T 시점 관측 램프 대수**로 만든 하한 `count·3600/drain_sec` 를 모든 스텝에 `max` 로 건다(`adapter.py:9810-9880`). 1800 s 까지 늘리면 관측 시점 램프 큐가 30분 동안 하한으로 남는다.
  - 물리 램프 plant 가 `demand.ramp_arrival` 을 실제로 쓰는지는 확인하지 못했다. `area_freeway_accounting.py:141-155` 는 `update_ramp_queues=True` 일 때만 쓰고, lane 경로는 False 로 부른다(`lane_freeway_runtime.py:123-126`) [추론].
  - 파일럿 진단 D1 으로 확인한다(§4.8).
- **도시 신호.** 행동의 green/offset 을 들고 plant 신호 시계가 시각으로 현시를 계산한다. 시간 제한은 없다 [추론: 450 이나 horizon 에 묶인 코드를 찾지 못함].
- **관측 기반 버퍼**(도착 시드, release 버퍼, 경로 코호트): 유한량이라 시간이 지나면 비워질 뿐이다 [추론].

### 2.3 종단 상태에서 쓸 수 있는 것, 비용-투-고 그래프 자료 [읽음]

- **Ω 원장 재고(종단)**: `get_ledger(states[-1]).stocks[key] = {inside, outside}` (`area_runtime.py:332-335`, `control_area_objective.py:684-692`).
  - 초기 코호트: freeway 는 전부 inside, origin(본선 미진입 큐)은 전부 outside, 나머지는 물리 투영 코호트(`area_runtime.py:41-58`).
- **셀 단위 본선**:
  - `continuity_vehicle_counts(state, cfg)` = 셀별 ρ·길이·차로(`area_freeway_accounting.py:84-98`), `cell_lengths_km(cfg, link, n)` (`:79-81`).
  - FW_E lane plant 는 셀·차로군마다 off-ramp 행 라벨(known_off / unknown × 분율)을 들고 있다(`lane_freeway_runtime.py:70-91` `upstream_off`, `off`). FW_W 는 집계 모형이다(`:36-37, 118-127`).
- **도시**: `urban_movement_queue`, `urban_link_storage`(가용량 → 점유 = cap − available), `urban_inflow_transit_buffer`(도착 스텝별), `urban_arrival_buffer`, `urban_storage_release_buffer`, `urban_link_speed_kph` (`vendor/…/state.py:1105-1137`).
- **램프·off-ramp**: `ramp_queue`, `offramp_transit_buffer`, lane 램프·off-ramp 런타임.
- **경로 코호트**: native 입력의 경로 단계(`native_input_routes.py:203-227` `distance_m`, `sdmpc_aggregate.py` 칸), shared_approach / sc2001 / route_choice 회랑 상태.
- **그래프 자료**:
  - movement 는 `origin, destination, receiving_link, beta, kind(boundary_in/off_ramp/on_ramp/boundary_out/internal), signal, phase, ramp, off_ramp` 을 가진다(`vendor/src/models/grid_topology.py:250-324`).
  - 접근 소스별 β 경로: `urban_queue_model.approach_routing` (`:150-166`). 싱크 링크: `:169-176`.
  - 물리 링크 → 저류 키: `detector_mapping.physical_storage_projection.link_to_storage` (`area_runtime.py:183-186`).
  - Ω 소속: 링크별 inside/outside `control_area_membership_213a5d.json` (inside 635 / outside 601, 종단 inside 링크 24·120). 경로별 `target_inside`: `cfg.network.control_area_routes` (`area_runtime.py:171-176, 272`).
  - 링크 길이: 망 `.inpx` 의 linkPolyPoint(`physical_ramp_branches.py:68-69` 와 같은 계산), 저류 정본의 `urban_link_length_km`(`adapter.py:4936`).
  - 자유류 속도: 도시 명목 50 km/h(`urban_avg_speed_km_h`), 본선은 lane plant 빈 셀 v_free 바인딩(`lane_plant_runtime.py:573`)과 VSL 최댓값 110.
  - off-ramp 위치: `off_access[off]['cell']`, 합류 셀: `ramp_merge_segment_index` / lane 램프 사양. off 분할 예보: `off_ramp_split_ratio` (`lane_freeway_runtime.py:32`).

### 2.4 후보를 만들 때 알아야 할 행동 공간 [읽음]

- **미터.**
  - 10 s 주기, 최소 녹색 2 s, 표 `per_lane_veh_per_cycle` g2 0.71 … g10 4.2(`config_n31_v2.json` actuation).
  - 10490 은 lane plant 가 헤드 곡선으로 바꾼다. g2 = g3 = 360 veh/h (HYBRID_BUILD §1.3).
  - `prepare_control` 은 표에 있고 0 또는 ≥ 2 인 정수 녹색이면 받는다(`physical_ramp_branches.py:255-278`).
  - SDMPC 한 결정의 이동 상자는 블록 k 에서 ±2·(k+1) s 다(`area_follower_objective.py:1290-1297`, `sdmpc_sequence.py:101-106, 113-116`). 기록 좌표로는 블록 0 이 [8, 9, 10] 이다 [실행: base_wu_900 좌표 읽음].
  - 그래서 "450 s 동안 녹색 2 유지"는 plant 로는 평가할 수 있지만 **SDMPC 한 결정으로는 갈 수 없다.** 도달 가능한 가장 빠른 조임은 8 → 6 → 4 다.
- **신호 녹색.** 이동 상자는 결정당 ±6 s, 블록 k 는 ±6(k+1) 이다. ±10 은 블록 0 에서는 못 가고 블록 1·2 에서는 간다. 녹색 축은 `{p: +1, 마지막 live 현시: −1}` 이다(`sdmpc.py:305-306`).
- **VSL.**
  - 자유 구역은 머리 0/5/10(`vsl_zone_heads FW_E [0,5,10,15]`, `vsl_zone_free [0,1,2]`). 블록 0 허용값 {80, 90, 100, 110} [실행: 좌표 읽음].
  - plant 는 표지판 셀마다 **그 셀이 속한 구역 머리의 키**(`FW_E__seg{head}`)를 읽는다(`freeway_fd.py:130-162`).
  - S4(셀 10)와 S5(셀 13)는 둘 다 머리 10 이다. **W 의 plant 로는 S5 만 따로 줄 수 없다** → "S5 단독 80" 은 뺀다. 하이브리드 브랜치는 머리 12 를 따로 만들었지만(HYBRID_BUILD §1.2) 그건 다른 튜닝이다.

---

## 3. 하네스 설계 (plant 코드 무수정, 두 번째 plant 없음)

### 3.1 구조
1. **상태 준비.**
   - `make_replay_state_v2.py prepare <R-obs decisions> <T> <scratch/termcost/replays/T>` 를 쓴다(`diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py:1-40`).
   - 볼륨이 다르므로 sha 를 확인하는 사본이 만들어진다.
   - 직전 행동은 런 폴더에서 **읽기만** 한다(무제어 직전 행동은 SDMPC 영수증 검사가 없다, `sdmpc.py:500-505`).
2. **부모 프로세스** `tools/tc_parent.py`:
   - `run_replay.py direct` 와 같은 인자·환경으로 어댑터를 `runpy.run_path(adapter, run_name='__main__')` 로 실행한다. 인자와 환경은 `replay_decision_n31.ps1` 규약과 run provenance env(`base_wu_900/replay/replay_run.json`)를 따르고 W 로 rebase 한다.
   - 실행 전에 두 곳을 패치한다:
     - (a) `adapter.demand_from_state` 를 감싸 첫 호출의 인자(state_json, calibration, detector_mapping)를 붙잡는다.
     - (b) `sdmpc_tangent_surrogate.Query.__init__` 를 감싸 **SDMPC 가 실제로 만든 요청 틀**을 붙잡고 센티넬 예외를 던진다.
   - `sdmpc.solve` 는 원본 그대로 `sdmpc.py:529-583` 까지 돈다. 그래서 follower·state·reference·coord·bootstrap 이 운영과 같다.
   - 틀을 잡은 뒤 부모는 H=12 예보를 새로 만들고 `forecast12[:3] == forecast3` 를 pickle 바이트로 확인한다. 이어서 후보 요청을 만들어 워커를 띄운다.
   - 결과를 스크래치에 쓰고 `os._exit(0)` 로 끝낸다. 행동 파일은 쓰지 않는다.
3. **워커 래퍼** `tools/tc_worker.py`:
   - `sdmpc_tangent_worker.main()` 과 같은 순서로 finder(`sdmpc_tangent_runtime.install`)를 설치한 뒤 두 곳을 패치하고 `sdmpc_tangent_worker.run(request, finder, result)` 를 **스칼라 모드**(`surrogate_evaluation='scalar'`)로 부른다.
     - `sdmpc_sequence.prediction_scope` → N블록판. `diagnostics['sdmpc_prediction_sequence']` 에 `{'schema': 'termcost-blocks/v1', 'controls': [...N개]}` 를 받는다. 검사 규칙은 원본과 같다: 블록·시계 일치, 전부 방문.
     - 블록 경계마다 원장 `ttt_veh_h`, 원장 재고 사본, 셀별 본선 대수, lane 라벨, transit/arrival 버퍼, 큐, 시각을 기록한다. 스냅숏은 **T+450 과 T+1800 두 번**만 뜬다.
   - 요청 사본에서 `follower.cfg.mpc.horizon_steps = H` 와 `request['horizon'] = H` 로 두고 예보 H 개를 넣는다.
   - 모형 무결성 검사(`frozen` pickle 비교, 소스 sha)는 원본 그대로 돈다.
   - Ω 블록 합은 블록 경계 원장값의 차분으로 구한다. "모형 전체"(inside+outside) 적분은 residence 행의 `model_stock_veh` 로 구한다(진단용).
4. **TC 계산** `tools/tc_cost.py`: 스냅숏 + 그래프(상태마다 한 번 추출)로 순수 파이썬 계산. plant 를 부르지 않는다.
5. **변경 요약 (하네스 쪽만)**:
   - ① Query 틀 붙잡기
   - ② 예보 길이 H
   - ③ 워커 사본의 `horizon_steps`
   - ④ N블록 범위와 스냅숏 훅

   W 의 추적 파일은 고치지 않는다. finder 캐시 `evaluation/controllers/__tangentcache__` 만 W 에 생긴다(허용 범위).

### 3.2 실행 규칙
- 모든 프로세스: `PYTHONHASHSEED=0`, BELOW_NORMAL(자식 상속), `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `NUMBA_NUM_THREADS=1`.
- `NUMBA_CACHE_DIR = scratch/termcost/nbc`, `TMP/TEMP = scratch/termcost/tmp`. 쓰기는 W 와 scratch/termcost 안에서만 한다.
- 하네스 잡은 한 번에 하나. 그 안에서 워커는 동시에 최대 4개(스레드 합 ≤ 4). 다른 워크플로가 재생 중이므로 시작 전에 여유 RAM ≥ 40 GB 를 확인한다. 이 세션에서 본 값은 106.7 / 127.6 GB 여유, 논리 CPU 20 [실행].
- RW_* 환경은 run provenance 값만 쓰고, 나머지 RW_* 는 지운다(`run_replay.py base_env`).
- 끝날 때 R-obs 결정 폴더의 목록(이름·크기·수정시각)이 전후 같은지 확인한다. `frozen/*` 과 다른 워크트리는 건드리지 않는다.

---

## 4. 사전 선언

### 4.1 상태 (R-obs = `sdmpc31_v3c1_nc_s31`, 직전 행동 = T−150 무제어)
1200(비혼잡 대조), 1800, 2250, 2700, 3000, 3600, 4200, 4950. 선택 추가: 6300.
- 판정에 쓰는 것은 앞의 8개다. 6300 은 보고만 한다.
- NC s31 FW_E 혼잡 창(≈2250–4650)에 5개(2250–4200)가 들어간다.

### 4.2 후보 (20개, 결과 전에 고정)

모든 후보는 [T, T+450) 에 후보 제어를 쓰고, [T+450, T+1800) 에는 **모두 같은 이어가기 정책 = 참조 행동**(무제어 명령을 held 로 유지)을 쓴다. 미터 녹색 "최소" = 2 s (`min_green_sec`) 이다.

| ID | 내용 (450 s 유지) | SDMPC 한 결정으로 도달 |
|---|---|---|
| C00 | base = 참조 행동(무제어) | 예 |
| C01–C04 | FW_E 미터 하나씩 녹색 2: 10681 / 10490(g2 ≡ g3, 360 veh/h) / 10484 / 10639 | 아니오(블록 0 은 ≥ 8) |
| C05 | FW_E 4개 모두 녹색 6 | 아니오 |
| C06 | FW_E 4개 모두 녹색 2 | 아니오 |
| C07 | FW_W 4개(10480, 10482, 10646, 10644) 모두 녹색 2 | 아니오 |
| C08 | VSL FW_E 구역 머리 10(S4+S5, 머리 10 셀 전부) = 90, 링크 키 = 셀 최솟값 | 예 |
| C09 | 같은 구역 = 80 | 예 |
| C10 | C06 + C09 (**"S5 단독 80" 대체**, §2.4) | 아니오 |
| C11/C12 | SC1001 off-ramp 현시 +10 / −10 s | 아니오(블록 0 은 ±6) |
| C13/C14 | SC1004 off-ramp 현시 +10 / −10 s | 아니오 |
| C15/C16 | SC109 p3 +10 / −10 s | 아니오 |
| C17 | FW_E 4개 8 → 6 → 4 (블록별, 이동 상자 안) | 예 |
| C18 | 10681 만 8 → 6 → 4 | 예 |
| C19 | C11 + C13 (off-ramp 출구 두 곳 동시 +10) | 아니오 |

- **off-ramp 현시를 고르는 규칙**(결과 전 고정):
  - `cfg.network.urban_movements` 에서 `signal == SC` 이고 `kind == 'off_ramp'` 인 movement 의 `phase` 를 본다.
  - 여럿이면 Σ β × `movement_capacity_by_movement` 가 가장 큰 현시를 쓴다. SC1001 은 p3 로 예상한다 [추론: 메모리 기록].
- **±Δ 녹색 규칙**:
  - 대상 현시에 +Δ 를 준다. −Δ 는 나머지 live 현시가 물리 하한(`signal_actuation_contract.phase_bounds`) 위에 가진 여유에 비례해 나눠 뺀다. 유효 녹색 합은 보존한다.
  - 그 뒤 `signals.validate_control` 을 통과해야 한다. 통과하지 못하면 Δ 를 가능한 최대로 줄이고 그 값을 기록한다. 그러면 "사후 조정"으로 보고한다.
- **미터 후보**: `diagnostics['rw_meter_green_*']` 와 `ramp_metering[mid] = service_by_green` 을 함께 넣고 `physical_ramp_branches.prepare_control` 로 검증한다.
- **VSL 후보**: `Coordinates.decode` 와 같은 규칙(`sdmpc.py:389-394, 404-405`)을 따른다.
- 후보가 plant 에서 예외를 내면 그 후보만 빼고 이유를 적는다. 다른 후보로 바꾸지 않는다.

### 4.3 롤아웃 하나로 얻는 값
H = 12 블록(1800 s) 롤아웃을 한 번 돌리면 블록별 Ω TTT 누적값 B_k(k = 1..12)와 T+450·T+1800 스냅숏이 나온다.

### 4.4 채점기

| 기호 | 정의 |
|---|---|
| (a) | Ω TTT[T, T+450] = B_3. 현재 SDMPC 목적과 같다(§4.7 V1·V4 로 확인) |
| (b1) | (a) + TC1(T+450 스냅숏) |
| (b2) | (a) + TC2 = (a) + TC1 + TC_q |
| (h900) | Ω TTT[T, T+900] = B_6 (후보 450 s + 이어가기 450 s), 종단비용 없음 |
| ref | Ω TTT[T, T+1800] = B_12. 안정성 비교용 ref1350 = B_9 |
| 진단(판정 제외) | e150 = (a) − (150/3600)·TTD(출구 보상, 엔드포인트가 이미 계산). TC1p = 도시 τ 를 plant 자기 지연 규칙으로 잰 TC1. ref_all = 모형 전체(inside+outside) TTT[T, T+1800] |

**TC1 — 자유류 비용-투-고 (veh·h).**

마디는 원장 재고와 본선 셀이다. V(x) 는 "x 에 있는 차가 앞으로 Ω 안에서 보낼 자유류 시간의 기댓값"이다.

- 도시 링크 L 에 들어온 차: V_E(L) = m(L)·ℓ_L / 50 + Σ_{m∈out(L)} β̂_m · V_M(m)
- movement m: V_M(m) = V_E(recv(m)). on_ramp 이면 V_R(ramp). 출구·싱크나 outside 로 가는 경로(`target_inside = False`) 뒤는 m(·) = 0 으로 이어간다.
- on-ramp r: V_R(r) = m(r)·ℓ_r / 50 + V_F(road(r), merge_cell(r))
- 본선 셀 i: V_F(i) = ℓ_i / 110 + (1 − x_i)·V_F(i+1) + x_i·V_O(o(i)). 마지막 셀 다음 = 0. x_i 는 off 분할 예보.
- off-ramp 저류 o: V_O(o) = m(o)·ℓ_o / 50 + Σ β̂ · V_M(m) (SC1001/SC1004 movement)
- m(·) ∈ {0, 1} 은 소속이다: 링크는 membership 파일, 전이는 route `target_inside`.
- β̂ 규칙: plant 가 β 로 나누는 곳은 설정 β 를 쓴다. 회랑·native 경로 단계·off 분할처럼 β 로 나누지 않는 재고는 **C00 롤아웃의 전이 기록**(`transfers`, [T, T+1800])에서 잰 분율을 쓴다. 관측 흐름이 0이면 설정 β 로 되돌린다.
- 도시망에 순환이 있을 수 있어 V 는 선형계 (I − P)V = c 를 푼다. P 는 하위확률행렬이다.

종단 상태에서의 합산:

TC1 = Σ_s [ inside_s · τ_rem(s) + n_s · V_down(s) ] + Σ_{셀 i} n_i · (ℓ_i / (2·110) + V_down(i))

- τ_rem 규칙:
  - movement 큐 = 0 (정지선).
  - transit = min(도착까지 남은 시간, ℓ/50).
  - 그 밖의 저류 점유 = ℓ/(2·50).
  - 램프 큐 = 0 (정지선에서 합류 대기).
- FW_E 셀에서 off 라벨이 붙은 차는 x_i 대신 자기 off-ramp 로 보낸다.
- outside 재고(예: `origin:` 본선 미진입 큐)도 V_down 을 통해 **앞으로 Ω 에 들어가 보낼 시간**을 받는다. 자기 대기시간은 Ω 밖이므로 넣지 않는다.
- 속도: 도시 50 km/h, 본선 110 km/h (질문 명세). 길이는 물리 길이(.inpx)다.

**TC_q — 결정적 큐 해소 지연 (veh·h).**

큐 q 에 n_q 대가 있고 이어가기 정책의 방출률이 μ_q veh/h 일 때, 새 도착을 무시한 D/D/1 해소 지연은

  D_q = n_q² / (2·μ_q)

이다. TC_q = Σ_{q: inside} D_q.

- movement 큐: μ = `movement_capacity_by_movement` × (현시 녹색 / 주기) (이어가기 신호 계획 기준). 무신호는 녹색비 1.
- 램프 큐: μ = service_by_green[10] (이어가기 = 개방).
- off-ramp 저류 대기분: μ = 해당 출구 movement μ 의 합.
- 본선: 임계 밀도를 넘는 초과 대수 N_ex(연속 혼잡 구간별 합), μ = 그 구간 머리 셀의 plant 용량. D = N_ex² / (2μ).
- outside 큐(`origin:`, Ω 밖 도시 큐)는 넣지 않는다. Ω 정의와 맞추기 위해서다. 크기는 따로 보고한다.

### 4.5 지표 (상태마다)
- **Kendall τ-b**: 채점기 X 대 ref, 20개 후보 전체. 둘 다 작을수록 좋다.
- **argmin 일치**: argmin_X == argmin_ref.
- **regret_X** = ref(argmin_X) − min_c ref(c). argmin_X 가 동률이면 그중 ref 가 가장 나쁜 것을 쓴다. 상대값 regret_X / ref(C00) 도 함께 적는다.
- ref 최적 후보, 그리고 **RM 조임 후보**(C01–C07, C10, C17, C18)나 **VSL 후보**(C08–C10)가 ref 에서 한 번이라도 최적인지.
- 보고만 하는 것(판정 제외):
  - 후보별 T+450 / T+1800 의 `origin:` 큐와 Ω 밖 재고, ref_all 순위.
  - NP·NUF 실측 수량. SDMPC 예산 가능성은 따지지 않는다.
  - h900·e150·TC1p 의 같은 지표.
  - SDMPC 도달 가능 부분집합 {C00, C08, C09, C17, C18} 의 지표.

### 4.6 성공 기준 (지금 고정, 이 순서대로 판정)
1. **"병목이 아니다(not the bottleneck)"**: 다음 중 하나라도 성립하면.
   - (a) 의 argmin 이 ref 와 같은 상태가 8개 중 7개 이상.
   - mean_state( regret_a / min_c ref ) ≤ 0.001.
2. 그렇지 않을 때 **"종단비용이 돕는다(helps)"**: 같은 X ∈ {b1, b2} 하나가 두 조건을 모두 만족하면.
   - mean regret_X ≤ 0.5 × mean regret_a.
   - τ_X > τ_a (엄격) 인 상태가 8개 중 6개 이상.
3. 둘 다 아니면 **"판단 불가(inconclusive)"**.

- h900 은 같은 기준으로 따로 적는다. "긴 지평은 돕고 값싼 TC 는 못 돕는다" 같은 구분을 하기 위해서다.
- **ref 안정성**: 상태마다 τ-b(ref1350, ref1800) 를 잰다. 0.8 미만이면 그 상태에 "ref 불안정" 표시를 한다. 판정은 8개 전체로 내고, 표시한 상태를 뺀 판정도 함께 적는다. 둘이 다르면 결론에 적는다.

### 4.7 실행 전 검증 (하나라도 실패하면 본 실행 금지)

| ID | 무엇 | 기준 |
|---|---|---|
| V0 | R-obs 900 준비 → 부모가 잡은 요청 틀의 horizon = 3, 예보 3개, `aggregate` 미생성 | 모두 참 |
| V1 | 참조 행동, H=3, 표준 워커 스칼라 | 기록된 held **354.9290103546391**(AD, `base_wu_900/replay/action_000900.json` `joint_leader_selection.held_objective`)과 \|Δ\| ≤ 1e-6 veh·h. repr 차이는 보고 |
| V2 | 기록된 선택 3블록 계획(같은 JSON, `diagnostics.sdmpc_prediction_sequence`), H=3, 스칼라 | **348.3666786204171** 과 \|Δ\| ≤ 1e-9 (기록값 자체가 스칼라 평가다: 진행 로그 마지막 배치가 `derivative_predictions: False`, 60.4 s) |
| V3 | 하네스 N블록 범위, N=3, 블록 = 참조 × 3 | V1 과 비트 동일 |
| V4 | 상태마다 C00 H=12 의 B_3 대 C00 H=3 목표 | 상대차 ≤ 1e-9. 두 상태에서 후보 2개(C06, C09)도 같은 검사 |
| V5 | TC1 건전성 | (i) FW_E 셀 0 through 1대 → Σℓ_i/110, .inpx 본선 사슬 길이/110 과 2% 이내. (ii) 도시 경계 입구 1대(β=1 인 단일 경로를 고른다) → 손으로 더한 길이/50 과 2% 이내. (iii) RM_C10681 큐 1대 → 램프 + 합류점~끝 / 110 과 2% 이내. (iv) 빈 상태 → 0 |
| V6 | 쓰기 경계 | R-obs 결정 폴더 목록 전후 동일, `frozen/*` 무변경 |

### 4.8 파일럿 관문 (T=2700, 본 실행 전)
- C00·C06 을 H=12 로 돌려 롤아웃당 벽시계·최대 RSS 를 잰다. 예외 없이 끝나는지 본다.
  - 롤아웃이 15분을 넘거나 워커 RSS 가 8 GB 를 넘으면 동시 워커를 2로 줄이고 6300 을 뺀다.
  - H=12 가 예외를 내면 원인 모듈을 찾는다. 하네스 쪽에서 cfg 로 풀 수 있으면 풀고, 아니면 feasible = false 로 보고한다.
- **D1 (램프 도착 하한 감사)**: C00 H=12 를 한 번 더 돌리되 스텝 4..12 의 `ramp_arrival` 을 0 으로 둔다.
  - 같으면 plant 가 쓰지 않는 값이다.
  - 다르면 1800 s 까지 이어진 관측 하한이 ref 를 부풀린다고 적는다. 판정은 그대로 두고 보고만 한다.

### 4.9 연산량
- 부모 준비: 상태당 약 16 s (기록 `load_and_model_prepare` 16.1 s) [실행: 읽음].
- 롤아웃: 160 (본) + 8 (V4 H=3) + 4 (V4 추가) + 3 (V1–V3) + 2 (D1·파일럿) ≈ 177회.
- 450 s 스칼라 1회 60.4 s 가 기동을 포함한 기록값이다. 1800 s 는 2–5 분으로 추정한다 [추론]. 워커 4개 동시면 전체 약 1.5–4 시간.

---

## 5. 산출물 배치 (scratch/termcost)
- `tools/` tc_parent.py · tc_worker.py · tc_cost.py · tc_metrics.py · run_all.py
- `replays/T/` 준비된 상태(사본)
- `out/T/` 후보별 `C??.json`(블록 누적, 스냅숏 요약, 수량), `graph.json`, `tc.json`
- `metrics.json`, `REPORT.md`
- `nbc/`, `tmp/`

---

## 6. 위험·한계 (보고서에 그대로 옮긴다)
1. **plant 자기 일관성만 본다.**
   - VISSIM 에서는 VSL 이 방류를 올리지 않았다(N1/N1F). plant 의 VSL 법칙 L1 과 two-branch FD 는 VSL 이득을 줄 수 있다(메모리: "VSL 이득 = Carlson 허구").
   - plant 는 SDMPC 계획을 native 보다 좋게 본 적이 있다.
   - VSL·미터 후보의 ref 값은 plant 의 믿음이다.
2. **Ω 반대 편향.** Ω 는 미진입 큐(`origin:` = outside)와 Ω 밖 도시 큐를 뺀다. 큐를 Ω 밖으로 밀어내는 후보(VSL 로 본선 진입 억제 등)는 ref 에서도 공짜처럼 보인다.
   - TC1 은 outside 재고의 앞으로의 Ω 시간을 넣어 일부만 되돌린다.
   - ref_all 과 origin 큐 변화를 함께 보고한다. VISSIM 의 미삽입 대기열은 모형에도 없다.
3. **이어가기 정책이 급하다.** 450 s 에 무제어로 바로 돌아간다. 미터 녹색 2 → 10 같은 도약은 이동 상자 밖이다. 폐루프 SDMPC 의 실제 궤적과 다르다.
4. **ref 도 잘린 지평이다**(1800 s). 종단 상태 문제가 줄어들 뿐 없어지지 않는다. ref1350 대조로 표시한다.
5. **TC1 근사.**
   - 링크 안 위치를 절반으로 둔다.
   - 묶인 저류의 길이를 직렬 합으로 둔다.
   - β̂ 는 C00 궤적에서 잰다(후보 간 공통).
   - plant 의 도시 링크 지연은 차로 수 배로 과대하다(메모리: 차로수 차원 오류). 물리 50 km/h TC1 은 plant 자신의 자유류 통과시간과 다르다 → TC1p 진단으로 크기를 보인다.
6. **TC_q 근사.** 새 도착 무시(과소), 역류·상호작용 무시, 본선 큐를 한 병목으로 묶는다.
7. **1800 s 예보.**
   - 본선 채택률은 최근값으로 상한이 걸린다(후보와 무관한 외생).
   - 램프 도착 하한은 T 의 관측 큐로 고정된다(D1 로 사용 여부 확인).
8. **SDMPC 예산 제약**(NP·NUF cap)은 적용하지 않는다. 채점기의 순위 일치만 본다.
9. **도달 가능성.** 20개 중 5개만 SDMPC 한 결정으로 갈 수 있다. 나머지는 여러 결정에 걸쳐야 한다. 판정은 전체 20개로 하고, 부분집합은 보고만 한다.
10. **plant 비결정성 없음.** 차이가 아무리 작아도 순위가 선다. VISSIM 시드 σ(메모리: 1% 급)와 비교할 수 있게 상대 regret 을 함께 적는다.

---

## 7. 블로커와 조정 목록
- **하드 블로커: 없음** [읽음]. 남은 위험은 H>3 롤아웃이 처음이라는 점이다(§4.8 관문).
- **조정** (결과 전):
  1. S5 단독 80 → 제외. plant 가 구역 머리 키를 읽기 때문이다(`freeway_fd.py:156-157`). 대체 후보는 C10.
  2. "최소 허용 녹색" = plant 최소 2 s 로 정의하고, SDMPC 도달형 8/6/4 두 개(C17, C18)를 더했다.
  3. ±10 s 는 plant 가 평가할 수 있지만 블록 0 이동 상자(±6) 밖이다. 도달 여부 열로 표시한다.
  4. C19(off-ramp 두 출구 동시 방류)를 더해 20개를 맞췄다.
- **나중 통합 메모** [추론]: TC1 은 종단 재고에 대해 선형이다. 그래서 AD 로 미분할 수 있고, 재고 소유표(`install_cost_ownership`, `sdmpc.py:220-258`)로 소유자별로 나눌 수 있다. SDMPC 에 넣으려면 `sdmpc.configure` 의 beta 가드와 `omega_costs` 의 원장 일치 검사(`sdmpc.py:279-280`)를 바꿔야 한다. 이번 연구 범위 밖이다.
