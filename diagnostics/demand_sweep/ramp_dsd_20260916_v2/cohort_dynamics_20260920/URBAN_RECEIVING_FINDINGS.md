# Urban receiving and initial destination diagnostics,2026-09-20

**RM/VSL gain prediction remains NOT_QUALIFIED. No production model/config has been promoted.**

The preceding input1101 sensitivity turn was progress: two completed native runs changed the diagnosis by showing that this input supplies only12.5% of71 visits. The original network remains the calibration reference; reduced-demand cases are additional diagnostic conditions. The earlier network-choice block is superseded by the user's demand-first direction. This goal turn uses completed native records only; no VISSIM run was started and no process remains owned/live.

## 1. Current receiving state predicts short discharge better than a historical mean

The current component boundary holds past150s10643 departures as the future drainage-service proxy. The aggregate proxy cannot respond to the shared71 queue or signal phase. In baseline seed23,1800–2850s,10643 lane1/lane2 discharge is182/61 vehicles and mean stocks10.34/42.70. The lanes are not interchangeable reservoirs.

`urban_receiving_probe_v1/` adds NC seed13 observations900–4500s from an existing native recording. The existing extractor verifies off/urban stock-flow conservation and7,202 SC1004 SG2/5 samples against native LDP. The first extraction attempt failed only when serializing a relative path; the absolute-path retry completed and the failure note is preserved.

A small linear one-step screen predicts lane-specific normal departures over the next10s. Inputs are past150s lane discharges, current lane-tail vehicle counts/speeds, current126/71 receiving queues, and saved signal timing. Coefficients are trained only on NC seed13,1050–3290s; four ridge penalties are selected on3300–4490s. Training/tuning excludes10s windows containing a71 abnormal loss. No RM/VSL benefit target is fitted.

|10s total departure RMSE [veh]|Past150s rolling mean|Current state + signal screen|
|---|---:|---:|
|seed23 NC|1.474|1.182|
|seed23 VSL|1.691|1.201|
|seed33 NC|1.393|1.156|
|seed33 spread-only|1.275|1.096|
|input1101 90%,seed23|1.275|1.107|
|input1101 80%,seed23|1.557|1.198|

This13–29% improvement is **reinitialized one-step prediction**, not450s autonomous forecasting. Each next prediction gets a new current state. Original seeds have been seen in earlier development; the input-sweep conditions are new conditions, not independent seeds. The all-window and no-loss-window scores are both retained.

The unconstrained green coefficients can be negative, so they are not suitable as physical MPC sensitivities. A second screen enumerates only two nonnegative-green constraints and signal lags0/10/20/30/40/60s. NC seed13 selects30s for history+signal and40s when current state is included. The constrained current-state screen still improves test RMSE by8–19%, but does not identify a universal startup delay. This is an aggregate signal/queue-propagation relation and must not be implemented as a40s driver reaction time.

Both screens pass future-traffic-row truncation checks. Signal states come from the saved fixed program, not future traffic. Linear coefficients are diagnostic feature associations, not a conserved urban flow law. Files: `urban_receiving_lag_probe_v1/result.json`, `urban_receiving_probe.py`.

## 2. A450s current-state anchor is insufficient

Holding only the current traffic features at2400s and advancing known signal time gives the following normal-departure forecasts. Future traffic rows were deleted before construction.

|NC case,2400–2850s|Actual|Fixed past150s|Current-state/signal anchor|
|---|---:|---:|---:|
|seed23|107|72|110.17|
|seed33|87|75|78.06|
|input1101 90%|100|69|72.21|
|input1101 80%|88|96|76.71|

The90% case remains badly underpredicted and80% worsens. Current receiving state is useful information, but freezing it is not a coupled urban forecast. Native control and NC have identical initial states, so this anchored forecast is also identical between their arms. It does not manufacture a VSL/RM benefit.

`urban_boundary_rollout_v1/` applies the anchored10643 service to the existing canonical component harness without changing parameters, arrivals, actuators, cost accounting, or other boundaries. Absolute seed23 off-ramp cost changes13.23657→10.83125veh·h, but mainline and on-ramp predictions remain exactly identical. Aggregate off-ramp space is not a binding receiving constraint in this case. All three predicted treatment cost differences stay unchanged.

`urban_boundary_rollout_lanes_v1/` also enables the existing lane-resolved store for10643 only. It retains finite storage, interval service and past causal lane-exchange rates; empty-lane service cannot drain the occupied lane. Parameter verification passes with existing calibration-override warnings.

|Predicted450s ΔTTT [veh·h]|23 RM|23 VSL|33 RM|33 VSL|
|---|---:|---:|---:|---:|
|Reference|−0.04138|+0.01241|−0.03199|+0.02682|
|Lane storage + historical service|−0.03999|+0.01131|−0.03244|+0.02605|
|Lane storage + current-state anchor|−0.04136|+0.01650|−0.03199|+0.02672|

These still miss the substantial native gain cases. The new boundary must **not** be promoted merely because one-step RMSE improved. This experiment does not prove that71 never matters; it proves that correcting this isolated boundary proxy is insufficient in the current mainline dynamics.

## 3. Initial exit intention is biased, but correcting one cell alone is insufficient

The model initializes branch-destination stock using historical exiting-cohort proportions. In congestion that is not necessarily the current waiting population's destination proportion.

`initial_exit_intent_audit_v1/` follows vehicles present at2400s through3000s. All inspected upstream-cell5–8 vehicles originate at link74, downstream of routing decision1130 which assigned their first exit earlier. Native later paths identify all audited destinations with no censored vehicles. **Future paths are used for diagnosis only, never as an online observation.**

|Cell8 vehicles before10643 at2400s|seed23|seed33|
|---|---:|---:|
|Total eligible stock|24|12|
|Historical exit proportion|0.11468|0.14732|
|Model initial10643 labels|2.7523|1.7679|
|Native later-observed10643 destination|6|2|

In seed23,10 of26 vehicles in cell7's first two lane groups are exit-bound; in seed33 it is6 of12. The current lane model introduces destination labels only at the branch cell. It does not carry this upstream exit-intention stock. These conditional queue fractions must not be substituted for configured network demand fractions.

`initial_intent_rollout_oracle_v1/` supplies only the exact branch-cell initial labels, leaving every vehicle count, speed, future split, demand and command unchanged. This is explicitly a future-path oracle. Aggregate and lane-store variants both fail to fix gains: seed23 VSL+0.01275/+0.01177 andseed33+0.02695/+0.02632veh·h. Initial label error in one cell alone is not the explanation.

## Verification and next action

`urban_receiving_validation_v1.json` verifies24 reference forecast replays exactly,64 forecast conservation checks and64 unchanged western cells/flows. Production core source hashes remain unchanged. These counts include repeated reference runs and are not independent validation samples. The lane candidate passes the required parameter check. No gain qualification or full twelve-state adoption gate was passed or claimed.

The next bounded question is how upstream exit-bound inventory, its lane distribution and longitudinal passage timing affect the mainline response. First test the information/transport mechanism on the existing paired recordings; do not fit a constant gain bonus or turn the observed queue mixture into extra desired demand. New state/route observations should be added to native recording only if that diagnostic shows a plausible path to a causal model.71 receiving remains a necessary coupling to preserve, but further isolated drainage coefficient searches are not justified by this checkpoint.

The complete objective remains active: meaningful RM/VSL/both gain direction, component costs, candidate ranking, free-flow release and state protection on unused validation data, followed by canonical adoption. Ω/full GNE and component qualification remain separate.
