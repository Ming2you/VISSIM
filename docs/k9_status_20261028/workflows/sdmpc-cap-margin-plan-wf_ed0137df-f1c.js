export const meta = {
  name: 'sdmpc-cap-margin-plan',
  description: 'Map every dependency of cap == PFO-achieved and plan a configurable cap margin',
  phases: [
    { title: 'Map', detail: 'cap consumers, cap==achieved assumptions, margin evidence' },
    { title: 'Verify', detail: 'adversarial check of each map' },
    { title: 'Plan', detail: 'concrete edit list + test plan' },
  ],
}

const SCRATCH = 'C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\cap_margin'

const CONTEXT = `
## Task
The user wants option (a): in SDMPC mode central-pfo-cap-v3, set each interval's budget caps to the PFO-achieved
values PLUS A MARGIN, instead of exactly the achieved values, so the SDMPC can also move NP / NUF upward. Everything
else stays as is (inequality caps, carried prices, max_leader_candidates=1). The margin will be a config parameter
(defaults chosen later by a paired offline sweep). We need a precise, complete edit plan before implementing.

## Facts checked by the lead
- Tree (read-only for you): D:\\VISSIM-merge\\sim3 (branch claude/sdmpc-native-20260923 @ c3799d3). Code in
  evaluation\\controllers\\. Params in evaluation\\parameters.json: sdmpc_pfo_cap {max_iterations 2,
  nuf_tolerance_veh_h 1e-7}; sdmpc_central {np_step_veh 50, nuf_step_veh_h 1000, active_tolerance 1e-8, ...};
  budget_scale_np_veh 100, budget_scale_nuf_veh_h 1000 (in the tuning config
  diagnostics\\sdmpc_pfo_caps_20260922\\config_candidate_obs1.json; that config also has max_leader_candidates 1).
- Mode wiring: sdmpc.py:83-90 (budget_caps=True, pfo_cap_options from parameters section sdmpc_pfo_cap).
- Cap initialization: sdmpc_budget.initialize (~sdmpc_budget.py:1-35): seed.N_P_star, seed.N_UF_star =
  q['np']['actual'], q['nuf']['actual']; receipt fields np_cap_veh, nuf_cap_veh_h, budget_policy='upper_caps',
  physical_commands_unchanged=True.
- PFO-to-SDMPC binding: sdmpc.py:~562-575 (sdmpc_pfo, sdmpc_budget.initialize, query.bind_warm_budget,
  emit sdmpc_pfo_budget_initialized) and sdmpc_tangent_surrogate.py:~80-95, which REQUIRES
  token(expected)==token(action) with expected.N_P_star/N_UF_star recomputed from the reused prediction's achieved
  quantities, and equality with init['np_cap_veh'] / init['nuf_cap_veh_h'] ("PFO budget binding changed physical
  inputs or achieved quantities"). The reuse of the PFO prediction for the first SDMPC iteration is justified by
  "physical commands unchanged".
- First candidate: sdmpc.py:~618 targets = [(anchor.N_P_star if cap_mode ..., anchor.N_UF_star)], :733-736.
- An earlier offline test (decision_mlc3, diagnostics\\sdmpc_pfo_caps_20260922\\decision_mlc3) had a second budget
  candidate with NUF cap +1000 veh/h which ended 0.401 veh.h WORSE (394.317 vs 393.916); NUF -1000 failed the QP.
- Audit today: at 900 s the players asked for +26.0 veh / +24.0 veh/h but projection allowed ~0 because both caps bind
  at the start; the final points ended slack (900 s: NP -7.49, NUF -3.15; 1050 s: NP -24.61, NUF -4.25). Carried
  iteration duals: 900 s -> [2.387, 0.141]; 1050 s -> [1.229, 0.122].

## HARD RULES
- A 20 h native run is LIVE and re-reads Python sources from D:\\VISSIM-merge\\sim3 at every decision: do NOT modify
  anything under D:\\VISSIM-merge\\sim3 (or its .git), C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM, D:\\VISSIM_runs.
  Read-only. Scratch only under ${SCRATCH}. No process kills/launches.
- Big JSON (>1 MB): extract with python, never print whole.
- Cite file:line for every claim.
`

const MAP = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    sites: { type: 'array', items: { type: 'object', properties: {
      where: { type: 'string', description: 'file:line' },
      role: { type: 'string' },
      affected_by_margin: { type: 'string', enum: ['must-change', 'behaviour-changes-automatically', 'unaffected', 'unclear'] },
      required_edit: { type: 'string' } },
      required: ['where', 'role', 'affected_by_margin', 'required_edit'] } },
    risks: { type: 'string' },
  },
  required: ['summary', 'sites', 'risks'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] }, note: { type: 'string' } },
      required: ['claim', 'verdict', 'note'] } },
    missed_sites: { type: 'string', description: 'sites the mapper missed, with file:line and the edit they need' },
  },
  required: ['verdicts', 'missed_sites'],
}

const PARTS = [
  { key: 'consumers', prompt: `
## Your part: every consumer of the caps
Find every read of action.N_P_star / N_UF_star, np_cap / nuf_cap, init['np_cap_veh'] / ['nuf_cap_veh_h'] and the
'target' vector on the live central-pfo-cap-v3 path (sdmpc.py, sdmpc_budget.py, sdmpc_pfo.py, sdmpc_central.py,
sdmpc_sequence.py, sdmpc_tangent_surrogate.py, sdmpc_tangent_worker.py, area_leader_objective.py,
area_follower_objective.py, control_area_objective.py, vissim_stackelberg_adapter.py, signal_actuation_contract.py).
Decide for each: does the cap value change the ROLLOUT (plant prediction / follower physics), the VISSIM COMMANDS
(action CSV, inflow_outflow_allocation, ramp metering targets), the QP / duals / gates, or only receipts? This decides
whether reusing the PFO prediction with a different cap stays valid (the binding's premise).` },
  { key: 'assumptions', prompt: `
## Your part: every place that assumes cap == PFO-achieved, and the tests
1. The binding proof in sdmpc_tangent_surrogate.py (~80-95) and query.bind_warm_budget, any other identity checks,
   receipts and schemas (decision-pfo-budget-initialization/v1, sdmpc-pfo-budget-binding/v1), and the first candidate
   construction in sdmpc.py (~600-620, ~730-745). Specify the exact edit so the binding stays a real proof:
   e.g. record achieved and margin separately, check expected achieved == recorded achieved and
   action cap == achieved + margin, and keep "physical commands unchanged" true.
2. Unit tests that encode cap == achieved: grep diagnostics\\test_sdmpc_pfo_caps.py and other diagnostics\\test_sdmpc*.py
   and test_shared_joint_price_quantity.py etc. List each assertion that must change and how, and propose new tests
   (margin 0 reproduces today bit-for-bit; margin > 0 sets caps = achieved + margin; binding rejects tampering).
3. Parameter plumbing: how sdmpc_pfo_cap is validated (sdmpc.py:84-89) and where scripts/verify_parameters.py checks
   parameters.json / config sections, so new keys (np_cap_margin_veh, nuf_cap_margin_veh_h) are validated, default 0,
   and part of the policy token (so carried prices from a different margin are refused -- check load_prices and
   token(policy)).` },
  { key: 'margin', prompt: `
## Your part: evidence for the margin size and its interaction with the duals
1. Read the decision_mlc3 artefacts (diagnostics\\sdmpc_pfo_caps_20260922\\decision_mlc3\\progress.jsonl and anything
   small there; the big result may be absent) and SQUEEZE / audit docs (D:\\VISSIM-merge\\evidence\\*.md) to explain
   WHY a NUF cap +1000 candidate ended worse even though its feasible set is larger (duals shrink -> bigger steps ->
   worse nonlinear trial? decoding limits? line search?). Use the recorded trial rows if available.
2. From the 900 s native decision and 1050 s replay progress/joint files
   (D:\\VISSIM_runs\\20260923_sdmpc\\sdmpc_lp_9000\\decisions_sdmpc_lp_9000\\action_000900.joint.progress.jsonl and
   D:\\VISSIM_runs\\20260923_sdmpc\\replay_1050_fix\\action_001050.joint.progress.jsonl, plus the joint.json via
   python extraction) get: the achieved NP/NUF, the players' requested budget change (e.g. +26 veh / +24 veh/h at
   900 s), dual values, and the QP scaling (budget_scale). Recommend a sweep grid for (np_margin, nuf_margin) that
   brackets what the players asked for (e.g. 0, ~requested, ~2-4x requested) and say which single default you
   would try first, with reasons. Keep the grid to 2-3 nonzero points (each offline decision costs ~9 min).
3. How the carried price (sdmpc.py:498-505, :758) interacts with a slack starting cap: the dual update formula
   (sdmpc_central.py:1-35), what happens to prices over 2 iterations when the cap starts slack.` },
]

phase('Map')
const results = await pipeline(
  PARTS,
  p => agent(CONTEXT + p.prompt, { label: 'map:' + p.key, phase: 'Map', schema: MAP }),
  (r, p) => r ? agent(CONTEXT + `
## Your job: adversarial verification of the ${p.key} map below
Re-read each cited line. Find missed sites (grep broadly: N_P_star, N_UF_star, np_cap, nuf_cap, np_cap_veh,
nuf_cap_veh_h, initialization, bind_warm_budget, 'upper_caps'). Mark 'confirmed' only for what you checked yourself.

Map:
${JSON.stringify(r, null, 1)}`, { label: 'verify:' + p.key, phase: 'Verify', schema: VERDICTS }).then(v => ({ key: p.key, map: r, check: v })) : null,
)
const done = results.filter(Boolean)
log(`${done.length}/${PARTS.length} maps verified`)

phase('Plan')
const plan = await agent(CONTEXT + `
## Your job: the implementation plan (English, precise)
From the verified maps below, write:
1. EDIT LIST: for each file, exact function / line and the change (code-level), including new parameter keys with
   validation and defaults (margin 0 must be bit-identical to today in decisions AND pass the binding), receipts that
   record achieved and margin separately, and the policy token so prices from a different margin are not inherited.
2. TESTS: which existing assertions change, new tests to add, and the command to run them
   (PYTHONPATH must include C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM\\.review-deps\\sdmpc and ...\\sdmpc-numba).
3. OFFLINE CHECK: margin 0 must reproduce the 900 s objective 393.91612458424544 and the 1050 s objective
   422.6749131864695 exactly; recommended sweep grid and first default, with reasons.
4. RISKS: anything that could make the margin silently not apply (e.g. clipping to np_values grid, sequence copies,
   binding fallback) or break price inheritance.
Use only confirmed claims; flag uncertain ones.

Maps:
${JSON.stringify(done, null, 1)}`, { label: 'plan', phase: 'Plan' })

return { plan, results: done }
