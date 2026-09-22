# 도시부 예측 계산의 배열 직접 사용

2026-09-22 사용자 요청: 저장 배열을 다시 객체로 꺼내 계산하는 경계를 줄이고, 계산시간마다 SDMPC iteration 횟수를 함께 보고한다.

## 변경 범위

`sdmpc_array_urban_pipeline` 하나로 켜는 선택 기능이다. `prediction_cache`, `fast_primitives`, `reverse-v1`을 요구하며 기본 설정은 바뀌지 않는다.
`physical_urban_transport.UrbanTransport.step`의 재고·sending/receiving → 횡방향 요청/배분 → FIFO prefix 요청/배분 → 이동 → compact → 체류비용·차량 보존·저류용량 검사를 하나의 컴파일 계산 경로로 옮겼다.

내부 차량 조각은 `(integer label ID, value, reverse node ID, active flag)`의 연속 숫자 레코드로 처리한다. 레코드 중간마다 Python Dual 객체를 만들지 않는다. NumPy FIFO 버퍼는 후보 예측 스코프가 소유하며, 해당 도시부 계산이 사용하는 큐만 등록한다. 나머지 램프/경로 큐는 기존 표현을 유지한다.

**최종 연결은 미분 예측에만 적용한다.** 일반 후보 예측에 같은 배열 경로를 적용한 동시점 측정은 OFF 57.599초 / ON 61.992초로 느려졌다(`states_v1`의 개별 witness receipt; 각 단일 450초 예측이며 최적화 iteration을 실행하지 않았다). 따라서 scalar 후보·검증 예측은 기존 경로를 유지하고, reverse AD worker의 미분 예측 스코프 안에서만 배열 경로를 사용한다. 이는 제어/정확도 근사가 아니라 표현 선택이다.

셀 초기 receiving 예산을 횡방향·종방향이 공유한다. 같은 초에 나간 공간을 새 receiving으로 재사용하지 않는다. 차량 ID, 미지정 목적지, 통행 가능한 FIFO prefix, 출구별 수용 한도, 신호, 비용·보존 검사와 세 제어 구간을 유지한다. 실패한 검사는 기존처럼 예외다.

객체 변환은 도시부 계산에 들어오는 신호·경계유량과 나오는 경계 이동 증거·진단 상태에서 수행한다. **전체 망 예측의 모든 객체를 제거한 것은 아니다.** 외부 Ω 회계, 경로 예측, 본선 및 다른 도시부 계산은 여전히 기존 경로다. 수치 버퍼와 공개 상태의 연결을 유지하기 위해 스냅샷/예측 종료 때 FIFO를 변환한다. 게시되지 않은 배열 상태를 갖는 중첩 예측 스코프는 명시적으로 거부한다.

## Sensitivity 갱신 규칙

`sdmpc.py`는 outer iteration k에서 현재 제어열 `u^k`의 예측과 Jacobian을 구한다. 한 iteration 안의 QP, line search, restoration은 그 Jacobian을 공유한다. 새 제어열이 수락되면 다음 iteration은 `u^(k+1)` 기준으로 다시 구한다. 최초 관측 상태는 고정되고 예측 궤적이 달라진다.

캐시·비동기 선계산은 동일한 제어열과 비용/자원 응답을 검증한 경우에만 사용한다. 다른 제어열의 미분을 고정하여 재사용하는 근사로 바꾸지 않았다. 따라서 2회 iteration으로 `u^2`를 수락했다면 `J(u^0)`, `J(u^1)`을 쓴 것이며, `J(u^2)`까지 계산했다는 뜻은 아니다.

## 검증 기록

증거: `diagnostics/sdmpc_array_pipeline_20260922/`. 실패한 초기 컴파일/연결 로그도 보존한다.

- 기존 소스를 보존한 OFF/ON 대조: 유한/무제한/닫힌 출구, 명시적·미지정 목적지, fallback, 횡방향 FIFO, 적색 신호, defer/prefer/footprint, 혼합 정수/실수 라벨 조건의 20개 조합. 수치·차량 순서·이동 경로 및 라벨 표현 일치, Jacobian 절대오차 1e-12 이내.
- SDMPC 회귀 136개 PASS (`regression_v3.log`).
- 기존 실제 결합 테스트 OFF 9개 / ON 9개 PASS (`coupling_v4.json`).
- `verify_parameters.py` PASS (`parameters_v1.log`).
- 실제 저장 900초 상태, 450초 horizon, 3×150초 제어, 231축의 단일 Jacobian (`pipeline_h3_v2`): 비용·제약·두 Jacobian의 기존 결과 대비 최대 차이 0. 역전파 그래프 14,137,087개 node로 기존과 동일. 내부 scalar/tangent 전체 상태 대조도 통과.

단일 Jacobian 시간은 최적화 iteration을 실행하지 않은 측정이다. 첫 배열 경로 148.360초에서 불필요한 FIFO 변환과 중복 재고 합산을 줄인 경로 145.511초. 기존 선택 경로의 과거 측정은 143.419초다. 이 단일 측정만으로 전체 결정 속도 개선을 주장하지 않는다.

첫 전체 결정은 **426.878635초**였다. 후보별 iteration 상한 2회, 선택 후보 2회 수락, `converged=False`이며 6회 수렴 결과가 아니다. 다른 NP 후보도 각각 2회/0회 수락(마지막 후보는 첫 QP 실패)했다. 실제 endpoint 예측 6회는 iteration 횟수와 다르다. 기존 빠른 경로의 과거 386.692933초보다 10.39% 느려 속도 개선 경로로 채택하지 않는다. 이전 저장만 배열로 연결한 444.001963초보다는 짧다.

`pipeline_h3_v3`의 단일 Jacobian은 147.576788초(최적화 iteration 미실행)이며, 기존 결과 대비 비용·제약·Jacobian 차이는 0이다. node 수, branch event 수, exact-tie/discrete 축도 동일하다. 새 배열 내부 step 450회의 합은 13.507429초이고 그중 컴파일 kernel은 2.708298초다. 일반 scalar 예측은 기존 경로를 유지한다.

`states_v2`의 독립 OFF/ON 비교에서 전체 상태·비용·제약 차이가 0이며, 전체 결정의 23개 검증도 PASS다(`qualification_summary.json`). native VISSIM/9000초 비교를 수행한 결과가 아니다. 남은 재포장/회계 변환을 줄이는 후속 수정은 별도 증거 폴더에서 진행한다.

초기 전체 상태 비교 `states_v1`은 실패 기록이다. 물리 유량은 같았지만 출구 이벤트 표현이 `('exit', 10634.0)`에서 `('exit', 10634)`로 바뀌어 문자열로 보존된 자원 배분 키가 달라졌다. 비교기를 완화하지 않았다. 최종 구현은 수치적으로 같은 차량 identity와 원래 라벨 표현을 별도 정수 ID로 보존하고, 각 prefix 배분에서 원래 첫 요청의 출구 표현을 전파한다. 혼합 라벨 테스트를 추가했다.
