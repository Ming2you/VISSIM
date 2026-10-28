export const meta = {
  name: 'sdmpc-compute-time-reduction',
  description: 'Find where the SDMPC decision spends its 544.5s and what can safely cut it under the 150s interval',
  phases: [
    { title: 'Survey', detail: 'one angle per agent on where the time goes' },
    { title: 'Verify', detail: 'adversarial check of each proposed cut' },
  ],
}

const A = 'C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/sdmpc-tangent-20260921'

const CONTEXT = `
TREE: ${A} (the controller worktree; uncommitted SDMPC work lives here).
A mirror of the same source with the plant merged is at D:/VISSIM-merge/sim3 - prefer ${A}
because that is where the measured diagnostics live.

ENVIRONMENT (PowerShell for python; Git Bash POSIX paths break Windows PYTHONPATH):
  PYTHONPATH = C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc ; ...sdmpc-numba
  PYTHONUTF8=1  RW_OFFSET_WRITER=experiment  OMP/OPENBLAS/MKL_NUM_THREADS=1
  Four VISSIM runs plus one SDMPC decision measurement are occupying the machine.
  KEEP CPU USE LIGHT. Read code and archived diagnostics; do NOT launch new rollouts,
  decision measurements, or anything that spawns workers.

THE PROBLEM (from docs/HANDOFF_20260922_PFO_CAP_SDMPC.md, measured, 900s saved state,
H450 = three 150s independent control blocks, max 8 workers, no time limit, 1 budget candidate):

  | computation        | seconds | iterations cap/run/accepted | converged |
  | PFO                | 370.711 | 2 / 2 / 2                   | no, iteration_limit |
  | SDMPC after PFO    | 171.194 | 1 candidate x 2 / 2 / 2     | no, iteration_limit |
  | whole incl. init   | 544.512 |                             | no |

  PFO used 6 rollouts, SDMPC 3 more, 9 total. The PFO->SDMPC binding added 0 rollouts.
  The control interval is 150s, so this is 3.6x too slow for real time. The handoff says
  plainly: "현재는 150초 실시간 계산조건을 충족하지 못한다."

ALREADY KNOWN (do not re-derive):
- Evidence lives under ${A}/diagnostics/sdmpc_pfo_caps_20260922/ :
  summary.json, decision_v1/ (progress.jsonl, result.json, request.pickle), decision_v1.log
- adapter.joint_owner_game.max_leader_candidates = 1 in config_candidate.json, so the
  multi-budget outer loop never ran; more candidates would ADD ~171s each.
- evaluation/parameters.json sdmpc block: max_iterations, line_search_steps=3,
  restoration_iterations, qp_iterations, proximal, dual_step=1.0, qp_tolerance=1e-10,
  objective_tolerance=1e-07.
- A long list of speed features is already ON in config_candidate.json: sdmpc_fast_primitives,
  sdmpc_prediction_cache, sdmpc_prediction_hotpath, sdmpc_surrogate_reuse,
  sdmpc_initial_shared_prediction, sdmpc_response_np_cache, sdmpc_ramp_stock_cache,
  sdmpc_initial_derivative_overlap, sdmpc_trial_derivative_overlap,
  sdmpc_tangent_concurrent_primal, sdmpc_derivative_workers=8, sdmpc_tangent_backend=reverse-v1.
  So the easy wins may already be taken - check before proposing them again.

RULES: quote file:line and, where a number exists, quote the measured number from the
archived diagnostics. Distinguish "this would cut time" from "this would cut time WITHOUT
changing the decision". The handoff's own rule: any iteration-count change needs a separate
config/parameters experiment against the same state. Do not propose accepting a worse
decision to go faster without saying so explicitly.
`

const SCHEMA = {
  type: 'object',
  properties: {
    angle: { type: 'string' },
    where_time_goes: { type: 'string', description: 'Measured or code-derived breakdown for this angle, with numbers where available.' },
    proposals: { type: 'array', items: { type: 'object', properties: {
      change: { type: 'string' },
      expected_saving: { type: 'string' },
      changes_the_decision: { type: 'string', description: 'yes / no / unknown, and why' },
      risk: { type: 'string' },
      config_key: { type: 'string', description: 'The single config key that gates it, or NEW if one must be added' },
    }, required: ['change','expected_saving','changes_the_decision','risk','config_key'] } },
    already_done: { type: 'string', description: 'Speedups already enabled that this angle would otherwise propose.' },
    hard_floor: { type: 'string', description: 'What cannot be removed without changing the answer, and why.' },
  },
  required: ['angle','where_time_goes','proposals','already_done','hard_floor'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    refutation: { type: 'string' },
    corrected: { type: 'string' },
    missed: { type: 'string' },
  },
  required: ['refuted','refutation','corrected','missed'],
}

const ANGLES = [
  { key: 'profile', prompt: `ANGLE 1: where does the 544.5s actually go?

Read the archived run rather than guessing: ${A}/diagnostics/sdmpc_pfo_caps_20260922/decision_v1/progress.jsonl
and decision_v1.log, plus summary.json. Build the best timing breakdown you can from what
was recorded (per phase, per iteration, per rollout, worker wait vs compute). Say explicitly
which parts of the 544.5s are NOT explained by the records. Also check whether
diagnostics/measure_sdmpc_pfo_decision.py records timers that would give a finer breakdown
on a future run, and name them.` },

  { key: 'pfo_cost', prompt: `ANGLE 2: the PFO half (370.7s of 544.5s).

PFO is the bigger half and it hit iteration_limit at 2/2/2. Read
${A}/evaluation/controllers/sdmpc_pfo.py and its callers in sdmpc.py.
Determine: what does one PFO iteration cost and why; how many rollouts per iteration (the
record says 6 rollouts total for PFO); whether the 19 owner QPs are solved serially or in
parallel; whether the line search (line_search_steps=3) re-predicts or reuses; and what the
cheapest honest reduction is. Note the handoff's own framing: the PFO exists to produce the
first budget (achieved NP and NUF) and its final prediction/Jacobian is reused as the SDMPC
first-iteration binding at zero extra rollouts.` },

  { key: 'parallelism', prompt: `ANGLE 3: parallelism and the worker pool.

sdmpc_derivative_workers = 8 and the machine has 20 logical cores, 128GB RAM, and is
currently only ~30% busy with four VISSIM runs. config_candidate.json also sets
config_overrides.mpc.stackelberg_leader_parallel_backend = "serial" and
config_overrides.mpc.grid_parallel_backend = "serial".
Determine what is actually parallelised today (read sdmpc_tangent_concurrent.py,
sdmpc_tangent_worker.py, sdmpc_tangent_prefetch.py and the derivative-overlap options),
what is left serial and why, and whether raising the worker count or flipping either
"serial" backend is safe and would help. Check for any recorded worker-wait time.` },

  { key: 'iterations', prompt: `ANGLE 4: iteration counts and tolerances.

Both PFO and SDMPC stopped at iteration_limit (2/2/2), i.e. they were cut off, not
converged, and central stationarity was 8.18447 against
sdmpc_central.stationarity_tolerance = 0.001.
Read evaluation/parameters.json's sdmpc / sdmpc_central / sdmpc_tangent blocks and
evaluation/controllers/sdmpc.py's use of max_iterations, line_search_steps,
restoration_iterations, qp_iterations, qp_tolerance (1e-10), objective_tolerance (1e-07).
Question honestly: is any of this over-tight for a controller that is already stopping at
the iteration cap? A tolerance that is never reached costs nothing; a tolerance that forces
extra inner work costs a lot. Separate the two. Say what the time/quality trade actually is,
and what experiment would settle it without hand-waving.` },
]

phase('Survey')

const out = await pipeline(
  ANGLES,
  (a) => agent(`${CONTEXT}\n\n${a.prompt}`, { label: `survey:${a.key}`, phase: 'Survey', schema: SCHEMA }),
  (res, a) => res ? agent(`${CONTEXT}

Adversarially review this compute-time analysis of ${a.key}. Try to REFUTE it.

${JSON.stringify(res, null, 2)}

Attack: are the quoted numbers actually in the archived diagnostics, or invented? Does each
proposed change really save what is claimed? Would it change the decision (the honest answer
is often "unknown without an experiment")? Is any proposal already enabled in
config_candidate.json? Only mark refuted=true with concrete evidence.`,
    { label: `verify:${a.key}`, phase: 'Verify', schema: VERDICT })
    .then(v => ({ ...res, verdict: v })) : null
)

return { angles: out.filter(Boolean) }
