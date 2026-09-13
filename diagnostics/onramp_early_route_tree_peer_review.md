# 상류 on-ramp 경로 전개안 독립 검토

1135의 세 부모 경로를 아홉 경로로 전개하는 **XML 확률·연결 계산에서 차단 오류를 찾지 못했다.** 69에는 흡수할 상류 유입 경로가 없어 1134를 유지하는 판단도 맞다. 다만 이것은 경로 정보가 실제로 더 일찍 제공되거나, 동일 seed의 차량별 목적지가 보존되었다는 검증은 아니다. 기존 Combine/LookAhead 설정 때문에 수동 전개가 기존 엔진의 선행 결합과 얼마나 다른지도 아직 확인되지 않았다.

검토 원본은 `onramp_early_route_tree_audit.py/.json/.md`와 Ver2 INPX다. 독립 파서는 원 producer를 import하거나 재실행하지 않았다. 정확한 시각·네 파일 SHA·원점/경로별 결과는 `onramp_early_route_tree_peer_review.json`에 보존했다. 원본/생산 수정, 모델, COM, VISSIM, FZP 스캔은 모두 0이다.

## 독립 재계산 결과

| 부모:기존 경로 | 기존 선택 확률 | 1135:2 → 120 새 가중치 / 부모 확률 | 1135:3 → 123 | 1135:4 → 2 |
|---|---:|---:|---:|---:|
| 1123:2 | 10/12 | 6 / 1/2 | 2 / 1/6 | 2 / 1/6 |
| 1124:1 | 6/8 | 18/5 / 9/20 | 6/5 / 3/20 | 6/5 / 3/20 |
| 1125:1 | 6/8 | 18/5 / 9/20 | 6/5 / 3/20 | 6/5 / 3/20 |

부모의 다른 두 경로 속성과 가중치는 그대로이며, 분해한 가중치 합은 원래 10 또는 6이다. 세 suffix는 각각 `68→10772→121→10646→120`, `68→10772→121→10773→123`, `68→10681→2`다. 목적 위치 문자열도 원 1135의 `2272.2977955121637`, `179.06973212909716`, `2289.1984998704838`과 정확히 같다. connector 양 끝 도로, 차로 범위, 도로상 진입→진출 순서, 목적 위치의 XML polyline 범위를 별도로 검사했다. polyline 검사는 1mm 반올림 허용이며 COM 길이를 측정한 것은 아니다.

68의 incoming은 10625/10629/10633 세 개이고 모두 1135 앞이다. 부모 경로의 68 종점 4.950656/5.676183/6.322767m도 1135의 7.491513m보다 앞이다. 68 native input은 없다. 한 단계 더 확인하면 52의 10498/10501 및 46의 10495/10497 유입도 각 부모 decision 앞이다. 66은 incoming connector가 없는 source다. 이것은 삭제안의 구조적 범위를 지지하지만, 실제 차량의 경로 유효성과 완전한 적용 대상 집합을 대신하지 않는다.

1134에는 69 incoming 0, input1101이 있고 원 가중치 12:1:3:0.25가 확인된다. 따라서 48/65, 4/65, 12/65, 1/65 네 경로를 유지해야 한다. 10639 목적은 이미 69에서 정해지는 경로다. 1134 삭제는 이 세 부모 경로 전개에 포함되지 않는다.

## 차종·시간·기존 선행 정보

1123/1124/1125/1134/1135는 모두 `allVehTypes=true`, `routeChoiceMeth=STATIC`, `combineStaRoutDec=true`; 각 route의 formula는 빈 값이다. 현재 관련 링크는 `direction=ALL`, lane별 차종 제한 subtree도 없다. `AllVehTypes`는 차종 목록의 일부가 아니라 모든 차량 유형을 대상으로 하는 설정이며, STATIC 선택은 상대 가중치에 따른다. [PTV 2020 decision 속성](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_RoutenEntsch_Attr.htm)

정적 경로 interval은 시작 0 하나다. `2 0:x`의 x를 해당 구간 가중치로 읽는 해석은 맞다. input의 900초별 수요 구간과 혼동하지 않아야 한다. 빈 RelFlow=1은 기존 `total_offramp_ratio_audit.json`에 보존된 설치본 `attribute.xlsx`의 Attributes 1777행 기본값 증거와 일치한다. 이번 검토에서 COM readback은 하지 않았다. 상대 가중치 정규화는 선택된 decision 내부의 몫이며 경로 끝에 별도로 차량을 생성하는 수요가 아니다. [PTV 2020 정적 route 속성](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_Routen_Attr.htm)

관련 16개 물리 링크의 linkBehaviorType→drivingBehavior 및 차종 override를 확인했다. 도시부는 behavior1, 고속도로 목적 도로/connector는 behavior3이고 두 행동 모두 `vehRoutDecLookAhead=true`, `consNextTurn=false`다. 따라서 원 보고서의 behavior1 조건은 부모/68에 맞으며 freeway 부분도 LookAhead가 켜져 있다. `consNextTurn=false`를 LookAhead 비활성으로 해석하면 안 된다. PTV 문서는 LookAhead가 같은 도로의 후속 선택을 차로 선택에 반영하고, 더 먼 후속 선택은 Combine과 연결한다고 설명한다. 현 설정은 그 선행 정보 기능이 이미 작동할 수 있는 조건이다. [PTV 2020 lane-change 속성](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/FahrverhaltensparameterFahrstreifenwechsel_bearb.htm)

특히 66→10633은 68 lane4로만 들어온다. 10681은 lane1–2이므로 새 경로도 이 차로 이동을 없애지 않는다. 조기 route 정보, 실제 차로 접근, 입력 cohort의 목적지 구성은 서로 다른 측정 항목이다.

## p×q와 같은 seed의 한계

조건부 선택 가중치가 부모/차종/시간에 대해 그대로 적용된다는 전제에서 `P(parent turn)×P(child | turn)`은 **이 세 경로의 지역 목적 단면별 확률**을 보존한다. 이를 전체 여행의 최종 OD나 같은 시간 구간에 도착한 차량 수의 보존으로 넓히면 안 된다. 123의 route 종점은 네트워크 출구가 아니며, 2의 종점 뒤에는 decision1131이 있다. 120 경로는 decision1133@424m보다 뒤의 2252.998m로 진입한다. 이 후속 운행도 동일하게 남겨야 한다.

같은 seed는 같게 대응되는 난수 사용을 보장하는 계약이 아니다. 예를 들어 두 단계 선택이 첫 난수로 부모 turn, 다음 난수로 child를 골랐다면, 한 번의 누적 가중치 선택은 동일한 분포를 가져도 개별 차량에 같은 child를 줄 필요가 없다. 실제 VISSIM이 Combine 경로를 언제 몇 번 추첨하는지, 난수 stream을 어떻게 나누는지는 이번 검토로 확인하지 않았다. 따라서 추첨 수가 반드시 줄었다고도 단정하지 않는다. 변경으로 추첨 호출 순서·시점·대상 차량이 달라지면 같은 seed의 실현 경로 대응은 깨질 수 있다는 것이 정확한 제한이다.

경로의 조기 인식이 차로 변경/막힘을 바꾸면 수요 입력의 실제 수용 시각·차량 수와 downstream decision 도달 시각도 달라질 수 있다. 고정 명령으로 폐루프 제어 차이는 제거해도 이 실현 수요·목적지 차이는 남는다. 한 seed에서 총량이 비슷하거나 분율이 이론값 근처라는 이유만으로 차로 정보 효과를 분리했다고 주장할 수 없다. 동일 실현 OD 효과를 보려면 명시적인 차량별 목적지 coupling/replay가 필요하고, 그것을 구현하지 않는 실험은 seed별 실현 경로 차이를 함께 보고하는 확률 보존 네트워크 비교로 표현해야 한다.

## 고정 명령 VISSIM 비교의 구체적 확인표

실행은 root가 별도로 관리한다. 다음은 이번 검토에서 실행하지 않은 검증 계약이다.

| 계층 | 저장/비교 키와 분모 | 판정 |
|---|---|---|
| 입력 | seed, input ID, veh type, 생성 순서/시각, 실제 진입 시각; 예정 volume과 실제 admitted를 분리 | 기존/변경 실행의 요청 수요와 실제 admitted 차이를 모두 제시한다. 단순 VehNo만으로 다른 실행을 무조건 join하지 않는다. 반복 visit은 occurrence를 붙인다. |
| 부모 선택 | 1123/1124/1125 각각의 eligible crossing cohort, type, 입력 시간 구간; 원 decision/route 또는 새 symbolic child | 미변경 turn 6개를 포함해 분모를 닫는다. 신규 route 번호는 명시 mapping으로 원 parent×1135 child에 대응한다. 기존 active-route 때문에 선택을 건너뛴 차량은 별도 계수한다. |
| 합성 branch | 부모별 3×3 joint count: parent→10646/10773/10681; 선택된 목적지와 실제 connector 진입을 별도 저장 | `10772`는 10646/123 공유 prefix이므로 두 branch로 중복 세지 않는다. 각 선택 cohort = 목적 진입 + 아직 미도달 + 확인된 제거 + 추적 불명이다. |
| 수신 단면 | 10646→120@2252.998, 10773→123, 10681→2@2165.429의 고유 crossing; 실제 원 route destPos 통과도 별도 | connector 진입은 ramp 선택/대기 이후의 처리량이다. 같은 달력 구간의 부모 선택 수와 직접 같은 분모로 나누지 않는다. 선택 cohort를 종료까지 추적하거나 우측 검열을 명시한다. |
| 비대상 69 | input1101과 1134 네 경로 전체, 특히 75/10640 포함 | 네트워크 정의는 불변이어야 한다. 주변 교통과 난수 소비 영향으로 실제 counts는 달라질 수 있어 대조 표에 남긴다. |
| 물리 명령 | 동일한 절대 시각 CSV/JSON, VSL·meter quantized 값, SG GREEN/offset/cycle 및 1초 readback | 명령 replay가 동일해야 한다. 같은 최적화 설정만으로 동일 명령을 대신하지 않는다. 기존 strict cadence gate를 재사용한다. |
| 기전 | 부모 및 68 진입 전후 route/current decision, 차로·position, 첫 필요 차로 변화, 정지/대기, ERR 제거 | Combine 작동 전후의 정보 인식을 직접 구별한다. RoutDecNo 하나가 전체 미리 결합한 route를 노출한다고 가정하지 않고 물리 경로와 함께 본다. |

실현 OD 보존을 주장하려면 대응 가능한 입력 cohort에서 각 차량의 목적지 label이 일치하고, 미매칭/미선택/제거/검열도 함께 닫혀야 한다. 단순 branch 총수 일치는 차량 간 목적 교환을 숨길 수 있다. 일반 확률 보존 비교라면 이 차이를 숨기지 않고 seed별 parent×child 표와 성능 차이를 함께 제시하고, 필요한 반복 seed 범위를 사전에 정한다. Ω 출입 지표와 route 목적 단면은 별개이므로 route 종점 도달을 TTD로 자동 보상하지 않는다.

원 producer의 `native_input_on68=False` 같은 항목은 현재 XML과는 일치하지만 상수다. 향후 다른 INPX까지 일반화하려면 이 값 및 classes/STATIC/Combine/LookAhead/길이 검사를 실제 XML에서 유도·실패 처리해야 한다. 이번 고정 파일의 아홉 경로 결과를 무효화하는 발견은 아니다.
