export const meta = {
  name: 'urban-batch2-stages3-7',
  description: 'Urban batch 2 stages 3-7 of BATCH2_PLAN.md: evidence files (U4 table v1, U5 contract v1, U6 evidence, SC105/SC1 p3 authority evidence) + C6 overhead reduction with G-ID(d) recheck; U4, U5, U6 code; C3 bundle gates; independent verify + fix; no commits, no VISSIM',
  phases: [
    { title: 'S3', detail: 'evidence files + C6 overhead' },
    { title: 'S4', detail: 'U4 code' },
    { title: 'S5', detail: 'U5 code' },
    { title: 'S6', detail: 'U6 code' },
    { title: 'S7', detail: 'C3 bundle gates' },
    { title: 'Verify', detail: 'independent review + fix' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const B = R + '/urban-b2'
const WT = 'D:/VISSIM-merge/sim3-n31-urban-b2'
const COMMON = `
CONTEXT (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line. If the Write tool refuses a report file, write it with Bash.
- Approved plan ${B}/BATCH2_PLAN.md — read §0-§10 and appendix C fully; follow §4.3-4.6, §5, §6, §7 exactly (stop rules in §7 are binding: on any stop rule, set stop=true and do not continue). Data artefacts: ${B}/u4_saturation_table.json, u5_contract_draft.json, u6_diagnosis.md, code_map.md.
- USER DECISIONS (binding): batch 2 = C3 (U4+U5+U6, all-or-nothing) + C2 (U2) + C6. U5 covers ALL overcounted groups (v3b: 53) AND native groups (Q1: apply U4 and U5 to native). Q2: fix the SC105/SC1 shared left-lane phase authority to p3 with an evidence file (like the U1 SC7 correction) and statically reduce SC7's serial-head group; interim static reduction until the evidence file exists. Q3: no v3b closed-loop run. 2026-09-29: C6 overhead on no-control decisions (+0.5 s, JSON +6.8 %, gate G-C6-3 limit 1 %) must be REDUCED (parse the inpx once per process / cache, and keep only flagged rows in the groups/boundary tables) and re-checked (G-ID (d) and G-C6-0..4 again).
- Stages 0-2 are DONE and independently verified (no blocking): ${B}/impl/STAGE0.md, STAGE1.md, STAGE2.md (worktree diff sha 36ac3916 at the end of stage 2; tests test_n31_urban_batch2 28 OK). Open notes carried: install_lane_group_membership ["internal"] restriction must widen when all C3 keys are present (stage 4); C6 boundary rule currently fires on 35-38 movements (206.53 defect marker; must drop after U4 — report it as a C3 secondary metric); C6 key 1.0/8/3/3 must go into the candidate configs (stage 9, later); delete evaluation/controllers/__pycache__ before any freeze; tests using TemporaryDirectory(dir=fx.HERE) can race the diff-sha check.
- Worktree ${WT} (branch claude/urban-batch2-20260928 at cf3ce37), uncommitted. Development stays on the v3b-pinned tree; tables are re-derived on v3c1 later (v3c1 re-pin is committed on claude/repin-v3c1-20260928 at 9ed2ef0 — never touch that branch/worktree D:/VISSIM-merge/sim3-n31-v3c1).
- SAFETY: never modify D:/VISSIM-merge/frozen/*, sim3-n31, sim3-n31-urban, sim3-n31-v3c1 or any run folder under D:/VISSIM_runs. Offline replays only (make_replay_state_v2.py prepare + replay_decision_n31.ps1 -Root ${WT} or ${R}/xreplay/alt_replay.ps1), ONE at a time, BELOW_NORMAL, NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2i; FZP streaming one process at a time. Never start/kill VISSIM or cscript; never run watchdog/cscript/ps1 *tests* (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Never open seed 37 outputs, RM arms, or sealed seeds 59/61/67. No commits/pushes. An N1F analysis process may be running: keep CPU modest.
- Every new switch is a config key (absent = bit-identical); no env/getattr gates; superseded code isolated, not flagged. Harness under ${B}/harness with provenance incl. worktree_diff_sha256. Reports under ${B}/impl/STAGE<n>.md.
- RESUME RULE: if a previous attempt of your stage left partial results, reuse only after checking provenance (tree, diff sha, tuning shas) and completeness; say what you reused.
`
const S = { type: 'object', properties: { summary_ko: { type: 'string' }, gates_ko: { type: 'string' }, changed_files: { type: 'array', items: { type: 'string' } }, stop: { type: 'boolean' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'gates_ko', 'stop'] }
const stages = [
  { n: 3, ph: 'S3', task: 'STAGE 3 (plan §4.3 + §7 row 3): finalise the evidence files — U4 saturation table v1 (incl. multi-head and native-group FZP measurements over the 5 fit seeds of v3b NC: 31/41/43/47/53), U5 contract v1 (all overcounted groups + native groups; SC7 serial-head static reduction), U6 diverge evidence, and the Q2 evidence file that sets the SC105/SC1 shared left-lane phase authority to p3 (derive it like the U1 SC7 correction; cite FZP/signal evidence) — each with a generator and --check, and cross-consistency checks between them. ALSO the C6 overhead reduction (user decision 2026-09-29): implement it, then re-run G-C6-0..4 and G-ID (d) and report the new no-control overhead vs the 1 % limit. Write ' + B + '/impl/STAGE3.md.' },
  { n: 4, ph: 'S4', task: 'STAGE 4 (plan §4.4): U4 capacity scale replacement in code (head-floor lane-ratio callback, two-step contract loading, lane file pin), widen install_lane_group_membership when all C3 keys are present; unit tests; T1a via harness patch; stop rule: boundary allocation binding > 0. Write ' + B + '/impl/STAGE4.md.' },
  { n: 5, ph: 'S5', task: 'STAGE 5 (plan §4.5): U5 shared discharge resource per physical head group (own raw assertion, port.ready() weights, sequential residual, static reduction, install assertions); unit tests; §5.2 assertion (group sum <= lanes x s x g every step) with the check count > 0 and accounting substep/LOR installed (stop rules); 10634 equality with the harness-patched "C3 without U5" arm. Write ' + B + '/impl/STAGE5.md.' },
  { n: 6, ph: 'S6', task: 'STAGE 6 (plan §4.6): U6 W-side ramp diverge physical_diverge_v1; unit tests; G6 partial (9-state preliminary) per §6.5. Write ' + B + '/impl/STAGE6.md.' },
  { n: 7, ph: 'S7', task: 'STAGE 7 (plan §6 and §7 row 7): C3 bundle gates — G-ID, T1 (group capacity 0.8-1.2 x measured), G0 (R-obs-b 61 states, T3 one-step metrics not worse than U1+U3), G-U5-127, G6 (U6), G-SC109 (S1 3600/4500/6300/7650, S0e 3600/6300 with the C3 candidate tuning), G-v3b remainder and time (deterministic counters first, alternating wall clock), secondary checks §6.10 incl. the C6 boundary-rule count after U4, completeness census, attribution arms (harness patch vK, vU6, 9 states). Produce the C3 verdict (pass/fail per gate, all-or-nothing). Write ' + B + '/impl/STAGE7.md.' },
]
const reports = []
for (const st of stages) {
  phase(st.ph)
  const prev = reports.length ? `\nPrevious stage reports (this run): ${JSON.stringify(reports.map(r => ({ n: r.n, stop: r.r.stop, summary_ko: r.r.summary_ko, open_issues_ko: r.r.open_issues_ko })))}` : ''
  const r = await agent(`${COMMON}${prev}\nTASK ${st.task}`, { label: 'stage' + st.n, phase: st.ph, schema: S })
  reports.push({ n: st.n, r })
  if (!r || r.stop) { log('stopped at stage ' + st.n); return { reports, stopped_at: st.n } }
}
phase('Verify')
const v = await agent(`${COMMON}\nReports: ${JSON.stringify(reports.map(x => ({ n: x.n, summary_ko: x.r.summary_ko, gates_ko: x.r.gates_ko })))} (and ${B}/impl/STAGE3..7.md)\nTASK (independent verifier, adversarial): review the full diff of ${WT} against cf3ce37 (+ untracked) for: behaviour change when C3/C2/C6 keys are absent (re-run G-ID on 10 R-obs-b states + one S1 SDMPC decision yourself), env/getattr gates, the U4 table and U5 contract evidence (recompute at least 3 groups from FZP), the Q2 p3 authority evidence, the §5.2 assertion really checking (count > 0), and the C3 verdict numbers (recompute G0 T3 metrics and G-SC109 on at least two states). Report blocking issues (real defects only).`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
let fix = null
if (v && v.blocking && v.blocking.length) {
  fix = await agent(`${COMMON}\nVerifier blocking issues: ${JSON.stringify(v.blocking)}\nTASK: fix what is real in ${WT}, re-run affected gates (and the C3 verdict if touched), explain rejected items. Write ${B}/impl/STAGE3-7_FIX.md.`, { label: 'fix', phase: 'Verify', schema: S })
}
return { reports, v, fix }
