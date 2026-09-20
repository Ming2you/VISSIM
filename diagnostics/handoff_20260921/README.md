# 2026-09-21 모델 수정 증분 전달

최신 상태는 [인계 문서](../../docs/HANDOFF_20260921_gain_prediction.md)를 먼저 읽는다. RM/VSL 이득 보정은 NOT_QUALIFIED이며 미채택 후보도 재현과 실패 원인 보존을 위해 포함했다.

저장소 루트에서 Python 환경(numpy 포함)을 준비하고 순서대로 실행한다. 이 명령은 VISSIM을 시작하지 않는다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260919 --restore --verify
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --package diagnostics/handoff_20260921 --restore --verify
python -B -X utf8 diagnostics/handoff_20260921/verify_portable.py
python -B -X utf8 diagnostics/handoff_20260921/verify_latest_records.py
```

`verify_portable.py`는 이번 직접 전달 파일의 SHA256과170개 단위 검사를 확인한다. 마지막 검사는 저장된 비교 결과의 정확 일치·서측 불변·보존·비용 차이를 확인하며 새 예측을 실행하지 않는다. 예전 패키지의 source freeze 검사는 당시 소스를 대상으로 하므로 현재 수정 소스에 그대로 실행해 통과할 것으로 기대하지 않는다.

증거 ZIP은 SHA256으로 중복 제거하고48MiB 이하 조각으로 나눴다. 앞선 패키지와 동일한 증거는 중복 싣지 않는다. 기존 복원 파일이 다르면 restore는 덮어쓰지 않고 중단한다.

원본 FZP·native DB·KNR/RSR·캐시는 Git에서 제외했다. `evidence_manifest.json`의 `excluded_raw`에 로컬 상대 경로와 크기를 남겼다. 원시 차량 분석을 다시 하려면 이 파일을 별도로 옮겨야 한다. 현재 요청은 모델 및 진단 전달이며 원본 수십 GB 전체 업로드가 아니다.

`test_output.log`는 통과한 파일 기반 검사 기록이다. `initial_stdin_test_failed.log`는 Windows spawn 호출 방식 오류를 보존한 것으로 모델 검증 결과와 분리한다. 코드/기본설정/실험 결과를 조용히 바꾸는 자동 복구는 없다.
