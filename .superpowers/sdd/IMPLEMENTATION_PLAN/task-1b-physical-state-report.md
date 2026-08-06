# v2.1 Physical-State and Topology Amendment Review

## Review basis and verdict

- Repository: `C:/tmp/vissim-pstack-controller`
- Branch: `codex/plant-fidelity-v2-1`
- Reviewed commit/baseline: `cb3c44d170b7f818baae7af399fb65c93b6fb1e3`
- Mode: read-only review of `IMPLEMENTATION_PLAN.md`, the VISSIM adapter and observation writer, topology/capacity generators, NumSim state and dynamics, tests, and the plant-fidelity auditor. This report is the only file produced.

**Verdict: BLOCKED until the amendments below are incorporated.** The v2 plan names most physical topics, but it does not yet define one conserved physical-stock model, it permits physical links to disappear as explained clipping or exit exclusion, it does not make lane/route geometry authoritative, and its physical validation gates are incomplete. In particular, Section D is stale: link speed and queue-tail fields are already exported, but rollout delay does not consume them.

## Binding physical invariants

The v2.1 plan should state these invariants before its task list. Every later artifact and gate must use the same definitions.

1. **One vehicle, one physical stock.** At an instant, every observed VISSIM vehicle belongs to exactly one modeled physical stock: an urban lane-group stock, a ramp queue, an off-ramp stock, a freeway segment, an exit/boundary-out stock, or an explicitly named external/unobservable stock. Visibility, control ownership, and objective attribution are views of that stock and never create copies.
2. **Conservation is not a tolerance target.** A capacity limit constrains sending or receiving flow. It must not delete mass. Any excess remains in an upstream stock or an explicit overflow/external queue.
3. **Routes precede compass labels.** Connectivity is the lane-level directed connector graph plus active static-route evidence. A compass leg is derived metadata, never the source of adjacency, ownership, movement, or stock identity.
4. **Physical and objective boundaries are separate.** Excluding a stock from one objective does not remove it from the plant, its travel time, its receiving supply, or its backpressure.
5. **Calibration and certification are disjoint.** No holdout run, anchor, or future trajectory may influence a fitted jam density, storage fraction, queue capacity, discharge capacity, or error threshold.

## P0-1. Separate link ownership from shared physical stocks

### Issue and evidence

The current assignment contract says one link has exactly one player and emits scalar `link_owner`, `link_upstream`, and `link_stop_line` fields (`scripts/assign_links_to_players.py:1-15`, `scripts/assign_links_to_players.py:315-326`). The distributed generator then overwrites each observed link with exactly one model origin (`scripts/generate_real_world_distributed_players.py:763-781`). The v2 plan recognizes a possible shared route, but only says to "consider" weighted ownership while still requiring a strict partition artifact (`IMPLEMENTATION_PLAN.md:152-165`). This conflates three different concepts:

- physical stock membership;
- follower visibility/control responsibility;
- objective attribution.

That is unsafe where two route branches share pavement or where one downstream stock is visible to multiple players. The audit already warned that assigning an internal connector immediately to the next approach can hide conflict occupancy and travel time (`reports/plant_fidelity_audit.md:94-98`).

### Exact v2.1 amendment text

> ### A-0. Authoritative physical-stock contract (new P0 blocker)
>
> **Inputs:** the hash-bound `.inpx`, active-program route tables, signal-head inventory, ramp/freeway mapping, and the resolved lane-route graph from B-1.
>
> **Implementation paths:** add `scripts/compile_physical_stock_topology.py`; extend `scripts/generate_real_world_distributed_players.py`, `evaluation/controllers/vissim_stackelberg_adapter.py`, and `vendor/NumSim-mine/src/models/state.py` to consume the resulting schema. Do not use `link_owner` as a state key.
>
> Build one global physical stock registry. A VISSIM `(link, lane, interval)` member appears in exactly one stock. Store control ownership, observer visibility, and objective attribution as separate references to that stock. Shared pavement is represented once; multiple agents may observe it. A route split may divide future flow, but may not split or duplicate the current vehicle count unless lane/route observations identify the vehicles.
>
> **Command:**
> `python scripts/compile_physical_stock_topology.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --lane-routes outputs/lane_route_proofs_v2_1.json --assignment outputs/link_player_assignment_v2_1.json --out outputs/physical_stock_topology_v2_1.json --report reports/physical_stock_topology_v2_1.md`
>
> **Stop condition:** any lane interval belongs to zero or more than one physical stock, any objective weight lacks route evidence, or any shared stock is materialized more than once in `TrafficState`.

### Required artifact/schema

`outputs/physical_stock_topology_v2_1.json` must include:

```json
{
  "schema_version": "physical-stock-v2.1",
  "source_hashes": {"inpx_sha256": "...", "route_graph_sha256": "..."},
  "stocks": {
    "stock:<stable-id>": {
      "kind": "urban|ramp|off_ramp|freeway|boundary_out|external",
      "members": [{"link": "31", "lanes": [1, 2], "from_m": 0.0, "to_m": 421.0}],
      "capacity_veh": 143.5,
      "upstream_stock_ids": [],
      "downstream_stock_ids": [],
      "control_owner": "U_SC1001|null",
      "visible_to": ["U_SC1001", "U_SC1004"],
      "objective_weights": {"U_SC1001": 0.7, "U_SC1004": 0.3},
      "route_evidence_ids": ["route-proof:..."]
    }
  },
  "member_to_stock": {"31:1:0.000-421.000": "stock:<stable-id>"}
}
```

### Dependency and quantitative acceptance

- Prerequisite: P0-2 lane-route graph and all unresolved topology ties resolved or represented as an explicit shared route.
- The 1,205-link urban assignment universe remains complete, but physical membership is checked at lane-interval granularity: missing members `= 0`, duplicate members `= 0`.
- Every nonempty `objective_weights` map sums to `1.0 +/- 1e-9`; weights without route-flow evidence `= 0`.
- Global physical stock count and vehicle mass are invariant under agent iteration order and agent masking, with absolute difference `<= 1e-9 veh`.
- Hashes from three independent compilations are byte-identical.

## P0-2. Replace hop-BFS and centroid legs with deterministic lane-route geometry

### Issue and evidence

Current ownership uses hop-count BFS over sets (`scripts/assign_links_to_players.py:130-197`), records multiple same-hop terminals as unresolved, and still chooses the first sorted upstream controller before reporting the tie (`scripts/assign_links_to_players.py:232-263`). It derives legs by quantizing a stop-link/centroid bearing to eight directions (`scripts/assign_links_to_players.py:266-276`). The separate adjacency generator skips connector nodes, retains one parent path, derives leg labels from controller centroids, and synthesizes missing reverse adjacency (`scripts/derive_intersection_adjacency.py:78-89`, `scripts/derive_intersection_adjacency.py:114-148`, `scripts/generate_real_world_distributed_players.py:344-360`). A synthetic reverse edge can therefore create a model route forbidden by the VISSIM network.

The v2 plan asks to reclassify 123 pairs, but it does not prohibit reverse-edge synthesis, define a metric, or define a route-proof schema (`IMPLEMENTATION_PLAN.md:172-181`). Its C-3 direction is better, but applies only to signal movement mapping (`IMPLEMENTATION_PLAN.md:252-280`).

### Exact v2.1 amendment text

> ### B-1. Lane-level directed route graph and deterministic geometry (replace A/B BFS)
>
> **Inputs:** the exact `.inpx`; every connector's from-link/from-lane/from-position and to-link/to-lane/to-position; active `vehicleRoutingDecisionStatic` routes and `relFlow`; signal heads; freeway/ramp terminal sets.
>
> **Implementation paths:** replace hop-BFS in `scripts/assign_links_to_players.py` and parent-path BFS in `scripts/derive_intersection_adjacency.py` with one shared parser/module. Remove permissive reverse-edge synthesis from the production path. Keep compass labels only as reported metadata.
>
> Create a directed lane graph whose edges are executable connector traversals. Resolve a terminal by shortest physical path length in metres, not hop count. Use active route membership first and route `relFlow` second. If two feasible paths reach different terminals, emit an explicit shared-route record with normalized flow shares; do not choose the lowest ID. If evidence cannot distinguish them, stop.
>
> Compute approach and exit legs from the final connector tangent and destination-link tangent. Movement identity is `(approach_stock_id, connector_path_id, exit_stock_id)`. No 45-degree or centroid fallback may enter a production artifact.
>
> **Commands:**
> `python scripts/build_vissim_lane_graph.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --out outputs/vissim_lane_graph_v2_1.json`
> `python scripts/resolve_lane_routes.py --graph outputs/vissim_lane_graph_v2_1.json --roles evaluation/real_world_modi_inventory/signal_controller_roles.csv --out outputs/lane_route_proofs_v2_1.json --ties reports/tie_resolution_v2_1.md`
>
> **Stop condition:** any production edge is synthetic, any path uses a connector in the wrong direction/lane, any material route has no terminal, or any terminal tie lacks a physical shared-route record.

### Required artifact/schema

`outputs/lane_route_proofs_v2_1.json` must record, per source lane interval: ordered link/lane/connector sequence, path length, first downstream stop line or freeway/exit terminal, upstream terminal, active route IDs, normalized `relFlow`, turn angle, and resolution status (`unique`, `shared`, or `unresolved`). It must also record why any legacy adjacency pair was removed or added.

### Dependency and quantitative acceptance

- Prerequisite: S1 active program and route/program schedule are hash-bound; route evidence is program-specific.
- Production unresolved route count `= 0`; arbitrary lowest-ID resolutions `= 0`; synthetic reverse adjacency count `= 0`.
- Every emitted adjacency edge has at least one executable connector path; executable-path coverage `= 100%`.
- Every route-share vector sums to `1.0 +/- 1e-9`; nonzero shares have nonzero active `relFlow` or an explicit equal-share physical approval.
- Signal-head outgoing connector turn classification agrees with connector geometry on at least `99.0%` of vehicle-weighted mapped movements; the remaining `<= 1.0%` must be listed and blocks promotion if any has more than `0.1%` vehicle weight individually.
- Three builds from permuted XML iteration order produce the same canonical SHA-256.

## P0-3. Make initial projection a complete source-to-stock ledger

### Issue and evidence

The adapter splits a link count into storage and movement queues, clips storage at capacity, and leaves clipped mass unrepresented (`evaluation/controllers/vissim_stackelberg_adapter.py:816-865`, `evaluation/controllers/vissim_stackelberg_adapter.py:944-1004`). The current regression test explicitly accepts 14 clipped vehicles and 17 unrepresented vehicles (`tests/test_vissim_stackelberg_adapter_fidelity.py:51-60`). The auditor permits up to `max(5 veh, 3% of input)` unrepresented and permits nonzero clipping if it is merely explained (`scripts/audit_plant_fidelity.py:891-901`). Those are diagnostic rules, not a physical projection contract.

There is also a total-state inconsistency: the adapter reports `total_model_vehicles` without ramp queues or mainline-origin queues while exposing both as separate fields (`evaluation/controllers/vissim_stackelberg_adapter.py:2450-2475`). The VISSIM calibration patch replaces `total_freeway_vehicles` with segment vehicles only, dropping the original ramp/origin terms (`evaluation/controllers/vissim_stackelberg_adapter.py:1287-1296`; compare `vendor/NumSim-mine/src/models/state.py:997-1006`).

### Exact v2.1 amendment text

> ### D-1. Conserved state projection ledger (replace percentage capture)
>
> **Inputs:** state schema v2 link/lane counts, `physical_stock_topology_v2_1.json`, freeway segment observations, ramp connector observations, exit stocks, and scan status.
>
> **Implementation paths:** rewrite the physical branch of `build_local_observation_summary()` and `traffic_state_from_vissim()` around a source-to-stock ledger. Add a single `TrafficState.total_physical_vehicles()` implementation and use it in adapter summaries, objectives, and audit output. Legacy projection may remain only behind an explicit non-production flag.
>
> Project each observed source link/lane count once. Queue/in-transit composition is metadata inside the same physical stock. If observed occupancy exceeds nominal capacity, preserve the excess in the stock's upstream spillback/external-overflow stock and mark the capacity violation; never discard it. `unobservable_vehicle_count` is a separately measured root category, not a residual used to close the identity.
>
> **Command:**
> `python scripts/validate_state_projection_v2_1.py --states <state-manifest.json> --topology outputs/physical_stock_topology_v2_1.json --out outputs/projection_ledger_v2_1.json --report reports/projection_ledger_v2_1.md`
>
> **Stop condition:** any scanned vehicle is unmapped, multiply mapped, clipped away, or omitted from `total_physical_vehicles()`.

### Required artifact/schema

Every action/state pair must carry `projection_ledger.schema_version = "projection-v2.1"`, with one row per observed source and fields `source_link`, `source_lane_scope`, `observed_veh`, `stock_id`, `queued_veh`, `in_transit_veh`, `overflow_veh`, `objective_weights`, and `assignment_evidence_id`. Totals must expose:

```text
N_scan = N_urban + N_ramp + N_offramp + N_freeway + N_exit + N_scanned_external
N_total = N_scan + N_unobservable
N_stock = N_queued + N_in_transit + N_overflow
```

### Dependency and quantitative acceptance

- Prerequisites: P0-1 physical stocks and P0-2 route proofs.
- For every state: both mass-identity absolute residuals `<= 1e-6 veh`; cumulative source-row residual `<= 1e-6 veh`.
- With `scan_ok=true`: unmapped scanned vehicles `= 0`, multiply mapped vehicles `= 0`, clipping loss `= 0`, unexplained residual `= 0`.
- `total_physical_vehicles()` equals the ledger total within `1e-6 veh` and includes ramp queues and mainline-origin queues exactly once.
- Randomly permuting input link order 100 times yields byte-identical canonical stock totals and differences `<= 1e-12 veh`.
- Replace the audit's 3% residual allowance with zero unexplained residual; a nonzero capacity violation may be reported only when the same mass appears in `overflow_veh`.

## P0-4. Eliminate runtime clipping as a mass sink

### Issue and evidence

Even after initialization, NumSim clips each movement queue independently to a movement capacity and only increments a diagnostic before deleting the excess (`vendor/NumSim-mine/src/models/urban_queue_model.py:1022-1032`). Shared receiving space is partially accounted for during sending (`vendor/NumSim-mine/src/models/urban_queue_model.py:982-1011`), but the later per-movement clip can still erase vehicles and each turn can use the full receiving-link capacity. This violates a single shared physical-stock constraint.

### Exact v2.1 amendment text

> ### D-2. Substep conservation and shared-capacity flow gating
>
> **Inputs:** D-1 projected state, physical stock capacities, movement composition, exogenous arrivals, and all urban/freeway/ramp transfer flows.
>
> **Implementation paths:** update `vendor/NumSim-mine/src/models/urban_queue_model.py`, `models/metanet.py`, and `simulation/coupling.py`. Replace post-update queue clipping with pre-transfer sending/receiving constraints against the shared stock. Keep movement queues as composition views whose sum plus in-transit occupancy is bounded by the stock; if external demand cannot enter, retain it in an explicit gate/origin queue.
>
> Emit a substep ledger with opening stock, external inflow, each internal transfer, sink outflow, closing stock, and residual. Every accepted transfer is subtracted from exactly one stock and added to exactly one stock or named sink in the same ledger interval.
>
> **Command:**
> `python -m unittest vendor.NumSim-mine.src.tests.test_physical_mass_ledger tests.test_vissim_stackelberg_adapter_fidelity`
>
> **Stop condition:** a projection/clamp changes total mass, a movement queue exceeds its shared stock without an overflow stock, or a coupling transfer is recorded on only one side.

### Required artifact/schema

`mass_ledger_v2_1.jsonl` rows require `run_key`, `step_index`, `dt_sec`, `opening_veh`, `external_in_veh`, `internal_in_veh`, `internal_out_veh`, `sink_out_veh`, `closing_veh`, `overflow_veh`, and `residual_veh`, plus per-channel urban/ramp/off-ramp/freeway breakdowns.

### Dependency and quantitative acceptance

- Prerequisite: P0-3 ledger-backed state.
- Per-substep absolute residual `<= max(1e-9, 1e-12 * opening_veh)` and full-horizon cumulative residual `<= 1e-6 veh`.
- Silent clipping count and clipped-away mass both `= 0` in normal and forced-overflow tests.
- A forced full receiving stock leaves all rejected flow in the upstream stock; opening plus inflow minus sink equals closing within `1e-9 veh`.
- For every shared stock, `sum(movement_queue) + in_transit <= capacity + overflow + 1e-9`.

## P1-1. Use observed link speed and lane queue tail in rollout delay

### Issue and evidence

`IMPLEMENTATION_PLAN.md:302-308` says VBS does not export link speed. That is stale. VBS already writes schema-v2 `link_speeds_kph`, stopped counts, and queue-tail position (`scripts/run_real_world_stackelberg_controller.vbs:1482-1494`), and the adapter reads and returns them (`evaluation/controllers/vissim_stackelberg_adapter.py:805-807`, `evaluation/controllers/vissim_stackelberg_adapter.py:1035-1051`). However, the model delay still infers distance from available vehicle slots and divides by a fixed `urban_avg_speed_km_h` (`vendor/NumSim-mine/src/models/urban_queue_model.py:518-529`; default fixed speed at `vendor/NumSim-mine/src/models/state.py:291-294`). The adapter stores the metrics only in `local_observation_summary` (`evaluation/controllers/vissim_stackelberg_adapter.py:2291-2300`).

The queue tail is also currently one minimum position across all lanes (`scripts/run_real_world_stackelberg_controller.vbs:1671-1683`), which is insufficient for lane-group stocks.

### Exact v2.1 amendment text

> ### D-3. Observed urban kinematics and FIFO delay (replace current D)
>
> **Inputs:** existing state-v2 speed/stopped/tail fields, lane-level stock geometry, and `T_u=5 s`.
>
> **Implementation paths:** retain the existing VBS fields and extend them to lane or lane-group scope. Add `urban_stock_kinematics` to `TrafficState`; initialize each physical stock with observed count, space-mean speed, stopped count, and tail position. Replace `_link_delay_steps()` with a FIFO travel-time buffer based on physical remaining distance and the current/forecast stock speed. Queue service and in-transit delay must remain distinct. Missing speed uses a documented class/stock prior and emits a fallback flag; zero speed never creates zero delay.
>
> **Commands:**
> `python -m unittest tests.test_vissim_stackelberg_adapter_fidelity vendor.NumSim-mine.src.tests.test_urban_kinematics`
> `python scripts/validate_urban_kinematics.py --paired-futures outputs/paired_future_manifest_v2_1.json --split holdout --out reports/urban_kinematics_holdout_v2_1.md`
>
> **Stop condition:** any positive-length traversal arrives in the same substep, any production stock uses the fixed global mean while an observation exists, or lane queue tails are collapsed across incompatible lanes.

### Required artifact/schema

State rows require `stock_id`, `timestamp_sec`, `length_m`, `lane_group`, `count_veh`, `space_mean_speed_kph`, `stopped_veh`, `queue_tail_from_start_m`, `observation_age_sec`, `fallback_used`, and the source-link/lane IDs. Replay output must include predicted and observed entry/exit time and tail position.

### Dependency and quantitative acceptance

- Prerequisites: P0-1/P0-2 stock geometry and J-1 paired futures.
- Same-substep positive-length arrivals `= 0`; minimum delay is one `T_u` substep.
- Halving speed with all other inputs fixed never decreases delay; moving a queue tail upstream never increases receiving supply.
- On holdout traversals: median absolute link travel-time error `<= 5 s`, p95 `<= 15 s`, and queue-tail MAE `<= 20 m`.
- Missing-speed fallback rate `<= 1%` of vehicle-weighted urban stock observations; every fallback is listed.

## P0-5. Keep exit and boundary-out stocks in the plant with physical backpressure

### Issue and evidence

The adapter currently recognizes `monitor_only_exit_links`, skips their projection, and reports their vehicles only as `exit_excluded` (`evaluation/controllers/vissim_stackelberg_adapter.py:809-830`, `evaluation/controllers/vissim_stackelberg_adapter.py:944-963`). The generator likewise gives exit links no origin (`scripts/generate_real_world_distributed_players.py:787-790`). This directly contradicts the v2 statement that all 226 exit links remain in plant state (`IMPLEMENTATION_PLAN.md:349-355`).

NumSim does contain a finite synthetic `boundary_out` sink and backpressure mechanism (`vendor/NumSim-mine/src/models/state.py:232-240`, `vendor/NumSim-mine/src/models/urban_queue_model.py:838-873`), but it uses one scalar discharge capacity and is not connected to the 226 omitted VISSIM exit links. Objective exclusion is already separately expressible (`vendor/NumSim-mine/src/models/state.py:1093-1121`).

### Exact v2.1 amendment text

> ### G-1. Physical exit/boundary-out stocks and objective dual view
>
> **Inputs:** all `monitor_only_exit_links`, lane-route terminal proofs, lane metres, observed exit flows/speeds/tails, and downstream VISSIM sink/route identity.
>
> **Implementation paths:** add every physical exit link to `physical_stock_topology_v2_1.json`; project its vehicles into `TrafficState`; replace scalar-only `boundary_out_capacity_veh_h` on the VISSIM branch with per-stock discharge capacity. Connect upstream receiving supply to actual remaining exit-stock space. Preserve two objective summaries over the identical evolved state: `objective_include_boundary=true/false`.
>
> `boundary_out` receives no exogenous arrival demand. It receives only upstream modeled flow and releases only through its physical sink capacity. Excluding it from an objective must not change any state, flow, action feasibility, or backpressure calculation.
>
> **Commands:**
> `python scripts/compile_boundary_out_stocks.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --routes outputs/lane_route_proofs_v2_1.json --out outputs/boundary_out_topology_v2_1.json`
> `python scripts/validate_boundary_backpressure.py --paired-futures outputs/paired_future_manifest_v2_1.json --out reports/boundary_backpressure_v2_1.md`
>
> **Stop condition:** any of the 226 exit links remains diagnostic-only, any exit occupancy disappears at projection, or objective mode changes the physical rollout.

### Required artifact/schema

Each `boundary_out` stock must record physical members, storage capacity, discharge capacity and calibration CI, upstream stocks/movements, sink ID, observed opening occupancy, inflow, departure, closing occupancy, spillback flag, and both objective contributions.

### Dependency and quantitative acceptance

- Prerequisites: P0-1/P0-2 topology; discharge parameters are frozen by P1-2 calibration before certification.
- All 226 legacy exit links are covered exactly once; omitted and duplicated exit members `= 0`.
- Projection and every substep conserve exit mass within the P0-3/P0-4 tolerances.
- Closing an exit reduces or preserves upstream receiving flow monotonically; reopening it drains the retained queue without mass loss.
- Include/exclude objective runs use byte-identical state/flow traces and differ in objective value by exactly the recorded boundary contribution within `1e-9`.
- Holdout spillback evaluation has at least 20 positive and 20 negative stock-events, F1 `>= 0.80`, and onset/release timing MAE `<= 60 s`.

## P1-2. Calibrate storage geometry, jam density, split fractions, and exit/ramp capacity with a frozen holdout

### Issue and evidence

The urban-capacity script pools every assigned link by `(upstream SC, owner SC)`, sums `length * lanes`, and derives jam density from the same late congested observation window (`scripts/derive_urban_storage_capacity.py:39-66`, `scripts/derive_urban_storage_capacity.py:103-128`). Its comment mentions a parallel-mode treatment that is not implemented (`scripts/derive_urban_storage_capacity.py:14-17`). The audit notes that 140.5 veh/km/lane is 41.8% above the low-demand estimate and that 186 storages have not been classified by lane connectivity (`reports/plant_fidelity_audit.md:102-106`).

The production observation split remains provisional at 0.35/0.50 (`evaluation/calibration/vissim_network_calibration_v3_prediction_audit_20260629.json:242-248`), and that calibration artifact is itself marked heldout-failed and points at a different source network (`evaluation/calibration/vissim_network_calibration_v3_prediction_audit_20260629.json:5-20`). The current audit passes storage whenever jam density and capacities are merely positive (`scripts/audit_plant_fidelity.py:486-515`, `scripts/audit_plant_fidelity.py:1734-1741`). The v2 H section has no split manifest, estimator, uncertainty, or verdict thresholds (`IMPLEMENTATION_PLAN.md:359-364`).

### Exact v2.1 amendment text

> ### H-1. Frozen physical-parameter calibration protocol
>
> **Inputs/runs:** demand multipliers 0.75/1.0/1.25, seeds 13/29/47, 3,600 s, with network/action/signal hashes. Training cells are seeds 13 and 29 at demand 0.75 and 1.0 (4 runs). Congested model-selection cells are seeds 13 and 29 at demand 1.25 (2 runs). The untouched holdout is seed 47 at all three demands (3 runs). Split by whole run; no anchor or row from a holdout run may enter fitting or threshold selection.
>
> **Implementation paths:** replace SC-pair pooling in `scripts/derive_urban_storage_capacity.py` with disjoint lane-section accounting from A-0/B-1. Keep independent parallel branches as independent stocks unless a physical merge and shared queue-tail observation prove a common reservoir. Fit jam density from training saturated lane groups (`speed <= 3 kph`, stopped fraction `>= 0.5`) using a run-clustered robust estimator and bootstrap by run. Compare it with the VISSIM vehicle-length plus standstill-distance geometry prior. Fit fallback queue/in-transit split parameters only where lane-level tail observations cannot identify the split. Fit per-stock ramp and boundary discharge/storage parameters. Freeze one calibration JSON before opening seed 47.
>
> **Commands:**
> `python scripts/fit_physical_stock_calibration.py --run-manifest outputs/calibration_run_manifest_v2_1.json --topology outputs/physical_stock_topology_v2_1.json --train seeds13,29:demand0.75,1.0 --select seeds13,29:demand1.25 --out evaluation/calibration/physical_stock_calibration_v2_1.json`
> `python scripts/validate_physical_stock_calibration.py --calibration evaluation/calibration/physical_stock_calibration_v2_1.json --run-manifest outputs/calibration_run_manifest_v2_1.json --split seed47 --out reports/physical_stock_calibration_holdout_v2_1.md`
>
> **Stop condition:** train/holdout hashes overlap, fewer than 30 independent saturated lane groups or 200 saturated lane-group samples support jam fitting, a pooled stock crosses an unproven parallel branch, or any promoted parameter lacks a confidence interval and source-run IDs.

### Required artifact/schema

`physical_stock_calibration_v2_1.json` requires network/topology/signal hashes, exact run IDs and split, estimator name/version, sample counts, geometry prior, fitted value, run-cluster bootstrap 95% CI, per-stock lane metres/capacity, per-class split fractions and fallback rules, per-ramp queue capacity, per-exit discharge capacity, training loss, selection loss, and a sealed holdout hash. The holdout verdict is a separate artifact written only after the calibration file is frozen.

### Dependency and quantitative acceptance

- Prerequisites: P0 topology and conserved projection; J-1 capture harness may collect runs, but no controller ranking is needed to fit physical parameters.
- Train/selection/holdout run overlap `= 0`; all nine expected run keys present.
- Jam-density bootstrap 95% CI half-width `<= 10%` of the estimate; frozen estimate differs from the geometry prior by `<= 15%` or the task stops for a documented vehicle-class/spacing investigation.
- On seed-47 holdout, per-stock occupancy exceeds calibrated physical capacity in no more than `0.5%` of stock-time rows; all excess is conserved as upstream/overflow mass.
- Where queue split is observed, holdout queued-vehicle MAE `<= max(2 veh, 10% of observed queue)` and total signed bias `<= 5%`; fallback fraction usage `<= 10%` of vehicle-weighted observations.
- Capacity parameters refit on each training seed separately differ by `<= 15%`; otherwise report `BLOCKED`, not an averaged value.
- The auditor must fail, not pass, on missing split provenance, missing CI, holdout failure, or a stale network hash.

## P0-6. Preserve each physical ramp queue and exact merge/diverge location

### Issue and evidence

Ramp capacity derivation is hard-coded to eight connector IDs and four model keys and sums two physical connectors into one queue (`scripts/derive_ramp_queue_capacity.py:33-37`, `scripts/derive_ramp_queue_capacity.py:80-90`, `scripts/derive_ramp_queue_capacity.py:114-120`). The freeway mapping explicitly allows a ramp group's physical meters to straddle segments and then injects all flow into a representative segment (`scripts/generate_real_world_control_mapping.py:527-546`; approximation documented at `scripts/generate_real_world_control_mapping.py:921-928`).

Although `NetworkConfig.ramp_queue_cap(ramp)` exists, physical dynamics still use the scalar cap in several paths (`vendor/NumSim-mine/src/models/urban_queue_model.py:357-365`, `vendor/NumSim-mine/src/models/urban_queue_model.py:932-950`, `vendor/NumSim-mine/src/models/metanet.py:744-750`, `vendor/NumSim-mine/src/simulation/coupling.py:242-247`). Therefore the plan's statement that 93.0-145.9 veh values are validated does not make them authoritative in the rollout.

### Exact v2.1 amendment text

> ### E-5. Physical ramp and off-ramp stocks (new P0 before D/E replay)
>
> **Inputs:** lane-route graph, all ramp-meter and off-ramp connectors, signal-head position, mainline chain coordinates, observed connector counts/tails/flows, and calibration H-1.
>
> **Implementation paths:** derive ramp groups from the `.inpx` and control mapping, not hard-coded ID lists. Keep one queue stock per physically independent connector/lane group; a shared controller may command several stocks. Inject each stock's accepted flow at its own physical merge coordinate/segment. Preserve each off-ramp diverge coordinate and stock. Remove representative-segment relocation from the production branch and use `ramp_queue_cap(stock_or_ramp)` in every physical path.
>
> **Commands:**
> `python scripts/compile_ramp_freeway_topology.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --control-mapping evaluation/real_world_modi_control/control_mapping.json --out outputs/ramp_freeway_topology_v2_1.json`
> `python scripts/validate_ramp_freeway_topology.py --topology outputs/ramp_freeway_topology_v2_1.json --states <state-manifest.json> --out reports/ramp_freeway_topology_v2_1.md`
>
> **Stop condition:** an independent connector queue is averaged with another queue, a physical merge/diverge is relocated, a production code path uses the scalar cap when a per-stock cap exists, or accepted/rejected off-ramp flow is not conserved.

### Required artifact/schema

For each physical ramp queue: connector/lane members, control group, queue capacity and CI, upstream stock, exact merge mainline/chain position/segment, meter head position, observed count/tail, requested/accepted flow. For each off-ramp: exact diverge position/segment, split evidence, storage stock, downstream receiving stocks, and blocked-flow ledger.

### Dependency and quantitative acceptance

- Prerequisites: P0-2 route graph and P1-2 frozen capacities before certification.
- All eight installed ramp-meter connectors are represented as physical queue stocks and exactly four command groups; missing/duplicate connector count `= 0`.
- Physical merge/diverge segment mismatch and representative-segment relocation count `= 0`.
- Group flow equals the sum of physical connector flows within `1e-9 veh` per substep; no connector count is divided by list length without observed route/lane evidence.
- Holdout ramp queue MAE `<= max(3 veh, 10% of capacity)` and ramp/off-ramp flow WAPE `<= 10%/15%` respectively.
- Off-ramp rejected mass is `0`; if supply blocks a diverge, the blocked mass remains in the freeway sending segment.

## P1-3. Certify freeway state, flux, and coupling rather than count reconstruction

### Issue and evidence

The adapter initializes freeway density and speed from segment counts and speed sums (`evaluation/controllers/vissim_stackelberg_adapter.py:2255-2277`), so count reconstruction is algebraic. The audit correctly says 100% capture does not validate segment dynamics, speed, travel time, or ramp/off-ramp flux (`reports/plant_fidelity_audit.md:126-130`). The base adapter still contains uniform synthetic defaults while relying on later override order for real geometry (`evaluation/controllers/vissim_stackelberg_adapter.py:1905-1951`). This needs an artifact-level proof, not comments and override precedence.

### Exact v2.1 amendment text

> ### E-6. Freeway physical topology and dynamic certification
>
> **Inputs:** exact mainline chain/lane geometry, segment measurement bounds, per-segment count/speed, mainline origin counts, P0-6 merge/diverge topology, VSL coverage, and paired futures.
>
> **Implementation paths:** make `freeway_topology_v2_1.json` the only production source for segment lengths, lane profiles, buffer boundaries, VSL coverage, origins, sinks, and every ramp/off-ramp coordinate. Configuration fallback values are allowed only in synthetic tests and must emit `synthetic_topology=true`. Extend the mass ledger through origin queues, core/buffer segments, ramp merges, off-ramp diverges, and terminal exits.
>
> **Commands:**
> `python scripts/validate_freeway_physics.py --topology outputs/freeway_topology_v2_1.json --paired-futures outputs/paired_future_manifest_v2_1.json --split holdout --out reports/freeway_physics_holdout_v2_1.md`
>
> **Stop condition:** a production run uses a fallback length/lane/index, a ramp/origin queue is absent from freeway total mass, or count reconstruction is reported as dynamic fidelity.

### Required artifact/schema

The topology artifact must list ordered physical chain members, non-overlapping segment bounds, lane metres, measured and controlled extents, exact origin/sink and ramp coordinates, and source hashes. Validation rows must include count, density, speed, mainline flow, ramp inflow, off-ramp outflow, terminal outflow, queue counts, TTT, and mass residual by segment and horizon.

### Dependency and quantitative acceptance

- Prerequisites: P0-4 ledger, P0-6 ramp topology, D-3 kinematics, and J-1 paired futures.
- Segment bounds cover each physical mainline chain exactly once: gap `= 0 m`, overlap `= 0 m`; all production fallback flags `= 0`.
- H=1 holdout: per-segment count MAE `<= max(3 veh, 5% of observed count)`, speed MAE `<= 5 kph`, speed MAPE `<= 10%` for observations `>= 5 kph`, and mainline flow WAPE `<= 10%`.
- H=15 holdout: freeway TTT absolute percentage error `<= 20%`; direction-specific signed count bias `<= 5%`.
- Freeway/ramp/off-ramp/terminal mass residual meets P0-4 on every substep.

## P2-1. Add fail-closed physical validation gates with canonical paired futures

### Issue and evidence

The current matrix runner only creates baseline runs, not anchor branches, perturbations, or model/VISSIM paired futures (`IMPLEMENTATION_PLAN.md:426-445`). The current auditor has no dynamic physical gates; projection can pass with 3% residual and explained clipping, storage passes on positivity, and signal timing is unconditionally `NOT_EVALUATED` (`scripts/audit_plant_fidelity.py:1580-1604`, `scripts/audit_plant_fidelity.py:1710-1741`, `scripts/audit_plant_fidelity.py:1780-1786`). The existing J thresholds cover only ranking (`IMPLEMENTATION_PLAN.md:447-450`). The audit lists queue, speed, flux, TTT, spillback, and horizon errors as unmeasured (`reports/plant_fidelity_audit.md:86-88`).

### Exact v2.1 amendment text

> ### J-0. Canonical paired-future protocol and physical gates (replace J-1/J-3/J-4)
>
> **Inputs:** the nine 3,600 s baseline runs, anchors 900/1500/2100/2700 s, horizons H=1/3/5/10/15, exact action perturbations, frozen physical calibration, and all source hashes.
>
> **Harness:** run every future from t=0 to preserve VISSIM prefix state. For an anchor branch, require byte-identical prefix telemetry through the anchor for the same demand/seed. Apply the candidate action at the first VISSIM step after the anchor for exactly one 60 s control interval unless the experiment declares a longer duration. Store low/base/high physical actuator readback, not only requested action. Use a canonical run key `(network_hash, signal_hashes, topology_hash, calibration_hash, demand, seed, anchor_sec, horizon, lever, level, replicate)`.
>
> **Implementation paths:** add `scripts/run_plant_fidelity_paired_futures.ps1`, `scripts/build_paired_future_manifest.py`, and dynamic gates to `scripts/audit_plant_fidelity.py`. Extend, do not repurpose, the baseline matrix runner.
>
> **Commands:**
> `powershell -File scripts/run_plant_fidelity_paired_futures.ps1 -Manifest outputs/paired_future_request_v2_1.json -Sequential`
> `python scripts/build_paired_future_manifest.py --runs evaluation/runs/plant_fidelity_v2_1 --out outputs/paired_future_manifest_v2_1.json`
> `python scripts/audit_plant_fidelity.py --paired-futures outputs/paired_future_manifest_v2_1.json --physical-calibration evaluation/calibration/physical_stock_calibration_v2_1.json --report reports/plant_fidelity_audit_v2_1.md`
>
> **Stop condition:** prefix mismatch, stale hash, missing state/action/readback pair, fewer than the required support rows, a macro average hiding a failed demand/seed/anchor/H=1 cell, or any required gate is `NOT_EVALUATED` on the congested holdout.

### Required artifact/schema

`paired_future_manifest_v2_1.json` must bind every run to network, `.sig`, active-program schedule, topology, calibration, NumSim source, adapter source, state/action hashes, VISSIM seed/demand, anchor, action effective time/duration/readback, horizon, sampling interval, and parent-prefix hash. Comparison rows must be keyed by stock/segment/channel and contain opening/observed/predicted values plus units.

### Dependency and quantitative acceptance

All topology/projection/dynamics/calibration work above is prerequisite. Promotion requires every applicable holdout cell to pass, not only an aggregate:

| Gate | Required verdict |
|---|---|
| Prefix parity | Same demand/seed parent prefix: count/speed/action telemetry hash identical through anchor; mismatches `= 0` |
| Projection | P0-3 identities, unmapped `= 0`, clipping loss `= 0` at all 36 anchors |
| Runtime conservation | P0-4 residual at every urban/freeway substep |
| Urban stock/queue H=1 | Capacity-normalized absolute error `<= 0.10`, signed total bias `<= 0.05`, active-stock median count error `<= 2 veh` |
| Urban travel H=1 | D-3 median `<= 5 s`, p95 `<= 15 s`, queue-tail MAE `<= 20 m` |
| Freeway H=1 | P1-3 count/speed/flow thresholds |
| TTT by horizon | Absolute percentage error: H1 `<= 10%`, H3 `<= 12%`, H5 `<= 15%`, H10 `<= 18%`, H15 `<= 20%` |
| Flux | Urban boundary-in/out and ramp WAPE `<= 10%`; off-ramp WAPE `<= 15%` |
| Spillback | At least 20 positive and 20 negative events on congested holdout, F1 `>= 0.80`, onset/release MAE `<= 60 s` |
| Action ranking | Per demand/seed/anchor/horizon/lever Spearman `>= 0.70`, top-action pairwise `>= 0.80`, repeated material-effect sign reversals `= 0` |
| H=1 protection | H=1 is reported and gated separately; failure cannot be averaged with longer horizons |
| Runtime | Existing production gate remains p95 `<= 30 s`, max `<= 45 s`; timeout/fallback counts `= 0` for certification runs |

Low demand may report spillback `NOT_EVALUATED` only when it has fewer than five positive events. That does not waive the congested holdout support requirement. Any missing congested physical gate is `BLOCKED`, never PASS.

## Required dependency graph

The physical portion of the v2.1 dependency graph should be replaced with:

```text
S0 source/baseline + S1 active program/routes
  -> P0-2 lane graph and route proofs
  -> P0-1 single physical-stock topology
  -> P0-3 conserved initial projection
  -> P0-4 substep mass ledger

P0-2 -> C movement/SG mapping
P0-1 + P0-2 -> P0-5 exit/boundary-out stocks
P0-1 + P0-2 -> P0-6 exact ramp/off-ramp stocks

P0-3 + capture harness -> P1-2 train/select/holdout calibration
P0-1 + observed state -> P1-1 urban kinematics
P0-4 + P0-6 + P1-1 -> P1-3 freeway/coupling dynamics

All P0/P1 physical tasks + exact signal oracle/cycle support
  -> J-0 paired futures and physical gates
  -> K audit rerun
  -> promotion decision
```

No J/K promotion run may start with an unresolved physical tie, a synthetic production edge, a stale topology/calibration hash, a nonzero projection loss, or an unopened physical gate. Collection-only baseline runs may proceed earlier but cannot be cited as certification.

## Coverage of requested topics

| Requested topic | Amendment |
|---|---|
| Link ownership and shared physical stocks | P0-1 |
| Deterministic BFS/leg geometry | P0-2 |
| Projection mass accounting and clipping | P0-3, P0-4 |
| Link speed/queue delay | P1-1 |
| Exits and boundary-out backpressure | P0-5 |
| Storage capacity/fraction train/holdout calibration | P1-2 |
| Ramps/freeway | P0-6, P1-3 |
| Physical validation gates | P2-1 |

## Final reviewer concern

The largest immediate risk is not parameter error but state ontology: until physical stock, ownership, visibility, and objective attribution are separate, improved calibration can make duplicated or deleted mass look numerically better without making the rollout physically faithful.
