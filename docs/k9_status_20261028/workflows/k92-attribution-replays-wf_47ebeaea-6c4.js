export const meta = {
  name: 'k92-attribution-replays',
  description: 'Offline attribution of the J1 link-174 / Ω-outside mechanisms by decision replays on J1 states (no VISSIM): fixed method first, adversarial review, replays with toggled arms, analysis, verification, report for K9-2 decisions',
  phases: [
    { title: 'Design', detail: 'method: states, arms, metrics, precondition; sha before any replay' },
    { title: 'ReviewDesign', detail: 'adversarial review, fix' },
    { title: 'Run', detail: 'precondition replays then arms, one at a time, detached' },
    { title: 'Analyze', detail: 'attribution tables' },
    { title: 'Verify', detail: 'independent recomputation + reruns' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const J1 = K8 + '/j1'
const OUT = K8 + '/k92/attrib'
const MEM = 'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- No VISSIM, no COM, no runners. Offline decision replays ARE allowed (user decision D-K9-28), using the existing replay tooling (make_replay_state_v2 prepare/copy-only + replay_decision_n31.ps1, as in ${J1}/s31fail/repro and ${J1}/fix/gates harnesses). Heavy jobs: one at a time, DETACHED via WMI (Invoke-CimMethod Win32_Process Create), BELOW_NORMAL, PYTHONHASHSEED=0, python -B; poll with short checks (≤ 9 min per wait). Kill only your own PIDs if ever needed.
- READ-ONLY: J1 run folders (D:/VISSIM_runs/20261004_sdmpc31_k8/*), NC3/R-obs runs, frozen trees (FRZ_K8 D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824, FRZ_K8b ..._b9734abe_202610141821 — snapshot before/after), GWT8 D:/VISSIM-merge/sim3-n31-k8 (no commits, no edits). Arms are built in scratch trees (git archive of b9734abe or 74cd495f) under D:/VISSIM-merge/k8_gate_trees/k92attrib/ with byte-fix to frozen bytes as in previous gate harnesses, and scratch tuning/config copies; read-only instrumentation hooks via sitecustomize (as REPRO A0h) are allowed. Outputs under ${OUT}/ and D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_attrib/.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix.
- The method file must be written and its sha256 recorded BEFORE the first arm replay; never change arms/metrics/thresholds after seeing arm results (if needed, add clearly labelled post-hoc extras, never replace). No verdict language.
- Stop if C: or D: < 8 GB free. AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs in ${OUT}/.
`

const CTX = `
CONTEXT
- J1 cause analysis: ${J1}/causes/CAUSES.md (r2 0d86ead8…; read §0–§5), lens files ${J1}/causes/lens_*.md, verification ${J1}/causes/VERIFY_CAUSES.md; J1 report ${J1}/analysis/J1_REPORT.md. Key mechanisms to attribute:
  (a) SC109 west through modelled as boundary_out 206.53 × 3 lanes = 619.6 veh/h-green vs VISSIM discharge ~5,900; SC109 east inflow (link 1220000704, 826.1) also implicated (09-27 diagnosis: east inflow cost +0.97 > west through gain −0.80); (b) left-turn head floor (present in s31r/s43, absent in s41 because warm-up saturated left-turn passes < 5) and 50:50 projection; (c) objective counts only Ω-inside stock (Ω-outside waiting cost 0) → SC1004_p1 / SC108_p1 green shifts led by ext; green axis convention p_k +1 s / last live phase −1 s (sdmpc.py:318-319) so dependent phase p4 stock mixes in; (d) projection flip / fallback non-monotone (N2); (e) phantom stock bias (D-K9-19).
- Decision states available: J1 runs v3c3-s31 rerun (FRZ_K8b), v3c3-s41 and v3c3-s43 (FRZ_K8) decision bundles; replaying a recorded decision on its own tree reproduced the record bit-for-bit before (REPRO C0, P0, G-H3). Previous harness code: ${J1}/s31fail/repro/, ${J1}/fix/gates/, ${J1}/fix/p0/.
- Capacity value source for the SC109 arms (D-K9-28 did not decide Q4): primary = existing NC-derived tables (v3b S1 / U4 tables, see ${MEM}/vissim-urban-batch1-and-rmcal-20260926.md and ${MEM}/vissim-boundary-movement-capacity-206.md and repo diagnostics), sensitivity = J1 FZP same-seed measurement; label both.
- User decisions record: ${K8}/K9_1_J1_NOTES_20261013.md (D-K9-28: attribution by offline replays first + behaviour-invariant diagnostic enhancement via hooks/scratch, no commits).
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
phase('Design')
out.design = await agent(`${RULES}\n${CTX}\nTASK (Design): write ${OUT}/METHOD.md fixing, before any replay:
1) States (≤ 6): e.g. v3c3-s43 and s31 rerun decisions just before/at the onset where SC109 p3 got pushed to ~20 s and the link-174 queue started (find exact T from CAUSES/lens data), the same T in v3c3-s41 as contrast, and one later state; justify.
2) Precondition: replay each chosen state on its own tree as-is (A0) and require bit-identity with the recorded action (CSV + 7 control fields + objective repr); if not identical, that state is dropped (report).
3) Arms (≤ 8, each a single, exactly specified change; config/tree diff written out): SC109 west boundary capacity = measured (primary table value), + east side too, J1-FZP sensitivity value, head floor removed (or seeded), 50:50 projection replaced by the declared alternative, objective with Ω-outside waiting weight (diagnostic only, exact definition), and at most two combinations. Total replays ≤ 36.
4) Metrics: chosen greens (SC109 p1..p4, SC1004 p1/p3, SC108 p1, SC1001 p3), objective and own/ext by owner (instrumented), predicted link-174 / SC109 stocks over the horizon, gradient components on the SC109 p3 axis, Ω-outside predicted waiting; how 'attribution' is computed (differences vs A0, interaction table), and what is report-only.
5) Instrumentation: read-only hooks for owner-wise ext decomposition (behaviour-invariant: prove by A0+hooks bit-identical to A0).
Record sha256 of METHOD.md in ${OUT}/METHOD.sha256 with time. Return pass=true if complete with no TBD.`, { label: 'design', phase: 'Design', schema: SCHEMA })
if (!out.design || !out.design.pass) return { stoppedAt: 'Design', out }

phase('ReviewDesign')
out.review = await agent(`${RULES}\n${CTX}\nTASK (ReviewDesign): adversarially review ${OUT}/METHOD.md against CAUSES r2 and the code: are the arms single, exact and implementable; can an arm silently change something else (e.g. capacity table also used by other movements, floor rule also elsewhere); is the precondition strict; is the attribution arithmetic sound (interactions, non-additivity); are states chosen without peeking at arm results; is the Ω-outside weight arm clearly diagnostic; is the replay budget feasible. Apply corrections (keep METHOD_r1.md), then re-record sha256 in ${OUT}/METHOD.sha256 as the fixation point (before any arm replay). Return pass=true if fixed with no unresolved issue.`, { label: 'review-design', phase: 'ReviewDesign', schema: SCHEMA })
if (!out.review || !out.review.pass) return { stoppedAt: 'ReviewDesign', out }

phase('Run')
out.run = await agent(`${RULES}\n${CTX}\nTASK (Run): verify ${OUT}/METHOD.sha256 matches METHOD.md; build the scratch trees/configs exactly as declared (record diffs and shas); run the precondition replays (A0 and A0+hooks) then all declared arm replays, one at a time, detached; snapshot frozen trees and J1 run folders before/after (must be unchanged). Write ${OUT}/RUN_LOG.md (job list, start/end, exit codes, output paths, sha256). Do not analyse beyond completeness checks. Return pass=true if all declared replays completed (dropped states reported per the method).`, { label: 'run', phase: 'Run', schema: SCHEMA })
if (!out.run || !out.run.pass) return { stoppedAt: 'Run', out }

phase('Analyze')
out.ana = await agent(`${RULES}\n${CTX}\nTASK (Analyze): compute the declared metrics and attribution exactly per METHOD.md from the replay outputs; write ${OUT}/ATTRIBUTION.md: §0 plain summary (which mechanism moves SC109 p3 / link-174 stock / Ω-outside waiting by how much, per state; interactions), §1 tables, §2 what this implies for K9-2 options (capacity fix scope west/east/full, head floor rule, objective boundary policy E1–E4) as options with recommendation [추론], §3 caveats (replays are single decisions, not closed loop), §4 questions for the user. Return status, Korean summary (<= 30 lines), artifacts, open.`, { label: 'analyze', phase: 'Analyze', schema: SCHEMA })

phase('Verify')
out.ver = await agent(`${RULES}\n${CTX}\nTASK (Verify): independently recompute every number in ${OUT}/ATTRIBUTION.md from raw replay outputs with your own code; re-run 2 arm replays (one capacity arm, one objective arm) detached and confirm bit-identity; check arms match METHOD exactly (tree/config diffs), the method sha preceded arm runs, and claims/recommendations follow from numbers. Write ${OUT}/VERIFY_ATTRIBUTION.md, apply corrections to ATTRIBUTION.md (keep _r1) with a change log. Return status, Korean summary (<= 30 lines) suitable for relaying to the user, artifact + sha256, open (user decisions for K9-2).`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

return { stoppedAt: out.ver && out.ver.pass ? null : 'Verify', out }
