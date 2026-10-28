# GATE1 — B 관문 1 결과: v3c3 첫 제어 결정(T=900) 재생 4개 + 러너 사전 점검 (2026-10-26 11:11–11:42 KST, VISSIM 0)

- 선언: `SP/codex_handoff/b/GATE1_RULE.md`(sha256 `766c5737…`, LOG 11:11 항목에 재생 전 고정). 비교 규칙: `SP/codex_handoff/b/COMPARE_RULE_B.md`(`f902f7f0…`, LOG 11:20 항목에 B 데이터 전 고정). SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, W1 = `SP/codex_handoff/work/gate1`, G1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1`.
- 판정 낱말은 쓰지 않습니다. "조건 만족" 은 GATE1_RULE §3 에 미리 적은 네 조건이 사실로 맞는다는 뜻입니다.
- 표시: [실행] 명령으로 확인 · [읽음] 파일을 읽어 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.
- 줄임말: FRZ_B0 = B 동결 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258`(FREEZE `853d1c4f…`). V-A = 우리 묶음 B1 폐루프 기록(상태만 빌려 씀). B 설정 = `config_b0_v3c3.json`(`729640af…`). 그룹키 설정 = 램프 도착 예측 객체만 codex 원래 값인 대조 설정(`e8a5730a…`). env_hsw = OpenBLAS·numpy·numba 를 Haswell(AVX2) 길로 묶는 변수 셋.

## 0. 쉬운 답

1. [실행] 재생 넷(R1 s31·R2 s41·R3 s43 은 B 설정, R4 s31 은 그룹키 설정) 모두 종료 0, 예외 0(Traceback·DECISION_FAILED·오류 파일 없음), 결정이 끝까지 돌아 명령 JSON·CSV 를 썼습니다(`output_completed = true`).
2. [실행] 결정 벽시계(파이썬 프로세스 시작–끝) 381.5 / 403.1 / 296.4 / 401.3 s. 최대 403.1 s(R2) 로 1,500 s 아래, StallSec 2,400 s 의 16.8 % 입니다 [계산]. budget wall 은 각각 1 s 쯤 짧습니다.
3. [실행] 러너 `-PreflightOnly` s31·s41·s43(B 설정) 모두 종료 0, `FREEZE_VERIFIED`, 망 sha `3de889f0…`, 유지 env(`hold_previous_on_exception`, `RW_DECISION_HOLD_PREVIOUS=1`, `RW_DECISION_TIMEOUT_SEC=0`), 튜닝·freeze·plant manifest·검지표 핀이 모두 맞습니다. 빈 RW 값은 `RW_OBS150_GT` 하나뿐(A1 에서 본 `RW_PYTHON_EXE=""` 없음, env 키 21). R4 입력용 s31gk 점검도 같습니다.
4. [실행] 재생이 끝난 뒤 FRZ_B0 를 다시 검사: `FREEZE_VERIFIED … files=7989 head=a49981ff…`(exit 0).
5. 그래서 GATE1_RULE §3 의 관문 1 조건(재생 넷 모두 + 사전 점검 셋 모두 + 재생 뒤 FREEZE_VERIFIED)이 모두 맞습니다. 이 단계는 B 런을 띄우지 않았습니다(띄우는 것은 BRuns 단계 몫).
6. [실행] H8 대조(R1 대 R4, 같은 s31 상태): 램프 도착 예측 합은 4,067.4 대 2,040.0 veh/h 로 다르지만, 명령 CSV 는 **바이트까지 같고**(213행, 다른 행 0), selection 스칼라 다섯도 같습니다. 이 한 상태에서는 RM_C 키가 결정 출력을 바꾸지 않았습니다(한 상태·한 시드).
7. 밝힘 셋: (가) 요약 도구 r1 이 FRZ_B0 검사 출력(Windows PowerShell 5.1 `>` 가 쓴 UTF-16)을 UTF-8 로 읽어 `FREEZE_VERIFIED` 를 못 찾았습니다 → 읽기만 고친 r2 로 다시 냄(데이터 뒤 고침, 값 판단 무관). (나) 재생이 FRZ_B0 안에 캐시 106개(`__tangentcache__` 100, numba `__pycache__` .nbi/.nbc 6)를 썼습니다. 둘 다 FREEZE 제외 폴더이고 그 밖의 새 파일은 0 입니다. (다) LDP 신호 실행 대조(ldp_cmp 꼴)는 NC3 에 LDP 가 없어 COMPARE_RULE_B 에 "못 냄" 으로 미리 적었습니다.

## 1. 한 일 (시각 KST)

| 시각 | 일 | 근거 |
|---|---|---|
| 10:50–11:10 | 입력·도구 읽기, 관문 1 도구 작성, GATE1_RULE 작성 | – |
| 11:11 | GATE1_RULE·도구 sha 를 LOG 에 고정 → WMI 발사(ReturnValue 0, 큐 PID 33528, Normal) | [실행 `W1/launch_receipts.log`] |
| 11:11:09–11:13:33 | 러너 `-PreflightOnly` s31(89.8 s)·s41(15.0 s)·s43(16.8 s)·s31gk(16.4 s), 모두 exit 0 | [실행 `W1/queue_g1.state.txt`] |
| 11:13:34–11:13:39 | 재생 입력 넷 만듦(각 89 파일), exit 0 | [실행 `G1/pristine/*/T000900/INPUT_MANIFEST.json`] |
| 11:13:41–11:39:03 | 재생 R1→R2→R3→R4 한 번에 하나 | [실행 `G1/out/g1R*/…/replay_state.json`] |
| 11:39:29 | FRZ_B0 `freeze_manifest.py verify` exit 0 | [실행 `G1/freeze_verify_after.txt`] |
| 11:39:42 | 요약 r1 → (UTF-16 결함) → 11:4x 요약 r2·표 | [실행] |
| 11:12–11:20 (재생과 겹쳐, 가벼운 일) | COMPARE_RULE_B·사본 23개 작성·고정 | LOG 11:20 항목 |
| 11:41–11:42 | 사본 하나 연기 시험(NC3 s31 첫 관측 스캔, 원본과 같음) | §5 |

- 이 PC 의 다른 세션: VISSIM PID 29264(rolling_cea)·cscript 32716 이 내내 돌았고 TD3 학습 python 도 있었습니다 [실행 10:51, 11:23, 재생 시작 때 목록]. 건드리지 않았습니다. 재생 중 CPU 전체 평균 38–56 %(5 s 표본) [실행 typeperf].

## 2. 재생 결과 (시드 3: v3c3-s31·s41·s43, 상태 4: s31 은 두 설정)

### T1 끝남·예외·벽시계

| 재생 | 종료 | 예외 | `[경고]` 줄 | 래퍼 벽시계 (s) | budget wall (s) | budget CPU (s) | output_completed | 진행 줄 | CPU 평균 % (큐 길이) | GATE1_RULE §3 네 조건 |
|---|---:|---|---:|---:|---:|---:|---|---:|---|---|
| R1 V-A v3c3-s31 · B 설정 | 0 | 없음 | 3 | 381.5 | 380.5 | 168.6 | True | 43 | 41.5 (0.0) | 넷 모두 만족 |
| R2 V-A v3c3-s41 · B 설정 | 0 | 없음 | 3 | 403.1 | 401.7 | 196.8 | True | 43 | 50.3 (1.7) | 넷 모두 만족 |
| R3 V-A v3c3-s43 · B 설정 | 0 | 없음 | 3 | 296.4 | 295.6 | 164.4 | True | 30 | 38.2 (0.0) | 넷 모두 만족 |
| R4 V-A v3c3-s31 · 그룹키 설정 | 0 | 없음 | 3 | 401.3 | 400.4 | 188.1 | True | 43 | 55.9 (0.5) | 넷 모두 만족 |

- `[경고]` 세 줄은 넷 모두 같은 글입니다(leader_hinge·np_deadband·leader_mfd_far 성분의 캘리브레이션 기하가 지금 merge 집합과 다르다는 안내). A1 의 T=900 런 로그에도 같은 세 줄이 있습니다 [읽음 A1 runlog:500]. 예외로 세지 않습니다(GATE1_RULE §3-2).
- 참고 [읽음 A1_LAUNCH §6.1]: A1(64cf-s29, codex 설정) T=900 은 400.74 s 였습니다. 망·설정·상태가 달라 짝 비교는 아닙니다.
- 우선순위 Normal, python 프로세스 Normal [실행 replay_state]. `decision_budget` 은 "Wall limits explicitly disabled"(`unlimited_time = true`) [실행].

### T2 명령 CSV·VSL·유지

| 재생 | 행 수 (kind 별) | CSV sha256 앞 16 | VSL 속도 집합 (행) | `controller_status` | 새 `sdmpc_state` | 유령 별칭 언급 | 유지·오류 파일 |
|---|---|---|---|---|---|---:|---|
| R1 | 213 (vsl 66, signal 17, signal_sg 122, ramp_meter 8) | `c130fde6b115567d` | 110 (66) | ok | 있음 | 0 | 없음 |
| R2 | 213 (같은 구성) | `ccae782398957a13` | 110 (66) | ok | 있음 | 0 | 없음 |
| R3 | 213 (같은 구성) | `a2e32a11df7f597e` | 110 (66) | ok | 있음 | 0 | 없음 |
| R4 | 213 (같은 구성) | `c130fde6b115567d` | 110 (66) | ok | 있음 | 0 | 없음 |

- 유지 0 은 정상입니다: T=900 은 첫 제어 결정이라 VBS 유지 대상이 아니고(B0.md H3), 재생 장치는 VBS 를 거치지 않습니다. B 런에서 T=900 예외가 나면 런이 멈춥니다 [읽음·추론].
- VSL 은 B 설정의 고정 110 그대로입니다.

### T3 미터 명령 (rate_vph / green_sec, 명령 CSV)

| 미터 | R1 s31 | R2 s41 | R3 s43 | R4 s31(그룹키) |
|---|---|---|---|---|
| RM_C10480 | 720 / 8 | 720 / 8 | 900 / 10 | 720 / 8 |
| RM_C10482 | 900 / 10 | 900 / 10 | 900 / 10 | 900 / 10 |
| RM_C10484 | 720 / 8 | 720 / 8 | 900 / 10 | 720 / 8 |
| RM_C10490 | 720 / 8 | 720 / 8 | 720 / 8 | 720 / 8 |
| RM_C10639 | 720 / 8 | 720 / 8 | 900 / 10 | 720 / 8 |
| RM_C10644 | 900 / 10 | 900 / 10 | 900 / 10 | 900 / 10 |
| RM_C10646 | 900 / 10 | 900 / 10 | 900 / 10 | 900 / 10 |
| RM_C10681 | 900 / 10 | 720 / 8 | 900 / 10 | 900 / 10 |

- 명령 JSON 의 `ramp_metering` 칸 값(예 RM_C10480 1,166.4, RM_C10482 3,024.0)은 CSV 의 rate 와 다른 양입니다. A1 의 T=900 JSON 도 같은 꼴입니다 [실행]. 실제로 적용되는 것은 CSV 입니다 [추론].

### T4 신호 명령 (p1/p2/p3/p4 녹색 s, offset s; 명령 CSV `signal` 행)

| 신호 | R1 s31 | R2 s41 | R3 s43 | R4 s31(그룹키) |
|---|---|---|---|---|
| SC1 | 58.75/20.0/34.25/25.0, 53.554 | 60.0/20.0/33.0/25.0, 94.0 | 60.0/20.0/33.0/25.0, 69.801 | R1 과 같음 |
| SC5 | 49.0/21.453/47.413/20.134, 114.125 | 49.0/20.0/49.0/20.0, 75.177 | 49.0/20.0/49.0/20.0, 108.493 | R1 과 같음 |
| SC6 | 49.0/20.471/47.327/21.202, 32.841 | 49.0/20.0/49.0/20.0, 25.786 | 49.0/23.0/46.0/20.0, 28.03 | R1 과 같음 |
| SC7 | 67.341/84.0/0.0/30.0, 6.714 | 73.0/84.0/0.0/30.0, 111.511 | 73.0/84.0/0.0/30.0, 113.035 | R1 과 같음 |
| SC11 | 31.919/29.0/39.802/37.279, 73.537 | 41.461/29.0/39.719/27.82, 73.428 | 42.0/29.0/40.0/27.0, 77.231 | R1 과 같음 |
| SC12 | 49.738/24.262/38.0/26.0, 141.518 | 54.0/20.0/38.0/26.0, 115.183 | 48.649/25.351/38.0/26.0, 117.929 | R1 과 같음 |
| SC16 | 57.0/17.0/33.0/0.0, 39.114 | 59.325/17.0/30.675/0.0, 17.317 | 57.0/17.0/33.0/0.0, 34.867 | R1 과 같음 |
| SC101 | 54.0/21.275/42.725/20.0, 32.437 | 54.0/26.0/35.902/22.098, 62.37 | 54.0/27.083/33.0/23.917, 0.247 | R1 과 같음 |
| SC105 | 50.877/20.0/39.123/28.0, 0.184 | 48.782/20.218/41.0/28.0, 103.885 | 54.0/20.0/36.0/28.0, 76.585 | R1 과 같음 |
| SC107 | 0.0/26.273/82.727/32.0, 136.815 | 0.0/25.0/84.0/32.0, 137.191 | 0.0/31.0/78.0/32.0, 136.813 | R1 과 같음 |
| SC108 | 37.0/0.0/82.0/22.0, 30.522 | 37.0/0.0/82.735/21.265, 42.022 | 37.0/0.0/84.0/20.0, 38.339 | R1 과 같음 |
| SC109 | 0.0/26.0/90.0/25.0, 12.379 | 0.0/26.0/90.0/25.0, 10.077 | 0.0/26.0/90.0/25.0, 16.764 | R1 과 같음 |
| SC1001 | 48.776/20.0/39.224/30.0, 83.252 | 46.873/20.0/41.127/30.0, 75.064 | 52.0/27.0/39.0/20.0, 79.718 | R1 과 같음 |
| SC1002 | 52.0/20.0/46.0/20.0, 54.709 | 52.0/20.0/44.474/21.526, 69.555 | 52.0/24.43/41.57/20.0, 85.112 | R1 과 같음 |
| SC1003 | 51.645/21.83/39.0/25.525, 70.009 | 52.0/20.0/39.0/27.0, 70.054 | 52.0/20.0/39.0/27.0, 61.653 | R1 과 같음 |
| SC1004 | 44.741/22.027/50.494/20.738, 128.5 | 40.0/20.0/51.0/27.0, 0.0 | 52.0/20.0/46.0/20.0, 68.054 | R1 과 같음 |
| SC1005 | 44.982/29.0/43.982/20.036, 78.993 | 44.964/29.0/43.964/20.072, 79.041 | 45.0/29.0/44.0/20.0, 78.875 | R1 과 같음 |

- 17개 신호 모두 명령이 나왔습니다(signal_sg 122행 포함). "R1 과 같음" 은 R4 의 값이 R1 과 글자까지 같다는 뜻입니다(CSV 바이트 같음, §3).

### T5 램프 도착 예측 메타데이터와 선택 스칼라 (`joint.json` selection)

| 칸 | R1 s31 | R2 s41 | R3 s43 | R4 s31(그룹키) |
|---|---|---|---|---|
| `forecast_ramp_arrival_total_vph` (RM_C 경로) | 4,067.4 | 5,558.0 | 3,471.2 | 2,040.0 |
| 옛 그룹키 4칸(`…_R_D_W/R_D_E/R_F_W/R_F_E_vph`) | 0 ×4 | 0 ×4 | 0 ×4 | 0 ×4 |
| RM_C 이름이 붙은 도착 칸 | 출력에 없음 | 출력에 없음 | 출력에 없음 | 출력에 없음 |
| `dedicated_offramp_arrival_duplicate_removed_veh` | 12 | 8 | 7 | 12 |
| `held_objective` | 410.555 | 411.547 | 409.212 | 410.555 |
| `warm_start_objective` | 408.489 | 409.283 | 407.534 | 408.489 |
| `selected_objective` | 407.147 | 407.702 | 407.410 | 407.147 |
| `prediction_ttt_reduction` | 3.409 | 3.845 | 1.802 | 3.409 |
| `selection_status` | best_observed_feasible_sdmpc (넷 모두) | | | |
| `decision_wall_sec` 메타 (s) | 370.9 | 393.3 | 290.8 | 391.7 |

- 반올림은 표시용입니다(원값은 `W1/gate1_summary_r2.json`). [계산] R4 의 2,040.0 = 30 × 68 로 30 의 배수입니다(B0 에서 본 120 s·900 veh/h 폴백 꼴과 같은 성질).
- 옛 그룹키 4칸이 0 인 것은 RM_C 런에서 늘 0 인 메타데이터 칸이라서입니다(B0.md §4-4) [읽음].

## 3. R1 대 R4 (H8 대조: 같은 상태, 램프 도착 예측 객체만 다름) [실행]

- 명령 CSV 바이트 같음: 예(sha `c130fde6…` 둘 다). 213 대 213 행, 한쪽만 있는 키 0, 다른 행 0.
- selection 스칼라 다섯 같음, `decision_wall_sec` 만 다름(370.9 대 391.7 s, 같은 일의 시간 차).
- 램프 도착 예측 합: 4,067.4(RM_C·strict) 대 2,040.0(그룹키) veh/h.
- 읽는 법 [추론]: 이 v3c3-s31 T=900 상태에서는 RM_C 키가 바꾼 예측 합이 결정 출력까지 닿지 않았습니다. B0 에서 읽은 "gate 램프 착지 0" 길(B0.md §4)과 맞습니다. 다만 상태 하나·시드 하나이고, 리더 N_UF 도착 목표 길(B0.md §4 r2 보충)이 다른 상태에서 결정을 바꾸는지는 이 대조가 닫지 않습니다.

## 4. 러너 사전 점검 [실행]

| 점검 | 종료 | FREEZE_VERIFIED | 망 sha | 유지 env | 튜닝 sha | freeze 핀 | plant 핀 | 검지표 핀(294행) | seed·9000·wu-link | 빈 RW 값 | env 키 | 벽시계 (s) | provenance sha256 |
|---|---:|---|---|---|---|---|---|---|---|---|---:|---:|---|
| s31 | 0 | 예 | 예 | 예 | 예(B) | 예 | 예 | 예 | 예 | RW_OBS150_GT | 21 | 89.8 | `f734ebcbbf8f79b5ab0297e15430f60d4a6c81a47c8af36033e6d80711f3deac` |
| s41 | 0 | 예 | 예 | 예 | 예(B) | 예 | 예 | 예 | 예 | RW_OBS150_GT | 21 | 15.0 | `9b10552766ef5df5f7fec3b19c14dd3456c835c0dff613769bb33d5414f61905` |
| s43 | 0 | 예 | 예 | 예 | 예(B) | 예 | 예 | 예 | 예 | RW_OBS150_GT | 21 | 16.8 | `19aa70671cf7ab0be27706245aadee51ee28e5c9d7ffac5a127d4f8760e1242a` |
| s31gk (R4 입력용) | 0 | 예 | 예 | 예 | 예(그룹키) | 예 | 예 | 예 | 예 | RW_OBS150_GT | 21 | 16.4 | `e622be686497b56b1dcbc4d6174eb880f90e66dd8f67ee95715fc6edeea9dd6f` |

- 방법: `W1/g1_preflight_wrapper.ps1`(A1 래퍼 v2 꼴: RW_*·NUMBA*·PYTHON* 일부를 `Remove-Item` 으로 지움, env_hsw·PYTHONHASHSEED=0) → 동결 러너 `run_closedloop3000.ps1 -PreflightOnly`, PRE_B §1 인자 그대로(`-SimPeriod 9000 -Seed <s> -Arms sdmpc -TuningRelativePath diagnostics/b0_v3c3/config_b0_v3c3.json -NetworkRelativePath diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx -NetworkSha256 3de889f0… -PythonExe Python312 -PowerShellExe <codex 런타임 pwsh> -DependenciesPath D:/VISSIM-window264-deps`).
- 다른 점 하나: 결과 뿌리는 `G1/runner_preflight/s<seed>` 이고 B 결과 뿌리(`D:/VISSIM_runs/20261026_codex_b_v3c3/s<seed>`)가 아닙니다. 그 폴더는 이 단계에서 만들지 않았습니다 [실행 ls].
- workspace_root = FRZ_B0, StartupStallSec 300 [실행]. B0 의 사전 점검(10-26 03:0x)은 env 키 22개로 `RW_PYTHON_EXE=""` 이 있었습니다 [실행 `ece04055…` 읽음]. 이번 래퍼에서는 없습니다.
- s41·s43·s31gk 의 벽시계가 짧은 것은 동결 검사(파일 7,989개 해시)의 파일 캐시 때문으로 봅니다 [추론]. 넷 모두 `FREEZE_VERIFIED` 를 찍었습니다.

## 5. FRZ_B0 상태와 B 분석 도구 준비

- [실행] 재생 뒤 `freeze_manifest.py verify FRZ_B0`: `FREEZE_VERIFIED … sha256=853d1c4f… files=7989 head=a49981ff…`, exit 0(`G1/freeze_verify_after.txt` `983da4e3…`, UTF-16LE).
- [실행] GATE1_RULE 고정 뒤 FRZ_B0 에 새로 생긴 파일: `evaluation/controllers/__tangentcache__/` 100개, `evaluation/controllers/__pycache__/` numba 캐시 6개(.nbi 3·.nbc 3). 그 밖 0. 두 폴더는 FREEZE 제외 목록입니다(`freeze_manifest.py:35-37`) [읽음]. GATE1_RULE §2 는 탄젠트 캐시만 적었고 numba 캐시는 적지 않았습니다(밝힘). B 런은 같은 env_hsw(`NUMBA_CPU_NAME=haswell`)로 이 캐시를 다시 쓸 수 있고, 캐시는 같은 기계어를 다시 읽는 것이라 결정 값은 바뀌지 않는 것으로 봅니다 [추론].
- COMPARE_RULE_B(`f902f7f0…`)와 분석 도구 사본 23개를 B 데이터 전에 고정했습니다(LOG 11:20, 묶음 목록 `SP/codex_handoff/b/PINS_B.sha256` `5e8ffbc5…`, 54줄 `sha256sum -c` OK). ④ 두 적분 꼴을 글로 적었습니다: 우리 꼴 [0, 9000] s(5.1–8,995.1 s 사다리꼴, 0.10 s 프레임 건너뜀, 양끝 늘림 없음), codex 꼴 [0, 8100] s = 시각축 사다리꼴(0 s 빈 망에서 선형, 8,095.1 s 재고를 8,100 s 까지 유지; VERIFY_A1_B0 §0-4 로 확인된 꼴).
- [실행] 사본 연기 시험 하나: `vhr_b/vhr_firstseen_b.py nc3_s31` 출력이 원본 `vhr/scan_out/first_nc3_s31.json` 과 같음(걸린 초 칸만 다름). 이 사본은 출력 폴더를 만들지 않아(원본도 같음) 폴더 `CW/vhr_b/scan_out` 을 미리 만들었습니다. COMPARE_RULE_B §7.5 차례(vhr_scan_b 가 먼저)를 따르면 필요 없는 일입니다. omega 사본은 인자 없이 부르면 docstring 머리에 B 사본 표시를 찍고 멈춥니다(정상).

## 6. 밝힘 (데이터 뒤에 한 일, 값 판단 무관)

1. 요약 도구 r2: `W1/g1_summary.py`(r1, `cf1786c8…`)는 `freeze_verify_after.txt` 를 UTF-8 로 읽어 `verified = false`, 관문 칸 `pass = false` 를 냈습니다(`W1/gate1_summary.json` `2f8742db…`). 그 파일은 Windows PowerShell 5.1 의 `>` 가 쓴 UTF-16LE 입니다 [실행 첫 바이트 `ff fe`]. 읽기 두 줄만 고친 `W1/g1_summary_r2.py`(`520bb2b9…`, 사본 생성기로 만듦, 바뀐 줄 기록 `W1/copies_g1_summary_r2_record.json` `803a415b…`)로 다시 내어 `W1/gate1_summary_r2.json`(`ea27c492…`) 을 얻었습니다. 재생·사전 점검 칸은 r1 과 같고(표 T1–T7 글자 같음 [실행 diff]), 다른 것은 freeze 칸뿐입니다.
2. 표 도구 `W1/g1_tables.py`(`7b91496a…`): 요약 JSON 을 Markdown 표로 옮기기만 합니다(새 숫자 없음). 출력 `W1/gate1_tables_r2.md`(`398b2049…`). 이 문서의 표는 그 출력에서 옮기고 표시용으로 반올림했습니다.
3. 입력 기록의 `state_paths_unrelocated_after` 칸에 넷 모두 한 줄(`D:\\VISSIM-merge\\k8_gate_trees\\codexhandoff\\b0\\frozen\\sdmpc31_a49981ff_20261026`)이 남았습니다. 입력 도구의 정규식이 경로를 80자에서 자르는데 FRZ_B0 경로가 그보다 길어 생긴 표시입니다(잘린 글은 FRZ_B0 경로의 앞부분, 경로 바꿈 수 obs 1·run 6·frozen_other 0) [실행].
4. LOG 의 "11:20 KST — COMPARE_RULE_B" 항목 머리 시각은 어림값이며 실제로는 11:19 무렵에 썼습니다.

## 7. 이 관문이 알려 주지 않는 것 [추론]

- 준비 결정(T=1–750, no-control)은 시험하지 않았습니다. B 런은 이 결정도 codex 어댑터로 돕니다.
- T=900 하나는 뒤 결정의 짐을 대표하지 않습니다(A1: T=900 400.7 s, 평균 520.5 s, 최대 771.5 s). 뒤 결정의 최대는 B 런에서만 봅니다.
- 재생 상태는 V-A(우리 러너) 기록입니다. B 런의 T=900 상태는 codex 러너·codex 준비 결정이 만들어 바이트가 다릅니다(예: V-A 에는 `vsl_cohorts_000750.json` 이 없음).
- 다른 세션 VISSIM·TD3 학습이 도는 동안 잰 시간입니다.
- 64cf-s29 로 맞춘 D 부류 계수와 64cf 유도 codex 계약 11개는 그대로입니다(D-K9-89 ②). 결정이 끝까지 돈다는 것은 그 뜻이 v3c3 에 맞는다는 근거가 아닙니다.

## 8. 다음 (이 단계 밖)

- BRuns 단계: PRE_B §1 그대로 v3c3-s31 → s41 → s43, 한 번에 하나, 결과 뿌리 `D:/VISSIM_runs/20261026_codex_b_v3c3/s<seed>`. [실행 11:42] 다른 세션 VISSIM PID 29264 가 아직 돕니다 → 인계 러너는 VISSIM 이 있으면 발사를 거부합니다(`run_closedloop3000.ps1:170-178`) → 끄지 않고 기다려야 합니다(최대 12 h).
- B 런 뒤 분석은 COMPARE_RULE_B §7.5 차례로, 고정한 사본만 씁니다. LDP 신호 실행 대조는 "못 냄" 으로 이미 적었습니다(사용자가 다른 근거를 원하면 따로 물을 일).
- 디스크 [실행 11:42]: C 29.1 GB, D 253.9 GB(런당 약 7.3 GB 어림).

## 9. 지킨 것

- VISSIM·cscript 띄움 0, B 폐루프 0, kill 0(남의 것도 내 것도; 재생 상한 7,200 s 는 닿지 않음), 커밋·푸시 0, GWT8·`D:/VISSIM-merge/frozen/*`·인계 사본·런 폴더·Y: 쓰기 0(GWT8 의 Ω635 파일과 런 폴더는 읽기만), sealed/·봉인 시드 0, 금지 시험 0. FRZ_B0 에는 재생의 캐시 106개만 생김(§5).

## 10. 파일 (sha256) [실행]

| 파일 | sha256 |
|---|---|
| `SP/codex_handoff/b/GATE1_RULE.md` | `766c57376c9a78e154fca93c8bbaafe6887575b6ad38d747c43198de267fc5e0` |
| `SP/codex_handoff/b/COMPARE_RULE_B.md` | `f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c` |
| `SP/codex_handoff/b/PINS_B.sha256` | `5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804` |
| `W1/gate1_summary.json` (r1) / `W1/gate1_summary_r2.json` | `2f8742dbdbeaf5b1c79b39bc34fd50a44b631e0b31f88df84567bd71b89b515f` / `ea27c492e54cc2547433e507abdf4517cc0f79593c6c1b875943f5672241ac6b` |
| `W1/gate1_tables_r2.md` | `398b20492f971dc4a5a1e4fc76cb2c1134ae75e9b8d48d713522b612fa9c48ab` |
| `W1/g1_summary_r2.py` / `W1/g1_tables.py` | `520bb2b99a3cda8fc637572cbcbf80e735302ab3eb338ee0d3fd2014b054b5f5` / `7b91496aea61568e1c8e217a8e5b65058b6ed39430c7aeb9d7bce5ee1cb16007` |
| `W1/queue_g1.state.txt` / `W1/launch_receipts.log` | `e80564158462d71888fb47f1bf88719cae45589c428c07ead2290c25b451bbc8` / `e94ceb39c8c39dda0f9ec1a5c8cf8886270bf685372bd6991046a2a969f28642` |
| `G1/freeze_verify_after.txt` | `983da4e3c3a9f908df708a30aac90afcb9de9da136627dc4f68c443932934199` |
| 명령 CSV R1 / R2 / R3 / R4 (`G1/out/g1R*/…/files/decisions_…/action_000900.csv`) | 앞 16: `c130fde6b115567d` / `ccae782398957a13` / `a2e32a11df7f597e` / `c130fde6b115567d` |
