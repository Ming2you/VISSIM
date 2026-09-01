# Vissim-MPC Calibration Progress Report

Date: 2026-06-26

## Outcome

Started the Vissim plant calibration workflow for the MPC evaluation environment.

Implemented:

- Single-run Vissim calibration probe:
  - `scripts/run_vissim_calibration_probe.vbs`
- Parallel batch launcher:
  - `scripts/run_vissim_calibration_batch.py`
- Batch fitter:
  - `scripts/fit_vissim_calibration.py`
- Preliminary fit output:
  - `evaluation/calibration/vissim_calibration_fit_smoke.json`
- Preliminary override candidate, not active:
  - `evaluation/calibration/vissim_calibrated_overrides_smoke.json`

The staged Vissim network used for calibration probes:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx`

## Parallel execution note

Parallel execution is useful for calibration, but Vissim COM startup is fragile.

Observed:

- `max_workers=2` completed 8 of 9 smoke cases.
- One case froze at/after `STAGE=COM_CREATED`.
- The frozen `cscript` / `VISSIM200` process was cleaned up.
- The missing case was rerun successfully as a single worker.

Mitigation added:

- `scripts/run_vissim_calibration_batch.py` now supports `--startup-stagger-sec`.

Recommended next setting:

```powershell
python scripts\run_vissim_calibration_batch.py --profile fd --max-workers 2 --startup-stagger-sec 30 --out-dir evaluation\runs\calibration_fd
```

Use `max_workers=3` only after a short staggered 2-worker test is stable. More Vissim instances can be slower overall if one GUI COM instance hangs.

## Runs completed

Smoke/profile runs:

- FD smoke:
  - `fd_fw800_seed13`
  - `fd_fw1400_seed13`
  - `fd_fw2000_seed13`
- FD high-demand supplements:
  - `fd_fw2800_seed13`
  - `fd_fw3400_seed13`
- Ramp green sweep smoke:
  - `ramp_g1_seed13`
  - `ramp_g2_seed13`
  - `ramp_g4_seed13`
  - `ramp_g6_seed13`
  - `ramp_g8_seed13`
  - `ramp_g10_seed13`
- Ramp high-demand checks:
  - `ramp_high_g2_seed13`
  - `ramp_high_g10_seed13`

All completed result folders are under:

- `evaluation/runs/calibration_batch_smoke/`

## C1. Freeway FD preliminary fit

Source:

- `evaluation/calibration/vissim_calibration_fit_smoke.json`

Fitted from short no-adaptive-control freeway demand probes after 60 s warm-up.

Preliminary observed values:

| Quantity | Preliminary value |
|---|---:|
| free-speed p85 | 125.17 km/h |
| max flow proxy | 4491.689 veh/h |
| density at max flow proxy | 20.926 veh/km/lane |
| max observed density | 38.15 veh/km/lane |

Demand progression:

| Freeway demand | Median density | Median speed | Max flow proxy |
|---:|---:|---:|---:|
| 800 veh/h | 1.993 veh/km/lane | 117.952 km/h | 1271.656 veh/h |
| 1400 veh/h | 3.986 veh/km/lane | 118.667 km/h | 2564.979 veh/h |
| 2000 veh/h | 5.741 veh/km/lane | 117.216 km/h | 3615.580 veh/h |
| 2800 veh/h | 8.097 veh/km/lane | 113.006 km/h | 4278.180 veh/h |
| 3400 veh/h | 9.716 veh/km/lane | 110.951 km/h | 4491.689 veh/h |

Interpretation:

- `v_free` in the Vissim plant is clearly higher than the Numerical-Sim default 100 km/h.
- A safe next smoke override candidate is `v_free=120`.
- The observed capacity proxy is around 4,400-4,500 veh/h per two-lane direction.
- `rho_crit` is provisionally around 21 veh/km/lane from the max-flow proxy.
- `rho_max` is not calibrated yet. The max observed density of 38.15 is not a jam-density observation.

Do not finalize FD parameters until a longer high-demand / breakdown run confirms the congested branch.

## C2. Ramp metering preliminary fit

Ramp metering was implemented as runtime COM signal control:

- SC 6: D ramp meter
- SC 7: F ramp meter
- 10 s cycle
- green duration varied by case
- 1 s amber
- remaining cycle red

Preliminary release-rate observations:

| Site | Green | Release-rate estimate |
|---|---:|---:|
| D | 1 s | 246.316 veh/h |
| D | 2 s | 331.579 veh/h |
| D | 4 s | 360.000 veh/h |
| D | 6 s | 360.000 veh/h |
| D | 8 s | 378.947 veh/h |
| D | 10 s | 506.250 veh/h |
| F | 1 s | 37.895 veh/h |
| F | 2 s | 28.421 veh/h |
| F | 4 s | 37.895 veh/h |
| F | 6 s | 18.947 veh/h |
| F | 8 s | 0.000 veh/h |
| F | 10 s | 56.250 veh/h |

Interpretation:

- D ramp can be calibrated, but the short smoke runs still appear partly underfed except in the high-demand checks.
- F ramp is not ready for release-rate calibration. Even under high urban demand and always-green metering, F passage counts remain very low.
- F likely needs one of:
  - route split/demand adjustment toward F on-ramp,
  - signal-head position review,
  - ramp link/connector movement verification,
  - movement-specific meter split instead of aggregate F meter.

The current controller adapter should keep the simple rate-to-green mapping until D/F ramp actuation is revalidated.

## C3. Signal saturation flow / lost time

Status: not yet fitted.

Reason:

- The current probe logs fixed signal states and global vehicle state, but not enough per-approach stopline discharge counts to fit saturation flow robustly.

Next required runner extension:

- Add approach stopline crossing counts for controlled approaches.
- Run high approach-demand fixed signal cases.
- Estimate:
  - `network.movement_capacity_veh_h`
  - `network.lost_time`
  - effective green discharge curve.

## C4. Urban MFD / `N_P_crit_veh`

Status: not yet fitted.

Reason:

- MFD needs protected urban accumulation and production.
- Current logs include urban accumulation proxy but not robust urban production.

Next required runner extension:

- Log protected urban accumulation.
- Log boundary/internal urban output crossing counts.
- Run urban-demand sweep.
- Fit production peak and update `leader.N_P_crit_veh`.

## C5. MPC weight / smoothness / activation tuning

Status: intentionally pending.

Do not tune MPC weights until:

1. FD/capacity is stable.
2. Ramp release curves are valid for D and F.
3. Signal saturation flow is fitted.
4. Urban MFD setpoint is fitted.

Otherwise, the controller would be tuned to compensate for plant/model mismatch rather than actual control behavior.

## Recommended next action

1. Fix or validate F ramp metering actuation/arrival.
2. Run longer FD sweep with staggered parallel workers:

   ```powershell
   python scripts\run_vissim_calibration_batch.py --profile fd --max-workers 2 --startup-stagger-sec 30 --out-dir evaluation\runs\calibration_fd
   ```

3. Extend the probe runner for signal stopline discharge and urban production counts.
4. Run signal saturation and urban MFD sweeps.
5. Only then apply numeric overrides to the active MPC adapter/config.
