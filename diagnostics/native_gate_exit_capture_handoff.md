# Native gate process exit capture

Windows PowerShell 5.1 reproduced the native v2 gate's missing exit code without COM: redirected child processes exiting 0 and 7 both returned `null` with the original lifecycle. Removing `Refresh()` alone also returned `null`. Acquiring `Process.Handle` immediately after `Start-Process`, while retaining the same process object, preserved the exact 0 and 7 codes with the same polling and refresh sequence.

The narrow change in `run_flat_network_native_gate.ps1` acquires that handle, rejects a zero handle, and records `OWNED_CSCRIPT_EXIT_CODE_UNAVAILABLE` when the code remains unknown. Completion markers never substitute for an OS process exit code. The existing owned PID/creation-time cleanup and serial stop conditions are unchanged.

- Current PS SHA256: `a223dcd408bbff2cd39c3b0d2ebcfad795613c2a47b221062205d432d5152c50`.
- Prior encoding-fixed PS SHA256: `6aa969a57b3520231d719a7bc27f91a1dcd7b85a84c4e507da887de1b04607b3`.
- Reproduction: `native_gate_process_exit_probe_v1/result.json` (six actual tiny PowerShell children; 5.1.26100.9444, CLR 4.0.30319.42000).
- Actual launch/poll/capture source regression: `native_gate_actual_exit_test_v2/result.json`; 0 and 7 exact, full PS AST parse errors 0. Only the child executable/arguments are substituted with tiny PowerShell commands; no COM/model is executed.
- The first actual-source harness attempted a tiny VBS. This tool host returned script-engine access denied and genuine process exit 1 for both cases. Its failed result and stderr remain under `native_gate_actual_exit_test_v1`; this is not described as a successful VBS run or deleted.

The real native v2 evidence remains unchanged: its baseline LoadNet/readback completed with no attribute failures, both owned processes were gone, but an unknown OS exit code correctly made the gate fail. `flat_network_native_readback_v1` and `v2` are historical results and must not be overwritten. VBS, Python validator, original network/SIG files and generated network assets are unchanged by this fix. A real v3 LoadNet readback is still a separate parent-run validation.

Parent execution command (new output directory):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File diagnostics/run_flat_network_native_gate.ps1 -OutputDirectory diagnostics/flat_network_native_readback_v3
```

Tiny regression command (choose a fresh output directory):

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File diagnostics/test_native_gate_process_exit.ps1 -OutputDirectory diagnostics/native_gate_actual_exit_test_v3
```
