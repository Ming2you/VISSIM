---
name: vissim-ver2-mapping-signals-defect
description: ver2 계열 제어 매핑의 signals 가 인터페이스 1개뿐이라 제어런이 조용히 무제어가 된다 (2026-09-08)
metadata: 
  node_type: memory
  type: project
  originSessionId: 363c7808-e973-4c3e-92d8-2d00dcc50f83
  modified: 2026-09-08T08:13:47.267Z
---

**증상이 조용하다.** 21셀 제어런이 시뮬을 완주하고 결정 JSON 도 전부 `status=ok` 인데
**플랜트에는 아무 행동도 안 갔다**. 런로그 마지막 줄에만 보인다:

    ERROR=RUN_INTEGRITY_FAILURE decisions_failed=31   (= wu-link 결정 전부)

원인 사슬. `generate_real_world_control_mapping.py:908` 은
`"signals": [dict(row) for row in REAL_WORLD_INTERFACE_SIGNALS]` 로 **인터페이스 컨트롤러만**
싣는다 — 이 망에서는 SC1001 하나, 그것도 `id: "D"` 다. 그런데 런타임
`vissim_stackelberg_adapter._signal_rows_for_mapping` 은 그 절을 **전체 신호 목록**으로 읽고
`{id}_{phase}` 로 `control.green_times` 를 조회한다. id 가 "D" 라 전부 빗나가면 p1/p2 는
진단 기본값(40 s), p3/p4 는 0 이 되고 `signal_group_action_rows` 가 죽는다:

    SignalGroupPlanError: sc 1001: action commands green on phases ('p1','p2')
                          but the actuation plan has signal groups on ('p1','p2','p3','p4')

action JSON 은 예외 **전에** 써지므로 `ok` 로 남는다. 그래서 JSON 만 보면 정상으로 보인다.

**왜 이제야 났나.** ver2 계열 매핑(`control_mapping_ver2.json` 8셀 · `control_mapping_ver2n21.json`
21셀)은 FD 스윕용으로 만들어져 **무제어 런에만** 쓰였다. 제어런에 처음 쓴 것이 2026-09-08 사다리다.
**8셀 ver2 매핑도 같은 상태다 — 아직 안 고쳤다.**

**수선**: `scripts/fix_ver2n21_mapping_signals_20260908.py`. 통제 17개를 CLAUDE.md 지정 정본
`control_mapping_distributed_core17legs4b_20260819.json` 에서 가져오고, SC1001 의
`major_maps_to=p1` 과 인터페이스 주석(coverage·phase_map·interface_head_count·note)을 보존하며,
러너 VBS 의 `RW_SIGNAL_SCS` 와 sc_no 집합을 대조한다(다르면 안 쓴다). **매핑을 재생성하면 다시 돌려라** —
생성기는 안 고쳤다(`REAL_WORLD_INTERFACE_SIGNALS` 가 `RW_SIGNAL_SCS` 생성에도 쓰여 의미를 바꾸면
VBS 상수까지 흔들린다).

**교훈**: 제어런을 "완주했다"로 판정하지 마라. `DECISIONS_OK` / `DECISIONS_FAILED` 요약행과
`RUN_INTEGRITY_FAILURE` 를 봐라. 결정 JSON 의 `status` 는 CSV 쓰기 전 값이라 무죄추정이 안 된다.
새 매핑으로 제어런을 처음 돌릴 때는 **첫 결정에서** `CONTROLLER_DECISION ... result=exit=0` 을 확인해라.

관련: [[vissim-vsl-sign-zones]] (같은 런에서 함께 드러난 VSL 배관 문제), [[vissim-n21-vsl-product-oom]]
