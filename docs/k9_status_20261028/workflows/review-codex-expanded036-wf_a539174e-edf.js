export const meta = {
  name: 'review-codex-expanded036',
  description: 'Read-only review of codex commit 7ecace6 (freeway expanded036 lineage) and whether it can be layered onto our plant fixes',
  phases: [
    { title: 'Read' },
    { title: 'Synthesize' },
    { title: 'Challenge' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const X = SP + '/codex7ec'
const OUT = SP + '/codex7ec_review'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag claims [실행]/[읽음]/[추론]; cite file:line or JSON key paths). If the Write tool refuses a file, write it with Bash/python.
- The user asked: read commit 7ecace62 (branch codex/sdmpc31-upstream-20260926, author = the user via Codex) and review whether it can be layered onto OUR current plant-fix work.
- The commit (docs/configs/coefficient tables, 51 files, NO code) is extracted read-only under ${X} (same relative paths as the repo). Also available via git in D:/VISSIM-merge/sim3-n31-v3c1 (origin/codex/sdmpc31-upstream-20260926 fetched; commit parent 886a014 = also an ancestor of our branches). Start from ${X}/docs/FREEWAY_MODEL_LINEAGE_20260930.md and ${X}/diagnostics/freeway_lineage_20260930/EXPANDED036_PARAMETERS.md.
- Their setting: network 64cf5f55 (FW80-Urban90 / DSD110 handoff network), seeds 29/43/47 (+ s61 route inventory), 31 physical cells per direction, 159 east coefficients (31 cells x rho_crit, a, tau, nu_ge, nu_lt + delta_merge at cells 10,12,21,23), VSL FD Carlson A 0.5 E 2.0 alpha 0, code = 886a014-based working copy with UNCOMMITTED experimental code (not in the commit). A seed-29 9000 s SDMPC run with expanded036 is in progress on their side.
- OUR plant-fix work (read these; do not modify):
  * Network v3c1 repin: D:/VISSIM-merge/sim3-n31-v3c1 branch claude/repin-v3c1-20260928 (HEAD 9ed2ef0; repin commit 5323faa). Worklog: D:/VISSIM-merge/sim3-n31-v3c1/diagnostics/worklog_20260927_29/README.md and subfolders 01_urban .. 05_repin_p10 (FWE_STRUCT_PROPOSAL.md, P0_REPORT.md, N1_RESULTS.md, N1F_RESULTS.md, VSL_FIXED_DSD_REVIEW.md, capacity-drop addendum, REPIN_PLAN.md). Tuning: diagnostics/sdmpc_n31_20260924/config_n31_v2.json in that tree; plant parameters parameters.json (per-direction FW_E tau 12, nu 38.7, kappa 17, delta 1.0, rho_c x1.4; FW_W v x1.12, rho_c x0.68, delta 0; phi 3.0; per lane-count class rho_crit/a 4 lanes 25/2.0, 3 lanes 28/1.70; v_free per segment measured p85). VSL law chosen from native step experiments: distribution compliance L1 Carlson A 0.94 / E 1.44 (capacity +-1 % at 100/90, -3.6 % at 80); single-value compliance L2 (A 1.33, E 0.87, m_v 0.901/0.812/0.723). N1/N1F: VSL does NOT raise bottleneck discharge (B2 +-2-3 %); the deployed Carlson L0 predicted +6-8 % and was REJECTED. B2 capacity drop INCONCLUSIVE.
  * FW_E structural diagnosis (not yet implemented, user-approved plan): B1 deficit 78 % = cell-12 speed artefact from METANET anticipation (fix F1 acceptance-limited speed closure); cell 18 false bottleneck from 21->31 refinement (F2 phi 0 simple form, F3 scalar through 3 lanes + 10481 bypass storage); collapse origin = 10681 merge lane 2; deployed plant lacks a B1 mainline discharge constraint (F8); F4 gap node b=0. Principle adopted: fix structure before fitting parameters; judge FW_E closed-loop effects only by >=3-seed paired comparisons (J1).
  * Urban batch 2 (urban plant U4/U5/U6) in D:/VISSIM-merge/sim3-n31-urban-b2 (uncommitted; a concurrent workflow is editing starvation_monitor.py there - read only). C3 failed its gates; diagnosis in progress. Mostly urban, but U6 touches the W-side ramp diverge and 10481/10491 off-ramp ports.
  * Memory notes with details: C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory/ (vissim-fwe-plant-structure-20260927.md, vissim-vsl-fixed-dsd-20260928.md, vissim-network-v3c-20260927.md, vissim-vsl-handoff-repro-20260924.md, vissim-sdmpc31-obs150-state-20260924.md).
- HARD RULES: read-only everywhere except writing under ${OUT}. No git checkout/switch/merge/commit/push in any worktree; git show/diff/log/cat-file only. Do not start VISSIM or replays. No downloads. Do not open our sealed held-out seeds (59/61/67 on OUR networks) or held-out s37 data; the codex s61_late README concerns THEIR network 64cf and may be read, but flag it.
`

const R_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    key_findings: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'key_findings', 'open_questions'],
}
const S_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    verdict: { type: 'string' },
    items: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, class: { type: 'string' }, reason: { type: 'string' } }, required: ['item', 'class', 'reason'] } },
    recommended_path: { type: 'string' },
    user_decisions: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'verdict', 'items', 'recommended_path', 'user_decisions'],
}
const C_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    confirmed: { type: 'array', items: { type: 'string' } },
    corrected: { type: 'array', items: { type: 'string' } },
    missing: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'confirmed', 'corrected', 'missing'],
}

phase('Read')
const readers = [
  { key: 'evidence', prompt: `READER 1 - EVIDENCE AND RESULTS. Read every .md in the commit and the small verification/summary/protocol JSONs (cellwise_calibration/*, jacobian_step/*, expanded_joint/*, coupled_expanded_joint/*, freeway_first/**, expanded036_9000_20260930/*, integration_20260926/SELECTION.md). Produce ${OUT}/R1_EVIDENCE.md: for each stage (cellwise 159-coef joint, Jacobian trust015, expanded036, coupled expanded036, and the post-036 branches) state data used (network, seeds, states/time windows, training vs check sets), objective/loss, what improved (state vs response/control-gain prediction, numbers), what failed, adoption status, and stated limitations. Assess overfitting risk (159 values vs number of informative training windows; cell-to-cell parameter spread; parameters at bounds e.g. nu 18.375/36.75), whether any held-out/blind validation exists, and whether results distinguish state fit from control-gain fit. Note any use of seed 61 and what it was used for.` },
  { key: 'config', prompt: `READER 2 - CONFIG AND CODE COMPATIBILITY. Compare the coupled candidate config (${X}/diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json, manifest, effective_parameters.json) and expanded_joint/eval_036/reference_config.json against OUR tunings: 886a014:diagnostics/sdmpc_n31_20260924/config_n31_v2.json, the v3c1 tuning in D:/VISSIM-merge/sim3-n31-v3c1 (HEAD), and the urban-b2 worktree config. Write a structured key-level diff (which sections/keys differ: freeway.physical_cell_fd, state_response.cell_overrides, segment_params, VSL law, merge/lane-drop, off-ramp storage/route inventory bridge, urban, ramps, network pins/sha). For every key their config relies on, check whether OUR code at v3c1 HEAD and in the urban-b2 worktree reads it (grep the reader, cite file:line) and whether validation would accept or reject it; list features whose code is NOT in any of our trees (their uncommitted code). Check the cell partition: are their 31 physical cells (bounds/indices) the same as our sdmpc31 FW_E cells on v3b/v3c1 (compare boundaries, merge/diverge cell indices 10,12,21,23 vs our 10681/10484/10490/10639 merges, cell 12 and cell 18 in our diagnosis)? Check network differences 64cf5f55 vs v3b/v3c1 relevant to the freeway (geometry, lanes, connectors, DSD positions, meters). Write ${OUT}/R2_CONFIG_CODE.md.` },
  { key: 'physics', prompt: `READER 3 - PHYSICS AND CONFLICTS WITH OUR FW_E FINDINGS. Using ${X}/diagnostics/freeway_lineage_20260930/expanded036_parameters.csv and effective_parameters.json plus our FWE_STRUCT_PROPOSAL/P0_REPORT/N1/N1F/capdrop reports and parameters.json in the v3c1 tree: (1) compute what their VSL law Carlson A 0.5 E 2.0 alpha 0 implies for rho_crit, a and capacity at 100/90/80 (use the Carlson VSL FD formula as implemented in OUR code - find it and cite), and compare with our measured L1/L2 and the N1/N1F discharge results (VSL does not raise discharge). (2) Compare their per-cell rho_crit/a/tau/nu/delta with our per-direction values (after multipliers); where do they deviate most, and do the deviations coincide with our structural defects (cell 12 speed artefact from anticipation, cell 18 false bottleneck from refinement, missing B1 discharge constraint, merge delta)? I.e. is expanded036 absorbing structural defects into parameters, which our principle says to fix structurally first? (3) delta_merge 2.2-5.1 at cells 10/12/21/23 vs our delta 1.0 (P0 found delta hits its upper bound on the refined grid) - consistent or conflicting? (4) Would layering expanded036 on top of our planned F1/F2/F3/F8 fixes double-count (parameter compensation + structural fix)? Give concrete examples by cell. Write ${OUT}/R3_PHYSICS.md.` },
]
const reads = await parallel(readers.map(r => () => agent(CTX + '\nYOUR TASK: ' + r.prompt, { label: 'read-' + r.key, phase: 'Read', schema: R_SCHEMA })))

phase('Synthesize')
const synth = await agent(CTX + `
YOUR STAGE: SYNTHESIS. Read the three reader reports: ${reads.map(r => r ? r.report_path : '(failed)').join(', ')} (and spot-check their key claims in the sources). Answer the user's question: can the codex expanded036 work be layered onto our current plant fixes (v3c1 network, VSL L1/L2 law, planned FW_E structural fixes F1/F2/F3/F4/F8, urban batch 2)?
Classify every transferable item (e.g. the 159 coefficients as a whole, delta_merge values, per-cell tau/nu, rho_crit/a pattern, VSL A0.5/E2 law, 31-cell physical partition conventions, route-inventory/storage/proxy branches, inlet speed boundary, exit lane-drop/recovery ideas, calibration METHOD (Jacobian trust-region on response loss), their validation protocol ideas (same-state RM/VSL response comparisons), RM2700 findings) into: A = usable as-is on our line; B = usable after re-deriving on v3c1 / after our structural fixes (say how); C = conflicts or not transferable (say why); D = useful idea/method only. Give a recommended path (ordered steps, what to run, pre-declared checks, cost) and list the decisions the user must make. Be honest about uncertainty. Write ${OUT}/REVIEW.md (Korean, readable by the user; start with a 5-line summary).`, { label: 'synthesis', phase: 'Synthesize', schema: S_SCHEMA })

phase('Challenge')
const chal = await agent(CTX + `
YOUR STAGE: ADVERSARIAL CHECK of ${synth ? synth.report_path : '(synthesis failed)'}. Try to refute its classifications and recommendation: re-verify at least 8 load-bearing claims directly in the sources (coefficient values, key readers in our code, partition equivalence, VSL capacity arithmetic, network differences, seed usage, adoption status). Look for anything the synthesis missed that could make layering either easier (e.g. our code already supports the keys) or riskier (e.g. hidden dependency on their uncommitted code, sign conventions, multiplier double-application 1.4, index base 0 vs logical VSL zones). Write ${OUT}/REVIEW_CHECK.md with confirmed / corrected / missing.`, { label: 'challenge', phase: 'Challenge', schema: C_SCHEMA })

return { reads, synth, chal }
