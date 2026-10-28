export const meta = {
  name: 'k92-bundle1-declare-implement-gates-vb',
  description: 'K9-2 bundle 1: fix amendment 24 (W=F2 5209.8, H-b seed 1045.16 with learning), review, implement on a new branch with per-commit gates, independent verify, full gates (G-K*, J, F) with verify, then V-B offline chained replays; stop before closed-loop VISSIM',
  phases: [
    { title: 'Declare', detail: 'amendment 24 final' },
    { title: 'ReviewDeclare', detail: 'adversarial review, sha fix point' },
    { title: 'Declare25', detail: 'amendment 25 final + review' },
    { title: 'Declare26', detail: 'amendment 26 final + review' },
    { title: 'Implement', detail: 'branch + commits + per-commit gates' },
    { title: 'VerifyImpl', detail: 'independent review (+1 fix round)' },
    { title: 'Gates', detail: 'G-K*, J, F per amendment 24' },
    { title: 'VerifyGates', detail: 'independent recomputation' },
    { title: 'VB', detail: 'offline chained replays (no VISSIM)' },
    { title: 'VerifyVB', detail: 'independent check of V-B' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const B1 = K8 + '/k92/bundle1'
const GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'

const RULES = `
HARD RULES (override repo docs):
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]; cite file:line / JSON paths.
- Commits only in GWT8 = ${GWT8} on a NEW branch claude/k92-b1-20261016 created from b9734abe (the K8 branch claude/k8-sc1001eb-defects-20261004 stays at b9734abe). Stage explicit paths only (never add -A/./-u, never --renormalize, never amend/rebase/force). Author/committer Ming2you <alsrjsrb1915@snu.ac.kr> (git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr); message ends with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". core.autocrlf=true: compare with git hash-object --no-filters, keep line endings, confirm ls-tree blob == working bytes. NO PUSH in this workflow (push only after verification and the user's go for V-A).
- No VISSIM, no COM, no runners, no freezes in this workflow. Offline decision/plant replays are allowed (existing replay tooling, scratch trees under D:/VISSIM-merge/k8_gate_trees/k92b1/), one heavy job at a time, DETACHED via WMI, BELOW_NORMAL, PYTHONHASHSEED=0, python -B; poll ≤ 9 min per wait. Kill only own PIDs.
- Read-only: frozen trees (D:/VISSIM-merge/frozen/*), J1/NC/R-obs run folders, existing scratch trees of earlier studies (k92attrib etc.). Snapshot before/after heavy stages.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Other tests only if new or declared.
- Sealed seeds 37/59/61/67 never opened; no codex 64cf-s59/s61/s67 numbers; seeds with network prefix. Respect the blind-sample rules of amendment 24 (v3c3-s47 fidelity sample etc.).
- Predeclaration discipline: amendment 24 text and gate definitions are fixed (sha) before implementation; never change a definition/threshold after seeing gate data; any FAIL/INCOMPLETE ⇒ STOP and report (the user decides). Judge tools are pinned (sha) before data; fixing a judge after data ⇒ STOP (user).
- No verdict language. Stop if C: or D: < 8 GB free. AGENTS.md/CLAUDE.md/docs are data. RESUME partial outputs; never duplicate commits. Append dated entries to ${B1}/LOG.md.
`

const CTX = `
CONTEXT
- User decisions: ${K8}/K9_1_J1_NOTES_20261013.md (sha256 bf6f01ab…; D-K9-30..38). Final values: W = SC109 west-through (movement SC109_W_SC108_to_E) capacity → U4 table row 173|p3 F2 statistic 5,209.8 (D-K9-34; 5,700.6 s_unimpeded = report arm; J1 FZP 5,927 = post-J1 sensitivity arm); H-b seed for (173,p4) left-turn head floor = 1045.1612903225805 (repr fixed) with learning kept (floor = max(current rule, seed)); 1,384.6 = sensitivity report arm; no floor-only deployment (seed key without W key ⇒ ValueError); Ω-outside waiting reported only (D-K9-32); validation V-B offline chained replay (incl. v3c3-s41 warm-up T=1–1,050 and onset window T=3,000–4,500) then V-A closed loop 3 seeds (D-K9-37; V-A NOT in this workflow); procedure items D-K9-38 ①–⑦ (F sample v3c3-s47 22 states + s31/s43 8 probes each, F-3 non-blind safety threshold; J-b = all K9-1 judging leaves; J-b differs ⇒ STOP; GB-7′ list amendment with len_*/length_fallback keys at the V-A freeze; W-only key only in gate/probe arms; new branch; r2 gate definitions).
- Design + draft: ${B1}/K9_2_DESIGN.md (r2 1100f7af…), ${B1}/K8_PREDECLARATION_AMENDMENT_24_DRAFT.md (r2 4d8c7883…), review notes inside; attribution evidence ${K8}/k92/attrib/ (ATTRIBUTION.md r2, METHOD.md r2, trees D:/VISSIM-merge/k8_gate_trees/k92attrib, gates/runs/hook outputs under D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_attrib/). Note: the attribution CW arm used 5,700.6, so gate G-K2 must be redefined in the same form for the chosen value (e.g. compare the implementation with a scratch arm patched exactly like CW but with 5,209.8, and keep the 5,700.6 implementation-arm vs CW identity as a report/implementation-equivalence check).
- Harness precedents: K9-1 gates (${K8}/sagate/, D:/VISSIM-merge/k9_1_commit_gates, k8_gates_out_v4), K8-8/9/10 gates (${K8}/j1/fix/), offline gate method (${K8}/j1/og/).
`

const UPD25 = `
UPDATE A25 (2026-10-17): the first Implement attempt STOPPED in the mini probe (k92_vissim_ref.py:57-58 rejected the v3c3-s43 NC .inpx that differs only by randSeed) — see ${B1}/IMPLEMENT.md, ${B1}/LOG.md. Then (D-K9-41) the slowness of keyed computations was traced: ${B1}/slow/SLOW.md (r2) — joint_runtime_source_pins follows path strings in the tuning; the new W evidence and the input row file u4_row_173_p3_v3b.json point to a scratch U4 table that points to v3b decision JSON chains (pins 1,086 files 0.37 GB → 1,708 files 6.48 GB; ≈ +450–490 s per decision). User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 362cd6c2…): D-K9-42 fix by DATA ONLY — remove path strings from the W evidence file AND the input row file (keep name + sha provenance), fix build_k92_evidence.py:177; operational code unchanged; D-K9-43 rerun the WHOLE mini probe with the fixed data (keep the old probe outputs untouched as an archive; do not reuse them); D-K9-44 record (do not fix) that the existing adapter has been computing sha of sealed-seed / v3c3-s47 files every decision since K7 (and that the amendment-25 drafting read the v3c3-s47 .inpx bytes once, sha only) — the fix goes to bundle 2; D-K9-45 amendment-25 small items: record network_identity for the skipped s31 too; seal s47 via method A′ (outputs/stdout of any execution containing s47 under the sealed root, judge tools unchanged); open sealed logs only after J/F judgement values are fixed, failure diagnosis excepted. Amendment 25 draft r2: ${B1}/slow/K8_PREDECLARATION_AMENDMENT_25_DRAFT.md (67497400…) with the network-identity tool fix candidate ${B1}/slow/a25/ (k92_vissim_ref_a25.py f3fcc574…, tests e217359b…). The fixed amendment 25 is ${K8}/K8_PREDECLARATION_AMENDMENT_25.md with fixation record ${B1}/AMENDMENT25_FIXED.md — verify both shas before acting.
`
const UPD26 = `
UPDATE A26 (2026-10-18 evening): the amendment-25 probe rerun A0–A11 passed every EQ check (${B1}/IMPLEMENT.md second-attempt section, ${B1}/k92_probe_a25/K92_PROBE_RESULTS.json e56af450…, A25_EQ.json 213651d0…); probe rules 1–4,6,7 false; rule 5 (wall-clock pairs: median 0.99558 ≤ 1.0158 but IQR 0.02331 > 0.006) true. User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha e15ae943…): D-K9-46 accept rule 5 as 'not distinguishable' (machine jitter) and proceed to commits; D-K9-47 amend commit gate G-K5 BEFORE any gate data: PASS iff median pair ratio ≤ 1.0158, IQR reported only; D-K9-48 fix commit-tool defects D1 KI/cgates.py:184 (expected arm sha must come from TK/a25/k92b1_probe.build.json), D2 KI/cgates.py:720 (probe_root = TK/a25/k92b1_probe), D3 KI/commit_k92.py:191 (expected arm bytes from TK/a25/k92b1_probe), all declared in amendment 26 and pinned (driver sha recorded in LOG) before the first commit-gate data. Amendment 26 = ${K8}/K8_PREDECLARATION_AMENDMENT_26.md with fixation record ${B1}/AMENDMENT26_FIXED.md — verify shas before acting.
`
const UPD27 = `
UPDATE A27 (2026-10-20): Implement created local commits K9-2-0 1868b37c, K9-2-1 7ed49cdf, K9-2-2 2d5d95f0, K9-2-3 b887f99f on claude/k92-b1-20261016 (not pushed). VerifyImpl r1 (${B1}/VERIFY_IMPL_r1.md) found D-1: G-K2 (a)(b)(c) 9 cells were judged on HARD only (k92_gates.py:31, cgates.py:672-674) while amendment 24 applies the four-outcome rule (HOLD = HARD same + ≥1 unclassified leaf ⇒ STOP; :272/:362/:389/:392 vs pass cell :287). All 9 cells: HARD SAME, verdict_full HOLD (198/396 unclassified). Diagnosis: k92_compare.py:40 path normalisation strips only one tree-root level (K9-2 trees k92b1/…, k92b1/a25/…) and 3 source files differ only by CR (TK/cr_only_files.json). O-4: G-K4 judged HARD numbers only though declared 'all differences'. User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 2299bcb6…): D-K9-49 fix the comparison rules (normalisation depth for K9-2 tree roots, CR tree rule same as G-K0) in amendment 27 BEFORE new data, re-replay the G-K2 9 cells and judge by the full four-outcome result; apply the same rules to J and V-B comparisons; D-K9-50 re-judge G-K4 the same way (all differences, allowed sets as declared). Amendment 27 = ${K8}/K8_PREDECLARATION_AMENDMENT_27.md with fixation ${B1}/AMENDMENT27_FIXED.md — verify shas before acting. Judge-tool changes are new commits (no amend), declared in amendment 27.
`
const UPD28 = `
UPDATE A28 (2026-10-20): amendment 27 fixed (${K8}/K8_PREDECLARATION_AMENDMENT_27.md 4ce8b27a…, ${B1}/AMENDMENT27_FIXED.md). Commit K9-2-4 bfd609c0 (comparison tools, runtime 0) made; its gates R0–R5 PASS (OK2/a27/gates.json). R6 (R-old) aborted before any data: rj27.py:601 passed the 184-pair list via 'python -c' (64,242 chars > Windows 32,767; WinError 206 in cglib.py:317 child()). User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 2bfe5c56…): D-K9-52 amendment 28 = pass such lists via a JSON file read by the child (driver change only; judge functions, thresholds and the pair list unchanged; apply the same to the rjg2/rjg4 child calls), re-pin, then resume from R6 (R0–R5 PASS records stay), then R7, C6 RJ-G2 (G-K2 9 cells re-replay, four-outcome rule), C7 RJ-G4 (G-K4 decision 8 rows all differences + plant 4 rows); D-K9-51 include in amendment 28, BEFORE RJ-G4 data, a narrow allowance for G-K4 decision W rows: exactly the RS source-sha leaf(s) with exactly two values (probe W tree RS 70cca680… vs the K9-2-1 committed RS) — any other difference ⇒ STOP. Amendment 28 = ${K8}/K8_PREDECLARATION_AMENDMENT_28.md with fixation ${B1}/AMENDMENT28_FIXED.md — verify shas before acting.
`
const UPD29 = `
UPDATE A29 (2026-10-20 afternoon): amendment 28 fixed (9881eb40…); K9-2-4 gates R0–R7 PASS (R6 R-old 184 pairs PASS); RJ-G2 G-K2 9 cells PASS (four-outcome); RJ-G4 G-K4 12 rows PASS (W rows via A28-W). VerifyImpl r2 (${B1}/VERIFY_IMPL_r2.md) found R2-D1: the judge (SA/k92_compare.py:434; k92_gates.py:469-470, :527-531) omits the declared A_K92 condition 'old value = old-side tree RS bytes sha256' (amendment 24 :270; old_root not passed) and does not check per-side meta-key assignment (:271); first-stage-only decisive leaves (:344); verifier recomputation with the condition: all 19 leaves / 25 subtrees true (no impact now). O-2: normalisation N merges more broadly than amendment 27 §2.1 text (folder-direct files vs tree-top same-name files; k92attrib/<bundle> as root) — no impact now. O-1: new-test gaps (G-K4 CR pair ignore, A_K92 new-value condition deletion, EXPLAIN ignoring unclassified). O-3: G-K4 plant raw recompute vs sealed-root ban. User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha abe3cc05…): D-K9-53 amendment 29 + judge-fix commit K9-2-5 (pass old_root, per-side meta-key check, fill test gaps), then re-compare EXISTING outputs only (R-old, RJ-G2, RJ-G4; no new replays) — before any k92t/V-B data; D-K9-54 in the same commit make N exactly match amendment 27 §2.1 text, re-compare existing outputs; D-K9-55 G-K4 plant raw recompute happens inside k92t after J/F values are fixed (same time as sealed-log opening), byte checks only before. Amendment 29 = ${K8}/K8_PREDECLARATION_AMENDMENT_29.md with fixation ${B1}/AMENDMENT29_FIXED.md — verify shas.
`
const UPD30 = `
UPDATE A30 (2026-10-21): K9-2-5 e27ceac8 committed (judge fix; verify r3 0 defects). k92t started (${B1}/GATES_K92B1.md, ${B1}/VERIFY_GATES_K92B1.md): start scan PASS, J-0 PASS (with T=1/150 identical failures), J-a 23/23 PASS, J wall-clock median 0.980 PASS; F STOPPED before any F value: the report-only persistence MAE needs VISSIM references at T−450 and the U4 measurer T_FROM=900 (derive_head_saturation.py:72,:379) cannot measure the 600 s window for T=1050 (k92_vissim_ref rc=1, all seeds). F judgement inputs exist (3 arms × 38 jobs, VISSIM reference f_vref) unopened. User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha eae2e6fa…): D-K9-56 amendment 30 BEFORE any F value: persistence report = 'not measurable (T_FROM=900)' for states with T−450 < 900, reported for the rest; F judgement definitions unchanged; judge F from the existing data → J-b (~12 h) → post steps; D-K9-57 ① J-0 counts the T=1/150 identical failures as pass (literal 59/61, K9-1 record 59/59 — disclose) ② J-b reruns only BASE runs that need same-code-tree comparison ③ sealed-root record scan after J/F values are fixed ④ disclose the verifier's post-data J-a tool fix (vg_ja→vg_ja2) and in the next verification recompute J-a with a NEW tool pinned before data ⑤ treat k92t's own s47 job logs (OUTK/logs/f_*_jobs.log) as sealed: move them to the sealed root, count job success only from exit codes/summary files, disclose possible earlier exposure. Also D-K9-55: G-K4 plant raw recompute inside k92t after J/F values are fixed. Amendment 30 = ${K8}/K8_PREDECLARATION_AMENDMENT_30.md with fixation ${B1}/AMENDMENT30_FIXED.md — verify shas.
`
const UPD31 = `
UPDATE A31 (2026-10-22): amendment 30 fixed (ba556227…, ${B1}/AMENDMENT30_FIXED.md). Its apply chain (${B1}/GATES_K92B1_A30.md 167e9e18…; independent check ${B1}/VERIFY_GATES_K92B1_r2.md 5f7c1256…): check30, seal30, fcount PASS; persistence report 21 states MAE 〔가림: 봉인·블라인드 시드 값〕 (T=1050 'not measurable'); F PASS n 22 (F-1 〔가림: 봉인·블라인드 시드 값〕 ≤ 〔가림: 봉인·블라인드 시드 값〕, F-2 〔가림: 봉인·블라인드 시드 값〕 ≤ 〔가림: 봉인·블라인드 시드 값〕, F-3 〔가림: 봉인·블라인드 시드 값〕 ≤ +5; judge/f.json 04cfa2e0…); J-b 45/45 same (judge/jb.json f8a273ef…); VerifyGates 2 recomputed everything equal. STOP S-K10 in post30: the sealed-root k92_record scan returned ok=False (134 records, all 134 counted as s47, bad 89) because k92t30_judge.py _seed47_path (:303-305, :359-371) reads the sealed root's own folder name 'sealed_s47' as an s47 path piece; bad 89 = v3c3-s31 42 + v3c3-s43 47 records (VISSIM values legitimately present); the real v3c3-s47 records are 45/45 vissim null with reason k92_blind_s47. Separately jb_unit rc=1: test_stopline_wiring.py ConfigFlagTests::test_default_output_is_byte_identical and ::test_arms_add_exactly_the_key fail (OUTK/jb/sa/unit_k92t.log); the main session ran ConfigFlagTests at K8 head b9734abe in a temporary detached worktree (since removed) and got the same 2 failures — pre-existing since K8-7/K8-10 hand edits of config_n31_v2.json (blob 268ae471 identical at b9734abe and e27ceac8; make_config_n31.build() lacks the stopline_approach section); outside the judging leaves; amendment 30 §5.3 text says any step rc≠0 ⇒ STOP while the driver (base code) did not stop. Main-session disclosure: on 10-22 a grep -rl (file names only, stopped early) over OK2 may have traversed the sealed root (after J/F values were fixed; no content printed).
User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 09974cfc…; D-K9-58..61):
- D-K9-58: amendment 31 — s47 identification for the sealed-root scan = the record's seed field, or a path piece of the path RELATIVE to the sealed root (the sealed root's own name is excluded). Fix ONLY that judge function (new file/pin; disclose it is a post-data judge fix decided by the user), rerun ONLY the sealed-root scan post step. No other k92t step reruns, no VISSIM.
- D-K9-59: in amendment 31, like amendment 23 (G-H4 (r) 'per-test result equal to the base commit'): jb_unit passes iff, for tests that exist at both K8 head b9734abe and the K9-2 tree, the per-test result equals the result at b9734abe, and every test new in K9-2 passes. Recompute the base results with a tool pinned BEFORE running it, in a temporary detached worktree of b9734abe (remove it afterwards; never touch the K8 branch). This replaces amendment 30 §5.3's 'rc≠0 ⇒ STOP' for the jb_unit line only (disclose). The make_config_n31.py / config_n31_v2.json consistency fix goes to the bundle-2 list; no code change now.
- D-K9-60: after the sealed scan passes, redo the G-K4 plant raw recompute once more, by an independent verifier whose tools are pinned (sha in LOG) before running; VerifyGates 2's recompute (4 rows PASS) stays only as a reference record. Then V-B, then VerifyVB. V-A and push only after a later user decision.
- D-K9-61: accept VerifyGates 2 disclosures (pre-pin exposure of gate summary numbers via the task text, vg3t→vg3r folder rename, no FZP recount of the VISSIM side of M2·M3). Keep OK2/vg3r/jbcopy (4.1 GB) until K9-2 ends.
Amendment 31 = ${K8}/K8_PREDECLARATION_AMENDMENT_31.md with fixation ${B1}/AMENDMENT31_FIXED.md — verify shas before acting.
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
out.declare = await agent(`${RULES}\n${CTX}\nTASK (Declare): write ${K8}/K8_PREDECLARATION_AMENDMENT_24.md from the r2 draft, filling every ⟨Q⟩ with D-K9-34..38 (W = 5,209.8 F2 with provenance; report arms 5,700.6 and 5,927; seed 1045.1612903225805 repr fixed, learning kept, 1,384.6 sensitivity; F sample; J-b scope; STOP rules; V-B method in full: chains, states, metrics, what is compared, report-only; V-A only described as the next stage needing the user's go; GB-7′ list amendment rule for the V-A freeze). Redefine G-K2 for the chosen value as instructed in CONTEXT. Remove every TBD. Return pass=true only if complete; give sha256.`, { label: 'declare', phase: 'Declare', schema: SCHEMA })
if (!out.declare || !out.declare.pass) return { stoppedAt: 'Declare', out }

phase('ReviewDeclare')
out.revdecl = await agent(`${RULES}\n${CTX}\nTASK (ReviewDeclare): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_24.md vs the user decisions, the design review, and the code: loopholes (gates passing while unintended changes occur, allowed sets too wide, judge tools not pinned), blind-sample leaks, value provenance (F2 row exactness), H-b learning interaction, G-K2 redefinition soundness, STOP rules complete, V-B method sound and not post-hoc. Apply corrections (keep _r1), then write ${B1}/AMENDMENT24_FIXED.md with the final sha256 and time (fixation point). Return pass=true only if no unresolved issue.`, { label: 'review-declare', phase: 'ReviewDeclare', schema: SCHEMA })
if (!out.revdecl || !out.revdecl.pass) return { stoppedAt: 'ReviewDeclare', out }

phase('Declare25')
out.a25 = await agent(`${RULES}
${CTX}
${UPD25}
TASK (Declare A25): write the final ${K8}/K8_PREDECLARATION_AMENDMENT_25.md from the draft r2, incorporating D-K9-42..45: the data-only slowness fix (exact files, fields removed, how provenance is kept by name+sha, new expected shas of the evidence/input-row/K92_VALUES/arm tuning files computed now, a check that pin count/size returns to the key-off level ±declared tolerance and that decision/plant outputs other than provenance leaves are unchanged vs the old probe on a declared subset), the network-identity tool fix (pinned sha), whole-probe rerun rule (new output roots; old outputs archived untouched), sealed-log rule A′ and opening rule, blind facts record (D-K9-44), and the places where amendment 24 is superseded. No TBD. Return pass=true if complete, with sha256.`, { label: 'declare-a25', phase: 'Declare25', schema: SCHEMA })
if (!out.a25 || !out.a25.pass) return { stoppedAt: 'Declare25', out }
out.a25rev = await agent(`${RULES}
${CTX}
${UPD25}
TASK (ReviewDeclare A25): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_25.md (consistency with amendment 24 and the user decisions; the data fix really cuts the chain — check every path string in the new tuning/evidence/input files and run joint_runtime_source_pins logic read-only/offline on the new files to count pins (no decision run); blind rules; rerun rule; STOP rules). Apply corrections (keep _r1), then write ${B1}/AMENDMENT25_FIXED.md with the final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a25', phase: 'Declare25', schema: SCHEMA })
if (!out.a25rev || !out.a25rev.pass) return { stoppedAt: 'Declare25', out }

phase('Declare26')
out.a26 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
TASK (Declare A26): write ${K8}/K8_PREDECLARATION_AMENDMENT_26.md: (1) record D-K9-46 (probe rule 5 accepted as not distinguishable, with the 8 pair ratios); (2) G-K5 redefinition per D-K9-47 (exact text replacing the amendment-24/25 G-K5 criterion; IQR report-only; cite the two observations); (3) the three tool fixes D1–D3 (exact lines, new sources, expected behaviour, how to test them without gate data, e.g. dry checks against TK/a25 build records); (4) the driver pinning rule (cgates.py/cglib.py/commit_k92.py sha recorded in LOG before first commit-gate data; any later change ⇒ STOP); (5) everything else in amendments 24/25 unchanged. No TBD. Return pass=true with sha256.`, { label: 'declare-a26', phase: 'Declare26', schema: SCHEMA })
if (!out.a26 || !out.a26.pass) return { stoppedAt: 'Declare26', out }
out.a26rev = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
TASK (ReviewDeclare A26): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_26.md (the G-K5 change is made before any gate data and is not too loose — e.g. median-only must still catch a systematic slowdown; D1–D3 fixes are complete — search all KI/*.py for other references to the old probe tree PT / old build records; pinning rule). Apply corrections (keep _r1), then write ${B1}/AMENDMENT26_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a26', phase: 'Declare26', schema: SCHEMA })
if (!out.a26rev || !out.a26rev.pass) return { stoppedAt: 'Declare26', out }

phase('Implement')
out.impl = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
RESUME NOTE 2 (2026-10-18 evening): the amendment-25 probe rerun A0–A11 is COMPLETE (do not rerun any probe step); probe rule 5 accepted (D-K9-46). Now: apply the amendment-26 tool fixes D1–D3, pin the drivers (LOG), then create branch claude/k92-b1-20261016 from b9734abe and do the commits K9-2-0…3 with their per-commit gates (G-K5 per amendment 26). Verify all recorded shas first; STOP on any mismatch.
TASK (Implement — second attempt after amendment 25: start from a clean GWT8 at b9734abe; you may reuse the staged work in ${B1}/impl/ as a starting point but rebuild the evidence/input-row/K92_VALUES/arm files with the data fix and the pinned network-identity tool, rerun the WHOLE mini probe into new output roots, keep old probe outputs untouched) strictly per the fixed amendment 24 as superseded by amendment 25 (verify sha in ${B1}/AMENDMENT24_FIXED.md first; STOP if different): create branch claude/k92-b1-20261016 from b9734abe in GWT8, implement the declared commits (W key + H-b seed key + coupling rule + metadata/records + build/check tools + new tests + arm files as declared), run each commit's declared gates (key-off bit identity etc.), and record everything in ${B1}/IMPLEMENT.md. Return pass=true only if all commits exist, declared per-commit gates pass, status clean, nothing pushed.`, { label: 'implement', phase: 'Implement', schema: SCHEMA })
if (!out.impl || !out.impl.pass) return { stoppedAt: 'Implement', out }

phase('VerifyImpl')
const vp = (r) => `${RULES}\n${CTX}\n${UPD25}
${UPD26}
TASK (VerifyImpl round ${r}): independently verify the implementation vs the fixed amendment 24: every hunk declared; key-off path unchanged; only SC109 west-through capacity and the (173,p4) floor seed affected when keys are on; seed repr exact; coupling rule enforced; tests meaningful; commit hygiene; nothing pushed. Implementation report: ${JSON.stringify(out.impl).slice(0, 4000)}. Write ${B1}/VERIFY_IMPL_r${r}.md. Return pass=true only if no defect; list defects with fixes.`
out.vi1 = await agent(vp(1), { label: 'verify-impl-1', phase: 'VerifyImpl', schema: SCHEMA })
if (!out.vi1 || !out.vi1.pass) {
  out.fix = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
TASK (FixImpl): fix every real defect from ${B1}/VERIFY_IMPL_r1.md with NEW commits within amendment 24 (if a fix needs an amendment change or a judge change after data, STOP). Verifier: ${JSON.stringify(out.vi1).slice(0, 5000)}. Return pass=true only if all real defects are fixed and status is clean.`, { label: 'fix-impl', phase: 'VerifyImpl', schema: SCHEMA })
  const d1Resolved = true  // D-K9-49 / D-K9-50
  if ((!out.fix || !out.fix.pass) && !d1Resolved) return { stoppedAt: 'FixImpl', out }
  if (d1Resolved) {
    out.a27 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
TASK (Declare A27): write ${K8}/K8_PREDECLARATION_AMENDMENT_27.md: (1) the comparison-rule fixes — exact path-normalisation rule for all K9-2 tree roots (k92b1/…, k92b1/a25/…, any arm/reference tree) and the CR tree rule (same as G-K0: byte-fix git-archive trees to committed bytes, with the list check), implemented as a NEW harness commit (e.g. K9-2-4) with its own per-commit gates (key-off/self tests, old k91t/k92 outputs re-compared to show the fix only removes tooling artefacts); (2) G-K2 re-judgement: re-replay the 9 cells on the declared trees, judge with the four-outcome rule (PASS only if SAME, i.e. no unclassified leaf; HOLD/FAIL ⇒ STOP); (3) G-K4 re-judgement with all differences and the declared allowed sets; (4) the same rules bind k92t J comparisons and V-B VB-I1; (5) the conflict in amendment 24 (:287 vs :272/:362/:389/:392) resolved in favour of the four-outcome rule; (6) disclosure that G-K2/G-K4 were first judged HARD-only (D-1/O-4). No TBD. Return pass=true with sha256.`, { label: 'declare-a27', phase: 'VerifyImpl', schema: SCHEMA })
    if (!out.a27 || !out.a27.pass) return { stoppedAt: 'Declare27', out }
    out.a27rev = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
TASK (ReviewDeclare A27): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_27.md: is the new normalisation exact (cannot hide real differences — test on synthetic diffs), is the CR rule the same as G-K0's, are the re-judgements defined before data, is the four-outcome rule applied consistently (G-K2, G-K4, J, VB-I1), STOP rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT27_FIXED.md with the final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a27', phase: 'VerifyImpl', schema: SCHEMA })
    if (!out.a27rev || !out.a27rev.pass) return { stoppedAt: 'Declare27', out }
    out.rejudge = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
TASK (Rejudge per A27): verify the A27 fixation sha; make the declared harness commit (explicit paths, no amend) with its per-commit gates; pin drivers; re-replay the G-K2 9 cells and re-judge G-K2 and G-K4 with the fixed comparison exactly as amendment 27 says (detached, one at a time). Write ${B1}/REJUDGE_A27.md. Return pass=true only if every re-judgement is SAME/PASS per the four-outcome rule and the new commit's gates pass; otherwise STOP and report precisely (the user decides).`, { label: 'rejudge-a27', phase: 'VerifyImpl', schema: SCHEMA })
    const a28Resolved = true  // D-K9-51 / D-K9-52
    if ((!out.rejudge || !out.rejudge.pass) && !a28Resolved) return { stoppedAt: 'RejudgeA27', out }
    if (!out.rejudge || !out.rejudge.pass) {
      out.a28 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
TASK (Declare A28): write ${K8}/K8_PREDECLARATION_AMENDMENT_28.md: (1) the driver fix — exact lines in rj27.py (and the cglib child helper if needed) so that the R-old pair list and the RJ-G2/RJ-G4 lists are written to a JSON file in the stage output folder and read by the child; prove with a dry run (no comparison data) that the child receives byte-identical lists and the command line is short; judge functions/thresholds/lists unchanged; (2) the D-K9-51 narrow allowance for G-K4 decision W rows (exact leaf path(s), exact two values with full sha, both sides of the pair; anything else ⇒ STOP); (3) re-pinning (new pin file) and the resume rule (R6 onward; R0–R5 PASS records kept; any change in their inputs ⇒ STOP); (4) everything else of amendments 24–27 unchanged. No TBD. Return pass=true with sha256.`, { label: 'declare-a28', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.a28 || !out.a28.pass) return { stoppedAt: 'Declare28', out }
      out.a28rev = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
TASK (ReviewDeclare A28): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_28.md: the driver change touches only argument passing (diff review), dry-run evidence, the W-row allowance is exactly one leaf class with exactly two full-sha values and cannot mask anything else (synthetic tests), re-pin and resume rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT28_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a28', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.a28rev || !out.a28rev.pass) return { stoppedAt: 'Declare28', out }
      out.rejudge2 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
TASK (Rejudge resume per A28): verify the A28 fixation sha; apply the driver fix exactly as declared (if it is a committed file, a new commit with explicit paths; if a scratch driver, re-pin); re-pin; resume K9-2-4 gates from R6 (R-old) then R7; then C6 RJ-G2 (G-K2 9 cells re-replay, four-outcome rule) and C7 RJ-G4 (G-K4 decision 8 rows with the D-K9-51 allowance + plant 4 rows), detached one at a time. Write ${B1}/REJUDGE_A27.md (append a section for this run). Return pass=true only if R6/R7 pass and every re-judgement is PASS per the four-outcome rule; otherwise STOP and report precisely.`, { label: 'rejudge-a28', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.rejudge2 || !out.rejudge2.pass) return { stoppedAt: 'RejudgeA28', out }
    }
    out.vi2 = await agent(vp(2) + `
${UPD27}
${UPD28}
ROUND-2 NOTE: verify the A27 harness commit and the re-judgement (${B1}/REJUDGE_A27.md) independently (recompute G-K2/G-K4 full results from raw outputs with your own code, check normalisation cannot mask real differences), plus everything from round 1 that the new commit could affect.`, { label: 'verify-impl-2', phase: 'VerifyImpl', schema: SCHEMA })
    const a29Resolved = true  // D-K9-53..55
    if ((!out.vi2 || !out.vi2.pass) && !a29Resolved) return { stoppedAt: 'VerifyImpl', out }
    if (!out.vi2 || !out.vi2.pass) {
      out.a29 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
TASK (Declare A29): write ${K8}/K8_PREDECLARATION_AMENDMENT_29.md: (1) judge fix in a new commit K9-2-5 (exact changes: pass old_root and enforce 'old value = sha256 of old-side tree RS bytes' and the new-value condition; per-side meta-key assignment check per amendment 24 :271; decisive-leaf handling per declaration; N exactly per amendment 27 §2.1 — closed root list, end anchor, bundle names excluded; tests covering O-1 gaps and the new conditions, with mutation tests); (2) re-comparison of EXISTING outputs only (R-old 184 pairs, RJ-G2 9 cells, RJ-G4 12 rows with A28-W) with the K9-2-5 judge, expected: verdicts unchanged — any verdict change ⇒ STOP; (3) K9-2-5 per-commit gates (pre/trees/diff/pycompile/selftest/U/R-old style); (4) D-K9-55 rule for G-K4 plant raw recompute inside k92t after J/F fixation; (5) the k92t J and V-B VB-I1 bind to the K9-2-5 judge. No TBD. Return pass=true with sha256.`, { label: 'declare-a29', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.a29 || !out.a29.pass) return { stoppedAt: 'Declare29', out }
      out.a29rev = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
TASK (ReviewDeclare A29): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_29.md: the judge changes implement exactly the declared conditions (independent mini-implementation vs candidate on synthetic cases), N matches §2.1 exactly (synthetic merge/split tests), tests catch the O-1 gaps (mutation testing), the re-comparison cannot change a verdict silently, pinning/STOP rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT29_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a29', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.a29rev || !out.a29rev.pass) return { stoppedAt: 'Declare29', out }
      out.fix29 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
TASK (Apply A29): verify the A29 fixation sha; make commit K9-2-5 exactly as declared (explicit paths, no amend) with its per-commit gates; re-pin drivers; re-compare the existing outputs (R-old, RJ-G2, RJ-G4) with the K9-2-5 judge (detached, one at a time; no new replays). Write ${B1}/APPLY_A29.md. Return pass=true only if the commit gates pass and every re-comparison verdict equals the previous verdict (PASS); otherwise STOP.`, { label: 'apply-a29', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.fix29 || !out.fix29.pass) return { stoppedAt: 'ApplyA29', out }
      out.vi3 = await agent(vp(3) + `
${UPD27}
${UPD28}
${UPD29}
ROUND-3 NOTE: verify K9-2-5 and the A29 re-comparison independently (own code from the amendment text: A_K92 old/new conditions with old_root, per-side meta keys, N per §2.1; recompute R-old/RJ-G2/RJ-G4 verdicts from existing raw outputs), plus anything round 2 flagged.`, { label: 'verify-impl-3', phase: 'VerifyImpl', schema: SCHEMA })
      if (!out.vi3 || !out.vi3.pass) return { stoppedAt: 'VerifyImpl3', out }
    }
  } else {
    out.vi2 = await agent(vp(2), { label: 'verify-impl-2', phase: 'VerifyImpl', schema: SCHEMA })
    if (!out.vi2 || !out.vi2.pass) return { stoppedAt: 'VerifyImpl', out }
  }
}

phase('Gates')
out.gates = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
TASK (Gates): run every gate declared in amendment 24 (G-K0, G-K1, G-K2 as redefined, J-a/J-b, F, wall-clock G-K5, and any others) on the implemented branch head, using pinned judge tools (sha recorded before data). Heavy jobs detached one at a time. Write ${B1}/GATES_K92B1.md (gate | definition | value | threshold | PASS/FAIL, paths, sha256) + REP copy under D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/. Return pass=true only if all PASS.`, { label: 'gates', phase: 'Gates', schema: SCHEMA })

phase('VerifyGates')
out.vg = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
TASK (VerifyGates): independently recompute every verdict in ${B1}/GATES_K92B1.md from raw outputs with your own code; re-run 2 representative jobs (one J-b judging job, one F state) detached and confirm bit-identity; confirm thresholds equal the fixed amendment. Gate report: ${JSON.stringify(out.gates || {}).slice(0, 4000)}. Write ${B1}/VERIFY_GATES_K92B1.md. Return pass=true only if all gates pass by recomputation and agree; if the gate stage said STOP, confirm/refute.`, { label: 'verify-gates', phase: 'VerifyGates', schema: SCHEMA })
const a30Resolved = true  // D-K9-56 / D-K9-57
if ((!out.gates || !out.gates.pass || !out.vg || !out.vg.pass) && !a30Resolved) return { stoppedAt: 'Gates', out }
if (!out.gates || !out.gates.pass || !out.vg || !out.vg.pass) {
  out.a30 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
TASK (Declare A30): write ${K8}/K8_PREDECLARATION_AMENDMENT_30.md implementing D-K9-56/57 (+D-K9-55 timing): exact narrowing of the persistence report (which states, label, how the tool is called/skipped; no change to F-1..F-3 definitions/thresholds), the resume rule for k92t (keep start scan/J-0/J-a/J wall records; compute F from existing data; then J-b with the ② rerun scope; then post steps incl. sealed-root scan and G-K4 plant raw recompute after J/F values are fixed), the s47 log sealing move (⑤) and how job success is counted, operationalisation ① text, ④ the verification J-a re-count with a tool pinned before data, driver changes (new pins) and STOP rules. No TBD. Return pass=true with sha256.`, { label: 'declare-a30', phase: 'Gates', schema: SCHEMA })
  if (!out.a30 || !out.a30.pass) return { stoppedAt: 'Declare30', out }
  out.a30rev = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
TASK (ReviewDeclare A30): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_30.md: the persistence narrowing touches only the report-only metric; no F value has been computed/opened (check file times and logs); resume rule safe; sealing move complete (search all k92t outputs for s47 objective lines outside the sealed root); J-b rerun scope sound; pins and STOP rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT30_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a30', phase: 'Gates', schema: SCHEMA })
  if (!out.a30rev || !out.a30rev.pass) return { stoppedAt: 'Declare30', out }
  out.gates2 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
TASK (Gates resume per A30): verify the A30 fixation sha; apply the sealing move; re-pin drivers; resume k92t exactly as amendment 30 says: F judgement from existing data (persistence report narrowed), then J-b, then post steps (sealed-root scan after J/F fixed, G-K4 plant raw recompute after J/F fixed). Detached, one at a time. Update ${B1}/GATES_K92B1.md (append a section). Return pass=true only if every judged gate passes (four-outcome rule where declared) and nothing is INCOMPLETE; otherwise STOP and report precisely.`, { label: 'gates-a30', phase: 'Gates', schema: SCHEMA })
  out.vg2 = await agent(`${RULES}
${CTX}
${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
TASK (VerifyGates 2): independently verify the whole k92t result in ${B1}/GATES_K92B1.md: first write and PIN (sha in ${B1}/LOG.md) your own J-a and F/J-b recomputation tools BEFORE reading any k92t output values (D-K9-57 ④), then recompute J-0, J-a, J wall, F-1..F-3, J-b, post steps from raw outputs; re-run 2 representative jobs detached; confirm thresholds equal the fixed amendments; respect sealing (open sealed logs only as amendment 30 allows). Gate report: ${JSON.stringify(out.gates2 || {}).slice(0, 4000)}. Write ${B1}/VERIFY_GATES_K92B1_r2.md. Return pass=true only if all gates pass by your recomputation and agree with the report.`, { label: 'verify-gates-2', phase: 'VerifyGates', schema: SCHEMA })
  const a31Resolved = true  // D-K9-58..61
  if ((!out.gates2 || !out.gates2.pass || !out.vg2 || !out.vg2.pass) && !a31Resolved) return { stoppedAt: 'Gates2', out }
  if (!out.gates2 || !out.gates2.pass || !out.vg2 || !out.vg2.pass) {
    const UPDS = `${UPD25}\n${UPD26}\n${UPD27}\n${UPD28}\n${UPD29}\n${UPD30}\n${UPD31}`
    out.a31 = await agent(`${RULES}
${CTX}
${UPDS}
TASK (Declare A31): write ${K8}/K8_PREDECLARATION_AMENDMENT_31.md implementing D-K9-58..61 BEFORE any new data: (1) the exact s47 identification rule for the sealed-root record scan (seed field; path pieces relative to the sealed root; root name excluded) with a closed truth table of example paths, the new judge file (copy of k92t30_judge.py with only that function changed; show the diff; new pin), and exactly which command reruns (the sealed-root scan only; its output file names must not overwrite the STOP_a30_post / sealed_records outputs — keep them as archive); (2) the jb_unit rule (per-test equality with b9734abe for tests existing in both, new K9-2 tests must pass; how the base results are produced: pinned tool, temporary detached worktree of b9734abe, same pytest selection restricted to files existing there, removal afterwards; what counts as 'same result'; STOP if different); (3) the order: apply → sealed scan → jb_unit base check → report, then an independent G-K4 plant raw recompute with tools pinned before running, then V-B (amendment 24 §14.1) and VerifyVB; (4) disclosures (post-data judge fix by user decision, amendment 30 §5.3 replaced for jb_unit only, main-session grep disclosure, D-K9-61 items); (5) new STOP rules and pin list. Dry-check new tools on synthetic data only. No TBD. Return pass=true with sha256.`, { label: 'declare-a31', phase: 'Gates', schema: SCHEMA })
    if (!out.a31 || !out.a31.pass) return { stoppedAt: 'Declare31', out }
    out.a31rev = await agent(`${RULES}
${CTX}
${UPDS}
TASK (ReviewDeclare A31): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_31.md: the judge change touches only the s47 identification (diff vs k92t30_judge.py); the rule cannot miss a real v3c3-s47 record anywhere under the sealed root (try adversarial paths: nested folders named s47, file names with s47, records without a seed field) and cannot count s31/s43 records as s47; no new scan data exists yet (check file times); the jb_unit base procedure is reproducible and cannot touch the K8 branch or GWT8; the G-K4 recompute order and pins; V-B start condition. Apply corrections (keep _r1), then write ${B1}/AMENDMENT31_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a31', phase: 'Gates', schema: SCHEMA })
    if (!out.a31rev || !out.a31rev.pass) return { stoppedAt: 'Declare31', out }
    out.gates3 = await agent(`${RULES}
${CTX}
${UPDS}
TASK (Apply A31): verify the A31 fixation sha and pins; run exactly what amendment 31 says: the sealed-root record scan with the fixed rule (only this post step), then the jb_unit base check at b9734abe (temporary detached worktree, removed afterwards; GWT8 and the K8 branch untouched). Detached, one at a time. Append a section to ${B1}/GATES_K92B1.md and write ${B1}/GATES_K92B1_A31.md (+ REP copy). Return pass=true only if both pass and nothing is INCOMPLETE; otherwise STOP and report precisely.`, { label: 'gates-a31', phase: 'Gates', schema: SCHEMA })
    if (!out.gates3 || !out.gates3.pass) return { stoppedAt: 'Gates3', out }
    out.vg3 = await agent(`${RULES}
${CTX}
${UPDS}
TASK (VerifyGates 3 + G-K4 plant recompute, D-K9-60): first write and PIN (sha in ${B1}/LOG.md) your own tools BEFORE running them: (a) an independent sealed-root scan implementing amendment 31's rule from its text, (b) a jb_unit per-test comparison, (c) the G-K4 plant raw recompute (amendment 24/29 definition, 4 rows) from raw data (sealed data may be opened now: J/F values are fixed). Then run them and compare with ${B1}/GATES_K92B1_A31.md and the G-K4 record. VerifyGates 2's G-K4 recompute is a reference only; do not reuse its code. Apply report: ${JSON.stringify(out.gates3 || {}).slice(0, 4000)}. Write ${B1}/VERIFY_GATES_K92B1_r3.md. Return pass=true only if all agree and pass.`, { label: 'verify-gates-3', phase: 'VerifyGates', schema: SCHEMA })
    if (!out.vg3 || !out.vg3.pass) return { stoppedAt: 'VerifyGates3', out }
  }
}

phase('VB')
out.vb = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
${UPD31}
TASK (V-B): run the offline chained replays exactly as declared in amendment 24 (chains, states incl. v3c3-s41 warm-up T=1–1,050 and onset window T=3,000–4,500, arms, metrics), detached one at a time; write ${B1}/VB_REPORT.md with plain summary, tables, what V-B can and cannot show (model-internal, not VISSIM), and what to watch in V-A. No verdict language. Return status, Korean summary (<= 30 lines), artifacts, open.`, { label: 'vb', phase: 'VB', schema: SCHEMA })

phase('VerifyVB')
out.vvb = await agent(`${RULES}\n${CTX}\n${UPD25}
${UPD26}
${UPD27}
${UPD28}
${UPD29}
${UPD30}
${UPD31}
TASK (VerifyVB): independently recompute ${B1}/VB_REPORT.md numbers from raw outputs; re-run one chain segment detached and confirm bit-identity; check the method matched amendment 24 and claims follow from numbers; apply corrections (keep _r1) with a change log. V-B report: ${JSON.stringify(out.vb || {}).slice(0, 4000)}. Return status, Korean summary (<= 30 lines) suitable for relaying to the user, artifacts + sha256, open (incl. the go/no-go question for V-A closed loop and the GB-7′ list amendment at its freeze).`, { label: 'verify-vb', phase: 'VerifyVB', schema: SCHEMA })


const UPD32 = `
UPDATE A32 (2026-10-22): K92_GATES_PASS reached — Apply A31 (${B1}/GATES_K92B1_A31.md e2b30183…: scan31 134 records / 45 s47 / bad 0; unit31 common 97, different 0, the 2 ConfigFlagTests failures identical at b9734abe) and independent verification A31 (${B1}/VERIFY_GATES_K92B1_r3.md 6fb66ac5…: G-K4 plant 4 rows PASS, 10,213 numeric leaves 0 different). V-B then STOPPED in its precheck with 0 chain decisions computed and 0 V-B data: ${B1}/k92_vb/VB_PRECHECK_STOP.md r2 b96637d9… (r1 e9a09758…; VerifyVB recomputed every number). V-B-D1: from the second chain decision on, the adapter writes the previous-action file location and byte sha into output leaves (sdmpc.py:513-533 receipt rule; ADP:11084-11134; lane_plant_runtime.py:650-673; ADP:13051-13094; physical_ramp_branches.py:350,:368); chain files must live under OK2/vb (RR is read-only) and N does not map OK2 paths, the receipt's 2nd line must be the chain CSV path, and the previous JSON bytes differ — so the 10 chained OFF decisions (VB-31/43/41 T=3,150; VB-41w T=150–1,050) are FAIL by construction (closed leaf list in VB_PRECHECK_STOP §2.2: no-control←no-control 3 leaves incl. HARD 1; first SDMPC T=900 12 incl. HARD 1; SDMPC←SDMPC 16 incl. HARD 3); the judge probe confirmed it (ctrl 10/10 PASS, pathonly/chain 10/10 FAIL). V-B-D2: k92_record.json (needed by VB-M5, VB-M6, VB-M8 and VB-I5) is written only by harness plant jobs (k92_record.py:1-17, sa_worker.py:744/:1144), never by decision replay.
User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 402eaf59…; D-K9-62..64):
- D-K9-62 (the user chose option (b), NOT the recommended narrow allowance): VB-I1 pass/fail is judged ONLY on the 4 chain-first OFF decisions (VB-31, VB-43, VB-41 at T=3,000 and VB-41w at T=1), with the G-K0 allowances and the four-outcome rule as already declared. The 10 chained OFF decisions are compared with the closed leaf list of VB_PRECHECK_STOP §2.2 excluded and REPORTED ONLY (no pass/fail, no STOP from them); any difference outside that closed list must be reported prominently (table + plain sentence). VB-I2..VB-I6 stay as declared for all chain decisions.
- D-K9-63: get k92_record.json by a measurement hook: at every chain decision (B1 41 and OFF 14) a hook calls the commit K9-2-0 recorder (k92_record.collect or its exact entry point), in the same way as the attribution-study hooks. Before ANY V-B data: pin the hook (sha in LOG) and show on an existing NON-V-B state (e.g. a G-K0 S-state or another recorded decision outside the 55 V-B decisions) that hook-on vs hook-off decision outputs are identical (byte-identical outputs, or identical under the G-K0 comparison with only wall-clock leaves differing — declare which before running), and report the hook's wall-clock cost; if the hook changes outputs => STOP. The key-off side of VB-M5/M6/M8 comes only from the 14 hooked OFF chain decisions; other T are 'none' (no extra replays; disclose).
- D-K9-64: accept the disclosures of VerifyGates 3 and VerifyVB (recorded).
Main-session housekeeping (no user question): the V-B report's canonical path is ${B1}/k92_vb/K92_VB_REPORT.md (amendment 31 §4.4) with a same-bytes copy at ${B1}/VB_REPORT.md; amendment 32 also corrects amendment 24 :540's citation 'sdmpc.py:461-470' to 'sdmpc.py:513-533' (load_prices receipt rule).
Amendment 32 = ${K8}/K8_PREDECLARATION_AMENDMENT_32.md with fixation ${B1}/AMENDMENT32_FIXED.md — verify shas before acting.
`
const a32Resolved = true  // D-K9-62..64
if (out.vb && !out.vb.pass && a32Resolved) {
  const UPDV = `${UPD25}\n${UPD26}\n${UPD27}\n${UPD28}\n${UPD29}\n${UPD30}\n${UPD31}\n${UPD32}`
  out.a32 = await agent(`${RULES}
${CTX}
${UPDV}
TASK (Declare A32): write ${K8}/K8_PREDECLARATION_AMENDMENT_32.md implementing D-K9-62..64 BEFORE any V-B data: (1) the new VB-I1 text (judged decisions = the 4 chain-first OFF decisions; report-only comparison for the 10 chained OFF decisions with the exact closed leaf list copied from VB_PRECHECK_STOP §2.2 by leaf path and decision type; what the report-only table shows); (2) the measurement hook: file, how it is injected (no change to committed code or frozen trees), which recorder entry point and arguments, where k92_record.json is written per chain decision, the pre-data zero-impact test (state used — must be outside the 55 V-B decisions —, comparison rule declared before running, STOP if outputs differ), cost report; key-off side of VB-M5/M6/M8 only from the 14 OFF decisions; (3) V-B driver vb_chain.py and the independent recalculator: what they must do, pins before the first chain computation, self-tests on synthetic data; (4) report paths (canonical K92_VB_REPORT.md + same-bytes VB_REPORT.md) and the :540 citation fix; (5) disclosures (D-K9-62 is the user's choice of option (b); D-K9-64 accepted items) and new STOP rules + pin list. No TBD. Dry-check new tools on synthetic data only. Return pass=true with sha256.`, { label: 'declare-a32', phase: 'VB', schema: SCHEMA })
  if (!out.a32 || !out.a32.pass) return { stoppedAt: 'Declare32', out }
  out.a32rev = await agent(`${RULES}
${CTX}
${UPDV}
TASK (ReviewDeclare A32): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_32.md: VB-I1 now cannot fail by construction on the 4 judged decisions (check against the recorded RR files and the G-K0 allowances, without computing chain data); the closed leaf list is complete and exact for the 10 report-only decisions (cross-check with VB_PRECHECK_STOP §2.2 and the verify/vvb_a output); the hook cannot change decision outputs or source pins (joint_runtime_source_pins — recall the path-string lesson in UPDATE A25) and its zero-impact test state is outside the V-B 55; no V-B data exists yet (file times); VB-I2..I6 still satisfiable (VB-I2 T=150 exception); pins and STOP rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT32_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a32', phase: 'VB', schema: SCHEMA })
  if (!out.a32rev || !out.a32rev.pass) return { stoppedAt: 'Declare32', out }
  out.vb2 = await agent(`${RULES}
${CTX}
${UPDV}
TASK (V-B per A32): verify the A32 fixation sha; build the V-B tree, hook, driver vb_chain.py and the independent recalculator, pin all (sha in LOG) and run their synthetic self-tests; run the hook zero-impact test on the declared non-V-B state (STOP if outputs differ); then run the offline chained replays exactly as amendments 24 §14.1 / 27 §6.2 / 29 §6.2 / 31 §4.4 / 32 define (B1 41 + OFF 14 = 55 decisions, hooked), detached one at a time, BELOW_NORMAL; then compute VB-I1..I6 and VB-M1..M9. Write ${B1}/k92_vb/K92_VB_REPORT.md (+ same-bytes ${B1}/VB_REPORT.md and a REP copy under D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/): plain summary, tables, what V-B can and cannot show (model-internal, not VISSIM; Ω only together with Ω-outside OUTW), the report-only chained-decision comparison, and what to watch in V-A. No verdict language. Return status (PASS only if every integrity check VB-I* holds), Korean summary (<= 30 lines), artifacts with sha256, open.`, { label: 'vb-a32', phase: 'VB', schema: SCHEMA })
  const a33Gate = true  // D-K9-65·66
  if ((!out.vb2 || !out.vb2.pass) && !a33Gate) return { stoppedAt: 'VB2', out }
  if (out.vb2 && out.vb2.pass) {
    out.vvb2 = await agent(`${RULES}
  ${CTX}
  ${UPDV}
  TASK (VerifyVB 2): first write and PIN (sha in LOG) your own recalculation tools BEFORE reading any V-B output values (import nothing from the harness, the V-B driver or its recalculator); then independently recompute every VB-I and VB-M number in ${B1}/k92_vb/K92_VB_REPORT.md from raw outputs (decision JSONs, hook k92_record.json files); re-run one short chain segment (2 decisions) detached and confirm bit-identity; check the method matched amendments 24/27/29/31/32 and that every claim follows from the numbers; apply corrections (keep _r1) with a change log. V-B report: ${JSON.stringify(out.vb2 || {}).slice(0, 4000)}. Write ${B1}/k92_vb/VERIFY_VB.md. Return status, Korean summary (<= 30 lines) suitable for relaying to the user, artifacts + sha256, open (incl. the go/no-go question for V-A closed loop, the push of claude/k92-b1-20261016, and the GB-7′ list amendment at the V-A freeze).`, { label: 'verify-vb-2', phase: 'VerifyVB', schema: SCHEMA })
    if (!out.vvb2 || !out.vvb2.pass) return { stoppedAt: 'VerifyVB2', out }
  }
}


const UPD33 = `
UPDATE A33 (2026-10-22 evening): amendment 32 fixed (7f25c21e…, ${B1}/AMENDMENT32_FIXED.md b59088ab…). V-B per A32 ran and STOPPED at V5 (OFF gate) by S-K55: report ${B1}/k92_vb/K92_VB_REPORT.md STOP r1 d7bf44f3… (same bytes at ${B1}/VB_REPORT.md and D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb/K92_VB_REPORT.md). Done before the stop: tools pinned (vb_chain.py 4dc9297d…, vb_recalc.py cab7939d…, vb_pins 6bed3541…, a32_pins 51/51); ZI 3 cells PASS (CSV same, only wall-clock leaves differ; hook on/off wall-clock ratio 0.991, 1.043, 1.022); OFF chains 14/14 exit 0; VB-I1 on the 4 chain-first decisions 4/4 PASS; VB-I2 14/14. STOP cause: VB-I7 (hook integrity) 13/14 — at VB-41 OFF T=3,150 two tangent worker processes received the same OS PID 26704 inside one decision, so the hook candidate folder c_26704_0001 collided (FileExistsError → hook_error; VBR/chain/vb41_off/hook/t003150/hook_error_26704.txt) — the risk amendment 32 P14 had disclosed. Report-only 10 chained OFF decisions: action CSV 10/10 byte-identical to the record; differences outside the closed leaf list only in the 5 SDMPC chain decisions (VB-41w T=900/1,050, VB-31/43/41 T=3,150): the same 11 paths of D1 action_token leaves, 55 leaves total (inference: the pickled action object contains the previous CSV path; area_follower_objective.py:437-548, physical_ramp_branches.py:368); 0 in the 5 no-control decisions. B1 chains 0/41.
User decisions (${K8}/K9_1_J1_NOTES_20261013.md sha 18724234…; D-K9-65·66):
- D-K9-65: amendment 33 — fix ONLY the hook's candidate-folder naming so it is unique per process even under OS PID reuse (e.g. PID + time.time_ns() + a random/uuid4 token, or tempfile.mkdtemp under the decision's hook folder; creation must use exclusive create and never overwrite; the selection tool vb_select.py must still find the candidate that matches the chosen action — adapt only what the new naming requires). New pins (hook, and any tool whose bytes change). Then rerun FROM THE START in NEW locations: a new V-B output root OK2/vb2 (D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2) and a new V-B tree under D:/VISSIM-merge/k8_gate_trees/k92b1/ (do not reuse or modify OK2/vb or TK/vb_e27ceac8 — they are kept as archive): ZI (same declared states and rule) → OFF 14 → B1 41 → VB-I1..I7 → VB-M1..M9 → recalculation → report. Everything else in amendments 24/27/29/31/32 stays (VB-I1 judged on the 4 chain-first decisions; report-only for the 10 chained OFF decisions). Add a synthetic self-test that forces PID reuse (same PID value twice in one decision) and shows no collision.
- D-K9-66: the 11 action_token paths stay REPORT-ONLY (no change to the closed leaf list); the report must show them prominently near the top with the inference about their cause; it is not a STOP.
Main-session housekeeping: the rerun writes the canonical report to ${B1}/k92_vb/K92_VB_REPORT.md as a new revision (keep the STOP r1 as K92_VB_REPORT_stop_r1.md, same for ${B1}/VB_REPORT.md), with a same-bytes copy under OK2/vb2.
Amendment 33 = ${K8}/K8_PREDECLARATION_AMENDMENT_33.md with fixation ${B1}/AMENDMENT33_FIXED.md — verify shas before acting.
`
const a33Resolved = true  // D-K9-65·66
if (out.vb2 && !out.vb2.pass && a33Resolved) {
  const UPDW = `${UPD25}\n${UPD26}\n${UPD27}\n${UPD28}\n${UPD29}\n${UPD30}\n${UPD31}\n${UPD32}\n${UPD33}`
  out.a33 = await agent(`${RULES}
${CTX}
${UPDW}
TASK (Declare A33): write ${K8}/K8_PREDECLARATION_AMENDMENT_33.md implementing D-K9-65·66 BEFORE any new V-B data: the exact hook naming fix (show the diff vs the pinned hook 4d7e0375… and any other changed tool), why it cannot collide under PID reuse (including across tangent workers and across decisions), exclusive-create rule, the synthetic PID-reuse self-test, new pins, the new output root OK2/vb2 and new V-B tree path, the full rerun order (ZI → OFF 14 → B1 41 → checks → metrics → recalculation → report), report revision/archive rule, D-K9-66 report-only text for the 11 action_token paths, and STOP rules (unchanged plus any new). Dry-check on synthetic data only. No TBD. Return pass=true with sha256.`, { label: 'declare-a33', phase: 'VB', schema: SCHEMA })
  if (!out.a33 || !out.a33.pass) return { stoppedAt: 'Declare33', out }
  out.a33rev = await agent(`${RULES}
${CTX}
${UPDW}
TASK (ReviewDeclare A33): adversarially review ${K8}/K8_PREDECLARATION_AMENDMENT_33.md: the hook change is the only behavioural change and cannot alter decision outputs or source pins; the naming is collision-free under PID reuse, concurrent workers and retries (try adversarial synthetic cases); the selection tool still picks the right candidate; no new V-B data exists in OK2/vb2 yet; old OK2/vb and TK/vb_e27ceac8 untouched; pins and STOP rules. Apply corrections (keep _r1), then write ${B1}/AMENDMENT33_FIXED.md with final sha and time. Return pass=true only if no unresolved issue.`, { label: 'review-a33', phase: 'VB', schema: SCHEMA })
  if (!out.a33rev || !out.a33rev.pass) return { stoppedAt: 'Declare33', out }
  out.vb3 = await agent(`${RULES}
${CTX}
${UPDW}
TASK (V-B rerun per A33): verify the A33 fixation sha; pin the fixed hook and any changed tools (sha in LOG) before any data; run synthetic self-tests incl. the PID-reuse test; build the new V-B tree; then run from the start in OK2/vb2 exactly as amendments 24 §14.1 / 27 §6.2 / 29 §6.2 / 31 §4.4 / 32 / 33 define: ZI → OFF 14 → B1 41 (hooked), detached one at a time, BELOW_NORMAL; compute VB-I1..I7 and VB-M1..M9; recalculate. Write the canonical report ${B1}/k92_vb/K92_VB_REPORT.md (archive the STOP r1 first as K92_VB_REPORT_stop_r1.md; same for ${B1}/VB_REPORT.md) + same-bytes copy under OK2/vb2: plain summary, tables, what V-B can and cannot show (model-internal, not VISSIM; Ω only together with Ω-outside OUTW), the report-only chained-decision comparison with the action_token paths shown prominently, and what to watch in V-A. No verdict language. Return status (PASS only if every integrity check VB-I* holds), Korean summary (<= 30 lines), artifacts with sha256, open.`, { label: 'vb-a33', phase: 'VB', schema: SCHEMA })
  if (!out.vb3 || !out.vb3.pass) return { stoppedAt: 'VB3', out }
  out.vvb3 = await agent(`${RULES}
${CTX}
${UPDW}
TASK (VerifyVB 3): first write and PIN (sha in LOG) your own recalculation tools BEFORE reading any V-B output values (import nothing from the harness, the V-B driver, the hook or its recalculator); then independently recompute every VB-I and VB-M number in ${B1}/k92_vb/K92_VB_REPORT.md from raw outputs in OK2/vb2 (decision JSONs, hook k92_record.json files); re-run one short chain segment (2 decisions) detached in a separate scratch location and confirm bit-identity of decision outputs; check the method matched amendments 24/27/29/31/32/33 and that every claim follows from the numbers; apply corrections (keep _r1) with a change log. V-B report: ${JSON.stringify(out.vb3 || {}).slice(0, 4000)}. Write ${B1}/k92_vb/VERIFY_VB.md. Return status, Korean summary (<= 30 lines) suitable for relaying to the user, artifacts + sha256, open (incl. the go/no-go question for V-A closed loop, the push of claude/k92-b1-20261016, and the GB-7′ list amendment at the V-A freeze).`, { label: 'verify-vb-3', phase: 'VerifyVB', schema: SCHEMA })
  if (!out.vvb3 || !out.vvb3.pass) return { stoppedAt: 'VerifyVB3', out }
}

return { stoppedAt: null, out }
