---
name: vissim-connector-delete-breaks-routes
description: "VISSIM에서 커넥터를 지우면 정적 경로가 미완성이 되어 시뮬이 아예 시작 안 되고, 엉뚱한 증상(램프 COM 실패)으로 나타난다"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-14T11:01:12.292Z
---

VISSIM에서 커넥터를 삭제하면 그 커넥터를 명시로 지나던 `vehicleRouteStatic`의
`linkSeq`에서 **그 항목만 빠지고 경로 자체는 남는다.** 링크 사이에 대체 커넥터가
있어도 VISSIM은 `Static Vehicle Route N-M is not complete` 오류로 **시뮬레이션을
시작하지 않는다.**

**Why:** 시뮬이 안 도니 `RunSingleStep`이 시계를 못 움직이고(before=0 after=0),
그 상태에서 모든 COM 속성 설정이 거부된다. 2026-08-14에 이게 램프미터 SC 8개의
`ContrByCOM` 실패 + 차량 캡처 실패로 나타나 3시간을 램프 쪽에서 헤맸다. 램프는
증상이지 원인이 아니었다.

**How to apply:**
1. 망 편집 후 **`network/**/<망이름>.err` 의 `Error` 줄을 먼저 봐라.** Warning은
   정상 망에도 많다. 정상 망과 비교해 **늘어난 Error만** 보면 된다.
2. 링크 연결성만 보고 "대체 경로가 있으니 안전"이라 판단하지 마라. 정적 경로가
   특정 커넥터를 명시로 지정한다.
3. 경로 완결성 검사는 `[결정.link] + linkSeq + [destLink]` 가 커넥터로 **정확히**
   이어지는지 보는 엄격 규칙으로 하되, 정상 망을 기준선으로 잡고 **델타만** 본다
   (엄격 규칙은 정상 망에서도 9건을 과검출한다).
4. 고칠 때는 끊긴 자리에 잇는 커넥터를 `linkSeq` 맨 앞에 넣는다.

관련: [[vissim-execution-gotcha]] · [[vissim-workstation-state]]
