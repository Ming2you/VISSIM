# S0R-1 / S0R-3 Independent Code Review

## Verdict

**CHANGES_REQUIRED**

S0R-1과 S0R-3의 기본 happy-path 테스트는 통과하지만, 현재 artifact를 promotion evidence로
사용하기 전에 해결해야 하는 load-bearing false-PASS 경로가 남아 있다. 이번 검토에서는 코드를
수정하지 않았다.

## Critical Findings

### C1. `0240ba8`와 canonical Python tree 사이에 독립적인 trust anchor가 없다

**근거**

- `vendor/NumSim-mine/SNAPSHOT.md:6-11`은 upstream commit 문자열만 선언하고, 그 commit의 Git tree
  OID나 파일별 blob manifest를 보존하지 않는다.
- `scripts/verify_runtime_source.py:356-365`는 selected root가 bundled canonical이면 실제 upstream
  commit을 확인하지 않고 `commit_actual = EXPECTED_SNAPSHOT_COMMIT` 및 `commit_ok = True`로 처리한다.
- `scripts/verify_runtime_source.py:367-390`의 tree 비교 기준은 현재 checkout의 canonical tree 자체다.
  `canonical.tracked_source_clean`은 현재 VISSIM 저장소 index와 같다는 것만 증명하며, 그 bytes가 실제
  NumSim commit `0240ba8`에서 왔다는 것은 증명하지 않는다.

**영향**

vendor Python을 변경한 뒤 그 변경을 VISSIM 저장소에 정상 commit하고 `SNAPSHOT.md`의 문자열만
유지하면, dirty check는 사라지고 새 tree가 스스로의 canonical reference가 되어 PASS할 수 있다.
따라서 현재 보고되는 commit/tree 일치는 self-consistency이지 upstream commit identity가 아니다.

**필수 수정**

`0240ba8`에서 생성한 immutable Git tree OID 또는 파일별 path/blob digest manifest를 별도 trust
anchor로 보존하고 bundled tree를 그 값과 비교해야 한다. clean committed vendor drift가 FAIL하는
회귀 테스트도 필요하다. 현재 테스트는 uncommitted override mutation만 다룬다
(`scripts/tests/test_verify_runtime_source.py:82-140`).

### C2. baseline snapshot PASS가 S0R-1/preflight provenance에 닫혀 있지 않다

**근거**

- `scripts/validate_baseline_snapshot.py:173-203`은 provenance에서 이름, seed, 요청 시간, controller 등
  profile만 검사한다. `preflight_manifest`, preflight hash/fingerprint/status, runtime-source manifest,
  network/SIG/mapping/adapter/watchdog hash 및 Python/VISSIM version은 검사하지 않는다.
- `scripts/tests/test_validate_baseline_snapshot.py:55-75`의 PASS fixture는 위 필드와 `files`,
  `signal_programs`를 모두 생략하며, `scripts/tests/test_validate_baseline_snapshot.py:124-144`가 이를
  완결 baseline으로 고정한다.
- `scripts/run_plant_fidelity_matrix.ps1:125-131`은 baseline snapshot을 먼저 PASS로 publish하고,
  provenance를 더 넓게 검사하는 generic audit는 그 뒤 `scripts/run_plant_fidelity_matrix.ps1:132-160`에
  실행한다. 후속 audit가 실패해도 이미 생성된 `baseline_snapshot_v2_1.json`은 PASS로 남는다.
- snapshot은 자신을 S1/A/DEV-DATA/CERT-PREP/K의 downstream evidence로 선언한다
  (`scripts/validate_baseline_snapshot.py:625-631`).

**재현**

기존 synthetic PASS fixture에서 preflight를 계속 생략하고, `.err`에 `FATAL`을 기록하며,
`action_000900.json`에 비어 있지 않은 signal/VSL 명령을 추가해도 validator 결과는
`status=PASS`, `reasons=[]`였다.

**영향**

S0R-2 또는 runtime provenance가 실패한 run도 baseline artifact만 보면 downstream을 unlock할 수
있다. 이는 `IMPLEMENTATION_PLAN.md:744-745`의 선행 artifact PASS 및 exact-input-hash 계약을 깨뜨린다.

**필수 수정**

baseline validator가 exact `preflight-v3`와 strict `runtime-source-v2.1`의 status/hash/fingerprint를
검증하고 그 값을 자신의 `input_hashes`에 직접 결속해야 한다. 또는 generic audit PASS를 먼저 만든
뒤 그 hash/status를 포함한 baseline snapshot을 마지막에 atomic publish해야 한다. 후속 gate 실패 시
독립적인 PASS snapshot이 남아서는 안 된다.

### C3. preflight fingerprint가 실제 baseline watchdog를 hash하지 않는다

**근거**

- preflight 기본 입력은 `scripts/build_preflight_manifest.py:36`에서
  `scripts/run_real_world_single_watchdog.ps1`로 고정되어 있다.
- 실제 baseline matrix는 `scripts/run_plant_fidelity_matrix.ps1:39`에서
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`를 실행한다.
- 실제 watchdog는 자신의 hash를 별도 run provenance에 기록하지만
  (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:185-189`), baseline validator는 그
  필드나 preflight와의 일치를 검사하지 않는다.

**영향**

PASS preflight fingerprint가 실제 process launcher의 bytes를 보증하지 않는다. 실제 watchdog가
변경되거나 잘못 선택되어도 baseline snapshot은 같은 preflight를 참조하며 PASS할 수 있다.

**필수 수정**

preflight의 watchdog path를 matrix가 실제 실행하는 파일과 단일 source of truth로 공유하고,
baseline validator에서 `run_provenance.files.watchdog_wrapper.sha256`가 preflight의 exact hash와 같은지
검사해야 한다.

## Important Findings

### I1. S0R-1 strict interpreter 계약이 standalone artifact에서는 opt-in이다

- `scripts/verify_runtime_source.py:308-325`의 `RW_PYTHON_EXE` 검사는 `strict=True`일 때만 강제되고,
  parser 기본값은 false다 (`scripts/verify_runtime_source.py:480-486`).
- 계획의 직접 실행 명령 `IMPLEMENTATION_PLAN.md:97-104`에는 `--strict`가 없다. 실제로
  `RW_PYTHON_EXE`를 제거하고 non-strict report를 만들면 `status=PASS`, `strict=False`, Python failure 0이
  재현됐다.
- matrix는 현재 `--strict`를 전달하지만 (`scripts/run_plant_fidelity_matrix.ps1:69-75`), preflight reader는
  runtime report의 `strict=True` 자체를 요구하지 않는다
  (`scripts/build_preflight_manifest.py:406-454`).

Strict를 기본값으로 만들거나 diagnostic 전용 `--allow-nonstrict`를 명시적으로 분리하고, preflight도
`strict=True`와 interpreter check PASS를 요구해야 한다.

### I2. baseline completeness가 파일 존재와 metadata label만 검사한다

- `scripts/validate_baseline_snapshot.py:516-535`는 state/action CSV, readback, stderr, `.err`의 존재만
  검사하며 내용, row count, freshness, run ID를 검사하지 않는다.
- VBS config copy와 wall-time profile 존재/내용은 required artifact 목록에 없다. 이는
  `IMPLEMENTATION_PLAN.md:127-132`의 보존 계약보다 약하다.
- action JSON은 metadata의 `NoControl/no-control` label만 검사한다
  (`scripts/validate_baseline_snapshot.py:394-408`). 실제 lever payload가 no-op인지, action JSON과 CSV가
  같은 action인지 확인하지 않는다.

Main state CSV의 최종 3600초 row, action CSV의 semantic no-op, JSON/CSV hash linkage, PERF/wall-time
evidence, copied VBS config를 검증해야 한다.

### I3. `COM_FAILURES`가 없어도 PASS하며 `.err`는 stale evidence가 될 수 있다

- `scripts/validate_baseline_snapshot.py:249-255`는 `COM_FAILURES` line이 있을 때만 검사하고, 누락을
  failure로 처리하지 않는다. 실제 PASS fixture도 이 line이 없다
  (`scripts/tests/test_validate_baseline_snapshot.py:77-98`). 이는 정상 조건 `COM 실패 0`과 다르다.
- watchdog는 run 전에 source `.err`를 제거하거나 pre-run hash/mtime을 기록하지 않고, 성공 후 존재하는
  파일을 복사할 뿐이다 (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:168-173`,
  `:347-352`). 이전 run의 `.err`가 남아 있으면 현재 run evidence로 복사될 수 있다.
- validator는 `.err` 내용도 검사하지 않아 `FATAL` text가 있어도 preserved-artifact gate가 PASS했다.
  반대로 VISSIM이 clean run에서 `.err`를 만들지 않으면 이유를 구분하지 못하고 NOT_EVALUATED가 된다.

명시적인 COM failure summary를 필수화하고, `.err`의 pre-run 상태를 격리한 뒤 새로 생성된 파일만
run ID/attempt와 연결해야 한다. clean absence도 hash-bound marker로 표현해야 한다.

### I4. Python identity가 version/preflight에 결속되지 않고 현재 파일 상태에 의존한다

- watchdog provenance의 Python evidence는 path/existence/SHA-256뿐이다
  (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:147-153`, `:250`). VBS가 출력하는
  `PYTHON_VERSION`은 baseline validator가 읽지 않는다.
- validator는 recorded hash를 run 당시 immutable record와 비교하는 대신 현재 같은 path의 bytes를
  다시 hash한다 (`scripts/validate_baseline_snapshot.py:490-501`). Python이 정상 update/이동되면 과거
  run이 false FAIL하고, 반대로 runtime-source/preflight와 다른 interpreter였는지는 직접 검사하지 않는다.
- synthetic test는 실행 불가능한 임의 bytes를 `python.exe`로 만들어도 identity PASS가 된다
  (`scripts/tests/test_validate_baseline_snapshot.py:21-28`, `:70-75`).

VBS/adapter가 실제 실행한 `sys.executable`, version, binary hash를 run-time artifact로 기록하고 exact
preflight/runtime-source Python record와 비교해야 한다. live-file drift와 historical-run invalidity는
별도 상태로 구분해야 한다.

## Atomicity And Test Assessment

- `scripts/verify_runtime_source.py:456-477`와 `scripts/validate_baseline_snapshot.py:641-658`의 final JSON
  writer는 same-directory temporary file, flush/fsync, `os.replace`를 사용해 기본 atomicity는 적절하다.
- watchdog의 `run_provenance_*.json`은 direct `WriteAllText`다
  (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:266-271`). 중단 시 partial provenance가
  남을 수 있으므로 같은 atomic publication 규칙을 적용하는 편이 안전하다.
- 대상 테스트 22개는 모두 PASS했다. 그러나 위 C1-C3 및 I1-I4 false-PASS 경로를 포착하지 못한다.
  특히 current synthetic PASS fixture 자체가 missing preflight, missing COM summary, header-only readback,
  content-free artifact 검사를 정상 상태로 고정하고 있다.

## Final Decision

S0R-1/S0R-3는 **구현 완료로 승인할 수 없다**. C1-C3를 먼저 수정하고, 각 finding의 adversarial
regression test를 추가한 뒤 동일 범위로 재검토해야 한다.
