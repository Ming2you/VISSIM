# A0 재생 대조 규칙 (A0-CMP-1) — 첫 재생 전에 고정 (2026-10-25 02:20 KST)

대상: codex 64cf-s29 joint 런의 기록 결정 T = 900, 2700, 4950 (한 런, 한 시드).
기록본: `D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29/` 의
`action_T.csv`, `action_T.json`, `action_T.joint.json`, `action_T.joint_written.json`, `obs150/derived_T.json`, `obs150/vsl_cohorts_T.json`.

## 규칙
- R1 명령 바이트: 재생 `action_T.csv` sha256 = 기록 `action_T.csv` sha256. CSV 에는 경로·시계 칸이 없어 제외 없음.
- R2 일곱 필드: 재생 `joint_written.json` 의 `seven_action_fields_sha256`, `ordered_physical_rows_sha256`, `expected_live_metadata_sha256`, `expected_csv_sha256`, `ordered_row_count` 가 기록과 같음.
- R3 채점 토큰: `scored_action_token` 같음. 다르면 R4 결과로 원인 부류를 적음(아래 (c)).
- R4 잎 비교: 위 JSON 넷(+derived, vsl_cohorts)의 모든 잎(dict 키 포함)을 정확 일치(float repr 동일, 허용오차 0)로 비교. 제외 부류는 셋뿐이며, 제외된 잎도 개수·예시를 따로 적음.
  - (a) 시계 잎: 마지막 키가 정규식 `(?i)(wall|cpu|elapsed|perf_counter|timestamp|_utc$|^started|^ended|seconds$|_sec_including_spawn$|^scalar_sec$|^scalar_export_sec$)` 에 맞는 잎. 값이 시뮬레이션 시각으로 보이는 잎이 여기에 걸리면 따로 적음.
  - (b) 경로 잎: 재배치 사상 두 개(`E:\VISSIM_runs\20261012_adopted355_optimized_s29_8100\sdmpc` → `a0\runs\T<T>\sdmpc`, `D:\VISSIM_runtime\20261012_adopted355_vsl_three\frozen\sdmpc31_ca181e84_202610121132` → `a0\code`)를 기록 쪽 문자열·키에 적용한 뒤 비교. `%TEMP%` 아래 임시 폴더 이름(`sdmpc-*`)은 패턴으로 같게 봄.
  - (c) 경로 유래 정체 해시: 재배치로 바뀐 입력(상태 JSON 의 경로 칸)에서 유도된 해시(`derived.inputs.raw_sha256`, 그것을 담은 문서의 sha256·토큰 사슬, 경로가 든 파일의 sha256). 자동 제외하지 않음. 다른 해시 잎을 모두 나열하고 하나씩 사슬 근거를 적음. 근거를 못 대면 "설명 안 된 차이" 로 남김.
- 결과 표기: 같음/다름 개수, 처음 다른 잎. 판정 낱말 없음.
- 속도 후보 대조: 같은 작업 경로(같은 재배치)에서 돈 기준 재생과 후보 재생을 R1–R4 로 비교하되 (b)(c) 는 필요 없음(같은 경로). 제외는 (a) 뿐. 그리고 기록본과 R1·R2 를 다시 확인.

## 선언한 환경 차이 (codex 실행 대비)
- Python 3.12.2 (codex 기록 3.12.14). 의존성 `D:/VISSIM-window264-deps`: numpy 2.3.5, numba 0.67.0, llvmlite 0.49.0, scipy 1.18.1, pandas 3.0.1 (codex `current_environment_20261024.json` 과 같은 판; 당시 판은 codex 도 모름).
- PYTHONHASHSEED=0 (codex 런은 설정 안 함). 그 밖 환경은 codex 러너(run_closedloop3000.ps1:109-117)와 provenance `/env` 의 RW_* 그대로(경로 값만 재배치).
- 입력: 상태 JSON 의 경로 접두 둘만 바꿈. 다른 입력 파일은 바이트 그대로. `mer_index.json`·readback CSV 는 런 끝 판(T 뒤 항목 포함; 코드가 T 뒤를 읽지 않음: `obs150_contract.py:1205-1206` index.get(T), `vsl_exposure_history.py:117` t>=end 에서 멈춤).
- 관측 checkpoint(`lane_observations/observer_checkpoint.json`) 는 원자료에 없어 넣지 않음.
- CPU·부하 다름(이 PC 에서 다른 세션의 VISSIM 폐루프·학습·FZP 스캔이 같이 돎).
