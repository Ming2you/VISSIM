# Vissim physical-spec cross-check and adapter calibration

Date: 2026-06-28

Scope: Vissim physical values only. METANET empirical/dynamic parameters such as `kappa`, `nu`, `tau`, and similar calibration constants were intentionally excluded.

## Cross-check roles

- Geometry inventory reviewer: checked Vissim link/connector/VSL/signal geometry against `vissim_network_calibration_v2_20260628.json`.
- Code wiring reviewer: checked which physical values the Vissim adapter actually injects into Numerical-Sim config/runtime.
- Signal/ramp reviewer: checked q_sat/lost-time and ramp metering calibration defensibility.

## Applied corrections

| Area | Applied value / behavior | Evidence/source |
|---|---|---|
| Freeway segment lengths | `FW_E = [0.498032, 0.313359, 0.923224, 0.293535, 0.870853] km`; `FW_W = [0.536739, 0.617511, 0.588210, 0.654785, 0.501758] km` | `evaluation/vsl_install/vsl_segment_mapping.json` |
| Freeway vehicle counts | Adapter runtime patches `TrafficState.freeway_vehicle_count_by_link()` and `TrafficState.total_freeway_vehicles()` to use the Vissim segment-length profile. | `evaluation/controllers/vissim_stackelberg_adapter.py` |
| Urban/boundary/on-ramp/off-ramp storage | 29 `urban_link_storage_veh` keys are now geometry-calibrated from lane-metres and central jam spacing `6.49 m/veh`. | `evaluation/eval_vsl_segmented_inventory/links.csv`, `evaluation/signal_install/signal_manifest.csv` |
| Boundary queue scalar | `boundary_queue_max_veh = 147.3` as a scalar fallback from the largest inbound boundary stopline storage. | Signal stopline geometry |
| Ramp queue scalar | `ramp_queue_max_veh = 39.5` as a scalar fallback from the largest one-lane pre-meter storage. | F ramp meter at 256.326 m / 6.49 |
| Off-ramp spillback capacity | `OR_D_W=95`, `OR_F_W=102`, `OR_D_E=154`, `OR_F_E=144`; total `495 veh`. | Connector + assigned stem lane to signal stopline |
| Legacy spillback metadata | Marked `deprecated_not_physical_do_not_use`. | Prevents accidental reuse of old `480/960 veh` nonphysical values |
| Signal q_sat/lost time | Kept scalar `q_sat = 1800 veh/h/approach`, `lost_time = 6.0 s`. | Signal fits are weak/underfed; per-approach curves not promoted |
| F ramp guard | `F_status=invalid_for_physical_metering_fit` now forces F to always-green/monitor-only unless explicitly allowed. F model cap uses full-green observed discharge `237.073 veh/h`, not the invalid raw max `316.098 veh/h`. | Ramp calibration cross-check |

## Verification

Smoke command:

```powershell
python evaluation\controllers\vissim_stackelberg_adapter.py --state-json evaluation\runs\diagnostic_vsl_rm_300s_20260628\diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s\decisions\state_000060.json --previous-action-json evaluation\runs\diagnostic_vsl_rm_300s_20260628\diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s\decisions\action_000001.json --out-action-json evaluation\runs\physical_spec_adapter_check_20260628\action_000060.json --out-action-csv evaluation\runs\physical_spec_adapter_check_20260628\action_000060.csv --controller diagnostic-vsl-rm --mode fast-smoke --tuning-json evaluation\configs\diagnostic_vsl_rm_metered_f.json
```

Key smoke metadata:

| Check | Result |
|---|---:|
| `calibration_state_vehicle_count_patch_installed` | `1.0` |
| `calibration_freeway_segment_length_profile_applied` | `1.0` |
| `calibration_freeway_segment_length_count` | `10.0` |
| `network_urban_link_storage_count` | `29.0` |
| `network_urban_link_storage_total_veh` | `3733.4` |
| `network_boundary_queue_max_veh` | `147.3` |
| `network_ramp_queue_max_veh` | `39.5` |
| `calibration_offramp_capacity_total_veh` | `495.0` |
| `F_ramp_mode` under metered-F diagnostic tuning | `always_green` |
| `F_ramp_invalid_guard_active` | `1.0` |
| F ramp CSV green | `10.0 s` |

## Remaining limitation

The adapter now fixes Vissim-side vehicle-count reconstruction, controller state summaries, and `TrafficState` vehicle-count methods. The core METANET propagation equation in the Desktop Numerical-Sim source may still use the scalar `freeway_segment_length_km` directly. For exact segment-specific propagation, promote `freeway_segment_length_profile_km` into the core `NetworkConfig`/METANET implementation instead of relying only on adapter runtime patches.
