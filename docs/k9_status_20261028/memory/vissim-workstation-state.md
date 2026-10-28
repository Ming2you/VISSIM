---
name: vissim-workstation-state
description: "plant-fidelity-v2-1 현황(2026-08-20) — wu-link 팔 가격 병렬화 2.71배 검증 완료, 유효 기준선 TTT 176.144/해시 0ef928fe, 다음은 현시가격 OFF 대조군"
metadata:
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-20T10:59:01.472Z
---

2026-08-20 기준 `C:\Users\TRLAB\Desktop\찐찐막\VISSIM`, 브랜치 `codex/plant-fidelity-v2-1`
(origin 대비 **ahead 10, 미푸시**).

**현재 팔**: `--controller wu-link` = `PricedWuLinkStackelbergController`
(가격 리더 + Wu 충실 팔로워 + 링크 단위 freeway player 2개 + 현시별 교환 가격).
설정 `evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_phaseprice_20260820.json`.

**유효 기준선 (이 값과 다르면 뭔가 바뀐 것)**
- `phaseprice3_20260820`(완전 직렬) == `phasepar2_20260820`(4채널 병렬) — **비트 동일**.
  제어창[600,900] TTT **176.144 veh·h**, 궤적해시 **0ef928fe**, 커밋 제어 전 결정 동일.
- `phasepar_20260820` 은 **무효**다(워커가 어댑터 패치를 잃은 채 돌았다). TTT 176.351,
  해시 1e80c699. 대조 자료로만 쓴다. 자세한 함정은 CLAUDE.md 참조.

**가격 병렬화 현황** — 채널 넷(green·offset·VSL·현시) 전부 병렬. 결정 wall 368 → 136초
(2.71배), 900초 런 961 → 680초. 프로파일 근거: 결정 시간의 **88%가 가격 갱신**,
리더 후보 탐색은 12%. 리더 후보를 병렬화하려던 건 오진이었다.

**진단 주의**: `wu_price_rollout_count` 는 병렬화 후 **과소 계상**된다(124 → 43).
워커에서 증가한 카운터가 부모로 안 돌아온다. 성능 판단에 쓰지 마라.

**런 발사 주의**: 워치독 스크립트에 `-OutDir` 를 안 넘기면 산출물이
`evaluation/runs/real_world_modi_watchdog/` 에 떨어진다(`evaluation/runs/<name>/` 아님).
`wu-link` 는 연속모드 조건에 안 걸려 STEPWISE 가 기본 — `-ForceStepwise` 불필요.

**다음**: 현시가격 **OFF 대조군** 1런(약 11분). 지금 데이터는 전부 ON 이라 그 250~366초
재배분이 TTT 를 개선하는지 판정할 수 없다. `g` 분포는 "작동한다" 만 보여준다 —
공통 오프셋 ≈ 0(설계대로 순수 교환가격), 퍼짐 중앙 0.0033~0.0059, 17개 신호 전부 이동.

관련: [[vissim-execution-gotcha]] [[vissim-parent-run-launch-traps]]
[[vissim-resolve-live-controller-first]] [[vissim-plant-fidelity-three-layers]]
