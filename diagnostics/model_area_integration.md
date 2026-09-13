# Ω 관측·예측 연결: 실행 가능한 최소 수정

기준: `6056c94` worktree, n7 실제 설치 순서, NC `state_000900.json` 및 저장된 n7 상태 재현. Ω는 사용자가 확정한 **고속도로 + 도시 보호망(PN)의 합집합**이다. 도시↔고속도로 내부 이동은 TTD가 아니다. 소유권 대장은 변경하지 않는다.

## 1. 구현한 수정과 적용 순서

`evaluation/controllers/observation_projection.py`를 구현했다. 실행 중인 어댑터는 편집하지 않았다. 적용할 정확한 diff는 `diagnostics/observation_projection.patch`, 시나리오 overlay는 `diagnostics/observation_projection_config.json`이다. `diagnostics/prepare_observation_projection.py`는 현재 어댑터를 읽어 diff를 재생성하며 어댑터를 쓰지 않는다.

하나의 키 `observation.physical_branch_projection.enabled`로 켠다. 키가 없거나 false이면 cfg와 detector mapping을 수정하지 않고 동일 객체를 반환한다. 기존 n7의 제어 상태 재현을 유지한다. true이면 기존에 설치된 직행/신호 분기 저장고에 물리 관측을 배정한다.

| 물리 관측 링크 | 새 예측 저장고 | Ω | 의미 |
|---|---|---|---|
| 10491 | OR_D_W_storage | 안 | 대모 서행 신호 경유 분기 |
| 10638 | OR_F_W_storage | 안 | 양재 서행 신호 경유 분기 |
| 10481 | OR_D_E_storage | 안 | 대모 동행 신호 경유 분기 |
| 10643 | OR_F_E_storage | 안 | 양재 동행 신호 경유 분기 |
| 10479, 10775, 125 | SC1001_W_tail | 밖 | 대모 서행 외부 직행 + 종단 도로 |
| 10645, 10773, 123 | SC1004_W_tail | 밖 | 양재 서행 외부 직행 + 종단 도로 |

동행 직행 10483→124와 10682→121은 기존 W_out에 남는다. 이들은 검증된 고속도로 재진입 회랑 안에 있다. 이 표는 ownership 교체가 아니라 물리 관측→이미 존재하는 모델 재고의 투영표다.

새 투영은 선택한 링크의 전체 관측을 한 저장고에만 배정하고, 해당 링크의 기존 movement queue 투영을 제거한다. `queue_origin_binding`이 켜져도 다시 큐에 배정되지 않도록 전용 링크는 storage_fraction=1로 처리한다. freeway/ramp/monitor-only-exit 관측 채널과의 중복, 같은 저장고의 양의 미등재 관측원을 거부한다. projection audit는 목표 재고에 실제 도착한 대수와 원시 대수의 잔차가 0인지 확인한다.

어댑터 patch의 분기 관측 부분은 다음 다섯 지점이다. 이후 같은 flag로 ramp spillback 중복 관측 두 지점도 추가했다.

1. 독립 module import.
2. `build_local_observation_summary`에서 전용 물리 링크 목록 로드.
3. 전용 링크에 storage_fraction=1, queue origin binding 재진입 방지.
4. summary 반환 전 배정 대수 감사 및 물리 링크별 provenance metadata 기록.
5. `main`의 direct/landing/leg-ramp runtime 설치 뒤, `traffic_state_from_vissim` 직전에 mapping과 용량 설치.

같은 flag가 켜졌을 때 ramp 접근부 정지차량은 `ramp_spillback` 관측/guard 값으로 계속 남기지만 `ramp_queue`에 다시 더하지 않는다. 그 차량은 이미 도시 저장고/큐에 있고, 실제 ramp 커넥터 차량은 기존 ramp 관측에 따로 있다. `ramp_spillback_observed_only`와 `ramp_spillback_duplicate_avoided_veh`를 기록한다. 분기 전 경로를 추측하여 도시 차량을 ramp로 옮기지 않는다.

worker는 수정된 cfg를 받는다. 이 수정은 runtime function monkeypatch를 추가하지 않으며, 이미 투영한 초기 상태와 cfg의 저장고 용량을 전달한다. follower 모델 캐시는 cfg 교정 뒤 생성되어야 한다.

## 2. 검증 결과

`diagnostics/test_observation_projection.py`: **9 tests PASS**. 검증한 내용은 아래와 같다.

- 20대 합성 관측의 신호 12대 / 외부 직행 8대 단일 배정.
- 전량 정지한 신호 커넥터 + queue origin binding ON에서도 movement/ramp queue 0, storage 합 20.
- 일반 도시 접근부 정지20대는 기존 도시20+ramp20=40에서 수정 후 도시20으로 보존된다. spillback guard 관측20은 그대로다. flag OFF는 기존40을 재현한다.
- disabled cfg/mapping 객체 무변경.
- 공유 물리 채널, 미등재 재고원, clipping 및 이중 배정 검출.
- 관측 하한으로 용량을 확장한 경우 대수 보존 및 확장량 공개.
- NC 900초와 테스트 실행 당시의 모든 n7 상태를 **실제 main 설치 순서**로 재현하여 총 모델 재고 차이가 정확히 기존 spillback 이중관측 제거량과 같음을 확인했다.

상태별 결과는 `diagnostics/observation_projection_replay.json`에 기록했다. 마지막 검증은 총38개 상태(NC900 + n7 최종5400초까지)이며 n7 이중관측 제거량의 최대값은38대다. 테스트는 어댑터 제안 함수를 메모리에서만 컴파일한다. VISSIM 실행이나 production 파일 변경은 없다.

NC 900초에서는 원래 0이던 OR 저장고가 순서대로 D_W=1, F_W=10, D_E=5, F_E=4가 된다. SC1001_W_tail=27, SC1004_W_tail=33이 된다. 기존 W_out에서 외부 60대를, in_SC*_W에서 신호 커넥터 20대를 이동시킨 결과이며, 합계는 **2621.6890509521886대 전후 동일**이다. 이 상태에서는 spillback duplicate가0이다. 원시 전체2591대와 남는 차이는 다른 투영/기하 재구성 경로의 별도 문제이며 이 패치가 해결했다고 주장하지 않는다.

## 3. 일괄 cap 120/200을 실제 지오메트리에 맞추기

관측을 기존 OR 저장고에 넣기만 하면 옛 일괄 cap 120과 물리 크기가 불일치한다. overlay는 ledger가 고정한 INPX hash를 검사하여 3D polyline 길이×차로수를 구하고, 정본 `network.urban_avg_vehicle_length_m=6`으로 나눈 값을 명시한다. 이 값은 해당 spacing에 따른 용량 추정이며 실측 jam density 자체가 아니다.

| 저장고 | 지오메트리 용량 veh |
|---|---:|
| OR_D_W_storage | 38.582370 |
| OR_F_W_storage | 96.050442 |
| OR_D_E_storage | 151.472003 |
| OR_F_E_storage | 106.332776 |
| SC1001_W_tail | 655.183505 |
| SC1004_W_tail | 1150.272483 |

용량 계산의 링크별 길이·차로수·spacing·Ω 여부는 overlay `geometry_evidence`에 있다. 평균 차장/간격 추정이 실제 재차보다 작은 경우를 숨기지 않도록 `capacity_policy=observed_lower_bound`를 명시했다. 실효 cap=max(명시 cap, 이번 관측 재차)이며, `observed_floor_added_veh`를 별도 기록한다. 실제로 존재하는 차량 수는 물리 capacity의 하한이라는 근거다. 이 정책은 초과 차량을 버리지 않지만 물리 jam 용량을 정확히 식별한 것은 아니므로, 해당 카운터가 양수인 경우 spacing 민감도/실측 포화 관측으로 보완해야 한다. 무단 상수 .5 분기나 임의 queue 생성은 하지 않는다.

## 4. 실제 runtime은 이미 잠재 분기가 있다

앞선 raw detector supports의 OR_D_W/OR_F_W 혼합 판정만으로 4→8 off-ramp 개편이 필수라고 결론 내리면 틀린다.

- adapter `install_offramp_direct_landing` 3097~3164는 D=.468/F=.484를 현재 기본 분율로 설치한다.
- `install_offramp_landing_runtime` 3170~3200의 실제 schedule은 `s*flow`를 direct tail로, 나머지만 원래 OR storage에 넣는다.
- 서행 direct는 W_tail, 동행 direct는 W_out이다.
- `install_leg_ramp_split_runtime`도 n7에서 켜져 W_out 램프 몫을 재주입한다.

따라서 지금의 OR storage는 신호 분기라는 의미로 사용할 수 있다. 원시 `off_ramp_connectors`의 두 커넥터를 모두 OR storage support로 역변환하는 일반 함수는 설치 후 이 의미를 놓친다. `control_area_objective.detector_stock_supports`의 원시 그룹 지원 검사 결과는 보수적 감사이며, 설치 후의 분기 투영표가 우선해야 한다.

물리 8분기는 서로 다른 freeway 위치에 있다. 추후 branch별 spillback 위치까지 모델링할 때 8개 분기 확대를 검토할 수 있지만, 현재 관측 오류의 최소 수정으로 요구되지는 않는다. 단순히 그룹 수만 늘리면 hardcoded direct installers, split ratio, cell index, cap, movement/agent 연결 및 worker 설치 경로를 모두 갱신해야 한다.

## 5. 아직 필요한 국소 예측 일치 수정

**확정된 불일치:** vendor `wu_faithful_follower.py:2320~2344`는 OR 저장고 가용량만으로 전체 off-ramp flow를 제한하고, **전체 flow**를 signal OR occupancy에 더한다. `local_freeway_plant.py:260~265`는 total diverge를 반환한다. 반면 위 실제 global schedule은 direct/signal로 분기한다. `offramp_direct_share_by_offramp` 검색은 adapter에만 나온다.

직행을 `_local_offramp_drain`의 신호 drain에 더하면 잘못된 재고에서 빼는 셈이다. 수정 위치는 **inflow dispatch와 receiving capacity**다.

1. cfg의 기존 direct share/target dictionary를 국소 모델에서도 읽는다.
2. 후보마다 OR signal occupancy와 direct target occupancy를 별도로 복사하고 갱신한다.
3. 고정 분율을 유지할 경우 전체 flow 수용량은 signal_available/(1−s)와 direct_available/s 중 작은 값으로 제한한다. s=0/1은 해당 경로만 쓴다. 단위는 veh를 dt_h로 나누어 veh/h.
4. 실제 accepted total flow f의 (1−s)f만 OR storage에 넣고 sf는 direct target에 넣는다.
5. 신호 분기 drain은 실제 저장 차량량과 downstream available 양쪽으로 제한한다. direct target의 출구/램프 분기 처리도 global runtime과 같아야 한다.
6. 한 substep test: 총 10대, s=.4, 수용 충분→OR6/direct4. direct target 포화→고정 분율 모델의 accepted total 0; 초과6/4를 임의 다른 분기로 보내지 않는다. 반대로 global이 분기별 독립 diverge를 쓰도록 바꿀 경우 양쪽을 같이 바꾼다.

이 수정은 부모/수요·관측 에이전트가 담당한 local conservation 모듈과 결합해야 하므로 vendor/adapter를 중복 편집하지 않았다.

**global receiving 추가 확정 오류와 수정:** `urban_queue_model.py:487~506`의 기존 cap은 OR만 확인한다. `coupling.py:225~227`은 schedule의 rejected를 진단에 더할 뿐 FW에서 이미 빠진 차량을 복원하지 않는다. 따라서 direct tail 포화 시 accepted되지 못한 direct 차량이 사라질 수 있다. `observation_projection.install_direct_branch_capacity_runtime`을 추가하여 같은 `link_predictor.branch_capacity` helper를 global cap에 사용한다. cfg.network.local_landing_state가 켜질 때만 동작하며 false cfg는 기존 함수를 그대로 호출한다. coupling의 imported alias도 재바인딩한다. 적용 diff는 `diagnostics/direct_branch_receiving.patch`이며, 관측 patch 적용 뒤 사용하고 **main의 link_predictor.configure 뒤** 및 spawned worker에서 설치해야 한다. 이 선행 수용 제약은 차량을 FW에서 빼기 전에 양쪽 목적지 수용량을 확인한다.

## 6. 분율은 관측 출구 표본으로 검증해야 한다

NC 900초 저장 상태의 `link_departures_window`로 계산한 분율은 다음과 같다. 같은 구간의 커넥터 통과수 비율이며 미래의 정확한 경로 확률이라고 단정할 수 없다. 표본 지연·짧은 커넥터 누락을 확인해야 한다.

| 그룹 | direct 커넥터 | direct/total window counts | 관측 비율 | 현 설정 |
|---|---|---:|---:|---:|
| OR_D_W | 10479 | 58/179 | .324022 | .468 |
| OR_F_W | 10645 | 62/112 | .553571 | .484 |
| OR_D_E | 10483 | 69/129 | .534884 | .468 |
| OR_F_E | 10682 | 166/217 | .764977 | .484 |

현재 snapshot occupancy 비율을 route split으로 사용하면 정체한 분기를 과대 추정하므로 사용하면 안 된다. 최소 구현은 모든 분기의 실제 동일-window 통과수와 표본시간을 읽어 `observed_window_estimate`로 설치하고 provenance를 남기는 것이다. 0표본일 때 .5 등 임의값 대신 마지막 유효 관측+age 또는 명시된 정적 경로 원천을 사용한다. 초기값 원천이 없다면 초기 구간을 관측하는 절차가 필요하다.

## 7. Ω 목적함수 연결의 남은 범위

최종 물리 ledger는 inside 635/outside 601, unresolved 0이며 NC 900초 원시 Ω 재차는 1763이다. 정확한 main 설치 순서로 만든 모델 stock 607개를 원시 support로 감사하면 no_support256 / inside206 / mixed50 / outside95이다. **no_support256개는 모두 현재 0대**다. 양의 inside stock1380.522384, mixed664.416667, outside576.75대이다. 위 branch 수정 전 수치이며 broad mixed support의 모든 현재 차량이 혼합이라고 해석하면 안 된다.

큰 혼합 재고는 in_SC1001_W99, SC1004_W_out55, SC1001_W_out44, in_SC1004_S42, SC104_to_SC6 41 등이다. storage 명칭/소유 player만으로 Ω boolean을 정하면 잘못된다. 이번 branch provenance는 선정한 10링크에는 정확한 inside/outside 초기 stock을 준다. 나머지 일반 urban projection도 현재 실제 `assigned` 발생 지점(adapter5954~5958 및 movement attribution)에 `physical_link → model_stock → assigned_veh`를 기록해야 한다.

미래 Ω stock은 이 초기 물리 provenance를 가진 병렬 cohort로 추적할 수 있다. 다만 혼합 저장고의 총방류를 내부/외부 cohort에 비례 배정하면 **혼합 완전교반 모델 근사**다. 현재 위치의 정확한 측정과 미래 routing 근사를 구분하여 표기해야 한다. 개별 physical branch별 queue를 만들거나 실측 회전분율로 세분화하면 그 근사를 줄일 수 있다.

TTD는 actual accepted crossing을 event로 쌓아야 한다. `urban_queue_model.py:1230~1245`의 실제 이동, global off-ramp dispatch의 direct/signal accepted, freeway terminal exit가 연결 지점이다. 내부 FW↔urban은 0, 서행 external direct target으로 나갈 때 1회, 그 외부 tail의 후속 자연 소멸은 추가 TTD 0이다. 일반 PN 경계 신호는 physical turn connector 매핑을 사용해야 하며 `kind=boundary_out`만으로 판정하면 안 된다.

`control_area_objective.py`는 이 계약의 독립 ledger와 `J=TTT_veh_h−beta_hours*TTD_veh`를 구현했고 20 tests를 통과했다. beta는 필수 인자이며 임의 기본값은 없다. 기존 최적화기에는 아직 연결하지 않았다. 연결할 때 near 비용은 Ω cohort residence, far 비용은 동일 Ω 안의 잔여 재고에만 적용하고, TTD는 terminal stock subtraction으로 대체하지 않는다. 음의 exit reward가 있는 경우 기존 partial-TTT pruning은 안전하지 않으므로 미래 최대 exit reward의 유효 하한을 사용하거나 해당 pruning을 끈다.

실제 런 평가에서는 `scripts/measure_control_area.py`가 final635 ledger와 FZP를 사용한다. 샘플 간 직접 관측 exit, terminal 추정 exit, 설명되지 않는 내부 소실을 분리한다. 이 측정도 샘플 사이의 짧은 excursion을 완전 관측했다고 주장하지 않는다.

## 8. 후속 구현: 초기 cohort 해결, 실제 near objective의 필요한 연결

`diagnostics/physical_stock_provenance.patch`를 추가했다. 관측 patch 뒤에 적용한다. 실제 배정된 양을 clipping **후** 기록하는 공통 함수 `observation_projection.record_projection_assignment`를 storage, movement queue, origin-bound movement queue, ramp queue의 네 mutation 지점에서 호출한다. 전체 저장고·큐·ramp의 재고와 provenance 합이 일치해야 한다. 기본 flag OFF에서는 metadata도 추가하지 않는다.

`control_area_objective.projection_stock_cohorts`가 이 provenance를 final635 ledger와 조인한다. 이제 양의 urban/ramp 모델 재고 전부에 실제 inside/outside 초기 분해를 줄 수 있다. 무게는 기존 projection이 배정한 실재 값이며, 지도 링크 개수나 저장고 이름으로 추정하지 않는다. 9개 관측 tests 안에서 NC900+저장된 전체 n7 상태의 **각 재고마다** inside+outside=모델 재고를 확인했다. flag OFF는 git6056c94에서 함수 자체를 고정 추출한 summary 전체 dict와 비교한다.

NC900의 실제 혼합 재고는 다음 다섯 개다. 원시 support 역변환에서는 두 SC5 movement도 혼합으로 보였지만 실제 배정 provenance에서는 그렇지 않았다.

| 저장고 | inside veh | outside veh |
|---|---:|---:|
| in_SC1001_W | 92 | 1 |
| SC2004_to_SC1002 | .5 | 14.5 |
| in_SC2001_W | 6 | 6 |
| SC107_to_SC1 | 17 | 11.5 |
| SC107_to_SC108 | 12.5 | 2 |

이 단계의 getter로 계산한 초기 Ω는1818.689051대였지만 후속 감사에서 getter가 없는 state.freeway_lanes를 읽고 전부4차로로 대체한 오류를 발견했다. METANET 보존식의 effective_lanes와 scalar segment length로 계산한 FW는841.015565대(물리841대)다. 여기에 도시 누락50대를 실제 physical records/공용road69 저장고로 복구한 현재 NC900 Ω는1763.015565대(물리1763대)다. 차이0.015565는 W/E chain length를 공통 scalar 길이로 표현하는 반올림 차이다. 초기 혼합 cohort 표는 유효하며, 이전 `corrected_area_support.json`의 총량은 getter 수정 이전 결과로 구분해야 한다.

near horizon의 단일 핵심 hook은 `rollout_endpoint.evaluate_price_point`가 적합하다. 모든 leader/가격 rollout이 이 endpoint를 통과한다. 기존 함수를 복제하지 않고 wrapper가 후보별 context ledger를 열고 원 endpoint를 호출한 뒤, 수집한 Ω residence/실제 crossing으로 near score를 대체한다. alias 재설치와 worker 설치도 동일한 runtime_setup에서 수행한다. 이 wrapper만으로는 손실된 flow 정보가 되살아나지 않으므로 아래 지점에서 동일한 작은 `emit_transfer` API를 호출해야 한다.

| 실제 mutation 지점 | 내보낼 event | Ω 처리 |
|---|---|---|
| urban_queue_model1021, arrived storage→movement 분배 | storage→movement, actual release | 동일 물리영역이면0; mixed storage의 경계 통과 시점은 physical path로 정의 필요 |
| urban_queue_model1100대 gate/ramp transit 예약·도착 | external/internal input→transit→queue | 입력 물리링크의 inside/ outside 확인; PN 내부 생성과 외부 진입 구분 |
| urban_queue_model1185 | movement→ramp actual | 두 위치가Ω이면TTD0 |
| urban_queue_model599 off-ramp drain | OR storage→receiving actual | 확인된 internal transfer0; 물리 turn 경계가 있으면그때만횡단 |
| urban_queue_model1245 | movement→receiving actual | canonical physical turn의 inside→outside만TTD |
| adapter leg-ramp runtime intended/accepted/free | W_out→ramp / W_tail / external | W_out→FW내부0; W_out→외부tail에서1회, 외부tail자연출구0 |
| adapter off-ramp schedule accepted | FW→OR / direct target | OR내부0, 동행직행내부0, 서행외부직행은accepted만TTD |
| metanet terminal_out/mainline_exit_acc | FW→외부 actual rate×T_f_h | 진짜Ω 종단에서만TTD; off-ramp flow와 합치지 않음 |

도시 substep마다 도시/ramp/cohort stock residence를 T_u_h로, freeway substep마다 freeway stock residence를 T_f_h로 적분한다. `arrival_buffer`, `release_buffer`, `offramp_transit_buffer`는 이미 잡힌 저장고 차량의 예약이므로 재고에 다시 더하지 않는다. `urban_inflow_transit_buffer`는 독립 재고이므로 Ω 안의 부분만 residence에 포함한다. 현재 no_support254개는 초기0이지만, 예측 중 만들어질 mainline origin queue와 inflow transit에 대한 물리 위치 선언이 반드시 필요하다.

단순 source-stock inside 비율로 방류를 나누는 것은 혼합 모델의 가정이다. 초기 cohort가 정확하다는 이유로 미래 흐름도 실측 정확도라고 표기하면 안 된다. canonical PN turn306개를 merge 이후 movement에 연결하고, 실측 beta/실제 물리 경로를 사용한 전이표를 준비해야 한다. 그 조인이 불명확한 양의 flow는 diagnostic coverage에 드러내며 terminal stock 차감으로 메우지 않는다.

β 후보는 **0,60,150,300초/완료차량**이다. 동일 후보 rollout에서 `Jβ = TTT_veh_h − (β_sec/3600)*TTD_veh`를 각각 산출한다. 150초이면 완료1대의 보상은1/24 veh·h다. 기본 생산 β를 임의로 택하지 않는다. 후보별 `(TTT,TTD)`가 확보되면 4열 점수를 비교할 수 있으므로 같은 후보를 β마다 다시 simulation할 필요는 없다.

`rollout_endpoint.py:308`의 기존 partial-TTT>incumbent pruning은 β>0이면 무효다. endpoint wrapper는 해당 spec의 abort threshold를 없애거나, `ControlAreaObjective.lower_bound`에 증명된 잔여 최대 exit 수를 넣어야 한다. 이 lower bound와 음의 reward 반례는 기존 tests에서 검증됐다. 이 단계에서 near score를 교체하더라도 기존 far가 전역 재고를 쓰면 전체 목적함수는 Ω가 아니므로, Ω far를 연결하기 전의 β 민감도 실험에서는 far OFF를 명시하고 결과를 near-only로 표시해야 한다.

**후속 구현:** 아래9절의 신규 모듈에서 event emission/context/endpoint wrapper가 실제 연결됐다. 전체 망의 남은 물리 경로 오류는 strict coverage 검사로 중단되며, coverage가 틀린 상태를 Ω 최적화 결과라고 보고하지 않는다.

## 9. 실제 배선 및 초기 재고 복제 오류 수정 (2026-09-10)

`area_runtime.py`는 기존 `evaluate_price_point`를 한 번 감싼다. 후보의 native deepcopy로 ledger를 분리하고, 현재 평가 구간의 누적값을0으로 초기화한 뒤 원 endpoint를 호출한다. 전이 이벤트를 누산한 `TTT−βTD`로 near TTT를 한 번 대체하고 기존 penalty는 보존한다. β는 explicit seconds 필수이며 far와 기존 partial-TTT pruning은 이 모드에서 꺼진다. 원 endpoint의 후보 생성·action 적용·롤아웃 순서를 복제하지 않는다.

`urban_flow_accounting.py`는 vendor 도시 substep/OR drain과 adapter legsplit의 method 단위 추출본이다. 수용된 양을 계산하는 지점에서만 `emit_transfer`를 호출한다. FW→OR/direct event는 landing scheduler가, mainline 실제 유입/terminal/미터 합류는 `area_freeway_accounting.py`가 소유한다. FW residence는 off scheduler 뒤에 적분한다. runtime AST/exec나 dict mutation interception을 사용하지 않는다. `build_urban_flow_accounting.py`는 이 생산 모듈을 만드는 별도 일회성 진단 도구다.

가장 큰 추가 결함은 초기 arrival seed와 release seed의 불일치였다. NC900에서 내부 arrival예약1094대와 대응 storage release예약0대가 존재했다. 예약 만기에 movement queue에는 차량이 추가되지만 원래 storage도 그대로 남았다. 합성20대는 기존40대로 증가했고, 같은 만기의 release예약을 붙이면20대로 보존됐다. 전용 OR 저장고20대도 별도 OR drain과 generic arrival seed를 함께 타므로 후자를 제거했다. 누락connector18대 복구 후 일반 초기 pairing은1112대다.

이 물리 수정은 목적함수와 독립인 `urban.conservative_initial_transit: true`로 켠다. shared runtime은 state 투영 직후 딱 한 번 적용하며, 후보가 만든 미래 예약은 재초기화하지 않는다. area objective는 이 초기화가 완료됐는지만 검사한다. 미래의 정상 movement→storage 유입은 vendor가 arrival/release를 함께 예약하므로 별도 복제 결함이 없었고, 실제 관측 수요450초 회계로 이를 검증했다.

`projection_support.py`와 `shared_approach.py`를 결합한 NC900은 물리 Ω1763대에 대해 모델1763.015565대로 닫힌다. road69의32대는 native route prior별 도달 시간과 실제 수용 공간을 가진 하나의 shared storage에 들어간다. native1101의 외생 입력은 내부 생성이며 TTD가 아니다. 물리 목적지를 관측하지 못한 부분에 native route 비율을 쓰는 예측 근사임을 명시한다.

실행 가능한 재현:

```text
python diagnostics/test_urban_flow_accounting.py
python diagnostics/test_area_arrival_routes.py
python diagnostics/probe_area_endpoint.py --structural-only --observed-demand --depth 3
python diagnostics/probe_area_endpoint.py evaluation/runs/codex_n7_s13_6056c94_20260909/decisions_codex_n7_s13_6056c94_20260909/state_003300.json --structural-only --observed-demand --depth 3
```

NC900은28984 events, n7t3300은32833 events에서 모든 model storage/movement/ramp/transit/FW closing stock이 ledger와 일치했다. 대응 JSON은 `area_endpoint_000900_d3_structure.json`, `area_endpoint_003300_d3_structure.json`이다. structural-only는 미해결 경로의 cohort를 진단용으로만 유지해 뒤의 보존 문제까지 드러내는 모드이므로 TTT/TTD/β 점수를 출력하지 않는다.

SC1_S 등52개 alias는 native 입구/관측원점에서 첫 model stopline까지 이동한 후 검증된 동일 물리 회전을 사용하도록 연결했다. 예1220042300→10595→100→10598→1210006903→10590/10591→1220006903에서 외부→PN 입장은 arrival에, SC1 실제 회전은 그 뒤 movement event에 해당한다. 다른 model 교차로를 건너거나 freeway를 돌아 반대 접근으로 도는 경로는 허용하지 않는다. SC10 같은 명시적으로 비모형화된 midblock 통과 시간은 기존 lumped delay 근사에 남는다.

450초 검사에서 추가로 드러난14개 movement/3개 arrival는 아래10절의 미적용 proposal로 해소했다. SC2001의78→31 진입은350.718m이며79복귀 분기281.156m를 이미 지나므로79복귀는 실제 가능한 경로가 아니다. 단순 그래프 도달성과 진행 위치를 구분해야 한다.

strict 명령(`--structural-only` 제외)은 첫 미해결 positive event에서 멈춘다. 회계 검증과 미래 예측 정확도 검증은 다르며, 이 수정들은 production에 적용되거나 holdout 검증된 상태가 아니다.

## 10. 위치 감사, 원점별 오프라인 prior와 strict endpoint (2026-09-10)

`dynamic_area_runtime.patch`는 신규 `area_dynamic_routes`와 shared runtime/area configure 두 hook의 미적용 패치다. `dynamic_area_routes_ver2.json`은 실제 SC1004 N/W/offE/offW→56→10621 경로 네 개를 정본 INPX hash, native route edge, connector 진입·진출 위치, 실제 model receiver까지 검증한다. 경로의 존재 증거와 분기 비율의 근거는 분리했다.

SC1004 E→E와 SC107 W→W의 네 선언은 해당 정지선의 실제 진출 커넥터 세 개 중 어느 것에도 해당하지 않는 U-turn이다. 새 config `urban.movements.dynamic_physical_route_topology`는 이 네 선언을 제거하고 원래 물리 관측을 다시 투영한다. 이미 투영한 queue를 임의 분배하거나 버리지 않는다. physical379는 `SC107_to_SC108`, `in_SC107_S`, `in_SC108_W` 세 alias로 나뉘던 것을 실제 SC107 남측 입력 하나로 정정한다. NC900의379 관측3대는 모두 유지되며 잘못 SC108에 도착하던1대가 사라진다.

SC107의 native decision1061은387의2.341022m에 있지만 SC1005측10499는2.603441m, SC1004측10621은3.603864m에 진입한다. 두 원점 모두 이 decision을 이미 지나므로117:1026:57을 적용되는 정적 경로 비율이라고 쓸 수 없다. `dynamic_area_nc13_calibration.json`은 별도 NC seed13 과거 FZP에서 같은 차량의 원점과 실제 출구를 연결한 **동결 오프라인 예측 prior**다. runtime은 FZP를 읽지 않는다.

| 원점 | 완료 표본 | 좌/직/우 관측 | 미완료·관측 소실 |
|---|---:|---|---:|
| SC1005→SC1004 |856|57/719/80|17|
| SC107→SC1004 |586|54/493/39|7|
| SC1005→SC107 |790|0/403/387|106|
| SC1004→SC107 |729|0/683/46|46|

분모, Wilson 구간, 검열만으로 가능한 분율 범위를 함께 저장했다. 표본0은 물리 불가능이라는 뜻이 아니며 임의 pseudocount로 채우지 않는다. 이 seed13 결과는 보정 집합의 탐색 결과이며 seed14 holdout이 필요하다. 특히 SC107 원점별 차이와 미완료 비율을 무시한 하나의 평균 prior는 적합성 근거가 없다.

SC2001 proposal은78의 공유 유한 저장고와 원점별 후보 전용 travel bins를 사용한다. 이미 실제 수용된 movement→78 흐름만 예약하고, 이후 수용 가능한 R_D_E/R_D_W/외부125로 각각 한 번 이동한다. generic sink와 중복 arrival/release 예약을 제외한다. 원점별 offline NC13 prior를 쓰며, 원점이 관측되지 않는 초기78은 명시된 pooled prior다.31/124의 기존 재고를 임의 원점별 분할하거나 별도 용량으로 복제하지 않는다.78에 이동 재고를 오래 보유하는 보수적 공간 집약 때문에 실제보다 spillback이 빨라질 수 있다.

`probe_sc2001_corridor_replay.py`는 미적용 canonical urban patch를 **진단 프로세스 안에서만** 적용한다. NC900과 n7t3300의150/450초 observed-demand 평가에서 양수 미해결 경로 없이 Ω event/model 재고가 닫힌다. `test_dynamic_area_routes.py`의7개 검증은 원점 보존, native 위치, 표본 계수, 없는 flag의 항등 동작을 포함한다.

`probe_all_area_snapshots.py`는 pure n7의900..5400을 각각 독립 프로세스로 최대45초 제한한다.450초 동안 이전 control 및 green/meter/VSL/offset 후보 다섯 개를 실제 price endpoint에서β0/60/150/300으로 평가하고, 계수가 바뀌어도 물리 rollout이 변하지 않는지, 후보끼리 상태가 섞이지 않는지, 다시 평가한 기준 후보가 같은 점수인지 검사한다. 이 경우 고정 레버의 영향을 구분하려고 `box_walk=False`를 명시한다. far ON/abort0 입력도 Ω wrapper가 올바르게 제거하는지 검사한다. 결과는 `area_all_pure_n7_snapshots.json`에 저장한다. SG offset 부호/죽은 현시 clearance의 별도 actuation timing 문제를 해결했다는 검증은 아니다.

초기 실측 coverage는 `probe_all_area_initial.py`로 별도 검사한다. 첫 전수 감사에서 pure의6개 짧은 connector(10224,10554,10774,10273,10579,10294)가8시점에 각1대 누락되어 data 보강 대상으로 전달됐다. 최종 `physical_projection_support_635_proposal.json`은 해당 여섯 개를 포함한170개 support를 실제 유일한 downstream storage로 추가했으며, 모호한45개는 양수 관측 시 strict error로 남겼다. 이 자료를 쓴31시점 도시 물리배정 누락은0이다. 별도 작은 `freeway_initial_count.patch`는 `physical_vehicle_counts` ON에만 각 cell의 관측N을 실제 continuity scalarL×effective lanes로 투영하고 두 getter도 그 좌표를 쓴다. 물리 길이 프로파일은 speed/travel 용도로 유지하며 합계 상수 보정은 없다. 전체31시점 rawΩ=modelΩ 오차0.0, FW 셀별 최대오차2.84e−14대로 확인됐다. `freeway_initial_count_handoff.md`에 정확한 적용 순서와 추가 flag, 검증 명령을 기록했다.

635 support를 적용한651개450초 endpoint 검사는 전부 통과했다(`area_all_pure_n7_snapshots_physical635.json`). 추가 FW exactN까지 적용한 동일 검사는 `area_all_pure_n7_snapshots_physical635_exactN.json`의 `complete` 필드로 완료를 확인한다. 모델 회계가 닫혀도 속도 예측 정확도가 입증되는 것은 아니다. 같은 actual action으로150초 뒤E8을 비교하면 t1200의 속도는96.41→95.90km/h, 실제23.27이고, t3300은23.36→23.26, 실제6.27이다. 물리 재고 수정만으로 낙관적 혼잡 회복 오류는 거의 줄지 않는다(`corrected_prediction_fidelity_two_states.json`).
