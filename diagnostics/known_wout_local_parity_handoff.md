# W_out local parity — 보존 후 중단

2026-09-10 부모 지시에 따라 이 물리 수선은 더 진행하지 않고 성능 계측으로 전환합니다. 운영/Git은 수정하지 않았고, 전체MPC/endpoint/VISSIM도 실행하지 않았습니다. 아래는 아직 미적용인 부분 제안입니다.

## 실제 소비 경로와 한 단계 결과

`adapter.install_leg_ramp_split_runtime._flows`는 frozen `u_on`을 기존 destination share로 계산합니다. `WuDistributed._coupling`은 이를150초 평균유량으로 받아 FW local에 넘깁니다. `link_predictor.LocalLandingState`는 동일 share의 초기 재고항을 `replaced_coupling`으로 빼고 매5초 W_out에서 다시 수신합니다. global known-route 태그만 넣으면 이 두 local 계산은 여전히 이전 share를 사용합니다.

|시각|목적지|기존 FW-local5s (veh)|known-global5s (veh)|부분 제안 local5s (veh)|
|---|---|---:|---:|---:|
|1200|free|0.279117677|0.558285599|0.558285599|
|1200|R_F_E|0.139600710|0.027920142|0.027920142|
|1200|R_F_W|0.418718387|0.251231032|0.251231032|
|3300|free|1.465367802|1.549245469|1.549245469|
|3300|R_F_E|0.732903728|0.104692158|0.104692158|
|3300|R_F_W|2.198271530|2.500000000|2.500000000|

초기 raw 전체N/ready, 동일 held control, 기존 이동률과 수신공간/connector 예산을 사용했습니다.3300 R_F_W는 기존2.5veh/5s connector 예산에 제한됩니다. global에는 실제 도시 본문이 포함되고 local은 다른 도시 경계를 동결하므로 표는 W_out의 해당 accepted sub-transfer만 비교합니다. 두 모델 전체 궤적이 일치한다는 뜻이 아닙니다. 보존된 before JSON의 ‘receiver caps nonbinding’ 문구는 **저장공간**에만 해당하며3300 connector budget은 binding입니다.

초기 stock 항의 `u_on_R_F_E`와 LocalLanding replacement를 함께 바꾸면1200에는80.016→16.0032vph,3300에는420.084→60.0072vph로 정확히 같은 값이 됩니다. 한쪽만 바꾸면 이미 local에서 전진시키는 재고항이 frozen 접근 유입으로 다시 들어갈 수 있습니다.

## 부분 제안

`known_wout_local_landing.patch`는 `known_wout_routes.patch` 다음에 적용하도록 만든 **미적용** 후속입니다. 기존 route helper의 query/commit을 그대로 재사용하고 새 adapter나 model class 사본은 만들지 않습니다. 추가된 snapshot query는 destination alias만 deepcopy하고 물리 dictionary를 읽기만 합니다. LocalLanding candidate마다 같은 초기 alias를 복제하고, 기존 local stock owner가 실제 이동한 뒤 accepted 수량만 차감합니다. direct landing의 native-path prior와 ready 시각도 이전 global 제안 그대로입니다.

실제1200/3300 초기 소비 일치, 원본candidate 불변, pending due241 전후, 수신거절, 새direct 수신, OFF 결과/상태 동치의3회귀가5.243초에 PASS했습니다. 근거는 `test_known_wout_local_landing.py`, `known_wout_local_landing_initial_results.json`입니다. 기존 external ramp receiving boundary는 동결하므로 전체 horizon의 모든 receiver update 정합을 검증한 것은 아닙니다. 모든 실제production import는 현재 정본이며 변경 method만 진단 프로세스에서 적용했습니다.

## urban green/offset/refinement는 여전히 범위 밖

현재 `local_signal_service.rollout_shared_ramp`와 `ramp_refinement_setup`은 W_out을 frozen receiving space로만 받습니다. SC1004에는 W_out으로 받는6개 movement가 있지만 W_out을 origin으로 삼는 movement는0개입니다. 현재 local ramp dictionary에는R_F_E만 있고R_F_W는 없습니다. ‘local_queue_override’라는 파일/식별자는 현재 검색한 정본 tree에 없습니다.

실제 local phased cost 호출에서 W_out destination alias만 모두R_F_E로 바꿔도1200 비용15.239926629572143,3300 비용23.450768604967205가 각각 정확히 같습니다. setup에 W_out N/ready/destination seed가 없으며 S_eff=200/115veh만 같습니다. 기록된 source-run 설정은 shared pool 도입 전이므로 이 감사에서는 **기존 shared_local_service_pool만 private cfg에 ON**으로 하여 현재 shared cost caller를 검사했습니다. capacity/demand/control은 바꾸지 않았습니다. 실제 phase-price refresh가 하는 `follower.phase_price_local_cost_model=controller.phase_price_local_cost_model` handshake도 동일하게 수행했습니다.

이는 원래 local 목적함수가 이웃 receiver를 동결하는 분해 가정과 관련됩니다. 이 경계에서 태그를 읽지 않는 사실만으로 새로운 차량 보존 버그라고 단정하면 안 됩니다. 다만 global과 같은 W_out 예측을 요구한다면 초기 alias 전달만으로는 부족합니다. 최소 다음 계약이 필요합니다.

1. green/offset/refinement 모두 같은 immutable W_out seed(N,ready,선택 목적지)에서 candidate-private 상태를 만든다.
2. 기존 도시 본문과 같은 순서로 W_out destination request를 준비하고, 실제 ramp/receiver 수용 뒤에만 공통 helper로 debit한다. 미래 urban movement accepted receipt는 기존 delay 후 선택 전 cohort로 넣는다.
3. W_out의 finite space는 actual 수신/방출로 갱신한다. queue에서 W_out으로 이동한 N은 사라지지 않고 residence에 남아야 한다.
4. 현재 local에 없는R_F_W의 receiving boundary와 비용 소유를 먼저 정한다. 무조건R_F_W 재고를 local 비용에 더하면 기존 game의 player/목적함수 범위를 변경할 수 있다. 다른 FW ramp의 동적 예측까지 보완했다고 주장하지 않는다.

이 urban 계약은 구현하지 않았습니다. 따라서 현재 두 패치를 합쳐도 네 lever 전체 local/global parity를 검증했다고 표시하거나 active MPC로 승격하지 않습니다. 문제·후보·검증 결과를 보존하고 여기서 중단합니다.
