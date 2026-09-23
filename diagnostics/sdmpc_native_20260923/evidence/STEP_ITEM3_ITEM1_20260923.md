# 인계 3번(다중 budget) · ①(계산시간) 결과

## 3번 — 버그 발견·수정 후 검증 완료

### 버그
evaluation/controllers/sdmpc_central.py:next_budget 이 `tuple(np.clip(...))` 을 돌려주어
원소가 numpy.float64 였다. 소비자 area_leader_objective._joint_number:187 이
`type(value) not in (int, float)` 로 검사하므로 **numpy 스칼라가 거부**된다.
값은 유한한데(isinstance float True, math.isfinite True) 타입에서 막히고, 오류 메시지는
"N_P target must be a finite number" 라 원인을 가린다.

경로: 1번 후보는 q['np']['actual'](파이썬 float) -> 통과.
      2번부터는 next_budget 산물 -> 매번 거부.
**즉 다중 budget 탐색은 한 번도 작동한 적이 없다.** max_leader_candidates=1 이 이를 가렸다.

수정: next_budget 이 `tuple(float(v) for v in trial)` 반환. SDMPC suite 111/111 통과.

### 검증 (max_leader_candidates=3, 같은 900초 저장상태)

| # | budget NUF | status | accepted_steps | objective | stationarity | gradient | 방향채택 |
|---|---:|---|---:|---:|---:|---|---|
| 1 | 5216.792 (중심) | iteration_limit | 2 | **393.9161** | 8.1845 | [-0.0, 0.0] | True |
| 2 | 4216.792 (-1000) | **linear_resource_qp_failed** | 0 | None | 3.7952 | [-0.0022, 0.0] | False |
| 3 | 6216.792 (+1000) | no_improving_step | 1 | 394.3169 | 8.4471 | [-0.0, 0.0] | True |

held_objective = 395.5349589669397 -> 최종 393.9161 (hold 대비 -1.619 veh·h)

네 요소 모두 확인:
- **방향**: 리더 경사가 정확히 [-0.0, 0.0] -> 좌표축 폴백 (0,-1) -> (0,+1) 순서대로
- **중복방지**: 세 후보 모두 상이
- **상한**: NP 가 전 후보에서 564.110 고정(limits 클립)
- **가격 기록**: central-multiplier 기록 3건 모두 저장

판정: 탐색 기구는 정상 작동하나 **쓸 신호가 없다.** 중심에서 경사 0, 조이면 QP 실패,
풀면 악화. 라그랑주 승수 크기에 비례한 이동은 여기서 문자 그대로 0 걸음이 된다.

주의: selection.price_state.price_update_signal.candidate_dual = [2.387, 0.141] 은
가격 갱신 신호이지 리더 방향 경사가 아니다. 혼동 금지.

### 부수 결함
sdmpc.py:743 의 emit('sdmpc_candidate_start') 가 evaluate() 와 feasible() **뒤**에 있어,
후보 평가 중 실패하면 그 후보가 로그에 아예 안 남는다. 수정 후보.

## ① — 544.5초의 실측 분해

98.60% 가 직렬 롤아웃 배치 5개. 롤아웃 하나 안에서:

| 구성 | 초 | 비중 |
|---|---:|---:|
| 테이프 전방 프리멀 tangent_sec | 100.54 | **83.3%** |
| 스폰/전송 잔여 | 17.46 | 14.4% |
| 역전파 reverse_sec | 2.65 | 2.2% |
| 상태검사 | 0.005 | ~0 |

테이프 14,064,354 노드 / 450,071,024 바이트 / 231축 / 22출력 / 450 모델초.
그중 **primal_comparisons 8,869,202** (노드의 63%).
비테이프 scalar 롤아웃 47.92초 vs 테이프 113.25초 -> **테이핑이 ~3.2배**.

배치: A(PFO 초기평가 113.30) B(PFO it0 시행 135.12) C(PFO it1 시행 120.90)
      D(SDMPC it0 119.61) E(SDMPC it1 scalar 47.97). 합 536.91 = 98.60%.
롤아웃 9회 중 **4회는 계산하고 버려짐**(unused_ad_predictions: 4).
동시성은 이미 거의 이상적(3슬롯 2.97배, 2슬롯 1.99배).

### 값 0 으로 확인된 제안 (재제안 금지)
- derivative_workers > 8: sdmpc.py:148-150,178 하드캡. 게다가 2.2% 항에만 쓰임
- serial 백엔드 해제: 0초, tests/test_real_run_stays_serial.py 가 직렬 강제
- 배치 슬롯 상한: 배치당 1,3,2,2,1 이라 상한 8 미접촉
- stationarity_tolerance / qp_iterations / qp_tolerance / restoration_iterations 완화:
  **전부 0.000초.** qp 는 76개 SLSQP 전부 성공 종료, restoration 루프는 미실행

### 실효 후보
| 방안 | 절감 | 결정변경 |
|---|---:|---|
| 워커 프리스폰/재사용 | ~139초 (25%) | 아니오(순수함수 유지 시) |
| line_search_steps 3->1 | -29.4초 | 이 상태선 아니오 |
| PFO 시행별 미분 플래그 | ~-27초 | 1e-8 이내 |
| PFO max_iterations 2->1 | -120.9초 | **예** (반복1 수락, omega 397.48->395.53) |
| 테이프 단축(블록 3->2) | 거의 선형 | **예**, sdmpc.py:492 가 차단 |

### 바닥
테이프 프리멀 100초 + 최소 직렬 2롤아웃 => 단독 113.25 + 47.92 = **161초**,
이미 150초 초과. **지평이나 모델을 바꾸지 않으면 150초 실시간 불가.**

단서: 544.5초 측정이 유휴 머신이었는지 미확인. 재측정 시 배치 B 의 +18% 중 일부가
경쟁 부하일 수 있음.
