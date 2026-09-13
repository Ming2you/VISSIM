# Watchdog Git-root encoding: unapplied minimal repair

The existing function reproduces the reported `GetFullPath` exception under Windows PowerShell 5.1 with `Console.OutputEncoding=949`. Git returns an **unquoted UTF-8** path; CP949 decoding introduces `?` into the Korean directory names, then .NET rejects that path. `core.quotepath=false` produces exactly the same raw bytes and does not repair this failure. With CP437 the path is also wrong, but the old function silently returns an empty commit instead of throwing. With UTF-8 the old function works.

The historical r03 process did not record its console code page. This is an exact exception reproduction in the same checkout, rather than a direct measurement of that process's encoding.

| Native stdout decoding | Original root result | Proposed root result |
|---|---|---|
| UTF-8 (65001) | `dd13e0810fe4fc5582a863cb19839fe0f2464d9f` | Same commit |
| Korean CP949 | Empty; `Illegal characters in path` | Same commit, no errors |
| OEM CP437 | Empty; path mismatch | Same commit, no errors |

`watchdog_exact_git_commit.patch` changes only `Get-ExactGitCommit`. It checks exact ASCII `--is-inside-work-tree=true`, an empty `--show-cdup` response, and one verified `HEAD^{commit}` ID of 40 or 64 lowercase hexadecimal characters. Every native exit code is checked; failed, multiline, whitespace, quoted or malformed responses return empty metadata. No global encoding, Git configuration, repository contents or wrapper is introduced. Git documents `--show-cdup` as the relative path from the current directory to the worktree root, and `--verify ...^{commit}` as commit verification. [Git rev-parse documentation](https://git-scm.com/docs/git-rev-parse)

The root requirement remains: the actual `scripts` and `vendor/NumSim-mine` subdirectories return empty values. The vendor snapshot's separate `numsim_snapshot_commit` remains the appropriate recorded identifier. Existing root, trailing separator and relative `.` inputs return the same commit across all tested encodings. Bare/non-worktree and unresolved HEAD conditions are tested with native-output fakes; no test Git repository was created. The helper retains the existing optional-metadata failure policy, not a new run-abort policy.

The r03 provenance file records an empty workspace commit, while all **17/17 artifact entries contain 64-character SHA fields**, including the expected LCD network SHA. The Git helper is called after artifact hashes are gathered and supplies commit metadata only; this repair does not change demand, simulation, file hashing or process control. These are historical hash fields, not a claim that every historical input equals today's file. A Git commit also does not certify uncommitted source; per-file SHA evidence remains necessary.

Validation: **6 tests PASS in 12.936 seconds**, PS `5.1.26100.9444`; production source changes `[]`; read-only `git apply --check` exit 0. The harness parses the production script and extracts only this function, then executes original/proposed functions with read-only Git commands and 14 fake response cases. It does not invoke the watchdog, COM, VISSIM or a model. Evidence is in `watchdog_exact_git_commit_validation_20260910T074754634911Z/evidence.json`, including raw Git bytes, decoded codepoints, errors and source pins. Earlier harness attempts remain in the earlier evidence directories. Initial apply-check failures were resolved by matching the existing line endings exactly. The patch deliberately preserves this frozen function's mixed LF/CRLF context; it does not normalize production bytes.

Frozen production SHA: `15eac24e146a3398c15c2bfe05f75b09aecc1fd10527eace4d35503053b54c37`.
Final unapplied patch SHA: `ad6fb24e6aa070f3abe45b436edf29c3c96ddd42c86c6a0ebbcc1795bbba1efc`.

Reproduce the isolated tests from the checkout:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 -m unittest diagnostics.test_watchdog_exact_git_commit -v
```

Ready diagnostic files: `watchdog_exact_git_commit.patch`, `test_watchdog_exact_git_commit.py`, `watchdog_exact_git_commit_review.md`, `watchdog_exact_git_commit_review.json`, plus the final evidence directory. Production application and any manifest regeneration remain deferred to the parent after the active run.
