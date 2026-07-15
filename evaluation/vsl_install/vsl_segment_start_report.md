# Segment-Start VSL/DSD Layout Report

Date: 2026-06-25

## Outcome

Rebuilt the VSL Desired Speed Decision layout so that every DSD is located at a freeway control-segment start.

New staged network:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.inpx`
- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi_eval_vsl_segmented.layx`

The original user-edited network was not modified:

- `C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work\modi.inpx`
- verified `LastWriteTime`: `2026-06-25 오후 6:00:53`

## Why this layout

The previous VSL layout was station/bottleneck-oriented. It was useful for actuation smoke testing, but less clean for controller integration.

This layout uses:

- one control action per freeway segment
- one DSD per lane at the segment start
- direct `segment_id -> DSD list -> speed distribution` mapping

So the controller can output speed limits by `segment_id` without needing to reason about station names or offsets.

## Implemented files

- `scripts/install_eval_vsl_segment_starts.vbs`
- `scripts/run_com_segment_speed_controller.vbs`
- `evaluation/vsl_install/vsl_segment_start_manifest.csv`
- `evaluation/vsl_install/vsl_segment_mapping.json`
- `evaluation/eval_vsl_segmented_inventory/inventory.json`

## Segment definitions

Positions are in Vissim link-coordinate metres along the link direction.

| Segment ID | Direction | Link | Segment start m | Segment end m | DSD no |
|---|---|---:|---:|---:|---|
| EB_S0_W_ENTRY_TO_D_DIVERGE | EB | 33 | 1.000 | 499.032 | 1, 2 |
| EB_S1_D_DIVERGE_TO_D_MERGE | EB | 33 | 499.032 | 812.391 | 3, 4 |
| EB_S2_D_MERGE_TO_F_DIVERGE | EB | 33 | 812.391 | 1735.615 | 5, 6 |
| EB_S3_F_DIVERGE_TO_F_MERGE | EB | 33 | 1735.615 | 2029.150 | 7, 8 |
| EB_S4_F_MERGE_TO_E_EXIT | EB | 33 | 2029.150 | 2900.003 | 9, 10 |
| WB_S0_E_ENTRY_TO_F_DIVERGE | WB | 34 | 1.000 | 537.739 | 11, 12 |
| WB_S1_F_DIVERGE_TO_F_MERGE | WB | 34 | 537.739 | 1155.250 | 13, 14 |
| WB_S2_F_MERGE_TO_D_DIVERGE | WB | 34 | 1155.250 | 1743.460 | 15, 16 |
| WB_S3_D_DIVERGE_TO_D_MERGE | WB | 34 | 1743.460 | 2398.245 | 17, 18 |
| WB_S4_D_MERGE_TO_W_EXIT | WB | 34 | 2398.245 | 2900.003 | 19, 20 |

Each DSD controls vehicle classes:

- `10`: Car
- `20`: HGV
- `30`: Bus

by writing:

- `DesSpeedDistr(10)`
- `DesSpeedDistr(20)`
- `DesSpeedDistr(30)`

## Inventory after install

- desired speed decisions: 20
- freeway control segments: 10
- lane-level DSDs per segment: 2
- detectors: 120
- signal heads: 44
- signal controllers: 9

## Segment-based smoke controller

Runner:

- `scripts/run_com_segment_speed_controller.vbs`

Smoke run outputs:

- `evaluation/runs/com_segment_speed_smoke/state_180s.csv`
- `evaluation/runs/com_segment_speed_smoke/actions_180s.csv`
- `evaluation/runs/com_segment_speed_smoke/summary_180s.json`

Smoke profile:

| Time | Profile | Weave segment limit | Non-weave segment limit |
|---:|---|---:|---:|
| 0-59 s | FREE_FLOW | 120 km/h | 120 km/h |
| 60-119 s | MODERATE | 80 km/h | 100 km/h |
| 120-180 s | RESTRICTIVE | 60 km/h | 80 km/h |

Weave segments are:

- `EB_S1_D_DIVERGE_TO_D_MERGE`
- `EB_S3_F_DIVERGE_TO_F_MERGE`
- `WB_S1_F_DIVERGE_TO_F_MERGE`
- `WB_S3_D_DIVERGE_TO_D_MERGE`

## Smoke result

The 180-second segment-based VSL smoke test completed successfully.

Summary:

- state log rows: 37
- action log rows: 740
- segments controlled: 10
- DSDs controlled: 20
- commanded speeds: 60, 80, 100, 120 km/h
- readback mismatch count: 0
- final total vehicles: 90

The final action log confirms that segment-level commands were applied and read back correctly. Example at 180 s:

- D/F weave segments: 60 km/h
- non-weave segments: 80 km/h
- Car/HGV/Bus readback values match command values

## Controller integration note

The controller should treat `evaluation/vsl_install/vsl_segment_mapping.json` as the current VSL actuator map.

Expected controller action shape:

```json
{
  "EB_S0_W_ENTRY_TO_D_DIVERGE": 80,
  "EB_S1_D_DIVERGE_TO_D_MERGE": 60,
  "EB_S2_D_MERGE_TO_F_DIVERGE": 80,
  "EB_S3_F_DIVERGE_TO_F_MERGE": 60,
  "EB_S4_F_MERGE_TO_E_EXIT": 80,
  "WB_S0_E_ENTRY_TO_F_DIVERGE": 80,
  "WB_S1_F_DIVERGE_TO_F_MERGE": 60,
  "WB_S2_F_MERGE_TO_D_DIVERGE": 80,
  "WB_S3_D_DIVERGE_TO_D_MERGE": 60,
  "WB_S4_D_MERGE_TO_W_EXIT": 80
}
```

The runner maps each segment speed to both lane DSDs and all configured vehicle classes.
