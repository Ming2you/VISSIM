# 1초 계산 사이의 배열 재사용과 지연 출력

이전 단계: `docs/SDMPC_ARRAY_PIPELINE_20260922.md`. 426.879초(후보별 상한 2회, 선택 후보 2회 수락, 수렴 확인 없음) 결과와 검증 소스는 `diagnostics/sdmpc_array_pipeline_20260922/final_sources/`에 보존했다. 이전 빠른 경로의 386.693초를 넘어 그 수정본은 속도 개선으로 채택하지 않았다.

## 이번 변경

기존 `sdmpc_array_urban_pipeline` 키의 미분 예측 경로를 확장했다. 추가 config 키나 물리 파라미터 변경은 없다.

- 도시부 큐의 숫자 레코드, 누적 회계, 재고, 비용과 reverse node ID를 query-owned native 컨테이너에 유지한다. 매초 전체 도시부 큐를 Python/NumPy → native → Python/NumPy로 왕복시키지 않는다.
- 새 외부 FIFO와 실제 외부 수정이 발생한 셀만 입력한다. 내부 유량 요청·공유 receiving 배분·FIFO 이동·체류비용·보존 및 용량 검사는 같은 native 기록을 읽는다.
- 공개 FIFO의 stock은 계산된 값의 캐시를 사용한다. packet 목록을 읽거나 수정하거나 스냅샷을 만들 때 해당 셀만 동기화한다. 외부 FIFO 수정은 다음 계산 전에 다시 입력한다.
- 누적 admitted/departed/movements와 vehicle_seconds는 읽기/스냅샷/예측 종료에 출력한다. 공개 Counter를 읽으면 외부 수정 가능성을 보수적으로 인정하여 다음 계산 전에 해당 Counter를 다시 입력한다.
- 매초 새 local reverse node를 같은 전역 tape의 node ID로 바꿔 유지한다. 세 제어 구간 사이의 sensitivity 연결을 끊거나 고정하지 않는다. geometry 변경과 alias된 외부 FIFO는 명시적으로 거부한다.
- 기존 일반 scalar 후보 예측은 그대로 사용한다. 이번 배열 경로는 config가 켜진 reverse AD 예측에서만 실행된다.

공개 TrafficState에는 native 저장소를 추가하지 않는다. 스냅샷에는 기존 deque/Counter 형식이 들어간다. 기본 OFF 경로, 최초 관측 상태, 1초 물리 갱신, 450초 horizon, 3×150초 입력, 231축과 모든 제약을 유지한다.

## 결과와 채택 판단

900초 저장 상태, 450초 예측, 3×150초 제어 입력, 최대 8워커로 전체 오프라인 결정을 실행했다. 세 측정은 모두 후보별 outer iteration 상한 2회이며, 선택 후보가 2회 갱신을 수락한 결과다. **수렴 완료나 6회 iteration 시간은 아니다.** 각 버전의 전체 결정은 1회 측정이므로 반복 측정 평균이나 통계적으로 확정된 속도 차이는 아니다.

| 경로 | 전체 결정 시간 | 후보별 iteration 상한 | 선택 후보 수락 횟수 | 수렴 확인 |
|---|---:|---:|---:|---|
| 기존 최선 `sdmpc_trial_20260922/full_decision_v1` | 386.693초 | 2 | 2 | 없음 |
| 이전 배열 저장 연결 `sdmpc_persistent_plant_20260922` | 444.002초 | 2 | 2 | 없음 |
| 이번 숫자 배열 유지 `full_decision_v1` | 413.393초 | 2 | 2 | 없음 |

이번 값은 이전 배열 저장 연결보다 6.89% 짧지만 기존 최선보다 6.90% 길다. 같은 작업 중 먼저 검증한 전체 도시부 연산 묶음은 426.879초(동일 상한 2회, 선택 후보 2회 수락, 수렴 확인 없음)였고, 그 값 대비 추가 감소는 3.16%다. **150초 목표는 미달이며, 속도 개선 정본으로 채택하지 않는다.** 새 config 키는 기본 OFF다. 기존 최선 config는 변경하지 않았다.

전체 세 후보의 수락 횟수는 N_P=2400에서 2회, N_P=743.75에서 2회, N_P=81.25에서 0회다. 마지막 후보는 첫 iteration의 결합 QP에서 실패한 것으로, 계산을 전혀 하지 않았다는 뜻이 아니다. 앞의 두 후보는 iteration 상한으로 종료했다. 선택한 목적값은 396.57370910204804 veh·h, hold 목적값은 402.31251168233456 veh·h로 기존 측정과 같다. 모델 예측 비용이며 VISSIM 개선율이 아니다.

## 검증

증거 폴더: `diagnostics/sdmpc_native_arrays_20260922/`.

- scalar/AD × 12개 조건, 총 24개 비교: 수치·라벨 표현·FIFO 순서·이동 경로 동일, Jacobian 절대오차 1e-12 이내. 무조회 연속 실행, 중간 스냅샷, 외부 재고 변경, 사라졌다 다시 나타나는 유입 포트를 포함한다.
- SDMPC 회귀 136개 PASS (`regression_v2.log`).
- 기존 결합 OFF/ON 각 9개 PASS (`coupling_v2.json`).
- `verify_parameters.py` PASS (`parameters_v1.log`).
- 최종 단일 Jacobian 검증 `native_h3_v2`: 기존 대비 비용·자원·비용 Jacobian·자원 Jacobian 최대 차이 모두 0. 원래 scalar 예측과 숫자 배열 AD 예측의 전체 상태가 일치한다. reverse 연산 수, 분기 이벤트, tie 및 discrete 의존 축도 기존 결과와 같다.

독립 OFF/ON 전체 상태 비교는 `states_v1/comparison.json`, 전체 결정·제약·명령 및 모든 사용 Jacobian 비교는 `qualification_summary.json`, 기존 기본 경로의 과거 상태 대조·최종 소스 SHA·채택 여부는 `connection_summary.json`에 기록한다. 해당 파일의 `pass_all`이 최종 판정이다. 실패한 과거 측정은 덮어쓰거나 통과로 바꾸지 않았다.

## 어느 부분을 줄였는가

`native_h3_v2`의 단일 Jacobian은 145.665초다. **최적화 iteration을 실행하지 않은 미분 1회 측정**이다. 그 안의 미분 예측은 122.594초, 그중 이번 도시부 배열 처리 구간은 9.999초이고 컴파일 본체는 2.342초다. scalar 검증 예측·미분 예측·일부 병렬 작업의 시간이 겹치므로 세부 시간을 합쳐 전체 시간으로 해석하면 안 된다.

450개 물리 step에서 숫자 상태를 449번 재사용했고, 도시부 셀 초기 입력은 40번, 누적 Counter 입력은 4번이다. 셀 출력은 공개 조회와 외부 FIFO 처리를 포함해 6,690번이므로 모든 출력 변환을 없앴다는 뜻은 아니다. 필요한 외부 입력·이동 결과·검증 스냅샷에는 기존 형식으로 변환하는 경계가 남는다.

배열 처리는 도시부의 재고 조회→유량 배분→차량 이동→비용·제약 계산까지 연결했다. 다른 본선·램프와 전체 예측 조율 코드까지 전부 배열로 옮긴 결과는 아니다. 이 범위의 변환 제거만으로 전체 병목이 해결되지 않았다는 것이 이번 측정의 한계다.

AD query 중에만 지연 조회를 처리하는 임시 접근 클래스를 사용한다. 일반 scalar 예측에는 추가 attribute hook을 부과하지 않으며, 스냅샷과 query 종료 후 객체 타입은 기존 `UrbanTransport`로 복원한다.

## Sensitivity와 iteration

outer iteration k에서는 현재 제어열 u^k로 예측하고 J(u^k)를 사용한다. 같은 iteration의 QP, line search와 제약 복원은 같은 미분 행렬을 사용한다. 갱신을 수락하여 다음 iteration으로 들어가면 새 제어열 u^(k+1)을 기준으로 다시 선형화한다. 시작 관측 상태는 그 결정 동안 고정이고 제어열에 따른 미래 궤적이 바뀐다.

정확히 같은 입력·비용·자원 응답에 대한 캐시나 정확히 일치하는 선계산 결과는 재사용한다. 최초 sensitivity를 모든 iteration에 고정하는 방식은 아니다. 상한 2회에서 J(u^0), J(u^1)을 사용해 u^2까지 수락했다고 해서 J(u^2)까지 계산했다는 뜻은 아니다. endpoint 예측 횟수와 QP 내부 반복 수는 outer iteration 횟수와 구분한다.

이 작업에서 native VISSIM 실행이나 9000초 비교는 수행하지 않았다.
