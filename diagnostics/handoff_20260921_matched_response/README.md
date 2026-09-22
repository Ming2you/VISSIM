# 모델 수정·RM 응답 후속 인계

브랜치 `codex/control-full-review-20260909`, `9b0108d` 이후 증분이다. 누적 모델 수정은 이전 커밋까지 이미 포함되어 있다. 이번에는 그 모델의 기존 선택 기능을 비교한 코드4개, 완료 예측48개 사례, 실패 기록과 사후 본선 회계를 보존한다. **이득 예측 보정은 NOT_QUALIFIED**이며 본체·기준망·기본 설정을 추가 변경하지 않았다.

최신 결과와 다음 작업은 [MATCHED_SPATIAL_RESPONSE.md](../demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/MATCHED_SPATIAL_RESPONSE.md)를 읽는다. 기존 native 완료·물리 명령 검증은 [이전 인계](../handoff_20260921_midpoint/README.md)에 있다. 이번 푸시 작업에서 새 시뮬레이션이나 예측을 시작하지 않았다.

이동거리·진출 위치 후보는 seed23의 RM 손해와 seed33의 이득에 대한 순위를 맞췄다. 다만 seed33 강한 RM은 실제 −0.837222에 대해 −0.065032veh·h만 예측했고 seed23 본선 부호도 틀려 채택하지 않았다. VSL과 전체 Ω/follower game 검증도 미완료다.

## 다른 컴퓨터에서 복원

저장소를 이 브랜치로 받은 후, 이전 인계의09-16 →09-19 →09-21 →response →entry_speed →spatial →midpoint 패키지 복원을 먼저 한다. 이후 저장소 루트에서 실행한다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_matched_response --restore --verify
python -B -X utf8 diagnostics/handoff_20260921_matched_response/verify_records.py
```

검사기는 저장 기록과 파일 해시만 확인한다. native나 모델 예측을 재실행하지 않는다. 기존 파일이 다르면 복원 도구가 덮어쓰지 않고 중단한다. `verification.json`은 전달 전 검사 결과다. 이 패키지 자체의 빈 폴더 복원도 별도로 확인한다.

원본 FZP·native DB는 이전처럼 Git에서 제외되어 있다. 현재/과거 관측 추출, 고정 예측, 설정·진단과 해시를 전달하므로 저장 기록의 검토는 가능하다. 원시 차량을 다시 추출하려면 이전 manifest에 기재된 FZP를 별도로 옮겨야 한다. 기존 원본은 로컬에 보존했다.
