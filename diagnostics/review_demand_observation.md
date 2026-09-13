# 6056c94 수요·관측·평가영역 독립 감사

검토 기준은 `n21_n7_20260908.json`, Ver2 INPX SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`이다. 이 문서는 생산 코드·config를 수정하지 않고 작성했다. `probe_demand_observation.py`는 실제 어댑터의 수요/관측 함수를 호출하며, 결과는 `demand_observation_probe.json`이다. 실제 관측 점검에는 이번 세션의 `codex_nc_s13_6056c94_20260909_retry` t=900 상태를 사용했다. 합성 probe와 VISSIM 실측은 구별한다.

핵심 판정은 세 가지다. 수요 배율은 이번 VISSIM COM 되읽기로 정상 적용을 확인했다. 반면 MPC 예보는 알려진 미래 시간표를 쓰지 않는 현재값 지속이며, 스필백 관측은 같은 차량을 도시 저장고와 램프 큐에 두 번 심는 오류가 있다. `off_ramp_storage=0`은 착지 커넥터를 못 관측해서 생긴 것이 아니라 관측→모형 저장고 귀속의 문제다.

## ① 수요

| 의심 | 근거 | 판정 | 최소 조치 |
|---|---|---|---|
| x15의 0.8333이 잘못된 배율인가 | `chain_fdsweep_ver2_20260907.py:8-10,59`는 현재 망 본선 첨두8316을 x18로 정의한다. 8316×0.8333=6929.7228vph이며 도시부는1.0이다. | 설계 의도. x15는 현재값의15배가 아니다. | 명칭에 기준 첨두를 함께 기록. |
| 배수가 첫 구간에만 쓰이는가 | VBS `ApplyDemandMultipliers:3931`, `ScaleInputAllIntervals:3995`는 모든 interval을 쓰고 개별 되읽기를 비교한다. 이번 실런로그에서1098/1099 양쪽6구간 모두 정확히 변했다. | 실재 오류 아님. 과거 버그는 현재 경로에서 수정됐다. | 되읽기 증거 유지. |
| MPC가 참 시간표를 예측하는가 | VBS `LoadInpxDemandSchedule:3588-3704`는 전체 시간표를 읽지만 `WriteStateJson:2349,2370`은 현재 시점 값만 보낸다. 어댑터 `demand_from_state:9161-9183`는 단일 `DemandStep` 객체를 horizon 전체에 반복한다. 실제 호출로2000vph가3스텝 전부2000이며 객체도 동일함을 확인했다. | 현재값 지속이라는 설계 제한. `demand_profile_forecast_profile_aware=1` 메타(`12385`)는 미래 시간표 인지로 읽으면 잘못이다. | VBS가 horizon 시간표를 보내고 어댑터가 각 스텝의 interval을 선택하도록 계약을 같이 바꾼다. 외생 시간표와 관측 기반 램프 도착은 분리해서 명시한다. |
| 램프 유입 경로가 없다 | VBS의 `ramp_volume_vph=0`만 보면 그렇지만 n7의 `calibration_override.prediction.local_ramp_arrival_forecast.enabled=true`. 어댑터 `9092-9151`은 관측 점유×3600/drain으로 램프별 도착을 추정한다. n7 B5는 도시부 substep에서 같은 램프의 외생항을0으로 바꾸고(`2965-2975`), 게이트 β×수요 및 W_out 전달(`3023-3066`)을 쓴다. vendor 도시 동역학 `1116-1148`에는 gate와 ramp transit 경로가 있다. | '지금도 유입 경로 없음'은 반박. 단, 점유→유량 휴리스틱의 정확성과 B5 경로별 크기는 별도 검증 필요. | 실제 커넥터 전이 유량, 게이트 수요와 B5 주입량을 같은150초 창에서 대조. 초기 큐와 유입률을 혼동하지 않는다. |
| 도시 내부발생·미배정 유입을 놓치는가 | 어댑터는 `urban_internal_volume_vph`, `urban_unmapped_volume_vph`를 읽지 않는다. t=900 실제 값은2120+1333vph, mapped14756.2vph. INPX 전체 도시량18209.2의18.96%다. 첨두도2226+1400=3626vph를 별도 필드에만 둔다. | 명시적으로 알려진 모델 범위 제한. 다만 B5·잔차 버퍼의 대체 기여가 있으므로 곧바로 '실효 총유입19% 손실'로 단정할 수 없다. | 입력ID→물리 발원지→모델 reservoir의 독립 장부로 대조. 내부발생은 미래 외생항으로, 공용69는 방향/분기별로 다루어 중복을 막는다. |
| `in_*` 저장고가 고정되는가 | config39개가 모두 movement origin이고 receiver는0개. n7 `urban.boundary` 없음. `seed_boundary_inflow:5372`는 기본 no-op이며 자체 문서(`5354-5370`)도 죽은 저장고 문제를 설명한다. 실제 gate 수요는 vendor `1102-1120`의 inflow transit→movement 경로로 움직인다. | 실재 상태 표현 오류. 새 수요가 없다는 뜻은 아니며 **초기 관측 재고**가 죽은 통에 남는 문제다. | 기존 시더를 별도 ablation으로 켜되 관측 정지큐와의 이중계상을 검증. 상수 재고 제거만으로 far 분기/기울기도 바뀔 수 있다. |

이번 COM 배율 되읽기 결과(방향별 vph):

| 시작[s] | INPX 원본 | 설정·되읽기 | 상태/모델 현재 예보 |
|---:|---:|---:|---:|
|0|5544|4619.8152|현재 구간 값|
|900|7920|6599.7360|실제 t900 상태6599.7360|
|1800|8316|6929.7228|현재 구간 값|
|2700|7128|5939.7624|현재 구간 값|
|3600|5544|4619.8152|현재 구간 값|
|4500|3960|3299.8680|현재 구간 값|

양방향 값이 이 망에서는 같아 `freeway_volume_vph`를 두 링크에 복제해도 현재 총량/방향은 맞는다. 비대칭 수요라면 이 평균 스칼라 계약이 방향 차이를 잃는다. COM에서 요청 수요가 맞았다는 것은 **실제로 모든 차량이 네트워크에 진입했다는 뜻은 아니다**. 입구 대기/삽입불가 차량을 실제 차량ID 유입과 따로 확인해야 한다.

## ② 관측·매핑

| 의심 | 근거 | 판정 | 최소 조치 |
|---|---|---|---|
| off-ramp 착지 커넥터를 전혀 관측하지 못한다 |10481/10483/10682/10643 모두 detector agent의 visible_links와 VBS `RW_LOCAL_OBSERVABLE_LINKS`에 있다. 이번 t900 raw count는5/3/9/4대.121·124도 각각12대. 다만 far flow CSV에는 네 커넥터가 없다. | 광범위한 '센서 결측' 주장은 반박. **별도 유량 채널 부재 및 저장고 귀속 불일치**가 실제 문제. | raw count와 projected reservoir를 같은 물리 범위로 조인. 유량 진단용 landing ledger는 독립 그룹으로 추가; far 배수합에 무조건 더하면 내부이동 중복. |
| off-ramp 모델 저장고가 초기화0인가 |10481/10643의 origin은 in_SC1001_W/in_SC1004_W,10483/10682는 SC1001_W_out/SC1004_W_out. 별도 OR_*_storage로 관측 재고를 심지 않는다. `_apply_landing_storage:3268`는 config 사양 없으면 no-op이며 n7은 꺼져 있다. | 실재 투영/모델 공간 불일치. h1처럼 다른 넓은 접근로 전체를 OR storage에 복제하면 해결되지 않는다. | 한 차량이 한 통에만 배정되는 ledger를 먼저 만들고 분기와 물리길이에 맞는 저장고를 정의. |
| 과거 39/39 zero 채널 통계가 현재도 유효한가 | 해당 통계는8월20일 calibration 문서의 이전 데이터다. 현재 `traffic_state_from_vissim:9483-9488`는 램프 관측을 실제 ramp_queue에 심으며 이번 t900 값은26대다. `boundary_queue`는 `6103`의 주석처럼 legacy 호환이고 movement 모델의 정지큐와 다른 항이다. | 과거 통계를 현재 실런의 전수조사로 인용할 수 없다. | 최신 n7 상태/예측쌍으로 각각 존재/유효/0/NaN 및 물리 의미를 분리 집계. 이번 NC는 t1,t900 두 상태라39표본 검증을 주장하지 않는다. |
| 모니터9개 신호는 관측이0인가 | detector의 movement259개는 모두 제어17개 소속이고9개 monitor movement mapping은0. 그러나 link counts→urban storage는 monitor에도 적용된다(`5841-5966`). native 신호에 따른 방류 모델도 별도 패치다. | movement 센서0은 맞지만 **전체 상태 미관측**은 아니다. 신호레버가 없는 영역을 objective에 넣는 의미는 사용자 Ω 정의와 대조해야 한다. | 본 검토의 물리 PN ledger로 평가를 제한. 신호 소유권17개를 PN 내부라고 대체하지 않는다. |
| 차로 정보가 전혀 소비되지 않는가 | freeway projection `9447-9473`은 셀 단위 집계만쓴다. 그러나 n7 스필백 관측은 `6091-6096`에서 vehicle_records.lane_no/stopped/position_m를 실제로 읽는다. | freeway 단일차로 병목 모델링 한계는 맞다. '어디에서도 차로 안 읽음'은 반박. | FW_E5-10 차로별 속도·재차·전이량을 진단하고 partial-FIFO/경로별 저장고 필요성을 검증. |
| 스필백을 ramp_queue에 더해도 보존되는가 | `6071-6101`은 도시 링크 정지차를 ramp_queue에 더하면서 도시 저장고/큐에서 차감하지 않는다. 실제 n7 함수에 link32의20정지차를 입력한 probe는 도시20+램프20=40대로 출력. 끄면도시20+램프0=20. 기존 `projection_diagnostics.mass_balance_error_veh`는 두 경우 모두0. | **실재 오류, P1.** 동일 물리차량 복제와 그것을 못 잡는 검증장부 오류. t900 실런에서는 해당 정지차가0이어서 추가분도0; 혼잡 후 영향은 후속 상태로 측정해야 한다. | spillback을 별도 신호로 유지하고 실제 램프 저장고와 합치지 않거나, 차량ID 단위 단일 귀속으로 이동시킨다. 관측표현 합계와 raw 차량수를 직접 대조하는 테스트가 필요. |

스필백 대장에는 `upstream_links`가 들어있지만 이 관측 루프는 각 entry의 `link`만 읽는다. 상류 목록을 자동으로 포함하지 않는다. `conn_pos_m`도 이 대장에는 없어서 위치 제한은 -1 폴백이다. 따라서 '1km 스필백을 전부 감지한다'는 주장 역시 실제 커버리지 확인이 필요하다. 차로정보만으로 차량이 어느 램프를 선택했는지는 확정할 수 없어, 점유를 실제 ramp reservoir로 이관하는 수정에는 경로/분기별 중복 검증이 필요하다.

## 사용자 정의 Ω = 보호 도시부 PN ∪ 제어 freeway

사용자 최신 정의는 Ω 안 차량시간 TTT와 Ω→비제어 영역으로 나간 차량수 TTD다. VISSIM 전체에서 사라져야만 TTD가 되는 것은 아니다. urban↔freeway 이동은 내부 이동이다.

**신호 제어 소유권과 PN은 다르다.** 기존 `protected_ttt_from_fzp_20260828.py:35-62`는17SC 소유 링크를 protected라고 부르지만, canonical `pn_boundary_turns_v2_20260907.json.leg_zone`은 내부/경계면을 구분한다. `derive_pn_boundary_turns.py:226-228`의 경계면 우선을 그대로 적용하면 PN 내부583링크, 경계면136링크다. FW19를 합친 기본 Ω는602이다. 예전 소유권 합집합738을 PN으로 사용할 수 없다.

이를 반영해 `diagnostics/control_area_membership.json`을 만들었다. 재현 생성기는 `build_control_area_membership.py`이며, 기존 소유권 파일에는 손대지 않는다.

- canonical PN turn의 inflow/outflow connector 편을 적용해 정지선 횡단 위치를 반영한다.
- FW↔도시 연결을 끊는 IC 접근 도로31/68/69/121/124/32/129/127/70/126/71을 물리 평가영역에 포함한다. 같은 도로의 비제어 목적지 차량도 공유구간을 떠날 때까지 한 번 센다. 기존 소유권을 새로 배정하는 것은 아니다.
- canonical internal 회전10528의 무소유 짧은 도로336→10529→1210014303도 내부 연결로 포함한다. canonical 하류첫소유자 규칙(최대6hop, known외부/경계leg에서중단)으로 전수 확인해259→10411→1220011003 연결의2개element도 추가한다. 그 밖의 비제어 도시를 따라가서 영역을 넓히지 않는다.
- 양쪽 도로가 이미 inside인 직접 connector24개를 포함한다. 결과 inside635/outside601개이며, old ownedSC union은 비교용 필드로만 남긴다.
- 8개 on-ramp는 모두 내부. off-ramp8개 중6개는 내부이며10479→125,10645→123 두 갈래는 외부 sink 방향이다. shared121의10773→123, shared124의10775→125는 외부 branch다.
- 자연적인 VISSIM 전체 이탈 말단은 actual Ver2 mapping의 FW_E24, FW_W120이다. **FW_W26은 이제 체인 중간**이다.

`connector_transitions`는 from/connector/to별 inside 판정과 실제 outward/inward edge를 모두 기록한다. 처음부터 inside 링크635개를 차량ID에 대해 합집합으로 검사하면 이중계상이 없다. 현재 far 도시유량 CSV는44회전 중3개(10482·10490·10639)를 명백한 내부 urban→FW 이동인데도 포함하므로 TTD로 재사용하지 않는다. 나머지에도31/68 이후 램프로 복귀하는 흐름이 있어 endpoint만 한 번 보는 식의 제외도 부족하다.

이 물리 ledger는 모델 reservoir의 binary mask를 자동 보장하지 않는다. 한 저장고가 PN 내부/경계 접근부/외부 sink를 함께 담으면 이름으로 판정하거나 임의 비율을 곱하면 안 된다. `control_area_objective` 작업은 물리 ledger→detector support→모델 공간을 검증하고 mixed/unknown을 명시해야 한다.

실제 Ω 경계에는 connector130개(outward92/inward38)가 있다. canonical PN 회전표에 없는 outward60개를 추가 조사했다. 대다수는470·468·20·22·140·142 등 **실제로 하류 connector가 없는 외부 말단도로**로 나가는 갈래다. 따라서 모델 경계회전34개만 합쳐서는 물리 TTD를 포괄하지 못한다. 이들을 모두 '무소유니까 내부'로 채우는 것 역시 잘못이다. 생성기는 안으로 복귀하는 짧은 경로만 추가하고 그런 외부 말단은 그대로 제외한다.

## 매 런에서 사용할 수 있는 진단 자료

VBS native output은 기본 켜짐(`4193-4205`): 전차량 FZP,5초 sampling, 신호 변경기록. 이번 실제 FZP header는 `SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM`이다. 표본시각은1,6,…로, 시작0/끝5400과 동일하지 않다. 프로파일/차로별 혼잡 시계열, 미터/다이버지 connector 전이량, SG 상태 이력과 action 시각을 함께 대조할 수 있다. 각 결정 state에는 전차량ID/link/lane/position/speed/stopped가 있다(`2450-2480`).

5초 사이 짧은 밖→안 재진입, 누락된 짧은 connector, 마지막 표본 이후 종료는 정확한 출구 횟수에서 구분해야 한다. 내부 링크에서 사라진 차량을 모두 완료차량이라고 처리하면 lane-change removal 등도 섞인다. 검증된 terminal/전이 경로로 설명하지 못하는 것은 unknown removal로 보고, 마지막 표본 차량은 종료로 인한 censor로 남겨야 한다. 부모 작업이 Ω TTT·TTD와 혼잡 발생시각/전파/차로별 병목/실제 레버 이력을 함께 산출한다.

## 이번 범위에서 완료한 검증

1. INPX 배율을6구간 재계산하고 실제 COM 되읽기·t900 state와 일치 확인.
2. 실제 어댑터 함수로 horizon persistence 확인.
3. n7 config/매핑으로 spillback 단일차량집합 중복을 재현하고 strict stock assertion을 통과(기존 모델이 보존을 위반한다는 재현 테스트).
4. 최신 실제 t900에서 raw landing count·ramp26·detector mapping 경로 확인. 이 시점의 스필백 추가량은0이며, 혼잡 후 효과를 미리 주장하지 않음.
5. Ω ledger의 INPX hash, 모든 corridor connector의 양끝, 모든8on/8off mapping,25개 이상의 내부·유입 경로의 출구재진입 부재, 자연말단24/120을 기하적으로 검증.

수요·관측 축만으로 지배적 손실을 확정할 수는 없다. 다만 배율 전달 실패는 이번 실행에서 배제되고, 초기 재고의 비보존/잘못된 통 배정과 실제 분기 형태를 표현하지 못하는 모델이 우선 수정 대상이다. 미터·VSL 가격을 조정하기 전에 이 상태·경계 장부를 맞춰야 후보의 상대 성능을 믿을 수 있다.

