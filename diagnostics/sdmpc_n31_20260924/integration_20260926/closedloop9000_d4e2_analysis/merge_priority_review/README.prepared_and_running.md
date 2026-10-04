# 10484 합류 우선권·협력적 차로 변경 — 입력 준비, 실행 전

2026-09-28. 기존 STOP 유지·새 VISSIM 금지 지시를 유지한다. 사용자가 제안한 합류 동작의 변경을 독립적으로 검토할 수 있게 사본만 준비했다. 기준 망·플랜트·controller·기존 결과를 바꾸지 않았고 VISSIM은 시작하지 않았다.

## 확인한 문제와 비교 자료

seed53의 기존 RM 완화에서 head 통과106대, 합류91대, 종료 posthead16대였다. 실제 도착을 준 조건부 모델은107.55/107.80/0.75로 신호 이후 대기를 과소예측했다. 다만 기존 seed53 완화는 동측 미터4개를 함께 바꿨으므로 이 결과를10484 단독 개입의 인과 효과로 표현하지 않는다.

10484만 완화한 완료된 seed47의 `hold`와 `release_10484`를 기준으로 사용한다. 원본은 선택망과 **seed29→47만** 달라지며, 그 값을 되돌린 바이트가 선택망과 정확히 같다. 기존 두 런의 native LDP·readback 검증은 모두 통과했다. 우선권 조건에 사용할 이벤트 CSV는 각각 기존 실런의 CSV와 바이트 단위로 같다.

## 준비한4개 망

|조건|conflict area2867|협력적 차로 변경|
|---|---|---|
|baseline|PASSIVE|기존 유지|
|priority|ONEYIELDSTWO: 본선24가 램프10484에 양보|기존 유지|
|cooperation|PASSIVE|본선 링크24에만 활성|
|both|램프10484 우선|본선 링크24에만 활성|

2867은 link1=24, link2=10484다. 우선권은 이1개 conflict area만 수정하며 다른 기하 겹침 영역은 활성화하지 않는다. 자동 conflict type 판정은 유지했다. XML에 남은 비활성 `conflTypMan=CROSSING`을 실제 유효 유형으로 오해하지 않는다. 실제 VISSIM 로드 후 우선 대상·유효 유형 확인은 아직 수행하지 않았다.

협력적 차로 변경은 driving behavior3를6으로 복사해 `coopLnChg=false→true`만 변경하고, 새 link behavior6으로 **링크24 전체 약3.346km에만** 연결했다. 원래 behavior3와 나머지 링크는 바꾸지 않았다. 짧은 셀23만의 변경은 아니며 그 범위 제한을 보고해야 한다. 기존 `advMerg=true`, 협력 감속·차두거리·안전거리 계수는 유지했다. 연결 기하가 이 기능을 실제로 활용하는지는 실런 검증 대상이다.

네 망 모두 변경 부분을 되돌리면 원본 seed47 바이트와 정확히 일치한다. 수요·경로·신호·DSD·기하·seed·SimRes는 그대로다. 신규 객체는 협력 실험용 behavior6/link behavior6뿐이다. 수요·신호 서비스·METANET 계수를 함께 바꾸지 않았다.

## 먼저 실행할 유한 비교안

먼저 **priority만2런**을 기존 정본 `fast_fixed_profile.py`로 준비하고 `fast_nc_run.ps1`의 비실행 검사를 통과했다. 새 runner나 adapter는 만들지 않았다.

- seed47,3300초 종료, SimRes10, native FZP5초와 LDP·명령 readback 유지.
- 같은 과거 명령 재생 후2700초부터10484만 비교: g2 유지 또는 g4→6→8→10으로150초마다 완화. 다른7미터와 VSL·도시 신호는 두 런에서 동일.
- 주 평가 구간2670.1–3120.1초,450초. 기존 런과 같은 정의를 사용한다. 무제어 실험이나 새로운 ALINEA 폐루프라고 부르지 않는다.
- 각 망의 유지/완화 쌍은 같은 초기 이력을 갖는다. 그러나 우선권은 t0부터 적용되므로 **서로 다른 망의2670.1초 상태는 같다고 가정하지 않는다.** 망별 RM 차이와 전체 시나리오 차이를 구분한다.
- 기존 seed47 passive 두 런을 재사용한다. 새로운 결과는D드라이브의 별도 폴더에 두도록 계획했지만, 그 결과 폴더·실행 프로세스는 아직 만들지 않았다.
- 새2런은 순차 실행한다. 사용자 VISSIM 창에 연결하거나 종료하지 않는다. 기존 소유 PID/생성시각 확인 및 최초 실제 무진행300초 watchdog을 사용한다. 자동 재시도·추가 seed·9000초 확대는 이2런에 포함하지 않는다.

판단 지표는 명령/실제 SG 일치, 신호 통과→합류 누적량과 시차, pre/posthead 재고·미완료 차량, 셀21–25 차로별 감속·방출, 도시·외부 대기와 Ω TTT다. 램프 합류만 늘고 본선 대기가 더 커질 수도 있다. 임의의 이득 또는 RM 활성화를 성공 기준으로 삼지 않는다. 이 짧은 비교로9000초 성능을 인증하지 않는다. seed53의 더 강한 현상을10484 단독으로 재현한 시험도 아니다.

협력만·둘다의 source/profile/event 파일은 준비했지만 실런 준비/시작은 별도 결정 대상으로 남겼다. 먼저 두 우선권 런에서 실제 posthead 병목이 나타나는지, 우선권이 어떤 동작을 바꾸는지 확인한다.

## 현재 상태

`prepared_review.json`, `verification.json`과 두 `*_dry_run.json`에 검증 결과를 저장했다. 기존 STOP 해시 동일, 새 native0회, push0회. 실런 전에는 사용자의 이전 새 런 금지 범위를 변경하는 응답이 필요하다. 질문은 “램프 우선권2런 시작 / 새 런 없이 준비 자료 유지”로 보냈다.

공식 근거: [VISSIM2020 conflict areas](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Konfliktflaechen_modellieren.htm), [VISSIM2020 lane change behavior](https://www.cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/FahrverhaltensparameterFahrstreifenwechsel_bearb.htm). XML 우선권 문자열은 현재2020 네트워크에 이미 사용되는 `ONEYIELDSTWO`를 따랐다.

## 2026-09-28 사용자 승인 후 실행

사용자 `ㄱㄱ`에 따라 priority-only 두 런을 19:49:58부터 순차 실행했다. 큐 PID40640, 첫 VISSIM PID31672(19:49:59 생성)이다. 시작 전 조회에서 다른 VISSIM/계산은 없었다. 기존9000초 STOP은 변경하지 않았다.

로드 후 COM 확인: conflict2867 `ONEYIELDSTWO`, link1=24, link2=10484, 자동 유형 판정=True. 비활성 수동 유형은 CROSSING으로 남아 있지만 유효 유형으로 해석하지 않는다. 자동 계산된 차로별 유형은 시험한 COM 속성으로 노출되지 않아 `NOT_EXPOSED`로 명시했다. 우선권·대상 링크 확인은 통과했다.

`fast_nc_runner.vbs`에 선택적인 읽기 전용 로드 확인만 추가했다. 변경 전 파일과 prepared metadata를 보관했고, 명령 이벤트·물리 설정은 그대로다. 최초 실제 FZP 진행은 19:50:28,60.1초로 확인했다.

실행 위치: `D:/VISSIM_runs/20260928_merge10484_priority_s47`. `queue_status.json`이 두 런과 native LDP/readback 검증을 기록한다. `compare_completed.py`는 두 런이 모두 닫힌 후 기존 IndexedFzp로 각450초 구간만 한 번 비교하며, 추가 native/보정/최적화는 하지 않는다. 결과는 `completed_comparison/summary.json`과 `README.md`다. 진행/실패는 `postprocess_status.json`과 D의 postprocess stderr에 남긴다.

기존 STOP을 해제한 것이 아니며, cooperation·both·추가seed·9000초 확장은 승인 범위에 포함되지 않는다.

## 원래 plant와 우선권 실험의 연결 범위

`plant_priority_interface_review.json`은 실행 중에 작은 기존 CSV와 합류 코드만 읽어 확인한 자료다. 신규 예측·보정이나 실행 중 FZP 조회는 하지 않았다.

기존 seed47의 동일450초 구간에서10484 유지/완화의 실제 합류는45/94대, 램프 도착은77/81대다. 완화 시 초기 대기 재고도 방출하므로 도착보다 합류가 많을 수 있다. 이 상태에서는 RM의 물리 유량 효과가 이미 있으므로 “RM이 전혀 실현되지 않는다”는 일반 해석은 지지하지 않는다.

10484 head 서비스 모델의 g2/g4/g6/g8/g10 상한은360/720/1080/1440/1512대/h다. 실제 합류는 이 상한을 그대로 쓰는 것이 아니라, 출발 가능한 재고·이동 시간·본선 수용량·gap 공급으로 추가 제한된다. 실제450초 평균 도착률만으로 짧은 첨두나 초기 재고 효과를 배제하지 않는다.

검토한 runtime에는 conflict area 우선권 또는 coopLnChg의 직접 입력이 없다. 본선 충돌 유량이 많아지면 gap 식이 램프 공급을 낮추는 근사다. 따라서 VISSIM의 램프 우선권 변경 결과를 원래 passive 망의 계수 보정 자료로 곧바로 합치지 않는다. 우선권 망을 나중에 채택한다면 합류 노드의 공통 수용량 아래에서 램프와 본선의 양보 관계를 함께 표현해야 한다. 램프 gap 상한만 제거하고 본선 흐름을 그대로 두는 방식은 그 변경을 설명하지 못한다.
