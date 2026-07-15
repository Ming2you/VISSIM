# Signal head installation report

Date: 2026-06-25

## Output Vissim files

Input routed copy:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_routed.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_routed.layx`

Signalized evaluation copy:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_signalized.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_signalized.layx`

The original source network was preserved:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- Source timestamp remained `2026-06-25 18:00:53`

## Installer

Script:

- `scripts/install_eval_signal_heads.vbs`

Manifest:

- `evaluation/signal_install/signal_manifest.csv`

Inventory after installation:

- `evaluation/eval_signalized_inventory/inventory.json`
- `evaluation/eval_signalized_inventory/network_mapping.json`
- `evaluation/eval_signalized_inventory/missing_objects.json`

## Object counts

| Object type | Routed copy | Signalized copy |
|---|---:|---:|
| Static route decisions | 9 | 9 |
| Static routes | 68 | 68 |
| Signal controllers | 9 | 9 |
| Signal groups | 0 | 12 |
| Signal heads | 0 | 44 |
| Detectors | 120 | 120 |
| Data collection points | 104 | 104 |
| Queue counters | 29 | 29 |

## Signal object groups

| Object group | Count |
|---|---:|
| Signal groups | 12 |
| Intersection major-axis signal heads | 20 |
| Intersection minor/ramp-axis signal heads | 20 |
| Ramp-meter signal heads | 4 |

Signal controllers 1–7 were set inactive after signal head installation. This is intentional:

- Signal heads are present and mapped to signal groups.
- Fixed-time timing / controller actuation is not configured yet.
- Keeping SCs inactive prevents the newly installed signal heads from unexpectedly stopping traffic before timing is installed.

## Signal controller mapping

| SC no | Role |
|---:|---|
| 1 | A intersection |
| 2 | B intersection |
| 3 | C intersection |
| 4 | D intersection |
| 5 | F intersection |
| 6 | D ramp metering |
| 7 | F ramp metering |
| 8 | EB VSL detector ownership |
| 9 | WB VSL detector ownership |

## Smoke test after signal head installation

Smoke output:

- `evaluation/runs/eval_signalized_smoke/global_state_180s.csv`
- `evaluation/runs/eval_signalized_smoke/summary_180s.json`

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
  "min_mean_speed_kph_when_vehicles_present": 52.108
}
```

## COM API notes discovered

- Signal group creation works with `sc.SGs.AddSignalGroup(no)`.
- Signal head creation works with `Vissim.Net.SignalHeads.AddSignalHead(no, lane, pos)`.
- Signal head assignment to a group works by setting `SG` to a string such as `1-2`.
- Fixed-time signal group `SigState` is not directly writable through `AttValue`.

## Remaining work

Next phase:

1. Probe/configure fixed-time signal timing or COM-driven external signal control.
2. Enable signal controllers after timing logic is verified.
3. Add VSL `DesSpeedDecision` objects on freeway links 33 and 34.
4. Run baseline, ramp-meter, VSL, and combined-controller experiments.
