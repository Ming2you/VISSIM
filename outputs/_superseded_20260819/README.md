# 격리 보관 — 2026-08-19

여기 있는 것은 **쓰지 않는다.** 무엇이 대체했는지 아래에 적어 둔다.
지우지 않고 옮겨만 둔 이유는 되돌릴 수 있게 하기 위해서다.

## 정본

- player 권역 : `outputs/urban_player_territory_v1_20260819.json`  (재유도 금지, 읽어서 쓴다)
- 토폴로지    : `evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json`
- 인접표      : `outputs/intersection_adjacency_core17legs4b_20260819.json`
- 경계 추가leg: `evaluation/real_world_modi_inventory/boundary_extra_legs_legs4b_20260819.csv`
- 경계 회전   : `outputs/pn_boundary_turns_v1_20260819.json`  (생성기 `scripts/derive_pn_boundary_turns.py`)

> 2026-08-19 정정: 위 세 줄이 `core17legs4` / `legs4`(= b 없는 판) 를 가리키고 있었다.
> 그것들은 이 폴더로 격리됐다. 정본은 **legs4b** 다.

## 격리한 것

| 파일 | 왜 |
|---|---|
| `urban_storage_capacity_core17legs4_20260818.json` | 새 인접표로 저류를 재유도해 봤으나 링크배정 아티팩트가 옛 8방위 기준이라 `SC1004_SE_out` 같은 이름을 뱉는다. 쓰면 안 된다. 저류는 아직 `urban_storage_capacity_jam168_20260815.json` 을 쓰고, 새로 생긴 8쌍(16구간)은 기본 220 폴백 상태다 |
| `boundary_extra_legs_dedup_20260818.csv` | 중복 게이트 15쌍만 뺀 중간 산출물. 4방위 변환과 강등 노드 재배치까지 마친 `boundary_extra_legs_legs4_20260818.csv` 가 대체한다 |

## 2026-08-19 2차 격리 — 9개

원래 상대경로를 보존해 옮겼다. 되돌리려면 `outputs/_superseded_20260819/<원래경로>` 에서 제자리로 옮기면 된다.
옮기기 전에 저장소 전체 `git grep` 으로 참조 0건을 확인했다.

| 파일 (원래 경로) | 세대 | 대체 |
|---|---|---|
| `outputs/canonical_topology_up10701_20260814.json` | up10701 | `outputs/canonical_topology_v3.json`, 필요 시 `scripts/build_canonical_topology.py` 로 재생성 |
| `outputs/canonical_topology_up10701_sw020_20260814.json` | up10701 | 〃 |
| `outputs/canonical_topology_up10701_sw050_20260814.json` | up10701 | 〃 |
| `outputs/canonical_topology_up10701_sw080_20260814.json` | up10701 | 〃 |
| `outputs/canonical_topology_up10701_sw100_20260814.json` | up10701 | 〃 |
| `outputs/intersection_adjacency_core17legs4_20260818.json` | core17legs4 | `outputs/intersection_adjacency_core17legs4b_20260819.json` |
| `evaluation/real_world_modi_inventory/boundary_extra_legs_legs4_20260818.csv` | core17legs4 | `…legs4b_20260819.csv` (legs4b 는 legs4 의 순수 상위집합 — `SC103,E` · `SC2001,S` 2행 추가) |
| `evaluation/real_world_modi_inventory/boundary_extra_legs_20260814.csv` | 구세대 | 계보상 `dedup_20260818` → `legs4_20260818` → `legs4b_20260819` |
| `outputs/intersection_adjacency_20260804.json` | 구세대 | `…core17legs4b_20260819.json`. 8방위 이전 포맷이라 현행 소비자가 파싱도 못 한다 |

`.gitignore` 에 `outputs/_superseded_*/**/canonical_topology_*.json` 을 추가했다.
원래 패턴 `outputs/canonical_topology_*.json` 은 `*` 가 슬래시를 넘지 않아,
하위 폴더로 옮기는 순간 24MB × 5 = 116MB 가 추적 대상이 된다.

## 옮기려다 되돌린 것

| 파일 | 왜 남겼나 |
|---|---|
| `outputs/intersection_adjacency8_legfix_20260812.json` | `outputs/preflight_manifest_legfix_20260812.json` 이 이름을 들고 있다. 그 값이 다른 PC 의 절대경로라 이미 해석 불가라는 판정이 있었으나, 참조 문자열이 살아 있어 보수적으로 제자리에 뒀다 |

## 손대지 않은 세대 — 살아 있는 참조가 있다

- **pedovrx / pedfold / jam168 / userfix_20260814e** — `scripts/build_preflight_manifest.py` 의
  `DEFAULT_PATHS` 와 `plant/src/vissim_strict/run_evidence.py` 의 두 표가 이 세대를 못 박고,
  그 표가 곧 `scripts/approve_physical_stock_topology.py` 의 `is_production` 판정이다.
  옮기면 승인이 **통과하되 아무것도 증명하지 않는** 약한 경로로 조용히 떨어진다.
- **어댑터 실행 지문 4개** — `evaluation/controllers/vissim_stackelberg_adapter.py` 가 매 결정
  해시해 `execution_fingerprint_sha256` 에 넣는다. 없어도 예외가 안 나고 지문만 바뀌어서,
  기존 기준선과의 비트 재현 비교가 소리 없이 무의미해진다.
  특히 `outputs/urban_storage_capacity_jam168_20260815.json` 은 차로수 표의 실입력이라
  옮기면 lane-delay 보정이 no-op 이 된다.
- **`core17legs4`(b 없는 판) 의 config·control_mapping·detector_mapping·player_config·생성 vbs**
  — `scripts/run_real_world_single_watchdog_distributed_core17legs4.ps1` 이 살아 있다.
- **정본 러너가 참조하는 옛 이름 3개** — `outputs/link_player_assignment_20260805.json`,
  `outputs/intersection_adjacency8_20260805.json`, `outputs/urban_storage_capacity_20260805.json`.
  `core17legs4b.ps1:191-193` 이 provenance 로 해시한다.
