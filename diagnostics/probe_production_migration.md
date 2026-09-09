Five diagnostic callers now initialize the installed canonical model using an explicit final configuration, recorded snapshot and actual previous action. Grid replay imports the endpoint after runtime installation. Prediction and trace probes additionally require the action to replay. No AST-generated body, proposal module or isolated production-package replacement remains in these five callers.

| Diagnostic | Current behavior |
|---|---|
| `probe_all_area_snapshots.py` | Installed endpoint, explicit one-state or decisions-directory mode; depth/candidates/beta may be bounded from CLI. No search is performed by the default endpoint calls. |
| `probe_corrected_prediction_fidelity.py` | One control interval with the declared action and snapshot-only forecast. Recorded future outcomes are read after prediction for comparison. Optional historical prediction CSV remains separately labeled. |
| `probe_direct_branch_order.py` | Physical geometry and one snapshot, plus `sys.settrace` observations of the installed freeway accounting function. |
| `probe_offramp_feedback_trace.py` | Installed endpoint; observation wrappers call original functions with unchanged arguments and return their results. The selected E8 ramp trace now correctly names and reads `R_F_E`; the old diagnostic accidentally read `R_F_W`. This changes the trace label/value, not model flow. |
| `probe_single_transfer_grid.py` | Historical CLI name delegates to the same installed grid driver. It has no separate runtime/body. |

`build_projected(..., fixture_inputs=False)` validates explicit files and uses the offset-writer declaration from that configuration only while constructing the model. The environment is restored afterward. Default `fixture_inputs=True` retains the existing portable-fixture behavior and fixed OFF references. The old `proposal_module()` and its `types` import have no remaining callers and were removed from `probe_sc2001_corridor_replay.py`.

Every probe refuses an already-existing requested output, so the former proposal results are not overwritten. Source fingerprints distinguish the explicit configuration, raw snapshot, previous action, replay action and current production files. These are model replays under the declared final configuration, not claims that the old live n7 run used that model.

Validation: all five CLI entrypoints were imported and executed in separate subprocesses using pure-n7 state1200, actual previous action1050 and (where relevant) actual action1200. Each was restricted to150 seconds; the grid used one candidate and beta0, plus its repeat/copy check. Five checks passed in8.429 seconds on the first run. The existing portable area-coverage/OFF five checks also passed in5.920 seconds; `probe_production_migration_portable_validation.json` preserves that new result separately from the historical phase/follower report. Current run results and input files were fingerprinted unchanged. No VISSIM connection, fullgrid, full search, production edit or runtime-input regeneration was performed.

Reproduce the bounded checks:

```powershell
python -m unittest diagnostics.test_probe_production_migration -v
```

They require the explicitly named pure-n7 state/action and small bottleneck CSV records used by this integration test. They are not part of the minimal receiver-turn fixture. Use each script's `--help` to select other explicit files. Fullgrid execution requires the explicit `--decisions` and a new `--output` path.

Before editing or deleting diagnostic sources,23 existing files were preserved byte-for-byte in `fixtures/diagnostic_proposals_20260910.zip` (58,847 bytes; SHA256 `7f640beb262291b8e2c665885d743bf2855c2f46d73e759a4767f07daa710f01`). Each `raw/<original path>` entry and its size/SHA appears in the companion manifest. The archive includes historical versions of the five probes and shared helpers; archival presence does not mean every archived file was deleted. The earlier52-item inventory already contained37 files no longer present at this task's start.

Only `build_area_projection_coverage.py` was deleted in this task. It had no executable consumers and its old170/45 algorithm was superseded by the reviewed186/29 support data. The exact resolved single-file path, raw SHA, Git commit/blob and byte-identical ZIP recovery are recorded in `retired_projection_builder_audit.json`. Deletion used one nonrecursive PowerShell `Remove-Item -LiteralPath`. The current physical-support JSON, Ω membership, ownership and calibrated inputs remain unchanged.

The remaining11 migration-first artifacts are still required by these historical consumers, so they are retained:

| Retained artifact | Remaining executable consumer |
|---|---|
| `audit_snapshot_readonly.patch` | `test_audit_snapshot_windows.py` fallback |
| `diagnostic_profile.patch` | `test_diagnostic_profile.py` fallback |
| `freeway_count_geometry.patch` | `test_freeway_count_geometry.py` |
| `build_area_routes_and_sc2001_patch.py` | `probe_area_package_runtime.py`, `test_legsplit_receiving.py`, receiving proposal builders |
| `prepare_sc2001_urban_patch.py`, `proposed_area_dynamic_routes.py`, `sc2001_corridor_proposal.py` | The combined route/SC2001 builder |
| `prepare_freeway_initial_count_patch.py` | `probe_all_area_initial.py`, `probe_area_full_decide.py` |
| `prepare_legsplit_receiving_patch.py` | `test_legsplit_receiving.py`, single-transfer proposal builder |
| `prepare_legsplit_single_transfer_patch.py` | `probe_area_full_decide.py` |
| `prepare_area_failfast_patch.py` | `probe_area_full_decide.py` |

Those older consumers have not been relabeled as current production evidence. Their migration can be a separate bounded task. Fixed6056c94/3299040 source references, current runtime data and the four actual diagnostic input generators/tools remain intact.
