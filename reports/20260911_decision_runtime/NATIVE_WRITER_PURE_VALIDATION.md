# Native clock writer: source and actual WSH validation

2026-09-11. The optional native clock writer passed 26 tests: seven new native/adapter checks and 19 existing native-OFF VBS validator, state, atomic-contract, event and mutation checks. The combined command completed in 16.899 seconds. No VISSIM process was started or accessed.

```powershell
& 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B -X utf8 -m unittest diagnostics.test_native_vbs_clock scripts.tests.test_action_csv_vbs_validators scripts.tests.test_signal_group_plan_vbs_behavior
```

Windows Script Host required normal host settings access. The initial sandbox run failed before parsing the script (`CScript Error: Loading your settings failed. (Access is denied.)`). That failed attempt is not validation evidence. The subsequent normal-host command was approved and actually executed the extracted VBS procedures.

## Validated behavior

- Actual `render_vbs()` config and actual adapter `signal_group_action_rows()` windows were consumed by procedures extracted from the current canonical VBS runner.
- All 17 source controllers matched their actual `.sig` program at 0.5-second intervals over one complete native cycle: 40,320 SG states, including the 136 owned initial states, with zero mismatches. Permanent red groups are included; unowned midblock groups are excluded.
- SC7 uses cycle 120, independent p1, and the p2+p4=114 constraint. SG4/8 own AMBER at phase 68 remains present while SG7 is GREEN. Incorrect pair sum, conflicting clearance and nonzero dead phase are rejected.
- SC16 uses cycle 150, order p3,p2,p1 and the fixed 34-second idle interval. Incorrect total green is rejected.
- The generated SG rows for all 17 controllers pass the actual VBS atomic CSV contract. Substituting the legacy SC7 cycle 190 produces `cycle_mismatch`.
- Axis CSV offset-at-cycle, an incorrect native pair sum and green below the writer minimum are rejected. Unknown/duplicate/partial native config and invalid mask tokens are rejected.
- Empty native-clock config retains the legacy SC7/SC16 derived cycles and legacy AMBER suppression. The existing native-OFF behavior suite also passes.
- Adapter activation sets SC7 cycle 120/pair budget 114, SC16 green budget 107 and native live phases. It requires the explicit physical contract and `include_source_reference` policy. The capacity sentinel and meter capacity remain unchanged, with no concurrency capacity multiplier or drive-cycle recomputation. The disabled path is a no-op and the explicit plan path is used when configured.

## Evidence and limits

`native_writer_pure_v1/` contains the actual generated harness `.vbs` files and captured return code/stdout/stderr `.json` for each new WSH check. Each record includes the runner and harness SHA256. The tested runner SHA256 is `cf16bc39fe75a32be2686228ab31afa56de82da24fd4b96bc86530b4fa01e338`.

The old fixture pins runner SHA256 `8a9cf29a13356960428693cdc21595adf8711eaac412e859c98edce7ddc51bb2`. An in-memory reversal of the disclosed new globals/functions, five cycle call replacements, parser call and two AMBER conditions did not recover that hash. No reconstructed file was promoted or treated as the original. These checks qualify the current optional behavior and current native-OFF semantics; they do not prove historical source byte equality or historical native FZP equality.

The source change is explicit: empty native config delegates cycles to the old `SignalCycleFromPhases()` and retains the old AMBER suppression; configured controllers use source-cycle validation and own-SG AMBER. Config parser validation and complete-cohort enforcement are tested. A short actual VISSIM run with native LSA verification is still required before activation can be considered physically verified.

Only test files and evidence were edited for this validation task. Production VBS and adapter code were owned by the root agent and held unchanged during the checks.
