# 고속도로 검증 후 전체 망 이식 시 확인할 차이

2026-09-30. seed67 네 native 런 실행 중 수행한 작은 소스 검토다. 모델·실행 설정을 수정하지 않았고, 새 결과를 읽거나 재보정하지 않았다. 우선순위는 고속도로 반응 검증 → 램프/진출부 연결 → 전체 Ω/SDMPC다.

## 확인된 연결 차이

- 이번 세 모델 비교는 `replay_congested_component.py:audit_freeway_choice_ranking`에서 각 rollout에 `offramp_inventory={contract, raw}`와 `port_dynamics.entry_capacity_mode=storage`를 명시한다. 현재 차량의 목적 경로 재고와 동적 진출부 저장을 사용하는 조건이다.
- `runtime_setup.py:218–224`는 `lane_context is None`일 때만 일반 `offramp_routing.configure_inventory/initialize_inventory`를 호출한다. 현재 v2 전체 망 경로에서는 이 호출을 건너뛴다.
- `lane_freeway_runtime.py:28–35`는 `component._config`로 방향별 설정을 만들고, 관측 `off_splits`를 `off_ramp_split_ratio`에 넣는다. `lane_plant_runtime.py:_load_sources_v2`는 lane group 기능을 금지한다. 따라서 그 아래의 lane-group 전용 `install_observed_exit_labels`는 v2의 이번 경로 재고 초기화를 대신하지 않는다.
- `canonical_harness.py:_config`는 초기화되지 않은 경로 재고를 상속하면 오류를 낸다. 명시적인 `rollout(..., offramp_inventory=...)` 초기화는 이후 별도 단계다.
- 전체 망의 `LaneOfframpRuntime`은 실제 저장 재고, 이동 지연, 하류 신호 서비스/수용 공간에 따른 배수를 이미 갖고 있다. 위 차이를 이유로 이 저장·배수 자체가 없다고 해석하면 안 된다.

## 의미와 다음 검증

계수 manifest만 교체해도 이번 component 시험과 동일한 전체 망 모델이 된다고 볼 수 없다. **현재 목적 경로 재고의 초기화·이송·분기 선택까지 연결해야 한다.** 이는 소스에서 확인한 이식 누락 가능성이며, 새 seed의 예측 실패 원인이나 본선 보정 성공을 뜻하지 않는다.

seed67 종료 후에는 먼저 사전에 동결한 3모델×4명령의 450초 본선 결과를 검증한다. 통과 근거를 확보한 뒤 기존 전체 망 runtime에 같은 경로 재고를 연결하고, 동일 초기 상태/동일 수용·합류 경계에서 component와 전체 망 본선의 한 단계 및 450초 전이를 비교한다. 경계가 달라질 때의 도시·램프 상호작용은 그 다음에 구분한다.

현재 native가 끝나기 전 helper/core를 수정하지 않는다. 기존 9000초 STOP, Ω TTT 목적함수, 동적 off-ramp 저장·배수, 대기 비용, 차량 보존을 유지한다. 이 문서는 전체 망 또는 SDMPC의 검증 통과를 선언하지 않는다.
