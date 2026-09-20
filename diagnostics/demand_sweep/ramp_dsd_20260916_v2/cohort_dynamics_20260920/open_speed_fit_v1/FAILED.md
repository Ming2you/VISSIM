# Incomplete first attempt

The first rollout stopped on an in-memory versus loaded-JSON equality assertion. The in-memory forecast contains tuple/list distinctions in ramps and diagnostics. `failed_reference_prediction.json`, serialized from the same current calculation, is exactly equal to `terminal_probe_v1/prediction_s13_open_outlet_none.json` after loading both JSON files. There was no numerical traffic divergence.

The failed attempt's script is preserved as `source_before_retry.txt`; its protocol pins the original source. The retry normalizes the in-memory forecast through JSON before the full equality assertion and writes to a new output directory. The incomplete local fits here are not rollout qualification results.
