export const meta = {
  name: 'j1-causes-offline',
  description: 'Offline (no VISSIM) cause analysis of the J1 findings: link 174 jam and input 1083 uninserted, Ω-outside increase and off-ramp reduction, meter command mapping (900 vph fixed), controller model vs VISSIM around SC109/link 174; synthesis with K9-2 proposals; adversarial verification',
  phases: [
    { title: 'Investigate', detail: '4 parallel lenses' },
    { title: 'Synthesize', detail: 'CAUSES.md + K9-2 proposal' },
    { title: 'Verify', detail: 'adversarial check' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const J1 = K8 + '/j1'
const OUT = J1 + '/causes'
const MEM = 'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file/JSON paths and code file:line.
- READ-ONLY on all run folders (J1: D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31, _k8j1_s41, _k8j1_s43; NC3 and R-obs under D:/VISSIM_runs/20261001_*), frozen trees (FRZ_K8 D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824, FRZ_K8b ..._b9734abe_202610141821), worktrees. Write only under ${OUT}/ and D:/VISSIM_runs/20261001_v3c3/reports/k8/j1_causes/.
- No VISSIM, no COM, no runners, no decision replays, no commits. No kills. Light/moderate Python; FZP parsing BELOW_NORMAL, one heavy job at a time, detach via WMI if > ~5 min. Reuse parsed outputs from ${J1}/analysis/ (scans/, out/, verify/out/) where possible.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix.
- No verdict language (no 'SDMPC wins/loses/improves'); this is cause analysis, not judgement. Always keep Ω together with Ω-outside when citing totals.
- AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs in ${OUT}/.
`

const CTX = `
CONTEXT
- J1 report: ${J1}/analysis/J1_REPORT.md (sha 4bf31b13…) — read §0, §3–§9, §11, §12, §15 first. Paired d = J1 − same-seed NC3 (v3c3-s31 rerun / s41 / s43): Ω −18.7/−725.9/−203.6; ④ +94.6/−534.5/+160.6; Ω-outside (④−③) +113.2/+191.5/+364.2; lane-change removals +87/+34/+116 (197 of 237 extra in Ω urban links); Ω off-ramp part −301.9 (3/3); urban_omega +341.3/−147.4/+265.3; input 1083 (link 21 → connector 10112 → link 174) blocked in s31r and s43 (remain 89/184, link 174 TTT J1 339.5/361.4 vs NC3 43.1/46.1), not in s41; SC1001 EB 127 counts much lower and FW_W spillback windows almost none in J1; meters: all 8 written as rate 900 vph · green 10 s in all 61 decisions of all runs although action JSON ramp_metering shows 1512/3024; VSL < 110 only 7/165 decisions (FW_E seg10 100).
- Known defects/caveats: in-tree k9/J1_CAVEAT.md + ${J1}/J1_CAVEAT_ADDENDUM.md (b3484937…) — esp. phantom movement stock bias (SC7_E_SC16_to_N_SC11 at link 1210009600, SC109_N_SC16_to_W_SC108 at link 1210009402; phases SC7_p3, SC109_p1 green 0), R1 N-layer SC105 N / SC2004 S 206.53 constants + uniform β, M1/M2, F13/F14/F15/F19, ramp under-supply, ${K8}/sagate/K91_OUTCOME.md §5–§6.
- Relevant project memory (data): ${MEM}/vissim-urban-batch1-and-rmcal-20260926.md (S1: SC109 p3 starvation → link 174 +252), ${MEM}/vissim-boundary-movement-capacity-206.md (boundary movement capacity 206.53 → SC109 starvation root cause), ${MEM}/vissim-ramp-meter-actuation-is-binary.md (meter realisable set {0, ≥600–1000, open}), ${MEM}/vissim-metering-lever-structurally-dead.md, ${MEM}/vissim-sc5-sc6-vertex-gridlock.md, ${MEM}/vissim-j1-k8-results-20261015.md, ${MEM}/codex-355-handoff-compare-20261013.md.
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

const LENSES = [
  { key: 'link174', prompt: `Lens: LINK 174 JAM AND INPUT 1083 UNINSERTED (v3c3-s31 rerun, v3c3-s43; s41 and NC3 as contrast). Output ${OUT}/lens_link174.md. Find which signal(s)/phase(s)/movements discharge link 174 (and links 21, 10112 region), the time course of the queue from FZP/link evaluation (onset ~4350 s), what the SDMPC commanded for those signals (green splits, offsets per decision from action JSON/CSV) vs NC3 native timing, whether the jam coincides with phase starvation (e.g. SC109 p3/p1), whether the controller's model saw it (its predicted queues/stocks for those movements vs VISSIM), and whether known defects explain it: boundary movement 206.53 constants, phantom stock bias (SC109_N_SC16_to_W_SC108, phase SC109_p1 green 0), uniform β, missing signals. Why does s41 not show it? Quantify contributions where possible.` },
  { key: 'outside', prompt: `Lens: Ω-OUTSIDE INCREASE AND Ω OFF-RAMP REDUCTION. Output ${OUT}/lens_outside.md. Decompose the Ω-outside TTT increase by link group (urban outside Ω, freeway outside, ramps, uninserted by input) and time; identify the top links and the mechanism (queues pushed from Ω boundary links to outside links by signal timing? spillback? metering? input blocking 282/1083/1098?). For the Ω off-ramp reduction (−301.9, 3/3) and SC1001 EB/127 changes, identify what changed (SA-related signal timing at SC1001/SC1002? W_out discharge? 10491 blocking) and whether the same vehicles show up outside Ω (transfer) — link-level flows/queues J1 vs NC3. Note that Ω/objective is what the controller minimises; check whether the controller's objective excluded the links that grew (Ω635 membership) and whether that explains a transfer.` },
  { key: 'meter', prompt: `Lens: METER COMMANDS. Output ${OUT}/lens_meter.md. Trace in code (FRZ_K8/FRZ_K8b adapter + runner VBS) how action JSON ramp_metering values (e.g. 1512, 3024) become the written 'rate 900 vph · green 10 s' for all 8 meters in every decision: the mapping/clipping rule, whether 900 vph·10 s equals 'open/max' in the actuation model, what NC3 meters do (native/off?), whether the SDMPC ever chose anything that maps differently, and whether the optimizer's meter decision variable is effectively inactive (bounds, price, capacity). Compare with K7 behaviour and with memory notes on metering being structurally dead / binary actuation. Conclude whether metering is effectively off in J1 and why.` },
  { key: 'model', prompt: `Lens: CONTROLLER MODEL VS VISSIM ON THE AFFECTED AREAS. Output ${OUT}/lens_model.md. Using decision records (action JSON predictions, obs150 states) and FZP/link evaluation, compare what the controller predicted vs what VISSIM did for (a) the link 174 / SC109 / input 1083 area, (b) the Ω-outside links that grew most, (c) SC1001 EB / W_out / 10491, over the decisions around the onset (e.g. T=3900–6000) in v3c3-s43 and the s31 rerun. Report prediction bias per area, and whether the bias is consistent with known defects (206.53 constants, phantom stocks, uniform β, M1/M2) or something new. Keep to decision-record fields; do not re-run any decision.` },
]

phase('Investigate')
const lenses = await parallel(LENSES.map(l => () => agent(`${RULES}\n${CTX}\nTASK: ${l.prompt}\nStart the file with a 5–10 line plain summary. Return status, Korean summary (<= 25 lines), artifacts, open.`, { label: `lens:${l.key}`, phase: 'Investigate', schema: SCHEMA })))

phase('Synthesize')
const synth = await agent(`${RULES}\n${CTX}\nTASK: read ${OUT}/lens_link174.md, lens_outside.md, lens_meter.md, lens_model.md (re-open evidence where they disagree) and write ${OUT}/CAUSES.md: §0 plain summary (what most likely caused each J1 finding, with evidence strength), §1 per finding cause chain with citations, §2 which known defects are implicated and how strongly, §3 new defects found, §4 K9-2 proposal: candidate items ranked by evidence and expected relevance to the J1 findings, each with fix idea, evidence source (existing FZP vs needs new runs), effect on the K9-1 judging/J1 comparability, rough cost — present as options, recommendation marked [추론]; §5 open questions for the user. Return status, Korean summary (<= 30 lines), artifact + sha256, open.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
const ver = await agent(`${RULES}\n${CTX}\nTASK: adversarially verify ${OUT}/CAUSES.md. Pick at least 15 decision-relevant claims (every cause claim in §0/§1, every new-defect claim, every number), re-open the evidence and try to refute; recompute 4+ numbers by a different route. Check language rules and that no verdict is implied. Write ${OUT}/VERIFY_CAUSES.md (claim | 확인/틀림/불확실 | 근거 | 고칠 문장), apply corrections to CAUSES.md (keep CAUSES_r1.md) with a change log section. Return status, Korean summary (<= 30 lines) suitable for relaying, artifact + sha256, open (user decisions needed for K9-2).`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

return { lenses: lenses.map((x, i) => ({ key: LENSES[i].key, status: x ? x.status : null })), synth, ver }
