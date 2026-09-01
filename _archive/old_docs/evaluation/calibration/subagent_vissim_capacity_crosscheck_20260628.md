# Subagent Vissim capacity cross-check — 2026-06-28

## Validation Report

### Overall Assessment: Needs revision — now corrected in calibration v2

The earlier claim that the calibrated off-ramp spillback capacity should be `240 veh` per model off-ramp, or `480 veh` for a D+F same-direction freeway agent, was not supported by the actual Vissim geometry.

After three independent reviews:

- Vissim physical inventory review rejected `240 / 480` as too high.
- Adapter review confirmed the patch was wired correctly, so the issue was the value, not the runtime path.
- PFO/spillback review confirmed that the stock `480 per off-ramp / 960 per same-direction agent` was a model artifact, but that a single `240` replacement was still too coarse.

The active calibration file has been revised:

- `evaluation/calibration/vissim_network_calibration_v2_20260628.json`

## Corrected physical capacity

The revised v2 calibration now uses direction-specific connector-plus-stem-to-signal lane-metre storage estimates:

| model off-ramp | Vissim path | central cap |
| --- | --- | ---: |
| `OR_D_E` | connector `10067` + link `26` lane 2 to signal | 154 veh |
| `OR_D_W` | connector `10071` + link `26` lane 1 to signal | 95 veh |
| `OR_F_E` | connector `10072` + link `32` lane 2 to signal | 144 veh |
| `OR_F_W` | connector `10069` + link `32` lane 1 to signal | 101 veh |

Same-direction freeway-agent capacities are therefore:

| freeway direction | old stock model | first v2 provisional | revised geometry v2 |
| --- | ---: | ---: | ---: |
| `FW_E`: `OR_D_E + OR_F_E` | 960 veh | 480 veh | 298 veh |
| `FW_W`: `OR_D_W + OR_F_W` | 960 veh | 480 veh | 196 veh |

## Methodology Review

The corrected estimate uses:

```text
capacity = (one-lane freeway-to-off-ramp connector length
            + same-lane downstream stem length to the ramp signal head)
           / jam spacing
```

Central jam spacing:

```text
weighted vehicle length ≈ 4.486 m
Wiedemann 74 ax / standstill allowance ≈ 2.0 m
central jam spacing ≈ 6.49 m/veh
```

The previous `240 veh per OR` used a model abstraction:

```text
120 veh storage + 120 veh shared downstream approach allowance
```

That was better than the stock `120 + 3×120 = 480`, but it was still not measured from the Vissim network.

## Issues Found

1. Severity: High — old `480` same-direction cap was too high.

   Evidence: actual same-direction geometry supports roughly `298 veh` eastbound and `196 veh` westbound at the central jam-spacing assumption.

2. Severity: High — `240 veh per model off-ramp` was also too high.

   Evidence: all four individual off-ramp central estimates are below 240; even tight-spacing upper estimates remain below 240.

3. Severity: Medium — Vissim physical storage is direction-specific, but the old model treated each model OR uniformly.

   Evidence: D/F eastbound off-ramp connectors are much longer than westbound connectors. A single value cannot represent both directions.

4. Severity: Medium — PFO off-ramp capacity diagnostics are freeway-link scoped.

   Evidence: PFO diagnostics now report `298` for all `F_E*` agents and `196` for all `F_W*` agents. That is expected under the current PFO implementation, but the labels can look segment-local when they are really same-direction sums.

5. Severity: Medium — F-ramp metering fit is still marked invalid but can be consumed when metered-F tuning is enabled.

   This is a separate operational calibration caveat, not a physical-storage issue.

## Calculation Spot-Checks

- Adapter patch path: verified. PFO diagnostics use patched capacity.
- Revised calibration JSON parse: verified.
- Adapter syntax: verified.
- PFO single-state run with revised geometry cap: verified.

Validation output:

- `evaluation/runs/calibration_v2_geometry_capacity_pfo_check/action_000300.json`

Key metadata:

| metric | value |
| --- | ---: |
| `calibration_offramp_capacity_patch_installed` | 1 |
| min per-OR capacity | 95 veh |
| max per-OR capacity | 154 veh |
| all-four OR total | 494 veh |
| `FW_E` agent off-ramp cap | 298 veh |
| `FW_W` agent off-ramp cap | 196 veh |

## Required Caveats

- These capacities are still storage-threshold estimates, not fully dynamic spillback calibration.
- Next calibration should add service-aware off-ramp spillback in the freeway-agent candidate check:

```text
violation = max(0, occupancy + predicted_inflow - predicted_service - capacity)
```

- F-ramp metering calibration remains suspect until the F connector/route bottleneck is resolved or separately fitted.
