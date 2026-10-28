---
name: vissim-far-rates-measured
description: far 배수율(도시 G·본선 g_fw·램프 merge)을 VISSIM 링크평가 150초 실측으로 배선했다 (2026-09-01). g_fw 상수 300 이 실측 612 의 절반이었다
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-31T17:17:56.824Z
---

2026-09-01, `mfd_far_cost_to_go` 의 배수율이 전부 vendor 상수였던 것을 VISSIM 실측 온라인
채널로 바꿨다. far 는 `N²/(2G)` 라 G 가 배수 곱이 아니라 **곡률**을 정한다.

```
             상수         실측(구간 최대)
도시 G       640 / 500    732 / 572
본선 g_fw    300          612            <- 방류능력을 2배 과소평가하고 있었다
램프 merge   1800 x 4     1248/1776/1464/888
```

**사용자가 방향을 잡아줬다.** 나는 150초 상태 스냅샷 차분으로 가려 했는데 그건 커넥터에서
과소계상한다(램프 250 vph vs 실측 886). 사용자가 "link data 150초 volume 칸을 읽으면
online update 아니냐"고 했고 그게 맞았다 — VISSIM 이 구간 내내 세므로 체류시간과 무관하다.

`.fzp` 는 1초가 아니라 **5초** 해상도다(스냅샷 1080장). 정답지 전용이다.

관련: [[vissim-measured-capacity-online]] 의 도시부 movement 용량과 같은 감쇠 러닝맥스를 쓴다.
[[vissim-arm-confusion-whose-code]] — far 는 wu-link 에서 채점 호출의 3.2%(리더 5회)에서만
켜지고 가격 경로 126회는 안 본다. 상세는 저장소 CLAUDE.md 의 "far 배수율은 이제 VISSIM
실측이다" 절에 있다.

**Why:** 램프 merge 를 고치려고 `ramp_capacity_veh_h` 를 낮췄다가 N_UF 상한을 52% 잘라먹을
뻔했다(그 dict 는 `_force_open_ramps`·`_candidate_bounds` 도 읽는다). 그리고 내가 넣었던
752/1212/938/555 는 **수요 평균**이지 용량이 아니었다.

**How to apply:** far 전용 값은 `cfg.network.far_ramp_capacity_veh_h` 에 따로 얹고
`install_far_ramp_capacity_patch` 가 호출 동안만 스왑한다. 공용 dict 는 1800x4 로 둔다.
