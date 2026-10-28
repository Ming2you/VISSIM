export const meta = {
  name: 'sdmpc-9pct-vs-v5b',
  description: 'Explain why the 2026-09-20 seed13 SDMPC run improved Omega TTT 9.03% (urban-only) while our V5b SDMPC-31 run lost 5.9% (urban-only): scenario, controller/plant code, actions, prediction accuracy',
  phases: [
    { title: 'Compare', detail: 'scenario | controller+plant code | urban actions | urban prediction error' },
    { title: 'Synthesize', detail: 'ranked causes' },
    { title: 'Critique', detail: 'adversarial check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/sdmpc9pct'
const CTX = `
CONTEXT (you have no other context).
Two SDMPC closed-loop VISSIM results that both moved ONLY urban signals (green splits + offsets of 17 SCs; 8 ramp meters stayed fully green g10; VSL stayed at the base speed):
(A) "9% run" (user's, 2026-09-20): NC D:?? no — located at C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/confidence-audit-order-20260913/evaluation/runs/{sdmpc_nc9000_s13_v1, sdmpc_cl9000_s13_v3} (read-only; that worktree has uncommitted edits — never modify it). Each run folder: runlog_*.txt, run_provenance_*.json (workspace_git_commit c4e6463, seed 13, controller no-control / wu-link), decisions_*/ (state/action json/csv, readback), vissim_eval/ (FZP etc.), completion_receipt.json. Packaged copy + evidence: C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/sdmpc-9000-data-20260925/datasets/sdmpc_9000_seed13_20260920/ (README.md, evidence/{README.md, comparison.json, config.json, config_original_clock.json, result_review_20260920.json, compare.py, sdmpc_cl9000_s13_v3/, sdmpc_nc9000_s13_v1/}, ttt_recheck_20260925.json). Result: Omega TTT NC 4192.123 -> CL 3813.755 veh.h (-9.026%), warmup 900 s FZP rows identical (939,080). Controller: canonical adapter with adapter.sdmpc = "proxlinear-v1" (evaluation/controllers/sdmpc.py), 17 urban / 2 freeway players, 450 s horizon, decisions 142-349 s wall; original controller preserved at branch codex/sdmpc-controller-20260920 @ 502168d in the repo C:/Users/TRLAB/Documents/ChatGPT/VISSIM (read with git show/log only). Runlog shows demand inputs 1098/1099 scaled x0.66664 to 3695.9/5279.8/5543.8/4751.8/3695.9/2639.9 veh/h, total inputs 13765-20648 veh/h ("80/50" demand), RUN_MODE=STEPWISE_PHYSICAL_HEAD_OBSERVATION (per-second head observation), base VSL 120.
(B) "V5b" (ours, 2026-09-24): D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b (runlog, run_provenance, launch_plan.json, decisions_sdmpc31_v2_s31b/ with action_*.json containing prediction/prediction_error, signal_readback.csv; vissim_eval/*.fzp). Paired NC = D:/VISSIM_runs/20260923_stage1/s31_v2nc (native no-control, same network f475ce42 / seed 31 / SimRes 10; frames identical to 900.1 s). Result: Omega TTT NC 7113.1 -> V5b 7530.4 (+5.87%; our stage-1 Omega definition, D:/VISSIM-merge/tools/stage1/stage1_scan.py + stage1_common.py; V5b scan at ${SP}/../v5b_scan/analysis/scan.json). Scenario FW80/U90 v2 demand (1098 at 7096-10644 veh/h, 1099 at 4300-6000), base speed 110, SimRes 10, obs150 (one exact 150 s observation per decision), controller SDMPC-31 (31-cell METANET freeway plant + coupled lane/urban plant, manifest coupled-lane-plant/v2) from the frozen tree D:/VISSIM-merge/frozen/sdmpc31_7216e253_202609241509 (identical sources readable at D:/VISSIM-merge/review-7216e25; branch claude/sdmpc-n31-20260924). Our tree descends from a merge of plant 00abbab + controller 5fdfabd (sim3), i.e. later than 502168d.
Known V5b facts: over 54 decisions the 150 s one-step prediction error was freeway total -0.7%, urban total +8.9% (raw), urban movement queue 1690 vs 552 observed (3x), urban link occupancy 1135 vs 2010 (-42%), boundary queue 1140 vs 429 (+173%); offsets changed every decision (e.g. 3000 s: SC1 59.8 vs native 131, SC16 0.07 vs native 149).
SAFETY (hard): read-only everywhere except NEW folders under ${SP}/<your-name>/. Never launch VISSIM/cscript/.ps1, never kill processes, never modify any worktree, repo, frozen copy or run folder; git: only log/show/diff/status. A native VISSIM run and another analysis workflow are live — Python threads 1 (OMP/NUMBA/MKL), at most one heavy Python process of yours at a time. No recalibration. Write the final answer in Korean with exact numbers and file paths, marking [실행] vs [읽음].`

const scenario = () => agent(`${CTX}
YOUR TASK (name: scenario): Build an exact scenario difference table A vs B from files: network file and sha (find the .inpx each run used), differing INPX sections, every vehicle input's demand per interval (scaled values actually applied at runtime per runlog), vehicle compositions, desired-speed distributions and base speeds, seed, SimRes, simulation period, native signal programs (.sig sha), routes, runner/observation mode (stepwise per-second head observation vs obs150), what the NC arm is (native no-control in both?). Then compare congestion levels in the two NC runs: Omega TTT, urban vs freeway split, per-SC delay/queue if extractable, freeway speeds. Determine whether the two Omega definitions are the same (A's compare.py / ttt recheck vs our stage1_scan): if the link sets or integration differ, quantify on one FZP. Conclude how comparable A and B are.`, {label: 'scenario', phase: 'Compare'})

const code = () => agent(`${CTX}
YOUR TASK (name: code): Diff the controller and urban-plant code/config that produced A (502168d / the confidence-audit-order worktree at c4e6463 + its config.json used by the run) against what produced B (frozen sdmpc31_7216e253 = review-7216e25 + diagnostics/sdmpc_n31_20260924/config_n31_v2.json and the plant manifest). Focus on what drives URBAN signal decisions: SDMPC algorithm (proxlinear-v1 settings, iterations, proximal weights, move limits for green and offset, price/dual handling, resource projection, externality gradients), urban plant model (queue vs link occupancy, phase clocks, offsets/transition handling, capacity/head observation, arrival modeling), objective/cost partition, observation pipeline feeding the urban plant (per-second head observation vs obs150 derived state), signal actuation contract (offset writer, how offsets/splits are applied natively, cycle), and any 'held/native plan' reference. Produce a ranked list of differences with the likely effect on urban decisions and cite file:line on both sides.`, {label: 'code', phase: 'Compare'})

const actions = () => agent(`${CTX}
YOUR TASK (name: actions): Compare the urban actions and outcomes. (1) For A and B, per SC and decision: cycle, splits, offset vs the native program (.sig), size of change between consecutive decisions (splits and offsets), how often offsets jump. (2) Decompose each CL-NC difference by region (urban per SC/approach vs freeway vs off-ramp vs outside) and by time, using each run's own FZP (A's links map to the same physical network family — verify before applying our stage-1 regions; otherwise use A's own area definition). (3) Relate: do the SCs where A gained coincide with modest, stable changes, and do the SCs where B lost coincide with large/frequent offset changes? Report tables.`, {label: 'actions', phase: 'Compare'})

const pred = () => agent(`${CTX}
YOUR TASK (name: pred): Compare urban prediction quality in A vs B. For A, find the per-decision prediction and realized observation (action json prediction / prediction_error fields or equivalent in decisions_*; or state files) and compute the same one-step (150 s) errors as for B: urban total, movement queue, link occupancy, boundary queue, off-ramp storage, freeway total (raw, and with any audit scaling separately). Also check whether A's plant had observation-driven corrections (per-second head observation, measured capacity) that B lacks. If A lacks those fields, reconstruct the comparison from its state/observation files as far as possible and say what is not comparable.`, {label: 'pred', phase: 'Compare'})

phase('Compare')
const [rS, rC, rA, rP] = await parallel([scenario, code, actions, pred])

phase('Synthesize')
const synth = await agent(`${CTX}
YOUR TASK (name: synth): From the four reports, answer the user's question: "Both runs moved only urban signals; A improved 9%, B lost 5.9%. What changed?" Give a ranked list of causes with evidence and confidence: scenario (demand level / congestion regime, base speed, seed), measurement (Omega definition), controller/plant code differences (which specific changes after 502168d plausibly broke urban control), observation pipeline (per-second head observation vs obs150), action behavior (offset jumps). Separate what is proven from what is plausible. Propose the smallest decisive checks (offline first; e.g. run B's controller on A's saved states or A's controller on B's states in replay, or A's scenario with B's code) and say which ones need VISSIM. Korean, tables first.
=== scenario ===
${rS}
=== code ===
${rC}
=== actions ===
${rA}
=== pred ===
${rP}`, {label: 'synth', phase: 'Synthesize'})

phase('Critique')
const crit = await agent(`${CTX}
YOUR TASK (name: critic): Adversarially review the synthesis: verify at least four key numbers from the files, check that A and B metrics are not mixed, that causes are not over-claimed (single seeds on both sides, different scenarios), and that proposed checks are feasible without violating the safety rules. Output a Korean severity-ordered corrections list and then the corrected final answer in full.
=== synth ===
${synth}
=== scenario ===
${rS}
=== code ===
${rC}
=== actions ===
${rA}
=== pred ===
${rP}`, {label: 'critic', phase: 'Critique'})

return { scenario: rS, code: rC, actions: rA, pred: rP, synth, critique: crit }