# Native 대기시간 기록 — 2026-09-27

정밀 재보정을 늘리지 않고, 실제 폐루프 비교에 빠져 있던 미삽입 차량 대기시간을 수집한다. 기존 Ω TTT 정의, 목적함수, 물리 계수, 제어 지평·주기·명령은 바꾸지 않았다.

VISSIM 2020 공식 도움말의 `DelayLatent`는 차량이 원래 투입 시각에 네트워크로 들어오지 못해 발생한 대기시간이다. 종료 때의 `DemandLatent` 대수와 다르다. `TravTmTot + DelayLatent`는 네트워크 내부 주행·체류와 외부 미삽입 대기를 합한 비교량으로 별도 보고한다. Ω TTT와 대체하거나 중복 합산하지 않는다.

출처: https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/11_Auswertungen/AuswertungNetzauswertungFzg.htm

정본 VBS runner에서 0..종료 시각의 단일 native 평가 구간을 켜고, 종료 시 `TravTmTot`, `DelayLatent`, `DemandLatent`, `VehAct`, `VehArr`를 한 번 읽는다. 모든 링크가 평가에 포함되는지 확인한다. 누락·음수·부분 구간·기존 결과 파일은 실패 처리한다. 매초 COM 읽기는 추가하지 않는다. 결과 파일은 각 런의 `native_network_performance.json`이다.

설치된2020에서 설정 속성 네 개와 전체1236개 링크 포함을 COM으로 확인했다. 첫150초 smoke 런은 시뮬레이션을150초까지 완료했으나 최종 링크 배열을 jagged array로 읽어 기록에 실패했다. 실제 COM은2차원 배열이다. 실패본은 `D:/VISSIM_runs/20260927_sd31_native_cost150/nc`와 동결본에 보존했다. 테스트 fixture를 실제2차원 형식으로 바꿔 실패 재현 후 수정했고, 관련10개 테스트가 통과했다(`native_network_performance_2d_before.log`, `native_network_performance_2d_after.log`).

별도150초 재검증을 준비한다. native 기록과 과거 무제어 FZP 데이터 행 일치를 확인하기 전에는 완료로 표시하지 않는다. 기존9000초 목표는 유지하지만 실제 순이득은 런 완료·비용 분석 후 판단한다. 세부 속도 오차나 거의 같은 후보의 순위를 모두 맞추는 것은 선행 조건이 아니다.

## 단기 확인의 현재 증거

- v2는 최종 COM 조회에서 실패했다. 설치된2020 공식 `Doc/Eng/attribute.xlsx`를 읽어 `DelayLatent`, `DemandLatent`는 SimulationRun·TimeInterval 두 인수만, 나머지 세 지표는 VehicleClass까지 세 인수를 받는 것을 확인하고 수정했다. 해당 수정의10개 테스트PASS, `native_network_performance_api_tests.log`.
- 첫두150초 실행의 FZP는 서로 정확히 일치했다. 기존3000초 런의 prefix와는130.1초부터 일부 도시 차량이 달라져 동등하다고 선언하지 않았다.
- 이전 동결 runner도 동일150초 길이로 새 대조 런을 완료했다(`D:/VISSIM_runs/20260927_sd31_native_cost150_baseline`, session99993 exit0). 이 대조와 새 평가를 켠150초 런들은 **18,745행 모든25개 열이 정확히 같다**. 데이터SHA256 `6f5287333417b841cc59f746d4403b85ceb64e15ca022eaf8969544e675b3172`, 마지막145.1초. 서로 다른 실행 길이를 섞은 prefix 비교와 구분한다.
- 현재 최종 기록 확인은 `D:/VISSIM_runs/20260927_sd31_native_cost150_v3`, session78835. 그 동결본 SHA `1d2f0fd3c61b50586198058a03d3ef65e6af324a8e14baa88ab26f62eae79dbc`. 준비 중 상태 파일이 바뀌어 첫 동결 검사가 거부된 증거는 보존했고, 실행 종료 후 해당 상태 파일만 정합시켜 전체 동일성 검사를 통과했다. 기존 유효 동결본은 변경하지 않았다.

## 9000초 비교에서의 판단

최종150초 확인(session78835 exit0)이 통과했다. `native_cost150_validation.json`: 모든25개 FZP열18,745행이 기존 같은 길이 실행과 정확히 같고, native LDP/readback PASS다. native 내부 시간26.838833대·시간, 미삽입 대기2.025444대·시간, 종료 미삽입118대를 서로 구분해 기록했다. LSA COM 기록 실패는 사용자 승인 LDP 대체와 별도로 남겼다.

검증한 동결본으로 같은 seed29 무제어→SDMPC9000초 비교를 시작했다(session9778). 결과폴더 `D:/VISSIM_runs/20260927_sd31_closedloop9000`. 물리 계수·목적함수·수요·명령 범위를 이번에 바꾸지 않았다. 종료 전 큰 분석을 하지 않는다. 다음 읽을 실행 상태는 `closedloop9000_status.json`이며, 실제 진행은 해당소유세션과 native runlog로 확인한다.

기존3000초의 실제 제어 적용, 유한 RM 명령의 작은 물리 반응, 보존·명령 검증을 재사용한다. 현재 모델을 고정한 전체9000초 비교는 남은 이득 검증이다. 실행 성공을 이득 보정 완료로 취급하지 않는다. Ω TTT, Ω 밖 실제 체류, native 미삽입 대기, 삭제·유출을 함께 판단한다. 모든 근소한 후보 차이와 속도 궤적을 먼저 맞추기 위한 추가 계수 탐색은 하지 않는다.

`evaluation/controllers/sdmpc.py::omega_costs`는 사용자 정의에 따라 Ω 내부 체류만 최적화한다. 게임의 externality는 다른 Ω 주체 비용이며, Ω 밖 대기를 목적함수에 더한다는 뜻이 아니다. 이 정의를 이번 측정 보완에서 바꾸지 않았다. Ω 개선이 전체 비용 개선과 다르면 먼저 이 평가 범위와 대기 이동을 설명해야 하며, 이를 속도식 보정으로 해결됐다고 주장하지 않는다.
