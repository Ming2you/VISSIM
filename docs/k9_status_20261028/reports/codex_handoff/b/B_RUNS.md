# B_RUNS — B 폐루프 런 기록 (v3c3-s31·s41·s43, 2026-10-26 14:40 – 10-27 00:39 KST)

- **r2 (2026-10-27 02:03 KST)**: VERIFY_B(`f2851f8b…`) D5 에 따라 §9 의 반박된 예시("`.lsa` 로 녹색 세기")만 지웠습니다. 런 기록·숫자는 바뀐 것이 없습니다. r1 은 `B_RUNS_r1.md`(`0e30cb71…`)로 남깁니다. 변경 기록은 §12.
- 이 문서는 **런 기록**입니다. 짝 차(Ω·④·Ω 밖 등) 숫자는 없습니다. 그 숫자는 COMPARE_RULE_B 의 분석 단계에서 냅니다. 판정 낱말은 쓰지 않습니다.
- 단서(COMPARE_RULE_B §4-10): 64cf-s29 로 맞춘 D 부류 계수와 64cf 유도 codex 계약 11개를 v3c3 에 그대로 얹은 런입니다. 계수 불일치와 기구 효과 없음을 가를 수 없습니다(PRE_B §7).
- 시드 3: v3c3-s31·s41·s43. 모두 우리 fit 시드이며 codex 계수에는 표본 밖입니다.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단.
- 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CW = `SP/codex_handoff/work`, R = `D:/VISSIM_runs/20261026_codex_b_v3c3`, RL(s) = `R/s<s>/sdmpc/runlog_sdmpc31_sdmpc9000_s<s>.txt`, SUM(s) = `CW/b/b_run_summary_s<s>.json`.
- 근거: D-K9-90(NOTES `59e41ff5…`), PRE_B_CONCURRENT `3d21dddd…`(바꾸지 않음), COMPARE_RULE_B `f902f7f0…`(바꾸지 않음), PINS_B `5e8ffbc5…`(바꾸지 않음; 끝난 뒤 `sha256sum -c` 54줄 OK) [실행 00:41].

## 0. 줄임말 (처음 한 번)

- B = codex 판(a49981ff)을 우리 v3c3 망으로 옮긴 폐루프 런. NC3 = 같은 시드 v3c3 무제어 런. V-A = 우리 묶음 B1 폐루프 런.
- 러너 = codex 폐루프 실행 스크립트 `run_closedloop3000.ps1`(FRZ_B1). 워치독 = 러너가 띄우는 감시 스크립트. 래퍼 = 우리 발사 스크립트 `b_wrapper_b1.ps1`. 발사기 = 세션과 떨어져 도는 `b_launcher.ps1`.
- FZP = VISSIM 차량 궤적 파일(5 s 프레임). LDP = 신호 상태 초별 기록 파일. 유지(hold) = 결정이 파이썬 예외로 실패할 때 앞 명령을 그대로 두는 동작.
- 결정 벽시계 = 한 결정에 걸린 실제 시간(런 로그 `CONTROLLER_DECISION … wall_sec`).

## 1. 한눈에

1. [실행] 세 런 모두 끝까지 돌았습니다. 런 로그에 `STAGE=SIM_DONE` 과 `SIM_SEC=9000` 이 있습니다(RL(31):6920-6921, RL(41):6828-6829, RL(43):6942-6943). 러너 종료 코드는 셋 다 0 입니다.
2. [실행] 시드마다 시도 1번입니다. 재발사 0, kill 0, 발사 거부 0, 이상 종료 0 입니다(발사기 로그 `SP/codex_handoff/b/b_launcher.log`, `R/_launcher/tryend_s<s>_run1_try1.json` status=completed).
3. [실행] 결정은 런마다 61개(워밍업 6 + 제어 55)이고 모두 exit 0 입니다. 유지 0, 결정 실패 0 입니다(RL(31):6897-6900 등, `DECISIONS_OK=61`·`DECISIONS_FAILED=0`·`DECISIONS_HELD_PREVIOUS=0`·`DECISIONS_HELD_ON_EXCEPTION=0`).
4. [실행] 첫 제어 결정 T=900 은 셋 다 exit 0 입니다. 벽시계는 s31 488.32 s, s41 521.82 s, s43 516.41 s 입니다(RL(s):500).
5. [실행] 제어 결정 벽시계 최대는 s31 597.7 s, s41 690.9 s, s43 634.7 s 입니다. 1,500 s 를 넘은 결정은 0 입니다.
6. [실행] 900 s 전 접두(≤ 895.1 s) 점검: v3c3-s43 은 NC3 와 같습니다. v3c3-s31·s41 은 다릅니다. 다른 것은 0.1 s 프레임의 1행(B 에만 차 1대)뿐이고, 5.1–900.1 s 프레임은 모두 같습니다(§7). 세 시드 모두 B 접두 sha 는 같은 시드 V-A 와 같습니다. 규칙(COMPARE_RULE_B §1)대로 s31·s41 의 B − NC3 칸에는 "†접두 다름" 을 붙여야 합니다.
7. [실행] 미터 실행 대조(`rm_exec_b_s<s>.py`)는 셋 다 쓰인 대로 돌지 못했습니다. B 런 폴더에 LDP 파일이 없습니다(§9). COMPARE_RULE_B §5 X6 대상입니다(열린 것).
8. [실행] VSL 명령은 모두 110 입니다(명령 CSV 3,630행, 결정 JSON 54개).

## 2. 런과 시각 [실행]

| 시드 | 래퍼 발사 (WMI) | 발사 직전 PC VISSIM | 워치독이 본 VISSIM | 래퍼 끝 | 래퍼 벽시계 | 결과 뿌리 |
|---|---|---|---|---|---|---|
| v3c3-s31 | 10-26 14:40:08, 래퍼 PID 42296 | 1 [29264] | 14:41:07 PID 38792 | 10-27 00:13:03 | 34,368.9 s | `R/s31` |
| v3c3-s41 | 10-26 14:41:22, 래퍼 PID 25476 | 2 [29264, 38792] | 14:42:19 PID 55280 | 10-27 00:24:38 | 34,993.3 s | `R/s41` |
| v3c3-s43 | 10-26 14:42:36, 래퍼 PID 54020 | 3 [29264, 38792, 55280] | 14:43:32 PID 23840 | 10-27 00:28:22 | 35,143.2 s | `R/s43` |

- 출처: SUM(s) `/wrapper/wmi_launch_run1_try1.json`, `/wrapper/wrapper_run1_try1_end.json`, `/launch.log`. 워치독 끝 줄은 `OK sdmpc31_sdmpc9000_s<s> attempt=1` 입니다.
- 발사기 PID 30860: 10-26 14:40:07 시작, 폴 387번, 10-27 00:28:52 `LAUNCHER_EXIT all seeds ended`. `LAUNCH_STOPPED.json`·`STOP_B_LAUNCHER`·`STOP` 파일은 없습니다(STOP_B_LAUNCHER 를 만들 일이 없었음).
- 남은 우리 프로세스 0, PC VISSIM 0 [실행 00:40].

## 3. 끝 기록 [실행]

| 시드 | STAGE | SIM_SEC | DECISIONS_OK / FAILED / HELD_PREVIOUS / HELD_ON_EXCEPTION | 결정 줄 (워밍업 T<900 / 제어 T≥900) | 러너 종료 | native_status | 런 로그 .err | FZP 바이트 · 데이터 행 |
|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 1,122,662,375 · 6,561,813 |
| v3c3-s41 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 1,126,938,207 · 6,587,544 |
| v3c3-s43 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 1,141,723,119 · 6,672,048 |

- 워밍업 결정 T = 1·150·300·450·600·750, 벽시계 13.3–21.0 s, 모두 exit 0 (SUM(s) `/runlog/warmup_decisions`).
- 제어 결정 T = 900, 1,050, …, 8,850, 9,000 (55개). 결정 JSON(action_<T>.json)도 61개입니다(SUM(s) `/decisions_dir/action_json_T`).
- `RUN_MODE=CONTINUOUS_EVENT_OBS150 controller=wu-link warmup_controller=no-control control_start_sec=900` (셋 같음).
- 결정 폴더의 `action_*.error.txt` 0개. 런 로그의 `ERROR|FATAL|ABORT|STOP` 로 시작하는 줄 0개(SUM(s) `/decisions_dir/error_txt`, `/runlog/error_like_lines`).
- B 결과 뿌리 전체 21.67 GB. 디스크: 시작 C 26.5 GB · D 250.3 GB → 끝 C 29.4 GB · D 224.0 GB [실행].
- `native_network_performance.json` 이 시드마다 있습니다(315 / 315 / 313 B, 키 schema·from_sec·to_sec·read_at_sim_sec·evaluated_links·all_links_included·time_unit·native). 값은 분석 단계(COMPARE_RULE_B §3 ④b 수준값)에서 읽습니다.

## 4. 결정 벽시계 [실행]

출처: SUM(s) `/runlog/wall_ge900`(런 로그 결정 줄), `CW/rawcheck_b/s<s>/walltimes_out.json`(고정 도구, 같은 값), 결정 `action_<T>.decision_budget.json` 의 wall_sec 최대 596.6 / 689.6 / 633.4 s.

| 시드 | n | 평균 | 중앙 | p90 | 최소 | 최대 (T) | > 360 | > 1,500 | > 1,800 | > 2,400 | exit ≠ 0 | 유지 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | 55 | 458.7 | 449.2 | 570.9 | 276.2 | 597.7 (1650) | 48 | 0 | 0 | 0 | 0 | 0 |
| v3c3-s41 | 55 | 470.1 | 469.9 | 592.0 | 287.6 | 690.9 (4050) | 51 | 0 | 0 | 0 | 0 | 0 |
| v3c3-s43 | 55 | 472.3 | 469.3 | 591.4 | 326.6 | 634.7 (2700) | 48 | 0 | 0 | 0 | 0 | 0 |

- 단위 s. "> 2,400" 칸은 COMPARE_RULE_B §4-6 글대로 옛 StallSec 문턱입니다. 새 StallSec 은 3,600 s 입니다(PRE_B_CONCURRENT §3).
- 첫 제어 결정 T=900: 488.32 / 521.82 / 516.41 s. 관문 1 의 T=900 재생 296–403 s 보다 깁니다. 관문 1 은 다른 VISSIM 1–2개, B 는 세 런의 T=900 결정이 겹쳐 돈 때입니다. 같은 조건이 아닙니다 [실행 값 · 추론 까닭].

### 4.1 동시 실행 상황 [실행 `CW/b/b_concurrency.py` v2 → `CW/b/b_concurrency.json`]

- 결정 구간 = `state_<T>.json` 쓴 시각 → `action_<T>.decision_budget.json` 쓴 시각. 그 구간에서 함께 돈 B 결정 수를 시간 가중 평균으로 셉니다.
- 남의 VISSIM 구간(`CW/b/other_vissim_windows.json`): 29264(codex rolling_cea) 10:14 – [21:11:10, 21:19:32] 사이에 끝남, 23564(다른 세션) 23:11:56 – [23:42:52, 23:51:11] 사이에 끝남. 끝 시각은 폴 사이로만 압니다. 둘 다 스스로 끝났고 우리는 건드리지 않았습니다.
- PC VISSIM 수: 14:43–21:1x 4개(남 1 + B 3), 21:1x–23:11 3개, 23:12–23:4x 4개, 그 뒤 3개 → 런이 끝나며 2·1·0 [실행 b_status 폴].

| 시드 | 남의 VISSIM 있음: n · 평균 · 최대 | 없음: n · 평균 · 최대 | 모름: n · 평균 | 함께 돈 B 결정 수: 평균 · 최소 · 최대 |
|---|---|---|---|---|
| v3c3-s31 | 37 · 491.0 · 597.7 | 15 · 386.7 · 521.4 | 3 · 419.9 | 2.5 · 2.1 · 3.0 |
| v3c3-s41 | 36 · 502.6 · 690.9 | 15 · 409.4 · 540.4 | 4 · 406.0 | 2.5 · 1.7 · 2.9 |
| v3c3-s43 | 36 · 503.5 · 634.7 | 15 · 418.2 · 503.6 | 4 · 393.8 | 2.5 · 1.4 · 2.9 |

- 벽시계 큰 다섯: s41 T=4050 690.9, s41 T=4350 673.4, s43 T=2700 634.7, s43 T=3600 627.5, s43 T=2850 624.5 s. 모두 남의 VISSIM 이 있던 때입니다.
- 이 표는 같은 결정을 조건을 바꿔 다시 잰 것이 아닙니다. 남의 VISSIM 유무와 sim 시각(앞쪽 결정 대 뒤쪽 결정)이 겹쳐 있어 까닭을 가르지 못합니다 [추론].

## 5. 유지(hold)와 예외 [실행]

- 세 런 모두 `DECISION_HOLD_ATTEMPT` 줄 0, `DECISION_HELD_PREVIOUS` 줄 0, `DECISIONS_HELD_PREVIOUS=0`, `DECISIONS_HELD_ON_EXCEPTION=0` 입니다(SUM(s) `/runlog/hold_attempts`, `/runlog/held_previous`; walltimes_out.json `held` 빈 목록).
- 결정 JSON 54개(T = 900–8,850)의 `metadata.controller_status` 는 모두 ok, `joint_leader_selection.selection_status` 는 모두 best_observed_feasible_sdmpc 입니다(dec_extract_b → `CW/rawcheck_b/dec_s<s>.json`, SUM(s) `/dec_tool`).

## 6. 미터·VSL 명령 [실행]

- 결정마다 명령 CSV 행 수: 미터 8, 신호 17, 신호 SG 122, VSL 66 (55개 결정 시각 모두 같음; SUM(s) `/action_csv/rows_per_kind_per_T`).
- VSL: 명령 CSV 3,630행이 모두 110.0 입니다. 결정 JSON 의 `vsl_out` 도 54개 모두 [110.0] 입니다. 110 밖 값 0 (SUM(s) `/action_csv/vsl_non110`, `/dec_tool/vsl_out_sets`).

### 6.1 미터 명령 녹색(초) — 명령 CSV, T = 900–9,000 (55개 결정 시각). 칸 = 녹색:결정 수

| 미터 | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| RM_C10480 | 2:49 · 4:4 · 6:1 · 8:1 | 2:41 · 4:10 · 6:3 · 8:1 | 2:42 · 4:9 · 6:3 · 8:1 |
| RM_C10482 | 10:55 | 10:55 | 10:55 |
| RM_C10484 | 4:1 · 6:30 · 8:22 · 10:2 | 2:3 · 3:4 · 4:4 · 5:15 · 6:9 · 7:7 · 8:8 · 9:1 · 10:4 | 4:5 · 6:34 · 8:16 |
| RM_C10490 | 3:6 · 5:5 · 6:5 · 7:10 · 8:5 · 9:16 · 10:8 | 4:6 · 6:17 · 8:16 · 10:16 | 3:1 · 4:5 · 5:5 · 6:9 · 7:13 · 8:4 · 9:11 · 10:7 |
| RM_C10639 | 2:26 · 4:6 · 6:10 · 8:7 · 10:6 | 2:12 · 4:10 · 6:13 · 8:13 · 10:7 | 2:39 · 4:4 · 6:3 · 8:4 · 10:5 |
| RM_C10644 | 10:55 | 10:55 | 10:55 |
| RM_C10646 | 6:14 · 8:14 · 10:27 | 6:24 · 8:12 · 10:19 | 4:2 · 6:15 · 8:19 · 10:19 |
| RM_C10681 | 2:2 · 3:14 · 4:14 · 5:9 · 6:5 · 7:2 · 8:2 · 9:5 · 10:2 | 2:2 · 3:6 · 4:17 · 5:6 · 6:9 · 7:2 · 8:8 · 9:2 · 10:3 | 2:3 · 3:6 · 4:18 · 5:6 · 6:6 · 7:3 · 8:8 · 9:3 · 10:2 |

- 명령 CSV 의 rate_vph 는 모든 행에서 녹색 × 90 입니다(SUM(s) `/action_csv/meter_rate_green_counts` 의 키 `rate/green`).
- RM_C10482·RM_C10644 는 세 시드 모두 55번 내내 녹색 10 입니다. 나머지 여섯은 결정마다 값이 바뀝니다.
- 결정 JSON 의 미터 녹색(`rm_green`, dec_extract_b, T = 900–8,850 의 54개)은 위 CSV 녹색과 같은 분포에서 T=9,000 하나가 빠진 것입니다(SUM(s) `/dec_tool/rm_green_counts`).

### 6.2 결정 JSON 의 미터 rate(`rm_out` = 진단 `ramp_metering`, dec_extract_b, T = 900–8,850, 54개). 칸 = rate:결정 수

| 미터 | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| RM_C10480 | 255.6:49 · 518.4:3 · 842.4:1 · 1166.4:1 | 255.6:41 · 518.4:9 · 842.4:3 · 1166.4:1 | 255.6:42 · 518.4:8 · 842.4:3 · 1166.4:1 |
| RM_C10482 | 3024.0:54 | 3024.0:54 | 3024.0:54 |
| RM_C10484 | 720.0:1 · 1080.0:30 · 1440.0:21 · 1512.0:2 | 360.0:3 · 540.0:4 · 720.0:4 · 900.0:15 · 1080.0:8 · 1260.0:7 · 1440.0:8 · 1512.0:5 | 720.0:5 · 1080.0:34 · 1440.0:15 |
| RM_C10490 | 540.0:6 · 900.0:5 · 1080.0:5 · 1260.0:10 · 1440.0:5 · 1512.0:23 | 720.0:6 · 1080.0:17 · 1440.0:16 · 1512.0:15 | 540.0:1 · 720.0:5 · 900.0:5 · 1080.0:9 · 1260.0:13 · 1440.0:4 · 1512.0:17 |
| RM_C10639 | 360.0:26 · 720.0:6 · 1080.0:10 · 1440.0:7 · 1512.0:5 | 360.0:12 · 720.0:10 · 1080.0:13 · 1440.0:12 · 1512.0:7 | 360.0:39 · 720.0:4 · 1080.0:3 · 1440.0:4 · 1512.0:4 |
| RM_C10644 | 1512.0:54 | 1512.0:54 | 1512.0:54 |
| RM_C10646 | 842.4:14 · 1166.4:14 · 1512.0:26 | 842.4:24 · 1166.4:12 · 1512.0:18 | 518.4:2 · 842.4:15 · 1166.4:19 · 1512.0:18 |
| RM_C10681 | 720.0:2 · 1080.0:14 · 1440.0:14 · 1800.0:9 · 2160.0:5 · 2520.0:2 · 2880.0:1 · 3024.0:7 | 720.0:2 · 1080.0:6 · 1440.0:17 · 1800.0:6 · 2160.0:9 · 2520.0:2 · 2880.0:7 · 3024.0:5 | 720.0:3 · 1080.0:6 · 1440.0:18 · 1800.0:6 · 2160.0:6 · 2520.0:3 · 2880.0:7 · 3024.0:5 |

- `rm_out` 은 명령 CSV 의 rate_vph(녹색 × 90)와 다른 양입니다. 두 칸은 다른 이름으로 따로 적습니다. 둘 사이의 식은 이 기록에서 확인하지 않았습니다 [추론].
- 램프 도착 예측 합(`forecast_ramp_arrival_total_vph`, 결정 JSON 메타데이터): 54개 결정 모두 값이 있습니다. 범위 s31 1,832.0–6,610.1, s41 1,791.0–6,526.8, s43 1,851.1–6,685.5 vph (SUM(s) `/dec_tool/forecast_ramp_arrival_total_vph`; 고정 도구 출력 `CW/rawcheck_b/s<s>/ramp_fc_out.json`).

## 7. 900 s 전 접두 짝 점검 (PRE_B §2-5, COMPARE_RULE_B §1) [실행]

주 값 = `CW/vhr_b/scan_out/j1_s<s>.json` 대 `nc3_s<s>.json` 의 `lf_sha_le_895_1`. 상세 = `CW/rawcheck_b/s<s>/fzp_firstdiff_s<s>.json` 의 짝 `a1-joint`(= B − NC3)·`a1-lnc`(= B − V-A). NC3·V-A 스캔은 원본 `CW/vhr/scan_out` 과 scan_sec 칸 말고 모두 같습니다(`CW/b/cmp_prescan.out.txt`).

| 시드 | B 접두 sha (행 수) | NC3 접두 sha (행 수) | B = NC3 | B = V-A | B 첫 프레임 · 0.1 s 행 | B − NC3 처음 다른 프레임 · 내용 | B − NC3 다른 프레임 중 ≤ 900.1 s | B − NC3 그다음 다른 프레임 | B − V-A 처음 다른 프레임 |
|---|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | `aef8ea5b…` (387,398) | `734a2d88…` (387,397) | 다름 | 같음 | 0.1 s · 있음 | 0.1 s · B 에만 1대(차 1, 링크 90), 다른 행 0 | 1 (0.1 s 프레임) | 905.1 s (900–1,050 s 블록 29 프레임) | 905.1 s |
| v3c3-s41 | `817dc613…` (398,332) | `b61cdb73…` (398,331) | 다름 | 같음 | 0.1 s · 있음 | 0.1 s · B 에만 1대(링크 26), 다른 행 0 | 1 (0.1 s 프레임) | 905.1 s (같음) | 905.1 s |
| v3c3-s43 | `86c06c73…` (393,558) | `86c06c73…` (393,558) | 같음 | 같음 | 5.1 s · 없음 | 905.1 s · 다른 행 171대 | 0 | — | 905.1 s |

- 전체 sha: B s31 `aef8ea5b61234b3362202e147590590d03990c7a00a8582c14ad96cff684c177`, B s41 `817dc613b9b8579cae41ab705964ebdff7f50786bbaa0a27c76697a88f0eda51`, B s43 `86c06c735b3aba291da9a2efc94fb6f4086ea90392ba2ea16410b9823605b9a8`.
- 도구는 다른 프레임이 있는 150 s 블록만 적습니다(a1_fzp_firstdiff_b_s31.py:53-64). s31·s41 의 B − NC3 블록은 '0'(0.1 s 프레임 1개)과 '900' 이상만 있습니다. 그래서 5.1–895.1 s 프레임 179개는 모두 같습니다. 900.1 s 프레임도 따로 대조했고 세 시드 모두 같습니다(행 3,106 / 3,086 / 3,057, 정렬 행 sha 같음; `CW/b/b_frame900.py`, 읽기만, 새로 씀). 그래서 B − NC3 의 0.1 s 다음 첫 다른 프레임은 905.1 s 입니다.
- **규칙 적용**: COMPARE_RULE_B §1 의 주 값은 "다름" 입니다. 그래서 분석 단계에서 v3c3-s31·s41 의 B − NC3 칸에는 모두 "†접두 다름" 을 붙여야 합니다. 런은 버리지 않습니다.
- **고정 때 예상과 다른 점**: COMPARE_RULE_B §1 은 "codex 러너 A1 FZP 는 5.10 s 부터" 라고 적었습니다. v3c3-s31·s41 의 B FZP 에는 0.1 s 행이 있습니다. V-A s31·s41 과 접두 sha 가 바이트로 같습니다 [실행].
- [추론] 0.1 s 행은 러너가 처음 한 스텝(`STARTUP_STAGE=FIRST_STEP_DONE`)을 따로 밟을 때 그 순간 망에 있던 차를 적은 것으로 봅니다. s43 은 그때 망에 차가 없어 행이 없는 것으로 봅니다. NC3 러너는 이 프레임을 적지 않습니다. 5.1 s 부터 같으므로 900 s 까지 교통 상태는 같다고 봅니다. 시험하지는 않았습니다.
- 세 시드 모두 B − NC3·B − V-A 의 905.1 s 이후 프레임은 8,100 s 까지 1,439개 모두 다릅니다(frames_differing; s31·s41 의 B − NC3 는 0.1 s 하나를 더해 1,440).

## 8. VISSIM .err [실행 SUM(s) `/err_b`, `/err_nc3`]

| 시드 | B `network/sdmpc31_sdmpc9000_s<s>_001.err` 줄 (Warning / Note) | NC3 `run/baseline_s<s>_v3c3nc_001.err` 줄 (Warning) | "Vehicle input … could not be finished completely" B / NC3 | B `network/VISSIG_Controller.dll.err` 줄 |
|---|---|---|---|---|
| v3c3-s31 | 1,616 (1,432 / 184) | 1,481 (1,481) | 1 / 1 | 9 |
| v3c3-s41 | 1,726 (1,542 / 184) | 1,412 (1,412) | 2 / 1 | 9 |
| v3c3-s43 | 1,597 (1,413 / 184) | 1,591 (1,591) | 0 / 0 | 9 |

- B 의 Note 184줄은 OBS150 기록 줄(`OBS150_ERR_FLUSH_PADDING` 122, `OBS150_ERR_BARRIER_…` 61, `Stop the simulation? : &Yes` 1)입니다.
- Warning 의 주된 글은 B·NC3 같습니다: "vehicle … already passed start of travel time section …", "After … seconds of waiting for lane change …".
- 미삽입 남은 대수는 ④b 와 관련된 값이라 이 기록에서는 줄 수만 적습니다. 대수는 분석 단계(COMPARE_RULE_B §5 X5)에서 봅니다.
- `VISSIG_Controller.dll.err` 9줄은 "The signal controller # has no signal program" 꼴입니다. NC3 폴더 쪽은 이 요약 도구가 run 바로 아래 `.err` 만 읽어서 대조하지 않았습니다.
- s41 은 `vissim_simulation_001.err`(1,327,104 B)와 `network/…_001.err`(1,333,214 B)의 크기가 다릅니다. 위 표는 network 쪽입니다 [실행].

## 9. 분석 도구 실행 기록 [실행]

모두 WMI 분리 발사, BELOW_NORMAL, 한 번에 하나, 실행 전 PINS_B sha 대조(`CW/b/b_ana_seed.ps1` 737ffc60…, 발사 `CW/b/b_ana_seed_launch_wmi.ps1` 37de941a…). 기록 `CW/b/ana_<plan>_s<s>.state.txt`, 영수증 `CW/b/launch_receipts.log`.

| 계획 | 시각 | 단계 (종료 코드, 초) |
|---|---|---|
| prescan s41 | 10-26 14:50:24–14:51:56 | vhr_scan_b va_s41 nc3_s41 (0, 91.8) |
| prescan s43 | 10-26 14:53:43–14:55:13 | vhr_scan_b va_s43 nc3_s43 (0, 89.9) |
| stage s31 | 10-27 00:14:11–00:15:51 | walltimes_b_s31 (0, 1.0) → ramp_fc_b_s31 (0, 97.8) → **rm_exec_b_s31 (1, 1.1)** → 멈춤 |
| rest s31 | 00:22:08–00:25:27 | dec_extract_b s31 (0, 96.8) → vhr_scan_b j1_s31 (0, 41.4) → a1_fzp_firstdiff_b_s31 (0, 60.5) |
| stage s41 | 00:26:06–00:27:42 | walltimes (0, 1.1) → ramp_fc (0, 93.8) → **rm_exec_b_s41 (1, 1.1)** → 멈춤 |
| rest s41 | 00:28:10–00:31:31 | dec_extract (0, 93.8) → vhr_scan_b j1_s41 (0, 42.4) → a1_fzp_firstdiff (0, 64.6) |
| stage s43 | 00:32:46–00:34:10 | walltimes (0) → ramp_fc (0, 80.8) → **rm_exec_b_s43 (1, 1.1)** → 멈춤 |
| rest s43 | 00:35:17–00:38:11 | dec_extract (0, 74.6) → vhr_scan_b j1_s43 (0, 40.4) → a1_fzp_firstdiff (0, 59.6) |

- **rm_exec 를 못 냄**: 셋 다 `FileNotFoundError: …/vissim_eval/sdmpc31_sdmpc9000_s<s>_9101_001.ldp`. B 의 `vissim_eval` 에는 `_001.fzp`·`_001.lsa`·`_001.mer` 셋만 있습니다 [실행 ls]. COMPARE_RULE_B §1 표는 B 에 LDP 가 있다고 적었습니다. §5 X6 에 따라 도구를 고치지 않았고 대체 계산도 하지 않았습니다. 그래서 COMPARE_RULE_B §4-4 미터 실행 대조 칸은 "못 냄(B 런 폴더에 LDP 없음)" 입니다.
- (r2) [실행 VERIFY_B D5] `.lsa` 에는 미터 SC 9101–9108 상태 줄이 1.0 s `off` 한 줄씩(런마다 8줄)뿐이라 `.lsa` 로는 미터 녹색을 셀 수 없습니다. 같은 런의 결정 폴더 `signal_readback.csv`(규칙 도구 목록 밖)를 검증자가 선언 밖으로 세어 보니, 세 시드 × 미터 8 × 10 s 주기 810개 모두 읽은 SG(신호 그룹) 녹색 = 명령 녹색이었습니다. SG 상태 수준이며 차 통과는 아닙니다.
- [추론] LDP 가 없는 까닭은 v3c3 망의 평가 설정(신호 기록 켜짐 여부)이 codex 64cf 망과 다른 데 있다고 봅니다. 망 파일은 열어 보지 않았습니다.
- 이 감시 단계에서 고정 도구 가운데 돌린 것은 위 표뿐입니다. Ω·④·지표 도구(omega701_recount_b, vhr_firstseen_b, vhr_v3c3_all_b, scan_fzp_b, metrics_b, top66)는 돌리지 않았습니다.
- 완료 요약 `CW/b/b_run_summary.py`(762420920ad7…, 12:24 고정, 그대로) → `CW/b/b_run_summary_s31.json`·`_s41.json`·`_s43.json`. 표 조각 `CW/b/b_runs_tables.py` → `CW/b/b_runs_tables.md`, 요약 출력 `CW/b/b_digest.py`, 900.1 s 프레임 대조 `CW/b/b_frame900.py`(셋 다 읽기만, 새로 씀; sha 는 LOG).

## 10. 감시 기록 [실행]

- 감시 도구: `SP/codex_handoff/b/b_status.ps1`(f07a8f6b…, 읽기만) 을 `CW/b/b_poll_wait.ps1`(4a0b0dd4…) 로 30 s 마다 불러, 깃발이 바뀌면 바로, 아니면 ≤ 520 s 뒤 끝남. 14:46 부터 00:39 까지 폴을 이어 감.
- 폴에서 본 무진행(진행 신호 사이 간격) 최대 약 126 s 입니다. 499 s 문턱(PRE_B_CONCURRENT §7-1)을 넘은 적이 없습니다. 그래서 120 s CPU 확인·kill·재발사를 한 번도 하지 않았습니다.
- PC VISSIM 수는 4 를 넘은 적이 없습니다(폴에서 본 최대 4).
- 남의 VISSIM(29264, 23564)은 건드리지 않았습니다. 이름으로 끈 것 0, PID 로 끈 것 0.
- 커밋·푸시 0. GWT8·`D:/VISSIM-merge/frozen`·`D:/VISSIM_handoff/20261024`·Y:·기존 런 폴더 쓰기 0. sealed/·봉인 시드 0. 금지 시험 0. COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT 바꾸지 않음.
- 시각 기록은 `SP/codex_handoff/LOG.md` 의 2026-10-26 14:51 – 10-27 00:4x 항목에 있습니다.

## 11. 열린 것 · 이 기록이 알려 주지 않는 것

1. **X6 (COMPARE_RULE_B §5, STOP 조건)**: `rm_exec_b_s<s>.py` 가 B 데이터에서 쓰인 대로 돌지 못했습니다(LDP 없음). 규칙은 "그 칸을 못 냄으로 두고 멈추고 보고" 입니다. 분석 단계를 이대로 나아갈지는 사용자가 정할 일입니다.
2. **접두 다름 (v3c3-s31·s41)**: 주 값이 "다름" 이라 B − NC3 칸에 "†접두 다름" 이 붙습니다. 차이는 0.1 s 프레임 1행뿐입니다(§7). 이 단서를 어떻게 읽을지는 분석 보고에서 밝힙니다.
3. 결정 벽시계는 동시 실행 아래 잰 값입니다. A1·관문 1 과 같은 조건이 아닙니다(PRE_B_CONCURRENT §3).
4. "같은 시드·코드·설정이면 결정 결과는 기다린 시간과 상관없다" 는 PRE_B_CONCURRENT §3 의 추론은 B 런 자체로 시험하지 않았습니다(§8 그대로).
5. 짝 차(Ω635·Ω701·④a·④b·④·Ω 밖·①·②·링크 66·도시도로)는 이 문서에 없습니다. COMPARE_RULE_B §7.5 의 분석 단계에서 냅니다.

## 12. 변경 기록 (r1 → r2)

| # | 곳 | 바꿈 | 근거 |
|---|---|---|---|
| 1 | §9 rm_exec 줄 | "대체 계산(예: .lsa 로 녹색 세기)" 의 예시를 지움 | VERIFY_B D5 (반박: `.lsa` 에 미터 SC 상태 줄은 1.0 s `off` 한 줄뿐) |
| 2 | §9 | `.lsa` 로 셀 수 없음과 선언 밖 readback 결과 한 줄을 더함 | VERIFY_B D5·§3-8 |
| 3 | 머리 | r2 표시 | — |
