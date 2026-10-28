export const meta = {
  name: 'v3c3-k7-amend-freeze-push',
  description: 'K7 continuation: amendment (O-3 keep v3c1 unsignalized list per user, O-5 value-level criterion, O-7 doc, O-8 stray pyc), fix commit, re-run affected offline gates, freeze/preflight, push, launch lines, independent verification',
  phases: [
    { title: 'Amend+fix' },
    { title: 'Regate' },
    { title: 'Freeze+push' },
    { title: 'Verify' },
  ],
}

const R3 = 'D:/VISSIM_runs/20261001_v3c3'
const OUT = R3 + '/reports/k7'
const W = 'D:/VISSIM-merge/sim3-n31-v3c3'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- K7 state: W = ${W} (branch claude/repin-v3c3-20261001, K7 head 99dc641, 5 local K7 commits on K6 54d821c, not pushed). Reports ${OUT}: K7_GB_J1_PREDECLARATION.md (sha fad31d70), K7_IMPLEMENT.md, K7_OFFLINE_GATES.md (stopped by O-9). Gate worktree GWT7 = D:/VISSIM-merge/sim3-n31-v3c3-k7gate (detached at 99dc641); K6 gate worktree GWT6 = D:/VISSIM-merge/sim3-n31-v3c3-k6gate.
- Offline-gate failures and the USER DECISION (2026-10-01 17:3x):
  * O-3 (DA-2 unsignalized_turns list 23 -> 22 because SC103_S_SC6_to_E stop ratio 0.0472 -> 0.0544 > 0.05 on v3c3 data): USER CHOSE TO KEEP THE OLD v3c1 LIST (23 entries) - pin the membership to the v3c1 list (validation numbers may be recomputed on v3c3 and reported, but membership stays the v3c1 23; record SC103_S_SC6_to_E's v3c3 ratio as a known exceedance). The deployed tuning does not read this table (U3 candidate only).
  * O-5 condition 4 (exact tangent op-count delta n x 38): amend to a value-level criterion: primal bit-identical, FW_W tangent columns/trace identical, event counts identical, FW_E derivative ratio kappa = 1.1924542785990433 within relative 1e-9 (observed <= 2.3e-13); record the observed op-count deltas and the zero-cancellation explanation.
  * O-7: fill the missing grep counts in REPIN_V3C3_REPORT.md section 5.
  * O-8: the stray ignored file GWT6/__pycache__/control_area_objective.cpython-312.pyc (17:04:51) - record its sha and probable source (another read-only workflow importing from GWT6 without -B), then delete it; GWT6 must return to 0 lines with --ignored.
- Pending outside this workflow: v3c3 NC s53 and sealed s37 were relaunched at 16:20 after an unexplained runner interruption (GB-1 amendment reports/gb1_amendment_1.md); the main session judges GB-1 when they complete. O-0 allows the v3c2 s53 substitute with a byte check later.
- Launcher seat rule: at most 2 concurrent dev runs (run_sdmpc_n31.ps1:84-87) -> J1 baseline seeds s31,s41 first, s43 after a seat frees. VISSIM total <= 4: the two NC reruns occupy 2 seats until ~18:00.
- HARD RULES: commits only in W with explicit paths, identity GIT_AUTHOR_NAME=GIT_COMMITTER_NAME=Ming2you, GIT_AUTHOR_EMAIL=GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr, message ending "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; no --renormalize; push only after all (amended) offline gates pass: git push -u origin claude/repin-v3c3-20261001 (user-approved). Never modify existing D:/VISSIM-merge/frozen/* (new freezes via run_sdmpc_n31.ps1 -Freeze -PreflightOnly are fine). Do not touch other worktrees (sim3-n31-v3c1, -urban-b2, -f10f11, -termcost, -hybrid). No VISSIM start/kill. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results. Python with -B / PYTHONDONTWRITEBYTECODE=1 in gate trees; BELOW_NORMAL.
`
const S1 = { type: 'object', properties: { report_path: { type: 'string' }, amendment_sha: { type: 'string' }, commit: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'amendment_sha', 'commit', 'stop', 'stop_reason'] }
const S2 = { type: 'object', properties: { report_path: { type: 'string' }, gates: { type: 'string' }, all_pass: { type: 'boolean' } }, required: ['report_path', 'gates', 'all_pass'] }
const S3 = { type: 'object', properties: { report_path: { type: 'string' }, frz: { type: 'string' }, pushed: { type: 'string' }, launch_lines: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'frz', 'pushed', 'launch_lines', 'stop', 'stop_reason'] }
const S4 = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Amend+fix')
const a = await agent(CTX + `
YOUR STAGE: write ${OUT}/K7_AMENDMENT_1.md (+ .sha256) BEFORE any re-run, stating each item above, that O-3/O-5 changes are post-result decisions (O-3 by the user), and the exact new criteria. Then make the O-3 fix as a separate commit in W (keep v3c1 membership; regenerate/derive so the generator --check chain stays consistent; adjust tests that pin the list), fix the O-7 report, handle O-8. Write ${OUT}/K7_FIX.md.`, { label: 'amend-fix', phase: 'Amend+fix', schema: S1 })
if (!a || a.stop) { return { a, stopped: 'amend/fix stopped' } }

phase('Regate')
const g = await agent(CTX + `
YOUR STAGE: re-run the offline gates affected by the fix and the amendment from a fresh detached gate worktree at the new head (recreate or re-point GWT7 to ${a.commit}; never run gates in W): O-1 (suites incl. any changed tests), O-2 generator/repin/configure chain, O-3 (paths + content, with O-3 per amendment), O-5 under the amended criterion (reuse the 4 v3c1 R-obs states), O-7, O-8; confirm the other gates are unaffected (diff since 99dc641 touches only the declared files). Write ${OUT}/K7_REGATE.md; all_pass=false if anything fails.`, { label: 'regate', phase: 'Regate', schema: S2 })
if (!g || !g.all_pass) { return { a, g, stopped: 'regate not all pass' } }

phase('Freeze+push')
const f = await agent(CTX + `
YOUR STAGE: FREEZE + PREFLIGHT + PUSH + LAUNCH LINES exactly as the original K7 plan stage (see K7_GB_J1_PREDECLARATION.md GB-4/GB-5 and J1 section): run_sdmpc_n31.ps1 -Freeze -PreflightOnly from W for R-obs sdmpc31_v3c3_nc_s31 (RunsRoot D:\\VISSIM_runs\\20261001_sdmpc31_v3c3, 9000 s, seed 31, no-control obs150) and preflight-only for J1 runs sdmpc31_v3c3_j1_s31 / _s41 / _s43 (wu-link, PYTHONHASHSEED=0 set inside the WMI command line); verify FREEZE_VERIFIED, LAUNCH_PLAN_OK, PROVENANCE_OK, FRZ tuning shas == W; git push -u origin claude/repin-v3c3-20261001 and report the remote head; write exact WMI commands to ${R3}/launch_lines_k7.txt: group 1 = R-obs + RM s31 + RM s41 + RM s37 (sealed) (needs 4 free seats; the NC reruns hold 2 until ~18:00), group 2 (after GB-6/GB-7 pass) = J1 s31 + s41, group 3 = J1 s43 when a dev seat frees. Do NOT launch. Write ${OUT}/K7_FREEZE_PUSH.md.`, { label: 'freeze-push', phase: 'Freeze+push', schema: S3 })

phase('Verify')
const v = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only; own code under ${OUT}/verify2; write ${OUT}/VERIFY2.md). Inputs: K7_AMENDMENT_1.md, ${a.report_path}, ${g.report_path}, ${f ? f.report_path : '(freeze/push failed)'}. Check: amendment precedes re-runs; O-3 membership equals the v3c1 list; O-5 amended values; FRZ contents == pushed remote head; launch lines (cwd = new FRZ for SDMPC runs, PYTHONHASHSEED=0 for J1, names, logs, seat groups, RM runner like v3c1); the full K7 diff covers the repin inventory (grep for leftover v3c1 network shas / paths / 110-only assumptions).`, { label: 'verify', phase: 'Verify', schema: S4 })

return { a, g, f, v }
