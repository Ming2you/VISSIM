---
name: vissim-why-control-loses
description: "제어가 무제어를 못 이기는 구조적 이유 — offset 0 잠금 vs 협조된 기준선(1~149s), 리더 층 분해능 없음, 탐색이 field plan 근방 미진입. 2026-08-24 probe"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T07:22:29.327Z
---

2026-08-24 probe (conv/merge action JSON 33개 전수 + 러너 + `.sig` 정본 대조).
Fable 검증 워크플로가 별도로 돌았으니 그 결과와 함께 읽어라.

## ① 구조적: 액추에이터 4채널 중 3개가 죽어 있고, offset 이 핵심이다

- **offset 33/33 결정 전부 0.0.** 러너가 잠근다 — `RW_OFFSET_WRITER="intent_only"`
  (VBS:150), 0 아닌 offset 이 오면 `OffsetPromotionRejectReason()` 이 CSV **전량 거부**.
  권위는 `evaluation/controllers/offset_promotion.py` (삼중 잠금, 설정으로 못 연다).
  **offset 탐색은 결정마다 145~196회 계산하고 버린다**(`wu_faithful_offset_evals`).
- **무제어 기준선은 offset 1~149초로 협조된 실계획이다**
  (`signal_timeline_from_sig_20260823.json` `program_offset_sec`: SC7 1 · SC105 35 ·
  SC5 36 · SC11 95 · SC1 131 · SC16 149 …). SC7 은 native 주기 120초인데 150초로
  25% 강제 연장.
- 램프 미터링 132/132 건 커밋 rate > 수요(무구속) · VSL 전 결정 120 고정 ·
  N_P 배분 33/33 빈 dict.
- **TTT 분해가 정확히 lockstep 손실 모양이다**: conv +57.0 = 도시부 **+62.4** +
  고속부 −5.6 + 램프 +0.2. 정지차량 적분 +4.05%. 손실은 1800~3600s 에 집중.

즉 "협조 없는 스플릿"으로 "협조된 스플릿"을 상대한다.

## ② 가드는 이제 범인이 아니다 (CLAUDE.md 의 "7/7 기각"은 옛 사건)

base guard 기각 **0/33** (ttt_worse·terminal_severe·completed_severe 전부 0).
그 사건은 램프 상한 5000 시절이고 박스 [0,7200] 복원 후 발화 조건이 사라졌다.
rejected 9/33 은 wu-link 의 PFO incumbent tie-break 이고 두 안의 예측 rollout TTT 차가
최대 0.1(0.03%)이라 어느 쪽을 커밋해도 같다. **리더 후보 9개의 목적 스프레드가 전체의
0.15%** — 리더 층은 TTT 를 움직일 분해능이 없다. 팔 간 차이는 전부 팔로워/정련의 스플릿
차이였다. `stackelberg_enable_fallback:false` 팔(lead_20260820)은 실재하나 다른
컨트롤러/어댑터 세대(stackelberg, 20ee90bc)라 wu-link 대조로 못 쓴다.

## ③ 탐색이 field plan 근방에 들어간 적이 없다

전 팔의 커밋 스플릿이 `.sig` 정본에서 **L1 786~963초** — 균등분할의 거리(809.3)와
같거나 멀다. native 에 가깝다고 좋은 것도 아니다(순서 뒤집힘: nophaseprice 가 가장
가까운데 +7.25%). 최적화된 적 없는 분지가 통째로 남아 있다.

## 분리 실험 (probe 설계)

**제어 ON + 녹색 스플릿을 `.sig` 정본값으로 고정** (offset 0 · 주기 150 유지).
- 여전히 ~1% 지면 → 손실 = offset lockstep + SC7 주기 강제. 스플릿 최적화 무죄.
  다음 수 = offset 승격(삼중 잠금 열 증거 산출) 또는 SC7 주기 예외.
- 동률/승리면 → 손실 = 스플릿 선택. 그때 정련/가격을 더 판다.

관련: [[vissim-seed-variance]] [[vissim-flat-local-cost-vertex]]
[[vissim-movement-leg-crossproduct]] [[vissim-workstation-state]]

## 정정 (2026-08-25)

여기 적힌 **"offset 0 잠금"** 은 원인을 잘못 짚었다. 잠긴 게 아니라 **거부되고 있었다** —
컨트롤러는 35.7% 슬롯에서 0 아닌 offset 을 고르고 두 관문에서 전량 되돌려진다.
[[vissim-offset-rejected-not-dead]] 참조. 그러므로 이 메모의 "구조 핸디캡" 논거 중
offset 부분은 **재검토가 필요하다** — offset 을 실제로 실어 본 적이 없다.

그리고 "왜 제어가 못 이기나" 라는 이 메모의 전제 자체가 2026-08-25 에 깨졌다.
default_20260825 가 4723.9 로 무제어 4808.1 을 **−84.2** 이겼다
([[vissim-default-stack-20260825]]).
