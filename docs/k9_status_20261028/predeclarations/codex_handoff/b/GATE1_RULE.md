# GATE1_RULE — B 관문 1 선언: v3c3 첫 제어 결정(T=900) 재생 4개 + 러너 사전 점검 (2026-10-26 KST, 재생 전에 고정)

- 이 문서는 재생을 돌리기 **전에** 씁니다. sha256 을 `SP/codex_handoff/LOG.md` 에 적은 뒤에만 돌립니다. 돌린 뒤에는 고치지 않습니다. 이대로 할 수 없으면 멈추고 보고합니다.
- 판정 낱말은 쓰지 않습니다. 적는 것은 "끝까지 돌았나, 예외가 있었나, 몇 초 걸렸나, 무엇을 골랐나" 입니다.
- 표시: [실행] 명령으로 확인 · [읽음] 파일을 읽어 확인 · [추론] 시험하지 않은 판단.
- 근거: 사용자 결정 D-K9-88(관문 1 = T=900 재생 4개, 예외 0·결정 최대 ≤ 1,500 s 이면 B 3시드)·D-K9-89(B 설정 = PRE_B §1 그대로), 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(sha256 `d248605e…` [실행]). 계획 `SP/codex_handoff/b0/PRE_B.md` §2-1·§2-3, `b0/B0.md` r2 §7-1, `A1_B0_RESULTS.md` r2 §3 결정 거리 1 (a). SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`.

## 줄임말 (처음 한 번)

- FRZ_B0 = B 동결 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258`(FREEZE.json `853d1c4f…`). G1 = 관문 1 작업 뿌리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1`. W1 = 도구 폴더 `SP/codex_handoff/work/gate1`.
- B 설정 = `diagnostics/b0_v3c3/config_b0_v3c3.json`(`729640af…`). 그룹키 설정 = `…/config_b0_v3c3_groupkeys.json`(`e8a5730a…`, B 설정과 램프 도착 예측 객체 하나만 다름, 대조용이며 B 팔이 아님).
- V-A = 우리 묶음 B1 폐루프(v3c3, `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}`, 읽기만).
- env_hsw = `OPENBLAS_CORETYPE=Haswell`, `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX`, `NUMBA_CPU_NAME=haswell`.

## 1. 재생 넷 (이 차례, 한 번에 하나)

| ID | 상태(기록 런·T) | 설정 | 왜 |
|---|---|---|---|
| R1 | V-A v3c3-s31, T=900 (`state_000900.json` `d005d68a…`) | B 설정 | s31 첫 제어 결정 |
| R2 | V-A v3c3-s41, T=900 (`22b521a6…`) | B 설정 | s41 첫 제어 결정 |
| R3 | V-A v3c3-s43, T=900 (`1d3a40bd…`) | B 설정 | s43 첫 제어 결정 |
| R4 | V-A v3c3-s31, T=900 (R1 과 같은 상태) | 그룹키 설정 | H8 대조: 램프 도착 키(RM_C 대 옛 그룹키)가 같은 상태에서 결정을 바꾸는지 |

- 시드 수: 3(v3c3-s31·s41·s43). 넷 모두 v3c3 망(`3de889f0…`)의 기록 상태입니다.
- [실행] 세 시드 모두 직전 명령 `action_000750.json` 은 `metadata.controller = NoControl` 이고 `metadata.sdmpc_state` 가 없습니다(s31 `b9df6a61…`, s41 `4a4dd683…`, s43 `deb93df9…`), `.applied` 파일도 없습니다. codex A1 런의 T=750 도 `.applied` 가 없습니다. 그래서 `sdmpc.py:771-773`(`load_prices`, sdmpc_state 없음 → `first_sdmpc_decision`) 길로 갑니다 [읽음·추론].
- [실행] V-A 런에는 `vsl_cohorts_000750.json` 이 없습니다(codex A1 런에는 있음). codex 코드는 앞 VSL 이력이 없으면 VSL 제한 이력이 없을 때만 그대로 지나갑니다(`vsl_exposure_history.py:212-213, 231-232`) [읽음]. 이것은 재생 장치와 B 런의 알려진 차이입니다.
- V-A 의 T=900 기록 명령과는 비교하지 않습니다(다른 제어기).

## 2. 어떻게 돌리나

- 코드: FRZ_B0 를 그대로 code root 로 씁니다(읽기만). SDMPC 탄젠트 코드 캐시(`__tangentcache__`)는 코드가 FRZ 안에 만들 수 있고, 이 폴더는 FREEZE 검사 제외 목록에 있습니다(`freeze_manifest.py:35-37`) [읽음]. B 런도 같은 곳에 씁니다. 재생이 끝난 뒤 `freeze_manifest.py verify FRZ_B0` 를 돌려 바뀜·빠짐·더함 0 을 확인합니다.
- 러너 사전 점검(과제 4): 위 재생보다 **먼저** 넷을 돌립니다 — s31·s41·s43(B 설정, 관문 판정용)과 s31gk(그룹키 설정, R4 입력용 provenance 만). 도구 `W1/g1_preflight_wrapper.ps1`(A1 래퍼 v2 꼴: NUMBA*·PYTHON* 일부·RW_* 를 `Remove-Item` 으로 지움, env_hsw·PYTHONHASHSEED=0, env 기록) → 동결 러너 `run_closedloop3000.ps1 -PreflightOnly` 를 PRE_B §1 인자 그대로(`-SimPeriod 9000 -Seed <s> -Arms sdmpc -TuningRelativePath … -NetworkRelativePath diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx -NetworkSha256 3de889f0… -PythonExe Python312 -PowerShellExe <codex 런타임 pwsh 7.6.5> -DependenciesPath D:/VISSIM-window264-deps`). 다른 점은 결과 뿌리 하나: `G1/runner_preflight/s<seed>[gk]`(B 결과 뿌리가 아님). `-PreflightOnly` 는 VISSIM 점유 검사를 건너뛰고 VISSIM 을 띄우지 않습니다(`run_closedloop3000.ps1:168-179`) [읽음].
- 입력: `W1/g1_build_inputs.py` = B0 입력 도구(`work/b0/b0_build_inputs.py` `62dabb59…`)의 경로 상수만 바꾼 사본(바뀐 줄은 `W1/copies_gate1_record.json`). 기록 상태·직전 명령·obs150·lane 프레임·readback 을 바이트 그대로 복사하고, state·provenance 의 경로만 바꿉니다. provenance 는 같은 시드·같은 설정의 러너 사전 점검 출력에서 run_id·name·망 경로만 기록 상태에 맞춥니다(freeze 핀은 FRZ_B0 의 실제 FREEZE.json).
- 재생: `W1/g1_replay.ps1`(B0 재생 도구 `1b32085d…` 에서 바꿈: code root FRZ_B0, RW_* = 입력 provenance 의 비지 않은 RW_* 값(튜닝 sha 일치 검사), 감싸개 없이 어댑터 직접 호출, 우선순위 Normal, A1 래퍼 v2 의 지움 목록). 어댑터 인자는 B0 재생과 같습니다(`--controller wu-link`, 매핑·검지 매핑·보정 파일 같음, `--previous-action-json action_000750.json`).
- 환경: env_hsw, `PYTHONHASHSEED=0`, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, OMP·OPENBLAS·MKL 스레드 1, `PYTHONPATH = D:/VISSIM-window264-deps;FRZ_B0`, `NUMSIM_REPO_ROOT = FRZ_B0/vendor/NumSim-mine`.
- 우선순위: Normal. 까닭: 지금 B 런이 없고(과제 규칙의 BELOW_NORMAL 은 B 런이 돌 때만), B 런의 결정도 Normal 로 돕니다(PRE_B §1). 다른 세션 프로세스(다른 VISSIM, TD3 학습 등)는 건드리지 않습니다. 그 부하는 재생마다 `typeperf`(5 s) CPU 기록과 시작 때 프로세스 목록으로 적습니다.
- 발사: `W1/g1_launch_wmi.ps1` → WMI `Win32_Process.Create`(Normal, 숨김) → `W1/g1_queue.ps1`(Windows PowerShell 5.1). 큐 차례: 사전 점검 4 → 입력 4 → 재생 R1·R2·R3·R4 → FRZ_B0 freeze verify → 요약(`W1/g1_summary.py`).
- 상한: 재생 하나가 7,200 s 를 넘으면 그 재생의 **내 프로세스 나무만** 멈추고 `stopped_cap` 으로 적습니다(통과 아님). 디스크 C·D 가 8 GB 아래면 큐가 다음 단계로 가지 않습니다. 다른 것은 끄지 않습니다.

## 3. 통과 조건 (데이터 전 고정)

재생마다 넷을 모두 만족하면 그 재생 "통과":

1. 종료 코드 0.
2. 예외 0: stderr 에 `Traceback (most recent call last)` 없음, `DECISION_FAILED` 없음, 결정 폴더에 `action_000900*.error*` 파일 없음. stderr 의 `[경고]` 줄은 예외로 세지 않습니다.
3. 결정이 끝남: `action_000900.json`·`action_000900.csv` 가 있고 `action_000900.decision_budget.json` 의 `output_completed = true`.
4. 결정 벽시계 ≤ 1,500 s. 벽시계 = 래퍼 스톱워치(파이썬 프로세스 시작–끝)와 `decision_budget.wall_sec` 가운데 큰 값.

관문 1 = 재생 넷 모두 통과. 과제의 반환 조건은 여기에 더해 **러너 사전 점검 s31·s41·s43 모두 통과**와 **재생 뒤 FRZ_B0 `FREEZE_VERIFIED`** 입니다.

러너 사전 점검 하나 "통과" = 아래 칸이 모두 참(`g1_summary.py` 의 `checks`):
종료 0 · 러너 로그에 `FREEZE_VERIFIED` · provenance 망 sha `3de889f0…` · `RW_DECISION_ERROR_POLICY=hold_previous_on_exception`, `RW_DECISION_HOLD_PREVIOUS=1`, `RW_DECISION_TIMEOUT_SEC=0` · 튜닝 sha(B `729640af…`, gk `e8a5730a…`) · freeze 핀 `853d1c4f…` · plant manifest 핀 `11842498…` · 검지표 핀 `108debbb…`·294행 · seed 일치 · sim 9000 · controller `wu-link` · 빈 RW 값은 `RW_OBS150_GT` 하나뿐(A1 에서 본 `RW_PYTHON_EXE=""` 함정이 없음).

- 관문 1 에서 통과하지 못한 것이 하나라도 있으면 B 런을 띄우지 않고 멈추고 정확한 까닭을 보고합니다. 1,500 s 를 넘은 경우는 StallSec(2,400 s)를 올릴지 사용자에게 따로 묻는 일입니다(PRE_B §2-2).
- T=900 은 첫 제어 결정이라 예외 유지 대상이 아닙니다(B0.md H3 `ExceptionHoldGate`). 그래서 이 재생의 유지 수는 0 이 정상이고, B 런에서 T=900 예외는 런 멈춤입니다 [읽음·추론].

## 4. 적는 것 (`W1/g1_summary.py` → `W1/gate1_summary.json`)

- 재생마다: 종료 코드, 예외 종류와 stderr 마지막 줄, `[경고]` 줄 수, 벽시계 두 개(래퍼·budget)와 budget CPU 초, `unlimited_time`, 진행 기록 줄 수, CPU 평균·큐 길이 평균, 시작 때 다른 python·VISSIM·cscript 프로세스, 명령 CSV 행 수(kind 별)와 sha256, VSL 속도 집합과 행 수, 미터 행(`rate_vph`·`green_sec`, 8개), 신호 행(SC 별 p1–p4 녹색·offset, 17개)과 signal_sg 행 수, `ramp_metering` 값, 램프 도착 예측 메타데이터(`forecast_ramp_arrival_total_vph` 와 옛 그룹키 4칸, `RM_C` 이름이 붙은 도착 칸이 있으면 그것), `decision_wall_sec`·`prediction_wall_sec` 메타, `sdmpc_state` 유무, 유령 경로 별칭 언급 수, `joint.json` 의 selection 스칼라 5개, 유지·오류 파일 목록.
- R1 대 R4: 명령 CSV 바이트 같음 여부, kind 별 다른 행 수와 id, 숫자 칸별 최대 |차|, 예측 합 두 값, selection 두 값. "같음/다름" 사실만 적고 판정하지 않습니다.
- 사전 점검마다: 위 §3 칸들과 provenance sha256, env 키 수, 래퍼 벽시계.
- 재생 뒤 freeze verify 출력 끝 400자와 `FREEZE_VERIFIED` 유무.

## 5. 이 관문이 알려 주지 않는 것 [추론]

- 준비 결정(T=1–750, no-control 길)은 시험하지 않습니다. B 런은 이 결정들도 codex 어댑터로 돕니다(A1 에서 11–16 s).
- T=900 하나는 뒤 결정의 짐을 대표하지 않습니다(A1: T=900 400.7 s, 평균 520.5 s, 최대 771.5 s).
- 재생 상태는 V-A(우리 제어기 러너)의 기록입니다. B 런의 T=900 상태는 codex 러너·codex 준비 결정으로 만들어지므로 바이트가 다릅니다(예: `vsl_cohorts_000750.json`, derived 파일).
- 이 PC 의 다른 세션 부하가 벽시계를 늘릴 수 있습니다. 부하는 적되 빼지 않습니다.

## 6. 도구 (sha256, 이 문서와 함께 LOG 에 고정)

| 파일 (W1 = `SP/codex_handoff/work/gate1`) | sha256 |
|---|---|
| `W1/g1_preflight_wrapper.ps1` | `17549a56d04dfc5989045b60352745cc5d504d9b3451c8105f759fa0b404f56e` |
| `W1/g1_build_inputs.py` (← `work/b0/b0_build_inputs.py` `62dabb59…`, 경로 상수만) | `51aa645e7be64ca7c0f1092776dfe58a4b1ee04a467738e6093275d742363db3` |
| `W1/g1_replay.ps1` (← `work/b0/run_replay_b0.ps1` `1b32085d…`) | `4fa4167826dc6d80abf8c2dad10789c77d07ca6e7a9ac6d373f74ea2e68bfa29` |
| `W1/g1_queue.ps1` | `7b41d3d859c68b08a0373bdcde644eca7a35008da4809311a325eec2086f6ede` |
| `W1/g1_launch_wmi.ps1` | `bcd208f905ecaa38e58b81290d391c11c6ce591405f469b2744d5747659da045` |
| `W1/g1_summary.py` (← `work/b0/b0_replay_summary.py` `b20edbf4…` 에서 넓힘, 수집 경로 결함 고침) | `cf1786c878bfecfe4bb896fa8886ab6fc0125025557ba43cfbff89e3a0f33370` |
| `W1/mkcopy.py` (사본 생성기) / `W1/spec_gate1_copies.json` / `W1/copies_gate1_record.json` | `8ec4f60c…` / `83b297e8…` / `3330c867…` |
| `work/a0/s5_collect.py` (바꾸지 않고 씀) | `90b1a350f1c05f8f5aa3f39275d893a12af46b850da3aab53e718b3d0020dcb1` |
| 설정 B / 그룹키 (FRZ_B0 안, 바꾸지 않음) | `729640af…` / `e8a5730a…` |
