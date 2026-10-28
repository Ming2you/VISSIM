export const meta = {
  name: 'sdmpc-observation-150s',
  description: 'Classify every observation the SDMPC uses at a decision (snapshot / 150 s aggregate / per-second only) and design a 150 s collection path',
  phases: [
    { title: 'Map', detail: 'lane plant observer, urban head observation, freeway/ramp inputs for the 31-cell plant' },
    { title: 'Design', detail: 'classification table + 150 s observation design' },
  ],
}

const CONTEXT = `
## Why
The user wants the SDMPC to COLLECT OBSERVATIONS ONCE PER 150 s DECISION, not every second. Today the native runner
scripts\\run_real_world_stackelberg_controller.vbs forces SimRes 1 and steps VISSIM one second at a time, writing a ~850 KB lane frame
every second (WriteLanePlantObservation, CollectHeadObservation, SealHeadSignalStates, head windows ...), because the 21-cell lane
plant (evaluation\\controllers\\lane_plant_observation.py load_causal_snapshot, lane_plant_runtime.observe_live / initialize) rebuilds
its decision state from the last 150 s of per-second frames, and the urban head observer needs SimRes 1. The user deliberately uses
VISSIM SimRes 10 (more accurate recovery / no spurious blocking) and prefers 150 s collection. Goal: SimRes 10, VISSIM run
continuously between decisions (a RunEventContinuousMode with SimBreakAt already exists in the runner, ~lines 721-880), and at each
decision read (a) one snapshot and (b) 150 s aggregates from VISSIM's own evaluations (link evaluation segments, data collection
measurements -- the rule arms use 58 'RULE|...' detectors --, queue counters, node evaluation, signal changes), as the older
wu-link controller did ("far rates measured: link evaluation every 150 s updates G, g_fw, merge online").
The SDMPC is moving to the 31-cell METANET plant (plan: D:\\VISSIM-merge\\evidence\\SDMPC_N31_PLAN_20260923.md, which assumed the
per-second path); the 31-cell freeway state from a single snapshot was already shown equal to the per-second binning.

Code: D:\\VISSIM-merge\\sim3-n31 (branch claude/sdmpc-n31-20260924, = SDMPC with cap margin; READ-ONLY for you) -- same code as
D:\\VISSIM-merge\\sim3. Key files: evaluation\\controllers\\{lane_plant_observation.py, lane_plant_runtime.py, runtime_setup.py,
vissim_stackelberg_adapter.py (traffic_state_from_vissim, head observation consumers), lane_urban_runtime.py, lane_ramp_runtime.py,
lane_offramp_runtime.py, area_freeway_accounting.py, urban_flow_accounting.py, native_demand_forecast.py, sdmpc.py},
scripts\\run_real_world_stackelberg_controller.vbs, config diagnostics\\sdmpc_pfo_caps_20260922\\config_candidate_obs1.json.
A saved decision state to inspect: D:\\VISSIM_runs\\20260923_sdmpc\\sdmpc_lp_9000\\decisions_sdmpc_lp_9000\\state_000900.json and its
lane_observations\\ frames (read with python, never print whole files).

## HARD RULES
READ-ONLY everywhere (VISSIM runs and calibrations are live). Scratch only under
C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\obs150.
Cite file:line for every claim.
`

const MAP = { type: 'object', properties: {
  summary: { type: 'string' },
  quantities: { type: 'array', items: { type: 'object', properties: {
    name: { type: 'string' }, used_by: { type: 'string', description: 'which model/decision part consumes it, file:line' },
    current_source: { type: 'string' },
    class: { type: 'string', enum: ['snapshot', 'aggregate_150s', 'per_second_needed', 'unused_or_audit_only', 'unclear'] },
    proposed_source: { type: 'string', description: 'for snapshot/aggregate: exact VISSIM object/attribute/evaluation and how to read it at the decision' },
    notes: { type: 'string' } }, required: ['name', 'used_by', 'current_source', 'class', 'proposed_source', 'notes'] } },
  risks: { type: 'string' } },
  required: ['summary', 'quantities', 'risks'] }

const PARTS = [
  { key: 'lane-observer', prompt: `
## Your part: everything the lane-plant observer derives from per-second frames
Go through lane_plant_observation (snapshot fields: lane_group_dynamics, current_exit_labels, off_split_ratio, off_split_history,
frames, ramp_origin_tags, ...) and lane_plant_runtime (observe_live, initialize, ramp lane-arrival shares ~:352-356, port stocks,
cohorts) and list every quantity with its consumer in the SDMPC rollout. Classify each and propose the snapshot or 150 s aggregate
replacement. Pay special attention to anything that genuinely needs vehicle tracking (origin tags, cohorts) and whether the
31-cell plant (no lane groups) still consumes it.` },
  { key: 'urban-head', prompt: `
## Your part: the urban side and head observation
List everything the urban model / SDMPC uses from CollectHeadObservation, head windows, SealHeadSignalStates, queue counters,
signal readback, RW_SIGNAL_OBSERVATION, RW_QUEUE_COUNTER/WINDOW and the state JSON (traffic_state_from_vissim) at a decision,
with consumers. Classify each; for aggregates name the VISSIM evaluation (queue counters, data collection points on approaches,
node/link evaluation, signal changes) that can produce it at 150 s, whether the network already has those objects (check the v2
network D:\\VISSIM_runs\\20260923_stage1\\s31_v2nc\\prepared\\network\\baseline_s31_v2nc.inpx: queueCounters, dataCollectionPoints,
linkEvaluation settings), and why the head observer requires SimRes 1 (VBS ~6058-6069).` },
  { key: 'runner-freeway', prompt: `
## Your part: runner mode and freeway/ramp inputs for the 31-cell plant
(1) The runner: what RunStepwiseMode does per second that the SDMPC actually needs vs what is audit/logging; whether
RunEventContinuousMode (SimBreakAt at decision times) can serve the SDMPC at SimRes 10, and what must be captured at each break
(snapshot via GetMultiAttValues on vehicles, link/segment evaluation results via COM). (2) Freeway/ramp quantities the 31-cell plant
needs at a decision: cell density/speed (snapshot), ramp and connector stocks (snapshot), mainline source admitted rate and backlog
over the last 150 s (the plan's review item A1), off-ramp split ratios and ramp arrival rates (150 s aggregates from
link evaluation / data collection), meter and VSL states (readback). Name exact VISSIM attributes/evaluations and whether the
v2 network already records them.` },
]

phase('Map')
const maps = (await parallel(PARTS.map(p => () =>
  agent(CONTEXT + p.prompt, { label: 'map:' + p.key, phase: 'Map', schema: MAP }).then(r => r ? { key: p.key, map: r } : null)))).filter(Boolean)

phase('Design')
const design = await agent(CONTEXT + `
## Your job: the answer for the user, IN KOREAN
1. One table of every observation the SDMPC uses at a decision: 항목 | 쓰는 곳 | 지금 출처 | 분류(스냅샷 / 150초 집계 / 매초 추적 필요 /
   감사용·미사용) | 제안 출처(VISSIM 객체·속성·평가). Merge duplicates across the three maps; mark uncertain ones.
2. The items that truly need per-second tracking, why, and how to drop or approximate them (with the cost to fidelity).
3. The proposed 150 s observation design: runner mode (continuous at SimRes 10, break at decisions), what is read at each break,
   which VISSIM evaluations must be enabled in the network, changes to the adapter/observer, and how the 31-cell plant and the
   urban model are initialized from it.
4. Effort (per step) and risks; what it removes (per-second frames, SimRes-1 constraint) and what it costs.
Keep it clear and concise; the user wants to understand and decide.

Maps:
${JSON.stringify(maps, null, 1)}`, { label: 'design', phase: 'Design' })

return { design, maps }
