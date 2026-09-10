# Connector10634 — shared local/global service contract, not a new capacity fit

실제 900초 초기 상태와 행동으로 공유 서비스 차이를 한 urban step에서 재현했다. 전역은 10634 하나의 5초 예산 **0.860544218대**를 사용하고, 국소 ramp-aware 서비스 계산은 세 source가 각각 이 예산을 사용하여 **2.581632653대**를 내보낸다. 이 차이는 충분한 재고를 새로 가정한 대수 예시를 넘어, 현재 초기 donor 재고에서 발생한다. 다만 국소 검사는 도착/후속 off-ramp 유입/ramp drain을 0으로 분리한 서비스 검사이며, 실제 follower horizon 전체의 목적함수 차이를 재현한 것은 아니다.

`selected_signal_capacity_audit.md` 첫 문단의 β 표기는 **이동 회전비율 beta**이며 목적함수 TTD 가중치 β와 다름을 명시했다. 현재 런의 목적함수 가중치는 0이다.

## 재현 입력과 비교 범위

대상은 `codex_area_sources_beta0_s13_20260910`의 state900, action750, action900과 런 manifest가 지정한 실제 beta0 설정이다. 정본 `configure_runtime`으로 설치하고 실제 `demand_from_state`의 첫 demand를 사용했다. optimizer, 가격 endpoint, freeway step, VISSIM은 실행하지 않았다.

전역은 설치된 `urban_queue_model.urban_substep`을 state.copy()에 딱 한 번 실행했다. 국소는 vendor 정본 `rollout_local_tts_ramp_aware`를 같은 시작 재고/행동의 서비스 입력으로 한 번 실행했다. 기존 함수의 call/return/line만 읽어 target query와 accepted amount를 기록했다. 함수 대체나 소스 수정은 없다. 전역 한 step 반복은 exact 동일하고 원 cfg/state/action/demand/raw/detectors 및 실행 소스의 SHA도 불변이다. 전역 도시 재고와 ledger를 비교할 때, 아직 실행하지 않은 freeway 단계로 전달될 `merge_pending`은 실제 반환된 ramp release receipt와 대조했다. 전체 coupled interval 보존을 대신 주장하지 않는다.

| 10634의 source | 실제 저장 형태 | 초기 총재고 | 서비스 가용량 | phase | 국소 accepted | 전역 accepted |
|---|---|---:|---:|---|---:|---:|
| SC1004_offW_to_E_SC1005 | OR_F_W_storage | 10대 | 0.6×10=6대 | p3 | 0.860544218 | 0.860544218 |
| SC1004_offE_to_E_SC1005 | OR_F_E_storage | 4대 | 0.6×4=2.4대 | p3 | 0.860544218 | 0 |
| SC1004_W_to_E_SC1005 | movement queue | 3대 | 3대 | p3 | 0.860544218 | 0 |

off-ramp movement의 `urban_movement_queue`는 두 source 모두 0이다. 이들을 ‘off movement 큐가 비어 있으므로 공유 경쟁이 없다’고 판단하면 틀린다. 국소 모델은 `offramp_movements`와 `offramp_occ0`를 통해 OR 저장소에서 직접 방출한다. W의 3대에는 회전비율 0.458333을 다시 곱하지 않는다. 이미 해당 movement queue에 분배된 수량이기 때문이다.

세 이동은 모두 **SC1004의 동일 LocalSignalModel**에 있으며 이 모델의 movement는 24개, `has_ramps=True`이다. 다른 16개 LocalSignalModel에는 이 세 이동이 하나도 없다. 따라서 현재10634 범위에는 서로 다른 신호 agent 간 공유 예산 통신이 필요하지 않다.

실제 action900의 SC1004 green은 p1=23.001, p2=24.333, p3=66.333, p4=24.333초, offset=56.25초다. canonical physical signal clock에서 900–905초의 세 target GREEN fraction은 모두 1이다. 양쪽의 `dt=5/3600 h`, per-source capacity=619.591836735 veh/h, 수신 링크=`SC1004_E_choice`가 일치한다. 전역 실제 query의 source 가용량/green/dt를 국소 입력과 assert하여 일치를 확인했다.

시작 수신공간은 양쪽 673.984455682대다. 전역은 첫 accepted 이후 673.123911464대로 줄고 국소 모델은 이 receiver가 자기 origin이 아니므로 frozen 공간을 유지한다. 중간 수신공간 숫자까지 동일한 것은 아니다. 그러나 전역의 모든 target query 수신공간이 세 요청 전체 2.581633대보다 훨씬 커, **이 비교에서 receiving 제약은 양쪽 모두 비구속**임을 assert했다. 공유 pool 소진이 FE/W의 전역 intended를 0으로 만들었고 receiver 제한은 해당 차이의 원인이 아니다. JSON의 `global_queries`가 순서·remaining budget·수신공간을 보존한다.

## 현재 코드의 연결점

전역 `route_choice_corridor.intended_departure`는 connector별 `service_limit_veh`/`service_used_veh`를 사용한다. `receive_accepted`가 실제 수신된 수량만 used에 반영한다. 일반 이동 batch는 `limit_intended_batch`로 동일 connector 예산을 나눠 갖는다. `advance`가 매 urban step의 예산 상태를 초기화한다. 현재 순서는 off-ramp OR_F_W → OR_F_E → 일반 W이다. 이 순서를 임의의 동시 비례배분으로 바꾸는 것은 별도 알고리즘 변경이다.

국소 `LocalSignalModel.cap_flow_of`는 동일한 per-movement scalar를 보유한다. `rollout_local_tts_ramp_aware`의 (b) off-ramp와 (d) 일반 이동 루프 사이에 공통 connector used counter가 없다. 값 세 개가 같은 것과 하나의 물리 예산을 공유하는 것은 다르다. 기존 receiver 공간 배분을 이 pool로 대신하면 안 된다. 서로 다른 물리 제약이다.

또한 `priced_wu_link_controller._phase_refine_signal_setup`은 `model.has_ramps`이면 None을 반환하고, phase refinement가 `phase_shape_local_cost`의 큐 배수 proxy로 fallback한다. 이 경로는 phase별 `len(movements) × movement_capacity_veh_h`를 사용하며 OR 저장소와10634 pool을 직접 표현하지 않는다. ramp-aware stepper 하나에만 새 예산 함수를 붙여 ‘모든 green/offset 후보 정합’을 주장할 수 없다. 실제 후보 통합 검증은 이 경로도 포함해야 한다.

## 제안하는 최소 공통 API — 아직 구현하지 않음

기존 cfg의 `route_choice_corridor.turns`에서 다음 정적 plain-dict view만 만든다. 새 용량·재고·route·owner를 추가하지 않는다.

```python
group_of[movement] = '10634'
groups['10634'] = {
    'members': (offW_to_E, offE_to_E, W_to_E),
    'service_veh_h': 619.5918367346939,  # current value, not re-estimated
    'signal': 'SC1004',
    'phase': 'p3',
    'receiver': 'SC1004_E_choice',
}
```

`LocalSignalModel`에 optional `physical_service_groups`/`service_group_of`를 붙인다. 생성은 corridor configure 뒤이며, 같은 cfg에서 global과 local view를 만든다. 대상 member가 해당 LocalSignalModel에 전부 있는지, 기존 physical connector와 맞는지, finite positive rate인지, 같은 source group의 green 노출 계약이 일치하는지 검증한다. 닫힌 group이 아니면 조용히 나눠 붙이지 않고 별도 지원이 필요하다고 실패한다. 현재10634는 SC1004에서 닫혀 있다.

세 개의 작은 공통 산술 primitive면 충분하다. 함수 이름은 제안이며 생산 API가 아니다.

```python
limits_veh = service_limits(groups, green_fraction_by_movement, dt_h)
limited_veh = limit_service_requests(
    requests_veh, group_of, limits_veh, used_veh, allocation_rule)
next_used_veh = consume_accepted(
    accepted_veh, group_of, limits_veh, used_veh)
```

- `service_limits`: 오직 `veh/h × h × fraction = veh`. 같은 connector의 세 rate를 합하지 않는다. 후보의 실제 integer-event green fraction을 호출자가 넘긴다. 이 함수가 offset/phase clock을 다시 구현하지 않는다.
- `limit_service_requests`: 요청은 이미 source availability/β/녹색 의미를 정리한 vehicle 단위다. group remaining 예산만 적용한다. query는 used를 변경하지 않는다. global off-ramp의 기존 순서를 보존하려면 singleton batch로 호출하고 일반 단계는 기존 batch/receiving rule을 유지한다.
- `consume_accepted`: 실제 수신된 수량만 더한다. requested 또는 희망 흐름을 미리 차감하지 않는다. 중복 commit, 음수/NaN, 예산 초과를 거부한다. 재고·route cohort·Ω event는 기존 owner가 한 번만 기록하며 이 primitive는 회계 event를 만들지 않는다.

전역의 현재 `service_limit_veh`/`service_used_veh`가 바로 이 primitive의 상태가 되어야 한다. 별도 새 counter를 병렬로 두면 두 개의 예산이 생긴다. receiver 배분에서 거절된 요청은 예산을 소비하지 않으므로 같은 단계 이후 적격 source가 잔여 예산을 사용할 수 있어야 한다.

국소에서는 함수 호출마다 독립 used dictionary를 만들고 **매 substep 시작에 0으로 초기화**한다. (b) OR_F_W/OR_F_E와 (d) W가 그 dictionary 하나를 공유한다. 모델의 공유 cfg/cache 객체에 mutable used를 저장하면 green/offset 후보 순서와 worker 재사용에 따라 비용이 바뀌므로 금지한다. start state나 candidate ControlAction에도 지속 예산을 기록할 이유가 없다. 중간 substep부터 재개할 필요가 생기면 used를 명시 입력으로 복제하며, 현재 step-boundary 시작은 항상 0이다.

현재 코드에는 국소 scalar getter만 감싸서 이 순서를 안전하게 주입할 hook이 없다. cached capacity를 함수 호출 순서에 따라 낮추거나 전역 dictionary를 monkeypatch하는 방법은 피한다. 필요한 코드는 local substep의 **begin / intended limit / accepted commit** 명시 지점이다. vendor 원본을 보존해야 한다면 그 국소 substep만 정본 모듈로 좁게 추출하고 OFF는 원 callable로 위임한다. 전체 follower/adapter 사본은 필요하지 않다. worker는 같은 static group spec과 공통 함수를 다시 설치하되 후보의 used counter를 부모/다른 후보에서 상속하지 않는다.

## 수선 후 필요한 좁은 검증

1. 이 actual900 fixture에서 같은 green/dt/source availability와 비구속 receiver를 사용해 local/global 합 0.860544218, source별 기존 우선순위 일치.
2. 실제 receiver를 작은 **시험 입력**으로 제한했을 때 accepted만 pool 소비, 수신 거절로 예산 유실 없음. 이는 새 물리 capacity fit이 아니라 산술 회귀다.
3. 두 번째 substep은 새 예산, 같은 후보 반복·다른 후보 순서·candidate copy·새 worker가 동일 결과. 원 state/cfg/action 불변.
4. RED/부분 GREEN/event 경계에서 같은 물리 clock 사용. off availability의 pending transit 제외 여부도 같은 입력 계약으로 확인하되 pool 함수 안에서 새 여행시간 모델을 만들지 않는다.
5. OFF exact 원동작, 무관한 movement 변경 없음. phase refinement의 ramp fallback을 그대로 둔다면 ‘ramp-aware 국소 pool 수선’까지만 완료로 표시하고 모든 후보 정합 완료로 승격하지 않는다.

이 수정은 현재619.59의 물리적 참값을 보장하지 않는다. 먼저 같은 용량을 같은 물리 제약으로 소비하도록 하는 정합 수정이다. 관측 기반 서비스율 식별, downstream finite-state 예측, 다른 head/우회 authority는 별도 과제다.

근거: `local_signal_plant.py` 65/90/271/386/428; `wu_faithful_follower.py` 589/803/837/939; `priced_wu_link_controller.py` 293/341/419; `route_choice_corridor.py` 622/641/656/723; `urban_flow_accounting.py` 73/90/107/435/449. 정확한 입력·source SHA와 전역 query/receipt는 동명 JSON에 있다. 재현 명령: `python -X utf8 -m diagnostics.local_shared_service_contract_review` (2.56초). 생산 source/config/data 변경 0.
