export const meta = {
  name: 'vsl-repro-audit',
  description: 'Audit reproduction of the handed-off seed29 VSL90 experiment: condition diff vs our fix90, Omega 7113.1 vs 7263.267, metric definitions, offline reproduce check',
  phases: [
    { title: 'Audit', detail: 'conditions, omega, metrics, offline reproduction' },
    { title: 'Report', detail: 'user-facing tables' },
    { title: 'Critique', detail: 'adversarial check of the tables' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/vslrepro'
const CTX = `
CONTEXT (you have no other context; read carefully).
The user handed off a VSL experiment package: branch codex/control-full-review-20260909 @ d80faf9, checked out read-only at D:/VISSIM-merge/review-d80faf9. Package: diagnostics/vsl_handoff_20260924/ (README.md, reproduce.py, native.py, analyze.py, assets.json, manifest.json, verification.json, candidate.json, parameters.json, segment_params.json, geometry.json, case_29.json.gz, network/native_seed29.inpx (sha 64cf5f55...) + 42 .sig, evidence/ {RESULTS.md, index.json, accounting/east_link_sets_source.json, native9000_seed29/{FINAL_REVIEW_SEED29.md, summary.json, settings.json, full_audit_seed29.json, east_heatmap.png}, native9000_seed43/, training450_seed29/, heldout450_seed43/, early450_seed43/}). Also docs/vsl_bottleneck90_reproduction_20260924/README.md in that worktree. Its analysis imports diagnostics/control_comparison_20260922/compare.py (Omega definition) from the same worktree.
ORIGINAL EXPERIMENT (as the user states it; verify each item from files, do not trust names): network with freeway east/west 80% and urban 90% demand already applied; seed 29; 9000 s; from 900 s only east DSD63-66 changed from distribution 110 to 90, held to 9000 s; applied at about 6.342 km, lane drop at about 6.842 km; entry/upstream DSD59-62 and DSD67-69 after about 8.09 km stay 110; RM off (no control); native urban signals; SimRes 10; FZP 5 s; the saved demand is kept to the end (never zeroed). Reported: seed29 east local TTT (mainline + entry/exit connectors + direct entry approach links) -6.153%; whole network internal + uninserted outside queue -78.7637 veh.h (-0.2721%); seed43 same policy +67.6357 veh.h (+0.2358%) (a loss, kept as a valid result); seed29 NC Omega TTT 7263.267 veh.h.
OUR RUNS (a DIFFERENT experiment unless proven otherwise; the name "fix90" means nothing):
- D:/VISSIM_runs/20260923_stage1/s31_v2nc (no control) and s31_v2fix90 / s31_v2fix70 (fixed VSL) / s31_v2vsl (rule VSL). Network of s31_v2nc = f475ce42 (also the SDMPC v2 network), fix arms = exact bytes of the s31_v2vsl snapshot fe7f4a7d (same traffic settings, different detectors/evaluation). s31_v2fix90: DSDs 51-66 (link 2 positions 48, 1305, 2652, 3998 m; link 2 starts at fw_e_main chain offset 2734.527 m) all 4 classes -> distribution 90 at 1200 s, held; s31_v2fix70: 90 at 1200 s then 70 at 1350 s. Seed 31. Demand "v2": input 1099 (FW_W entry) reduced to 4300/5600/6000/5200/3900/3450 veh/h (about 45% of v1), everything else from the FW80/U90 both_off_half network with base speed changed 120 -> 110 (a 110 distribution 98-140 added). Each run: prepared/ (network, fixed_profile.json or prepared.json, fixed_events.csv), run/ (vissim_eval/*.fzp, fixed_readback.csv, readback.csv, run.json, *.err), analysis/scan.json (our Omega etc.). Our Omega TTT for s31_v2nc = 7113.1 (scan.json totals.omega_ttt_veh_h), computed by D:/VISSIM-merge/tools/stage1/stage1_scan.py with regions from stage1_common.py; report D:/VISSIM-merge/tools/stage1/out_v2/STAGE1_RESULTS.md; notes D:/VISSIM_runs/20260923_stage1/README.md.
- Our fix90 result vs s31_v2nc (scan.json region_vh): fw_e_main +358.8 veh.h, Omega +378.9, uninserted -135.3; fix70 +554.9 / +572.7 / -106.3.
LIVE (do not touch): native reproduction of the original pair is RUNNING now in D:/VISSIM_runs/vsl_repro_s29 (prepared by the package's native.py prepare --seed 29; the only change is one key concurrent_identity_network_stem added to prepared_{none,vsl}/prepared.json, see concurrency_receipt.json), plus an SDMPC run. Read-only access to D:/VISSIM_runs/vsl_repro_s29/{none.json,vsl.json,preflight.json,prepared_*} is fine.
SAFETY (hard): never launch VISSIM, cscript or any .ps1; never kill processes; never modify anything in D:/VISSIM-merge/review-d80faf9 (run its Python with -B; outputs only to ${SP}/<your-name>/), D:/VISSIM-merge/sim3, D:/VISSIM-merge/sim3-n31 or existing files under D:/VISSIM_runs. No git commits/checkouts. Python: OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1, one heavy process at a time. Interpreter matching the package: C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe (3.12.14, numpy 2.3.5). Do NOT refit anything, do NOT propose or run new 70/90 sweeps; losses are valid results. Do not assume a VSL capacity gain.
Write your final answer in Korean with exact numbers and file:line or file paths; distinguish verified-by-running vs read.`

const conditions = () => agent(`${CTX}
YOUR TASK (name: conditions): Build the exact condition-difference table ORIGINAL (package) vs OUR s31_v2fix90 (and s31_v2nc as its pair), from the actual files, not names.
Rows at least: network file + sha; demand per input (1098 FW_E, 1099 FW_W, urban inputs; time intervals and veh/h) and whether demand is kept to 9000 s; vehicle compositions of the freeway inputs (e.g. vehComp 14 "Freeway entry DSD110" vs 1); desired-speed distribution curves 90 and 110 (points) in each network, and any other distributions used on the east freeway; the list of VSL DSDs changed (numbers, link, lane, position, fw_e chain position in km computed from each network's geometry), the unchanged DSDs (59-62, 67-69 in the original; which in ours), lane drop location in each network; command time and value, vehicle classes written; readback evidence (original: from evidence/settings, summary, full_audit; ours: fixed_events.csv, fixed_readback.csv, readback.csv — prove the DSDs actually held the distribution from the command time to 9000 s); seed; SimRes; simulation period and terminal; FZP interval; RM state; urban signals (native .sig, same 42 files? compare sha); routes/geometry differences (section-by-section diff of the two INPX files: list differing top-level sections and summarize what differs); runner/profile (native-fixed-profile/v1 fields, collect_native_network_performance). Also compare the package's native.py-prepared profile in D:/VISSIM_runs/vsl_repro_s29 with the original evidence settings (should be identical).
Write helper scripts/outputs under ${SP}/conditions/. Return the table (markdown) plus a verdict: same experiment or different, with the decisive differences.`, {label: 'conditions', phase: 'Audit'})

const omega = () => agent(`${CTX}
YOUR TASK (name: omega): Explain why our no-control Omega TTT is 7113.1 (s31_v2nc) while the original seed29 NC Omega TTT is 7263.267.
Check each candidate cause separately: seed (31 vs 29), network (demand, compositions, distributions, geometry — use the conditions from the INPX files), simulation period/terminal, aggregation scope (Omega link membership: compare the package's Omega definition in diagnostics/control_comparison_20260922/compare.py + evidence omega membership proof vs our stage1_common.py region 'urban_omega'... note our 'omega' in stage1_scan may be a union of regions — read stage1_scan.py to see exactly what totals.omega_ttt_veh_h integrates), integration method (their native network-performance measurement vs FZP 5 s trapezoid; start/end handling; vehicles in outside queue), and what counts as internal vs outside. Where possible quantify each difference. If a definitional difference exists, say how to compute the other definition on our FZP (and whether their numbers could be recomputed on our runs), but you cannot run on their FZP (not available). The native reproduction NC run (D:/VISSIM_runs/vsl_repro_s29/none) will finish around 23:15; prepare (do not run on live files) a script that, once it completes, computes BOTH definitions on that FZP so we can reconcile 7263.267 exactly; save it under ${SP}/omega/ with usage notes. Mark conditions that differ as a separate experiment. Return a Korean report with a cause table.`, {label: 'omega', phase: 'Audit'})

const metrics = () => agent(`${CTX}
YOUR TASK (name: metrics): Define precisely, with formulas and link sets, the four metrics and map the original numbers to them: (1) east mainline TTT (analyze.py TTT_FW_E), (2) east local TTT including approaches (the -6.153% scope: mainline + entry/exit connectors + direct entry approach links; see evidence/accounting/east_link_sets_source.json and the docs), (3) Omega TTT, (4) whole-network internal + uninserted outside queue total cost (native network performance; -78.7637 veh.h = -0.2721%; seed43 +67.6357 = +0.2358%). Give base values and deltas/percentages for seed29 and seed43 from the evidence files.
Then compute the closest equivalents for OUR runs (s31_v2fix90, s31_v2fix70 vs s31_v2nc) from our scan.json (region_vh, link_vh, totals, uninserted.json), mapping their link sets to our network (link numbers may be the same network family; verify link existence and lengths). Clearly label ours as a different experiment (seed 31, demand v2, DSD51-66 from 1200 s). Put everything in one table with columns metric | original s29 | original s43 | ours fix90 s31 | ours fix70 s31 and a definitions table. Save helpers under ${SP}/metrics/.`, {label: 'metrics', phase: 'Audit'})

const offline = () => agent(`${CTX}
YOUR TASK (name: offline): Run the package's offline reproduction check exactly as the README says, from the worktree root D:/VISSIM-merge/review-d80faf9, with the matching interpreter and a NEW output folder in scratch: python -B diagnostics/vsl_handoff_20260924/reproduce.py offline --output ${SP}/offline/vsl_offline_s29 (set OMP/NUMBA/MKL threads 1). Read reproduce.py first to know what it checks and writes, and make sure it writes nothing inside the worktree (if it would, stop and report). Report pass/fail of each check: source/input SHA256 manifest, NC and VSL cells/flows/ports/ramps arrays exact vs saved, conservation residual < 1e-7, finite non-negative stocks, predicted TTT NC 140.690656672765 and VSL 140.421537434149, predicted delta -0.269119238616 vs actual -0.325000. If the manifest check fails, determine whether it is line endings (autocrlf on this PC; the worktree shows modified files under reports/ from checkout) or real content differences, without modifying the worktree (you may copy the package to scratch to test a hypothesis, but report the as-is result first). Also report which model code it used (canonical_harness path/sha) and whether that code differs from the SDMPC worktree D:/VISSIM-merge/sim3-n31 (the ported VSL law) — just the file-level diff summary, no fixes.`, {label: 'offline', phase: 'Audit'})

phase('Audit')
const [rC, rO, rM, rOff] = await parallel([conditions, omega, metrics, offline])

phase('Report')
const report = await agent(`${CTX}
YOUR TASK (name: report; read-only): Write the user-facing Korean report from the four audits below. Required sections, in order:
1) 조건 차이표 (원본 seed29 VSL90 vs 우리 s31_v2fix90/s31_v2nc) — exact values, and a clear verdict that ours is a separate experiment if it is, naming the decisive differences.
2) 무제어 Omega TTT 7113.1 vs 7263.267 — cause table (seed/network/demand/duration/scope/integration), what is proven vs pending the running native reproduction.
3) 지표 구분표 — the four metrics with definitions and the numbers (original s29, s43; ours labelled separate).
4) offline 재현 검사 결과 — each check pass/fail with values.
5) native 재현 상태 — running since 21:41/21:44 in D:/VISSIM_runs/vsl_repro_s29 (one key added to prepared.json for concurrency; nothing else changed); what will be compared when it finishes (analyze.py outputs vs evidence numbers; both Omega definitions on the same FZP).
6) 다음 단계 (after reproduction): feed the actual commands into the plant from the same initial state and compare discharge / stock / queue-cost changes; explicitly NOT doing Carlson refit or new 70/90 sweeps before the user reviews.
Keep it compact: tables first, short prose. No speculation beyond evidence.
=== conditions ===
${rC}
=== omega ===
${rO}
=== metrics ===
${rM}
=== offline ===
${rOff}`, {label: 'report', phase: 'Report'})

phase('Critique')
const crit = await agent(`${CTX}
YOUR TASK (name: critic; read-only; re-check numbers against the files): Adversarially check this report. Every number in the tables must be traceable to a file you open; flag any that are not, any mislabelled metric (mixing the 450 s 31-cell scope, east local scope, Omega and whole-network+outside), any claim that our fix90 reproduces the original, any hidden assumption of a capacity gain, and any omission the user asked for (INPX, distribution curves, command table, readback checked; Omega cause; offline check; native status). Return a Korean list of required corrections (severity-ordered) and then the corrected report in full.
=== report ===
${report}
=== conditions ===
${rC}
=== omega ===
${rO}
=== metrics ===
${rM}
=== offline ===
${rOff}`, {label: 'critic', phase: 'Critique'})

return { conditions: rC, omega: rO, metrics: rM, offline: rOff, report, critique: crit }