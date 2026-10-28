export const meta = {
  name: 'v3c1-sc1004w-offramp-diagnosis',
  description: 'Diagnose why the off-ramp region around SC1004 W grew on v3c (+43.5) and v3c1 (+76.5 veh.h, 2.05 sd, all seeds positive) and why links 71 and 84 exceeded the G4 lane-change-removal baseline, and attribute it (or not) to specific routing edits V1, V3-V7; read-only',
  phases: [
    { title: 'Diagnose', detail: 'FZP flow/queue comparison and attribution' },
    { title: 'Verify', detail: 'adversarial check' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = R + '/net-v3c/v3c1/sc1004w'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line. READ-ONLY: no network edits, no code changes, no git, never start/kill VISSIM/cscript, write only under ${OUT}/.
- Networks: v3b (base, D:/VISSIM_runs/20260925_v3b/source), v3c (= v3b + decisions 1160-1168, D:/VISSIM_runs/20260927_v3c), v3c1 (= v3c minus 1161, D:/VISSIM_runs/20260927_v3c1; items V1 SC109 W, V3 SC5 S, V4 SC16 N, V5 SC1 N, V6 SC101 S, V7 SC104 S_SC106; see D:/VISSIM_runs/20260927_v3c1/v3c1_edit_receipt.json and ${R}/net-v3c/V3C_PROPOSAL.md). NC runs (FZP 5 s frames, lane level, .err, stage-1 scan analysis/scan.json): v3b D:/VISSIM_runs/20260925_v3b/s{31,41,43,47,53}_v3bnc, v3c D:/VISSIM_runs/20260927_v3c/s{31,41,43}_v3cnc, v3c1 D:/VISSIM_runs/20260927_v3c1/s{31,41,43}_v3c1nc (s47/s53 v3c1 are running now — do not read them until their run.json says completed; they will be judged separately). Never open s37, RM arms, sealed seeds.
- Gate reports: D:/VISSIM_runs/20260927_v3c1/reports/gates_batch1/GATES_BATCH1.md (§7: non-item G4 exceedances link 71 SC1004 W s41 116 > 102 and link 84 SC2001 E_SC2002 s43 12 > 9; G5 offramp +76.5 veh.h = 2.05 sd, concentrated at off-ramps 10638/10643 and links 70/126 near SC1004 W; inflow ratios unchanged per the evaluator, so the discharge side is suspected), its support/ g4_err.json g5_scan.json, and the v3c batch-1 reports D:/VISSIM_runs/20260927_v3c/reports/gates_batch1/ (offramp +43.5, 1.17 sd). Independent verification ${R}/net-v3c/v3c1/gates/VERIFY_BATCH1.md.
- User decision 2026-09-28: keep V1, V3-V7, re-judge on 5 seeds, and diagnose this in parallel; attribute to an item only with direct evidence.
- Stream FZPs one at a time at BELOW_NORMAL (typed ctypes, read back GetPriorityClass). Other jobs run concurrently (2 VISSIM runs, N1 analysis, urban batch-2 design): keep CPU modest.
`
const DG = { type: 'object', properties: { verdict_ko: { type: 'string' }, evidence_ko: { type: 'string' }, attribution_ko: { type: 'string' }, options_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict_ko', 'evidence_ko', 'attribution_ko', 'options_ko'] }
phase('Diagnose')
const d = await agent(`${COMMON}\nTASK: (1) localise the extra time around SC1004 W per seed and per 150 s bin (off-ramp links/connectors 10638, 10643, 70, 126, 71 and their downstream), separate arrival (inflow volume and timing) from discharge (SC1004 W approach discharge per green, downstream blocking, lane use, lane-change removals on 71), (2) trace which OD/route flows through SC1004 and its downstream changed between v3b and v3c1 (vehicle-level: which inputs/decisions/routes the extra vehicles on 71/70/126 come from, and which movements at SC1004 and downstream signals gained or lost volume), and whether any of V1, V3-V7 (directly or via rerouted volumes) plausibly causes it; do the same for link 84 (SC2001 E_SC2002); (3) compare against seed-to-seed variability of v3b NC (5 seeds) to say whether the shift is distinguishable from noise; (4) list options (none / specific item revert / wait for 5 seeds) with the evidence strength. Write ${OUT}/SC1004W_DIAG.md.`, { label: 'diagnose', phase: 'Diagnose', schema: DG })
phase('Verify')
const v = await agent(`${COMMON}\nDiagnosis: ${JSON.stringify(d)}\nTASK: adversarial review — re-check at least 5 numbers yourself from the FZP/.err/scan files, check causal claims have direct evidence (not correlation across 3 seeds), look for alternative explanations (chaotic divergence after the first difference, FW_W off-ramp demand changes, SC1004 signal timing is native in NC), and revise ${OUT}/SC1004W_DIAG.md in place with an appendix of issues and resolutions. Return the final verdict.`, { label: 'verify', phase: 'Verify', schema: DG })
return { d, v }
