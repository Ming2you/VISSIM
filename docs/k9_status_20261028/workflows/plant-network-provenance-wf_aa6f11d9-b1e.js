export const meta = {
  name: 'plant-network-provenance',
  description: 'Why the SDMPC run uses the 21-cell lane plant and which VISSIM network it runs on, vs the 31-cell plant and the FW80/U90 scenario',
  phases: [
    { title: 'Investigate', detail: '31-cell plant, 21-cell lane plant, the two VISSIM networks, decision history' },
    { title: 'Verify', detail: 'adversarial check of each report' },
    { title: 'Synthesize', detail: 'direct answers + switch options' },
  ],
}

const SCRATCH = 'C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\plant_provenance'

const CONTEXT = `
## The user's questions (Korean, verbatim meaning)
"Why do we use the 21-cell per-lane plant instead of the 31-cell plant? Wasn't the 31-cell plant the latest?
Is the current VISSIM network also not the 80-90 one used with the 31-cell plant?"
("plant" in this project = the controller's internal prediction model of the traffic network; VISSIM is the real system.)

## Facts the lead has checked
- Merged tree: D:\\VISSIM-merge\\sim3 = plant branch 00abbab (codex/control-full-review-20260909) + SDMPC controller
  branch 5fdfabd (codex/sdmpc-tangent-20260921), branch claude/sdmpc-native-20260923 @ 673eece.
- docs\\HANDOFF_20260922_control_choice.md (plant branch): fixed scenario "FW80%, urban 90%, seed 23, 9000 s, SimRes 10,
  FZP 5 s"; source network recorded in diagnostics\\selected_control_demand\\CURRENT_SCENARIO.json (SHA + external path),
  byte copy at diagnostics\\handoff_20260922_control_choice\\scenario\\source\\baseline.inpx; "latest 3 plants"
  (boundary / Hadi / Wang) under diagnostics\\demand_sweep\\user_native_20260914\\metanet_calibration_v1\\res10_20260922\\
  boundary_literature_v1\\; its next-task item 3 says to align evaluate_response.py::mpc_choice/online_data/window's
  "21-cell projection, integer-time assumption, fixed 10 s cost weights" with the "latest 31-cell / real .1 s / 1 s
  integration". Also relevant: diagnostics\\demand_sweep\\ramp_dsd_20260916_v2\\segment_resolution_20260921\\README.md,
  diagnostics\\control_comparison_20260922\\model_choice_probe\\README.md, AGENTS.md, docs\\HANDOFF_20260921_gain_prediction.md,
  docs\\SDMPC_*.md, docs\\HANDOFF_20260922_PFO_CAP_SDMPC.md, docs\\SDMPC_PERSISTENT_PLANT_20260922.md.
- The live SDMPC run (sdmpc_lp_9000c, D:\\VISSIM_runs\\20260923_sdmpc\\sdmpc_lp_9000c) is launched by
  D:\\VISSIM-merge\\tools\\run_sdmpc_laneplant.ps1: network = C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM\\.worktrees\\
  sdmpc-lane-plant-20260921\\diagnostics\\lane_plant_20260921\\native\\native_recording\\baseline.inpx with recording proof
  native\\network_recording.json (resolves to the physical source sha fcb349d3...), VBS config scenario\\lane_native.vbs,
  demand profile scenario\\profile.csv, gate map ver2, mapping ver2n21, seed 13, the runner forces SimRes=1.
  The controller's model: lane plant diagnostics\\lane_plant_20260921\\plant.json (7 sha256 pins incl.
  diagnostics\\demand_sweep\\ramp_dsd_20260916_v2\\source_dsd\\baseline.inpx, controller_response_s23_v1\\none\\geometry.json,
  cohort_dynamics_20260920\\..., lane_group_response_20260919\\observations_v1\\s23.json, port_travel_fit_v1, port_profile).
- A memory note from earlier today (2026-09-23) says: "re-pinning the 21-cell lane plant to the new 31-cell plant is
  unfinished (of 7 pins, lane_geometry and port_profile need re-derivation)". Tools the lead wrote earlier:
  D:\\VISSIM-merge\\tools\\repin_survey.py, check_n31_source.py, audit_config_paths.py; evidence write-ups in
  D:\\VISSIM-merge\\evidence\\*.md (STEP2_MERGE_20260922.md, STEP1_TESTS_20260922.md, RM_SEED_SWEEP_20260923.md,
  MECHANISM_20260922.md, FZP_VERIFIED_20260922.md, OBJECTIVE_COMPARE_20260922.md, RM_REPLAY_FIDELITY_20260922.md, ...).
- The conversation transcript with the user (JSONL, large) is
  C:\\Users\\TRLAB\\.claude\\projects\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788.jsonl. It can be
  searched with python/grep for what was decided and told to the user (e.g. "31", "21셀", "repin", "80", "fw080").
  Earlier sessions' transcripts are in the same folder (*.jsonl); search them only with bounded greps.

## HARD RULES
- READ-ONLY everywhere. Two things are running and must not be disturbed: the native run sdmpc_lp_9000c (reads
  D:\\VISSIM-merge\\sim3 at every decision) and an offline sweep that edits D:\\VISSIM-merge\\sim3-capmargin\\evaluation\\
  parameters.json between replays. Do not modify, move or lock files in D:\\VISSIM-merge\\sim3, D:\\VISSIM-merge\\sim3-capmargin,
  D:\\VISSIM_runs, C:\\Users\\TRLAB\\Documents\\ChatGPT\\VISSIM. No git commands that write (no checkout/switch/stash/reset).
  Read-only git (log, show, diff, ls-files, cat-file) is fine. Do not start VISSIM or long computations.
- .inpx files are large XML: never print them whole; parse or grep bounded (sizes first).
- Scratch files only under ${SCRATCH}.
- Cite file:line or path + sha for every claim. Distinguish "the 31-cell plant" (METANET cells) from "the 21-cell lane
  plant" and from VSL sign zones etc.; say exactly what the 21 and 31 count (cells of what, on which corridor/direction).
`

const REPORT = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    facts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, evidence: { type: 'string' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] } }, required: ['claim', 'evidence', 'confidence'] } },
    open_questions: { type: 'string' },
  },
  required: ['summary', 'facts', 'open_questions'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] }, note: { type: 'string' } },
      required: ['claim', 'verdict', 'note'] } },
    missed: { type: 'string' },
  },
  required: ['verdicts', 'missed'],
}

const PARTS = [
  { key: 'plant31', prompt: `
## Your part: the 31-cell plant
What exactly is it: files and code (where the model/config lives, e.g. res10_20260922, boundary/Hadi/Wang configs,
segment_resolution_20260921), what the 31 counts (cells per direction? total? minimum cell 76 m), what it was calibrated
on (which VISSIM network file + sha, which scenario/demand/seed, SimRes), its validation status per the handoff docs
(held-out errors, NOT_QUALIFIED items), and which controller code paths can use it today (does anything in the SDMPC /
wu-link / adapter path load it? evaluate_response.py::mpc_choice uses a 21-cell projection per the handoff). Is it newer
than the lane plant, and in what sense (date, fidelity)?` },
  { key: 'plant21', prompt: `
## Your part: the 21-cell lane plant that the SDMPC uses
What the 21 counts, where it comes from (lane_plant_20260921/plant.json, its 7 pins and what each is), when and on which
branch it was built, and why the SDMPC is tied to it: which SDMPC modules consume lane-plant structures (lane_plant_runtime,
lane_urban_runtime, lane_coupling, the tangent/AD instrumentation, 21-cell VSL product noted in memory), whether the
SDMPC could run on the 31-cell model and what re-pinning requires (the memory note: lane_geometry and port_profile
re-derivation). Read D:\\VISSIM-merge\\tools\\repin_survey.py and check_n31_source.py and any output they wrote (search
D:\\VISSIM-merge\\evidence and the scratchpad folder above it for repin/n31 results). Estimate the work to switch, with
the concrete list of pins/artifacts to re-derive and the checks that would prove the switch.` },
  { key: 'networks', prompt: `
## Your part: the two VISSIM networks and scenarios
Compare (a) the FW80/U90 scenario network (CURRENT_SCENARIO.json -> path + sha; the handoff byte copy) with (b) the
network the SDMPC run uses (lane-plant worktree native_recording/baseline.inpx, its recording proof, the physical source
it resolves to, e.g. ramp_dsd_20260916_v2/source_dsd/baseline.inpx, sha fcb349d3...). Report sha256 of each, sizes,
and a structural diff (parse the XML: links/lanes/connectors counts, vehicle inputs and their volumes, signal
controllers, detectors/data collection points, desired speed decisions/VSL, lnChgDist on meter connectors, evaluation
settings, random seed/SimRes if stored). Also compare the demand actually applied: the SDMPC run's profile.csv +
lane_native.vbs + gate map vs the FW80/U90 scenario's demand scaling/profile (4500 s hold to 9000 s), seed 23 vs 13,
SimRes 10 vs 1. Conclude: same physical network with different demand/settings, or different networks? Which
differences change traffic, which are bookkeeping?` },
  { key: 'history', prompt: `
## Your part: how this choice was made and what the user was told
Search the evidence write-ups (D:\\VISSIM-merge\\evidence\\*.md), docs in D:\\VISSIM-merge\\sim3\\docs, the controller branch
docs, memory files in C:\\Users\\TRLAB\\.claude\\projects\\C--Users-TRLAB-Desktop----\\memory\\, and the conversation
transcript JSONL (bounded python search; print only short excerpts with their timestamps) for: when the SDMPC was
connected to the lane plant rather than the 31-cell plant; whether the user's original request (finish the SDMPC
controller 5fdfabd, connect it to the new plant 00abbab, verify RM/VSL work and TTT improves, check whether the plant
captures RM/VSL benefit) was understood as "connect to the 31-cell plant"; what the assistant told the user about 21 vs
31 cells and about the network/scenario (quote short excerpts); and whether earlier today's native runs (RM seed sweep,
omega TTT, fast_nc) used the FW80/U90 scenario or the lane-plant scenario. Be factual about any gap between the request
and what was done.` },
]

phase('Investigate')
const results = await pipeline(
  PARTS,
  p => agent(CONTEXT + p.prompt, { label: 'investigate:' + p.key, phase: 'Investigate', schema: REPORT }),
  (r, p) => r ? agent(CONTEXT + `
## Your job: adversarial verification of the ${p.key} report below
Re-check every claim yourself (re-read the cited files, recompute hashes/counts cheaply). Look for what it missed or got
wrong, especially: what the 21 and 31 actually count, sha identities of the networks, and whether the SDMPC path loads
any 31-cell artefact. Mark 'confirmed' only for what you checked.

Report:
${JSON.stringify(r, null, 1)}`, { label: 'verify:' + p.key, phase: 'Verify', schema: VERDICTS }).then(v => ({ key: p.key, report: r, check: v })) : null,
)
const done = results.filter(Boolean)
log(`${done.length}/${PARTS.length} reports verified`)

phase('Synthesize')
const answer = await agent(CONTEXT + `
## Your job: the answer, in Korean, for the user
Using only confirmed claims (flag uncertain ones), answer directly and concisely:
1. What the 31-cell plant is and whether it is the latest; what the 21-cell lane plant is; why the SDMPC run uses the
   21-cell one (the technical reason and how it happened), stated plainly including any gap versus the user's original
   request.
2. Whether the current VISSIM network/scenario is the FW80/U90 one: same physical network or not, and every difference
   that changes traffic (demand, seed, SimRes, inputs, meters, VSL, signals).
3. What switching to (31-cell plant + FW80/U90 scenario) would take: concrete work items, checks, rough effort, risks;
   and a middle option if one exists (e.g. keep the lane plant but run on the FW80/U90 network/demand, or vice versa),
   with what each option would and would not answer.
4. What this means for the currently running 9000 s run (sdmpc_lp_9000c) and the cap-margin sweep: keep, stop, or keep
   as a lane-plant baseline.
Use tables where helpful. Cite paths/shas for the key facts.

Material:
${JSON.stringify(done, null, 1)}`, { label: 'synthesize', phase: 'Synthesize' })

return { answer, results: done }
