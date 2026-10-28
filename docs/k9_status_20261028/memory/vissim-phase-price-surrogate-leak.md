---
name: vissim-phase-price-surrogate-leak
description: 현시가격 꼭짓점은 결함이 아니라 모델의 진짜 최적점이다 — 채점 과대 1.47배·부호오류 27.5%, 다만 순효과는 이득이고 손실은 σ 아래
metadata:
  node_type: memory
  type: project
---

2026-09-04 오프라인 실측(`scripts/probe_phase_price_curvature_20260904.py`).
**[[vissim-flat-local-cost-vertex]] 의 "꼭짓점 래칫 = 결함" 프레이밍을 정정한다.**

## 꼭짓점은 모델의 참 최적점이다

가격 방향으로 d 를 늘려가며 **전역 롤아웃을 실제로 굴렸다**(ctl_start900 t=900).

```
SC1001 p3   d=0 → 48 초에서 실제 ΔTTT  0 → -0.60   단조 감소, 상자 경계까지
SC1004 p3   d=0 → 48 초에서 실제 ΔTTT  0 → -1.70   단조 감소
```

응답은 **오목하지만 반환점이 없다.** 곡률을 정확히 넣어도 argmin 은 여전히 꼭짓점이다 —
"선형이라 꼭짓점으로 간다" 는 진단은 증상 설명일 뿐 처방이 아니었다.

## 진짜 결함은 외삽 거리다

가격은 **δ=6초** 유한차분인데 커밋점은 base 에서 36~50초다(6~8배). 커밋점에서
정련 점수(phased 국소 + Σ가격·Δg)와 실제 전역 롤아웃을 맞대면:

```
움직인 신호 40개 (3결정 x 17신호)
  점수↓ 실제↓  맞음      25 (62.5%)   실제 합 -4.49
  점수↓ 실제↑  부호오류  11 (27.5%)   실제 합 +0.31
  점수↑                    3           +0.00
  전체  점수합 -6.12  대  실제합 -4.18   =  **1.47배 과대**
```

배율이 방향마다 다르다 — SC1001 1.63배 과대인데 SC108 은 0.28~0.52배 **과소**다.
단순 가중치 축소로는 못 고친다.

**손실은 작다.** 부호오류 +0.31 은 이득 -4.49 의 **7%**. 폐루프 마진 -148.6 veh·h 에
비례하면 ~10 veh·h 로 시드 σ=50.7 아래다. → **지금 고칠 자리가 아니다.**

처방이 필요해지면: 커밋 후보를 전역 롤아웃으로 **1회 검증**하고 base 보다 나쁘면 기각.
비용 +17 롤아웃/결정(가격 68 위에 +25%, 결정 wall 145 → ~180초).

## 프로브 함정 둘 (되풀이하지 마라)

1. **`phase_shape_local_cost` 를 직접 부르면 drain 모형을 잰다.** 실런은
   `install_phased_price_local`(어댑터:1871)이 `_refresh_phase_prices` 를 통째로 갈아
   `_phase_local_cost_phased` 를 쓴다. 그 패치는 **컨트롤러 레벨**이라
   `build_priced_wu_link_controller` 안에 있고, cfg 레벨 하네스
   (`probe_far_components.build_cfg_and_state`)에는 안 들어간다.
   국소항은 `_phase_refine_context` → `_phase_refine_signal_setup` →
   `_phase_local_cost_phased` 순으로 재라.
2. **그 스위치 키는 최상위 `phase_price.price_local_model` 이다.** docstring 은
   `urban.phase_price` 라고 적었지만 코드는 `tuning.get("phase_price")` 를 읽는다.

## 부수 확인

- 가격 소음대역 없음 — 17신호 전부 최대|가격| ≥ 0.017. deadband 불필요.
- **첫 결정 72.3초 이동은 과도현상이다.** 균등 base 에서 출발해서다. 정상상태 평균은
  결정당 17.0초(SC1001 17.0 · SC1004 3.8 · SC109 53.1 이 최대).

관련: [[vissim-flat-local-cost-vertex]] [[vissim-price-local-term-drain]]
[[vissim-green-max-78-wall]] [[vissim-default-stack-20260904]]
