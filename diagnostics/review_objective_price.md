# ④ 리더 목적함수·⑤ 가격 독립 검토

검토 기준: `6056c94`에서 만든 `control-full-review` worktree, root가 복구한 `evaluation/configs/n21_n7_20260908.json`. 2026-09-09. Production code 수정·VISSIM 실행은 하지 않았다. Python은 번들 Python을 사용했다. `systematic-debugging`과 `karpathy-guidelines`에 따라 실제 dispatch, 단위, 최소 합성 재현을 먼저 확인했다.

## 최종 사용자 정의와 결론

**최종 경계는 고속도로 + 도시 보호망(PN)의 합집합 Ω다. TTT는 Ω 내부 차량의 체류시간만 적분하고, TTD는 Ω에서 비제어 영역으로 나가는 차량수를 센다. 차량이 VISSIM 안에 남아도 Ω를 벗어나면 TTD다. 양쪽 모두 Ω 안인 도시↔고속도로 전이는 TTD가 아니다.** 초기 검토 중 “VISSIM 망 최종 출구”로 이해한 부분은 이 정의로 정정했다.

확정된 누락 현상은 **경계 유입 transit이 현행 near TTT에 포함되지 않는 것**이다. 이것을 새 목적에서 오류로 판정하려면 해당 transit이 Ω 안인지 밖인지 분류해야 한다. TTD를 추가할 때는 **도시→램프 내부 전이를 TTD로 세는 오류**를 막아야 한다. 기존 두 sink 진단의 합은 모형 장부를 닫지만 사용자가 정의한 Ω 경계의 TTD와 같지 않다. Far에는 미보정 임계값과 불연속이 있고 일부 stock이 빠져 있다. 이는 `-N(T)`로 completed를 대체할 수 없다는 근거지만, 현재 `total_physical_vehicles` 자체가 stock 네 개를 모두 누락한다는 뜻은 아니다.

문서의 **팔로워 off-ramp 점유 동결**과 **ΔG=0이면 가격이 전역 한계값 전체를 싣는다는 해석**은 반박된다. 전자는 dead dispatch를 읽은 것이고, 후자는 ΔG와 ΔL을 뒤바꾼 해석이다.

## 검토 범위와 실행 경로

- `resolve_live_controller.py --tuning evaluation/configs/n21_n7_20260908.json --controller wu-link` 및 실제 객체 생성으로 확인했다. 실제 follower는 `LinkAgentWuFollower`, `metering_in_gne=True`, `segment_agents=True`다. resolve 도구의 설명 문자열 `segment_agents=False`는 실제 값을 대변하지 않는다.
- 실제 flags: far enabled/state_aware/real_speed/at_d0=True, value_depth=0, price_far=False, price_lite=False, follower_terminal_cost_enabled=False. `leader_mfd_far_ncrit`와 `leader_mfd_far_freeflow_offset`은 cfg에 없다. ncrit는 vendor 1700, freeflow_offset은 False다.
- n7의 phase price: delta=6 s, weight=0.25, local_cost_model=phased, refine_rounds=12. Meter price delta=300 veh/h, trust_frac=0.2.
- 저장된 과거 `state_*.json`/`action_*.json`는 이 worktree에서 확보하지 못했다. 따라서 과거 특정 시각의 가격·N 및 far 활성 비율/후보 랭킹을 새 실측처럼 제시하지 않는다. 아래 수치는 명시한 합성 프로브 결과다.

## ④ 의심 → 근거 → 판정 → 조치

### A. 경계 유입 transit의 near TTT 누락 — 재현 확정, Ω 내부 여부에 따라 수정

`vendor/NumSim-mine/src/models/state.py:1256-1261`은 `urban_inflow_transit_veh()`를 physical stock에 더한다. 게이트를 통과한 뒤 정지선에 도착하기 전 차량의 유일한 거처라는 docstring도 있다. 반면 `urban_queue_model.py:1292-1295`의 urban TTT는 movement queue와 storage occupancy만 적분한다. `simulation/coupling.py:180-193`은 그 값과 별도로 off-ramp storage TTT만 옮기므로 inflow transit을 복구하지 않는다.

최소 재현: n7 cfg에서 모든 stock을 비우고 `urban_inflow_transit_buffer={'gate:<유효 게이트>': {100:10.0}}`만 둔다. 제로 수요, `urban_substep(..., urban_step_index=0)` 1회:

| 항목 | 결과 |
|---|---:|
| physical stock after | 10 veh |
| inflow transit after | 10 veh |
| urban TTT | 0 veh·h |
| 10대 × 5초의 기대 TTT | 0.013888888889 veh·h |

제안 수정: Ω membership을 먼저 확정한다. **Ω 내부인 transit만** 어댑터 runtime wrapper에서 매 urban substep TTT에 stock×`T_u_h`를 일관된 시점으로 더한다. Ω 밖 접근대기는 사용자 정의 TTT에서 제외해야 하므로 일괄 가산하지 않는다. stock 자체나 release buffer를 중복 추가하지 않는다. 후보 간 transit이 같으면 common offset이어서 그 결정 랭킹은 유지되지만, 이것이 모든 후보에서 항상 같다는 보장은 없으므로 먼저 값을 계측해야 한다. 변경 전 위 프로브가 0이고 변경 후 기대 적분값이어야 한다. 전체 far·TTD를 동시에 바꿀 필요는 없다.

### B. `boundary_out_sink + mainline_exit`를 completed로 간주 — 새 구현 시 실재 오류가 될 조건 확인

사용자 정의 TTD는 **Ω에서 비제어 영역으로 나간 차량[veh]**이며, 양쪽 모두 Ω 안인 도시→램프는 내부 전이다. `urban_queue_model.py:1043-1046`은 도시 out 링크의 램프행을 외생 `demand.ramp_arrival`과 중복하지 않기 위해 ramp queue에 더하지 않는다고 명시한다. 그런데 `:1081-1084`에서 이 램프행 allowed를 departed에 더하고, `:1089-1090`에서 departed 전체를 `boundary_out_sink_veh`로 기록한다. 이 값은 모형의 절단 경계를 닫는 sink이지 Ω→비제어 crossing counter는 아니다.

**n7 실제 split 설치 후 합성 재현**: SC1001_W_out의 이미 도착한 stock 10대, 나머지 stock/수요 0, ramp_release=1800 veh/h씩, urban 5초 1회.

| 항목 | 결과 |
|---|---:|
| split | free 0.25 / R_D_E 0.50 / R_D_W 0.25 |
| boundary_out_sink_veh | 7.222222222222 |
| 그중 boundary_out_ramp_released_veh | 5.000000000000 |
| 비램프 sink 차이 | 2.222222222222 |
| physical stock before → after | 10 → 2.777777777778 |
| ramp_queue after | 네 램프 모두 0 |

장부는 10−7.22222=2.77778로 닫힌다. 하지만 TTD 보상에 7.22222를 주면 **Ω 내부 램프로 이동 중인 5대를 외부 유출로 보상**한다. 따라서 두 누산기의 합이 질량 장부의 sink_out과 같다는 사실만으로 TTD 정의를 검증할 수 없다.

초기 bookkeeping 점검식은 interval의 `boundary_out_sink_veh - boundary_out_ramp_released_veh + mainline_exit_flow_total * T_c_h`다. **이를 최종 TTD 식으로 채택하지 않는다.** 실제 Ω 경계가 boundary_out movement의 정지선 crossing에 있다면 이 차량은 receiving sink storage에 들어갈 때 이미 Ω를 벗어났다. storage 통과 뒤의 delayed sink를 세면 TTD 시점이 잘못된다. `urban_substep`의 `outbound_service_veh`/actual movement departure를 canonical PN crossing connector와 조인해 Ω 내부→외부인 몫을 crossing 시점에 기록해야 한다. 비제어 영역에 도착해 VISSIM에는 남는 차량도 포함한다. Ω 내부 전이는 제외한다. 고속도로 쪽도 제어구간의 끝과 VISSIM 최종 출구가 다르면 controlled freeway exit 단면을 사용한다. `mainline_exit_flow_total`은 substep 평균 veh/h이며 단순 합이 아니다(`metanet.py:783-784`, `coupling.py:51-81`). off-ramp flow를 completed에 더하면 안 된다.

TTT[veh·h]와 TTD[veh]는 `J=TTT-β·TTD`, β[h]로 써야 단위가 맞는다. β=1은 완료차량 1대를 1 veh·h 개선과 동등하게 보는 큰 정책 선택이다. 임의 기본값으로 고정하지 않는다. 같은 후보 집합의 (TTT, TTD)를 저장하면 새 VISSIM 런 없이 β별 Pareto/랭킹 민감도를 먼저 계산할 수 있다. 음의 reward 도입 시 `rollout_endpoint.py:304-307`의 비음 비용 기반 조기 가지치기 가정도 바뀌므로 기존 `total_ttt > incumbent` prune을 그대로 재사용하면 안 된다.

### C. 물리 stock 보존과 far의 stock 범위 — 혼동 정정 + far 근사 범위 확인

`TrafficState.total_physical_vehicles`는 이미 urban+freeway+off-ramp storage+inflow transit을 포함한다(`state.py:1256-1261`). `total_urban_vehicles`에는 on-ramp movement queue가 포함되고(`:1286`), `total_freeway_vehicles`에는 ramp queue 및 mainline origin queue가 포함된다(`:1269-1274`). 그러므로 **physical helper가 네 채널을 누락한다는 주장은 틀리다**. docstring의 “35.46대 사라짐”은 과거 정의를 설명한다.

반면 far는 N_u=`protected_accumulation + boundary_in_queue`, mainline=`total_freeway-ramp_queue`, 별도 ramp queue tail을 쓴다(`stackelberg_mpc.py:113-124,178-208`). on-ramp 도시 접근큐, off-ramp storage, inflow transit은 far 밖이다. ramp_queue는 별도 tail로 **포함**된다.

모든 stock을 비운 n7 cfg에 10대씩 따로 넣은 실제 함수 결과:

| 10대의 위치 | physical | far의 N_u | far(veh·h) |
|---|---:|---:|---:|
| boundary_in movement | 10 | 10 | 0.003255208333 |
| internal movement | 10 | 10 | 0.003255208333 |
| on_ramp movement | 10 | 0 | 0 |
| off_ramp storage | 10 | 0 | 0 |
| inflow transit | 10 | 0 | 0 |

이는 far가 완전한 physical stock 함수가 아님을 증명한다. 따라서 far 내부의 N을 `-N(T)`로 바꿔 completed를 만들면 차량을 보상 밖 저장고로 옮기는 가짜 이득이 가능하다. 명시적 출구를 추적하는 방향은 타당하다. 한편 현행 near TTT는 on-ramp queue·ramp queue·off-ramp storage를 포함하며 위 A의 inflow transit만 누락하므로 near도 네 개를 모두 누락한다는 주장은 반박한다.

검증: `python -m unittest src.tests.test_global_mass_conservation src.tests.test_total_physical_vehicles`를 vendor cwd에서 실행. 8개 중 7 PASS, 1 FAIL. 실패는 `test_offramp_rejection_stays_unreachable_under_forced_saturation`의 `assertEqual(rejected_total,0.0)`에 `2.7755575615628914e-17`이 들어간 부동소수 정확비교다. 3개 합성 시나리오의 24-step 물리 보존 테스트는 PASS다. 이를 n7 실관측 전역 보존 증명으로 확대하지 않는다.

### D. ncrit=1700과 far 불연속 — 미보정 모델 상수 확인, 수치 불연속 재현

n7 실효 cfg에는 `leader_mfd_far_ncrit`가 없다. `stackelberg_mpc.py:114-118`의 fallback 1700 및 `N²*Tc/(2G)`에서 G를 순간 교체하는 식이 활성이다. `adapter.py:7973-7980`은 관측 방류로 g_cong을 갱신하고 g_free는 관측 독립값이 아니라 **고정 비율 500/640의 역산**으로 만든다. 과거 큰 망은 항상 혼잡이라는 주석(`:7794-7799`)이 Ver2의 작은 N에서도 참이라는 검증은 없다.

관측 주입 전 n7 cfg 실제 함수 호출:

| N_u (veh) | urban far (veh·h) |
|---:|---:|
| 1699.999999 | 94.075520722656 |
| 1700.000000 | 120.416666666667 |
| 1700.000001 | 120.416666808333 |

0.000001대 변화에 26.341145944011 veh·h가 점프한다. 관측 g를 적용해도 g_free/g_cong=1.28이므로 상대 28% 불연속은 남는다. 임계값을 재적합해도 불연속 자체는 없어지지 않는다.

판정: 미보정 임계 및 수치 jump는 확정. 이것이 해당 결정의 주된 손실인지는 **terminal candidate N 분포와 후보별 far 성분**이 필요하다. 별도 이력변수 없이 단순 N 임계로 전량의 배수율을 바꾸는 것이 의도된 혼잡 hysteresis인지도 설명되어 있지 않다. 단순 piecewise 배수율의 적분 tail을 의도했다면 연속식 `Tc*[min(N,Nc)^2/(2Gf)+max(N²-Nc²,0)/(2Gc)]`가 그 의도에 맞는다. 새 기준값을 임의로 정하지 말고 N/실측 최종 유출을 같은 경계·시간창으로 수집해 적합해야 한다.

### E. 감시 도로가 far N에 포함되는 문제 — Ω membership 기준이어야 함, quadratic 효과는 상수 아님

`protected_accumulation_veh`는 owner 필터 없이 모든 non-off-ramp storage와 internal/boundary_out/off_ramp movement를 센다(`state.py:1406-1417`). 사용자 정의 Ω 안에 속한 도로라면 직접 제어 가능한 신호가 없어도 TTT에 포함하는 것이 타당하다. 반대로 Ω 밖 도로는 소유 여부와 관계없이 빼야 한다. 신호 소유권 자체가 Ω membership은 아니다. 하지만 후보가 바꾸지 못하는 몫 C도 far `(A+C)^2/(2G)`의 **교차항 2AC**를 통해 제어 가능한 A의 marginal을 `(A+C)/A`배로 키운다. Near의 단순 상수 offset과 다르다.

문서의 C=430.5, total=1649가 실제 같은 stock 정의로 재확인된다면 marginal 증폭은 1649/1218.5=1.3533배다. 전체 far의 45.4%가 C 및 교차항에서 생긴다. 이 수치는 제공 기록에 대한 조건부 계산이지 새 실측은 아니다. 해결은 단순 owner 필터 삭제/추가가 아니라 **N과 배수율 G의 동일 경계 정의** 및 동역학으로 C가 실제 후보 간 상수인지 검증하는 것이다.

### F. far 활성 3.2%·g_fw 단위 — 확인 범위

리더 full candidate에서 far_mode는 objective_mode!=state_accumulation AND (depth>0 OR far_at_d0)다(`stackelberg_mpc.py:2410-2425`). n7은 이 조건을 만족한다. Price rollout은 `price_far=False`로 far를 끄므로 **모든 채점 호출 중 비율**은 full leader 후보 중 비율과 다르다. `3.2%`만으로 리더 far 무효라고 판정할 수 없다. 현재 산출물에는 full/proxy/price 호출별 counts와 실제 far/near/penalty, terminal N이 필요하다.

추가 단위 조사: `freeflow_offset=True AND state_aware=True` 경로는 segment capacity[veh/h]를 g_fw_l에 넣고 다시 veh/Tc처럼 쓰는 단위 문제가 있다(`stackelberg_mpc.py:160-174`). **n7의 freeflow_offset은 미설정 False여서 현재 dead branch**다. 지금 제어 실패의 원인이라고 보고하지 않는다. 이 기능을 켜려면 capacity에 Tc_h를 곱하거나 tail식을 시간유량 단위로 통일해야 한다.

## 사용자 정의 Ω에 맞춘 최소 측정·최적화 설계

- 정본 urban PN boundary ledger(`outputs/pn_boundary_turns_v1_20260819.json`)와 실런 42-cell freeway mapping을 조인한다. `controlled` 신호 여부나 `protected_accumulation` 함수 이름을 membership의 대용으로 쓰지 않는다. 정본 `derive_pn_boundary_turns.py:78-83`의 outflow/external은 **도시 PN만의 전이**이며 합집합에서의 외부 전이와 다시 구분해야 한다.
- 동일 차량 ID 궤적에서 `inside_Ω(previous)`와 `inside_Ω(current)`의 전이로 TTD를 계수하고, 출구 소멸은 확인된 outward exit link/position에서의 소멸만 센다. 상태에 안 보인다는 이유만으로 출구 처리하면 관측 누락을 TTD로 보상할 수 있다. 재진입 후 재유출은 stock 보존상 crossing event로 세며, unique trip completion과 구분한다.
- TTT는 같은 Ω mask로 `∫N_Ω(t)dt`. Ω 밖 boundary queues/outbound link 체류 및 외부 감시 구간을 일괄 포함하면 사용자 목적이 아니다. 관측은 같은 mask의 차량별 residence 혹은 충분히 촘촘한 count 적분, 모델은 reservoir별 Ω 소속 또는 fractional occupancy로 일치시킨다.
- 모델 한 substep에서 `N_Ω(next)−N_Ω(now)=entered_Ω−exited_Ω+generated_Ω−removed_Ω`를 대조한다. on/off-ramp 내부 전이는 양쪽 stock 이동만 만들고 `exited_Ω=0`이어야 한다. 모델이 도시 램프행을 외생 절단 sink/source로 처리하는 현재 seam은 전역 모형 장부와 Ω 장부를 분리해 기록해야 한다.
- 필수 합성 검증: (i) Ω 내부 도로에 10대×5초→TTT 0.01388889, TTD0; (ii) Ω 밖 도로 같은10대→두지표0; (iii) 도시PN→Ω 내부FW 전이→TTD0 및 stock보존; (iv) PN→비제어 도시→TTD crossing 대수 즉시 증가(차량은 VISSIM에 남음); (v) controlled freeway→외부→TTD 증가; (vi) 경계 connector에서 중복계수0.
- 최적화 rollout은 각 substep의 Ω TTT와 Ω exits를 명시적으로 누산한다. `rollout_endpoint`가 현재 states+TTT만 돌려주는 반환형 때문에 출구 event를 terminal N로 역산하지 말고 adapter runtime wrapper에서 새 누산 결과를 직접 전달한다. 전체 global TTT는 보조 진단으로 남겨도 사용자 primary 결과와 구분해야 한다.

## ⑤ 의심 → 근거 → 판정 → 조치

### G. “ΔG=0이므로 전역 한계값 전체를 가격에 싣는다” — 반박

live phased patch는 `p=(n_live−1)/n_live · (ΔG−ΔL)/δ`다(`vissim_stackelberg_adapter.py:2279-2281`). ΔG=0이면 p는 **자기 local 변화의 반대 부호**로 전역 불변을 만드는 상쇄 신호다. **ΔL=0일 때** 가격이 전역 변화 전체가 된다. 후자는 패치 docstring에 적힌 과거 drain surrogate 결함이고, 전자와 다른 경우다.

4현시의 0.75는 고정 총 녹색 simplex에서 방향미분을 평균 제거한 가격 좌표로 바꾸는 계수다. 실제 식에 부호 clip은 없으므로 가격이 구조적으로 한쪽 부호라는 결론도 성립하지 않는다. 현재 상태에서 ΔG가 모두 0인지는 각 phase별 global/local baseline·perturbed 비용을 기록해 별도로 확인해야 한다.

같은 국소 scorer와 국소 선형 근사에서 정련이 `L + w·price`를 쓰면 허용 방향의 gradient는 `(1−w)L' + wG'`이다. n7 w=0.25에서 G'=0이면 0.75L'이므로 local 선호를 감쇠할 뿐 역전하지 않는 현상은 설명된다. 그것만으로 가격 부호 버그라고 할 수 없다. 반대로 서로 다른 scorer/forecast/clip을 쓰면 이 상쇄 정합성이 깨지므로 global/local raw deltas와 허용 perturbation 크기를 모두 저장해야 한다.

### H. meter 가격이 green의 1/1000 — raw 값 비교로는 오류 아님

green 가격 단위는 veh·h/s, meter 가격은 veh·h/(veh/h), VSL 가격은 veh·h/(km/h)다. 코드가 각 가격에 해당 레버 변화량을 곱해 비용으로 넣으므로 raw derivative 비율은 서로 비교할 수 없다. 동일 단위로 비교하려면 `|p_green|·green_trust_sec`, `|p_meter|·meter_trust_veh_h` 또는 무차원 레버 기준 `p·lever_range`를 쓰면 된다. 예를 들어 0.1×6과 0.002×300은 둘 다 0.6 veh·h다. 이는 단위 예시이며 관측 가격 수치는 아니다.

별도 현상: n7 meter price 프로브는 δ=max(300,0.2×1800)=360 veh/h이며 운영점 1800에서 [1440,1800]만 본다(`stackelberg_wu_metered.py:1372-1380`). 실효 수요/receiving가 두 끝보다 작으면 양 끝 release가 같아 ΔG=ΔL=0일 수 있다. 이때는 단위 오류가 아니라 **포화영역 밖에서 용량 레버를 흔든 식별 실패**다. 후보 허용 범위 안에서 실제 release가 달라지는 breakpoint를 포함하는 진단이 필요하다.

### I. off-ramp 점유·램프큐 동결 — live 경로에서는 반박

`priced_wu_link_controller.py:147-166`에서 segment_agents=True는 metering을 GNE에 넣는 dispatch gate이며 override가 `_solve_freeway_agent_metered`로 보낸다. 해당 live local scorer는 매 substep ramp_q/blocked_q를 갱신하고(`wu_faithful_follower.py:2310-2318`), 현재 off-ramp 가용 storage로 cap을 계산하고(`:2320-2324`), METANET을 전진한 뒤 inflow−drain으로 occ 및 receiving occ를 갱신한다(`:2330-2348`). own-TTS도 갱신 stock을 포함한다(`:2353-2365`). `:2545/2553`의 동결값만 읽고 wu-link 전체 동결이라고 단정하면 틀린다.

다만 Jacobi의 이웃 신호·이웃 coupling 입력은 각 후보의 외부 경계조건으로 동결하는 설계다. 이것과 **자기 off-ramp storage state 동결**은 다른 의미다. φ·λ 효과는 후보별 dynamic occ를 사용하므로 “Δλ가 후보 간 반드시 상수여서 VSL만 벌점을 줄인다”는 전제도 성립하지 않는다. φ=3.0의 적합 근거 및 v² 감속항의 실측 일치 문제는 ⑥ 동역학 검토에서 별도로 판정해야 한다.

### J. price_far·follower_terminal 켜기 — 설계 선택, 지금 자동 활성 근거 없음

price_far는 live builder에 실제 배선되어 있으나 n7에서 OFF다(`adapter.py:6990-6997`). 현재 far의 stock 누락·N/G 경계·불연속부터 확인하지 않고 켜면 그 오류를 매 phase 가격까지 전달한다. Near leader 후보를 far로 랭킹하는 것과 follower에 linearized far 가격을 보내는 것은 별도 실험이다.

follower terminal cost는 live local scorer에 배선되어 있으며 종료시 ramp+blocked 큐의 Q²/(2R) 비용이다(`wu_faithful_follower.py:2369-2381`); OFF가 미배선인 것은 아니다. 이를 켜면 램프 잔류를 더 비싸게 보므로 방류를 더 선호할 수 있다. 현재 문제를 미터링 부족으로만 보는 경우에는 반대 방향일 수 있다. 실제 후보별 tail 차이와 선택 변화가 확인될 때 독립 팔로 검증해야 한다.

## root에 제안한 최소 작업 순서

1. 현재 baseline 중 어댑터 수정 금지 유지. **Ω 물리 membership 및 crossing ledger를 먼저 확정**한다. urban PN 정본과 controlled freeway 정본의 합집합을 사용하며, 소유권을 새 규칙으로 재유도하지 않는다.
2. TTT·TTD·N·외부 accepted inflow를 같은 Ω에서 정의한다. 내부 램프 전이 제외, 실제 Ω→외부 crossing 시점 반영, 단위 β를 명시한 candidate-level 누산기를 계측한다. A의 transit도 Ω 내부 몫만 가산한다. `-N(T)`를 사용하지 않는다. reward 도입 시 early-stop 보수 하한을 다시 검증한다.
3. 리더 후보별 near/far/penalties/N/true exits 및 phase price별 ΔG/ΔL를 남긴다. 매 호출을 섞은 far 활성률이나 derivative raw scale로 원인을 결정하지 않는다.
4. ncrit를 동작점에 맞게 적합하되 jump를 별도로 판정한다. phase price 부호, follower storage 동결을 원인으로 가정한 수정은 하지 않는다.

본 파일 외의 생산 코드 수정은 하지 않았다.
