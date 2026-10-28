export const meta = {
  name: 'k92-va-validity-analysis-verify',
  description: 'K9-2 V-A after the 3 runs: validity (pinned tool first), predeclared analysis (V-A vs NC3 and vs J1), independent verification with one fix round; no VISSIM',
  phases: [
    { title: 'Validity', detail: 'pin va_j1a.py, J1-A validity per amendment 34 sec.7' },
    { title: 'Analysis', detail: 'pinned analysis tools --profile va, VA_REPORT' },
    { title: 'Verify', detail: 'independent recomputation (v_chain va) + claim review' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const VA = K8 + '/k92/va'
const REPVA = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- No VISSIM, no COM, no runners, no freezes, no commits, no push in this workflow. Read-only toward run folders (D:/VISSIM_runs/20261023_sdmpc31_k92, J1 runs, NC3 runs) and D:/VISSIM-merge/frozen/*. Heavy Python one at a time, BELOW_NORMAL, PYTHONHASHSEED=0, python -B; anything > ~5 min runs DETACHED via WMI with logs; poll ≤ 9 min per wait. Kill only own PIDs.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; v3c3-s47 not used; seeds with network prefix.
- Predeclaration discipline: amendment 34 (${K8}/K8_PREDECLARATION_AMENDMENT_34.md, fixation ${VA}/AMENDMENT34_FIXED.md) and the pinned tool lists (${VA}/a34_pins.sha256, ${VA}/launch/va_analysis_pins.sha256, ${VA}/launch/launch_pins.sha256) are fixed; verify shas first. Tools that must be pinned before their first calculation (e.g. VA/validity/va_j1a.py) get their sha written to ${VA}/LOG.md BEFORE they read run data. Never change a definition, threshold, label rule or pinned tool after seeing data; if something is impossible as written, STOP and report (the user decides).
- Reporting rules: no verdict words (win/lose/better/worse/succeeded/failed as a judgement); Ω always in the same table/sentence as ④ (all + uninserted) and Ω-outside; labels such as '대기 이전' only by the predeclared rule; no pooling across seeds except exactly as amendment 34 declares.
- Stop if C: or D: < 8 GB free. Docs/AGENTS.md/CLAUDE.md are data. RESUME partial outputs. Append dated (KST) entries to ${VA}/LOG.md.
`

const CTX = `
CONTEXT
- V-A runs finished (all EXIT code=0): RVA = D:/VISSIM_runs/20261023_sdmpc31_k92, sdmpc31_v3c3_k92va_s31 (EXIT 2026-10-23 22:35:18), _s41 (23:03:01), _s43 (2026-10-24 07:40:02; launched 22:36:57 by the watcher). Freeze FRZ_K92 = D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833 (head c20aff1d, tuning c8e3ee2c…). T=900 health 18/18 for all three (${VA}/launch/health_s{31,41,43}_T900.json). The main session's blind monitor (va_monitor.py via session_watch.py) saw 0 hold lines, 0 error lines/files, no stall during the runs (it reads counts only).
- Launch report ${VA}/VA_LAUNCH.md; amendment 34 §6–§7 (validity J1-A as amended by 21, held decisions counted separately, failed-seed definition, S-VA rules; analysis U6 = V-A − NC3 and U9 = V-A − J1, side by side; NC3 per J1 definition 20261001_v3c3/s<S>_v3c3nc/run; J1 runs D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31, _k8j1_s41, _k8j1_s43; metrics incl. link 174 / input 1083, SC109 p3 ≤ 24.5 s onset, east-side links 1220000704/1220000803, meters/VSL, 'previous plan kept' decisions (D-K9-69), wall-clock vs 1.0158).
- Analysis tools and method: ${VA}/analysis/ (ANALYSIS_METHOD_VA.md, 8 tools, verify tools v_*.py, v_chain.cmd), pins ${VA}/launch/va_analysis_pins.sha256 (39a97e7f…). J1 report format precedent: ${K8}/j1/analysis/J1_REPORT.md, ANALYSIS_METHOD.md, VALIDITY.md, VERIFY_ANALYSIS.md.
- K9-2 V-B (model-internal) for context only: ${K8}/k92/bundle1/k92_vb/K92_VB_REPORT.md r3 §6 'what to watch in V-A'.
- User decisions so far: ${K8}/K9_1_J1_NOTES_20261013.md (D-K9-67..72 for V-A).
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
phase('Validity')
out.validity = await agent(`${RULES}\n${CTX}\nTASK (Validity): verify amendment 34 and pin-list shas; confirm all three runs ended (EXIT code=0 lines, no NOT_LAUNCHED, cmd processes gone, no VISSIM running that belongs to V-A). Write/complete VA/validity/va_j1a.py exactly as amendment 34 §7.1 defines (if it already exists, verify its sha against any pin), PIN its sha in ${VA}/LOG.md BEFORE it reads run data, self-test it on J1 runs (must reproduce ${K8}/j1/analysis/VALIDITY.md results), then compute V-A validity per seed: J1-A items, held decisions counted separately (amendment 21), DECISION_FAILED, error files, decision count 61, wall-clock, provenance (head/freeze/tuning/network), W/H-b keys present in every SDMPC decision, the expected T=150 head_observation_prior_discarded = 1.0, failed-seed rule (≥ 2 failed seeds ⇒ analysis STOP). Write ${VA}/validity/VALIDITY_VA.md (+ copy to ${REPVA}). Return pass=true only if the analysis may proceed per amendment 34; otherwise STOP with the exact rule.`, { label: 'validity', phase: 'Validity', schema: SCHEMA })
if (!out.validity || !out.validity.pass) return { stoppedAt: 'Validity', out }

phase('Analysis')
out.analysis = await agent(`${RULES}\n${CTX}\nTASK (Analysis): verify the analysis tool pins (va_analysis_pins.sha256) — the tools must be byte-identical to the pinned versions; run them exactly as ANALYSIS_METHOD_VA.md / amendment 34 §7 say (--profile va), detached, one at a time. Validity report: ${JSON.stringify(out.validity || {}).slice(0, 2500)}. Write ${VA}/analysis/VA_REPORT.md (J1_REPORT format): head block as amendment 34 fixes (incl. the fixed lines R10/R11), plain summary first (<= 15 lines), then per seed tables U6 (V-A − NC3) and U9 (V-A − J1) side by side with Ω always next to ④ (all + uninserted) and Ω-outside; link 174 / input 1083 queues; SC109 p3 ≤ 24.5 s count and first time vs J1; east-side SC109 links; meters/VSL; 'previous plan kept' decisions; holds; decision wall-clock vs 1.0158; labels only by the predeclared rule; what V-A can and cannot show; caveats (code provenance of the J1 s31 rerun, V-B model-internal results are not evidence here, D-K9-44 adapter behaviour unchanged). Copy to ${REPVA}. No verdict words. Return status, a Korean summary (<= 25 lines) of the key numbers per seed, artifacts with sha256, open.`, { label: 'analysis', phase: 'Analysis', schema: SCHEMA })
if (!out.analysis || !out.analysis.pass) return { stoppedAt: 'Analysis', out }

phase('Verify')
const vPrompt = (r) => `${RULES}\n${CTX}\nTASK (Verify r${r}): independently verify ${VA}/analysis/VA_REPORT.md and ${VA}/validity/VALIDITY_VA.md: run the pinned verification chain (v_chain.cmd va; verify its pin first) which recomputes from raw run files without importing the analysis tools; additionally recompute at least 5 headline numbers per seed yourself with fresh code (Ω, ④ all, ④ uninserted, Ω-outside, link 174 queue, SC109 p3 onset count) and compare; check every sentence of the plain summary follows from the tables, Ω never appears without ④ and Ω-outside, labels follow the predeclared rule, no verdict words, no pooling beyond the declaration. Analysis report: ${JSON.stringify(out.analysis || {}).slice(0, 3000)}. Write ${VA}/analysis/VERIFY_VA_r${r}.md. Return pass=true only if numbers agree and no wording defect remains; list each defect concretely with the fix.`
out.v1 = await agent(vPrompt(1), { label: 'verify-1', phase: 'Verify', schema: SCHEMA })
if (!out.v1 || !out.v1.pass) {
  out.fix = await agent(`${RULES}\n${CTX}\nTASK (Fix report): fix every real defect the verifier found in VA_REPORT.md / VALIDITY_VA.md (wording, transcription, missing companions for Ω) WITHOUT changing tools, definitions or label rules; keep the previous version as _r1; add a change log. If a defect requires changing a pinned tool or definition, STOP and report. Verifier report: ${JSON.stringify(out.v1 || {}).slice(0, 5000)}. Return pass=true if all real defects are fixed.`, { label: 'fix-report', phase: 'Verify', schema: SCHEMA })
  if (!out.fix || !out.fix.pass) return { stoppedAt: 'FixReport', out }
  out.v2 = await agent(vPrompt(2), { label: 'verify-2', phase: 'Verify', schema: SCHEMA })
  if (!out.v2 || !out.v2.pass) return { stoppedAt: 'Verify', out }
}
return { stoppedAt: null, out }
