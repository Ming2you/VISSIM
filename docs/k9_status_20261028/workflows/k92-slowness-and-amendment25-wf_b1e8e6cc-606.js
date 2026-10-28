export const meta = {
  name: 'k92-slowness-and-amendment25',
  description: 'Find why keyed K9-2 computations are much slower (captures 30-60 s -> 380-430 s, decision replays +400 s) using existing outputs and, if needed, offline profiling on s31/s43 states; in parallel draft amendment 25 (randSeed-normalized network check, sealed s47 logs); adversarial verification of both',
  phases: [
    { title: 'Investigate', detail: 'slowness cause + amendment 25 draft (parallel)' },
    { title: 'Verify', detail: 'adversarial checks' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const B1 = K8 + '/k92/bundle1'
const OUT = B1 + '/slow'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations first time. Tag [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- No VISSIM, no COM, no runners, no commits, no pushes, no edits in GWT8 (D:/VISSIM-merge/sim3-n31-k8, head b9734abe) or frozen trees. Read-only on run folders and existing probe outputs (D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/, ${B1}/k92_probe/, ${B1}/impl/). Write under ${OUT}/ and D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/slow/.
- Offline profiling runs are allowed ONLY on v3c3-s31 / v3c3-s43 states already used by the probe (NEVER v3c3-s47 — blind sample, D-K9-40), in scratch copies of the probe trees (D:/VISSIM-merge/k8_gate_trees/k92b1/ or copies), one heavy job at a time, DETACHED via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, ≤ 6 profiling jobs total. Profiling must not overwrite any probe output (use new output dirs). Kill only own PIDs.
- Do not open any v3c3-s47 log/output (sealed until the judging stage). Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; seeds with network prefix. No verdict language. AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs.
`

const CTX = `
CONTEXT
- K9-2 bundle 1 (amendment 24 fixed, ${K8}/K8_PREDECLARATION_AMENDMENT_24.md sha d46db6dc…): W key urban.sc109w_through_saturation (SC109_W_SC108_to_E 619.6 → 5209.8) + H-b seed key urban.capacity.head_floor_seed ((173,p4) seed 1045.1612903225805, learning kept). The Implement stage built the commits' content in ${B1}/impl/repo (not committed), ran the mini probe (§3.3) and STOPPED at k92_vissim_ref.py:57-58 (v3c3-s43 .inpx differs only by randSeed). Report: ${B1}/IMPLEMENT.md, log ${B1}/LOG.md, probe outputs ${B1}/k92_probe/ and D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/probe/.
- Observation to explain (D-K9-41): keyed TL3 captures took ~380–430 s vs keyless ~30–60 s; keyed decision replays ~400 s longer than base arms. Questions: which stage got slower (plant rollout events? AD tape size? recorder/metadata k92_record? cfg deep copies? validation/asserts? learning loop of the head floor? more vehicles moving through SC109 so more events?), is it in production code paths (would affect closed-loop decision time and the GB-9′ wall-clock gate ≤ 1.5× K7, StallSec 2400) or only in gate/probe instrumentation, and is it proportional to traffic (state-dependent) or constant overhead.
- User decisions: ${K8}/K9_1_J1_NOTES_20261013.md (sha 711a1180…; D-K9-39 amendment 25 + resume remaining probe steps only; D-K9-40 s47 job logs to a sealed folder unopened before k92t; D-K9-41 find the slowness cause first).
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

phase('Investigate')
const [slow, a25] = await parallel([
  () => agent(`${RULES}\n${CTX}\nTASK (Slowness): find the cause. First mine existing timing data (probe logs, progress jsonl, capture/run.json wall fields, per-stage timers, decision progress events, AD tape node counts) for keyed vs keyless pairs on the same states. Then, if needed, profile (cProfile or the existing progress hooks) one keyed vs keyless TL3 capture and one keyed vs base decision replay on an s31/s43 state. Identify the responsible code path(s) with file:line, whether it's production or instrumentation, whether it scales with traffic, and estimate the closed-loop decision-time impact (vs J1 decisions 409–490 s median, max 588 s) and risk vs GB-9′ / StallSec. Propose remedies (if any) as options without implementing. Write ${OUT}/SLOW.md (5–10 line plain summary first). Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: 'slowness', phase: 'Investigate', schema: SCHEMA }),
  () => agent(`${RULES}\n${CTX}\nTASK (Amendment 25 draft): write ${OUT}/K8_PREDECLARATION_AMENDMENT_25_DRAFT.md: (1) the fix of k92_vissim_ref.py network identity check — exact rule (normalize only the randSeed attribute value, then sha must equal the v3c3 network 3de889f0's normalized sha; record each seed's raw sha; any other difference ⇒ STOP), how the fixed tool is pinned (sha) and where it is also used (K9-2-0 harness commit, k92t F); (2) resumption rule: keep completed probe outputs (list them with sha), run only the remaining steps (s43 VISSIM reference, wall-clock 8 pairs, report) and re-check the stop/ask rules 1–6 of §3.3; (3) sealed-log rule for v3c3-s47 jobs (D-K9-40): where logs go, who may open when, what counts as a breach (STOP); (4) placeholders for any slowness-related change ONLY as 'to be decided after SLOW.md' (no content). Verify the randSeed-only difference claim yourself by a normalized diff of the s31/s43/s47 NC .inpx files (do not read s47 outputs — the .inpx network file is not an output; if you are unsure whether reading s47's .inpx is allowed under the blind rules, only compute its sha and normalized sha, no content diff, and say so). Return status, Korean summary (<= 20 lines), artifacts, open.`, { label: 'amend25', phase: 'Investigate', schema: SCHEMA }),
])

phase('Verify')
const ver = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially verify ${OUT}/SLOW.md (re-open timing evidence, recompute 3+ numbers, try to refute the named cause; check no s47 data was opened and probe outputs were not overwritten) and ${OUT}/K8_PREDECLARATION_AMENDMENT_25_DRAFT.md (rule too wide/narrow, blind-rule consistency, resumption soundness). Write ${OUT}/VERIFY_SLOW_A25.md, apply corrections to both (keep _r1). Slowness return: ${JSON.stringify(slow || {}).slice(0, 3000)}. A25 return: ${JSON.stringify(a25 || {}).slice(0, 2000)}. Return status, Korean summary (<= 25 lines) suitable for relaying to the user, artifacts + sha256, open (user decisions).`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

return { slow, a25, ver }
