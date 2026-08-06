# B1a trusted runner/live-evidence integration brief

## Purpose and boundary

Close the remaining B1a trust gaps between the approved A2 topology, the immutable
pre-run identity, VBS state capture, online projection, and offline live-gate audit.
This task also closes core rereview C2's malformed nested-record stale-output case and
I3's self-declared/duplicate live-evidence case, plus I4's current runner/VBS manifest
incompatibility.

This task does not implement B1b substep dynamics, calibration, candidate evaluation,
or claim a live VISSIM PASS. Without a supported-version live run and measured timing,
the gate remains `NOT_EVALUATED`.

## Fix-round-4 amendment and precedence

The round-4 requirements headed `Exact duplicate bindings`, `Normative artifact-role
constants`, and `Exact preserved-artifact contracts` are the controlling requirements.
They override any conflicting or less-specific wording elsewhere in this brief,
including the earlier architecture-review closure. Legacy `v2.1` post-exit markers and
locale-dependent redirected logs may remain for legacy runs, but they cannot establish a
required-mode PASS; required mode uses the versioned replacements specified below.

## Normative closure after architecture review

Subject to the fix-round-4 precedence above, this section resolves the exact interfaces
and overrides any less-specific wording below.

### Verdict meaning and trust boundary

`PASS` means the supplied local campaign is internally reproducible from pinned
producer bytes and raw run artifacts, with no stale, mixed, partial, or summary-only
self-certification. It is not a cryptographic assertion against a workspace owner who
can rewrite every producer, raw artifact, preflight, and trust input. No source hash or
`command_version` may be described as cryptographic execution attestation. An optional
externally signed receipt may be added later, but is not a B1a gate.

The replay summary can never establish a fact by authoring and rehashing that fact. It
must recompute from the exact raw companion files and pinned current producer/policy
bytes. A coherently rehashed summary alone fails. A coherently fabricated entire raw
campaign is outside the stated local reproducibility threat model.

### Exact qualification and retry identity

- `run_id` identifies exactly one `cscript` process attempt, not a retry group.
- `campaign_id` identifies the watchdog invocation and links attempts.
- Every attempt gets an exclusive create-once directory
  `<out>/<campaign_id>/attempt_<NN>_<run_id>/`; same-name concurrent campaigns cannot
  share it. Failed/killed attempts retain FAIL post-run evidence and are never selected
  for qualification. At most one successful attempt is selected.
- Immutable `run-manifest-v2.1` has exact keys
  `schema_version/run_id/campaign_id/attempt/qualification/approved_topology/preflight/producer_sources/configuration/allowed_capture_times/supported_version_policy/semantic_sha256`.
  `qualification` is exactly `{ "mode": "live_required" }` or
  `{ "mode": "synthetic_fixture" }`. Its semantic hash covers every field except
  `semantic_sha256` in that listed order/scope. Extra/missing keys fail.
- Nested run-manifest shapes are exact:
  - `preflight` is
    `schema_version/path/file_sha256/fingerprint_sha256` and must identify the exact
    validated `preflight-v3` below the workspace.
  - `approved_topology` is exactly the five-key object returned by
    `expected_approved_topology_binding`.
  - `producer_sources` has exactly the closed roles listed under `Exact source and
    version policy`; each value is exactly `path/file_sha256`.
  - `configuration` is exactly `inputs/simulation`. `inputs` has exact roles
    `network/generated_vbs_config/adapter/calibration/tuning/control_mapping/vehicle_input_roles/demand_profile`
    and each value is exactly `path/file_sha256`. Every present input uses a nonempty
    canonical workspace-relative forward-slash `path` and a lowercase 64-hex
    `file_sha256`. Only `demand_profile` may represent absence, and it does so only as
    `{ "path": null, "file_sha256": null }`; empty strings and one-null/one-present
    pairs fail. `simulation` has exact keys
    `sim_period_sec/control_interval_sec/seed/controller/control_start_sec/warmup_controller/state_log_interval_sec/demand_scale/demand_profile/incident_link/incident_lane/incident_pos_m/incident_start_sec/incident_end_sec/incident_name`.
    `simulation.demand_profile` is JSON null exactly when
    `inputs.demand_profile.path` is null. When present it is the exact same decoded
    string as `inputs.demand_profile.path`; normalization before comparison is forbidden.
  - `allowed_capture_times` is always an array, never null/omitted. Required mode
    enumerates every permitted decision/anchor time as finite nonnegative decoded
    doubles in strictly increasing unique order. Synthetic fixtures use their exact
    enumerated times. An empty array permits no state publication.
  - `supported_version_policy` is exactly
    `schema_version/path/file_sha256/semantic_sha256`.
  Every nested validator rejects extra/missing keys and booleans masquerading as
  numbers.
- Run-manifest numeric and enum rules are exact: integral seconds/counts and `seed` are
  JSON integers, never booleans. Period, interval, seed, and state-log interval are
  positive. Control/incident start/end use `-1` or fall within the simulation period.
  Incident link/lane are nonnegative 32-bit integers; incident position is finite and
  at least `-1`; demand scale is finite and positive. `controller` and
  `warmup_controller` must be accepted by the pinned adapter parser. All strings are
  bounded and all paths/hashes follow the rules above.
- The run-manifest semantic hash is shared canonical JSON v1 over every exact
  top-level field except `semantic_sha256`, after all nested type/range checks and
  before hash comparison.
- Creation uses exclusive no-clobber publication. An existing byte-identical manifest
  may be validate-only reused; a differing existing file fails without modifying the
  immutable manifest and writes a separate `run_manifest_creation_result_v2_1.json`.
  Validate-only never writes. Stale-output replacement still applies to approval,
  state-manifest, replay, audit, and creation-result outputs.
- All fake-COM and unit-test launchers can create only `synthetic_fixture` manifests.
  A valid synthetic chain yields `NOT_EVALUATED`; missing/mixed mode is FAIL. Removing
  or changing mode and rehashing descendants must not yield PASS because every
  companion is compared to the immutable manifest.

### Exact duplicate bindings

Duplicate path/hash records are equality constraints, never independent assertions:

- For every role in the intersection of `producer_sources` and
  `configuration.inputs`, the complete decoded `path/file_sha256` objects are equal.
  The current closed intersection is exactly `{adapter}`; therefore
  `producer_sources.adapter == configuration.inputs.adapter`. A schema revision that
  adds another intersecting role must add it to this equality set rather than silently
  creating a second binding.
- `producer_sources.supported_version_policy.path/file_sha256` equals the corresponding
  fields of top-level `supported_version_policy`; the latter's semantic hash is then
  independently recomputed from the policy bytes.
- Every `producer_sources` role equals the same role in the validated preflight producer
  map, including path spelling and lowercase hash. The run-manifest producer may not
  relabel one file under two roles or substitute a byte-identical file at another path.
- The executed generated-config binding is
  `configuration.inputs.generated_vbs_config`. The post-run
  `generated_vbs_config` artifact is the attempt-local preserved copy: its path is
  necessarily different, but its file SHA-256 and bytes equal the executed binding.
  The copy is made and hashed before launch; a post-launch source or copy mismatch fails.
- Existing action-JSON `run_provenance.inputs` sightings are mandatory duplicate checks,
  not new trust roots: `adapter_py/calibration_json/tuning_json/control_mapping_json/network_inpx`
  equal `configuration.inputs.adapter/calibration/tuning/control_mapping/network`, while
  `main_vbs_runner/watchdog_wrapper/run_manifest_json` equal
  `producer_sources.vbs/producer_sources.watchdog` and the immutable run manifest.
  Their existing `path/sha256/exists` spelling is validated exactly, `exists` is true,
  and `sha256` equals the corresponding `file_sha256`; missing sightings or disagreement
  fail before action acceptance.
- Top-level post-run `run_manifest` equals the sole `run_manifest` artifact after the
  common canonical path resolution, and its hash is byte-equal. All action, state,
  capture, projection, reference, timing, error, and wall-time documents repeat
  `run_id`, `campaign_id` where present, attempt where present, manifest path/hash where
  present, and `(run_id,sim_sec)` where present exactly; no consumer may normalize a
  mismatch into agreement.

These equalities are checked before semantic-hash comparison. Rehashing two disagreeing
authored bindings cannot make either object valid.

### Exact CLI and path contract

- Add watchdog parameters `[switch]$B1aRequired`,
  `[string]$TopologyApproval`, and existing `[string]$PreflightManifest`. Defaults keep
  legacy mode. The strict plant-fidelity matrix always passes `-B1aRequired` and both
  explicit manifests; required mode exits before COM creation on any missing or failed
  trust input. Dry-run validates intended paths but emits no PASS evidence.
- Required-mode run directories must be canonical, non-reparse descendants of the
  workspace. JSON stores canonical workspace-relative forward-slash paths; environment
  values use Python-produced absolute Windows paths. Consumers resolve both and compare
  canonical final paths with Windows case-insensitive semantics.
- Environment mutation for `RW_RUN_ID`, `RW_RUN_MANIFEST_PATH`,
  `RW_RUN_MANIFEST_SHA256`, `RW_B1A_REQUIRED`, and qualification mode is wrapped in one
  `try/finally`, restoring absent versus empty values exactly even when launch throws.
  Tests cover spaces, non-ASCII, slash/case variants, junction escape, stale inherited
  values, and launch exception.

### Exact source and version policy

The preflight and run manifest use a closed producer-role map containing exactly
`watchdog`, `vbs`, `adapter`, `run_manifest_producer`, `topology_approval_validator`,
`state_manifest_builder`, `physical_projection_module`, `post_run_artifact_producer`,
`live_replay_builder`, `preflight_producer`, `monotonic_clock_helper`, and
`supported_version_policy`. Required mode rehashes the exact bytes
immediately before launch and after process exit; mismatch fails the attempt. The
acyclic order is sources -> preflight -> approval -> run manifest -> raw artifacts ->
post-run manifest -> replay.

Read raw version only from `Vissim.AttValue("VERSION")`. Preserve the exact string in
capture evidence. A checked-in `supported-vissim-versions-v2.1` policy, pinned by
preflight/run manifest, defines a strict parser and closed accepted normalized major
versions. Accept only a finite ASCII version token whose leading major is `20` or
`2020`, normalized to `2020`; reject empty, fallback, malformed, or any other major for
supplied live evidence. Replay derives support; no authored support boolean exists.
Synthetic mode remains `NOT_EVALUATED` regardless of the version text.

### Exact state and companion transaction

`vehicle_records` retains exactly the field set and six-field record shape in the
governing B1a brief. It receives no version, timing, qualification, sample, trust, or
producer fields. Exact-key empty/nonempty regression tests are mandatory.

VBS writes the state to a same-directory unique temporary file, closes and checks it,
then atomically renames to an initially absent final name. It then atomically publishes
`<state-stem>.vehicle_capture_v2_1.json`. A later adapter/projection/action/timing
failure makes the attempt FAIL; selection and replay require the complete companion
set, so an orphan state can never qualify. Unique attempt directories avoid Windows
delete-before-rename replacement. Termination is tested after each boundary.

Capture sidecar schema `vehicle-capture-evidence-v2.1` has exact keys
`schema_version/run_id/sim_sec/qualification/run_manifest_path/run_manifest_sha256/state_path/vissim_version_raw/counts/capture_timer/raw_attribute_samples/semantic_sha256`.
`qualification` exactly copies the immutable manifest. `counts` binds the two scalar
counts and record count. A third pinned monotonic-helper call occurs after atomic state
publication and before capture-sidecar serialization. `capture_timer` is exactly
`clock/start_ns/end_ns/elapsed_sec`: it reuses the combined sample's first `start_ns`,
uses the third call as `end_ns`, requires `end_ns > start_ns`, and recomputes elapsed.
Samples have exact raw COM key, No, Lane, Pos, Speed and called parser outputs.

Use at most 64 raw samples/state, deterministic ascending `veh_no`: always include the
lowest occupied target connector lane and lowest occupied target multi-lane road lane
from a compact target list produced from the approved A1 graph, then fill with lowest
remaining IDs. Oversize or nondeterministic ordering fails. Lack of occupied target
coverage is valid but insufficient and leaves the live-capture gate
`NOT_EVALUATED`; malformed/mixed samples fail.

### Exact timing protocol

Do not use VBScript `Timer` or wall-clock subtraction. Add a pinned helper whose only
operation is to emit `time.perf_counter_ns()` as one unsigned decimal integer and clock
ID `python_perf_counter_ns`. Required mode pins Python >=3.10 on Windows, where the
performance counter is system-wide and shared across processes. VBS synchronously
invokes the helper immediately before the first scalar `Vehicles.Count` read, again
after atomic state publication for the capture-sidecar endpoint, and finally after the
projection-only adapter returns for the combined endpoint. Every helper call emits
exactly one ASCII/UTF-8-without-BOM line
`python_perf_counter_ns=<positive decimal integer>\n` and nothing on stderr. Missing
newline, missing output, extra output, nonintegral or
nonpositive values, end <= start, helper timeout/nonzero exit, Python/source hash
mismatch, or a process-window inconsistency fails the timing receipt. Elapsed seconds
is `(end_ns-start_ns)/1e9`; replay recomputes it from the raw integers.

The adapter exposes a production `--projection-only` path that validates the immutable
run manifest/topology before any NumSim import, strict-parses the state, calls the sole
public projector, atomically writes the physical projection sidecar and bounded
`physical_projection_reference_v2_1.json`, then exits. It cannot import NumSim, build a
controller/config/forecast, evaluate candidates, or write a control action. VBS stops
the B1a clock immediately after this subprocess returns and both required files pass
existence/hash/schema checks. Only afterward does VBS invoke the normal controller
adapter, passing the exact projection-reference path/hash. The normal path revalidates
and consumes that reference without rerunning or bypassing projection; failure occurs
before candidate or fallback evaluation.

The bounded reference schema is `physical-projection-reference-v2.1`, exact keys
`schema_version/status/reasons/qualification/run_id/sim_sec/run_manifest_sha256/state_path/state_file_sha256/topology_file_sha256/topology_semantic_sha256/projection_sidecar_path/projection_sidecar_file_sha256/projection_sidecar_semantic_sha256/normalized_projection_sha256/record_count/assigned_count/stock_total/global_residual/semantic_sha256`.
It contains no assignments. PASS requires empty reasons; reasons use the closed B1a
vocabulary. Canonical JSON v1 hashes every listed field except `semantic_sha256`,
including status/reasons. The normal adapter and replay reopen the exact state and
sidecar, validate run/topology bindings, and recompute all counts, residuals, file
hashes, and semantic hashes. Missing/extra keys, path escape, mismatch, or non-PASS
status fails before controller or fallback evaluation.

Then atomically write `<state-stem>.projection_timing_v2_1.json`, exact keys
`schema_version/run_id/sim_sec/qualification/run_manifest_sha256/state_path/capture_evidence_path/projection_sidecar_path/projection_reference_path/clock/start_ns/end_ns/elapsed_sec/status/reasons/semantic_sha256`.
`clock` is exactly `python_perf_counter_ns`; `start_ns/end_ns` are positive integers.
Elapsed is recomputed from raw endpoints, not
trusted from the authored field. One unique receipt exists per `(run_id,sim_sec)`.
The post-run manifest hashes it. Live p95 requires at least 20 successful receipts from
one qualified run and uses nearest-rank p95. Offline remeasurement cannot replace
historical receipts. The 20,000-record synthetic size/complexity gate is separate and
never populates live p95.

### Versioned post-run and replay schemas

Use `run-artifact-manifest-v2.2` for the incompatible post-run shape, exact keys
`schema_version/status/reasons/run_id/campaign_id/attempt/qualification/run_manifest/process/artifact_roles/artifacts/semantic_sha256`.
`run_manifest` is exactly `path/file_sha256`; `process` is exactly
`pid/started_at_utc/finished_at_utc/exit_code/termination_reason`, with
`termination_reason` closed to `normal/watchdog_timeout/launch_failure/process_error`.
`artifact_roles` is an exact object whose keys are
`run_manifest/generated_vbs_config/state/capture_evidence/projection_sidecar/projection_reference/timing_receipt/control_action_json/control_action_csv/state_csv/cumulative_action_csv/stdout_runlog/stderr_runlog/signal_readback_csv/vissim_error_evidence/wall_time_profile`.
Each value is exactly `phase/success_min_count/failure_min_count/max_count`; counts are
nonnegative JSON integers, never booleans. The authored object must equal the following
constant table field-for-field. Producers and validators import one checked-in constant;
they never use authored minima or maxima to decide validity.

#### Normative artifact-role constants

| Role | Phase | Success min | Failure min | Max |
|---|---:|---:|---:|---:|
| `run_manifest` | `pre_run` | 1 | 1 | 1 |
| `generated_vbs_config` | `pre_run` | 1 | 1 | 1 |
| `state` | `in_process` | 1 | 0 | null |
| `capture_evidence` | `in_process` | 1 | 0 | null |
| `projection_sidecar` | `in_process` | 1 | 0 | null |
| `projection_reference` | `in_process` | 1 | 0 | null |
| `timing_receipt` | `in_process` | 1 | 0 | null |
| `control_action_json` | `in_process` | 1 | 0 | null |
| `control_action_csv` | `in_process` | 1 | 0 | null |
| `state_csv` | `in_process` | 1 | 0 | 1 |
| `cumulative_action_csv` | `in_process` | 1 | 0 | 1 |
| `stdout_runlog` | `in_process` | 1 | 0 | 1 |
| `stderr_runlog` | `in_process` | 1 | 0 | 1 |
| `signal_readback_csv` | `in_process` | 1 | 0 | 1 |
| `vissim_error_evidence` | `post_exit` | 1 | 1 | 1 |
| `wall_time_profile` | `post_exit` | 1 | 1 | 1 |

Here `null` means unbounded by the manifest schema, not unchecked. Size limits,
identity uniqueness, expected schedule, and the equations below still bound a successful
run. Let `n(role)` be the number of artifact records for that role, `Q` the replayed
ordered qualifying-state identity set, and `D` the replayed ordered controller-decision
identity set.

For every structurally valid attempt, successful or failed:

- `n(run_manifest)=n(generated_vbs_config)=n(vissim_error_evidence)=n(wall_time_profile)=1`.
  Every other singleton has cardinality zero or one, and every repeated role has a
  nonnegative cardinality.
- Artifact records are exactly
  `role/path/file_sha256/size_bytes/last_write_time_utc`, sorted by `(role,path)`, with
  unique canonical contained paths. Every extant file matching a closed-role filename
  pattern is inventoried; a producer may not omit a partial artifact to improve status.
- `last_write_time_utc` is a well-formed UTC diagnostic only. It never establishes or
  reverses PASS, and no replay rejects otherwise valid immutable bytes solely for mtime
  skew. Attempt identity, atomic publication, hashes, process endpoints, and companion
  closure are the gating evidence.

For a successful required attempt, all of these equations and bijections are mandatory:

- `|Q| = n(state) = n(capture_evidence) = n(projection_sidecar) =
  n(projection_reference) = n(timing_receipt) >= 1`. `Q` is unique by
  `(run_id,sim_sec)` and sorted by `(run_id,sim_sec,state_path)`. For each member of `Q`
  there is exactly one state and exactly one of each four companions; every companion
  binds that exact state path/hash and identity. No orphan or extra companion is allowed.
- `|D| = n(control_action_json) = n(control_action_csv) >= 1`. `D` is the unique ordered
  sequence of `(run_id,sim_sec)` values recomputed from exact anchored
  `CONTROLLER_DECISION` stdout lines and the VBS schedule. Each decision has exactly one
  action JSON/CSV pair with the same zero-padded stem; JSON
  `metadata.sim_sec/run_provenance.run_id`, the referenced state, and the stdout identity
  agree. Each decision identity maps to exactly one member of `Q`; qualifying anchor-only
  states may make `|Q|>|D|` but can never create an action.
- `D` equals the action JSON identities, action CSV identities, and successful decision
  log identities in the same order. `DECISIONS_OK=|D|` and `DECISIONS_FAILED=0`.
- `n(state_csv)=n(cumulative_action_csv)=n(stdout_runlog)=n(stderr_runlog)=
  n(signal_readback_csv)=1`. Their internal row equations are normative below.
- The two pre-run records and two post-exit records are each singletons. The generated
  config copy has the executed config's exact bytes/hash. The error and wall-time
  records repeat the post-run process identity exactly.

For a failed attempt, every in-process role independently has cardinality zero through
its table maximum; no positive cross-role equality is asserted because termination may
occur between publications. The producer still inventories every extant partial file.
Any partial companion identity, unpaired action, or missing singleton adds the applicable
closed reason and forces top-level FAIL. This relaxed failure inventory makes an honest
FAIL manifest valid; it can never make replay or either live gate PASS.

The semantic hash covers exactly every listed top-level field except
`semantic_sha256`, including the constant role table, status/reasons, process, and sorted
artifact records, by shared canonical JSON v1.

Process types and sentinels are exact. `pid` is a positive integer except null for
`launch_failure`. Start/finish are nonempty RFC3339 UTC strings for the attempt window
and are never null. `exit_code` is integer `0` for `normal`, nonzero for
`process_error`, and null for `launch_failure` or a timeout with no reliable code.
`watchdog_timeout` requires a positive PID and permits null/nonzero exit. Top-level PASS
requires `normal`, exit 0, empty reasons, every success equation above, and every gating
predicate under `Exact preserved-artifact contracts`. Replay derives these facts from
the bound bytes before comparing the authored process/status fields.

The top-level `run_manifest` path/hash equals the unique artifact record with role
`run_manifest` under the path rules above. Any disagreement fails.

### Exact preserved-artifact contracts

These contracts preserve the current VBS column meanings and ordering while removing
locale-dependent or summary-only acceptance. Replay reads bytes first, validates the
contract, and only then compares authored status, counts, and hashes. Only predicates
stated below are gating. Opaque metadata, warning text, timing magnitudes outside the
projection receipts, and any legacy field with no byte-derived predicate are
diagnostic-only; existence or hashing of such a field cannot establish PASS.

#### Encoding, framing, and CSV dialect

- `state_csv`, `cumulative_action_csv`, every per-decision `control_action_csv`, and
  `signal_readback_csv` are the printable-ASCII subset of UTF-8, without a BOM. The only
  control bytes are CRLF record terminators. Each file has one exact header, zero or more
  data records as allowed below, one final CRLF, no blank records, no NUL, no bare CR/LF,
  and no bytes outside ASCII `0x20..0x7e` other than CRLF.
- The dialect is comma-delimited with exactly the declared field count. Fields contain
  no comma, double quote, CR, or LF, so quoting and escape forms are forbidden. Leading
  or trailing horizontal whitespace is data and fails every canonical numeric, enum, or
  identifier field. This matches the VBS `Split` consumer rather than pretending it is a
  general quoted-CSV parser.
- A canonical integer is `0` or `[1-9][0-9]*`. A canonical finite number uses JSON number
  grammar, has no surrounding whitespace, parses to a finite IEEE-754 double, and obeys
  the field range. NaN, infinities, locale commas, leading plus, and leading zeroes fail.
- JSON evidence produced by the watchdog/post-run helpers is strict UTF-8 without BOM,
  one JSON value, and exactly one final LF. Duplicate keys, non-finite numbers, and
  trailing non-whitespace bytes fail.

The current direct `Start-Process -RedirectStandardOutput/-RedirectStandardError` files
have no guaranteed child-stream encoding and therefore cannot fill required-mode log
roles. Required mode uses a versioned `runlog-capture-v2.2` helper: it invokes
`cscript.exe //nologo //U`, captures both redirected streams with a strict UTF-16LE
decoder configured to throw on invalid bytes, and permits no decoded U+FEFF (there is no
transport BOM contract to guess). It atomically writes UTF-8-without-BOM
`stdout_runlog_v2_2.txt` with normalized CRLF records and one final CRLF when the
decoded stream is nonempty. Decoded-empty stderr is the sole framing exception: the
helper atomically publishes `stderr_runlog_v2_2.txt` as exactly zero bytes, with no
terminator. A nonempty decoded stderr stream is normalized by preserving its logical
records, converting CRLF, bare CR, and bare LF boundaries to CRLF, and appending exactly
one final CRLF; it then fails the run. Thus decoded CRLF-only, horizontal-whitespace-only,
and literal `diagnostic` stderr become respectively the exact bytes `0d 0a`,
`20 0d 0a`, and `64 69 61 67 6e 6f 73 74 69 63 0d 0a`, and none can PASS. Each
normalized runlog is at most 16 MiB and each logical record is at most 8192 UTF-8 bytes
excluding its CRLF. A decode error, BOM/U+FEFF, replacement character, bound violation,
or missing capture-helper binding fails. The helper is code in the exact
`producer_sources.watchdog` bytes, not a dynamically loaded unpinned script. Legacy
`runlog_*.txt` files may be retained as diagnostics only.

#### State CSV

The exact header and order are:

```text
sim_sec,total_vehicles,urban_vehicles,freeway_vehicles,ramp_vehicles,boundary_vehicles,other_vehicles,mean_speed_kph,freeway_mean_speed_kph,stopped_vehicles,controller_mode,controller_status,decision_wall_sec
```

For simulation period `P` and state-log interval `L`, both positive manifest integers,
the ordered row identities are exactly
`T_state = sorted_unique({1} union {k*L | k>=1 and k*L<=P} union {P})`.
There is exactly one row per identity in that order and no other row, so
`state_csv_row_count=|T_state|`. `sim_sec` is the canonical integer identity.
The seven `*_vehicles`/`stopped_vehicles` fields are canonical nonnegative integers;
the five category counts sum to `total_vehicles`, and `stopped_vehicles <=
total_vehicles`. Both speed fields are finite in `[0,300]` km/h. `controller_mode` is
exactly `VISSIM_REAL_WORLD_` plus the uppercased manifest `controller` token.

State/action binding is by replayed VBS publication order, never by the greatest action
`sim_sec <=` the row time. Let `A` be the ordered action JSON/CSV pairs for which
`RunControllerDecision` returned exit 0, both files passed their required validation and
application, and `lastActionJson` was advanced. At entry to each specific `LogStateCsv`
invocation, the row binds the last member already published in `A`. An action with equal
`sim_sec` that is accepted after that invocation is excluded; a failed decision never
advances the binding and makes run PASS impossible. Replay must reconstruct this order
from the pinned VBS and manifest schedule as follows:

- every mode invokes the initial decision at `sim_sec=1` before its initial state row;
  run PASS requires acceptance, so that row binds decision 1;
- stepwise mode performs a due interval decision before a same-time state-log call, so a
  coincident row binds that same-time action; otherwise it retains the prior action;
- continuous-static mode logs before the one main control-start decision when control
  start and state logging coincide, so that row retains the prior action; a noncoincident
  control-start decision binds every later row;
- event-continuous single-decision mode likewise logs before a coincident control-start
  decision; event-continuous repeated-control mode performs a due repeated decision
  before the same-time log, so the row binds that same-time action.

`controller_status` and `decision_wall_sec` equal the corresponding fields in that exact
bound action JSON. Status is exactly `ok` for run PASS. The wall token is the action
producer's locale-invariant canonical nonnegative JSON number copied byte-for-byte; its
magnitude is diagnostic, not live-performance evidence. Because publication order is
fully reconstructed for every current mode, this v2.2 contract retains the exact
13-column header; adding an inferred or unversioned action column is forbidden.

#### Per-decision and cumulative action CSVs

Every per-decision CSV has this exact 13-column header/order:

```text
kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata
```

Every row has exactly one `kind` in `vsl/ramp_meter/signal`, a nonempty bounded printable
ASCII `id`, and bounded printable ASCII `metadata`; fields not listed for the row kind
are the empty string exactly. `metadata` is opaque diagnostic text except that its bytes
must remain identical between the per-decision and cumulative rows:

| Kind | Required typed fields | Empty fields |
|---|---|---|
| `vsl` | `dsd_no/link/lane` canonical nonnegative integers; `speed_kph` finite and in the generated config's exact allowed VSL set | `sc_no/major_green/minor_green/offset/rate_vph/green_sec` |
| `ramp_meter` | `sc_no` canonical positive integer; finite `rate_vph` in `[0, configured capacity]`; finite `green_sec` in `[0,RAMP_CYCLE_SEC]` and equal within `0.001` to the configured rounded rate-to-green conversion | `dsd_no/link/lane/speed_kph/major_green/minor_green/offset` |
| `signal` | `sc_no` canonical positive integer; finite `major_green/minor_green` each in `[5,90]`; finite `offset` in `[0,cycle)` | `dsd_no/link/lane/speed_kph/rate_vph/green_sec` |

For decision `d`, let `V` be the ordered generated-config VSL key sequence, `R` the
ordered ramp-meter mapping sequence, and `G(d)` the ordered signal-controller sequence,
or empty when the effective controller suppresses signal rows. The row sequence is
exactly `V` followed by `G(d)` followed by `R`, with identities respectively
`dsd_no`, `id/sc_no`, and `id/sc_no`; every identity is unique in its kind. Thus each
file has exactly `|V|+|G(d)|+|R|` rows. Replay derives all keys, values, suppression, and
order from the pinned generated config, control mapping, action JSON, and effective
warmup/main controller; row count alone is insufficient.

The paired action JSON is strict UTF-8 without BOM and has the same `(run_id,sim_sec)`
as its state, filename, and decision log. It has `metadata.controller_status == "ok"`,
and its physical control fields deterministically reproduce every non-metadata CSV
field. Missing JSON or
CSV, an extra pair, different stems, different identities, or different physical values
fails the pair and the run.

The singleton cumulative CSV has this exact 15-column header/order:

```text
sim_sec,kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata,readback
```

Its rows are the byte-field-equivalent concatenation of all per-decision rows in `D`
order, adding the decision's canonical `sim_sec` at the front and the VBS readback at
the end. Therefore
`cumulative_action_row_count = sum(per_decision_action_row_count(d) for d in D)`, and
row `j` maps to exactly one `(decision identity, per-decision row ordinal)`; sorting or
deduplication is forbidden. For `vsl`, `readback` is exactly two finite `|`-separated
values, neither containing `ERR`, and both equal the requested speed. For `ramp_meter`
it is the canonical `GREEN/AMBER/RED` state requested at that decision time. For
`signal` it is exactly `stored`, which proves only COM-control enablement; physical
signal state is gated solely by the readback CSV below.

#### Signal-readback CSV

The exact header/order is:

```text
sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage
```

`sim_sec` is a canonical nonnegative integer; `sc_no/sg_no` are canonical positive
integers; both states are exactly `GREEN`, `AMBER`, or `RED`; `ok` is exactly `0` or
`1`; and `stage` is exactly `immediate` or `post_step`. Replay reconstructs the complete
ordered expected write sequence from the pinned VBS event schedule, generated config,
and accepted cumulative actions. The file rows must equal that sequence in order:

- every expected COM write has exactly one `immediate` row at its write time;
- every persistence check has exactly one `post_step` row, and its
  `(sc_no,sg_no,requested_state)` equals the most recent preceding successful immediate
  row for that signal group;
- every row has `readback_state == requested_state` and `ok == 1` after exact enum
  normalization; duplicate, missing, unexpected, reordered, or unpaired rows fail;
- stdout's exact counters satisfy
  `SIGNAL_WRITE_ATTEMPTS = SIGNAL_READBACK_OK = immediate_row_count` and
  `SIGNAL_PERSISTENCE_CHECKS = SIGNAL_PERSISTENCE_OK = post_step_row_count`.

A header-only file passes run integrity only when the reconstructed expected immediate
and post-step sequences are both empty. In that case signal COM actuation coverage is
`NOT_EVALUATED`, not PASS. If any write is expected, both immediate and subsequent
persistence evidence required by the schedule must be nonempty and complete.

#### Stdout and stderr

After strict `runlog-capture-v2.2` decoding, every nonempty line is bounded UTF-8 text
without NUL or C0 controls, with no leading/trailing horizontal whitespace. The file and
record byte bounds above apply before semantic matching. Required tokens are whole-line
anchored; substring matching is forbidden.

- Completion is exactly one line equal to `STAGE=SIM_DONE`. Zero, two, a prefix/suffix,
  or whitespace variation fails.
- Each of `DECISIONS_OK`, `DECISIONS_FAILED`, `OBSERVATION_FAILURES`,
  `SIGNAL_FAILURES`, `SIGNAL_WRITE_ATTEMPTS`, `SIGNAL_READBACK_OK`,
  `SIGNAL_PERSISTENCE_CHECKS`, `SIGNAL_PERSISTENCE_OK`,
  `ACTION_FORMAT_FAILURES`, `COM_FAILURES`, and `SIM_SEC` occurs exactly once as
  `^KEY=(0|[1-9][0-9]{0,9})$`. Each numeric token is at most 10 ASCII bytes and no
  greater than 2147483647. PASS requires every failure counter zero, `SIM_SEC=P`, and the
  decision/readback equalities above.
- Decision lines are printable ASCII and match this literal anchored grammar (ASCII
  regex mode):
  `^CONTROLLER_DECISION sim_sec=(0|[1-9][0-9]{0,9}) wall_sec=(0|[1-9][0-9]{0,5})(?:\.[0-9]{0,5}[1-9])? result=exit=0 stdout=(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{2}|[A-Za-z0-9_-]{3})? stderr=$`.
  `sim_sec` is at most 10 bytes and must also be in `D`, no greater than `P`, and no
  greater than 2147483647. `wall_sec` is at most 12 bytes and in `[0,86400]`. Required
  mode obtains monotonic `python_perf_counter_ns` endpoints immediately around the
  adapter subprocess, sets `wall_us=floor((end_ns-start_ns)/1000)`, and rejects invalid
  ordering or `wall_us > 86400000000`. It serializes `wall_us` without floating point or
  locale APIs: decimal integer seconds, followed only when the remainder is nonzero by
  `.` and a six-digit zero-padded microsecond remainder with trailing zeroes removed.
  The stdout token is unpadded RFC-4648 base64url over the UTF-8-without-BOM bytes of the
  exact captured stdout string before any `OneLine`/trim/newline conversion; the source
  is at most 4096 bytes and the token at most 5462 ASCII bytes. Empty stdout is the empty
  token. The identical encoding applies to captured stderr, but PASS requires its source
  and token to be empty, yielding the literal suffix ` stderr=`. Padding `=`, a token
  whose length is 1 modulo 4, invalid UTF-8 on decode, a non-round-tripping token, or a
  byte-bound violation fails. Their ordered identities equal `D`; malformed, nonzero,
  missing, or extra lines fail.
- After that strict unpadded-base64url decode/re-encode byte-for-byte round-trip and
  strict UTF-8 decode of captured adapter stdout, replay splits the decoded string into
  logical records using the already defined CRLF, bare-CR, and bare-LF boundary rules.
  Replay scans every decoded record for the literal ASCII byte sequence `ERROR=` and
  fails the run if it occurs anywhere, including as an embedded token or malformed
  error form; outer decision-line framing and base64url representation cannot conceal
  it. This scan does not replace or relax any outer runlog predicate. Captured adapter
  stderr is decoded and round-tripped under the same strict rules but remains required
  to be byte-empty; no stderr record, delimiter, or diagnostic text can PASS.
- Any line containing the literal `ERROR=` must itself match
  `^ERROR=[A-Z0-9_]+(?: .*)?$`; every such line fails, without an allowlist. An embedded
  or malformed `ERROR=` also fails. `WARN=` and unknown well-framed stdout lines are
  retained as diagnostics and do not override a failed gating predicate.
- PASS stderr is exactly zero bytes. There is no acceptable warning, banner, encoding
  replacement, or whitespace-only stderr. Any nonempty stderr fails.

#### Versioned VISSIM-error evidence

The current `vissim-error-evidence-v2.1` marker is not accepted in required mode: it has
no hashed status/reasons contract and its replacement-decoded keyword scan cannot prove
that arbitrary VISSIM `.err` bytes are benign. Required mode writes
`vissim-error-evidence-v2.2`, strict JSON with exact top-level keys
`schema_version/status/reasons/run_id/campaign_id/attempt/termination_reason/process_exit_code/source_observation/artifact/stale_pre_run/checked_at_utc/semantic_sha256`.

- `status` is `PASS` or `FAIL`; PASS has empty reasons and FAIL has a nonempty sorted
  unique list from the closed B1a vocabulary. `run_id/campaign_id/attempt`, termination,
  and exit code exactly equal the run-artifact manifest. `checked_at_utc` is RFC3339 UTC,
  no earlier than process finish.
- `source_observation` is exactly `path/present/size_bytes/file_sha256`. `path` is the
  canonical expected `.err` path for the exact network loaded by this attempt.
  If absent, `present=false` and size/hash are null. If present, `present=true`, size is a
  nonnegative integer, and hash is lowercase 64-hex over the observed raw bytes.
- `artifact` is null for absent source. For a present source it is exactly
  `path/file_sha256/size_bytes`, points to an attempt-contained atomic copy, and its
  bytes/size/hash equal the source observation made after process exit.
- `stale_pre_run` is an array sorted by `(attempt,archived_path)`; each record is exactly
  `attempt/source_path/archived_path/file_sha256/size_bytes/archived_at_utc`. It inventories
  rather than erases pre-run source bytes. Any nonempty array forces FAIL for required
  qualification.
- Semantic hash is canonical JSON v1 over every field except `semantic_sha256` after
  exact nested validation.

VISSIM-error PASS is exact: termination is `normal`, exit is 0, bindings match, reasons
and stale list are empty, and the post-exit source is absent or present with
`size_bytes=0` and an equal zero-byte preserved artifact. Any nonzero `.err` is FAIL
without decoding or keyword interpretation; its raw bytes remain diagnostic. A future
policy that accepts nonempty `.err` content must be a new version tied to documented
supported-version encoding and grammar. It must not weaken `v2.2` by guessing ANSI,
accepting a BOM opportunistically, or decoding with replacement.

#### Versioned wall-time evidence

The current `wall-time-profile-v2.1` derives PASS from exit code and subtracts wall-clock
timestamps, so it is retained only as legacy diagnostic evidence. Required mode writes
`wall-time-profile-v2.2`, strict JSON with exact keys
`schema_version/status/reasons/run_id/campaign_id/attempt/pid/termination_reason/process_exit_code/started_at_utc/finished_at_utc/clock/start_tick/end_tick/frequency_hz/semantic_sha256`.

- Identity/process fields exactly equal the run-artifact manifest. PID/exit sentinels
  obey its process rules. Both timestamps are nonempty RFC3339 UTC and equal the manifest
  strings exactly; they locate the attempt but do not compute elapsed time.
- `clock` is exactly `dotnet_stopwatch_timestamp`; start/end/frequency are positive JSON
  integers, never booleans. Their JSON tokens match `(0|[1-9][0-9]{0,18})`, are at most
  19 ASCII bytes, and are in `[1,9223372036854775807]`. Require `end_tick >= start_tick`
  and `frequency_hz` equal to the pinned runtime's `Stopwatch.Frequency`. The sole
  duration rule is the exact rational `(end_tick-start_tick)/frequency_hz` seconds from
  those three integers. No binary64, rounded decimal, locale-formatted text, tolerance,
  or authored elapsed field is stored, hashed, or compared. Replay validates the integer
  tuple and uses that rational only; any added `elapsed_wall_sec` or equivalent field
  fails the exact-key schema.
- PASS is exact: `normal`, PID positive, exit 0, empty reasons, valid monotonic endpoints,
  and all duplicate bindings equal. Every other termination has status FAIL and a
  nonempty closed reason while still producing a structurally valid singleton record.
  Semantic hash is canonical JSON v1 over every field except `semantic_sha256`.

Total attempt duration derived by the sole tick-ratio rule is diagnostic and never
substitutes for any `projection_timing_v2_1` receipt or live p95 sample. The wall
schema's identity, monotonic integers, and normal-exit status gate run PASS; its duration
does not gate live performance.

#### Gating versus diagnostic evidence

| Evidence/predicate | Run PASS | Live gate effect |
|---|---|---|
| Constant role table, singleton counts, companion/action equations, paths, hashes, exact schemas/encoding | Gating | Malformed or mismatched supplied evidence is FAIL |
| Process sentinel, unique completion token, zero failure counters, empty stderr, no `ERROR=` | Gating | Failed process makes supplied live evidence FAIL |
| State/action CSV row identities, types, order, cumulative equality, observable readbacks | Gating | Integrity prerequisite only |
| Complete expected signal immediate/persistence sequence | Gating when writes are expected; empty expected sequence may pass run integrity | Empty expected sequence leaves signal actuation coverage `NOT_EVALUATED` |
| `vissim-error-evidence-v2.2` PASS predicate | Gating | Integrity prerequisite only |
| `wall-time-profile-v2.2` identity/arithmetic/normal-exit predicate | Gating | Duration is diagnostic only |
| Per-state projection timing receipts | Gating for supplied receipt integrity | At least 20 valid live receipts and nearest-rank p95 determine `live_performance_p95` |
| Supported raw VISSIM version and required capture samples | Gating for supplied evidence integrity | Coverage determines `supported_vissim_com_capture`; inadequate valid coverage is `NOT_EVALUATED` |
| Artifact mtimes, warning lines, total attempt wall seconds, state-CSV `decision_wall_sec`, raw nonzero `.err` bytes after they force FAIL | Diagnostic only | Never establish PASS |
| Any authored `status`, count, reason, or semantic hash | Comparison target only | Replay-derived values control |

Use `projection-live-replay-v2.2`, exact keys
`schema_version/status/reasons/input_hashes/producer/qualification/sample_dimensions/units/run_artifact_manifests/states/performance/live_gates/semantic_sha256`.
Nested shapes are exact:

- `input_hashes` is
  `state_manifest_file_sha256/state_manifest_semantic_sha256/state_set_semantic_sha256/approving_manifest_sha256/topology_file_sha256/topology_semantic_sha256/run_artifact_set_semantic_sha256`.
- `producer` is exactly `role/path/file_sha256/preflight_file_sha256`, with role
  `live_replay_builder`.
- `qualification` exactly copies the selected immutable manifest.
- `sample_dimensions` is exactly
  `runs/states/nonzero_states/timing_samples/connector_samples/multilane_road_samples`.
- `units` is exactly `sim_sec/wall_time/size/count` with values `s/s/byte/veh`.
- `run_artifact_manifests` records are exactly
  `path/file_sha256/semantic_sha256/run_id/campaign_id/attempt`, sorted uniquely.
- `states` records are exactly
  `state_path/state_file_sha256/run_id/sim_sec/capture_evidence_path/capture_evidence_file_sha256/projection_sidecar_path/projection_sidecar_file_sha256/projection_reference_path/projection_reference_file_sha256/timing_receipt_path/timing_receipt_file_sha256/record_count/assigned_count/stock_total/global_residual/connector_sample_count/multilane_road_sample_count`, sorted by `(run_id,sim_sec,state_path)`.
- `performance` is exactly
  `timing_scope/sample_count/p95_wall_sec/max_wall_sec/decision_budget_sec/state_envelope_max_bytes/projection_sidecar_max_bytes/projection_reference_max_bytes`.
- `live_gates` is exactly `supported_vissim_com_capture/live_performance_p95`, each
  closed to `PASS/FAIL/NOT_EVALUATED` and derived from replay status.

It references raw manifests and recomputes every derived field. Producer binds the
current replay script and shared validators through the preflight role map; it is not
`command_version={}`. Duplicate manifest paths, artifact paths, state paths, or
`(run_id,sim_sec)` identities fail before set comparison. Its semantic hash covers
exactly every listed top-level field except `semantic_sha256`, including derived
status/reasons/gates, by shared canonical JSON v1. Every nested validator rejects
extra/missing keys and wrong cardinality/type.

`run_artifact_set_semantic_sha256` is canonical JSON v1 over the exact
`run_artifact_manifests` record list above, sorted by
`(campaign_id,attempt,run_id,path)`. The payload includes each relative path, exact file
hash, recomputed semantic hash, and the three identities, with no other fields.

Limits: capture sidecar <=256 KiB, timing receipt <=16 KiB, projection reference <=32 KiB,
state envelope <=8 MiB, projection sidecar <=16 MiB, 64 raw samples/state, and >=20
live timing receipts. A valid synthetic chain or inadequate real sample coverage is
`NOT_EVALUATED`; a missing/mixed mode, supplied malformed artifact, unsupported live
version, hash/path/identity mismatch, oversize evidence, partial companion set, or
failed process is FAIL. Closed reasons add `qualification_mismatch`,
`companion_set_incomplete`, `unsupported_vissim_version`, `producer_source_mismatch`,
`run_attempt_mismatch`, `timing_receipt_invalid`, and
`live_sample_coverage_insufficient` to the governing B1a vocabulary.

## Governing trust model

Evidence protects against stale, mixed-run, partially written, manually copied, and
coherently rehashed summary artifacts. A summary JSON must never be its own trust
anchor. The consumer reopens the raw artifacts named below and recomputes every value
used for verdict. The exact non-cryptographic trust boundary is defined above.

## 1. Close malformed-input stale-output paths

- Every parseable approval/manifest/audit invocation with a usable output path must
  atomically replace old output with deterministic FAIL on malformed nested types.
- In particular, numeric/list/string records in `resolved_signal_programs`, preflight
  artifact records, graph/routes/evidence arrays, selection entries, live evidence
  records, and performance records must not leak `AttributeError`, `IndexError`,
  `OverflowError`, or raw `TypeError` past the CLI boundary.
- Add a mutation matrix that seeds `{"status":"STALE_PASS"}` and proves replacement.
  Do not solve this only with a broad catch: validate record types at the owning
  boundary and keep the outer boundary as a final fail-closed guard.

## 2. Immutable pre-run manifest

Add a controller-independent Python producer/validator for `run-manifest-v2.1` and
call it from the watchdog before `cscript` starts.

The manifest is immutable for the whole run and contains exactly one `run_id`, the
exact validated `topology-approval-v2.1` binding returned by
`expected_approved_topology_binding`, a `configuration` object, an exact
`allowed_capture_times` array, and producer/preflight source bindings. The caller may supply no
requested times to the producer, but the manifest field itself is always present as the
exact array specified above, using `[]` for none. It must not contain
actual snapshot time or mutable post-run fields.

The producer must:

- validate the approval with `validate_approval_artifact` and independently validate
  the PASS preflight that pins the current watchdog, VBS, adapter, and producer bytes;
- bind exact network/config/mapping/calibration/tuning/vehicle-role input hashes and
  simulation/control/demand/seed/anchor values;
- write atomically below the run directory, reload it strictly, and publish its exact
  SHA-256;
- reject path escape, noncanonical duplicates, wrong producer bytes, mixed approval,
  or stale output;
- support a validate-only entry point reused by online adapter and offline consumers.

The strict plant-fidelity matrix must require an explicit topology approval and pass it
to the watchdog. Dry-run may report intended paths but must not emit PASS evidence.
Legacy non-B1a invocations may remain optional, but `-Strict -RequireComplete` and the
B1a matrix must fail before VISSIM if approval/run-manifest creation fails.

## 3. VBS run binding and raw capture evidence

The watchdog sets `RW_RUN_ID`, `RW_RUN_MANIFEST_PATH`,
`RW_RUN_MANIFEST_SHA256`, and `RW_B1A_REQUIRED=1` for the child process, restoring all
prior environment values afterward. In required mode the VBS fails before state
publication when any value is absent or malformed.

Every state root writes `run_provenance` with exactly matching `run_id`, canonical
manifest path, and manifest SHA-256. The current root-level `vehicle_records` envelope
and its schema remain unchanged.

For each published state, emit a separate atomic capture-evidence sidecar beside it,
named `<state-stem>.vehicle_capture_v2_1.json`. It must bind the exact run ID/time,
state filename, scalar counts, record count, capture start/end high-resolution timing,
VISSIM version read from the live COM application, and bounded raw key/value samples
from the actually called No/Lane/Pos/Speed tables. Samples include raw Lane strings and
called-parser outputs and must cover a connector and a multi-lane road across the
qualified set. The state must be published before the sidecar is finalized; the
post-run producer binds the exact state and sidecar byte hashes.

Capture failure publishes no state or PASS sidecar and retains the exact reachable
COM/observation failure counters. Sidecar JSON is UTF-8 without BOM and uses the same
strict numeric/escape helpers. Static plus executable fake-COM tests must trace the
actual path and reject dead-decoy evidence writers.

## 4. Post-run artifact trust and live evidence replay

Replace required-mode `run-artifact-manifest-v2.1` with the exact incompatible
`run-artifact-manifest-v2.2` above. The legacy shape may be preserved for legacy runs but
cannot qualify. The replacement is written after every attempted process termination,
including launch failure and watchdog timeout, and binds:

- the immutable pre-run manifest path/hash;
- process start/end/exit code and run window;
- exact state, capture-evidence, physical-projection sidecar, and bounded action
  reference files by relative path and SHA-256;
- VISSIM error evidence and wall-time/timing records;
- the preserved generated VBS config and all existing required artifacts.

Reject duplicate paths, duplicate qualifying `(run_id,sim_sec)`, missing companions,
artifacts outside the run directory, post-run mutation, or incomplete/failed process
evidence. A malformed mtime fails the exact artifact-record schema, but an otherwise
well-formed mtime outside a tolerance is recorded only as a diagnostic and cannot by
itself change the verdict.

Replace the current self-declared `projection-live-evidence-v2.1` PASS logic with a
builder/replayer whose output references the raw run-artifact manifests. The validator
must reopen and validate those manifests and all bound files, then recompute:

- the exact manifest/topology/state universe and unique `(run_id,sim_sec)` identities;
- supported VISSIM version and raw No/Lane/Pos/Speed sample correspondence to the
  state records and A1 graph;
- public projector parse/assignment/count/residual results from state bytes;
- UTF-8/BOM checks and bounded action-reference contents;
- combined per-snapshot capture + serialize + strict parse + public project + atomic
  sidecar write samples, nearest-rank p95, sample count, size limits, and budget.

No authored boolean such as `supported_vissim_version`, `public_projector_parsed`, or
`capture_source` may directly establish PASS. Duplicate live-state rows must fail even
when sample dimensions and semantic hashes are recomputed. Producer identity must bind
the current checked-in builder/replayer bytes through the preflight; arbitrary
`command_version={}` is not producer evidence.

Synthetic fixtures may prove parser/replay behavior but must carry an explicit
synthetic qualification marker and can yield at most `NOT_EVALUATED`, never live PASS.
Only raw artifacts from a successful required-mode run with supported COM version and
real timing can make the two live gates PASS.

## 5. Online/offline readiness interfaces

Expose shared pure validators rather than duplicating schema/hash/path logic in
PowerShell, VBS tests, adapter, and audit scripts. The next adapter slice must be able
to call the run-manifest validator before importing NumSim or evaluating a controller.

Keep reason codes closed and machine-readable. Missing live artifacts are
`NOT_EVALUATED` only when no campaign/evidence set was supplied for evaluation. Once a
required attempt or manifest is supplied, a missing role required by its status,
missing companion, or malformed/mismatched artifact is FAIL. Valid synthetic mode or
valid but inadequate live coverage remains `NOT_EVALUATED`. A fallback action cannot
mask failed run or projection trust.

## Required tests

- Exact `run-manifest-v2.1` happy path and mutations for approval, producer/preflight,
  configuration, capture times, path, hash, duplicate, and mutable-time injection.
- Watchdog tests prove manifest creation precedes `Start-Process`, required env values
  are set/restored, and failure prevents VISSIM launch.
- VBS tests prove exact root provenance, raw-sample capture from the called tables,
  atomic companion publication, version read, and failure-before-state behavior.
- Offline replay rejects self-declared summary-only evidence, duplicate state rows,
  stale/missing/mixed companions, post-run byte mutation, wrong run window, unsupported
  version, fake/synthetic qualification, incorrect timing scope/p95, and all malformed
  nested-type stale-output mutations.
- Role-table mutations cover every role's phase/min/max, all singleton over/under-counts,
  unequal action pairs, unequal state companions, partial failed attempts, omitted
  extant partial files, demand-profile null/present cases, and every duplicate binding.
- Byte mutations cover BOMs, non-UTF-8 logs, bare LF/CR, missing final terminators,
  quoted/extra CSV fields, row reorder/duplicate/omission, hidden or malformed `ERROR=`,
  duplicate completion/counter lines, readback counter mismatch, and missing/unpaired
  signal persistence rows. Stderr fixtures assert exact bytes for zero bytes (the sole
  PASS case), CRLF-only, whitespace-only, and one diagnostic line. Decision-line tests
  cover empty and maximum base64url fields, 4097 decoded bytes, invalid padding/length,
  delimiter-looking decoded text, and the 8192-byte record bound. The decoded-adapter
  stdout fixtures are byte/token exact: ASCII `ERROR=ADAPTER_FAILURE` /
  `RVJST1I9QURBUFRFUl9GQUlMVVJF` fails; ASCII
  `prefixERROR=ADAPTER_FAILUREsuffix` /
  `cHJlZml4RVJST1I9QURBUFRFUl9GQUlMVVJFc3VmZml4` fails; UTF-8 byte strings
  `ok\r\nERROR=ADAPTER_FAILURE\r\nok`, `ok\rERROR=ADAPTER_FAILURE\rok`, and
  `ok\nERROR=ADAPTER_FAILURE\nok` with respective tokens
  `b2sNCkVSUk9SPUFEQVBURVJfRkFJTFVSRQ0Kb2s`,
  `b2sNRVJST1I9QURBUFRFUl9GQUlMVVJFDW9r`, and
  `b2sKRVJST1I9QURBUFRFUl9GQUlMVVJFCm9r` each fail after CRLF/bare-CR/bare-LF
  splitting. Token `wyg` decodes to bytes `c3 28` and fails strict UTF-8; `QQ==`
  fails for padding, `A` for length 1 modulo 4, `QQ$` for alphabet, and `AB` because
  decode/re-encode yields `AA`, not the original token. Benign ASCII
  `stdout=RVJST1I9Tk9UX0FUX1RPUF9MRVZFTA stderr=` /
  `c3Rkb3V0PVJWSlNUMUk5VGs5VVgwRlVYMVJQVUY5TVJWWkZUQSBzdGRlcnI9` contains
  delimiter-looking text but no literal decoded `ERROR=` and therefore does not fail
  this predicate. Every fixture still obeys all independent framing and gating rules;
  adapter stderr is the empty source and empty token in every PASS candidate.
- State/action binding tests cover coincident and noncoincident schedules in stepwise,
  continuous-static, event-continuous single-decision, and event-continuous repeated-
  control modes; an equal-time action published after `LogStateCsv` must never bind that
  row.
- Required-mode replay rejects legacy error/wall/log evidence, nonzero `.err` bytes,
  stale error inventory, wall-clock-derived elapsed values, invalid Stopwatch endpoints,
  and any authored PASS/status/count rewrap after these mutations. Tests run the decision
  formatter under a comma-decimal locale and prove byte-identical ASCII output. Tick
  tuples whose rational duration lies between adjacent binary64 values remain governed
  only by exact integers; adding either adjacent float as `elapsed_wall_sec` is an
  extra-key FAIL.
- Online/offline use the same run/topology/projector validators.
- Run focused B1a, VBS, runner, A1/A2, compiler, adapter, and auditor regressions.

## Completion report

Write `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-report.md` with
changed files, schemas, commands/results, finding dispositions C2/I3/I4, exact
NOT_EVALUATED live gates, and self-review. Do not claim live COM or live p95 PASS.
This planning-only round also writes
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief-fix4-report.md`
with the amended sections, I3/I13 disposition, grounded source locations, and brief
self-review; it reports no implementation or live-run completion.
