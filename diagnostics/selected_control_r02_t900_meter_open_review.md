# r02 t900: fully open physical meters and retained model rate

Initial read-only review, 2026-09-10. Source run: `evaluation/runs/codex_selected_fw070_u040_beta0_r02`; initial evidence limited to `action_000900.json`, its CSV, `state_000900.json`, the declared tuning, and current source. No model replay, native access, source change, or traffic-effect estimate was performed during that initial review. The subsequently completed paired model query is recorded in the final section below.

## Observed command

The CSV has 213 rows: 66 VSL, 17 signal summaries, 122 SG windows, and 8 meters. The 196 physical-address rows have no duplicate keys; numeric fields are finite. All 17 signal summary vectors and offsets exactly match the action JSON. There are 63 positive phase values and 15 nonzero offsets. Every VSL address is 120 km/h. Every meter is GREEN 10/10 seconds with CSV `rate_vph=900`: all eight physical meters are open. This is command evidence, not native readback verification.

The finalized marker agrees with those eight GREEN values and the writer reports `control_area_meter_writer_matches_scored=1`. The four model rates nevertheless remain distinct:

| Model group | Physical meters | Frozen demand-hint sum, veh/h | Retained requested/realized model rate, veh/h | Physical GREEN seconds |
|---|---|---:|---:|---|
| R_D_W | 10480, 10482 | 532.637520 | 1169.0634529178417 | 10, 10 |
| R_F_W | 10646, 10644 | 789.743133 | 1484.531726458921 | 10, 10 |
| R_D_E | 10490, 10484 | 509.921412 | 1800 | 10, 10 |
| R_F_E | 10639, 10681 | 339.243626 | 962.6324439585037 | 10, 10 |

The rate sum exactly equals recorded `N_UF_star=5416.227623335266`. The state reports 3/7/6/2 vehicles on the respective physical ramp groups. These counts and frozen throughput hints do not certify future desired demand or unconstrained release.

## Existing branch, not a late writer change

`evaluation/controllers/vissim_stackelberg_adapter.py:10506–10530` constructs each hint as `max(current measured passage, decay-or-retained previous hint, floor)`. It retains the previous hint when the previous GREEN was restrictive. This improves on treating restricted passage as fresh demand, but it still does not observe future platoons or future queues.

At `:10414–10424`, the allocator computes

`open_total = sum(min(table_capacity_at_max_green, connector_demand_hint))`.

If `requested >= open_total`, both physical commands become `max_green` and `realized[group] = requested` deliberately survives. Every group in this action takes this branch. At `:10601–10610`, CSV `rate_vph = green * per_meter_capacity / cycle` is reconstructed for the VBS rate/GREEN consistency check. Thus CSV 900 is a command encoding; neither eight times 900 nor the table's GREEN-10 extrapolation is an observed discharge rate.

`area_meter_finalization.py:1–6,87–139` explicitly describes a grouped equivalent-rate approximation, freezes its input context, and prevents the writer from changing the scored schedule. Those checks establish command consistency. They do not remove the residual model rate limit when the native schedule is fully open.

The model still uses `requested = clip(control.ramp_metering[group], 0, cap)` and `release = min(no_meter, requested)` in `vendor/NumSim-mine/src/models/metanet.py:297–302`. The active area coupling calls that same release function at `evaluation/controllers/area_freeway_accounting.py:341`, then preserves accepted transfer/receiving accounting. Therefore a later offer above the retained rate can be restricted in the model while the physical meter stays fully open. Whether/how often that happened in this action's 450-second forecast is **not established by the saved action**, which has no substep release trace. This can matter even before a new arrival if an existing queued offer is sufficiently large.

The four active near-model capacities are reported as 1800 veh/h each. The separate `far_ramp_capacity_*` metadata is not the near-model cap: adapter `:7961–7962,8075–8110` installs those empirical values only during far evaluation. They must not be substituted into this argument.

## Small correction alternatives to test after the run

The narrow semantic correction for an all-open group is **no additional meter constraint**, while retaining the existing demand, receiving, storage and physical/model capacity limits. In the present scalar release API, that is equivalent to assigning the group's existing near-model `ramp_capacity_veh_h`, or to an explicit open flag that selects `no_meter` in the existing release primitive. The former is smaller but also changes the group-budget coordinates. For this action, canonicalizing all four groups to the declared 1800 caps would produce a model budget of 7200; it does not assert native discharge is 7200.

Do not sum the two CSV 900 encodings as a newly identified capacity, multiply the GREEN-10 per-lane table by lane count to inflate group capacity, or treat the frozen hint as a future cap. Partial GREEN retains its existing measured-table approximation; this note proposes no replacement calibration or independent eight-meter strategy.

Before any adoption, the same canonical open representation must be used in follower candidates, price probes, leader evaluation, fallback, finalization and the emitted action. Reclose `N_UF_star` to the same represented model rates and validate its box/owner shares. Otherwise identical eight-meter commands can still carry different modeled flow caps, costs or prices. Preserve original requested values separately for diagnosis. Changing the open representation only in the writer or only after scoring would reintroduce a late action change; changing it only in the global plant would leave local prices inconsistent. A new flag must survive copy/worker/box-walk and be invalidated when its physical schedule changes.

The smallest saved-state check after completion is a bounded paired endpoint: current action versus the same physical GREEN/VSL/urban commands with only the open group model-rate representation canonicalized. Record per-substep `no_meter`, requested and accepted flows, ramp stocks, receiving rejections, Ω closure and J components; check physical command equality. This is a model consistency experiment, not causal evidence of native traffic improvement. A separate same-physical-command alias test should require equal fixed-query cost under the corrected representation.

## Objective records and follow-up scope

β is zero, Ω enabled, unknown route holding is zero, initial Ω stock is recorded as 892, and all applied leader legacy penalties are zero. `leader_selected_objective=162.99000117374214` and follower held score `163.03814934741493` differ by 0.04814817367278579 veh·h; the top-two leader gap is only 0.0001366807053386765 veh·h.

These are two source-level evaluations, not evidence of a writer failure: `area_follower_objective.py:31–58` holds the finalized vector for three intervals (`box_walk=False`); `stackelberg_mpc.py:1536–1548` first closes leader quantities, then `area_leader_objective.py:170–183` reruns the endpoint with the leader spec. Its default box-walk and `walk_previous` differ; the configured `leader_rollout_box_walk_vg=True` and `rollout_endpoint.py:210–283` can evolve future primary greens. The link builder removes the SEG13 meter/VSL boxes but does not remove that green-walk flag. No replay here attributes the numeric difference to an individual mechanism. Compare identical post-closure, fixed-command contexts after completion before calling it stale metadata.

`nash_converged=1` is the existing scalar-control stopping result. The same output reports NP price iterations 2, lambda 10, and predictor residual 55.9344130195542 before output closure; it contains no final 19-owner finite-candidate gap certificate. These labels must not be interpreted as proof of full-vector GNE or hard shared-target equality. No traffic-performance conclusion is drawn from this first command.

## 완료된 450초 alias 진단 — 수선은 미적용

`diagnostics/control_improvement/open_meter_alias_t900_before_v1.json`의 두 endpoint는 21.531초에 정상 완료됐다. 두 팔 모두 기존 CSV 213행의 물리 주소·값 **multiset**이 같았다(행 순서 동치 검사는 아님). 기록된 표현의 J는 `163.03814934741493`, 기존 near capacity로 정규화한 표현은 `163.02727669760085` veh·h로, 차이는 `−0.01087264981407543`이다. 첫 10초의 `R_F_W` accepted flow는 `1484.531726458921 → 1800` veh/h였으며, 당시 두 팔의 aggregate `no_meter_total`은 모두 5400 veh/h였다. 두 팔의 입력과 고정 미터 문맥·near capacity는 불변이고 `source_changes=[]`였다.

이는 **같은 물리 명령에 남아 있던 모델 유량 표현의 민감도**를 확인한 결과다. 실제 차량 흐름 개선이나 10% 성능 개선의 증거가 아니다. 정규화한 팔은 `N_UF_star`도 `5416.227623335266 → 7200`으로 바꾸므로, 기존 예산을 고정한 follower 후보 검증으로 해석할 수 없다. 최소 수선은 동일 정규화를 예산 검사와 국소·전역 채점/가격 평가보다 먼저 적용하고, 불가능한 예산은 명시적으로 거부하는 것이다. 선택 후 예산만 올리거나 전역 방출만 바꾸는 수선은 정합하지 않다. 이 최초 진단 시점에는 정규화안을 생산 코드에 적용하지 않았다.

후속으로 `area_meter_finalization.prepare_canonical_candidate()`를 구현했다. 고정7200 예산에서 두 입력 표현의450초 상태·유량·비용이 같고, 원래5416 예산은 cap/equality 모두 거부되는 것을 저장 상태로 확인했다. 기존 solver/가격 dispatch에는 아직 연결하지 않았다. [후속 구현과 검증](control_improvement/fixed_candidate_preparation_v1.md)에 새로운 결과와 현재 미완료 범위를 구분했다. 실차 개선 증거는 여전히 아니다.
