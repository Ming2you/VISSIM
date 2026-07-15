# Global-state controller connection

The first Vissim evaluation phase is detector-independent. `scripts/run_global_state_smoke.vbs`
loads the current user-edited network, sets low demand in memory, advances the simulation, and
logs a controller-ready global state vector every control interval.

Current action mode is `GLOBAL_NOOP` because the network has no signal controllers or signal
heads yet. After signal objects are added to an evaluation copy of the INPX, this same interval
can be used to call a fixed-time controller first, then the target controller.

State columns currently emitted:

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

Next actuation layer:

1. Add/verify static route decisions so low and nominal demand traverse intended OD paths.
2. Add signal controllers, signal groups, and signal heads at A/B/C/D/F in an evaluation INPX.
3. Replace `GLOBAL_NOOP` with fixed-time signal updates.
4. Replace fixed-time updates with the target controller.

Additional VSL/speed-control layer now exists:

- `scripts/install_eval_vsl.vbs` installs Desired Speed Decisions on freeway links 33/34.
- `scripts/run_com_speed_controller.vbs` performs runtime COM VSL actuation by writing
  `DesSpeedDistr(10/20/30)` for Car/HGV/Bus vehicle classes.
- Smoke-test report: `evaluation/vsl_install/vsl_controller_report.md`.

Current controller-facing VSL layout is the segment-start version:

- staged network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx`
- installer: `scripts/install_eval_vsl_segment_starts.vbs`
- runner: `scripts/run_com_segment_speed_controller.vbs`
- actuator map: `evaluation/vsl_install/vsl_segment_mapping.json`
- report: `evaluation/vsl_install/vsl_segment_start_report.md`
