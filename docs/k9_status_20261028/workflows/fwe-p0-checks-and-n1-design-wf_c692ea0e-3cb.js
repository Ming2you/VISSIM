export const meta = {
  name: 'fwe-p0-checks-and-n1-design',
  description: 'FW_E proposal P0 pre-checks (no code changes; offline decision replays after the running cross replay finishes) and the design of the native VSL step experiment N1 (design only, no VISSIM launch)',
  phases: [
    { title: 'Check', detail: 'P0 checks in three groups + N1 design' },
    { title: 'Report', detail: 'P0_REPORT.md and N1_DESIGN.md' },
    { title: 'Critique', detail: 'adversarial review and revision' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = R + '/fwe-struct/p0'
const COMMON = `
CONTEXT (absolute paths). Korean text; mark numbers [실행]/[읽음]/[추론]/[미확인]; cite file:line.
- The FW_E structural proposal is ${R}/fwe-struct/FWE_STRUCT_PROPOSAL.md (read §0, §2, §3 P0/V0/F1-F9/J1, §6, §7 first). User decisions 2026-09-27: P0 approved (no code changes); VSL handling = F6 option (C): re-fit the VSL response from a native VSL step experiment N1 (design first, VISSIM launch needs a later approval); J1 agreed (FW_E closed-loop effects judged only from >=3 same-seed paired comparisons); the order of FW_E fixes vs urban batch 2 vs network v3c is decided later.
- SAFETY: no code or config changes anywhere; no git; never start/kill VISSIM or cscript; never write under D:/VISSIM_runs/* or D:/VISSIM-merge/*; write only under ${OUT}/. Offline decision replays with D:/VISSIM-merge/sim3-n31/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py prepare + replay_decision_n31.ps1 -ReplayDir <dir under ${OUT}> -SkipFreezeVerify are allowed (they are offline adapter runs, not the forbidden watchdog/cscript/ps1 *tests*). BUT another job (cross replay, ${R}/xreplay/orchestrate.log) is using ~18 of 20 cores until the line ALL_DONE appears: before any decision replay, wait (poll the log every few minutes) until ALL_DONE is present, then run replays ONE at a time at BELOW_NORMAL priority with NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_p0. Harness runs (fwe-struct scripts, rmcal-v3b/harness) one process at a time, threads 1, BELOW_NORMAL.
- Data rules: fit seeds 31/41/43/47/53 only; s37 NC, v3b RM arms and sealed seeds 59/61/67 are not used for anything. S0e/S1 closed-loop decisions (D:/VISSIM_runs/20260925_sdmpc31_v3b/{sdmpc31_v3b_s31e,sdmpc31_v3b_b1u13_s31}) may be replayed for P0-3/5/6 (descriptive).
- Deployed code: D:/VISSIM-merge/sim3-n31 (886a014); frozen tree used by S0e D:/VISSIM-merge/frozen/sdmpc31_886a014a_202609260935.
`
const RES = { type: 'object', properties: { results_ko: { type: 'string' }, open_items_ko: { type: 'string' }, evidence_files: { type: 'array', items: { type: 'string' } } }, required: ['results_ko'] }
const GROUPS = [
  { key: 'code', prompt: 'DO P0-1 (LIVE path via scripts/resolve_live_controller.py and scripts/whose_code.py for the listed symbols), P0-2 (two-way table: harness-only vs deployed-only vs shared structure, with file:line), P0-7 (delta_merge 1/L term budget at cells 10/12/21/23, like terms.py; where delta=1.0 was fitted) and P0-8 (does state.urban_link_storage of the OR_F_E storage link move inside the plant horizon; metanet.py:197-200 lane profile start with 4 lanes vs 3-lane cells). Mostly code reading and harness/T4 runs; no decision replays needed.' },
  { key: 'replay', prompt: 'DO P0-3 (V0 paths a-e: which are viable given joint_owner_game.py:146, sdmpc.py:337-341/391, previous committed action; note the user chose VSL option C, so V0 is now only a fallback for closed-loop runs before the refit — still report viability), P0-5 (AD unit tests listed in the proposal §2.4 that are pure python tests — run them if they do not touch ps1/cscript/watchdog; and T5 decision replays of 5 S0e decisions to record wall time, discrete comparison counts, exact ties) and P0-6 (how often and how much the RM_C10681/10484 gap-acceptance receiving nodes bind in the deployed path, from the replays). Wait for ALL_DONE in the cross-replay log before replays (see SAFETY).' },
  { key: 'vissim', prompt: 'DO P0-4 (lane-1 discrepancy re-check: one table from the same FZP scan, 100 m x lane, 30 s, 1800-4500 s, 3.0-5.3 km: per-lane speed and exit-bound share, fit seeds; decide whether F3b should open) and P0-9 (B2 T1 regressions on fit5: (i) q23 ~ m10484 + m10490 (10490 weaves with the 10483 direct exit in cell 21), (ii) a hazard model of B2 onset from the density and ramp inflow in the 150 s windows before onset; state the weak identification with 4 breakdown events).' },
  { key: 'n1', prompt: 'DESIGN the native VSL step experiment N1 (design only; no launch). Goal: re-fit the plant VSL response (Carlson FD modifiers A, E in freeway_fd.py:39-46, reference_config vsl_fd_response) or show another law is needed, from v3b VISSIM data: compliant free-flow speed per command, saturation discharge at B1 (10681 merge) / M / B2 under 110/100/90/80 (and whether 50-70 are needed), capacity drop and breakdown timing. Find and reuse existing infrastructure for native runs with scripted VSL commands (the user VSL-handoff/fix90 experiment: memory C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory/vissim-vsl-handoff-repro-20260924.md and vissim-vsl-sign-zones.md; fast_nc_run.ps1; run_sdmpc_n31.ps1 with a scripted/fixed controller; how VSL DSDs are written) and state exactly which tool would launch it and whether a small code/tool change is needed. Specify: seeds (fit seeds only, paired with the existing v3b NC of the same seed so the run is FZP-identical until the first step), zones (4 sign zones per direction, FW_E), step schedule and durations (steps long enough to reach a steady state; avoid confounding with the natural B2 breakdown times 1410-2460 s of fit seeds), which levels, measurement windows and estimators, how many runs (<=4 VISSIM at once, each 9000 s about 8 h), the fitting procedure and a held-out check inside fit seeds, what would falsify Carlson, and what else the data would serve (F4 discharge law?). Note the interaction with a possible network change v3c (urban routing at SC109; FW_E physics should be unaffected, but check which ramp demands v3c could change).' },
]
phase('Check')
const res = await parallel(GROUPS.map(g => () => agent(`${COMMON}\n${g.prompt}\nReturn results with numbers and evidence files.`, { label: `p0:${g.key}`, phase: 'Check', schema: RES })))

phase('Report')
const REP = { type: 'object', properties: { p0_path: { type: 'string' }, n1_path: { type: 'string' }, summary_ko: { type: 'string' } }, required: ['p0_path', 'n1_path', 'summary_ko'] }
const rep = await agent(`${COMMON}
Results: ${JSON.stringify(res)}
TASK: write (1) ${OUT}/P0_REPORT.md: per P0 item the result, what it decides in the proposal (V0 path, F2 option c, F3b, F4/F5 porting scope, F7 feasibility, F9 design), and the updated list of user decisions (proposal §7) with recommendations; (2) ${OUT}/N1_DESIGN.md: the N1 experiment for approval (runs, seeds, schedule, tools and any needed tool change, estimators, fitting and falsification, wall time, risks). Korean.`, { label: 'report', phase: 'Report', schema: REP })

phase('Critique')
const crit = await agent(`${COMMON}
Report: ${JSON.stringify(rep)}
Adversarial review: re-check at least 5 numbers, check every conclusion follows from the evidence, check N1 is identifiable (steady states, confounding with natural breakdowns, pairing with NC, enough samples per level), that it uses fit seeds only, and that the launch plan respects the VISSIM rules (WMI detached, <=4 concurrent, no global kill). Revise both files in place and append an appendix of issues and resolutions. Return the final summary.`, { label: 'critique', phase: 'Critique', schema: REP })
return { res, rep, crit }
