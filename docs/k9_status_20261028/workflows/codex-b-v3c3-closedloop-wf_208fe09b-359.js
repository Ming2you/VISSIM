export const meta = {
  name: 'codex-b-v3c3-closedloop',
  description: 'B: gate 1 (4 offline T=900 replays on v3c3, no VISSIM), then if exceptions 0 and max decision ≤ 1,500 s launch B closed loop v3c3-s31 → s41 → s43 one at a time (WMI, wait for other VISSIM, stop on abnormal s31), J1 report correction memo in parallel, analysis per PRE_B paired with NC3 and V-A, synthesis, adversarial verify, finalize',
  phases: [
    { title: 'Gate1', detail: 'COMPARE_RULE_B + 4 T=900 replays' },
    { title: 'BRuns', detail: 's31 → s41 → s43 closed loop' },
    { title: 'Side', detail: 'J1 report correction memo' },
    { title: 'Analyze', detail: 'B − NC3, B − V-A tables' },
    { title: 'Synthesize', detail: 'results + decisions' },
    { title: 'Verify', detail: 'adversarial recomputation' },
    { title: 'Finalize', detail: 'corrections + user summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const CH = K8 + '/codex_handoff'
const TK = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff'
const BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths.
- No commits, no push, no changes to GWT8 (${GWT8}) or branches; never write into D:/VISSIM-merge/frozen/*; read-only toward existing run folders, the handoff copy D:/VISSIM_handoff/20261024 and Y:.
- VISSIM: ONLY the BRuns stage may start VISSIM, ONLY the three declared B runs (v3c3-s31, then s41, then s43; 9,000 s each) from the B frozen tree per ${CH}/b0/PRE_B.md §1, one at a time, via detached WMI from PowerShell (Korean paths break Git Bash), results under ${BR}/s<seed>. The codex runner refuses to launch while any VISSIM runs: if another session's VISSIM is running, never kill it — wait (poll ≤ 9 min, up to 12 h per launch) and log; if still blocked, STOP and report. Never kill by name; kill only PIDs you started. User policy: if a B run shows no progress for 5 minutes beyond its declared normal behaviour, check, then you may kill only its own PIDs and relaunch once, and record it.
- Offline replays (Gate1): scratch under ${TK}/ only, one at a time, detached via WMI, PYTHONHASHSEED=0, python -B, env_hsw as PRE_B §1. While a B run is going, other heavy CPU jobs run BELOW_NORMAL, at most one at a time.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed: never open sealed/ or data of seeds 37/59/61/67 (any network); never quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Predeclaration: COMPARE_RULE_B.md (with the ④ integration forms written out explicitly: our form [0, 9000] s and codex form = time-axis trapezoid over [0, 8100] s, anchored as verified in VERIFY_A1_B0) and the analysis tool list (PRE_B §4, path-constant-only copies allowed and logged) are fixed (sha in LOG) BEFORE the first B launch; never change after data; if impossible as written, STOP and report. Gate 1 rule and its replay comparison are fixed before the replays. No verdict words; Ω always with ④ and Ω-outside; seed counts explicit; ④b by first-observation difference (main), stage-1 reconstruction as a reference column.
- Stop if C: or D: < 8 GB free (and keep ≥ 8 GB per upcoming run). Append dated (KST) entries to ${CH}/LOG.md.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha d248605e…): D-K9-88 gate 1 = 4 offline replays of the first v3c3 control decision T=900 (no prior sdmpc_state; states from our existing v3c3 runs as PRE_B §2-1 says — choose and declare which 4 before running), VISSIM 0, ~1 h; if every replay has 0 exceptions and the max decision wall time ≤ 1,500 s, launch B closed loop v3c3-s31 → s41 → s43 one at a time; if s31 is abnormal (unheld exception/STOP, stall, abnormal termination, decision > StallSec, or a declared S-rule), stop and ask; wait up to 12 h for other VISSIM; D-K9-89 B settings exactly PRE_B §1; 64cf-derived codex contracts (11) and D-class coefficients kept and labelled; no A1 repeat; no T=1,200 cause trace; VSL-100 reason after B; V-A r4 stays a memo; attach the same correction memo to J1_REPORT.
- Plans/results: ${CH}/b0/PRE_B.md (§1 run definition, §2 gates, §3 metrics, §4 pinned tools, §5 monitoring/stop, §6 time), ${CH}/b0/B0.md r2 (11fa7578…; FRZ_B0 ${TK}/b0/frozen/sdmpc31_a49981ff_202610260258, FREEZE.json 853d1c4f…, config diagnostics/b0_v3c3/config_b0_v3c3.json 729640af…; the 3 earlier replays stopped at sdmpc.py:783 prior-context mismatch), ${CH}/A1_B0_RESULTS.md r2, ${CH}/a1/A1_LAUNCH.md (wrapper/WMI pattern, env record, RW_* clearing incl. the pwsh SetEnvironmentVariable(null) pitfall), ${CH}/VERIFY_A1_B0.md (codex form = time-axis trapezoid). V-A runs D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}; NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run; J1 runs D:/VISSIM_runs/20261004_sdmpc31_k8/…; J1 report ${K8}/j1/analysis/J1_REPORT.md; V-A r4 memo ${K8}/k92/va/analysis/VA_REPORT_r4_CORRECTION.md (method/tools in ${K8}/k92/va/analysis/r4/).
`

const SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['PASS', 'STOP', 'PARTIAL'] },
    pass: { type: 'boolean' },
    summary: { type: 'string' },
    artifacts: { type: 'string' },
    open: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'pass', 'summary', 'artifacts', 'open'],
}

const out = {}
phase('Gate1')
out.gate1 = await agent(`${RULES}\n${CTX}\nTASK (Gate 1 + rule fixing): (1) write ${CH}/b/COMPARE_RULE_B.md per PRE_B §3/§4 with the ④ integration forms spelled out, make path-constant-only tool copies if needed, and pin all (sha in LOG); (2) declare the 4 T=900 replay states (from our v3c3 runs; at least one per seed s31/s41/s43) and the pass condition (0 exceptions, every decision finishes, max wall ≤ 1,500 s) in ${CH}/b/GATE1_RULE.md, pin it; (3) run the 4 replays one at a time on the B frozen tree code (env_hsw), record exceptions, wall times, chosen meter/VSL/signal commands, ramp-arrival forecast totals (RM_C path), holds; (4) re-run the runner -PreflightOnly for s31, s41, s43 (FREEZE_VERIFIED, network sha, hold policy env, pins). Write ${CH}/b/GATE1.md. Return pass=true only if the gate condition holds for all 4 and all 3 preflights pass; otherwise STOP with the exact reason (do not launch anything).`, { label: 'gate1', phase: 'Gate1', schema: SCHEMA })
if (!out.gate1 || !out.gate1.pass) return { stoppedAt: 'Gate1', out }

phase('Side')
const j1memo = agent(`${RULES}\n${CTX}\nTASK (J1 report correction memo, D-K9-89 ⑦): like the V-A r4 memo, recount ④b (first-observation difference), ④ and Ω-outside (a) for the J1 pairs (J1 − NC3, per seed) with the pinned r4 method/tools, compare with J1_REPORT cells, list changed cells and any label change under the J1 predeclared label rule; write ${K8}/j1/analysis/J1_REPORT_CORRECTION.md (J1_REPORT bytes unchanged; disclose post-data method change by user decision). BELOW_NORMAL, one FZP scan at a time (B runs may be going). Copy to D:/VISSIM_runs/20261001_v3c3/reports/k8/. Return status, Korean summary (<= 15 lines), artifacts with sha256, open.`, { label: 'j1-memo', phase: 'Side', schema: SCHEMA })

phase('BRuns')
out.bruns = []
for (const seed of [31, 41, 43]) {
  const r = await agent(`${RULES}\n${CTX}\nTASK (B run v3c3-s${seed}): gate 1 result: ${JSON.stringify(out.gate1).slice(0, 1500)}. Previous B runs: ${JSON.stringify(out.bruns.map(x => x && { status: x.status, summary: (x.summary || '').slice(0, 600) }))}. (1) confirm COMPARE_RULE_B.md and tool pins unchanged (sha), disk space, no VISSIM running (wait as RULES say), and that the previous B run (if any) finished (STAGE=SIM_DONE, exit codes, holds, .err) — if the previous run ended abnormally, STOP; (2) launch v3c3-s${seed} exactly per PRE_B §1 via the A1-style wrapper/WMI (results ${BR}/s${seed}), record env (RW_* cleared correctly), time, PIDs, command line; (3) check the first control decision T=900 finished with exit 0; (4) poll (each wait ≤ 9 min) until the run completes, applying the 5-minute no-progress rule only to its own PIDs; (5) record completion state, decision count, holds (T, exception type), decision wall-time distribution, meter/VSL command summaries, and the 0–895 s FZP prefix equality vs NC3 v3c3-s${seed}. Write ${CH}/b/B_RUN_s${seed}.md. Return pass=true if the run completed normally; STOP with exact reason otherwise${seed === 31 ? ' (for s31 any abnormality ⇒ STOP and the user decides before s41)' : ''}.`, { label: 'b-run-s' + seed, phase: 'BRuns', schema: SCHEMA })
  out.bruns.push(r)
  if (!r || !r.pass) return { stoppedAt: 'BRun_s' + seed, out, j1memo: await j1memo }
}
out.j1memo = await j1memo

phase('Analyze')
out.analyze = await agent(`${RULES}\n${CTX}\nTASK (Analyze per COMPARE_RULE_B.md): verify rule/tool pins; produce the declared tables: B − NC3 per seed (main) and B − V-A per seed (secondary), both integration forms, Ω635 and Ω701 (and Ω-outside for both bases), ④a, ④b (first-observation difference main; stage-1 reference), ④, ①, ②, per-input uninserted (1098, 1099, urban), link 66 line, urban roads under both partitions, LDP signal execution check, meter execution check and green/rate distribution, decision wall times, holds, ramp-arrival forecasts; also place codex 64cf-s29 joint − NC and A1 − LNC as a separate labelled block (different network, one seed). Write ${CH}/b/B_REPORT.md (+ copy to ${REP}/b/). No verdict words. Return status, Korean summary (<= 25 lines) with key numbers per seed, artifacts with sha256, open.`, { label: 'analyze', phase: 'Analyze', schema: SCHEMA })

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${CH}/b/GATE1.md, b/B_RUN_s31.md, b/B_RUN_s41.md, b/B_RUN_s43.md, b/B_REPORT.md, ${K8}/j1/analysis/J1_REPORT_CORRECTION.md (summaries: ${JSON.stringify({ g: out.gate1 && out.gate1.summary, a: out.analyze && out.analyze.summary, j: out.j1memo && out.j1memo.summary }).slice(0, 8000)}). Write ${CH}/B_RESULTS.md in Korean: (0) plain answer first (<= 12 lines): what the codex controller (RM + TSC, VSL fixed 110) does on our v3c3 baseline per seed vs NC3 and vs our V-A, with Ω always beside ④ and Ω-outside, whether meters moved, holds/exceptions, decision times; (1) tables; (2) what this implies for the takeover question and for activating VSL next (with the VSL-100 observation from A1); (3) numbered user decisions with a recommended option each. No verdict words. Return pass=true with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${CH}/B_RESULTS.md and B_REPORT.md with fresh scripts (no reuse of the authors' scripts): recount Ω701, Ω635, FW_E7 and ④b (first-observation difference) for at least two B − NC3 pairs, re-check the meter/VSL command summaries and holds from the run files, re-check the J1 correction memo cells; try to refute the plain answer and the recommendations. Write ${CH}/VERIFY_B.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${CH}/VERIFY_B.md to B_RESULTS.md (and sub-reports, keeping _r1 copies, change logs; never keep a refuted claim). Copy finals to ${REP}/. Return status, a Korean summary (<= 25 lines) for the user (per-seed results vs NC3 and vs V-A with Ω beside ④ and Ω-outside, meters/VSL behaviour, holds, what it means for the takeover and for VSL activation, the decision list with recommended options), artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
