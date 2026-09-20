# Open-outlet causal checks: rejected candidates

2026-09-20. These experiments are complete, offline and NOT_QUALIFIED. The established `merge_drain_response_20260919/decisions_v1/internal_cost` remains the default diagnostic model. No production/default config or native network was changed.

## NC-only speed fit

`open_speed_fit_v2` uses seed23 NC900–2390, cells5–20 (5,183 samples), to fit scalar or acceleration/deceleration/density-gradient dependent METANET response coefficients. Selection uses next10s speed error, not intervention cost or gain. Training exposure includes observed merges; subsequent450s forecasts use only current/past observations. Seed33 is development data already inspected, not an unused holdout.

The scalar fit selected tau60s, nu3; the split fit selected tau_acc40/tau_dec60s and nu_ge3/nu_lt4.71196. Training RMSE14.011/13.986km/h improves on the previous local one-step model24.986 but remains worse than persistence11.861. More importantly, the450s NC state guards pass only2/12 and3/12 against the established model. VSL gain remains the wrong sign. Both candidates are rejected.

`open_speed_fit_v1` retains a failed in-memory tuple-versus-JSON-list equality assertion, its source snapshot and the offending prediction. Saved forecasts normalize to exactly the previous reference; v2 makes that representation comparison explicit without relaxing numeric equality.

## Observed downstream lane resolution

`downstream_lanes_observations_v1` extends the same physical lane grouping from cells5–14 through20. It reads existing NC FZPs and only past150s/current states. Three seeds preserve every old upstream state/history and72 downstream cell stocks/weighted speeds exactly; the existing4→3 lane transition is unchanged. This is a state-resolution experiment, with the same open outlet, model laws, parameters and commands.

`open_downstream_lanes_v1` barely changes450s gain:

| Seed | RM old→split [veh h] | VSL old→split | Both old→split |
|---|---:|---:|---:|
|13|+0.001331→+0.001015|+0.370919→+0.371880|+0.372264→+0.372877|
|23|−0.022164→−0.022648|+0.026151→+0.025991|+0.004111→+0.003471|
|33|−0.015288→−0.015736|+0.046635→+0.046522|+0.031564→+0.031013|

Both open reference and downstream split pass10/12 state guards against the **established** model. The earlier terminal probe's12/12 comparison was against the preceding unqualified lane candidate, a different comparator. No gain/ranking qualification follows from either count.

`open_causal_validation_v1.json` verifies current source pins,12 whole reference JSONs exactly,36 new forecasts' conservation/nonnegative/storage guards and unchanged west cells/flows. Both speed configs pass `verify_parameters.py`; receipts are beside the configs. Data/computation validation PASS is distinct from gain qualification failure.

## Next discriminating test

Stop extending lane resolution or sweeping speed coefficients without new response evidence.10484 has a large unexplained waiting response when the adjacent10490 is actuated. A direct10484 intervention can distinguish its own meter/head/merge/wait response from propagated mainline interactions. Freeze predictions before one3000s seed23 native run, reuse the exact matching NC prefix, and compare head passages, actual merges, pre/post-head residence and downstream response. Keep the existing10s RED/GREEN cycle and green8→6→4 at150s intervals. This is causal diagnosis on an inspected seed, not independent model validation or a controller-success claim.
