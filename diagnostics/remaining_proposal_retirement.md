# Remaining route/receiving proposal retirement

Four diagnostic consumers now use the installed canonical model. Eight obsolete proposal builders/copies were removed only after external executable references reached zero. No production, active configuration, native network, VBS, run input, historical receiving pickle, fixed-source fixture, Git index or live VISSIM process was changed.

|Consumer|Current contract|
|---|---|
|`probe_area_full_decide.py`|Requires explicit config, snapshot, previous action, new output, and either `--prepare-only` or `--decide`. Calls actual adapter `main()` with its original production worker bootstrap. Preparation stops at `decide_with_info`; it does not execute or claim a successful optimizer search.|
|`probe_area_package_runtime.py`|Requires explicit config/state/history/action/new output. Uses `configure_runtime` and the canonical endpoint for one150-second point, repeat installation, and a fresh process calling `install_worker_runtime`; compares objective, area metrics, numerical state and final inventory exactly.|
|`probe_all_area_initial.py`|Requires explicit snapshot/history pairs and a new output. Uses canonical projection without rollout. The supplied config controls exact-count behavior; OFF residuals are reported without silently enabling a proposal.|
|`test_legsplit_receiving.py`|Calls the current production receiving wrapper directly. Only the historical comparison wrapper is loaded from immutable fixed source3299040. It uses the current body's unchanged default path and is explicitly not a replay of the entire historical model.|

All three CLIs reject missing inputs and existing outputs. No isolated production package, source substitution or proposal installation remains. The receiving suite preserves `first_ramp_clip_50548.pkl`: historical loss0.22302305524194777veh, ramp limit153.2veh, rejected stock retained in its original source by production, exact repeat/candidate isolation, and no-competition state/flow equivalence.

Before any existing source was changed, all12 original files were archived byte-for-byte in `fixtures/remaining_route_proposals_20260910.zip`: **30,956 bytes**, SHA256 `81b530e14d95c8b595e0fd81d13feff045b5c9fb499b743e68ece23096c610b7`. Its deterministic ZIP entries contain83,841 original source bytes, and an embedded manifest. The companion `.manifest.json` records every raw length/hash, ZIP member and Git context. CRC and every member's exact original bytes were checked before editing, and again against the eight still-unmodified retirement targets immediately before deletion. All12 were untracked at archive time, so byte-exact ZIP recovery is the authoritative restoration path; no Git-only recovery was assumed.

Deleted exact files, all within the worktree's diagnostics directory:

- `build_area_routes_and_sc2001_patch.py`
- `prepare_sc2001_urban_patch.py`
- `proposed_area_dynamic_routes.py`
- `sc2001_corridor_proposal.py`
- `prepare_freeway_initial_count_patch.py`
- `prepare_legsplit_receiving_patch.py`
- `prepare_legsplit_single_transfer_patch.py`
- `prepare_area_failfast_patch.py`

The audit used an entire-worktree `rg --hidden --no-ignore` scan of Python/PowerShell/VBS/CMD/BAT sources. Before deletion only mutual references inside this set remained. Each exact resolved target was checked for diagnostics containment, file identity and archive hash, then removed with individual `Path.unlink()` calls. No recursive deletion or glob deletion was used. The same executable-source scan afterward returned zero matches. Full paths, hashes, per-file completion and the preserved live-pin comparison are in `remaining_proposal_retirement_audit.json`. Historical Markdown/JSON references remain historical and do not execute the retired tools.

Validation ran against the immutable `fixtures/area_baseline_before_route_choice_beta0.json` with the actual pure-n7 t1200 state/action and t1050 previous action. This validates migration to **current production code under the preserved pre-route-choice baseline settings**, not the newly extended complete-route live model. The first attempted configuration was `route_choice_native_phase_integration_config.json`; it correctly failed for all three CLIs because the old pure-n7 run manifest lacks `urban_input_gate_map`, required by native internal-input provenance. No raw manifest was repaired or supplemented to make it pass. The unsuccessful attempt is preserved separately in `remaining_probe_migration_validation_20260909T214107084301Z.json`.

The accepted run passed **7 tests in51.548 seconds**: three CLI integration checks plus four receiving regressions. Each CLI additionally rejected a repeated output and omitted inputs. Actual main stopped before search/output, used `evaluation.controllers.vissim_stackelberg_adapter.install_price_worker_runtime_patches`, and retained the production bootstrap. Main/repeated/fresh-worker150-second results were exactly equal. Initial projection added no Ω entry and closed stock. The successful report is `remaining_probe_migration_validation_20260909T214254979032Z.json`. Active manifest-pinned files and historical fixture bytes were unchanged before/after tests and deletion. After deletion all three import/help commands passed and the four receiving tests passed again in0.675 seconds. No full optimizer or VISSIM execution occurred.

Reproduce with `python -X utf8 -m unittest diagnostics.test_remaining_probe_migration diagnostics.test_legsplit_receiving -v`; validation reports use unique names and do not overwrite the recorded results. Each migrated CLI documents required inputs with `--help`. The explicit stage/deletion inventory is `remaining_proposal_retirement_stage_paths.json`; nothing has been staged or committed by this task. `test_legsplit_single_transfer.py`, `review_fixtures.py` and fixture README files were left to their assigned owner.
