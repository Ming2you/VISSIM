# Vissim evaluation environment setup summary

Date: 2026-06-25  
Workspace: `C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com`

## 1. Scope and geometry policy

The current user-edited Vissim network is treated as the frozen geometry source.

Source files:

- Network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- Layout: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.layx`

Important policy:

- Do not rewrite or regenerate link/connector geometry.
- New detector, route, signal, ramp-metering, and VSL objects should be added only to a separate evaluation copy, e.g. `modi_eval_control.inpx`.
- Existing smoke tests set demand in memory through COM and do not save changes to the source INPX.

## 2. Current inventory

Generated inventory folder:

- `evaluation/current_inventory/inventory.json`
- `evaluation/current_inventory/network_mapping.json`
- `evaluation/current_inventory/missing_objects.json`
- `evaluation/current_inventory/required_objects_phase_plan.json`
- `evaluation/current_inventory/links.csv`
- `evaluation/current_inventory/connectors.csv`
- `evaluation/current_inventory/object_inventory_summary.md`

Generated smoke/group config:

- `evaluation/generated/global_state_config.vbs`
- `evaluation/generated/global_state_config.json`

Current parsed object counts:

| Object type | Count |
|---|---:|
| Road links | 34 |
| Connectors | 74 |
| Total link objects | 108 |
| Vehicle inputs | 9 |
| Data collection points | 64 |
| Queue counters | 23 |
| Static route decisions | 0 |
| Static routes | 0 |
| Signal controllers | 0 |
| Signal heads | 0 |
| Nodes | 8 |

Key mapping:

- Urban links: 5, 6, 7, 8, 11, 12, 13, 14, 19, 20, 23, 24, 27, 28
- Freeway links: 33, 34
- Ramp links: 25, 26, 31, 32
- Boundary links: 1, 2, 3, 4, 9, 10, 15, 16, 17, 18, 21, 22, 29, 30
- D trumpet ramp links: 25, 26
- F trumpet ramp links: 31, 32
- Ramp/freeway-related connectors: 20 connectors
- Intersection turn connectors: 54 connectors

## 3. Existing runnable scripts

Inventory:

```powershell
python scripts\inventory_vissim_inpx.py --inpx "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx" --out-dir evaluation\current_inventory
```

Generate global-state VBS config from inventory/mapping:

```powershell
python scripts\generate_global_state_config.py --mapping evaluation\current_inventory\network_mapping.json --inventory evaluation\current_inventory\inventory.json --out-vbs evaluation\generated\global_state_config.vbs --out-json evaluation\generated\global_state_config.json
```

Load probe:

```powershell
cscript.exe //nologo scripts\probe_vissim_load_only.vbs "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx"
```

Single-step probe:

```powershell
cscript.exe //nologo scripts\probe_vissim_sim_only.vbs "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx"
```

Global-state smoke:

```powershell
cscript.exe //nologo scripts\run_global_state_smoke.vbs "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\low_demand_smoke\global_state.csv" 180 60 120 5
```

## 4. Global-state smoke runner behavior

Script:

- `scripts/run_global_state_smoke.vbs`

Inputs:

1. network INPX
2. output CSV
3. simulation period in seconds
4. urban vehicle input volume in vph
5. freeway vehicle input volume in vph
6. control/logging interval in seconds

Behavior:

- Loads the source network through Vissim COM.
- Loads `evaluation/generated/global_state_config.vbs` when present.
- Sets all non-freeway vehicle inputs to the urban volume in memory.
- Sets freeway vehicle inputs by input link number, not by name string.
- Does not save the network.
- Runs an explicit step-count loop to avoid Vissim reset behavior exactly at `SimPeriod`.
- Sets internal `SimPeriod = requested_period + 1` so the last logged row is not post-reset.
- Logs a controller-ready global state every control interval.

Output columns:

- `sim_sec`
- `total_vehicles`
- `urban_vehicles`
- `freeway_vehicles`
- `ramp_vehicles`
- `boundary_vehicles`
- `other_vehicles`
- `mean_speed_kph`
- `stopped_vehicles`
- `controller_action`

Current action mode:

- `GLOBAL_NOOP`

Reason:

- Signal controllers and signal heads do not exist yet.

## 5. Existing smoke result

Run folder:

- `evaluation/runs/low_demand_smoke`

Files:

- `global_state.csv`
- `summary.json`
- `controller_actions_noop.jsonl`
- `global_state_30s.csv`

Latest 180-second low-demand smoke summary:

```json
{
  "rows": 37,
  "first_sec": "0",
  "last_sec": "180",
  "max_total_vehicles": 26,
  "final_total_vehicles": 25,
  "max_urban_vehicles": 4,
  "max_freeway_vehicles": 6,
  "max_ramp_vehicles": 4,
  "max_boundary_vehicles": 11,
  "min_mean_speed_kph_when_vehicles_present": 52.357,
  "max_stopped_vehicles": 0
}
```

Interpretation:

- The network loads.
- The simulation advances.
- Vehicles are generated under low demand.
- Global state logging works.
- Ramp links receive vehicles during the smoke test.
- This does not yet prove route realism or signal control performance because route decisions and signal objects are absent.

## 6. Scenario/config files

Low-demand smoke config:

- `evaluation/configs/low_demand_smoke_global.json`

Baseline scenario config:

- `evaluation/configs/baseline_scenario_global_v0.json`

Controller connection:

- `evaluation/controllers/global_controller_api.py`
- `evaluation/controllers/README.md`

Current controller API status:

- Reads the global-state CSV.
- Produces JSONL controller actions.
- Supports `noop` and `fixed-time-placeholder`.
- Does not actuate Vissim yet.

## 7. Detector and actuator plan

Detector/actuator design document:

- `evaluation/controllers/actuator_detector_design.md`

Detector families to use:

| Purpose | Vissim object | Role |
|---|---|---|
| Evaluation flow/speed | `DataCollectionPoint` | per-lane flow/speed output |
| Queue/spillback | `QueueCounter` | queue and spillback measurement |
| Controller input | `Detector` | presence/occupancy/pulse input for signal/ramp/VSL logic |

Recommended next detector additions:

1. Ramp DCPs on links 25, 26, 31, 32.
2. Ramp queue/presence detectors on on-ramp links 25 and 31.
3. Mainline detector pairs upstream/downstream of D/F merge-diverge zones on links 33 and 34.
4. Stop-line detectors at A/B/C/D/F controlled approaches.
5. Advance detectors upstream of A/B/C/D/F approaches.

Ramp metering:

- Implement as `SignalHead` objects on D/F on-ramp links, mainly links 25 and 31.
- Controller action should set ramp cycle/green split.
- Queue override should prevent excessive ramp spillback.

VSL:

- Implement as `DesSpeedDecision` objects on freeway links 33 and 34.
- Use discrete speed distributions such as 40, 50, 60, 70, 80, 90, 100 km/h.
- Controller action should set speed by freeway zone.

## 8. Known gaps before full controller evaluation

The current environment is good enough for:

- Load verification
- Low-demand smoke verification
- Global-state logging
- Controller API skeleton validation

It is not yet enough for:

- OD-controlled route realism
- Signalized intersection control
- Ramp metering actuation
- VSL actuation
- Detector-based controller comparison
- Hysteresis-loop performance analysis under congested demand

Blocking missing objects:

1. Static route decisions and route definitions.
2. Signal controllers and signal heads at A/B/C/D/F.
3. Ramp meter signal heads.
4. Desired speed decisions and speed distributions for VSL.
5. Dedicated `Detector` objects for signal/ramp/VSL control.

## 9. Review checklist

The reviewer should verify:

1. The document matches the generated artifacts.
2. The current scripts do not save or overwrite the user-edited source INPX.
3. The smoke runner's explicit step-count loop avoids the Vissim `SimPeriod` reset issue.
4. Global state grouping matches `network_mapping.json`.
5. The current smoke result is enough to justify detector installation as the next step.
6. The limitations are stated clearly, especially the absence of route and signal objects.
7. The proposed ramp metering and VSL implementation uses appropriate Vissim object types.
