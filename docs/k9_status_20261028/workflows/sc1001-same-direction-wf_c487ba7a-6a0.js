export const meta = {
  name: 'sc1001-same-direction',
  description: 'Why both SDMPC runs (9% run A and V5b B) pushed SC1001 green from p1+p2 to p3+p4 regardless of load: model view, gradient components, SC1001-specific code paths',
  phases: [
    { title: 'Inspect', detail: 'A decisions | B decisions | code paths' },
    { title: 'Synthesize', detail: 'mechanism verdict' },
    { title: 'Critique', detail: 'adversarial check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/sc1001'
const CTX = `
CONTEXT (you have no other context).
Two SDMPC closed-loop VISSIM runs that moved only urban signals:
(A) 9% run, seed 13: C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/confidence-audit-order-20260913/evaluation/runs/sdmpc_cl9000_s13_v3 (NC pair sdmpc_nc9000_s13_v1), controller "wu-link" adapter with adapter.sdmpc = proxlinear-v1 (code at that worktree, workspace commit c4e6463 plus the run's config; original controller branch codex/sdmpc-controller-20260920 @ 502168d in repo C:/Users/TRLAB/Documents/ChatGPT/VISSIM). Omega TTT -9.03%.
(B) V5b, seed 31: D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b (decisions_sdmpc31_v2_s31b/action_*.json with prediction, prediction_error and diagnostics; joint/iteration files if present), controller SDMPC-31 central-pfo-cap-v3 (sources: D:/VISSIM-merge/review-7216e25, identical to the frozen launch copy; config diagnostics/sdmpc_n31_20260924/config_n31_v2.json). Paired NC: D:/VISSIM_runs/20260923_stage1/s31_v2nc. Omega TTT +5.87%.
Finding to explain (verified): both controllers moved SC1001 the same way — p1+p2 green from native 69 s down to ~42 s over the first ~5 decisions (~6 s per decision: A 60.7/54.4/48.0/42.0, B 60.8/56.0/50.0/44.0), 54-decision mean 42.0 vs 42.3, giving it to p3+p4 (native 69 -> ~96; the off-ramp side, link 127 / connector 10481 = OR_D_E1 landing) — although the loads were opposite: early NC load on link 40 (SC1001 south approach, served by p1+p2) was 2-4x heavier in B, and link 127 was much lighter in B. Outcome: A gained -314 veh.h on the off-ramp legs (+40 on link 40); B gained only -111 on the off-ramp legs and lost +281 on link 40.
Leads: (1) V5b one-step prediction errors over 54 decisions: off_ramp_storage predicted 40.2 vs observed 8.0 veh (5x), boundary_queue 1140 vs 429 (+173%), urban movement queue 3x, link occupancy -42%; A had boundary queue +170% and queue 2.1x too. If the plant over-predicts the off-ramp storage / queue that SC1001 p3/p4 discharges, both controllers would push green there regardless of real load. (2) An old defect in the previous leader-follower path: priced_wu_link_controller.py _phase_refine_signal_setup returned None for signals with model.has_ramps (only SC1001 and SC1004), so their local cost fell back to an identically-zero drain model and the price term became the whole global marginal, ratcheting green to box vertices (memory 2026-09-04). Check whether an analogous exclusion / zero-curvature / ownership issue exists in the SDMPC paths of A and B for SC1001.
SAFETY (hard): read-only everywhere except NEW folders under ${SP}/<your-name>/. Never launch VISSIM/cscript/.ps1, never kill processes, never modify any worktree/repo/frozen copy/run folder; git only log/show/diff/status. Another analysis workflow is running: Python threads 1 (OMP/NUMBA/MKL), at most one heavy Python process of yours at a time. No recalibration, no code edits. Final answer in Korean with exact numbers and file:line, marking [실행] vs [읽음].`

const viewB = () => agent(`${CTX}
YOUR TASK (name: viewB): For B's decisions at 900, 1050, 1200, 1350, 1500, 1650 and also 2700, 3000: extract everything the controller logged about SC1001: its decision axes (p1..p4 green, offset), box/move limits, the gradient/tangent components per axis (own, external, price) and QP steps/iterations if logged (look in action json diagnostics, joint/iteration files, sdmpc metadata), the chosen value, and the model's initial state and prediction for the SC1001 approaches: link 40 (south, p1+p2) and link 127 / connector 10481 / off-ramp storage (p3+p4), plus whatever reservoir the plant uses for that off-ramp (off_ramp_storage, boundary queue). Compare with FZP-measured counts/queues on those links at the same times (use D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b/vissim_eval/*.fzp and the NC FZP; or the scan json at C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/v5b_scan/analysis/scan.json link_vh). Answer: which term drives SC1001 toward p3+p4 in B, and is it driven by an over-predicted off-ramp/boundary reservoir or by a pricing/ownership artifact?`, {label: 'viewB', phase: 'Inspect'})

const viewA = () => agent(`${CTX}
YOUR TASK (name: viewA): Same as for B but for A's decisions at 900..1650 and 2700, 3000 (decisions folder of sdmpc_cl9000_s13_v3; proxlinear-v1 logs its local QP gradients own/external/price and prices per decision somewhere in action json / metadata / diagnostics — find them). Extract SC1001 axes, gradient components, steps, chosen values, the model's initial state and prediction for link 40 and the off-ramp side (127/10481/storage), and compare with A's FZP-measured values (vissim_eval FZP is 1 s frames; read only the needed time windows). Answer: which term drives SC1001 toward p3+p4 in A, and was the model's view of the off-ramp side accurate in A (where the off-ramp was really congested)?`, {label: 'viewA', phase: 'Inspect'})

const code = () => agent(`${CTX}
YOUR TASK (name: code): Trace, in both code bases (A: the confidence-audit-order worktree code used by the run / 502168d; B: review-7216e25), how SC1001's green axes get their cost gradient in SDMPC: which player owns SC1001, what local model/cost it uses, whether signals with ramps (has_ramps or equivalent: SC1001, SC1004) are handled specially (excluded, drain fallback, zero curvature, passive ownership), how off-ramp storage / boundary queues feeding SC1001 are modeled and priced (e.g. storage:SC1001_* reservoirs, lane_offramp_runtime landing, urban boundary queues), and whether SC1004 shows the same monotone drift in both runs (check its decision trajectories quickly). Cite file:line on both sides and state whether the old has_ramps drain-fallback defect (priced_wu_link_controller.py) is still reachable in either SDMPC path.`, {label: 'code', phase: 'Inspect'})

phase('Inspect')
const [rB, rA, rC] = await parallel([viewB, viewA, code])

phase('Synthesize')
const synth = await agent(`${CTX}
YOUR TASK (name: synth): Decide the mechanism that makes both controllers push SC1001 toward p3+p4 regardless of load, with evidence strength: (a) over-predicted off-ramp/boundary reservoir, (b) pricing/ownership artifact (e.g. has_ramps-like exclusion, global marginal as price), (c) move-limit/box geometry (one-directional ratchet), (d) something else. Explain why the same move helped A and hurt B. Give the smallest offline check that would confirm it (e.g. rescore one B decision with the off-ramp reservoir initialized to the measured value) and state whether it needs any .ps1/VISSIM. Korean, tables first.
=== viewB ===
${rB}
=== viewA ===
${rA}
=== code ===
${rC}`, {label: 'synth', phase: 'Synthesize'})

phase('Critique')
const crit = await agent(`${CTX}
YOUR TASK (name: critic): Adversarially check the synthesis: re-verify at least four key numbers from the files, make sure gradients/terms are read from the right decision/iteration and units, that A and B are not mixed, and that claims do not exceed evidence. Output a Korean severity-ordered list of corrections, then the corrected conclusion in full.
=== synth ===
${synth}
=== viewB ===
${rB}
=== viewA ===
${rA}
=== code ===
${rC}`, {label: 'critic', phase: 'Critique'})

return { viewB: rB, viewA: rA, code: rC, synth, critique: crit }