export const meta = {
  name: 'sc1001eb-joint-item-p0',
  description: 'Pre-checks for the joint SC1001 EB stop-line item (FW_W F12/F14 + batch-2 127 handling + F17 boundary forecast): VISSIM/plant facts, estimators, forecast and acceptance issues; synthesis of design options (no code)',
  phases: [
    { title: 'Facts' },
    { title: 'Synthesize' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/sc1001eb'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER DECISIONS (2026-10-01): (1) the SC1001 EB stop line (link 127; off-ramp drains 10491 from FW_W and 10481 from FW_E; urban W approach) is ONE joint item that merges FW_W proposal items F12 (stop-line physical capacity + shared pool) and F14 (10491 storage chain) with urban batch 2's 127 handling (U5 127 head-group budget, U8 off-ramp-vehicle category) and F17 (boundary forecast needed to judge), implemented on the v3c3 repin line BEFORE the rest of C3 v2; (2) the VISSIM network is the truth (FW_W lane 1 acts as a 3.4 km exit lane: all connectors lnChgDist 9999, route decision 1132 at 75.7 m) - the plant must reproduce it.
- Read first: ${SP}/fww-struct/FWW_STRUCT_PROPOSAL.md, FWW_STRUCT_CHECK.md (refutations: VISSIM SG2 saturated 36/36 windows, s ~1,633-1,702 at VISSIM green 48 s; '5th+ headway' estimator impossible with 5 s FZP; F14 inseparable from F12; G-F12-3 fails because of A1/F17; missing items: acceptance compression AFA:218 / rho_max 180 / v_min 5, 2b definition for bottleneck-bound cells), P_PLANT.md, S_STRUCTURE.md, V_VISSIM.md; batch 2 round-1 ${SP}/urban-b2/diag_c3/C3_DIAGNOSIS.md + C3_DIAGNOSIS_CHECK.md (U8 category: off-ramp vehicles wait 240-324 s on link 127; ~41-45 % of W-link vehicles at T+150 are off-ramp-origin; 127 budget binds 100 % of green). Round 2 (U7/U8) is running in ${SP}/urban-b2/diag_c3_r2 - read its outputs if present, do not wait for it.
- Data (READ-ONLY): v3c2 NC fit seeds D:/VISSIM_runs/20260930_v3c2/s{31,41,43,47,53}_v3c2nc (FZP, .sig/.lsa if present), EO D:/VISSIM_runs/20260930_v3c2/reports/nc_analysis/eo; v3c1 R-obs states D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31; plant code D:/VISSIM-merge/sim3-n31-v3c1 (deployed U1+U3) and D:/VISSIM-merge/sim3-n31-urban-b2 (C3 code, uncommitted; another workflow uses it - read only). Never s37/*_rm/59/61/67; seed notation with network prefix.
- HARD RULES: read-only everywhere; write only under ${OUT}. No code changes, no commits, no VISSIM start/kill, never modify D:/VISSIM-merge/frozen/*. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Heavy Python at BELOW_NORMAL, PYTHONHASHSEED=0, one heavy job at a time (other workflows and 4 VISSIM runs are active).
`
const A = { type: 'object', properties: { report_path: { type: 'string' }, findings: { type: 'array', items: { type: 'string' } }, open: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'findings', 'open'] }
const P = { type: 'object', properties: { report_path: { type: 'string' }, options: { type: 'string' }, user_decisions: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'options', 'user_decisions'] }

phase('Facts')
const facts = await parallel([
  () => agent(CTX + `
TASK F1 - STOP-LINE FACTS. VISSIM side (v3c2 fit seeds): SC1001 EB geometry (link 127 lanes, heads, signal groups SG2 lanes 1-2 to_E/to_S, SG5 lane 3 to_N), green definitions (VISSIM 48/27 s vs plant p3 45 / p4 24 s - align the definition), a FEASIBLE saturation-flow estimator with 5 s FZP (e.g. stop-line crossings per second of green in cycles whose queue at green start exceeds a declared threshold; state it before computing), discharge by origin (10491 / 10481 / urban), storage chain capacities (10491 connector, link 129, link 127), spillback events onto FW_W/FW_E. Plant side: how the deployed U1+U3 plant and the C3 plant (U4/U5/U6 in the b2 tree) represent these movements, capacities, LOR ports, budgets and which vehicles the observation projection assigns where (the U8 category). Write ${OUT}/F1_STOPLINE.md.`, { label: 'stopline-facts', phase: 'Facts', schema: A }),
  () => agent(CTX + `
TASK F2 - FORECAST + ACCEPTANCE. (a) F17: the A1 boundary forecast (source_boundary.py:37-59) holds the T entry rate across the horizon while a virtual backlog exists; quantify its effect on FW_W/FW_E with the plant (probe arms only in scratch), list design options (backlog as plant origin queue with schedule demand; observed entry-rate injection; Omega membership of origin queues) and their effect on C6 invariants and the Omega objective. (b) Acceptance compression: AFA:218 storage-based acceptance without wave-speed limit, rho_max 180 vs VISSIM lane-1 jam ~149 and cell means <= 74, v_min 5 - quantify how much they inflate blocked-section stocks (probe arms), and whether they must be fixed together with the stop-line item to pass its gates. (c) The 2b definition for bottleneck-bound cells (sustained discharge vs p95; Poisson null). Write ${OUT}/F2_FORECAST_ACCEPT.md.`, { label: 'forecast-accept', phase: 'Facts', schema: A }),
])

phase('Synthesize')
const syn = await agent(CTX + `
TASK: SYNTHESIS (no code). Read ${facts.map(f => f ? f.report_path : '(failed)').join(', ')} and the round-2 batch-2 outputs if present. Write ${OUT}/SC1001EB_OPTIONS.md (Korean, 6-line summary first): the joint item's scope and 2-3 design options (e.g. shared stop-line pool with origin-tagged members and a storage chain 10491->129->127; value-level fix; staged), each with what changes (keys, modules, interaction with U4/U5/U8 and with the v3c3 repin), the declared estimators, pre-registered gates (plant one-step/450 s/long rollouts vs VISSIM, 10491 flow, FW_W jam, fictitious SC1001 lever removed, G-SC109 untouched, key-absent identity), what must come along (F17, acceptance compression), risks, effort, and the user decisions. Do not pick final numbers; this is the options paper to bring to the user.`, { label: 'options', phase: 'Synthesize', schema: P })

return { facts, syn }
