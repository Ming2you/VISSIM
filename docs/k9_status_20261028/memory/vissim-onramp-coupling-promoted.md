---
name: vissim-onramp-coupling-promoted
description: "on-ramp 결합을 정본 승격(2026-09-03, -483.8). 램프 저수지에 유입 경로가 아예 없었고, 세 조각이 함께여야 이득이 난다"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-09-02T22:20:59.960Z
---

**2026-09-03 승격 (커밋 4258061).** 롤아웃 램프 저수지에 유입 경로가 하나도 없었다 —
`on_ramp_to_movement` 공집합이 `urban_queue_model.py:1134` 의 `or not movements` 가드에
걸려 외생 도착을 통째로 버렸다(37결정 5,393.5 veh). metanet 경로는
`coupling.py:214 update_ramp_queues=False` 로 죽어 있다.
검정: `demand.ramp_arrival` 을 0 으로 두든 3976 vph 로 채우든 궤적이 비트 동일.

**세 조각이 함께여야 한다** (시드 13 · x18 rampbn · 기준선 8822.786):

```
주입만                      8909.0   +86.2 악화
주입 + 관측 커넥터 8개        8432.8  -390.0
주입 + 관측 + beta 비례축소   8339.0  -483.8 (-5.48%)   <- 정본
```

- **주입만으로는 악화한다.** `ramp_link_to_queues` 가 도시 피더 링크 4개(31·68·78·10703)를
  100% 램프 큐로 세어 상한을 넘기고, 유입을 켜면 `uqm:1197` 의 min 절단이 차량을 지운다.
  미터 커넥터 8개만 세면 초과 0/37. 상한이 틀린 게 아니라 관측이 과대였다.
- **beta 는 균등 유도값으로 덮지 마라.** `build_urban_movements` 산출을 그대로 얹으면 형제
  17개가 25~50% 깎인다. 새 movement 만 넣고 기존 실측 beta 를 `(1-램프몫)` 배로 비례축소하면
  상대비가 보존된다(351쌍 깨짐 0). [[vissim-uniform-beta-defect]] 와 같은 함정.

**배선은 스크립트가 아니라 config 데이터다.** 2026-08-17 의
`derive_ramp_coupling_movements.py` 는 현행에서 실행 불가(W_RAMP leg 가 이미 있어 충돌) —
삭제했다. 현행은 `grid_node_legs.{SC1001,SC1004}.W_RAMP.on` 을 채우고 movement 18개를
`urban_movements` 에 얹으면 된다. `on` 은 60개 config 전부에서 한 번도 채워진 적이 없었다.

**CLAUDE.md '하지 말 것 2' 는 철회됐다.** 기각 사유 셋 중 beta 손상만 참이고 원인 진단도
틀렸다. `kind=boundary_in` 6개는 실제로 경계 게이트 in링크에서 출발하므로 옳은 계상이고,
이중계상은 미터 전폐 1구간 실측으로 반박(순증 183.2 대 외생 165.7 = 초과 10.6%).

**아직 안 지운 것**: `sync_onramp_queues_*`(테스트 참조) · metanet `update_ramp_queues`
(다른 컨트롤러 호출) · `boundary_out_ramp_split`(검증값이 이걸 켠 채 나왔다).

**남은 한계**: 제거한 4링크(중앙 143 veh)가 `link_to_movements` 에도 없어 도시 저류로 안 간다.
제대로 된 자리는 `SC1001_W_out`·`SC1004_W_out` 저류이고 매핑 재작성이 필요하다.
