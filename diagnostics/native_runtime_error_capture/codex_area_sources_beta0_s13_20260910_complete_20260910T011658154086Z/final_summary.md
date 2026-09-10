# Final native runtime error capture

The completed run `codex_area_sources_beta0_s13_20260910` (run ID `329913b3a1a747948d4b5196242254c5`) contains **386 explicit lane-change deletions: 181 inside Ω and205 outside**. No deletion was on terminal24/120. There are352 events after45s waiting and34 after60s, with no duplicate event keys.

Runtime ERR is fully captured:296590bytes, SHA256 `6bccbd4541ba1d491d3d691e03353e3b6cbc3a2962628260ecfbff8bc7cf3c40`; stable read, unfinished final bytes0, unparsed runtime lines0. The same run log has`STAGE=SIM_DONE` and sim5400. Native event times span36–5399s. Network and run manifest hashes match. Native ERR itself has no run ID: the manifest, time and unchanged network support the association; this is not embedded proof of a run ID.

The final source ERR files still match all three captured raw hashes. Setup warnings are retained separately. The now-readable DLL log is464bytes and contains eight complete messages: controllers9101–9108 have no native signal program. Its final message has no newline; the exact complete punctuated message is reported separately from line-prefix parsing. This report does not infer that their COM commands failed.

## End-of-run input backlog

| Native input | Physical source | Classification | Mapped urban gate | Native remaining vehicles |
|---|---|---|---|---:|
|1098 (`경부_EB`)|74|Controlled freeway, insideΩ|excluded from urban gates|1932|
|1099 (`경부_NB`)|26|Controlled freeway, insideΩ|excluded from urban gates|574|
|1105|99|Urban source outsideΩ|`in_SC2003_N`|71|

These are the native termination messages' remaining input demand that could not be inserted over the completed run. They are not vehicles already admitted and then deleted, and are not TTD. The physical source and roles/gates were joined by exact input ID and link against the INPX and the run-manifest-pinned CSVs. The CSV volume columns are historical inventory values and were not used to infer actual admitted demand or the current schedule. The prior NC native ERR was overwritten, so no NC difference in this backlog is estimated.

## Matched interior deletions and measurement meaning

Existing interval-audit unresolved losses4/1/11 contain exactly1/0/5 native deletion ID/time/last-link matches for900–1050,1200–1350 and3300–3450. The matched native timestampT corresponds to an observed FZP disappearance atT+1.17,100,339 bytes were read by bounded seeks. Each selected byte range was rehashed. Earlier valid outward crossings by a subsequently removed vehicle remain valid TTD; no ID blacklist exists.

The181 internal deletions must be reported as a loss guardrail: they can reduce measured TTT and stop queue propagation. They are not exit events. With terminal native deletions0 there is no evidence here that terminal exit inference needs modification. Full-run all-loss reconciliation is separate from the bounded six exact ID matches above.

Current parser regression:8 tests PASS0.008s. Outputs and raw bytes under this directory are immutable capture evidence; `capture.json`, `removals.csv` and`final_summary.json` contain source paths/hashes and exact rows. Production/model/config/measurement files were unchanged.
