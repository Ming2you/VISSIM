export const meta = {
  name: 'vsl-plant450-and-v5b-decomp',
  description: 'Item 1: package-plant 450 s VSL90 comparison prep (plant deltas + VISSIM extraction validated on NC). Item 2: decompose V5b +417 and rank SDMPC vs native urban plans in the plant',
  phases: [
    { title: 'Analyze', detail: 'plant450 | v5b decomposition | v5b plan ranking' },
    { title: 'Verify', detail: 'adversarial check per track' },
    { title: 'Report', detail: 'Korean synthesis' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const SAFE = `
SAFETY (hard): Do not launch VISSIM, cscript or any .ps1 runner/replay script; never kill processes. A native VISSIM run is LIVE right now in D:/VISSIM_runs/vsl_response2250_s29 (package run_commands.ps1: NC then VSL, 2250/3000) — do not touch that folder except reading finished files. Never modify: D:/VISSIM-merge/review-d80faf9, D:/VISSIM-merge/review-7216e25, D:/VISSIM-merge/frozen/*, D:/VISSIM-merge/sim3, tracked files of D:/VISSIM-merge/sim3-n31, or existing files under D:/VISSIM_runs (you may create NEW folders under ${SP}/<track>/ only). Run Python with -B. Threads: OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1; at most one heavy Python process of yours at a time. No git commits/checkouts. Do NOT recalibrate or refit anything, do not assume a VSL capacity gain; losses are valid results. Write the final answer in Korean with exact numbers, file paths/lines, and mark [실행] (you ran it) vs [읽음] (read only).`

const plant450 = () => agent(`
CONTEXT: The user's handed-off VSL package is Ming2you/VISSIM @ d80faf9, checked out read-only at D:/VISSIM-merge/review-d80faf9; package dir diagnostics/vsl_handoff_20260924 (README.md, reproduce.py, case_29.json.gz = common initial state at cutoff 2220.1 s + history-based boundary forecast + executed commands, candidate.json, parameters.json, segment_params.json, geometry.json, evidence/training450_seed29/{protocol.json, check_summary.json, REPORT.md, ...}). The package's 450 s case: seed 29, common state 2220.1 s, VSL90 on DSD63-66 from 2250 s, 450 s horizon; scope = east 31 cells + 4 on / 4 off connectors, 30 s stock integration; predicted TTT NC 140.690656672765 / VSL 140.421537434149 (delta -0.269119), actual NC 137.6292 / VSL 137.3042 (delta -0.325). On this PC the offline check reproduces everything except one NC cells value differing by 1 ULP (user accepted this as a platform difference). A previous agent's diagnostic script that runs the same functions without stopping at the first failure is ${SP}/vslrepro/offline/diag_offline.py (outputs diag_asis.json etc.). Interpreter: C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe (3.12.14, numpy 2.3.5), run from the worktree root.
Native data: the 9000 s seed29 NC/VSL pair was reproduced bit-exactly in D:/VISSIM_runs/vsl_repro_s29/{none,vsl}/run (FZP 5 s in vissim_eval/, VSL from 900 s — NOT the 450 s case). The matching short native pair for the 450 s case is running now in D:/VISSIM_runs/vsl_response2250_s29/{none,vsl}/run (VSL from 2250 s, terminal 3000 s); its NC arm is traffic-identical to the 9000 s NC run up to 3000 s.
YOUR TASK (track name: plant450; scratch ${SP}/plant450/):
1. Produce and save the package plant's predicted NC and VSL arrays for case_29 (cells, flows, ports, ramps; per 30 s and per second if available), with the exact time grid, using the package code (reuse diag_offline.py logic; do not edit the worktree).
2. From the evidence and code, establish exactly how the package computed the ACTUAL side (which FZP, which time window e.g. 2220.1->2670.1 or 2250->2700, which links/cells/connectors, 30 s stock trapezoid) so the comparison is apples to apples.
3. Define the comparison quantities and compute them for the plant (NC, VSL, delta): (a) discharge: vehicle passages per 30 s and in total across the lane-drop section (6.842 km, cell 18->19 boundary), off-ramp 10481 and 10483 exits, merges 10490 (->cell 21) and 10484 (->cell 23), upstream entry and downstream exit of the 31-cell chain; (b) stock: per-cell vehicle counts over time and connector stocks; (c) queue cost: on-ramp connector / ramp queue residence veh.h and any origin/external queue the plant carries; (d) the 31+8 TTT total. Report the plant's delta decomposition: which part of -0.269 comes from which cells/ports, and how much of the plant's change comes from the FD capacity change of the A0.5_E4 law (e.g. compare with a plant run where the VSL command changes only desired speed without the law's capacity change, if the package code allows an in-memory switch; otherwise explain).
4. Write a VISSIM-side extraction script (FZP-based, same geometry.json cells/chain offsets and connector links, same time grid and quantities) and VALIDATE it now on the NC arm using D:/VISSIM_runs/vsl_repro_s29/none/run FZP over the 450 s window: its 31+8 TTT must reproduce the package's actual NC 137.6292 (report exact match or the residual and why). Leave the script ready to run on D:/VISSIM_runs/vsl_response2250_s29/vsl/run once it finishes (give the exact command). Also report the NC-side observed quantities.
${SAFE}`, {label: 'plant450', phase: 'Analyze'})

const v5bdecomp = () => agent(`
CONTEXT: SDMPC-31 closed-loop 9000 s run V5b: D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b (network f475ce42, seed 31, SimRes 10; FZP vissim_eval/sdmpc31_sdmpc31_v2_s31b_001.fzp with a frame at 0.1 s then every 5 s; decisions_sdmpc31_v2_s31b/action_*.json|csv = per-decision actions incl. urban green_times per SC/phase, offsets, signal_sg rows; signal_readback.csv; vsl_readback.csv). It was paired with the native no-control run D:/VISSIM_runs/20260923_stage1/s31_v2nc (same network/seed/SimRes; frames identical through 900.1 s, first difference at 905.1 s). A stage-1-style scan of V5b is in ${SP}/v5b_scan/analysis/scan.json (+uninserted.json); the NC scan is D:/VISSIM_runs/20260923_stage1/s31_v2nc/analysis/scan.json. Scan code and region/link definitions: D:/VISSIM-merge/tools/stage1/{stage1_scan.py, stage1_common.py}. Headline V5b - NC (veh.h): Omega +417.3 (7530.4 vs 7113.1), fw_e_main +252.7, urban_omega +311.4, offramp -149.7, fw_w_main +2.2, outside +235.3, all links +653.6, uninserted -101.9. In V5b the freeway levers did nothing (all 488 meter commands green 10 of 10 s, readback GREEN; all VSL commands 110 = base), so the difference comes from SDMPC's urban signal control (17 SCs: green splits and offsets every 150 s; e.g. at 3000 s SC1 offset 59.8 vs native 131, SC16 0.07 vs native 149). Native signal programs: the 42 .sig files next to the network (D:/VISSIM_runs/20260923_stage1/s31_v2nc/prepared/network/*.sig); a native timeline table may exist as signal_timeline_from_sig_20260823.json somewhere under D:/VISSIM-merge (search).
YOUR TASK (track name: v5bdecomp; scratch ${SP}/v5bdecomp/):
1. Decompose V5b - NC by region and by link (scan.json link_vh exists) and by 150 s bin: which urban links/approaches (grouped by signal controller and approach) gain or lose; where on FW_E (by chain position / link) the +252.7 accrues and when.
2. Test the off-ramp spillback hypothesis: for each FW_E off-ramp (10643->126, 10682->121, 10481->127, 10483->124) and its urban receiver, compare V5b vs NC queue/occupancy on the receiver and connector over time, exit flows, and whether the FW_E loss is located just upstream of those exits at the same times. Quantify how much of the FW_E +252.7 is explained by blocked exits.
3. Tabulate SDMPC's urban actions vs native: per SC, cycle, splits and offset over decisions; how often and by how much offsets/splits change between consecutive decisions (transition frequency); relate the SCs with the largest action deviations to the SCs with the largest delay increases.
4. Early window check: in the first windows after 900 s (where states are still nearly equal) compare per-SC delay V5b vs NC to see where the divergence starts.
${SAFE}`, {label: 'v5b-decomp', phase: 'Analyze'})

const v5brank = () => agent(`
CONTEXT: SDMPC-31 closed-loop run V5b (D:/VISSIM_runs/20260924_sdmpc31/sdmpc31_v2_s31b) lost Omega +417 veh.h vs the native no-control pair (s31_v2nc) while its freeway levers stayed at no-control values; the only lever it moved was urban signals (green splits and offsets of 17 SCs every 150 s). Question to decide: does the SDMPC plant rank SDMPC's chosen urban plan above the native plan (then the plant/objective disagrees with VISSIM -> plant or missing transition-loss problem), or does the plant itself prefer the native plan (then the optimizer/objective chose against its own model)?
Resources: source tree identical to V5b's frozen copy (442 files same hash, other 8 differ only by CRLF): D:/VISSIM-merge/review-7216e25 (read-only; the frozen launch copy is D:/VISSIM-merge/frozen/sdmpc31_7216e253_202609241509 — do not touch). A previous plant trace built isolated replay states and scoring tools you should reuse: scripts in ${SP}/rm_trace/plant/ (capture.py, probe.py, plans.py, hooks.py, analyze.py, prepare_copy.py, results.py; RESULTS.json; T2700/T3000/T3300 subfolders with record.json and cont/ traces) and isolated replay state folders D:/VISSIM_runs/20260924_sdmpc31/rm_trace_plant_T2700, rm_trace_plant_T3000, rm_trace_plant_T3300 (read-only copies; if you need to write, copy to your scratch). That trace scored alternative METER plans with the exact coupled plant and the continuous surrogate from those states; you need the same for URBAN signal plans. The V5b decisions folder decisions_sdmpc31_v2_s31b has action_*.json (fields green_times, offsets, ramp_metering, vsl, prediction, held/joint diagnostics). The last pre-SDMPC action action_000750.json (no-control phase) may already encode the native plan in SDMPC action format — check; otherwise build the native plan (splits/offsets/cycle per SC) from the network .sig files (D:/VISSIM_runs/20260923_stage1/s31_v2nc/prepared/network/*.sig) and the SDMPC signal mapping, and document the mapping.
YOUR TASK (track name: v5brank; scratch ${SP}/v5brank/): At the three prepared states (2700, 3000, 3300 s) and, if cheap, one early state (e.g. 1050 or 1200 s, preparing it like prepare_copy.py did — only offline Python, no .ps1), score over the SDMPC horizon with the SAME plant and objective SDMPC used: (a) SDMPC's chosen action at that decision, (b) the native urban plan (meters cap, VSL 110 unchanged), (c) the previous applied action held (if different). Report J for each (exact coupled plant and continuous surrogate), the sign of J(a)-J(b), and per-SC contributions if available. Also report whether the plant's objective includes any offset-transition cost. Conclude which branch applies (plant prefers native vs plant prefers SDMPC) with the evidence strength; do not speculate beyond the runs.
${SAFE}`, {label: 'v5b-rank', phase: 'Analyze'})

const verify = (name, report) => agent(`
You are an adversarial verifier for the track "${name}". Default to skepticism. Re-check at least three key numbers yourself from the cited files (re-run small read-only computations if needed), check that metrics are not mixed (scopes, time windows, integration rules), that no claim goes beyond the evidence (single seed; plant vs VISSIM windows), that the SAFETY rules were respected, and that nothing assumed a VSL capacity gain or recalibrated anything. Output a Korean severity-ordered list of corrections, then a corrected concise version of the track's conclusions.
${SAFE}
=== report ===
${report}`, {label: `verify:${name}`, phase: 'Verify'})

phase('Analyze')
const [r1, v1] = await Promise.all([
  (async () => { const r = await plant450(); const v = await verify('plant450', r); return [r, v] })(),
  (async () => {
    const [d, k] = await parallel([v5bdecomp, v5brank])
    const [vd, vk] = await parallel([() => verify('v5b-decomp', d), () => verify('v5b-rank', k)])
    return [[d, k], [vd, vk]]
  })(),
])
const [rPlant, vPlant] = r1
const [[rDecomp, rRank], [vDecomp, vRank]] = v1

phase('Report')
const report = await agent(`
Write the Korean user-facing report from the verified tracks below. Two sections:
(1) VSL 450초 plant 대조 준비 상태: plant delta table (discharge / stock / queue cost / 31+8 TTT, NC vs VSL), how much comes from the law's capacity change, the actual-side definition, NC-side validation result of the extraction script (exact or residual), and the exact command to run on the VSL short run when it finishes. State clearly that the VISSIM VSL-side comparison is pending the running short run.
(2) V5b +417 분해: region/link/time decomposition, off-ramp spillback share of the FW_E loss, SDMPC urban action vs native (transition frequency), and the plant ranking result (plant prefers SDMPC plan or native plan) with evidence strength and what it implies (plant error vs optimizer/objective vs missing transition cost).
Apply every correction from the verifiers. Tables first, short prose, no speculation. Mark [실행]/[읽음].
=== plant450 ===
${rPlant}
=== verify plant450 ===
${vPlant}
=== v5b-decomp ===
${rDecomp}
=== verify v5b-decomp ===
${vDecomp}
=== v5b-rank ===
${rRank}
=== verify v5b-rank ===
${vRank}`, {label: 'report', phase: 'Report'})

return { plant450: rPlant, verify_plant450: vPlant, v5b_decomp: rDecomp, verify_decomp: vDecomp, v5b_rank: rRank, verify_rank: vRank, report }