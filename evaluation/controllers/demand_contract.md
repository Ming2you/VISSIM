# `state.demand` 계약 — VISSIM 러너(생산자) ↔ Stackelberg 어댑터(소비자)

- 문서 상태: `발효` (2026-08-11 게이트 앵커링 개정)
- 계약 대상: 러너가 매 결정마다 쓰는 `state_*.json` 의 `demand` 블록
- 강제 검사: `tests/test_demand_contract.py`, `scripts/tests/test_urban_gate_demand_vbs_behavior.py`
  (`python -m unittest <module>`, 저장소 루트에서)
- 실측 근거: `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`,
  `evaluation/real_world_modi_inventory/vehicle_input_roles.csv`,
  `evaluation/real_world_modi_inventory/urban_input_gate_map_20260811.csv`,
  `evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json`
  — 봉인 런 `evaluation/runs/n1_final_20260807/.../run_manifest_v2_1.json` 이 지정한 조합

이 문서가 존재하는 이유. 러너는 도시부 수요로 **유입 지점당 평균 스칼라 하나**를 썼고
어댑터는 그것을 **게이트 각각의 값**으로 읽었다. 게이트 117 vs 유입 32 라서 도시부 수요가
3.66배로 주입됐다. 2026-08-11 개정에서 러너가 **게이트별 벡터**를 쓰도록 바꿨다.
스칼라 경로는 합성망 러너(8seg·g6)를 위해 폴백으로 남아 있다.

---

## 1. 요약

| 필드 | 생산자가 넣는 것 | 소비자가 읽는 것 | 뿌리는 대상 |
|---|---|---|---|
| `urban_volume_vph_by_gate` | 게이트별 [veh/h] — 그 게이트를 먹이는 VISSIM vehicle input 의 유량 | 그대로 게이트 도착률 | 대장이 지정한 게이트 |
| `urban_volume_vph` | 도시부 유입 **지점당 평균** [veh/h] (폴백 전용) | `by_gate` 가 비었을 때만, 게이트 **전부**에 복제 | `boundary_in_links` + `boundary_out_links` |
| `urban_unmapped_volume_vph` | 격자에 게이트가 없어 못 실은 유입의 합 | **안 읽는다** (회계·감사용) | — |
| `urban_internal_volume_vph` | 내부 발생(`Dummy Link`) 유입의 합 | **안 읽는다** (회계·감사용) | — |
| `freeway_volume_vph` | 고속부 유입 **지점당 평균** [veh/h] | 본선 링크 **각각의** 유입률 | `freeway_links` (2 vs 2) |
| `ramp_volume_vph` | 실 러너는 **리터럴 0** | 램프 **각각의** 외생 도착률 | `ramps` (외생 도착 없음) |

불변식 두 개다.

1. **회계가 닫힌다.** `sum(by_gate) + unmapped + internal == VISSIM 도시부 총량`.
   러너가 유입을 하나라도 흘리면 이 등식이 깨진다.
2. **게이트 하나에 유입 하나.** 모델이 주입하는 게이트별 값은 그 게이트를 먹이는
   vehicle input 의 유량과 같다. 총량만 맞는 것으로는 부족하다 — 공간 분포도 계약이다.

`freeway_volume_vph` 는 아직 스칼라다. 유입 2개 == 링크 2개라 총량이 맞는다(§4.3).

---

## 2. 생산자 — `scripts/run_real_world_stackelberg_controller.vbs`

### 2.1 값을 만드는 곳

`LoadInpxDemandSchedule(inpxPath, rolesPath, scale, profilePath, gateMapPath)` 가
`.inpx` 의 `//vehicleInput` 을 전수 순회한다.

```vbs
' 분류 — 역할 문자열이 "freeway" 로 시작하거나 링크가 RW_FREEWAY_INPUT_LINKS(="26,74")
isFreeway = (Left(roleKey, 7) = "freeway" Or InCsvInt(linkNo, RW_FREEWAY_INPUT_LINKS))

' 도시부: 시간구간별 (합, 개수)는 폴백 스칼라용으로 그대로 두고,
AddDemandScheduleValue urbanSumBySec, urbanNBySec, secKey, volume
' 같은 값을 대장이 지정한 게이트로도 보낸다.
AddUrbanGateDemand demandUrbanGateBySec, demandUrbanUnmappedBySec, _
    demandUrbanInternalBySec, secKey, urbanGateMap, viNo, volume
```

`volume` 에는 `scale` 과 역할별 `multiplier` 가 이미 곱해져 있다. **게이트별 값이
런타임 배수를 그대로 물고 간다** — 이것이 조인을 어댑터가 아니라 러너에 둔 이유다.
정적 산출물을 어댑터가 읽으면 `-DemandScale` / `-DemandProfile` 런에서 조용히 어긋난다.

### 2.2 조인 키 — 대장 CSV

`evaluation/real_world_modi_inventory/urban_input_gate_map_20260811.csv`,
생성기 `scripts/derive_urban_input_gate_map.py`. 러너는 앞 세 열(`no,gate,status`)만
읽는다(`LoadUrbanInputGateMap`). 이름 열에 콤마가 있어서(`개포3,4단지_WB`) `name` 은 마지막 열이다.

방위 규칙 — **유입 이름의 진행방향 접미사가 정본**이고(`NB→S`, `SB→N`, `EB→W`, `WB→E`),
이름이 없으면 기하 추정 `leg.link_geometry`(`outputs/boundary_input_alignment_20260811.json`)를 쓴다.
기하만 쓰면 22곳 중 11곳밖에 못 붙는다(실측). 이름 규칙이 8곳을 더 붙인다.
게이트 이름은 문자열로 짓지 않고 `grid_node_legs[node][leg]["in"]` 에서 읽어 온다.

`status` 는 다섯 가지다 — `mapped` / `internal`(Dummy Link, 내부 발생) /
`leg_absent_at_node` / `leg_occupied_by_grid_neighbour` / `freeway_excluded`.
`mapped` 가 아니면 게이트로 안 가고 사유 버킷으로 간다. 조용히 사라지지 않는다.

### 2.3 값을 쓰는 곳

```vbs
ts.WriteLine "  ""demand"": {""urban_volume_vph"": " & Num(demandUrbanNow) & _
  ", ""urban_volume_vph_by_gate"": " & UrbanGateDemandJson(simSec) & _
  ", ""urban_unmapped_volume_vph"": " & ... & ", ""urban_internal_volume_vph"": " & ... & _
  ", ""freeway_volume_vph"": " & Num(demandFreewayNow) & ", ""ramp_volume_vph"": 0, ...
```

- 시간 선택은 세 필드 모두 `ActiveDemandScheduleKey(simSec)` 하나를 쓴다.
- `ramp_volume_vph` 는 **리터럴 0**. VISSIM 램프 유입을 재지 않는다(§3.3).
- `demand_profile` 은 `"real_world_inpx_time_profile"` 또는 `"..._scaled"`.
  어느 쪽도 어댑터의 프로파일 분기에 걸리지 않으며, 게이트 앵커링이 켜지면
  그 분기 자체를 건너뛴다(§3.2).

### 2.4 fail-closed 와 열화 경로

- 도시부 유입 중 대장이 아는 것이 **하나도 없으면** `ERROR=URBAN_INPUT_GATE_MAP_UNUSABLE`
  로 런을 세운다(`WScript.Quit 2`). 그대로 두면 `by_gate` 가 비고 어댑터가 스칼라
  폴백으로 돌아가 3.66배가 조용히 되살아난다.
- 매 런 `URBAN_GATE_ANCHOR_LOADED mapped_inputs=.. internal_inputs=.. unmapped_inputs=..` 를 남긴다.
  실 망 기대값은 `19 / 10 / 3`.
- `.inpx` XML 로드 자체가 실패하면(`WARN=DEMAND_SCHEDULE_XML_LOAD_FAILED`)
  `ComputeOriginalDemandAverages` 폴백이 도는데 그 경로는 **게이트별 값을 만들지 않는다**.
  `by_gate` 가 `{}` 라서 어댑터는 스칼라로 돌아간다 — 열화 경로이고, 러너 로그에
  WARN 이 남는다.

---

## 3. 소비자 — `evaluation/controllers/vissim_stackelberg_adapter.py`

`profiled_demand_rates` (adapter:2789-) 가 값을 벡터로 편다.

```python
urban_by_gate = demand.get("urban_volume_vph_by_gate")
gate_anchored = isinstance(urban_by_gate, Mapping) and bool(urban_by_gate)
if gate_anchored:
    unknown = sorted(g for g in urban_by_gate if g not in set(gate_keys))
    if unknown:
        raise ValueError(...)          # 대장과 격자가 따로 갱신됐다 -> 런을 세운다
    urban_boundary = {key: 0.0 for key in gate_keys}
    for gate, value in urban_by_gate.items():
        urban_boundary[str(gate)] = float(value)
else:
    urban_boundary = {key: urban_vph for key in gate_keys}   # 예전 스칼라 복제
```

`demand_from_state` (adapter:3008-) 가 이 셋을 `DemandStep` 으로 묶어 `horizon_steps` 개
복제한다. 호출 지점은 `adapter:5479` 와 `harness/g6/g6_core.py:378`.

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

위 표의 모든 경로가 `boundary_in` 만 본다. 실 cfg 에서
`boundary_in_links ∩ boundary_out_links = ∅` 이고 `boundary_in` movement 의 origin 중
`boundary_out_links` 에 든 것은 하나도 없다. 그럼에도 전 키를 합산하는 경로가 둘 있다.

| 위치 | 성격 | 실 런에서 쓰이나 |
|---|---|---|
| `controllers/stackelberg_mpc.py:2237-2246` `_forecast_demand_metadata` | **진단 메타데이터만** (`leader_forecast_boundary_*`), 결정에 안 들어감 | 쓰인다 |
| `controllers/classical_hierarchical.py:408-411` `avg_boundary_demand` | 결정에 들어감 | **안 쓰인다** — 어댑터는 `StackelbergMPCController` / `StackelbergWuMeteredController` / `DistributedCoordinator` 만 만든다(adapter:5769, 5791, 5823) |

스칼라 복제 시절에는 이 진단값이 `(117+119)/117 = 2.0171` 배 부풀어 있었다
(t=1800 s 에서 주입 69,909 vs 로그 141,012 veh/h). 게이트 앵커링 뒤에는
`boundary_out` 값이 **0** 이라 진단 합 == 주입 합이다(t=1800 s: 둘 다 14,563.6).

도시부 공간 프로파일 분기(`urban_west_heavy` 등)와 `urban_west_east_ratio` 는
게이트 앵커링이 켜지면 **건너뛴다**. 러너가 이미 vehicle input 단위로 배수를 적용한
값을 주므로 여기서 또 흔들면 이중 적용이다. 그 분기들은 합성망 게이트 이름
(`in_A_left` 등) 기준이라 실 망에서는 애초에 걸리지도 않았다.

### 3.3 `ramp_volume_vph` 판정 — 실 런에서 램프 외생 도착은 **0**

러너가 0 을 쓰므로 어댑터의 기본값(`max(120, 0.12·freeway_vph)`)은 절대 발동하지 않는다.
`ramp_arrival` 를 0 에서 끌어올릴 수 있는 경로는 셋뿐이다.

1. `prediction.onramp_route_forecast.enabled` (adapter:2863-2870)
2. `prediction.route_bias_forecast` + `demand_profile ∈ {d_ramp_bias, f_ramp_bias, ...}`
3. `prediction.local_ramp_arrival_forecast.enabled`

실 런 캘리브레이션 `real_world_prediction_calibration_pshb4500fix_20260724.json` 의
`prediction` 키는 `["audit_calibration"]` 하나뿐이고, `demand_profile` 은
`real_world_inpx_time_profile` 이라 2번 분기에도 안 걸린다. 따라서 세 램프 경로가 모두
꺼져 있고 `ramp_arrival = {R_D_W: 0, R_F_W: 0, R_D_E: 0, R_F_E: 0}` 이다.
`.inpx` 의 vehicle input 34개 중 램프 링크에 놓인 것은 없다 — VISSIM 램프 교통은
도시부 origin 의 static route 로 들어온다. 러너가 그것을 재지 않는다는 뜻이지
"램프 수요가 0" 이라는 뜻이 아니다.

---

## 4. 알려진 불일치 — `KNOWN-URBAN-GATE-COVERAGE`

- 상태: **미해결. 이번 회차 범위 밖.** 남은 것은 **격자에 없는 입구 3곳**뿐이다.
- 이유: 게이트 신설 2 + leg 병합 1 은 `config_overrides.network` 재생성
  (`scripts/generate_real_world_distributed_players.py`)의 몫이다. `urban_movements` 1,414 와
  `turning_ratios` 41 노드가 같이 바뀐다.
- 드러내는 검사: `tests/test_demand_contract.py::DemandContractKnownMismatchTests`
  — 지금 **의도적으로 FAIL** 한다. xfail 로 감추지 않았다.

| 유입 | 위치 | status | peak veh/h |
|---|---|---|---:|
| 1101 (무명) | `SC1004_SW` | `leg_absent_at_node` | 1,400.0 |
| 1100 (무명) | `SC1004_SE` | `leg_absent_at_node` | 849.2 |
| 194 `개포주민센터_NB` | `SC13_S` | `leg_occupied_by_grid_neighbour` (`S_SC16`) | 81.5 |

### 4.1 실측 (scale=1, `modi_eval_rw_control.inpx`)

도시부 — VISSIM 유입 32개 = 입구 22 + 내부발생 10. 모델 게이트 117개 중 19개가 먹인다.

| 구간 시작 s | VISSIM 32 | 입구 22 | 게이트 19 | 미배정 3 | 내부발생 10 | 모델 주입 (개정 전) | 모델 주입 (개정 후) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 12,747 | 11,263 | 9,709 | 1,554 | 1,484 | 46,607 | 9,709 |
| 900 | 18,209 | 16,089 | 13,870 | 2,219 | 2,120 | 66,577 | 13,870 |
| 1800 | 19,120 | 16,894 | 14,564 | 2,331 | 2,226 | 69,909 | 14,564 |
| 2700 | 16,389 | 14,481 | 12,483 | 1,998 | 1,908 | 59,922 | 12,483 |
| 3600 | 12,747 | 11,263 | 9,709 | 1,554 | 1,484 | 46,607 | 9,709 |
| 4500 | 9,106 | 8,046 | 6,935 | 1,110 | 1,060 | 33,292 | 6,935 |

개정 전 배율은 6구간 전부 3.6562(= 117/32). 개정 후 주입/입구 비는 6구간 전부
0.8620 이고, 모자란 0.1380 이 위 표의 입구 3곳이다. 게이트별 값은 각 유입의 유량과
같다(검사 `test_each_gate_carries_its_own_vissim_input_volume`).

고속부 — 유입 지점 2개, 모델 링크 2개. 총량이 맞는다(배율 1.0000, 6구간 전부).

| 구간 시작 s | VISSIM 고속부 총량 | 지점당 평균 | 모델 주입 총량 |
|---:|---:|---:|---:|
| 0 / 900 / 1800 / 2700 / 3600 / 4500 | 6,160 / 8,800 / 9,240 / 7,920 / 6,160 / 4,400 | 3,080 / 4,400 / 4,620 / 3,960 / 3,080 / 2,200 | 같음 |

### 4.2 내부 발생 10개 (`Dummy Link 1~12`)

사용자 확정으로 **망 입구가 아니다**. 그래서 경계 게이트에 안 싣는다. 사실만 적는다.

- 개정 전에는 이 10개가 도시부 평균에 섞여 들어가 게이트 117개에 복제됐다.
  peak 기준 2,226 veh/h 가 평균에 69.6 veh/h 를 얹었고, 게이트 전체로는 8,138 veh/h 였다.
- 개정 후에는 경계 주입에서 완전히 빠지고 `urban_internal_volume_vph` 로만 남는다.
  즉 모델이 아는 도시부 유입 총량이 VISSIM 총량보다 peak 2,226 veh/h(11.6%) 적다.
- VISSIM 안에서는 그대로 발생한다. 이 차이를 모델이 받아야 하는지(내부 발생원 추가),
  받지 않아야 하는지(격자 밖 통행으로 간주)는 **이 문서가 판단하지 않는다**.

### 4.3 고속부가 맞는 것은 우연이다

두 조건이 겹쳐서 맞는다.

1. VISSIM 고속부 유입이 2개이고 모델 `freeway_links` 도 2개다 → 총량이 맞는다.
2. 두 유입(`no=1098` link 74, `no=1099` link 26)의 시간구간별 volume 이 **완전히 같다**
   (3080 / 4400 / 4620 / 3960 / 3080 / 2200) → 평균 == 각 값이라 방향 분해도 맞는다.

둘 중 하나만 깨져도(고속부 유입 추가, 방향별 수요 비대칭 도입, `freeway_links` 분할)
고속부도 도시부와 같은 오류를 낸다.
`test_freeway_volume_vph_is_point_mean_and_model_total_matches_plant` 는 (합, 개수)만
보므로 **조건 2 가 깨지는 것은 못 잡는다** — 방향이 뒤바뀌어도 합은 같다. 도시부는
게이트 앵커링으로 지점별 대조가 되지만 고속부는 아직 아니다. 고속부를 앵커링하려면
같은 방식으로 유입→링크 대장을 만들면 된다(이번 범위 밖).

---

## 5. 검사

```powershell
python -m unittest tests.test_demand_contract                       # Ran 15, FAILED (failures=7)
python -m unittest scripts.tests.test_urban_gate_demand_vbs_behavior # Ran 2, OK
python -m unittest scripts.tests.test_derive_urban_input_gate_map    # Ran 9, OK
```

기대 결과 (2026-08-11 기준): 불변식 13개 PASS, 알려진 불일치 2건 FAIL
(그중 하나가 6개 시간구간 subTest).

### 5.1 지금 성립하는 규약 — `DemandContractInvariantTests` (전부 PASS)

| 검사 | 지키는 것 |
|---|---|
| `test_producer_emits_exactly_the_contract_fields` | 러너가 쓰는 필드 7개와 `ramp_volume_vph` 리터럴 0 |
| `test_freeway_volume_vph_is_point_mean_and_model_total_matches_plant` | 고속부는 지점 수 == 링크 수, 6구간 전부 총량 일치 |
| `test_urban_boundary_arrivals_read_boundary_in_gates_only` | `boundary_out` 는 주입 경로가 없다 |
| `test_each_gate_carries_its_own_vissim_input_volume` | **지점별** 대조 — 게이트값 == 그 유입의 유량 |
| `test_gates_without_a_vissim_input_get_zero` | 유입 없는 게이트 98개는 0 |
| `test_boundary_out_entries_are_populated_and_carry_zero` | 키는 유지, 값은 0 → 진단 부풀림 소멸 |
| `test_unknown_gate_key_in_state_is_rejected` | 모르는 게이트 이름이 오면 런을 세운다 |
| `test_scalar_only_state_still_uses_the_point_mean_fallback` | 8seg·g6 스칼라 경로 보존 |
| `test_ramp_volume_vph_zero_yields_zero_ramp_arrival_in_live_run` | 램프 예측 3경로 모두 없음 → 도착 0 |
| `test_producer_accounting_closes` | 게이트합 + 미배정 + 내부발생 == 도시부 총량 |
| `test_gate_anchoring_conserves_entry_demand_on_a_complete_grid` | 게이트 3개를 가정으로 채우면 입구 총량이 **정확히** 보존 |
| `test_known_ledger_matches_measurement` | 대장 상수(117 / 32 / 22 / 19 / 10 / 3)가 실측과 같은가 |
| `test_gate_map_gates_exist_in_the_model_grid` | 대장의 게이트가 격자에 있고 중복이 없다 |

생산자 쪽은 `scripts/tests/test_urban_gate_demand_vbs_behavior.py` 가 러너 프로시저를
떼어 **cscript 로 실행**한다 — 조인·구간 선택·JSON 직렬화를 실제로 돌려 본다.
두 번째 검사는 `WriteStateJson` 의 demand 줄을 그대로 실행해 나온 문자열을
`json.loads` 로 파싱한다.

되돌림 증명 6건 (인위로 깨서 FAIL 로 뒤집히는 것을 확인).

| 깬 것 | FAIL 로 뒤집힌 검사 |
|---|---|
| 어댑터 게이트 앵커링 제거(스칼라 복제로 되돌림) | 지점별·0채움·boundary_out·보존 + 미지 게이트 거부 |
| 미지 게이트를 조용히 무시 | `test_unknown_gate_key_in_state_is_rejected` |
| `boundary_out` 에 스칼라 채우기 | boundary_out·0채움·보존 |
| 러너 조인 제거(전부 unmapped) | `test_gate_join_behaviour` |
| state 에서 `urban_volume_vph_by_gate` 제거 | 필드 집합 + 방출 줄 JSON |
| 방위 규칙 뒤집기(NB→N …) | 생성기 검사 3건 |

### 5.2 지금 깨져 있는 규약 — `DemandContractKnownMismatchTests` (전부 FAIL, 의도됨)

| 검사 | 지금 값 |
|---|---|
| `test_every_vissim_urban_entry_has_a_model_gate` | 입구 22 중 3곳에 게이트가 없다 |
| `test_urban_boundary_total_equals_plant_entry_total_each_interval` | 6구간 전부 0.8620배 |

이 둘이 PASS 로 바뀌면 §4 를 해결한 것이다. 그때 대장 상수와 §4 표를 같이 갱신해라.

---

## 6. 이 계약을 바꾸려면

1. 이 문서의 §1 표를 먼저 고친다.
2. `tests/test_demand_contract.py` 상단 대장 상수와 §5 표를 맞춘다.
3. 생산자·소비자 **양쪽**을 같은 커밋에서 고친다. 한쪽만 고치면 3.66배와 같은 종류의
   침묵 오류가 다시 생긴다.
4. 격자(`config_overrides.network`)를 재생성했으면 대장도 재생성해라.
   `python scripts/derive_urban_input_gate_map.py --out <새 CSV>` 후
   러너의 `DefaultUrbanInputGateMapPath()` 를 새 파일로 옮긴다. 안 그러면 어댑터가
   모르는 게이트 이름을 보고 런을 세운다(그것이 의도된 동작이다).
5. `vendor/NumSim-mine` 은 해시고정 스냅샷이다. 소비 측 의미를 바꿔야 하면 상류를
   고치고 `scripts/update_numsim_snapshot.py` 로 재스냅샷한다.
