# Direct10484 response: native benefit, model misses congestion/recovery

2026-09-20. The direct10484 diagnostic is complete; **gain calibration remains NOT_QUALIFIED**. No production/default model was changed. This is one inspected seed and a fixed-command diagnostic, not an MPC/full-GNE or whole-Omega improvement result.

## Frozen setup and completed execution

- `direct10484_s23_v1`: original user geometry/demand, seed23, native run to3000s, evaluation2400–2850s. Input1101 reductions are separate preserved experiments and are not used here.
- Only10484/SC9108 changes: native OFF until2400, then green8/6/4 at2400/2550/2700, holding4 through3000. Existing10s RED/GREEN clock and command-after-frame convention are preserved. Head position377.11076m on connector10484. All other meters, VSL and urban signals retain baseline conditions.
- The prepared INPX is byte-identical to the reused NC prepared network. `protocol.json` and `frozen_predictions.json` were saved before execution, with source/model pins. No fit uses this outcome.
- The existing `fast_nc_run.ps1` completed in193.656s including loading and native checks; its owned process exited normally. No live vehicle COM scans or concurrent heavy analysis were used.
- LDP/readback:120 applied events and600 controlled SG samples passed. All8,646,345 original FZP rows through2400s matched exactly, as did untargeted native signals. `fixed_validation_initial.json` preserves the initial run validation before paired verification.
- `validation_summary.json`, `review.json`, `boundary_balance.json`, extraction manifests and raw FZP/LDP/LSA/ERR are retained. Evaluation-component unexplained transitions/removals are zero and stock/flow/residence identities close. Raw ERR notices elsewhere remain recorded; the whole network is not claimed error-free.

##450s response

TTT is the physical component residence of FW_E mainline plus its four on-ramp and four off-ramp connectors. Units below are vehicle-hours; negative delta is improvement.

| Component delta | Native | Established model | Open-outlet candidate |
|---|---:|---:|---:|
|Mainline|−0.878889|−0.185878|−0.176112|
|On-ramp connectors|+0.424444|+0.193233|+0.178639|
|Off-ramp connectors|−0.004444|+0.001629|+0.001139|
|Total|**−0.458889**|**+0.008984**|**+0.003666**|

Baseline component TTT is103.61778veh h; the native benefit is about0.443%. It is a real same-seed contrast, but one small component improvement does not establish robust gains across seeds or a10% controller benefit.

Actual10484 merges decrease97→86 (−11), with connector arrivals91→90 and terminal stock8→18. Its own residence increases0.409167veh h. The model predicts about8 fewer merges and only0.18–0.19veh h additional residence. The adjacent10490 contributes+0.015278veh h, while the other two on-ramp connectors are unchanged.

|Interval|Green|Native10484 head passages NC→RM|Merges NC→RM|
|---|---:|---:|---:|
|2400–2550|8|31→31|35→35|
|2550–2700|6|37→30|33→28|
|2700–2850|4|28→22|29→23|

Unchanged150s counts in the8s phase do not prove identical timing. Nevertheless, total component benefit is only−0.00750veh h in that first interval and−0.00250 in the second;−0.448889 occurs in the third. Most useful response appears after the restriction and its effects have propagated.

## What the model misses

The last150s10484 merge-cell14 native vehicle-weighted speed is42.16km/h under NC and64.24 under RM. Its mean stock falls53.88→37.95. The open-outlet model instead predicts80.18→81.96km/h and32.03→30.97 vehicles (model speed/stock summaries use its30s output frames). It already predicts a much milder NC bottleneck and therefore barely changes with control.

This is not explained by lower modeled upstream demand. In2550–2700 the actual cell14 upstream arrivals are202 and the model predicts201.38, while modeled outgoing flow232.30 exceeds actual207. In2700–2850 the model even overpredicts upstream arrivals203.72 versus actual172 and still misses the congested state. Compare receiving/transport/speed response before increasing demand or fitting another global source multiplier.

`spatial_response.json` shows the intervention response starting near the physical merge. Initial-cohort vehicle19383 first differs in cell14 at2421s and reaches cells15/16/17/18/19/20 at2432/2450/2470/2487/2503/2518. Initial-cohort vehicle18281 first differs upstream in cell13 at2472. These are matched trajectories, **not** a calibrated shock-wave speed. Late numeric IDs allocated after the intervention can refer to different generated vehicles; only the initial-cohort matches in `validation_summary.json` are used as identity evidence.

Changes are spatially mixed:450s delta residence in cells14/15/16/17/18/19/20 is−1.0253/+0.4231/−0.4611/+0.3578/+0.2236/−0.0264/−0.2592veh h. Averaging these into a single capacity bonus would obscure downstream moving congestion.

The exact external-interface time-moment identity gives:

- Mainline input contribution0, with identical673 admissions and timing.
- Mainline terminal contribution−0.449167veh h,15 additional terminal exits.
- All other component interfaces together−0.009722veh h.

Thus this contrast is not a benefit from changing mainline source timing or deleting component vehicles. It remains a component result: off-ramp departures enter urban roads and are not whole-Omega exits.

## Arrival timing does not solve it

`arrival_diagnostic` retains the same physical laws and supplies only the actual future10484 arrival sequence, as an explicitly noncausal identification test. Predicted total delta changes+0.003666→−0.028481; using the same NC future arrival sequence for both arms gives+0.012353. Its10484 waiting delta remains too small. Both original causal predictions replay exactly and conservation/west invariants pass. Do not adopt these future observations as operational inputs or claim that arrival forecasting alone fixes the model.

## Next bounded calibration step

The preceding speed refits and downstream lane expansion are documented in `OPEN_OUTLET_CAUSAL_CHECKS.md` and rejected. The new direct response does not justify another blind global coefficient sweep.

1. Audit consumed cell14 FD/relaxation/anticipation/merge terms against the observed NC local speed and accepted flows, focusing on the transition from clearing to growing queue. Distinguish the modeled source/receiving boundary error from the local law using short measured-input diagnostics; keep them separate from causal forecasts.
2. If that establishes a local law deficiency, fit only the supported term/branch on NC data and re-run the existing450s causal multi-state/state-guard and RM/VSL/combined gain comparisons. Evaluate the new10484 arm as an additional falsification case; preserve10490, VSL loss cases and free-flow release requirements.
3. Freeze any promising causal candidate before unused seed/state validation. No default promotion until the original component qualification conditions pass. Neither the native result nor this diagnostic completes gain calibration or full GNE.

All work launched for this checkpoint is terminal; no owned VISSIM/cscript remains. Earlier goal-turn restatement of the completed1101 test was no new progress; this turn completed a new physical intervention, matched execution validation and spatial/conservation diagnostics that change the next calibration target. The goal remains active, with no external blocker.
