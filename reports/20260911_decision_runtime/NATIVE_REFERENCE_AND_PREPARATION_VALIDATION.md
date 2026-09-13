# Native reference and preparation tests

2026-09-11. Tests only; no production edits, model endpoint, VISSIM start or COM access.

## Native initial reference

`diagnostics.test_native_runtime_reference`: 6 PASS, 2.024 seconds.

The actual baseline network binds all 17 declared source programs to the expected `.sig` SHA256, active program number, controller offset and active fixed-time controller type. Altering program, program number, controller offset, active flag or type, or removing SC7, causes refusal.

The represented no-control action exactly contains the source greens and offsets: SC7 `(67,90,0,24)`, offset119; SC16 `(63,17,27,0)`, offset1. VSL, meters, NP/NUF and allocation fields are unchanged; the proof declares `new_com_command=False`. The disabled path returns the same action and does not read a source or plan. A partial native cohort is refused.

Historical reference loading accepts the exact native proof and rejects nominal archived warmup, missing proof, stale plan SHA and incorrect offset before meter preparation. The downstream meter preparation is stubbed in this signal-boundary test; its implementation is covered separately by the historical-meter tests. The actual runtime setup calls source validation only when the explicit source minimum policy is active.

## Selected config and fixed replay

`diagnostics.test_selected_native_clock_binding`: 6 PASS, 1.595 seconds.

- Default selection is exactly the existing VBS config with no added pins. Native selection requires the JSON/config pair, unchanged base config bytes and an exact rendered sibling. Missing pair/sibling, incomplete source cohort, changed base config and changed sibling are refused.
- Recording preparation reads and pins the selected config and its sibling. It includes 25 controllers / 144 owned SGs and performs no writes while planning.
- The actual PowerShell launcher was invoked without `-Execute`. It passed the selected `$proof.vbs_config` through `arguments.VbsConfig`, created no run or prepared folder and returned `execute=False`.
- The first PowerShell invocation failed before preparation because inherited environment enumeration reported a duplicate key. Explicit `env=dict(os.environ)` in the test subprocess removed that environment-block issue; production launcher code was not changed.
- Native fixed signal replay preserves SC7 cycle120 with an independent p1 move and SC16 cycle150 with paired green redistribution. Offset wrap uses the native cycles. `fixed_actuation(actuation,tuning)` preserves the RM_C10639 g9 override: physical command g9/rate810, other seven meters g10. Absent native basis retains legacy cycles190/116 and default proportional all-open meter actuation.

## Existing exact preparation regression

Initial `diagnostics.test_selected_native_recording` result: 5 PASS, 1 FAIL, 5.656 seconds. The preserved-r03 exact six-tuple test failed because `package()` added `report['vbs_config']` even when native clock selection was absent. The test was not weakened and its historical fixture was not changed.

Root corrected the absent-option behavior: `report.vbs_config` is added only when explicit signal sources are selected, and PowerShell uses the original config when that field is absent. The requested rerun of `diagnostics.test_selected_native_recording` plus `diagnostics.test_selected_native_clock_binding` passed all 12 tests in 6.395 seconds. This includes the unchanged historical exact six-tuple comparison, selected native config propagation, and the actual PowerShell planning path. The earlier failure is retained here to distinguish the original result from the corrected result.

The fixed signal diagnostic applies physical meter overrides in the writer helper. `build_control()` itself does not rewrite uncontrolled grouped meter rates or add the physical-meter diagnostic representation. Therefore g9 execution must be verified from actual CSV/native signal evidence; reusing its JSON as a future actual-action anchor needs a separate consistency check.
