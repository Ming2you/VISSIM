# Fixed commands for COM execution equivalence

Prepared only; no adapter/model import, prediction, COM, VISSIM, or experiment was run. These are two physical-command fixtures, with a separate head-OFF event variant for each. Both arms use the **same config file**, network, demand, seed, command values, and root-merged COM/VSL-sidecar source. In the primary comparison only two environment settings differ: old uses readback=1/write-on-change=0; new uses readback=0/write-on-change=1. RW_PERF=1 in both. This measures the SG-loop reduction within the same merged source, not a source-version comparison.

| Fixture | Controller / primary config | Command from immediate 900 through post-step 1200 |
|---|---|---|
| Signal | `diagnostic-signal-profile` / `signal_profile.json` | Recorded valid 68 greens and 17 offsets (11 nonzero); all 17 cycles are 150 s, including 3 s amber per live phase. VSL120; all eight meters GREEN10. Expected action CSV: 213 rows. |
| Ramp/VSL | `diagnostic-ramp-profile` / `ramp_profile.json` | FW_E and FW_W zone heads 0/5/10/15 fixed at 80, expanded by the existing writer. Eight explicit physical meters GREEN5 in a 10 s cycle (5G + 1A + 4R). Urban SIG remains native. Expected action CSV: 74 rows. |

Both warm up with `no-control` before 900 (expected 74-row commands: urban rows absent, VSL120, meters fully open). This physical expectation must be checked in actual outputs, not inferred from the mode name. At 1200 the primary stepwise path also makes a final decision; compare the traffic ending at **post-step 1200**, before that command can affect another simulation step. VBS sets native SimPeriod to the requested endpoint plus one but stops its loop at the requested 1200. There are two complete selected urban cycles and 30 meter cycles after 900. A 1050 endpoint would cover only one selected urban cycle.

The config parent is the existing validated physical signal diagnostic, not the r02 optimizer config. Its Omega objective, physical model signal contract, and shared local pool remain OFF. This keeps the existing forced-offset `test_only` path. These fixtures do not claim r02 model/prediction fidelity or GNE equivalence. The adapter still calls its ordinary one-step prediction; neither diagnostic performs an MPC search, and profile-specific guard bypasses prevent that prediction from selecting a different physical command. The new primary configs enable only the existing head observer (measured=true, min_green_sec=30, min_crossings=5), matching r02's observation thresholds. Its collected floors may change diagnostic model metadata; they must not change these fixed physical commands.

Demand is the **unchanged r02 profile** `diagnostics/selected_control_demand/codex_selected_fw070_u040_beta0_r02/profile.csv`, with DemandScale=1. Its 34 inputs x 6 intervals reproduce selected FW70/urban40 within 1e-10 veh/h (recorded maximum error 4.547473508864641e-13). The two freeway raw-INPX multipliers are 0.58331 (= 0.8333 x 0.7), not 0.7. All other input multipliers are 0.4. Do not reapply .7/.4 or use the old full-demand profile. The native network is the same flat `baseline.inpx`; no route/geometry/SIG change is part of either arm. The diagnostic parent has no native_internal_inputs/shared_approach declarations: the r02 derived declarations are not silently replaced or activated. A later closed-loop r02 comparison must retain both r02 declarations and their profile SHA.

## Direct canonical watchdog invocation

Run each arm separately, only after the active r02 run and all prior owned native processes have ended. Root must first install and freeze the merged implementation that supports readback=0 as disabling the post-step SG sweep; the pre-optimization function instead clamps zero to one. Use the **same merged source** for both arms. Use a fresh **Windows PowerShell 5.1** process, from the `control-full-review` worktree root. The block is ASCII-only; JSON reads explicitly use UTF8. It calls the existing watchdog directly, with no Adapter override, CSV dispatcher, or new launcher. Select one fixture and arm label below; do not execute the block merely to inspect the config.

```powershell
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path '.').Path
$bundle = Join-Path $repo 'diagnostics/com_execution_equivalence'
$fixture = 'signal'   # signal or ramp
$arm = 'old'          # old or new settings, with the SAME frozen merged source
$mode = 'head'        # head for SG-loop comparison; event for the separate mode comparison
if ($fixture -notin @('signal','ramp') -or $arm -notin @('old','new') -or $mode -notin @('head','event')) { throw 'Explicit fixture/arm/mode required' }
if (@(Get-Process -Name VISSIM200,VISSIM200CL,cscript -ErrorAction SilentlyContinue).Count) { throw 'Another native/script process is present; do not run concurrently' }
$manifest = Get-Content -LiteralPath (Join-Path $bundle 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($pin in $manifest.input_pins) {
  $file = Join-Path $repo $pin.path
  if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $pin.sha256) { throw ('Input pin mismatch: ' + $pin.path) }
}
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
foreach ($key in @('PYTHONPATH','PYTHONSTARTUP','PYTHONPROFILEIMPORTTIME','NUMSIM_REPO_ROOT')) {
  [Environment]::SetEnvironmentVariable($key, $null, 'Process')
}
$env:PSModulePath = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/Modules'
$env:PYTHONUTF8 = '1'; $env:PYTHONHASHSEED = '0'
$env:RW_PYTHON = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:NUMSIM_REPO_ROOT = Join-Path $repo 'vendor/NumSim-mine'
$env:RW_OFFSET_WRITER = 'test_only'
$env:RW_NATIVE_EVAL = '1'; $env:RW_VEHREC_RESOLUTION = '1'; $env:RW_VEHICLE_ROUTES = '1'
$env:RW_QUEUE_COUNTER = '1'; $env:RW_QUEUE_WINDOW = '1'; $env:RW_STATE_LOG = 'full'
$env:RW_PERF = '1'
$oldSgLoop = ($mode -eq 'head' -and $arm -eq 'old')
$env:RW_SIGNAL_READBACK_SEC = if ($oldSgLoop) { '1' } else { '0' }
$env:RW_SIGNAL_WRITE_ON_CHANGE = if ($oldSgLoop) { '0' } else { '1' }
$suffix = if ($mode -eq 'event') { '_event' } else { '' }
$name = 'codex_com_' + $fixture + '_' + $mode + '_' + $arm + '_s13_1200_r01'
$out = Join-Path $repo ('evaluation/runs/' + $name)
if (Test-Path -LiteralPath $out) { throw 'Require a new output; preserve every previous arm' }
$a = @{
  Name=$name; OutDir=$out; Controller=('diagnostic-' + $fixture + '-profile');
  Tuning=(Join-Path $bundle ($fixture + '_profile' + $suffix + '.json'));
  Network=$manifest.runner_inputs.Network;
  DemandProfile=$manifest.runner_inputs.DemandProfile; DemandScale=1;
  Calibration=$manifest.runner_inputs.Calibration; Mapping=$manifest.runner_inputs.Mapping;
  VbsConfig=$manifest.runner_inputs.VbsConfig; VehicleInputRoles=$manifest.runner_inputs.VehicleInputRoles;
  UrbanInputGateMap=$manifest.runner_inputs.UrbanInputGateMap;
  SimPeriod=1200; ControlIntervalSec=150; ControlStartSec=900; WarmupController='no-control';
  Seed=13; StateLogIntervalSec=30; StartupStallSec=300; StallSec=300;
  MaxAttempts=1; NoGlobalKill=$true;
  ForceStepwise=($mode -eq 'head' -or $arm -eq 'old')
}
& (Join-Path $repo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1') @a
```

The watchdog resolves relative runner paths against its own canonical workspace. It captures effective config/source/network/SIG/environment provenance and transports the head flag from the config, overriding inherited observer environment. No trace bootstrap, RW_ADAPTER_MODE, alternative NUMSIM tree, or inherited RW setting is retained. Input pins include the inherited config and frozen green/plan files because the top-level tuning hash alone does not pin an extends chain. Recheck those pins after each completed arm. Root must capture the final merged source before the pair and require identical runtime sources in both watchdog provenances. Apart from run identifiers/output paths, only the two primary SG environment settings above may differ. Do not apply a production patch from these commands.

## Head observer versus event mode

Primary `head` arms both select `STEPWISE_PHYSICAL_HEAD_OBSERVATION`, with the same 1 s head observations, explicit ForceStepwise, state full/30 s, RW_PERF=1, and merged source. The diagnostic is rerun at 1,150,...,1200; require every action at/after 900 to retain the same physical rows. Old readback=1/write-on-change=0 exercises the prior SG-loop settings; new readback=0/write-on-change=1 removes the post-step SG sweep and redundant state writes. The head observer must still retain its required 1 s inputs. Do not label the new trace as full 1 Hz SG readback. Both arms also share the logger environment caches and the VSL sidecar's removal of the two summary reads, so the measured reduction is conservative: it isolates the remaining SG-loop saving and does not measure the old VSL-summary cost.

For the optional `event` comparison, use `*_profile_event.json` for **both** arms and freeze the same fast merged source and environment (readback=0/write-on-change=1/RW_PERF=1) for both. These overlays change only head_observation.enabled to false. Old is forced stepwise; new omits ForceStepwise and uses the existing `UseSingleDecisionEventMode` with decisions only at 1/900, and RunContinuous stops at signal/meter transitions, 30 s logs, and terminal 1200. This is a separate execution-mode experiment, not an old-head-ON/new-head-OFF comparison. Head-OFF resumes the parent's legacy measured-capacity path; its model diagnostics need not match head-ON. Physical commands must still match. No head samples may be skipped in a claimed head-ON optimization.

Setting RW_SIGNAL_READBACK_SEC=1 does **not** add event stopping points. The proposed fast/event settings instead disable that sweep. Check every readback that the merged writer actually records against the same command clock; missing post-step rows are not evidence of 1 Hz validation. Native LSA has not recorded the COM-controlled SG transitions in the inspected runs, so it cannot fill this gap. Require complete ordered 1 s FZP payload equality and unchanged required head-observation inputs in the primary comparison, with the old arm's 1 Hz post-step checks as the reference. If a separate full 1 Hz event COM comparison is needed, set readback=1 and StateLogIntervalSec=1 for **both** event-mode arms; that wakes the event loop each second and no longer measures transition-skipping savings.

## Completion and equivalence gates

`checks_signal.json` and `checks_ramp.json` adapt the unchanged `diagnostics/selected_control_completion.py` consumer for the two primary fixtures. Each preserves all 21 bundle input pins: 20 source entries plus the selected absolute tuning path in generated_sha256. The actual generated-config sibling `_sgplan.vbs` is pinned as well: its 136 controlled SG addresses include 14 RED-only groups absent from the 122 CSV SG-window rows. They also supply the exact network/profile hashes. Each checks file is identical for the old/new pair. This is a **fixture-schema adaptation**, not a new full selected-demand preparation proof; the existing r02 checks/comparison/profile are pinned. The event overlays require separately bound completion checks before any event run; using a primary checks file for them must fail the tuning SHA gate.

Root's inline orchestration runs the canonical watchdog in an external process using the argument block above and records its actual exit plus the exact owned native PID, creation time, final alive flag, and ownership ambiguity in `wrapper_exit_observation.json`. No launcher copy is supplied. Do not manufacture that observation from a guessed exit code or a missing window. Once those actual records exist, root can call the existing completion CLI directly:

```powershell
& $env:RW_PYTHON -B -X utf8 'diagnostics/selected_control_completion.py' --run $out --name $name --terminal 1200 --observation (Join-Path $out 'wrapper_exit_observation.json') --checks (Join-Path $bundle ('checks_' + $fixture + '.json'))
if ($LASTEXITCODE -ne 0) { throw 'Actual completion receipt failed; preserve the run' }
```

That CLI produces the actual `completion_receipt.json` consumed by the equivalence verifier. It checks canonical terminal/failure counters, native ERR receipts, provenance, exact process-exit observation, and nonempty native outputs. No completion receipt was synthesized during preparation. FZP payload/command/head-window equivalence remains a separate subsequent gate.

Fail and preserve the output on nonzero watchdog/decision status, missing SIM_DONE, terminal other than 1200, lingering owned native process, source/input mismatch, command/readback mismatch, incomplete FZP, or unequal ordered FZP payload. No retries or allow-difference option is proposed. Check errors/ERR receipts, since exit0 alone is insufficient. StartupStallSec=300 applies before traffic progress. StallSec=300 is a separate diagnostic no-progress limit: if a valid prediction calculation exceeds it, report a computation/watchdog failure rather than a native-startup failure or equivalence result. Compare warmup 0..900 and controlled 900..1200 separately as well as the full payload. Existing `diagnostics.audit_observed_nc_trajectory.payload` can stream/hash the ordered FZP payload after execution; no FZP was read during this preparation.

Use existing command parsers/clock checks for actual 74/213 CSV rows, header, order, and every physical column. Report CSV metadata and JSON timing/run-path/provenance separately; they are not physical command identity. Check pre/post-step boundary convention, all eight meter schedules, SG amber transitions, SC5 red-only rows, and all 66 VSL rows. Expected signal fixture physical rows can be compared with the existing baseline CSV pinned in the manifest (current file bytes recorded; this is not a new writer invocation); the ramp fixture's 74-row writer output has not yet been produced and its runtime check remains pending. Unchanged physical commands do not assert identical model metadata or forecast quality. After these gates pass, repeat the same-source/config/environment discipline for the actual head-ON wu-link closed-loop run, comparing each action and observation window as well as traffic; fixed-command PASS alone does not establish closed-loop equivalence.
