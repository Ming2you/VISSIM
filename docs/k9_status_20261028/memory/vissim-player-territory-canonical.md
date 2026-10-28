---
name: vissim-player-territory-canonical
description: "player 권역 정본 = outputs/urban_player_territory_v1_20260819.json. 재유도 금지, 읽어서 쓴다. 사용자가 전수 검토해 확정"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-19T02:26:21.163Z
---

**player 권역은 재유도하지 않는다. 읽어서 쓴다.**

정본: `C:\Users\TRLAB\Desktop\찐찐막\VISSIM\outputs\urban_player_territory_v1_20260819.json`
(urban player 26 · leg 119 · freeway 2 · 권역 링크 1,025 · `semantic_sha256` 17e3c526…)

2026-08-19 에 사용자가 전수 검토해 확정했다. 그 파일 안에 `regeneration_policy`,
`decision_log`(14건, 근거 포함), `sources`(6개 sha256), `config_todo` 가 다 들어 있다.

**왜 재유도하면 안 되나.** 자동 규칙이 실제 망과 어긋나는 자리가 여럿이다.

- `link 21` — 신호두는 SC108 인데 상류가 없고 하류가 SC109 다. 신호두 소속 ≠ 권역
- `SC1·N_SC11` — 신호군 `SC11_to_SC1 = WBT` 라 실제는 **E**. 인접표가 N 으로 오배정
- `SC11·S_SC1` — `SC1_to_SC11 = EBT` 라 실제는 **W**. S 의 내용은 SC7 것
- 지상/지하차도를 갈라야 한다 — SC107·SC1004·SC1005
- 폴백을 쓰면 SC1 East 링크가 North 에도 들어간다

**2026-08-18 에 이미 한 번 롤백했다** — 금요일에 만들어 둔 배정(`boundary_extra_legs_20260814.csv`,
config `notes` 의 merged-gate 목록)을 못 읽고 재유도해서 "유령 게이트" 라는 잘못된 결론을 냈다.
같은 실수를 반복하지 않으려고 정본을 박았다.

**아직 config 에 반영 안 된 것** (`config_todo`)
- leg 삭제: `SC1·N_SC11`, `SC11·S_SC1`
- leg 신설: `SC103·E`, `SC2001·S`

이 권역 위에서 보호망 경계를 판정한 결과가 [[vissim-pn-boundary-canonical]] 이다.

관련: [[vissim-topology-rebuild-core17]] [[vissim-workstation-state]]
