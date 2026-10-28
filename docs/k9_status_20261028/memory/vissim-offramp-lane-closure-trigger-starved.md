---
name: vissim-offramp-lane-closure-trigger-starved
description: METANET off-ramp spillback 차로폐쇄(λ_eff)는 구현·기본ON·식도 맞는데 방아쇠인 저장고 점유 관측이 39/39 전부 0이라 한 번도 발동한 적이 없다
metadata:
  type: project
---

2026-09-09. 사용자가 문헌식(N_eff = (N−1) + exp[−(1/b)(n_o/(γ·n_o^max))^b])을 들고 물어서 확인.

**있다. 그리고 켜져 있다.** `metanet.offramp_spillback_lambda_eff`(:168-186, 주석 "Wu Eq.(22) 계열")
+ `effective_lane_profile`(:189), 팔로워 복제는 `local_freeway_plant._local_lane_profile`(:106-119)
— 리더 롤아웃과 팔로워 채점 양쪽에 들어간다. 런타임 실효값
`enabled=True · lane_reduction=1.0 · gamma=0.5 · b=2.0` (default.yaml 이 dataclass 기본 0.35 를 덮는다).
`off_ramp_storage_link` 도 런타임에 채워진다(config 는 빈 dict 지만 default.yaml 병합) —
**죽은 코드라고 판단하지 마라, 내가 한 번 그렇게 오독했다.**

**고장은 방아쇠다.** λ_eff 점유는 `OR_*_storage` 저장고 점유인데 실런 진단이
`local_observation_offramp_storage_occupancy = 0.0` 이다 — 어댑터 주석대로 관측 채널
`off_ramp_storage_veh` 가 **39/39 표본 전부 0**. 점유 0 → `capacity_veh<=0` 분기 → nominal 차로 반환
→ **차로폐쇄가 한 번도 발동하지 않았다.**

**심는 함수는 이미 있다**: `install_landing_storage` + `install_landing_storage_runtime` +
매 결정 `_apply_landing_storage`. 전부 `urban.ramp.landing_storage` 유무에만 걸린다(없으면 no-op).

**실측 용량·점유** (`outputs/offramp_landing_cap_ver2_20260909.json`, 길이×차로×jam 168.18):
```
OR_F_E 커넥터 10682  38.1 veh  실측 평균 18.8 최대 24  포화 49%  ← 셀 8, 유일하게 포화
OR_D_E 10483 50.8 / 2.7 (5%) · OR_D_W 10479 43.5 / 2.2 (5%) · OR_F_W 10645 58.9 / 3.8 (6%)
```
λ_eff: 점유 49% → 0.386 차로 손실(−9.6%), 63% → 0.548(−13.7%), 100% → **1.000 차로(−25%)**.
VISSIM 이 보이는 차로 1 폐쇄와 같은 크기다.

**옛 B4c 이중계상 함정 회피법**: B4c 는 도시 **접근로**(링크 32 등) 재차를 심어 어댑터 도착 seed 와
겹쳤다. off-ramp **커넥터 자신**만 세면 겹치지 않는다 — 그 차량은 movement 큐에도 도착 버퍼에도
없다. `queue_prefix` 를 비워 정지큐 차감도 끈다(진단 `landing_storage_queue_* = 0.0` 으로 확인).

팔: `scripts/chain_n21_offramp_landing_20260909.py` → `n21x15h_h1_landing_20260909` (f3 7496.6 분기).

관련: [[vissim-fwe-collapse-is-offramp-lane1]] · [[vissim-offramp-reservoir-blockage]] ·
[[vissim-gate-outside-config-is-dead]]

**v3b 재검증 (2026-09-27):** 이 결론은 옛 21셀 시나리오 것이다. v3b 에서는 [[vissim-fwe-plant-structure-20260927]] 참조 — 붕괴 기원은 10681 합류 차로 2, off-ramp 차로폐쇄는 배포 프로필에서 꺼져 있음(occupancy_lane_loss false).
