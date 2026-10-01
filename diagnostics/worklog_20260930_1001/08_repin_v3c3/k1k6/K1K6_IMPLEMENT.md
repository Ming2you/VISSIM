# K1–K6 구현 보고 (v3c1 기반, 재핀 계획 2026-10-01)

- 작업 트리 W = `D:/VISSIM-merge/sim3-n31-v3c3`, 브랜치 `claude/repin-v3c3-20261001`
  - 시작 `9ed2ef0` → **K6 head `54d821c1e7140d23635f295283849d5a1197624c`**
  - 로컬 커밋 6개, 푸시하지 않았습니다.
  - 작성자·커미터: Ming2you <alsrjsrb1915@snu.ac.kr>
  - 메시지 끝: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  - `git status --porcelain --ignored` 0줄. 바뀐 파일 19개는 모두 작업본 바이트 = `git cat-file --filters HEAD:<f>`(줄끝 일치) [실행]
- 사전 선언(코드 수정 전에 고정)
  - `GA_PREDECLARATION.md` sha256 `34cc48ee7694af28…`
  - 보충 1 `GA_PREDECLARATION_ADDENDUM_1.md` `607a2eb5df12702b…`
  - 보충 2 `GA_PREDECLARATION_ADDENDUM_2.md` `c96b8a0271e49cfa…`
  - 보충 두 개는 GA 재생 전에, 개발용 점검(smoke)에서 찾은 Root 의존 필드를 **추가 열거**한 것입니다(§4). 원 선언 파일은 바꾸지 않았습니다.
- 표기: [실행] 직접 돌려 확인 · [읽음] 코드·파일에서 확인 · [추론] 시험하지 않은 판단

## 0. 결론

- K1–K6을 모두 구현했습니다. 계획이 선언한 효과 밖의 동작 변화는 없습니다. 그래서 **stop = false**입니다.
- 키가 없거나 표가 유일할 때의 동일성은 단위 시험과 smoke 두 건으로 확인했습니다 [실행].
  - **무제어 4050**: CSV 같음. 판정 IDENTICAL. 남는 차이는 선언한 것뿐(휘발 7, provenance, 새 키 3, 4필드 1/1/1/2 ulp, 보충 1의 경로 2)
  - **SDMPC 900**(T5-B 5323faa4 기록 대비): 다음이 모두 같습니다.
    - CSV 바이트
    - 목적함수 repr
    - 제어 필드 7개
    - 탄젠트 트레이스
    - 4필드
- 기존 시험 묶음의 실패 id 집합은 `9ed2ef0` 기준선과 같습니다. 새 시험은 모두 통과합니다(§3).
- 사용자가 볼 것 두 가지
  - **K6 `state_response` 거부**: 계획은 "이 트리에 설치기가 없다"고 했습니다. 실제로는 `freeway_fd.configure_state_response`(`freeway_fd.py:393`)가 설치합니다 [읽음]. 계획의 결정대로 v2 reference에서는 거부했습니다. 지금 reference에는 이 키가 없으므로 영향은 없습니다.
  - **K5의 V-11(U5-a 생성기 가족 옵션)과 V-6(러너 81,91,101,110)은 K7로 미뤘습니다.** 지금 생성기는 분포형 가족(L1, 사상 없음, 80..110) 하나만 만듭니다. 옵션은 기본값이 단일값으로 바뀌는 K7에서야 의미가 있습니다.

## 1. 커밋별 내용

| K | 커밋 | 바꾼 곳 | 키 없음·현재 설정에서 |
|---|---|---|---|
| K1 | `2d70e4a` | `vendor/NumSim-mine/src/models/state.py:1308` `sorted(set(...), key=str)` | 합산 순서만 고정. 4필드 ≤ 2 ulp |
| K2 | `779037b` | `tools/make_replay_state_v2.py:240`(`action_contract`), `:262`(`compare(out_dir, vsl_expected=None, *, vsl_contract=None)`), `:350`; `tools/n31_common.py:221`(`effective_vsl_written_set`), `:232`(`tuning_vsl_contract`); 새 `evaluation/controllers/vsl_command_distribution.py`(parse, written_set, runner_allowed_speeds) | 전부 110인 결정은 판정 같음. `replay_compare.json`에 키 5개 추가 |
| K3 | `de5ff5f` | `physical_ramp_branches.py:33-86`(`normalise_service_table`, `measured_head_service_table`), `:140`(configure 수송표), `:231`(메타); `lane_plant_runtime.py:512`(측정 곡선 설치), `:543`(메타) | 10490: {0,2,3,..,10} → {0,2,4,..,10}. 나머지 7개 표와 수송표는 같은 객체 |
| K4 | `8959efa` | `freeway_fd.py:19-113`(`speed_scale_knots`, `validate_speed_scale`, `speed_scale_ratio`, `literature_validation_maximum`), `:141`(b 분기), `:178`(installer 검사); `physical_lane_groups.py:211-214` | 비트 동일. 탄젠트 연산·비교 수 동일 |
| K5 | `07a2f7a` | `vissim_stackelberg_adapter.py:12652-12665`(writer), `vsl_command_distribution.py:101-163`(written_value, validate_tuning, check_family, check_family_files), `obs150_contract.py:207-214`, `runtime_setup.py:246-251`, `tools/launch_plan.py:134-140`, `make_config_n31.py:418-421` | CSV 비트 동일. 가족 검사 통과. 생성기 `--check`: config `33027258`, urban_b1 `ad482a53` 그대로 [실행] |
| K6 | `54d821c` | `lane_plant_runtime.py:69-89`(`reference_install_check`), `:124`(호출), `:542`(메타) | 현재 reference 통과(두 키 declared) |

### K1 (H-1)
- **바뀐 것**: off-ramp 저장고 점유 합산만 정렬된 링크 이름 순서로 고정했습니다. 다른 set 순회(H-2: AD:4457 등)는 계획대로 건드리지 않았습니다.
- **시험** `N31D/tests/test_n31_hash_order.py`(새 파일)
  - 순서에 민감한 저장고(1e16 하나 + 1대 일곱)를 해시 시드 6개의 자식 python에서 합산합니다.
  - 옛 FRZ 코드는 결과가 **3가지**였습니다.
  - K1 코드는 **1가지**이고, 정렬 순서 합과 같습니다 [실행].

### K2 (P-1, P-2, N14)
- **`--tuning` 판정**: 다음을 모두 요구합니다.
  - VSL 행 66개, 미터 8개
  - 모든 VSL 값 ∈ 쓰는 집합(튜닝 vsl_set을 `actuation.vsl_command_distribution`으로 옮긴 상. 키가 없으면 항등)
  - 쓰는 집합 = 튜닝 트리 러너(`execution.signal_vbs_config`)의 `RW_ALLOWED_VSL_SPEEDS`
- **위치 인자 의미는 그대로**입니다: `--vsl-expected`와 `compare(out_dir, vsl_expected)`.
- **시험** `tools/tests/test_tools_replay_contract.py`(새 파일, 8개)
  - 통과: {110}, {91,110}
  - 거부: 단일값 가족에서 {90}, 두 가족 모두 {120}, 행 수 오류, 러너 불일치, 잘못된 사상 9종
  - 위치 인자 의미, 이 트리의 배포 튜닝
  - `test_tools_replay.py`는 건드리지도 돌리지도 않았습니다.
- **종단 확인**: T5 `A/T004050` 사본에서 새 compare `--tuning`이 IDENTICAL이었습니다 [실행].

### K3 (R-1, R-2, R-4, N3)
- **규칙**: 같은 서비스 그룹에서 **가장 낮은 허용 녹색**(0 또는 ≥ `min_green_sec` 2.0)만 남깁니다.
  - 순서를 보존하는 필터이고, `str` 키는 그대로입니다.
  - 유일한 표는 **같은 객체**로 돌려줍니다.
- **거부하는 경우**: 허용 녹색이 없는 공유 그룹, 최대 서비스 녹색 탈락. 거부는 configure와 결정마다 도는 lane plant 설치 경로 두 곳에 있습니다.
- **디코드의 거부(`candidate_from_services`)는 바꾸지 않았습니다.** hybrid `92fa4b8` 코드는 옮기지 않았습니다.
- **시험** `diagnostics/test_physical_ramp_branches.py::ServiceNormalisationTests`(fixture 없음, 9개)
  - 10490 표와 `list(items())`
  - 유일한 표의 동일성, 규칙, 거부(설치 경로 helper 포함)
  - **GA-4(b)**: 옛 표 + 적용 녹색 5 → `no unique physical green: RM_C10490`이 재현됩니다. 새 표에서는 디코드 {4,5,6,7}입니다.
  - 기준점 0/2/4/5/6/10에서 모든 씨앗이 디코드됩니다.
  - 상자에 3이 없으면 격자가 같습니다(pickle 바이트).
  - SDMPC 미터 축 허용집합
  - 기록된 녹색 3은 거부됩니다. ALINEA는 3 → 4가 됩니다.

### K4 (V-1, V-2, N1, N6)
- **스펙**: `speed_scale={'form':'cubic_lagrange','levels':{'80','90','100'},'maximum':110.0}`(Carlson 전용)
  - b = (80,m80),(90,m90),(100,m100),(110,1)을 지나는 Lagrange형 3차식입니다. 매듭에서 정확하고, 110에서 1.0입니다.
  - 기울기 [실행]: 80 0.009361, 90 0.008719, 100 0.009212, 110 좌 0.010840
  - b(75) = 0.673966로 외삽합니다.
- **검사 위치**
  - 단조 검사는 installer(`configure_literature_vsl`)에서만 합니다. 이때 매듭 = vsl_set도 확인합니다.
  - 매 호출 경로는 구조만 파싱합니다(비용 [추론] 수 µs).
- **시험** `tests/test_literature_vsl_fd.py::SpeedScaleTests`(8개)
  - 키 없음 비트 = 옛 함수 원문 사본
  - **탄젠트 연산 수·비교 수·tangent_entries 동일**: 계측 math proxy를 붙여 확인
  - 수준 정확, 110 공칭, 단조와 ρc, 잼 거부
  - AD = 중앙차분(80/90/100), 110 좌기울기
  - 거부(frejo, 구조, 최대 불일치, 110 초과), installer와 lane-group 검증
- T9(`test_n31_ad_smoke`)와 `test_n31_vsl_model`/`vsl_binding`, `diagnostics/test_freeway_fd`는 그대로 OK입니다.

### K5 (V-5, V-9, N5, N7)
- **writer**
  - 사상이 있으면 엄격합니다(1e-9 안의 명령만 받고, nearest와 120 확장 없음).
  - action JSON `vsl`은 명령 공간 그대로입니다.
  - 키가 없으면 옛 nearest + 120입니다.
- **V-9 검사**: 다음이 모두 성립해야 합니다.
  - reference vsl_set = 튜닝 vsl_set
  - 러너 목록 = 상
  - speed_scale ⇔ single_value
  - levels = vsl_set − {max}, maximum = max
- **사상 자체 검사**: 정의역 = vsl_set, 단사, 110→110
- **새 메타데이터 키는 없습니다.**
- **시험** `diagnostics/test_vsl_command_distribution.py`(새 파일, 9개)
  - 실제 ver2n21 매핑 66행 writer: 키 없음 = nearest+120, 사상 → 81/91/101/110 float, 95/120 거부
  - 혼합 가족 5종 거부
  - 이 트리 파일 통과
  - `validate_tuning_v2`가 잘못된 사상을 거부

### K6 (E-1)
- **검사**: reference `vsl_fd_response`/`component_vsl_transport` = 성분이 설치한 속성이어야 합니다(양쪽 부재는 같음으로 봄). `physical_cell_fd`나 `state_response`가 있으면 거부합니다.
- **기록**: 결과를 메타 `lane_plant_install_check`로 남깁니다.
- **시험** `test_n31_plant_load`
  - 실제 plant context의 install_check, 설치값 = reference
  - stub installer로 키 누락·speed_scale 누락·transport 누락·미선언 설치·거부 키·비객체가 모두 거부됨

## 2. 핵심 해시 (K6, 작업본 바이트) [실행]

| 대상 | sha256 |
|---|---|
| `src/models/state.py` (K1 판) | `7c1f577a8d0ac485198ddaeb2dd8ddea799b3f5578ad57e966974ad16f7847e9` |
| `vissim_stackelberg_adapter.py` (K5 판) | `028cf0cd6e0b1019e2232e7a2afadc75dda9e8a2ce8c9154bd4236f25292aa18` |
| `numsim_src_sha256` (smoke provenance) | `f394c83bbc16a70ada4ff3bfb8e0e69910778cbf3903b5a5fa91b432d9351ca5` |
| `config_n31_v2.json` (변경 없음) | `3302725804f09e5b44345234546f89799c7b1253041fe8d9282d707dabd86365` |

- K1–K6 diff 파일 19개 = `git diff --name-only 9ed2ef0 54d821c1`. GA §2.3 마지막 항목의 기대 집합입니다.

## 3. 시험 묶음 (BELOW_NORMAL, 금지 시험 제외) [실행]

- 기준선 `logs/base`(K1 전 W), 비교 `logs/k6`
- 로그 위치: `…/scratchpad/v3c3-k1k6/logs/`

| 묶음 | 9ed2ef0 | K6 | 판정 |
|---|---|---|---|
| N31 unittest 16모듈 | 190 OK (skip 3) | 194 OK (skip 3) | +4는 K6 시험 |
| T9 `test_n31_ad_smoke` | 9 OK | 9 OK | 같음 |
| tools(plant_gate, verify_gt, watch, common) | 60 OK | 60 OK | 같음 |
| obs150 비-ps1 13모듈 | 143 OK | 143 OK | 같음 |
| repin/prepare pytest | 67 passed | 67 passed | 같음 |
| diag 20파일(아래 목록) | 211 passed / 28 failed / 37 errors | 228 passed / 28 failed / 37 errors | **실패 id 집합 같음**(diff 0). +17은 K3 9개 + K4 8개 |
| extra 3파일 | 13 passed / 7 failed / 4 errors | 같음 | 실패 id 집합 같음 |
| dprof(`test_diagnostic_profile`, `test_action_csv_vbs_validators`) | 16 passed, 2 skipped | 같음 | 같음 |
| 새 시험 | — | hash_order 1, replay_contract 8, vsl_command_distribution 9, ServiceNormalisation 9, literature 23(8 신규) | 모두 통과 |

- **diag 목록**: `tests/test_literature_vsl_fd`, `diagnostics/test_{physical_ramp_branches, freeway_fd, action_row_iterator, joint_written_action, runtime_setup, lane_plant_observation, sdmpc_pfo_caps, joint_owner_addresses, joint_neighbor_callbacks, sdmpc_initial_shared, shared_joint_price_quantity, validated_decision_hold, joint_final_output_budget, signal_profile_experiments}`, `tests/test_{diagnostic_rule_profile, action_csv_signal_group_rows, model_plant_cycle_identity}`, `demand_sweep/…/test_literature_terms`, `…/test_state_response`
- **기준선 실패의 원인**: 거의 모두 없는 fixture입니다(`evaluation/runs/codex_native_clock_*` 등 git 무시 폴더) [실행].
  - 그래서 writer 쪽 기존 시험(`test_action_row_iterator`, `test_joint_written_action`)은 이 트리에서 돌지 않습니다.
  - K5 writer 동일성은 새 시험과 smoke(CSV 바이트)로 확인했습니다.
- **돌리지 않은 것**
  - 금지 7종: `test_b1a_watchdog_attempt_launch`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150`, `test_native_vbs_clock`, `test_tools_launch`, `test_tools_replay`, real_watchdog
  - `test_tools_integration`
  - `launch_plan.py`는 import 확인만 했습니다.

## 4. 재생 3건 (모두 GA 관문 아님) [실행]

| 무엇 | Root | 결과 | 파일 |
|---|---|---|---|
| **N1** 옛 트리 A/B: 4050 반사실 SDMPC, `PYTHONHASHSEED` 0 대 2 | W @ 9ed2ef0(K1 전, FRZ_OLD 표 대비 changed/missing 0, extra = worklog 35) | **완전히 같음**. CSV, 목적함수 repr(497.36952262710264 / 498.47908727527283), 제어 필드, 탄젠트 트레이스, 4필드, JSON(시간·토큰·state_json 제외) 차이 0 | `n1/n1_compare.json`, `n1/B/`, `n1/tree_check_{before,after_n1}.json` |
| smoke 무제어 4050 | W @ 54d821c1 | exit 0, IDENTICAL, CSV 같음. 4필드 1/1/1/2 ulp. 새 키 3개 값이 선언과 같음. 선언 밖 2개 → 보충 1 | `smoke/T004050_54d821c1.summary.json` |
| smoke SDMPC 900 | W @ 54d821c1 | T5-B r1 대비 CSV·목적함수·제어 필드·탄젠트 트레이스가 같음. RM_C10490 축 [8,9,10], VSL 블록 0 [80..110]. 선언 밖 384개 = 전부 `transformed_source_sha256` 경로 키 → 보충 2. 상대 경로 97/97 같음, sha가 다른 파일 5개 = K diff 안 | `smoke/S000900_54d821c1.summary.json` |

- **N1 해석**
  - 4050 SDMPC에서는 해시 시드 0과 2가 같은 비트를 냈습니다. 옛 코드에서도 이 상태의 SDMPC 출력에는 해시 순서가 닿지 않았습니다.
  - 다만 T5-H 무제어 4050에서는 시드 2가 4필드를 바꿨습니다. 그러니 "닿지 않는다"는 이 상태 하나의 결과입니다 [추론].
- **정리**: 재생이 만든 `__tangentcache__`(N1 92개, smoke 95개)는 지우지 않고 `n1/moved_tangentcache/`, `smoke/moved_tangentcache/`로 옮겼습니다(목록 csv). W에는 무시 파일이 0개입니다.
- **B3**: 이 재생들은 개발용이고, W를 편집하지 않는 동안에만 돌렸습니다. GA 재생은 선언대로 FRZ_K6과 GWT에서만 돌립니다. GWT와 FRZ_K6는 이 단계에서 만들지 않았습니다.

## 5. 계획에서 달라진 것과 남긴 것

1. **GA-4 옛 코드 쪽**
   - "K2 트리 재생" 대신 기록 증거(runlog 1825–1827, `action_003000.error.txt`)와 함수 수준 재현(K3 시험)으로 바꿨고, 이를 선언했습니다.
   - K2 코드를 돌릴 수 있는 트리가 편집 트리와 쓰기 금지 트리뿐이기 때문입니다.
   - 또 hybrid 튜닝 파일이 K6 트리에 없어서, K6 쪽 반사실은 ps1 대신 어댑터를 직접 부르는 하네스가 필요합니다(선언 GA-4).
2. **선언 보충 2건**(§4): Root에 따라 바뀌는 문자열 필드를 B1 열거에 더했습니다.
   - `numsim_git_commit`은 git 트리 Root에서도 ''입니다(원 선언 정정).
3. **K6 `state_response`**: §0 참고
4. **K5**
   - V-11과 V-6은 K7로 미뤘습니다(§0).
   - N12(VSL 행 metadata에 `vsl_command` 토큰)은 넣지 않았습니다(선택 항목).
   - N7의 "상 ⊂ 망 DSD"는 K7의 `repin_scenario_v2.runner_config_check`가 맡습니다.
5. **K1 시험 파일 줄끝**: `test_n31_hash_order.py`는 CRLF로 커밋됐습니다(속성 `-text`, 같은 폴더 다른 파일은 LF). 기능에는 영향이 없습니다.
6. **H-2**(다른 set 순회)는 고치지 않았습니다. GA-2가 판정합니다.

## 6. 다음 단계 (GA, 선언 §6 순서)

1. FRZ_K6(`run_sdmpc_n31.ps1 -Freeze -PreflightOnly`, GWT에서)과 GWT(`git worktree add --detach D:/VISSIM-merge/sim3-n31-v3c3-k6gate 54d821c1`)를 만듭니다.
2. 트리를 확인합니다.
3. GA-1 → GA-2 → GA-3 → GA-4 → GA-5 순으로 진행합니다.
   - N1은 이미 끝났습니다(§4).
   - 하네스는 `n1/n1_common.py`의 틀에 선언 §5의 상수(FRZ_K6, GWT, K6 tools)를 넣어 씁니다.
