# K9-2 묶음 1 V-B 보고서 — 기록 위 오프라인 사슬 재생 (보충 33 재실행) — r3 완료 판 (r2 + VerifyVB 3 고침)

- **상태: 완료 판 r2.** V-B 구동기가 V0–V10을 모두 PASS 기록으로 마쳤습니다(2026-10-23 00:49:14 KST, STOP 파일 0). 무결성 점검: VB-I1(판정하는 사슬 첫 결정 4개) 4/4 PASS, VB-I2·VB-I3·VB-I4·VB-I6·VB-I7 55결정 모두 참, VB-I5 독립 재계산 4,204칸 다름 0 [실행]. 다음 단계는 VerifyVB(보충 33 §6.5)입니다. V-A와 푸시는 그 뒤 사용자 결정입니다.
- **[VerifyVB 3 고침, 2026-10-23]** 독립 검증(`KV/VERIFY_VB.md`)이 도구를 고정한 뒤 VB-I1–I7·VB-M 표·ZI (z2)–(z6)·고르기·훅 이름 넷·보관 대조를 원자료에서 다시 냈습니다: 구동기 판정 파일과 3,105칸 다름 0, 이 보고서 표 줄 243개 모두 같음, §9 sha 43줄 같음 [실행]. 사슬 두 결정(VB-41 B1 T=3,300 → 3,450)을 따로 자리에서 다시 돌려 두 결정 모두 행동 CSV 바이트 같음·HARD 같음·미분류 0(T=3,450은 선언한 직전 파일 해시 잎만 더 다름)이었고, T=3,300의 `no_match`도 그대로 다시 나왔습니다 [실행]. 숫자가 바뀐 곳은 둘(§3.7 B1 벽시계 합 6.53 → 6.52 h, 비용 어림과 견준 말), 단위 표시 하나(머리 크기), 사실 더함 하나(`no_match` 두 결정, §0-5)입니다. 변경 기록은 §10.
- 판 r3 = r2(보충 33 재실행, D-K9-65·66) + VerifyVB 3 고침(§10). r2 = `KV/K92_VB_REPORT_r2.md` = `KB/VB_REPORT_r2.md` = `OK2/vb2/K92_VB_REPORT_r2.md`(sha256 `79e7cb03c65151fb240d33af3a362cda5b985bd4fac6bc832fc0999983e424a0`, 보관). r1 = STOP 판(`KV/K92_VB_REPORT_stop_r1.md` = `KB/VB_REPORT_stop_r1.md` = `OK2/vb/K92_VB_REPORT.md`, sha256 `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00`, 보관). 정본 = `KB/k92_vb/K92_VB_REPORT.md`, 같은 바이트 사본 = `KB/VB_REPORT.md`, `OK2/vb2/K92_VB_REPORT.md`(보충 33 §8). 고칠 때는 정본을 고치고 다시 복사합니다.
- 쓴 자리: VBR = `OK2/vb2`(9.7 GB — `du -h` 표시, 2의 거듭제곱 단위; 바이트로 10,391,383,863 B ≈ 10.4 GB [VerifyVB 3]), VBT = `TK/vb2_e27ceac8`(2.1 GB — 같은 표시; 2,150,845,988 B, 빌드 기록 `TK/vb2_e27ceac8.build.json`). 옛 VBR `OK2/vb`·옛 VBT `TK/vb_e27ceac8`·`KV`의 옛 도구는 보관이고 바뀌지 않았습니다(V0 C13·V10 대조, §2).
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
   - [VerifyVB 3 더함, 사실만] 두 결정의 출력 JSON은 `green_times`·`offsets` 전체가 바로 앞 B1 결정과 같고, `diagnostics.sdmpc_prediction_sequence`가 없으며, `selected_objective` = `held_objective`입니다. 후보 가운데 하나(AD 값)는 녹색·오프셋이 출력과 같지만 미래 블록 녹색 2개를 가지고 있어(출력에는 없음) 서명 조건 (m1)에서 맞지 않았고, 모든 후보의 시각 조건 (m2)은 참이었습니다 [실행]. 직전 계획을 그대로 유지한 결정으로 보이지만 [추론], 까닭은 이 보고에서 정하지 않습니다. 두 결정 재실행에서 T=3,300의 `no_match`(후보 3, 맞음 0)는 그대로 다시 나왔습니다 [실행].
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

### 3.1 ZI 세 칸 (`VBR/zi/<칸>/zi_judge.json`)

| 칸 | (z1) | (z2) CSV 같음 | (z3) KC 결과 넷 | (z4) 진행 기록 | (z5) 벽시계 잎만 | (z6) 끔에 훅 파일 0 | (z7) 훅 무결성·고르기 | 칸 결과 |
|---|---|---|---|---|---|---|---|---|
| z1_off | 참 | 참 | PASS | 참 | 참 | 참 | 참, `selected` | PASS |
| z1_b1 | 참 | 참 | PASS | 참 | 참 | 참 | 참, `selected` | PASS |
| z2_b1 | 참 | 참 | PASS | 참 | 참 | 참 | 참, `no_candidate` | PASS |

훅 비용 (보고만)

| 칸 | 훅 끔 벽시계 (s) | 훅 켬 벽시계 (s) | 켬/끔 비 | 후보 수 | 맞는 후보 | 훅 안 시간 합 (s) | 후보 파일 합 (MB) | `loaded` 파일 수 |
|---|---|---|---|---|---|---|---|---|
| z1_off | 689.2 | 694.0 | 1.007 | 10 | 1 | 11.2 | 11.3 | 11 |
| z1_b1 | 689.2 | 696.6 | 1.011 | 10 | 1 | 11.2 | 11.3 | 11 |
| z2_b1 | 29.5 | 28.9 | 0.980 | 0 | 0 | 0.0 | 0.0 | 1 |

- z1_off: 두 출력 JSON의 차이 잎 36개, 벽시계 이름 경로 17개, 그 밖 0개.
- z1_b1: 두 출력 JSON의 차이 잎 36개, 벽시계 이름 경로 17개, 그 밖 0개.
- z2_b1: 두 출력 JSON의 차이 잎 3개, 벽시계 이름 경로 3개, 그 밖 0개.
- z1_off 훅 끔 출력 대 RR 기록(보고만): 결과 넷 PASS, HARD SAME, 미분류 0, 허용 수 {'V': 6, 'F1': 12, 'F3': 33, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2}.

- 상태는 V-B 55결정 밖의 RR v3c3-s43 두 시각입니다(z1: T=1,050 SS, z2: T=750 NN). 칸마다 같은 준비 폴더·같은 출력 경로로 훅 끔 → 훅 켬을 돌렸습니다(보충 32 §3.5).
- 보충 32 P12(같은 경로면 16진 토큰도 같다는 [추론])는 이번 실행에서도 세 칸 모두 그대로였습니다 [실행 (z5) 참].
- 새 훅이 더한 프로세스마다 `os.urandom(8)`·`time.time_ns()` 한 번이 결정 출력을 바꾸지 않았음을 세 칸이 보입니다(보충 33 P8) [실행].

### 3.2 VB-I1 판정 4결정 (`VBR/judge/vb_i1.json`)

| 사슬·T | 결과 넷 | HARD | 미분류 | 허용 수 | A_K92 줄 | D5 뿌리 점검 | 칸 결과 |
|---|---|---|---|---|---|---|---|
| VB-41w/T000001 | **PASS** | SAME | 0 | {'V': 6, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 0 | 없음 | PASS |
| VB-31/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 31, 'A_K92': 2, 'R3-01': 2} | 2 | 참 | PASS |
| VB-43/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 29, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 2 | 참 | PASS |
| VB-41/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 32, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 2 | 참 | PASS |

- VB-I1 4결정 모두 PASS: 참. OFF 14결정 VB-I2: 참, VB-I7: 참.

- 비교 = `KC.compare(RR 결정 폴더, VBR/chain/<사슬>_off/dec, T, VBT, keyed=None, old_root=그 런의 동결본)`(보충 32 §2.1). 이 4결정도 새 훅을 켠 채 돌았으므로 "훅을 켠 결정 출력 = RR 기록"의 증거이기도 합니다.
- 보충 32 P13(VB-41w T=1의 직접 선례 없음)은 이번 실행에서도 PASS였습니다 [실행].

### 3.3 보고 전용 10결정 (`VBR/judge/vb_reportonly.json`; 판정 아님, D-K9-62·66)

| 사슬 | T (직전 T) | 꼴 | 결과 넷(참고) | CSV 같음 | 목록 안 HARD / 목록의 HARD | 목록 안 미분류 경로 | **목록 밖 경로 수** (잎 수) | 그중 `action_token` 꼴 | 목록 밖 HARD | 잘림 | 보이지 않은 목록 잎 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VB-41w | 150 (1) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 300 (150) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 450 (300) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 600 (450) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 750 (600) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 900 (750) | SN | FAIL | 참 | 1 / 1 | 8 | **11** (31) | 11 | 0 | 없음 | 0 |
| VB-41w | 1050 (900) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (29) | 11 | 0 | 없음 | 0 |
| VB-31 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (27) | 11 | 0 | 없음 | 0 |
| VB-43 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (29) | 11 | 0 | 없음 | 0 |
| VB-41 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (31) | 11 | 0 | 없음 | 0 |

- VB-41w T=150: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=300: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=450: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=600: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=750: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=900: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-41w T=1050: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-31 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-43 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-41 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)

- 목록 밖 `action_token` 꼴 경로(서로 다른 것) 11개. STOP 판 r1의 11경로와 견주면: 같은 경로 11개, 이번에 새로 보인 경로 0개, 이번에 보이지 않은 경로 0개.
- `action_token` 꼴이 아닌 목록 밖 차이: 0건

- 판정 아님, STOP 아님(D-K9-62·66). 결과 넷 값은 참고로만 적었습니다. 닫힌 목록 `AD32/vb_closed_leaves.json`(`b800be45…`)은 바꾸지 않았습니다.
- 목록 밖 경로의 까닭 추론은 §0의 정해진 글에 있습니다. 목록 안 HARD 경로(NN·SN: `/prediction_error/source_action_json`; SS: 그것과 `/metadata/sdmpc_state/previous_application/receipt_sha256`·`…/source`)는 목록이 정한 대로 모두 보였습니다(보이지 않은 목록 잎 0).

### 3.4 VB-I2·VB-I7 — OFF 14결정 (`VBR/judge/vb_i1.json` `/off_rows`)

| 사슬 | T | VB-I2 | VB-I7 | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |
|---|---|---|---|---|---|---|
| VB-41w | 1 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 150 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 300 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 450 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 600 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 750 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 900 | 참 | 참 | selected | 10 / 1 | 10.9 |
| VB-41w | 1050 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-31 | 3000 | 참 | 참 | selected | 8 / 1 | 8.7 |
| VB-31 | 3150 | 참 | 참 | selected | 8 / 1 | 8.5 |
| VB-43 | 3000 | 참 | 참 | selected | 6 / 1 | 7.2 |
| VB-43 | 3150 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-41 | 3000 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41 | 3150 | 참 | 참 | selected | 10 / 1 | 11.1 |

### 3.5 VB-I2–VB-I7 (55결정; `VBR/judge/vb_i.json`, VB-I5 = `VBR/recalc/recalc.json`)

| 점검 | 결과 |
|---|---|
| VB-I2 | 참 |
| VB-I3 | 참 |
| VB-I4 | 참 |
| VB-I6 | 참 |
| VB-I7 | 참 |
| VB-I5 (재계산 같음) | 참 |

- SDMPC 결정의 고르기 상태 개수: {'selected': 41, 'no_match': 2}. `selected`가 아닌 SDMPC 결정: [['VB-41', 'b1', 3300, 'no_match'], ['VB-41', 'b1', 4500, 'no_match']].
- VB-I6 VB-41w: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참, T=150 값 = T=1 값 = s 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613']
- VB-I6 VB-31: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1384.6154', '1384.6154', '1384.6154', '1384.6154', '1384.6154']
- VB-I6 VB-43: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774']
- VB-I6 VB-41: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613']

| 사슬 | 팔 | T | VB-I2 | VB-I7 | SDMPC | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |
|---|---|---|---|---|---|---|---|---|
| VB-41w | off | 1 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 150 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 300 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 450 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 600 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 750 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 900 | 참 | 참 | 참 | selected | 10 / 1 | 10.9 |
| VB-41w | off | 1050 | 참 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-31 | off | 3000 | 참 | 참 | 참 | selected | 8 / 1 | 8.7 |
| VB-31 | off | 3150 | 참 | 참 | 참 | selected | 8 / 1 | 8.5 |
| VB-43 | off | 3000 | 참 | 참 | 참 | selected | 6 / 1 | 7.2 |
| VB-43 | off | 3150 | 참 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-41 | off | 3000 | 참 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41 | off | 3150 | 참 | 참 | 참 | selected | 10 / 1 | 11.1 |
| VB-41w | b1 | 1 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 150 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 300 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 450 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 600 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 750 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 900 | 참 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41w | b1 | 1050 | 참 | 참 | 참 | selected | 7 / 1 | 7.5 |
| VB-31 | b1 | 3000 | 참 | 참 | 참 | selected | 8 / 1 | 8.9 |
| VB-31 | b1 | 3150 | 참 | 참 | 참 | selected | 11 / 1 | 12.1 |
| VB-31 | b1 | 3300 | 참 | 참 | 참 | selected | 6 / 1 | 6.7 |
| VB-31 | b1 | 3450 | 참 | 참 | 참 | selected | 7 / 1 | 8.0 |
| VB-31 | b1 | 3600 | 참 | 참 | 참 | selected | 6 / 1 | 6.8 |
| VB-31 | b1 | 3750 | 참 | 참 | 참 | selected | 5 / 1 | 6.1 |
| VB-31 | b1 | 3900 | 참 | 참 | 참 | selected | 3 / 1 | 3.5 |
| VB-31 | b1 | 4050 | 참 | 참 | 참 | selected | 2 / 1 | 2.5 |
| VB-31 | b1 | 4200 | 참 | 참 | 참 | selected | 8 / 1 | 9.4 |
| VB-31 | b1 | 4350 | 참 | 참 | 참 | selected | 5 / 1 | 5.6 |
| VB-31 | b1 | 4500 | 참 | 참 | 참 | selected | 5 / 1 | 6.0 |
| VB-43 | b1 | 3000 | 참 | 참 | 참 | selected | 9 / 1 | 10.0 |
| VB-43 | b1 | 3150 | 참 | 참 | 참 | selected | 5 / 1 | 5.9 |
| VB-43 | b1 | 3300 | 참 | 참 | 참 | selected | 4 / 1 | 4.6 |
| VB-43 | b1 | 3450 | 참 | 참 | 참 | selected | 8 / 1 | 9.2 |
| VB-43 | b1 | 3600 | 참 | 참 | 참 | selected | 6 / 1 | 6.8 |
| VB-43 | b1 | 3750 | 참 | 참 | 참 | selected | 9 / 1 | 10.0 |
| VB-43 | b1 | 3900 | 참 | 참 | 참 | selected | 8 / 1 | 8.8 |
| VB-43 | b1 | 4050 | 참 | 참 | 참 | selected | 6 / 1 | 7.0 |
| VB-43 | b1 | 4200 | 참 | 참 | 참 | selected | 11 / 1 | 12.4 |
| VB-43 | b1 | 4350 | 참 | 참 | 참 | selected | 7 / 1 | 7.6 |
| VB-43 | b1 | 4500 | 참 | 참 | 참 | selected | 7 / 1 | 7.9 |
| VB-41 | b1 | 3000 | 참 | 참 | 참 | selected | 11 / 1 | 11.9 |
| VB-41 | b1 | 3150 | 참 | 참 | 참 | selected | 4 / 1 | 4.5 |
| VB-41 | b1 | 3300 | 참 | 참 | 참 | no_match | 3 / 0 | 3.9 |
| VB-41 | b1 | 3450 | 참 | 참 | 참 | selected | 5 / 1 | 5.7 |
| VB-41 | b1 | 3600 | 참 | 참 | 참 | selected | 9 / 1 | 9.9 |
| VB-41 | b1 | 3750 | 참 | 참 | 참 | selected | 8 / 1 | 9.2 |
| VB-41 | b1 | 3900 | 참 | 참 | 참 | selected | 7 / 1 | 8.2 |
| VB-41 | b1 | 4050 | 참 | 참 | 참 | selected | 8 / 1 | 9.0 |
| VB-41 | b1 | 4200 | 참 | 참 | 참 | selected | 9 / 1 | 10.1 |
| VB-41 | b1 | 4350 | 참 | 참 | 참 | selected | 6 / 1 | 6.7 |
| VB-41 | b1 | 4500 | 참 | 참 | 참 | no_match | 2 / 0 | 2.5 |

- 재계산기 요약 키: ['equal', 'n_compared', 'n_diff', 'schema', 'tool_sha256', 'vbr']

- **`selected`가 아닌 SDMPC 결정 2개(눈에 띄게 적음, 보충 32 §2.5)**: VB-41 B1 T=3,300(후보 3, 맞음 0)과 T=4,500(후보 2, 맞음 0), 상태 `no_match`. 그 두 결정의 VB-M5·M6·M8 = 없음(`record:no_match`). 두 결정의 고른 행동 SC109 p2·p3·p4는 바로 앞 B1 결정(T=3,150, T=4,350)과 같은 값입니다 [실행 §4.5 표]. 까닭은 이 보고에서 정하지 않습니다. VerifyVB 3이 더한 사실(녹색·오프셋 전체, 예측 순서 없음, 고른 목적값 = 유지 목적값, 후보별 어긋난 자리)은 §0 5번에 있습니다.
- VB-I6: 하한 키 이름은 결정마다 하나이고 그 런의 기대 이름과 같습니다(`K92_VALUES.json` `/p0_2/f_expected_floor_keys`).

### 3.6 훅 폴더 이름 요약 (보고만; 보충 33 §8-5)

- 훅 폴더 58/58개 있음. `loaded` 파일 합 381, 서로 다른 토큰 합 381(후보가 있는 토큰 323), 후보 폴더 합 323.
- 이름 꼴: 옛 꼴 이름 0, 그 밖의 이름 0, `hook_error_*` 0, `hook_setup_error_*` 0.
- 같은 PID를 둘 이상의 토큰이 받은 묶음(= 한 폴더 안 PID 재사용): 폴더 1개에서 묶음 1개(더 생긴 토큰 1). 그 묶음들의 후보 `time_ns` 구간 겹침 0건.
- 이 표의 짝 점검(참고, 판정은 VerifyVB): 모든 후보 토큰에 `loaded` 있음 참, PID = 토큰 첫 조각 참, 순번 1부터 이어짐 참, 후보 폴더 안 파일 꼴 참, 어댑터 `loaded` 폴더마다 하나 참.

| 훅 폴더 | `loaded` | 토큰 (후보 있음) | 후보 | 같은 PID 묶음 (더 생긴 토큰) | 겹침 |
|---|---|---|---|---|---|
| VB-41w off T=1 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=150 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=300 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=450 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=600 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=750 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=900 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| VB-41w off T=1050 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41w b1 T=1 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=150 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=300 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=450 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=600 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=750 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=900 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41w b1 T=1050 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-31 off T=3000 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 off T=3150 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=3000 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=3150 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-31 b1 T=3300 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-31 b1 T=3450 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-31 b1 T=3600 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-31 b1 T=3750 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-31 b1 T=3900 | 4 | 4 (3) | 3 | 0 (0) | 0 |
| VB-31 b1 T=4050 | 3 | 3 (2) | 2 | 0 (0) | 0 |
| VB-31 b1 T=4200 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=4350 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-31 b1 T=4500 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-43 off T=3000 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 off T=3150 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3000 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3150 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-43 b1 T=3300 | 5 | 5 (4) | 4 | 0 (0) | 0 |
| VB-43 b1 T=3450 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-43 b1 T=3600 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 b1 T=3750 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3900 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-43 b1 T=4050 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 b1 T=4200 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-43 b1 T=4350 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-43 b1 T=4500 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-41 off T=3000 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41 off T=3150 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| VB-41 b1 T=3000 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-41 b1 T=3150 | 5 | 5 (4) | 4 | 0 (0) | 0 |
| VB-41 b1 T=3300 | 4 | 4 (3) | 3 | 0 (0) | 0 |
| VB-41 b1 T=3450 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-41 b1 T=3600 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41 b1 T=3750 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-41 b1 T=3900 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-41 b1 T=4050 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-41 b1 T=4200 | 10 | 10 (9) | 9 | 1 (1) | 0 |
| VB-41 b1 T=4350 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-41 b1 T=4500 | 3 | 3 (2) | 2 | 0 (0) | 0 |
| ZI z1_off | 11 | 11 (10) | 10 | 0 (0) | 0 |
| ZI z1_b1 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| ZI z2_b1 | 1 | 1 (0) | 0 | 0 (0) | 0 |

- 이 절은 보고만입니다. 훅 이름 꼴·토큰 짝의 판정은 VerifyVB가 보충 33 §6.5 넷으로 합니다.
- **PID 재사용 1번**: VB-41 B1 T=4,200 훅 폴더에서 PID 3024를 두 프로세스(토큰 둘)가 받았습니다. 새 이름에서는 두 토큰이 달라 폴더·파일이 겹치지 않았고, 두 토큰의 후보 `time_ns` 구간도 겹치지 않았습니다(차례로 뜬 두 프로세스) [실행]. 이 결정의 고르기 상태는 `selected`, VB-I7 참입니다. 옛 이름(보충 32)이었다면 r1과 같은 `hook_error`가 났을 꼴입니다 [추론].
- `loaded` 수 = 토큰 수(381)이고, 후보가 있는 토큰 323 = 후보 폴더 323입니다. 토큰마다 후보는 한 개였습니다(작업자 한 프로세스가 `omega_costs`를 한 번 부름) [실행].

### 3.7 사슬 결정 벽시계 (구동기 `done` 기록, 보고만)

| 사슬 | 팔 | 결정 수 | 벽시계 합 (h) | 최소 (s) | 최대 (s) |
|---|---|---|---|---|---|
| VB-41w | off | 8 | 0.46 | 25.0 | 744.3 |
| VB-41w | b1 | 8 | 0.45 | 27.0 | 732.7 |
| VB-31 | off | 2 | 0.41 | 727.5 | 733.3 |
| VB-31 | b1 | 11 | 1.99 | 384.4 | 778.3 |
| VB-43 | off | 2 | 0.42 | 727.7 | 787.0 |
| VB-43 | b1 | 11 | 2.10 | 521.5 | 790.9 |
| VB-41 | off | 2 | 0.38 | 615.3 | 754.8 |
| VB-41 | b1 | 11 | 1.99 | 354.5 | 795.5 |

- 사슬 결정 벽시계 합: OFF 1.67 h, B1 6.52 h [계산; VerifyVB 3 고침: r2의 6.53 h는 사슬별로 반올림한 값을 더한 것, 41결정 합은 23,466 s = 6.518 h]. 구동기 전체: 2026-10-22 15:28:04 발사 → 10-23 00:49:14 끝(약 9.4 h; ZI 약 0.8 h 포함) [실행]. 보충 33 §6.6 어림 9.5–10 h보다 조금 짧습니다(VerifyVB 3 고침: r2는 "안쪽"이라 적음).
- SDMPC 결정만: B1 35결정 중앙 710.4 s(354.5–795.5), OFF 8결정 중앙 733.5 s(615.3–787.0) [계산 `vb_m.json` `wall_run_sec`]. RR 기록 `decision_wall_sec`(같은 T, 35결정) 중앙 493.8 s는 재는 자리가 달라 같은 양이 아닙니다(기록 런은 VISSIM과 함께 돈 러너 안의 값).

## 4. VB-M 지표 (`VBR/judge/vb_m.json`; 보고만, 모형 안 값, 문턱 없음)

읽는 법
- 줄은 (사슬, 쪽, T)마다 하나입니다. 쪽: **B1** = B1 사슬(41결정), **OFF** = 훅을 단 OFF 사슬(14결정), **REC** = RR 기록 결정 JSON(같은 T). 같은 T끼리 나란히 둡니다. 사슬끼리·시드끼리 더하거나 평균 내지 않습니다(보충 24 §14.1).
- VB-M1 p2·p3·p4 = `green_times.SC109_p{2,3,4}`(s). VB-M2·M3는 사슬 줄 표. VB-M4 = 하한·씨앗 묶임·나름/갱신 칸. VB-M5 = 174 사슬 T+450·사슬 최대·직진 용량 묶임 비·E_out/220과 사슬 줄 표의 k92_w/k92_hb 키 결정 수. VB-M6 = OUTW·FEED-4(몫)·Ω. VB-M7 = PFO>유지 / 고름>유지·selection_status. VB-M8 = 유령 끝. VB-M9 = CSV=REC·벽시계와 사슬 줄 표의 "기록과 CSV 처음 다른 T". 정의 원문은 `vb_m.json`의 `definitions`와 보충 32 §3.6.
- 기록 기반 칸(VB-M5·M6의 OUTW·FEED-4·M8)은 고르기 상태가 `selected`인 B1·OFF 결정에만 있습니다. REC 쪽은 "없음"(기록 런에 기록기 없음), 무제어 결정은 "없음"(SDMPC 예측 없음), `no_match` 두 결정(VB-41 B1 T=3,300·4,500)도 "없음"입니다.
- 키 끔 쪽(OFF)의 기록 기반 값은 VB-31·43·41의 T=3,000·3,150과 VB-41w 8결정에만 있고, T=3,300–4,500은 "없음"입니다(추가 재생 없음, 보충 32 P3).
- 벽시계 칸: B1·OFF = 구동기가 잰 어댑터 실행 시간(`run_t<T>.json` `wall_sec`, 훅 켬), REC = 기록 JSON의 `metadata.decision_wall_sec`. 재는 자리가 달라 같은 양이 아닙니다.
- **Ω는 Ω 밖 대기(OUTW, FEED-4 몫)와 같은 줄에서만 읽습니다**(D-K9-32, 보충 24 §7-1). REC 줄의 Ω는 OUTW가 "없음"이라 그 줄만으로 Ω 차이를 인용하지 않습니다.

### 4.1 B1 대 OFF — 같은 상태 8개에서 Ω와 Ω 밖을 함께 (보고만) [실행 `vb_m.json`, 차이는 계산]

B1과 OFF가 둘 다 기록을 가진 상태는 이 8개뿐입니다. 두 쪽은 같은 RR 관측을 쓰고, 직전 행동만 각자 사슬의 앞 결정입니다(사슬 첫 결정 T=3,000은 둘 다 RR 기록).

| 사슬 | T | Ω B1 | Ω OFF | Ω B1−OFF | OUTW B1 (veh·h) | OUTW OFF | OUTW B1−OFF | FEED-4 B1 | FEED-4 OFF | FEED-4 B1−OFF | 174 사슬 T+450 B1 / OFF | E_out/220 B1 / OFF | 유령 끝 B1 / OFF | p3 B1 / OFF (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VB-41w | 900 | 328.36 | 332.98 | −4.62 | 671.13 | 674.10 | −2.96 | 56.83 | 55.99 | +0.84 | 14.66 / 78.88 | 0.126 / 0.016 | 4.46 / 4.34 | 85.41 / 88.09 |
| VB-41w | 1,050 | 410.88 | 414.57 | −3.69 | 805.29 | 807.18 | −1.89 | 63.23 | 61.98 | +1.25 | 19.38 / 80.82 | 0.120 / 0.062 | 2.92 / 3.24 | 79.41 / 88.63 |
| VB-31 | 3,000 | 473.44 | 483.18 | −9.73 | 1,018.03 | 1,021.80 | −3.77 | 144.03 | 146.16 | −2.14 | 86.53 / 234.65 | 0.285 / 0.066 | 6.09 / 6.18 | 43.65 / 36.71 |
| VB-31 | 3,150 | 464.01 | 473.69 | −9.68 | 1,006.14 | 1,009.87 | −3.73 | 151.26 | 151.43 | −0.18 | 84.93 / 208.91 | 0.230 / 0.019 | 5.35 / 5.44 | 40.69 / 35.21 |
| VB-43 | 3,000 | 459.08 | 470.01 | −10.93 | 1,019.94 | 1,022.80 | −2.86 | 144.01 | 145.35 | −1.33 | 50.62 / 171.69 | 0.324 / 0.126 | 4.42 / 4.83 | 44.65 / 37.09 |
| VB-43 | 3,150 | 464.89 | 476.61 | −11.72 | 1,008.50 | 1,013.05 | −4.55 | 148.13 | 149.57 | −1.44 | 51.64 / 193.16 | 0.299 / 0.076 | 4.45 / 4.23 | 47.27 / 35.59 |
| VB-41 | 3,000 | 459.75 | 467.58 | −7.83 | 989.71 | 993.84 | −4.13 | 119.70 | 120.55 | −0.85 | 44.44 / 171.27 | 0.235 / 0.058 | 5.51 / 5.39 | 56.81 / 54.20 |
| VB-41 | 3,150 | 443.94 | 452.02 | −8.08 | 986.90 | 989.68 | −2.77 | 119.78 | 119.26 | +0.52 | 45.71 / 178.46 | 0.227 / 0.076 | 4.89 / 4.82 | 55.67 / 55.01 |

- 8개 모두 Ω와 OUTW가 B1 쪽에서 작고, FEED-4 몫은 3개에서 B1 쪽이 큽니다(VB-41w 두 T, VB-41 T=3,150) [계산]. 모두 모형 예측이고 VISSIM 실측이 아닙니다(§5).
- OFF 줄의 Ω는 RR 기록 Ω와 같은 값입니다(OFF 행동 CSV = 기록, §4.2–§4.5 표).
- OUTW는 Ω 밖 전체 모형 대기이고 FEED-4는 그 일부입니다. Ω와 OUTW는 서로 다른 자리를 재는 양이라 더하거나 빼지 않습니다.

### 4.2 VB-41w — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 1.0 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 27 | no_candidate |
| 1 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 25 | no_candidate |
| 1 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 17 | REC: recorder not run (J1 record) |
| 150 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 1.0 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 27 | no_candidate |
| 150 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 26 | no_candidate |
| 150 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 18 | REC: recorder not run (J1 record) |
| 300 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 1/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 29 | no_candidate |
| 300 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 30 | no_candidate |
| 300 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 20 | REC: recorder not run (J1 record) |
| 450 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 10/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 450 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 9/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 30 | no_candidate |
| 450 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 9/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 20 | REC: recorder not run (J1 record) |
| 600 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 21/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 600 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 20/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 29 | no_candidate |
| 600 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 20/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 21 | REC: recorder not run (J1 record) |
| 750 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 35/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 750 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 34/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 750 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 34/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 21 | REC: recorder not run (J1 record) |
| 900 | B1 | 26.00 | 85.41 | 29.59 | 1045.1613 | 0.0 | 41/45 | 14.66 | 34.88 | 0.237 | 0.126 | 671.13 | 56.83 (0.085) | 328.36 | 4.46 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 710 | selected |
| 900 | OFF | 26.00 | 88.09 | 26.91 | 없음 | 없음 | 40/45 | 78.88 | 78.88 | 0.929 | 0.016 | 674.10 | 55.99 (0.083) | 332.98 | 4.34 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 734 | selected |
| 900 | REC | 26.00 | 88.09 | 26.91 | 없음 | 없음 | 40/45 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 332.98 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 576 | REC: recorder not run (J1 record) |
| 1050 | B1 | 32.00 | 79.41 | 29.59 | 1045.1613 | 0.0 | 45/40 | 19.38 | 42.13 | 0.185 | 0.120 | 805.29 | 63.23 (0.079) | 410.88 | 2.92 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 733 | selected |
| 1050 | OFF | 30.90 | 88.63 | 21.47 | 없음 | 없음 | 44/40 | 80.82 | 80.82 | 0.926 | 0.062 | 807.18 | 61.98 (0.077) | 414.57 | 3.24 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 744 | selected |
| 1050 | REC | 30.90 | 88.63 | 21.47 | 없음 | 없음 | 44/40 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 414.57 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 546 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 8 | 0 (없음) | 7 | 1 | 0.35 | 0 / 0 | 0 / 0 | – | {'None': 6, 'best_observed_feasible_sdmpc': 2} | – |
| OFF | 8 | 0 (없음) | 7 | 1 | 0.35 | 0 / 0 | 0 / 0 | 없음 | {'None': 6, 'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 8 | 0 (없음) | 7 | 0 | 1.51 | 8 / 8 | 0 / 0 | 900 | {'None': 6, 'best_observed_feasible_sdmpc': 2} | 2 |

- VB-41w B1 하한 = max(기록 하한, s): ['T=1 참', 'T=150 참', 'T=300 참', 'T=450 참', 'T=600 참', 'T=750 참', 'T=900 참', 'T=1050 참']

### 4.3 VB-31 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 72.61 | 43.65 | 24.74 | 1045.1613 | 0.0 | 50/39 | 86.53 | 158.72 | 0.621 | 0.285 | 1018.03 | 144.03 (0.141) | 473.44 | 6.09 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 600 | selected |
| 3000 | OFF | 77.30 | 36.71 | 26.99 | 1045.1613 | 없음 | 50/39 | 234.65 | 234.65 | 0.832 | 0.066 | 1021.80 | 146.16 (0.143) | 483.18 | 6.18 | 참/거짓 | best_observed_feasible_sdmpc | 참 | 728 | selected |
| 3000 | REC | 77.30 | 36.71 | 26.99 | 1045.1613 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 483.18 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 490 | REC: recorder not run (J1 record) |
| 3150 | B1 | 74.62 | 40.69 | 25.68 | 1045.1613 | 0.0 | 51/38 | 84.93 | 129.20 | 0.720 | 0.230 | 1006.14 | 151.26 (0.150) | 464.01 | 5.35 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 750 | selected |
| 3150 | OFF | 76.83 | 35.21 | 28.96 | 1045.1613 | 없음 | 51/38 | 208.91 | 208.91 | 0.838 | 0.019 | 1009.87 | 151.43 (0.150) | 473.69 | 5.44 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 733 | selected |
| 3150 | REC | 76.83 | 35.21 | 28.96 | 1045.1613 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 473.69 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 494 | REC: recorder not run (J1 record) |
| 3300 | B1 | 69.37 | 45.94 | 25.68 | 1045.1613 | 0.0 | 51/35 | 88.53 | 159.55 | 0.716 | 0.319 | 993.46 | 147.10 (0.148) | 454.83 | 3.82 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 740 | selected |
| 3300 | REC | 75.33 | 35.21 | 30.46 | 1045.1613 | 없음 | 51/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 467.89 | 없음 | 참/참 | best_observed_feasible_sdmpc | – | 237 | REC: recorder not run (J1 record) |
| 3450 | B1 | 67.72 | 50.44 | 22.84 | 1045.1613 | 0.0 | 51/39 | 101.05 | 168.55 | 0.782 | 0.337 | 971.60 | 146.92 (0.151) | 461.94 | 5.38 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 675 | selected |
| 3450 | REC | 79.46 | 30.71 | 30.83 | 1045.1613 | 없음 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 472.95 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 389 | REC: recorder not run (J1 record) |
| 3600 | B1 | 62.96 | 56.44 | 21.60 | 1045.1613 | 0.0 | 51/40 | 103.34 | 179.83 | 0.810 | 0.399 | 936.57 | 144.20 (0.154) | 435.71 | 4.70 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 752 | selected |
| 3600 | REC | 76.27 | 29.96 | 34.77 | 1045.1613 | 없음 | 51/40 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 447.54 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 478 | REC: recorder not run (J1 record) |
| 3750 | B1 | 62.37 | 55.97 | 22.66 | 1045.1613 | 0.0 | 51/38 | 102.49 | 153.67 | 0.903 | 0.333 | 919.26 | 141.81 (0.154) | 441.50 | 4.58 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 3750 | REC | 74.73 | 27.00 | 39.27 | 1045.1613 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 453.49 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 488 | REC: recorder not run (J1 record) |
| 3900 | B1 | 60.87 | 55.97 | 24.16 | 1384.6154 | 0.0 | 51/41 | 116.73 | 174.84 | 0.811 | 0.295 | 924.08 | 142.65 (0.154) | 443.58 | 3.76 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 514 | selected |
| 3900 | REC | 73.04 | 23.25 | 44.71 | 1384.6154 | 없음 | 51/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 453.38 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 478 | REC: recorder not run (J1 record) |
| 4050 | B1 | 57.87 | 58.97 | 24.16 | 1384.6154 | 0.0 | 51/39 | 117.64 | 212.05 | 0.635 | 0.357 | 926.06 | 137.36 (0.148) | 451.89 | 4.50 | 참/참 | best_observed_feasible_sdmpc | 거짓 | 384 | selected |
| 4050 | REC | 69.48 | 22.31 | 49.21 | 1384.6154 | 없음 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 462.19 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 501 | REC: recorder not run (J1 record) |
| 4200 | B1 | 54.95 | 63.71 | 22.34 | 1384.6154 | 0.0 | 51/38 | 121.87 | 232.05 | 0.675 | 0.474 | 906.45 | 138.83 (0.153) | 433.29 | 5.69 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 778 | selected |
| 4200 | REC | 75.48 | 20.00 | 45.52 | 1384.6154 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 444.91 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 481 | REC: recorder not run (J1 record) |
| 4350 | B1 | 52.25 | 67.87 | 20.88 | 1384.6154 | 0.0 | 51/37 | 127.56 | 263.55 | 0.844 | 0.581 | 861.28 | 127.50 (0.148) | 420.42 | 4.18 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 613 | selected |
| 4350 | REC | 73.86 | 20.00 | 47.14 | 1384.6154 | 없음 | 51/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 434.67 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 257 | REC: recorder not run (J1 record) |
| 4500 | B1 | 49.05 | 71.62 | 20.33 | 1384.6154 | 0.0 | 52/37 | 86.97 | 264.52 | 0.866 | 0.815 | 832.42 | 117.81 (0.142) | 407.31 | 4.85 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 604 | selected |
| 4500 | REC | 73.86 | 20.00 | 47.14 | 1384.6154 | 없음 | 52/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 422.51 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 444 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 5 (3900) | 10 | 0 | 1.67 | 0 / 0 | 8 / 1 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 1.50 | 0 / 0 | 1 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 1 | 3.48 | 11 / 11 | 5 / 1 | 3000 | {'best_observed_feasible_sdmpc': 11} | 11 |

### 4.4 VB-43 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 57.73 | 44.65 | 38.63 | 1509.6774 | 0.0 | 49/37 | 50.62 | 113.00 | 0.669 | 0.324 | 1019.94 | 144.01 (0.141) | 459.08 | 4.42 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 791 | selected |
| 3000 | OFF | 57.15 | 37.09 | 46.76 | 1509.6774 | 없음 | 49/37 | 171.69 | 176.13 | 0.835 | 0.126 | 1022.80 | 145.35 (0.142) | 470.01 | 4.83 | 참/거짓 | best_observed_feasible_sdmpc | 참 | 787 | selected |
| 3000 | REC | 57.15 | 37.09 | 46.76 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 470.01 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 533 | REC: recorder not run (J1 record) |
| 3150 | B1 | 55.76 | 47.27 | 37.97 | 1509.6774 | 0.0 | 49/36 | 51.64 | 135.55 | 0.717 | 0.299 | 1008.50 | 148.13 (0.147) | 464.89 | 4.45 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 660 | selected |
| 3150 | OFF | 55.29 | 35.59 | 50.12 | 1509.6774 | 없음 | 49/36 | 193.16 | 196.44 | 0.836 | 0.076 | 1013.05 | 149.57 (0.148) | 476.61 | 4.23 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 728 | selected |
| 3150 | REC | 55.29 | 35.59 | 50.12 | 1509.6774 | 없음 | 49/36 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 476.61 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 520 | REC: recorder not run (J1 record) |
| 3300 | B1 | 54.26 | 48.77 | 37.97 | 1509.6774 | 0.0 | 49/37 | 58.10 | 157.00 | 0.775 | 0.372 | 997.67 | 144.39 (0.145) | 460.30 | 3.70 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 522 | selected |
| 3300 | REC | 54.16 | 31.84 | 55.00 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 470.24 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 523 | REC: recorder not run (J1 record) |
| 3450 | B1 | 54.03 | 49.70 | 37.27 | 1509.6774 | 0.0 | 49/38 | 93.73 | 164.68 | 0.597 | 0.305 | 991.76 | 143.09 (0.144) | 460.86 | 3.94 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 740 | selected |
| 3450 | REC | 53.77 | 28.09 | 59.14 | 1509.6774 | 없음 | 49/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 471.75 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 546 | REC: recorder not run (J1 record) |
| 3600 | B1 | 54.03 | 53.45 | 33.52 | 1509.6774 | 0.0 | 49/37 | 101.92 | 194.00 | 0.601 | 0.289 | 965.97 | 141.36 (0.146) | 451.47 | 4.82 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 593 | selected |
| 3600 | REC | 55.27 | 28.09 | 57.64 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 462.17 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 416 | REC: recorder not run (J1 record) |
| 3750 | B1 | 51.96 | 58.32 | 30.72 | 1509.6774 | 0.0 | 49/39 | 107.45 | 190.55 | 0.556 | 0.306 | 933.73 | 141.90 (0.152) | 441.86 | 3.66 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 3750 | REC | 56.45 | 23.59 | 60.96 | 1509.6774 | 없음 | 49/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 452.47 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 528 | REC: recorder not run (J1 record) |
| 3900 | B1 | 50.67 | 62.24 | 28.09 | 1509.6774 | 0.0 | 49/37 | 117.96 | 225.55 | 0.633 | 0.435 | 919.37 | 143.39 (0.156) | 424.62 | 5.47 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 743 | selected |
| 3900 | REC | 59.63 | 20.50 | 60.86 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 436.37 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 544 | REC: recorder not run (J1 record) |
| 4050 | B1 | 49.17 | 63.74 | 28.09 | 1509.6774 | 0.0 | 49/34 | 91.88 | 264.64 | 0.903 | 0.652 | 918.99 | 140.66 (0.153) | 432.98 | 4.66 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 656 | selected |
| 4050 | REC | 59.07 | 21.78 | 60.15 | 1509.6774 | 없음 | 49/34 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 445.16 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 520 | REC: recorder not run (J1 record) |
| 4200 | B1 | 47.76 | 68.89 | 24.34 | 1509.6774 | 0.0 | 49/34 | 134.62 | 285.55 | 0.664 | 0.551 | 911.25 | 141.26 (0.155) | 429.55 | 4.56 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 4200 | REC | 62.64 | 20.44 | 57.92 | 1509.6774 | 없음 | 49/34 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 443.13 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 562 | REC: recorder not run (J1 record) |
| 4350 | B1 | 46.26 | 70.39 | 24.34 | 1509.6774 | 0.0 | 49/37 | 140.89 | 297.55 | 0.699 | 0.614 | 886.60 | 132.74 (0.150) | 421.94 | 3.83 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 665 | selected |
| 4350 | REC | 58.20 | 20.39 | 62.42 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 436.74 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 519 | REC: recorder not run (J1 record) |
| 4500 | B1 | 44.61 | 76.39 | 20.00 | 1509.6774 | 0.0 | 49/36 | 75.71 | 314.32 | 0.860 | 0.821 | 824.45 | 124.89 (0.151) | 400.63 | 6.73 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 701 | selected |
| 4500 | REC | 58.82 | 22.58 | 59.60 | 1509.6774 | 없음 | 49/36 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 417.80 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 481 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 6 (3750) | 10 | 3 | 2.14 | 0 / 0 | 6 / 0 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 1.50 | 0 / 0 | 1 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 0 | 3.17 | 11 / 11 | 2 / 0 | 3000 | {'best_observed_feasible_sdmpc': 11} | 11 |

### 4.5 VB-41 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 62.01 | 56.81 | 22.19 | 1045.1613 | 1.0 | 50/42 | 44.44 | 82.64 | 0.493 | 0.235 | 989.71 | 119.70 (0.121) | 459.75 | 5.51 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 784 | selected |
| 3000 | OFF | 66.18 | 54.20 | 20.61 | 없음 | 없음 | 50/42 | 171.27 | 171.27 | 0.890 | 0.058 | 993.84 | 120.55 (0.121) | 467.58 | 5.39 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 615 | selected |
| 3000 | REC | 66.18 | 54.20 | 20.61 | 없음 | 없음 | 50/42 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 467.58 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 449 | REC: recorder not run (J1 record) |
| 3150 | B1 | 62.76 | 55.67 | 22.57 | 1045.1613 | 0.0 | 51/38 | 45.71 | 80.98 | 0.431 | 0.227 | 986.90 | 119.78 (0.121) | 443.94 | 4.89 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 625 | selected |
| 3150 | OFF | 65.76 | 55.01 | 20.23 | 없음 | 없음 | 50/38 | 178.46 | 179.78 | 0.896 | 0.076 | 989.68 | 119.26 (0.121) | 452.02 | 4.82 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 755 | selected |
| 3150 | REC | 65.76 | 55.01 | 20.23 | 없음 | 없음 | 50/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 452.02 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 553 | REC: recorder not run (J1 record) |
| 3300 | B1 | 62.76 | 55.67 | 22.57 | 1045.1613 | 0.0 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 444.03 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 526 | no_match |
| 3300 | REC | 66.70 | 54.11 | 20.19 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 449.85 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 550 | REC: recorder not run (J1 record) |
| 3450 | B1 | 67.26 | 51.17 | 22.57 | 1045.1613 | 0.0 | 51/41 | 23.39 | 65.16 | 0.493 | 0.193 | 966.85 | 125.97 (0.130) | 441.42 | 5.20 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 456 | selected |
| 3450 | REC | 70.37 | 50.61 | 20.02 | 없음 | 없음 | 50/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 449.41 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 553 | REC: recorder not run (J1 record) |
| 3600 | B1 | 65.04 | 50.42 | 25.54 | 1045.1613 | 0.0 | 51/39 | 59.33 | 81.68 | 0.480 | 0.191 | 937.53 | 124.46 (0.133) | 427.09 | 4.80 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 759 | selected |
| 3600 | REC | 70.02 | 48.27 | 22.71 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 434.31 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 550 | REC: recorder not run (J1 record) |
| 3750 | B1 | 64.36 | 49.68 | 26.96 | 1045.1613 | 0.0 | 51/39 | 20.81 | 98.96 | 0.853 | 0.203 | 898.58 | 122.34 (0.136) | 419.47 | 4.78 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 796 | selected |
| 3750 | REC | 70.41 | 50.59 | 20.00 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 428.39 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 513 | REC: recorder not run (J1 record) |
| 3900 | B1 | 64.25 | 48.70 | 28.05 | 1045.1613 | 0.0 | 51/39 | 42.98 | 92.02 | 0.699 | 0.192 | 901.97 | 127.97 (0.142) | 408.08 | 4.76 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 756 | selected |
| 3900 | REC | 67.41 | 53.59 | 20.00 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 418.31 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 367 | REC: recorder not run (J1 record) |
| 4050 | B1 | 62.37 | 48.58 | 30.05 | 1045.1613 | 0.0 | 51/37 | 81.77 | 99.29 | 0.434 | 0.185 | 876.35 | 128.56 (0.147) | 404.45 | 3.68 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 732 | selected |
| 4050 | REC | 69.14 | 47.59 | 24.27 | 없음 | 없음 | 50/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 411.72 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 300 | REC: recorder not run (J1 record) |
| 4200 | B1 | 61.88 | 45.58 | 33.54 | 1045.1613 | 0.0 | 51/37 | 36.36 | 80.27 | 0.675 | 0.251 | 856.99 | 129.67 (0.151) | 388.07 | 3.72 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 729 | selected |
| 4200 | REC | 69.14 | 47.59 | 24.27 | 없음 | 없음 | 50/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 395.91 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 151 | REC: recorder not run (J1 record) |
| 4350 | B1 | 59.25 | 48.21 | 33.54 | 1045.1613 | 0.0 | 51/39 | 31.75 | 79.77 | 0.630 | 0.247 | 846.02 | 129.22 (0.153) | 373.20 | 3.63 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 634 | selected |
| 4350 | REC | 67.64 | 49.09 | 24.27 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 380.99 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 374 | REC: recorder not run (J1 record) |
| 4500 | B1 | 59.25 | 48.21 | 33.54 | 1045.1613 | 0.0 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 365.65 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 354 | no_match |
| 4500 | REC | 67.64 | 49.09 | 24.27 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 372.33 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 144 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 0 (없음) | 10 | 4 | 2.04 | 0 / 0 | 3 / 0 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 0.80 | 0 / 0 | 0 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 1 | 1.39 | 11 / 11 | 2 / 0 | 3000 | {'best_observed_feasible_sdmpc': 11} | 9 |

## 5. V-B가 보일 수 있는 것과 없는 것

- **보이는 것**: 기록된 J1 관측(RR) 위에서 B1 팔을 결정마다 이어 돌렸을 때 **모형 안에서** SC109 p3 녹색이 어떻게 가는지(VB-M1–M3), (173, p4) 하한이 씨앗에서 출발해 사슬로 나르는지(VB-M4, VB-I6), 모형 174 사슬 재고·직진 용량 묶임·`SC109_E_out`(VB-M5), Ω 밖 대기 OUTW와 FEED-4 몫(VB-M6), PFO 계수(VB-M7), 유령 movement 재고(VB-M8), 행동 CSV가 기록과 처음 달라지는 결정과 벽시계(VB-M9). 모두 모형 예측 값이고 결정마다 따로입니다.
- **보이지 않는 것**: VISSIM 반응, TTT, 실측 Ω, 실측 대기. 관측은 옛 제어기(J1 기록 런)가 만든 궤적이라, B1 사슬이 기록과 달라질수록 상태가 B1을 실제로 적용했을 때의 상태와 맞지 않습니다. 영수증은 "적용했다고 치는" 것입니다(보충 32 P9).
- **Ω 인용 규칙**: Ω(모형 목적값, `selected_objective`) 차이는 Ω 밖 대기 OUTW(와 FEED-4 몫)와 같은 줄에서만 읽습니다(보충 24 §7-1, D-K9-32). 이 보고는 Ω만 따로 떼어 인용하지 않습니다. 기록(REC) 쪽 OUTW는 없습니다(기록 런에 기록기 없음).
- **키 끔 쪽의 범위**: VB-M5·M6·M8의 키 끔 값은 훅을 단 OFF 사슬 14결정(VB-31·43·41의 T=3,000·3,150, VB-41w 8결정)에서만 있고, VB-31·43·41의 T=3,300–4,500은 "없음"입니다(추가 재생 없음, 보충 32 P3).
- **더하지 않음**: 사슬끼리·시드끼리 더하거나 평균 내지 않습니다. VB-41(대조)은 VB-31·VB-43 옆에 나란히만 둡니다(보충 24 §14.1 "무엇을 비교하나").

## 6. V-A에서 볼 것 (V-A는 사용자 결정 뒤; 이 워크플로 밖)

1. **SC109 p3 녹색**: J1 발병 정의(p3 ≤ 24.5 s) 결정 수와 첫 시각을 J1 기록과 같은 T끼리. V-B의 B1 사슬 표(§4)는 모형 안 값이라 VISSIM에서 같은 방향이 나온다는 보장이 없습니다 [추론].
2. **(173, p4) 하한**: 키 이름·값, `k92_hb_seed_binding`, `head_observation_groups_carried`·`_updated`. B1 폐루프에서는 모든 시드의 T=150 결정에 `head_observation_prior_discarded` = 1.0이 예상입니다(보충 24 §14.2).
3. **Ω와 Ω 밖**: Ω 감소를 볼 때 Ω 밖 대기(OUTW, FEED-4 몫)·`SC109_E_out`을 같은 표에(D-K9-32). V-B의 모형 OUTW와 V-A의 실측 대기는 다른 양입니다.
4. **174 사슬**: V-B의 모형 174 사슬 재고(VB-M5)는 모형 예측이고 VISSIM 링크 174의 실측 대기가 아닙니다. V-A에서는 실측 쪽을 보충 24 §7-1의 폐루프 표(J1_REPORT §3 꼴)로 따로 둡니다.
5. **결정 벽시계**: G-K5 예산 1.0158 안인지 보고. V-B 결정 벽시계(§3.7)는 훅을 켠 오프라인 재생 값입니다.
6. **측정 훅**: V-A에서 쓰지 않는다면 훅 관련 위험(이름 겹침 등)은 V-A에 없습니다. 쓴다면 이번 새 이름 규칙을 그대로 써야 합니다 [추론].
7. **보고 전용 `action_token` 경로**: 폐루프에서는 직전 행동이 러너가 쓴 실제 파일이므로 이 경로 차이는 오프라인 사슬의 산물로 봅니다 [추론]. V-A의 비교는 G-K0 꼴이 아니라 V-A 보충이 정합니다.

## 7. 한계 (보충 24 §14.1 "한계", 보충 32 §11, 보충 33 §13을 이번 실행에 맞춰)

1. 관측은 옛 제어기 궤적입니다. VISSIM 반응·TTT·Ω 실측은 보이지 않습니다.
2. 키 끔 = 기록은 사슬 첫 결정 4개(VB-I1)와 ZI z1_off 훅 끔 대 기록, 그리고 G-K0 상태에서만 직접 보입니다. 사슬 이어받는 OFF 10결정은 판정에서 빠지고 보고만입니다(D-K9-62, 보충 32 P1).
3. 닫힌 목록은 RR 기록 구조에서 만든 것이라, 해시로 한 번 더 감싼 잎(`action_token`)은 들어 있지 않습니다(§0). 목록은 바꾸지 않았습니다(D-K9-66).
4. 훅이 재는 자리는 `omega_costs` 응답뿐이고, `w_receiving_limited_steps`·`vissim` 칸은 재지 않습니다(보충 32 P2). 지평은 3블록(450 s) 고정입니다.
5. 영수증은 적용한 셈 치는 것입니다(보충 32 P9).
6. ZI는 V-B 밖 두 상태·세 칸에서만 훅 영향 0을 직접 봅니다. 그 밖의 결정은 같은 훅 코드라는 데서 미루어 봅니다 [추론]. 새 훅이 더한 `os.urandom(8)`·`time.time_ns()` 한 번의 영향 0도 ZI와 VB-I1이 실제 출력으로 봅니다.
7. D-K9-44(어댑터가 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 셈)는 이번 어댑터 실행에서도 코드 그대로입니다 [추론: 코드 그대로]; 고침은 묶음 2.
8. 토큰 겹침 확률은 0이 아니지만 겹치면 배타 생성이 거절해 STOP 쪽입니다(보충 33 §13-2).
9. 한 프로세스 안에서 훅이 두 번 실리는 꼴은 지금 코드에 생길 길이 보이지 않습니다(보충 33 §13-8). 같은 PID 토큰 묶음의 `time_ns` 겹침을 §3.6에 보고합니다.
10. 보충 24 §2.6의 한계 1–13, 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, 보충 30 §10, 보충 31 §9, 보충 32 §11, 보충 33 §13은 그대로입니다.

## 8. 공개 (보충 33 §8-4·§12, 보충 32 §5 "머리에 옮김")

### 이 V-B 재실행 단계의 공개

- **E1 자기 시험을 다시 돌리지 않음**: 작업 지시 글은 "PID 재사용 시험을 포함한 합성 자기 시험을 돌림"이었지만, 보충 33 §6.1-4는 V-B 단계가 자기 시험을 다시 돌리지 않는다고 정합니다(출력이 고정 목록 7–8·11–16줄에 있고 `AD33/dry_a33.py`는 출력 자리를 `AD33/dry/decl`로 박아 두어 다시 돌리면 고정 파일을 덮어씀 → S-K53). 그래서 고정 출력의 바이트(63/63)와 내용을 읽어 확인했습니다 [실행]: `dry_a33_summary.json` all_ok 참(static·hook·pidreuse·paths·mutants, BelowNormal 참), `dry_a33_pidreuse.json` P1–P8 참(P1 옛 훅 같은 PID → `hook_error`; P2·P3·P4·P6 새 훅 `selected`; P5 토큰 전체 강제 겹침 → 배타 생성 거절·`hook_error`; P7 결정끼리 독립; P8 강제 방법 통제), 구동기 자기 시험 t1–t7 참, 재계산기 자기 시험 26사례 참. 실제 PID 재사용의 직접 관찰은 이번 실행의 훅 폴더 이름 요약(§3.6)에 있습니다.
- **E2 세션 도우미**(판정 도구 아님, 첫 판정 파일 읽기 전 LOG 고정): 진행 확인 `KV2/poll_vb2.sh`(`81b4348b…`, 이름·개수만), 표 도구 `KV2/mk_vb2_tables.py`(`c59cef11…`; PASS·참/거짓은 구동기 파일 그대로 옮기고, 스스로 세는 것은 훅 폴더 이름 요약과 r1 11경로 대조뿐). 표 도구는 합성 폴더로 한 번 시험한 뒤 하한 소수 자리 한 곳만 고쳐 고정했습니다(고정 전, V-B 데이터 0).
- **E3 쓸모없는 명령 한 줄**: 고정 목록을 복사하던 명령 줄에 `cp AD33=1 2>/dev/null`이 잘못 섞여 들어갔습니다(`KB` 폴더에서). 대상이 하나뿐이라 `cp`가 오류로 끝났고 파일은 생기지 않았습니다 [실행 `ls`]. 고정 목록 복사·`cmp`·63/63은 같은 줄의 다음 명령으로 했습니다.
- **E4 진행 중 열람**: `VBR/driver_log.txt`·`steps.jsonl` 끝, 단계 이름, 발사 로그 끝. 여기에는 ZI 칸의 (z1)–(z7) 참/거짓과 결정 종료 코드·벽시계·고르기 상태 이름이 보입니다(목적값·예측값 0).
- **E5 보고서 쓰기**: 이 글은 구동기가 끝난 뒤 세션이 판정 파일을 읽고 표 도구 출력을 옮겨 썼습니다. VB-M 표의 숫자는 구동기 `judge/vb_m.json` 값 그대로입니다.
- **E6 실행 출력 쪽 사본 자리**: `OK2/vb2/K92_VB_REPORT.md`(VBR 안, V10 끝 대조 뒤에 씀; 보충 33 §8-3). 구동기 V10의 "OK2의 vb2 밖" 대조를 건드리지 않습니다.

### 보충 33 §12 공개 (요약; 원문은 보충 33)

- P1 이름 고침이 결정 글의 "후보 폴더"보다 넓음(`loaded`·오류 파일·배타 생성). P2 구동기·재계산기를 Declare가 씀(V-B 단계는 자기 시험을 다시 돌리지 않음). P3 확인 판 둘(S-K57 이름만 고침). P4 Declare가 STOP 판 r1 보관 사본을 씀. P5 Declare가 읽은 기록 자료(STOP 보고 r1, 멈춘 실행 출력은 sha만). P6 합성 강제의 한계(`-S` + `os.getpid` 바꿈). P7 시계 해상도에 기대지 않음(난수 조각이 가름). P8 훅이 더하는 일은 프로세스마다 `os.urandom(8)` 한 번. P9 VB-I7에 짝 점검을 더하지 않음(VerifyVB가 봄). P10 보충 32 P12·P13은 이번 재실행에서 다시 판가름. P11 B1 사슬은 이번이 첫 데이터. P12 Declare 스냅숏 SAME. P13 비용 어림 9.5–10 h. P14 `AD33/run_bn.py` 우선순위 설정 실패(V-B에서 쓰지 않음; 이 단계는 `KI/launch.ps1` WMI 16384로 발사). P15 검토 시험 세 번·보관 목록 도구 첫 시도 문법 오류. P16 고르기 자식 작업 폴더가 보관 `KV`(쓰기 아님).

### 보충 32 §7 공개 (요약)

- P1 D-K9-62는 사용자가 권장안이 아닌 (나)를 고른 것 — 사슬 이어받는 OFF 10결정은 판정이 아니라 보고. P2 측정 훅은 결정 프로세스 안의 읽기 전용 도구, 무제어 결정에는 기록 없음, `on_alloc` 부르지 않음, 지평 3블록. P3 VB-M5·M6·M8의 키 끔 값은 OFF 14결정에만. P4 D-K9-64 수용. P5·P15 Declare·검토가 읽은 자료는 V-B 데이터 아님. P6 VB-I7·VB-I3 파일 sha 조건은 STOP을 늘리는 쪽. P7 VB-I1 D5 뿌리 점검의 꼴. P8 기록기 `write`가 작업자에 표준 모듈을 더 실을 수 있음(ZI가 영향을 봄). P9 오프라인 영수증. P10 옛 줄 번호(`sdmpc.py:461-470` → `:513-533`). P11 "미분류 2–13개"의 뜻. P12 ZI (z5)의 토큰 가정. P13 VB-41w T=1 직접 선례 없음. P14 훅 이름 PID 겹침(r1에서 일어남 → 보충 33으로 고침).

### 물려받은 공개 (한 줄씩; 원문은 각 보충)

- 보충 27 §8: K9-2-1·K9-2-2 관문에서 G-K2를 HARD만으로, G-K4를 HARD 숫자만으로 판정했던 사실과 다시 판정(RJ-G2·RJ-G4) — 데이터를 본 뒤의 규칙 고침. 보충 27 §13: N이 어느 K9-2 트리에서 나온 경로인지 보지 못함 등 1–15.
- 보충 28 §9: A28-W는 결과를 짐작하는 상태의 허용, 명령줄 길이 점검은 안전 장치 등 1–18.
- 보충 29 §11: A_K92는 옛 뿌리가 필수, 다시 비교는 "같은 보고"를 요구, 망가뜨림 시험 범위 등 1–20.
- 보충 30 §10: 지속성 보고 21/22, F 잡 로그 걸러 읽기 한 번(개수만), J-0 글자 그대로 59/61, VerifyGates J-a 도구 사후 수정, 봉인 뿌리 등 1–17.
- 보충 31 §5·§9: `_seed47_path` 데이터 뒤 고침(사용자 결정), jb_unit 규칙 바꿈, 메인 세션 `grep -rl`, 검증 2차 공개 수용, 임시 트리 보관 등.
- 보충 24 §7-6 값 선택 표시: W = 5,209.8은 몫 가르기 뒤 선택(D-K9-34), 씨앗 s = 1045.1612903225805는 F-3 비블라인드(보충 24 §2.6-6).

## 9. 파일과 sha256 (조립 때 파일에서 다시 계산)

| 파일 | sha256 |
|---|---|
| 보충 33 고정판 `SP/K8_PREDECLARATION_AMENDMENT_33.md` | `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea` |
| 고정점 `KB/AMENDMENT33_FIXED.md` | `9254e2792bad367586c99c05925e649414c01601ea2e8642bcf575ed17f60908` |
| 고정 목록 `KB/a33_pins.sha256`(= `AD33/a33_pins.expected.sha256`, 63줄) | `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74` |
| 새 훅 `AD33/vbhook/sitecustomize.py` | `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c` |
| 구동기 `KV2/vb_chain.py` | `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322` |
| 재계산기 `KV2/vb_recalc.py` | `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b` |
| 고르기 `AD32/vb_select.py` | `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc` |
| 도움 함수 `AD32/vb_lib32.py` | `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f` |
| 닫힌 잎 목록 `AD32/vb_closed_leaves.json` | `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426` |
| 세션 도우미 `KV2/poll_vb2.sh`(판정 도구 아님) | `81b4348b01f6502a11bd011beda41682f2f465b5b134a26c9ac4bb3ff4ef1397` |
| 세션 도우미 `KV2/mk_vb2_tables.py`(판정 도구 아님) | `c59cef11b9273191a5c60fbad85b7fb69f7685440e2ab14667bfc3a4c41f0e70` |
| 표 도구 출력 `KV2/report/tables.md` | `f68e92850f3182591fd82ec6aca0bb37c0be1362d53ffa7d10a012f2f2ab3788` |
| 표 도구 출력 `KV2/report/tables_summary.json` | `c8b7c83651968983f28720ae37f297ca4aae8cd049162c668b329ab5feb83bda` |
| `VBR/check_v0.json` | `d8bc2130d8ebb4fdd7b3e33cf35545b99a95c1025ce46fcde496fe146c1dbad6` |
| `VBR/zi/zi.json` | `8d1ae5a157e8a708f1195c4e4d2a8a278f3ea962eafab66787b3a85f805112b5` |
| `VBR/zi/z1_off/zi_judge.json` | `619eadf19a61d9b08e615fed21baa92e0dad51350b5eb348d9391fd252767441` |
| `VBR/zi/z1_b1/zi_judge.json` | `67094284f76844f336a86c479a22968d7afc846bd060f9b873e6dad7859cea32` |
| `VBR/zi/z2_b1/zi_judge.json` | `6ef4ac5d821bc5935a06cfe5c1dfbe11cbfc9b57663809f79734b818074bde75` |
| `VBR/judge/vb_i1.json` | `47de078e9c1a6333ca8aa1828b8706dbb2fb33305303a318c1944954fc031815` |
| `VBR/judge/vb_reportonly.json` | `9ab57fcfcf0611c815b28e3aa7ae83e467508d979291b2f7578c402b86487bcf` |
| `VBR/judge/vb_i.json` | `18eb483b006e62aa7becc20d3d402e6bf6a5cd09c0674605dfccce0694093b96` |
| `VBR/judge/vb_m.json` | `459369834f7c9df5ffb18812494664e5896341596d14315faf13ba39d355dcf4` |
| `VBR/recalc/recalc.json` | `bee4d4622b79bc824425fb7566fb258d156cf890a98e76ef31c2348154866d77` |
| `VBR/stages/V0.json` | `1ccd7fb14391ed4c2e1741b65c5efae2d66836ed03a9c684244694311d4c5740` |
| `VBR/stages/V1.json` | `f717fe26733da996bd886f07faef4c2d1fcd607c4d8a2e21af491c003455c463` |
| `VBR/stages/V2.json` | `091e01b5a415b2c56a49dee057c673f71d550e05c57b78dbc1b945c10164c8f2` |
| `VBR/stages/V3.json` | `45acdb2f52aa201fa1e3f2d31ef95bff830cf0199166abb66a4173d66368e015` |
| `VBR/stages/V4.json` | `fe1f7753e9159383599be09e32b443e2b06a411d694a76c0b97ae43389b01399` |
| `VBR/stages/V5.json` | `76cc5993bba65081660a678b379700d0881cf23fb1e379b75b10e348d4933cc2` |
| `VBR/stages/V6.json` | `c8bd717357b27e212eb80ab4331495917453e93794fe4814c0a3500d6c233a8a` |
| `VBR/stages/V7.json` | `67beab1ac68dff9da0a993b69e7fa980009112351696862d653c1fb517d4b636` |
| `VBR/stages/V8.json` | `8226e71c8e95cadedf4a95018ea8b99ec5174fa61a47cc7e6577f3eb39629c74` |
| `VBR/stages/V9.json` | `bc14df47fe45b7be94526250c00110e851550399dbaf7e5fd540d339d9799f56` |
| `VBR/stages/V10.json` | `3ec43f2d9377399fef83d4aeb15fda2481914ef5a5b795124de438a23ded7dec` |
| 스냅숏 `OK2/snap/s43_vb2_v0.json` | `8cc4da7261ad968e3c074d4f475f6cb9cbd5f1b34b2e890ed691d0ab3eaf5752` |
| 스냅숏 `OK2/snap/s44_vb2_zi.json` | `24d977a5cff1866cd3f9c1baed7d526eb9f82fa3056fb72bf4dce13e0a9383d1` |
| 스냅숏 `OK2/snap/s45_vb2_off.json` | `59a2c2f23fd611e1b5216d06da11ca3d47cc7854ec533d2ec2358dd9c89695aa` |
| 스냅숏 `OK2/snap/s46_vb2_end.json` | `583592df84638b5bb31127c6244e67c4523b486ea86e7e55330fd0340b72bef3` |
| 빌드 기록 `TK/vb2_e27ceac8.build.json` | `e2c4ee176a249cbd53e993ec0d680962a75dbb4dd4d75dca00e8ee1fad10fb00` |
| SAF-B1 `VBR/arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json` | `65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28` |
| STOP 판 r1 보관 사본 `KV/K92_VB_REPORT_stop_r1.md` | `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00` |
| STOP 판 r1 보관 사본 `KB/VB_REPORT_stop_r1.md` | `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00` |
| STOP 판 r1 보관 사본 `OK2/vb/K92_VB_REPORT.md` | `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00` |

- 이 보고서 자신의 sha256은 LOG의 보고서 항목에 적습니다(정본·사본 둘 같은 바이트).

## 10. VerifyVB 3 변경 기록 (r2 → r3, 2026-10-23)

- r2 바이트는 `KV/K92_VB_REPORT_r2.md` = `KB/VB_REPORT_r2.md` = `OK2/vb2/K92_VB_REPORT_r2.md`(`79e7cb03…`)로 남겼습니다. 정본을 고친 뒤 사본 둘(`KB/VB_REPORT.md`, `OK2/vb2/K92_VB_REPORT.md`)에 다시 복사했습니다. 근거와 숫자는 `KV/VERIFY_VB.md`.
- 판정(VB-I1–I7, ZI, 결과 넷)과 VB-M 숫자는 하나도 바뀌지 않았습니다 [실행: 다시 낸 값 3,105칸 다름 0, 표 줄 243개 같음].

| # | 자리 | r2 | r3 | 까닭 |
|---|---|---|---|---|
| 1 | 제목·머리 | r2 완료 판 | r3 완료 판, VerifyVB 3 요약 한 줄, r2 보관 자리 | 판 바뀜 |
| 2 | 머리 "쓴 자리" | VBR 9.7 GB, VBT 2.1 GB | 같은 숫자 + `du -h`(2의 거듭제곱) 표시라는 말과 바이트(10,391,383,863 B·2,150,845,988 B) | 단위 표시만 |
| 3 | §0 5번, §3.5 끝 | `no_match` 두 결정: SC109 p2·p3·p4가 앞 결정과 같음, 까닭 정하지 않음 | + 녹색·오프셋 전체 같음, 예측 순서 없음, 고른 목적값 = 유지 목적값, 후보별 (m1) 어긋난 자리(미래 블록), 재실행에서 다시 나옴; 까닭은 여전히 정하지 않음 | 사실 더함([실행]), 추론은 [추론] 표시 |
| 4 | §3.7 | B1 6.53 h | B1 6.52 h | 41결정 합 6.518 h(r2는 반올림 값의 합) |
| 5 | §3.7 | 어림 9.5–10 h "안쪽" | 어림보다 "조금 짧음"(9.35 h) | 말이 숫자와 어긋남 |
