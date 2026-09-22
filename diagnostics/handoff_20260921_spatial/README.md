# 차로별 공간 수송 및 150초 예측 인계

브랜치 `codex/control-full-review-20260909`, 기준 커밋 `7bb685c` 이후 증분이다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**다. 누적 모델 본체 수정은 이전 커밋에 포함되어 있고 이번에는 후속 진단 코드·저장 결과·실패 근거를 전달한다. 정본 모델, 기준망, 수요, 기본 설정의 추가 변경은 없다.

`K` = `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920`.

## 완료한 것과 판단

- 동일 초기 차량의 NC/RM native 추종 반응을 대조했다. 첫 제동을 피하더라도 다른 차량·시점으로 제동이 옮겨갔다. 이를 전체 이득의 인과 분해로 해석하지 않는다.
- 하류 15–20셀에서 차로별 약 100m 재고와 속도 모멘트를 실제로 수송하는 국소 진단을 구현했다. 기존 METANET 속도식을 호출하며 새 controller/adapter가 아니다.
- 30초 자체 예측 40개와 관련 검사를 완료했다. 짧은 식 오차를 줄인 계수 재적합은 자체 예측을 악화시켜 기각했다.
- 계수를 유지한 150초 인과 예측 12개를 완료했다. 초기 30초 trace는 기존 결과와 정확히 같다. 해상도 개선은 장기 오차를 일관되게 줄이지 못했다.
- 실제 미래 상류 통과량만 주는 경우와 통과량·속도를 함께 주는 경우를 각각 12개 계산했다. 이는 원인 분리용이며 실시간 MPC 입력이나 성능 검증으로 사용하지 않는다. 내부 상태·말단 방출은 계속 예측했다.

차로별 100m·속도 모멘트 수송에서 RM−NC 국소 ΔTTT[veh·h]:

| 시작 | 과거 경계 고정 예측 | 실제 미래 경계 입력 진단 | 실제 VISSIM |
|---|---:|---:|---:|
|2400초|0.000000|−0.217778|−0.218611|
|2550초|−0.486915|−0.224831|−0.043611|
|2700초|−0.315604|−0.008660|−0.656667|

국소 영역에는 직접 움직이는 RM/VSL이 없다. 2400초에는 같은 초기 상태·과거 경계 때문에 인과 예측이 같고, 2550/2700초의 초기 상태는 이미 제어로 달라져 있다. 따라서 이 표는 동일 초기 상태의 450초 제어 이득 검증이 아니다. 실제 미래 경계를 줘도 2700초 차이가 남아, 상류 도착량만의 문제가 아니라 국소 전파·회복 동역학도 해결해야 한다. 이 결과로 공간 세분화를 정본에 승격하지 않았다.

## 복원 및 읽기 전용 검사

저장소 루트에서 아래 패키지를 순서대로 복원한다. 같은 내용이면 재복원하지 않으며 다른 내용의 기존 파일은 덮어쓰지 않는다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_response --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_entry_speed --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_spatial --restore --verify
python -B -X utf8 diagnostics/handoff_20260921/verify_followup.py
python -B -X utf8 diagnostics/handoff_20260921_spatial/verify_records.py
```

이번 검사기는 저장된 36개 150초 trace의 비용·속도 오차·보존식·경계 통과와 이전 30초 prefix를 재검사한다. 원래 수행했던 자체 예측 재실행 검사와 구분한다. 과거 소스 핀은 당시 보존한 스냅샷에 대조하며 결과의 핀을 고치지 않았다. `verify_local_interaction_spatial.py`는 최초 산출용 검사기이므로 기존 출력 폴더에 다시 실행하지 않는다. 이번 전달 검사는 위 `verify_records.py`를 쓴다.

전달 전 차로군·분기 공간·합류 속도 관련 단위 검사38개 PASS, 저장 기록의37개 소스 핀·5,400단계 보존식·3,600개 경계 통과 검사 PASS다. 정본 core4파일은 `7bb685c`와 바이트가 같다. 상세 영수증은 `tests.log`, `records_verification.json`, `core_unchanged.json`에 있다. 이는 구현/전달 검증이며 이득 예측 보정 완료를 뜻하지 않는다.

원시 FZP/DB는 이전 전달과 마찬가지로 Git에 없다. 현재 분석에 필요한 추출 프레임·집계·경계 사건·예측 trace는 증거 패키지에 있다. 원시 차량 재추출에는 원본 별도 전송이 필요하다. 준비/실패 디렉터리를 완료된 실험으로 세지 않는다. 실패한 scipy 적합 시도와 퇴화 계수 결과도 보존했다.

## 이어서 할 일

1. `K/PAIRED_INTERACTION_AND_SPATIAL_RESPONSE.md` 및 이번 150초 결과부터 읽는다. 추가 관측 RM 3000초 런은 이미 완료되어 반복할 필요가 없다.
2. 2700초 이후 상류 도착을 알아도 남는 하류 전파·회복과 off-ramp 배수/차로 접근을 분리한다. 평균 합류속도나 전역 계수 sweep을 다시 반복하지 않는다.
3. 약한 RM의 실제 이득과 같은 초기 상태에서 강화 RM의 손해를 모두 설명해야 한다. 중간 강도의 같은 초기 상태 비교는 다음 선택지이며 이번에 실행하지 않았다.
4. 450초 구성 비용·순이득·후보 순위·NC/자유류 보호를 통과한 뒤 미사용 seed로 검증한다. 새 기하의 Ω 도시 대기/TTD 및 full GNE 연결은 별도 미완료다.

이번 푸시는 완료 결과 정리다. 새 VISSIM 런이나 프로세스 종료는 수행하지 않았다.
