---
name: vissim-measured-capacity-online
description: movement 용량을 직전 구간 실측 방류율로 온라인 갱신 — 5초 스캔 링크이탈 계수 + 플랜트 씨앗 + 감쇠 러닝맥스. 2026-08-22 구현·검증
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-22T10:26:54.080Z
---

2026-08-22 구현. `RW_QUEUE_WINDOW=1` + tuning `urban.capacity.measured: true`.

**문제.** 용량이 두 군데서 서로 다르고 둘 다 틀렸다 —
`phase_shape_local_cost` 는 `len(movements) x 1400`(SC1_p1 이 28,000 veh/h, SC1 전체
실측 통과는 2,640), 플랜트/GNE 는 `차로수 x 330`(실측 접근로 1,100~7,900 대비 과소).
리더가 녹색을 나눌 때 쓰는 게 **상대** 용량이라 그대로 배분 왜곡이 된다.

**측정.** 러너의 5초 스캔이 차량별 `(No, Link)` 를 이미 읽는다. 연속 두 스캔을 비교해
링크를 **떠난 대수**를 센다 — COM 왕복 0. 상태 JSON `link_departures_window`.
(점유 스캔만으로는 통과량을 못 구한다. 유입을 모르니 점유 차분으로도 안 나온다.)

    cap_obs[접근로] = 이탈대수 / (그 접근로가 받은 **모든 현시** 녹색초 합) x 3600

**회계 단위가 함정이다.** 이탈 계수는 **링크 단위**인데 용량 증거는 차로군(SG) 단위다.
한 링크에 차로군이 둘 붙는다(WBL+WBT). 처음엔 링크당 최대 녹색을 분모로 쓰고 차로군
값을 현시별로 각각 심어서, 같은 9대를 두 번 쓰고 접근로가 용량의 2배를 방류했다
(증상: `measured_capacity_observed_links` 가 60개 중 1개). **링크 하나 = 접근로 하나**로
통일하고 `_approach_topology` 헬퍼 한 곳에서 정의한다 — 좌·직·우는 같은 차로를
나눠 쓰므로 총량을 공유하고, 배분은 현시를 가로질러 `beta` 로 한다.

**수요제약을 어떻게 넘기나.** 한산한 구간의 `이탈/녹색` 은 용량이 아니라 수요다.
오프라인 분위수로 거르려다 실패했다(중앙값 차로환산 0.52, 상위3 0.86 — 1차로 미만).
대신 **감쇠 러닝맥스**: `cap_est = max(cap_obs, 0.98 x cap_est_prev)`. 증거가 나오면
즉시 오르고 없으면 천천히 잊는다. 어댑터는 결정마다 새 프로세스라 직전 추정치를
**직전 action JSON 의 metadata `sat_est_<link>`** 로 나른다.

**씨앗은 플랜트 현재값이다** (`seed: "plant"`, 기본). 기하값(차로수 x 1800)을 쓰면
실측보다 3~8배 커서 사실상 늘 이기고(60개 중 2개만 채택), "직전 실측을 쓴다"가 아니라
"1800/차로를 가정한다"가 되어 낙관적이다. 플랜트 값에서 출발하면 데이터가 지배한다.
실측(1500초 스모크): 채택 **2 → 11~18개**, sat_est 중앙 1,482 → **1,654 로 상승**
(기하 씨앗은 4,784 → 4,324 로 하강 — 가정을 잊는 것뿐이었다).
`seed: "geometric"` 으로 옛 거동 복원 가능.

**부수 산출** `scripts/derive_measured_saturation.py` — 무제어 `.knr` 에서 차로군 90개
포화유량. 지금은 접근로 토폴로지(링크→신호·현시) 공급용으로만 쓴다.

관련: [[vissim-flat-local-cost-vertex]] [[vissim-ew-axis-observation-blind]]
[[vissim-parent-run-launch-traps]]
