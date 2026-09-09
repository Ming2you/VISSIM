The production integration now has actual imports and fresh-process preflight support. `run_area_production_preflight.py` calls the canonical adapter script directly; it does not run proposal builders, AST replacements or an adapter copy. It writes a unique diagnostic output directory, checks all required Ω/signal/experiment metadata and zero serial reruns, pins runtime source hashes, and records child PID plus creation time. WMI access must work before it launches a child. On this host that read-only process audit requires the approved unsandboxed execution context.

Generate and check the four flattened inputs from the integrated checkout:

```powershell
$areaPython = 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $areaPython -X utf8 diagnostics/prepare_area_candidate_configs.py
foreach ($areaBeta in @(0, 60, 150, 300)) {
  & $areaPython -X utf8 scripts/verify_parameters.py "diagnostics/area_candidate_configs/n7_area_beta$areaBeta.json"
  if ($LASTEXITCODE -ne 0) { throw "Parameter verification failed: beta=$areaBeta" }
}
```

The generator deep merges n7, physical Ω projection/finite corridor support, exact freeway counts, and the explicit physical signal contract. Config names end in `_review`. Its manifest hashes actual canonical code and datasets, not unapplied patch artifacts. All four configs passed `verify_parameters`; existing calibration-override warnings remain. That legacy check does not install every new runtime hook, so it is only one part of the preflight.

Run the actual adapter with the same default mode, mapping, calibration, signal selector and offset experiment environment as VBS:

```powershell
& $areaPython -X utf8 diagnostics/run_area_production_preflight.py --time 1 --beta 0 --controller no-control --execute
& $areaPython -X utf8 diagnostics/run_area_production_preflight.py --time 900 --beta 0 --execute
& $areaPython -X utf8 diagnostics/run_area_production_preflight.py --time 1200 --beta 0 --execute
& $areaPython -X utf8 diagnostics/run_area_production_preflight.py --time 3300 --beta 300 --execute
```

Without `--execute`, the helper prints its exact command and environment. The child has `RW_OFFSET_WRITER=experiment`, config-derived `RW_MAINLINE_SG_ONLY`, the canonical NumSim root, and no inherited `RW_ADAPTER_MODE` override. Output validation requires physical signal contract=1, Ω endpoint=1, exact counts=1, requested β, offset writer=experiment, production offset writes=0, and the normalized per-signal writer table. An all-zero selected offset is allowed and its search/guard diagnostics must be inspected.

The final area follower/offset/fallback fix is integrated in commit5248255. State1 warmup passed again with exit0, source unchanged and no surviving children. Final t900/β0 main also passed with decision121.859965s, exit0,31 observed worker processes all gone, source unchanged and zero serial reruns. Its selected Nash J=ΩTTT298.579011 and TD1410.978453 satisfy the explicit coefficient formula. The fallback uses objective comparison. It searched13 nonzero offsets and retained13 because ΩJ on298.579011 improves on off300.145254; the experiment writer contains those13 actual nonzero offsets. The exact validated records are under `area_production_preflight/no-control_t1_beta0_20260909T183219584193Z` and `area_production_preflight/wu-link_t900_beta0_20260909T183226944811Z`.

The earlier t1200/β0 production decision completed with status=ok in130.650579s and zero serial reruns. It searched10 nonzero offsets but the old global-TTT keep guard kept0: on528.249365 versus off529.036236veh·h. Its monitoring parent failed before collecting the exit code, so that attempt is only historical wiring evidence. The final t900/β0 and t3300/β300 preflights supersede it. A read-only profile of the latter also checks whether the outer GNE phase commit changes the vector after the inner follower score; its result must be reported separately.

After successful final preflight and the parent-owned commit, a single β arm uses this exact launch shape. Substitute only β and a unique run name for each of0/60/150/300. Run arms sequentially on the same frozen source and seed; the first requested arm is β0.

```powershell
$areaBeta = 0
$areaName = 'codex_area_beta0_s13_20260910'
$env:RW_PYTHON = $areaPython
$env:RW_OFFSET_WRITER = 'experiment'
$env:RW_QUEUE_COUNTER = '1'
$env:RW_QUEUE_WINDOW = '1'
$env:RW_SIGNAL_READBACK_SEC = '1'
$env:RW_SIGNAL_WRITE_ON_CHANGE = '0'
$env:RW_VEHREC_RESOLUTION = '1'
Remove-Item Env:RW_ADAPTER_MODE -ErrorAction SilentlyContinue
& scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1 `
  -Name $areaName -Controller wu-link `
  -Network 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx' `
  -OutDir "evaluation/runs/$areaName" `
  -Tuning "diagnostics/area_candidate_configs/n7_area_beta$areaBeta.json" `
  -Calibration 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json' `
  -Mapping 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json' `
  -VbsConfig 'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs' `
  -UrbanInputGateMap 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv' `
  -VehicleInputRoles 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv' `
  -DemandProfile 'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv' `
  -DemandScale 1 -SimPeriod 5400 -ControlIntervalSec 150 -ControlStartSec 900 `
  -WarmupController no-control -Seed 13 -StateLogIntervalSec 30 `
  -StartupStallSec 300 -StallSec 600 -MaxAttempts 1 -NoGlobalKill `
  -AuditAnchorsSec '900,1500,1800,2100,2700,3600,4500,5400'
```

The wrapper derives strict decision fail-fast from the existing area-enabled config and native/mainline plan selection from the existing signal config. Both config and environment explicitly declare the optimizer offset experiment. No production promotion evidence is changed. The600s stall budget is above the observed131s decision and must be reassessed from final preflight; four full runs can require several hours because each arm has roughly31 actual MPC decisions.

Resource audit: the selected price/green/phase batches use `with ProcessPoolExecutor`; worker exceptions leave the context and perform shutdown before serial retry or main's strict rethrow. `controller.close()` is called only on successful main decisions. Its inherited method owns the optional leader pool; n7 uses serial leader/grid backends, so that pool is not created on this route. A generic exception-safe close would still improve other modes, but is not a prerequisite established by this n7 path. The strict handler does not suppress an area exception; the VBS/watchdog chain stops on failed output. The preflight helper additionally observes descendant cleanup and rejects any surviving owned process; it never kills unrelated Python or VISSIM processes.
