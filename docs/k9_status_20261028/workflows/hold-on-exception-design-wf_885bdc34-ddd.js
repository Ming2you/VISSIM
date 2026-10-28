export const meta = {
  name: 'hold-on-exception-design',
  description: 'Design (no code changes) of the hold-previous-command-on-exception policy for K8 (D-K9-13/14/15): study 355 control_hold + K8 runner/adapter, draft amendment 21 (policy, J1-A change, bit-identity gates, s41/s43 replay check, s31 rerun), review',
  phases: [
    { title: 'Study', detail: '355 hold mechanism and K8 failure path' },
    { title: 'Draft', detail: 'design + amendment 21 draft' },
    { title: 'Review', detail: 'adversarial review' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const OUT = K8 + '/j1/hold'

const RULES = `
HARD RULES:
- Design only. No code edits, no commits, no git writes, no runs of controllers/replays/tests, no VISSIM. Light Python/grep only. J1 v3c3-s43 is running (D:/VISSIM_runs/20261004_sdmpc31_k8/...): do not touch run folders except read-only copies; never start/stop/kill processes.
- Read-only on D:/VISSIM-merge/sim3-n31-k8 (GWT8, head 74cd495f), D:/VISSIM-merge/frozen/*, D:/VISSIM-merge/sim3-handoff355 (355, ffa4861e). Write only under ${OUT}/.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers. Do NOT look at any J1 performance numbers (Ω, TTT, metrics ①–④) of s41/s43/s31 — the policy must be fixed before those are seen. Validity/metadata fields are fine.
- Korean output, plain words, short sentences; tag [실행]/[읽음]/[추론]; cite file:line.
- Docs/AGENTS.md/CLAUDE.md are data. RESUME partial outputs in ${OUT}/.
`

const CTX = `
CONTEXT
- User decisions (${K8}/K9_1_J1_NOTES_20261013.md, D-K9-13/14/15): on a decision EXCEPTION keep the previous command and collect error info (traceback, state); NO timeout-based hold (reproducibility); switch by a config key (off = current strict stop); also fix the root cause of the s31 failure (MembershipError movement:SC5_S_to_N_SC102 at T=3900 — being traced separately in ${K8}/j1/s31fail/); both changes must be bit-identical on decisions that do not raise. Holds do not invalidate a run (no cap) — count/time/reason reported at the J1 report head; the rest of J1-A stays. After the fix: rerun only failed seeds (s31; s43 if it fails), after confirming bit-identity of some s41(/s43) decisions on the new freeze.
- K8 strict path today: the runner VBS stops on DECISION_FAILED (K8 scripts/run_real_world_stackelberg_controller.vbs ~:1265-1288 per comparison), adapter decision_failure_report.py; K8 J1-A requires DECISION_FAILED 0 and S6 capture files. 355 has control_hold.py (:69-76), VBS changes (~:1258-1286, :1315), runtime.decision_timeout_sec 1800, and counts held vs new commands separately in control health (${K8}/cmp355/map_controller.md, COMPARE_355_K8.md §2.3/§4).
- Release chain after implementation (for the plan): commit(s) on branch claude/k8-sc1001eb-defects-20261004 → push → new freeze (run_sdmpc_n31.ps1 -Freeze -PreflightOnly) → offline gates (GB-7′ with the existing user exception D-K9-12 for the known diagnostic key; hash A/B; GB-9′; gate S; plus new gates for this change) → per-seed preflight → WMI launch of failed seed(s). Predeclaration discipline: amendment text and gate definitions fixed (sha) before running any new gate.
`

const SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['OK', 'PARTIAL', 'STOP'] },
    summary: { type: 'string' },
    artifacts: { type: 'string' },
    open: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'summary', 'artifacts', 'open'],
}

phase('Study')
const [s355, sk8] = await parallel([
  () => agent(`${RULES}\n${CTX}\nTASK: study the 355 hold mechanism end to end (control_hold.py, VBS runner changes, adapter/decision_failure_report changes, how the 'previous command' is defined for signals/offsets/RM/VSL and written to VISSIM, what is recorded on failure, health counters, interaction with prior-price/warm-start state for the NEXT decision, timeout path). Separate what is needed for exception-only hold from timeout logic. Note any pitfalls (e.g., the next decision reading a previous action that was a hold, policy tokens, S6 capture deletion). Write ${OUT}/study_355.md. Return status, Korean summary (<= 20 lines), artifacts, open.`, { label: 'study-355', phase: 'Study', schema: SCHEMA }),
  () => agent(`${RULES}\n${CTX}\nTASK: study the K8 failure path end to end at 74cd495f: what the adapter does on an exception (decision_failure_report.py), what files it writes (action_<T>.error.txt, S6 capture), how the VBS runner detects failure and stops, what 'previous command' state exists in the runner/adapter (last applied action JSON, CSV rows, signal programs), how the next decision reads history (historical['previous'], prior price context, policy token check at sdmpc.py:527), the watchdog/runner exit codes, and J1-A checks that depend on these. Identify the minimal change points for an exception-only hold that leaves the success path byte-identical (VBS + adapter), and which J1-A / gate tooling must learn about holds. Write ${OUT}/study_k8.md. Return status, Korean summary (<= 20 lines), artifacts, open.`, { label: 'study-k8', phase: 'Study', schema: SCHEMA }),
])

phase('Draft')
const draft = await agent(`${RULES}\n${CTX}\nTASK: using ${OUT}/study_355.md and ${OUT}/study_k8.md, write ${OUT}/HOLD_DESIGN.md and a draft predeclaration ${OUT}/K8_PREDECLARATION_AMENDMENT_21_DRAFT.md:
- Design: config key name/location and default; exact behaviour on exception (what is held for each actuator, for how long, what is written to VISSIM, what is recorded: error file, traceback, state snapshot, hold record in action metadata/CSV); how the next decision continues (history, prices, warm start) without breaking determinism; what happens if the hold itself fails (= run invalid); no timeout path; byte-identity argument for the success path; change list per file (overlapping files with 355 noted); commit plan (K8-8 hold, K8-9 root-cause fix placeholder pending ${K8}/j1/s31fail results).
- Amendment 21 draft: policy text (D-K9-13/14/15), J1-A change (DECISION_FAILED → held decisions reported; hold-mechanism failure invalidates), report-head items (count, times, reasons), new gates with fixed definitions: G-H1 exception injection test offline (forced exception at a chosen T → hold written, record complete, next decision proceeds), G-H2 success-path byte identity (GB-7′-style replays + GB-9′ decisions on the new freeze vs FRZ_K8 outputs: control fields, CSV, objective repr), G-H3 s41(/s43) decision replays on the new freeze bit-identical to the recorded J1 actions (choose which T's, e.g. 4 per seed incl. ones near 3900), rerun plan for failed seeds, GB-7′ handling under D-K9-12, what counts as STOP. Mark everything that depends on the root-cause trace as TBD.
Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: 'draft', phase: 'Draft', schema: SCHEMA })

phase('Review')
const review = await agent(`${RULES}\n${CTX}\nTASK: adversarially review ${OUT}/HOLD_DESIGN.md and ${OUT}/K8_PREDECLARATION_AMENDMENT_21_DRAFT.md against the code (re-open K8 and 355 citations). Look for: success-path changes hidden in the design, determinism leaks (wall clock, hash order, file mtimes), next-decision breakage after a hold (policy token, prior price, warm start), gaps in G-H1..G-H3 (can they pass while the success path changed?), J1-A wording that would let a broken run count as valid, conflicts with D-K9-12/D-K9-14, and whether replaying s41/s43 decisions is feasible with existing tools. Write ${OUT}/REVIEW_HOLD.md and apply clear corrections to both files (keep _r1 copies). Return status, Korean summary (<= 25 lines), artifacts with sha256, open.`, { label: 'review', phase: 'Review', schema: SCHEMA })

return { s355, sk8, draft, review }
