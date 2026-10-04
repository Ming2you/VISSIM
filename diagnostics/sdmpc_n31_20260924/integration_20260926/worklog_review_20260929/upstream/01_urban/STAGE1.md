# 도시 묶음 2 — 단계 1 보고 (U4-0 비트 동일 정리)

- 작성: 2026-09-28 (16:01 시작, 18:05 세션 한도로 중단, 19:13 재개). 계획: `B/BATCH2_PLAN.md` §4.1, §6.1 G-ID (a)(b)(c), §7 행 1, 부록 C-7·C-8·C-9.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·rebase·다른 브랜치/워크트리 조작은 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S1 = `B/impl/stage1`, S0 = `B/impl/stage0`, H = `B/harness`, W = b2 트리, OLD = `D:/VISSIM-merge/sim3-n31-urban`(cf3ce37, 읽기 전용), A = `W/evaluation/controllers/vissim_stackelberg_adapter.py`(작업 트리 줄 번호), MC = `W/diagnostics/sdmpc_n31_20260924/make_config_n31.py`.

---

## 0. 결론

**G-ID (a)(b)(c) 모두 통과했습니다. 멈춤 규칙은 걸리지 않았습니다(stop=false).** 단계 2(C6)로 넘어가도 됩니다.

| 확인 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| 재개 검토 (과업 지시) | 결함 셋을 고침: 변환이 U4-0 뒤 튜닝의 빠진 키를 채울 수 있던 것, 평탄화가 seed를 안 보던 것, provenance가 diff 내용을 못 보던 것. 실운영 경로는 변환을 import하지 않음(정적 시험) | [실행] §2.8 |
| 필수 키 4개·`install_lane_group_membership` (§4.1-1·2) | 계획대로. 헤드 경로는 옛 키를 하나도 읽지 않음 | [실행] §2.1·§2.2·§3 |
| `_SUS_SIGS` 대체 계수 (§4.1-2 (i)) | R-obs-b 61·S1 19·S0e 19 상태, 전체 결정 61: 대체 0, 반환 뒤 옛 코드 호출 0 → (ii) 적재 안 함, `sustained_json` 제거 | [실행] §2.3 |
| 죽은 분기 격리 (§4.1-3) | **하지 않음**: 옛 경로를 실제로 쓰는 추적 튜닝 65개 | [실행] §2.4 |
| 죽은 키 제거·평탄화 diff 검사 (§4.1-4·5, §3 C-9) | 세 config 모두 15개 삭제·3개 추가, 목록 밖 변경 0 → PASS | [실행] §2.7 |
| 기존 스위트 (§4.0-2, 단계 0 해석) | 68개 실행 대비 회귀 0. 새 시험 14 OK | [실행] §4 |
| **G-ID (a)** R-obs-b 61, 평탄화 기본 튜닝 | `MRS compare` IDENTICAL **61/61**, 기록 결정과 비경로 차이 0/61, 한 스텝 포착 16필드 단계 0과 61/61 동일 | [실행] §5.1 |
| **G-ID (b)** R-obs-b 61, 평탄화 U1+U3 | OLD(cf3ce37) 재생과 action JSON 비경로 차이 **0/61**, 한 스텝 포착 OLD·단계 0과 61/61 동일, compare IDENTICAL 61/61 | [실행] §5.2 |
| **G-ID (c)** SDMPC 결정 재생 5회 | S1 1800·3600·6300, S0e 1800·3600 모두 녹색·offset·action_csv·action_controls·목적값(선택·유지)과 **tangent 결정론 계수(operations·event_counts)** 가 기록과 같음. `action_contract`만 다름(알려진 VSL 100/110 혼재, 기록도 같음) | [실행] §5.3 |
| provenance | b2 쪽 모든 산출물(포착 160, SDMPC 5)이 트리 W·HEAD `cf3ce37`·dirty 16·`worktree_diff_sha256` `9d577731…`·어댑터 `7d42df08`·튜닝 `d4327cbf`/`f137f711` 한 조합. 체인 BEGIN과 ALLDONE의 diff sha가 같음 | [실행] §5.0 |
| 금지 대상 무변경 | 런 폴더 3곳·frozen 2곳·OLD에 16:01 이후 새 파일 0, OLD `git status` 0줄 | [실행] §7 |

- 넘길 것은 §8에 적었습니다. 가장 중요한 것 둘입니다.
  1. U4-0 전에 쓴 추적 튜닝 245개는 새 어댑터에서 설치 단계에 멈춥니다(계획 §3·C-9가 받아들인 결과). 옛 튜닝 재생은 `name_former_defaults`를 명시적으로 불러야 합니다.
  2. 단계 4는 `install_lane_group_membership`의 `["internal"]` 제한을 "C3 세 키가 모두 있을 때"로 넓혀야 합니다(A:4295-4297).

---

## 1. 바꾼 것 (작업 트리, 커밋 안 함) [실행: `git status`, `git diff --stat`]

| 파일 | 내용 |
|---|---|
| A | 코드 기본값 4개를 필수 키로(§2.1), `install_lane_group_membership` 신설과 헤드 관측 반환 앞당김(§2.2), 도우미 `_required_config_number/_bool` |
| `W/evaluation/controllers/u40_former_defaults.py` (새 파일) | 옛 튜닝을 **일부러** 재생하는 곳이 옛 코드 기본값을 이름으로 붙이는 변환 `name_former_defaults` (§2.6, 계획에 없던 것). 재개 검토에서 `is_post_u40` 통과 규칙 추가(§2.8-1) |
| MC | `flatten_capacity_defaults`(의미 보존 평탄화)를 C9 `apply` 끝에 붙임. 재개 검토에서 seed `sustained` 전제 추가(§2.8-2) |
| `config_n31_v2.json` / `_urban_b1.json` / `_urban_b1_u1u3.json` | 생성기 재생성: `82688d2f → d4327cbf`, `0f78bfa6 → ae8f4940`, `f88d05f1 → f137f711` |
| `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py` (새 파일) | U4-0 단위 시험 14개 (§3; 재개 검토에서 2개 추가) |
| `tests/test_n31_generators.py`, `tests/test_n31_urban_batch1.py` | C9 차이 목록에 U4-0 18경로 추가, 합성 튜닝에 새 필수 키 한 줄 |
| `diagnostics/probe_model_area_integration.py`, `sdmpc_n31_20260924/repin_scenario_v2.py`, `diagnostics/test_{head_service_resources,native1083_signal_authority,link_predictor,projection_support_receiver_turns,runtime_setup}.py` | sha 핀된 옛 튜닝을 불러오는 자리에서 `name_former_defaults` 호출 (각 1~3줄) |

- 원래 줄바꿈을 보존했습니다. `test_head_service_resources.py`(CRLF·LF 혼재)와 `test_projection_support_receiver_turns.py`(CRLF 줄)는 바이트 단위로 고쳐 diff가 3~4줄입니다.
- `git diff --stat`: 14 파일, +231 / −73. 새 파일 2개(untracked, 101줄·386줄).
- 최종 작업 트리 식별값 [실행 `H/_prov.py`]: `worktree_diff_sha256` = `9d5777314743d8e98a66712a96ff64b88b2a5d4e09473a513c2a5830d0a7ac72`(추적 diff + 새 파일 2개), 어댑터 `7d42df08…`, config `d4327cbf`·`ae8f4940`·`f137f711`. §4의 스위트와 §5의 G-ID는 모두 이 값에서 돌았습니다.

---

## 2. 항목별

### 2.1 코드 기본값 → 명시 키 (계획 §4.1-1, `[검토 C-8]`)

| 키 | 옛 코드 (cf3ce37) [읽음] | 새 코드 | 필수가 되는 조건 | n31 세 config 값 |
|---|---|---|---|---|
| `urban.ramp.gate_onramp_queue_capacity_veh_h` | A@cf3ce37:3391 `_as_float(…, 1800.0)` | A:3392 `_required_config_number` | 게이트 on-ramp 큐가 실제로 남았을 때(`kept` 비어 있지 않음) | `1800.0` |
| `urban.capacity.equivalent_uniform_veh_h` | A@cf3ce37:3832 `_as_float(…, 600.0)` | A:3802 (per_lane 판정 직후) | `per_lane` 켜짐 | `330.0` (그대로) |
| `urban.capacity.perimeter_include_boundary_out` | A@cf3ce37:3874 `section.get(…, True)` | A:3872 `_required_config_bool` (JSON bool만) | perimeter 모드가 `resolved`/`all` | `true` |
| `urban.capacity.lane_group_kinds` | A@cf3ce37:4351 `… or ["internal"]` (seed "sustained" 부작용) | A:4261-4311 `install_lane_group_membership` | 헤드 관측 켜짐 | `["internal"]` |

- 도우미: A:4231 `_required_config_number`(양의 유한수, bool 거부), A:4242 `_required_config_bool`. 없으면 `"<절>.<키> is required (its former code default is no longer implied)"`.
- 값은 옛 기본값과 **같은 타입·같은 값**입니다(§2.7 평탄화 diff 검사). 반환값은 `float(…)`라 옛 `_as_float`와 비트가 같습니다.
- `lane_group_kinds`의 코드 기본값은 **헤드 경로에서만** 없앴습니다. 헤드 관측이 꺼진 옛 경로(A:4455)는 `or ["internal"]`를 그대로 가집니다. 그 경로를 쓰는 추적 튜닝 65개 때문에 격리하지 않았기 때문입니다(§2.4, §2.8-5).

### 2.2 `_LG_KINDS`·`_LTO`·`_SUS_SIGS` 설정 분리 (계획 §4.1-2, `[검토 C-8]`)

- **옛 구조** [읽음 A@cf3ce37:4230-4435]: `install_measured_movement_capacity`가 씨앗 계산(seed 분기) 전체를 돈 **뒤** 헤드 관측이면 반환했습니다. 씨앗 값은 버려지고, 남는 효과는 `seed: "sustained"` 분기의 전역 설정(`_LG_KINDS`·`_LTO`·`_SUS_SIGS`·`_SUS_LANES`)뿐이었습니다.
- **새 구조**
  - A:4359-4366: `measured` 판정 직후, 헤드 관측이면 `install_lane_group_membership(cfg, tuning)`을 명시 호출하고 곧바로 `observe(…)`로 반환합니다. 넘기는 인자(`base_caps`, 계획, `_distribute_lane_group_capacity_to_movements`, 옵션)는 옛 반환과 같습니다.
  - 그래서 헤드 경로는 옛 키(`seed`, `decay`, `sustained_json`, `distribute`, `fallback`, `update` …)를 **하나도 읽지 않습니다**. 단위 시험이 읽힌 키를 기록해 `{head_observation, measured, lane_group_kinds}`뿐임을 확인합니다(§3).
  - A:4261 `install_lane_group_membership`
    - `lane_group_kinds` 필수. 비어 있지 않은 서로 다른 문자열 목록이어야 하고, 런타임에 없는 kind(`on_ramp`)는 오류입니다(A:4255 `LANE_GROUP_RUNTIME_KINDS`).
    - `["internal"]` 밖의 값은 **C3 세 키가 필요하다**는 오류로 거부합니다(`[검토 C-7]`, A:4257 `LANE_GROUP_C3_KEYS`). C3 코드가 단계 4부터라 지금은 `["internal"]`만 허용합니다. 단계 4에서 "C3 세 키가 모두 있을 때"로 넓힙니다.
    - `detector_mapping_json` 필수. 옛 코드처럼 적재 오류를 삼키지 않습니다(파일 없음 → `OSError`, `link_to_origins` 없음 → `ValueError`).
    - `_SUS_SIGS`·`_SUS_LANES`는 **비웁니다**(적재하지 않음, §2.3). 전역 이름은 그대로 둡니다. tangent 요청이 `_`+대문자 전역을 나르기 때문입니다(`sdmpc_tangent.py:25-26`).
    - 결정 메타데이터에 아무것도 쓰지 않습니다(키 없음 비트 동일).
- **헤드 관측이 꺼진 옛 경로는 코드가 그대로입니다.** 옛 `sustained` 분기의 전역 설정 줄(A:4452-4456)도 남아 있고 주석만 더했습니다.
  - `W/diagnostics/test_signal_observation_window_patch.py:197-212`는 이 함수에서 `head_observation`이 들어간 `if` 두 개를 지우면 커밋 109afee의 원본 AST와 같아야 한다고 단언합니다. 새 헤드 `if`도 조건식에 `head_observation`을 넣어 이 증명이 계속 성립하게 했고, 시험이 통과합니다(§4, `u40_extra`).

### 2.3 `_SUS_SIGS` 대체 계수 (계획 §4.1-2 (i)→(ii)) [실행]

- 방법: `H/u40_probe.py`가 `_distribute_lane_group_capacity_to_movements`를 감싸, 호출자의 `groups`에 신호가 없는 (링크, 현시) 항목을 세고, 그중 `_SUS_SIGS` 대체로만 신호를 얻는 항목과 그 뒤 구성원을 찾은 항목을 셉니다. OLD 트리(cf3ce37)에서 돌렸습니다.

| 상태 집합 (OLD 트리, 튜닝) | 상태 | distribute 호출 | 추정 항목 | `groups`에 신호 없는 항목 | `_SUS_SIGS` 대체 | 대체 뒤 구성원 찾음 | 반환 뒤 옛 코드 호출 (3함수) |
|---|---|---|---|---|---|---|---|
| R-obs-b 설치까지, 기본 `82688d2f` (`old_base_inst`) | 61 (1–9000) | 12,869 | 15,603 | 0 | 0 | 0 | 0 / 0 / 0 |
| S1 결정 상태 설치까지, U1+U3 `f88d05f1` (`old_s1_inst`) | 19 (900–9000, 450 간격) | 4,009 | 5,059 | 0 | 0 | 0 | 0 / 0 / 0 |
| S0e 결정 상태 설치까지, 기본 (`old_s0e_inst`) | 19 (같음) | 4,009 | 5,069 | 0 | 0 | 0 | 0 / 0 / 0 |
| R-obs-b 전체 결정, U1+U3 (`old_u1u3`) | 61 | 12,869 | 15,548 | 0 | 0 | 0 | 0 / 0 / 0 |

- 모든 OLD 포착의 provenance: `D:/VISSIM-merge/sim3-n31-urban`, `cf3ce374`, dirty 0, 어댑터 `2215d163` [실행 `S1/probe/old_*/T*.json`].
- 설치 직후 전역 크기(OLD, 모든 상태 같음): `_LG_KINDS` 1, `_LTO` 1,071, `_SUS_SIGS` 68, `_SUS_LANES` 107.
- 전체 결정(`old_u1u3`)의 distribute 호출 수가 설치까지만 돈 것(`old_base_inst`)과 같습니다(12,869). 이 함수는 **설치에서만** 불립니다. 예측·후보 평가·tangent는 부르지 않습니다.

- 구조상 이유 [읽음]: 두 호출자(SHO.install `signal_head_observation.py:188-189,198,254`, HSR.observe `head_service_resources.py:101,104`)가 넘기는 추정 키는 모두 같은 `physical_groups` 기하에서 나오고, `groups`도 그 기하의 모든 (링크, 현시)에 `stopline_link`와 비지 않은 `signal`(`"SC" + sc`)을 줍니다. 대체 줄(A:4669-4671)은 `sigs`에 **없는** 링크만 더하고, 배분은 추정 키의 링크로 `sigs.get(link)`만 봅니다(A:4679). 그래서 헤드 경로에서는 튜닝과 상관없이 `_SUS_SIGS`가 결과에 닿을 수 없습니다. 계수 0은 이를 확인합니다.
- **판정 (ii):** 헤드 경로는 `_SUS_SIGS`를 적재하지 않고, 세 config에서 `sustained_json`을 뺐습니다.
  - 옛 경로(헤드 관측 꺼짐)의 `_SUS_SIGS` 대체 줄은 남겼습니다. 그 경로는 아래 §2.4대로 격리 조건이 안 됩니다. 추적된 어떤 JSON도 `sustained_extra_groups`(대체가 실제로 필요한 유일한 생산자)를 이름으로 갖지 않습니다 [실행: `git grep`, 재개 뒤 다시 확인] — 참고로만 적습니다.

### 2.4 죽은 분기 격리: **하지 않음** (계획 §4.1-3 조건 불충족) [실행 `S1/pre/config_scan.json`]

- 방법: `H/scan_capacity_configs.py`가 추적된 `*.json` 전부(2,815개)를 읽고, `extends` 사슬을 어댑터와 같은 규칙(A:700-719)으로 풀어 튜닝 358개를 찾았습니다. 해석기 두 개는 쓰지 않았습니다.
- 결과
  - `measured` 켜짐 152, 헤드 관측 켜짐 87.
  - **옛 경로가 실제로 도는 튜닝(`measured` 켜짐 + 헤드 관측 꺼짐) 65개.** 폴더별: `evaluation/configs` 40(`h_METER_SAT_*` 등), `diagnostics` 13, `diagnostics/area_candidate_configs` 4, `contract_observer_off_configs_v3` 4, `com_execution_equivalence` 2, `diagnostics/fixtures` 2.
  - 이들의 씨앗/배분 모드: `sustained`+`lane_group`+`geometric`+`queued_ewma` 56(그중 `est_cap_geometric` 14), `observed`+`lane_group` 3, `plant`/`geometric`/기본 6.
- 계획 조건("하나라도 있으면 격리하지 않고 표로 남긴다")에 따라 A:4367 이하(온라인 갱신·fallback·observed/sustained 씨앗, 도우미 `_approach_topology`·`_measured_green_sec_by_link`·`_distribute_group_capacity_to_movements`)를 **격리하지 않았습니다.** `_superseded_20260928/`은 만들지 않았습니다.
- 대신 n31 튜닝(헤드 관측 켜짐)에서는 이 코드가 한 번도 돌지 않음을 계수로 보였습니다: 위 표의 `legacy_after_return` 세 함수 호출 0.

### 2.5 죽은 키 제거 (계획 §4.1-4)

- 세 config의 `urban.capacity`에서 15개를 뺐습니다(CFG:7822-7839, code_map §3.4 DEAD 행): `seed, observed_clip, seed_missing_frac, queued_links_json, unqueued_geometric_frac, distribute, fallback, fallback_frac, decay, sustained_json, sustained_stat, sustained_min_windows, update, ewma_alpha, queued_stopped_min`.
- `sustained_json`: §2.3 (ii) 판정 뒤에 뺐습니다.
- `decay`: 옛 코드에서는 헤드 반환 전(A@cf3ce37:4269)에 **읽기만** 했습니다. 쓰는 곳은 반환 뒤 `carried = decay × …`뿐인데, 반환 뒤 코드 호출이 0입니다(§2.3 표 `legacy_after_return`). 새 코드는 헤드 경로에서 읽지도 않습니다.
- 헤드 관측이 꺼진 튜닝에서는 이 키들이 여전히 살아 있으므로 코드에서 지우지 않았습니다(§2.4).

### 2.6 계획에 없던 것: 옛 튜닝 재생용 변환 `u40_former_defaults` [실행]

- **문제:** 필수 키로 바꾸자 기존 스위트에서 새 실패가 생겼습니다(첫 실행 `S1/suites_r1`).
  - `test_head_service_resources` 16 errors, `test_shared_service_pool` 25 errors, `test_repin_scenario_v2::test_configure_runtime_accepts_the_v2_pack_like_the_fcb_pack` 1 failed. 모두 `perimeter_include_boundary_out is required`.
  - 원인: 이 시험과 repin 도구가 쓰는 튜닝(`area_candidate_configs/n7_area_beta0.json`, `contract_candidate_configs_v2/n7_area_beta0.json`, OBS1, `scenario/config_n31_v2.base.json`)은 옛 튜닝이고, 파일 sha가 여러 매니페스트에 핀돼 있습니다(`area_candidate_configs/manifest.json:140`, `area_checkout_bytes_verification.json:25` 등) [실행 grep]. 그래서 평탄화할 수 없습니다.
  - 계획 §4.1-1 "필수 키"와 §4.0-2 "기존 스위트 통과"가 여기서 충돌합니다.
- **선택:** 런타임은 필수 키 그대로 두고(fail-closed), **옛 튜닝을 일부러 재생하는 자리**만 옛 기본값을 이름으로 붙이게 했습니다.
  - `W/evaluation/controllers/u40_former_defaults.py:70` `name_former_defaults(tuning)`: 어댑터가 그 기본값을 쓰던 조건(위 §2.1 표)일 때만, 키가 없을 때만, 옛 값(600.0 / True / 1800.0 / `["internal"]`)을 붙입니다. 순수 함수입니다.
  - 재현할 수 없는 옛 거동은 거부합니다: 헤드 관측 + seed가 `sustained`가 아님(옛 코드는 전역을 비워 두었음. 해당 튜닝 3개: `com_execution_equivalence/{ramp,signal}_profile.json`, `control_area_contract_overlay.json`), 읽을 수 없는 `detector_mapping_json`.
  - **U4-0 뒤에 쓴 튜닝은 채우지 않습니다**(재개 검토에서 추가, §2.8-1). `:60` `is_post_u40`가 참이면 받은 그대로 돌려줍니다. 그래서 그런 튜닝에 빠진 필수 키는 런타임에서 실패합니다.
  - 어댑터는 이 모듈을 부르지 않습니다. MC의 평탄화 값도 이 모듈에서 가져옵니다(MC:186-191). 값의 출처가 하나입니다.
  - 부르는 곳(7곳): `probe_model_area_integration.py:76-77`(기록된 런 상태를 다시 푸는 진단 공용 로더), `repin_scenario_v2.py:1346-1347`(configure-check의 두 팔: OBS1과 C9 이전 시나리오 base), 시험 5개 파일의 튜닝 적재 줄.
- **남는 영향 [실행 `config_scan.json`]:** 추적된 튜닝 245개가 새 필수 키 가운데 하나 이상을 이름으로 갖지 않습니다. 이들을 새 어댑터로 그대로 돌리면 설치에서 멈춥니다(계획 §3·C-9가 받아들인 결과). 시험이 아닌 옛 도구 3개(`diagnostics/review_unresolved_projection_support.py:38`, `scripts/offline_harness_20260904.py:17`, `scripts/probe_far_components_20260901.py:29`)는 고치지 않았습니다. 필요하면 같은 한 줄을 넣으면 됩니다.

### 2.7 평탄화와 diff 검사 (계획 §3 `[검토 C-9]`, §4.1-5)

- MC:238 `flatten_capacity_defaults(doc)`: C9 `apply()` 끝(MC:309)에서 부릅니다. 기본·b1·U1+U3 세 config가 모두 이것을 거칩니다.
  - 전제를 검사하고 어긋나면 거부합니다: `measured` true + 헤드 관측 켜짐(죽은 키가 죽은 조건), **seed `sustained`**(재개 검토에서 추가, §2.8-2), `per_lane` + perimeter 모드 + `equivalent_uniform_veh_h`, `leg_split` + `gate_onramp_queue`, `detector_mapping_json`, 15개 옛 키가 모두 있음, 새 키가 아직 없음.
  - 새 키는 읽기 좋은 자리에 넣습니다: `perimeter_include_boundary_out`는 `_why_perimeter` 뒤, `lane_group_kinds`는 `measured` 뒤, `gate_onramp_queue_capacity_veh_h`는 `gate_onramp_queue` 뒤.
  - `_n31_note`와 `_why_perimeter` 문구는 바꾸지 않았습니다(아래 기계 검사가 "바뀐 키 0"을 요구).
- **기계적 diff 검사** `H/flatten_diff_check.py` [실행 `S1/flatten_diff_check.json`]

| config | HEAD sha → 작업 sha | 지운 키 (죽은 키 목록 안) | 더한 키 (옛 기본값과 같은 타입·값) | 목록 밖 삭제 / 틀린 추가 / 값이 바뀐 키 / 순서 바뀜 | 판정 |
|---|---|---|---|---|---|
| `config_n31_v2.json` | `82688d2f → d4327cbf` | 15 | 3 | 0 / 0 / 0 / 0 | PASS |
| `config_n31_v2_urban_b1.json` | `0f78bfa6 → ae8f4940` | 15 | 3 | 0 / 0 / 0 / 0 | PASS |
| `config_n31_v2_urban_b1_u1u3.json` | `f88d05f1 → f137f711` | 15 | 3 | 0 / 0 / 0 / 0 | PASS |

- 재개 뒤 최종 diff(`worktree_diff_sha256` `9d577731…`)에서 다시 돌린 결과입니다. 처음 결과(16:07, 수정 전 diff)는 `S1/_prev_diff_1705/flatten_diff_check_1607.json`에 두었고 판정이 같습니다.
- 더한 세 키의 옛 기본값 근거: `lane_group_kinds` = A@cf3ce37:4351 `or ["internal"]`(seed `sustained` 분기, n31 세 config 모두 seed `sustained` [읽음 `git show cf3ce37:…`]), `perimeter_include_boundary_out` = A@cf3ce37:3874 `section.get(…, True)`, `gate_onramp_queue_capacity_veh_h` = A@cf3ce37:3391 `_as_float(…, 1800.0)`.

- 생성기 `--check` 세 개가 새 바이트를 재현합니다(§4 `check00-02`).

### 2.8 재개 검토: 남아 있던 편집을 계획에 대어 본 결과 (2026-09-28 19:13 이후)

세션 한도로 18:05에 멈춘 편집을 다시 읽고 계획 §2·§4.1과 대조했습니다. 결함 셋을 고쳤고, 나머지는 그대로 둘 근거를 적습니다.

| # | 본 것 | 판정 | 조치 |
|---|---|---|---|
| 1 | 변환 `name_former_defaults`가 "옛 튜닝을 일부러 재생하는 곳"에만 쓰이는가, 실운영 경로에서 빠진 키를 가리지 않는가 | **실운영 경로는 안전, 공용 로더는 결함** | 아래 |
| 2 | 평탄화 `flatten_capacity_defaults`의 전제 검사 | **결함**: seed를 보지 않았음 | seed `sustained` 필수로 추가 |
| 3 | 하네스 provenance가 "지금의 diff"를 식별하는가 | **결함**: porcelain 요약은 이미 수정된 파일의 내용 변화를 못 봄 | `worktree_diff_sha256` 추가, b2 쪽 G-ID 전부 재실행 |
| 4 | 어댑터 헤드 경로가 옛 경로와 같은 입력으로 같은 결과를 내는가 | 이상 없음 | §2.2·§2.3 구조 논증 + §5·§6 실행 증거 |
| 5 | 옛 경로(A:4455)의 `or ["internal"]` 코드 기본값 | 계획대로 남김 | §2.4 조건 불충족(옛 경로 65 튜닝). 헤드 경로에는 기본값 없음 |

1. **변환의 범위** [실행 grep, 읽음]
   - 실운영 경로: 러너 → 어댑터 `__main__` → `runtime_setup.configure_runtime`은 이 모듈을 import하지 않습니다. `evaluation/`·`vendor/` 아래 `.py` 222개 가운데 이 이름을 담은 파일은 모듈 자신뿐입니다. 이것을 새 시험 `test_the_runtime_never_imports_it`로 고정했습니다. 옛 튜닝을 실운영에 넣으면 설치에서 멈춥니다.
   - 시험 5곳과 repin configure-check는 각각 특정 옛 파일(sha 핀)을 불러옵니다. 의도된 옛 튜닝 재생입니다.
   - **결함:** 공용 로더 `probe_model_area_integration._build_projected`는 받은 config 무엇에든 변환을 적용했습니다. 지금 호출자 109개는 모두 `diagnostics/` 아래의 기록 런 재생이고, 하네스(H)와 n31 도구는 이 로더를 쓰지 않습니다 [실행 grep]. 그래도 U4-0 뒤에 쓴 튜닝이 필수 키 하나를 빠뜨린 채 이 로더로 들어오면, 옛 기본값이 조용히 채워져 오프라인 진단은 통과하고 실운영 설치는 실패합니다.
   - **수정:** `is_post_u40`(u40_former_defaults.py:60)를 더했습니다. U4-0 전 추적 튜닝 358개 가운데 `perimeter_include_boundary_out`·`gate_onramp_queue_capacity_veh_h`를 쓴 것은 0개이고, `lane_group_kinds`를 쓴 12개(`h_METER_SAT_*`, `h_V2TEST`)는 모두 헤드 관측이 꺼져 있습니다 [실행 `S1/pre/config_scan.json`, cf3ce37 상태에서 잰 것]. 그래서 이 셋 가운데 하나라도 이름으로 가진 튜닝(`lane_group_kinds`는 measured 헤드 관측과 함께일 때)을 U4-0 뒤 튜닝으로 보고, **손대지 않고** 돌려줍니다.
   - 시험 `test_never_completes_a_post_u40_tuning`: 평탄화 config에서 필수 키를 하나씩 지우면 변환이 그대로 돌려주고, 해당 설치 함수가 `<키> is required`로 실패합니다(4키).
   - 남는 한계 [추론]: U4-0 뒤에 쓴 튜닝이 세 표지 키를 하나도 쓰지 않으면(예: perimeter off, 게이트 큐 off, 헤드 관측 off인 per_lane 튜닝) 옛 튜닝과 구별할 수 없어 `equivalent_uniform_veh_h`가 600으로 채워질 수 있습니다. 이 경우도 공용 로더를 거친 진단에서만이고, 실운영은 실패합니다.
2. **평탄화 전제** [읽음, 실행]
   - 옛 헤드 경로에서 `_LG_KINDS`·`_LTO`는 seed가 `sustained`일 때만 채워졌습니다(A@cf3ce37:4350-4358). 다른 seed면 `_LTO`가 비어 구성원 판정이 origin 맵만 썼습니다. 새 코드는 늘 `_LTO`를 적재하므로, seed가 다른 튜닝을 평탄화하면 의미가 조용히 바뀝니다.
   - n31 세 config는 모두 seed `sustained`라 출력은 그대로입니다: `--check` 세 개가 `d4327cbf`·`ae8f4940`·`f137f711`을 다시 냈습니다. 시험 `test_flattening_refuses_a_tuning_it_would_change`에 seed `plant` 경우를 더했습니다(7가지).
3. **provenance** [실행]
   - 18:05에 멈춘 체인의 b2 포착(N1 61, N2 49)은 `worktree_status_sha256`(porcelain 요약)과 어댑터 sha만 적었습니다. 이 둘은 이미 수정된 파일의 내용이 다시 바뀌어도 같습니다.
   - 위 1·2를 고치면서 diff가 바뀌었으므로, 그 결과는 "지금 diff" 증거가 될 수 없습니다. `S1/_prev_diff_1705/`로 옮기고(참고용, 값은 §5에서 대조) b2 쪽 G-ID를 **모두 다시** 돌렸습니다.
   - `H/_prov.py`에 `worktree_diff_sha256`을 더했습니다: `git diff --binary HEAD` + 추적 안 된(무시 아님) 파일의 경로·바이트. 체인은 BEGIN과 ALLDONE에서 이 값을 기록합니다.
   - OLD 트리 포착(P1·P2·P3)은 그대로 씁니다. 기록된 provenance가 OLD·`cf3ce374`·dirty 0·어댑터 `2215d163`·튜닝 `f88d05f1`/`82688d2f`이고, OLD는 지금도 깨끗합니다(`git status` 0줄, 새 diff sha = 빈 입력의 sha, 16:01 이후 새 파일 0 [실행 §7]). 깨끗한 트리에서는 porcelain 요약만으로도 내용이 HEAD와 같음이 정해집니다.
4. **헤드 경로 동치** [읽음]: 옛 코드가 반환 전에 한 일은 (a) 씨앗 계산(지역 변수만, `cfg` 불변), (b) 이전 action·증거 JSON 읽기(읽기만), (c) seed `sustained` 분기의 전역 네 개 설정뿐입니다. 새 코드는 (c) 중 `_LG_KINDS`·`_LTO`를 같은 파일·같은 순서로 채우고 `_SUS_*`는 비웁니다. `_SUS_*`가 헤드 경로 결과에 닿지 않음은 §2.3 구조 논증과 계수 0으로 보였습니다. 부수 효과로 결정마다 이전 action JSON(약 58 MB)을 한 번 덜 읽습니다.
5. 그 밖에 확인한 것: `equivalent_uniform_veh_h`·`perimeter_include_boundary_out` 읽기가 앞당겨져 `share`가 비거나 perimeter 파일이 없어도 키를 요구합니다. fail-closed 방향이고, 변환은 같은 조건(per_lane / perimeter 모드)에서 채우므로 옛 튜닝 재생과 어긋나지 않습니다.

---

## 3. 단위 시험 (계획 §5.1 U4-0 행) [실행]

`W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py` — 14개, 모두 통과 [실행 `S1/s3/tests/n31_batch2.txt`].

| 묶음 | 시험 |
|---|---|
| RequiredKeyTests | `equivalent_uniform_veh_h`(per_lane 켜짐에서 누락·0·음수·문자열·bool·NaN 거부, 꺼지면 불필요), `perimeter_include_boundary_out`(누락·비 bool 거부, off면 불필요, true/false 효과), `gate_onramp_queue_capacity_veh_h`(큐가 남으면 필수, 1800.0이 float로 설치) |
| LaneGroupMembershipTests | kind 누락·빈 목록·중복·비문자열 거부, `on_ramp` 거부, `["internal"]` 밖은 C3 오류; `detector_mapping_json` 누락·없는 파일·`link_to_origins` 없음 거부; **옛 `sustained` 부작용과 같은 전역**(옛 경로 코드를 cf3ce37 capacity 절로 실제로 돌려 기준을 만들고, 세 config 모두 `_LG_KINDS`·`_LTO` 값과 순서가 같고 `_SUS_*`는 빈 것); 헤드 경로가 읽는 키가 `{head_observation, measured, lane_group_kinds}`뿐이고 옛 키에 독(잘못된 값)을 넣어도 영향 없음 |
| FormerDefaultsTests | `name_former_defaults`가 경로가 도는 곳에만 옛 값을 붙이고 순수하며, 평탄화 튜닝은 그대로; 생성기 평탄화와 같은 값; 재현 불가(seed plant, 읽을 수 없는 매핑)는 거부; **(재개 추가)** 필수 키 하나를 뺀 U4-0 뒤 튜닝은 채우지 않고 돌려주며 런타임이 `<키> is required`로 실패(4키); **(재개 추가)** `evaluation/`·`vendor/`의 어떤 모듈도 이 변환을 import하지 않음(정적) |
| GeneratorTests | 커밋할 세 config가 평탄화돼 있음(값·자리), 평탄화가 의미를 바꿀 튜닝을 거부(7가지, seed `plant`는 재개 추가), 세 config = 생성기 출력 |

---

## 4. 기존 스위트 (단계 0 기준선 대비) [실행 `S1/s3/tests/summary.json`, `S1/s3/fixtures/summary.json`, 대조 `S1/suite_compare_s3.json`]

- **최종 실행 `S1/s3`**: 재개 검토의 수정(§2.8)을 넣은 뒤, 포착·재생을 시작하기 **전에** 19:26–19:45에 돌렸습니다. 시작·끝의 `worktree_diff_sha256`이 `9d577731…`로 같고, 그 뒤 G-ID 체인도 같은 값에서 돌았습니다(§5).
- 실행 조건은 단계 0과 같습니다(한 번에 한 프로세스, BELOW_NORMAL, 스레드 1, `nbc_b2i`, 금지 시험 제외).
- **판정: 새 실패·새 오류 0, 통과 수 감소 0.** `H/compare_suites.py`가 두 루트에 모두 있는 68개 실행(스위트 38 + fixture 30)마다 전체 로그의 `FAILED`/`ERROR` 시험 id 집합, 종료 코드, 통과·실행 수를 단계 0(`S0/tests`, `S0/fixtures`)과 비교했습니다. 회귀 0, 개선 0, 사라진 실행 0입니다.

| 스위트 | 단계 0 | 단계 1 최종 (`S1/s3`) |
|---|---|---|
| n31 (12 파일) | 167 OK (skip 3) | 167 OK (skip 3) |
| n31_observe_pipeline / t6_runner / parity / ad_smoke | 4 / 6 / 5 / 8 OK | 같음 |
| tools / obs / obs_head / pyt | 60 OK / 29 OK / 31 passed / 61 passed | 같음 |
| diag11 (한 번에) | 32 failed, 69 passed, 4 skipped, 15 errors | 같음 (같은 id) |
| diag11 파일별 | head_service_resources 16, head_free 7, shared_service_pool 25, sdmpc_aggregate 5, urban_flow_accounting 12 passed, legsplit 4 skip, 나머지 5개 파일은 이전부터 실패 | 같음 (같은 id) |
| extra_known | 7 failed, 13 passed, 4 errors | 같음 |
| fixture (core + route v1/v2, 30 실행) | sc1004 6, RCC 14, head_service_resources 16, shared_service_pool 25, dynamic_area_routes 7, native1083 v2 6 passed … | 같음 |
| 생성기 `--check` 15개 | 전부 0 | 전부 0 (config 세 개는 새 sha `d4327cbf`·`ae8f4940`·`f137f711`) |
| **새로 더한 것** `n31_batch2` | – | 14 OK |
| **새로 더한 것** `u40_extra` (`test_signal_observation_window_patch`, `test_runtime_setup`) | (단계 0에 없음) | 11 passed, 3 skipped (AST 증명 포함) |

- 변환(§2.6)을 쓰는 시험 파일은 모두 통과 쪽에 있습니다: head_service_resources 16, shared_service_pool 25, native1083 v2 6, pyt(repin configure-check 포함) 61, u40_extra(`test_runtime_setup`) 11.
- 변환을 쓰지만 스위트 목록에 없는 시험 두 파일(`test_link_predictor.py`, `test_projection_support_receiver_turns.py`)은 22:3x에 따로 돌렸습니다 [실행 `S1/s3/extra2/*.txt`]. fixture 없이도, core + route v2 fixture로도 결과가 같습니다: 9 passed, 1 failed, 4 errors.
  - 실패·오류 다섯은 모두 트리에 없는 과거 run 입력 때문입니다(`evaluation/runs/codex_nc_s13_6056c94_20260909_retry/…/state_000900.json`, `evaluation/runs/codex_area_beta0_s13_20260910/…/state_001050.json`). 두 입력 모두 변환을 부른 **뒤**의 단계에서 없다고 나옵니다.
  - 통과한 9개 가운데 `N7ReplayTests`는 `setUpClass`에서 변환한 옛 튜닝(`n21_n7_20260908.json`)으로 런타임을 설치합니다. 변환이 없으면 이 설치가 필수 키 오류로 멈춥니다 [추론, §2.6과 같은 원인].
  - 두 파일은 단계 0 기준선 목록에 없어서 "회귀 0" 비교에는 넣지 않았습니다. 실행 전후 `git status`는 같았습니다.
- 시험이 다시 쓴 추적 파일(`head_service_resources_canonical_validation.json`, `route_input_fixture_validation{,_v2}.json`, `road_support_336_portable_regression.json`)은 하네스가 diff를 남기고 되돌렸습니다. 끝난 뒤 `git status`는 16줄(우리 변경만)입니다.
- 중간 실행: `S1/suites_r1`(변환 전, §2.6의 새 실패 42건), `S1/suites_r2`(하네스 사고로 중단), `S1/s2`(16:40–17:00, 재개 수정 전 diff; 같은 대조기로 회귀 0 `S1/suite_compare_s2.json`). 이들은 최종 판정에 쓰지 않았습니다.
- 하네스 사고 두 가지(단계 1 처음 시도)
  - 스위트가 도는 동안 시험 파일을 고쳤더니, 추적 파일 보호 장치가 그 편집을 "시험이 바꾼 파일"로 보고 되돌렸습니다(`S1/suites_r2/tests/diag11_tracked_*.diff`). 편집을 다시 넣고 처음부터 다시 돌렸습니다. 재개 뒤에는 스위트·재생 중에 트리를 건드리지 않았습니다.
  - `suites_r2`의 파일별 단계는 diff 파일 이름이 MAX_PATH를 넘어 중단됐습니다. `H/run_suites.py`의 diff 파일 이름을 sha 앞 10자리로 줄였습니다.

---

## 5. G-ID (계획 §6.1)

### 5.0 방법과 provenance [실행]

- 체인 `H/stage1_chain.py`(한 번에 하나, BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=…/nbc_b2i`).
  - OLD 쪽 P2·P3·P1은 16:02–17:04에 돌았고(§2.8-3 조건으로 재사용), b2 쪽 N1–N4는 재개 뒤 19:45:55–22:26:26에 모두 새로 돌렸습니다.
  - 체인 로그: `19:45:55 BEGIN … dirty=16 diff_sha256=9d577731… adapter=7d42df08 … tuning_u13 (f137f711) tuning_def (d4327cbf)`, `22:26:26 ALLDONE diff_sha256=9d577731… (same at BEGIN)`.
  - 22:14에 N4 도중 체인을 제가 한 번 멈추고 N4만 다시 띄웠습니다. P10 워크플로의 v3c1 SDMPC 재생(약 10분씩)이 끝나기를 기다리느라 설치까지만 도는 짧은 단계(약 22 s)가 멈춰 있었기 때문입니다. 그때 제 자식 프로세스는 없었고, CPU 부하는 20 논리 코어 중 7%, VISSIM 0개였습니다. 다시 띄울 때 `--no-wait-foreign`(대기 생략)만 더했고, 이미 끝난 6상태는 건너뛰었습니다. 이 사실은 `S1/chain.log`에 NOTE로 남겼습니다.
- **provenance 검사** [실행 `S1/stage1_results.json`, 각 `T*.json`·`*.summary.json`]: b2 포착 160개(`b2_base` 61, `b2_u1u3` 61, `b2_s1_inst` 19, `b2_s0e_inst` 19)와 SDMPC 요약 5개가 모두 아래 한 조합입니다.
  - 트리 `D:\VISSIM-merge\sim3-n31-urban-b2`, HEAD `cf3ce374`, dirty 16, `worktree_diff_sha256` `9d5777314743…`, 어댑터 `7d42df08…`
  - 튜닝: 기본 `d4327cbf…`, U1+U3 `f137f711…`. SDMPC 재생의 action JSON도 이 경로·sha를 적었습니다(S1 → `config_n31_v2_urban_b1_u1u3.json` `f137f711`, S0e → `config_n31_v2.json` `d4327cbf`).
- OLD 쪽 기준(P1·P2·P3)은 OLD `cf3ce374`, dirty 0, 어댑터 `2215d163`, 튜닝 `f88d05f1`/`82688d2f`로 기록돼 있고, OLD는 보고 시점에도 깨끗합니다(diff sha = 빈 입력의 sha).
- 이전 diff에서 나온 b2 결과(18:05에 멈춘 체인, `S1/_prev_diff_1705/`)는 판정에 쓰지 않았습니다. 참고로, 새 결과와 한 스텝 포착·설치 기록이 `b2_base` 61/61, `b2_u1u3` 49/49 같습니다.

### 5.1 (a) R-obs-b 61상태, 평탄화 기본 튜닝 `d4327cbf` [실행 `S1/probe/b2_base`]

| 검사 | 결과 |
|---|---|
| 종료 / 예측 상태 | 61/61 종료 0, `prediction.status ok` |
| `MRS compare` (derived, action_csv, action_controls, objective, action_contract) | **IDENTICAL 61/61**. objective 검사는 no-control이라 해당 없음(`None`), 단계 0 `b2base`와 같은 모양 |
| 기록 결정 대비 action JSON 비경로 차이 | 0/61 상태 |
| 한 스텝 포착 16필드(β, movement_meta, q0/o0/inv0, assign0, q1/o1/inv1, departures, routed_departures, greens, prediction_summary, offramp 분율, 큐 수, route_attr; route_attr는 U2가 꺼져 양쪽 모두 없음) vs 단계 0 `S0/capture/b2base` | 61/61 모두 같음 |
| 장부 | 최대 차이 8.61e-9, 실패 0 |
| 새 코드가 실제로 돌았나 | `install_lane_group_membership` 61회, `head_service_resources.observe` 61회, 반환 뒤 옛 코드 호출 0 |

### 5.2 (b) R-obs-b 61상태, 평탄화 U1+U3 `f137f711`: OLD 트리 재생 대 b2 트리 재생 [실행 `S1/probe/b2_u1u3` 대 `S1/probe/old_u1u3`]

| 검사 | 결과 |
|---|---|
| action JSON 전체 비교(트리·출력 경로 정규화) | **비경로 차이 0/61**. 다른 잎은 `run_provenance`의 sha 4종(어댑터·튜닝·state·실행 지문, 양쪽 사본 모두)과 벽시계 3종(`prediction/wall_sec`, `decision_wall_sec`, `prediction_wall_sec`)뿐. 키 유무 차이 0 |
| 한 스텝 포착 16필드 vs OLD `old_u1u3` | 61/61 같음 |
| 한 스텝 포착 16필드 vs 단계 0 `S0/capture/b2u1u3`(`b1_capture.py`) | 61/61 같음 |
| `MRS compare` vs 기록 결정 | IDENTICAL 61/61 (OLD도 61/61) |
| 기록 결정 대비 비경로 차이 | 61/61 상태에 있음. OLD도 같은 61상태. 기록 결정이 기본 튜닝이라 β 등이 다르기 때문(단계 0 §5.3과 같은 모양). 판정은 OLD 대 b2로 함 |
| 장부 | 최대 8.61e-9, 실패 0 (OLD와 같음) |

### 5.3 (c) SDMPC 결정 재생 5회 [실행 `S1/sdmpc/b2_*_T*.summary.json`, `replay_compare.json`]

- 도구: `H/sdmpc_replay.py` → `MRS.prepare`(복사 전용) → `W/…/replay_decision_n31.ps1 -Root W`. 런의 튜닝 경로가 W로 rebase돼 평탄화 config를 씁니다. 이전 action은 런 폴더에서 읽기만 합니다.
- 비교는 계획 §6.1 (c)대로 action_csv·action_controls·objective 세 검사, 녹색·offset, 그리고 과업 지시대로 tangent 결정론 계수입니다.

| 상태 (튜닝) | derived / csv / controls / objective | 녹색 / offset | 선택 목적값 (기록 = 재생) | 유지 목적값 | tangent 2개 `operations` (기록 = 재생) | `event_counts` primal·ties·discrete (도함수 1 / 2) | `action_contract` |
|---|---|---|---|---|---|---|---|
| S1 1800 (U1+U3) | ok ×4 | 같음 / 같음 | 460.9685165323024 | 462.7372813177537 | 13,662,852 / 13,810,195 | 8,505,198·368,622·639,987 / 8,561,165·372,634·668,616 | 다름 |
| S1 3600 (U1+U3) | ok ×4 | 같음 / 같음 | 491.4356825691444 | 493.5432636752482 | 12,123,157 / 11,962,967 | 7,850,416·335,580·630,241 / 7,778,513·336,378·630,972 | 다름 |
| S1 6300 (U1+U3) | ok ×4 | 같음 / 같음 | 357.44510216515835 | 359.3969080380441 | 11,114,385 / 11,336,611 | 7,708,419·341,303·583,778 / 7,841,131·350,859·588,650 | 다름 |
| S0e 1800 (기본) | ok ×4 | 같음 / 같음 | 468.49466951165346 | 470.22280722558446 | 14,089,170 / 13,851,387 | 8,672,874·400,211·676,779 / 8,572,328·394,225·672,062 | 다름 |
| S0e 3600 (기본) | ok ×4 | 같음 / 같음 | 490.13138414502527 | 491.4703575883558 | 12,058,005 / 11,964,315 | 7,893,041·345,923·589,949 / 7,825,408·344,739·610,284 | 다름 |

- 모든 행에서 `tangent_traces_equal True`이고 계수가 기록과 **정수까지 같습니다.** S1 1800·6300 계수는 단계 0 재생(cf3ce37 트리)과도 같습니다.
- S0e 기록 결정은 886a014 frozen 트리와 그 튜닝(`16c5f8bc`)으로 만들어졌습니다. 재생은 W의 평탄화 기본 튜닝(`d4327cbf`, 원래 `82688d2f`)을 씁니다. XREPLAY가 cf3ce37 기본 튜닝으로 이 두 상태를 재현한 것과 같은 구성입니다 [읽음 `xreplay/XREPLAY_RESULT.md` "재현 확인"].
- `action_contract`가 다른 이유는 다섯 모두 `vsl_speeds [100, 110]`(기대 110)입니다. action_csv가 기록과 같으므로 기록 action도 같은 성질이고, 단계 0·SC109_DIAG §4와 같은 정의로 제외했습니다.
- **action JSON 전체 비교** [실행 `H/analyze_stage1.py` `full_action_diff`]
  - 대 단계 0 재생(S1 1800·6300, 같은 W 트리의 리팩터 전 코드): 차이 잎 58·56개, 키 유무 차이 0. 모두 세 부류입니다.
    - `run_provenance` sha(어댑터·튜닝·state·실행 지문)
    - 시간 필드(`*_sec`, `seconds`, `wall_sec`)
    - 경로·설정 바이트에 민감한 요약값: `request_sha256`, 어댑터의 `transformed_source_sha256`, `frozen_context_token`·`response_token`·`reference_response_token`
  - 대 기록 결정(5개): 위 세 부류에 더해 frozen 경로 문자열과 경로를 키로 쓴 `transformed_source_sha256` 항목의 유무 차이뿐입니다. 값 필드(녹색, 목적값, local_costs, quantities, resource_summary, control_area, 도함수 값 등)의 차이는 0입니다.
  - 토큰 차이가 행동 차이가 아니라는 근거 [실행]: 같은 커밋(cf3ce37)인 기록 결정과 단계 0 재생 사이에서도 `response_token`·`frozen_context_token`·`request_sha256`이 이미 다릅니다(S1 1800: `515ad06b…` 대 `8fbe6d6f…`). 이 토큰들은 cfg·응답을 pickle한 바이트의 sha라서(`area_follower_objective.py:536-549`, :653) 트리 경로와 튜닝 바이트에 따라 바뀝니다 [읽음]. 이번 변경은 튜닝 바이트(키 15 삭제·3 추가)와 어댑터 전역 `_SUS_*` 내용을 바꿨으므로 토큰이 달라지는 것이 예상대로입니다 [추론].
- 벽시계(참고, 관문 아님): 결정 `decision_wall_sec` 재생 504–606 s(기록 424–586 s). 이 구간에 VISSIM은 0개였고 P10 재생 1개가 함께 돌았습니다. action JSON 크기는 기록보다 5.2–5.6 kB 작고(경로 문자열 길이), stdout 486–489 B입니다.

### 5.4 판정

| 관문 | 기준 (계획 §6.1) | 결과 |
|---|---|---|
| (a) | `MRS compare` IDENTICAL 61/61 | **통과** (61/61) |
| (b) | OLD 대 b2 action JSON 비경로 차이 0, 한 스텝 포착 바이트 동일 | **통과** (0/61, 61/61) |
| (c) | 결정 재생 5회가 기록과 녹색·offset 비트 동일, action_csv·action_controls·objective 동일 (+ 과업: 결정론 계수 동일) | **통과** (5/5) |

---

## 6. 설치 결과 동일성 (추가 증거) [실행]

설치 직후(`runtime_setup.configure_runtime` 반환 시점) OLD와 b2를 같은 상태·같은 튜닝 의미로 비교했습니다 [실행 `S1/stage1_results.json` `install`].

| 쌍 (OLD → b2) | 상태 | 설치 메타데이터 (경로 키 제외) | movement 용량 맵 | urban_movements | `_LG_KINDS` | `_LTO` | `_SUS_SIGS`/`_SUS_LANES` 크기 |
|---|---|---|---|---|---|---|---|
| R-obs-b 기본 (`old_base_inst` → `b2_base`) | 61 | 61 같음 | 61 같음 | 61 같음 | 61 같음 | 61 같음 | (68, 107) → (0, 0) |
| R-obs-b U1+U3 (`old_u1u3` → `b2_u1u3`) | 61 | 61 | 61 | 61 | 61 | 61 | (68, 107) → (0, 0) |
| S1 결정 상태 U1+U3 (`old_s1_inst` → `b2_s1_inst`) | 19 | 19 | 19 | 19 | 19 | 19 | (68, 107) → (0, 0) |
| S0e 결정 상태 기본 (`old_s0e_inst` → `b2_s0e_inst`) | 19 | 19 | 19 | 19 | 19 | 19 | (68, 107) → (0, 0) |

- 메타데이터에서 다른 키는 `native_phase_share_map_path`(트리 경로 문자열) 하나뿐입니다.
- `_LG_KINDS`·`_LTO`는 정렬한 정규 JSON의 sha로 비교했고 모두 같습니다. 단위 시험은 `_LTO`의 삽입 순서까지 같음을 따로 확인합니다(§3). tangent 요청이 이 전역을 나르기 때문입니다.
- b2 쪽 distribute 호출·항목 수(12,869/15,603, 4,009/5,059, 4,009/5,069, 12,869/15,548)가 OLD와 같습니다. `groups`에 신호 없는 항목 0, `_SUS_SIGS` 대체 0, 반환 뒤 옛 코드 호출 0입니다.

---

## 7. 안전 [실행]

- `find -newer S1/marker_stage1_start`(16:01:08), 22:30 이후 확인: 아래 여섯 곳 모두 새 파일 0개.
  - 런 폴더 `sdmpc31_v3b_nc_s31b`(R-obs-b), `sdmpc31_v3b_b1u13_s31`(S1), `sdmpc31_v3b_s31e`(S0e)
  - `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`
  - OLD `D:/VISSIM-merge/sim3-n31-urban` (`git status` 0줄, HEAD `cf3ce37`)
- W: HEAD `cf3ce37`, 브랜치 `claude/urban-batch2-20260928`, 커밋 없음. `git status` 16줄(수정 14 + 새 파일 2)이고 diff sha `9d577731…`가 스위트 전·체인 시작·체인 끝·보고 직전에 같습니다. 무시 대상인 `__tangentcache__`(SDMPC 재생)와 `.review-fixtures/`(fixture 스위트)에만 새 파일이 생겼습니다.
- 다른 브랜치·워크트리: `claude/repin-v3c1-20260928`(`5323faa`), `sim3-n31-v3c1`, `sim3-n31`, frozen은 어떤 명령에서도 쓰기 대상이 아니었습니다. v3c1 경로는 프로세스 목록에서 P10의 재생으로 **보이기만** 했습니다.
- VISSIM·cscript는 시작하지도 죽이지도 않았습니다. 제가 멈춘 프로세스는 제 체인 python 하나(22:14, 자식 없음)뿐입니다. 워치독·cscript·ps1 시험은 돌리지 않았습니다(`H/run_suites.py`의 제외 목록).
- 재생은 한 번에 하나였습니다. N4 재시작 전까지는 다른 재생 python이 있으면 기다렸고, 재시작 뒤 N4(설치까지만, 약 22 s씩)는 P10 재생 1개 옆에서 돌았습니다(부하 7%, §5.0).
- seed 37, RM 팔, 봉인 시드는 열지 않았습니다. 폐루프 런은 없습니다.

---

## 8. 다음 단계에 넘기는 것

1. **단계 2(C6)로 갑니다.** 이 단계의 G-ID 기준은 이제 평탄화 config(`d4327cbf`·`ae8f4940`·`f137f711`)와 이 diff입니다. 단계 2 뒤 G-ID (a)(b)를 다시 받을 때 비교 기준은 `S1/probe/b2_base`, `S1/probe/b2_u1u3`, `S1/sdmpc/b2_*`입니다.
2. **옛 튜닝은 새 어댑터에서 멈춥니다.** U4-0 전 추적 튜닝 245개가 필수 키 하나 이상을 이름으로 갖지 않습니다. 옛 런을 새 코드로 재생하려면 `name_former_defaults`를 명시적으로 불러야 합니다. 고치지 않은 옛 도구 3개(`review_unresolved_projection_support.py:38`, `scripts/offline_harness_20260904.py:17`, `scripts/probe_far_components_20260901.py:29`)도 같습니다.
3. **단계 4(U4) 할 일:** `install_lane_group_membership`의 `["internal"]` 제한(A:4295-4297)을 "C3 세 키가 모두 있을 때"로 넓힙니다. 오류 문구와 시험 `test_kinds_are_required_known_and_internal_until_c3`도 함께 바꿉니다.
4. **옛 경로(헤드 관측 꺼짐)** 는 코드 기본값(`seed` `plant`, `decay` 0.98, `lane_group_kinds` `["internal"]` 등)을 그대로 가진 채 남아 있습니다. 쓰는 추적 튜닝이 65개라 격리하지 않았습니다. 승격 때 계획 §2-5대로 격리합니다.
5. **변환의 남은 한계**(§2.8-1): 표지 키 셋을 하나도 쓰지 않는 U4-0 뒤 튜닝은 옛 튜닝과 구별되지 않습니다. 공용 로더를 거치는 진단에서만 생기는 문제이고, 실운영은 실패합니다.
6. **커밋할 때:** 세 config 바이트가 바뀌므로 옛 런 provenance와 frozen 트리에 기록된 튜닝 sha는 이 브랜치 코드와 맞지 않습니다(계획 §3 `[검토 C-9]`가 받아들인 결과). `test_head_service_resources.py` 등 4개 시험이 추적 파일을 다시 쓰므로, 커밋 전에 `git status`로 되돌렸는지 확인하십시오.
7. **v3c1으로 옮길 때:** `claude/repin-v3c1-20260928`(`5323faa`)의 `make_config_n31.py`와 이 브랜치의 평탄화가 겹칩니다. v3c1 config에 평탄화를 다시 적용하면 새 전제 검사(seed `sustained` 포함)가 조건을 확인합니다. 이 브랜치와 그 워크트리는 건드리지 않았습니다.
8. **하네스:** `H/_prov.py`가 이제 `worktree_diff_sha256`을 기록합니다. 이후 단계의 결과 재사용은 이 값으로 판정하십시오. `H/stage1_chain.py`에는 `--no-wait-foreign`이 생겼습니다(기본은 이전처럼 대기).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE1.md`
- 체인: `S1/chain.log`(16:02 OLD, 17:04 이전 diff b2 — 판정에 안 씀, 19:45 재개 b2 N1–N3, 22:14 N4 재시작), `S1/logs/*.txt`, 발사 스크립트 `S1/launch_chain_resume.cmd`, `S1/launch_chain_n4.cmd`
- 계수·포착: `S1/probe/old_{base_inst,s1_inst,s0e_inst,u1u3}/`, `S1/probe/b2_{base,u1u3,s1_inst,s0e_inst}/` (`T*.json`, 전체 결정은 `T*.action.json.gz`)
- SDMPC: `S1/sdmpc/b2_{s1,s0e}_T*.summary.json` + 재생 폴더(`original/`, `replay/`, `replay_compare.json`)
- 분석: `S1/stage1_results.json` (`H/analyze_stage1.py`)
- config 조사: `S1/pre/config_scan.json` (`H/scan_capacity_configs.py`, cf3ce37 상태)
- 평탄화 검사: `S1/flatten_diff_check.json` (`H/flatten_diff_check.py`, 최종 diff)
- 스위트: `S1/s3/tests/`, `S1/s3/fixtures/`(최종), 대조 `S1/suite_compare_s3.json`(`H/compare_suites.py`). 중간: `S1/suites_r1/`, `S1/suites_r2/`, `S1/s2/`(+ `S1/suite_compare_s2.json`), 빠른 확인 `S1/r3_quick/`
- 이전 diff 결과 보관: `S1/_prev_diff_1705/` (b2 포착 110개, 로그, 18:05까지의 체인 로그, 이전 평탄화 검사·분석)
- 하네스(새로): `H/u40_probe.py`, `H/stage1_chain.py`, `H/scan_capacity_configs.py`, `H/flatten_diff_check.py`, `H/analyze_stage1.py`, `H/compare_suites.py`(재개). 고친 것: `H/run_suites.py`(stage 1 스위트 두 개, 짧은 diff 이름), `H/_prov.py`(재개: `worktree_diff_sha256`), `H/stage1_chain.py`(재개: BEGIN/ALLDONE diff sha, `--no-wait-foreign`), `H/analyze_stage1.py`(재개: provenance에 diff sha, SDMPC action JSON 전체 비교)
