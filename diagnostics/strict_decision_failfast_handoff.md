# Strict Ω decision failure: watchdog → VBS proposal

`strict_decision_failfast.patch` is prepared and **not applied**. It changes only the canonical watchdog wrapper and VBS runner. No VISSIM COM connection was created and no live source was edited.

The existing adapter can report a failed decision; the normal VBS path increments `decisionsFailed` but keeps running the preceding command until the final integrity check. That behavior would allow a strict Ω candidate failure to continue a run with an unintended policy. The adapter-side exception propagation is a separate prerequisite: `diagnostics/area_failfast.patch` from flow_feedback. This runner patch cannot detect a silently successful fallback inside an adapter.

The wrapper resolves the existing `control_area_objective.enabled` key and sets `RW_DECISION_FAIL_FAST` for its child process. It resets a stale inherited value to0 on every launch. The existing single-parent `extends` chain is followed for that key so a thin child overlay cannot silently disable strict failure handling. Child enabled:false and null section override the parent; missing enabled inside a child object inherits it. Unreadable or cyclic tuning fails before starting a decision because the effective strict setting cannot be established. There is no new configuration flag.

When the selected run is diagnostic **or** this derived environment value is1, any nonzero child exit, missing CSV or failed `ApplyActionCsv` validation stops the fake/real simulation, closes the existing output handles and exits3. Diagnostic errors retain `ERROR=DIAGNOSTIC_DECISION_FAILED`; strict normal controllers use `ERROR=STRICT_DECISION_FAILED`. Successful decisions continue, and absent/OFF configurations retain the previous continuation behavior. Existing watchdog retry policy is unchanged.

Validation: `python -m unittest diagnostics.test_strict_decision_failfast` passed **6 tests /12 subprocess cases** in8.387s. The harness reuses `test_profile_runner_invocation.py` to extract actual proposed VBS functions. Only VISSIM objects and state capture are faked; the child Python process, command capture, actual CSV validation/application, the proposed PowerShell gate and its environment inheritance are executed. Cases cover wu-link child exit7, missing/incomplete output, OFF/absent/null with stale incoming env1, enabled inherited through extends, explicit child disabled, existing diagnostic error label, a valid real n7 CSV success and cyclic tuning rejected before any decision.

The initial sandbox run could not start Windows Script Host (`Loading your settings failed: Access is denied`). The same bounded fake-COM tests passed with the approved Windows Script Host execution outside that sandbox. This is a test-host settings issue, not a VISSIM runtime result.

`git apply --check diagnostics/strict_decision_failfast.patch` passed. The builder preserves mixed CRLF/LF regions instead of normalizing production files. Source and proposed hashes are in `strict_decision_failfast_manifest.json`.

Package contents:

- `prepare_strict_decision_failfast.py`: reproducible patch builder, never edits production.
- `strict_decision_failfast.patch`: wrapper+VBS integration, apply once after the live freeze is lifted.
- `strict_decision_failfast_manifest.json`: exact source/proposed hashes.
- `test_strict_decision_failfast.py`: independent new regression test; existing harness was only imported.

This patch does not overlap adapter-only `area_failfast.patch` or the replacement `legsplit_single_transfer.patch`. The latter replaces the earlier incomplete `legsplit_receiving.patch`; it is not bundled or reimplemented here. Root owns package integration and actual VISSIM validation.
