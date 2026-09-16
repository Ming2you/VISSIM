# Native fixed-profile preparation

Prepared only: no VISSIM or COM was launched. The existing `fast_nc_run.ps1` / `fast_nc_runner.vbs` now accept explicit `fixed_profile` prepared mode. The original default and `native_preserve` traffic-setting paths retain their existing behavior. Byte-for-byte copies of both already-modified sources before this task are in `../native_fixed_profile_v1/source_before/`; this task did not revert prior uncommitted work.

All four new snapshots retain the approved seed13 east080 network bytes, SHA256 `3795b346d7eafbbdf47ede0673050c12a4dcea2e40bca7abc085abf71381d65c`, saved SimRes1 and all sibling assets. No demand, route, urban signal, seed, SimRes, or driving-behavior setting is changed. None uses the frozen METANET artifacts or an optimizer/adapter. The four native runs are a causal command diagnostic, with no N_UF or GNE feasibility claim.

| Arm | VSL events | Physical meter events | Native history |
|---|---:|---:|---|
| none | 0 | 0 | preserved throughout |
| vsl | 64 class writes | 0 | preserved through t=1350 |
| rm | 0 | 151 RED/GREEN transitions | preserved through t=1350 |
| both | 64 class writes | 151 RED/GREEN transitions | preserved through t=1350 |

End time is 2250 s. Distribution-ID sequence on DSD59–62, classes10/20/30/70: 100@1350,80@1500,100@1800,120@1950. Native ID120 is preserved before1350 and restored at1950. IDs denote actual INPX distributions, not deterministic speeds; each full distribution is included in each prepared proof. The physical signs are at link2 position2652.027349m, global chain5386.554349m. The next unchanged signs63–66 are at6733.192994m; they reset native ID120. The affected interval is therefore5386.554349–6733.192994m, not the stale mapping's nominal segment boundaries.

RM treatment is only SC9107/SG1, connector10490: g8@1350,g6@1500,g4@1650,g6@1800,g8@1950,g10@2100. Every declared green change is at most2s per150s. The native state is OFF, retained literally in evidence. The user approved10 as an open-service trust anchor only; OFF/GREEN physical equivalence has not been established. The other seven meters remain native OFF. Signalhead90030900 is at connector pos272.603559m; connector length279.032130m leaves6.428571m downstream. Endpoint is link119 lane1 pos305.386468m, global chain7153.367468m. Already downstream vehicles must not be counted as stopped meter queue.

`RunContinuous` stops only at compiled state-change times and terminal. A write at t occurs after native frame t and first affects native LDP frame t+1. Meter states use absolute time modulo10, RED/GREEN only. There are no all-vehicle COM queries. All824 DSD-class/SG objects receive initial/final read-only snapshots; each command receives immediate readback. Untargeted distribution IDs and signal ownership are compared with equal canonical hashes. Native signal states are allowed to evolve under their own programs.

Native LDP declaration covers25SC/144SG (17 urban SC×8SG plus8meters), not every SG in all50 controllers. The remaining296SG are explicitly listed in `unrecorded_signal_groups` and have initial/final ownership evidence only. The verifier requires every configured LDP second through2250, checks each targeted meter's after-step state and actual green totals120,90,60,90,120,150 seconds over successive150s windows. Existing completed seed13 native LDP files passed the same configured-scope parser for all56,250 rows/324,000 samples through2250.

The original owned-PID startup300s guard remains. Fixed mode continues monitoring advancing complete native FZP timestamps every2wall-seconds after startup and records `progress.csv`;300s stagnation stops only the identified cscript/native PID+creation-time instances. Unknown or preexisting VISSIM processes are never stopped. Existing recording, exact terminal, exit-code and process-closure checks are reused. Failed validation preserves `fixed_validation.json`, its error and stdout/stderr. It marks the run incomplete.

Run from the worktree only after root approval/source lock, one arm at a time:

```powershell
& diagnostics/fast_nc_run.ps1 -Prepared diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/prepared_none -Output diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/run_none -Execute
```

Substitute vsl/rm/both for the two arm names. Omit `-Execute` for the read-only command plan. Do not reuse an existing output directory. No seed override is permitted against a prepared snapshot.

After every treatment run, root must separately verify comparability against the new none run:

```powershell
& $Python -B -X utf8 diagnostics/fast_fixed_profile_verify.py --prepared diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/prepared_vsl --run diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/run_vsl --reference diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/run_none
```

This compares every raw FZP data column/row through1350 by normalized-line SHA (volatile headers excluded), all configured native signal states through1350, and every untargeted configured signal throughout2250. `completed` alone does not certify paired comparability. Restore-free replay starts from time0 for every arm; no VISSIM checkpoint/snapshot restoration API is used. A450s model forecast and900s observed response are distinct scopes.

Validation:27 tests pass, including legacy NC preparation guards, exact source-copy pins, composition and green-duration schedules, invalid trust/address/time rejection, native before/after-step alignment, missing LDP tail rejection and full-column FZP prefix comparison. PowerShell parser passes. VBS `--check` passes and exits before COM creation; CScript settings required a read-only sandbox escalation. No native behavior has yet been validated for this newly added mode.
