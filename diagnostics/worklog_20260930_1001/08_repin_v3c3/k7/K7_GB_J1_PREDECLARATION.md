# K7 오프라인 관문 · GB 런 관문 · J1 기준선 폐루프 사전 선언 (v3c3 재핀 + 단일값 VSL·L2)

- 작성 2026-10-01 15:2x KST. **K7 코드 수정 전**에 고정합니다. W HEAD = K6 `54d821c1…`, `git status --porcelain --ignored` 0줄 [실행]. 고정 수단: 같은 폴더의 `K7_GB_J1_PREDECLARATION.md.sha256`.
- 이 문서는 코드·핀·망·런을 바꾸지 않습니다. 쓴 곳은 `D:/VISSIM_runs/20261001_v3c3/reports/k7/` 하나입니다.
- 표기: **[실행]** 이번에 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단. 줄 번호는 따로 적지 않으면 W @ K6 기준입니다.

## 근거 문서 [실행 sha256]

| 문서 | sha256 | 이 선언이 쓰는 곳 |
|---|---|---|
| 계획 `D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md` | `d4b70c02…` | §3.7 K7 순서(:270-300), §4 파생 표(:314-328), GB 표(:356-371), 멈춤(:373-379), 금지(:381-384), U9(:481), U11(:483) |
| 검토 `…/REPIN_V3C2_PLAN_REVIEW.md` | `bc08f3df…` | B1–B3, N4(:118-125), N5, N7(:141-147), N8(:149-152), N10(:162-165), N11(:167-180), N12, N13(:188-191), N16(:205-207), N18 |
| 목록 `…/repin_v3c2_inventory.json` | `07028e24…` | 52항목(C-1…C-11, V-1…V-12, RA-*, DA-*, N-*) |
| `D:/VISSIM_runs/20261001_v3c3/reports/k1k6/K1K6_IMPLEMENT.md` | `53fa71ed…` | K5에서 K7로 미룬 V-6·V-11(:30) |
| `…/k1k6/GA_RESULTS.md` | `1e6df10e…` | K6 기준 실패 id 집합(§8 :263-280), 하네스 재조준(§2) |
| `…/k1k6/VERIFY.md` | `ab411518…` | 이월 P2(:193-197), P3(:198-202), P6(:208-211), P1(:188-192) |
| `D:/VISSIM_runs/20261001_v3c3/reports/V3C3_BUILD.md` | `820ca005…` | 시드별 v3c3 sha(:60-67), GB-1 정의(§5) |
| `D:/VISSIM_runs/20260930_v3c2/reports/nc_analysis/GATES_AND_COMPARISON.md` | `2cb46af0…` | 시드별 병목 체제(:128-133), fw_e_main(:286), 1099 remain(:327) |
| N1F 2단계 `D:/VISSIM_runs/20260928_n1f_vsl_stage2/reports/fit_results.json` | `4091d6e1…` | L2 정확값 |

- 사용자 결정(10-01, 과제 지시): 9000 s 폐루프는 **VSL을 켠 채**(단일값 DSD + plant 법칙 L2, V0 아님) 돌립니다. 그래서 K7은 재핀 항목 전부에 더해 아래를 **배포 경로에서 켭니다**: 러너 허용 목록 81,91,101,110(V-6), 튜닝의 명령→분포 사상(K5), reference의 L2 `speed_scale`(K4), 생성기 가족 옵션(V-11, U5-a).

---

## 0. 용어

| 이름 | 뜻 |
|---|---|
| W | `D:/VISSIM-merge/sim3-n31-v3c3`, 브랜치 `claude/repin-v3c3-20261001`. K7 편집·커밋은 여기서만 합니다 |
| K6 | `54d821c1e7140d23635f295283849d5a1197624c` |
| K7 | 오프라인 관문(§1)을 모두 통과한, 푸시 직전 W HEAD. 수정 커밋이 생기면 그 새 HEAD가 K7입니다 |
| GWT6 | `D:/VISSIM-merge/sim3-n31-v3c3-k6gate` (detached K6). **손대지 않습니다** |
| GWT7 | `D:/VISSIM-merge/sim3-n31-v3c3-k7gate`. K7 관문 전용 새 작업 트리(`git -C W worktree add --detach <경로> <K7>`). SDMPC 재생 Root와 시험 실행 위치(검토 B3) |
| FRZ_K6 | `D:/VISSIM-merge/frozen/sdmpc31_54d821c1_202610011123` (v3c1 핀 + K1–K6 코드). 읽기만 합니다 |
| FRZ_K7 | 푸시 뒤 W에서 `run_sdmpc_n31.ps1 -Freeze -PreflightOnly`로 만드는 새 동결본(GB-4) |
| R-obs1 | `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31` (v3c1, 결정 61) |
| R-obs3 | `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31` (no-control + obs150, s31, 9000 s; 메인 세션이 발사) |
| NC3 s | `D:/VISSIM_runs/20261001_v3c3/s<s>_v3c3nc/run` (fast_nc, v3c3) |
| M | 명령→분포 사상 `{'80':81,'90':91,'100':101,'110':110}` (`actuation.vsl_command_distribution`, model `single_value`) |
| L2 | `{'law':'carlson','A':1.33,'E':0.87,'alpha':0.0,'speed_scale':{'form':'cubic_lagrange','levels':{'80':0.7225223093088844,'90':0.8119772280655296,'100':0.9006844904146349},'maximum':110.0}}` |
| KA | L2에서 `speed_scale` 키만 뺀 것(A 1.33, E 0.87, b = c/110). "키 없음" 비교 대상 |
| L1 | `{'law':'carlson','A':0.94,'E':1.44,'alpha':0.0}` (v3c1 배포 법칙) |
| κ | 110에서 L2 기울기 / KA 기울기 = 110·b′_L2(110). `_lagrange_slope`로 1.1924542785990417, 단일 호출 Dual 비로 1.1924542785990433 [실행] |
| V | 무제어 결정의 휘발 7필드(GA 선언 §2.1과 같음): `metadata.decision_wall_sec`, `metadata.prediction_wall_sec`, `prediction.wall_sec`, `run_provenance.inputs.state_json.{path,sha256}`, `metadata.run_provenance.inputs.state_json.{path,sha256}` |
| V_s | SDMPC 결정의 휘발: V + pickle 토큰 4종 + 시간 정규식 `(wall\|_sec$\|seconds\|elapsed\|time_s\|timestamp\|started\|finished\|cpu\|pid)`. **이월 P3**: 정규식은 **리프 자신의 키 이름**에만 적용하고, 경로형 키(`/`·`\` 포함 또는 `.py`로 끝남, 특히 `transformed_source_sha256` 아래 키)에는 적용하지 않습니다. 하위 트리 통째 제거는 하지 않습니다 |
| S | 상시 관문(§2.8) |

---

## 1. K7 오프라인 관문 (푸시·동결 전, VISSIM 없음)

### O-0 전제와 트리 규칙

- K7 커밋: W에서만, 명시 경로만, `GIT_AUTHOR_NAME=GIT_COMMITTER_NAME=Ming2you`, `GIT_AUTHOR_EMAIL=GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr`, 메시지 끝 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `--renormalize` 금지.
- 관문은 **커밋된 K7**에서만 판정합니다. 실행 위치는 GWT7(시험·SDMPC)과 FRZ_K6(O-5, 읽기만)입니다. W에서는 관문을 돌리지 않습니다(B3).
- 관문 중 수정 커밋이 생기면 O-1…O-8을 새 HEAD에서 **처음부터 다시** 돌립니다. 관문 정의는 바꾸지 않습니다.
- **s53 입력** (RA-1 s53, RA-4, RA-5가 씀)
  - 원칙: v3c3 s53 출력만 씁니다. 조건은 `s53_v3c3nc/run/run.json` `completed=true` 그리고 `gb1_identity.py judge --seed 53` PASS입니다.
  - 15:2x 현재 상태 [실행]: run.json `completed=false`, `exit_code=null`. 그런데 `run/stdout.txt`에는 `STAGE=SIM_DONE`, `SIM_SEC=9000`(13:39)이 있고, FZP 1,173,499,393 B가 있으며, `run/*.err`는 없고, VISSIM 프로세스는 0개입니다. [추론] VISSIM은 끝났지만 래퍼가 run.json·.err 마무리를 하지 못한 상태로 보입니다. 이 상태로는 GB-1 s53이 PASS할 수 없습니다(run.json 조건).
  - 대체(메인 세션이 고를 때만): v3c2 s53 출력(`D:/VISSIM_runs/20260930_v3c2/s53_v3c2nc/run`)을 씁니다. 근거는 "GB-1 4/4(s31/41/43/47) + N1F G0 8/8"이고, s53 자체의 동일성 증명은 아닙니다. 영수증·QUALIFICATION·REPIN_V3C3_REPORT에 "s53 = v3c2 출력(GB-1 s53 미판정)"이라고 적습니다. 영수증의 망 필드는 v3c2 s53 sha(`c2dd1a48…`)를 그대로 적습니다(바꿔 적지 않음).
  - 대체를 쓰고 나중에 v3c3 s53이 완료되면: GB-1 s53 PASS와, v3c3 s53 재추출의 `boundaries_30s.csv`·`flows_30s.csv`·`cells_30s.csv` 바이트 = 대체 입력의 것을 확인합니다. 하나라도 어긋나면 STOP합니다.

### O-1 시험 묶음 (GWT7, BELOW_NORMAL, `python -B`, `-p no:cacheprovider`)

- 묶음: GA-5와 같은 9묶음(`reports/k1k6/ga/ga5/run_tests_gwt.sh`의 n31·t9·tools·obs·pyt·extra·diag·dprof·new). 경로만 GWT7로 바꿉니다. 여기에 K7 새 시험을 더합니다.
- 기준: K6 실패 id 집합 `reports/k1k6/ga/ga5/logs/k6gate/<묶음>.ids`. diag 65개, extra 11개, 나머지 0개입니다(GA_RESULTS §8).
- **통과 조건**
  1. K7 실패 id 집합 ⊆ K6 실패 id 집합. 이름이 바뀐 시험(예: `test_reference_law_is_l1` → `_l2`)은 K7 보고서의 개명표로 대응합니다. 개명표에 없이 사라진 id는 실패로 봅니다.
  2. K6 실패 → K7 통과로 바뀐 id는 이유와 함께 나열합니다(실패 아님).
  3. K7 새 시험은 모두 통과합니다. 최소 범위는 다음과 같습니다.
     - N8 열거: v3c3 받기. 거부: v3c2(81/91/101 없음), v3c3 + 여분 DSD 94 블록, v3c3 − DSD 101, 구성 14 바이트 변조, vehComp 13번째 행 변경, v3c1(구성 14 없음).
     - C-10 β 원천: 키 `routing_v3c3`/`routing_v3c3_2`, v3c1 원천이 트리에서 빠졌음을 확인하는 시험.
     - V-11 생성기 두 가족(§O-4 c), V-10 L2 상수, C-5 망 상수, `test_n31_urban_batch1.py:59`의 생성일(N11).
  4. **T9**(`test_n31_ad_smoke`, V-10): L2 reference에서 AD = 중앙차분(80/90/100, 상대 1e-4), 110 한쪽 도함수 ≠ 0, FW_W 열 0. 허용 오차를 넓히지 않습니다. 실패하면 STOP합니다(계획 R9).
- 금지 7종은 돌리지 않습니다: `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, real_watchdog.
  - `test_tools_launch.py:175`는 편집만 합니다(C-5).
  - dprof의 `scripts/tests/test_action_csv_vbs_validators.py`는 cscript로 검증기 조각만 돌립니다. VISSIM이 아닙니다(GA-5 선례).

### O-2 생성기·도구 점검 (GWT7, 임시 출력은 `reports/k7/gates/tmp/`)

모두 exit 0, 판정 OK여야 합니다.
- `make_reference_config.py --check`, `make_plant_n31.py --check`
- `make_config_n31.py --check`, `--urban-batch1 --check`, `--urban-batch1 --components U1,U3 --check` (세 벌)
- `derive_ramp_forecast_n31.py --check` (RAMP_FORECAST = v3c3 fit 5시드 유도값)
- `port_profile_v2/extract_port_profile.py --check`, `scripts/build_obs150_detectors.py --check`
- `scripts/derive_unsignalized_validation.py --check` 두 번, 두 sha가 같음
- C-9 생성기 다섯 개의 `--check`, `scripts/preflight_tuning_paths.py` 세 벌
- `repin_scenario_v2.py verify` → `REPIN_VERIFY_OK`
- `repin_scenario_v2.py configure-check --sec 1 --sec 150 --sec 900 --workdir <tmp>` → 세 시각 모두 OK. 구성·분포 열거와 런타임 가족 검사(`runtime_setup.py:246-251`)를 지나야 합니다.

### O-3 허용 diff와 파생 기대값 (계획 GB-3의 오프라인판)

- **경로**: `git diff --name-only 54d821c <K7>`는 다음 합집합 안에 있어야 합니다. 밖의 경로가 하나라도 있으면 STOP합니다.
  - 목록 52항목의 경로
  - 검토 N7(`obs150_contract.py`)·N8·N11의 경로
  - K5에서 미룬 V-6·V-11
  - 새 v3c3 파생 파일, `REPIN_V3C3_REPORT.md`, K7 새 시험
  - v3c1 파일 삭제(계획 §3.7-6)
- **내용**

| 대상 | 기대 | 구속 여부 |
|---|---|---|
| RA-1 추출(fit 5) | checks 18538, 마지막 프레임 8995.1, 망 sha = 시드 v3c3 sha(O-0 대체를 쓰면 s53만 예외로 v3c2 sha, 그 사실을 영수증에 적음) | 구속 |
| RA-1 `boundaries_30s.csv`·`flows_30s.csv`·`cells_30s.csv` | v3c2 `nc_analysis/eo` 같은 시드와 바이트 동일. 추출기 sha가 둘 다 `5fa27047…`입니다 [실행] | 인자(phase-sec, geometry-profile, refined-geometry)가 eo 영수증과 같으면 구속, 다르면 보고 |
| RA-2 s31 geometry | v3c2 eo geometry(s31 `b705f472…`)와 provenance 키(network, source_network, 입력 경로)만 다름 | 구속 |
| RA-3 포트 프로필 | 내용 변화 예상. 포트별 \|Δ\| 표 | 보고 |
| RA-4 RAMP_FORECAST | 새 drain_sec·max_vph 표(v3c1 값과 나란히) | `--check`만 구속 |
| RA-5 unsignalized validation | 수치 변화 | `--check` ×2 동일 sha만 구속 |
| DA-1 β | 키 `routing_v3c3{,_2}`, 파일 `*_v3c3_<날짜>.json`(U8-a). 핀 사상 뒤 β 값 JSON 포인터 차이 0. `check_complete_beta_runtime` 망 sha = `3de889f0…` | 구속 |
| DA-2 도시 묶음 1 표 | sha만 바뀜(unsignalized_turns의 검증 수치는 예외). area 계약 바이트 동일 | 구속 |
| DA-3 선언 20 + transfer + receipt + base | `REPIN_VERIFY_OK`. transfer에 구성 14·vehComp 12행·DSD 81/91/101 기록 | 구속 |
| DA-4 `control_area_membership_213a5d.json` | 망 핀 필드만 바뀜. lineage relFlow 1134/1135 5행은 v3c1 트리 값과 같음. lineage 시험 2개 통과 | 구속 |
| DA-5 obs150 | CSV 바이트 = `108debbb…`(294행). 사이드카는 핀만 바뀜(망 3de889f0, 러너 config 새 sha, 생성기 sha256_lf) | 구속 |
| DA-6 reference | `freeway.vsl_fd_response.FW_E` = 위 L2와 JSON 동일(정확값. 반올림값 0.901/0.812/0.723이면 실패). `vsl_set` [80,90,100,110], transport 불변 | 구속 |
| DA-6 튜닝 세 벌 | `actuation.vsl_command_distribution` = `{'model':'single_value','distribution_by_command':M}`, `vsl_set` [80,90,100,110], `max_vsl_step` 40, `adapter.joint_owner_game.ignore_wall_time_limits` true(현재값 [읽음]) | 구속 |
| V-6 러너 config | `lane_native_b110.vbs`의 `RW_ALLOWED_VSL_SPEEDS = "81,91,101,110"`. 나머지 줄은 바이트 동일 | 구속 |
| N-4 망 사본 | `baseline_s31_v3c3nc.inpx` sha `3de889f0…`, .sig 42개 바이트 불변 | 구속 |
| C-7 obs150 생성기 | 망 상수 `3de889f0…` | 구속 |
| 바꾸지 않는 것 | 러너 VBS `8c753c08…`, `sdmpc.py` VSL 축, 표지 셀 [0,3,5,8,14,18,26,28], 발사기·동결기·`prepare_sdmpc31_network.py` | 구속 |
| QUALIFICATION·CONTRACT·문서 | O-7 목록 | 구속(읽어서 확인) |

### O-4 VSL 가족 일관성

- (a) `vsl_command_distribution.check_family_files`(`vsl_command_distribution.py:159`)를 K7 튜닝 세 벌 × K7 reference × K7 러너 config에 돌립니다. 반환이 정확히 다음과 같아야 합니다: `{'family':'single_value','commands':[80,90,100,110],'written':[81,91,101,110],'speed_scale_roads':['FW_E']}`.
- (b) `repin_scenario_v2.runner_config_check`(`:859`)를 K7 망 사본에 돌리면 81/91/101/110이 모두 망의 분포로 있어야 합니다(N7: 사상의 상 ⊂ 망 DSD). 대조로 v3c2 s31 원본에서는 `[81, 91, 101]` 부재로 거부되어야 합니다.
- (c) **V-11/U5-a/N16**: 생성기 가족 옵션(이름은 구현이 정함, 계획 문구는 `--vsl-family distribution`)이 임시 폴더에 L1 가족 한 벌을 만듭니다. 내용은 reference FW_E = L1(speed_scale 없음), 사상 없음, 러너 80,90,100,110, 그 핀을 담은 plant·사이드카입니다.
  - `check_family`가 `{'family':'distribution',…,'written':[80,90,100,110],'speed_scale_roads':[]}`을 냅니다.
  - 두 번 만들면 sha가 같습니다.
  - 이 가족으로 `configure-check --sec 1`(임시 폴더)이 OK입니다. 이 가족은 커밋하지 않습니다.
- (d) **런타임 거부 쪽(이월 P6)**: 임시 사본으로 `configure-check --sec 1`을 돌립니다.
  1. K7 파일 그대로 + 튜닝에서 사상 키만 지움(L2 + 항등, 러너 81…): 가족 검사(`check_family`, `vsl_command_distribution.py:122`) 메시지로 거부되어야 합니다. 핀은 그대로라 다른 검사에 먼저 걸리지 않습니다 [추론].
  2. (c)의 L1 가족 한 벌 + 튜닝에 단일값 사상을 더함(러너 80…, speed_scale 없음): 가족 검사 메시지로 거부되어야 합니다.
  3. K7 파일 + K6 러너 config(80,90,100,110)로 바꿔 끼움: 거부되어야 합니다. 핀 sha 검사가 먼저 걸릴 수 있으므로 거부 사유는 기록만 하고 가족 메시지를 요구하지 않습니다.
  - 세 경우 모두 VISSIM 없이 configure 단계에서 끝나야 하고, 거부 외의 예외(파일 없음 등)가 나면 하네스 오류로 보고 다시 만듭니다.
- (e) 발사기 쪽 검사(`launch_plan.py:136-140`)를 배포 튜닝으로 직접 부르면 통과해야 합니다. 실제 발사 경로 확인은 GB-4입니다.

### O-5 L2 all-110 plant 동일성, v3c1 R-obs 상태 (FRZ_K6, 읽기 전용)

- **왜 FRZ_K6인가** [읽음]
  - P10 하네스는 상태의 망 sha가 plant manifest의 망 sha와 같아야 돕니다(`scratchpad/v3c1-p10/l0l1/l0l1_common.py:65-72`). 그래서 v3c1 상태는 v3c1 핀 트리에서만 돌 수 있습니다.
  - FRZ_K6은 v3c1 핀에 K4 코드를 얹은 트리입니다.
- **전제 (아니면 STOP, 섞인 코드로 돌리지 않음)**
  - `freeway_fd.py`, `area_freeway_accounting.py`, `lane_freeway_runtime.py`, `sdmpc_dual.py`, `sdmpc_tangent_runtime.py`의 blob이 K6 = K7입니다.
  - 하네스가 import한 그 밖의 저장소 모듈에서 K6과 K7이 다른 곳은 목록에 선언된 덩어리뿐입니다(예: 어댑터 C-10 β 키). 결과에 나열합니다.
- **하네스**
  - P10 `l0l1_*.py`의 사본을 `reports/k7/gates/o5/`에 둡니다. `FRZ`=FRZ_K6, `RUN`=R-obs1이고, numba 캐시와 tcache는 o5 아래에 둡니다. P10 원본은 고치지 않습니다.
  - FRZ_K6의 생성 파일 목록이 실행 전후 같아야 합니다.
- **reference 세 벌**: FRZ_K6 reference(`6c597e25…`) 사본에서 `freeway.vsl_fd_response.FW_E`만 바꿉니다.
  - L2 = K7 reference의 FW_E 객체(JSON 동일)
  - KA = 그 객체에서 `speed_scale`만 뺀 것
  - L1 = 원본 그대로
- **상태**: 900, 3600, 4800, 6300 (P10과 같음)
- **통과 조건**
  1. `speed_scale_ratio(knots, 110.0) == 1.0`. 설치된 FW_E 31셀 행마다 `literature_vsl_parameters(L2, v, ρc, a, 110, 110)`의 hex = `(v, ρc, a)`의 hex. [실행 단위값: b(110) = 1.0, 세 매듭 정확]
  2. **스칼라 all-110**: L2 = KA = L1. 4상태 × 2도로의 모든 리프가 P10 방식(Python ==, float.hex sha)으로 비트 동일이고, 입력도 같아야 합니다. 이 경로는 법칙을 평가하지 않습니다(`freeway_fd.py:239-241`, `area_freeway_accounting.py:375-381`) [읽음]. 그래서 Dual 연산 수는 세 벌 모두 0으로 같습니다.
  3. **대조 fwe100**(FW_E 구역 머리 0/5/10/15 = 100, FW_W 110): FW_E에서 L2 ≠ KA여야 합니다(b(100) 0.90068 대 0.90909). FW_W는 같아야 합니다.
  4. **탄젠트 ad110**(FW_E 4축 + FW_W 4축, forward, P10 방식)
     - primal: L2 = KA = L1, 모든 리프 hex 동일
     - FW_W 도로: 도함수 열 0(세 벌 모두). FW_W 도로의 Trace(하네스가 도로별 Trace를 쓰지 않으면 FW_W 4축만 seed한 별도 실행)의 `Trace.result()` 키 전부가 L2 = KA
     - FW_E 도로 연산 수: `event_counts`, `max_tangent_entries`, `exact_tie_axes`, `discrete_dependent_axes`는 L2 = KA. `operations`와 `tangent_entries`는 각각 **L2 − KA = n × d1**이어야 합니다.
       - n = 탄젠트 명령으로 법칙을 평가한 횟수. L2와 KA를 같은 방법으로 세고, 두 값이 같아야 합니다.
       - d1 = 단일 호출 차이. 110에서 1축 Dual로 L2 48, KA 10 → d1 = 38(연산·항목 둘 다), `event_counts`는 둘 다 {primal_comparisons 2, exact_primal_ties 1} [실행].
       - 같은 탄젠트 런타임 프로세스 안에서 d1을 다시 재고, 판정은 그 값으로 합니다. 38과 다르면 적습니다.
     - FW_E 도함수: 모든 도함수 리프에서 \|t_L2 − κ·t_KA\| ≤ 1e-9·max(\|t_L2\|, \|κ·t_KA\|) + 1e-12. κ = 1.1924542785990433.
       - [추론] 110에서 두 법칙은 b = 1로 같은 점이고 b만 통해 명령에 반응하므로, forward 접선은 b′ 비만큼 정확히 비례해야 합니다. 단일 호출 세 출력의 비는 모두 1.1924542785990433이었습니다 [실행].
     - 상태마다 0이 아닌 FW_E 도함수가 1개 이상 있어야 하고, L2 ≠ L1이어야 합니다.
  5. (보고) all-110 digest를 P10 기록(예: 900 FW_E `8710ad71…`, FW_W `6ec1d1b8…`)과 대조합니다. 다르면 K1–K6 효과인지 원인만 적습니다.
- **"탄젠트 연산 수가 키 없음과 같다"를 문자 그대로 두지 않는 이유** [읽음]
  - 110에서 명령이 탄젠트 스칼라이면, 왼쪽 도함수를 내려고 법칙을 평가합니다(`freeway_fd.py:239-244`).
  - 이때 L2는 3차식(`:90-102`, `:146-147`)을, KA는 나눗셈 한 번(`:149`)을 계산합니다.
  - 그래서 그 자리에서 연산 수가 같기를 요구하면 구성상 실패합니다(검토 B1과 같은 구조).
  - 동일은 법칙이 탄젠트 명령으로 불리지 않는 곳(스칼라, FW_W)에서 요구합니다. FW_E 탄젠트에서는 위의 정확한 차이식을 요구합니다.

### O-6 110 미만 쓰기 경로 (오프라인, GWT7)

- **입력**
  - K7 배포 튜닝 `config_n31_v2.json`(sha 기록)
  - 발사 계획이 가리키는 control mapping(VSL 66행)
  - writer `iter_action_csv_rows`/`write_action_csv`(`vissim_stackelberg_adapter.py:12652-12665`)
  - K2 `make_replay_state_v2.action_contract(…, vsl_contract=n31_common.tuning_vsl_contract(…))`(`:240`, `n31_common.py:232`)
- **러너 검증기**
  - `scripts/run_real_world_stackelberg_controller.vbs`(`8c753c08…`, 불변)에서 다음 프로시저를 원문 그대로 뽑습니다: `ExperimentMetadataValid`, `VslActionKeyValid`, `IsCsvFiniteNumber`, `IsCanonicalCsvInt`, `IsCanonicalNonNegativeInt`, `InDelimitedText`, `IsFiniteNumberInRange`.
  - 상수는 K7 `lane_native_b110.vbs`에서 읽습니다: `RW_ALLOWED_VSL_SPEEDS`, `RW_EXPECTED_VSL_DSD_IDS`, `RW_EXPECTED_VSL_ACTION_KEYS`, `RW_EXPECTED_VSL_ACTION_ROWS`(66).
  - `ApplyActionCsv`의 VSL 행 규칙(15열, 메타데이터, 키, 허용 속도, 중복 키; VBS `:1336-1350`)과 행 수 검사(`:1424-1436`)를 함께 거울로 둡니다.
  - 하네스는 `scripts/tests/test_action_csv_vbs_validators.py:68-112` 방식(cscript, VISSIM 없음)입니다. 금지 시험 `test_b1a_watchdog_attempt_launch`는 import하지 않습니다.
- **양성 경우와 통과 조건**

| 경우 | 명령(JSON, 명령 공간) | 통과 조건 |
|---|---|---|
| P1 | 66행 전부 110 | VSL 66행 110. CSV 바이트 = 같은 입력에서 K7 튜닝의 사상 키만 지운 사본(항등)으로 쓴 CSV |
| P2/P3/P4 | FW_E 전 구간 80 / 90 / 100, FW_W 110 | FW_E 행 = 81 / 91 / 101 |
| P5 | FW_E 구역 80/90/100/110 혼합 + FW_W 90 | 81/91/101/110, FW_W 91(N13) |

  - 공통: 행마다 speed_kph = M(명령), 행 수 66, VBS 검증기가 모든 행을 받고 중복 키 0, K2 action_contract ok(written = runner = [81,91,101,110]), JSON 명령은 80…110 그대로.
- **음성 경우와 통과 조건**
  - N1: 명령 95 → writer ValueError
  - N2: 명령 120 → ValueError(120 확장 없음, N5)
  - N3: 90 + 2e-9 → ValueError. 90 + 5e-10 → 91로 받음(허용 1e-9, `vsl_command_distribution.py:101-111`)
  - N4: P2–P4 CSV의 속도를 80/90/100으로 바꿔 쓰면 VBS `IsCsvFiniteNumber`가 그 행을 거부하고(→ `ACTION_CSV_CONTRACT` 경로), K2 계약도 거부합니다.
  - N5: P2–P4 CSV를 K6 러너 상수(80,90,100,110)로 검사하면 81/91/101 행이 거부됩니다. 받아들여지는 이유가 K7 허용 목록임을 보입니다.
  - N6: K7 튜닝에서 사상 키만 지운 사본으로 P2를 쓰면 nearest+120 경로가 그대로입니다(FW_E 행 80, 항등). 같은 입력을 FRZ_K6의 writer(읽기만, `python -B`)로 쓴 CSV와 바이트 동일해야 합니다.

### O-7 문서·주석·이월 항목 (읽어서 확인, 구속)

- `CONTRACT.md:687-721`: speed_kph = 분포 번호(R3), 네 곳 = 명령 공간이고 러너 = 상, L2·M, 번호 겹침 81/91/101 ↔ FW_W desSpeedDecision(N12), FW_W 법칙 미적합(N13), `diagnostic_profile.py:29-36, :262-266` 비호환(N11), 생성기 가족 옵션의 발사 경로(N16)
- `PLANT_PORTING_GUIDE.md`, `physical_movement_routes.py:456`·`:571` 주석, `test_n31_urban_batch1.py:59`(N11)
- QUALIFICATION(C-2) 문구
  - L2 이월 사전값(v3b 기반 N1F 2단계, 시드 41/43/47/53)
  - Carlson 계열 형식 기각 χ²/dof 6.41
  - 80 방류 비관(예측 −4.0 % 대 관측 −0.34 %)
  - 단일값 사상, FW_W 사상(N13)
  - P2: `min_green_sec ≤ 0`이면 유일한 표도 거부(`physical_ramp_branches.py:57`). 문서화만 하고 코드는 바꾸지 않습니다. 바꾸면 O-3 위반입니다.
  - P7: `state_response` 거부 근거 정정(`freeway_fd.py:393`에 설치기가 있음)
- 이월 사전값 목록(N11, v3c1 MA-1에 해당): b110 segment_params, boundary fit, 10490 측정 곡선(R-5)을 출처 sha와 함께 적습니다.
- `REPIN_V3C3_REPORT.md`에 grep 기록을 남깁니다. 패턴은 `2577209b`, `226baa37`, `b8e7cf1f`, `ec0cd81d`, `385f40da`, 코드의 `v3c1`, 코드의 `0.94`/`1.44`, `RW_ALLOWED_VSL_SPEEDS`이고, 범위·건수·남은 곳의 사유를 적습니다(N17).

### O-8 트리 위생

- W: `status --porcelain --ignored` 0줄(관문 전후)
- GWT7: 관문 뒤 `__tangentcache__`를 `reports/k7/gates/moved_tangentcache/`로 옮기고(목록 csv) `status --ignored` 0줄
- FRZ_K6·FRZ_OLD: `FREEZE.json` 표 대비 0/0/0, 생성 파일 목록 불변
- GWT6과 다른 작업 트리(`sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`): HEAD·status·최신 mtime 불변. `D:/VISSIM-merge/frozen/*` 기존 폴더 수정 0

### O-9 오프라인 멈춤 규칙

- O-1…O-8 중 구속 조건 하나라도 실패하면 STOP합니다. 푸시·동결·발사하지 않고, 원인 키 목록과 함께 보고합니다.
- 허용 오차와 허용 목록은 넓히지 않습니다.
- 보충 선언은 열거만 더할 수 있습니다(GA 보충 1·2와 같은 방식, 해당 관문 실행 전, sha 고정). 조건을 약하게 바꾸는 보충은 무효입니다.

---

## 2. 런 쪽 GB 관문 (푸시·동결 뒤)

### GB-4 (전제) 푸시·동결·사전점검

1. O 전부 통과 → `git -C W push -u origin claude/repin-v3c3-20261001`. 푸시한 head = K7입니다.
2. W에서 계획 §6.3 명령(`:416-430`) 그대로 `-Freeze -PreflightOnly … -Name sdmpc31_v3c3_nc_s31 -Seed 31 -Controller no-control -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3`을 돌립니다.
3. 통과 조건(로그)
   - `FREEZE_OK … head=<K7>`
   - `FREEZE_VERIFIED … head=<K7>`
   - `LAUNCH_PLAN_DETAIL … network_sha=3de889f0… detectors=294 controller=no-control`
   - `NETCOPY … sha256=3de889f0… sig=42`
   - `PREFLIGHT PROVENANCE_OK`
   - `EXIT … code=0`
   - 가족 검사(`launch_plan.py:136-140`)가 거부하지 않음
   - FRZ_K7 `FREEZE.json` `git.head` = `git rev-parse origin/claude/repin-v3c3-20261001`

### GB-5 R-obs3 완료 (메인 세션이 발사)

통과 조건:
- 발사기 `EXIT … code=0`
- 런로그
  - `DECISIONS_OK=61`, `DECISIONS_FAILED=0`
  - `ERROR=`로 시작하는 줄 0
  - `STAGE=SIM_DONE`, `SIM_SEC=9000`
  - `OBSERVATION_FAILURES=0`, `SIGNAL_FAILURES=0`, `ACTION_FORMAT_FAILURES=0`, `COM_FAILURES=0`
- t = 1 configure 통과. 런타임 가족 검사를 배포 경로에서 처음 지나는 지점입니다.
- 무제어 신호 기준(앞 세 값은 v3c1 R-obs 런로그 값과 같음 [실행 tail])
  - `SIGNAL_WRITE_ATTEMPTS=8`(미터뿐)
  - `SIGNAL_MIDBLOCK_COM_SKIPS=0`, `SIGNAL_MIDBLOCK_PLAN_SKIPS=24`
  - `signal_readback.csv`에 `sg_no ≥ 9` 행 0
- `vsl_readback.csv` 16,104행(61 × 66 × 4)이 모두 requested 110 = readback 110, ok = 1
- 런 폴더와 런로그에 `RW_*` 누출이 없음

### GB-6 짝: R-obs3 FZP 대 NC3 s31 FZP (0.10 s 프레임 제외)

- 대상
  - R-obs3: `vissim_eval\sdmpc31_sdmpc31_v3c3_nc_s31_001.fzp`
  - NC3 s31: `run\vissim_eval\baseline_s31_v3c3nc_001.fzp`
  - 도구: P10 `pair/fzp_bytecompare.py`·`pair_metrics.py` 사본(경로만 바꿈)
- 통과 조건
  1. 헤더는 `* File:`과 `* Date:` 두 줄만 다릅니다.
  2. R-obs3에만 있는 SimSec 0.10 행을 빼면 데이터 부분이 바이트 동일합니다. 그 sha = NC3 s31 payload sha = v3c2 s31 payload `8be8b274…`(GB-1)입니다.
  3. 파일 크기 차 = 헤더 차 + 0.10 s 행 바이트로 정확히 설명됩니다(v3c1은 145 B).
  4. 프레임을 맞춘 스캔에서 `stage1_report.pairing_check(t_act=None)` ok, 네 지표 차 0.000000.
  5. 런타임 `.err`(R-obs3 `network\…_001.err` 대 NC3 `run\…_001.err`)의 제거 대수와 remain이 같습니다. 그 밖의 줄 차이(`Stop the simulation?` 등)는 보고만 합니다.
- 통과하면 R-obs3는 짝 비교에서 NC3 s31을 대신할 수 있습니다(s31 한정).

### GB-7 T5 (Root = FRZ_K7, 무제어 재생)

- `test_g1_frame` PASS
  - 명령: `N31_G1_STATE=<R-obs3>\decisions_…\state_000900.json`, `python -B -m pytest -p no:cacheprovider …/test_n31_initialize.py::BinningTests::test_g1_frame`, GWT7에서 실행
- 결정 61/61 재생
  - FRZ_K7 `make_replay_state_v2.py prepare` → `replay_decision_n31.ps1 -Root <FRZ_K7>`
  - 통과 조건
    - ps1 자체 판정(`--tuning`, K2 소속 검사)과 `--tuning` 없는 compare가 둘 다 61/61 IDENTICAL
    - action JSON 전체가 61/61 같음. 예외는 V뿐이고, **ulp 예외도 provenance 예외도 없습니다**(기록 Root = 재생 Root = FRZ_K7, 기록도 K1 코드)
    - CSV 바이트와 정수 리프가 61/61 같음
- 해시 시드 A/B
  - 4050, 4500, 9000 × `PYTHONHASHSEED` {미설정, 0, 2}
  - 같은 T의 세 실행에서 action JSON(V 제외)과 CSV가 바이트 동일
- 다르면 그 필드를 적고 STOP합니다. K1 범위를 넓히지 않습니다(계획 §5.3).

### GB-8 L2 all-110 동일성, v3c3 R-obs 상태 (Root = FRZ_K7, 읽기 전용)

- O-5와 같은 하네스와 판정입니다. 다른 점은 다음뿐입니다.
  - FRZ = FRZ_K7, RUN = R-obs3, 상태 = 900, 2700, 4800, 6300(계획의 2700·6300 포함)
  - reference: L2 = FRZ_K7 reference 그대로, KA = `speed_scale`만 뺀 것, L1 = FW_E만 L1으로 바꾼 것
- 통과 조건 = O-5의 1–4 그대로. 실제 배포 코드와 핀에서 K4 활성 경로가 처음 실행되는 지점입니다(이월 P6).
- digest를 기록합니다.

### GB-9 반사실 SDMPC 결정 (Root = GWT7, 도구 = FRZ_K7, wu-link, K7 배포 튜닝)

- **실행 목록**
  - 900 r1, r2
  - 2700 r1
  - 4950 r1(`PYTHONHASHSEED` 미설정), r2(0), r3(2)
  - 6300 r1
  - 7회, 한 번에 하나, BELOW_NORMAL
- **직전 행동**: R-obs3의 `action_<T−150>`입니다. 무제어 기록이라 `sdmpc_state`가 없으므로 `load_prices`는 `first_sdmpc_decision`으로 시작합니다.
  - 이월 P1: 정책 토큰 불일치는 생기지 않습니다. 생기면 하네스 오류로 기록하고 STOP합니다.
- **통과 조건**
  1. S(§2.8). ps1 exit 2는 무제어 기록 대비 구성상 DIFFERENT입니다(T5-B 선례). 판정은 파일로 합니다.
  2. provenance
     - `replay_run.json root` = `workspace_root` = GWT7, imported 모듈은 모두 GWT7 아래
     - `inputs.tuning_json.sha256` = K7 `config_n31_v2.json`
     - `inputs.adapter_py.sha256` = K7 blob
     - 탄젠트 트레이스 `transformed_source_sha256`에 `freeway_fd.py`가 K7 blob sha로 있음(K4 코드가 계측·실행됨)
     - `metadata.lane_plant_install_check.declared` = `['vsl_fd_response','component_vsl_transport']`이고 설치값 = reference(speed_scale 포함)
  3. VSL
     - 블록 0의 모든 VSL 축 허용집합 = (80, 90, 100, 110). `max_vsl_step` 40이고 집합 폭이 30이라 직전 명령과 무관하게 전체 집합입니다.
     - action JSON `vsl` 값 ⊂ {80,90,100,110}
     - CSV VSL 66행 ⊂ {81,91,101,110}, 행마다 CSV = M(JSON 해당 구간 값)
     - K2 `--tuning` action_contract ok
  4. 미터
     - RM_C10490 미터 축 허용집합에 3이 없음
     - `metadata.lane_ramp_head_service_normalisation.dropped` = `{'RM_C10490': {'3': '2'}}`
     - `physical_ramp_service_normalisation.dropped` = `{}`
  5. 결정성: 900 r1 = r2, 4950 r1 = r2 = r3. 비교 대상은 CSV 바이트, progress `objective`·`held_objective` repr, `CONTROL_FIELDS` 7, 탄젠트 트레이스(V_s, 리프 규칙), derived입니다. action JSON 차이는 V_s뿐이어야 합니다.
- **보고**: 블록 0에서 쓴 VSL(110 미만이 있었는지, 어느 구역·수준인지), 미래 블록 계획 VSL, 미터 녹색

### GB-10 110 미만 쓰기 경로, 재생 안에서 (GWT7)

- (a) GB-9 결정 하나(900 r1)의 action JSON과 그 재생의 유효 튜닝(provenance `inputs.tuning_json`)을 씁니다. FW_E 구간 명령만 80, 90, 100(세 변형)과 O-6 P5 혼합으로 바꾸고, 같은 프로세스에서 K7 `write_action_csv`로 씁니다. 그 뒤 다음을 돌립니다.
  - `area_leader_objective.verify_joint_written_action`(`:501`)식 행 재생성 일치
  - K2 `--tuning` action_contract
  - O-6과 같은 VBS 검증기 하네스
- (b) GB-9에서 블록 0이 실제로 110 미만을 쓴 결정이 있으면, 바꾸지 않은 그 결정에 같은 검사를 합니다. 이것이 더 강한 증거이고, 어느 결정인지 적습니다.
- 통과 조건 = O-6의 P2–P5와 N4·N5 조건. 이 관문으로 K5 활성 경로(사상 writer)와 K2 소속 검사의 110 미만 경우가 재생 산출물에서 실행됩니다(이월 P6).

### GB-11 = J1 U9-a 감사 (§3.4)

### GB-13 RM 팔 동일성 (검토 N10)

- 기본은 **보고만**입니다. v3c3 RM s31/s41 FZP가 NC3 같은 시드와 첫 규칙 쓰기 시각 t_rw 전까지 같은지 적습니다.
  - t_rw는 prepared `rule_policy.json`·`rule_runtime.txt`에서 읽어 결과에 적습니다. 계획은 900 s로 추론했습니다.
- **구속으로 올리는 조건**: v3c3 RM 결과를 열기 전에, v3c1 RM s31/s41 대 v3c1 NC s31/s41 FZP에서 t_rw 전 프레임이 바이트 동일함을 보여야 합니다(fit 시드라 허용). 그렇게 확인되면 같은 t_rw로 v3c3 RM s31/s41에 구속을 적용합니다.
- s37 RM·NC는 run.json의 `completed`·`exit_code` 두 필드만 봅니다.

### GB-12 U1 T1 재집계 (선택, 보고만)

### 2.8 상시 관문 S (검토 N4)

- **재생·반사실마다**
  - 어댑터 exit 0
  - 결정 폴더에 `action_<T>.error.txt` 없음
  - stdout·stderr·ps1 출력에 `DECISION_FAILED` 없음
- **런마다**(R-obs3, J1, 이후 모든 제어 런)
  - `DECISIONS_FAILED=0`, `ERROR=`로 시작하는 줄 0
  - 발사기 `EXIT … code=0`, `STAGE=SIM_DONE`
  - `ACTION_FORMAT_FAILURES=0`, `COM_FAILURES=0`, `SIGNAL_FAILURES=0`, `OBSERVATION_FAILURES=0`, `SIGNAL_NAME_RULE_FALLBACKS=0`
- **검토 N4 정정** [읽음]
  - 이 러너는 결정 실패가 있으면 끝에 `ERROR=RUN_INTEGRITY_FAILURE`를 쓰고 exit 3으로 끝납니다(`run_real_world_stackelberg_controller.vbs:585-591`).
  - 그러나 실패 구간 동안 plant는 직전 DSD·녹색으로 계속 돕니다(`:1241-1252`). 그래서 실패 구간이 남은 런은 결과가 오염된 런이고, 이 관문이 그런 런을 막습니다.

---

## 3. J1 기준선 폐루프

### 3.1 시드: **s31, s41, s43** (fit 시드만, 봉인 37/59/61/67 제외)

- **GB-1**: 세 시드 모두 PASS입니다(`reports/gb1_result_s{31,41,43}.json` `pass=true`) [실행]. 같은 시드 NC3가 있어 짝이 바로 섭니다. s53은 위 O-0 상태라 고르지 않았습니다.
- **체제가 갈립니다** [읽음 `GATES_AND_COMPARISON.md:131,133`; GB-1에 따라 v3c3 궤적 = v3c2 궤적]
  - B2(셀 19–24) 60 km/h 미만 150 s 구간 수, s31/41/43/47/53 = 2/14/8/9/14. 첫 구간 시작 3300/1800/2400/2100/1950 s
  - B1(셀 8–13) 같은 값 = 9/10/24/7/27
  - 셋으로 고르면: s31 = B2 경미·늦음, s41 = B2 이르고 김, s43 = B1 가장 김. s47은 B2가 s43과, s53은 s41과 비슷합니다.
  - VSL이 작동할 상황(B2 혼잡)과 작동하지 않아야 할 상황을 모두 담습니다 [추론].
- **파이프라인 연결**
  - s31은 R-obs3·GB-6/7의 시드입니다.
  - s31과 s41은 v3c3 RM 팔이 있어 나중에 같은 시드 3자(NC·RM·SDMPC) 비교가 됩니다(계획 §6.1).
  - 31/41/43은 v3c NC 1차와 U1 T1 3시드 점검에서 쓴 조합과도 같습니다 [읽음 memory].
- **단서**
  - 세 시드 모두 plant 파생(RA-1…RA-5, fit 5시드)의 표본 안입니다. s41·s43은 L2 적합 시드이기도 합니다(v3b 기반 N1F, 41/43/47/53). 일반화 주장은 하지 않습니다.
  - v3c2-s31은 끝날 때 입력 1099 remain이 122대입니다(다른 시드 0) [읽음 `:327`]. 그래서 s31의 ④가 흔들리기 쉽습니다.

### 3.2 발사 (메인 세션이 발사; 이 선언은 형식만 고정)

- **전제**
  - GB-4…GB-10 전부 통과, R-obs3 S 통과
  - FRZ_K7 = 푸시한 K7
  - 발사 직전 VISSIM 수 확인, 대상 폴더 없음, D: 여유 ≥ 30 GB(계획 §6.3 관례), `STOP` 표시 없음
- **사전점검**(이름마다, FRZ_K7에서, `-Freeze` 없이): `run_sdmpc_n31.ps1 -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_j1_s<S> -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3`
  - 로그 조건: `FREEZE_VERIFIED … head=<K7>`, `LAUNCH_PLAN_DETAIL … network_sha=3de889f0… controller=wu-link`, `NETCOPY … sha256=3de889f0… sig=42`, `PREFLIGHT PROVENANCE_OK`, `EXIT … code=0`
- **발사 줄**(hybrid 관행, U11): `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_j1_s<S> -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3 > D:\VISSIM_runs\20261001_sdmpc31_v3c3\wmi_sdmpc31_v3c3_j1_s<S>.log 2>&1'; CurrentDirectory = '<FRZ_K7>'}`
  - 같은 dev 런과 동시에 띄울 때는 `-AllowConcurrentDev`를 붙입니다.
  - 발사마다 시각·PID·VISSIM 수·명령을 `wmi_launch_lines.txt`에 적습니다.
- **좌석**
  - 발사기 규칙상 dev(sdmpc) VISSIM은 동시에 최대 2개입니다(`run_sdmpc_n31.ps1:84-87`). PC 전체 상한은 4개입니다(memory).
  - 순서는 메인 세션이 정합니다. 판정에는 영향이 없습니다. 배포 튜닝의 `ignore_wall_time_limits: true` 때문에 결정이 벽시계에 따라 달라지지 않기 때문입니다 [읽음 `config_n31_v2.json`, 추론]. 아래 J1-A에서 결정마다 확인합니다.
  - 예상 벽시계는 SDMPC 결정 약 600 s × 55 + 예열로 런당 약 9–11 h입니다 [읽음 T5 599.9–653.3 s, hybrid 577 s; 추론].
- **해시 시드**: `PYTHONHASHSEED`는 provenance에 기록되지 않습니다(코드 grep 0건 [실행]). 증거는 발사 줄과 J1-R 재생입니다.
- **감시**: `StallSec`은 기본 2400(`launch_plan.py:41`)입니다. kill은 소유 PID만 합니다(`-NoGlobalKill`).

### 3.3 런 유효성 J1-A (구속, 시드마다)

- **S 전부**
- **신호**
  - `SIGNAL_MIDBLOCK_COM_SKIPS > 0`(hybrid s31b 선례 1,320 [실행])
  - `signal_readback.csv`에 `sg_no ≥ 9` 행 0(hybrid s31b 0/54,502 [실행]; memory `vissim-midblock-sg-com-red-env-leak`)
- **결정**
  - 61개: T < 900은 예열 no-control 6개, T ≥ 900은 wu-link 55개(`launch_plan.py:40`)
  - T ≥ 900인 모든 action JSON `metadata.sdmpc_active` true
  - 모든 `action_<T>.decision_budget.json`에서 `unlimited_time: true`, `expired_stage: null`, `output_completed: true`(v3c1 R-obs 1·900, hybrid s31b 600에서 같은 필드·값 확인 [실행])
- **provenance**
  - `FREEZE_VERIFIED head=<K7>`
  - 튜닝 sha = K7 `config_n31_v2.json`
  - 망 사본 sha = `3de889f0…`. 세 시드 모두 s31 망 파일이고, 시드는 러너가 COM `RandSeed`로 덮습니다(`run_real_world_stackelberg_controller.vbs:516`)
- **VSL 상자**: 연속 결정 사이 구역별 \|Δ명령\| ≤ 40(`max_vsl_step`). 블록 0 VSL 축 허용집합 = (80,90,100,110)
- **미터**: RM_C10490 쓴 녹색에 3이 없음(K3)
- **J1-V 짝 유효성**
  - J1 FZP에서 0.10 s 행을 빼고 NC3 같은 시드와 `pairing_check(t_act=900)`을 돌리면 ok여야 합니다. 900 s 전 프레임과 입력 진입 시각이 같아야 한다는 뜻입니다.
  - 근거 [읽음 memory·P10]: hybrid wu-link s31은 v3c1 NC와 0–900 s가 같았고, R-obs는 NC와 전 구간이 같았습니다.
  - s41·s43에서 "s31 망 파일 + RandSeed 덮기" = "시드 망 파일" 동등성은 처음 시험합니다 [추론]. fast_nc도 COM으로 시드를 씁니다(`D:/VISSIM-merge/sim3/diagnostics/fast_nc_runner.vbs:106`).
  - 실패한 시드는 짝 분석에서 빼고 보고합니다. 2개 이상 실패하면 J1 분석 전체를 STOP합니다.
- **실패하면**: 그 런은 무효이고, 보고합니다. 재발사는 사용자 결정 뒤에만 합니다.

### 3.4 U9-a 감사 (구속; 계획 GB-11)

런마다, 결정 T(61개), VSL 행 r(66개)마다 다음 사슬이 끊김 없이 이어져야 합니다.

1. action JSON `vsl`(명령): 값 ⊂ {80,90,100,110}, 행 r의 구간 값 = c
2. 어댑터 CSV `decisions_<name>\action_<T>.csv`: speed_kph = M(c). 집합 ⊂ {81,91,101,110}. 80/90/100/120은 0행
3. 러너 행동 로그 `action_<name>.csv`: (T, dsd_no) 행이 있고, speed_kph = 2의 값, readback 열 = "m\|m"(클래스 10\|70). VBS가 `:1444-1466`에서 쓰고 되읽은 뒤 `:1491`에서 이 로그에 적습니다.
4. `decisions_<name>\vsl_readback.csv`(`:417`, `:1970-1978`): (T, dsd)마다 클래스 10/20/30/70 네 행, requested = m, readback_distribution_no = m, ok = 1, stage immediate. 총 16,104행입니다.
5. c < 110인 모든 (T, r)에서 m ∈ {81,91,101}이 2·3·4에 모두 있습니다. 수준별·도로별 건수를 적습니다.

- **통과**: 1–5의 불일치 0, ok ≠ 1 행 0, `ERROR=VSL_COM_WRITE_READBACK`·`ERROR=ACTION_CSV_CONTRACT` 0
- **공허 규칙**: 세 런 모두 110 미만 쓰기가 0건이면 "공허 통과"로 적습니다. 네이티브 110 미만 쓰기는 여전히 미검증이므로, U9-b(탐침 런, 발사기 컨트롤러 목록 확장 필요; 계획 `:481`)를 사용자에게 묻습니다.
- **보고만**: FZP `DESSPEED`로 차량 수준을 봅니다. (T, FW_E 구역)마다 m < 110이면, (T, T+150] 안에 그 구역 표지 결정점 하류에서 처음 관측된 차량 중 희망속도 ∈ [m−1, m+1]인 비율을 적습니다. 110 구역은 [98, 140] 비율을 적습니다. 램프 합류 차량(17–19 %)은 명령을 받지 않으므로 따로 셉니다.

### 3.5 VSL 선택 통계 (보고)

- 런별과 세 런 합계로 적습니다. 대상은 SDMPC 결정 55개, FW_E 구역 머리(`metadata.fw_vsl_zone_heads_FW_E`)와 FW_W 구역입니다.
  - 구역별 선택 명령의 분포(80/90/100/110 건수)
  - 110 미만을 하나라도 쓴 결정의 비율(도로별), 첫 시각, 최장 연속 길이, 전이 행렬
  - 미래 블록 1·2 계획 VSL
  - 110 미만 결정과 110 결정의 `objective`/`held_objective`
  - 110 미만 구역 노출(veh·km, FZP)
  - 미터 8개 녹색 분포
- 계획 R8에 대한 기록: L2의 110 좌기울기는 0.010840으로 L1 0.009091보다 가파릅니다. 그래서 SDMPC가 110을 떠날지는 사전에 알 수 없습니다 [추론]. 이 절의 수치가 그 답입니다.

### 3.6 분석: 같은 시드 짝, 네 지표

- **도구**
  - `D:/VISSIM-merge/tools/stage1`: common `e000c69e…`, scan `651c4f51…`, uninserted `19eba94e…`, report `cb4ccc3a…` [실행 sha]
  - 드라이버: N1F 0단계 방식(`stage0_metrics.py` `b1101969…`). 출력은 `reports/k7/j1/`에만 씁니다. 런 폴더에는 쓰지 않습니다.
- **입력**
  - J1: `vissim_eval\sdmpc31_sdmpc31_v3c3_j1_s<S>_001.fzp`(0.10 s 행 제외), `network\…_001.err`
  - NC3: `run\vissim_eval\baseline_s<S>_v3c3nc_001.fzp`, `run\…_001.err`
- **지표**(정의는 N1F `N1F_STAGE0_FOUR_METRICS.md` §1, P10 `PAIR_REPORT.md` §4와 같음)
  - ① `fw_e_main` 7링크(74, 10699, 2, 10613, 119, 10702, 24)
  - ② 동측 국소 19링크(`east_link_sets_source.json`)
  - ③ Ω(635링크)와 그 부품 ③u `urban_omega`
  - ④ 전체 1,236링크 + 미삽입, 그리고 ④a·④b
  - 미삽입은 6런(J1 3 + NC3 3) 어디서든 줄이 선 입력(끝 remain > 0 또는 큐 > 4 sd)의 합집합 하나를 모든 런에 같게 적용하고, 시드별 NC 앵커로 재구성합니다.
  - Ω 분해: fw_e_main, fw_w_main, onramp, offramp(Ω 안), urban_omega(`stage0_omega_split.py` 방식)
- **적분**: FZP 프레임 5.1–8,995.1 s의 사다리꼴, 150 s 칸
- **통계**
  - d_s = J1_s − NC3_s. 시드별 d, 평균, sd, 90 % CI = 평균 ± 2.920·sd/√3(t0.95(2)), 부호 일치 수, 평균/NC %
  - 150 s 칸별 d 시계열(① ③)에 VSL 작동 시각을 겹쳐 그립니다.
  - s31에서는 R-obs3 − NC3 = 0을 함께 적어 점검합니다(GB-6).
- **잡음 참고**(판정 기준 아님)
  - N1F 0단계의 짝 차 sd: ① 104, ② 115, ③ 102, ③u 8, ④ 63 veh·h(개방 루프 v3b 팔)
  - k = 3의 90 % 반폭으로 환산하면 약 ① 175, ② 194, ③ 172, ③u 13, ④ 106 veh·h입니다(1.686 × sd).
  - 폐루프 잡음은 이보다 클 수 있습니다 [추론].
- **해석 규칙(고정)**
  - J1은 **판정을 내리지 않습니다**. 수준값과 짝 차만 적습니다.
  - CI가 0을 벗어난 칸은 "관측된 차이"로만 적고, 다중 비교(지표 5개 이상)와 §3.7 단서를 함께 적습니다.
  - "SDMPC가 이긴다/진다"는 문장은 쓰지 않습니다.

### 3.7 J1 단서 (보고서 머리에 그대로 둠)

1. **SC1001 EB 진출 배수 결함이 남아 있습니다. 그래서 J1은 기준선이고, 컨트롤러 판정이 아닙니다.**
   - plant의 진출 배수: 10491(FW_W OR_D_W)과 10481(FW_E)이 약 219 veh/h입니다. off-ramp movement 용량이 정규화 상수 206.53/차로이기 때문입니다.
   - VISSIM 실측은 856–925 veh/h입니다.
   - 그래서 plant는 38.6대 저장고를 T+300 s 안에 채우고(9/9 상태), FIFO 상한으로 FW_W 단면을 막습니다. 또 SC1001 p3 녹색을 FW_W 처리량으로 착각합니다.
   - 근거 [읽음]: `scratchpad/fww-struct/FWW_STRUCT_PROPOSAL.md:5, :34, :86`, memory `vissim-fww-offramp-drain-206-20261001`
   - 사용자 결정(10-01)은 이 결함을 v3c3에서 C3 v2 나머지보다 먼저 고치는 것입니다. K7에는 들어가지 않습니다.
   - 따라서 J1의 SDMPC 결정(도시 현시·미터·VSL)은 알려진 오류가 있는 plant에 대해 최적화된 것입니다.
2. k = 3이고 모두 fit 시드입니다(표본 안). 봉인 시드는 없습니다.
3. L2
   - Carlson 계열은 형식 기각(χ²/dof 6.41)입니다.
   - 80 방류를 비관합니다(−4.0 % 대 −0.34 %).
   - v3b 기반 팔에서 맞춘 이월 사전값입니다.
   - 단일값 VSL도 VISSIM 방류를 늘리지 않았습니다(N1F D1). L2의 목적은 plant가 VSL의 허구 이득을 믿지 않게 하는 것입니다.
4. FW_W 명령도 81/91/101로 쓰입니다. 그런데 FW_W plant 법칙은 legacy cap이고 단일값으로 맞춘 적이 없습니다(N13).
5. F10/F11과 도시 묶음 2(C3·C2·C6)는 들어 있지 않습니다.
6. `PYTHONHASHSEED=0`으로 고정했습니다. K1이 알려진 순서 의존 하나를 없앴고, 다른 set 순회는 순서와 무관합니다(검토 N18).
7. 제어는 900 s부터입니다(예열 no-control). 세 시드 모두 s31 망 파일에 시드를 덮어 씁니다(J1-V가 확인).
8. 잡음 참고값은 개방 루프 설계에서 온 것입니다. 폐루프 잡음은 모릅니다.

### 3.8 J1-R 재현 표본 (보고, 구속 아님)

- 대상: s31 결정 900, 110 미만을 처음 쓴 결정(없으면 4950), 9000
- 조건: Root = GWT7, 도구 = FRZ_K7, `PYTHONHASHSEED` 0과 미설정
- 볼 것
  - ps1 `--tuning` 판정 IDENTICAL
  - CSV 바이트, `CONTROL_FIELDS`, 목적함수 repr가 기록과 같음
  - action JSON 차이는 V_s와 Root 의존 필드뿐이고(`workspace_root`, `numsim_repo_root`, `inputs.*.path`, imported 경로, `transformed_source_sha256` 경로 키, 그리고 경로를 담아 다시 계산되는 `execution_fingerprint_sha256`), 그 밖의 sha 값(모듈·입력·`numsim_src_sha256`)은 기록과 같음
- 다르면 사용자에게 보고합니다. J1 런의 유효성은 바뀌지 않습니다.

---

## 4. 순서와 멈춤 규칙

| 순서 | 단계 | 실패하면 |
|---|---|---|
| 1 | K7 편집·커밋(W) → GWT7 생성 → O-1…O-8 | STOP. 푸시·동결 없음 |
| 2 | 푸시 → FRZ_K7 + GB-4 | STOP. R-obs3 발사 없음 |
| 3 | R-obs3(메인 세션) → GB-5, S | STOP |
| 4 | GB-6 | STOP. 같은 러너 동등성이 J1 짝의 전제이기 때문입니다 |
| 5 | GB-7(해시 차이 포함) | STOP. K1 범위를 넓히지 않습니다 |
| 6 | GB-8, GB-9, GB-10 | STOP |
| 7 | (병행) RM v3c3 → GB-13 | 보고만(구속 조건이 증명되면 구속) |
| 8 | J1 사전점검 → J1 발사(메인 세션) | 사전점검 실패 시 발사하지 않음 |
| 9 | J1-A, J1-V, U9-a | 런 무효 또는 STOP(§3.3·§3.4) |
| 10 | §3.5–3.6 분석·보고 | — |

- GB 판정과 J1 분석은 이 선언과 보충(열거만 허용) 그대로 합니다. 결과를 본 뒤 조건을 바꾸지 않습니다.

## 5. 금지와 자료 규율

- 금지 시험 7종은 돌리지 않습니다(§O-1).
- VISSIM 시작·종료는 하지 않습니다(발사는 메인 세션). 기존 `D:/VISSIM-merge/frozen/*`는 수정하지 않습니다. 새 동결은 `run_sdmpc_n31.ps1 -Freeze -PreflightOnly`로만 만듭니다.
- 다른 작업 트리(`sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`, `-k6gate`)는 건드리지 않습니다.
- 커밋은 W에서만, 명시 경로로 합니다. 푸시는 §4 단계 2에서만 합니다.
- s37/59/61/67 결과는 열지 않습니다(s37은 run.json 두 필드만). 재생은 한 번에 하나, BELOW_NORMAL로 돌립니다.

## 6. 이 선언을 쓰며 한 일 (공개)

- **[실행]**
  - 근거 문서 sha 계산
  - W status 0줄, R-obs3 폴더 미존재, VISSIM 프로세스 0
  - v3c3 NC run.json 다섯 개(s31/41/43/47 완료, s53 미완료), s53 `run/` 목록과 stdout
  - GB-1 결과 4개의 `pass`
  - stage1 도구 sha, 추출기 sha 대조(repo = v3c2 eo = `5fa27047…`)
  - hybrid s31b(fit 시드 31)의 `signal_readback.csv`·`vsl_readback.csv` 집계와 runlog 요약 줄, v3c1 R-obs·hybrid s31b의 `decision_budget.json` 3개, v3c1 R-obs runlog 끝부분
  - W에서 `python -B`로 κ·b(110)·단일 호출 Trace 연산 수 계산. 파일을 만들지 않았고, 실행 뒤 W status 0줄을 확인했습니다.
- **[읽음]**: 계획·검토·목록·K1K6 보고 3종·V3C3_BUILD·v3c2 NC 비교 보고, P10 보고(P10_VERIFY, L0L1, T5 앞부분, PAIR_REPORT), N1F 0단계 지표 문서, 러너 VBS·발사기·launch_plan·freeway_fd·vsl_command_distribution·writer 해당 줄, 배포 튜닝 키, memory 파일 8개
- **하지 않은 것**: 코드·핀·망·git 쓰기, VISSIM·cscript 실행, 금지 시험, s37 열람(상위 폴더 목록에 `s37_v3c3nc` 이름만 보였고, 그 안은 열지 않음)
- 이 선언의 J1 시드 선택과 U9-a 공허 규칙, GB-13 승격 조건, O-5의 차이식(n × d1, κ)은 이 단계에서 새로 정한 것입니다. 계획·검토의 해당 문구보다 구체적이고, 약하게 바꾼 조건은 없습니다.
