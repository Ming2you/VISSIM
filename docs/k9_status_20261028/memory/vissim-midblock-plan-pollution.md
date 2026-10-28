---
name: vissim-midblock-plan-pollution
description: 액추에이션 계획이 미드블록 SG를 모델 현시에 넣어 본선 배달을 0.44배로 깎았다. narrowaxis·subwin 이 같은 오염을 잘못된 끝에서 건드린 것
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-25T03:06:48.769Z
---

`outputs/signal_group_actuation_plan_v3.json` 의 `phase_signal_groups` 가 미드블록 SG 를
모델 현시에 함께 넣는다 — SC5 p1 = `["4","8","12","16","20","24"]`.

```
axis_green_sec[p1] = 97      (SG20 의 native 창 [50,147])
본선 SG4·SG8 native  [78,121] = 43초
계획이 그 창을 43/97 = 0.4433 분율로 적는다
→ 컨트롤러가 p1 에 54.5초 주문 → 본선에 24.2초만 배달 (1초 되읽기 12주기 실측)
```

**본선만 보면 억지로 맞출 게 없다** — SC5 `p1{4,8}=43 · p2{3,7}=23 · p3{2,6}=47 · p4{1,5}=25`
합 **138 = 모델 예산**, +4×3s 황색 = 150 = 주기.

**"상충" 은 안전 제약이 아니다.** `signal_group_plan.py:222-228` 이 *native 에서 한 번도
안 겹치면 상충* 으로 **추론**한다. 기하도 intergreen 행렬도 아니다. SC5 는 SG 24개로
본선 + 미드블록 노드 둘을 몰고, 둘은 **다른 교차로**라 동시녹색이 나도 무방하다
(2026-08-25 사용자 판정).

**Why:** 러너는 이미 `RW_MAINLINE_SG_ONLY=1` 로 `sg<=8` 만 COM 으로 몰고 미드블록엔
ContrByCOM 조차 안 건다(VBS:1820-1833). 러너 주석이 앞 절반을 적어 뒀다 — *"미드블록은
제어 대상이 아닌데 지금까지 컨트롤러가 함께 눌러 왔다. SC5 SG10 EBT 101s → 22s (21%)"*.
**계획에서 빼는 나머지 절반이 안 돼 있었다.**

이것이 [[vissim-flat-local-cost-vertex]] 와 별개로 **실행채널 +201** 의 유력한 몫이고,
`narrowaxis`(+53)·`subwin`(+25.8)이 실패한 이유다 — 둘 다 이 감쇠를 **모델에 새겨 넣거나
share 를 좁히려** 했지 플랜트를 고치지 않았다. 실제로 모델은 이미 share=1.0(전 movement)로
현시 전체 배달을 가정하고 있었고 어긋난 쪽은 플랜트다.

**How to apply:** 생성기 사본 `scripts/derive_signal_group_actuation_plan_mainline_20260825.py`
가 `phase_signal_groups` 를 SG 1–8 로 거른다. 미드블록은 `signal_group_ids`(EXPECTED 계약)에
남으므로 커버리지 검증은 통과하고, 상충의 `active` 필터가 `window_counts>0` 이라 미드블록
쌍은 자동으로 빠진다. 산출: `outputs/signal_group_actuation_plan_mainline_20260825.json`
+ 형제 `_sgplan.vbs` + 생성config 사본. 어댑터는 `RW_MAINLINE_PLAN=1`, 러너는 `-VbsConfig`.

검증: `status=PASS · uncovered=0 · 전 17 SC 부분창 0개`. SC5 axis 97→43, SC7 91→67.
리플레이 — 꺼짐 비트 동일 PASS / 켜짐 **녹색 변화 0**, 배달 창만 SC5 SG4 31.03→**70.00s**(2.26배).
순수 플랜트 변경이다.
