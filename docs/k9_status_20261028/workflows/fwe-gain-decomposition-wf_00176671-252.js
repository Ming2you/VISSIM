export const meta = {
  name: 'fwe-gain-decomposition',
  description: 'D-K9-106: offline decomposition of FW_E improvement — NC FW_E congestion per seed/network, link×time breakdown of FW_E mainline gains (B, V-A, VSL-only on v3c3; codex joint/A1 and split arms on 64cf-s29), meter actions and ramp merge flows vs gain timing, costs; synthesize a C1 FW_E reference line; verify. No VISSIM, no code changes',
  phases: [
    { title: 'Declare', detail: 'PRE_FWE: questions, data inventory, metrics, tool pins' },
    { title: 'Run', detail: 'R1 NC regime, R2 gain decomposition, R3 meters/ramps, R4 codex split arms' },
    { title: 'Synthesize', detail: 'FWE_DECOMP + C1 reference line' },
    { title: 'Verify', detail: 'independent recount' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const FE = K8 + '/fwe_decomp'
const TK = 'D:/VISSIM-merge/k8_gate_trees/fwe_decomp'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/fwe_decomp'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]/[계산]; cite file:line / JSON paths.
- Read-only everywhere except ${FE}/ and ${TK}/ (scratch). No VISSIM, no COM, no runners, no freezes, no code changes, no commits/push (GWT8 D:/VISSIM-merge/sim3-n31-k8 stays at c20aff1d). Prefer EXISTING outputs/caches (OMEGA701 recount cache, w1099 scans, vsl_v3c3 cell/zone scans, B/V-A analyses, READBACK_METER, A1 results) over new FZP scans; new scans only for numbers that do not exist. Heavy jobs (> 2 min or large FZP) one at a time under the shared lock ${HL} (create exclusively, retry; after release pause ≥ 20 s before re-acquiring so C1 / VSL-plant workflows get turns; delete only your own), detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. Kill only own PIDs; other sessions' VISSIM/python never touched.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened (no sealed/ folders, no *_s37 etc.); no codex 64cf-s59/s61/s67 numbers; seeds always with network prefix; v3c3-s47 values never opened.
- Declare metrics/tools (sha) in PRE_FWE.md before computing new numbers; post-data analyses labelled "데이터 뒤". No verdict words (no win/lose). Ω701 always shown with ④ and Ω-outside when shown. Urban roads = codex partition ONLY (D-K9-104). FW_W is not an improvement target (monitor only). Signal/meter greens GREEN-only. Evidence by name + sha; never read seed tokens from folder names (use provenance/run.json). Same-seed pairs only; no averaging across seeds; 64cf and v3c3 never subtracted from each other (side by side only).
- Append dated KST entries to ${FE}/LOG.md (create). Report copies to ${REP}.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha a11fc94c…): D-K9-104 (Ω701 is the objective/main area; urban roads = codex partition; FW_E is the main improvement target; my earlier claim that the 8 % gap is mostly 1099 demand was wrong for Ω701), D-K9-106 (this task).
- Known numbers: ${K8}/codex_handoff/HANDOFF_RESULTS.md r2 §1.1–1.2 (codex form 0–8100: codex 64cf-s29 joint − NC Ω701 −494.7, ① −283.7 (−13.35 %), ② −156.6, urban −294.6 (−8.09 %), ④b 1099 −69.2; V-A − NC3 ① −21.5/−66.7/−6.9), ${K8}/codex_handoff/B_RESULTS.md r2 §1.2 (our form 0–9000: B − NC3 ① −37.3/−178.1/−88.9, ② +28.2/−245.2/−34.7, ④b 1098 −25.5/−19.3/−113.5; V-A − NC3 ① −12.3/−72.6/−5.3), ${K8}/codex_handoff/OMEGA701_V3C3.md (definitions: ① 7 links 74·10699·2·10613·119·10702·24, ② 19 links, integration forms, cache files), ${K8}/codex_handoff/a1/A1_RESULT.md r2 (A1 = our reproduction of codex joint on 64cf-s29), ${K8}/c_port/READBACK_METER.md (B meter readback per cycle), ${K8}/c_port/INPUT1099.md r2, ${K8}/vsl_v3c3/VSL_RESULTS.md r2 + ${K8}/vsl_v3c3/o1o2/ (zone/cell definitions VSa/VSb/M1/Mu/VS0/B1/B2, FZP cell scanners with sha; NC3 s31 M spillback 0 min, s41 12 min; 64cf NC B1 spillback 62 min), ${K8}/rmcause/ (METER_CAUSE r2, METER_NEXT r2, METER_NEXT2 r2: why V-A meters never moved; N4 meter service per green), memory facts: FW_E collapse origin = 10681 merge lane 2 (vissim-fwe-plant-structure-20260927), off-ramp lane-1 collapse history (vissim-fwe-collapse-is-offramp-lane1).
- Runs (read-only): NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run; V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}; B D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43}; VSL-only D:/VISSIM_runs/20261027_vsl_v3c3/s{31,41,43}; A1 D:/VISSIM_runs/20261025_codex_a1_s29; LNC D:/VISSIM_runs/vsl_repro_s29/none/run (and vsl_repro_s29 other arms); codex handoff copy D:/VISSIM_handoff/20261024 (HANDOFF.md, raw/, derived/, analysis/; sealed/ excluded and never opened) — its §5 lists split arms (RM-only / TSC-only / VSL-only etc.) for 64cf-s29 if any.
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
out.decl = await agent(`${RULES}\n${CTX}\nTASK (Declare): (1) inventory the available arms and their FZP/readback/decision files with sha (v3c3: NC3, V-A, B, VSL-only × s31/s41/s43; 64cf-s29: codex joint, codex NC, any split arms from HANDOFF §5, A1, LNC and vsl_repro_s29 arms) and which existing caches already hold per-link per-time stocks; (2) write ${FE}/PRE_FWE.md fixing: questions R1 (NC FW_E congestion: ① level, collapse onset time/location by cell, bottleneck link/lane, spillback minutes per zone), R2 (gain decomposition: ① and ② differences by link × 300 s window, zone/cell speed differences; both integration forms where relevant), R3 (meter actions: GREEN-only meter greens/readback per meter per cycle, ramp merge flows into FW_E per merge per window, ramp/approach stocks 129·31·68·70 and connectors, ④b 1098; timing of first tightening vs gain onset; cost location), R4 (codex split arms on 64cf-s29: ① / ② / urban / Ω701 / ④ / Ω-outside per arm), and the synthesis outputs (attribution table with tags; a C1 FW_E reference line = report-only fields that C1 will be compared against, e.g. ① and ② same-seed differences, per-meter tightening windows, merge-flow change); metric definitions by name + sha of existing tools; tool pins; order (light first, heavy under lock); stop rules. Return pass=true with sha256.`, { label: 'declare', phase: 'Declare', schema: SCHEMA })
if (!out.decl || !out.decl.pass) return { stoppedAt: 'Declare', out }

phase('Run')
const RUNS = [
  { key: 'r1', prompt: 'R1 (NC FW_E congestion regime per seed/network)' },
  { key: 'r2', prompt: 'R2 (FW_E gain decomposition by link × time and zone/cell)' },
  { key: 'r3', prompt: 'R3 (meter actions, ramp merge flows, timing vs gain, cost location)' },
  { key: 'r4', prompt: 'R4 (codex split arms on 64cf-s29)' },
]
out.runs = await pipeline(RUNS, r => agent(`${RULES}\n${CTX}\nTASK (Run ${r.prompt} exactly per the fixed ${FE}/PRE_FWE.md): verify PRE_FWE sha and tool pins first; compute; write ${FE}/${r.key.toUpperCase()}_REPORT.md (+ json with sha; copy to ${REP}). Return status, summary, artifacts, open.`, { label: 'run-' + r.key, phase: 'Run', schema: SCHEMA }))
if (out.runs.some(r => !r || !r.pass)) return { stoppedAt: 'Run', out }

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nRun reports: ${JSON.stringify(out.runs).slice(0, 8000)}\nTASK (Synthesize): write ${FE}/FWE_DECOMP.md: §0 plain answer (≤ 12 lines: how much FW_E congestion exists in v3c3 NC per seed vs 64cf; where and when B and codex gained on FW_E; which meters/timing; what V-A lacked; what C1 must do to move FW_E), §1 tables, §2 attribution (each claim tagged; separate measured co-timing from causal inference), §3 C1 FW_E reference line (exact report-only fields and their B / V-A / NC3 values per seed, for inclusion in supplement C1-2 before C1 data), §4 user decisions (numbered, recommended marked), §5 pins. Return status, Korean summary (≤ 25 lines), artifacts with sha, open.`, { label: 'synth', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nSynthesis: ${JSON.stringify(out.synth || {}).slice(0, 3000)}\nTASK (Verify): pin your own tools before reading outputs; recompute the key numbers of ${FE}/FWE_DECOMP.md (① / ② differences by window for at least B and V-A all three seeds and codex joint, meter tightening windows, merge flows) from raw FZP/readback with independent code; check that every causal claim is tagged [추론] unless tested, that 64cf and v3c3 are never subtracted, that urban roads use the codex partition, that no sealed/s47 data was read. Apply corrections as r2 (keep r1), write ${FE}/VERIFY_FWE.md, copy finals to ${REP}. Return status, Korean summary for the user (≤ 25 lines), artifacts + sha, open (user decisions).`, { label: 'verify', phase: 'Verify', schema: SCHEMA })
return out
