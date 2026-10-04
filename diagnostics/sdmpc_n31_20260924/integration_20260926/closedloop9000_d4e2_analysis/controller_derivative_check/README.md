# RM·VSL 연속 예측 미분 검사 — 완료

**검사한 두 좌표에서는 미분 전달 누락을 발견하지 못했다. 실제 교통 이득 보정과 SDMPC 선택 검증의 완료를 뜻하지는 않는다.**

원래 passive 망 seed29의 실제4500초 상태와4350초 적용 명령을 사용했다. 과거 head 관측·VSL 이력은 기존 재생 코드로 복원했다. 모델은 동결된 셀23/도시 초기화 보정 후보(`local_merge_cell23/candidate_full_config.json`)이며 기본 채택하지 않았다. Ω TTT 목적함수·물리 계수·450초 지평·제약·명령 범위는 변경하지 않았다.

## 검사와 결과

실제 SDMPC의 PFO 진입점에서 최적화 직전에 가로채 기존 continuous predictor를 호출했다. 초기 명령은10484만 g8/6/4, 다른7미터·VSL·17도시 신호는 직전 실제 명령 유지다. 초기 명령은 기존 decoder와 actuator/trust-region 검사에 통과했다.

|검사 좌표|작은 변화 크기 두 가지|Ω TTT 미분(자동미분 / 독립 차분)|최대 owner 비용 미분 오차|최대 NP/NUF 미분 오차|
|---|---|---|---|---|
|10484 RM, 세 번째150초 블록|±0.001 / ±0.0005초|0.037372870 / 0.037372873|3.31e−9|6.43e−9|
|FW_E seg13 VSL, 첫150초 블록|±0.01 / ±0.005km/h|−0.398839477 / −0.398839480|9.55e−9|7.94e−8|

미분 수치는 제어기가 쓰는 정규화 좌표 기준이다(RM scale10초, VSL scale110km/h). 기준점 자체의20개 owner/passive 비용은 최대4.44e−16대·h 차이, NP/NUF는 정확히 일치했다. 두 변화 크기 모두 사전에 정한 허용오차를 통과했다. 좌·우 차분도 원자료에 남겼다.

이 점의 국소 Ω 기울기를 물리 단위로 환산하면 RM 녹색 증가 방향은+0.003737대·h/초, VSL 속도 증가 방향은−0.003626대·h/(km/h)다. 따라서 모델은 이 점에서 미터 제한 강화의 작은 이득, VSL 제한 완화의 작은 이득 방향을 전달한다. 이 수치를 실제1초/10km/h 변경의 유한 이득으로 외삽하거나, 다른 혼잡 상태의 일반 결론으로 사용하지 않는다.

FD 명령은 양자화를 거치지 않는 연속 미분 진단이다. 일부 점은 초기 명령의 변경 한도를 아주 조금 벗어날 수 있으며 native 후보로 검증·적용하지 않았다. 기존 실제 후보 검사와 구분한다. 전체 상태 궤적/모든 미분 열의 정확성을 인증한 것도 아니다.

## 계산과 실패 기록

- 총 AD450초1회, 독립 scalar450초9회. PFO/SDMPC 최적화 iteration0회. 새 VISSIM0회.
- AD 계산38.08초. 독립 scalar는3개씩3배치로59.47초. 독립검사 실행의 초기화 포함82.04초. 최적화나 VISSIM 실행 시간으로 보고하지 않는다.
- 첫 실행은 AD를 저장한 뒤 독립 query 복제의 pickle 식별자 검사에서 멈췄다. 역직렬화/재직렬화의 alias memo 때문에 식별자가 달라졌다. 원래 동결 요청 바이트와 그 context token을 그대로 사용하는 방식으로 진단 helper만 수정했다.
- 저장 AD의 anchor action token, 입력 SHA, 전체 변환 대상 모델 소스를 검증하고 재사용했다. 추가 AD0회. 첫 실패 자료는 삭제하지 않았다.
- 독립 scalar query는 빈 캐시에서 시작하므로 AD의 primal을 독립 예측으로 재사용하지 않는다. 아홉 응답의 action/context token은 기존 검증을 통과했다.
- `unused_action.joint.json`의 completed=false는 최적화 전에 의도적으로 종료한 adapter 기록이다. 이번 진단의 완료 여부는 아래 witness 폴더의`summary.json`과 exit0으로 판정한다.

## 해석과 다음 범위

합류 우선권 실험에서 원래 망에서도 RM 명령은 실제 합류량을 크게 바꿨다. 이번 작은 계산에서는 RM·VSL의 비용/자원 민감도도 SDMPC까지 전달된다. 따라서 두 사례를 “명령이 전혀 실행되지 않는다” 또는 “미분 연결이 통째로 빠졌다”로 설명할 근거는 없다.

남은 것은 원래 망의 실제 합류→상류 혼잡/하류 회복→대기 비용 예측 크기와, 실제로 유량 차이가 큰 상태에서의 제약·유한 후보·최종 선택이다.4500초의 기존 허용 RM 후보 이득은 작았으므로 이 결과로 큰 예방 이득을 탐색이 놓쳤다고 단정하지 않는다. 새로운 계수 탐색·native·push 없이 이번 검사를 종료했다. 기존9000초 STOP과 원래 망을 유지한다.

## 원자료

- 사전 계획: `protocol.json`
- AD 완료/독립검사 준비 실패: `../../closedloop_recorded4500_budget_check_derivatives_cell23_v1/`
- 완료된 독립검사: `../../closedloop_recorded4500_budget_check_derivatives_cell23_witness_v1/`
- 핵심 결과: 위 witness의`summary.json`, `ad_columns.json`, `scalar_responses.json`, `protocol.json`
- 원인/실행 로그: `ad_completed_witness_setup_failure.log`, `witness_run.log`
- 실행 helper: `../../probe_selected_arrival_path.py`의`--derivative-check`, `--derivative-resume`

전체 이득 보정 및 SDMPC9000 목표는 여전히 미완료다.
