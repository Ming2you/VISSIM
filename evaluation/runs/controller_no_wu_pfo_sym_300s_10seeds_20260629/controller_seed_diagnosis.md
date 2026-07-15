# Controller seed-batch diagnosis

- Source: `evaluation\runs\controller_no_wu_pfo_sym_300s_10seeds_20260629`
- Baseline: seed-paired no-control.
- Negative total/stopped percentage means improvement vs no-control.

## Paired summary

| controller | cases | total % mean | total improved | stopped % mean | stopped improved | speed % mean | pred err % mean | wall s | signal split | signal offset | VSL step | ramp step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `no-control` | 10 | 0.000% | 0/10 | 0.000% | 0/10 | 0.000% | 0.000% | 0.359 | 0.000 | 0.000 | 0.000 | 0.000 |
| `pfo` | 10 | -0.274% | 8/10 | -3.764% | 10/10 | 0.775% | -42.342% | 31.972 | 5.976 | 12.750 | 0.000 | 0.000 |
| `wu` | 10 | 0.034% | 2/10 | 0.279% | 2/10 | -0.127% | -1.667% | 1.706 | 1.487 | 0.000 | 0.000 | 0.000 |

## Prioritized causes / next fixes

1. Wu is effectively inactive under this setup: mean total veh-h 0.034% vs no-control, stopped veh-h 0.279%, VSL step 0.000 kph, ramp step 0.000 s, signal offset 0.000 s. It solves without fallback, but the selected actions barely change the plant.
2. PFO benefits are limited to signal timing: stopped veh-h improves -3.764% on average, but total veh-h only -0.274%. VSL and ramp steps are both 0.000/0.000, while signal split/offset move 5.976 s / 12.750 s.
3. PFO is computationally heavy for this loop: mean decision wall time 31.972 s, max 54.315 s. It fits a 60 s control interval, but it is expensive for larger horizons, more seeds, or parallel VISSIM.
4. METANET audit calibration is not stable enough to promote blindly. The latest Bayesian patch is recorded at `evaluation\calibration\prediction_audit_bayes_update_no_wu_pfo_10seed_20260629.md`; use it as a candidate and validate on held-out demand/seed before replacing active dynamics.
5. This symmetric-high demand mainly exercises signal timing. Because VSL and ramp metering never activate, the next diagnostic should use freeway-heavy and ramp-biased scenarios after the audit calibration is held out.
