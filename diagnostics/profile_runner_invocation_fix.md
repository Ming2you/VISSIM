# Diagnostic runner invocation failure and correction, 2026-09-10

`codex_meter10639_g5_s13_20260910` is a failed intervention run. At 900 s,
`RunControllerDecision` omitted `--diagnostic-allowed-vsl-speeds` for
`diagnostic-ramp-profile`; the adapter raised `runner allowed VSL speeds must
be supplied`. There is no `action_000900.csv`. The plant retained the warmup
all-open meter action until 5400 s. The final integrity gate rejected the run
(exit 3 / watchdog `EXIT_NO_DONE`); it was not a silent successful run, but the
missing early stop wasted the remaining simulation time. Do not use this run
as evidence for the effect of RM_C10639 green 5 s.

The VBS runner now supplies the existing physical speed allowlist for all
three profile aliases: VSL, ramp, and signal. The signal profile currently does
not consume this argument, but the runner supplies the same profile contract.
For any selected `diagnostic-*` run, a failed decision, missing action CSV, or
CSV application rejection stops the simulation, closes the evidence files,
prints `ERROR=DIAGNOSTIC_DECISION_FAILED`, and exits 3 immediately. This also
covers a failed `no-control` warmup of a diagnostic run. Non-diagnostic runs
retain their existing final-integrity failure handling.

`test_profile_runner_invocation.py` extracts the current VBS functions and
executes the actual `RunControllerDecision`, command construction,
`RunCapture3` / `shell.Exec`, canonical adapter entry point, `ApplyActionCsv`,
speed writer, signal ownership handoff, SG plan validation/replay, meter event
scheduler, and signal write/readback functions. Only VISSIM objects, observed
state capture, and the passage of simulation time are faked. The test does not
make a duplicate adapter or replace its `main` function. Native `.sig` program
behavior cannot be established by this test and remains a live-run check.

Before the VBS correction, this test reproduced five failures: the ramp
argument omission, the signal argument omission, and continuation after each
of three failed-decision/output cases. After correction, all seven unittest
tests in the combined invocation and lever suites passed (15.2 s). The tests
include actual adapter output for VSL80, RM_C10639 green 5, and the frozen
SC1004 green variation; the ramp writer requests GREEN at 900, AMBER at 905,
RED at 906, and GREEN at 910. Post-step checks correctly see the previously
held state at each transition before the next write. Every other meter stays
GREEN. These are fake-COM pipeline results; physical VISSIM readback at the
same times is still required after restart.

The older `test_lever_profiles.py` now reads the integrated production source
directly. Its historical pending-patch reapplication failed after the shared
initializer refactor, before any behavioral test ran. The lever assertions
remain in place.

Run in a Windows environment that permits Windows Script Host settings access:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest diagnostics.test_profile_runner_invocation diagnostics.test_lever_profiles
```

Changed files for this correction: the runner VBS, the new invocation test,
the existing lever test source loader, and this report. No production adapter,
profile module, network, `.sig`, or numerical parameter was changed here.
