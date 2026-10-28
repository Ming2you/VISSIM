export const meta = {
  name: 'terminal-cost-offline',
  description: 'Offline plant study: does a terminal cost (free-flow cost-to-go) make the 450 s Omega-TTT objective pick what the long-horizon plant consequence prefers?',
  phases: [
    { title: 'Design' },
    { title: 'Review' },
    { title: 'Build' },
    { title: 'Run' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/termcost'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag claims [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- QUESTION (user, 2026-09-30): SDMPC-31 minimises Omega TTT over a 450 s horizon (150 s x 3 blocks) with NO terminal cost (sdmpc.py:203-207 even rejects control_area_objective.beta_seconds != 0). At the horizon end a vehicle still waiting on a ramp and one 100 m before an exit count the same (both stop accruing), so "cost now, benefit later" actions (e.g. metering to protect the mainline, urban release) may be undervalued. Does adding a terminal cost - the cheapest form being the remaining free-flow travel time to leave Omega (equivalently a travel-distance/TVD reward converted to free-flow time per link, so urban 50 km/h and freeway 110 km/h are weighted neutrally) - make the 450 s objective choose what the plant's own long-horizon consequence prefers? PLANT-ONLY offline study (no VISSIM). Whether the plant itself is right is a separate question (plant-fix work) - state that limitation.
- Code: dedicated worktree W = D:/VISSIM-merge/sim3-n31-termcost (branch claude/terminal-cost-offline-20260930 from claude/repin-v3c1-20260928 @ 9ed2ef0 = network v3c1 repin incl. VSL law L1). Only W and ${OUT} may be written. No commits needed; if you commit, local only with explicit paths (identity Ming2you / alsrjsrb1915@snu.ac.kr, message ending "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"), never push, never --renormalize.
- States: R-obs no-control run D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31 (61 decision states decisions_sdmpc31_v3c1_nc_s31/state_*.json; READ-ONLY - prepare replay copies elsewhere). Default tuning W/diagnostics/sdmpc_n31_20260924/config_n31_v2.json. Replay tooling and how states are prepared: see ${SP}/hybrid/HYBRID_BUILD.md sections 2.2 and 11.4 (make_replay_state_v2.py prepare/compare, replay_decision_n31.ps1, run_replay.py) - reuse the plant/rollout code path SDMPC uses, do not write a second plant.
- Known facts to respect: vendor state.py:1306 set-iteration float sum depends on PYTHONHASHSEED -> always PYTHONHASHSEED=0. FW_E congested roughly 2250-4650 s in NC s31 (cells 7-9 at 36-51 km/h, B2 cells 13-14 ~51 km/h). VSL does not raise discharge in VISSIM (N1/N1F); plant VSL law is L1. Omega excludes uninserted entry queues and outside-urban queues (opposite bias: pushing queues out of Omega looks free) - report it.
- HARD RULES: do not start/kill VISSIM or cscript; never modify D:/VISSIM-merge/frozen/* or any D:/VISSIM_runs folder (read-only); do not touch other worktrees (sim3-n31-v3c1, sim3-n31-urban-b2 has a concurrent workflow, sim3-n31-hybrid). Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No held-out s37 or sealed seeds 59/61/67. No downloads. Run heavy Python at BELOW_NORMAL priority with limited threads (NUMBA_NUM_THREADS<=4, one heavy job at a time); another workflow is replaying concurrently.
`

const D_SCHEMA = { type: 'object', properties: { design_path: { type: 'string' }, feasible: { type: 'boolean' }, blockers: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } }, required: ['design_path', 'feasible', 'blockers', 'summary'] }
const RV_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'blocking', 'nonblocking'] }
const B_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, harness: { type: 'string' }, validation: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'harness', 'validation', 'stop', 'stop_reason'] }
const RUN_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, verdict: { type: 'string' }, headline_numbers: { type: 'string' }, caveats: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'verdict', 'headline_numbers', 'caveats'] }
const V_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Design')
const design = await agent(CTX + `
YOUR STAGE: DESIGN + FEASIBILITY SCOUT (read code in W; write only ${OUT}/DESIGN.md and scratch notes).
Find and cite: (1) how SDMPC evaluates a candidate action sequence with the plant from a prepared decision state (entry point, sequence blocks, what is held after the last block, how Omega TTT is accumulated incl. control_area_objective / AreaMetrics); (2) whether the rollout can run beyond 450 s (more blocks or step loop), and how boundary demand / arrival forecasts / urban signal plans are continued beyond the forecast window; (3) what end-state is available (per-cell stocks, lane/queue stocks, ramp storage, urban movement queues, cohorts/routes) and the graph data needed for a cost-to-go (link lengths, free-flow speeds per link/cell, turning fractions beta, Omega membership, exits).
Then PRE-DECLARE (before any result exists):
- States: 8 R-obs states = 1200 (uncongested control), 1800, 2250, 2700, 3000, 3600, 4200, 4950 (+ 6300 optional).
- Candidates per state (about 20, each held for the first 450 s, then an IDENTICAL continuation policy for all candidates, e.g. the no-control/held plan): base (held/no-control); RM on FW_E meters 10681, 10490, 10484, 10639 each alone at its minimum admissible green, all four at green 6, all four at minimum; FW_W four meters at minimum; VSL S4 at 90 and 80, S5 at 80 (only if the plant/ownership allows it offline); urban: SC1001 and SC1004 (off-ramp exit signals) and SC109 phase-3 green +10 s and -10 s (keep cycle feasible). Adapt only if a candidate is infeasible, and say why.
- Scorers: (a) 450 s Omega TTT (current); (b1) (a) + terminal cost TC1 = sum over end-state stocks of free-flow cost-to-go to leave Omega (backward recursion over the plant graph with beta splits; veh*h); (b2) (a) + TC2 = TC1 + deterministic queue-clearance delay for queued stocks (state the formula); (h900) 900 s horizon without terminal cost. Reference (ref): Omega TTT to T+1800 s (candidate 450 s, then continuation) - check stability against T+1350.
- Metrics per state: Kendall tau vs ref; argmin agreement; regret_X = ref(argmin_X) - min ref; also whether any RM-restrict or VSL candidate is ever optimal under ref.
- Success criteria (fixed now): terminal cost 'helps' if mean regret of b1 or b2 <= 50 % of (a)'s mean regret AND tau improves in >= 6/8 states; 'not the bottleneck' if (a) already agrees with ref on argmin in >= 7/8 states or its mean regret <= 0.1 % of ref. Otherwise 'inconclusive'.
- Validation required before the run: the harness's (a) for the base/held action must reproduce SDMPC's own held objective at a replayed state (numerically, cite the recorded value), and TC1 sanity (a single free-flow vehicle at an entry gets ~ its path free-flow time).
Set feasible=false with blockers only if the plant cannot be rolled out/scored as required even with small harness-side changes.`, { label: 'design', phase: 'Design', schema: D_SCHEMA })

if (!design || !design.feasible) { return { design, stopped: 'design infeasible' } }

phase('Review')
const review = await agent(CTX + `
YOUR STAGE: ADVERSARIAL DESIGN REVIEW (read-only; write ${OUT}/DESIGN_REVIEW.md). Read ${design.design_path}. Try to break it: is the continuation policy truly identical across candidates and does it avoid favouring any candidate? Is T+1800 long enough for affected vehicles to leave Omega (check path free-flow times and queues)? Does TC1 double-count stocks already counted in TTT or miss stocks (ramp storage, off-ramp ports, urban queues, transit reservations)? Is beta-weighted cost-to-go correct for fixed routes (plant cohorts) and consistent with Omega exits? Are candidates feasible in the plant (meter admissible/unique-service greens, VSL ownership, cycle constraints)? Could plant nondeterminism or demand-forecast extrapolation dominate the differences (check magnitude vs differences)? Are success criteria meaningful given typical candidate spreads? Blocking = would make the conclusion wrong; give concrete fixes.`, { label: 'design-review', phase: 'Review', schema: RV_SCHEMA })

phase('Build')
const build = await agent(CTX + `
YOUR STAGE: BUILD + VALIDATE THE HARNESS. Design ${design.design_path}; review ${review ? review.report_path : '(none)'} blocking: ${JSON.stringify(review ? review.blocking : [])} - address every blocking item (or argue with evidence). Build the harness under ${OUT}/harness (import the plant/SDMPC code from W; minimal changes in W only if unavoidable, guarded so default behaviour is unchanged, and list them). Prepare replay states for the 8 states (copies, never write the run folder). Implement scorers a, b1, b2, h900, ref (+1350 stability) and the cost-to-go recursion. VALIDATE: (1) (a) for the held action equals SDMPC's held objective at >= 2 states (replay the decision with the default tuning if no recorded value exists; cite numbers and tolerance); (2) TC1 sanity cases; (3) determinism: re-run one state twice, identical numbers under PYTHONHASHSEED=0; (4) per-rollout wall time, and a cost estimate for the full run. Write ${OUT}/BUILD.md. stop=true if (1) cannot be made to match.`, { label: 'build', phase: 'Build', schema: B_SCHEMA })

if (!build || build.stop) { return { design, review, build, stopped: 'build stopped' } }

phase('Run')
const run = await agent(CTX + `
YOUR STAGE: RUN THE STUDY with the validated harness ${build.harness} (report ${build.report_path}). All 8 states x all candidates x scorers (a, b1, b2, h900, ref1800, ref1350). One heavy job at a time, BELOW_NORMAL. Save raw per-candidate numbers (CSV/JSON) under ${OUT}/results. Compute the pre-declared metrics and apply the pre-declared success criteria WITHOUT changing them; add descriptive extras (which candidate types win under each scorer, magnitude of differences vs ref spread, where TC1/TC2 reorder candidates and why - e.g. ramp-held vehicles' cost-to-go, congested-cell stocks). Explicitly answer: (i) does the missing terminal cost change the chosen action in this plant? (ii) do RM-restrict or VSL candidates ever win under the long-horizon reference (if never, a terminal cost cannot create RM/VSL gains - the plant lacks a throughput mechanism)? (iii) urban release candidates? Write ${OUT}/RESULTS.md (Korean, start with a 5-line summary for the user).`, { label: 'run', phase: 'Run', schema: RUN_SCHEMA })

phase('Verify')
const verify = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only on W; own recomputation under ${OUT}/verify). Read ${OUT}/DESIGN.md, DESIGN_REVIEW.md, BUILD.md, RESULTS.md and the raw results. Recompute the metrics and the verdict from the raw numbers with your own code; spot-check 2 states by re-running (a) and ref for 3 candidates; check that the success criteria were applied exactly as pre-declared; check TC1 on a hand-computed example; look for confounds (continuation policy, demand extrapolation, nondeterminism, Omega boundary). Write ${OUT}/VERIFY.md with confirmed / problems.`, { label: 'verify', phase: 'Verify', schema: V_SCHEMA })

return { design, review, build, run, verify }
