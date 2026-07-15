# Vissim network calibration v2 report — 2026-06-28

> Update after subagent cross-check: the first v2 physical off-ramp capacity
> values (`240 veh` per model off-ramp / `480 veh` same-direction agent) were
> too high for the actual Vissim geometry. The active calibration JSON has been
> revised to direction-specific values: `OR_D_E=154`, `OR_D_W=95`,
> `OR_F_E=144`, `OR_F_W=101`; same-direction agent caps are now `FW_E=298`
> and `FW_W=196`. See
> `evaluation/calibration/subagent_vissim_capacity_crosscheck_20260628.md`.

## Scope

This pass covers calibration items 1–4 before controller tuning:

1. Vissim physical inventory calibration
2. Vissim operational calibration
3. State observation calibration
4. Prediction / propagation audit calibration

Controller weight tuning is intentionally left for the next pass.

## Files

- Calibration file: `evaluation/calibration/vissim_network_calibration_v2_20260628.json`
- Adapter: `evaluation/controllers/vissim_stackelberg_adapter.py`
- Validation outputs:
  - `evaluation/runs/calibration_v2_prediction_pair/action_000001.json`
  - `evaluation/runs/calibration_v2_prediction_pair/action_000060.json`
  - `evaluation/runs/calibration_v2_pfo_spillback_check/action_000300.json`

## 1. Physical inventory calibration

The previous off-ramp spillback capacity was not a direct Vissim physical storage value. Numerical-Sim computed:

- off-ramp storage = 120 veh
- downstream turning movement storage = 3 × 120 veh
- per off-ramp combined capacity = 480 veh
- two off-ramps seen by a freeway agent = 960 veh

For the current Vissim network, the downstream approach space is shared. Summing all three turning movements double-counts the available receiving space.

Calibration v2 changes the runtime off-ramp spillback capacity to:

| item | old | v2 |
| --- | ---: | ---: |
| per off-ramp combined capacity | 480 veh | 240 veh |
| D+F same-direction freeway-agent capacity | 960 veh | 480 veh |

The adapter applies this as a runtime patch only; the Desktop Numerical-Sim source files are not edited.

Validation from `action_000300.json`:

| metric | value |
| --- | ---: |
| patch installed | 1 |
| per-off-ramp min capacity | 240 veh |
| all four off-ramp capacity sum | 960 veh |
| freeway-agent D+F combined capacity | 480 veh |

## 2. Operational calibration

The v2 calibration carries forward the 2026-06-26 operational fits:

| parameter | v2 value |
| --- | ---: |
| free-flow speed | 123.825 km/h |
| freeway capacity | 4574.818 veh/h |
| critical density | 20.401 veh/km/lane |
| signal lost time | 6.0 sec |
| initial signal saturation flow | 1800 veh/h/approach |
| protected accumulation threshold `N_P_crit` | 390 veh |

Ramp metering mapping is also carried forward. D-ramp is usable as an initial metering fit. F-ramp is still marked invalid for physical metering calibration because it remains discharge-limited by route/lane/connector behavior in the calibration runs.

## 3. Observation calibration

Observation mode remains:

- `detector_local_v2_storage_split`

But the split fractions are now read from the v2 calibration JSON instead of being only hardcoded in the adapter.

| link class | queue fraction | storage fraction |
| --- | ---: | ---: |
| boundary links | 1.00 | 0.00 |
| internal urban links | 0.65 | 0.35 |
| off-ramp storage links | 0.50 | 0.50 |

Validation from `action_000060.json`:

| metric | value |
| --- | ---: |
| observation mode | `detector_local_v2_storage_split` |
| internal storage fraction | 0.35 |
| off-ramp storage fraction | 0.50 |

Validation from high off-ramp state `action_000300.json`:

| metric | value |
| --- | ---: |
| local off-ramp storage occupancy | 60.5 veh |
| terminal off-ramp storage in PFO response | 9.235 veh |
| distributed off-ramp spillback violation | 0.0 veh |

Spillback violation is still zero, but this is now because the state does not exceed the calibrated 480 veh same-direction threshold, not because the threshold is accidentally 960 veh.

## 4. Prediction / propagation audit calibration

The existing one-step diagnostics showed freeway retention bias: the Numerical-Sim rollout retained too many freeway vehicles relative to Vissim.

Calibration v2 stores an audit-only freeway scale:

- freeway observed / predicted mean = 0.6506866

Important: this does not silently scale controller dynamics. The adapter stores both:

- raw `prediction.state_summary`
- audit-calibrated `prediction.calibrated_state_summary`

`prediction_error` now compares against the calibrated summary when available.

Validation using `state_000001 -> state_000060`:

| freeway total | value |
| --- | ---: |
| raw predicted | 103.616 veh |
| calibrated predicted | 67.422 veh |
| observed | 60.558 veh |
| raw error | -43.058 veh |
| calibrated error | -6.863 veh |

The calibrated one-step audit is therefore much closer, but true METANET propagation dynamics are not yet changed. That should be handled deliberately after checking whether the remaining bias is from downstream sink/outflow, off-ramp split, segment length/count mapping, or demand injection.

## Validation commands run

- `python -m py_compile evaluation/controllers/vissim_stackelberg_adapter.py scripts/diagnose_prediction_error_components.py`
- `python -m json.tool evaluation/calibration/vissim_network_calibration_v2_20260628.json`
- Adapter no-control prediction pair:
  - `state_000001 -> action_000001`
  - `state_000060 -> action_000060`
- Adapter PFO high off-ramp state:
  - `state_000300 -> action_000300`

All checks completed successfully.

## Current interpretation

Items 1–4 are now wired into the evaluation stack:

- physical off-ramp capacity is no longer inflated to 960 veh at the freeway-agent level;
- operational calibration values are centralized in v2;
- detector-local observation split is calibration-driven;
- one-step prediction audit now records raw and calibrated summaries.

Next step is item 5: controller tuning. The first useful controller-tuning question is now not “why is off-ramp capacity 960?” but “under calibrated 480 veh D+F storage threshold, what demand state actually makes VSL/RM beneficial before spillback?”
