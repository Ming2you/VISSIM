---
name: vissim-uniform-beta-defect
description: movement 회전분율 beta 474개가 전부 1/n 기본값이었다. .knr 로 고치려다 실패(내생성) — 정본은 .inpx 정적 경로결정. 2026-08-24
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T01:54:28.062Z
---

2026-08-24. **모델의 `urban_movements[*].beta` 474개가 전부 균등 분배 기본값이었다.**
값 집합이 {0.5, 0.25, 0.167, 0.125, 0.1} = {1/2, 1/4, 1/6, 1/8, 1/10} 뿐이다.
실측 산출물이 저장소에 없었다.

**왜 치명적인가.** `beta` 는 관측 투영과 플랜트 라우팅에 **함께** 쓰인다
(`urban_queue_model.approach_routing` → `:1018 queue[m] += beta * arrived`).
하나가 큐 분포와 동역학을 동시에 왜곡한다.

## 정본은 `.inpx` 정적 경로결정이다 — `.knr` 을 쓰지 마라

```bash
python scripts/derive_routing_turn_beta.py   # -> outputs/movement_beta_routing_20260824.json
```

어댑터 tuning `urban.beta.measured: true` + `source: "routing"`(기본). 팔 `beta2_20260824`.

`vehicleRoutingDecisionStatic/relFlow` 는 VISSIM 이 차량을 배분할 때 쓰는 **입력**이라
신호 타이밍과 무관하고(외생), 정의가 모델 beta 와 같다.
결과: 접근로 94 · movement 345 · **미매칭 0.00%** · **beta 0 인 movement 0** ·
굶는 현시 0. 통제 17신호 접근로 87개 중 60개(69%).

### 유도 함정 셋 (전부 실제로 밟았다)

1. **`relFlow` 가 비어 있으면 1 이다**(0 아님 — CLAUDE.md 되돌리면 안 되는 규칙 4).
   결정 130개 중 52개가 전부 비었고 **18개가 섞였다.** 섞인 쪽에서 0 으로 읽으면
   그 경로만 조용히 사라진다.
2. **결정 링크의 권역을 접근로로 쓰면 13개가 틀린다.** 경로결정이 교차로가 아니라
   **상류 대기 구간**에 놓여 있다. 결정 24 '개포고교_NB' 는 권역이 (SC7, S_SC108)
   인데 목적지 집합 {SC1, SC12, SC5} 가 (SC11, S_SC7) 을 가리킨다(개포고교=SC11).
   **목적지 신호 집합으로 역추론**해야 하고, 그 판정은 권역과 독립이라 서로 검산이
   된다. 목적지가 하나뿐이면 정보 부족이라 권역으로 되돌린다.
3. **한 접근로에 결정이 여럿 붙는다**(15개). 덮어쓰지 말고 **더해라**. 그리고
   목적지가 출발 접근로 자신이면 교차로 회전이 아니라 **구간 연장**이라 버린다.

`linkSeq` 로 exit leg 를 잡으려는 시도는 실패한다(99.4% miss) — 결정이 상류에 있어
경로가 원 신호 권역을 곧장 벗어난다.

## `.knr` 판(폐기)이 왜 틀렸나 — 되풀이하지 마라

`scripts/derive_measured_turn_beta.py`(파일 상단에 폐기 표시).
**정의가 어긋난다.** `.knr` 은 교차로를 **통과 완료**한 차량 = 그 방향에 준 녹색의
**결과**다. 컨트롤러가 최적화하는 변수에서 그 입력을 역산하는 자기실현 루프.

- 미매칭 2,758/44,746 = **6.16%**("미매칭 0" 은 SC5 한 접근로 값을 전체로 착각한 것)
- 매칭 실패분을 "OUT" 한 덩어리로 모아 **균등 분할** → 없애려던 1/n 부활
  (SC11_N_SC5 의 to_W·to_E 가 똑같이 0.3336)
- 244개 중 **85개가 정확히 0**, internal 25개(우회전 17 · 직진 2).
  beta=0 → 도착 주입 영구 0 → 큐 항상 0 → 리더가 그 현시를 굶긴다.
  **[[vissim-ew-axis-observation-blind]] 와 같은 실패 모드다.**
- 실런 실증: `beta_20260824` 가 conv 대비 녹색 **하한 부착 6.7% → 9.1%**.
  sim 2640/5400 에서 중단.

**"접근로 합 = 1.0" 검산을 근거로 쓰지 마라.** 정규화의 항등식이라 중복 계상도
OUT 몰아넣기도 미매칭 쓰레기도 전부 통과한다. 진짜 검증은 **미매칭 대수**와
**0 이 된 movement 목록**이다.

## 가격 부호 규약 (여기서 재확인)

정련 목적함수는 `local + w x Σ p_i (g_i − ref_i)` 를 **최소화**한다 →
**음수 가격이 녹색을 더 원한다.** SC5 는 p1 −0.039 · p4 −0.019 가 받고 싶어하고
p3 **+0.046** 은 내놓으라는 뜻이다(동서직진이 SC6/SC101 로 밀어내는 외부효과).

관련: [[vissim-flat-local-cost-vertex]] [[vissim-measured-capacity-online]]
[[vissim-ew-axis-observation-blind]] [[vissim-player-territory-canonical]]
