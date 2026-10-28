export const meta = {
  name: 'codex-c-prep-offline',
  description: 'After B (no VISSIM): readback meter execution check (new declaration), offline decomposition of the input-1099 waiting increase, offline VSL analysis (plant vs VISSIM response), and a C-bundle-1 design draft (objective boundary + meter decision bundle) with user decisions; synthesis, adversarial verify, finalize',
  phases: [
    { title: 'Work', detail: 'readback check, 1099 decomposition, VSL offline' },
    { title: 'Design', detail: 'C bundle-1 design draft' },
    { title: 'Synthesize', detail: 'results + decisions' },
    { title: 'Verify', detail: 'adversarial check' },
    { title: 'Finalize', detail: 'corrections + user summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const CH = K8 + '/codex_handoff'
const CC = K8 + '/c_port'
const TK = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff'
const BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths.
- NO VISSIM, no COM, no closed-loop runners, no freezes, no commits, no push, no changes to GWT8 (${GWT8}) or branches; read-only toward run folders (${BR}, V-A, NC3, J1, A1 D:/VISSIM_runs/20261025_codex_a1_s29, codex raw D:/VISSIM_handoff/20261024), frozen trees and Y:. Offline decision/plant replays only where the task says, in scratch trees under ${TK}/, one heavy job at a time, detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, env_hsw. Kill only own PIDs; other sessions' VISSIM/python (codex work) may be running — never touch them.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Sealed: never open sealed/ or data of seeds 37/59/61/67; never quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Each new analysis that is defined after B data was seen must say so ('데이터 뒤 선언'); write its rule and pin tools (sha in ${CC}/LOG.md) before running it. Existing pinned rules (COMPARE_RULE_B, PINS_B) are not changed.
- No verdict words; Ω always with ④ and Ω-outside; ④b first-observation difference main; seed counts explicit; 64cf numbers labelled 'different network, one seed'.
- Stop if C: or D: < 8 GB free. Append dated (KST) entries to ${CC}/LOG.md (create folder).
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha c6c720eb…): D-K9-91 path C = port codex mechanisms bundle by bundle into our line (no wholesale replacement); first-bundle candidates: objective boundary (Ω701 approaches) + meter decision bundle (neighbor audit, leader cap 3, green-0 ban, storage guard, head service table); confirm after the readback check and the 1099 decomposition; K9-3 (D1/D2) stays on hold. D-K9-92 VSL offline first: A1's 8 VSL-100 decisions + codex T=1,800 decision JSON (+ 64cf-s29 window/off/VSL-only arms) → plant vs VISSIM VSL response. D-K9-93: X6 cell-wise (only the meter-execution cell 'not computed'), † numbers as they are, readback meter check as a new declaration, 1099 waiting offline decomposition (link 26 position/lane/time, link 120, meters 10480/10482, end weaving 10479/10491), no same-seed repeats.
- B results: ${CH}/B_RESULTS.md r2 (152a2f6f…), ${CH}/b/B_REPORT.md r2, ${CH}/b/B_RUNS.md r2, ${CH}/VERIFY_B.md (f2851f8b…; readback 810/810 cycles matched commands outside the declaration; link 26 increase lane 1, 0–3,750 m, 2,700–4,500 s; link 120 B−NC3 −10.2/−10.4/−1.5). B runs ${BR}/s{31,41,43} (codex controller on v3c3, FRZ_B1). V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}; NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run.
- Mechanism references: ${CH}/R_MECH.md (codex vs ours lever table with file:line), ${CH}/TAKEOVER_PLAN.md r2 §1.3 (C bundles), ${CH}/b0/B0.md r2 (port edits), ${K8}/rmcause/METER_CAUSE.md r2, ${K8}/rmcause/r2c_n/METER_NEXT2.md r2 (D1–D5 defects, change order), ${K8}/rmcause/r2c_n/K9_3_DESIGN_DRAFT.md r2 (design style), ${K8}/k92/bundle1/K9_2_DESIGN.md (design style), ${CH}/RAW_CHECK.md (VSL gradients all secant, 2,410/2,688 negative), ${CH}/a1/A1_RESULT.md r2 (A1 VSL 100 in 8 decisions), ${CH}/W264_READ* in ${K8}/rmcause/o1o4/ (VSL window arm).
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
  { key: 'readback', file: 'READBACK_METER.md', t: `Readback meter execution check (D-K9-93 ③, new declaration after data): declare the rule (signal_readback.csv per decision folder: per meter, per 10 s cycle, read green seconds vs commanded green; also commanded rate vs realised discharge from FZP where the meter connector can be counted), pin tools, run for B s31/s41/s43 (and V-A for contrast), report match rates, mismatches and the discharge-per-green comparison (veh/h per lane per green vs model table). Limit: readback is signal-group state level.` },
  { key: 'w1099', file: 'INPUT1099.md', t: `Input-1099 waiting decomposition (D-K9-93 ④, new declaration after data): for B, NC3, V-A per seed, from FZP: link 26 occupancy/speed by position (100 m bins), lane and 300 s time bins; queue spillback to the entrance (insertion blocking times and counts); link 120 and downstream FW_W mainline; FW_W meters 10480 and 10482 green/rate and their queues; end weaving section 10479 / off-ramp 10491 flows and lane-1 occupancy; relate to the timing of meter commands (e.g. 10480 at g2–4) and to SC1001/urban states if relevant. Identify which mechanism the data supports (e.g. FW_W meter holding traffic on the on-ramp that spills into weaving lane 1 → link 26 blockage → 1099 insertion stops), with numbers, and which alternatives are refuted. No replays needed.` },
  { key: 'vsl', file: 'VSL_OFFLINE.md', t: `VSL offline (D-K9-92): (1) from A1's 8 VSL-100 decisions and codex joint/window decisions around T=1,800 (and the 4,500 s price-step case): what the plant predicted for 110 vs 100 (gradients, secant probe values, price terms) and why it chose/didn't choose; (2) what VISSIM showed: compare 64cf-s29 arms (VSL-only vs NC, window vs off, joint vs off) for FW_E bottleneck speeds/flows/spillback around VSL zones (cells/links, time windows) — label one seed, different network; (3) if needed, run offline plant rollouts (no VISSIM) for 2–4 recorded states with VSL 110 vs 100 vs 90 to read the plant's response by cell, and compare with the VISSIM direction; (4) conclude what plant parts (VSL compliance model, FD branch, capacity drop, merge terms, sign cell mapping 16 vs 18 on v3c3) would have to change for the model to see a VSL gain where VISSIM shows one, and what minimal next experiment is (offline first; any VISSIM run listed separately with hours).` },
]

phase('Work')
const works = await parallel(JOBS.map(j => () => agent(`${RULES}\n${CTX}\nTASK (${j.key}): ${j.t}\nWrite ${CC}/${j.file}. Return status PASS when complete (unknowns with reasons), a Korean summary (<= 25 lines) with key numbers, artifacts with sha256, open questions.`, { label: 'work-' + j.key, phase: 'Work', schema: SCHEMA })))
const out = { works: JOBS.map((j, i) => ({ key: j.key, r: works[i] })) }

phase('Design')
out.design = await agent(`${RULES}\n${CTX}\nTASK (C bundle-1 design draft): using READBACK_METER.md, INPUT1099.md, VSL_OFFLINE.md (summaries: ${JSON.stringify(out.works.map(v => ({ k: v.key, s: v.r && v.r.summary }))).slice(0, 8000)}) and R_MECH/B0 references, write ${CC}/C1_DESIGN_DRAFT.md in the K9-2/K9-3 design style: scope of bundle 1 (objective boundary Ω701 approaches; meter decision bundle — neighbor audit, cap 3, green-0 ban, storage guard, head service table — and whether an FW_W-entrance/weaving guard is needed given the 1099 findings), what is ported from codex code (file:line both sides), what is NOT ported (64cf-derived coefficients, calibrated_aggregate, VSL parts), config keys (no path strings; name + sha), interaction with our K8/K9-2 fixes and with the deferred K9-3 D1/D2, expected model effects, gates to predeclare (key-off identity, record-vs-replay with declared differences, offline replay comparisons, decision-time budget, fidelity), how it would be judged in closed loop vs NC3 and V-A (Ω with ④ and Ω-outside, input 1099 line), risks, cost, and a numbered ⟨Q⟩ decision table with a recommended option each. No code changes. Return pass=true with sha256.`, { label: 'design', phase: 'Design', schema: SCHEMA })

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${CC}/READBACK_METER.md, INPUT1099.md, VSL_OFFLINE.md, C1_DESIGN_DRAFT.md. Write ${CC}/C_PREP_RESULTS.md in Korean: (0) plain answer first (<= 12 lines): did meters execute as commanded and with what discharge; what drives the 1099 waiting increase under B; why the model avoids VSL and what VISSIM says; the proposed C bundle 1 and why; (1) key tables; (2) the decision list (from the design draft plus anything new) with recommended options. No verdict words. Return pass=true with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${CC}/C_PREP_RESULTS.md, the three work reports and C1_DESIGN_DRAFT.md with fresh scripts (no reuse of the authors' scripts): recount the readback match for one seed, the link-26/1099 mechanism numbers for two seeds, the VSL gradient/price claims from decision JSON, and the design draft's file:line references and porting scope against code; try to refute the mechanism claims and the recommendations. Write ${CC}/VERIFY_C_PREP.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${CC}/VERIFY_C_PREP.md to C_PREP_RESULTS.md and the sub-reports/design draft (keep _r1 copies, change logs; never keep a refuted claim). Copy finals to ${REP}/. Return status, a Korean summary (<= 25 lines) for the user (readback result, 1099 mechanism, VSL offline answer, C bundle-1 proposal, the decision list with recommended options), artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
