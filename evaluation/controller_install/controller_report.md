# COM Fixed-Time Controller Implementation Report

Date: 2026-06-25

## Outcome

Implemented and smoke-tested a COM-driven fixed-time baseline controller for the staged Vissim evaluation network.

The controller is implemented as:

- `scripts/run_com_fixed_time_controller.vbs`

It loads:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_signalized.inpx`

and writes run logs to:

- `evaluation/runs/com_fixed_time_smoke/state_180s.csv`
- `evaluation/runs/com_fixed_time_smoke/actions_180s.csv`
- `evaluation/runs/com_fixed_time_smoke/summary_180s.json`

The original user-edited source network was not modified:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- verified `LastWriteTime`: `2026-06-25 오후 6:00:53`

## Controller architecture

The current controller is a baseline fixed-time controller that drives Vissim signal groups through COM during simulation runtime.

Runtime sequence:

1. Load `modi_eval_signalized.inpx`.
2. Apply temporary low/smoke-test demand in memory.
3. Activate signal controllers 1-7.
4. Enable `ContrByCOM` on controlled signal groups.
5. During simulation, write `SigState` every simulation second.
6. Log global state and controller actions.
7. Stop without saving the network file.

Signal groups are controlled as follows:

| Controller | Name | Control role | Signal groups |
|---:|---|---|---|
| 1 | A | Urban/freeway intersection | SG1 major, SG2 minor |
| 2 | B | Urban/freeway intersection | SG1 major, SG2 minor |
| 3 | C | Urban/freeway intersection | SG1 major, SG2 minor |
| 4 | D | Urban/freeway intersection | SG1 major, SG2 minor |
| 5 | F | Urban/freeway intersection | SG1 major, SG2 minor |
| 6 | RM_D | Ramp metering | SG1 ramp meter |
| 7 | RM_F | Ramp metering | SG1 ramp meter |
| 8 | Reserved | Detector placeholder | not controlled |
| 9 | Reserved | Detector placeholder | not controlled |

## Fixed-time timing used in smoke test

Intersection controllers 1-5:

- Cycle length: 90 s
- Major green: 40 s
- Major amber: 3 s
- All-red 1: 2 s
- Minor green: 40 s
- Minor amber: 3 s
- All-red 2: 2 s

Ramp metering controllers 6-7:

- Cycle length: 10 s
- Green: 2 s
- Amber: 1 s
- Red: 7 s

## Smoke test command

```powershell
cscript.exe //nologo scripts\run_com_fixed_time_controller.vbs "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_signalized.inpx" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\com_fixed_time_smoke\state_180s.csv" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\com_fixed_time_smoke\actions_180s.csv" 180 60 120 5
```

Parameters:

- simulation duration: 180 s
- urban input demand: 60 veh/h
- freeway input demand: 120 veh/h
- random seed: 5

## Smoke test result

The controller completed the 180-second simulation successfully.

Summary:

- state log rows: 37
- action log rows: 1260
- last logged simulation time: 180 s
- final total vehicles in network: 25
- average logged mean speed: 46.060 km/h
- final logged mean speed: 30.591 km/h
- final stopped vehicles: 9

Observed phase/action rows:

| Phase | Rows |
|---|---:|
| MAJOR_GREEN | 400 |
| MAJOR_AMBER | 30 |
| ALL_RED_1 | 20 |
| MINOR_GREEN | 400 |
| MINOR_AMBER | 30 |
| ALL_RED_2 | 20 |
| RAMP_GREEN | 72 |
| RAMP_AMBER | 36 |
| RAMP_RED | 252 |

The final action rows show the controller transitioning from all-red/ramp-red at 179 s to major-green/ramp-green at 180 s, confirming that runtime COM signal actuation is active.

## Logged outputs

`state_180s.csv` columns:

- `sim_sec`
- `total_vehicles`
- `urban_vehicles`
- `freeway_vehicles`
- `ramp_vehicles`
- `boundary_vehicles`
- `other_vehicles`
- `mean_speed_kph`
- `stopped_vehicles`
- `controller_mode`
- `phase_A`
- `phase_B`
- `phase_C`
- `phase_D`
- `phase_F`
- `ramp_meter_D`
- `ramp_meter_F`

`actions_180s.csv` columns:

- `sim_sec`
- `controller_mode`
- `sc_no`
- `control_name`
- `sg1_state`
- `sg2_state`
- `phase_label`

## Current limitations

This is a baseline controller, not yet the final adaptive controller.

Remaining implementation steps:

1. Add VSL infrastructure through Vissim desired-speed decisions or equivalent COM-controlled speed-control objects.
2. Add detector-based state extraction path after the global-state controller path is stable.
3. Replace fixed-time phase logic with the actual controller policy.
4. Calibrate ramp metering logic against queue/speed/occupancy state instead of the current fixed 10-second cycle.
5. Run stronger demand scenarios to evaluate hysteresis-loop behavior.

## Assessment

The signalized staged network is now controllable through COM at runtime. The baseline fixed-time controller can be used as the first evaluation reference and as the integration harness for the later adaptive controller, detector-based observation path, ramp metering policy, and VSL policy.
