export const meta = {
  name: 'k92-bundle1-design',
  description: 'Design and predeclaration draft for K9-2 bundle 1 (SC109 west-through capacity + seed-independent left-turn head floor H-b): exact change, keys, values with evidence, gates (bit-identity, fidelity on NC states, regression guard), validation plan options; adversarial review; no code changes',
  phases: [
    { title: 'Design', detail: 'K9_2_DESIGN.md + amendment 24 draft' },
    { title: 'Review', detail: 'adversarial review and fixes' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const OUT = K8 + '/k92/bundle1'
const MEM = 'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory'

const RULES = `
HARD RULES:
- Design only: no code edits, no commits, no replays, no VISSIM, no tests. Light Python/grep for reading only. Write only under ${OUT}/.
- Read-only on worktrees (GWT8 D:/VISSIM-merge/sim3-n31-k8 head b9734abe, pushed), frozen trees, run folders, scratch trees.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix. No verdict language.
- Korean output, plain words, short sentences; tag [실행]/[읽음]/[추론]; cite file:line / JSON paths. AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs in ${OUT}/.
`

const CTX = `
CONTEXT
- User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha256 919b0f33…): D-K9-30 bundle 1 capacity = SC109 west-through boundary movement only (206.53×3 → U4 measured table 5,700.6; J1 FZP 5,927 as sensitivity; SC1001 untouched to preserve K9-1 judging states; east side later with a physical value); D-K9-31 left-turn head floor rule H-b = seed-independent seed from a fixed table (no floor-only deployment); D-K9-32 Ω-outside waiting: report only in bundle 1 (no objective-boundary change); D-K9-33 P (50:50) deferred to bundle 2, PFO own-only/PASSIVE-in-line-search issue recorded as a K9-2 investigation item, scratch trees kept.
- Evidence: ${K8}/k92/attrib/ATTRIBUTION.md (r2), METHOD.md (r2), VERIFY_ATTRIBUTION.md; J1 cause analysis ${K8}/j1/causes/CAUSES.md (r2) and lens files; J1 report ${K8}/j1/analysis/J1_REPORT.md; known defects ${K8}/j1/J1_CAVEAT_ADDENDUM.md, ${K8}/sagate/K91_OUTCOME.md §5; arm patches used in the attribution (CW, H0/H1) in D:/VISSIM-merge/k8_gate_trees/k92attrib/*.build.json and ${K8}/k92/attrib/trees/*.diff.txt; memory ${MEM}/vissim-boundary-movement-capacity-206.md, ${MEM}/vissim-urban-batch1-and-rmcal-20260926.md, ${MEM}/vissim-j1-k8-results-20261015.md.
- Process precedent: K9-1 = design proposal → user decision sheet → amendment (predeclared gates) → mini probe → implementation commits with per-commit gates → full re-judge → independent verify → outcome; K8-8/9/10 = amendments 21/22 with G-H*/G-R* gates (${K8}/K8_PREDECLARATION_AMENDMENT_21.md, _22.md, _23.md, ${K8}/j1/fix/).
`

const SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['OK', 'PARTIAL', 'STOP'] },
    summary: { type: 'string' },
    artifacts: { type: 'string' },
    open: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'summary', 'artifacts', 'open'],
}

phase('Design')
const design = await agent(`${RULES}\n${CTX}\nTASK: write ${OUT}/K9_2_DESIGN.md and ${OUT}/K8_PREDECLARATION_AMENDMENT_24_DRAFT.md for K9-2 bundle 1.
1) Exact change W: which movement(s)/lanes/code path set SC109 west-through capacity today (runtime_setup override site, boundary_out constant), the new config key (off = current behaviour), the value 5,700.6 with its provenance (U4 table row, network version, lanes), sensitivity value 5,927 (J1 FZP; label as post-J1 data), assertions (sum ≤ lanes × 2,000 etc.), and anything else that reads the same capacity (must be unchanged).
2) Exact change H-b: what the left-turn head floor is today (code path, warm-up learning rule, threshold 5 vehicles), what 'seed-independent seed from a fixed table' means concretely (which table/value, e.g. the 1384.6 used in the attribution H1 arm or an NC-derived measurement — give candidates with evidence and pick a recommendation for the user), how learning continues after the seed, and the 'no floor-only' coupling rule.
3) Commit plan and per-commit gates in the K9-1/K8-8 style: key-off bit identity vs b9734abe (decisions + plant outputs on existing judging/probe states), key-on effect limited to the SC109 movements (diff classification), K9-1 judging-state invariance where SC1001 is concerned (which K9-1 gates/states must be bit-identical), fidelity evidence for SC109 west discharge and link-174 queue prediction on NC-only states (blind sample rule: which states may be used; J1 states were already used for attribution), regression guard numbers fixed now, STOP rules.
4) Validation plan options after gates (for the user later): closed-loop VISSIM on v3c3-s31/s41/s43 with the bundle (J1-K9-2) vs offline chained replay; costs; what each can show. Reporting of Ω-outside per D-K9-32.
5) User decisions still needed (values, sample, validation) as a short list.
Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: 'design', phase: 'Design', schema: SCHEMA })

phase('Review')
const review = await agent(`${RULES}\n${CTX}\nTASK: adversarially review ${OUT}/K9_2_DESIGN.md and ${OUT}/K8_PREDECLARATION_AMENDMENT_24_DRAFT.md against the code and the evidence: hidden scope creep (other movements sharing the constant/path), H-b ambiguity (seed value provenance, interaction with learning, seed dependence remaining), gates that could pass while unintended changes happen, blind-sample leaks (reuse of J1/attribution states as fidelity evidence), regression guards defined after data, conflicts with D-K9-30..33, feasibility/cost. Apply corrections (keep _r1 copies) and list remaining user decisions. Return status, Korean summary (<= 25 lines) suitable for relaying, artifacts with sha256, open (user decisions).`, { label: 'review', phase: 'Review', schema: SCHEMA })

return { design, review }
