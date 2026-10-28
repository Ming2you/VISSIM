# A1 첫 SDMPC 결정(T=900) 점검 선언 — A1 데이터가 생기기 전에 고정 (2026-10-25 KST)

- 무엇: A1(64cf-s29 joint 8,100 s 재현 런 한 번, 한 시드)의 첫 SDMPC 결정 T=900 이 끝났는지, 그 명령이 A0 의 env_hsw T=900 재생 및 codex 기록과 같은지 적는 법.
- 근거: PRE_A1 r2 §4(1·2·5), A0-CMP-1(`work/a0/COMPARE_RULE_A0.md`, a05f2071…) 의 R1–R3 정의, A0b 선언(`work/a0b/COMPARE_RULE_A0B.md`, 6b988a28…) 의 행 목록 꼴.
- 도구: `work/a1/a1_t900_check.py`(sha 는 LOG 에 적음). 두 번째 인자(런 폴더 바꾸기)는 기록끼리 돌린 시험 전용이며 A1 점검에는 쓰지 않음.

## 적는 것

1. 종료와 시간: runlog `CONTROLLER_DECISION sim_sec=T` 줄의 `exit`·`wall_sec`(T = 1, 150, …, 900), `action_000900.decision_budget.json /wall_sec`. codex 같은 칸과 나란히, 배수 = A1/codex.
2. R1 명령 바이트: `action_T.csv` sha256, T = 1, 150, 300, 450, 600, 750(무제어 준비 결정), 900. 900 은 codex 기록과 A0 env_hsw 재생(`a0/out/env_hsw/T000900`) 둘 다와 비교.
3. R2 `joint_written.json` 다섯 칸, R3 `scored_action_token`: T=900, codex 기록·A0 env_hsw 와 각각.
4. 다른 명령 행: 파일 순서로 짝지은 행, 식별 칸(kind·id·dsd_no·sc_no·link·lane) 확인, kind 별 행 수, kind·칸별 최대 |차|, 이산 차 셋(신호 녹색 차 ≥ 1 s, 미터 rate_vph·green_sec 차, VSL speed_kph 차).
5. 입력: `state_000900.json`, `obs150/derived_000900.json` 의 모든 잎을 codex 기록과 비교. 두 런 폴더와 두 동결 뿌리를 같은 이름으로 바꾼 뒤 정확 일치(repr 같음). 다른 잎은 네 부류로 셈: 시계(A0-CMP-1 시계 정규식, 마지막 키), 경로꼴 문자열, 64자리 hex, 그 밖. 그 밖 부류는 예시 40개까지 적음.

## 읽는 법

- 판정 낱말 없음. 같음/다름과 차의 크기만 적음. 한 런·한 시드.
- T=900 이 종료 0 이고 명령 CSV 가 생기면 "T=900 끝남" 으로 적음. 종료 ≠ 0, 시한 유지(hold), CSV 없음은 그대로 적음.
- R1 이 codex 와 다르면 행 목록(4)과 입력 비교(5)를 함께 적어, 차가 입력(관측)에서 왔는지 결정 계산에서 왔는지 가를 근거로 둠. 원인 판단은 [추론] 으로만.
- 이 선언과 도구는 A1 데이터를 본 뒤 고치지 않음.
