# NC v2 observer smoke QA — 1050 seconds

The run completed normally. Collection/provenance checks pass, but the full ordered trajectory equality check fails for 52 rows in the final 20 seconds. Do not describe the collector as proven behavior-neutral over all 1050 seconds.

Run: `codex_contract_observed_nc_s13_1050_v2_20260910`, run ID `787fedf55fc1494b820d8e2665c2c925`. The stopped v1 run and its source/configuration remain separate evidence. This report uses the v2 run manifest and recorded commands, not any later model source revisions.

## Observed windows and consumer evidence

| Decision | Window | Transitions | Updated groups | Carried groups | Current floor keys |
|---:|---|---:|---:|---:|---:|
| 1 | [1, 1] | 0 | 0 | 0 | 0 |
| 150 | [1, 150] | 149 | 0 | 0 | 0 |
| 300 | [150, 300] | 150 | 5 | 0 | 5 |
| 450 | [300, 450] | 150 | 9 | 5 | 11 |
| 600 | [450, 600] | 150 | 15 | 11 | 19 |
| 750 | [600, 750] | 150 | 18 | 19 | 24 |
| 900 | [750, 900] | 150 | 17 | 24 | 28 |
| 1050 | [900, 1050] | 150 | 16 | 28 | 29 |

All 235 configured physical head identities/lanes/SGs and exactly serialized coordinates match the pinned INPX in all eight snapshots. Seven nonempty windows contain 1,645 head-window comparisons: actual GREEN exposure equals the pinned native program integer left-step integral in every case. Native ownership covers every second; controlled/unverified exposure is zero. The first [1,1] window correctly has no transition and is not admitted as valid flow evidence. Subsequent windows are adjacent, with no overlap or gap.

The same run/config/network/quality provenance identity is retained. Candidate ends equal their snapshot time; new floor keys have two adjacent recorded candidate windows, and previous floors are preserved. Updated-group counts do not mean that many capacities increased: a floor can equal the existing installed base capacity. The consumer reports 19 groups with no model members at every decision; this smoke does not claim those groups received capacity updates.

## Independent native signals and actual command comparison

The native `.lsa` protocol has 6,051 identical raw state-change rows from 1–1050 in both runs (SHA `eefd581aef8b39f4a851599574cdb438d8c269ca19c13121de2531446013d1f2`). This covers native SC2/16/17 as well as the selected controllers. It rules out a recorded SG-state difference in this interval.

The new stepwise NC applies at 1/150/300/450/600/750/900/1050; the reference continuous NC applies at 1 and900. Each application writes 66 freeway DSD selectors to120 for vehicle classes10/20/30/70, including unchanged values, plus eight all-green ramps. Physical vectors and readbacks are identical at every new application to the reference900 vector. No urban signal command row is applied. `SetClassSpeedChecked` assigns a DSD distribution selector, not the global distribution curve or an individual vehicle speed. The first differences occur away from applied DSD links: no DSD exists on source341 or any of the nine vehicles' retained1020–1050 physical links. This does not prove that repeated writes or indirect traffic effects have no simulator-internal effect.

## Ordered trajectory comparison

Both prefixes have exactly 1,992,241 rows and the same one-second frame set, header, vehicle IDs, order, links, lanes, lateral positions and time-in-network fields. All rows through1030 are byte-identical. There are52 changed rows from1031–1050: POS52, SPEED41 and DELAYTM17. Maximum absolute differences are26.79m,37.66km/h and1.46s respectively. The total payload lengths differ by5bytes; that is a length difference, not five harmless formatting differences.

Identical physical link/vehicle series support identical link-based Ω stock and observed crossing samples in this prefix. They do not establish identical speed, stopped queues, physical positions or freeway cell assignment. Terminal position-based inference and any aggregate measurements are not recomputed or silently declared exact by this audit.

| Vehicle | First observed source record | First difference | Changed rows | First-difference link |
|---:|---|---:|---:|---:|
| 2347 | t=391, link117, speed40.83 | 1049 | 2 | 10265 |
| 2714 | t=447, link26, speed42.44 | 1041 | 10 | 1220008301 |
| 4187 | t=690, link13, speed43.56 | 1050 | 1 | 10396 |
| 4542 | t=745, link113, speed44.57 | 1050 | 1 | 1210009403 |
| 5627 | t=912, link341, speed20.60 | 1031 | 20 | 255 |
| 5659 | t=916, link201, speed42.09 | 1050 | 1 | 1210009700 |
| 6070 | t=965, link341, speed17.28 | 1037 | 14 | 10408 |
| 6423 | t=1007, link236, speed37.89 | 1049 | 2 | 10396 |
| 6484 | t=1016, link236, speed23.99 | 1050 | 1 | 254 |

The first vehicle5627 entered source341 at912s (native input1087), then at1030 was on connector10401 at3.74m/39.69km/h in both runs. At1031 it is on255 lane2: target1.90m/40.30km/h versus reference1.94m/40.59km/h. Vehicle6070 likewise originates on341 at965s and differs from1037. Other first differences occur later across native SC2/16/17 approaches. Exact short traces and native geometry are retained in `observer_smoke_v2_last20_context.json`; source appearance uses actual nearby frames, not only a time-in-network subtraction. The extra binary-seek read was bounded to17MB total.

## Native error capture and timing limits

Final raw runtime/setup/DLL files are preserved under `native_runtime_error_capture/codex_contract_observed_nc_s13_1050_v2_20260910_complete_20260910T015802064795Z`. Runtime parsing is complete: ten explicit lane-change removals, five insideΩ/five outsideΩ, none on terminal24/120. The native remaining input1099 quantity is32; this is the end-of-period admission residual, not completed output. Native ERR contains no embedded run ID; network/manifest/time association is explicit and preserved.

The exact `Stop the simulation? : &Yes` note has no simulation or wall timestamp. It follows the1045 warning in file order and precedes the unfinished-input/DLL notices. Normal VBS code sets SimPeriod=requested+1, finishes its step loop at1050, reports SIM_DONE, then releases the Vissim object. That is relevant shutdown context, but the raw note alone neither proves when the prompt was answered nor establishes a cause for1031 differences.

The parent watchdog reports622s elapsed. Eight logged decision child calls total23.61s;598.39s remains unattributed. No per-component PerfReport rows were enabled, so startup/loading, simulator time, COM reads, serialization and cleanup cannot be separated quantitatively. The collector records1,050 verified capture batches (four bulk attribute calls each) and45 same-time cache reuses. This demonstrates cache operation, not a measured wall-time saving.

## Smallest discriminating next run

Use a separate1050s seed13 NC run with the head-observation config disabled and the existing runner `-ForceStepwise` option enabled. This preserves the v2 RunSingleStep path, actual SimPeriod1051, and1/150/.../1050 action reapplication schedule. Plain headOFF NC would select continuous execution and change another variable. Compare its prefix with both retained runs. If it matchesv2 but not the5400 reference, there is no demonstrated collector-only effect; horizon versus mode/reapplication remains to distinguish. If it matches the5400 reference but notv2, the observer bundle becomes implicated, with repeatability still worth checking. No cause or neutrality is assumed in advance. No further VISSIM run was started by this audit.

## Evidence and checks

- `observer_smoke_v2_complete.json`: original completion, window, program and prefix-hash result, preserving `ordered_payload_exact=false`.
- `observer_smoke_v2_trajectory_differences.json`, `observer_smoke_v2_last20_context.json`: raw-field differences and bounded physical traces.
- `observer_smoke_v2_native_lsa_comparison.json`, `observer_smoke_v2_actuation_performance.json`, `observer_smoke_v2_reapply_scope.json`: native SG/command/timing source evidence.
- `test_signal_observation_smoke_audit.py`: four small frame/order/censoring/provenance/carry checks passed. The preceding actual150 precision fix and installed observer regressions passed15 tests; they are recorded separately in `observer_head_precision_failure.json`.
