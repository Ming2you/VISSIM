# Obsolete diagnostic artifact cleanup

Removed exactly the 34 approved removable artifacts and the 3 now-integrated meter artifacts: **37 files, 322,181 bytes**. No production file, runtime input, configuration, calibration, fixed OFF reference or run evidence was removed. The 11 migration-first artifacts and four retained diagnostic tools remain. All 19 explicitly protected files exist and have unchanged SHA256 values.

The independent review searched 1,865 current code/config files for exact filenames and Python module stems. No executable reader remains outside the deletion set. References in retained builders are output producers or historical print/doc text; the audit classifier has a filename pattern. Remaining JSON mentions are historical audit manifests. Manual/dynamically constructed reuse cannot be excluded by static search, but the current production/test paths use the integrated modules.

Meter artifacts were released because production commit `bc9078efbfea5a0ace2354a9bcadb88fd7492221` includes the six-file integration and `area_final_preflight_results.json` records successful actual-main score/writer alignment. After deletion, the actual phase/follower/meter regression suite passes **18 tests in 0.769 seconds**. This cleanup does not claim that the later live coverage failure is resolved.

## Recovery and timing

The request for a deterministic archive arrived after the authorized 37 unlinks had completed. A bounded Git-object and existing-workspace recovery search was then performed. **Only three files were recovered with raw SHA256 and byte length identical to their pre-deletion values.** `retired_diagnostic_sources.zip` is explicitly a partial recovery archive: it contains those three members, with fixed ZIP metadata, verified CRC and verified member SHA256. It is not a complete 37-file backup.

The other **34 original byte sequences are unavailable** from that bounded search. The tracked lever patch has an exact normalized Git text reference, but its original mixed line endings cannot be recovered byte-for-byte and were not replaced by a near-match. The manifest distinguishes original raw hashes, normalized Git references and functional production recovery references. The untracked obsolete generators/patches had no original committed blob. Production implementation and historical result manifests remain available.

|Exact archive member|Recovery source|
|---|---|
|diagnostics/area_follower_objective_candidate.py|Git blob `68936196a1e5e9d502c77ec47240f9b270b23384`; git_raw_blob|
|diagnostics/area_phase_finalization_candidate.py|Git blob `d610cd3530ce52d565fefb00b4a122b2644d5669`; git_LF_to_CRLF_with_exact_original_sha256|
|diagnostics/area_meter_finalization_candidate.py|Git blob `61c20257c844e319e5a9e3b027bcbe7fc68ad06c`; git_raw_blob|

Archive SHA256: `edadf174768dc3f7745c61457b0549a769812b8f34f98e90864c515a61356c2b`.

## Exact deletion list

|Path|Tracked|Raw bytes|Raw SHA256|
|---|---|---:|---|
|diagnostics/archive_simulation_errors.patch|no|1090|`8e264f5c9657512427f308ed831371209d7afc231ac0050a604d342ff51823ae`|
|diagnostics/area_failfast.patch|no|1148|`7c3baccf7e21f3a053d76848e877ba151e2cf14c840a44b4f2c6d0af85fc47c1`|
|diagnostics/area_follower_objective.patch|no|7014|`9b5fdd561052d14ab4fb49035b711cd970e9695536ef23bb64d1bb099dd2e525`|
|diagnostics/area_follower_objective_candidate.py|no|5790|`6aef2cd378a9c61a9ee7d5a88a49acd2ba360926231e256e90b1a4717cbd557c`|
|diagnostics/prepare_area_follower_objective.py|no|2257|`652725885280237e7f0b1c1e9a07995ee49707087ace219a3601a53e34930389`|
|diagnostics/area_phase_finalization.patch|no|5276|`cc783a3fb2c73e4fe906fc28502b2bd03376ad7a08c79c2d30ea0551afa23d2a`|
|diagnostics/area_phase_finalization_candidate.py|no|10401|`81830036f2332fca80ceb342035f0b509b3d11494c36034537b2377c34733b60`|
|diagnostics/prepare_phase_finalization.py|no|5903|`4f30553f2f8cf7a1424443b9399ab19877e41cf4b1897758f6a3b9112d046f00`|
|diagnostics/area_routes_and_sc2001.patch|no|41939|`1e830bed364030315195d2165ba8a83d8ad8e6f6fc810e4ad1db3cd3fd8efbba`|
|diagnostics/build_dynamic_area_runtime_patch.py|no|2328|`0c1ccad03dc085d2b211c074c85c242072804a078745beaf8e3f4ad0394685be`|
|diagnostics/build_offset_experiment_patch.py|no|13246|`14f2cfbae9e428236884d40cf3ac2c790368c0cbc3f9ccae000774096c77e73c`|
|diagnostics/build_signal_contract_patch.py|no|5721|`0bd90afdb60e52f61037a1a269e35fb75b60e454a0eef6cee9743e4b83eee294`|
|diagnostics/build_urban_flow_accounting.py|no|8801|`7610447f6397cc4817f72bc90ec74c512132b44bfb719b860dd3df5adb35be0b`|
|diagnostics/diagnostic_lever_profiles.patch|yes|12122|`2d96d009accaff5b75e448caef3b7dcc0dd3d7cfdb0e7f53242e917c594a5542`|
|diagnostics/diagnostic_signal_profile.patch|no|3982|`255570f534290811477b79783ed2a4cab26172939fe27a837520c6026eee8452`|
|diagnostics/direct_branch_receiving.patch|no|1345|`99a0ade94c59408b71b64513c7a440b561c9b965dd2483e958ae727e3df77f6e`|
|diagnostics/dynamic_area_runtime.patch|no|11231|`604cdd2de22a8a9729b411720a5c8296672c66dc5181ea9b397e58eb9330ebf1`|
|diagnostics/freeway_initial_count.patch|no|2984|`aee19081bb41c2f92e308c5ded9ca987069961a7afeadf3af16a242ca41ecfcc`|
|diagnostics/legsplit_receiving.patch|no|2382|`0ec82c7a86d0f873105cb3e66b3e6c290ddcfaf24ad3816da8bdec37ad93c5a3`|
|diagnostics/legsplit_single_transfer.patch|no|7985|`c0f02e8fdf5b6490c45fbcfefb16275d0c32777fd6dabb2780ef59af3515806b`|
|diagnostics/native_fixed_selector.patch|no|2621|`46c1fc7b415c854f83adade427d1d360bdd8d73f32e6baf1d0de9c8b85399d2f`|
|diagnostics/observation_projection.patch|no|4092|`80302f695d56fb5bf8e6bb1ffae9ac1d09e247edc66b661253098387e4f2c3b4`|
|diagnostics/offset_experiment.patch|no|17886|`d147decdbe3eb6ac881fd14494bad64d6f19913d3abadd73232ac1bf9e73c8da`|
|diagnostics/physical_stock_provenance.patch|no|3530|`3a1b8051b003938049a90f683b15b3861da18f5444b613e59b12f1768d0e69e8`|
|diagnostics/prepare_observation_projection.py|no|10719|`9f0a762c22a6eff216fed5d64512a6c9e78e7341c522e0b682d4f570b280a4cd`|
|diagnostics/prepare_transit_storage_projection.py|no|981|`6826233171595318b244a881e31f1e55c8cd599e0a01ccfb9655fa0ba1318bff`|
|diagnostics/prepare_strict_decision_failfast.py|no|4990|`879e68c89566b3dec9c23358175c0ef157b2f2d7b39a2409edf4be5dd6ad28fa`|
|diagnostics/runtime_setup.patch|no|16509|`543b4b1733774639336de49ea6d6bfeb762edd53110274b861e02bf7bc3e569c`|
|diagnostics/sc2001_urban_flow_accounting.patch|no|6595|`b95671bfa47be6ff76bb44fca8796e8132971ccaf868080e0c317dd6ea3bd77c`|
|diagnostics/signal_actuation_contract.patch|no|20657|`44c95535066918bd1ee0511c357b94e6f5b42468ab7fecd62ec38eb272ee6668`|
|diagnostics/signal_actuation_contract_candidate.py|no|16026|`dad1405b021e54c0235c333904f6093060a9ddb6008689b1ba53d2feb6b94b10`|
|diagnostics/signal_contract_with_offset_experiment.patch|no|35780|`e4f96a97fd109892ee4be535641d9449f39a950367aa00357a38756b6f65b642`|
|diagnostics/strict_decision_failfast.patch|no|3817|`f0b7bbf47ac0934930cc856397151d991b64dfb0dae531ae6bc1fcc0ed43d3bd`|
|diagnostics/transit_storage_projection.patch|no|1750|`21c9dcccee28d84419f5d7c5f3cc82ff8a3ab0f26429d9a32dd138b7de7b4555`|
|diagnostics/area_meter_finalization.patch|no|11747|`6650dce38abb61debd1c90272fc2b132d2ba9e375fa95eb4c681b497d74b05cc`|
|diagnostics/area_meter_finalization_candidate.py|no|7119|`cb8c24cc9be689a2ebceac7d12693730eb67908b29c3ded9984657854d509162`|
|diagnostics/prepare_meter_finalization.py|no|4417|`351f996ba83f9f021c1c4a6f6be104e651af15842cc0a349f71896232ffcecb0`|

Every deletion used Python `Path.unlink()` only after resolving the full explicit set and checking that each regular, nonsymlink file was a direct child of this worktree diagnostics directory, outside the protected set, with matching pre-reviewed SHA256 and mtime. No recursive or glob deletion was used. The execution JSON records individual deletion state, canonical commit/path references, surviving mentions, archive availability and protected-file hashes.

## Staging handoff

No staging or commit was performed. `diagnostic_cleanup_stage_paths.json` lists the single tracked deletion and the audit/archive additions for an explicit root commit. The other 36 deletions were untracked working artifacts and therefore do not appear as Git deletion entries. Keep the original `diagnostic_cleanup_actions` files as the historical proposal; this execution record supersedes their old pending meter classification.
