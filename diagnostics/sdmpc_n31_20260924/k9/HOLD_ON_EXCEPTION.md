# K8-8 — 결정 예외 때 이전 명령 유지(hold on exception)

- 구속: K8 보충 21(sha256 `ca369954977fc5f98e19b84d08932202847d37e36e26f243caa25df2d135d176`) P-1…P-12, §3, §4, §7.2. 고정점 = 작업 메모의 `AMENDMENTS_FIXED.md`.
- 사용자 결정: D-K9-13(예외만 유지, 시간 초과 유지 없음, 설정 키로 켜고 끔), D-K9-14(유지 횟수로 런을 무효로 하지 않음, 보고 머리에 적음), D-K9-17(Q-H1…Q-H7 권장안; Q-H3는 정정 1에 따라 여덟 형).
- 이 커밋(K8-8)은 장치만 넣습니다. 배포 튜닝에는 키가 없으므로 기본은 지금과 같은 엄격 정지입니다. 켜는 것은 K8-10입니다.

## 1. 켜고 끄기

- 튜닝 JSON 최상위 `runtime.decision_error_policy`.
  - 키 없음 또는 `"strict"` = 엄격 정지(74cd495f 동작 그대로).
  - `"hold_previous_on_exception"` = 유지 켬.
  - 그 밖의 값(355의 `"hold_previous"` 포함), 문자열이 아닌 값, 객체가 아닌 `runtime`, 또는 `runtime.decision_timeout_sec`가 있으면 발사 거부.
- `extends` 사슬은 자식부터 읽습니다. 사슬의 모든 파일을 검사하고(위 거부 조건), 가장 자식 쪽에서 선언된 값이 유효합니다. 어디에도 없으면 `strict`. 이 규칙은 셋이 똑같이 씁니다: 워치독 `Read-DecisionErrorPolicy`, `launch_plan.decision_error_policy`, `scripts/decision_hold.py`의 `read_policy_chain`.
- 결정 코드(`evaluation/`, `vendor/`, `plant/`)는 이 키도 환경 변수도 읽지 않습니다.
- 운반: 워치독이 매번 `RW_DECISION_ERROR_POLICY=strict`로 지운 뒤 튜닝에서 읽어 세우고, 한 줄 `RW_DECISION_ERROR_POLICY=<값> (runtime.decision_error_policy)`을 찍습니다. `launch_plan.py`는 같은 값을 `expected_env`에 넣어 `check_provenance`가 대조합니다. 러너는 시작 때 `ValidateDecisionErrorPolicy`로 값을 확인합니다(켜짐이면 `DECISION_ERROR_POLICY=hold_previous_on_exception` 한 줄, 잘못된 값이면 `ERROR=DECISION_ERROR_POLICY_INVALID` + 종료 2).

## 2. 언제 유지하나 (모두 참일 때만)

러너(`RunControllerDecision`, 중첩 If):

1. 어댑터 종료 코드 = 1
2. `RW_DECISION_ERROR_POLICY = hold_previous_on_exception`
3. 직전 적용 명령(`lastActionJson`)이 있음
4. 예열이 아님, 컨트롤러가 `diagnostic-`로 시작하지 않음
5. T ≥ ControlStartSec + 150 (T=900 첫 SDMPC 결정의 예외는 엄격 정지, Q-H2), 5′ ControlStartSec ≥ 0
6. 이번 결정의 `action_T.error.txt`가 있음(decision_failure_report 예외 경로만 씀)

helper `scripts/decision_hold.py`의 자격 판정 E1–E10(하나라도 걸리면 종료 3 → 엄격 정지):

| # | 거부 조건 |
|---|---|
| E1 | 튜닝 정책 ≠ 켜짐, 또는 시간 키·잘못된 값 |
| E2 | `.error.txt` 없음, S6 stderr에 `DECISION_FAILED type=` 줄이 정확히 1개가 아님, 그 줄의 `traceback=` 경로 ≠ `.error.txt` |
| E3 | 사슬의 예외 머리 줄 어디에든 `DecisionDeadline`·`TimeoutError`·`MemoryError`·`KeyboardInterrupt`·`GeneratorExit`·`BrokenProcessPool`·`BrokenPipeError`·`ConnectionResetError` (이름 글자 일치, 여덟 개 닫힌 목록) |
| E4 | traceback의 (파일, 함수) 짝이 직전 명령·이력 계약 목록에 있음, 또는 메시지 `Invalid applied central multiplier warm start` |
| E5 | 상태 `sim_sec` ≠ T, `control_interval_sec` ≠ 150, ControlStartSec < 0, 또는 T − 150 < ControlStartSec |
| E6 | 직전 JSON이 이 런의 바로 앞 결정이 아님(`metadata.sim_sec`, run_id 세 곳) |
| E7 | 직전 JSON이 SDMPC 결정도 유지 기록(+영수증)도 아님 |
| E8 | 직전 CSV 머리·행, SDMPC 원천의 `.applied`(UTF-16, 3줄) 또는 유지 원천 영수증의 CSV sha가 안 맞음 |
| E9 | `obs150/derived_<T>.json`이 없거나 이 런·이 창의 문서가 아님 |
| E10 | 이름을 바꿀 `*.failed_decision`이 이미 있음 |

## 3. 유지하면 무엇이 생기나

- 실패 결정의 부분 산출물(`action_T.json`, `.csv`, `.json.sdmpc_pending`, `.joint_written.json`)은 `<이름>.failed_decision`으로 이름을 바꿉니다. 적용하지 않습니다.
- `action_T.csv` = 직전 CSV **바이트 그대로**.
- `action_T.json` = 직전 JSON에서 `prediction`·`prediction_error`·`projection_diagnostics`와 `diagnostics.sdmpc_prediction_sequence`를 지우고, `metadata`를 작은 사전으로 바꾼 것(`sim_sec`, `controller`, `controller_variant`, `controller_status = hold_previous_on_exception`, `run_provenance`, `far_rate_est_*`·`sat_est_*`, `hold_previous_on_exception`). `sdmpc_state`가 없으므로 다음 결정은 가격을 0에서 다시 시작합니다(P-B′). 이 두 파일의 바이트는 (직전 JSON, 직전 CSV, T, 정책 상수)만의 함수입니다.
- 영수증 `action_T.hold.json`(마지막에 씀): 예외 형·사슬, 자격 판정 결과, 원천·유지 파일 sha, 부분 산출물, 증거 파일 sha, 입력, 벽시계.
- 러너는 평소 경로 `ApplyActionCsv`로 유지 CSV를 다시 씁니다. `.applied`는 생기지 않습니다.
- 런로그: `DECISION_HOLD_ATTEMPT sim_sec=T source=…`, `DECISION_HELD_ON_EXCEPTION sim_sec=T HOLD_OK …`, 끝 요약 `DECISIONS_HELD_ON_EXCEPTION=n`(켜졌을 때만). 유지는 `DECISIONS_FAILED`에 넣지 않습니다.
- helper와 러너의 유지 줄에는 `DECISION_FAILED` 문자열이 나오지 않습니다.

## 4. 유지가 실패하면 = 런 무효

- helper 거부(종료 3, `DECISION_HOLD_REFUSED reason=E<n>`, `action_T.hold_error.txt`), helper 예외(종료 1, `DECISION_HOLD_EXCEPTION`), 종료 0인데 세 파일 중 하나라도 없음 → `ERROR=DECISION_HOLD_FAILED` 뒤 기존 줄(`ERROR=DECISION_EXIT_NONZERO`는 결정의 stderr) → 즉시 정지(`Quit 3`).
- 유지 CSV 적용 실패 → `ERROR=ACTION_CSV_INCOMPLETE` → 정지.
- 시간 제한은 없습니다. 결정과 helper 모두 S6 파일 캡처(`RunDecisionCapture`)로 부르고, 멈춘 결정은 워치독 `StallSec`이 끝냅니다.

## 5. 시험

- `scripts/tests/test_decision_hold.py`: helper 단위 시험(E1–E10, 여덟 형 각각 바깥·사슬 중간, 목록 밖 `ConnectionAbortedError` 유지, 결정성 `PYTHONHASHSEED` 0·2, 바이트 복사, 이름 바꾸기, CSV 열 상수).
- `scripts/tests/test_k8_decision_hold_vbs.py`: 러너 대역(cscript, VISSIM 없음). 보충 21 §7.2 (a)–(v) 중 (o)(r)(u) 밖의 사례, WD·LP·helper 정책 읽기 일치.
- `scripts/tests/test_k8_s6_decision_capture_vbs.py`: `RunDecisionCapture(` 코드 줄 수 2 → 3(호출 2 + 선언 1) 한 곳만 바뀜.
- `diagnostics/sdmpc_n31_20260924/tools/tests/test_tools_watch.py`: 유지 T 보고 사례 2개 추가.
- 감시 도구 `watch_sdmpc.py`는 결정 줄에 목적값(`obj=`·`gain=`)을 찍습니다. J1 분석 전 J1 런에는 쓰지 않습니다(보충 21 S-11).
