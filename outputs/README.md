# outputs/ 안내

여기에는 성격이 **다른 두 가지**가 섞여 있다. 구분하지 않으면 옛 측정치를 현행으로 오해한다.

## 1. 살아 있는 아티팩트 — 현재 파이프라인이 소비한다

아래 셋은 기록이 아니라 **입력**이다. 생성기와 검증 스크립트가 이 파일들을 읽는다.

| 파일 | 만든 스크립트 | 내용 |
|---|---|---|
| `link_player_assignment_20260805.json` | `assign_links_to_players.py` | 링크 → 플레이어 분할 귀속, `link_upstream`, `freeway_bound_links`, 출구 목록 |
| `urban_storage_capacity_20260805.json` | `derive_urban_storage_capacity.py` + `derive_ramp_queue_capacity.py` | 저류 용량·길이, jam density, `ramp_queue_max_veh_by_ramp` |
| `intersection_adjacency8_20260805.json` | `derive_intersection_adjacency.py` | 8방위 인접(복합 키), `internal_link_members` |

**네트워크(`.inpx`)를 고치면 이 셋을 다시 만들어야 한다.** 순서는 `README.md` 의
"아티팩트 생성 파이프라인" 참조. 날짜 스탬프가 다른 구버전(`*_20260804.json` 등)은 이력이다.

`real_world_distributed_urban_followers_*.md` 는 생성기가 슬러그마다 남기는 산출 리포트다.
현행 슬러그는 **`core15n41`**(41노드) 이고, 그 이전(`core15rc`/`core15net`/`core15cap`/
`core15axis`/`core15full`)은 같은 날 단계별 스냅샷이다.

## 2. 측정 기록 — 그때의 값이고 고치지 않는다

나머지 `.md` 와 `gates_*/` 디렉터리는 **측정 시점의 기록**이다.
지금 값과 다르더라도 수정하지 않는다 — 고치면 "언제 무엇을 알고 무엇을 몰랐는가" 가 사라진다.
실제로 이 프로젝트에서는 판단이 여러 번 뒤집혔고, 그 궤적 자체가 근거다.

**따라서 여기 있는 수치를 현행으로 인용하면 안 된다.** 현행 수치는 `README.md` 와
`PLANT_FIDELITY_AUDIT_REQUEST.md` 4장에 있다.

대략의 시기 구분.

| 시기 | 플랜트 | 대표 파일 |
|---|---|---|
| 2026-07-15 ~ 07-18 | 8-seg 가상격자 (A–F 6교차로) | `guarded_*_ladder_*`, `prediction_response_*`, `pstack_nonimprovement_audit_20260718.md` |
| 2026-07-24 ~ 08-03 | 개포동 실도로망 도입, FD/MFD·네트워크 수리 | `real_world_congestion_*`, `network_repair_20260803.md`, `metanet_calibration_20260802.md` |
| 2026-08-04 | 램프 축 복구, 리더 목적함수 환원 | `leader_objective_reduction_20260804.md`, `ramp_marginal_price_20260804.md`, `gates_v6_*` |
| 2026-08-05 | 도시부 토폴로지·관측 배선·플랜트 충실도 | `gates_v7_*`, 위 1번의 JSON 3종 |

`gates_*/` 는 G5/G6 채점 산출(`g6_report.json`, `g6_records.jsonl` 등)이다.
**2026-08-05 의 어댑터 투영·`NS_AXIS`·램프 큐 변경과 플랜트 SC 추가 이후로는 전부
재채점이 필요하다** — 과거 점수와 직접 비교할 수 없다.

## 3. 여기 없는 것

`.gitignore` 가 `evaluation/runs/` 를 제외한다. 즉 **런 원본(state/action JSON, 로그)은
저장소에 없다.** 포착률 같은 수치를 재현하려면 런을 직접 돌려야 하고 PTV Vissim 라이선스가
필요하다.
