# 도시 묶음 2 — 단계 0 보고 (준비·기준선 재현)

- 작성: 2026-09-28 15:50. 계획: `B/BATCH2_PLAN.md` §4.0, §6.2, §7 행 0.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 소스는 한 줄도 고치지 않았습니다. 커밋·push·rebase도 하지 않았습니다.
- 표기
  - **[실행]**: 이번에 직접 돌리거나 계산한 값입니다.
  - **[읽음]**: 파일에서 읽은 값입니다.
  - **[추론]**: 직접 증거 없이 끌어낸 판단입니다.
- 약어
  - B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`
  - S0 = `B/impl/stage0`, H = `B/harness`
  - W = b2 트리, OLD = `D:/VISSIM-merge/sim3-n31-urban`(cf3ce37)
  - R-obs-b = `D:/VISSIM_runs/20260925_sdmpc31_v3b/sdmpc31_v3b_nc_s31b`, S1 = `…/sdmpc31_v3b_b1u13_s31`

---

## 0. 결론

**멈춤 규칙은 하나도 걸리지 않았습니다.** 단계 1(U4-0)로 넘어가도 됩니다.

| 확인 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| 워크트리·브랜치 (§3) | HEAD `cf3ce37`, 상태 깨끗함, OLD와 추적 파일 10,256개(2.13 GB)가 바이트 단위로 같음 | [실행] §1 |
| 하네스 매개화 (§3 함정) | 트리를 필수 인자로 받고, 모든 산출물에 트리·HEAD·어댑터 sha를 기록함. 남은 하드코딩 트리 경로 0 | [실행] §2 |
| 기존 스위트 (§4.0-2) | n31·obs150·도구·생성기 `--check` 15개는 전부 통과. **diagnostics 11개 가운데 5개 파일은 이전부터 실패합니다.** 원인은 트리에 없는 과거 run 입력이며, 이식형 fixture를 복원하면 핵심 2개 파일이 통과합니다 | [실행] §4 |
| T3 기준선 (§6.2) | A1 6.361 … C 11.011. 일곱 지표가 묶음 1 값과 **부동소수까지 같음** | [실행] §5.1 |
| 세 경로·FD (§6.2) | 캐시·반복 차이 0, no_agg 5.7e-14, AD 대 스칼라 0, 연속 대 정확 0.01299. FD 세 쌍이 묶음 1과 비트 동일 | [실행 재사용 확인] §5.2 |
| R-obs-b 61상태 재생 | U1+U3 61/61, 기본 튜닝 61/61 모두 IDENTICAL. 한 스텝 포착값이 묶음 1 포착과 필드 단위로 같음 | [실행] §5.3 |
| S1 1800·6300 자기 설정 재현 (§6.1 (c), `[검토 C-12]`) | 두 상태 모두 녹색·offset·목적값·tangent 계수가 기록과 같음. `action_contract`만 다름(알려진 VSL 100 혼재) | [실행 재사용 확인] §6 |
| 206.53 fixture 목록 (§4.0-4) | 27개 파일, 69줄 | [실행] §7 |
| 시간 기준선 (§4.0-5) | 결정론 계수와 벽시계를 기록함 | [실행] §8 |
| 금지 대상 무변경 | 런 폴더 두 곳, frozen, OLD 모두 11:25 이후 새 파일 0개. VISSIM·cscript는 시작하거나 죽이지 않음 | [실행] §9 |

- 넘길 문제 세 가지가 있습니다(§10).
  1. "기존 스위트 전부 통과"는 문자 그대로는 어느 체크아웃에서도 성립하지 않습니다. 이후 단계의 기준은 "이 기준선 대비 새 실패 0"으로 읽기를 제안합니다.
  2. 테스트 4개가 추적 파일을 다시 씁니다. 하네스가 이것을 기록한 뒤 되돌립니다.
  3. 계획 §3의 브랜치 이름은 `claude/urban-b2-20260928`인데, 실제 브랜치는 `claude/urban-batch2-20260928`입니다.

---

## 1. 워크트리·브랜치 [실행]

- `git -C W rev-parse HEAD`는 `cf3ce3740705959a89fd470a3f37cc55c31ff68a`입니다. 브랜치는 `claude/urban-batch2-20260928`이고, `git status --porcelain`은 0줄입니다.
  - 이 워크트리는 지시대로 재사용했고 다시 만들지 않았습니다. 워크트리 목록에서 `D:/VISSIM-merge/sim3-n31-urban-b2 cf3ce37 [claude/urban-batch2-20260928]`을 확인했습니다.
  - 계획 §3:139는 브랜치 이름을 `claude/urban-b2-20260928`로 적었습니다. 실제 이름은 중단된 시도가 만든 것이고, 과업 지시가 이 이름을 가리킵니다.
- **OLD와 같은 입력인지** 네 가지로 확인했습니다.
  - 트리 객체가 같습니다: W와 OLD 모두 `HEAD^{tree}` = `1834922a…`입니다.
  - 추적 파일을 바이트로 비교했습니다(`S0/redo/tree_bytes_compare.py`, `…json`). 10,256개, 2,132,700,698 B 가운데 다른 파일 0개, 빠진 파일 0개입니다.
  - 무시(ignored) 파일 목록을 비교했습니다(`S0/redo/ignored_{old,b2}.txt`).
    - OLD에는 `__pycache__` 3곳과 `evaluation/controllers/__tangentcache__/`만 있습니다.
    - W에는 `__tangentcache__`와 테스트가 만든 `.review-fixtures/`만 있습니다.
    - 따라서 OLD에만 있는 데이터 입력은 없습니다.
  - 어댑터 sha256은 두 트리 모두 `2215d163…`입니다. 튜닝 sha는 `config_n31_v2_urban_b1_u1u3.json` `f88d05f1…`(S1 런 provenance의 frozen 튜닝 sha와 같음 [읽음]), `config_n31_v2.json` `82688d2f…`입니다.
- 결론: b2 트리에서 재생한 결과는 cf3ce37(OLD) 트리에서 재생한 결과와 같은 입력에서 나온 것입니다. 계획 §6.1 (c)의 "cf3ce37 트리로 먼저 재현" 요구를 이것으로 충족한 것으로 봅니다.

---

## 2. 하네스 매개화 (H) [실행: diff]

- **원본 대비 바뀐 곳은 경로와 provenance뿐입니다.** 줄바꿈 무시 `diff`로 확인했습니다.
  - `_prov.take_tree`는 `--tree`가 없거나 코드 트리가 아니면 `HARNESS_REFUSED`로 멈춥니다. `tree_provenance`는 트리 경로·HEAD·브랜치·dirty 수·status sha·어댑터 sha를 산출 JSON에 넣습니다.

| 하네스 | 원본 | 원본과의 차이 |
|---|---|---|
| `b1_capture.py` | `urban-b1d/b1_capture.py` | 트리·출력 루트 필수 인자, provenance·튜닝 sha 기록 |
| `t3_arms.py` | `urban-sc7/t3_sc7.py` | 팔·쌍을 명시 인자로 받음, 이동 블록(5) bootstrap 추가(§6.4 `[검토 C-18]`). 지표 정의는 같음 |
| `check_paths.py` | `urban-sc7/check_paths.py` | 트리·출력 필수, provenance 기록. **오늘 한 줄 수정**(아래) |
| `livecheck.py` | `urban-b2/livecheck.py` | 트리·출력 필수, provenance 기록 |
| `u6_capture.py` | `urban-b2/u6/u6_capture.py` | 트리·출력 필수, NUMBA `nbc_b2i`, provenance 기록 |
| `cfw/cf_driver.py`, `cfw/capture_alt.ps1` | `sc109-diag/cfw/*` | root는 원래 필수 인자, provenance 기록, 캐시 경로 |
| `alt_replay.ps1` | `xreplay/alt_replay.ps1` | NUMBA 캐시만 `nbc_b2i` |
| `sdmpc_replay.py`, `stage0_chain.py`, `run_suites.py`, `compare_captures.py`, `fixture_scan.py`, `analyze_stage0.py` | 중단된 시도에서 새로 쓴 것 | 내용을 읽고 확인한 뒤 재사용 |

- `grep`으로 H 전체를 확인했습니다. `sim3-n31-urban`을 하드코딩한 곳은 `_prov.py`의 `OLD_TREE` 상수 하나뿐이고, 어디서도 기본값으로 쓰이지 않습니다.
- **오늘 고친 하네스 네 가지** (모두 H 안, 코드 트리 밖)
  1. `stage0_chain.py`에 `--phases B1,B2,S`를 더했습니다.
     - 포착을 먼저 모두 돌리고, 스위트는 그 뒤에 따로 돌립니다.
     - 중단된 시도는 스위트를 포착과 **동시에** 돌렸습니다. 그 때문에 테스트가 추적 파일을 바꾼 동안 포착 6개(T900–1650)의 provenance가 `worktree_dirty_entries 1`로 기록됐습니다(§3).
  2. `run_suites.py`를 네 군데 고쳤습니다.
     - 스위트마다 `git status`를 앞뒤로 비교합니다. 테스트가 추적 파일을 바꾸면 diff를 `S0/tests/*_tracked_*.diff`에 남기고 `git checkout -- <파일>`로 되돌립니다(이 워크트리만).
     - diagnostics 11개 파일을 파일별로(`-rfE --tb=line`) 따로 돌립니다.
     - `test_sdmpc_spatial`은 numba 8스레드로 한 번 더 돌립니다.
     - summary를 새로 씁니다.
  3. `check_paths.py`: 어댑터가 886a014(cf3ce37에 병합)부터 모든 예외를 `decision_failure_report.run`으로 감쌉니다(`vissim_stackelberg_adapter.py:14061-14062`, `decision_failure_report.py:90-105`) [읽음].
     - 그래서 하네스의 `Captured` 정지가 `SystemExit(1)`이 되고 rc=1로 보였습니다. 중단된 시도의 `A_paths` rc=1이 이것입니다. 산출 JSON은 정지 전에 이미 쓰여 있었습니다.
     - 이제 `.error.txt`에 `Captured: captured`가 있고 산출 JSON이 있으면 `PATHS_OK`로 끝냅니다.
  4. 새 파일 `fixture_suites.py`: 이식형 fixture를 복원하고 diagnostics 시험을 다시 돌립니다(§4.3).

---

## 3. 중단된 시도(11:25–12:54) 산출물: 재사용한 것과 다시 한 것

**재사용 조건:** provenance가 W·`cf3ce37`·dirty 0·어댑터 `2215d163`일 것, 산출물이 완결될 것, 옛 트리 참조값과 대조될 것. 셋 다 확인한 것만 재사용했습니다.

| 조각 | 만든 시각 | provenance 확인 | 완결성·대조 | 처리 |
|---|---|---|---|---|
| `S0/sdmpc/s1u13_T1800`, `_T6300` (+ `.summary.json`) | 11:25–11:48 | W, cf3ce37, dirty 0, 2215d163 | 재생 종료 0 → compare 실행(ps 종료 2는 `action_contract`만 False). `replay_compare.json`과 요약 필드 완결. 녹색·offset·목적값·tangent 계수가 기록 action과 같음 | **재사용** (§6) |
| `S0/paths/b2u1u3_T2700.json` | 11:48–12:05 | 같음 (dirty 0) | exact·반복·no_cache·no_agg·tangent·FD 3 owner가 모두 있음. `urban-sc7/paths/u1u3sc7_T2700.json`과 owner 비용·tangent 비용·FD가 비트 동일 | **재사용**. rc=1은 §2-3의 감싸기 때문 |
| `S0/live/s1u13_T3600.json` | 12:05–12:10 | 같음 (dirty 0) | `errors {}`. 계수 1,459개가 OLD livecheck(`B/live/s1u13_T3600.json`, 09:52)와 **전부 같음**. 목적값·그룹 행·U2·램프 추적도 같음 | **재사용** (§8) |
| `S0/capture/b2u1u3` 40상태 (T1–750, T1800–6750) | 12:10–12:54 | 같음 (dirty 0) | `compare IDENTICAL`, 장부 실패 0. 묶음 1 `urban-sc7/capture/u1u3sc7`와 필드 단위로 같음 | **재사용** |
| 같은 폴더 6상태 (T900, 1050, 1200, 1350, 1500, 1650) | 12:13–12:21 | **dirty 1**: 동시에 돌던 테스트가 추적 JSON을 바꾼 상태. 그 파일은 어댑터가 읽지 않음 [실행 grep] | 값은 참조와 같았음 | `S0/_aborted_0928am/capture_b2u1u3_dirty/`로 옮기고 **다시 포착** |
| 같은 폴더 T6900 | 12:54 중단 | – | 재생 폴더만 반쯤 있음 | 지우고 다시 포착 |
| `S0/tests/*` (스위트) | 12:10–12:24 | dirty 0으로 시작했지만 도중에 추적 파일이 바뀜 | 포착과 동시 실행이었고, 파일별 분해가 없음 | `_aborted_0928am/tests/`로 옮기고 **다시 실행** |
| `S0/fixture_scan.json` | 11:27 | W | 정적 grep | 다시 생성. 행 69개가 옛 산출과 같음 |
| `H/out/t3_selfcheck_sc7.json` | 11:20 | – | 하네스 t3가 묶음 1 포착으로 `t3_sc7.json`을 재현하는지 보는 자기 점검 | 다시 실행(`S0/redo/t3_selfcheck_batch1.json`). 일곱 지표가 `t3_sc7.json`과 같음 |
| `S0/replay/b2u1u3_T6900` (부분) | 12:54 | – | – | 삭제 (scratch) |

- 중단 시도의 `chain.log`는 `_aborted_0928am/chain_until_1254.log`에 복사해 두었습니다. `S0/chain.log`에는 이어서 기록했고, 재개 시작은 `14:31:11 BEGIN … phases=['B1','B2','S']`입니다.

---

## 4. 기존 스위트 (§4.0-2) [실행 `S0/tests/summary.json`, `S0/fixtures/summary.json`]

- **실행 조건:** 한 번에 한 프로세스, BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=…/nbc_b2i`, OLD는 PYTHONPATH에 넣지 않음.
- **금지 시험은 돌리지 않았습니다:** watchdog, cscript, ps1 시험 전부와 `test_tools_integration`(watchdog ps1 `-PreflightOnly`를 실행함).
- 포함한 시험 파일이 cscript·powershell·VISSIM을 부르지 않는 것도 `grep`으로 확인했습니다. subprocess는 python과 `git apply --check`·`git check-attr`뿐입니다.

### 4.1 통과한 스위트

| 스위트 | 결과 | 묶음 1 기록 [읽음 `urban-sc7/tests`] |
|---|---|---|
| n31 (`test_n31_*` 12 + ramp_forecast_keys + qp_fallback) | 167 OK (skip 3) | 165 OK (skip 3). cf3ce37이 시험 2개를 더함 [추론] |
| n31_observe_pipeline / t6_runner / parity / ad_smoke | 4 / 6 / 5 / 8 OK | – |
| tools (plant_gate, verify_gt, watch, common) | 60 OK | 60 OK |
| obs (generator_detectors, lane_context, lane_support) | OK, `OBS150_DETECTORS_OK` `108debbb` | 같음 |
| obs_head (`test_head_*.py` 4개) | 31 passed, 62 subtests | – |
| pyt (repin_scenario_v2, prepare_sdmpc31_network) | 61 passed | 61 passed |
| 생성기 `--check` 15개 | 전부 종료 0 | – |

- 생성기 sha: config `82688d2f`, b1 `0f78bfa6`, U1+U3 `f88d05f1`, plant `a087aa67`, 현시 권한 `e729cdc4`, 면적 경로 `fdc21f06`, 경로 β `41b3113f`, 무신호 `6febd53f`, U2 경로 `ec8697a4`, 무신호 검증 `b5dedf80`.

### 4.2 diagnostics 11개 + extra: 이전부터 있던 실패

| 파일 | fixture 없음 (그대로) | 원인 [실행: `--tb=line`] |
|---|---|---|
| test_head_service_resources | 16 passed | – (추적 파일을 다시 씀, §10-2) |
| test_head_free_service | 7 passed | – |
| test_shared_service_pool | 25 passed | – |
| test_sdmpc_aggregate | 5 passed | – |
| test_urban_flow_accounting | 12 passed | – |
| test_legsplit_receiving | 4 skipped | – |
| **test_sc1004_resource_service** | 5 failed / 1 passed | `probe_model_area_integration.py:66` "Explicit production replay input is missing: evaluation/runs/codex_area_beta0_retry_s13_20260910/…/state_001200.json" |
| **test_route_choice_corridor** | 13 failed / 1 passed | 같음 |
| **test_native_input_prehead** | 9 errors | 같은 종류: `codex_area_observed_nc_s13_20260910/…/state_000900.json` |
| **test_sdmpc_spatial** | 3 failed / 3 passed | 2개는 하네스 스레드 상한("number of threads must be between 1 and 1"). numba 8스레드로는 1 failed / 5 passed가 되고, 남은 하나는 `diagnostics/sdmpc_trial_20260922/trial_h3_v1/request.pickle` 없음 |
| **test_shared_approach** | 8 failed / 6 errors / 2 passed | `probe_model_area_integration.py:85` `KeyError 'control_interval_sec'`(8), `codex_native_clock_fw080_u050_open_v2` run 없음(6) |
| extra_known (lane_initial_projection, dynamic_area_routes, native1083) | 7 failed / 4 errors / 13 passed | "Snapshot lacks a valid network fingerprint"(6), `codex_nc_s13_6056c94_20260909_retry` run 없음(4), `D:/VISSIM-merge/sdmpc-lane-plant-20260921/…` 없음(1) |

- **OLD에서도 같은 실패라는 근거**
  - [실행] 추적 파일이 바이트 단위로 같고(§1), 빠진 입력은 OLD에도, `repo`·`sim3`·`sim3-n31`·frozen에도 없습니다. `request.pickle`만 `sim3`·`sim3-n31`에 있고 OLD에는 없습니다.
  - [읽음] 묶음 1도 OLD에서 extra를 돌려 같은 `7 failed, 13 passed, 4 errors`를 기록했습니다(`urban-sc7/tests/extra.txt`).
  - diagnostics 11개는 묶음 1에서 돌린 적이 없습니다(계획 §4.0-2가 "처음"이라고 적음). 그래서 이 표가 첫 기준선입니다.

### 4.3 이식형 fixture를 복원했을 때 [실행 `S0/fixtures/`]

- `diagnostics/fixtures/README.md`는 과거 run 입력을 ZIP으로 둡니다: `control_area_v1`(core), `route_input_v1`/`_v2`. 복원 위치는 `.review-fixtures/…`(ignored)이고, env로 켭니다(`review_fixtures.py:14-16`, `route_input_fixtures.py:5`) [읽음].
- `fixture_suites.py`는 두 가지를 돌렸습니다.
  - 문서화된 러너 `python -m diagnostics.run_route_input_fixture_tests [--extended]`를 그대로
  - `W/.review-fixtures/b2s0_{core,route1,route2}` 복원본으로 파일별 재실행

| 파일 | core + route v1 | core + route v2 | 남은 원인 |
|---|---|---|---|
| test_sc1004_resource_service | **6 passed** | **6 passed** | – |
| test_route_choice_corridor | **14 passed** | **14 passed** | – |
| test_dynamic_area_routes | 7 passed | 7 passed | – |
| test_native1083_signal_authority | 6 failed | **6 passed** | v1 ZIP에 `codex_area_observed_nc_s13_20260910` 없음 |
| test_shared_approach | 10 passed / 6 errors | 10 passed / 6 errors | `codex_native_clock_fw080_u050_open_v2` 없음 |
| test_native_input_prehead | 9 errors | 9 errors | `diagnostics/route_choice_corridor_1099_ver2.json` 없음(어느 트리에도 없음 [실행]) |
| test_lane_initial_projection | 1 failed / 10 passed | 같음 | 다른 트리(`sdmpc-lane-plant-20260921`)의 run |
| test_sdmpc_spatial | 3 failed | 3 failed | 스레드 상한 2, pickle 1 |
| 나머지 6개 | §4.2와 같음 (통과·skip) | 같음 | – |
| 러너 기본 / `--extended` | errors 1 / errors 24 | – | `selected_control_demand/…/config.json`, `route_choice_corridor_1099_ver2.json`, `native_internal_input_deferred_paths.json` 없음 |

- **다음 단계에 중요한 점**
  - U4·U5가 건드리는 RCC와 SC1004 풀 시험(`test_route_choice_corridor`, `test_sc1004_resource_service`)은 **fixture를 켜면 통과합니다.** 이후 회귀 비교에는 `VISSIM_REVIEW_FIXTURE_ROOT=W/.review-fixtures/b2s0_core`, `VISSIM_ROUTE_INPUT_FIXTURE_ROOT=W/.review-fixtures/b2s0_route2` 설정을 쓰기를 제안합니다.
  - `test_native_input_prehead`는 입력 파일이 없어 어떤 설정에서도 돌지 않습니다. U4 §4.4-5(NIP:266-268·AGG:276-278 pre-head 1093)는 새 시험(`test_n31_urban_batch2.py`)으로 덮어야 합니다 [추론].

---

## 5. 기준선 재현 (§6.2)

### 5.1 T3 (R-obs-b 54전이, U1+U3 = `f88d05f1`, b2 트리) [실행 `S0/t3_b2u1u3.json`]

- 팔 구성은 묶음 1과 같습니다: base·u1u3(`urban-b1d`)에 SC7 정정 뒤 팔 자리에 **b2u1u3**을 둡니다. B그룹 합집합과 공통 전이가 팔 구성에 좌우되므로 같은 구성을 썼습니다.

| 지표 | 전이 | 키 | b2u1u3 | 묶음 1 목표 (PLANT_PORTING_GUIDE:75) | 같음 |
|---|---|---|---|---|---|
| A1 | 54 | 123 | 6.360570688771058 | 6.361 | 부동소수 동일 |
| A2 | 14 | 123 | 8.892142140201445 | 8.892 | 동일 |
| A3 | 13 | 123 | 11.586976223422187 | 11.587 | 동일 |
| B1 | 54 | 122 | 7.190921650202904 (편향 +158.9) | 7.191 | 동일 |
| B2 | 14 | 122 | 10.040777887277917 (+472.7) | 10.041 | 동일 |
| B3 | 13 | 122 | 12.884052513027292 (+829.3) | 12.884 | 동일 |
| C | 54 | 100 | 11.011478163385599 (−999.6) | 11.011 | 동일 |

- "동일"은 `urban-sc7/t3_sc7.json`의 `u1u3sc7` 값과 `==` 비교한 결과입니다.
- A1·C 키별 값도 모두 같습니다.
- SC7 정정 증분(b2u1u3 − u1u3)도 같습니다: A1 −0.00902, iid CI [−0.0141, −0.0044], 블록5 CI [−0.0123, −0.0060].
- U3 회전 한 스텝 방류: 10377은 6.65 대 FZP 6.15, 10686은 8.29 대 FZP 33.09입니다. 묶음 1과 같습니다.

### 5.2 세 예측 경로·FD (T2700, U1+U3) [재사용 확인, `S0/paths/b2u1u3_T2700.json`]

| 비교 | b2 | 기준 (§4.0-3) |
|---|---|---|
| 정확 대 반복 / 캐시 끔 | 목적·owner 차이 0 / 0 | 0 |
| route-bins (`no_agg`) | 목적 5.68e-14, owner 최대 1.78e-15 | ≤ 1.6e-13 |
| AD 대 스칼라(같은 점) | 0.0 | ≤ 3.6e-15 |
| 연속 대 정확, 도시 owner 최대 | 0.012989 (SC12). 전체 최대 0.0457은 비도시 owner | ≤ 0.013 |
| FD h=0.01 SC1001 | tangent 3.00330 / 중앙 2.97491 | 3.003 / 2.975 |
| FD SC1002 | 0.91284 / 0.91627 | 0.913 / 0.916 |
| FD SC7 p1 | −0.23771 / −0.20878 (한쪽 −0.29890 / −0.11866, 꺾임점) | −0.238 / −0.209 |

- Ω 목적값은 504.82540210299754입니다. owner 비용·tangent 비용·FD 값이 `urban-sc7/paths/u1u3sc7_T2700.json`과 비트 동일합니다(`S0/stage0_results.json` `paths`).

### 5.3 R-obs-b 61상태 재생 (G-ID 기준 참조) [실행]

| 팔 | 상태 | compare | 비경로 action 차이 | 장부 최대 / 실패 | depth3 | 묶음 1 포착과 필드 비교 |
|---|---|---|---|---|---|---|
| `S0/capture/b2u1u3` (U1+U3) | 61 | IDENTICAL 61/61 | 61상태 모두 있음: 기록 결정이 기본 튜닝이라 β·게이트 β·램프 분할 등이 다름. 묶음 1 `u1u3sc7`도 같은 모양 | 9.89e-9 / 0 | 14/14, 오류 0 | `urban-sc7/capture/u1u3sc7`와 17개 필드 61/61 동일, 최대 차이 0.0 |
| `S0/capture/b2base` (기본 `82688d2f`) | 61 | IDENTICAL 61/61 | **0/61** | 8.61e-9 / 0 | – | `urban-b1d/capture/base` 61/61, `urban-sc7/capture/base_sc7` 6/6 동일 |

- 비교 필드: β, movement_meta, q0/o0/inv0, assign0, q1/o1/inv1, departures, routed_departures, greens, depth3, prediction_summary 등. 대조 파일은 `S0/compare_b2u1u3_vs_u1u3sc7.json`, `S0/compare_b2base_vs_{b1dbase,base_sc7}.json`입니다.
- 모든 포착의 provenance는 W·cf3ce37·dirty 0·`2215d163` 한 가지입니다.
- 이 두 폴더가 단계 1 이후 G-ID (a)(기본 튜닝, `MRS compare`)와 (b)(U1+U3 한 스텝 포착 바이트 동일)의 "b2 키 없음" 참조입니다.

---

## 6. S1 1800·6300 자기 설정 재현 (§6.1 (c), `[검토 C-12]`) [재사용 확인]

- **방법:** `H/sdmpc_replay.py`로 `MRS.prepare`(복사 전용)를 하고 `W/…/replay_decision_n31.ps1 -Root W`를 부릅니다.
  - 튜닝은 frozen `sdmpc31_cf3ce374_202609261037`에서 W로 rebase되며, sha `f88d05f1`로 런 provenance와 같습니다 [읽음].
  - 이전 action은 런 폴더에서 읽기만 합니다.

| 상태 | derived | action_csv | action_controls | objective | action_contract | 녹색·offset | 선택·유지 목적값 | tangent 계수 |
|---|---|---|---|---|---|---|---|---|
| 1800 | ok | ok | ok | ok | 다름 | 같음 | 460.9685 / 462.7373 = 기록 | 2개 모두 기록과 같음 |
| 6300 | ok | ok | ok | ok | 다름 | 같음 | 357.4451 / 359.3969 = 기록 | 같음 |

- `action_contract`가 다른 이유는 action 자체에 VSL 100과 110이 섞여 있기 때문입니다(`vsl_speeds [100, 110]`, 기대 110, `S0/sdmpc/s1u13_T*/replay_compare.json`). `action_csv`가 기록과 같으므로 기록 action도 같은 성질입니다. SC109_DIAG §4와 같은 정의로 이 검사는 제외했습니다.
- **판정:** 두 상태 모두 재현됐습니다. 대체 상태(2700·4500)는 필요 없었고, 멈춤 규칙 `[검토 C-12]`은 걸리지 않았습니다.
- G-ID (c)의 S1 쪽 1800·6300은 이 정의로 쓸 수 있습니다. S0e 1800·3600과 S1 3600은 이번에 재현하지 않았고, 계획대로 XREPLAY·SC109_DIAG의 기존 확인에 기댑니다 [읽음 계획 §6.1 (c)].

---

## 7. 206.53 가정 fixture 목록 (§4.0-4) [실행 `S0/fixture_scan.json`]

- **방법:** `diagnostics/**/test_*.py`와 `n31_fixtures.py` 300개 파일을 정적으로 스캔했습니다. 69줄, 27개 파일이 걸렸습니다.
- 행동 판단 [추론]: U4는 키가 있을 때만 동작하므로, 키가 없으면 아래 시험은 모두 그대로여야 합니다. 이 목록은 "U4 키 있음" 쌍둥이 시험이 필요한 곳입니다(§5.1 끝).

| 범주 | 뜻 | 파일:줄 |
|---|---|---|
| NUM206 (206.53의 k배 리터럴) | 등가 균일 정규화를 박아 둔 값 | `sdmpc_n31_20260924/tests/test_n31_urban_batch1.py:623,625`(k=1), `test_head_service_resources.py:146`(826.12 = 4×), `test_physical_phase_authority.py:297`(413.06 = 2×), `test_signal_observation_window_patch.py:122`(619.59 = 3×) |
| CAP_BY_LANES | 옛 용량 경로 직접 호출·메타 키 | `test_n31_urban_batch1.py:870,906-911`, `test_native1083_signal_authority.py:42`, `test_route_choice_corridor.py:28`, `test_route_choice_projection_claim.py:32`, `test_sc1004_resource_service.py:19,86` |
| RCC_SCALAR | 회랑·풀에 넘기는 스칼라 `per_lane_capacity_veh_h` (U4 §4.4-4) | 위 셋 + `test_native_route_choice.py:173`, `test_sc15_service_calibration.py:41,50` |
| PREHEAD | pre-head 예산식 (U4 §4.4-5) | `test_native_input_prehead.py:44,64`(입력 없어 못 돎, §4.3), `test_sdmpc_aggregate.py:61` |
| LG_MEMBERS | 헤드 하한 배분·`_LTO` (U4-0, §4.4-1b) | `test_n31_urban_batch1.py:607-628` |
| HARDCODED_CAP | 용량 맵 값 단언(합성 fixture 200/800 등) | `obs150…/test_head_sho_v2.py:126,133`, `test_head_free_service.py:108-153`, `test_head_service_resources.py:284,333`, `test_native1083_signal_authority.py:63`, `test_sc1004_resource_service.py:58`, `test_sc15_service_calibration.py:37`, `test_signal_observation_window_patch.py:101-177` |
| FULL_CONFIG | 실제 튜닝·`configure_runtime` 사용. 값은 config를 따르므로 U4 키가 없으면 불변 | 18줄 (`test_lane_context:42`, `test_n31_plant_load:221`, `test_runtime_setup:117` 등) |

- `HARDCODED_CAP`의 합성 fixture는 206.53과 무관하지만, U4가 켜지면 `distribute` 콜백이 바뀝니다(§4.4-1b). 그래서 SHO·HSR 단위 시험(`test_head_sho_v2`, `test_head_free_service`)은 콜백 쌍둥이 후보입니다 [추론].

---

## 8. 시간 기준선 (§4.0-5, §6.7 (e))

### 8.1 결정론 계수 [실행]

| 대상 | 값 |
|---|---|
| S1 1800 tangent 도함수 2개 `operations` | 13,662,852 / 13,810,195 |
| 〃 `event_counts` primal / ties / **discrete** | 8,505,198 / 368,622 / **639,987**; 8,561,165 / 372,634 / **668,616** |
| S1 6300 `operations` | 11,114,385 / 11,336,611 |
| 〃 primal / ties / **discrete** | 7,708,419 / 341,303 / **583,778**; 7,841,131 / 350,859 / **588,650** |
| 위 계수: 재생 대 기록 | 전부 같음 (`tangent_traces_equal True`) |
| livecheck S1 3600, 정확 450 s 예측 1회 | `urban_substep_accounted` 450, `LaneOfframpRuntime.drain` 450, `regular_batch` 44,550, `LaneRampRuntime.receiving_space` 6,750 (계획 §4.0-5 값과 같음) |
| livecheck 계수 전체 (설치+투영, 정확 예측) | 1,459키가 OLD livecheck과 모두 같음. 목적값 493.66162676219653 |

### 8.2 크기 [실행]

- action JSON: S1 1800 기록 57,757,610 B / 재생 57,752,042 B, 6300 57,744,035 / 57,738,472 B. 차이는 경로 문자열 길이입니다.
- 어댑터 stdout 487 B, stderr 406 B(경고 3줄). C6의 stdout 상한 512 B를 더해도 파이프 4,096 B 안입니다 [산술].

### 8.3 벽시계 [실행, 부하 표기]

- 단계 0 동안 VISSIM이 3~4개 돌았습니다. 재개 구간 스텝 83개 가운데 69개는 4개, 14개는 3개였습니다. 그래서 아래 값은 교대 비교용 기준일 뿐이고, 절대 관문 값이 아닙니다.

| 대상 | b2 | 참고 |
|---|---|---|
| S1 1800 결정 `decision_wall_sec` | 707.2 s (프로세스 723.7 s) | 기록 586.5 s. VISSIM 4개 |
| S1 6300 결정 | 606.9 s (623.1 s) | 기록 465.0 s |
| T2700 정확 예측 (SDMPC horizon) | 64.9 s (반복 64.4, 캐시 끔 67.9, no_agg 190.3) | 묶음 1 57.2 / 56.2 / 59.7 / 162.7 s |
| T2700 tangent 평가 | 134.0 s (wall 141.8) | 묶음 1 115.7 s |
| R-obs-b 한 스텝 포착, U1+U3 | 예측 13.96 s, 상태당 25.8 s, depth3 120.8 s | – |
| R-obs-b 한 스텝 포착, 기본 | 예측 14.77 s, 상태당 27.2 s | – |
| livecheck 정확 450 s (프로파일러 부하) | 227.5 s | OLD 197.3 s. 관문 값 아님 |

- 계획 §6.7이 말하는 "예측 1회 약 45~50 s"보다 부하 때문에 약 30% 느립니다. 교대 벽시계 관문은 같은 부하에서 기준과 후보를 번갈아 재야 합니다.

---

## 9. 안전 확인 [실행]

- `find -newer marker_stage0_start`(11:25) 결과, 아래 네 곳 모두 새 파일 0개입니다.
  - S1 런 폴더, R-obs-b 런 폴더
  - `frozen/sdmpc31_cf3ce374_202609261037`
  - OLD `sim3-n31-urban`
- W 안에서 바뀐 것
  - 추적 파일 4개를 테스트가 다시 썼다가 되돌렸습니다: `head_service_resources_canonical_validation.json`, `route_input_fixture_validation{,_v2}.json`, `road_support_336_portable_regression.json`. 지금 `git status --porcelain`은 0줄입니다.
  - ignored 산출은 `.review-fixtures/`(테스트·fixture 복원), `__tangentcache__`입니다. 그 밖의 untracked 파일은 0개입니다.
- v3c1 워크트리, `sim3-n31`, s37, RM 팔, 봉인 시드 59/61/67에는 손대지 않았습니다.
  - v3c1 폴더는 VISSIM 프로세스 명령줄에서 **보이기만** 했고 열지 않았습니다.
  - VISSIM·cscript는 시작하지도 죽이지도 않았습니다. 관찰한 프로세스는 s37 NC, s31/s41 RM, 이후 네 번째 1개입니다.
- 재생은 한 번에 하나였습니다. 체인이 다른 재생 python을 감시했고, 대기(BUSY)는 0회였습니다.
- 모든 재생에 BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2i`를 적용했습니다. 예외는 `test_sdmpc_spatial` numba 8스레드 1회(2 s)입니다.

---

## 10. 다음 단계에 넘기는 것

1. **스위트 기준 해석 (결정 제안)**
   - 계획 §4.0-2·§5.1은 "기존 스위트 전부 통과"라고 적었습니다. 그런데 diagnostics 5개 파일과 extra는 **cf3ce37의 어느 체크아웃에서도** 입력이 없어 실패합니다(§4.2).
   - 제안
     - (a) 이후 단계의 회귀 기준을 "`S0/tests/summary.json` + `S0/fixtures/summary.json` 대비 새 실패·새 오류 0, 통과 수 감소 0"으로 읽습니다.
     - (b) RCC·SC1004 시험은 fixture env(core + route v2)로 돌립니다.
     - (c) pre-head 1093은 새 단위 시험으로 덮습니다.
   - 멈춤 규칙(§7) 목록에는 없는 항목이라 멈추지 않았습니다.
2. **추적 파일을 다시 쓰는 시험 4개**
   - `test_head_service_resources.py:130`, `run_route_input_fixture_tests.py:46-47`, `test_projection_support_road_paths.py:159`
   - 첫째 것은 소스 sha 지문이 커밋 당시와 달라서 매번 diff가 납니다(`S0/tests/*_tracked_*.diff`).
   - 단계 1 이후 커밋 전에는 반드시 되돌려야 합니다. `H/run_suites.py`·`H/fixture_suites.py`가 이것을 자동으로 합니다.
3. **포착과 스위트를 동시에 돌리지 마십시오.** 추적 파일 변경이 포착 provenance를 dirty로 만듭니다(§3).
4. `H/check_paths.py`는 이제 rc 0으로 끝납니다(§2-3). 옛 산출 JSON의 rc=1 기록은 이 감싸기 때문입니다.
5. 브랜치 이름이 계획 §3:139와 다릅니다(`urban-batch2` 대 `urban-b2`). 커밋 메시지나 보고서의 이름은 실제 브랜치를 따르십시오.
6. G-ID (c)의 S0e 1800·3600과 S1 3600은 이번 단계에서 다시 재현하지 않았습니다. 단계 1 G-ID (c)에서 b2 트리로 받습니다(§6).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE0.md` (이 문서)
- 체인·로그: `S0/chain.log`, `S0/logs/*.txt`, `S0/chain_stdout_resume.txt`
- 재현: `S0/t3_b2u1u3.json`·`.txt`, `S0/stage0_results.json`, `S0/compare_*.json`, `S0/paths/b2u1u3_T2700.json`, `S0/sdmpc/s1u13_T{1800,6300}.summary.json`, `S0/live/s1u13_T3600.json`
- 포착(G-ID 참조): `S0/capture/b2u1u3/T*.json`(61), `S0/capture/b2base/T*.json`(61)
- 스위트: `S0/tests/summary.json`·`*.txt`·`*.diff`, `S0/fixtures/summary.json`·`*.txt`·`*.diff`
- fixture 목록: `S0/fixture_scan.json`
- 트리 동일성: `S0/redo/tree_bytes_compare.json`, `S0/redo/ignored_{old,b2}.txt`, `S0/redo/t3_selfcheck_batch1.json`
- 중단 시도 보관: `S0/_aborted_0928am/`
- 하네스: `H/*.py`, `H/cfw/*`, `H/alt_replay.ps1`
