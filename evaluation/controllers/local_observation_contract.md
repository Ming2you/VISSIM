# Vissim local observation contract

This controller mode is for the detector/local-information evaluation phase.

## What changed

- The Vissim runner now writes `local_observation.link_counts` into every decision state JSON.
- The Stackelberg adapter prefers `local_observation` over aggregate fields such as `urban_vehicles`, `boundary_vehicles`, and `ramp_counts`.
- When local observation is present, the adapter switches the Numerical-Sim follower mode to `distributed`.
- `evaluation/detector_install/detector_local_mapping.json` defines which local links, movements, and ramps each follower may observe.
- A runtime guard masks the `TrafficState` immediately before each distributed follower solve, so an urban/freeway agent cannot read non-owned queues from the shared state object.

## Information rule

- The leader may use global state.
- Followers should receive only their mapped local observation:
  - urban agents: local approach links and movements at their signal;
  - freeway agents: their freeway link/segment plus directly coupled ramps/off-ramps;
  - ramp queue state: only from the ramp local-zone links 25 and 31.

The Vissim implementation may still scan all vehicles internally for speed. That scan is treated as a data-acquisition detail only: the adapter masks it through the detector/local mapping before follower state is built.

## Validation

Run:

```powershell
python scripts\validate_local_observation_contract.py
```

The synthetic leak test intentionally sets global `urban_vehicles=9999` and `boundary_vehicles=8888`, while only D-side local links contain vehicles. The expected result is:

- D ramp queue is positive;
- F ramp queue is zero;
- U_D movement queue is positive;
- U_F movement queue is zero;
- total movement queue equals the local D-side count, not the global aggregate count.

Adapter CLI smoke after the lightweight local-distributed profile:

- state file: `evaluation/runs/local_observation_contract/state_cli.json`
- action file: `evaluation/runs/local_observation_contract/action_cli.json`
- observed metadata: `observation_mode=detector_local_v1`, `follower_solver_mode=distributed`, `local_observation_runtime_guard=1.0`
- decision wall time: about 3 seconds on the synthetic local state
