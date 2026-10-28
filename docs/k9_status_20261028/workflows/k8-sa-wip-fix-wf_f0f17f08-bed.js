export const meta = {
  name: 'k8-sa-wip-fix',
  description: 'Fix SA WIP review blockers B-1..B-5 and adopted N-items per K8 amendment 5 in worktree sim3-n31-k8sa (light work only), then adversarial re-review',
  phases: [ { title: 'Fix' }, { title: 'Re-review' } ],
}

const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const WS = 'D:/VISSIM-merge/sim3-n31-k8sa'

const CTX = `CONTEXT (Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line).
SA (K8-6, SC1001 EB option-1 v2 lane FIFO) WIP worktree ${WS}, branch claude/k8-sa-wip-20261004, HEAD 2929816 (commits 983360b core, 4780b57 wiring/config/evidence, 2929816 gate harness code). Review with blockers: ${K8}/sawip/REVIEW.md. Plan: ${K8}/sawip/PLAN.md. Binding: OPT1_V2_SPEC.md + OPT1_V2_SPEC_AMENDMENT_1.md (r2), K8_PREDECLARATION.md + AMENDMENT_1 (r2) + _2 + _3 + _4 + **${K8}/K8_PREDECLARATION_AMENDMENT_5.md (sha 342e6d62...; main-session decisions on B-1..B-5, the 13 operationalisations, N-items — follow it exactly)**, K8_USER_DECISIONS_20261004.md.
Another workflow is running heavy K8-3..K8-5 gate jobs in D:/VISSIM-merge/sim3-n31-k8 — do not touch that worktree.
HARD RULES: LIGHT WORK ONLY: code edits, py_compile, unit tests via ${K8}/impl/run_pytest_bn.py (BELOW_NORMAL, PYTHONHASHSEED=0, python -B, -p no:cacheprovider), --help/--dry-run. NO adapter runs, NO captures, NO rollouts, NO harness jobs, NO gate computations, NO VISSIM, NO cscript, never the forbidden tests (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Do not modify frozen/*, other worktrees, D:/VISSIM_runs/*. Sealed seeds s37/59/61/67 never. Commits only in ${WS}, explicit paths, identity Ming2you <alsrjsrb1915@snu.ac.kr>, message prefix "WIP K8-6:", ends "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push. Remove __tangentcache__/__pycache__ created by tests before committing.`

const R = { type: 'object', properties: { commits: { type: 'string' }, summary: { type: 'string' }, tests: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } }, required: ['commits', 'summary', 'tests', 'open'] }
const REV = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } }, required: ['report_path', 'blocking', 'nonblocking', 'verdict'] }

phase('Fix')
const fix = await agent(`${CTX}
TASK: implement amendment 5 in the WIP branch:
§1 judging-arm principle in sa_gates.py (G-EB-* judged on SAF only; BASE comparator only; SAG report only; G-EB-2 counts all keyed arms; G-EB-6(a) judged on SAF requiring all 45 H3 + 14 H6 else INCOMPLETE; completeness checks per judging arm everywhere), restrict SAG jobs in sa_jobs.py to FH event-14 H6 and TL3 9 H3 OBS.
§2 OPERATIONALISATIONS: update constants text for item 4 (G-EB-5 both sides cut at 8970.1 — implement in sa_gates/sa_worker as needed), item 2 strict (d), item 10 p4 "no axis" note; add unit tests for the 8970.1 tail rule.
§3 lane-stock ledger identity: update H-2b (sa_smoke), T8 (test_stopline_approach), capture probe (sa_cap_child records N_127, N_10777, |A|, N_tail129, M_other separately) to the corrected identity; document T8 case.
§4 G-EB-14 reads T9b/T9c from unit logs (>=1 PASSED, 0 SKIPPED else INCOMPLETE); add diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach_captured.py with T3-N7, T6b, T8b, T9b, T9c, T15b written against captured states (skip with explicit reason when captures absent; they run in the gate phase); G-EB-13 requires TL3 hook job.
§6 N-1 (I11 two-sided), N-2 (follow spec: no StoplineInitError in branch (a); reject only in (d)), N-3 (deviation note + new kind into GB-7' A_K8 list file if it exists in k8_gates, else document), N-4 (pass spec/receiving_key so key-absent path does no new work; keep bit identity tests), N-8 (reject origin_binding on in install_check), N-11, N-13; copy sha-pinned evidence inputs into diagnostics/sdmpc_n31_20260924/stopline/inputs/ and make the builder default to them (verify sha and --check bit-identical output).
Run all SA unit tests + harness tests + test_urban_flow_accounting.py; all must pass. Commit as one or a few "WIP K8-6: amendment-5 fixes ..." commits. Report what changed per item.`, { label: 'SA WIP fixes', phase: 'Fix', schema: R })

phase('Re-review')
const rev = await agent(`${CTX}
Fix result: ${JSON.stringify(fix)}.
TASK: adversarial re-review of the fixes against amendment 5 item by item and against REVIEW.md B-1..B-5 (git diff 2929816..HEAD in ${WS}). Also re-check: key-absent bit identity tests still pass and still compare against the right base; no gate logic can return PASS with missing judging-arm jobs; corrected ledger identity matches spec §5.8-5/-6 code. Run the unit tests (light). Write ${K8}/sawip/REVIEW_r2.md. verdict PASS or BLOCKING.`, { label: 'SA WIP re-review', phase: 'Re-review', schema: REV })
return { fix, rev }
