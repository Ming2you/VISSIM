# SDMPC FIFO 순회 최적화와 150초 × 3개 입력

사용자 승인 범위는 조각 관리/반복 순회를 먼저 개선하고, 이어서 서로 다른 세 제어입력을 최적화하는 것이다.
VISSIM과 9000초 세 조건 비교는 재시작하지 않았다. 실행 checkout은
`C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921`이다.

## 설정과 제어 의미

다음 실행 설정: `diagnostics/sdmpc_sequence_20260921/config_candidate.json`.

- `adapter.sdmpc_fifo_batch: true`: 차로 변경 단계 동안 같은 label의 조각 위치를 재사용한다.
- `adapter.sdmpc_control_blocks: 3`: 150초씩 독립된 세 입력을 사용한다. `sdmpc_derivatives: tangent-v1`이 필요하다.
- 두 키가 없으면 기존 한 입력 유지 경로/기존 FIFO 처리 경로를 유지한다.
- 무거운 실제 차량 관측은 기존 수정대로5초, 물리 예측 적분은1초, 실제 명령 갱신은150초다.

77개 좌표(녹색46, offset17, meter8, VSL6)를 각 구간에 배치해231개 좌표를 만든다.
하나의450초 공통 예측에서 모든 도함수를 직접 전파한다. solver에서 제어값을 바꿔가며 미분하는 FD는 사용하지 않는다.
각 owner의 prox-linear QP도 세 구간 좌표를 함께 조정한다.

녹색 합/최소/최대/동시 현시 제약은 각 구간에 적용한다. 첫 구간은 실제 직전 명령과,
두 번째와 세 번째는 각각 바로 앞 계획 입력과 변화량을 비교한다. offset은 원형 차이를 연속 좌표로 펼친다.
meter/VSL은 최종 후보에서 실제 허용값으로 투영한 뒤 모든 구간의 제약을 다시 확인한다.
예를 들어 현재 미터10초에서8→6→4초는 허용되며, 한 구간에서2초를 초과하는 변경은 거부한다.

NP는 기존450초17-owner accepted signed service cap, NUF는 기존450초 실제 본선 합류량 목표를 유지한다.
구간별 service ceiling 합이나 새로운 가격/용량/교통 계수로 바꾸지 않았다.

`ControlAction`의 기존 물리 명령 필드는 첫 구간만 나타낸다. 미래 두 입력은
`diagnostics.sdmpc_prediction_sequence`의 JSON 가능 예측 메타데이터로 보관한다.
기존 단일 endpoint의 coupling 호출에서150초 경계마다 해당 입력을 선택하고 전체450초 ledger로 평가한다.
예외가 나도 임시 coupling 선택기를 복구한다. 실제 writer는 첫 명령만 쓰며 다음 결정은 새 관측에서 다시 계산한다.
직전 명령에 저장된 미래 계획을 이미 실행한 명령으로 취급하지 않도록 다음 solve 진입 시 제거한다.

## FIFO 최적화와 첫 검증

기존 FIFO의 label/차량량/순서는 바꾸지 않는다. 서로 다른 목적지 사이의 조각을 합치거나 작은 차량량을 버리지 않는다.
한 차로 변경 단계 동안 label별 조각 위치를 인덱싱하고, 소진된 prefix를 다시 방문하지 않으며,
모든 요청 처리 후 한 번만 물리 FIFO를 복구한다. 숫자값이0이어도 미분이 남아 있으면 다음 조각에 전파한다.
과잉 차감 검사의 합산 순서는 기존 순서를 유지한다. 양수 prefix만으로 기존 판정이 확정되면 합산을 끝낸다.
경계에서는 원래 전체 합을 계산하므로 마지막 ULP에서의 과잉 차감 거부도 유지한다.

같은900초 저장 상태/같은 유지 명령에서 첫 인덱싱 수정 전후를 대조했다.

| 예측 지평 | 수정 전 일반/미분 | 인덱싱 후 일반/미분 | 상태 및 Jacobian 차이 |
|---|---:|---:|---:|
|150초|24.40 / 68.04초|23.60 / 66.44초|전 항목0|
|450초|211.64 / 826.12초|173.81 / 673.44초|전 항목0|

`diagnostics/sdmpc_sequence_20260921/fifo_h1/comparison.json` 및 `fifo_h3/comparison.json`.
이는77개 축의 공통 미분 시간이며 전체 SDMPC 결정 시간이 아니다.
450초 미분 시간 감소는 약18.5%이고150초 계산 목표는 미달이다.
당시 코드는 `fifo_h3/sources/`와 `before/`에 보존했다.
최종 코드의 양수 prefix 합산 단축은 이후 세 입력 검증에 포함된다. 위 시간을 그 추가 수정만의 효과로 해석하지 않는다.

후반5초 프로파일에서 FIFO `take_label`은249표본 중0개, 도시부 native route/prehead
`receive_accepted`를 포함한 stack은122개였다. 전체 실행의 시간 비중을 나타내는 통계는 아니다.
경로별 차량 묶음과 직접 미분의 비용이 남아 있으며, 이 자료로 모든 계산 병목이 해결됐다고 주장하지 않는다.

## 검증 진행 기록

- FIFO 순서·질량·미분 동등성,0값/비영 미분, 마지막 ULP 과잉 차감 거부 검사.
- 세 구간 causal sensitivity,150초 경계 선택, 잘못된 clock/불완전 예측 거부와 hook 복구 검사.
- 저장900초 조건에서231좌표, 구간별 native 제약,8→6→4 meter 변경, 미래 offset만 변경되는 경우 검사.
- 기존 lane coupling/관측/신호/5초 수집 검사를 포함하여58개 PASS. 별도 Python 워커로 실제 계획을 전달해 동일 pickle 바이트가 유지되는지 검사했다.
- `verify_parameters.py diagnostics/sdmpc_sequence_20260921/config_candidate.json`: PASS. 기존 calibration override 경고는 유지된다.
- 실제900초 상태의231축450초 검증 PASS: 일반 예측171.45초, 미분759.86초.
  checkpoint 저장과 전체 상태 검산을 포함한 진단 소요는1089.55초다.
  같은 입력 세 개의 일반 상태는77축 기준과 완전히 같고, 구간별 Jacobian 합의 최대 차이는1.09e-12 미만이다.
- 각 구간에서 green 한 방향씩 별도 FD로 검산했다. 상대 L2 오차는 각각0.00218%,0.000327%,0.00477%이며 세 경우 모두 PASS.
  이FD는 독립 진단이며 실제 SDMPC solver에는 들어가지 않는다.
- 정수 실행 모델에서 한 prox-linear step을 평가했다.19개 owner QP와 자원 투영에1.377초,
  유지 예측과 두 후보의 원 모델 확인에는 합계299.13초가 들었다. 전체 SDMPC 결정 시간은 아니다.
  모든 후보의 물리 상태/자원 제약 검사는 완료되었고, 첫 구간만 writer에 전달되는213개 명령 행 증거도 통과했다.
  각 후보에서 구간별 변경 좌표 수는58/58/47이고 서로 다른 세 입력을 사용했다.
- 현재 유지 순유입량552.4413대를 진단 상한으로 고정한 조건에서 두 후보의 NP 초과는9.26084대/3.30005대다.
  NUF 오차는-3.05770/-1.90644veh/h로 기존40veh/h 허용 범위 안이다. 두 후보는 NP 제약 때문에 모두 거부했다.
  비용 감소3.4753/1.9002veh-h(0.864%/0.472%)는 **미채택 예측값**이며 제어 성능으로 주장하지 않는다.
  이 상태에서는 RM/VSL이 구간별로 변하지 않았다. 본선 제어 이득을 확인한 결과가 아니다.
- 기존 설정의 최대2회 제약 복원까지 실행했다(293.43초). NP 초과는3.30005→0.90322→-1.94611대로 줄었다.
  마지막 입력의 NP550.49519대는 상한552.44130대 이하이고, NUF5145.27384veh/h는 목표5144.21439와1.05946 차이다.
  마지막 후보는 모든 모델/자원/구간별 actuator/변화량/NP/NUF 제약과 첫 구간 writer 검사를 **통과**했다.
  Ω 예측TTT402.31251→400.43822veh-h(약0.466% 감소)인 채택 가능한 한 step이다.
  원래 최대2회 설정, 상한, 허용오차, 모델을 바꾸지 않았다. 초기 거부 후보와 첫 실패 복원도 그대로 보존했다.

결과 경로:

- `diagnostics/sdmpc_sequence_20260921/three_blocks_h3/comparison.json`: 세 입력을 같은 값으로 둔 전체 상태와77축 Jacobian의 block합 대조.
- `diagnostics/sdmpc_sequence_20260921/sequence_proposal_v3/report.json`: 한 prox-linear step의 세 구간 후보, 원래 정수 실행 예측의 자원 제약, 첫 구간 writer 증거.
- `diagnostics/sdmpc_sequence_20260921/sequence_directions/report.json`: solver 밖에서 각 구간 green 미분을 독립 검산.
- `diagnostics/sdmpc_sequence_20260921/sequence_restoration/report.json`: 같은 상한과 기존 반복 횟수로 제약 복원 결과.
- `diagnostics/sdmpc_sequence_20260921/sequence_restoration/final_plan.json`: 세 구간 실제 제어값과 첫 구간 writer 행. VISSIM에는 적용하지 않은 검토용 계획.
- `diagnostics/sdmpc_sequence_20260921/qualification_summary.json`: 전체 요약. `change_sources.json`: 이번 수정 소스 SHA256.

이 검사는 과거1초 관측으로 저장한900초 상태를 재사용한다. 다음 실제 런의5초 관측 간격을 다시1초로 바꾸지 않는다.
짧은 native 적용, 전체 SDMPC 결정의 수렴/시간,9000초 NC/CL 성능은 이 문서의 오프라인 검증과 별개다.

## 워커 전달 수정과 증거 범위

첫 후보 검증은 sandbox에서 scipy.optimize를 읽지 못해 종료했다(`sequence_proposal.log`).
SciPy 접근을 확보한 두 번째 실행은 미래 계획의 pickle hash가 워커 경계에서 달라져 종료했다(`sequence_proposal_v2.log`).
기존 hash 검사를 완화하지 않았다. 미래 payload의 field-name 문자열이 최상위 ControlAction 속성 키와 같은 객체를 공유하면,
unpickle이 속성 키를 재구성하면서 값은 같아도 pickle memo 바이트가 달라지는 것이 원인이었다.
미래 payload 키에 값이 같은 독립 문자열을 사용해 실제 저장 상태/새 워커 왕복 검사까지 통과했다.

231축 수치 결과는 **전달 수정 전 소스에서 수행한 결과 그대로**다. 이전 source는`three_blocks_h3/sources/`에 보존했다.
`check_sdmpc_sequence_transport.py`는 AST에서 해당 dictionary key 표현식 한 곳만 바뀌었음을 강제하고,
일반/미분 값을 포함한 세 제어의 decode 결과가 바이트까지 같음을 확인한다. 수치 계산을 다시 했다고 표기하지 않는다.
`sequence_proposal_v3/source_equivalence.json`에 이전 미분 소스와 현재 native 예측 소스 SHA256을 모두 남겼다.
현재 소스는 native worker bootstrap에서 별도 hash로 고정된다. 다른 계산식이 바뀌면 이 검증은 거부된다.

## 종료 시점

오프라인 검증 프로세스는 모두 정상 정리했다. VISSIM/기존 감독/9000초 비교를 재시작하지 않았다.
실제 적용 config는 이 문서의`config_candidate.json`이며 기존 고정 실행 자료는 수정하지 않았다.
완료 범위는 FIFO 최적화,231개 독립 제어 좌표의 미분과 시간 배치,
동일 저장 상태의 한 prox-linear step 및 기존 제약 복원 검증이다.
전체 cap 탐색·반복의 수렴/한 결정 총시간과 실제 제어 효과는 미검증이다.150초 계산 목표도 미달이다.

## 후속: 병렬 미분과 경로 집계

이후 승인된8워커 미분과 도시부 경로 집계는[SDMPC_PARALLEL_AGGREGATE_20260921.md](SDMPC_PARALLEL_AGGREGATE_20260921.md)에 기록했다. 위 수치와 증거는 당시 결과로 그대로 보존한다.
