# Static route installation report

Date: 2026-06-25

## Output Vissim files

Input detector-instrumented copy:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_control.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_control.layx`

Routed evaluation copy:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_routed.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_routed.layx`

The original source network was preserved:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- Source timestamp remained `2026-06-25 18:00:53`

## Installer

Script:

- `scripts/install_eval_routes.vbs`

Manifest:

- `evaluation/route_install/route_manifest.csv`

Inventory after installation:

- `evaluation/eval_routed_inventory/inventory.json`
- `evaluation/eval_routed_inventory/network_mapping.json`
- `evaluation/eval_routed_inventory/missing_objects.json`

## Object count changes

| Object type | Before detector copy | Routed copy |
|---|---:|---:|
| Static route decisions | 0 | 9 |
| Static routes | 0 | 68 |
| Detectors | 120 | 120 |
| Data collection points | 104 | 104 |
| Queue counters | 29 | 29 |
| Signal controllers | 9 | 9 |
| Signal heads | 0 | 0 |

All route candidates succeeded:

- Route decisions: 9
- Static routes: 68
- Failed routes: 0

## Route decision origins

| Origin | Start link | Routes |
|---|---:|---:|
| AW | 1 | 8 |
| AN | 3 | 8 |
| BN | 9 | 8 |
| CN | 15 | 8 |
| CE | 18 | 8 |
| DW | 21 | 8 |
| FE | 30 | 8 |
| FW_EB | 33 | 6 |
| FW_WB | 34 | 6 |

Vissim automatically generated route `LinkSeq` values from destination links.

Example:

```text
AW → CE: 10001,5,10013,11,10025
AW → FW_EB: 10001,5,10014,13,10049,27,10059,31,10073
AW → FW_WB: 10002,7,10038,25,10066
```

## Smoke test after route installation

Smoke output:

- `evaluation/runs/eval_routed_smoke/global_state_180s.csv`
- `evaluation/runs/eval_routed_smoke/summary_180s.json`

Result: PASS

Summary:

```json
{
  "rows": 37,
  "first_sec": "0",
  "last_sec": "180",
  "max_total_vehicles": 25,
  "final_total_vehicles": 24,
  "max_urban_vehicles": 8,
  "max_freeway_vehicles": 5,
  "max_ramp_vehicles": 2,
  "max_boundary_vehicles": 12,
  "max_other_vehicles": 4,
  "max_stopped_vehicles": 0,
  "min_mean_speed_kph_when_vehicles_present": 52.156
}
```

## Remaining work

Next phase:

1. Add signal groups and signal heads.
2. Configure fixed-time timing or COM-driven signal state control.
3. Add VSL desired speed decisions.
4. Run fixed-time baseline and then ramp/VSL/controller ablation scenarios.
