# Native pre-step alignment v2

The first actual replay remains a direct source-clock failure: COM LDP(t) matched source(t−1), with 370/20,400 mismatches against source(t). Its report and run artifacts were not changed.

The root agent added the native-only `SignalClockPosition()` helper to the canonical VBS runner. A COM write at time t now selects the source state for frame t+1. The composite event clock and actual urban signal application use the same helper. Simulation step order, legacy urban clock and meter clock remain unchanged.

The existing command-clock postchecker now applies the same one-second advance only when the pinned generated sibling declares native clocks. Hence immediate at t expects source(t+1), while post-step at t expects source(t). This changes the expected behavior for the new replay; it does not relabel the previous lagged run as source-equivalent. Before this change, the exact command-clock and verifier bytes were preserved under `native_clock_replay_v1/source_v1/` beside this report.

Validation:

- Existing command-clock, pair-verifier and native-record suites: 60 PASS in 7.767 seconds. Native source comparisons cover actual generated rows for all 17 SCs at both immediate and post-step boundaries. Legacy and meter checks remain passing.
- Actual cscript extracted helper/composite/event tests plus the existing native-OFF suite: 20 PASS in 12.386 seconds. SC7 write907 selects phase67 / AMBER for recorded frame908, while SG7 remains GREEN. The next state transitions are scheduled at write907 and write910. Without native config, the same write907 remains at phase66 / GREEN. Both production call sites are checked to use the helper.

The new actual cscript harness and captured result are `native_writer_pure_v1/native_prestep_frame_alignment_v2.vbs` and `.json`. Earlier native proof outputs were not overwritten. No simulator/model was started by this validation task. A new bounded native replay must establish same-time LDP/source equality before direct source equivalence can be claimed. LSA coverage remains independent.
