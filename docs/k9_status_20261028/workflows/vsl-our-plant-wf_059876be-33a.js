export const meta = {
  name: 'vsl-our-plant',
  description: 'D-K9-103: offline probe of OUR plant (V-A line) VSL response (Q-V3: ΔJ for VSL 110/101/100/90 at V-A decision states + plant-vs-VISSIM fidelity at V-A VSL decisions) and P1 tracing of VSL-independent freeway bias (cell 18, M1, VSb stock) from existing FZP; predeclare, review, run, synthesize, verify; no code changes, no VISSIM',
  phases: [
    { title: 'Declare', detail: 'PRE_VP rules + tool pins' },
    { title: 'Review', detail: 'adversarial review, fixation' },
    { title: 'Run', detail: 'Q-V3 probe + P1 tracing (offline, shared lock)' },
    { title: 'Synthesize', detail: 'VP_RESULTS' },
    { title: 'Verify', detail: 'independent recomputation' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const VP = K8 + '/vsl_plant'
const TK = 'D:/VISSIM-merge/k8_gate_trees/vsl_plant'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- NO code changes in any repo/frozen tree; GWT8 D:/VISSIM-merge/sim3-n31-k8 stays at c20aff1d (no branch/commit/push). No VISSIM, no COM, no runners, no freezes. Offline plant rollouts/decision replays and FZP reads of EXISTING runs only, in scratch copies under ${TK}/; probe hooks live in scratch copies/wrappers only. Heavy jobs one at a time under the shared lock ${HL} (create exclusively, retry; after release pause ≥ 20 s before re-acquiring so other workflows — C1 guard design / C1 — get turns; delete only your own), detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS removed (K9-2 form, D-K9-99); poll ≤ 9 min. Kill only own PIDs; other sessions' VISSIM/python never touched.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix; v3c3-s47 values never opened.
- Predeclaration: rules, states, arms, metrics and tool sha fixed in PRE_VP.md before any probe data; never change after data; any defect ⇒ STOP and report (user decides). Post-data analyses labelled "데이터 뒤". No verdict words. Signal greens GREEN-only. Evidence by name + sha.
- LESSONS: no path strings in evidence; long lists via files; PID-unique temp names; never read seed tokens from folder names (use provenance fields); replaying recorded states with a changed policy token stops at load_prices — use single-decision plant rollouts from the recorded state with the recorded prices; worker-path vs in-process path can differ (VSL_RESULTS: up to 0.294 veh·h) — use the same path as the deployed decision (worker path) or report the gap. RESUME partial outputs.
- Append dated KST entries to ${VP}/LOG.md (create). Report copies to ${REP}.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha b33fe5e7…): D-K9-101 (C1 keeps V-A VSL), D-K9-102 (no new VSL VISSIM runs now), D-K9-103 (Q-V3: offline O1·O2-form probe of OUR plant on the V-A line using V-A decision states where VSL 101 and 110 were chosen + V-A FZP cell/zone comparison; Q-V4: start plant fixing with P1 = trace the VSL-independent bias — cell 18 before the lane drop, M1, VSb stock; Q-V5 no φ in-between; Q-V6 C1 report VSL line handled elsewhere).
- Prior VSL work: ${K8}/vsl_v3c3/VSL_RESULTS.md r2 (9bbf83a3…) §1.5–1.8 (O1/O2 on codex plant, V-A used VSL 101 at DSD 59–66 in 9/10/14 decisions), ${K8}/vsl_v3c3/VERIFY_VSL.md, ${K8}/vsl_v3c3/o1o2/ (PRE_O1O2 be6852a2…, tools, zone/cell definitions VSa/VSb/M1/Mu/VS0/B1/B2, FZP cell scanners), ${K8}/c_port/VSL_OFFLINE.md r2, memory facts: plant φ 3.0 alive / Carlson VSL law / single-value VSL compliance model (vissim-vsl-fixed-dsd-20260928), freeway plant status (freeway-plant-status-20261004), FW_E plant structure (vissim-fwe-plant-structure-20260927: B1 deficit 80% = cell 12 speed artefact).
- V-A line: runs D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43} (decision JSON with sdmpc_state, action CSV, FZP), V-A freeze/launch records ${K8}/k92/va/ (frozen tree path and sha there), analysis ${K8}/k92/va/analysis/VA_REPORT.md. NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run, VSL-only D:/VISSIM_runs/20261027_vsl_v3c3/s{31,41,43}, B D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43} (read only).
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
out.decl = await agent(`${RULES}\n${CTX}\nTASK (Declare): write ${VP}/PRE_VP.md and pin tools before data. Contents: (1) Q-V3 probe A (plant ΔJ): which V-A decision states (seed, T; choose from provenance/action CSV — states where V-A chose VSL 101 and nearby states where it chose 110, ≤ 12 states total, list fixed), arms (VSL 110 / 101 / 100 / 90 on the V-A zone heads, other levers held at the recorded decision), exactly how the arm is imposed (scratch wrapper around the deployed decision/plant code, worker path), metric = plant J over the deployed horizon and zone/cell terms, sanity checks (recorded arm reproduces the recorded J bit-exactly, else STOP); (2) Q-V3 probe B (fidelity): at V-A states where VSL 101 was applied, plant rollout T..T+300/450 s vs V-A FZP over the same window for zones VSa/VSb/M1/Mu/VS0/B1/B2 and cells 8–25 (speed, flow, stock) — reuse the o1o2 zone/cell definitions and scanners by sha, define bias = plant − VISSIM; (3) P1 tracing: from existing FZP (NC3, VSL-only, V-A, B, all three seeds) and plant rollouts at VSL-off states, locate the VSL-independent bias (cell 18 before the lane drop, M1, VSb stock): decompose by plant term (free speed, FD branch, merge δ, lane-drop capacity, φ capacity drop, compliance law, initial-state projection), with a fixed list of candidate causes and the test for each (term ablation in scratch wrapper), and what result would point to each; (4) outputs, tables, stop rules, cost, order (light first). No TBD. Return pass=true with sha256.`, { label: 'declare', phase: 'Declare', schema: SCHEMA })
if (!out.decl || !out.decl.pass) return { stoppedAt: 'Declare', out }

phase('Review')
out.rev = await agent(`${RULES}\n${CTX}\nTASK (Review): adversarially review ${VP}/PRE_VP.md: arms imposable without changing the policy token path, recorded-arm bit reproduction check present, worker vs in-process path, zone/cell definitions identical to o1o2 by sha, states chosen from provenance (not folder names), P1 candidate list complete and each test discriminating, definitions not true/false by construction, cost realistic, lock etiquette. Apply fixes (keep _r1), write ${VP}/PRE_VP_FIXED.md with final sha/time. Return pass=true only if no unresolved issue.`, { label: 'review', phase: 'Review', schema: SCHEMA })
if (!out.rev || !out.rev.pass) return { stoppedAt: 'Review', out }

phase('Run')
const RESUME = `RESUME NOTE (user decisions D-K9-108·109, notes sha 64f20294…): the first Run attempt STOPPED (S-R1: P1 state v3c3-s31 T=1,800 objective differed from the record by +1.137e-13 veh·h = 2 ULP; costs within 1e-9). See ${VP}/QV3_REPORT.md (7e196d9f…), ${VP}/P1_REPORT.md (c28c9178…), ${VP}/LOG.md, STOP_VP (ebd85663…). User chose: (D-K9-108) post-data fix r3: R1 objective tolerance |replay − record| ≤ 1e-9 veh·h (same as costs), no determinism re-check run; (D-K9-109) keep s31 T=3,450 (started 19 s after STOP_VP, all checks passed) with a mark; fix vp_queue.py so it re-checks STOP_VP after acquiring the lock; drop the code_va.tree.json line (timestamp field) from the EXT pin list and compare its ok/count fields instead; delete STOP_VP only after the r3 pins are recorded. Keep finished outputs (s31 T=3,300 and T=3,450 plant_A); move the stopped P1 job folder and its .done to *_interrupted_* and rerun it.`
out.amend = await agent(`${RULES}
${CTX}
${RESUME}
TASK (Amend r3): write ${VP}/PRE_VP_R3.md (data-after amendment, labelled 데이터 뒤) with exactly these changes; patch only vp_probe/vp_jobcheck tolerance for R1 objective and vp_queue.py STOP re-check (show diffs in LOG); rerun self-tests; re-pin as SHA256SUMS_VP_r3.txt / SHA256SUMS_VP_EXT_r3.txt (record in LOG before any new computation); move the interrupted P1 job folder and .done; then delete STOP_VP. No probe computations. Return pass=true with sha256.`, { label: 'amend-r3', phase: 'Run', schema: SCHEMA })
if (!out.amend || !out.amend.pass) return { stoppedAt: 'AmendR3', out }
const RUNS = [
  { key: 'qv3', prompt: `${RESUME}
TASK (Run Q-V3 probes A and B exactly per the fixed PRE_VP + PRE_VP_R3): verify fixation and r3 pins, resume (skip finished states), run under the lock, apply stop rules. Write ${VP}/QV3_REPORT.md r2 (keep r1 as QV3_REPORT_r1.md) (+ json with sha; copy to ${REP}). Return status, summary, artifacts, open.` },
  { key: 'p1', prompt: `${RESUME}
TASK (Run P1 tracing exactly per the fixed PRE_VP + PRE_VP_R3): verify fixation and r3 pins, resume (rerun the interrupted first state), run under the lock, apply stop rules. Write ${VP}/P1_REPORT.md r2 (keep r1 as P1_REPORT_r1.md) (+ json with sha; copy to ${REP}). Return status, summary, artifacts, open.` },
]
out.runs = await parallel(RUNS.map(r => () => agent(`${RULES}\n${CTX}\n${r.prompt}`, { label: 'run-' + r.key, phase: 'Run', schema: SCHEMA })))
if (out.runs.some(r => !r || !r.pass)) return { stoppedAt: 'Run', out }

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nRun reports: ${JSON.stringify(out.runs).slice(0, 6000)}\nTASK (Synthesize): write ${VP}/VP_RESULTS.md: §0 plain answer (≤ 12 lines: how our plant values VSL 101/100/90 vs 110 at V-A states; how faithful it is under VSL; where the VSL-independent bias comes from, ranked by evidence), §1 tables, §2 meaning for C1 reading ((1)·1098 lines) and for the plant-fix order P1→P5, §3 user decisions (numbered, recommended marked: which fix to design first, whether a VSL closed-loop pair is worth planning, etc.), §4 pins. No verdict words. Return status, Korean summary (≤ 25 lines), artifacts with sha, open.`, { label: 'synth', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nSynthesis: ${JSON.stringify(out.synth || {}).slice(0, 3000)}\nTASK (Verify): pin your own tools before reading outputs; recompute the key numbers of ${VP}/VP_RESULTS.md from raw outputs with independent code; re-run one probe-A state and one P1 ablation and confirm bit identity; check every claim follows from numbers and tags are right. Apply corrections as r2 (keep r1), write ${VP}/VERIFY_VP.md, copy finals to ${REP}. Return status, Korean summary for the user (≤ 25 lines), artifacts + sha, open (user decisions).`, { label: 'verify', phase: 'Verify', schema: SCHEMA })
return out
