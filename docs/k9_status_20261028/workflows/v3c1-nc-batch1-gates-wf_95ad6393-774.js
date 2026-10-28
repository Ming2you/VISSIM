export const meta = {
  name: 'v3c1-nc-batch1-gates',
  description: 'Evaluate the pre-declared v3c no-control gates G1-G6 on the v3c1 rerun (V2 reverted; seeds 31/41/43) and cross-check with an independent classifier; report pass/fail per item (no network edits, no VISSIM)',
  phases: [
    { title: 'Evaluate', detail: 'G1-G6 per the pre-declaration' },
    { title: 'Verify', detail: 'independent recount and review' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const V = 'D:/VISSIM_runs/20260927_v3c1'
const V0 = 'D:/VISSIM_runs/20260927_v3c'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- Network v3c1 = v3b + routing decisions 1160, 1162-1168 (v3c minus decision 1161 = item V2, reverted under the pre-declared per-item revert rule after V2 failed G4 on the v3c batch-1 runs). Receipt ${V}/v3c1_edit_receipt.json, README ${V}/README.md, pre-declaration copy ${V}/reports/gate_predeclaration_nc_batch1.md (same rules as the v3c original sha 1905adf4..., header says V2 is held: its gates no longer apply except that G3/G4 on stop line 1220012103 must return to the v3b level).
- v3c1 NC batch 1 FINISHED: ${V}/s{31,41,43}_v3c1nc/run (run.json completed exit 0; FZP vissim_eval/baseline_s{seed}_v3c1nc_001.fzp; simulation .err run/baseline_s{seed}_v3c1nc_001.err; load .err prepared/network/baseline_s{seed}_v3c1nc.err). Stage-1 scans are not made yet: run D:/VISSIM-merge/tools/stage1/stage1_scan.py <run dir> (python -B) yourself for the three runs first (it writes ${V}/s{seed}_v3c1nc/analysis/). Same-seed v3b NC: D:/VISSIM_runs/20260925_v3b/s{31,41,43}_v3bnc.
- The v3c gate evaluation (method to reuse): ${V0}/reports/gates_batch1/ (GATES_BATCH1.md, gates_batch1.json, scripts/ g12_eval.py, g3_compare.py, g4_err.py, g5_scan.py, f1_fzp.py, r1_v3c.py, a3_rl.py, n1_net.py, v3c_fzp_pass.py, build_report.py; support/). Its independent verification: ${R}/net-v3c/gates/VERIFY_BATCH1.md (VB1 classifier in ${R}/net-v3c/gates/verify_b1/). Copy scripts into your own folder and re-point them to v3c1 (decisions without 1161; V2 approach now expected route-less like v3b). Do not modify anything under ${V0}.
- Gates exactly as pre-declared: G1 route-less passages at the 6 fixed stop lines (V1, V3-V7) <= 1% per seed and each new decision's acceptance >= 99%; G2 |v3c1 realized - expected mixture| <= 0.05 per movement share of the approach rows of V1, V3-V7 (3-seed pooled now, 5 seeds later; binomial CI report only); V4 split must be re-judged since the 1092 chain is route-less again at SC12 W; G3 diverge-wide route-less rescan vs the v3b audit (no new route-less diverge; SC12 W back to its v3b list entry) + the static checks; G4 .err lines containing "seconds of waiting for lane change" (45.0 and 60.0 s) per link <= v3b NC 5-seed max + 2 per run (baseline from the v3b fit-seed .err files), with 1220012103 back at the v3b level; G5 report only (Omega, urban_omega, fw_e_main, fw_w_main, offramp, uninserted vs same-seed v3b NC and vs v3c batch 1; flag if mean shift > 2 sd, sd 115.9); G6 load .err equal to v3b; G7 static (from the v3c1 build checks).
- WRITE ONLY under ${V}/reports/gates_batch1/ (new), ${V}/s{seed}_v3c1nc/analysis/ (stage-1 scan outputs) and ${R}/net-v3c/v3c1/gates/. No git, no VISSIM/cscript; never write under D:/VISSIM-merge or other run folders. Stream FZPs one at a time at BELOW_NORMAL (typed ctypes, read back GetPriorityClass); another workflow (N1 analysis) runs concurrently. Never open s37, RM arms or sealed seeds.
`
const G = { type: 'object', properties: { verdict_ko: { type: 'string' }, per_gate_ko: { type: 'string' }, per_item_ko: { type: 'string' }, next_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict_ko', 'per_gate_ko', 'per_item_ko', 'next_ko'] }
phase('Evaluate')
const ev = await agent(`${COMMON}\nTASK: evaluate G1-G7 for V1, V3-V7 (and the V2 revert check on 1220012103) on v3c1 NC batch 1 exactly as pre-declared; write ${V}/reports/gates_batch1/GATES_BATCH1.md + gates_batch1.json (per seed, per item, per gate numbers, pass/fail, revert decisions if any), and state what remains for the 5-seed re-judgement.`, { label: 'evaluate', phase: 'Evaluate', schema: G })
phase('Verify')
const vf = await agent(`${COMMON}\nEvaluation: ${JSON.stringify(ev)}\nTASK (independent verifier): recount G1 and G2 with an independent classifier (adapt the VB1 verifier), recount G4 from the .err files yourself, spot-check G5, and check every pass/fail follows the pre-declared rules (no post-hoc criteria). Write ${R}/net-v3c/v3c1/gates/VERIFY_BATCH1.md. Return agreement/disagreement per gate and item.`, { label: 'verify', phase: 'Verify', schema: G })
return { ev, vf }
