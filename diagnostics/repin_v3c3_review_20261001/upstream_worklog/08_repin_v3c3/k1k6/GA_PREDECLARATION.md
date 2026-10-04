# GA 관문 사전 선언 — K1–K6 (v3c1 기반 동일성)

- 작성 2026-10-01, **코드 수정 전**에 고정합니다. 고정 수단은 같은 폴더의 `GA_PREDECLARATION.md.sha256`입니다.
- 근거 문서
  - 계획 `D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md` (sha256 `d4b70c02…`) §3, §5.1, §5.3, §5.4
  - 검토 `…/REPIN_V3C2_PLAN_REVIEW.md` B1–B3, N1–N4, N14 (사용자 승인 2026-10-01)
- 기준 코드: W = `D:/VISSIM-merge/sim3-n31-v3c3`. 브랜치 `claude/repin-v3c3-20261001`, 시작점 `9ed2ef0` (`git status` 0줄 [실행]).
  - `9ed2ef0`과 `5323faa`의 차이는 worklog 문서 35개뿐입니다(`git diff --stat 5323faa 9ed2ef0` [실행]). 그래서 W의 시작 코드는 FRZ `sdmpc31_5323faa4_202609281442`와 같습니다.
- 자료(읽기 전용)
  - R-obs `D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31`: 결정 61개. 모두 NoControl이고, 8개 미터 녹색이 61/61 모두 10입니다 [실행].
  - T5 기록 `…/scratchpad/v3c1-p10/t5/{A,B,H}`
  - hybrid 실패 상태 `D:/VISSIM_runs/20260929_hybrid/sdmpc31_v3c1_hybrid_s31`
- 표기: [실행] 직접 돌려 확인 · [읽음] 파일·코드에서 확인 · [추론] 시험하지 않은 판단

---

## 0. 용어

| 이름 | 뜻 |
|---|---|
| K6 | K1–K6 마지막 로컬 커밋(W). 해시는 `K1K6_IMPLEMENT.md`에 적습니다 |
| FRZ_K6 | K6의 **새 동결본**. 만드는 명령은 §6-1에 있습니다. 기존 FRZ는 고치지 않습니다 |
| GWT | 관문 전용 작업 트리 `D:/VISSIM-merge/sim3-n31-v3c3-k6gate`. `git worktree add --detach … <K6>`로 만듭니다(B3) |
| FRZ_OLD | `D:/VISSIM-merge/frozen/sdmpc31_5323faa4_202609281442`(R-obs와 T5의 트리) |
| ulp 거리 | 두 float의 IEEE-754 64비트 정수 표현 사이 거리. 부호가 다르면 무한대로 봅니다 |
| 휘발 V | 아래 §2.1 목록 |
| 4필드 | `off_ramp_storage_veh`(`prediction.state_summary`, `prediction.calibrated_state_summary`), `prediction.terminal_features.ramp_vehicles`, `prediction.terminal_features.stopped_vehicles` (T5 §3 표) |

---

## 1. K1–K6가 선언하는 효과 (이 밖의 차이 = 선언 밖)

| K | 바꾸는 것 | 선언한 효과 (키 없음·현재 설정 기준) |
|---|---|---|
| K1 | `vendor/NumSim-mine/src/models/state.py:1306` `set(...)` → `sorted(set(...), key=str)` | 같은 링크 집합의 float 합 순서만 고정됩니다. **4필드에서 결정마다 ≤ 2 ulp**(N2: 61개 중 어느 결정이든). 그 밖의 차이는 0으로 선언합니다 |
| K2 | `N31D/tools/make_replay_state_v2.py`, `N31D/tools/n31_common.py`, 새 `evaluation/controllers/vsl_command_distribution.py` | 재생 도구 판정만 바꿉니다. `compare(out_dir, vsl_expected)`의 위치 인자 의미는 그대로입니다(N14). 새 소속 검사는 `--tuning` 경로(키워드)에만 붙습니다. VSL 행이 전부 110이고 110 ∈ 쓰는 집합이면 판정이 같습니다. `replay_compare.json`의 `checks.action_contract`에 키가 더해집니다. action JSON과 CSV는 바뀌지 않습니다 |
| K3 | `evaluation/controllers/physical_ramp_branches.py`(정규화 함수와 `configure` 수송표), `lane_plant_runtime.py:482-486`(측정 곡선 설치) | 같은 서비스 그룹에서 **가장 낮은 허용 녹색**(0 또는 ≥ `min_green_sec` = 2.0)만 남깁니다. 순서를 보존하는 필터이고, 남는 키는 `str` 그대로입니다. RM_C10490 측정표 `{'0','2','3',…,'10'}` → `{'0','2','4',…,'10'}`(3 삭제)입니다. 나머지 7개 표와 수송표는 `list(items())`까지 같습니다. 아래 (a)–(d)는 RM_C10490 적용 녹색의 ±2 s 상자에 3이 들어가는 상태(적용 녹색 1–5)에서만 생깁니다. 옛 코드는 그 상태에서 리더 씨앗 디코드(`physical_ramp_branches.py:358-360`)가 죽었습니다. (a) SDMPC 미터 축 `allowed`와 리더 씨앗 격자에서 3이 빠짐 (b) `sdmpc_continuous.meter_rate`의 [2,4] 매듭 (c) 기록된 RM_C10490 녹색 3을 `prepare_control`·`diagnostic_profile`이 거부 (d) 규칙 프로필 `alinea_meter_step`(`diagnostic_profile.py:227-251`)이 3을 고를 수 없음. (d)는 옛 코드가 죽지 않던 경로입니다(N3). 다만 이번 런 목록에는 없습니다. 새 메타데이터 키 2개(§2.2) |
| K4 | `evaluation/controllers/freeway_fd.py`(`speed_scale` 선택 키), `physical_lane_groups.py:211-212` | 키가 없으면 **값과 연산 순서가 비트 동일**합니다. Dual 연산·비교를 하나도 더하지 않습니다(N1, 탄젠트 카운터 19키 동일) |
| K5 | `vissim_stackelberg_adapter.py` `iter_action_csv_rows`(쓰기 사상), `vsl_command_distribution.py`(가족 일관성), `obs150_contract.validate_tuning_v2`, `runtime_setup.configure_runtime`, `N31D/tools/launch_plan.py` | 키(`actuation.vsl_command_distribution`)가 없으면 CSV가 비트 동일입니다(120 확장·nearest 그대로). 현재 설정(L1, 키 없음, 러너 80,90,100,110)은 가족 검사를 통과합니다. 새 메타데이터 키는 없습니다. 어댑터 sha가 바뀝니다(§2.3) |
| K6 | `lane_plant_runtime._load_sources_v2` 설치 검사 | 현재 reference는 통과합니다. reference `freeway`에 `physical_cell_fd`나 `state_response`가 있으면 거부합니다. 새 메타데이터 키 1개(§2.2) |

- 선언 밖 차이가 하나라도 나오면 그 관문은 실패입니다. 허용 범위를 넓히지 않고 **STOP**합니다(계획 §5.3).

---

## 2. 비교 규칙

### 2.1 휘발 V (어느 관문에서든 비교하지 않음)

- **무제어 결정**(GA-1, GA-2의 4050·4500): T5-A와 같은 **명시 목록 7개**만 휘발입니다.
  - `metadata.decision_wall_sec`, `metadata.prediction_wall_sec`, `prediction.wall_sec`
  - `run_provenance.inputs.state_json.{path,sha256}`, `metadata.run_provenance.inputs.state_json.{path,sha256}`. prepare가 만든 격리 상태 사본입니다(T5 §3)
- **SDMPC 결정**(N1, GA-2의 900, GA-3, GA-4): 위 7개에 다음을 더합니다.
  - T5-B 규칙 그대로: 키 이름이 정규식 `(wall|_sec$|seconds|elapsed|time_s|timestamp|started|finished|cpu|pid)`(대소문자 무시, `t5_chain_b.py`의 `TIMING`)에 맞는 리프. 제어 필드·CSV·목적함수 repr은 §2.4에서 따로 보므로, 이 규칙으로 판정 필드가 빠지지는 않습니다
  - pickle 토큰: `frozen_context_token`, `reference_response_token`, `response_token`, `request_sha256`. 코드 스스로 "process-local exact-value key"라고 밝힙니다(`area_follower_objective.py:436`)
- `replay_run.json`의 경로 문자열은 비교 대상이 아닙니다(Root 확인에만 씀).

### 2.2 새 메타데이터 키 (action JSON `metadata`, "only in replay"로만 허용)

| 키 | 쓰는 곳 | 값 형태 |
|---|---|---|
| `physical_ramp_service_normalisation` | K3, `physical_ramp_branches.configure` 반환 | `{'rule': 'keep_lowest_admissible_green', 'minimum_green_sec': 2.0, 'dropped': {}}`. 수송표는 순증가라 `dropped`가 비어 있어야 합니다 |
| `lane_ramp_head_service_normalisation` | K3, `lane_plant_runtime.initialize` 반환 | `{'rule': 'keep_lowest_admissible_green', 'minimum_green_sec': 2.0, 'dropped': {'RM_C10490': {'3': '2'}}}` (버린 녹색 → 남긴 녹색) |
| `lane_plant_install_check` | K6, `_load_sources_v2`가 만들고 `initialize`가 반환 | `{'compared': ['vsl_fd_response', 'component_vsl_transport'], 'declared': [<reference에 있는 것>], 'refused_if_present': ['physical_cell_fd', 'state_response']}` |

- 값은 위와 정확히 같아야 합니다. 현재 reference에서 `declared` = `['vsl_fd_response', 'component_vsl_transport']`입니다.
- K1·K2·K4·K5는 action JSON 메타데이터 키를 더하지 않습니다.

### 2.3 B1 — 예상되는 `run_provenance` 변화 (열거 + 양성 확인)

- 범위: 최상위 `run_provenance`와 `metadata.run_provenance` 둘 다(같은 객체 [실행]).
- 재생 Root가 FRZ_OLD에서 K6 트리(FRZ_K6 또는 GWT)로 바뀌므로, 아래 필드는 **반드시 달라집니다**. 각 필드에 양성 조건을 둡니다.

| 필드 | 원본(R-obs) | 재생에서 기대값(양성 확인) |
|---|---|---|
| `workspace_root` | FRZ_OLD | 그 재생의 Root(FRZ_K6 또는 GWT)와 경로가 같음 |
| `numsim_repo_root` | `FRZ_OLD\vendor\NumSim-mine` | `<Root>\vendor\NumSim-mine` |
| `numsim_src_sha256` | `05a58a33…` | `<Root>/vendor/NumSim-mine/src/**/*.py`를 `_source_tree_sha256`(`AD:1222-1232`)과 같은 방식으로 따로 다시 계산한 값. 그리고 `05a58a33…`과 다름 |
| `imported_modules` | 30개, 경로는 FRZ_OLD 아래 | **키 집합이 같은 30개**. 경로는 모두 `<Root>` 아래. sha는 `src.models.state` 하나만 다르고, 그 값 = `git show <K6>:vendor/NumSim-mine/src/models/state.py`의 sha(K1 판). 나머지 29개는 sha가 같음 |
| `inputs.<k>.path` (FRZ_OLD 아래 15개: control_mapping_json, detector_mapping_json, calibration_json, tuning_json, parameters_json, parameters_py, adapter_py, fixed_signal_schedule_py, strict_signal_program_py, main_vbs_runner, watchdog_wrapper, numsim_default_yaml, link_assignment_json, intersection_adjacency_json, storage_capacity_json) | FRZ_OLD 아래 | 같은 상대 경로로 `<Root>` 아래 |
| `inputs.adapter_py.sha256` | `66876d53…` | `git show <K6>:evaluation/controllers/vissim_stackelberg_adapter.py`의 sha(K5 판) |
| `inputs.<그 밖 14개>.sha256` | — | 원본과 같음(K1–K6은 설정·매핑·러너를 바꾸지 않음) |
| `execution_fingerprint_sha256` | `f14a041f…` | 재생 JSON 자신의 증거(`AD:1316-1328`의 stable_evidence)로 다시 계산한 값과 같음. 그리고 원본과 다름 |

- 바뀌지 않아야 하는 필드: `schema_version`, `run_id`, `workspace_git_commit`(FRZ는 '' / GWT는 K6 해시), `numsim_git_commit`, `numsim_snapshot_commit`(`e77b7d65…`), `signal_program_sha256`, `inputs.network_inpx`, `inputs.run_manifest_json`(둘 다 런 폴더 안). GWT Root에서는 `workspace_git_commit`과 `numsim_git_commit`이 git 해시가 됩니다. 그러면 기대값은 K6 해시입니다(빈 값이면 실패).
- 트리 양성 확인: FRZ_K6의 `FREEZE.json` 표와 FRZ_OLD의 표 사이 `changed ∪ extra ∪ missing`은 다음 합집합과 정확히 같아야 합니다.
  - (5323faa..9ed2ef0의 worklog 35개)
  - (`git diff --name-only 9ed2ef0 <K6>`)

### 2.4 판정 필드 (지금대로)

- CSV 바이트
- `make_replay_state_v2.CONTROL_FIELDS` 7개(`:61-62`)
- `derived_T.json`(입력 sha뿐이라 경로 영향 없음 [실행 T5])
- SDMPC 결정은 추가로 다음을 봅니다.
  - progress 로그 `objective`/`held_objective`의 repr
  - 탄젠트 트레이스(시간 키를 뺀 리프 전부. T5에서 860/864개)

---

## 3. 관문

### GA-1 — R-obs 결정 61개 재생 (Root = FRZ_K6, 무제어)

- **도구**: FRZ_K6 `tools/make_replay_state_v2.py prepare` → FRZ_K6 `tools/replay_decision_n31.ps1 -ReplayDir <d> -Root <FRZ_K6>`
  - 로그에 `FREEZE_VERIFIED … head=<K6>`, `REBASE provenance root FRZ_OLD -> FRZ_K6`이 있어야 합니다.
  - 이어서 FRZ_K6 `make_replay_state_v2.py compare <d>`(`--tuning` 없음)을 돌립니다.
- **통과 조건**: 아래가 모두 성립해야 합니다.
  1. 비-tuning compare 판정 61/61 IDENTICAL. ps1 자체 판정(`--tuning`, 새 소속 검사) 61/61 IDENTICAL, exit 0
  2. action JSON 전체 diff에서 원본과 다른 곳이 다음뿐
     - V
     - §2.3 열거 필드(양성 조건 모두 성립)
     - §2.2 새 키 3개(값 일치)
     - 4필드: 61개 중 **어느 결정이든** 원본 대비 ≤ 2 ulp(N2)
  3. CSV 바이트, 정수 리프(T5 37,551개)가 61/61 같음
  4. 상시 관문(§4)

### GA-2 — 해시 시드 A/B (K6), N1 옛 트리 A/B 포함

- **N1(옛 트리, GA 앞, 진단 — 판정 아님)**
  - 대상: R-obs 4050 반사실 SDMPC(wu-link) 결정. `PYTHONHASHSEED`를 0과 2로 한 번씩 돌립니다.
  - Root = W @ `9ed2ef0`. **K1 편집 전**에 돌리고, 끝날 때까지 W를 고치지 않습니다.
  - 트리 확인: W 대 FRZ_OLD `FREEZE.json` 표에서 changed 0, missing 0, extra = worklog 35개뿐이어야 합니다. 전후로 확인합니다.
  - 도구 = FRZ_OLD tools(읽기만).
  - 이 위치를 고른 이유: FRZ에는 탄젠트 캐시를 쓸 수 없습니다. 다른 작업 트리는 쓰기 금지입니다. 그리고 W는 이 시점에 옛 코드 그대로입니다.
  - 기록: 두 시드 사이의 CSV 바이트, 목적함수 repr, 제어 필드, 탄젠트 트레이스, 4필드, JSON 차이 목록
  - 해석
    - 같으면: 이 상태에서는 K1이 SDMPC 출력에 닿지 않습니다.
    - 다르면: 그 필드를 GA-3에서 K1 효과로 가를 근거로 씁니다. 이것만으로 STOP하지는 않습니다.
  - 생긴 `__tangentcache__/*.mcode`는 `reports/k1k6/n1/moved_tangentcache/`로 **옮깁니다**. W의 캐시 목록을 전과 같게 되돌립니다.
- **GA-2 본 관문(K6)**: 아래 9회를 돌립니다.
  - 재생 4050·4500(무제어, Root = FRZ_K6) × `PYTHONHASHSEED` {미설정, 0, 2} = 6회
  - 반사실 900(SDMPC wu-link, Root = GWT) × 같은 3개 = 3회
- **통과 조건**: 같은 T의 세 실행끼리 다음이 모두 같아야 합니다.
  - action JSON(V 제외) 바이트 단위 값
  - CSV 바이트
  - 목적함수 repr(900)
  - 탄젠트 트레이스(900)
  - 4필드는 세 실행 사이에서 **비트 동일**(K1의 효과)
- 다르면 그 필드를 적고 **STOP**합니다. K1 범위를 넓히지 않습니다(§5.3, H-2).

### GA-3 — T5-B 반사실 SDMPC 5개 재현 (Root = GWT)

- 대상: 900 r1/r2, 2700 r1, 4950 r1/r2. 각각을 5323faa4 기록 `t5/B/T<T>_r<n>/`과 비교합니다.
- 하네스 재조준(B2)은 §5를 따릅니다.
- **통과 조건**: 아래가 모두 성립해야 합니다.
  1. 각 실행이 기록 대비 같음
     - CSV 바이트
     - progress `objective`·`held_objective` repr
     - CONTROL_FIELDS 7개
     - 탄젠트 트레이스(시간 키 제외 리프 전부)
     - `derived`
  2. action JSON diff가 다음뿐
     - V
     - §2.3 열거 필드(Root = GWT 기준 양성 조건)
     - §2.2 새 키 3개
     - 4필드와 같은 이름의 리프(`off_ramp_storage_veh`, `ramp_vehicles`, `stopped_vehicles`. `prediction` 또는 `diagnostics` 아래 어디든) ≤ 2 ulp
  3. T5 VSL 검사가 그대로 성립
     - 쓰인 값 ⊂ {80,90,100,110}
     - 블록 0 허용집합 = [80,90,100,110]
     - RM_C10490 미터 축 `allowed` = [8,9,10](적용 녹색 10)
  4. 각 재생의 `replay_run.json root` = GWT
  5. 상시 관문(§4)
- 다르면 원인 키 목록과 함께 **STOP**합니다(§5.3). N1 결과를 원인 판단의 근거로 함께 적습니다.

### GA-4 — RM_C10490 양성 대조 (hybrid s31 3000 s)

- **옛 코드 쪽(재현)**: 다음 두 가지로 확인합니다.
  - (a) 기록 증거(읽기만)
    - `runlog_sdmpc31_v3c1_hybrid_s31.txt:1825-1827`의 `DECISION_FAILED … Service coordinate has no unique physical green: RM_C10490`
    - `action_003000.error.txt`
    - 직전 2850 적용 녹색 RM_C10490 = 5.0 [실행]
  - (b) 함수 수준 재현(K6 트리 단위 시험): 정규화하지 **않은** 측정표에서 적용 녹색 5의 ±2 격자를 `candidate_from_services`로 디코드하면 같은 ValueError가 나야 합니다.
  - 계획의 "K2 트리 재생"은 하지 않습니다. K2 코드를 돌릴 수 있는 트리가 W(편집 트리, B3 금지)와 다른 작업 트리(쓰기 금지)뿐이기 때문입니다. 이 변경을 선언합니다.
- **K6 쪽(전체 반사실)**
  - Root = GWT, 컨트롤러 wu-link
  - 상태 = hybrid `state_003000.json`(prepare로 격리)
  - 이전 행동 = hybrid `action_002850`(런 폴더)
  - 튜닝 = **GWT의 배포 `config_n31_v2.json`**
  - hybrid 튜닝 파일이 K6 트리에 없어서 ps1의 rebase로는 줄 수 없습니다. 그래서 ps1과 같은 인자로 어댑터를 직접 부르는 하네스를 씁니다. 그 하네스의 인자는 `replay_run.json`과 같은 형식으로 기록합니다.
- **통과 조건**
  - exit 0
  - `metadata.lane_ramp_head_service_normalisation.dropped = {'RM_C10490': {'3': '2'}}`
  - 선택된 RM_C10490 녹색 ∈ {4,5,6,7} (= 정규화 표 ∩ 상자 3..7)
  - 미터 축 `allowed`(RM_C10490) = [4,5,6,7]
  - 상시 관문(§4)
- 하네스가 hybrid 직전 행동을 다른 이유로 거부하면, R-4 합성 fixture(단위 시험)로 대체하고 그 사실과 거부 사유를 기록합니다.

### GA-5 — 시험 묶음 (금지 시험 제외)

- 목록
  - N31 unittest 16모듈
  - T9 `test_n31_ad_smoke`
  - repin/prepare pytest
  - tools(plant_gate, verify_gt, watch, common)
  - obs150 비-ps1 13모듈
  - `tests/test_literature_vsl_fd.py`
  - `diagnostics/test_physical_ramp_branches.py`
  - K1–K6 새 시험
  - 수정 모듈을 import하는 기존 진단 시험(`K1K6_IMPLEMENT.md`에 목록)
- **통과 조건**
  - 각 묶음의 실패 id 집합이 `9ed2ef0` 기준선과 같습니다(기준선은 같은 명령으로 K1 전에 W에서 측정).
  - 새 시험은 모두 통과합니다.

---

## 4. 상시 관문 (N4 — 모든 제어 결정에 적용)

- 재생·반사실 하나하나
  - 어댑터 exit 0
  - 결정 폴더에 `action_<T>.error.txt` 없음
  - stdout·stderr에 `DECISION_FAILED` 없음
- 런(GB-5 R-obs, J1 등 이후 모든 제어 런)
  - 런로그 `DECISIONS_FAILED` = 0
  - `ERROR=`로 시작하는 줄 = 0
  - `SKIPS` = 0
- 이유: 러너는 CSV 거부(`ACTION_CSV_CONTRACT`)와 VSL 되읽기 거부(`VSL_COM_WRITE_READBACK`)가 나도 그 구간을 직전 DSD로 계속하고 exit 0으로 끝납니다(검토 N4). 그래서 이 관문만이 "조용한 되돌림"을 잡습니다.

---

## 5. 하네스 재조준 (B2)

- 옛 하네스는 고치지 않습니다: `…/scratchpad/v3c1-p10/t5/t5_common.py:9-14`, `t5_chain_b.py:144`(P10 증거).
- `reports/k1k6/ga/`에 사본(`ga_common.py`, `ga_chain_a.py`, `ga_chain_b.py`, `ga_chain_h.py`)을 두고 상수만 바꿉니다.

| 상수 | 옛 값 | 새 값 |
|---|---|---|
| `FRZ` | FRZ_OLD | FRZ_K6 |
| `WT` (SDMPC Root, `t5_chain_b.py:144`의 `-Root`) | `D:/VISSIM-merge/sim3-n31-v3c1` | GWT `D:/VISSIM-merge/sim3-n31-v3c3-k6gate` |
| `TOOLS` (prepare/compare/ps1) | `FRZ_OLD/diagnostics/sdmpc_n31_20260924/tools` | `FRZ_K6/diagnostics/sdmpc_n31_20260924/tools` |
| `WT_PS1` | FRZ_OLD 사본 | FRZ_K6 사본 |
| `NUMBA` | `…/nbc_p10` | `reports/k1k6/ga/numba_cache` |
| `RUN`, `DEC`, `PY` | 그대로(R-obs, RW_PYTHON) | 그대로 |

- **시작 거부 조건**(체인 머리에서 확인)
  - `FRZ_K6/FREEZE.json`의 `git.head` ≠ K6
  - `git -C GWT rev-parse HEAD` ≠ K6
  - GWT 대 FRZ_K6 표 diff ≠ 0(캐시 폴더 제외)
- **재생마다 기록하고 통과 조건에 넣는 것**
  - `replay_run.json`의 `root`
  - action JSON `run_provenance.workspace_root`
  - `imported_modules['src.models.state'].sha256`
  - `inputs.adapter_py.sha256`
  - 이 값들은 §2.3 기대값과 같아야 합니다. 하나라도 FRZ_OLD나 `sim3-n31-v3c1`을 가리키면 그 재생은 무효이고 관문은 실패입니다(거짓 통과 방지).
- **B3**
  - GA 재생은 FRZ_K6과 GWT에서만 돌립니다. W(편집 트리)에서는 돌리지 않습니다.
  - GWT의 트리 확인(FREEZE 표 대비 바이트 동일, 캐시 목록)을 GA 전후로 기록합니다.
  - GA가 만든 `__tangentcache__`는 `reports/k1k6/ga/moved_tangentcache/`로 옮깁니다.
  - K7 편집은 W에서만 하므로 GA와 병행할 수 있습니다.
- 재생은 한 번에 하나, BELOW_NORMAL로 돌립니다. `RW_*`는 지우고 provenance env만 넣습니다(ps1).

---

## 6. 절차 순서

1. FRZ_K6를 만듭니다. GWT에서 다음을 돌립니다(VISSIM 없음).
   `powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name k6gate_preflight -SimPeriod 9000 -Seed 31 -Controller no-control -RunsRoot D:\VISSIM_runs\20261001_v3c3\reports\k1k6\ga\preflight`
   - 로그의 `FRZ=` 줄이 FRZ_K6입니다.
   - `-Freeze`는 튜닝을 담은 git 작업 트리(GWT)를 동결합니다.
2. 트리 확인을 기록합니다: FRZ_K6 표, GWT = FRZ_K6, §2.3 마지막 항목.
3. 순서: N1 → GA-1 → GA-2 → GA-3 → GA-4 → GA-5.
   - N1은 K1 편집 전에 끝냅니다(이번 단계).
   - 실패하면 §5.3에 따라 STOP하고 보고합니다.
4. 결과는 `reports/k1k6/ga/GA_REPORT.md`에 적습니다. 관문마다 통과/실패와 근거 파일을 남깁니다.

## 7. 금지 (계획 §5.4, 과제 HARD RULES)

- 돌리지 않는 것: `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, real_watchdog
- VISSIM을 시작하거나 종료하지 않습니다.
- s37/59/61/67 자료를 보지 않습니다.
- 기존 FRZ와 다른 작업 트리를 고치지 않습니다.
- 푸시하지 않습니다.
