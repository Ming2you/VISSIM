# S0R-2/3 코드 리뷰

## 판정

**CHANGES_REQUIRED**

대상은 `scripts/audit_plant_fidelity.py`, `scripts/run_plant_fidelity_matrix.ps1`,
`scripts/tests/test_audit_plant_fidelity.py`, `scripts/tests/test_run_plant_fidelity_matrix.py`의 현재 변경분이다.
`IMPLEMENTATION_PLAN.md`의 S0R-2/3 계약과 대조했다.

## 발견 사항

### [Critical] baseline 완결성을 판정하는 gate가 없어 불완전하거나 오염된 run도 통과할 수 있다

- `scripts/run_plant_fidelity_matrix.ps1:37-47`은 `-BaselineOnly`일 때 새 case 하나를 생성할 뿐,
  지정된 `OutDir`이 비어 있는지 또는 이번 invocation의 parent만 포함하는지 확인하지 않는다.
- 같은 파일 `:80-114`는 `OutDir` 전체를 auditor의 `--action-dir`로 넘긴다.
- `scripts/audit_plant_fidelity.py:1129-1172`는 해당 디렉터리를 재귀 탐색하고,
  `:1764-1772`의 `action_inventory`는 state/action JSON이 하나라도 있으면 PASS한다.
- 어느 gate도 `actual_sim_sec=3600`, anchor `900/1500/2100/2700` 정확히 4개,
  baseline parent 정확히 1개, 예상 decision/action 수, action/readback 누락 0을 검증하지 않는다.

따라서 과거 case나 archive가 남은 `OutDir`, 일부 파일만 있는 run, 다른 seed/demand parent가 섞인
디렉터리도 현재 필수 gate들이 우연히 PASS하면 baseline snapshot으로 인정될 수 있다. 이는
`IMPLEMENTATION_PLAN.md:125-132`의 S0R-3 핵심 완료 조건을 직접 위반한다.

### [Critical] S0R-2의 `preflight-v3` 증거와 고정된 provenance fingerprint가 구현되지 않았다

- `scripts/run_plant_fidelity_matrix.ps1:87-114`가 auditor에 전달하는 실행 문맥은 `--repo`,
  `--action-dir`, strict 관련 옵션뿐이다. `outputs/preflight_manifest_v3.json`을 생성하거나 case에
  그 hash를 전달하는 경로가 없다.
- `scripts/audit_plant_fidelity.py:1518-1550`의 `signal_controller_scope`는 scope 간 산술 일관성만
  검사하므로 model SC가 정확히 41인지 강제하지 않는다.
- 같은 파일 `:1817-1891`은 일반 audit manifest를 만들지만, 41개 SC가 `supplyFile2`로 선택한
  SIG 41개의 정합성, Python/VISSIM version, runner/VBS/adapter를 포함한 preflight fingerprint,
  모든 case의 동일 preflight hash 참조를 검증하지 않는다.

현재 gate 목록을 모두 통과해도 `IMPLEMENTATION_PLAN.md:118-123`의 selected SC/SIG 수와
case 공통 provenance 조건은 증명되지 않는다. 이 상태의 결과는 S0R-2 promotion evidence가 될 수 없다.

### [Important] strict 실행이 항상 적용되지 않고 Python 검증도 VISSIM 실행 뒤에 수행된다

- 계획은 matrix runner가 auditor를 항상 `--strict --require-complete`로 호출하도록 요구하지만,
  `scripts/run_plant_fidelity_matrix.ps1:92-113`은 사용자가 두 switch를 준 경우에만 전달한다.
  옵션 없이 실행하면 FAIL/NOT_EVALUATED가 exit 0으로 남을 수 있다.
- `RW_PYTHON_EXE` 존재 검사는 같은 파일 `:80-85`, 즉 모든 VISSIM case를 실행한 뒤에 있다.
  strict run도 잘못된 interpreter 환경으로 수 시간 실행한 다음에야 중단될 수 있다.
- runner는 `RW_PYTHON_EXE`를 watchdog/VBS argument나 VBS가 사용하는 환경 계약으로 전달하지 않고,
  auditor 실행에만 사용한다. 따라서 audit Python과 실제 adapter Python이 같다는 보장이 없다.

strict 전제 검사는 case loop 전에 끝나야 하며, production VBS가 실제 사용하는 interpreter identity와
동일한 값이 provenance에 기록되어야 한다.

### [Important] PowerShell help 계약이 없고 help 요청이 실제 simulation 경로를 연다

- `scripts/run_plant_fidelity_matrix.ps1:1-19`에는 동작하는 help switch나 advanced-script help 계약이 없다.
- 실제 확인 결과 `--help -DryRun`과 `-? -DryRun` 모두 도움말 대신 9개 matrix case를 확장하고 exit 0했다.
- 더 위험하게 `-?`만 실행했을 때 첫 VISSIM case가 실제로 시작됐다. 검토 과정에서 시작된 프로세스는
  종료되었고 남은 `VISSIM/cscript` 프로세스가 없음을 확인했다.
- `scripts/tests/test_run_plant_fidelity_matrix.py:31-51`에는 help contract test가 없다.

이는 `IMPLEMENTATION_PLAN.md:111-114`의 `--help` contract test 선행조건을 충족하지 못하며,
운영자가 단순히 도움말을 요청해도 실험을 시작할 수 있는 안전 문제다.

### [Important] 필수 `vissim_error_log` gate가 이번 run의 보존된 `.err`를 읽지 않는다

- matrix는 watchdog가 run output에 보존한 `.err` 경로를 auditor에 전달하지 않고
  `scripts/run_plant_fidelity_matrix.ps1:87-91`에서 `--action-dir`만 지정한다.
- auditor는 명시적 `--vissim-err`가 없으면 `scripts/audit_plant_fidelity.py:1840`에서 network 옆의
  `.err`를 선택한다. CLI 기본도 `:2076`에 그렇게 정의되어 있다.
- 따라서 `:95-109`에서 `vissim_error_log`를 required gate로 지정해도, 이번 parent의 run별 보존본이
  아니라 mutable/stale network `.err` 또는 마지막 case의 파일만 판정할 수 있다.

S0R-3의 “각 run directory에 `.err` 보존” 계약과 gate의 실제 입력이 연결되지 않아 오류 attribution과
재현성이 깨진다.

### [Important] 테스트가 실제 CLI exit와 PowerShell argument forwarding 경로를 실행하지 않는다

- `scripts/tests/test_audit_plant_fidelity.py:145-180`은 `completion_policy()`와
  `audit_exit_code()` helper만 직접 호출한다. `main()`을 실행해 `--strict`, `--require-complete`,
  반복 `--required-gate`, unknown gate의 실제 process exit를 검증하지 않는다.
- `scripts/tests/test_run_plant_fidelity_matrix.py:31-51`의 성공 경로는 모두 `-DryRun`이다.
  matrix 본문의 `if (-not $DryRun)` 블록이 `scripts/run_plant_fidelity_matrix.ps1:80`에서 통째로
  건너뛰어지므로 auditor argument 배열, repeated `--required-gate`, `$LASTEXITCODE` 전파,
  strict Python 검증을 테스트하지 않는다.
- baseline test는 출력 한 줄과 부분 문자열 `demand=1`, `seed=13`만 검사하고, fresh output,
  정확한 parent manifest, 4 anchors 및 완결성 gate를 검증하지 않는다.

현재 24개 대상 테스트는 모두 PASS했지만 위 결함을 탐지할 수 없는 구조다. watchdog와 auditor를
주입 가능한 stub으로 바꾼 spawn test, auditor `main()` process-level exit test, help test,
stale/mixed `OutDir` fault-injection test가 필요하다.

## 정상으로 확인된 부분

- `scripts/audit_plant_fidelity.py:2015-2045`의 helper 기준으로는 `--strict`가 전체 FAIL을 exit 2로,
  `--require-complete`가 선택된 required gate의 PASS 이외 상태를 exit 3으로 처리하며 우선순위도 일관된다.
- `scripts/run_plant_fidelity_matrix.ps1:37-47`은 메모리상 case expansion 기준으로
  `-BaselineOnly`를 demand 1.0 / seed 13 한 건으로 고정한다. 사용자 지정 seed/demand를 함께 줘도
  dry-run은 한 건으로 유지됨을 확인했다.
- `scripts/run_plant_fidelity_matrix.ps1:87-114`의 PowerShell 배열 splatting 문법 자체는 올바르다.
  문제는 전달할 계약/경로의 누락과 해당 경로를 테스트하지 않는 데 있다.

## 검증

- 대상 unit/CLI test: **24/24 PASS**
- `-BaselineOnly -DryRun -Seeds 29 -DemandScales 1.25`: 정확히 nominal demand 1.0 / seed 13 한 건
- `--help -DryRun`: 도움말 대신 9-case expansion, exit 0
- `-? -DryRun`: 도움말 대신 9-case expansion, exit 0

