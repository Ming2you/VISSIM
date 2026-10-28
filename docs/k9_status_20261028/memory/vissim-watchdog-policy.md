---
name: vissim-watchdog-policy
description: "장기 VISSIM 런의 무진행 kill 정책 — 기본은 5분 kill+재실행, 수요 스케일링 망에서는 끈다"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-28T05:39:30.823Z
---

장기 런은 5분(StallSec 300) 무진행이면 kill 하고 재실행한다 (사용자 지시, 2026-07-15).

**예외 (2026-08-28 사용자 지시): 수요를 키운 망에서는 끈다.** "300킬 끄고 돌려줘, 오래 걸려도 괜찮으니까".
fw14_ramp2(고속도로 x1.4) 망에서 attempt 1 이 **첫 결정 전 기동 단계**에 idle 311s 로 killed 됐다.
결정 자체는 중앙 92.7초라 문턱과 무관했다 — VISSIM 이 무거운 망을 여는 시간이 문턱을 넘은 것이다.

**How to apply:** 러너 인자로 넘긴다 — `-StallSec 86400`. 큐 스크립트는 기본적으로 이 인자를
안 넘기므로 러너 기본값 300 이 걸린다. **`-StallSec 0` 은 쓰지 마라** — 러너가
`if ($idle -gt $StallSec)` 로 판정해서 첫 폴링에 즉시 kill 된다. 끄려면 큰 값이다.
kill 을 끄면 재시도의 의미가 EXIT_NO_DONE 뿐이므로 `-MaxAttempts` 도 낮춰도 된다.
준비해 둔 판: `scripts/queue_canon_fdfw14_nostall_20260828.ps1`.

건강한 런을 중간에 죽여서 다시 시작하지는 않는다 — 진행 중인 시도가 문턱 아래로 정상
진행 중이면 그대로 두고, 실패했을 때만 끈 판으로 재발사한다.

관련: [[vissim-parent-run-launch-traps]] (StallSec 300 이 수요 스케일링 중 kill)
