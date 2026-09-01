# Vissim full-spec calibration audit — 2026-06-28

## Validation Report

### Overall Assessment: Needs revision before controller tuning

No: only the off-ramp spillback capacity had been fully cross-checked against the actual Vissim geometry. A broader spot audit found additional mismatches or weakly verified assumptions in:

- urban / boundary / on-ramp storage capacity,
- nonuniform freeway segment lengths,
- signal saturation flow `q_sat`,
- F-ramp metering release fit.

The current calibration is usable as a scaffold, but not yet a fully Vissim-spec-consistent calibration.

## Sources inspected

- Vissim inventory:
  - `evaluation/eval_vsl_segmented_inventory/links.csv`
  - `evaluation/eval_vsl_segmented_inventory/connectors.csv`
  - `evaluation/vsl_install/vsl_segment_mapping.json`
  - `evaluation/signal_install/signal_manifest.csv`
- Calibration files:
  - `evaluation/calibration/vissim_network_calibration_v2_20260628.json`
  - `evaluation/calibration/vissim_calibrated_overrides_vector_20260626.json`
  - `evaluation/calibration/vissim_signal_green_fit_20260626.json`
- Adapter:
  - `evaluation/controllers/vissim_stackelberg_adapter.py`
- Spot state:
  - `evaluation/runs/diagnostic_vsl_rm_300s_20260628/diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s/decisions/state_000060.json`

## 1. Freeway geometry

### Verified

Total Vissim freeway length and lanes match the adapter-level abstraction:

| item | Vissim | adapter/model |
| --- | ---: | ---: |
| `FW_E` length | 2900.003 m | `5 × 0.58 km = 2900 m` |
| `FW_W` length | 2900.003 m | `5 × 0.58 km = 2900 m` |
| lanes | 2 | 2 |

### Issue: segment lengths are not uniform

The actual VSL / connector-defined segments are nonuniform:

| segment | actual length m |
| --- | ---: |
| `EB_S0_W_ENTRY_TO_D_DIVERGE` | 498.032 |
| `EB_S1_D_DIVERGE_TO_D_MERGE` | 313.359 |
| `EB_S2_D_MERGE_TO_F_DIVERGE` | 923.224 |
| `EB_S3_F_DIVERGE_TO_F_MERGE` | 293.535 |
| `EB_S4_F_MERGE_TO_E_EXIT` | 870.853 |
| `WB_S0_E_ENTRY_TO_F_DIVERGE` | 536.739 |
| `WB_S1_F_DIVERGE_TO_F_MERGE` | 617.511 |
| `WB_S2_F_MERGE_TO_D_DIVERGE` | 588.210 |
| `WB_S3_D_DIVERGE_TO_D_MERGE` | 654.785 |
| `WB_S4_D_MERGE_TO_W_EXIT` | 501.758 |

The adapter observation path reads `length_km` from Vissim state rows when forming density, but the propagation config still uses a single `freeway_segment_length_km = 0.58`. This can distort reconstructed vehicle counts and METANET propagation.

Spot check at `state_000060`:

```text
actual segment count sum             = 52.000 veh
uniform-0.58 reconstruction from rho = 54.558 veh
```

This is not the entire prediction-error problem, but it is a real geometry mismatch.

## 2. Urban / boundary storage capacity

### Physical lane-metre estimate

Using central jam spacing `6.49 m/veh` from the off-ramp audit:

| link class | Vissim physical range |
| --- | ---: |
| urban internal 436 m, 2 lanes | ~134 veh |
| urban internal 536 m, 2 lanes | ~165 veh |
| boundary 448 m, 2 lanes | ~138 veh |
| boundary 488 m, 2 lanes | ~150 veh |
| D ramp stem 191 m, 2 lanes | ~59 veh |
| F ramp stem 286 m, 2 lanes | ~88 veh |

### Issue

The Numerical-Sim defaults previously observed in `default.yaml` use larger generic storage abstractions:

- `grid_link_storage_veh = 220`
- many `urban_link_storage_veh` entries = 220
- on-ramp storage links = 180
- old off-ramp storage = 120

The revised v2 calibration now corrects off-ramp storage only:

| off-ramp storage | revised v2 |
| --- | ---: |
| `OR_D_E_storage` | 154 |
| `OR_D_W_storage` | 95 |
| `OR_F_E_storage` | 144 |
| `OR_F_W_storage` | 101 |

But ordinary urban internal, boundary, and on-ramp storage are still not geometry-calibrated. If controller penalties depend on protected accumulation / storage pressure, those capacities can still be too high.

## 3. Signal saturation flow / `q_sat`

### Current model value

The active calibration file still recommends:

```text
movement_capacity_veh_h = 1800 veh/h/approach
lost_time = 6.0 sec
```

### What the Vissim logging actually supports

From `vissim_signal_green_fit_20260626.json`:

| metric | value |
| --- | ---: |
| median fitted saturation flow | 829 veh/h/approach |
| median direct saturation proxy | 1541 veh/h/approach |
| median fitted lost time | 6.009 sec |
| median fit R² | ~0.25 |

Approach values vary wildly. Some approaches are underfed or effectively blocked:

- `D_L26` direct median: ~102 veh/h/approach
- `F_L32` direct median: ~26 veh/h/approach
- `B_L5` direct median: ~3747 veh/h/approach

### Interpretation

`q_sat = 1800` is not a verified Vissim spec. It is a conservative/heuristic initial value chosen because the fitted values were contaminated by underfed approaches and poor fit quality.

Before serious controller tuning, we need a cleaner saturated approach discharge experiment or a per-approach service curve, especially for off-ramp approaches `D_L26` and `F_L32`.

## 4. Ramp metering release

D-ramp green-to-release has a usable fitted curve in the current calibration.

F-ramp is still flagged:

```text
F_status = invalid_for_physical_metering_fit
```

The adapter can still consume `F_green_to_release_vph_raw` if a tuning enables metered F. That is risky because the F fit likely reflects a route/lane/connector bottleneck, not pure metering release capacity.

## 5. Off-ramp capacity

This was corrected after subagent cross-check:

| item | old stock | first v2 | revised v2 |
| --- | ---: | ---: | ---: |
| per model off-ramp | 480 | 240 | 95–154 direction-specific |
| `FW_E` same-direction D+F | 960 | 480 | 298 |
| `FW_W` same-direction D+F | 960 | 480 | 196 |

Validation output:

- `evaluation/runs/calibration_v2_geometry_capacity_pfo_check/action_000300.json`

## Required fixes before controller tuning

1. Replace uniform freeway segment length in the controller rollout with segment-specific lengths, or store segment length profile in `NetworkConfig`.
2. Geometry-calibrate ordinary urban internal, boundary, and on-ramp storage capacities.
3. Refit signal service / `q_sat` using saturated approach runs or per-approach discharge curves.
4. Guard F-ramp metering so invalid F release calibration is not used silently.
5. Keep off-ramp physical storage, downstream signal service, and planning spillback thresholds separate.

## Caveat

This audit did not modify controller behavior except for the previously applied off-ramp geometry-cap correction. It documents remaining calibration risks that should be fixed before interpreting PFO/MPC performance claims.
