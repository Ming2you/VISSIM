---
name: vissim-metering-grid-blindspot
description: FW_E 미터링 후보 격자의 하한이 available 보다 높아 후보 7개 롤아웃이 비트동일 — 동측 미터링 결정에 payoff 정보가 아예 없다. δ·가격·FD 어느 수정도 여기 못 닿는다
metadata:
  type: project
---

2026-09-09 15에이전트 교차검증에서 확정. 등예산 미터링 탐색(`wu_faithful_follower.py:3610-3644`,
`metering_price_split=True` 라 이 분기가 산다)의 FW_E 격자는
`linspace(ω_E·N_UF* − 1800, 1800, 7)` = [1122.33 … 1800.00] 인데,
모델의 방출 상한 `available = ramp_queue / T_f_h` 는 t=900 에 **1080(R_D_E) / 720(R_F_E)** 다.
**후보 7개가 전부 상한 위라 롤아웃이 비트동일**하고 승자는 격자 순서가 정한다
(`best_cost = inf`, 엄격 `<` → `splits[0]`). 검증자가
`0.5278631356412602 × 5536.142448979592 − 1800 = 1122.3255124750526` 을 16자리로 재현했고
커밋된 `R_D_E` 와 같다.

**그래서 동측 미터링 "결정" 에는 payoff 정보가 없다.** 약한 기울기가 아니라 사각지대다 —
δ_merge 를 고치든 가격 탐침을 넓히든 FD 를 재적합하든 이 격자를 안 고치면 FW_E 에 못 닿는다.
붕괴가 일어나는 쪽이 바로 FW_E 다.

FW_W 는 다르다: 격자가 813.82 에서 시작해 `available` 이 실제로 물리고, 0 이 아닌 미터 가격
둘도 서측 램프다(R_D_W −7.570e-06 · R_F_W −3.661e-05).

수정 방향: 격자 하한을 N_UF 예산이 아니라 `min(available, ω·N_UF* − cap)` 에서 유도한다.
재적합 불필요. vendor 직접 편집 금지이므로 어댑터 몽키패치 자리다.

관련: [[vissim-metering-lever-structurally-dead]] · [[vissim-ramp-meter-actuation-is-binary]] ·
[[vissim-model-flat-where-plant-steep]]
