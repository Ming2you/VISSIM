# Two finite route corridors — integration handoff

The implementation is ready to freeze. It uses one canonical engine for1129 and1128; no adapter copy, alternate urban body, optimizer search, or VISSIM run was added. Root's existing main/worker/urban/shared69 hooks already consume the aggregate fields unchanged. The multi-evidence stock claim validator in `projection_support.py` is Hubble's integrated change.

Runtime files/data for this change:

- `evaluation/controllers/route_choice_corridor.py`, SHA256 `d4e35708bfcaebaa558246ab9d2e40026fea750f6bc2ed7c8071b3b901ece3cf`.
- `diagnostics/route_choice_corridor_ver2.json` (1129 unchanged), SHA256 `3cd24cd81c7335dfe54ba9c9770d407ef04737f9f426b695c485954593147ec9`.
- `diagnostics/route_choice_corridor_1128_ver2.json`, SHA256 `5ce589875e64cd8940d968084ca502aec62fdffb65c2c8ca819ed8cf3b0e5bf4`.
- Existing dependencies: canonical `vehicle_routes.py`, `projection_support.py`, `physical_movement_routes.py`, `control_area_objective.py`, the pinned Ver2 INPX, jam geometry source and635 membership. No diagnostic probe or raw FZP is a runtime dependency.

Use the existing route flag with an explicit list; there is no new top-level flag:

```json
"urban": {"route_choice_corridor": {
  "evidence_paths": [
    "diagnostics/route_choice_corridor_ver2.json",
    "diagnostics/route_choice_corridor_1128_ver2.json"
  ],
  "unknown_policy": "error"
}}
```

Root should enable the canonical `RW_VEHICLE_ROUTES=1` collector for live work. Missing post-decision route identity fails under `error`; `hold_diagnostic` is only an explicitly incomplete historical replay mode. Old single `evidence_path` and absent-flag behavior remain supported. `route_choice_prediction_route_complete` and `route_choice_held_unknown_route_veh` keep their names and aggregate all corridors.

`configure` stores child specs under `cfg.network.route_choice_corridor.corridors` for a multi configuration. Its top-level `capacity_veh`, `turns`, and `renames` are unions for existing generic source/arrival/sink exclusions and area-route installation. Physical keys, managed stocks, and incoming movement keys may not overlap. Candidate-private state remains a single `route_choice_corridor_state`; distinct physical storage identifies each cohort. No runtime cfg swapping or shared mutable proxy is used.

1128 closes the following paths:

- Prefix10610→385→10611,10618,10619 and1220000102 go to new finite `SC107_W_choice`. Every suffix is checked against physical edges and forward positions; intermediate roads must have one next connector. No independent input or signal head may be silently swallowed by this prefix.
- N/S/E each keep their `_W_SC1005` movement name and remove the `_W_SC1004` future-destination alias. Only beta totals are summed. The physical service budget is one source connector, using XML lane count times the already installed per-lane scalar; capacities are never added across aliases. N10610 is one lane/no upstream controlling head, S10618 is three lanes with its upstream head, E10619 is four lanes with upstream heads. At the current existing per-lane scale this is206.5306/619.5918/826.1224veh/h. These are inherited model scales, not newly measured saturation flows.
- Future eligible1128 decisions get native conditional1:1 weights. Branch1 enters finite local10500/62 stock `SC107_to_SC1005`, retaining its selected tag, then passes10603 into `SC1005_to_SC105` only as receiving space and the one physical connector budget accept it. The branch leaves62 at391.834m before its relevant heads; it never enters an SC1005 signal movement queue and is never resplit by old through/turn betas. A full downstream receiver retains it on62.
- Branch2 goes once to the existing bypass receiver `SC107_to_SC1004`. Observed10501 belongs to that receiver. The whole downstream52 road is not reassigned, because it also receives10498 from another origin. Existing downstream mixing/travel approximations remain.
- Observed10603 goes to the physically and canonically verified404 receiver `SC1005_to_SC105`. Both branches and404 remain inside635: these transfers create no TTD. S source382 is outside whereas10618 is inside, so accepted S→prefix is a single inward crossing. N/E entries and all initial stocks create no extra entry event.
- Managed local62 has only10500 as a physical incoming connector. Its sole1128 continuation is identifiable from that physical branch even if the current static route has already ended. Such a cohort is labeled `unique_physical_branch`, not a fabricated observed route ID. Shared pre-decision1220000102 has two possible destinations and does not get this exemption.

1129 preserves existing behavior: eligible8:1:1 choice, observed through/left tags on57, single10634 service shared by W/offE/offW, and shared69 branch2's deterministic continuation through10636/75/10701 into the prefix. Local57 typed queues still use the existing SC1005 model service/phase mapping. The known SC1005 mixed-SG authority issue is **not fixed or validated** by preserving route tags. Likewise, checking that a source connector has upstream signal heads does not prove every existing phase-to-SG waveform mapping; the separate signal-authority review owns that.

Evidence limits are explicit. Native1:1 and8:1:1 values are conditional future-choice priors read from the pinned static route definitions (empty relative flow uses the documented VISSIM default1). They are not measured historical posterior route shares, nor unconditional flow fractions at a downstream bottleneck. Already selected routes are never redrawn. Geometry-based travel uses the existing observed-speed floor and a scalar inherited lane service scale; detailed lane changes, queue tails, and exact substep spatial residence are still approximate. The conservation guarantees apply to the canonical coupled model endpoint; these tests do not calibrate every follower's local approximation.

Validation commands (actual production imports):

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -m unittest diagnostics.test_runtime_setup diagnostics.test_route_choice_projection_claim diagnostics.test_route_choice_corridor diagnostics.test_route_choice_1128 diagnostics.test_route_choice_native_observation -v
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -m diagnostics.probe_route_choice_1128_integration
```

28 tests PASS (11.526s), including immutable original-n7 numerical/worker comparisons, old1129 tests, six physical-claim tests, five two-corridor tests, and two actual native route-observation tests. They cover separate choices, accepted-once source receipt, full receiving blockage/release, red-signal-independent10603 movement, true382 entry, clone/fresh process isolation, and explicit failure after a past-choice observation is removed.

The actual β0retry1350→1800 held-action450s replay is saved in `route_choice_1128_canonical_1350_450.json`. Initial Ω stock2669 is exact; all macrostep ledger inventories close, main/repeat/fresh worker results match, ΩON/OFF physical states match, ΩOFF fresh worker matches, and source hashes stayed unchanged. Jβ0=410.7317604042veh·h and TD=1468.7457081veh are model outputs. The old snapshot lacks route attributes:1129 holds1 unknown vehicle and1128 holds5, so this replay remains incomplete with held_unknown6 throughout. Its values must not be presented as validated live optimization performance.

`route_choice_native_observation_qualification.json` separately uses nine actual native COM route/position captures at0/1/150/300/450/600/750/900/1050. It does not mix these records into a different run's full raw state. All captures initialize the two corridors under `error` with zero held unknowns and zero initial events. At1050,23 managed vehicles comprise16 observed-current-route and7 eligible-future-choice cohorts. Removing actual1128 post-decision identities correctly fails. This qualifies the new collector-to-cohort interface, not a full controller decision or live performance arm.

Root's remaining preflight is the combined active config with native internal input1091 and phase fixes, a full main decision using an actual route-bearing raw snapshot, and the all-state/positive-support gate before another VISSIM attempt. Active configs, source-manifest regeneration, controller run lifecycle, and any newly found fix remain root-owned.
