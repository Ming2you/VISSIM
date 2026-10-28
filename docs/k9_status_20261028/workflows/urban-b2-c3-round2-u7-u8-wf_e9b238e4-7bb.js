export const meta = {
  name: 'urban-b2-c3-round2-u7-u8',
  description: 'Second C3 decomposition focused on U7 (SC1004 S arrival seeds / projection composition) and U8 (off-ramp vehicles on link 127 category), then C3 v2 proposal and adversarial check',
  phases: [
    { title: 'U7' },
    { title: 'U8' },
    { title: 'Propose' },
    { title: 'Check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const B = SP + '/urban-b2'
const OUT = B + '/diag_c3_r2'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- Urban batch 2 (v3b network), worktree W = D:/VISSIM-merge/sim3-n31-urban-b2 (branch claude/urban-batch2-20260928, all changes uncommitted; current diff sha a2dbc0e8 after the C6 levers). Plan ${B}/BATCH2_PLAN.md; stage reports ${B}/impl/STAGE0-7.md, STAGE3-7_FIX.md, STAGE3c_C6_LEVERS.md; round-1 diagnosis ${B}/diag_c3/C3_DIAGNOSIS.md and its adversarial check ${B}/diag_c3/C3_DIAGNOSIS_CHECK.md (READ BOTH FIRST); harness ${B}/harness; R-obs-b states and stage-7 captures as in STAGE7.md.
- USER DECISIONS (2026-10-01): C3 failure stays confirmed; do a SECOND decomposition focused on the real roots found by the check: U7 and U8. Adopt F2 (U4 value rule = saturation rate including start-up loss, s_from_green_start; check showed G-SC109 holds). DROP F1 (approach FIFO; its SC1004|S mechanism was refuted and it breaks G-SC109: all six G-SC109 states have SC109|W stock >= 80, W->E cap 5700.6 -> 1424) and DROP F4 (U5 request-proportional; moves error into G6-7). The definition questions (T3 transit inclusion, G-U5-127 category, G-v3b (d) counterpart, three-path criterion, G6-3) are collected AFTER this round.
- Known facts from the check: SC1004|S error is not approach FIFO: N and E vehicles pass the 2.66 km link at free-flow time; only W on dedicated lane 4 stops 541.7 s; the model's arrival seeds (+15/+105 s, adapter:5425-5427, :10238-10313) and projection composition (W 64.2 veh projected as queue 9.2 + beta-split storage) are the suspects; o1[in_SC1004_S] = 0.0 in all arms. SC1001 W (link 127): off-ramp vehicles spend 10-20 s on the connector then wait 240-324 s on link 127; at T+150 about 85 vehicles (41-45 %) on the W link are off-ramp-origin; observation counts them as W approach storage while the model holds them in LOR ports (U8 category mismatch). 127 budget binds 100 % of green; total discharge 61.2 vs FZP 55.5 (F2 gives 56.8).
- HARD RULES: code changes only as harness in-memory patches (attribution arms) unless an item is explicitly declared as a C3 v2 code proposal (then describe, do not commit). No commits, no push. Read-only on run folders; never modify D:/VISSIM-merge/frozen/*; do not touch other worktrees (sim3-n31-v3c1, sim3-n31-f10f11, sim3-n31-termcost, sim3-n31-hybrid). Do not start/kill VISSIM or cscript. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 data. Replays one at a time, BELOW_NORMAL, PYTHONHASHSEED=0. Seed notation with network prefix (v3b-s31).
`
const S = { type: 'object', properties: { report_path: { type: 'string' }, findings: { type: 'array', items: { type: 'string' } }, open: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'findings', 'open'] }
const P = { type: 'object', properties: { report_path: { type: 'string' }, proposal: { type: 'string' }, user_decisions: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'proposal', 'user_decisions'] }
const C = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, refuted_or_weak: { type: 'array', items: { type: 'string' } }, missing: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'refuted_or_weak', 'missing'] }

phase('U7')
const u7 = await agent(CTX + `
YOUR TASK: U7 DECOMPOSITION. (1) Read the adapter's arrival-seed / travel-time logic for urban approaches (adapter:5425-5427, :10238-10313 and whatever sets the +15/+105 s seeds) and the projection that splits observed approach vehicles into queue vs storage (why SC1004|S W 64.2 veh becomes queue 9.2 + beta-split storage; why o1[in_SC1004_S] = 0). (2) Build attribution arms as harness patches on C3 (and on U1+U3 for reference): U7a link-length / observed-speed based arrival time; U7b lane-based projection (vehicles on a dedicated-lane stop line assigned to that movement's queue); U7a+U7b. (3) Measure on R-obs-b states (same states/tools as stage 7): G0 T3 A1/A2/A3/B1/C (batch-1 and transit-included), per-approach contributions (SC1004|S, SC105|W_SC1003, SC107|W_SC1004 physical approach sum, SC11|E_SC12), G6, G-SC109 (must stay PASS), boundary allocation binding 0. (4) Say which U7 variant is structurally right (evidence from FZP vehicle trajectories) and its effect size with CIs. Write ${OUT}/U7.md.`, { label: 'u7', phase: 'U7', schema: S })

phase('U8')
const u8 = await agent(CTX + `
YOUR TASK: U8 DECOMPOSITION (after U7; U7 report: ${u7 ? u7.report_path : '(U7 failed)'}). (1) Pin down where off-ramp-origin vehicles on link 127 are counted in the observation projection vs the model (LOR ports 10491/10481, W approach queue/storage, U5 127 budget members), with FZP evidence per state. (2) Design category alignment options: U8a observation side (count off-ramp-origin vehicles on 127 into the port/off-ramp member stocks), U8b model side (hold them on 127 as members of the 127 head group with origin tags), and say which keeps vehicle conservation and U5 budget semantics. (3) Build harness arms (C3+F2, C3+F2+U8a/b, with and without the best U7 variant) and measure G-v3b (a) SC1001 W MAE vs persistence, G-U5-127 (a)(b), G6-7, G6-5, G0 A1 (both definitions), G-SC109. Write ${OUT}/U8.md.`, { label: 'u8', phase: 'U8', schema: S })

phase('Propose')
const prop = await agent(CTX + `
YOUR TASK: C3 v2 PROPOSAL (round 2). Inputs: ${u7 ? u7.report_path : '-'}, ${u8 ? u8.report_path : '-'}, round-1 diagnosis and check. Produce ${OUT}/C3V2_PROPOSAL.md: the C3 v2 bundle (C3 + F2 + chosen U7/U8 items; F1/F4 dropped) with what changes in code/evidence, expected effect per gate with the evidence and CIs, risks to G-SC109 and key-absent identity, what remains failing and why, and a pre-registration draft (the 14 gates and thresholds unchanged; list separately the definition questions the user must decide before the re-gate: T3 transit inclusion, G-U5-127 category, G-v3b (d) counterpart, three-path 0.013 criterion (U1+U3 also fails it), G6-3 noise-level). Also note what must change when batch 2 later moves from v3b to v3c2 (re-derive U4 table / U5 contract / U6 evidence on v3c2 NC fit seeds).`, { label: 'propose', phase: 'Propose', schema: P })

phase('Check')
const chk = await agent(CTX + `
YOUR TASK: ADVERSARIAL CHECK of ${prop ? prop.report_path : '(proposal failed)'} and the U7/U8 reports. Recompute key numbers with your own code (not the arm scripts), try alternative explanations (timing/transit accounting, observation definitions, chance cancellations across movements like the round-1 FIFO80 artefact, state selection, single seed), check the G-SC109 claim on the exact path, and list what is still unproven. Write ${OUT}/C3V2_CHECK.md.`, { label: 'check', phase: 'Check', schema: C })

return { u7, u8, prop, chk }
