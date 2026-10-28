export const meta = {
  name: 'vissim-scope-expansion-assessment',
  description: 'Assess how to bring the urban network into the RM/VSL prediction scope',
  phases: [
    { title: 'Survey', detail: 'what urban-capable prediction paths already exist' },
    { title: 'Verify', detail: 'adversarial check of each route' },
  ],
}

const S = 'D:/VISSIM-merge/sim3'

const CONTEXT = `
MERGED TREE: ${S} (branch sim/merge-v2). This is the only tree to verify against.

ENVIRONMENT (PowerShell for python; Git Bash POSIX paths break Windows PYTHONPATH):
  PYTHONPATH = C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc ; ...sdmpc-numba ; ${S}
  PYTHONUTF8=1  RW_OFFSET_WRITER=experiment  OMP/OPENBLAS/MKL_NUM_THREADS=1
  A long VISSIM run is occupying the machine - keep CPU use light, avoid heavy rollouts.

ESTABLISHED BY MEASUREMENT (do not re-derive; these are the motivation):
- The small diagnostic MPC (diagnostics/demand_sweep/ramp_dsd_20260916_v2/evaluate_response.py)
  predicts on a FREEWAY-ONLY component. component() states its own scope:
  "42 mainline cells + 8 on connectors + 8 off connectors; not Omega".
- Replaying ALINEA's real commands from a common state (cutoff 3450.1, 450s) gives:
      model   dFW_E -12.33  dFW_W  0.0000  dRampConnector +9.92
      native  dFW_E -17.84  dFW_W +2.1583  dRampConnector +9.32   network total -9.09
  So in-scope terms are roughly right (FW_E 69%, ramps 106%) and the out-of-scope terms
  (FW_W cross-direction, urban) are missed entirely.
- dFW_W == 0 exactly is CORRECT for that component: the four ramps ALINEA metered in that
  window are all FW_E ramps (FW_E = 10484,10490,10639,10681 / FW_W = 10480,10482,10644,10646).
  native's FW_W +17.14 vehicles comes through the URBAN network (blocked ramps spill back onto
  shared upstream urban links). Omega = freeway + protected urban network, 635 inside links.
- Coefficient sweeps cannot close the gap: nu 35->15 changes the response 0.5%,
  delta_merge 0->1 changes it 0.2%, capacity-drop phi 1.0->0.85 changes it 48% but from a
  small base. The deficit is scope, not calibration.

GOAL: the user wants RM/VSL evaluated against Omega TTT, which includes urban. Determine
what already exists in this tree for an urban-inclusive prediction, and what it would take
to use it for the same replay-fidelity test.

RULES: verify by reading actual code, quote file:line. If you cannot confirm something,
say so. Do not propose building anything that already exists.
`

const SCHEMA = {
  type: 'object',
  properties: {
    route: { type: 'string' },
    exists: { type: 'boolean' },
    evidence: { type: 'string', description: 'file:line quotes' },
    what_it_models: { type: 'string', description: 'Exactly which physical scope: freeway cells? urban links? signals? ramps? Omega?' },
    can_run_offline: { type: 'string', description: 'Can it be driven from archived observations like evaluate_response can, without VISSIM? What inputs does it need and do they exist in this tree?' },
    blockers: { type: 'string' },
    effort: { type: 'string', description: 'small / medium / large, with reasoning' },
  },
  required: ['route','exists','evidence','what_it_models','can_run_offline','blockers','effort'],
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

const ROUTES = [
  { key: 'sdmpc_urban', prompt: `ROUTE A: the SDMPC controller's own urban modules.

The controller work added these CTRL-only modules under ${S}/evaluation/controllers/:
  lane_urban_runtime.py, physical_urban_transport.py, sdmpc_tangent_urban.py,
  sdmpc_tangent_urban_store.py, lane_coupling.py, lane_plant_runtime.py
Determine whether these give an urban-inclusive prediction, what they model exactly, and
whether they can be driven offline from archived observations (what state do they need?).
Specifically check what lane_coupling.run_interval couples, and whether the urban side
carries signal timing, queues and routing or only aggregate transport.` },

  { key: 'gne_area_runtime', prompt: `ROUTE B: the pre-existing GNE / area objective path.

${S}/evaluation/controllers/ contains area_runtime.py, control_area_objective.py,
area_leader_objective.py, area_follower_objective.py, urban_flow_accounting.py,
shared_approach.py, signal_head_observation.py. The project's Omega accounting
(diagnostics/control_area_membership.json, 635 inside links) is used by the native compare.
Determine whether this path already predicts urban queues/delays jointly with the freeway,
what drives it, and whether it can be run offline on archived observations for a
replay-fidelity test like the freeway-only one.` },

  { key: 'canonical_urban', prompt: `ROUTE C: does the canonical harness itself have an urban option?

${S}/diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py
is the freeway component model. Check for any urban/lane-group/coupled option inside it
(search lane_group_dynamics, urban, coupled, component_boundary) and whether
CanonicalFreewayModel.rollout can be extended or is structurally freeway-only.
Also check evaluate_response.py's simulate() for a lane_group_dynamics path.` },

  { key: 'minimal_bridge', prompt: `ROUTE D: the cheapest honest bridge.

Given the goal is only to EXPLAIN the missing out-of-scope terms (FW_W +2.16 and urban
-2.73 over a 450s window), is there a cheaper route than a full urban prediction? Consider:
 (a) measuring the urban/cross-direction response empirically from the FZP and reporting it
     as a known out-of-scope correction rather than predicting it,
 (b) extending the component boundary just to the four FW_W ramps and their shared upstream
     urban links (which ones are shared? check diagnostics/control_area_membership.json and
     the ramp upstream links 124,32,31,129,70,69,121,68),
 (c) doing nothing and scoping every claim to the freeway component.
Assess each honestly, including what each would and would not let the controller optimize.` },
]

phase('Survey')

const out = await pipeline(
  ROUTES,
  (r) => agent(`${CONTEXT}\n\n${r.prompt}`, { label: `survey:${r.key}`, phase: 'Survey', schema: SCHEMA }),
  (res, r) => res ? agent(`${CONTEXT}

Adversarially review this assessment of ${r.key}. Try to REFUTE it.

${JSON.stringify(res, null, 2)}

Attack: does the named code actually exist and do what is claimed? Re-check every file:line.
Is "can_run_offline" real, or does it need state that is absent from this tree? Is the
effort estimate defensible? Only mark refuted=true with concrete evidence.`,
    { label: `verify:${r.key}`, phase: 'Verify', schema: VERDICT })
    .then(v => ({ ...res, verdict: v })) : null
)

return { routes: out.filter(Boolean) }
