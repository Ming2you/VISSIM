# Pending observer integration and test migration

Status: **implemented after root authorized application**. The historical plan below was executed; current evidence is `signal_observation_integration_validation.json`. Actual-import11tests and installed complete-script syntax passed. Root still owns active config/Git and real VISSIM smoke.

## Exact production scope after authorization

Apply the reviewed `diagnostics/signal_observation_window.patch` to exactly four paths:

- `scripts/run_real_world_stackelberg_controller.vbs`
- `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`
- `evaluation/controllers/vissim_stackelberg_adapter.py`
- New `evaluation/controllers/signal_head_observation.py`

First compare all three current raw source hashes against `signal_observation_window_patch_manifest.json` and re-run apply-check. Stop on unexpected drift and report the exact file; do not automatically rebase a changed proposal. Configs/runtime evidence/manifests remain root-owned. The absent config keeps the existing execution path; no active option will be enabled by the application itself.

## Actual-code harness migration

Migrate `diagnostics/test_signal_observation_window_patch.py` in place so existing test commands remain usable:

1. Replace `proposed_sources()` with an explicit reader of the current installed VBS/watchdog/adapter/helper files. Remove patch parsing and patch-base preconditions from executable tests.
2. Import `evaluation.controllers.signal_head_observation` normally. Do not compile a proposal string into a fake module. Retain the physical fake input fixtures and real provenance validation.
3. Extract exact current VBS procedures for fake-COM execution, and exact current PowerShell config functions for config-only execution. This retains the safety boundary: no simulator creation, no watchdog body or full runtime execution in unit tests.
4. Preserve the OFF equivalence test using the immutable Git baseline `109afeef5da0fded77b6b68848d271a68743933e`, via `diagnostics.fixed_source_reference.source_at(commit,path)`. Its adapter AST was verified equal to the current pre-application production adapter on2026-09-10. Compare that fixed original installer against the installed installer with only the two documented opt-in guards removed. Do not use current production as its own before/after reference.
5. Keep the eleven focused assertions: same-run/source-only prior carry, foreign/future/overlap rejection, invalid-held ownership across reset, physical bypass/duplicate exclusion, exact clock/cadence, same-timestamp bulk cache, no-member updates0, quality rules, ON/OFF config transport, and publish-before-reset order. Add a direct installed adapter dispatch check if its small existing fixture is sufficient; do not stub the new finalizer or invent markers.
6. Verify the complete installed VBS syntax with the same Option Explicit followed immediately by WScript.Quit0 compile-only temporary script, plus duplicate-declaration negative control; parse the entire installed PowerShell with Parser.ParseFile. Root owns the subsequent real VISSIM smoke and performance/cadence acceptance.

## Provenance and reporting

Keep the unapplied patch, old validation and capture outputs as historical evidence. Write a new integration validation record with before/after raw SHA, exact applied paths, installed-module source path, test results and syntax results. Update handoff status only after application and actual tests pass. Any old statement of fake/proposal validation remains historical and must not be relabeled as an actual simulator test.
