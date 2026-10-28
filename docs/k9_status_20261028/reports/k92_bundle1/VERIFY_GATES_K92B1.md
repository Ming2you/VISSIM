# K9-2 묶음 1 관문 보고 독립 검증 (VerifyGates, 2026-10-21)

- 검증 대상: `KB/GATES_K92B1.md` sha256 `63dd35e29ced298c9e7538f0aeefe7e48871e6197285b3994fa2e51683a03b60` (상태 STOP) [실행 sha256].
- 결과: **STOP을 확인합니다.** 보고서가 낸 판정 값은 내 코드로 다시 계산해도 모두 같습니다. F 단계의 멈춤 원인도 s47 없이 다시 만들어 확인했습니다. 그래서 pass = false입니다(F·J-b가 아직 없음).
- 단, 내 쪽에 공개할 것이 있습니다. (1) 미리 고정한 비교 규칙으로는 대표 잡 두 개의 다시 돌리기가 "DIFFERENT"입니다. 차이는 모두 출력 폴더 경로에서 나온 해시와 시간 값으로 설명됩니다(§7). (2) 내 J-a 도구에 결함이 있어 데이터 뒤에 고친 사본을 썼습니다. 이것은 보충 24 S-K12(독립 검증기를 데이터 뒤 바꿈)에 걸립니다. 두 결과를 모두 적습니다(§9).
- 이 보고는 교통 성능 판정을 하지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다.
- 표시: [실행] 이번에 내가 돌리거나 계산함, [읽음] 문서·코드·기록에서 확인, [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. VG = `KB/vgates`(이 검증의 도구·출력).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. OUTK = `OK2/k92t`(판정 단계 출력). VG2 = `OK2/vg2t`(내 다시 돌리기 출력, 새 폴더).
- TREE = `D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t`(git archive K9-2-5 `e27ceac8`). V4 = `D:/VISSIM-merge/k8_gates_out_v4`(K9-1 판정 산출).
- k92t = 보충 24 §5의 판정 단계. J = K9-1 판정이 그대로인지 보는 관문(J-0 정적, J-a 기준 확인, J-b 판정 잎). F = 충실도 관문. VR = VISSIM 기준 도구 `k92_vissim_ref.py`.
- SAF-K91 = K9-1 판정 팔(`5f0d0e40…`). SAF-K92b1 = 두 키(W·H-b)를 더한 팔(`65cac7ea…`). BASE = K9-1 기준 팔(`319d07aa…`).
- W = SC109 서측 직진 용량 키(5209.8). L = 좌회전 movement `SC109_W_SC108_to_N_SC16`. 씨앗 = H-b 하한 값 1045.1612903225805.
- HARD = 반드시 같아야 하는 결정 잎. 결과 넷 = PASS / FAIL / 보류 / INCOMPLETE(보충 21 §6.4).

## 0. 고정점 확인 [실행 sha256]

- 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…` = 각 `.sha256` 파일 = 각 `AMENDMENT2x_FIXED.md` 표 값.
- 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `abe3cc05…`(작업 지시의 A29 값과 같음).
- 판정 단계 고정 목록 `KB/k92t_pins.sha256` `38a2ce14…` 56/56 OK(시작 때와 끝 때 두 번). 구동기 `b07ffb56…`·판정기 `eb4c113a…` = 보고서 값.
- 판정 단계 산출 sha = 보고서 값: `k92_judging_stage.json` `34e63a99…`, `start/scans.json` `410fde88…`, `judge/j0.json` `24ee9d3b…`, `judge/ja.json` `74806cb0…`, `judge/jwall.json` `1fb5c604…`, `STOP_f.json` `ebff59c9…`, `steps.jsonl` `7edd53c9…`(59줄), `driver.log` `8140fd2f…`, `stages/{start,prep,j0,ja}.json` `f3ed1dce…`/`9ef3a7ed…`/`3845def6…`/`b40593bb…`, 스냅숏 s27 `fabe7d5e…`.
- 내 도구는 데이터 전에 sha를 LOG에 고정했습니다(`KB/LOG.md` 2026-10-21 "VerifyGates: 내 도구 고정" 항목, 목록 `VG/vg_pins.sha256`). 데이터 뒤에 만든 도구 셋은 따로 공개합니다(§9).

## 1. 한눈에

| 관문 | 보고서 값 | 내 다시 계산 | 같음 | 근거 (출력 sha256) |
|---|---|---|---|---|
| 커밋 관문 K9-2-0…3 | 단계 모두 PASS | gates.json 4개 sha = 기록, 단계 40개 모두 PASS, 단계 목록 = 보충 24 §4.4 | 같음 | `VG/out/commit.json` `70f23db3…` |
| G-K5 (K9-2-1·2) | 중앙 0.98999·0.99505 PASS | 원자료 요약 16개에서 다시 냄: 0.9899949870786262·0.995050862095435, 깨끗한 짝 8/8씩, 사분위 0.01519·0.00958(보고만) | 같음 | 같은 파일 |
| 판정기 고침 K9-2-4·5 | R-old 184, RJ-G2 9, RJ-G4 12 PASS | 기록 a27·a29 단계 모두 PASS; VerifyImpl r3 다시 계산(`items.jsonl` `5d400482…`) R-old 184/184 PASS, G-K2 9/9 PASS | 같음 [읽음 r3] | 같은 파일 |
| k92t 시작 훑기 | 봉인 12,538 다름 0, 새는 줄 0, s47 VISSIM 값 0, 주 표본 이름 0 | 같음(아래 §3) | 같음 | `VG/out/scans.json` `0d40d55f…` |
| J-0 | 105/105 PASS, 61 = 59 + 같은 실패 2 | 103 PASS + 같은 실패 2(T=1·150), 씨앗 묶임 7상태 같음 | 같음(조작화 기준). 글자 그대로는 59/61 | `VG/out/j0.json` `cf9c1d0d…` |
| J-a | 23/23 같음 | 잡 21 SAME, 결정 2 PASS(고친 사본). 고정 도구는 결정 2 보류(내 결함) | 같음(§9 공개) | `VG/out/ja2.json` `7c08e358…`, `VG/out/ja.json` `e2dfecf3…` |
| J 잡 벽시계 짝 | 11/11, 중앙 0.98010 ≤ 1.01575 | 11/11, 중앙 0.9800955989161412, 사분위 0.030372, 범위 0.9484–1.0350 | 같음 | 같은 두 파일 `jwall` |
| F | INCOMPLETE (STOP) | STOP 기록·멈춘 자리·원인 확인, 원인을 s43으로 다시 만듦 | **STOP 확인** | `VG/out/f.json` `9cf1bcea…`, `VG2/vr600.jsonl` `5a55c349…` |
| J-b·사후 | 돌리지 않음 | 출력 없음 확인 | 같음 | `VG/out/f.json` |
| 대표 잡 다시 돌리기 2개 | (검증 몫) | 고정 규칙 DIFFERENT, 차이 = 경로 해시·시간 값뿐 | §7 | `VG/out/rerun_cmp.json` `3988be6e…` |

## 2. 커밋 관문 기록 [실행 `VG/vg_commit.py`]

- gates.json 6개 sha = 보고서 값: K9-2-0 `04a5f316…`, K9-2-1 `dbf64493…`, K9-2-2 `176dd263…`, K9-2-3 `064d1b4b…`, a27 `e57f1b36…`, a29 `129b642d…`. 모든 단계 verdict = PASS.
- G-K5를 원자료에서 다시 냈습니다. 짝 = 상태마다 (A0, B1)·(A2, B3), 깨끗함 = 시작 때 VISSIM 0·전 0·뒤 0·launch 0·재생 종료 0, 비 = `replay_run.wall_sec` B / A. 중앙은 기록 `gates/gk5.json`과 비트로 같습니다. 문턱 1.0157507938976496 아래입니다.
- GWT8: head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 `b9734abe`, `b9734abe..HEAD` 6커밋이 K9-2-0…5 순서, 작성자 `Ming2you <alsrjsrb1915@snu.ac.kr>`, 6개 모두 `Co-Authored-By` 끝 줄, status 0줄, 원격 k92 참조 0.
- R-old·RJ-G2·RJ-G4는 다시 비교하지 않았습니다. VerifyImpl r3가 어제 하네스 없이 다시 냈고(184/184, 9/9, 결정 8행), 그 출력 sha가 LOG 기록과 같습니다 [읽음 `KB/VERIFY_IMPL_r3.md` `c242792f…`].
- 공개: 내 `vg_commit.py`는 r3 출력의 판정 칸을 잘못 골라 R-old를 "PASS 167·보류 17"로 셌습니다(보류 17은 무리 R의 새 쪽 보고 판정). R-old 판정 칸(`rold_mine`)으로 다시 세면 184/184 PASS입니다 [실행, 도구는 고치지 않고 따로 읽음].

## 3. k92t 시작 훑기 [실행 `VG/vg_scans.py`, 2,139 s]

| 항목 | 정의 (보충 25 §6.5, 보충 24 §3.1-3b, S-K10) | 내 값 | 보고서 값 |
|---|---|---|---|
| 봉인 sha 대조 | `OK2/sealed_s47` 모든 파일 sha 다시 계산 = 목록 | K9-2-0 3,573·K9-2-1 4,072·K9-2-2 4,072·K9-2-3 821, 빠짐·더함·다름 0, 실행 수 5·9·9·3 = 목록, a27 1파일(크기 0) 같음 | 같음 |
| 새는 줄 | 선언 뿌리의 줄에 잡 이름 꼴 + (값 꼴 또는 잡 줄 꼴) | 0줄(지금 29,333파일; 시작 뒤 바뀐 11파일 포함), 보고만 a27·a29 908파일 0줄, 대조 문자열 5개 맞음 | 0줄(29,325) |
| §3.1-3b | 봉인 밖 JSON의 s47 VISSIM 값 | 0(JSON 29,988, VR 파일 2, 기록 96, s47 기록 0) | 같음 |
| 주 표본 이름 | OK2(k92t 뺌)·`k8_gate_trees/k92b1` 이름 | 0(지금 1,205,247개; 늘어난 254개는 내 출력·스냅숏) | 0(1,204,993) |
| §5.4 파일 시각 | 주 표본 폴더가 k92t 시작(21:45:53) 뒤에 생김 | 세 F 팔 모두 포착·잡·재생 22개씩, 가장 이른 시각 22:23:49, 뿌리 생성도 시작 뒤 | (보고서에 없음) |

- 내가 더 본 것: 실행마다의 파일 목록 대 최종 목록. K9-2-0·1·2에서 `plant/new/commit_gates.log`와 `sa/k91_history_copies.json`만 다릅니다. 같은 출력 뿌리에 뒤 실행이 덧붙인 파일이고, 최종 목록은 마지막으로 쓴 실행과 같습니다 [실행, 목록 파일만 읽음]. 위반이 아닙니다.
- 봉인 뿌리 안의 데이터·로그는 열지 않았습니다(sha만). 봉인 뿌리 `k92_record.json` 훑기는 J·F 값 고정 뒤로 미룬 조작화 7과 같게 하지 않았습니다.

## 4. J-0 [실행 `VG/vg_j0.py`]

- 105상태 = TL3m 27(s31·s43·s47 × GRID9) + DP 17 + R-obs3 61. 팔: SAF-K91 = `OUTK/ja`, SAF-K92b1 = `OUTK/jb`.
- 내 코드는 하네스를 부르지 않습니다. 용량은 `template.pickle`을 내 대체 클래스 언피클러로 읽었습니다.
- 결과: 103상태 PASS. 메타 7개 같음, SA 초기 상태(구성원·포트·127·`SC1001_W_out`, 그리고 install_check 전체·initial·probes.sa·records) 같음, install_check 통과 양쪽, `posthead_veh` 같음.
- 용량 차이 키: W만 96상태, W + L 7상태. 7상태 = ROBS61 300·450·600·750, TL3m s43 900, s47 900·1,200 = 새 쪽 메타 `k92_hb_seed_binding` = 1.0인 상태와 정확히 같음. W 새 값 repr `5209.8`, L 새 값 repr `1045.1612903225805`.
- 한쪽 메타 = `k92_w`·`k92_hb`·`k92_hb_seed_binding`(새 쪽)뿐.
- ROBS61 T=1·150: 두 팔 모두 같은 실패. 예외 줄과 런타임 프레임 4개가 같고, ja↔jb 뿌리만 바꾸면 오류 글 전체가 같습니다. T=1 = `FileNotFoundError … __missing_previous.json`, T=150 = `ValueError: Previous command must be the immediately preceding action in this run`.
- 두 가지 읽기:
  - 조작화 1(같은 실패를 61에 셈): 59 + 2 = 61 → PASS. 보고서와 같음.
  - 보충 24 :324 글자 그대로("초기화 61/61 오류 0"): 59/61 → FAIL. K9-1 기록 `gates_k91t.json` G-EB-14 `i_init`도 시드마다 59/59이고 T=1·150은 따로 보고했습니다(보충 13 :26) [읽음]. 그래서 글자 그대로는 어느 팔이든 성립하지 않는 자리입니다. 사용자 결정 Q2 몫입니다.

## 5. J-a와 J 잡 벽시계 짝 [실행 `VG/vg_ja.py`, `VG/vg_ja2.py`]

- 잡 21개(V4 k91t 대 `OUTK/ja`): 숫자 잎 전부(하네스 G5 규칙보다 넓게)를 비교했습니다. 공통 숫자 잎 7,730–142,350개. 다른 숫자 잎은 `/wall_sec`(17잡)와 장기 잡의 `/segment_sec[*]`(4잡)뿐, 모두 시간 값입니다. 한쪽 숫자 잎 0. 새 쪽 ok 21/21. 다른 글자 잎 3개(`/job/tree`·`/job/template`·`/job/forecast_long`, 트리 이름·경로)뿐입니다. → 21/21 SAME.
- 결정 2개(full 2700 hooks SAF·BASE): 보충 21 §6 규칙을 내 코드로 새로 짰습니다(N + 보충 27 K92-N, HARD H1–H5, V·R3·F, D 빼기, A_K92는 보충 29 §2.2 네 조건).
  - 고정 도구 `vg_ja.py`: 두 결정 모두 보류(미분류 4 = CAO 키 2, RS 키 2). 원인은 내 결함입니다. 사전 키에 `/`가 든 경로(`<root>/evaluation/…`)를 문자열로 다시 찾다가 값이 None이 되었습니다(`vg_ja.py:113-125`, `:250`).
  - 고친 사본 `vg_ja2.py`(키 묶음으로 찾기만 고침): 두 결정 모두 **PASS**(HARD 같음, 미분류 0). H1 CSV 같음, 진행 기록 끝 줄 같음. CAO 새 값 = 새 트리 CAO sha. RS(A_K92): 새 값 `70cca680…` = 새 트리 RS, 옛 값 `8a5aec79…` = k91t 트리 RS, 아는 다섯 값 안. `run.json` objective·held_objective·exit·csv_sha256 같음.
  - 분류 개수: SAF V 7·F1 12·F3 30·R3-08 2·A_K92 2·R3-01 2·R3-03 2, BASE는 여기에 R3-05 2·F3 32. 판정기 기록은 V 6입니다. 내 V에는 HARD 안의 `/prediction/wall_sec`가 들어 있습니다 [추론: 판정기는 이 잎을 허용 개수에 넣지 않음]. 판정에는 영향 없습니다.
- J 잡 벽시계 짝: 11짝 모두 깨끗함(VISSIM 개수 넷 0, 종료 0, ok 양쪽), A가 끝나고 0.4–0.5 s 뒤 B 시작. 비 = 0.9637, 0.9760, 1.0350, 0.9735, 0.9883, 0.9995, 1.0176, 0.9484, 0.9766, 0.9801, 1.0107. 중앙 0.9800955989161412 ≤ 1.0157507938976496 → PASS. 사분위 범위 0.030372(보고만).

## 6. F 단계 STOP 확인

- 기록 [실행 `VG/vg_f.py`]: F 단계의 14단계가 차례대로 있고, `f_persist`만 rc=1(마지막 단계, 23.7 s), 나머지 rc 0, 모든 단계 VISSIM 0. `STOP_f.json` = {stage f, why "persist rc=1"}. `judge/f.json`, `stages/f.json`, `judge/jb.json`, `stages/jb.json`, `stages/post.json`, `jb/sa/gates/gates_k92t.json`, `f_persist/sa/k92_vissim_ref.json`, `judge/sealed_records.json` 모두 없음. STOP 파일은 하나. 끝난 단계 = start·prep·j0·ja.
- 있는 F 데이터 [실행, 이름·있음만]: 세 팔 모두 포착 38(capture.json 있음, capture_failed 없음)·잡 38(summary.json·k92_record.json 있음). 둘째 표본(s31·s43) 16잡은 summary `ok` 칸만 읽어 16/16 참. 팔 sha: f_off `5f0d0e40`, f_w `d179f01d`, f_b1 `65cac7ea` = 선언. `f_vref` sha `09f9194b…` = 보고서 값(열지 않음). s47 잡의 ok 값은 블라인드 때문에 열지 않았습니다.
- 원인 [읽음 + 실행]:
  - 지속성 상태 = 주 표본 T − 450: 600, 1200, …, 7950. 그중 600만 900 아래입니다.
  - VR이 쓰는 U4 측정기는 `T_FROM = 900.0`(`k8b/u4/derive_head_saturation.py:72`)이고, 시작이 900 아래인 창을 버립니다(`:379`). 그래서 창 (600.1, 750.1]의 주기가 0개가 되고 VR이 SystemExit 합니다(`k92_vissim_ref.py:119-122`).
  - 다시 만들기 [실행 `VG/vg_vr600.py`, VG2]: 같은 VR로 v3c3-s43 T=600 → rc 1, 끝 줄 "K92 VISSIM ref s43 T=600: window (600.1, 750.1) found 0 times for 1090201". 대조 T=1050 → rc 0. 그래서 원인은 자료가 아니라 측정기 범위입니다. 보고서의 [추론]을 실행으로 확인했습니다. s47은 쓰지 않았습니다.
- STOP 근거:
  - 멈춘 것은 구동기 코드입니다: `must()`가 rc≠0이면 무조건 멈춤(`k92t.py:248-250`, `:632-634`).
  - 보고서 §3은 O7을 "단계 안의 실행이 rc≠0이면 STOP"이라고 적었습니다. O7 글(`k92t.py:51-52`)은 "판정 입력을 빠뜨리는 rc≠0"입니다. F 판정 값은 `f_persist`를 읽지 않습니다(`k92t_judge.py:759-767`; 지속성은 `:774-782` 보고만). 그래서 O7 글만으로는 근거가 좁습니다.
  - 그래도 STOP은 맞습니다. 지속성 MAE는 보충 24 §5.3에 선언된 보고 항목입니다(:347). 그 출력이 없으므로 §6 INCOMPLETE("출력 없음·실행 미완 → STOP·보고", :365)입니다. 이어 가려면 데이터 뒤에 구동기를 바꿔야 하므로 S-K12(:400)입니다. 작업 규칙도 "FAIL·INCOMPLETE면 STOP"입니다.
- Q1에 보탤 사실 [읽음·실행]: (나) "F 처음부터"를 같은 구동기로 하면 같은 자리에서 다시 멈춥니다. 어느 길이든 지속성 보고를 바꿔야 합니다. (가)로 T−450 ≥ 900만 쓰면 지속성 보고는 21상태(1050 빠짐)가 됩니다. F-1–F-3 판정 값은 지속성과 무관합니다.

## 7. 대표 잡 두 개 다시 돌리기 [실행 `VG/vg_rerun.py`, WMI 분리·BelowNormal·PYTHONHASHSEED=0·python -B]

- 고른 것: J = jb(SAF-K92b1) `TL3_900_SAF_OBS_H3`. J-b는 돌지 않았으므로, J-b의 tl3 가족이 판정할 것과 같은 잡(J 짝의 B 잡)을 골랐습니다. F = f_b1 `TL3_1050_s43_SAF_OBS_H3`(둘째 표본). s47 주 표본은 블라인드 때문에 고르지 않았습니다.
- 방법: 새 뿌리 `VG2/{jb,f_b1}`에 V4 입력 사본 → prep → 팔(`sa_arms.py --k92b1`) → 포착 → 잡(`k92t.py child`, 구동기와 같은 라이브러리 호출·env). 7단계 모두 rc 0, VISSIM 0, 합 약 3.5분. TREE에 새 파일 0.
- 비교 규칙(데이터 전 고정, `vg_cmp.py` 머리말): 뿌리 이름 바꾸기(`vg2t`→`k92t`, 길이 같음) 뒤 바이트 같음, 아니면 시간 잎(L_T 55개 + 몇 개)만 다를 때 설명됨.
- 결과: **고정 규칙으로 J·F 모두 DIFFERENT.** 파일 수는 양쪽 같음(J 39, F 40).
  - 같음(뿌리 이름 바꾼 뒤): prep 상태 파일 `state_*.json`·프레임·obs150 파일 등(J 19/21, F 20/22), 팔 파일 2, 포착 5파일(coord·forecast_long pickle 등), 잡의 `k92_record.json`·`k91_record.json`·`k92_series.npz`·`job.pickle`.
  - 시간만 다름(규칙상 설명됨): 잡 `summary.json`(`wall_sec`), `result.pickle`(`wall_sec`·`scalar_sec`), `vissim_counts.json`.
  - 규칙상 DIFFERENT 6파일: `replay_manifest.json`, `obs150/derived_*.json`, `capture.json`(`template_sha256`), `template.pickle`, 포착 `action_*.joint.json`(4잎), 잡 `log.txt`(1줄).
- 데이터 뒤 설명(공개, 판정은 바꾸지 않음) [실행 `vg_cmp_diag.py`, `vg_cmp_diag2b.py`]:
  - 경로에서 나온 해시: 매니페스트 `raw_sha256/replay`와 derived `inputs/raw_sha256` = 각 쪽 `state['obs150']` 정규 JSON의 sha이고, 그 객체는 뿌리 경로만 바꾸면 같습니다. `state/replay_sha256`·`source_sha256/<상태 파일>`·`runtime_sources/<상태 파일>` = 각 쪽 상태 파일 sha(두 파일은 뿌리만 다름). `template_sha256` = 각 쪽 template 파일 sha. `runtime_sources` 1,089개 중 다른 것은 상태 파일 하나뿐. `source_fingerprint` = 각 쪽 `runtime_sources`의 pickle sha(`area_follower_objective.py:1776`).
  - `parallel_transport_token`: 입력에 bootstrap 바이트와 `source_fingerprint`가 들어감(`area_follower_objective.py:829-830`) [읽음; 값 재계산은 안 함, 그래서 이 잎은 추론].
  - 시간 값: `worker_cleanup_wall_sec`(내 시간 목록에 없던 이름), `log.txt`의 `continuous_scalar_done <x>`의 x = 각 쪽 `scalar_sec`(perf_counter 경과 시간, `sdmpc_tangent_worker.py:303-307`).
- 해석 [추론]: 출력 뿌리가 다르면 같은 바이트가 될 수 없는 잎들입니다(OUTK에 쓸 수 없으므로 피할 수 없음). 결정·잡 결과 값은 비트로 같습니다. 그러나 미리 정한 규칙 결과는 DIFFERENT이므로 그대로 적습니다.

## 8. 문턱 = 고정 보충 [읽음]

| 항목 | 고정 보충 | 판정 단계 값 | 같음 |
|---|---|---|---|
| J 잡 짝·G-K5 중앙 | ≤ 1.0158 = 1.05 / 1.033718118959995 = 1.0157507938976496 (보충 24 :290, :328; 보충 26 :117, D-K9-47) | `k92t_judge.py:110`, `gk5.json` limit 1.0157507938976496 | 같음 |
| 사분위 범위 | 보고만 (보충 26) | 보고만 | 같음 |
| F-1·F-2·F-3 | MAE_B1 ≤ MAE_OFF, \|편향_B1\| ≤ \|편향_OFF\|, 편향 차 ≤ +5 (보충 24 :343-345) | `k92_gates.py` `f_judge` :876-878. 함수 글은 K9-2-0과 K9-2-5에서 같음(sha16 `c37738ae`) | 같음 |
| F 표본 | 주 22, 둘째 s31 8·s43 8 (보충 24 :336-337) | `k92t.py:132-134`, `k92t_judge.py:98-100` | 같음 |
| J-0 메타 7·W·씨앗 | 보충 24 :324, D-K9-34, H-b | `k92t_judge.py:104-108` | 같음 |
| J-b 판정 파일 | `gates_k91t.json` `4e59f61d…`, G-EB-2…8·13·14 (보충 24 :326) | `k92t_judge.py:92-94`, 파일 sha 같음 | 같음 |

## 9. 찾은 것과 공개

1. **[관찰] 보고서의 O7 인용이 넓음.** §6 둘째 덩어리. STOP 자체는 보충 24 §6 INCOMPLETE·S-K12로 맞습니다. 보고서 글은 고칠 몫입니다.
2. **[관찰] F 잡 "ok 38/38"을 센 방법이 LOG에 없음.** 보고서는 "구동기 줄로만 셈"이라고 적었습니다. 그 줄(`K92T_JOB`)은 `OUTK/logs/f_*_jobs.log`에 있고, 같은 파일에 v3c3-s47 잡의 `SA_JOB … objective=` 줄도 있습니다(`k92t.py:227-229`, `sa_jobs.py:385`) [읽음 코드; 파일은 열지 않음]. 보충 25 §6.4는 걸러 읽기도 "엶"으로 보고, k92t 안에서는 J·F 값 고정 전 실패 진단에만 열게 합니다(:447, :449). 이 규칙이 k92t 자신의 s47 로그에 걸리는지는 보충 글이 분명하지 않습니다(§6.1–6.3은 k92t 전 실행, 보충 26 :356). 사용자가 볼 몫입니다 [추론]. 나는 이름·있음만 셌습니다.
3. **[관찰, 작음]** 실패 진단으로 `f_persist.log`를 연 기록의 시각이 "07:0x"입니다. 보충 25 §6.4는 파일·시각·목적을 적게 합니다.
4. **[관찰, 작음]** TREE에 지금 `evaluation/controllers/__tangentcache__/*.mcode` 90개가 더 있습니다(J-a 때 00:15·01:53에 생긴 실행 캐시). 커밋 파일 10,569개는 모두 블롭과 같습니다(그대로 5,813, CRLF만 다름 4,756, 다름 0, 빠짐 0). 판정기 블롭 19/19. 보고서의 "10,569파일·k925와 같음"은 만들 때 기준으로 맞습니다 [실행 `VG/vg_tree.py`, `VG/out/tree.json` `8f07e2ce…`; 내 도구 규칙은 캐시 폴더 이름을 몰라 ok=거짓].
5. **[관찰, 작음]** 판정기 머리말은 `f_judge`를 "K9-2-0 blob, unchanged since"라고 적었습니다. 파일 블롭은 K9-2-4·5에서 바뀌었고, 함수 글은 같습니다.
6. **[공개] 내 도구 결함과 데이터 뒤 변경.**
   - `vg_ja.py`(결정 비교의 값 찾기) → 고친 사본 `vg_ja2.py` `eb0dacbc…`. 보충 24 S-K12는 독립 검증기의 데이터 뒤 변경을 STOP·사용자 몫으로 둡니다. 고정 도구 결과(보류)와 고친 결과(PASS)를 모두 적었습니다. 고친 것은 경로 찾기뿐이고 규칙·문턱은 같습니다.
   - `vg_cmp_diag2.py` 첫 실행은 셸이 백슬래시를 먹어 뿌리 바꾸기가 작동하지 않았습니다(무효, 보관). 고친 사본 `vg_cmp_diag2b.py` `3ec7614a…`로 다시 냈습니다. 설명용 도구이고 판정 도구가 아닙니다.
   - `vg_cmp.py` 시간 목록에 `worker_cleanup_wall_sec`와 `log.txt` 시간 줄이 없었고, 뿌리에서 나온 해시를 예상하지 못했습니다. 규칙 결과(DIFFERENT)는 바꾸지 않았습니다.
   - `vg_commit.py`의 r3 개수 칸 잘못 고름(§2).

## 10. 지킨 것 [실행]

- VISSIM·COM·러너·동결 0. 커밋·브랜치·푸시 0: GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`.
- 봉인 시드 37/59/61/67 0. codex 64cf 숫자 0. 봉인 뿌리의 로그·데이터 파일 열람 0(sha만). v3c3-s47 결과 값 열람 0: F s47 잡 summary·k92_record·`f_vref` 내용·`OUTK/logs/f_*` 모두 열지 않음. 내가 연 s47 자료는 J 상태(GRID9 포착·J-a 잡 900)뿐이고, 이는 K9-1 판정 상태입니다.
- 쓴 곳: `VG`, `VG2`(새 폴더), `OK2/snap/vg1_before.json`·`vg2_after.json`, `KB/LOG.md`(덧붙임만), 이 보고서. `OUTK`는 07:09 뒤 바뀐 파일 0, TREE는 07:29 뒤 새 파일 0.
- 스냅숏 `vg1_before` `ee575983…`·`vg2_after` `5ee9cc79…` 모두 s02 대비 SAME. 고정 목록 56/56 OK, 내 목록 OK.
- 금지 시험 0, 시험 실행 0. 한 번에 무거운 일 하나, 모두 WMI 분리·BelowNormal. 끈 프로세스 0. 끝에 python·VISSIM 0. C: 37.5 GB, D: 395 GB.

## 11. 파일

| 파일 | sha256 |
|---|---|
| `VG/vg_pins.sha256` (도구 15개) | `8d1307c5669ed3a27d5ac5a9ada13f087f750397a1e5008f637164f6b8f7a3a3` |
| `VG/out/commit.json` | `70f23db3675af4f398a3bf432c24b61b9a759bed975eadd676d5fb3c108fc37f` |
| `VG/out/scans.json` | `0d40d55f113edc5ad1750091c70650497ab1b1b4fc24990d6f5f547e5c6e8bff` |
| `VG/out/j0.json` | `cf9c1d0dba4335384c18f8f256c3a8ff4f0665bf6d3850c711918139ce9dba73` |
| `VG/out/ja.json` (고정 도구) / `ja2.json` (고친 사본) | `e2dfecf34b11a742a56084c96ed89c598965befa8fd717e7895e6e999a4b6212` / `7c08e358795c6e9fb37c71861b8891c8d24f74d6dc503afc5cf7da2f5862decc` |
| `VG/out/f.json` | `9cf1bcea4169eca64fd79d926dd73073420bd638683af7d0a06b21ee5e8a1af5` |
| `VG/out/tree.json` | `8f07e2ce36f2ec5b9833cb57477c8fcc6094c1253f97fa4f4de8ffb6e39d842d` |
| `VG/out/rerun_cmp.json` | `3988be6efb49513282032f12e008ee79e7ddce1bdcb6d5b1dd333becd3184f3f` |
| `VG/out/rerun_diag.json` / `rerun_diag2.json`(무효) / `rerun_diag2b.json` | `08c3139a…` / `ba2346b7…` / `c0e46946…` |
| `VG2/steps.jsonl` / `VG2/vg_rerun.log` / `VG2/vr600.jsonl` | `c56eed3b…` / `fff49473…` / `5a55c349…` |
| `OK2/snap/vg1_before.json` / `vg2_after.json` | `ee57598379a0d0ab60485028eaf702153b205ca9bdb55f2a4edd39abc9369a41` / `5ee9cc79550f5249c41fdfba69a9be7fed02a9b9615dac5c90b0c01557ef3a7a` |
