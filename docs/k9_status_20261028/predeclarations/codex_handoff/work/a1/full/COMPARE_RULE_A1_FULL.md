# A1 전체 런 대조 선언 — A1 출력(T ≥ 1,050 결정 내용·FZP·지표)을 읽기 전에 고정 (2026-10-26 KST)

- 무엇: A1(64cf-s29 joint 8,100 s 재현 런 한 번, 한 시드)이 끝난 뒤 (A) 결정 추적, (B) FZP 프레임 대조, (C) 결과 표, (D) 결정 벽시계를 적는 법.
- 근거: PRE_A1 r2 §4·§5(sha `2d9aa15a…`), NOTES D-K9-85·87(`67dcc32b…`), HANDOFF_RESULTS r2 H10–H14(`964a23ce…`), A0-CMP-1(`work/a0/COMPARE_RULE_A0.md`, `a05f2071…`), T=900 선언(`work/a1/COMPARE_RULE_A1_T900.md`, `14349ed9…`).
- 이 선언 전에 본 A1 자료(밝힘): T ≤ 900 의 결정·입력(T=900 점검), 그리고 감시 도구(`work/a1/a1_watch.ps1`)가 읽는 runlog `CONTROLLER_DECISION` 줄의 sim_sec·wall_sec·exit 와 파일 시각. T ≥ 1,050 의 명령 CSV·결정 JSON·상태 JSON·FZP·지표 파일은 이 선언과 도구 sha 를 LOG 에 적기 전에 열지 않음.
- 도구는 모두 `work/a1/full/` 에 두고 sha 를 LOG 에 적음. PRE_A1 §5 의 고정 도구 가운데 런 경로가 파일 안 상수인 것은 "경로만 더한 사본" 으로 씀(`scan_fzp_a1.py` ← `rawcheck/scan_fzp.py` c8a6e5c4…, `metrics_a1.py` ← `rawcheck/metrics.py` b524b51b…, `vhr_firstseen_a1.py` ← `vhr/vhr_firstseen.py` 42e17585…, `unins_a1.py` ← `vhr/vhr_unins.py` fc233013… 의 S_int·dU 그대로). 사본의 차는 경로·짝 목록·`--smoke` 스위치뿐임. 새 도구: `a1_trace.py`, `a1_fzp_firstdiff.py`, `a1_ours.py`(omega701_recount.py 5b7826f6… 의 scan_fzp·integ_ours·integ_codex 를 sha 확인 뒤 import), `a1_table.py`(분할 함수는 metrics.py 글자 그대로), 실행기 `run_a1_analysis.ps1`·`launch_wmi_analysis.ps1`.
- 자기 시험(`--smoke`): A1 자리에 codex joint 기록을 넣어 모든 도구를 먼저 돌림(A1 자료 아님). 기대: 결정 55개 모두 R1 같음·다른 행 0·입력 값 잎 차 0, FZP a1-joint 차 프레임 0, 표의 A1 − LNC 칸 = joint − NC 칸 = RAW_CHECK §5.2·HR §1.1 값(Ω701 −494.7, ④a −449.0, ④b 첫 관측 −221.3, ① −283.7, 입력별 +97.0/−69.2/−249.0), A1 − joint 칸 0. 결과는 LOG 에 적음. 시험에서 도구 결함이 나오면 A1 자료를 읽기 전에만 고치고, 고친 뒤 sha 를 다시 적음.

## A. 결정 추적 (`a1_trace.py`)

- 대상 T: 1, 150, …, 750(준비 결정 6개)과 900, 1,050, …, 8,100(49개). 비교 상대: codex joint 기록(`D:/VISSIM_handoff/20261024/raw/joint/sdmpc`). T = 1,050–2,550 은 A0b 재생 출력(`a0/out/a0b_hsw`)과도 R1·다른 행을 적음.
- 결정마다 적는 것:
  1. runlog: `CONTROLLER_DECISION` exit·wall_sec, exit ≠ 0 이면 stderr 앞 300자, `DECISION_HOLD_ATTEMPT` 원인 줄, `DECISION_HELD_PREVIOUS`, `ERROR=` 줄. 결정 JSON 의 `controller_status`(유지면 `hold_previous_error`), `action_T.error.txt` 마지막 줄.
  2. R1 명령 CSV sha 같음, R2 `joint_written.json` 다섯 칸, R3 `scored_action_token`(R3 은 A0 이래 늘 달랐음; 수치 근거로 쓰지 않음).
  3. 레버별 명령: 미터 8개 각각의 rate_vph·green_sec(A1·codex 나란히), VSL 의 서로 다른 속도값 목록과 속도 다른 행 수, 신호(signal·signal_sg) 다른 행 수·다른 SC 목록·최대 |녹색 차|·최대 |offset 차|(선형, 주기 감싸기 보정 없음)·녹색 차 ≥ 1 s 칸 수·≥ 0.01 s 칸 수·offset 차 ≥ 1 s 칸 수. 유지 표지(`hold_previous_error=1`) 행 수.
  4. 입력: `state_T.json`, `obs150/derived_T.json` 의 모든 잎. 두 런 폴더·두 동결 뿌리를 같은 이름으로 바꾼 뒤 정확 일치(repr). 다른 잎을 다섯 부류로 셈: 시계(A0-CMP-1 정규식), 경로꼴, 64자리 hex, 부속(마지막 키가 run_id·byte_start·byte_end·max_t_any — T=900 에서 기록 부속으로 본 네 키), 값(그 밖). 값 부류는 수, 숫자 잎 최대 |차|, 최상위 키별 수, 예시 30개.
  5. 결정 JSON 의 selection_status·selected_objective·held_objective·prediction_ttt_reduction, selected_objective 차.
- 요약: 처음 R1 이 다른 T, 처음 상태 값 잎이 다른 T, 처음 derived 값 잎이 다른 T. T 별 성장 표(다른 행 수, kind 별, SC 수, 최대 녹색·offset 차, 미터·VSL 차, 상태 값 잎 수와 최대 차). 유지 결정의 T 와 원인(A1·codex 따로).
- 읽는 법 [PRE_A1 U9]: A1 의 처음 다른 T 가 A0b 의 처음 다른 T(1,200)와 같은지, 앞인지, 뒤인지를 적음. 원인 판단은 [추론] 으로만.

## B. FZP 프레임 대조 (`a1_fzp_firstdiff.py`)

- 짝: A1–joint(주), A1–LNC, joint–LNC(맥락). 프레임 = 같은 SIMSEC 글자의 연속 데이터 행. 차량 번호로 짝지은 LF 행 바이트 비교, t ≤ 8,100.
- 적는 것: 895.1 s 까지 같음 여부, 처음 다른 프레임의 t·행 수·한쪽에만 있는 차·내용이 다른 차·그 링크 상위 20, 150 s 구간별 다른 프레임 수와 프레임 안 최대 다른 차량 수. 접두 sha(≤ 895.1 s) `f1a0b040…fbcda` 는 `scan_fzp_a1.py` 출력으로 따로 확인.

## C. 결과 표 (`scan_fzp_a1.py` → `metrics_a1.py` → `vhr_firstseen_a1.py` → `unins_a1.py` → `a1_ours.py` → `a1_table.py`)

- 주 적분 꼴: codex 꼴 0–8,100 s(빈 망에서 시작, 마지막 프레임 재고를 8,100 까지 유지). 보조: 우리 꼴 0–8,100 s(링크 칸만, OM integ_ours).
- 칸: Ω701, Ω635(`previous_inside_links` 635개), Ω701 − Ω635, 링크 66, ④a, ④b, ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω, Ω 밖 (b) = ④a − Ω(Ω701·Ω635 둘 다), ① FW_E 본선 7링크, ② 국소 19링크, 도시도로 codex 분할과 우리 분할(미터 상류 링크 70·68·129·31 → 동측 진입, 124·32·121·69 → 서측 진입), 진입램프 E·W 두 분할, 입력별 ④b(1098 = 첫 관측 링크 74, 1099 = 링크 26, 도시 = 그 밖).
- 열: A1, LNC, **A1 − LNC**, codex joint, codex NC, **joint − NC**, A1 − joint. 링크 칸의 NC 수준은 codex NC 스캔(LNC 와 데이터 행 같음; 표 도구가 링크별 차를 다시 확인).
- ④b:
  - 수준값: A1·joint = native DelayLatent(0–8,100)/3,600. NC·LNC = 경로 A 16,643.4 / 경로 B 16,644.9(`rawcheck/uninserted2_out.json`). 백분율 분모는 경로 B 수준(첫 관측과 같은 NC 수준, VH 0-3).
  - 짝 차 주 값 = 첫 관측 차분(HR H14, D-K9-87): A1 − LNC, joint − NC, A1 − joint. 참고 값 = A1 native − NC 수준(경로 A·B). A1 − joint 는 첫 관측 차분과 native 차를 나란히 적어 방법 점검으로 씀.
  - 같은 도착열 점검: 입력 링크 74 의 8,100 s 까지 첫 관측 수(codex 16,070), 1099 도착 = 링크 26 첫 관측 수 + `.err` remain(codex 20,166), LNC 첫 관측 = codex NC 첫 관측.
  - stage-1 재구성은 이번 표에 넣지 않음(PRE_A1 §5 의 참고 열; 계산하지 않았다고 적음).
- ④·Ω 밖 (a) 짝 차는 ④a 짝 차 + 첫 관측 ④b 짝 차. 수준값 칸의 ④ 는 native(A1·joint)·경로 B(NC) 로 적고 경로 A 는 따로 둠.

## D. 결정 벽시계

- runlog `CONTROLLER_DECISION wall_sec`(VBS 잼)와 `decision_budget.json /wall_sec`(python 잼), A1·codex 나란히, 배수 = A1/codex. 합·최대·> 1,500 s·> 1,800 s 수, 시한 유지 수(exit −2 또는 `EXEC_TIMEOUT`).

## 읽는 법

- 판정 낱말 없음. 한 런·한 시드(A1), 비교 상대도 한 런씩(codex joint, LNC). 같음/다름과 차의 크기만 적음. Ω 숫자는 늘 ④·Ω 밖과 함께 적음.
- A1 파일이 없거나 도구가 실패하면 그대로 "없음/실패" 로 적고 다른 값으로 메우지 않음.
- 이 선언과 도구는 A1 자료를 본 뒤 고치지 않음. 고칠 수밖에 없으면 멈추고 보고함.
