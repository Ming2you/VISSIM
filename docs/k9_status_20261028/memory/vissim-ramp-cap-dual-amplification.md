---
name: vissim-ramp-cap-dual-amplification
description: LocalSignalModel.ramp_queue_max 를 0→111/153 으로 고치면 nin 유출항이 살아나 듀얼 λ_P 를 타고 전 신호로 증폭돼 TTT +1432 — 2신호 국소 수정이 전역으로 번지는 경로
metadata:
  node_type: memory
  type: project
---

2026-09-04. **4팔 분해로 귀속이 깨끗하게 떨어졌다** (같은 망 rampbn_qc · 시드 13 · ControlStartSec 900).

```
팔                              TTT      미터합   lambda_P  도시재차  고속속도
기준 (셋 다 꺼짐)              7829.0     6049     2.90     3521    42.2
C    cap 만                   9261.3     3881     6.13     4614    42.0
D    cap + 램프국소            9262.3     3529     5.81     4516    39.8
E    cap + 램프국소 + in_gne    9268.4     3573     5.81     4606    41.7

② cap 수정   +1432.3 (28.3 sigma)  <- 손실 100%
① 램프국소       +1.0 (0.02 sigma)  <- 잡음
③ in_gne        +6.1 (0.12 sigma)  <- 잡음
```

**[[vissim-has-ramps-drain-fallback]] 와 [[vissim-ingne-demand-kwarg-bug]] 의 두 패치는 정상
작동하지만 폐루프 TTT 를 안 움직인다.** 국소비용 곡률 0->3.5/5.6, in_gne 램프채점 10->242,
꼭짓점 부착률 47%->33.7% 로 전부 의도대로인데 결과가 안 바뀐다. 고칠 가치는 있으나
**성능 지렛대가 아니다.**

## 전파 경로 — 국소가 아니라 듀얼이다

`local_signal_plant.py:123` 의 `ramp_queue_max` 는 SC1001·SC1004 두 신호 국소 모형만
건드리는데, 실제로 녹색이 갈린 곳은 **비램프** 신호였다
(t=900~1950 L1: SC7 444 · SC6 396 · SC16 373 · SC109 369 / SC1001·SC1004 는 합계 −0.9초).

```
① ramp_queue_max 0 -> 111/153
② rollout_local_tts_ramp_aware:381  ramp_space = max(0, cap - res)
   cap 0 이면 ramp_space ≡ 0 -> scale = 0 -> actual = 0
   => on-ramp movement 가 국소 모형에서 **한 번도 방류를 못 했다**
      (전역 plant urban_queue_model 은 2026-09-01 에 이미 개별 상한으로 고쳐져 정상 방류)
③ nin_i = sum_INFLOW served - sum_OUTFLOW served,  OUTFLOW ∋ on_ramp
   => cap 0 은 유출항을 영구 0 으로 만들어 Sigma nin 을 과대평가했다
      feasible_max 179.9 -> 95.4 (-47%) · np_target 124.6 -> 65.7
④ 리더 N_P* 164.2 -> 29.6 (-82%) · np_target_error +44%
⑤ lambda_P 가 `+lambda_P * nin_i(green)` 로 **17신호 전부**의 국소 채점에 들어간다
   평균 2.90 -> 6.13 · 비영 9/31 -> 19/31 결정
⑥ 전 신호 녹색 재배분 -> 도시 누적 (미터링 아직 동일한 t=1950 에 이미 +296대)
⑦ t=2100 리더가 미터를 하한 1440 으로 **쾅** (bang-bang, 조절 아님)
⑧ 램프에 차 갇힘 46->148->190 · 도시 +2436 · 본선은 무변화(속도 42.2->42.0, 재차 2281->2254)
```

**본선이 전혀 안 좋아진다는 것이 핵심이다.** `metanet_delta_merge = 0` 이라 램프 유입이
본선 속도를 안 건드리고 `freeway_congestion` 도 전 구간 0 이다. 미터링은 이득 경로가
없는 채로 조이기만 한다 = 순수 도시 비용.

## delta_merge 를 켜서 이득 경로를 열자는 것도 답이 아니다 (기록 확인)

```
쌍           d=0.0     d 켬      TTT      미터합
bn          8770.0   9334.2    +564   3442->3069  조임
far         7227.7   6897.5    -330   3783->4178  **엶**  <- 유일한 승리
farbn       8596.0   8771.0    +175   3702->3529  조임
wrq0 d4.0   7197.2   7479.8    +283   3464->3304  조임
wrq0 d17.3  7197.2   7602.3    +405   3464->3553  거의 동일
```
5쌍 중 4쌍 패배, 진 쌍은 전부 조였다. 이긴 far 만 열었다. 방향이 일치한다.

## 그래서 `ramp_queue_max = 0` 은 버그이자 브레이크였다

회계로는 cap 수정이 옳다 — on-ramp 유출이 안 보이던 것이 정상이 됐다. 그런데 컨트롤러는
그 정보를 받고 N_P 를 82% 낮추고 미터를 하한으로 닫는다. 이 망에서 그건 순손실이다.
**모델을 고치면 컨트롤러가 나빠지는 구조** — 고칠 곳은 cap 이 아니라 그 반응이다.

다음: `dual.lambda_np_cap` (2026-09-04 신설 스위치, 0 이면 lambda 영구 0) 으로 2x2
(G = cap끔·lambda끔 / H = cap켬·lambda끔). H≈G 면 해악이 전부 듀얼을 탄 것.

관련: [[vissim-has-ramps-drain-fallback]] [[vissim-ingne-demand-kwarg-bug]]
[[vissim-onramp-coupling-promoted]] [[vissim-leader-np-erased-by-projection]]

## 2x2 로 확정 (2026-09-05)

`dual.lambda_np_cap = 0` 스위치로 lambda 를 영구 0 으로 묶고 4칸을 다 채웠다.

```
              cap 끔      cap 켬
lambda 켬     7829.0      9261.3    (+1432.3, 28.2 sigma)
lambda 끔     9099.9      9099.9    (+0.0, **레버 해시 비트 동일** 7057dcfd…)
```

**lambda 를 끄면 cap 수정이 제어를 한 비트도 안 바꾼다.** H 에서 cap 은 정상 발화했다
(`local_ramp_queue_cap_was_zero = 2.0`). 해악이 100% 듀얼을 탄다는 확정 증거다.

**다만 lambda 자체는 일을 한다** — 끄는 것만으로 +1270.9 (25.1 sigma). 즉 답은
"lambda 끄기"가 아니다. 리더가 lambda 에게 시키는 목표가 문제다.

## 진짜 결함 — N_P 목표가 도달 불가다

```
                 np_target 이 feasible 범위 밖    lambda 포화(=10)
기준 (cap 끔)        3/31 (10%)                   9/31
C    (cap 켬)       11/31 (35%)                  19/31
```

범위 밖 값은 **전부 -250.0** — 리더 탐색 박스의 하한이다. 팔로워 도달 범위가
`[153, 377]` 인데 리더가 -250(최대 도시 배수)을 요구한다. 도달 불가라 lambda 가 상한 10 에
붙고, 그 lambda 가 `+lambda*nin_i(green)` 로 17신호 전부의 채점을 지배한다.
CLAUDE.md '유출 실명' 절이 이미 적은 결함이고(21~23/37 결정에서 N_P*=-250),
**cap 수정은 그 빈도를 10% -> 35% 로 키운다.**

## 사영은 있는데 새고 있다 (다음 시작점)

`_project_action_to_follower_feasible_np`(stackelberg_mpc.py:1987)가
`min(max(raw, lower), upper)` 로 클램프하고 후보마다 호출된다(:1523 · :1940).
실측: active 9/31(기준) · 19/31(C) · failed 0 · applied 6/8 · 잔차 38.

**그런데 사영이 active 인 결정에서도 `wu_faithful_np_target` 이 -250.0 으로 간다.**
active 가 31/31 이 아닌 것도 미해명이다 — 리더 후보가 기각되고 PFO 폴백이 커밋되면
사영된 값이 아닐 수 있다. 여기가 다음 조사 지점이다.
