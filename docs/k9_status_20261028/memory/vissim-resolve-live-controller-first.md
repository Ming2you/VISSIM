---
name: vissim-resolve-live-controller-first
description: VISSIM 작업 전 scripts/resolve_live_controller.py 를 먼저 돌린다 — 구성을 추론하지 마라 (2026-08-20 하루에 6번 오독)
metadata:
  type: feedback
---

VISSIM Stackelberg 저장소에서 **컨트롤러 구성을 코드 읽고 추론하지 마라.** 작업 전에 먼저 돌린다:

```bash
python scripts/resolve_live_controller.py --tuning <config> --controller stackelberg
```

`--controller` 는 러너의 `-Controller` 와 같은 값을 넘긴다 — 이 인자가 flagship 분기를 정하고,
그 한 글자가 `leader_value_depth` 를 0/3 으로 가른다.

**Why:** 2026-08-20 하루에 구성을 여섯 번 오독했다. `green_sec`(플랜 주기를 녹색 길이로),
현시 녹색과 SG 계획창 혼동, 오프라인 하네스를 `flagship=True` 로 돌림, `N_P`(순유입을 누적으로),
450초 예측을 900초 실측과 비교, 가격이 어느 컨트롤러에 있는지. 컨트롤러가 27개고 게이트가
층층이라 한 자리만 틀려도 결론이 뒤집힌다.

**How to apply:** 해석기가 리더/팔로워 클래스 · player 수 · 레버 · budget · 가격채널 · 게이트 ·
목적함수 가중치 · 이 팔이 안 쓰는 controllers 파일을 다 찍는다. 사용자가 컨트롤러 삭제를
제안했을 때 앵커(`anchor_python_file_set` 121핀)가 깨지고 삭제가 `local_patches` 스키마로
표현 불가라 **삭제 대신 이 도구를 두기로 합의했다.**

[[vissim-workstation-state]] · [[vissim-parent-run-launch-traps]]
