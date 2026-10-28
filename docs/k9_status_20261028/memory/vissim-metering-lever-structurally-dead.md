---
name: vissim-metering-lever-structurally-dead
description: 미터링이 못 이기는 이유는 튜닝이 아니라 구조 — 가격 탐침이 수요를 못 가로지르고(정확히 0) capacity drop φ가 꺼져 물리 payoff 자체가 없었다
metadata:
  type: project
---

2026-09-09 n21/Ver2 진단. 첫 IC 병목(FW_E 셀 8/9, 붕괴 t≈1112)에 전조가 t=900 부터 있었는데
VSL 은 6결정 동안 120 을 유지했고 R_F_E 미터는 t=1650 까지 1800 이었다. 원인 둘 다 구조다.

**미터 가격이 정확히 0.000e+00 이다** (t=900~1650 전 구간 실측). 작동점이
`previous.ramp_metering` = 1800(= 램프 cap)인데 탐침 반경이
`d_r = max(metering_price_delta_veh_h 300, metering_price_trust_frac 0.20 × cap 1800) = 360`
이라 `m_lo = 1440`. 실측 램프 수요는 428~571 vph 뿐이라 두 코너 롤아웃이 동일 → 유한차분 0.
가격이 작은 게 아니라 **국소 미분이 존재하지 않는다**. trust 0.75 면 d_r 1350 → m_lo 450
으로 수요를 가로지른다. 키는 `adapter.flagship.metering_price_trust_frac`
(어댑터 7001행, 기본 0.20). 미터 가격은 green 가격보다 2~3자릿수 작기도 하다.

**`capacity_drop_discharge_phi` 가 1.0 = 꺼짐이었다.** φ<1 이면 ρ>ρ_cr 셀의 송출이 φ·용량으로
제한된다 — "임계 아래로 지키면 방류를 지킨다"는 payoff. `metanet_delta_merge` δ 는 켜져 있는데
(vendor 주석이 그걸 "metering 의 교과서적 payoff" 라 적었다) φ 만 꺼져 있었다. 적용 위치가
`local_freeway_plant.freeway_substep_local` = **팔로워가 후보를 채점하는 그 함수**이고
`metanet.py` 모델 플랜트에도 같이 들어가 예측-플랜트 정합이 유지된다. 문헌 근거 =
breakdown 후 배출률 5~18% 감소, vendor 권장 arm 0.85.

**단 φ 를 켜도 vendor 주석이 말하는 VSL 기구는 우리 config 에서 안 돈다.** 주석은
"VSL 이 ρ_crit(VSL) 을 올려 subcritical 로 지키면 drop 을 회피한다" 인데, 그건
`vsl_fd_two_branch` 가 있어야 한다 — 없으면 `effective_rho_crit` 이 고정 `net.rho_crit`
을 그대로 돌려준다(metanet.py:65). 그래서 φ 의 payoff 는 **밀도 채널로만** 온다:
미터가 합류 유입을 줄여 ρ 를 임계 아래로 지키는 것. VSL 쪽 payoff 는 절반만 산다.
two_branch 를 켜려면 FD 재적합(`rho_jam`)이 먼저다.

관련: [[vissim-vsl-sign-zones]] · [[vissim-ramp-meter-actuation-is-binary]] ·
[[vissim-price-rollout-budget]] · [[vissim-ver2-mapping-signals-defect]]
