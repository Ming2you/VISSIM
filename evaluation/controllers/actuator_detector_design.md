# Detector, ramp metering, and VSL implementation plan

This design assumes the user-edited geometry in
`C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx` is frozen.
All added objects should be written to a separate evaluation copy, e.g.
`modi_eval_control.inpx`.

## 1. Detector expansion

Use three Vissim object families because they serve different purposes.

| Purpose | Vissim object | Use in this project |
|---|---|---|
| Evaluation / measured flow-speed | `DataCollectionPoint` | per-lane flow/speed on freeway, arterials, ramps |
| Queue measurement | `QueueCounter` | approach queues, ramp queues, spillback checks |
| Signal/controller trigger | `Detector` | presence/occupancy/pulse inputs for actuated signals, ramp metering, VSL logic |

Initial detector layers:

1. Keep the existing 64 data collection points and 23 queue counters.
2. Add ramp data collection points on ramp links 25, 26, 31, 32.
3. Add freeway mainline DCP/detector pairs upstream and downstream of D/F merge-diverge zones.
4. Add stop-line presence detectors on all controlled approaches at A/B/C/D/F.
5. Add advance detectors upstream of controlled approaches for phase actuation/arrival estimation.
6. Add ramp queue detectors on links 25 and 31 for metering queue override.

## 2. Ramp metering

Ramp metering should be modeled as a signal head on the on-ramp, not as a route decision.

Current ramp links from mapping:

- D on-ramp toward freeway: link 25, connectors to freeway 10066 and 10068
- D off-ramp from freeway: link 26, connectors from freeway 10067 and 10071
- F on-ramp toward freeway: link 31, connectors to freeway 10070 and 10073
- F off-ramp from freeway: link 32, connectors from freeway 10069 and 10072

Implementation:

1. Place ramp meter signal heads on link 25 and link 31, near the downstream end before the freeway connector split.
2. Start with one shared metering signal state per ramp. If lane-by-lane metering is needed later, add one signal head per ramp lane.
3. Add a short cycle controller for each ramp meter:
   - green: release one vehicle or short platoon
   - red: hold ramp vehicles
   - minimum red/green bounds to avoid unrealistic flickering
4. Add detector inputs:
   - ramp queue detector upstream on link 25/31
   - passage detector immediately downstream of meter stop line
   - mainline occupancy/speed detectors upstream of merge
5. Control rule v0:
   - high mainline occupancy or low mainline speed → lower metering rate
   - long ramp queue/spillback risk → queue override, temporarily increase metering rate
   - low mainline occupancy → relax metering

For the first controller comparison, ramp metering can be included as a controllable action:

```text
action.ramp_meter.D = {cycle_sec, green_sec}
action.ramp_meter.F = {cycle_sec, green_sec}
```

## 3. Variable speed limit (VSL)

VSL should be modeled with Vissim `DesSpeedDecision` objects on freeway mainline links.

Current freeway links:

- EB mainline: link 33
- WB mainline: link 34

Implementation:

1. Create desired speed distributions for discrete VSL states, e.g. 40, 50, 60, 70, 80, 90, 100 km/h.
2. Place `DesSpeedDecision` objects on links 33 and 34 at VSL gantry locations.
3. Use zones around D/F merge-diverge areas:
   - upstream of D interchange
   - between D and F
   - downstream of F interchange
4. At each control interval, assign the desired speed distribution for each VSL decision.
5. Apply smoothing:
   - no abrupt speed jumps larger than one step per control interval
   - downstream speed should not be much lower than upstream without a transition zone

For controller action:

```text
action.vsl.EB = {zone_D_upstream: 80, zone_mid: 70, zone_F_downstream: 90}
action.vsl.WB = {zone_F_upstream: 80, zone_mid: 70, zone_D_downstream: 90}
```

## 4. Controller staging

Recommended order:

1. Add all detector/DCP/QC objects to evaluation copy.
2. Add route decisions so demand follows intended OD paths.
3. Add signal heads and fixed-time signal controllers at A/B/C/D/F.
4. Add ramp meter signal heads on D/F on-ramps.
5. Add VSL desired speed decisions on freeway links 33/34.
6. Run fixed-time + no-ramp-meter + no-VSL baseline.
7. Enable ramp metering only.
8. Enable VSL only.
9. Enable combined controller.

This sequence makes the ablation tests clean:

```text
baseline
baseline + ramp metering
baseline + VSL
baseline + ramp metering + VSL
target controller
```
