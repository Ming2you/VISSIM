# 새 SDMPC: 예산 후보 1개, outer iteration 2회 실측

2026-09-22. 사용자 요청에 따라 Numerical-Sim `8c016939a6c8a6994b60ca0836d00fdcfe096209`의 반복 가격 갱신·별도 중앙 승수 회수를 현재 VISSIM controller에 이식한 뒤 실제 결정을 계산했다. 추정 시간이 아니다.

## 결과

**전체 결정 311.388초(5분 11.4초)**. 상위 예산 후보 1개, 후보별 outer iteration 상한 2회, 실제 실행 2회·수락 2회, 종료 사유 `iteration_limit`, **수렴 미확인**이다. 중앙 stationarity 잔차는 9.6476으로 설정 기준을 통과하지 못했다. NNLS가 계산됐다는 것과 원 최적화가 수렴했다는 것은 다르다.

- 같은 900초 저장 상태에서 450초를 예측하고 150초별 독립 제어 3개를 최적화했다.
- 최대 계산 워커 8개. 두 line-search 제어를 예측할 때는 각각 역방향 워커 4개를 사용했다.
- 예산 후보는 `NP cap=2400veh`, `NUF target=5144.162909veh/h` 한 개다. 내부 line search 후보와 구분한다.
- NUF는 8개 램프에서 실제 본선으로 수용된 차량의 450초 평균 합류율이다. 미터 명령 합으로 변경하지 않았다.
- 최종 예측 NUF=5141.827107veh/h, 목표 오차 −2.335802veh/h로 기존 ±40veh/h 안이다. NP actual=565.243477veh로 상한 이내다.
- 교통 예측 총 5회: AD 3회 + scalar 2회. 지역 QP 38회이며 지역 QP 내부 교통 rollout은 0회다.
- 새 config만 `adapter.sdmpc="central-reuse-v2"`로 활성화한다. 기존 adapter 및 vendor는 수정하지 않았다.

|구간|wall time|포함 계산|
|---|---:|---|
|초기 공통 예측·미분|119.621초|AD 1회, 물리 상태 민감도 포함|
|첫 iteration 후보 평가·다음 민감도|133.197초|AD 후보 2개 병렬; 선택 후보의 다음 iteration 미분 재사용|
|두 번째 iteration 최종 후보 평가|52.408초|scalar 후보 2개 병렬|
|중앙 승수 회수|0.088691초|제어 재최적화 iteration 0회, 추가 교통 예측 0회|
|초기화·QP·검증·기타|6.073초|기타 전체 결정 작업|
|전체|311.388초|outer 상한 2회, 실행/수락 2/2회, 수렴 미확인|

## 같은 조건의 기존 버전

이식 전 기존 SDMPC도 별도로 새 프로세스에서 계산했다. 후보 1개, outer 상한 2회, 실행/수락 2/2회, 수렴 미확인, 같은 5개 rollout에서 **293.059초**였다. 이번 새 버전은 한 번씩의 측정에서 18.330초 더 걸렸다. 여러 상태의 평균이나 성능 향상/저하를 입증하는 반복 benchmark는 아니다.

과거 3개 예산 후보 측정의 304.255초와 비교하면 안 된다. 그 실행도 각 후보 outer 상한 2회였지만 수락 횟수는 2/2/0회였고, 서로 같은 제어 경로를 공유해 추가 예측을 거의 하지 않았다. 이번 비교 기준은 같은 작업에서 직접 실행한 1후보 293.059초다.

## 이식 내용과 범위

1. 각 후보는 같은 초기 가격의 독립 복사본에서 시작한다. 모든 지역 QP가 공통 기준점/가격을 사용한 뒤, 선형화한 공동 제약의 잔차로 다음 iteration 가격을 갱신한다. 미분은 변경된 기준점에서 갱신한다. 다음 결정으로 넘길 가격은 실제 적용 receipt 확인 후 사용한다.
2. NP 상한용 1개, 실제 합류량 NUF의 양측 band용 2개 비음수 승수를 둔다. 양측 NUF 승수를 각각 저장하며 signed price만 저장해서 정보를 잃지 않는다. 기존 NP 상한과 NUF ±40veh/h를 유지한다. Numerical-Sim의 NP ±10대/NUF ±5%나 명령 합의 상수 미분을 가져오지 않는다.
3. 최종 후보에서 같은 budget 후보의 가장 가까운 기존 선형화 계수를 재사용해 별도의 중앙 승수를 회수한다. 활성 집합은 최종 후보의 실제 연속-model 제약값으로 판정한다. 기준점/최종점 차이를 기록하며 최종점에서 새로 미분한 정확한 KKT 승수로 부르지 않는다.
4. H3 각 끝 시점의 queue/density/storage/lane inventory 및 실제 기록된 도시 queue/cell bound 총 5,169개 상태 부등식을 연결했다. 제어 box, green·블록 간 변화량 및 budget 행을 합하면 중앙식은 6,391행이다. 기존 매-step 수용·할당·보존 검사는 계속 실행한다. 이들 동역학 검사에 임의 승수를 붙이지 않으며, 전체 시간 경로의 KKT 완전성이나 native 물리 정확도를 인증하지 않는다.
5. 상태 미분은 교통을 다시 rollout하지 않고 이미 생성한 reverse tape를 사용한다. 출력 수가 입력 231축보다 많으면 같은 tape를 231개 방향으로 전파하는 컴파일 배열 계산을 사용한다. 실제 사용한 두 선형화의 상태 미분 시간은 7.058초(8워커), 11.259초(4워커)였다. 각각 추가 최적화 iteration 0회·교통 rollout 0회이며 위 AD batch 시간에 이미 포함됐다. 이 시간을 전체 wall에 다시 더하면 안 된다.
6. NUF 목표를 움직이는 상위 후보 생성 함수도 실제 합류량의 단위로 연결했다. 이번 요청은 후보 1개이므로 다음 budget 생성/재최적화는 실행하지 않았다. 그 방향·중복 방지는 단위 검사로만 확인했으며 다중 budget 및 native closed-loop 실행 완료를 주장하지 않는다.

이 저장 상태에서는 raw 제안이 band 안에 있어서 가격 갱신 2회 후에도 가격은 0을 유지했다. “갱신을 호출했다”를 “가격이 실제로 변했다”로 보고하지 않는다. 중앙 budget gradient도 0이었고 stationarity는 미통과했다. 이번 결과는 해당 입력에서 새 코드의 실행·제약·시간을 확인한 것이며 metering 효과나 장기 성능 입증이 아니다.

## 검증과 증거

- 신규 및 기존 관련 단위 검사 합계 67 PASS; config 파라미터 검사 PASS.
- 원 상태에서 비용·실제 NP/NUF·그 Jacobian은 기존 버전과 최대 차이 0이었다.
- 새 full decision의 후보 수·iteration 수·가격 전달·상태 미분·실제 합류량·3개 블록 actuator 검사·소스 불변·워커 종료 등 23개 검사가 통과했다.
- 연속 예측 모델의 제약을 만족했다. 별도 원 actuator 모델 사후 검사도 완료했고 제약 만족·명령 차이 0·3블록 actuator 검사·소스 불변을 확인했다. **사후 검사 49.640초는 최적화 iteration 0회인 두 예측의 병렬 대조**이며 위 결정 시간에 포함하지 않는다. 이를 포함한 계산시간 합계는 361.029초다. VISSIM native 런은 실행하지 않았다.
- 실행 전 소스는 `diagnostics/sdmpc_central_port_20260922/before_sources/`, 새 실행 결과와 SHA256은 `decision_v1/result.json`, 요약은 `summary.json`에 보존했다.
- 이전 버전 실측: `diagnostics/sdmpc_one_candidate_20260922/summary.json`.

실행 명령:

```powershell
python -B diagnostics/measure_sdmpc_central_decision.py diagnostics/sdmpc_stream_summary_20260922/hotpath_h3_v1 diagnostics/sdmpc_central_port_20260922/decision_v1 diagnostics/sdmpc_central_port_20260922/config_candidate.json
```

출력 경로는 이미 존재하면 실패하므로 재실행 시 새 디렉터리를 지정한다. 수치 의존성 경로 및 1-thread BLAS 설정은 같은 디렉터리의 실행 로그/현재 작업 환경을 따른다. 9000초 실런이나 배포 설정 변경은 이번 요청에 포함하지 않았다.
