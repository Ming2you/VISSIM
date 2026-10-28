---
name: vissim-density-penalty-closes-ramps
description: 리더가 램프를 하한으로 닫는 이유는 far 도 램프큐도 아니고 density_penalty 다 — TTT 가 나빠지는데도 채택되고, 그걸 막을 가드 관문(min_ttt_gain_frac)은 0 으로 꺼져 있다
metadata:
  node_type: memory
  type: project
---

2026-09-05. **"램프 큐가 큰데 왜 유입을 막나"의 답.** 램프 큐 때문이 아니다.

## 쾅 친 결정의 후보 비교 (C 팔, t=2100)

```
후보 A   N_UF = 1440   objective 2509.2465   rollout TTT 957.9747
후보 B   N_UF = 7200   objective 2523.9225   rollout TTT 957.1774   (PFO incumbent)
                       차이 -14.68 (0.58%)   차이 +0.80  <- TTT 는 A 가 **더 나쁘다**
```
리더는 **자기 rollout TTT 가 나쁜 쪽**을 objective 가 0.58% 낮다는 이유로 골랐다.

## objective 분해 — 범인은 density_penalty

```
leader_objective_base       2176.80
leader_density_penalty       322.83   <- 비-base 항의 97% (w_F = 3.0)
leader_mfd_storage_penalty     9.62
leader_boundary_in_queue       0.00
leader_target_penalty          0.00
leader_ramp_queue_penalty      0.00   (w_ramp_queue = 0, 의도된 값)
                            -------
leader_objective            2509.25
```

far 도 target 도 ramp_queue 도 0 이다. **램프를 닫으면 본선 유입이 줄어 밀도 초과가 줄고,
그 벌점이 준다.** 모델 안에서는 일관되지만 TTT 와 어긋난다.

## 톱니 거동 (기준·C 동일)

```
램프큐 0        -> 미터 전개방 7200
램프큐 발생     -> 하한 1440 으로 **쾅** (조절 아님)
그 뒤           -> 결정당 +1200 씩 기어오름 (신뢰반경 leader_local_nuf_radius_veh_h = 1500)
큐 다시 발생    -> 또 쾅
```
[[vissim-ramp-cap-dual-amplification]] 의 cap 수정이 한 일은 **큐 발생 시점을
t=4350 -> t=2100 으로 2250 초 앞당긴 것**뿐이다. 그래서 런 대부분을 쾅/기어오름 구간에서 보낸다.

## 가드가 이걸 잡으라고 있는데 꺼져 있다

`stackelberg_mpc.py:1682-1687` 주석이 같은 사건을 이미 적었다 —
"모델이 중립이라고 말하는 행동을 커밋하고 plant 에서 손해를 본다.
`insufficient_gain` 은 terminal/completed 가 함께 나쁠 때만 쓰여 이 경우를 못 막는다."

실측 진단이 그대로다: `insufficient_gain = 1.0` (필요 126.20 대 실제 14.68) 인데
`rejected_leader = 0.0`. 표시만 하고 통과시킨다. TTT 차 -0.80 은 margin 1.0 안이라 안 걸린다.

처방도 코드에 있다:
```python
_min_frac = getattr(cfg.mpc, "stackelberg_fallback_guard_min_ttt_gain_frac", 0.0)
if _min_frac > 0.0:
    ttt_worse = (fallback_ttt - leader_ttt_guard) < _min_frac * max(fallback_ttt, 1.0)
```
**실효값 0.0 (state.py:722 기본값) · 저장소 config 어디에서도 켠 적 없다.**
`use_rollout_ttt` 는 True 라 비교 자체는 TTT 로 하고 있다.

## 다음

`stackelberg_fallback_guard_min_ttt_gain_frac` 을 작은 양수(예: 0.001 = 0.1% 실질 이득 요구)로
켜는 팔. 그러면 TTT 중립/악화 행동은 폴백(전개방)으로 떨어진다.
병행: `arm_meterfullopen_20260905` (N_UF_star_range 를 [7200,7200] 로 고정)이 인과를 직접 확인한다.

8팔 상관: 미터 개방률 대 TTT r = -0.947 · 기울기 -581 veh·h / 1000 vph.
단 무제어(개방 100%, 신호제어 없음)는 7952.4 로 기준 7829.0 보다 나쁘다 —
"많이 열수록 좋다"가 아니라 "신호제어는 이득, 램프 닫기는 손해"다.

관련: [[vissim-ramp-cap-dual-amplification]] [[vissim-why-control-loses]]

## 정정 — 미터 개방률은 인과가 아니었다 (2026-09-05 강제 개방 실험)

`leader.N_UF_star_range = [7200,7200]` 로 램프를 **강제 전개방**하고 나머지는 canon 그대로 돌렸다.

```
팔                       TTT      개방률   도시    고속   램프  고속속도
기준 ctl_start900      7829.0      84%    3521   2281    53    42.2
C  cap 켬              9261.3      54%    4614   2254   126    42.0
G  lambda 끔           9099.9      64%    4458   2309    98    41.2
전개방 N_UF=7200       9117.7     100%    4568   2270    41    42.6
```

**전개방이 +1289 (25.4 sigma) 로 오히려 나쁘다.** 8팔 상관 r=-0.947 은 인과가 아니었다.
미터링과 도시 누적이 **둘 다 다른 무언가의 하류**였던 것이다.

## 진짜 그림 — 양극 체제이고 갈리는 것은 녹색이다

```
좋은 체제  ctl_start900 7829.0 · ctl_canon 7972.7 · arm_qsplit 7972.7
나쁜 체제  C 9261.3 · D 9262.3 · E 9268.4 · G/H 9099.9 · 전개방 9117.7
중간이 없다.
```

고속도로 재차는 **전 팔이 사실상 동일**하다(t=5400 에 2343~2623). 갈리는 건 전부 도시다.
그리고 C(미터 54%)와 전개방(100%)의 **도시 궤적이 거의 같다** —
t=1500 2944/2944 · t=1800 3334/3334 · t=3600 5417/5391. 미터링과 무관하다.

기준만 후반에 도시를 비운다(t=3600 4165 -> t=5400 3529). 나머지는 계속 쌓인다(5417 -> 5965).

## 녹색 거리 행렬 — 기준이 외톨이다

```
결정당 녹색 L1      기준      C    전개방      G
기준                 0.0   644.4   576.4   600.3
C                  644.4     0.0   226.6   379.7
전개방              576.4   226.6     0.0   371.3
G                  600.3   379.7   371.3     0.0
```
**서로 무관한 세 변경(cap 수정 · lambda 끔 · N_UF 고정)이 전부 기준에서 멀어져 서로 가까운
녹색 패턴으로 수렴한다.** 차이는 SC7 · SC108 · SC6 · SC107 · SC16 · SC105 에 몰린다(램프 신호 아님).

즉 "무엇이 미터를 닫는가"가 아니라 **"무엇이 녹색을 기준 패턴에서 밀어내는가"** 가 진짜 질문이다.
기준 패턴이 정말 좋은 것인지, 아니면 기준이 칼날 위에 있고 나쁜 쪽이 컨트롤러의 자연 끌개인지는
아직 모른다.

다음: 리더 목적함수를 base 하나로 줄인 사다리 6팔(`arm_objbase*`, w_F=0 · mfd_storage=0)이
돌고 있다. 목적함수가 그 밀어냄의 원인인지 가른다.
