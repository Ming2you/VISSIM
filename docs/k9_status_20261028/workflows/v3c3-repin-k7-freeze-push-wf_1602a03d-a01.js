export const meta = {
  name: 'v3c3-repin-k7-freeze-push',
  description: 'K7: repin to network v3c3 + single-value VSL activation (L2, CSV map, runner allow-list), regenerate derived evidence, offline gates, freeze/preflight, push, prepare R-obs/RM/J1-baseline launch lines and GB/J1 predeclarations',
  phases: [
    { title: 'Predeclare' },
    { title: 'Implement' },
    { title: 'Offline gates' },
    { title: 'Freeze+push' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const PLAN = 'D:/VISSIM_runs/20260930_v3c2/reports/repin'
const R3 = 'D:/VISSIM_runs/20261001_v3c3'
const OUT = R3 + '/reports/k7'
const W = 'D:/VISSIM-merge/sim3-n31-v3c3'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER-APPROVED repin plan ${PLAN}/REPIN_V3C2_PLAN.md (d4b70c02) + inventory repin_v3c2_inventory.json + review REPIN_V3C2_PLAN_REVIEW.md, all recommended U1-U12 (push, freeze and launches included). K1-K6 are DONE and gated: W = ${W} branch claude/repin-v3c3-20261001 HEAD 54d821c (K6), reports ${R3}/reports/k1k6 (K1K6_IMPLEMENT.md, GA_RESULTS.md all pass, VERIFY.md problems P1-P8: carry P3 'apply the time regex to leaf keys only', P6 'K4/K5 active paths still unexercised -> must be exercised in GB-8..10', P2 min_green<=0 refusal noted). K6 gate worktree D:/VISSIM-merge/sim3-n31-v3c3-k6gate (detached, leave it).
- Network v3c3 = v3c2 + DSD 81/91/101 (${R3}/reports/V3C3_BUILD.md, receipt v3c3_edit_receipt.json, per-seed shas s31 3de889f0..., s41 726af589..., s43 51478c39..., s47 1895ca30..., s53 095fb701..., s37 7edf0f7a... sealed). NC fit seeds in ${R3}/s<seed>_v3c3nc/run: s31/41/43/47 done and GB-1 PASS (FZP payload byte-identical to v3c2); s53 + sealed s37 finishing ~13:45 (if a derivation needs s53, wait for ${R3}/s53_v3c3nc/run/run.json completed true, or use the byte-identical v3c2 s53 payload and say so).
- USER DECISION (10-01): the 9000 s closed loop runs with VSL ACTIVE using single-value DSDs + plant law L2 (not V0). This K7 must therefore activate: runner allow-list 81,91,101,110 (V-6), the CSV command->distribution map (K5) and the L2 speed_scale (K4) in the deployed SDMPC tuning, the generator family option for L1 (V-11, U5-a), plus all repin items of the inventory (network sha constants, repin_scenario_v2 enumerations incl. vehicleCompositions/vehComp/DSD blocks with the CHANGE_RULES 'added' narrowed per review N8, β sources routing_v3c3, ramp arrival forecast re-derivation on v3c3 fit seeds, obs150 detector build sha, control_area_membership drift handling, docstrings/tests listed in review N11).
- HARD RULES: commits only in W with explicit paths, identity GIT_AUTHOR_NAME=GIT_COMMITTER_NAME=Ming2you, GIT_AUTHOR_EMAIL=GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr, message ending "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; no --renormalize; PUSH only in the Freeze+push stage after all offline gates pass (git push -u origin claude/repin-v3c3-20261001). Never modify existing D:/VISSIM-merge/frozen/* (new freezes via run_sdmpc_n31.ps1 -Freeze -PreflightOnly are fine). Do not touch other worktrees (sim3-n31-v3c1, -urban-b2, -f10f11, -termcost, -hybrid, -k6gate). No VISSIM start/kill (the main session launches). Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results. Replays one at a time, BELOW_NORMAL.
`
const S1 = { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, summary: { type: 'string' } }, required: ['path', 'sha256', 'summary'] }
const S2 = { type: 'object', properties: { report_path: { type: 'string' }, commits: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'commits', 'stop', 'stop_reason'] }
const S3 = { type: 'object', properties: { report_path: { type: 'string' }, gates: { type: 'string' }, all_pass: { type: 'boolean' } }, required: ['report_path', 'gates', 'all_pass'] }
const S4 = { type: 'object', properties: { report_path: { type: 'string' }, frz: { type: 'string' }, pushed: { type: 'string' }, launch_lines: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'frz', 'pushed', 'launch_lines', 'stop', 'stop_reason'] }
const S5 = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Predeclare')
const pre = await agent(CTX + `
YOUR STAGE: PREDECLARE (no code). Write ${OUT}/K7_GB_J1_PREDECLARATION.md (+ .sha256) containing: (1) K7 offline gates (unit/T9/tools/obs150/repin pytest suites vs baseline failure sets; make_config_n31 --check; family consistency check; L2 at all-110 plant identity on >= 4 v3c1 R-obs states (speed_scale at 110 = 1, predictions and tangent op counts identical to key-absent); an offline <110 write-path test (forced VSL command 80/90/100 -> CSV 81/91/101 accepted by the runner allow-list, strict map, no 120 extension) ; (2) the run-side GB gates GB-6 (R-obs v3c3 FZP vs NC v3c3 s31 pair, 0.10 s frame excluded), GB-7 (T5 61 decision replays of R-obs v3c3 IDENTICAL), GB-8 (L2 all-110 identity on R-obs v3c3 states), GB-9 (counterfactual SDMPC decisions), GB-10 (<110 write path in a replay), standing gate DECISIONS_FAILED=0 / ERROR=0; RM arm identity rule as in review N10 (report-only unless proven); (3) the J1 BASELINE closed loop: seeds (choose 3 fit seeds and justify; never sealed seeds), PYTHONHASHSEED=0, tuning = deployed v3c3 SDMPC with single-value VSL + L2 active, and its U9-a audit: every VSL write < 110 reaches VISSIM as DSD 81/91/101 (action CSV vs VBS readback vs vsl_readback.csv), DECISIONS_FAILED=0, per-decision VSL choice statistics; analysis = paired vs v3c3 NC same seed on the four metrics (fw_e_main, east local 19, Omega + urban, all + uninserted) with J1 caveats; state explicitly that the SC1001 EB off-ramp drain defect (10491/10481 at 219 veh/h) is still present so this is a BASELINE, not a controller verdict.`, { label: 'predeclare', phase: 'Predeclare', schema: S1 })
if (!pre) { return { stopped: 'predeclaration failed' } }

phase('Implement')
const im = await agent(CTX + `
YOUR STAGE: IMPLEMENT K7 in W on top of 54d821c (separate commits per logical item), following the plan/inventory and the predeclaration ${pre.path}. Regenerate the derived evidence on v3c3 fit seeds with the generators (record input shas). Produce the deployed SDMPC tuning(s) for R-obs (no-control + obs150) and for the J1 baseline (VSL single-value + L2 active), and the RM arm preparations like D:/VISSIM_runs/20260927_v3c1/rm_build (s31, s41, sealed s37). Write ${OUT}/K7_IMPLEMENT.md. stop=true if any inventory item cannot be completed safely.`, { label: 'implement-k7', phase: 'Implement', schema: S2 })
if (!im || im.stop) { return { pre, im, stopped: 'K7 implementation stopped' } }

phase('Offline gates')
const og = await agent(CTX + `
YOUR STAGE: RUN THE K7 OFFLINE GATES exactly as predeclared (${pre.path}, verify sha). Commits: ${im.commits}. Use a detached gate worktree at the K7 head (git worktree add --detach D:/VISSIM-merge/sim3-n31-v3c3-k7gate <head>) for replays, never W. Write ${OUT}/K7_OFFLINE_GATES.md with a per-gate table; all_pass=false if any fails (do not fix silently).`, { label: 'offline-gates', phase: 'Offline gates', schema: S3 })
if (!og || !og.all_pass) { return { pre, im, og, stopped: 'offline gates not all pass' } }

phase('Freeze+push')
const fp = await agent(CTX + `
YOUR STAGE: FREEZE + PREFLIGHT + PUSH + LAUNCH LINES. (1) run_sdmpc_n31.ps1 -Freeze -PreflightOnly from W for the R-obs run (name sdmpc31_v3c3_nc_s31, RunsRoot D:\\VISSIM_runs\\20261001_sdmpc31_v3c3, 9000 s, seed 31, no-control obs150 as for v3c1 R-obs) and preflight-only for the J1 baseline runs (names sdmpc31_v3c3_j1base_s<seed>, same RunsRoot, wu-link, PYTHONHASHSEED=0 inside the WMI command line); confirm FREEZE_VERIFIED, LAUNCH_PLAN_OK, PROVENANCE_OK, tuning shas inside the FRZ == W. (2) git push -u origin claude/repin-v3c3-20261001 (explicitly approved by the user) and report the remote head. (3) Write exact WMI launch commands (Invoke-CimMethod Win32_Process Create; CurrentDirectory = new FRZ for SDMPC runs; the RM arms with their own runner like v3c1) to ${R3}/launch_lines_k7.txt in the order: R-obs + RM s31 + RM s41 + RM s37(sealed) [4 seats], then J1 baseline seeds after GB-6/7 pass. Do NOT launch. Write ${OUT}/K7_FREEZE_PUSH.md.`, { label: 'freeze-push', phase: 'Freeze+push', schema: S4 })

phase('Verify')
const ve = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only; own code under ${OUT}/verify; write ${OUT}/VERIFY.md). Inputs: ${pre.path}, ${im.report_path}, ${og.report_path}, ${fp ? fp.report_path : '(freeze/push failed)'}. Check the inventory is fully covered by the K7 diff (grep for leftover v3c1 network shas / v3c1 paths / 110-only assumptions), the family check and strict CSV map, the regenerated evidence (re-derive one artefact independently), the FRZ contents == pushed head, the launch lines (cwd, env PYTHONHASHSEED=0 for J1, names, logs, seat order), and that predeclarations precede all computations.`, { label: 'verify-k7', phase: 'Verify', schema: S5 })

return { pre, im, og, fp, ve }
