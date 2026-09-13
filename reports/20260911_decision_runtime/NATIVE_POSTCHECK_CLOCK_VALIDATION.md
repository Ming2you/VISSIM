# Native postcheck command clock

2026-09-11. Updated only the existing `diagnostics/com_execution_equivalence/command_clock.py` and `verify_pair.py` production diagnostic paths, with focused tests. No runner/adapter changes and no VISSIM/model execution.

The prior postcheck reused a legacy oracle that suppresses a signal group's AMBER whenever any SG in that controller is GREEN. That would incorrectly reject the validated native SC7 program at phase67–70: SG4/8 are AMBER while SG7 remains GREEN.

`native_clock_options()` now reads the explicit `RW_SIGNAL_NATIVE_CLOCKS` literal from the SHA-verified generated SG-plan sibling. Missing/empty native config preserves the original oracle. Native tokens require a complete owned controller cohort, valid kind, cycle, idle and phase mask. The clock verifies native command bounds, source cycle, axis/window offset agreement and the SC7 paired-green/clearance constraints. It retains own-SG AMBER only for these explicitly configured controllers; native mode is never inferred from CSV windows.

All three existing verifier entry points now pass this pinned source contract to `CommandClock`. Immediate/post-step readback checks, LDP command comparisons and the direct changed-writes scan use the same optional oracle. The LSA coverage function, independent failure state and final pass criteria are unchanged. This implementation does not make a failing or incomplete native LSA record pass.

Validation command:

```powershell
python -B -X utf8 -m unittest diagnostics.com_execution_equivalence.test_command_clock diagnostics.com_execution_equivalence.test_verify_pair diagnostics.test_native_signal_record
```

Result: 60 PASS in 7.351 seconds. New checks include actual generated config and adapter CSV rows against 17 actual `.sig` programs over 20,160 one-second SG states, with zero mismatches; SC7 own AMBER; legacy OFF suppression; multiline token parsing; malformed/duplicate/incomplete source rejection; and native mask, clearance, cycle and offset mismatch rejection. Existing source-pin, readback, pair-verifier and native-record tests remain passing.

Production diagnostic files and tests were frozen after this run so the root agent can capture sources and start the bounded native experiment.
