# FO_RUNS — FO 폐루프 런 기록 (v3c3-s31·s41·s43, 2026-10-27 21:40 – 10-28 04:30 KST)

- 이 문서는 **런 기록**입니다. 짝 차(Ω701·④·Ω 밖 등) 숫자는 없습니다. 그 숫자는 COMPARE_RULE_FO §7 (다) `-Plan final` 뒤 분석 단계에서 냅니다. 판정 낱말은 쓰지 않습니다. "참·거짓" 은 PRE_FO 에 미리 적은 런 점검 칸의 값입니다.
- 근거: 사용자 결정 D-K9-112(관문 뒤 자리 나는 대로 3시드)·D-K9-113(O2), PRE_FO r2 `743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210` §6–§9, COMPARE_RULE_FO r2 `7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8` §1·§7, PINS_FO r2 `314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66`, 관문 요약 `d0494cfb78270f2d6b272e189e6b6606ed33c324de5262321d2195dc8adb2ce1`(pass true). 이 넷은 바꾸지 않았습니다.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, FO = `SP/codex_handoff/fo`, FA = `FO/work/ana`, R = `D:/VISSIM_runs/20261028_codex_fo_v3c3`, RL(s) = `R/s<s>/sdmpc/runlog_sdmpc31_sdmpc9000_s<s>.txt`, COL = `FO/work/run/fo_runs_collect.json`(이 문서의 숫자 모음, 읽기 전용 수집 도구 `fo_runs_collect.py` `0451d4d9…` 의 출력 `ec1ce7d8…`).

## 0. 줄임말 (처음 한 번)

- **FO** = codex SDMPC(분산 모형예측제어기)가 램프 미터만 정하고, 도시 신호 17곳은 baseline(v3c3 무제어 명령 값)을 다시 쓰기만 하는 v3c3 폐루프 팔. **B** = 같은 codex 판이 도시 신호 + 미터를 정한 팔. **NC3** = v3c3 무제어 런.
- **SC** = 신호 제어기, **SG** = 신호 그룹, **VSL** = 가변 제한속도(FO·B 모두 110 고정), **FZP** = VISSIM 차량 궤적 파일.
- **발사기** = 세션과 떨어져 도는 `fo_launcher.ps1`. **래퍼** = `fo_wrapper.ps1`(codex pwsh 7, env_hsw). **러너** = 동결 트리 FRZ_FO 의 `run_closedloop3000.ps1`. **워치독** = 러너가 띄우는 감시(StallSec 3,600, 자기 PID 만 끔).
- **자리** = PC 전체 VISSIM 수. 규칙: PC 전체 VISSIM + 우리 대기 런 < 4 일 때만 발사, 우리 런 최대 3.
- **유지(hold)** = 결정이 파이썬 예외로 실패하면 앞 명령을 그대로 두는 동작. **V1–V9** = PRE_FO §7 의 런 점검 칸(`fo_run_check.py` r2 `1415cddc…`).

## 1. 한눈에

1. [실행] **세 런 모두 끝까지 돌았습니다.** 런 로그에 `STAGE=SIM_DONE`·`SIM_SEC=9000`(RL(31):6735-6736, RL(41):6728-6729, RL(43):6539-6540), 러너 종료 0, 발사기 TRY_END status=completed 셋.
2. [실행] **시드마다 시도 1번입니다.** 재발사 0, 멈춤 기록(`stalled_*`) 0, kill 0, 발사 거부 0, `LAUNCH_STOPPED` 0. 멈춤 도구 `fo_stall_stop.ps1` 은 한 번도 부르지 않았습니다(`FO/fo_stall_stop.log` 없음).
3. [실행] **결정은 런마다 61개(워밍업 6 + 제어 55), 모두 exit 0, 유지 0** (`DECISIONS_OK=61`·`FAILED=0`·`HELD_PREVIOUS=0`·`HELD_ON_EXCEPTION=0`, `action_*.error.txt` 0).
4. [실행] **런 점검 V1·V2·V3·V4·V5·V6·V9 는 세 시드 모두 참**(usable true, pass true). V7·V8 은 보고 칸입니다(§7).
5. [실행] **자리 규칙대로 돌았습니다.** PC VISSIM 은 발사기 폴 265번에서 최대 4 였습니다. s43 은 남의 VISSIM 2개 때문에 약 36 분 기다린 뒤(SEAT_BUSY 폴 24번) 남의 것 하나가 스스로 끝나자 떴습니다. 남의 VISSIM(30964·51120·6768)은 세기만 했습니다.
6. [실행] **래퍼 벽시계**: v3c3-s31 22,204.5 s · v3c3-s41 22,801.9 s · v3c3-s43 21,779.5 s. 제어 결정 벽시계 최대 466.3 / 527.9 / 435.5 s, 1,500 s 넘은 결정 0.
7. 사건 하나(§8): s41 분석 단계의 상태 파일 끝 두 줄이 내 읽기 때문에 빠졌습니다. 런 점검 결과는 같은 도구로 다시 돌려 바이트 같음을 확인했습니다.

## 2. 런과 시각 [실행]

| 시드 | 래퍼 발사 (WMI, Normal) | 발사 직전 PC VISSIM (자리) | 워치독이 본 VISSIM | 래퍼 끝 | 래퍼 벽시계 | 결과 뿌리 |
|---|---|---|---|---|---|---|
| v3c3-s31 | 10-27 21:40:14, 래퍼 PID 40692 | 2 [30964, 51120] (둘 다 남) | 21:41:14 PID 53192 | 10-28 03:50:25 | 22,204.5 s | `R/s31` |
| v3c3-s41 | 10-27 21:41:28, 래퍼 PID 50620 | 3 [30964, 51120, 53192] | 21:42:25 PID 52432 | 10-28 04:01:33 | 22,801.9 s | `R/s41` |
| v3c3-s43 | 10-27 22:19:11, 래퍼 PID 53820 | 3 [30964, 53192, 52432] | 22:20:08 PID 55356 | 10-28 04:22:14 | 21,779.5 s | `R/s43` |

- 출처: `R/_launcher/receipt_s<s>_run1_try1.json`(ReturnValue 0, PriorityClass 32), `R/s<s>/fo_launch/wrapper_run1_try1_started.json`·`_end.json`, `R/s<s>/sdmpc/WATCHDOG_PROGRESS.txt`(끝 줄 `OK sdmpc31_sdmpc9000_s<s> attempt=1 elapsed=22192s / 22788s / 21766s`), `R/wmi_launch_lines.txt` `16447b07…`. COL `/seeds/s<s>/receipt`·`/wrapper_end`·`/watchdog_vissim`.
- 시드는 각 런의 `run_provenance_sdmpc31_sdmpc9000_s<s>.json` 의 `seed` 로 확인했습니다(31·41·43; 폴더 이름에서 읽지 않음).
- 워치독 끔 정책 줄: 세 런 모두 `KILL_POLICY … pid_only` (자기 러너 PID 만). 워치독의 KILL·STALL·TIMEOUT 줄 0.
- 발사기: `fo_launcher_start.ps1` 10-27 21:40:13 → WMI ReturnValue 0, 발사기 PID 47704(영수증 `FO/fo_launcher_start_receipts.log` `03f768d1…`). 폴 265번, 10-28 04:22:32 `LAUNCHER_EXIT all seeds ended`. 발사기 로그 `FO/fo_launcher.log` `b62f9513…`(276줄, ERROR 줄 0), 마지막 상태 `R/_launcher/STATE.json` `cfe88841…`.
- 끝난 뒤(04:31): 우리 프로세스(래퍼·러너·VISSIM·발사기·분석) 남은 것 0, 공용 잠금 파일 없음, STOP 파일 0, PC VISSIM 1개(6768, 남의 것).

## 3. 자리 기록 [실행 COL `/launcher`]

| 항목 | 값 |
|---|---|
| 발사기 폴 수 · PC VISSIM 수 분포 | 265 · {1: 1, 2: 14, 3: 24, 4: 226} 폴, 최대 4 |
| s43 자리 기다림 | 10-27 21:42:41 – 22:17:40 의 SEAT_BUSY 폴 24번(PC VISSIM 4 = 남 2 + 우리 2). 22:19:11 발사(직전 3) |
| 남의 VISSIM 30964 | 우리 발사 전부터(14:25 시작) – 발사기 폴 10-28 01:04:05 에 있음, 01:05:37 에 없음. 스스로 끝남 |
| 남의 VISSIM 51120 | 10-27 21:40:03 시작(우리 첫 발사 11 s 전) – 22:17:40 폴에 있음, 22:19:11 재셈에 없음. 스스로 끝남 |
| 남의 VISSIM 6768 | 10-28 01:25:28 폴에 없음, 01:27:00 폴부터 있음 – 04:31 에도 돎. 우리 셋 + 이것 = 4 |

- 남의 VISSIM 은 세기만 했고, PID 로든 이름으로든 끈 것 0 입니다. 다른 세션의 발사는 그 세션의 자리 규칙 몫입니다.
- 디스크: 발사 때 C 16.1 GB · D 191.5 GB → 끝난 뒤 C 15.4 GB · D 179.9 GB. FO 결과 뿌리 시드별 2.48 / 2.49 / 2.45 GB [실행 COL `/seeds/s<s>/result_root_bytes`].

## 4. 끝 기록 [실행 COL]

| 시드 | STAGE | SIM_SEC | DECISIONS_OK / FAILED / HELD_PREVIOUS / HELD_ON_EXCEPTION | 결정 줄 (워밍업 / 제어) | 러너 종료 | native_status | 런 로그 .err | `action_*.json` · `error.txt` | FZP 바이트 |
|---|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 61 · 0 | 1,140,488,386 |
| v3c3-s41 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 61 · 0 | 1,171,446,282 |
| v3c3-s43 | SIM_DONE | 9000 | 61 / 0 / 0 / 0 | 61 (6 / 55) | 0 | requested_native_arms_complete_unanalyzed | 0 B | 61 · 0 | 1,165,375,506 |

- `RUN_MODE=CONTINUOUS_EVENT_OBS150 controller=wu-link warmup_controller=no-control control_start_sec=900` (셋 같음, RL(s):469).
- 런 로그의 `ERROR|FATAL|ABORT|STOP` 로 시작하는 줄 0. `DECISION_HOLD_ATTEMPT`·`DECISION_HELD_PREVIOUS` 줄 0.
- `vissim_eval` 에는 `_001.fzp`·`_001.lsa`·`_001.mer` 셋이 있습니다(B 와 같은 꼴, LDP 없음).
- VISSIM `network/sdmpc31_sdmpc9000_s<s>_001.err` 줄(Warning / Note): s31 1,541 (1,357 / 184), s41 1,762 (1,578 / 184), s43 1,691 (1,507 / 184). "could not be finished completely"(차량 입력 미완) 줄 1 / 2 / 0. `VISSIG_Controller.dll.err` 9줄씩. 미삽입 대수는 분석 단계 몫입니다.

## 5. 결정 벽시계 [실행 COL `/seeds/s<s>/decisions`, 런 로그 `CONTROLLER_DECISION` 줄]

| 시드 | 워밍업 6개 (최소–최대) | 첫 제어 T=900 | 제어 n | 평균 | 중앙 | p90 | 최소 | 최대 (T) | > 360 | > 1,500 | > 3,600 | exit ≠ 0 | 유지 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v3c3-s31 | 14.1–18.5 | 155.4 | 55 | 238.1 | 211.9 | 372.5 | 118.5 | 466.3 (4500) | 6 | 0 | 0 | 0 | 0 |
| v3c3-s41 | 12.8–19.4 | 159.7 | 55 | 247.7 | 204.2 | 409.5 | 127.5 | 527.9 (3150) | 9 | 0 | 0 | 0 | 0 |
| v3c3-s43 | 16.2–20.4 | 138.7 | 55 | 231.4 | 211.7 | 365.1 | 113.0 | 435.5 (6450) | 6 | 0 | 0 | 0 | 0 |

- 단위 s. 세 런과 남의 VISSIM 1–2개가 함께 돈 때의 값입니다. 관문 재생 R1–R3(161–171 s, PC VISSIM 1개)과 같은 조건이 아닙니다 [실행 값 · 추론 까닭].
- 참고(조건 다름, 판정 아님): B 런의 래퍼 벽시계는 34,369–35,143 s, 제어 결정 최대 597.7–690.9 s 였습니다 [읽음 B_RUNS r2 §2·§4].

## 6. 무진행 정책·재발사 [실행]

- 감시: `FO/work/run/fo_poll_wait.ps1`(`e9694a4d…`, B 의 `b_poll_wait.ps1` `4a0b0dd4…` 에서 상태 스크립트 경로·머리 주석만 바꾼 읽기 전용 사본)이 30 s 마다 `fo_status.ps1`(`9b4e35be…`)를 부르고, 깃발이 바뀌면 바로, 아니면 ≤ 520 s 뒤 돌아옴. 21:40 – 04:31 동안 폴 호출을 이어 갔고, 호출 사이 간격은 9 분 아래였습니다.
- 활성 런에 `IDLE_OVER_499` 깃발이 선 적이 없습니다. 깃발 변화로 돌아온 경우는 T=900 끝남·s43 발사·런 끝남·**끝난 런**(s31·s41)의 IDLE 표시·발사기 끝뿐이었습니다. 끝난 런의 IDLE 표시는 활성 시도가 아니라 정책 대상이 아닙니다(멈춤 도구도 `NOT_ACTIVE` 로 끝나는 꼴). 출력에서 본 활성 런의 진행 나이 최대는 약 69 s 였습니다.
- 그래서 120 s CPU 확인·PID 멈춤·이름 바꾸기·재발사를 한 번도 하지 않았습니다. 워치독 StallSec 3,600 도 발동하지 않았습니다(워치독 끝 줄 OK).

## 7. 런 점검 V1–V9 (PRE_FO r2 §7, COMPARE_RULE_FO §7 (나) `-Plan stage` 의 마지막 단계) [실행]

출력: `FA/runcheck_s31.json` `2aa529424885d440dcba653e9ec7c72bebdfa681ad26ab1918401ef262323d73`, `FA/runcheck_s41.json` `0dbf0a43585bedea3433c8d1bacea0a8fcff453d5ac318a2660baf351f642750`, `FA/runcheck_s43.json` `816890954f6fca2126fd39f83916a12a2584e6e410ca82f68af566bb1effd89a`.

| 칸 | v3c3-s31 | v3c3-s41 | v3c3-s43 |
|---|---|---|---|
| V1 완주 (멈춤 아님, 쓸 수 있는 런) | 참: runner_exit 0, SIM_DONE·9000, FAILED 0 = HELD_ON_EXCEPTION 0, error.txt 0 | 참 (같음) | 참 (같음) |
| V2 provenance [멈춤] | 참: 시드 31, 망 `3de889f0…`, 설정·RW 설정 sha `80e0abef…`, freeze `d7fa4db6…`, 유지 env (hold_previous_on_exception, 1, 0) | 참 (시드 41) | 참 (시드 43) |
| V3 미터 명령대로 [멈춤] | 참: 미터 readback 18,583행 요청 = 읽음·ok 1, 8 × 810 주기 readback GREEN 초 = 명령, 어긋남 0 | 참: 17,331행, 어긋남 0 | 참: 17,761행, 어긋남 0 |
| V4 도시 신호 baseline 만 [멈춤] | 참: (a) signal 935행 baseline 차 0, (b) signal_sg 일정 55결정에서 1개, (c) 쓴 SG 136 GREEN 차 0 프레임, (d) 쓰지 않은 SG 146 FO `.lsa` 차 0 프레임, (e) 도시 readback 46,396행 어긋남 0 | 참 (같은 수) | 참 (같은 수) |
| V5 VSL 110 [멈춤] | 참: 명령 VSL 4,026행 모두 110.0, vsl_readback 16,104행 110·ok 1 | 참 (같은 수) | 참 (같은 수) |
| V6 900 s 전 접두 | FO = B (`aef8ea5b…`), FO ≠ NC3 (0.1 s 행 1개) → FO − NC3 칸 † | FO = B (`817dc613…`), FO ≠ NC3 (0.1 s 행 1개) → † | FO = B = NC3 (`86c06c73…`), 0.1 s 행 없음 |
| V7 워밍업 (보고) | t=1–750 명령 CSV 6개 바이트 = B, t=1 글자 = solo 글자 | 같음 | 같음 |
| V8 벽시계 (보고) | n 55 · 평균 238.1 · 중앙 211.9 · 최대 466.3 · > 1,500 0 · > 3,600 0 | n 55 · 247.7 · 204.2 · 527.9 · 0 · 0 | n 55 · 231.4 · 211.7 · 435.5 · 0 · 0 |
| V9 범위 유지 없음 [멈춤] | 참: 범위 검사 글자 든 유지 0, error.txt 0 | 참 | 참 |
| usable · pass | true · true | true · true | true · true |

- V4 (d)·(e)·V3 의 SG/행 수는 세 시드에서 같은 꼴입니다(쓰는 SG 136 = 창 122 + 적색 14, 쓰지 않는 SG 146). V4 의 FO `.lsa` sha: s31 `117d626e…`, s41 `85002675…`, s43 `fa60a1c1…`. FO `.lsa` 와 B `.lsa` 의 [2, 899] 도시 SG GREEN 차 0 SG(보고 칸).
- V3 보고 칸(readback 녹색 < 10 s 인 주기 수, 810 주기 중; s31 / s41 / s43): RM_C10480 810 / 810 / 810, RM_C10482 0 / 0 / 0, RM_C10484 795 / 765 / 765, RM_C10490 765 / 660 / 675, RM_C10639 735 / 675 / 705, RM_C10644 0 / 0 / 0, RM_C10646 615 / 585 / 645, RM_C10681 810 / 720 / 720. 값의 해석은 분석 단계 몫입니다.
- V6 † 는 COMPARE_RULE_FO §1 규칙대로 분석 표에 붙입니다. B 에서도 v3c3-s31·s41 이 같은 꼴이었습니다(B_RUNS §7).

### 7.1 분석 계획 실행 기록 (COMPARE_RULE_FO §7, `fo_ana.ps1` `543a6d16…`, fo_launch_wmi.ps1 로 WMI 발사, BelowNormal, FZP 일마다 공용 잠금) [실행]

| 계획 | 시각 | 단계 · 결과 | 상태 파일 sha |
|---|---|---|---|
| prescan (NC3·V-A, FO 데이터 아님) | 10-27 21:47:20–22:06:06 | 22단계 모두 exit 0, 잠금 22번 0 s 만에 잡음 | `ana_prescan.state.txt` `3b5ce4c8…` |
| stage s31 | 10-28 03:51:05–03:58:00 | 11단계 모두 exit 0 (rb_readback, walltimes, ramp_fc, dec_extract, vhr_scan, vhr_firstseen, omega 스캔, scan_fzp joint, a1_fzp_firstdiff, fwe_scan, fo_run_check) | `ana_stage_s31.state.txt` `05ef2d58…` |
| stage s41 | 04:03:27–04:10:14 | 단계 1–10 exit 0; 단계 11 출력 끝까지 씀, 상태 파일에 끝 줄 없음(§8) | `ana_stage_s41.state.txt` `e4b8dc81…` |
| stage s43 | 04:23:00–04:29:46 | 11단계 모두 exit 0 | `ana_stage_s43.state.txt` `5456f177…` |

- 점검 X3b 를 미리 셈(가벼운 일, final 계획에서 다시 셈): `CW/vhr_fo/scan_out` 의 nc3_s31·s41·s43·va_s31·s41·s43 이 `CW/vhr_b/scan_out` 의 같은 파일과 scan_sec 빼고 같음 6/6.
- `-Plan final`(Ω701·④·Ω 밖·FW_E 칸·표)은 돌리지 않았습니다. 분석 단계 몫입니다.

## 8. 사건: s41 상태 파일 끝 두 줄 빠짐 (내 읽기 탓) [실행]

- 무엇: `ana_stage_s41.state.txt` 에 "step end 11" 과 "plan stage_s41 done" 이 없고, fo_ana 프로세스(PID 29748)는 사라졌습니다. 단계 11 `fo_run_check.py 41` 은 04:10:14 에 출력(RUNCHECK 줄, `runcheck_s41.json` 5,395 B)을 끝까지 썼고 .err 는 0 B 였습니다.
- 까닭: 같은 04:10:14 에 내 감시 명령이 그 상태 파일을 PowerShell `Get-Content` 로 읽었습니다. 시험 두 개(scratchpad 임시 파일): PS 5.1 `Get-Content | Select-String` 이 읽는 동안, 그리고 .NET `FileShare.ReadWrite|Delete` 로 연 동안에도 `Add-Content` 는 "being used by another process" 로 실패했습니다. `fo_ana.ps1` 은 `ErrorActionPreference Stop` 이라 Note(Add-Content) 실패에서 끝납니다. 그래서 내 읽기가 원인으로 봅니다 [추론, 시험으로 받침].
- 보충(선언 밖, 가벼운 읽기 전용, 결과 바꾸지 않음): 핀 sha 같은 `fo_run_check.py` 를 fo_ana 와 같은 env(python -B, PYTHONHASHSEED=0, 스레드 1)로 `41 <다른 출력 경로>` 로 다시 돌림 → **exit 0**, 출력 `FA/recheck/runcheck_s41_recheck_44964.json` 이 `runcheck_s41.json` 과 바이트 같음(`0dbf0a43…`), `.v4c.json` 도 같음(`6a192d85…`).
- 그 뒤 s43 stage 는 프로세스가 끝난 것을 확인한 뒤에만 상태 파일을 읽었고, 끝 줄이 정상으로 있습니다.
- 교훈: 돌고 있는 도구가 `Add-Content` 로 쓰는 파일은 어떤 방식으로도 읽지 않는다(프로세스 끝을 본 뒤 읽음).

## 9. 지킨 것 [실행]

- VISSIM 은 발사기(WMI, 자리 규칙)로만 띄움: 우리 런 최대 3, PC 전체 최대 4. 시드마다 한 번. 남의 VISSIM·프로세스 손댐 0, kill 0(우리 것도 0).
- 무거운 일(FZP 스캔)은 공용 잠금 `heavy.lock` 아래에서만, 내 토큰만 지움, 끝난 뒤 잠금 파일 없음.
- `D:/VISSIM-merge/frozen/*`·FRZ_B0·FRZ_B1·V-A·K92·FRZ_FO·GWT8(c20aff1d)·codex 작업 트리 쓰기 0. 커밋·푸시 0. `sealed/`·봉인 시드 37/59/61/67·codex 64cf-s59/s61/s67·v3c3-s47 값 0. 금지 시험 0.
- PRE_FO·COMPARE_RULE_FO·PINS_FO·관문 요약은 바꾸지 않았습니다(발사 전 `sha256sum -c PINS_FO.sha256` 154/154 OK).
- 새로 만든 파일: `FO/work/run/fo_poll_wait.ps1`(감시, 읽기 전용), `FO/work/run/fo_runs_collect.py`·`.json`(이 문서의 숫자 모음, 읽기 전용), `FA/recheck/*`(§8 보충), 이 문서, LOG 항목.

## 10. 열린 것 · 이 기록이 알려 주지 않는 것

1. 짝 차(Ω701·④a·④b·④·Ω 밖·①·②·진입 E·W·링크 66·도시도로·FW_E RF/DA 칸)는 이 문서에 없습니다. `-Plan final` 과 COMPARE_RULE_FO 표 단계에서 냅니다.
2. V6 † (v3c3-s31·s41 의 FO − NC3) 는 B 와 같은 꼴입니다. 읽는 법은 분석 보고에서 밝힙니다.
3. 결정 벽시계는 동시 실행 아래 잰 값이라 관문 재생·B 와 같은 조건이 아닙니다.
4. §8 사건의 원인은 시험으로 받친 추론입니다. 그 순간의 실제 예외 글은 남아 있지 않습니다(숨김 창, 출력 재지정 없음).

## 11. sha256 (이 단계 증거)

| 파일 | sha256 |
|---|---|
| `FO/fo_launcher.log` | `b62f95139f6544226ece61bbf402de3825612a64235de6922712ebcf61e2f22a` |
| `FO/fo_launcher_start_receipts.log` | `03f768d1cda3fe69c3a3895f5f8f31341a33da536530210b0e2dc5bc70bb54b2` |
| `R/wmi_launch_lines.txt` | `16447b073761f8861dd8a480bbec54cf32004580d8cceef643c95f96280145ed` |
| `R/_launcher/STATE.json` | `cfe888416283ebe5de63e06330d87d6c94f4c915e89a33bb358529364a42a45b` |
| `FA/runcheck_s31.json` / `s41` / `s43` | `2aa52942…` / `0dbf0a43…` / `81689095…` (64자는 §7) |
| `FA/ana_prescan.state.txt` | `3b5ce4c8ae1952ad2283bfb979ffd701446c54f79ad4ee844a710c1cbd53df33` |
| `FA/ana_stage_s31.state.txt` / `s41` / `s43` | `05ef2d58b9911a6f265440a329cd0763c98a34d730576452b28742dab2412bb2` / `e4b8dc814c2ba5155b1d4ba4665a6a8e2f02207ed466b85d055488ab0cf62518` / `5456f17746dbac6ba59ecfd5bb54b73722e860c854c7e0eeb75aeb203bcd2364` |
| `FO/work/run/fo_poll_wait.ps1` | `e9694a4d4e9fb9a7b283be46ab1e562d045b3433384b2621e10a90bcab0d0a71` |
| `FO/work/run/fo_runs_collect.py` / `.json` | `0451d4d9592693a36168773f53f1db3372348dfa074912c708056544903e27bc` / `ec1ce7d8dabd15f2cc9ed5a90700bfe4811f1c796a241ce8f5a4b361f3b370f3` |
| 이 문서 | `FO/FO_RUNS.md.sha256` |
