# 모델 수정 및 최신 반응 진단 전달

브랜치: `codex/control-full-review-20260909`. 누적 모델 변경은 `6d7612b`, 이전 진단은 `f7a6ca3`이며 이번 증분에는 그 이후의 차량군 추적, 실제 속도식 점검, 기각된 두 완화 후보와 합류 속도·시점 자료를 담았다. **RM/VSL 순이득 보정은 NOT_QUALIFIED**다.

먼저 `docs/HANDOFF_20260921_gain_prediction.md`와 `diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920/SPEED_RESPONSE_AND_HANDOFF.md`를 읽는다. 코드와 짧은 요약은 Git에 직접 포함하고 대형 저장 예측·단계별 진단은 이번 증분 압축 파일로 전달한다. 기존 복원기를 사용하며 같은 경로의 다른 파일을 덮어쓰지 않는다.

저장소 루트에서:

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921_response --restore --verify
python -B -X utf8 diagnostics/handoff_20260921/verify_followup.py
python -B -X utf8 diagnostics/handoff_20260921_response/verify_response_records.py
```

새 검사는 저장된 입력 해시·예측·보존식·항별 재구성을 확인한다. VISSIM이나 예측 계산을 다시 실행하지 않는다. 기존170개 단위 검사의 통과 기록은 이전 전달 시점의 결과로 유지한다. 이번 전달에서 생산 모델 변경이나 단위 검사 재실행은 없다.

`direct_files.json`은 의도적으로 갱신한 문서와 새 직접 전달 파일의 해시다. 기존 두 직접 전달 manifest는 동결해 두고 `verify_followup.py`가 이번 manifest를 마지막에 겹쳐 검사한다. 이전 결과의 입력 pin은 덮어쓰지 않는다. 증분 압축의 `evidence_manifest.json`은 모든 복원 대상과 조각 해시를 기록한다.

원본 FZP/native DB는 포함하지 않는다. 새 저장 결과를 읽고 검증하는 데는 필요하지 않지만 차량 궤적 원시 추출을 반복하려면 기존 manifest의 원본 파일을 별도 전송해야 한다. 시뮬레이션·다른 사용자 프로세스는 이 전달 작업에서 건드리지 않았다.
