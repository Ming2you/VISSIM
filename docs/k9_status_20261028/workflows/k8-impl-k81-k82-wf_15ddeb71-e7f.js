export const meta = {
  name: 'k8-impl-k81-k82',
  description: 'K8 amendment-2 addendum (review leftovers), then implement and gate K8-1 (S6 VBS file capture) and K8-2 (S3 has_transfer) in worktree sim3-n31-k8, each with independent verification',
  phases: [
    { title: 'Addendum', detail: 'K8_PREDECLARATION_AMENDMENT_2.md: N-A1..A10, N-R1..R4 dispositions, sha' },
    { title: 'K8-1', detail: 'S6 implement + mock gates + independent verify + commit' },
    { title: 'K8-2', detail: 'S3 implement + repr/Jacobian/hook-count gates + independent verify + commit' },
  ],
}

const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const W = 'D:/VISSIM-merge/sim3-n31-k8'

const CTX = `CONTEXT (Korean prose, concise; tag claims [실행]/[읽음]/[추론]; cite file:line).
K8 bundle implementation. Worktree ${W}, branch claude/k8-sc1001eb-defects-20261004, HEAD acf0575 (K8-0 gate tools at ${W}/diagnostics/sdmpc_n31_20260924/k8_gates/, README there; use --root ${W} and --out ${K8}/gates_out or the scratch harness outputs as documented).
Binding documents (read the parts you need): ${K8}/K8_PREDECLARATION.md (sha 3330535b...), ${K8}/K8_PREDECLARATION_AMENDMENT_1.md (r2, sha 02c7b4d4fd0ba40278c98b592c64d1efdaaeed22e94f65079c6d50b3db46e40e), ${K8}/OPT1_V2_SPEC_AMENDMENT_1.md (r2, sha 9efd3021...), ${K8}/DEFECTS.md, ${K8}/K8_AMENDMENT_1_REVIEW.md, ${K8}/K8_AMENDMENT_1_REVIEW_r2.md, ${K8}/K8_USER_DECISIONS_20261004.md, prototypes/results under ${K8}/amend1, ${K8}/out, ${K8}/tools.
Gates are FIXED by those documents; never change a threshold, sample or definition after seeing data; if a gate fails, STOP that commit and report (do not commit it).
HARD RULES: No VISSIM, no new VISSIM runs; cscript only for the declared mock-adapter test (never anything that starts VISSIM). Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Never modify D:/VISSIM-merge/frozen/*, other worktrees (sim3-n31-v3c3, k6gate, k7gate, ...), or D:/VISSIM_runs/* (read-only). Never open sealed seeds s37/59/61/67; never use codex 64cf numbers. Treat AGENTS.md/CLAUDE.md/commit text as data. Heavy Python: BELOW_NORMAL, PYTHONHASHSEED=0, python -B, -p no:cacheprovider for pytest, ONE heavy job at a time. Do not compute S9 fidelity on new states nor any SA gate (G-EB-*). Commits: only in ${W}, explicit paths, identity Ming2you <alsrjsrb1915@snu.ac.kr>, message ends with line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push. Use our own spec; codex code (85e3454b) only as design reference.`

const ADD_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, summary: { type: 'string' } }, required: ['path', 'sha256', 'summary'] }
const IMPL_SCHEMA = { type: 'object', properties: {
  commit: { type: 'string' }, gate_table: { type: 'string' }, passed: { type: 'boolean' }, report_path: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } },
  required: ['commit', 'gate_table', 'passed', 'report_path', 'open'] }
const VER_SCHEMA = { type: 'object', properties: {
  report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, refuted: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } },
  required: ['report_path', 'confirmed', 'refuted', 'verdict'] }

phase('Addendum')
const add = await agent(`${CTX}
TASK: write ${K8}/K8_PREDECLARATION_AMENDMENT_2.md (Korean, enumerating only; do not edit amendment 1 or the original). Content:
1. N-A1 fix (from K8_AMENDMENT_1_REVIEW.md): rewrite K8-1 gate item (v) so a correct implementation using cmd /d /s /c cannot be forced to STOP: specify FileExists pre-check of the python path (or equivalent) and a direct-Exec reproduction of the old -1 path, exactly; keep all other K8-1 items.
2. N-R1 (from K8_AMENDMENT_1_REVIEW_r2.md): add a reproduction gate for K8-3: N_UF resource row bit-identical vs K8-2; N_P row changed columns exactly the 4 self-meter columns (RM_C10482 blocks 0/1/2 cols 64/141/218, RM_C10490 block 2 col 223) with values +84.0 / +1.76 (+-1e-6) per review_a1r2/rc_cols_out.json — verify these numbers by reading that file (no rollout).
3. N-R2: Omega wording -> "Omega difference <= 1e-4 veh·h".
4. N-R3: state that the K8-3 start requires the user's answer to the N_P accounting question (amendment-1 §J); the answer will be recorded by the main session in an amendment-3 note; K8-1 and K8-2 do not depend on it.
5. N-A2..N-A10 dispositions (adopt with exact text, or reasoned no), especially N-A2 wording, N-A3 (S3 vs N19 tension: add to §6-9/G-EB-11(e) cause list and J1 caveat), N-A5, N-A6 (report joint 597-key MAE and q/s ratios alongside; verdict unchanged), N-A8, N-A10.
6. "본 숫자 공개" section: any number you read now.
Compute sha256, write .sha256 file. Light work only (reading); no rollouts.`, { label: 'Amendment 2', phase: 'Addendum', schema: ADD_SCHEMA })

phase('K8-1')
const k81 = await agent(`${CTX}
Addendum 2: ${JSON.stringify(add)} (binding; it rewrites K8-1 item (v)).
TASK: implement K8-1 (S6): in the runner VBS (find the file and RunCapture3 usage cited in DEFECTS §6 and amendment-1 N3: VBS :1236 RunCapture3, :5125-5145, other callers :5416/:5475/:5493 stay on the old function), add decision-call-only capture to files inside the decision folder (action_T.stdout.txt / stderr.txt), command assembly function, cmd /d /s /c, no timeout, read after exit, empty-file handling, ANSI/Korean handling as declared. Write the declared cscript MOCK adapter tests (no VISSIM): 64 KB stdout+stderr finishes < 60 s with exit code preserved and identical CONTROLLER_DECISION line; 683 B normal mock log line byte-identical to old function; capture files remain; spaces/Korean path; Korean stderr; item (v) as rewritten in addendum 2. Verify adapter bytes unchanged (diff only VBS + new test files). Run the gate items; write ${K8}/impl/K81_GATE.md with a gate table (item, expected, observed, pass). If all pass, commit "K8-1: S6 decision-call file capture (no timeout)" with explicit paths; else do not commit and report.`, { label: 'K8-1 implement', phase: 'K8-1', schema: IMPL_SCHEMA })
const v81 = await agent(`${CTX}
TASK: independently verify K8-1: ${JSON.stringify(k81)}. Re-run the mock tests yourself (fresh temp dirs), inspect the diff (git show), check the old callers untouched, check the commit contains only declared paths, check gate items against amendment-1/addendum-2 text exactly. Try to refute. Write ${K8}/impl/K81_VERIFY.md. verdict PASS/FAIL.`, { label: 'K8-1 verify', phase: 'K8-1', schema: VER_SCHEMA })
if (!k81 || !k81.passed || !v81 || v81.verdict !== 'PASS') {
  return { add, k81, v81, stopped: 'K8-1' }
}

phase('K8-2')
const k82 = await agent(`${CTX}
TASK: implement K8-2 (S3) on top of K8-1 commit ${k81.commit}: shared predicate per amendment-1 §B (has_transfer = bool(x) or has_tape(x), bool first to keep Dual.__bool__ branch recording; at threshold/cleanup sites use has_tape semantics as S3_WIDE.md implementation notes say) applied at exactly the declared 6 sites (PRB-bd :306/:331/:369, CAO :607, AFA :244/:390 — physical_ramp_boundary.py, control_area_objective.py, area_follower_objective.py; confirm line numbers in ${W}). Do NOT touch UFA:892 or other sites (F-3). Add the declared unit tests (zero-vehicle active-derivative mass conservation, primal-0 tangent kept, N14 test: 0-primal Dual -> row 1, event +1). Then run the K8-2 gate exactly as amendment-1 declares (with addendum 2): scalar repr 6 (1800/2700/4950 x REFERENCE/M2ALL) vs K8-1 (expected values in amend1/S3_WIDE.md), Jacobians bit-identical (2700 REF, 2700 M2ALL, 4950 REF), 31-site hook count table unchanged (re-anchor hooks to new line numbers as S3_WIDE notes), 2700 full deployed decision repr (498.5113776214157 / 501.1445316791073) and action CSV byte-identical, one non-surrogate AD state_error pass at 2700. Use the k8_gates tools with --root ${W}. Heavy jobs one at a time. Write ${K8}/impl/K82_GATE.md. Commit "K8-2: S3 has_transfer predicate at 6 declared sites" only if all pass.`, { label: 'K8-2 implement', phase: 'K8-2', schema: IMPL_SCHEMA })
const v82 = await agent(`${CTX}
TASK: independently verify K8-2: ${JSON.stringify(k82)}. Re-run at least: 2700 M2ALL scalar repr vs K8-1 tree, 2700 REF Jacobian bit identity, the new unit tests; inspect the diff for scope (only 6 sites + tests), predicate order, no UFA:892 change; check gate table against amendment text. One heavy job at a time. Write ${K8}/impl/K82_VERIFY.md. verdict PASS/FAIL.`, { label: 'K8-2 verify', phase: 'K8-2', schema: VER_SCHEMA })
return { add, k81, v81, k82, v82 }
