export const meta = {
  name: 'k8b-blind-probe',
  description: 'K8b offline blind probe (amendment 15): fix probe sample (held-out R-obs states), define candidate fixes P-1..P-4 as scratch patches, run BASE/SAF/SAF+patch rollouts on held-out states only, adversarial check of blindness and results, propose K8b scope with user decisions',
  phases: [ { title: 'Design' }, { title: 'Probe' }, { title: 'Check' }, { title: 'Propose' } ],
}
const K8 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
const W = 'D:/VISSIM-merge/sim3-n31-k8'
const OUT = 'D:/VISSIM-merge/k8_gates_out_v2'
const P = 'D:/VISSIM-merge/k8b_probe'
const CTX = `CONTEXT (Korean prose, concise; tag claims [실행]/[읽음]/[추론]; cite file:line and paths).
K8 SA gates ended STOP (verified). Diagnosis: ${OUT}/diag_sa_fail/D1D2.md, D3D6.md; options ${K8}/sagate/SA_FAIL_OPTIONS.md. User decisions: ${K8}/K8_PREDECLARATION_AMENDMENT_15.md (sha c32cef1a...): D-K8-9 = fix causes then rerun (K8b), J1 held; D-K8-10 = keep the G-EB-3(b) definition; BLIND PROBE RULES there are binding: never compute gate metrics for patched arms on the judging states (TL3m 27 = seeds 31/43/47 x T in {900,1200,1800,2250,2700,3000,3600,4200,4950}; long jobs TL3 s31 900 H24 / 2700 H42 / 4950 H27; DP 17; FH 45 judging use) — probe only on held-out R-obs decision times (same three R-obs runs D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s{31,43,47}) and held-out long rollouts (different start/seed, e.g. s43 2250 H42, s47 3000 H27).
Code: K8 worktree ${W} HEAD 28c6ab55 (runtime = K8-6c f7407ca5; SA key-only); harness diagnostics/sdmpc_n31_20260924/k8_gates/ (README) with sa_tl3m.py prep/capture/jobs for R-obs seeds. Freeway/urban background: ${K8}/../fw_status/FREEWAY_STATUS.md, ${K8}/DEFECTS.md, OPT1 spec + amendment 1, batch-2 docs (U4 saturation table, U7a/U7b kinematic arrival) under ${K8}/../urban-b2/.
RULES: NO commits to ${W}; patches live only in a scratch tree ${P}/tree (git archive of ${W} HEAD + patches) and outputs under ${P}/out. No VISSIM/COM/cscript, no new VISSIM runs, no forbidden tests (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Never modify ${W}, frozen/*, other worktrees, D:/VISSIM_runs/* (read-only), k86g/k86h outputs (read-only). Sealed seeds never; codex 64cf numbers never. Heavy Python BELOW_NORMAL, PYTHONHASHSEED=0, python -B, one heavy job at a time (only the 'Probe' agent runs rollouts). Stop and report if any drive < 8 GB free.`
const G = { type: 'object', properties: { report_path: { type: 'string' }, summary: { type: 'string' }, open: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'summary', 'open'] }
phase('Design')
const des = await agent(`${CTX}
TASK (no rollouts): write ${P}/PROBE_PLAN.md and fix it with sha256 before any probe rollout:
1. Probe sample: list exact held-out states (seed, T) — about 8-10 per seed spread over regimes, incl. some with VISSIM 10491 spill events and non-events (use the VISSIM-side classification method of the gate harness applied to held-out T; that is VISSIM data, allowed) — plus 2 held-out long rollouts (s43 2250 H42, s47 3000 H27 or similar). Record sha.
2. Candidate fixes as exact formulas + code locations (scratch patches): P-1 SC1002 W internal movements capacity from v3c3 NC FZP saturated discharge (declared rule like U4, re-derived on v3c3 NC fit seeds 31/41/43/47/53 FZPs, never the judging-state outputs); P-2 in_SC1001_W urban arrival kinematics (gate arrival delay by link-32 travel/queue position, beta_W from FZP; U7a/U7b lineage); P-3 F13: when 10491 blocks, the FIFO section speed cap applies only to the exit-bound lane-1 share of FW_W cells (state the exact math in METANET terms and which AFA lines change); P-4 W_out exit law (branch positions 412/735 m, 734 m residence instead of tau 117.6 s); combos (P1+P4, P1+P2+P4, all four).
3. Metrics to report on the probe sample (same definitions as the gates, but labelled 'probe, not judging') + side effects (SC1002 downstream, other signals' queues, Omega one-step).
4. Order of rollouts and compute budget (<= ~12 h).`, { label: 'design', phase: 'Design', schema: G })
phase('Probe')
const pr = await agent(`${CTX}
Plan: ${JSON.stringify(des)} (read ${P}/PROBE_PLAN.md; verify its sha before starting; do not change it).
TASK: build the scratch tree ${P}/tree (git archive ${W} HEAD) and the patch variants exactly as the plan defines; run captures/rollouts ONLY on the plan's probe sample for arms BASE, SAF, and SAF+each patch/combination as planned; compute the planned metrics; write ${P}/PROBE_RESULTS.md with tables (per arm, per metric, per seed/regime) and side effects; list every deviation from the plan. Never touch judging states. Resume-friendly; one heavy job at a time.`, { label: 'probe', phase: 'Probe', schema: G })
phase('Check')
const ck = await agent(`${CTX}
Results: ${JSON.stringify(pr)}.
TASK: adversarial check: (1) blindness — prove from the run logs/paths that no judging state was captured/rolled out for patched arms, and the plan sha was fixed before the first probe rollout; (2) re-run 2 probe rollouts yourself and compare numbers; (3) check each patch implements the planned formula exactly (diff the scratch tree vs ${W}); (4) look for side effects the results table hides. Light reruns only. Write ${P}/PROBE_CHECK.md.`, { label: 'check', phase: 'Check', schema: G })
phase('Propose')
const prop = await agent(`${CTX}
Inputs: ${JSON.stringify({ des, pr, ck })}.
TASK: write ${K8}/sagate/K8B_SCOPE_PROPOSAL.md (Korean, for the user, plain language first): which fixes to include in K8b and why (probe evidence, effect sizes, side effects, confidence), which to leave for K9, design decisions the user must make (e.g. F13 options) with a recommended choice each, how the gates would be rerun (new commits, fresh trees, all SA judging gates from scratch, judging states still blind until then), expected timeline to J1, and risks (e.g. G-EB-3(b) definitional part ~+22; P-1 increasing SC1002 downstream load).`, { label: 'propose', phase: 'Propose', schema: G })
return { des, pr, ck, prop }
