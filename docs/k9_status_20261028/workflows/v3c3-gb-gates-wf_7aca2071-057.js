export const meta = {
  name: 'v3c3-gb-gates',
  description: 'Run the predeclared run-side GB gates (GB-5..GB-10, standing S) on R-obs v3c3 s31, then independent verification; decide whether J1 group 2 may launch',
  phases: [
    { title: 'Gates' },
    { title: 'Verify' },
  ],
}

const R3 = 'D:/VISSIM_runs/20261001_v3c3'
const OUT = R3 + '/reports/gb'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- v3c3 repin pushed: origin/claude/repin-v3c3-20261001 = 6c4c740; FRZ_K7 = D:/VISSIM-merge/frozen/sdmpc31_6c4c7400_202610011831; predeclaration ${R3}/reports/k7/K7_GB_J1_PREDECLARATION.md (sha fad31d70) + amendment K7_AMENDMENT_1.md (1b1d3955; O-5 value-level criterion also governs GB-8) + decision note K7_AMENDMENT_1_DECISION_NOTE.md. Gate worktree GWT7 = D:/VISSIM-merge/sim3-n31-v3c3-k7gate (detached at 6c4c740, 0 lines).
- Runs finished 2026-10-01: R-obs3 D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31 (EXIT 0, 61 decisions, DECISIONS_FAILED=0, wall 6,993 s); NC v3c3 fit seeds ${R3}/s{31,41,43,47,53}_v3c3nc (GB-1 PASS 6/6, reports/gb1_verdict.json); RM arms ${R3}/s31_v3c3rm, s41_v3c3rm (fit) and s37_v3c3rm (SEALED: read only run.json completed/exit_code; never open its results). GB-13 (RM) is report-only and the predeclaration says the v3c1 RM/NC prefix check must come BEFORE opening any v3c3 RM result - do not open v3c3 RM results in this workflow.
- TASK: run GB-5, GB-6 (R-obs3 vs NC3 s31 FZP pair excluding the 0.10 s frame; payload must equal 8be8b274...), GB-7 (T5: 61/61 decision replays IDENTICAL, hash seed x3 as declared), GB-8 (L2 all-110 identity on v3c3 states 900/2700/4800/6300 under the amended criterion), GB-9 (7 SDMPC counterfactual decisions: block-0 VSL allowed {80..110}, CSV written {81,91,101,110}, determinism), GB-10 (force a <110 write inside a replay and check the CSV/runner path), and the standing gate S (DECISIONS_FAILED=0, ERROR= absent, J1-A run validity checks where applicable) exactly as predeclared. Replays from GWT7 or FRZ_K7 only (never a working tree that is being edited), one at a time, BELOW_NORMAL, python -B. Volatile-field regex applied to leaf keys only (VERIFY P3).
- HARD RULES: read-only on run folders; write only under ${OUT} (and harness scratch inside it). No commits, no pushes, no VISSIM start/kill, never modify D:/VISSIM-merge/frozen/*. Do not touch other worktrees (sim3-n31-v3c3 W, -urban-b2, -f10f11, -termcost, -hybrid, -k6gate). Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results.
`
const G = { type: 'object', properties: { report_path: { type: 'string' }, gates: { type: 'string' }, all_pass: { type: 'boolean' }, j1_go: { type: 'boolean' } }, required: ['report_path', 'gates', 'all_pass', 'j1_go'] }
const V = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Gates')
const g = await agent(CTX + `YOUR STAGE: run the gates and write ${OUT}/GB_RESULTS.md with a per-gate verdict table and j1_go = (all GB-4..GB-10 and S pass per the predeclaration section 3.2).`, { label: 'gb-gates', phase: 'Gates', schema: G })

phase('Verify')
const v = await agent(CTX + `YOUR STAGE: INDEPENDENT VERIFICATION (own code under ${OUT}/verify; write ${OUT}/VERIFY.md). Input: ${g ? g.report_path : '(gates failed)'}. Re-run GB-6 yourself, one GB-7 replay, one GB-8 state and one GB-9 decision from FRZ_K7/GWT7; check that every verdict follows the predeclaration/amendment and that no sealed or RM result was opened.`, { label: 'gb-verify', phase: 'Verify', schema: V })

return { g, v }
