export const meta = {
  name: 'fww-structural-diagnosis',
  description: 'Diagnose why the plant mis-models FW_W (weaving bottleneck cells 7-10, upstream capacity shortfall, long-horizon fictitious jam) using v3c2 NC data and plant replays; propose structural fixes; adversarial check',
  phases: [
    { title: 'Analyze' },
    { title: 'Propose' },
    { title: 'Check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/fww-struct'
const V2 = 'D:/VISSIM_runs/20260930_v3c2'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER DECISION (2026-10-01): diagnose FW_W STRUCTURE first (no code changes until the proposal is approved), like the earlier FW_E structural diagnosis (D:/VISSIM-merge/sim3-n31-v3c1/diagnostics/worklog_20260927_29/02_fwe/FWE_STRUCT_PROPOSAL.md, P0_REPORT.md - read them for method and for which FW_E items F1-F9 might also apply to FW_W). F10 is on hold.
- Evidence so far:
  * Static check 2b on v3c2 (${V2}/reports/nc_analysis/STATIC_CHECKS_V3C2.md): FW_W cells 0-7 plant capacity < VISSIM throughput p95 (direction rho_c multiplier 0.68; cell 0 also v_free), cells 11-15 only on short peaks. FW_W cell 0 congested 91-100 % of the time; 0-40 m speed 15-21 km/h; input 1099 entry queue non-empty ~99 %; v3c2 analysis says FW_W entry congestion is spillback from a downstream weaving-section queue (GATES_AND_COMPARISON.md).
  * F11 attempt (${SP}/f10f11/EVALUATION.md, VERIFY.md): raising rho_c of FW_W cells 0-6 to 24.58 (congested-branch speed fit) passed the capacity gate and LOSO but made one-step and 450 s predictions much worse (R1 MAE 61.8 -> 97.9, 450 s 70 -> 177; weaving zone W 8.6 -> 18.7): front cells empty, vehicles pile up before the bottleneck (cells 4-7). Not overfitting (LOSO rho_c same).
  * Terminal-cost study (${SP}/termcost/RESULTS.md, VERIFY.md P1, BUILD N9): in long plant rollouts FW_W holds 1,569-1,956 veh at T+1800 and ~2,100 at T+3600 vs VISSIM 595-673; from 2700 to 9000 s plant FW_W 822 -> 2,215 and origin queue 0 -> 1,674 while VISSIM clears after 4,650 s. Urban off-ramp release (SC1001 p3) 'wins' in the plant by draining this fictitious FW_W jam.
  * Deployed FW_W plant parameters: v x1.12, rho_c x0.68, delta 0 (parameters.json 8e4f6047 in the v3c1 tree); 31-cell physical partition (FW_W merge/diverge cells per ${SP}/codex7ec_review/R2_CONFIG_CODE.md); FW_W meters 10480/10482/10646/10644; off-ramps OR_D_W1 10479 (link 26 -> 125), OR_D_W2 10491 (26 -> 129), OR_F_W1 10645 (120 -> 123), OR_F_W2 10638 (120 -> 70).
- Data (READ-ONLY): v3c2 NC fit seeds ${V2}/s{31,41,43,47,53}_v3c2nc/run (FZP), EO extraction ${V2}/reports/nc_analysis/eo, static-check code copies ${V2}/reports/nc_analysis/static_checks_v3c2 (P-comp plant harness incl. FW_W mode); v3c1 R-obs decision states D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31 and the termcost harness ${SP}/termcost/harness for long plant rollouts; plant code in D:/VISSIM-merge/sim3-n31-v3c1 (HEAD 9ed2ef0, read-only). Never s37 or *_rm, no 59/61/67, no 64cf-s59/s61/s67 numbers. Seed notation with network prefix.
- HARD RULES: read-only everywhere; write only under ${OUT}. No code changes, no commits, no VISSIM start/kill, never modify D:/VISSIM-merge/frozen/*. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Heavy Python at BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_NUM_THREADS<=4; other workflows run concurrently.
`
const A = { type: 'object', properties: { report_path: { type: 'string' }, findings: { type: 'array', items: { type: 'string' } }, open: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'findings', 'open'] }
const P = { type: 'object', properties: { report_path: { type: 'string' }, items: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, what: { type: 'string' }, evidence: { type: 'string' }, test: { type: 'string' } }, required: ['id', 'what', 'evidence', 'test'] } }, user_decisions: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'items', 'user_decisions'] }
const C = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, refuted_or_weak: { type: 'array', items: { type: 'string' } }, missing: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'refuted_or_weak', 'missing'] }

phase('Analyze')
const reads = await parallel([
  () => agent(CTX + `
TASK V - VISSIM SIDE (FZP v3c2 fit seeds): characterise FW_W traffic physically. Map FW_W links/connectors to the 31 cells (chainage), lanes per cell (through vs auxiliary/weaving lanes), on-ramp merges and off-ramp diverges. Find the active bottleneck(s): where queues start (speed-time by cell and by lane), onset times, discharge rate downstream of the queue head (symmetric definitions as in the capacity-drop study), lane-level behaviour in the weaving section (lane changes on/off ramp, which lane blocks, off-ramp 10479/10491 queue spillback onto the mainline?), how far the queue reaches (to the entry?), and when/how it clears. Compare seeds. Write ${OUT}/V_VISSIM.md.`, { label: 'vissim-side', phase: 'Analyze', schema: A }),
  () => agent(CTX + `
TASK P - PLANT SIDE: (1) one-step and 450 s plant predictions for FW_W by cell on v3c2 NC fit seeds with the P-comp harness (bias/MAE, where stock appears/disappears, speed errors), term decomposition of the METANET speed update in the bottleneck cells (relaxation, convection, anticipation, merge/diverge terms, lane drop phi) and flows at cell boundaries vs VISSIM; (2) long rollouts (termcost harness, v3c1 R-obs states e.g. 900, 2700, 4950) to locate where the fictitious FW_W jam forms and why it never clears (discharge cap? off-ramp exit capacity/blocking? boundary/ramp arrival forecast held at T values? origin queue logic?), with the plant's off-ramp and on-ramp flows vs VISSIM. Write ${OUT}/P_PLANT.md.`, { label: 'plant-side', phase: 'Analyze', schema: A }),
  () => agent(CTX + `
TASK S - STRUCTURE/CODE AUDIT: how the deployed plant represents FW_W: parameters and where they came from (v x1.12, rho_c x0.68, delta 0 - which fit produced them and on what data/network), lane counts per cell vs VISSIM (auxiliary lanes, weaving lanes), diverge handling (off-ramp capacity, occupancy_lane_loss off in port profile, off-ramp storage/blocking), merge handling (gap-acceptance receiving nodes for FW_W meters?), any FW_E-only structures (B1 node, anticipation fixes) that FW_W lacks, and the boundary/forecast logic that could keep FW_W loaded beyond the forecast window. List candidate structural defects with file:line. Write ${OUT}/S_STRUCTURE.md.`, { label: 'structure', phase: 'Analyze', schema: A }),
])

phase('Propose')
const prop = await agent(CTX + `
TASK: SYNTHESIS + PROPOSAL. Read ${reads.map(r => r ? r.report_path : '(failed)').join(', ')} and spot-check key claims. Write ${OUT}/FWW_STRUCT_PROPOSAL.md (Korean, 6-line summary first): the FW_W mechanism in VISSIM vs the plant, ranked structural fix items (F12, F13, ...) each with what changes, the evidence, expected effect on 2b/one-step/450 s/long-horizon divergence, risk, and a pre-declared test; which FW_E items (F1-F9) also apply to FW_W; what NOT to do (e.g. capacity coefficients alone - F11 showed harm); and the user decisions needed. Keep the principle: structure first, few physical parameters, values from declared estimators.`, { label: 'propose', phase: 'Propose', schema: P })

phase('Check')
const chk = await agent(CTX + `
TASK: ADVERSARIAL CHECK of ${prop ? prop.report_path : '(proposal failed)'} and the three analysis reports. Recompute key numbers independently (bottleneck location/onset, discharge rates, plant bias by cell, long-rollout jam growth), test alternative explanations (forecast held values, origin/boundary logic, measurement definitions, seed dependence), and mark each proposed item confirmed / weak / refuted. Write ${OUT}/FWW_STRUCT_CHECK.md.`, { label: 'check', phase: 'Check', schema: C })

return { reads, prop, chk }
