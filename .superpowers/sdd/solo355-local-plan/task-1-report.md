# Regional local-information implementation handoff

Status: **NEEDS_CONTEXT — bounded predictor and Query milestones complete; production controller incomplete.**

Parent approved a fresh production implementer after this checkpoint. Do not
activate this package or claim the task complete from these results. Native
runs: **0**. No freezer, queue dispatch, push, deletion, or publication.

Package: `E:/VISSIM_packages/solo355_20261012`, branch
`codex/solo355-local-information`, baseline
`d2ca825a2dbe2e776e9509cddcb47b411a5c75af`.
First commit: `16a0d45` (cut predictor and conservation probes).
Second commit: `21bb7e9` (regional Query/AD checkpoint). This report is saved in
the required normally ignored handoff directory and committed explicitly.

## Files and enabled scope

- `evaluation/controllers/sdmpc_regional_prototype.py`: state cut, causal
  entrance requests, actual adopted regional dynamics, local coverage and
  accepted quantities. This is intentionally named prototype.
- `evaluation/controllers/sdmpc_tangent_worker.py`: small diagnostic-only
  branch selected by `cfg.network.sdmpc_options['regional_prediction_prototype']`
  equal to `freeway_only` or `urban_only`. Absent option preserves prior branch.
  Matching projected state required. Central registry is explicitly rejected
  until a regional registry is implemented. All AD seeding/reverse code reused.
- `diagnostics/solo355_local_20261013/test_regional_prototype.py`.
- `diagnostics/solo355_local_20261013/regional_prototype_probe.py`: two-axis
  direct scalar/AD probe, older evidence explicitly identified below.
- `diagnostics/solo355_local_20261013/regional_query_probe.py`: actual Query
  and worker, all48 or189 axes, three150s blocks. Full cfg/bootstrap are still
  supplied; this harness is not an end-to-end information-isolation proof.
- `diagnostics/solo355_local_20261013/README.md`: boundary assumption/scope.

No production adapter option or dispatch was enabled. Existing actuator-only
configs and previous validation are untouched. No new successful
`validation.json` was written.

## Stable interfaces for the next implementer

`boundary_requests(derived, mode, now, ramps, offramps)` reads ONLY the exact
last closed obs150 entrance counts. Input is
`capture['obs']['merged']['obs150_derived']`. `end_s` must equal current state
time and window length is positive and <=150. It returns
`{mode,start_sec,end_sec,inlets,forecast,outlet,measured_flow_is_capacity:false}`.
Each inlet has `rate_veh_h` and `lane_rates_veh_h`. Keys are exact full ramp
names for `ramp_arrival:RM_C...`, physical connector IDs for `off_entry:10481`.
Use `state.lane_freeway_runtime.offramps`, not legacy `cfg.network.off_ramps`.

`project_state(original,cfg,mode,boundary)` constructs new TrafficState. Own
objects are copied TOGETHER to preserve lane_urban/lane_offramp aliases.
Remote objects are absent, with zero shape-only stock shells for existing APIs.
The allowlists are explicit `FREEWAY_FIELDS`/`URBAN_FIELDS`. Own initial ledger
cohorts are retained; model_inventory conservation is checked immediately.
Own route/lane tags on existing vehicles stay intact. It adds
`regional_boundary` and zero `regional_arrival_backlog`.

`predict(local,cfg,forecast,action)` returns the expected point shape:
`objective,ttt,states,control_area,control_area_response,aborted=False`, plus
ledger/rejected_arrival_backlog. It executes existing physical freeway/ramp
components only for freeway, existing urban/offramp components only for urban.
It applies `sdmpc_sequence.actions(action,3)` itself; do NOT wrap it in the
global `prediction_scope`, whose coupling-visit check would then fail.
10s arrival/residence integration and FW5/U10 interior clocks are preserved.

`quantities(point,state,cfg)` returns schema
`regional-accepted-quantities/v1`: active_resource=NUF for freeway, NP for
urban. Absent resource is inactive0, not a fabricated prediction. Freeway has
actual accepted8-ramp merge records and contiguous5s horizon coverage; urban
has17 signed accepted movement-owner totals and no remote merge frames.
Current owner rows contain only `net_inflow_veh`; lazy scalar-upgrade helper
requires additional accepted_event_count/by_kind fields if enabled later.

Coverage uses `regional-model-constraint-coverage/v1`, not the old global
certificate: only own allocator expectations are declared; 180FW/900urban
visits at saved900. Missing/failed original allocator constraints still fail.
The response explicitly says remote_frames_required=false and limits its
claim to own original state/allocation checks with the cut boundary assumption.

The Query harness builds SequenceCoordinates with canonical ownership/writer
address mapping and fixed movement box, then a sparse follower namespace
containing cfg and runtime `{'_PHASE_VECTOR_FOLLOWER':{}}`. It never calls the
global `_wu._coupling` to obtain callbacks. It disables the unqualified global
central registry/cache/hotpath optimizations for this bounded milestone.
It retains the existing reverse-v1 AD implementation, not finite differences.

## Physical boundary assumption and review fixes

Connector entrance is the split: onramps are freeway-owned; offramps urban-owned.
Current/past exact entrance counts form a frozen arrival REQUEST, not capacity.
Own finite storage restricts admission; rejected requested vehicles remain in
an explicit backlog. Backlog is external to region TTT, but conservation is
checked. Existing own-region physical stocks remain in local TTT.

Outlets use adopted static capacities with no remote stock/receiving history:
freeway off entrance uses configured freeway capacity; urban ramp outlet uses
static ramp capacity. Own source queues and finite local roads still constrain
outflow. This is explicit downstream boundary uncertainty, not evidence that
joint control is necessary. No claim has been made that a direct local-side
obstruction observation is unavailable in all collector fields; identifying
one would warrant a causal closure improvement before qualification.
Incoming10638 route classes use the existing unrouted branch law.

Reviewer P2 #1 fixed: copied onramp `lane_arrival_shares` could preserve urban
ready/receiving offers even with fixed allowed boundary counts. Projection now
sets new-arrival shares from exact local boundary lane rates; zero observed
count uses static uniform shares and zero requested flow. It never changes
cohorts/tags on already owned vehicles. Focused saved4500 asymmetric inlet test
changes stale shares, proves identical projected state and own-lane admission.
Fixture uses actual two-lane LaneResolvedRampBoundary RM_C10681; legacy
aggregate PhysicalRampBoundary also has a lanes count but no child buffers.

Reviewer P2 #2 fixed: removed an invented unused action diagnostic price key
from the test and corrected README claims. Persisted prices have NOT been
tested. Existing projected-state/forecast invariance is not a price-loader or
raw-observation proof.

## Input dependency policy and pending proof

Static geometry/topology/native schedules and local vehicle route/lane tags
are allowed, even when labels mention another region. A global initializer is
not itself a leak if its inputs are own observations plus static geometry.
Do not erase own measured service coefficients just because they were created
by a shared initializer.

Demonstrated/live cuts already made: no remote physical runtime in local state;
opposite demand forecast discarded; no coupled remote predictor; no remote
receiving stock/history at outlet; lane arrival shares replaced as above.
Urban prediction retains only urban_link_speed_kph from local_observation_summary.

Still unproved: cfg dynamic service/guard parameters and worker bootstrap.
Audit their actual live dependency before changing them. Candidate fields to
trace include head_free_service/head_service_resources,
head_green_exposure_windows/sc1001_shared_observation, urban_storage_guard,
local_service_pool, head_queue_movement_lanes/upstream_storage,
freeway_source_boundary_observed, control_area_meter_context. These are an
inventory for dependency tracing, NOT a claim that each leaks remote data.
The capture's worker bootstrap state_json contains network path, but
detector_mapping also contains runtime projection/record proof fields.
`sdmpc_tangent.prepare_request` captures ALL uppercase adapter dict/list/set
caches and full follower: do not use it unchanged for final regional contexts.
The diagnostic harness avoids that cache capture but still sends full cfg and
bootstrap, so its sparse runtime alone does not establish isolation.
Historical action diagnostics also contain full prior meter context; construct
minimal command history while retaining only actual writer/hold prerequisites.

## Exact remaining production contracts

1. Build audited local decision context before Query. Mutate opposite raw and
   derived observations/history while holding allowed own/boundary data fixed,
   and prove complete decision-relevant response/Jacobian invariance. Prove
   derived cfg service/guards depend only on permitted inputs. Do not merely
   zero external gradients around the old global predictor.
2. Extend `sdmpc_tangent_constraints.Registry.finish/install` for own-region
   endpoints. Existing finish loops all urban/ramp/mainline/storage fields and
   expects global bound visits; do not register zero remote shells as physical
   constraints. Keep genuine own allocation/state checks. Then allow regional
   worker central mode with that registry, not by removing the guard blindly.
3. Adapt `sdmpc.solve`, `sdmpc_budget.initialize`, Query.bind_warm_budget,
   load_prices and central dual initialization for only the active local
   NP orNUF resource and regional persisted state. Preserve within-region
   distributed S-DMPC, leader/follower/PFO and original optimization policy.
   Do not replace with a single regional sum-gradient optimizer or finite differences.
   Global budget initialization currently expects full urban and physical merge
   proof; urban has no freeway merge prediction and must not fabricate one.
4. Reduce owner/cost/gradient coordination to regional owners. Current worker
   diagnostic matrices retain20 rows with opposite-owner costs/Jacobians zero;
   this is temporary shape compatibility, not final distributed context.
   Own unassigned stock remains in PASSIVE_OMEGA: saved900 urban passive TTT is
   142.98201331404775. Keep its gradient in regional merit, do not discard it
   just because it has no actuator owner. Whole701 remains posthoc only.
5. Build actual callbacks without `_joint_runtime_callbacks` invoking global
   `_wu._coupling`. The Query harness demonstrates direct canonical ownership
   and move-box construction. Preserve actual three-block writer checks and
   inactive baseline, even when replacing global quantity validators.
   `validate_actual_decision_hold` currently expects19owners/global quantities;
   branch its quantity scope explicitly while retaining command validation.
6. Add new opt-in config(s), startup/failure-hold behavior, and dispatch. No
   boundary exists at0/1s before a closed observation; retain safe inactive
   baseline through canonical warmup, no accidental global local fallback.
7. Full saved900 selection per mode: feasible accepted local result, all three
   blocks validated, inactive fixed commands, raw/history/real-price isolation,
   own sensitivity, saved4500 bounded congested checks. Only after success write
   `diagnostics/solo355_local_20261013/validation.json` with scope
   regional_information_isolation and actual evidence. Native remains separately
   unauthorized until parent review. Do not reuse actuator-only validation.

## Captures and commands

Python: `C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
Workdir MUST be E package. PYTHONPATH: E package; E package/vendor/NumSim-mine;
`C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc`.
Set PYTHONDONTWRITEBYTECODE=1,PYTHONUTF8=1 and OPENBLAS/OMP/MKL threads=1.
Import vissim_stackelberg_adapter before loading pickle to install worker alias.
Running from C root imports the wrong adapter via empty sys.path entry.

Capture900: `D:/VISSIM_analysis/20261013_solo355_local/projected.pkl`.
Capture4500: `D:/VISSIM_analysis/20261013_solo355_local_4500/projected.pkl`.
Both are captured at sdmpc.solve entry after canonical projection, no solver or
native. Dict args=(controller,state,forecast,historical,mapping), kwargs has
options/runtime_sources/worker_bootstrap/previous_path; obs has
merged/observation/boundary_sides/geometry. Reuse these; no giant history reload.

Passed `python -B diagnostics/solo355_local_20261013/test_regional_prototype.py`:
6 tests,59.607s, saved900/4500, including lane-share fix, boundary causality,
disjoint complete own stock partition, full cut trajectory/state equality
under opposite state/forecast perturbation, own queue sensitivity, and1000x
arrival stress retaining rejected flow under finite storage.

Passed `python -B diagnostics/solo355_local_20261013/regional_query_probe.py
--mode MODE --output ABSOLUTE_FILE` for both modes at900:

| mode | axes | objective veh h | own coverage visits | single AD Query seconds |
|---|---:|---:|---:|---:|
| freeway_only |48|190.19997589111472|180/180|5.816|
| urban_only |189|239.15129725761594|900/900|9.946|

Receipts: `D:/VISSIM_analysis/20261013_solo355_local/freeway_query_ad.json` and
`urban_query_ad.json`. Checked finite20×48/189 cost and2×48/189 resource matrices,
empty AD fallback list, zero opposite-owner cost/Jacobian rows, zero inactive
resource/Jacobian, and complete own coverage. Receipts expressly state no
production/input-isolation qualification. This is one candidate, not selection.

Prior scalar/AD prototype receipts are in the same D directories. Old freeway900
two-axis receipt predates corrected10s quadrature and must NOT be used as latest
numeric evidence. Old4500 scalar227.9788 freeway predates lane-share correction.
Urban scalar239.151297257616 matched prior two-axis AD239.15129725761594.

`git diff --check` passed (line-ending conversion notices only). Production
default option is absent and its original tangent branch remains intact.
No complete saved selection, persisted-price isolation, startup preflight,
native performance, or full production qualification is claimed.
