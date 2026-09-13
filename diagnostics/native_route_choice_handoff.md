# Native inputs 1086/1087: finite route-source integration

The existing route-choice engine now accepts finite generation from native inputs 1086/1087, preserves observed current routes, applies the native 200:150 choice only at an eligible future decision, and uses the actual unactuated SC15 fixed signal. The software and accounting checks pass; the inherited service capacity is not a calibration of actual SC15 discharge.

## Files and configuration

Production ownership is limited to `evaluation/controllers/route_choice_corridor.py`. Append these two paths to the existing `urban.route_choice_corridor.evidence_paths`, keeping the original 1128/1129 paths:

- `diagnostics/route_choice_corridor_1099_ver2.json`: input 1086, physical source 343, finite storage `native_1086_choice`, SC15/SG5.
- `diagnostics/route_choice_corridor_1100_ver2.json`: input 1087, physical source 341, finite storage `native_1087_choice`, SC15/SG1.

Hubble's native input contract must include each corresponding row with `target_kind="route_choice"`, the matching `target_storage`, `physical_source`, `source_decision` 1099/1100, `approach_path=[source]`, and `physical_projection_links=[]`. Its extended input evidence is maintained separately. The existing canonical initialization and urban-step hooks need no additional change.

`generated_input_contracts(cfg)` exposes the validated contracts. Native generation owns finite admission and backlog, adds accepted physical stock and emits `input:internal:<number>` once, then calls `receive_generated(state,cfg,input_no,accepted,index)`. Receipt only reserves the route cohort and refuses a duplicate receipt. It never creates an arrival/release shadow or a second ledger event. Route `advance` runs before native `advance`, so new admitted vehicles cannot depart in the same step.

Both branches at each one-lane source share one inherited service budget. Pre-head cohorts additionally use the source's native GREEN overlap; observations already past the head are not stopped at that head again. The program parser object is cached per process, while only pinned primitive evidence is serialized in cfg. This keeps fresh worker and candidate copies valid.

## Evidence and verification

The network, input/decision/branch geometry, source head, selected-controller exclusion, actual SC15 FIXEDTIME/progNo1/controller offset0, and SIG file hashes are validated by configure. Source-only prefix ownership replaces the old source projection exactly once. All branches resume the existing `SC1_to_SC101` or `SC101_to_SC1` receiver.

`native_sc15_clock_audit.json` compares SG1/SG5 to the completed native LSA: each has 102 transitions; all event states, program phases, integer-second states and GREEN overlap from second 23 through 5399 agree. Native cycle is 160s, program offset61s, and each group has 35 GREEN seconds per cycle. The first 23 seconds lack explicit LSA states and are excluded from that observed comparison. Dewey independently checked the source hashes and geometry.

Command (Windows UTF-8 mode required by the existing fixtures):

```powershell
& $python -X utf8 -m unittest diagnostics.test_native_route_choice diagnostics.test_route_choice_corridor diagnostics.test_route_choice_1128 -q
& $python -X utf8 -m diagnostics.probe_native_route_choice
```

28 tests passed: 11 new tests plus 17 existing corridor tests. Coverage includes all eight actual route-bearing anchors 900..5400 with exact initial Ω stock and zero initial events; observed route preservation; future-choice eligibility; accepted-once generation; red and full-receiver holding; one-lane shared budget; past-head observations; candidate copies; fresh process pickle; actual 450-second endpoint closure; and Ω OFF physical equivalence.

`native_route_choice_integration.json` pins the actual held-action 900/2700→450s runs, explicit effective input contract and source hashes. The final execution has `source_changes=[]`; every 150-second inventory closes, candidate input is unchanged, and held unknown route stock is zero. This is an endpoint integration test, not an optimizer or a VISSIM run.

## Material model limitation

The inherited service scale is 206.530612 veh/h/lane. Applying the actual 35/160 green ratio allows only 45.178571 veh/h before receiver blocking, while the 900s source input requests 280 veh/h. The 450-second run therefore fills both finite source stores: desired35 vehicles each, accepted admission16.2992/15.1094, unadmitted backlog18.7008/19.8906. Actual SC15 head discharge and the provenance of that inherited capacity are the next independent audit; no value was raised or fitted here.

The 2–4m head-to-branch gap is represented by gating branch acceptance rather than another reservoir. Aggregate route cohorts do not recover microscopic one-lane head-of-line blocking. Native 200:150 weights are conditional route priors, not capacity or performance calibration. Downstream dynamics after the short native route endpoints remain the existing receiver model.
