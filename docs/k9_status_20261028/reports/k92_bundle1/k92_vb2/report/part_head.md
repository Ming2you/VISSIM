# K9-2 묶음 1 V-B 보고서 — 기록 위 오프라인 사슬 재생 (보충 33 재실행) — r2 완료 판

- **상태: 완료 판 r2.** V-B 구동기가 V0–V10을 모두 PASS 기록으로 마쳤습니다(2026-10-23 00:49:14 KST, STOP 파일 0). 무결성 점검: VB-I1(판정하는 사슬 첫 결정 4개) 4/4 PASS, VB-I2·VB-I3·VB-I4·VB-I6·VB-I7 55결정 모두 참, VB-I5 독립 재계산 4,204칸 다름 0 [실행]. 다음 단계는 VerifyVB(보충 33 §6.5)입니다. V-A와 푸시는 그 뒤 사용자 결정입니다.
- 판 r2 (보충 33 재실행, D-K9-65·66). r1 = STOP 판(`KV/K92_VB_REPORT_stop_r1.md` = `KB/VB_REPORT_stop_r1.md` = `OK2/vb/K92_VB_REPORT.md`, sha256 `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00`, 보관). 정본 = `KB/k92_vb/K92_VB_REPORT.md`, 같은 바이트 사본 = `KB/VB_REPORT.md`, `OK2/vb2/K92_VB_REPORT.md`(보충 33 §8). 고칠 때는 정본을 고치고 다시 복사합니다.
- 쓴 자리: VBR = `OK2/vb2`(9.7 GB), VBT = `TK/vb2_e27ceac8`(2.1 GB, 빌드 기록 `TK/vb2_e27ceac8.build.json`). 옛 VBR `OK2/vb`·옛 VBT `TK/vb_e27ceac8`·`KV`의 옛 도구는 보관이고 바뀌지 않았습니다(V0 C13·V10 대조, §2).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보고는 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. V-B는 보고만이고, 통과·실패가 있는 것은 무결성 점검(VB-I)뿐입니다. 교통 성능 판정이 아닙니다. 아래 지표는 모두 **모형 안 값**이고 VISSIM 값이 아닙니다.
- 값 선택 표시(보충 24 §7-6): W = 5,209.8(D-K9-34, 몫 가르기 뒤 선택), 씨앗 s = 1045.1612903225805(F-3 비블라인드, 보충 24 §2.6-6).

## 0. 쉬운 요약

**사슬 이어받는 OFF 10결정의 닫힌 목록 밖 차이: 결정 5개에서 모두 55개.** (보충 32 §2.3 요약 문장; 경로 기준, 잎으로는 147개)

> **보고 전용 OFF 10결정의 닫힌 목록 밖 차이(판정 아님, STOP 아님; D-K9-62·66): 결정 5개에서 모두 55개.** 그 가운데 `action_token` 꼴 경로는 55개입니다. 까닭 [추론, 근거 읽음]: `action_token`은 행동 객체를 피클(pickle, 파이썬 객체를 바이트로 바꾸는 것)한 바이트의 sha256입니다(`evaluation/controllers/area_follower_objective.py:436-441`, `:548`). 행동 객체의 `diagnostics`에는 직전 행동 CSV의 경로와 sha가 들어갑니다(`physical_ramp_branches.py:368`; 닫힌 목록 F2–F7·S4–S9가 가리키는 칸). 사슬을 이어받는 결정에서는 그 경로가 RR이 아니라 V-B 출력 뿌리 아래에 있으므로 이 해시가 달라집니다. 닫힌 목록은 "직전 경로 글자를 담거나 직전 파일 sha와 같은 잎"을 찾아 만든 것이라, 그 값을 다시 해시한 이 잎은 목록을 만드는 방법으로 잡히지 않았습니다. 사슬 첫 결정 4개에서는 직전 행동이 RR 파일 그대로라 이 잎이 다르지 않습니다.

- 55개 = 결정 5개 × 같은 11경로(서로 다른 경로 11개). 다섯 결정은 VB-41w T=900·1,050과 VB-31·VB-43·VB-41의 T=3,150(모두 SDMPC 결정)입니다. 무제어 사슬 결정 5개(VB-41w T=150–750)의 목록 밖 차이는 0개입니다 [실행 `VBR/judge/vb_reportonly.json`].
- **STOP 판 r1에서 본 11경로와 견주면: 같은 경로 11개, 이번에 새로 보인 경로 0개, 이번에 보이지 않은 경로 0개.** 결정마다 잎 수(31·29·27·29·31)도 r1과 같습니다 [실행].
- `action_token` 꼴이 아닌 목록 밖 경로: **0개.** 목록 밖 HARD 0, 잘림 0, 보이지 않은 목록 잎 0, 행동 CSV(H1)는 10/10 RR 기록과 바이트 같음 [실행].

| # | 목록 밖 경로 (종류 `value`, 까닭 D1 = 미분류) | VB-41w T=900 (SN) | VB-41w T=1,050 (SS) | VB-31 T=3,150 (SS) | VB-43 T=3,150 (SS) | VB-41 T=3,150 (SS) | 잎 합 |
|---|---|---|---|---|---|---|---|
| 1 | `/metadata/joint_leader_selection/budget_initialization/reference_action_token` | 1 | 1 | 1 | 1 | 1 | 5 |
| 2 | `/metadata/joint_leader_selection/control_sequence/plan_action_token` | 1 | 1 | 1 | 1 | 1 | 5 |
| 3 | `/metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token` | 2 | 2 | 2 | 2 | 2 | 10 |
| 4 | `/metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token` | 4 | 4 | 4 | 5 | 4 | 21 |
| 5 | `/metadata/joint_leader_selection/surrogate_query/rows[*]/action_token` | 10 | 9 | 8 | 9 | 10 | 46 |
| 6 | `/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token` | 1 | 1 | 1 | 1 | 1 | 5 |
| 7 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token` | 2 | 2 | 2 | 2 | 2 | 10 |
| 8 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token` | 2 | 2 | 2 | 2 | 2 | 10 |
| 9 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token` | 1 | 1 | 1 | 1 | 1 | 5 |
| 10 | `/metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token` | 2 | 2 | 2 | 2 | 2 | 10 |
| 11 | `/metadata/joint_leader_selection/trial_rows[*]/action_token` | 5 | 4 | 3 | 3 | 5 | 20 |
| | 결정마다 잎 합 | 31 | 29 | 27 | 29 | 31 | 147 |

쉬운 말로 (번호마다 근거 자리는 본문 절)

1. **무엇을 했나.** J1 기록 런(RR)의 관측 위에서, 커밋 K9-2-5 트리 사본(VBT)으로 결정을 하나씩 이어서 다시 계산했습니다. VISSIM은 쓰지 않았습니다. OFF 팔(키 없음) 14결정, B1 팔(W + 씨앗 키) 41결정, 훅 영향 0 시험 6실행입니다. 결정마다 고친 측정 훅(보충 33)이 모형 안의 기록기를 불렀습니다 [실행, §1].
2. **훅 이름 고침이 한 일.** 훅을 켠 58개 폴더(사슬 55 + ZI 3)의 이름이 모두 새 꼴이고 오류 파일은 0개입니다. 이번 실행에서 한 폴더 안 PID 재사용이 **한 번** 일어났습니다(VB-41 B1 T=4,200, PID 3024를 두 프로세스가 받음). 새 이름은 토큰이 달라 겹치지 않았고, 두 프로세스의 후보 시각 구간도 겹치지 않았습니다 [실행, §3.6]. r1을 멈춘 것과 같은 꼴의 사건이 이번에는 기록을 막지 않았다는 뜻입니다.
3. **훅 영향 0 시험(ZI) 세 칸: 모두 PASS** [실행, §3.1]. 훅을 켜도 결정 출력의 CSV 바이트가 같고, JSON 차이는 벽시계 잎뿐이었습니다. 훅 켬/끔 벽시계 비는 1.007·1.011·0.980입니다.
4. **무결성 점검**: VB-I1 판정 4결정 4/4 PASS(HARD 같음, 미분류 0, SDMPC 셋은 A_K92 2줄·뿌리 점검 참), OFF 14결정 VB-I2·VB-I7 14/14 참, 55결정 VB-I2·I3·I4·I6·I7 참, 재계산 VB-I5 4,204칸 다름 0 [실행, §3.2–§3.5].
5. **고르기 상태**: SDMPC 결정 43개 가운데 `selected` 41, **`no_match` 2(VB-41 B1 T=3,300과 T=4,500)**. `no_match`는 STOP이 아니지만 그 두 결정의 VB-M5·M6·M8은 "없음"입니다. 두 결정 모두 고른 행동의 SC109 p2·p3·p4 녹색이 바로 앞 B1 결정과 같은 값이었습니다 [실행, §4 표]. 왜 맞는 후보가 없었는지는 이 보고에서 정하지 않습니다.
6. **B1 사슬에서 보이는 것(모형 안 값, 보고만)** [실행, §4]:
   - SC109 p3 ≤ 24.5 s 결정 수: B1 사슬 VB-31·VB-43·VB-41·VB-41w 모두 0개. 같은 T의 RR 기록은 VB-31 5개(첫 T=3,900), VB-43 6개(첫 T=3,750), VB-41 0개, VB-41w 0개.
   - (173, p4) 하한(VB-I6): VB-41w·VB-41은 모든 결정에서 s(1,045.1613), VB-31은 s에서 T=3,900부터 1,384.6154, VB-43은 처음부터 1,509.6774. 사슬 안에서 줄지 않았습니다.
   - Ω와 Ω 밖 대기(OUTW)를 같은 상태에서 함께 볼 수 있는 곳은 B1과 OFF가 둘 다 기록을 가진 8개 상태(VB-41w T=900·1,050, 세 사슬의 T=3,000·3,150)뿐입니다. 그 8개에서 B1 − OFF는 Ω −3.69 ~ −11.72, OUTW −1.89 ~ −4.55 veh·h, FEED-4 몫 −2.14 ~ +1.25 veh·h입니다 [계산, §4.1]. 이 숫자는 모형 예측이고, Ω만 따로 떼어 인용하지 않습니다(D-K9-32).
   - 같은 8개 상태에서 모형 174 사슬 재고(지평 끝)는 B1 14.66–86.53, OFF 78.88–234.65였고, `SC109_E_out` 지평 최대/220은 B1 0.120–0.324, OFF 0.016–0.126이었습니다 [실행, §4.1].
7. **사슬 기구(보고만)**: 사슬 이어받는 OFF 10결정 모두 행동 CSV가 RR 기록과 바이트가 같았습니다. 목록 밖 차이는 위 `action_token` 11경로뿐입니다(맨 위 표).
8. **보관과 고정**: 옛 VBT 목록 sha(V0·V10) = `d51f4deefc53b69c…`(10,660행) = 고정점 33의 검토 값, 보관 바이트 점검 아홉 참, 고정 목록 63/63, GWT8 head `e27ceac8`·status 0줄, RR 목록 = V0, 스냅숏 넷 SAME [실행, §2].
9. **V-B가 보이지 못하는 것**: VISSIM 반응, TTT, 실측 Ω·대기. 관측은 옛 제어기 궤적입니다(§5).

## 줄임말 (처음 한 번만 풉니다)

- **V-B** = 관문 뒤 오프라인 연쇄 재생 확인(보충 24 §14.1). **VB-I** = V-B 무결성 점검(통과·실패 있음). **VB-M** = V-B 지표(보고만).
- **RR** = `D:/VISSIM_runs/20261004_sdmpc31_k8`(J1 기록 런, 읽기만). **OK2** = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **VBR** = `OK2/vb2`(이번 V-B 출력 뿌리). **TK** = `D:/VISSIM-merge/k8_gate_trees/k92b1`. **VBT** = `TK/vb2_e27ceac8`(커밋 K9-2-5 `e27ceac8` git archive + CR 고침).
- **SP** = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, **KB** = `SP/k92/bundle1`, **KV** = `KB/k92_vb`(r1 도구·보고서 자리, 보관), **KV2** = `KB/k92_vb2`(이번 구동기·재계산기), **AD32** = `KB/a32decl`, **AD33** = `KB/a33decl`(새 훅), **KI** = `KB/impl`.
- **KC** = K9-2-5 비교기 `k92_compare.py`. **REC** = K9-2-0 기록기 `k92_record.py`. **ZI** = 훅 영향 0 시험. **HARD** = 딱 같아야 하는 잎 묶음 H1–H5(H1 = 행동 CSV 바이트). **결과 넷** = PASS / FAIL / 보류 / INCOMPLETE.
- **SDMPC** = 모형 예측 제어 결정(T ≥ 900, 제어기 `wu-link`). **무제어** = T < 900(`no-control`). **NN / SN / SS** = 무제어←무제어 / 첫 SDMPC←무제어 / SDMPC←SDMPC.
- **OFF** = 그 런의 튜닝 그대로(키 없음). **B1** = W + 씨앗 묶음 팔. **사슬 첫 결정** = 직전 행동이 RR 파일인 결정, **사슬 이어받는 결정** = 직전 행동이 같은 사슬의 앞 결정 출력인 결정.
- **OUTW** = 지평 450 s 동안 Ω(통제 구역) 밖 모형 대기(veh·h). **FEED-4** = SC109 서측으로 들어오는 네 접근 몫. **Ω** = 모형 목적값(`selected_objective`). **PFO** = SDMPC 앞 단계의 웜 스타트 풀이.
- **PID** = 운영 체제가 프로세스에 주는 번호. **토큰** = 훅이 프로세스마다 한 번 만드는 이름 조각 `<pid>_<time_ns>_<16진 16자>`(보충 33 §2.1).

## 1. 한 일과 하지 않은 일

한 일 [실행]
- 보충 33 고정판 sha `76ae084b2b12eb82…` = `.sha256` = 고정점 `KB/AMENDMENT33_FIXED.md`(`9254e2792bad3675…`) 안 64자. 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `187242343570f1fe…`(214줄) = 작업 지시 값.
- 보충 33 §6.1 고정: `KB/a33_pins.sha256` = 기대 파일 `AD33/a33_pins.expected.sha256` 바이트(`cmp` 같음, `a1b02027c3238dcb…`, 63/63 OK). LOG에 고정점 33 sha·고정 목록 sha·구동기 `87b89ce4…`·재계산기 `6531a5e8…`·새 훅 `691fe810…`을 적은 뒤 발사(LOG "V-B 재실행 (보충 33 §6.1): 고정" 항목). 자기 시험은 다시 돌리지 않고 고정 출력을 읽어 확인했습니다(공개 E1).
- `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain` 한 번(WMI 분리, BelowNormal 16384, `PYTHONHASHSEED=0`, `python -B`; 2026-10-22 15:28:04, cmd.exe PID 6736). 구동기가 V0–V10을 끝까지 돌고 `VB_CHAIN_DONE`을 남겼습니다(00:49:14). 진행 확인은 한 번에 510 s 이하, 이름·개수·로그 끝만 봤습니다.
- 끝난 뒤: 고정한 표 도구 `KV2/mk_vb2_tables.py`(`c59cef11…`) 한 번, 이 보고서와 사본 둘, LOG 항목.

하지 않은 일
- VISSIM·COM·러너·동결 0. 커밋·브랜치·푸시 0. 금지 시험 0. 봉인 시드(37/59/61/67)·봉인 뿌리·v3c3-s47·codex 64cf 열람 0. 도구 고침 0(구동기가 결정마다 VBT RS·SHO·REC·KC와 훅·고르기·도움 함수 바이트 전후를 봄). 끈 프로세스 0. 옛 VBR·옛 VBT 쓰기 0.

## 2. 단계 결과 (V0–V10)

| 단계 | 결과 | 기록 (`VBR/…`) sha256 앞 16자 | 메모 |
|---|---|---|---|
| V0 사전 점검 C1–C13 | 모두 참 | `check_v0.json` `d8bc2130d8ebb4fd`, `stages/V0.json` `1ccd7fb14391ed4c` | C1 보충 24–32, C2 보충 33 고정점, C3 결정 기록 앞 214줄, C4 GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·K8 `b9734abe`·status 0줄·`b9734abe..HEAD` 6·원격 k92 0·이름에 vb 든 worktree 0, C5 고정 목록 63줄·구동기/재계산기/훅/고르기/도움 함수/닫힌 목록 줄 각각 한 번·기대 sha, C10 VISSIM 0·남의 러너 0, C11 C: 42.4 GB·D: 411.5 GB, C13 보관 바이트 아홉 참. 보관 트리 목록 `archive_tree` = 10,660행 `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680`(고정점 33 검토 값과 같음), OK2 목록(vb2 밖, 옛 VBR 포함) 90,369파일 `929c27ff7dd62000…` |
| 스냅숏 s43 | s02 대비 SAME | `snap/s43_vb2_v0.json` `8cc4da7261ad968e`, 단계 `ace1ba2da15d37a9` | |
| V1 트리 | 참 | `stages/V1.json` `f717fe26733da996`, 빌드 기록 `TK/vb2_e27ceac8.build.json` `e2c4ee176a249cbd` | CR 형태 `CCCCCCCCCC`, `cr_pair(FRZ_K8b, VBT)`·`cr_pair(FRZ_K8, VBT)` 참, `tree_root_ok` 참, RS·SHO·CFG·SAF-K91·CFG-B1·REC·KC·`k92_replay.py`·`sa_arms.py`·`k92_a27.py` sha 기대값. 보고만: VBT 대 GWT8 작업 트리 바이트 다름 0, VBT에만 0, GWT8에만 1 |
| V2 팔 | 참 | `stages/V2.json` `091e01b5a415b2c5` | SAF-B1 `65cac7ea0b33d8f0…`; VB-I3 두 팔 참(바탕과 차이 = `/urban/capacity/head_floor_seed`·`/urban/sc109w_through_saturation` 두 경로, 증거 sha = VBT 커밋 증거, CFG-B1 `c8e3ee2c…`); C12 넷 모두 `phase_price.mode` 없음 |
| V3 ZI | 세 칸 PASS | `zi/zi.json` `8d1ae5a157e8a708`, `stages/V3.json` `45acdb2f52aa201f` | §3.1 |
| 스냅숏 s44 | s02 대비 SAME | `snap/s44_vb2_zi.json` `24d977a5cff1866c`, 단계 `dacd0b71871379b5` | |
| V4 OFF 사슬 | 14결정 종료 0 | `stages/V4.json` `fe1f7753e9159383` | 순서 VB-41w(8) → VB-31(2) → VB-43(2) → VB-41(2) |
| V5 OFF 관문 | PASS | `judge/vb_i1.json` `47de078e9c1a6333`, `judge/vb_reportonly.json` `9ab57fcfcf0611c8`, `stages/V5.json` `76cc5993bba65081` | VB-I1 4/4 PASS, VB-I2 14/14 참, VB-I7 14/14 참; 보고 전용 표(§0, §3.3) |
| 스냅숏 s45 | s02 대비 SAME | `snap/s45_vb2_off.json` `59a2c2f23fd611e1`, 단계 `f19424740a39dc17` | |
| V6 B1 사슬 | 41결정 종료 0 | `stages/V6.json` `c8bd717357b27e21` | 순서 VB-41w(8) → VB-31(11) → VB-43(11) → VB-41(11) |
| V7 무결성 | 모두 참 | `judge/vb_i.json` `18eb483b006e62aa`, `stages/V7.json` `67beab1ac68dff9d` | VB-I2·I3·I4·I6·I7 55결정; SDMPC 고르기 상태 `selected` 41·`no_match` 2 |
| V8 지표 | 표 만들어짐 | `judge/vb_m.json` `459369834f7c9df5`, `stages/V8.json` `8226e71c8e95cade` | 결정 줄 96(REC 41 + OFF 14 + B1 41), 사슬 줄 12 |
| V9 재계산 | 같음 | `recalc/recalc.json` `bee4d4622b79bc82`, `stages/V9.json` `bc14df47fe45b7be` | VB-I5: 비교 4,204칸, 다름 0(재계산기 `6531a5e8…`, 구동기 import 0, 180.2 s) |
| 스냅숏 s46 | s02 대비 SAME | `snap/s46_vb2_end.json` `583592df84638b5b`, 단계 `5d3c32912fe42419` | |
| V10 끝 대조 | 모두 참 | `stages/V10.json` `3ec43f2d9377399f` | a33 고정 63/63·바이트 = 기대, GWT8 상태 = V0, RR 목록 = V0, OK2 목록(vb2 밖, 옛 VBR 포함) = V0, 옛 VBT 목록 = V0(`d51f4dee…`), 보관 바이트 참, VISSIM 0; C: 42.4 GB·D: 398.7 GB |

## 3. 결과 표

