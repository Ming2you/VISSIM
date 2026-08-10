# P-Stack 플랜트 구현 계획 v3 (경량판)

- 작성: 2026-08-07
- 대체 대상: `IMPLEMENTATION_PLAN.md` (v2.1)
- 상태: **채택됨 (2026-08-07)** — 이 문서가 활성 계획이다

---

# 후임 작업자에게 — 이 문서를 먼저 읽어라

**이 계획은 v2.1 보다 의도적으로 작다. 맥락 상실이나 누락이 아니다.**

`IMPLEMENTATION_PLAN.md`(v2.1)는 저장소에 남아 있고 앞으로도 남는다. 그러나 **활성 계획은 v3 다.**
v2.1 은 참조 문서이지 되돌아갈 목표가 아니다.

## 예상되는 실패 모드

새 세션이나 다른 에이전트가 두 문서를 나란히 놓고 보면 v2.1 이 더 철저해 보인다.
그래서 "누가 실수로 잘라냈구나" 로 읽고 원복하려는 충동이 생긴다.
**그 충동이 정확히 이 문서가 막으려는 것이다.**

v2.1 이 요구하는데 v3 에 없는 항목을 발견했다면, 그것은 **버그가 아니라 결정**이다.
결정의 근거는 아래에 있다. 근거를 읽고도 되살려야 한다고 판단되면, **사용자에게
"어떤 주장이 이것을 요구하는지" 를 제시하고 승인을 받아라.** 조용히 되살리지 마라.

## 왜 축소했는가

v2.1 은 두 가지를 동시에 추구한다.

| | 무엇 | 이 연구에 필요한가 |
|---|---|---|
| **A. 물리 충실도** | 플랜트가 VISSIM 을 옳게 투영하는가 | **필수** |
| **B. 증거 출처 관리** | 그 판정을 제3자가 원본 바이트에서 재현할 수 있는가 | 아니오 |

**A 가 필수인 이유.** 이 연구의 주장은 "내 제어기가 고정신호보다 TTT 를 X% 줄인다" 가 아니다.
Stackelberg marginal price 는 **미분의 부호와 순위**에 대한 주장이다. 총량이 10% 맞아도 기울기
부호가 뒤집히면 메커니즘 자체가 무너진다. 그리고 이미 실증됐다 —
**H=1 에서 rho 0.4378, top pairwise 0.000.** 총 통행시간 기준으로는 그럭저럭 보이던 플랜트가
기울기 순위에서는 무작위였다. 총량 지표만 보는 검증은 이 오류를 구조적으로 못 잡는다.
`spillback F1 = 1.000` 도 같은 부류였다 — 라벨이 전부 같아 정보량이 0인데 지표는 만점이었다.

**B 를 걷어낸 이유.** 런 **사후** 출처 사슬(`run-artifact-manifest-v2.2`,
`projection-live-replay-v2.2`), 재생 검증기, ACL 격리 staging, 서명 번들, wave 폐기 프로토콜,
사후 변조 탐지는 **규제 제출이나 이해상충이 있는 다자 검증**의 장치다.
(**주의** — 런 *전* 불변 매니페스트와 해시 결속은 B 가 아니라 A 다. 원칙 2 의 단서를 보라.)
학위논문·저널 심사는 이를 요구하지 않는다. 단일 연구자가 자기 실험을 돌리면서 자신을 상대로
ACL 을 거는 것은 방어 가치보다 비용이 크다.

**그리고 비용이 실제로 문제였다.** 2026-08 초 시점에서 이 저장소는 B1a 증거 배관을 여덟 라운드에
걸쳐 강화했다. 그동안 **플랜트는 실 데이터로 단 한 번도 돌지 않았다.** `outputs/` 에 토폴로지
산출물조차 없었다. 한 번도 열어 본 적 없는 문에 자물쇠를 계속 달고 있었던 것이다.
v2.2 생산자 두 개(약 3,500줄)를 더 써야 첫 실 런이 가능한 상태였고, 그 두 파일은 물리 검증에
아무것도 기여하지 않는다.

**v3 는 A 를 한 줄도 줄이지 않고 B 를 걷어낸다.**

## 무엇을 포기했는지 정확히

포기한 것은 하나다 — **"누군가 중간 산출물을 조용히 바꿨을 때 탐지된다"** 는 보장.
v3 에서도 설정과 시드로 재실행은 되지만 변조 탐지는 안 된다.

포기하지 않은 것 — 질량 보존, 정확 분할, 기울기 부호·순위 검증, H별 동적 게이트,
런타임 p95, 자기신고 PASS 금지. **논문의 주장이 서는 것은 전부 여기 있고 하나도 줄이지 않았다.**

## 되살리는 것이 옳은 경우

다음 중 하나에 해당하면 v2.1 요소를 되살려라. 그 외에는 되살리지 마라.

1. **주장이 바뀌었다.** 예를 들어 규제 제출이나 외부 감사가 목표가 되면 B 전체가 필요해진다.
2. **게이트가 경계선이다.** v3 가 줄인 표본(아래 표)으로 판정이 임계 근처에 걸리면
   **해당 표본만** v2.1 수준으로 복원한다. 다른 항목까지 함께 되돌리지 마라.

   | 항목 | v2.1 | v3 | 단계 |
   |---|---|---|---|
   | 부모 런 | 18 | 9 | N5 |
   | holdout 시드 | 47/59/71 | 47 | N5 |
   | SPSA 방향 batch / state | 30 | 20 | N8-1 |
   | 결정 동등성 twin | 108 | 36 | N8-2 |
   | 런타임 attempt / stratum | 100 | 50 | N8-4 |
   | 런타임 독립 VISSIM 런 | 10 | 5 | N8-4 |
   | 레버 재료 비교 | 24 | 16 | N9-4 |
   | spillback pos/neg / 셀 | 각 20 | 각 10 | N9-4 |
   | J 런 키 필드 | 22 | 13 | N9-1 |
   | BLOCKED 판정 | 5회 | 3회 | N10 |

   **이 표에 없는 것을 줄이지 마라.** 표에 없는데 v2.1 과 다르면 그것은 버그다.
3. **여러 사람이 동시에 이 저장소를 수정한다.** 그때는 산출물 출처 추적이 실질적 가치를 갖는다.

"v2.1 이 더 엄격해서" 는 근거가 아니다.

## 원칙

1. **주장이 요구하는 것만 검증한다.** 기울기 부호·순위를 주장하므로 그 검증은 타협하지 않는다.
   출처 사슬은 주장의 일부가 아니다.
2. **런 단위 사후 출처 사슬을 쓰지 않는다.** 구체적으로 — `run-artifact-manifest-v2.2`,
   `projection-live-replay-v2.2`, 재생 검증기, 서명 번들, ACL 격리 staging, 사후 변조 탐지.

   **⚠ 이 원칙은 아래를 포함하지 않는다. 이것들은 유지한다.**
   - `run-manifest-v2.1` (런 **전** 불변 매니페스트, `build_run_manifest_v2_1.py`)
   - approval → selection → topology → state-set 의 `input_hashes` / `semantic_sha256` 결속
   - state 의 `run_provenance` ↔ 런 매니페스트 결속

   이것들은 **"어느 런의 어느 시각에 어느 토폴로지로 계산했는가" 를 확정하는 물리적 신원**이지
   출처 감사가 아니다. 그리고 코드가 이미 요구한다 —
   `build_state_manifest_v2_1.py` 의 `MANIFEST_INPUT_HASH_NAMES` 가 사슬을 강제하고
   `validate_state_projection_v2_1.py:22-26` 이 `validate_approval_artifact` 를 import 한다.

   **v3 초판은 이 단서를 빠뜨려 승인 아티팩트를 삭제했다가 N0-3 에서 되돌렸다.**
   원칙만 읽고 해시 결속을 지우면 투영 사슬 전체가 무너진다. 같은 실수를 반복하지 마라.
3. **사전 등록은 문서로 하고 봉인하지 않는다.** 임계치와 시드는 런 전에 이 문서에 적는다.
   ACL 격리, 서명 번들, wave 폐기 프로토콜은 쓰지 않는다.
4. **자기신고 PASS 는 계속 금지한다.** 이것만은 v2.1 그대로다. 지금까지 걸린 결함
   (spillback F1 인공물, 포착률 지표 혼동, `.sig` 오독)이 전부 이 부류였다.
5. **VISSIM 은 한 번에 하나만 실행한다.** 변경 없음.

## 유지되는 불변식

v2.1 의 물리·신호 불변식은 그대로 가져온다.

- 질량 보존 — stock 잔차 `<=1e-6 veh`, clipped-away mass 0
- **stock 내부 분해 항등식** — `queue + in-transit + movement composition = stock 질량`.
  외부 항등식과 내부 분해는 서로를 함의하지 않는다. 총량은 맞는데 분해가 어긋난 플랜트는
  N4-2 의 movement 귀속과 N3-1 의 큐꼬리 계산을 오염시킨다
- 정확 분할 — 링크→player 귀속 100%, unresolved vehicle mass 0
- `unobservable_count = 0`, `external_source_count = 0` (잔차로 균형 맞추기 금지)
- 신호는 `(SC, SG번호)` 정확 매핑. 이름·NEMA 산술·45도 방위 fallback 을 production 에 쓰지 않는다
- 상태 어휘 `PASS / FAIL / NOT_EVALUATED / BLOCKED` 고정

---

# 단계

## N0. 토폴로지 정합과 고정 — P0

**지금 상태.** A1 차로 그래프(2,649 차로 / 커버리지 1.000), 경로 증명(339 경로 / 유량오차 1.1e-16),
A2 one-stock 토폴로지(7,275 stock / 7,418 edge / 전 게이트 0 위반)가 실 네트워크에서 컴파일되고 PASS 한다.

### N0-1. v2.2 필수 역할 제거

`plant/src/vissim_strict/run_evidence.py:94-95` 의 닫힌 필수 소스 역할 집합에
`post_run_artifact_producer`(`build_run_artifact_manifest_v2_2.py`)와
`live_replay_builder`(`build_projection_live_evidence_v2_2.py`)가 들어 있다(`:108-109` 경로 맵도 같다).
**v3 는 이 두 생산자를 만들지 않으므로 preflight 가 영원히 FAIL 한다.**

**같은 계약이 여섯 곳에 독립으로 박혀 있다. 한 단계에서 함께 바꾼다.**
(초판은 세 곳이라 적었으나 실측하니 테스트 두 곳이 더 있었다.)

| 위치 | 무엇 |
|---|---|
| `plant/src/vissim_strict/run_evidence.py:86-99` | `PRODUCER_SOURCE_ROLES` 필수 역할 12 → 10 |
| 같은 파일 `:100-113` | `PRODUCER_SOURCE_DEFAULT_PATHS` 역할 → 경로 맵 |
| `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:553` | `$sourceBindings` 하드코딩 키 12 → 10 |
| `scripts/tests/test_build_preflight_manifest.py:419-441` | 두 역할 부재를 **FAIL 기대**로 고정 → PASS 기대로 |
| `scripts/tests/test_validate_baseline_snapshot.py:186-196` | 픽스처가 두 역할 파일을 합성 생성 |

파이썬만 고치면 워치독이 `Get-B1aWorkspaceRelativeFile` 에서 부재 파일로 throw 하고,
워치독만 고치면 `build_run_manifest_v2_1.py` 의 `producer_sources` **정확 집합** 검증이 거부한다.
닫힌 역할 우주를 픽스처로 고정한 테스트도 함께 바뀐다.

**PASS.** `build_preflight_manifest.py` 산출 `status=PASS`, reasons 0.
`RW_PYTHON_EXE` 를 정본 파이썬으로 고정한 상태에서 `verify_runtime_source.py` 도 PASS.
워치독 `-B1aDryRun` 이 소스 결속 단계를 통과.

### N0-2. 커넥터 진입 엣지 위치 정합

컴파일러/검증기 불일치 35건을 닫는다. 커넥터 진입 엣지의 `from_position_m` 이
`.inpx` 저장값(6자리 반올림)이고 stock 경계는 좌표 계산값(전정밀도)이라 정확 일치에서 갈린다.
차이는 최대 4.96e-07 m 다.

수정 방향은 **컴파일러**다. 엣지의 `from_position_m` 을 자기가 떠나는 stock 의 경계값으로 맞춘다.
원시 커넥터 위치는 A1 그래프에 출처로 남는다. 검증기의 정확 일치 규율은 건드리지 않는다.

### N0-3. 승인 아티팩트 생성

**초판의 정정.** v3 초판은 `topology_approval_v2_1.json` 을 만들지 않겠다고 했다. **오판이었다.**
`validate_state_projection_v2_1.py:22-26` 이 `validate_approval_artifact` 를 import 하므로,
승인을 빼면 **이미 완성된 투영 사슬 전체를 새로 써야 한다.** 승인 스크립트는 1,067줄이 이미 있고
동작한다. v3 가 걷어내려는 것은 **v2.2 쌍과 런 단위 출처 사슬**이지 토폴로지 결속이 아니다.

승인 아티팩트는 그래프·경로·토폴로지·preflight 가 서로 일치함을 한 파일로 묶는다.
이것은 물리 결속이며 유지한다.

```powershell
& $py -B scripts/approve_physical_stock_topology.py --workspace-root . `
  --preflight outputs/preflight_manifest_v3.json `
  --graph outputs/lane_route_graph_v2_1.json `
  --routes outputs/lane_route_proofs_v2_1.json `
  --topology outputs/physical_stock_topology_v2_1.json `
  --out outputs/topology_approval_v2_1.json
```

**현재 FAIL 이유와 대응.** 2026-08-07 실행 결과 두 코드가 나왔다.

| 코드 | 건수 | 닫는 단계 |
|---|---|---|
| `topology_structure_invalid` | 35 | **N0-2** |
| `topology_trust_mismatch` | 4 — v2.2 아티팩트 2 + preflight 비-PASS + status/reasons 불일치 | **N0-1** |

즉 N0-1 과 N0-2 가 끝나면 승인이 PASS 할 것으로 예상한다. 예상이 빗나가면 그 자체가 N0 의 산출이다.

### N0-4. state selection 생산자 — **완료 (2026-08-07)**

`state-selection-v2.1` 은 `build_state_manifest_v2_1.py` 가 **소비만** 하고
테스트가 픽스처로 만들 뿐 **생산자가 없었다.** `scripts/build_state_selection_v2_1.py` 를 새로 썼다.

**계약 소유자는 소비자다.** 생산자는 검증 규칙을 재구현하지 않고, 만든 뒤
`validate_state_selection` 을 스스로 호출해 잘못된 selection 이 하류가 아니라 여기서 죽게 한다.

sidecar 배제는 glob 이 아니라 **정규식 `^state_(\d+)\.json$`** 으로 한다. sidecar 가
`state_` 접두사를 물려받으므로 `state_*.json` 으로 훑으면 함께 걸린다(감사 쪽 N0 이전 결함과 같은 부류).

```powershell
& $py -B scripts/build_state_selection_v2_1.py --workspace-root . `
  --run-directory <런 디렉터리> --run-manifest <런 매니페스트> `
  --campaign-id <캠페인> --out outputs/state_selection_v2_1.json
```

**PASS.** `scripts/tests/test_build_state_selection.py` 4/4 —
소비자 수용, sidecar 미선택, `run_provenance` 부재 시 fail-closed, CLI 산출물 수용.

### N0-5. 토폴로지 해시 고정

`outputs/physical_stock_topology_v2_1.json` 의 SHA-256 한 줄을 `context-notes.md` 에 적고
이후 모든 실행이 그 값을 참조한다. N0-2 수정 후의 값이 정본이다.

**산출물은 커밋하지 않는다.** 그래프 2.7 MB + 경로증명 8.9 MB + 토폴로지 30.7 MB = 42 MB 이고,
git 은 모든 판을 영구 보관하므로 재생성할 때마다 같은 크기가 이력에 쌓인다.
셋 다 `.inpx` 와 입력 3개(`link_player_assignment` / `intersection_adjacency8` /
`urban_storage_capacity`)에서 아래 명령으로 결정적으로 재생성된다. **해시가 정본이다.**

```powershell
$py = $env:RW_PYTHON_EXE
$inpx = "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
& $py -B scripts/build_vissim_lane_graph.py --inpx $inpx --output outputs/lane_route_graph_v2_1.json
& $py -B scripts/resolve_lane_routes.py --inpx $inpx --graph outputs/lane_route_graph_v2_1.json --output outputs/lane_route_proofs_v2_1.json
& $py -B scripts/compile_physical_stock_topology.py --graph outputs/lane_route_graph_v2_1.json --routes outputs/lane_route_proofs_v2_1.json --ownership outputs/link_player_assignment_20260805.json --adjacency outputs/intersection_adjacency8_20260805.json --capacity outputs/urban_storage_capacity_20260805.json --output outputs/physical_stock_topology_v2_1.json
```

**PASS.** `validate_physical_stock_topology` 구조 오류 0.
재생성 결과의 SHA-256 이 `context-notes.md` 기록과 일치. 아래 실네트워크 테스트 전부 통과.

```powershell
& $py -m pytest -q scripts/tests/test_compile_physical_stock_topology_real_network.py `
                  scripts/tests/test_vissim_lane_graph_real_network.py `
                  scripts/tests/test_validate_sc12_shared_lane.py
```

2026-08-07 기준 이 세 파일 합계 **23개**가 통과했다. 개수는 테스트 추가에 따라 변하므로
**개수가 아니라 실패 0 이 게이트다.**

## N1. 차량단위 초기상태 투영 — P0

**목적.** VISSIM 을 한 순간 정지시켜 차량을 전부 긁고, A2 stock 위에 초기 상태를 확정한다.
MPC 롤아웃의 초기 조건이다.

**남기는 것.**
- `(run_id, sim_sec, veh_no)` 스냅샷 신원, 한 스냅샷 안 `veh_no` 중복 0
- 원시 `No/Lane/Pos/Speed` → A2 stock 배정, 배정 실패 0
- 루트 카운트 항등식 — `total_vehicles`, `stopped_vehicles` 가 records 에서 재유도한 값과 일치
- 링크별 카운트/정지 맵이 records 와 일치
- `unobservable_count = 0`, `external_source_count = 0`

**재사용하는 것 (초판의 정정).** 아래 v2.1 사슬은 **이미 완성돼 있고 검토를 거쳤다.**
새로 쓰지 않고 그대로 쓴다. v3 초판은 이것들도 걷어낸다고 읽힐 여지가 있었으나,
그렇게 하면 동작하는 코드를 버리고 같은 것을 다시 쓰게 된다.

```
build_run_manifest_v2_1.py         (573줄)   런 전 불변 매니페스트
approve_physical_stock_topology.py (1,125줄)  토폴로지 결속
build_state_manifest_v2_1.py       (1,384줄)  선택된 state 인벤토리
validate_state_projection_v2_1.py  (990줄)    투영 판정과 sidecar 발행
```

state 의 `run_provenance` 가 런 매니페스트와 결속되는 것도 유지한다.
이것은 "어느 런의 어느 시각인가" 를 확정하는 물리적 신원이지 출처 감사가 아니다.

**걷어내는 것.** `run-artifact-manifest-v2.2`, `projection-live-replay-v2.2`,
capture evidence sidecar 와 projection reference 의 별도 해시 아티팩트화,
timing receipt 의 독립 봉인, 사후 변조 탐지.

워치독 소스 결속에 대해서는 **v2.2 두 역할만** 뺀다(`ps1:553`, N0-1 이 처리).
나머지 10개 역할 결속과 `build_run_manifest_v2_1.py` 의 `producer_sources` 정확 집합 검증은
**유지한다.** 결속 사슬 전체를 지우면 매니페스트 생산이 즉시 거부된다.

**대체.** 스냅샷마다 `state_XXXXXX.json` 과 그 옆의 projection sidecar 하나.
런 식별은 **기존 `run-manifest-v2.1` 이 담당한다** — 별도 `run_config.json` 을 만들지 않는다.
`run_evidence.py` 의 `CONFIGURATION_FIELDS`/`SIMULATION_FIELDS` 가 설정·시드를 이미 담고
VBS 가 `vissim_version_raw` 를 기록한다. 워크스페이스 git commit 필드만 매니페스트에 추가한다.

**실행.** 초판은 "3600초 · 제어주기 60초 → 스냅샷 61회, 61/61 PASS" 로 적었다.
**그 기준은 달성 불가였다** — 61회는 stackelberg decision 61회를 전제하는데
단일 decision 이 1200초를 넘는다(N8-4 소관). 계획을 쓸 때 solve 시간 제약을 반영하지 않았다.

의존 관계를 드러내 둘로 나눈다.

### N1a. 캡처·투영 체인 — **완료 (2026-08-07)**

`no-control` + audit anchor 로 MPC 비용 없이 3600초 전 구간을 캡처한다.

```powershell
-SimPeriod 3600 -ControlIntervalSec 60 -StateLogIntervalSec 30 `
-Controller no-control -AuditAnchorsSec 900,1500,2100,2700 -B1aRequired
```

`allowed_capture_times = {1} ∪ ({900,1500,2100,2700} ∩ logTimes)` 로 5시점이 잡힌다.
**앵커 캡처는 `state_*` 가 아니라 `anchor_*` 로 저장된다.**

**실측 PASS.**

| 시점 | 차량 | 정지 | 레코드 | 미관측 | 외부 | 링크 |
|---|---|---|---|---|---|---|
| anchor_000900 | 2,193 | 536 | 2,193 | 0 | 0 | 282 |
| anchor_001500 | 3,365 | 873 | 3,365 | 0 | 0 | 334 |
| anchor_002100 | 3,776 | 1,126 | 3,776 | 0 | 0 | 346 |
| anchor_002700 | 4,088 | 1,355 | 4,088 | 0 | 0 | 334 |
| state_000001 | 6 | 0 | 6 | 0 | 0 | 5 |

`sim=3600` 완주, `observation_failures=0`, `decisions_failed=0`, `signal_failures=0`.

### N1b. MPC 캡처 61회 — **N8-4 대기**

`stackelberg` 로 61회 decision 을 완주해야 한다. 단일 decision 이 1200초를 넘으므로
**N8-4(런타임 계약)가 닫히기 전에는 착수 불가**다. N1a 가 캡처·투영 자체를 이미 증명했으므로
N2 이후는 N1b 를 기다리지 않는다.

### 잔여 (별건)

`COM_FAILURES=2` 가 `RUN_INTEGRITY_FAILURE` 를 낸다 — `DatabaseConnection` 모듈 비활성과
`SimSpeed=0` 최소값 위반. 시뮬레이션·캡처에 영향이 없는 시작 시점 설정 경고다.

런 후 처리는 N0-4 의 selection 생산자 → `build_state_manifest_v2_1.py` →
`validate_state_projection_v2_1.py` 순이다.

**PASS.** 61/61 스냅샷에서 배정 100%, 잔차 `<=1e-6 veh`, 위 항등식 전부 성립.

## N1.5. vendor 스냅샷 재앵커 파이프라인 — P0 — **완료 (2026-08-07)**

**초판에 빠져 있던 선행 과제다.** N0~N1 이 전부 `scripts/`·`plant/` 안에서 끝나서
드러나지 않았을 뿐, **N2 이후는 전부 NumSim 안에 있다.**

```
vendor/NumSim-mine/src/models/state.py             TrafficState        (N2)
vendor/NumSim-mine/src/models/urban_queue_model.py urban_substep       (N2, N3-1)
vendor/NumSim-mine/src/controllers/coupling.py     run_coupled_interval(N2)
vendor/NumSim-mine/src/controllers/stackelberg_mpc.py                  (N7, N8)
```

`verify_runtime_source.py` 가 96개 파이썬 blob OID 를 `UPSTREAM_TREE.json` 에 대조하고,
`SNAPSHOT.md` 와 검증기 상수 두 개(`EXPECTED_SNAPSHOT_COMMIT`,
`EXPECTED_PYTHON_FILE_COUNT`)가 같은 사실을 반복한다. **그 넷을 만드는 코드가 없었다.**
소비자만 있고 생산자가 없어 NumSim 을 한 줄만 고쳐도 사슬이 깨지고 되돌릴 방법이 없었다.

`scripts/update_numsim_snapshot.py` 가 그 생산자다.

```powershell
& $py -B scripts/update_numsim_snapshot.py --workspace-root . --upstream ..\NumSim-mine
# 이후 반드시: verify_runtime_source -> build_preflight_manifest -> approve_physical_stock_topology
```

**고정한 계약 5건.** 상류 커밋과 LF 정규화 blob OID 기록 / 소스 복사와 stale 제거 /
더러운 상류 트리 거부 / SNAPSHOT.md 여섯 행과 **앵커 상수 여섯 개** 동시 갱신 /
내용이 같으면 줄바꿈을 다시 쓰지 않음(다시 쓰면 `tracked_source_clean` 이 FAIL 한다).

**앵커 사실이 반복되는 여섯 지점** (실전에서 드러났다 — 초판은 둘만 갱신해 바로 막혔다).

```
verify_runtime_source.py    EXPECTED_SNAPSHOT_COMMIT
                            EXPECTED_ROOT_TREE
                            EXPECTED_SRC_TREE
                            EXPECTED_PYTHON_FILE_COUNT
                            EXPECTED_ANCHOR_SEMANTIC_SHA256
build_preflight_manifest.py EXPECTED_NUMSIM_COMMIT
```

앵커 semantic 해시는 `verify_runtime_source._semantic_json_sha256` 과 **정확히 같은 방식**으로
계산해야 한다(`ensure_ascii=True, sort_keys=True, separators=(",",":")`).

**재스냅샷 후 vendor 변경을 반드시 `git add` 하라.** 검증기는 커밋된 트리를 보므로,
안 하면 `tracked_source_clean` 과 `tracked_python_complete` 가 FAIL 한다.

**PASS.** 현재 스냅샷(`0240ba8`, 96파일)에 돌려 앵커 값이 완전히 동일하게 재현되고
`verify_runtime_source` 가 PASS 다. 테스트 5/5.

**NumSim 을 고치는 모든 단계는 이 순서를 따른다** — 상류 저장소에서 커밋 →
이 스크립트 → 사슬 재생성. 벤더를 직접 고치지 마라.

## N2. substep 질량 장부 — P0

v2.1 B-1 의 후반부. 스냅샷 사이 차량 이동을 복식부기로 기록한다.

```
closing_i = opening_i + accepted_external_i − sink_i + Σ_j F[j,i] − Σ_k F[i,k]
```

### 실측으로 갱신된 착수 상태 (2026-08-07)

| 항목 | 상태 |
|---|---|
| **post-update clipping 제거** | **이미 완료 — 할 일 없음** |
| 단일 `TrafficState.total_physical_vehicles()` | **완료** (상류 `72b37cc`, TDD 2/2) |
| `transfer_id` 복식부기 장부 | **미구현** — 저장소에 `transfer_id` 가 없다 |
| 내부 분해 항등식 | 미확인 |

**clipping 은 이미 무력화돼 있다.** `urban_queue_model.py:532` 의 `_queue_max` 가 `1.0e9` 를
반환하며 주석이 이유를 밝힌다 — *"큐 클립은 차량을 삭제해 보존 회계를 깬다. 공간 제약은
receiving-space allocation 이 담당한다."* `:1022-1032` 의 클립 코드는 남아 있으나 발동하지
않는다. **그 RED 는 만들 수 없다.** (`:139` 의 `movement_storage_capacity` 와 혼동하지 마라 —
그쪽은 밀도 정규화용이고 실 저장용량을 쓴다.)

### 완료 (2026-08-09, 상류 `7d05097`)

| 수용 기준 | 결과 |
|---|---|
| 전역 잔차 `<=1e-6 veh` | **PASS** — 109 시나리오 24스텝 최대 `6.7e-12` |
| 내부 분해 잔차 `<=1e-6 veh` | **PASS** |
| clipped-away mass 0 | **PASS** — `_queue_max` 가 이미 무력 |
| 수용포화 fixture 보존 | **PASS** — `urban_gridlock`(4677 veh) · `sweet_220`(9681 veh) |
| transfer 다중집합 / ID 중복 | **미구현 — 아래 판단 참조** |

**고친 결함.** `total_physical_vehicles` 가 off-ramp 램프 storage 를 세지 않았다.
`total_urban_vehicles` 는 "freeway 로 재귀속" 을 이유로 빼는데 `total_freeway_vehicles` 가
더하지 않아 어느 계정에도 없었다. 4 스텝 후 35.46 veh 누락. 되돌림 증명까지 테스트에 박았다.

**전역 항등식의 항.** 하나라도 빠지면 **상수** 잔차가 남는다 — 그게 누락의 신호다.

```
유입  urban_demand_arrivals_veh + onramp_arrivals_veh + freeway_mainline × T_c_h
유출  boundary_out_sink_veh + mainline_exit_flow_total × T_c_h
```

`mainline_exit_flow_total` 은 `avg_keys` 라 substep **평균 유량**[veh/h]이다. 합이 아니다.

### transfer ledger 를 만들지 않은 판단

`transfer_id` 복식부기는 `urban_substep`/`freeway_substep` 내부의 수백 개 유량 계산을 전부
계측해야 하는 대공사다. 그것이 추가로 잡아내는 것은 **상쇄 오류**(A 큐에서 5대가 잘못
B 큐로 가는데 총합은 그대로)뿐이고, 전역·분해 항등식이 이미 `1e-12` 로 서 있다.
비용 대비 수확이 맞지 않아 만들지 않았다. 필요해지면 N8 이후 별건으로 올린다.

### 남은 결함 2건 (N2 범위 밖 — 기록만)

**① off-ramp 거부 차량은 증발한다.** `schedule_offramp_arrivals` 가 거부한 차량은 이미
본선을 떠난 뒤인데 호출부가 어느 stock 에도 되돌리지 않는다. 지금은 게이트가
off-ramp **별**(`cap[off_ramp]`)이라 도달 불가지만, 같은 함수가 legacy 링크 합산
`cap[link]` 도 계속 내보낸다. 그리로 회귀하면 한 링크의 off-ramp 둘 중 하나만 포화된
순간 질량이 샌다. 비대칭 포화 강제 테스트로 불변식을 고정해 두었다.

**② `boundary_out` 출구 게이트가 링크 주행을 건너뛴다.** 게이트가
`min(점유, exit_cap·dt)` 를 쓰는데 점유에는 **아직 링크를 다 못 간 차량**이 포함된다.
실측으로 sink 링크 점유 1.02 veh 인데 release buffer 에 121.75 veh 가 남아 있었다 —
방금 진입한 차량이 지연을 다 채우기 전에 빠져나갔다는 뜻이다. 질량은 보존되지만
링크 통행시간이 과소평가된다. 물리 변경이라 파급이 커 N2 에서 손대지 않는다.

## N3. 관측 확장 — P0/P1

### N3-1. 속도·큐꼬리·통행지체
VBS 와 어댑터가 이미 내보내는 `link_speeds_kph` 와 정지 대수를 lane-group 운동학에 연결한다.
관측 속도가 있으면 전역 평균속도를 쓰지 않는다. 0 속도는 0 지체가 아니다.
FIFO 주행 버퍼와 정지선 서비스를 분리한다.

**PASS.** 통행시간 중앙값 `<=5 s`, p95 `<=15 s`, 큐꼬리 MAE `<=20 m`, 동일 substep 도착 0.

### N3-2. 출구와 목적함수
출구를 유한 `boundary_out` stock 으로 만든다. 목적함수 포함/제외는 **같은 물리 trace 에
다른 가중치만** 적용한다.

> #### ⚠️ 정정 (2026-08-10) — "226/226" 은 단위가 다른 두 수를 비교한 것이다
>
> | 수 | 정체 | 출처 |
> |---:|---|---|
> | **226** | **플랜트(VISSIM) 링크·커넥터** 번호 목록 (일반 77 + 커넥터 149) | `outputs/link_player_assignment_20260805.json` 의 `monitor_only_exit_links` |
> | **119** | **모델 stock 게이트** 수 | 실런 config 의 `boundary_out_links` |
>
> 모델 stock 으로 226 을 만들 수는 없다. **모델 측 기준으로 재정의한 119/119 는 달성했다** —
> sink 링크 전부 양수 용량, 누락 0, 중복 0, destination 별 sink 정확히 1개, sink 는 순수
> sink(approach_routing 소스 0, origin movement 0).
>
> **미해결로 남는 것.** 플랜트 226 링크 ↔ 모델 119 게이트의 대응 관계는 확인 못 함.
> 어댑터는 226 링크를 monitor-only 로 투영에서 제외하고 `exit_excluded_*` 진단만 낸다.

**PASS.** 출구 커버리지 **119/119(모델 stock 기준)**, 잔차 `<=1e-6`, 목적함수 모드 간
state/flow trace 동일, 목적함수 차이가 기록된 경계 기여분과 `<=1e-9` 일치.

> #### 착지 (2026-08-10) — 3/4 충족
>
> **고친 결함.** 출구 게이트가 `min(점유, exit_cap·dt)` 를 써서 **아직 링크를 다 못 간
> 차량까지 내보내고 있었다.** 실런 A/B(core15n41, 120 substep) 실측이다.
>
> ```
> sink 누적 이탈  26,311.59 → 22,620.52 veh   (−3,691.07)
> 물리 총량       53,622.81 → 57,313.88 veh   (+3,691.07)
> ```
>
> 두 수가 소수점까지 일치한다 — 질량은 원래 보존됐고 **통행시간이 과소평가**되던 것이다.

### N3-3. 램프·유출램프·고속도로
물리적으로 독립인 커넥터/차로 큐를 합치지 않는다. **스칼라 램프 상한 fallback 을 production 에서 금지**하고
stock 별 상한을 쓴다. 합류의 모든 유입은 우선순위 규칙이 명시된 하나의 하류 수용 예산을 공유한다.
SC1004 역할 재분류(F측 인터체인지)를 포함한다.

**PASS.** 램프 커넥터 누락/중복 0, 합류/분기 재배치 0, 그룹 유량과 물리 유량 합 차이
`<=1e-9 veh/substep`, 고속도로 구간 gap/overlap 0 m, production fallback 0.

## N4. N현시 신호 — P0

> ### 정본 결선 (2026-08-10 실측) — **core15n41 이다**
>
> **`control_mapping.json`(SC 1개, `id:"D"`) 결선은 죽은 경로다.** 현행 러너에서 두 겹으로
> 막힌다.
>
> 1. 생성 config 가 `RW_SCHEMA_VERSION = 2` 라 `LoadGeneratedConfig` 직후 `WScript.Quit 2`
>    (`run_real_world_stackelberg_controller.vbs:135, :140-144`).
> 2. 통과하더라도 매핑의 signal 행 id 가 `"D"` 인데 러너는 `UCase(id) = "SC"&sc_no` 를
>    요구해(`vbs:857`) 액션 CSV 전 행이 거부되고 `:874-882` 에서 종료한다.
>
> **실제로 도는 결선은 `core15n41`** — controlled 15 + monitor 26 = 41 SC 다.
> `run_plant_fidelity_matrix.ps1:43` 과 최신 실런(`n1_final_20260807`) 매니페스트가 그것을
> 가리킨다. `evaluation/generated/*.vbs` 11개 중 schema 3 은 core15n41 하나뿐이다.
>
> **따라서 "실런 도시부 모델은 합성 6노드 격자" 도 base 전용 서술이다.** core15n41 튜닝은
> `signals`·`uncontrolled_nodes`·`urban_movements` 를 통째로 교체한다.
>
> | | base | core15n41 |
> |---|---:|---:|
> | signals | 1 (`"D"`) | 15 (`SC1`…`SC1005`) |
> | uncontrolled_nodes | 기본값 `['E']` | 26 |
> | urban_movements | 78 | **1,414** |
> | urban_link_storage_veh | 29 | **302** |
>
> 이전 세션이 base 만 보고 "A/B/C/E 는 VISSIM 대응이 없다" 고 적었다. 그것은 죽은 경로에
> 대한 서술이었다. **N4 작업량이 1 SC 대 41 SC 로 40배 갈리므로 이 전제를 다시 뒤집지 마라.**
>
> **부수 정정 — ContrByCOM 실패는 제어 실패가 아니다.** `evaluation/runs` 전체 1,506건 중
> **1,504건이 `isolate_20260805` 한 런**에서 나왔고 그 런은 `SIM_SEC=0` 이다. 원인은 신호가
> 아니라 끊긴 정적경로(`Static Vehicle Route 1157 - 3 is not complete`)였고 이미 해소됐다
> (현재 `.err` 에 해당 오류 없음). 정상 런은 ContrByCOM 실패 0건이다.
> 다만 그 사건이 드러낸 **signal 액션의 fail-open 비대칭은 실재했고 닫았다**(2026-08-10).
>
> **낡은 토폴로지 주의.** `evaluation/strict_plant_20260731/canonical_topology.json` 은 소스
> 네트워크와 컴파일러가 둘 다 낡아 신호를 과소 계상한다(controllers 37 vs 실제 50,
> groups 392 vs 440, heads 475 vs 541). N4 는 반드시 재생성본을 써라.
> `python scripts/build_canonical_topology.py`
>
> ### 정본 타이밍 표 (2026-08-10 실측) — `outputs/signal_group_timing_v3.json`
>
> `scripts/derive_signal_group_timing.py` 가 실 `.sig` 에서 뽑는다. 제어 15 SC, SG 136개,
> 미해결 0.
>
> **정정(2026-08-10).** 처음 이 표는 파일명 끝자리 번호로 `.sig` 를 골랐고, 그 선택이
> inpx `supplyFile2` 와 4/15 SC 에서 달랐다(SC5/6/11/12). VISSIM 이 읽는 것은 inpx 쪽이라
> 그 넷의 주기·녹색·offset 이 전부 틀린 프로그램 위에 있었다. 생산자가 `supplyFile2` 를
> 읽도록 고친 뒤 수치가 아래처럼 바뀌었다 — SG 128→**136**, 동시녹색 쌍 160→**222**,
> 최악 과대 5.00→**5.47배**. 즉 문제는 보고돼 있던 것보다 **39% 크다**.
>
> | 항목 | 실측 |
> |---|---|
> | native 주기 | **140 / 150 / 160 / 170 s** |
> | 모델 `cycle_length` | **120 s 하나** (`state.py:225`) — 실망에 120 s 는 없다 |
> | 이름 규칙이 만드는 동시녹색 쌍 | **222 쌍** |
> | 최악 녹색 과대평가 | **5.47배** |
>
> **원인은 하나다.** SG 상태를 정하는 유일한 경로가 이름 부분문자열이다
> (`vbs:1285-1299` — EB/WB → major, NB/SB → minor). `(SC, SG번호) → 모델 phase` 매핑이
> 저장소에 없다. SC1001 실측 분율은 0.120~0.340 인데 규칙은 두 값(0.300/0.340)으로 뭉갠다.
> WBL(48–72 s)과 EBT(0–45 s)는 겹치지 않는데 둘 다 major 를 받아 대향 좌회전이 대향 직진을
> 횡단한다. `.sig` 41개 전부 `<intergreenmatrices />` 가 비어 VISSIM 도 막지 않는다.
>
> **N4-3 은 만드는 일이 아니라 배선하는 일이다.** N현시 적분기가 이미 있다 —
> `plant/src/vissim_strict/signal_program.py:85-110 green_overlap_phase`.
>
> ### 착지 상태 (2026-08-10)
>
> | 항목 | 상태 |
> |---|---|
> | **N4-4** fail-closed | ✅ 조용한 폴백 4곳이 전부 `MonitorFixedSignalPatchError` |
> | **N4-1** 배관 | ✅ `cycle_length_by_signal` + `signal_cycle_length()` + 폴백 카운터 |
> | **N4-1** 매핑 채우기 | ❌ **의도적 미착수** — green 예산이 아직 전역이라 채우면 회계가 깨진다 |
> | **N4-3** 배선 | ⚠️ **부분** — 229/698 movement 에 적용, **304건(43.6%)이 아직 2현시** |
> | **N4-2** movement→SG 매핑 | ⚠️ **부분** — 아래 참조 |
> | **N4-5** action 스키마 N현시 | ✅ 완료 (2026-08-10). 아래 참조 |
> | **N4-6** timing oracle (D-core) | ⚠️ **BLOCKED** — 판정기는 완성, 게이트는 못 넘는다. 아래 참조 |
>
> #### N4-2 착지 (2026-08-10) — 분모를 바꿔서 봐야 한다
>
> 미해결 **304 → 282**. 겉보기 감소가 22건뿐인데, 그 이유는 legacy 가 조용히 **틀리게**
> "해결" 로 세던 24건을 새 매핑이 미해결로 되돌렸기 때문이다.
>
> 제어 movement 698 = **물리 movement 416** + **모델이 만든 가상 경계 leg 282**(`in_<SC>_<방위>`).
>
> | | 작업 전 | 작업 후 |
> |---|---:|---:|
> | 물리 movement 해결 | 370/416 (88.9%) | **416/416 (100%)** |
> | `no_signal_group_mapping` | 282 | **0** |
> | `axis_mismatch` | 22 | **0** |
> | `synthetic_boundary_leg` | — | 282 |
> | **이름규칙 폴백** | 698 / 416 | **0 / 0** |
>
> **남은 282는 해결 불가다.** 경계 leg 은 `generate_real_world_distributed_players.py:391-397`
> 이 인접 없는 방위에 심은 수요 게이트라 VISSIM 에 대응 링크·신호두가 **아예 없다** —
> 경계 origin 119개 중 링크를 가진 것이 0개임을 강제 해결 시도로 확인했다.
> 잔차 뭉개기가 아니라 구조적 부재다.
>
> 해결 방법별 내역은 `origin_link_head` 333 / `connector_chain` 53 / `shared_leg_bearing` 30.
> 산출물은 `outputs/movement_signal_group_map_v3.json`.
>
> **N4-3 은 계획의 PASS("scalar-cycle fallback 0")를 아직 못 맞춘다.** 미해결 304건의 내역은
> `no_signal_group_mapping` 282 · `axis_mismatch` 22 다. 둘 다 N4-2 가 없어서 생긴다.
>
> **효과는 실재한다.** SC1001 movement 54개 중 21개(38.9%)의 녹색분율이 바뀌었고, 실측 대비
> 오차가 **1.56배·1.21배 → 1.01배·0.97배**로 줄었다. 질량 보존은 N4-1·N4-3 을 **동시에 켠**
> 상태에서 24스텝 최대 잔차 `1.148e-11 veh` 로 성립한다(동역학이 실제로 바뀐 것은 같은
> 시나리오 총 대수가 baseline 대비 1.2~3.7배 갈리는 것으로 확인).
>
> **모델↔플랜트 비대칭이 열려 있다.** 모델은 native 분율로 예측하는데 러너는 여전히 이름
> 규칙 2현시로 구동한다(N4-5). N9 짝지은 검증 전에 반드시 닫아야 한다.
>
> #### N4-5 착지 (2026-08-10) — 축 안의 분배만 닫았다
>
> 축 녹색 시간의 **단조 재매개화**로 축 창을 SG 별로 쪼갠다. SG g 의 realize 녹색이
> `지시 축 녹색 × union_green(g) / union_green(축)` 이 되어 모델 share 와 **같은 분수**다.
> 축의 위치·길이·주기 공식은 그대로다.
>
> | | 값 |
> |---|---:|
> | 계획된 SG | 136 (VISSIM 선언 SG 전부, 미커버 0) |
> | 녹색창 | 118 |
> | 영구 적색 SG | 20 (inpx 프로그램에 녹색창이 없다 — 이름 규칙은 이들에게 축 녹색을 통째로 줬다) |
> | 동시녹색 금지 쌍 | 312 |
> | 계획 자체의 위반 | 0 |
>
> **정본 타이밍 표를 쓰지 않았다.** `signal_group_timing_v3.json` 은 파일명 번호로 `.sig` 를
> 골라 SC5/6/11/12 에서 inpx `supplyFile2` 와 다른 프로그램을 기술한다(주기 140↔160,
> 100↔160, 160↔150, 150↔140). VISSIM 도 모델도 inpx 를 읽으므로 계획도 inpx 에서 나온다.
> 표는 고치지 않고 산출물의 `timing_table_disagreements` 로 남겼다.
>
> **작업 중 발견한 실제 버그.** 러너는 매초 돌지 않는다. `NextSignalTransitionAfter` 가
> `SignalCompositeStateAt` 이 바뀌는 초까지 `RunContinuous` 한다. 그 합성 상태가 2현시 축만
> 보고 있어 **축 안의** SG 경계가 이벤트가 아니었다. 고쳤다.
>
> **아직 열려 있는 것.** 주기가 여전히 다르다 — 모델은 `signal_cycle_length()`(현재 전역
> 스칼라), 플랜트는 `major + minor + 10` 이다. N4-5 는 축 안의 분배만 닫았다.
>
> #### N4-6 착지 (2026-08-10) — 판정기는 완성, 게이트는 BLOCKED
>
> **valid-interval 계약.** `stage=immediate(t)` 는 t 에 쓴 값이 그 자리에서 되읽혔음만,
> `stage=post_step(t')` 는 t 의 값이 t' 까지 유지되었음만 입증한다. 유효 구간은 `[t, t')`
> 이고 증거는 **양 끝점 두 표본뿐**이다. 구간 내부는 표본이 없다.
>
> | gate | 결과 |
> |---|---|
> | plan_self_conflict | PASS |
> | cycle_wrap | PASS |
> | command_quantization_sec | **FAIL 0.990 s** (게이트 0.5 s) |
> | min_green_sec | NOT_EVALUATED — `.sig` 의 `<intergreenmatrices/>` 가 비어 권위가 없다. 최단 계획 녹색 7.28 s |
> | transition_time_error_sec | **BLOCKED** — readback 격자 1 s > 게이트 0.5 s |
> | readback 5개 게이트 | NOT_EVALUATED — 실 런 필요 |
>
> **핵심은 `command_quantization_sec` 다.** 계획의 창 경계는 실수인데(지시 축 녹색 × native
> 분율) 러너는 정수 초에만 쓴다. 실현 전이는 의도의 올림이라 오차가 최대 0.99 s 다.
> 이 값은 계획과 쓰기 격자만으로 정해지므로 **실 런 없이 재진다**.
>
> 따라서 D-core 는 PASS 가 아니고, **N4-7 삼중 잠금에 따라 offset production writer 는
> 계속 잠겨 있다.** 판정기는 `evaluation/controllers/signal_timing_oracle.py` +
> `scripts/verify_signal_timing_oracle.py` 다.

### N4-1. SC별 고유 주기 (v2.1 X-1)
원본 network/SIG 를 바꾸지 않고 SC별 실제 주기를 `NetworkConfig` 에 넣는다. N4-2 의 선행조건이다.
150초 정규화 실험은 **이 계획에서 제외**한다(별도 과제).

### N4-2. movement / SG 매핑
`head lane → 커넥터 → 목적지 stock → movement` 추적. 키는 `(SC, SG번호)`.
정확 매핑이 없는 차량 질량은 항상 unresolved 이며 각도 fallback 으로 PASS 처리하지 않는다.
공용 차로(SC12)는 stock 하나와 movement 조합을 쓴다.

**PASS.** 정확 커버리지 100%, unresolved vehicle mass 0.

### N4-3. N현시 녹색분율
`_phase_green_fraction` 이 원시 타임라인의 부분 step 녹색을 적분한다. clearance 는 실제 SIG 를 쓴다.
**기존 N=2 경로는 bit-identical 유지.**

**PASS.** N=2 경로 bit-identical, SC별 주기 재구성 오차 0, native production 에서 scalar-cycle fallback 0.

### N4-4. monitor 26개 고정 타임라인
monitor node 를 "항상 녹색" 이 아니라 "고정 스케줄, 제어 불가" 로 재생한다.

**PASS.** monitor always-green movement 0, 영구적색 녹색분율 0, monitor 큐/저장이 물리적으로 갱신됨.

### N4-5. action 스키마 fail-closed
N현시 action 은 stage duration 또는 tangent 좌표를 가진다. 모델 state·action CSV·VBS config·readback 이
불일치하면 적용하지 않는다.

**PASS.** 부분 적용 0, request/readback 불일치 0, 공용차로 SG 제약 위반 0, 충돌 SG 동시녹색 0,
최소녹색/clearance 위반 0.

### N4-6. 신호 timing oracle (D-core) — P1

**v2.1 D 를 그대로 유지한다.** 이것은 증거 출처 관리가 아니라 **액추에이션 충실도**다.
명령한 신호가 VISSIM 에 실제로 그 시각에 들어갔는지를 검증한다. 여기가 틀리면 아래 모든
동적 검증이 엉뚱한 것을 측정한다.

`D-core` 가 검증하는 것.

- 예상 전이 대 **즉시 및 step 이후 COM readback**
- source offset 과 command lag, **양의 lag 부호**
- 주기 경계 처리와 SC별 고유 주기 (N4-1 의존)
- 충돌 SG 와 최소녹색

**green-only production release 는 D-core 뒤에 온다.** 즉 D-core 가 PASS 하기 전에는
녹색 레버조차 production 으로 내보내지 않는다.

**PASS.** 전이 시각 오차 `<=0.5 s`, request/readback 불일치 0, 명령 지연 부호 오류 0,
충돌 SG 동시녹색 0, 최소녹색/clearance 위반 0, 주기 wrap 경계 오류 0.

**readback 주기 분기 (v2.1 J-4 에서 유지).** `0.5 s` 게이트는 readback 해상도가 그보다 고와야
측정 가능하다. **실 readback 이 1 Hz 뿐이면 이 게이트는 PASS 가 아니라 `BLOCKED`** 다.
측정 불가를 통과로 처리하지 마라. 이 경우 N4-7 offset 승격도 함께 막힌다.

### N4-7. offset 승격 잠금 (D-offset-enable) — P1

offset 은 **삼중 잠금**이다. 하나라도 빠지면 production writer 를 열지 않는다.

```
D-offset-enable = D-core(같은 신호 profile + 같은 topology SHA-256)
                ∧ N9 offset 효과·순위 게이트
                ∧ N8-4 런타임 게이트
```

- D-core PASS 전까지 production writer 는 **`intent_only`** 다. 의도만 기록하고 COM 에 쓰지 않는다.
- D-core PASS 후에도 **격리된 시험 harness 의 test-only writer** 만 강제 offset arm 을 낼 수 있다.
  production writer 는 삼중 잠금이 모두 PASS 할 때 열린다.
- 승격되지 않은 profile 의 nonzero offset 기록은 **fail-closed 로 거부**한다.
- 주기 정규화 실험(150초 등)을 별도로 수행하더라도 그 결과는 **native offset 을 활성화하지 못한다.**

**PASS.** 미승격 profile 의 production offset write 0, `intent_only` 우회 0,
test-only writer 가 production 경로에 도달한 경우 0.

#### N4-7 착지 (2026-08-10) — 잠금은 걸렸고, 열 수 없는 상태가 맞다

**착수 전 상태를 먼저 확인했다. 잠금은 걸려 있지 않았다.** 모델(`urban_follower._offsets`
+ `offset_price` + `joint_green_offset`)이 고른 offset 이 `control.offsets` → action CSV
`offset` 열 → 러너 `sigOffset` → `FMod(simSec + offset, cycle)` 로 **COM 까지 그대로**
갔다. 과거 action CSV 9831개 중 191개가 nonzero offset 을 담고 있다. 즉 "D-core PASS
전까지 production writer 는 intent_only" 는 지켜지지 않고 있었다.

**권위는 `evaluation/controllers/offset_promotion.py` 하나다.** 판정은 상수가 아니라 증거
산출물에서 나온다 — `outputs/offset_promotion_{d_core,n9_offset_effect,n8_4_runtime}.json`
셋이 모두 있고, 모두 `status=PASS` 이고, 셋이 **같은** `signal_profile_id` +
`topology_sha256` 를 가리킬 때만 열린다. 사람이 상수를 고쳐서 여는 길은 없다.

| writer | 누가 정하나 | 무엇을 쓰나 |
|---|---|---|
| `intent_only` | 기본값 | 아무것도. 의도는 action JSON `offsets` 에 남는다 |
| `test_only` | 격리 harness 가 config 로 선언 | **강제 arm 만**. 최적화기 offset 은 안 나간다 |
| `production` | **증거만** | 최적화기 offset |

`production` 은 config 로 선언할 수 없다(`OffsetPromotionError`). 선언 없는 런에 강제 arm 이
오면 0 으로 뭉개지 않고 런을 세운다 — 조용한 0 은 나중에 "offset 효과 없음"으로 읽힌다.

**자물쇠는 두 겹이다.** 러너의 `RW_OFFSET_WRITER`(기본 `intent_only`)는 증거를 읽을 수
없으므로 권위가 아니다. 보장하는 것은 "선언하지 않은 런은 offset 을 액추에이션하지 못한다"
하나이고, 위반이면 기존 전량 거부 자리에서 action CSV 전체를 거부한다.

**N9 행렬은 유도한다.** `LEVER_STATUS/LEVER_WRITER["offset"]` 을 손으로 적지 않고
`offset_promotion.matrix_lever_*()` 에서 받는다. 오늘 값은 `BLOCKED` / `test_only` 이고
seal 은 `d397fa07d1c05692` 로 불변이다.

**열 수 없는 것이 맞다.** D-core 가 `command_quantization_sec` FAIL 0.990 s /
`transition_time_error_sec` BLOCKED 이므로 증거 산출물 세 개 중 하나도 만들 수 없다.
N8-4 런타임 게이트는 아직 존재하지 않는다(파일 이름만 잡아 뒀다).

## N5. 개발 데이터와 잡음 바닥 — P0

VISSIM 을 순차 실행해 개발용 부모 런을 만든다. anchor `900/1500/2100/2700` 의 상태를 보존한다.

**부모 런 (v2.1 의 18개에서 축소)**

| 용도 | demand | seed | 개수 |
|---|---|---|---|
| training | 0.75, 1.0 | 13, 29 | 4 |
| congested | 1.25 | 13, 29 | 2 |
| holdout | 0.75, 1.0, 1.25 | 47 | 3 |

**총 9개.** SPSA 전용 seed 31 은 training 과 공유한다(별도 3개를 만들지 않는다).
인증 wave 3개 시드(47/59/71) 대신 holdout 단일 시드(47)를 쓴다.

**잡음 바닥 — 두 개다. 절대 혼용하지 마라.**

각 부모-anchor 에서 독립 `t=0` base replay 를 **20회** 실행해
`eps_J_vissim = max(1e-6 veh·h, max_{i,j}|J_base_i − J_base_j|)` 를 동결한다.
**이 부분은 축소하지 않는다.** 이후 모든 "효과가 실재하는가" 판정의 기준선이기 때문이다.

**이것은 VISSIM 런간 분산 척도이고 N9 의 `ΔJ` 재료성 판정 전용이다.**
플랜트 endpoint 의 재현성 잡음 `eps_J_endpoint` 는 **별개이며 N8-1 에서 따로 측정한다.**
v2.1 도 둘을 따로 정의했다 — `IMPLEMENTATION_PLAN.md:359`(하한 `1e-6 veh·h`)와
`:473`(하한 `1e-9`). 하한이 세 자리 다르고 재는 대상이 다르다.
**v3 초판은 하나로 합쳐 VISSIM 척도를 endpoint 자리에 넣었다.** 그러면 `eps_g` 가 과대해져
`|intercept| <= median(eps_g)` 가 느슨해지고 재료 표본이 줄어 지지 요건이 무너진다.

**PASS.** 부모 9/9, anchor 완비, 누락/중복 0, base replay 부모-anchor 당 `>=20`,
training/holdout 시드 중복 0.

## N6. 캘리브레이션 — P1

`evaluation/calibration/physical_stock_calibration_v3.json` 에 run ID/split, 추정기, 표본 수,
차량 길이+정지간격 prior, 적합값, run-cluster bootstrap 95% CI, jam density, 램프/출구 저장·방류를 기록한다.

- jam density 는 `speed <= 3 kph`, 정지분율 `>= 0.5` 인 포화 lane-group 에서 robust fit
- 큐꼬리 관측이 있으면 고정 분율(0.35/0.50) 대신 관측 분해를 쓴다
- **적합은 training 시드에서만.** holdout 시드는 적합·임계선택·후보교체에 쓰지 않는다

**PASS.** split 중복 0, 포화 독립 lane-group `>=30`, 표본 `>=200`,
jam CI 반폭 `<= 추정값의 10%`, geometry prior 차이 `<=15%`, training 시드별 적합 차이 `<=15%`,
fallback 분율 사용 `<=10%`.

## N7. production MPC rollout endpoint — P0

순수 함수 `evaluate_price_point(state, previous, forecast, action_schedule, objective_spec)` 를 만들고
`stackelberg_mpc.py`, `stackelberg_wu_metered.py`, 어댑터의 실제 `decide_with_info` 경로에 통합한다.

- MPC 가 후보 생성·목적함수 비교·action 선택을 소유
- endpoint 는 상태 투영·제어독립 동역학·제약·레버 반응·목적함수 성분만 평가
- exact FD, SPSA, no-control replay 가 **전부 같은 endpoint 와 동결 파라미터**를 사용

**PASS.** 채널 커버리지 100%, endpoint 호출 수 = 후보 평가 수, 우회 호출 0,
one-step / H=3 통합 테스트 PASS.

> ### 착지 (2026-08-10) — 3/4 충족, **우회 7곳 남음**
>
> `src/controllers/rollout_endpoint.py` 신설. 정본 Stackelberg decide 경로
> (`stackelberg_mpc.py` · `stackelberg_wu_metered.py` · `wu_faithful_follower.py`)의
> `run_coupled_interval` 직접 호출은 **0** 이다.
>
> | 구분 | 수 |
> |---|---:|
> | 정본 decide 경로 우회 | **0** |
> | endpoint 본체 · plant 전진 (정당) | 2 |
> | **NumSim 잔여 우회** | **5** — `analysis/stage2_mechanism.py:133`, `centralized_mpc.py:299,:328`, `distributed_coordinator.py:673`, `wu_distributed.py:862` |
> | **어댑터 잔여 우회** | **2** — `adapter:2503`(`flagship_sup_score`, **후보 채점이라 진짜 우회**), `:3672`(`build_one_step_prediction`) |
>
> 계획의 "우회 호출 0" 은 **미충족**이다. 어댑터 `:2503` 이 후보를 채점하므로 실질적이다.
> vendor 가 `5a2fe7d` 로 재앵커돼 이제 어댑터가 endpoint 를 import 할 수 있다 —
> 그전까지는 `rollout_endpoint.py` 가 스냅샷에 없어 통합 자체가 불가능했다.

## N8. marginal price 와 런타임 — P0

### N8-1. exact FD 대 SPSA 자격심사
FD 와 SPSA 가 하나의 production endpoint 를 호출한다. endpoint control, 목적함수 성분, feasibility,
종단 상태, 실현 섭동 폭이 동일하지 않으면 비교 자체가 FAIL 이다.

- **endpoint 재현성 잡음을 먼저 잰다.** qualification state 마다 **동일 control** 목적함수를
  최소 20회 평가해 `eps_J_endpoint = max(q99(|J_r − J_1|), 1e-9·max(|J_1|, 1))` 를 구한다.
  **`eps_g` 는 오직 이 값으로만 환산한다** — `eps_g = 2·eps_J_endpoint / realized_span`.
  N5 의 `eps_J_vissim` 을 여기 쓰지 마라(척도가 다르다). 목적함수 단위 잡음을 기울기와 직접 비교하지 않는다
- 중앙차분을 `h` 와 `h/2` 에서 비교. `|g_h − g_h2| <= max(eps_g, 0.10·max(|g_h2|, eps_g))`.
  사전 등록 수렴 tolerance 실패는 required coordinate 의 **`INDETERMINATE`/`BLOCKED`** 이지 PASS 가 아니다
- 사전 등록 전진폭 — 녹색 `6 s`, VSL `10 km/h`, offset `C/8`, 램프미터 `max(300 veh/h, 0.20·capacity)`.
  두 추정기 모두 요청 폭이 아니라 **경계된 실현 변위**로 나눈다
- SPSA 쌍 개수 `k ∈ {8,16,32,64}`, state 당 독립 방향 batch **20개** (v2.1 의 30에서 축소).
  모든 stratum 을 통과하는 최소 `k` 를 동결한다
- 좌표는 `|g_fd|·realized_span >= max(5·eps_J_endpoint, 0.005·max(|J0|,1))` 일 때만 material.
  bound 로 붕괴된 좌표는 zero gradient 가 아니라 **ineligible** 이다

**stratum 지지 요건 (v2.1 I-1 에서 유지).**

- 전체 최소 **12 state cluster** 가 모든 demand, H, 채널, free/congested 와
  active/inactive barrier regime 을 덮는다
- 각 `채널 × demand × H` stratum 은 독립 state cluster 최소 12 와 nonempty material set 을 요구한다
- **required stratum 이 지지 미달이면 빈 remainder PASS 가 아니라 `BLOCKED`** 다
- 부호 통계는 **state-direction batch 당 사전 등록한 좌표 하나만** 독립 Bernoulli 로 센다.
  여러 좌표를 같은 SPSA 쌍에서 독립 표본처럼 세지 않는다
- N현시 신호는 결정적 Helmert `(N−1)` tangent 기저를 쓰고 N=2/3/4/5/6 과 모든 active N 을 시험한다

**raw 레버 표나 material remainder 가 빈 결과는 자격 근거가 아니다.**
`k` 와 모든 임계치는 holdout 을 열기 전에 동결한다.

**PASS.** nRMSE 상한 `<=0.20`, 기울기 CI 전체 `0.90..1.10`, `|intercept| <= median(eps_g)`,
재료 부호 반전 0. 부호 오류 Clopper-Pearson 95% 상한 전체 `<=0.05` (재료 비교 `>=59`),
채널별 `<=0.10` (`>=29`).

### N8-2. 결정 동등성
기울기만 비교하지 않는다. holdout 상태 **12개** × 방향 seed 3개 = **36 twin** 에서
후보집합·순위·선택 action·제약·spillback 가드·미터 방류를 FD 와 SPSA 사이에 비교한다.

**산술 근거.** N5 의 holdout 은 `demand 3 × seed 47` = 부모 3개이고 anchor 는 4개이므로
상태 상한이 **3 × 4 = 12** 다. v2.1 은 부모 9개(demand 3 × seed 47/59/71) × anchor 4 = 36 상태에서
108 twin 이었다. **v3 초판은 시드축을 3→1 로 줄이면서 상태 수만 36→18 로 절반만 줄여 산술이
성립하지 않았다.** 12 는 N5 가 실제로 공급할 수 있는 상한이다.

**36 twin 이 부족하다고 판단되면** N5 의 holdout 을 시드 47/59 두 개로 되돌려
6 부모 × 4 anchor = 24 상태를 확보하고 그중 사전 등록분을 쓴다. 그 경우 사전 등록 절의
시드 항목도 함께 고친다. **런 전에 어느 쪽인지 확정한다.**

**PASS.** 상태·feasibility·안전 인증서·fallback 등급·리더 후보 36/36 정확 일치.
명령은 정확 일치 또는 선언된 양자화 1단계 이내,
exact-FD 재채점 regret `< max(2·eps_J_endpoint, 0.5%·|J_FD|)`.

### N8-3. 통합 rollout 스케줄러
녹색·미터·VSL·offset 의 독립 rollout 을 하나의 deadline-aware 스케줄러에 넣는다.
Windows spawn-safe worker, task timeout/cancel, 결정적 축약.

**PASS.** workers 0/1/2/5 에서 후보 목적함수/가격 차이 `<=1e-9`, 선택 action 정확 일치,
병렬 예외 뒤 조용한 직렬 재실행 0.

### N8-4. 런타임 계약
두 시계를 기록한다 — `decide_with_info` 내부 시간과, anchor 관측 스캔부터 검증된 COM readback 까지의
end-to-end. **운영 게이트는 end-to-end 만** 본다.

```
30초  목표 초과 이벤트
42초  어댑터/워커 프로세스만 종료 (VISSIM 은 paused/alive 유지)
 3초  fallback 생성·검증·적용·readback 예약
45초  최대
```

표본은 `demand × cold/warm` stratum 마다 **최소 50 attempt, 독립 VISSIM 런 최소 5개**
(v2.1 은 100 attempt / 10 런).

**PASS.** stratum 별 p95 `<=30 s`, 관측 최대 `<=45 s`, controller fallback `<5%`, timeout `<1%`,
조용한 fallback / 낡은 action / readback 실패 / 고아 워커 0.

## N9. 짝지은 VISSIM 검증 — P1

> ### 규모 실측 (2026-08-09) — **N8 이 N9 의 성립 조건이다**
>
> `scripts/build_experiment_matrix_v3.py` 로 행렬을 실제로 전개한 결과다.
> 산출물은 `outputs/experiment_matrix_v3.json`, 봉인 `d397fa07d1c05692`.
> 시드는 N5 부모 런과 일치시킨 `{13, 29, 47}` 이다.
>
> | 항목 | 값 |
> |---|---|
> | 전체 셀 | 2,160 |
> | 실행 대상 | 1,620 |
> | BLOCKED (offset, N4-6 대기) | 540 |
> | 총 시뮬레이션 시간 | **994 h** |
> | 제어 결정 | **59,616 회** |
>
> 60배속이어도 순수 VISSIM 벽시계가 17시간이다. 여기에 **결정마다 solve** 가 붙는다.
>
> **결정당 solve 비용 (2026-08-10, 실 런로그 217개에서 추출).** 이전에 이 자리에 있던
> "300초" 는 근거가 없었다. `CONTROLLER_DECISION ... wall_sec=` 이 실측을 남긴다.
>
> | controller | 중앙값 | p95 |
> |---|---:|---:|
> | `pstack-flagship` (실 MPC) | **11.0 s** | 12.9 s |
> | `stackelberg` | 8.0 s | 10.0 s |
> | `no-control` | 1.0 s | — |
>
> 따라서 N9 총비용은 이렇다.
>
> ```
> solve   59,616 결정 × 11.0 s ≈  182 h ≈ 7.6 일   (p95 기준 214 h ≈ 8.9 일)
> VISSIM  994 시뮬시간 → 30배속 33 h / 60배속 17 h
> ```
>
> **즉 N9 는 단일 기기에서 8~9일 규모다. 불가능하지 않다.** N8 최적화가 solve 쪽을 더 줄인다.
>
> 줄일 수 있는 축은 replicate(현재 1)와 holdout 시드다. **진폭·anchor·H 는 사전등록이라
> 사후 조정 금지**다 — 줄이려면 런 전에 spec 을 고치고 봉인을 다시 찍어야 한다.
>
> **합성 측정을 믿지 마라.** `TrafficState.initial` 에 균일 수요(경계 117링크 각 300 veh/h)를
> 꽂아 같은 config 로 solve 를 쟀더니 이렇게 나왔다.
>
> ```
> solve 1,144 s      _leader_direct_feasible_set_diagnostics 호출 65,721 회
> ```
>
> 실 런은 11초다. **100배 차이의 원인은 코드가 아니라 상태다** — 관측 상태에서 출발하지 않으면
> 리더 target 이 도달 불가라 탐색이 후보를 소진한다(default.yaml 은 11,799 회, 여기선 5.6배).
> 비용을 재려면 런로그의 `wall_sec` 을 써라. 합성 상태로 잰 값을 계획에 넣지 마라.

### N9-1. replay 신원
VISSIM 스냅샷 복원을 믿지 않고 모든 branch 를 `t=0` 부터 재실행한다.
플랜트와 VISSIM 이 동일한 schedule entry, 활성화 경계, 반열린 구간 `[start, end)` 를 쓴다.

런 키는 v2.1 의 21필드에서 축소한다.

```
(experiment_id, inpx_hash, topology_sha256, calibration_version,
 controller_version, demand, seed, anchor_sec, H, channel, lever_id,
 action_payload_hash, replicate)
```

### N9-2. 실험 행렬
demand `0.75/1.0/1.25`, 런 3,600초, warm-up 900초, anchor `900/1500/2100/2700`,
H `1/3/5/10/15`, 제어주기 60초. VISSIM 은 한 번에 하나만 실행한다.
기본은 **레버 하나씩 low/base/high** 이며 joint action 은 별도 experiment ID 다.
development 진단은 시드 13/29, 승격 판정은 holdout 시드만 쓴다.

**feasible low/high — 사전 등록 진폭 (v2.1 J-2 유지).**

| 레버 | 진폭 | cap |
|---|---|---|
| green | base 대비 `-10 / +10 s` (정본 tangent 기저) | 최소녹색 · clearance · 주기 |
| VSL | base 대비 `-10 / +10 km/h` | actuator bounds |
| ramp meter | base 대비 `-150 / +150 veh/h` | actuator bounds |
| offset | base 대비 `-10 / +10 s` (native cycle modulo) | **test-only writer 전용**, N4-6 D-core PASS 후 |

offset 은 production writer 와 분리된 test-only writer 가 적용한다. 실현 readback 이 같은
valid-interval 계약을 입증하지 못하면 offset 은 `NOT_EVALUATED`/`BLOCKED` 이고
production writer 는 `intent_only` 로 남는다(N4-7).

세 값이 서로 구별되지 않으면 그 셀을 `NOT_EVALUATED` 로 기록하고 **더 작은 대칭 step 을 한 번만**
시도한다. 값을 사후 조정하지 않고 요청 매니페스트에 정확한 값을 먼저 봉인한다.

### N9-3. 집계
VISSIM 1초 관측을 보존하고 60초로 집계한다. `ΔJ(action) = J(action) − J(base)` 를 같은 prefix 에서 계산한다.
반복은 잡음만 추정하고 표본 수를 늘리지 않는다.
controlled 15 / monitor 26 / midblock 9 / boundary / ramp / freeway 를 분리한다.

### N9-4. 합격 게이트
**H=1 은 독립 게이트다.** 다른 H 로 구제하지 않는다.

| H | 게이트 |
|---:|---|
| 1 | 도시부 큐/저장 NMAE `<=15%`; 통행 중앙값/p95 `<=5/15 s`; 꼬리 MAE `<=20 m`; 속도 MAPE `<=10%`; count MAE `<=max(5 veh,10%)`; GEH `<=5` 인 행 `>=85%`; **signed flow bias `<=10%`**; TTT APE `<=10%` |
| 3 | TTT APE `<=12%`; 종단 NMAE `<=20%`; 속도 MAPE `<=15%`; **count MAE `<=max(7.5 veh,15%)`; H1 flow gate 유지** |
| 5 | TTT APE `<=15%`; 종단 NMAE `<=20%`; **속도 MAPE `<=15%`; count MAE `<=max(7.5 veh,15%)`; H1 flow gate 유지** |
| 10 | TTT APE `<=18%`; 종단 NMAE `<=35%`; **속도 MAPE `<=20%`; count MAE `<=max(10 veh,20%)`**; nonfinite/음수/clipping/질량 실패 0 |
| 15 | TTT APE `<=20%`; 종단 NMAE `<=35%`; **속도 MAPE `<=20%`; count MAE `<=max(10 veh,20%)`**; nonfinite/음수/clipping/질량 실패 0 |

**지표 정의 (v2.1 J-4 에서 유지 — 분모를 명시하지 않으면 두 사람이 다르게 계산한다).**

```
NMAE       = Σ|pred − obs| / max(Σ obs, 1 veh)
관측 0인 셀 = MAE <= 1 veh
speed MAPE = 차량가중, 분모 max(obs_speed, 5 kph)
TTT APE    = 분모 max(obs_TTT, 1 veh·h)
```

**모든 absolute metric 은 같은 분모의 signed bias 를 함께 게이트한다.**
`|signed_bias|` 가 해당 H 의 absolute metric 한계를 넘으면 실패다. flow signed bias 는 항상 `<=10%`.

**인터페이스 유량 게이트 (별도).** 도시부·램프 경계 유량 WAPE `<=10%`, 유출램프 WAPE `<=15%`.
총량 지표가 접속부 오차를 흡수하지 못하게 한다 — 램프미터 레버 효과가 발생하는 곳이 정확히 거기다.

레버 효과는 `demand × H × 채널` 마다 재료 비교 **16개 이상** (v2.1 은 seed 축을 포함해 24).
`effect_NMAE <= 0.25`, signed bias `<=0.15`, **재료 부호 일치 100%**.

Spearman `>=0.70`, top pairwise `>=0.80` 을 점추정과 **부트스트랩 95% 하한 둘 다** 통과.

**spillback.** `(run_id, anchor, physical_stock_id)` episode 당 positive/negative 각 최대 하나로 센다.
혼잡 `demand × H × 채널 × asset-class` 마다 독립 positive/negative 각 **10개** (v2.1 은 20),
F1 `>=0.80`, 발생/해소 중앙값 오차 `<=60 s`, p90 `<=120 s`.

**면제는 저수요 셀에 한한다.** 저수요 셀의 positive 가 5개 미만이면 spillback 게이트만
`NOT_EVALUATED` 다. **혼잡 셀에서 positive 가 10개 미만이면 `BLOCKED`** 다.
(v3 초판은 "저수요" 한정을 빠뜨려, 탐지를 덜 할수록 게이트를 피하는 역인센티브를 만들었다.)

**검정력 손실을 승인된 위험으로 기록한다.** 20 → 10 축소로, 참 recall 0.60 인 탐지기가
게이트를 통과할 확률이 약 0.245 에서 0.382 로 **1.6배** 오른다. 감사 시정책
(`reports/plant_fidelity_audit.md`)은 각 20개였다. 판정이 임계 근처면 혼잡 셀만 20 으로 되돌린다.

## N10. 감사와 승격 — P1

`audit_plant_fidelity.py` 에 신호·토폴로지·투영·질량·캘리브레이션·짝동역학·순위·런타임 게이트를 추가한다.
출처 게이트(매니페스트 해시 사슬, 아티팩트 변조 탐지)는 **추가하지 않는다.**

승격은 세 demand 의 holdout 시드에서 필수 게이트가 PASS 일 때만 가능하다.
저수요라고 spillback 외 지표를 면제하지 않는다.

**결함 수정 루프**

1. 실패 아티팩트와 최소 재현 테스트를 먼저 고정한다
2. 결함 하나를 수정하고 관련 단위 게이트를 실행한다
3. **단계 경계에서만** 독립 검토를 받는다 (v2.1 은 수정 라운드마다)
4. development 셀만 재실행한다
5. 마지막에 전체 회귀와 whole-branch 검토

동일 load-bearing finding 이 **3회** fix/review 에도 남으면 BLOCKED 로 판정한다 (v2.1 은 5회).

---

# 사전 등록 (런 전에 여기 적는다)

- **임계치** — 위 각 단계의 PASS 조건. 런 후 수정 금지
- **시드** — training `13, 29` / holdout `47`. holdout 은 N6 적합과 N8/N9 임계선택에 쓰지 않는다
- **전진폭 (N8-1 FD 미분 스텝)** — 녹색 6 s, VSL 10 km/h, offset C/8,
  램프미터 max(300 veh/h, 0.20·capacity)
- **레버 진폭 (N9-2 짝지은 검증)** — 녹색 `±10 s`, VSL `±10 km/h`, 램프미터 `±150 veh/h`,
  offset `±10 s`. **위 전진폭과 다른 양이다** — 하나는 기울기 추정용 섭동이고 하나는
  실험 레버의 low/high 다. 이름이 비슷해 혼동하기 쉬워 둘 다 적는다.
- **H 축** — `1/3/5/10/15`. H=1 독립 게이트
- **잡음 바닥** — N5 의 20회 base replay 로 동결. 이후 재추정 금지

봉인·서명·ACL 격리는 하지 않는다. 이 문서의 git 이력이 사전 등록 증거다.

# 의존 순서

```
N0 ─┬─ N1 ─ N2 ─ N3 ─┬──────────────────────────┐
    └─ N4-1 ─ N4-2..5 ─ N4-6(D-core) ───────────┼─ N7 ─ N8 ─ N9 ─ N10
                      └─ N5 ─ N6 ───────────────┘             │
                                                              └─ N4-7 (offset 승격)
```

- N5(개발 데이터)는 N1~N4 가 끝나야 의미 있는 상태를 만든다. N6 은 N5 에 의존한다.
- N7 은 N2/N3/N4 의 플랜트를 요구한다. N8 은 N7 의 endpoint 를 요구하고 `eps_J_endpoint` 를
  자체 측정한다. N9 는 N5 의 `eps_J_vissim` 을 요구한다.
- **N4-6(D-core)은 N7 앞에 온다.** 액추에이션이 검증되지 않은 상태로 production endpoint 를
  통합하면 이후 모든 동적 측정이 오염된다.
- **N4-7(offset 승격)은 마지막이다.** D-core · N9 효과/순위 · N8-4 런타임이 모두 PASS 해야 열린다.
  그전까지 offset writer 는 `intent_only` 로 남는다.

# 이 계획에서 다루지 않는 것

의도적으로 범위 밖이며, 필요해지면 **별도 과제**로 세운다.

- **150초 주기 정규화 실험** — 별도 `.inpx`/SIG/감사를 요구하고, 계획 스스로 그 결과가
  native plant·offset·controller 를 승격하지 못한다고 규정한다. 승격 경로에 기여하지 않는다.
- **증거 출처 관리 일체** — 서두의 표 B 항목 전부. 되살리는 조건은 서두에 적혀 있다.
- **미드블록 offset 슬레이빙** — 설계는 확정됐으나 미구현. N4-7 이 offset 을 열기 전까지 무의미하다.
- **테스트 스위트 timeout** — 인프라 문제이지 플랜트 충실도가 아니다.
- **`.gitignore` 의 `*.err` 제외** — 운영 위생. 별건으로 처리한다.

## `checklist.md` 매핑

기존 `checklist.md` 의 미완료 항목이 v3 어디에 대응하는지 고정한다.

| checklist 항목 | v3 대응 |
|---|---|
| 모니터 26개 항상 녹색 | **N4-4** |
| 실시간 링크 속도 관측 | **이미 해소** — `run_real_world_stackelberg_controller.vbs` 가 `link_speeds_kph` 를 기록한다. checklist 가 낡았다 |
| 인접부 TTT 분해 배선 | **N3-1** |
| `boundary_in` 큐 122.7대의 목적함수 포함 여부 | **N3-2** 에서 결정한다. 물리 trace 는 동일하게 두고 가중치만 다르게 한다 |
| SC1004 역할 오분류 | **N3-3** |
| solve 시간 초과 | **N8-4** |
| H=1 지평 퇴행 | **N9-4** (H=1 독립 게이트) |
| G6 게이트 FAIL / 전면 재채점 | **N9-4** (Spearman·pairwise 부트스트랩 하한) |
| spillback F1 인공물 | **N9-4** (episode 당 1개 · 셀별 표본 요건) |
| G5 셀 게이트가 잡음 바닥 아래 | **N5** — `eps_J_vissim` 을 동결한 뒤 임계를 그 위로 재설정한다. 잡음 바닥 아래 임계는 모델 작업으로 통과할 수 없다 |
| 미드블록 offset 슬레이빙 / 테스트 timeout / `*.err` | 위 **명시적 제외** |
