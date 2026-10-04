# T5 보고서 (REPIN_PLAN §5.5-4): v3c1 R-obs 위 결정 재생

- 대상: 재핀 커밋 5323faa4(브랜치 `claude/repin-v3c1-20260928`)
- 동결 트리 FRZ: `D:/VISSIM-merge/frozen/sdmpc31_5323faa4_202609281442`(FREEZE.json sha 472406…, 10275 파일)
- R-obs: `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31`
  - no-control + obs150, seed 31, 9000 s, 결정 61개
  - launch_plan: controller = warmup_controller = no-control
- 배포 튜닝: FRZ `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`, sha256 33027258…6365
  - 이 sha는 `git show 5323faa:…` blob, launch_plan.json의 tuning.sha256과 같습니다 [실행].
  - `adapter.sdmpc_control_blocks` 3, `sdmpc_derivatives` tangent-v1, `freeway_follower.vsl_set` [80,90,100,110], `max_vsl_step` 40
- 표기: [실행] 이번에 돌려 확인 / [읽음] 파일에서 읽음 / [추론] 확인하지 않은 판단
- 최종 갱신: 2026-09-28 22:35

## 0. 결론

| 항목 | 판정 |
|---|---|
| (1) test_g1_frame | **PASS**. R-obs state_000900으로 1 passed. FW_E 720대, FW_W 455대. 31/21셀 binning 합이 맞고 부모 소속 불일치 0 [실행] |
| (2) 기록된 결정 61개 재생 | **61/61 IDENTICAL**(`--tuning`을 쓰지 않는 compare). ps1 자체 판정(`--tuning`)도 61/61 IDENTICAL, exit 0 [실행] |
| (2) 결정적 카운터 | action JSON의 정수 리프 37,551개가 61/61 전부 같습니다. CSV 바이트, derived, 제어 필드도 61/61 같습니다 [실행] |
| (2) 단서 | action JSON 전체 비트 동일은 **59/61**입니다. 4050·4500에서는 예측 진단 필드 4개가 1–2 ulp 다릅니다. 원인은 `PYTHONHASHSEED`에 따라 합산 순서가 바뀌는 코드(`vendor/NumSim-mine/src/models/state.py:1306`)입니다. 해시 시드를 고정한 재생 5회로 확인했습니다(§4) [실행]+[읽음] |
| (3) VSL 행동 집합 | R-obs에는 **기록된 SDMPC 결정이 0개**입니다(61개 모두 NoControl). 그래서 같은 R-obs 상태에서 배포 컨트롤러 wu-link와 배포 튜닝으로 SDMPC 결정을 새로 만들었습니다(반사실 재생, 4개 상태, 5회). 결과는 **전부 통과**입니다. 쓰인 VSL, CSV VSL 66행, 미래 블록 1·2 계획 VSL이 모두 {80,90,100,110} 안에 있습니다. 결정 metadata의 VSL 축 18개(블록당 6개 × 3블록)의 허용집합이 모두 정확히 {80,90,100,110}입니다. 같은 상태를 두 번 돌린 쌍(900, 4950)은 CSV 바이트, 목적함수 repr, 탄젠트 카운터가 같습니다 [실행] |
| (3) 한계 | 쓰인 블록 0 명령은 5회 모두 110이었습니다. 110 미만 값은 미래 블록 계획에서만 나왔습니다(2700·4950의 블록 1, FW_E 구역 머리 10, 100 km/h). "110 미만 명령을 CSV로 쓰는 경로"는 이번 T5에서 실행되지 않았습니다 |
| (4) 벽시계 | 무제어 재생의 어댑터 시간은 중앙 28.2 s(23.2–33.3)이고, ps1 한 단계 전체는 중앙 47.1 s입니다. SDMPC 재생의 어댑터 시간은 599.9–653.3 s입니다(§6) [실행] |

- 61개를 전부 돌렸습니다. 대체 규칙(900 s부터 150 s 간격, 최소 20개)은 쓰지 않았습니다. 19:13에 남은 52개의 예상 시간이 약 1.5시간이었고, 실제로 20:23에 끝났습니다.

## 1. 이어받기: 재사용한 것과 확인 방법

첫 시도(17:37)는 18:01쯤 세션 한도로 끊겼고 체인 프로세스도 함께 죽었습니다. A/chain.log 마지막 줄은 18:01:02 YIELD이고, 19:13 프로세스 목록에도 없었습니다 [실행].

| 첫 시도 산출 | 처리 | 확인 방법 |
|---|---|---|
| A/T000001…T001200 요약 9개와 재생 폴더 | **재사용** | 9개 모두 ps1 로그에 다음이 있습니다: `FREEZE_VERIFIED sha=472406… files=10275 head=5323faa4…`, `REPLAY_START … controller=no-control root=<FRZ>`, `--tuning-json <FRZ>\…\config_n31_v2.json`. 비교는 exit 0, IDENTICAL이고, 휘발성이 아닌 차이는 0개입니다. `t5_aggregate.py`로 다시 집계해 확인했습니다 [실행] |
| g1_frame_pytest.txt, g1_frame_numbers.json | 수치는 재사용하고 시험은 **다시 돌림** | 옛 출력에는 환경변수가 없었습니다. 명령, HEAD, 상태 sha, 시험 파일 sha를 적으면서 다시 돌렸습니다(`g1_frame_pytest_rerun.txt`) |
| tree_check_before.json(17:42) | 기준선으로 재사용 | 19:17에 다시 확인했습니다: worktree HEAD 5323faa4, `git status --porcelain` 빈 값, 무시 목록은 `__tangentcache__/`(60개, 최신 12:23)뿐 |
| t5_chain_a.py, t5_common.py | 그대로 사용 | 읽어서 확인했습니다: FRZ 도구 사용, BELOW_NORMAL, `NUMBA_CACHE_DIR=nbc_p10`, RW_* 제거, 남의 재생 python이 돌면 대기, batch-2 체인이 살아 있으면 40 s 양보 |
| t5_chain_b.py, t5_aggregate.py | **고쳐서 사용** | ① 탄젠트 트레이스는 `trace.workers[]` 아래에 있습니다(`evaluation/controllers/sdmpc_tangent.py:119-121,213`). 옛 비교는 `(None, None)`끼리 비교해 늘 "같음"이었습니다. 시간 키를 뺀 트레이스 전체를 비교하게 바꿨습니다. ② 튜닝 sha를 기록합니다. ③ batch-2 체인 생존 대기를 45분 상한으로 두었고, 재기동 뒤에는 0으로 두고 재생마다 양보하게 했습니다(§7) |

## 2. (1) test_g1_frame [실행]

- 명령(worktree에서 실행, 캐시를 쓰지 않음):
  `N31_G1_STATE=<R-obs>\decisions_sdmpc31_v3c1_nc_s31\state_000900.json PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/tests/test_n31_initialize.py::BinningTests::test_g1_frame -v`
- 결과: `1 passed in 0.47s`, EXIT 0(19:19:56). 실행 조건은 다음과 같습니다.
  - HEAD 5323faa4
  - 시험 파일 sha a8faec8a…(FRZ의 같은 파일과 같음)
  - 상태 sha 095215e9…
- 시험 내용 [읽음]
  - 위치: `test_n31_initialize.py:99-104`, `check_frame :58-71`.
  - T5 가이드 서술은 `PLANT_PORTING_GUIDE.md:597`에 있습니다. 과제 문구와 계획서의 `:579`는 5323faa에서 L6 G1 발사 코드 블록의 끝(```)을 가리킵니다 [읽음].
  - 도로마다 31/21셀 수를 확인합니다.
  - 시작 이전 차량 제외가 두 해상도에서 같은지 확인합니다.
  - binned 합 = 체인 차량 − 제외 차량인지 확인합니다.
  - 21셀 부모마다 31셀 자식들의 차량 집합이 같은지 확인합니다.
- 수치: `g1_frame_numbers.json`
  - frame_000900 sha 2d4ee3bb…, 3172대
  - geometry: v3c1 NC s31 관측 geometry, sha 8752f0cd…

| 도로 | 체인 차량 | 시작 전 제외(31/21) | binned 31/21 | 부모 소속 불일치 |
|---|---|---|---|---|
| FW_E | 720 | 0 / 0 | 720 / 720 | 0 |
| FW_W | 455 | 0 / 0 | 455 / 455 | 0 |

## 3. (2) 기록된 61개 결정 재생 [실행]

- 절차: 결정마다 한 번에 하나씩, BELOW_NORMAL로 돌렸습니다. `NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_p10`입니다.
  1. FRZ `make_replay_state_v2.py prepare <R-obs decisions> T A/T<T>`
  2. FRZ `replay_decision_n31.ps1 -ReplayDir A/T<T>`
     - Root는 run_provenance의 FRZ이고, FREEZE를 다시 검증합니다.
     - 컨트롤러는 launch_plan에서 가져옵니다(no-control).
     - 튜닝은 런의 config_n31_v2.json입니다.
     - ps1의 compare(`--tuning` 사용) 결과는 `replay_compare_ps1.json`에 따로 남겼습니다.
  3. FRZ `make_replay_state_v2.py compare A/T<T>`(`--tuning` 없음): **T5 판정**
  4. 원본과 재생의 action JSON 전체 경로 diff, CSV 바이트, 정수 리프 비교(`t5_a_stats.py`)
- 결과(`t5_a_stats.json`, `t5_aggregate.json`)

| 검사 | 결과 |
|---|---|
| 비-tuning compare verdict | IDENTICAL 61/61 |
| derived / action_csv / action_controls / action_contract | 각각 True 61/61 |
| objective | None 61/61. SDMPC가 돌지 않은 결정이라 정의상 None입니다(`make_replay_state_v2.py:287-299`) |
| ps1 자체 판정(`--tuning`) | IDENTICAL 61/61, exit 0 61/61. 무제어는 전부 110이라 알려진 all-110 문제(`:234-242`)가 걸리지 않습니다 |
| FREEZE_VERIFIED / Root | 61/61, 모두 FRZ |
| metadata | NoControl / no-control 61/61, tuning_name `sdmpc31_v2_repin_base_20260924` |
| 쓰인 VSL | JSON과 CSV 모두 {110}, VSL 66행, 미터 8행 |
| CSV 바이트 / 정수 리프 | 61/61 같음 / 37,551개 전부 같음 |
| float 리프 | 186,507개. 휘발성이 아닌 차이는 아래 7개뿐 |

- 휘발성 필드(결정마다 7개)
  - `metadata.decision_wall_sec`, `metadata.prediction_wall_sec`, `prediction.wall_sec`
  - `(metadata.)run_provenance.inputs.state_json.{path,sha256}` 두 쌍. prepare가 만든 격리 상태 사본의 경로와 sha입니다.
- 휘발성이 아닌 차이(모두 `prediction` 진단 필드)

| T | 필드 | 원본 | 재생 | ulp |
|---|---|---|---|---|
| 4050 | `state_summary`와 `calibrated_state_summary`의 `off_ramp_storage_veh` | 78.69970870217517 | 78.69970870217519 | 1 |
| 4050 | `terminal_features.ramp_vehicles` | 179.79145106598813 | 179.79145106598816 | 1 |
| 4050 | `terminal_features.stopped_vehicles` | 1894.268921094536 | 1894.2689210945364 | 2 |
| 4500 | `state_summary`와 `calibrated_state_summary`의 `off_ramp_storage_veh` | 82.81629937866342 | 82.81629937866343 | 1 |

- compare는 `CONTROL_FIELDS`(`make_replay_state_v2.py:61-62`), CSV 바이트, derived만 봅니다(`:274-286`). 그래서 위 차이는 판정에 들어가지 않습니다 [읽음].

## 4. ulp 차이의 원인: 해시 시드 탐침 H

- 코드 [읽음]
  - `vendor/NumSim-mine/src/models/state.py:1305-1311`의 `off_ramp_storage_occupancy_veh`는 `set(net.off_ramp_storage_link.values())`(문자열 집합)을 순회하며 float를 더합니다.
  - 이 합은 `summarize_model_state`(`evaluation/controllers/vissim_stackelberg_adapter.py:10503,10520`)로 들어가 보정(`:10656-10670`)과 terminal features(`:10755`, `:10797`)로 퍼집니다.
- `PYTHONHASHSEED`는 어디에도 고정되어 있지 않습니다 [실행]
  - R-obs run_provenance env(RW_* 17개)에 없습니다.
  - FRZ `tools/`, `diagnostics/sdmpc_n31_20260924/`, `scenario/`를 grep하면 0건입니다.
- 실험 [실행]
  - 4050을 A와 같은 FRZ 재생으로 돌리되, 환경에 `PYTHONHASHSEED`를 넣었습니다(`t5_chain_h.py`, `H/`).
  - 5회 모두 FREEZE_VERIFIED, exit 0, IDENTICAL이었습니다.

| 시드 | off_ramp_storage_veh | 원본 대비 휘발성 외 차이 | CSV sha |
|---|---|---|---|
| 0 (1회) | …17517 | 0 | 4796faec… |
| 0 (2회) | …17517 | 0 | 4796faec… |
| 1 | …17517 | 0 | 4796faec… |
| 2 | …17519 | 4 필드(A와 같은 값) | 4796faec… |
| 3 | …17517 | 0 | 4796faec… |

- 해석
  - 값은 해시 시드의 결정적 함수입니다. 원본 런은 시드 0·1·3과 같은 순서 계열이고, A의 재생은 시드 2와 같은 계열이었습니다.
  - A에서 본 7개 차이는 이 기전 하나로 모두 설명됩니다.
- 파급 [읽음]
  - 같은 함수가 다음에도 들어갑니다: `state.py:1258`(총 물리 차량), wu-link 시스템 목적함수 `vendor/NumSim-mine/src/controllers/wu_distributed.py:809`, `leader.py:777`.
  - SDMPC 결정에서 이 순서가 목적함수의 마지막 자리까지 닿는지는 확인하지 않았습니다[추론].
  - §5의 두 쌍(r1/r2, 둘 다 무작위 시드)은 목적함수 repr이 같았습니다. 하지만 H에서도 시드 5개 중 4개가 같은 순서 계열이었으므로, 이것만으로 면역을 증명하지는 못합니다.

## 5. (3) SDMPC 결정의 VSL 행동 집합 (B) [실행]

- 왜 반사실 재생인가
  - R-obs의 61개 결정은 모두 NoControl이라 SDMPC VSL이 없습니다(§3).
  - 그래서 같은 상태 위에서 배포 기본 컨트롤러 wu-link로 결정을 새로 만들었습니다(`tools/launch_plan.py:290` 기본값).
- 명령: `replay_decision_n31.ps1 -ReplayDir B/T<T>_r<n> -Root D:/VISSIM-merge/sim3-n31-v3c1 -Controller wu-link`
- Root를 worktree로 둔 이유
  - SDMPC는 `<Root>/evaluation/controllers/__tangentcache__`에 코드 캐시를 씁니다(`sdmpc_tangent_runtime.py:76`). FRZ에는 쓰면 안 됩니다.
  - worktree는 FREEZE 표 10275 파일과 바이트 동일합니다(20:24, 22:16, 22:28 세 번 확인).
  - ps1은 provenance 경로를 worktree로 재기준합니다(`REBASE`, `ROOT_NOT_FROZEN`). 튜닝 sha 33027258…은 FRZ와 같습니다.
  - 새로 생긴 캐시 32개는 끝난 뒤 옮겼습니다(§7).
- 이전 action은 기록된 무제어 action(T−150)입니다.
  - 그래서 `vsl_cohort_initialization`의 명령은 전부 110이고 VSL 축의 기준값도 110입니다. 폐루프 첫 SDMPC 결정(900)과 같은 조건입니다.
- 상태 선택: R-obs 본선 평균속도 기준
  - 900: 제어 시작
  - 2700: 혼잡 시작, 71 km/h
  - 4950: 정점, 66 km/h
  - 900과 4950은 결정성 확인을 위해 두 번씩 돌렸습니다.

| T/회 | 시작–끝 | 어댑터 s | 결정 s | 쓰인 VSL(JSON / CSV 66행) | 미래 블록 1 / 2 VSL | VSL 축 허용집합(18축) | Ω held→selected |
|---|---|---|---|---|---|---|---|
| 900 r1 | 21:13:15–21:23:26 | 605.1 | 594.2 | {110} / {110} | {110} / {110} | 전부 {80,90,100,110} | 354.929→348.367 |
| 900 r2 | 21:32:51–21:42:58 | 599.9 | 588.9 | {110} / {110} | {110} / {110} | 전부 {80,90,100,110} | 354.929→348.367 |
| 2700 r1 | 22:04:06–22:15:07 | 653.3 | 642.6 | {110} / {110} | {100,110} / {110} | 전부 {80,90,100,110} | 513.458→504.545 |
| 4950 r1 | 21:52:01–22:02:26 | 618.2 | 607.3 | {110} / {110} | {100,110} / {110} | 전부 {80,90,100,110} | 437.697→432.343 |
| 4950 r2 | 22:16:36–22:27:06 | 623.0 | 612.3 | {110} / {110} | {100,110} / {110} | 전부 {80,90,100,110} | 437.697→432.343 |

- 공통 결과(5회 모두)
  - metadata: WuDistributedController / wu-link, `sdmpc_active` True, prediction ok, `sdmpc-central-pfo-cap/v3`, `best_observed_feasible_sdmpc`, 미터 8행
  - VSL 축: 블록 0·1·2마다 6개(FW_W·FW_E × 구역 머리 0/5/10), 기준값 110, fd 10/110. 블록 0의 허용집합은 6축 모두 정확히 [80,90,100,110]입니다. 계획서 §5.2(`sdmpc.py:333-341`)의 기대 "{70..110} → {80..110}"과 맞습니다.
  - 미래 블록 1의 100: 2700과 4950에서 `FW_E`, `FW_E__seg10…seg14`(FW_E 구역 머리 10)입니다. 블록 0만 쓰이므로 CSV에는 나오지 않습니다(`sdmpc_sequence.py:1-6`) [읽음].
  - ps1 자체 판정은 모두 DIFFERENT(exit 2)입니다. 비교 상대가 기록된 무제어 결정이므로 구성상 당연합니다. derived는 True입니다.
  - ps1의 `--tuning` action_contract는 이번에는 ok였습니다. 쓰인 값이 전부 110이었기 때문입니다. 110 미만 명령이 쓰이면 이 검사는 실패합니다(알려진 문제, `REPIN_V3C1_REPORT.md:219`). 판정은 위의 허용 집합 소속으로 했습니다.
- 결정성(같은 상태 r1 대 r2, `t5_aggregate.json` determinism)

| T | CSV 바이트 | 목적함수 repr(objective, held) | derived | 탄젠트 호출 / 카운터(시간 키 제외 수치 리프) | JSON 차이 50개의 내역 |
|---|---|---|---|---|---|
| 900 | 같음 | 같음 | 같음 | 2 / 860개 전부 같음 | 시간 34, 경로·sha 6, 토큰 10 |
| 4950 | 같음 | 같음 | 같음 | 2 / 864개 전부 같음 | 시간 34, 경로·sha 6, 토큰 10 |

- 토큰(`frozen_context_token`, `reference_response_token`, `response_token`)과 `request_sha256`은 pickle 바이트의 sha입니다.
  - 코드가 스스로 "Pickle is a process-local exact-value key, not a portable content hash"라고 밝힙니다(`area_follower_objective.py:436`; 토큰 `:453-454`, `:546-549`; `sdmpc_tangent.py:55-57`).
  - 프로세스마다 다른 것이 설계이므로 휘발성으로 분류했습니다 [읽음].

## 6. (4) 재생 벽시계 [실행]

- 무제어 61개(`replay_run.json` wall_sec, 어댑터 프로세스)
  - 23.2 / 사분위 25.8 / 중앙 28.2 / 사분위 29.3 / 최대 33.3 s. 합 1678.9 s
- ps1 한 단계 전체(FREEZE 10275 파일 재검증 + 어댑터 + compare)
  - 41.7 / 중앙 47.1 / 53.3 s. 합 2852.8 s(47.5분)
  - prepare 약 1 s와 비-tuning compare 약 1 s는 따로 듭니다.
- 결정 자체(`metadata.decision_wall_sec`)
  - 재생: 중앙 26.96 s(21.95–31.82)
  - 원본 런: 중앙 22.98 s(19.26–26.10)
  - 비율 중앙 1.16입니다. BELOW_NORMAL과 batch-2 탐침과의 교대 때문으로 봅니다[추론].
- 결정별 값: `t5_a_stats.json`의 rows[].adapter_wall / step_sec / decision_wall_replay / decision_wall_recorded
- SDMPC 반사실 재생(§5 표)
  - 어댑터 599.9–653.3 s
  - 900은 폐루프 G1b의 결정 900(605.8 s, `PLANT_PORTING_GUIDE.md:584`)과 비슷합니다.
  - 900 r1과 r2는 batch-2의 SDMPC 재생과 동시에 돌았습니다(§7). 벽시계 비교에는 4950·2700 쪽이 깨끗합니다.
- 체인 경과
  - A: 17:43–18:01(9개), 19:20–20:23(52개, 3801 s, batch-2 대기·양보 포함)
  - H: 20:25–20:34(5회)
  - B: 21:13–22:27(5회, batch-2 SDMPC와 교대)

## 7. 트리·런 폴더 무결성과 정리 [실행]

| 시점 | FRZ = FREEZE 표 | FRZ 캐시 | worktree = FREEZE 표 | worktree 캐시 | R-obs 런 폴더 |
|---|---|---|---|---|---|
| 17:42 before | 예 | 119 | 예(0/0/0) | 60 | 618 |
| 20:24 before_B | 예 | 119, 목록 같음 | 예 | 60, 목록 같음 | 618, 크기·mtime 같음 |
| 22:16 after_B | 예 | 119 | 예 | **92**(+32 `.mcode`, 21:13:38–42) | 618 |
| 22:28 final(정리 뒤) | 예 | 119, 목록·mtime 같음 | 예 | 60, 목록·크기·mtime이 17:42와 같음 | 618, 17:42와 같음 |

- 정리: B가 만든 `__tangentcache__/*.mcode` 32개는 지우지 않고 `t5/moved_tangentcache/`로 **옮겼습니다**(목록 `moved_tangentcache_list.csv`).
- 22:28 worktree 상태: HEAD 5323faa4, `git status --porcelain` 빈 값, `--ignored`는 기존 `__tangentcache__/`뿐, `__pycache__`와 `.pytest_cache`는 없습니다(`worktree_after.txt`).
- FRZ에는 한 번도 쓰지 않았습니다. 캐시 119개의 목록과 mtime이 17:42와 같습니다.
- 금지된 동작은 하지 않았습니다.
  - VISSIM, cscript, 워치독, ps1 시험을 시작하거나 멈추지 않았습니다.
  - seed 37, RM 팔, 봉인 시드 59/61/67 산출은 열지 않았습니다.
- 제 프로세스 정리
  - 21:11: 대기 중이던 제 드라이버와 B 체인을 멈췄습니다. B 재생을 하나도 시작하기 전이었고, B에 양보가 없어 batch-2를 굶길 수 있었기 때문입니다. `t5_driver2.py`로 다시 띄웠습니다.
  - 제 로그를 잡고 있던 제 `tail` 3개(만료된 모니터 1, 첫 시도 2)를 끝냈습니다.
- **batch-2와 동시 실행 두 번(경쟁)**
  - 두 체인 모두 프로세스 목록을 폴링해 유휴를 판단합니다. 그래서 상대 재생이 끝난 같은 초에 둘 다 시작했습니다.
  - 제 900 r1은 batch-2 `sdmpc_b2_s1_T3600`(21:13:15–21:23:13)과 겹쳤습니다.
  - 제 900 r2는 batch-2 `sdmpc_b2_s0e_T1800`(21:32:51–21:41:37)과 겹쳤습니다.
  - 두 경우 모두 SDMPC끼리, 8+8 워커가 20 논리 CPU에서 돌았습니다. 결과 내용에는 영향이 없습니다(결정적). **양쪽 벽시계는 오염**입니다. 그런데도 batch-2의 단독 N3 단계(544.9, 529.8 s)와 겹친 단계(597.6, 525.9 s)는 큰 차이가 없었습니다.
  - A도 61개 중 24개가 batch-2의 약 30 s 탐침과 시간이 겹쳤습니다(무제어 계열).

## 8. 남은 문제와 권고

1. **해시 시드 비결정성**(§4)
   - `state.py:1306`의 `set(...)` 순회 합산 때문에, 같은 입력의 결정 재생이라도 action JSON이 프로세스마다 ulp 수준으로 다를 수 있습니다.
   - 지금의 compare는 이 필드를 보지 않아서 IDENTICAL입니다.
   - SDMPC 재생의 `objective` 검사는 `repr` 완전 일치입니다(`make_replay_state_v2.py:295-298`). 그래서 혼잡 상태에서 이 기전이 목적함수에 닿으면 거짓 DIFFERENT가 날 수 있습니다[추론].
   - 권고(코드 변경이라 이번에는 하지 않음): `sorted(set(...))`로 순회하거나, 러너와 재생 ps1에서 `PYTHONHASHSEED=0`을 고정합니다.
   - 확인 실험 제안: 4050에서 SDMPC 재생을 시드 0과 2로 한 번씩(약 20분).
2. **SDMPC 쓰기 경로에서 110 미만 명령은 실행되지 않았습니다**(§5)
   - 5회 모두 블록 0이 110이었습니다.
   - 110 미만 명령이 CSV와 VSL 행(DSD 번호 80–100)으로 나가는 경로와, 그때 ps1 `--tuning` action_contract가 실패하는 알려진 문제는 이 T5로 확인되지 않았습니다. 폐루프 SDMPC 런(J1)에서 확인해야 합니다.
3. **action_contract**(`make_replay_state_v2.py:234-242`)
   - 계획대로 "허용 집합 소속" 검사로 바꾸지 않으면, SDMPC 런의 T5에서 ps1 판정이 쓸모없습니다. 이번 B는 스크래치 스크립트에서 소속 검사를 했습니다.
4. **재생 동시성**
   - 워크플로 사이의 "한 번에 하나"를 프로세스 목록 폴링으로 지키면 같은 초 경쟁을 막지 못합니다(§7).
   - 공용 잠금 파일이나 이름 있는 뮤텍스를 권합니다.
5. 관찰만 한 것
   - B의 metadata `held_objective`(예 354.929)와 progress 로그의 `held_objective`(351.261)는 값이 다릅니다. 두 값의 정의가 다른 것으로 보이며 조사하지 않았습니다[추론].

## 9. 파일 (모두 `…/scratchpad/v3c1-p10/t5/`)

- 보고서: `T5_REPORT.md`
- (1): `g1_frame_pytest_rerun.txt`(이번), `g1_frame_pytest.txt`, `g1_frame_numbers.json`, `g1_frame_numbers.py`
- (2)(4): `A/T<T>.summary.json`(61), `A/T<T>/`(재생 폴더, `replay_compare.json`은 비-tuning 판정, `replay_compare_ps1.json`은 ps1 판정), `A/chain.log`, `t5_a_stats.json`, `t5_aggregate.json`
- H: `H/T004050_h<seed>_r<n>.summary.json`, `H/chain.log`, `t5_chain_h.py`
- (3): `B/T<T>_r<n>.summary.json`(5), `B/T<T>_r<n>/`, `B/chain.log`
- 무결성: `tree_check_{before,before_B,after_B,final}.json`, `worktree_before.txt`, `worktree_after.txt`, `moved_tangentcache/`, `moved_tangentcache_list.csv`
- 스크립트: `t5_common.py`, `t5_chain_a.py`, `t5_chain_b.py`, `t5_aggregate.py`, `t5_a_stats.py`, `tree_check.py`, `t5_driver.py`, `t5_driver2.py`, `driver.log`
