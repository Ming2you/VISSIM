# FD·MFD와 탐색 범위의 연결

2026-09-11. 사용자 선택은 **고속도로 80%·도시 50%·seed 13·9000초 무제어**다. 아래 범위는 이 결과에서 다음 비교의 출발점을 정하기 위한 관측 범위다. FD/MFD 보정값이나 최적 운전점으로 확정하지 않았고 설정도 활성화하지 않았다.

## 도시 MFD: 범위와 단위

원자료는 `reports/20260911_cooldown_80_90/fw080/urban_mfd_points.csv`의 150초 집계다. `n`은 평균 재고 [vehicle], `P`는 주행 생산량 [vehicle·km/h]이며 TTD가 아니다. 각 범위에서 관측된 최대 P의 90% 이상인 12개 구간을 단순한 높은 생산량 관측대로 표시했다.

| 범위 | 높은 생산량을 관측한 n 범위 [대] | 관측 최대 P [대·km/h] | 최대 구간 [초] | 다음 검토의 둥근 시작 범위 [대] |
|---|---:|---:|---|---:|
| PN core: 정지선 기준 도시 protected network | 569.72–742.67 | 18,073.44 | 2550–2700 | 570–745 |
| Ω urban: IC 접근·연결도로 포함 도시부 | 761.08–1024.34 | 22,596.96 | 2700–2850 | 760–1025 |

PN core는 581개 링크 목록, Ω urban은 611개이며 두 범위 모두 고속도로·램프 자체를 제외한다. 329는 양쪽에 포함되고 127·71은 Ω urban에만 포함된다. 범위가 다른 재고를 같은 MFD나 목표값에 섞지 않는다. 위 범위는 최대 P 부근의 관측 재고를 되짚어 보는 초기 후보대이며, 그 안에 재고를 유지하면 성능이 좋아진다는 인과 증거는 아니다.

수요가 감소한 뒤 5400–7200초 PN core n=471.74–531.62에서 P=10,551.8–12,890.3, Ω urban n=642.22–748.70에서 P=13,441.6–15,875.0이었다. 같은 재고에서도 공간 분포·신호·도착 이력에 따라 생산량이 다르므로 단일 꼭짓점만으로 목표를 정하지 않는다. 329의 자연 삭제로 감소한 재고도 포함된 관측이므로 MFD 생산량만으로 정상 회복을 판정할 수 없다.

## NP, NUF는 재고 목표와 다른 양

현재 `shared_urban_quantities()`가 만드는 NP 서비스는 제어 urban owner들의 **450초 누적** `(boundary_in + off_ramp − boundary_out − on_ramp)` [대]다. 비owner 신호 서비스는 별도이며 owner NP에 합산되지 않는다. 따라서 NP=−250은 stock=−250도, 총 TTD 250도 아니다. NP 후보를 위 MFD 재고 570–745에 직접 대입하지 않는다. `n_target − n_now`를 초기 설명값으로 삼더라도 동일한 물리 범위, 내부 생성·비owner 경계와 저장량 수지, 실제 450초 도달 가능 서비스부터 확인해야 한다.

NUF는 최종 미터 명령률 합 [대/h]이다. 450초 동안 명령률×0.125시간은 가용 서비스 예산일 뿐 실제 램프 방출량이 아니다. 차량 도착, 대기 재고, 신호 양자화, 본선 receiving 공급에 따라 실제 방출이 작아진다. 명령률·실행률·정상 경계 방출을 따로 비교한다.

현행 `prepare_joint_leader_candidates()`는 설치된 `_omega_f` 방향 비중을 그대로 강제한다. 동서 50/50이면 양방향 미터 예산이 반드시 같고, 합계 NUF를 낮추면 두 방향을 함께 제한한다. 80–50에서 동측 정체가 훨씬 컸다는 사실만으로 전체 NUF 조절이 적절한 방향 배분이 되지는 않는다. `meter_bank`의 도달 가능한 비대칭 명령조합 중 고정 비중과 다른 것은 현재 필터에서 탈락한다. 방향별 예산을 독립적으로 비교할지 여부는 별도 전략공간 변경이므로 이번 속도 개선에 몰래 포함하지 않았다.

## 동서 two-branch FD 선택 훅

기존 `freeway.two_branch` 안에 선택적 `rho_crit_two_branch_by_direction` 매핑을 추가했다. 키는 정확히 `FW_E`, `FW_W`이고 각 값은 유한한 숫자로 0보다 크며 해당 방향의 모든 셀 jam density보다 작아야 한다. 활성화 시 셀의 기존 자유속도·jam density와 해당 방향의 kc를 사용한다. 매핑이 없으면 기존 global kc가 그대로 쓰이고 기능 OFF에서는 매핑이 물리에 영향을 주지 않는다. scalar 소비자에는 방향이 없으므로 기존 global kc가 계속 필요하다.

구현은 `freeway_fd.cell_parameters()`와 기존 adapter의 `install_freeway_two_branch_fd()`에만 넣었다. 서로 다른 12/18 값은 단위 테스트용 합성 수치일 뿐 실험 추천값이 아니다. 방향별 훅에 관한 source/config 테스트 6개가 통과했고, 현재 선택 설정에는 two_branch를 활성화하지 않았다.

이 모델의 `w = v_free × kc / (kj − kc)`, `kc(VSL) = w × kj / (VSL + w)` 관계는 낮은 VSL로 자동으로 capacity가 늘어난다는 모델이 아니다. 고정 w·kj에서 VSL을 낮추면 이 삼각형의 최대 유량은 감소한다. 관측된 낮은 유량·높은 밀도가 하류 분기 막힘과 spillback 때문일 때 kc나 w로 모두 흡수하면 receiving 제약을 이중으로 보정하게 된다. 80/90 무제어 자료는 VSL의 인과적 capacity 효과를 식별하지 않는다. 동서 FD를 분리해도 off-ramp 수용량, 하류 receiving, lane drop은 유지해야 한다.

## 기존 SPSA와 작은 비교 실험

기존 SPSA는 vendor의 `StackelbergWuMetered._spsa_global_price_gradients()`에 있으며 canonical joint 경로의 drop-in 대체가 아니다. 현재 source audit에서 확인한 차이는 다음과 같다.

- `green`은 scalar primary phase 변경 후 나머지 녹색 재배분이다. 현재 모든 live phase의 고정합 공간을 직접 섭동하지 않는다.
- offset은 global cycle을 사용한다. SC별 실제 시계와 원형 거리를 증명하지 않는다.
- meter·VSL은 연속 수치 양끝을 사용한다. 최종 미터 양자화·VSL zone 명령 및 이전 실제 명령 상자와 같은 섭동이라는 확인이 없다. 상한에서는 대칭 섭동도 아니다.
- 동시에 모든 lever를 바꾼 두 rollout의 **global objective만** 차분한다. 현재의 동일 response에서 J와 owner local C를 구해 외부효과를 만드는 계약과 다르다. 추가 all-meter-high probe도 개별 meter 효과의 증명이 아니다.

작은 비교는 기존 `make_decision_shared_query()`를 그대로 받아 수행할 수 있다. root가 보존한 동일 state·forecast·물리 기준 action·source fingerprint에서 `evaluate_joint_prices()`의 현행 유효 방향 차분을 기준으로 삼는다. 새로운 샘플도 `callbacks['neighbors']`, `command_evidence`, 실제 주소·소유권 검증을 통과한 명령만 query에 보낸다. 모든 응답에서 동일 J와 owner local C를 읽고 같은 외부효과를 계산한다.

1차 비교는 seed를 미리 고정한 4쌍(8개의 새로운 whole-action 응답)으로 제한하고, 기준점 응답과 검증용 현행 방향 6개를 공유한다. 각 lever 종류와 상한의 one-sided meter를 포함한다. 대칭점이 없는 좌표는 SPSA라고 거짓 표시하지 않고 비대칭 설계행렬·실제 변위를 기록하거나 기존 유효 방향 차분으로 남긴다. 8개 응답으로 전체 약73차원의 결정론적 full-rank 가격을 식별했다고 주장하지 않는다. 부호, 상대 크기, 예측한 후보 순위와 실제 공유 응답의 순위, native 명령 변화, endpoint 수·wall time을 함께 비교한다. 오차가 큰 경우에만 예산을 늘린다. 현행 full-rank 인증은 이 실험이 통과했다고 자동 유지되는 것이 아니다.

아직 이 SPSA 비교나 새 FD 모델 런을 실행하지 않았다. 우선 해결할 문제는 `NATIVE_ANCHOR_AUDIT.md`의 native 실제 신호가 현재 명목 action과 다른 기준점 문제다. 실제 기준점이 확보되기 전 추정기 속도만 비교해서 물리적 가격 정확성을 결론내리지 않는다.
