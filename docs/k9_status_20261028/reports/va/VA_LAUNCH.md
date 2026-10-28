# V-A 발사 보고 (Launch 단계, 보충 34 §6) — 2026-10-23

- 이 문서는 V-A(묶음 B1을 배포한 폐루프 VISSIM 3시드 런)의 발사 전제 마련, 시드별 사전점검, 발사, s43 감시기, 첫 SDMPC 결정 건강 점검 기록입니다. 판정과 분석은 없습니다. 성능 숫자(Ω·TTT·지연·목적값·녹색)는 열지 않았습니다.
- 표시: [실행] 이 단계에서 직접 돌려 확인, [읽음] 파일·코드에서 확인, [추론] 시험하지 않은 판단.
- 이 문서는 subagent의 Write 도구가 `.md` 쓰기를 막아 `VA/launch/va_launch_src.txt`로 쓴 뒤 바이트 그대로 `VA/VA_LAUNCH.md`로 복사했습니다(J1 선례와 같은 방식).

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. AV = `VA/analysis`. REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`.
- RVA = V-A 런 폴더(RunsRoot) `D:/VISSIM_runs/20261023_sdmpc31_k92`. FRZ_K92 = V-A 동결본 `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`(`FREEZE.json` sha256 `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`, head K9-2-7 `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`).
- WMI = 윈도 관리 도구(`Invoke-CimMethod -ClassName Win32_Process -MethodName Create`, 이 세션과 떼어 프로세스를 띄움). WD = 감시 러너(watchdog). SDMPC = 이 계열의 모형예측 제어기(wu-link). dev 좌석 = 창 제목에 `obs150|sdmpc|probe`가 있는 VISSIM.
- 유지(hold) = 결정이 예외로 죽으면 직전 명령을 다시 쓰는 장치. W·H-b = 묶음 B1의 두 튜닝 키(SC109 서측 직진 용량, (173, p4) 하한 씨앗).
- 시드는 망 접두어를 붙여 v3c3-s31처럼 적습니다.

## 1. 결론: pass = true

1. **v3c3-s31과 v3c3-s41은 돌고 있고, 첫 SDMPC 결정(T = 900)까지 건강합니다** [실행].
   - v3c3-s31: 12:34:21 발사, cmd PID 19740, VISSIM PID 22724. T = 900 결정 12:52 끝, `exit=0`, wall_sec 581.17. 건강 점검 H1–H16·T1·T2 18항목 모두 참.
   - v3c3-s41: 12:36:17 발사(`-AllowConcurrentDev`), cmd PID 18580, VISSIM PID 27572. T = 900 결정 12:54 끝, `exit=0`, wall_sec 579.3. 18항목 모두 참.
2. **s43 감시기가 돌고 있습니다** [실행]. 12:38:25 WMI 시작, cmd PID 24564 → powershell PID 8084. 3분마다 폴하고 폴마다 한 줄을 씁니다. 지금까지 POLL 1–8 모두 `WAIT`(두 런 모두 살아 있음, 좌석 총 2·dev 2).
3. **발사 전제 (1)–(6)은 첫 발사 전에 모두 참이었습니다**(보충 34 §6.1). 그 가운데 (4) 분석 도구·방법 문서·검증 도구 고정과 (5) 감시·건강·감시기 고정은 이 단계가 처음 만들었습니다(§3, §4). V-A 자료가 0개일 때 고정했습니다.
4. 시드별 사전점검 ×3은 관문 판정기로 조건 1–8 모두 참이었습니다(§5).
5. 유지(hold) 0, `DECISION_FAILED` 0, 오류 파일 0. 좌석 규칙을 지켰고 PC 전체 VISSIM은 최대 2개였습니다. 아무것도 끄지 않았습니다.
6. 공개할 작은 결함 하나: 감시기 시작 기록 줄의 cwd 칸이 내 PowerShell 변수 겹침으로 잘못 찍혔습니다. 발사 자체는 맞았고, 고친 줄을 따로 남겼습니다(§10-4).

## 2. 시작 전 확인 [실행]

- **재개 점검**: `VA/LOG.md`에 Launch 줄 없음, `VA/launch`·`VA/analysis`·`VA/VA_LAUNCH.md` 없음, RVA에는 `_preflight` 아래 네 폴더(동결 사전점검 1 + G-H5′ 3)뿐, RVA 런 이름 폴더·`wmi_launch_lines.txt` 없음, VISSIM·python·cscript 0 → 앞 시도 흔적 없음, 처음부터.
- **발사 전제** (보충 34 §6.1 R18):

| # | 전제 | 결과 |
|---|---|---|
| (1) | `VA/a34_pins.sha256` 대조, 보충 34 sha = 고정점 | 83/83 OK, 보충 34 `a05592d4…205e` = `AMENDMENT34_FIXED.md`(`fef58eca…c167`) 값, 결정 기록 `6b76cc09…af88` |
| (2) | VerifyPromote pass, 푸시·동결 PASS | `VERIFY_PROMOTE_VA.md` pass = true, `FREEZE_PUSH.md` pass = true(원격 k92 = `c20aff1d…`) |
| (3) | 관문 FG·1–5·G-H5′ PASS, `VERIFY_GATES_VA.md` pass = true | 참(`K92_VA_OFFLINE_GATES.md` `f5812e45…`, `VERIFY_GATES_VA.md` `2c349f21…`) |
| (4) | 분석 도구·`ANALYSIS_METHOD_VA.md`·검증 도구 sha 고정 | 이 단계에서 만들고 고정(§3). 첫 발사 직전 다시 대조 20/20 OK |
| (5) | `va_monitor.py`·`va_health.py`·감시기(드라이런 8건) sha 고정 | 이 단계에서 만들고 고정(§4). 첫 발사 직전 다시 대조 8/8 OK |
| (6) | C:·D: 8 GB 이상, K8 가지 = `b9734abe…` | C: 39.5 GB, D: 365.6 GB, K8 가지 로컬·원격 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991` |

- GWT8 HEAD `c20aff1d…`, `status --porcelain` 0줄(끝까지 같음).

## 3. 발사 전제 (4): 분석 도구·방법 문서·검증 도구 [실행]

- **왜 이 단계에서 했나**: 보충 34 §6.1 (4)와 §8.0-2는 이것을 "첫 V-A 발사 전"에 고정하라고 정합니다(J1보다 이름, R18). 앞 단계들에 이 일을 맡은 곳이 없어, 발사를 맡은 이 단계가 V-A 자료 0 상태에서 만들었습니다.
- **파일** (AV, 고정 목록 `AV/va_analysis_pins.sha256` sha256 `39a97e7f5a95d3db2d9841849ea3613f26b4d8a3a5426904156aac4770f7903e`, 20줄):
  - 방법 문서 `AV/ANALYSIS_METHOD_VA.md` `72b004f6ec81e61f…`(= `AV/method_src.txt` 바이트). 보충 34 §8을 코드로 옮긴 조작 정의만 적었습니다(두 짝·세 합집합·지표 1–14·표시 규칙·검증·자기 시험·공개).
  - 분석 도구 여덟(이름은 보충 34 §8.0 그대로): `va_provenance.py` `80c97aff…`, `va_scan.py` `34076c3c…`, `va_metrics.py` `e6b8bda7…`, `va_fzp_local.py` `9f34f2b4…`, `va_control.py` `5c9d944f…`, `va_followup.py` `4c6ba408…`, `va_tables.py` `37a8bb36…`, `va_report_build.py` `651812cd…`. 더한 파일: 공통 `va_common.py` `49681fa9…`, 자기 시험 `va_selftest.py` `c624c3d8…`, 분리 실행 `AV/run_py.ps1` `f3e39935…`.
  - 검증 도구(분석 도구·stage1 import 0): `v_common.py` `464492ba…`, `v_fzp.py` `9edffc0e…`, `v_metrics.py` `80aef6de…`, `v_local.py` `8a6cf68e…`, `v_control.py` `81458cb6…`, `v_compare.py` `b66be3c4…`, `v_chain.cmd` `142e7719…`.
- **자기 시험** (보충 34 §8.0-2; `--profile selftest` = V-A 자리에 J1 런; 고정 바이트로 마지막 재실행):
  - 분석 쪽 `va_selftest.py`: **223/223 참, ALL_OK**. J1_REPORT §3.1·§3.2·§3.3·§5·§7·§8.1 표 칸을 표 자릿수 반올림 안에서 다시 냄, J1 분석 JSON(`an_metrics`·`an_local`·`an_followup`·`an_control`)과 같음, 짝 B(= J1 − J1) 모두 0, B′ = J1R = A, 다시 한 스캔 = J1 스캔. 출력 `AV/selftest/out/va_selftest.json` `41425603…74c3`.
  - 검증 쪽 `v_chain.cmd selftest` → `v_compare.py`: **1332/1332 참, ALL_OK**(`AV/verify/selftest_out/v_compare.json` `5561f412…05cf2`). 검증 FZP 행렬·DESSPEED 기록이 J1 검증 출력과 배열까지 같음(3/3).
  - 그 밖 시험: 보고서 조립기 — 금지 낱말 exit 3, 모르는 표 exit 2, 머리 줄 없음 exit 5. `va` 프로필은 고정 목록에 없는 사본을 거부(exit 1).
  - 자기 시험 중 고친 것(고정 전): `va_control.py`(유지 영수증 필드 위치, "줄어든 T"를 있는 값끼리 비교), `va_metrics.py`(같은 뜻 한 줄), `va_selftest.py`(대조 쪽 열 번호·사건 줄 파싱). 계산 정의는 바꾸지 않았습니다.
- 시간: 자기 시험 Python은 모두 BELOW_NORMAL·`python -B`·`PYTHONHASHSEED=0`으로 하나씩(무거운 것은 WMI 분리). 짧은 JSON 대조·표 만들기는 이 세션에서 바로 돌렸습니다(보통 우선순위, §10-6).

## 4. 발사 전제 (5): 감시·건강·감시기 [실행]

- 고정 목록 `VA/launch/launch_pins.sha256` sha256 `fa5329c621b17cbab22219fa733cfffe720ca49651cd564600792dece8a53a9c`(8줄): `va_health.py` `723045c0…`, `va_monitor.py` `9f147967…`, `va_snap.py` `abb74b27…`, `pre_launch.ps1` `a2984ef5…`, `launch_va.ps1` `02d86e20…`, `dryrun_watcher.ps1` `0e12cfcb…`, 감시기 `RVA/k92va_s43_watcher.ps1` **`a465c5ed293847c557aae8e43be2c9e2339e3b3a1314cb52404a850f2b171ed3`**, 드라이런 요약 `DRYRUN_SUMMARY.txt` `ccc11d99…`.
- `va_health.py`: 보충 34 §6.4 H1–H16·T1·T2. H10은 데이터 전에 고정한 읽는 법대로 "WD 호출마다 1줄 = 2줄(러너 `START` 줄 앞 1, 뒤 1), 모두 hold, strict 0". 값 비교(5209.8, s, 1.0)는 메모리에서만 하고 내지 않습니다. 결정 파일은 5분 넘게 지난 것만 `REPVA/live/<런>/health/`로 복사해 읽고, 자라는 로그는 그 순간 사본(sha 같음 확인)을 읽습니다.
- `va_monitor.py`: 보충 34 §6.3 블라인드 감시(결정 T·개수, `exit=`·`wall_sec`, sim_sec, 유지·ERROR 줄 수와 첫 토큰, 영수증 형 이름, EXIT 줄, 파일 나이, cmd 생존, S-VA-7 멈춤 표시, VISSIM 수·창 제목). 목적값·녹색·Ω는 읽지 않습니다. `watch_sdmpc.py`는 쓰지 않습니다.
- 도구 시험(발사 전, J1 런으로): `va_health` J1 s31r T = 900 → J1과 V-A가 다른 항목(H11–H16)만 거짓, 나머지 참. 첫 판은 H10의 `START` 정규식이 WD의 `START … attempt=` 줄까지 잡아 거짓이었고, 러너 자기 줄만 잡게 고친 뒤 참(V-A 자료 0 상태). `va_monitor` J1 s41·s43 읽기와 cmd 생존 판정(PID + 생성 시각) 시험.
- **감시기 드라이런** (발사·실제 잠금·기록 0, RVA 쓰기 0, 앞뒤 감시기 sha 같음):

| 시험 | 입력 | 결과 |
|---|---|---|
| T1 | 실제 좌석, 두 대상 살아 있음 | WAIT(아직 끝난 런 없음) |
| T2 | s31 끝남(시험) + 좌석 1/1 | RECHECK 뒤 WOULD_LAUNCH `-AllowConcurrentDev` |
| T3 | 둘 다 끝남 + 0/0 | WOULD_LAUNCH 플래그 없음 |
| T4 | s41 끝남 + 3/1 | WAIT(좌석 부족) |
| T5 | 둘 다 끝남 + 1/1(외부 dev) | WAIT |
| T6 | 잠금 파일 있음 | EXIT(already launched) |
| T7 | `-DryRun` 없이 시험 입력 | REFUSED, exit 2 |
| T8 | 가짜 RunsRoot에 s41 `EXIT … code=0` 줄, cmd는 살아 있음 | 끝남 아님 → WAIT |
| T9 | STOP 파일 | exit 3 |
| T10 | 시간 한도 아주 짧게 | GIVE_UP, exit 4 |
| T11 | s31 cmd 죽음 + EXIT 줄 없음 | ABNORMAL_NO_EXIT_LINE 표시, WAIT |
| T12 | T11 + s41 끝남 | S-VA-7 → WAIT(발사 안 함) |

## 5. 시드별 사전점검 ×3 (과제 1단계) [실행]

- 명령: FRZ_K92에서 `-Freeze` 없이 `run_sdmpc_n31.ps1 -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 -Name sdmpc31_v3c3_k92va_s<S>`, WMI·BelowNormal·`PYTHONHASHSEED=0`, 하나씩(`VA/launch/pre_launch.ps1` = 관문 `gh5_launch.ps1` 꼴). 판정 = 관문 고정 판정기 `VA/gates/gh5_check.py`(`29324dc6…`, `gcommon.py` `9f59ae2d…`, `va_gates_pins` 값과 같음).

| 시드 | cmd PID | FREEZE_VERIFIED | plan | provenance run_id | 조건 1–7 | 조건 8 (런 이름 폴더 없음) |
|---|---|---|---|---|---|---|
| 31 | 20944 | `011f5be2…`, head `c20aff1d…` | `785cdc10…`, 튜닝 `c8e3ee2c…`, warnings [] | `4a629867…` | 참 12/12 | 참 |
| 41 | 25820 | 같음 | `2412e534…` | `54fc6584…` | 참 12/12 | 참 |
| 43 | 16600 | 같음 | `44bd9443…` | `51b85259…` | 참 12/12 | 참 |

- 세 출력 모두 `PREFLIGHT_ONLY done; no VISSIM started`, `EXIT … code=0`, WD 정책 줄 1, REFUSED 0. 생긴 것은 `RVA/_preflight` 새 폴더 셋뿐입니다. → **사전점검 통과.**

## 6. 좌석과 발사 (과제 2–4단계) [실행·읽음]

- 좌석 규칙 [읽음 `run_sdmpc_n31.ps1:84-86`]: 플래그 없음 = PC 전체 VISSIM ≤ 3이고 dev 0. `-AllowConcurrentDev` = 총 ≤ 2이고 dev ≤ 1. 러너가 플랜 전과 VISSIM 직전에 두 번 셉니다. PC 전체 상한 4.
- 발사 줄 = 보충 34 §6.1 글자 그대로, `CurrentDirectory` = FRZ_K92, 우선순위 인자 없음(J1과 같음). WMI가 돌려준 프로세스의 CommandLine이 보낸 명령과 같음을 확인했습니다.
- **v3c3-s31** (플래그 없음): 직전 VISSIM 0·dev 0. 12:34:21.538 RV 0, cmd PID 19740(생성 12:34:21.661203). 러너: `SEAT total=0 dev=0 ok=True`, `FREEZE_VERIFIED … sha256=011f5be2… files=10569 head=c20aff1d…`, plan `1c3a0bb5…`, `NETWORK_COPY_OK … 3de889f0…`, `PREFLIGHT PROVENANCE_OK run_id=cfec4ccc… freeze=011f5be2…`, 재검사 `SEAT … ok=True`, `START` 12:34:41, WD `NoGlobalKill`·`KILL_POLICY … pid_only runner_pid=18112`. VISSIM PID 22724(창 제목 `sdmpc31_sdmpc31_v3c3_k92va_s31.inpx - PTV Vissim 2020 (SP 14)`). 런로그 `RUN_MODE=CONTINUOUS_EVENT_OBS150 controller=wu-link warmup_controller=no-control control_start_sec=900`, `NATIVE_SIM_PROGRESS sim_sec=1`.
- **v3c3-s41** (`-AllowConcurrentDev`): s31의 VISSIM 창 제목이 보이고 시뮬레이션이 시작된 뒤. 직전 VISSIM 1·dev 1. 12:36:17.105 RV 0, cmd PID 18580(생성 12:36:17.261976). 러너: 앞검사 `SEAT total=1 dev=1 ok=True allow_concurrent_dev=True`, plan `180850b4…`, `PROVENANCE_OK run_id=4dc4f9ca…`, 재검사 `SEAT total=1 dev=1 ok=True`, `START` 12:36:37, WD `KILL_POLICY … pid_only runner_pid=24848`. VISSIM PID 27572(창 제목 `…k92va_s41.inpx`), `NATIVE_SIM_PROGRESS sim_sec=1`.
- 발사 뒤 PC 전체 VISSIM 2(≤ 4). 5개 이상인 적 없음.
- 발사 기록 `RVA/wmi_launch_lines.txt`(2행, sha256 `192526cf…`; 같은 두 줄이 `VA/launch/wmi_launch_lines.txt`에도):

```
2026-10-23T12:34:21.5383743+09:00  k92va_s31  RV=0 PID=19740 VISSIM_before=0 dev_before=0 cwd=D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833 head=c20aff1d flag=none | cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_k92va_s31 -SimPeriod 9000 -Seed 31 -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 > D:\VISSIM_runs\20261023_sdmpc31_k92\wmi_sdmpc31_v3c3_k92va_s31.log 2>&1
2026-10-23T12:36:17.1045080+09:00  k92va_s41  RV=0 PID=18580 VISSIM_before=1 dev_before=1 cwd=D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833 head=c20aff1d flag=-AllowConcurrentDev | cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_k92va_s41 -SimPeriod 9000 -Seed 41 -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 -AllowConcurrentDev > D:\VISSIM_runs\20261023_sdmpc31_k92\wmi_sdmpc31_v3c3_k92va_s41.log 2>&1
```

## 7. s43 감시기 (과제 5단계) [실행]

- 파일 `RVA/k92va_s43_watcher.ps1`(sha256 `a465c5ed…71ed3`, ASCII, 구문 오류 0). 대상 파일 `RVA/k92va_s43_watcher_targets.json`(`c8dad3d6…`): s31 cmd 19740 생성 12:34:21.661203, s41 cmd 18580 생성 12:36:17.261976(VA/launch/launch_s31·s41.json에서 옮김). 감시기는 대상 이름이 기록 파일에 같은 PID로 있는지 처음에 확인합니다(`TARGET … record=OK` 두 줄).
- 규칙(J1 `j1_s43_watcher.ps1` `d388f498…` 규칙에 이름·PID를 바꿈):

| 항목 | 내용 |
|---|---|
| 끝남 판정 | 러너 자기 로그 `RVA/<런>/launch_<런>.log`에 `EXIT <런> code=N` 줄이 있고 **그리고** 발사 cmd PID(생성 시각까지 맞는 것)가 없을 때 |
| 좌석·플래그 | V-A 하나가 아직 돌면 `-AllowConcurrentDev`(총 ≤ 2, 1 ≤ dev ≤ 1). 하나도 안 돌면 플래그 없이(총 ≤ 3, dev 0). 그 밖은 기다림 |
| 발사 전 | 20 s 간격 두 번 맞아야 발사. 발사 줄 = §6.1 줄(s43, 플래그는 위 규칙) |
| 두 번 발사 막기 | `k92va_s43_watcher.lock`을 `CreateNew`로 먼저 만듦. 잠금·기록 파일의 s43 줄·s43 런 폴더 중 하나라도 있으면 발사 없이 끝냄 |
| 발사 뒤 | 기록 두 곳(RVA, VA/launch)에 J1 꼴 한 줄(`by=k92va_s43_watcher.ps1(pid …)`), `VA/launch/launch_s43.json`, 5분 동안 s43 러너의 SEAT/START/REFUSED/EXIT 줄 옮겨 적기, PC 전체 VISSIM ≥ 5면 질문 지점 표시(끄지 않음) |
| 멈춤 | `RVA/STOP_K92VA_S43` 파일이 있으면 발사 없이 끝냄. C: < 8 GB 또는 D: < 30 GB면 기다림. 36 h(2026-10-25 00:38께) 지나면 `GIVE_UP` |
| 비정상 끝 | EXIT 줄 없이 cmd가 없어진 런은 끝남이 아님(`ABNORMAL_NO_EXIT_LINE`). 그런 런이 있고 도는 런이 없으면 발사하지 않고 기다림(S-VA-7, §10-3) |
| kill | 없음. 어떤 프로세스도 멈추거나 죽이는 코드가 없음 |

- 시작: 12:38:25 WMI RV 0, cmd PID 24564 → powershell PID 8084, cwd RVA. 기록 `RVA/k92va_s43_watcher_launch.txt`(`0ee47e6a…`). 로그 `RVA/k92va_s43_watcher.log`. POLL 1(12:38:26)–8(12:59:29) 모두 `WAIT reason=no watched V-A run finished yet`, 좌석 총 2·dev 2(두 V-A VISSIM 창 제목이 읽힘), C: 39.5 GB·D: 365.6 GB.
- s43 발사 예상 [추론]: T = 900 결정이 약 580 s였으므로(J1과 비슷), s31·s41은 약 8.5–9.5 h 뒤(2026-10-23 21–22시께) 끝나고, 그때 감시기가 s43을 띄울 것으로 봅니다.

## 8. 건강 점검: 첫 SDMPC 결정 T = 900 (과제 6단계) [실행 `VA/launch/va_health.py`, 읽기만]

- T = 900 결정 파일이 5분 넘게 지난 뒤 `REPVA/live/<런>/health/T000900_<시각>/`로 복사해 사본만 읽었습니다(s31 12:58:39, s41 12:59:4x). 결과 `VA/launch/health_s31_T900.json`(`2f80fab6…`), `health_s41_T900.json`(`dfc89a2b…`).

| # | 항목 (보충 34 §6.4) | v3c3-s31 | v3c3-s41 |
|---|---|---|---|
| H1 | `action_000900.json`·`.csv`·`.json.applied` 있음 | 참 (58,252,638 B · 28,033 B · 248 B) | 참 (58,245,448 B · 28,163 B · 248 B) |
| H2 | `metadata.sdmpc_active` 참 | 참 | 참 |
| H3 | `stopline_approach_install_check` 있음·`passed` 참 | 참 | 참 |
| H4 | S6 캡처 `.stdout.txt`·`.stderr.txt` | 참 (325 B · 406 B) | 참 (325 B · 406 B) |
| H5 | `*.error.txt` 0 | 참 | 참 |
| H6 | `DECISION_FAILED` 0 (runlog·`.err`·launch·wmi·stdout·stderr) | 참 (모두 0) | 참 (모두 0) |
| H7 | 예산 `unlimited_time`·`expired_stage`·`output_completed` = 참·null·참 | 참 | 참 |
| H8 | 결정 수(T = 1 … 900) 7 | 참 (1, 150, …, 900) | 참 |
| H9 | 런로그 `DECISION_ERROR_POLICY=hold_previous_on_exception` 1줄 | 참 | 참 |
| H10 | launch 로그 WD 정책 줄: WD 호출마다 1줄 = 2줄(START 앞 1·뒤 1), 모두 hold, strict 0 | 참 (2줄, 1·1, strict 0) | 참 (2줄, 1·1, strict 0) |
| H11 | `FREEZE_VERIFIED … head=c20aff1d…` 1줄, sha = FRZ_K92 | 참 | 참 |
| H12 | `PROVENANCE_OK … freeze=011f5be2…` 1줄(사전점검 줄) | 참 | 참 |
| H13 | 런 provenance 튜닝 sha `c8e3ee2c…` | 참 (실행·사전 둘 다; 튜닝 sha 4회·망 1회·freeze 1회, env 정책 hold, FAIL_FAST 1, seed 31) | 참 (같음, seed 41) |
| H14 | T = 1 metadata: `k92_w`(`after` repr `5209.8`)·`k92_hb` 있음, `head_discharge_floor_173_p4_*` 정확히 1개·repr `1045.1612903225805`, `k92_hb_seed_binding` = 1.0 | 참 (키 `…_0d58a14f910af049`) | 참 (키 `…_d53f3bddee47d38c`) |
| H15 | T = 150 `head_observation_prior_discarded` = 1.0 | 참 | 참 |
| H16 | T = 900 `k92_w`·`k92_hb` 있음, 하한 키 이름 = H14 이름 | 참 | 참 |
| T1 | T = 900 `exit=0` | 참 (wall_sec 581.17) | 참 (wall_sec 579.3) |
| T2 | 유지·오류 없음 | 참 (영수증·hold_error·유지 줄·`ERROR=` 0) | 참 |

- 예열 결정 T = 1 … 750도 모두 `exit=0`이고 wall_sec 18.9–23.0 s(s31)·19.0–22.1 s(s41)입니다. `metadata.controller_status` = `ok`, 유지 메타 없음.
- 하한 키 이름은 런마다 다릅니다(`0d58a14f…`, `d53f3bdd…`; R-obs3 v3c3-s31 기록 이름 `e36d6761…`, V-B VB-41w `301ceabb…`와도 다름). H14는 이름의 개수만 보므로 판정에 영향이 없습니다. 이름의 해시16이 무엇에서 오는지는 이번에 보지 않았습니다 [추론: 런 고유 값에서 옴].
- → **s31·s41 둘 다 건강.** 보충 34 §7.2 S-VA-3 해당 없음.

## 9. FRZ_K92·주변 읽기 전용 확인 [실행 `VA/launch/va_snap.py`]

| 시점 | 캐시 밖 파일 / digest | 캐시 파일 | FREEZE.json | FRZ_K8b FREEZE.json | frozen/ | GWT8 HEAD / status |
|---|---|---|---|---|---|---|
| snap_00 사전점검 전 (12:31) | 10,570 / `aa4b6c83…` | 0 | `011f5be2…` | `6143d3eb…` | 36 | `c20aff1d` / 0줄 |
| snap_01 사전점검 뒤 (12:34) | 같음 | 0 | 같음 | 같음 | 36 | 같음 |
| snap_02 발사·건강 점검 뒤 (13:00) | 같음 | **229** | 같음 | 같음 | 36 | 같음 |

- 바뀐 것은 캐시 229파일(`__pycache__` 139, `__tangentcache__` 90)뿐이고, 생성 시각 12:34:44–12:52:39는 두 런의 `START` 뒤입니다. 동결 도구가 일부러 빼는 폴더이고 J1 때와 같은 수입니다(J1_LAUNCH §7). 보충 34 S-VA-5대로 보고만 합니다. 지우거나 옮기지 않았습니다.
- 캐시 밖에서 `FREEZE.json`보다 새 파일 0.

## 10. 공개

1. **발사 전제 (4)·(5)를 이 단계가 만들었습니다**(§3·§4). 보충 34가 "첫 발사 전"으로 정했고, 이 워크플로의 앞 단계에는 그 일이 없었습니다. 모두 V-A 자료 0 상태에서 만들고 시험하고 고정했습니다.
2. **도구 파일이 보충 34가 이름 붙인 것보다 많습니다**: `va_common.py`, `va_selftest.py`, `run_py.ps1`, `v_compare.py`, `v_chain.cmd`, `va_snap.py`, `pre_launch.ps1`, `launch_va.ps1`, `dryrun_watcher.ps1`. 모두 고정 목록에 있습니다. 분석 도구 여덟의 이름은 그대로입니다.
3. **감시기가 J1 감시기와 다른 곳**(이름·PID 밖): (가) 대상 PID를 스크립트에 박지 않고 발사 뒤 쓴 대상 파일에서 읽음(감시기를 발사 전에 고정해야 해서), 대상 파일과 기록 줄의 PID 맞춤 확인, (나) EXIT 줄 없이 끝난 런이 있으면 다른 런이 끝나도 s43을 띄우지 않고 기다림(S-VA-7은 STOP이므로; J1 감시기는 이 경우 플래그 없이 띄웠을 것), (다) 기록 줄을 `VA/launch/wmi_launch_lines.txt`에도 쓰고 `launch_s43.json`을 남김(보충 34 §6.1 "같은 줄을 VA/launch에도"), (라) 발사 뒤 PC 전체 VISSIM ≥ 5이면 질문 지점 표시. 모두 더 보수적인 쪽입니다.
4. **감시기 시작 기록 줄 결함**: 시작에 쓴 내 PowerShell 명령에서 RunsRoot 변수 `$R`이 `$r = Invoke-CimMethod …`로 덮였습니다(PowerShell 변수 이름은 대소문자를 가리지 않음). WMI 호출은 덮이기 전 값으로 이미 끝나 cwd = RVA로 맞게 떴습니다 [실행: CommandLine, 자식 powershell 8084, 감시기 로그 정상]. 그러나 `VA/launch/watcher_launch.txt` 첫 줄의 cwd 칸이 객체 글로 찍혔고 RVA 쪽 기록 파일 쓰기는 경로 오류로 실패했습니다. 고친 줄을 `RVA/k92va_s43_watcher_launch.txt`에 새로 쓰고, `VA/launch/watcher_launch.txt`에는 옛 줄 아래 정정 줄을 덧붙였습니다(옛 줄은 지우지 않음). 다른 곳에 생긴 파일은 없습니다(그 경로 없음 확인). 런 발사 스크립트 `launch_va.ps1`·`pre_launch.ps1`·감시기에는 이 겹침이 없습니다(변수 이름 확인).
5. **건강 도구 H10 정규식을 발사 전에 고침**: J1 런 시험에서 WD의 `START … attempt=` 줄까지 잡는 것을 보고, 러너 자기 `START <런> out_dir=` 줄만 잡게 고쳤습니다. 선언 글(WD 호출마다 1줄 = 2줄)은 그대로입니다. V-A 자료 전입니다.
6. **가벼운 Python을 보통 우선순위로 돌림**: JSON 대조(`va_selftest`·`v_compare`)·표 만들기·건강 점검·감시·스냅숏·사전점검 판정기는 이 세션에서 바로 돌렸습니다(각 수 초–1분, 한 번에 하나). 무거운 것(스캔·FZP·결정 JSON 다량 읽기·검증 묶음)은 BELOW_NORMAL·WMI 분리였습니다.
7. **발사 전 `va` 프로필 한 번**: 고정 확인 시험으로 `va_metrics.py --profile va`를 돌렸고, V-A 스캔이 없어 멈췄습니다(V-A 자료 없음, 빈 `AV/out`·`AV/scans` 폴더만 생김).
8. **도구 시험 사본**: J1 런 파일 사본이 `REPVA/tooltest_live/`에 생겼습니다(J1 s31r 결정 JSON 3개·로그). 읽기 전용 시험용이고 런 폴더에는 쓰지 않았습니다.
9. **로그 읽기**: 런로그·launch 로그는 계속 자라므로 "5분 지난 파일" 조건을 걸 수 없어, 그 순간 사본(원본 sha = 사본 sha)을 읽었습니다(J1 재실행 선례 S31_RERUN_LAUNCH §7-3).
10. `.md` 보고서와 방법 문서는 `.txt`로 쓴 뒤 바이트 복사했습니다(subagent Write 도구 제한, J1 선례).

## 11. 이 단계에서 하지 않은 일

- 커밋·푸시·동결 0. GWT8·FRZ_K92(런이 쓴 캐시 말고)·FRZ_K8b·다른 `frozen/*` 쓰기 0.
- kill·stop 0(내가 띄운 것 포함). 이름으로 끄기 0. 내가 띄우지 않은 프로세스는 건드리지 않음(감시 도구의 생존 확인은 읽기만).
- VISSIM은 s31·s41 두 런만. s43은 감시기에 맡김. 재발사 0.
- V-A 성능 숫자(Ω·TTT·①–④·지연·목적값·녹색) 열람·계산 0. `watch_sdmpc.py` 사용 0. 분석 도구를 V-A 자료로 돌린 적 0.
- 금지 시험 7종·그 밖 시험 0. 봉인 시드(37/59/61/67) 자료·codex 64cf 숫자 0. v3c3-s47 자료 0.
- 판정 정의·문턱·관문 판정기 변경 0. 보충 34 수정 0.

## 12. 다음 (사용자·메인 세션)

1. 감시: `VA/launch/va_monitor.py`로 9분 이하 간격(보충 34 §6.3). 첫 유지가 나면 곧바로 보고(S-VA-6). WD가 끝내지 못하는 멈춤(4,800 s 무진행·EXIT 없음·cmd 살아 있음)은 S-VA-7 STOP.
2. s31 또는 s41이 끝나면 감시기가 s43을 띄웁니다. `RVA/k92va_s43_watcher.log`의 `LAUNCHED`·`S43_RUNNER` 줄과 `RVA/wmi_launch_lines.txt` 3행째로 확인하고, s43의 T = 900 건강 점검(`va_health.py 43 900 …`)을 합니다.
3. 세 런이 끝나면 유효성(보충 34 §7.1 개정 J1-A·H-A, `VA/validity/va_j1a.py`는 첫 계산 전 고정) → 보고 머리 → 분석(`ANALYSIS_METHOD_VA.md`, 고정 도구, `--profile va`) → 독립 검증(`v_chain.cmd va`).
4. 감시기를 멈추려면 `RVA/STOP_K92VA_S43` 파일을 만들면 됩니다(다음 폴, 3분 안). kill은 필요 없습니다.

## 13. 파일 (sha256 앞 16자) [실행]

- `VA/launch/`: `pre_k92va_s31.out` `40ceff6a…`, `pre_k92va_s41.out` `94edcddf…`, `pre_k92va_s43.out` `e5666905…`, `pre_check_s31.json` `b22fcb6e…`, `pre_check_s41.json` `cb47938a…`, `pre_check_s43.json` `57659edc…`, `wmi_preflight_lines.txt` `09541473…`, `launch_s31.json` `274a31aa…`, `launch_s41.json` `879c1965…`, `wmi_launch_lines.txt` `192526cf…`, `watcher_launch.txt` `454a43fd…`, `health_s31_T900.json` `2f80fab6…`, `health_s41_T900.json` `dfc89a2b…`, `snap_00_before_preflight.json` `f1e7c691…`(= `snap_01`), `snap_02_after_launch_health.json` `947c37c3…`, `launch_pins.sha256` `fa5329c6…`, `dryrun/DRYRUN_SUMMARY.txt` `ccc11d99…`, 감시 출력 `monitor/mon_*.json`.
- `VA/analysis/`: `va_analysis_pins.sha256` `39a97e7f…`, `ANALYSIS_METHOD_VA.md` `72b004f6…`, 자기 시험 출력 `selftest/out/va_selftest.json` `41425603…`, `verify/selftest_out/v_compare.json` `5561f412…`.
- RVA: `wmi_launch_lines.txt` `192526cf…`(2행 시점), `k92va_s43_watcher.ps1` `a465c5ed…`, `k92va_s43_watcher_targets.json` `c8dad3d6…`, `k92va_s43_watcher_launch.txt` `0ee47e6a…`, `k92va_s43_watcher.log`(계속 자람).
- REPVA 사본: `REPVA/launch/`(이 문서 `VA_LAUNCH.md` + `VA/launch/` 파일 + RVA 기록·감시기 파일, `SHA256SUMS_LAUNCH.txt`), `REPVA/analysis_tools/`(방법 문서·고정 목록·도구·자기 시험 출력, `SHA256SUMS_ANALYSIS_TOOLS.txt`).
