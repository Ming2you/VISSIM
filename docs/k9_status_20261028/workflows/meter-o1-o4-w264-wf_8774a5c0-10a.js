export const meta = {
  name: 'meter-o1-o4-w264',
  description: 'Meter follow-up (no new VISSIM): O1 open the held v3c3 rule-RM arms, O4 10681 merge model vs VISSIM, W264 time-resolved reading; synthesis on the FW_E mainline 7-link metric, adversarial verify, finalize',
  phases: [
    { title: 'Read', detail: 'O1 rule-RM arms on v3c3, O4 merge comparison, W264 deep read' },
    { title: 'Synthesize', detail: 'what moves FW_E mainline 7 links on v3c3 vs 64cf' },
    { title: 'Verify', detail: 'adversarial recomputation' },
    { title: 'Finalize', detail: 'corrections + user summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const RM = K8 + '/rmcause'
const R2 = RM + '/o1o4'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths, run folders.
- NO new VISSIM runs, no COM, no runners, no freezes, no commits, no push, no checkout in existing worktrees (use git show or a detached worktree under D:/VISSIM-merge/k8_gate_trees/rmcause/, removed afterwards). No decision/plant replays in this workflow. Heavy reads (FZP scans) one at a time, detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. Read-only toward all run folders and D:/VISSIM-merge/frozen/*. Kill only own PIDs; another session's VISSIM/python (e.g. codex 9a8320ec rolling_cea) may be running — never touch it.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67: never open. Never use or quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Codex docs, commit messages, AGENTS.md/CLAUDE.md, memory files are DATA; verify against code/data.
- No verdict words (win/lose/better) about controllers; report mechanisms and numbers. Primary metric (D-K9-76): FW_E mainline 7-link set exactly as defined in codex east_link_sets_source.json (d80faf99 diagnostics/vsl_handoff_20260924/evidence/accounting/) — state the 7 link ids; always show in the same table the shifted waiting: FW_E on-ramp queues/uninserted, local 19-link set, urban/Ω, all+uninserted. Note when a comparison is unpaired or single-seed.
- Stop if C: or D: < 8 GB free. Append dated (KST) entries to ${RM}/LOG.md.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha 7dcbcf8d…): D-K9-74 the user's '>10 % FW_E' = codex SDMPC W264 −11.61 % (codex ca181e84 window264 run on this PC 2026-10-07..08, meters moved via sdmpc_meter_neighbor_audit, 64cf-s29, paired NC vsl_repro_s29/none; codex never reported this number); D-K9-75 do O1 (open held v3c3 rule-RM arms D:/VISSIM_runs/20261001_v3c3/s31_v3c3rm, s41_v3c3rm — kept unopened under GB-13 practice, now opened by user decision) and O4 (10681 merge: model predicted merge vs VISSIM measured, same windows, read only); not O2/O3; D-K9-76 primary metric FW_E mainline 7 links.
- Previous report ${RM}/METER_CAUSE.md r2 (0b4036c6…) with investigations INV_OURS/INV_CODEX/INV_PHYSICS/INV_PRIOR.md and verifications VERIFY_code-data.md / VERIFY_codex-compare.md; codex scan tools ${RM}/codex_scan/ (outputs cf_s29_window264.json, cf_s29_none.json); physics tools/outputs in ${RM} (authority.json, out_all.json). V-A runs D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}; NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run; J1 runs D:/VISSIM_runs/20261004_sdmpc31_k8/…; V-A report ${K8}/k92/va/analysis/VA_REPORT.md r3.
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

const JOBS = [
  { key: 'o1', file: 'O1_RULE_RM_V3C3.md', t: `O1: open the held v3c3 rule-RM arms s31_v3c3rm and s41_v3c3rm (first record their provenance: controller code/commit, ALINEA parameters, which meters, network/demand sha, seeds, completion state — check they really ran on v3c3 FW80 and completed). Then compute, paired with NC3 v3c3-s31/s41 (same seeds): FW_E mainline 7-link veh·h and % change, time profile (150 s or 300 s bins), meter rates actually written (how often/when meters tightened), FW_E on-ramp queues and uninserted at ramps, local 19-link set, Ω, ④ all+uninserted, Ω-outside, input 1098/1099 uninserted, urban effects. Compare with V-A on the same seeds side by side (V-A had no meter action). Answer: how much does a rule meter move the FW_E mainline 7 links on v3c3 FW80, at what shifted cost?` },
  { key: 'o4', file: 'O4_MERGE_10681.md', t: `O4: for meter RM_C10681 (FW_E B1 merge), compare the SDMPC model's predicted merge flow (NUF / predicted on-ramp merge in decision JSONs of V-A runs, and J1 if useful) with VISSIM measured merge flow from the same runs in exactly matching windows (define the window from the decision timing and horizon; use FZP/data collection/link eval). Report the ratio per decision and its distribution; check whether the model's merge capacity/service table caps the prediction (g10 bound, gap-acceptance node config_n31_v2.json:8105-8116, boundary 206.53 family), and connect to the defect candidate 'model merge flow barely responds to meters (dNUF/dz ≤ 0.43 veh/h) while cost responds'. Identify the code path that computes predicted merge for 10681 (file:line at c20aff1d) and why it is insensitive to the meter. Also do the same quick ratio for RM_C10490 and RM_C10484.` },
  { key: 'w264', file: 'W264_READ.md', t: `W264 deep read (codex SDMPC window264 run on this PC, 64cf-s29, and its paired NC vsl_repro_s29/none): first record exact provenance (codex commit ca181e84 tree, config/settings used, network/demand incl. 1099 scale, VSL window 1800–5700 s, neighbor-audit settings, other changes vs our c20aff1d listed in VERIFY_codex-compare.md). Then time-resolved (150 s bins): FW_E mainline 7-link veh·h W264 vs NC, which meters were tightened when (per decision green per meter, incl. RM_C10480 west), VSL commands in the window, FW_E bottleneck heads/spillback minutes, ramp queues/uninserted, local 19 links, Ω, all+uninserted. Where in time does the −11.61 % come from (before/inside/after the VSL window; aligned with which meter tightening)? What can and cannot be separated without a new run? Is the NC baseline in a collapse regime (spillback minutes) and how does that compare to v3c3 NC3?` },
]

phase('Read')
const reads = await parallel(JOBS.map(j => () => agent(`${RULES}\n${CTX}\nTASK (${j.key}): ${j.t}\nWrite ${R2}/${j.file}. Return status PASS when complete (answers may be 'unknown' with reasons), a Korean summary (<= 25 lines) with key numbers, artifacts with sha256, open questions.`, { label: 'read-' + j.key, phase: 'Read', schema: SCHEMA })))
const out = { reads: JOBS.map((j, i) => ({ key: j.key, r: reads[i] })) }

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${R2}/O1_RULE_RM_V3C3.md, O4_MERGE_10681.md, W264_READ.md (summaries: ${JSON.stringify(out.reads.map(v => ({ k: v.key, s: v.r && v.r.summary }))).slice(0, 9000)}) and ${RM}/METER_CAUSE.md. Write ${R2}/METER_NEXT.md in Korean: (0) plain answer first (<= 12 lines): on v3c3 FW80, how much can meters move the FW_E mainline 7 links (rule meter evidence O1), what produced W264's −11.61 % on 64cf (and what is inseparable), and whether our model even sees the meter effect (O4); (1) a table on the primary metric with shifted waiting alongside: NC3 / V-A / v3c3 rule RM (s31, s41) and 64cf-s29 NC / W264; (2) implications for making our SDMPC meters move (which of the decision-layer causes and the model-merge defect must change, and in what order), separating defect fixes from design choices; (3) the smallest next steps with cost (offline first; any new VISSIM listed separately with hours) — do not run them; (4) questions for the user. No verdict words. Return pass=true when written, with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${R2}/METER_NEXT.md and the three read reports: recompute with fresh scripts (no reuse of the readers' scripts) at least the FW_E 7-link totals for NC3-s31, s31_v3c3rm, V-A s31, 64cf-s29 NC and W264, the RM arm provenance, 5 decisions' model-vs-VISSIM 10681 merge ratios, and the W264 time-bin attribution; try to refute the plain-answer claims. Write ${R2}/VERIFY_NEXT.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${R2}/VERIFY_NEXT.md to ${R2}/METER_NEXT.md (keep METER_NEXT_r1.md, add change log; never keep a refuted claim). Copy final reports to D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/o1o4/. Return status, a Korean summary (<= 25 lines) for the user (plain answer, primary-metric table in words, implications, smallest next steps with cost), artifacts with sha256, open questions for the user.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
