# v3c3 재핀 실행 보고 (K7, REPIN_V3C2_PLAN §3.7)

- 작성 2026-10-01. 계획 `D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md`(`d4b70c02…`), 목록 `repin_v3c2_inventory.json`(`07028e24…`), 검토 `REPIN_V3C2_PLAN_REVIEW.md`(`bc08f3df…`). 관문 사전 선언 `D:/VISSIM_runs/20261001_v3c3/reports/k7/K7_GB_J1_PREDECLARATION.md`.
- 사용자 결정(10-01): U1–U12 권고값 승인. 9000 s 폐루프는 VSL을 켠 채(단일값 DSD + plant 법칙 L2) 돌립니다.
- 브랜치 `claude/repin-v3c3-20261001`, K6 `54d821c` 위의 K7 커밋들(아래 §5). `N31D` = `diagnostics/sdmpc_n31_20260924`.
- 표기: **[실행]** 돌려서 얻은 값 · **[읽음]** 파일에서 확인 · **[추론]** 시험하지 않은 판단. 근거 스크립트와 로그는 실행 보고 `D:/VISSIM_runs/20261001_v3c3/reports/k7/K7_IMPLEMENT.md`에 적었습니다.

## 0. 결론

1. 목록 52항목과 검토 N7·N8·N11, K5에서 미룬 V-6·V-11을 모두 넣었습니다. 생성기 `--check` 연쇄, `repin verify`, `configure-check` t=1/150/900, preflight ×3이 통과합니다 [실행].
2. 배포 튜닝 `config_n31_v2.json`은 단일값 가족입니다: `actuation.vsl_command_distribution` {80→81, 90→91, 100→101, 110→110}, reference 법칙 L2(정확값), 러너 81,91,101,110. `check_family_files` = `{'family': 'single_value', 'commands': [80,90,100,110], 'written': [81,91,101,110], 'speed_scale_roads': ['FW_E']}` [실행].
3. 계획과 다르게 나온 것 셋(§4): (a) s53은 v3c2 런을 대체로 썼습니다(v3c3 s53 런 미완료). (b) 무신호 회전에서 `SC103_S_SC6_to_E`가 규칙 문턱을 넘었습니다. 사용자 결정(K7 수정 선언 1)으로 소속은 v3c1 23개로 고정하고 이 회전을 알려진 초과로 적었습니다(U3 후보 튜닝에만 영향). (c) T9의 80/90/100 중앙차분 간격을 0.25 → 0.0625로 줄였습니다(허용 오차 1e-4 그대로).

## 1. 무엇을 했나

### RA-1 추출 [실행]
- `extract_observations.py`(`5fa27047`)를 v3c3 NC s31/41/43/47과 v3c2 NC s53에 v3c1과 같은 인자로 하나씩 BELOW_NORMAL로 돌렸습니다. 산출 `metanet_calibration_v1/v3c3_nc_20261001/`(시드별 `boundaries_30s.csv`·`manifest.json`, s31 `geometry.json`, 영수증 5개).
- 다섯 시드 모두 checks 18538, 마지막 프레임 8995.1, 망 sha = 런의 망입니다. `boundaries/flows/cells_30s.csv`는 v3c2 `nc_analysis/eo` 같은 시드와 바이트가 같습니다(추출기 sha 같음, payload sha 같음).
- s31 기하 `2e3d8bfe…`는 v3c1(`8752f0cd`)·v3c2 eo 기하와 출처 키 6개(network, source_network, 입력 경로 4개)만 다릅니다.

### C-4 재핀 도구와 빌드 [실행]
- `repin_scenario_v2.py`: 망 상수 v3c3, 열거표 `V3C2_ADDED_COMPOSITION`(391 B `82c11cd5`), `V3C2_INPUT_COMPOSITION_EDITS`(12행), `V3C3_ADDED_DISTRIBUTIONS`(81/91/101), `element_block_audit`. `CHANGE_RULES`는 넓히지 않았습니다. 분포 추가 목록은 열거(110 + 81/91/101)와 정확히 같아야 합니다(N8). `VSL_FAMILIES`와 `runner-family`(V-11), `configure-check`의 열거·가족 단계와 `--workdir`/`--tuning`/`--overlay-root`.
- `build` → `REPIN_OK files=70`, `verify` → `REPIN_VERIFY_OK files=70 pins=122 net=identical`.
- v3c1 출력 대비(핀 사상 뒤) 내용 차이: transfer·repin 영수증의 구성/분포 기록과 러너 목록, 선언 7개 `prior_mismatch`의 vehicleInputs 문구, base config 설명. membership `213a5d`는 내용 0(1134/1135 lineage 5행 그대로).
- configure-check: `REPIN_CONFIGURE_OK enumeration=compositions:14;vehcomp_rows:12;distributions:81,91,101,110 family=single_value:written=81,91,101,110 t=1:keys=312,enabled=38 t=150:keys=328,enabled=38 t=900:keys=376,enabled=38`. v3c1 보고의 311/327/375보다 1개 많은 것은 K1–K6 코드 차이입니다 [추론: K3 configure 메타].

### 손 기록·도시 유도·β (DA-1, DA-2, RA-5, C-8/9/10) [실행]
- 손 기록 넷(explicit, entry, nonexistent, offramp prior)은 망 핀만 바꾼 `*_v3c3_20261001`이고, 각 파일이 v3c1 앞 파일을 기록합니다.
- v3c1 순서로 다시 유도했습니다. v3c1 표 대비(핀 사상 뒤): phase authority, `routing_v3c3_2`, route queue, area provenance, `routing_v3c3`은 `generated`만 다르고 β 값은 같습니다. area 계약은 바이트 같음(`fdc21f06`).
- unsignalized validation(FZP 5개, `--check` 두 번 같은 sha `d8718b9d`)은 수치가 바뀌었습니다. unsignalized turns는 규칙대로면 22개지만 소속을 v3c1 23개로 고정했습니다(§4 b).
- 어댑터 β 원천 `routing_v3c3`/`routing_v3c3_2`, `COMPLETE_BETA_SOURCES = {routing_v3c3_2}`. v3c1 키와 파일은 뺐습니다(U8-a).

### plant 연쇄 [실행]
- 포트 프로필(v3c3 s31, FZP `f8476f83`): v3c1 대비 |Δ| ≤ 3.30 km/h(10491 −3.30, 10481 −2.91, 10479 −2.49, 10480 +2.45, 10645 −2.06, 10638 +1.79, 10646 −1.59, 10643 +1.53, 나머지 ≤ 0.82), 표본 수 ±9 이내.
- obs150: CSV 바이트 그대로(`108debbb`, 294행), 사이드카는 핀만.
- reference: `vsl_fd_response.FW_E` = L2 정확값(아래 §2), vsl_set·transport·표지 셀 그대로.
- plant: v3c3 핀, `qualification` = 단일값 가족 문구(이월 사전값, 계열 기각, 80 비관, FW_W, s53 대체, K3 `min_green_sec ≤ 0` 거부, K6 `state_response` 거부 근거).
- 램프 예측(RA-4): drain 17.4/43.0/31.1/88.4/38.6/154.3/33.1/44.6 s, cap 220/2353/413/545/551/1262/850/600 veh/h(v3c1 16.0/43.6/30.2/88.5/40.8/159.6/33.4/44.4 s, 220/2347/408/545/551/1248/843/592).
- config ×3: v3c1 대비(핀 사상 뒤) 사상 키, 램프 예측 13값, β 원천 이름, 설명 문구만 다릅니다.

## 2. VSL 가족 (U3-a, U4, U5-a)

| | single_value (트리) | distribution (생성기 옵션) |
|---|---|---|
| 명령(튜닝·reference vsl_set, SDMPC, action JSON) | 80,90,100,110 | 80,90,100,110 |
| 튜닝 사상 | {80:81, 90:91, 100:101, 110:110} | 없음(항등) |
| 러너 `RW_ALLOWED_VSL_SPEEDS` | 81,91,101,110 | 80,90,100,110 |
| reference FW_E | L2 Carlson 1.33/0.87 + `speed_scale` cubic_lagrange {80: 0.7225223093088844, 90: 0.8119772280655296, 100: 0.9006844904146349}, maximum 110 | N1 L1 Carlson 0.94/1.44 |
| `check_family` | single_value, written 81..110, speed_scale FW_E | distribution, written 80..110, 없음 |

- 분포형 가족은 트리 밖 폴더에만 만듭니다(`CONTRACT.md` v3c3 항목의 명령 다섯 개). 두 번 만들면 바이트가 같고 가족 검사를 통과합니다(`VslFamilyTests`) [실행].

## 3. 이월 사전값 (재적합하지 않은 것, N11 / v3c1 MA-1)

| 이름 | 파일 | sha256 |
|---|---|---|
| b110 segment_params | `metanet_calibration_v1/res10_b110_20260923/train_s31_v2nc/free_speed_b110/segment_params.json` | `6b40550a748fabe086bfdb79ad0245c0d6b98c440c1d8c5227912f4474f62052` |
| boundary fit | `…/train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json` (freeze `8c85c095…`) | `8e4f60470f0c182594a152949d76bf7327ed3b65c09cb034de19c7ce435490f7` |
| boundary config | `…/train_s31_v2nc/boundary_literature_v1/boundary_config.json` | `54704bee9cca2015dc7aca76fd2c0ae7fa4b81c8e35cab2b3db2dae409a1fec5` |
| 10490 측정 곡선(R-5) | transport `transport_step1_exchange_off_v2/config.json` → reference `physical_ramp_head_service_veh_per_cycle.RM_C10490` {2: 1.0, 3: 1.0, 4: 1.44, …, 10: 4.2}; 설치 때 K3가 3을 뺌 | `a33902540cfaef22d35c330f9ec6f15d830ac0d9955ff118515d3091eb008454` |
| VSL 법칙 L2 | N1F 2단계 `fit_results.json` k4_stage2.D6.fits.L2 (v3b 기반 단일값 팔 s41/43/47/53) | `4091d6e140f1cf1b29ae51e7863eb1d41d0d8169756ae28987deda69b2516f6c` |
| 시나리오 팩 사전값 7개 | `prior_mismatch` 영수증(D-B) | `historical_prior_transfer.json` |

## 4. 계획과 다르게 나온 것

- **(a) s53 = v3c2 런.** v3c3 s53 NC 런은 시뮬레이션은 끝났지만 run.json `completed`를 쓰지 못했습니다(메인 세션 `gb1_amendment_1.md`, 16:19 재발사). 그래서 RA-1·RA-4·RA-5의 s53 입력은 v3c2 s53 런입니다(과제 지시 10-01, 선언 O-0 대체). 근거는 GB-1 s31/41/43/47 PASS와 N1F G0 8/8이고 s53 자체의 동일성 판정은 아닙니다. 참고로 재발사 전 v3c3 s53 FZP의 payload sha는 v3c2 s53과 같았습니다(`72385aa5…`, 행 6,850,613; GB-1 판정 아님) [실행]. v3c3 s53 런이 완료되면 GB-1 s53과 재추출 바이트 동일을 확인해야 합니다.
- **(b) 무신호 회전: 소속을 v3c1 23개로 고정.** 같은 규칙(정지 비율 ≤ 0.05, 전이 ≥ 100)에서 `SC103_S_SC6_to_E`(커넥터 10096)가 0.0472 → 0.0544로 문턱을 넘어, 첫 K7 유도는 22개였습니다. 오프라인 관문 O-3(DA-2)이 이 소속 변화를 구속 실패로 잡았습니다. 사용자 결정(10-01 17:3x)으로 소속은 v3c1 표(K6 `54d821c` blob `c2558392`, sha256 `95ea2732`)의 23개로 고정합니다(`D:/VISSIM_runs/20261001_v3c3/reports/k7/K7_AMENDMENT_1.md`). 생성기 `MEMBERSHIP_PIN`이 소속과 알려진 초과 집합을 고정하고, 다른 소속·초과는 거부합니다. 검증 수치는 v3c3 값이고, 이 회전은 표의 `membership_pin.known_validation_exceedances`에 v3c3 0.0544(n 5602)와 v3c1 0.0472(n 5611)로 적힙니다. 표 `43247697`, 후보 config `4e85cfd6`·`c60bde7c`. 문턱 근처 다른 회전: `SC1002_W_SC1001_to_S_SC105` 0.0421, `SC2005_S_SC101_to_E_SC102` 0.0401. 이 표는 U3 후보(`config_n31_v2_urban_b1*.json`)만 읽고 배포 튜닝 `config_n31_v2.json`은 읽지 않습니다 [읽음].
- **(c) T9 중앙차분 간격.** L2에서 80/90/100의 AD 대 h 0.25 중앙차분이 100(ttt)에서 상대 2.5e-4로 1e-4를 넘었습니다. h를 0.5→0.0078로 줄이면 오차가 4배씩 줄고(4.8e-6, 1.2e-6, 3.0e-7, 7.5e-8, …) 좌·우 한쪽 차분이 양쪽에서 AD로 모입니다. 꺾임이 아니라 O(h²) 절단 오차이고 AD가 극한값입니다 [실행 `reports/k7/evidence/t9_probe.json`]. 간격을 0.0625로 줄였고 허용 오차 1e-4는 그대로입니다(계획 R9 "원인 조사(곡률, h)").

## 5. grep 기록 (N17, W @ K7 작업본, `vendor` 제외) [실행]

| 패턴 | 결과 |
|---|---|
| `2577209b` (v3c1 s31) | 28개 파일. 모두 이력 문구(생성기 주석·docstring, plant qualification, 문서, worklog), v3c1 추출 폴더(기록으로 남김), `PREVIOUS_RUNTIME_NETWORK`, 재핀 영수증의 이전 망, 시험의 v3c1 재구성 상수입니다. 살아 있는 핀은 0개입니다 |
| `226baa37`/`b8e7cf1f`/`ec0cd81d`/`385f40da` (v3c1 fit 41–53) | v3c1 추출 폴더와 worklog뿐 |
| 코드의 `v3c1` (`*.py/*.ps1/*.vbs`) | 20개 파일. 이력 주석, 이전 망 상수, v3c1 키가 빠졌음을 보는 시험(`test_the_v3c1_sources_left_this_tree`), v3c1 표와 값 비교 시험 |
| 코드의 `0.94`·`1.44` | 분포형 가족 정의(`make_reference_config.VSL_FD_RESPONSE_BY_FAMILY['distribution']`, plant qualification), 그 가족 시험, K5/K6 단위 시험의 합성 법칙. 배포 reference는 L2 |
| `RW_ALLOWED_VSL_SPEEDS = ` | N31 경로는 `scenario/lane_native_b110.vbs` = 81,91,101,110 하나. 나머지는 다른 설정(ver2n21, lane_plant 팩, generated)과 시험 고정값 |

## 6. 남은 것 (이 보고 밖)

- 관문 O-1…O-8(GWT7), 푸시, 동결과 GB-4…GB-13, R-obs3·J1 발사는 사전 선언 순서대로 다음 단계입니다.
- RM v3c3 팔은 `D:/VISSIM_runs/20261001_v3c3/rm_build`에 준비했고 발사하지 않았습니다.
