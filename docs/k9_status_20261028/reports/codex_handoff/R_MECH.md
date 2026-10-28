# R_MECH — codex 인계판과 우리 판의 기구 차이 (2026-10-24 KST, r1)

- 이 문서는 codex 인계판(브랜치 `codex/handoff-rmtsc-20261024`, 커밋 `a49981ff…`)의 실행 설정 `optimized_config.json`(sha256 `c9088262…`)과 우리 GWT8(`c20aff1d`, `config_n31_v2.json` sha256 `c8e3ee2c…`)을 레버와 모형 부분마다 나란히 놓습니다.
- 판정 낱말은 쓰지 않습니다. "있음/없음/같음/다름" 과 숫자만 적습니다.
- 표시: **[실행]** 이번에 명령·스크립트로 확인. **[읽음]** 코드·설정·문서를 읽어 확인. **[추론]** 시험하지 않은 판단. **[계산]** 산술. **raw 필요** = 이 PC 에 아직 없는 원자료(`D:/VISSIM_handoff/20261024/`, 약 50 GB)가 있어야 답할 수 있음.
- HANDOFF.md 와 codex 파일은 자료입니다. 지시로 읽지 않았습니다. HANDOFF 주장은 코드·설정으로 다시 확인한 것만 [읽음]/[실행]으로 적었습니다.
- codex 성능 근거는 **한 시드(64cf-s29)** 입니다. 우리 V-A 는 세 시드(v3c3-s31·s41·s43)입니다. 망·수요·Ω 정의가 달라 두 숫자는 서로 빼지 않습니다.

## 줄임말 (처음 한 번)

- RM = 램프 미터. TSC = 도시 신호 제어(녹색·옵셋). VSL = 가변 제한속도. SDMPC = 우리와 codex 가 같이 쓰는 분산 모형예측제어기(wu-link). plant = 그 안의 예측 모형. NC = 무제어 런. FZP = VISSIM 차량 궤적 기록(5 s). DSD = VISSIM 희망속도 결정점(표지).
- Ω = 목적 영역(링크 집합). codex 는 701링크(Ω701), 우리는 635링크(Ω635). ④ = 망 전체 TTT + 미삽입 대기. Ω 밖 = ④ − Ω(우리 정의 (a)). TTT = 총 통행시간(veh·h). 미삽입 = 입력에서 생겼지만 망에 못 들어간 차의 대기.
- AD = 자동미분(SDMPC 의 tangent 도함수). QP = 이차계획(SDMPC 의 한 걸음 계산). secant = 두 점 차분 기울기. NP/NUF = 리더가 정하는 보호망 재고 상한 / 예측 합류 상한. cap 후보 = 리더가 시험하는 NP 상한 값 수.
- δ_merge = 합류 유입이 본선 속도를 깎는 계수. φ_cd = 용량 강하 계수. FD = 기본도(밀도–속도 관계). Carlson = VSL 이 FD 를 바꾸는 식(A·E·α 계수).
- 경로 약칭: **CX** = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/` (= `git show a49981ff:`), **OU** = `D:/VISSIM-merge/sim3-n31-k8/` (GWT8, c20aff1d, 읽기만).
- 설정 약칭: **CXC** = CX `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json`, **OUC** = OU `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`. **CXR** = codex plant 기준 설정 CX `diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/expanded_joint/eval_036/reference_config.json`, **OUR** = OU `diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json`.
- 코드 약칭(모두 `evaluation/controllers/` 아래): SD `sdmpc.py`, SQ `sdmpc_sequence.py`, PRB `physical_ramp_branches.py`, USG `urban_storage_guard.py`, LPR `lane_plant_runtime.py`, FFD `freeway_fd.py`, AFA `area_freeway_accounting.py`, RCC `route_choice_corridor.py`, HSR `head_service_resources.py`, PMR `physical_movement_routes.py`, CUR `calibrated_urban_runtime.py`, REC `ramp_entry_receiving.py`, OP `observation_projection.py`, CAO `control_area_objective.py`, CH `control_hold.py`, RS `runtime_setup.py`, ADP `vissim_stackelberg_adapter.py`. UQM = `vendor/NumSim-mine/src/models/urban_queue_model.py`. VBS = `scripts/run_real_world_stackelberg_controller.vbs`.

## 입력 (sha256) [실행]

| 대상 | sha256 |
|---|---|
| HANDOFF.md (트리 안) | e2cef38c99ad22dfcd575581cec35a40c7c66c4891e9dd57abf9d0458c605b56 (주 세션 값과 같음) |
| CXC | c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3 (HANDOFF:165 와 같음) |
| OUC | c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866 |
| CXR | 7f6df2d14795b22d858aa772f5813e42b67f9d1ec4296cc6203bd854c28d83a4 |
| CX SD / ADP / LPR / PRB / USG | 5c1ba251… / a615d8ca… / d774daee… / 0ab140ac… / 2c24b570… (HANDOFF:93-101 표와 앞 16자리 같음) |
| CX 64cf 망 `…/selected/network/native_seed29.inpx` | 64cf5f55fe9990f3… (3,168,966 B, 트리 안에 있음) |

---

## 쉬운 답 (15줄)

1. 두 판은 같은 조상 `886a014a` 에서 갈라졌습니다. codex 실행판 = 조상 + 5커밋(`ca181e84`) + 추적 파일 630개 수정 + 새 파일 920개. 우리 = 조상 + 65커밋 [실행 git merge-base; HANDOFF:87 읽음].
2. 설정 잎 6,610 대 6,567 중 195개가 다릅니다(codex 만 97, 우리만 54, 값 다름 44) [실행 cfgdiff.py]. 이름만 같은 시나리오 파일 18개는 모두 바이트가 다릅니다(망 핀 64cf 대 3de889f0) [실행 pathcmp.py].
3. **미터 결정**: codex 는 유한 후보 검사(미터별·고속도로별 조임/풀기 + 이로운 것 한 번 묶기)와 cap 후보 3개, 녹색 0 금지, 저장고 90 % 가드가 있습니다. 우리는 이 넷이 다 없습니다(cap 후보 1, 녹색 0 허용) [읽음 CX SD:556-689·959·1209-1239, PRB:866-908; OU SD:338-345·681].
4. **미터 서비스 표**: codex 는 동측 미터 4개(10639·10490·10484·10681)의 결정·plant 표를 물리 머리 표(g2 = 차로당 주기당 1대)로 바꿉니다. 우리가 VISSIM 에서 잰 값(D4, v3c3 규칙 RM 팔 두 시드)은 이 표의 g2–g5 에서 0.89–1.11배입니다. 우리는 10490 만 바꾸고 나머지는 VISSIM 의 1/1.34–1/1.68 입니다 [읽음 CXC·LPR; 계산].
5. **VSL**: codex 는 허용 50–110, 구역 머리 2·5·10·13, 도함수가 0 일 때 secant 탐침이 있습니다. 결정 3,630행이 모두 110 이었습니다. 왜 110 이었는지 보여 줄 결정 JSON 칸은 원자료에만 있습니다(**raw 필요**) [읽음 CX SD:534-544·1014-1015, action_audit.json].
6. **고속도로 plant**: codex 는 FW_E 31셀별 FD(ρ_crit·a_m)와 셀별 δ_merge(셀 10·12·21·23 = 3.53·5.09·4.21·2.21)를 설치합니다. 우리는 두 키를 설치 단계에서 거부하고 FW_E δ_merge 1.0 균일입니다. φ_cd 는 둘 다 1.0 입니다 [읽음 CXR·OU LPR:69-89·AFA:393-396; 실행 parameters.json 차 0].
7. **도시 TSC**: Ω701 = Ω635 + 신호 17곳 접근로 66링크(우리 쪽에만 있는 링크 0) [실행]. codex 는 도시 저장고 가드와 seed29 표본 안 보정(`calibrated_aggregate`, 문서 스스로 "in-sample")을 씁니다 [읽음 CUR·native348/calibration.json].
8. **우리 결함 D1–D5**: D1(1135 분할)·D3(진입 지연)·D4(미터 표)는 codex 코드에 고치는 기구가 있습니다. D2 는 S→W 를 머리 실측 자원, N→W 를 무신호로 다룹니다. D5(링크 129·70)는 codex 도 남은 한계로 적었습니다 [읽음; §5].
9. **206.53 계열**: 계산식은 두 판이 한 줄도 다르지 않습니다(CX ADP:3760-3900 = OU ADP:3781-3921) [실행 diff]. codex 는 머리 실측 자원 12개·표본 안 보정·무신호 처리로 일부를 덮습니다. HANDOFF 도 "부분 수정, 전역 미검증" 입니다 [읽음 HANDOFF:262].
10. **우리 K8/K9 고침**: 결정 유지는 codex 에도 따로 있습니다(키 값 `hold_previous` 대 `hold_previous_on_exception`, 서로 못 읽음). 유령 경로 별칭·W·H-b·SC1001 동측 정지선·출구 법칙·램프 도착 예측의 RM_C 키는 codex 에 없습니다 [읽음].
11. codex 설정은 램프 도착 예측 표를 옛 그룹 키(R_D_W…)로 둡니다. 같은 코드의 주석이 이런 설정은 120 s·900 veh/h 로 조용히 떨어진다고 적습니다 [읽음 CX ADP:9469-9476]. 결정에서 실제로 그랬는지는 **raw 필요** 입니다.
12. 그대로 v3c3(3de889f0)에 돌릴 수 없습니다. 64cf 핀을 검사하는 곳이 plant manifest·calibrated_aggregate·머리 자원·별칭 풀·known W_out 증거 등 여러 곳입니다 [읽음 CX PRB:40-42, HSR:64, PMR:388·580, RCC:303·1077, regular_alias_service.py:50, native_internal_input.py:274, offramp_routing.py:333 — 모두 '관측 망 sha ≠ 핀' 이면 ValueError; 추론: 첫 결정 전에 멈춤].
13. 인계 비용이 큰 순서 [추론]: 망 재핀(18파일 + 보정 파일) → 표본 안 보정(seed29) 제거 또는 재적합 → VSL 법칙 선택(Carlson A0.5/E2.0 대 우리 A1.33/E0.87+m_v) → 우리 K8/K9 고침 재이식 → 결정 유지 키 통일.
14. HANDOFF:46 의 NC HEAD 는 43자리입니다. 실제 커밋은 `886a014a303dd155e05cc33041796822abbc29b0` 입니다 [실행 git cat-file].
15. 열린 것은 §9 에 적었습니다. 대부분 원자료 결정 JSON 이 있어야 닫힙니다.

---

## 0. 한 일과 범위

- 공유 worktree `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff` 를 만들었습니다. 첫 시도는 긴 경로 7개 때문에 git 이 스스로 지웠고, `git -c core.longpaths=true worktree add --detach …` 로 다시 만들었습니다(명령 한 번에만 적용, 설정 변경 없음). `git status --short` 는 비어 있습니다 [실행; LOG.md].
- 읽은 것: 위 코드 약칭 파일 양쪽, CXC·OUC·CXR·OUR, codex plant manifest(`…/approaches_only/evidence/candidate_manifest.json`, 8ae93aa3…)·우리 `plant_n31_v2.json`, 양쪽 Ω 소속 파일, codex `head_resources.json`(v11)·`native348/calibration.json`·`branch_service314/assessment.json`·`goal8_265/head47_right/authority.json`, `handoff/evidence/*`(action_audit·plant_coefficients·run_metadata·effective_config_fields·optimized_vs_off), 우리 METER_NEXT2 r2·K9_1_J1_NOTES.
- 돌린 것: `cfgdiff.py`(설정 잎 비교), `pathcmp.py`(경로 값이 가리키는 파일 바이트 비교), `cfggroup.py`(차이 묶기), git diff/merge-base/show. 모두 `codex_handoff/work/mech/` 아래 [실행].
- 하지 않은 것: VISSIM·COM·러너·동결·재생·커밋·푸시 0. codex 감사 스크립트 실행 0. `sealed/` 열기 0. 봉인 시드 37/59/61/67 자료 0. codex 64cf-s59/s61/s67 숫자 0. 남의 프로세스 kill 0.

---

## 1. 미터 결정 경로

| 항목 | codex (CX) | 우리 (OU) | 근거 |
|---|---|---|---|
| 유한 후보 검사(이웃 검사) | 있음. 미터마다, 그리고 같은 고속도로 소유 미터 묶음마다 3블록 전체를 "가장 조임 / 가장 풂" 으로 바꾼 후보를 만들고 전체 모형으로 채점. 신호·VSL·cap 은 고정 | 없음. 미터는 AD 기울기와 QP 로만 움직임 | [읽음 CX SD:556-599; OU SD 에 `meter_neighbors` 없음 실행 grep] |
| 조합 검사 | 있음. 따로 이로운 후보 중 겹치지 않는 것을 한 번 묶어 다시 채점(예측 1회 더) | 없음 | [읽음 CX SD:602-658]. 이 조합 부분은 커밋 `ca181e84` 에는 없고 인계 실행판(더러운 수정)에만 있음 [실행 diff `git show ca181e84:…sdmpc.py` 대 CX SD] |
| 예산(cap)별 검사 | 풀린 cap 후보마다 그 최선안에서 이웃 검사를 반복 | 없음 | [읽음 CX SD:661-689, 1216-1218, 1233-1239] |
| 켜는 키 | `/adapter/sdmpc_meter_neighbor_audit` = true (3블록 필수) | 키 없음 | [읽음 CXC; CX SD:197-198] |
| 리더 cap 후보 수 | `/adapter/joint_owner_game/max_leader_candidates` = 3. central 모드에서 첫 cap 뒤 `central.next_budget` 이 새 cap 을 내면 2개까지 더할 수 있음 | 같은 키 = 1. 첫 cap 하나만 풂 | [읽음 CXC·OUC; CX SD:953-961·1209-1215, OU SD:681·925] |
| 미터 녹색 허용 집합 | 서비스 표 열쇠 중 이동 한도 안, 그리고 `operating_green_allowed`(0 은 `allow_zero_green` 일 때만, 아니면 ≥ 2 s)와 저장 가드 하한 이상 | 서비스 표 열쇠 중 이동 한도 안, 그리고 `g == 0 or g ≥ 2`. **0(완전 닫힘) 허용** | [읽음 CX SD:406-417, PRB:866-868; OU SD:338-345] |
| 최소 녹색 / 녹색 0 | min 2 s, `/actuation/real_world_ramp_metering/allow_zero_green` = false | min 2 s, 키 없음(0 허용) | [읽음 CXC; OU PRB:333] |
| 미터 저장고 가드 | 켜짐, trigger 0.9. 머리 앞 재고 / 차로별 저장 ≥ 0.9 인 차로가 있으면 그 결정의 녹색 하한 = 이전 녹색 + 변경 한도. 명령 하한일 뿐, 하류 수용 보장은 아님(코드 주석) | 없음 | [읽음 CX PRB:871-908, CXC `/actuation/real_world_ramp_metering/storage_release_guard`] |
| 결정용 서비스 표 | 동측 4개(RM_C10639·10490·10484·10681)는 plant 머리 표가 결정 표를 **대체**: 1차로 g2–g10 = 1.0·1.5·2.0·2.5·3.0·3.5·4.0·4.2·4.2 대/주기(=360…1,512 veh/h), 10681 = 두 배. 서측 4개는 배분 표 0.71·0.99·1.44·…·4.2 대/주기/차로 | RM_C10490 만 대체(1.0·1.0·1.44·1.89·…·4.2, g3 는 같은 서비스라 정규화로 빠짐). 나머지 7개는 배분 표 | [읽음 CX LPR:614-620, CXC `/freeway/physical_ramp_head_service_veh_per_cycle`; OU LPR:512-520, PRB:36-86, OUC 같은 포인터] |
| g9 = g10 | 동측 1차로 표는 g9 = g10 = 4.2 → 열린 미터에서 기울기 0(METER_NEXT2 N5 와 같은 표) | 10490 g9 3.69 ≠ g10 4.2 | [읽음 CXC; METER_NEXT2:15·225] |
| 열린 미터 secant | 코드는 있음(`meter_activation_secant`), 설정은 켜지 않음 | 없음. 3블록에서 도함수가 안 풀리면 오류 | [읽음 CX SD:547-553·1016-1017, SQ:202-208, CXC 에 키 없음; OU SQ:202-203] |
| 실제 미터 움직임 | joint 440행에서 8개 중 7개 변함, RM_C10644 만 늘 10 s (64cf-s29 한 시드) | V-A 세 시드 내내 g10(900 veh/h) | [읽음 `handoff/evidence/action_audit.json` /joint/rm_values_by_id; VA_REPORT r3:153·772] |

- 뜻 [추론]: 우리 미터가 안 움직인 결정층 원인(METER_CAUSE r2 의 a2-5, 근접 문턱, 유한 후보 없음)에 codex 는 "유한 후보 검사 + 물리 머리 표 + 녹색 0 금지 + 저장 가드" 넷을 한꺼번에 넣었습니다. 넷의 몫을 가를 짝 런은 codex 도 없다고 적었습니다(HANDOFF:239·315).

---

## 2. VSL 경로

| 항목 | codex | 우리 | 근거 |
|---|---|---|---|
| 허용 집합 | 50·60·70·80·90·100·110 | 80·90·100·110 | [읽음 `/config_overrides/freeway_follower/vsl_set` 양쪽] |
| 한 번 변경 한도 | 40 km/h | 40 km/h(같음, 차이 목록에 없음) | [실행 cfgdiff; 읽음 CX ADP:8765] |
| 구역 머리(셀) | FW_E·FW_W 모두 [0,2,5,10,13,15], 자유 구역 [1,2,3,4] → 머리 2·5·10·13. 0 과 15 는 110 고정 | [0,5,10,15], 자유 [0,1,2] → 머리 0·5·10. 15 고정 | [읽음 `/freeway/vsl_zone_heads`, `/freeway/vsl_zone_free`; CX SD:418-428 = OU SD:346-354 와 같은 꼴] |
| 도함수 0 일 때 | `sdmpc_vsl_activation_secant` = true: AD 기울기와 자원 기울기가 정확히 0 인 110 축에 대해 가장 가까운 합법 값(10 km/h 걸음 → 100)으로 secant 탐침 | secant 없음. 3블록에서는 AD 로만 | [읽음 CX SD:534-544·1014-1015·512-531, SQ:202-208; OU SQ:202-203] |
| 고정 VSL 일정 | `adapter.sdmpc_fixed_vsl` 로 VSL 축을 빼고 외생 일정 사용 가능(off 팔 = 110 고정, window 팔 = seg13 90 @1800–5700) | 기구 없음 | [읽음 CX SD:256-260·420-421·829-833, CH; `optimized_vs_off.json`] |
| plant VSL 법칙 | FW_E 만 Carlson A 0.5·E 2.0·α 0, 속도 척도 없음. 표지 셀 [0,3,5,8,14,16,26,28]. `physical_vsl_sign_binding`(VISSIM DSD 묶음 → 보정 표지) 켬, `observed_vsl_history` 켬 | FW_E 만 Carlson A 1.33·E 0.87·α 0 + 측정 속도 척도 m_v(80 0.7225, 90 0.8120, 100 0.9007). 표지 셀 [0,3,5,8,14,**18**,26,28]. 단일값 명령 분포 81/91/101/110 | [읽음 CXR·OUR `/freeway/vsl_fd_response`, `/freeway/component_vsl_transport`; CX LPR:749-753·771-796; OUC `/actuation/vsl_command_distribution`] |
| FW_W VSL | 법칙 없음(옛 경로) | 같음(옛 경로, 110 에서 기울기 0 — 우리 manifest 적시) | [읽음 CXR; OU plant_n31_v2.json qualification] |
| 실제 결과 | joint 3,630행 모두 110, 읽어 들인 값도 110\|110 (64cf-s29 한 시드) | V-A: FW_E seg10 이 100 인 결정이 55 중 9/10/14번, FW_W 늘 110 (세 시드) | [읽음 action_audit.json /joint; VA_REPORT r3:153] |

### 2.1 왜 모든 결정이 110 이었나

- 결정 JSON 의 해당 칸은 원자료에만 있습니다: `metadata.gradient_rows[*]`(kind = vsl 인 행의 `derivative_method`, `fallback_reason` = `inactive_vsl_legal_step`, `stencil`, `own`·`external`·`total`, `resource_derivatives_scaled`), `metadata.local_rows[*].step`, `metadata.trial_rows`, `metadata.candidates[*].status`, `metadata.meter_neighbor_audit` [읽음 CX SD:1040-1062·1107-1110·1156-1157·1185-1189·1288-1289]. 이 PC 의 git 트리에는 결정 JSON 이 없습니다(`git ls-files` 에 adopted355 결정 JSON 0) [실행]. → **raw 필요**.
- 코드로 말할 수 있는 길(모두 [추론], 어느 것이 실제였는지는 raw 필요):
  1. secant 기울기 ≥ 0: 모형에서 110→100 이 Ω 비용을 늘리면 QP 걸음이 위쪽(상한 110)으로 막혀 그대로입니다.
  2. 기울기가 음수여도 작으면 반올림으로 110 에 돌아옵니다. own QP 걸음 d = −g/proximal(proximal 10, CX `evaluation/parameters.json` /sdmpc/proximal), 축 척도 110 이라 100 으로 반올림되려면 |d| ≥ 0.5 × 10/110 = 0.0455 → 110→100 의 예측 Ω 비용 감소가 약 0.041 veh·h 이상이어야 합니다 [계산; 자원 QP·선탐색(1, 0.5, 0.25배)이 더 줄일 수 있음, CX SD:1122-1129].
  3. 걸음이 있어도 전체 모형 재채점에서 목적 감소가 1e-7 보다 크고 NP/NUF cap 을 지켜야 받아들여집니다(CX SD:1154-1175).
  4. 미터 이웃 검사는 VSL 을 고정합니다(CX SD:556-562).
- codex 준비 기록도 VSL 이득을 자격 없음으로 적습니다: `native413_adopted355/preparation.json` /validation_reused/qualification = "Physical and controller integration verified; material VSL gain still unqualified". 같은 파일은 이 판이 직전 판(native354)에 `urban.single_lane_causal_receiving` 하나만 더한 것이라고 적습니다(/config_delta_only) [읽음].
- 같은 시드 off 팔(VSL 110 고정)과 optimized 팔은 VSL 명령이 같았는데 Ω701 이 7,011.8 대 6,911.5 로 −100.3 다릅니다(FW_E 7링크 1,823.1 대 1,840.9). 두 설정 차이는 이름과 `sdmpc_fixed_vsl` 뿐입니다 [읽음 HANDOFF:229-231, optimized_vs_off.json]. VSL 좌표가 있으면 QP·cap 경로가 바뀌는지, 런 사이 흔들림인지는 한 시드로 가를 수 없습니다 [추론]. Ω 밖·④ 는 이 두 팔에 대해 HANDOFF 에 없습니다(run_metadata.json 의 native 도로 TTT+미삽입: off 25,103.2, joint 24,969.6 veh·h, 0–8100 s) [읽음].

---

## 3. 고속도로 plant

| 항목 | codex | 우리 | 근거 |
|---|---|---|---|
| plant manifest | `…/approaches_only/evidence/candidate_manifest.json`(8ae93aa3…), 망 64cf, 기준 설정 CXR, parameters `port_gain/parameters.json`(bd743989…), 자격 문구 "NOT gain qualified or production adopted" | `plant_n31_v2.json`(b119d6d9…), 망 3de889f0, 기준 OUR, parameters `boundary_fit/parameters.json`(8e4f6047…), "NOT_QUALIFIED" | [실행 sha; 읽음 두 manifest] |
| 셀별 FD | FW_E 31셀 모두 ρ_crit·a_m 따로(예: 셀 12 ρ_crit 14.97·a_m 2.37, 셀 10 32.95·2.13). 설치 확인 코드 있음 | 키를 설치 단계에서 거부(K6). "이 트리에는 설치기가 없음" | [읽음 CXR `/freeway/physical_cell_fd`, CX LPR:182-183, harness `canonical_harness.py:329-332`; OU LPR:69-89] |
| 셀별 상태 반응(완화·예상) | FW_E 31셀 `cell_overrides`(완화 시간·예상 계수) | 거부(K6). 우리 FFD 는 `delta_merge` 키 자체를 받지 않음 | [읽음 CXR `/freeway/state_response`; OU LPR:75, FFD:407] |
| δ_merge | 방향 기본 FW_E 1.0·FW_W 0.0 + FW_E 셀 덮어쓰기 10 = 3.530, 12 = 5.089, 21 = 4.212, 23 = 2.211 | FW_E 1.0 균일, FW_W 0.0 | [읽음 CX AFA:415-419, FFD:297-323·345-348, plant_coefficients.json; OU AFA:393-396, parameters.json by_direction] |
| φ_cd (용량 강하) | 1.0 | 1.0 | [실행 `evaluation/parameters.json` 두 파일 잎 차 0; `capacity_drop_discharge_phi` 1.0] |
| lane_drop_phi | 3.0 | 3.0 | [읽음 CXR·OUR] |
| 방향 계수 | W: vf×1.09, ρ_crit×0.68, τ 12, ν 43.05, κ 5. E: 1/1.4/12/36.75/5 | W: vf×1.12, ρ_crit×0.68, τ 12, ν 47.4, κ 17. E: 1/1.4/12/38.7/17 | [실행 parameters 두 벌 읽기] |
| v_free(망) | 120 | 110 | [읽음 `/config_overrides/network/v_free`] |
| segment_params | `port_gain/segment_params.json` | `free_speed_b110/segment_params.json` (바이트 다름) | [실행 pathcmp] |
| 램프 합류 수용(간격 수용) | 4개: 10639 2.5/1.5, 10681 3.5/1.5, 10490 1.5/1.5, 10484 2.0/1.5 (임계 간격/추종 s) | 2개: 10681 3.0/2.0, 10484 2.5/2.5 | [읽음 `/freeway/physical_ramp_receiving_nodes`] |
| 램프 주행 속도 | 10639·10490·10484 실측(상류 40–42 km/h, 머리 뒤 48–68 km/h) | 키 없음 | [읽음 `/freeway/physical_ramp_travel_speeds`] |
| 단일 차로 인과 수용(10639·10484) | 켬. 램프 머리 앞 버퍼 입구에 후진파(3.256 m/s) 상한 | 없음(파일 없음) | [읽음 CX REC:11-50, CXC `/urban/single_lane_causal_receiving`] |
| 링크 68 차로 저장·10681 앞 재고 | `known_wout_*` 일곱 키(차로 수용·국소 대기·커넥터 대기·횡 접근 0.00805/s·물리 주행·native 선택 사전값·인과 차로 반응) | `preserve_known_wout_routes` 만. 대신 10681 차로 결합 `physical_ramp_lane_coupling`·`physical_ramp_conflict_through_inventory`(우리 키) | [읽음 CX RCC:1043-1171; OUC] |
| plant 시계 | 고속도로 5 s·도시 10 s 다중 속도 교환 | 1 s | [읽음 CXC `/freeway/multirate_exchange_sec`·`/urban/multirate_exchange_sec`, CX RS:332-335, HANDOFF:149] |
| 램프 기준 계약 | `ramp_reference_contract` 켬(설정의 램프 키 = 기준 설정 키) | 키 없음 | [읽음 CX LPR:20-36] |

- 뜻 [추론]: METER_NEXT2 N5 의 "codex 에서 조임 값이 B2 합류 셀(큰 δ_merge)+VSL 구역에서만 나왔다" 는 이 셀별 δ_merge·셀 FD 와 같은 자리입니다. 우리 plant 는 같은 자리에 같은 기구가 없습니다. 인계하면 우리 S1(본선 이득 기구) 자리를 codex 계수가 채우지만, 그 계수는 64cf·이전 망에서 맞춘 "자격 없음" 값입니다.

---

## 4. 도시 TSC

| 항목 | codex | 우리 | 근거 |
|---|---|---|---|
| Ω | 701링크 = 우리 635 + 신호 17곳의 접근로·헤드 링크·직접 커넥터 66개. 밖 535. 우리 쪽에만 있는 링크 0 | 635링크, 밖 601 | [실행 두 membership 파일 집합 비교; 읽음 정의 문구] |
| 목적 | Ω701 체류 TTT 만(beta_seconds 0) | Ω635 체류 TTT 만 | [읽음 `/control_area_objective`] |
| 도시 저장고 가드 | 켬(trigger 0.9, 예비 녹색 2 s). 관측 차로 점유로 현시마다 압력 점수 → 신호마다 반공간 제약 하나(LP 로 가능한 크기의 절반까지). 따뜻한 시작점만 투영 | 없음(파일 없음) | [읽음 CX USG:13-99·102-145·148-166, SD:438-439·853-864, RS:252-254] |
| 표본 안 도시 보정 | `/urban/calibrated_aggregate` 켬: 5개 movement 용량(1,677–1,707), 서비스 하한 3개(SC101 5,236·SC109 W→N 2,000·SC108 W→E 1,812.6), SC16 206.53→1,440, 1129 우회 904, 입력 1099/1100 고정 서비스. 파일 문구 "Prior closed seed29 runs … in-sample experiment, not held-out" | 없음 | [읽음 CUR:22-66, `native348/calibration.json`, CXC `/description`] |
| 회전 분율 β 원천 | 기본 `routing`(`outputs/movement_beta_routing_20260824.json`, 2026-08-14 망에서 뽑은 것) + native 선택 묶음 8개(64cf 정적 경로) + 위 보정 | `routing_v3c3`(v3c3 정적 경로 전체 유도) | [읽음 CX ADP:3990-4004, `native_beta/physical_routes.json` native_choice_groups 8; OUC `/urban/beta/source`] |
| 머리 실측 자원 | v11 계약, 커넥터 12개(10619·10629·10633·10698·10283·10285·10119·10691·10539·10631·10493·10206). 따로 SC1 별칭 풀. 코드는 v13 까지 읽지만(10286 은 v12 부터) 실행 계약은 v11 | v1 계약, 2개(10619·10629). 우리 코드는 v1 만 읽음 | [읽음 CX HSR:33-55·104-259, `sc6_queue/head_resources.json` schema v11; OU HSR:33·42] |
| 무신호 처리 | 10개 = 권한 파일 6(SC1004 W→S 셋, SC1004 N→W, SC1001 N→W_RAMP, SC1003 S→E) + 설정 3(SC1002 W→S 우회전, SC1005 N→W 둘) + 보정 1(SC101 S→E 떼어냄) | 5개 = 권한 파일 3(SC1004 W→S 셋) + 설정 2(SC1005 N→W 둘) | [읽음 두 authority 파일, CX PMR:217-260, CXC `/config_overrides/network/urban_movements/SC1002_W_SC1001_to_S_SC105/unsignalized`, CUR:39-46] |
| 대기 귀속 | `/urban/queue/attribution` = head_phase(차로별 머리 현시로 대기 나눔) | 키 없음(β 비례) | [읽음 CX ADP:5937-5947·6192-6203] |
| 신호 좌표·QP | 같은 코드(녹색 벡터, 옵셋, 3블록). codex 는 반올림 1 ms 수리만 더함 | 같음 | [실행 diff: CX SD:493-503 만 더해짐] |
| 실제 움직임 | 17곳 계획이 각각 46–48종 (64cf-s29 한 시드) | V-A 에서도 지령 녹색이 결정마다 바뀜(예: SC109 p2·p3·p4 평균과 최대가 다름, 세 시드). 계획 종류 수는 세지 않음 | [읽음 action_audit.json; VA_REPORT r3:516-523] |

- 숫자 맥락(빼지 않음): codex joint − NC, 64cf-s29 한 시드, 0–8100 s: Ω701 −494.7 veh·h(−6.68 %), Ω 밖 관측 체류 +45.7(+2.87 %), 망 전체 관측 체류 −449.0. ④(native 도로+미삽입)의 공정한 8100 s 차는 NC 누적이 0–9000 s 뿐이라 "모름" [읽음 HANDOFF:17-27·69-74, run_metadata.json]. 우리 V-A − NC3, v3c3 세 시드, 900–9000 s: Ω635 −489/−659/−617, ④ −368/−518/−353, Ω 밖 (a) +122/+141/+264 [읽음 과제 문맥·VA_REPORT r3]. Ω 정의·망·수요·창이 달라 비교하지 않습니다.
- 뜻 [추론]: Ω701 은 접근로 대기를 목적에 넣으므로 TSC 가 접근로 대기를 줄이는 쪽으로 기울어집니다. codex 가 보고한 "도시도로 −8.09 %" 는 이 목적과 같은 땅을 잽니다. 인계하면 우리 Ω635 판정 기록과 끊깁니다.

---

## 5. 우리 결함 D1–D5 와 206.53 계열

| 결함 | 우리 (OU) | codex (CX) | codex 쪽 근거 |
|---|---|---|---|
| **D1** 결정점 1135 분할 사전값(표 0.1667/0.5/0.3333 대 망 0.6/0.2/0.2) | 있음: RCC:1125-1126 가 표 값을 미래 선택에 씀. 표 파일 927d0ba4 | 같은 표 파일(927d0ba4)을 설치하지만 `known_wout_native_choice_prior` 켬 → SC1004_W_out 미래 선택은 망 relFlow 로 계산(64cf 1135 도 2→10646 1, 3→자유 1, 4→10681 3 = 0.2/0.2/0.6) | [실행 64cf .inpx 34455-34466 읽기; 읽음 CX RCC:962-994·1133-1134·1770-1771, aggregate_wout.py:165]. 표가 다른 경로(CX ADP:2919-3042)에서 아직 읽히는지는 열림 |
| **D2** SC1004 W 행 경계 movement 206.53 (S→W·N→W) | 있음(둘 다 206.53 × 차로) | S→W: 머리 자원 10633(66\|p2, 녹색 노출 4창, "max(기존, 관측 지지)") 으로 대체 가능. N→W: 갈림 10625 를 무신호 떼어냄으로 처리(용량 값은 그대로, 녹색 묶임만 없앰) | [읽음 HSR:178-185, head_resources.json v11 rate_policy; PMR:217-260, authority.json unsignalized 6개]. 실제 쓰인 서비스 값은 raw 필요 |
| **D3** 게이트 진입 지연 34 s 상수 | 있음: UQM:617-634 전역 상수 | 기원별 지연 칸 추가(UQM:632-636). `native_gate_travel` 로 게이트 in_SC1001_W(링크 32→129→10490 등 1136 경로)를 경로 길이 ÷ 관측 링크 속도로 계산. 운동학 계약 원천은 관측 위치·속도로 지연 설정 | [읽음 CX PRB:276-338·380-395, OP:217-228] |
| **D4** 미터 서비스 표가 VISSIM 의 1/1.34–1/1.68 | 있음(10490 만 머리 표) | 동측 4개 물리 머리 표. VISSIM(N4) 대비 1차로 g2 1.00, g3 1.11/0.89, g4 0.97/0.98, g5 1.09/1.07배. 서측 4개는 배분 표 그대로 | [읽음 CXC; METER_NEXT2:198-201; 계산] |
| **D5** 링크 129·70 하나짜리 저장고 문턱 | 있음 | 남은 한계로 적음("공유링크129/70의 FIFO/차로접근·포트수용결합"). 대신 미터 저장 가드 0.9·녹색 0 금지·10639/10484 입구 수용 상한이 있음 | [읽음 HANDOFF:263, CX PRB:871-908, REC] |
| **206.53 계열 전체** | 계산식 OU ADP:3781-3921. 고친 곳: K8b-1 SC1002 W 셋, K9-1 W1 SC1001→W_RAMP 셋, K9-2 W SC109 W 직진 5,209.8 (RS:421-424) | 계산식 CX ADP:3760-3900 — 우리와 한 줄도 다르지 않음. 덮는 곳: 머리 실측 자원 12개, 표본 안 보정, 무신호 처리. HANDOFF "부분 수정, 전역 미검증" | [실행 두 구간 diff 0줄; 읽음 HANDOFF:262, branch_service314 `goal_complete=false`, `production_adopted=false`] |

- 뜻 [추론]: 우리 K9-3 설계(D1·D2)의 내용 중 D1 은 codex 가 다른 길(망 relFlow 를 코드에서 읽음)로 이미 넣었습니다. D2 S→W 는 codex 가 고정값 대신 실시간 머리 관측으로 덮습니다. 인계하면 K9-3 의 D1·D2 를 "codex 기구가 v3c3 에서 같은 값을 내는지" 확인하는 일로 바뀝니다.

---

## 6. 우리 K8/K9 고침이 codex 에 있는가

| 고침 | 우리 | codex | 근거 |
|---|---|---|---|
| 결정 예외 시 직전 명령 유지(K8-8/K8-10) | `runtime.decision_error_policy` = `hold_previous_on_exception`. 파이썬 예외(exit 1 + 오류 보고)일 때만 `scripts/decision_hold.py` | 같은 키 = `hold_previous`. 출력이 없거나 exit ≠ 0 이면 `--hold-previous-action`(30 s 시한) → CH:69-125 가 직전 적용 명령 복사. 넓은 조건 | [읽음 OU VBS:1241-1250, watchdog ps1:336-340; CX VBS:1272-1276, CH:75] 두 값은 서로의 검사에서 거부됨 [읽음 OU ps1:339, CX CH:75] |
| 유령 경로 별칭(K8-9, SC5_S 셋) | CAO:254-260·654-666·759-760 | 없음. CAO:664 에서 그대로 "unresolved destination" 오류 → 유지로 넘어갈 것 | [실행 grep] |
| W (SC109 W 직진 5,209.8) | RS:242·423 | 키 없음. 같은 movement 를 머리 자원 10285(173\|p3, regular_exit)로 실시간 측정 | [읽음 CX HSR:105-125, head_resources.json v11] |
| H-b ((173,p4) 하한 씨앗 1,045.16) | `signal_head_observation.configure_head_floor_seed`, RS:415 | 키 없음. 머리 자원 10286(173\|p4)은 코드에 있으나 실행 계약 v11 에 없음 → 표본 안 서비스 하한 2,000(seed29)만 | [읽음 CX HSR:46-54, head_resources.json v11 resources, calibration.json service_floors] |
| K8b SC1001 동측 정지선(차로 FIFO)·출구 법칙·옆 넘김·SC1001/SC1002 포화·off-ramp 분할 예측·직접 출구 몫 | 있음(OUC `/urban/stopline_approach` 등 26잎) | 없음. 대신 `shared_sc1001_approach` boundary_only_v1·`sc1001_shared_lane_receiving`·`sc1001_destination_travel` | [실행 grep 0; 읽음 CXC] |
| 램프 도착 예측 RM_C 키 + `strict_ramp_keys` | 있음(8개 물리 미터 키) | 옛 그룹 키 R_D_W·R_F_W·R_D_E·R_F_E. 코드 주석상 이 설정은 120 s·900 veh/h 폴백 | [읽음 CXC `/calibration_override/prediction/local_ramp_arrival_forecast`, CX ADP:9457-9489] |
| 서비스 표 정규화(K3) | 있음(PRB:36-86) | 없음(동측 표 g9 = g10 그대로) | [실행 diff] |
| plant 기준 키 거부(K6) | 있음 | 반대로 설치·검사 | [읽음 §3] |
| 정렬 합(PYTHONHASHSEED, K1) | 있음(UQM:1306) | 같은 고침이 있음(주석만 다름) | [실행 diff UQM] |
| 미터 넘침 귀속(K8-3 S1-OWN) | OU SD:262-297 | 없음 | [실행 diff] |
| 단일값 VSL 명령 분포 | 81/91/101/110 | 없음 | [읽음 OUC `/actuation/vsl_command_distribution`] |
| GB-7′ 허용 목록 | 진단 전용(gb7_allowed.py), 런타임 무관 | 해당 없음 | [읽음 c20aff1d 커밋 메시지] |

---

## 7. 설정 키 차이

- 셈 [실행 cfgdiff.py: 사전은 펼치고, 사전을 품은 목록도 펼치고, 스칼라 목록은 한 잎]: codex 6,610잎, 우리 6,567잎, 공통 6,513. 차이 195 = codex 만 97 + 우리만 54 + 값 다름 44. 인계 증거 `effective_config_fields.csv` 6,561행과는 펼치는 규칙만 다릅니다(빈 사전 50개, 목록 하나) [실행].
- 묶음 [실행 cfggroup.py; 이름은 이 문서가 붙임]:

| 묶음 | codex 만 | 우리만 | 값 다름 | 합 |
|---|---:|---:|---:|---:|
| 메타(이름·설명·노트·재핀 기록) | 7 | 0 | 5 | 12 |
| 미터 결정(cap 후보·이웃 검사·녹색 0·저장 가드) | 5 | 0 | 1 | 6 |
| VSL(집합·구역·secant·명령 분포) | 3 | 5 | 4 | 12 |
| 램프 plant(머리 표·수용·속도·인과 수용) | 42 | 2 | 11 | 55 |
| 고속도로 plant(manifest·segment_params·v_free·다중 시계) | 2 | 2 | 3 | 7 |
| 램프 도착 예측 키 | 8 | 17 | 0 | 25 |
| Ω 영역 | 0 | 0 | 2 | 2 |
| 망 핀·시나리오 파일 경로 | 0 | 0 | 17 | 17 |
| codex 도시 모형(known_wout·저장 가드·보정·머리 귀속·게이트·SC1001 공유) | 29 | 2\* | 0 | 31 |
| 우리 도시 고침(K8b·K9) | 0 | 26 | 0 | 26 |
| runtime(유지 정책·시한) | 1 | 0 | 1 | 2 |
| 합 | 97 | 54 | 44 | 195 |

\* 이 2잎은 우리 `sc1001_wout_saturation` 이 접두어로 섞인 것입니다. 우리 도시 고침은 실제로 28잎입니다 [실행 cfg_leaf_diff.csv 읽기].

- 경로 값이 다른 18곳은 가리키는 파일의 바이트가 모두 다릅니다(Ω 소속·경로 계약·VBS·plant manifest·segment_params·관측 망·투영 보수·머리 자원·known W_out·경로 위상 둘·신호 권한 둘·내부 입력·램프 가지·SC2001·공유 접근로) [실행 pathcmp.py].
- 가장 큰 영향 열 가지 [읽음 값; 영향은 추론]:
  1. `/control_area_objective/membership_path` — Ω701 대 Ω635. 목적 자체가 다름.
  2. `/freeway/lane_plant` — manifest 와 그 안 기준 설정(CXR 대 OUR): 셀 FD·셀 δ_merge·Carlson 계수.
  3. `/adapter/sdmpc_meter_neighbor_audit` — 미터가 움직이는 유일한 결정 길.
  4. `/freeway/physical_ramp_head_service_veh_per_cycle` — 동측 미터 결정·plant 표.
  5. `/adapter/joint_owner_game/max_leader_candidates` 3 대 1 — 결정당 예측 횟수와 이웃 검사 대상 수.
  6. `/actuation/real_world_ramp_metering/allow_zero_green`·`storage_release_guard` — 닫힘 금지·넘침 하한.
  7. `/urban/calibrated_aggregate` — seed29 표본 안 보정.
  8. `/urban/known_wout_native_choice_prior` 등 known_wout 일곱 키 — D1 과 10681 앞 재고.
  9. `/config_overrides/freeway_follower/vsl_set`·`/freeway/vsl_zone_*`·`/adapter/sdmpc_vsl_activation_secant` — VSL 탐색 공간.
  10. `/runtime/decision_error_policy` 값 — 두 러너가 서로의 값을 거부.

---

## 8. 종합 표 — 레버 | codex | 우리 | 인계할 때 생기는 일

| 레버·부분 | codex | 우리 | 인계할 때 생기는 일 [추론] |
|---|---|---|---|
| RM 결정 길 | 이웃 검사 + 조합 1회 + cap 후보 3 | AD·QP 만, cap 1 | 우리 V-A 의 "미터 늘 g10" 원인이 코드 쪽에서 바뀜. 결정당 예측 수가 늘어 벽시계가 늘 것(codex joint 8100 s 런 17,264 s, HANDOFF:41) |
| RM 운영 경계 | 녹색 0 금지, 저장 가드 0.9 | 녹색 0 허용, 가드 없음 | 우리 K9-3 S5(안전 장치) 자리를 codex 가 채움. 링크 129 공유 넘침(우리 규칙 RM 팔 v3c3-s41 1099 미삽입 +644.6, METER_NEXT2:130)이 막히는지는 확인 안 됨 |
| RM 서비스 표 | 동측 4개 물리 머리 표(VISSIM 0.89–1.11배), g9 = g10 | 10490 만, 나머지 배분 표 | D4 가 동측에서 닫힘. 서측 4개와 10681 g7 이상은 근거 없음(양쪽 다) |
| VSL 탐색 | 50–110, 머리 2·5·10·13, secant | 80–110, 머리 0·5·10, secant 없음 | 사용자 계획(VSL 활성화)의 출발점은 "codex 에서도 110 고정" 임. 활성화는 법칙·이득 방향 문제로 남음(HANDOFF:265) |
| VSL plant 법칙 | Carlson A0.5/E2.0, 척도 없음, 표지 16 | Carlson A1.33/E0.87 + m_v, 표지 18, 단일값 81/91/101 | 둘 중 하나를 골라야 함. 우리 기록은 Carlson 계열이 통계적으로 기각됐다고 적음(plant_n31_v2.json qualification) |
| 고속도로 plant | 셀 FD + 셀 δ_merge + 셀 상태 반응, 5 s | 균일 δ 1.0, K6 거부, 1 s | 우리 S1 자리를 codex 계수가 채우지만 64cf·b110 이전 자료로 맞춘 "자격 없음" 값. v3c3 로 옮기면 재적합 필요 |
| 램프 합류·입구 | 수용 노드 4개, 램프 속도 3개, 10639/10484 입구 후진파 | 수용 노드 2개 | 10639·10490 합류 모형이 생김. 값의 v3c3 타당성은 미확인 |
| 링크 68·10681 | known_wout 일곱 키(차로 저장·횡 접근 등) | 차로 결합 두 키(우리 것) | 두 기구가 겹치는 자리. 하나만 남겨야 함 |
| 도시 Ω | Ω701 | Ω635 | 판정 기록 단절. 짝 비교는 같은 Ω 로 다시 세야 함 |
| 도시 TSC 모형 | 저장 가드, 머리 자원 12, 무신호 10, 머리 현시 대기 귀속 | 머리 자원 2, 무신호 5 | 접근로 대기 쪽 기구가 더 많음. 우리 W·H-b 와 같은 movement 를 다른 길로 덮음 |
| 표본 안 보정 | seed29 로 맞춘 도시 보정 켬 | 없음 | 인계 수치(64cf-s29)는 같은 시드로 맞춘 값 위에서 잰 것. 다른 시드·v3c3 에서 같은 크기가 날지는 모름 |
| β 원천 | 2026-08 망 routing + native 8묶음 | routing_v3c3 | v3c3 로 옮기면 β 원천을 다시 정해야 함 |
| 206.53 계열 | 계산식 같음, 일부 덮음 | 계산식 같음, 일곱 movement 고침 | 남은 경계 movement(우리 셈 146)는 양쪽 다 남음 |
| D1 / D3 | 코드로 고치는 기구 있음 | 없음(K9-3 설계 단계) | K9-3 D1 은 codex 기구 재사용으로 바뀔 수 있음 |
| D2 | S→W 실측 머리, N→W 무신호 | 206.53 | K9-3 의 Q3(S→W 1,807.4)·Q5(N→W 신호 유지 1,850) 와 다른 선택. 하나를 골라야 함 |
| D5 | 남음(가드로 막음) | 남음 | 양쪽 같은 열린 문제 |
| 결정 유지 | `hold_previous`, 넓은 조건 | `hold_previous_on_exception`, 예외만 | 러너·키를 하나로 통일해야 함 |
| 우리 K8/K9 고침 | 유령 별칭·W·H-b·SC1001 동측·RM_C 도착 키 없음 | 있음 | 인계 뒤 다시 옮기거나 codex 기구로 대체 판단 필요 |
| 망·핀 | 64cf, 핀 검사 여러 곳 | 3de889f0 | v3c3 에서 그대로는 초기화 단계에서 멈춤(망 sha 검사 9곳 이상, 쉬운 답 12). 재핀 18파일 + 보정·머리 자원·별칭 풀 |

---

## 9. 열린 것

1. VSL 이 110 에 머문 까닭: 결정 JSON 의 VSL 기울기 행(`derivative_method`, `fallback_reason`, `stencil`, `total`)과 `local_rows`·`trial_rows`·`candidates.status` — **raw 필요**(`raw/joint/sdmpc/` 결정 JSON 48개).
2. codex 램프 도착 예측이 결정에서 120 s·900 veh/h 폴백을 탔는가 — **raw 필요**(결정·예측 JSON 의 ramp_arrival 진단).
3. 1135 표(0.1667/0.5/0.3333)가 codex plant 의 다른 길(CX ADP:2919-3042)에서 아직 읽히는가 — 코드 추적 더 필요(이번에 끝내지 않음).
4. 머리 자원 10633(SC1004 S→W)이 실제로 고른 서비스 값과 시점 — **raw 필요**.
5. optimized 와 off 팔의 Ω701 −100.3 차이(VSL 명령 같음)의 기구 — 한 시드라 가를 수 없음. 같은 판 다른 시드 짝이 필요(봉인 시드 제외).
6. 표본 안 도시 보정을 끈 같은 판의 결과 — codex 자료에 없음(HANDOFF:315 와 같은 결).
7. 인계 판을 v3c3 로 재핀할 때 codex 셀 FD·δ_merge·Carlson 계수를 다시 맞출지, 우리 값을 쓸지.
8. 결정 유지 키·러너 통일 방법(codex VBS:1272-1276 대 우리 VBS:1241-1250).
9. codex 인계 수치(Ω701 −6.68 %, Ω 밖 +2.87 %)의 ④ 공정 비교: NC 0–8100 s native 미삽입 누적이 없음 — **raw 필요**(NC FZP·.err 로 재구성하거나 새 NC).

---

## 10. 파일

- 이 문서: `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/R_MECH.md` (sha256 은 LOG.md 끝 항목과 반환값에 적음).
- 작업 파일: `codex_handoff/work/mech/cfgdiff.py`, `pathcmp.py`, `cfggroup.py`, `cfg_leaf_diff.csv`(195행), `sdmpc_886.py`·`sdmpc_ca181.py`·`prb_886.py`·`lpr_886.py`·`adp_886.py`·`rs_886.py`(git show 사본, 비교용).
- 공유 worktree: `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff` (지우지 않음).
