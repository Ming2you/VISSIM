# Portable shared service and landing-clock inputs

`shared_service_v1.zip` contains four exact historical inputs, **226,523 bytes**, SHA256`8313b2266987b8c203056f0d6ab5a4fab46c6cd7b8580a907a2319784d3d4d46`. The ZIP CRC and every member's byte equality were checked at creation. `index.json` and companion `shared_service_v1.manifest.json` retain individual raw lengths and SHA256.

| Raw input | Bytes | Purpose |
|---|---:|---|
| state_000900.json |728991| Actual initial state and vehicle/route observations |
| action_000750.json |308301| Actual preceding observation/actuation context |
| action_000900.json |371675| Held physical command for the bounded local tests |
| run_provenance_codex_area_sources_beta0_s13_20260910.json |39192| Manifest actually read by native_internal_input.configure |

These are from `codex_area_sources_beta0_s13_20260910`. References to older state/actions or FZP inside historical diagnostics are preserved but are not executed or silently fetched. No production module, runtime config, network, calibration or FZP copy is included. The tests still require the current checked-out dependencies and their existing pinned data.

`diagnostics.shared_service_fixtures.input_path` always resolves these three test JSONs from the archive. Without environment setup it restores once per process into a fresh short `.review-fixtures/sp_<id>` path. With `VISSIM_SHARED_SERVICE_FIXTURE_ROOT`, it requires a verified existing restoration. It never falls back to the original ignored run. Unknown/missing records and changed restored fingerprints fail. The existing `review_fixtures.restore` performs containment, archive/index/member validation and whole-string path relocation. Raw copies retain original bytes; relocated JSON copies change only absolute workspace aliases, recording all changes in `restoration.json`. Traffic values, controls, IDs and historical source SHA fields remain unchanged.

Reproduce the isolated regression with:

```text
python -X utf8 -m diagnostics.run_shared_service_fixture_tests
```

The final execution passed **30 actual-import tests** (shared25 and clock5) in7.314 seconds. A temporary sitecustomize installs the same read/listing and Git-subprocess denial in the test process and each of its three fresh Python workers. All four process audit records show zero forbidden accesses. The134 source pins, four config outputs and contract manifest remained unchanged. See `diagnostics/shared_service_fixture_validation.json/.log`. This is a fresh restore with denied original inputs, not a new operating-system or dependency-install validation.

The regular test command also auto-restores these inputs:

```text
python -X utf8 -m unittest diagnostics.test_shared_service_pool diagnostics.test_local_landing_clock diagnostics.test_local_landing_clock_receiving -v
```

Only archive creation requires the old run: `python -X utf8 -m diagnostics.build_shared_service_fixture_archive`. Creation refuses to overwrite an existing ZIP/manifest. Ordinary tests do not import the archive builder. Restored directories are disposable ignored fixtures; no existing directory is recursively removed or replaced. The original archive families and their historical validation evidence are unchanged.
