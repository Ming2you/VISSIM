# V2.1 Reproducibility and Signal-Plan Amendment Proposal

Review target: branch `codex/plant-fidelity-v2-1`, baseline
`cb3c44d170b7f818baae7af399fb65c93b6fb1e3`.

Review mode: read-only. This report is the only created file. The proposal below is
executable after its named scripts and flags are implemented. It does not treat any
historical report as current promotion evidence.

## Decision

Do not execute v2 as written. Adopt all ten v2.1 amendments below first. The highest
priority correction is that the current signal reference grouped downstream connectors
by link rather than by exact lane. That error made the SC12 report's shared-lane
conclusion false and invalidates `reports/signal_reference_20260805.json` as a canonical
input.

## 1. Reopen S0 and Pin the Amendment Baseline

### Current contradiction and evidence

- `IMPLEMENTATION_PLAN.md:54` labels all of S0 complete, but S0-3 is simultaneously
  marked "completed (decision unresolved)" at `IMPLEMENTATION_PLAN.md:81` and has
  remaining work at `IMPLEMENTATION_PLAN.md:93`. An unresolved physical source change
  is not a completed baseline gate.
- The current audit summary is historical: it records commit `dc216be`, a different
  branch, and `dirty=True` at `reports/plant_fidelity_audit_summary.md:60`. Its network
  SHA-256 is `2f75...ceda0` at `reports/plant_fidelity_audit_summary.md:70`; the baseline
  worktree network bytes reviewed here hash to
  `f3ce390f281c2bd60a367435dd5567767edafb4681cb66a2c566a480aa74d635`.
- The audit report also names the old NumSim snapshot `35a5c82` at
  `reports/plant_fidelity_audit.md:4-6`, while the current vendored snapshot declares
  `0240ba8` at `vendor/NumSim-mine/SNAPSHOT.md:7-10`.

### Exact replacement text

Replace `IMPLEMENTATION_PLAN.md:54-56` with:

```markdown
## S0R. v2.1 reproducibility baseline - NOT COMPLETE

The amendment baseline is `cb3c44d170b7f818baae7af399fb65c93b6fb1e3` on
`codex/plant-fidelity-v2-1`. Historical audit outputs from `dc216be` are context only,
not promotion evidence. S0R is complete only after source identity, EOL policy,
canonical signal-reference regeneration, and SC12 lane-level resolution all pass.

Every v2.1 artifact MUST contain both `baseline_commit=cb3c44d...` and the clean
`implementation_commit` that generated it. The baseline must be an ancestor of the
implementation commit. A dirty or detached execution is fail-closed.
```

Replace the S0-3 status text at `IMPLEMENTATION_PLAN.md:81` with:

```markdown
### S0R-4. SC12 network change resolution - REOPENED
```

### Prerequisites

None. This is the first gate.

### Command and artifact

```powershell
python -B scripts/build_reproducibility_lock.py `
  --repo . `
  --baseline cb3c44d170b7f818baae7af399fb65c93b6fb1e3 `
  --output reports/reproducibility_lock_v2_1.json
```

Artifact: `reports/reproducibility_lock_v2_1.json`.

### Numeric pass/fail rule

PASS only when all are true: baseline ancestor check `1/1`; worktree dirty paths `0`;
missing locked inputs `0`; SHA-256 values with invalid length `0`; branch mismatch `0`.
Any nonzero count is FAIL, not `NOT_EVALUATED`.

## 2. Make Source, Import, Hash, and EOL Identity One Contract

### Current contradiction and evidence

- The request and snapshot still say runtime imports an external NumSim checkout
  (`PLANT_FIDELITY_AUDIT_REQUEST.md:42-46`, `vendor/NumSim-mine/SNAPSHOT.md:20-27`).
  The adapter now defaults to the bundled vendor tree at
  `evaluation/controllers/vissim_stackelberg_adapter.py:27-31`.
- The adapter correctly rejects imported `src.*` modules outside the selected root at
  `evaluation/controllers/vissim_stackelberg_adapter.py:1350-1369`, but the plan never
  chooses a mandatory promotion root.
- Source hashes use raw working-tree bytes at
  `evaluation/controllers/vissim_stackelberg_adapter.py:563-573` and
  `scripts/audit_plant_fidelity.py:944-957`. There is no `.gitattributes`. On this clean
  checkout, `git ls-files --eol` reports `i/lf w/crlf` for the adapter, both runners,
  the plan, and the signal reference because `core.autocrlf=true`. Thus clean clones can
  execute different bytes and produce different SHA-256 values.
- The plan's ASCII requirement for PowerShell at `IMPLEMENTATION_PLAN.md:25-27` solves
  code-page ambiguity, not line-ending identity.

### Exact addition text

Add this subsection immediately after the absolute constraints:

```markdown
### 0.2A Source/import/hash/EOL contract

For every promotion run, the only allowed NumSim import root is
`<repo>/vendor/NumSim-mine`. `NUMSIM_REPO_ROOT` and adapter `--repo-root` MUST resolve to
that exact directory. External NumSim roots are development-only and their output is
ineligible for promotion.

The lock records: baseline commit, implementation commit, dirty status, effective
NumSim root, snapshot commit, NumSim Python-tree SHA-256, every imported `src.*` module
path/SHA-256, Python executable/version/SHA-256, VISSIM version, network profile, INPX
SHA-256, the 41 supplyFile2-selected SIG SHA-256 values, mapping SHA-256, compiler
version, and EOL policy version.

Hash executed bytes, not path names or timestamps. Pin checkout EOLs with
`.gitattributes`; record both Git blob identity and executed-byte SHA-256. Never compare
raw-byte hashes from checkouts with different declared EOL policies.
```

Add `.gitattributes` with this exact content during implementation:

```gitattributes
*.py   text eol=lf
*.json text eol=lf
*.md   text eol=lf
*.csv  text eol=lf
*.sig  text eol=lf
*.inpx text eol=lf
*.yaml text eol=lf
*.yml  text eol=lf
*.ps1  text eol=crlf
*.vbs  text eol=crlf
```

Update `PLANT_FIDELITY_AUDIT_REQUEST.md` and `vendor/NumSim-mine/SNAPSHOT.md` to say
that promotion executes the vendor snapshot; the upstream repository remains the edit
source and must be committed, copied, and snapshot-locked before use.

### Prerequisites

S0R baseline pin only.

### Command and artifact

```powershell
git add --renormalize --dry-run .
git ls-files --eol > reports/eol_inventory_v2_1.txt
python -B scripts/check_reproducibility_lock.py `
  --lock reports/reproducibility_lock_v2_1.json `
  --require-numsim-root vendor/NumSim-mine `
  --require-clean
```

Artifacts: `reports/eol_inventory_v2_1.txt` and the updated reproducibility lock.

### Numeric pass/fail rule

PASS only with: external imported modules `0`; imported-module hash mismatches `0`;
NumSim tree mismatch `0`; undeclared EOL files among hashed/executed inputs `0`; dirty
paths at launch `0`; effective NumSim roots across all cases `1`; execution fingerprints
across all matrix cases `1`. Otherwise FAIL.

## 3. Make the Runner Strict in Fact, Not Only in Name

### Current contradiction and evidence

- The matrix invokes the auditor without `--strict` at
  `scripts/run_plant_fidelity_matrix.ps1:71-77`.
- The auditor returns nonzero only when `--strict` is supplied and at least one gate is
  FAIL (`scripts/audit_plant_fidelity.py:2048`,
  `scripts/audit_plant_fidelity.py:2070-2080`). It still returns zero when gates are
  `NOT_EVALUATED`.
- The matrix therefore can print DONE even when the overall result is FAIL or
  `NOT_EVALUATED`. Its current body also runs only fixed/no-control baselines
  (`scripts/run_plant_fidelity_matrix.ps1:1-6`,
  `scripts/run_plant_fidelity_matrix.ps1:43-56`), consistent with the plan's admission
  at `IMPLEMENTATION_PLAN.md:428-433`.
- The watchdog uses `$ErrorActionPreference="Continue"` at
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:39`, permits three
  attempts by default at line 34, and accepts an exited child based on a log marker at
  lines 309-320 without checking the child exit code and complete artifact contract.
- The VBS itself has useful fail-closed checks for decision, observation, signal, action
  format, and early termination at
  `scripts/run_real_world_stackelberg_controller.vbs:271-300`; the wrapper must preserve,
  not weaken, those semantics.

### Exact replacement/addition text

Replace J-1 with:

```markdown
### J-1. Strict runner and paired-future harness - build before plant changes

Add `-Strict` and `-RequireComplete` runner modes. In those modes:

1. set `$ErrorActionPreference = "Stop"`;
2. use one unique run ID per case and one unique attempt ID per attempt;
3. default `MaxAttempts=1`; retries require an explicit infrastructure-failure code and
   every attempt remains in the final manifest;
4. acquire a machine-wide VISSIM mutex before launch;
5. require child exit code 0, exactly one `STAGE=SIM_DONE`, target SimSec reached, all
   required artifacts present and nonempty, VISSIM error count 0, and VBS integrity
   counters 0;
6. invoke the auditor with `--strict --require-complete` and write audit output inside
   the run directory;
7. treat either FAIL or NOT_EVALUATED as runner exit 2;
8. never reuse a prior state/action/log file as success evidence.

The same harness then adds anchor forks and low/base/high actions. Baseline-only mode is
not dynamic validation and cannot satisfy J or K.
```

Add auditor flag text:

```markdown
`--strict` fails on any FAIL. `--require-complete` additionally fails on any
NOT_EVALUATED, missing expected case, duplicate case, mixed fingerprint, or unpaired
state/action/future artifact.
```

### Prerequisites

S0R source lock and EOL contract. It does not depend on C through I.

### Command and artifact

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  scripts/run_plant_fidelity_matrix.ps1 `
  -OutDir evaluation/runs/plant_fidelity_v2_1_native `
  -Strict -RequireComplete -MaxAttempts 1
```

Artifacts: one `case_manifest.json` per case and
`evaluation/runs/plant_fidelity_v2_1_native/matrix_manifest.json`.

### Numeric pass/fail rule

For the baseline matrix: expected cases `9`, completed cases `9`, duplicate cases `0`,
concurrent VISSIM instances maximum `1`, successful attempts per case `1`, child
nonzero exits `0`, `STAGE=SIM_DONE` count per case `1`, early endings `0`, integrity
failures `0`, required-artifact misses `0`, audit FAIL `0`, audit NOT_EVALUATED `0`.
Any violation is FAIL.

## 4. Bind Provenance to the Run, Network Profile, and Selected Programs

### Current contradiction and evidence

- The watchdog manifest hashes inputs and all SIG files at
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:178-235`, but it
  does not record dirty state, EOL policy, Python/VISSIM build identity, network profile,
  the exact supplyFile2 SC-to-SIG map, or the generated signal-reference hash.
- Adapter provenance checks imported module paths and hashes
  (`evaluation/controllers/vissim_stackelberg_adapter.py:610-660`), but SIG identity is
  an unscoped directory glob at lines 625-628 rather than the 41 mapped model programs.
- The audit records dirty state at `scripts/audit_plant_fidelity.py:105-140`, but
  `input_provenance` only checks that files exist at
  `scripts/audit_plant_fidelity.py:1677-1684`; dirty execution is not a gate.
- When `NUMSIM_REPO_ROOT` and `--numsim-root` are unset, the auditor marks actual NumSim
  unavailable (`scripts/audit_plant_fidelity.py:1828-1837`) even though the adapter
  defaults to the vendor tree. The matrix neither passes the root nor rejects this
  `NOT_EVALUATED` state.

### Exact addition text

Add to S0R:

```markdown
### S0R-3. Run provenance schema v3

One preflight process resolves every effective path. The resolved lock is passed to the
watchdog, VBS, adapter, signal compiler, paired-future harness, and auditor. Consumers
MUST NOT independently rediscover defaults.

Required identity fields are: `baseline_commit`, `implementation_commit`, `dirty=false`,
`network_profile` (`native` or `normalized-150s`), `network_id`, INPX SHA-256,
`signal_reference_sha256`, ordered `sc_to_sig` with 41 SIG SHA-256 values,
`numsim_root`, snapshot commit/tree hash, imported module evidence, mapping/config
hashes, runner/VBS/adapter/compiler hashes, Python executable/version/hash, VISSIM
version/build, EOL policy version, seed, demand identity, run ID, attempt ID, and parent
anchor ID for forked futures.

The execution fingerprint excludes only per-case state/action bytes, timestamps, run ID,
attempt ID, seed, and demand. A run ID may have exactly one execution fingerprint.
```

### Prerequisites

Issues 1 and 2, plus the canonical signal reference from issue 6.

### Command and artifact

```powershell
python -B scripts/build_run_manifest.py `
  --lock reports/reproducibility_lock_v2_1.json `
  --network-profile native `
  --signal-reference outputs/signal_reference_v2_1.json `
  --out evaluation/runs/plant_fidelity_v2_1_native/preflight_manifest.json
```

Artifact: `preflight_manifest.json`, copied by hash into every case manifest.

### Numeric pass/fail rule

Required fields missing `0`; unavailable files `0`; dirty flag values other than false
`0`; selected SC-to-SIG entries `41`; selected SIG hashes `41`; model SC without SIG `0`;
unapproved extra SC `0`; fingerprints per run ID `1`; manifest hash mismatches across
VBS/adapter/auditor `0`. Any deviation is FAIL.

## 5. Correct SC12 Using Exact Lane Connectivity

### Current contradiction and evidence

- The SC12 report says both changed lanes reach straight, left, and right connectors and
  therefore cannot be resolved geometrically
  (`reports/network_change_sc12_heads_20260805.md:26-56`).
- The reference lists all three link-level connectors under head 50201 at
  `reports/signal_reference_20260805.json:1527-1549` and does the same for 50601 at
  `reports/signal_reference_20260805.json:1683-1705`.
- INPX proves the grouping is wrong. Head 50201 is on lane `1220012103 2` and SG12/5
  (`network/real_world_gaepo_modi/modi_eval_rw_control.inpx:29061`). Connector 10242
  starts from that exact lane at line 13707. Connectors 10241 and 10243 start from lane 1
  at lines 13685 and 13729. Thus lane 2 has only the left-turn connector 10242.
- Head 50601 is on lane `1220013600 2` and SG12/1
  (`network/real_world_gaepo_modi/modi_eval_rw_control.inpx:29067`). Connector 10240
  starts from lane 2 at line 13663. Straight/right connectors 10238/10239 start from
  lane 1 at lines 13620 and 13642. Thus lane 2 has only left-turn connector 10240.
- Static route totals are approach-level, not evidence that each lane serves all turns:
  EB L/T/R are 120/94/30 at
  `network/real_world_gaepo_modi/modi_eval_rw_control.inpx:30401-30433`; WB L/T/R are
  38/147/131 at lines 30438-30453.
- The changed pairs are timing-equivalent in active program 1: SG2 equals SG5 and SG1
  equals SG6 (`network/real_world_gaepo_modi/개포동 test-bed5.sig:91-143`). The same
  equality holds in programs 2 and 3. The reassignment changes semantic/movement
  ownership, not current fixed-time windows.

### Exact replacement text

Replace S0-3's physical assessment and remaining-work paragraphs with:

```markdown
**Lane-level resolution:** head 50201 (`1220012103/2`) controls only connector 10242,
the EB left-turn route; head 50601 (`1220013600/2`) controls only connector 10240, the WB
left-turn route. The prior shared-lane conclusion came from grouping connectors by link
instead of exact source lane. Therefore the current EBL/WBL assignments are physically
consistent and S0R-4 may close after regenerated-reference validation.

Approach-level `relFlow` is retained as demand evidence only; it does not override exact
lane-to-connector connectivity. Programs 1/2/3 currently give old and new SG pairs
identical windows, so the network edit has zero native fixed-time event delta but a real
movement-authority delta. Record both facts.
```

Replace `reports/network_change_sc12_heads_20260805.md:26-63` with the same conclusion
during implementation and link it to the regenerated reference hash.

### Prerequisites

Exact-lane signal-reference generator from issue 6.

### Command and artifact

```powershell
python -B scripts/validate_signal_reference.py `
  --reference outputs/signal_reference_v2_1.json `
  --check-sc 12 `
  --output reports/sc12_head_resolution_v2_1.json
```

Artifact: `reports/sc12_head_resolution_v2_1.json`.

### Numeric pass/fail rule

PASS requires: head 50201 exact-lane downstream connector set exactly `{10242}`; head
50601 set exactly `{10240}`; wrong-lane connector count `0`; resolved turn class LEFT
for both heads; current SGs `5` and `1`; native timeline differences between SG2/SG5 and
SG1/SG6 across programs 1/2/3 exactly `0`; unresolved SC12 heads `0`.

## 6. Generate the Signal Reference from the Strict Compiler Path

### Current contradiction and evidence

- `reports/signal_reference_20260805.json` has no generator in the repository. Its source
  object contains only a path, with no input hash, compiler version, command, selected
  program, or EOL policy (`reports/signal_reference_20260805.json:1-5`). It cannot be a
  canonical input as claimed at `IMPLEMENTATION_PLAN.md:43` and
  `IMPLEMENTATION_PLAN.md:217-218`.
- The plan proposes a second parser, `scripts/derive_signal_phase_spec.py`, at
  `IMPLEMENTATION_PLAN.md:189-192`, while a tested strict parser already exists at
  `plant/src/vissim_strict/signal_program.py:159-228` and the compiler already follows
  supplyFile2 at `plant/src/vissim_strict/compiler.py:53-95`.
- The compiler currently loops all controllers and errors on missing supply files
  (`plant/src/vissim_strict/compiler.py:61-70`). The live network has 50 active records,
  including eight artificial ramp meters with no SIG and SC9004, an empty duplicate.
  Role-aware scope must be added before using this compiler on the live network.
- Strict topology already has exact lane mappings at
  `plant/src/vissim_strict/topology.py:226-235`, but `_build_signal_gates` keeps only the
  nearest exact-lane connector at lines 652-675. The reference must report all exact-lane
  downstream route choices and separately identify the nearest physical gate.

### Exact replacement text

Replace C-1's opening and input/output rules with:

```markdown
### C-1. Canonical signal-reference compiler

Do not create a second SIG parser. Extend `plant/src/vissim_strict/compiler.py` and
`signal_program.py`, then expose one thin CLI. Inputs are the explicit native INPX,
signal-role CSV, control mapping, and supplyFile2-selected SIG files.

The compiler MUST:

- select the 41 modeled urban SCs by role; explicitly exclude artificial SC9101-9108
  and empty duplicate SC9004 with reason codes;
- resolve SIG only through each controller's `supplyFile2`;
- preserve `(SC, SG number)` identity and never require the internal SIG controller ID
  to equal the INPX SC number;
- join each head to connectors by exact `(from link, from lane)` and downstream position;
- emit all exact-lane downstream connector choices, route names/relFlow, nearest gate,
  and unresolved reason;
- include raw millisecond values and source XPath/attribute provenance;
- include compiler/input/EOL hashes and canonical-json output hash;
- emit one canonical artifact consumed by C, E, F, the runner, and the auditor.

`reports/signal_reference_20260805.json` becomes historical and MUST NOT be consumed by
v2.1 code.
```

Required artifact fields are at least:

```json
{
  "schema_version": "vissim-signal-reference/v2.1",
  "network_profile": "native",
  "source": {
    "inpx_sha256": "...",
    "compiler_version": "...",
    "compiler_sha256": "...",
    "eol_policy_version": "v2.1",
    "sc_to_sig": {"12": {"path": "...test-bed5.sig", "sha256": "..."}}
  },
  "controllers": {},
  "signal_groups": {},
  "signal_heads": [],
  "validation": {}
}
```

### Prerequisites

Issues 1 and 2. No A/B/C model changes are prerequisites.

### Command and artifact

```powershell
$env:PYTHONPATH = (Resolve-Path plant).Path
python -B -m src.vissim_strict.compiler `
  network/real_world_gaepo_modi/modi_eval_rw_control.inpx `
  --signal-roles evaluation/real_world_modi_inventory/signal_controller_roles.csv `
  --control-mapping evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json `
  --output outputs/signal_reference_v2_1.json
python -B scripts/validate_signal_reference.py `
  --reference outputs/signal_reference_v2_1.json `
  --output reports/signal_reference_v2_1_validation.json
```

### Numeric pass/fail rule

PASS requires: modeled controllers `41`; selected unique SIG files `41`; declared SGs
`424`; signal heads `541`; supplyFile2 resolutions missing `0`; INPX/SIG SG-name
mismatches `0`; wrong-lane connector joins `0`; dangling references `0`; duplicate
canonical IDs `0`; unclassified heads `0` (approved terminal/no-outgoing heads carry an
explicit reason); validation errors `0`; canonical artifact hashes identical across
three generations `3/3`.

## 7. Fix Active Program and Timeline Semantics Before Deriving Stages

### Current contradiction and evidence

- S1 treats active program selection as unresolved and discusses daily program lists at
  `IMPLEMENTATION_PLAN.md:102-110`; the proposed schema then hardcodes
  `"active_program":"0"` at `IMPLEMENTATION_PLAN.md:199-203`.
- INPX uses `progNo="1"`; for example SC1 is explicit at
  `network/real_world_gaepo_modi/modi_eval_rw_control.inpx:27681`. An exhaustive XML
  read at this baseline found all 50 controller records at program 1 and offset 0, with
  simulation `startTm=0` at
  `network/real_world_gaepo_modi/modi_eval_rw_control.inpx:29555`.
- Every one of the 41 SIG files has programs 1/2/3; SC12's selected SIG demonstrates
  them at `network/real_world_gaepo_modi/개포동 test-bed5.sig:89`, line 165, and line 241.
  Its `stages`, `stageProgs`, and `dailyProgLists` are empty at lines 318-321. Exhaustive
  XML inspection found those structures empty in all 41 files.
- Existing strict code already reads INPX `progNo` and controller offset at
  `plant/src/vissim_strict/topology.py:340-353` and selects that exact SIG program at
  `plant/src/vissim_strict/compiler.py:61-69`.
- The strict parser converts integer milliseconds directly to float seconds and drops
  the raw integer at `plant/src/vissim_strict/signal_program.py:660-664`, contrary to
  the raw-ms provenance contract in `plant/docs/vissim_strict_plant_g0_contract.md:164`.
- All 41 `intergreenmatrices` are empty (example
  `network/real_world_gaepo_modi/개포동 test-bed1.sig:87`). A nonempty `clearance` map like
  the example at `IMPLEMENTATION_PLAN.md:209-212` would be fabricated unless explicitly
  marked derived.
- Source stages are absent. Derived stages therefore cannot become the command authority;
  the strict contract makes SG timelines primary at
  `plant/docs/vissim_strict_plant_g0_contract.md:129-170`.

### Exact replacement text

Replace S1-1 and S1-2 with:

```markdown
### S1-1. Active program lock and runtime readback

The native baseline selects INPX `progNo=1` for every controller; `startTm=0`, INPX
controller offset is 0, and all daily program lists are empty. Compile program 1 through
supplyFile2 for each of the 41 modeled SCs. Do not use program 0 and do not infer a
time-of-day switch.

At runtime, read back `ProgNo` at t=0 and every audit anchor. Program switching is
disabled in v2.1. Any readback other than 1 or any within-run change is fatal.

### S1-2. Canonical SG timeline

Preserve raw integer `cycletime`, `switchpoint`, program `offset`, command `begin`, and
fixedstate `duration` with source XPath plus exact seconds. Expand GREEN/AMBER/RED into
half-open periodic intervals with zero gaps/overlaps. Keep program offset, controller
offset, cycle epoch, start time, and runtime action lag as separate terms. `switchpoint`
is program-switch metadata, not phase offset.

All native intergreen matrices and source stage collections are empty. Record that fact.
Do not synthesize source clearance or source stages. Derived stage clusters may be
reported for diagnostics and sensitivity only; VBS/COM commands and movement service
must remain keyed by `(SC, SG)` timeline/gate identity.
```

Replace E-2's stage-index authority with:

```markdown
### E-2. SG timeline action transform

Replace major/minor naming rules with a validated `(SC, SG)` action transform over the
canonical SG timelines. A derived stage index is diagnostic metadata only. Every action
must preserve fixed SGs, amber/all-red sequence, min-green, conflicts, native cycle, and
atomic SC-level activation.
```

### Prerequisites

Canonical signal reference and SC12 resolution.

### Command and artifact

```powershell
python -B scripts/validate_signal_timeline.py `
  --reference outputs/signal_reference_v2_1.json `
  --program-source inpx-progNo `
  --output reports/signal_timeline_native_v2_1.json
```

### Numeric pass/fail rule

PASS requires: INPX controllers with `progNo=1` `50/50`; modeled SC runtime readback
program 1 at all anchors `41/41`; runtime program changes `0`; compiled active programs
`41`; timeline SGs `424`; raw-ms fields missing `0`; interval gap/overlap errors `0`;
unsupported display states `0`; fabricated intergreen entries `0`; authoritative
stage-index commands `0`; timeline hash repeatability `3/3`.

The measured native active-program cycle distribution is exactly
`{100:1, 120:2, 140:1, 150:23, 160:11, 170:3}`. A different distribution is FAIL.
The observed 4,744 SIG time attributes are all integer-second aligned; event timing is
still judged from exact raw ms and must meet the oracle threshold, not rounded masks.

## 8. Separate Native and Normalized Cycles by Identity and Promotion Scope

### Current contradiction and evidence

- X correctly says native and normalized networks are different experiments at
  `IMPLEMENTATION_PLAN.md:464-496`, but X-1 is ordered after C in the dependency graph
  (`IMPLEMENTATION_PLAN.md:503-507`) even though C-2 needs per-SC cycles.
- The vendored model has one scalar `cycle_length` at
  `vendor/NumSim-mine/src/models/state.py:220-225`, and the urban model consumes that
  scalar at `vendor/NumSim-mine/src/models/urban_queue_model.py:561`. The repository has
  many additional scalar consumers; changing only `_phase_green_fraction` is incomplete.
- The strict bridge already accepts per-controller cycle values at
  `plant/src/vissim_strict/bridge.py:110-145`, so the v2.1 model contract should use that
  identity rather than normalize the native plant.
- No 150-second normalized INPX currently exists in the network directory. Existing
  alternate INPX files are not a normalized-cycle promotion artifact.

### Exact replacement text

Replace X with:

```markdown
## X. Native cycle support and separate normalized experiment

### X-1. Native per-SC cycles - promotion prerequisite

Before C-2, add a single `cycle_sec(signal_id)` lookup backed by the canonical signal
reference. Audit every scalar `cycle_length` consumer and classify it as signal-specific,
network-global, or intentionally legacy. Signal-specific code MUST use the per-SC value.
The scalar remains only an explicit legacy fallback and fallback use is counted.

Native fidelity and all K promotion evidence use the unmodified
`modi_eval_rw_control.inpx` and active program-1 distribution
`100x1,120x2,140x1,150x23,160x11,170x3`.

### X-2. Normalized-150s experiment - never native promotion evidence

A normalized network has a distinct filename, `network_profile`, `network_id`, INPX
hash, SIG-reference hash, run directory, audit report, and network-change report. No
state, anchor, action, oracle, calibration, or gate result may be shared across native
and normalized profiles. Normalized results cannot satisfy native K or release gates.
```

### Prerequisites

X-1 requires S1. X-2 requires S1 plus an approved standalone network-change design, but
is not on the native promotion critical path.

### Command and artifact

```powershell
python -B scripts/audit_cycle_consumers.py `
  --numsim-root vendor/NumSim-mine `
  --signal-reference outputs/signal_reference_v2_1.json `
  --output reports/native_cycle_consumers_v2_1.json
```

Future normalized generation must emit
`reports/network_change_normalized_150s_<stamp>.md` and a distinct INPX/SIG bundle.

### Numeric pass/fail rule

Native PASS requires cycle distribution exact match; modeled SC cycle mappings `41/41`;
unclassified scalar cycle consumers `0`; signal-specific scalar fallback uses `0` in
promotion runs; network profiles per run `1`; native/normalized hash sharing `0`.
Normalized output is `NOT_EVALUATED` for native promotion by definition, never PASS.

## 9. Promote Offset Only Through G3, G6, and Green-Only Release

### Current contradiction and evidence

- The plan permits offset experiments after F alone at `IMPLEMENTATION_PLAN.md:338-345`
  and confines them to the normalized network at `IMPLEMENTATION_PLAN.md:495-496`.
- The approved strict contract requires positive-lag semantics and keeps offset actuation
  disabled until controller-specific COM round-trip at
  `plant/docs/vissim_strict_plant_g0_contract.md:196-206`. It additionally requires G3,
  G6, and green-only release before offset actuation at lines 825-833.
- The current strict bridge labels offset as `intent_only` at
  `plant/src/vissim_strict/bridge.py:171-183`, and its test confirms that state at
  `plant/tests/test_vissim_strict_bridge.py:192-212`. There is no promotable offset writer
  today.
- Native source phase must keep SIG program offset, controller offset, cycle epoch, and
  runtime lag separate (`plant/docs/vissim_strict_plant_g0_contract.md:172-206`).

### Exact replacement text

Replace F's final sentence and X's offset sentence with:

```markdown
**Offset remains disabled after F.** F validates source phase and readback only. Runtime
offset actuation may be promoted for a named network profile only after all of these are
PASS on that same profile and identical hashes: G3 controller-by-controller COM
write/read round-trip and sign test; G6 paired VISSIM ranking including forced offset;
green-only release; full-SC atomic replay; stale-action/fallback tests.

Canonical positive offset is lag:
`phase = mod(source_phase - action_offset_lag_delta_sec, cycle)`.
`switchpoint` is never included. Activation occurs at the next validated canonical cycle
boundary without phase truncation.

Native and normalized offset promotion are separate. A normalized offset PASS cannot
enable offset on the native plant. Until a profile-specific promotion artifact passes,
the writer MUST reject nonzero runtime offset and the bridge remains `intent_only`.
```

### Prerequisites

S1 timeline, X-1 per-SC cycles, E SG action transform, F oracle, J paired futures, G6
pass, and green-only release on the same network profile.

### Command and artifact

```powershell
python -B scripts/evaluate_offset_promotion.py `
  --network-profile native `
  --run-dir evaluation/runs/plant_fidelity_v2_1_native `
  --signal-reference outputs/signal_reference_v2_1.json `
  --output reports/offset_promotion_native_v2_1.json
```

### Numeric pass/fail rule

Before promotion, attempted nonzero offset writes `0`. Promotion PASS requires all 41
modeled SCs covered by source/readback identity; sign mismatches `0`; activation-boundary
errors `0`; phase cuts `0`; conflicting greens `0`; min-green/amber/all-red violations
`0`; immediate and post-step readback agreement `100%`; event timing absolute error
`<=0.5 s`; G6 Spearman `>=0.70`; top-action pairwise `>=0.80`; repeated material-effect
sign reversals `0`; stale/fallback fault-injection failures `0`; green-only regression
failures `0`. Every criterion must be evaluated. Any FAIL or NOT_EVALUATED blocks offset.

## 10. Replace the Dependency Graph and Gate Ownership

### Current contradiction and evidence

- The plan says S1 must finish before A at `IMPLEMENTATION_PLAN.md:98-110`, although A/B
  need topology and physical route identity, not active timing.
- S0-3 consumes the ad hoc signal reference at `IMPLEMENTATION_PLAN.md:93-94`, while the
  generator is postponed to C-1 at lines 189-218. That is an evidence dependency
  inversion.
- J is titled "harness first" at `IMPLEMENTATION_PLAN.md:426`, but Appendix A postpones
  J-1 until C through I are complete at `IMPLEMENTATION_PLAN.md:511`.
- X-1 supplies per-SC cycles needed by C-2, yet Appendix A places X-1 downstream of C at
  `IMPLEMENTATION_PLAN.md:503-507`.
- F alone is not an offset promotion gate, as shown in issue 9.

### Exact replacement text

Replace Appendix A with:

```markdown
## Appendix A. v2.1 dependency and promotion order

S0R-1 baseline/clean/EOL lock
  -> S0R-2 canonical source/import lock
  -> S0R-3 provenance schema
  -> R1 canonical signal-reference compiler

After R1, run in parallel:
  - S0R-4 SC12 resolution
  - S1 active program + exact SG timeline
  - A link ownership tie resolution
  - B route adjacency resolution
  - J-1 strict runner + paired-future harness dry-run/contract tests

S1 -> X-1 native per-SC cycle support

S0R-4 + S1 + X-1 + A + B
  -> C SG/movement artifact and N-phase model
  -> E SG action contract
  -> F signal oracle (source/readback only; offset still disabled)

A + B -> G exit/boundary stock and H storage/holdout
S0R source lock -> D speed/delay work and I price parity may proceed in parallel

C + D + E + F + G + H + I + J-1
  -> J-2/3/4 native paired executions
  -> K strict complete audit and green-only release

F + J(G6 PASS) + K(green-only release PASS)
  -> profile-specific offset promotion review

X-2/X-3 normalized-150s generation and experiments are a separate branch of evidence.
They never feed native J/K or native offset promotion.
```

Add this gate rule:

```markdown
Each arrow is enforced by an artifact hash dependency, not prose status. A downstream
command verifies prerequisite artifact status=PASS and exact input hashes before work.
NOT_EVALUATED never unlocks a dependency. J-1 is built early; only its live VISSIM
execution waits for the completed plant changes.
```

### Prerequisites

Acceptance of issues 1 through 9.

### Command and artifact

```powershell
python -B scripts/check_plan_dependencies.py `
  --graph evaluation/configs/plant_fidelity_v2_1_dependencies.json `
  --status-dir reports `
  --output reports/dependency_gate_status_v2_1.json
```

### Numeric pass/fail rule

PASS requires graph cycles `0`; missing prerequisite artifacts `0`; prerequisite
statuses other than PASS used to unlock work `0`; prerequisite hash mismatches `0`;
native/normalized cross-profile edges `0`; offset-unlock paths bypassing G3/G6/green-only
`0`. Any nonzero count is FAIL.

## Required Implementation Deliverables

The amendment is complete only when all of these exist and validate:

1. `.gitattributes` and `reports/reproducibility_lock_v2_1.json`.
2. Updated source-of-truth wording in the audit request and NumSim snapshot document.
3. Role-aware strict compiler with raw-ms provenance and exact-lane signal references.
4. `outputs/signal_reference_v2_1.json` plus validation report.
5. Corrected SC12 network-change report and machine-readable SC12 resolution.
6. Active-program/runtime-readback and native timeline report.
7. Native per-SC cycle consumer audit.
8. Strict runner, complete auditor mode, per-case manifests, and paired-future harness.
9. Profile-scoped offset promotion evaluator with default offset actuation disabled.
10. Machine-readable dependency graph and gate-status artifact.

No current historical audit, `reports/signal_reference_20260805.json`, normalized-network
result, or baseline-only matrix result can substitute for these deliverables.
