# S0R source/preflight fix round 1/5

## Status

**DONE**

리뷰 `task-4-s0r1-s0r3-review.md`의 C1, C3, I1을 수정했다. 요청에 따라 baseline
validator, watchdog 구현, VBS는 수정하지 않았다.

## 변경 사항

### C1: immutable upstream trust anchor

- `vendor/NumSim-mine/UPSTREAM_TREE.json`을 추가했다.
  - upstream: `https://github.com/Ming2you/Numerical-Sim.git`
  - commit: `0240ba89b97bf43438e1a0f519f7b0c978288913`
  - root tree: `ce7ec4e66d936a53f77e7586977775b8b4eef186`
  - src tree: `f90966498b75bfd29639e0649491d68b2e8a6424`
  - object format: `sha1`
  - 정렬된 `src/**/*.py` path/blob OID: 96개
- anchor semantic SHA-256
  `46f09f3ca71f2b9388e86864fe49c1781b35180a1db859d8bea583a3b3bd6cf9`를
  verifier에 고정했다.
- verifier는 checkout Python 파일을 LF로 정규화한 뒤 Git blob framing
  (`blob <length>\0<bytes>`)으로 OID를 계산하고 anchor의 path/blob과 비교한다.
- bundled canonical과 selected override 모두 anchor의 96 path/blob identity를 만족해야 한다.
- selected override는 exact full Git commit, full snapshot commit, clean tracked source,
  anchor byte identity와 import module path/hash를 모두 만족해야 한다.
- current VISSIM index/blob과 raw checkout SHA-256/EOL 기록은 유지하되 upstream 신뢰 근거로
  사용하지 않는다.
- clean Git commit으로 vendor content를 변경한 fixture도
  `canonical.anchor_python_blobs=FAIL`이 되는 negative test를 추가했다.

### I1: strict fail-closed

- source verifier CLI 기본값을 strict로 변경했다.
- 비엄격 실행은 `--allow-nonstrict`를 명시해야만 가능하다. 기존 `--strict`는 호환된다.
- preflight는 runtime-source report의 `strict is True`, full expected commit, 그리고 19개
  trust-anchor required check가 모두 `PASS`인지 강제한다.
- nonstrict report와 required anchor check 누락을 각각 실패시키는 테스트를 추가했다.

### C3: actual watchdog identity

- preflight 기본 watchdog를
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`로 변경했다.
- matrix가 preflight builder에 실제 `$watchdog`를 `--watchdog $watchdog`로 명시 전달한다.
- default path와 matrix 전달식을 고정하는 regression test를 추가했다.
- 실제 strict preflight artifact의 watchdog SHA-256은
  `8423a7168f4aa5f35b04f10c40e8cef5e19aa7843925ca3ce711b9f3160c615e`였다.

### 유지한 계약

- runtime-source/preflight의 global artifact keys를 유지했다.
- source import root/module path/hash 및 external import 검사를 유지했다.
- 두 JSON writer의 same-directory temp, flush/fsync, `os.replace` atomic publish를 유지했다.

## 변경 파일

- `.gitattributes`
- `vendor/NumSim-mine/SNAPSHOT.md`
- `vendor/NumSim-mine/UPSTREAM_TREE.json` (new)
- `scripts/verify_runtime_source.py` (new shared-tree file)
- `scripts/build_preflight_manifest.py` (new shared-tree file)
- `scripts/run_plant_fidelity_matrix.ps1`
- `scripts/tests/test_verify_runtime_source.py` (new shared-tree file)
- `scripts/tests/test_build_preflight_manifest.py` (new shared-tree file)
- `scripts/tests/test_run_plant_fidelity_matrix.py` (new shared-tree file)
- `tests/test_vissim_stackelberg_adapter_fidelity.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-s0r-source-fix-report.md` (this report)

## 테스트

Bundled Python:

```text
C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

Targeted verifier:

```powershell
& $python -B -m unittest scripts.tests.test_verify_runtime_source -v
```

- 9/9 PASS
- anchor tamper, clean committed vendor drift, source drift, snapshot mismatch, explicit
  nonstrict, strict-default missing interpreter, EOL normalization, atomic write 포함

Targeted preflight/matrix:

```powershell
& $python -B -m unittest scripts.tests.test_build_preflight_manifest scripts.tests.test_run_plant_fidelity_matrix -v
```

- 18/18 PASS
- nonstrict report rejection, missing trust check rejection, watchdog default/forwarding 포함

전체 회귀:

```powershell
& $python -B -m unittest discover -s scripts/tests -q
& $python -B -m unittest discover -s tests -q
Push-Location plant
try { & $python -B -m unittest discover -s tests -q } finally { Pop-Location }
```

- `scripts/tests`: 72/72 PASS
- root `tests`: 10/10 PASS
- `plant/tests`: 82/82 PASS

실제 strict chain:

```powershell
$env:RW_PYTHON_EXE = $python
& $python -B scripts/verify_runtime_source.py --repo . --out outputs/runtime_source_v2_1.json --strict
& $python -B scripts/build_preflight_manifest.py --repo . `
  --runtime-source outputs/runtime_source_v2_1.json `
  --watchdog scripts/run_real_world_single_watchdog_distributed_core15n41.ps1 `
  --out outputs/preflight_manifest_v3.json --strict
```

- runtime-source: `PASS`, `strict=true`, reasons 0, anchored Python files 96
- preflight: `PASS`, reasons 0, required anchor failures 0
- preflight fingerprint:
  `57fb66cfcf4e874c4ef9d31f8d8b280466330e2056b628be066eaf281b03b6cf`

## Self-review

- local upstream clone를 `-c safe.directory=C:/tmp/numsim-trust-anchor`로 읽어 anchor와
  독립 대조했다: commit/root tree/src tree/object format 모두 일치, 96/96 path/blob mismatch 0.
- clean committed drift test에서 `canonical.tracked_source_clean=PASS`인 동시에
  `canonical.anchor_python_blobs=FAIL`임을 확인해 self-proof 경로가 제거됐음을 확인했다.
- strict 기본 실행과 explicit nonstrict 실행을 각각 검증했고, preflight는 nonstrict artifact를
  거부한다.
- preflight artifact가 matrix의 실제 distributed watchdog path/hash를 기록함을 확인했다.
- trailing whitespace 0, Python compile PASS, 전체 회귀 PASS.
- 범위 밖인 `scripts/validate_baseline_snapshot.py`,
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`, VBS는 수정하지 않았다.
