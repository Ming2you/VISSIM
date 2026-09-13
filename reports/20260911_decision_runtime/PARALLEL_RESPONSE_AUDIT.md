# 기존 가격 워커 재사용 조사

2026-09-11, 현재 source 읽기 전용 조사. 생산 코드 변경·worker 생성·모델/native 실행은 하지 않았다.

## 재사용할 부분과 그대로 쓸 수 없는 부분

| 기존 위치 | 재사용 가능한 역할 | 현재 제한 |
|---|---|---|
| adapter `install_price_worker_bootstrap()` | 실제 network 경로·detector mapping·runtime installer를 전송 | workers≤1이면 payload를 만들지 않음; controller를 pickle할 때만 `__setstate__` 경로가 작동 |
| `runtime_setup.install_worker_runtime()` | 동일 cfg에서 signal·tau·freeway·landing·route·Ω 모델 hooks 복구 | 부모 operational globals의 임의 현재값까지 같다는 증거는 아님 |
| vendor `stackelberg_wu_metered._price_worker_init()` | controller/state/previous/forecast를 worker별 1회 보관, 기존 patch marker 확인 | marker 하나는 전체 물리 동일성 증명이 아님 |
| 같은 클래스 `_price_batch()` / `_phase_price_rollouts()` | spawn executor·initializer·작업 순서 수집의 기존 패턴 | 현행 worker 결과는 legacy scalar J; native shared response/local C를 반환하지 않음. 매 batch 새 pool, timeout 없음, 예외 시 전체 직렬 재시도 |
| `area_follower_objective.make_decision_shared_query()` | 결정 하나의 고정 operand/runtime·정확한 full-action cache | 현재 직렬 closure; closure 자체를 spawn에 보내면 안 됨 |
| `_evaluate_shared_owner_batch_owned()` | 같은 response에서 J·19 owner C·NP/NUF 양·제약증거를 계산하고 compact 결과 반환 | frozen/action pickle은 process-local 검증값; 외부프로세스 identity 계약은 추가 필요 |

기존 가격 실행기와 같은 bootstrap을 **현재 shared query 안의 물리 miss batch**에 붙이는 것이 가장 작은 재사용 경로다. 별도의 adapter나 범용 pool registry는 필요 없다. 기존 scalar `_phase_price_rollouts()`를 부르면 현행 가격의 계산 정의가 달라지므로 대체로 사용할 수 없다. `grid_parallel._PROCESS_POOLS`는 전역·worker 수 키이며 context initializer와 hard deadline이 없어 이 작업에 더 적합하지 않다. thread pool은 adapter globals를 복원·재바인딩하는 `shared_query_runtime_scope()`와 충돌하므로 사용하지 않는다.

## 최소 연결안

부모 query가 현재와 동일하게 정확한 action key로 중복과 cache hit를 처리하고, miss만 원래 순서의 index와 함께 최대4개 worker에 보낸다. worker initializer는 이미 준비된 operand bytes와 runtime bytes를 1회 받아 기존 `install_worker_runtime()`을 호출한다. 설정 보정·관측 투영·가격 갱신은 다시 하지 않는다. 그 뒤 operational snapshot을 복원하고 `_PHASE_VECTOR_FOLLOWER['ref']`를 worker 소유 follower로 연결한다. 모델 installer가 만든 새 hook은 유지하고 매 query의 operational 데이터만 기존 scope 규칙으로 복구한다.

각 task는 같은 `_evaluate_shared_owner_batch_owned()`를 사용하고 compact 결과를 반환한다. 큰 captured trajectory는 worker 안에서 현재와 같이 폐기한다. 부모는 original index/action token/완료 evidence를 확인하고 원래 순서로 결과를 합친다. child completion 순서로 가격 합산·동점 처리 순서를 바꾸지 않는다. 실제 게임은 순차 결과에 의존하므로 이 병렬화는 먼저 독립적인 공통 가격 probe batch에만 적용하는 편이 범위가 작다.

기존 `cache_equivalence_v1.json`의 900초 조건에서 고정 operand는786,351bytes, runtime은60,349bytes, 두 compact 결과 합190,338bytes였다. 이는 현재1050초 조건의 측정값은 아니지만 매 작업 전체 controller를 보내기보다 initializer에서1회 전송할 근거가 된다.

## 동일성에서 빠지기 쉬운 부분

- follower만 전달하면 controller의 `PricedWuLinkStackelbergController.__setstate__()`가 호출되지 않는다. 따라서 bootstrap을 명시적으로 실행해야 한다. `__name__='__main__'`로 불린 adapter 이름을 spawn import 대상으로 삼지 않고 기존 import 가능한 canonical module 경로를 쓴다.
- 부모 runtime snapshot에는 `_CONFIG_SWITCHES`, freeway/lane context와 follower binding 등 실제 계산 입력이 있다. cfg만 같다고 이를 생략하지 않는다. 이미 추가한 native clock basis와 per-direction FD 속성도 worker cfg/hook에 남아야 한다.
- 현재 frozen token은 `pickle.dumps((follower,state,reference,forecast))`의 SHA다. set 순서·hash seed·unpickle 후 alias/caches 때문에 재직렬화 byte가 프로세스 사이에서 달라질 수 있다. 기존 코드도 이를 process-local key라고 명시한다. **전송한 고정 bytes의 digest**와 실제 source pins를 공통 provenance로 유지하고, worker의 local pre/post 불변 검사는 별도로 보존해야 한다. worker token을 검사 없이 부모 값으로 덮어써서는 안 된다.
- 반환값은 J만이 아니라 전체 compact 비용·양·제약증거와 full response content digest를 비교한다. payload/token만 같고 실제 numerical response가 다르면 실패다. 상호 별칭과 독립 반환 객체, cache OFF/ON 동작도 그대로여야 한다.
- 기존 vendor 병렬 테스트는 legacy green/grid/leader 경로의 근거다. 현재 Ω shared response + physical phase authority + native clock을 인증하지 않는다.

## 시간 제한과 소유 worker 정리

설치된 Python은 **3.12.14**, `ProcessPoolExecutor.terminate_workers()`가 없다. `with executor:` 탈출은 `shutdown(wait=True)`라 deadline 이후에도 진행 중 모델을 기다린다. `shutdown(wait=False,cancel_futures=True)`만으로 실행 중 작업이 종료되지 않는다. 기존 `_price_batch()`의 예외→전량 직렬 재시도도120초 제한과 맞지 않는다.

따라서 기존 executor의 **해당 인스턴스가 생성한 Process handle만** 기록하고, 남은 whole-decision 시간으로 future 대기를 제한해야 한다. timeout/error에서는 pending future 취소, 그 pool 소유 process만 terminate/join(짧은 제한), 필요하면 같은 handle의 kill, nonwaiting shutdown으로 닫는다. 다른 Python/VISSIM을 이름으로 찾거나 일괄 종료하지 않는다. 초기 spawn/직렬화 자체가 block될 때까지 엄격한120초를 보장하려면 기존 바깥 decision supervisor가 이 worker 소유권도 받아야 한다. cooperative `DecisionBudget.check()`만으로 이를 보장했다고 말하지 않는다.

측정은 parent 전체 batch wall, spawn 요청→각 worker ready(bootstrap 포함), worker endpoint wall/CPU와 local score wall/CPU, IPC 대기, 종료 시간을 분리한다. worker CPU는 합산 가능하지만 겹치는 worker wall을 parent 경과시간에 더하지 않는다. 실패·실제 시도·완료·검증 후 수용·cache hit를 각각 센다. 부분 결과를 full-rank 가격 완료로 인정하거나 deadline 실패를 조용한 직렬 retry로 숨기지 않는다.

첫 검증은 이미 저장된 동일 기준점의 공통 action과 green·offset·meter·VSL probe를 1worker/4worker에서 대조하고, 중복 요청·처리 순서 교란·initializer 오류·중간 worker 오류·timeout 및 소유 worker 잔존0을 확인하는 정도면 충분하다. 통과한 뒤 전체69방향+anchor를 같은 source/state에서 비교한다. 70×2.5초를4로 나눈43.75초는 startup·CPU/메모리 경합·score·basis 비용을 뺀 이상적 계산치이며 아직 실측 단축률은 아니다.
