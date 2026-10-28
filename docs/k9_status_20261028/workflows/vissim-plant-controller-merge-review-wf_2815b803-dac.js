export const meta = {
  name: 'vissim-plant-controller-merge-review',
  description: 'Semantic merge-compatibility review of VISSIM plant branch (00abbab) vs uncommitted controller work',
  phases: [
    { title: 'Analyze', detail: 'one agent per overlapping/auto-merged file' },
    { title: 'Verify', detail: 'adversarial check of each claim' },
    { title: 'Synthesize', detail: 'integration risk + merge order' },
  ],
}

const REPO = 'D:/VISSIM-merge/repo'
const SIM2 = 'D:/VISSIM-merge/sim2'
const AN = 'D:/VISSIM-merge/analysis'

const CONTEXT = `
CONTEXT (established facts, do not re-derive):
- Repo clone: ${REPO}. Refs:
  * BASE  = 6d7612b  (common ancestor, 2026-09-21 01:07)
  * PLANT = 00abbab  (branch codex/control-full-review-20260909, 11 commits ahead)
  * CTRL  = sim/ctrl-lf  (branch reconstructed from the user's UNCOMMITTED local worktree
            at C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/sdmpc-tangent-20260921,
            LF-normalized. Its committed ancestor 5fdfabd only added 2 doc files.)
- ${SIM2} holds an IN-PROGRESS merge of PLANT into CTRL (LF-normalized).
  Conflicted files there still contain <<<<<<< ======= >>>>>>> markers.
  Files NOT listed as conflicted were AUTO-MERGED by git.
- Pre-computed WHITESPACE-IGNORING per-side diffs live in ${AN}/ as
  <basename>.PLANT.diff  (BASE -> PLANT) and <basename>.CTRL.diff (BASE -> CTRL).
  USE THESE. Raw git diffs are polluted by CRLF noise.
- PLANT is plant/model fidelity work (freeway FD, lane groups, ramp boundary, accounting).
  CTRL is SDMPC controller work: 39 NEW modules (sdmpc*.py, lane_*.py) plus edits to 24
  existing evaluation/controllers files.

TOOLING RULES:
- Use: git -C ${REPO} show <ref>:<path>   to read a specific version.
- vissim_stackelberg_adapter.py is ~27000 lines. NEVER cat it whole. Use grep -n with
  context, or sed -n 'A,Bp'.
- Report ONLY what you verified by reading actual code. If you could not verify a claim,
  say so explicitly rather than guessing.
`

const FINDING_SCHEMA = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    status: { type: 'string', description: 'CONFLICT or AUTO_MERGED or ONE_SIDED' },
    plant_intent: { type: 'string', description: 'What PLANT changed and why, concretely (function/symbol names).' },
    ctrl_intent: { type: 'string', description: 'What CTRL changed and why, concretely.' },
    semantic_collision: { type: 'boolean', description: 'True if the two sides change the SAME behavior in incompatible ways (not merely the same lines).' },
    collision_explanation: { type: 'string' },
    recommended_resolution: { type: 'string', description: 'Concrete instruction: take plant / take ctrl / combine how. Name symbols and line regions.' },
    silent_breakage_risk: { type: 'string', description: 'What could break with NO conflict marker and NO test failure. Be specific or write NONE.' },
    confidence: { type: 'string', description: 'high / medium / low' },
  },
  required: ['file', 'status', 'plant_intent', 'ctrl_intent', 'semantic_collision', 'collision_explanation', 'recommended_resolution', 'silent_breakage_risk', 'confidence'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    refutation: { type: 'string', description: 'Concrete evidence the analysis is wrong, or empty if it holds.' },
    corrected_resolution: { type: 'string', description: 'If refuted, the corrected recommendation. Else repeat the original.' },
    extra_risk_found: { type: 'string', description: 'Any risk the first pass missed, or NONE.' },
  },
  required: ['refuted', 'refutation', 'corrected_resolution', 'extra_risk_found'],
}

const TARGETS = [
  {
    key: 'area_freeway_accounting',
    path: 'evaluation/controllers/area_freeway_accounting.py',
    status: 'CONFLICT (2 hunks)',
    note: 'Both sides edited. Read the conflict markers in the merge worktree.',
  },
  {
    key: 'physical_lane_groups',
    path: 'evaluation/controllers/physical_lane_groups.py',
    status: 'CONFLICT (2 hunks)',
    note: 'PLANT made a large change here (+260/-9 raw). Read conflict markers.',
  },
  {
    key: 'control_area_objective',
    path: 'evaluation/controllers/control_area_objective.py',
    status: 'AUTO_MERGED',
    note: 'Git auto-merged this after LF normalization. Auto-merge is the DANGEROUS case: verify the merged result in the merge worktree is semantically coherent, not just textually clean.',
  },
  {
    key: 'vissim_stackelberg_adapter',
    path: 'evaluation/controllers/vissim_stackelberg_adapter.py',
    status: 'AUTO_MERGED',
    note: 'Huge file (~27k lines). PLANT change is tiny (+2/-1 ignoring whitespace). CTRL adds ~55 lines. Verify the auto-merge did not drop either side. Use grep, never cat whole.',
  },
  {
    key: 'physical_ramp_boundary',
    path: 'evaluation/controllers/physical_ramp_boundary.py',
    status: 'AUTO_MERGED',
    note: 'Auto-merged even before LF normalization. Verify semantic coherence of the merged result.',
  },
  {
    key: 'freeway_fd',
    path: 'evaluation/controllers/freeway_fd.py',
    status: 'ONE_SIDED (PLANT only)',
    note: 'Only PLANT touched it (+84 lines). CTRL did not. But CTRL added 39 new modules that may CALL into it. Check whether PLANT changed any signature/return-shape that CTRL new modules (grep sdmpc_*.py, lane_*.py in CTRL) depend on. Also PLANT added tests/test_literature_vsl_fd.py and tests/test_receiving_speed_response.py.',
  },
  {
    key: 'parameters_json',
    path: 'evaluation/parameters.json',
    status: 'ONE_SIDED (CTRL only)',
    note: 'Only CTRL touched it (adds sdmpc_pfo_cap constants per the handoff doc). Verify PLANT code changes do not ALSO require new parameter keys that are absent. Check scripts/verify_parameters.py expectations if present.',
  },
  {
    key: 'agents_md',
    path: 'AGENTS.md',
    status: 'CONFLICT',
    note: 'Documentation/working-agreement file. PLANT rewrote a lot (+131 raw). Determine whether the two sides state CONTRADICTORY working rules (that matters operationally) or merely additive sections.',
  },
]

phase('Analyze')

const results = await pipeline(
  TARGETS,
  (t) => agent(
    `${CONTEXT}

TASK: Analyze merge compatibility for ONE file: ${t.path}
Git status of this file in the merge: ${t.status}
Note: ${t.note}

Steps:
1. Read ${AN}/${t.path.split('/').pop()}.PLANT.diff and ${AN}/${t.path.split('/').pop()}.CTRL.diff
   (whitespace-ignoring). These show each side's real change.
2. If CONFLICT: read the conflicted region in ${SIM2}/${t.path} (grep -n for the markers).
   If AUTO_MERGED: read the merged result in ${SIM2}/${t.path} around the regions both
   sides touched, and confirm both sides' intent survived and still makes sense together.
3. Read enough surrounding code (via git -C ${REPO} show) to judge SEMANTICS, not just text.
4. Decide: do the two sides collide in MEANING, or are they independent edits that happen
   to sit near each other?
5. Give a concrete resolution instruction someone can execute.

Be skeptical. The most valuable output is a silent-breakage risk: something that merges
clean, passes tests, and is still wrong.`,
    { label: `analyze:${t.key}`, phase: 'Analyze', schema: FINDING_SCHEMA }
  ),
  (finding, t) => finding ? agent(
    `${CONTEXT}

TASK: Adversarially verify this merge analysis of ${t.path}. Try to REFUTE it.

ANALYSIS UNDER REVIEW:
${JSON.stringify(finding, null, 2)}

Independently check the code yourself (git -C ${REPO} show, and ${SIM2}/${t.path}).
Specifically attack:
- Is "semantic_collision: ${finding.semantic_collision}" actually right? Look for a shared
  variable, constant, call-order, or unit assumption the first pass missed.
- Is the recommended resolution actually executable and correct?
- Did the first pass invent any symbol name that does not exist? Verify each named symbol
  exists via grep.
Default to refuted=true only with concrete evidence. If it holds, say so.`,
    { label: `verify:${t.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }
  ).then(v => ({ ...finding, verdict: v })) : null
)

const clean = results.filter(Boolean)
log(`analyzed ${clean.length}/${TARGETS.length} files`)

phase('Synthesize')

const [apiDrift, critic] = await parallel([
  () => agent(
    `${CONTEXT}

TASK: Cross-cutting API-drift audit.

CTRL adds 39 NEW modules under evaluation/controllers/ (sdmpc*.py, lane_*.py) that exist
ONLY in CTRL. PLANT changed 6 existing files:
  area_freeway_accounting.py, control_area_objective.py, freeway_fd.py,
  physical_lane_groups.py, physical_ramp_boundary.py, vissim_stackelberg_adapter.py

Question: do any of CTRL's 39 new modules import from / call into those 6 files in a way
that PLANT's changes break?

Method:
1. List CTRL-only modules: git -C ${REPO} diff --name-only --diff-filter=A 00abbab sim/ctrl-lf -- evaluation/controllers
2. For each of the 6 PLANT-changed files, extract what PLANT changed at the API surface
   (function signatures, return shapes, dict keys, constants) from ${AN}/<name>.PLANT.diff
3. grep the new CTRL modules in ${SIM2}/evaluation/controllers/ for calls to those symbols.
4. Report each concrete mismatch: caller file+line, callee symbol, what changed, what breaks.

Report ONLY verified call-sites you actually grepped. If there are none, say so plainly -
a clean result is a valid and useful answer. Do not manufacture risk.`,
    { label: 'api-drift', phase: 'Synthesize', schema: {
      type: 'object',
      properties: {
        mismatches: { type: 'array', items: { type: 'object', properties: {
          caller: { type: 'string' }, callee_symbol: { type: 'string' },
          what_changed: { type: 'string' }, breakage: { type: 'string' },
        }, required: ['caller','callee_symbol','what_changed','breakage'] } },
        clean_summary: { type: 'string' },
        modules_checked: { type: 'number' },
      },
      required: ['mismatches','clean_summary','modules_checked'],
    } }
  ),
  () => agent(
    `${CONTEXT}

TASK: Completeness critic for this merge review.

We reviewed these 8 paths: ${TARGETS.map(t => t.path).join(', ')}
We established: 3 textual conflicts after LF normalization (AGENTS.md,
area_freeway_accounting.py, physical_lane_groups.py); everything else auto-merges.

Ask: WHAT IS MISSING from this review? Specifically investigate and report on:
1. Are there files changed by BOTH sides that we did not list? Verify:
   git -C ${REPO} diff --name-only 6d7612b 00abbab > /tmp/p.txt
   git -C ${REPO} diff --name-only 6d7612b sim/ctrl-lf > /tmp/c.txt
   then compare, EXCLUDING pure diagnostics/ output data.
2. Does the branch codex/sdmpc-controller-20260920 (502168d) contain committed controller
   work that is NOT in sim/ctrl-lf and would be LOST? Check:
   git -C ${REPO} log --oneline 5fdfabd..502168d  and what files it touches.
3. Test-suite risk: does PLANT add tests that CTRL's changes would fail, or vice versa?
   List test files added/changed by each side.
4. Any config/JSON contract file (diagnostics/*.json used as a CONTRACT, not output)
   changed by both sides?

Report concrete, verified gaps only.`,
    { label: 'completeness-critic', phase: 'Synthesize', schema: {
      type: 'object',
      properties: {
        missed_dual_edited_files: { type: 'array', items: { type: 'string' } },
        lost_work_risk: { type: 'string' },
        test_risk: { type: 'string' },
        contract_file_risk: { type: 'string' },
        other_gaps: { type: 'string' },
      },
      required: ['missed_dual_edited_files','lost_work_risk','test_risk','contract_file_risk','other_gaps'],
    } }
  ),
])

return { findings: clean, apiDrift, critic }
