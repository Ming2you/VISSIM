# 8-seg sweet-cell VISSIM re-baseline (2026-07-14)

## Demand mapping (user-approved: total-preserving time-mean)

The numeric model (`src/models/demand.py`) generates, for scenario scale `s`:

- per boundary-in gate k (7 gates): `500 * s * peak(t) * (1 + 0.10*k)` vph
- per freeway link j (2 links):     `1650 * s * peak(t) * (1 + 0.05*j)` vph
- `peak(t) = 1 + 0.22*sin(pi * t/T)` — time mean over [0,T] = `1 + 0.44/pi = 1.140056`

The VISSIM runner supports one constant volume per input class, so we map to
uniform constant volumes that preserve the model's TOTAL inflow:

- urban VI volume  = `500 * s * 1.140056 * mean_k(1+0.10k) = 500*s*1.140056*1.3  = 741.04*s`
- freeway VI volume = `1650 * s * 1.140056 * mean_j(1+0.05j) = 1650*s*1.140056*1.025 = 1928.19*s`

| cell      | scale | urban VI vph | freeway VI vph |
|-----------|-------|--------------|----------------|
| sweet_128 | 1.28  | 949          | 2468           |
| sweet_155 | 1.55  | 1149         | 2989           |
| sweet_190 | 1.90  | 1408         | 3664           |

Known deviations from the numeric model (accepted):
- constant in time (no sine peak shape, no per-gate/per-link stagger)
- ramp demand is NOT set independently: VISSIM routes ~10.5% of each urban
  origin onto the directional on-ramps (route_manifest RelFlow), while the
  model uses `560*s` — this is the standing calibration reality.

## _w (warmup/pulse) cells — 2026-07-14 addendum

The mainline `_w` cells (sweet_155_w / sweet_190_w etc., T=10800) use the pulse
trapezoid: base 0.5x for [0,3600), 300 s ramp-up, 3600 s plateau at full scale,
300 s ramp-down, base 0.5x tail; controller forced to no-control during warmup
(WARMUP_NC). In pulse mode the numeric model DISABLES the sine peak (peak=1),
so the time-mean factor 1.140056 does NOT apply. Plateau (full-scale) volumes:

- urban VI  = `500 * s * 1.3   = 650*s`
- freeway VI = `1650 * s * 1.025 = 1691.25*s`

| cell        | scale | urban VI vph | freeway VI vph |
|-------------|-------|--------------|----------------|
| sweet_155_w | 1.55  | 1008         | 2621           |
| sweet_190_w | 1.90  | 1235         | 3213           |

VISSIM runner: `run_stackelberg_vissim_controller_8seg.vbs` arg 14 pulse spec
`0.5:3600:300:3600:300`, simPeriod 10800; demand updated every 60 s along the
trapezoid; decisions before 3600 s forced to no-control. NOTE (PowerShell): the
empty tuning-json arg must be passed as `'""'` — a bare `""` is dropped by
PowerShell and shifts the arg positions.

## Run config

- network: `Network_Vissim_Work/modi_eval_vsl_8seg.inpx` (8-seg plant)
- runner: `scripts/run_stackelberg_vissim_controller_8seg.vbs`
- calibration: `evaluation/calibration/vissim_network_calibration_v2_8seg_20260714.json`
- controller: `no-control`, T=7200 s, control interval 60 s, seed 13, profile `sym`
- cells run serially (single Vissim COM license)
