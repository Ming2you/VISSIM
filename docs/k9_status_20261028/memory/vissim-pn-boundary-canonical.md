---
name: vissim-pn-boundary-canonical
description: "보호망 경계 판정 정본 — leg 구역 3종 + 전이표 + 정지선 커넥터. 생성기 scripts/derive_pn_boundary_turns.py, 산출 outputs/pn_boundary_turns_v1_20260819.json. 규칙 되돌리지 말 것"
metadata:
  node_type: memory
  type: project
---

**보호망 유입·유출·외부통과는 이 규칙으로만 판정한다. 재유도 말고 생성기를 돌려라.**

```
python scripts/derive_pn_boundary_turns.py            # outputs/pn_boundary_turns_v1_20260819.json
python scripts/build_pn_boundary_map.py               # outputs/pn_boundary_map_20260819.html
```

**절차** — leg 에 구역(내부/경계면/외부)을 매기고 전이표로 판정한 뒤, leg 의 **정지선 링크**
(그 SC 의 signal head 가 걸린 최하류 링크)에서 나가는 커넥터로 실체화한다.
`(from_link, connector, to_link)` 가 VISSIM 런타임 주소다.

```
내부->내부 internal · 내부->외부 outflow · 경계면->내부 inflow
경계면->외부 external · 외부->내부 inflow · 외부->외부 outside_pn
```
진출 leg 는 "그 leg 로 나가면 어디로 가느냐" 로 읽는다 — 경계면 leg 로 나가면 곧 외부다.

**게이트맵** — `urban_input_gate_map_legs4b_20260819.csv` (생성기 `build_urban_input_gate_map_legs4b.py`).
런 발사 시 `-UrbanInputGateMap` 으로 **반드시 넘겨라**. 안 넘기면 VBS 가 옛 맵을 열고
어댑터가 `in_SC9001_S` 를 모른다며 ValueError 로 선다(조용한 오염 아님, 하드 크래시).
link 69 는 공용 줄기라 `shared_stem_unmapped`. mapped 21.

**SC1004 서측** — 69 무소유. W = 71·10640·10634·10635·10642 / W_RAMP = 70·10637·10641·10700·10638·10643
/ SC1005·W = 75·10701·10636 / on-ramp 10644·10639 는 freeway.

**수치 (2026-08-19)**
- leg 구역 내부 67 · 경계면 18 · 외부 36
- 회전 306 (통제 17 SC 안 204) · internal 123 · inflow 35 · outflow 34 · external 10 · outside_pn 104
- **통제 가능 경계 74** (유입 32 · 유출 34 · 외부통과 8)
- **상수 부하 3,920 veh/h** = 통제 불가 유입 1,529 (10595 구룡터널 1336 · 10636 지하차도 193)
  + 내부 주입 11곳 2,391 (10곳이 `Dummy link` 계열 2,226)
- 완전 내부 player 6: SC1 · SC7 · SC11 · SC105 · SC1003 · SC1005

**되돌리면 안 되는 규칙 다섯** (전부 사용자 확인)
1. **경계면 우선** — 한 링크를 경계면 leg 와 내부 leg 가 같이 물면 경계면이 이긴다.
   내부로 흡수되면 그 자리 유입·유출이 사라진다 (SC107·S 의 378·379 사례)
2. **도착 구역은 하류로 걷는다** — 교차로 직후 진출 카리지웨이 25곳이 무소유다.
   그대로 두면 통제 SC 사이인데도 유출로 찍힌다
3. **양끝이 버퍼면 횡단 아님** — 정지선 앞 회랑 안 이동. 세면 이중계상
   (379→378 은 SC107 정지선 382 앞, 실제 횡단은 10618). 제외 5개: 10229·10604·10605·10637·10640
4. **relFlow 는 비면 1** (0 아님). 0 으로 읽으면 지하차도 경로가 통째로 사라진다.
   결정부 130개 중 68개가 빈 relFlow
5. **`FORCE_PERI = {("SC1","S")}`** — 1220042300 구룡터널_NB 1336 veh/h 주입점.
   나머지 내부 주입점 14곳은 사용자 지시로 경계면으로 올리지 **않고** 상수 부하로만 기록

**config 의 urban_movements 474개는 쓰지 마라.** leg 교차곱 선언이라 물리 회전보다 많다
(SC1 은 4갈래인데 56개 선언, 실제 17). 통제 17 SC 합계 선언 364 대 회전 201.

**망 정본이 둘로 갈려 있다 (미해결).** 정본 러너
`scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1:84` 는
`modi_eval_rw_control.inpx` 를, 권역 정본의 `sources` 는 `modi_eval_userfix_20260814d.inpx` 를
가리킨다. 단순 치환 금지 — 별도 판정 필요. **다만 경계 판정은 두 망에서 완전히 같다**
(회전 303개의 from/conn/to/class/ctrl/flow 전부 일치, 2026-08-19 확인). 차이는 커넥터
`10613` 1개와 신호두 배치 3링크(`29`·`10696`·`57`)뿐이고 판정에 안 닿는다.

**2026-08-19 아카이브 정리.** `_archive/`(bucket 7개, 원래 경로 보존) 로 236개 122MB 이동.
707개 파일 분류 → 후보 343 → 전수 grep 으로 참조 0건인 236개만. `_archive/manifest.csv` 에 복원 경로.
`.gitignore` 에 `_archive/**/canonical_topology_*.json` 필요(`*` 가 슬래시를 안 넘는다).
`tests/test_action_csv_contract.py` 실패는 **이동 전부터** 있던 것(HEAD 워크트리 7실패로 확인).

**2026-08-19 정리 완료.** `VISSIM/CLAUDE.md` 를 새로 만들어 정본·규칙·롤백 위험 지점을 박았다.
옛 세대 9개를 `outputs/_superseded_20260819/` 로 격리(원래 상대경로 보존, git grep 참조 0건 확인).
`.gitignore` 에 `outputs/_superseded_*/**/canonical_topology_*.json` 추가 — 원 패턴은 `*` 가
슬래시를 안 넘어 하위 폴더로 옮기면 116MB 가 추적된다.
**pedovrx/pedfold/jam168/userfix_e 는 살아 있다** — 승인 사슬의 `is_production` 판정과
어댑터 `execution_fingerprint_sha256` 이 경로 문자열을 물고 있어 옮기면 조용히 깨진다.

관련: [[vissim-player-territory-canonical]] [[vissim-topology-rebuild-core17]]
