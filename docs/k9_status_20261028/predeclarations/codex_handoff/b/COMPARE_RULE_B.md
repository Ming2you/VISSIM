# COMPARE_RULE_B — B 폐루프(codex 판 v3c3 이식 탐침, v3c3-s31·s41·s43) 비교 규칙 (2026-10-26 KST, 첫 B 발사 전 고정)

- 이 규칙과 §7 의 도구는 **첫 B 런을 띄우기 전에** sha256 을 `SP/codex_handoff/LOG.md` 에 적어 고정합니다. B 데이터를 본 뒤에는 고치지 않습니다. 쓰인 대로 할 수 없는 일이 생기면 고치지 않고 멈추고 보고합니다(그 칸은 "못 냄").
- 판정 낱말은 쓰지 않습니다. Ω 는 늘 ④ 와 Ω 밖과 같은 표에 둡니다. 시드 수는 표마다 적습니다(계획 3: v3c3-s31·s41·s43, 모두 우리 fit 시드이며 codex 계수에는 표본 밖).
- 표시: [실행] 명령으로 확인 · [읽음] 파일을 읽어 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.
- 근거(읽은 판): PRE_B `SP/codex_handoff/b0/PRE_B.md`(sha256 `3149cfe5…`) §3·§4, 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(`d248605e…`) D-K9-84 Q2·D-K9-87·D-K9-89, HANDOFF_RESULTS r2 H10–H14·B-7·B-8, VERIFY_A1_B0 `6075c1df…` §0-4·§2·§7-1(codex 꼴 = 시각축 사다리꼴), OMEGA701_V3C3 §0(두 꼴 정의), COMPARE_RULE_R4 `349bd69d…` §2(첫 관측 차분). SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CW = `SP/codex_handoff/work`.

## 0. 줄임말 (처음 한 번)

- B = codex 판(a49981ff)을 우리 v3c3 망으로 옮긴 폐루프 런. NC3 = 같은 시드 v3c3 무제어 런. V-A = 우리 묶음 B1 폐루프 런.
- Ω635 = 우리 목적 영역 635링크(`D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json` 의 inside, 읽기만). Ω701 = codex 목적 영역 701링크(`D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json`, sha256 `efdfaeb1…`, inside).
- ④a = 망 전체 링크 체류(veh·h). ④b = 미삽입 대기(차가 입력에서 망에 못 들어가 기다린 시간, veh·h). ④ = ④a + ④b. Ω 밖 (a) = ④ − Ω, (b) = ④a − Ω.
- ① = FW_E 본선 7링크 {74, 10699, 2, 10613, 119, 10702, 24}. ② = 동측 국소 19링크 = ① ∪ {10484, 10490, 10639, 10681, 10481, 10483, 10643, 10682, 129, 31, 68, 70}.
- FZP = VISSIM 차량 궤적 파일(5 s 프레임, x.1 s 시각). LDP = 신호 상태 초별 기록. d(X) = 짝 차.
- 칸 이름(slot): 고친 도구는 원래 런 이름 칸을 그대로 두고 경로만 B 로 바꿨습니다(§7). 그래서 출력 안의 "j1"·"joint"·"a1" 칸이 B 입니다. 이 규칙의 표에서는 모두 "B" 로 옮겨 적습니다.

## 1. 런과 짝

| 런 (시드 s ∈ {31, 41, 43}) | 폴더 / 파일 |
|---|---|
| B | `D:/VISSIM_runs/20261026_codex_b_v3c3/s<s>/sdmpc` (이름 `sdmpc31_sdmpc9000_s<s>`): FZP `vissim_eval/sdmpc31_sdmpc9000_s<s>_001.fzp`, 망 `network/sdmpc31_sdmpc9000_s<s>.inpx`, 오류 `network/sdmpc31_sdmpc9000_s<s>_001.err`, 명령 `action_sdmpc31_sdmpc9000_s<s>.csv`, 런 로그 `runlog_sdmpc31_sdmpc9000_s<s>.txt`, 결정 `decisions_sdmpc31_sdmpc9000_s<s>/`, LDP `vissim_eval/sdmpc31_sdmpc9000_s<s>_<SC>_001.ldp`, native `native_network_performance.json`(있으면) |
| NC3 | `D:/VISSIM_runs/20261001_v3c3/s<s>_v3c3nc/run/vissim_eval/baseline_s<s>_v3c3nc_001.fzp` (망 `…/prepared/network/baseline_s<s>_v3c3nc.inpx`, 오류 `…/run/baseline_s<s>_v3c3nc_001.err`) |
| V-A | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s<s>/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s<s>_001.fzp` |

- 주 짝 = **B − NC3**(같은 시드). 보조 짝 = **B − V-A**(같은 시드). 시드끼리 평균 내지 않습니다. 다중 비교 보정은 하지 않습니다(3시드). 칸은 늘 시드별로 적습니다.
- 쓸 수 있는 B 런 = 런 로그에 `STAGE=SIM_DONE` 과 `SIM_SEC=9000` 이 있는 런. 아니면 그 시드의 짝 칸은 모두 "못 냄(런 미완: 까닭)". 일부 구간만 잘라 내는 분석은 하지 않습니다.
- 짝 성립 점검(PRE_B §2-5): 같은 시드 B 와 NC3 의 FZP 접두(시각 ≤ 895.1 s 의 데이터 행) 가 같은지. 주 값 = `vhr_scan_b.py` 출력의 `lf_sha_le_895_1` 같음 여부, 상세 = `a1_fzp_firstdiff_b_s<s>.py` 의 짝 (a1, joint) = (B, NC3) 의 접두 같음·처음 다른 프레임. 다르면 그 시드의 모든 짝 칸에 "†접두 다름" 을 붙이고 따로 보고합니다(런은 버리지 않음). B − V-A 접두는 참고로만 적습니다: V-A v3c3-s31·s41 FZP 에는 러너의 0.10 s 행이 있어 첫 다른 프레임이 0.1 s 로 나올 수 있습니다 [실행: V-A s31 FZP 첫 데이터 행 `0.10;…`, NC3 s31·codex 러너 A1 FZP 는 5.10 s 부터].

## 2. 적분 두 꼴 (④a·Ω·①·②·링크 66·도시도로 모두 같은 두 꼴)

FZP 프레임마다 링크별 차 수 n_l(t) 를 셉니다. 링크 체류(veh·h) = 시간축 적분 / 3600.

1. **우리 꼴 [0, 9000] s** (stage-1·V-A 보고 꼴): 첫 프레임 t = 5.1 s 부터 9,000 s 이하 마지막 프레임(8,995.1 s)까지, 이웃 프레임 사이 사다리꼴 Σ (n_i + n_{i+1})/2 · (t_{i+1} − t_i). 러너의 0.10 s 프레임은 건너뜁니다. 양 끝은 늘리지 않습니다(실제 적분 구간 [5.1, 8,995.1] s). 도구 이름 `ours_9000`.
2. **codex 꼴 [0, 8100] s = 시각축 사다리꼴(TR)**: t = 0 에 빈 망(n = 0)에서 시작해 첫 프레임까지 선형, 8,100 s 이하의 모든 프레임(0.10 s 프레임이 있으면 그것도)을 실제 시각으로 이어 사다리꼴, 8,100 s 를 넘는 행은 버리고, 8,100 s 이하 마지막 프레임(8,095.1 s)의 재고를 8,100 s 까지 그대로 둡니다(4.9 s). 도구 이름 `codex_8100`. 이 꼴은 codex `handoff/check_fzp.py integrate()` 와 codex `area_metrics.json /ttt_integration_rule`("trapezoid in actual timestamp space")와 같고, VERIFY_A1_B0 §0-4 에서 codex 자체 수치(nc·joint 의 Ω701·④a·①·②)와 1e-3 안, A1 표 76칸이 보고와 0.06 veh·h 안으로 맞음이 확인된 꼴입니다 [읽음 VERIFY_A1_B0:14, :22-23, :71].
3. ④b(첫 관측 차분)의 창 끝 W: 우리 꼴 W = 9,000 s, codex 꼴 W = 8,100 s(`vhr_v3c3_all.py` 의 식 그대로).
4. 도구가 함께 내는 `ours_8100`·`codex_9000` 은 주 표에 넣지 않습니다(참고 파일로만 남음).

## 3. 지표 정의와 출처 (주 표 T1: B − NC3, 보조 표 T2: B − V-A, 각 꼴마다 한 표)

출처 줄임: V = `CW/vhr_b/v3c3_all.json` 의 `cells`(form, pair, seed, metric, `mine`), O = `CW/omega_b/omega701_v3c3.json` 의 `pairs`(`<짝>|s<s>|<꼴>|<합집합>`), P = `CW/omega_b/omega701_per_link.csv`, M = `CW/rawcheck_b/s<s>/metrics_out.json`.
V 의 짝 이름: B − NC3 = `pair = "j1-nc3"`, B − V-A = **−1 ×** `pair = "va-j1"`(V-A − B 의 부호를 뒤집음). O 의 짝 이름: B − NC3 = `J1-NC3`, B − V-A = **−1 ×** `VA-J1`.

| 줄 | 정의 | 출처 (꼴 F ∈ {ours_9000, codex_8100}) |
|---|---|---|
| Ω635 | Ω635 링크 체류 합 | V `metric O635` |
| Ω701 | Ω701 링크 체류 합 | V `O701` |
| Ω701 − Ω635 | 더한 66링크 몫 | [계산] 위 두 줄의 차 |
| ④a | 모든 링크 체류 합 | V `A4a` |
| ④b (주 값, 첫 관측 차분) | d④b(a − b) = S_b − S_a, S_r(W) = Σ_{첫 관측 ≤ W} (W − t_첫)/3600 (같은 망·시드 짝은 도착열이 같다고 봄) | V `U` |
| ④ | d④a + d④b | V `A4` |
| Ω 밖 (a) Ω701 | d④ − dΩ701 | V `outa701` |
| Ω 밖 (b) Ω701 | d④a − dΩ701 | V `outb701` |
| Ω 밖 (a) Ω635 | d④ − dΩ635 | V `outa635` |
| Ω 밖 (b) Ω635 | d④a − dΩ635 | [계산] V `A4a` − V `O635` |
| ① | FW_E 7링크 | V `FWE7` |
| ② | 국소 19링크 | O `local19` (합집합 칸은 링크 지표에 영향 없음; `U6J1` 칸을 읽음) |
| ④b 중 입력 1098 (FW_E 입구) | 첫 관측 링크 74 인 차 | V `u1098` |
| ④b 중 입력 1099 (FW_W 입구) | 첫 관측 링크 26 인 차 | V `u1099` |
| ④b 중 도시 입력 | 그 밖 첫 관측 링크 | V `ucity` |
| ④b 참고 열 (stage-1 재구성, NC3 앵커) | 입력별 도착 일정 재구성 | O `M4b`(B − NC3 은 합집합 `U6J1` = B·NC3 의 대기 입력, B − V-A 는 `U9` = V-A·B·NC3), 입력별 O `unins_1098`·`unins_1099`·`unins_urban` |
| ④b 수준값 (B, 있으면) | codex 러너가 남긴 native `DelayLatent` / 3600 (to_sec 함께) | [읽음] B `native_network_performance.json` `/native/DelayLatent`, `/to_sec`. NC3·V-A 에는 이 파일이 없어 짝 차는 내지 않음 |

- 주 표의 ④·Ω 밖 (a) 는 첫 관측 차분 ④b 로 냅니다. stage-1 재구성은 참고 열로만 둡니다(D-K9-87, H14).
- 같은 표에 Ω635·Ω701·④a·④b·④·Ω 밖 (a)(b)(두 기준)·①·②·입력별 ④b 를 모두 둡니다. 어느 한 줄만 따로 떼어 적지 않습니다.
- 수준값 표 T0(참고): B·NC3·V-A 의 링크 지표 수준값(꼴 둘) = O 의 `table`(`<런>|<꼴>|U6J1`; B = `j1_s<s>`), ④b 수준값은 위 native 줄과 재구성(참고)만.

## 4. 따로 적는 줄

1. **링크 66**(SC1004 남측, H11): d = P 에서 `link = 66` 의 (B − NC3), (B − V-A) 값, 꼴 둘. 우리 꼴은 원래 `CW/omega/top66.py`(고치지 않음, 작업 폴더 = `CW/omega_b`)의 `J1-NC3` 열과 같아야 합니다(점검 X4).
2. **도시도로 두 규칙**(H12): codex 꼴 [0, 8100] 만. codex 규칙 = M `codex_rule.joint.urban_roads − codex_rule.nc.urban_roads`, 우리 규칙(미터 상류 링크 70·68·129·31 / 124·32·121·69 를 진입 쪽으로 셈) = M `alt_rule` 의 같은 차. 진입 E·W 도 같은 두 규칙으로 함께 적음(`onramps_E`, `onramps_W`). 우리 꼴 [0, 9000] 의 codex 규칙 도시도로는 O `urban_roads` 로 적음.
3. **LDP 신호 실행 대조(B-8, `ldp_cmp.py` 꼴)**: 이 꼴은 "팔 LDP 대 NC LDP" 의 초별 상태 비교입니다. NC3(그리고 V-A) 폴더에는 LDP 가 없습니다 [실행 ls: NC3 s31·s41·s43 `vissim_eval` = FZP 하나, V-A = fzp·lsa·mer]. 그래서 **이 줄은 쓰인 대로는 못 냅니다 → "못 냄(NC3 에 LDP 없음)" 으로 적고 대체 계산은 하지 않습니다**. 신호 실행의 다른 근거는 런 로그·readback(`signal_readback.csv`)이지만 이 규칙의 도구 목록에 없어 표에 넣지 않습니다.
4. **미터 실행 대조(`rm_exec.py` 꼴)**: `rm_exec_b_s<s>.py` → 미터 SC 마다 150 s 구간(900 ≤ t0 < 8,100) 수, 명령 녹색(green_sec)과 LDP 녹색 초/15 의 차가 0.5 s 를 넘는 구간 수와 예 5개. 창은 도구 그대로(8,100 s 까지).
5. **미터 녹색·rate 분포(B-7)**: `dec_extract_b.py s<s>` → `dec_s<s>.json` 의 결정별 `rm_green`(진단 `rw_meter_green_*`)과 `rm_out`(`ramp_metering` rate). 미터마다 값별 결정 수, T ∈ [900, 8,850] [계산: 단순 셈].
6. **결정 벽시계 분포**: `walltimes_b_s<s>.py` → `walltimes_out.json` 의 `joint`(= B): T ≥ 900 결정 수, 평균·중앙·최대·최소, > 1,800 s 수, > 360 s 수, budget wall 평균·최대, 결정별 (T, wall, 결과). [계산] 같은 결정별 목록에서 > 1,500 s 수와 > 2,400 s(StallSec) 수.
7. **유지(hold) 수·T·예외 종류(H9)**: `walltimes_out.json` 의 `held`(`DECISION_HELD_PREVIOUS` 줄의 T) + [읽음] 런 로그의 `DECISION_HOLD_ATTEMPT sim_sec=<T> cause=<…>` 줄(예외 종류 = cause 의 첫 `:` 앞 이름과 메시지 앞 120자), 요약 줄 `DECISIONS_OK=`·`DECISIONS_FAILED=`·`DECISIONS_HELD_PREVIOUS=`·`DECISIONS_HELD_ON_EXCEPTION=`, 결정 폴더의 `action_<T>.error.txt` 마지막 줄. 유지 아닌 실패(런 멈춤)는 따로 적음.
8. **램프 도착 예측(H8)**: `ramp_fc_b_s<s>.py` → `ramp_fc_out.json` 의 결정별 `logged`(= 명령 JSON 메타데이터 `forecast_ramp_arrival_total_vph`). RM_C 별 값은 B 명령 JSON 메타데이터에 `RM_C` 이름이 붙은 도착 칸이 있으면 그 값, 없으면 "출력에 없음"(codex 메타데이터는 합과 옛 그룹키 4칸만 적음, ADP:13211-13217 [읽음 B0.md §4-4]). 이 도구가 함께 내는 두 재계산 열(120 s·900 폴백, 옛 그룹표)은 B 의 RM_C 식이 아니어서 쓰지 않습니다.
9. **VSL 명령**: `dec_s<s>.json` 의 `vsl_out` 집합(B 설정은 고정 110). 110 밖 값이 있으면 T 와 값을 적음.
10. **단서(D-K9-89 ②)**: 모든 B 표 머리에 "64cf-s29 로 맞춘 D 부류 계수와 64cf 유도 codex 계약 11개를 v3c3 에 그대로 얹은 런(계수 불일치와 기구 효과 없음을 가를 수 없음, PRE_B §7)" 을 적습니다.

## 5. 점검 (데이터 전 고정)

- X1 [보고]: 같은 꼴에서 V 의 dΩ701·dΩ635·d①·d④a 와 O 의 같은 짝 값(`Omega701`·`Omega635`·`FW_E7`·`M4a`) 차 ≤ 0.05 veh·h. 넘으면 두 값을 다 적고 "‡두 스캐너 차" 를 붙입니다(주 값은 V).
- X2 [보고]: codex 꼴 도시도로 codex 규칙 M 값과 O `urban_roads`(codex_8100) 짝 차의 차 ≤ 0.05. 넘으면 두 값을 다 적음(M 은 64cf geometry 의 사슬·램프 분할을 씀).
- X3 [STOP]: 고친 도구가 원본과 같게 도는지. V 의 `pair = "va-nc3"` 칸 전부 = 원본 `CW/vhr/v3c3_all.json`(`bf26275e…`)의 같은 칸(`mine` 같음), O 의 `VA-NC3|*|*|U6VA` 의 모든 지표 = 원본 `CW/omega/omega701_v3c3.json`(`fa6d24cf…`)의 같은 칸(|차| ≤ 1e-6). 하나라도 다르면 B 숫자를 내지 않고 멈춤.
- X4 [보고]: 링크 66 우리 꼴 짝 차가 P 와 `top66.json` 에서 같음(≤ 1e-6).
- X5 [보고]: 시드마다 첫 관측 차 수(`vhr_v3c3_all_b` 의 `arrival_totals_9000`) B 대 NC3, 그리고 입력 1099 도착 수(첫 관측 링크 26 수 + `.err` 남은 수, 가능하면). 차이가 크면 "도착열 같다" 가정에 단서.
- X6 [STOP]: 도구가 B 데이터에서 쓰인 대로 돌지 못하면(예외·파일 꼴 다름) 그 도구를 고치지 않고, 그 칸을 "못 냄" 으로 두고 멈추고 보고합니다.

## 6. 서식·반올림·결측

- veh·h 는 소수 첫째 자리(부호 표시, 음수는 `−`). 벽시계 초는 소수 첫째. rate·green 은 CSV 글자 그대로. 개수는 정수. 비율(%)은 이 규칙의 표에 넣지 않습니다.
- 반올림은 마지막에 한 번(합·차는 반올림 전 값으로 계산; V 의 `mine` 은 도구가 0.001 로 반올림한 값이라 그대로 씀).
- 결측: 파일이 없거나 런이 미완이면 "못 냄(까닭)", 출력에 그 칸이 원래 없으면 "없음". 0 으로 채우지 않습니다.
- 표 머리: 꼴(우리 [0, 9000] / codex [0, 8100]), 짝, 시드 수(예 "시드 3: v3c3-s31·s41·s43"; 미완 런이 있으면 실제 수), 단서(§4-10).
- 칸 이름: "B − NC3 v3c3-s31" 처럼 짝과 시드를 같이 씀. "j1"·"joint"·"a1" 같은 도구 칸 이름은 표에 쓰지 않습니다.

## 7. 도구 (고정; B 데이터 전)

### 7.1 PRE_B §4 목록 다시 확인 [실행 sha256, 2026-10-26 11:18 KST]

PRE_B §4 의 14개 sha 가 모두 그대로입니다: vhr_firstseen `42e17585…`, vhr_unins `fc233013…`, vhr_v3c3_all `b4237251…`, omega701_recount `5b7826f6…`, build_tables `134d580b…`, top66 `1424b5ad…`, metrics `b524b51b…`, scan_fzp `c8a6e5c4…`, ldp_cmp `2bb7d6c2…`, rm_exec `27f64022…`, SHA256SUMS_RAWCHECK `3e3b5307…`, va_analysis_pins `39a97e7f…`, R4_PINS `1ca353a9…`, COMPARE_RULE_R4 `349bd69d…`. 목록 파일 셋(`SHA256SUMS_RAWCHECK.txt`·`va_analysis_pins.sha256`·`R4_PINS.sha256`)을 `sha256sum -c` 로 돌려 OK 아닌 줄 0 입니다.

### 7.2 경로 상수만 바꾼 사본 (생성기 `CW/gate1/mkcopy.py` `8ec4f60c…`, 명세 `CW/gate1/spec_b_copies.json` `f857d830…`(만든 도구 `CW/gate1/make_spec_b.py` `c8674322…`), 바뀐 줄 기록 `CW/gate1/copies_b_record.json` `51936d43…`)

바꾼 것은 파일·폴더 경로 글과 "런 칸 → 경로" 대응뿐입니다. 식·창·격자·분할 규칙 줄은 바꾸지 않았습니다. 바뀐 줄은 기록 파일에 원본 줄 번호와 옛 글·새 글로 모두 있습니다.

| 사본 (CW 아래) | 원본 (sha 앞 8) | 바꾼 것 | 사본 sha256 |
|---|---|---|---|
| `omega_b/omega701_recount_b.py` | `omega/omega701_recount.py` (5b7826f6) | 칸 j1 → B 의 FZP·망·오류·런 폴더(B_RUNS 상수), J1 stage-1 스캔 대조 줄 지움, docstring 머리 표시. 출력은 `omega_b/` | `3d5160da36f984b554444c06e513500590551682b706a234cc67f9fc0221f150` |
| `vhr_b/vhr_scan_b.py` | `vhr/vhr_scan.py` (a19942b8; PRE_B §4 의 vhr_v3c3_all 입력을 만드는 도구, VERIFY_HANDOFF_RESULTS 에서 고정) | 출력 폴더 `vhr_b/scan_out`, 칸 j1 → B FZP | `0c445bc4bf05f45f7638be8227f0f29c2b036c0f276083958ff6bac87a85466e` |
| `vhr_b/vhr_firstseen_b.py` | `vhr/vhr_firstseen.py` (42e17585) | 같음 | `d5c3c126490e4d1260063b51a9b97b4948b7c1ac35846c32761423c90088471b` |
| `vhr_b/vhr_v3c3_all_b.py` | `vhr/vhr_v3c3_all.py` (b4237251) | 읽는 폴더 `vhr_b/scan_out` | `d91ded54904eb43a78a49f0d2a1382396258a0cf0621fbf6e7ba2410fb7283ed` |
| `rawcheck_b/s31/scan_fzp_b_s31.py` · s41 · s43 | `rawcheck/scan_fzp.py` (c8a6e5c4) | 출력 `rawcheck_b/s<s>/scan`, 칸 nc → NC3 s, joint → B s | `943e06db…` · `19e33689…` · `906b8ae3…` |
| `rawcheck_b/s<s>/metrics_b_s<s>.py` | `rawcheck/metrics.py` (b524b51b) | 읽는 폴더 `rawcheck_b/s<s>/scan` | `84d15045…` · `f93e6537…` · `b27ab3b3…` |
| `rawcheck_b/s<s>/rm_exec_b_s<s>.py` | `rawcheck/rm_exec.py` (27f64022) | 결과 뿌리, 팔 폴더 `s<s>`, 파일 이름 `sdmpc9000_s<s>` | `0c26104b…` · `1fbac884…` · `af2c9eb8…` |
| `rawcheck_b/s<s>/walltimes_b_s<s>.py` | `rawcheck/walltimes.py` (13734307; SHA256SUMS_RAWCHECK 안) | 칸 joint → B 런 폴더(팔 하나) | `6974d2b4…` · `a16776b5…` · `c5916bd7…` |
| `rawcheck_b/s<s>/ramp_fc_b_s<s>.py` | `rawcheck/ramp_fc.py` (cee99f5b; SHA256SUMS_RAWCHECK 안) | B 결정 폴더 | `22275050…` · `9732ffc9…` · `9134790c…` |
| `rawcheck_b/s<s>/a1_fzp_firstdiff_b_s<s>.py` | `a1/full/a1_fzp_firstdiff.py` (00924703; A1 고정 도구, PRE_B §2-5 의 접두 점검 도구로 더함) | 칸 a1 → B, joint → NC3, lnc → V-A | `8e476eba…` · `e4df20af…` · `c20db189…` |
| `rawcheck_b/dec_extract_b.py` | `rawcheck/dec_extract.py` (672c7bed; SHA256SUMS_RAWCHECK 안) | 결정 폴더 뿌리 = B 결과 뿌리, 인자 = s31/s41/s43 | `2d128f759685f1ff7151aeb09659ca1fcfe847abd6aebf220a1e2a5a8b3a9e97` |

- 전체 sha256 은 LOG 의 이 규칙 고정 항목에 64자로 적습니다.
- `rawcheck_b/s<s>/scan/` 에는 metrics 가 요구하는 codex 스캔 다섯(window·off·freeway_only·urban_only·lnc)을 원본 `rawcheck/scan/` 에서 바이트 그대로 복사해 두었습니다(sha 가 SHA256SUMS_RAWCHECK 와 같음 [실행]). 그 다섯 칸의 출력 줄은 B 와 무관하며 표에 쓰지 않습니다.

### 7.3 고치지 않고 쓰는 것

- `CW/omega/top66.py`(`1424b5ad…`): 작업 폴더 `CW/omega_b` 에서 실행(같은 폴더의 `omega701_per_link.csv` 를 읽음). 출력 `J1-NC3` 열 = B − NC3(우리 꼴).
- stage-1 도구(`D:/VISSIM-merge/tools/stage1`, omega701_recount 가 sha 확인 뒤 import).

### 7.4 목록에 있지만 B 에 쓰지 않는 것 (까닭)

- `vhr_unins.py`: 짝 목록이 s31 의 codex 검증용이라 B 3시드 짝을 낼 수 없음. 같은 식(dU = S_b − S_a)을 `vhr_v3c3_all.py` 가 시드·꼴별로 계산하므로 그것을 씀.
- `build_tables.py`: 검증 블록이 V-A·J1 보고값과 대조하므로 칸 j1 에 B 가 들어가면 뜻이 없음. 표는 §3 의 출처에서 바로 옮김.
- `ldp_cmp.py`: §4-3(NC3 에 LDP 없음).
- r4 도구(`R4_PINS`), `COMPARE_RULE_R4`: 입력별 귀속을 stage-1 `scan.json` 에서 하는데 B 에는 stage-1 스캔이 없음. 첫 관측 차분의 정의(§2·§4)는 R4 규칙 §2-4 와 같고, 입력별 몫은 첫 관측 링크(74·26·그 밖)로 나눔(VERIFY_A1_B0 에서 r4 와 193/199 칸 같음, 다른 6칸은 입력 1091·1092 몫).
- `dec_summary.py`: 출력이 print 뿐이라 §4-5 는 `dec_s<s>.json` 을 직접 셈.
- `va_analysis_pins` 의 V-A 도구: B 짝에는 쓰지 않음(참고 목록).

### 7.5 실행 차례·환경 (B 런 뒤; 다른 B 런이 돌면 BELOW_NORMAL, 무거운 일 한 번에 하나)

1. `vhr_b/vhr_scan_b.py va_s31 nc3_s31 j1_s31 va_s41 nc3_s41 j1_s41 va_s43 nc3_s43 j1_s43` → 2. `vhr_b/vhr_firstseen_b.py`(같은 9칸) → 3. `vhr_b/vhr_v3c3_all_b.py`.
4. `omega_b/omega701_recount_b.py scan` → `omega_b/omega701_recount_b.py metrics` → 5. `omega/top66.py`(작업 폴더 `omega_b`).
6. 시드마다 `rawcheck_b/s<s>/scan_fzp_b_s<s>.py nc`, `… joint` → `metrics_b_s<s>.py` → `a1_fzp_firstdiff_b_s<s>.py <out.json>`.
7. 시드마다 작업 폴더 `rawcheck_b/s<s>` 에서 `rm_exec_b_s<s>.py`, `walltimes_b_s<s>.py`, `ramp_fc_b_s<s>.py`. 8. 작업 폴더 `rawcheck_b` 에서 `dec_extract_b.py s31` · `s41` · `s43`.
- 환경: `python -B`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, OMP·OPENBLAS·MKL 스레드 1. 런 폴더·NC3·V-A·인계 사본·GWT8 은 읽기만.
- B 런이 덜 끝난 동안 NC3·V-A 칸만 미리 스캔해도 됩니다(데이터가 B 가 아니므로). 그 출력은 X3 로 원본과 같아야 합니다.

## 8. 이 규칙이 알려 주지 않는 것 [추론]

- PRE_B §7 그대로: 64cf-s29 로 맞춘 D 부류 계수가 v3c3 에 맞는가, 기구별 몫, codex 64cf 숫자의 재현. 작거나 반대 방향의 결과도 "계수 불일치" 와 "기구 효과 없음" 을 가르지 못합니다.
- 첫 관측 차분은 "같은 망·같은 시드면 도착열이 같다" 는 가정 위의 값입니다(X5 로 도착 수만 봄).
- B 는 codex 러너, NC3·V-A 는 우리 러너입니다. 접두 점검(§1)이 900 s 전 같음을 보지만 러너 차이 전체를 보지는 않습니다.
