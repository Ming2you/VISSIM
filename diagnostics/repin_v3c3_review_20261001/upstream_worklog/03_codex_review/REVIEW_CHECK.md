# REVIEW_CHECK: `REVIEW.md`(7ecace62 검토) 반박 점검

작성 2026-09-30. 읽기 전용입니다. VISSIM·재생·git checkout은 하지 않았고, 새 파일은 이 폴더(`REVIEW_CHECK.md`, `chk/`)에만 썼습니다.
태그: [실행] 이번에 명령·계산으로 확인 / [읽음] 파일·코드에서 확인 / [추론] 시험하지 않은 해석.
재현: `chk/check_numbers.py` → `chk/check_numbers.json`(숫자 전부), `chk/inputs.py`·`chk/dsd.py`(두 .inpx 파싱), `chk/L.py`(긴 경로 로더).
약어: CAL = `codex7ec/diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration`, V3C1 = `D:/VISSIM-merge/sim3-n31-v3c1`(HEAD 9ed2ef0), B2 = `D:/VISSIM-merge/sim3-n31-urban-b2`.

## 0. 판정

- **권장 결론은 유지됩니다.** 값은 얹지 않고, 우리 순서(도시 묶음 2 → v3c1 재핀 + L2 → F1+F8 → F2+F3 → F4)를 지키고, 점검 항목과 프로토콜만 들이는 것이 맞습니다. 반박을 시도한 22개 주장 가운데 결론을 뒤집는 것은 없었습니다.
- **다만 근거 네 곳은 고쳐야 합니다.**
  1. "잠복 결함 #3(경로 재고 초기화 생략)"은 우리 트리에서는 결함이 아닙니다.
  2. "계수 지도가 우리 진단을 독립적으로 재발견했다"는 과장입니다. 대표 사례(셀 12 ρc ×0.6, 셀 23 ν_lt /16)는 159계수 적합 전에 사람이 넣은 초기값입니다.
  3. VSL 법칙의 "N1 모순"은 c80에서만 성립하는 정도 차이입니다. 우리 L1·L2도 같은 c80 신뢰구간 밖에 있습니다.
  4. "0.007 대 0.751 → F4 필요"는 3계수 국소 민감도를 전체로 일반화한 것입니다.
- **REVIEW가 놓친 위험 세 가지가 있습니다.**
  1. 6구역 VSL은 그쪽 미커밋 `physical_vsl_sign_binding`에 숨은 의존이 있습니다. 없으면 plant와 VISSIM이 DSD63–66에 서로 다른 명령을 씁니다.
  2. 우리 배포 head-service 표 자체가 10490 {2 = 3} 비유일입니다. 같은 부류의 실제 잠복 결함입니다.
  3. 64cf-s61/s67이 우리 봉인 s61/s67과 독립이라고 단정할 수 없습니다.
- **쉽게 만드는 요소도 둘 있습니다.** 우리 CONTRACT와 이식 안내서가 이미 "옮기지 않음"과 "조용한 무시 검사"를 정해 두었습니다.

---

## 1. 확인 (재검증 통과)

| # | REVIEW 주장 | 재검증 | 결과 |
|---|---|---|---|
| C1 | trust015에서 122/159가 SPSA 반응점 대비 ±0.15 부호 스텝 | `jacobian_step/selection.json` `relative_values` − `selected_coefficients.json`(mode=response) `relative_change` | +0.15가 61개, −0.15가 61개 [실행]. 추가로 확인: expanded036은 trust015에서 거의 안 움직였습니다(중앙값 0.64 %, 5 % 넘는 것 15/159) [실행]. 경로 흔적이 그대로 이어집니다. |
| C2 | seed43 순위 쌍 불일치 1/6 → 2/6, 후회 0.094 | `CAL/coupled_expanded_joint/comparison.json` `seed43.rank` = actual [rm, both, held, vsl], before [rm, held, both, vsl], after [both, rm, vsl, held]; README 표 | 맞습니다 [실행]. 기존 계수는 최선(RM)을 골랐고, expanded036은 결합을 골랐습니다(차 0.093750, `coupled_expanded_joint/README.md`) [읽음]. |
| C3 | κ = 5(31셀 전부), VSL carlson A0.5/E2.0/α0, sign_cells [0,3,5,8,14,16,26,28], vsl_set 50..110 | `effective_parameters.json` `FW_E.segment_params[*].metanet_kappa_veh_km_lane`, `eval_036/reference_config.json` `freeway.vsl_fd_response`·`component_vsl_transport`·`config_overrides.freeway_follower.vsl_set` | 맞습니다 [실행]. 우리는 sign 18, L1 0.94/1.44, 80..110입니다(`V3C1/diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json`) [실행]. |
| C4 | 우리 기준 FW_E τ 12, ν 38.7, κ 17, δ 1.0, ρc ×1.4 / FW_W v ×1.12, ρc ×0.68, δ 0 | `…/res10_b110_20260923/train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json` | 맞습니다 [실행]. 그쪽 FW_W도 ρc ×0.68입니다(셀 0 ρc 19.04 = 28 × 0.68). 방향 배율은 두 줄기가 같고, κ·ν만 다릅니다 [실행]. |
| C5 | 31셀 분할 비트 동일, 합류 셀 10/12/21/23, 진출 셀 9/11/18/20 | effective `segment_length_km` 대 v3c1 `geometry.json` `cells[*].length_km`; `boundaries` | 양방향 62셀 max\|ΔL\| = 0 [실행]. 합류 to_cell 10/12/21/23, 진출 from_cell 9/11/18/20 [실행]. (R3 표의 "셀 8 = 10643 분기"는 틀렸고, 10643은 셀 9입니다. REVIEW 본문은 맞습니다.) |
| C6 | state_response 셀 인덱스 검증이 21셀 분할 전에 돎 | `canonical_harness.py:301` → `runtime_setup.py:59` → `freeway_fd.py:289, 330`, 분할은 `canonical_harness.py:302-317` | 맞습니다 [읽음]. 그쪽 31개 override(0..30)는 21에서 거부됩니다. 그쪽 `SELECTION.md` 1번도 같은 오류를 적었습니다 [읽음]. 우리 reference에는 `state_response`가 없어서 지금은 영향이 없습니다 [실행]. |
| C7 | Carlson 용량 배수 (a = 2) | `freeway_fd.py:39-46` 식으로 재계산 | 그쪽 −0.91/−3.61/−8.01 %, L1 +0.59/−0.58/−3.60 %, L0 +5.79/+6.48/+3.50 % (100/90/80) [실행]. |
| C8 | `physical_cell_fd` 저장값 × 1.4 = 실효값. CSV·MD 표는 실효값 | 31셀 비 effective/stored | 정확히 {1.4} [실행]. `EXPANDED036_PARAMETERS.md`의 ρcrit를 설정에 그대로 넣으면 1.4가 두 번 곱해집니다(×1.96). REVIEW #11의 "저장값 × 배율 1회" 규칙이 맞습니다. |
| C9 | 램프 도착 예측이 옛 4그룹 키이고 strict 없음 | `candidate_config.json` `calibration_override.prediction.local_ramp_arrival_forecast` | R_D_W/R_F_W/R_D_E/R_F_E이고 strict 없음. 우리는 RM_C 8키 + `strict_ramp_keys: true` [실행]. |
| C10 | 핀 9개 중 7개가 우리 트리에 없음, 핵심 코드 sha 불일치 | `candidate_manifest.json` `sources` 경로 존재 검사, `protocol.json` `core_sha256` 대 `git show {886a014,HEAD}` LF/CRLF | 7/9 부재 [실행]. freeway_fd `ca1a68a4`, runtime_setup `1d1d9568`은 불일치합니다. lane_freeway_runtime `1707e476`은 우리 CRLF와 일치합니다 [실행]. |
| C11 | 망 차이: DSD63–66 link 2 pos 3607.216 / 3998.666, DSD110 75–145 / 98–140, 입력 1098 부피 동일 | 두 .inpx 파싱(`chk/dsd.py`, `chk/inputs.py`). sha 64cf5f55 / 2577209b 확인 | 맞습니다 [실행]. |
| C12 | 최종 상태 `OFFLINE_CHECK_COMPLETE_NOT_GAIN_QUALIFIED`, production_adopted false, 블라인드 없음 | `final_verification.json`, `expanded_joint/README.md`("이미 열람한 자료이므로 blind holdout이 아니다") | 맞습니다 [실행·읽음]. |
| C13 | FD 용량·평형속도: 셀 12 6,394, V(55) 1.8 km/h / 셀 24 5,022 (그쪽 실측 통과 6,816–6,876) | effective 값으로 λρc v_f e^(−1/a) | 6,394 / 1.83 / 5,022 [실행]. 실측 통과량은 `freeway_first/connected_fd/README.md`의 값입니다 [읽음]. |
| C14 | δ 실효 합류 항 ×2.7–7.5, 필요 δ 약 2.4–3.0 | δ·(ρ+17)/(ρ+5), ρ 20–45; P0-7 세 점 외삽(`02_fwe/P0_REPORT.md:316-317`) | 비 ×2.74–7.53 [실행]. 필요 δ는 셀 12 2.36–2.46, 셀 21 2.97–3.11입니다(기울기를 0–1로 잡느냐 0.65–1로 잡느냐의 차이) [실행]. |
| C15 | F 번호 정정(F4 = B1 병목 노드, F8 = 차로수 정수화) | `02_fwe/FWE_STRUCT_PROPOSAL.md:97, 101` | 맞습니다 [읽음]. 과제 문구의 번호가 틀렸습니다. |
| C16 | seed43 상태 손실 악화 +2.9/+8.1/+10.3 % | `CAL/jacobian_step/summary.json` `check.state` 0.6347 대 `CAL/summary.json` `baseline_check.state` 0.5757 | +10.25 % [실행]. 이 세 값은 SPSA 두 개와 trust015의 값입니다. expanded036은 확인 집합이 6개라 같은 기준으로 비교할 수 없습니다(`expanded_joint/summary.json` `check_loss.state` 0.756) [실행]. "159차원 단계 모두"는 이 세 단계라는 뜻으로 읽어야 합니다. |
| C17 | U6 `REFUSED_KEYS`는 그쪽 도시 키를 모른다, B2는 필수 키 3개 | `B2/evaluation/controllers/ramp_diverge.py:60`, `vissim_stackelberg_adapter.py:3424` | 맞습니다 [읽음]. |

## 2. 정정

| # | REVIEW 위치 | 주장 | 정정 | 근거 |
|---|---|---|---|---|
| K1 | 요약 3·§2 #3·§4.2 | "배포 v2가 경로 재고 초기화를 건너뜀 → 우리 코드에 있는 잠복 결함. 하네스와 배포의 진출 분기 모형이 다르다" | **우리 트리에서는 결함도, 하네스·배포 불일치도 아닙니다.** 우리 SDMPC 튜닝에는 `freeway.offramp_route_inventory`가 아예 없어서 `configure_inventory`는 어느 경로에서든 `{}`를 돌려줍니다. 우리 component는 `_config`에서 상속된 재고를 명시적으로 거부하고(`canonical_harness.py:632-633`), rollout은 `off_split_ratio` 경계를 씁니다. 그래서 하네스와 배포가 모두 β 분할이고 서로 일치합니다. 불일치는 그쪽 **미커밋** 하네스(`rollout(..., offramp_inventory=...)`)에서만 생깁니다. #3은 "경로 재고(#16)를 들일 때의 선행 조건(D)"으로 내리고, §4.2의 "잠복 결함 두 건"에서 뺍니다. | `runtime_setup.py:211-217`, `offramp_routing.py:292-295`, `config_n31_v2.json` `freeway.offramp_route_inventory` = None [실행], `canonical_harness.py:632-633, 636-650` [읽음] |
| K2 | 요약 1·§0·§1 | FW_W 수요 "2.06–2.26배 / 2.1–2.3배" | **1.84–2.27배**입니다. 구간별로 2.063/2.263/2.218/2.193/**2.274**/**1.837**이고, 마지막 구간(4500 s–끝, 런의 절반)이 1.84배입니다. 결론은 바뀌지 않습니다. | `chk/inputs.py` 1099 `timeIntervalVehVolume` [실행] |
| K3 | 요약 4·§2 #5·§3(1)·§4.1 셋째 항 | "계수가 크게 움직인 셀이 우리 진단 셀과 겹친다 = 독립 방증" | **셀 12 ρc 21.0과 셀 23 ν_lt 4.59는 적합 전 초기값입니다**(CSV `initial`: 12 rho_crit 21.0 → 20.954, −0.2 %. 23 nu_lt 4.594 → 4.645, +1.1 %). 셀 10·21 ρc ×1.2와 δ 4/4/4/2도 적합 전 사람이 넣은 국소 보정(`local_merge_cell23`)입니다. 159계수 적합 자체가 움직인 양(그쪽 초기값 대비 평균 \|상대변화\|)은 우리 핵심 진단 셀 {12, 13, 18, 23, 24}가 0.124로, 진단 밖 셀 0.143보다 **작습니다**. 가장 많이 움직인 셀은 25, 27, 11, 21, 22, 26, 24, 1 순이고 회복·말단 쪽에 몰려 있습니다. 게다가 적합은 셀 12 ν_lt를 **+25 % 올렸습니다**(머리 셀 과속을 키우는 방향). 따라서 방증은 "옵티마이저가 같은 셀을 찾았다"가 아니라 **"그쪽 사람이 12/21/23을 국소 보정 대상으로 골랐다"(질적 방증)**와 그쪽 감사 문장(셀 21 과감속, 셀 24 FD < 통과량, 셀 19 VSL 통과 +59.9 대 실측 +6)으로 한정합니다. 적합이 직접 만든 보상은 셀 18(a +25 %), 셀 24(ρc −21 %, a −16 %), 셀 13(τ +33 %)입니다. 셀 12의 V(55) 1.8은 초기값만으로도 3.8 km/h입니다. | `expanded036_parameters.csv`, `chk/check_numbers.json` `mean_abs_rel_*`, `top8_cells_by_mean_abs_rel`, `V55_cell12_prior_a2` [실행]. R3 §2 전제 문단 [읽음] |
| K4 | §2 #9·§3(3)·요약 1 | "A0.5/E2.0은 L0의 거울상, N1과 모순, 우리 L1은 최대 +2.7" | **c80에서만 신뢰구간 밖**입니다(B2 z = 5.14). c100 z 0.07, c90 z 1.76은 N1 90 % CI(t₃ = 2.35) 안이고, 그쪽 SDMPC가 실제로 고른 명령은 90이었습니다. 우리 **L1도 c80 B2 z = 2.70**(−2.92 % < CI 하한 −2.56 %)이고, 다음 핀 **L2는 z = 3.79**로 역시 CI 밖입니다. 따라서 "그쪽은 모순, 우리는 적합"이 아니라 **c80 비관의 정도 차이**(5.1 대 3.8 대 2.7)입니다. L2를 고른 근거는 N1F 단일값 LOSO+LOLO이지 이 표가 아닙니다. L0는 세 수준 모두 z −6.3 ~ −8.2였으므로 "거울상"이라는 말도 c80에만 맞습니다. 결론(그쪽 법칙 불채택)은 그대로이고, 근거 문장만 약하게 고칩니다. | SE 0.98은 `04_vsl/N1_RESULTS.md:94`, t₃ = 2.353은 `:15`. `chk/check_numbers.json` `z_B2_*` [실행]. 혼합 예측값은 R3 표 인용(재계산 안 함) |
| K5 | §2 #20·§4.1 둘째 항·요약 4 | "계수를 ±25 % 움직여도 초기 RM 반응 0.007(필요 0.751) → 구조(F4)가 필요" | 0.007은 **3계수**(δ21·τ24/25·ν_lt24/25)의 국소 접선입니다. 159계수 전체의 근거는 `jacobian_step/RESULT.md` "±30 % 전부 유리하게 선택해도 −0.103 ~ +0.032 대 실측 −0.825"이므로 이것을 인용해야 합니다. 또 그 라벨(seed29 초기 RM)은 실제 합류 변화가 **−3대**(10639 0, 10681 −1, 10490 −3, 10484 +1)인데 방출이 +22대라서, 그쪽도 새 차량의 목적지 구성과 무작위 차이가 섞였다고 적었습니다. 그러니 이 사례는 "계수로는 안 된다"와 "라벨이 잡음일 수 있다"를 뒷받침할 뿐, **F4(B1 방류 법칙)를 특정해 지지하지는 않습니다**. REVIEW #22의 "분기 잡음 바닥 미측정"과도 일관되게 고칩니다. | `regional_joint/FLOW_RESPONSE_REVIEW.md` 끝 절, `jacobian_step/RESULT.md` "RM 반응의 분해" [읽음] |
| K6 | §2 #16 | "실측 +9.467, 고정 β+storage +8.284, 경로 재고+storage +8.502, 경로 재고+proxy는 +0.858로 악화" | **+0.858은 다른 지표**(본선+8커넥터, 실측 +4.704)입니다. 같은 "본선" 지표로는 경로 재고+proxy가 **+6.364**이고, 고정 β+proxy는 +7.744입니다. "storage 몫이 크고 경로 재고 몫은 작다"는 해석은 유지됩니다(고정 β에서 proxy → storage가 +0.54, storage에서 β → 경로 재고가 +0.22, proxy에서는 경로 재고가 −1.38). | `freeway_first/route_inventory/README.md` 결과 표·첫 글머리 [읽음] |
| K7 | §2 #15 | "1800 veh/h/차로는 우리 `gate_onramp_queue_capacity_veh_h` 1800과 같다" | 단위가 다릅니다. 그쪽은 `…_per_lane_…`(차로당)이고, 우리 키는 movement 하나의 용량으로 설치됩니다(`capmap[name] = conn_cap`). 차로당 1800이라는 뜻에 맞는 우리 쪽 상대는 U6 A1입니다. | `B2/…/vissim_stackelberg_adapter.py:3424, 3442` [읽음] |
| K8 | §2 #17 | "FW_E 입력 1098은 두 망이 같습니다" | **부피만 같습니다.** 차량 구성이 64cf 14(Freeway entry DSD110, 75–145) 대 v3c1 1(Default, 이후 11–40 m DSD가 110 설정)로 다릅니다. 입구 경계 후보가 쓰는 값이 바로 0–40 m 관측 속도이므로, 그쪽 MAE 개선(31.3 → 14.5)이 우리 망에 옮겨진다는 근거가 되지 못합니다. 단계 2a(우리 fit 시드로 먼저 측정)의 필요성이 오히려 커집니다. | `chk/inputs.py` `vehComp` 14 대 1 [실행] |

## 3. 누락 — 얹기를 더 위험하게 만드는 것

**M1. 6구역 VSL(S13 독립)에는 그쪽 미커밋 `physical_vsl_sign_binding`에 숨은 의존이 있습니다** [읽음·추론]
- 매핑은 DSD63–66을 `model_segment_index` 13에 묶습니다(`evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json:907, 927`). 그래서 VISSIM에는 13번 구간 명령이 나갑니다.
- 그런데 plant에서 이 표지판은 정제 셀 18(우리) 또는 16(그쪽), 즉 **부모 12**에 있습니다. 러너 경계도 부모 12는 6315.46–6841.74 m입니다(`lane_native_b110.vbs:14`).
- plant는 표지판 셀의 명령을 그 셀이 속한 구역 머리로 읽습니다(`canonical_harness.py:316`, `freeway_fd.py:156-157`).
- 우리 머리 [0,5,10,15]에서는 12와 13이 같은 구역이라 문제가 없습니다.
- 그쪽 머리 [0,2,5,10,13,15]에서는 plant가 DSD63–66 코호트를 **구역 10 명령**으로 붙이고, VISSIM은 **구역 13 명령**을 보여 줍니다.
- 그쪽은 `candidate_config.json` `freeway.physical_vsl_sign_binding: true`(미커밋)로 이것을 막는 것으로 보입니다. `SELECTION.md`에 "실제 DSD 위치의 구역 매핑"이라고 적혀 있습니다.
- 그쪽 `_note_zones`는 아직 4구역 설명 그대로라 낡았습니다.
- → REVIEW #10 "D, 보류"는 유지하되, **"sign binding 없이 6구역 금지"**를 §5 "하지 말 것"에 추가해야 합니다.

**M2. 우리 배포 head-service 표 자체가 비유일입니다(10490 {2: 1.0, 3: 1.0})** [실행·읽음]
- `reference_config_n31_v2.json` `freeway.physical_ramp_head_service_veh_per_cycle`의 값입니다.
- 이 표는 `lane_plant_runtime.py:484`에서 디코드 표 `service_by_green_veh_h`를 통째로 덮습니다.
- 서비스 360 veh/h가 들어오면 `physical_ramp_branches.py:360`에서 멈춥니다. 09-29 혼합 런이 멈춘 원인이 이것입니다.
- 이 문제의 수정(92fa4b8)은 혼합 브랜치의 혼합 키 아래에만 있습니다(메모리).
- → REVIEW가 그쪽 9 = 10 표를 거절하는 근거로 쓴 결함이 **우리 v3c1 SDMPC 경로에도 잠복**해 있습니다. K1에서 뺀 #3 대신 이것을 "우리 코드의 잠복 결함"에 넣고, "서비스값 유일성" 정적 관문을 우리 표에도 적용하도록 권장합니다.

**M3. 64cf-s61/s67이 우리 봉인 s61/s67과 독립이라고 단정할 수 없습니다** [추론, 미검증]
- 메모리에 따르면 같은 시드의 v3b와 v3c1은 FW_E 진입을 900 s까지 공유했습니다.
- 64cf와 v3c1은 입력 1098의 부피·시간 구간이 같습니다. 구성(14 대 1)이 난수 소비를 바꾸는지는 확인하지 않았습니다.
- REVIEW §8의 "다른 자료"는 너무 강합니다. 그쪽 s61/s67 수치(connected_fd의 seed61 4조건, merge_speed_audit의 seed67)는 **우리 선택·보정 결정에 쓰지 않는다**를 규칙으로 두는 편이 안전합니다.
- 이 점검에서 s61_late README와 우리 봉인 자료는 열지 않았습니다. `connected_fd/README.md`에 seed61 결과 표가 있다는 것은 읽었습니다(⚑ 64cf 자료).

**M4. 그쪽 셀 0–1 계수는 입구 가상 상류 속도 120을 전제로 적합됐습니다** [읽음·추론]
- 그쪽 `config_overrides.network.v_free`는 120, 우리는 110입니다.
- AFA는 셀 0 상류 속도로 `net.v_free`를 씁니다(`area_freeway_accounting.py:365`). 셀 0의 v_free 자체는 두 줄기 모두 85.97입니다.
- 그쪽 입구 경계 문서도 "기존 가상 상류 속도는 120"이라고 적었습니다.
- 셀별 값을 옮기면 입구 조건이 달라져 셀 0–1의 τ/ν가 뜻을 잃습니다. 불채택 근거가 하나 더 생깁니다.

**M5. 경로 재고 교훈("합류 차량을 지난 출구에 재배정 금지")은 정적 경로에 의존합니다** [읽음·추론]
- 64cf와 v3b/v3c1은 고속도로 관련 정적 경로 편집 5건(1131·1132·1136·1133·1140)이 다릅니다(R2 §3).
- 그쪽의 "10639·10681 합류 차량은 10682로 나가지 않는다"를 단계 2c 단위 시험의 기대값으로 쓰기 전에, v3c1 경로에서 같은 사실을 다시 확인해야 합니다.

**M6. 망 수준 `metanet_delta_merge: 0.3`이 두 reference에 다 남아 있습니다** [실행·읽음]
- 우리 쪽은 `config_overrides.network.metanet_delta_merge` 0.3입니다. P0 정정 16이 설정과 문서의 불일치로 이미 기록했습니다.
- 그쪽 셀별 δ(미커밋)가 override 없는 셀에서 방향 δ로 떨어지는지 0.3으로 떨어지는지 알 수 없습니다. 합류는 네 셀에만 있으므로 영향은 작을 것입니다.
- 셀별 δ(#8)를 설계할 때 이 키를 먼저 정리해야 합니다.

## 4. 누락 — 얹기를 더 쉽게, 또는 결정을 더 분명하게 만드는 것

**E1. 우리 문서가 이미 이 결정을 내려 두었습니다** [읽음]
- `diagnostics/sdmpc_n31_20260924/CONTRACT.md:713`: "옮기지 않은 것: parent 14/15의 v_free 108.159, anticipation 18.375, `physical_cell_fd`, 램프 head-service 곡선 … v2 재적합 때 후보로 봅니다."
- REVIEW #4–#6·#13의 C 분류는 새 판단이 아니라 기존 계약을 다시 확인한 것입니다. 이 줄을 인용하면 사용자 결정 1은 "기존 방침 유지 확인"이 됩니다.

**E2. 조용한 무시를 막는 설치 검사도 이미 설계돼 있고, 구현만 안 됐습니다** [읽음]
- `PLANT_PORTING_GUIDE.md:426-428`((d)-3 1)은 `_load_sources_v2`가 reference의 `vsl_fd_response`·`component_vsl_transport`·`physical_cell_fd`·`state_response`가 실제로 설치됐는지 확인하도록 정했습니다.
- 현재 `lane_plant_runtime.py:70-127`에는 이 검사가 없습니다.
- 이것이 REVIEW #11("reader가 없어 조용히 무시")의 실제 우리 쪽 결함입니다. 셀별 키를 처음 들이는 묶음에서 단계 3(인덱스 순서)과 함께 넣으면 됩니다.

**E3. 기술적 이식 폭은 작습니다** [읽음·추론]
- 우리 코드는 이미 다음을 받습니다.
  - 셀 0–20의 relaxation과 anticipation ge/lt(`freeway_fd.py:289-331`; 필드명 `downstream_ge_local`/`downstream_lt_local`도 같고 부호 규약도 같음)
  - 4램프 receiving node, 램프별 head-service, travel speed, Carlson 법칙
- 모자란 것은 세 가지뿐입니다: 인덱스 검증 순서, 셀별 `delta_merge` 필드와 소비자, `physical_cell_fd` 설치기.
- 즉 "못 얹는" 이유는 코드가 아니라 과학적 이유(망·κ·VSL 법칙·구조 보상)입니다. REVIEW 결론과 같은 방향이지만, 사용자에게 "코드 장벽"으로 비치지 않게 적어야 합니다.

**E4. 그쪽 VSL 법칙은 L0에서 스스로 물러난 결과입니다** [읽음]
- 그쪽 09-24 인계 패키지는 A0.5/**E4.0**이었습니다(`git show d80faf9:diagnostics/vsl_handoff_20260924/candidate.json:8128-8134`). 우리가 이식해 N1이 기각한 L0(`886a014` reference, 75f0151 "port the A0.5_E4")가 바로 이것입니다.
- 그쪽은 이후 E2.0으로 바꿨습니다(LINEAGE §1 "과거 커밋명의 A0.5_E4를 현재 계수값으로 대신 사용하지 않는다"). 변경 근거는 커밋에 없습니다.
- 이것은 "E4는 용량을 과대 예측한다"는 N1 결론과 같은 방향의 독립 방증입니다(K4의 "거울상" 표현을 대신할 서술).
- 159계수는 E2.0 아래에서 적합됐으므로 VSL 창 적합이 이 법칙을 전제한다는 REVIEW §3(3)의 지적은 그대로 유효합니다.

## 5. REVIEW 권장안에 대한 수정 제안

1. **요약 3과 §4.2:** "잠복 결함 두 건"을 다음 두 건으로 바꿉니다.
   - (#2) 인덱스 검증 순서
   - (M2) 10490 head-service 비유일
   - (E2) `physical_cell_fd`·`state_response` 설치 검사 부재를 세 번째로 덧붙입니다.
   - #3은 "경로 재고를 들일 때의 선행 조건"으로 내립니다(K1).
2. **요약 1:** FW_W를 "1.84–2.27배"로 고칩니다(K2).
3. **요약 4와 §4.1:** "계수 지도 = 독립 방증"을 "그쪽 국소 보정 대상 선택(12/21/23)과 감사 문장 = 질적 방증"으로 낮춥니다. 적합이 직접 만든 보상은 셀 18·24·13으로 한정합니다(K3). "0.007 대 0.751 → F4"는 "159열 선형 범위 −0.103 대 −0.825, 라벨은 합류 −3대라 잡음 가능"으로 바꿉니다(K5).
4. **§3(3)과 #9:** "c80에서 그쪽 z 5.1, 우리 L1 2.7, L2 3.8 — 정도 차이. c90은 CI 안"으로 고칩니다. E4 → E2 이력(E4)을 덧붙입니다(K4).
5. **§5 "하지 말 것"에 추가:**
   - sign binding 없이 6구역 VSL 금지(M1)
   - 그쪽 s61/s67 수치를 우리 선택·보정에 쓰지 않기(M3)
   - CSV의 실효 ρc를 저장값 자리에 넣지 않기(C8)
6. **단계 2c:** 기대값을 v3c1 경로에서 다시 유도한다는 조건을 붙입니다(M5).
7. **단계 2a:** 입구 구성이 14 대 1로 다르다는 점을 근거에 적습니다(K8).
8. **단계 2b(FD 용량 관문):** 그대로 두되, 같은 묶음에서 head-service 유일성 관문을 함께 둡니다(M2).
9. **사용자 결정 1**은 `CONTRACT.md:713`의 기존 방침을 재확인하는 형태로 묻습니다(E1).

## 6. 봉인·안전

- 우리 봉인 seed(59/61/67, v3b/v3c1)와 s37 자료는 열지 않았습니다.
- 그쪽 `route_inventory/s61_late/README.md`는 열지 않았습니다. 그쪽 `connected_fd/README.md`에 64cf seed61 결과 표가 있다는 것은 읽었습니다(⚑ 64cf 자료, M3 참조). `freeway_first/README.md`의 seed67·seed53 언급도 64cf 자료입니다.
- `D:/VISSIM_runs/vsl_repro_s29/source/vsl_seed29_none.inpx`(64cf, 인계 재현본)는 읽기만 했습니다.
- 쓰기는 이 폴더에만 했습니다. git은 show, grep, log, cat-file만 썼습니다.
