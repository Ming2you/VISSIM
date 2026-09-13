# Head service and known W_out integration review

Reviewed after the head patch was applied, before the known-W_out patch was applied. This is a source/install-order review; historical proposal test and endpoint results are not evidence of a combined canonical run.

The regenerated known patch passes `git apply --check` against this head-applied checkout. Apply head first (already done), then this regenerated known patch. The former draft used whole-file CRLF context and could not apply to these LF files; the regenerated patch resolves packaging only. Do not reapply the head patch or overwrite shared files from a proposal snapshot.

| Site | Installed head contract | Pending known W_out contract | Combined ownership |
|---|---|---|---|
| runtime_setup.configure_runtime | Configure proof before observer; observe raw windows; finalize after physical route topology and before local pool configure | Configure/tag initial W_out after projection, corridor initialization and area ledger seed | Head changes the service view only. Known initialization partitions the existing W_out stock without adding vehicles, arrivals or initial entry events. |
| urban_substep_accounted | Per-invocation 10629 resource budget; batch limits before receiving; only actual accepted departures debit the budget | No replacement of this service allocator | The two incoming boundary-out aliases consume one physical 10629 budget. Neither alias receives an independent extra capacity. |
| _receive_corridor | Existing receiver acceptance and stock/event owner retained | Tags only that owner's accepted amount, using the existing arrival/release due time | A head-limited accepted amount becomes exactly one W_out stock transfer and one route receipt. Head does not create or debit route tags. |
| legsplit_substep_accounted | No destination-share or stock change | Request from eligible tags before body; original receiver reconciliation and stock/events; commit accepted receipts afterwards | Existing legsplit remains sole stock/event owner. Rejected destination demand remains tagged to that destination. New same-body receipts are not added to the earlier request plan. |
| schedule_offramp_arrivals_accounted | No direct-admission change | Tags the existing accepted OR_F_E direct landing after its original transfer | No head service debit for a freeway direct landing; no duplicated urban signal service. Future direct destination uses the explicitly declared native single-path prior, not a measured future ID route. |
| local_signal_service | Final cap map and pool groups include independent 10634 and 10629 resources | No local helper changes in this patch | Both resources remain separate even where their phase labels match. Shared 10629 local accepted budget cannot debit known W_out global tag stock. |

The patches overlap by filename in runtime_setup.py and urban_flow_accounting.py, but their hooks are at different functions/sites. The known patch also appends route-choice helpers. It does not replace the head observer, head finalizer, group extension, regular batch limit, or accepted budget debit. Its runtime initialization is later than head finalization and does not alter movement capacities or pool groups.

## Important scope limits

- 10629 support is the verified observed-only floor (1040 veh/h after the seven saved windows), not the legacy seed-max floor. 10619 observed support 784.6154 remains below its existing 826.1224 service and does not raise it. Independent 10634 calibrated service remains unchanged.
- Cold installation using an original action without the new contract namespace intentionally starts observed support at zero. The new canonical contract SHA requires regenerating the private warm history; an old proposal namespace cannot be silently reused.
- Known routes preserve initial destination tags and current aggregate readiness. Historical initial pending is split proportionally across destination classes where per-ID pending correlation is unavailable. It is not recovered physical travel-time knowledge.
- Known W_out ON requires the accounted area scheduler; its configure rejects the unsupported area-OFF combination before mutation. Post-choice unknown routes remain stock/residence and are exposed as incomplete rather than routed by an invented posterior.
- Existing free-leg aggregate exit timing remains unchanged. A larger modeled free share can change modeled area TD, but the patch does not observe the physical 10773/123 exit time or establish an actual throughput improvement.
- Local green/refinement models still have their documented aggregate/frozen W_out receiving and future-off approximations. The known patch does not add destination-tag dynamics to those local plants. This is a local/global fidelity limitation, separate from the accepted-only global ownership reviewed here.
- The head local pool currently supports these two SC1004 resources. Generalization to resources on other signal controllers requires a separate model-view contract.

## Canonical validation order

1. Head-only actual imports: state1 with the actual CLI empty-string previous; separately verify the existing outer-runtime rejection of None and direct head-observer acceptance of None; all seven windows through actual configure_runtime; saved current action metadata carries only verified canonical namespace values. Check final 10629/10619/10634 resource rates and removed phantom movements.
2. Run the canonical urban 5-second method with independent candidate copies, the existing local shared consumer under full/partial/zero GREEN and blocked receiver, actual main builder local cost, and a fresh serialized controller worker. Original-run and Git accesses are denied by the portable verifier. New results use canonical filenames; old proposal result JSONs remain untouched.
3. After root applies known, migrate its tests to actual imports and run its stock/readiness/accepted-only/unknown/worker cases. Add a combined receiving case with both 10629 aliases and ready existing W_out tags: one 10629 accepted budget; pre-body tag plan excludes same-body arrivals; sum tags equals physical W_out after accepted legsplit debit; no extra entry event at initialization. Test a full destination ramp and partial receiver acceptance.
4. Actual main preflight must use the canonical warmed action namespace and final combined configuration. Confirm both pool groups survive worker restore, known route completeness/unknown counts are exposed, and final phase/meter score-to-writer assertions pass. A successful head-only cold-history main run does not establish that its observed 10629 floor was active.

No production/index/config changes, endpoint, full MPC, FZP scan, or VISSIM run were made for this review. Root owns sequential application and subsequent integrated main validation.

## Review fingerprints

Reviewed 2026-09-10T12:15:08.248917+09:00

| File | SHA256 |
|---|---|
| diagnostics/head_service_resources.patch | `e6cd67b617739b2f52ceb8b0e7aa5adaf1c26fbccb8090fc1d7c0d7227938cc8` |
| diagnostics/known_wout_routes.patch | `41e42e5dabdbf6c02416017b7aca701e0b04e9546b1ccd61787f8a28c04d9044` |
| evaluation/controllers/runtime_setup.py | `f71560b0b31b196fcb40bbc1b2eab66210634c4d3376a21716babcec5b9839fc` |
| evaluation/controllers/urban_flow_accounting.py | `7b0e9388fbc6a9a8c7f7bff3665b0406d0b642dc3647037b6e48fd3bfad4c36f` |
| evaluation/controllers/route_choice_corridor.py | `6e616c01ae296d5c49722df37898ff4780d3b9fd999d621808e0007c617e6ae6` |
| evaluation/controllers/local_signal_service.py | `3e1db452f2d6ee929a766a82e0c8459eca4f4e5027c3c8ba7ebc7d2384efdfa5` |
| evaluation/controllers/head_service_resources.py | `5843cb62c36d50602feafbc650e8e2999a8f751039f15e7009bb329c59b5fdc5` |

## Head-only canonical validation now completed

`head_service_resources_canonical_portable_validation.json`: 16 tests passed in 23.124 s (25.251 s including startup), original-run and Git access attempts zero. `head_service_resources_canonical_validation.json` records source_changes=[] and all seven actual configure_runtime windows. 10629 support becomes 1040 at t600 and remains 1040 through t1050; 10619 support stays below its existing rate. Actual main builder local cost and a fresh controller worker both return 16.203408254098534 with the same ready seed and two resource groups.

The initial attempt passed the same warm tests but failed the deliberately broadened outer `previous=None` call before reaching the head helper. Both head-OFF and head-ON fail at existing adapter Path(None), while the actual CLI's empty string succeeds. The first RED JSON/log are preserved with `_first_red`; the final tests record this unsupported outer API explicitly and retain the direct head.observe(None) compatibility test. No production API was widened to obtain a pass.

These are head-only canonical results. They do not certify the pending known-W_out patch or a combined live run.
