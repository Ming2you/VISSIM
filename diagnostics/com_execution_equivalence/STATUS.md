# COM execution optimization — 2026-09-10

The requested short qualification runs have finished. No native VISSIM process remains. No additional5400-second run was launched for this COM test. All comparison arms used the same frozen producer sources, physical settings, demand, seed and initial conditions within each pair. Only the two existing SG execution switches differed. Required1-second head/vehicle observations remained ON.

| Pair | End | Ordered FZP rows, exactly equal | Actual commands / observations / readbacks / final controls | Native LSA coverage |
|---|---:|---:|---|---|
| signal_head_pair_v2.json |1200|1210521|PASS|FAIL|
| ramp_head_pair_v1.json |1200|1226653|PASS|FAIL|
| closed_loop_head_pair_v1.json |1050|986195|PASS|FAIL|

All three verifier results set actual_execution_equivalent=true, native_lsa_com_coverage_passed=false, passed=false. The1050-second closed-loop check covers the900-second initial decision and the next1050-second decision after one observed control interval; it does not certify5400-second adaptive behavior. Both fixed pairs cover900 seconds unchanged warmup plus300 controlled seconds.

Canonical edits remain installed: scripts/run_real_world_stackelberg_controller.vbs SHA961d61d06479d9872ba2bb8594e6495ab9ca7cfdf23d58c710cce8834125eee6; scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1 SHA619066dfa4191e1482cb54d0bc8beee5aa74760c8418ce6b16e9de79e9804774. Neither file changed during qualification. canonical_edit_receipt.json preserves the before/after sources, and ../com_execution_canonical_applied.patch preserves changes with unchanged line endings retained.

The writer skips successful repeated SG states, verifies changed writes immediately and at the next callback, and checks all owned groups at control/end boundaries. VSL keeps four-class application-time setters/actual readbacks and removes two redundant summary reads. Required head, actual ownership/state capture, queue/arrival/far histories, route snapshots, reset boundaries, timing/amber/meter quantization and pre/post-step order stay unchanged. Head ON remains stepwise. Existing event replay uses different diagnostic decision cadence and is not adopted as an equivalent closed-loop acceleration.

Native LSA did not cover the actual COM-owned transitions or applied initial states. No native rows were fabricated from commands. This fails the user's native recording criterion, independently of passing actual-readback and FZP equivalence. No setting guaranteeing that coverage was established in installed2020 attributes or official documentation. diagnostics/run_selected_control_trial.ps1 still explicitly selects full readback/repeated writes; promotion of its normal experiment defaults is deferred while the required native criterion remains unsatisfied. The tested fast options remain available in the canonical runner.

Canonical no-argument VBS compilation, watchdog syntax,15 installed writer/observer regressions,21 startup-watchdog cases,42 command/readback verifier regressions and8 timing-parser cases passed. Synthetic checks are not substituted for the actual native results above. signal_head_pair_v1.json retains the first verifier schema error, corrected using the actual state/action provenance contract before v2.

One actual old signal attempt, codex_com_signal_head_old_s13_1200_r01, stalled after actual post-readback1158. Its existing watchdog stopped only owned cscript46036/native38484 after314 seconds idle. Failed receipt, raw outputs and failure_assessment.json are preserved. Exact blocked COM API is unknown; this attempt is excluded from speed comparisons. The unchanged retry succeeded. No user or unrelated process was stopped.

Timing is summarized in RESULTS.md and the three *_timing_v1.json files. Nested PERF buckets must not be summed. Counted COM excludes enumeration and uninstrumented getters. The old signal startup wait is principally in demand after-read101.477 seconds, not setters1.555 seconds. Whole-run wall changes include startup/cleanup and must not be called pure simulation speedup. post_analysis_timing.json records separate post-run verifier command wall times. Initial300-second watchdog progress uses actual positive SimSec, not ordinary log writes or GUI responsiveness.

The earlier full controller r02 (FW70/urban40 seed13) completed before these edits: Omega TTT1828.88 versus NC1938.977083, about5.68% lower, still below10%. Its raw/postprocessed evidence and source were preserved. No controller/model/candidate/objective/demand/route change is part of this COM qualification. The original70/30 target remains separately unachieved; do not substitute70/40 results for it. Controller refinement and its meter-alias probe remain paused for this execution request. Future scenario/controller decisions require their own authorized scope; do not start another5400-second run merely to validate this COM change.
