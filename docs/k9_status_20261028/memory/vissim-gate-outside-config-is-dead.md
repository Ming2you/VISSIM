---
name: vissim-gate-outside-config-is-dead
description: 게이트가 config 밖(필드 없는 getattr · env 전용)에 있으면 그 기능은 실행되지 않는다 — 2026-09-04 하루에 다섯 건 적발
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-09-04T01:50:31.484Z
---

**진단도 구현도 다 되어 있는데 게이트가 config 밖에 있어서 한 번도 안 돈 기능이 다섯 개였다**
(2026-09-04 전수 조사).

```
follower_terminal_cost_enabled     dataclass 필드 없음 → getattr(...,False) 영구 False
meter_queue_constraint_enabled     동상. ALINEA 큐 오버라이드가 통째로 사문
                                   (docstring 이 "기본 OFF"라 적어놓고 켤 방법이 없었다)
distributed_rollout_far_enabled    반대 방향 — parameters.json 전역 기본으로 조용히 승격,
                                   config 27개 중 아무도 안 켰는데 25런이 달고 돌았다
RW_RESTORE_RELEASE_BUFFERS         env 전용. 기록 남은 39런 전부 off
RW_QUEUE_WINDOW                    env 전용. 어느 런에서도 켜진 적 없음 (순시 r 0.674 → 창평균 0.967)
```

**규칙 셋.**

1. **게이트는 config 키 하나.** `getattr(cfg.x, "flag", False)` 를 쓰려면 그 필드가 dataclass 에
   **반드시** 있어야 한다. 없으면 영구 False 이고 grep 으로도 안 잡힌다.
2. **생산자와 소비자를 갈라놓지 마라.** VBS env 로 데이터를 만들고 어댑터 config 로 소비하면,
   config 만 켰을 때 조용히 폴백해 "켰는데 안 돌았다"가 된다. 2026-09-04 에 `RW_QUEUE_BINS` 를
   없애고 러너가 항상 내도록 바꾼 이유다.
3. **"켰다"와 "돌았다"를 디스크가 말하게 하라.** 결정 JSON 은 `local_summary` 중
   `projection_diagnostics` 하위 dict **만** 나른다(adapter:7057). 요약 최상위에 둔 진단은
   기록에 안 남고, 실제로 arm_qsplit 런에서 스위치가 켜져 돌았는데 확인할 방법이 없어
   상태 JSON 으로 역산해야 했다.

**승격할 때는 게이트를 올리는 것과 기능을 켜는 것을 구분한다.** 2026-09-04 정본에서
`urban.release_buffer.restore` 와 `urban.queue.window_stat` 은 config 로 **올리되 껐다** —
폐루프 부호가 미검증이라서다. 보이게 만드는 것이 켜는 것은 아니다.

관련: [[vissim-supersede-dont-flag]] [[vissim-default-stack-20260904]]
