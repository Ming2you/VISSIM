# SDMPC-31 × obs150 계약 (WP-0, 2026-09-24)

계획서 `D:\VISSIM-merge\evidence\SDMPC31_OBS150_PLAN_20260924.md` §1의 정본입니다. 모든 WP는 이 문서와 코드 한 벌을 기준으로 씁니다.

- **코드:** `evaluation/controllers/obs150_contract.py` (이하 OC). 스키마 상수, 검증기, 데이터클래스, 시간 규약·항등식의 참조 구현, §1.9 시그니처가 들어 있습니다.
- **시험:** `diagnostics/obs150_20260924/tests/test_contract_*.py` (63개). 합성 픽스처는 `contract_fixtures.py`에 있고, 다른 WP도 가져다 써도 됩니다.
- **규칙:**
  - 검증기는 `ObsContractError`(ValueError)를 던집니다. 값을 고치거나 기본값으로 채우지 않습니다.
  - 지연 규칙 위반만 하위 클래스 `ObsLagError`를 씁니다.
  - 인터페이스를 바꿀 때는 이 문서와 OC를 함께 고칩니다. 다른 WP는 OC를 직접 고치지 않고, 통합 담당에게 요청합니다.
  - 아래 "계획 대비 확정"(§10)은 계획서가 열어 두었거나 모순이던 부분을 WP-0이 닫은 목록입니다.

실행: `PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider diagnostics/obs150_20260924/tests/` (W 루트에서).

---

## 1. 스위치 (계획 1.1)

**키는 하나입니다:** 튜닝의 `freeway.lane_plant`이고, 그 manifest의 `schema`를 봅니다. `plant_mode(document)`(OC:155)가 `'v1'` 또는 `'v2'`를 돌려줍니다.

| schema | 경로 |
|---|---|
| `coupled-lane-plant/v1` | 21셀, 매초 관측, SimRes 1. `diagnostics/lane_plant_20260921/plant.json`은 바이트 그대로 둡니다 |
| `coupled-lane-plant/v2` | 31셀, 150초 1회 관측, SimRes는 망 값 10. 정본입니다 |

### 1.1 v2 manifest (`validate_plant_manifest_v2`, OC:163) — 키 집합이 정확히 이것이어야 합니다

```json
{
  "schema": "coupled-lane-plant/v2",
  "sources": {
    "network": {"path": "...", "sha256": "..."}, "geometry": {}, "refined_partition": {},
    "reference_config": {}, "parameters": {}, "port_profile": {}, "reference_protocol": {},
    "runner_config": {"path": "diagnostics/sdmpc_n31_20260924/scenario/lane_native_b110.vbs", "sha256": "..."},
    "sig_manifest": {"path": "diagnostics/sdmpc_n31_20260924/network/sig_manifest.json", "sha256": "..."}
  },
  "membership": {"path": "...", "sha256": "..."},
  "off_groups": "diagnostics/control_improvement/.../offramp_route_inventory_v1.json",
  "observation": {"detectors": {"path": "diagnostics/sdmpc_n31_20260924/obs150/obs150_detectors_v2.csv", "sha256": "..."},
                  "expected_simres": 10, "vehrec_interval_sec": 5},
  "source_boundary": {"mode": "calibrated_history_forecast", "history_sec": 150, "model_step_sec": 10},
  "lane_groups": false, "fw_e_terminal": "component", "vsl_command_space": "parent_21",
  "future_observations": false, "qualification": "<정직한 상태 문장>"
}
```

- 모든 핀은 `{path, sha256}`입니다. path는 저장소 상대경로이고 `/`만 씁니다. 역슬래시, 절대경로, `..`는 거부합니다.
- sha는 소문자 hex입니다.
- `lane_geometry` 소스는 없습니다(lane_groups false).
- `runner_config`와 `sig_manifest`는 WP-0이 추가했습니다(§10).

### 1.2 튜닝 규칙 (`validate_tuning_v2(tuning, document)`, OC:192)

튜닝은 extends를 합친 유효 튜닝을 기준으로 봅니다.

- `freeway.lane_plant`: `/` 경로
- `urban.capacity.head_observation.enabled == true`이고 `sample_interval_sec`는 **없어야** 합니다
- `execution.native_signal_record == false` (NEW-2)
- `execution.signal_vbs_config == manifest.sources.runner_config.path`
  - 새 발사기는 `-VbsConfig`를 이 값에서 끌어냅니다.
  - 망은 `sources.network`와 런 사본에서, 관측 env는 `observation`에서 끌어냅니다.

### 1.3 러너 env (PS1 `Set-HeadObservationTransport`, v2일 때만)

`expected_runner_env(document, detectors_abs_path)`(OC:240)가 정확한 집합입니다. SHO v2는 provenance의 `env`를 이것과 대조합니다.

| 변수 | 값 |
|---|---|
| RW_SIGNAL_OBSERVATION | `0` |
| RW_LANE_PLANT_OBSERVATION | `1` |
| RW_VEHICLE_OBSERVATION_INTERVAL_SEC | `1` |
| RW_QUEUE_WINDOW | `0` |
| RW_OBSERVATION_CADENCE | `decision150` |
| RW_STATE_LOG | `decision` |
| RW_OBS150_DETECTORS | CSV 절대경로 (FRZ 또는 런 사본) |
| RW_OBS150_DETECTORS_SHA256 | `observation.detectors.sha256` |
| RW_OBS150_EXPECTED_SIMRES | `10` |
| RW_OBS150_VEHREC_SEC | `5` |
| RW_OBS150_GT | 정답 창이 있을 때만 `750:900,1050:1200`. 이름이 `sdmpc31_g`로 시작하는 dev 런에서만 허용합니다(`parse_gt_windows`/`format_gt_windows`) |

- `RW_SIGNAL_OBSERVATION_CONFIG_SHA256`은 v1 규칙 그대로이고, obs150 모드에서는 읽지 않습니다.
- v1 env는 바이트 불변입니다(A8 PreflightOnly diff 0).

### 1.4 provenance `observation` 블록 (A8; `validate_provenance_observation`, OC:252)

```json
"observation": {"schema": "obs150-provenance/v1", "cadence": "decision150",
  "plant_manifest": {"path": "<abs>", "sha256": "..."},
  "detectors": {"path": "<abs>", "sha256": "...", "rows": 290},
  "expected_simres": 10, "vehrec_interval_sec": 5,
  "ground_truth_windows": [[750, 900], [1050, 1200]],
  "freeze": {"path": "<FRZ>\\FREEZE.json", "sha256": "..."}}
```

- `freeze`는 PreflightOnly(W)에서만 `null`을 허용합니다. 발사에서는 `require_freeze=True`입니다.
- `ground_truth_windows`는 정렬돼 있고, 150초 경계에 맞고, 겹치지 않아야 합니다.

### 1.5 거부 규칙 (섞어 쓰면 조용히 돌지 않음)

- **VBS `Quit 2` (obs150Mode에서):**
  - `obsEnabled` 동시 켜짐
  - `ForceStepwiseMode()`
  - `stateLogIntervalSec ≠ controlInterval`
  - `auditAnchorsSec ≠ ""`
  - `incidentEnabled`
  - `SimRes ≠ RW_OBS150_EXPECTED_SIMRES`
  - 평가 속성 되읽기 불일치
  - 검지기 키 재사용, 차로·위치 되읽기 불일치, 키 0 대체
  - 같은 T 번들 두 번 쓰기
- **PS1 throw (v2일 때):**
  - `sample_interval_sec` 존재
  - `-StateLogIntervalSec ≠ -ControlIntervalSec`
  - `-ForceStepwise`
  - dev 이름이 아닌데 `-GroundTruthWindows`
  - 검지기 CSV sha가 manifest 핀과 다름
  - (통합 추가, WP-A A8) `-MaxAttempts > 1`: v2는 한 번만 시도합니다.
  - (통합 추가) 이름 기반 정지 없음: v2는 항상 `-NoGlobalKill`로 동작하고, `Kill-Vissim`은 v2에서 throw합니다. 러너가 띄운 cscript, 그 자손(어댑터 python, SDMPC 워커), 식별한 VISSIM만 PID와 시작 시각으로 정지합니다(`Stop-RunProcesses`).
  - (통합 추가) 정답 창: 시작 < 150이거나 겹치거나 붙은 창(`750:900,900:1050`)은 거부합니다. 붙은 창은 합쳐서 씁니다(`750:1050`).
  - (통합 추가) `-VbsConfig` ≠ manifest `sources.runner_config`(경로와 sha)
  - (통합 추가) 핀 경로에 `..`나 `:`가 있으면 거부합니다(`Resolve-Obs150RepoPin`).
- **파이썬:**
  - v2 키에 v1 팩을 붙이면 망/팩 핀에서 즉시 예외가 납니다.
  - `validate_tuning_v2`, `validate_raw`, `validate_lane_meta_v2`가 나머지를 막습니다.

---

## 2. 시간 규약 (계획 1.2 + B3·B5 규칙)

### 2.1 상수 (OC:276-287)

| 상수 | 값 |
|---|---|
| DECISION_INTERVAL_SEC | 150 |
| FIRST_DECISION_SEC | 1 |
| EXPECTED_SIMRES | 10 |
| VEHREC_INTERVAL_SEC | 5 |
| MER_TIME_DECIMALS | 2 |
| BOUNDARY_EPS_S | 0.005 |
| LAG_MARGIN_S | 1.0 |
| STEP_ORDER_SCAN_S | 0.2 |
| GREEN_STATE | `"GREEN"` (황색 통과는 녹색이 아님, D7) |

### 2.2 정지·창

- **정지:** 정지는 정수 초에서만 합니다. 번들(결정)은 t=1과 150의 배수에서만 있습니다(`is_decision_stop`).
- **창:** 창 k는 (150k−150, 150k]입니다(`window_bounds`, `window_index`).
  - 참시각 τ의 통과는 `window_of_time(τ) = ⌈τ/150⌉` 창에 속합니다. τ=150k이면 창 k입니다.
- **t=1:** 열린 구간 (0, 1]입니다. `bundle_interval(1) = (0, 1, None)`이고 k는 None입니다.
- **쓰기 시점:** 결정 T에서의 쓰기는 창 k+1에 속합니다.
  - 창 k의 시작 상태 = 정지 T−150에서 쓰기 **전**의 상태입니다. 그 쓰기는 T−149부터 헤드에 반영되므로(2.3) 창 k의 사건입니다.
  - 창 1의 시작은 t=1 번들 시점(정지 1의 쓰기 전)의 상태이고, 모든 SG가 네이티브입니다. 러너는 그 전에 쓰기가 없음을 강제합니다.

### 2.3 신호 상태와 녹색 구간

- **헤드 갱신은 매초 끝에 한 번입니다**(Vissim 2020 매뉴얼 §2.17.3, p.616). 차량은 그 다음 스텝부터 반응합니다. 그래서 슬롯 (t, t+1]의 상태는 t의 갱신 하나로 정해집니다.
  - **네이티브 SG:** t의 갱신은 프로그램 상태(phase t − offset)입니다. 정지 t의 되읽기와 같습니다(V0-4).
  - **COM SG (D10, WP-B1 `COM_HEAD_DELAY_S = 1`):** 정지 t의 쓰기는 되읽기에는 바로 보이지만, 정지가 t의 갱신 뒤라서 헤드에는 t+1에 올라갑니다. 그래서 t에 쓰고 t′에 바꾼 상태는 차량 시각 (t+1, t′+1]에 적용됩니다. `own`과 `fail`도 같은 1초 뒤에 적용됩니다.
  - 근거: 탐색 런 850 GREEN 쓰기 뒤 미터 두 차로의 정지 선두차가 851.0까지 v=0이었고 851.1에 출발했습니다(네이티브는 s+0.1). SimRes 1 재생에서도 COM LDP(t)가 source(t−1)과 같았습니다. 계획 1.2의 "정지 t에서 쓴 상태는 (t, t′]"(PRB g, 되읽기 근거)를 이것으로 대체합니다.
  - COM으로 네이티브 프로그램을 흉내 내는 러너는 정지 t에 t+1의 상태를 씁니다(`frameAdvance` 1, VBS `OBS150_FRAME_ADVANCE`).
- **녹색 구간은 정수 쌍 (a, b)입니다.** 참시각 τ의 통과는 `a < τ ≤ b`일 때 녹색입니다(`in_green`, OC:323).
  - 구간은 절대 sim 초이고, T−150 ≤ a < b ≤ T입니다.
  - 정렬돼 있고 서로 떨어져 있어야 하며, 붙은 구간은 합칩니다.
- **꼬리(tail):** 꼬리 통과는 (T−1, T]에 있고, 그 1초의 상태는 하나입니다. `tail_in_green(T, iv) = in_green(T−0.5, iv)`입니다.
- **네이티브 SG:** `.sig` 적분입니다. 스텝 규약 상수 `NATIVE_STEP_RULE`은 WP-B1 소유(`obs150_signal_clock`)이고, 값은 V0-4가 정합니다.
  - 허용값은 `NATIVE_STEP_RULES = ('program_state_at_step_end', 'program_state_at_step_start')`입니다.

### 2.4 `.mer` 시각과 파일 순서 규칙 (B5, D8)

`.mer` 시각은 0.01초로 반올림돼 있습니다. `near_integer(t)`는 |t−s| ≤ 0.005인 정수 s를 돌려줍니다.

**`boundary_side(rows, i, s)` (OC:366):** rows는 청크 행을 seq(파일) 순서로 둔 것입니다. 행 i의 시각이 녹색 경계 s(±0.005)에 있을 때 다음과 같이 판정합니다.
- **`'after'`:** 앞선 행에 `t_file ≥ s+0.005`가 있으면 → 스텝 (s, s+0.1]입니다.
- **`'before'`:** 뒤따르는 행에 `t_file ≤ s−0.005`가 있으면 → 스텝 (s−0.1, s]입니다.
- **`'ambiguous'`:** 둘 다 없으면 모호입니다.
- **둘 다 있으면** 스텝 순서 전제가 깨진 것이므로 `ObsContractError`입니다.
- **탐색 범위:** 뒤로는 `t_file < s−0.2`, 앞으로는 `t_file > s+0.2`에서 멈춥니다.
- **청크 시작:** 청크 첫머리에서는 더 볼 행이 없으므로 보수적으로 모호가 될 수 있습니다.
- **창 경계 (WP-B1 `obs150_head_window.classify_at_window_edge`):** T−150 또는 T(±0.005)의 기록은 파일 순서로 판정하지 않습니다.
  - 서수 배정이 이미 (T−150, T]에 넣었으므로 스텝이 정해집니다: T−150이면 τ=T−150+0.05, T이면 τ=T입니다.
  - 녹색이 창 경계에서 잘려 끝점이 돼도 모호로 세지 않습니다. 파일 순서가 반대 스텝을 가리키면 `ObsContractError`입니다.

**`classify_passage(rows, i, intervals)` (OC:396):** 진입 사건 하나를 판정해 `'green' | 'not_green' | 'ambiguous'`를 돌려줍니다.
- 녹색 구간 끝점이 아닌 정수 근처의 기록은 그냥 `in_green(t)`로 봅니다.
- 끝점이면 판정 결과에 따라 before → τ=s, after → τ=s+0.05로 봅니다.
- **D8:** 검증 런(`ground_truth_windows` ≠ [])에서는 모호 > 0이면 실패입니다(`validate_derived`가 강제). 운영 런에서는 기록만 합니다.

### 2.5 지연 규칙 (B3; `lag_ok`, OC:411)

- Σtail = 0이면 통과입니다.
- 아니면 `max_t_any > T − 1 + 0.005`여야 합니다. `max_t_any`는 파일 전체의 진입·이탈 열 최대 시각입니다.
- 위반하면 `ObsLagError`이고, 결정 실패입니다.
- **t=1은 항상 통과입니다.** 열린 구간 (0, 1]이 곧 (T−1, T]입니다. 이때 `.mer`는 헤더 중간인 경우가 많고(`max_t_any` null), 1.0 m 원점 스테이션은 이미 1대를 셀 수 있습니다.
- `.err` 지연은 D11(G1 측정 뒤)에서 정합니다.

### 2.6 서수 창 배정 (B3; `assign_window(obs, mer_rows) -> WindowAssignment`, OC:430)

- **C 값:** Cₖ = `detectors_cum[d]`, Cₖ₋₁ = Cₖ − `detectors[d]`입니다(t=1이면 0).
- **창 판정:** 진입 행의 지점 서수 n이 Cₖ₋₁ < n ≤ Cₖ이면 이 구간에 속합니다.
- **tail:** `tail[d] = Cₖ − records_cum_by_dcp[d]`이고, 모두 (T−1, T]에 있습니다.
- **검사:**
  - Cₖ₋₁ ≤ records ≤ Cₖ
  - 청크의 진입 서수가 records까지 연속
  - 이 구간 행이 전부 이 청크에 있음 (records − 청크 진입 수 ≤ Cₖ₋₁)
  - 진입 시각 ∈ [T−150−0.005, T+0.005]
  - 표에 없는 dcp 행 없음
- **결과:** `entries{dcp: 진입 MerRow…}`, `tails{dcp:int}`, `sum_tail`, `max_t_any`, `lag_ok`
- **전제:** 한 지점에서 0.1초 스텝당 통과는 1대 이하입니다. 그러면 지점 안 파일 순서가 곧 시각 순서입니다.
- **소유:** 이 함수는 WP-0 정본입니다. WP-B1은 V0-1, V0-2로 이것을 탐색 런 자료에 대조합니다.

---

## 3. 계수 항등식 (계획 1.3)

### 3.1 식은 하나입니다: `identity_cross(orientation, vehs, n_end, n_start, removed)` (OC:522)

| orientation | 뜻 | 식 |
|---|---|---|
| `at` | 스테이션이 x에 정확히 있음 | cross = Vehs(x); N, R은 0이어야 함 |
| `down` | 하류 오프셋 p > x | in_x = Vehs(p) + N_[x,p)(T) − N_[x,p)(T−150) + R_[x,p) |
| `up` | 상류 오프셋 p < x | out_x = Vehs(p) + N_[p,x](T−150) − N_[p,x](T) − R_[p,x] |

### 3.2 구간 (`SegmentPiece(link, from_m, to_m, lanes|None)`, 경로 순서)

- **닫힘:**
  - 모든 조각은 닫힌 구간 [from, to]입니다.
  - 단, `down`의 **마지막** 조각은 [from, to)입니다(끝이 스테이션 p).
  - 차량 앞머리 위치 q ≥ x이면 x를 지난 것으로 봅니다(`segment_contains`, OC:505).
- **`down` 구간:** 마지막 조각은 (row.link, …, to=pos)이고, 비어 있으면 안 됩니다.
- **`up` 구간:** 첫 조각은 (row.link, from=pos, …)입니다.
- **N:** 프레임 차량 `[veh, link, lane, pos, …]` 가운데 구간 안에 있는 수입니다. 차로 제한 조각은 lane으로 거릅니다.
  - 스테이션 N은 같은 boundary_ref 행들 구간의 합집합이고, 차량 번호로 중복을 뺍니다.
- **R:**
  - 창 (start, end] 안의 `lane_change_removal` 행 가운데 (link, position_m)이 구간 안에 있는 수입니다.
  - **.err에는 차로가 없으므로 R은 스테이션 단위뿐**입니다(`removals_in_boundary`, OC:817).
  - R_k는 T에 읽힌 청크의 행만 셉니다. 늦게 기록된 제거는 D11로 감사합니다.
- **체인 커넥터:** 체인 내부 커넥터(10699/10613/10702/10771)는 조각으로 허용합니다. 그 밖의 커넥터가 구간에 닿는지는 B1 생성기가 망에서 assert합니다.

### 3.3 결과: `evaluate_boundary(rows, detectors, frame_end, frame_start, removal_rows, start_s, end_s) -> IdentityTerms` (OC:577)

- **필드:** `boundary_ref, role, orientation, vehs, n_end, n_start, removed, cross, lanes, lane_exact, removed_vehicles`
  - `lanes`는 차로별 `LaneTerms(lane, vehs, n_end, n_start, cross)`이고, 차로별 cross는 R=0으로 계산합니다.
- **`lane_exact`:** R = 0이고 차로 cross가 모두 0 이상인 경우입니다. 이때 Σ차로 cross + R = 스테이션 cross가 성립합니다.
  - 차로값을 소비하는 경계(램프 도착분율, 10643 차로분율)에서 `lane_exact`가 False이면, B6은 `ObsContractError`로 닫습니다.
- **음수 검사:** 스테이션 cross < 0이면 예외입니다.
- **일괄 계산:** `evaluate_boundaries(obs, rows, frame_end, frame_start, err_rows)`(OC:611)는 표의 모든 boundary_ref를 한 번에 계산합니다. B5, B6, B7은 모두 이것을 부릅니다. 그래서 같은 값이 나옵니다.
- **초기 조건:** t=0에서 N=0입니다(frame_000000은 빈 프레임).
- **부호 시험:** 0.1초 정수 cm 궤적 합성으로 `down`, `up`, 링크 경계를 넘는 2조각, 차로별, 창 경계 제거를 모두 봅니다(`test_contract_identity.py`, V0-6b).

---

## 4. `obs150-raw/v1` (계획 1.4; A7이 쓰고 B가 읽음; `validate_raw`, OC:996)

### 4.1 위치와 경로

- `state_<T:06d>.json`의 **최상위 키 `obs150`**입니다(`RAW_STATE_KEY`).
- 상대경로는 전부 `/`이고, `obs150.directory`(= decisionDir, 절대경로)를 기준으로 풉니다(`resolve`, OC:886).

| 경로 함수 | 값 |
|---|---|
| `frame_path(t)` | `lane_observations/frame_%06d.json` |
| `mer_chunk_path(t)` | `obs150/mer_%06d.jsonl` |
| `err_chunk_path(t)` | `obs150/err_%06d.jsonl` |
| `MER_INDEX_PATH` | `obs150/mer_index.json` |
| `capture_meta_path(t)` | `obs150/capture_%06d.json` |
| `derived_path(t)` | `obs150/derived_%06d.json` |
| `INSTALL_RECORD_PATH` | `obs150/obs150_install.json` |

### 4.2 필드 (키 집합 정확히; t=1만 `open_interval` 추가)

| 키 | 형식·규칙 |
|---|---|
| schema | `"obs150-raw/v1"` |
| sim_sec | 1 또는 150의 배수 |
| k / window | T≥150: `k=T/150`, `{"start_s":T−150,"end_s":T}`. t=1: `null`, `null` |
| open_interval | t=1에만 `{"k":1,"end_s":1}` |
| directory | decisionDir 절대경로 |
| simres_steps_per_sec | 정수, manifest `expected_simres`와 같음 |
| run_id | 문자열 |
| ground_truth_windows | `RW_OBS150_GT` 해석값, 운영 런은 `[]` (D8/D9 strict 판정) |
| detector_config | `{path, sha256, rows}` |
| install_record | `{path:"obs150/obs150_install.json", sha256}` |
| detectors | `{"<dcm_no>": int}`. **CSV의 모든 키**를 담고, `Vehs(Current,k,All)`입니다. t=1은 열린 구간 1의 부분 누적입니다. 값은 JSON 정수만 허용합니다(VBS는 `VarType∈{2,3,5}`를 검사한 뒤 CLng) |
| detectors_cum | 같은 키. `Σ_{j≤k} detectors_j` (닫힌 창만 누적). t=1에서는 detectors와 같음 |
| detectors_last_equal | T≥150이면 `true`여야 함(false면 거부). t=1이면 `null` |
| rule_crosscheck | `{"9100xx": int}`: 망에 있는 910030–910047의 `Vehs(Current,k,All)` |
| linkeval_volume_veh_h | `{"<link>": float≥0 \| null}`: 오프 커넥터 8개와 10565/10570의 `AVG:LinkEvalSegs\Volume(Current,k,All)`. 읽기 실패는 null. 감사용입니다 |
| mer | §4.4 |
| err | §4.4 |
| signal_log | §4.3 |
| source_cumulative_vehs | `{"FW_E":int,"FW_W":int}` = 도로별 source 행 `detectors_cum`의 합 |
| frames | `{"current":{path: frame_path(T), sha256, vehicles:int}, "previous":{path: frame_path(start), sha256}}`. previous는 T−150 프레임이고, t=1이면 frame_000000입니다 |

**교차 검사 (행을 주면):**
- `detector_config.rows`와 키 집합
- 각 dcp에 대해 `C_prev ≤ records_cum ≤ C`
- `source_cumulative_vehs` 합
- `removals_cum_by_boundary` 키 = 오프셋 경계 전부

### 4.3 `signal_log` (`validate_signal_log`, OC:947)

```json
{"scs": ["1004","5","9106"],
 "start": {"1004-2": {"owner":"native"}, "9106-1": {"owner":"com","state":"GREEN","verified":true}},
 "events": [[812,"9106","1","write","RED"], [830,"9106","1","fail","RED","ERR:readback=GREEN"], [860,"9106","1","own",false]],
 "complete": false}
```

- **`scs`:** 러너가 쓸 수 있는 SC 전부와 헤드·미터 SC의 합집합입니다.
- **`start`:** 그 SC들의 **모든 SG**에 대해 창 시작 상태, 곧 정지 T−150에서 쓰기 **전**의 상태를 담습니다(2.2). 키 형식은 `"<sc>-<sg>"`입니다.
  - native: `{"owner":"native"}`만 둡니다.
  - com: `{"owner":"com","state":<대문자 SigState>,"verified":bool}`입니다. verified=false는 직전 fail 뒤 아직 성공 write가 없다는 뜻입니다.
- **`events`:** 시각은 정수이고 T−150 ≤ t < T만 담습니다. 정지 T−150의 쓰기(결정 쓰기 포함)는 이 창의 사건이고, 정지 T의 쓰기는 다음 창의 사건입니다. 시각순이고, 같은 t에서는 발생순입니다. 정지 t의 사건은 슬롯 (t+1, t+2]부터 적용됩니다(2.3).
  - `write` 5칸: 되읽기 일치
  - `fail` 6칸: 쓰기 실패 또는 되읽기 불일치. 마지막 칸은 요청값과 상세입니다
  - `own` 5칸: 마지막 칸이 ContrByCOM 되읽기 bool입니다. true면 슬롯 (t+1, t+2]부터 COM 소유, false면 네이티브입니다(2.3)
  - write와 fail은 그 시점에 COM이 소유한 SG에만 허용합니다.
  - own(true) 뒤 같은 t에 write/fail이 없으면, 다음 성공 write까지 미검증입니다(B4).
- **`complete`:** fail이 있거나 verified=false인 start가 있으면 `false`여야 합니다. 러너는 다른 사유로도 false를 낼 수 있습니다.

### 4.4 포착 meta — `mer`/`err` 블록 (`validate_capture_meta(meta, T)`, OC:933)

**`mer` 키:**

| 키 | 뜻 |
|---|---|
| source | EvalOutDir의 `*.mer` 절대경로. t=1에 정확히 1개여야 함 |
| chunk | `mer_chunk_path(T)` |
| chunk_sha256 | 청크 파일 sha |
| index | `obs150/mer_index.json` |
| index_sha256 | 이 호출 인덱스 엔트리의 `entry_sha256` |
| prev_index_sha256 | 직전 엔트리의 `entry_sha256`. t=1은 null |
| byte_start, byte_end | 읽은 완결 줄 범위 [start, end). t=1은 start=0. 다음 호출의 start = 이번 end. **t=1은 헤더만 소비합니다:** byte_end ≤ 열 제목 줄 끝이고 청크 0행, records 0, max_t_any null입니다. 창 1의 행((0, 1] 포함)은 모두 T=150 청크에 들어갑니다 |
| max_t_any | 소비한 파일 전체(모든 dcp, 진입·이탈 열)의 최대 시각. 없으면 null |
| records_cum_by_dcp | `{"<dcp>": 파일 전체의 진입 행 누계}`. 모든 CSV 키 |

**`err` 키:**

| 키 | 뜻 |
|---|---|
| source | `<망 폴더>\<망 stem>_001.err` 절대경로. 파일이 아직 없으면 빈 파일로 봄. 다른 `_*.err`가 있으면 실패 |
| chunk, chunk_sha256 | 청크 파일과 sha |
| byte_start, byte_end | 완결 줄 범위 |
| partial_tail_bytes | 다음 호출로 넘기는 미완결 꼬리 |
| max_sim_sec | 파일에 나온 가장 큰 "Simulation second" |
| removals | 이 청크의 제거 행 수 |
| unparsed_removal_lines | **0이어야 함** |
| removals_cum_by_boundary | `{boundary_ref: int}`. 오프셋 경계(down/up) 전부에 대해, 파일 전체 제거 행 가운데 구간 안(차로 무시)에 든 누계. 원점 admitted_cum을 정확히 하려고 추가 |

**청크 행 (`MER_ROW_FIELDS`, LF JSONL):**
- **`.mer`:** 한 줄 = JSON 배열 `[seq, dcp, t_entry, t_exit, veh, vtype, v_kmh, length_m, ordinal]`
  - `seq`: 파일 전체 **데이터 행**의 0-기반 번호. 비생성 지점 행도 셉니다
  - 시각 −1.00 → null
  - ordinal: 진입 행이면 그 지점의 1-기반 서수, 이탈 전용 행이면 null
  - 생성 지점 행만 저장합니다. 로더는 `load_mer_chunk` → `MerRow`입니다.
- **`.err`:** 한 줄 = ERRP `parse_bytes`의 사건 dict입니다. 정규화는 두 가지입니다.
  - `byte_offset`을 **절대** 오프셋으로 바꾸고, `line_number`는 뺍니다.
  - 제거·무시 행의 `link`는 int로 바꿉니다.
  - 제거 행 키: `kind, message, byte_offset, raw_line_sha256, time_sec, wait_sec, vehicle_id, route_decision, route_index, link, position_m`
- **파일 규칙:**
  - 조각 파일이 이미 있으면 거부합니다.
  - 인코딩은 UTF-8이고 CR이 없어야 합니다.
  - 빈 청크는 0바이트 파일입니다.

**인덱스 `obs150/mer_index.json`:** `{"schema":"obs150-mer-index/v1","source":…,"entries":[…]}`
- 엔트리 키: `sim_sec, chunk, chunk_sha256, byte_start, byte_end, max_t_any, records_cum_by_dcp, prev_entry_sha256, entry_sha256`
- `entry_sha256 = canonical_sha256(엔트리 − entry_sha256)`입니다. 사슬로 이어지므로, 파일을 다시 써도 과거 state의 핀이 검증됩니다(`validate_mer_index`, OC:1171).

**`load_bundle(raw)` (OC:1193):** 청크, 인덱스 엔트리, 두 프레임을 sha로 확인해 읽습니다.
- 프레임은 VBS가 UTF-16(BOM) 또는 UTF-8로 씁니다.
- B1, B2는 이 로더만 씁니다.

### 4.5 포착 CLI (VBS A7.4 ↔ WP-B1)

```
python -B scripts\obs150_capture.py --eval-dir <EvalOutDir> --err <망폴더\stem_001.err> --out-dir <decisionDir>\obs150
       --sim-sec <T> --detectors <CSV 절대경로> --detectors-sha256 <sha>
```

- **파일:** 청크 두 개, 인덱스, 그리고 `obs150/capture_<T>.json`을 씁니다.
  - capture 파일은 `capture_meta_bytes`와 같은 바이트입니다: 한 줄, ASCII, 키 순서 mer→err, 끝 개행 없음.
- **stdout:** 정확히 한 줄 `OBS150_CAPTURE_OK meta=obs150/capture_<T>.json sha256=<hex>`만 냅니다.
  - meta 자체는 stdout으로 보내지 않습니다. `RunCapture3`는 종료 뒤에야 stdout을 읽기 때문에, 4 KB가 넘으면 파이프가 막힐 위험이 있습니다.
- **exit:** 성공은 0입니다. 0이 아니면 VBS가 `AbortVehicleObservation`을 부릅니다.
- **VBS 조립:** VBS는 파일 텍스트의 바깥 중괄호를 떼고(`Mid(text,2,Len−2)`) `"mer":…,"err":…`를 obs150 객체에 그대로 끼웁니다.
- **파이썬 함수:** `obs150_capture.capture(...)`는 같은 meta dict를 돌려줍니다.

### 4.6 그 밖에 러너가 쓰는 것

- **`obs150/obs150_install.json`** (`validate_install_record`, OC:1212):
  - 키: `{schema:"obs150-install/v1", run_id, detector_config{path,sha256,rows}, simres_steps_per_sec:10, points:[{dcp_no,dcm_no,link,lane,pos,readback:{link,lane,pos}}], evaluation:{…}}`
  - points는 CSV 순서입니다.
  - 되읽기 pos 허용오차는 `POS_READBACK_TOL_M = 1e-3`입니다.
  - `evaluation` = `DataCollCollectData:true, DataCollFromTime:0, DataCollToTime:int, DataCollInterval:150, DataCollRawWriteFile:true, DataCollRawFromTime:0, DataCollRawToTime:int`
- **프레임** `lane_observations/frame_<T>.json`:
  - `lane-plant-frame/v1`, 15칸 행 `FRAME_ROW_FIELDS`(OC:851)를 v1 writer 그대로 씁니다(`sample_interval_sec` 없음).
  - `frame_000000`은 첫 스텝 전의 빈 프레임입니다(`validate_frame`).
- **`lane_plant_observation` meta (A7.1):** `{directory, run_id, time_s, cadence:"decision_150s"}`입니다(`validate_lane_meta_v2`).
- **`local_observation.far_measurement` (v2):**
  - `interval_sec:150`
  - `link_volume_veh_h`: `(Current,k,All)`로 읽습니다. 뜻은 Edie 평균 그대로입니다(D-D (a))
  - **`freeway_exit_count: null`**
  - `signal_observation_window`와 `link_departures_window`는 쓰지 않습니다(병합이 채움).

---

## 5. 파생 스키마 (계획 1.5)

### 5.1 `obs150-derived/v1` (`validate_derived`, OC:1434)

키 집합(`DERIVED_KEYS`)은 다음과 같습니다.

| 키 | 내용 |
|---|---|
| schema, sim_sec, k, window, run_id | 번들과 같음 |
| strict | `bool(ground_truth_windows)`. true면 모호 0, 10643 `unidentified` 0이어야 함 (D8/D9) |
| inputs | `raw_sha256`(=`canonical_sha256(raw['obs150'])`), `detector_config_sha256, mer_chunk_sha256, mer_index_sha256, err_chunk_sha256, frame_current_sha256, frame_previous_sha256` |
| boundaries | `{boundary_ref: IdentityTerms.as_dict()}`. 각 항목이 §3 식을 만족 |
| lag | `{sum_tail, max_t_any, threshold_s, ok:true, err_max_sim_sec}` |
| tails | `{"<dcp>": int}`, 합 = sum_tail |
| boundary_ambiguous | int. 헤드 창 행의 합 |
| removals | `{window_total, rows:[{vehicle_id,time_sec,link,position_m,route_decision,route_index,boundary_refs:[…],on_chain:bool}]}`. 시각은 창 안 |
| head_window | `physical-head-window/v2`. t=1은 null |
| off_split | `{off:{downstream_veh, off_veh, post_branch_ramp_bypass_veh:0, eligible_exits_veh, ratio}}`. 8개이고 10643 포함. ratio = off/(off+through), 0/0이면 0 |
| ramp_arrival_shares | `{ramp_id:[차로 분율…]}`. 합 1. 도착 0이면 균등(LPR:357-360 닫힘) |
| offramp_10643_history | `local_history` 모양: `off_composition`(2차로, `[[connector\|null, share]…]`), `background:{}`, `exchange_rates:[]`, `information_cutoff_s:T`, `history_start_s:max(0,T−150)`, `endogenous_background:true` |
| offramp_10643_lane_shares | `[s1, s2]`: `off_entry:10643` 차로 cross 분율. 합 0이면 [0.5,0.5]. **D-C (b)**용으로 WP-0이 추가 |
| ledger_10643 | `{vehicles:[{veh,lane,via:"mer"\|"tail",connector,label_source:"frame"\|"destination"\|"removal"\|"unidentified"}], by_lane:{"1":{conn:n},"2":{…}}, tail_by_lane:{"1":n,"2":n}}` |
| freeway_exit_count | `{value, off_total, chain_end_total, chain_removals}`. value = 합 |
| source_boundary | §5.2와 같음 |
| link_departures_window | `{"403": cross(headfree:10565)+cross(headfree:10570)}`. t=1이면 0 |
| edie_residuals | `{"<link>": float}`. 감사 전용, 정의는 B6 |

**B6 식 (계획 그대로, 항은 §3):**

- **오프 분기**
  - X_off = cross(`off_entry:<off>`)
  - through = cross(`through:<off>`)
- **freeway_exit_count** = Σ X_off(8) + cross(`chain_end:FW_E`) + cross(`chain_end:FW_W`) + R_chain
  - R_chain = 창 안 제거 가운데 link ∈ 체인 링크(내부 커넥터 포함)인 수
- **원점 (도로 r)**
  - admitted_window = cross(`source:r`)
  - **admitted_cum = source_cumulative_vehs[r] + N_src(T) + removals_cum_by_boundary['source:r']** (항등식을 누적하면 이렇게 됩니다. N(0)=0)
  - interval_s = 150 (t=1이면 1)
  - recent_vph = 3600·admitted_window/interval_s
  - schedule_integral_veh = ∫₀ᵀ 스케줄
  - backlog_veh = max(0, 적분 − admitted_cum)
- **t=1 닫힘**
  - 분기율 0, 균등 분율, 10643 None 분율, `freeway_exit_count` 0
  - 열린 구간 off_entry·chain_end Vehs가 전부 0인지 B6이 assert합니다.

**파일:** `write_derived(raw, derived)`(OC:1516)가 `obs150/derived_<T>.json` = `canonical_json_bytes(derived)+b"\n"`를 씁니다.
- 같은 바이트가 이미 있으면 통과하고(재생 멱등), 다르면 예외입니다.
- `derive`는 순수 함수입니다. 쓰는 쪽은 WP-C `observe_live` v2입니다.

### 5.2 `lane-plant-observation/v2` (LPR 소비; `validate_lane_observation_v2`, OC:1409)

키 집합은 다음과 같습니다.
`schema, information_cutoff_s(T), history_start_s(max(0,T−150)), future_traffic_inputs:false, lane_group_dynamics:{}, current_exit_labels:{}, off_split_ratio{off:ratio}, off_split_history{off:{downstream_veh,off_veh,post_branch_ramp_bypass_veh:0,eligible_exits_veh}}, frames:[frame_T], ramp_arrival_shares, offramp_10643_history, offramp_10643_lane_shares, freeway_exit_count:int, source_boundary, source`

- **`source_boundary[r]`:** `{admitted_window:int, admitted_cum:int, interval_s:150|1, recent_vph, schedule_integral_veh, backlog_veh}`. 식 두 개(recent, backlog)는 1e-9로 검사합니다.
- **`source`:** `{run_id, manifest_sha256, derived_sha256(=canonical_sha256(derived)), + DERIVED_INPUT_KEYS}`
- **C4(h):**
  - `local_history(...)` → `observation['offramp_10643_history']`
  - 램프 프레임 루프 → `observation['ramp_arrival_shares'][name]`
  - `frames={T: frame_T}`
  - C5는 `offramp_10643_lane_shares`
  - C6은 `source_boundary`

### 5.3 `physical-head-window/v2` (SHO 소비; `validate_head_window_v2`, OC:1311)

```json
{"schema":"physical-head-window/v2","config_sha256":"<provenance signal_observation.config_chain[0].sha256>",
 "detector_config_sha256":"<CSV sha>","start_sec":T-150,"end_sec":T,"cadence_sec":150,
 "exposure_method":"runner_write_log+sig_program","clock_complete":bool,
 "heads":[{"head_id":"…","link":"…","lane":1,"position_m":<serialized_head_position(inpx)>,"sc":"…","sg":"…",
           "crossings":int,"qualified_crossings":int,"green_sec":int,"native_sec":int,"controlled_sec":int,
           "unverified_sec":int,"boundary_ambiguous":int}],
 "bypass_link_exits":{"403": cross(headfree:10565)}}
```

- **heads:** 적격 헤드 전부(`physical_groups`, SHO:82-104)이고, head_id는 유일합니다.
  - `crossings` = Vehs
  - `qualified_crossings` = 창 진입 행 가운데 `classify_passage == 'green'`인 수 + (`tail_in_green`이면 tail)
- **없어진 필드:** `transition_count`, `unknown_links`, `vehicle_cadence_sec`
- **검사:**
  - qualified ≤ crossings
  - native+controlled+unverified = 150
  - green ≤ native+controlled, green은 정수
  - unverified > 0이면 clock_complete=false

### 5.4 신호 시계 (B4 출력; `validate_clocks(clocks, window)`, OC:1283)

- **모양:** `{"<sc>-<sg>": {"green":[(a,b)…], "native_sec":int, "controlled_sec":int, "unverified_sec":int, "complete":bool}}`
  - window는 raw의 `{"start_s","end_s"}` dict입니다.
- **녹색:** 절대 초 정수, (a,b]이고, 정렬·분리·병합돼 있어야 합니다.
- **초 합:** 세 초의 합 = 150입니다. 미검증 초가 있으면 complete는 false입니다.

### 5.5 병합 `merge_into_state(raw, derived) -> raw′` (`validate_merged_state`, OC:1532)

raw는 깊은 복사하고, **정확히 다음만** 바꿉니다.
- `local_observation.signal_observation_window = derived.head_window` (t=1은 키가 있고 값은 null)
- `local_observation.link_departures_window = derived.link_departures_window`
- `local_observation.far_measurement.freeway_exit_count = derived.freeway_exit_count.value`
- `local_observation.far_measurement.freeway_exit_count_provenance = "conservation_v2"`
- 최상위 `obs150_derived = derived` (메모리 전용이고 state 파일에는 다시 쓰지 않습니다. `lane_observation`이 읽습니다)

병합 전 `far_measurement`는 객체여야 하고, 그 `freeway_exit_count`는 null이어야 합니다. AD:8059 v2 assert(WP-B1)는 이 값이 없거나 음수이면 예외를 냅니다.

---

## 6. `Obs150Context` (계획 1.6; OC:1629, `validate_context` OC:1656)

`obs150_observation.load_context(document, paths)`(WP-B2)가 런마다 한 번 만듭니다. `paths`는 LPR `load_sources`의 `{key: read_pin 결과}`입니다.

| 필드 | 내용 |
|---|---|
| manifest_sha256, network_sha256 | manifest와 망 sha |
| detector_csv_path, detector_csv_sha256, detectors | `read_detector_csv(pin)`. 행은 dcp 순서 |
| boundaries | `group_boundaries(detectors)`: `{boundary_ref: 행들(차로순)}`. 1.3의 오프셋 구간은 이 행들의 `segment` |
| chain_links | `{"FW_E":(74,10699,2,10613,119,10702,24),"FW_W":(26,10771,120)}`: `sources.runner_config`의 `RW_FW_*_CHAIN_LINKS` 파싱 |
| chain_internal_connectors | frozenset, 체인 위 커넥터 |
| offramps | `{off: OfframpRef(connector, road, from_cell(31셀), lanes, off_entry_ref, through_ref)}`: 8개 |
| ramp_arrivals | `{ramp_id: RampArrivalRef(ramp_id, connector, lanes, boundary_ref, receiving)}`. receiving = `component.ramp_receiving_nodes` |
| source_refs, chain_end_refs | 도로 → `source:<r>` / `chain_end:<r>` |
| headfree_refs | `{"10565":…, "10570":…}` |
| x10643_exit_ref | `"x10643_exit:10643"` |
| destination_refs | `{"10634","10635","10642"}` → `destination:<c>` |
| lane_map_10643 | `{link: {lane: 10643차로}}`: 10643, 126, 10641, 10700, 71 (inpx 커넥터 차로 사상) |
| route_destinations_10643 | RD 1126 경로번호 → 목적지 커넥터 (inpx) |
| head_groups | `physical_groups(network, plan)`. **head 검지기 집합과 정확히 같아야 함** |
| sig_table | `{sc: SigProgram(sc, path, sha256, prog_no, offset_s, cycle_s, green_s{sg:((start,end)…)})}` |
| source_schedule | `{road: (ScheduleRow(start_sec, end_sec\|None, vph)…)}`: `net.native_input_schedule` + `freeway_link_by_input` |

- **sig_table:**
  - 값은 `.sig`의 `<prog id=progNo>`에서 정수 초로 읽습니다(NEW-9).
  - `.sig` 42개는 `sig_manifest.json` 옆, 곧 `N31D/network/`에 바이트 사본으로 있어야 합니다. **WP-E에 요청합니다.**
  - B4는 런 망 폴더의 `.sig` sha를 이 표와 다시 대조합니다.
- **스케줄 도우미:**
  - `schedule_rate_at(s, t)`는 BF `demand_vph`와 같습니다.
  - `schedule_integral_veh(s, 0, T)`는 BF `desired_before`와 같습니다.
  - 이 동일성을 시험으로 고정했습니다(T7b의 절반).

---

## 7. 검지기 CSV (계획 1.7; `format_detector_csv`/`parse_detector_csv`/`read_detector_csv`, OC:750-811)

**열:** `dcp_no,dcm_no,role,ref,link,lane,pos,pos_mode,orientation,boundary_ref,segment_json,geometry_assert`

- **바이트 형식:**
  - ASCII, LF, 헤더 한 줄, dcp_no 오름차순입니다.
  - `pos`는 `'%.6f'`로 씁니다.
  - JSON 열은 compact하고 sort_keys이며, CSV 인용을 합니다.
  - **정본 형식만 받습니다.** 다시 서식했을 때 같은 바이트여야 합니다.
- **VBS 읽기:** 앞 10열에는 쉼표와 따옴표가 없습니다. VBS는 `Split(line, ",", 11)`로 앞 10개만 씁니다.
- **키:**
  - `dcp_no == dcm_no`(측정은 지점마다 1:1)입니다.
  - 범위는 `960001–969999`입니다. 910001–910116과 950xxx는 범위 밖이라 쓸 수 없습니다.
- **역할과 방향:**

| role | orientation | ref | boundary_ref |
|---|---|---|---|
| head | at | `<head_no>\|<sc>-<sg>` | `head:<head_no>` |
| meter_head | at | `<head_no>\|<sc>-<sg>` | `meter_head:<head_no>` |
| off_entry | down | off 커넥터 | `off_entry:<c>` |
| through | at/down/up | off 커넥터 | `through:<c>` |
| x10643_exit | up | `10643` | `x10643_exit:10643` |
| destination | down | 커넥터 | `destination:<c>` |
| ramp_arrival | down | `RM_C<n>` | `ramp_arrival:RM_C<n>` |
| source | down | `FW_E`/`FW_W` | `source:<r>` |
| chain_end | up | `FW_E`/`FW_W` | `chain_end:<r>` |
| headfree | down | `10565`/`10570` | `headfree:<c>` |

- **`boundary_ref`는 `expected_boundary_ref(role, ref)`와 같아야 합니다.**
  - 한 boundary_ref 안에서는 차로당 한 행이고, role과 orientation이 같아야 합니다.
- **`pos`:** 설치 절대위치(m)입니다. `pos_mode`는 유도 방식입니다.
  - `exact`: 지정 위치를 그대로 씁니다.
  - `end_minus`: `pos == round(link_length_m − offset_from_end_m, 6)`이어야 합니다.
- **`segment_json`:**
  - `[{"from_m","lanes":[…]|null,"link","to_m"}…]`이고 경로 순서입니다.
  - `at`이면 `[]`입니다.
  - 값은 6자리로 반올림합니다.
  - 닫힘과 끝점 규칙은 §3.2입니다.
- **`geometry_assert`:**
  - 필수: `link_length_m`, `lane_count`. `end_minus`이면 `offset_from_end_m`도 필수입니다.
  - 생성기 assert 값을 더 넣어도 됩니다.
  - lane ≤ lane_count, pos ≤ 길이 + 1e-3이어야 합니다.

---

## 8. `.gitattributes` (계획 1.8, WP-0이 한 번 수정 — 완료)

```
diagnostics/sdmpc_n31_20260924/** -text
diagnostics/obs150_20260924/** -text
```

- 파일 끝에 CRLF 줄로 덧붙였습니다. 이 파일 자체가 `-text` CRLF입니다.
- `git check-attr text`는 두 폴더에서 `unset`입니다(시험으로 확인).
- 다른 WP는 이 파일을 건드리지 않습니다. `git add -u --renormalize`는 금지입니다.
- (통합 추가) C1 사본 폴더 `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/`는 하위 `.gitattributes`(`* -text`, WP-C)로 CRLF 핀을 지킵니다. 폴더째 커밋하면 이 파일도 함께 들어갑니다(`test_pinned_inputs_are_byte_exact_in_git`).

---

## 9. 파이썬 인터페이스 (계획 1.9; `INTERFACES`, OC:1729)

**시그니처 검사:** `assert_implements(qualname, func)`와 `check_module(module)`로 합니다.
- 인자 이름, 순서, 종류(위치/키워드), 기본값이 정확히 같아야 합니다.
- 추가 인자는 기본값이 있는 **키워드 전용**만 허용합니다.
- 각 소유 WP는 자기 시험에서 `check_module`을 부릅니다.

| 함수 (소유) | 입력 → 출력 |
|---|---|
| `obs150_capture.capture(eval_dir, err_path, out_dir, sim_sec, detector_table)` (B1) | out_dir = `<decisionDir>/obs150`, detector_table = `DetectorRow` 튜플 → `{"mer":…, "err":…}` (§4.4). CLI는 §4.5 |
| `obs150_signal_clock.windows(signal_log, sig_table, window)` (B1) | raw signal_log, `context.sig_table`, raw window dict → 시계 dict (§5.4) |
| `obs150_head_window.build(raw, context, clocks, mer_rows)` (B1) | raw = state 전체, mer_rows = **T 청크 전체** `MerRow` 목록(파일 순서) → head window v2. 창 배정은 `assign_window`, 녹색은 `classify_passage`, bypass는 `evaluate_boundaries`(프레임·err는 `load_bundle`) |
| `obs150_lane.derive(raw, context, mer_rows, err_rows, frame_T, frame_prev)` (B2) | T 청크 전체 행, 두 프레임 → `LANE_PART_KEYS` dict (`off_split, ramp_arrival_shares, offramp_10643_history, offramp_10643_lane_shares, ledger_10643, freeway_exit_count, source_boundary, link_departures_window, edie_residuals`) |
| `obs150_observation.load_context(document, paths)` (B2) | → `Obs150Context` |
| `obs150_observation.derive(raw, context)` (B2) | 순수 함수 → `obs150-derived/v1`. 흐름: `validate_raw` → `load_bundle` → `evaluate_boundaries` → `assign_window` → `windows` → `build` → `obs150_lane.derive` → 조립 → `validate_derived` |
| `obs150_observation.merge_into_state(raw, derived)` (B2) | → raw′ (§5.5) |
| `obs150_observation.lane_observation(context, raw)` (B2) | raw = 병합본(raw′). `raw['obs150_derived']`에서 → `lane-plant-observation/v2` |
| `source_boundary.forecast(recent_vph, backlog_veh, schedule, start_s, block_s, n_blocks, step_s=10)` (C) | `[vph per block]` |

**`forecast` 의미 (BF:136-138 재귀, 계획 C6):**

```
backlog = backlog_veh
for b in range(n_blocks):
    rates = []
    for i in range(block_s // step_s):              # block_s % step_s == 0, step_s ∈ {1,5,10}
        t = start_s + b*block_s + i*step_s
        d = schedule_rate_at(schedule, t)
        rate = min(recent_vph, max(0, d + backlog*3600/step_s))
        backlog = max(0, backlog + (d - rate)*step_s/3600)
        rates.append(rate)
    out.append(fsum(rates)/len(rates))
```

**호출 순서 (C3, RS:77-84):**

```
observe_live v2 → obs150_observation.derive(raw, context)
               → write_derived(raw, derived)
               → raw′ = merge_into_state(raw, derived)
               → obs = lane_observation(context, raw′)
               → RS가 state_json을 raw′로 바꿈 (소비자보다 먼저)
```

**OC가 주는 공용 도우미 (다시 구현하지 말 것):**
- 시간: `bundle_interval`, `window_*`, `in_green`, `tail_in_green`, `near_integer`, `boundary_side`, `classify_passage`, `lag_ok`, `assign_window`
- 항등식: `identity_cross`, `segment_contains`, `vehicles_in_segment`, `window_removals`, `removals_in_boundary`, `evaluate_boundary`, `evaluate_boundaries`
- CSV: `format_detector_csv`, `parse_detector_csv`, `read_detector_csv`, `group_boundaries`, `offset_boundary_refs`, `expected_boundary_ref`, `parse_head_ref`
- 로더·기록: `load_bundle`, `load_mer_chunk`, `load_err_chunk`, `load_frame`, `mer_index_entry_sha256`, `capture_meta_bytes`, `write_derived`, `canonical_json_bytes`, `canonical_sha256`
- 검증: `validate_*` 전부
- 스케줄: `schedule_rate_at`, `schedule_integral_veh`

---

## 10. 계획 대비 확정·추가 (WP-0 판단)

| 항목 | 결정 | 이유 |
|---|---|---|
| raw `directory` 추가 | 상대경로의 기준 | derive(raw, context)가 청크를 찾을 곳이 raw 안에 있어야 합니다. D1은 이 키도 바꿉니다 |
| raw `detectors_cum` 추가 | Cₖ | B3 서수 배정에 Cₖ₋₁이 필요합니다. 직전 state를 읽지 않으려고 러너가 누적합니다 |
| raw `ground_truth_windows` 추가 | D8/D9 strict 판정 | derive 시그니처에 모드 인자가 없습니다 |
| signal_log start `verified` 추가 | fail 이월 | 창 경계를 넘는 미검증을 정확히 잇기 위해서입니다 |
| err `removals_cum_by_boundary` 추가 | 원점 admitted_cum | T 청크 하나로는 과거 창의 R 합을 알 수 없습니다 |
| 포착 meta를 파일로 전달 | stdout은 한 줄 | `RunCapture3`는 종료 뒤 stdout을 읽습니다. meta가 4 KB를 넘으면 막힐 수 있습니다 |
| mer 인덱스 엔트리 해시 사슬 | 파일 해시 대신 | 인덱스 파일은 매번 다시 쓰이므로 파일 sha로는 과거 핀을 검증할 수 없습니다 |
| `.err` `_001` 고정, 부재 = 빈 파일 | | 이 경로를 쓰는 러너는 모두 단일 run입니다 |
| manifest `sources.runner_config`, `sources.sig_manifest` 추가 | load_context 입력 | 체인 목록과 `.sig` 표를 manifest 핀으로 가져옵니다. 튜닝 `signal_vbs_config`와 같아야 합니다 |
| `offramp_10643_lane_shares` 추가 | D-C (b) | 차로군이 없는 31셀에서 C5가 쓸 관측입니다 |
| far `freeway_exit_count_provenance` | 키 이름 | `link_volume`에 대한 표기로 오독되지 않게 합니다 |
| 병합본 `obs150_derived` | lane_observation 입력 | 시그니처 `(context, raw)`를 지키면서 같은 결과를 씁니다 |
| `assign_window`, `evaluate_boundaries`, `classify_passage`를 OC에 둠 | 한 구현 | B1·B2가 같은 수를 내야 합니다(헤드 bypass, 403 이탈, 10643 대장) |
| 헤드 창 v2에서 `transition_count` 제거 | | 1초 전이 개념이 없습니다. 노출은 `end−start=150`으로 검사합니다 |
| D10: COM 헤드 반영 1초 지연, `frameAdvance` 1 (WP-B1 V0-4, `patches/OC_B1_D10.patch`) | 2.2, 2.3, 4.3 | 매뉴얼의 초당 1회 헤드 갱신과 탐색 런 차량(851.1 출발), SimRes 1 재생(t−1)이 같은 결과입니다. 네이티브 흉내가 정확해지는 값이라 계획 §9 D10의 "여쭐 경우"(0.1초 늦음/0.9초 이름)에 해당하지 않습니다. G1 D6에서 도시 COM 헤드로 재확인합니다 |

**아직 열린 것 (결정 주체):**
- D10 재확인: G1 1050–1200 도시 COM 헤드에서 GREEN 쓰기 t 뒤 선두차 출발 t+1.1, RED 쓰기 t′ 뒤 (t′, t′+1] 통과가 녹색으로 세어지는지 (D6)
- `.err` 실시간성과 제거 항 처리 (D11, G1)
- 10643 tail 식별 실패의 운영 처리 (D9, G1)
- `lane_exact=False` 빈도 (G1에서 0이 아니면 여쭘)

**사용자 결정 (2026-09-24, 통합 뒤 반영):**
- C12 `port_profile_v2` 선택 = `interp`: off-ramp 체류시간을 5 s FZP 기록 구간 안에서 재구성합니다(b120과 ±5% 안). `port_profile_v2/extract_port_profile.py`의 기본값이고 `port_profile.json` provenance가 `selection: interp`입니다.
- v2 VSL 행동 집합 = `{50,60,70,80,90,100,110}`(10 km/h 간격, c_max 110). 처음 정한 `"60,80,110"`을 같은 날 사용자 결정으로 바꿨습니다. 115·120은 v2에서 쓰지 않습니다.
  - 정의하는 곳은 넷이고 값이 모두 같아야 합니다(`test_repin_scenario_v2`와 `test_n31_generators`가 대조): 러너 `RW_ALLOWED_VSL_SPEEDS`(`repin_scenario_v2.py`의 `VSL_SPEEDS`), 튜닝 `config_overrides.freeway_follower.vsl_set`(`make_config_n31.py`의 `VSL_SET`), plant reference config의 같은 키(`make_reference_config.py`의 `VSL_SET`; boundary의 `[60,80,110]`을 덮음), 그리고 SDMPC 좌표(`sdmpc.py` `Coordinates`가 튜닝 `vsl_set`을 그대로 읽음).
  - plant는 `max(vsl_set)`=110만 읽습니다(Carlson 기준·비활성 명령). 그래서 명령이 모두 110이면 예측이 바뀌지 않습니다.
  - 일곱 속도 모두 v2 망에 같은 번호의 `desSpeedDistribution`이 있습니다(`runner_config_check`). 러너는 `DesSpeedDistr(class) = CLng(speed)`를 쓰고 읽어 온 번호가 같아야 성공합니다(`run_real_world_stackelberg_controller.vbs:1937-1967`, 행 검사 `:1343`). 분포 모양은 한 계열이 아닙니다: 50·60·70은 좁은 균등(48–58, 58–68, 68–78), 80–110은 넓고 오른쪽 꼬리가 깁니다(중앙값 약 86/96/107/117).
  - SDMPC: 블록 0의 VSL 상자는 직전 명령 ±`max_vsl_step` 40입니다. 110에서 {70,80,90,100,110}이고(전에는 {80,110}), 블록 1·2는 ±80·±120이라 50까지 갑니다. decode는 가장 가까운 허용값이고 동률이면 기준값 쪽입니다(`sdmpc.py:338`, `:390-391`). 축 수는 그대로입니다. follower의 k-best VSL 시퀀스 후보(`install_freeway_vsl_sequence_kbest`)는 SDMPC 결정 경로에 없습니다.
  - 핀 연쇄: `scenario/lane_native_b110.vbs` → `obs150/obs150_detectors_v2.manifest.json`(CSV 그대로) → `plant_n31_v2.json`, 그리고 `reference_config_n31_v2.json` → `plant_n31_v2.json`. `config_n31_v2.json`은 `vsl_set` 때문에 바뀝니다.
- D10 = 1 s (위 표). G1 D6의 `d10` 항목으로 재확인합니다.
- VSL 모형을 먼저 plant에 옮깁니다(2026-09-24). 110 속도분포는 VSL을 돌려 본 뒤 정합니다. 분포와 망은 바꾸지 않았습니다.
  - 브랜치 `codex/control-full-review-20260909` d80faf9, 후보 A0.5_E4(`diagnostics/vsl_handoff_20260924/candidate.json` sha `a2fe3366…`)를 브랜치 키 이름 그대로 `reference_config_n31_v2.json`의 `freeway`에 넣었습니다.
    - `vsl_fd_response`: FW_E Carlson A 0.5, E 4, alpha 0, 기준 명령 = max(vsl_set) = 110
    - `component_vsl_transport`: FW_E 표지 셀 `[0,3,5,8,14,18,26,28]`, initial/ramp 명령 110
  - 생성기는 `make_reference_config.py`(`--check`)입니다. 표지 셀은 이 망의 FW_E DSD 단면마다 가장 가까운 정제 셀 경계로 다시 뽑습니다. 이 규칙은 handoff 망에서 handoff 값 `[…,16,…]`을 그대로 재현합니다. 이 망은 DSD63–66이 체인 6733.2 m(link 2 pos 3998.666)에 있어서 셀 18이 됩니다.
  - 계수 출처: seed29, 수요 v1, 다른 110 곡선에서 적합한 값입니다. v2 재적합은 아직 하지 않았습니다. 적합은 90에서만 했으므로 50–80은 외삽이고 100은 90과 110 사이 내삽입니다. FW_W에는 적합한 법칙이 없어서 기존 속도상한 식을 쓰고, 110에서 도함수는 0입니다.
  - 옮기지 않은 것: parent 14/15의 v_free 108.159, anticipation 18.375, `physical_cell_fd`, 램프 head-service 곡선. 모두 handoff 시나리오에 맞춘 국소 보정이라 v2 보정을 덮어씁니다. v2 재적합 때 후보로 봅니다.
  - manifest 키 집합은 그대로입니다. `sources.reference_config` sha와 `qualification` 문장만 바뀝니다. `config_n31_v2.json`은 포트 때 바이트 그대로였습니다(`eddfd19f`). 행동 집합을 바꾼 뒤로는 `vsl_set` 때문에 달라집니다.
  - full follower 가드(`runtime_setup.configure_freeway_runtime`)는 브랜치 가드를 두고 `component_vsl_transport`까지 넓혔습니다(브랜치와 다른 점, 2026-09-24 리뷰). 컨트롤러 튜닝에 `vsl_fd_response`나 `component_vsl_transport`를 넣으면 거부합니다. transport는 component만 설치하므로 다른 경로에서는 조용히 죽은 키가 되기 때문입니다. lane plant component(`CanonicalFreewayModel`)만 `component_validation=True`로 이 두 키를 씁니다. SDMPC의 모든 예측(스칼라 surrogate와 AD)은 lane plant의 도로별 커널(AFA `_freeway_substep_events`)을 거치므로 새 모형은 결정 경로 안에 있습니다. follower와 leader의 자체 VSL 롤아웃은 기존 식을 씁니다. SDMPC는 이 롤아웃을 결정에 쓰지 않습니다.
  - 110 유지 비트 동일: 명령이 모두 110이면 스칼라 값이 옮기기 전과 비트 단위로 같습니다. 진단 키도 새로 늘리지 않았습니다.
  - AD: 110에서는 Carlson 좌미분(한쪽 도함수)만 값 0인 차분으로 싣습니다. cohort 키는 명령의 plain 값이고, 명령 감도는 질량 가중으로 따로 들고 다닙니다(`VSLExposure.tangents`). 관측으로 초기화할 때 cohort의 시작 명령은 아래 결정을 따릅니다(브랜치는 매번 전부 110).
- VSL cohort 초기화 = 직전에 **적용된** 명령(2026-09-24 사용자 결정, v2 정본, env 게이트 없음).
  - 결정 시각의 각 정제 셀 차량은 자기 셀 또는 상류에서 가장 가까운 표지 셀이 직전 적용 행동에서 보여 준 명령으로 태그됩니다(`freeway_fd.applied_cohort_commands`). 차량은 표지 셀에 들어갈 때만 다시 태그되기 때문입니다(`VSLExposure.advance`). 표지 명령은 plant가 명령을 읽는 규칙(표지의 parent 구역 머리 키 → 링크 키 → 110)으로 읽되, `segment_vsl` 훅의 셀 문맥 부작용은 피합니다. on-ramp 유입은 계속 `ramp_command` 110입니다.
  - 직전 적용 행동은 러너가 주는 `--previous-action-json`입니다. 러너는 `ApplyActionCsv`가 성공한 행동에만 이 경로를 넘기고(`run_real_world_stackelberg_controller.vbs:1225`, `:1249-1254`), 그 성공에는 VSL 행마다 쓰기와 읽기 값 일치가 들어 있습니다(`:1446-1462`). 쓰인 것은 top-level `vsl`(블록 0)뿐입니다. 경로가 없으면(t=1) 110이고, 이름은 있는데 파일이 없으면 오류입니다(`lane_plant_runtime.applied_vsl_from_previous`).
  - `lane_plant_runtime.initialize`가 도로별 plant config에 `component_vsl_initial_commands`로 싣고(`_initialize_vsl_cohorts`), AFA가 rollout마다 `VSLExposure`를 만들 때 씁니다. 결정 metadata의 `n31_binding.vsl_cohort_initialization`에 출처(sha, sim_sec, `.applied` 영수증 유무)와 셀별 명령이 남습니다.
  - 전부 110이면 태그 없는 cohort와 비트 단위로 같습니다. 근사: 셀 안을 잘 섞인 것으로 봅니다. 램프에서 들어온 차량이나 직전 명령 이전에 표지를 지난 차량을 따로 나누지 않습니다.

---

## 11. 시험 (`diagnostics/obs150_20260924/tests/`)

| 파일 | 내용 |
|---|---|
| `test_contract_detectors.py` | CSV 정본 바이트 왕복, VBS 앞 10열 분할, sha 핀, 행 규칙 전부(키 범위, 역할·방향, boundary_ref, 구간 끝점, end_minus, 6자리, 차로 중복) |
| `test_contract_time.py` | 창·t=1, (a,b] 녹색, tail, 파일 순서 규칙(after/before/ambiguous/모순/탐색 정지), classify_passage, 지연 규칙, 서수 배정(tail, ObsLagError, 서수 불연속, 누락, 창 밖 시각, t=1) |
| `test_contract_identity.py` | 식 부호, 닫힘, 합성 궤적 대 정답(down / 2조각 down / up / 차로별 / 창 경계 제거), 음수 가드 (V0-6b) |
| `test_contract_raw.py` | raw 필드마다의 거부, t=1 규칙, signal_log 규칙, 디스크 번들 적재(UTF-16 프레임, 인덱스 사슬, 변조 검출), 행 검증, 포착 meta 바이트, 설치 기록, 제거 누계, derived 파일 멱등 |
| `test_contract_schemas.py` | v1 manifest가 v1로 남음(실제 plant.json), v2 manifest·튜닝·env·provenance, GT 창, 헤드 창 v2, 시계, lane obs v2, derived, 병합, lane meta, context, 스케줄 대 BF 동일성, 시그니처 검사, `.gitattributes` |
