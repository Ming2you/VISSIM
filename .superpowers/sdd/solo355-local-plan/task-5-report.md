# Task 5 report: own-information production context

Status: implemented and qualified at the saved-input adapter/optimizer/writer boundary. Code/config/test/evidence commit `886f82b` on `codex/solo355-local-information`, based on `218d7b1`. This report is committed separately. No native run, freeze, queue creation, dispatch or push was performed. Parent retains the final review/preflight/dispatch decision.

## Result and scope

Both opt-in configurations now prepare a disjoint own-information decision graph before the canonical `sdmpc.solve` call. Mandatory full saved900 selections completed feasibly after the input isolation gate passed. They used the existing distributed owner solver/PFO/leader/search policies and restored original eight reverse workers. Both returned `best_observed_feasible_sdmpc`, `converged:false`; this is not an optimality/GNE certificate or evidence of native traffic improvement.

| Mode | Held objective veh h | Selected objective veh h | Selection wall seconds | Approximate scalar / AD rollouts | Executable VSL secant rows | RM neighbor predictions |
|---|---:|---:|---:|---:|---:|---:|
| freeway_only | 190.12384806062906 | 189.27754227640241 | 180.6188145 | 144 / 10 | 118 | 22 |
| urban_only | 239.07617641664146 | 234.06544106057717 | 62.6223915 | 1 / 9 | 0 | 0 |

FW had 240 gradient rows over five derivative points: 122 compiled reverse active-path rows and 118 configured `inactive_vsl_legal_step` executable secant rows. Urban had 378 compiled reverse rows over two derivative points, with no executable secant fallback. AD receipts themselves had all axes and empty AD fallback reasons. FW evaluated finite RM neighbors for two distinct budget incumbents and selected `combined_meter_owners`; urban had three budget incumbents with no active RM neighbors. Finite audits are not exhaustive. The approximate-query totals were 154 and 10 predictions; exact-execution rollout and independent-AD-witness counts in these selections were zero. Earlier separate numerical/AD/conservation qualifications remain checkpoint evidence.

All three planned blocks passed the canonical physical command checks (213 ordered rows per block), fixed inactive actuator scope, actual move-box checks, regional model witness and quantity constraints. The final action JSON and CSV passed both prewrite binding and written-command binding. Whole-region owner plus PASSIVE cost sums had residuals 0 FW and 1.14e-13 urban. Active owners were FW_W/FW_E or the seventeen urban SC owners. Passive local residence was 5.918e-16 and 144.9088126479578 veh h respectively. `final_check_complete:false` and quantity-only `physical_feasibility_certified:false` retain their existing meanings: no exhaustive finite-game certificate, and quantities alone do not certify physics. The actual model witness and command checks are separate and passed. Native application was not tested.

## Source changes

- New `evaluation/controllers/sdmpc_regional_context.py` copies declared dataclass configuration fields and explicitly allowed installed static/own fields. It removes top-level and every nested freeway runtime config's live meter raw/history/spillback payload, preserves static actuation/mapping, sanitizes observed urban schema fields in FW mode, projects forecast and state, freezes local boundary requests, and reconstructs follower/leader instances without previous response or coordination caches. Full local graph includes nested configs, state, forecast, reference/history, bounds and callback context.
- Historical physical commands are checked before copying. Inactive target budgets and remote diagnostics/allocation/infeasibility are removed; own active physical commands and actual physical-ramp CSV provenance remain. Old integrated4500 history continues to fail inactive guards rather than being silently rewritten.
- Bootstrap retains only static network path, detector origin/owned-leg mapping and runtime source provenance. The regional callback fingerprint hashes the full prepared context without adapter uppercase mutable caches. Ordinary callbacks retain the previous fingerprint behavior.
- `sdmpc.configure` exposes only `adapter.sdmpc_information_scope` equal to `freeway_only` or `urban_only`, requires the existing PFO-cap policy and matching actuator scope, and rejects unqualified global hotpaths. Production solve requires the exact completed regional-context marker. Wrong or incomplete contexts do not fall back to full information.
- `runtime_setup` saves only the appropriate locally observed closed-window boundary role after canonical initialization. The adapter invokes the context factory after existing full-runtime prerequisites, using this retained local observation. This resolves the merged-input/outer-JSON boundary mismatch without reimplementing initialization.
- At0/1s without a closed window the regional adapter writes the legal native baseline without optimization or prediction. The original no-control startup behavior remains limited to1s. Regular windows follow the full preparation path. Existing native writer/failure-hold mechanisms remain in use.

No adopted interior traffic equations, calibration, cost ownership, horizon/terminal policy, physical partition, finite search budget or VSL/RM fallback policy changed in Task5. Source crossing requests come from the last closed own boundary window. Outlet supply remains adopted static capacity with open outlets; no additional local blockage observation is consumed. This is not an observed-empty receiver claim or a remote-spillback forecast.

## Configuration review appendix

Exact recursive semantic diff: `diagnostics/solo355_local_20261013/config_delta.json`, copied from the parent's independently generated comparison and checked against file bytes. Both new configurations have only nineteen adapter-field changes plus name/description relative to their exact source:

| Mode | Exact source relative to package | Source SHA256 | New SHA256 |
|---|---|---|---|
| freeway_only | diagnostics/solo355_20261012/freeway_only_config.json | e57280205613abe67d0d329100341636bf56a89eec285e5b4ace97014a80afd1 | cd193948e7267c40373ea9bcd92013f7ffe34dff36438239113db58b7d433778 |
| urban_only | diagnostics/solo355_20261012/urban_only_config.json | a5397c922621db18eb491d4ef17173a670cd600b7e94becee2894e8a5e4549c3 | 0dfe8dfbe490e207083916fcefae9aa7c318698561446a6291b37f22e7186172 |

New files are `diagnostics/solo355_local_20261013/{freeway_only,urban_only}_config.json`. Added information scope matches mode. `sdmpc_` adapter flags set false are array_transport, array_urban_pipeline, compact_audit, fast_primitives, flow_update_cache, initial_derivative_overlap, initial_shared_prediction, persistent_urban_fifo, prediction_cache, prediction_hotpath, ramp_stock_cache, receiving_geometry_cache, response_cap_cache, spatial_receiving, stock_geometry_hotpath, tangent_shared_primal and trial_derivative_overlap. `sdmpc_tangent_concurrent_primal` is removed and inherits false; explicitly supplying false violates its existing validator, so omission preserves the disabled setting. Name and description describe local information. No tuning beyond these fields changed. Derivative workers remain the original8, with BLAS/OMP/MKL threads1, and existing two-iteration/three-line-search policies unchanged. These disabled hotpaths and the measured wall times are this experiment's computation settings, not previous-run performance.

## Input isolation and retained-field provenance

Evidence root: `D:/VISSIM_analysis/20261013_solo355_local/task5/`.

`regional_raw_replay.py` rebuilds current canonical configuration, physical projection, reactive guards, demand forecast and the local context from captured merged raw plus observation frames. Injection is at `lane_plant_runtime.observe_state`, after the upstream collector/transport validation. It is not an unchanged already-projected-state perturbation. Static geometry is loaded by the canonical initializer. Cached own VSL cohort history and own head passage/exposure service support are held identical between variants; live physical state is rebuilt. This specifically does not revalidate transport or obs150 source hashes.

FW ownership for intervention is the compiled mainline address set plus eight onramp connectors. Opposite-speed variants changed1889 urban records for FW-only and1476 freeway/onramp records for urban-only, including matching observation-frame speeds. The independent opposite-stock variant removed one opposite vehicle and updated matching raw counts, stopped counts, queue bins and observation records, while own crossing requests remained fixed. Own-speed variants changed the corresponding own records and kept boundary requests fixed.

The complete graph hashes, including declared dataclass fields and nested freeway configs, were equal for base/opposite-speed/opposite-stock:

- FW: `6c9b91f0cab924275b0f6aa59484f69034334b0defa5350f180914fa9cba12d9`.
- Urban: `3fce832e6e05b44602974def774dc30fc0ec1396427a9debebbacdc034cbef62`.

Both own variants changed the graph and actual response: FW raw-replay objective190.12384806062906 to192.25235853933137; urban238.87131977894447 to247.34592819278558. The fresh raw-derived context is a separate preparation fixture from the original captured context used for full selections; its objective is not relabeled as the full selection's held objective.

Fresh base/opposite full response, Jacobian and writer evidence were equal after only the explicit timing/pickle-identity exclusions in `input_gate.json`; complete decision graph equality is checked separately with stable canonical serialization. Excluded names: compile_or_load_sec, context_fingerprint, frozen_context_token, reference_response_token, request_sha256, response_token, reverse_sec, seconds, state_check_sec, sweep_sec, tangent_sec, wall_sec_including_spawn. No cfg, bounds, leader domain, history, callback decision or numerical row was excluded. Stock variants reuse the identical full context and prior fresh response/Jacobian rather than repeating AD.

Retained dynamic fields have concrete own provenance: freeway source-boundary admission/backlog and component VSL history belong to own mainline/source records; urban head passage/exposure/resource support, movement capacity, queue storage guards and lane split derive own urban passages/queues and static lane authority. `physical_gate_travel`, `sc109_transport317` and `urban_boundary_travel_time_sec` derive own urban raw speed/transport inputs and are retained only for urban. The first raw FW test found357 repeated graph differences in exactly those three fields, which had initially been misclassified as static. That failed evidence (`raw_fw_base.json`, `raw_fw_opposite.json`) is preserved. Moving those fields to urban-only provenance restored full graph invariance; the successful receipts use `_v2` names.

Five integrated context tests additionally poison actual nested meter raw/history/spillback fields, opposite live cfg/state/forecast/boundary fields, follower/controller caches, adapter cache payloads, inactive targets, bootstrap projection payload and historical diagnostics. They check full prepared graph and physical command invariance. The real `load_prices` path is exercised with an explicitly offline synthetic receipt: inactive arbitrary data is ignored, active same-mode price changes remain visible and wrong region rejects. Historical inactive actuator changes reject; own commands remain. No synthetic application is described as native.

Raw numerical receipts were created before the worker-contract repair, using the earlier one-worker single-query setting. That setting did not support full batched optimization. These receipts are preserved under their actual settings; the current full-context/regression checks and both successful full selections use restored8. No numerical/model equation changed during this repair.

## Validation commands and evidence

Interpreter: `C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`, package workdir `E:/VISSIM_packages/solo355_20261012`. Set PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH to package + package/vendor/NumSim-mine + `C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc`; process-only TEMP and TMP to `D:/VISSIM_analysis/20261013_solo355_local/task5/tmp`. Diagnostic harnesses set BLAS/OMP/MKL threads1 and canonical offline writer switches.

Raw qualification command pattern, actually run for both modes and variants base/opposite/own with `--evaluate`, and opposite_stock without `--evaluate`:

```text
python -B diagnostics/solo355_local_20261013/regional_raw_replay.py --mode MODE --variant VARIANT --output D:/VISSIM_analysis/20261013_solo355_local/task5/raw_PREFIX_VARIANT_v2.json [--evaluate]
```

Prefix FW uses `fw`, urban uses `urban`; opposite_stock outputs use `stock`. These are retained historical runs, not instructions to repeat completed selections. Large graph pickles and full matrices remain in D.

Final focused regression after the8-worker repair:

```text
python -B -m unittest diagnostics.solo355_local_20261013.test_regional_context diagnostics.solo355_local_20261013.test_regional_contracts diagnostics.test_sdmpc_central diagnostics.test_sdmpc_pfo_caps diagnostics.test_validated_decision_hold
```

PASS66 tests in11.947s. Includes the earlier61 required regression cases plus five new context/startup/price/worker tests. The worker regression requires8 and rejects1/2/4, preventing the exposed batched reverse-limit mismatch. Earlier context-only4 tests passed10.485s before that fifth regression. Task4's documented unrelated fixture failures remain unchanged; no broad test-suite success is claimed.

```text
python -B diagnostics/solo355_local_20261013/regional_full_selection.py --mode freeway_only --output D:/VISSIM_analysis/20261013_solo355_local/task5/full_freeway900_v2
python -B diagnostics/solo355_local_20261013/regional_full_selection.py --mode urban_only --output D:/VISSIM_analysis/20261013_solo355_local/task5/full_urban900
python -B diagnostics/solo355_local_20261013/regional_startup_probe.py --mode freeway_only --output D:/VISSIM_analysis/20261013_solo355_local/task5/startup_freeway
python -B diagnostics/solo355_local_20261013/regional_startup_probe.py --mode urban_only --output D:/VISSIM_analysis/20261013_solo355_local/task5/startup_urban
python -B diagnostics/solo355_local_20261013/summarize_qualification.py
```

Full selections were sequential; FW PID20436 and urban PID42188, exact start epochs/HEAD/options/policies in each `protocol.json`, stages in `joint.progress.jsonl`, full adapter report in `joint.json`. Both used source HEAD218d7b1 plus the then-uncommitted bytes now in886f82b. Actual canonical1s startup returned status ok in6.720583/5.670039s with `sdmpc.solve`, adapter decision and prediction functions patched to raise on invocation. Actual native-format CSV writing still executed. Unit tests additionally cover the0s predicate and legal native writer scope; no saved0 native observation is claimed.

The first full FW attempt under `full_freeway900` failed after approximately29s with `Invalid overlapped reverse worker limit`: the existing Query scheduler batches predictions with an eight-worker pool, while the provisional local configuration supplied1. The original validation and8-worker setting were restored, then the unique successful FWv2 run was performed. That failed attempt is preserved as failed, not counted as a completed selection. Urban was first started afterward. No successful full selection was repeated.

`diagnostics/solo355_local_20261013/validation.json` was created only after both successes. SHA256 `4f94aea71f328d57f29816380dd28c7ce6f7d3fa584d0ad2b93a92884c26a032`. It has the required per-mode booleans, concrete input/startup receipts, regression results and full selection records:

- FW `full_freeway900_v2/selection.json`: `05cdc98ecbd14222bdc962dbe123e058f12e4fd75575358f58b7acf04306cb97`.
- Urban `full_urban900/selection.json`: `48cd2d576fd8cd21ca0d6863b49ad3b62f3611e2016558ad073e170e20efe86b`.

The retained-receipt summarizer actually rechecks input hashes, complete-context equality/sensitivity, entire normalized numerical response/Jacobian/writer equality, both canonical final writer bindings, three block counts, local cost conservation, startup success and current package pins. It performs zero rollouts.

## Source closure, self-review and limits

Actual current package source closure is `D:/VISSIM_analysis/20261013_solo355_local/task5/current_package_source_pins.json`, SHA256 `e3ea5fa87a4d629a7913faef4a478d2c9d9d33cc7ef0563130384b1ef1f46b0a`:1154 distinct currentE package files,1153 per selection. Every listed byte hash matched its actual selection receipt after both runs. Full canonical receipts each retain1458 pins, including223 C,35 D and1200 E provenance entries; not all are executed local source files. Old capture C/runtime provenance is explicitly not proof that C code implemented the new selection. The currentE checks and actual canonical adapter/worker source collector are the execution pins used here.

`diagnostics/solo355_local_20261013/required_source_inputs.json` refreshes the Task4 observed171 imported/transformed/static inputs with exact paths, current/checkpoint hashes and whether each is in the current canonical selection pins. It links the larger current closure. Three earlier observed harness/test files are not canonical source-scan pins and remain labeled accordingly. Unchanged imported vendor/plant/adopted diagnostic inputs are explicitly pinned, not gratuitously committed as new Task5 source, per parent's subsequent instruction. The53 untracked package inputs from that observed manifest remain baseline runtime files; final queue/freezer must carry and verify these inputs. No old evidence was relabeled with newly calculated source hashes.

Self-review checked local/static/own schema separation, nested cfg sanitization, copied active command history, same-mode real price loading, fail-closed production entry, regional startup and unchanged default path. The meaningful raw test caught and repaired the three-field cfg leak; the genuine full selection caught and repaired the worker configuration mismatch. Current source bytes were kept unchanged after successful selections. `git diff --cached --check` reported only six extra final blank-line warnings in new Python files, no trailing-space/conflict issues; these cosmetic final newlines were retained to preserve the exact executed source pins. Explicit-file commit only; unchanged imported code was not added.

Remaining limits are deliberate and concrete: no new blockage measurement, no upstream transport revalidation, own-history injection in raw replay, no native traffic/application claim, approximate finite nonconverged selections, and correct rejection of the old integrated4500 inactive history. Parent approved omitting an optional4500 counterfactual without a new concern. Native0 / freeze0 / queue0 / push0. Task5 implementation and mandatory saved-input qualifications are complete; parent review and canonical native preflight/dispatch remain outside this task.
## Review fix round 1 — I1 and M1 (base e104272)

Status: Important I1 is fixed; focused producer/preparation and numerical equivalence evidence passed. The original sections above describe the executed886f82b checkpoint and its source pins. They are retained as history, not claims that the original selections executed the following source delta. Current release validation supersedes its original hash and explicitly links both old executed evidence and this fix.

The sole production semantic change moves `far_ramp_capacity_veh_h` from `STATIC_NETWORK` to `OWN_NETWORK['freeway_only']`. This is live own freeway information: the unchanged estimator computes a decayed maximum of current onramp connector volumes and preceding action `far_rate_est_ramp_*` values. The groups are R_D_W=10480/10482, R_F_W=10646/10644, R_F_E=10639/10681 and R_D_E=10490/10484. The field is preserved for freeway and absent from urban. No coefficient, estimator, forecast, traffic model or optimization policy changes. Six extra final blank lines identified by M1 were normalized alongside this necessary fix; `git diff --check` now passes (Git line-ending conversion advisories are separate from whitespace errors).

New bounded harness `regional_far_context_probe.py` calls actual `build_config` before legacy ramp-name projection and actual `install_measured_far_reservoir_rates`. The latter reads real captured merged far measurements and an actual diagnostic previous-action JSON file. It then propagates all four fields mutated by that producer (far capacity plus three dynamic MFD g values) into the captured initialized cfg and executes complete local preparation. This is explicitly a dependency-specific producer/preparation check, not another full raw-initializer or upstream collector replay. The JSON fixtures retain all original previous fields except the deliberate estimator mutation; physical own history, prices, traffic state and causal boundary observations remain fixed. The three dynamic g fields are already excluded as undeclared cfg extensions.

For each region, three variants were executed: original inputs; all eight measured onramp volumes raised to100000veh/h; and all four previous-action ramp estimates raised to300000. The actual producer changed the four capacities from1413.5222/1978.1706/1329.2927/1714.7647 to200000 (measurement variant) and298500 (history variant, decay0.995). Urban retained none of the field and had an identical complete graph in all three variants. Freeway retained the exact produced values and had three distinct complete graph hashes. The existing opposite-field poison test also now covers this field through the corrected ownership set.

For numerical source compatibility, the harness loads the exact preserved old factory bytes and current factory against the same captured900 input. Complete FW graphs match. Complete urban graphs differ only by removing this named field, appearing at21 aliases of the same cfg across follower/local models; no other graph field changes. Urban old/new graph hashes are706ea81a6a8061859a748a7f1657ed498624e87e9d956c23c5025d77a46671b0 and9c5efa90f8a0cbbb7f93069adacfae6f87fd9e02e2e44208696b7072b06f9211.

The retained field's named consumers install the legacy far-cost wrapper. The actual regional worker dispatches directly to `sdmpc_regional_prototype.predict`, which executes the owned-region intervals and returns ledger TTT with `far_disabled=True`; it does not call that legacy far function. This is a path-level terminalOFF argument, not an assumption that the captured `leader_mfd_far_enabled` flag is false (it is true but the regional endpoint bypasses that function). Old/new fresh selected-action evaluation independently confirms the bound: the exact saved urban selected three-block physical action, unchanged NP cap and history produced equal full responses, complete AD Jacobians and canonical hold/writer evidence after the previously declared identity/timing exclusions. Both objectives were234.06544106057717, matching the retained full selection within1e-9. These two bounded single-action evaluations took9.7734672s and9.8787832s. They are not new full selections or a global mathematical equivalence certificate.

Commands:

```text
python -B diagnostics/solo355_local_20261013/regional_far_context_probe.py --output D:/VISSIM_analysis/20261013_solo355_local/task5/fix1/qualification
python -B -m unittest diagnostics.solo355_local_20261013.test_regional_context
python -B diagnostics/solo355_local_20261013/summarize_qualification.py
```

Use the same interpreter/PYTHONPATH and D-only process TEMP/TMP described above. The bounded probe passed. Five focused context/price/history/startup/worker regressions passed in12.773s. The prior66-test result remains a prior result; the unchanged61-case subset was not repeated. The summarizer detects the completed fix receipt and invokes `finalize_fix1.py`, which verifies the retained old selection/evidence hashes, exact source delta, current bytes and explicit compatibility receipt. No full optimization was repeated; parent approved this bounded proof after the path assessment.

Evidence and release binding:

- `D:/VISSIM_analysis/20261013_solo355_local/task5/fix1/qualification/receipt.json`, SHA256 `f73381ce67c6ed3dfa7bec326c062d88bf8db464fa6c4eb2352e4a119198c917`, contains producer outputs, graph hashes, old/new selected response/Jacobian/writer paths and hashes, and precise limits. Large numerical JSONs remain only on D.
- The exact old factory bytes are preserved under `fix1/executed_sources/evaluation/controllers/sdmpc_regional_context.py`, SHA256 `e1136ab97b58fae2fd06071a166f9fa2762266115a4c6a01140b2b155c1fa958`. Current factory SHA256 is `519df9b7858a92c30fa06c9f45295d751702099598e1770edc5a871e92c69a05`.
- `fix1/source_delta.json`, SHA256 `7e15a5e2f14a254241c9cbbcae5bd0a4d2282beef868e0c1ad7e8ecd90f42a22`, verifies the factory has exactly the two ownership-list text changes plus final blank-line cleanup; the other five saved files differ only by final blank lines. All other1153 original numerical package pins remain byte-identical. Unchanged old source manifest and original full-selection hashes are retained.
- `fix1/current_release_package_source_pins.json`, SHA256 `7097f8f5c62de723e44b52122443b4738d885711f03c97beb06792d285fab244`, has1162 current release entries: the1154 execution-closure paths with current bytes plus eight qualification diagnostic paths. It explicitly links the old executed manifest and fix receipt. It does not claim full selections ran with the new factory.
- Current `diagnostics/solo355_local_20261013/validation.json` SHA256 is `e8405003adfe471080b4f053cbbf73e16da40482ba7665f2eb4b352febb08c3e`. `source_pins` names the current release manifest, `executed_source_pins` names the original manifest, `fix1` carries the source delta/qualification/five-test receipt, and each retained full selection states its original source binding and the current-release equivalence link. `required_source_inputs.json` links both manifests too. The original validation is preserved byte-for-byte at `fix1/executed_validation.json`.

No production-readiness claim extends past these bounds. Important I1's own-graph defect is resolved; the source-delta argument and selected-action comparison preserve the earlier full-selection evidence without relabeling its executed source. Native0 / freeze0 / queue0 / push0; original nonconvergence, static open outlets and transport/native limits remain.