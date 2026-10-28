export const meta = {
  name: 'c1-port-bundle1',
  description: 'C1 (codex mechanism port, bundle 1: Ω701 + meter decision bundle) per C1_DESIGN_DRAFT r2 and D-K9-94: amendment C1 + review, P0 + mini probe, new branch commits with per-commit gates, independent verify, gates (G-RR, R, J, F, wall) with verify, offline replays (T=900 five states + 900–2,700 s chain, SG2 stop rule) with verify; stop before closed loop and push',
  phases: [
    { title: 'DeclareC1', detail: 'amendment C1 from design r2 + D-K9-94' },
    { title: 'ReviewC1', detail: 'adversarial review, fixation' },
    { title: 'P0Probe', detail: 'P0 reads/checks + mini probe' },
    { title: 'Implement', detail: 'branch claude/c1-port-20261027, commits, per-commit gates' },
    { title: 'VerifyImpl', detail: 'independent review (+1 fix round)' },
    { title: 'Gates', detail: 'G-RR, R, J, F, wall' },
    { title: 'VerifyGates', detail: 'independent recomputation' },
    { title: 'Replay', detail: 'T=900 x5 + 900–2,700 s chain + verify' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const CC = K8 + '/c_port'
const C1 = CC + '/c1'
const G = C1 + '/guard'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
const TK = 'D:/VISSIM-merge/k8_gate_trees/c1'
const HL = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- Commits only in GWT8 = ${GWT8} on a NEW branch claude/c1-port-20261027 created from c20aff1d (claude/k92-b1-20261016 stays at c20aff1d; K8 branch at b9734abe). Stage explicit paths only (never add -A/./-u, never --renormalize, never amend/rebase/force). Author/committer Ming2you <alsrjsrb1915@snu.ac.kr> (git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr); message ends with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". core.autocrlf=true: compare with git hash-object --no-filters, keep line endings, confirm ls-tree blob == working bytes. NO PUSH.
- No VISSIM, no COM, no closed-loop runners, no freezes of D:/VISSIM-merge/frozen/*. Offline decision/plant replays and FZP reads of EXISTING runs only, in scratch trees under ${TK}/, heavy jobs one at a time and under the shared lock ${HL} (create exclusively; wait/retry; delete when done — the VSL workflow uses it too), detached via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, env_hsw where codex code runs; poll ≤ 9 min. Kill only own PIDs (other sessions' VISSIM/python — codex work, the VSL workflow's three VISSIM runs — never touched).
- Read-only: frozen trees, all run folders, the codex handoff copy D:/VISSIM_handoff/20261024, codex trees under D:/VISSIM-merge/k8_gate_trees/codexhandoff/, Y:.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Other tests only if new or declared.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix. Blind sample for F: R-obs v3c3-s47 (report only per D-K9-94).
- Predeclaration discipline: amendment C1 text, gate definitions, thresholds and judge tools are fixed (sha) before the data they judge; never change after data; any FAIL/INCOMPLETE/HOLD ⇒ STOP (user decides). No verdict words. Ω always with ④ and Ω-outside; ④b first-observation difference main.
- LESSONS (apply from the start): no path strings in tuning/evidence (name + sha); long lists via files; PID-unique temp names; judges never read seed tokens from folder names; metadata markers of new keys need declared differences in record-vs-replay gates; make_config --check before promotion; wall-clock judged on median only; tests judged per test vs base; chained replays: previous-action paths/receipts in outputs → closed leaf list, report-only; path normalisation must cover new tree roots; NC3 signal green seconds in .lsa-derived files may include amber — compare GREEN-only; replaying recorded states with a new policy token stops at load_prices (use T=900 single decisions or chains); codex head table g9=g10 conflicts with our K3 normalisation (decided: drop g9, keep g10).
- Stop if C: or D: < 8 GB free. RESUME partial outputs; never duplicate commits. Append dated (KST) entries to ${C1}/LOG.md (create).
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha bbfe77b0…): D-K9-91 path C; D-K9-94 C1 design Q1–Q26 all recommended (see ${CC}/C1_DESIGN_DRAFT.md r2 §12 decision table and ${CC}/C_PREP_RESULTS.md r2 §2): one bundle = Ω701 (66 links: 35 roads + 31 direct connectors) + meter decision bundle (neighbor audit + combination, leader cap 3, green-0 ban, storage guard 0.9 + operating seed + held keep, FW_E 4-meter head table with g9 dropped and g10 kept); NOT ported: VSL parts, 64cf-derived coefficients, calibrated_aggregate, urban bundle C5, speed caches, link-124 shared lane; no FW_W entrance guard — instead chained-replay SG2 (SC1001 EBT) plan green compared with key-off, STOP if shorter by > 100 s (GREEN-only), and a chain line in tables; evidence by name + sha; runtime allows keys alone, deployment together; J and F report-only; offline replays T=900 five states + 900–2,700 s chain; closed loop 3 seeds concurrent asked again before launch; thresholds fixed now; K9-3 on hold; reads: B storage guard at 10639, reason for B SG2 shortening (decision JSON, GREEN-only), plant chain representation, head-curve provenance; 3,625.8 m correction memo; entrance throughput deferred to a network bundle.
- Design and evidence: ${CC}/C1_DESIGN_DRAFT.md r2 (c32e1006…; file:line insertion points at c20aff1d, codex file:line, config keys section c1_port, gates G-K0..G-K5a/b, G-RR, R, J, F, stop rules S-C1-*, cost), ${CC}/C_PREP_RESULTS.md r2 (4b58fb4e…), ${CC}/READBACK_METER.md, ${CC}/INPUT1099.md r2, ${CC}/VERIFY_C_PREP.md (open items: physical_projection_support pack carries old membership 4863f5ee…; storage-guard neighbor candidate count; adapter keys differ in five incl. joint_owner_game.max_leader_candidates), ${K8}/codex_handoff/R_MECH.md, ${K8}/codex_handoff/b0/B0.md r2, codex handoff worktree D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff and B trees (FRZ_B1 D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410), our runs V-A D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}, B D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43}, NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run.
- Precedent for form: K9-2 bundle 1 (${K8}/k92/bundle1/, amendments 24–33) and the K9-3 workflow plan; V-A freeze/launch pattern ${K8}/k92/va/.
- Report copies: ${REP}.
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
phase('DeclareC1')
out.decl = await agent(`${RULES}\n${CTX}\nTASK (Declare amendment C1): write ${K8}/K8_PREDECLARATION_AMENDMENT_C1.md from C1_DESIGN_DRAFT r2 with every ⟨Q⟩ filled per D-K9-94: exact keys and values (repr fixed), codex source file:line and our insertion file:line, provenance by name + sha, assertions, unchanged list (G-K1 static), commit plan, P0 steps (incl. the open items: membership pack 4863f5ee vs Ω635 — declare expected difference or STOP rule; storage-guard neighbor candidate count; which keys change the policy token), mini probe (scratch arms, report only), gates G-K0..G-K5a/b with the four-outcome rule and declared difference sets, G-RR, R, J (report-only), F (report-only, R-obs v3c3-s47), offline replays (T=900 five states + 900–2,700 s chain; SG2 GREEN-only stop rule at 100 s; chained decisions report-only with a closed leaf list), stop rule S-C1-7 (no tightening ever chosen in probe and chain ⇒ STOP before closed loop), regression numbers, pins, cost. Apply the LESSONS explicitly. No TBD. Return pass=true with sha256.`, { label: 'declare-c1', phase: 'DeclareC1', schema: SCHEMA })
if (!out.decl || !out.decl.pass) return { stoppedAt: 'DeclareC1', out }

phase('ReviewC1')
out.rev = await agent(`${RULES}\n${CTX}\nTASK (Review amendment C1): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_C1.md: hunt for definitions that FAIL/HOLD by construction (K9-2 lessons list), check every code reference on both sides, values and provenance, the Ω701 membership/plant consistency, the g9 drop rule vs K3 normalisation, token-changing keys and replay feasibility, SG2 stop-rule definition (GREEN-only), S-C1-7, pins and STOP rules. Apply corrections (keep _r1), then write ${C1}/AMENDMENT_C1_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-c1', phase: 'ReviewC1', schema: SCHEMA })
if (!out.rev || !out.rev.pass) return { stoppedAt: 'ReviewC1', out }

phase('P0Probe')
out.p0 = await agent(`${RULES}\n${CTX}\nRESUME NOTE (user decisions D-K9-96·97, notes sha cb84bf22…): a previous P0 attempt STOPPED at P0-4 INCOMPLETE because my pinned P0 tool c1_p0.py:588-589 decoded git grep output with cp949 (see ${C1}/P0_PROBE.md 5755da89… and ${C1}/LOG.md). User chose: (D-K9-96) add encoding='utf-8', errors='replace' to ONLY the three git grep subprocess calls in c1_p0.py (no counting line changes; show the diff in LOG), re-pin as PINS_P0_r2.sha256 (only that file's sha changes; record before any new computation), KEEP P0-1/P0-2 PASS results (do not rerun them), resume from P0-4, then the remaining P0 steps (P0-3·5·6·7·8·9·10·11·13, C1_VALUES.json fixation) and the mini probe (pin c1_probe.py before its data). Probe stop 4 (C1 decision wall median > 1,500 s) stays as fixed. (D-K9-97) RV-1 and RV-2 from the review are accepted. Keep existing trees/outputs (p0_5cdc6eb1, probe_5cdc6eb1); write P0_PROBE r2 (keep r1).\nTASK (P0 + mini probe per amendment C1): verify the fixation; run P0 (reads and checks declared there: membership pack, storage-guard candidate count, token-changing keys, B storage guard at 10639, B SG2 shortening reason from B decision JSON GREEN-only, plant chain representation, head-curve provenance) and the mini probe on scratch arms under ${TK}/ (report only; apply declared stop rules). Write ${C1}/P0_PROBE.md (+ copy to ${REP}). Return pass=true only if every P0 check passes and no stop rule fired.`, { label: 'p0-probe', phase: 'P0Probe', schema: SCHEMA })
if (!out.p0) return { stoppedAt: 'P0Probe', out }

const C12 = `SUPPLEMENT C1-2 CONTEXT (user decisions D-K9-98..114; notes ${K8}/K9_1_J1_NOTES_20261013.md sha bfd3fc2b...): the first probe stopped at stop rule 2 (Omega-arm plant trajectory != OFF, explained by the 29-connector link_to_storage channel; ${C1}/P0_PROBE.md r2 e467583f..., ${C1}/C1_PROBE_RESULTS.md/.json). Supplement C1-2 must carry, fixed before any new data: (1) D98 Omega701 explained-difference condition and the revised 'trajectory same' definitions (T2, C0E, C3' vs C0; D98-4' stop), per ${G}/GUARD_DESIGN_DRAFT.md r2 section 3 as carried into ${G}/general/GENERAL_GUARD_DESIGN.md r1 (cffbef23...) with the D98-5 wording fix; (2) thread erratum D-K9-99 (NUMBA_NUM_THREADS removed, K9-2 form); (3) reporting: Omega701 is the main objective/report area, urban roads = codex partition only (D-K9-104); (4) the GENERAL storage-capacity guard per GENERAL_GUARD_DESIGN r1 and D-K9-114: trigger U = lane-level (vehicles >= length/6 m) OR observed spillback (queue tail at the lane upstream end), all 17 controlled signals' head lanes, feeder chains (416 segments, cell-graph attribution), off-ramp landings as sources, short segments excluded as sources and short receivers counted by vehicles only, codex half-space form r = 2 s with max-overlap weights and no FW_E extra weight, meters = existing M4 0.9 plus a floor raise only when the queue overflows into the meter approach link (must not loosen FW_E meter tightening), offline segment evidence files, same-time frames, arm C1G = C1 + guard keys, probe r2 guard states by categories K0-K6 (<= 14), R-b for C1G only, new commit C1-G, plus GG decisions as in r1 section decision table; also G6-G12 of the narrow design as modified there; RV-1/RV-2 (D-K9-97) stay; (5) FW_E reference line (D-K9-110): ${K8}/fwe_decomp/FWE_DECOMP.md r2 (7f58ab3e...) section 3.3 text + FWE_REF_C1 + fwe_synth.py sha as pre-data report-only fields, DA1-DA4 (DA1 cell assignment = 100 m bin centre; DA4 tool vf_extra2.py 3777458d...), FW_E text leads with C1 - V-A and C1 - B, then C1 - NC3; v3c3 pair noise unknown with the 64cf A1 - joint yardstick beside (D-K9-111); (6) VSL report line Q-V6 (D-K9-103): in C1 - B rows for (1) FW_E and input 1098, note the VSL policy difference (V-A-form 101 vs B 110) with each arm's count/times of VSL < 110 decisions, and the VSL-only 1099 4b swing (-57.8..+145.9) as a reference size; (7) everything else in amendment C1 (a98580dd...) unchanged unless a change is listed here. Probe r2 restarts from scratch with new patch/tools/pins (old HALT bundle kept as record).`

phase('DeclareC1')
out.decl12 = await agent(`${RULES}\n${CTX}\n${C12}\nTASK (Declare supplement C1-2): write ${K8}/K8_PREDECLARATION_AMENDMENT_C1_2.md (no TBD): every change to amendment C1 with exact text, keys/values (c1_port guard key set, repr fixed), insertion file:line at c20aff1d + probe patch, edit-site list additions, P0 additions (P0-14..P0-18 incl. segment evidence builder and runtime count reproduction), probe r2 arms/states/stop rules (incl. guard states K0-K6, stop 5-8), gate changes (G-K1/2/3/4/5b/RR/B), stop rules S-C1-18..21+, commit plan (C1-G), report fields (Omega701/urban codex partition/FW_E reference line/DA1-DA4/VSL line), regression numbers, cost. Apply the LESSONS. Return pass=true with sha256.`, { label: 'declare-c1-2', phase: 'DeclareC1', schema: SCHEMA })
if (!out.decl12 || !out.decl12.pass) return { stoppedAt: 'DeclareC1-2', out }
phase('ReviewC1')
out.rev12 = await agent(`${RULES}\n${CTX}\n${C12}\nTASK (Review supplement C1-2): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_C1_2.md against amendment C1, GENERAL_GUARD_DESIGN r1, FWE_DECOMP r2 and the decisions: definitions true/false by construction, guard feasibility and key-off identity, observability, meter rule cannot loosen FW_E tightening, D98 computability, report fields exact, pins. Apply corrections (keep _r1), write ${C1}/AMENDMENT_C1_2_FIXED.md with final sha/time. Return pass=true only if no unresolved issue.`, { label: 'review-c1-2', phase: 'ReviewC1', schema: SCHEMA })
if (!out.rev12 || !out.rev12.pass) return { stoppedAt: 'ReviewC1-2', out }
phase('P0Probe')
out.p0b = await agent(`${RULES}\n${CTX}\n${C12}\nTASK (P0 additions + probe r2 per amendment C1 + fixed supplement C1-2): verify both fixations; run the added P0 steps (P0-14..18 as declared); build the new probe patch/tools, pin them before data, and run probe r2 from scratch on new output roots (old HALT bundle kept), applying all stop rules (incl. stop 3 'no tightening chosen', stop 4 wall median > 1,500 s, guard stops). Write ${C1}/P0_PROBE_R2.md (+ copy to ${REP}). Return pass=true only if every P0 check passes and no stop rule fired.`, { label: 'p0-probe-r2', phase: 'P0Probe', schema: SCHEMA })
if (!out.p0b || !out.p0b.pass) return { stoppedAt: 'P0Probe-r2', out }

phase('Implement')
out.impl = await agent(`${RULES}\n${CTX}\n${C12}
TASK (Implement per amendment C1 + fixed supplement C1-2): create branch claude/c1-port-20261027 from c20aff1d in GWT8 and make the declared commits with the per-commit gates G-K0..G-K5 exactly as declared (judge tools pinned before data, heavy jobs under the shared lock). Write ${C1}/IMPLEMENT.md (commit shas, gate tables, sha256). Return pass=true only if all commits exist, all per-commit gates PASS, status clean, nothing pushed.`, { label: 'implement', phase: 'Implement', schema: SCHEMA })
if (!out.impl || !out.impl.pass) return { stoppedAt: 'Implement', out }

phase('VerifyImpl')
const vi = (r) => `${RULES}\n${CTX}\n${C12}
TASK (VerifyImpl r${r}): independently verify the C1 implementation against amendment C1 + supplement C1-2: diff c20aff1d..HEAD only in declared paths; key-off byte identity; key-on effects exactly as declared (Ω701 membership, neighbor audit, cap 3, green-0 ban, storage guard, head table without g9); assertions; evidence name+sha; no path strings; gate verdicts recomputed with your own pinned code; tests per test vs base; commit hygiene; nothing pushed. Implement report: ${JSON.stringify(out.impl || {}).slice(0, 3000)}. Write ${C1}/VERIFY_IMPL_r${r}.md. Return pass=true only if no defect; list each defect with the fix.`
out.vi1 = await agent(vi(1), { label: 'verify-impl-1', phase: 'VerifyImpl', schema: SCHEMA })
if (!out.vi1 || !out.vi1.pass) {
  out.fix = await agent(`${RULES}\n${CTX}\n${C12}
TASK (FixImpl): fix every real defect with NEW commits (no amend), re-run affected per-commit gates as declared; if a fix would change anything amendment C1 fixed, STOP instead. Verifier report: ${JSON.stringify(out.vi1 || {}).slice(0, 5000)}. Return pass=true only if all real defects are fixed and status is clean.`, { label: 'fix-impl', phase: 'VerifyImpl', schema: SCHEMA })
  if (!out.fix || !out.fix.pass) return { stoppedAt: 'FixImpl', out }
  out.vi2 = await agent(vi(2), { label: 'verify-impl-2', phase: 'VerifyImpl', schema: SCHEMA })
  if (!out.vi2 || !out.vi2.pass) return { stoppedAt: 'VerifyImpl', out }
}

phase('Gates')
out.gates = await agent(`${RULES}\n${CTX}\n${C12}
TASK (Gates per amendment C1 + supplement C1-2): run G-RR, R (report), J (report-only), F (report-only, R-obs v3c3-s47) and the wall-clock gates on the branch head, judge tools pinned before data, heavy jobs under the shared lock. Write ${C1}/GATES_C1.md (+ copy to ${REP}). Return pass=true only if every judged gate passes and nothing is INCOMPLETE/HOLD; otherwise STOP precisely.`, { label: 'gates', phase: 'Gates', schema: SCHEMA })
phase('VerifyGates')
out.vg = await agent(`${RULES}\n${CTX}\n${C12}
TASK (VerifyGates): pin your own tools before reading gate outputs; recompute every verdict in ${C1}/GATES_C1.md from raw outputs; re-run 2 representative jobs and confirm bit-identity; confirm thresholds equal amendment C1. Gate report: ${JSON.stringify(out.gates || {}).slice(0, 3000)}. Write ${C1}/VERIFY_GATES_C1.md. Return pass=true only if all judged gates pass and agree; if the gate stage said STOP, confirm or refute (pass=false either way).`, { label: 'verify-gates', phase: 'VerifyGates', schema: SCHEMA })
if (!out.gates || !out.gates.pass || !out.vg || !out.vg.pass) return { stoppedAt: 'Gates', out }

phase('Replay')
out.replay = await agent(`${RULES}\n${CTX}\n${C12}
TASK (Offline replays per amendment C1 + supplement C1-2, arms C1 and C1G as declared): run the declared T=900 single decisions (five states) and the 900–2,700 s chains (C1 arm vs key-off), compute the declared checks and metrics: meter commands (does any tightening get chosen — S-C1-7), SC1001 SG2 plan green vs key-off (GREEN-only; STOP if shorter by > 100 s), Ω701/Ω635 model costs with ④-type and Ω-outside model terms, ramp forecasts, decision times (G-K5b 1,500 s), chained decisions report-only with the closed leaf list. Write ${C1}/C1_REPLAY_REPORT.md (+ copy to ${REP}). No verdict words. Return status (PASS only if every integrity check holds and no stop rule fired), Korean summary (<= 25 lines), artifacts with sha256, open.`, { label: 'replay', phase: 'Replay', schema: SCHEMA })
if (!out.replay || !out.replay.pass) return { stoppedAt: 'Replay', out }
out.vreplay = await agent(`${RULES}\n${CTX}\n${C12}
TASK (VerifyReplay): pin your own tools before reading replay outputs; recompute every check/metric in ${C1}/C1_REPLAY_REPORT.md from raw outputs; re-run one decision and confirm bit-identity; check claims follow from numbers; apply corrections (keep _r1). Replay report: ${JSON.stringify(out.replay || {}).slice(0, 3000)}. Write ${C1}/VERIFY_REPLAY_C1.md. Return status, Korean summary (<= 25 lines) suitable for the user, artifacts + sha256, open (incl. the go/no-go question for the C1 closed loop on v3c3 s31/s41/s43 and the push of claude/c1-port-20261027).`, { label: 'verify-replay', phase: 'Replay', schema: SCHEMA })
return { stoppedAt: out.vreplay && out.vreplay.pass ? null : 'VerifyReplay', out }
