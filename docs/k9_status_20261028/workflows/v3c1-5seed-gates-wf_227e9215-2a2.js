export const meta = {
  name: 'v3c1-5seed-gates',
  description: 'Re-judge the v3c1 no-control gates on all 5 fit seeds (31/41/43/47/53) exactly as pre-declared, plus the pre-declared SC1004 W shift test; independent verification; no network edits, no VISSIM',
  phases: [
    { title: 'Evaluate', detail: 'G1-G6 on 5 seeds + SC1004 W permutation test' },
    { title: 'Verify', detail: 'independent recount' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const V = 'D:/VISSIM_runs/20260927_v3c1'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- Network v3c1 = v3b + routing decisions 1160, 1162-1168 (V1, V3-V7; V2 held). NC runs FINISHED on v3c1 for all fit seeds: ${V}/s{31,41,43,47,53}_v3c1nc/run (s47/s53 finished 11:0x on 2026-09-28; run stage-1 scans for s47/s53 first: python -B D:/VISSIM-merge/tools/stage1/stage1_scan.py <run dir>). v3b NC: D:/VISSIM_runs/20260925_v3b/s{31,41,43,47,53}_v3bnc. Never open s37 (held out; s37 v3c1 is not run yet), RM arms, sealed seeds.
- PRE-DECLARED RULES (apply exactly, no post-hoc criteria): ${V}/reports/gate_predeclaration_nc_batch1.md (G1-G7; G2 binding on the 5-seed pool; G4 per run on all links, reverts only for item-attributed failures) and ${V}/reports/predeclaration_5seed_sc1004w.md (sha 195683e7..., written 10:46 before s47/s53 completed): SC1004 W shift = metrics M-a complex veh.h (links/connectors 10638, 70, 10637, 10776, 126, 10643, 10641, 10700, 71, 10640; stage-1 link_vh full run) and M-b region_vh offramp; one-sided exact permutation test 5 vs 5 (v3c1 vs v3b, independent samples, statistic mean difference); BOTH p <= 0.05 -> 'shift confirmed' (no automatic revert; propose a half-split item-removal experiment), otherwise 'not confirmed' (record as not attributable, keep V1, V3-V7). Report per-seed signs and link 71/84 removal counts as report-only.
- Batch-1 evaluation and scripts to extend (SEEDS and the seed checks only): ${V}/reports/gates_batch1/ (GATES_BATCH1.md, scripts/, support/); its independent verification ${R}/net-v3c/v3c1/gates/VERIFY_BATCH1.md (VC1 classifier); SC1004 W diagnosis ${R}/net-v3c/v3c1/sc1004w/ (SC1004W_DIAG.md, runs.py, o_noise.py).
- WRITE ONLY under ${V}/reports/gates_5seed/ (new), ${V}/s{47,53}_v3c1nc/analysis/ (stage-1 outputs) and ${R}/net-v3c/v3c1/gates5/. No git, no VISSIM/cscript; never write elsewhere. Stream FZPs one at a time at BELOW_NORMAL (typed ctypes, read back). The N1 B5 queue (4 VISSIM runs) is active: keep CPU modest, never touch D:/VISSIM_runs/20260927_n1_vsl.
`
const G = { type: 'object', properties: { verdict_ko: { type: 'string' }, per_gate_ko: { type: 'string' }, sc1004w_ko: { type: 'string' }, next_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict_ko', 'per_gate_ko', 'sc1004w_ko', 'next_ko'] }
phase('Evaluate')
const ev = await agent(`${COMMON}\nTASK: evaluate G1-G7 on the 5 fit seeds and the pre-declared SC1004 W shift test; write ${V}/reports/gates_5seed/GATES_5SEED.md + gates_5seed.json (per seed, per item, per gate, pass/fail, revert decisions, SC1004 W verdict with p-values, report-only items).`, { label: 'evaluate', phase: 'Evaluate', schema: G })
phase('Verify')
const vf = await agent(`${COMMON}\nEvaluation: ${JSON.stringify(ev)}\nTASK (independent verifier): recount G1/G2 on s47/s53 with the VC1 classifier, recount G4 for s47/s53 from the .err files, recompute M-a/M-b from scan.json yourself and the exact permutation p-values (enumerate all 252 splits), and check every verdict follows the two pre-declarations. Write ${R}/net-v3c/v3c1/gates5/VERIFY_5SEED.md. Return agreement/disagreement per gate and for the SC1004 W verdict.`, { label: 'verify', phase: 'Verify', schema: G })
return { ev, vf }
