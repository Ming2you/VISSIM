# v3c1 재핀 실행 보고 (REPIN_PLAN §6 P3–P8)

- 작성 2026-09-28. 계획: `D:/VISSIM_runs/20260927_v3c1/reports/REPIN_PLAN.md`(sha `b00059f2…`), 목록 `repin_inventory.json`.
- 승인: 2026-09-28 사용자 승인(§0 (a)–(f), §3 (가)–(바), §5 VSL L1 + 행동 집합 {80,90,100,110}, §6 P3–P8, §8 D1–D7).
- 작업 트리: `D:/VISSIM-merge/sim3-n31-v3c1`, 브랜치 `claude/repin-v3c1-20260928`, 출발 `cf3ce37`. **커밋·푸시·동결·발사는 하지 않았습니다.** 변경은 모두 커밋 전 상태입니다.
- 표기: **[실행]** 이번에 돌려 얻은 값 · **[읽음]** 코드·파일을 읽고 확인 · **[추론]** 시험하지 않은 판단. 줄 번호는 이 작업 트리 기준입니다. `N31D` = `diagnostics/sdmpc_n31_20260924`.
- 근거 스크립트와 로그: scratchpad `repin-v3c1-exec/`(`p4_extract.py`, `p4_receipts.py`, `p6_hand_records.py`, `p6_c9_defaults.py`, `p7_*.py`, `cmp_v3b.py`, `run_checks.sh`, `run_tests.sh`, `logs/`).

---

## 0. 결론

1. **P3–P8을 순서대로 끝냈고, 실패한 점검은 없습니다** [실행].
   - `repin_scenario_v2.py build` → `REPIN_OK files=70 written=26`, `verify` → `REPIN_VERIFY_OK files=70 pins=122 net=identical`.
   - `configure-check` → `REPIN_CONFIGURE_OK t=1:keys=311,enabled=38 t=150:keys=327,enabled=38 t=900:keys=375,enabled=38`. 1083 가드와 635 projection support가 v3c1 망에서 configure를 통과합니다.
   - 생성기 `--check` 연쇄 16개와 `preflight_tuning_paths.py` 3개가 모두 통과했습니다(§3).
   - 시험: N31 190개(skip 3), T9 9개, repin/prepare pytest 67개, tools 60개, obs150 29개 모두 통과. `extra` 묶음은 7 failed / 4 errors인데, 묶음 1 기준(`urban-b1d/tests/extra.txt`)과 **실패 목록이 정확히 같습니다**(옛 픽스처 부재, 재핀과 무관).
2. **v3b 대비 diff는 §4.5 허용 목록과 같습니다** [실행 `cmp_v3b.py`]. 예외는 두 가지이고 둘 다 계획이 예상한 종류입니다.
   - DA-3 `unsignalized_turns`: 판정(23개 movement와 모든 제외 목록)은 같고, 행에 복사된 FZP 검증 수치만 RA-5(fit 5시드)로 바뀝니다. 계획 §9가 "RA-5 뒤 DA-3이 달라질 수 있다"고 적은 경우입니다.
   - 모든 표의 `generated` 날짜가 2026-09-28입니다.
3. 런타임 코드 변경은 둘뿐입니다. 둘 다 키가 없으면 전과 같습니다.
   - C-11 `physical_movement_routes.check_source_routing_decisions`(`evaluation/controllers/physical_movement_routes.py:451-490`, 호출 `:556`).
   - C-10 β 원천 키 `routing_v3c1`/`routing_v3c1_2`(`vissim_stackelberg_adapter.py:3998-3999, 4082`, `beta_source.py:42`). v3b 키는 뺐습니다(D1, 플래그로 남기지 않음).

---

## 1. 단계별 결과

### P3 worktree [실행]
- `git -C D:/VISSIM-merge/sim3-n31-urban worktree add D:/VISSIM-merge/sim3-n31-v3c1 -b claude/repin-v3c1-20260928 cf3ce37`.
- 체크아웃 바이트가 목록의 sha와 같습니다: 망 `be0075bf`, `make_config_n31.py` `4de0202d`, `repin_scenario_v2.py` `c2378c8b`, `physical_movement_routes.py` `03140235`.

### P4 RA-1 추출 [실행]
- `extract_observations.py`를 fit 5시드에 하나씩 돌렸습니다. 자기 자신과 자식 모두 BELOW_NORMAL이고, typed ctypes로 읽어 0x4000을 확인했습니다. 각 약 88–92 s였습니다.
- 명령 형태는 v3b 영수증과 같습니다(`--phase-sec 0.1`, geometry profile, refined geometry `9769b3a4`).
- 산출: `metanet_calibration_v1/v3c1_nc_20260928/`.
  - v3b 폴더처럼 `.gitattributes`(`* -text`), 시드별 `boundaries_30s.csv`·`manifest.json`, s31 `geometry.json`, 영수증 `s{seed}_v3c1nc_extraction_receipt.json` 5개를 둡니다.
  - 나머지 산출(cells/flows 등)은 manifest에 sha로 남기고 scratch `p4_pruned/`로 옮겼습니다.
- 검증
  - 5시드 모두 checks 18538, last frame 8995.1 s, 망 sha가 각 시드의 v3c1 sha와 같습니다.
  - s31에 FW_E 본선 미설명 손실 1대가 있습니다(차량 34211, 4090.1–4095.1 s). 영수증 `note`에 적었습니다. v3b s31은 0대, v3b s37은 1대였습니다.
  - s31 기하는 v3b 기하와 출처 키 6개(`network`, `source_network`, 네 입력 경로)만 다르고, 입력 sha는 같습니다 → `8752f0cd`.
- s37은 추출하지 않았고, 어떤 FZP도 열지 않았습니다.

### P5 재핀 도구 + 1083 가드 [실행·읽음]
- **C-4** `repin_scenario_v2.py`
  - 망 상수(`:102-111`)를 v3c1로 바꿨습니다. 이전 망은 v3b `be0075bf`이고, 영수증 note는 `PREVIOUS_RUNTIME_NOTE`입니다.
  - `VSL_SPEEDS = (80, 90, 100, 110)`(`:162`).
  - 추가 결정 열거표를 넣었습니다.
    - `V3C1_EDIT_RECEIPT`(`:406`, sha `8e69013d…`)
    - `V3C1_ADDED_DECISIONS`(`:410-419`, 결정·항목·링크·pos·경로 수 8행)
    - `V3C1_INSERTED_BLOCK`(`:420`, 1159 뒤 9293 B, `2b77ab01…`)
  - `characterize_changes(…, added_decisions=…)`(`:506`)는 추가된 결정 번호가 열거표와 정확히 같을 때만 받습니다. `CHANGE_RULES`는 넓히지 않았습니다.
  - `added_block_audit`(`:588`)는 바이트 블록의 위치, 길이, sha, 내용 순서를 다시 증명합니다. 결과는 전달 영수증 `repin_step.added_decision_block`에 남습니다.
  - 전달 선언 편집 열거표 `V3C1_DECLARATION_AMENDMENTS`(`:430`)는 네 행입니다.
    - `apply_amendments`(`:1159`): 옛 값이 맞아야 적용합니다.
    - `amendment_check`(`:1134`): 1083은 런타임과 같은 `check_source_routing_decisions`로, 635는 새 route id가 `physical_triplet`을 지나는지로 대상 망에서 다시 증명합니다.
    - 적용 기록은 `scenario_derivation.declaration_amendments`와 영수증 `files[].declaration_amendments`에 남습니다. 모든 행이 쓰였는지도 확인합니다(`:1371`).
- **NA-7 / D2**: 1083 선언에 `reviewed_source_decisions = [1160]`을 넣었습니다(링크 21, pos 20.0, 경로 `21-10112-174-10281-173-10286-1220009502` / `…-10280-173-10285-1220000803`). `native_route_prior` 문구도 v3c1로 고쳤습니다.
- **NA-9 / D4**: `/evidence/10419/native_route_ids` = [1024:1, 1162:1], `/evidence/10568/native_route_ids` = [13:1, 1164:1, 1165:1].
- **C-11** `physical_movement_routes.py:442-490`
  - 원천 링크의 결정 집합이 선언 목록과 같아야 합니다.
  - 각 결정의 번호, 링크, pos, 모든 경로의 링크열이 망 요소와 같아야 합니다.
  - 모든 경로가 `[source, connector, receiver]` = `[21, 10112, 174]`로 시작해야 합니다.
  - 키가 없으면 목록이 비고, 원천 링크의 결정은 전처럼 같은 메시지로 거부됩니다.
- **시험**
  - `tests/test_n31_source_decision_guard.py`(새 파일, 7개): 옛 규칙 유지, 1160 허용, 다른 결정 거부, 위치·경로 변경 거부, 누락 거부, 다른 회전 거부, 형식 오류, 실제 핀 선언과 v3c1 망에서 `['1160']`, 키를 빼면 거부.
  - `test_repin_scenario_v2.py`에 합성 시험 5개와 실제 팩 시험 1개를 더했습니다. 추가 결정 허용·거부, 바이트 블록, 영수증 대조, 편집 규칙, NA-7/NA-9 열거, 1134/1135 lineage 5행 유지를 봅니다.
- build 전에 v3b 망 사본을 지웠습니다(`write_outputs`가 폴더에 산출물 밖의 파일이 있으면 거부합니다).
- build/verify diff는 §2와 같습니다.

### P6 손 기록과 도시 유도 연쇄 [실행]
- 새 손 기록 넷을 만들고 v3b 파일은 트리에서 지웠습니다(`p6_hand_records.py`). 각 파일은 `repin`/`v3c1_repin` 필드로 앞 파일(path, sha)을 기록합니다.
  - NA-3 `beta/explicit_approach_v3c1_20260928.json`(`c74dfebe`): 망 핀과 `"1165": [["SC1","N_SC101"]]`를 바꿨습니다(D3). 1165의 physical 설명도 넣었습니다.
  - NA-4 `beta/approach_entry_v3c1_20260928.json`(`8c44404e`): 망 핀과 SC108\|W `why` 문구를 바꿨습니다. entries는 그대로입니다.
  - DA-4 `urban/movement_nonexistent_v3c1_20260928.json`(`e822196b`): 망 핀만 바꿨습니다. 결정 행은 그대로입니다.
  - DA-5 `urban/offramp_static_route_prior_v3c1_20260928.json`(`2f916a87`): 망 핀만 바꿨습니다. `offramp_routing.derive_prior`가 통과합니다(`check_urban_batch1`).
- C-8/C-9: 생성기 6개의 DEFAULTS와 `--generated` 기본값(2026-09-28)을 새 파일로 바꿨습니다. `derive_unsignalized_validation.FZPS`(`:45`)는 v3c1 fit 5시드입니다.
- 순서대로 유도했습니다. v3b 비교는 `cmp_v3b.py`로, 같은 역할의 핀을 v3b→v3c1로 사상한 뒤 JSON 포인터 단위로 했습니다.

| 단계 | 산출(sha8) | v3b 대비 | §4.5 |
|---|---|---|---|
| derive_phase_authority | `urban/physical_phase_authority_v3c1_20260928.json` 77d43c5c | `generated`만 | 내용 0 ✓ |
| derive_routing_beta_physical | `beta/movement_beta_routing_v3c1_2_20260928.json` 4979c05c | β 26개(V1, V3–V7과 별칭), 사유 SC104\|S_SC106·SC108\|W → relflow, `no_route_evidence_approaches` [] | ✓ 26개 모두 영수증 `expected_plant_beta.beta_v3c`와 정확히 같음(불일치 0) |
| derive_unsignalized_validation(FZP 5개, 약 5.9 GB) | `urban/unsignalized_validation_v3c1nc_20260928.json` 42515ae9 | 내용(망 + 시드 집합) | (라) 예상대로. `--check` 재실행에서 같은 바이트 |
| derive_unsignalized_turns | `urban/unsignalized_turns_v3c1_20260928.json` 95ea2732 | movement 23개와 모든 목록 같음, 행의 검증 수치만 바뀜 | 판정 0. 검증 수치는 RA-5 결과(§0.2) |
| derive_route_queue_attribution | `urban/route_queue_attribution_v3c1_20260928.json` 01d58ca8 | routes/route_end_anchors 1160:1–1168:3 46개 + `generated` | ✓ |
| derive_area_routes | `urban/control_area_route_contract_v3c1_20260928.json` fdc21f06(바이트 동일), provenance 5ce65a45 | 계약 0, provenance는 `generated`만 | ✓ |
| derive_routing_turn_beta(+explicit) | `beta/movement_beta_routing_v3c1_20260928.json` c5484fff | β 17개(SC104_S_SC106 3개 신설 포함). SC1005_W_SC1004는 v3b 값 그대로 | ✓ (NA-3 없이 19개였던 것에서 SC1005 두 행이 빠짐) |

- 추가 결정의 부착 [실행]
  - 1160 → SC109\|W_SC108, 1162 → SC5\|S_SC11, 1163 → SC16\|N_SC12, 1164·1165 → SC1\|N_SC101(1165는 명시 배정), 1166·1167 → SC101\|S_SC1, 1168 → SC104\|S_SC106.
  - 템플릿 결정(13, 283, 1014, 1024, 1081)이 붙은 접근로와 같습니다.
- U1 area 계약의 옛 사본(1061, 1128:2, 1124; §4.3 2)은 D5대로 그대로 두었습니다. `make_config_n31.py`의 주석과 이 보고에 적었습니다.

### P7 plant 연쇄 [실행]
- **RA-3 / C-3** 포트 프로필 `51934e48`: v3c1 s31 NC, FZP `5c9e43e8`, 900 s 이하.
  - v3b 대비 |Δ| ≤ 2.07 km/h입니다(10483 +2.07, 10646 +1.97, 10682 +1.78, 10480 −1.59). 표본 수는 ±7 이내입니다.
- **DA-7 / C-7** obs150: CSV `108debbb` 바이트 그대로(294행). 사이드카는 망, 기하, 러너, 헤드 계약 sha와 생성기 `sha256_lf`만 바뀝니다.
  - 새 plant 전에는 명시 인자로 만들었고, config가 생긴 뒤 기본(튜닝 경유) `--check`가 통과했습니다.
- **V-1** reference `6c597e25`: `vsl_fd_response.FW_E` = L1 {A 0.94, E 1.44, alpha 0}, `vsl_set` [80,90,100,110], `_vsl_model_note`(N1 출처 sha: fit `a81eb5cf…`, 계획 `0db0d1c6…`). 표지 셀과 transport는 그대로입니다.
- **VBS** `f0ed036e`(P5 build): `RW_ALLOWED_VSL_SPEEDS = "80,90,100,110"`. `runner_config_check`에서 네 속도 모두 같은 번호의 분포가 있습니다.
- **C-2** plant `aaf49170`: 망, 기하, reference, 러너, 포트, sig_manifest, membership 핀과 QUALIFICATION(v3c1, L1 자격, 이월, 80–110, fit 5시드 재추출)을 바꿨습니다.
- **C-6 / RA-4** `derive_ramp_forecast_n31.py`: OBS/PATTERN/INPUTS를 v3c1 fit 5시드로 바꿨습니다(`boundaries_30s.csv` ab52fe80/ec2c9779/f67e2508/9365a93d/50dd5e9d).
  - drain 16.0/43.6/30.2/88.5/40.8/159.6/33.4/44.4 s, cap 220/2347/408/545/551/1248/843/592 veh/h입니다(RM_C10480/10482/10646/10644/10639/10681/10490/10484).
  - `make_config_n31.RAMP_FORECAST`(`:179`)에 옮겼고 `--check`가 통과합니다.
- **C-1** `make_config_n31.py`: 망 상수(`:79-81`), BETA_*(`:93-97`), URBAN_B1_* 핀 전부, `VSL_SET`(`:154`), 주석을 바꿨습니다.
  - config `33027258`, 후보 U1+U2+U3 `ad482a53`, U1+U3 `8187505d`.
  - v3b 대비 diff는 망 핀, 램프 예측 16값, `vsl_set`, β 원천·핀, 묶음 1 입력 경로·sha, `known_wout_route_evidence` sha, 주석뿐입니다.
- **C-10 / D1**
  - 어댑터 `BETA_EVIDENCE_JSON` = {routing, knr, routing_v3c1, routing_v3c1_2}, `COMPLETE_BETA_SOURCES = {routing_v3c1_2}`.
  - 옛 키 `routing_v3b`는 이제 설치에서 "urban.beta.source 는 … 중 하나" 오류가 납니다(시험 `test_the_v3b_sources_left_this_tree`).

### P8 시험·점검·문서 [실행]
- **생성기 연쇄**(`run_checks.sh`, 로그 `logs/checks_p8.log`): repin verify, 도시 생성기 5개 `--check`, obs150 `--check`, reference/plant/ramp forecast/config ×3/port profile `--check`, preflight ×3 모두 exit 0입니다. `derive_unsignalized_validation --check`(FZP 5개)도 같은 sha `42515ae9`를 냅니다.
- **시험**(금지 시험은 돌리지 않음: `test_tools_launch`, `test_tools_replay`, `test_tools_integration`(watchdog ps1), obs150의 ps1/cscript 시험)
  - N31 unittest 16모듈: Ran 190, OK, skipped 3(`test_missing_owner_inputs_are_listed` 설계상, `test_regenerates_bytes` N31_SLOW, `test_g1_frame` N31_G1_STATE).
  - T9 `test_n31_ad_smoke`: Ran 9, OK.
    - 110에서 한쪽 도함수가 0이 아니고, 80·90·100에서 AD == 중앙차분(상대 1e-4)이며, reference 법칙 == L1입니다.
    - 새 기준점은 `n31_ad_smoke.py:191`에 있습니다. 임시 파일은 남지 않았습니다.
  - pytest `test_repin_scenario_v2` + `test_prepare_sdmpc31_network`: 67 passed(configure 시험 t=1 포함).
  - tools(plant_gate, verify_gt, watch, common): Ran 60, OK. obs150(generator_detectors, lane_context, lane_support): Ran 29, OK.
  - extra(`test_lane_initial_projection`, `test_dynamic_area_routes`, `test_native1083_signal_authority`): 7 failed / 13 passed / 4 errors. 묶음 1 기준과 실패 id 집합이 같습니다(diff 0). 원인은 없는 픽스처 파일과 스냅숏 지문이고 재핀과 무관합니다 [실행·읽음].
- **§5.5 1** all-110 비트 동일: `test_n31_vsl_model.test_110_hold_is_bit_identical`가 L1 reference로 통과합니다. 런 상태에서의 L0/L1 대조는 R-obs 뒤로 남깁니다.
- **configure-check**: 임시 폴더에만 썼고, t=1/150/900에서 control과 v3c1의 켜진 플래그가 같습니다.
- **문서**: `CONTRACT.md`(v3c1 + L1 + 행동 집합 절 추가), `PLANT_PORTING_GUIDE.md`(머리 노트 v3c1 절과 현재 sha, VSL 표·줄 234/322/356/451-452/485-486/526-527 고침), 생성기 docstring, `test_generator_detectors`·`test_lane_context` docstring.

---

## 2. repin build diff (v3b 트리 대비, 핀 사상 뒤) [실행 `dry_diff.py`]
- 망 사본 `baseline_s31_v3c1nc.inpx`(`2577209b`)를 새로 넣고 v3b 사본을 뺐습니다. `sig_manifest`는 이름, bytes, `copied_from`만 바뀌고 `.sig` 42개는 바이트 같습니다.
- 1083 선언: 편집 두 개와 `declaration_amendments`. 635 support: `native_route_ids` 두 행과 `declaration_amendments`.
- `historical_prior_transfer`
  - `native_changes`에 `added_decisions`, `added_decision_receipt`, meaning 문구가 더해집니다.
  - `repin_step.added_decision_block`이 생기고, limitations 문구가 바뀝니다.
  - `actual_native_differences` 결정 added 0→8, changed 28→36입니다(`native_diff`는 추가도 changed로 셈).
- 사전 이월 선언 7개: `prior_mismatch.differences_since_previous_pack` 문구만 바뀝니다("… (24 elements, 8 added)").
- membership: 내용 0입니다. 1134/1135 lineage 5행이 그대로 남습니다(§4.3 1, 시험으로 고정).
- 나머지 선언: 망 핀과 이를 가리키는 sha만 바뀝니다.
- config base: `description` 문구만 바뀝니다.
- 영수증: 위 내용, `runner_config_check.allowed_vsl_speeds` [80,90,100,110], 이전 망 = v3b.

---

## 3. §8 결정의 적용

| # | 적용 |
|---|---|
| D1 | 새 파일 `movement_beta_routing_v3c1{,_2}_20260928.json`, 키 `routing_v3c1`/`routing_v3c1_2`, v3b 키·파일 삭제 |
| D2 | 1083 허용 목록 = 1160만(선언 + 런타임 가드 + 시험) |
| D3 | explicit 1165 → SC1\|N_SC101 |
| D4 | NA-9 1162:1, 1164:1, 1165:1 추가(열거 편집) |
| D5 | U1 area 계약 옛 사본은 그대로 두고 기록만(`make_config_n31.py` 주석, 이 보고) |
| D6 | 새 파일 `*_v3c1_*`, v3b 파일은 트리에서 삭제. 시나리오 선언 이름(`<stem>_<sha6>`)은 그대로 |
| D7 | L1은 이월 사전값. reference note와 plant QUALIFICATION에 자격을 적음 |

---

## 4. 커밋할 파일

**git rm (13개, 이미 작업 트리에서 지움)**
```
diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3bnc.inpx
diagnostics/sdmpc_n31_20260924/beta/approach_entry_v3b2_20260925.json
diagnostics/sdmpc_n31_20260924/beta/explicit_approach_v3b_20260925.json
diagnostics/sdmpc_n31_20260924/beta/movement_beta_routing_v3b_20260925.json
diagnostics/sdmpc_n31_20260924/beta/movement_beta_routing_v3b2_20260925.json
diagnostics/sdmpc_n31_20260924/urban/control_area_route_contract_v3b_20260926.json
diagnostics/sdmpc_n31_20260924/urban/control_area_route_contract_v3b_20260926.provenance.json
diagnostics/sdmpc_n31_20260924/urban/movement_nonexistent_v3b_20260926.json
diagnostics/sdmpc_n31_20260924/urban/offramp_static_route_prior_v3b_20260925.json
diagnostics/sdmpc_n31_20260924/urban/physical_phase_authority_v3b_20260926.json
diagnostics/sdmpc_n31_20260924/urban/route_queue_attribution_v3b_20260925.json
diagnostics/sdmpc_n31_20260924/urban/unsignalized_turns_v3b_20260925.json
diagnostics/sdmpc_n31_20260924/urban/unsignalized_validation_v3bnc_20260925.json
```
**git add**: 수정 66개와 새 파일 32개(이 보고 포함), 모두 98개입니다. 전체 목록은 워크플로 반환값 `files_add`에 있습니다. 경로를 하나씩 명시하고, `--renormalize`는 쓰지 않습니다.

---

## 5. R-obs 발사 절차 (메인 세션, 커밋 뒤)

1. 커밋: `D:\VISSIM-merge\sim3-n31-v3c1`, 브랜치 `claude/repin-v3c1-20260928`.
2. 런 루트 만들기(PowerShell): `New-Item -ItemType Directory -Force D:\VISSIM_runs\20260928_sdmpc31_v3c1 | Out-Null`
3. 동결과 사전점검을 한 번에 합니다. `-Freeze`가 `freeze_worktree.ps1`을 부르고 로그에 `FRZ=`를 찍습니다. VISSIM과 좌석은 쓰지 않습니다.
   ```powershell
   Set-Location D:\VISSIM-merge\sim3-n31-v3c1
   powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly `
     -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c1_nc_s31 -SimPeriod 9000 -Seed 31 `
     -Controller no-control -RunsRoot D:\VISSIM_runs\20260928_sdmpc31_v3c1
   ```
   - 합격 기준: `FREEZE FREEZE_VERIFIED … head=<새 커밋>`, `LAUNCH_PLAN_DETAIL … network_sha=2577209b detectors=294 controller=no-control`, `NETCOPY NETWORK_COPY_OK … sha256=2577209b… sig=42`, `PREFLIGHT PROVENANCE_OK`, `EXIT … code=0`.
   - 사전점검은 `<RunsRoot>\_preflight\<Name>_<stamp>`를 쓰므로 같은 Name으로 본 발사가 가능합니다(`launch_plan.py:9-11`).
   - 동결을 따로 하려면 `freeze_worktree.ps1 -Source D:\VISSIM-merge\sim3-n31-v3c1`로 FRZ를 만든 뒤, FRZ 안에서 `-Freeze` 없이 `-PreflightOnly`로 돌립니다. FRZ 안에서 `-Freeze`를 주면 code 2로 거부됩니다.
4. 본 발사는 WMI로, 세션과 분리해서 합니다. 3의 `FRZ=` 경로를 넣습니다. v3b R-obs-b(`sdmpc31_v3b_nc_s31b`)와 같은 형태입니다.
   ```powershell
   $frz = 'D:\VISSIM-merge\frozen\sdmpc31_<head8>_<yyyyMMddHHmm>'
   $log = 'D:\VISSIM_runs\20260928_sdmpc31_v3c1\wmi_sdmpc31_v3c1_nc_s31.log'
   $cmd = 'cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 ' +
          '-Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c1_nc_s31 -SimPeriod 9000 -Seed 31 ' +
          '-Controller no-control -RunsRoot D:\VISSIM_runs\20260928_sdmpc31_v3c1 > ' + $log + ' 2>&1'
   Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd; CurrentDirectory = $frz}
   ```
   - PID와 명령을 `D:\VISSIM_runs\20260928_sdmpc31_v3c1\wmi_launch_lines.txt`에 v3b 형식대로 적습니다.
5. **좌석**: 이 발사기는 VISSIM이 3대 이하이고 dev VISSIM(창 제목 `obs150|sdmpc|probe`)이 없을 때만 띄웁니다(`run_sdmpc_n31.ps1:84-86`). `-AllowConcurrentDev`면 2대 이하와 dev 1대 이하입니다.
   - 이 보고를 쓰는 시점에 VISSIM 4대(N1 B5)가 돌고 있습니다 [실행 Get-Process]. 그대로 발사하면 code 5(NO_SEAT)로 멈춥니다.
   - 좌석이 빌 때까지 기다리거나 `-WaitSeatMinutes <분>`을 더합니다. 다른 SDMPC dev 런과 함께 돌릴 때만 `-AllowConcurrentDev`를 씁니다(v3b R-obs-b는 S0b 옆이라 썼습니다).
6. 감시: `run_provenance_*.json`, `launch_sdmpc31_v3c1_nc_s31.log`의 `EXIT` 줄, 워치독 진행 파일. 5분 동안 진행이 없으면 memory `vissim-watchdog-policy`를 따릅니다.
7. R-obs 뒤(P10)
   - §5.5 4: T5 `N31_G1_STATE=…\decisions_sdmpc31_v3c1_nc_s31\state_000900.json`, 결정 재생 `REPLAY_COMPARE verdict=IDENTICAL`.
   - §5.5 1의 L0/L1 all-110 런 상태 대조.
   - U1 T1 재판정(RA-6).

---

## 6. 남은 위험과 열린 문제

- **런타임 최종 확인은 R-obs t=1입니다.** configure-check는 fcb donor 상태를 v3c1로 다시 가리킨 것이라 실제 v3c1 스냅숏과 다릅니다. 계획 §9 "훑은 것보다 많은 검증기"의 위험이 남습니다 [추론].
- **재생 action_contract**(`tools/make_replay_state_v2.py:234-242`): `--tuning`이 있으면 모든 VSL이 max(vsl_set) = 110이어야 합니다. SDMPC가 80–100을 고르면 실패합니다. v3c1 전부터(50..110) 있던 문제이고, R-obs(no-control)에는 영향이 없습니다. T5를 SDMPC 런에 쓸 때 "허용 집합 소속" 검사로 바꿔야 합니다(가이드 :526 기존 서술) [읽음].
- **s31 추출의 미설명 손실 1대**(차량 34211): 영수증에 적었습니다. 램프 행과 기하에는 영향이 없습니다 [실행·추론].
- **DA-3 검증 수치 변경**: 판정은 같지만 표 sha는 바뀌었습니다. U3를 쓰는 후보의 T3 재측정은 R-obs 뒤입니다.
- **RA-7**(fit5 stats6·RM 관측)과 **RA-6**(U1 T1)은 하지 않았습니다. R-obs에는 필요 없습니다.
- 묶음 2 워크플로(`sim3-n31-urban-b2`)는 v3b 핀 트리에서 돕니다. 이 브랜치로 옮길 때 β 원천 키 이름이 바뀐 것(`routing_v3b2` → `routing_v3c1_2`)을 반영해야 합니다 [추론].

## 7. 하지 않은 것
- 커밋, 푸시, 동결, 발사, VISSIM/cscript/fast_nc_run, watchdog·ps1 시험.
- `frozen/*`, `sim3-n31`, `sim3-n31-urban`, `sim3-n31-urban-b2`, `D:/VISSIM_runs/*`는 쓰지 않았습니다(읽기만 함).
- s37 FZP와 산출은 어떤 유도에도 쓰지 않았고 열지도 않았습니다.
