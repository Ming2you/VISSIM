# GetAll-free calibration logging note

Date: 2026-06-26

The original calibration probe scanned all live vehicles via `Vissim.Net.Vehicles.GetAll`
and then called per-vehicle `AttValue("Link")`, `AttValue("Pos")`, `AttValue("Speed")`,
and `AttValue("No")`. This worked, but it made long calibration sweeps very slow because
each simulation second created many COM round-trips.

The probe now uses vectorized Vissim COM reads:

- `Vissim.Net.Vehicles.GetMultiAttValues("Lane")`
- `Vissim.Net.Vehicles.GetMultiAttValues("Pos")`
- `Vissim.Net.Vehicles.GetMultiAttValues("Speed")`

`Link` is not available as a direct multi-attribute on `Vehicles` in the tested Vissim 2020
COM interface, so the link number is parsed from the `Lane` attribute. The first column of
the returned array is used as the vehicle key for crossing-count continuity.

Smoke result:

- Script: `scripts/run_vissim_calibration_probe.vbs`
- Network: `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx`
- Run: 120 simulation seconds
- Wall time: about 37 seconds
- Output folder: `evaluation\runs\calibration_probe_vector_smoke`
- Generated: `state.csv`, `segments.csv`, `ramps.csv`, `signal_discharge.csv`, `urban_production.csv`

Recommended split:

1. Use this GetAll-free/vectorized COM probe for calibration cases that still need scripted
   fixed-time signals or ramp-meter signal states during the run.
2. Use Vissim evaluation outputs for later long sweeps where signals/actuators can be static
   or where detector/queue-counter outputs are sufficient after the simulation finishes.
3. Keep real-time state collection separate for closed-loop MPC/controller evaluation.
