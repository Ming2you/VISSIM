# 8개 램프의 독립 전략·예측 확장: 최소 연결 범위

**사용자 결정 반영:** N_UF는 **8개 램프에서 실제 본선으로 들어갈 예측 유량의 합 [veh/h]**으로 확정됐다. 450초 지평의 램프별 accepted merge 차량 수에 3600/450을 곱한다. 서비스 상한·head 통과·4그룹 명령률·CSV 인코딩의 합은 대체값이 아니다. 고정 leader 목표와 후보별 실제량을 분리하며 기존 7,200veh/h를 자동 승계하지 않는다. 아래의 NUF 선택지 논의는 이 결정 전의 검토 이력이다. 구현 및 미완료 범위의 최신 기록은 [후속 보고서](RUNTIME_FOLLOWUP_20260911.md)를 따른다.

사용자가 요청한 것은 실제 8SG뿐 아니라 예측 모형도 8개 branch로 분리하는 것이다. 기존 진단 helper를 활성화하는 것만으로 완료할 수 없다. follower owner는 도시17개+FW_E/FW_W의 **19개를 유지**하며, 각 FW owner가 자신의 실제 미터4개와 기존 zoned VSL을 함께 선택해야 한다. 아래는 현재 소스를 읽은 설계 검토이며 코드·모형·COM을 실행하거나 변경하지 않았다.

## 물리 주소와 기준 행동

| FW owner | 기존 그룹 | 실제 미터(SG) | 관리할 직접 상류 link+connector |
|---|---|---|---|
| FW_W | R_D_W | RM_C10480 (9101:1) | 124+10480 |
| FW_W | R_D_W | RM_C10482 (9102:1) | 32+10482 |
| FW_W | R_F_W | RM_C10646 (9103:1) | 121+10646 |
| FW_W | R_F_W | RM_C10644 (9104:1) | 69+10644 |
| FW_E | R_F_E | RM_C10639 (9105:1) | 70+10639 |
| FW_E | R_F_E | RM_C10681 (9106:1) | 68+10681 |
| FW_E | R_D_E | RM_C10490 (9107:1) | 129+10490 |
| FW_E | R_D_E | RM_C10484 (9108:1) | 31+10484 |

10482/10681에는 두 차로의 신호 head가 있다. 같은 SG를 쓰므로 독립 전략은 차로별10개가 아니라 **SG별8개**다. 각 권역의 전체 차량·정지·속도를 관측해도, 도시 통과나 다른 목적지 차량은 그 미터의 도착 수요가 아니다. 69에서10639를 향해70으로 가는 차량처럼 다른 램프행 차량이 현재 권역을 통과할 수도 있다.

전략의 원시 좌표는 `g_m [s/10s cycle]`가 적합하다. 직전 실제 CSV/readback으로 인증된8개 녹색을 기준점으로 고정하고, 명시적인 미터별 변경 한도와 양자화 가능한 녹색 집합의 교집합에서 탐색한다. 동일 decision 내 기준점·폭은 유지한다. 기존 group1800을 두 branch900으로 나누거나 관측 방출에 맞춰 기준점을 이동하면 실제 명령 기준이라는 계약이 깨진다. ±1초는 기존 진단에서 사용한 물리 이동 예시이며 기존 ±300veh/h와 같은 조건이 아니다.

## 변경이 연결돼야 하는 기존 함수

| 파일·함수 | 현재 제약과 최소 변경 |
|---|---|
| `joint_owner_game.build_ownership` | `len(ramps)==4`, FW당2개 group strategy, group당2physical meter를 요구한다. 8branch 물리 catalog와 FW당4개 독립 녹색 strategy를 연결하고, 기존4그룹은 보고/명시적 compatibility 용도로 분리한다. native SC/SG 중복 소유 검사는 유지한다. |
| `joint_owner_game.LEVER_FIELDS`, `_action_key`, `validate_action_addresses`, `assert_owner_transition`, `_extra` | 녹색8개가 실제 game action identity와 변경 검증에 들어가야 한다. FW_E가 FW_W의 미터를 변경하면 실패한다. 기존4rate가 같다는 이유로 서로 다른8녹색을 동일 행동으로 제거하면 안 된다. derived group 값과 NUF의 허용 변화도 별도 검증한다. |
| `joint_owner_neighbors.build_fixed_move_box` + `area_follower_objective.joint_decision_move_limits` | 현재 `meter_veh_h=300`과4rate만 박스에 포함한다. 실제8녹색의 단위·한도·기준 token을 명시한 물리 박스를 추가한다. 후보 생성 전과 실제 writer 양자화 후 모두 검사한다. |
| `joint_owner_neighbors.Domain`, `generate`, `_independent_meter_points`, `build_current_freeway_domain` | `two model meters`와2원소 rate point를 전제한다. FW당4개의 물리 녹색을 직접 바꾸는 후보로 확장한다. 적어도 각 미터의 단독 변화가 basis에 남아야 한다. `수요/정지 대기`는 고정 박스 안 후보의 순서와 서비스 필요량 설명에 사용하며, 관측 유량으로 cap을 잘라서는 안 된다. |
| `joint_owner_neighbors.fixed_meter_coordinate_proofs`, `make_joint_neighbor_callbacks` | 현재1500–1800 요청이 모두 OPEN으로 정규화되는 증명은 새8녹색 영역의 고정 증명이 아니다. 새 영역에서는 허용 녹색 집합이 실제로 singleton인 경우만 고정 좌표로 제외한다. writer/소유권/물리 박스 fingerprint와 구체적8명령을 동일 context에 묶는다. |
| `area_meter_finalization.prepare_physical_service_meter_candidate`, `finalize`, `assert_writer`, `for_endpoint` | 기존 helper는8녹색 보존을 검증하지만 서비스는 다시4그룹 합/1800cap으로 만든다.8branch 예측 소비량을 독립적으로 넘기도록 확장해야 한다. 최종 검증한 명령을 endpoint와 writer가 동일하게 소비하고, 나중에 `_measured_meter_allocation`이4rate로 재배분하지 않아야 한다. |
| `area_meter_finalization.prepare_recorded_historical_meter_reference`, `prepare_historical_meter_reference`, `prepare_held_actual_meter_reference` | 직전 실제8명령의 주소·시각·cycle·녹색을 보존한다. 기존4rate history만으로8branch를 임의 분할하지 않는다. 과거4그룹 NUF 값은 원 정의와 함께 보존하며 새8서비스 target으로 변환하지 않는다. |
| `vissim_stackelberg_adapter.real_world_ramp_meter_actions`, `real_world_ramp_meter_write_back`, JSON load/serialize | writer는8녹색에서 기존 CSV 명령을 직접 생성하고 적용 readback을 유지한다. 명령 인코딩과 예측 서비스량을 별도 필드로 남긴다. 새 action 좌표를 추가할 때 load/serialize/copy/worker pickle/response applied_control round-trip 전체가 보존돼야 한다. |
| `area_runtime.evaluate_joint_prices` | 현재 FW 가격 basis가 zoned VSL+2group rate다. 각 FW의 3VSL+4미터 녹색 방향에서 동일 실제 anchor의 응답을 측정한다. group 합이 같아도 서로 다른 branch 명령을 제거하지 않는다. 도시 basis, 공통 상태·forecast·가격 anchor와 lambda 분리는 유지한다. |
| `area_leader_objective.matched_external_secant`, `fit_joint_price_field`, `install_joint_price_field`, `fixed_joint_price_terms` | 외부 비용은 계속 동일 응답의 ΔJΩ−ΔCi다. 미터의 실제8녹색 변위를 사용하면 가격 단위는 veh·h/녹색초이며 이를 rate 가격과 섞지 않는다. 기존2미터 equality tangent의 `delta[0]-delta[1]`, `[p,-p]` 전제는4개로 일반화할 계약이 필요하다. 독립 dual 정책에서는 실제4좌표의 rank를 검사한다. |
| `area_leader_objective.shared_quantity_constraints`, `verify_joint_written_action`, `validate_joint_leader_result` | 현재 NUF는4group finalized rate의 합이다.8개 녹색 전략·8branch 서비스로 전환해도 NUF 정의는 자동으로 바뀌지 않는다. 아래의 명시적 수량 계약을 소비하도록 연결하고, leader target과 action의 실제 파생 값을 별도 유지한다. |
| `area_meter_finalization.reachable_meter_budgets`, `area_follower_objective.prepare_joint_leader_candidates`, `solve_runtime_joint_leader` | 현재4rate/방향당2rate 가능한 budget을 만든다. 새 정의가 정해지면 동일8녹색 명령에서 도달 가능한 수량을 만든다. 가능한 budget 합이 같아도 서로 다른 명령·대기 분포의 대안을 보존하며, budget을 만족시키려고 후단에서 다른 branch로 방출을 옮기지 않는다. |

action 저장 위치도 주의해야 한다. vendor `ControlAction.copy()`는 선언된 필드를 열거해 복사하므로 새 Python attribute를 붙이는 것만으로는 녹색이 복사 과정에서 사라질 수 있다. 기존 `rw_meter_green_<MID>`는 diagnostics의 scalar라 현재 복사에서 유지되지만, 이를 실제 전략으로 사용할 때는8개를 읽고 변경하는 정본 좌표 접근·identity·검증이 반드시 있어야 한다. 새 adapter나 vendor 전체 개편을 만들기보다 기존 action의 저장·복사 계약과 위 game 접근 함수를 함께 정리하는 것이 최소 경로다. 제어기의 metadata에만8개 값을 기록하고 전략에 포함했다고 할 수 없다.

## NUF를 유지하거나 바꾸는 경우의 경계

다음 세 값은 현재 같지 않다.

1. 기존 **4group `ramp_metering`/NUF**: all-open group1800, 전체7200이라는 정규화된 모델 명령량. 구속 시에는 과거 connector 유량 hint로 잘린 표의 합이 들어갈 수 있다.
2. 실제 CSV의 **`rate_vph=900×g/10`**: writer 명령 인코딩. g10이면 SG당900이다.
3. 기존 서비스표의 **`μ_m(g)=차로수×n(g)×3600/10`**: 예측 포화 서비스량. g10은 차로당1512veh/h, g9는1328.4veh/h다. 이것도 실측 방출량 또는 VISSIM의 모든 교통 조건에서 보증된 용량이 아니다. 실제 native에서 g9는9초 GREEN+1초 AMBER이며 RED는0초였다. 예측 모형에서 이를9초 GREEN+1초 RED로 바꾸거나 표의 차이를 이미 검증된 VISSIM 용량 차이로 해석하면 안 된다.

따라서 기존7200 target을 `sum(μ_m)` 제약에 그대로 사용하면 조건을 몰래 바꾼 것이다.8미터가10차로이므로 표상 all-open 서비스 합은15120veh/h로 규모부터 다르다. 반대로 μ를7200에 맞춰 비례 축소하면 가짜 용량 정규화가 된다.

최소 안전 경로는 **8branch 물리 예측/8명령 보존을 먼저 검증하면서 기존 NUF 이력을 별도 보존**하는 것이다. leader 연결 시 수량 정책을 config와 모든 action/result에 버전·단위로 명시해야 한다. 기존4group 정책을 계속 쓰려면 그 파생 함수와 old target을 그대로 보존하고 그것이8branch 물리 서비스 합이 아님을 표시한다. 물리 서비스 합으로 바꾸기로 선택하면 `physical_meter_service_sum`처럼 새 정의를 명시하고, 새 reachable budget/target/dual을8명령에서 구성하며 과거7200을 자동 승계하지 않는다. CSV 인코딩의 합이나 observed discharge를 서비스 합 대신 쓰지 않는다. 어느 선택도 단순 속도 최적화로 보고할 수 없다.

NUF equality의 tangent는 현재 두 rate의 차 한 방향이라는 가정에 묶여 있다.4개의 독립 녹색에서 μ(g)가 이산 비선형이면 고정 총서비스를 유지하는 swap 후보도 실제 양자화된8명령에서 검증해야 한다. 연속 선형 `sum(delta g)=0`만으로 동일 NUF라고 하면 안 된다. leader target은 decision 내 고정하고, infeasible target을 후보에 맞춰 확장하지 않는다.

## 직접 상류 권역과 local cost의 현 상태

권역 관측은 사용자 지정8개 직접 상류 link+connector를 물리 집합으로 다룰 수 있다. 같은 실제 차량이 도시 stock·ramp stock 두 곳에 저장되거나 Ω TTT에 두 번 들어가면 안 된다. 이동에는 송신원에서 한 번 빼고 수신원에 한 번 넣는 수지가 필요하며, 권역 전체 재고와 램프 목적지 cohort는 같은 physical stock의 서로 다른 분류다.

현재 FW local cost의 접근 항은 `link_predictor.shared_freeway_approach_source_contract`/`_shared_freeway_approach_quantities`가 등록된 램프행 movement와 shared approach의 **램프 목적지 bin**만 합친다. 직접 상류 link 전체의 도시 통과 차량을 FW owner에 주는 구조가 아니다. `area_follower_objective.shared_urban_cost_inputs`는 기존 도시 movement/ramp/landing 귀속을 유지한다. `link_predictor.score_shared_freeway_response`는 local landing 항 등이 다른 owner와 겹칠 수 있으며 JΩ의 가산적 분할이 아니라고 명시한다.

따라서 **이번8권역 관측 추가 단계에서는 기존 actor별 local cost를 변경하지 않는다.** 권역 전체 residence를 FW 비용에 바로 더하면 도시 비용과의 중복 또는 목적지 미확정 차량의 잘못된 귀속을 만들 수 있다. 향후 전체 권역 비용을 FW가 맡게 하려면 실제 physical stock/cohort마다 현재 도시/FW 귀속을 표로 확인하고, 단일 재고에 대한 중복 추가 없이 별도 local objective 변경으로 검증해야 한다. 외부 가격도 변경 후의 같은 Ci로 양쪽 차분을 다시 측정해야 한다.

## 연결 완료를 판정할 최소 증거

- 각각의8녹색 단독 변화가 소유 FW의 후보·박스·price basis·물리 응답·writer까지 살아 있고 다른 미터는 유지된다.
- 실제 직전8명령과 한 decision의 고정 박스를 load/copy/cache/worker/output 뒤에도 보존한다.
- 8branch 재고·도착·정지·서비스·실제 방출이 독립이며, 동일 group 총량의 두 배분에서도 각 branch 수지와 합류 receiving이 올바르다. 수요가 막힌 branch의 차량을 다른 branch로 보내지 않는다.
- 직접 상류 권역의 도시/다른 목적지/미확정 차량을 관측하되 해당 미터 수요로 일괄 분류하지 않는다. Ω TTT/TTD와 내부 이동 수지는 중복 없이 유지한다.
- NUF의 버전·단위·정확 파생 함수·leader target이 명시되고 기존 이력과의 전환을 숨기지 않는다.
- 19owner 공통가격 및 유효 hold/deadline 처리는 유지한다. 독립 미터8개가 추가로 활성화되면 exact basis 비용도 증가한다. 현재69방향+기준 응답에 단순히8방향이 늘 수 있으므로 전체120초 budget 충족을 새로 측정해야 하며, 실패한 SPSA를 속도 때문에 자동 채택하지 않는다.

이 문서는 구현할 연결 범위를 정리한 것이며,8branch follower·예측·native 실행의 완료 증거는 아니다.
