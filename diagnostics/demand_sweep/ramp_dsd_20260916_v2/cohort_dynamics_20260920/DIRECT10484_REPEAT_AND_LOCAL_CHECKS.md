# Direct10484 repeat and bounded local checks

2026-09-20. **Gain calibration remains NOT_QUALIFIED.** The seed33 native repeat is complete. Both offline parameter candidates below are rejected. No production/core/default configuration, geometry, demand or turning movement was changed in this checkpoint.

## Native repeat: same accepted-merge reduction, different network response

`direct10484_s33_v1` reused the original network and demand, not the input1101 reduction scenario. Only RM_C10484/SC9108 changed: green8/6/4 seconds at2400/2550/2700, held4 at2850, with the existing10-second RED/GREEN cycle and post-frame application order. All other meters, urban signals and desired-speed distributions remained native. The existing runner completed3000s in189.622s and exited its owned VISSIM process normally.

The prepared network is byte-identical to the paired no-control network. Before treatment,8,606,202 complete FZP rows through2400s match exactly.120 command readbacks,600 controlled-SG LDP samples, all unaffected recorded signals and actual green durations pass. `paired_validation.json`, `review.json`, `boundary_balance.json`, `spatial_response.json` and `validation_summary.json` preserve the checks. Analysis ran after the native simulation ended.

All costs below use2400–2850s and the same component: FW_E physical mainline plus its four on-ramp and four off-ramp connectors. Native costs integrate1-second end-frame stocks. This is not the full urban+freeway Omega objective. Negative delta means less residence time.

| Seed | Mainline delta [veh h] | On-ramp delta | Off-ramp delta | Total delta | Relative total change |
|---|---:|---:|---:|---:|---:|
|23|−0.878889|+0.424444|−0.004444|−0.458889|−0.443%|
|33|+0.311111|+0.197222|−0.050833|+0.457500|+0.457%|

Both seeds reduce actual10484 merges by11 vehicles:97→86 and101→90. Its end stock increases by10 in both:8→18 and17→27. Its own connector residence increases by0.409167 and0.218333veh h. The different total outcome is therefore not evidence that the seed33 actuator failed, nor that metering always helps. Seed33 g8 and g6 each leave the150-second merge count unchanged; g4 reduces35→24. Unchanged interval counts do not mean unchanged passage times.

The established plant's predicted totals are+0.008984/+0.000204veh h for seeds23/33; the open-outlet candidate predicts+0.003666/+0.018023. Seed33's positive total sign alone is not a pass: both models predict a mainline benefit while the native mainline cost increases, and the component magnitudes are missed. Model integration uses10-second mainline,1-second ramp and event-time off-ramp accounting; this finite integration distinction is retained rather than represented as exact equality with native1-second costs.

Two seeds with opposite small effects do not establish a statistically zero expected effect. Nor is it defensible to fit a universal10484 benefit term to the first seed. The NC state of seed33 was already inspected in development; this is a frozen-before-run new-intervention check, not qualification on a wholly unused state.

## Spatial and conservation evidence

Seed33 mainline cost includes cell13+0.596111, cell14−0.397500, cell16+0.254167, cell17+0.348333 and smaller mixed changes elsewhere. Thus improving the controlled merge cell alone does not imply a mainline or network benefit.

During2700–2850s, vehicle-weighted native mean speeds and mean stocks are:

| Seed / cell | NC speed→RM [km/h] | NC stock→RM [veh] |
|---|---:|---:|
|23 /14|42.16→64.24|53.88→37.95|
|33 /14|35.52→41.46|64.27→55.95|
|33 /13|37.09→31.70|56.39→66.01|

The first matched intervention-time vehicle difference appears around the10484 merge at2425s in seed33, then in neighboring cells. Matching is limited to IDs present in the exactly equal2400s frame: later generation may assign the same numeric ID to a different vehicle. These first-difference times are not shockwave-speed estimates or proof of a causal transmission path. Later western differences also occur; the analysis does not assume that every cross-run difference is a physical wave from10484 rather than a change in stochastic execution.

The component ledger has zero unexplained transitions, zero component removals and zero extraction exclusions. Both seed33 source counts and their time moments are identical. The terminal has8 fewer exits; its signed residence contribution is+0.543333veh h. Other external-interface time moments total−0.085833, giving exactly+0.457500. This is an accounting identity, not attribution of every contribution to an independent causal mechanism. No vehicle was silently deleted to close the ledger.

`direct10484_two_seed_summary_v1.json` includes150-second spatial aggregates and both predicted and actual component costs. The prior seed23 spatial source is preserved in `direct10484_s23_v1/spatial_source_before_seed_extension.txt` and matches its old recorded source hash. The current spatial tool explicitly selects seed33 and matches only the intervention-time cohort. Old results and pins were not rewritten.

## Consumed FD and local response checks

The downstream critical densities are not an accidental stale default: the earlier NC spatial fit selected39.2veh/km/lane for ordinary three-lane cells15–20, from28×1.4. Cell14 uses28. These are effective fitted parameters, not measured capacities. `downstream_fd_check_v2` tests the single alternative of restoring15–20 to the existing plain three-lane value28 and recomputing its FD-implied capacity. It does not add a capacity gain or fit control costs.

`local_merge_response_v1` independently changes only cells13/14's relaxation/anticipation coefficients. Five bounded tau candidates with bounded analytic nu fitting use NC seed23 samples before2400 only. It selects tau60s and nu3. Training10-second speed RMSE falls32.78→16.63km/h but remains worse than speed persistence15.36. On later seed23 and seed33 samples, fitted RMSE16.93/16.95 also exceeds persistence14.98/14.38. No treatment cost entered the fit.

Both use the same open outlet and existing ramp/exit model. The table shows full causal450-second gain tests; negative values mean predicted benefit.

| Candidate | State guards vs established /12 | Seed23 RM10490 | Seed23 VSL | Seed23 both | Seed23 RM10484 |
|---|---:|---:|---:|---:|---:|
|Open reference|10|−0.022164|+0.026151|+0.004111|+0.003666|
|Downstream critical28|9|−0.037040|+0.016508|−0.020409|−0.007596|
|Local tau60 / nu3|11|−0.031090|+0.022722|−0.008210|+0.016382|

Neither recovers the known VSL response or the seed23 direct10484 response. The local fit is not promoted merely because it passes more state guards. Seed13/33 results and all arm forecasts are retained in each candidate's `results.json`.

Runtime instrumentation reconstructs the consumed cell14 relaxation, convection and anticipation speed update to numerical tolerance, with135 group updates per forecast. It confirms that the intended coefficients reach the evaluated equation; merge losses act afterward and are not part of that intermediate speed total. Each comparison exactly reproduces13 reference forecast JSONs, preserves west-cell/flow results and passes vehicle conservation, nonnegative stock and storage checks. Both config parameter checks pass with existing warnings. The local scoped override is applied by the diagnostic model instance; its effective values are verified by the runtime trace, not by the config-only check. It is not a new production configuration feature.

`fd_and_local_response_validation_v1.json` records this verification. The earlier FD-only script's exact source is archived at `downstream_fd_check_v2/source_before_local_extension.txt`; all its other pins still match. The initial v1 instrumentation import failure is preserved separately and is not counted as an experiment result.

## Next bounded test

The evidence no longer supports tuning10484 to reproduce a universal positive gain. Retain both direct-response seeds as opposing cases, together with the existing RM10490, VSL, combined and dispersion-only cases.

Before another coefficient fit, examine conserved transport within the actual merge cell14: its upstream part, merge insertion position and downstream part. The earlier resolution experiment deliberately used port-free stretches and did not test this cell. A small offline measured-speed/input identification can determine whether cell averaging loses the local storage and outflow response; it must be labeled a future-input diagnostic, preserve all entering/remaining vehicles and include both seeds. Only an improvement there justifies a causal local-state change and the full existing gain/state checks. If it does not improve, do not expand the grid or repeat broad parameter sweeps. A causal speed-response law still needs independent justification; no future measurement can qualify an operational forecast.

Input1101 reduction remains a separate completed demand test in `input1101_sweep_v1/REPORT.md`. No reduced-demand scenario or turn deletion was adopted. Full Omega control performance and full GNE remain outside this component checkpoint. No new commit or push was requested or performed.
