# 모델 수정 및 두 상태 RM 비교 인계

브랜치 `codex/control-full-review-20260909`, 기준 커밋 `4f8d2c3` 이후 증분이다. 누적 모델 수정은 이미 이 브랜치에 포함되어 있다. 이번 전달은 그 뒤 완료한 세 native 실행, 고정 예측, 진단 코드와 재개 문서를 추가한다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**다. 모델 본체·기준망·기본 설정을 추가 변경하거나 실패 후보를 기본 활성화하지 않았다.

`K` = `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920`.

## 완료 결과

사용자 가속거리 수정 + 램프 DSD120 망에서 동측 본선 입력1098만 0.8배로 둔 조건이다. 과거 전역80/도시50 조건이 아니다. 각 seed 내 2550초까지 전체 차량 기록이 같은 상태에서 RM_C10490만 바꿨다. 10초 RED/GREEN 주기, 변경 폭 최대2초, VSL 및 다른 신호 조건은 유지했다.

2550–3000초 동측 본선 + 진입4개 + 진출4개 connector의 ΔTTT[veh·h], 8초 녹색 유지 대비다. 음수는 개선이다. 이 기준은 무제어가 아니며 Ω 전체 비용도 아니다.

| seed | 명령(150초별 녹색) | 실제 | 실행 전 모델 예측 |
|---|---|---:|---:|
|23|6→6→6초|+0.849444|−0.002318|
|23|6→4→4초|+1.498611|+0.013486|
|33|6→6→6초|−0.589167|−0.006916|
|33|6→4→4초|−0.837222|+0.040241|

모델이 모든 효과를 0으로 보는 것은 아니다. seed33에서는 본선 이득 일부를 예측하지만 크기가 부족해 강화 RM의 순이득 부호를 놓친다. seed23에서는 본선 부호도 틀린다. 실제 후보 순위는 두 상태에서 역전되는데 모델은 둘 다 6초 유지를 선택한다. seed33의 약한 RM은 실제 합류가103→104대로 늘면서 이득을 냈으므로 누적 합류량 감소만으로 설명할 수 없다. 합류 시점·차량군과 하류 전파·회복을 함께 확인해야 한다.

- 새 native3개는 모두3000초 완료했다. seed23의 중간 강도1개, seed33의 기준/중간 강도2개이며 기존 강화 런은 재사용했다.
- 같은 seed 내2550초 FZP prefix 정확 일치, 중간/강화2700초 prefix 일치, native LDP·적용 readback 및 비대상 신호 검증을 통과했다. LSA로 모든 COM 전환을 검증할 수 없는 한계는 기존 사용자 승인에 따라 LDP로 대체했다.
- seed23 최초 집계는 Pos<0 본선 생성 차량50vehicle-seconds를 빠뜨렸다. `result_v2.json`이 유효하며 총 차이는+0.835556에서+0.849444로 정정했다. 최초 결과·분석 실패·수정 전 소스를 보존했다. 런이나 사전 예측은 바뀌지 않았다.
- 두 seed는 개발 자료이며 독립 holdout이 아니다. VSL/동시 제어의 기존 이득 예측 실패도 미해결이다.

상세 근거는 `K/MATCHED_METER_MIDPOINT.md`, 유효 결과는 `K/matched_meter_midpoint_v1/result_v2.json`, `network_response_v2/result.json`, `K/matched_meter_midpoint_s33_v2/result.json`이다. 최신 실행 완료 기록은 마지막 폴더의 `checkpoint.json`이다. seed23 폴더의 checkpoint는 seed33 실행 전 과거 기록이다.

## 복원과 검증

저장소 루트에서 아래 순서로 복원한다. 기존 파일이 다르면 덮어쓰지 않고 중단한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_response --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_entry_speed --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_spatial --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_midpoint --restore --verify
python -B -X utf8 diagnostics/handoff_20260921_midpoint/verify_records.py
```

검사기는 저장된 소스 핀·LDP 파일 해시·구성 비용·포트 보존·경계 사건 회계를 재검사한다. 원시 FZP 전체를 다시 읽거나 예측/native 실행을 재시작하지 않는다. 대형 FZP/DB/배경이미지와 재생성 가능한 native 부가 출력은 Git에서 제외하고 위치·크기를 manifest에 남겼다. 추출 관측, 예측, LDP/LSA, 명령, 오류 기록, 망/신호 설정은 보존한다. 원시 궤적 재추출에는 제외된 원본의 별도 전송이 필요하다.

## 다음 작업

1. 두2550초 상태에서 같은 경계 입력·명령을 사용해 기존1초 수송 및 공간 분리 후보를 비교한다. 현재 lane/port 관측은 해당 cutoff로 다시 구성해야 하며2400초 상태를 옮겨 쓰지 않는다. 이번 전달에서 이 후속 계산은 아직 실행하지 않았다.
2. seed23의 손해와 seed33의 이득을 모두 설명해야 한다. 현재 혼잡 파동과 합류 시점 반응을 확인하고 보상항·임의 capacity drop·두 표본에 맞춘 임계값으로 부호를 만들지 않는다.
3. 구성 비용·순이득·후보 순위와 NC/자유류 보호가 통과한 뒤 미사용 seed를 검증한다. 그 뒤 Ω 도시 대기/TTD 및8개 독립 RM·green/offset/VSL의 follower game 연결을 검증한다.

푸시 작업 중 새 VISSIM 런·제어 계산·프로세스 종료는 하지 않았다. 누적 모델 구현과 검증 후보는 보존되지만 보정 완료를 뜻하지 않는다.
