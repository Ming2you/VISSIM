# SimPeriod preservation hypothesis

V2 no-control completed0–2250 and passed native actuation/recording validation. Its comparison with original east080 seed13 native9000 first differed at data row8,048,605 (t2231,vehicle11020,link1210012101); the previous8,048,604 data rows were identical. The reported positions were193.57/193.71m and speeds42.43/43.46km/h. That evidence is preserved in `../native_fixed_profile_v2/baseline_first_difference.json`; the completed v2 run is retained as a valid execution with failed full-baseline parity. The cause is not established.

The testable hypothesis is that shortening SimPeriod from the saved9001 to2251 affected late trajectories. V3 changes only the fixed-profile runtime period policy: preserve saved SimPeriod when it exceeds the requested stop; otherwise increase it to terminal+1. The simulation still stops with SimBreakAt2250. The default and native_preserve modes retain their previous period behavior. There are no demand, route, signal, DSD, network or calibration changes relative to the corresponding v2 arm. Initial/effective period values are now explicit preparation fields and independently required runtime readbacks.

Every v3 network and sibling asset is an exact new copy of the same approved source SHA256 `3795b346d7eafbbdf47ede0673050c12a4dcea2e40bca7abc085abf71381d65c`. Each arm's profile JSON, fixed event CSV and complete initial-address CSV is byte-identical to v2. Saved/effective SimPeriod is9001/9001; stop2250. V3 source-before copies include every v2 locked implementation/dependency and exact `LOCK_v2.json`. V2 logs, prepared inputs, reports and original LOCK were not edited.

Root first runs only zero-command NC, after checking no active native processes and the new LOCK:

```powershell
& diagnostics/fast_nc_run.ps1 -Prepared diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/prepared_none -Output diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/run_none -Execute
```

Then require full2250 raw FZP-row equality and all144 configured native SG states against the original long run:

```powershell
& $Python -B -X utf8 diagnostics/fast_fixed_profile_verify.py --prepared diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/prepared_none --run diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/run_none --reference diagnostics/demand_sweep/user_native_20260914/east080_v1/native9000
```

For a zero-event profile, the verifier's reference cutoff is the terminal2250; `paired_comparison_end_sec` records it. Thus matching only the initial1350 seconds cannot pass this hypothesis gate. No treatments start before root accepts the baseline comparison. If it still differs, preserve the failed comparison and investigate further without declaring SimPeriod the cause. For eventual treatment runs the paired cutoff remains1350 and the reference becomes v3/run_none; actuation completion and comparability remain separate.

Validation includes legacy NC tests, long saved period9001 retained, shorter saved period1800 increased only to2251, incorrect effective-period readback rejected, and a late FZP difference at2250 rejected even when1350 is identical. VBS --check compiles without COM; the existing native run is not repeated by the preparing agent. The prior v2 preparation report documents the unchanged commands, geometry, native LDP coverage and OFF service-anchor distinction.
