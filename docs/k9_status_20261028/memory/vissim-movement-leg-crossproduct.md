---
name: vissim-movement-leg-crossproduct
description: urban_movements 474 = 권역 leg 121의 교차곱 L×(L-1). SC1은 4갈래인데 56개. 커넥터로 재유도하면 12개. 병합 규칙 A/B와 link_to_movements 함정. 2026-08-24
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T03:16:56.970Z
---

2026-08-24 규명. CLAUDE.md 가 "leg 교차곱이라 물리 회전보다 많다"고만 적어 둔 것의
정확한 구조와 해법.

## 항등식

**26개 신호 전부에서 `movement 수 == L × (L−1)`** 이 성립한다(L = 권역 leg 수).
권역 leg 121 → `urban_movements` 474. 한 자리도 안 틀린다.

## 왜 leg 가 많은가 — 같은 방위가 두 번 세어진다

    SC1 leg 8개: E, E_SC11, N, N_SC101, S, S_SC107, W, W_SC105
      E vs E_SC11    링크 27 / 27·27  → **완전히 같은 집합**
      N vs N_SC101   링크  1 / 1·25   → 경계판이 내부판의 부분집합
      S vs S_SC107   링크  1 / 1·17
      W vs W_SC105   링크  1 / 1·19

경계판의 그 1개 링크는 `boundary_extra_legs` 가 "상류 종단에 vehicleInput 있음"으로
적어 둔 **수요 주입점**이지 새 접근로가 아니다. 그래서 4갈래가 8×7 = 56 이 됐다.
실제 물리 회전은 4×3 = **12**.

부산물: u_turn 44개 중 **40개가 같은 방위 쌍둥이 사이**(`SC1_E_to_E_SC11` = 자기참조).
같은 물리 회전이 둘로 쪼개진 쌍이 **70쌍**이고 **70쌍 전부 현시가 같다**.
같은 정지선을 공유하는 movement 가 각자 용량을 갖는다 — SC1 동쪽 14개의 모델 용량
합이 16,226 veh/h 인데 그 접근로는 3차로 하나(실효 620)다.

## 정지선 커넥터로 다시 유도한다

```bash
python scripts/derive_connector_movements.py
```

movement 는 "정지선에서 **어느 커넥터를 타는가**"여야 한다 — 그게 신호가 통제하는
단위고, 그 뒤 목적지 분기는 `beta` 몫이다.

1. `.inpx` `signalHead`(`lane="<link> <lane>"`, `sg="<controller> <group>"`)로 정지선을
   정한다. **SG 1–8 만** 본다(9 이상은 미드블록).
2. 정지선 링크에서 나가는 커넥터 = 물리 회전. 접근로당 **79개가 정확히 3개**다.
3. 커넥터 `to_link` 를 권역으로 접어 목적을 얻는다.

SC1 검산: 접근로 4개 × 커넥터 3개 = 12, 정지선이 각각
`1220008201`·`1210008401`·`1220006903`·`1220007104` 로 하나씩이다.

## leg 병합 규칙 둘

- **A(포함)**: 링크 집합이 같거나 부분집합이면 한 접근로다. 17 leg 흡수.
- **B(합류)**: 유출 커넥터가 **전부 같은 한 leg 로만** 향하면 그 leg 로 합류하는
  상류다. 2 leg 추가. `SC5·S` 가 여기 걸린다 — 링크 256("Dummy Link 12") 하나이고
  `S_SC11` 과 교집합 0 인데, 유출 커넥터 `10415` 가 본선 정지선 `1220014100` 으로만
  간다. 256 의 신호두는 **SG24(미드블록)** 이고 본선은 SG3·SG8 이다.

**규칙 B 가 지상/지하 분기를 안 건드리는 게 핵심이다.** SC107 `W_SC1004`/`W_SC1005`,
SC1004 `E_SC1005`/`E_SC107` 은 유출이 한 곳으로 안 모여 걸리지 않는다(CLAUDE.md 가
갈라 두라고 한 곳). **예외 목록을 손으로 관리할 필요가 없다.**

## 설치 — 출구 쌍둥이만 합친다

진입 쌍둥이(`SC1_E_*` 게이트 유입 / `SC1_E_SC11_*` SC11 유입)는 **합치면 안 된다**.
`approach_routing` 이 movement 당 origin 하나를 전제하므로 게이트 유입 경로가 끊긴다.
그쪽 이중계상은 용량을 접근로 단위로 묶어 다뤄야 한다.

출구만 병합: 474 → **368**(삭제 36, 전부 u_turn) · 통제 17신호 364 → 263 · SC1 56 → 24.
안전 검증 실측 전부 0 — 병합 그룹 안에서 `origin` 갈림 0 · `phase` 갈림 0.

## 함정 둘 (둘 다 실제로 밟았다)

**`link_to_movements` 는 문자열 리스트가 아니라 dict 리스트다.**

    "17": [{"movement": "...", "weight": 0.25, "source": ..., "approach": ...}, ...]

`str(entry)` 를 키로 쓰면 등장 이름 501개 중 **0개**가 맞아 링크 204개가 전부 빈
리스트가 되고 **큐 주입이 통째로 0** 이 된다(`movement_queue_assigned_veh`
1291.7 → 0.00, `storage_assigned_veh` 917 → 1982). **weight 도 합산**해야 한다 —
두 항목이 같은 대상으로 접히면 더해야 링크 총량이 보존된다.

**이름 규약은 자기 기준 출구 방위 + 하류 신호**(`SC1_..._to_N_SC101`). 커넥터의
`dest` 는 하류 권역 leg 이름이라 뒤집혀 있고(`SC101_S_SC1`), 좌표 방위 계산도
커넥터가 교차로 내부라 실패한다. **하류 신호로 기존 movement 를 찾아 이름을 재사용**해라.

movement 이름을 쓰는 곳은 셋뿐이다 — `urban_movements`,
`detector_mapping["link_to_movements"]`, `agents[*]["visible_movements"]`.
`on_ramp_to_movement`/`off_ramp_to_movement` 는 빈 dict 다.

관련: [[vissim-uniform-beta-defect]] [[vissim-player-territory-canonical]]
[[vissim-measured-capacity-online]] [[vissim-pn-boundary-canonical]]
