# 제어 계산 후속 검증과 확정된 N_UF 정의

현재 코드 수정과 저장 상태 재현을 완료한 범위다. 이번 후속 검증에서 VISSIM을 새로 실행하지 않았다. 8개 램프의 독립 예측·follower 연결, 전체 후보 검사, 10% 교통 개선은 아직 완료하지 못했다.

## 확정된 N_UF

사용자 선택: **8개 램프에서 실제 본선으로 들어갈 예측 유량의 합 [veh/h]**.

기존 450초 예측 지평을 유지하며 다음 수량으로 구현한다.

`NUF_pred = (3600 / 450) × Σ_m Σ_j accepted_merge_vehicles[m,j]`

- 집계 경계는 각 램프의 **본선 합류**다. 미터 신호 head 통과와 램프 진입은 별도 기록한다. 램프 안에 남은 차량은 아직 합류 유량에 포함하지 않는다.
- 실제 수용 가능한 예측 합류량은 목적지별 도착·재고, 녹색 서비스, 본선 receiving에 의해 정해진다. 녹색 서비스 상한이나 CSV의 `900 × green/10` 인코딩을 유량으로 대체하지 않는다.
- 450초 총 차량 수와 평균 veh/h를 함께 기록한다. 첫 150초의 실현·예측 비교는 별도 창으로 보고하며, leader 제약의 집계 지평을 몰래 150초로 바꾸지 않는다.
- `N_UF_star`는 고정된 leader 목표, 위 식은 후보별 예측 실제량이다. 후보에 맞춰 목표를 다시 쓰지 않는다. 기존 4그룹 합 7,200veh/h는 과거 정의의 기록으로 보존하며 새 목표로 자동 승계하지 않는다.
- 동서 두 방향과 8개 램프의 부분합을 모두 남긴다. 한 램프의 미방출량을 같은 그룹의 다른 램프로 재배분하지 않는다.
- 합류는 Ω 내부 이동이므로 Ω의 TTD가 아니다.
- 현재 생산 코드는 `shared_quantity_constraints`와 최종 transport에서 여전히 4그룹 명령률 합을 검사한다. 아래 속도 실험도 그 과거 수량 계약을 유지했다. **새 N_UF 정의를 적용한 제어 결과로 해석하면 안 된다.** 8개 독립 재고·합류 흐름을 연결한 뒤 수량 검사·가격·초기화·출력 검증을 함께 전환해야 한다.

## 기존 정본 코드에서 수정한 것

1. `area_follower_objective.py`: 한 물리 응답 동안 cyclic GC를 지연하고 종료·예외 시 회수 및 기존 GC 상태를 복원한다. 회수 시간도 비용에 포함한다. 단순 참조 카운트 해제는 계속 작동한다.
2. `joint_owner_neighbors.py`: 큰 고정 문맥의 반복 Python 재귀 비교를 정확한 builtin 직렬화 비교로 단축한다. 직렬화가 다르면 기존 canonical 검증으로 돌아간다. 실제 방문 후보는 물리 writer·소유권·고정 박스 검사를 수행한 뒤에만 평가한다. 미방문 후보의 중복 전체 writer 검사는 선택적으로 지연한다.
3. `area_follower_objective.py`: 첫 후보 응답을 기존 정확 캐시에 worker 수만큼 미리 계산한다. 19개 전부의 완료를 기다리는 방식은 마감 전에 게임이 응답을 사용하지 못했으므로 폐기하고, 4개씩 소비하도록 수정했다. 후보 영역·가격·선택 규칙은 유지했다.
4. Worker 마감 예외 때 값이 그대로인 고정 문맥을 불필요하게 unpickle하여 자기 검증을 깨뜨리는 경로를 수정했다. 변화 없는 builtin 문자열 set도 clear/update로 재구성하지 않는다. 실제 변경 검사는 유지한다.

새 기능은 기존 `control_area_objective` config의 `defer_response_gc`, `defer_unvisited_command_checks`, `prefetch_first_owner_responses`로 명시적으로 켠다. 없는 설정의 경로를 바꾸지 않는다. adapter·VBS·PowerShell 실행 경로를 복제하지 않았다.

## 측정 결과

근거 디렉터리: `diagnostics/control_improvement/decision_common_anchor_20260911/`.

| 실험 | 측정 결과 | 판정 범위 |
|---|---|---|
| 80/50 기록 상태 900초, 같은 450초 단일 응답 | GC 기존 4.058초 → 지연 3.461초 | 회수 포함 약 14.7% 단축. full point·response·states의 pickle SHA 모두 정확히 동일 |
| 같은 후보 생성·writer 미시 비교 | 기존 0.340/0.342초 → 수정 0.225/0.218초 | 두 실행 순서에서 후보·명령·provenance pickle 동일. 전체 decision 단축률 아님 |
| 기존 GC, 4worker 전체 decision | 전체 111.147초, 가격 99.605초, game 평가 1회 | 시간 내 검증된 hold 출력. 전체 순회 0 |
| GC 지연, 4worker 전체 decision | 전체 111.141초, 가격 83.086초, game 평가 5회 | 공통 가격 값·기준 레버·기준 응답 token·단위 동일. 가격 구간 약 16.6% 단축 |
| 전 owner 응답을 한꺼번에 기다린 시험 | 전체 111.106초, game 평가 0회 | 실행 출력은 유효하지만 탐색 개선 실패. 보존하고 이 방식을 교체 |
| 4개씩 응답을 미리 계산한 최종 시험 | 전체 111.238초, 가격 83.354초, game 평가 17회 | 8개 도시 owner의 기준 및 비기준 후보, 다음 도시 owner의 기준 평가까지 확인. 전체 순회 0, FW 탐색 미도달 |

전체 decision 비교의 자료는 **70/30의 기존 저장 상태 1050초·실제 행동 900초**다. 선택한 80/50 교통 시나리오의 신규 런이 아니다. 전체 예산은 120초, 최종 출력 예약 10초, 물리 모델·450초 지평·수요·명령 박스를 유지했다. 남는 시간에 탐색이 계속되므로 전체 경과시간은 약 111초로 유지됐다. worker별 CPU/응답 시간의 합을 병렬 전체 wall time과 합산하면 안 된다.

최종 시험 `controlled_t1050_prefetch_v2`는 exit0, 실행 중 source 변경 없음, worker pool 종료 및 잔여 소유 worker 없음으로 완료했다. JΩ는 기준 hold 165.1501에서 선택 165.1631veh·h다. 이는 같은 Ω 목적함수 기준의 개선이 아니며, own-payoff 선택을 전체 교통 개선으로 해석하지 않는다. 모든 최종 gap은 미확인이고 GNE 인증은 없다.

## 실패·미완료의 보존

- C pickle로 응답 복사를 치환한 시험은 일부 참조 공유/직렬화 동일성이 깨졌고, 보완 후에도 일관된 시간 이득이 없어 생산 변경을 되돌렸다. trial 코드와 실패·비교 자료는 보존했다.
- `controlled_t1050_runtime_v1`의 초기 `Frozen joint query context changed`는 실패 자료를 보존한다. set 재구성의 직렬화 변화는 별도로 재현해 수정했지만, 이 초기 실패의 단일 원인으로 확정하지 않는다.
- `controlled_t1050_runtime_debug_v2`의 worker 마감 후 `Private fixed game inputs changed`는 불필요한 문맥 재구성 회귀 검사로 수정·검증했다.
- 기존 짧은 native 실행의 독립 LSA coverage 실패와 예측 방출 오차는 해결되지 않았다. LDP/readback 통과를 LSA 통과로 바꾸지 않는다.

## 검증과 다음 순서

최종 관련 110개 unittest 통과(11.007초). 실제 응답 batch, GC 예외 복원, immutable 문맥·typed key, writer 후보 동일성, deadline/hold, round-robin, 캐시, 최종 leader/action transport를 포함한다. `verify_parameters.py config_parallel4_prefetch.json` PASS. 실제 기록 상태 전체 decision 재현을 별도로 완료했다.

속도 개선으로 확보한 시간이 아직 19개 owner를 모두 평가하기에는 부족하다. 다음 연결은 독립 8개 램프의 재고·경로 귀속·정확한 합류 셀과 녹색 전략이다. 사용자 지정 **10초 cycle, RED/GREEN만 사용, 직전 실제 녹색 기준 ±2초/150초**를 유지한다. 그 응답의 합류 수량으로 새 N_UF를 계산하고, 같은 목표·박스 안의 초기화 및 제약/가격/출력을 함께 연결한다. 그 뒤 필요한 짧은 native 비교와 연속 제어 단계를 수행한다. 8개 분리가 검증되기 전에 4그룹을 나눠 기록만 채우거나 full run으로 성능을 주장하지 않는다.
