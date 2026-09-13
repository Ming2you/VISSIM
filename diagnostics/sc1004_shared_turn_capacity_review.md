# SC1004 east destination aliases의 공유 service 근거

Actual retry1200 cfg/1050 previous action을 구성해 기존 capacity를 확인했다. 두 east destination alias의 용량을 더할 물리 근거는 없다. **하나의 first connector를 통과한 뒤56의 native1129 route choice가 갈라지는 구조**와 model destination alias를 구분해야 한다. 다만 이 자료는 새로운 capacity의 실측 식별이 아니다.

| 출발군 | 기존 두 alias capacity (veh/h) | native 첫 서비스 증거 | 판정 |
|---|---|---|---|
|N_SC1003|206.530612 /206.530612|46→10627→56,1 connector lane, source46 lane4, SG7 head953.190746m < branch957.068834m|하나의1차로 서비스. 두 alias를 합쳐413.061224로 만드는 근거 없음. 기존1차로 기준을 보존하려면 명시한 single source206.530612를 참조.|
|S|206.530612 /206.530612|66→10632→56,1lane, branch2630.062020m < 같은 lane SG8 head2658.841933m|하나의 우회 분기. 기존206.530612는 보존 가능한 모델 scalar지만 signal-green discharge capacity로 검증된 값이 아님.|
|W|619.591837 /413.061224|71→10634→56,3lane, source71 lanes1–3, SG2 heads78.874–78.980m < branch81.238116m|하나의3차로 서비스. 합계1032.653061은 이 서비스의 차로수와 불일치. 기존W→SC1005의619.591837는3×206.530612와 일치하지만W→SC107의413.061224는2차로 alias 값.|
|offW|413.061224 /413.061224|현재 exact movement route contract 미해결.70/126에서71로 이어지는 경로와 실제 cohort 분기를 먼저 증명해야 함.|각각 독립2차로 service라고 확정 불가.|
|offE|413.061224 /413.061224|현재 exact movement route contract 미해결.10643→126/10641 관측과 선언 geometry/route의 관계 검증 필요.|각각 독립2차로 service라고 확정 불가.|

206.530612는 현재 모델의 lane-normalized 기준이며 VISSIM에서 이번에 측정한 포화 방출률이 아니다. 정본 adapter의 `configure_movement_capacity_by_lanes`는 `movement_lanes_core17legs4b_20260821.json`의 lane count와 internal normalization을 이용한다(3771–3810행). 실제 서비스 호출은 vendor `urban_queue_model._movement_capacity_flow(control,cfg,movement,spec)`이며, configured physical ceiling과 perimeter allocation을 구분한다(730–768행). 공유 자원 생성시 서로 다른 destination allocation ceiling을 capacity와 합치지 않아야 한다.

Native에서56으로 진입하는 connector는10627(N1lane),10632(S1lane),10634(W3lane),10701(75에서56@249.407m로 진입하는2lane)의 네 개다. offE/offW cohort가71→10634로 이어짐을 증명한다면 **W와 동일한3차로 자원**을 소비한다. `W619.59 + offE413.06 + offW413.06`이라는 독립 예산 합도 근거가 없다.75→10701은 다른 하류 진입점이므로 이름에east가 있다는 이유로 합치지 않는다.

안전한 인터페이스는 `physical_service_key`(예: connector10634), `capacity_source`(명시한 기존 cfg key와 native lane 근거), `green_authority`(SG2 또는 signal bypass), `contributing_cohorts`, `accepted_vehicle_budget`이다. 하나의 물리 예산을 한 번 소모하고 그 뒤 route choice에 따라 target cohort로 나눠야 한다. 기존 값의 max/sum으로 source를 추측하지 않는다. 한 서비스에 실제 합류하는 cohort가 아직 미해결이면 failfast/미해결 표기를 유지한다. 여러 cohort의 배분/FIFO는 별도 모델 선택이며 geometry만으로 정해지지 않는다.

관련 실제 모델 specs/capacity·head/lane/path 증거와 입력 SHA는 `movement_signal_authority_audit.json`의 SC1004 movement 항목에 있다. full physical route가 해결되지 않은 N→SC107, W→SC107, offE/offW 계약 상태도 그대로 보존했다. 생산 코드·수치·VISSIM은 변경하지 않았다. 이 자료를 Flow에게 전달했다.

## 10701의 기존 future 유입 출처

추가 actual retry1200 runtime 조회에서10636·75·10701은 모두 `in_SC1005_W`에 투영된다. 이 origin의 기존 두 boundary movement는 `SC1005_W_to_E_SC107`(p3, beta2/3)와 `SC1005_W_to_N_SC105`(p4, beta1/3)다. 기존 `shared_approach_ver2.json`도 native1134 branch2의 target을 `in_SC1005_W`로 둔다. 그러므로 새56 route-choice prefix를 도입할 때 이 기존 유입을 소비해 연결해야 한다. 같은 차량을 새 외생 유입으로 추가하거나 SC1005 phase 서비스를 먼저 거쳐야 prefix로 이동하게 하면 경로 의미가 달라진다.

Native1134 branch2는69→10636→75이며 static route 자체는75@67.103376m에서 끝난다. 그 이후75의 유일한 outgoing connector는10701이다:75 lanes1–2@341.655140m→56 lanes3–4@249.407145m. 이는1129 decision253.172201m의 약3.765m 전이다.69·10636·75·10701·56에는 native signal head가 없고75/56의 vehicle input도 없다(69에는 input1101). 따라서69 branch2 cohort를10701 경유56 prefix로 이어야 한다는 것은 **route 종료 뒤 유일한 물리 continuation** 근거다.10701까지 명시된 하나의 static route가 있다는 주장은 아니다. 새 구현에서는1129 선택의 actual route-tag/계측 증거를 별도로 검증한다.

1134 branch3은69→10637→70→10639→FW_E이며, 기존 shared future branch target도 `R_F_E`다. Detector70/10637의 `in_SC1004_W` alias와 실제 future branch target을 혼동하지 않는다.1134 branch4의10640→71 lane4@3.470218m가 SC1004_W 신호 접근으로 가는 명시 경로다. branch2·3을 모두 SC1004_W signal queue로 보내는 수정은 근거가 없다.
