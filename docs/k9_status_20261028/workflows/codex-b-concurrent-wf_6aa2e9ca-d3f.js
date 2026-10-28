export const meta = {
  name: 'codex-b-concurrent',
  description: 'B (codex controller on v3c3) concurrent: new freeze with only the runner seat check changed (allow when VISSIM < 4) and StallSec 3600, preflights, detached seat-aware launcher that starts v3c3-s31/s41/s43 once each as seats free (survives session loss), monitor to completion, analysis per COMPARE_RULE_B (B − NC3, B − V-A), synthesis, adversarial verify, finalize',
  phases: [
    { title: 'Prep', detail: 'FRZ_B1 + preflights + PRE_B_CONCURRENT' },
    { title: 'Launcher', detail: 'detached seat-aware launcher, dry-run, start' },
    { title: 'Monitor', detail: 'until all three runs finish' },
    { title: 'Analyze', detail: 'COMPARE_RULE_B tables' },
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
- No commits, no push, no changes to GWT8 (${GWT8}) or branches; never write into D:/VISSIM-merge/frozen/*; read-only toward existing run folders, D:/VISSIM_handoff/20261024 and Y:.
- VISSIM: only the three declared B runs (v3c3-s31, s41, s43; 9,000 s each), started ONLY by the detached seat-aware launcher of the Launcher stage, results ${BR}/s<seed>, each seed at most once (plus the user's one-time relaunch rule below). PC-wide VISSIM count must stay ≤ 4; other sessions' VISSIM (codex rolling_cea, codex TD3 training) are never touched or killed; never kill by name; kill only PIDs we started. User policy: if a B run shows no progress for 5 minutes beyond its declared normal behaviour, check, then you may kill only its own PIDs and relaunch that seed once, and record it.
- Heavy Python while B runs: BELOW_NORMAL, at most one at a time, PYTHONHASHSEED=0, python -B, detached via WMI for anything > ~5 min; Korean paths: use PowerShell / files with forward slashes.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed: never open sealed/ or data of seeds 37/59/61/67 (any network); never quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Predeclaration: COMPARE_RULE_B.md and PINS_B.sha256 (${CH}/b/, fixed before any B data) stay unchanged; the concurrency change is written in ${CH}/b/PRE_B_CONCURRENT.md and pinned (sha in LOG) BEFORE the first B launch; never change after data; if impossible as written, STOP and report. No verdict words; Ω always with ④ and Ω-outside; ④b first-observation difference main.
- Stop if C: or D: < 8 GB free (keep ≥ 8 GB per run). Append dated (KST) entries to ${CH}/LOG.md.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha 59e41ff5…): D-K9-90 replaces the 'sequential' part of D-K9-88: change only the runner's pre-launch 'refuse if any VISSIM is running' check to 'allow when PC-wide VISSIM < 4', raise StallSec 2,400 → 3,600, controller code and config unchanged (holds are exception-only with no decision time limit, so decision outputs do not depend on wall time); new freeze + per-seed preflight; record the change before B data; a detached launcher starts s31, s41, s43 once each as seats free (up to 3 concurrent). D-K9-88/89 otherwise unchanged (B settings PRE_B §1, stop if s31 abnormal — with concurrency: if any run ends abnormally, the launcher stops launching further seeds and the workflow STOPs with the reason).
- Done earlier (workflow wf_208fe09b-359): gate 1 PASS (${CH}/b/GATE1.md; T=900 replays 296–403 s, 0 exceptions; preflights s31/s41/s43 PASS on FRZ_B0 ${TK}/b0/frozen/sdmpc31_a49981ff_202610260258), COMPARE_RULE_B.md (f902f7f0…) and PINS_B.sha256 pinned, J1 correction memo written (${K8}/j1/analysis/J1_REPORT_CORRECTION.md). No B run was ever launched (${BR} does not exist). The earlier s31 agent's wait script was a foreground poll; nothing of ours is running.
- Seats now: VISSIM 29264 (codex rolling_cea, since 10:14) + 42156/33600/40128 (codex TD3 native training, since 13:20) = 4 (cap). Codex may start new VISSIM at any time; the launcher must re-check the count immediately before each launch and use a lock so it never pushes the PC above 4.
- Plans: ${CH}/b0/PRE_B.md (§1 run definition incl. runner args, env_hsw, wrapper/WMI pattern from ${CH}/a1/A1_LAUNCH.md with RW_* clearing), ${CH}/b0/B0.md r2, ${CH}/A1_B0_RESULTS.md r2, ${CH}/VERIFY_A1_B0.md. Our runs: V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}; NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run.
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
phase('Prep')
out.prep = await agent(`${RULES}\n${CTX}\nTASK (Prep, NO VISSIM): (1) locate the runner's pre-launch VISSIM check and the StallSec setting in the B0 tree (file:line); make a new source tree from FRZ_B0's source with exactly these edits: the check allows launch when the PC-wide VISSIM process count is < 4 (refuses at ≥ 4), StallSec 3,600 — show the full diff; nothing else changes (verify by file-hash diff against FRZ_B0: only the runner file(s) differ); (2) freeze it as FRZ_B1 under ${TK}/b1/frozen/ with the same freeze tool, FREEZE_OK; (3) runner -PreflightOnly for s31, s41, s43 on FRZ_B1 (FREEZE_VERIFIED, network sha 3de889f0…, hold env, StallSec 3600 visible in provenance/watchdog settings, pins); (4) write ${CH}/b/PRE_B_CONCURRENT.md (what changed and why, D-K9-90; launch policy; seat rule; one-time relaunch rule; what concurrency may change: wall times only; what stays: COMPARE_RULE_B and pins) and pin its sha in LOG. Return pass=true only if the diff is exactly as intended and all preflights pass.`, { label: 'prep', phase: 'Prep', schema: SCHEMA })
if (!out.prep || !out.prep.pass) return { stoppedAt: 'Prep', out }

phase('Launcher')
out.launcher = await agent(`${RULES}\n${CTX}\nTASK (Launcher): prep report: ${JSON.stringify(out.prep).slice(0, 2000)}. Write a detached PowerShell launcher ${CH}/b/b_launcher.ps1 that: loops (poll every 60–120 s, logs every poll to ${CH}/b/b_launcher.log); for each seed in order s31, s41, s43 not yet launched: takes an exclusive lock file, counts PC-wide VISSIM processes, and if < 4 launches that seed exactly per PRE_B §1 on FRZ_B1 via the A1-style wrapper (RW_* cleared, env_hsw, PYTHONHASHSEED=0, Normal priority), writes a per-seed marker (so it can never launch a seed twice, even if restarted), records PID/command/time to ${BR}/wmi_launch_lines.txt, then waits until that seed's VISSIM is up before considering the next seed; stops launching if a STOP file ${BR}/STOP_B_LAUNCHER exists or if any launched B run has ended abnormally (runner exit ≠ 0 / no SIM_DONE); never kills anything; gives up after 72 h. Dry-run it first with a test mode (no launch; simulated counts incl. ≥4 busy, free seat, existing marker, STOP file) and keep the dry-run log. Then start it detached via WMI (Invoke-CimMethod Win32_Process Create) so it survives session loss, and confirm it is polling. Also write ${CH}/b/b_status.ps1 (read-only status: per seed launched?, sim_sec/decision T, last progress age, holds, exit) for monitoring. Return pass=true when the launcher runs (seeds may still be waiting for seats); give its PID.`, { label: 'launcher', phase: 'Launcher', schema: SCHEMA })
if (!out.launcher || !out.launcher.pass) return { stoppedAt: 'Launcher', out }

phase('Monitor')
out.monitor = await agent(`${RULES}\n${CTX}\nTASK (Monitor): launcher report: ${JSON.stringify(out.launcher).slice(0, 2000)}. Poll (each wait ≤ 9 min) with b_status.ps1 and the launcher log until all three B runs have completed (SIM_DONE, exit codes) or the launcher stops/gives up. For each run as it starts: check its first control decision T=900 finished with exit 0. Apply the 5-minute no-progress rule only to B runs' own PIDs (one relaunch per seed max; record; the launcher's marker must reflect it). If any run ends abnormally, create ${BR}/STOP_B_LAUNCHER, let other running B runs finish, and return STOP with details. For each finished run record: completion, decision count, holds (T, exception type), decision wall-time distribution (and concurrency at the time), meter/VSL command summaries, 0–895 s FZP prefix equality vs NC3 same seed. Write ${CH}/b/B_RUNS.md (+ copy to ${REP}/b/). Return pass=true if all three completed normally.`, { label: 'monitor', phase: 'Monitor', schema: SCHEMA })
if (!out.monitor || !out.monitor.pass) return { stoppedAt: 'Monitor', out }

phase('Analyze')
out.analyze = await agent(`${RULES}\n${CTX}\nTASK (Analyze per COMPARE_RULE_B.md): verify rule/tool pins (PINS_B.sha256) unchanged; produce the declared tables: B − NC3 per seed (main) and B − V-A per seed (secondary), both integration forms, Ω635 and Ω701 (and Ω-outside on both bases), ④a, ④b (first-observation difference main; stage-1 reference), ④, ①, ②, per-input uninserted (1098, 1099, urban), link 66 line, urban roads under both partitions, LDP signal execution check, meter execution check and green/rate distribution, decision wall times (note concurrency), holds, ramp-arrival forecasts; codex 64cf-s29 joint − NC and A1 − LNC as a separate labelled block (different network, one seed). Write ${CH}/b/B_REPORT.md (+ copy to ${REP}/b/). No verdict words. Return status, Korean summary (<= 25 lines) with key numbers per seed, artifacts with sha256, open.`, { label: 'analyze', phase: 'Analyze', schema: SCHEMA })

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${CH}/b/GATE1.md, b/PRE_B_CONCURRENT.md, b/B_RUNS.md, b/B_REPORT.md, ${K8}/j1/analysis/J1_REPORT_CORRECTION.md (summaries: ${JSON.stringify({ m: out.monitor && out.monitor.summary, a: out.analyze && out.analyze.summary }).slice(0, 8000)}). Write ${CH}/B_RESULTS.md in Korean: (0) plain answer first (<= 12 lines): what the codex controller (RM + TSC, VSL fixed 110) does on our v3c3 baseline per seed vs NC3 and vs our V-A, with Ω always beside ④ and Ω-outside, whether meters moved, holds/exceptions, decision times; (1) tables; (2) what this implies for the takeover question and for activating VSL next (with the VSL-100 observation from A1); (3) numbered user decisions with a recommended option each. No verdict words. Return pass=true with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${CH}/B_RESULTS.md and B_REPORT.md with fresh scripts (no reuse of the authors' scripts): recount Ω701, Ω635, FW_E7 and ④b (first-observation difference) for at least two B − NC3 pairs, re-check the meter/VSL command summaries and holds from the run files, re-check that FRZ_B1 differs from FRZ_B0 only in the declared runner lines; try to refute the plain answer and the recommendations. Write ${CH}/VERIFY_B.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${CH}/VERIFY_B.md to B_RESULTS.md (and sub-reports, keeping _r1 copies, change logs; never keep a refuted claim). Copy finals to ${REP}/. Return status, a Korean summary (<= 25 lines) for the user (per-seed results vs NC3 and vs V-A with Ω beside ④ and Ω-outside, meters/VSL behaviour, holds, decision times, what it means for the takeover and for VSL activation, the decision list with recommended options), artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
