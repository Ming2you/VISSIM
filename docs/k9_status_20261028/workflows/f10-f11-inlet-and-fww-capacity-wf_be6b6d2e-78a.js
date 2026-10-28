export const meta = {
  name: 'f10-f11-inlet-and-fww-capacity',
  description: 'Pre-declare, review, implement and evaluate F10 (observed inlet speed boundary + cell-0 v_free) and F11 (FW_W per-cell FD) on network v3c2, with key-absent identity and an offline selection check',
  phases: [
    { title: 'Predeclare' },
    { title: 'Review' },
    { title: 'Implement' },
    { title: 'Evaluate' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/f10f11'
const W = 'D:/VISSIM-merge/sim3-n31-f10f11'
const V2 = 'D:/VISSIM_runs/20260930_v3c2'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- Network v3c2 ADOPTED by the user (2026-09-30; ${V2}/reports/DECISION_v3c2_adopt.md). v3c2 NC fit seeds v3c2-s31/41/43/47/53 (FZP-only fast NC runs) in ${V2}/s<seed>_v3c2nc/run; analysis ${V2}/reports/nc_analysis/ (GATES_AND_COMPARISON.md, STATIC_CHECKS_V3C2.md, VERIFY.md; EO extraction nc_analysis/eo; 2a/2b code copies nc_analysis/static_checks_v3c2/). s37 is SEALED (never open). The code repin to v3c2 is NOT done yet (later, bundled); no v3c2 decision states exist (R-obs v3c2 needs the repin).
- Static check results on v3c2 (frozen method, PREDECLARATION a992341e in ${SP}/static_checks and ${V2}/reports/static_check_source): 2a OPEN - FW_E cell 0 one-step stock bias -23.8..-26.3 veh (plant uses virtual upstream speed net.v_free at area_freeway_accounting.py:365; VISSIM inserts into a saturated queue at 23-26 km/h; free-flow insertion 83-89); cell-0 row v_free 85.97 (FW_E) measured on the throttled v3c1 network is inconsistent with v3c2 free-flow p85 ~117; FW_W row 98.16 not judgeable (few free-flow frames). 2b FAIL 14 cells: FW_E 0; FW_W 0-7 (rho_c direction multiplier 0.68 too low upstream; cell 0 also v_free); FW_W 11-15 short 150 s peaks only (pass at 300 s; need multiplier 0.680-0.695).
- USER DECISIONS: F10 = (a) observed inlet speed boundary for cell 0, BOTH directions (and fix the cell-0 v_free rows together); F11 = per-cell (region) FD for the FW_W upstream cells that violate 2b (user approved 0-6; cell 7 and 11-15 now also violate - include them only if the predeclaration justifies it; say so explicitly). Per-cell FD is reimplemented by us (codex code is not used; codex values are never used). Structure first; few physically meaningful parameters; values from declared estimators on v3c2 fit seeds only; no fitting to closed-loop outcomes.
- Code: dedicated worktree W = ${W} (branch claude/fw-inlet-wcap-20260930 from claude/repin-v3c1-20260928 @ 9ed2ef0, clean). All plant changes behind new config keys; key ABSENT => bit-identical behaviour. Known latent defect: state_response cell-index validation runs before the 31-cell partition (canonical_harness.py:301 vs :302-317) - fix it only if F11 needs cell indices >= 21. Local commits allowed only in W with explicit paths, identity Ming2you / alsrjsrb1915@snu.ac.kr, message ending "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; never push; never --renormalize.
- Decision states for identity/selection replays: v3c1 R-obs D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31 (61 states; read-only; replay tooling per ${SP}/hybrid/HYBRID_BUILD.md sections 2.2 and 11.4; always PYTHONHASHSEED=0 because of vendor state.py:1306). These states come from the v3c1 network: fine for code-identity checks and as a descriptive selection check, not as v3c2 evidence.
- HARD RULES: write only in W and ${OUT}; read-only on every run folder and other worktrees (sim3-n31-v3c1, sim3-n31-urban-b2 and sim3-n31-termcost have concurrent workflows); never modify D:/VISSIM-merge/frozen/*. Do not start/kill VISSIM or cscript. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 data; no 64cf-s59/s61/s67 numbers; seed notation with network prefix. Heavy Python at BELOW_NORMAL, NUMBA_NUM_THREADS<=4, one heavy job at a time.
`
const P_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, summary: { type: 'string' }, open_questions: { type: 'array', items: { type: 'string' } } }, required: ['path', 'sha256', 'summary', 'open_questions'] }
const R_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'blocking', 'nonblocking'] }
const I_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, commit: { type: 'string' }, keys: { type: 'string' }, identity: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'commit', 'keys', 'identity', 'stop', 'stop_reason'] }
const E_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, verdict_f10: { type: 'string' }, verdict_f11: { type: 'string' }, selection_check: { type: 'string' }, caveats: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'verdict_f10', 'verdict_f11', 'selection_check', 'caveats'] }
const V_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Predeclare')
const pre = await agent(CTX + `
YOUR STAGE: DESIGN + PRE-DECLARATION (read code in W; no code changes; do NOT compute any estimator output or gate metric - only check data/code availability).
Write ${OUT}/PREDECLARATION_F10F11.md (+ .sha256) fixing:
F10: (i) where the plant sets the cell-0 upstream speed for each direction (cite), the new key and its semantics: upstream speed = causal observed mean speed of vehicles in the first 0-40 m (or the nearest obs150 origin detectors - find which detectors exist for links 74 and 26 in the obs150 bundle and what state_json exposes at decision time) over the last 150 s, held over the horizon; fallback when no vehicles observed; the offline P-comp equivalent from FZP. (ii) cell-0 v_free rows: re-derive with the SP S1 free-flow rule (n>=5, rho<10, p85, t in 900.1-8995.1 s) on v3c2 fit seeds for BOTH directions; declared fallback if too few free-flow frames (keep current). (iii) GATES: 2a harness on v3c2 fit seeds (same frozen method): cell-0 |bias| < 15 veh in >= 3/5 seeds AND cell-0 MAE lower in 5/5 AND cells 1-2 |bias| not increased by > 3 veh in any seed AND the history_forecast mode also meets the first condition; key-absent decision-replay identity (>= 3 v3c1 R-obs states, IDENTICAL via make_replay_state_v2 compare).
F11: (i) which FW_W cells are in scope (0-6 approved; argue 7 and 11-15 in/out), (ii) the ESTIMATOR for each in-scope cell's rho_c (and cell-0 v_free if needed) from v3c2 fit seeds - e.g. critical density at the observed flow maximum of the 150 s Edie flow-density scatter, or capacity = pooled p99 of 150 s flow then rho_c from the FD formula; it must not be defined as 'just above the gate p95', and must be applied after the direction multiplier exactly once, (iii) GATES: 2b on v3c2 with the new plant = 0 violating cells (FW_E 0 counts for F10); leave-one-seed-out: rho_c estimated on 4 seeds passes p95 of the held-out seed in >= 4/5 folds; FW_W one-step prediction (P-comp on FW_W) per-cell stock MAE: improved in in-scope cells in >= 3/5 seeds and not worse by > 10 % in any out-of-scope cell in >= 3/5 seeds; key-absent identity as for F10.
SELECTION CHECK (descriptive, no gate): at 4 v3c1 R-obs states (e.g. 2250, 2700, 3600, 4950), SDMPC decision replays with default tuning vs +F10+F11 keys: selected freeway/urban actions, objective, top-candidate ranking changes; state that it is not v3c2 evidence.
Record everything that is decided by judgement and could be questioned.`, { label: 'predeclare', phase: 'Predeclare', schema: P_SCHEMA })

if (!pre) { return { stopped: 'predeclaration failed' } }

phase('Review')
const rev = await agent(CTX + `
YOUR STAGE: ADVERSARIAL REVIEW of ${pre.path} (sha ${pre.sha256}); read-only; write ${OUT}/PREDECLARATION_REVIEW.md. Try to break it: is the F10 observation causal and available at runtime (not future data)? Would F10 double-count with the existing inlet/buffer paths (freeway_buffer_segments, q_cap 6,937 at AFA:272)? Is the F11 estimator independent of the 2b gate (not tautological) and physically meaningful, and does it respect the one-time multiplier rule? Is the scope choice for cells 7 and 11-15 justified before seeing estimator outputs? Are gates strong enough to catch harm elsewhere (FW_W downstream congestion, B-bottleneck behaviour, VSL sign cell 0)? Could F10's held observed speed misbehave in free flow or empty entry? Blocking items must come with concrete fixes. NOTE: the predeclaration is frozen; blocking fixes go into an AMENDMENT written BEFORE any computation.`, { label: 'review', phase: 'Review', schema: R_SCHEMA })

phase('Implement')
const impl = await agent(CTX + `
YOUR STAGE: AMEND (if needed) + IMPLEMENT. Predeclaration ${pre.path} (sha ${pre.sha256}); review ${rev ? rev.report_path : '(none)'} blocking: ${JSON.stringify(rev ? rev.blocking : [])}. First, if there are blocking items, write ${OUT}/AMENDMENT_1.md (+ sha) addressing each BEFORE computing anything. Then implement F10 and F11 in W behind new config keys (key absent => bit-identical), unit tests (key-absent identity at the module level, multiplier-once, index handling, causal observation, fallbacks), and a tuning generator entry producing a candidate tuning with the keys (values filled later by the estimator stage; keep the generator deterministic). Verify key-absent identity with >= 3 v3c1 R-obs decision replays (IDENTICAL). Commit locally in W with explicit paths. Write ${OUT}/IMPLEMENT.md. stop=true if identity fails.`, { label: 'implement', phase: 'Implement', schema: I_SCHEMA })

if (!impl || impl.stop) { return { pre, rev, impl, stopped: 'implementation stopped' } }

phase('Evaluate')
const ev = await agent(CTX + `
YOUR STAGE: ESTIMATE + EVALUATE exactly as frozen (${pre.path} + any AMENDMENT in ${OUT}; verify shas first; do not change definitions). Implementation: ${impl.report_path} (commit ${impl.commit}). Steps: (1) compute the declared estimators on v3c2 fit seeds (cell-0 v_free both directions; F11 rho_c per in-scope cell) and write the values into the candidate tuning via the generator; (2) run the F10 gates (2a harness, history_forecast mode, cells 1-2), the F11 gates (2b with the new plant, LOSO, FW_W per-cell one-step prediction), and report pass/fail per gate; (3) the descriptive selection check at 4 v3c1 R-obs states (default vs +F10+F11). Outputs under ${OUT}/eval. Commit the filled candidate tuning locally in W (explicit paths). Write ${OUT}/EVALUATION.md (Korean, 6-line summary first) with a clear verdict for F10 and F11 and what the user must decide.`, { label: 'evaluate', phase: 'Evaluate', schema: E_SCHEMA })

phase('Verify')
const ver = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (own code under ${OUT}/verify). Inputs: ${pre.path}, amendments in ${OUT}, ${impl.report_path}, ${ev ? ev.report_path : '(evaluation failed)'}. Check sha/timestamp order (predeclaration and amendments before computations); recompute the estimators from FZP/EO for 2 seeds; recompute 2a bias for 2 seeds and the 2b violation set with the new plant; re-run one key-absent identity replay; review the code diff for guards (every new branch behind the keys) and the multiplier-once rule; check verdicts follow the frozen gates. Write ${OUT}/VERIFY.md with confirmed / problems.`, { label: 'verify', phase: 'Verify', schema: V_SCHEMA })

return { pre, rev, impl, ev, ver }
