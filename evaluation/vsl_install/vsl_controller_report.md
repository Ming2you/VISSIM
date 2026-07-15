# VSL Speed Controller Implementation Report

Date: 2026-06-25

## Outcome

Implemented the first VSL/speed-control layer for the staged Vissim evaluation network.

Update: this initial station/bottleneck-oriented layout has been superseded for controller integration by the segment-start layout documented in `evaluation/vsl_install/vsl_segment_start_report.md`.

New staged Vissim files:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl.layx`

The source geometry/network was not modified:

- original user-edited network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- verified `LastWriteTime`: `2026-06-25 오후 6:00:53`

## Implemented scripts

- `scripts/probe_desired_speed_api.vbs`
- `scripts/install_eval_vsl.vbs`
- `scripts/run_com_speed_controller.vbs`

## Vissim COM API findings

Vissim 2020 uses:

- collection: `Vissim.Net.DesSpeedDecisions`
- distribution collection: `Vissim.Net.DesSpeedDistributions`
- create method: `Vissim.Net.DesSpeedDecisions.AddDesSpeedDecision(0, lane, pos)`
- speed distribution attribute by vehicle class: `DesSpeedDistr(<vehicle_class_no>)`

Confirmed writable/readable examples:

- `DesSpeedDistr(10)` for Car
- `DesSpeedDistr(20)` for HGV
- `DesSpeedDistr(30)` for Bus

The staged speed controller writes these three vehicle classes together.

## Installed VSL infrastructure

Installed 16 Desired Speed Decisions:

- 2 freeway directions
- 4 VSL stations per direction
- 2 lanes per station

| Direction | Link | Section | Position m | Purpose |
|---|---:|---|---:|---|
| EB | 33 | EB_PRE_D | 430 | upstream of D ramp area |
| EB | 33 | EB_D_BOT | 880 | D bottleneck/ramp area |
| EB | 33 | EB_PRE_F | 1680 | upstream of F ramp area |
| EB | 33 | EB_F_BOT | 2070 | F bottleneck/ramp area |
| WB | 34 | WB_PRE_F | 430 | upstream of F ramp area |
| WB | 34 | WB_F_BOT | 1200 | F bottleneck/ramp area |
| WB | 34 | WB_PRE_D | 1680 | upstream of D ramp area |
| WB | 34 | WB_D_BOT | 2430 | D bottleneck/ramp area |

Every station has one Desired Speed Decision per lane.

Inventory after install:

- desired speed decisions: 16
- road links: 34
- connectors: 74
- detectors: 120
- signal heads: 44
- signal controllers: 9

Manifest:

- `evaluation/vsl_install/vsl_manifest.csv`

Inventory:

- `evaluation/eval_vsl_inventory/inventory.json`
- `evaluation/eval_vsl_inventory/links.csv`
- `evaluation/eval_vsl_inventory/connectors.csv`

## Speed controller smoke test

Smoke runner:

- `scripts/run_com_speed_controller.vbs`

Run network:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl.inpx`

Run outputs:

- `evaluation/runs/com_speed_smoke/state_180s.csv`
- `evaluation/runs/com_speed_smoke/actions_180s.csv`
- `evaluation/runs/com_speed_smoke/summary_180s.json`

Command:

```powershell
cscript.exe //nologo scripts\run_com_speed_controller.vbs "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl.inpx" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\com_speed_smoke\state_180s.csv" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\com_speed_smoke\actions_180s.csv" 180 60 1200 5 7
```

Parameters:

- simulation duration: 180 s
- urban input demand: 60 veh/h
- freeway input demand: 1200 veh/h
- control logging interval: 5 s
- random seed: 7

## Smoke controller profile

The current controller is a VSL actuation test controller, not yet the final adaptive policy.

It uses a deterministic three-stage profile:

| Time | Profile | PRE station limit | BOT station limit |
|---:|---|---:|---:|
| 0-59 s | FREE_FLOW | 120 km/h | 120 km/h |
| 60-119 s | MODERATE | 100 km/h | 80 km/h |
| 120-180 s | RESTRICTIVE | 80 km/h | 60 km/h |

This verifies that spatially different VSL commands can be issued across upstream and bottleneck stations.

## Smoke test result

The 180-second run completed successfully.

Summary:

- state log rows: 37
- action log rows: 592
- DSD objects loaded: 16
- speed commands observed: 60, 80, 100, 120 km/h
- readback mismatch count: 0
- final total vehicles in network: 100
- final freeway mean speed: 65.132 km/h

Profile counts in state log:

- FREE_FLOW: 12
- MODERATE: 12
- RESTRICTIVE: 13

The final action rows show:

- upstream PRE stations set/read as 80 km/h
- bottleneck BOT stations set/read as 60 km/h
- Car/HGV/Bus readback values all match the commanded speed

## Current limitations

This establishes the VSL actuator layer. It is not yet the final speed-control policy.

Remaining steps:

1. Replace the deterministic step profile with the actual controller policy.
2. Connect VSL to global/freeway state first, then detector-based state.
3. Combine VSL with ramp metering and intersection signal control in one runner.
4. Run high-demand hysteresis scenarios and compare:
   - no-control baseline
   - signal/ramp-only control
   - VSL-only control
   - combined control

## Assessment

The Vissim evaluation network now supports runtime COM speed control through Desired Speed Decisions. The staged speed controller can command different limits by freeway direction, station, lane, and vehicle class, and the smoke test confirms that Vissim accepts and returns the commanded speed distributions during simulation.
