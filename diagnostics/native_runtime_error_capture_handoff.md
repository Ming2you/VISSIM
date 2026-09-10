# Native runtime deletion capture handoff

Final capture completed after SIM_DONE: `diagnostics/native_runtime_error_capture/codex_area_sources_beta0_s13_20260910_complete_20260910T011658154086Z/final_summary.md` and `.json`. Final386 deletions =181 inside +205 outside; terminal24/120=0; runtime parse has no unclassified lines. The historical prefix findings below remain unchanged. The final summary separately maps native uninserted residuals1098/1932,1099/574,1105/71 to their exact physical inputs; no NC comparison is inferred. Current tests:8 PASS.

Read-only capture/parser is ready. Production, measurement logic, configs and the simulator were untouched.

The latest preserved **prefix**, through native warning time 4884 s, contains **325 explicit lane-change deletions**: **146 inside Ω**, **179 outside**, none on terminal links **24/120**. The waiting times are 45 s for 296 events and 60 s for 29. Fifteen “next link not found” warnings are retained separately because they do not explicitly say a vehicle was removed.

Raw capture: `diagnostics/native_runtime_error_capture/codex_area_sources_beta0_s13_20260910_prefix_20260910T010330759902Z/`.

- Runtime raw bytes: 262144; SHA256 `3e2e8688fda0e9e357d5a31878d48d7913d4de17784c71cd772b8f4564168a47`.
- Complete-line prefix: 261920 bytes; the final 224 partial bytes are preserved but unparsed.
- Setup ERR bytes are preserved independently. The zero-size DLL log is exclusively locked; its size is observed, its bytes are **not claimed captured**.
- Run manifest/network/Ω network SHA and timestamps agree. Native ERR has no embedded run ID, so these establish a supported association, not a cryptographic run binding.

| Audited interval | Cached inside unresolved losses | Native deletion ID matches | Remaining unexplained by these native deletions |
|---|---:|---:|---:|
| 900–1050 | 4 | 1 | 3 |
| 1200–1350 | 1 | 0 | 1 |
| 3300–3450 | 11 | 5 | 6 |

The exact matched IDs are 4133 at native time 959; 20979/3311, 15473/3348, 8059/3351, 16644/3364 and 16009/3368. Each is still present in FZP at its native warning time T and absent at T+1. Matching uses the observed disappearance time and physical last link, not warning time alone. The bounded seeks read 16,986,545 FZP bytes, not the complete file.

No vehicle-ID blacklist is used. Earlier genuine outward crossings by a vehicle removed later remain valid TTD. These internal deletion disappearances are already excluded from completed exits; they can still artificially lower TTT and terminate congestion and should be reported as a separate loss guardrail. This prefix provides no evidence of contamination of terminal-exit inference, because its terminal deletion count is zero. Final warnings remain to be captured.

## Complete capture command

After this run's `STAGE=SIM_DONE`, run from the worktree:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 diagnostics/capture_native_runtime_errors.py --run codex_area_sources_beta0_s13_20260910 --run-id 329913b3a1a747948d4b5196242254c5 --complete --fzp-checks
```

The command creates a fresh timestamped diagnostic directory and refuses output overwrites. `complete_runtime_bytes` additionally requires a stable read and no unfinished final line. Check that field and `complete_line_removal_parse_complete`; `--complete` alone does not prove native DLL flushing. The locked DLL file remains explicitly unreadable if still locked.

## Verification and historical records

Six small tests cover optional Korean route names, 45/60-second waits, partial lines, other warning categories, start-edge timestamp candidates, and T→T+1 disappearance without an ID blacklist. Existing prefix results are immutable historical records. Since that capture, the producer added a start-edge check neighbourhood, required matching physical links for exact joins, and repaired Markdown formatting; all current captured events have identical classifications under these checks (no start-edge events were omitted).

The earliest bootstrap directory `source_beta0_prefix_20260910T005543813439Z` contains two exact raw files saved before the DLL lock error; its new `incomplete_capture_note.json` indexes those files without changing them. The 010058 prefix preserves an earlier parser with 14 named-route deletion lines and 15 next-link warnings unclassified; the 010330 prefix is the corrected evidence. Do not reuse the earlier parser's 311 as the current deletion total.

Files to stage explicitly: `diagnostics/capture_native_runtime_errors.py`, `diagnostics/test_capture_native_runtime_errors.py`, this handoff, and selected exact raw/report files under `diagnostics/native_runtime_error_capture/`. No Git operation was performed by this task.
