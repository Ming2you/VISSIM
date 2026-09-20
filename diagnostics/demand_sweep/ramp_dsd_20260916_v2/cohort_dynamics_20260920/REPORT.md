**최신 재개점(실효 속도식·수송 시간·하류 이득):** `CONTEXT_TIME_AND_DOWNSTREAM_GAIN.md`, `partition_context_work_v1/verification.json`, `transport_step_work_v1/verification.json`을 읽는다. 단일adapter의명시적공간길이와매속도호출segment문맥을수정했고기본비활성이다.1/2초수송은150초제어·10초미터주기·전체요청량을보존한다.32유효450초예측·12전체JSON exact·50+22검사·166pin.1초 RM+.00498/VSL+.04692/동시+.05204로여전히gain실패·미채택.2초도유사하여더짧은step sweep은중단한다. 새보존분해:실제RM합류−15/말단+16대,모델−12.21/−1.20대. 실제본선이득은주로10490합류뒤cell14–20(0-based)에서나오며모델이놓친다. VSL도여러off진입+38을못잡는다. 다음은그하류회복·방출의시공간/차로반응과공통경계예측오차분리다. 원본망/수요/native런/기본config/vendor/commit/push없음,자체작업종료, NOT_QUALIFIED·goal active. 아래는역사적체크포인트다.

**최신 재개점(공간별 이동률·실효 속도 인자):** `SPATIAL_EXCHANGE_AND_TIME_RESOLUTION.md`와 `partition_exchange_work_v1/verification.json`을 읽는다. 기본 비활성 physical_partition_exchange를 core/harness에 시험했다. 차로 순유입 오차는−34.69→−1.57대(실제+4)로 줄었지만450초 RM−.01401/VSL+.07919/동시+.06547, NC점수3.1343으로 gain 실패·미채택이다.12예측/비활성8전체JSON exact/5412도시보존/1080인터페이스/55pin/48+1검사/parameterPASS. Native 무차로변경270대 중97대가 같은10초 내176m를 통과했고, 제조 수송 반례는1/.5초 적분 수렴을 보였다. 더 우선할 구현 오류도 확인했다: adapter가 분기 앞176m를전체526m로 덮어쓰고 문맥을 소비하여 뒤 계산은다른길이/계수경로를쓴다(speed_context_trace.json). 다음은 매 공간·ODE단계 실효인자정합 수정, 이후 수치적분 비교다. transport_convergence.json은 일정속도 가정실패로무효, v2만유효. 새native/기본config/망/수요/adapter/vendor/commit/push없음,자체계산종료, NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.

**최신 재개점(분기 전후 수송 구현):** `BRANCH_PARTITION_IMPLEMENTATION.md`와 `branch_partition_v1/verification_v4.json`을 읽는다. 기존core/harness에 config 기본 비활성 `physical_branch_partition`을 추가했다. 분기 앞뒤 재고·속도/실제 유량 기반 모멘트를 보존한다. 첫10초 방출0→3.8547대(실제5) 반례는 개선됐으나450초v4 ΔTTT RM−.01566/VSL+.07216/동시+.05664로gain 실패, NC점수2.6451도 기존2.1642보다 악화해 미채택.45검사(신규9), 도시27계약,16예측·비활성8전체JSON exact·7216보존·1440인터페이스·72pin·parameterPASS. 새native/기본config/망/수요/adapter/vendor/commit/push없음,자체계산종료. 열린3·4차로 분기앞 재고11.16vs실제4.89·속도60.9vs98.2가 남아 수송수량/공간별교환을 먼저 구분한다. NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.

**최신 재개점(분기 전후 차단 적용):** `BRANCH_POSITION_AND_INTENT.md`와 `branch_position_audit_v1/result.json`을 읽는다. 목적지1/6 및 현재 지정 경로를 보강한450초 후보도 gain 실패다(RM−.0164/VSL+.0504/동시+.0341).12예측·4exact·5412보존·1080인터페이스·52pin 검증 완료. 새 native 분석에서2400초10643 분기 뒤2차로5대가 차로변경 없이2403–2408에 나갔으나 모델은같은10초방출0이다. 현재FIFO가분기뒤350m까지적용되는 공간 오류를 확인했다. 다음은 분기 전후 보존 수송 구분이며, 초기값만 분리하거나 전체FIFO를 풀지 않는다. 새native/core/기본config/망/수요/commit/push없음, 자체계산종료, NOT_QUALIFIED·goal active. 아래는 역사적 체크포인트다.

**최신 재개점:** `RECEIVING_COMPARISON_AND_CONTROL_PATH.md`와 `urban_route_transport_space_v1/verification.json`을 읽는다. 공간 비교 조건의5개450초·8개40초 예측은 완료됐으나 제어 이득에 실패해 미채택했다. NC 방출27.59(실제23), VSL27.59(실제30).27계약·45pin·기준4JSON exact. 본선 수용 상한은 바뀌지만 이NC의 본선 물리 기록은 그대로다. 다음은 실제 유량을 제한하는 경계와 진입시각/주행지연/합류순서 연결이며 도시부 지연 조건 sweep은 반복하지 않는다. 신규native/core/망/수요/commit/push없음,자체실행종료,목표active·NOT_QUALIFIED. 아래는 이전 체크포인트다.

**최신 재개점(정상 국소 예측):** `LOCAL_RECOVERY_PREDICTION.md`와 `urban_local_recovery_v1/verification.json`을 먼저 읽는다. NC/VSL의2510/2810초에서40초 인과 국소 예측8개 완료. 현재 차량 길이+native간격의 셀 여유공간 조건은NC 두 정상 해제 시점을1초 개선했지만VSL13038/13301 정상2530/2536진출을 여전히 놓쳐 기각했다.2510구간은71삭제0이라 삭제만으로 실패를 설명할 수 없다.20계약·기존4예측160초ledger/trace정확·328도시보존·11pin확인. 다음은71 강제 차로 변경에서 한 차량의 점유/변경완료를 유지하는 국소 표현을 검토한다. 단순 임계값 sweep/45초삭제해제 가정/전체미시복제는 하지 않는다. 정본core/망/수요/새native/commit/push없음,모든자체계산종료,목표active·NOT_QUALIFIED. 아래는 이전 체크포인트다.

**최신 재개점(차로 틈·비정상 해제):** `LANE_ACCESS_AND_ABNORMAL_CLEARANCE.md`와 `urban_access_head_outcomes_v2/verification.json`을 읽는다. 현재 차체가 들어갈 전체 틈·전진 여유·진행 중 변경을 구분하는 관측을 추가했다(정본 유량 법칙 아님). NC/VSL 저속·틈 부족 선두차각8대 중 정상진출2/삭제5/잔여1이며 full native hash·경로·ERR로 확인했다.45초 삭제 후 공간 회복을 정상 배수로 보정하지 않는다. nominal6m 때문에 제외했던 VSL63snapshot을 현재 기하 관측에서는 모두 보존한다.7계약·기존14관측exact. 다음은 정상 해제에 한정한 공간 회복/차로별 receiving 법칙 검증이다. 새native/core/망/수요/commit/push없음,모든자체분석종료,목표active·NOT_QUALIFIED. 아래는 이전 체크포인트다.

# 2026-09-20 진행 중: 이득 예측 원인 분리와 물리 후보 검증

**현재 재개점: [ROUTING_CONTINUATION_AND_LOCAL_GAPS.md](ROUTING_CONTINUATION_AND_LOCAL_GAPS.md).**1133–2 종료 뒤의 무경로 진행을 full FZP와PTV2020 설명으로 확인했고, 과거 차로 교환·ALL connector 진행을 모델에 시험했다. NC방출을 약60대(실제23)로 과대예측해 기각했다. 분수 차량 조각 폭증과 첫 조각 크기에 의존하던 합류 배분도 수정했다. 이전 약25대 근접은 정정하며, 수치 수정 후 교환 미적용 기준은30.819대다. 다음은 실제 차체/앞뒤 간격/진행 중 차로 변경에 따른 국소 수용·해제다. 셀 공간이 양수여도 정지한 head의 차체 투영이 겹친241/206초 동안 다음1초 차로 변경은0회였다. VSL 저장량 모델 미지원63snapshot/257candidate초는 별도 보존했다.18계약·125pin·7완료 NC 재검증·parameterPASS. 모든 작업 종료, 신규native/core/망·수요 변경/commit/push 없음, 목표active·NOT_QUALIFIED. 아래는 역사적 단계다.

**현재 재개점: [DESTINATION_LANE_COUPLING.md](DESTINATION_LANE_COUPLING.md).** 목적지별 FIFO10643과126/10641/71의 유한 차로 수용·신호를 기존 harness에 연결했다. 인과적8개와 명시적 경계 oracle4개 계산 완료. 맨 앞 차량만 차로를 바꾸던 과한 차단을 수정하여 NC2차로 방출은5.982→24.995대(실제23)로 개선됐으나 VSL도24.995대로 실제30대 증가를 못 맞춘다. 실제 미래 경계 유입을 준 진단도30.000→30.992에 그쳤다. 정본 채택 금지다. 다음은 빠진126의2→1 이동42/43회와10643의 내부 교환, 공유 합류 공간을 연결한다.126 이동 중35대씩은 현재 경로1133–2가126에서 끝나71 목적지가 미확정이다. 이를 임의 목적지로 확정하지 않는다.45pin·10계약·5,412도시 보존·720인터페이스·parameter PASS. 신규native/core/망/수요/commit/push 없음, 모든 계산 종료, 목표active·NOT_QUALIFIED. 아래 관측 체크포인트는 직전 단계다.

**현재 재개점: [CURRENT_ROUTE_STATE.md](CURRENT_ROUTE_STATE.md).** seed23 NC/VSL 두 관측 반복을 기존 runner로3000초까지 완료했다. 현재 경로·NextLink·차량 길이 등을 native FZP에 추가했고, 원래10개 열 각각11,788,963/11,791,383행 정확 일치와LDP/readback PASS다. 개입 전20개 전체 열8,646,345행도 두 조건 간 동일하다. 2400초10643의2차로45대 중40대가71의4·5차로를 필요로 하는10635행이며,1차로16대에는 그 목적지가 없다. 같은 초기40대의10643 정상 진출은NC22→VSL28대, 해당 포트 체류는2,028veh·s 감소했다(Ω/TTD 아님). 현재 목적 경로가 관측 가능해졌으며 미래 삭제 경고를 입력으로 쓰지 않는다. 다음은 차로별 FIFO/목적지 재고와71의접근·수용·신호 서비스를 보존적으로 연결하는 것이다. 현재 관측 계약3개·미래 제거14개 PASS는 예측 qualification이 아니다. 기존 누적/배수 후보 gain실패는 `CUMULATIVE_BOUNDARY_AND_ROUTE_ACCESS.md`에 보존했다. 정본/기본 config/원본 망·수요 변경·commit/push 없음, 모든 이번 실행·분석 종료, NOT_QUALIFIED·목표active다. 아래 체크포인트는 역사 기록이며 이 문단이 우선한다.

**최신 완료 체크포인트: [OFFRAMP_SPATIAL_SERVICE.md](OFFRAMP_SPATIAL_SERVICE.md).** 10643 두 차로의 현재 위치·차량 길이와 공간 수송을 기존 모델에 진단용으로 연결해 네 후보를 시험했다. 모두 이득 예측에 실패했다. native 차로 보존 360건, 모델 보존·인터페이스 각각 1,440건, 기준 JSON 8개 재현은 통과했지만, 추가 지속 방출 시험에서 입력 서비스 900대/h를 600대/h로 낮추는 중복 지연이 드러났다. 정본 채택 금지다. 실제 VSL은 2차로 방출을 23→30대 늘리지만 현재 도시 상태를 고정한 후보는 두 조건 모두 약25대로 예측한다. 다음은 방출 서비스와 공간 지연을 중복하지 않는 경계 검사, 하류126/71 수용과 내부 차로 이동의 연계다. 이전 출발파 근거는 `OFFRAMP_QUEUE_RECOVERY.md`에 보존했다. 이번 core/기본 config/원본 망·수요 변경과 새 native 실행은 없다. 모든 이번 계산은 종료했고 목표는 active, 보정은 NOT_QUALIFIED다. 아래의 실행 중·답변 대기는 당시의 역사 기록이다.

직전 직접10484 seed23/33 시험은 `DIRECT10484_REPEAT_AND_LOCAL_CHECKS.md`에 완료·검증 결과를 보존했다. 재실행하지 않는다. input1101 시험·회전·원본망은 그대로다.

**보정 미완료, 목표 계속 진행 중. 이 문서는 종료 보고가 아니다.** 어느 후보도 기본 plant로 승격하지 않았다. 사용자 망·수요·기준 제어는 유지했고 새로운 full GNE나 Ω 개선을 주장하지 않는다. 비용은 동측 본선+동측 진입4개/진출4개 connector의450초 체류시간이다.

## 완료된 native 관측

`native_v1/none_s23`, `none_s33`를 기존 fast runner로3000초까지 완료했다. 추가된 것은 native FZP DESSPEED 열이다. 원래9열은 각각11,788,963행/11,604,208행 정확히 일치했다. 실행·native 기록 검사 PASS. 독립 성능 표본으로 세지 않는다. 이후 아래 진단들은 완료 자료를 재사용했으며 추가 VISSIM 런은 없었다.

`moments_v1/verification.json`, 두 native 폴더의 run/validation, `moments_v1`의7조건10초 관측이 근거다. 씨드23 none/VSL/mean_only/spread_only/affine_both 및 씨드33 none/spread_only다.

## 속도 분포와 차로 진입 손실

미래의 실제 희망속도 평균까지 주고 기존 평형속도에 비율을 곱한 진단은 실패했다. 씨드23 VSL의 실제ΔTTT−0.98194veh·h를+0.68343으로 예측했다. `mean_oracle_v1`은 온라인 예측이 아니다.

`lateral_v1`은 native1초에서 같은 링크 내 차로 이동 후 기존 추종차의 감속을 측정한다. 같은 시각·셀·차로·속도/간격 구간의 안정된 선행차 사례와 비교했지만 관찰 자료의 교란을 제거한 인과 추정은 아니다. 느린 차량 진입의 추종 감속을

`loss = gamma * max(v_follower - v_entering, 0)`

로 근사하면 무제어씨드23의900–2400초255개 일치 사례에서 gamma=0.376137이다. 제외한씨드33 무제어436사례의 감속 RMSE는12.867→9.509km/h로 줄었다. 희박한 매칭과 평균 FD에 이미 반영된 손실의 이중 계산 가능성이 남는다. 동기는 [Laval·Daganzo2006](https://its.berkeley.edu/node/4685)이지만 위 선형식은 해당 논문의 식을 그대로 옮긴 것이 아니다.

기존 `PhysicalLaneGroups`에 선택적 `physical_lane_interruption_gamma`를 추가했다. 수용된 느린 횡이동만 기존 수신 차량의 속도를 낮추며 차량 수·보상을 직접 바꾸지 않는다. `interruption_qualification_v2`는 기본12개+직전 후보12개 전체 JSON 일치, 상태 보호7/12이나 이득 예측 실패다. 미래의 실제 감속 노출량까지 준 `interruption_oracle_v1`도 씨드23 VSL−0.04083, 씨드33 spread+0.00619로 실제−0.98194/+0.63389에 크게 못 미쳤다.

## 진출램프 차로별 저장

`physical_offramp_lanes` 후보는10643/10481의 두 실제 차로를 분리한다. 진입은 기존 본선lane1/2→connector lane1/2 정합을 검사한다. 각 차로는 기존 `DelayedPort`를 사용하며 과거150초 차로별 배수를 예측한다. 총 배수 서비스는 이전 경계 값과 정확히 같다. 빈 차로의 서비스를 막힌 차로에 옮기지 않는다.

차로 이동은 과거30초 재고 보존식에서 추정한 순이동/차량·초를 사용한다. 상반되는 구간 내 이동은 관측되지 않는 근사다. 차량·이동 중 도착 시계·내부 이전이 보존되고 수신 저장공간을 넘지 않는다. 목적 방향의 자유로운 재선택을 입증한 모형이 아니다.

`off_lanes_qualification_v1`: 기본/직전12+12 정확 일치, 서측 동일, 상태 보호7/12. 씨드23 RM/VSLΔTTT는+0.00910/+0.01048로 실제−0.55333/−0.98194를 놓친다. 기본 채택하지 않는다.

## 본선 수용·끝나는 차로·속도 대류

`receiving_probe_v2`: 남은 공간 전체 대신 `min(space, w*dt/L*space)` 수용을 시험했다. w=18/24/36km/h는 관측으로 식별한 파속이 아닌 제한된 구조 진단값이다. [CTM의 유한 파속 수용 개념](https://its.berkeley.edu/node/4777)을 이용한 혼합 진단이지 완성 CTM은 아니다. 이득 문제를 해결하지 못해 운영 코드 옵션으로 추가하지 않았다.

반면 실제 기하에서10481 직후 본선lane1은 끝난다. 이전 차로군 모형의 목적지 배분이 이 차로에 직진 재고를 남겼다. 씨드23의2850초 해당 차로는 실제2대, 기존 예측20.6대였다.

`physical_lane_destination_policy`의 `prefer_exit`는 전체 희망 진출 비율을 유지하면서 계속 갈 수 없는 차로에 진출 목적 재고를 우선 배분한다. `clear_ending_lane`은 남은 직진 재고만 인접한 계속 차로로 보존 이전한다. 요청량은 기존 `n*v*dt/L`, 실제 이전량은 수신 공간 이하이며 진출 목적 라벨을 같이 빼지 않는다. 새 경로 수요를 만들지 않는다. 이 근사는 운전자의 목적지별 사전 차로 선택 전체를 재현한 것은 아니다.

`destination_clear_ending_lane_qualification_v2`에서 위 재고는2.88대로, 상태 보호는9/12로 개선됐다. 기본/직전12+12 결과와 서측은 동일했다. 그러나 이득 크기는 미달이다.

| 씨드·명령 | 실제ΔTTT | 위 후보ΔTTT [veh·h] |
|---|---:|---:|
|23 RM|−0.55333|−0.00217|
|23 VSL|−0.98194|+0.01002|
|23 동시|−0.51500|+0.00788|
|33 RM|−0.16222|−0.01833|
|33 VSL|−0.06278|+0.00532|

`fd_shape_probe_v1`에서는 기존 지수 FD의 첨두용량을 그대로 유지하도록 임계밀도를 변환한 two-branch FD를 동측에만 임시 적용했다. 용량 증대를 사서 얻는 비교가 아니다. 상태 보호7/12, 씨드23 VSL+0.04394로 실패했다. 기존 installer/FD 구현을 사용했고 실행 후 임시 함수를 복원했다.

`local_speed_fit_v2`는 무제어씨드23의2400초 이전 현재 상태와 실제 합류 노출에서6개 기존 계수를96회 제한 탐색했다. 10초 속도 오차는 줄었지만 단순 속도 유지보다 나쁘고, `local_speed_qualification_v2`의 씨드23 VSL+0.55062로450초 이득이 더 틀렸다. 채택하지 않는다. 국소 검사는 횡방향 운동량·내생 FIFO를 생략한 식별 진단이므로 전체 물리 모델 오차로 과장하지 않는다.

`physical_lane_momentum_advection`은 수용된 본선 이동량으로 차량 수×속도를 전달하고 기존 Euler 대류 항의 중복을 제거하는 후보다. 램프 진입 속도를 새로 가정하지 않고 기존 merge 손실은 유지한다. `momentum_qualification_v1`의 씨드23 RM/VSL은−0.00195/+0.00681로 역시 미달이다. 이 후보도 기본 채택하지 않는다.

## 미래 속도 원인 분리

`speed_oracle_v1`은 미래 실제 차로군 속도를 주되 N·흐름은 보존식으로 계산한다. **온라인 예측이나 controller 성과가 아니다.** 실제 속도를 전 구간에 주면 씨드23 VSL−0.34882, 씨드33 spread+0.23606으로 방향이 살아나지만 실제−0.98194/+0.63389의 크기에는 못 미친다. 합류 구간cell12–14만 주면 씨드23 VSL−0.49586, 하류cell15–20만 주면 씨드33 spread+0.08491이다. 구간 효과는 비선형이라 합산하지 않는다.

따라서 상류 VSL 적용 자체뿐 아니라10490→10484의 속도 반응, 하류 차량군 도착/방출을 연결해야 한다. 평균 속도 오차 또는 단일 이득 부호만 개선돼서는 완료가 아니다. 다음에는 실제 N·속도에서 계산한 `N*v/L`와 native 경계 통과를 대조해, 셀 내부 공간 분포를 잃은 유량 폐쇄가 남은 오차를 만드는지 먼저 판별한다. 근거 없이 다시 많은 계수를 한꺼번에 적합하지 않는다.

## 검증·실패 보존·운영 상태

- `tests_momentum_v1.json`:94개 검사 PASS. 과거 형상/FD/램프/배수/분포/차로군 검사와 새 감속·차로 저장·목적지·운동량 검사다.
- off-lane/destination config parameter 검사 PASS, 기존 경고 유지. 새 후보 기본 비활성. 과거 manifest는 덮어쓰지 않았다.
- interruption_qualification_v1은 상대 경로 준비 오류, receiving_probe_v1은 exclusive JSON 저장 재사용 오류, destination_clear_ending_lane_qualification_v1은 지역 변수 충돌에 따른 ledger 실패다. 각각 수정 후 새 결과 폴더에서 검증했다.
- local_speed_fit_v1은 비활성 VSL에도120 상한을 준 국소 검사였으므로 채택 근거에서 제외한다. v2가 수정본이다. scipy 미설치 때문에96회 자체 제한 좌표 탐색을 사용했다.
- 최초 stdin 단위검사는 Windows spawn이 `<stdin>`을 열지 못해 실패했다. 해당 실행 소유 PID12532/부모16440을 명령으로 확인하고 PID12532만 CIM 종료했다. 별도 사용자 Numerical Simulation 프로세스는 건드리지 않았다. 파일 기반94검사는 정상 완료했다.
- 이번 세션의 commit/push는 아직 없다. 아래 새 seed 실험은 미검증 후보의 전향적 반증 검사다. 기존 표본을 반복 보정한 뒤에만 검증하는 방식의 과적합을 피하려고, 미통과 상태를 명시하고 후보를 먼저 고정했다.

## 후속 핵심 발견: 같은 셀 안의 진출→진입 순서

`flux_closure_v2`는1초 native N·속도로 적분한 공간 평균 유량과 실제 셀 이탈을 비교했다. 씨드23 무제어 cell8의450초 이탈은732대인데, 공간 `Nv/L` 적분은593.45대다. 이것을 그대로 FD 용량 부족이라고 해석하면 안 된다. 이 셀에는 앞쪽 진출과 끝부분 진입이 함께 있어서 모든 차량이 셀 전체 거리를 주행하지 않는다. cell7의 VSL 이탈 증가44대는 셀 평균 속도장 적분으로24.62대, 마지막100m 적분으로43.54대다. 위치 정보가 평균에 사라지는 별도 문제도 있다. 마지막100m 실측은 미래 자료를 쓴 진단이며 예측 성과가 아니다.

| 포트 | 해당 셀 길이 | 실제 셀 안 주행거리 |
|---|---:|---:|
|10639 진입→셀 끝|526.29m|37.85m|
|10681 진입→셀 끝|526.29m|220.97m|
|10490 진입→셀 끝|492.79m|91.44m|
|10484 진입→셀 끝|492.79m|223.57m|
|셀 시작→10643 진출|526.29m|176.03m|
|셀 시작→10682 진출|526.29m|10.29m|

기존 모델은 이 차이를 sending에서 구분하지 않았다. 특히10483 진출7240.27m 뒤에10490 진입7243.09m가 같은cell13에 붙는다. 셀 진입량을 전부 같은 목적지 비율로 나누면 뒤에서 합류한 차량에도 이미 지난 진출의 목적 재고를 배정할 수 있다.

`physical_port_travel_lengths` 후보를 기존 `PhysicalLaneGroups`에 추가했다. 같은 셀에 뒤에서 합류한 재고를 따로 보존하고, 상류 진출 라벨을 부여하지 않는다. mainline 진입→진출, mainline 통과, ramp 진입→셀 끝의 실제 길이로 각각 `min(n,n*v*dt/L_path)`를 계산한다. 차량을 삭제하거나 비용에서 빼지 않는다. 현재 네 진입램프가 같은 셀 내 모든 진출 뒤에 있음을 기하에서 검사한다. 다른 순서는 조용히 일반화하지 않고 거부한다.

`ramp_origin_v1`은 예측 시점의 native 위치와 그 시점 이전의 램프 통과 차량 ID만으로 같은 셀의 초기 진입 출처를 추출했다. 기존12개 차로군 초기 재고와 정확히 일치했다. 미래 목적지나 미래 이탈로 초기 상태를 분류하지 않았다. 단, 각 종류의 내부 위치 분포는 여전히 균일 혼합 근사이며 작은 거리의10초 시간 절단 한계가 남는다.

`port_travel_qualification_v1`: 기본12개+직전12개 정확 일치, 서측 동일, 보존 PASS. 씨드23 RM−0.03829/VSL+0.00224, 씨드33 RM−0.03826/VSL+0.00424로 이득 보정은 미완료다. 상태 보호는6/12로 악화되어 바로 채택하지 않는다. 기존 셀 평균을 보상하던 계수를 새 이동 구조에 그대로 쓸 수 있는지 확인하기 위해 `port_travel_fit_v1`에서 무제어씨드13/23의4시점만 기존 `lane_group_response_20260919/fit.py`로 재보정하고 있다. 제어 결과는 이 계수 선택에 쓰지 않는다.

`tests_port_travel_v1.json`:96검사 PASS. 새 검사는10490 출처 차량이10483으로 돌아가지 않고91.44m의 잔여 길이로 이동하는지, 새 합류·본선/진출 재고와 원장 보존을 확인한다. `flux_closure_v1`의 완전히 비어진 구간 이탈 누락 가능성을 수정한v2가 최종 공간 비교다.

## 재보정 결과와 전향적 seed43 검사

`port_travel_fit_v1`의 무제어 보정은 완료했다. 11개 상이한 후보에서 상태 손실2.50981→2.41443, 선택된 동측 v_free 배율은1.0이다. `port_travel_fit_qualification_v1`의 상태 보호는8/12, 기본12개+직전12개 전체 예측은 그대로다. seed23 RM/VSL/동시 ΔTTT는−0.03996/+0.02560/−0.01429veh·h로 여전히 이득 보정 미완료다. RM 대기 비용을 없애거나 추가 보상을 주지 않았다. parameter 검사 PASS다.

`fresh_s43_v1`은 새 seed43에서 기존 고정 명령4조건을3000초까지 순차 실행한다. 첫 예측 구간은2400–2850초다. RM은10490 하나를g8→6→4, VSL은동측DSD51–58을100분포로 변경한다. 다른 레버·도시신호·망·수요는 동일하다. 제어기가 선택한 결과가 아닌 **고정 명령의 물리 반응 검증**이다.

기존 기준 `internal_cost`와 `port_travel_fit_v1`의 config·계수·물리 코드 및 프로토콜을 런 전에 `model_freeze.json`으로 고정했다. seed43 결과에 맞춰 이 검사 계수를 바꾸지 않는다. LDP/readback,2400초 이전 FZP 전체 행 일치, 보존, 현재 상태만 사용한450초 예측, 구성 비용/후보순위, 무제어900/1650/2400초 상태 오차를 함께 확인한다. 원시자료 분석은 네 런 종료 뒤에 수행한다.

평가 시 동측 물리 본선·4진입/4진출 커넥터 체류시간을1초로 계산한다. 본선 시작점 전 음수 좌표 차량은 별도 열로 보존하고 셀 상태와 일치하는 본선 비용과 구별한다. 도시부로 밀린 대기는 이 component 밖이므로 Ω 성능이나 full GNE 개선을 주장하지 않는다. 작은 단일 짝 차이를 통계적으로 확실한 제어 이득이라고 부르지 않는다.

### seed43 완료: VSL 이득과 선택 순위 실패

네 조건 모두3000초 정상 완료, LDP/readback·개입 전2400초 전체 FZP 행 일치 PASS다. `fresh_s43_v1/predictions/result.json`의450초 결과는 다음과 같다. 음수는 체류시간 감소다.

| 명령 | 실제 ΔTTT | 고정 기준 모델 | 고정 port_travel 후보 |
|---|---:|---:|---:|
|RM10490|−0.06028|−0.03897|−0.03831|
|VSL|−0.36972|+0.00424|+0.01825|
|동시|−0.05972|−0.03471|−0.02006|

실측 최선은 VSL, 두 모델은 RM을 고른다. 실측 선택 후회는0.30944veh·h다. 후보는 무제어 상태 보호도900/1650초만 통과하고2400초는 기준 오차2.6893→3.0733으로10% 제한을 넘는다. 따라서 **NOT_QUALIFIED**다.

VSL의 실제 구성 비용은 본선−0.44444, 진입−0.26417, 진출+0.33889veh·h다. 모델의 거의0인 총효과가 이 큰 상쇄를 설명하지 못한다. 평가 구간의 component 차량 삭제0, 설명되지 않은 본선 전이0이다. 시작점 전 음수 좌표 체류는 무제어0.01111/VSL0.01972veh·h로 별도 보존했다. native 도시부 차량 삭제가 전체 망에서 존재하므로 Ω 개선으로 확대 해석하지 않는다.

이 결과는 **당시 고정했던 소스**로 생성했다. 다음 수정 전에 `source_snapshot_v2/manifest.json`과14개 `.txt`로 원본을 보존했다. 첫 `source_snapshot/` 시도는 Windows 긴 경로 오류로 불완전하며 재현용이 아니다. 후속 핵심 코드 변경 때문에 현재 소스는 당시 `model_freeze.json` hash와 다르다. 과거 pin을 새 hash로 덮어쓰지 않는다.

## 다음 수정: 현재 위치와 조건부 진출 비율

`position_audit_v1.json`: seed43의2400초 cell9에는36대가 있으나10682 진출점 전에 있는 차는2대다. 당시 후보는 같은 셀 ramp 출처4대만 빼고 나머지32대에0.15748을 곱해5.039대의 진출 라벨을 만들었다.900초에는 진출점 앞0대인데2.5대를 배정했다. 이미 진출점을 지난 본선 차량에도 잘못된 진출 라벨이 생기는 것이다.

선택적 `physical_port_initial_positions`는 초기 라벨을 현재 진출점 전 재고 안에서만 배정한다. 미래 목적지를 사용하지 않는다. `port_positions_v1`에는 기존3개 seed의 현재 위치·과거 ramp 통과로 얻은 시작/150초 전 출처 재고와 진출 가능 재고가 있다. 초기 위치 제한만의 `port_initial_positions_qualification_v1`은 상태 보호8/12, seed23 VSL+0.02631로 이득 문제는 해결하지 못했다.

또한 과거 진출 비율 분모의 셀 말단 통과량에는 진출 뒤에서 합류한 차량이 섞여 있었다. `physical_port_origin_split`은

`동일 셀 ramp 출처 통과 = 관측 합류 + 시작 출처 재고 − 종료 출처 재고`

를 셀 말단 통과량에서 빼고, 상류에서 온 이탈 집단에 조건부로 진출 비율을 구한다. 예를 들어 seed23의2400초10483 비율은0.18298→0.21393이다. 이는 과거 이탈 집단의 비율이며 **설정 OD 희망 수요를 추정·변경한 것이 아니다.** 관측되지 않은 대기 목적지를 알아낸 것으로도 해석하지 않는다.

`port_origin_split_qualification_v2` 역시 상태 보호8/12, 기본12개+직전12개 JSON 동일이다. seed23 RM/VSL/동시 예측−0.04138/+0.01241/−0.02891veh·h로 이득 미완료다. `tests_port_origin_split_v1.json`의100검사는 PASS다. v1 검증은 새 지역변수 `rows`가 CSV reader를 가려 중단됐고, `history_flows`로 고친v2가 완료본이다.

실제 미래 속도를 주는 진단을 같은 새 구조로 반복한 `port_origin_split_speed_oracle_v1`도 seed23 VSL−0.22791(실제−0.98194), seed33 spread−0.14433(실제+0.63389)로 부족하다. 온라인 예측 성과가 아니다. 따라서 다음은 추가 속도 계수 적합보다, 셀 평균이 차량의 셀 내 위치와 통과 시각을 잃어 유량을 잘못 계산하는지 `flux_moments_v1`에서 확인한다. 현재 위치1차 모멘트의 비음수 선형 분포 복원은 계수 없이 먼저 진단하며, 아직 plant에 넣지 않는다.

## 공간·경계·하류 소실 후속 검증 완료

위 공간 진단은 `flux_moments_v2`와 `resolution_oracle_v1`까지 완료했다. 위치만의 선형 복원은 실패했다. 뒤쪽 절반의 현재 N·속도는10초 유량 오차를 줄이지만, 실제 미래 속도/유입을 준450초 진단에서 기존 거친 격자도 진출입 없는 구간의 비용 차이를 상당 부분 설명한다. 전 망 격자를 무조건 더 잘게 바꾸지 않는다.

속도 원인 분리 도구가 merge/FIFO 후에도 실측 속도를 유지하도록 고쳤다. `diagnostic_validation_v1.json`에서7,293개 차로군 속도 표본이 정확히 맞고, 그래도 전체 순이득은 실패한다. 미래 배수를 주어 총합만 맞아진 경우에도 진출 비용 부호가 틀리면 성공으로 인정하지 않았다.

`component_boundary_cohorts_v2`는 실제 진입·정상 유출 사건과 초기/나중 진입 차량 집단의 체류를 분리했다. seed33 분산 축소 손해+0.63028veh·h 중 초기 차량 집단의 변화는+0.01528, 이후 진입 집단은+0.61500이다. 유입 시각의 회계 기여를 단순히 빼서 제어 이득이라고 부르지는 않는다.

`urban_drain_observations_v5`에서10643→126→71 연결과 실제 SC1004 신호를 확인했다.8,408개 신호 표본이native LDP와 일치하고4,200초의 상태·흐름이 보존식에 맞는다. 단71에는 정상 방출 외의 비정상 소실이 있다.2400–2850초 seed23 NC/VSL10/6대, seed33 NC/spread7/9대이며 후자에는 route-next-link 실패+FZP 소실이 포함된다. 원래 component 밖에 있는 소실도 공유 하류 대기열과 배수에 영향을 줄 수 있다.

이것이 모든 이득의 원인이라는 주장은 아니다. 첫 진출 방출 차이는 서로 다른 소실이 발생하기 전부터 나타난다. 다만 삭제를 보존 모형의 정상 capacity로 적합해서는 안 된다. 상세 수치·한계·다음 선택은 최신 체크포인트를 따른다. 이 단계에서는 core/adapter/runner/writer/기본 config/망/수요를 변경하지 않았고 신규 native 실행도 없다.
# Latest: native downstream local stop/release audit

See `DOWNSTREAM_LOCAL_STOP_RESPONSE.md`, `downstream_wave_v2/validation.json` and `downstream_fd_resolution_v1/result.json`. The matched native1s RM downstream benefit includes less local stopping and time-varying positive/negative costs. Coarse density hides some stopped clusters, but a no-fit finer-density FD aggregation does not improve conditional next-second speeds. This is new diagnostic evidence, not450s causal gain qualification. Canonical/default model and native network unchanged; all owned calculations terminal. NOT_QUALIFIED, goalactive.

# Latest: first merge response and rejected startup cap

See `MERGE_ORDER_AND_RESTART_LIMITS.md`, `first_merge_response_v2/validation.json` and `restart_response_validation_v1/result.json`. Native original9 matches312,712rows, initialcohort5,189rows. Same11ramp merges/60s still changes mainline/ramp ordering: the first affected mainline vehicle brakes after a5.890m NC gap, while RM delays the entering vehicle2s. Regional response later reverses; this is not proof of net gain from that event. Fixed-lane20s startup support/errors are insufficient; a mean-car acceleration cap never binds the existing downstream prediction in9,000steps, so neither is adopted. Next identify causal current-gap/relative-speed dependence rather than repeat pulse-only or parameter sweeps. Production/defaults/network unchanged, no new native run, all owned work terminal. NOT_QUALIFIED, goalactive.

# Latest: conditional gap and acceleration memory

See `CURRENT_GAP_AND_MEMORY.md` and `current_gap_history_v1/validation.json`. NC-trained short conditional forecasts improve when current relative speed/gap/previous acceleration are supplied. Validation1s RMSE5.363→3.385,10s24.699→22.111km/h. These are per-cutoff observed-current-state fits, not canonical450s plant/gain improvements. Full initial5189cohort avoids the first narrow pool's lack of VSL exposure; later generated IDs remain excluded. Recovery magnitude and simultaneous-control loss remain wrong.19source pins, exact training-table refit and feature/time leakage checks pass; no production/native/network change. Next assess compact lane-group states and self-propagation, preserving all full qualification requirements. Goalactive, NOT_QUALIFIED.

# Latest: compact autonomous-state gate

See `COMPACT_STATE_PROPAGATION.md`. Local6-cell30s autonomous prediction is now tested, using only current states and a past30s boundary estimate. Compact linear moments do not improve consistently. A conserved-moment transport extension preserves mass but produces14impossible mean0/positive-variance states in NC/VSL2550; `compact_moment_transport_v1/validation.json` explicitly rejects it. This is not a new canonical adapter or a full lever/cost test. Next require a realizable nonnegative population/speed representation before further local prediction and full qualification. No production/native change, all own workterminal, goalactive/NOT_QUALIFIED.


## 2026-09-21 latest: positive speed populations and neighbor persistence

See `SPEED_POPULATION_AND_RECOVERY.md` (cohort_dynamics_20260920). The absolute transition kernel's zero-change mixing defect was corrected and archived. Positive speed populations preserve mass/realizable moments but still recover too quickly. Refining acceleration phases does not fix the local30s forecast; conditioning on current mean speed reduces some errors but remains worse than the simpler comparator on key states. Do not promote these candidates or continue broad bin/parameter sweeps. The newest local validation replays64forecasts and1920mass steps; canonical core4files unchanged. Current-state gap/history conditional reaction helps, but native geometric leaders persist only51.9% at10s and19.9% at30s among continuously observed pairs (616initial pairs). A frozen-neighbor rollout is not justified. Next distinguish current native interaction targets from geometric neighbors in same-cohort short-response identification before proposing a causal neighbor-change closure. Off-ramp spillback/ramp waiting, full450s costs/ranking, NC guards, fresh holdout and canonical integration remain outstanding. All owned work terminal; no native/network/default changes or commit/push. Goalactive, NOT_QUALIFIED.
