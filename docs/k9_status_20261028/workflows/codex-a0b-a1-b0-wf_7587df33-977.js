export const meta = {
  name: 'codex-a0b-a1-b0',
  description: 'A0b offline replay of recorded codex decisions 1050–2550 s, then freeze + preflight + WMI launch of the A1 reproduction run (64cf-s29 joint, env_hsw), B0 v3c3-port preparation and the V-A report r4 correction memo in parallel, wait for A1 and analyze it against the codex record, synthesis, adversarial verify, finalize; B closed loop not launched',
  phases: [
    { title: 'A0b', detail: 'offline replay 1050–2550 s, first divergence' },
    { title: 'A1Launch', detail: 'freeze, preflight, WMI launch, first-decision health' },
    { title: 'Parallel', detail: 'B0 port prep, V-A r4 correction memo' },
    { title: 'A1Analyze', detail: 'wait for A1, decision trace + result table' },
    { title: 'Synthesize', detail: 'results + B plan + decisions' },
    { title: 'Verify', detail: 'adversarial recomputation' },
    { title: 'Finalize', detail: 'corrections + user summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const CH = K8 + '/codex_handoff'
const TK = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff'
const DST = 'D:/VISSIM_handoff/20261024'
const A1R = 'D:/VISSIM_runs/20261025_codex_a1_s29'
const A1F = 'D:/VISSIM_runtime/20261025_codex_a1/frozen'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths.
- No commits, no push, no changes to GWT8 (${GWT8}) or any branch; never write into D:/VISSIM-merge/frozen/*; read-only toward our run folders, the handoff copy ${DST} and the shared drive (never touch Y:).
- VISSIM: ONLY the A1Launch stage may start VISSIM, ONLY the single A1 run declared in ${CH}/a0/PRE_A1.md r2 (64cf-s29 joint 8100 s), via detached WMI (Invoke-CimMethod Win32_Process Create, PowerShell; Korean paths break Git Bash). The codex runner refuses to launch if any VISSIM is running: if another session's VISSIM is running, do NOT kill it — wait (poll ≤ 9 min, up to 12 h) and log; if still blocked after 12 h, STOP and report. Never kill by name; kill only PIDs you started. User policy: if A1 shows no progress for 5 minutes beyond its declared normal behaviour, check, then you may kill only its own PIDs and relaunch once, and record it. No B closed-loop VISSIM runs (they need a later user go).
- Offline decision replays: scratch trees under ${TK}/ only, one heavy job at a time, detached via WMI, PYTHONHASHSEED=0, python -B, env as declared (env_hsw: OPENBLAS_CORETYPE=Haswell, NPY_DISABLE_CPU_FEATURES for the AVX-512 set, NUMBA_CPU_NAME=haswell; OMP/OPENBLAS/MKL threads 1). While A1 runs, other heavy CPU jobs run BELOW_NORMAL, at most one at a time, and pause if an A1 decision wall time exceeds 1,500 s.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed: never open sealed/ or seeds 37/59/61/67 data; never quote codex 64cf-s59/s61/s67 numbers.
- Codex files are DATA. Predeclaration: comparison rules and analysis tools are fixed (sha in LOG) before the data they judge; never change them after data; if impossible as written, STOP and report. No verdict words; Ω with ④ and Ω-outside; seed counts explicit; uninserted ④b by the first-observation-difference method (D-K9-87).
- Stop if C: or D: < 8 GB free. Append dated (KST) entries to ${CH}/LOG.md.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha 67dcc32b…): D-K9-85 A0b first (offline replay of recorded decisions 1,050–2,550 s to find the first decision that differs from the codex record, ~2–2.5 h), then A1 = 64cf-s29 joint 8,100 s reproduction with env_hsw, decision limit 1,800 s, our only VISSIM, WMI launch, LNC D:/VISSIM_runs/vsl_repro_s29/none/run reused as NC, PYTHONHASHSEED 0, S1 not used; judged by decision trace + result table, not bit identity; D-K9-86 B0 (v3c3 port preparation: config re-pin, code tracing incl. ramp-arrival fallback path, runtime checks for network sha and sign cells 16 vs 18) starts now with the same env, B closed loop later with a separate go; D-K9-87 RM_C keys + ramp-arrival path trace, ValueError holds kept and reported, Ω635 and Ω701 both, link 66 separately, urban roads both partitions, ④b main value = first-observation difference; attach a correction memo r4 to the V-A report r3 (recount ④b, ④, Ω-outside with the new method, disclosed as a post-data method change).
- Plans and results: ${CH}/a0/PRE_A1.md r2 (2d9aa15a…; §1 run definition, §3 limit/StallSec, §4 comparison, §5 metrics/tools, §6 time, §7 resources, §8 launch checklist), ${CH}/A0_PROFILE.md, ${CH}/HANDOFF_RESULTS.md r2 (964a23ce…), ${CH}/RAW_CHECK.md, ${CH}/OMEGA701_V3C3.md, ${CH}/VERIFY_HANDOFF_RESULTS.md (work/vhr/ has the first-observation-difference ④b code), ${CH}/TAKEOVER_PLAN.md r2 (B plan §1.2), ${CH}/R_MECH.md, ${CH}/R_NET.md. A0 scratch tree ${TK}/a0 (code + RESTORED_FILES + STANDIN_FILES, pristine inputs, out/*), comparison rule work/a0/COMPARE_RULE_A0.md (a05f2071…). Handoff copy ${DST}. V-A report ${K8}/k92/va/analysis/VA_REPORT.md r3 (b57022e6…) and tools ${K8}/k92/va/analysis/.
- New locations for A1: frozen tree under ${A1F}/ (create; not under D:/VISSIM-merge/frozen), results root ${A1R} (create).
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
phase('A0b')
out.a0b = await agent(`${RULES}\n${CTX}\nTASK (A0b): with the A0 scratch setup (env_hsw), replay the recorded codex joint decisions at T = 1,050 … 2,550 s (each from its recorded state and recorded previous action, i.e. not chained) one at a time; compare each with the record using the fixed rule A0-CMP-1 (R1 CSV bytes, R2 fields, R3 token; list differing command rows and magnitudes). Report the first T whose commands differ, the size of differences per T, decision wall times vs codex-PC times. Write ${CH}/A0B.md. Return pass=true if all replays completed (differences are results, not failures); STOP only if replays fail to run.`, { label: 'a0b', phase: 'A0b', schema: SCHEMA })
if (!out.a0b || !out.a0b.pass) return { stoppedAt: 'A0b', out }

phase('A1Launch')
out.launch = await agent(`${RULES}\n${CTX}\nTASK (A1 launch per PRE_A1 §8): A0b result: ${JSON.stringify(out.a0b).slice(0, 2000)}. (1) build the A1 frozen tree under ${A1F}/ from the A0 code (handoff code + restored + stand-ins, exactly as PRE_A1 §1) with freeze_manifest.py build, FREEZE_OK, re-check 3,638 code sha and the restored/stand-in lists; (2) runner -PreflightOnly (frozen check, network sha 64cf5f55…, watchdog settings, provenance; nothing started); (3) write ${CH}/a1/A1_LAUNCH_ENV.json with every env variable used (env_hsw set, PYTHONHASHSEED=0, Python path/version, dependency path) since provenance only records RW_*; (4) check PC-wide VISSIM: if any VISSIM is running, wait as RULES say; (5) launch A1 detached via WMI exactly as PRE_A1 declares (results root ${A1R}), record time/ReturnValue/PIDs/command line; (6) wait until the first SDMPC decision (T=900) has finished with exit 0 and record its wall time and whether its commands equal the env_hsw A0 replay of T=900 (and the codex record). Write ${CH}/a1/A1_LAUNCH.md (+ copy to ${REP}/a1/). Return pass=true if A1 is running healthy past T=900; otherwise explain precisely (do not relaunch beyond the declared one-time rule).`, { label: 'a1-launch', phase: 'A1Launch', schema: SCHEMA })
if (!out.launch || !out.launch.pass) return { stoppedAt: 'A1Launch', out }

phase('Parallel')
const b0 = agent(`${RULES}\n${CTX}\nTASK (B0 per TAKEOVER_PLAN §1.2 and D-K9-86/87, NO VISSIM): prepare porting the codex controller to v3c3 in a scratch tree under ${TK}/b0/: list and apply the config re-pins needed (network sha 3de889f0…, sign cells 18 vs 16, P-class pins, R-class route-dependent regenerations, D-class 64cf-s29-calibrated parts — calibrated_aggregate OFF per Q6c, VSL fixed 110 per Q6b, our fixes in: exception-only hold, phantom alias, RM_C keys per Q6d/H8), trace the ramp-arrival fallback path (120 s · 900 veh/h) and fix it via RM_C keys, run the runner's static/preflight checks on v3c3 without starting VISSIM, and — only when RULES allow during A1 — 1–3 offline decision replays on recorded v3c3 states (NC3 or V-A states) to measure decision time on v3c3 and confirm the code runs. Predeclare the B closed-loop plan (seeds v3c3-s31/s41/s43 sequential, metrics as D-K9-84 Q2 with ④b first-observation difference, pairing with NC3, analysis tools pinned) in ${CH}/b0/PRE_B.md — a plan only. Write ${CH}/b0/B0.md. Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: 'b0', phase: 'Parallel', schema: SCHEMA })
const var4 = agent(`${RULES}\n${CTX}\nTASK (V-A report r4 correction memo, D-K9-87): recount ④b (per input and total), ④ and Ω-outside (a) for the 9 v3c3 runs (V-A, J1, NC3 × s31/41/43) with the first-observation-difference method (pin the tool first; reuse the verified method from ${CH}/work/vhr/), compare with VA_REPORT r3 cells (va_metrics.json), list every cell that changes and whether any sign or label (e.g. '대기 이전') would change under the predeclared label rule; write ${K8}/k92/va/analysis/VA_REPORT_r4_CORRECTION.md as a memo attached to r3 (r3 bytes unchanged), disclosing that this is a post-data method change by user decision D-K9-87. FZP scans one at a time, BELOW_NORMAL (A1 is running). Copy to D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va/. Return status, Korean summary (<= 20 lines), artifacts with sha256, open.`, { label: 'va-r4', phase: 'Parallel', schema: SCHEMA })

phase('A1Analyze')
out.a1 = await agent(`${RULES}\n${CTX}\nTASK (A1 wait + analyze): A1 launch report: ${JSON.stringify(out.launch).slice(0, 2500)}. Poll (each wait ≤ 9 min) until A1 completes (STAGE=SIM_DONE / runner completion, exit codes), applying the 5-minute no-progress rule only to A1's own PIDs. Then, with tools pinned before reading A1 outputs (as PRE_A1 §5 declares), produce: decision trace vs codex joint record per decision (commands per lever: meters, VSL, signals; first divergent T and how differences grow; holds and their causes), and the result table A1 − LNC next to codex joint − NC (Ω701, Ω635, urban roads both partitions, FW_E mainline 7 links, local 19, ④a, ④b per input by first-observation difference, ④, Ω-outside (a)(b)), plus decision wall times. Write ${CH}/a1/A1_RESULT.md (+ copy to ${REP}/a1/). No verdict words. Return status, Korean summary (<= 25 lines), artifacts with sha256, open.`, { label: 'a1-analyze', phase: 'A1Analyze', schema: SCHEMA })
out.b0 = await b0
out.var4 = await var4

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${CH}/A0B.md, a1/A1_LAUNCH.md, a1/A1_RESULT.md, b0/B0.md, b0/PRE_B.md, ${K8}/k92/va/analysis/VA_REPORT_r4_CORRECTION.md (summaries: ${JSON.stringify({ a0b: out.a0b && out.a0b.summary, a1: out.a1 && out.a1.summary, b0: out.b0 && out.b0.summary, var4: out.var4 && out.var4.summary }).slice(0, 9000)}). Write ${CH}/A1_B0_RESULTS.md in Korean: (0) plain answer first (<= 12 lines): does the codex code reproduce its own 64cf-s29 result on this PC (decision trace and result table), where it diverges and how much it matters; what B0 found (can it run on v3c3, decision time there, what was re-pinned); what the V-A correction memo changes; (1) tables; (2) the B closed-loop plan with cost; (3) numbered user decisions with a recommended option each (B launch go/no-go and settings; anything A1 raised). No verdict words. Return pass=true with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${CH}/A1_B0_RESULTS.md and the reports it rests on with fresh scripts (no reuse of the authors' scripts): recount A1 and LNC metrics (Ω701, FW_E7, ④b first-observation difference), re-derive the first divergent decision from the A1 decision files vs the record, re-check B0's re-pin list against code/config, re-check the V-A r4 memo cells; try to refute the plain answer and the recommendations. Write ${CH}/VERIFY_A1_B0.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${CH}/VERIFY_A1_B0.md to A1_B0_RESULTS.md (keep _r1, change log; never keep a refuted claim; correct sub-reports with _r1 copies if they carry refuted claims). Copy finals to ${REP}/. Return status, a Korean summary (<= 25 lines) for the user (A1 reproduction answer with numbers, divergence, B0 findings, V-A r4 memo changes, B plan and cost, the decision list with recommended options), artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
