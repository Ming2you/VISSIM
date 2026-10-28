export const meta = {
  name: 'k8-sa-wip-fix-r6',
  description: 'Implement K8 amendment 7 in SA WIP (posthead shortfall as head packet, failure classification, instrument validity, small fixes), then one false-PASS-focused review and at most one more fix',
  phases: [ { title: 'Fix' }, { title: 'Review' }, { title: 'Final fix' } ],
}

const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const WS = 'D:/VISSIM-merge/sim3-n31-k8sa'

const CTX = `CONTEXT (Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line).
SA (K8-6) WIP worktree ${WS}, branch claude/k8-sa-wip-20261004, HEAD d217e261. Prior reviews ${K8}/sawip/REVIEW*.md. Binding: OPT1_V2_SPEC.md + OPT1_V2_SPEC_AMENDMENT_1.md (r2), K8_PREDECLARATION.md + AMENDMENT_1 (r2) + _2 .. _6, and **${K8}/K8_PREDECLARATION_AMENDMENT_7.md (sha ad745e9b...; overrides amendment 6 §2; follow exactly)**, K8_USER_DECISIONS_20261004.md.
Another workflow runs heavy K8-4/K8-5 jobs in D:/VISSIM-merge/sim3-n31-k8 — do not touch it.
HARD RULES: LIGHT WORK ONLY (code edits, py_compile, unit tests via ${K8}/impl/run_pytest_bn.py with BELOW_NORMAL/PYTHONHASHSEED=0/python -B/-p no:cacheprovider, --help/--dry-run). NO adapter runs, captures, rollouts, harness jobs, gate computations, VISSIM, cscript; never the forbidden tests (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Do not modify frozen/*, other worktrees, D:/VISSIM_runs/*. Sealed seeds never. Keep each file's line-ending style (git ls-files --eol before/after). Commits only in ${WS}, explicit paths, identity Ming2you <alsrjsrb1915@snu.ac.kr>, prefix "WIP K8-6:", end "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push. Remove __tangentcache__/__pycache__ before committing.`

const R = { type: 'object', properties: { commits: { type: 'string' }, summary: { type: 'string' }, tests: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } }, required: ['commits', 'summary', 'tests', 'open'] }
const REV = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } }, required: ['report_path', 'blocking', 'nonblocking', 'verdict'] }

phase('Fix')
const fix = await agent(`${CTX}
TASK: implement amendment 7 §1-§4 completely: §1 posthead branch (a) shortfall kept as the 127 lane head ready packet (+ init_excess if the lane exceeds its cap), urban storage never negative, mass preserved, shortfall reported, lane-stock identity term N_shortfall_kept in sa_identity/H-2b/T8/probes, unit tests (incl. an area-ledger _nonnegative pass on the toy); §2 unified error classification ('Ledger' -> stocks), SAF FAIL only for runtime-code traceback recorded by the child, infra/harness -> INCOMPLETE, SAG non-invariant failures reported and not blocking G-EB-2 completeness, G-EB-1 either-run-unfinished -> INCOMPLETE, G-EB-11(d) ev_unevaluated>0 -> INCOMPLETE; §3 instrument validity (S3 hook_errors/patch_errors/errors 0, fold hook errors 0, final records, run completeness) for G-EB-11(d) and G-EB-13, positive control BASE full 2700/4950 plant reads > 0 required for G-EB-13; §4 unit_T11 precedence fix, job input forecast_long_len/prefix check. Tests for each. Run all SA unit + harness tests + diagnostics/test_urban_flow_accounting.py; all pass. Commit "WIP K8-6: amendment-7 fixes".`, { label: 'fix a7', phase: 'Fix', schema: R })

phase('Review')
const rev = await agent(`${CTX}
Fix: ${JSON.stringify(fix)}.
TASK: review per amendment 7 §5 scope. BLOCKING only for: (1) any path where a required input is missing/failed/unfinished yet the gate returns PASS or combine returns PROMOTE_ELIGIBLE (false PASS) — probe it; (2) violation of the judging-arm principle (D-K8-1: SAF judges, BASE comparator, SAG report) or of a declared threshold/sample; (3) amendment 7 §1 not implemented as written (mass preservation, non-negative storage, head packet). False STOP/INCOMPLETE issues are NON-blocking (list them). Run the unit tests. Write ${K8}/sawip/REVIEW_r6.md. verdict PASS or BLOCKING.`, { label: 'review a7', phase: 'Review', schema: REV })

let fix2 = null, rev2 = null
if (rev && rev.blocking && rev.blocking.length) {
  phase('Final fix')
  fix2 = await agent(`${CTX}
TASK: fix only these blocking items from ${K8}/sawip/REVIEW_r6.md: ${JSON.stringify(rev.blocking)}. If an item needs a main-session decision, do not decide it; put it in open. Run all tests; commit "WIP K8-6: review-r6 fixes".`, { label: 'final fix', phase: 'Final fix', schema: R })
  rev2 = await agent(`${CTX}
TASK: re-check ONLY these items after the fix: ${JSON.stringify(rev.blocking)} (fix: ${JSON.stringify(fix2)}). Same scope rules as amendment 7 §5. Write ${K8}/sawip/REVIEW_r7.md. verdict PASS or BLOCKING.`, { label: 'final check', phase: 'Final fix', schema: REV })
}
return { fix, rev, fix2, rev2 }
