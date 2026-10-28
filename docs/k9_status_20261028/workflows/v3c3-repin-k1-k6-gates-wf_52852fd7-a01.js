export const meta = {
  name: 'v3c3-repin-k1-k6-gates',
  description: 'Implement repin plan K1-K6 (defect fixes on the v3c1 base) in sim3-n31-v3c3, commit locally, run GA gates on v3c1 data in a separate K6-pinned worktree, independent verification',
  phases: [
    { title: 'Implement' },
    { title: 'Gates' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const PLAN = 'D:/VISSIM_runs/20260930_v3c2/reports/repin'
const OUT = 'D:/VISSIM_runs/20261001_v3c3/reports/k1k6'
const W = 'D:/VISSIM-merge/sim3-n31-v3c3'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER APPROVED (2026-10-01) the repin plan ${PLAN}/REPIN_V3C2_PLAN.md (sha d4b70c02) + inventory repin_v3c2_inventory.json with ALL recommended values U1-U12, and the plan review ${PLAN}/REPIN_V3C2_PLAN_REVIEW.md: blocking B1-B3 MUST be applied (B1 enumerate expected run_provenance changes - FRZ/worktree paths, imported module paths/shas incl. src.models.state, numsim_src_sha256, execution_fingerprint - and positively check they point to the K6 tree and the K1 state.py; B2 re-aim the T5/P10 harnesses (${SP}/v3c1-p10/t5/t5_common.py:9-14, t5_chain_b.py:144) at the K6 tree/FRZ and require replay provenance to point there; B3 run GA replays from a SECOND worktree detached at the K6 commit, never from the editing worktree), and the nonblocking notes N1-N15 where they concern K1-K6 (N1 do the old-tree PYTHONHASHSEED 0 vs 2 A/B before GA; N2 ulp wording; N3 '10490: lowest admissible green' rule, list(items()) order tests, rejection check on the lane_plant_runtime.py:482-486 install path; N4 DECISIONS_FAILED=0 and ERROR=0 as a standing gate; N14 keep compare(out_dir, vsl_expected) positional semantics).
- SCOPE OF THIS WORKFLOW: K1-K6 only (defect fixes and checks on the v3c1 base; no network repin, no VSL law change - that is K7, done later after the v3c3 network shas exist). K items per the plan: state.py:1306 sorted sum; replay action_contract 'member of allowed set'; RM_C10490 head-service normalisation generalised (port the idea of hybrid commit 92fa4b8 on branch claude/hybrid-rulefw-sdmpc-urban-20260929, but as a general fix, not under the hybrid key); E2 silent-ignore install check in _load_sources_v2; plus whatever else the plan lists as K1-K6. Key-absent / unique-table behaviour must stay bit-identical except the declared ulp-level effects.
- Worktree W = ${W} (branch claude/repin-v3c3-20261001 from claude/repin-v3c1-20260928 @ 9ed2ef0, clean). Local commits only in W with explicit paths, identity GIT_AUTHOR_NAME=GIT_COMMITTER_NAME=Ming2you, GIT_AUTHOR_EMAIL=GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr, message ending "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; no --renormalize; NO PUSH in this workflow (push happens after K7 gates).
- Data: v3c1 R-obs D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31 (read-only), P10 artefacts ${SP}/v3c1-p10, hybrid failure states D:/VISSIM_runs/20260929_hybrid (read-only) for the GA-4 10490 positive control.
- HARD RULES: write only in W, the K6 gate worktree you create (git worktree add --detach D:/VISSIM-merge/sim3-n31-v3c3-k6gate <K6 commit>) and ${OUT}. Do not touch other worktrees (sim3-n31-v3c1, sim3-n31-urban-b2, sim3-n31-f10f11, sim3-n31-termcost, sim3-n31-hybrid) or frozen/*; you may create a NEW freeze of the K6 commit via run_sdmpc_n31.ps1 -Freeze -PreflightOnly only if a gate needs a FRZ (never modify existing ones). No VISSIM start/kill. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 data. Replays one at a time, BELOW_NORMAL.
`
const IS = { type: 'object', properties: { report_path: { type: 'string' }, commits: { type: 'string' }, tests: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'commits', 'tests', 'stop', 'stop_reason'] }
const GS = { type: 'object', properties: { report_path: { type: 'string' }, gates: { type: 'string' }, all_pass: { type: 'boolean' } }, required: ['report_path', 'gates', 'all_pass'] }
const VS = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Implement')
const im = await agent(CTX + `
YOUR STAGE: IMPLEMENT K1-K6 + unit tests (write ${OUT}/K1K6_IMPLEMENT.md). Before coding, write ${OUT}/GA_PREDECLARATION.md (+ .sha256) with the GA gates exactly (GA-1 R-obs 61 decision replays, GA-2 hash-seed A/B incl. the N1 old-tree A/B, GA-3 T5-B counterfactual 5 decisions, GA-4 hybrid 3000 s 10490 positive control, standing DECISIONS_FAILED/ERROR gate), the enumerated expected provenance/ulp differences (B1, N2), and the harness re-aiming (B2). Then implement each K item as a separate local commit in W with tests; run the relevant existing suites (not the forbidden ones). stop=true if an item cannot be done without changing behaviour beyond the declared effects.`, { label: 'implement-k1k6', phase: 'Implement', schema: IS })
if (!im || im.stop) { return { im, stopped: 'K1-K6 implementation stopped' } }

phase('Gates')
const ga = await agent(CTX + `
YOUR STAGE: RUN THE GA GATES exactly as predeclared (${OUT}/GA_PREDECLARATION.md; verify its sha first). Commits: ${im.commits}. Create the detached K6 gate worktree, re-aim the harnesses (B2), run GA-1..GA-4 and the N1 A/B one at a time, record provenance checks (B1), and write ${OUT}/GA_RESULTS.md with a per-gate verdict table. all_pass=false if any gate fails (do not 'fix and retry' silently; report).`, { label: 'ga-gates', phase: 'Gates', schema: GS })

phase('Verify')
const ve = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only; own code under ${OUT}/verify; write ${OUT}/VERIFY.md). Inputs: ${im.report_path}, ${ga ? ga.report_path : '(gates failed)'}, GA_PREDECLARATION.md. Review each K commit diff (guards, unique-table identity, lowest-admissible-green rule, sorted-sum scope, action_contract semantics, install check), re-run one GA-1 replay and the GA-4 positive control yourself from the K6 gate worktree, check provenance points to K6, and check verdicts follow the predeclaration.`, { label: 'verify-k1k6', phase: 'Verify', schema: VS })

return { im, ga, ve }
