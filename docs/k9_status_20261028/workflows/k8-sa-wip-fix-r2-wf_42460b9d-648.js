export const meta = {
  name: 'k8-sa-wip-fix-r2',
  description: 'Fix SA WIP re-review blockers B-r2-1/2 and N-r2-1..5 per K8 amendment 6 (light), then loop adversarial review/fix until no blocking (max 3 rounds)',
  phases: [ { title: 'Fix' }, { title: 'Review' } ],
}

const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const WS = 'D:/VISSIM-merge/sim3-n31-k8sa'

const CTX = `CONTEXT (Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line).
SA (K8-6) WIP worktree ${WS}, branch claude/k8-sa-wip-20261004, HEAD 0f338c6e. Reviews: ${K8}/sawip/REVIEW.md, ${K8}/sawip/REVIEW_r2.md. Binding: OPT1_V2_SPEC.md + OPT1_V2_SPEC_AMENDMENT_1.md (r2), K8_PREDECLARATION.md + AMENDMENT_1 (r2) + _2 .. _5, and **${K8}/K8_PREDECLARATION_AMENDMENT_6.md (sha c2664e46...; follow exactly)**, K8_USER_DECISIONS_20261004.md.
Another workflow runs heavy K8-3..K8-5 jobs in D:/VISSIM-merge/sim3-n31-k8 — do not touch it.
HARD RULES: LIGHT WORK ONLY (code edits, py_compile, unit tests via ${K8}/impl/run_pytest_bn.py with BELOW_NORMAL/PYTHONHASHSEED=0/python -B/-p no:cacheprovider, --help/--dry-run). NO adapter runs, captures, rollouts, harness jobs, gate computations, VISSIM, cscript; never the forbidden tests (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Do not modify frozen/*, other worktrees, D:/VISSIM_runs/*. Sealed seeds never. Keep each file's existing line-ending style (check git ls-files --eol before/after). Commits only in ${WS}, explicit paths, identity Ming2you <alsrjsrb1915@snu.ac.kr>, prefix "WIP K8-6:", end "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push. Remove __tangentcache__/__pycache__ before committing.`

const R = { type: 'object', properties: { commits: { type: 'string' }, summary: { type: 'string' }, tests: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } }, required: ['commits', 'summary', 'tests', 'open'] }
const REV = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } }, required: ['report_path', 'blocking', 'nonblocking', 'verdict'] }

const rounds = []
let todo = 'Implement amendment 6 §1-§3 completely (unit-log parsing rules with real pytest 9.1.1 output tests, missing line => INCOMPLETE, T9b/T9c assertions out of subTest, multi --unit-log or single combined -v run + README, captured-test provenance (capture root/tree/template sha256) cross-checked by sa_gates, posthead branch (a): no clipping subtraction + mass preservation + shortfall report + updated unit test, G-EB-13 judged job TL3 2700 SAF hook (+ all present), G-EB-2 declared job list completeness, G-EB-5 step completeness/monotonic/recorder_errors).'
for (let i = 1; i <= 3; i++) {
  phase('Fix')
  const fix = await agent(`${CTX}\nROUND ${i}. TASK: ${todo}\nRun all SA unit + harness tests + diagnostics/test_urban_flow_accounting.py; all must pass. Commit "WIP K8-6: amendment-6 fixes (round ${i})".`, { label: `fix r${i}`, phase: 'Fix', schema: R })
  phase('Review')
  const rev = await agent(`${CTX}\nFix round ${i}: ${JSON.stringify(fix)}.\nTASK: adversarial review of the WIP branch against amendment 6 (and 5) item by item, plus a fresh look for any gate path that can return PASS with missing/failed inputs, or STOP when inputs are merely missing, or that contradicts D-K8-1 (SAF judging only). Run the unit tests. Write ${K8}/sawip/REVIEW_r${i + 2}.md. verdict PASS or BLOCKING.`, { label: `review r${i}`, phase: 'Review', schema: REV })
  rounds.push({ fix, rev })
  if (!rev || !rev.blocking || rev.blocking.length === 0) break
  todo = `Fix these review blockers (from ${K8}/sawip/REVIEW_r${i + 2}.md) without weakening any amendment rule: ${JSON.stringify(rev.blocking)}. If a blocker needs a main-session/user decision rather than code, do not decide it: report it in open.`
}
return rounds
