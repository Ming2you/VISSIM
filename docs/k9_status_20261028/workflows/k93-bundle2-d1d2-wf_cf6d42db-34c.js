export const meta = {
  name: 'k93-bundle2-d1d2',
  description: 'K9-3 bundle 2 (D1 split row at decision point 1135, D2 SC1004 west-bound boundary capacities): amendment 35 + review, P0 evidence + mini probe, new branch commits with per-commit gates, independent verify, full gates (C, R, J, F, wall-clock) with verify, chained offline replay with verify; stop before closed-loop VISSIM and push',
  phases: [
    { title: 'Declare35', detail: 'amendment 35 from design draft r2 + D-K9-80' },
    { title: 'Review35', detail: 'adversarial review, fixation' },
    { title: 'P0Probe', detail: 'P0 evidence + FZP checks C-1..C-3, mini probe (report only)' },
    { title: 'Implement', detail: 'branch claude/k93-b2-20261024, commits K9-3-*, per-commit gates' },
    { title: 'VerifyImpl', detail: 'independent review (+1 fix round)' },
    { title: 'Gates', detail: 'C, R, J, F, wall-clock' },
    { title: 'VerifyGates', detail: 'independent recomputation' },
    { title: 'Chain', detail: 'chained offline replay + verify' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const KB2 = K8 + '/k93/bundle2'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/k93_b2'
const TK = 'D:/VISSIM-merge/k8_gate_trees/k93b2'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- Commits only in GWT8 = ${GWT8} on a NEW branch claude/k93-b2-20261024 created from c20aff1d (the K9-2 branch claude/k92-b1-20261016 stays at c20aff1d; the K8 branch stays at b9734abe). Stage explicit paths only (never add -A/./-u, never --renormalize, never amend/rebase/force). Author/committer Ming2you <alsrjsrb1915@snu.ac.kr> (git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr); message ends with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". core.autocrlf=true: compare with git hash-object --no-filters, keep line endings, confirm ls-tree blob == working bytes. NO PUSH in this workflow.
- No VISSIM, no COM, no runners, no freezes. Offline decision/plant replays and FZP reads of EXISTING runs only, in scratch trees under ${TK}/, one heavy job at a time, DETACHED via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B; poll ≤ 9 min per wait; FZP scans take the lock ${KB2}/fzp.lock exclusively. Kill only own PIDs (another session's VISSIM/python may be running — never touch it).
- Read-only: frozen trees (D:/VISSIM-merge/frozen/*), all run folders, earlier scratch trees. Snapshot before/after heavy stages.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Other tests only if new or declared.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix. Blind sample for F: R-obs v3c3-s47 (partially exposed — U4 66|p2 contains v3b-s47; disclose); its K9-3 VISSIM-reference values are computed only inside the judging stage, and its job logs go to a sealed root whose NAME does not contain a seed token.
- Predeclaration discipline: amendment 35 text, gate definitions, thresholds and judge tools are fixed (sha) before the data they judge; never change a definition/threshold/judge after seeing its data; any FAIL/INCOMPLETE/HOLD ⇒ STOP and report (the user decides). No verdict words. Ω always with ④ and Ω-outside.
- LESSONS FROM K9-2 (apply from the start): (1) never put path strings in tuning/evidence files — name + sha only (joint_runtime_source_pins follows path strings; D-K9-42); (2) pass long lists to child processes via files, not command lines (32,767 chars; amendment 28); (3) per-process temp names must not rely on PID alone (Windows PID reuse; amendment 33); (4) judges must not read a seed token from a folder name such as a sealed root (amendment 31); (5) new keys that write metadata markers into every decision need a declared difference set in record-vs-replay gates (amendment 34 E_K92); (6) make_config --check for an arm must run on the clean tree before promotion (D-K9-72); (7) wall-clock is judged on the median pair ratio only, IQR reported (amendment 26); (8) test failures are judged per test against the base commit (the 2 ConfigFlagTests failures pre-exist since K8-7; amendment 31 §3); (9) chained replays write previous-action paths/receipt sha into outputs — compare chain decisions with a closed leaf list, report-only (amendment 32, D-K9-62/66); (10) path normalisation must cover the new tree roots (amendment 27/29).
- Stop if C: or D: < 8 GB free. AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs; never duplicate commits. Append dated (KST) entries to ${KB2}/LOG.md (create).
`

const CTX = `
CONTEXT
- User decisions: ${K8}/K9_1_J1_NOTES_20261013.md (sha d0757bb0…): D-K9-77 D1/D2 are bundle-2 defects fixed first; D-K9-80 design decisions ⟨Q1⟩–⟨Q12⟩ all (가) (D1 = v3c3 relFlow row (0.2, 0.6, 0.2) fixed now, FZP only C-1 ±0.03 check; SC1004_W_out row only; S→W = U4 F2 1,807.4 (s_unimpeded 1,919.7 report arm); v3b value fixed, v3c3 NC3 re-measure C-2 ±5 % check; N→W keeps signalised movement with 1,850 labelled 'not measured', C-3 mechanism report; runtime allows each key alone, deployment/closed loop only both (make_config --k93b2); evidence keys name + sha (new loader, code-constant folder); blind = R-obs v3c3-s47 50 states, partial-exposure label with U4 66|p2 v3b-s47 first in the exposure list; J = all K9-1/K9-2 judging leaves, differ ⇒ STOP; F-1..F-3 'not larger than key-off', false ⇒ STOP; after gates chained replay first, then closed loop 3 seeds (closed loop and push need a later user go); thresholds C-1 ±0.03, C-2 ±5 %, probe stop 1.2× fixed now).
- Design draft: ${K8}/rmcause/r2c_n/K9_3_DESIGN_DRAFT.md r2 (549f20e2…; sections §2 D1, §3 D2, §4 relation to the K9-2 W key, §5 expected effects, §6 commit plan and gates incl. P0, mini probe, G-K0..G-K5, C, R, J, F, regression numbers, STOP rules, cost, §8 decision table). Evidence: ${K8}/rmcause/r2c_n/N12_CODE_PLANT.md (206.53 = 330×184/294 chain CFG:7823-7825 → RS:400 → ADP:3832-3836 → ADP:3888-3896 → UFA:589-591 → UQM:742-767), N34_FLOWS.md, METER_NEXT2.md r2, VERIFY_N2.md; O4 ${K8}/rmcause/o1o4/O4_MERGE_10681.md.
- K9-2 precedent (follow its form): ${K8}/k92/bundle1/ (K9_2_DESIGN.md, amendments 24–33 in ${K8}/K8_PREDECLARATION_AMENDMENT_{24..33}.md with fixations, IMPLEMENT.md, GATES_K92B1*.md, VERIFY_*; harness diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_*.py; V-B ${K8}/k92/bundle1/k92_vb/). V-A (K9-2 closed loop) ${K8}/k92/va/ (amendment 34). Current GWT8 head c20aff1d (K9-2-7), config_n31_v2.json = bundle-1 arm (W + H-b, CFG c8e3ee2c…).
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
phase('Declare35')
out.a35 = await agent(`${RULES}\n${CTX}\nTASK (Declare A35): write ${K8}/K8_PREDECLARATION_AMENDMENT_35.md from the design draft r2 with every ⟨Q⟩ filled per D-K9-80: exact key names, values (repr fixed), provenance with sha (no path strings in evidence), installation points (file:line at c20aff1d), assertions, unchanged-list (G-K1 static), commit plan (K9-3-0 harness … K9-3-n arm/docs), P0 steps (C-1/C-2/C-3 with fixed thresholds; values are NOT re-fit from P0), mini probe (scratch arms, report only, stop rule 1.2×), gate definitions G-K0..G-K5 (four-outcome rule, normalisation covering the new tree roots, declared difference sets for any new metadata markers, per-test equality for unit tests), C, R (report), J (all K9-1/K9-2 judging leaves; differ ⇒ STOP), F (blind R-obs v3c3-s47 50 states, F-1..F-3 not larger than key-off, partial exposure list), wall-clock (median only), chained replay method (closed leaf list for chained decisions, report only; hook with PID-unique names if a recorder is needed), regression numbers, STOP rules, pins, cost. Apply the LESSONS list explicitly (one line each, where it applies). No TBD. Return pass=true with sha256.`, { label: 'declare-a35', phase: 'Declare35', schema: SCHEMA })
if (!out.a35 || !out.a35.pass) return { stoppedAt: 'Declare35', out }

phase('Review35')
out.a35rev = await agent(`${RULES}\n${CTX}\nTASK (ReviewDeclare A35): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_35.md: hunt for definitions that FAIL or HOLD by construction (as happened in K9-2: HARD-only judging, path normalisation depth, judge seed parsing from folder names, chained previous-action leaves, metadata markers in record-vs-replay gates, make_config check order, wall-clock IQR, PID temp names, command-line length); check values/provenance against code and data (D1 row from INPX relFlow, D2 values from U4 rows, 206.53 chain lines), unchanged lists, blind-sample exposure, J scope, F thresholds, STOP rules and pins. Apply corrections (keep _r1), then write ${KB2}/AMENDMENT35_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a35', phase: 'Review35', schema: SCHEMA })
if (!out.a35rev || !out.a35rev.pass) return { stoppedAt: 'Review35', out }

phase('P0Probe')
out.p0 = await agent(`${RULES}\n${CTX}\nTASK (P0 + mini probe per amendment 35): verify the fixation sha; run P0 (evidence files name+sha, FZP checks C-1/C-2/C-3 on the declared NC3 runs with the FZP lock, report against the fixed thresholds — values are not re-fit) and the mini probe on scratch arms under ${TK}/ (report only; apply the 1.2× stop rule). Write ${KB2}/P0_PROBE.md (+ copy to ${REP}). Return pass=true only if every P0 check passes and no stop rule fired; otherwise STOP with exact reasons.`, { label: 'p0-probe', phase: 'P0Probe', schema: SCHEMA })
if (!out.p0 || !out.p0.pass) return { stoppedAt: 'P0Probe', out }

phase('Implement')
out.impl = await agent(`${RULES}\n${CTX}\nTASK (Implement per amendment 35): create branch claude/k93-b2-20261024 from c20aff1d in GWT8 and make the declared commits (harness, D1 key, D2 key, arm/docs) with the per-commit gates G-K0..G-K5 exactly as declared, judge tools pinned before data. Heavy gate jobs detached one at a time. Write ${KB2}/IMPLEMENT.md (commit shas, gate tables, paths, sha256). Return pass=true only if all commits exist, all per-commit gates PASS, git status clean, nothing pushed.`, { label: 'implement', phase: 'Implement', schema: SCHEMA })
if (!out.impl || !out.impl.pass) return { stoppedAt: 'Implement', out }

phase('VerifyImpl')
const viPrompt = (r) => `${RULES}\n${CTX}\nTASK (VerifyImpl r${r}): independently and adversarially verify the K9-3 implementation against amendment 35: diff c20aff1d..HEAD only in declared paths; key-off byte identity; key-on effects exactly D1 row and D2 two keys; assertions; evidence name+sha; no path strings; unchanged lists; gate verdicts recomputed from raw outputs with your own code (pin it first); tests (new pass, pre-existing per-test equal to base); commit hygiene; nothing pushed. Implement report: ${JSON.stringify(out.impl || {}).slice(0, 3500)}. Write ${KB2}/VERIFY_IMPL_r${r}.md. Return pass=true only if no defect; list each defect with the fix.`
out.vi1 = await agent(viPrompt(1), { label: 'verify-impl-1', phase: 'VerifyImpl', schema: SCHEMA })
if (!out.vi1 || !out.vi1.pass) {
  out.fix = await agent(`${RULES}\n${CTX}\nTASK (FixImpl): fix every real defect the verifier found with NEW commits (no amend), re-run the affected per-commit gates as declared; if a fix would change anything amendment 35 fixed (definition, threshold, judge after data), STOP and report instead. Verifier report: ${JSON.stringify(out.vi1 || {}).slice(0, 5000)}. Return pass=true only if all real defects are fixed and status is clean.`, { label: 'fix-impl', phase: 'VerifyImpl', schema: SCHEMA })
  if (!out.fix || !out.fix.pass) return { stoppedAt: 'FixImpl', out }
  out.vi2 = await agent(viPrompt(2), { label: 'verify-impl-2', phase: 'VerifyImpl', schema: SCHEMA })
  if (!out.vi2 || !out.vi2.pass) return { stoppedAt: 'VerifyImpl', out }
}

phase('Gates')
out.gates = await agent(`${RULES}\n${CTX}\nTASK (Gates per amendment 35): run C, R (report), J (all K9-1/K9-2 judging leaves), F (blind R-obs v3c3-s47 50 states, sealed handling as declared) and the wall-clock gate on the branch head, judge tools pinned before data, heavy jobs detached one at a time. Write ${KB2}/GATES_K93B2.md (gate | definition | value | threshold | outcome, paths, sha256) + copy to ${REP}. Return pass=true only if every judged gate passes (four-outcome rule) and nothing is INCOMPLETE/HOLD; otherwise STOP precisely.`, { label: 'gates', phase: 'Gates', schema: SCHEMA })
phase('VerifyGates')
out.vg = await agent(`${RULES}\n${CTX}\nTASK (VerifyGates): pin your own recomputation tools before reading gate outputs; recompute every verdict in ${KB2}/GATES_K93B2.md from raw outputs (no import of the gate tools); re-run 2 representative jobs detached and confirm bit-identity; confirm thresholds equal amendment 35; respect sealing (open sealed logs only after J/F values are fixed). Gate report: ${JSON.stringify(out.gates || {}).slice(0, 3500)}. Write ${KB2}/VERIFY_GATES_K93B2.md. Return pass=true only if all gates pass by recomputation and agree; if the gate stage said STOP, confirm or refute it (pass=false either way).`, { label: 'verify-gates', phase: 'VerifyGates', schema: SCHEMA })
if (!out.gates || !out.gates.pass || !out.vg || !out.vg.pass) return { stoppedAt: 'Gates', out }

phase('Chain')
out.chain = await agent(`${RULES}\n${CTX}\nTASK (Chained offline replay per amendment 35): run the declared chains (B2 arm = W + H-b + D1 + D2 vs key-off for D1/D2, chain-first decisions judged, chained decisions report-only with the closed leaf list, recorder hook with PID-unique names if declared), detached one at a time; compute the declared integrity checks and metrics (incl. 10681/10646 model arrivals vs VISSIM, SC1004 west-bound services, meter gradients, FW_E mainline 7 links model-internal, Ω with ④ and Ω-outside). Write ${KB2}/K93_CHAIN_REPORT.md (+ copy to ${REP}). No verdict words. Return status (PASS only if every integrity check holds), Korean summary (<= 25 lines), artifacts with sha256, open.`, { label: 'chain', phase: 'Chain', schema: SCHEMA })
if (!out.chain || !out.chain.pass) return { stoppedAt: 'Chain', out }
out.vchain = await agent(`${RULES}\n${CTX}\nTASK (VerifyChain): pin your own tools before reading chain outputs; recompute every integrity check and metric in ${KB2}/K93_CHAIN_REPORT.md from raw outputs (no import of the driver/recalculator/hook); re-run one 2-decision segment detached and confirm bit-identity; check claims follow from numbers; apply corrections (keep _r1). Chain report: ${JSON.stringify(out.chain || {}).slice(0, 3500)}. Write ${KB2}/VERIFY_CHAIN.md. Return status, Korean summary (<= 25 lines) suitable for the user, artifacts + sha256, open (incl. the go/no-go question for the K9-3 closed loop and the push of claude/k93-b2-20261024).`, { label: 'verify-chain', phase: 'Chain', schema: SCHEMA })
return { stoppedAt: out.vchain && out.vchain.pass ? null : 'VerifyChain', out }
