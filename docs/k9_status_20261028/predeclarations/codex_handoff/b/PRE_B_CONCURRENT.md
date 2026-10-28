# PRE_B_CONCURRENT — B 런을 동시에 띄우려고 바꾼 것 (D-K9-90) · 첫 B 발사 전 고정 (2026-10-26 14:18 KST)

- 이 문서는 **첫 B 런을 띄우기 전에** 씁니다. sha256 을 `SP/codex_handoff/LOG.md` 에 적어 고정합니다. B 데이터가 생긴 뒤에는 고치지 않습니다. 쓰인 대로 할 수 없으면 고치지 않고 멈추고 보고합니다.
- 판정 낱말은 쓰지 않습니다. Ω 는 늘 ④ 와 Ω 밖과 같은 표에 둡니다(COMPARE_RULE_B 그대로). 시드는 망 이름을 붙여 v3c3-s31·s41·s43 으로 적습니다.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CW = `SP/codex_handoff/work`.
- 근거: 사용자 결정 D-K9-90 (`SP/K9_1_J1_NOTES_20261013.md` sha `59e41ff5…` :296-301), D-K9-88·89 (:293-294), PRE_B `SP/codex_handoff/b0/PRE_B.md`(`3149cfe5…`) §1·§2·§5, 관문 1 `SP/codex_handoff/b/GATE1.md`(`aae6b0ca…`), B1 준비 요약 `CW/b1/b1_summary.json`(`89040b1a…`).

## 0. 줄임말 (처음 한 번)

- B = codex 판(a49981ff)을 우리 v3c3 망으로 옮긴 폐루프 런. NC3 = 같은 시드 v3c3 무제어 런. V-A = 우리 묶음 B1 폐루프 런.
- 러너 = codex 폐루프 실행 스크립트 `run_closedloop3000.ps1`. 워치독 = 러너가 띄우는 감시 스크립트 `run_real_world_single_watchdog_distributed_core17legs4b.ps1`.
- StallSec = 워치독이 "진행 신호가 이만큼 없으면 이 런을 끈다" 고 보는 초.
- FRZ = 동결 트리(발사용 코드 사본, FREEZE.json 에 파일마다 sha256). FRZ_B0 = 관문 1 까지 쓴 트리, FRZ_B1 = 이번에 만든 트리.
- 자리(seat) = 이 PC 에서 동시에 열 수 있는 VISSIM 하나. 이 PC 상한은 4개(5번째는 COM 생성 거부) [읽음 메모리 vissim-single-instance-license].
- 발사기(launcher) = 세션과 떨어져 도는 스크립트. B 런 셋을 자리가 날 때 띄웁니다(다음 단계에서 씀).

## 1. 무엇을 바꿨나 [실행]

러너 **한 파일**의 **두 곳**만 바꿨습니다. 제어기 코드·설정·망·워치독·VBS·래퍼 환경은 그대로입니다.

| | FRZ_B0 | FRZ_B1 |
|---|---|---|
| 경로 | `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258` | `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410` |
| FREEZE.json sha256 | `853d1c4fb97ed3de4cf62a409b06b9001648ce56171e2ed826236bdddb1506c6` | `558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1` |
| 파일 수 / 바이트 | 7,989 / 495,607,788 | 7,989 / 495,607,946 (+158 B) |
| git head · status 줄 · status sha | a49981ff · 3,653 · `558ddef8…` | 같음 |
| 러너 sha256 · 줄 수 | `8b2da855…` · 194 | `6ff68b385a4bf6dab23a26bea5a6015641a77808230bfc8366bbc5d2554b38f7` · 195 |

바꾼 곳(FRZ_B1 러너 줄 번호) [실행 `CW/b1/runner_b0_to_b1.diff` `ae599d8b…`]:

```diff
-          '-NoGlobalKill','-MaxAttempts','1','-StartupStallSec','300','-StallSec','2400')
+          '-NoGlobalKill','-MaxAttempts','1','-StartupStallSec','300','-StallSec','3600')
         if ($PreflightOnly) { $arguments+='-PreflightOnly' }
         else {
             $live=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'})
             # The cscript may exit just before its COM server closes. Only wait;
             # never close another process or replay a completed simulation.
-            for($wait=0; $live.Count -and $wait -lt 30; $wait++) {
+            # D-K9-90 (2026-10-26): launch while the PC-wide VISSIM count is below the 4-seat cap; wait/refuse at 4 or more.
+            for($wait=0; $live.Count -ge 4 -and $wait -lt 30; $wait++) {
                 if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) {throw 'STOP exists; no next run'}
                 Start-Sleep -Seconds 1
                 $live=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'})
             }
-            if($live.Count) {throw 'Another VISSIM is open; preserve it and do not launch'}
+            if($live.Count -ge 4) {throw 'PC-wide VISSIM count is at the 4-seat cap; preserve them and do not launch'}
```

1. **발사 전 VISSIM 검사** (FRZ_B1 러너 :169-180, FRZ_B0 :169-179). 전에는 VISSIM 이 하나라도 있으면 30 s 기다린 뒤 거부했습니다. 이제는 PC 전체 VISSIM 수가 4 미만이면 띄우고, 4 이상이면 30 s 기다린 뒤 거부합니다. 세는 법(이름이 `Vissim` 으로 시작하는 모든 프로세스, 남의 것 포함)은 그대로입니다. 사전 점검(`-PreflightOnly`)은 이 검사를 건너뜁니다(:168).
2. **StallSec** (:167). 워치독 인자 2,400 → 3,600.

확인 [실행, `CW/b1/b1_summary.json` 의 tree_checks 13개 모두 true]:

- 새 원천 `b1/source` = 새 git 저장소(커밋·브랜치 없음)에 FRZ_B0 의 원천 `b0/source` HEAD(a49981ff)를 fetch·detached + `b0/source` robocopy. 고치기 전 파일표가 FRZ_B0 FREEZE.json 과 **0 차이**(7,989 / 7,989, `diff_src_preedit_vs_frzb0.json` `eb7da08b…`).
- 고친 뒤 원천 대 FRZ_B0: 바뀜 1(러너), 빠짐 0, 더함 0 (`diff_src_postedit_vs_frzb0.json` `7b7c9db7…`).
- 동결: codex `tools/sdmpc31/freeze_worktree.ps1`(sha `2f8ff1ea…`, FRZ_B0 의 것과 같은 바이트) → **FREEZE_OK**, 122.2 s. FRZ_B1 FREEZE.json 대 FRZ_B0 FREEZE.json: 바뀜 1(러너), 빠짐 0, 더함 0 (`diff_frzb1_vs_frzb0.json` `c4672774…`). FREEZE_VERIFIED 사전 점검 앞·뒤 두 번. FRZ_B0 도 그 뒤 FREEZE_VERIFIED(`853d1c4f…`).
- 좌석 검사 흉내 시험(VISSIM 없음, Get-CimInstance 를 가짜 VISSIM N 개로 바꿈, `seat_test_b1.json` `6d5c21a1…`): N = 0·1·2·3 띄움, N = 4·5·6 거부. 같은 시험에서 FRZ_B0 러너는 N = 0 만 띄움.

사전 점검(`-PreflightOnly`, VISSIM 0) [실행, 시드마다 검사 16개 모두 true]:

| 시드 | 러너 종료 | 벽시계 | provenance sha256 | FREEZE_VERIFIED / freeze 핀 | 망 sha | 유지 env | StallSec (워치독 명령줄 · 러너 상태 인자) |
|---|---|---|---|---|---|---|---|
| v3c3-s31 | 0 | 17.5 s | `0d3ec1c35612f2204b746ec10828fabf4d2010cbdf7741b57e482556b8bac227` | FRZ_B1 `558de2c1…` | `3de889f0…` | hold_previous_on_exception · 1 · 0 | 3600 · 3600 |
| v3c3-s41 | 0 | 14.8 s | `86ae6e5d468029c44c9873f43517f5433fe5eb96a0fe72e08141cec1f54006b8` | 같음 | 같음 | 같음 | 3600 · 3600 |
| v3c3-s43 | 0 | 14.2 s | `d8e6ea3fb078371e4dd0f887795049a725135bbe07ed92bc21788c17802cc7dc` | 같음 | 같음 | 같음 | 3600 · 3600 |

- 그 밖 핀: 설정 `729640af…`, plant manifest `11842498…`, 검지표 294행 `108debbb…`, 제어기 wu-link, SIM 9,000 s, 작업 뿌리 = FRZ_B1, 빈 RW_* 값 없음(RW_OBS150_GT 만 허용) [실행].
- provenance 를 관문 1(FRZ_B0) 같은 시드 사전 점검과 잎 단위로 견줌(트리·결과 뿌리 경로를 같은 글로 바꾼 뒤): 다른 잎은 셋 모두 `created_at`·`run_id`·`observation/freeze/sha256`(853d1c4f → 558de2c1) 뿐, 한쪽에만 있는 잎 0 [실행].
- StallSec 은 provenance JSON 에 칸이 없습니다(워치독은 `startup_stall_sec` 만 적음, 워치독 :808-832) [읽음]. 그래서 사전 점검 동안 (가) 러너가 띄운 워치독 자식 프로세스의 명령줄과 (나) 러너 상태 파일의 'preflight' 단계 `arguments` 를 기록해 3600 을 확인했습니다 [실행 `b1/runner_preflight/_wrapper/s<seed>/watchdog_cmdline.json`·`preflight_status_stage_preflight.json`].

## 2. 왜 바꿨나 (D-K9-90)

- D-K9-88 은 B 를 v3c3-s31 → s41 → s43 차례로 띄우게 했습니다. 러너는 다른 VISSIM 이 하나라도 열려 있으면 거부합니다(FRZ_B0 :170-178) [읽음]. 이 PC 에는 codex 가 따로 시킨 VISSIM 이 늘 돌았습니다(rolling_cea 1, TD3 학습 3; 사용자: "codex에서 따로 시킨 업무") [실행 LOG 13:30·13:55]. 그래서 s31 은 11:52 무렵부터 기다리기만 했고 한 번도 뜨지 못했습니다 [실행 LOG 11:58–13:55].
- 차례로 돌리면 런당 약 12–14 h, 셋에 약 36–41 h 에 대기까지 더해집니다(PRE_B §6) [추론].
- 사용자는 "자리 나면 세 시드 동시에" 를 골랐습니다. 바꾸는 것은 러너의 발사 전 검사와 StallSec 둘뿐입니다.
- StallSec 을 3,600 으로 올린 까닭 [추론]: 동시에 돌면 CPU 를 나눠 써서 결정이 느려질 수 있습니다. 관문 1 결정은 296–403 s 였고(다른 VISSIM 1–2개), 64cf 의 codex 코드 결정은 이 PC 에서 최대 1,042.5 s 였습니다(PRE_B §2-2). 느리지만 진행 중인 런을 워치독이 끄는 일을 줄이려는 것입니다. 이 PC 는 논리 코어 20개, RAM 127.6 GB(14:15 여유 100.4 GB) [실행].

## 3. 동시 실행이 바꿀 수 있는 것: 벽시계뿐

- 결정에는 벽시계 시한이 없습니다. 설정 `adapter/joint_owner_game/ignore_wall_time_limits = true` [실행 config_b0_v3c3.json `729640af…`]. 이것이 켜지면 후보 시간 예산·복원 예산·결정 마감이 꺼집니다(area_follower_objective.py:2363-2364, :2375-2380, :2386, :2396-2397) [읽음]. 관문 1 재생 넷의 decision_budget `unlimited_time` 은 모두 true 였습니다 [실행 `CW/gate1/gate1_summary_r2.json`].
- 유지(앞 명령 그대로 두기)는 파이썬 예외 때만 합니다. 시간 초과로는 하지 않습니다: 워치독이 `RW_DECISION_TIMEOUT_SEC=0` 을 세웁니다(워치독 :327-333) [읽음], 세 사전 점검 provenance 에 그대로 있습니다 [실행].
- 그래서 같은 시드·같은 코드·같은 설정이면 결정 결과는 기다린 시간과 상관없다고 봅니다 [추론]. 바뀔 수 있는 것은 결정 벽시계, 런 전체 벽시계, 진행 신호 간격입니다.
- 이 추론의 빈틈 [추론]: (1) 모든 코드 길에서 시각에 기대는 분기를 다 훑지는 않았습니다. (2) 자원 압박이 예외를 낳으면(예: 메모리, 프로세스 풀 깨짐) 결과가 달라질 수 있습니다. 이런 예외는 유지 대상이 아니면 런이 멈추고 §7 의 "이상 종료" 가 됩니다. (3) StallSec 은 "워치독이 끄는 때" 만 바꿉니다. 끝까지 돈 런의 결과에는 들어가지 않습니다.
- COMPARE_RULE_B §3-6 의 결정 벽시계 칸은 쓰인 그대로 냅니다. 그 칸은 동시 실행 아래 잰 값입니다. A1·관문 1 의 벽시계와 같은 조건이 아닙니다. 그 표의 "> 2,400 s(StallSec) 수" 칸은 글대로 문턱 2,400 s 를 씁니다(새 StallSec 은 3,600 s). 새 칸은 더하지 않습니다.

## 4. 그대로인 것

- **COMPARE_RULE_B.md** `f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c`, **PINS_B.sha256** `5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804` — 바꾸지 않습니다. 14:14 에 `sha256sum -c` 54줄 모두 OK [실행]. 분석 도구는 FRZ 경로를 쓰지 않습니다(work/rawcheck_b·omega_b·vhr_b 에 FRZ 경로 0건) [실행 grep].
- PRE_B §1 런 정의: 설정 `diagnostics/b0_v3c3/config_b0_v3c3.json`(`729640af…`), 망 `diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx`(`3de889f0…`) + `-Seed`, 9,000 s, 결정 150 s, 제어 시작 900 s, `-Arms sdmpc`, Python312, codex 런타임 pwsh 7.6.5, `-DependenciesPath D:/VISSIM-window264-deps`, env_hsw + PYTHONHASHSEED=0 + RW_* 지우기(래퍼), 우선순위 Normal, WMI 분리 발사. **바뀐 것은 둘**: `-FrozenTree` = FRZ_B1, 차례 → §5 의 동시 발사.
- 결과 뿌리: `D:/VISSIM_runs/20261026_codex_b_v3c3/s<seed>` (COMPARE_RULE_B §1 의 `s<s>/sdmpc`). 지금 없음 [실행 14:14].
- 짝·지표·적분 꼴·④b 첫 관측 차분 주 값·표 형식은 COMPARE_RULE_B 그대로입니다.
- 전 단계 발사 도구 `CW/b/b_launch_wmi.ps1`(`b88a51db…`)·`b_wrapper.ps1`(`43348294…`)는 FRZ_B0 를 가리키고 "VISSIM 0" 을 요구하므로 쓰지 않습니다. 발사기 단계에서 FRZ_B1 판을 새로 쓰고 첫 발사 전에 sha 를 LOG 에 적습니다.

## 5. 발사 정책

1. 발사기 하나가 세션과 떨어져 돕니다(WMI `Win32_Process.Create`). 세션이 꺼져도 계속 돕니다.
2. 띄우는 것: v3c3-s31, s41, s43 를 **한 번씩만**. 차례는 s31 → s41 → s43 (자리가 나는 대로). 우리 B 런은 동시에 최대 3개.
3. 각 B 런 = FRZ_B1 러너, PRE_B §1 인자, 결과 뿌리 `D:/VISSIM_runs/20261026_codex_b_v3c3/s<seed>`.
4. 기다림 상한: 발사기 시작부터 12 h 안에 자리를 못 얻은 시드는 띄우지 않고 멈추고 보고합니다(D-K9-88 의 12 h 를 그대로 씀).
5. 디스크: 띄우기 직전 C·D 각 8 GB 이상, D 는 8 GB × (아직 안 끝난 우리 런 수 + 이번 런) 이상. 모자라면 띄우지 않고 멈춤.
6. 어떤 B 런이든 **이상 종료**(§7)하면: 발사기는 남은 시드를 띄우지 않습니다. 작업 흐름은 까닭을 적고 STOP 합니다. 이미 도는 다른 B 런은 끄지 않습니다(그 런들을 쓸지는 사용자가 정함).
7. 남의 VISSIM(codex rolling_cea, codex TD3 학습 등)은 절대 건드리지 않습니다. 이름으로 끄지 않습니다. 끄는 것은 우리가 띄운 PID 뿐입니다(PID + 시작 시각으로 확인).

## 6. 자리 규칙

1. 셈: PC 전체에서 이름이 `Vissim` 으로 시작하는 프로세스 수(러너 :170 과 같은 셈, 우리 것 + 남의 것).
2. 잠금: 발사기는 잠금 파일(배타적으로 만듦)을 잡은 채로 (가) 셈 → (나) **수 < 4 일 때만** 래퍼를 띄움 → (다) 그 런의 VISSIM 이 보일 때까지(워치독 launch.log 의 `VISSIM_PROCESS` 줄, 또는 러너 종료, 또는 600 s) 기다린 뒤 잠금을 놓습니다. 그래서 우리 발사끼리는 같은 자리를 두고 겨루지 않습니다. 셈은 띄우기 **바로 직전**에 다시 합니다.
3. 둘째 관문: 러너 자신이 띄우기 직전에 다시 세고, 4 이상이면 30 s 기다린 뒤 거부합니다(FRZ_B1 :169-180).
4. 러너 거부(종료 1, 'at the 4-seat cap', 워치독·VISSIM 안 뜸, 런 로그 없음)는 **발사 시도 실패**이지 런이 아닙니다. 그 시드의 "한 번" 에 세지 않습니다. 기록하고 자리가 나면 같은 결과 뿌리에 다시 시도합니다. 러너는 런 로그가 없으면 같은 뿌리에서 다시 돕니다(:131-138 망 사본 재사용·sha 검사, :153 런 로그 있을 때만 거부) [읽음]. 래퍼의 "한 번만" 표지는 시도 번호를 따로 세게 발사기 단계에서 만듭니다.
5. 남는 위험 [추론]: codex 가 러너 검사 뒤, 우리 VISSIM 이 뜨기 전에 VISSIM 을 띄우면 5번째가 생길 수 있습니다. 그 사이는 A1 에서 러너 시작 → VISSIM 약 98 s 였습니다(LOG 01:18 항목) [실행 기록]. 5번째 COM 생성은 거부되므로, 그것이 우리 런이면 시작 실패 → §7 의 이상 종료(멈추고 보고), codex 런이면 우리가 끼친 일로 보고합니다. 우리는 이것을 막으려고 남의 것을 끄지 않습니다.

## 7. 이상 종료와 한 번 재발사 규칙

**이상 종료**(하나라도 맞으면; 재발사 없음, §5-6 적용):
- (가) 유지되지 않은 결정 실패, 제외 예외 8종(NOTES:47)으로 런이 멈춤.
- (나) 워치독이 뜬 뒤 러너/래퍼 종료 ≠ 0, native_status `failed`, 런 로그에 `STAGE=SIM_DONE` 없음, `SIM_SEC` ≠ 9000.
- (다) 워치독 자신의 `WATCHDOG_KILL`(진행 없음 > StallSec 3,600 s) 또는 `STARTUP_TIMEOUT`(300 s 안에 시뮬레이션 시작 못함), VISSIM COM 생성 실패.
- (라) 아래 재발사 뒤 그 시드가 다시 멈춤 또는 (가)–(다).
- 예외 유지(`DECISION_HELD_PREVIOUS`)는 설계된 동작입니다. 이상 종료가 아니며 T 와 예외 종류를 적습니다.

**한 번 재발사**(사용자 정책: 정상보다 5분 더 진행이 없으면 확인 뒤 그 런 PID 만 끄고 한 번 다시 띄우며 기록):
1. 정상 = 진행 신호 간격 최대 199 s (A1·관문 1 관측 최대 178.7 s 이상, `CW/b/b_normal_gaps.json` `0dd2b38c…`, 11:58 고정). 방아쇠 = 진행 신호가 **499 s** 넘게 없음. 진행 신호 목록은 LOG 11:58 항목 그대로(runlog·state CSV·action CSV·최신 action_*.json·최신 progress.jsonl·WATCHDOG_PROGRESS, 기동 중에는 발사 기록·launch.log).
2. 확인: 방아쇠가 당겨지면 그 런의 프로세스 나무(래퍼 → 러너 → 워치독 → cscript → 결정 python, + 워치독이 `VISSIM_PROCESS` 로 적은 VISSIM)의 CPU 시간 합을 120 s 동안 봅니다. 1 s 넘게 늘면 "느리지만 진행 중" 으로 적고 끄지 않습니다(다음 499 s 뒤 다시 봄). 동시 실행에서 간격이 길어질 수 있어서 이 확인을 둡니다.
3. 늘지 않으면 멈춘 것으로 봅니다: 그 런의 PID 만(PID + 시작 시각) 끕니다. 그 시드 결과 뿌리 `s<seed>` 를 지우지 않고 `s<seed>_try1_stalled` 로 이름만 바꿉니다. 같은 시드를 `s<seed>` 에 **한 번만** 다시 띄웁니다(COMPARE_RULE_B 경로 그대로). 자리 규칙(§6)을 똑같이 따릅니다. 모두 LOG 에 적습니다.
4. 이 재발사는 시드마다 한 번입니다. 다시 멈추거나 이상 종료하면 (라) 입니다.

## 8. 이 문서가 알려 주지 않는 것 [추론]

- 동시 실행 아래 결정 벽시계가 얼마나 늘지, 런이 언제 끝날지.
- §3 의 "결과는 벽시계와 무관" 을 B 런 자체로 시험하지는 않습니다(같은 시드를 차례 실행과 동시 실행으로 두 번 돌리지 않음).
- PRE_B §7·COMPARE_RULE_B §8 의 한계(64cf-s29 계수의 v3c3 적합성, 기구별 몫, 러너 차이)는 그대로입니다.
