export const meta = {
  name: 'sdmpc-squeeze-taped-primal',
  description: 'Squeeze the SDMPC decision hard: attack the taped forward primal (83.3%), the serial batch count, and the spawn residual',
  phases: [
    { title: 'Attack', detail: 'one lever per agent, measured not guessed' },
    { title: 'Verify', detail: 'adversarial check of each claimed saving' },
  ],
}

const A = 'C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/sdmpc-tangent-20260921'

const CONTEXT = [
  'TREE: ' + A + '. Archived evidence: diagnostics/sdmpc_pfo_caps_20260922/{summary.json,',
  'decision_v1/{progress.jsonl,result.json},decision_v1.log} and a newer 3-candidate run at',
  'diagnostics/sdmpc_pfo_caps_20260922/decision_mlc3/.',
  '',
  'ENVIRONMENT: PowerShell for python. PYTHONPATH = C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc ; ...sdmpc-numba',
  'PYTHONUTF8=1 RW_OFFSET_WRITER=experiment OMP/OPENBLAS/MKL_NUM_THREADS=1',
  'Three VISSIM runs occupy the box. KEEP CPU LIGHT: read code and archives. A tiny targeted',
  'micro-benchmark is allowed ONLY if it runs in well under a minute and spawns no workers.',
  '',
  'MEASURED BASELINE - do not re-derive, these are established:',
  '  Whole decision 544.512 s. 98.60% is five SERIAL rollout batches:',
  '    A PFO initial eval 113.303 | B PFO it0 trials 135.122 | C PFO it1 trials 120.898',
  '    D SDMPC it0 119.610 | E SDMPC it1 scalar 47.974      (sum 536.907)',
  '  Inside ONE taped rollout (two receipts survive, result.json:1277119 and :2515622):',
  '    tangent_sec (taped forward primal) 100.536 / 99.665   -> 83.3% / 83.4%',
  '    reverse_sec (whole adjoint)          2.647 /  2.710   ->  2.2%',
  '    state_check_sec                      0.00498/ 0.00485',
  '    wall_sec_including_spawn           120.652 /119.501',
  '    UNATTRIBUTED residual               17.464 / 17.121   -> 14.4%  (spawn + import + pickling)',
  '    tape 14,064,354 nodes / 450,071,024 bytes / 231 axes / 22 outputs / 3 control blocks',
  '    primal_comparisons 8,869,202 / 8,922,564   <- 63% of tape nodes are COMPARISONS',
  '  A SCALAR (untaped) rollout is 47.974 s with the same spawn class, so the untaped forward',
  '  simulation is roughly 31 s and TAPING MULTIPLIES IT BY ~3.2x. (inferred, not measured)',
  '  9 rollouts total, 4 of them thrown away (unused_ad_predictions: 4). Cross-prediction',
  '  concurrency is already near ideal (3 slots 2.97x, 2 slots 1.99x); extra TRIALS are nearly',
  '  free (+18% each), extra ITERATIONS cost a whole serial batch.',
  '',
  'ALREADY TAKEN, worth 0 s, DO NOT propose again:',
  '  reverse-v1 backend (adjoint already 2.2%); derivative_workers>8 (hard-capped at',
  '  sdmpc.py:148-150,178); flipping the "serial" mpc backends (tests/test_real_run_stays_serial.py',
  '  asserts serial); raising the batch slot cap (counts are 1,3,2,2,1, the cap of 8 never binds);',
  '  relaxing stationarity_tolerance / qp_iterations / qp_tolerance / restoration_iterations',
  '  (all measured at exactly 0.000 s; the 76 SLSQP solves all terminate successfully and the',
  '  restoration loop never runs); the last-iteration derivative skip (already on, sdmpc.py:803).',
  '',
  'TARGET: the control interval is 150 s. The known floor is one taped rollout (113.25 s) plus',
  'one trial (47.97 s) = 161 s serial, already over. So the question is NOT "can we reach 150 s',
  'with the current horizon" - assume we cannot - but "how far down can this honestly go, and',
  'what is the cheapest path there".',
  '',
  'RULES: every number must come from the archive or from a micro-benchmark you actually ran.',
  'Separate "saves time" from "saves time WITHOUT changing the decision". If a lever changes the',
  'decision, say so plainly rather than burying it. Do not propose accepting a worse decision',
  'without labelling it.',
].join('\n')

const SCHEMA = {
  type: 'object',
  properties: {
    lever: { type: 'string' },
    finding: { type: 'string', description: 'What you established, with file:line and numbers.' },
    proposals: { type: 'array', items: { type: 'object', properties: {
      change: { type: 'string' },
      measured_or_estimated: { type: 'string', description: 'MEASURED (say how) or ESTIMATED (say from what)' },
      saving_sec: { type: 'string' },
      changes_the_decision: { type: 'string' },
      risk: { type: 'string' },
      effort: { type: 'string' },
    }, required: ['change','measured_or_estimated','saving_sec','changes_the_decision','risk','effort'] } },
    dead_end: { type: 'string', description: 'What you checked on this lever that turned out worthless, so nobody retries it.' },
  },
  required: ['lever','finding','proposals','dead_end'],
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

const LEVERS = [
  { key: 'tape_comparisons', prompt: [
    'LEVER 1: 63% of the tape is comparisons. Attack that.',
    '',
    'primal_comparisons = 8,869,202 out of 14,064,354 tape nodes per prediction.',
    'Read ' + A + '/evaluation/controllers/sdmpc_tangent_reverse.py (Trace.branch around :121-131,',
    '_COMPILED around :161), sdmpc_tangent.py and sdmpc_tangent_fast.py.',
    'Establish: what a "comparison" node costs vs an arithmetic node (memory and time); what the',
    'branch records are USED for downstream (grep exact_tie_axes, discrete_dependency and whatever',
    'else Trace.branch feeds); whether anything in the returned Jacobian or the feasibility',
    'certificates depends on them, or whether they are purely diagnostic.',
    'Then say concretely what switching them off would save and what evidence would be lost.',
    'If you can, time a tiny synthetic tape with and without branch recording to get a real ratio',
    'rather than assuming comparisons and arithmetic cost the same.',
  ].join('\n') },

  { key: 'untaped_primal', prompt: [
    'LEVER 2: the untaped forward simulation itself (~31 s inferred).',
    '',
    'Even with zero AD overhead, one 450-model-second prediction appears to cost ~31 s of plain',
    'Python simulation. That is the true floor under everything.',
    'Find where it goes. The prediction is three 150 s control blocks over freeway cells, ramp',
    'queues and the urban model. Read the prediction entry point used by the tangent worker',
    '(' + A + '/evaluation/controllers/sdmpc_tangent_worker.py around :393-400 calls predict(action)),',
    'follow it into the plant, and identify the dominant inner loops. Look for anything that is',
    'recomputed per step but is constant across a block, any per-second Python loop that could be',
    'vectorised, and anything already cached (sdmpc_prediction_cache, sdmpc_ramp_stock_cache,',
    'sdmpc_fast_primitives) so you do not propose it twice.',
    'A micro-benchmark of one scalar predict() is NOT allowed (too heavy). Work from code and from',
    'the archived scalar rollout timing (47.974 s wall, same spawn class).',
  ].join('\n') },

  { key: 'serial_batches', prompt: [
    'LEVER 3: reduce the number of SERIAL batches from five.',
    '',
    'Batches A..E are serial because each needs the previous result. Measured: extra trials inside',
    'one batch are nearly free (+18%), extra batches cost ~110-135 s each. So the only large win is',
    'fewer batches.',
    'Read sdmpc_pfo.py end to end and sdmpc.py solve() around :560-620 and :730-870.',
    'Answer concretely:',
    ' (a) Does batch A (PFO initial evaluation of the reference) really need derivatives, or could',
    '     it be scalar? What does the first PFO QP consume?',
    ' (b) The PFO->SDMPC binding already reuses the PFO final prediction/Jacobian at zero extra',
    '     rollouts (handoff). Is there an equivalent reuse available ACROSS control intervals - the',
    '     previous interval final Jacobian as this interval batch-A - and what makes that unsound',
    '     (the handoff says PFO is re-run fresh every interval by design; say whether that is a',
    '     correctness requirement or a conservative choice)?',
    ' (c) Can batch E (SDMPC final scalar trial) be dropped or merged?',
    'For each, state whether it changes the decision.',
  ].join('\n') },

  { key: 'spawn_residual', prompt: [
    'LEVER 4: the 17.3 s per-rollout spawn/transport residual (139 s aggregate, 25% of the run).',
    '',
    'Measured residual = wall_sec_including_spawn - tangent_sec - reverse_sec - state_check_sec',
    '= 17.464 and 17.121 s. Eight tangent rollouts => ~139 s.',
    'Read ' + A + '/evaluation/controllers/sdmpc_tangent.py (_evaluate_single around :38-62: it makes a',
    'TemporaryDirectory, pickles the request, subprocess.run sdmpc_tangent_worker.py, reads the',
    'result back) and sdmpc_tangent_worker.py startup.',
    'Break the 17.3 s down as far as the code allows: interpreter start, numba import/cache load',
    '(reverse_sec already shows compile_or_load 1.31-1.44 s INSIDE the child, so the numba cost is',
    'partly already counted), request pickle size and write, result pickle read, parent-side',
    'validate/deepcopy.',
    'Then design a persistent worker: what exactly must be reset between requests for the worker to',
    'remain a pure function of the request; what the isolation guarantee currently is (the worker',
    'own checks) and what would be lost; and how much of the 139 s is actually recoverable versus',
    'irreducible.',
    'If you can measure interpreter+numba import cost cheaply (time a bare python -c import numba',
    'with the pinned dependency path), do it - that is one number that grounds the whole estimate.',
  ].join('\n') },
]

phase('Attack')

const out = await pipeline(
  LEVERS,
  (l) => agent(CONTEXT + '\n\n' + l.prompt, { label: 'attack:' + l.key, phase: 'Attack', schema: SCHEMA }),
  (res, l) => res ? agent(CONTEXT + '\n\nAdversarially review this squeeze analysis of ' + l.key + '. Try to REFUTE it.\n\n'
      + JSON.stringify(res, null, 2)
      + '\n\nAttack: is every quoted number actually in the archive, or invented? Is any "MEASURED" claim'
      + '\nactually an estimate? Does the proposed change really save what is claimed, or does it move'
      + '\ncost elsewhere? Would it change the decision? Is it already enabled? Is the effort estimate'
      + '\ncredible given what the code actually looks like? Only mark refuted=true with concrete evidence.',
    { label: 'verify:' + l.key, phase: 'Verify', schema: VERDICT })
    .then(v => Object.assign({}, res, { verdict: v })) : null
)

return { levers: out.filter(Boolean) }
