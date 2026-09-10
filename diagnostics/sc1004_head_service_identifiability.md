# SC1004 head별 서비스 식별 가능성 — 완료 NC seed13

**10634 공유 자원의 현재619.591837veh/h는 실제 확인된 GREEN 통과량도 수용하지 못하는 상한이다. 다만 세 차로의 포화용량을 동시에 식별할 자료는 부족하다.** 71번 도로의 SG2 head를 확실히 GREEN 안에서 통과하고 이후10634에 진입한 이벤트668건을 확인했다. 전체 native GREEN1620초로 나눈 관측 노출당 통과율 하한은1484.444veh/h다. 현재 상한×동일 GREEN 노출이 허용하는 최대량은278.816대다. 포화 가정을 하지 않아도 현재 상한과 관측이 양립하지 않는다.

668건은666개 차량 ID의 물리 통과 이벤트다.5049는1136–1137초와2333–2334초,11350은2034–2035초와2628–2629초에 별도로 통과했다. 이들은 같은 프레임의 중복행이 아니며, 재진입할 때마다 같은 자원을 다시 사용한다. 반복 ID를 무조건 한 번으로 줄이지 않았다. 다만 **동일 head에서 반복 관측된 ID는 기존 SC15 block key와 혼동하지 않도록 headway fit에서 제외**했다. 원 이벤트는 모두 남겼다.

관측된 차로별 지속 대기 출발은71의3차로에서만 충분하다. 같은 SC15 규칙으로 얻은3차로의 구간 기반 출발률은1435.443–2100veh/h이고1·2차로에는 적격 gap이 없다. 이 값을3배하거나 세 source(W/offE/offW)에 각각 적용하면 안 된다. 생산 용량·설정·현 런은 변경하지 않았다.

## 원자료와 시간

완료된 `codex_area_observed_nc_s13_20260910`의1초 FZP만 사용했다. SC15가 사용한 동일 원천SHA `55c1bc02c68bb8def9c0c3b3ce163a918c20845b4e7113a4768ffe9616986340`과 일치한다. 현재 제어 런의 FZP나 다음 행동은 읽지 않았다.

- 원본1,415,953,087bytes/26,693,633행을 **한 번** 스캔하며 전체SHA를 계산했다(15.59초).
- source46/66/71, 각 직결 connector와 target의16개 물리 요소를 추출했다.1,408,275행을20,877,658bytes gzip으로 보존했다. 각 원래 FZP 행은 그대로이며 새 관측을 보간해 추가하지 않았다.
- 이후 조인·민감도·검증은 이 작은 추출만 읽었다. 최종 분석은9.81초다. 추출SHA·원본 크기/mtime·선택 목록·원문SHA를 `.extract.json`으로 고정했다.
- `[900,1350]`, `[2700,3150]`에 닿는 gap 전체를 fit에서 제외했다. 같은 seed의 시간 검증이고 seed14는 미검증이다.

Native INPX의 SC1004는FIXEDTIME/prog1/controller offset0, 실제 공급 SIG는`개포동 test-bed1004_n4dr150.sig`다. SIG 내부 offset75초, cycle150초를 포함했다. SG2/3/4/5/7/8의 완료 NC LSA와 각 그룹 첫 관측부터5399초까지 정수초 상태가 모두 일치했다. 최초 상태 시각은 각각75/49/1/123/49/1초다. 최초 LSA 이전 crossing은 guaranteed-GREEN fit에 쓰지 않았다. 제어로 COM override된 다른 런에 native LSA를 적용하지 않는다.

## 물리 head와 모델 자원의 조인

모든 head의 정확한 ID·position·lane·connector geometry는 JSON에 보존했다. 모델 연결은 새 모델을 구성해 추측하지 않고, 이미 고정된 `selected_signal_capacity_audit.json`의 실제900 최종 movement/physical authority 및 corridor turn view에 조인했다.

| Source / head 차로 | Native SG / 선택 phase | head 뒤 자원 | 현재 연결 가능한 model 경로 | 판정 |
|---|---|---|---|---|
|46 L1–3|SG4 / p1|10626→67|`SC1004_N_SC1003_to_S`(boundary_out)|head 경로는 고유. sustained gap0 → 용량 추정 없음.|
|46 L4|SG7 / p2|10627→56|`SC1004_N_SC1003_to_E_SC1005`의 단일 corridor turn|head 경로는 고유. gap0 → 추정 없음. 미래1129 목적지 분율을 서비스에 다시 곱하지 않음.|
|66 L1–3|SG8 / p1|10631→47|`SC1004_S_to_N_SC1003`(boundary_in)|head 경로는 고유. gap0 → 추정 없음.|
|66 L4|SG3 / p2|10633→68|`SC1004_S_to_W`(boundary_in)|1개 실제 head 서비스. 아래 출발 표본 존재. 현재206.530612는 실측 식별값이 아님.|
|71 L1–3|SG2 / p3|10634→56|W/offW/offE→E의 세 입력이 **하나의 자원**을 사용|668 GREEN 통과 이벤트 확인. L3 출발 표본만 존재;3차로 포화용량 추정 없음.|
|71 L4–5|SG5 / p4|10635→47|`SC1004_W_to_N_SC1003`(boundary_in)|각 차로의 작은 출발 표본. 서로 다른 시간 표본을 합해2차로 용량으로 삼지 않음.|

10634의 source membership은 현재 corridor turn contract에서 직접 확인된다: `SC1004_W_to_E_SC1005`, `SC1004_offW_to_E_SC1005`, `SC1004_offE_to_E_SC1005`. 세 항목의619.591837을 합하지 않는다. 각 차량이 어느 상류 source에서 왔는지를 이번 head 관측만으로 다시 분해하거나, 이동 beta를 곱해 서비스율을 배분하지 않았다.

다음 세 가지는 해당 source head를 통과하기 **전에** 갈라지므로 head service에서 제외했다.

| source lane | 우회 connector | branch position | 해당 head position |
|---|---|---:|---:|
|46 L1|10625→68|949.207554m|953.160164m (SG4)|
|66 L1|10632→56|2630.062020m|2658.841933m (SG8)|
|71 L1|10642→67|37.487450m|78.980074m (SG2)|

특히66→10632는1129 prefix로 가는 경로지만 SG8 뒤가 아니다. 이 우회 흐름에 아래66 L4/SG3 수치를 적용할 수 없다. 71→10642는 **L1**이며 L4가 아니다. 제 초기 계획 메시지의 lane4 표기는 INPX 확인 직후 정정했다.

전체 선택 도로 이탈에서907건은 확인된 pre-head bypass,225건은 departure lane 대응 미확정,81건은 다음1초의 선택 범위에서 endpoint를 찾지 못한 경우다. 마지막81건을 실제 차량 소실로 판단하지 않는다. 해당 자료는 head crossing lower bound와 다른 사건이며, 이탈 표의 열을 head 통과량에 합산하지 않았다. head를 걸쳐 lane이 바뀐 bracket도 임의 SG 배분 없이 미확정으로 남겼다.

## 대기 출발 표본과 보수적 해석

SC15와 같은 핵심 조건을 **물리 head/lane별**로 적용했다: 두 crossing bracket 전체가 같은 GREEN이고, 두 번째 출발이4번째 이상이며, 그 사이의 모든 정수초에 head 전 동일 차로 정지 차량(speed≤5km/h)이1대 이상 있어야 한다. 불확실한 crossing이 사이에 끼거나 같은 head의 반복 ID가 섞인 gap은 제외했다. 연속 gap 블록의 첫/마지막 crossing 구간으로 duration 상하한을 계산하여1초 오차를 gap마다 중복 누적하지 않았다.

| head / 경로 | 확인 head crossing | Fit gap / block | 같은 SC15 queue 조건의 출발률 구간(veh/h) | 제외된 시간 검증 gap |
|---|---:|---:|---:|---:|
|46 L1/L2/L3 SG4→10626|14 /17 /18|각0|추정 없음|0|
|46 L4 SG7→10627|60|0|추정 없음|0|
|66 L1/L2/L3 SG8→10631|45 /37 /16|각0|추정 없음|0|
|66 L4 SG3→10633|396|209 /30|1642.795–1890.452|47|
|71 L1/L2 SG2→10634|110 /172|각0|추정 없음|0|
|71 L3 SG2→10634|398|63 /25|1435.443–2100.000|8|
|71 L4 SG5→10635|240|14 /9|1362.162–2652.632|9|
|71 L5 SG5→10635|269|10 /8|1241.379–2769.231|8|

이 구간은 표본 crossing 시각의1초 불확실성에 따른 범위다. 통계적 신뢰구간이나 자유 하류에서의 포화용량 범위가 아니다. 실제 수신 공간·양보/conflict 예약을 FZP가 직접 제공하지 않는다. 같은 차로 경로의 head 이후20m 안에 정지 차량이 보이면 그 gap을 제외했지만, 정지 차량이 안 보인다는 사실만으로 자유 수신을 증명하지 않았다.

긴66번 도로에서는 ‘어딘가에 정지 차량이 있다’가 특히 약한 조건일 수 있다. 그래서 SC15에도 있던20m 근접 정지 대기 지표를 별도 민감도로 남겼다.66 L4의 적격 gap 중 가장 가까운 정지 차량은1.78–115.96m upstream에 있었고, 각 gap 최대 거리의 중앙값은67.00m다. head20m 이내 정지 대기가 계속 보이는 표본은3gap뿐이며981.818–2160veh/h로 매우 넓다. 출발 두 차량 모두 해당 방문에서 이전에 같은 차로에 정지한 것을 확인한209gap의 부분집합은205gap이고1651.007–1916.883veh/h다.

71 L3은 도로 길이가 약79m이며 적격 gap의 가장 가까운 정지 차량 거리는26.51–74.36m다. 근접20m 조건을 매 순간 요구하면0gap이다. 정지 대기의 전파와 출발 가속 때문에 근접20m 표본 부재를 ‘대기 출발 없음’으로 해석하지 않았다. 실제 두 출발 ID의 이전 정지도 확인되는59gap에서는1454.795–2259.574veh/h다. 원래의63gap 결과와 이 강화 조건을 구분하여 보존했다.

71의 세 SG2 차로에 정지 대기가 동시에 보이는 GREEN 정수초는65초다. 하지만 L1·L2에는4번째 이후까지 지속되는 적격 gap이 없다. 초기 대기를 모두3차로의 지속 포화로 승격할 수 없다. **현재619.59보다 큰 물리 처리량이 필요하다는 근거는 강하지만, 이를 바꿀3차로 포화 파라미터의 단일값은 이 자료로 선택하지 않았다.**

## Fit에서 제외한 시간 구간

| 경로 / 차로 |900–1350 gap / 관측 출발률 구간|2700–3150 gap / 관측 출발률 구간|
|---|---|---|
|66 L4→10633|26 /1872.000–2127.273|21 /1680.000–2043.243|
|71 L3→10634|4 /1309.091–2057.143|4 /1600.000–4800.000|
|71 L4→10635|7 /1145.455–1400.000|2 /1200.000–1800.000|
|71 L5→10635|6 /1270.588–2400.000|2 /1440.000–2400.000|

검증 표본이 적고 범위가 넓다.66 L4의 첫 검증 구간은 fit 구간보다 빠른 출발을 보여 동일 seed 안에서도 변화가 있다. 이 표는 held-time의 관측 비교이며 차량 방출·backlog를 새 모델로 재현한 결과가 아니다. endpoint/MPC는 실행하지 않았다.

## `measurement members=0`의 의미와 최소 연결 방향

현재 온라인 추정 그룹46/p1,66/p1,71/p3은 sat_est가 있어도 members가 모두 빈 목록이다. 기본 배분 종류가internal만이어서 실제 대응인 boundary_out/boundary_in/off_ramp가 빠진다. 이것은 head→물리 서비스 자원 연결이 불가능하다는 뜻이 아니다. 위의 조인은 고유한 head/connector/SG 수준에서 성립한다.

그러나 종류 필터만 완화하여 기존 링크 sat_est를 대입하는 것은 안전한 수선이 아니다. 링크 이탈에는 pre-head bypass와 다른 SG 차로가 섞이고, 기존 seed 그룹66/p1은SG8인데 이번에 출발 표본이 있는 것은SG3/p2다. 창720→870의 이탈 분자와 action750의 미실행 기본 녹색 분모 문제도 기존 감사에서 남아 있다. 이 자료는 온라인4162.397이나46의4687.878을 포화율로 승인하지 않는다.

후속 변경의 최소 계약은 `physical_service_key=connector`, 실제SC/SG/head/lane 목록, 창별 executed GREEN 및 crossing bracket, queue/receiving 적격 조건, 증거 해시를 먼저 가진다. 이를 확인된 model member 목록과 연결하여 **단일 accepted service budget**에 공급한다. physical10634가 여러 source를 받는 경우 전체 자원에 한 번 공급하며 source별 beta로 용량을 재분배하지 않는다.10632처럼 head 전 우회하는 경로는 이 신호 서비스 계약의 수신 대상이 아니다. 미확정 다른 off-ramp alias는 이름만으로 이 표에 넣지 않는다.

현재 산출물은 식별 가능성·하한 증거다. 생산 cap을 변경하거나17SC 전체로 수치를 확대하지 않았다. 다른16SC에 대해서는 기존 `selected_signal_capacity_audit`의 head/phase/종류 목록을 후속 관측 대상 목록으로 사용할 수 있으나, 이번 FZP 분석이나 용량 추정에 포함하지 않았다.

## 산출물·검증

모든 파일은 `diagnostics/sc1004_head_service_identifiability.*`다. `.json`에는 head별 수치·fit block·held-time·모델 연결·미확정 사건·sourceSHA를, `.head_crossings.csv/.headways.csv/.head_frames.csv/.departures.csv`에는 재계산 가능한 작은 행을 담았다. `.selected.fzp.gz/.extract.json`은 원 FZP 재스캔을 피하는 추출 증거다. `.py`는 재현기, `.checks.py`는7개 집중 회귀다.

7개 회귀는 pre-head bypass3건, lane ambiguity, GREEN 경계, block endpoint 오차, 모든 fit의 holdout 제외·산술, 실제 반복 방문과 프레임 중복의 구분, 표본 없는 차로의 no-estimate를 확인했다. Hubble의 독립 읽기에서도63gap 블록 합과1435.443–2100 계산이 일치했다. 작은 artifact만 읽었고 추가 FZP scan은 없었다. 생산·설정·네트워크 수정0, 분석에서 고정한 source의 전후 변경0이다.

재현: `python -X utf8 -m diagnostics.sc1004_head_service_identifiability` — 첫 실행만 원 FZP를 읽고 이후 SHA 검증한 추출을 재사용한다. 검증: `python -X utf8 diagnostics/sc1004_head_service_identifiability.checks.py`.
