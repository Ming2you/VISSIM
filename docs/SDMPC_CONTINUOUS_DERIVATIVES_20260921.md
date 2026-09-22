# SDMPC 연속 완화와 직접 민감도 전파

사용자 우선순위: SDMPC 미분을 먼저 수정한다. VISSIM/9000초 비교는 중단 상태를 유지한다.
작업 브랜치 `codex/sdmpc-tangent-20260921`; 이전 `lane-inventory-20260921`의
`sources_v6.json`에 고정된 554개 내부 파일을 검증하여 가져온 별도 checkout이다.
5초 차량 관측 작업은 `observation-5s-20260921`에서 검증하여 이 checkout에 통합했다.
다음 검증용 설정은 `diagnostics/sdmpc_continuous_20260921/config_candidate.json`이다.
새 미분 옵션과 `urban.capacity.head_observation.sample_interval_sec: 5`를 켰으며
파라미터 검사는 PASS했다. 과거1초 자료로 하는 미분 대조 검사는 원래 관측 간격을 유지한다.

## 원인과 변경

Numerical-Sim `b53ebd72e512fb365bc5ebbabf1e9f40e5c08ed5`의 최신
`work/sdmpc_proxlinear_20260916` 경로는 sparse forward 민감도와 예외 축의 FD를
사용한다. 기존 VISSIM 이식에는 이 엔진이 빠져 공통 기준점의 77개 좌표를
모두 FD로 계산했다. 저장된 900초 상태에서 변경된 끝점은 136개였다.

새 경로는 `adapter.sdmpc_derivatives: "tangent-v1"`로 켠다. 키가 없으면
기존 SDMPC 미분 경로를 사용한다. 수치는 `evaluation/parameters.json`의
`sdmpc_tangent`만 읽는다. vendor 파일과 이전 실행 checkout은 수정하지 않는다.

사용자 후속 지시에 따라 예측 제어변수를 연속화했다. 정수 실행 모델의 거의
모든 곳에서 0인 미분을 그대로 최적화에 넣지 않는다.

- 신호: native 현시 순서·clearance·cycle을 유지하면서 GREEN 창을 2초 폭의
  compact cubic kernel로 평활화한다. 각 1초 구간의 평균 service fraction을
  적분한다. 한 cycle의 총 GREEN 적분은 원래 녹색시간과 같다. offset도 이
  이동한 창의 도함수로 전달한다.
- 물리 도시부: SC1004의 신호 정지선에서는 연속 fraction으로 차로별 출구
  예산을 제한한다. 같은 출구 예산을 FIFO 조각마다 새로 부여하지 않는다.
- Meter: 기존 측정 service table의 이웃 점을 선형 보간하고 cycle 평균으로
  공급한다. 녹색 정수화와 RED clock은 실행 모델에서 적용한다. 계수나 용량을
  새로 적합하지 않는다.
- VSL: 예측 민감도에는 실수 속도값을 넣는다. 기존 허용 속도 집합은 최종
  후보를 만들 때 적용한다.

한 공통 예측에서 상태·비용·실제 자원량의 chain rule을 동시에 전파한다.
예를 들어 `S[k+1] = F_x S[k] + F_u`에 해당하는 연산을 sparse tangent가 수행한다.
QP 자체는 기존처럼 traffic rollout을 하지 않는다. 이 경로의 미분 계산에는
제어값을 흔든 FD 후보를 만들지 않는다.

모든 물리식이 전역적으로 매끄러워졌다는 뜻은 아니다. 수용량 min/max, FIFO
분기, 이동시간의 이산 이벤트 등에서는 현재 분기에 대한 국소 미분을 사용하며
그 사건을 trace에 남긴다. 새 경로는 FD 후보를 사용하지 않으므로 가상의 FD
stencil 교차 및 출력까지의 위험 전파는 계산하지 않는다. `trace_mode`,
`stencil_crossings_assessed=false`, `output_risk_propagation=false`로 명시한다.
기록된 tie 축은 보수적인 후보 집합이며, 매끄러움의 증명이 아니다.
신호·meter 연속화는 미분용 예측의 명시적 근사다.
따라서 기존 정수 실행 예측과 비용이 같다고 주장하지 않는다.

## 실행 가능한 명령과 검증

연속 QP 결과를 기존 `Coordinates.decode`로 허용된 actuator 값에 투영한다.
모든 값을 일괄 ceiling하지 않는다. 녹색 예산·현시 하한·offset 주기·미터 최소
녹색·VSL 집합·직전 명령 대비 변화량 제한을 기존 검증으로 확인한다.
각 최종 후보의 원래 비선형 예측/제약/목적함수 확인도 유지한다.

미분용 연속 예측과 실행 예측의 기준점 값 차이는 숨기지 않고
`anchor_correction_costs/resources`에 기록한다. 국소 제약의 기준점 잔차는
기존 실행 예측값을 사용한다. NP는 17개 owner의 실제 kind-signed accepted
service, NUF는 실제 본선 합류량이며 command 합으로 바꾸지 않는다.

별도 Python child에서만 수치 primitive를 계측한다. 같은 연속 예측의 scalar
상태와 tangent의 primal 상태를 모든 저장 field에서 비교한다. 코드 module
참조는 동일 객체/소스로 확인하고 interpreter 전체를 교통 상태로 취급하지
않는다. 암묵적 float 변환으로 미분이 유실되면 실패한다. 실패를 0 gradient나
조용한 전 축 FD로 대체하지 않는다.

## 완료한 검증과 범위

- 신호 주기 적분 보존, green/offset 도함수 수치 검산, meter 보간, 연쇄 미분,
  정밀 합산, implicit cast 차단, 상태 비교기 및 기존 lane coupling 검사를 추가했다.
  이후 동일-label FIFO 처리의 primal/Jacobian 동등성, 과잉 차감 경계의 기존
  덧셈 순서, 경량 trace의 도함수 보존 및5초 관측 검사를 포함하여45개 PASS.
- `verify_parameters.py diagnostics/tangent_900_h1/config.json`: PASS.
- 저장된 실제 900초 상태, 150초 예측에서 scalar 23.74초, 77축 tangent
  104.80초. 20개 owner/passive 비용과 두 실제 자원량의 primal 오차는 모두0.
  저장한 전체 물리 상태의 최대 오차는9.095e-13으로 재검증 PASS했다.
  `diagnostics/tangent_900_h1/revalidated_h1.json`.
- 초기 검사는 deque/module 참조에서 실패했고, 이후 sparse transfer 로그의
  길이도2개 달랐다. 실제 차이는 각각1.33e-15,1.78e-15대의 sink event였다.
  같은 시간·출발·도착·route의 vehicles/TTD/entry를 모두 합산 비교하고,
  event counter를 실제 기록 개수로 검증하도록 비교기를 고쳤다. 이벤트를
  지우거나 예측을 수정하지 않았다. 물리 상태/cohort 비교는 유지한다.
  실패 기록과 원본 예측을 `result_attempt*.json`, `prediction_attempt05.pickle`,
  `prediction_attempt05.audit.json`에 보존했다.
- 별도 수치 미분 검산은 solver 경로 밖에서6개 scalar 예측, 최대8워커로
  수행했다(34.54초). 대표 green 상대오차4.18e-8, meter7.08e-9, offset0.006164.
  offset 차이는 활성 분기 근사에 남아 있으며 전역 매끄러움을 주장하지 않는다.
  대표 VSL 축은 이120km/h 기준점에서 양쪽 방법 모두0이었다.
  `diagnostics/tangent_directions_v1/report.json`.
- 연속 QP→native 명령 투영 및 writer dry-run PASS: QP0.921초,
  선형 제약 잔차1.05e-13, green31축·offset13축 변경. 이 검사는 actuator
  도메인 검사이며 비선형 NP/NUF 실행 가능성 검사가 아니다.
  `diagnostics/tangent_900_h1/projection_check.json`.
- VSL80km/h 가상 기준점의150초 예측도 PASS: scalar24.36초,
  tangent117.95초, 검증·저장 포함171.56초. 6개 VSL 축 모두 비영 Jacobian을
  확인했다. 물리 상태 최대 오차9.095e-13. 이 기준점은 VSL 전달을 확인하기
  위한 진단이며 직전120에서 이번 결정에80을 적용할 수 있다는 증거가 아니다.
  `diagnostics/tangent_900_vsl80_h1/result_attempt01.json`.
- 경량 미분 및 FIFO 검사 최적화 후 같은900초 기준점의150초 예측도 PASS:
  scalar24.40초, tangent68.04초, 검증·저장 포함118.78초.
  물리 상태 최대 오차9.095e-13. 이전 full-trace의20개 비용+2개 자원량,
  77축 Jacobian과 원소별 최대 차이가 모두0이다.
  `diagnostics/tangent_900_h1_v2/result_attempt01.json`, `full_trace_comparison.json`.
- 전체450초 Jacobian 대조도 PASS: scalar211.64초, tangent826.12초,
  전체 상태 대조·저장·프로세스 준비를 포함하여1194.20초(약19.90분).
  20개 비용+2개 자원의77축 행렬은 모두 유한하며 FD 미분 후보는0개다.
  모든 저장 물리 상태의 primal 최대 오차3.638e-12, 입력 불변과 소스 확인 PASS.
  `diagnostics/tangent_900_h3_v3/result_attempt01.json`.
  이 결과는 미분 검증 한 건이며 전체 SDMPC 결정시간이 아니다. 전체 결정,
  비선형 자원 제약을 만족하는 새 선택 명령, native 적용/9000초 성능은 미검증이다.
  150초 계산시간 목표도 달성하지 못했다.
- 첫450초 검사는 scalar223.34초 이후 tangent가30분 이상 계속되어 중단했다.
  `diagnostics/tangent_900_h3_v1/stopped_incomplete.json`에 미완료 상태와
  실제 중단 시간을 보존했다. 10초 프로파일498개 표본 모두 도시부
  `FIFO.take_label` 내부였다. 이동하지 않는 label의 모든 fragment에도
  전체 count와0 차감의 tangent 연산을 반복하는 것이 병목이었다.
  요청 label만 같은 순서로 합산·차감하고 다른 label은 그대로 보존하도록
  바꿨다. FIFO 순서·모든 label 질량·도함수·초과 차감 거부의 동등성 검사를
  통과했다. 물리식/기하/계수/시간 간격은 바꾸지 않았다.
  두 번째450초 검사 `diagnostics/tangent_900_h3_v2`도1276초 부근에서 동일
  label의 많은 FIFO 조각 때문에 느려져 미완료로 중단했다.
  다음 수정은 과잉 차감 assertion에만 쓰는 합계의 불필요한 tangent를 제거하고,
  원래 Counter와 같은 순서의 scalar 합을 유지한다. 다른 물리 합계는 미분한다.
  연속 미분에서 쓰지 않는 가상 FD 위험 전파와 상수0/1 산술의 중복 tangent
  계산도 제거했다. 미분값이0이 아닌 Dual은 숫자값이0이어도 제거하지 않는다.
  새450초 검사는 `diagnostics/tangent_900_h3_v3`에 분리했다.
- 과거 일반 신호/램프 테스트 일부는 이 checkout에 없는 과거 replay fixture와
  PROTOCOL 자료 때문에 시작하지 못했다. 해당 테스트를 PASS로 세지 않는다.

이 문서는 VISSIM native 적용이나 NC/CL 9000초 완료 증거가 아니다.

요약은 `diagnostics/sdmpc_continuous_20260921/qualification_summary.json`,
직접 변경한19개 코드·설정 파일의 SHA256은 같은 폴더의 `change_sources.json`에
보존했다. 기존 v6에 고정된 baseline의 해당 파일은 변하지 않았음을 확인했다.
미완료450초 시도v1/v2를 성공 기록으로 바꾸지 않았다. 마지막 오프라인 프로세스는
정상 종료했고 VISSIM/NC/CL 및 기존 감독을 재시작하지 않았다.

## 5초 차량 관측

무거운 전체 차량 조회와 차로별 파일은 startup1초 후5초 격자에서 수집한다.
신호 실행과 GREEN/RED 노출량 집계는1초 시계를 유지하고, SDMPC 명령은150초다.
5초 사이 RED를 한 번이라도 포함한 통과는 green-qualified로 세지 않는다.
차로 이동률은 frame 수가 아닌 실제 경과초로 계산하며, 다른 간격의 checkpoint를
재사용하지 않는다. 매초 차량을 조회한 뒤 파일만 덜 쓰는 변경이 아니다.
실제 VBS 함수와 가짜 COM으로 조회 횟수, 중복 호출, 신호 소유권 전환, window
초기화, 누락 시각 거부 및5초 provenance를 검증했다. VISSIM 실런은 하지 않았다.

## 후속: FIFO 순회와 세 구간 입력

이후 승인된 반복 순회 개선 및150초 ×3개 독립 입력 구현은
[SDMPC_SEQUENCE_20260921.md](SDMPC_SEQUENCE_20260921.md)에 기록했다.
기존 수치/실패 기록은 그대로 유지하며, 후속 검증도 VISSIM 실런과 구분한다.
