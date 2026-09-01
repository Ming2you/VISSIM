# Detector installation report

Date: 2026-06-25

## Output Vissim files

Source geometry files were preserved:

- Source network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- Source layout: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.layx`

Detector-instrumented evaluation copy:

- Evaluation network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_control.inpx`
- Evaluation layout: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_control.layx`

The source `modi.inpx` timestamp remained unchanged after installation:

- `2026-06-25 18:00:53`

## Installer

Script:

- `scripts/install_eval_detectors.vbs`

Manifest:

- `evaluation/detector_install/detector_manifest.csv`

Inventory after installation:

- `evaluation/eval_control_inventory/inventory.json`
- `evaluation/eval_control_inventory/network_mapping.json`
- `evaluation/eval_control_inventory/missing_objects.json`
- `evaluation/eval_control_inventory/links.csv`
- `evaluation/eval_control_inventory/connectors.csv`

## Object count changes

| Object type | Before | After | Added |
|---|---:|---:|---:|
| Links including connectors | 108 | 108 | 0 |
| Data collection points | 64 | 104 | 40 |
| Queue counters | 23 | 29 | 6 |
| Signal controllers | 0 | 9 | 9 |
| Signal heads | 0 | 0 | 0 |
| Detectors | 0 | 120 | 120 |
| Static route decisions | 0 | 0 | 0 |
| Desired speed decisions | 0 | 0 | 0 |

Signal controllers added here are placeholders required by Vissim for detector ownership.
Signal heads and actual controller actuation are intentionally left for the next phase.

## Added object groups

| Object group | Count |
|---|---:|
| Placeholder signal controllers | 9 |
| Approach stop-line detectors | 40 |
| Approach advance detectors | 40 |
| Freeway/VSL mainline detectors | 24 |
| Off-ramp entry detectors | 4 |
| Ramp-meter queue detectors | 4 |
| Ramp-meter presence detectors | 4 |
| Ramp-meter passage detectors | 4 |
| Ramp flow/speed data collection points | 24 |
| Freeway bottleneck data collection points | 16 |
| Ramp-meter queue counters | 2 |
| Freeway queue counters | 4 |

## Placeholder signal controllers

| SC no | Name | Intended role |
|---:|---|---|
| 1 | `EVAL_SC_A` | Future intersection A signal control |
| 2 | `EVAL_SC_B` | Future intersection B signal control |
| 3 | `EVAL_SC_C` | Future intersection C signal control |
| 4 | `EVAL_SC_D` | Future intersection D signal/ramp-stem control |
| 5 | `EVAL_SC_F` | Future intersection F signal/ramp-stem control |
| 6 | `EVAL_SC_RM_D` | Future D ramp metering |
| 7 | `EVAL_SC_RM_F` | Future F ramp metering |
| 8 | `EVAL_SC_VSL_EB` | Future EB VSL detector ownership |
| 9 | `EVAL_SC_VSL_WB` | Future WB VSL detector ownership |

## Smoke test after detector installation

Smoke output:

- `evaluation/runs/eval_control_detector_smoke/global_state_60s.csv`
- `evaluation/runs/eval_control_detector_smoke/summary_60s.json`

Result: PASS

Summary:

```json
{
  "rows": 13,
  "first_sec": "0",
  "last_sec": "60",
  "max_total_vehicles": 8,
  "final_total_vehicles": 8,
  "max_urban_vehicles": 1,
  "max_freeway_vehicles": 2,
  "max_ramp_vehicles": 1,
  "max_boundary_vehicles": 4,
  "max_stopped_vehicles": 0,
  "min_mean_speed_kph_when_vehicles_present": 53.618
}
```

Pass criteria:

- The evaluation INPX loaded through Vissim COM.
- The simulation advanced to 60 seconds.
- Global state rows were logged every 5 seconds from 0 to 60 seconds.
- Vehicles were generated.
- The final row was not affected by Vissim's end-of-period reset behavior.
- The original source INPX timestamp remained unchanged.

## Remaining work

Next phase:

1. Add static route decisions/routes to the evaluation copy.
2. Add signal heads to A/B/C/D/F using the placeholder signal controllers.
3. Add ramp-meter signal heads on links 25 and 31.
4. Add VSL desired speed decisions on freeway links 33 and 34.
5. Run fixed-time/no-actuation baseline, then ramp-meter/VSL/controller ablations.
