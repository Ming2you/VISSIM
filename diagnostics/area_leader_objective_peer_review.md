# Independent review of the pending Ω leader objective patch

**Resolution after this review:** root authorized proposal-only fixes. Both issues below are now addressed: unsupported base proxy/fallback fail closed and the actual Wu PFO method has a focused regression. Root also requested strict endpoint purity: unknown residual extras now fail; final J/additional-cost/beta-table values are explicitly pure Omega. Final proposal suite14 PASS (1.201s), patch applicability PASS, production unchanged. The reviewed hashes and findings below describe the earlier artifact and remain as historical evidence.

The active Wu full/PFO path is connected to the proposed endpoint score correctly by inspection. Two gaps should be closed before claiming the entire leader surface supports Ω: the test does not exercise the actual Wu PFO method, and unsupported base/DistributedCoordinator consumers can currently label a non-Ω scalar as an Ω endpoint score. No production files, model endpoint, optimizer or VISSIM were executed or changed for this review.

Reviewed artifact SHA256:

| Artifact | SHA256 |
|---|---|
| area_leader_objective.patch | d38f3fcebe1484b61fcbbeba0d542ae446e3cad224de37470f47254865fbd079 |
| area_leader_objective_proposal.py | ceb50c26a823e7cd73bb60901e7f8122d4a3b742e129ba883bf753d5e2c3efb9 |
| test_area_leader_objective.py | 739351acd0248df245cde44d50feb9332dfb10ae94e8066f8562b3b7ffd82274 |

These are reviewed proposal bytes, not a production integration claim. The author may subsequently supersede them.

## Actionable issues

**1. Explicitly reject or separately support non-Wu score consumers.** `validate_config` (proposal:21) checks `objective_mode` and the direct far flag, but cannot establish that its scalar came from an Ω endpoint. Installation patches `Leader.objective_terms` for all Leader instances. The base `StackelbergMPCController._proxy_score_candidate` (vendor `stackelberg_mpc.py:1932`) remains unchanged: its non-Distributed branch uses current whole-network stock times horizon; its DistributedCoordinator branch uses `_response_tts_objective`. The latter (`distributed_coordinator.py:3826`) is a separate service/terminal-stock approximation, not an Ω ledger endpoint. Both scalars can now pass canonicalization and receive `leader_control_area_objective_only=1`.

Similarly, the base `_make_fallback_evaluation` (`stackelberg_mpc.py:1866`) feeds `nash.objective_value` on repeated current-state copies directly into the cost gate. The proposed wrapper (proposal:159) retains diagnostics but does not validate or replace that score source. This is harmless for the active Wu PFO path because it does not call this base method. It is not proof that base fallback or DistributedCoordinator now supports Ω.

Minimal scope repair: retain the active Wu class hooks, and make unsupported base proxy/base fallback invocations fail explicitly in enabled Ω mode unless a separately tested canonical score contract is supplied. Alternatively, add a controller-install gate restricting this feature to the tested Wu controller/follower combination. A scalar with a `follower_ttt` configuration name is insufficient score provenance. Keep OFF consumers unchanged. The handoff should state this support boundary, not only the already rejected `leader_proxy_near_far` and state-accumulation modes.

**2. Test the actual active Wu PFO method.** `test_real_full_proxy_fallback_consumers_return_same_endpoint_score_once` (`test_area_leader_objective.py:116`) replaces the instance `_leader_evaluation_base` with a lambda at line126 and calls base `_make_fallback_evaluation` at line135. It therefore cannot catch a break in the active fallback path despite its test name. The separate base test at line139 confirms the proposed endpoint scalar accessor, but not its composition with Wu PFO, passed previous action, or metadata retention.

A bounded regression can call the actual `StackelbergWuMeteredController._evaluate_fallback_candidates` with explicit follower-result and endpoint-response fixtures. No physical rollout is needed. Leave the actual `_leader_evaluation_base` method installed, make `_make_fallback_evaluation` raise if reached, and verify:

1. Exactly one endpoint response is requested for the candidate, and its `objective=-20` wins over a deliberately distinct fixture `ttt=30`/`nash.objective_value=99`.
2. `pfo_previous` has the actual existing zeroed leader targets and empty allocation; it is passed to `_leader_evaluation_base`/`walk_previous`. The leader penalty call still receives the original previous control, as the vendor method specifies.
3. The candidate, incumbent cache and progress event all use the same `-20` objective, retain `leader_control_area_objective_only=1` and excluded quantities, and keep the candidate's control dictionary consistent.
4. OFF retains the original method result and does not add a new score-source invocation. An enabled unsupported base proxy/fallback is rejected, not marked as Ω.

The terminal tests cover installation before/after the class hook, empty states and ON→OFF. They do not establish arbitrary repeated terminal-wrapper installation on the same instance; that should not be claimed as covered. The active adapter branches create a controller and install its terminal wrapper once (`vissim_stackelberg_adapter.py:12636`/12642 for wu-link), so no active repeated-install defect is established here.

## Verified active call path

| Consumer | Actual source | Assessment |
|---|---|---|
| Wu full candidate | inherited full evaluation → patched `_leader_evaluation_base` → endpoint `point.objective` → patched `Leader.objective_terms` | Code path uses Ω once; no second β subtraction. |
| Wu proxy | patched Wu `_proxy_score_candidate` → endpoint `point.objective` | Corrects old `_predict` returning `point.ttt`; preserves the existing meter-only response approximation. |
| Wu PFO fallback | `stackelberg_wu_metered.py:2155`, base call at2175, terms call at2182 | Uses the same patched base and terms as full candidates. Stores the complete returned terms dictionary, so excluded fields are not dropped. |
| Base fallback / base proxy / DistributedCoordinator | current-state or response proxy scalar | Not established as Ω; require the explicit support boundary above. |

The active Wu PFO method constructs `pfo_nash`, maps the existing equivalent leader action, then executes `_leader_evaluation_base` and `objective_terms` directly. It never depends on the proposed base-fallback diagnostic-retention wrapper. No missing hook on this active method was found by inspection.

## Objective, constraint and numerical checks

The endpoint changes `price_hinge=False`, `leader_hinge=False` and `protected_queue=False` affect additive soft cost calculations after `_rollout` returns (`rollout_endpoint.py:383`–419). The protected-queue component is a weighted excess sum (`:341`); it is not a stock cap or receiving allocator. This patch does not alter `apply_action_schedule`, `_rollout`, signal-clock/green feasibility, accepted-flow equations, route reservations, finite storage, or the final `closing.assert_stocks` check in `area_runtime`. Disabling these extras therefore does not delete a physical acceptance constraint. Existing follower local penalties and the separate fallback terminal/completion guards remain; an unqualified claim that every internal decision minimizes only J would still be too broad.

`Leader.objective_terms` currently adds exactly the five ordinary penalties listed in `APPLIED_LEGACY_COSTS`; the optional terminal wrapper adds the sixth. The canonicalizer verifies that recognized sum, retains excluded values and sets total exactly to the endpoint scalar. A second canonicalization of an already normalized dictionary adds zero applied costs, so the intended final-boundary operation is idempotent. The terminal wrapper's final canonicalization handles its capture of the old bound method when installed before the class hook. OFF returns the original terms object and retains configured weights.

Negative J is not clipped and β is not re-applied. The existing objective fallback comparator uses additive differences and `abs(fallback_obj)` for its secondary required-gain scale (`stackelberg_mpc.py:1648`–1652), avoiding a sign reversal from multiplying a negative objective. Terminal/completion severe rejection remains intentional and separate. The already installed area follower runtime disables the obsolete rollout-TTT guard branch.

`leader_follower_ttt_base` and proxy `follower_ttt` retain legacy field names while holding J, which may be negative (proposal:64/125). This is not negative physical TTT. Keep the distinction explicit in analysis and preferably add a clearly named Ω objective field; actual Ω TTT/TD remain in endpoint/follower metrics. The handoff currently explains the endpoint objective but should not present these legacy-named scalars as measured or predicted TTT.

This review is source/call-path analysis. It does not claim that the pending tests ran against integrated production, that a new candidate physical prediction was produced, or that existing proxy approximations were calibrated.
