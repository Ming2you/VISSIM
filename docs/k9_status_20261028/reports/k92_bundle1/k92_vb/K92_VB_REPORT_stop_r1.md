# K9-2 묶음 1 V-B 보고서 — 기록 위 오프라인 사슬 재생 (보충 32) — STOP (V5, S-K55)

- **상태: STOP.** V-B 구동기가 V5(OFF 관문)에서 멈췄습니다(2026-10-22 13:59:46 KST, 규칙 S-K55). 까닭은 무결성 점검 VB-I7(훅 무결성) 하나가 거짓인 것입니다(OFF 사슬 VB-41의 T=3,150 결정). **B1 사슬은 0결정 돌았습니다.** VB-M1–M9 표와 VB-I3 재확인·VB-I4·VB-I5·VB-I6은 계산하지 않았습니다(구동기 V6–V10 미실행). 사용자 결정이 필요합니다(§6).
- 판 r1 (2026-10-22). 정본 = `KB/k92_vb/K92_VB_REPORT.md`, 같은 바이트 사본 = `KB/VB_REPORT.md`, 실행 출력 쪽 사본 = `OK2/vb/K92_VB_REPORT.md`(§8 E8). 고칠 때는 정본을 고치고 다시 복사합니다(보충 32 §5).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보고는 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. V-B는 보고만이고, 통과·실패가 있는 것은 무결성 점검(VB-I)뿐입니다. 교통 성능 판정이 아닙니다.
- 값 선택 표시(보충 24 §7-6): W = 5,209.8(D-K9-34, 몫 가르기 뒤 선택), 씨앗 s = 1045.1612903225805(F-3 비블라인드, 보충 24 §2.6-6).

## 0. 쉬운 요약

**사슬 이어받는 OFF 10결정의 닫힌 목록 밖 차이: 결정 5개에서 모두 55개(경로 기준, 결정마다 11개).** 다섯 결정은 VB-41w T=900·1,050과 VB-31·VB-43·VB-41의 T=3,150(모두 SDMPC 결정)입니다. 55개는 모두 같은 11가지 경로의 `action_token`(행동 객체 해시) 잎이고 규칙 D1로 미분류입니다(§3.2). 무제어 사슬 결정 5개(VB-41w T=150–750)의 목록 밖 차이는 0입니다. 이 표는 판정이 아닙니다(D-K9-62).

1. **무엇을 했나.** J1 기록 런(RR) 위에서, 커밋 K9-2-5 트리 사본(VBT)으로 결정을 하나씩 이어서 다시 계산했습니다. VISSIM은 쓰지 않았습니다. 결정마다 측정 훅이 모형 안의 기록기를 불렀습니다 [실행].
2. **훅 영향 0 시험(ZI) 세 칸: 모두 PASS** [실행]. 훅을 켜도 결정 출력은 CSV 바이트가 같고, JSON 차이는 벽시계 잎뿐이었습니다. 훅 켬/끔 벽시계 비는 0.991–1.043입니다.
3. **OFF 사슬 14결정은 모두 종료 0으로 끝났습니다** [실행]. 사슬 첫 결정 4개의 VB-I1은 4/4 PASS입니다(HARD 같음, 미분류 0, SDMPC 셋은 A_K92 뿌리 점검 참).
4. **OFF 14결정의 VB-I2는 14/14 참, VB-I7은 13/14 참입니다** [실행]. 거짓 하나는 VB-41 T=3,150입니다. 한 결정 안에서 서로 다른 두 탄젠트 작업자 프로세스가 같은 PID(26704)를 받았고, 둘째 프로세스의 후보 폴더 `c_26704_0001`이 첫째 것과 겹쳐 훅이 오류 파일을 썼습니다. 보충 32 P14가 미리 적은 위험이 실제로 일어난 것입니다.
5. **사슬 기구에 대해 보이는 것(보고만):** 사슬 이어받는 OFF 10결정 모두 행동 CSV가 RR 기록과 바이트가 같았습니다(H1 같음). HARD 차이는 모두 닫힌 목록 안이었습니다. 목록 밖 차이는 위의 D1 `action_token`뿐입니다. 이 해시는 직전 CSV 경로를 담은 행동 객체를 피클한 값이라, 경로가 다르면 달라지는 것으로 봅니다 [추론, 근거 §3.2].
6. **B1 사슬·지표는 아직 없습니다.** 그래서 이 보고는 B1의 SC109 녹색·하한 나르기·174 사슬·OUTW 같은 VB-M 값을 하나도 담지 않습니다.
7. 읽기 전용 뿌리(RR·동결본 등) 스냅숏은 STOP 뒤에도 s02 대비 SAME이고, RR 결정 폴더 목록·OK2의 vb 밖 목록·GWT8 상태·고정 목록 51/51·4/4도 V0와 같습니다 [실행, §2].

## 줄임말 (처음 한 번만 풉니다)

- **V-B** = 관문 뒤 오프라인 연쇄 재생 확인(보충 24 §14.1). **VB-I** = V-B 무결성 점검(통과·실패 있음). **VB-M** = V-B 지표(보고만).
- **RR** = `D:/VISSIM_runs/20261004_sdmpc31_k8`(J1 기록 런, 읽기만). **VBR** = `OK2/vb`(V-B 출력 뿌리), OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **VBT** = `D:/VISSIM-merge/k8_gate_trees/k92b1/vb_e27ceac8`(커밋 K9-2-5 `e27ceac8` git archive + CR 고침).
- **SP** = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, **KB** = `SP/k92/bundle1`, **KV** = `KB/k92_vb`, **AD32** = `KB/a32decl`, **KI** = `KB/impl`.
- **KC** = K9-2-5 비교기 `k92_compare.py`. **REC** = K9-2-0 기록기 `k92_record.py`. **ZI** = 훅 영향 0 시험. **HARD** = 딱 같아야 하는 잎 묶음 H1–H5(H1 = 행동 CSV 바이트). **N** = 비교 전 경로 정규화. **결과 넷** = PASS / FAIL / 보류 / INCOMPLETE.
- **SDMPC** = 모형 예측 제어 결정(T ≥ 900, 제어기 `wu-link`). **무제어** = T < 900(`no-control`). **NN / SN / SS** = 무제어←무제어 / 첫 SDMPC←무제어 / SDMPC←SDMPC.
- **OFF** = 그 런의 튜닝 그대로(키 없음). **B1** = W + 씨앗 묶음 팔. **사슬 첫 결정** = 직전 행동이 RR 파일인 결정, **사슬 이어받는 결정** = 직전 행동이 같은 사슬의 앞 결정 출력인 결정.
- **OUTW** = 지평 450 s 동안 Ω(통제 구역) 밖 모형 대기(veh·h). **FEED-4** = SC109 서측으로 들어오는 네 접근 몫. **Ω** = 모형 목적값(`selected_objective`). **PFO** = SDMPC 앞 단계의 웜 스타트 풀이.
- **PID** = 운영 체제가 프로세스에 주는 번호.

## 1. 한 일과 하지 않은 일

한 일 [실행]
- 보충 32 고정판 sha `7f25c21e…` = `.sha256` = 고정점 `KB/AMENDMENT32_FIXED.md`(`b59088ab…`) 안 64자. 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `402eaf59…`(204줄).
- 보충 32 §4.1 고정: `KB/a32_pins.sha256` = 기대 파일 바이트(51/51 OK), 구동기 `KV/vb_chain.py` `4dc9297d…`, 재계산기 `KV/vb_recalc.py` `cab7939d…`, 자기 시험 두 출력(합성, 자식 프로세스 0, 모두 참), `KV/vb_pins.sha256` `6bed3541…`(4줄). 모두 LOG에 적은 뒤 시작했습니다(LOG "V-B (보충 32 §4.1): 도구 고정" 항목).
- `KI/launch.ps1 -Tag vb_chain`(WMI 분리, BelowNormal, `PYTHONHASHSEED=0`, `python -B`, 11:23:27 PID 14464) 한 번. 구동기가 V0–V4를 마치고 V5에서 STOP했습니다(종료 코드 3).
- STOP 뒤 읽기만 하는 확인: 스냅숏 하나(`KI/launch.ps1 -Tag vb_stop_snap`, 출력 `VBR/poststop/s40x_vb_stop.json`), 그 s02 대비 비교, 고정 목록·GWT8·RR 목록·OK2 목록 대조, 실패 진단(훅 오류 파일·`loaded_*.json` 시각 읽기).

하지 않은 일
- B1 사슬(0/41), V6–V10, VB-M 표, 재계산(VB-I5). VISSIM·COM·러너·동결 0. 커밋·브랜치·푸시 0. 금지 시험 0. 봉인 시드·봉인 뿌리·v3c3-s47·codex 64cf 열람 0. 도구 고침 0(STOP 뒤 구동기·훅·고르기·도움 함수 바이트 그대로 [실행 `tree_files_ok` 모두 참]).

## 2. 단계 결과 (V0–V5)

| 단계 | 결과 | 기록 (`VBR/…`) sha256 앞 16자 | 메모 |
|---|---|---|---|
| V0 사전 점검 C1–C12 | 모두 참 | `check_v0.json` `81cb1768…`, `stages/V0.json` `5d86fa99…` | GWT8 head `e27ceac8`, status 0줄, K8 `b9734abe`, `b9734abe..HEAD` 6, 원격 k92 0; VISSIM 0, 남의 러너 0; C: 40 GB 이상, D: 388 GB 이상 |
| 스냅숏 s38 | s02 대비 SAME | `stages/snap_s38_vb_v0.json` `e9087608…` | |
| V1 트리 | 참 | `stages/V1.json` `2fad326d…`, 빌드 기록 `TK/vb_e27ceac8.build.json` `2ace3363…` | CR 형태 `CCCCCCCCCC`, `cr_pair(FRZ_K8b, VBT)`·`cr_pair(FRZ_K8, VBT)` 참, RS `70cca680…`·SHO·튜닝 셋·REC·KC·`k92_replay.py`·`sa_arms.py` sha 기대값. 보고만: VBT 대 GWT8 작업 트리 바이트 다름 0, VBT에만 0, GWT8에만 1 |
| V2 팔 | 참 | `stages/V2.json` `68022848…` | SAF-B1 `65cac7ea…`; VB-I3 두 팔 참(바탕과 차이 = 두 경로, 증거 sha = VBT 커밋 증거, 파일 sha); C12 넷 모두 `phase_price.mode` 없음 |
| V3 ZI | 세 칸 PASS | `zi/zi.json` `79c79883…`, `stages/V3.json` `a163ec2e…` | §3.1 |
| 스냅숏 s39 | s02 대비 SAME | `stages/snap_s39_vb_zi.json` `4e4914b0…` | |
| V4 OFF 사슬 | 14결정 종료 0 | `stages/V4.json` `9153c05a…` | 순서 VB-41w(8) → VB-31(2) → VB-43(2) → VB-41(2) |
| **V5 OFF 관문** | **STOP (S-K55)** | `judge/vb_i1.json` `9c1749a9…`, `judge/vb_reportonly.json` `30fcda3e…`, `STOP_vb_V5.json` `4127cbf2…` | VB-I1 4/4 PASS, VB-I2 14/14 참, **VB-I7 13/14** |
| (STOP 뒤) 스냅숏 | s02 대비 SAME | `poststop/s40x_vb_stop.json` `415ae03a…` | 구동기 스냅숏 이름(s40)을 쓰지 않으려고 VBR 안에 따로 둠 |
| (STOP 뒤) 끝 대조 | 모두 같음 | – | `KB/a32_pins.sha256` 51/51·바이트 = 기대 파일, `KV/vb_pins.sha256` 4/4, GWT8 상태 = V0, RR 세 런 결정 폴더 목록(이름·크기·시각) sha = V0 C9, OK2의 vb 밖 목록 sha = V0 [실행] |

## 3. 결과 표

### 3.1 ZI 세 칸 (`VBR/zi/<칸>/zi_judge.json`) [실행]

상태는 V-B 55결정 밖의 RR v3c3-s43 두 시각입니다. 칸마다 같은 준비 폴더·같은 출력 경로로 훅 끔 → 훅 켬을 돌렸습니다.

| 칸 | 결정 꼴 | (z1) 종료·출력 | (z2) CSV 같음 | (z3) KC 결과 넷 | (z4) 진행 기록 같음 | (z5) 벽시계 잎만 | (z6) 끔에 훅 파일 0 | (z7) 훅 무결성·고르기 | 칸 결과 |
|---|---|---|---|---|---|---|---|---|---|
| z1_off (T=1,050, OFF) | SS | 참 | 참 | PASS | 참 | 참 (차이 잎 36, 벽시계 경로 17, 그 밖 0) | 참 | 참, `selected` | PASS |
| z1_b1 (T=1,050, B1) | SS | 참 | 참 | PASS | 참 | 참 (차이 잎 36, 벽시계 경로 17, 그 밖 0) | 참 | 참, `selected` | PASS |
| z2_b1 (T=750, B1) | NN | 참 | 참 | PASS | 참(둘 다 없음) | 참 (차이 잎 3: `decision_wall_sec`·`prediction_wall_sec`·`/prediction/wall_sec`) | 참 | 참, `no_candidate`(예상대로) | PASS |

훅 비용 (보고만)

| 칸 | 훅 끔 벽시계 (s) | 훅 켬 벽시계 (s) | 켬/끔 비 | 후보 수 | 맞는 후보 | 훅 안 시간 합 (s) | 후보 파일 합 (MB) | `loaded` 파일 수 |
|---|---|---|---|---|---|---|---|---|
| z1_off | 701.2 | 694.7 | 0.991 | 10 | 1 | 11.2 | 11.3 | 11 |
| z1_b1 | 670.4 | 699.2 | 1.043 | 10 | 1 | 11.1 | 11.3 | 11 |
| z2_b1 | 31.8 | 32.5 | 1.022 | 0 | 0 | 0.0 | 0.0 | 1 |

- z1_off 훅 끔 출력 대 RR 기록(보고만, G-K0 D-c와 같은 꼴): 결과 넷 PASS, HARD 같음, 미분류 0 [실행].
- 보충 32 P12(같은 경로면 16진 토큰도 같다는 [추론])는 이번 실행에서 세 칸 모두 그대로였습니다 [실행].
- z1_off의 훅 끔 실행은 새 트리 VBT의 첫 실행이라 캐시를 새로 만들었고, 훅 켬 실행은 그 캐시를 썼습니다. 그래도 (z5)는 참이었습니다 [실행].

### 3.2 VB-I1 — 판정하는 사슬 첫 결정 4개 (`VBR/judge/vb_i1.json`) [실행]

비교 = `KC.compare(RR 결정 폴더, VBR/chain/<사슬>_off/dec, T, VBT, keyed=None, old_root=그 런의 동결본)`.

| 사슬·T | 결정 꼴 | 결과 넷 | HARD | 미분류 | 허용 수 | A_K92 줄 / 모두 ok·새 뿌리·옛 뿌리 |
|---|---|---|---|---|---|---|
| VB-41w T=1 | 무제어 | **PASS** | SAME | 0 | V 6, R3-01 2, R3-03 2, R3-05 2 | 0 / 해당 없음 |
| VB-31 T=3,000 | SDMPC | **PASS** | SAME | 0 | V 6, F1 12, F3 31, A_K92 2, R3-01 2 | 2 / 참 |
| VB-43 T=3,000 | SDMPC | **PASS** | SAME | 0 | V 6, F1 12, F3 29, R3-08 2, A_K92 2, R3-01 2, R3-03 2, R3-05 2 | 2 / 참 |
| VB-41 T=3,000 | SDMPC | **PASS** | SAME | 0 | V 6, F1 12, F3 32, R3-08 2, A_K92 2, R3-01 2, R3-03 2, R3-05 2 | 2 / 참 |

- 이 4결정도 훅을 켠 채 돌았습니다. 그래서 "훅을 켠 결정 출력 = RR 기록"의 증거이기도 합니다(보충 32 §2.1).
- 보충 32 P13(VB-41w T=1의 직접 선례 없음)은 이번 실행에서 PASS로 나왔습니다 [실행].

### 3.3 보고 전용 — 사슬 이어받는 OFF 10결정 (`VBR/judge/vb_reportonly.json`; 판정 아님, D-K9-62)

| 사슬 | T (직전 T) | 꼴 | 결과 넷(참고) | CSV 같음 | 목록 안 HARD / 목록의 HARD | 목록 안 미분류 경로 | **목록 밖 경로 수** (잎 수) | 잘림 | 보이지 않은 목록 잎 |
|---|---|---|---|---|---|---|---|---|---|
| VB-41w | 150 (1) | NN | FAIL | 참 | 1 / 1 | 2 | 0 | 없음 | 0 |
| VB-41w | 300 (150) | NN | FAIL | 참 | 1 / 1 | 2 | 0 | 없음 | 0 |
| VB-41w | 450 (300) | NN | FAIL | 참 | 1 / 1 | 2 | 0 | 없음 | 0 |
| VB-41w | 600 (450) | NN | FAIL | 참 | 1 / 1 | 2 | 0 | 없음 | 0 |
| VB-41w | 750 (600) | NN | FAIL | 참 | 1 / 1 | 2 | 0 | 없음 | 0 |
| VB-41w | 900 (750) | SN | FAIL | 참 | 1 / 1 | 8 | **11 (31)** | 없음 | 0 |
| VB-41w | 1,050 (900) | SS | FAIL | 참 | 3 / 3 | 10 | **11 (29)** | 없음 | 0 |
| VB-31 | 3,150 (3,000) | SS | FAIL | 참 | 3 / 3 | 10 | **11 (27)** | 없음 | 0 |
| VB-43 | 3,150 (3,000) | SS | FAIL | 참 | 3 / 3 | 10 | **11 (29)** | 없음 | 0 |
| VB-41 | 3,150 (3,000) | SS | FAIL | 참 | 3 / 3 | 10 | **11 (31)** | 없음 | 0 |

결정마다 한 줄(함수 `vb_lib32.reportonly`가 만든 글자 그대로의 뜻):
- VB-41w T=150·300·450·600·750: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- **VB-41w T=900, VB-41w T=1,050, VB-31 T=3,150, VB-43 T=3,150, VB-41 T=3,150: 닫힌 목록 밖 차이 11개가 있습니다.** 다섯 결정 모두 아래 같은 11경로이고, 모두 종류 `value`, 까닭 D1(`action_token`)입니다.

| # | 목록 밖 경로 (미분류, D1) |
|---|---|
| 1 | `/metadata/joint_leader_selection/budget_initialization/reference_action_token` |
| 2 | `/metadata/joint_leader_selection/control_sequence/plan_action_token` |
| 3 | `/metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token` |
| 4 | `/metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token` |
| 5 | `/metadata/joint_leader_selection/surrogate_query/rows[*]/action_token` |
| 6 | `/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token` |
| 7 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token` |
| 8 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token` |
| 9 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token` |
| 10 | `/metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token` |
| 11 | `/metadata/joint_leader_selection/trial_rows[*]/action_token` |

- 왜 생기나 [읽음 + 추론]: `action_token`은 행동 객체를 피클한 바이트의 sha256입니다(`evaluation/controllers/area_follower_objective.py:437-439`, `:548`). 행동 객체의 `diagnostics`에는 직전 CSV의 경로와 sha가 들어갑니다(`physical_ramp_branches.py:368`; 닫힌 목록의 F2–F7·S4–S9 경로가 바로 그 칸). 사슬에서는 직전 CSV 경로가 RR이 아니라 VBR 아래이므로 이 해시가 달라집니다. 사슬 첫 결정 4개에서는 이 잎이 다르지 않았습니다(§3.2 미분류 0). 닫힌 목록은 "직전 경로 글자를 담거나 직전 파일 sha와 같은 잎"을 찾아 만든 것이라(보충 32 §2.2), 그 값들을 다시 해시한 이 잎은 목록 작성 방법으로는 잡히지 않았습니다 [추론].
- 같은 10결정에서 행동 CSV(H1)는 모두 RR 기록과 바이트가 같았고, 목록의 HARD 잎은 모두 보였으며(보이지 않은 목록 잎 0), 목록 밖 HARD는 0이었습니다 [실행].

### 3.4 VB-I2·VB-I7 — OFF 14결정 (`VBR/judge/vb_i1.json` `/off_rows`) [실행]

| 사슬 | T | 직전 | 어댑터 종료 | 벽시계 (s) | VB-I2 | VB-I7 | 고르기 상태 | 후보 / 맞음 | `loaded` 수 | 훅 안 시간 합 (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| VB-41w | 1 | 없음 | 0 | 27.1 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 150 | 사슬 | 0 | 27.3 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 300 | 사슬 | 0 | 31.2 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 450 | 사슬 | 0 | 30.4 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 600 | 사슬 | 0 | 31.9 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 750 | 사슬 | 0 | 32.8 | 참 | 참 | no_candidate | 0 / 0 | 1 | 0.0 |
| VB-41w | 900 | 사슬 | 0 | 732.1 | 참 | 참 | selected | 10 / 1 | 11 | 11.6 |
| VB-41w | 1,050 | 사슬 | 0 | 723.4 | 참 | 참 | selected | 9 / 1 | 10 | 9.9 |
| VB-31 | 3,000 | RR | 0 | 745.1 | 참 | 참 | selected | 8 / 1 | 9 | 9.4 |
| VB-31 | 3,150 | 사슬 | 0 | 744.8 | 참 | 참 | selected | 8 / 1 | 9 | 9.2 |
| VB-43 | 3,000 | RR | 0 | 777.5 | 참 | 참 | selected | 6 / 1 | 7 | 7.2 |
| VB-43 | 3,150 | 사슬 | 0 | 728.3 | 참 | 참 | selected | 9 / 1 | 10 | 10.5 |
| VB-41 | 3,000 | RR | 0 | 623.2 | 참 | 참 | selected | 9 / 1 | 10 | 9.8 |
| **VB-41** | **3,150** | 사슬 | 0 | 746.0 | 참 | **거짓** | **hook_error** | 9 / 1 | 10 | 10.2 |

- VB-41 T=3,150의 VB-I7 거짓 항목: 2번(훅 오류 파일 0)과 4번(고르기 상태가 네 가지 가운데 하나) [실행 `k92_select.json` `fe8b6319…`].
- **진단** [실행 파일 이름·시각만]: 훅 오류 파일 `chain/vb41_off/hook/t003150/hook_error_26704.txt`(`c98097670e66…`, 757 B)는 `os.makedirs(…\c_26704_0001)`의 `FileExistsError`입니다(13:57:29). 그 폴더는 13:53:44에 PID 26704(부모 = 어댑터 5132, 순번 1)가 이미 만들었습니다. `loaded_26704.json`의 시작 시각은 13:56:26이라, 그 파일은 둘째 프로세스가 덮어쓴 것입니다(`w` 모드). 그래서 이 결정의 `loaded` 파일은 10개(어댑터 1 + 작업자 9)이고, 작업자 안 `omega_costs` 호출은 10번(후보 폴더 9 + 실패 1)이었습니다. 작업자 프로세스는 10개였고 PID는 9가지였습니다 [추론: 위 시각들]. 결론: 한 결정 안에서 같은 부모의 두 작업자가 같은 PID를 차례로 받았습니다(Windows PID 재사용). 보충 32 P14 "겹치면 STOP 쪽, 거짓 PASS 없음" 그대로입니다.
- 그 결정의 다른 산물: 어댑터 종료 0, 출력 JSON·CSV 있음, 영수증 씀(고르기보다 먼저), VB-I2 참. 맞는 후보 1개는 있었지만(`n_match` 1) 상태가 `hook_error`라 기록은 고르지 않았습니다(규칙대로).
- 작업자 수는 결정마다 6–10개였습니다(후보 수 = 작업자 안 `omega_costs` 호출 수) [실행].

### 3.5 계산하지 않은 것

- VB-I3(V7 재확인), VB-I4(55결정), VB-I5(재계산), VB-I6(B1 하한 나르기): B1 사슬 0이라 계산 0. VB-I3은 V2에서 두 팔 참이었습니다.
- VB-M1–M9: 0. B1·OFF·RR 어느 쪽 값도 표로 내지 않았습니다.

## 4. V-B가 보일 수 있는 것과 없는 것

- **보일 수 있는 것(완료되면)**: 기록된 J1 관측 위에서 B1 팔을 연속 결정으로 돌렸을 때, 모형 안에서 SC109 p3 녹색이 어떻게 가는지, 결정이 흔들리는지, (173, p4) 하한이 씨앗에서 출발해 나르는지, 모형 174 사슬·OUTW가 어떻게 가는지(보충 24 §14.1 목적). 모두 **모형 안의 값**입니다.
- **보일 수 없는 것**: VISSIM 반응, TTT, 실측 Ω. 관측은 옛 제어기 궤적이라 B1 사슬이 기록과 멀어질수록 상태가 실제 적용과 맞지 않습니다. 영수증은 "적용했다고 치는" 것입니다(P9).
- **Ω 인용 규칙**: Ω(모형 목적값) 감소는 Ω 밖 대기 OUTW 증가와 함께만 적습니다(보충 24 §7-1, D-K9-32). 이번에는 Ω·OUTW 표가 없습니다.
- **이번 실행이 보인 것**: 훅을 켜도 결정 출력이 바뀌지 않는다는 것(ZI 3칸, 사슬 첫 결정 4개 PASS), 사슬 이어받는 OFF 결정이 기록 CSV를 바이트 그대로 다시 낸다는 것(10/10), 그리고 목록 밖 차이는 `action_token` 해시 11경로뿐이라는 것(보고만).
- **이번 실행이 보이지 못한 것**: B1에 관한 모든 것.

## 5. V-A에서 볼 것 (V-A는 사용자 결정 뒤; 이 워크플로 밖)

1. SC109 p3 녹색이 24.5 s 아래로 내려가는 결정(J1 발병 정의)과 그 첫 시각을 J1 기록과 같은 T끼리.
2. (173, p4) 하한 키 이름·값과 `k92_hb_seed_binding`, `head_observation_prior_discarded`(B1 폐루프에서 모든 시드의 T=150은 1.0이 예상, 보충 24 §14.2).
3. Ω 감소를 볼 때는 Ω 밖 대기(OUTW, FEED-4 몫)·`SC109_E_out`을 같은 표에(D-K9-32).
4. 결정 벽시계(G-K5 예산 1.0158 안인지 보고).
5. 측정 훅을 V-A에 쓰지 않는다면 이 PID 겹침 문제는 V-A에 없습니다. 쓴다면 같은 위험이 있습니다 [추론].
6. V-B가 끝나지 않은 채 V-A로 가면 B1 연속 결정의 오프라인 근거(보충 24 §2.6-7: "H-b 동역학의 오프라인 근거는 사실상 V-B뿐")가 없습니다.

## 6. 사용자가 정할 것

**Q1. 훅 후보 폴더 겹침(VB-I7 거짓)을 어떻게 할까요?**
- (가) **훅 고침 + 보충 33** [추론, 권장 후보]: 후보 폴더·`loaded` 파일 이름에 프로세스마다 다른 값(예: 시작 시각 나노초)을 넣어 PID가 다시 쓰여도 겹치지 않게 합니다. 훅 바이트가 바뀌므로 고정 목록·자기 시험·ZI를 새로 하고, OFF 사슬(VB-I7)과 B1 사슬을 처음부터 다시 돌립니다(약 8–9 h). 이번 OFF 14결정은 보관합니다.
- (나) 훅 그대로, 겹친 결정만 다시: PID 재사용은 우연이라 다시 돌리면 대개 겹치지 않을 것으로 봅니다 [추론]. 다만 이번 OFF SDMPC 8결정 가운데 1결정에서 일어났으므로, B1 SDMPC 35결정에서도 몇 번 다시 일어날 수 있습니다 [추론, 단순 비율로 약 4번]. 그때마다 STOP입니다.
- (다) VB-I7의 `hook_error`를 STOP이 아니라 "그 결정의 VB-M5·M6·M8 = 없음"으로 보고만 하도록 바꿈(STOP을 줄이는 쪽, 데이터를 본 뒤의 바꿈).

**Q2. 보고 전용 10결정의 `action_token` 11경로(목록 밖, 판정 아님)는 어떻게 다룰까요?**
- (가) 지금처럼 보고만(D-K9-62 그대로). 다음 V-B 보고에도 같은 표로 적습니다.
- (나) 다음 보충에서 닫힌 목록에 이 11경로를 더함(데이터를 본 뒤의 목록 바꿈이라 공개 필요). 판정은 여전히 없습니다.

**Q3. 다시 돌릴 때 이번 출력은?** 구동기는 이어 하기를 지원합니다(완료 결정은 건너뜀). 다만 Q1 (가)처럼 훅이 바뀌면 고정 위반(S-K53)이 되므로 새 VBR(예: `OK2/vb2`)과 새 고정이 필요합니다 [읽음 `vb_chain.py` `tree_files_ok`·V0 C5]. 이번 `OK2/vb`(약 2.5 GB)·`TK/vb_e27ceac8`(약 2.1 GB, 실행 캐시 포함)은 지우지 않고 둡니다.

## 7. 한계 (보충 24 §14.1 "한계"와 보충 32 §11, 이번 실행에 맞춰)

1. 관측은 옛 제어기 궤적입니다. VISSIM 반응·TTT·Ω 실측은 보이지 않습니다.
2. 키 끔 = 기록은 사슬 앞 결정과 G-K0 상태에서만 직접 보입니다. 이번에는 사슬 첫 결정 4개(PASS)와 ZI z1_off 훅 끔 대 기록(PASS)이 그 증거입니다.
3. 보고 전용 10결정은 판정에서 빠집니다(P1). 닫힌 목록은 RR 기록 구조에서 만든 것이라, 해시로 한 번 더 감싼 잎(`action_token`)은 들어 있지 않았습니다(§3.3).
4. 훅이 재는 자리는 `omega_costs` 응답뿐이고, `w_receiving_limited_steps`·`vissim` 칸은 재지 않습니다(P2).
5. 지평 3블록 고정, 영수증은 적용한 셈 치는 것(P9), D-K9-44(어댑터가 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 셈)는 이번 61번 어댑터 실행에서도 그대로입니다 [추론: 코드 그대로].
6. ZI는 V-B 밖 두 상태·세 칸에서만 훅 영향 0을 직접 봅니다. 그 밖의 결정은 같은 훅 코드라는 데서 미루어 봅니다 [추론].
7. 보충 24 §2.6의 한계 1–13, 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, 보충 30 §10, 보충 31 §9는 그대로입니다.

## 8. 공개 (보충 32 §5 "머리에 옮김")

### 이 V-B 단계의 공개

- **E1 구동기가 글을 기계로 옮기며 정한 해석** (데이터 전에 고정, LOG "V-B (보충 32 §4.1): 도구 고정" 항목) [읽음 `KV/vb_chain.py`]: VB-I2의 "그 T 파일" = 출력 폴더에서 이름에 6자리 T가 든 파일. VB-M7 "PFO 결과 목적값" = `warm_start_objective`, "유지 목적값" = `held_objective`, "고른 행동 목적값" = `selected_objective`(근거 `sdmpc.py:990-994`, 짝짓기는 [추론]). VB-M3 Δp3 = 사슬 안 이웃 결정 차이, 부호 바뀜은 |Δ| ≥ 0.5 s인 Δ만. VB-M9 첫 다른 결정 = CSV sha가 RR과 다른 첫 T. 이번에는 VB-M을 계산하지 않아 결과에 쓰이지 않았습니다.
- **E2 STOP을 늘리는 쪽 더함**: V0 C2에 고정점 32 파일 sha, V1에 VBT `k92_replay.py`·`sa_arms.py` sha, 결정마다 VBT RS·SHO·REC·KC와 훅·고르기·도움 함수 바이트 전후 대조(14결정 모두 참).
- **E3 자기 시험 판 하나 더**: 재계산기 자기 시험 첫 판이 통과한 뒤 "결정 JSON 값 하나를 바꾸면 잡음" 사례를 실제 파일을 바꿔 다시 계산하는 꼴로 강화해 다시 돌렸습니다(둘째 판이 고정 대상, 고정 전·데이터 0).
- **E4 VBT 안 실행 캐시**: 어댑터 자식이 `VBT/evaluation/controllers/__tangentcache__/*.mcode`를, 숫자 캐시를 `VBR/numba_cache`에 만들었습니다(앞선 TK 트리 재생과 같음). 원천 고정은 `*.py`만 셉니다(ADP:13110) [읽음].
- **E5 실패 진단 열람**: STOP 뒤 훅 오류 파일 전문(757 B, 경로·예외 이름뿐), 그 결정 훅 폴더의 파일 이름, `loaded_*.json`의 `argv0`·`pid`·`ppid`·`recorder_ok`·시작 시각, 후보 `cand.json` 한 개의 `pid`·`ppid`·`seq`·`time_ns`를 읽었습니다. 목적값·예측값은 열지 않았습니다.
- **E6 진행 중 열람**: 진행 확인으로 `VBR/driver_log.txt`·`steps.jsonl` 끝, ZI 칸 판정 파일(가부·개수·벽시계 경로 이름·비용), ZI z1_off 훅 폴더 이름과 `loaded` 파일의 `argv0`·`recorder_ok`, V0–V2 단계 기록을 읽었습니다. 설계 확인 때 RR v3c3-s43 T=1,050 JSON의 키 이름 목록(캐시·컴파일 관련)과 v3c3-s41 T=3,000 JSON의 `joint_leader_selection` 키 이름·`green_times` SC109 키 이름을 한 번씩 보았습니다(값 출력 0).
- **E7 보고서 쓰기**: 이 글은 STOP 뒤 세션이 판정 파일을 읽어 썼습니다. 서식 도구 `KV/mk_tables.py`는 만들었지만 VB-M 표가 없어 쓰지 않았습니다.
- **E8 실행 출력 쪽 사본 자리**: 작업 지시는 OK2 아래 사본을 요구했습니다. OK2 맨 위에 두면 다시 돌릴 때 구동기 V10의 "OK2의 vb 밖 = 스냅숏·로그뿐" 대조가 어긋나므로 `OK2/vb/K92_VB_REPORT.md`에 두었습니다. STOP 뒤 스냅숏도 같은 까닭으로 `VBR/poststop/`에 두었고, 그 발사 로그는 `OK2/logs/vb_stop_snap.txt`(구동기 대조가 빼는 `vb_` 이름)입니다.

### 보충 32 §7 공개 (요약)

- P1 D-K9-62는 사용자가 권장안이 아닌 (나)를 고른 것입니다. 사슬 이어받는 OFF 10결정은 판정이 아니라 보고입니다.
- P2 측정 훅은 결정 프로세스(주로 탄젠트 작업자) 안에서 도는 읽기 전용 도구입니다. 무제어 결정에는 기록이 없습니다. `on_alloc`을 부르지 않아 "수신 제한 스텝"은 재지 않습니다. 지평은 3블록(450 s)입니다.
- P3 VB-M5·M6·M8의 키 끔 값은 OFF 사슬 14결정에만 있습니다(추가 재생 없음).
- P4 검증 3차와 VerifyVB의 공개 사항을 받아들였습니다(D-K9-64).
- P5·P15 Declare·ReviewDeclare 단계가 읽은 기록 자료는 V-B 데이터가 아닙니다.
- P6 VB-I7과 VB-I3 팔 파일 sha 조건은 새 STOP 점검입니다. **이번 STOP은 그 VB-I7에서 나왔습니다.**
- P7 VB-I1 D5 뿌리 점검의 꼴(A_K92 줄 하나 이상, 모두 참) — 이번 SDMPC 셋 모두 2줄·참.
- P8 기록기 `write`가 작업자에 표준 모듈을 더 실을 수 있습니다(ZI가 영향 0을 보임).
- P9 오프라인 영수증은 VISSIM 적용 없이 러너와 같은 바이트 꼴로 씀.
- P10 옛 줄 번호(`sdmpc.py:461-470` → `:513-533`).
- P11 결정 기록 근거 줄의 "미분류 2–13개"는 HARD 밖 잎 수.
- P12 ZI (z5)의 토큰 가정 — 이번에 그대로였음.
- P13 VB-41w T=1 직접 선례 없음 — 이번에 PASS.
- P14 훅 후보 폴더 PID 겹침은 STOP 쪽 — **이번에 일어남(VB-41 T=3,150).**

### 물려받은 공개 (한 줄씩; 원문은 각 보충)

- 보충 27 §8: K9-2-1·K9-2-2 관문에서 G-K2를 HARD만으로, G-K4를 HARD 숫자만으로 판정했던 사실과 다시 판정(RJ-G2·RJ-G4). 데이터를 본 뒤의 규칙 고침이라 결과를 짐작하는 상태였습니다.
- 보충 27 §13: N이 어느 K9-2 트리에서 나온 경로인지 보지 못함, CR 범위는 L 10파일, 묶음 폴더 목록은 닫힘 등 1–15.
- 보충 28 §9: A28-W는 결과를 짐작하는 상태의 허용, A28-W는 구동기 층, 명령줄 길이 점검은 안전 장치 등 1–18.
- 보충 29 §11: A_K92는 옛 뿌리가 필수, 무리 K 옛 뿌리 = 같은 바이트 동결본, 다시 비교는 "같은 보고"를 요구, 망가뜨림 시험 58개 범위 등 1–20.
- 보충 30 §10: 지속성 보고 21/22, F 잡 로그 걸러 읽기 한 번(개수만), J-0 글자 그대로 59/61, VerifyGates J-a 도구 사후 수정, 봉인 뿌리 맨 위 여섯 등 1–17.
- 보충 31 §5·§9: `_seed47_path` 데이터 뒤 고침(S-K12 예외, 사용자 결정), jb_unit 규칙 바꿈, 메인 세션 `grep -rl`, 검증 2차 공개 수용, 임시 트리 보관 등.

## 9. 파일과 sha256

| 파일 | sha256 |
|---|---|
| 구동기 `KV/vb_chain.py` | `4dc9297df760800ebb20948b05ba94a645d93a8c7e44abb64c511d1be21d6e99` |
| 재계산기 `KV/vb_recalc.py` | `cab7939df8fd55ff4d7df36b058f8892d045a9aff5610b17c8f81f336d5c3e7c` |
| 자기 시험 `KV/selftest/vb_selftest.json` / `vb_recalc_selftest.json` | `0bf303ef77566f7b67e215a7257ab9af30765f38f2659b8f0b0df87b459e8f54` / `27faab53a04db7bbce41600907b82802a157607f9b39a739d273dacca4a1d84f` |
| 고정 목록 `KB/a32_pins.sha256` / `KV/vb_pins.sha256` | `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb` / `6bed354112b93b65d6ffe59bbc8b1472c5e3911683e0d0fcc31964e44514f366` |
| `VBR/check_v0.json` | `81cb17682cf7c78b14031374c8eaab63c22f294104df9bd207ae49bdfbf8fe5e` |
| `VBR/zi/zi.json` / `zi/z1_off/zi_judge.json` / `zi/z1_b1/zi_judge.json` / `zi/z2_b1/zi_judge.json` | `79c7988361cefa87a79586a93e06cf7207bb1ee853c7d1c1a77f80ccaa6129c5` / `4a55cbd87b5e385b51ef534e32f0329454e801bc5b40860b2d2214eee357c567` / `30d51d8f1a49089770d334c7cf5557e6ef5fb80d3fa740a3a6b36b28a16c4ff6` / `272e91b0df03dfe79d15e74720a4924f19c396f3d38b6fc90f82b2ac8e6f12bf` |
| `VBR/judge/vb_i1.json` / `vb_reportonly.json` | `9c1749a9f7bc6331f527026cb53ae83c7ebbdfd7c479695e522e38615fe358e9` / `30fcda3ec3e3d8b7c08a476a02b96d47f8c049f6209c4bac3e603f2f983f971c` |
| `VBR/STOP_vb_V5.json` | `4127cbf2bfbbd3625bb625e388c29c6191b755e4a774b9f1cbbcacd3490a751c` |
| 훅 오류 `VBR/chain/vb41_off/hook/t003150/hook_error_26704.txt` / 고르기 `…/rec/t003150/k92_select.json` | `c98097670e66928de549abd885a4e571d422d5dd75e233d56fdd7311809f77c4` / `fe8b63197a0b168e091ec443a3f9b8e29bb71abf14a9fbfd286cbc3b904bdc9c` |
| STOP 뒤 스냅숏 `VBR/poststop/s40x_vb_stop.json` | `415ae03a0e30e5f6fbb100744073a61b6a737ff0326ae1838249e7e4f3b6f646` |
| 빌드 기록 `TK/vb_e27ceac8.build.json` / SAF-B1 `VBR/arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json` | `2ace33638b30a4daccb63544d55e668608e2f51e140a6f93706e79c0514bab0e` / `65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28` |
| 단계 기록 `VBR/stages/V0–V4.json` | V0 `5d86fa99…`, V1 `2fad326d…`, V2 `68022848…`, V3 `a163ec2e…`, V4 `9153c05a…` (64자는 LOG) |

- 이 보고서 자신의 sha256은 LOG의 STOP 항목에 적습니다.
