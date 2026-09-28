# v3c1 재핀 계획 (SDMPC-31 핀·표·설정을 망 v3c1로 옮기는 일)

- 작성 2026-09-28. **계획만 세웠습니다.** 저장소 코드·핀·git은 하나도 바꾸지 않았습니다.
- 적용 조건: v3c1 NC 5시드 재판정(s47·s53 진행 중) 통과, 그리고 사용자 승인(Q12 재핀 코드 변경 + VSL L1 + 행동 집합 {80,90,100,110}).
- 기계 판독용 목록: `D:/VISSIM_runs/20260927_v3c1/reports/repin_inventory.json` (항목 48개, 각 파일의 현재 sha256, grep 결과, 단계 3a 결과 포함).
- 근거 스크립트·산출물: scratchpad `net-v3c/v3c1/repin_drift/` (§10).
- 표기: **[실행]** 이번에 직접 돌려 얻은 값 · **[읽음]** 코드·파일을 읽고 확인 · **[추론]** 시험하지 않은 판단.
- 줄 번호는 모두 `D:/VISSIM-merge/sim3-n31-urban` @ `cf3ce37`(깨끗한 작업 트리 [실행 `git status`]) 기준입니다. `N31D` = `diagnostics/sdmpc_n31_20260924`.

---

## 0. 한눈에 보기

1. **v3b 기존 drift (단계 3a).** (나)·(다) 생성기 14개를 v3b 망에 다시 돌렸습니다. **모두 핀된 바이트를 그대로 재현했습니다** [실행]. 도구 수준의 기존 drift는 없습니다.
   - 내용 수준의 기존 불일치는 두 건입니다 [실행 독립 대조].
     - `control_area_membership_213a5d.json` 1134/1135 relFlow 5행: 재핀 도구가 이미 "lineage 사본"으로 영수증에 적어 둔 것입니다(`scenario/repin_receipt.json` files[0].relflow_copies.lineage). 제안서 R3(v)의 열린 질문은 이것으로 답이 됩니다(§4.3).
     - **새로 찾음:** 묶음 1 U1의 `urban/control_area_route_contract_v3b_20260926.json`이 결정 1061(pos·relFlow), 1128:2(relFlow), 1124(pos)의 옛 망 사본을 들고 있습니다. 바탕 계약 파일에서 물려받은 것입니다.
   - 두 건 모두 v3c1에서 바이트까지 그대로입니다. 그래서 v3c1 diff와 섞이지 않습니다 [실행].
2. **재핀은 "sha 상수 5곳"보다 큽니다.** 제안서 Q12 목록에 없던 것이 여섯 가지 나왔습니다.
   - (a) 재핀 도구가 v3c1 망을 거부합니다: `characterize_changes` → `vehicleRoutingDecisionsStatic: elements added [1160, 1162, …, 1168]` [실행]. 결정 추가를 열거표로 허용하는 코드 변경이 필요합니다(C-4).
   - (b) **런타임 가드가 V1을 거부합니다.** `evaluation/controllers/physical_movement_routes.py:511-513`은 입력 1083의 원천 링크 21에 경로결정이 있으면 예외를 냅니다. v3c1은 거기에 1160을 둡니다 [실행·읽음]. 이 가드는 기본 튜닝에서 켜져 있습니다(`config_n31_v2.json:7860`). 그대로면 **R-obs가 t=1 configure에서 멈춥니다** [추론]. 런타임 코드와 선언을 함께 바꿔야 합니다(NA-7, C-11).
   - (c) 여섯째 망 sha 상수: `scripts/build_obs150_detectors.py:52`. 제안서 Q12에는 없고, `PLANT_PORTING_GUIDE.md:322`에는 있습니다.
   - (d) 기본 튜닝 β(`routing_v3b`)의 역추론이 새 결정 1165(V5b)를 **SC1005|W_SC1004에 잘못 붙입니다**(0.675/0.075 → 0.3229/0.4271) [실행 미리보기]. `explicit_approach`에 1165를 적어야 합니다(NA-3).
   - (e) `scripts/derive_unsignalized_validation.py:43-45`의 FZP 목록이 v3b s31/s41/**s37**입니다. fit 5시드로 바꿔야 합니다(C-8).
   - (f) β 원천 이름과 파일 경로가 어댑터에 박혀 있습니다(`vissim_stackelberg_adapter.py:3994-3999`, `beta_source.py:40`). 파일 이름을 바꾸면 코드 변경입니다. 결정이 필요합니다(C-10).
3. **v3c1 미리보기 (스크래치, 재핀 아님).** v3b 손 기록의 망 sha만 v3c1로 바꿔 도시 생성기를 돌렸습니다 [실행].
   - U1 β(`routing_v3b2`): 26개 movement가 바뀝니다. V1, V3–V7이 **영수증 기대값 `expected_plant_beta.beta_v3c`와 모두 정확히 같습니다.** V2는 그대로입니다.
   - `route_queue_attribution`: 새 경로 23개와 그 anchor만 더해집니다.
   - phase authority, area route contract, unsignalized turns, obs150 CSV: 내용이 같고 핀만 바뀝니다.
4. **VSL L1 + 행동 집합은 코드 변경 없이 상수 3곳, 시험, 매니페스트로 끝납니다** [읽음].
   - T9는 이미 "110에서 0이 아니다"를 단언합니다(`tests/test_n31_ad_smoke.py:57-70`). 문서의 "==0" 서술(`PLANT_PORTING_GUIDE.md:452`, `:485`, `:527`)이 낡은 것입니다.
   - 갱신할 것은 두 가지입니다. L1 값을 확인하는 단언과 중앙차분 기준점(80 → 80·90·100)입니다.
5. **의존.** R-obs는 재핀 전체(VSL 포함)가 필요합니다. RM 3팔과 NC는 SDMPC 재핀과 무관합니다(§7).

---

## 1. 범위와 전제

- 망: v3c1 = v3b + 결정 1160, 1162–1168. V2(1161)는 보류입니다 [읽음 `README.md`, `v3c1_edit_receipt.json`].

| 시드 | v3b sha | v3c1 sha |
|---|---|---|
| 31 | be0075bf | 2577209b |
| 41 | 261a1fb0 | 226baa37 |
| 43 | 64ff0766 | b8e7cf1f |
| 47 | 4a0230fe | ec0cd81d |
| 53 | 2e5332c1 | 385f40da |
| 37 (봉인) | f5c3d640 | 3eb06c63 |

- 런타임 망은 s31 사본 하나입니다.
  - 원본: `D:/VISSIM_runs/20260927_v3c1/s31_v3c1nc/prepared/network/baseline_s31_v3c1nc.inpx`
  - 이 파일은 `source/` 파일과 sha가 같습니다(2577209b) [실행].
- FZP에서 뽑는 것은 fit 시드 31/41/43/47/53만 씁니다. **s37은 쓰지 않습니다.**
- 새 worktree의 출발점은 `cf3ce37`입니다(urban 묶음 1 = 886a014 + U1–U3).
  - `sim3-n31`(886a014)에는 묶음 1 파일 10개가 없습니다 [실행 grep 비교].

---

## 2. 저장소 grep 결과 [실행]

- 방법: `rg --no-ignore --hidden`(.git 제외), 두 작업 트리 전체, BELOW_NORMAL로 돌렸습니다.
- 찾은 패턴: v3b fit 5시드 sha 앞 8자(be0075bf 261a1fb0 64ff0766 4a0230fe 2e5332c1)와 참고용 s37 v3b `f5c3d640`.

| 저장소 | 5시드 sha가 든 파일 | 분류 |
|---|---|---|
| sim3-n31-urban (cf3ce37) | 56 | N31D 핀 산출물 39 · 생성기 코드 상수/문서 6 · 시험 3 · 문서 2 · v3b NC 관측 기록 5 · 런타임 주석 1 |
| sim3-n31 (886a014) | 58 | urban에 없는 것: v3b NC 관측 기록 12개(RM 보정용 `v3b_nc_extra_20260926` s43/s47/s53 등). urban에만 있는 것: 묶음 1 파일 10개 |

- N31D 안의 sha 파일은 **47개**, `.inpx`를 언급하는 파일은 **58개**입니다. 제안서 §6.2의 수와 같습니다.
  - sha는 없고 `.inpx`만 언급하는 파일 13개도 봤습니다. `make_reference_config.py:53`(NETWORK 경로), `movement_beta_routing_v3b`(source 경로), 시험·도구 파일들입니다.
- s37 v3b sha는 `make_config_n31.py:147`, `derive_ramp_forecast_n31.py:15`, 그리고 v3b s37 관측 기록(manifest·receipt)에 있습니다. 제안서 R3(ii)와 같습니다.
- 목록 전체와 분류: `repin_inventory.json` → `grep`.

---

## 3. 다시 만들 목록 (§6.2 (가)–(바) + 검토 R3, 이번 확인으로 보강)

"예상 변화" 열의 뜻은 다음과 같습니다.
- **내용**: 표나 선언의 값이 바뀝니다.
- **sha만**: 망 핀 같은 출처 필드만 바뀝니다.
- **재분류**: 제안서가 (나)로 둔 것을 미리보기 결과로 (다)로 옮긴 것입니다.

### (가) 망

| id | 대상 | 생성기 | 예상 변화 |
|---|---|---|---|
| GA-1 | `N31D/network/baseline_s31_v3bnc.inpx` → `baseline_s31_v3c1nc.inpx` | `python -B N31D/repin_scenario_v2.py build` (C-4 뒤) | 내용(새 망). v3b 사본은 트리에서 뺍니다. v3b 재생은 동결 트리에서만 합니다(memory `vissim-supersede-dont-flag`) |
| GA-2 | `N31D/network/sig_manifest.json` | 같은 build | sha만. .sig 42개는 바이트가 같습니다 [읽음 영수증 assets] |
| GA-3 | v3c1 .inpx 6시드 + `v3c1_edit_receipt.json` | 완료 | 다시 만들지 않습니다 |

### (나) .inpx에서 유도되어 내용이 바뀌는 것

| id | 대상 | 생성기(명령) | 입력 | 예상 변화 / 근거 |
|---|---|---|---|---|
| NA-1 | `beta/movement_beta_routing_v3b2_20260925.json` (U1) | `python -B scripts/derive_routing_beta_physical.py --out <새 파일>` | 망 v3c1, NA-4, DA-4, DA-1, 시나리오 base config | **내용.** 26개 movement가 바뀌고, 모두 영수증 기대값과 같습니다. SC104\|S_SC106과 SC108\|W의 사유가 `no_route_evidence_config_default` → `relflow` [실행 미리보기] |
| NA-2 | `beta/movement_beta_routing_v3b_20260925.json` (기본 튜닝) | `python -B scripts/derive_routing_turn_beta.py --network <v3c1 사본> --movements-config N31D/beta/movements_core17legs4b_20260819.json --out <새 파일> --generated <날짜> --explicit-approach <NA-3>` | 망, NA-3 | **내용.** 19개 movement, 그중 3개(SC104_S_SC106_*)는 새로 생깁니다. **NA-3 없이 돌리면 1165가 SC1005\|W_SC1004에 붙습니다** [실행 미리보기] |
| NA-3 | `beta/explicit_approach_v3b_20260925.json` (손 기록) | 손 편집 + 검토 | — | **내용.** 망 핀을 고치고 `"1165": [["SC1","N_SC101"]]`을 더합니다. 1160, 1162–1164, 1166–1168의 부착도 검토합니다(미리보기에서는 올바른 접근로에 붙었음) |
| NA-4 | `beta/approach_entry_v3b2_20260925.json` (손 기록) | 손 편집 | — | **사실상 sha만** + SC108\|W의 `why` 문구. `start []` 그대로 두어도 유도가 1160 경로(정지선 21 통과)를 잡습니다. SC108_W_to_E_SC109 β는 1로 불변입니다 [실행 미리보기]. 제안서의 "V1-A면 바뀜"은 문구만 해당합니다 |
| NA-5 | `urban/route_queue_attribution_v3b_20260925.json` (U2) | `python -B scripts/derive_route_queue_attribution.py --out <새 파일>` | 망, NA-1, NA-4 | **내용.** 새 경로 23개(1160:1–1168:3)와 route_end_anchors만 더해집니다(46개 경로, 그 밖의 차이 0) [실행 미리보기] |
| NA-6 | `urban/control_area_route_contract_v3b_20260926.json` (+ `.provenance.json`) | `python -B scripts/derive_area_routes_v3b.py --out <새 파일>` | base 계약, DA-4, DA-1, membership | **재분류 → (다).** 계약 바이트가 그대로(fdc21f06)이고 provenance만 바뀝니다 [실행 미리보기]. 기존 drift는 §4.3 |
| NA-7 | `scenario/native_input_1083_signal_authority_ver2_022a16.json` | `repin_scenario_v2.py build` + **열거 수정 규칙**(손 편집은 build/verify가 덮거나 거부) | 망 | **내용 + 런타임 코드(C-11).** 검토한 결정 1160을 명시하고, `native_route_prior`의 "no source21 decision"(:109)을 고칩니다. 근거: v3b 링크 21 결정 없음, v3c1 [1160] [실행]. 가드 `physical_movement_routes.py:511-513` [읽음] |
| NA-8 | `scenario/native_internal_inputs_c92673.json` | repin build | — | **재분류 → (다).** 1092는 V2 보류로 그대로입니다. 1097은 원천 링크 256에 1162가 생기지만, 분기 근거가 `all_forward_connectors`이고 그 검증에는 결정 가드가 없습니다 [읽음 `native_internal_input.py:150-241`, 실행 v3c1 링크 256 결정 = [1162]] |
| NA-9 | `scenario/physical_projection_support_635_proposal_ec2393.json` | repin build (+ 선택 수정) | — | **재분류 → (다), 선택 보강.** 새 경로가 지나는 행은 둘뿐입니다(/evidence/10419 `1024:1`에 +1162:1, /evidence/10568 `13:1`에 +1164:1·1165:1) [실행 witness]. 검증은 "적힌 id가 경로를 지나는가"(부분집합)라서 거부되지 않습니다 [읽음 `projection_support.py:111-124`]. 원안이 적은 `1014:3`(V6) 행은 새 경로가 지나지 않습니다 [실행] |
| NA-10 | `scenario/physical_movement_routes_ver2_35eb21`, `dynamic_area_routes_ver2_dbaf86`, `topology_routes_v2_8ac6fd`, `known_wout_routes_ver2_proposal_a424b4` | repin build | — | **sha만.** 런타임이 집합 일치를 요구하는 witness 행(`physical_movement_routes.py:192-204`, `:275-287`) 가운데 새 경로가 닿는 행은 0입니다 [실행 witness] |
| NA-11 | 범위 F 전용(membership 1135·1137, `sc2001_corridor_nc13`, base config 1135·1137, `route_choice_corridor_sc1004`) | repin build | — | **sha만.** v3c1에는 범위 F가 없습니다 |

### (다) sha만 바뀔 것 (재유도 뒤 diff 0 확인)

| id | 대상 | 생성기 | 근거 |
|---|---|---|---|
| DA-1 | `urban/physical_phase_authority_v3b_20260926.json` | `python -B scripts/derive_phase_authority_v3b.py --out <새 파일>` | 미리보기: 내용 동일, 출처 6경로만 다름 [실행] |
| DA-2 | `scenario/physical_phase_authority_local_1df35c.json` | repin build | 이전 방식 그대로 |
| DA-3 | `urban/unsignalized_turns_v3b_20260925.json` (U3) | `python -B scripts/derive_unsignalized_turns.py --out <새 파일>` (RA-5 뒤) | 미리보기(v3b 검증표의 sha만 바꿈): 내용 동일 [실행] |
| DA-4 | `urban/movement_nonexistent_v3b_20260926.json` (사용자 결정 기록) | 손 편집(망 핀) | 결정 내용은 불변 |
| DA-5 | `urban/offramp_static_route_prior_v3b_20260925.json` | 손 편집(망 핀). 설치 때 `offramp_routing.derive_prior`가 다시 검사 | v3b에서 derive_prior 통과 [실행] |
| DA-6 | 나머지 시나리오 핀(`shared_approach`, `head_free_service_10565`, `head_service_resource_contract`, `route_choice_corridor_1099/1100/1128`, `native_input_1093_prehead`, `native_input_1096_route_ver2`, `physical_projection_support_ver2`, `historical_prior_transfer`, `repin_receipt`, `config_n31_v2.base.json`) | repin build → verify | v3b에서 `REPIN_VERIFY_OK files=70 pins=122 net=identical` [실행] |
| DA-7 | `obs150/obs150_detectors_v2.csv` + `.manifest.json` | `python -B scripts/build_obs150_detectors.py` (C-7 뒤) → `--check` | 미리보기: CSV 바이트 동일(108debbb, 294행), report는 network_sha256만 다름 [실행]. 사이드카는 망·기하·러너 핀 때문에 바뀝니다 |
| DA-8 | `CONTRACT.md:685-700`, `PLANT_PORTING_GUIDE.md:22-45, 76-80, 234, 322, 356, 451-452, 485-486, 526-527` | 문서 | sha, 망, VSL, 줄 번호 |

### (라) FZP에서 다시 뽑을 것 (fit 31/41/43/47/53만)

| id | 대상 | 명령 | 비고 |
|---|---|---|---|
| RA-1 | 새 폴더 `…/metanet_calibration_v1/v3c1_nc_<날짜>/observations/s{seed}_v3c1nc_observations` + 영수증 | `python -B diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/extract_observations.py --run D:/VISSIM_runs/20260927_v3c1/s{seed}_v3c1nc/run --out <폴더> --phase-sec 0.1 --geometry-profile diagnostics/demand_sweep/ramp_dsd_20260916_v2/controller_response_v1/geometry_profile.json --refined-geometry diagnostics/demand_sweep/ramp_dsd_20260916_v2/segment_resolution_20260921/geometry_200_branch_guard.json` | v3b 방식 그대로입니다(`v3b_nc_20260925/s31_v3bnc_extraction_receipt.json` command) [읽음]. v3b 때 약 60 s/시드. 한 번에 하나씩 돌립니다. `v3b_nc_20260925`는 v3b 기록으로 남깁니다 |
| RA-2 | s31 `geometry.json` | RA-1 | plant `SOURCES.geometry`, reference `GEOMETRY`, obs150, `n31_ad_smoke.py:45-46`가 가리킵니다 |
| RA-3 | `port_profile_v2/{port_profile.json, obs/port_travel_v2.json, obs/port_events_le900.csv}` | C-3 뒤 `python -B N31D/port_profile_v2/extract_port_profile.py` → `--check` | 900 s 이전 FZP도 경로가 바뀌어 다를 수 있습니다. diff로 확인합니다 [추론] |
| RA-4 | `make_config_n31.RAMP_FORECAST` (:164-171) | C-6 뒤 `python -B N31D/derive_ramp_forecast_n31.py` → 값 복사 → `--check` | **내용**(망 + 시드 집합 31/41/37 → fit 5) |
| RA-5 | `urban/unsignalized_validation_v3bnc_20260925.json` | C-8 뒤 `python -B scripts/derive_unsignalized_validation.py --out <새 파일>` | v3b는 31/41/37이었습니다. v3c1은 fit 5시드, FZP 5개(약 1.1–1.2 GB씩)를 스트리밍합니다 |
| RA-6 | U1 T1 재판정 | scratchpad `urban-b1/t1_v2.py` | R-obs 포착과 fit FZP가 필요합니다 |
| RA-7 | fit5 stats6·frames6·scan, RM 관측 추출 | stage-1 도구 | RM 5라운드용입니다. R-obs에는 필요 없습니다 |

### (마) 이월

- b110 segment_params(6b40550a), boundary fit(8e4f6047), boundary_config: v2 NC s31 사전값입니다. 라벨만 붙입니다(QUALIFICATION).
- N1 L1 적합도 v3b NC에서 얻은 값입니다(FW_E, 80–110). v3c1 편집은 도시 결정뿐이라 FW_E 셀 FD는 그대로입니다. 그래서 L1을 이월 사전값으로 적습니다 [추론].

### (바) 설정과 코드 (재핀은 코드 변경입니다)

| id | 파일:줄 | 바꿀 것 |
|---|---|---|
| C-1 | `N31D/make_config_n31.py:74-75`(NETWORK, NETWORK_SHA256), `:393-394`(검사), `:86-91`(BETA_*), `:104-132`(URBAN_B1_* 경로·sha), `:140`(VSL_SET), `:147-171`(RAMP_FORECAST), 문서 `:1-51, 161-163, 237-242` | 새 망, 새 파일 이름과 sha, fit5 예측, {80..110} |
| C-2 | `N31D/make_plant_n31.py:45-57`(V3B_NC, SOURCES), `:63`, `:64-76`(QUALIFICATION), `:108-109` | 새 망·기하 핀, L1과 행동 집합 문구 |
| C-3 | `N31D/port_profile_v2/extract_port_profile.py:60-65`(RUN, GEOMETRY, NETWORK_SHA256, FZP_SHA256), `:96` | v3c1 s31 NC 런 |
| C-4 | `N31D/repin_scenario_v2.py:89-94`(NET_DIR, NET_INPX, V2_SHA256, V2_PIN, PREVIOUS_RUNTIME_NETWORK = v3b be0075bf), `:144`(VSL_SPEEDS), `:312-379`(영수증·편집표), `:416-484`(characterize_changes), `:598`, 문서 `:1-45` | v3c1 영수증(sha 핀) + **추가 결정 열거표**(1160, 1162–1168, 삽입 블록 sha 2b77ab01…). `CHANGE_RULES`는 넓히지 않습니다. NA-7 수정 규칙, VSL_SPEEDS (80,90,100,110) |
| C-5 | `tests/test_prepare_sdmpc31_network.py:198, 203-206`, `tests/n31_fixtures.py:35`, `tests/test_n31_urban_batch1.py:820`, `tools/tests/launch_world.py:98, 162`, `tools/tests/test_tools_launch.py:175` | 망 sha, 경로, 파일 이름 |
| C-6 | `N31D/derive_ramp_forecast_n31.py:14-16, 37-43` | OBS/PATTERN/INPUTS → v3c1 fit 5시드(s37 금지) |
| C-7 | `scripts/build_obs150_detectors.py:50-52, 134-135` | NETWORK_SHA256 (여섯째 상수) |
| C-8 | `scripts/derive_unsignalized_validation.py:40, 43-45`, 문서 | FZPS → v3c1 fit 5 |
| C-9 | DEFAULTS: `scripts/derive_phase_authority_v3b.py:53-59`, `derive_routing_beta_physical.py:82-94`, `derive_unsignalized_turns.py:35-41`, `derive_route_queue_attribution.py:50-57`, `derive_area_routes_v3b.py:43-49` | 새 경로. 또는 명령줄로 모두 넘깁니다(출력이 인자 문자열을 기록하므로 한 방식으로 통일) |
| C-10 | `evaluation/controllers/vissim_stackelberg_adapter.py:3994-3999, 4080`, `evaluation/controllers/beta_source.py:40`, `tests/test_n31_beta_source.py:35-56` | β 원천 이름·경로 결정(§8 D1). `make_config_n31.py:309-311, 361-363`이 `BETA_EVIDENCE_JSON[source] == BETA_FILE`을 요구합니다 [읽음] |
| C-11 | `evaluation/controllers/physical_movement_routes.py:511-513` (함수 `:442-575`) | NA-7에 선언된 1160만 허용하고, 다른 결정은 계속 거부합니다. 시험을 추가합니다 |

- 런타임 sha 검사 모듈들은 핀을 읽기만 합니다(제안서 §6.2 (바)). 망 사본 도구 `D:/VISSIM-merge/tools/prepare_sdmpc31_network.py`도 sig_manifest에서 이름과 sha를 읽습니다 [읽음 :76-117]. 코드 변경이 필요 없습니다.

---

## 4. 단계 3a: v3b 망의 기존 drift

### 4.1 방법 [실행]

- 스크래치 트리를 쓰지 않은 이유
  - 스크래치 경로(약 142자)에 저장소 상대 경로(최장 약 150자)를 붙이면 Windows MAX_PATH 260을 넘습니다.
  - LongPathsEnabled는 0입니다 [실행 reg query]. `git archive`로 풀어 본 트리는 Python에서 `FileNotFoundError`가 났습니다.
- 그래서 생성기를 **깨끗한 저장소에서 읽기 전용으로** 돌렸습니다.
  - `python -B`, `PYTHONDONTWRITEBYTECODE=1`, BELOW_NORMAL(읽기값 0x4000, 자식 상속)로 돌렸습니다.
  - 출력은 `--check`(메모리 비교)이거나 절대 경로 `--out`로 스크래치에 썼습니다.
  - 전후 메타데이터 스냅숏으로 두 저장소 모두 **추가·삭제·변경 0**을 확인했습니다(`repo_snapshot.py`).
- 독립 대조 두 가지를 더 돌렸습니다.
  - `audit_copies.py`: 모든 N31D JSON의 relFlow·경로·XML 속성 사본을 망과 대조합니다. 재핀 도구를 import하지 않고, 파서는 `netv3_common.py`(88c6c556)를 씁니다.
  - `witness_sets.py`: 닫힌 경로 증거 집합이 새 경로에 닿는지 봅니다.

### 4.2 생성기 재실행 결과 (v3b 망) [실행 `v3b_regen/results.json`]

| 생성기 | 결과 |
|---|---|
| derive_phase_authority_v3b | 바이트 동일 (e729cdc4) |
| derive_area_routes_v3b | 계약·provenance 모두 바이트 동일 (fdc21f06 / db5826a1) |
| derive_routing_beta_physical | 바이트 동일 (41b3113f) |
| derive_unsignalized_turns | 바이트 동일 (6febd53f) |
| derive_route_queue_attribution | 바이트 동일 (ec8697a4) |
| derive_routing_turn_beta (+ explicit) | 바이트 동일 (movement_beta_routing_v3b) |
| build_obs150_detectors --check | OK, 294행, 108debbb |
| repin_scenario_v2 verify | `REPIN_VERIFY_OK files=70 pins=122 net=identical` |
| make_reference_config --check | OK |
| make_plant_n31 --check | OK (a087aa67) |
| make_config_n31 --check / --urban-batch1 / U1,U3 | OK (82688d2f / 0f78bfa6 / f88d05f1) |
| offramp_routing.derive_prior | OK |

- **도구 수준 기존 drift: 없음.**
- 돌리지 않은 것
  - `derive_ramp_forecast_n31.py --check`: v3b **s37** boundaries를 읽습니다(보류 자료).
  - `derive_unsignalized_validation.py`: v3b FZP s31/s41/**s37**을 읽습니다.
  - `extract_port_profile.py --check`: FZP를 읽는 (라) 항목입니다.
  - `repin configure-check`: donor 런이 필요하고, drift 목록에는 필요 없습니다.

### 4.3 내용 수준 기존 불일치 [실행 `audit_v3b.json`]

1. `scenario/control_area_membership_213a5d.json` `mixed_transfer_road_routes` 19행 중 5행입니다.

   | 경로 | 파일 | v3b 망 |
   |---|---|---|
   | 1134/1 | "2 0:12" | "2 0:3" |
   | 1134/2 | "" | "2 0:3" |
   | 1134/4 | "2 0:0.25" | "" |
   | 1135/2 | "2 0:3" | "" |
   | 1135/4 | "" | "2 0:3" |

   - 재핀 도구의 `relflow_audit`(`repin_scenario_v2.py:895-929`)은 이 사본이 파생 망(훈련 망)과 같고 그 결정이 바뀌지 않았을 때만 "lineage"로 받아들입니다.
   - verify가 통과했고, 영수증 `repin_receipt.json` files[0].relflow_copies.lineage가 정확히 이 5행을 적고 있습니다 [실행·읽음].
   - 런타임 독자는 없습니다(`test_repin_scenario_v2.py:570` `test_lineage_relflow_copies_have_no_runtime_reader`, 도구 문서 `:798-806`) [읽음].
   - **판정:** 제안서 R3(v)의 "재유도 뒤 diff 0 기대가 깨짐"은 도구 입장에서는 기록된 lineage입니다. v3c1 재핀 뒤에도 같은 5행이 같은 값으로 남아야 합니다. 1134·1135는 v3c1에서 편집하지 않았습니다.
2. **새로 찾음:** `urban/control_area_route_contract_v3b_20260926.json`과 그 바탕 `diagnostics/control_area_route_contract_physical_routes.json`의 `native_routes` XML 사본입니다.

   | 결정 | 파일 | v3b 망 | 영향 행 |
   |---|---|---|---|
   | 1061 | pos 2.341, relFlow 117/1026/57 | pos 6.0, relFlow 0/7128/2324 | movement 6개(SC107 W_SC1004·W_SC1005의 세 방향) |
   | 1128:2 | relFlow "" | "2 0:2" | 3개 |
   | 1124 | pos 1394.08 | pos 212.30 | 1개 |

   - 합계: relFlow 사본 17개 중 9개, 속성 사본 51개 중 16개가 다릅니다.
   - `derive_area_routes_v3b.py`는 바탕을 복사해 한 경로만 더하므로 사본을 갱신하지 않습니다 [읽음 :62-90, 복사는 :90].
   - 이 행들은 `weight_source: "exact movement route identity; no branch weighting"`, `weight: null`입니다. 그래서 런타임이 이 relFlow를 가중치로 쓰지 않을 것으로 봅니다 [추론, 독자 전수 확인 안 함].
   - v3c1에서 바이트까지 같습니다. 처리는 §8 D5에서 정합니다.
3. 경로 증거 집합(witness) 가운데 v3b에서 단일 경로 포함 규칙과 다른 12행은 두 경로를 이어 붙인 증명입니다(SC1004/SC107 구역). 규칙 차이이지 drift가 아닙니다. 새 경로도 닿지 않습니다 [실행].

### 4.4 v3c1 몫 분리 [실행]

- 같은 대조를 v3c1 s31 망(2577209b)에 돌렸습니다. 모든 파일의 불일치·인용 집합이 v3b와 **동일**합니다(`audit_v3c1_s31.json`).
  - 기존 결정은 v3c1에서 바이트가 같다는 영수증 검사(`line_diff_vs_v3b_only_inserted_block`)와 맞습니다.
  - 따라서 **v3c1 재핀 diff에서 위 두 건은 나타나지 않습니다.** 나타나는 것은 §4.5의 목록뿐이어야 합니다.
- 새 경로 23개가 닿는 기존 증거 행: `physical_projection_support_635`의 2행뿐입니다(NA-9).
- 재핀 도구: `characterize_changes`가 v3b에서는 통과하고, v3c1에서는 `elements added ['1160', '1162', '1163', '1164', '1165', '1166', '1167', '1168']`로 거부합니다(`repin_characterize_v3c1.txt`).
- 1083 가드
  - 입력 원천 링크의 결정 수: v3b는 21 → 없음, 256 → 없음입니다.
  - v3c1은 21 → [1160], 256 → [1162]입니다(`guard_1083_source_decisions.json`).

### 4.5 v3c1 미리보기로 확정한 "재핀 뒤 허용되는 diff" [실행 `preview/compare_preview.json`]

- 방법: v3b 손 기록·전달 선언의 망 sha(필요한 곳은 경로도)만 v3c1로 바꾼 스크래치 사본을 입력으로 도시 생성기 6개를 돌렸습니다.
- FZP 유래 입력(unsignalized validation)은 v3b 표를 sha만 바꿔 썼습니다. 이 부분은 (라)에서 다시 봅니다.

| 산출물 | 재핀 뒤 허용 diff |
|---|---|
| routing_v3b2 β | 26개 movement(V1: SC109_W_SC108 L .2379→.1740, T .7621→.8260; V3: SC5_S N .6498→.5245, W .2269→.1720, E .1233→.3035; V4: SC16_N_SC12 S .9622→.8351, E .0227→.1574, W .0151→.0075; V5: SC1_N S .8737→.7727, W .1044→.1665, E .0219→.0608; V6: SC101_S E .0439→.0971, N .7228→.6719, W .2333→.2310; V7: SC104_S_SC106 N .5→.6530, W .25→.0584, E .25→.2886; 나머지는 같은 값의 별칭 접근로). no_route_evidence_approaches [SC104\|S_SC106, SC108\|W] → [] |
| routing_v3b β | 19개 movement(SC104_S_SC106 3개 신설 포함). **NA-3을 넣은 뒤에는 SC1005_W_SC1004 두 행이 v3b 값으로 돌아와야 합니다** |
| route_queue_attribution | routes/route_end_anchors에 1160:1–1168:3 (46경로)만 |
| physical_phase_authority(U1) | 내용 0 (출처 6경로) |
| area route contract | 계약 0 (provenance만) |
| unsignalized_turns | 내용 0 (출처 5경로) |
| obs150 CSV | 0 (108debbb). 사이드카만 |

---

## 5. VSL 응답 법칙 L1 + 행동 집합 {80,90,100,110} 명세

### 5.1 값 [읽음 `N1_RESULTS.md` §6.1, §6.4 ①, `fit_results.json` (a81eb5cf…) k4_core.fits.L1]

- FW_E: `{"law": "carlson", "A": 0.94, "E": 1.44, "alpha": 0.0}`.
  - held-out 손실은 L1 149.66, L2 141.67입니다. 10% 안이라 모수가 적은 L1이 선택됩니다.
  - 규칙 (b)(i)로는 Carlson 계열이 χ²/자유도 4.19로 형식상 기각됩니다. 이 과제의 사용자 결정이 L1을 지정했으므로 QUALIFICATION에 함께 적습니다.
- FW_W: 법칙 없이 옛 cap을 유지합니다(`make_reference_config.py:30`).
- 행동 집합: [80,90,100,110]. 최댓값 110은 그대로입니다.
  - 그래서 Carlson 기준 b = 명령/max(vsl_set) = c/110이 바뀌지 않습니다(`freeway_fd.py:39`).
  - v_free 110, `max_vsl_step` 40(`config_n31_v2.json:7465`)도 그대로입니다.
- 네 곳이 같아야 합니다(`CONTRACT.md:688`): 러너, 튜닝, reference, SDMPC 좌표.

### 5.2 파일:줄

| 곳 | 파일:줄 | 변경 |
|---|---|---|
| reference (plant) | `N31D/make_reference_config.py:59` VSL_FD_RESPONSE, `:58` VSL_SET, `:63-69` VSL_MODEL_NOTE, 문서 `:1-33`, NETWORK/GEOMETRY `:53-55` | L1, [80..110], N1 출처(계획 sha 0db0d1c6, fit 결과 a81eb5cf, 선택 L1). 산출 `reference_config_n31_v2.json`: vsl_set `:7466`, vsl_fd_response `:8028-8035`, 주석 `:8052`, `_n31_note :8220` |
| 튜닝 | `N31D/make_config_n31.py:140` VSL_SET, `:237-242` 주석 | `config_overrides.freeway_follower.vsl_set`(`config_n31_v2.json:7466-7474`, 묶음 1 후보 두 개도 같은 키) |
| 러너 VBS | `N31D/repin_scenario_v2.py:144` VSL_SPEEDS → `set_vsl_speeds :705-725` → `scenario/lane_native_b110.vbs:34` | `RW_ALLOWED_VSL_SPEEDS = "80,90,100,110"`. `runner_config_check`(:732-756)가 망에 같은 번호의 속도분포가 있는지 검사합니다. 80–110은 있습니다 [읽음 `CONTRACT.md:690`] |
| SDMPC 좌표 | `evaluation/controllers/sdmpc.py:333-341`(축), `:389-394`(가장 가까운 허용값), `:421-430`(허용값 탐침) | **코드 변경 없음.** 튜닝 vsl_set을 읽습니다. scale = max = 110이라 z 척도와 fd 보폭이 같습니다. 블록 0이 110에서 허용하는 값은 {70..110} → {80..110}, 축 수는 같습니다 |
| plant 법칙 | `evaluation/controllers/freeway_fd.py:19-46`, 잼 검사 `:104-105` | **코드 변경 없음.** b = 1이면 A·E와 무관하게 공칭 FD입니다. 80에서 ρc 배수는 1+0.94·(30/110) = 1.256입니다. 급 ρc 25/28 veh/km/차로(`segment_params.json` plain_class)라 잼 밀도 검사에 걸리지 않을 것으로 봅니다 [추론, T9·vsl 시험이 80에서 실제로 확인] |

### 5.3 시험

- **T9** (`N31D/tests/test_n31_ad_smoke.py`, 작업은 `tests/n31_ad_smoke.py`)
  - 현재 이미 "110에서 한쪽 도함수가 0이 아님"을 단언합니다(`:57-70`: `max_abs_tangent > 0`, AD 대 왼쪽 차분·Richardson 1%, FW_W 열은 0).
  - 80에서 AD 대 중앙차분 비교도 있습니다(`:89-92`, `n31_ad_smoke.py:190-197`, h = 0.25, 상대 1e-4).
  - 바꿀 것
    - (i) `vsl_below_max`의 기준점을 80 하나에서 **80·90·100**으로 늘립니다. 새 행동 집합의 내부점입니다.
    - (ii) reference의 `vsl_fd_response['FW_E']`가 L1 값인지 단언합니다. 조용히 되돌아가는 것을 막습니다.
    - (iii) 110 한쪽 도함수 단언과 FW_W 0 열은 유지하고, 문서(`n31_ad_smoke.py:14-21`, `test_n31_ad_smoke.py:58`)의 A0.5/E4를 L1으로 고칩니다.
  - L1은 E가 작아 곡률이 작습니다. 그래서 1e-4/1%의 허용 오차가 유지될 것으로 봅니다 [추론, 재핀 때 실행].
  - 주의: T9는 `tests/` 폴더에 임시 파일을 씁니다(`test_n31_ad_smoke.py:25`). 이번에는 돌리지 않았고, 새 worktree에서만 돌립니다.
- `tests/test_n31_generators.py:76-77`(L1 리터럴), `:84-91`, `:207-208`(vsl_set 리터럴)
- `tests/test_repin_scenario_v2.py:183-198`(set_vsl_speeds 기대값, `:194` VSL_SPEEDS == config == reference), `:550-557`(runner check 리터럴)
- `tests/test_n31_vsl_model.py:111`(설치된 법칙 = L1), `:1` 문서
  - `:147`은 가드 시험용 합성 입력이라 그대로 두어도 됩니다.
  - `test_110_hold_is_bit_identical`(`:118`)과 `test_below_110_is_active_and_conserved`(80 명령, `:134-143`)는 L1에서도 성립해야 합니다.
- 합성 vsl_set을 쓰는 커널 시험(`test_n31_initialize.py:121, 161`, `test_n31_t6_runner.py:35` 등)은 행동 집합 상수와 무관합니다. 바꾸지 않습니다.

### 5.4 매니페스트 다시 만들기 (순서가 핀 연쇄를 따름, `CONTRACT.md:692`)

1. `lane_native_b110.vbs`(repin build) → obs150 사이드카(runner_config 핀)
2. `reference_config_n31_v2.json`(make_reference_config)
3. `plant_n31_v2.json`(make_plant_n31: 망, 기하, reference, 러너, port_profile, sig_manifest, membership 핀과 QUALIFICATION)
4. `config_n31_v2*.json`(make_config_n31, `validate_tuning_v2`로 plant와 대조)

QUALIFICATION 문구는 다음을 담습니다(`make_plant_n31.py:64-76` 교체).
- "network v3c1 (v3b + decisions 1160, 1162–1168; V2 held)"
- "VSL law = N1 L1 Carlson A 0.94 / E 1.44 / alpha 0 on FW_E (fit on v3b NC s41/43/47/53, 80–110; Carlson family formally rejected by rule (b)(i) χ²/dof 4.19, selected by user decision), FW_W legacy cap"
- "action set 80–110"
- geometry, port profile, ramp forecast를 v3c1 fit 5시드에서 다시 뽑았다는 사실

### 5.5 비트 동일·회귀 점검

1. **all-110 비트 동일.** b = 1이면 L0와 L1이 같은 FD입니다. 그래서 명령이 모두 110일 때 예측 값은 L0 reference와 L1 reference에서 비트 단위로 같아야 합니다. 도함수는 다릅니다.
   - 단위 시험: `test_110_hold_is_bit_identical`
   - 런 상태 점검(R-obs 뒤, 스크래치): v3c1 R-obs 상태 하나에서 L0/L1 reference로 plant 롤아웃 값을 비교 → IDENTICAL, FW_E VSL 축 도함수는 다름.
2. **T9**: §5.3.
3. **생성기 `--check` 연쇄**: reference, plant, config ×3, obs150, repin verify. 시험 묶음: N31D tests, `tools/tests`, `diagnostics/obs150_20260924/tests`.
4. **T5 (R-obs가 생긴 뒤)**
   - `N31_G1_STATE=<R-obs>\decisions_<Name>\state_000900.json`으로 `tests/test_n31_initialize.py:99-104`(`test_g1_frame`)를 돌립니다(`PLANT_PORTING_GUIDE.md:579`).
   - 결정 재생 `tools/make_replay_state_v2.py prepare` + `tools/replay_decision_n31.ps1` → `REPLAY_COMPARE verdict=IDENTICAL`(같은 입력의 결정적 재현). ps1이라 승인이 필요합니다.
   - 재생된 SDMPC 결정의 VSL이 모두 {80..110}에 있고, 결정 metadata의 블록 0 허용집합이 {80..110}인지 확인합니다.
   - v3b 상태와의 교차 비교는 하지 않습니다. 망 sha가 다르고, 행동 집합이 바뀌어 결정이 달라지는 것이 정상입니다.
5. 폐루프 FW_E 효과는 J1(3시드 이상 짝)로 봅니다(N1 §9).

---

## 6. 작업 순서와 worktree/branch

| 단계 | 내용 | 승인 |
|---|---|---|
| P0 | 이 계획, 단계 3a 기준선(완료) | — |
| P1 | v3c1 NC 5시드 재판정(s47/s53, G1–G6). 항목이 되돌려지면(v3c2) `repin_drift/`의 스크립트(audit_copies, witness_sets, preview_urban_v3c1, obs150 미리보기)를 새 망 경로로 다시 돌려 이 목록을 갱신합니다 | — |
| P2 | 승인: Q12(C-1…C-9, C-11), VSL L1 + {80..110}, NA-3, NA-7, §8 결정 | 사용자 |
| P3 | 새 worktree: `git -C D:/VISSIM-merge/sim3-n31-urban worktree add D:/VISSIM-merge/sim3-n31-v3c1 -b claude/repin-v3c1-<날짜> cf3ce37`. `frozen/*`, `sim3-n31`, `sim3-n31-urban` 작업 트리는 건드리지 않습니다. 이것이 첫 git 쓰기입니다 | 사용자 |
| P4 | RA-1 추출(fit 5시드, 한 번에 하나, BELOW_NORMAL, 약 5분). 새 폴더에 `.gitattributes`를 v3b 폴더처럼 둡니다 | — |
| P5 | C-4(추가 결정 열거표, NA-7 수정 규칙, VSL_SPEEDS) + C-11 + 시험 → `repin_scenario_v2.py build` → `verify` | — |
| P6 | 손 기록 NA-3·NA-4·DA-4·DA-5(새 이름 `*_v3c1_<날짜>`), C-9. 다음 순서로 돌리고 v3b 산출과 diff해 §4.5 목록만 허용합니다: derive_phase_authority → derive_routing_beta_physical → C-8 + derive_unsignalized_validation(FZP fit 5) → derive_unsignalized_turns → derive_route_queue_attribution → derive_area_routes; 그리고 derive_routing_turn_beta | — |
| P7 | plant 연쇄: C-3 + RA-3, C-7 + DA-7, V-1 reference, (P5에서 만든) VBS, C-2 plant, C-6 + RA-4, C-1 config 세 벌, C-10(결정대로) | — |
| P8 | 시험과 점검: §5.5 1–3, `scripts/preflight_tuning_paths.py`, `repin_scenario_v2.py configure-check`(임시 폴더에만 씀; 다른 런타임 검증기의 거부를 R-obs 전에 잡음), 문서 DA-8 | — |
| P9 | 커밋(새 브랜치) → `D:/VISSIM-merge/tools/freeze_worktree.ps1` → 동결 트리에서 `run_sdmpc_n31.ps1 -PreflightOnly`(VISSIM 없음) → R-obs 발사. 발사는 세션과 분리해 WMI로 합니다(memory `vissim-launch-detached-from-session`) | 사용자 (커밋, 발사) |
| P10 | R-obs 뒤: T5(§5.5 4), U1 T1(RA-6), 묶음 2 G0 계열 오프라인 관문 | ps1은 승인 |

- 제안서 §8.1대로 묶음 2 오프라인 개발은 v3b 핀 트리에서 계속합니다. 재핀 브랜치가 생기면 그 위로 옮깁니다.

---

## 7. 어느 런이 재핀에 의존하나

| 런 | 재핀 필요 | 이유 |
|---|---|---|
| **R-obs** (SDMPC 러너 no-control + obs150, v3c1) | **예, VSL 포함 전체** | LPR과 obs150이 망 sha를 대조합니다. v3c1에서는 1083 가드(NA-7/C-11)가 t=1 configure에서 거부합니다. 러너 VBS와 reference는 plant·obs150 사이드카에 핀되어 있으므로, 뒤에 VSL을 따로 재핀하면 R-obs 상태가 옛 트리에 묶입니다 [추론]. 한 번에 합니다 |
| RM 3팔 (31/37/41, stage-1 규칙 RM) | 아니오 | v2rm 방식 + 망 경로 블록으로 따로 짓습니다(`D:/VISSIM_runs/20260925_v3b/rm_build/build_v3brm.py:1-27` 방식). SDMPC 핀을 쓰지 않습니다 [읽음] |
| NC 6시드 | 아니오 | 이미 지었습니다. s47/s53은 진행 중이고, s37은 봉인입니다 |
| 폐루프 S0e-v3c1, 묶음 2 후보 | 예 | 재핀과 R-obs 관문(G0)이 필요합니다 |
| 봉인 59/61/67 | 5라운드 동결 뒤 | — |

---

## 8. 사용자가 정할 것

| # | 질문 | 권고 |
|---|---|---|
| D1 | β 원천 이름·경로(C-10) | 새 파일 `movement_beta_routing_v3c1{,_2}_<날짜>.json`과 새 원천 키를 두고, v3b 키는 뺍니다(v3b 재생은 동결 트리에서). 어댑터 3줄 + `beta_source.py:40` + 시험을 바꿉니다. 대안은 키 이름을 "세대 이름"으로 두고 경로만 바꾸는 것입니다(코드 변경은 같고 이름이 망 버전과 어긋남) |
| D2 | 1083 가드(C-11)와 선언(NA-7) | 허용 목록에 1160만 넣습니다. V1을 되돌리는 대안은 권하지 않습니다(관문 통과) |
| D3 | NA-3 explicit 1165 → SC1\|N_SC101 | 넣습니다 |
| D4 | NA-9 선택 보강(1162:1, 1164:1, 1165:1) | 넣습니다(증거 완결성, 거부와 무관) |
| D5 | U1 area 계약의 옛 사본(§4.3 2) | v3c1 재핀에서는 그대로 두고 기록만 합니다. 갱신은 별도 트랙입니다(바탕 계약의 생성기와 런타임 독자 확인 필요) |
| D6 | 파일 이름 | 새 파일은 `*_v3c1_*`, v3b 파일은 트리에서 뺍니다(memory `vissim-supersede-dont-flag`). 시나리오 선언 이름(`<stem>_<sha6>`)은 팩 경로에서 오므로 그대로입니다 |
| D7 | L1의 적용 | v3b에서 맞춘 FW_E 법칙을 v3c1 plant에 이월 사전값으로 씁니다(QUALIFICATION에 명시) |

---

## 9. 하지 않은 것, 남은 위험

- **하지 않은 것**
  - 코드·핀 변경, git, VISSIM/cscript/fast_nc_run, 시험 묶음 실행(T9는 tests 폴더에 씀), FZP 읽기, configure-check, `derive_ramp_forecast --check`(v3b s37 입력).
- **미리보기의 한계**
  - 손 기록의 sha만 바꾼 입력입니다. FZP 유래 표(unsignalized validation)는 v3b 값입니다.
  - 실제 재핀에서는 RA-5 뒤 DA-3이 달라질 수 있습니다 [추론].
- **남은 위험**
  - 제가 훑은 것보다 많은 런타임 검증기가 새 결정에 걸릴 수 있습니다.
    - 확인한 것: 1083 가드, witness 집합, projection support, native_internal_input, route_choice_corridor 10682, physical_urban_transport 126/10641/71, head_service 1123, lane_plant_runtime 1138/1140, obs150.
    - P8의 configure-check와 PreflightOnly, 그리고 R-obs t=1이 최종 확인입니다.
- **5시드 재판정**
  - 결과에 따라 망이 바뀌면(v3c2) 새 결정 목록과 §4.5 표를 다시 만듭니다.
- **공개**
  - `D:/VISSIM_runs/20260925_v3b/README.md` 앞부분을 읽으면서 v3b s37 NC의 Ω 한 행이 화면에 나왔습니다. 이 계획의 어느 판단에도 쓰지 않았습니다. v3c1 s37, v3b RM 팔 산출, 봉인 시드는 열지 않았습니다.

---

## 10. 파일

- 이 계획: `D:/VISSIM_runs/20260927_v3c1/reports/REPIN_PLAN.md`
- 목록: `D:/VISSIM_runs/20260927_v3c1/reports/repin_inventory.json` (sha256은 `repin_inventory.json`의 `evidence_scratch`에 스크립트별로 있음)
- 스크래치 `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/net-v3c/v3c1/repin_drift/`
  - `bn.py`(BELOW_NORMAL 래퍼), `repo_snapshot.py` + `snap_*.json`(쓰기 없음 증명)
  - `run_v3b_regen.py` → `v3b_regen/results.json`, `logs/`
  - `audit_copies.py` → `audit_v3b.json`, `audit_v3c1_s31.json`
  - `witness_sets.py` → `witness_sets.json`
  - `preview_urban_v3c1.py` → `preview/out/*`, `preview/pins/*`(sha 바꾼 사본, 미리보기 전용), `compare_preview.py` → `preview/compare_preview.json`
  - `obs150_v3c1_preview.py` → `obs150_v3c1_preview.json` (`preview/geometry_s31_PREVIEW_v3b_links_v3c1_sha.json`는 미리보기 전용)
  - `repin_characterize_v3c1.txt`, `guard_1083_source_decisions.json`, `grep_sha_*.txt`, `grep_s37sha_*.txt`, `grep_inpx_urban_n31d.txt`
  - `build_inventory.py` → `repin_inventory.json`
