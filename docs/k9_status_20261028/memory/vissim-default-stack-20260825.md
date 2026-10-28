---
name: vissim-default-stack-20260825
description: "새 default 스택은 default_20260825 (merge 대체). 정본 어댑터 승격 완료, 스위치는 config 키, 러너 기본 계획도 본선 전용"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-25T04:48:52.214Z
---

**2026-08-25 승격.** 종전 기준이던 `merge_20260824`(4838.7)를
`evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_default_20260825.json`
이 대신한다. 새 팔은 이것을 `extends` 한다.

실측 계보 (시드 13, 무제어 4808.1):
```
merge 4838.7 → sc7native 4829.4 → allfix 4783.9 (-24.2) → mainline 4723.9 (**-84.2**)
```
`default_20260825` = mainline + regret, 스위치를 전부 config 키로.

## 세 자리가 바뀌었다

| 자리 | 바뀐 것 | 검증 |
|---|---|---|
| 정본 어댑터 | 7542 → **8290행**. merge·native_signal·A·B·C1·본선계획·regret. 추가분 전부 기본 꺼짐 | 스위치 전무에서 레버 91개 **불일치 0** |
| 스위치 | env → **config 키**. `urban.queue.stopped_split` · `urban.plan.mainline_only` · `urban.plan.mainline_share`. env 는 폴백(tuning 이 이긴다) | config == env **불일치 0** |
| 러너 기본 | `-VbsConfig` 기본을 `..._mainline_20260825.vbs` 로 (형제 sgplan 이 본선 전용 계약) | 무제어는 signal 행을 안 써서 기준선 무영향 |

## 되돌리는 법

셋 다 git 추적. 옛 계획만 되돌리려면 러너에
`-VbsConfig ..._core17legs4b_20260819.vbs`. **그 한 줄이 −60.0** 이라 실수로 빠뜨리면
조용히 사라진다.

**Why:** env 는 `extends` 로 상속되지 않고 `run_provenance` 에도 안 남는다. 팔마다 러너
스크립트에 따로 세워야 했고 그것이 [[vissim-parent-run-launch-traps]] 의 `RW_ADAPTER_MODE`
누출 함정의 원인이다. 같은 이유로 러너가 이제 `RW_*` 전체를 provenance 에 남기고
`RW_ADAPTER_MODE` 가 켜져 있으면 경고한다.

**아직 못 하는 주장:** 전부 시드 13 하나다. −84.2 는 무제어 5시드 σ=50.7 을 넘는 첫
격차지만 짝지은 시드 검정(14~17) 전에는 논문에 인용할 수 없다. 그게 다음 1순위다.

관련: [[vissim-midblock-plan-pollution]] · [[vissim-price-local-term-drain]] ·
[[vissim-green-max-78-wall]] · [[vissim-queue-projection-fixed-fraction]]
