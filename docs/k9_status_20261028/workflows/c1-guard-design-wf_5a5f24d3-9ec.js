export const meta = {
  name: 'c1-guard-design',
  description: 'C1-2 design: FW_W entrance protection (links 129/10491 storage-limit guard, D5 form) per D-K9-100 + Ω701 explained-difference condition (D-K9-98) + thread erratum (D-K9-99); fact finding from existing code/data, design draft with options, adversarial review; stop for user decisions',
  phases: [
    { title: 'Facts', detail: 'plant/decision code, existing VISSIM data, codex guards' },
    { title: 'Draft', detail: 'GUARD_DESIGN draft + C1-2 items' },
    { title: 'Review', detail: 'adversarial review, r2' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const CC = K8 + '/c_port'
const C1 = CC + '/c1'
const G = C1 + '/guard'
const TK = 'D:/VISSIM-merge/k8_gate_trees/c1'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- READ-ONLY for code: GWT8 D:/VISSIM-merge/sim3-n31-k8 (stay at c20aff1d, no branch/commit/push), codex trees, frozen trees, all run folders, D:/VISSIM_handoff/20261024, Y:. No VISSIM, no COM, no runners, no freezes. Scratch outputs only under ${G}/ and ${TK}/guard/. Heavy jobs (FZP scans > 2 min, plant jobs) one at a time under the shared lock ${HL} (create exclusively, wait/retry with ≥ 20 s pause after release, delete only your own), detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B; NUMBA_NUM_THREADS removed (K9-2 form, D-K9-99). Kill only own PIDs; other sessions' VISSIM/python (codex work, the VSL workflow) never touched.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix; v3c3-s47 values never opened (blind F sample).
- No verdict words. Any threshold derived from data seen now is labelled "데이터 뒤". Prefer existing outputs (INPUT1099, READBACK_METER, B_RESULTS, VA analysis, N12/N34 scans) over new scans; new scans only if a needed number does not exist. Signal greens GREEN-only (no amber).
- Evidence by name + sha, no new path strings in anything meant for config/evidence.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha 4429c003…): D-K9-94 (C1 design Q1–Q26), D-K9-96·97 (P0 resume; RV-1 np_only with M3, RV-2 storage guard floor 9→8), D-K9-98 (Ω701 keeps the 29-connector link_to_storage channel; new condition: Ω-arm vs OFF initial-state difference must be fully explained by vehicles on the 29 connectors moved into their declared storage, else stop; F reports the channel effect), D-K9-99 (threads: K9-2 form, erratum to amendment C1 §3), D-K9-100 (Q2 changed from (가) to (나): ADD a storage-limit protection for links 129·10491 (METER_NEXT2 D5 form) to C1; Q3 SG2 stop rule unchanged; form/threshold/target to be decided by the user after this design draft).
- Amendment C1 fixed: ${K8}/K8_PREDECLARATION_AMENDMENT_C1.md (a98580dd…), ${C1}/AMENDMENT_C1_FIXED.md; design ${CC}/C1_DESIGN_DRAFT.md r2 (§2 point 2, Q2/Q3 rows ~:527-528, §8.6, §9.1); P0/probe ${C1}/P0_PROBE.md r2 (e467583f…; Q20 B RM_C10639 guard never fired, Q21 B SG2 cut by codex SC1001 own cost at price 0 → green to SG5 EBL, Q22 plant has links 127·129·10491 in stopline_approach.py but no link 26), ${C1}/C1_PROBE_RESULTS.md/.json, ${C1}/LOG.md, probe patch ${C1}/tools/c1_probe.patch (5cdc6eb1…), trees ${TK}/trees/{p0,probe}_5cdc6eb1.
- Chain evidence: ${CC}/INPUT1099.md r2 (SC1001 SG2 EBT shortening → link 127 → 129/10491 → link 26 lane 1 end 3,200–3,700 m → entrance 1099 insert −10.4/−15.2/−2.8 %), ${CC}/READBACK_METER.md, ${CC}/VERIFY_C_PREP.md, ${K8}/rmcause/r2c_n/METER_NEXT2.md §2.2 N2 (D5: model threshold = whole reservoir in_SC1001_W 1,237.8 veh vs VISSIM local ~45 connector + ~10 link-129 lane-1; exit port min(1,400×1, 127 free, S_eff)), N12/N34 files in ${K8}/rmcause/r2c_n/, ${K8}/codex_handoff/R_MECH.md (codex guards incl. urban storage guard C5), ${K8}/codex_handoff/B_RESULTS.md r2, ${K8}/k92/va/analysis/VA_REPORT.md.
- Runs (read-only): NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run, V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}, B D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43}, VSL-only D:/VISSIM_runs/20261027_vsl_v3c3/s{31,41,43} (being analysed by another workflow — read only, do not interfere).
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

phase('Facts')
const FACTS = [
  { key: 'code', prompt: `TASK (Facts: code): map exactly where a links 129·10491 protection could act, at c20aff1d plus the C1 probe patch: (1) plant representation of 127·129·10491·26 and the exit port/reservoir in_SC1001_W (file:line), what the plant predicts when 10491/129 fill (does it block FW_W cells, when), (2) decision layer: SC1001 phase candidate generation/refinement (how SG2=EBT=p3 green floors could be imposed), meter 10490 candidate filtering (C1 storage guard M4 code path and whether it can take a second storage target), (3) what the controller can OBSERVE at decision time for 10491 / link 129 lane 1 / link 26 (detectors, link evaluation, queue counters, observation JSON keys) — only observable quantities can drive a guard, (4) codex: any FW_W entrance / weaving / urban storage guard (C5 urban storage guard, head resource v11) and whether its code can be reused for 129/10491 (codex file:line). Write ${G}/FACTS_CODE.md. Return pass=true if done.` },
  { key: 'data', prompt: `TASK (Facts: data): from EXISTING outputs first (INPUT1099, READBACK_METER, N12/N34 scans, VA/B analyses), else new FZP scans under the lock: for NC3, V-A, B × v3c3-s31/s41/s43, give time series (300 s bins, 900–9,000 s) of: vehicles on connector 10491, link 129 lane 1 (last 200 m), link 127, link 26 lane 1 near the end (3,200–3,700 m), entrance 1099 unserved queue, and SC1001 SG2 GREEN-only seconds per cycle; identify the onset (first bin) of the chain per run and the occupancy values of 10491 and 129 lane 1 in the bins just before onset (candidate thresholds, labelled 데이터 뒤). Also whether the same signals are available to the controller online (match with FACTS_CODE observability when ready; otherwise list the VISSIM quantities). Write ${G}/FACTS_DATA.md (+ json with sha). Return pass=true if done.` },
]
const facts = await parallel(FACTS.map(f => () => agent(`${RULES}\n${CTX}\n${f.prompt}`, { label: 'facts-' + f.key, phase: 'Facts', schema: SCHEMA })))

phase('Draft')
const draft = await agent(`${RULES}\n${CTX}\nFacts: ${JSON.stringify(facts).slice(0, 6000)}\nTASK (Draft): write ${G}/GUARD_DESIGN_DRAFT.md for 보충 C1-2. Sections: 0 쉬운 요약 (what goes wrong in VISSIM, what the model misses, what the guard does, in plain Korean); 1 facts with tags; 2 guard options — at least: (A) decision-layer SC1001 SG2(EBT) green floor when observed 10491 / 129-lane-1 occupancy exceeds θ, (B) meter 10490 no-tightening (or forced open) under the same trigger, (C) plant fix: local lane-1 threshold for the 129/10491 port (D5 model fix), (D) combinations — for each: exact rule, observable input, threshold candidates with provenance (데이터 뒤 where applicable), key name under c1_port, insertion file:line, key-off byte identity, interaction with Ω701 (link 37 added to SC1001), meters (M1–M5), RV-1/RV-2, SG2 stop rule (Q3 unchanged), expected effect and risks (e.g. starving SG5/EBL, link 37), cost; recommended option with reasons; 3 the D-K9-98 Ω701 explained-difference condition (exact computable definition: per-storage first-state difference = Σ vehicles on the 29 connectors mapped by link_to_storage, tolerance, which states, stop rule; labelled 데이터 뒤), 4 thread erratum text (D-K9-99), 5 changes to amendment C1 gates/stop rules/probe arms (new arm(s) for the guard, G-K gates, S-C1 rules, R-b SG2 check unchanged), 6 decision table G1..Gn (each with recommended option marked), 7 cost and order (resume probe after C1-2 fixation). No TBD except the user questions. Return pass=true with sha256.`, { label: 'draft', phase: 'Draft', schema: SCHEMA })

phase('Review')
const rev = await agent(`${RULES}\n${CTX}\nDraft report: ${JSON.stringify(draft || {}).slice(0, 3000)}\nTASK (Review): adversarially review ${G}/GUARD_DESIGN_DRAFT.md: verify every file:line and number against code/data; check observability (the guard must use only what the controller sees online); look for definitions that hold or fail by construction (K9-2 lessons), unintended effects on SC1001 other phases / link 37 / meters, key-off identity, conflict with RV-1/RV-2 and the SG2 stop rule, whether thresholds are data-after and labelled, whether the Ω701 explained-difference condition is computable and not trivially true/false. Apply fixes as r2 (keep _r1), write ${G}/REVIEW_GUARD.md. Return status, Korean summary for the user (<= 30 lines: the options in plain words, recommended choice and why, the questions G1..Gn with recommended answers), artifacts with sha256, open.`, { label: 'review', phase: 'Review', schema: SCHEMA })
return { facts, draft, rev }
