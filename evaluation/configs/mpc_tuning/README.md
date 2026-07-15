# Vissim MPC tuning profiles

These JSON files are loaded by `evaluation/controllers/vissim_stackelberg_adapter.py`
through `--tuning-json`. They are intentionally small one-axis perturbations around
the calibrated Vissim profile in
`evaluation/calibration/vissim_calibrated_overrides_vector_20260626.json`.

The first sweep should compare:

- `00_calibrated_base`: calibrated baseline.
- `01_freeway_priority`: stronger density and ramp queue penalties.
- `02_urban_priority`: stronger protected-region/MFD and signal queue protection.
- `03_smooth_high`: conservative actuation.
- `04_smooth_low`: responsive actuation.
- `05_activation_early`: earlier control activation.
- `06_activation_late`: less intrusive, later activation.
- `07_boundary_queue_priority`: prices Vissim boundary queues in the leader objective.
- `08_mfd_strong`: stronger protected-accumulation penalty for MFD/hysteresis tests.

Recommended first pass: one 300 s smoke run for `00_calibrated_base`, then a 300 s
single-seed grid. If stable, repeat selected profiles at 600-900 s and multiple seeds.

Note: the Vissim adapter default keeps the original Numerical-Sim MFD objective:
`leader.mfd_penalty_mode="all_urban_halfcap"`, so storage penalties are based on
the excess over `mfd_storage_threshold_ratio * capacity` rather than direct
`N_P > N_P_crit` exceedance.
