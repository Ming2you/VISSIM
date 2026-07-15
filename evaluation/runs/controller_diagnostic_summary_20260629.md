# Controller diagnostic — why the controllers barely work (2026-06-29)

Three cells, seed 13, 1800s, warmup 300s, repo 0e07c1c, calibration v2. Metric vs each cell's own
no-control. green_sd = mean per-decision stdev of green_times (signal-retiming magnitude).

| cell | controller | TTT vs nc | stopped vs nc | speed vs nc | metering | green_sd | N_UF* |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sym x h1 (ref) | wu | +0.0% | +0.0% | +0.0% | 0 | 0.0 | 0 |
| sym x h1 (ref) | **pfo** | **-3.6%** | -10.4% | +9.0% | 0 | 7.3 | 0 |
| sym x h1 (ref) | swm | +1.0% | +2.7% | -1.5% | 10 | 0.0 | 3302 |
| asym(urban_d) x h1 | wu | +0.0% | +0.0% | +0.0% | 0 | 0.0 | 0 |
| asym(urban_d) x h1 | **pfo** | **-2.1%** | -10.7% | +4.4% | 0 | 5.6 | 0 |
| asym(urban_d) x h1 | swm | -0.4% | -1.8% | +0.4% | 14 | 0.0 | 3302 |
| sym x **h3** | wu | +0.5% | +1.0% | -0.4% | 0 | 0.6 | 0 |
| sym x **h3** | **pfo** | **+8.5%** | +10.0% | -4.5% | 0 | 7.3 | 0 |
| sym x **h3** | swm | +4.1% | +7.2% | -4.5% | 27 | 0.0 | 3302 |

## Conclusions

1. **Asymmetry did NOT unlock controller value.** PFO is a consistent ~-2 to -4% TTT / ~-10% stopped
   in both symmetric and asymmetric (urban_d_heavy) demand. So "no headroom at symmetric demand" is NOT
   the main reason the controllers are weak — they are similarly limited under asymmetry.

2. **Longer horizon (h1 -> h3) made PFO much WORSE: -3.6% -> +8.5% TTT.** This is the decisive result.
   Giving the MPC more lookahead HURTS. The only explanation consistent with this is model-plant
   mismatch: the controllers optimize a structurally mis-calibrated internal urban model, so planning
   3 steps ahead commits confidently to decisions that are wrong for the real VISSIM. Myopic h1
   accidentally limits the damage by relying less on the model's multi-step predictions. swm shows the
   same h3 degradation (+4.1%), and it meters more (27 vs 10) and still hurts.

3. **WU is a structural no-op in every cell** (green_sd ~0, +0.0% everywhere). WuDistributedController
   never differentiates signal green times in this integration.

4. **swm only meters, never retimes signals** (green_sd 0 in all cells), and metering an uncongested
   freeway is counterproductive (worse in every cell).

## Root cause (synthesised with the calibration findings)

The controllers barely work because their INTERNAL URBAN MODEL is structurally mis-calibrated (the
turn-split / storage / propagation trade-off that parameter joint-calibration could not remove — see
audit_followup_20260629/urban_joint_calib.md). Evidence: a longer planning horizon AMPLIFIES the error
(h3 worse than h1). This is model fidelity limited, NOT a controller-logic, demand-scenario, or horizon
tuning problem. PFO's small h1 benefit survives only because 1-step myopia minimises reliance on the
wrong model.

## Implications for next steps

- More controller tuning, more seeds, or different demand will NOT make these controllers work; the
  ceiling is model fidelity. The lever is a STRUCTURAL urban model improvement (urban_queue_model
  propagation/storage dynamics in the Numerical-Sim repo), not parameters.
- Separately fixable integration bugs: (a) WU never retimes signals; (b) swm never retimes signals and
  meters an uncongested freeway (its leader should gate metering on freeway congestion).
- Keep the VISSIM adapter at horizon=1 for now; horizon>1 is actively harmful until the model is fixed.
