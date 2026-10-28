# A1_LAUNCH — 64cf-s29 joint 8,100 s 재현 런 발사 기록 (2026-10-25 18:20 – 2026-10-26 01:40 KST)

- 무엇: PRE_A1 r2 §8 의 발사 전 점검 1–6 을 차례로 하고, A1 을 한 번 띄우고, 첫 SDMPC 결정(T=900)이 끝날 때까지 본 기록입니다.
- 근거 sha [실행]: NOTES `67dcc32b…`(D-K9-85·86·87), PRE_A1 r2 `2d9aa15a…`, A0B.md `7db91c0d…`. 시각별 기록은 `codex_handoff/LOG.md` 의 2026-10-25 18:20 – 2026-10-26 01:4x 항목입니다.
- 짝 개수: A1 은 한 런·한 시드(29)입니다. 비교 상대는 codex joint 한 런과 A0 의 env_hsw T=900 재생 하나입니다. 판정 낱말은 쓰지 않습니다.
- 태그: [실행] 이번에 돌려서 본 것, [읽음] 파일을 읽어서 안 것, [추론] 근거에서 미루어 본 것.

## 줄임말 (처음 한 번)

- A0 / A0b / A1: VISSIM 없는 결정 재생(3결정) / 기록 결정 1,050–2,550 재생 / VISSIM 재현 런.
- FRZ: A1 동결 트리 `D:/VISSIM_runtime/20261025_codex_a1/frozen/sdmpc31_a49981ff_202610251820`.
- W: FRZ 를 만든 원천 트리 `D:/VISSIM_runtime/20261025_codex_a1/source`.
- RES: 결과 뿌리 `D:/VISSIM_runs/20261025_codex_a1_s29`.
- env_hsw: OpenBLAS·numpy·numba 를 AVX2(Haswell) 경로로 묶는 변수 셋(PRE_A1 U1 (b)).
- R1 / R2 / R3: 명령 CSV 바이트 sha / `joint_written.json` 다섯 칸 / 채점 토큰(A0-CMP-1).
- WMI: Windows 관리 도구의 `Win32_Process.Create`. 띄운 프로세스가 이 세션과 떨어져 돕니다.

---

## 0. 쉬운 답

1. [실행] A1 은 2026-10-26 01:17:48 KST 에 WMI 로 한 번 떴고(ReturnValue 0, 래퍼 PID 34448), 지금 돕니다. VISSIM PID 40024, cscript PID 48380.
2. [실행] 첫 SDMPC 결정 T=900 은 종료 0 으로 끝났습니다. 벽시계 400.74 s(runlog), decision_budget 399.72 s 입니다. codex 는 229.39 s / 228.81 s 라 배수는 1.75 입니다.
3. [실행] T=900 명령은 codex 기록과 A0 env_hsw 재생 둘 다와 바이트까지 같습니다(R1 같음, CSV sha `5be7a91b…`, 213행 중 다른 행 0). R2 다섯 칸도 둘 다와 같습니다. R3 채점 토큰은 셋이 서로 다릅니다(A0 에서도 그랬음).
4. [실행] 무제어 준비 결정 T = 1, 150, …, 750 의 명령 CSV 도 codex 와 6/6 같습니다.
5. [실행] 01:40 에 T=1050 결정이 진행 중입니다(진행 기록 28줄, 마지막 쓰기 7 s 전). 그래서 "T=900 을 지나 돌고 있음" 입니다.
6. 바꾼 절차 둘(아래 §1·§2): 동결 도구가 git 원천을 요구해서 원천 W 를 git 으로 만들었고, pwsh 7 에서 변수 지우기가 빈 값을 남겨 래퍼를 한 번 고쳤습니다. 코드·설정 바이트는 바꾸지 않았습니다.
7. 기다림: 다른 세션 VISSIM(PID 29028)이 끝나기를 6 h 44 m 기다렸습니다(18:33 – 01:17). 건드리지 않았습니다.

---

## 1. 동결 트리 (점검 1)

### 1.1 왜 원천 W 를 따로 만들었나 [읽음·실행]

- `freeze_manifest.py build <W> <FRZ> <git-state>` 는 W 의 git 상태를 build 앞뒤로 비교합니다(freeze_manifest.py:101-109, 126-132). W 가 git 작업 트리가 아니면 build 가 멈춥니다.
- A0 코드 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code` 는 git 저장소가 아닙니다(`git rev-parse` 128) [실행].
- 그래서 같은 바이트를 담은 git 원천 W 를 새로 만들었습니다. 도구는 바꾸지 않았습니다.

### 1.2 W 만들기 [실행]

1. `git init` 빈 저장소(커밋·브랜치 만들지 않음).
2. 인계 사본 저장소 `D:/VISSIM_handoff/20261024/code`(읽기만)에서 `codex/handoff-rmtsc-20261024` 를 fetch. FETCH_HEAD = `a49981ffb258707c9a5e837d56f8cad829dab0ac`.
3. detached checkout. 4,343 파일. `core.autocrlf false`, 인계 `.gitattributes` 가 `* -text` 라 줄끝 변환 없음.
4. A0 코드 트리를 robocopy. 뺀 것: `__pycache__`·`__tangentcache__`·`.pytest_cache`·`*.pyc`, 그리고 A0 시험 파일 `optimized_config_t2390.json`(PRE_A1 §1 구성에 없음). 7,890 파일.
5. `git status`: "??"(추적 안 됨) 3,547줄뿐. 수정 0, 무시 0.

### 1.3 동결 [실행]

- 인계 `tools/sdmpc31/freeze_worktree.ps1`(sha `2f8ff1ea…`, 바꾸지 않음)을 `-Source W -FrozenRoot D:/VISSIM_runtime/20261025_codex_a1/frozen` 으로 돌렸습니다. 이 도구가 robocopy 뒤 `freeze_manifest.py build` 를 부릅니다(freeze_worktree.ps1:42-58).
- 출력: **FREEZE_OK**. FREEZE.json sha `b56268d988cbbb1cc727f903d77b3e36b341fc338ca39ba776bb17f700bac975`, 7,890 파일, 487,316,243 B, git head a49981ff, status 3,547줄, 217 s.

### 1.4 다시 대조 [실행 `work/a1/a1_tree_check.py` → `work/a1/tree_check_a1.json`]

| 대조 | 결과 |
|---|---|
| SOURCE_FILES.csv(목록 sha `5f575512…`) | 3,638 / 3,638 같음 |
| RESTORED_FILES.json(`184a2604…`) | 3,544 / 3,544 같음 |
| STANDIN_FILES.json(`c80839a9…`) | 3 / 3 같음 |
| 세 목록 밖 파일 | 705개, 모두 인계 code/ 사본과 바이트 같음 |
| FRZ 대 A0 코드 트리(캐시·t2390 뺌) | 바뀜 0, 빠짐 0, 더함 0 |
| FREEZE.json 파일표 대 FRZ | 같음 |
| FREEZE.json git status 경로 | = RESTORED + STANDIN 경로(모두 "??") |
| PRE_A1 §1 핵심 파일 | 러너 `8e95423b`·워치독 `b56e1b36`·VBS `14722088`·lane_native_b110.vbs `b74e05b2`·_sgplan `ec731cab`·어댑터 `a615d8ca`·sdmpc.py `5c1ba251`·tuning `c9088262`·망 `64cf5f55` 모두 같음 |

---

## 2. 러너 사전 점검 -PreflightOnly (점검 2)

- 방법 [실행]: 내 래퍼(`a1_wrapper.ps1`)를 WMI 로 띄워 인계 러너를 `-PreflightOnly` 로 돌렸습니다. 러너는 이 모드에서 VISSIM 점유 검사를 건너뛰고(run_closedloop3000.ps1:162-173), 워치독은 provenance 만 쓰고 끝납니다(watchdog:855-859) [읽음]. VISSIM·cscript 는 뜨지 않았습니다 [실행].
- 1차(18:28, 래퍼 v1 `84c438a4…`) [실행]: 종료 0, `FREEZE_VERIFIED`. 그런데 provenance `/env` 가 21키로, codex(20키)에 없는 `RW_PYTHON_EXE=""` 가 있었습니다.
  - 까닭 [실행]: 이 PC 사용자 레지스트리 env 에 `RW_PYTHON_EXE`(Python312 경로)가 있습니다. pwsh 7 에서 `SetEnvironmentVariable(name, $null)` 은 변수를 지우지 않고 빈 값으로 남깁니다. 러너도 RW_* 를 같은 방식으로 지웁니다(run_closedloop3000.ps1:109-111).
  - VBS 는 이 변수를 Python 후보로 읽습니다(run_real_world_stackelberg_controller.vbs:229-230, 5589) [읽음]. 빈 값의 영향은 시험하지 않았습니다.
- 2차(18:30, 래퍼 v2 `7a913760…`, `Remove-Item Env:` 로 지움) [실행]: 종료 0, `FREEZE_VERIFIED`, `/env` 20키 = codex 와 같은 키. 1차 출력은 `RES/a1_launch/preflight1_copy/` 에 보존했습니다.
- codex joint provenance 와 대조 [실행 `work/a1/a1_prov_cmp.py`, `a1_prov_blocks.py`]:
  - 값이 다른 RW_*: `RW_OBS150_DETECTORS`(동결 경로), `RW_PYTHON`(3.12.2 경로) 둘뿐.
  - `files` 18개 sha 모두 같음(망 `64cf5f55…`, tuning `c9088262…`, 어댑터, VBS, 워치독, 매핑, 보정, 수요 등).
  - `controller_sources` 116개, `signal_programs` 42개 차 0.
  - `ramp_meter_timing`·`signal_observation` 은 경로만 다름. `observation` 은 경로와 FREEZE.json sha 한 칸만 다름.
  - seed 29, sim 8100, 결정 간격 150, StartupStall 300, controller wu-link 같음.
- 워치독 설정 [실행 preflight_launch.log]: `OBS150 kill_policy=pid_only no_global_kill=True max_attempts=1`. 러너가 StallSec 2,400, StartupStallSec 300 을 넘깁니다(run_closedloop3000.ps1:161) [읽음]. 결정 시한은 tuning 의 1,800 s(`RW_DECISION_TIMEOUT_SEC=1800`) [실행].
- 실제 런의 provenance(01:19 작성, sha `4b56a69a…`)도 같은 대조에서 2차 사전 점검과 같은 결과였습니다 [실행 `work/a1/prov_cmp_run.json`].

---

## 3. env 기록 (점검 3)

- 파일: `codex_handoff/a1/A1_LAUNCH_ENV.json`(만든 도구 `work/a1/a1_env_record.py`). 런 provenance 는 RW_* 만 적으므로 나머지를 여기에 적습니다(PRE_A1 §1).
- 래퍼가 넣은 변수 [실행]: `PYTHONHASHSEED=0`, `OPENBLAS_CORETYPE=Haswell`, `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX`, `NUMBA_CPU_NAME=haswell`.
- 래퍼가 지운 변수 [실행]: NUMBA 6개, PYTHON* 8개(PYTHONPYCACHEPREFIX 포함), OPENBLAS 2개, NPY_ENABLE_CPU_FEATURES, MKL 2개, 그리고 RW_* 전부. S1 은 넣지 않았습니다.
- 러너가 넣는 변수 [읽음 run_closedloop3000.ps1:109-117]: RW_PYTHON, RW_MAINLINE_SG_ONLY=1, RW_OFFSET_WRITER=experiment, RW_RAMP_AMBER_SEC=0, RW_DECISION_FAIL_FAST=1, RW_QUEUE_COUNTER=1, PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=의존성;FRZ, NUMSIM_REPO_ROOT, OMP/OPENBLAS/MKL 스레드 1.
- Python [실행]: `C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe`, 3.12.2. A0·A0b 재생과 같은 인터프리터입니다(U9 의 같은 T 읽는 법이 같은 조건을 요구).
- 의존성 [실행]: `D:/VISSIM-window264-deps`. numpy 2.3.5, scipy 1.18.1, numba 0.67.0, llvmlite 0.49.0, pandas 3.0.1. 모두 그 폴더에서 import 됨. numba CPU 이름 haswell. numpy 의 AVX512F/CD/SKX/CLX 묶음 꺼짐.
- PowerShell [실행]: 래퍼·러너·워치독 모두 codex 런타임 pwsh 7.6.5. codex 기록도 codex 런타임 pwsh 로 돌았고, 그 판은 원자료에 없습니다 [읽음].
- 실제 런 래퍼 안의 env 전체(이름 46개, 비밀꼴 이름 가림)는 2차 사전 점검 때와 이름·값이 모두 같았습니다(차 0) [실행].

---

## 4. VISSIM 대기 (점검 4)

- [실행] 18:19 에 다른 세션 VISSIM PID 29028(rolling_cea 런, 14:16 시작)이 돌고 있었습니다. 인계 러너는 VISSIM 이 있으면 발사를 거부합니다(run_closedloop3000.ps1:164-172) [읽음].
- [실행] `work/a1/a1_wait_vissim.ps1` 로 30 s 마다 보고, 바뀔 때와 270 s 마다 `work/a1/vissim_wait.log` 에 적었습니다. 한 번 부를 때 최대 9 분이었습니다.
- [실행] 그 런은 01:16:07 에 스스로 끝났습니다(그 워치독 기록 "OK … elapsed=39589s"). 01:16:32 VISSIM 0, 01:17:32 에 60 s 넘게 0 을 확인했습니다. 01:17:41 에 python·pwsh·cscript·VISSIM 이 하나도 없었습니다(TD3 학습도 끝나 있었음).
- 기다린 시간 6 h 44 m(12 h 상한 안). kill 0.

---

## 5. 발사 (점검 5) [실행]

| 항목 | 값 |
|---|---|
| 시각 | 2026-10-26 01:17:48.909 KST(Create 전) – 01:17:48.955(뒤) |
| 방법 | `D:/VISSIM_runtime/20261025_codex_a1/launch/a1_launch_wmi.ps1 -Mode run`(sha `dbcf7048…`) → `Invoke-CimMethod Win32_Process Create` |
| ReturnValue / ProcessId | 0 / 34448 |
| 명령줄 | `"C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "D:\VISSIM_runtime\20261025_codex_a1\launch\a1_wrapper.ps1"` |
| 작업 폴더 | FRZ |
| 우선순위 | PriorityClass 32 = Normal(PRE_A1 U5 (b)) |
| 발사 때 | VISSIM 0, 디스크 C 30.2 GB, D 264.6 GB |
| 영수증 | `RES/a1_launch/wmi_launch_run.json`(sha `2be3e2f9…`) |

- 프로세스 [실행 01:18:03, 01:40:05]:
  - 래퍼 pwsh 34448(01:17:48) → 러너 pwsh 43828(01:17:54) → 워치독 pwsh 43080(01:19:25) → cscript 48380(01:19:28) → 결정마다 cmd → python.
  - VISSIM 40024(01:19:32, COM 서버라 부모는 svchost.exe PID 1204 [실행]). 워치독 기록 "VISSIM_PROCESS … pid=40024".
  - 러너가 동결 검사(freeze_manifest verify)에 약 90 s 를 썼습니다(01:17:54 – 01:19:25).
- 러너 명령(래퍼가 넘긴 그대로, `RES/a1_launch/wrapper_run_runner_cmd.json`): `run_closedloop3000.ps1 -FrozenTree FRZ -ResultsRoot RES -StatusPath RES/native_status.json -SimPeriod 8100 -Arms sdmpc -TuningRelativePath diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json -PythonExe <Python312> -PowerShellExe <codex 런타임 pwsh> -DependenciesPath D:/VISSIM-window264-deps`. `-Seed` 은 기본 29(codex detached 와 같은 생략). `-Detached` 는 쓰지 않았습니다.
- 소유 PID(kill 이 필요할 때만, 이 런 것만): 34448, 43828, 43080, 48380, 40024, 그리고 cscript 아래 결정 프로세스.

---

## 6. 첫 SDMPC 결정 T=900 (점검 6)

- 대조 선언 `work/a1/COMPARE_RULE_A1_T900.md`(sha `14349ed9…`)와 도구 `work/a1/a1_t900_check.py`(sha `2d41cd2a…`)는 A1 발사 전 LOG(2026-10-25 18:3x 항목)에 고정했습니다. 결과 `work/a1/t900_check_a1.json`(sha `a9b137ea…`).

### 6.1 종료와 시간 [실행]

| T (s) | A1 runlog wall_sec | codex wall_sec | A1 exit |
|---|---|---|---|
| 1 | 11.23 | 5.67 | 0 |
| 150 | 14.90 | 8.14 | 0 |
| 300 | 16.27 | 7.75 | 0 |
| 450 | 16.27 | 7.83 | 0 |
| 600 | 16.28 | 7.93 | 0 |
| 750 | 16.42 | 8.18 | 0 |
| 900 | **400.74** | 229.39 | **0** |

- T=900 decision_budget wall: A1 399.72 s, codex 228.81 s(배수 1.747).
- 시각 [실행 파일 시각]: `state_000900.json` 01:27:25, `action_000900.csv` 01:34:04. 그래서 시뮬 0–900 s(준비 결정 포함)는 VISSIM 기동부터 약 8 분이었습니다.
- 참고 [실행 A0_PROFILE §5.4]: 같은 T=900 의 A0 재생은 525.6–601.2 s(빈 PC 534.1 s)였습니다. A1 의 399.7 s 가 더 짧은 까닭은 확인하지 않았습니다. [추론] 우선순위(A1 Normal, 재생 BELOW_NORMAL)와 다른 세션 부하 0 이 후보입니다.
- 시한 1,800 s 에 닿지 않았고, 시한 유지 결정은 없습니다(R1 이 기록과 같고 exit 0).

### 6.2 명령 [실행]

| 대조 | R1 CSV | R2 다섯 칸 | R3 채점 토큰 | 다른 행 |
|---|---|---|---|---|
| A1 대 codex 기록 | 같음(`5be7a91b…`) | 같음 | 다름(A1 `942da6fd…`, codex `3a34ccae…`) | 0 / 213 |
| A1 대 A0 env_hsw 재생 | 같음 | 같음 | 다름(A0 `84cfeb38…`) | 0 / 213 |

- T = 1, 150, 300, 450, 600, 750 의 명령 CSV 도 codex 와 같습니다(6/6).
- [읽음 A0_PROFILE §4.1] R3 은 A0 에서도 기록·재생 사이에 늘 달랐습니다. 이번에도 셋이 서로 다릅니다.

### 6.3 결정 입력 [실행]

- `state_000900.json`: 잎 28,910개 중 28,898개 같음. 다른 12개는 64자리 해시 6(obs150 프레임·err 조각·설치 기록·mer 색인의 sha)과 그 밖 6(run_id 3칸, mer `byte_start`·`byte_end`, mer `max_t_any` 899.97 대 899.89)입니다. 경로·시계 잎 차는 0 입니다(두 런 폴더·두 동결 뿌리를 같은 이름으로 바꾼 뒤).
- `obs150/derived_000900.json`: 잎 6,986개 중 6,979개 같음. 다른 7개는 해시 5(입력 파일 sha)와 그 밖 2(run_id, `lag/max_t_any` 899.97 대 899.89)입니다.
- [추론] 다른 칸은 run_id·파일 바이트 위치·그 해시처럼 기록 부속물이고, 관측 값 잎은 같습니다. `max_t_any` 는 결정 때 읽은 차량 기록의 마지막 시각으로 보이며, 쓰기·읽기 시점 차일 수 있습니다. 명령에는 닿지 않았습니다(6.2).

---

## 7. 지금 상태와 다음

- [실행 01:40:05] T=1050 결정 진행 중(시작 01:36:03, 진행 기록 28줄), VISSIM 40024 살아 있음, `native_status.json` stage `native_running`, runlog `.err` 0 B, 결과 폴더 241 MB, 디스크 C 30.2 GB·D 264.3 GB.
- A0b 와의 관계 [읽음 A0B.md, 추론 PRE_A1 U9]: A0b 에서 기록과 처음 다른 결정은 T=1200 이었습니다. A1 의 T=1050 과 T=1200 명령이 codex 와 같은지는 아직 모릅니다. 같은 도구 꼴로 보려면 T 목록을 넓힌 선언을 데이터 전에 따로 고정해야 합니다.
- 감시 기준(발사 전 LOG 에 고정): 진행 신호 = 워치독 목록 + WATCHDOG_PROGRESS.txt, 무진행 499 s(A0 의 결정 안 최대 간격 199 s + 5 분) 넘으면 확인 → 이 런 PID 만 kill → 한 번만 재발사, 기록. 도구 `work/a1/a1_watch.ps1`(sha `7a1fced1…`).
- 끝 어림 [추론]: T=900 배수 1.75 와 A0b 배수 2.39 사이로 결정 49개(codex 14,088 s)를 잡으면 결정만 6.8–9.4 h 입니다. 시뮬 몫을 더해 2026-10-26 09–12 시 KST 무렵 끝날 것으로 봅니다. 한 결정만 본 배수라 넓게 잡았습니다.
- 끝나면 PRE_A1 §8.6: `STAGE=SIM_DONE`, 결정 49개 exit·유지 수, `.err` remain 줄. 그 뒤 §4·§5 대조(FZP 접두 sha, 지표 표)는 고정된 도구로.

---

## 8. 하지 않은 것과 지킨 것

- VISSIM 은 A1 하나만 띄웠습니다. 재발사 0, kill 0(다른 세션 프로세스 포함). B 폐루프 0.
- 커밋·푸시 0. W 의 git 은 빈 init + fetch + detached checkout 뿐이며 브랜치를 만들지 않았습니다. GWT8·`D:/VISSIM-merge/frozen/*`·인계 사본·공유 드라이브(Y:)에 쓰지 않았습니다.
- 금지 목록의 시험·도구(test_b1a_watchdog_attempt_launch.py 등)를 돌리지 않았습니다. sealed/·봉인 시드 0.
- 코드·설정 바이트를 바꾸지 않았습니다. 바꾼 것은 발사 절차 두 가지(§1.1 원천 W, §2 래퍼 v2)이며 둘 다 LOG 에 적었습니다.
- 디스크는 내내 8 GB 위였습니다(최저 C 29.2 GB, D 264.3 GB).

---

## 9. 파일과 sha256 [실행]

| 파일 | sha256 |
|---|---|
| FRZ/FREEZE.json | `b56268d988cbbb1cc727f903d77b3e36b341fc338ca39ba776bb17f700bac975` |
| `D:/VISSIM_runtime/20261025_codex_a1/freeze_worktree.out.txt` | `405eec9195bf682b0cd71f0af216855a43dd371bb3fdddf6c766a42f71d39757` |
| `launch/a1_wrapper.ps1`(v2, 런에 쓴 것) | `7a913760210f7cbf7460840b8a69d4e58e6287737b5d292b64c0ce8f728c7dbf` |
| `launch/a1_launch_wmi.ps1`(v2) | `dbcf7048c9d6fba8b92b25c6cb2b576e6a06a767ef64827603199da1bd654d7f` |
| `launch/a1_wrapper_v1.ps1` / `a1_launch_wmi_v1.ps1`(1차 사전 점검만) | `84c438a4…` / `8612f396…` |
| `RES/a1_launch/wmi_launch_run.json` | `2be3e2f9abed40f6929e99eacc024d8d1337d3c41014970cd28386b3d4a817eb` |
| `RES/a1_launch/wrapper_run_env.json` | `6007d6c7bd5e4c8502a284452ccf4f6c585acf3694c54a0bcf22d0dc1a722359` |
| `RES/a1_launch/wrapper_run_runner_cmd.json` | `dc1c1a44469f2b07948db5e96bf2c04f236705b5a22dfca805f20464ce0d2bf7` |
| `RES/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json` | `4b56a69acc5c94cc16f3223f871436aefa4e0d8b3873d9a2c88ed0ea1ccb2647` |
| `RES/sdmpc/preflight/run_provenance_…json`(2차) | `ccd7092c63f26bda7d84ca6e14b3bafe0a84f0ecea9d124b0dd1664989fa483b` |
| `RES/sdmpc/decisions_…/action_000900.csv` | `5be7a91b3061e31dfdcedba0b73813294d5a42df0727cecc575e9190a469a418` |
| `codex_handoff/a1/A1_LAUNCH_ENV.json` | `4faf4da5416b6d38655909f98a3ae70d797f1feb83c31e54c82a47d4d7d9a12c` |
| `work/a1/COMPARE_RULE_A1_T900.md` | `14349ed9b22ce5bcfe1f3ef0c37d6d0f24e9af8bec525bb8ec49b50165880b72` |
| `work/a1/a1_t900_check.py` | `2d41cd2a21a6dfb60dc0214447dcbb1891e1e9b18d0a32f4ab1ec74c5fb018b3` |
| `work/a1/t900_check_a1.json` | `a9b137eaf6ea63f80a0fee36f1c6bb40915d59d10719de4a2d0b114d15905b2f` |
| `work/a1/a1_tree_check.py` / `tree_check_a1.json` | `32869b5d…` / `6b8f6654…` |
| `work/a1/a1_prov_cmp.py` / `prov_cmp_preflight2.json` / `prov_cmp_run.json` | `c726cb4a…` / `a55144ee…` / `99c1a6fa…` |
| `work/a1/a1_prov_blocks.py` | `4a32cf9f…` |
| `work/a1/a1_env_record.py` | `a26f0b21…` |
| `work/a1/a1_wait_vissim.ps1` / `vissim_wait.log` | `26cc6731…` / `b6e21f8f…` |
| `work/a1/a1_watch.ps1` | `7a1fced1c3d26cb0756a4c34f38f887df8463216b524dc7184a8f59af33cadec` |
