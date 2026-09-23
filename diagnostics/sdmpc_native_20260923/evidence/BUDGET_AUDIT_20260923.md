# SDMPC budget: 등식인가, 상한 부등식인가 (2026-09-23 감사)

요청: "SDMPC budget 이 equality 일 텐데 상한 inequality 로 바꿔 달라. 그게 성능이 더 좋은 것 같다."

## 결론

**지금 런의 모드(`central-pfo-cap-v3`)에서 NP·NUF budget 은 이미 상한 부등식이다.** 제약 형식은 바꿀 것이
없어서 코드를 수정하지 않았다. 등식처럼 보이는 이유는 제약 형식이 아니라 **cap 을 어디에 두느냐**에 있다:
매 구간 cap 을 PFO 가 달성한 값에 정확히 맞추고, cap 탐색은 꺼져 있다.

감사는 워크플로 9개 에이전트로 했다(감사 4 + 반대 검증 4 + 종합 1). 핵심 지점은 직접 다시 읽어 확인했다.
결정 기록에 남은 source sha256 이 현재 소스와 같으므로, 읽은 코드가 실제로 돈 코드다.

## 1. 부등식으로 처리되는 곳 (라이브 경로)

`central-pfo-cap-v3` 는 `budget_caps=True`, `central_multiplier=True` 를 켠다 (`sdmpc.py:83-90`, `:481-482`).

| 단계 | 위치 | 형태 |
|---|---|---|
| QP 행 | `sdmpc.py:725-728` → `sdmpc_central.py:31-33` | `lo=-inf`, `hi=eps-c`. `solve_qp` 는 `glo==ghi` 인 행만 등식으로 넣는다(`sdmpc.py:435`) |
| 반복 듀얼 / 가격 | `sdmpc_central.py:9-10, 27-28` | 듀얼 2개, `max(0,·)` 사영. NUF 하한 가격 없음 |
| 이월 가격 검사 | `sdmpc.py:466-469` | cap 모드에서 음수 NUF 가격 거부 |
| 중앙 승수 복원 | `sdmpc_central.py:40-44, 63, 76` | `budget/NP/upper`, `budget/NUF/upper` 두 행만. NNLS 라 승수 ≥ 0 |
| trial 게이트 | `sdmpc.py:546-559` → `area_leader_objective.py:798-801` | `max(0, actual−cap) ≤ 1e-7` |
| 최종 게이트 | `area_follower_objective.py:1461-1469` | 두 budget 모두 cap 모드 |

config 의 `nuf_tolerance_veh_h: 40` 은 cap 모드에서 `parameters.json` 의 1e-7 로 덮어쓴다(`sdmpc.py:483-484`).
900 s native 결정과 1050 s 재현의 모든 trial·final 행이 `mode='cap'`, 허용오차 1e-7, 듀얼 길이 2 다.

## 2. 결정 경로에 남은 "등식"

| 위치 | 성격 | 판단 |
|---|---|---|
| `sdmpc_tangent_worker.py:255-258` `nuf_mode='equality'`, 허용오차 0 | 측정용 호출. `:270` 에서 actual 값만 쓰고 판정은 버림 | 이름만 등식. **바꾸지 않았다**: 테이프 위에서 `max(0,·)` 는 시작점(잔차 정확히 0)에서 exact tie 를 새로 기록할 수 있어, 표기만 바꾸려다 도함수 처리가 달라질 위험이 있다 |
| 신호별 Σ녹색 = 주기 − 손실시간 (`sdmpc.py:300-301`, `:396-398`) | NP/NUF 가 아닌 유일한 실제 등식. 고정 주기 plant 에 물리적으로 필요 | budget 과 무관 |
| `wu_faithful_nuf_coordination_mode=='equality'` (`vissim_stackelberg_adapter.py:12382-12385`, `area_follower_objective.py:1134-1137`) | 라벨. 결정을 제약하지 않음 | **'cap' 으로 바꾸면 예외 발생. 건드리지 말 것** |
| NP = owner 17개 합, NUF = 램프 8개 합 (`area_leader_objective.py:785, 791`), 미래 블록 cap 복사 (`sdmpc_sequence.py:42-43`), Omega 분할 합 = TTT (`sdmpc.py:272-275`) | 회계 항등식 | 바꿀 의미 없음 |
| 복원 시드 선택 (`sdmpc.py:812`) | 양측 노름 휴리스틱. 900·1050 에서 발동 안 함 | **바꾸지 않았다**: 복원 QP 는 이미 단측이고 시드만 양측이다. 단측(`max(0,·)`)으로 바꾸면 cap 위반 0 인 trial 이 뽑히는데, 그 trial 이 막힌 이유는 budget 이 아니므로 복원이 고칠 수 없다. 경계 가까운 시드가 오히려 복원 목적에 맞다 |

라이브가 아닌 진짜 등식은 옛 모드에만 있다. proxlinear-v1 은 NUF 행 `lo==hi`(`sdmpc.py:730`)에 가격 부호가
자유롭고, central-reuse-v2 는 ±40 veh/h NUF 밴드(`sdmpc_central.py:11, 17, 24, 33, 44, 86`)다.

## 3. 왜 등식처럼 보이나

- **cap = PFO 달성치.** `sdmpc_budget.py:25` 에서 cap 을 PFO 가 달성한 NP·NUF 로 잡는다(`budget_policy='upper_caps'`).
  SDMPC 시작점의 잔차가 0 이라 두 cap 모두 처음부터 걸려 있다.
- **cap 이 움직이지 않는다.** `max_leader_candidates=1` 이라 `next_budget`(`sdmpc.py:860-866`)에 도달하지 않는다.
  실효 가능집합은 {NP ≤ NP_PFO, NUF ≤ NUF_PFO}. 아래로는 가지만 위로는 못 간다.
- **900 s**: 플레이어 제안은 +26.0 veh / +24.0 veh/h 를 원했지만 투영 후 +0.0003 / −0.0013 (두 행 결속).
  NUF cap 을 0.10 veh/h 넘은 ¼ 스텝 trial 하나가 기각됐는데, 목적함수(394.818)가 채택 스텝(394.401)보다 나빠 비용 0.
- **최종점은 두 결정 모두 두 cap 에서 여유가 있다.**

  | 결정 | NP 최종 / cap (veh) | NUF 최종 / cap (veh/h) |
  |---|---|---|
  | 900 s | 556.62 / 564.11 (−7.49) | 5213.65 / 5216.79 (−3.15) |
  | 1050 s | 488.55 / 513.16 (−24.61) | 4906.91 / 4911.16 (−4.25) |

- **가격은 이월된다.** 반복 듀얼: 900 s [0,0] → [0.260, 0.024] → [2.387, 0.141], 1050 s → [1.805, 0.142] →
  [1.229, 0.122]. 이 가격이 다음 구간 모든 owner QP 기울기에 들어가서(`sdmpc.py:498-505`, `:758`), 새 cap 이 여유가
  있어도 NP·NUF 증가에 벌점을 준다. 반복 2회로는 0 까지 못 내려간다. (1050 s NP 제안 −58 veh 중 약 6 veh 가 이 이월
  때문이라는 추정은 **대략치, 미확인**.)
- 중앙 NNLS budget 승수는 두 결정 모두 0 이다. stationarity 가 8.18 / 3.47 로 허용 1e-3 를 한참 넘는데도
  `accepted_for_leader_direction=True` 다(`sdmpc_central.py:89` 는 stationarity 를 안 본다. 다만
  `optimality_certified=False` 로 근사임은 표시된다). `max_leader_candidates=1` 이라 지금은 결정에 영향 없음.

## 4. "부등식이 더 좋다"의 근거

- 흔히 인용되는 +2.436 veh·h (`SQUEEZE_FINAL_20260923.md`)는 v2 396.352 − v3 393.916. 같은 900 s 상태, **오프라인
  결정 1회**, 예측 목적함수 비교다. 세 요인이 섞여 있다:
  - PFO warm start: 이것만으로 395.535, v2 보다 0.817 좋다.
  - cap 수준: v2 NUF 밴드 상한 5184.16 vs v3 cap 5216.79 (32.6 veh/h 높음).
  - 밴드 대 cap 의미 차이: v2 밴드는 한 번도 활성화되지 않았다(듀얼 3개 0). **기여 0.**
- 하드 등식(v1) 대 밴드(v2): 396.475 대 396.352, 차이 0.123.
- cap 완화 시험(mlc3, 오프라인 1회): NUF +1000 은 394.317 로 **0.401 악화**, NUF −1000 은 QP 실패. NP 는 미시험.
- 등식→부등식 효과만 분리한 증거, native 폐루프 비교는 찾지 못했다(전수 검색은 아님).

즉 부등식이 주는 이득은 v3 에 이미 들어 있고, v3 이득의 대부분은 제약 형식이 아니라 PFO warm start 에서 왔다.

## 5. 더 풀어 주고 싶다면: 형식이 아니라 이 레버 (전부 결정을 바꾸는 변경, 미구현)

| 레버 | 위치 | 효과 | 증거/위험 |
|---|---|---|---|
| (a) cap = PFO 달성치 + 여유 | `sdmpc_budget.py:25` | 시작점이 경계에서 떨어져 위쪽 이동 허용 | NUF +1000 은 0.401 악화(오프라인 1회). 여유 크기 탐색 필요 |
| (b) 이월 가격 리셋/감쇠 | `sdmpc.py:498-505` | 여유 있는 새 cap 에 대한 벌점 제거 | 09-22 합의("가격은 적용 receipt 로만 이어받는다") 번복. 폐루프 짝지은 비교 필요 |
| (c) `max_leader_candidates>1` | config | `next_budget` 탐색 활성 | 중앙 승수 0 + stationarity 미달이라 고정 탐침만 돎. mlc3 는 653 s 더 쓰고 이득 0 |

어느 것이든 같은 900 s 상태로 짝지은 오프라인 비교를 먼저 하고, 라이브 런(`D:\VISSIM-merge\sim3` 를 매 결정 다시
읽음)과 분리된 트리에서 해야 한다.
