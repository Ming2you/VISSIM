export const meta = {
  name: 'static-checks-inlet-and-cell-fd',
  description: 'Pre-declare, then run two static plant checks on v3c1 (2a inlet cell-0 bias, 2b per-cell FD capacity >= VISSIM throughput p95), then verify independently',
  phases: [
    { title: 'Predeclare' },
    { title: 'Compute' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/static_checks'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- Origin: review of the user's codex commit 7ecace6 (${SP}/codex7ec_review/REVIEW.md §5 steps 2a/2b, items #17/#18; REVIEW_CHECK.md). User decision 2026-09-30: do NOT import codex values; RUN the two static checks now; criteria as proposed in REVIEW.md:137-138 are accepted (freeze them now, before any data is computed).
  * 2a INLET CELL CHECK (FW_E cell 0, 0-526 m, input 1098): congested-frame share (cell-0 mean speed < 60 km/h) and the one-step (150 s) plant inventory bias of cell 0, plus 0-40 m detector/FZP speed vs the plant's virtual upstream speed v_free (area_freeway_accounting.py:365). Rule: if in >= 3 of 5 fit seeds BOTH congested share >= 10 % AND |bias| >= 15 veh -> propose a new inlet-boundary F item; otherwise close. If the one-step bias can only be computed for some seeds (plant replays need decision states; on v3c1 only the R-obs s31 run has them), pre-declare how the rule is applied (e.g. the AND fails if congestion share < 10 % in >= 3/5 seeds regardless of bias; if congestion passes but bias is only available for < 3 seeds -> 'insufficient data', not 'open').
  * 2b PER-CELL FD CAPACITY GATE: for every one of the 31 physical cells in BOTH directions, the deployed v3c1 plant's maximum flow (lambda * rho_c * v_f * exp(-1/a) with the effective parameters actually used: per-segment v_free, lanes, lane-class rho_c/a, direction multipliers applied ONCE, VSL law at 110, plus any explicit capacity cap the plant flow computation applies - use the binding minimum) must be >= the VISSIM cell throughput p95 from the 5 v3c1 NC fit seeds. Intended bottlenecks are excluded only if listed BEFORE computing, with reasons (there may be none today because F3/F4 are not implemented). Pass = 0 violating cells.
- Code (READ-ONLY): D:/VISSIM-merge/sim3-n31-v3c1 (branch claude/repin-v3c1-20260928 @ 9ed2ef0 = deployed v3c1 plant; tuning diagnostics/sdmpc_n31_20260924/config_n31_v2.json; parameters.json, geometry.json with the 31-cell refined partition sha 9769b3a4). Worklog with FW_E structural diagnosis: diagnostics/worklog_20260927_29/ (FWE_STRUCT_PROPOSAL.md, P0_REPORT.md). Existing FZP scan tooling: ${SP}/v3c1-p10/pair/pair_scan.py, ${SP}/hybrid/ttt3000/hybrid_ttt3000.py (drop the SDMPC runner's 0.10 s frame when scanning R-obs FZPs), N1/N1F scripts under D:/VISSIM_runs/20260927_n1_vsl/scripts (FZP passes, B1/B2 discharge).
- Data (READ-ONLY): v3c1 NC fit seeds D:/VISSIM_runs/20260927_v3c1/s31_v3c1nc, s41_v3c1nc, s43_v3c1nc, s47_v3c1nc, s53_v3c1nc; R-obs (FZP byte-identical to NC s31 except the 0.10 s frame, 61 decision states) D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31. NEVER open s37 (sealed held-out) or any *_rm folders, nor seeds 59/61/67. Seed notation rule adopted today: cite runs with a network prefix (v3c1-s31, v3b-s31, 64cf-s61); never use the codex 64cf-s59/s61/s67 numbers in our selection/calibration.
- HARD RULES: read-only on all worktrees and run folders; write only under ${OUT}. Do not start/kill VISSIM or cscript; do not modify D:/VISSIM-merge/frozen/*. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Heavy Python (FZP streaming, plant replays) at BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_NUM_THREADS<=4; two other workflows run concurrently, so run one heavy job at a time.
`
const P_SCHEMA = { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, data_availability: { type: 'string' }, intended_bottlenecks: { type: 'string' } }, required: ['path', 'sha256', 'data_availability', 'intended_bottlenecks'] }
const C_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, verdict: { type: 'string' }, numbers: { type: 'string' }, deviations_from_predeclaration: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'verdict', 'numbers', 'deviations_from_predeclaration'] }
const V_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Predeclare')
const pre = await agent(CTX + `
YOUR STAGE: PRE-DECLARATION ONLY (do not compute any outcome: no speeds, biases, throughputs or capacities yet; only check that files exist and schemas are readable).
Write ${OUT}/PREDECLARATION.md freezing, for 2a and 2b: data sources per seed (paths), time window (e.g. t >= 900 s or full run - choose and justify), cell geometry (31-cell physical partition bounds and FW_E/FW_W chainage mapping; link/pos -> cell), exact formulas (congested share, one-step inventory bias definition = plant 150 s prediction of cell-0 stock minus VISSIM stock at T+150, sign convention; throughput = Edie flow per cell per 150 s bin as primary, 300 s as secondary; p95 over bins), the plant capacity formula and every parameter source (file:line/key), how multi-lane classes / lane drops / merge cells are handled, the list of intended bottlenecks with reasons (possibly empty), decision rules including the partial-data rule for 2a, and what is reported descriptively. Record the sha256 of PREDECLARATION.md in ${OUT}/PREDECLARATION.sha256 and in your return value. Timestamp it.`, { label: 'predeclare', phase: 'Predeclare', schema: P_SCHEMA })

if (!pre) { return { stopped: 'predeclaration failed' } }

phase('Compute')
const [a2, b2] = await parallel([
  () => agent(CTX + `
YOUR STAGE: COMPUTE CHECK 2a exactly as frozen in ${pre.path} (sha ${pre.sha256}; verify the sha before starting and do not edit that file). Outputs under ${OUT}/2a/. Report per seed: cell-0 congested share, 0-40 m speed distribution vs v_free, one-step inventory bias (mean, MAE, n) where computable, and the verdict under the frozen rule. Any deviation from the predeclaration must be listed with a reason. Write ${OUT}/2a/CHECK_2A.md (Korean, 5-line summary first).`, { label: 'check-2a', phase: 'Compute', schema: C_SCHEMA }),
  () => agent(CTX + `
YOUR STAGE: COMPUTE CHECK 2b exactly as frozen in ${pre.path} (sha ${pre.sha256}; verify the sha before starting and do not edit that file). Outputs under ${OUT}/2b/. Report a table for all 62 cells (direction, cell, lanes, plant capacity with the binding term, VISSIM throughput p95 (150 s) per seed and pooled, p95 300 s, ratio plant/p95, violation flag), the verdict (number of violating cells, excluding pre-listed intended bottlenecks), and for each violation which plant term causes it (FD shape a, rho_c, v_free, lane count, multiplier, explicit cap) and which planned F item (F1/F2/F3/F4/F8, see FWE_STRUCT_PROPOSAL.md) would touch it, or 'new'. Also flag cells where plant capacity exceeds p95 by > 30 % (descriptive only). Write ${OUT}/2b/CHECK_2B.md (Korean, 5-line summary first).`, { label: 'check-2b', phase: 'Compute', schema: C_SCHEMA }),
])

phase('Verify')
const ver = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only; own code under ${OUT}/verify). Inputs: ${pre.path}, ${a2 ? a2.report_path : '(2a failed)'}, ${b2 ? b2.report_path : '(2b failed)'}. Check the predeclaration sha is unchanged and that its timestamp precedes the compute outputs. Recompute independently: 2b plant capacity for all 62 cells from the source parameters (own formula implementation, check multiplier applied once) and VISSIM throughput p95 for at least 2 seeds; 2a congested share for at least 2 seeds and the bias for 5 states. Confirm the verdicts follow the frozen rules. Write ${OUT}/VERIFY.md with confirmed / problems.`, { label: 'verify', phase: 'Verify', schema: V_SCHEMA })

return { pre, a2, b2, ver }
