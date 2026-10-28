export const meta = {
  name: 'v3c2-nc-gates-and-static-checks',
  description: 'Judge v3c2 NC pre-declared gates, compare with v3c1 NC, re-run static checks 2a/2b on v3c2 with the frozen method, verify independently',
  phases: [
    { title: 'Analyze' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const ROOT = 'D:/VISSIM_runs/20260930_v3c2'
const OUT = ROOT + '/reports/nc_analysis'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- Network v3c2 = v3c1 + vehicle composition 14 'Freeway entry DSD110' on freeway inputs 1098 (link 74, FW_E) and 1099 (link 26, FW_W); nothing else changed (${ROOT}/reports/V3C2_BUILD.md, V3C2_BUILD_CHECK.md, receipt v3c2_edit_receipt.json). Reason: v3c1 inserted freeway entry vehicles with urban DSD 40/30 (~40 km/h); entry queue non-empty 97.5 %/99 % of the time; static check 2a OPEN (plant cell-0 stock bias -24..-28 veh) and 2b FAIL (12/62 cells; FW_E cell 0; FW_W cells 0-6 via rho_c x0.68; FW_W 11/12/13/15 short peaks) on v3c1 (${SP}/static_checks/: PREDECLARATION.md sha a992341e, 2a/CHECK_2A.md, 2b/CHECK_2B.md, VERIFY.md; method sources also archived in ${ROOT}/reports/static_check_source/).
- v3c2 NC runs (fast_nc_run, FZP-only, 9000 s): ${ROOT}/s31_v3c2nc, s41, s43, s47 finished EXIT 0 (19:57-20:01); s53 and sealed s37 launched 20:02 (expected done ~21:40). If s53 is not finished when you need it, WAIT for ${ROOT}/s53_v3c2nc/run/run.json "completed": true (poll with a background/Monitor until-loop, not chained sleeps); do not judge 5-seed gates without it. s37 is SEALED: read only its run.json completed/exit_code, never its FZP or any result.
- v3c1 NC comparison runs: D:/VISSIM_runs/20260927_v3c1/s{31,41,43,47,53}_v3c1nc (read-only; never s37 or *_rm).
- Pre-declared gates: ${ROOT}/reports/gate_predeclaration_v3c2_nc.md (sha256 2aa92d42...; verify before use, do not edit).
- HARD RULES: read-only on all run folders and worktrees; write only under ${OUT}. Do not start/kill VISSIM or cscript (two runs are live); never modify D:/VISSIM-merge/frozen/*. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results, no 64cf-s59/s61/s67 numbers. Heavy Python at BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_NUM_THREADS<=4. Seed notation: prefix with network (v3c2-s31, v3c1-s31).
`
const A_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, verdict: { type: 'string' }, headline: { type: 'string' }, deviations: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'verdict', 'headline', 'deviations'] }
const V_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Analyze')
const [gates, statics] = await parallel([
  () => agent(CTX + `
YOUR TASK: GATES + DESCRIPTIVE COMPARISON. Judge G1-G5 exactly as pre-declared for the five fit seeds (G1 receipt, G2 .err vs v3c1, G3 completion/EXIT 0 for all six incl. sealed s37 via run.json only, G4 entry 0-40 m median speed >= 80 km/h on links 74 and 26 every fit seed, G5 deletions / lane-change-wait timeouts vs v3c1 + tolerance). Then DESCRIPTIVE per seed, v3c2 vs v3c1 (same seed): uninserted delay (veh*h) and insertion rates at 1098/1099 and all inputs; entry queue non-empty share; FW_E and FW_W 31-cell speed-time profiles (breakdown onset/duration at B1 ~cell 12 / 10681 merge and B2 ~cells 21-23 / 10484 merge, and FW_W bottlenecks), mainline throughput at key sections, on-ramp merges and off-ramp flows (esp. OR_D_E1 link 127, SC1004 W), urban Omega, Omega TTT, all-link TTT and all + uninserted, vehicles in network over time. Explain in plain terms what changed when the entry throttle was removed (more vehicles on the mainline -> more/less congestion where?). Write ${OUT}/GATES_AND_COMPARISON.md (Korean, 6-line summary first).`, { label: 'gates-compare', phase: 'Analyze', schema: A_SCHEMA }),
  () => agent(CTX + `
YOUR TASK: RE-RUN STATIC CHECKS 2a AND 2b ON v3c2 NC with the SAME frozen method (PREDECLARATION a992341e: definitions, windows, thresholds, rules; fzp_pass.py 011a2462; the P-comp plant harness of ${SP}/static_checks/2a/pcomp with the deployed v3c1 plant, which the network change does not alter). Only the VISSIM data changes (v3c2-s31/41/43/47/53). If a v3c1-specific input (e.g. the EO 30 s extraction used for the grid-consistency stop condition) does not exist for v3c2, derive the equivalent from the v3c2 FZP with the same code or document the deviation. Report 2a (congested share, one-step cell-0 bias per seed, 0-40 m speeds, verdict OPEN/CLOSE/INSUFFICIENT) and 2b (62-cell table, violations, causes, planned F item or 'new'), and a side-by-side with the v3c1 results. Then state plainly whether F10 (inlet speed boundary) and F11 (FW_W upstream per-cell FD) are still needed on v3c2, and if so for which cells, and note whether the plant's per-segment v_free for cell 0 (85.97 FW_E, 98.16 FW_W row) - measured on the throttled network - is now inconsistent with VISSIM. Write ${OUT}/STATIC_CHECKS_V3C2.md (Korean, 6-line summary first).`, { label: 'static-2a2b', phase: 'Analyze', schema: A_SCHEMA }),
])

phase('Verify')
const ver = await agent(CTX + `
YOUR TASK: INDEPENDENT VERIFICATION (own code under ${OUT}/verify). Inputs: ${gates ? gates.report_path : '(gates failed)'}, ${statics ? statics.report_path : '(static checks failed)'}. Re-check the predeclaration sha; recompute G4 for all five seeds and G5 for two seeds; recompute the uninserted delay at 1098/1099 and Omega TTT for two seeds (v3c2 and v3c1); recompute 2a congested share and bias for two seeds and the 2b violation set (plant capacity + p95 for two seeds). Check that the static-check method was not changed after seeing v3c2 data and that verdicts follow the frozen rules. Write ${OUT}/VERIFY.md with confirmed / problems.`, { label: 'verify', phase: 'Verify', schema: V_SCHEMA })

return { gates, statics, ver }
