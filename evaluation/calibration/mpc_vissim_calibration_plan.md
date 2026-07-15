# MPC Calibration Plan for the Vissim Evaluation Plant

Date: 2026-06-25

## Why this is needed now

The Vissim bridge is now functional: the runtime loop can call Numerical-Sim `StackelbergMPCController` and apply VSL, signal, and ramp-metering actions through COM.

The next step is MPC calibration. Without this step, the controller may be optimizing against a plant model that does not match the Vissim network. In practice, that means the controller can look mathematically reasonable while pushing the wrong segment, wrong bottleneck, or wrong storage constraint.

## Calibration order

Use this order. The later steps depend on the earlier ones.

1. Topology calibration
2. Freeway FD / capacity calibration
3. Ramp-metering and signal actuator calibration
4. Urban MFD / protected-accumulation setpoint calibration
5. Objective-weight and smoothness tuning
6. Closed-loop validation against hysteresis scenarios

## C0. Topology calibration

Status: applied in `evaluation/controllers/vissim_stackelberg_adapter.py`.

The staged Vissim network uses 5 freeway control segments per direction, while the Numerical-Sim default config was originally a 4-segment abstraction. The adapter now overrides the MPC topology as:

| MPC link | Vissim link | Segment index | Meaning |
|---|---:|---:|---|
| `FW_E` | 33 | 0 | EB upstream of D |
| `FW_E` | 33 | 1 | EB D weave/ramp influence |
| `FW_E` | 33 | 2 | EB mid-mainline D-F |
| `FW_E` | 33 | 3 | EB F weave/ramp influence |
| `FW_E` | 33 | 4 | EB downstream of F |
| `FW_W` | 34 | 0 | WB upstream of F |
| `FW_W` | 34 | 1 | WB F weave/ramp influence |
| `FW_W` | 34 | 2 | WB mid-mainline F-D |
| `FW_W` | 34 | 3 | WB D weave/ramp influence |
| `FW_W` | 34 | 4 | WB downstream of D |

Ramp and off-ramp segment indices:

| Object | MPC link | Segment index |
|---|---|---:|
| `R_D_E` | `FW_E` | 1 |
| `R_F_E` | `FW_E` | 3 |
| `R_F_W` | `FW_W` | 1 |
| `R_D_W` | `FW_W` | 3 |
| `OR_D_E` | `FW_E` | 1 |
| `OR_F_E` | `FW_E` | 3 |
| `OR_F_W` | `FW_W` | 1 |
| `OR_D_W` | `FW_W` | 3 |

The profile is documented in:

- `evaluation/calibration/mpc_vissim_topology_profile_v0.json`

## C1. Freeway FD / capacity calibration

Goal: fit the Numerical-Sim freeway parameters to the Vissim mainline response.

Target parameters:

| Config parameter | Meaning |
|---|---|
| `network.v_free` | free-flow speed |
| `network.rho_crit` | critical density |
| `network.rho_max` | jam / storage density |
| `network.freeway_capacity_veh_h` | mainline capacity |
| `freeway_offramp_capacity_drop.*` | off-ramp / weave capacity-drop behavior |

Recommended Vissim experiment:

- Control mode: no adaptive control, fixed signal/ramp baseline, VSL at maximum.
- Urban demand: low enough not to dominate first pass.
- Ramp demand: low, then medium.
- Freeway demand sweep: e.g. 800, 1200, 1600, 2000, 2400, 2800 veh/h per input direction.
- Duration: at least 900-1800 s per demand level after warm-up.
- Log interval: 5-15 s.

Data to log:

- segment density by link/segment,
- segment mean speed,
- segment flow or passage count,
- queue/spillback onset near D/F,
- route/demand level,
- random seed.

Initial helper:

- `scripts/analyze_vissim_fd_samples.py`

This helper can summarize `state_*.json` samples from the current Vissim runner. The current smoke data are too sparse for real calibration, but the script establishes the analysis shape.

## C2. Actuator calibration

### Ramp metering

The current adapter maps controller ramp rate to green seconds in a 10-second cycle:

```text
green_sec = round(rate_vph / 1500 * 10), clamped to 0-8 s
```

This is a placeholder and should be calibrated using Vissim passage/release counts.

Needed sweep:

| Green in 10 s cycle | Measure |
|---:|---|
| 1 s | released veh/h |
| 2 s | released veh/h |
| 4 s | released veh/h |
| 6 s | released veh/h |
| 8 s | released veh/h |

Then replace the linear `rate → green_sec` mapping with an empirical lookup or fitted curve.

### Signal saturation

Calibrate:

- `network.movement_capacity_veh_h`
- `network.boundary_out_capacity_veh_h`
- `network.lost_time`
- `network.green_min`
- `network.green_max`

Use fixed green splits and high enough approach demand to observe saturation flow.

## C3. Urban MFD / setpoint calibration

Goal: recalibrate the leader's protected accumulation target against the Vissim plant.

Target parameters:

| Config parameter | Meaning |
|---|---|
| `leader.N_P_crit_veh` | protected-region MFD critical accumulation |
| `leader.N_P_star_range` | feasible protected accumulation target range |
| `leader.N_UF_star_range` | feasible urban-freeway transfer target range |
| `leader.mfd_storage_threshold_ratio` | storage penalty activation |
| `leader.mfd_boundary_queue_capacity_veh` | boundary queue guard capacity |

Recommended Vissim experiment:

- Vary urban demand while keeping freeway/ramp moderate.
- Use fixed signal timing first.
- Log protected urban accumulation and production.
- Fit the MFD peak and use that as the initial `N_P_crit_veh`.

## C4. Objective and controller tuning

Only after C1-C3 are reasonable, tune:

- `freeway_follower.ramp_queue_penalty`
- `freeway_follower.density_penalty`
- `freeway_follower.metering_smoothness_weight`
- `freeway_follower.vsl_smoothness_weight`
- `leader.metering_congestion_weight`
- `leader.metering_queue_weight`
- `leader.vsl_activation_density_ratio`
- `leader.metering_activation_density_ratio`
- `urban_follower.boundary_balance_weight`
- `urban_follower.green_smoothness_weight`
- `urban_follower.offset_smoothness_weight`

The tuning objective should not be just low TTT. For the target hysteresis environment, also track:

- loop area in accumulation-flow or density-flow space,
- breakdown onset time,
- recovery time,
- ramp spillback,
- VSL intervention frequency,
- signal green oscillation,
- queue fairness between D/F and A/B/C.

## Minimum acceptance criteria

Before calling the MPC calibrated:

1. Free-flow Vissim speed and MPC `v_free` differ by less than 10%.
2. Vissim max observed mainline flow and MPC `freeway_capacity_veh_h` differ by less than 15%.
3. D/F bottleneck segment indices are verified in action/state logs.
4. Ramp-meter commanded rate and Vissim released rate are monotonic and within an agreed tolerance.
5. Fixed-baseline and no-control runs reproduce a plausible breakdown/recovery loop under high demand.
6. Full controller improves at least one primary metric without creating ramp spillback or unrealistic signal/VSL oscillation.

## Current status

Done:

- Vissim controller bridge installed.
- Segment-start VSL DSDs installed.
- Vissim state to Numerical-Sim `TrafficState` adapter implemented.
- Topology calibration v0 applied for 5-segment D/F mapping.

Pending:

- Demand-sweep FD calibration runs.
- Ramp-meter green-to-release calibration.
- Signal saturation calibration.
- Urban MFD setpoint calibration.
- Closed-loop objective tuning for hysteresis scenarios.
