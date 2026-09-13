# Shared10634 service proposal: independent review

**Three boundary defects need correction before application.** The common accepted-only service arithmetic is sound for the reviewed closed group. The findings below concern the new opt-in's input validation, reusable configuration and refinement cache. The author has accepted all three fixes. No production file was changed and no endpoint, optimizer or VISSIM was run.

The reviewed patch hash and exact results are in `review_shared_service_pool_edges.json`; `review_shared_service_pool_edges.py` loads the exact proposed patch with its isolated test harness. One urban service step plus refinement input preparation took 1.90 seconds. Its watched source hashes were unchanged. Existing 12 tests were read, rather than treated as an independent proof by merely rerunning them.

| Finding | Reproduction | Required correction |
|---|---|---|
| Missing physical GREEN profiles silently become cycle averages | New `local_signal_service.py` lines154,166–172 rejects `None`, but accepts `{}`. Actual900 three target fractions are1; the empty dictionary silently uses66.333/150=.44222. Accepted service changes .860544218→.380549864veh without error. | Validate every pooled movement has a profile of the full requested length, with finite values in[0,1]. Preserve absence semantics for unrelated legacy signals. Add empty/all-missing/partial/truncated/nonfinite tests. |
| New ramp refinement can reuse stale stock inputs | New context wrapper lines355–359 delegates inherited cache. Vendor `priced_wu_link_controller.py`225–235 keys time, demand identity and action vectors, not state stocks or mutable Wu coupling caches. Same-time state.copy with OR_F_W10→9veh returns the identical setup with10; a fresh agent correctly sees9. | Rebuild the context in the ON branch, or use a complete dependency key. Existing OFF cache remains exact. Test altered copied stock and altered coupling cache, while an ordinary repeated unchanged call remains deterministic. |
| Public OFF configuration does not turn an already configured view off | `configure`24–25 returns{} for explicitFalse while `cfg.network.local_service_pool` remains. Cost remains .0785525321 instead of original .0761621315. Existing test manually deletes the attribute and therefore misses the public lifecycle. | Remove only the module-owned view on OFF, or explicitly reject unsupported reconfiguration. Test ON→configureFalse→original callable/result equality. Do not uninstall the global wrapper needed by other ON cfg objects. |

These are input/lifecycle counterexamples, not evidence that the actual900 closed-group fixture already used stale or absent inputs. Initial absent-flag configuration still delegates to the original function. Current main configuration is built fresh per decision, so ON→OFF reuse is a library/worker safety boundary.

## What is correct in the narrow contract

- The service limit has vehicle units: one rate×urban timestep×physical GREEN fraction. It is not the sum of three independently available capacities.
- `limit_one` and `limit_batch` do not consume service; `accepted` debits only the receiving allocator's accepted vehicle count. The global route corridor keeps its existing single `service_limit_veh`/`service_used_veh` dictionaries; it does not add a second reservation ledger.
- The local off-ramp order is changed to `net.off_ramps`, matching the canonical global loop. OffW precedes offE, then ordinary W. Source starvation under that priority is inherited policy, not a new proportional-allocation claim.
- All three members must have the same SC1004/p3, receiver and rate and must be present in the same LocalSignalModel. Thus current regular batch grouping by receiver cannot divide one pool between two receiver allocations. A future multi-receiver group is deliberately rejected at configure time.
- The local receiver balance is separate from the shared service budget. Within one substep, accepted off-ramp flow reduces the pooled receiver operand before the ordinary queue competes for the remainder. Receiver rejection does not consume the unused pool.
- Candidate used counters are local function dictionaries and reset each substep. The worker reinstalls static group views and callable hooks; no used budget is pickled. Both local-signal and imported Wu aliases are wrapped. The patch touches no vendor file.
- Actual SC1004 `apply_phase_price_refinement` is connected through setup/cost hooks to the same ramp-aware pool and vector clock. The setup explicitly removes off-ramp arrivals from ordinary queue arrivals before advancing OR stock. This closes the former `has_ramps`→drain-proxy path. It does not prove all entire-horizon local stocks equal the coupled model.

## Inherited limitations: keep distinct from fixed pool arithmetic

The readiness boundary still differs. Canonical `urban_flow_accounting.py`79–80 subtracts pending off-ramp transit from service availability. The local `_offramp_occupancy` getter (`wu_faithful_follower.py`589–596) returns full stock; the new refinement setup line330 uses it unchanged. A synthetic existing10veh OR_F_W cohort due next step makes global service allocate .860544218veh to offE, while local service allocates the same total to offW. No extra physical stock was created. The independent JSON preserves both receipt vectors.

This is an inherited local availability approximation, not a new pool overspend. A later readiness repair must keep pending vehicles in TTT stock and subtract them only from ready-to-depart availability, using existing due-step metadata. Setting initial stock to ready stock would lose residence accounting. Any statement of local/global agreement must presently require matched **ready** source availability.

Likewise the pooled external receiver's frozen available space is renewed every local substep; only same-substep competition is newly conserved. It is not a finite dynamic downstream-storage rollout. Existing off-ramp inflow is still capped locally without a rejected-inflow source ledger. Those are documented local-model limitations and do not justify expanding this small patch into a new plant.

The physical GREEN profile helper used by the actual solver normally populates all movement keys, so the new validation should be cheap and fail closed. The actual GNE phase-vector wrapper also has an existing catch-and-diagnostic path (`priced_wu_link_controller.py`684–695); preflight must still require its error count to be zero if that optional path is enabled. The direct refinement test does not establish that every optional controller mode propagates exceptions identically.

## Application gate

Apply only after the three new regressions pass against the revised patch. Then run the already requested actual main preflight with shared-pool opt-in, zero GNE/refinement errors and clean worker restore. No full optimizer was run for this independent review. Retain the distinction between corrected shared-capacity use, inherited availability/downstream approximations, and capacity calibration.
