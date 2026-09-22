# Lane-drop 연결 확인 및 φ 단독 재보정 — 2026-09-22

**완료. off-ramp 재고 → 유효 차로 감소 → lane-drop 감속항의 연결은 이미 존재한다.** 누락된 연결을 추가한 작업이 아니다. 고정돼 있던 φ=3을 방향별로 다시 맞췄으며, 다른 계수·망·수요·기하·생산 설정은 유지했다. 이번 실험의 식별 범위는 φ 하나이고, 저장용량/γ/b까지 재보정했다고 해석하면 안 된다.

동측은 φ 완화가 소폭 개선되지만 서측은 실제 예측에서 악화한다. **φ=0 후보를 정본에 일괄 채택하지 않았다. RM/VSL 이득 보정 완료도 아니다.** 진행 중 native 제어 큐는 건드리지 않았고 큐 코드 해시는 전후 동일하다. 새 VISSIM 실행과 FZP 전수 재스캔은 없다.

## 포함된 두 가지 효과

1. 물리적 차로 감소: 현재 셀별 기하의 유효 차로 수 차이. 동측에는 약 4→3 구간이 있다.
2. 진출램프 spillback 근사: off-ramp **커넥터에 있는 차량 재고 n / 기하 저장용량 C**에 따라 해당 본선 셀의 유효 차로 수를 줄인다. 검지기 OccupRate 또는 대기 차량만의 비율이 아니다.

포화 전의 현행 관계는 다음과 같다.

\[
\lambda_{eff}=\lambda_{geometry}-\Delta\lambda_{max}
\left[1-\exp\left\{-\frac{1}{b}\left(\frac{n}{\gamma C}\right)^b\right\}\right].
\]

현재 enabled=true, Δλmax=1, γ=0.5, b=2. n=0이면 손실 0, n≥C이면 별도 포화 처리로 손실 1차로다. 반만 차면 약 0.393차로 감소한다. 이 프로필이 밀도·수용 계산에 반영되고, 이어지는 속도식에는 다음 추가 감속이 적용된다.

\[
\Delta v_i=-\phi\frac{T\,[\lambda_{eff,i}-\lambda_{eff,i+1}]_+\rho_i v_i^2}
 {L_i\lambda_{eff,i}\rho_{crit,i}}.
\]

따라서 **φ=0은 이 추가 감속만 끈다. off-ramp 재고에 의한 유효 차로 감소, 본선 밀도·수용 효과, 실제 진출량 보존은 그대로 남는다.** 반대로 일반적인 진출부 weaving을 모두 설명하는 항도 아니다.

연결 위치: `vendor/NumSim-mine/src/models/metanet.py::effective_lane_profile` → 정본 adapter의 `install_freeway_segment_runtime` 내 물리 기하 보정/컨텍스트 → 같은 adapter의 speed update hook. 실제 전이는 `area_freeway_accounting.py`에서 사용한다. vendor와 adapter는 수정하지 않았다. `chain_audit.json`에는 빈 램프, 저장비율 25/50/75/100%, 실측 2700.1초의 최종 프로필과 양의 차로 차이를 기록했다. 부동소수점 수준의 3.000…→3 차이는 진짜 차로 감소로 집계하지 않았다.

80–90 전체 관측 중 10643은 최대 53/106.33대(49.84%), 10481은 16/151.47대(10.56%)다. 전체 커넥터 평균 저장비율만으로 입구에 몰린 대기열·국소 차로 차단을 정확히 판별할 수는 없다.

## 보정과 별도 수요 검증

- 기존 `calibrate.py`와 `canonical_harness.py`를 그대로 사용했다. 새 plant/adapter 없음.
- NC100%, seed23의 9개 상태(900.1~8100.1초), 각 450초로 φ만 적합. 방향별 8개 후보, 총 144개 학습 rollout. 범위 [0,6]의 유한 패턴 탐색이며 전역 최적 주장 없음.
- 학습은 명시적으로 미래 외부 경계가 주어진 conditioned diagnostic. 주행 중 본선 상태를 미래 실측으로 리셋하지 않는다.
- φ 외 기존 여섯 계수는 방향별로 정확히 고정. 양쪽 모두 학습 선택값 φ=0. 학습 점수 W 1.40756→1.39679, E 4.21436→4.12454.
- frozen 상태에서 100/90/80/70 및 FW80·도시100/90을 두 경계 모드로 평가: 368개, invalid 0.
- 별도로 80–90에서 59번 초기화 × 2방향의 실제 과거 정보만 쓰는 150초 예측 118개. 마지막 창은 120초, 끝 관측 8970.1초. 첫 150초는 이력 확보 구간. 단일 9000초 open-loop 예측이 아니다.
- 모두 seed23이다. 이전에 본 수요 조건을 쓰므로 blind 검증이나 독립 seed 검증으로 부르지 않는다.

80–90 **history forecast** 비교:

|방향|지표|기존 φ=3|후보 φ=0|
|---|---|---:|---:|
|동측|150초 전체 속도 RMSE [km/h]|24.1319|23.7009|
|서측|150초 전체 속도 RMSE [km/h]|14.4977|14.5025|
|동측|450초 속도 RMSE [km/h]|26.1713|25.7689|
|서측|450초 속도 RMSE [km/h]|16.4442|16.4636|
|동측|450초 밀도 RMSE [veh/km/lane]|11.2433|11.1500|
|서측|450초 밀도 RMSE [veh/km/lane]|6.2680|6.2686|
|동측|450초 셀 총방출 유량 RMSE [veh/h]|1126.8046|1126.5003|
|서측|450초 셀 총방출 유량 RMSE [veh/h]|980.2076|980.2672|

[동측 비교 히트맵](FW_E_rolling150.png) · [서측 비교 히트맵](FW_W_rolling150.png)

동측 450초 속도오차는 다른 검토 수요에서도 약 0.17~0.42 km/h 줄었다. 서측은 모든 history 조건에서 조금 악화했다. 동측 80–90 진출량 RMSE 자체는 434.885→435.103 veh/h로 소폭 악화한다. 따라서 속도 점수 개선을 배수·제어이득 개선으로 대체하면 안 된다.

## 추가 감속과 점유 기반 차로 감소의 분리

80–90 history의 9개 상태에서 점유 기반 유효 차로 감소를 끈 경우도 추가 36회 비교했다. 계수는 더 보정하지 않았다.

|방향|φ|점유 차로 감소|450초 속도 RMSE|셀 총방출 RMSE|
|---|---:|---|---:|---:|
|동측|3|켜짐|26.1713|1126.8046|
|동측|3|꺼짐|26.0896|1126.8298|
|동측|0|켜짐|25.7689|1126.5003|
|동측|0|꺼짐|25.6707|1125.0697|
|서측|3|켜짐|16.4442|980.2076|
|서측|3|꺼짐|16.4651|980.2479|
|서측|0|켜짐|16.4636|980.2672|
|서측|0|꺼짐|16.4651|980.2479|

영향 크기가 작다. 현 경계·초기 상태·이미 맞춘 여섯 계수 아래에서의 조건부 결과다. 이를 근거로 실제 spillback이 없거나 spillback 모델이 불필요하다고 판정하지 않는다.

## 남은 한계와 판단

일반 `history_forecast`는 off-ramp 초기 재고를 예측 지평 동안 고정한다. 반면 conditioned fitting에는 미래 관측 재고가 들어간다. **off-ramp의 진입−배수에 따라 재고가 늘고 줄면서 차로를 막거나 회복시키는 자율 동역학이 이 비교의 표준 예측에는 연결돼 있지 않다.** 기존 harness의 선택적 저장·배수 모형과는 구분해야 한다.

따라서 다음 개선은 φ를 더 크게 주는 것보다, 현재 망에 맞는 진출 진입·신호 배수·저장 재고 변화가 맞는지 검증하는 쪽이다. 재고 평균이 국소 입구 차단을 얼마나 대표하는지도 같이 확인해야 한다. 기존 FD/속도 계수와 추가 감속이 같은 손실을 중복 흡수했을 가능성은 있지만 이번 φ 단독 실험만으로 확정할 수 없다.

이번 결정: 동측 φ 완화는 후보로 유지하고 서측 변경은 채택 보류. 정본 생산 계수는 그대로. 제어 런의 RM/VSL 변경에 대한 방출·대기·회복의 실제 차이를 확인하기 전에는 제어이득 보정 성공을 선언하지 않는다.

## 검증·재현

validation 368, rolling 118, 차로감소 ablation 36에서 보존·밀도 실패 0. 주요 비교 최대 보존 잔차 5.68e-14대. 기존 150초 baseline 2방향의 물리 상태가 이전 그림 자료와 정확히 일치한다. 입력·코드·설정 pin 및 학습 전후 freeze는 `fit/input_pins.json`, `fit/freeze.json`, `final_integrity.json` 참조. 전체 약 19.4MB, 원본 FZP 추가 없음.

```powershell
# 이미 실행 완료. 기존 fit을 덮어쓰지 말 것.
python -B -X utf8 diagnostics/lane_drop_20260922/review.py prepare
python -B -X utf8 diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/calibrate.py --protocol diagnostics/lane_drop_20260922/protocol.json --out diagnostics/lane_drop_20260922/fit --max-evaluations 18
python -B -X utf8 diagnostics/lane_drop_20260922/review.py report
```

`protocol.json`, `fit/search.jsonl`, `fit/parameters.json`, `fit/validation.json`, `validation_summary.json`, `occupancy_ablation.json`, `rolling150.json.gz`, `completion.json`에 전체 결과가 있다. 실행은 Idle 우선순위였다.
