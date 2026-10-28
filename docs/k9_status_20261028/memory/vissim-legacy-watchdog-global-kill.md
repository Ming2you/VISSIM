---
name: vissim-legacy-watchdog-global-kill
description: 옛 워치독 PS1 의 Kill-Vissim 은 이름으로 모든 VISSIM·cscript 를 죽인다 — 테스트 한 번이 동시 런 3개를 날렸다 (2026-09-24)
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-23T18:17:58.278Z
---

`scripts/run_real_world_single_watchdog*.ps1` 의 `Kill-Vissim` 은
`Get-Process -Name VISSIM200,VISSIM200CL,cscript | Stop-Process -Force` 다. PID 소유 확인 없이 **PC 전체**를 죽인다.
- core17legs4b 에는 `-NoGlobalKill` 스위치가 있다 (:676). core15n41 등 옛 판에는 없다.
- `scripts/tests/test_b1a_watchdog_attempt_launch.py` 가 core15n41 워치독을 실제로 띄운다.
- 2026-09-24 03:15:32, SDMPC-31 구현 에이전트가 기존 테스트 묶음을 돌렸다. 그때 stage-1 v2 제어 런 3개가 동시에 죽었다.
  - s37_v2both 는 7340 s, s41_v2rm 는 5750 s 까지 가 있었다. 산출물은 `run_killed_0315` 로 옮겼다.

**Why:** 이 PC 는 VISSIM 을 4개까지 동시에 돌린다 ([[vissim-single-instance-license]]). 전역 kill 은 다른 런을 조용히 끝낸다. 런 로그에는 `completed=False error=` 만 남아서 원인이 안 보인다.

**How to apply:**
- VISSIM 런이 도는 동안 에이전트에게 기존 테스트 묶음을 통째로 돌리게 하지 마라. 워치독·PS1·cscript 를 띄우는 테스트는 이름을 박아서 금지해라.
- 새 발사기는 소유 PID 만 죽이게 해라. 옛 워치독을 쓰면 `-NoGlobalKill` 을 넘겨라.
- 여러 런이 한꺼번에 같은 초에 끝나면 먼저 이걸 의심해라.
