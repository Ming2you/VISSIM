# Unapplied Ω leader objective patch

**Integration update:** parent authorized application after the completed beta0 comparison. The final objective patch `edf74d9204e764015f00e8bec00ebd90279124da915455e48df780b0dbdadea3` is now applied. The test suite imports the canonical helper/installer directly, with no proposal fallback or source execution. Objective14 plus shared25 tests passed together against the integrated sources. See `objective_shared_production_validation.md/.json` for current source hashes and scope. The preparation narrative and hash table below are historical; the2550 intent/realization correction remains current.

`area_leader_objective.patch` is ready for review. **No production or vendor source was edited.** `git apply --check diagnostics/area_leader_objective.patch` passes against the currently frozen files. The adjacent manifest pins the two existing production targets and new-helper proposal bytes.

The patch has exactly three production targets:

1. New `evaluation/controllers/area_leader_objective.py`, sourced from `diagnostics/area_leader_objective_proposal.py`.
2. `evaluation/controllers/area_runtime.py`: install the helper before the existing endpoint-already-installed return; disable unrequested price/leader/protected-queue objective extras in the enabled endpoint spec. The remaining original objective must equal finite nonnegative TTT exactly, or the run fails for an unknown extra. The final objective and beta comparison table are assigned exactly Omega TTT-beta*TD; applied additional cost is0. No receiving, signal, storage or inventory checks change.
3. `evaluation/controllers/vissim_stackelberg_adapter.py`: only the existing optional terminal-cost installer method, with canonicalization after its final addition and on its empty-state return. Enabled-area terminal application flags become0 while the excluded fitted amount/features remain visible. OFF terms and returned installer metadata retain the original values.

**There are no vendor hunks.** `prepare_area_leader_objective_patch.py` regenerates this unified patch without writing to those production targets. Apply the final generated artifact, not an earlier four/five-file proposal.

## Shared score boundary

`Leader.objective_terms` is installed once at class level and checked at call time. OFF immediately retains original semantics; no weights are rewritten. ON requires a canonical finite follower_ttt endpoint base, excludes the known added target/MFD/boundary/density/ramp/optional terminal contributions, and sets the total exactly to that Ω endpoint objective. Applied penalty fields are0, raw quantities remain, and `leader_excluded_*` plus `leader_control_area_objective_only=1` make the distinction explicit. An unknown extra addition fails instead of silently being accepted.

The terminal instance wrapper can capture an old bound method if installed before the class hook, or wrap the hook if installed later. Its final call to the same idempotent canonicalizer covers both orders, including ON→OFF reuse. The canonicalizer checks the recognized addition sum and never subtracts β again.

## Proxy β omission corrected without changing generic `_predict`

The unpatched `StackelbergWuMeteredController._proxy_score_candidate` calls generic `_predict`, which returns `point.ttt`. In area mode this is Ω TTT **without** the reward, whereas full candidates use `point.objective`. A common cost gate alone would preserve that wrong proxy base.

The helper therefore contains only the enabled proxy method's existing projection and capacity-proportional allocation body, with its score read directly from the canonical endpoint objective. It is installed as a class wrapper; OFF delegates to the original method. The generic `_predict` return contract is unchanged. The local proxy allocation approximation is preserved; this patch does not claim that it equals the optimized follower response.

The enabled full-base wrapper passes the original rollout spec and previous action to the canonical endpoint, returning its objective independently of obsolete far-at-depth-zero switches. The original OFF full-base method remains intact. Full evaluation still performs the same endpoint count; no extra prediction is introduced.

The actual Wu PFO method (`StackelbergWuMeteredController._evaluate_fallback_candidates`) calls the same full-base endpoint and objective terms directly and retains the full diagnostic dictionary. It does not call base `_make_fallback_evaluation`. A focused regression now exercises that actual method, verifies one endpoint response fixture, distinct J/TTT/Nash scalars, the actual zero-target PFO previous action, incumbent/progress metadata and excluded quantities.

Base `_make_fallback_evaluation` and base `_proxy_score_candidate` do not establish Omega score provenance: they use response or current-state approximations, including the DistributedCoordinator proxy. Enabled calls therefore fail explicitly. OFF delegates exactly to the original methods. No extra endpoint or new generic-controller support was added.

## Installation and unsupported scope

All class hooks are installed from the shared main/worker/offline `area_runtime.install` before its existing endpoint shortcut. Class aliases imported before installation see the same modified class objects; fresh worker restoration is covered. There is no instance-global temporary `_predict` replacement, dictionary interception, last-candidate cache, or runtime source execution.

`leader_proxy_near_far=True` remains unsupported for enabled Ω and fails configuration because it adds global far cost outside the endpoint. The current configuration has it absent/false. State-accumulation leader mode is likewise rejected for Ω rather than silently assuming its scalar is an endpoint score. Supported selection consumers are the Wu full, Wu proxy and Wu PFO paths. Generic base proxy/fallback and DistributedCoordinator selection are not promoted to Omega support. Existing follower local/price response approximations and guard/quantization constraints remain separate from this outer objective correction.

## Focused validation

Command: `python -X utf8 -m unittest diagnostics.test_area_leader_objective -v`.

**14 tests pass**, with no endpoint rollout, full optimizer or VISSIM execution. Tests use actual original leader/consumer methods, and compile only the terminal/shared-install method nodes with their small pending hunks. Endpoint values in call-path tests are explicit response fixtures; they do not claim a new physical prediction.

Coverage includes original OFF dictionary equality with nonzero weights and state-accumulation mode; ON positive density/MFD/boundary/ramp/target exclusions; unchanged config/state/action pickles; negative ΩJ without double reward; terminal-before/after installation and empty-state/OFF reuse; actual Wu full/proxy/PFO consumers and fail-closed unsupported base consumers; worker pickle restoration and imported class aliases; a preinstalled-endpoint install order; unknown leader-cost and exact endpoint-purity rejection; and the real saved1200 comparator for β0/60/150/300. The proxy test explicitly shows the old method returning TTT30 while the proposed method returns J−20 from the same response fixture.

Production remains intentionally unpatched: the old saved1200 leader surrogate ranks the reopening worse, and the existing proxy still omits β. The passing suite currently tests the **pending proposal**, not a claim that live production is fixed. After application the test file detects the canonical helper path and automatically uses actual production helper/terminal/install functions; it does not reapply source hunks. Rerun the focused suite, then perform the root-managed actual main preflight. Its selected full or fallback record should carry `leader_control_area_objective_only=1`, zero applied legacy penalties and inspectable excluded values before any new VISSIM arm.

## Separate live2550 intent versus physical realization contract

`meter_budget_2550.json` independently pins actual2550 JSON/CSV/raw. Intent5787.918681 is raised by the observed guard on DW42 stopped and FE30 stopped (threshold8); requests after guard are1800×4=7200. The table writes DW1879.2/FW1763.672201/DE1800/FE1800, yielding **7242.872201**,42.872201 above the7200 intent search upper bound and DW79.2 above its1800 grouped request limit. Physical greens are DW4/5,FW10/4,DE10/10,FE10/10. These are command/table equivalent rates, not measured vehicle flow. The final action scalar correctly equals their sum.

This numerical difference does **not establish a physical-feasibility violation**. The existing meter-finalization contract permits observed guard releases and discrete table realization to differ from the continuous intent. The7200/1800 search limits have not been proved to be hard constraints on the final equivalent physical rates, and a fully-open rate can also be a demand-limited equivalent value. The former handoff's confirmed-violation interpretation is withdrawn; its numerical evidence is unchanged.

The objective patch leaves that intent/realization contract intact. Any later discrete-feasibility change must first specify whether each bound constrains intent, the realized schedule, or both, and how mandatory guard releases interact with it. Only then can the actual2550 case test that declared contract. Preserve the same scored physical schedule through the writer; clipping only its scalar equivalent rate would break that identity. No new table, guard floor or physical-capacity claim is proposed here.

Final bounded validation after peer fixes: 14 tests PASS in1.201s, `git apply --check` PASS. No physical endpoint, full optimizer or VISSIM was executed; endpoint call-path tests use explicit response fixtures. The two existing production targets retain their manifest source hashes.
