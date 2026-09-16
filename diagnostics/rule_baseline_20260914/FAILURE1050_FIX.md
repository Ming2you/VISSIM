# Rule VSL failure at1050s and restart

- `rule100_none3000_s13_v1` completed3000s; its completion receipt passes native LDP/readback execution evidence. Preserve and reuse this baseline.
- `rule100_vsl3000_s13_v1` failed at1050s, after its900s decision succeeded. The first60km/h request was rejected because the inherited `config_overrides.freeway_follower.vsl_set` contained only80,100,120. The sequential matrix stopped, so RM/both did not start. Preserve this failed run.
- The physical VBS allowed list and the native network already include desired-speed distribution60 (range58–68km/h). No network or distribution edit is needed. Merely bypassing the validator would be wrong: the canonical CSV writer uses the same model command set for its nearest-speed encoding and would turn60 into80.
- `prepare.py` now writes separate `config_*_v2.json` files with60 added to that command set. All original configs remain intact. Policy, writer and subsequent plant replay must use this corrected set. Physical model parameters, demand, native city signals, control150s, and RG meter rules are unchanged.
- The rule profile now checks every configured speed command even during the fixed100km/h warmup, so this mismatch fails before feedback. The new regression failed before this check and passes after it. All9 rule tests and3 existing profile/writer tests pass; parameter verification passes.
- `failure1050_recheck_v2/summary.json` records full canonical adapter/CSV execution for all4 arms using the saved failed1050s state and the actual900s command. VSL/both produce60 in both action JSON and all6 west-zone0 CSV rows. NC CSV is byte-exact to the completed NC1050s command. These are offline command checks, not a claim of completed native60 execution.

Restart only the unfinished cases, under new names:

```powershell
./diagnostics/rule_baseline_20260914/run_four.ps1 -EndSec 3000 -Arms @('vsl','rm','both') -Revision v2
```

The existing wrapper preserves failures, refuses concurrent VISSIM processes, checks native execution evidence at completion, and stops the sequence on failure. Per the user request, no live traffic analysis or repeated progress polling accompanies this restart.
