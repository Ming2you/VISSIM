export const meta = {
  name: 'urban-b2-c6-levers-and-c3-diagnosis',
  description: 'Apply C6 levers (a)(b) with re-gating, then decompose the C3 gate failures and draft a C3 v2 proposal, then adversarially check the diagnosis',
  phases: [
    { title: 'C6' },
    { title: 'Diagnose' },
    { title: 'Check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const B = SP + '/urban-b2'
const CTX = `
CONTEXT (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line. If the Write tool refuses a report file, write it with Bash/python.
- Urban batch 2 of SDMPC-31 (v3b network). Approved plan: ${B}/BATCH2_PLAN.md (read §0-§10 + appendix C as needed). Worktree W = D:/VISSIM-merge/sim3-n31-urban-b2, branch claude/urban-batch2-20260928, HEAD cf3ce37; all batch-2 changes are UNCOMMITTED in W (current diff sha256 1f33be50..., adapter b06aa24f... after the stage 3-7 fix). Harness H = ${B}/harness. Stage reports: ${B}/impl/STAGE0.md ... STAGE7.md and ${B}/impl/STAGE3-7_FIX.md. Stage-7 replay outputs (v1 decision-record format) under the R7 folder named in STAGE7.md.
- USER DECISIONS (2026-09-30):
  1. C3 (U4 head saturation table + U5 shared head-group budget + U6 physical_diverge_v1, all-or-nothing) is FAILED as registered (5 of 14 gates: G-U5-127, G0 A1, G-v3b (a) SC1001 W, G6 (G6-3/G6-5), three-path §5.3). Do NOT re-define gates to pass it. Next: decompose the causes and propose a C3 v2 that keeps the G-SC109 fix; C3 v2 will be re-registered and re-gated later after the user approves the proposal.
  2. Apply ALL record/time cleanups: C6 levers (a) parse only the links/signalHeads part of the inpx, (b) skip re-validation of the T-150 frame pinned by the same sha; KEEP the constant coding already done in stage 3 and the C3 decision-record v2 (install facts as sha16, no top-level projection_diagnostics copy) from the fix stage. Re-take G-ID (d) and the G-C6 gates.
  3. Stage 8 (C2 increment = C3+C2 − C3) is DEFERRED until C3 v2 exists (C2 alone on U1+U3 already failed in batch 1). Do not run stage 8 or stage 9.
- HARD RULES: no commits, no push, no git --renormalize; do not start/kill VISSIM or cscript; never modify D:/VISSIM-merge/frozen/* or any run folder under D:/VISSIM_runs (read-only); do not touch other worktrees (sim3-n31-v3c1, sim3-n31-hybrid, ...) or branches. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Do not read held-out seed 37 data or sealed seeds 59/61/67. No downloads. All replays ONE AT A TIME, BELOW_NORMAL, PYTHONHASHSEED=0, numba cache as in the stage reports. Key-absent paths must stay bit-identical. Preserve each file's line-ending style (use the stage-5 eol-preserving edit approach). Known nondeterminism: vendor state.py:1306 set-iteration float sum (last-digit differences in prediction summaries) - report it, do not fix it here.
`

const C6_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    diff_sha256: { type: 'string' },
    gates: { type: 'string' },
    time_result: { type: 'string' },
    stop: { type: 'boolean' },
    stop_reason: { type: 'string' },
  },
  required: ['report_path', 'diff_sha256', 'gates', 'time_result', 'stop', 'stop_reason'],
}
const DIAG_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    causes: { type: 'array', items: { type: 'object', properties: { gate: { type: 'string' }, component: { type: 'string' }, mechanism: { type: 'string' }, evidence: { type: 'string' }, confidence: { type: 'string' } }, required: ['gate', 'component', 'mechanism', 'evidence', 'confidence'] } },
    c3v2_proposal: { type: 'string' },
    user_decisions_needed: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'causes', 'c3v2_proposal', 'user_decisions_needed'],
}
const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    confirmed: { type: 'array', items: { type: 'string' } },
    refuted_or_weak: { type: 'array', items: { type: 'string' } },
    missing: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'confirmed', 'refuted_or_weak', 'missing'],
}

phase('C6')
const c6 = await agent(CTX + `
YOUR STAGE: C6 LEVERS (a)(b) + RE-GATING (code change in W only in evaluation/controllers/starvation_monitor.py and its tests unless strictly necessary).
Read ${B}/impl/STAGE3.md (C6 v2, the two remaining levers, G-C6 definitions and harness scripts c6_profile.py / c6_chain_inputs3.py / c6_analyze3.py / c6_queue3.py) and ${B}/impl/STAGE3-7_FIX.md. Record the starting W diff sha.
1. Implement (a) partial inpx parse limited to links/signalHeads (must yield exactly the same parsed physical groups; add an identity unit test against the full parse) and (b) skip re-validation of the T-150 frame when its pin (sha) is unchanged (fail-closed if the pin differs or is missing; unit test both paths). Keep constant coding and the C3 record v2 unchanged.
2. Tests: T2 (test_n31_urban_batch2) and the 40-run suite (H/run_suites.py + compare_suites.py) - regressions 0.
3. Gates: G-ID (d) = G-C6-0 (a) R-obs-b 61 MRS compare IDENTICAL and (c) SDMPC 5 (S1 1800/3600/6300, S0e 1800/3600) IDENTICAL; G-C6-1, 1b, 2, 3 (size per decision <= 1 % AND time: mean, alternating pairs, per-decision count > 1 %), 4; v2->v3 block identity (flag rows identical to before). Measure time under a quiet machine if possible (no VISSIM is running now).
Write ${B}/impl/STAGE3c_C6_LEVERS.md. stop=true only if G-ID fails.`, { label: 'c6-levers', phase: 'C6', schema: C6_SCHEMA })

if (!c6 || c6.stop) { return { c6, stopped: 'C6 stage stopped' } }

phase('Diagnose')
const diag = await agent(CTX + `
YOUR STAGE: C3 FAILURE DECOMPOSITION (no source changes in W; harness-only in-memory patches as in STAGE7 §11 attribution arms are allowed; outputs under ${B}/diag_c3/). Current W diff after C6 levers: ${c6.diff_sha256}.
Read STAGE7.md fully (§0, §4.4, §5.1-5.2, §6, §7, §10.1, §11, §13) and STAGE3-7_FIX.md (v2 records need unpack_record; stage-7 outputs are v1). Reuse R7 captures where valid; re-capture only what is missing.
Answer with evidence, per failed gate, WHICH component (U4 values, U5 budget/allocation/weights, U6, or interaction) and WHAT mechanism:
Q-a G0 A1 (+1.319; transit-included +0.264): decompose by approach and horizon; the named approaches SC1004|S (bias +19 -> -52), SC105|W_SC1003 (+22), SC107|W_SC1004 (+23; 1220000201|p3 n_g 4 but 3 flow lanes), SC11|E_SC12. Is it s_g too high vs FZP, n_g vs flow-lane mismatch, U5 budget binding/water-filling order, or queue/discharge timing? Quantify each approach's contribution to +1.319.
Q-b G-v3b (a) SC1001 W (link 127) MAE 30.2 (U6-only 16.9): over-discharge source - 127|p3/p4 s_g (table 1899.7/2058.3 vs independent FZP 1780/1803 and .mer exact 1877/2029.8), U5 off-ramp member weight beta*ready, 10481/10491 ports. Relate to G-U5-127 (off-ramp-origin share model 0.26/0.30 vs FZP 0.80/0.78; storage 10481 +4.0).
Q-c G6: G6-5 bias +8.8 (SC1004 W_out; SC1004 E->W discharge and 10682 landing larger than proxy) and G6-3 MAE 5.03.
Q-d three-path §5.3: continuous vs exact owner difference SC109 0.098, SC11 0.023 and SC7 FD out of the one-sided region at T2700 - is it the non-smoothness of U4/U5 (min/budget kinks) seen by the tangent worker, and what would make the continuous path consistent?
Q-e G-SC109 PASS: which exact part (e.g. U4 replacing the 206.53 boundary capacity, the 21|p3 membership of SC108_W_to_E_SC109) is responsible, so C3 v2 keeps it; show with an attribution arm.
Also note auxiliary: S1 7650 vertex ratio +11.1 %p and NUF dual 0 -> 0.113, slope tail x3-6 - attribute if feasible.
Then write a C3 v2 PROPOSAL: ranked candidate fixes (each: what changes, which gate it addresses, expected direction with evidence, risk to G-SC109 and G-ID), and a C3 v2 pre-registration draft that keeps the 14 gates and their thresholds. List the three definition issues from STAGE7 §13 (T3 transit inclusion, G-U5-127 category, G-v3b (d) ② counterpart) and any new ones as USER DECISIONS - do not decide them. Write ${B}/diag_c3/C3_DIAGNOSIS.md.`, { label: 'c3-diagnosis', phase: 'Diagnose', schema: DIAG_SCHEMA })

phase('Check')
const check = await agent(CTX + `
YOUR STAGE: ADVERSARIAL CHECK of the C3 diagnosis (read-only on W; your own recomputations under ${B}/diag_c3/check/).
Read ${diag ? diag.report_path : '(diagnosis failed - report that)'}. For each cause claimed, try to REFUTE it: recompute the key numbers independently (own code, not the diagnosis scripts), test alternative explanations (e.g. timing/transit accounting, observation definition, seed/state selection, the state.py:1306 nondeterminism), and check that each proposed C3 v2 fix would not break G-SC109 or key-absent identity. Mark each claim confirmed / weak / refuted with evidence, and list important questions the diagnosis did not answer. Write ${B}/diag_c3/C3_DIAGNOSIS_CHECK.md.`, { label: 'c3-check', phase: 'Check', schema: CHECK_SCHEMA })

return { c6, diag, check }
