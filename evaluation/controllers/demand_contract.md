# `state.demand` 계약 — VISSIM 러너(생산자) ↔ Stackelberg 어댑터(소비자)

- 문서 상태: `발효` (2026-08-11 실측 기준)
- 계약 대상: 러너가 매 결정마다 쓰는 `state_*.json` 의 `demand` 블록 세 필드
- 강제 검사: `tests/test_demand_contract.py`
  (`python -m unittest tests.test_demand_contract`, 저장소 루트에서)
- 실측 근거: `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`,
  `evaluation/real_world_modi_inventory/vehicle_input_roles.csv`,
  `evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json`
  — 봉인 런 `evaluation/runs/n1_final_20260807/.../run_manifest_v2_1.json` 이 지정한 조합

이 문서가 존재하는 이유. 러너는 세 필드에 **VISSIM 유입 지점당 평균**을 쓰고, 어댑터는
같은 값을 **모델 게이트/링크 각각의 값**으로 읽는다. 두 의미가 어디에도 적혀 있지 않아
도시부에서 3.66배가 났다. 배율을 고치는 것은 별건이고, 이 문서는 **의미를 못박고 어긋남을
검사로 드러내는 것**까지가 범위다.

---

## 1. 요약

| 필드 | 생산자가 넣는 것 | 소비자가 읽는 것 | 뿌리는 대상 | 개수 | 실측 총량 배율 |
|---|---|---|---|---:|---:|
| `urban_volume_vph` | 도시부 유입 **지점당 평균** [veh/h] | 게이트 **각각의** 도착률 | `boundary_in_links` (+`boundary_out_links` 는 채우기만) | 117 vs 32 | **3.6562** |
| `freeway_volume_vph` | 고속부 유입 **지점당 평균** [veh/h] | 본선 링크 **각각의** 유입률 | `freeway_links` | 2 vs 2 | 1.0000 |
| `ramp_volume_vph` | 실 러너는 **리터럴 0** | 램프 **각각의** 외생 도착률 | `ramps` | 4 vs — | 0 (외생 도착 없음) |

세 필드 모두 **스칼라 1개**다. 역할별 벡터도, 망 전체 총량도 아니다.
소비자는 그 스칼라를 자기 쪽 집합의 원소 수만큼 복제한다. 따라서
**총량이 맞으려면 생산자 쪽 지점 수 == 소비자 쪽 원소 수** 여야 한다.
이것이 이 계약의 유일한 불변식이다.

---

## 2. 생산자 — `scripts/run_real_world_stackelberg_controller.vbs`

### 2.1 값을 만드는 곳

`LoadInpxDemandSchedule` (vbs:2890-2963) 이 `.inpx` 의 `//vehicleInput` 을 전수 순회한다.

```vbs
' vbs:2935  분류 — 역할 문자열이 "freeway" 로 시작하거나 링크가 RW_FREEWAY_INPUT_LINKS(="26,74")
isFreeway = (Left(roleKey, 7) = "freeway" Or InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS))

' vbs:2937-2946  시간구간별 누적 (합과 개수를 같이 센다)
AddDemandScheduleValue urbanSumBySec, urbanNBySec, secKey, volume

' vbs:2949-2953  **지점당 평균**
demandUrbanBySec(key)   = urbanSumBySec(key)   / urbanNBySec(key)
demandFreewayBySec(key) = freewaySumBySec(key) / freewayNBySec(key)
```

스케줄이 비면 `ComputeOriginalDemandAverages` (vbs:2864-2888) 로 폴백하는데
그쪽도 `Volume(1)` 의 **지점당 평균**이다. 두 경로의 단위가 같다.

### 2.2 값을 쓰는 곳

```vbs
' vbs:2123
ts.WriteLine "  ""demand"": {""urban_volume_vph"": " & Num(demandUrbanNow) & _
  ", ""freeway_volume_vph"": " & Num(demandFreewayNow) & _
  ", ""ramp_volume_vph"": 0, ""demand_profile"": """ & demandForecastProfileName & """},"
```

- `demandUrbanNow` / `demandFreewayNow` 는 `DemandForecastAtSimSec` (vbs:2993-3004) 이
  현재 시각이 속한 구간의 평균을 꺼내 준다.
- `ramp_volume_vph` 는 **리터럴 0** 이다. VISSIM 램프 유입을 재지 않는다.
- `demand_profile` 은 `"real_world_inpx_time_profile"`(프로파일 미적용) 또는
  `"..._scaled"`. 어느 쪽도 어댑터의 프로파일 분기(`fw_eb_heavy`, `urban_west_heavy` 등)
  에 걸리지 않으므로, 실 런에서 게이트별 값은 **전부 동일**하다.
- 실 러너는 `urban_west_east_ratio` 를 쓰지 않는다(8seg 러너만 쓴다). 어댑터는 없으면 1.0.

봉인 런 로그가 이를 그대로 보여준다
(`evaluation/runs/n1_final_20260807/.../runlog.txt:24-25`).

```
DEMAND_FORECAST_SCHEDULE_LOADED intervals=6 profile=real_world_inpx_time_profile
DEMAND_FORECAST_CURRENT sim_sec=0 urban_vph=398.351250 freeway_vph=3080.000000
```

`398.35125 = 12,747.24 / 32` — 도시부 32개 지점의 평균이 맞다.

---

## 3. 소비자 — `evaluation/controllers/vissim_stackelberg_adapter.py`

`profiled_demand_rates` (adapter:2789-3005) 가 스칼라를 벡터로 편다.

```python
# adapter:2807-2818
urban_vph   = float(demand.get("urban_volume_vph", 60.0))
freeway_vph = float(demand.get("freeway_volume_vph", 1200.0))
ramp_vph    = float(demand.get("ramp_volume_vph", max(120.0, freeway_vph * 0.12)))

freeway_mainline = {str(link): freeway_vph for link in cfg.network.freeway_links}
urban_boundary = {
    str(link): urban_vph
    for link in list(cfg.network.boundary_in_links) + list(cfg.network.boundary_out_links)
}
ramp_arrival = {str(ramp): ramp_vph for ramp in cfg.network.ramps}
```

`demand_from_state` (adapter:3008-3029) 가 이 셋을 `DemandStep` 으로 묶어
`horizon_steps` 개 복제한다. 호출 지점은 `adapter:5479` 와 `harness/g6/g6_core.py:378`.

### 3.1 모델이 실제로 읽는 곳

`urban_boundary` 를 **외생 도착**으로 쓰는 코드는 전부 `kind == "boundary_in"` 인
movement 의 `origin` 키만 본다. 실측: 실 cfg 의 `boundary_in` movement 641개가 갖는
서로 다른 `origin` 은 117개이고, 이 집합은 `boundary_in_links` 와 **정확히 일치**한다.

| 소비 지점 | 키 |
|---|---|
| `models/urban_queue_model.py:137` (`movement_forecast_arrivals_veh`) | `spec["origin"]` |
| `models/urban_queue_model.py:1009` (게이트 실제 주입) | `net.boundary_in_links` 순회 |
| `controllers/distributed_coordinator.py:455, 3233` | `spec["origin"]` |
| `controllers/urban_follower.py:155` | `spec["origin"]` |
| `controllers/simplified_inflow_outflow_allocation.py:148` | `spec["origin"]` |
| `controllers/wu_faithful_follower.py:487, 596` / `wu_distributed.py:197, 230` | `spec["origin"]` |
| `controllers/leader.py:489` | `net.boundary_in_links` 순회 |
| `analysis/free_flow_reference.py:122` | `net.boundary_in_links` 순회 |

### 3.2 `boundary_out_links` 판정 — 외생 도착으로 **안 쓰인다**

어댑터 주석(adapter:2830-2833)의 주장은 코드로 확인된다. 위 표의 모든 경로가
`boundary_in` 만 본다. 실 cfg 에서 `boundary_in_links ∩ boundary_out_links = ∅` 이고
`boundary_in` movement 의 origin 중 `boundary_out_links` 에 든 것은 하나도 없다.

다만 **전 키를 합산하는 경로가 둘** 있다.

| 위치 | 성격 | 실 런에서 쓰이나 |
|---|---|---|
| `controllers/stackelberg_mpc.py:2237-2246` `_forecast_demand_metadata` | **진단 메타데이터만** (`leader_forecast_boundary_*`), 결정에 안 들어감 | 쓰인다 |
| `controllers/classical_hierarchical.py:408-411` `avg_boundary_demand` | 결정에 들어감 | **안 쓰인다** — 어댑터는 `StackelbergMPCController` / `StackelbergWuMeteredController` / `DistributedCoordinator` 만 만든다(adapter:5769, 5791, 5823) |

즉 `boundary_out` 값이 새는 곳은 진단 로그 한 군데다. 실측(t=1800 s):
모델이 실제로 주입하는 도시부 도착은 **69,909 veh/h** 인데 로그의 `boundary` 합은
**141,012 veh/h** — `(117+119)/117 = 2.0171`배 부풀어 있다. 이 진단값으로 수요를
읽으면 안 된다.

### 3.3 `ramp_volume_vph` 판정 — 실 런에서 램프 외생 도착은 **0**

러너가 0 을 쓰므로 어댑터의 기본값(`max(120, 0.12·freeway_vph)`)은 절대 발동하지 않는다.
`ramp_arrival` 를 0 에서 끌어올릴 수 있는 경로는 셋뿐이다.

1. `prediction.onramp_route_forecast.enabled` (adapter:2863-2870)
2. `prediction.route_bias_forecast` + `demand_profile ∈ {d_ramp_bias, f_ramp_bias, ...}` (adapter:2933-2940)
3. `prediction.local_ramp_arrival_forecast.enabled` (adapter:2942-3003)

실 런 캘리브레이션 `real_world_prediction_calibration_pshb4500fix_20260724.json` 의
`prediction` 키는 `["audit_calibration"]` 하나뿐이고, `demand_profile` 은
`real_world_inpx_time_profile` 이라 2번 분기에도 안 걸린다. 따라서 세 램프 경로가 모두
꺼져 있고 `ramp_arrival = {R_D_W: 0, R_F_W: 0, R_D_E: 0, R_F_E: 0}` 이다.

이것은 "계약 위반"이 아니라 **계약대로의 결과**다. 러너가 램프 유입을 안 재기로 되어
있으므로, 모델이 램프 수요를 알아야 한다면 캘리브레이션으로 넣거나 러너를 고쳐야 한다.

---

## 4. 알려진 불일치 — `KNOWN-URBAN-GATE-MEAN`

- 상태: **미해결. 이번 회차에서 고치지 않는다.**
- 이유: 배율 자체를 지우는 것(게이트 117→32)과 격자를 실 유입 구조에 맞추는 것은
  같은 결정이다. 격자 재정렬과 함께 결정한다.
- 드러내는 검사: `tests/test_demand_contract.py::DemandContractKnownMismatchTests`
  — 지금 **의도적으로 FAIL** 한다. xfail 로 감추지 않았다.

### 4.1 실측 (scale=1, `modi_eval_rw_control.inpx`)

도시부 — 유입 지점 32개, 모델 게이트 117개.

| 구간 시작 s | VISSIM 도시부 총량 | 지점당 평균(=state 값) | 모델 주입 총량 | 배율 |
|---:|---:|---:|---:|---:|
| 0 | 12,747.2 | 398.351 | 46,607.0 | 3.6562 |
| 900 | 18,209.2 | 569.038 | 66,577.4 | 3.6562 |
| 1800 | 19,120.4 | 597.513 | 69,909.0 | 3.6562 |
| 2700 | 16,388.9 | 512.153 | 59,921.9 | 3.6562 |
| 3600 | 12,747.2 | 398.351 | 46,607.0 | 3.6562 |
| 4500 | 9,105.6 | 284.550 | 33,292.3 | 3.6562 |

고속부 — 유입 지점 2개, 모델 링크 2개. 총량이 맞는다.

| 구간 시작 s | VISSIM 고속부 총량 | 지점당 평균 | 모델 주입 총량 | 배율 |
|---:|---:|---:|---:|---:|
| 0 | 6,160.0 | 3,080.0 | 6,160.0 | 1.0000 |
| 900 | 8,800.0 | 4,400.0 | 8,800.0 | 1.0000 |
| 1800 | 9,240.0 | 4,620.0 | 9,240.0 | 1.0000 |
| 2700 | 7,920.0 | 3,960.0 | 7,920.0 | 1.0000 |
| 3600 | 6,160.0 | 3,080.0 | 6,160.0 | 1.0000 |
| 4500 | 4,400.0 | 2,200.0 | 4,400.0 | 1.0000 |

배율이 6개 구간 전부 동일하다 — 시간 프로파일이 아니라 **구조**의 문제다.

### 4.2 고속부가 맞는 것은 우연이다

두 조건이 겹쳐서 맞는다.

1. VISSIM 고속부 유입이 2개이고 모델 `freeway_links` 도 2개다 → 총량이 맞는다.
2. 두 유입(`no=1098` link 74, `no=1099` link 26)의 시간구간별 volume 이 **완전히 같다**
   (3080 / 4400 / 4620 / 3960 / 3080 / 2200) → 평균 == 각 값이라 방향 분해도 맞는다.

둘 중 하나만 깨져도(고속부 유입 추가, 방향별 수요 비대칭 도입, `freeway_links` 분할)
고속부도 도시부와 같은 오류를 낸다. `test_freeway_volume_vph_is_point_mean_and_model_total_matches_plant`
가 그 순간 FAIL 한다.

### 4.3 게이트 수가 망마다 다르다

같은 어댑터·같은 격자(117 게이트)를 다른 실망 변형에 붙이면 배율이 달라진다.

| 네트워크 | 도시부 유입 지점 | 배율 (117 게이트 기준) |
|---|---:|---:|
| `modi_eval_rw_control.inpx` (실 런) | 32 | 3.656 |
| `modi_eval_rw_control_peakplateau_20260729.inpx` | 29 | 4.034 |
| `modi_eval_rw_control_peakhold4500_recovery_20260729.inpx` | 29 | 4.034 |

경계 게이트는 `scripts/generate_real_world_distributed_players.py:391-396` 이
**이웃이 안 쓴 정방위마다 자동 생성**한다. VISSIM 을 보지 않는다. 그래서 게이트 수와
유입 지점 수를 이어 주는 것이 아무것도 없다 — 이것이 근본 원인이다.

---

## 5. 검사

```powershell
python -m unittest tests.test_demand_contract
```

기대 결과 (2026-08-11 기준): **Ran 8 tests, FAILED (failures=7)**.
6개 불변식은 PASS, 알려진 불일치 2건이 FAIL 한다(그중 하나가 6개 시간구간 subTest).

### 5.1 지금 성립하는 규약 — `DemandContractInvariantTests` (전부 PASS)

| 검사 | 지키는 것 |
|---|---|
| `test_producer_emits_exactly_the_four_contract_fields` | 러너가 쓰는 필드 집합과 `ramp_volume_vph` 리터럴 0 |
| `test_freeway_volume_vph_is_point_mean_and_model_total_matches_plant` | 고속부는 지점 수 == 링크 수, 6구간 전부 총량 일치 |
| `test_urban_boundary_arrivals_read_boundary_in_gates_only` | `boundary_out` 는 주입 경로가 없다 |
| `test_boundary_out_entries_are_populated_and_only_leak_into_diagnostics` | 진단 부풀림 비율 `(117+119)/117` |
| `test_ramp_volume_vph_zero_yields_zero_ramp_arrival_in_live_run` | 실 캘리브레이션에 램프 예측 3경로 모두 없음 → 램프 도착 0 |
| `test_known_urban_mismatch_ledger_matches_measurement` | 이 문서의 117/32 가 실측과 같은가 (드리프트 감지) |

여섯 검사 모두 **되돌림 증명을 마쳤다** — 각각이 지키는 성질을 인위로 깨면 FAIL 로 뒤집힌다
(고속부 유입 오분류 / 대장 117→118 / 램프 예측 주입 / `boundary_out` 비우기 /
필드 집합 변조 / 가짜 게이트 추가).

### 5.2 지금 깨져 있는 규약 — `DemandContractKnownMismatchTests` (전부 FAIL, 의도됨)

| 검사 | 지금 값 |
|---|---|
| `test_urban_gate_count_equals_vissim_urban_input_point_count` | `32 != 117` |
| `test_urban_boundary_total_equals_plant_total_each_interval` | 6구간 전부 3.6562배 |

이 둘이 PASS 로 바뀌면 §4 를 해결한 것이다. 그때 이 절과
`test_known_urban_mismatch_ledger_matches_measurement` 의 대장 상수를 같이 갱신해라.

---

## 6. 이 계약을 바꾸려면

1. 이 문서의 §1 표를 먼저 고친다.
2. `tests/test_demand_contract.py` 상단 대장 상수와 §5 표를 맞춘다.
3. 생산자·소비자 **양쪽**을 같은 커밋에서 고친다. 한쪽만 고치면 3.66배와 같은 종류의
   침묵 오류가 다시 생긴다.
4. `vendor/NumSim-mine` 은 해시고정 스냅샷이다. 소비 측 의미를 바꿔야 하면 상류를
   고치고 `scripts/update_numsim_snapshot.py` 로 재스냅샷한다.
