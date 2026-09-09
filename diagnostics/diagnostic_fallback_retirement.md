Three regression suites now test installed sources directly: measurement-window resets, fixed diagnostic profiles, and physical freeway counts. They no longer patch or recompile replacement production functions. The freeway OFF comparison retains an immutable pre-integration function from the existing fixed-source fixture.

The first run exposed an obsolete assertion tied to the text of an old exception comment. That assertion was replaced with a behavioral check: injecting a diagnostic-profile failure into actual `main()` must raise and publish neither action JSON nor action CSV. All 15 checks then passed in 4.390 seconds. The VBS checks use mocked COM; no VISSIM instance was created.

`audit_snapshot_readonly.patch`, `diagnostic_profile.patch`, and `freeway_count_geometry.patch` had no remaining executable references after migration. Their three exact absolute paths were verified inside the worktree diagnostics directory, fingerprinted against the archive, and removed individually. `retired_diagnostic_fallbacks.json` records the operation.

Before any edit, the three old tests and three patches were preserved exactly in `fixtures/diagnostic_fallbacks_20260910.zip` (14,918 bytes, SHA256 `e3ecfa792cfbaaf9db4abd6d93655c2d25786c8d773cafb06a58d9dae9253f83`). The companion manifest lists every raw member's length and hash. The previous diagnostic proposal archive is unchanged.

The earlier `probe_production_migration.md` records the state before this follow-up. Its remaining-artifact table is historical: these three entries are now retired; the eight route/SC2001/receiving proposal artifacts still await consumer migration. No production model, active configuration, calibration, native input, or historical run output changed in this cleanup.

Reproduce with `python -m unittest diagnostics.test_audit_snapshot_windows diagnostics.test_diagnostic_profile diagnostics.test_freeway_count_geometry -v`. The profile main and count observation tests require the declared local or packaged historical snapshot; they explicitly skip when that fixture is absent.
