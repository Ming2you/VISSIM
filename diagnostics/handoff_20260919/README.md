# 2026-09-19 증분 인계 패키지

최신 판단과 다음 작업은 [인계 문서](../../docs/HANDOFF_20260919_cost_and_ramp_response.md)를 먼저 읽는다. 새 기하의 단독 진단 MPC 비용 집계 수정과 램프 보정 실험을 보존한다. full GNE 완성 또는 RM/VSL 성능 개선 완료를 뜻하지 않는다.

## 다른 컴퓨터에서 복원

branch `codex/control-full-review-20260909`를 받은 뒤 저장소 루트에서 실행한다. Python 의존성은 [기존 목록](../handoff_20260916/requirements-offline.txt)을 따른다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260919/verify_portable.py
```

마지막 명령은 VISSIM을 실행하지 않고 단위 검사와 기록 상태450초 예측을 검증한다. 기존 결과를 수정하지 않는다. JSON 영수증의 과거 절대 경로는 원본 출처이므로 일괄 치환하지 않는다. 실제 모델 로딩은 동일 SHA의 저장소 상대 경로로 기하를 찾는다. 옛 native 준비 폴더의 `rule_runtime.txt`는 옛 Python 경로를 포함할 수 있으므로 다른 컴퓨터에서 직접 실행하지 말고 해당 준비 스크립트로 새 폴더를 만든다.

## 포함 범위

- 수정된 정본 소스와 `ramp_dsd_20260916_v2`의 분석·준비·검증 스크립트, 보고서, 그림은 직접 Git에 저장한다.
- 기록 상태·보정/후보 JSON·관측 CSV·명령/검증 기록·LDP/LSA·오류 로그·망/신호/배경·실패 실행 기록은 SHA256으로 중복 제거한 분할 ZIP에 저장한다. `evidence_manifest.json`이 경로와 체크섬을 열거한다.
- 기존9월16일 증거 묶음은 그대로 유지하며 먼저 복원한다. 이번 묶음은 그 이후 `ramp_dsd_20260916_v2` 범위만 더한다.
- 약25GB의 원시 FZP와 native DB/knr/rsr, 재생성 가능한 pickle/cache는 Git에 넣지 않는다. 로컬 원본은 그대로 보존한다. 제외 파일의 경로·크기는 manifest에 있고, 분석에 사용한 FZP의 SHA·처리 행 수는 원래 extraction evidence에 있다.
- 따라서 기록 상태 모델 예측과 저장된 실측 집계 검토는 가능하지만, 원시 궤적을 새 기준으로 전수 재분석하려면 원래 컴퓨터의 FZP를 별도로 옮겨야 한다.

각 part는48MiB 이하이며 개별 SHA와 복원 파일 SHA를 검증한다. 기존 파일 내용이 다르면 덮어쓰지 않고 실패한다. `direct_files.json`은 이번 직접 전달 파일의 내용 pin이고,9월16일 direct manifest는 당시 역사적 pin이다.

추천 후속 진단 설정: `diagnostics/demand_sweep/ramp_dsd_20260916_v2/merge_drain_response_20260919/decisions_v1/internal_cost/config.json`. `entry_and_cost`의 추가 진출 가속 옵션은 보류 후보다.
