# 실제 신호두와 현재 urban movement의 녹색 권한 감사

**현재 선택된 신호 제어기에 속하는 261개 movement 중 26개가 선택 SG를 지나지 않는 물리 경로인데도 모델에서는 phase green으로 방출량을 제한한다.** 이들 중 8개 movement key는 실제 retry900/1050/1200/1350 중 적어도 한 snapshot에서 해당 connector에 차량이 있었다. 별도로16개 movement에서는 연결 차로의 실제 SG 집합이 모델 phase의 SG 집합과 다르다. 신호 clock 정합만으로는 이 두 종류의 잘못된 녹색 한계효과를 해결할 수 없다.

실제 β0 retry1200 snapshot과1050 previous action으로 정본 `configure_runtime`을 구성했다. 활성 configured movement는366개이며, 현재 selected mainline SG plan의17개 SC에 속하는 것은261개다. 데이터는 `movement_signal_authority_audit.json`, 모든 우회 경로 표는 `movement_signal_authority_bypass.csv`, 우선순위16개는 `movement_signal_phase_priority.csv`에 있다. 이 숫자는 **movement key 수**이며 독립 물리 차로·신호두 개수가 아니다. 분류는 현재 검증된 물리 route contract의 범위에 한정한다.

| 분류 | 전체366 | 실제 selected writer SC261 |
|---|---:|---:|
| 모든 matching native prefix가 해당 actuator 신호두를 거침 |189|141|
| 해당 actuator 신호두를 우회하는 경로 |45|26|
| 일부 차로/상류 경로 증거가 불완전 |59|27|
| 물리 경로 미해결 |71|65|
| 한 movement에 서로 다른 신호 권한의 branch가 합쳐짐 |2|2|

Writer 대상이 아닌105개 movement는 native 같은-SC head에 대해서만 분류했다. 그48개 head-controlled 판정을 MPC 권한으로 해석하지 않는다. Writer 대상의26개 bypass는 모두 `phase`가 있고 `unsignalized`가 false/absent다. 우회26개 key는24개 first connector를 가리킨다. SC1004 south→SC1005/SC107은10632를 공유하고, SC107 west-from-SC1004/SC1005→south는10616을 공유한다.

판정은 단순 SC 이름이나 source link의 head 유무로 만들지 않았다. Native route의 decision 위치부터 실제 source-lane connector 분기점까지의 ordered prefix와, 선언된 movement continuation을 확인했다. Positive 판정은 모든 matching native route가 실제 같은-SC head로 모든 road lane이 덮이는 구간을 지나야 한다. 일부 차로만 증명되면 ambiguous로 남겼다. Negative 판정도 matching route가 없으면 하지 않는다. Source link의 decision보다 앞에 head가 있으면 보수적으로 남겨, route가 head 뒤에서 시작했다는 이유로 우회라고 판정하지 않았다.

선택된 writer의 실제 `phase_signal_groups`에 없는 SG는 MPC head로 세지 않았다. 특히 SC5의 midblock-native SG10/14/20/24는 SC 번호가 같아도 현재 네 phase green으로 변경하는 SG가 아니다. 모든 native head, source lane/pos, route ID, active conflict record는 JSON에 보존했다. 원본은 `modi_eval_userfix Ver2.inpx`, SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`; 실제 selector가 `signal_group_actuation_plan_mainline_20260825.json`을 반환하는지도 assert했다.

**세 가지 중요한 반례/확정 사례:**

| movement / connector | 실제 근거 | 현재 모델의 의미 |
|---|---|---|
| SC101_S_SC1_to_E_SC5 /10528|native1014:3, source1220011503 lane1의 분기193.004715m, SG8 head209.187548m. 같은 SC101의 상류 prefix head 없음.|p1(SG4/8) 서비스로 gating하나 해당 분기 전에 신호두를 지나지 않는다. 336 초기 stock proof와 별개인 서비스 오류 후보.|
| SC11_E_SC12_to_N_SC5 /10366|직접 source1210012001에서는 branch1.814m가 head9.751m보다 앞이지만, native22:3은 **이전 road1220012001의 SG6 head410.748/410.918m**를 지난다.|p3(SG2/6) 권한 존재. source-only 검사로 전체 movement를 무신호로 처리하면 틀린다.|
| SC5_W_SC101_to_S_SC11 /10426|직접 source에서 branch159.735917m가 SG2 head162.354118m보다 앞. 이전 road1210014303에는 SG10 head가 있으나 midblock-native다.|Native signal 영향은 있지만 현재 MPC p3 권한의 증거는 아니다.|

SC101의 모든 head는1220014201/1220012502/1220011503/1220016001에만 있다. 문의된 상류1220008502/1210008501에는 SC101 head가 없어10528에는10366과 같은 숨은 동일-SC 반례가 없다. 이 정정은 Hubble에게 전달했다. 초기 receiver stock 보존과 signal service 식은 다른 검증 항목이다.

우회26개 중 SC107 north→south 터널10597, SC107 south→east10608, SC101 north→west10504, SC1004 south→east10632처럼 분기/입체 교통이 현재 signal phase로 묶인 경로도 포함한다. 실제 snapshot에서 connector stock이 양수였던8개는10527,10597,10608,10121,10683,10686,10625,10642다. 이는 그 시점의 **재고**이지 통과율이나 capacity가 아니다.10528에서는 connector snapshot stock은0이어도,1350의 downstream336에 차량1대가 있는 별도의 route/stock 증거가 있다.

선택 SG 불일치16개는 모두 현재17SC 제어 대상이다. 아래 우선순위의 교통 수치는 retry900/1050/1200/1350 네 snapshot에서 해당 물리 connector 재고 또는 source-lane stopped<5km/h 최대값이다. Alias가 같은 connector를 쓰면 같은 차량이 두 movement 행에 보일 수 있으며 합산하지 않는다. `queue1200`은 실제 상태를 정본으로 투영한 **모델 movement queue**다.

| 우선 | movement | 모델 phase / 기대 SG | 물리 source SG | connector 최대재고 / source-lane 최대정지 / queue1200 |
|---|---|---|---|---|
|P1|SC1_E_to_S_SC107|p4 /1,5|10566:6|2 /8 /2|
|P1|SC11_N_SC5_to_E_SC12|p2 /3,7|10375:4|0 /2 /2|
|P1|SC11_W_to_N_SC5|p4 /1,5|10372:2|0 /2 /0|
|P1 mixed route|SC1001_E_SC1002_to_N_SC2002|p3 /2,6|10695:5, 별도10122는우회|2 /28 /4.5|
|P1 mixed route|SC1001_E_SC1002_to_S_SC1003|p4 /1,5|10368:2, 별도10696:1|0 /18 /4.5|
|P2|SC1_S_SC107_to_N_SC101|p1 /4,8|10025:3,8|6 /25 /0.667|
|P2|SC5_E_SC6_to_W_SC101|p3 /2,6|10032:1,6|4 /23 /1.25|
|P2|SC107_W_SC1004_to_E_SC108|p3 /2,6|10023:2,5|1 /14 /0|
|P2|SC107_W_SC1005_to_E_SC108|p3 /2,6|10023:2,5|1 /14 /0.510|
|P2|SC1005_W_SC1004_to_E_SC107|p3 /2,6|10624:2,5|1 /1 /0.5|
|P2|SC12_E_SC106_to_W_SC11|p3 /2,6|10238:1,6|0 /5 /1.7|
|P2|SC12_W_SC11_to_E_SC106|p3 /2,6|10241:2,5|0 /5 /1|
|P2|SC7_N_SC11_to_S_SC108|p1 /4,8|10328:4,7|0 /4 /0.833|
|P2|SC7_N_SC11_to_E_SC16|p2 /3,7|10330:4,7|0 /2 /1.167|
|P2|SC11_E_SC12_to_W_SC1|p3 /2,6|10367:1,6|0 /1 /0.6|
|P2|SC1005_W_SC1004_to_N_SC105|p4 /1,5|10623:2,5|0 /1 /0.5|

P1 첫 세 행은 모델 기대 SG와 물리 source SG가 서로 겹치지 않는 단순한 재현 후보다. SC1_E는 connector에서 실제 차량도 확인되어 첫 actual COM/SG-통과 검증 우선순위가 높다. SC1001의 두 행은 먼저 상이한 물리 branch를 분리해야 한다. P2의 혼합 SG는 공유 차로, 다른 upstream/downstream head 또는 여러 현시에 열리는 connector를 포함할 수 있으므로 한 phase로 재라벨링해서 해결됐다고 볼 수 없다. SC107 두 alias도 별개의 물리 자원이 아니다.

이 모든 후보의 모델 서비스는 `urban_flow_accounting.py:66,330,386`에서 `_phase_green_fraction`을 곱하며, opt-in clock은 `signal_actuation_contract.py:185–210`에서 model phase를 선택한다. Local follower cache도 같은 model phase 기준이다(279–285행). 따라서 **정확한 clock으로 잘못된 movement/phase 대응을 계산할 수 있다.** 해당 검증은 scalar green 경계나 offset 부호 회귀와 독립적이다.

우회 판정은 해당 route가 **선택 head를 지나지 않는다는 topology 판정**이며, 그 차량이 자유롭게 항상 흐른다는 뜻이 아니다. SC5 north→west10423에는 active conflict area1992(`TWOYIELDSONE`)가 있고, 나머지에서도 implicit merge/car-following, 다음 링크 공간, native midblock 신호가 작동할 수 있다. Native branch/head 간격이 짧은10683(약0.53m),10423(약1.38m) 같은 사례는 실제 simulator의 정지선 접근 및 전이 관측을 우선 확인해야 한다. 모든26개를 `unsignalized=True`로 바꾸거나 기본 capacity를 쓰는 수정은 하지 않았다.

가장 작은 다음 단계는 P1의 actual SG state/vehicle lane-route crossing을 부모의 한 COM instance에서 확인하고, current movement의 accepted transfer가 **어느 physical service resource**를 통과하는지 명시하는 것이다. 모델 state/receiver/Ω 경계 증거는 유지하고, phase/SG 대응·여러 phase 공유·yield/receiving 제약을 서로 구분해야 한다. 전체261개의 모형을 이번 숫자로 재보정하지 않는다.

읽기 전용 스크립트 실행2.42초, 원본/계약/config/선택plan/실제snapshot SHA 전후 불변. `python -X utf8 -m unittest diagnostics.test_movement_signal_authority -v`의6 tests PASS:10528,10366 상류 반례,10426 native-only SG, 부실 증거 승격 금지, 실제 phase 불일치 재고, 전체 분류 합을 검증했다. FZP scan, optimizer, VISSIM/COM 호출, 생산 코드 변경은 하지 않았다.
