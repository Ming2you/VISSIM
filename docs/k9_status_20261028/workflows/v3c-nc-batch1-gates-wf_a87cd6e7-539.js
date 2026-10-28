export const meta = {
  name: 'v3c-nc-batch1-gates',
  description: 'Evaluate the pre-declared v3c no-control gates G1-G5 on NC batch 1 (seeds 31/41/43) and cross-check them with an independent classifier; report pass/fail per item and the revert decisions (no network edits, no VISSIM)',
  phases: [
    { title: 'Evaluate', detail: 'G1-G5 per the pre-declaration' },
    { title: 'Verify', detail: 'independent recount and review' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const V = 'D:/VISSIM_runs/20260927_v3c'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- Network v3c = v3b + 9 new static routing decisions 1160-1168 (V1-V7 of ${R}/net-v3c/V3C_PROPOSAL.md, cohort-specific, P1 splits). Receipt ${V}/v3c_edit_receipt.json, edits table ${V}/reports/v3c_edits_table.txt, shares ${V}/work/v3c_shares.json (v3b NC cohort counts, splits, expected beta), build checks ${V}/reports/v3c_build_checks.json.
- NC batch 1 FINISHED: ${V}/s{31,41,43}_v3cnc/run (run.json completed, exit 0; FZP vissim_eval/baseline_s{seed}_v3cnc_001.fzp 5 s frames; simulation .err run/baseline_s{seed}_v3cnc_001.err; load .err identical to v3b = G6 pass; stage-1 scans ${V}/s{seed}_v3cnc/analysis/scan.json + uninserted.json made by the main session). Same-seed v3b NC: D:/VISSIM_runs/20260925_v3b/s{31,41,43}_v3bnc (analysis/scan.json, run/*_001.err, FZP). v3b NC seeds 47/53 exist for baselines where the pre-declaration says "fit 5 seeds" (G4 baseline); v3c 47/53 are NOT run yet, so G2 is judged on the 3 batch-1 seeds now and re-checked with 5 later. NEVER open s37 (held out) or RM arms or sealed seeds.
- GATES ARE PRE-DECLARED and must be applied exactly: ${V}/reports/gate_predeclaration_nc_batch1.md (sha 1905adf4..., written before any v3c NC data existed) + V3C_PROPOSAL.md §5 G1-G7 and the per-item revert rule. G2 reference = expected mixture (old cohorts at their v3b NC realized split, new cohorts at P1, weighted by v3b NC cohort counts), binding criterion |v3c realized - expected mixture| <= 0.05 per movement share of the 11 approach rows, binomial CI reported only. G4 = all .err lines containing "seconds of waiting for lane change" (45.0 and 60.0 s), per link, v3c run value <= v3b NC 5-seed max + 2 per run. G1 = route-less passages at the 7 fixed stop lines <= 1% per seed and each new decision's acceptance (share of its targeted cohort carrying that decision's ROUTDECNO) >= 99%. G3 = diverge-wide route-less rescan (first-audit method, ${R}/net-v3c/ f1_fzp.py / r1_* scripts) shows no new route-less diverge vs the v3b audit, plus static checks already done. G5 = report only: Omega, urban_omega, fw_e_main, fw_w_main, offramp, uninserted vs same-seed v3b NC; flag if the mean shift exceeds 2 sd (v3b NC Omega sd 115.9).
- WRITE ONLY under ${V}/reports/gates_batch1/ (new) and ${R}/net-v3c/gates/. Do NOT modify any existing file in ${V} (receipt-pinned scripts included): if you need the classifier ${V}/scripts/v3c_fzp_pass.py, copy it into your folder and fix its below_normal() (ctypes argtypes/restype, read back GetPriorityClass). No git, no VISSIM/cscript, never write under D:/VISSIM-merge or D:/VISSIM_runs/20250925_v3b. Stream FZPs one at a time at BELOW_NORMAL (another workflow runs concurrently).
`
const G = { type: 'object', properties: { verdict_ko: { type: 'string' }, per_gate_ko: { type: 'string' }, per_item_ko: { type: 'string' }, revert_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict_ko', 'per_gate_ko', 'per_item_ko', 'revert_ko'] }
phase('Evaluate')
const ev = await agent(`${COMMON}\nTASK: evaluate G1-G5 for V1-V7 on NC batch 1 exactly as pre-declared; write ${V}/reports/gates_batch1/GATES_BATCH1.md + gates_batch1.json (per seed, per item, per gate numbers, pass/fail, and which items would be reverted under the per-item revert rule).`, { label: 'evaluate', phase: 'Evaluate', schema: G })
phase('Verify')
const vf = await agent(`${COMMON}\nEvaluation: ${JSON.stringify(ev)}\nTASK (independent verifier): recount G1 and G2 with an independent classifier (adapt ${R}/net-v3c/build/verify_numbers_r0/vn_fzp.py, which was validated on v3b), recount G4 from the .err files yourself, spot-check G5 from scan.json, and check that every pass/fail follows the pre-declared rules (no post-hoc criteria). Write ${R}/net-v3c/gates/VERIFY_BATCH1.md. Return agreement/disagreement per gate and item.`, { label: 'verify', phase: 'Verify', schema: G })
return { ev, vf }
