# Codex 재검토 요청 — 2026-08-10 ~ 08-11 회차

> Claude 가 이 두 회차에 찾은 것과 고친 것을 **독립적으로 재현·반증**해 달라는 요청이다.
> 내가 이번 회차에 **진단을 네 번 뒤집었으므로**, 여기 적힌 것도 틀렸을 수 있다.
> 각 항목에 내가 매긴 확신도와 **틀렸다면 어떻게 드러나는지**를 함께 적었다.

- VISSIM `codex/plant-fidelity-v2-1` — `d6bfbd0..49a3f51` (15 커밋)
- NumSim `freeway-zone-followers` — `5a2fe7d..e4bf4d0` (5 커밋)
- vendor 앵커 = 상류 `e4bf4d0`

## 실행 환경 (재현에 필요)

```
python  C:/Users/alsrj/AppData/Local/Programs/Python/Python313/python.exe
        ('python' 은 Windows Store 스텁이라 exit 49)
pytest  없음. python -m unittest <module.path> 를 쓴다.
plant/tests 는 cwd=VISSIM/plant 와 PYTHONPATH=VISSIM 저장소루트를 **둘 다** 요구한다.
scripts/tests 와 tests/ 는 unittest discover 가 안 먹는다(패키지 아님). 모듈을 명시해야 한다.
```

기대 상태 — `scripts/tests` 480/480, `tests/` 124/124, `plant/tests` 132/132 OK.
NumSim 은 기존 실패 10건이 baseline 이다(forecast_awareness 5, post_analysis 2,
segment_local_plant 2, wu_faithful_follower 1). `test_rl_ddqn` 은 torch 미설치,
`test_six_controller_comparison` 은 45분 초과로 미실행.

---

# 1. 최우선 재검토 — 모델이 도시부 수요를 3.66배 주입한다

**확신도 — 높음. 다만 영향 범위는 확인 못 했다.**

## 주장

러너는 VISSIM 도시부 유입의 **지점당 평균**을 `state.demand.urban_volume_vph` 에 쓴다.

```vbscript
' scripts/run_real_world_stackelberg_controller.vbs:2950
demandUrbanBySec(key) = CDbl(urbanSumBySec(key)) / CDbl(urbanNBySec(key))
```

어댑터는 그 평균을 **경계 게이트 117개 전부**의 값으로 읽는다.

```python
# evaluation/controllers/vissim_stackelberg_adapter.py:2814
urban_boundary = {
    str(link): urban_vph
    for link in list(cfg.network.boundary_in_links) + list(cfg.network.boundary_out_links)
}
```

유입 지점이 32개인데 게이트가 117개라 **117/32 = 3.66배**가 된다.

| timeInt | VISSIM 실제 도시부 유입 | 모델 주입 | 배율 |
|---|---:|---:|---:|
| 1 0 | 12,747 veh/h | 46,607 | 3.66 |
| 1 900000 | 18,209 | 66,577 | 3.66 |
| 1 1800000 | 19,120 | 69,909 | 3.66 |
| 1 2700000 | 16,389 | 59,922 | 3.66 |
| 1 3600000 | 12,747 | 46,607 | 3.66 |
| 1 4500000 | 9,106 | 33,292 | 3.66 |

여섯 구간 전부 배율이 같다. 우연이 아니라 구조다.

## 재현 방법

`inpx` 의 `vehicleInput/timeIntVehVols/timeIntervalVehVolume` 을
`evaluation/real_world_modi_inventory/vehicle_input_roles.csv` 의 `role` 로 걸러
`urban_input` 만 구간별로 합/개수를 낸 뒤, 게이트 수와 곱해 비교하면 된다.
게이트 수는 `evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json`
의 `config_overrides.network.boundary_in_links` 길이(117)다.

## 내가 확인 못 한 것 — **여기를 봐 달라**

1. **주입된 수요가 실제로 다 들어가는가.** `urban_boundary` 는 도착률 *지시값*이다.
   하류 용량·게이팅에서 잘리면 실제 유입 차량은 3.66배가 아닐 수 있다.
   `urban_demand_arrivals_veh` 실측과 대조해야 한다.
2. **`boundary_out_links` 119개도 같은 값을 받는데** 어댑터 주석은 "boundary_out links are
   not used as exogenous arrivals" 라고 한다. 정말 안 쓰이는지 확인이 필요하다.
3. **freeway 와 ramp 에도 같은 어긋남이 있는가.** `freeway_volume_vph` 도 러너가
   `freewaySumBySec / freewayNBySec` 로 평균을 낸다(vbs:2952). 어댑터는
   `{link: freeway_vph for link in cfg.network.freeway_links}` 로 뿌린다. **같은 구조다.**
   freeway_links 수와 VISSIM freeway 입력 수(2)를 비교해 봐야 한다. 나는 안 해봤다.
4. **`_scaled` 프로파일의 multiplier.** `roleMultipliers` 가 역할별 배수를 적용하는데
   (vbs:2933-2935) 그 값이 어디서 오고 3.66배에 어떻게 얹히는지 추적 안 했다.

## 틀렸다면 이렇게 드러난다

- 실제 유입 차량 수가 VISSIM 관측과 맞으면 → 지시값만 크고 실효는 정상. 내 주장이 과장이다.
- `boundary_in_links` 117개 중 상당수가 movement 에 안 물려 있으면 → 실효 게이트가 32개에
  가까울 수 있다. `urban_movements` 1,414 에서 boundary origin 을 쓰는 것이 몇 개인지 세면 된다.

---

# 2. 모델 격자가 VISSIM 망과 다르다

**확신도 — 중간. 분류는 사용자 확정, 격자 대조는 내 측정.**

## 주장

VISSIM 도시부 vehicle input 32개를 분류하면 이렇다(사용자가 dummy 를 내부 발생으로 확정).

| 종류 | 개수 | peak 합 | 모델 격자에서의 상태 |
|---|---:|---:|---|
| named (실제 위치) | 14 | 10,361 veh/h | leg없음 13, grid 1 — **전부 안 맞음** |
| unnamed | 8 | 6,533 | boundary 5 OK, leg없음 2, 노드없음 1 |
| dummy (내부 발생) | 10 | 2,226 | 경계 아님 |

진짜 망 입구 = 22개, 16,894 veh/h. 모델이 제대로 경계로 아는 것은 **5개뿐**이다.
반대로 모델은 경계 게이트를 117개 갖고 있어 **약 95개가 VISSIM 에 대응물 없는 정방향 패딩**이다.

즉 **모델 격자가 VISSIM 망보다 좁으면서 동시에 넓다.**

## 근거

- `outputs/link_player_assignment_20260805.json` 의 `link_leg`(957) · `link_owner`
- config 의 `grid_node_legs` — grid leg 는 대각선(NE_SC2 …), boundary leg 는 정방향(N/S/E/W)
- 유입 링크 31/32 가 `link_leg` 를 갖는데 **27개가 대각선**이라 정방향 게이트와 안 맞는다

## 봐 달라

1. **`link_leg` 의 방위 규약이 모델 격자와 같은 좌표계인가.** 나는 문자열만 비교했다.
   `link_leg` 의 NE 와 `grid_node_legs` 의 `NE_SC2` 가 같은 방위를 뜻하는지 확인이 필요하다.
   다르면 "27개가 대각선이라 안 맞는다" 는 전부 무효다.
2. **`link_owner` 가 없는 링크(link 69, 1,400 veh/h)** 가 왜 미배정인지.
3. **모델 격자의 정방향 패딩 95개가 언제 왜 들어왔는지.** git 이력을 못 봤다.
   의도가 있었다면 내 "패딩" 판정이 틀렸다.

---

# 3. 정본 신호 타이밍 표가 틀린 `.sig` 를 읽고 있었다 (고침)

**확신도 — 높음. 감사 게이트가 PASS 로 바뀌었다.**

`derive_signal_group_timing._sig_path_for` 가 파일명 끝자리 번호로 `.sig` 를 골랐는데
VISSIM 은 inpx 의 `signalController/@supplyFile2` 를 읽는다. 4/15 SC 가 달랐다.

```
SC5  timing=test-bed5.sig(140s)  inpx=test-bed7.sig(160s)
SC6  timing=test-bed6.sig(100s)  inpx=test-bed9.sig(160s)
SC11 timing=test-bed11.sig(160s) inpx=test-bed3.sig(150s)
SC12 timing=test-bed12.sig(150s) inpx=test-bed5.sig(140s)
```

**수치 변화 — SG 128→136, 동시녹색 쌍 160→222, 최악 녹색 과대 5.00→5.47배.**
즉 이름규칙 2현시 근사의 오차가 보고돼 있던 것보다 **39% 크다**.

체인을 전부 재생성했다(timing → movement map → actuation plan → sgplan.vbs → 감사).
그 과정에서 **커밋돼 있던 `sgplan.vbs` 가 계획 산출물과 어긋난 채**였음을 발견했고,
기존 검사가 집계만 봐서 못 잡았다. 원본 sha 대조를 추가했다.

## 봐 달라

- `outputs/signal_group_timing_v3.json` 을 재생성해 SG 136 / 쌍 222 / 5.47배가 나오는지
- 감사 `signal_timing_canon` 이 PASS 인지
- **222 쌍 중 실제로 동시녹색이 되는 것이 몇 개인지.** 나는 "이름 규칙이 만드는 쌍" 을 셌을 뿐
  러너가 실제로 동시에 녹색을 주는지는 확인 안 했다. N4-5 가 축 안 분배를 닫았다고 하는데
  그 효과가 이 222 에 어떻게 반영되는지 안 봤다.

---

# 4. assignment_ties 를 질량 기준으로 재정의 (고침)

**확신도 — 중간. 설계 판단이 들어갔다.**

33건 tie 중 차를 싣는 6건이 전부 off-ramp 커넥터였고, 정답이
`detector_local_mapping.off_ramp_connectors` 에 `from_link` 로 **이미 있었다**.
감사 BFS 가 그 파일을 안 봤다. BFS 는 이미 `stop_owners` 로 같은 제외를 한다(:517).

사용자가 망에서 직접 확인한 값과 매핑이 일치했다 — **10645 → FW:26, 10682 → FW:2**.

게이트를 "질량을 나르는 링크에 tie 가 없다" 로 바꿨다. 미측정은 통과가 아니므로 관측이
없으면 NOT_EVALUATED 이고 PASS 는 실 런 감사에서만 나온다. 커버리지 요건도 넣었다
("관측돼서 0" 과 "관측 안 됨" 을 가른다).

**감사 FAIL 2 → 0 (PASS 12 / NE 16).**

## 봐 달라

1. **off-ramp 를 BFS 에서 빼는 것이 정당한가.** 나는 "소유자가 선언됐으니 `stop_owners` 와
   같다" 고 봤다. 반론이 가능하다 — off-ramp 는 정지선 소유자가 아니다.
2. **`promotion_readiness` 가 FAIL → NOT_EVALUATED 로 바뀐 것**이 승격 안전성을 낮추지 않는가.
   NE 는 통과가 아니므로 여전히 막히지만, FAIL 이 사라져 눈에 덜 띈다.
3. **남은 27건**은 관측 차량이 0 이라 PASS 하는데, 관측이 넓어지면(N5/N9) 다시 터질 수 있다.
   그것이 의도다. 정말 그렇게 동작하는지 확인해 달라.

---

# 5. N8-3 병렬 정렬이 직렬의 동점 선택을 바꾸고 있었다 (고침)

**확신도 — 높음. 되돌림으로 확인했다.**

이번 회차에 들어간 `results.sort(key=item.index)` 의 주석이 "직렬은 무영향" 이라고
못박았는데 **거짓**이었다. `_prefilter_leader_candidates` 가 `selected` 를 proxy 랭킹
순서로 쌓으므로(`stackelberg_mpc.py:2020-2036`) 직렬 결과 순서는 인덱스 순서가 아니었고,
정렬 한 줄이 **직렬의 동점 선택도 5 → 2 로 바꿨다.**

기존 검사가 못 잡은 이유가 중요하다 — `test_parallel_determinism.py` 가 `selected_indices`
로 `list(range(n))` 을 넘겨 **prefilter 재정렬을 우회**했다.

정본 순서를 `selected_indices` 순서로 잡았다. 직렬이 내던 순서이고 flagship override
(`stackelberg_wu_metered.py:2782-2790`)가 정렬 없이 내는 순서와도 같다.

## 봐 달라

- **아직 안 닫힌 것이 하나 있다.** `stackelberg_mpc.py:2116` 이 병렬 payload 의
  `incumbent_obj` 를 seed 직후 값으로 고정하고 `:2119` 만 후보마다 조인다. 조기종료가
  걸리는 상태에서는 후보 목적함수가 worker 수에 따라 달라질 수 있고, 이는 계획의
  "차이 ≤ 1e-9" 위반 후보다. **아무도 재현 상태를 못 만들었다.**

---

# 6. N10 매트릭스 배선 (고침)

**확신도 — 높음. 다만 부작용이 있다.**

N10 이 감사 게이트를 18→28 로 늘렸는데 `run_plant_fidelity_matrix.ps1` 이 새 산출물 인자를
하나도 안 넘기고 `--required-gate` 에도 새 게이트가 0개였다. 매트릭스를 돌리면 10개가
전부 NOT_EVALUATED 로 조용히 지나간다.

산출물 5개를 넘기고 요구 게이트를 15 → 22 로 늘렸다. 나머지 6개는
`$matrixUnavailableGates` 로 **명시**했고, "모든 게이트는 요구되거나 불가로 선언돼야 한다"
를 검사로 강제했다.

## 봐 달라

**다음 매트릭스 런은 새로 요구한 7개가 PASS 하지 않으면 실패한다.** 의도한 fail-closed 지만,
특히 이 셋이 실 런에서 정말 PASS 하는지 확인이 필요하다.

- `signal_com_readback` — 러너가 `signal_readback.csv` 를 쓴다(vbs:247)는 것만 확인했다
- `mass_conservation` — `projection_diagnostics` 에서 나온다고 봤다
- `runtime` — `decision_wall_sec` 표본에서 나온다고 봤다

셋 다 **실 런 산출물로 검증 안 했다.**

---

# 7. 설계 판단 (B) — 구현했다가 되돌렸다

**확신도 — 변경 자체는 옳다고 본다. 되돌린 것은 절차 문제다.**

`_phase_green_fraction` 이 config 상수 `cycle_length`(120)로 나누는데, 모델은 이미
`cycle_length == p1 + p2 + lost_time` 을 항등식으로 주장하고 `metrics.py` 가 위반을 센다.
액션이 녹색 예산면을 벗어나면 **모델이 자기 항등식을 어긴다.**

실측 — 액션 아카이브 31,020 표본에서 **예산면(p1+p2=110) 위 액션이 0건**이다.
114(94.7%, +3.33%), 100(4.0%, −8.33%), 95(1.3%, −12.50%).

**중요 — 제어 런에서 native 주기는 재생되지 않는다.** 러너가 15 SC 의 모든 SG 에
`ContrByCOM = True` 를 걸어 inpx 프로그램을 통째로 우회한다
(`evaluation/controllers/plant_cycle.py:18-23`). 그래서 `cycle_length_by_signal` 에
native 주기를 채우는 것으로는 간극이 안 닫힌다. 계획서의 "N4-1 과 정면충돌" 은 과장이다.

되돌린 이유 — `test_cycle_green_budget_accounting` 이 통째로 무효가 된다(10 subtest).
그 파일은 "매핑을 채우면 무엇이 깨지는가" 를 측정하는데 이 변경이 그 깨짐을 없앤다.
역설적이지만 **그 파일 docstring 이 이 변경과 같은 주장을 한다.**

## 봐 달라

- 이 변경을 N현시 일반형 `C = Σ gᵢ + lost_time` 으로 다시 하는 것이 맞는지
- `test_cycle_green_budget_accounting` 을 어떻게 다시 쓸 것인지

---

# 8. 계획서에서 정확하지 않은 것으로 드러난 문장들

| 계획서 문장 | 실측 |
|---|---|
| "제어 15 SC, SG **128**개" | **136** (타이밍 표가 틀린 `.sig` 를 읽었다) |
| "이름 규칙 동시녹색 **160** 쌍, 최악 **5.00배**" | **222 쌍, 5.47배** |
| "native 주기 100/140/150/160/170" | **140/150/160/170** (100 은 잘못 읽은 SC6) |
| "N4-3 미해결 304건 — 잔차 뭉개기가 아니라 **구조적 부재**" | 결론은 맞으나 원인 진단이 틀렸다. `grid_node_legs` 의 boundary leg 에 **`in_link` 칸이 없어서** 조인될 수 없었다 |
| "N4-5 예산면 밖 **8.3% 과대**" | 재현되지 않는다. 실측은 +3.33% 이고 부호·크기가 다르다 |

**계획서에 적힌 진단도 근거를 다시 열어봐야 한다는 것이 이번 회차의 교훈이다.**

---

# 9. 내가 이번 회차에 틀렸던 방식 — 같은 함정을 조심해 달라

진단을 **네 번** 뒤집었다. 매번 원인이 같았다.

1. **잘못된 표를 봤다.** urban 저장 표(도시부 전용)로 "tie 33건 전부 질량 0" 이라 단정 →
   실 관측에서 중앙값 1.68%, 개별 최대 58 veh 를 나르고 있었다.
2. **계획서 문장을 근거로 썼다.** "구조적 부재" → 실제로는 스키마에 칸이 없는 것.
3. **작업량을 추정했다.** "(B) 는 검사 2건이면 끝" → 모듈 하나가 통째로 무효.
4. **쓰이지 않는 코드 경로를 쟀다.** `DemandProfile` 의 등차수열 397,800 veh/h 를 보고
   14배라 놀랐는데, 결합 런은 그 경로를 안 쓴다.

**4번이 특히 위험하다.** 값을 재기 전에 "그 값이 실 런에서 쓰이는가" 를 먼저 봐야 한다.

---

# 10. 아직 안 정해진 설계 판단

## (가) 총량 3.66배를 어떻게 고칠 것인가

- 어댑터가 `urban_vph × N입력 / N게이트` 를 쓰기, 또는
- 러너가 평균 대신 총량을 넘기고 어댑터가 나누기, 또는
- 격자를 실제 입구 22개로 재정렬해 자연히 맞추기

**러너-어댑터 규약이 어디에도 문서화돼 있지 않은 것**이 근본 원인이다. `demand` 필드가
"지점당 평균" 인지 "총량" 인지 적힌 곳이 없다.

## (나) 격자 재정렬 범위

실제 입구 22곳만 남기면 `grid_node_legs` → `boundary_in_links` → `urban_movements`(1,414)
가 바뀌고, `canonical_topology_v3` · `physical_stock_topology_v2_1` ·
`topology_approval_v2_1` 재생성, `parent_runs_v3`(봉인 `27aab945…`) 와
`experiment_matrix_v3`(봉인 `d397fa07…`) 재봉인까지 연쇄한다.

아직 실 런을 안 돌렸으므로 **지금이 바꿀 수 있는 마지막 시점**이다.

## (다) N9 를 어떻게 쪼갤 것인가

행렬은 development 1,080 / holdout 540 으로 이미 나뉘어 있다. H=1 은 독립 게이트다.

| 구간 | 셀 | 벽시계(직렬) | 4병렬 |
|---|---:|---:|---:|
| H=1 development | 216 | 0.5~0.6일 | 2.5~3시간 |
| development 전체 | 1,080 | 3.2~3.6일 | 0.8~0.9일 |
| 전체 runnable | 1,620 | 4.8~5.4일 | 1.2~1.4일 |

**플랜트가 얼기 전에 holdout 540 을 열면 안 된다.** 한 번 보면 더 이상 holdout 이 아니다.

솔브가 VISSIM 보다 3~6배 크다(제어 결정 97.5h 대 시뮬 16.6~33.1h). 결정당 중앙값 9.94s,
워밍업 0.16s 다. 셀 1,620개는 서로 독립이라 **셀 바깥 병렬**이 안전하다 —
solve 안쪽 병렬은 flagship override 가 follower 주입을 잃어(`stackelberg_wu_metered.py:2767`)
물리가 바뀐다.
