---
name: vissim-offramp-drain-share-semantics
description: off-ramp 저장고 배수는 β×잔여점유를 매 substep 재계산 — 무신호 출구 하나가 저장고를 통째로 비워 p3 를 무가치하게 만든다(B3 실패 기구). 착지 분할은 유입 함수에서 걸어라(B4a)
metadata:
  type: project
---

# off-ramp 저장고 배수 의미론과 B3 의 실패 (2026-09-05 밤)

`_drain_offramp_storage` (vendor urban_queue_model.py:542): movement 별 `intended = min(β × 잔여점유, dt·gf·cap)`.
β 는 "지금 남은 pool 의 분율" 이라 신호 movement 가 적색이어도 무신호 movement 가 매 substep 잔여의 β 만큼
가져간다 → 저장고가 통째로 비워진다. 모든 movement 가 같은 현시일 때만 상대비가 보존된다.

**B3 (g2_B_x18_20260905, TTT 9115.0 = 기준 7741.5 +1373.5) 실패 사슬**
1. `SC1001_off*_to_W_RAMP` 를 무신호(gf 1)·β 0.46·cap 1800 → 저장고가 p3 없이도 비워짐 → p3 녹색 무가치
2. SC1001 **첫 결정(t=900)부터** 75/21/21/21 (기준 22/23/71/23). 두 런의 plant 상태가 t=900 에 동일하므로 순수 모형 차이
3. 링크 32 재차 160 → 735 (p3 20 s 로는 게이트 1,333 + 착지 10491 1,395 − peel-off 869 ≈ 1,860 vph 를 못 뺀다)
4. off-ramp 10491 가 FW_W 로 역류 → FW_W 1,071→1,629 · FW_E 589→2,157 → **본선 +1002 veh·h**(미터 폐쇄 탓이 아니다)
5. 리더가 본선 정체에 반응해 R_D_W 0 · R_F_E 0 으로 닫음 → 램프 +210. 미터 폐쇄는 결과이지 원인이 아니다

**Why:** "직행 착지 분율" 은 착지 시점(연결로 선택)에 정해지는 양인데, 잔여 pool 분율로 넣으면 매 substep 재적용된다.

**How to apply (B4a):** 유입 함수 `schedule_offramp_arrivals(state,cfg,off_ramp,veh,step)` 를 감싸 s(D 0.468 · F 0.484,
30결정 실측 10479/(10479+10491) · 10645/(10645+10638)) 는 `<SC>_W_tail` 점유로, (1−s) 만 저장고로. `_to_W_RAMP`/`_to_W`
는 정지선→W_out 물리 회전이 없으니 β 0 + 형제 재정규화. coupling.py 가 이름으로 import 하므로 sys.modules 재바인딩,
워커 부트스트랩(`install_price_worker_runtime_patches`)에서도 다시 건다. 관련: [[vissim-offramp-reservoir-blockage]]
[[vissim-legsplit-B1-stock-tau]].

**plant 사실(같은 날 실측)**: 링크 32 진출 5개(10118→30, 10368→39, 10695→38, 램프 10482→26, 10490→2). 10481/10483(FW_E 쪽 off-ramp 착지)은 far 대장에 없어 **미측정**(0 이 아니다). 모형 off-ramp 유량 t=1800: OR_D_W 1413 · OR_F_W 960 · OR_D_E 870 · OR_F_E 1444 (합 4,686)
대 배출 1,932 vph → 롤아웃에서 저장고(cap 120)가 차오른다. 모형 서측 게이트는 peel-off 차감 뒤 97 vph, 링크 32 큐 5.6 대
(plant 160 대) — 이동 중 차량은 큐에 안 잡힌다(기준선도 같음).

**링크 31/68 커넥터 위치 (.inpx, 2026-09-05 23:00 확정)**
- 31: 신호 유입 10698/10119/10121 @2 · 링크78 유입 10703 @351 · 진출 10704→79 @281 · **R_D_E 10484 @412 · R_D_W 10480 @735** ·
  FW_E off-ramp 10483 @614(→ R_D_W·자유만 가능) · FW_W off-ramp 10479 @871(→ 자유만). far 실측: 신호 534 · 직행 1015 · 램프행 824.
- 68: 신호 10629/10625/10633 @2 · **R_F_E 10681 @117** · FW_E off-ramp 10682 @237(→ R_F_W·자유) · **R_F_W 10646 @352** ·
  FW_W off-ramp 10645 @573(→ 자유만). far 실측: 신호 1378 · 직행 1006 · 램프행 1110.
- 그래서 B4b: OR_*_W 직행 → 꼬리 sink, OR_*_E 직행 → W_out pool(τ 분할). 링크 78(2차로, 80/76/84 발, 재차 5~16)은 미측정 유입.
