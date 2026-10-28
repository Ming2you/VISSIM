export const meta = {
  name: 'vissim-step3-defect-fixes',
  description: 'Verify the 7 known controller/plant defects in the merged tree and design concrete fixes',
  phases: [
    { title: 'Verify', detail: 'confirm each defect exists in the merged tree' },
    { title: 'Design', detail: 'adversarial review of each proposed fix' },
  ],
}

const S = 'D:/VISSIM-merge/sim3'
const H = `${S}/diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1`

const CONTEXT = `
MERGED TREE: ${S} (branch sim/merge-v2, commit 2b46b80 = controller work + plant 00abbab).
This is the ONLY tree to verify against. Do not reason from the plant branch alone.

Key harness files:
  ${H}/boundary_factory.py    (217 lines) - build_window() builds boundary_steps
  ${H}/canonical_harness.py                - model config / rollout
  ${S}/diagnostics/demand_sweep/ramp_dsd_20260916_v2/evaluate_response.py  - the small MPC selector
  ${S}/evaluation/controllers/                                             - production controller code

ENVIRONMENT for running anything:
  PYTHONPATH = C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc ; ...sdmpc-numba ; ${S}
  PYTHONUTF8=1   RW_OFFSET_WRITER=experiment   OMP/OPENBLAS/MKL_NUM_THREADS=1
  Use PowerShell for python (Git Bash POSIX paths break Windows python's PYTHONPATH).

GOAL CONTEXT: the user wants (a) RM and VSL to actually actuate in native VISSIM, and
(b) to determine whether the plant models can CAPTURE the RM/VSL benefit at all - and if
not, whether that is because no benefit exists or because the prediction model is wrong.
A defect that makes a lever structurally invisible to the model is therefore top priority.

ALREADY ESTABLISHED (do not re-derive, but DO verify if your item depends on it):
  In build_window, mode='history_forecast':
    kind=='source' HAS dynamics - demand_vph + source_backlog accumulation (lines ~135-139)
    kind=='ramp'   has NONE     - item['ramp_release_vph'][name] = rate, where rate = recent[name]
  So a change in RM green cannot move the predicted ramp release.

RULES: verify by reading/running actual code in ${S}. Quote file:line. If you cannot
confirm a claim, say so explicitly. Do not propose a fix you have not traced end to end.
`

const SCHEMA = {
  type: 'object',
  properties: {
    defect_id: { type: 'string' },
    exists_in_merged_tree: { type: 'boolean' },
    evidence: { type: 'string', description: 'file:line quotes proving it exists or does not' },
    impact: { type: 'string', description: 'What is wrong in model terms. Be quantitative if possible.' },
    blocks_rm_or_vsl: { type: 'string', description: 'RM / VSL / BOTH / NEITHER, and why' },
    fix_design: { type: 'string', description: 'Concrete change: files, functions, new state, config key to gate it. Must be traceable end to end.' },
    fix_risk: { type: 'string', description: 'What the fix could break; what must be re-validated' },
    test_plan: { type: 'string', description: 'How to prove the fix works without a native VISSIM run' },
    effort: { type: 'string', description: 'small / medium / large' },
  },
  required: ['defect_id','exists_in_merged_tree','evidence','impact','blocks_rm_or_vsl','fix_design','fix_risk','test_plan','effort'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    refutation: { type: 'string' },
    corrected_fix: { type: 'string' },
    missed: { type: 'string' },
  },
  required: ['refuted','refutation','corrected_fix','missed'],
}

const DEFECTS = [
  { key: 'D1_ramp_dynamics', prompt: `DEFECT D1: the prediction has no ramp metering dynamics, so RM is invisible.

Verify in ${H}/boundary_factory.py that kind=='ramp' has no queue/capacity model while
kind=='source' does. Then DESIGN the fix, mirroring the source backlog pattern:

  ramp arriving demand -> ramp queue state -> metering capacity cap -> released rate

You must answer concretely:
 1. Where does ramp ARRIVING demand come from? Is it observable in the data ObservationData
    already loads (look at ObservationData.__init__ and data.boundaries / data.definitions)?
    If a ramp's arrivals are not currently measured, say exactly what would have to be read.
 2. How does an RM command become a capacity in veh/h? Search the merged tree for the
    existing meter command -> rate mapping (ALINEA, meter green, signal head). Note: native
    metering is a 10s integer green on a signal head, so realizable rates are coarse.
 3. Where must the ramp queue state live so it persists across the horizon AND is costed?
    Ramp waiting must enter the objective, otherwise metering looks free.
 4. What config key gates it (repo rule: new features are one config key, bit-identical when off)?` },

  { key: 'D2_stale_config', prompt: `DEFECT D2: evaluate_response.py reads stale config.

The plant README says "기존 소규모 MPC evaluate_response.py:540은 명시된 이전 config.json,
selected_parameters.json, port_profile.json을 읽는다. 최신 boundary/Hadi/Wang 보정값이
자동으로 승격되지는 않는다."

Verify at ${S}/diagnostics/demand_sweep/ramp_dsd_20260916_v2/evaluate_response.py around
line 540. Identify exactly which files it reads, which calibration they correspond to, and
where the NEW boundary/Hadi/Wang calibrations live in the merged tree (search
res10_20260922/boundary_literature_v1). Design the promotion path.` },

  { key: 'D3_vsl_zone_21', prompt: `DEFECT D3: VSL zone projection uses range(21) but there are 31 physical cells per direction.

Verify: grep for range(21) in evaluate_response.py and any VSL zone projection in the merged
tree. Confirm the current physical cell count per direction (search freeway_segment_params,
31 cells). Determine what the 21 refers to historically and what the correct projection is.
Cross-check against the known fact that VSL is written to 8 sign zones per direction
(not per-cell), so the zone->cell mapping matters more than the raw count.` },

  { key: 'D4_time_phase', prompt: `DEFECT D4: online data reading allows integer seconds only, but native FZP is at 5.1, 10.1s phases.

Verify where the integer-time restriction lives (evaluate_response.py and/or the online
reader). Show the code that rejects or rounds fractional times. Then check how
boundary_factory handles phase - it computes 'phase' and uses round(...,6); read that and
say whether the harness already handles the .1 offset correctly while the MPC reader does not.
Design the fix so both agree.` },

  { key: 'D5_cost_weight', prompt: `DEFECT D5: cost calculation uses a fixed 10-second weight, but mainline integration is now 1s.

Verify the fixed 10s weight in the cost calculation (evaluate_response.py). Confirm the
current mainline integration step and the ramp internal record step in the merged tree.
Quantify the error: a fixed 10s weight against a 1s integration is a 10x scale error on that
term unless compensated elsewhere - check whether anything compensates. State whether this
biases toward or against control.` },

  { key: 'M1_delta_merge', prompt: `DEFECT M1: PLANT zeroes metanet_delta_merge / freeway_lane_drop_phi for literature models;
CTRL re-sources the read so PLANT's write loses.

Verify both halves in the merged tree:
 (a) PLANT side: ${H}/canonical_harness.py near line 588-591, inside _config's literature
     branch, setting net.metanet_delta_merge = 0. and net.freeway_lane_drop_phi = 0.
 (b) CTRL side: ${S}/evaluation/controllers/area_freeway_accounting.py around line 160,
     delta_m read via direction_params (metanet_parameters_by_direction), and the
     install_freeway_segment_runtime phi read in vissim_stackelberg_adapter.py near 8980.
Determine whether CTRL's per-direction lookup actually overrides PLANT's zeroing, i.e.
whether metanet_parameters_by_direction carries a nonzero delta/phi for the literature roads.
Then design the fix so the literature models do not stack the empirical merge/drop terms.` },

  { key: 'M2_rho_max', prompt: `DEFECT M2: CTRL's metanet_parameter_transfer strips rho_max from segment rows, degrading
PLANT's VSL-induced-FD jam-density safety check from per-cell to global.

Verify in the merged tree:
 (a) ${S}/evaluation/controllers/metanet_parameter_transfer.py - find CELL_KEYS and confirm
     rho_max is absent, and confirm configure() overwrites net.freeway_segment_params.
 (b) ${S}/evaluation/controllers/freeway_fd.py - find _literature_target (or whichever
     function) doing row.get('rho_max', net.rho_max) and the raise
     'VSL-induced FD critical density exceeds physical jam density'.
Then determine whether a cell's real rho_max is ever BELOW the global net.rho_max in the
current calibrated data (check freeway_segment_params values in a real config). If it never
is, the defect is latent, not active - say so honestly. Design the fix either way.` },
]

phase('Verify')

const out = await pipeline(
  DEFECTS,
  (d) => agent(`${CONTEXT}\n\n${d.prompt}`, { label: `verify:${d.key}`, phase: 'Verify', schema: SCHEMA }),
  (r, d) => r ? agent(`${CONTEXT}

Adversarially review this defect analysis and fix design for ${d.key}. Try to REFUTE it.

${JSON.stringify(r, null, 2)}

Attack specifically:
- Does the defect actually exist in ${S}? Re-check the quoted file:line yourself.
- Is the fix traceable end to end, or does it hand-wave a data source that does not exist?
- Would the fix be bit-identical when its config key is off?
- Does the fix silently change any already-validated number?
Only mark refuted=true with concrete evidence.`, { label: `review:${d.key}`, phase: 'Design', schema: VERDICT })
    .then(v => ({ ...r, verdict: v })) : null
)

return { defects: out.filter(Boolean) }
