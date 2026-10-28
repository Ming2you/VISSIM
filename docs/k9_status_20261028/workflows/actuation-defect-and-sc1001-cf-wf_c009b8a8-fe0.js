export const meta = {
  name: 'actuation-defect-and-sc1001-cf',
  description: 'Check whether the 9% run (A) had the offset phase-restart actuation defect found in V5b (B), and run an offline SC1001 counterfactual (off-ramp storage cap / initial queues set to measured) on saved decisions',
  phases: [
    { title: 'Check', detail: 'A vs B signal execution | SC1001 counterfactual' },
    { title: 'Verify', detail: 'adversarial check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const SAFE = `
SAFETY (hard): Never launch VISSIM, cscript or any .ps1 runner/replay script; never kill processes; never modify any worktree/repo/frozen copy/run folder (read-only), git only log/show/diff/status. Write only NEW folders under ${SP}/<track>/. Python -B, threads 1 (OMP/NUMBA/MKL), at most one heavy Python process at a time. No recalibration, no code edits to trees (in-memory overrides in your own scratch scripts are fine). Final answer in Korean with exact numbers and file:line, marking [실행] vs [읽음].`

const act = () => agent(`
CONTEXT: V5b (B) = D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b, SDMPC-31 closed loop, obs150 continuous-event runner (runner VBS in the frozen tree D:/VISSIM-merge/frozen/sdmpc31_7216e253_202609241509, readable identical sources at D:/VISSIM-merge/review-7216e25; runner = the lane_native / real_world_stackelberg VBS used by run_sdmpc_n31.ps1). A verified analysis found an actuation defect in B: at each decision time, when a new offset is written, the controller restarts the phase that should be active under the new offset with its FULL duration instead of the remaining time (example: 3000 s SC1, SG4 started at 3001 s and ran 63 s; SG2 started at 3090 instead of planned 3059.8), so realized phase starts deviate from planned offsets by 18.9 (SC7) to 49.7 s (SC1005) on average (random baseline 37.5 s for C=150, 30 s for C=120); also 460 green->red transitions without amber and 177 greens shorter than 5 s across 17 SCs, almost all at decision boundaries; at 900 s handover SC1 SG2/6 went G->R immediately. Evidence files: B decisions_sdmpc31_v2_s31b/signal_readback.csv, vissim_eval/*.lsa, action_*.csv (signal / signal_sg rows with offsets and greens). The earlier analysis scripts live under ${SP}/wq21 or ${SP}/v5bdecomp (search ${SP} for lsa parsing scripts and reuse them).
The 9% run (A) = C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.worktrees/confidence-audit-order-20260913/evaluation/runs/sdmpc_cl9000_s13_v3 (+ NC sdmpc_nc9000_s13_v1), runner mode STEPWISE_PHYSICAL_HEAD_OBSERVATION (per-second COM stepping), its runner VBS and adapter in that worktree (read-only; it has uncommitted edits). Note an earlier note says A's independent LSA coverage was false (native execution checked by LDP + immediate readback).
YOUR TASK (track name: actuation; scratch ${SP}/actuation/): Determine, with the same metrics for A and B, how signal plans were actually executed: (1) realized phase start vs planned offset deviation per SC (mean, distribution) — use LSA/LDP/readback, whichever exists for each run; (2) phase restarts at decision boundaries (full-length restart vs remaining time); (3) green->red without amber, greens < 5 s; (4) the code path in each runner/adapter that applies a new offset/split mid-cycle (cite file:line), explaining why B restarts phases and whether A does the same or transitions smoothly. Conclude whether this defect is present in A, in B only, or both, and estimate its plausible share of B's urban loss if feasible (e.g. compare delay on SCs with large realized-offset error vs small), without over-claiming.
${SAFE}`, {label: 'actuation', phase: 'Check'})

const cf = () => agent(`
CONTEXT: In V5b (B, D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b) SDMPC pushed SC1001 green from p1+p2 (south approach link 40) to p4/p3 every decision. Verified mechanism: the p1-axis total gradient was positive in 55/55 decisions, dominated by external terms from (i) the modeled OR_D_W storage (connector 10491 only, capacity 38.58 veh, config_n31_v2.json:8103) filling and spilling back onto FW_W (never observed: 10491 held 1-9 veh, 0 stopped), (ii) W stop-line (link 127) saturation and OR_D storage over-prediction, (iii) downstream storage terms (to SC1003/SC1002); plus a constant marginal of 8.605 veh per saturated lane per z and a +-6 s move box that keeps only the sign. Prior analysis outputs: ${SP}/sc1001/ (viewB/extract_B.py, summary_B.txt, critic/regroup.py, final_*.md) and plant scoring tools from the RM trace: ${SP}/rm_trace/plant/ (capture.py, probe.py, plans.py, hooks.py, prepare_copy.py) with isolated replay state copies D:/VISSIM_runs/20260924_sdmpc31/rm_trace_plant_T2700, _T3000, _T3300 (read-only; copy to scratch if you must write) and ${SP}/v5brank/ (the plan-ranking harness that scored SDMPC vs native plans with the exact plant and the continuous surrogate — reuse it). Sources identical to V5b: D:/VISSIM-merge/review-7216e25.
YOUR TASK (track name: cf; scratch ${SP}/cf/): Offline counterfactual on B's saved states at 1200 (if a prepared state exists or can be prepared purely in Python like prepare_copy.py did), 1650, 2700 and 3000: recompute SC1001's p1..p3 axis gradients (own / external by owner) at the held point with the same surrogate, under variants: V0 as logged (must reproduce the logged gradients), V1 OR_D_W storage cap raised to a physically plausible value (connector 10491 + receiving link storage; document the number) or spillback to FW_W disabled, V2 W stop-line/off-ramp initial queues and storage set to the measured values from the observation (state_*.json / derived files), V3 = V1+V2. Report whether the p1 total gradient changes sign or drops below the ~0.4 saturation threshold, and what remains (downstream storage terms, constant marginal). If feasible, also re-run SDMPC's selection for SC1001 only under V3 and report the chosen p1..p4. Do not modify any tracked file; overrides in memory only.
${SAFE}`, {label: 'sc1001-cf', phase: 'Check'})

const verify = (name, report) => agent(`
You are an adversarial verifier for track "${name}". Re-check at least three key numbers from the cited files yourself, check that A and B are measured the same way, that claims do not exceed the evidence, and that the safety rules were followed. Output a Korean severity-ordered corrections list, then the corrected concise conclusion.
${SAFE}
=== report ===
${report}`, {label: `verify:${name}`, phase: 'Verify'})

phase('Check')
const results = await pipeline([['actuation', act], ['sc1001-cf', cf]], async ([name, fn]) => {
  const r = await fn()
  const v = await verify(name, r)
  return { name, report: r, verify: v }
})
return results