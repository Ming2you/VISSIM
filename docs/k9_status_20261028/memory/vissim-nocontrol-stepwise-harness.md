---
name: vissim-nocontrol-stepwise-harness
description: "plant 검증용 무제어 스텝별 런 만드는 법 — -ForceStepwise 는 러너 인자여야 하고(env 는 덮인다), 무제어는 도시신호를 COM 제어 안 해서 네이티브가 돈다"
metadata:
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-26T15:35:32.787Z
---

plant 롤아웃 정확도를 재려면 **컨트롤러가 루프에 없는** 데이터가 필요하다. 제어런을
재생하면 off-policy 오염이 생긴다(옛 config 가 고른 action 을 새 config 로 먹이는 꼴,
경계저류 39개 때문에 t=0 에 이미 +441대 차이).

```bash
scripts/launch_nocontrol_stepwise_20260826.ps1     # 621초에 끝난다 (제어런은 5,705초)
```

## 함정 셋

**1. `RW_FORCE_STEPWISE` 를 환경변수로 세워봐야 소용없다.** 러너가 자기 `-ForceStepwise`
스위치로 **덮어쓴다**(`run_real_world_single_watchdog_...ps1:335-339`, 꺼져 있으면 `$null`
로 지운다). 러너 인자로 넘겨야 한다. env 로만 세웠다가 `RUN_MODE=CONTINUOUS_STATIC` 으로
돌아 state 가 1개만 나왔다.

**2. 무제어 기본은 CONTINUOUS_STATIC 이라 state 가 2개뿐이다.** 롤아웃 검증에는
150초마다 스냅샷이 필요하다. `UseContinuousStaticMode = (Not ForceStepwiseMode()) And
(c = "no-control" ...)` 를 뒤집는 것이 `-ForceStepwise` 다.

**3. 무제어는 진짜 네이티브다.** 되읽기(`signal_readback.csv`)에 도시신호가 **0종**이고
램프미터 8개(9101~9108)만 COM 제어된다. 도시 17개 신호는 `.inpx` 신호 프로그램이 그대로
돈다. 제어런은 25종·도시 17종이 잡힌다 — 이걸로 두 런을 구별할 수 있다.

## 롤아웃에 먹일 제어

무제어 런의 action JSON 은 **균등 34.5초**를 쓴다. 그건 VISSIM 이 실제로 돌린 것과 다르다.
네이티브 분할은 `outputs/signal_group_actuation_plan_v3.json` 의 `axis_green_sec` 이고,
신호별로 모델 녹색총량(138)에 **비례배분**해서 쓴다. SC5(246초)·SC7(205초)처럼 동시현시로
합성 주기가 늘어난 신호도 비율만 보존한다([[vissim-nativefixed-cycle-inflation]]).

## 지표는 규칙 불변으로

투영 규칙(큐/저류 분할)을 바꾸면 성분별 오차는 비교가 안 된다. **origin 단위 총량**
(저류점유 + 그 origin 에서 출발하는 movement 큐 합) 대 150초 뒤 VISSIM 실측 링크 대수 합으로
잰다. 분할이 어떻든 합은 같으므로 두 변형을 같은 자로 잰다.

하네스: `scratchpad/nc_rollout.py` (층화) · `speed_oracle.py` · `discharge.py` · `out_drain.py`

관련: [[vissim-plant-rollout-diverges]] [[vissim-parent-run-launch-traps]]
