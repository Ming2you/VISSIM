---
name: vissim-offset-rejected-not-dead
description: offset 은 죽은 레버가 아니다 — 35.7% 슬롯에서 0 아닌 값을 고르고 관문 둘에서 전량 거부된다
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-25T06:45:27.846Z
---

**"컨트롤러가 561개 전부 0 을 의도한다" 는 틀렸다.** 2026-08-25 에 산출물을 다시 재서
정정한다. 컨트롤러는 0 아닌 offset 을 고르고, **커밋 직전에 전량 되돌려진다.**

```
                탐색에서 0 아닌 값 선택      최종 유지    결정당 평가
mainline_20260825   200 / 561  (35.7%)          0        187.3
allfix_20260825     192 / 561  (34.2%)          0        196.7
sc7native_20260824  210 / 561  (37.4%)          0        193.5
커밋된 offsets 의 서로 다른 값: {0.0}
```

진단 카운터 둘을 **갈라 봐야** 보인다 — `wu_faithful_offsets_searched_off_zero`(탐색)와
`wu_faithful_offsets_off_zero`(유지). 둘이 갈리면 "레버 없음" 이 아니라 **가드 기각**이다.

## 관문이 둘이고 둘 다 닫혀 있다

**관문 1 — 유지 마진.** `wu_faithful_follower.py:424` 의 `offset_keep_margin = 0.005` 가
하드코딩. 저장소 전체에서 config·어댑터가 쓰는 곳 **0곳**(테스트 3곳만 −1.0 우회).
판정 `:4632` — `ttt_off <= ttt_on × 1.005` 면 0 으로 되돌림.

```
실측 모델 안 이득 (ttt_off−ttt_on)/ttt_off
   평균 0.036%  최대 0.0966%  최소 −0.041%   대   요구 0.5%
   최대이득/요구 = 0.193  →  33/33 전량 기각
```

**관문 2 — 승격 잠금.** 37결정 전부 `offset_writer=intent_only` ·
`offset_promotion_status=NOT_EVALUATED`. `offset_promotion.py:339` 가 production/test_only
가 아니면 **무조건 0.0** 을 쓴다. 삼중 잠금의 증거 산출물 셋
(`outputs/offset_promotion_{d_core,n9_offset_effect,n8_4_runtime}.json`)은 **하나도 없다**.
그리고 `production` 은 config 로 **선언 불가**다(`:278-283` 명시 거부).

**How to apply:** **관문 하나만 열면 플랜트 TTT 가 비트 동일**이다 — 마진만 풀면
`offset_intent_suppressed_signals` 숫자만 바뀐다. 둘을 같이 열어야 한다.
팔: `..._offarm_20260825`(어댑터 사본 + config). 마진은 `nash_solver` 의 **인스턴스 속성**
이라 피클되어 가격 워커 spawn 을 넘는다. 최적화기 offset 은 `test_only` + 강제표로 싣는데,
**그 모듈이 test_only 를 "harness 가 지정한 값" 으로 못박아 둔 계약을 늘리는 것**이다 —
실험 팔 한정이고 production 승격 경로는 안 건드린다.

**Why:** 이 때문에 **지금까지의 연동 A/B 결론이 전부 무효 대조군**이다. 커밋된 offset 이
항상 0 이었으므로 "연동을 켰는데 차이가 없었다" 는 자료는 offset 을 시험한 적이 없다.
[[vissim-why-control-loses]] 의 "offset 0 잠금" 도 원인을 잘못 짚었다 — 잠긴 게 아니라
거부되고 있었다. `guard_forced_arm` 의 docstring 이 정확히 이 위험을 미리 적어 뒀다.
