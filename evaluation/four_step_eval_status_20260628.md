# Four-step controller evaluation status - 2026-06-28

## Scope

Requested four follow-up items:

1. Add startup-progress watchdog to the no-control/controller comparison runner.
2. Compare no-control, Wu, PFO, and MPC/Stackelberg.
3. Expand top MPC tuning candidates to longer runs.
4. Re-check signal service curves or prepare online prediction calibration.

## 1. Watchdog status

Implemented for `scripts/run_vissim_controller_stress_sweep.py`.

Behavior:

- If no `RUN_SINGLE_STEP`, controller decision, or output-file progress appears within `--startup-timeout-sec`, the case is marked `startup_freeze_no_run_single_step`.
- If progress appears at least once, the runner keeps the case alive until the larger `--timeout-sec`.
- `--reset-vissim-on-startup-timeout` kills stale `VISSIM200.exe` after startup freeze.
- `--resume-existing-ok` skips cases already completed with return code `0`.
- Analyzer now reads `batch_manifest_partial.csv` when final manifests are absent and excludes failed/empty cases from summaries.

## 2. Controller comparison status

New VISSIM COM runs were blocked by the current tool approval/usage limit, so no fresh no-control/Wu/PFO/Stackelberg sweep was executed in this pass.

Existing usable comparison artifacts were re-analyzed:

- `evaluation/runs/controller_stress_sweep_1200s_20260628/stress_summary.md`
- `evaluation/runs/controller_pfo_h3_i3_sym_high_600s_20260628/stress_summary.md`

Key existing 1200 s result, warmup 120 s:

| scenario group | controller | mean total % vs no-control | mean stopped % vs no-control | note |
| --- | --- | ---: | ---: | --- |
| ramp metering | PFO | +0.707% | +0.986% | Worse than no-control on ramp-biased cases. |
| ramp metering | Wu | 0.000% | 0.000% | Produced no effective action movement. |
| VSL | PFO | -1.120% | -3.981% | Small improvement on freeway-heavy cases. |
| VSL | Wu | 0.000% | 0.000% | Produced no effective action movement. |
| signal split | PFO | -0.341% | -1.369% | Small improvement on urban-heavy cases. |
| signal split | Wu | 0.000% | 0.000% | Produced no effective action movement. |
| symmetric high | PFO | -1.536% | -1.130% | Small improvement. |
| symmetric high | Wu | 0.000% | 0.000% | Produced no effective action movement. |

Interpretation: existing PFO action mostly changes signal split/offset. VSL and ramp-meter action movement remains effectively zero in these stress artifacts. Wu is functioning technically but is behaviorally equivalent to no-control under the current tuning/activation.

Fresh apples-to-apples comparison command to run when VISSIM execution is available again:

```powershell
python scripts\run_vissim_controller_stress_sweep.py --out-dir evaluation\runs\controller_compare_physical_300s_20260628 --controllers no-control,wu,pfo,stackelberg --scenarios sym_high,ramp_d_bias,urban_d_heavy --sim-period-sec 300 --control-interval-sec 60 --seed 13 --timeout-sec 900 --startup-timeout-sec 60 --reset-vissim-on-startup-timeout --resume-existing-ok --calibration evaluation\calibration\vissim_network_calibration_v2_20260628.json --tuning evaluation\configs\mpc_tuning\04_smooth_low.json
```

Then:

```powershell
python scripts\analyze_vissim_controller_stress_sweep.py --out-dir evaluation\runs\controller_compare_physical_300s_20260628 --warmup-sec 60
```

## 3. Longer MPC tuning status

Existing physical 300 s tuning was re-analyzed:

- `evaluation/runs/mpc_tuning_physical_300s_20260628/tuning_summary.md`

Physical 300 s, seed 13:

| demand | best/near-best candidate | result |
| --- | --- | --- |
| `urban_d_heavy` | `04_smooth_low` / `08_mfd_strong` | Lowest stopped veh-h among tested candidates, but total veh-h slightly above base. |
| `d_ramp_bias` | `07_boundary_queue_priority` | Best total veh-h; `08_mfd_strong` best stopped veh-h. |
| `sym` | `07_boundary_queue_priority` | Best balanced total/stopped/speed. |

Existing older 600 s selected tuning was re-analyzed:

- `evaluation/runs/mpc_tuning_selected_600s_20260626/tuning_summary.md`

Because that 600 s artifact predates the physical v2 calibration, it is useful only as a sanity check, not final evidence.

Recommended physical-v2 long-run command when VISSIM execution is available again:

```powershell
python scripts\run_vissim_mpc_tuning_batch.py --profile grid-smoke --out-dir evaluation\runs\mpc_tuning_physical_top_600s_20260628 --tunings 04_smooth_low,07_boundary_queue_priority,08_mfd_strong --demand-profiles sym,d_ramp_bias,urban_d_heavy --sim-period-sec 600 --urban-volume-vph 2600 --freeway-volume-vph 3400 --control-interval-sec 60 --seeds 13 --max-workers 1 --case-timeout-sec 1500 --startup-timeout-sec 60 --reset-vissim-on-startup-timeout --resume-existing-ok --calibration-json evaluation\calibration\vissim_network_calibration_v2_20260628.json
```

Then promote only the best 1-2 candidates to 1200 s.

## 4. Signal service / online calibration status

Signal service curve remains diagnostic-only:

- `evaluation/calibration/vissim_signal_service_curve_fit_20260628.md`
- Policy: keep scalar `q_sat = 1800 veh/h/approach`, `lost_time = 6.0 s`
- Reason: valid per-approach regression count is zero; approaches are not saturated/identified enough.

Implemented Bayesian prediction-audit calibration patch generator:

- `scripts/update_prediction_audit_calibration.py`
- Output:
  - `evaluation/calibration/prediction_audit_bayes_update_20260628.json`
  - `evaluation/calibration/prediction_audit_bayes_update_20260628.md`

Existing 531 decision files produced:

| target | prior scale | posterior scale | median observed/predicted ratio |
| --- | ---: | ---: | ---: |
| `freeway_total_veh` | 0.6507 | 0.7234 | 0.6753 |
| `urban_queue_plus_link_occupancy_total_veh` | 1.0126 | 0.9210 | 0.9324 |

The patch is recorded in `evaluation/calibration/vissim_network_calibration_v2_20260628.json` as `candidate_not_promoted`. It is not applied to active controller dynamics until held-out validation shows lower one-step prediction error.

## Validation stance

Overall assessment: share with caveats.

The runner and analyzers are ready. Existing artifacts support the conclusion that current PFO gives small benefits in VSL/signal/symmetric cases but not ramp-biased cases, while Wu is currently inactive/equivalent to no-control. Fresh Stackelberg-vs-no-control comparison and physical-v2 600/1200 s expansion still require a new VISSIM COM run.
