# Why the1200 decision closes two ramp groups

The controller deliberately selected the lower total-meter budget. The physical writer preserved the requested zeros. A controlled, held-action model comparison shows that **an inherited freeway-density penalty reverses the ranking given by Ω TTT alone**. The spillback guard sees a different observation from physical ramp stock, so it does not reopen these meters merely because connector queues grow.

This is a read-only diagnosis of `codex_area_sources_beta0_s13_20260910`. No model/configuration changes, optimizer search or VISSIM execution were made. Results and all source/input hashes are in `source_meter_shutdown_diagnosis.json`; the reproducible producer is the adjacent `.py`.

## Recorded selection and actuation

| Decision sec | Selected intended N_UF veh/h | Physical realized sum veh/h | DW | FW | DE | FE | Observed ramp stock DW/DE/FW/FE veh |
|---:|---:|---:|---:|---:|---:|---:|---|
|1050|See raw diagnostics|5314.032320|745.877773|1800|1800|968.154547|7/6/44/1|
|1200|1440|1425.6|0|712.8|712.8|0|21/15/31/4|
|1350|1440|1456.944880|0|774|682.944880|0|67/21/68/27|
|1500|1440|1414.210392|0|774|640.210392|0|101/32/118/51|

At1200, the request is DW0/FW736.910011/DE703.089989/FE0. The canonical table writes DW10480/10482 and FE10639/10681 at0 seconds GREEN; FW10646/10644 and DE10490/10484 at3 seconds GREEN per10-second cycle. The zero closure precedes quantization. The actual1200–1350 command/SG/VSL audit passes (`source_interval_1200_1350.json`).

The leader bounds are1440–7200, even though its arrival target is3976, queue-drain target5680 and heuristic target6593.486886. These targets enlarge/anchor search; they are **not a hard lower queue-drain requirement**. See `vendor/NumSim-mine/src/controllers/leader.py:323`–340 and the minimum-total-budget calculation at653. Individual simplex allocations can reach zero.

The selected candidate has J450.355866. The second candidate (realized N_UF3577.024176, intent3600) has J450.503719: a gap of only **0.147853 veh·h**. Nine proxy candidates were considered, but only four received full evaluation (top_k3 plus incumbent); proxy best and second tie453.639015. This is the recorded finite search result, not proof of a global optimum.

Link budget shares are W0.511743063/E0.488256937. Thus the1440 intent gives736.910011/703.089989. The follower splits each link budget between its two ramps using seven simplex points, including endpoints; own local rollout cost plus the metering external-price term ranks those splits (`wu_faithful_follower.py:3502`,3620–3642). At1200 the external marginal prices are DW+0.0006334642, FW−0.0022674514, DE−0.0007140740, FE+0.0000025815. They favor FW over DW and DE over FE, consistent with the selected allocation. The recorded log does not retain every local split cost, so the prices alone are not asserted to be the sole cause of choosing the endpoints.

## Same-action model intervention: reopen only DW/FE

Initial state and forecast are identical. N_P, greens, offsets and VSL remain identical at every10-second freeway step. The comparison changes only DW/FE to1800 and the total budget to its realized sum **5025.6**; FW/DE stay712.8. All four reopened physical meters are GREEN10/10, and the budget is inside7200. Each candidate/state/forecast is private, input immutability and closing ledger conservation pass. No future observations enter forecasting.

| Horizon sec | Quantity | Recorded closed | Reopen DW/FE | Reopen−closed |
|---:|---|---:|---:|---:|
|150|Ω TTT veh·h|111.600511|111.652650|+0.052140|
|150|Ω TTD veh|484.779891|485.855261|+1.075370|
|150|End ramp stock veh|212.309896|118.954632|−93.355264|
|150|Density penalty veh·h|7.851903|8.464071|+0.612168|
|150|Leader total cost veh·h|119.452413|120.116721|+0.664307|
|450|Ω TTT veh·h|390.650860|389.457098|**−1.193762**|
|450|Ω TTD veh|1594.103545|1636.333473|+42.229927|
|450|End ramp stock veh|379.410544|175.022570|−204.387974|
|450|Density penalty veh·h|59.807598|69.729835|**+9.922238**|
|450|Other added leader penalties|0|0|0|
|450|Leader total cost veh·h|450.458457|459.186933|**+8.728476**|

Closed450 is the held physical command and equals the recorded follower Ω TTT390.650860. It is not the exact leader's future box-walk score450.355866 (leader base390.548268); the0.102592 difference must not be hidden. Closed150 matches the independent Hubble held-action audit exactly in TTT, TTD, entries and all ramp stocks. The450 intervention is a model counterfactual; it does not prove actual improvement or identify a causal effect in VISSIM.

An earlier all-four1800 request maps to FW1819.299203 plus the other three1800, total7219.299203, with FW10646g6/10644g10. It exceeds the7200 leader box and is **excluded from candidate comparisons**. The exact mapping is retained separately as an inadmissible quantization diagnostic. No table changes or clipping were applied.

## Exact objective path and units

The outer path is:

1. `stackelberg_mpc.py:2414` evaluates the canonical near endpoint.
2. `evaluation/controllers/area_runtime.py:199` forces far/pruning off; at206–221 it replaces global TTT once with Ω TTT−β_seconds/3600×Ω TTD. `additional_cost_veh_h` measures only extras **inside that endpoint**. The recorded raw follower endpoint has additional_cost0.
3. `stackelberg_wu_metered.py:2636` then calls `Leader.objective_terms`. At`leader.py:914`–932 it adds legacy penalties to the already replaced Ω base. The candidate returned at`stackelberg_wu_metered.py:2661` is ranked by this new total. The endpoint's additional_cost field does not include these later costs.

The density penalty is

`P_density = w_F × T_c_h × Σ_horizon_states Σ_links,cells [L_km × lanes_weight × max(0, rho−rho_crit)]`.

Here `w_F=3`, `T_c_h=150/3600 h`. `rho` is veh/(km·lane); multiplying by L and lanes yields excess veh, then by T_c_h yields veh·h. The multiplier3 is dimensionless. This is an **extra excess-density residence surrogate**, in addition to actual Ω residence already charged in TTT. It is not a storage/receiving feasibility constraint. `_density_penalty` at`leader.py:783`–815 uses effective lanes where its enabled condition differs from the scalar nominal lane count, and `effective_rho_crit` under the action. The actual config inherits explicit`parameter_overrides.leader.w_F=3` at`n7_area_beta0.json:7472`; no new weight was introduced by this diagnosis.

All terms in the common outer candidate/fallback/proxy scoring path:

| Term | Current configuration and effect | Scope / code |
|---|---|---|
|Base|Ω TTT−βTTD; β0 here|Near endpoint then follower_ttt base, leader.py880–883|
|Protected accumulation excess|w_P1 but mode all_urban_halfcap, so inactive|Unweighted protected model stock threshold;893–899|
|Urban half-cap excess|weight1, threshold0.5;1200 zero,1350 **0.197470**,1500 **0.369184**|All urban movement queues and storage except off-ramp storage, including boundary queues;841–861,902–906. Not restricted by physical Ω membership.|
|Boundary-in queue|w_boundary_in0, cost0|907–909|
|Freeway excess density|w_F3, material59.807598 at1200|783–815,914–915|
|Extra ramp-queue term|w_ramp_queue0, cost0|916–917; diagnostic leader_ramp_queue_veh sums stocks across all predicted endpoints, not just the final stock.|
|Action smoothing|hardcoded0|918–921|
|Nonconvergence|computed for diagnostics, **not added** to total|922–934|

`Leader.objective_terms` is shared by full candidates, proxy filtering and fallback evaluation (`stackelberg_mpc.py:1549,1878,1967`, `stackelberg_wu_metered.py:2181,2559,2636`). A correction only to the final chosen action would leave earlier ranking/filtering inconsistent.

Endpoint-internal extras are separately controlled in`rollout_endpoint.py:405`–430: far, price hinge, leader hinge and protected queue. Area runtime forces far off. This active config has leader_hinge_enabledFalse; the observed raw follower additional_cost is0. Price/protected-queue extras are not enabled by the default ObjectiveSpec used here. Barrier and max-density components are returned separately rather than added to endpoint.objective at431–447. The proxy's optional direct far addition at`stackelberg_wu_metered.py:2552` defaults off (`leader_proxy_near_far` absent); this alternate opt-in path would need explicit rejection or Ω support if enabled later.

The inherited config note at7686 says w_ramp_queue0 is justified because a far ramp tail replaces it. The Ω endpoint now disables that far tail. This is a stale rationale, **not proof that ramp waiting has no cost**: Ω near TTT already includes every inside ramp vehicle. Finite-horizon residence and the extra density/MFD terms are different mechanisms.

## Why neither guard stops it

The spill guard uses only `state.local_observation_summary.ramp_spillback`: eligible stopped vehicles on configured approach roads. The actual snapshots independently recompute zero for all four groups at1050/1200/1350/1500. Current detector rows have no conn_pos_m cutoff, so the canonical absent-cutoff behavior includes the full declared road; lane filters still apply.

| Group | Declared physical approach / queue lanes | Not the same as |
|---|---|---|
|DW|32 lanes1/2;124 lane1|10482/10480 connector stock|
|DE|129 lane1;31 lane1|10490/10484 connector stock|
|FW|121 lane1;69 lane1|10646/10644 connector stock|
|FE|68 lanes1/2;70 lane1|10681/10639 connector stock|

`vissim_stackelberg_adapter.py:6103`–6134 builds these observations. The guard at10448–10478 forces1800 only if **observed stopped>8** and current rate<1800. It never checks ramp occupancy/capacity fraction or predicted450s queue. `area_meter_finalization.py:48`–61 pins this initial decision context for all candidate intervals; this is explicitly an observed guard, not a forecast queue-tail guard. Receiving/storage capacities still constrain modeled accepted flows.

The fallback comparison is a separate issue. At1200 the leader improves the legacy-augmented score by8.508789 against PFO458.864655, less than the22.943233 required5% gain. However, insufficient_gain alone is not a veto (`stackelberg_mpc.py:1699`–1708): it must accompany worsening terminal/completed proxies. All four leader/fallback terminal/completed proxy values are **0**, so no such condition is detected. The proxy getters at1584–1595 read old distributed_response fields and default missing values to0, not the new Ω TTD. The current metadata must not be described as a successful nonzero throughput/terminal safeguard.

## Prediction error is separate from the score reversal

At1350 the observed ramp total is183 while the closed model predicts212.310: it does **not** simply underestimate all queue growth. Per-group model/observed DW94.666/67, DE40.925/21, FW57.241/68, FE19.478/27. The model predicts E8/E9 speeds96.116/84.791, versus observed40.485/43.168. ΩTD484.780 versus575 observed crossings+243 terminal-inferred exits; one unresolved disappearance is not rewarded.

Root's separate `source_native_offratio_sensitivity_1200.json` changes a private conditional joint prior: total predicted off flow157.218→302.769 against286 observed branch entries, FW stock1285.088→1142.102 against1114. Yet E8 speed becomes98.866, farther from40.485, and FE overprediction offsets FW underprediction. This supports separate off-routing/physical-order and dynamic-speed defects. It does not establish that the synthetic0.2 is the sole cause of the two closures or warrant fitting one unconditional off fraction.

## Minimal correction to review after the run

For the enabled Ω objective, the common leader scoring boundary should rank the explicitly authorized Ω TTT−βTTD score. Keep legacy density, half-cap and queue quantities as clearly excluded diagnostics; they must not silently re-enter full/proxy/fallback totals. Preserve the exact legacy OFF branch. If any additional performance penalty is intended, it needs an explicit separately reviewed objective contract and units, not an inherited global config default. This change is to ranking, not physical receiving, storage, signal feasibility or mass conservation.

Required regression: this saved held pair reverses toward reopening under pure β0 ΩTTT; positive β further rewards its additional42.23 exits. Full/proxy/fallback all call the same gate, density/MFD diagnostics remain inspectable, legacy OFF returns identical terms, and no accepted-flow/state changes occur. The existing guard's observation scope and zero proxy limitation require explicit separate review rather than quietly changing its thresholds. Production remains untouched.

### Minimal patch boundary and tests (unapplied design)

- Add one small runtime installer, e.g. `area_leader_objective.install_runtime(cfg)`, called by the existing shared `area_runtime.install` path used by main/worker/offline. Wrap **only** `Leader.objective_terms`, once, with a call-time `cfg.network.control_area_enabled` check. The OFF branch immediately delegates to the captured original method with the original arguments and returns the original dictionary unchanged. Do not modify global config weights to zero; that would contaminate reused OFF configs and hide which inherited weights were excluded.
- Enabled mode requires `leader.objective_mode == 'follower_ttt'` and a finite canonical Ω follower_objective. Obtain the original raw quantities/terms for diagnostics, preserve each removed contribution under an explicit `leader_excluded_*` field, set the **applied** target/MFD/boundary/density/ramp costs to0, and set `leader_total_objective = follower_objective`. Retain density_excess, halfcap_excess, queue stocks and diagnostic convergence quantities. Add `leader_control_area_objective_only=1` and `leader_excluded_legacy_cost_total`; do not label excluded penalties as currently applied. This one gate covers the listed full/proxy/fallback calls and `Leader.objective`, which delegates to objective_terms.
- The gate does not change candidate generation, budget feasibility, accepted-flow receiving limits, finite storage, physical clock/CSV quantization, state integration or ledger transfers. It does not create a new queue-release rule. Existing follower allocation/local approximation remains a separate source of optimizer/model error; removing an outer penalty is not evidence that all candidate response approximations are exact.
- In the same review, explicitly lock the enabled area contract to endpoint extras it actually authorizes: current contract is pure near ΩTTT−βTTD, so price/leader/protected-queue hinge costs should not later slip into the canonical score through legacy flags. A narrow normalization in area_runtime's existing `replace(objective_spec,...)` can disable these unrequested objective components while retaining separately reported barrier/max-rho diagnostics. Alternatively reject such unsupported enabled flags during configure. The direct `leader_proxy_near_far=True` path adds far outside the endpoint and must be rejected at configuration for this contract. It is absent now, so neither item explains the current numbers. No new physics or broad adapter copy is needed.
- Test OFF full dictionary equality against the pre-patch actual method, including nonzero weights, state_accumulation mode, and an ON→OFF reuse of the installed class. Test enabled mode with separate nonzero density, halfcap, boundary and ramp quantities so zero-valued incidental fixtures cannot hide leakage. Verify original state/action/forecast pickles and all accepted-flow results remain unchanged.
- Test actual saved450s endpoints without new simulation: β0/60/150/300 rankings must equal the ledger's ΩTTT−βTD calculation, with reopen preferred in all four; excluded-density values remain59.807598/69.729835 and excluded MFD0. Add a synthetic nonzero urban halfcap case because the actual1200 held pair has none. Capture representative full candidate, proxy and fallback method invocations to prove all consume the same patched total and β is applied only once. Final actual main preflight should require the new objective-only metadata before a new VISSIM arm.
- Treat the old fallback proxy0/default semantics as an explicit limitation in this patch's report. Replacing those with ΩTD/terminal data or strengthening an insufficient-gain veto is a separate behavioral change and should not be bundled invisibly with cost-scope correction.

The completed endpoints were saved before a metadata serializer correction (`ramp_counts` in raw, not `ramp_queue`; descriptive detector keys excluded). `--reuse-partial` assembled the final report without recomputing endpoints, preserving the original producer hash and rechecking every runtime/input hash; source changes are empty. The strict first150 independent equality check is recorded. The earlier incomplete diagnostic attempts are not controller failures or performance arms.

`source_meter_shutdown_command_audit.py/.json` additionally runs the actual canonical CSV writer in memory: the closed arm matches all213 actual1200 physical rows; the reopening arm changes exactly four ramp-meter rows from0 to10 seconds, leaving all signal/VSL and other meter rows unchanged. No CSV is sent to the simulator. `python -X utf8 -m unittest diagnostics.test_source_meter_shutdown_evidence diagnostics.test_source_run_comparison -v` passes18 checks, including independent150s replay equality, admissible realized budget, excluded7219.299 request, β0/60/150/300 pure-area ranking and density-cost reversal.
