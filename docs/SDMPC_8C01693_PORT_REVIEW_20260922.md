# Numerical-Sim 8c01693 → VISSIM SDMPC 이식 검토

2026-09-22. 이번 작업은 소스 수령·비교·단위 검사·이식안 작성이다. VISSIM controller/plant/config 변경, native 실행, 새 전체 결정 계산은 하지 않았다.

## 결론

새 controller의 핵심은 현재 SDMPC에 이식할 수 있다. Plant를 다시 만들 필요는 없다. 다만 **iteration별 하위 가격 갱신**, **최종 후보에서 별도로 회수한 중앙 승수**, **그 승수를 이용한 상위 budget 후보 생성**은 구별해서 연결해야 한다. 중앙 승수의 물리 제약 미분까지 포함하면 현재 worker 반환 자료의 확장이 필요하므로 단순 파일 교체는 아니다.

사용자 추가 지시: **N_UF는 실제 램프→본선 합류량으로 한다.** Numerical-Sim의 미터링 명령 합으로 바꾸지 않는다. 최적화 중에는 plant가 예측한 실제 수용 합류량, native 적용 후에는 관측된 합류량을 구분해서 기록한다.

추천은 기존 plant·권역·8개 독립 미터·3개 제어 블록을 보존하면서 새 가격/상위 탐색 알고리즘을 이식하는 것이다. N_UF 목표를 매 결정의 기준 명령 예측값에 고정하는 현재 정책도 함께 변경해야 상위 탐색이 합류 총량을 조절할 수 있다. 이번 검토에서는 그 정책을 실제로 변경하지 않았다.

## 소스 고정과 확인

- repository: https://github.com/Ming2you/Numerical-Sim
- requested branch: `codex/sdmpc-20260911`
- fetched HEAD: `8c016939a6c8a6994b60ca0836d00fdcfe096209` (요청 commit과 일치)
- 이전 수령본: `b53ebd72e512fb365bc5ebbabf1e9f40e5c08ed5`, 기존 checkout 보존.
- 새 검토 checkout: `C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-sources/Numerical-Sim-8c01693` (detached).
- VISSIM 비교 checkout: `C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/sdmpc-tangent-20260921`의 현재 작업 파일. 이곳은 기존 수정이 많아 Git HEAD만으로 현재 controller를 대표할 수 없다.
- release 지정 진입점: `work/sdmpc_central_reuse_matrix_20260922/batch.py`.
- 실제 클래스: `work/sdmpc_central_kkt_reuse_20260922/central_controller.py`의 `CentralKKTSDMPC`.
- release의 `source_selection.json`, `validation_recovery.md`, `validation_14400.md`와 실제 상속/호출 경로를 함께 확인했다. 이전 실험 클래스가 아니라 release 지정 경로를 검토했다.

## 무엇이 달라졌는가

|항목|수령한 새 controller|현재 VISSIM SDMPC|이식 판단|
|---|---|---|---|
|공통 민감도|변경된 iteration 기준점에서 갱신, 동일점 cache 재사용|이미 같은 원칙, AD/응답 cache 구현|현재 방식 유지|
|하위 가격|모든 player가 같은 가격으로 계산한 뒤 k→k+1에서 갱신|한 결정 안에서 가격 고정, 선택 결과로 다음 결정용 가격 계산|후보별 독립 가격 상태와 iteration 갱신 이식|
|상위 신호|하위 반복 가격과 별도의 중앙 승수 회수|중앙 승수 회수 없음|새 기능 필요|
|상위 후보|승수로 NP/NUF 방향 제안, 각 후보를 다시 풀고 검증|NP 후보만 선택, NUF는 같은 결정에서 고정|실제 합류량 목표도 후보로 탐색하도록 연결|
|NP|horizon net service의 ±10veh band|17개 도시 권역의 실제 signed service 합에 대한 상한|현재 상한 정의 유지, 양측 band를 그대로 가져오지 않음|
|NUF|meter 명령 합, 목표의 ±5%|8개 램프의 실제 수용 합류율, 목표의 ±40veh/h|사용자 지시대로 현재 물리량과 절대 허용폭을 기준으로 이식|
|제어 좌표|9 players, 18축, H3 내 동일 명령|19 owners, 77축×150초 3블록=231축|권역·8개 미터·독립 3블록 유지|
|지역 QP|box만 있어 clip으로 해석해 계산|green 합, move box, 블록 간 변화율 등의 선형 제약 포함|clip을 무조건 복사하면 안 됨|
|최종 검증|원 Numerical-Sim rollout과 이산 VSL gate|현재 가속 경로는 연속 surrogate; 별도 원 모델 audit 존재|surrogate/원 모델/native 검증을 별도 표기|

새 코드의 지역 QP 안에서도 교통 rollout은 하지 않는다. 이 부분은 현재 구현도 같다. 새 버전의 “민감도 재사용”은 모든 iteration에서 같은 미분값을 고정한다는 뜻이 아니다. **중앙 승수를 회수할 때 최종점을 다시 미분하지 않는다는 뜻**이다.

## 중앙 승수 회수의 범위

동일 budget 후보에서 실제 호출했던 선형화 기준점 중 최종 제어와 가장 가까운 점의 TTT gradient와 제약 Jacobian을 재사용한다. 활성 제약 판정은 이미 계산한 **최종 제어의 실제 rollout 제약값**으로 한다. 과거 선형화점의 잔차나 affine 예측 잔차를 최종 실제값으로 대체 보고하지 않는다.

활성 제약에 대해 `min_{lambda >= 0} ||grad(TTT) + C.T @ lambda||²`를 계산한다. Proximal 항과 trust region은 원 TTT의 승수 회수에 넣지 않는다. 동역학은 총미분에 이미 포함되므로 별도 중복 승수를 만들지 않는다. 기준점과 최종점이 다르면 정확한 최종점 KKT 승수가 아닌 근사다.

최신 release는 유한한 근사 승수를 실행 가능한 후보의 **상위 탐색 제안**에 사용할 수 있게 했다. Stationarity/미분 인증 미통과는 별도로 남기며 최적화 수렴으로 취급하지 않는다. 새로운 budget마다 하위 문제와 실행 가능성을 다시 검사한다. 과거 `SelectedDualSDMPC` 문서의 더 엄격한 사용 조건과 현재 release의 조건을 혼동하면 안 된다.

현재 VISSIM worker는 비용 20행(19 owners + PASSIVE_OMEGA), 자원 2행의 Jacobian만 반환한다. 전체 물리 상태 제약 Jacobian은 반환하지 않는다. Reverse AD tape는 worker 안에 있고, 성공한 물리 검사 기록 중 일부는 검사 후 요약만 보존한다. 따라서 새 코드의 `state.tangent` 접근을 그대로 복사해서 모든 물리 제약의 중앙 승수를 얻을 수 없다.

이식 시 물리 제약을 식별하는 ID·최종값·같은 기준점의 미분을 추가로 보존해야 한다. 현재 reverse tape를 재사용하고 필요한 활성 행의 역방향 계산 범위를 정해야 한다. 활성 행 누락 여부도 증거로 남긴다. 비용/자원/box만으로 계산한 승수는 부분 진단으로 표기하며 완전한 중앙 KKT 회수로 부르지 않는다. 이 확장의 추가 시간·메모리는 아직 측정하지 않았다.

## 실제 합류량 계약

현재 `physical_ramp_branches.predicted_merge_quantity`는 각 frame에서 실제 본선으로 받아들인 차량을 누적하고, 같은 예측창 길이로 나누어 veh/h로 환산한다. 이를 `area_leader_objective.shared_quantity_constraints`가 사용한다.

`N_UF(u) = 3600 / H_sec × sum_ramp(예측창 안에서 실제 본선에 합류한 차량 수)`.

검토 대상은 H_sec=450초다. 150초별 값도 별도 기록할 수 있지만 450초 합계와 혼용하지 않는다. 명령상 통과 가능 대수, 미터 서비스 상한, 램프 진입 대수, 목표값 N_UF*는 실제 합류량이 아니다.

새 Numerical-Sim의 `prox_controller.derivatives`는 NUF 미분 행을 meter 명령 합의 상수 미분으로 덮어쓴다. **이 줄은 이식하면 안 된다.** 현재 AD가 계산하는 실제 합류량 총미분을 사용하여 ramp 수요·재고·본선 수용 및 연결된 VSL/도시부 영향이 반영되게 한다.

현재 NP 상한/NUF 절대 band를 유지한다면 중앙 제약은 다음과 같이 세 budget 행으로 구성한다.

- `h_P = (N_P(u) - B_P) / s_P <= 0` (기존 수치 허용오차는 별도 유지).
- `h_F+ = (N_UF(u) - B_F - 40) / s_F <= 0`.
- `h_F- = (-N_UF(u) + B_F - 40) / s_F <= 0`.

따라서 상위 gradient의 budget 성분은 `-lambda_P/s_P`, `(-lambda_F+ + lambda_F-)/s_F`이다. Numerical-Sim의 상대 band 폭 미분 `0.05*sign(B_F)`는 들어가지 않는다. 40은 설명을 위한 현재 설정값이며 구현 시 기존 parameters/config 출처에서 읽는다.

현재 resource QP는 NUF 선형화의 중심 등식을 맞추고 최종 예측 gate는 ±40을 허용한다. 새 band QP/가격 갱신으로 맞추는 것은 동작 변경이며, 비교 결과에서 분리해서 기록해야 한다. 기존 signed NUF price를 양측 비음수 승수로 옮길 경우 초기화·단위·부호와 실제 적용 확인 후의 commit 계약도 맞춰야 한다.

또한 현재 `initialize_decision_nuf`로 정한 목표는 모든 budget 후보에서 고정된다. 최신 저장 상태 benchmark에서는 목표가 5144.1629veh/h, 허용폭은 ±40veh/h였다. 이는 합류 총량을 크게 줄이는 선택을 제약할 수 있다. **실제 합류량이라는 물리량 정의와, 그 목표를 leader가 조정할 수 있는지는 별개**다. 새 상위 탐색의 효과를 내려면 실제 합류량 목표 B_F도 탐색 대상으로 삼아야 한다. 수요·재고·본선 수용 때문에 달성하지 못하는 목표는 후보 실패로 남긴다. 그 후보의 예측값으로 목표를 다시 맞춰 성공 처리하지 않는다.

## 검증 및 계산시간 해석

이번 환경에서 새 소스의 다음 단위 검사를 실행했다. SDMPC outer iteration 및 교통 rollout은 실행하지 않았다.

|검사|결과|
|---|---:|
|중앙 승수, 물리 행 누락, 중복 행, 부호|8 PASS|
|기존 1차식 재사용, 최종 실제 활성 집합, cache 부재|3 PASS|
|band 가격 갱신 부호, 공동 자원 교환|3 PASS|
|box 지역 QP의 독립 solver 대조|2 PASS|
|합계|16 PASS|

최초 sandbox 호출은 설치된 `scipy.optimize`를 찾지 못해 검사에 진입하지 못했다. 별도 로그를 보존하고 같은 코드를 설치 의존성 접근이 가능한 실행에서 재검사했다. source fixture 16개는 release 제공 복원기로 hash 확인 후 새 검토 checkout의 outputs 아래에만 복원했다. 기존 다른 실험 결과는 수정하지 않았다.

수령본의 자체 보고에서 중앙 승수 **회수 단계**는 9후보 합계 약 0.075초이며 추가 scalar/tangent rollout은 0회다. 회수 자체는 제어 재최적화 iteration 0회다. 이를 하위 최적화 6회가 끝난 총 결정 시간으로 해석하면 안 된다. 이 시간은 이번 컴퓨터에서 재측정한 값도 아니다. 이전 재미분 버전과 미분 검사의 보증 범위도 달라 동일 정확도의 속도 비교가 아니다.

현재 VISSIM의 직전 실측은 304.255초다. 8워커, 450초 예측, 후보별 outer 상한 2회, 수락 횟수는 NP2400/743.75/81.25에서 각각 2/2/0회, 선택 후보 2회 수락, **수렴 미확인**이다. 교통 예측 총 5회(AD 3 + scalar 2), local QP 95회였다. 새 중앙 승수 기능만 붙여 이 기존 교통 예측을 없앨 수는 없다. 150초 이내 달성이나 속도 개선은 이번 검토에서 측정/입증하지 않았다.

수령본 장기 실험은 하위 outer 상한 6회·최대 3 budget 후보 조건이며, 두 14400초 목표 런이 각각 1620초/1800초에 feasible 후보를 찾지 못해 중단됐다. 이번에는 장기 런을 재실행하지 않았다. 원 저장소에서도 최적화 수렴과 8% 성능 기준은 미충족이다. VISSIM plant의 RM/VSL 순이득 예측 문제도 이번 소스 검토로 해결된 것은 아니다.

## 권장 구현 순서

1. 현재 좌표·plant·실제 합류량 정의를 유지하고 후보마다 독립적으로 iteration 가격을 갱신한다. 민감도는 변경된 공통 기준점에서 갱신한다. 최종 적용이 확인된 선택 후보의 가격만 다음 결정으로 넘긴다.
2. 이미 계산한 TTT/자원 민감도에 필요한 물리 제약 정보를 연결하고, 중앙 승수를 별도 회수한다. 근사 기준점·실제 잔차·제약 포함 범위·수렴 상태를 기록한다. 새 rollout을 추가하지 않는 설계부터 검증하되 실제 추가 역방향 계산 비용은 측정한다.
3. 기존 NP 상한 및 실제 NUF 목표를 상위에서 제안하고 각 후보를 다시 검증한다. NUF를 실제 합류량으로 유지하며 명령 합의 반경/미분/상대 band 값을 복사하지 않는다. 일반·혼잡 직전 저장 상태에서 명령·제약·총시간과 iteration 횟수를 비교한 뒤 짧은 native 적용으로 진행한다.

새 알고리즘은 config 키 하나로 활성화하고 미설정 경로는 기존 결과를 보존한다. 수치는 parameters.json에서 읽으며 `verify_parameters.py`를 통과해야 한다. 구현 전 native 9000초부터 재시작하지 않는다. 이번에는 이식 검토까지만 완료했다.

검사 로그와 소스 고정 manifest: `diagnostics/sdmpc_source_review_20260922/`.
