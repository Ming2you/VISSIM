# Observation v2 storage-split report — 2026-06-28

## What changed

The Vissim local observation adapter now separates local link counts into:

- stopline/movement queue,
- urban link storage occupancy,
- off-ramp storage occupancy.

Previous behavior assigned nearly all local link counts to `urban_movement_queue`, leaving observed `urban_link_occupancy_total_veh = 0`. That made prediction-error diagnostics misleading and prevented off-ramp storage pressure from appearing in freeway/VSL logic.

## Implemented split

Current provisional split:

| link class | movement queue | storage occupancy |
| --- | ---: | ---: |
| boundary links | 100% | 0% |
| internal urban links | 65% | 35% |
| off-ramp links | 50% | 50% |

The split is intentionally provisional. It is an observation fix, not final calibration.

## Files changed

- `evaluation/controllers/vissim_stackelberg_adapter.py`

New observation mode:

- `detector_local_v2_storage_split`

New metadata emitted:

- `local_observation_total_storage_occupancy`
- `local_observation_offramp_storage_occupancy`
- `local_observation_internal_storage_fraction`
- `local_observation_offramp_storage_fraction`

## Adapter checks

### Single-state observation check

Input:

- `evaluation/runs/diagnostic_vsl_rm_300s_20260628/diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s/decisions/state_000060.json`

Output:

- `evaluation/runs/observation_v2_adapter_check/action_000060.json`

Result:

| metric | value |
| --- | ---: |
| movement queue | 223.55 veh |
| total storage occupancy | 13.45 veh |
| off-ramp storage occupancy | 4.00 veh |
| observation mode | `detector_local_v2_storage_split` |

### Prediction pair check

Output:

- `evaluation/runs/observation_v2_prediction_pair/action_000001.json`
- `evaluation/runs/observation_v2_prediction_pair/action_000060.json`

Important result:

| metric | predicted | observed | error |
| --- | ---: | ---: | ---: |
| urban movement queue + link occupancy | 254.95 | 237.00 | -17.95 |
| urban movement queue only | 172.83 | 223.55 | +50.72 |
| urban link occupancy only | 82.12 | 13.45 | -68.67 |

Interpretation:

The queue/storage decomposition is still approximate, but combined urban mass is now a usable diagnostic. The remaining large total error is mostly freeway-side propagation, not urban total observation.

### Spillback observability check

Input:

- `evaluation/runs/diagnostic_vsl_rm_300s_20260628/diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s/decisions/state_000300.json`

Output:

- `evaluation/runs/observation_v2_pfo_spillback_check/action_000300.json`

Result:

| metric | value |
| --- | ---: |
| local storage occupancy | 205.40 veh |
| off-ramp storage occupancy | 60.50 veh |
| response off-ramp inflow | 9.23 veh |
| response density excess | 15.37 veh |
| response spillback violation | 0.00 veh |
| response spillback penalty | 0.00 |

Off-ramp storage pressure is now nonzero in agent diagnostics:

- `OR_D_E`: ~0.108
- `OR_F_E`: ~0.144
- `OR_F_W`: ~0.144
- `OR_D_W`: ~0.108

Interpretation:

Observation issue #3 is partially fixed: storage pressure is now observable. Full spillback penalties are still zero because the current combined off-ramp capacity is high (`960 veh` in the checked agents). The next calibration step should revisit off-ramp/ramp storage capacity and freeway propagation, not the basic actuator path.

## Next step

Proceed to propagation calibration:

1. Fit freeway one-step retention/exit bias.
2. Revisit off-ramp combined capacity used by `assess_offramp_spillback`.
3. Then rerun PFO `h3/i3` and VSL/RM sensitivity.

