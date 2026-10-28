export const meta = {
  name: 'vsl-v3c3-response',
  description: 'VSL track (D-K9-95): predeclare and run three v3c3 fixed-VSL-only VISSIM runs (s31/s41/s43, native signals, meters open) paired with NC3, plus offline O1 (φ/ρ_crit sensitivity probes) and O2 (plant fidelity under VSL), synthesis, adversarial verify, finalize',
  phases: [
    { title: 'Declare', detail: 'VSL-only run plan + comparison rule, pinned' },
    { title: 'Runs', detail: '3 concurrent v3c3 VSL-only runs (seat-aware launcher)' },
    { title: 'Offline', detail: 'O1, O2' },
    { title: 'Analyze', detail: 'VSL − NC3 tables' },
    { title: 'Synthesize', detail: 'results + decisions' },
    { title: 'Verify', detail: 'adversarial check' },
    { title: 'Finalize', detail: 'corrections + summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const VS = K8 + '/vsl_v3c3'
const TK = 'D:/VISSIM-merge/k8_gate_trees/vsl_v3c3'
const VR = 'D:/VISSIM_runs/20261027_vsl_v3c3'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths.
- No commits, no push, no changes to GWT8 (D:/VISSIM-merge/sim3-n31-k8) or branches; never write into D:/VISSIM-merge/frozen/* or D:/VISSIM-merge/sim3 (read only; make copies under ${TK}/ if a profile/settings copy is needed); read-only toward existing run folders and Y:.
- VISSIM: ONLY the three declared v3c3 fixed-VSL-only runs (s31, s41, s43), results under ${VR}/s<seed>, started by a detached seat-aware launcher (PC-wide VISSIM ≤ 4, lock, per-seed marker so no seed launches twice, logs), via WMI from PowerShell (Korean paths break Git Bash). Other sessions' VISSIM (codex work, the C1 workflow does not launch VISSIM) are never touched; never kill by name; kill only own PIDs; user policy: no progress for 5 minutes beyond normal → check, kill only that run's own PIDs, relaunch once, record.
- Heavy Python (FZP scans, plant probes): take the shared lock ${HL} (create exclusively; wait/retry if present; delete when done) — another workflow (C1) uses it too; BELOW_NORMAL, PYTHONHASHSEED=0, python -B, detached via WMI if > ~5 min.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed: never open sealed/ or data of seeds 37/59/61/67; never quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Predeclaration: the run plan (VSL settings) and the comparison rule + tools are written and pinned (sha in ${VS}/LOG.md) BEFORE the first run starts; O1/O2 rules pinned before running them; never change after data. No verdict words; Ω always with ④ and Ω-outside; ④b first-observation difference main; seed counts explicit.
- Stop if C: or D: < 8 GB free. Append dated (KST) entries to ${VS}/LOG.md (create).
`

const CTX = `
CONTEXT
- Decision ${K8}/K9_1_J1_NOTES_20261013.md (sha bbfe77b0…) D-K9-95: offline O1 (capacity-drop φ and ρ_crit sensitivity probes of the plant) and O2 (plant fidelity when VSL is active) + three v3c3 fixed-VSL-only VISSIM runs (s31, s41, s43; native urban signals, meters open, no SDMPC) paired with NC3 (D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run), ~2 h concurrently, VSL settings fixed before data.
- Evidence so far: ${K8}/c_port/VSL_OFFLINE.md r2 (a8ff255e…; plant: 100 raises cost in 3/4 probed states, 90 in 4/4; φ 1.0, Carlson A0.5/E2.0, merge term the only gain path, solver quantisation/common line search/PFO asymmetry; 64cf-s29 VISSIM: VSL-only (DSD 63–66 = 90, 900–9,000 s) − NC Ω701 −165.2 / ④ −77.6 / Ω-outside (a) +87.6, delayed B2 collapse, B1 spillback 62 → 0 min), ${K8}/c_port/VERIFY_C_PREP.md, ${K8}/rmcause/o1o4/W264_READ.md (64cf VSL-only arm definition D:/VISSIM_runs/vsl_repro_s29/vsl and its json), memory notes on v3c3 VSL: single-value compliance model, DSD 81/91/101 on v3c3 (v3c3 repin), VSL sign zones, v3c3 sign cell 18 = 108.5 m upstream of the 4→3 lane drop; FW_E bottlenecks on v3c3 (10681 merge lane 2, B2/10484) per ${K8}/rmcause/INV_PHYSICS.md; NC3 v3c3 B1 spillback 0/0/2 min (not a collapse regime).
- Run tooling candidates: the fast fixed-profile runner used for the v3c3 rule-RM arms (D:/VISSIM-merge/sim3 diagnostics/fast_fixed_profile.py, fast_nc_run.ps1, fast_nc_runner.vbs; prepared folders under D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3rm*/prepared; the R2c runs D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3rm10681 show how a variant prepared folder was built and launched) — it supports VSL events (rule_policy / fixed profile). Prefer a prepared folder identical to NC3/rule-RM except the VSL event(s).
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
phase('Declare')
out.declare = await agent(`${RULES}\n${CTX}\nTASK (Declare): write ${VS}/PRE_VSL.md: the VSL-only arm on v3c3 — which signs/DSDs (the v3c3 equivalent of codex's seg13 DSD 63–66 near the 4→3 lane drop; state positions, cells, lanes), the speed (90, same as codex's VSL-only arm, and why), the time window (900–9,000 s like codex), everything else identical to NC3 (native signals, meters open/none, same network sha 3de889f0…, seeds 31/41/43, 9,000 s, same NC profile); how the prepared folders are built (diff vs NC3/rule-RM prepared: only the VSL events) and verified (static checks, dry run); the seat-aware launcher design; the comparison rule (VSL − NC3 per seed: Ω701, Ω635, ④a, ④b first-observation difference, ④, Ω-outside, FW_E mainline 7 links, local 19, per-input uninserted 1098/1099/urban, bottleneck speeds/flows by cell/time around B1/B2, spillback minutes, VSL compliance — realised speeds in the VSL zone; first-frame prefix equality with NC3 before 900 s); tools pinned. Build the prepared folders and dry-run them (no VISSIM). Pin everything in LOG. Return pass=true with sha256s.`, { label: 'declare', phase: 'Declare', schema: SCHEMA })
if (!out.declare || !out.declare.pass) return { stoppedAt: 'Declare', out }

phase('Runs')
const runs = agent(`${RULES}\n${CTX}\nTASK (Runs): plan: ${JSON.stringify(out.declare).slice(0, 2500)}. Write and dry-run a detached seat-aware launcher (as declared) and start it via WMI; it launches s31, s41, s43 once each as seats free (≤ 4 PC-wide). Poll (≤ 9 min per wait) until all three finish (completed, exit 0, validation), applying the 5-minute no-progress rule only to own PIDs. Check each run: VSL events applied as declared (readback of DSD/speed settings), completion, prefix equality with NC3 before 900 s. Write ${VS}/VSL_RUNS.md (+ copy to ${REP}/). Return pass=true if all three completed normally; STOP with reason otherwise.`, { label: 'runs', phase: 'Runs', schema: SCHEMA })

phase('Offline')
const offline = agent(`${RULES}\n${CTX}\nTASK (Offline O1 + O2): write and pin rules first. O1: on 3–5 recorded v3c3 states (V-A or B decision states; and the 64cf A1/joint states already probed in VSL_OFFLINE), run plant rollouts (no VISSIM) with VSL 110/100/90 under variants φ ∈ {1.0, 0.95, 0.9, 0.85} and ρ_crit multipliers ∈ {1.0, 0.9, 1.1} (only where the plant accepts them; state which keys) and report where the model's VSL gain sign flips. O2: plant fidelity when VSL is active: replay the 64cf-s29 VSL-only and window arms' recorded states through the plant (open loop, as in earlier fidelity work) and compare predicted vs VISSIM speeds/flows/stocks by cell over the 450 s horizon, VSL on vs off; same on v3c3 once the VSL-only runs exist (if they finish in time; otherwise state 'pending'). Use the shared heavy lock. Write ${VS}/VSL_O1_O2.md. Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: 'offline', phase: 'Offline', schema: SCHEMA })

out.runs = await runs
out.offline = await offline
if (!out.runs || !out.runs.pass) return { stoppedAt: 'Runs', out }

phase('Analyze')
out.analyze = await agent(`${RULES}\n${CTX}\nTASK (Analyze per the pinned comparison rule): verify pins; produce VSL − NC3 per seed tables (both integration forms if declared), bottleneck/time detail, VSL compliance, and place the 64cf-s29 VSL-only − NC numbers as a separate labelled block. Write ${VS}/VSL_REPORT.md (+ copy to ${REP}/). No verdict words. Return status, Korean summary (<= 25 lines), artifacts with sha256, open.`, { label: 'analyze', phase: 'Analyze', schema: SCHEMA })

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${VS}/PRE_VSL.md, VSL_RUNS.md, VSL_REPORT.md, VSL_O1_O2.md. Write ${VS}/VSL_RESULTS.md in Korean: (0) plain answer first (<= 12 lines): does fixed VSL 90 near the v3c3 lane drop help, hurt or do nothing in VISSIM per seed (Ω with ④ and Ω-outside), how it compares with 64cf, what O1/O2 say about the plant's VSL response and which plant changes would make the model see what VISSIM shows; (1) tables; (2) implications for VSL activation in our controller and for the C path; (3) numbered user decisions with recommended options. No verdict words. Return pass=true with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${VS}/VSL_RESULTS.md and the reports with fresh scripts (no reuse of the authors' scripts): recount Ω701, ④ (④b first-observation difference) and FW_E mainline for two VSL − NC3 pairs, re-check VSL compliance from the run files and that only the VSL events differ from NC3, re-check one O1 sign-flip claim; try to refute the plain answer. Write ${VS}/VERIFY_VSL.md. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${VS}/VERIFY_VSL.md (keep _r1 copies, change logs; never keep a refuted claim). Copy finals to ${REP}/. Return status, a Korean summary (<= 20 lines) for the user, artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
