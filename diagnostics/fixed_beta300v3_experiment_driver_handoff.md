# Fixed β300v3 three-arm driver — prepared, unexecuted

`run_fixed_beta300v3_route_experiment.py` is a diagnostics-only orchestrator. It calls the existing canonical `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`; there is no adapter copy, simulator implementation, or controller search in the driver. The existing profile adapter still attempts its ordinary one-step prediction. Those predictions are outside the physical experiment's validity claim.

The file was initially written and read during the parent's trace without execution. The subsequently authorized small stdlib checks are recorded below. **No experiment execution, model import, COM, traffic simulation, or large asset/FZP read was performed by this task.** The native gate and runtime manifest must still pass through the driver before execution; there is no bypass switch.

## Gates and invocation

Expected assets are the completed `fixed_beta300v3_network_arms_flat_v1` folder. The parent's asset generation result is manifest SHA `1e7544ee22fa52b0eed3a8eb23696a4b8b7117bd5fcf5daf75adf704da495367`. The driver obtains its required SHA from the exact native gate supplied by the caller and checks the three INPX,42 SIG,one JPG. Hashing the JPG occurs only during a future `--execute` validation, not during authoring or plan mode.

The native consumer interface agreed with Hubble is:

```
diagnostics/flat_network_native_readback_v3/native_gate.json
schema = flat-network-native-gate/v1
native_load_readback_passed = true
source_changes = []
flat_manifest_path / flat_manifest_sha256
preflight_sha256 -> sibling preflight.json / pinned_files
arms.<arm>.network_sha256
arms.<arm>.native_readback_exact = true
arms.<arm>.loadnet_passed = true
arms.<arm>.owned_processes_gone = true
arms.<arm>.readback_csv_path / readback_csv_sha256
arms.<arm>.process_manifest_sha256 -> <arm>/process.json
native_vehicle_eligibility_verified = false
```

The last false field is the honest LoadNet-only limit and does not prevent a diagnostic traffic experiment. It is not promoted to true by the run driver. The native gate's general `run_ready=false` is likewise retained; this driver separately requires the actual writer gate.

The writer gate is the immutable `fixed_beta300v3_profile_invocation_v2/validation.json`, SHA `5130a95a36b1ccb2f0e1fc02c042979b7f0e17fa0b1d18f3cb0eae0bd295a7c3`. It must have passed,exit0,source_unchanged,fake_readback_exact and exact74/213 nonmetadata rows. The original and validated CSV bytes are independently hashed and their physical columns compared. Its recorded canonical source SHA must match the run source. In particular, a temporary return to the pre-cache signal module during a benchmark fails this gate; do not silently regenerate the gate or accept another SHA.

The caller also supplies an exact SHA of a reviewed runtime manifest with `source_sha256`. All its pinned files, the profile manifest/source/output files, native preflight files and small runner inputs are checked before execution and before/after each arm. The original run's one FZP is additionally pinned at execution time and joins those unchanged-source checks. A manifest from a different runtime is rejected. The profile is permanently pinned to config SHA `304bba9e24d936e76b9c2a1c49ae977f49aeb60e408c4f27581fc9a774812970`.

Plan-only command (the same path was exercised with subprocess/mkdir/live-gate calls forbidden in the focused tests):

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 diagnostics/run_fixed_beta300v3_route_experiment.py --name r01
```

After checks and native gate completion, the parent can add:

```text
--native-gate diagnostics/flat_network_native_readback_v3/native_gate.json
--native-gate-sha256 <exact completed native gate SHA>
--source-manifest <reviewed current runtime manifest path>
--source-manifest-sha256 <exact current runtime manifest SHA>
--execute
```

These SHA placeholders are deliberately unresolved; no ready-to-run command is being claimed. The default mode prints an unvalidated plan and launches nothing. Each batch/run directory must be new. Long batch names that exceed the conservative legacy VBS path allowance fail before launching.

The parent subsequently completed native v3: `native_gate.json` SHA `56b3f9ff9e608e680482392ceb75f2109984194d7423ab5eac00cc265af09dbd`, all three arms passed LoadNet/settings/readback/owned-process exit. The earlier v1 UTF-8 decoding and v2 missing exit-code failures remain separate evidence. The default path now names v3; its exact SHA argument remains mandatory. This native result does not complete the runtime/writer source gate while the parent's trace uses the original clock source.

## Execution and failure behavior

Order is fixed: `baseline`, `lcd10635_2000`, `upstream1135`, one license and one canonical watchdog at a time. Arguments are identical except name/network/outdir: seed13,1050s,interval150,start900,no-control warmup,state30,scale1,the original demand profile/mapping/roles/gates,stepwise,MaxAttempts1,NoGlobalKill,StartupStallSec300,StallSec300. `-Adapter` is not passed, so the canonical runner chooses the production adapter.

All inherited RW variables and Python bootstrap paths are removed from the child environment. Required profile settings are explicitly reapplied: writer=test_only,signal/ramp readback1s,write-on-change0,vehicle recording1s,vehicle routes1,queue counters/window1. NUMSIM_REPO_ROOT is the current workspace vendor directory and RW_PYTHON is the recorded executable. Environment construction is shared by all three arms. The runner supplies its ordinary config-derived SG/head transport. No user/system environment is changed by the driver.

Before each arm, a read-only process inventory rejects existing VISSIM/cscript/wscript. An exclusive driver lock prevents concurrent copies of this experiment driver. It is not a universal mutex across every launcher; the parent must still avoid starting another COM launcher during these runs. The native gate is finished before this driver begins.

The canonical watchdog owns its existing300s no-start/no-progress handling and PID+StartTime cleanup. The driver performs **no process killing**. Nonzero watchdog exit, surviving processes, source mismatch, missing terminal state, controller error/fallback, command mismatch, readback failure, or full-payload baseline mismatch stops the batch and leaves the lock and all artifacts intact. A manual interrupt also starts no subsequent arm; a canonical watchdog already in progress may still be running and its recorded PID must be reviewed by the parent. There is no retry, recursive deletion, source restoration, or deletion of an old run. The lock is removed only after this exact batch passes all arms.

## Output and measurement boundary

For `--name r01`, run names are `codex_fixed_beta300v3_r01_<arm>_s13`, under `evaluation/runs`. The batch manifest is `diagnostics/fixed_beta300v3_experiments/r01/manifest.json`, schema `fixed-beta300v3-three-arm-experiment/v1`. It has `arms` in execution order, each with `arm,name,run,command,status,completed,valid,network_sha256,validation`. The latter SHA is populated after successful run validation. A successful arm has status`passed`,completed=true,valid=true. All-success batch status is `all_three_execution_and_readback_passed`,completed=true,valid=true. These require execution/command/readback checks for every arm and the separate exact baseline trajectory gate below. They do not claim treatment equivalence, performance, or complete route eligibility.

Each run retains the canonical provenance, decisions, stdout/stderr, state/action/bottleneck CSVs, raw route envelopes, FZP/LSA and ERR. Driver validation records the eight actual command CSVs at1/150/300/450/600/750/900/1050, verifies74-row warmup and213-row frozen policy, requires exact state endpoint1050, and invokes the existing pure `strict_signal_trace` and `vsl_readback_matches` helpers. SG/ramp1s coverage is `[900,1050)` immediate and `(900,1050]` post_step, with the existing documented identical initial meter reapplication exception. Immediate1050 and later traffic are outside the comparison. VSL66 rows are checked at command application, not incorrectly described as per-second VSL observations.

The per-arm readback validator lists FZP/LSA/ERR by path and size. After the baseline passes it, the additional baseline gate streams its FZP and the original reference FZP. Treatment FZP/LSA contents are not read by the driver, and it does not infer lane/route outcomes. Spatial diagnostics may consume only completed,valid arms. They must distinguish0..900 native warmup effects from900..1050 frozen-policy effects and keep the expected-OD versus same-seed realized-OD limitation. Native route snapshots remain the canonical150s observations; they do not prove every vehicle's selected route. Detailed cohort, removal/censoring, physical passage and congestion comparisons belong to the separate observation tools.

## Required baseline trajectory equivalence before treatments

The profile manifest's `source_run` identifies the original `codex_contract_beta300_s13_1050_v3_20260910`. Its provenance must be present in the profile's exact source proof, and both runs must have seed13,SimPeriod1050,control150,state30,demand scale1,native FZP resolution1. Their network, control mapping, vehicle-input roles, demand profile, and urban gate SHA values must match. Their different controller names (`wu-link` reference and `diagnostic-signal-profile` baseline) are checked explicitly. Exactly one nonempty FZP must exist inside each run.

The driver reuses `diagnostics.audit_observed_nc_trajectory.payload(path)` unchanged. It compares the exact `$VEHICLE` header, ordered payload SHA/byte count/row count, first time and last time, with last time1050 required even if both files otherwise match. Only the pre-data run/date preamble is excluded from equality. Both whole-file hashes are saved for identity; a different preamble can legitimately make them differ. A stat guard covers the helper's payload and final whole-file hash passes, and the original whole hash must equal its execution-preflight pin.

The batch records `baseline_trajectory_reference`; the baseline arm records `baseline_trajectory_comparison` (schema `fixed-beta300v3-baseline-trajectory/v1`) with both payload/file hashes, header/count/time fields and differences. The comparison is saved **before** a mismatch raises and stops the batch. Each treatment also explicitly requires that baseline record's `valid=true`. There is no allow-difference override. The original FZP joins the source pins checked before/after every arm; this requires additional streaming hash reads at execution time. No actual FZP was read while preparing these checks.

## Bounded preparation validation

`python -B -X utf8 -m unittest diagnostics.test_fixed_beta300v3_experiment_driver -v` passed **12 tests in 3.606 seconds**. The evidence is `fixed_beta300v3_experiment_driver_validation.json` and its console log. These tests use only standard-library code and already existing small 74/213-row command CSVs, action JSONs, and the v3 900/1050 raw/provenance schemas. Real beta300 provenance is explicitly distinguished from the profile's test-only writer environment.

A fresh Python import probe originally covered seven project modules; the trajectory revision adds the existing inert payload module for eight total (driver, two readback helpers, inert preflight dependency, payload helper, timing oracle, action schema, signal plan). It rejects model/COM imports, subprocess launch, workspace data reads, and writes during those imports. The driver source is parsed/compiled in memory. Plan mode is checked with live gates, process enumeration, launching, and mkdir forbidden. All three commands differ only in name/network/output; child environment cleanup preserves the caller's environment.

Physical comparison checks every physical column: absent/truncated columns, a missing row, changed values, duplicate physical addresses, and nonfinite numeric values fail. Metadata, decimal formatting, and action-log-only columns do not change the physical comparison. Driver hardening in this revision also requires correct raw snapshot times and nonempty FZP/LSA presence.

`validate_run` is exercised against **synthetic** run files with the real frozen command vectors and 130 groups of oracle-generated 1-second rows. Missing post-step1050, altered applied commands/VSL readback, wrong provenance, incomplete routes, wrong raw time, and empty native output files are rejected. Synthetic FZP/LSA files contain a placeholder header only; tests forbid opening their contents. Passing this fixture proves validator wiring and boundary checks; it provides no evidence of simulation, trajectory content, saturated service, performance, or full route eligibility. The driver checks the route envelope's presence/complete flag and timestamp; detailed per-vehicle identity/count/eligibility analysis remains the separate observation consumer's responsibility.

The trajectory revision passed **18 tests in 3.454 seconds**, recorded separately in `fixed_beta300v3_experiment_driver_validation_v2.json/.log`; the earlier12-test evidence is preserved. Six new tests use tiny synthetic FZP files only: equal payload/different preamble passes; data/order/header changes fail; two matching1049 endpoints fail; original-file changes and mutation during the helper hash are rejected; source provenance/physical inputs are bound. A mocked external watchdog exercises the actual driver's serial state machine: a baseline mismatch saves both hashes and the lock, then exits without creating or launching either treatment. No real process is launched by that state-machine test.

**Pending:** actual `validate_gates` against the final runtime/clock plus writer pins, canonical watchdog execution of the three arms, actual command/readback validation, exact original-baseline FZP comparison, and treatment trajectory analysis. None was substituted by these unit tests.
