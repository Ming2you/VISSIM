# Fixed-arm driver: bounded natural process exit

The integrated driver passed all **21 small regression tests** (3.639 s; subprocess wall 3.860 s), with source hashes unchanged during validation. Result: `fixed_driver_natural_exit_validation_v1/result.json`; complete log: `fixed_driver_natural_exit_validation_v1/stderr.txt`.

Driver SHA256: `272b50ec339a23914d126fff8e7a82be270930bc93045b49e8100735407a367e`. Test SHA256: `9bbb7096acb5e3c75cce68848baf6a2bded517ce7ef09828a22786374741a013`.

After watchdog exit0, `post_watchdog_process_gate` starts a 30-second deadline before the first process inventory. Each subsequent inventory query timeout and sleep is limited by the remaining budget. The initial observed PID/creation-time set is fixed; any observed new PID or reused PID with another creation time immediately fails. The driver never kills a process. Only an empty final inventory permits validation and later arm execution. Nonzero or unknown watchdog exit skips both the new inventory gate and waiting, and fails immediately.

Each arm records `post_run_natural_exit` with initial/final process rows, every timed observation, unexpected identities, status, wait limit and elapsed time. `post_run_processes` remains the final inventory; it is explicitly unknown (`null`) on the nonzero-exit path. Inventory failure and survivor timeout fail closed. This is sampled process evidence, not an atomic lock against an unrelated launch between observations; the existing pre-next-arm inventory check remains.

The three new tests use a fake monotonic clock and inventory sequence, without real sleep or process enumeration. They cover delayed natural exit; new PID and same PID/new creation time; persistent survivor timeout plus nonzero-exit no-wait. The existing 18 tests still pass, including the serial state machine's stop-before-treatment rule. Root's independent environment fix is covered in the same run: case-insensitive removal of inherited PSModulePath, one native Windows PowerShell Modules path, and successful/failed provenance hash preflight fixtures.

No runtime, source fixture, original network, r01 output, COM instance or traffic model was changed or executed for these tests. The completed-but-failed r01 evidence remains historical; this driver change does not retroactively certify r01 provenance or replace its failed gate. The next actual three-arm run and its process/provenance validation remain root-owned.
