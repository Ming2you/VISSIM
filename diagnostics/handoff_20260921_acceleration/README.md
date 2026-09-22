# 모델 수정 및 가감속 반응 검증 인계

브랜치 `codex/control-full-review-20260909`의 `fbdbeed` 이후 변경을 전달한다. 이전 커밋의 정본 모델 수정에 더해, 추종 이력·공간 가감속·속도 갱신 크기를 검사한 코드와 완료 결과를 보존한다. **RM/VSL 순이득 보정은 NOT_QUALIFIED이며, 실패 후보는 기본 비활성 상태다.**

## 이번에 포함한 내용

- `downstream_spatial_rollout.py`에 선택적 자기/전방 가감속 기억과 원래 물리 셀 크기의 속도 갱신을 추가했다. 기본값은 각각 `None`, `transport`이므로 기존 동작을 유지한다. 정본 controller에 채택하지 않았다.
- 현재 대상 차량의 직전 가감속은 조건부 5초 속도 예측 오차를 RM 약 4.3%, VSL 약 4.0% 줄였다. 대상 ID 없이 100m 공간으로 집계해도 추가 정보가 일부 남았다. 다만 나머지 입력에는 실제 차량 간격·상호작용 상태가 있으므로 거시 모델이나 450초 자율 예측의 검증 성공은 아니다.
- 자기/전방 기억을 실제 수송 예측에 연결한 두 후보는 각각 12개 30초 비교 중 11개에서 속도 오차가 커졌다. 계수는 유지하고 속도식의 공간 크기만 바꾼 후보도 30초 비교 11/12개 및 무제어 4/4개에서 악화했다. 모두 기각했다.
- 최초 DESSPEED 출력 자릿수 불일치로 중단된 검사, 수정 전 소스, 학습 행·계수·전체 60개 예측 궤적, 검증 결과를 함께 보존한다. 원본 20열 전체가 같았다고 주장하지 않는다.
- 과거 transport 검사기가 해당 실험에 실제 사용한 보존 소스를 해시로 확인하도록 보완했다. 이전 결과의 소스 해시는 변경하지 않았다.

`K`는 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920`이다. 자세한 근거는 [공간·자율 예측 보고서](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/SPATIAL_ACCELERATION_AND_AUTONOMOUS_GATE.md), [추종 이력 보고서](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/INTERACTION_MEMORY_AND_TARGET_RESPONSE.md)에 있다. 보고서의 “로컬·푸시 미포함”은 작성 당시 상태이며 이번 전달에 포함한다.

## 유지한 조건과 현재 한계

사용자 가속거리 수정 + 램프 DSD120 + 동측 본선 입력1098만 0.8배 조건이다. 과거 전역80/도시50 조건으로 바꾸지 않는다. 이번 증분에서 정본 core 4파일·기준망·수요·기본 설정은 바뀌지 않았으며, 새 VISSIM 실행이나 사용자 프로세스 조작도 하지 않았다.

모델은 제어 효과의 일부를 표현하지만 본선 이득과 램프/진출 대기 비용을 합한 순이득·선택 순위를 신뢰할 수준은 아니다. 이번 후속은 하류15–20셀의 국소 진단이다. 전체 Ω, 새 기하의 full GNE, 미사용 seed 검증은 완료되지 않았다. 개발에 사용한 seed13/23/33/43을 미사용 검증 자료로 세지 않는다.

다음 작업은 NC2550초16셀 주변의 현재→다음1초 속도 오차를 **차량 유입·유출·차로 이동에 따른 속도 혼합**과 **같은 차량들의 실제 가감속**으로 나누는 것이다. 아직 이 장부 분석의 완료 결과는 없다. 미래 소속 구간과 속도는 사후 정답에만 쓰고 운영 입력에는 넣지 않는다. 이 구분 전에 이미 기각한 기억 가중치·공간 크기·전역 계수 sweep을 반복하지 않는다. 이후 차량 보존·대기 비용·자율 예측·RM/VSL/동시의 구성 비용과 순이득·무제어 보호를 함께 검증해야 한다.

## 다른 컴퓨터에서 복원 및 검사

이전 패키지의 README 순서대로 `handoff_20260916`부터 `handoff_20260921_transport`까지 복원한 다음, 저장소 루트에서 실행한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_acceleration --restore --verify
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_interaction_memory.py
python -B -X utf8 diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/verify_target_spatial_coupling.py
python -B -X utf8 diagnostics/handoff_20260921_transport/verify_records.py
python -B -X utf8 scripts/verify_parameters.py diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/transport_step1_exchange_off_v2/config.json
```

위 검사는 저장 결과를 읽으며 VISSIM이나 새 예측을 실행하지 않는다. 저장 학습 행의 적합 결과는 재계산해 대조한다. 파라미터 검사의 기존 calibration 무시 경고는 그대로 남겨, full GNE가 검증됐다는 의미로 해석하지 않는다.

`verification.json`은 이번 전달 전 기록 검사 결과, `parameter_check.txt`는 파라미터 검사 출력이다. `restore_verification.json`에는 빈 폴더 복원과 해시 검증 결과를 기록한다. `direct_files.json`, `evidence_manifest.json`은 코드·문서·압축 증거의 정확한 파일 목록과 해시다. 이 패키지는 기존 자료를 덮어쓰지 않는 복원 도구를 재사용한다.

원시 FZP·native DB는 용량 때문에 Git에 포함하지 않고 로컬에 보존한다. 추출 결과와 이전 패키지로 저장 기록 검사를 할 수 있지만, 원시 차량 궤적을 다시 추출하려면 기존 manifest에 기재된 원본을 별도로 옮겨야 한다.
