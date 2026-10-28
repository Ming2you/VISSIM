---
name: vissim-topology-rebuild-core17
description: "2026-08-18~19 토폴로지 전면 재생성(core17legs4b). 권역·경계 판정 모두 확정됨. 남은 것은 저류용량·녹색없는SG·승인사슬"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-18T14:43:18.717Z
---

2026-08-18 `C:\Users\TRLAB\Desktop\찐찐막\VISSIM`. 하루치 작업이 통째로 새 토폴로지 판을 만들었다.

**만든 것** (전부 새 파일, 원본 미변경)
- `evaluation/configs/real_world_modi_pstack_distributed_core17legs4_20260818.json`
- `outputs/intersection_adjacency_core17legs4_20260818.json`
- `evaluation/real_world_modi_inventory/boundary_extra_legs_legs4_20260818.csv`
- 생성기 `scripts/generate_real_world_distributed_players.py` 에 옵션 4개 추가:
  `--boundary-drop-nodes` · `--ramp-leg-dir` · `--ramp-on-to-freeway` · 정렬표 4방위 접기

**확정된 사실**
- leg 방위 **NE↔E · NW↔N · SW↔W · SE↔S** — 신호군(NBT/SBT/EBT/WBT) 진행방향과 52/52 일치, 불일치 0
- 신호군 번호는 8개 블록으로 반복(1–8 / 9–16 또는 11–18 / 17–24)이고 **블록 = 별개 물리 교차로**
  (SC2·4·5·102 는 3개, SC3·7·9·13·9001 은 2개. 중심 간 53~284 m)
- 게이트 50개 중 **15쌍이 중복** — 같은 VISSIM 링크가 정렬표(유입 이름 접미사)와 추가 leg(기하)에서
  다른 이름을 받았다. 정방위 쪽으로 통일 → 게이트 37 → 최종 37
- 러너는 모든 SG 에 `ContrByCOM=True` 를 걸어 **inpx 프로그램을 통째로 우회**한다
  (`evaluation/controllers/plant_cycle.py:34`). 그래서 `.sig` 의 주기·녹색은 제어 런에서 재생되지 않는다
- on-ramp 는 freeway 권역 — `--ramp-on-to-freeway` 로 urban 램프 leg 에서 `on` 을 뺐다(off-ramp 만 남음)
- 최종: 노드 26(통제 17 + 관측 9), movement 462, **가능한 회전 462 = 선언 462 (비율 1.00)**
- PN=통제17 기준 분류: internal 114 / inflow 95 / outflow 95 / external 42 / outside_pn 98 / off-ramp 18

**1번은 끝났다 (2026-08-19)** — player 권역은 [[vissim-player-territory-canonical]] 로,
보호망 경계 판정은 [[vissim-pn-boundary-canonical]] 로 확정됐다. 둘 다 재유도 금지.

**2026-08-19 에 1~4 다 끝났다.**

1. **액추에이션 계획 재유도 완료** — 15 SC -> **17 SC**(SC7·SC16 추가). 체인은
   `derive_signal_group_timing` -> `derive_movement_signal_group_map` -> `derive_signal_group_actuation_plan`.
   망은 **`modi_eval_userfix_20260814e.inpx`**(실제 런이 쓰는 것)를 써야 한다 — `rw_control.inpx` 는
   `.sig` 배정이 달라(평 .sig, 주기 120~170) v3 와 어긋난다. userfix_e 로 하면 공통 15 SC 가
   v3 와 **완전 일치**하고 SC7·SC16 만 늘어난다. `_sgplan.vbs` 형제 7개를 `--from-plan` 으로 다시 뽑았다.
   테스트: `tests/` 는 9개 고치고 0개 만들었다(HEAD 10실패 -> 8). `scripts/tests/` 는
   **HEAD 78 -> 69, 12개 고치고 3개 만들었는데 그 3개는 내 것이 아니다**
   (`test_boundary_gate_alignment` — 커밋 안 된 4방위 생성기 변경 탓. 입력이 생성기와
   alignment JSON 둘뿐이고 후자는 안 건드렸다).

   **함정 둘.** (a) `link_to_origins` 가 얇으면 movement map 재유도가 SC1003 을 망친다.
   **2026-08-19 에 권역 정본 기반으로 전면교체해 해결했다**(`build_link_to_origins_territory.py`).
   링크 279->1,011, config origin 이름 인식 80->119, 해석 149->254, `origin_link_head` 0->228,
   관측이 닿는 origin 중 모델이 모르는 것 44->0, **전 SC 같은 현시 금지쌍 2->0**.
   중간에 "옛 map 을 보존하는 병합" 을 했다가 되돌렸다 — 알고 보니 **옛 배정이 결함**이었다
   (SC1003 p2=[3,4,7] 에 금지쌍 (3,4)·(4,7) 동거). 전수 수집으로는 안 풀린다, 소유 선언 문제다.
   (b) 15->17 상수가 여러 검사에 박혀 있었다. 갱신 근거는 "공유 15 SC 의 계획 노드가
   바이트 동일" 이다 — 기존 원소 불변, 집합만 커짐. 갱신한 것:
   `SIGNAL_SCS`(하네스, 이제 계획에서 유도) · `signal_rows`/`sg_rows`(계획 counts 유도) ·
   `forbidden_pair_total`(유도) · `name_rule_pair_total` 227->282 ·
   `cogreen_forbidden_pairs` 106->110 · `scored_signal_groups` 116->128 ·
   `worst_green_ratio` 6.05->7.54. **`test_derive_signal_group_actuation_plan` 의
   `controllers == 15` 는 건드리지 마라** — 그 검사는 core15n41 매핑으로 표를 만든다.
2. **"녹색 없는 SG 살리기" 는 할 일이 없다** — 죽은 현시 5개(SC7·p3, SC16·p4, SC107·p1,
   SC108·p2, SC109·p1) **전부 신호두 미배정**이다. 사용자 규칙이 "신호두가 있는데 all-red 인
   경우만 살린다" 였으므로 대상 0건. 이걸 다시 파지 마라.
3. **저류 용량 완료** — 누락 16구간(8쌍) 채움. config 144 -> **160키, 누락 0**.
   생성기 `scripts/derive_urban_storage_core17legs4b.py` (권역 정본을 구간 정의로 씀 —
   `internal_link_members` 는 링크를 덜 모아 `SC5_to_SC101` 이 0.08km 로 나온다. 실제 0.69km).
   기존 64개 값은 안 건드렸다(jam168 이 link_split 지분을 써서 더 정교, 내 계산과 중앙값 1.10 차).
4. **러너 인자 정리 완료** — `-UrbanInputGateMap` 기본값을 legs4b 대장으로 박고,
   provenance 3개를 2026-08-05 세대에서 core17legs4b 세대로 옮겼다(+경계 회전 추가).

**남은 것 — 다음 세션 시작점**
1. **승인 사슬 — 앵커 등재 하나 남았다.** `distributed_coordinator.py` 는 커밋했고(`e407adf`)
   `tracked_source_clean` 은 통과했다. 남은 것은 `anchor_python_blobs` — 앵커
   `vendor/NumSim-mine/UPSTREAM_TREE.json` 이 **상류** blob 을 적으므로 로컬 커밋으로는 안 맞는다.
   설계된 경로는 `local_patches` 등재(이미 `stackelberg_mpc.py` 선례 있음).
   `upstream_blob e5d7824e… / patched_blob d29b1b02…` 를 넣고 **동시에**
   `scripts/verify_runtime_source.py:24` 의 `EXPECTED_ANCHOR_SEMANTIC_SHA256` 을 갱신해야 한다(두 열쇠).
   `vendor/` 쓰기 차단이라 사용자 허용이 필요하다.

   **테스트 최종**: `tests/` HEAD 10->8, `scripts/tests/` HEAD 78->66. **내가 만든 실패 0건.**
   4방위 검사 3개는 기대값만 바꾸지 말 것 — `SE` 를 그냥 `S` 로 갈면 이름-규칙 검사가 공허해진다
   (접힌 뒤에도 답이 다른 `NE` 를 써야 한다). 램프 게이트 검사는 `S_RAMP` 복합키로 실패 모드가
   사라져 "램프 leg 가 게이트와 나란히 살아남는가" 로 다시 썼다.
2. 컨트롤러 스모크 런 (승인 사슬 뒤)
3. 회전 0개인 leg 3개 — `SC1004·E_SC107` · `SC107·W_SC1004` · `SC108·W`
4. 인접표에 아예 없는 12구간(SC1001↔1002/1003, SC2002·2004·2005 지하 회랑).
   detector mapping 이 얇은 것(링크 279 vs pedovrx 1194)과 같은 뿌리다

**(라) 는 죽었다** — `rampbase_iv150h3rf_20260818` 이 19:43 이후 무진행, 프로세스 없음. 사용자가 폐기 승인.

관련: [[vissim-workstation-state]] [[vissim-connector-delete-breaks-routes]] [[vissim-parent-run-launch-traps]]
