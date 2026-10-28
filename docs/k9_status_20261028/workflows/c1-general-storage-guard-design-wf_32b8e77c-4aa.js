export const meta = {
  name: 'c1-general-storage-guard-design',
  description: 'D-K9-107: redesign C1-G as a general storage-capacity guard for ALL controlled intersection approaches (signal-head lanes + headless feeder links like 129/10491) and ALL meter ramps; trigger = approach storage capacity exceeded (lane level); inventory from network + existing runs, data check of exceedance/spillback/false triggers, design draft r3 with options, adversarial review; stop for user decisions. No code changes, no VISSIM',
  phases: [
    { title: 'Inventory', detail: 'approaches, lanes, storage capacity, receivers, servers, feeders' },
    { title: 'Data', detail: 'exceedance vs spillback in NC3/V-A/B/VSL, codex USG firing in B' },
    { title: 'Draft', detail: 'GENERAL_GUARD_DESIGN r0' },
    { title: 'Review', detail: 'adversarial review → r1' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const C1 = K8 + '/c_port/c1'
const G = C1 + '/guard'
const GG = G + '/general'
const TK = 'D:/VISSIM-merge/k8_gate_trees/c1/guard_general'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]/[계산]; cite file:line / JSON paths.
- READ-ONLY for code/runs: GWT8 D:/VISSIM-merge/sim3-n31-k8 (stay at c20aff1d; no branch/commit/push), probe trees under D:/VISSIM-merge/k8_gate_trees/c1/trees/, codex trees, frozen trees, all run folders, D:/VISSIM_handoff/20261024, Y:. No VISSIM, no COM, no runners, no freezes, no plant/decision jobs. Scratch outputs only under ${GG}/ and ${TK}/. Prefer existing outputs (guard FACTS_DATA/FACTS_CODE, w1099 scans, OMEGA701 caches, vsl_v3c3 scans); new FZP scans only where a needed number does not exist, one at a time under the shared lock ${HL} (create exclusively, retry; after release pause ≥ 20 s so C1/VSL-plant/FW_E workflows get turns; delete only your own), detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. Kill only own PIDs; other sessions' processes never touched.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix; v3c3-s47 values never opened.
- Thresholds/counts derived from data seen now are labelled "데이터 뒤". No verdict words. Signal greens GREEN-only. Evidence by name + sha; no path strings in anything meant for config/evidence. Urban roads = codex partition (D-K9-104); FW_E is the main improvement target, FW_W monitored only.
- Append dated KST entries to ${G}/LOG_GENERAL.md (create).
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha efc3a722…): D-K9-107 — user: "not just that intersection and ramp: capacity constraints for ALL intersections and ramps"; trigger "when the approach link capacity is exceeded"; G2 (codex half-space, r = 2 s), G4 (meter M4 form), G5 (no plant fix C in C1), G6–G12 recommended accepted (see ${G}/GUARD_DESIGN_DRAFT.md r2 §6 for their exact text; G1/G3 are superseded by the general guard). My interpretation to verify/present: capacity = storage capacity (vehicles that fit = lane length ÷ jam spacing) counted per lane (lane group), because VISSIM spillback starts when one lane fills (129 lane 1 ≈ 10 veh vs whole reservoir in_SC1001_W 1,237.8 veh); "exceeded" = occupancy ≥ 1.0. Present alternatives (link-level, θ = 0.9 codex) with data, but recommend per the user's words unless data show it is ineffective (then say so plainly and offer the nearest option).
- Prior design: ${G}/GUARD_DESIGN_DRAFT.md r2 (553227cd…), ${G}/REVIEW_GUARD.md (d6c9eccd…), ${G}/FACTS_CODE.md (212af2ed…; codex USG CX urban_storage_guard.py: configure :13-99 (source = signal-head lanes, occupancy = vehicles from link start to head ÷ (length ÷ 6 m), receivers = downstream connector landing lanes), occupancy :51-56, half-space constrain :102-145 (per signal, w·z ≥ min(2 s, 0.5 × LP max)), operating_seed :148-166, called at CX SD:438-439/853-855, RS:252-254; our insertion points PT SD:400, SD:766-773, SD:807, C1P:263-286; M4 meter storage guard 0.9 already in C1 for meters), ${G}/FACTS_DATA.md (17dd03bc…; chain onset/order for 127→129/10491→26), amendment C1 ${K8}/K8_PREDECLARATION_AMENDMENT_C1.md (a98580dd…), probe tree ${'D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_5cdc6eb1'} (patch 5cdc6eb1…).
- Network/runs: v3c3 network sha 3de889f0… (.inpx in NC3 run folders), controlled signals and meters per our config (GWT8 diagnostics/sdmpc_n31_20260924/config_n31_v2.json at c20aff1d), NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run, V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}, B D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43} (decision JSON contain codex USG metadata), VSL-only D:/VISSIM_runs/20261027_vsl_v3c3/s{31,41,43}.
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

phase('Inventory')
const inv = await agent(`${RULES}\n${CTX}\nTASK (Inventory): build ${GG}/INVENTORY.md + inventory.json (sha): (1) every controlled signal (SC id) and every approach lane group with a signal head (link, lanes, head position, segment start..head, length, storage capacity per lane = length ÷ jam spacing; derive jam spacing from VISSIM standstill spacing in existing FZP (vehicle length + gap) and compare with codex's 6 m; give both), its serving phase(s) in our controller's phase model, and its receivers (downstream landing lanes); (2) every headless feeder link/lane segment that can spill into a controlled approach or the freeway (e.g. 10491 → 129 lane 1 → 127 → SC1001; 10638 → 70 → SC1004; off-ramp landings; shared links 124·121; urban midblocks) with the server that discharges it (phase or meter) — use topology/routes, not guesses; (3) every meter ramp (8 meters) storage (connector + approach) and current M4 definition; (4) what of this is observable at decision time from the full vehicle record (the controller's observation) and what is already computed by codex USG configure. Return pass=true with sha.`, { label: 'inventory', phase: 'Inventory', schema: SCHEMA })
if (!inv || !inv.pass) return { stoppedAt: 'Inventory', inv }

phase('Data')
const data = await agent(`${RULES}\n${CTX}\nInventory: ${JSON.stringify(inv).slice(0, 4000)}\nTASK (Data, existing runs; new scans only under the lock): for NC3, V-A, B, VSL-only × v3c3-s31/s41/s43, per inventory element, time series (decision-time snapshots every 150 s and 300 s bins, 900–9,000 s) of lane-level occupancy; count exceedances (≥ 1.0 and ≥ 0.9, lane-level and link-level); detect actual spillback events (queue tail reaching the upstream end / blocking an upstream intersection or freeway lane) and compare their timing with the first exceedance (lead/lag, misses, false triggers); in particular for the 127/129/10491/26 chain and for FW_E ramps (10484·10490·10639·10681 approaches). Also extract from B decision JSON when codex USG fired (signal, phase, score) and whether that matched exceedance. Report per element and per arm; flag which elements would trigger in V-A (would change V-A-like operation). Write ${GG}/DATA.md + data.json (sha). Thresholds/counts labelled 데이터 뒤. Return pass=true with sha.`, { label: 'data', phase: 'Data', schema: SCHEMA })
if (!data || !data.pass) return { stoppedAt: 'Data', inv, data }

phase('Draft')
const draft = await agent(`${RULES}\n${CTX}\nInventory: ${JSON.stringify(inv).slice(0, 3000)}\nData: ${JSON.stringify(data).slice(0, 4000)}\nTASK (Draft): write ${GG}/GENERAL_GUARD_DESIGN.md (r0) for supplement C1-2 (replacing the narrow A+B of GUARD_DESIGN_DRAFT r2 §2): §0 plain Korean summary (what the guard does at every intersection and ramp, when it fires, what it changes, what it cannot do); §1 facts; §2 the general guard: (a) source rule per approach lane group: occupancy ≥ θ → serving phase half-space +r (codex USG form, r = 2 s per G2), (b) receiver rule: all receivers ≥ θ → do not push (codex form), (c) headless feeders mapped to their server, (d) meters: M4 form with θ per the same capacity rule (state the change vs M4 0.9 if θ differs), (e) θ = 1.0 lane-level per the user, with link-level and 0.9 alternatives and their data (lead/lag, misses, false triggers, V-A firing count), (f) conflicts between guards at one signal (several approaches demanding green) and how the half-space rows combine (feasibility guaranteed? if not, priority rule), (g) observability, key name under c1_port (exact key set, key-off byte identity), insertion file:line, edit-site list E additions, (h) interaction with Ω701, meter bundle M1–M5, RV-1/RV-2, D98, SG2 stop rule, FW_E priority; §3 changes to amendment C1 (arms, P0, probe r2 with guard states S_G drawn from where the guard fires, gates G-K, stop rules, commit C1-G, cost); §4 user decisions (numbered GG1…, recommended marked; include anything the user's words leave open, e.g. lane vs link level, θ for meters, scope of feeders, priority rule). Carry over D98, thread erratum, urban-road definition, and G6–G12 from r2 unchanged unless the general guard requires a change (then say so). Return pass=true with sha.`, { label: 'draft', phase: 'Draft', schema: SCHEMA })

phase('Review')
const rev = await agent(`${RULES}\n${CTX}\nDraft: ${JSON.stringify(draft || {}).slice(0, 3000)}\nTASK (Review): adversarially review ${GG}/GENERAL_GUARD_DESIGN.md: verify every inventory element, capacity, mapping and number against network/data; check the guard cannot make the LP infeasible or deadlock a signal (all phases demanding green), cannot trigger in V-A-like operation more than reported, does not silently change key-off behaviour, uses only observable inputs, and that the user's rule (capacity exceeded) is implemented literally or any deviation is explicit; look for definitions true/false by construction. Apply fixes as r1 (keep r0), write ${GG}/REVIEW_GENERAL.md. Return status (PARTIAL if user decisions remain), Korean summary for the user (≤ 30 lines: what the general guard is in plain words, what data says about θ = 1.0 lane-level, the decisions GG1… with recommended answers), artifacts with sha256, open.`, { label: 'review', phase: 'Review', schema: SCHEMA })
return { inv, data, draft, rev }
