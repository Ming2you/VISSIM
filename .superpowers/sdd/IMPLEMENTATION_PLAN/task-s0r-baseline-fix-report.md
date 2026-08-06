# S0R Baseline/Evidence Fix Round 1/5 Report

## Status

**DONE_WITH_CONCERNS**

요청된 C2/I2/I3/I4 false-PASS 경로는 구현과 synthetic regression test로 차단했다. 최종 대상 테스트는 모두 통과했다. 다만 이 세션에서는 실제 VISSIM COM baseline을 새로 실행하지 못했고, 별도로 시도한 strict runtime-source/preflight CLI 재생성은 장시간 무출력 상태로 timeout되어 concern으로 남긴다.

## Scope Control

이번 작업에서 수정한 파일은 아래 목록뿐이다.

- `scripts/validate_baseline_snapshot.py`
- `scripts/tests/test_validate_baseline_snapshot.py`
- `scripts/run_plant_fidelity_matrix.ps1`
- `scripts/tests/test_run_plant_fidelity_matrix.py`
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`
- `scripts/run_real_world_stackelberg_controller.vbs`
- `scripts/audit_plant_fidelity.py`
- `scripts/tests/test_audit_plant_fidelity.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-s0r-baseline-fix-report.md`

기존 dirty worktree의 vendor/source verifier/compiler/SC12 관련 변경은 수정하지 않았다.

## C2: Exact Source, Preflight, Audit Binding

- baseline validator CLI에 `--runtime-source`, `--preflight`, `--audit`를 필수화했다.
- `runtime-source-v2.1`의 strict PASS/reasons, `preflight-v3`의 PASS/reasons와 canonical fingerprint 재계산, runtime-source path/hash linkage를 검증한다.
- generic audit의 schema, strict/require-complete, status/reasons, completion policy, gate summary, action directory, preflight provenance record를 검증한다.
- run provenance의 preflight path/hash/fingerprint를 exact 비교한다.
- network, tuning, calibration, mapping, adapter, main VBS, 실제 core15n41 watchdog, generated VBS와 41개 resolved SIG의 path/hash를 preflight와 비교한다.
- matrix는 stale baseline/audit 산출물을 먼저 제거하고, 전용 JSON/Markdown 경로로 generic strict audit를 성공시킨 뒤에만 baseline validator를 실행한다.
- audit 실패 시 validator가 호출되지 않고 stale PASS baseline이 남지 않는 동적 PowerShell regression test를 추가했다.

## I2: Deep Completeness And No-Control Semantics

- state CSV가 정확히 `1,5,10,...,3600`의 721개 canonical observation을 갖는지 검사한다.
- 정확히 두 decision `(1, 900)`과 네 anchor `(900,1500,2100,2700)`만 허용하며, 추가/stale state/action/anchor 파일을 거부한다.
- state/action/anchor의 run ID, sim_sec, run manifest path/hash linkage를 검사한다.
- action JSON에서 `NoControl/no-control`, `controller_status=ok`, `no_control_active=1`, `N_P_star=N_UF_star=0`, 빈 allocation을 검사한다.
- no-control 값을 `default.yaml + recursive tuning extends + control mapping + generated VBS`에서 유도한다. 현재 canonical 결과는 다음과 같다.
  - VSL: `120 km/h`
  - model ramp release: 각 `1800 veh/h`
  - physical ramp meter: 각 `900 veh/h`, `green=10s`
  - physical rows: VSL 71, ramp 8, signal 0
  - model phase green: `56s`, offset `0s`
- per-decision CSV의 DSD/link/lane/VSL 및 ramp SC/rate/green을 exact 검사하고 cumulative action CSV와 행 단위로 연결한다.
- signal readback은 no-control에서 header-only여야 한다.
- required artifact로 state/cumulative action CSV, stdout/stderr, signal readback, preserved generated config, wall-time profile, run-bound `.err` marker/artifact를 요구한다.
- signal/VSL/ramp non-noop CSV 및 VSL/ramp non-noop JSON 주입 regression test를 추가했다.

## I3: COM And VISSIM Error Evidence

- VBS가 `COM_FAILURES=<numeric>`를 항상 출력한다.
- direct COM setter/vehicle scan 오류를 집계하고, 최종적으로 `COM_FAILURES >= SIGNAL_FAILURES + OBSERVATION_FAILURES`를 강제한다.
- COM failure가 0이 아니면 `STAGE=SIM_DONE` 전에 integrity failure로 종료한다.
- watchdog는 매 attempt 전에 source network `.err`를 output directory 밖 sibling archive에 hash와 함께 보존한 뒤 제거한다.
- 성공 후 `.err`가 있으면 run별 copy/hash evidence를, 없으면 run ID/attempt/source/check time을 SHA-256 binding한 absence marker를 atomic write한다.
- marker와 wall-time profile의 run ID/name/attempt/exit code를 교차검증한다.
- malformed binding, stale attempt, mixed/orphan artifact, FATAL `.err` regression test를 추가했다.
- generated VBS copy, wall-time JSON, run provenance를 atomic publication으로 변경했다.
- retry cleanup에 `anchor_*.json`을 포함해 실패 attempt의 anchor 재사용을 막았다.

## I4: Exact Python Identity

- watchdog가 exact executable을 직접 실행해 `sys.executable`, full version, normalized version triplet을 기록하고 binary SHA-256을 보존한다.
- validator가 runtime-source, preflight, run provenance, runlog `PYTHON`, `PYTHON_VERSION`의 path/hash/version triplet을 비교한다.
- 현재 파일 hash drift는 historical record 불일치와 분리해 `live_status`로 보고하며, run 당시 기록이 일치하면 과거 run을 자동 무효화하지 않는다.
- synthetic PASS fixture는 실제 `sys.executable` bytes/path/version을 사용한다.
- fake Python path/hash와 wrong runlog version regression test를 추가했다.

## Test Results

성공:

- Final targeted suites: `49 tests`, `12.426s`, PASS
  - `scripts.tests.test_validate_baseline_snapshot`
  - `scripts.tests.test_audit_plant_fidelity`
  - `scripts.tests.test_run_plant_fidelity_matrix`
- Full `scripts/tests`: `81 tests`, `54.159s`, PASS
- `tests.test_vissim_stackelberg_adapter_fidelity`: `2 tests`, `0.416s`, PASS
- In-memory Python compile: PASS
- PowerShell parser check for matrix/watchdog: PASS
- Current canonical no-control derivation: reasons `[]`, VSL 120, 71 VSL rows, 8 ramp rows, ramp 1800/900/10 confirmed.

## Concerns And Interrupted Commands

1. 실제 VISSIM COM baseline run은 이 세션에서 실행하지 않았다. 따라서 VBS의 COM 출력과 watchdog의 live `.err` lifecycle은 static/source tests와 synthetic artifacts로 검증됐지만 실제 VISSIM process로 재현되지는 않았다.

2. 아래 추가 strict CLI 명령은 출력 없이 장시간 실행되어 timeout됐다. traceback은 없었다.

```text
verify_runtime_source.py --strict 후 build_preflight_manifest.py --strict 연속 실행
exit=124, timeout=300.4s, stdout/stderr 없음

build_preflight_manifest.py --strict 단독 재시도
exit=124, timeout=120.4s, stdout/stderr 없음
```

동일 verifier/preflight 코드의 repository/synthetic test는 full `scripts/tests`에서 PASS했다.

3. VBS 직접 syntax 실행 시 host의 CScript 설정 접근이 거부됐다.

```text
cscript.exe //nologo scripts\run_real_world_stackelberg_controller.vbs
CScript Error: Loading your settings failed. (Access is denied.)
```

4. 마지막 full-suite 재실행은 사용자 중단 시점에 종료됐고 남은 Python process도 종료했다. 그 전에 full 81개가 PASS했고, 중단 후 최종 변경 영향 범위 49개를 다시 PASS했다. 남아 있는 장기 Python process는 없다.

## Self Review

- audit-before-validator 순서와 stale PASS 제거를 확인했다.
- validator 최종 JSON은 same-directory temporary file, fsync, `os.replace`로 atomic write한다.
- provenance는 decision 시작 전 한 번 atomic write되어 adapter가 기록한 manifest hash가 이후 변경되지 않는다.
- success는 `STAGE=SIM_DONE`과 process exit code 0을 동시에 요구한다.
- strict gate를 완화하지 않았고, missing evidence는 NOT_EVALUATED 또는 FAIL로 남아 nonzero exit가 된다.
- 알려진 남은 항목은 실제 VISSIM live run 검증과 위 strict CLI 장기 실행 원인 확인뿐이다.

---

# Fix Round 2/5 - C2/I2/I3 Re-review Closure

## Status

**DONE**

The three `NOT_ADDRESSED` findings in `task-s0r-rereview-fix1.md` were implemented and
covered by fail-closed regression tests. Per the round-2 instructions, no standalone
runtime-source probe and no VISSIM COM run were executed.

## C2 - Exact Validator and Evidence Chain

- `validate_baseline_snapshot.py` now hashes the current
  `verify_runtime_source.py`, `build_preflight_manifest.py`, and
  `audit_plant_fidelity.py` commands and rejects any artifact whose command name,
  schema version, or command SHA-256 differs.
- Runtime-source certification requires the fixed full NumSim commit, root/src tree
  identities, trust-anchor semantic SHA-256, all 39 current verifier check IDs at
  `PASS`, all 96 canonical/selected Python paths and normalized Git blob identities,
  and the complete 19-module canonical/selected import identity.
- Preflight certification requires the exact current builder, the complete dynamically
  derived check inventory, all checks at `PASS`, all current artifact path/hash pairs,
  the 41 resolved SC/SIG records, and strict runtime-source path/hash/source/Python
  linkage.
- The generic audit artifact now publishes `input_hashes`, `command_version`,
  `reasons`, `sample_dimensions`, `units`, `downstream_consumers`, and
  `artifact_evidence`. The baseline validator independently recomputes the audit
  command hash, primary inputs, SIG hashes, action-directory file set/count/hash,
  JSON inventories, required gate list/count/status, completion policy, gate summary,
  preflight provenance, and VISSIM error evidence.
- The positive baseline fixture now uses the real 96-file trust anchor, a complete
  production-shaped runtime-source artifact, the current preflight builder with all
  41 SC/SIG checks, and the real no-control tuning/mapping contract. Empty checks,
  skeletal audit evidence, and fabricated all-`a` command hashes are regression-tested
  as failures.

## I2 - CSV, Readback, and Run-bound Artifacts

- State CSV validation requires the exact VBS 13-column header and all 721 canonical
  observations. Every row validates integer/nonnegative vehicle counts, category mass
  identity, stopped count bounds, finite speed ranges, exact no-control mode/status,
  and finite nonnegative decision wall time within the runtime hard limit.
- Cumulative action validation now checks the `readback` column. VSL rows require a
  nonempty non-`ERR` readback; ramp rows require `GREEN`, `AMBER`, or `RED`; any signal
  actuation remains forbidden for the no-control baseline.
- The watchdog atomically writes `run_artifact_manifest_<name>.json` after successful
  exit. It binds the immutable run provenance plus state/action CSVs, stdout/stderr,
  signal readback, preserved generated config, VISSIM error evidence, wall-time profile,
  and every decision/anchor/action JSON/CSV to one run ID and attempt with path, size,
  SHA-256, and modification time. This avoids changing the provenance hash already
  embedded in action JSON while proving final CSV freshness and run linkage.
- Regression tests reject the former two-column state CSV, nonfinite/negative row data,
  post-finalization CSV drift, and `ERR:VSL readback mismatch`.

## I3 - Fail-closed VISSIM Error Lifecycle

- Both the generic audit and baseline validator require `stale_pre_run` to be an
  explicit list and fail strict baseline certification when it is nonempty.
- Every stale record is checked for attempt validity, network source path, exact sibling
  archive path, run separation, archive existence/hash, timestamp syntax, and
  `ERROR`/`FATAL` text.
- An absence marker is rechecked against the live source `.err`; recreation after the
  marker is a failure. A present marker requires both the current source and preserved
  run artifact to exist with identical hashes and exact run-bound paths.
- Malformed stale records, stale hash mismatch, FATAL stale archive, source recreation,
  present-source drift, stale/mixed attempt, malformed binding, and orphan/mixed-run
  artifacts are covered by regression tests.

## Files Changed in Round 2

- `scripts/validate_baseline_snapshot.py`
- `scripts/audit_plant_fidelity.py`
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`
- `scripts/tests/test_validate_baseline_snapshot.py`
- `scripts/tests/test_audit_plant_fidelity.py`
- `scripts/tests/test_run_plant_fidelity_matrix.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-s0r-baseline-fix-report.md`

The source verifier, vendor snapshot/trust anchor, compiler, and SC12 implementation/tests
were not modified in this round.

## Verification Commands and Results

Target suites:

```text
<python> -B -m unittest scripts.tests.test_validate_baseline_snapshot scripts.tests.test_audit_plant_fidelity scripts.tests.test_run_plant_fidelity_matrix
Ran 59 tests in 36.659s - OK
```

Final full suite:

```text
<python> -B -m unittest discover -s scripts/tests -p test_*.py
Ran 92 tests in 77.711s - OK
```

Static verification:

```text
PowerShell parser: run_plant_fidelity_matrix.ps1 and core15n41 watchdog - PASS
Python in-memory compile: validator/audit and their affected tests - PASS
git diff --check on tracked affected files - PASS (line-ending warnings only)
whitespace check on untracked affected Python files - PASS
```

No test failure, traceback, or remaining implementation item was observed. The intentionally
excluded live runtime-source/VISSIM COM executions remain outside this round's verification
scope and are not represented as PASS evidence.

---

# Fix Round 3/5 - C2/I2 Residual Closure

## Status

**DONE_WITH_CONCERNS**

Both residual findings in `task-s0r-rereview-fix2.md` are implemented and their requested
counterexamples fail closed. The concern is verification scope only: the explicitly prohibited
runtime-source CLI probe suite and the two matrix dry-run tests that invoke that probe were not
executed. No VISSIM process or COM action was started.

## C2 - Current Auditor Replay and Semantic Equality

- `audit_plant_fidelity.py` now records a deterministic, fully resolved replay invocation for
  every build-affecting path/list/policy argument. Replay rejects unexpected/missing fields and
  forbids `.err` copy-target side effects.
- The auditor publishes a SHA-256 over a canonical semantic projection that excludes only
  nondeterministic generation/worktree fields. The projection includes every gate, all input
  hashes and primary evidence, state observations, action-directory inventory and contracts,
  projection/runtime/preflight evidence, VISSIM error evidence, completion policy, and strict
  result.
- `validate_baseline_snapshot.py` loads the exact current auditor, rebuilds the complete audit
  from the supplied invocation against the current baseline directory/files, and compares the
  complete canonical projections and independently recomputed hashes. It does not accept the
  stored semantic hash as proof.
- The validator also requires the replay repository to be the current repository, the action
  directory to be the baseline directory, the exact required-gate order, strict/complete mode,
  and an explicit NumSim root identical to the preflight selected runtime root.
- `run_plant_fidelity_matrix.ps1` passes the explicit effective NumSim root to the generic audit,
  making replay independent of a later environment change.
- The positive fixture now invokes the real current auditor with production-complete state,
  projection, runtime provenance, preflight provenance, artifact inventory, and `.err` evidence.
  It no longer manufactures `{status, reason}` gate maps. A synthetic tie-free assignment input
  is bound through the real preflight artifact so the positive fixture itself is strict PASS.
- Regression tests recompute the supplied semantic hash after replacing all gates with
  status-only records or emptying global evidence containers; both still fail because current
  auditor replay semantics differ.

## I2 - Run-window Freshness

- The watchdog run artifact manifest now declares the exact wall-time run window, a fixed
  2-second filesystem timestamp tolerance, and exhaustive artifact roles:
  `simulation_output`, `post_exit_evidence`, and `pre_run_input`.
- State/action cumulative CSV, stdout/stderr, signal readback, and every per-decision/anchor
  JSON/CSV must have current and recorded mtimes inside the process start/finish window.
  VISSIM error evidence and wall profile must fall between process finish and manifest
  finalization. The preserved generated config is explicitly classified as a pre-run input.
- The watchdog captures process finish before writing post-exit evidence and records
  `finalized_at_utc` only after all output/decision hashes have been collected.
- The validator cross-checks wall profile start/finish against the manifest run window, enforces
  start <= finish <= finalize, verifies exact role inventories, and applies the role-specific
  mtime bounds in addition to existing path/hash/size/current-mtime checks.
- Regression tests set the state CSV or a single decision action JSON mtime to 2000-01-01, then
  regenerate both the run artifact manifest and the real auditor artifact. Both packages fail
  solely on run-window freshness, closing the previous rewrapping false-PASS path.

## Files Changed in Round 3

- `scripts/audit_plant_fidelity.py`
- `scripts/validate_baseline_snapshot.py`
- `scripts/run_plant_fidelity_matrix.ps1`
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`
- `scripts/tests/test_audit_plant_fidelity.py`
- `scripts/tests/test_validate_baseline_snapshot.py`
- `scripts/tests/test_run_plant_fidelity_matrix.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-s0r-baseline-fix-report.md`

The source verifier, vendor/trust-anchor files, compiler, SC12 implementation/tests, and VBS
controller were not modified in round 3. Their pre-existing worktree changes were left intact.

## Verification Commands and Results

Focused residual tests:

```text
<python> -B -m unittest scripts.tests.test_validate_baseline_snapshot
Ran 20 tests in 92.529s - OK

<python> -B -m unittest scripts.tests.test_audit_plant_fidelity
Ran 31 tests in 3.153s - OK

Focused PASS/status-only/stale-state/stale-decision subset
Ran 4 tests in 15.303s - OK
```

All safe `scripts/tests` coverage under the no-runtime-probe constraint:

```text
audit + preflight + topology + baseline + SC12 suites
Ran 75 tests in 117.169s - OK

matrix/watchdog static, guard, help, and stubbed failure-path tests
Ran 9 tests in 2.177s - OK

Total distinct tests executed in the final safe scope: 84 - OK
```

Static verification:

```text
PowerShell parser: matrix and core15n41 watchdog - PASS
Python in-memory compile: auditor, validator, and affected tests - PASS
git diff --check - PASS (line-ending warnings only)
```

An initial `py_compile` command could not create `scripts/__pycache__` because the working
directory denies that generated-directory write; the same source set was compiled in memory
without writing bytecode and passed. One matrix failure-path test initially stopped early when
NumSim normalization required a non-existent stub vendor directory. Root cause was the eager
`Resolve-Path`; changing it to absolute path normalization while leaving existence enforcement
to the verifier/auditor restored the intended failure ordering, and the test passed on rerun.

Not run by explicit instruction: `scripts.tests.test_verify_runtime_source` (9 tests), the two
matrix dry-run expansion tests that invoke the real runtime-source verifier, any standalone
runtime-source probe, and all VISSIM/COM execution. These exclusions are why the round status is
`DONE_WITH_CONCERNS`, not an implementation concern or a relaxed gate.

Final post-self-review rerun after adding the replay copy-target field:

```text
<python> -B -m unittest scripts.tests.test_validate_baseline_snapshot scripts.tests.test_audit_plant_fidelity
Ran 51 tests in 95.462s - OK
```
