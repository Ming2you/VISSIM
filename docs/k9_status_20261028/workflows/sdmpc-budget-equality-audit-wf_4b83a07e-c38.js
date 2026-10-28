export const meta = {
  name: 'sdmpc-budget-equality-audit',
  description: 'Audit whether any SDMPC budget constraint is still an equality in the live path',
  phases: [
    { title: 'Audit', detail: 'QP/dual/gate, central recovery, follower use, decision records' },
    { title: 'Verify', detail: 'one adversarial checker per auditor' },
    { title: 'Synthesize', detail: 'answer + exact list of remaining equalities, if any' },
  ],
}

const SCRATCH = 'C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\budget_audit'

const CONTEXT = `
## Question
The user asks (Korean): "Our SDMPC budget is probably an EQUALITY constraint -- can you change it to an upper-bound
INEQUALITY? That seems to perform better." Before changing anything we must know exactly where, if anywhere, the
budget is still enforced as an equality in the code path the live run executes.

## Facts checked by the lead
- Tree: D:\\VISSIM-merge\\sim3 (branch claude/sdmpc-native-20260923). Controller code: evaluation\\controllers\\.
- The live run uses tuning diagnostics\\sdmpc_pfo_caps_20260922\\config_candidate_obs1.json with
  adapter.sdmpc = "central-pfo-cap-v3".
- sdmpc.py:83-90: mode central-pfo-cap-v3 sets options budget_caps=True, pfo_each_interval=True.
- sdmpc.py:547-551: shared_quantity_constraints(..., np_mode='cap', ..., nuf_mode='cap' if cap_mode else 'equality', ...)
  (shared_quantity_constraints is in area_leader_objective.py).
- sdmpc.py:429-446 solve_qp: rows with glo==ghi go in as equality, others as bounds.
- sdmpc.py:448-470 load_prices: prices[0] must be >= 0; prices[1] >= 0 only if budget_caps.
- sdmpc.py:926: receipt field budget_constraint_policy='NP <= cap; actual_merge_NUF <= cap'.
- sdmpc_central.py: recover(..., caps=False) at :36 uses an active set (:63) and scipy nnls (:76);
  next_budget at :109.
- docs\\HANDOFF_20260922_PFO_CAP_SDMPC.md: "NP <= cap, NUF <= cap, tolerance 1e-7; NUF two-sided band and lower-bound
  price removed; caps wired into QP projection, iteration dual update, central NNLS multipliers, final feasibility
  gate; only two nonnegative prices inherited." The earlier modes proxlinear-v1 / central-reuse-v2 are kept.
- The PFO warm start runs with budget_constraints=false (progress log), and the first cap is the PFO-achieved budget.
- Decision records: native 900 s decision at D:\\VISSIM_runs\\20260923_sdmpc\\sdmpc_lp_9000\\decisions_sdmpc_lp_9000\\
  action_000900.json (58 MB) and .joint.json (53 MB); offline replay of 1050 s at
  D:\\VISSIM_runs\\20260923_sdmpc\\replay_1050_fix\\action_001050.json / .joint.json / .joint.progress.jsonl.
  Earlier offline decision: D:\\VISSIM-merge\\sim3\\diagnostics\\sdmpc_pfo_caps_20260922\\decision_v1\\ and summary.json.
  Pre-change sources: diagnostics\\sdmpc_pfo_caps_20260922\\before_sources\\.

## HARD RULES
- A 20 h native run is LIVE and re-reads Python sources from D:\\VISSIM-merge\\sim3 at every decision:
  do NOT modify anything under D:\\VISSIM-merge\\sim3, C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM or D:\\VISSIM_runs.
  Do not kill or start processes. Scratch files only under ${SCRATCH}.
- The action/joint JSONs are 50+ MB: never print them; extract with python (json.load then walk keys, print small parts).
- Cite file:line for every code claim. Distinguish (a) an optimization CONSTRAINT enforced as equality, from
  (b) an accounting identity (e.g. owner shares summing to a total) that is not a restriction on the decision.
`

const REPORT = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    equalities_found: { type: 'array', items: { type: 'object', properties: {
      where: { type: 'string', description: 'file:line' },
      what: { type: 'string' },
      kind: { type: 'string', enum: ['constraint-on-decision', 'accounting-identity', 'inactive-legacy-mode', 'other'] },
      live_in_central_pfo_cap_v3: { type: 'string', enum: ['yes', 'no', 'unclear'] },
      evidence: { type: 'string' } },
      required: ['where', 'what', 'kind', 'live_in_central_pfo_cap_v3', 'evidence'] } },
    inequality_sites: { type: 'array', items: { type: 'object', properties: {
      where: { type: 'string' }, what: { type: 'string' } }, required: ['where', 'what'] } },
    notes: { type: 'string', description: 'anything the synthesis must know, e.g. a cap that is always active by construction' },
  },
  required: ['summary', 'equalities_found', 'inequality_sites', 'notes'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
      note: { type: 'string' } }, required: ['claim', 'verdict', 'note'] } },
    missed: { type: 'string', description: 'equality sites the auditor missed, if any, with file:line' },
  },
  required: ['verdicts', 'missed'],
}

const AUDITS = [
  { key: 'leader-qp', prompt: `
## Your part: the leader iteration in sdmpc.py and area_leader_objective.shared_quantity_constraints
1. How the budget rows enter solve_qp (G, glo, ghi) in cap mode: is glo = -inf (true upper bound) for NP and for NUF?
   Any row where glo == ghi (equality) that involves the budget?
2. The iteration dual/price update: projection of both prices onto >= 0? Any update that allows a negative NUF price
   or pushes the quantity to equal the cap?
3. The final feasibility gate and the 'cap' vs 'equality' branches of shared_quantity_constraints: exactly what
   'cap' checks (actual <= target + tol?) and what 'equality' checks.
4. Every other place in sdmpc.py / sdmpc_budget.py / sdmpc_pfo.py where a budget target is compared or enforced,
   including how the cap itself is chosen each interval (PFO-achieved value) and whether that makes the cap active by
   construction (an inequality that behaves like an equality at the start point).` },
  { key: 'central', prompt: `
## Your part: sdmpc_central.py (central multiplier recovery and the budget search)
1. recover(): which constraints enter the active set, whether caps=True is passed in the live mode (find the call
   site in sdmpc.py), whether NNLS enforces nonnegative multipliers, and whether complementary slackness holds
   (inactive cap -> zero multiplier) or an inactive cap can still get a multiplier (equality-like treatment).
2. next_budget(): does the leader search move the caps in both directions; is the budget treated as a decision
   variable with an inequality or pinned to a target?
3. Compare with the pre-change sources in diagnostics\\sdmpc_pfo_caps_20260922\\before_sources\\ to list exactly
   what was equality before and what changed.` },
  { key: 'follower', prompt: `
## Your part: the lower level and actuation
How N_P_star, N_UF_star and inflow_outflow_allocation are consumed by the followers and the joint objective
(area_follower_objective.py, area_leader_objective.py, control_area_objective.py, sdmpc_sequence.py,
signal_actuation_contract.py, vissim_stackelberg_adapter.py). Is any follower told to deliver EXACTLY the budget
(e.g. a penalty on |actual - N_UF*| or an allocation that must sum to N_UF*)? Separate real constraints on the
decision from accounting identities such as area_follower_objective.py:~2292 (owner shares sum to nuf) and
area_leader_objective.py:~316. For each, say whether it is on the path of mode central-pfo-cap-v3.` },
  { key: 'records', prompt: `
## Your part: what the actual decisions recorded
From the native 900 s decision and the 1050 s offline replay (paths above; extract with python, never print whole
files), and diagnostics\\sdmpc_pfo_caps_20260922\\summary.json / decision_v1:
1. The budget constraint records: mode ('cap'/'equality'), target/cap, actual NP and NUF, slack, feasibility, and
   the prices/multipliers (prices_scaled, next_prices_scaled, central multipliers) per iteration if recorded.
2. Were the caps active (actual == cap within tolerance) or slack at the final decision? Which multiplier is zero?
3. Is there any recorded comparison of equality vs cap performance (e.g. central-reuse-v2 vs central-pfo-cap-v3,
   a "+2.436 veh.h" figure mentioned in D:\\VISSIM-merge\\evidence\\SQUEEZE_FINAL_20260923.md, or docs in
   D:\\VISSIM-merge\\sim3\\docs\\SDMPC_*.md)? Summarize with numbers and say what exactly was compared.` },
]

phase('Audit')
const results = await pipeline(
  AUDITS,
  a => agent(CONTEXT + a.prompt, { label: 'audit:' + a.key, phase: 'Audit', schema: REPORT }),
  (r, a) => r ? agent(CONTEXT + `
## Your job: adversarial verification of the ${a.key} audit below
Re-read every cited line yourself. Try to find an equality the auditor missed or mislabelled (e.g. called an
accounting identity what is really a constraint, or said 'not live' for code the live mode does execute). Mark
'confirmed' only for what you checked yourself.

Audit:
${JSON.stringify(r, null, 1)}`, { label: 'verify:' + a.key, phase: 'Verify', schema: VERDICTS }).then(v => ({ key: a.key, report: r, check: v })) : null,
)
const done = results.filter(Boolean)
log(`${done.length}/${AUDITS.length} audits verified`)

phase('Synthesize')
const answer = await agent(CONTEXT + `
## Your job: the answer, in Korean
Using only confirmed claims (flag any uncertain one you rely on), answer:
1. Is the budget in the live mode central-pfo-cap-v3 an equality or an upper-bound inequality? Give the decisive
   file:line sites (QP rows, price projection, NNLS, feasibility gate).
2. List every remaining equality on the decision path, if any, with file:line and whether changing it to <= would
   be meaningful (a real constraint) or meaningless (an accounting identity).
3. The practical caveat, if confirmed: e.g. the first cap each interval is the PFO-achieved budget, so the cap starts
   active; whether caps ended active or slack in the 900/1050 decisions; which prices were zero.
4. What evidence exists that inequality performs better than equality (numbers, what was compared).
5. A concrete recommendation: nothing to change / change X at file:line (with the effect).
Keep it short and precise.

Material:
${JSON.stringify(done, null, 1)}`, { label: 'synthesize', phase: 'Synthesize' })

return { answer, results: done }
