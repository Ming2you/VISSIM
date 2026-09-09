# VISSIM controller runtime

`vissim_stackelberg_adapter.py` is the only active adapter. The canonical
`scripts/run_real_world_stackelberg_controller.vbs` invokes it at each decision,
validates the returned action CSV, writes the physical controls, and records COM
readback. VSL, eight ramp meters, and the selected urban signal groups are active
control surfaces in the Ver2 evaluation network.

Launch actual runs through
`scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`. Use a
flattened configuration and record its provenance. A new run must not change
the adapter, its imported modules, selected configuration, or VBS while another
run is active. Startup timeout defaults to 300 seconds without positive
simulation progress. `-NoGlobalKill` keeps termination scoped to the launched
processes.

| Component | Responsibility |
|---|---|
| `runtime_setup.py` | Shared configuration/projection order; worker hook installation |
| `observation_projection.py`, `projection_support.py` | Physical stock assignment without duplicated ramp/urban observations |
| `physical_movement_routes.py`, `area_dynamic_routes.py` | Evidence-backed physical routes and explicit unresolved-route failures |
| `shared_approach.py`, `sc2001_corridor.py` | Finite shared storage and accepted transfers through the SC2001 corridor |
| `freeway_fd.py`, `freeway_local_state.py`, `link_predictor.py` | Consistent freeway and local prediction physics |
| `control_area_objective.py`, `area_runtime.py`, `area_freeway_accounting.py`, `urban_flow_accounting.py` | Explicit control-area residence and boundary-flow accounting |
| `signal_actuation_contract.py` | Feasible candidate greens and the same signal clock used by the writer |
| `signal_group_plan.py`, `plant_cycle.py`, `action_csv_schema.py` | Selected SG plan, physical cycle, and serialization contracts |
| `offset_promotion.py` | Declared offset writer modes and existing production evidence gates |

The new physical and area paths are explicitly configured; absence of their
flags retains the legacy path. The control area is the union of the controlled
freeway and urban protected network. TTT counts residence inside that union;
TTD counts outward crossings, including crossings into noncontrol roads.
Internal freeway/urban transfers do not count as exits. The objective coefficient
is explicit in seconds per vehicle; no default reward is selected.

The `experiment` offset writer requires both the configuration declaration and
`RW_OFFSET_WRITER=experiment`, together with the physical signal contract. It is
a simulation experiment, not production promotion. Normal `intent_only`, forced
`test_only`, and the production evidence gates retain separate meanings.

Review configurations and measurement evidence are under `diagnostics/` and
`docs/REVIEW_20260910_control_diagnosis.md`. Passing accounting and actuation
checks does not establish prediction fidelity or traffic improvement. In
particular, the F interchange branch aggregation and optimistic E8 recovery
remain explicit review issues.

The old `GLOBAL_NOOP` documentation described the initial network smoke test.
It does not describe this runtime. Historical adapter storage and recovery are
listed in `_superseded_20260827/MANIFEST_20260827.json`.
