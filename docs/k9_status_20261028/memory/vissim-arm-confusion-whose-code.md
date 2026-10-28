---
name: vissim-arm-confusion-whose-code
description: vendor 컨트롤러 27개가 팔 구분 없이 남아 있어 grep 하면 다른 팔 코드를 우리 팔로 오독한다. scripts/whose_code.py 로 클래스 단위 LIVE/DEAD 를 먼저 받아라
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-31T05:18:51.991Z
---

`vendor/NumSim-mine/src/controllers/` 에 팔 셋(`stackelberg` · `pstack-flagship` · `wu-link`)의
코드가 **구분 없이 같이** 있다. grep 은 팔을 모르므로 히트 첫 줄을 읽고 "우리 팔 동작"이라고
설명하면 틀린다. 2026-08-31 에 이 실수를 한 세션에서 여러 번 반복해 사용자가 지적했다.

```bash
python scripts/whose_code.py <심볼> --controller wu-link
```

실제로 컨트롤러를 만들어 leader/follower 의 MRO 를 펴고, ast 로 각 grep 히트의 소속 클래스를
구해 **LIVE / DEAD** 를 붙인다. 모듈 수준 함수는 live 클래스 본문에서 호출되는지로 판정한다.

**Why:** `scripts/resolve_live_controller.py` 는 **파일 단위**라 이 자리를 못 막는다.
`distributed_coordinator.py` 는 어댑터가 몽키패치하려고 import 하므로 "미도달 7개"에 안 나오는데,
그 안의 `DistributedCoordinator` 클래스는 wu-link 가 인스턴스화하지 않는다 — **파일은 살아 있고
클래스는 죽어 있다.** 판정 단위가 클래스여야 한다.

2026-08-27 정본 통합(어댑터 19벌·config 139개 → 1벌·4개)으로도 안 풀린다. 그건 **우리 쪽 사본**을
정리한 것이고 vendor 27개는 앵커 `anchor_python_file_set` 121핀과 tests 가 물고 있어 지울 수 없다
(CLAUDE.md "컨트롤러를 지우지 마라"). `parameters.json` 으로도 안 된다 — `ramp_metering_weight` 는
vendor 클래스 `__init__` 에 박힌 상수이고 `blocked_to_urban` 은 값이 아니라 코드다.

**How to apply:** vendor 코드의 동작을 설명하기 전에 반드시 이 도구를 돌려라. 실측 사례 —

```
blocked_to_urban       LIVE 0 · DEAD 2   distributed_coordinator (stackelberg 팔 전용)
                       wu-link 은 계수 없는 FIFO 이월(blocked_q)을 쓴다. 0.5 계수가 없다.
ramp_metering_weight   LIVE 7            wu_faithful_follower · local_signal_plant
                       f1_wu_faithful_follower 히트는 dead (live 호출 없음)
```

같은 뿌리의 실수를 이 세션에서 두 번 더 했다 — 러너 VBS 의 `RW_ALLOWED_VSL_SPEEDS` 를 고쳤는데
실효값은 `evaluation/generated/*_config_*.vbs` 였고(VBS 주석: "THE GENERATED CONFIG IS
AUTHORITATIVE"), 램프 점유 출처를 config 의 `detector_mapping_json` 이라 **추론**했는데 실제로는
`state_json['ramp_counts']` 였다(매핑은 그게 전부 0 일 때만 타는 폴백). 공통점은 **코드를 안 읽고
구성을 추론한 것**이다. [[vissim-resolve-live-controller-first]] 와 같은 병이다.
