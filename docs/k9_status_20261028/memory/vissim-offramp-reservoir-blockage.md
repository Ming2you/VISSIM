---
name: vissim-offramp-reservoir-blockage
description: W_out(링크 31/68) 유입이 plant 의 60% 인 진짜 이유 — off-ramp 저장고에 차량이 쌓이기만 한다. 출구가 신호 movement(207/차로)로 표현되고 W_out 직행 beta 0.167(실측 0.47), 저장고 관측 0. 녹색·용량 문제가 아니다 (B3 후보)
metadata:
  type: project
---

2026-09-05 19:30, 정본 상태 ctl_start900 t=2400, 결합 롤아웃 1구간(150 s) 실측:

```
freeway → off-ramp 저장고 도착   191 veh/150 s (≈4,600 vph, 램프당 ~1,150 = plant 착지 10479 1,061 · 10645 1,019 · 10491 1,200 와 일치)
저장고 점유                     0 → OR_D_W 38.6 · OR_D_E 24.5 · OR_F_W 18 · OR_F_E 32   (쌓이기만 함)
off_ramp movement 큐 (8개)      1.6 → 1.6 (변화 없음)   cap 207 vph/차로 · gf 0.13~0.48 · 현시 p3/p4
```

plant 는 D 서측 off-ramp 를 **반반**으로 내려놓는다: 10491 → 링크 32(SC1001 접근, 신호 통과) 1,200 vph, 10479 → 링크 31(W_out,
신호 안 거침) 1,061 vph → W_out 몫 0.47. 모형은 `SC1001_offW_to_W_RAMP` 에 beta 0.167 만 주고 5/6 을 신호 통과 movement 로
보내며, W_out 행마저 SC1001 p3 녹색을 받게 돼 있다. 저장고 관측은 0(39/39 결측, 기존 메모리). → 삼중 결손.

**Why:** B 의 주입 총량이 실측의 0.74→0.48→0.33 으로 감쇠하고 uni1800 으로도 0.85→0.58 인 이유. 녹색 배분(커밋값과 동일)도
per-lane 용량(5배 올려도 0.11 개선)도 아니다. base 도 같은 구조지만 base 는 저수지를 외생 ramp_arrival 로 채워 W_out 에 안 의존했다.

**How to apply (B3 후보):** (1) W_out 착지분(10479/10645 링크평가 실측 또는 실측 분율 0.47)은 신호 없이 W_out 저류로 직접 도착,
(2) 접근로 착지분(10491/10481)은 W 접근 큐로 — 이건 신호 통과가 맞음, (3) 저장고 배수 용량을 on/off-ramp 연결로 용량으로.
관련: [[vissim-legsplit-B1-stock-tau]] [[vissim-onramp-coupling-promoted]]

**B3 구현·검증 (2026-09-05 19:35~19:55):** `install_offramp_direct_landing`(`urban.ramp.offramp_direct`): W_out 착지 movement 4개를
beta 0.46/0.50(실측 착지분율)·무신호(`unsignalized` → 녹색분율 패치가 1.0)·용량 1,800·수신을 새 sink `<SC>_W_tail`(cap 200,
꼬리 배출 상한 parameters `runtime.network.wout_tail_exit_capacity_veh_h` 5400/7200, 래퍼가 추가 배출)로. 꼬리 통과속도는 래퍼가
W_out 관측 유효속도를 미러(vendor 지연 = 가용공간×6 m/속도).
**시각 전진(`state.time_sec += 150`)을 넣은 6구간 시험**(빠뜨리면 step index 가 480 으로 리셋돼 예약이 영영 pop 안 되는 하네스 결함):
```
B2  저장고 OR_D_W 39→77→113→120(상한) 포화 · 램프 주입 6구간 0.35/0.42/0.42/0.42 (실측 대비)
B3  저장고 ~18/14/14/18 · 꼬리 ~16 안정 · 램프 주입 0.25/0.30/0.33/0.33   ← B2 가 높았던 건 램프에 못 가는 착지 차량이 W_out 재고를 부풀린 것
B3+uni1800  램프 주입 0.50/0.61/0.60/0.59 · SC1001 S 접근 W 행 큐 26→88 (gf 0.14 로 못 뺌)
```
→ 남은 결손 = 신호 통과 W 행 방류 Q_sig(용량·상류 도착·S 접근 녹색). g2 = B3 로 교체(드라이버 v5).

