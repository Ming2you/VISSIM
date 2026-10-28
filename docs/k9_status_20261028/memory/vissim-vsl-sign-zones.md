---
name: vissim-vsl-sign-zones
description: VSL 은 방향당 표지판 8개(셀 0·2·5·7·10·13·15·18)에만 써진다 - 셀 단위 자유도는 플랜트가 실현 못 한다 (2026-09-08)
metadata: 
  node_type: memory
  type: project
  originSessionId: 363c7808-e973-4c3e-92d8-2d00dcc50f83
  modified: 2026-09-08T05:52:14.041Z
---

**물리 사실.** 이 망의 VSL 은 방향당 **표지판 8개**이고 자리가 고정이다 — 21셀 격자에서
셀 **0·2·5·7·10·13·15·18**, 간격 ~1,347 m. 근거 둘이 일치한다:
`control_mapping_ver2n21.json` 의 `segments[].dsds`(DSD 보유 세그먼트 16 = 8 x 2방향)와
VBS 의 `RW_EXPECTED_VSL_ACTION_KEYS` 66행(= `RW_EXPECTED_VSL_ACTION_ROWS`).
플랜트 쓰기는 어댑터의 action CSV writer 가 세그먼트마다 `segment_vsl(control, link, i, cfg)` 를
불러 그 8자리에만 쓴다. **표지판 없는 셀에 건 값은 아무 데도 안 써진다.**

**커밋 행동은 세그먼트 키를 싣는다** (2026-09-08 실측, canon_ver2n21_dlit): vsl 키 44개
= 링크 2 + 세그먼트 42. 그러니 배관은 원래 있었다. (N=8 의 b4 런 action 이 링크 키 2개뿐인
것을 보고 "VSL 은 링크 스칼라" 라고 판단했는데 **틀렸다** — 그건 폴백/다른 구성이었다.
행동 JSON 하나로 구조를 단정하지 마라.)

**진짜 결함은 자유도가 물리와 안 맞은 것.** 팔로워의 자유 셀 규칙은 표지판이 아니라
`upstream_control_idx` = **첫 off-ramp 상류**였다 — FW_E 는 표지판 8개 중 4개, FW_W 는 3개만
움직이고 나머지는 vsl_max 영구 고정. 반대로 표지판 없는 셀에는 자유도를 줬다.

**수선 (2026-09-08 사용자 결정).** 표지판 2개 간격으로 **구역 4개**를 두고 셀은 자기 구역
머리 값을 물려받는다. 머리 = 셀 0/5/10/15 (전부 실제 표지판), 구역 길이 2.57~3.08 km.

    구역 0 [0-4]   상류 접근       가변
    구역 1 [5-9]   첫 IC 포함       가변   (FW_E 램프 S8·S9 / FW_W S6·S7)
    구역 2 [10-14] 둘째 IC 포함     가변   (FW_E S13·S14 / FW_W S11~S13)
    구역 3 [15-20] 하류 회복        vsl_max 고정

한 자리만 고치면 셋이 같이 맞는다 — 롤아웃·가격 코너·플랜트 쓰기가 **전부 `segment_vsl` 을
거친다**. `install_freeway_vsl_zones` (scripts/apply_vsl_zone_patch_20260908.py) 가 그 함수를
구역 인식으로 바꾸고, config 키 `freeway.vsl_zone_heads` / `vsl_zone_free` 로 켠다. 키가 없으면
비트 동일. 가격 워커(spawn)에도 다시 심어야 한다.

**후보 생성기는 `cfg.network.freeway_vsl_zone_*` 를 읽는다** — k-best 판(같은 날 도입,
[[vissim-n21-vsl-product-oom]])이 구역 머리만 훑고 나머지 셀에 머리 값을 편다. 구역이 없으면
종전 규칙으로 떨어져 비트 동일.

**5 km 를 한 값으로 거는 건 피해라.** 구역 0+1 을 합치면 5.13 km 가 되는데 사용자가 그 이유로
기각했다. 표지판 2개 간격(~2.57 km)이 상한선이다.

관련: [[vissim-n21-vsl-product-oom]], [[vissim-supersede-dont-flag]]
