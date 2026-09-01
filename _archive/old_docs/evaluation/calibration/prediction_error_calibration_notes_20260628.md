# Prediction error calibration notes — 2026-06-28

## Status

The VSL + ramp-metering actuator path works when forced, but the PFO optimizer still does not naturally select restrictive VSL/ramp-metering actions.

Evidence:

- Forced `diagnostic-vsl-rm` emitted VSL `80 km/h` and D/F ramp-meter green `4 sec` simultaneously.
- Vissim run completed successfully and `action.csv` readback stored the combined actuation.
- PFO `h3/i3` and sensitivity tuning still selected VSL `120 km/h` and near-max ramp release.

## Runs inspected

- `evaluation/runs/controller_pfo_h3_i3_sym_high_600s_20260628/pfo_sym_high_u2600_fw3400_seed13_600s`
- `evaluation/runs/controller_pfo_h3_i3_fw_eb_600s_20260628/pfo_fw_eb_heavy_u1800_fw3400_seed13_600s`
- `evaluation/runs/controller_pfo_h3_i3_ramp_d_300s_20260628/pfo_ramp_d_bias_u2200_fw3000_seed13_300s`
- `evaluation/runs/diagnostic_vsl_rm_300s_20260628/diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s`

Detailed component table:

- `evaluation/runs/prediction_error_components_20260628.md`
- `evaluation/runs/prediction_error_components_20260628.csv`

## Main diagnostic result

Prediction error is large, but the dominant issue is not simply "urban demand too high" or "signal capacity too high."

### 1. Urban queue/storage decomposition is inconsistent

The current local observation path maps Vissim link counts mostly into `urban_movement_queue`, while observed `urban_link_occupancy_total_veh` remains zero. The model rollout, however, moves vehicles into `urban_link_storage`.

That makes component errors look huge:

- observed `urban_link_occupancy_total_veh`: `0`
- predicted `urban_link_occupancy_total_veh`: roughly `167–287 veh`
- observed `urban_movement_queue_total_veh`: high
- predicted `urban_movement_queue_total_veh`: lower

But if movement queue and link occupancy are combined, urban mass is much better:

| run type | observed / predicted urban queue+storage |
| --- | ---: |
| diagnostic VSL+RM | `1.04` |
| PFO freeway-heavy | `1.03` |
| PFO ramp-D-bias | `1.04` |
| PFO symmetric-high | `0.94` |
| mean | `1.01` |

Interpretation: urban total accumulation is not the first calibration target; queue-vs-storage state decomposition/audit needs to be fixed.

### 2. Freeway one-step prediction is biased high

Across the inspected runs, one-step prediction consistently over-predicts freeway vehicles:

| run type | observed / predicted freeway total |
| --- | ---: |
| diagnostic VSL+RM | `0.66` |
| PFO freeway-heavy | `0.64` |
| PFO ramp-D-bias | `0.63` |
| PFO symmetric-high | `0.68` |
| mean | `0.65` |

Interpretation: the Vissim-to-METANET freeway calibration is still off. The model leaves too many vehicles on freeway/ramp state after one control interval.

### 3. Spillback/capacity-drop triggers are not active enough

PFO diagnostics show:

- `distributed_response_total_spillback_violation_veh = 0`
- `distributed_response_spillback_penalty = 0`
- off-ramp storage pressure is mostly zero
- capacity-drop lane-loss diagnostics are zero

Even with stronger density/spillback weights and `capacity_drop_anticipation=true`, PFO still chose VSL `120 km/h` and near-max ramp release in a single-state sensitivity check.

Interpretation: the controller does not see future spillback/capacity-drop benefit from VSL/RM under the current state abstraction.

## Recommended calibration before next controller step

1. Add a storage-aware local observation split:
   - keep movement queue for stopline pressure,
   - estimate internal-link storage occupancy separately,
   - avoid double-counting by adding a calibrated queue/storage split ratio per Vissim link group.

2. Refit freeway one-step propagation:
   - use observed `state_t -> state_t+60` transitions,
   - fit freeway segment retention / exit / ramp-release correction,
   - target the current bias where observed freeway total is about `0.65 × predicted`.

3. Revalidate spillback observability:
   - ramp queues and off-ramp storage must become nonzero in the model state before VSL/RM has a rational objective signal.

4. Only after these are stable, rerun PFO `h3/i3` and then longer `h5/i3`.

