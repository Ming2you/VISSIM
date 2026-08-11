# Codex 재검토 요청 — v3 구현계획 단계별

> `IMPLEMENTATION_PLAN_V3_LEAN.md` 의 N0~N10 순서대로, **각 단계에서 무엇을 했고 지금
> 어떤 상태인지**를 적었다. 각 단계 끝의 **[검토]** 가 Codex 에게 확인을 요청하는 지점이다.
>
> 나는 이번 회차에 **진단을 네 번 뒤집었다**(9절). 여기 적힌 것도 틀렸을 수 있으니
> 인용이 아니라 **직접 재현**해 달라.

- VISSIM `codex/plant-fidelity-v2-1` — `d6bfbd0..93d7ab4`
- NumSim `freeway-zone-followers` — `5a2fe7d..e4bf4d0`
- vendor 앵커 = 상류 `e4bf4d0`

**표기** — ✅ 계획 PASS 충족 / ⚠️ 부분 / ❌ 미충족 / ⛔ 실 런 필요 / 🔍 내가 확인 못 함

## 실행 환경

```
python  C:/Users/alsrj/AppData/Local/Programs/Python/Python313/python.exe
        ('python' 은 Windows Store 스텁, exit 49)
pytest 없음 → python -m unittest <module.path>
plant/tests 는 cwd=VISSIM/plant + PYTHONPATH=VISSIM저장소루트 를 **둘 다** 요구
scripts/tests · tests/ 는 패키지가 아니라 discover 안 됨 → 모듈 명시
```

기대 — `scripts/tests` 480/480, `tests/` 124/124, `plant/tests` 132/132 OK.
NumSim 기존 실패 10건이 baseline(forecast_awareness 5, post_analysis 2,
segment_local_plant 2, wu_faithful_follower 1). `test_rl_ddqn` torch 없음,
`test_six_controller_comparison` 45분 초과로 미실행.

---

# N0. 토폴로지 정합과 고정 — P0

**계획 PASS** — preflight `status=PASS` reasons 0 / state selection 4/4 /
`validate_physical_stock_topology` 구조 오류 0.

**상태 ✅ (이번 회차 재생성)**

vendor 재앵커 후 승인 사슬 3단을 다시 돌렸다.

```
verify_runtime_source.py       → status=PASS
build_preflight_manifest.py    → status=PASS, fingerprint abd5ba24...
approve_physical_stock_topology.py → status=PASS, hash 41d64c9c...
```

감사 게이트 `canonical_topology` PASS — `inpx_sha256` 가 감사 대상 망과 일치.

**[검토]**

1. 사슬 3단을 직접 재실행해 같은 fingerprint/hash 가 나오는지. `RW_PYTHON_EXE` 환경변수가
   필요하다.
2. **N0 는 "토폴로지 정합" 인데, 그 토폴로지가 VISSIM 망과 정말 같은가.** 아래 N4-2/N5 에서
   드러난 대로 모델 격자에 **VISSIM 에 없는 경계 게이트 약 95개**가 있다. N0 의 승인
   아티팩트가 그것을 통과시킨 이유를 봐 달라 — 검사 범위 밖인지, 아니면 놓친 것인지.

---

# N1 / N1a / N1b. 차량단위 초기상태 투영 — P0

**계획 PASS** — 61/61 스냅샷 배정 100%, 잔차 ≤1e-6 veh, 항등식 성립.

**상태 — N1a ✅(이전 회차) / N1b ⛔ N8-4 대기**

N1b(MPC 캡처 61회)는 N8-4 런타임 계약 충족 후에 돌린다. **미착수.**

**[검토]** 이번 회차에 손대지 않았다. N1a 의 61/61 을 재현할 수 있는지만 확인해 달라.

---

# N1.5. vendor 스냅샷 재앵커 파이프라인 — P0

**계획 PASS** — 스냅샷에 돌려 앵커 값이 완전히 동일하게 재현.

**상태 ✅ (이번 회차 실행)**

`5a2fe7d → e4bf4d0`, 115 파일. 상류 5커밋을 실 런 경로에 반영했다.

**중요 — 재앵커 전까지 실 런의 NumSim 층은 5곳에서 endpoint 를 우회했다.**
`stage2_mechanism:133`, `centralized_mpc:299/328`, `distributed_coordinator:673`,
`wu_distributed:862`. 상류만 고치고 vendor 를 안 옮기면 N7 은 실 런에서 미완이다.

앵커 상수는 **3파일 11개**다(`verify_runtime_source.py` 5, `validate_baseline_snapshot.py` 5,
`build_preflight_manifest.py` 1). 계획서에 6개로 적혀 있던 것이 이전 회차에 정정됐다.

**[검토]**

1. 지금 vendor 의 `run_coupled_interval` 직접 호출이 2곳(`rollout_endpoint.py:295` 본체,
   `simulation/simulator.py:33` 플랜트 전진)뿐인지. 그 둘은 우회가 아니다.
2. 앵커 상수 11개가 전부 `e4bf4d0` 를 가리키는지.

---

# N2. substep 질량 장부 — P0

**상태 ✅ (이전 회차)**

전역 항등식 `N_close = N_open + accepted_external − sink_out`.
109 시나리오 × 24 스텝, 최대 잔차 **6.7e-12 veh**.

이 과정에서 두 결함을 찾아 고쳤다 — off-ramp storage 를 urban/freeway 어느 쪽도 안 세던
누수(35.46 veh), `boundary_out` 게이트가 링크 주행을 건너뛰던 것(3,691.07 veh).

**[검토]** `src/tests/test_global_mass_conservation.py` 를 돌려 잔차가 재현되는지.
그 파일에 **되돌림 증명**(`test_pre_fix_measure_breaks_the_identity`)이 들어 있다.

---

# N3. 관측 확장 — P0/P1

**계획 PASS** — N3-1 통행 중앙값 ≤5s p95 ≤15s 큐꼬리 MAE ≤20m /
N3-2 출구 커버리지 119/119 잔차 ≤1e-6 / N3-3 램프 커넥터 누락·중복 0.

**상태 — N3-1a ✅ / N3-1b ✅ / N3-2 ✅ (이전 회차) / N3-3 🔍**

**[검토]** N3-3 은 이번 회차에 안 봤다. 상태를 확인해 달라.

---

# N4. N현시 신호 — P0 ★ 이번 회차 변화 큼

## N4-1. SC별 고유 주기

**계획 PASS** — 정확 커버리지 100%, unresolved vehicle mass 0.

**상태 ⚠️ 배관은 있고 매핑은 의도적으로 비어 있음. 그런데 정본표가 틀린 `.sig` 를 읽고 있었다.**

`derive_signal_group_timing._sig_path_for` 가 **파일명 끝자리 번호**로 `.sig` 를 골랐는데
VISSIM 은 inpx 의 `signalController/@supplyFile2` 를 읽는다. **4/15 SC 가 달랐다.**

```
SC5  timing=test-bed5.sig(140s)  inpx=test-bed7.sig(160s)
SC6  timing=test-bed6.sig(100s)  inpx=test-bed9.sig(160s)
SC11 timing=test-bed11.sig(160s) inpx=test-bed3.sig(150s)
SC12 timing=test-bed12.sig(150s) inpx=test-bed5.sig(140s)
```

**수치가 바뀌었다.**

| | 계획서 | 실측(정정 후) |
|---|---:|---:|
| SG 수 | 128 | **136** |
| 이름규칙 동시녹색 쌍 | 160 | **222** |
| 최악 녹색 과대 | 5.00배 | **5.47배** |
| native 주기 | 100/140/150/160/170 | **140/150/160/170** |

즉 2현시 근사의 오차가 보고돼 있던 것보다 **39% 크다**. 감사 `signal_timing_canon` FAIL→PASS.

체인(timing → movement map → actuation plan → sgplan.vbs → 감사)을 전부 재생성했다.
그 과정에서 **커밋돼 있던 `sgplan.vbs` 가 계획 산출물과 어긋난 채**였음을 발견했다 —
기존 검사가 집계(SG 수·창 수·충돌 쌍 수)만 봐서 sha 드리프트를 못 잡았다. 원본 sha 대조를 추가했다.

**[검토]**

1. `derive_signal_group_timing.py` 를 재실행해 **136 / 222 / 5.47배**가 나오는지.
2. **222 쌍 중 실제로 동시녹색이 되는 것은 몇 개인가.** 나는 "이름 규칙이 만드는 쌍" 을
   셌을 뿐, N4-5 가 축 안 분배를 닫은 뒤 러너가 실제로 동시에 녹색을 주는지는 **확인 안 했다.**
3. `cycle_length_by_signal` 을 채우지 않는 것이 맞는지. **제어 런에서 native 주기는
   재생되지 않는다** — 러너가 15 SC 의 모든 SG 에 `ContrByCOM = True` 를 걸어 inpx
   프로그램을 통째로 우회한다(`evaluation/controllers/plant_cycle.py:18-23`). 그렇다면
   계획서의 "native 주기를 채운다" 는 항목 자체가 제어 런에서는 성립하지 않는다.

## N4-2. movement / SG 매핑

**상태 ⚠️ 부분 — 698 중 416 해결, 282 미해결(전부 `synthetic_boundary_leg`)**

미해결 282건의 원인을 이번에 찾았다. **계획서의 "구조적 부재" 는 결론만 맞고 원인 진단이 틀렸다.**

`grid_node_legs` 의 boundary leg 구조가 이렇다.

```json
"N": { "type": "boundary",
       "in":  "in_SC1_N",        ← 유입 게이트 (VISSIM 링크 없음)
       "out": "out_SC1_N",
       "out_link": "SC1_N_out"   ← 유출만 링크 칸이 있다 }
```

**유입은 `in_link` 칸 자체가 없어서** 조인될 수가 없었다. `boundary_link_to_queue` 도 0 항목이다.
표가 안 채워진 게 아니라 채울 자리가 없다.

**[검토]**

1. `in_link` 를 추가하는 것이 옳은 방향인지, 아니면 아래 N5 의 격자 재정렬로 흡수되는지.
2. `link_to_origins` 의 유출 매핑이 **방향을 구분하지 않는다** — SC1 의 4개 링크가
   각각 `N_out`/`S_out`/`E_out`/`W_out` **넷 다**를 가리킨다. 이것이 의도인지.

## N4-3. N현시 녹색분율

**계획 PASS** — N=2 경로 bit-identical, SC별 주기 재구성 오차 0,
native production 에서 **scalar-cycle fallback 0**.

**상태 ⚠️ 부분 — 기구는 동작, 미해결 282건 때문에 PASS 불가**

`share(m) = union_green(m의 SG) / union_green(축의 SG)`. N=2 면 정확히 1.0(비트동일).
효과는 실재한다 — SC1001 movement 54개 중 21개 분율 변경, 실측 대비 **1.56배/1.21배 →
1.01배/0.97배**. 질량 보존은 N4-1·N4-3 동시 적용에서 24스텝 잔차 1.148e-11 veh.

**[검토]** PASS 조건 "scalar-cycle fallback 0" 은 282건이 있는 한 구조적으로 달성 불가다.
조건을 좁힐 것인지(SG 가 있는 movement 한정), 아니면 282건을 해소할 것인지 판단이 필요하다.

## N4-4. monitor 26개 고정 타임라인

**상태 ✅ (이전 회차)** — 조용한 폴백 4곳이 전부 `MonitorFixedSignalPatchError`.

## N4-5. action 스키마 fail-closed

**상태 ⚠️ 축 안 분배는 닫았고 예산면 밖은 열려 있음**

축 녹색의 단조 재매개화로 축 창을 SG 별로 쪼갠다. SG g 의 realize 녹색이
`지시 축 녹색 × union_green(g) / union_green(축)` 이 되어 모델 share 와 같은 분수다.

**계획서의 "예산면 밖 8.3% 과대" 는 재현되지 않는다.** 실측은 이렇다.

액션 아카이브 31,020 표본에서 **녹색 예산면(p1+p2=110) 위 액션이 0건**이다.

| p1+p2 | 비중 | 플랜트 주기 | 모델 120 대비 |
|---:|---:|---:|---:|
| 114.0 | 94.7% | 124.0 s | **+3.33%** |
| 100.0 | 4.0% | 110.0 s | **−8.33%** |
| 95.0 | 1.3% | 105.0 s | **−12.50%** |

`lost_time` 을 8→10 으로 올려 모델 주기와 러너 합성 주기를 같게 만든 것이 이번 회차 변경이다.
예산면 위에서는 0.0% 로 닫힌다. 다만 **그 예산면에 앉은 액션이 아직 하나도 없다** —
`lost_time` 변경 후 실 런을 안 돌렸다.

**[검토]**

1. 114 가 94.7% 인 것은 진단용 `fixed-57/57` 이 컨트롤러를 우회한 것인지 확인.
2. 생산 컨트롤러가 정말 `p2 = effective_green_total − p1` 로 예산면을 지키는지
   (`distributed_coordinator:1250`, `structured_grid:43` 등).
3. **생산 config 의 상자/예산 불일치** — `lost_time` 10 이면 예산 110 인데
   `green_min + green_max = 20 + 92 = 112` 를 그대로 뒀다. `green_max = 92` 는 도달 불가능한
   죽은 값이다.

## N4-6. 신호 timing oracle (D-core) — P1

**계획 PASS** — 전이 시각 오차 ≤0.5s, request/readback 불일치 0.

**상태 ⛔ BLOCKED — 판정기는 완성, 게이트를 못 넘는다**

**양자화 0.99s 가 게이트 0.5s 를 넘는다.** 이것이 선결 조건이다.

**[검토]** 0.99s 와 0.5s 가 각각 어디서 오는지, 코드로 닫을 수 있는지 설계 판단인지.
나는 추적 못 했다.

## N4-7. offset 승격 잠금 — P1

**상태 ⛔ 잠김** — D-core PASS + N9 효과/순위 + N8-4 런타임이 모두 PASS 해야 열린다.
N9 행렬의 **offset 레버 540셀이 BLOCKED** 다.

**[검토]** 모델은 p1-first 인데 플랜트는 major-first 이고, 제어 15 SC 중 **14곳이
`major_maps_to = "p2"`** 다. offset 이 0 이라 지금은 안 터지지만 승격 전에 반드시 짝지어야 한다.
나는 이것을 확인만 하고 손대지 않았다.

---

# N5. 개발 데이터와 잡음 바닥 — P0 ★★ 최우선 검토

**계획 PASS** — 부모 9/9, anchor 완비, 누락·중복 0, base replay 부모-anchor 당 ≥20.

**상태 ⛔ 미실행. 그런데 실행 전에 고쳐야 할 것을 찾았다.**

## 발견 — 모델이 도시부 수요를 3.66배 주입한다

러너는 VISSIM 도시부 유입의 **지점당 평균**을 state 에 쓴다.

```vbscript
' scripts/run_real_world_stackelberg_controller.vbs:2950
demandUrbanBySec(key) = CDbl(urbanSumBySec(key)) / CDbl(urbanNBySec(key))
```

어댑터는 그 평균을 **경계 게이트 117개 전부**의 값으로 읽는다.

```python
# evaluation/controllers/vissim_stackelberg_adapter.py:2814
urban_boundary = {str(link): urban_vph
                  for link in list(cfg.network.boundary_in_links)
                             + list(cfg.network.boundary_out_links)}
```

유입 지점 32개 대 게이트 117개 → **117/32 = 3.66배.**

| timeInt | VISSIM 실제 | 모델 주입 | 배율 |
|---|---:|---:|---:|
| 1 0 | 12,747 veh/h | 46,607 | 3.66 |
| 1 900000 | 18,209 | 66,577 | 3.66 |
| 1 1800000 | 19,120 | 69,909 | 3.66 |
| 1 2700000 | 16,389 | 59,922 | 3.66 |
| 1 3600000 | 12,747 | 46,607 | 3.66 |
| 1 4500000 | 9,106 | 33,292 | 3.66 |

여섯 구간 전부 배율이 같다. **구조적이다.**

시간 프로파일은 이미 inpx 에 앵커돼 있다(`real_world_inpx_time_profile`). **공간 분포만
안 돼 있다.** VISSIM 은 양재 EB/NB 에 1,400 veh/h 를, Dummy Link 9 에 63 을 넣는데 모델은
둘을 같게 본다.

## 발견 — 모델 격자가 VISSIM 망과 다르다

VISSIM 도시부 vehicle input 32개 분류(dummy = 내부 발생은 **사용자 확정**).

| 종류 | 개수 | peak 합 | 모델 격자 상태 |
|---|---:|---:|---|
| named(실제 위치) | 14 | 10,361 veh/h | leg없음 13, grid 1 — **전부 안 맞음** |
| unnamed | 8 | 6,533 | boundary 5 OK, leg없음 2, 노드없음 1 |
| dummy(내부 발생) | 10 | 2,226 | 경계 아님 |

진짜 망 입구 = **22개, 16,894 veh/h**. 모델이 제대로 아는 것은 **5개뿐**이다.
반대로 모델은 게이트를 117개 갖고 있어 **약 95개가 VISSIM 에 대응물이 없다.**

**즉 모델 격자가 VISSIM 망보다 좁으면서 동시에 넓다** — 실제 입구 17곳을 모르고,
없는 입구 95곳을 갖고 있다.

## [검토] — 여기가 제일 중요하다

1. **주입 지시값이 실제로 다 들어가는가.** `urban_boundary` 는 도착률 *지시값*이다.
   하류 용량·게이팅에서 잘리면 실효 유입은 3.66배가 아닐 수 있다.
   `urban_demand_arrivals_veh` 실측과 대조해야 한다. **나는 안 해봤다.**
2. **freeway 에도 같은 구조가 있는가.** 러너가 `freewaySumBySec / freewayNBySec` 로
   똑같이 평균을 내고(vbs:2952) 어댑터가 `{link: freeway_vph for link in freeway_links}`
   로 뿌린다. **같은 모양인데 확인 안 했다.** freeway_links 수와 VISSIM freeway 입력
   수(2)를 비교해 달라.
3. **`boundary_out_links` 119개도 같은 값을 받는다.** 어댑터 주석은 "boundary_out links
   are not used as exogenous arrivals" 라는데 정말 그런지.
4. **`_scaled` 프로파일의 `roleMultipliers`**(vbs:2933-2935)가 배율에 어떻게 얹히는지.
5. **`link_leg` 의 방위 규약이 모델 격자와 같은 좌표계인가.** 나는 문자열만 비교했다.
   `link_leg` 의 `NE` 와 `grid_node_legs` 의 `NE_SC2` 가 같은 방위인지 확인해 달라.
   **다르면 "27개가 대각선이라 안 맞는다" 는 전부 무효다.**
6. **정방향 패딩 게이트 95개가 언제 왜 들어왔는지** git 이력 추적. 의도가 있었다면 내
   "패딩" 판정이 틀렸다.

## N5 실행 전 결정해야 할 것

- **표본 사이징** — N6 는 표본 ≥200, 포화 lane-group ≥30, CI 반폭 ≤10% 를 요구하는데
  현 자료는 **표본 177 로 미달**이다. N5 명세(부모 9개 + anchor 당 replay 20)가 200 을
  넘기는지 계산이 필요하다. 못 넘기면 N5 를 다시 돌려야 하므로 **런 전 판단**이다.
- 위 수요 3.66배를 고치고 돌릴 것인가.

---

# N6. 캘리브레이션 — P1

**계획 PASS** — split 중복 0, 포화 독립 lane-group ≥30, 표본 ≥200, CI 반폭 ≤10%.

**상태 ⛔ 미실행 — 현 자료 표본 177, CI 없음**

검증기(`validate_physical_stock_calibration.py`)는 이번 회차에 기존 자료에 돌려
FAIL 11 을 진단했다(이전 회차).

**[검토]** N5 산출물이 200 표본을 만들 수 있는지 사전 계산.

---

# N7. production MPC rollout endpoint — P0

**계획 PASS** — 채널 커버리지 100%, endpoint 호출 수 = 후보 평가 수, **우회 호출 0**.

**상태 ✅ 상류·어댑터 0 / ⚠️ 하네스 1곳**

`run_coupled_interval` 직접 호출 전수 계수(정의 호출부 제외).

| 범위 | 우회 |
|---|---:|
| 상류 `NumSim-mine/src/`(테스트 제외) | **0** |
| VISSIM `evaluation/` | **0** |
| VISSIM `harness/` | **1** — `harness/g6/g6_core.py:371` |
| vendor 스냅샷 | **0** (재앵커 후) |

**[검토]**

1. `g6_core.py:371` 이동이 동작 보존인지. 조사 결과 `demand_from_state` 가 정확히 H 개를
   전부 같은 값으로 내므로(`adapter:3029`) 클램프가 발화하지 않고 시간 누적도 산술 동치다.
   보류 근거가 과보수적이었다는 것이 내 판단인데 확인 필요.
2. 재앵커 전 vendor 5곳 우회가 실 런에 어떤 영향을 줬는지 — 이전 실 런 산출물은 그 상태에서
   나온 것이다.

---

# N8. marginal price 와 런타임 — P0

## N8-1. exact FD 대 SPSA 자격심사

**상태 ❌ 미착수 — 하네스가 없다**

`eps_J_endpoint` 를 재는 하네스가 없어 계획 PASS 조항
(`exact-FD 재채점 regret < max(2·eps_J_endpoint, 0.5%·|J_FD|)`)을 판정할 수 없다.

**[검토]** **N5 의 `eps_J_vissim` 을 여기 쓰면 안 된다** — 하한이 세 자리 다르다.
이 구분이 코드로 강제돼 있는지 확인해 달라.

## N8-2. 결정 동등성

**계획 PASS** — 상태·feasibility·안전 인증서·fallback 등급·리더 후보 36/36 정확 일치.

**상태 ⚠️ 판정 불가**

holdout anchor 12 상태가 실 런 산출물이고 N8-1 하네스가 없다. 그리고 실측에서
**계획 PASS 두 조항("명령 양자화 1단계 허용" + "상태 정확 일치")이 논리적으로 함께
성립하지 않는다**는 것이 드러났다.

**[검토]** 계획 문안 자체를 고쳐야 하는지.

## N8-3. 통합 rollout 스케줄러

**계획 PASS** — workers 0/1/2/5 에서 목적함수·가격 차이 ≤1e-9, 선택 action 정확 일치.

**상태 ⚠️ 결정성 한 조각만. 본체(deadline-aware 스케줄러·timeout/cancel)는 미구현.**

이번 회차에 넣은 `results.sort(key=item.index)` 의 주석이 "직렬은 무영향" 이라고
못박았는데 **거짓이었다.** `_prefilter_leader_candidates` 가 `selected` 를 proxy 랭킹
순서로 쌓으므로(`stackelberg_mpc.py:2020-2036`) 직렬 결과 순서는 인덱스 순서가 아니었고,
정렬 한 줄이 **직렬의 동점 선택도 5 → 2 로 바꿨다.**

기존 검사가 못 잡은 이유 — `test_parallel_determinism.py` 가 `selected_indices` 로
`list(range(n))` 을 넘겨 **prefilter 재정렬을 우회**했다. 실배선에서 prefilter 는 항상 켜져 있다.

정본 순서를 `selected_indices` 순서로 정했다. 직렬이 내던 순서이고 flagship override
(`stackelberg_wu_metered.py:2782-2790`)가 정렬 없이 내는 순서와도 같다.

**[검토]**

1. **아직 안 닫힌 것** — `stackelberg_mpc.py:2116` 이 병렬 payload 의 `incumbent_obj` 를
   seed 직후 값으로 고정하고 `:2119` 만 후보마다 조인다. 조기종료 상태에서 후보 목적함수가
   worker 수에 따라 달라질 수 있고, 이는 "≤1e-9" 위반 후보다. **아무도 재현 상태를
   못 만들었다.**
2. **solve 병렬화는 켜면 안 된다** — flagship override 가 module-level worker 를 우회하는
   이유가 성능이 아니라 **follower 주입 소실**이다(`stackelberg_wu_metered.py:2767`).
   워커를 켜면 `WuFaithfulFollower` 가 기본 `NashSolver` 로 조용히 바뀐다.

## N8-4. 런타임 계약

**계획 PASS** — stratum 별 p95 ≤30s, 관측 최대 ≤45s, fallback <5%, timeout <1%.

**상태 ⛔ 실 런 필요. 실측 여유는 크다.**

실 런로그 실측 — 제어 결정 **중앙값 9.94s / p95 11.2s**, 워밍업 결정 0.16s(62배 차).
계약 30s 대비 여유 3배.

**[검토]** 계획서에 "결정당 300초" 라고 적혀 있던 것은 **근거 없는 값**이었다(이전 회차
정정). 지금 문서에 남은 값이 실측인지 확인해 달라.

---

# N9. 짝지은 VISSIM 검증 — P1

**상태 ⛔ 미실행. 명세는 봉인 완료.**

행렬 봉인 `d397fa07d1c05692` — 2,160 셀 / runnable 1,620 / BLOCKED 540(offset).

## 규모 실측 정정

계획서의 "8~9일" 은 **워밍업 틱을 전부 풀 solve 로 센 값**이다. 실측으로 다시 잡으면 이렇다.

| 항목 | 계산 | 벽시계 |
|---|---|---:|
| 제어 결정 solve | 35,316 × 9.94s | **97.5 h** |
| 워밍업 틱 | 24,300 × 0.16s | 1.1 h |
| VISSIM 시뮬 | 993.6 h ÷ 30~60배속 | 16.6~33.1 h |
| **합** | | **115~132 h ≈ 5~5.5일** |

**solve 가 VISSIM 보다 3~6배 크다.** 결합 루프에서 우리가 푸는 동안 VISSIM 은 멈춰 있어
두 값이 더해진다.

## 쪼개기 — development / holdout 이 이미 나뉘어 있다

| 구간 | 셀 | 시뮬 h | 직렬 | 4병렬 |
|---|---:|---:|---:|---:|
| **H=1 development** | **216** | 111.6 | 0.5~0.6일 | **2.5~3시간** |
| development 전체 | 1,080 | 662 | 3.2~3.6일 | 0.8~0.9일 |
| holdout | 540 | 331 | 1.6~1.8일 | 0.4일 |

계획이 **"H=1 은 독립 게이트다. 다른 H 로 구제하지 않는다"** 고 못박았다. 한 스텝도 못
맞히면 나머지를 볼 필요가 없다. **H=1 development 216셀이면 반나절**이다.

**[검토]**

1. **holdout 540 은 플랜트가 얼기 전에 열면 안 된다.** 한 번 보면 더 이상 holdout 이 아니다.
   이 규율이 코드로 강제돼 있는지.
2. **부분집합 실행이 봉인을 깨는가.** 내 판단은 아니다 — 봉인은 결과를 보고 명세를 바꾸는
   것을 막는 장치이고, 미리 정한 순서로 부분집합을 돌리는 것은 명세 변경이 아니다.
   development 를 보고 플랜트를 고치는 것은 development 데이터의 용도 그 자체다.
3. **셀 바깥 병렬이 안전한가.** 1,620 셀은 독립 프로세스라 구조적으로 결정을 못 바꾼다.
   solve 안쪽 병렬과 달리 증명할 필요조차 없다는 것이 내 판단.
4. 위 N5 의 수요 3.66배가 안 고쳐지면 N9 합격 게이트(NMAE ≤15%, TTT APE ≤10%)는
   통과할 수 없다고 본다. 동의하는지.

---

# N10. 감사와 승격 — P1

**상태 — 게이트 28개, overall FAIL→NOT_EVALUATED (PASS 12 / FAIL 0 / NE 16)**

## 이번 회차 변경 넷

**(1) 게이트 18 → 28 확장 + `BLOCKED` 상태 추가.**
BLOCKED 는 "아직 안 쟀다" 가 아니라 "잴 수 없다" 이고 NOT_EVALUATED 보다 나쁘다.

**(2) 매트릭스 러너 배선.** N10 이 게이트를 늘렸는데
`run_plant_fidelity_matrix.ps1` 이 새 산출물 인자를 하나도 안 넘기고 `--required-gate` 에도
새 게이트가 0개였다. **매트릭스를 돌리면 10개가 전부 NOT_EVALUATED 로 조용히 지나간다.**

산출물 5개를 넘기고 요구 게이트를 15 → 22 로 늘렸다. 나머지 6개는
`$matrixUnavailableGates` 로 **명시**하고, "모든 게이트는 요구되거나 불가로 선언돼야 한다"
를 검사로 강제했다.

**(3) `assignment_ties` 를 질량 기준으로 재정의.**
33건 tie 중 차를 싣는 6건이 전부 off-ramp 커넥터였고, 정답이
`detector_local_mapping.off_ramp_connectors` 의 `from_link` 에 **이미 있었다.** 감사 BFS 가
그 파일을 안 봤다. 사용자가 망에서 직접 확인한 값과 매핑이 일치했다 —
**10645 → FW:26, 10682 → FW:2.**

게이트를 "질량을 나르는 링크에 tie 가 없다" 로 바꿨다. 관측이 없으면 NOT_EVALUATED 이고
PASS 는 실 런 감사에서만 나온다. 커버리지 요건도 넣었다("관측돼서 0" 과 "관측 안 됨" 을 가름).

**(4) 통과할 수밖에 없던 검사 정정.** `uncovered_signal_groups` 가
`sg_no not in window_counts` 인데 `window_counts` 가 같은 목록으로 초기화돼
**구조적으로 항상 0** 이었다. 의미 있는 정의로 바꿨다(실측은 여전히 0 —
실질은 멀쩡했고 검사만 공허했다). 콘솔이 BLOCKED 를 안 찍던 것도 고쳤다.

## [검토]

1. **다음 매트릭스 런은 새로 요구한 7개가 PASS 하지 않으면 실패한다.** 의도한 fail-closed
   지만, 특히 셋은 **실 런 산출물로 검증 안 했다** — `signal_com_readback`(러너가
   `signal_readback.csv` 를 쓴다는 것만 확인), `mass_conservation`, `runtime`.
2. **off-ramp 를 BFS 에서 빼는 것이 정당한가.** 나는 "소유자가 선언됐으니 `stop_owners` 와
   같다" 고 봤다. **반론 가능하다 — off-ramp 는 정지선 소유자가 아니다.**
3. **`promotion_readiness` FAIL → NOT_EVALUATED** 가 승격 안전성을 낮추지 않는가.
   NE 는 통과가 아니라 여전히 막히지만 FAIL 이 사라져 눈에 덜 띈다.
4. 남은 tie 27건은 관측 차량 0 이라 PASS 하는데, N5/N9 로 관측이 넓어지면 다시 터져야 한다.
   그것이 의도다. 정말 그렇게 동작하는지.

---

# 계획서에서 정확하지 않은 것으로 드러난 문장

| 계획서 | 실측 |
|---|---|
| SG **128**개 | **136** |
| 동시녹색 **160**쌍 / 최악 **5.00**배 | **222쌍 / 5.47배** |
| native 주기 **100**/140/150/160/170 | **140/150/160/170** |
| N4-3 미해결 "잔차 뭉개기가 아니라 **구조적 부재**" | 결론은 맞고 **원인 진단이 틀림** — `grid_node_legs` 에 `in_link` 칸이 없어서 |
| N4-5 예산면 밖 **8.3%** 과대 | 재현 안 됨. 실측 **+3.33%** (부호·크기 다름) |
| N9 "결정당 300초" | **근거 없음.** 실측 중앙값 9.94s |
| 앵커 상수 6개 | **11개** (3파일) |

**계획서에 적힌 진단도 근거를 다시 열어봐야 한다는 것이 이번 회차의 교훈이다.**

---

# 내가 이번 회차에 틀렸던 방식 — 같은 함정을 조심해 달라

진단을 **네 번** 뒤집었다.

1. **잘못된 표를 봤다.** urban 저장 표(도시부 전용)로 "tie 33건 전부 질량 0" 단정 →
   실 관측에서 중앙값 1.68%, 개별 최대 58 veh 를 나르고 있었다.
2. **계획서 문장을 근거로 썼다.** "구조적 부재" → 실제로는 스키마에 칸이 없는 것.
3. **작업량을 추정했다.** "검사 2건이면 끝" → 모듈 하나가 통째로 무효.
4. **쓰이지 않는 코드 경로를 쟀다.** `DemandProfile` 의 등차수열 397,800 veh/h 를 보고
   14배라 놀랐는데 **결합 런은 그 경로를 안 쓴다.**

**4번이 특히 위험하다. 값을 재기 전에 "그 값이 실 런에서 쓰이는가" 를 먼저 봐야 한다.**

---

# 미해결 설계 판단

## (가) 수요 총량 3.66배를 어떻게 고칠 것인가

어댑터가 `× N입력 / N게이트` 를 쓰기 / 러너가 총량을 넘기고 어댑터가 나누기 /
격자를 실제 입구 22개로 재정렬해 자연히 맞추기.

**근본 원인은 러너-어댑터 규약이 어디에도 문서화돼 있지 않은 것**이다.
`state.demand` 필드가 "지점당 평균" 인지 "총량" 인지 적힌 곳이 없다.

## (나) 격자 재정렬 범위 — **사용자 방침: 플랜트 == VISSIM 망**

실제 입구 22곳만 남기면 `grid_node_legs` → `boundary_in_links` → `urban_movements`(1,414)
가 바뀌고 `canonical_topology_v3` · `physical_stock_topology_v2_1` ·
`topology_approval_v2_1` 재생성, `parent_runs_v3`(봉인 `27aab945…`) 와
`experiment_matrix_v3`(봉인 `d397fa07…`) 재봉인까지 연쇄한다.

**아직 실 런을 안 돌렸으므로 지금이 바꿀 수 있는 마지막 시점이다.**

## (다) N4-3 의 PASS 조건

"scalar-cycle fallback 0" 은 282건이 있는 한 구조적으로 달성 불가다. 조건을 좁힐지
282건을 해소할지.

## (라) 주기 항등식 (구현했다가 되돌림)

`_phase_green_fraction` 이 config 상수로 나누는데 모델은 이미
`cycle_length == p1 + p2 + lost_time` 을 항등식으로 주장한다. 예산면 밖에서 모델이 자기
항등식을 어긴다. 되돌린 이유는 `test_cycle_green_budget_accounting` 이 통째로 무효가 되고
(10 subtest), 다시 쓰려면 N4-3 을 먼저 정해야 하기 때문이다.

역설적이지만 **그 테스트 파일 docstring 이 이 변경과 같은 주장을 한다** —
"`cycle_length` 는 자유 파라미터가 아니라 녹색 예산이 결정한 값이다".
