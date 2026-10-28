export const meta = {
  name: 'k8-sa-wip-a8',
  description: 'Implement K8 amendment 8 in SA WIP (posthead (d) rehome shortfall kept as lane-3 head packet, SAG attempted-capture completeness, docs), light; then a focused check',
  phases: [ { title: 'Fix' }, { title: 'Check' } ],
}
const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const WS = 'D:/VISSIM-merge/sim3-n31-k8sa'
const CTX = `CONTEXT (Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line).
SA (K8-6) WIP worktree ${WS}, branch claude/k8-sa-wip-20261004, HEAD 18a951c0. Latest review ${K8}/sawip/REVIEW_r6.md (no blocking). Binding: spec + amendments, now **${K8}/K8_PREDECLARATION_AMENDMENT_8.md (sha 7e4abe34...)** on top of amendment 7.
Another workflow runs heavy K8-4/K8-5 jobs in D:/VISSIM-merge/sim3-n31-k8 — do not touch it.
HARD RULES: LIGHT WORK ONLY (code edits, py_compile, unit tests via ${K8}/impl/run_pytest_bn.py with BELOW_NORMAL/PYTHONHASHSEED=0/python -B/-p no:cacheprovider). No adapter runs, captures, rollouts, harness jobs, gate computations, VISSIM, cscript, forbidden tests. Do not modify frozen/*, other worktrees, D:/VISSIM_runs/*. Keep line endings (git ls-files --eol). Commits only in ${WS}, explicit paths, identity Ming2you <alsrjsrb1915@snu.ac.kr>, prefix "WIP K8-6:", end "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push. Remove __tangentcache__/__pycache__ before committing.`
const R = { type: 'object', properties: { commits: { type: 'string' }, summary: { type: 'string' }, tests: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } }, required: ['commits', 'summary', 'tests', 'open'] }
const REV = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } }, required: ['report_path', 'blocking', 'nonblocking', 'verdict'] }
phase('Fix')
const fix = await agent(`${CTX}\nTASK: implement amendment 8 §1-§3 (rehome (d) shortfall kept as the N-receiving 127 lane head ready packet + init_excess, combined shortfall reporting and ledger term, no projection reservation moved for the kept share; SAG attempted-capture counted as present/reported in G-EB-2 completeness; README D12 + rerun procedure). Add unit tests (toy room 2.0/1.5/1.0/0.5/0.0 all pass with mass preservation and non-negative storage; area-ledger _nonnegative passes). Run all SA unit + harness tests + diagnostics/test_urban_flow_accounting.py; all pass. Commit "WIP K8-6: amendment-8 fixes".`, { label: 'fix a8', phase: 'Fix', schema: R })
phase('Check')
const rev = await agent(`${CTX}\nFix: ${JSON.stringify(fix)}.\nTASK: check amendment 8 implemented as written; BLOCKING only for false-PASS paths, judging-arm violations, or mass/non-negativity violations (amendment 7 §5 scope). Run the unit tests. Write ${K8}/sawip/REVIEW_r8.md. verdict PASS or BLOCKING.`, { label: 'check a8', phase: 'Check', schema: REV })
return { fix, rev }
