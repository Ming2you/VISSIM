export const meta = {
  name: 'vsl-law-check',
  description: 'Check the Carlson A0.5_E4 VSL law against native fixed-VSL 90/70 runs (seed 31) and decompose the VISSIM VSL loss',
  phases: [
    { title: 'Extract', detail: 'EO cell/boundary extraction for fix90, fix70, rule-VSL arms' },
    { title: 'Analyze', detail: 'VISSIM decomposition + empirical FD vs Carlson + plant prediction' },
    { title: 'Synthesize', detail: 'VSL law verdict and recommendation' },
    { title: 'Critique', detail: 'adversarial review' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const CR = 'D:/VISSIM-merge/sim3-n31/diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923/control_response_v2'
const CTX = `
CONTEXT (you have no other context; read carefully).
Project: VISSIM network FW80/U90, base freeway speed 110, demand v2. Our SDMPC controller predicts with a 31-cell METANET plant per freeway direction. The user's VSL model was just ported into the plant: Carlson speed-limit FD "A0.5_E4" (A=0.5, E=4, alpha=0, base = 110) for FW_E only, with VSLExposure cohort transport; it was fitted on ANOTHER network at 90 only. In the plant it implies a capacity GAIN when the limit drops (theoretical max flow vs 110: 90 -> +6.5% on 4 lanes / +9.8% on 3 lanes; 100 -> +5.8%/+7.8%; 50 -> -21%/-17%). An offline SDMPC replay chose FW_E zone 5 = 100 and zone 10 = 90 for that reason.
NEW NATIVE DATA (VISSIM, seed 31, SimRes 10, 9000 s, same traffic settings as the no-control run s31_v2nc; only detector/evaluation config differs):
- D:/VISSIM_runs/20260923_stage1/s31_v2fix90: FW_E VSL zones seg5 + seg10 = DSDs 51-66 (link 2 at positions 48, 1305, 2652, 3998 m; link 2 starts at chain offset 2734.527 m of fw_e_main), all 4 vehicle classes set to desired-speed distribution 90 at 1200 s, held to 9000 s.
- D:/VISSIM_runs/20260923_stage1/s31_v2fix70: same DSDs 90 at 1200 s, 70 at 1350 s, held.
- D:/VISSIM_runs/20260923_stage1/s31_v2vsl: rule VSL (60/80/110 by thresholds, entry zones fixed at 110), stage-1 arm.
- Pair: D:/VISSIM_runs/20260923_stage1/s31_v2nc (no control). Each run folder has prepared/ (network, fixed_profile.json), run/ (vissim_eval/*.fzp 5 s vehicle records, .ldp, .err, run.json), analysis/scan.json (+ uninserted.json).
- Distributions in the network (x km/h, cumulative fx): 70 = uniform 68-78; 80 = 75/80/90/100/110 at 0/.05/.8/.95/1; 90 = 85/90/100/110/120 at 0/.05/.8/.95/1; 100 = 88/95/100/110/120/130 at 0/.03/.1/.7/.91/1; 110 = 98/105/110/120/130/140 at 0/.03/.1/.7/.91/1. So "90" has median ~96 and "110" median ~117.
HEADLINE (from scan.json region_vh, arm - s31_v2nc, veh.h): fw_e_main fix90 +358.8 (onset 1200-3000 +41.1, peak 3000-6000 +196.1, tail 6000-9000 +121.6), fix70 +554.9, rule VSL +280.6; Omega TTT +378.9 / +572.7 / +302.3; uninserted -135.3 / -106.3 / +50.7. The 150 s deltas grow steadily from 1200 s. The Carlson capacity gain is not visible in totals.
TOOLS:
- Stage-2 harness copy in the SDMPC worktree (untracked, you may add NEW files/folders inside it, never edit existing files): ${CR}. e0_extract.py makes the 31-cell FW_E EO observations (cells_30s etc.) from a run; calib_eval.py (read its docstring) replays the plant open loop (E1a: each arm's own observed boundaries; BOTH arms get their applied FW_E VSL) and reports FW_E metrics; baseline reference calib_baseline/baseline/. Existing observations: inputs/b110_observations/ (NC) and observations/ (RM/BOTH arms). Stage-1 tools: D:/VISSIM-merge/tools/stage1/ (stage1_common.py has region/link maps).
- Plant code: D:/VISSIM-merge/sim3-n31 (branch claude/sdmpc-n31-20260924 @ 75f0151): evaluation/controllers/freeway_fd.py (literature_vsl_parameters, VSLExposure, applied_cohort_commands), area_freeway_accounting.py, diagnostics/sdmpc_n31_20260924 (reference_config_n31_v2.json has freeway.vsl_fd_response and component_vsl_transport with sign cells [0,3,5,8,14,18,26,28]; tests/test_n31_vsl_model.py). The user's source package: read-only worktree D:/VISSIM-merge/review-d80faf9 (diagnostics/vsl_handoff_20260924 = how A0.5_E4 was fitted).
SAFETY (hard): never launch VISSIM, cscript or any .ps1 runner; never kill processes; never modify D:/VISSIM-merge/sim3 (live tree), any frozen copy, or existing files under D:/VISSIM_runs (you may create new folders under ${SP}/vslcheck/<your-name>/ and new files/folders inside ${CR}); no git commits/pushes/checkouts. Python: OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1, at most one heavy Python process of yours at a time (a live SDMPC run and another workflow share the CPU). Use the interpreter the harness uses (see its logs; typically C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe). Never run tests that launch watchdogs (test_b1a_watchdog_attempt_launch.py, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog).
Write your final answer in Korean with numbers and file:line; say what you ran vs only read.`

phase('Extract')
const extract = await agent(`${CTX}
YOUR TASK (name: extract): Produce 31-cell FW_E EO observations for s31_v2fix90, s31_v2fix70 and s31_v2vsl exactly the way e0_extract.py made them for the stage-1 arms (same schema, 30 s frames, boundaries: source inflow, off-ramp exits 10643/10682/10481/10483 flows, ramp merges 10639/10681/10490/10484, plus applied VSL command series per zone from the run's fixed_events.csv / readback / decisions). Write them as NEW folders inside ${CR}/observations_vsl/ (create it). Verify identity checks like E0 (31-cell sum == fw_e_main frame counts from scan.json; pre-1200 s frames identical to s31_v2nc since the arms share history until the first VSL write at 1200 s — report the first differing frame). Also write a short README.md there. Report paths, checks, and anything that differs from the stage-1 extraction.`, {label: 'extract', phase: 'Extract'})

phase('Analyze')
const vissim = () => agent(`${CTX}
EXTRACTION RESULT (from the previous step):
${extract}
YOUR TASK (name: vissim; read-only on runs, scratch in ${SP}/vslcheck/vissim/): Decompose the VISSIM loss of fix90/fix70 vs s31_v2nc on FW_E.
1. Free-flow slowdown component: vehicles traversing the VSL zones at reduced speed while uncongested (use the FZP or the EO cells: per cell speed in uncongested frames, arm vs NC; realized mean speeds under dist 90 / 70 vs 110), and its veh.h.
2. Congestion component: queue formation/extent/timing at B1 (4600-5050 m: 10639 merge @4699, 10682 exit @4747, 10681 merge @5042) and B2 (6842 m 4->3 lane drop, 10483 exit + 10490 merge @7240, 10484 @7604); bottleneck discharge flow (veh/h) during congestion at B1 (downstream of 5050) and B2 (downstream of 7700) for NC vs fix90 vs fix70 vs rule VSL: does a lower limit raise or lower queue discharge? Also off-ramp exits and ramp merges while queued, lane-change counts if cheap.
3. Empirical FD per zone (cells in seg5 5-13, seg10 14-24) under 110 vs 90 vs 70: flow-density and speed-density scatter from 30 s cell frames; estimate free speed, critical density, max flow (with uncertainty), compare to the plant's baseline FD rows and to the Carlson A0.5_E4 predictions (use freeway_fd.literature_vsl_parameters to compute the plant's v_f, rho_c, a at 90/70 for those cells).
4. Why is the uninserted delay lower in the fix arms (-135/-106)? Check input 1098 / 1099 queues vs NC; is it a real effect or accounting.
Return a Korean report with tables.`, {label: 'vissim', phase: 'Analyze'})

const plant = () => agent(`${CTX}
EXTRACTION RESULT (from the previous step):
${extract}
YOUR TASK (name: plant; scratch in ${SP}/vslcheck/plant/, new files allowed inside ${CR} only as new files): What does the plant predict for these fixed-VSL arms, and which VSL law would reproduce VISSIM?
1. Using the calib_eval.py machinery (extend it by a NEW script file, do not edit existing files), run the E1a open-loop replay for the new arms (fix90, fix70, rule VSL) with each arm's own boundaries and its applied FW_E VSL commands mapped to the plant's VSL zones/sign cells exactly as the SDMPC plant does (check how BOTH arms' VSL is applied in calib_eval/e1_replay and how the SDMPC plant maps zones -> sign cells; make sure the Carlson law and VSLExposure transport are actually active in this harness path — the chain audit said the harness reads boundary_config, the SDMPC plant reads reference_config_n31_v2.json which holds freeway.vsl_fd_response/component_vsl_transport; if the harness path does not include them, add them in-memory via the override mechanism and prove they are active).
2. Report plant fw_e_main dTTT (arm - NC) vs VISSIM (+358.8 / +554.9 / +280.6) per window (onset/peak/tail), per segment (seg5/seg10), and the free-flow vs congestion split if you can.
3. Variants: (a) Carlson A0.5_E4 as ported; (b) no VSL law (plain speed-limit: v_f capped by the command only, no capacity change — whatever the plant's non-literature VSL path is); (c) a refit of the law's parameters (e.g. A, E, or a speed-limit-only desired speed with capacity multiplier <= 1) to the fix90/fix70 data (fit on fix90, validate on fix70 and rule VSL, or leave-one-out). Report which variant matches VISSIM best and by how much.
Return a Korean report with tables and exact commands used.`, {label: 'plant', phase: 'Analyze'})

const [rV, rP] = await parallel([vissim, plant])

phase('Synthesize')
const synth = await agent(`${CTX}
YOUR TASK (name: synth; read-only): Synthesize a verdict for the user.
(1) Does VISSIM show any VSL capacity gain on this network (numbers)? (2) Where does the +359/+555 veh.h come from (free-flow slowdown vs congestion, B1 vs B2)? (3) Does the ported Carlson A0.5_E4 law predict the right sign/magnitude; what law should the SDMPC plant use for this network (with evidence), and what would SDMPC then do with VSL (likely: keep 110 unless a law that fits shows a gain somewhere)? (4) Implications for the user's open question about the 110 desired-speed distribution (our 110 = 98-140 median ~117 vs the user's other network 75-145): what does this data say and what would a decisive follow-up native run be (ask, don't decide). (5) Recommended next steps for the SDMPC plant's VSL component.
=== extract ===
${extract}
=== vissim ===
${rV}
=== plant ===
${rP}`, {label: 'synth', phase: 'Synthesize'})

phase('Critique')
const crit = await agent(`${CTX}
YOUR TASK (name: critic; read-only; you may re-check numbers from files): Adversarially review the synthesis and the two analyses. Default to skepticism: single seed (31) only — what can and cannot be concluded; confounds (the 90/70 distributions are not a pure speed-limit change: different shapes; all 4 vehicle classes incl. trucks were set to the same distribution; VSL held after congestion clears); correctness of the free-flow/congestion split; whether the plant replay really had the VSL law active; overfitting of any refit. Output a Korean severity-ordered list of corrections and a corrected short verdict.
=== synth ===
${synth}
=== vissim ===
${rV}
=== plant ===
${rP}
=== extract ===
${extract}`, {label: 'critic', phase: 'Critique'})

return { extract, vissim: rV, plant: rP, synth, critique: crit }