# COMPARE_RULE_FO — FO 폐루프(codex SDMPC 고속도로만, v3c3-s31·s41·s43) 비교 규칙 (2026-10-27 KST, FO 데이터 전 고정)

- 이 규칙은 **FO 데이터가 생기기 전에** sha256 을 `SP/codex_handoff/fo/LOG.md` 와 `PRE_FO.md` 에 적어 고정합니다. FO 데이터를 본 뒤에는 고치지 않습니다. 쓰인 대로 할 수 없으면 고치지 않고 그 칸을 "못 냄(까닭)" 으로 두고 멈추고 보고합니다.
- 꼴은 `b/COMPARE_RULE_B.md`(sha256 `f902f7f0…`)를 그대로 따릅니다. 바뀐 것은 짝 셋(FO − NC3, B − FO, FO − V-A)과 FW_E 분해 칸(RF1–RF11, DA1–DA4), 미터·도시 신호 실행 대조를 readback 으로 하는 것뿐입니다.
- 판정 낱말은 쓰지 않습니다. Ω701 은 늘 ④ 와 Ω 밖 (a)(b) 와 같은 표에 둡니다. 시드는 망 이름을 붙여 v3c3-s31·s41·s43 으로 적고 평균 내지 않습니다.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CW = `SP/codex_handoff/work`, FW = `SP/codex_handoff/fo/work`, FD = `SP/fwe_decomp`.

## 0. 줄임말 (처음 한 번)

- **FO** = codex SDMPC 가 램프 미터만 움직이고 도시 신호 17곳은 baseline(= v3c3 무제어 명령 값) 계획을 다시 쓰기만 하는 v3c3 폐루프 런(사용자 결정 D-K9-113, O2). VSL 은 B 와 같이 110 고정.
- **B** = codex 판을 v3c3 로 옮긴 폐루프(도시 신호 + 미터, VSL 110 고정). **NC3** = v3c3 무제어. **V-A** = 우리 묶음 B1 폐루프.
- **Ω701 / Ω635** = codex / 우리 목적 영역. **④a** 망 전체 링크 체류, **④b** 미삽입 대기(첫 관측 차분이 주 값), **④** = ④a + ④b, **Ω 밖 (a)** = ④ − Ω, **(b)** = ④a − Ω. **①** FW_E 본선 7링크, **②** 동측 국소 19링크.
- **도시도로** = codex 분할(`reporting_partition.json` `3142f69c…`, D-K9-104)만 씁니다.
- **FW_E** = 동측 고속도로(주 목표). **FW_W** = 서측 고속도로(감시만: ④b 1099, FW_W 본선, FW_W 미터).
- **RF1–RF11** = FW_E 기준 줄 칸(PRE_FWE §6.2, `c7cc0e6c…`). **DA1–DA4** = FWE_DECOMP r2 §3.4 의 보고 전용 칸(D-K9-110 이 C1 용으로 정한 정의를 그대로 씀).
- **readback** = 러너가 신호 그룹 상태를 쓴 뒤 다시 읽은 기록(결정 폴더 `signal_readback.csv`·`vsl_readback.csv`).

## 1. 런과 짝

| 런 (시드 s ∈ {31, 41, 43}) | 폴더 / 파일 |
|---|---|
| FO | `D:/VISSIM_runs/20261028_codex_fo_v3c3/s<s>/sdmpc` (이름 `sdmpc31_sdmpc9000_s<s>`): FZP `vissim_eval/sdmpc31_sdmpc9000_s<s>_001.fzp`, 망 `network/…`, 명령 `action_sdmpc31_sdmpc9000_s<s>.csv`, 런 로그 `runlog_…txt`, 결정 `decisions_sdmpc31_sdmpc9000_s<s>/`(readback 포함) |
| B | `D:/VISSIM_runs/20261026_codex_b_v3c3/s<s>/sdmpc` (기록; 분석 출력은 §3 의 고정 파일) |
| NC3 | `D:/VISSIM_runs/20261001_v3c3/s<s>_v3c3nc/run/vissim_eval/baseline_s<s>_v3c3nc_001.fzp` |
| V-A | `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s<s>/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s<s>_001.fzp` |

- 짝(같은 시드, 평균 없음, 다중 비교 보정 없음):
  1. **FO − NC3** (주): codex 고속도로 제어 몫. 도시 신호는 baseline 다시 쓰기이며, 그것이 NC3 의 native 프로그램과 GREEN 초가 같은지는 관문 G2·런 점검 V4 가 따로 확인합니다(같지 않으면 런 전에 멈춤).
  2. **B − FO**: codex 도시 제어 몫. 두 팔의 차이 = 설정 키 하나(`adapter.sdmpc_actuator_scope`) + 그 키 없이는 B 와 같게 도는 solo 코드(관문 R0 가 확인).
  3. **FO − V-A** (참고): 우리 폐루프와의 차. V-A 는 FW_E VSL 100 결정이 있어(9/10/14번) VSL 차가 섞입니다.
- **쓸 수 있는 FO 런** = 런 점검 V1(완주) 참. V1 거짓이면 그 시드의 칸은 모두 "못 냄(런 미완: 까닭)".
- 런 점검 V2–V5 중 하나라도 거짓이면 그 런은 선언한 FO 가 아닙니다 → 표를 내지 않고 멈추고 보고합니다(PRE_FO §9).
- **접두 표시 †**: 두 런의 FZP 접두(시각 ≤ 895.1 s 행)의 `lf_sha_le_895_1` 이 다르면 그 짝·시드 칸에 † 를 붙입니다(COMPARE_RULE_B §1 그대로). B 는 v3c3-s31·s41 에서 0.1 s 행 1개만 NC3 와 달랐습니다(B_RUNS §7). FO 도 같은 러너라 같은 꼴을 예상합니다 [추론].

## 2. 적분 두 꼴

COMPARE_RULE_B §2 그대로입니다: **우리 꼴 [0, 9000] s**(5.1–8,995.1 s 사다리꼴, 0.1 s 행 건너뜀) 과 **codex 꼴 [0, 8100] s**(시각축 사다리꼴, t=0 빈 망부터, 8,100 s 까지 마지막 재고 유지). ④b 첫 관측 차분의 창 끝 W 는 꼴마다 9,000 / 8,100 s.

## 3. 표 T1(우리 꼴)·T2(codex 꼴) — 줄과 출처

- 도구 `FW/ana/fo_tables.py`(B_RESULTS 표 도구 `b_results_tables.py` `065878dd…` 의 줄·반올림을 그대로 씀). 출력 `FW/ana/fo_tables_out.json`·`.md`.
- FO 출처: V = `CW/vhr_fo/v3c3_all.json`, O = `CW/omega_fo/omega701_v3c3.json`, P = `CW/omega_fo/omega701_per_link.csv`, M = `CW/rawcheck_fo/s<s>/metrics_out.json` (모두 §8 의 FO 사본 도구 출력).
- B 출처(고정): V `f982fbff…`, O `823f9dcc…`, P `c4f7a3a3…`, M s31 `74a06771…` · s41 `b9e41f92…` · s43 `9d3e4364…`, top66 `a4e47a48…`.
- 짝 값:
  - FO − NC3 = FO 출력의 `j1-nc3`(V), `J1-NC3|s|꼴|U6J1`(O), P 의 `j1_s − nc3_s`, M `codex_rule.joint − codex_rule.nc`.
  - FO − V-A = FO 출력의 −`va-j1`(V), −`VA-J1|s|꼴|U9`(O), P 의 `j1_s − va_s`.
  - B − FO = [계산] (B − NC3, B 고정 출력) − (FO − NC3). 모든 줄이 같은 NC3 기준의 선형 양이라 이 차가 곧 두 런의 차입니다(④b 첫 관측 차분도 S_FO − S_B 로 같음). P·M 은 B 와 FO 의 수준값을 바로 뺍니다.

| 줄 (veh·h) | 정의 | 출처 |
|---|---|---|
| **Ω701** | Ω701 링크 체류 합 | V `O701` |
| Ω635 | Ω635 링크 체류 합 | V `O635` |
| Ω701 − Ω635 | 더한 66링크 몫 | [계산] |
| ④a | 모든 링크 체류 | V `A4a` |
| **④b** (주 값, 첫 관측 차분) | d④b(a − b) = S_b − S_a | V `U` |
| **④** | d④a + d④b | V `A4` |
| **Ω 밖 (a) Ω701** | d④ − dΩ701 | V `outa701` |
| Ω 밖 (a) Ω635 | d④ − dΩ635 | V `outa635` |
| **Ω 밖 (b) Ω701** | d④a − dΩ701 | V `outb701` |
| Ω 밖 (b) Ω635 | d④a − dΩ635 | [계산] V `A4a` − V `O635` |
| ① FW_E 본선 7링크 | {74, 10699, 2, 10613, 119, 10702, 24} | V `FWE7` |
| ② 동측 국소 19링크 | ① ∪ 진입 8 ∪ 진출 4 | O `local19` |
| ④b 중 입력 1098 (FW_E 입구) | 첫 관측 링크 74 | V `u1098` |
| ④b 중 입력 1099 (FW_W 입구, 감시) | 첫 관측 링크 26 | V `u1099` |
| ④b 중 도시 입력 | 그 밖 | V `ucity` |
| 링크 66 (SC1004 남측) | 한 링크 | P `link = 66` |
| 도시도로 (codex 분할) | Ω701 − 양방향 본선 사슬 − 진입 커넥터 8 − Ω701 안 진출 커넥터 | O `urban_roads` (두 꼴) |
| 도시도로 codex 규칙 M (codex 꼴만) | X2 대조용 | M (FO − NC3, B − FO; FO − V-A 는 V-A 에 M 이 없어 "못 냄") |
| 감시: FW_W 본선 | 링크 26·120·10771 | O `FW_W_main` |

- 굵은 줄(Ω701, ④b, ④, Ω 밖 (a)(b) Ω701)은 한 줄만 떼어 적지 않습니다. 같은 표에 모두 둡니다.

## 4. FW_E 분해 칸 (FW_E 가 주 목표) — `FW/ana/fo_fwe.py`

- 정의·코드는 FW_E 분해 도구 그대로입니다: `fwe_r2.py` `59017c86…`, `fwe_r3.py` `34d5945a…`, `fwe_synth.py` `92904e95…`, `fwe_r1.py` `65882890…`, `tails.py` `cb6c0bd4…`, `fwe_analyze.py` `5c055dd4…`(함수는 import, 짝·칸 블록은 그대로 옮김). 자기 시험(FO := B)이 FWE_REF_C1 의 P-B·P-BVA 칸, R2_after 의 DA1, R1 의 DA2(NC3), VERIFY_EXTRA2 의 DA4 를 102칸 모두 같게 냈습니다 [실행 `FW/ana/selftest/fo_fwe_selftest.json`].
- 짝: X−NC3 (= FO − NC3; P-B 꼴 줄), B−X (= B − FO; P-BVA 꼴: R3 칸은 (B − NC3) − (FO − NC3), R2 칸은 직접 짝), X−VA (= FO − V-A; P-BVA 꼴).
- 칸(시드마다):

| 칸 | 내용 |
|---|---|
| RF1 | d① 우리 꼴 [0, 9000] · codex 꼴 [0, 8100] |
| RF2 | d② 같은 두 꼴 |
| RF3 | d① 다섯 구역(U·B1·M·B2·D) × 900 s (bin 꼴) |
| RF4 | 팔마다(FO·B·V-A) FW_E 미터 넷의 GREEN<10 주기 수, T_tight10, T_tight6, GREEN 초 분포, 평균 GREEN(readback 주기 표, GREEN 만). NC3 는 "기록 없음" |
| RF5 | 합류 넷(10639·10681·10490·10484) 유량 차 × 900 s (veh/h); X−NC3 는 팔 수준 함께 |
| RF6 | 미터별 연결로+접근 링크 재고·대기 차 (veh·h, 합과 × 900 s) |
| RF7 | ④b 1098 차 합과 × 900 s (첫 관측 차분) |
| RF8 | 진출 커넥터 넷(10643·10682·10481·10483) 재고 차 |
| RF9 | B1·M 번짐 분: 팔(FO·B·V-A)과 NC3; P-BVA 꼴 짝은 차 |
| RF10 | 팔마다 FW_E VSL<110 결정 수·시각(FO·B 는 110 고정이라 0 을 예상 [추론]) |
| RF11 | T_gain_a·T_gain_b·T_half·누적 d①(900 s–끝), T_gain − T_tight10 (X−NC3: 미터마다; P-BVA 꼴: 첫 팔의 T_tight10 기준) |
| 함께 | Ω701·④·Ω 밖 (a)(b) 두 꼴 (RF1 과 같은 줄에) |
| DA1 | 셀 5–9(c05–c09, 100 m 칸 가운데 배정) d① × 900 s 와 900 s–끝, d① 900 s–끝, 나머지 |
| DA2 | 팔마다(FO·NC3·B·V-A) 4,300 m 머리 분과 셀 5–9 혼잡 분(R1 규칙) |
| DA3 | 미터마다 "묶인 합류 칸 수" = 900 s 칸(900 s 부터) 중 그 미터 조임 몫 ≥ 0.30 이고 합류 차 ≤ −60 veh/h 인 칸 수 (X−NC3) |
| DA4 | 미터마다 900 s 칸의 합류 차·팔 수준·기준 수준(veh/h), 미터 평균 GREEN, 조임 몫, 미터 쪽 재고 차 (X−NC3; vf_extra2 칸) |

- 기준 열(나란히, 빼지 않음): `FD/out/FWE_REF_C1.json`(`ce39344b…`)의 같은 시드 P-B·P-VA·P-BVA 칸, 64cf joint − NC 옆 열.
- 문턱(2.0·5.0·1.0 veh·h, 0.30, −60 veh/h)은 칸을 나누는 선이지 판정 문턱이 아닙니다. 기구 깃발(PRE_FWE §6.1)은 이 규칙에서 내지 않습니다.
- 보고 순서: FW_E 칸(RF·함께)을 먼저, 그다음 T1·T2, 그다음 DA, 감시(FW_W), 실행 사실(§5).

## 5. 따로 적는 줄

1. **미터 실행(readback, GREEN 만)**: 런 점검 V3 — 미터 8개 × 810 주기(900–8,990 s)의 readback GREEN 초 대 명령 녹색, 어긋남 수, 미터별 GREEN 분포와 GREEN<10 주기 수. COMPARE_RULE_B §4-4 의 LDP 도구(rm_exec)는 codex 러너 런에 LDP 가 없어 쓰지 않습니다(B_RUNS §9; 이 대체는 FO 데이터 전에 정함).
2. **도시 신호 쓰기(GREEN 만)**: 런 점검 V4 — 명령 CSV 의 signal 행이 baseline 과 같음, signal_sg 행이 결정마다 같음, readback 으로 실현된 도시 SG GREEN 초가 native 프로그램(B `.lsa` 의 900 s 전 구간을 주기로 늘림)과 [901, 9000] s 에서 같음. 노랑·적색은 대조하지 않습니다.
3. **미터 명령 분포**: `dec_extract_fo.py` → 결정별 `rm_green`, `rm_out`(T = 900–8,850).
4. **VSL**: 런 점검 V5 (명령 CSV·vsl_readback 모두 110). 110 밖 값이 있으면 T 와 값.
5. **결정 벽시계·유지**: `walltimes_fo_s<s>.py` 와 런 점검 V8 (n, 평균, 중앙, 최대, > 1,500 s, > 3,600 s), 런 로그의 `DECISION_HOLD_ATTEMPT`·`DECISION_HELD_PREVIOUS` 와 요약 줄.
6. **램프 도착 예측**: `ramp_fc_fo_s<s>.py` 의 `logged`(= `forecast_ramp_arrival_total_vph`).
7. **감시(FW_W)**: ④b 1099, FW_W 본선(O), FW_W 미터 넷의 readback 분포(V3). 감시 칸은 FW_E 칸 뒤에 둡니다.
8. **단서**: 모든 FO 표 머리에 COMPARE_RULE_B §4-10 의 단서(64cf-s29 로 맞춘 계수·계약을 v3c3 에 얹은 런)와 "FO 는 codex 실행 기록 0회 조합(O2)" 을 적습니다.

## 6. 점검

- X1 [보고] V 대 O (dΩ701·dΩ635·d①·d④a) ≤ 0.05 veh·h (FO − NC3, FO − V-A). 넘으면 두 값과 "‡두 스캐너 차".
- X2 [보고] codex 꼴 도시도로 M 대 O ≤ 0.05.
- X3 [STOP] FO 사본 도구의 V-A − NC3 칸 = B 출력의 같은 칸(V 그대로, O |차| ≤ 1e-6).
- X3b [STOP] `CW/vhr_fo/scan_out` 의 NC3·V-A 스캔 = `CW/vhr_b/scan_out` 의 같은 파일(`scan_sec` 만 뺌).
- X4 [보고] 링크 66 우리 꼴: P 와 `CW/omega_fo/top66.json`.
- X5 [보고] 도착 수(`arrival_totals_9000`) FO 대 NC3·B.
- X6 [STOP] 도구가 FO 데이터에서 쓰인 대로 돌지 못하면 고치지 않고 그 칸 "못 냄", 멈추고 보고.
- X7 [STOP] `fo_fwe.py run` 의 `stops`(캐시 묶음 대조: vhr 스캔과 fwe_scan 이 같은 FZP, FO vhr 가 FO 런의 FZP)가 비어 있지 않음.
- X8 [보고] 접두 † 규칙(§1).

## 7. 서식·반올림·결측

COMPARE_RULE_B §6 그대로: veh·h 소수 첫째(부호, 음수 `−`), 반올림은 마지막에 한 번, 결측은 "못 냄(까닭)"·"없음"·"해당 없음", 0 으로 채우지 않음. 칸 이름은 "FO − NC3 v3c3-s31" 처럼 짝과 시드를 같이 씀. 도구 칸 이름(j1, joint)은 표에 쓰지 않음.

## 8. 도구와 실행 차례

- 도구 sha256 은 `SP/codex_handoff/fo/PINS_FO.sha256`(124줄, 이 규칙 고정 때 `sha256sum -c` 모두 OK)에 있습니다. 실행기 `FW/ana/fo_ana.ps1` 이 도구마다 sha 를 대조한 뒤 돌립니다.
- FO 사본 도구 = B 사본(PINS_B)에서 B 런 뿌리 → FO 런 뿌리, 출력 폴더 `*_b` → `*_fo`, 주석만 바꾼 것(생성 `FW/ana/make_spec_fo.py` + `CW/gate1/mkcopy.py` `8ec4f60c…`, 바뀐 줄 기록 `FW/ana/copies_fo_record.json`). `rm_exec_b_*` 는 복사하지 않음(§5-1).
- 무거운 일(FZP 를 읽는 모든 단계)은 공용 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 아래 하나씩(FZP 하나 = 잠금 한 번, 배타 생성, 30 s 마다 다시, 60 분 못 잡으면 멈춤, 내 토큰만 지움, 놓은 뒤 25 s 쉼), WMI 분리 발사, BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, 스레드 1.
- 차례: (가) `-Plan prescan`: NC3·V-A 의 vhr 스캔·첫 관측·omega 스캔(+ lnc)·scan_fzp nc — FO 데이터가 아니므로 FO 런 동안 해도 됨(X3·X3b 로 B 출력과 같아야 함). (나) 시드 런이 끝날 때마다 `-Plan stage -Seed s`: rb_readback(fo<s>), walltimes, ramp_fc, dec_extract, vhr 스캔·첫 관측·omega 스캔·scan_fzp joint·a1_fzp_firstdiff·fwe_scan(FO FZP), 그리고 `fo_run_check.py s`. (다) 세 시드 뒤 `-Plan final`: vhr_v3c3_all_fo, omega metrics, top66, metrics_fo ×3, `fo_fwe.py run`, `fo_tables.py`.

## 9. 이 규칙이 알려 주지 않는 것 [추론]

- COMPARE_RULE_B §8 그대로(64cf-s29 계수의 v3c3 적합성, 기구별 몫, codex 64cf 숫자의 재현). 작거나 반대 방향의 결과도 "계수 불일치" 와 "기구 효과 없음" 을 가르지 못합니다.
- B − FO 는 "도시 신호를 움직인 몫" 이지만, 미터 결정도 도시 신호 상태에 따라 달라지므로 두 레버의 상호작용이 함께 들어 있습니다.
- FO 의 도시 신호가 native 와 같은지는 GREEN 초만 봅니다. 노랑·적색 시각과 신호 쓰기 자체의 VISSIM 내부 효과는 보지 않습니다.
- 첫 관측 차분은 "같은 망·같은 시드면 도착열이 같다" 는 가정 위의 값입니다(X5).
