# S1 Compiler Fix Round 1/5 Report

## Status

DONE

## Scope

- `plant/src/vissim_strict/compiler.py`
- `plant/src/vissim_strict/signal_program.py`
- `plant/tests/test_vissim_strict_compiler.py`
- Existing `plant/tests/test_vissim_strict_signal_program.py` remains compatible and passing.

No production or test code outside the permitted plant compiler/signal scope was changed in this fix round.

## Finding 1: headless controller exclusion

### Fix

- Replaced the broad `supplyFile2 + zero heads => model_excluded` rule with an explicit exception table containing only SC9004.
- SC9004 is excluded with reason `explicit_sc9004_exclusion_no_signal_head_references` only while it has a supply file and zero referenced signal heads.
- Any other supplied controller with zero referenced heads is classified `invalid` with reason and validation error `missing_signal_head_provenance`.
- If SC9004 later gains a referenced head, the normal `model_selected` rule takes precedence.

### Negative evidence

`test_headless_non_exception_controller_fails_closed` compiles a mutated synthetic controller with a valid supply file but no signal head. It verifies:

- classification is `invalid`, not `model_excluded`;
- `excluded_controllers` is empty;
- validation is false;
- `missing_signal_head_provenance` is present in the error set.

## Finding 2: daily program and active schedule provenance

### Parser

- Added backward-compatible `parse_sig_definition(path)` while preserving `parse_sig(path, progNo)` and `parse_sig_programs(path)` behavior.
- Added deterministic parsing for VISSIG `dailyProgLists/dailyProgList/dailyProgListItem`.
- Preserves daily list ID/name and raw integer `time` milliseconds plus seconds and referenced `prog_id`.
- Rejects duplicate list IDs, duplicate item times, out-of-day times, empty lists, unknown child elements, and references to undefined programs.

### Compiler artifact

Each selected controller now records:

- configured INPX `signalController.progNo`;
- whether it selects a static program or a SIG daily program list;
- INPX daily-program structure status;
- SIG daily-list definition status and all parsed lists/items;
- INPX `simulation.startTm` as runtime-start provenance;
- a half-open `[start,end)` time-of-day schedule expanded to 86,400,000 ms;
- the program effective at runtime start;
- compile-time resolution status;
- runtime COM readback provenance as `NOT_EVALUATED` with an explicit reason;
- `fallback_used=false` in every path.

Ambiguous program/list IDs, unresolved `progNo`, and a daily-list gap at runtime start produce non-PASS validation evidence without selecting a fallback program.

### Synthetic schedule evidence

`test_daily_program_list_expands_at_inpx_runtime_start_without_fallback` uses `progNo=1000`, `startTm=3600`, and daily entries:

- `[0, 3,000,000) -> program 1`
- `[3,000,000, 7,200,000) -> program 2`
- `[7,200,000, 86,400,000) -> program 3`

It verifies program 2 at simulation start, exact millisecond interval expansion, no fallback, and runtime readback `NOT_EVALUATED`.

### Current network evidence

The current INPX has no daily-program structure, and each selected external SIG has an empty `<dailyProgLists />`. The artifact pins:

- `active_program_schedule_status=absent_in_inpx`;
- per-controller `sig_daily_program_list_status=empty_in_sig`;
- static active selection provenance `static_inpx_progNo`;
- runtime readback status `NOT_EVALUATED`;
- no fallback.

## Binding Results

- validation: `valid=True`, errors `0`
- selected model controllers: `41`
- compiled SIG schedules: `41`
- compiled programs: `123`
- auxiliary controllers: `8`
- excluded controllers: `1`, exactly SC9004
- three complete compile canonical hashes: one unique hash
- three topology hashes: one unique hash

## Tests

- Targeted signal/compiler tests: `11/11 PASS`
- Full plant suite: `82/82 PASS`
- Syntax compilation: PASS
- `git diff --check` for scoped files: PASS

## Self-review

- Existing seconds API and active-program `parse_sig` behavior remain covered by prior tests.
- Daily list iteration is numerically deterministic and interval endpoints are exact integer milliseconds.
- Static `progNo` is asserted only when it resolves to an actual program.
- Daily-list effective program is derived from INPX runtime start and never synthesized.
- Runtime readback is not fabricated by the compile-time artifact.
- Unrelated topology warnings retain their existing warning/error treatment; the current network remains valid with zero errors.

No open correctness concerns remain in this fix scope.
