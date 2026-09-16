# Local ramp 1 s refinement — 2026-09-16

The frozen first native-response evaluation exposed a spatial timing problem: every assessed arm/window allowed modeled post-head stock above the nominal 6.43 m storage. The 1350 s cases reached 4.2 vehicles for NC/VSL and 3.24 for RM/both, compared with native peak 2 and nominal spacing-derived capacity 1.071. Those first predictions and sources remain preserved in `native_response_v1`; this refinement was not selected by optimizing their cost or merge-count errors.

## Change and scope

`PhysicalRampBoundary.advance_local_interval` now offers an explicit local 1 s cycle calculation. The canonical component harness uses it only when `ramp_dynamics.local_step_sec=1` and the explicit `meter_cycle_sec` equals the existing 10 s freeway interval. Absent the option, or with explicit 10, the prior path is retained.

At each 10 s start, the harness calls the existing canonical receiving query once on a scratch state with nonbinding target-ramp availability. This gives a receiving **budget**, not an accepted merge or a source of live vehicles. All coefficients, receiving formulas, FD functions, METANET interval and mainline state update are unchanged.

Within that 10 s interval, each local second advances existing travel cohorts, accepts a merge limited by eligible vehicles and the uniform receiving-rate envelope, applies actual RED/GREEN head service, and admits forecast approach arrivals. New head departures retain positive post-head travel and may merge in a later local second of the same 10 s interval. The actual accepted sum becomes the freeway's supplied merge rate. Any floating-point interface residual is recorded and must stay within 1e-8 vehicles.

Head service keeps the existing service-table budget: g8 gives 3.24 vehicles spread over its first eight green seconds, g6 gives 2.34 over six, and g4 gives 1.44 over four. Red gives zero. The interval ending at t+1 matches the native t+1 signal sample. OFF remains a separate mode with the existing continuous g10 proxy 4.2/10 vehicles per second; this proxy is still an unverified actuator assumption. No extra startup-loss coefficient was fitted or deducted.

The post-head free-space bound is `(length-head)*lanes/spacing`. Initial observed excess is retained: no vehicle is deleted or moved backward, and new head service waits for space. This is a conservative fluid bound, not an exact microscopic front-position packing law. Native two-front occupancy of a short segment is not labeled inherently impossible.

The driver still receives 45 aggregate 10 s ramp records per 450 s forecast. Each record includes its ten local receipts, actual merges/head transfers/admissions, beginning/end stocks, receiving budget/envelope, post-head space and 1 s connector residence. The aggregate `eligible_merge_veh` is explicitly labeled as first-local-step eligibility; total accepted merge may include vehicles becoming eligible later. Outside-component backlog remains conserved and excluded from connector residence; no Ω cost claim follows.

## Verification

- Seven new helper tests pass: free-flow throughput after pipeline warmup remains 4.2 vehicles/cycle; zero receiving blocks further head service once short storage fills; red clears previously committed cars only; correct green/red sequence and cycle budget; initial two-vehicle post-head excess remains without deletion and clears; uniform supply envelope and exact conservation; valid 1 s stock-time cost; malformed request rejection before mutation.
- Three new harness tests pass: complete serialized predictions for both NC and combined-control 1350 s history windows exactly match frozen v1 with absent or explicit 10 s option; the local path queries receiving exactly 45 times, retains the 10 s freeway interval, exports 45×10 local receipts, transfers actual merge sums into freeway accounting, keeps west cells/flows identical, and rejects unsupported step/cycle settings.
- Six existing harness tests and eight existing helper tests pass. The preexisting no-ramp result structure and numerical hash remain unchanged.
- AST parsing passed for the two changed source files and two new tests. No VISSIM run, vendor/adapter edit, parameter search, native demand/network change or service-table change was made by this refinement.

The first new tests failed because the new local API did not yet exist. A later strict stock assertion encountered only 20 versus 19.999999999999996 and was expressed using the existing conservation precision. Frozen-output comparison initially compared in-memory immutable tuples with their persisted JSON arrays; comparing the full canonical JSON serialization then passed exactly, without numerical tolerance or omitted fields.

## Remaining validation

This fixes the previously identified unbounded post-head point queue and coarse head-to-merge clock. It does not promise better calibrated throughput: allowing physically timely passage can increase predicted merges and therefore worsen an existing overprediction. The next frozen response run must report that outcome as found. Local 1 s travel remains an approximation, finite post-head storage is nominal, mean service does not reproduce individual start-up/headway behavior, and the full urban waiting/coupled controller response is still outside this component test.
