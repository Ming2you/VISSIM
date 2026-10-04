# K7 오프라인 관문 결과 (O-0 … O-8)

- 작성 2026-10-01 17:3x KST. 판정 기준은 사전 선언 `reports/k7/K7_GB_J1_PREDECLARATION.md`(sha256 `fad31d70…`, 실행 전후 다시 계산해 sidecar와 같음) [실행]입니다.
- 판정 대상은 K7 head `99dc641809fb939515c6d6f1e2f655c21deef289`(W 위의 로컬 커밋 5개, 푸시 안 함)입니다.
- 관문 트리 GWT7 = `D:/VISSIM-merge/sim3-n31-v3c3-k7gate`. `git worktree add --detach … 99dc641`로 만들었습니다. 만든 직후 HEAD = K7이고 `status --porcelain --ignored`는 0줄이었습니다 [실행].
- 실행 위치는 GWT7(시험·생성기·SDMPC 쪽)과 FRZ_K6(O-5, 읽기만)입니다. W에서는 아무것도 돌리지 않았습니다.
- 모든 Python은 BELOW_NORMAL(`gates/bn.py`, 0x4000 되읽기 확인), `python -B`, `PYTHONDONTWRITEBYTECODE=1`로 돌렸습니다(`gates/env.sh`).
- VISSIM은 시작하지도 종료하지도 않았습니다. 금지 시험 7종은 돌리지 않았습니다. 커밋·푸시·동결도 하지 않았습니다.
- 증거 폴더는 `D:/VISSIM_runs/20261001_v3c3/reports/k7/gates/`입니다. 아래 상대 경로는 모두 이 폴더 기준입니다.
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단. 코드 줄 번호는 K7 기준입니다.

## 0. 판정표

| 관문 | 판정 | 핵심 근거 | 증거 |
|---|---|---|---|
| O-0 전제·트리 규칙 | **통과** (s53 재확인만 보류) | 커밋 5개 모두 작성자·커미터 Ming2you/alsrjsrb1915@snu.ac.kr, 메시지 끝 `Co-Authored-By` 줄. s53 대체를 영수증·QUALIFICATION·보고서에 적음. v3c3 s53 재발사 런은 아직 `completed=false`라 재확인은 보류 | §1 |
| O-1 시험 묶음 | **통과** | 9묶음의 실패 id 집합이 K6과 같음(diag 65, extra 11, 나머지 0). 사라진 id 5개는 모두 개명표에 있음. 새 시험 10개 통과. T9 통과(허용 오차 1e-4 그대로, h 0.0625) | `o1/` |
| O-2 생성기·도구 | **통과** | 20개 명령 모두 exit 0. unsignalized validation `--check` 두 번 모두 `d8718b9d`. `REPIN_VERIFY_OK`, `REPIN_CONFIGURE_OK` t=1/150/900 | `o2/o2.log` |
| O-3 경로 | **통과** | 98/98 경로가 선언한 합집합 안에 있음 | `o3/o3_paths.json` |
| O-3 내용 | **실패 (구속 1행)** | **DA-2**: `unsignalized_turns`의 회전 목록이 23 → 22로 바뀜(`SC103_S_SC6_to_E` 빠짐). 선언의 예외는 "검증 수치"뿐. 나머지 13행은 통과 | `o3/o3_content.json`, `o3/ra1/` |
| O-4 VSL 가족 | **통과** | (a)–(e) 모두 선언값과 같음 | `o4/o4_result.json` |
| O-5 L2 all-110 (FRZ_K6) | **실패 (조건 4의 연산 수 등식)** | 조건 1·2·3 통과. 조건 4 중 FW_E에서 `L2 − KA = n × d1`이 4상태 모두 어긋남: operations는 +4/−12/−10/−20, tangent_entries는 −133/−336/−267/−211. 나머지 조건 4 항목(primal 동일, FW_W 0열과 Trace 동일, 사건 수 동일, n 동일, κ 비례 2.3e-13 이내)은 성립 | `o5/out/o5_judgement.json` |
| O-6 110 미만 쓰기 | **통과** | 양성 P1–P5, 음성 N1–N6 모두 선언대로 | `o6/o6_result.json` |
| O-7 문서·이월 | **실패 (경미, 문서 1건)** | CONTRACT·안내서·주석·QUALIFICATION(P2·P7 포함)·이월 사전값 표는 충족. `REPIN_V3C3_REPORT.md` §5 grep 기록에 **건수가 빠진 행이 3개** 있음 | §8 |
| O-8 트리 위생 | **실패 (외부 원인으로 추정)** | W·GWT7·FRZ_K6·FRZ_OLD·`frozen/*`·다른 작업 트리 5개는 불변. 그러나 **GWT6**에 관문 중 무시 파일 1개가 새로 생김(17:04:51). 관문 프로세스가 쓴 것이 아니라고 봄 [추론] | `o8_before.json`, `o8_after.json` |

- **all_pass = false.** 선언 O-9에 따라 푸시·동결·발사를 하지 않고 멈춥니다. 허용 오차와 허용 목록은 넓히지 않았습니다. 고친 것도 없습니다.
- 관문 중 수정 커밋은 없습니다. K7 head는 그대로 `99dc641`입니다.

### 멈춘 원인 (O-9 원인 키)

1. **O-3 DA-2** (구속): `N31D/urban/unsignalized_turns_v3c3_20261001.json`
   - `/movements/SC103_S_SC6_to_E`가 `/not_included_fzp_validation/0`으로 옮겨졌습니다.
   - 커넥터 10096의 정지 비율이 0.0472 → 0.0544로 올라 규칙 문턱 0.05(`scripts/derive_unsignalized_turns.py:151` `max_stopped_before_share`)를 넘었습니다.
   - 생성기와 규칙은 바뀌지 않았습니다. 입력 검증표가 v3c3 fit FZP로 바뀌어 판정이 달라진 것입니다 [실행].
2. **O-5 조건 4** (구속): FW_E Trace의 `operations`·`tangent_entries`가 `L2 − KA = n × d1`을 정확히 만족하지 않습니다. n = 27809, d1 = 38입니다.
3. **O-7** (경미): grep 기록에 건수가 없는 행이 3개입니다(§8).
4. **O-8** (외부로 추정): GWT6에 새 파일 `evaluation/controllers/__pycache__/control_area_objective.cpython-312.pyc`가 생겼습니다(60,292 B, 17:04:51).

## 1. O-0 전제와 트리 규칙 [실행·읽음]

- 커밋 5개(`8892c91`, `6472308`, `69f44ef`, `4edc023`, `99dc641`)는 모두 위 신원이고, 메시지 끝 줄이 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`입니다.
- `--renormalize` 사용 여부는 사후에 직접 확인할 수 없습니다.
- **참고 (관문 조건 밖)**: 커밋 blob의 줄끝이 LF → CRLF로 바뀐 파일이 2개 있습니다.
  - `N31D/make_plant_n31.py`(0/160 → 221/221 CRLF)
  - `N31D/tests/test_repin_scenario_v2.py`(0/720 → 879/879)
  - 그래서 `git diff`가 이 두 파일을 통째로 다시 쓴 것처럼 보입니다. 내용 diff(`--ignore-cr-at-eol`)는 +170/−11입니다.
  - 저장소 설정은 `core.autocrlf=true`입니다. 생성기 `--check`와 시험에는 영향이 없었습니다 [실행].
- **s53 입력**: K7은 선언 O-0의 대체를 썼습니다.
  - 영수증 `s53_v3c2nc_extraction_receipt.json`: network `c2dd1a48…`, `substitute` 문구에 "GB-1 s53 is not judged"가 있음
  - QUALIFICATION: "declared substitute: the v3c3 s53 run did not complete"
  - `REPIN_V3C3_REPORT.md` §4(a): "s53 자체의 동일성 판정은 아닙니다"
  - 세 곳 모두 대체 사실을 적었습니다 [읽음].
- **보류**: v3c3 s53 재발사 런(16:19:58, VISSIM PID 25080)은 17:3x 현재 `run.json` `completed=false`입니다. 다음 둘은 런이 끝난 뒤 해야 합니다.
  - GB-1 s53 PASS
  - v3c3 s53 재추출의 boundaries/flows/cells 바이트 = 대체 입력
  - 하나라도 어긋나면 선언대로 STOP입니다.

## 2. O-1 시험 묶음 [실행]

- 러너는 `o1/run_tests_gwt7.sh`입니다. GA-5 `run_tests_gwt.sh`에서 경로 3종(env, 로그, 트리)만 GWT7로 바꿨습니다. 실행 시각은 16:51–16:56입니다.
- 실패 id 추출에는 `o1/ids2.py`를 썼습니다(GA `ids.py`에 pytest 실패 머리줄 파싱을 더함). extra 묶음은 K6 `extra.outcome`과 같은 방식으로 셌습니다. K6 로그에서 다시 뽑아도 K6 파일과 같았습니다(줄끝만 다름).

| 묶음 | K7 결과 | K6 실패 집합과 비교 |
|---|---|---|
| n31 | 198 OK (skip 3, K6과 같은 3개) | 같음 (0) |
| t9 | 9 OK | 같음 (0) |
| tools | 60 OK | 같음 (0) |
| obs | 143 OK | 같음 (0) |
| pyt | 73 passed | 같음 (0) |
| extra | 7 failed / 4 errors / 13 passed | 11개 id가 K6 `extra.outcome`과 같음 |
| diag | 28 failed / 37 errors / 228 passed / 3 skipped | 65개 id가 K6과 같음 |
| dprof | 16 passed, 2 skipped | 같음 (0) |
| new | 1 OK, 8 OK, 41 passed | 같음 (0) |

- **조건 1**: K7 실패 집합 ⊆ K6 실패 집합이 성립합니다(묶음마다 같음).
- 사라진 시험 이름은 K6 → K7 소스 비교로 찾았습니다. 5개가 모두 `K7_IMPLEMENT.md` §6 개명표에 있습니다.
  - `test_reference_law_is_n1_l1` → `_l2`
  - `test_runner_config_allows_exactly_80_to_110_each_with_a_v2_distribution` → `…_single_value_family_each_with_a_v3c3_distribution`
  - `test_the_v3b_sources_left_this_tree` → `test_the_v3c1_sources_left_this_tree`
  - `test_routing_v3c1_*` 2개 → `test_routing_v3c3_*`
- **조건 2**: K6 실패 → K7 통과로 바뀐 id는 없습니다.
- **조건 3** (새 시험 10개 모두 통과, 최소 범위 충족) [읽음 `N31D/tests/test_repin_scenario_v2.py:758-855`]
  - N8 열거
    - 받음: v3c3
    - 거부: v3c2(`lacks desSpeedDistribution [81, 91, 101]`), +DSD 94, −DSD 101, 구성 14 바이트 변조(`v3c3_block_audit`), vehComp 13번째 행, v3c1
  - C-10: `test_the_v3c1_sources_left_this_tree`, `test_the_v3c3_tables_carry_the_v3c1_values`
  - V-11: `VslFamilyTests` 3개
  - V-10: `test_reference_law_is_l2`
  - N11: `test_n31_urban_batch1.py:59` `'2026-10-01'`
- **조건 4 (T9)**: `test_vsl_below_max_equals_central_fd`가 통과합니다. 상대 1e-4 그대로이고, h는 0.0625입니다.
  - 110 한쪽 도함수 ≠ 0이고, FW_W 열은 0(`west_max_abs_tangent == 0.0`, `test_n31_ad_smoke.py:70`)입니다.
  - **단서**: h 0.25 → 0.0625 변경은 K7 구현 중 h 0.25에서 100(ttt) 상대 2.5e-4로 실패를 본 뒤 한 것입니다(계획 R9 "곡률, h").
  - GWT7에서 탐침을 다시 돌린 결과(`o1/t9probe/t9_probe.json`)는 구현 단계의 증거 파일과 **비트 동일**했습니다 [실행].
  - 중앙차분 오차는 h를 반으로 줄일 때마다 정확히 1/4이 됩니다(100: 1.0e-3, 2.5e-4, 6.3e-5, 1.6e-5, …). 좌·우 차분은 양쪽에서 AD로 모입니다. 따라서 O(h²) 절단 오차이고 AD가 극한값입니다.
  - 허용 오차는 넓히지 않았으므로 통과로 판정했습니다. 다만 사전 선언이 h를 정하지 않았고, 이 변경은 실패를 본 뒤 한 것임을 적어 둡니다.

## 3. O-2 생성기·도구 [실행] (`o2/run_o2.sh`, `o2/o2.log`)

- 다음이 모두 exit 0이고 sha가 같았습니다.
  - `make_reference_config --check`: `add58bc4`
  - `make_plant_n31 --check`: `b119d6d9`
  - `make_config_n31 --check` 세 벌: `319d07aa`, `7c43f881`, `371c6b75`
  - `derive_ramp_forecast_n31 --check`: `RAMP_FORECAST_OK`(입력 5시드, s53 = v3c2 폴더)
  - `extract_port_profile --check`, `build_obs150_detectors --check`: `108debbb`, 294행
  - `derive_unsignalized_validation --check` 두 번 모두 `d8718b9d`
  - C-9 생성기 5개 `--check`
  - `preflight_tuning_paths` ×3: PASS
  - `repin verify`: `REPIN_VERIFY_OK files=70 pins=122 net=identical`
  - `configure-check --sec 1 --sec 150 --sec 900 --workdir gates/tmp/cfgcheck`: `REPIN_CONFIGURE_OK enumeration=compositions:14;vehcomp_rows:12;distributions:81,91,101,110 family=single_value:written=81,91,101,110 t=1:keys=312,enabled=38 t=150:keys=328 t=900:keys=376`
- **단서** [읽음]: configure-check는 `freeway.lane_plant`를 빼고 돕니다(`repin_scenario_v2.py:1736`). 그래서 `runtime_setup.py:246-251`(plant v2일 때만, `:250`) **줄 자체는 실행되지 않습니다.**
  - 같은 함수 `check_family_files`는 배포 튜닝의 manifest 핀으로 따로 실행됩니다(`:1791`).
  - 선언 GB-5가 "런타임 가족 검사를 배포 경로에서 처음 지나는 지점"을 R-obs3 t=1로 적은 것과 같은 해석으로 통과 처리했습니다.

## 4. O-3 허용 diff와 파생 기대값

### 경로 [실행] (`o3/o3_paths.py` → `o3_paths.json`)
- `git diff --name-status 54d821c 99dc641`: 98개(A 18, M 67, R 13). 98/98이 합집합 안에 있습니다.
- R 13개는 모두 v3c1 → v3c3 개명(v3c1 파일 삭제)입니다.
- 분류할 때 근거로 쓴 것
  - `area_dynamic_routes.py`: C-10 `lines`의 `area_dynamic_routes.py:6`
  - `diagnostics/test_vsl_command_distribution.py`: K5 시험의 "트리 가족" 단언 distribution → single_value. K5에서 미룬 V-6/V-11의 시험으로 분류했습니다.
  - `metanet_calibration_v1/v3c3_nc_20261001/.gitattributes`: 새 파생 폴더의 바이트 보존 속성

### 내용 (`o3/o3_content.py` → `o3_content.json`, `o3/ra1/`)

| 행 | 판정 | 근거 |
|---|---|---|
| RA-1 영수증 | 통과 | 5시드 checks 18538, 프레임 8995.1, 추출기 `5fa27047`, 인자(phase 0.1, geometry_profile, branch_guard)가 eo와 같음. 망 sha는 31 `3de889f0`, 41 `726af589`, 43 `51478c39`, 47 `1895ca30`, 53 `c2dd1a48`(대체, 영수증에 적힘) [실행] |
| RA-1 boundaries/flows/cells | 통과 | **관문에서 GWT7로 다시 추출**했습니다(5시드, 하나씩, 출력은 끝난 뒤 `tmp/ra1_reextract`로 옮김). 15개 파일이 모두 v3c2 eo와 바이트 같음. 다시 뽑은 boundaries는 커밋본과도 같음. manifest·geometry 차이는 경로·벽시계(`elapsed_sec_not_benchmark`)뿐 [실행 `o3/ra1/ra1_compare.json`, `ra1_manifest_diff.json`] |
| RA-2 s31 geometry | 통과 | v3c2 eo `b705f472`와 다른 곳은 network/source_network(path, sha)와 입력 경로 4개(geometry_profile, mapping, off_inventory, refined_partition)뿐 |
| RA-3 포트 프로필 | 보고 | 수치 리프 30개 변화. 표본 수 최대 ±10, 속도 최대 \|Δ\| 3.30 km/h(10491) |
| RA-4 RAMP_FORECAST | 보고 | drain 16.0/43.6/30.2/88.5/40.8/159.6/33.4/44.4 → 17.4/43.0/31.1/88.4/38.6/154.3/33.1/44.6 s. max_vph 220/2347/408/545/551/1248/843/592 → 220/2353/413/545/551/1262/850/600. `--check` 통과 |
| RA-5 | 통과 | `--check` 두 번 모두 같은 sha `d8718b9d` |
| DA-1 β | 통과 | 표 4개의 차이는 모두 핀·출처·날짜 포인터. β 값 포인터 차이 0. v3c1 파일은 없음. 어댑터 키는 `routing_v3c3`, `routing_v3c3_2`. `COMPLETE_BETA_SOURCES = {routing_v3c3_2}`. `check_complete_beta_runtime`이 보는 표 망 sha는 `3de889f0`. 배포 튜닝 β 원천은 `routing_v3c3_2` |
| **DA-2 도시 묶음 1** | **실패** | phase authority, route queue, nonexistent, offramp prior, area provenance는 핀만 바뀌었고 area 계약은 바이트 같음(blob `e1400e3d`). 그러나 `unsignalized_turns`는 검증 수치 63개 외에 **회전 목록이 바뀜**: `SC103_S_SC6_to_E`(10096, 0.0472 → 0.0544 > 0.05)가 `movements`에서 빠져 `not_included_fzp_validation`으로 옮겨짐(23 → 22). 선언 `:110` "sha만 바뀜(unsignalized_turns의 **검증 수치**는 예외)"의 예외 밖 |
| DA-3 | 통과 | transfer `repin_step`: 구성 14(391 B `82c11cd5`), 분포 81/91/101(217/217/221 B), composition_edits 12, `desSpeedDistributions.added` = [81,91,101,110], `vehicleCompositions.added` = [14]. `REPIN_VERIFY_OK`는 O-2 |
| DA-4 membership | 통과 | 바뀐 곳은 network/scenario_derivation.runtime_network의 path·sha뿐. 1134/1135 리프 7개가 K6 트리 값과 같음. lineage 시험은 pyt 묶음에서 통과 |
| DA-5 obs150 | 통과 | CSV `108debbb`, 294행, K6 바이트 그대로. 사이드카는 핀만(망 `3de889f0`, 러너 `37c5021f`, 기하·헤드 계약 sha, 생성기 sha256_lf) |
| DA-6 reference | 통과 | FW_E가 L2와 JSON·키 순서까지 같음. 반올림값 없음. vsl_set [80,90,100,110]. transport `sign_cells [0,3,5,8,14,18,26,28]` 불변. 그 밖의 차이는 `_vsl_model_note`뿐 |
| DA-6 튜닝 ×3 | 통과 | 사상 M, vsl_set, max_vsl_step 40, ignore_wall_time_limits true(세 벌 모두) |
| V-6 러너 | 통과 | 34번 줄만 `"80,90,100,110"` → `"81,91,101,110"`. 37줄 중 나머지는 바이트 같음(`f0ed036e` → `37c5021f`) |
| N-4 망 사본 | 통과 | `3de889f0`, `.sig` 42개 blob 불변, v3c1 사본 없음 |
| C-7 | 통과 | 생성기 망 상수 `3de889f0`, v3c1 64자 sha 없음 |
| 바꾸지 않는 것 | 통과 | 러너 VBS `8c753c08`, `sdmpc.py`, `launch_plan`/`freeze_manifest`/`run_sdmpc_n31`/`prepare_sdmpc31_network` 모두 diff 없음. `EXPECTED_SIGN_CELLS = [0, 3, 5, 8, 14, 18, 26, 28]` |

- DA-2 영향 범위 [읽음]
  - 이 표를 읽는 곳은 `config_n31_v2_urban_b1.json`, `config_n31_v2_urban_b1_u1u3.json`(U3 후보)뿐입니다.
  - 배포 튜닝 `config_n31_v2.json`, plant, reference는 읽지 않습니다(`grep` 0건; 런타임 설치는 `vissim_stackelberg_adapter.py:7165` `install_unsignalized_turns`).
  - 따라서 R-obs3·J1 경로의 바이트에는 영향이 없다고 봅니다 [추론]. 그래도 선언상 구속 조건 실패이므로 사용자 결정이 필요합니다.

## 5. O-4 VSL 가족 일관성 [실행] (`o4/o4_run.py`, `o4_console.txt`)

- (a) `check_family_files`를 튜닝 세 벌 × 각 manifest 핀(reference, runner, sha 일치)에 돌렸습니다. 결과는 세 벌 모두 `{'family':'single_value','commands':[80,90,100,110],'written':[81,91,101,110],'speed_scale_roads':['FW_E']}`입니다(값은 float, `==` 성립).
- (b) `runner_config_check`(K7 러너 × K7 망 사본 `3de889f0`): 허용 [81,91,101,110], 분포 없는 값 []. 대조로 v3c2 s31 원본(`597191ac`)은 `v2 network lacks desSpeedDistribution [81, 91, 101]`로 거부됩니다.
- (c) 생성기 가족 옵션 5단계로 `tmp/o4/family_a`와 `family_b`를 만들었습니다.
  - 두 폴더의 파일 6개 sha가 같습니다.
  - reference FW_E = L1(speed_scale 없음), 사상 없음, 러너 80,90,100,110(= K6 러너 바이트 `f0ed036e`)입니다.
  - plant 핀이 overlay 파일과 같고, 사이드카 러너 핀 = plant 핀입니다.
  - `check_family`는 `distribution, written [80,90,100,110], speed_scale_roads []`입니다.
  - `configure-check --sec 1 --overlay-root family_a` → `REPIN_CONFIGURE_OK … family=distribution:written=80,90,100,110 t=1:keys=312,enabled=38`
  - 트리에는 쓰지 않았습니다.
  - 참고: 구현 단계 overlay와 비교하면 `plant_n31_v2.json` 하나만 다릅니다. 차이는 `/qualification` 문구뿐이고, 커밋 5에서 qualification을 고치기 전에 만든 것이기 때문입니다.
- (d) 세 경우 모두 configure 단계 전(가족·핀 단계)에서 끝났고, Traceback은 없었습니다.
  - (1) 사상 키 삭제: `REPIN_ERROR VSL family: Runner RW_ALLOWED_VSL_SPEEDS [81.0, 91.0, 101.0, 110.0] is not the written image [80.0, 90.0, 100.0, 110.0]` (`check_family` 메시지)
  - (2) L1 가족 + 단일값 사상: `REPIN_ERROR VSL family: … [80…] is not … [81…]`
  - (3) K6 러너로 바꿔 끼움: `REPIN_ERROR plant runner_config differs from its pin`(핀 검사가 먼저, 선언대로 사유만 기록)
- (e) `launch_plan.py`의 해당 줄(`load_effective_tuning` → `plant_mode` v2 → `validate_tuning_v2` → `_pin` → `check_family_files`, `:125-141`)을 GWT7 배포 튜닝으로 직접 부르면 single_value가 나오고 통과합니다. `build_plan`은 동결 트리를 요구하므로 함수 단위로 불렀습니다. 실제 발사 경로 확인은 GB-4입니다.

## 6. O-5 L2 all-110 plant 동일성 (FRZ_K6, R-obs1, 읽기 전용) [실행]

- **전제**
  - `freeway_fd.py`, `area_freeway_accounting.py`, `lane_freeway_runtime.py`, `sdmpc_dual.py`, `sdmpc_tangent_runtime.py`의 blob이 K6 = K7 = FRZ_K6 파일과 같습니다.
  - 하네스가 import한 FRZ 파일은 71개입니다. 그중 K6 ≠ K7은 `beta_source.py`, `vissim_stackelberg_adapter.py` 둘뿐이고, diff는 C-10 β 키·주석 덩어리뿐입니다 [읽음].
  - FRZ_K6 전체 파일 목록(경로·크기·mtime)이 실행 전후 같습니다(`o5/frz_listing_{before,after}.json`). FREEZE 표 대비 0/0/0입니다(O-8).
- **하네스**
  - P10 `l0l1_common.py`·`l0l1_scalar.py`·`l0l1_tangent.py`를 바이트 그대로 `o5/`에 복사했습니다(sha 같음). P10 원본은 건드리지 않았습니다.
  - 조건 1용 `o5_cond1.py`를 새로 썼습니다.
  - 조건 4용 `o5_tangent.py`는 P10 tangent에서 다음을 바꿨습니다.
    - 도로별 Trace(FW_E 4축만, FW_W 4축만)
    - `literature_vsl_parameters`를 감싸 n을 셈. 감싼 함수는 산술을 하지 않음
    - 같은 프로세스에서 1축 Dual(110)으로 d1을 측정
    - 끝 속도의 셀별 도함수를 보존
    - ad100·FD는 뺌
  - numba 캐시와 tcache는 `o5/` 아래에 두었습니다.
- **reference 세 벌** (`o5/refs/refs.json`): FRZ_K6 reference(`6c597e25`)에서 FW_E만 바꿨습니다. L2 = K7 객체(JSON 동일), KA = speed_scale만 뺀 것, L1 = 원본 바이트입니다. 세 벌 모두 FW_E 밖에서는 원본과 같습니다.
- 상태는 900, 3600, 4800, 6300입니다.

| 조건 | 판정 | 내용 |
|---|---|---|
| 1 | 통과 | `speed_scale_ratio(knots, 110.0) == 1.0`. 4상태 × FW_E 31셀 모두 `literature_vsl_parameters(L2, v, ρc, a, 110, 110)`의 hex = 입력 hex |
| 2 스칼라 all-110 | 통과 | 4상태 × 2도로에서 rows·ttt·blocks·vehicles·speeds·densities·exposure가 L2 = KA = L1(Python ==, digest). 입력 6종 동일. 스칼라 프로세스에는 Dual이 없음(연산 수 0) |
| 3 fwe100 | 통과 | FW_E는 L2 ≠ KA(예: 4800 ttt 148.051644 대 147.852611), FW_W는 같음 |
| 4 탄젠트 ad110 | **실패** | 아래 |
| 5 digest | 보고 | all-110 digest 8개가 P10 기록과 모두 같음(900 FW_E `8710ad711846`, FW_W `6ec1d1b8462d` …). K1–K6이 all-110 예측을 바꾸지 않았음 |

- **조건 4 세부** (`o5/out/o5_judgement.json`)
  - 성립한 것
    - primal: 4상태 × 2도로에서 ttt·blocks·vehicles·speeds hex가 L2 = KA = L1
    - FW_W: 세 벌 모두 도함수 열 0(빈 사전). FW_W Trace.result()는 L2 = KA = L1(operations 1). 법칙 호출 0
    - FW_E: `event_counts`, `max_tangent_entries`, `exact_tie_axes`, `discrete_dependent_axes`가 L2 = KA. n_L2 = n_KA = 27,809(4상태 모두)
    - d1: 세 프로세스 모두 operations 38, tangent_entries 38(L2 47, KA 9 연산). 선언의 48/10과는 절대값이 1씩 다르지만 차이 38은 같음. 사건 수는 둘 다 {primal_comparisons 2, exact_primal_ties 1}
    - κ 비례: 리프 148개(d_ttt, d_blocks, d_vehicles, 셀별 d_speed, max\|d_speed\|) 위반 0. 최대 상대 편차 1.8e-14 / 8.5e-15 / 5.5e-14 / 2.3e-13
    - 상태마다 0이 아닌 FW_E 도함수 148개, L2 ≠ L1
  - **실패한 것**: `L2 − KA = n × d1`(n × d1 = 1,056,742)

| T | operations L2 − KA | 편차 | tangent_entries L2 − KA | 편차 |
|---|---|---|---|---|
| 900 | 1,056,746 | +4 | 1,056,609 | −133 |
| 3600 | 1,056,730 | −12 | 1,056,406 | −336 |
| 4800 | 1,056,732 | −10 | 1,056,475 | −267 |
| 6300 | 1,056,722 | −20 | 1,056,531 | −211 |

- **원인 진단 (보고만)** (`o5/o5_diag_collapse.py`, `out/diag_collapse_{L2,KA}.json`) [실행]
  - `Trace.scalar`를 감싸 두 가지를 셌습니다. 연산 수는 관문 런과 정확히 같게 재현됐습니다.
    - 값이 정확히 0.0이라 버린 tangent 항목(`sdmpc_dual.py:41`)
    - 항목이 모두 사라져 float로 접힌 결과(`:51`, 그 뒤 연산은 세지 않음)
  - 결과
    - 900: 버린 항목 L2 283,042 대 KA 282,988(+54), 접힘 18,979 대 18,975(+4)
    - 6300: 버린 항목 +125, 접힘 +16
  - 즉 편차는 법칙 밖 하류 연산에서 생깁니다. tangent 성분이 **정확히 0으로 상쇄되는 횟수**가 L2와 KA에서 다르기 때문입니다.
  - [추론] 두 법칙의 접선은 κ배 차이이고, κ배된 부동소수 값에서는 정확한 상쇄(0.0)가 한쪽에서만 일어날 수 있습니다. 도함수 값 자체는 2.3e-13 안에서 비례하므로 K4 코드의 결함 신호는 아니라고 봅니다. 그러나 선언 `:160-163`은 정확한 등식을 요구했고, O-9에 따라 등식을 고치지 않았습니다.

## 7. O-6 110 미만 쓰기 경로 [실행] (`o6/o6_run.py`, `o6_result.json`, `csv/`, `vbs/`)

- 입력
  - K7 배포 튜닝(`319d07aa`)의 `actuation`(깊은 복사, 그대로), vsl_set
  - 발사 mapping `control_mapping_ver2n21.json`(42구간, VSL 66행), 미터 8개(K5 시험과 같음)
  - metadata `suppress_signal_rows`
  - `iter_action_csv_rows`로 만들고, `write_action_csv`와 같은 DictWriter로 직렬화했습니다.
- VBS 검증기
  - 러너 `8c753c08`에서 선언된 7개 프로시저와 그 하위 호출 `InCsvInt`·`CsvNonEmptyCount`를 원문 그대로 뽑았습니다.
  - K7 `lane_native_b110.vbs` 전문을 상수로 넣었고, `RW_OFFSET_WRITER = "intent_only"`(러너 기본값, VBS `:248`)로 두었습니다.
  - `ApplyActionCsv` VSL 규칙(`:1336-1350`)과 VSL 행 수 조건(`:1426-1427`)의 거울을 두었습니다.
  - cscript로 돌렸습니다(파일은 UTF-16 BOM). VISSIM은 쓰지 않았습니다.
- 양성

| 경우 | FW_E 쓰기 | FW_W 쓰기 | 66행·키 66개 | VBS | K2 |
|---|---|---|---|---|---|
| P1 all 110 | 110 | 110 | ✓ | ACCEPT | ok. CSV 바이트 = 사상 키를 지운 사본(항등)의 CSV |
| P2 / P3 / P4 | 81 / 91 / 101 | 110 | ✓ | ACCEPT | ok (written = runner = [81,91,101,110]) |
| P5 구역 80/90/100/110 + FW_W 90 | 81, 91, 101, 110 | 91 | ✓ | ACCEPT | ok |

- 행마다 speed_kph = M(그 구간 명령)이고, 명령은 {80,90,100,110}에 머뭅니다.
- 음성
  - N1(95): `VSL command 95.0 is not one of the mapped commands …`
  - N2(120): 같은 ValueError
  - N3: 90+2e-9는 ValueError, 90+5e-10은 91로 받음
  - N4: P2–P4의 FW_E 34행을 80/90/100으로 바꾸면 VBS가 그 34행을 `IsCsvFiniteNumber`로 거부합니다(`VERDICT ERROR=ACTION_CSV_CONTRACT`, vsl 32/66). K2도 거부합니다.
  - N5: P2–P4를 K6 러너 상수(80,90,100,110)로 검사하면 81/91/101 34행이 거부됩니다. K7 상수로는 ACCEPT입니다.
  - N6: 사상 키를 지운 K7로 P2를 쓰면 FW_E 80(항등 nearest)입니다. 같은 입력을 FRZ_K6 writer(별도 프로세스, `python -B`, FRZ 파일 import 확인)로 쓴 CSV와 바이트가 같습니다(`b00708b8…`).

## 8. O-7 문서·주석·이월 [읽음, grep은 실행]

- `CONTRACT.md` v3c3 항목(K7 :707-723): R3(speed_kph = 분포 번호), 명령 공간 네 곳과 러너 = 상, L2·M 정확값, N12 번호 겹침, N13 FW_W, V-9 가족 검사 위치, N11 `diagnostic_profile.py:29-36, :262-266` 비호환, N16 생성기 가족 옵션의 발사 경로 — 충족합니다.
- `PLANT_PORTING_GUIDE.md` v3c3 머리 절과 VSL 줄 — 충족합니다.
- 주석: `physical_movement_routes.py:456`("kept in v3c3")·`:571`(`routing_v3c3_2`), `area_dynamic_routes.py:6`. `test_n31_urban_batch1.py:59` `'2026-10-01'` — 충족합니다.
- QUALIFICATION(`plant_n31_v2.json` `/qualification`) — 충족합니다.
  - L2 이월 사전값(v3b 기반 단일값 팔 s41/43/47/53)
  - Carlson 계열 형식 기각 χ²/dof 6.41
  - 80 비관(−4.0 % 대 −0.34 %)
  - 단일값 사상과 FW_W(N13)
  - P2 `min_green_sec <= 0` 거부(`physical_ramp_branches.py:57`, 문서만)
  - P7 `state_response` 설치기 있음(`freeway_fd.py:393`)
  - s53 대체
- 이월 사전값 표(`REPIN_V3C3_REPORT.md` §3): b110 segment_params `6b40550a…`, boundary fit `8e4f6047…`, boundary config `54704bee…`, 10490 곡선 `a3390254…`, L2 `4091d6e1…` — 충족합니다.
- **grep 기록(N17) — 미충족(경미)**: §5에 패턴 5행과 범위(W 작업본, vendor 제외), 사유는 있습니다. 그러나 건수는 `2577209b` "28개 파일"과 코드 `v3c1` "20개 파일"에만 있고 나머지 3행에는 없습니다. 선언 `:215`는 "범위·건수·남은 곳의 사유"를 요구합니다.
- 관문이 K7 커밋 트리에서 잰 값(`git grep`, vendor 제외)

| 패턴 | 파일 수 | 줄 수 |
|---|---|---|
| `2577209b` | 29 (보고서 자신 포함; 보고 시점 28) | 57 |
| `226baa37` / `b8e7cf1f` / `ec0cd81d` / `385f40da` | 6 / 6 / 5 / 5 | 6 / 6 / 5 / 5 |
| 코드(`*.py/*.ps1/*.vbs`)의 `v3c1` | 20 | 107 |
| 코드의 `0.94` | 9 | — |
| 코드의 `1.44` | 12 | — |
| `RW_ALLOWED_VSL_SPEEDS = ` | 35 | — |

- `RW_ALLOWED_VSL_SPEEDS = `가 N31 경로에 있는 곳은 `lane_native_b110.vbs` 하나("81,91,101,110")입니다.

## 9. O-8 트리 위생 [실행] (`o8_snapshot.py`, `o8_before.json` 16:48, `o8_after.json` 17:3x)

- W: HEAD `99dc641`, `status --ignored` 0줄(전후).
- GWT7: 관문 뒤 `__tangentcache__` 60개를 `moved_tangentcache/`로 옮겼습니다(목록 `moved_tangentcache_list.csv`, 크기·sha256). 그 뒤 `status --ignored` 0줄입니다. RA-1 재추출 폴더도 GWT7 밖(`tmp/ra1_reextract`)으로 옮겼습니다.
- FRZ_K6(`54d821c1`), FRZ_OLD(`5323faa4`): FREEZE 표 무결, 다시 해시해도 0/0/0입니다. 캐시 파일 수는 0 / 119로 전후 같습니다.
- `D:/VISSIM-merge/frozen/*` 28개 항목은 파일 수·바이트·최신 mtime이 전후 같고, 새 폴더는 없습니다.
- `sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`는 HEAD·status 텍스트 sha·파일 수·바이트·최신 mtime이 모두 같습니다.
- **GWT6 `sim3-n31-v3c3-k6gate`: 불변 조건 미충족.**
  - HEAD `54d821c`는 같습니다.
  - 그러나 무시 파일 `evaluation/controllers/__pycache__/control_area_objective.cpython-312.pyc`(60,292 B)가 17:04:51에 새로 생겼습니다. 그래서 status가 1 → 2줄, 최신 mtime이 바뀌었습니다.
  - 관문 시작 전(16:48)에도 GWT6에는 16:29에 쓰인 `__tangentcache__`가 이미 있었습니다. 다른 세션이 이 트리를 쓰고 있다는 뜻입니다.
  - 관문 프로세스가 쓴 것이 아니라고 보는 근거 [실행·추론]
    - 관문의 모든 Python은 `-B`와 `PYTHONDONTWRITEBYTECODE=1`로 돌렸고, 자식 프로세스 env도 이를 물려받습니다.
    - 관문 스크립트 중 GWT6 경로를 가진 것은 `o8_snapshot.py`(git status와 os.walk, 읽기만) 하나입니다.
  - 그 파일은 지우지 않았습니다(GWT6은 손대지 않는 트리).

## 10. 다음 결정이 필요한 것

1. **DA-2**: `SC103_S_SC6_to_E` 제외(22개)를 받아들일지(선언 보충은 "열거만 더할 수 있음"이라 조건 완화로는 안 됨), 아니면 다르게 처리할지. 배포 튜닝은 이 표를 읽지 않습니다.
2. **O-5 조건 4**: 정확한 연산 수 등식이 부동소수 상쇄 횟수 차이로 깨졌습니다(편차 ≤ 20 ops / 336 항목, 도함수 비례는 2.3e-13). 선언을 고치지 않는 한 실패입니다.
3. O-7 grep 건수 3행 보완(문서).
4. O-8 GWT6 캐시 파일의 출처 확인(관문 밖).
5. 보류: v3c3 s53 런이 끝나면 GB-1 s53과 재추출 바이트 동일 확인(O-0).
- 위 결정 전에는 푸시, `-Freeze -PreflightOnly`, R-obs3·J1 발사를 하지 않습니다(O-9).
- 관문 정의는 바꾸지 않았고, K7에는 손대지 않았습니다(W HEAD `99dc641`, status 0줄).
