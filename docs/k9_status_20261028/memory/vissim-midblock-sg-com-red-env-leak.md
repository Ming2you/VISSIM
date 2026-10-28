---
name: vissim-midblock-sg-com-red-env-leak
description: RW_MAINLINE_SG_ONLY 는 러너가 아니라 옛 큐 스크립트가 세우는 env 라, 2026-09-04 16:31 이후 Bash 로 띄운 체인의 모든 런이 미드블록 SG(9+)를 COM 적색으로 고정한 채 돌았다 — "나쁜 유역"의 정체
metadata:
  type: project
---

`signal_readback.csv` 에 `900,5,14,RED,RED` — 러너가 컨트롤러 5 의 SG 14(WBT 미드블록 횡단, native 녹색 101 s)를
COM 으로 RED 요청. 런로그 `SIGNAL_MIDBLOCK_COM_SKIPS=0`. VBS 는 `RW_MAINLINE_SG_ONLY=1` 일 때만 SG 9+ 를 건너뛰는데
(`IsControlledSignalGroup = sg<=8`), 그 env 는 **러너 ps1 이 아니라 launch_*/queue_* 스크립트들이** 세웠다
(queue_audit2_20260904 이 마지막). 내가 Bash 에서 띄운 체인(relaunch_satcap·chain1·followup)은 안 세웠다.

```
09-04 ≤14:40  skips 888/744  native   ← ctl_start900 s13 기준 7803 포함
09-04 16:31~  skips 0 · (5,14) 151행  RED  ← C/D/G/H·objbase·meterfullopen·blindfix·s14·uni1800·v2·cap 전부
```

증상: SC5→SC101 링크(1220014203, 4차로 전부 SG 5/14)가 막다른 길 → t≈1200 부터 124/124대·0 kph 영구 →
SC5 서쪽 출구 spillback → SC5 접근로 +695 = 손실 96%. s13 이 "좋았던" 건 그 막다른 길에 차를 덜 넣었을 뿐이 아니라
**그 런에서는 SG 14 가 native 로 돌았기 때문**이다.

**Why:** 메모리 [[vissim-gate-outside-config-is-dead]] 그대로 — env 전용 게이트는 호출 경로가 바뀌면 조용히 꺼진다.
09-04 16:31 이후의 팔 비교·"시드 증폭 39배"·"곡률 체제" 판정은 전부 이 결함 위에서 나온 것이라 **재판정 대상**.

**How to apply:** 러너 ps1 안에서 config `urban.plan.mainline_only` 로 env 를 세우게 고쳐라(체인 스크립트 의존 금지).
런 시작 후 반드시 런로그 `SIGNAL_MIDBLOCK_COM_SKIPS>0` 과 readback 에 (5,14) 행이 **없음**을 확인해라.
관련: [[vissim-blindfix-load-bearing-under-curvature]] [[vissim-model-flat-where-plant-steep]] [[vissim-parent-run-launch-traps]]
