# Selected 17 SC capacity audit — actual source run, t=900

현재 17개 제어신호 전체가 `206.530612 veh/h/lane`에 고정된 것은 아니다. 실제 설치 설정에는 측정 용량이 적용된다. 그러나 **이동 회전비율 beta>0**인 이동 243개 중 110개는 정규화 기본값, 8개는 같은 기본값으로 다시 정한 물리 회전 용량, 1개는 기본값에 SC7 동시현시 계수를 곱한 값을 사용한다. 이 문서의 이동 분류 β는 목적함수의 TTD 가중치 β와 다르며, 감사 대상 런의 목적함수 가중치는 β=0이다. 더욱 직접적인 관측 문제는 **현재 raw900 이탈 계수의 실제 비교창이 720–870초이고, 녹색 분모는 실제 native SG 노출이 아닌 action750의 미실행 기본 녹색**이라는 점이다. 실측 차로별 포화용량이 검증되었다는 결론은 낼 수 없다.

대상은 `codex_area_sources_beta0_s13_20260910`의 `state_000900.json`, `action_000750.json`, `action_000900.json`과 런에 보관된 source manifest이다. `build_projected(..., fixture_inputs=False)` → 정본 `configure_runtime`을 실행하고 설정 함수 반환 시 값만 복사했다. 최종 용량 관련 메타데이터는 실제 action900과 전부 exact 일치한다. 정본 local model 생성/getter 및 worker 재설치까지 확인했으며 optimizer, endpoint, VISSIM은 실행하지 않았다. 런 manifest의 130개 source/output 및 명시 입력은 전후 SHA 동일이다. 전체 이동/링크/SG/프로그램 표와 SHA는 동명 JSON, 이동별 요약은 CSV, 재현기는 PY에 있다.

## 실제 최종 용량

전체 선언 이동 251개 중 β>0은 243개다. 아래의 ‘활성’은 이 β 조건이며 실제 출발 차량 수를 뜻하지 않는다. β=0이어도 초기 투영 큐가 남는 이동이 있을 수 있으므로 JSON/CSV에는 251개 전부 포함했다.

| 최종 용량 출처 | β>0 이동 | 의미 |
|---|---:|---|
| 측정 차로군 배분 | 118 | 링크 추정치 × 정적 seed 차로군 비율 × 해당 현시 내부 이동 β 비율 |
| 차로 정규화 기본값 유지 | 110 | `330 × 184 / 294 = 206.530612` × 기하/대체 차로수 |
| 기본값 × native concurrency factor | 1 | SC7의 `327.912639`; 새 측정값 아님 |
| 물리 회전 하나로 합치면서 기본값 재설정 | 8 | `route_choice_corridor`의 고유 connector 차로수 × 206.530612 |
| geometric fallback | 3 | 1800/lane: SC109 N→W, SC1005 E→W/N |
| gate on-ramp 명시 override | 3 | 각 1800, 무신호 ramp queue 경로 |

110개 기본값 이동의 종류는 internal 17, boundary_in 62, boundary_out 21, off_ramp 10이다. 현재 측정 배분의 `_LG_KINDS` 기본값은 `{'internal'}`이며 활성 설정에 `lane_group_kinds`가 없다. 따라서 다른 종류의 이동은 링크 관측 필드가 있어도 이 배분을 받지 않는다. 또한 fallback='geometric'은 **증거가 없는 internal, origin 링크 존재, covered link와 불교차, queued 분류와 불교차** 조건에만 적용한다. 미배분 이동 전체를 보완하지 않는다.

실제 SC1004는 β>0 22개 중 최종 측정 배분 0, 정규화 기본값 유지 16, 물리 회전 기본값 5, on-ramp override 1이다. SC1004 링크 46/p1, 66/p1, 71/p3의 `sat_est`는 생성되지만 현재 종류/현시/접근로 교집합에 측정 대상 internal 이동이 없어 3개 그룹 모두 members가 빈 목록이다. ‘sat_est가 있다’와 ‘해당 이동 용량이 갱신된다’는 다르다.

메타데이터 `measured_capacity_movements=127`은 설치 시 배분 assignment 124회 + geometric 3회를 센다. 이후 topology 변경을 지나 최종 이름으로 남은 측정 assignment는 120개이고 이 중 2개는 corridor 설정이 다시 덮어써, 최종 측정 출처가 118개다. SC107 E→W는 4221.100488에서 826.122449로, N→W는 385.278240에서 206.530612로 다시 설정된다. 전자는 선택 SG 제어 회전, 후자는 무신호 가지다. 이 수선의 기존 목적은 물리 회전 중복을 없애는 것이었으며 용량을 새로 식별한 것은 아니다.

`install_movement_capacity_by_lanes` 자체에는 녹색비가 없다. 최종 값은 GREEN일 때 적용하는 서비스율이며 실제 서비스 식에서 한 번 더 `green_fraction × dt`가 곱해진다. 따라서 206.53을 ‘실측 평균 처리량’이나 ‘검증된 포화교통량’으로 부르면 안 된다. 기존 SC15 전용 calibration은 SC15에만 적용되며 이 표의 17SC 값이 자동 보정되지는 않는다.

## 측정이 갱신되는 방식과 관측 공백

실제 t900의 추정 링크는 60개다. 45개는 decay×previous/seed가 지배하고, 5개는 observed running maximum, 10개는 queued EWMA이다. `measured_capacity_observed_links=18`은 유일 링크 수가 아니다. queued EWMA를 적용한 뒤 `obs >= carried` 조건도 참인 링크가 중복 가산되기 때문에 실제 관측 분기가 반영된 유일 링크는 15개다. EWMA의 queued 판단도 해당 창의 포화 지속 여부가 아니라 **t900 순간 `link_stopped_counts >= 6`**이다.

`link_departures_window`, 순간 stopped/count/speed, window mean/max 필드는 실제 수치 조회 합집합 680개에서 결측 0, 비유한값 0이다. 현재 17SC의 physical head 보유 링크 74개도 이 필드에 전부 존재한다. 조회 누락을 일반적인 원인으로 지목할 근거는 없다. 별도로 detector/origin 귀속에 등장하는 721개 support 중 289개는 이 로컬 필드 밖에 있지만, 이들은 capacity 함수가 각 링크 수치를 모두 조회하는 목록이 아니다. 수치 조회 누락 289개로 세지 않았다.

활성 seed 그룹 90개 중 19개는 측정 배분 대상 이동이 없다. 11개 그룹은 현재 INPX/선택 SG→phase에서 동일 link/phase head가 없다. 대부분은 빈 배분으로 끝나지만 403/p1은 현재 선택 head SG7/p2와 다른 역사적 그룹을 내부 N→W 이동에 배분한다. 링크32는 현재 SC1001 정지선 head가 없지만 역사적 seed/previous estimate가 남고, 실제 현재 head127은 측정 estimate가 없다. 이는 필드 결측과 별개의 오래된 그룹/현시 지원 범위다. 일괄 capacity 증가는 이 위치·현시 문제를 해결하지 않는다.

seed의 ‘sustained’ 이름도 그대로 포화 검증으로 해석할 수 없다. 실제 producer는 이전 150초 스냅샷에 있던 차량 ID가 다음 스냅샷에서 같은 링크에 남지 않았는지를 세며, 중간에 들어왔다가 나간 차량은 보지 못한다. 녹색 분모는 `signal_group_actuation_plan_v3.json`의 axis green 값이다. 현재 선택 mainline 계획이나 실제 native clock을 직접 적분하지 않는다. 이 자료는 검증이 필요한 초기 추정 근거이며 차로별 head crossing 전수 자료가 아니다.

## 실제 시간창과 녹색 노출

현재 runlog는 `RUN_MODE=STEPWISE controller=wu-link`이다. STEPWISE에서 900초 순서는 `RunControllerDecision` → `WriteStateJson(..., True)` → `ResetQueueWindow` → `LogStateCsv(900)`이다. 이탈 계수와 평균/최대는 `LogStateCsv`에서만 누적되고, reset은 `prevVehLink`를 지우지 않는다. 따라서:

- raw900 window samples=5: 점유/정지 표본 750, 780, 810, 840, 870초.
- 이탈 비교는 이전 log720과 log750의 전이를 시작으로 마지막 840→870까지, **720→870초**.
- 900 순간 count/stopped/speed는 새 스캔이고 window 추정치와 다른 끝 시각이다.
- 이후 raw1050도 같은 순서라 departure 창은 870→1020이며, 최초 제어 경계900을 가로질러 native와 새 command 노출이 섞인다. 현재 estimator는 action900 하나의 완전 주기 녹색으로 나눈다.

이는 완료 NC의 raw900을 재사용한 결론이 아니다. 완료 NC의 장시간 raw 관측 창과 혼합하지 않았다. native 시간표 검증에만 완료 NC의 `.lsa` 이벤트를 사용했다.

각 17SC의 actual Ver2 INPX `active`, FIXEDTIME, progNo=1, controller offset=0 및 각 SIG 내부 program offset을 읽었다. 물리 head가 있는 SC/SG 조합 114개 중 113개는 완료 NC LSA가 존재하며, 750–900 및 720–870 두 구간 각각 모든 정수초 상태와 녹색 적분이 canonical `parse_sig`와 일치한다. SC5 SG18은 LSA 시작 상태가 없어 검증 불가로 남겼다. 이 SG는 선택 writer 대상 밖이다. 모든 controller/SIG 경로와 원시 SHA는 JSON에 있다.

action750은 NoControl이고 CSV는 VSL66 + meter8행이며 도시 signal 행은 0이다. 그런데 `_measured_green_sec_by_link`는 JSON의 미실행 기본 녹색 34.5/47초를 읽는다. 60개 추정 링크 중 실제 head가 있는 59개를 비교하면 **52개 분모가 native link GREEN union과 다르다**. head32는 없으므로 이 비교에서 제외했다. 요청한 750–900 표와 실제720–870 표를 함께 저장했다. 두 표는 SC7의 1220007502,1220008601에서 1초씩 다르고 나머지 링크 union은 같다.

| 링크 | t900 업데이트 | 이탈 count | 사용 분모 s | native union s, 720–870 | 같은 count/노출 환산율 veh/h |
|---|---|---:|---:|---:|---:|
| 1220011503 | running max | 56 | 34.5 | 75 | 2688.00 |
| 1220021201 | queued EWMA | 31 | 34.5 | 74 | 1508.11 |
| 30 | running max | 38 | 34.5 | 69 | 1982.61 |
| 403 | queued EWMA | 41 | 69 | 23 | 6417.39 |
| 66 | queued EWMA | 17 | 34.5 | 69 | 886.96 |
| 71 | queued EWMA | 26 | 34.5 | 69 | 1356.52 |

마지막 열은 같은 불완전 이탈 count의 **단순 분모 비교**다. 재추정 권장 용량이나 실측 포화용량이 아니다. 링크에서 떠난 차량은 신호 head 통과, head 전 우회, 망 이탈 등을 구분하지 않고, 30초 사이 해당 링크에 들어왔다가 떠난 차량은 누락될 수 있다. 또한 여러 차로군에서 동시에 출발하면 링크 전체 이탈/union GREEN은 접근로 총 노출당 방류율이지 단일 차로군의 포화율이 아니다.

`mainline_only=true` 제어 이후에도 SG>8은 COM 소유권을 받지 않는다. head가 있는 미선택 SG는 SC5 10/14/18/20/24와 SC7 12/16이며 8개 physical link에 있다. 이들은 선택 offset/green의 노출로 대체하면 안 된다. 본 비교의 추정 head59 링크는 모두 선택 head만 있으나, 경로 상류의 native 보조 신호 영향은 별도로 남는다.

## 국소 후보와 전역의 공유 서비스

최종 251개 이동에서 `LocalSignalModel.cap_flow_of`와 정본 `_movement_capacity_flow(actual_action)`의 수치 차이는 0이다. worker hook 재설치 전후 capacity map도 exact 동일이다. 이는 용량 숫자 배선의 일치만 검증한다.

물리 connector10634를 공유하는 SC1004 W/offE/offW→E는 각각 같은 619.591837을 읽고, 전역 corridor는 3개 source를 **단일 accepted service pool**로 제한한다. 국소 phased/ramp-aware stepper는 per-movement 서비스와 receiving space만 적용하며 이 connector pool이 없다. 충분한 재고·수신공간·모두 GREEN인 5초 대수 상한은 국소 2.581633대, 전역 공유 풀 0.860544대다. 이는 포화 가정의 코드 비교이며 실제 t900 방류나 선택 행동 오차를 실측했다는 뜻은 아니다. 전역 Ω endpoint는 최종 점수를 다시 계산하지만 국소 green/offset 방향 탐색에 이 차이가 남을 수 있다. 다른 물리 head 공유 목록은 기존 pinned route audit에서 직접 확인되는 local head만 모은 하한 목록이며 모든 우회/상류 authority를 해결했다는 주장은 하지 않는다.

## 다음 최소 수선 계약 — 미적용

1. 관측 snapshot에 단일 timestamp를 붙이고 window를 decision 시각까지 닫은 뒤 serialize/reset한다. 이미 얻은 decision 스캔을 재사용하고 같은 timestamp가 뒤의 logger에서 이중 누적되지 않게 한다. 마지막 endpoint frame은 다음 창의 첫 전이 비교용으로 보존한다. `window_start_sec`, `window_end_sec`, 표본 시각/횟수, 전이 coverage를 함께 기록한다. 한 번의 reset 순서 변경만으로 완료 NC의 다른 scheduler 경로까지 동일하다고 가정하지 않는다.
2. 같은 `[start,end)`에서 실제 head/SG GREEN 노출을 기록한다. 제어 SG는 실제 writer command/COM readback, native SG는 COM ownership + 검증된 active program/offset/clock을 구분한다. 과거 JSON의 편의상 기본 녹색을 실행 노출로 쓰지 않는다. mixed native/controlled 창은 시간별로 나눈다.
3. 링크 집계라면 `union GREEN seconds`와 `lane-green-seconds`를 각각 저장한다. union은 하나 이상 head가 GREEN인 시간, lane-green은 차로별 GREEN 노출 합이다. head가 여러 위치에 있거나 우회가 먼저 갈라지면 단순 lane합도 중복/authority 혼합이 가능하므로 고유 서비스 위치·SG·차로와 실제 통과 집합이 먼저 필요하다. 같은링크 총 이탈을 임의의 한 SG로 배분하지 않는다.
4. 시간창을 맞춘 뒤에도 포화 식별은 별도다. 실제 head crossing 또는 대응 detector count, GREEN 중 대기/하류 수신 상태와 동일 차로군을 연결해 검증한다. 현재 rolling max/EWMA와 seed를 관측 원자료·가정값으로 구분하고 결측/불완전 창에서는 검증된 이전값 유지 또는 명시 진단으로 처리한다. 206.53 일괄 교체, 새 수치 fit, VSL capacity gain은 이 감사 범위에 없다.

근거 코드: adapter `install_movement_capacity_by_lanes` 3740, 정규화 3803, `install_measured_movement_capacity` 4065, 업데이트 4271, lane-group 배분 4383, 녹색 분모 4439; `runtime_setup.py` 90/100/129/196; `route_choice_corridor.py` 364/622/656; `urban_flow_accounting.py` 435/449; vendor `local_signal_plant.py` 90/245/401; VBS STEPWISE 624, `WriteStateJson` 2430/2526, `LogStateCsv` 2815/2847, `AccumulateDepartures` 3242, `ResetQueueWindow` 3488, native SG 제외 1968; sustained producer 65/95. 전체 과정은 read-only였으며 실행 소스·설정·네트워크 변경은 0이다.

재현: `python -X utf8 -m diagnostics.selected_signal_capacity_audit --run codex_area_sources_beta0_s13_20260910` (마지막 실행 3.65초). `*.json`, `*.csv`만 다시 생성한다. 이 문서는 같은 입력에 대한 해석이며 실행 중 새 decision을 자동으로 읽지 않는다.
