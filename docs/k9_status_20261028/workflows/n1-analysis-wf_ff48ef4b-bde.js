export const meta = {
  name: 'n1-analysis',
  description: 'Run the frozen N1 analysis pipeline on the 16 completed native VSL step runs (extract, FZP pass, moments, fit), report the Carlson (L0) verdict, the selected VSL response law and parameters, the B5 rule (plan text + exposure-weighted sensitivity), and verify independently; no plant/code changes',
  phases: [
    { title: 'Analyse', detail: 'frozen pipeline' },
    { title: 'Verify', detail: 'independent checks of numbers and rule adherence' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const N = 'D:/VISSIM_runs/20260927_n1_vsl'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- N1 = native VSL step experiment (user-approved 2026-09-27): 16 runs seeds 41/43/47/53 x {c90, c100, c80, S5-pulse placebo}, all COMPLETED (queue finished 07:08 on 2026-09-28; every batch passed G0 prefix identity with v3b NC, G1 completion, G2 readback) — ${N}/queue.log, ${N}/<seed>_<arm>/run. Design ${R}/fwe-struct/p0/N1_DESIGN.md (revision 3), spec ${R}/fwe-struct/p0/n1/n1_plan_v3.json (sha 0db0d1c6...). Tools and the analysis freeze: ${N}/scripts (n1_extract.py, n1_fzp_pass.py, n1_moments.py, n1_fit.py, n1_common.py require_freeze), ${N}/reports/analysis_freeze.json (sha 3b54d484...; 17 implementation choices in n1_fit.py IMPLEMENTATION_CHOICES, frozen before any N1 data was opened), README ${N}/README.md (analysis procedure), NC moments ${N}/reports/nc_moments.
- The user did not change the frozen rules or the 17 implementation choices: apply them exactly. The B5 rule is evaluated with the plan-text halves (B1 2.9/3.2 %) and reported with the exposure-weighted halves as a sensitivity; if the two verdicts differ, say so clearly (the user decides; B5 = optional s31 batch, NOT to be launched here).
- SAFETY: first verify that the tool files still match the freeze hashes (require_freeze) and refuse to proceed otherwise; no edits to the frozen tools (if a tool crashes, report it — a fix would need a documented re-freeze decision, do not patch silently); no VISSIM/cscript; write only under ${N}/<arm>/analysis-type outputs the tools define, ${N}/reports/ and ${R}/fwe-struct/p0/n1/analysis_work/. One heavy process at a time, BELOW_NORMAL. Another workflow (v3c1 gate evaluation) runs concurrently. Fit seeds only; never open s37, RM arms or sealed seeds.
`
const A = { type: 'object', properties: { verdict_ko: { type: 'string' }, results_ko: { type: 'string' }, b5_ko: { type: 'string' }, implications_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict_ko', 'results_ko', 'b5_ko', 'implications_ko'] }
phase('Analyse')
const an = await agent(`${COMMON}\nTASK: run the README analysis procedure for all 16 arms (n1_extract -> n1_fzp_pass -> n1_moments --arm, then n1_fit --run), check every declared gate/rule outcome, and write ${N}/reports/N1_RESULTS.md (Korean): per-moment table (M1-M7 by level and zone, paired deltas with rule SE), L0 (deployed Carlson A0.5/E4) falsification verdict on B2, L1-L4 fits and the selection by held-out loss (LOSO/LOLO), the recommended VSL response law and parameters for the plant (and what F6 option C implies: refit values, or 'VSL does not raise discharge'), B5 rule outcome, caveats, and implications for the FW_E structural fixes (F4 discharge law, F5) and for closed-loop runs (V0).`, { label: 'analyse', phase: 'Analyse', schema: A })
phase('Verify')
const vf = await agent(`${COMMON}\nAnalysis report: ${JSON.stringify(an)}\nTASK (independent verifier): re-check that the tools matched the freeze, recompute at least the B2 and B1 paired dq/q (M4) per level and seed and the L0 verdict with your own code from the extracted outputs (and spot-check one arm's extraction against its FZP), check the selection logic and the B5 rule against n1_plan_v3.json, and look for post-hoc choices. Write ${R}/fwe-struct/p0/n1/VERIFY_N1.md. Return agreement/disagreement and any blocking issue.`, { label: 'verify', phase: 'Verify', schema: A })
return { an, vf }
