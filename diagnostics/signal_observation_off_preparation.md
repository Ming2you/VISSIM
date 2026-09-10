# Head-OFF, forced-stepwise NC comparison — prepared only

`signal_observation_off_overlay.json` contains only `urban.capacity.head_observation.enabled=false`. The existing min-green/min-count settings and every other effective configuration leaf stay unchanged. The flat v2 ON configuration plus this in-memory overlay passed `verify_signal_observation_pair.py`; no candidate family was generated and no simulator was launched.

Root added `[switch]$ForceStepwise` to the existing launcher and passes it as `-ForceStepwise:$ForceStepwise` to the watchdog. The launcher has one matching parameter and PowerShell AST parse errors0. Root owns that edit; this preparation changed diagnostic files only.

Use the existing Python runtime (`C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`); set `$Python` to that path in the shell before the commands below.

After root finishes the model fix, generate a new OFF family using the same base, physics, clock and ordered ON overlays, appending OFF last. With the currently reviewed ON overlay list the command is:

```powershell
& $Python -X utf8 diagnostics/prepare_area_candidate_configs.py --overlay diagnostics/control_area_contract_overlay.json --overlay diagnostics/signal_observation_off_overlay.json --output-dir diagnostics/contract_head_off_candidate_configs
```

Verify the two actual flattened outputs before launch (substitute the final ON family path):

```powershell
& $Python -X utf8 diagnostics/verify_signal_observation_pair.py --on-config diagnostics/contract_candidate_configs_v2/n7_area_beta0.json --off-config diagnostics/contract_head_off_candidate_configs/n7_area_beta0.json --output diagnostics/signal_observation_actual_pair_config_proof.json
```

This must report exactly one difference, the boolean head flag; it refuses changed quality thresholds, names, other parameters or numeric0 in place of false. The v2 path above is the actual retained ON baseline; if root generates a newer ON family, verify that too and retain its separate source identity.

Root-only launch command:

```powershell
diagnostics/run_area_beta_trial.ps1 -BetaSeconds 0 -Seed 13 -SimPeriod 1050 -Controller no-control -ForceStepwise -ConfigDirectory contract_head_off_candidate_configs -Name codex_contract_head_off_nc_s13_1050_20260910
```

The launcher preserves demand scale1, control interval150, control start900, no-control warmup, state log30, native FZP1s, native route records, queue windows, signal readback1s, VBS/mapping/network/calibration and native input profile paths. Both forced-stepwise runs call decisions at1,150,...,1050 and therefore reapply the same DSD/ramp command vector on the same schedule. Native urban signals remain native under NoControl. The watchdog derives `RW_SIGNAL_OBSERVATION=0` from the OFF config; do not set an independent environment toggle. Absence of the physical head window in OFF state is the intentional difference, while existing full vehicle/state serialization remains enabled.

After SIM_DONE and stable1050 EOF, compare with the retained ON run using the existing prefix parser:

```powershell
& $Python -X utf8 diagnostics/audit_signal_observation_smoke.py --trajectory-only --run codex_contract_head_off_nc_s13_1050_20260910 --reference codex_contract_observed_nc_s13_1050_v2_20260910 --through-sec 1050 --output diagnostics/observer_head_off_vs_v2_prefix1050.json
```

`--trajectory-only` does not require OFF head windows. It streams each prefix once, checks all one-second frames and complete EOF/later-row closure, retains ordered raw row bytes, and preserves false equality as a result. It does not start an adapter, optimizer or simulator. The original full NC reference1050 payload proof is already retained in `observer_smoke_v2_complete.json`; a second explicit comparison can replace `--reference` with `codex_area_observed_nc_s13_20260910` and use a new output filename if source re-reading is desired.

Seven focused tests pass, including the head-OFF/no-head prefix mode. Existing v2 results and their producer/source hashes are not overwritten. The old v2 ON run predates the independent phase-price repair, so software hashes may differ from the later OFF run. Record those differences and compare all actual physical command/readback vectors and native LSA events before drawing a collector-only conclusion. The head flag also selects its capacity consumer; in NoControl those model changes should have no actuator effect, but this remains an observed-command verification requirement.
