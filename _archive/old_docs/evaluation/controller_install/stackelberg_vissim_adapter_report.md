# Stackelberg MPC Vissim Adapter Report

Date: 2026-06-25

## Outcome

Implemented and smoke-tested a first Vissim runtime adapter for the Numerical-Sim `StackelbergMPCController`.

The controller loop is split into two pieces:

- `evaluation/controllers/vissim_stackelberg_adapter.py`
- `scripts/run_stackelberg_vissim_controller.vbs`

The active staged Vissim network is:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx`

The original user-edited source network was not modified:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- verified `LastWriteTime`: `2026-06-25 오후 6:00:53`

## Architecture

`pywin32` is not available in the current Python environment, so the runtime architecture keeps Vissim COM ownership in VBScript and calls the Python controller adapter only for decisions.

Runtime sequence:

1. VBScript loads the staged Vissim network through COM.
2. VBScript writes the current Vissim state to `state_*.json`.
3. Python adapter converts the Vissim state into Numerical-Sim `TrafficState`.
4. Python adapter calls `StackelbergMPCController.decide_with_info(...)`.
5. Python adapter writes controller action to both JSON and actuator CSV.
6. VBScript reads the actuator CSV and applies:
   - VSL through Desired Speed Decision distribution attributes.
   - intersection signals through COM `SigState`.
   - ramp metering through COM `SigState`.
7. VBScript logs global state and actuator readback.

The current adapter mode is intentionally light for COM integration smoke tests:

- `adapter_mode`: `fast-smoke`
- MPC horizon: 1 step
- control horizon: 1 step
- serial candidate evaluation
- fallback disabled

This is not yet the final heavy/offline controller profile; it is the safe first bridge proving that Vissim can call the controller and receive/apply actions during simulation.

## Vissim actuator mapping

### VSL

VSL is applied to the 20 Desired Speed Decisions installed at the starts of the 10 mainline control segments:

| Direction | Vissim link | Numerical-Sim link | Segments | Lanes | DSD count |
|---|---:|---|---:|---:|---:|
| EB | 33 | `FW_E` | 5 | 2 | 10 |
| WB | 34 | `FW_W` | 5 | 2 | 10 |

The segment-to-DSD map is stored in:

- `evaluation/vsl_install/vsl_segment_mapping.json`

Topology calibration update:

- The Vissim freeway abstraction uses 5 segments per direction.
- `FW_E` D/F weave segments are indices 1 and 3.
- `FW_W` F/D weave segments are indices 1 and 3.
- The adapter now overrides Numerical-Sim's default 4-segment ramp/off-ramp indices for this Vissim plant.
- Detailed profile: `evaluation/calibration/mpc_vissim_topology_profile_v0.json`

### Signals

Intersection signal controllers:

| Vissim SC | Logical node |
|---:|---|
| 1 | A |
| 2 | B |
| 3 | C |
| 4 | D |
| 5 | F |

The adapter maps controller phase greens into `major_green`, `minor_green`, and `offset` rows for each node.

### Ramp metering

Ramp-metering signal controllers:

| Vissim SC | Logical ramp group |
|---:|---|
| 6 | D |
| 7 | F |

The controller returns ramp-metering rates for Numerical-Sim ramps. The Vissim runner currently converts these into a green duration inside a 10-second ramp cycle.

## Smoke test command

```powershell
cscript.exe //nologo "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\scripts\run_stackelberg_vissim_controller.vbs" "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\stackelberg_vissim_smoke\state_120s.csv" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\stackelberg_vissim_smoke\actions_120s.csv" "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com\evaluation\runs\stackelberg_vissim_smoke\decisions" 120 60 1200 60 13
```

Parameters:

- simulation duration: 120 s
- urban input demand: 60 veh/h
- freeway input demand: 1200 veh/h
- control interval: 60 s
- random seed: 13

## Smoke test result

Vissim completed the 120-second simulation and the controller returned successfully at all decision points.

Controller calls:

| Sim second | Controller status | Adapter mode | Decision wall time |
|---:|---|---|---:|
| 1 | ok | fast-smoke | 2.930822 s |
| 60 | ok | fast-smoke | 2.903315 s |
| 120 | ok | fast-smoke | 3.808919 s |

Logged outputs:

- `evaluation/runs/stackelberg_vissim_smoke/state_120s.csv`
- `evaluation/runs/stackelberg_vissim_smoke/actions_120s.csv`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/state_000001.json`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/state_000060.json`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/state_000120.json`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/action_000001.json`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/action_000060.json`
- `evaluation/runs/stackelberg_vissim_smoke/decisions/action_000120.json`

Log summary:

| Metric | Value |
|---|---:|
| state CSV rows | 25 |
| action CSV rows | 81 |
| decision points | 1, 60, 120 |
| VSL action rows | 60 |
| signal action rows | 15 |
| ramp-meter action rows | 6 |
| VSL readback mismatches | 0 |
| controller status rows | ok: 25 |
| final total vehicles | 64 |
| final mean speed | 89.802580 km/h |
| final freeway mean speed | 105.229408 km/h |

Observed first-smoke control values:

- VSL: 100 km/h on all controlled segments and lanes.
- Ramp metering: 1500 veh/h for D/F ramp groups.
- Intersection greens: 56 s major / 56 s minor with 0 s offset.

These values are expected under the short low-demand smoke case: the controller bridge is being validated, not congestion response.

## Current limitations

The current bridge is functional but intentionally conservative:

- State is built from Vissim global/vehicle-level information, not yet detector-only measurements.
- Ramp metering currently compresses per-ramp Numerical-Sim rates into two Vissim ramp-meter groups, D and F.
- The smoke profile uses a very short MPC horizon to keep Vissim COM runtime stable.
- The controller is not yet tuned against high-demand hysteresis-loop scenarios.

## Recommended next step

Run a stronger demand scenario after detector installation is finalized:

1. Replace or cross-check global state with detector-derived state.
2. Raise demand around the D/F weaving/ramp areas to force a congestion/recovery loop.
3. Compare:
   - no control,
   - fixed-time signal/ramp baseline,
   - speed-only control,
   - full Stackelberg controller.
4. Track hysteresis using accumulation-flow or density-flow logs from the Vissim run.
