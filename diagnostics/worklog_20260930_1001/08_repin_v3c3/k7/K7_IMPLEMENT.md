# K7 구현 보고 (v3c3 재핀 + 단일값 VSL·L2 배포 경로 활성화)

- 작업 트리 W = `D:/VISSIM-merge/sim3-n31-v3c3`, 브랜치 `claude/repin-v3c3-20261001`
  - K6 `54d821c` → **K7 head `99dc641809fb939515c6d6f1e2f655c21deef289`**. 로컬 커밋 5개, **푸시하지 않았습니다**.
  - 작성자·커미터 Ming2you <alsrjsrb1915@snu.ac.kr>, 메시지 끝 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, 경로 명시 커밋, `--renormalize` 없음.
  - `git status --porcelain --ignored` 0줄. 바뀐 파일 전부 작업본 바이트 = `git cat-file --filters HEAD:<f>` [실행].
- 사전 선언 `K7_GB_J1_PREDECLARATION.md`(sha256 `fad31d70…`, 15:27 고정)는 K7 편집 전에 있었습니다. 이 단계는 구현만 했고, 선언의 관문 O-1…O-8은 다음 단계(GWT7)에서 판정합니다.
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단. 줄 번호는 K7 기준입니다. `N31D` = `diagnostics/sdmpc_n31_20260924`.
- 근거 스크립트·로그 사본: `reports/k7/impl/`(scripts, logs, o4, family_l1_overlay). 원본은 세션 스크래치 `v3c3-k7/`.

## 0. 결론 — stop = false

1. 목록 52항목, 검토 N7·N8·N11, K5에서 미룬 V-6·V-11을 모두 넣었습니다. 막는 항목은 없습니다.
2. 배포 경로에서 켠 것 [실행]
   - 러너 `scenario/lane_native_b110.vbs` `RW_ALLOWED_VSL_SPEEDS = "81,91,101,110"`(나머지 줄 바이트 같음, `37c5021f…`)
   - 튜닝 `config_n31_v2.json`(`319d07aa…`) `actuation.vsl_command_distribution` = `{'model':'single_value','distribution_by_command':{'80':81,'90':91,'100':101,'110':110}}`
   - reference(`add58bc4…`) `freeway.vsl_fd_response.FW_E` = L2 정확값(선언 §0의 L2와 JSON·키 순서까지 같음)
   - `check_family_files`(배포 튜닝 × reference × 러너) = `{'family':'single_value','commands':[80,90,100,110],'written':[81,91,101,110],'speed_scale_roads':['FW_E']}` — 선언 O-4(a)의 값과 같음
3. **다음 단계가 꼭 볼 것(선언과 부딪힐 수 있는 곳)**
   - **(가) 무신호 회전 22개 [실행].** v3c3 fit FZP로 다시 뽑은 검증표에서 `SC103_S_SC6_to_E`(커넥터 10096)의 정지 비율이 0.0472 → 0.0544로 규칙 문턱 0.05를 넘어, `unsignalized_turns`에서 빠졌습니다(23 → 22). 규칙·생성기는 그대로입니다. 선언 O-3 DA-2는 "sha만 바뀜(unsignalized_turns의 검증 수치는 예외)"인데, 이번에는 검증 수치 때문에 **판정(목록)도** 바뀌었습니다. 이 표는 U3 후보 튜닝(`config_n31_v2_urban_b1*.json`)만 읽고 배포 튜닝·R-obs3·J1은 읽지 않습니다 [읽음 `make_config_n31.apply_urban_batch1`]. 판정은 다음 단계 몫이라 손으로 고치지 않았습니다.
   - **(나) T9 중앙차분 간격 0.25 → 0.0625 [실행].** L2에서 h 0.25의 AD 대 중앙차분이 100(ttt)에서 상대 2.5e-4로 1e-4를 넘었습니다. h를 0.5 → 0.0078로 줄이면 오차가 정확히 4배씩 줄고(4.77e-6, 1.19e-6, 2.98e-7, 7.45e-8, …) 좌·우 한쪽 차분이 양쪽에서 AD로 모입니다. 꺾임이 아니라 O(h²) 절단 오차입니다(`evidence/t9_probe.json`). **허용 오차 1e-4는 그대로**이고, 계획 R9("원인 조사: 곡률, h")의 경로입니다. 시험이 `h == 0.0625`를 단언합니다.
   - **(다) s53 = v3c2 런(대체) [실행].** 과제 지시대로 v3c2 s53 출력을 썼습니다(RA-1·RA-4·RA-5). v3c3 s53 런은 run.json을 완료하지 못했고, 메인 세션이 16:19에 재발사했습니다(`reports/gb1_amendment_1.md`). 참고로 재발사 전 v3c3 s53 FZP(1,173,499,393 B)의 payload sha는 v3c2 s53과 같았습니다(`72385aa5…`, 6,850,613행; GB-1 판정 아님, 읽은 뒤 폴더가 `run_interrupted_20261001_1339`로 옮겨짐). 재발사 런이 끝나면 선언 O-0대로 GB-1 s53과 재추출 바이트 동일을 확인해야 합니다.
   - **(라) 경로 분류 하나.** `diagnostics/test_vsl_command_distribution.py`(K5 시험, V-9)의 "이 트리" 단언을 distribution → single_value로 바꿨습니다. 목록 V-9·V-6/V-11의 시험으로 분류했습니다.

## 1. 커밋

| 커밋 | 시각 | 내용 |
|---|---|---|
| `8892c91` | 15:41 | RA-1: v3c3 fit 추출(s53 = v3c2), 영수증 5개 |
| `6472308` | 15:46 | C-4/V-6/N-4/N-5/DA-3/DA-4: 재핀 도구 열거표·가족·configure-check 단계, build 출력(망 사본, 선언 20, transfer, receipt, base, 러너 VBS), 시험 |
| `69f44ef` | 15:54 | DA-1/DA-2/RA-5/C-8/C-9/C-10: 손 기록 4, 도시 유도 7, β 키 `routing_v3c3{,_2}`, `make_config_n31` β/묶음1 핀, 시험 |
| `4edc023` | 16:15 | RA-3/C-3, DA-5/C-7, V-3/C-11, C-2, RA-4/C-6, C-1/V-5, V-11: plant 연쇄, config ×3, 가족 옵션, 시험(L2·T9·가족) |
| `99dc641` | 16:35 | V-12/N11/N12/N13/N16/R3 문서, QUALIFICATION P2·P7 문구(plant 재생성), K5 시험 갱신, `N31D/REPIN_V3C3_REPORT.md` |

- `git diff --name-status 54d821c 99dc641`: 98개(A 18, M 67, R 13), 목록 `impl/logs/k7_diff_name_status.txt`. 분류는 아래 §2 표와 `REPIN_V3C3_REPORT.md`에 있습니다. 바꾸지 않은 것(선언 O-3 "바꾸지 않는 것"): 러너 VBS `8c753c08`, `sdmpc.py`, 발사기·동결기·`prepare_sdmpc31_network.py`, `obs150_contract.py`(N7은 K5 `validate_tuning_v2`와 이번 `runner_config_check`로 충족) [실행 diff].

## 2. 목록 항목별 처리

| 항목 | 처리 | 근거 |
|---|---|---|
| N-1…N-3 | 망·prepare는 앞 단계(V3C3_BUILD) | — |
| N-4/N-5 | `network/baseline_s31_v3c3nc.inpx` `3de889f0…`, v3c1 사본 삭제, sig_manifest 이름·bytes·copied_from만 | `repin build/verify` |
| N-6 | RM 팔 준비(§5) | `rm_build/` |
| C-1 | 망·β·묶음1 핀, RAMP_FORECAST, `VSL_COMMAND_DISTRIBUTION`, 가족 옵션, 문서 | `make_config_n31 --check` ×3 |
| C-2 | v3c3 핀, `QUALIFICATION_BY_FAMILY`(L2 이월·계열 기각 6.41·80 비관·FW_W·s53 대체·K3 min_green·K6 state_response) | `make_plant_n31 --check` |
| C-3 / RA-3 | RUN·GEOMETRY·NETWORK·FZP(`f8476f83`) → 포트 프로필 | `extract_port_profile --check` |
| C-4 | 상수 v3c3, 열거표 3개 + `element_block_audit`, N8 좁힘, `VSL_FAMILIES`, `runner-family`, configure-check 열거·가족 단계 | 시험 6개 신규 |
| C-5 | 시험 상수(prepare, fixtures, urban_batch1 :59 포함, generators, ad_smoke, launch_world, test_tools_launch 편집만, obs150 docstring) | — |
| C-6 / RA-4 | `FOLDERS`(s53 = v3c2 폴더), INPUTS 5개 | `derive_ramp_forecast --check` |
| C-7 / DA-5 | 망 상수, `--out-root` 덮어쓰기 옵션(V-11) | CSV `108debbb` 그대로 |
| C-8 / C-9 | DEFAULTS·`--generated 2026-10-01`·FZPS | 각 `--check` |
| C-10 | 어댑터·`beta_source`·주석(N11 `physical_movement_routes.py:456`, `:571`), v3c1 키 제거 | `test_the_v3c1_sources_left_this_tree` |
| C-11 / V-3 / V-4 | NETWORK·GEOMETRY v3c3, `VSL_FD_RESPONSE_BY_FAMILY`, note | `make_reference_config --check` |
| V-1 / V-2 / V-5 / V-9 | K4/K5에서 이미 | — |
| V-6 | 러너 81,91,101,110 | `runner_config_check` |
| V-7 / V-8 | 바꾸지 않음 | diff 0 |
| V-10 | L2 리터럴(`test_reference_law_is_l2`), T9 h(§0 나), vsl_model, generators, repin | 시험 |
| V-11 | 생성기 `--vsl-family distribution --out-root`(5단계) | `VslFamilyTests`, §7 |
| V-12 | CONTRACT v3c3 항목, GUIDE 머리 노트·VSL 줄 | 읽기 |
| R-*, H-*, P-*, E-1 | K1–K6 | GA |
| RA-1 / RA-2 | §3 | 영수증 |
| RA-5 | 검증표 `d8718b9d`(생성 + `--check` 같은 sha) | §0 (가) |
| RA-6 | R-obs 뒤(선택) | — |
| DA-1…DA-4 | §3 | cmp 로그 |
| DA-6 | §4 | — |
| DA-7 | `N31D/REPIN_V3C3_REPORT.md` | — |

## 3. 다시 만든 파생 증거 (입력 sha)

- **RA-1** `metanet_calibration_v1/v3c3_nc_20261001/` [실행]
  - 입력 런: v3c3 `s31/41/43/47_v3c3nc/run`(망 `3de889f0`/`726af589`/`51478c39`/`1895ca30`, FZP `f8476f83`/`f63f0080`/`048823b9`/`9caa12c8`), v3c2 `s53_v3c2nc/run`(`c2dd1a48`, FZP `61e496a2`). 추출기 `5fa27047`, 인자는 v3c1 영수증과 같음(phase 0.1, geometry profile, refined `9769b3a4`), 하나씩 BELOW_NORMAL(자식 0x4000 확인).
  - 결과: 5시드 checks 18538, 마지막 프레임 8995.1. boundaries/flows/cells = v3c2 eo 같은 시드 바이트 같음, 합계 7항목도 같음(`impl/logs/ra1_check.json`). s43·s53에 미설명 본선 손실 1대씩(영수증 note).
  - s31 기하 `2e3d8bfe…` = v3c1·v3c2 eo 기하와 출처 키 6개만 다름.
- **DA-1 / DA-2** (v3c1 표 대비 핀 사상 뒤 포인터 차이, `impl/logs/cmp_urban_beta.txt`)
  - phase authority `9ba47f3b`(generated 1), routing_v3c3_2 `4290d180`(1), route queue `181a452a`(1), area provenance `f912429d`(1), routing_v3c3 `506ec5c1`(1), area 계약 `fdc21f06`(바이트 같음)
  - 손 기록: explicit `a3957146`, entry `514ae8e0`, nonexistent `04fce57c`, offramp prior `c2ef5b0f`(망 핀 + repin 기록만)
  - unsignalized validation `d8718b9d`(FZP 5개: v3c3 31/41/43/47 + v3c2 53), turns `83326aca`(§0 가)
- **DA-3 / DA-4** `repin build`: `REPIN_OK files=70 written=26`; v3c1 출력 대비 차이 `impl/logs/dry_diff_v3c1_v3c3.txt`(membership 0, 선언 7개 vehicleInputs 문구 1, transfer 12, receipt 27, base 1). transfer에 `added_composition_block`·`added_distribution_blocks`·구성/vehComp 12행/분포 기록.
- **RA-3** 포트 프로필 `de0b575f`: v3c1 대비 |Δ| ≤ 3.30 km/h(표는 `REPIN_V3C3_REPORT.md` §1).
- **RA-4** drain 17.4/43.0/31.1/88.4/38.6/154.3/33.1/44.6 s, cap 220/2353/413/545/551/1262/850/600 veh/h(입력 boundaries 5개 sha는 `derive_ramp_forecast_n31.INPUTS`).
- **DA-5** 사이드카 `12e67cee`(망·기하·러너·헤드 계약 핀과 sha256_lf만).

## 4. 배포 SDMPC 튜닝 (R-obs3 · J1)

- 두 런 모두 **같은 파일** `N31D/config_n31_v2.json`(`319d07aac77472d4318ddf6266003916cb7afab98da35a06254952e393542bb8`)을 씁니다. 컨트롤러만 다릅니다(선언 GB-4 `-Controller no-control`, J1 `-Controller wu-link`).
  - R-obs3(no-control + obs150): 무제어 결정은 VSL 66행 모두 110을 씁니다 → CSV `110.0`(사상 110→110). obs150 관측은 튜닝이 켭니다.
  - J1(VSL 단일값 + L2): SDMPC 축은 명령 80…110, CSV는 81/91/101/110, plant는 L2.
- 키 [실행]: `vsl_set` [80,90,100,110], `max_vsl_step` 40, `adapter.joint_owner_game.ignore_wall_time_limits` true, 사상(위), `execution.signal_vbs_config` = `N31D/scenario/lane_native_b110.vbs`, `freeway.lane_plant` = `N31D/plant_n31_v2.json`(`b119d6d9…`), `urban.beta.source` `routing_v3c3`.
- 후보 튜닝: `config_n31_v2_urban_b1.json`(`7c43f881`), `_u1u3.json`(`371c6b75`). 같은 사상·L2입니다.
- 발사 줄과 사전점검은 선언 §2 GB-4, §3.2 그대로입니다. 동결·푸시는 하지 않았습니다.

## 5. RM 팔 준비 (`D:/VISSIM_runs/20261001_v3c3/rm_build/`) [실행]

- `build_v3c3rm.py`(`54ea94e7…`) = v3c1rm 레시피, 망 단계만 v3c3. 스크래치 리허설 두 번째에서 통과한 뒤 실제 `all`을 돌렸습니다.
  - 사슬이 v2rm을 바이트 재현, 도구 stdout·인자 = v3c1rm 빌드(경로 교체).
  - 망 세 구성법이 시드마다 바이트 같음: (b) v3c3nc + v2rm RM 절, (a) v2rm 사슬 + v3c3nc 경로 절 + 영수증 편집, (c) v3c1rm + 영수증 편집. v3c1rm 대비 +1058 B, +25줄.
  - 규칙·프로필 7개 파일은 v3c1rm과 바이트 같음. `fixed_profile.json`은 망 sha만, 증명은 망 sha와 분포 81/91/101 추가만 다름. prepared 핀 53개 유효.
  - 망 sha: s31 `04630354`, s41 `e4953eaf`, s37(봉인) `a9baf671`. 드라이런 3개 exit 0, v3c1rm 드라이런과 `arguments`의 경로만 다름.
  - `rule_runtime.txt`: python 경로와 helper 존재, 셋째 줄 900(GB-13 t_rw).
- 영수증 `v3c3rm_build_receipt.json`(`20060a55`), `v3c3rm_dryrun_receipt.json`(`d4fbefa7`), 검사 `reports/v3c3rm_checks.json`(`04d33d6b`, 10/10 OK), 발사 줄 `../launch_lines_rm.txt`(`aa6ed434`, s37은 봉인 블록). **발사하지 않았습니다.**

## 6. 점검과 시험 (W, BELOW_NORMAL, `python -B`) [실행]

- N17 기준선(K6, 편집 전): `--check` 연쇄 17개 전부 exit 0(`impl/logs/checks_base_k6.log`).
- K7 HEAD: `--check` 연쇄 17개 exit 0, `derive_unsignalized_validation --check` 같은 sha, `repin verify` → `REPIN_VERIFY_OK files=70 pins=122 net=identical`, configure-check → `REPIN_CONFIGURE_OK enumeration=compositions:14;vehcomp_rows:12;distributions:81,91,101,110 family=single_value:written=81,91,101,110 t=1:keys=312,enabled=38 t=150:keys=328,enabled=38 t=900:keys=376,enabled=38`(`impl/logs/checks_k7*.log`).
- 시험 9묶음(GA-5 목록, 경로만 W; 금지 7종 제외) — 실패 id 집합이 K6 기준과 같습니다(`impl/logs/final/`)

| 묶음 | 결과 | K6 대비 |
|---|---|---|
| n31 | 198 OK (skip 3) | 같음(실패 0) |
| t9 | 9 OK | 같음 |
| tools | 60 OK | 같음 |
| obs | 143 OK | 같음 |
| pyt | 73 passed | 같음 |
| extra | 7 failed / 4 errors / 13 passed | 실패 11개 id = K6 `extra.outcome` |
| diag | 28 failed / 37 errors / 228 passed | 실패 65개 id = K6 |
| dprof | 16 passed, 2 skipped | 같음 |
| new | 41 passed (+ K6 새 시험) | 같음 |

- 새·바뀐 시험 이름 표(선언 O-1-1의 개명표): `test_reference_law_is_n1_l1` → `test_reference_law_is_l2`; `test_runner_config_allows_exactly_80_to_110_each_with_a_v2_distribution` → `test_runner_config_allows_exactly_the_single_value_family_each_with_a_v3c3_distribution`; `test_the_v3b_sources_left_this_tree` → `test_the_v3c1_sources_left_this_tree`; `test_routing_v3c1_*` → `test_routing_v3c3_*`(2개). 새 시험: repin 6개(`test_runner_family_bytes_write_each_family_list`, `test_v3c3_enumerations_*` 3개, `test_v3c2_v3c3_tables_are_the_edit_receipts`, `test_v3c2_v3c3_changes_are_recorded`), β 1개(`test_the_v3c3_tables_carry_the_v3c1_values`), 생성기 3개(`VslFamilyTests`).
- 시험이 W에 만든 무시 파일(`evaluation/controllers/__pycache__`, `__tangentcache__`, 61개)은 지우지 않고 스크래치 `v3c3-k7/moved_ignored/`로 옮겼습니다. 이후 W status --ignored 0줄.

## 7. 선언 관문을 미리 돌려 본 것 (개발 확인, 관문 판정 아님) [실행]

- O-4(a): 위 §0-2 값과 같음.
- O-4(b): 시험이 v3c3 사본에서 81/91/101/110이 모두 분포로 있음을 보고, v3c3 바이트에서 블록을 빼 만든 v3c2(sha `597191ac` 확인)는 `lacks desSpeedDistribution [81, 91, 101]`로 거부됨을 봅니다.
- O-4(c): 생성기 가족 옵션으로 만든 L1 가족(두 번 만들어 바이트 같음, `impl/family_l1_overlay/`): reference FW_E = L1, 사상 없음, 러너 `f0ed036e`(= K6 러너, 80,90,100,110), plant·사이드카가 그 핀. `configure-check --sec 1 --overlay-root <F>` → `REPIN_CONFIGURE_OK … family=distribution:written=80,90,100,110 t=1:keys=312,enabled=38`.
- O-4(d): (1) K7 + 사상 키 삭제 → `REPIN_ERROR VSL family: Runner … [81,91,101,110] is not the written image [80,90,100,110]`; (2) L1 가족 + 단일값 사상 → `REPIN_ERROR VSL family: … [80,90,100,110] is not … [81,91,101,110]`; (3) K7 + K6 러너 → `REPIN_ERROR plant runner_config differs from its pin`(핀 검사가 먼저). 모두 VISSIM 없이 configure 전 단계에서 끝남(`impl/o4/o4_console.txt`).
- O-3 경로·내용: §2·§3. 다음 단계가 볼 점은 §0-3 (가)·(라).
- **configure-check의 가족 단계에 대해 [읽음·추론]**: configure-check는 lane plant 없이 `configure_runtime`을 돌리므로 `runtime_setup.py:246-251`(plant v2일 때만) 줄 자체는 지나지 않습니다. 그래서 같은 함수(`vsl_command_distribution.check_family_files`)를 배포 튜닝의 manifest 핀으로 따로 부르게 했습니다. 런타임 줄을 배포 경로에서 처음 지나는 곳은 R-obs3 t = 1입니다(선언 GB-5).

## 8. 주의와 남은 일

- §0-3 (가)…(라)는 선언 관문에서 판정해야 합니다. (가)가 O-3 DA-2 "구속"에 걸리면 선언 O-9대로 멈추고 사용자 결정이 필요합니다(J1·R-obs3에는 영향 없음 [읽음]).
- s53: 재발사 런(16:19) 완료 뒤 GB-1 s53 판정, 그리고 v3c3 s53 재추출의 boundaries/flows/cells가 대체 입력(`s53_v3c2nc_observations`, 영수증의 sha)과 바이트 같은지 봐야 합니다. 추출기는 출력 폴더를 저장소 안으로만 받으므로(`extract_observations.py:595`) W가 아닌 관문 트리에서 하거나 비교 뒤 지워야 합니다.
- configure-check 키 수가 v3c1 보고(311/327/375)보다 1개 많습니다(312/328/376). control·v2가 같은 코드라 비교는 그대로 성립하고, 차이는 K1–K6 코드의 configure 메타 1개로 봅니다 [추론].
- 다른 작업 트리는 건드리지 않았습니다. 이 보고를 쓸 때 `sim3-n31-urban-b2` status 40줄, `sim3-n31-termcost` 1줄은 이전부터의 상태로 봅니다(이 세션에서 쓰지 않음) [실행·추론]. `D:/VISSIM-merge/frozen/*`는 쓰지 않았습니다.
- 하지 않은 것: 푸시, 동결, GWT7 생성, VISSIM 시작·종료(16:19 이후 돌던 s53·s37은 메인 세션 재발사), 금지 시험 7종 실행(`test_tools_launch.py`는 편집만), s37 출력 열람(RM s37은 prepared만 만듦).

## 9. 파일

| 구분 | 경로 |
|---|---|
| 이 보고 | `D:/VISSIM_runs/20261001_v3c3/reports/k7/K7_IMPLEMENT.md` |
| 저장소 보고 | `D:/VISSIM-merge/sim3-n31-v3c3/diagnostics/sdmpc_n31_20260924/REPIN_V3C3_REPORT.md` |
| 근거 | `reports/k7/impl/{scripts,logs,o4,family_l1_overlay}`, `reports/k7/evidence/t9_probe.{py,json}` |
| RM | `D:/VISSIM_runs/20261001_v3c3/rm_build/`, `launch_lines_rm.txt`, `reports/v3c3rm_checks.json`, `s{31,41,37}_v3c3rm/` |
