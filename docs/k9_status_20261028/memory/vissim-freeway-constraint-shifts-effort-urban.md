---
name: vissim-freeway-constraint-shifts-effort-urban
description: 본선 모형을 더 제약할 때마다 도시가 좋아지고 본선이 나빠진다 — 세 개입에서 재현. 그리고 two-branch 는 VSL 권한은 줬지만 방아쇠는 못 줬다
metadata:
  type: project
---

2026-09-09/10, x15 Ver2. 서로 다른 세 개입에서 방향이 같다(veh·h, 상태적분):

```
h1 − f3 (λ_eff 발동)     도시 −68.7   본선 +131.7   램프  +3.3
h2 − n2 (λ_eff 발동)     도시 −17.1   본선  +93.3   램프  +7.8
i1 − n7 (two-branch FD)  도시 −54.2   본선  +49.1   램프 −19.4
```

컨트롤러가 "본선이 더 막힌다"고 믿으면 노력을 도시로 옮기고 순효과가 대체로 상쇄된다.
**본선 모형 정확도를 올리는 것만으로는 본선이 좋아지지 않는다.**

**two-branch FD 판정 (i1 = 7238.3, 무제어 −165.6 = −2.24%, n7 대비 −10.2 = 0.2σ).**
권한은 실제로 생겼다 — `effective_rho_crit` 이 vsl 120/100/80 에서 15.16/17.90/21.83 으로
움직이고(끄면 고정 27.00), VSL 사용도 21/31 → 24/31 로 늘었다.
**그런데 붕괴 창(t=900~1800)에는 여전히 안 쓴다** — n7·i1 둘 다 FW_E 전 셀 120.0 이고 80 은
t=2100 부터다(붕괴 개시 t≈1112). two-branch 를 켜면 ρ_c(120)=15.16 이라 t=900 의 최대 ρ 15.6 이
**이미 임계를 넘는데도** 안 움직인다 ⇒ **임계 초과가 목적함수에서 행동으로 번역되지 않는다.**

**권한(authority)과 방아쇠(trigger)는 다른 문제다.** two-branch·λ_eff·capacity drop 은 전부
권한 쪽이고, 남은 벽은 리더 목적함수(far·ncrit·TTD)와 가격이다.

관련: [[vissim-fwe-collapse-is-offramp-lane1]] · [[vissim-offramp-lane-closure-trigger-starved]] ·
[[vissim-capdrop-refuted-merge-structural]]
