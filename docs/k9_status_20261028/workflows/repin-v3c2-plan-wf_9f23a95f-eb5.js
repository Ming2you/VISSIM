export const meta = {
  name: 'repin-v3c2-plan',
  description: 'Plan (no code) the v3c1 -> v3c2 repin bundled with single-value VSL adoption, the 10490 service-uniqueness fix and the two pre-J1 defects; independent plan review',
  phases: [
    { title: 'Plan' },
    { title: 'Review' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = 'D:/VISSIM_runs/20260930_v3c2/reports/repin'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER DECISIONS: network v3c2 adopted (D:/VISSIM_runs/20260930_v3c2/reports/DECISION_v3c2_adopt.md; v3c2 = v3c1 + vehicle composition 14 'Freeway entry DSD110' on inputs 1098/1099; per-seed shas in V3C2_BUILD.md; NC fit seeds done). 2026-10-01: do the code REPIN v3c1 -> v3c2 NOW, SEPARATELY from urban batch 2 (batch 2 moves later after C3 v2 passes), bundled with: (1) the single-value VSL adoption bundle (user decision 09-28: DSD 81/91/101 for commands 80/90/100 as single-value compliance, command -> DSD mapping, plant VSL law L2 = Carlson A 1.33 / E 0.87 with level scales m_v 0.901/0.812/0.723, see memory C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory/vissim-vsl-fixed-dsd-20260928.md and D:/VISSIM_runs/20260928_n1f_vsl*/reports; N1F used DSD 91 = 90-92 etc.), (2) the RM_C10490 head-service uniqueness fix (deployed table {2:1.0, 3:1.0} non-unique; the SDMPC path can stop in physical_ramp_branches decode; the fix exists only on the hybrid branch claude/hybrid-rulefw-sdmpc-urban-20260929 commit 92fa4b8 under the hybrid key - it must become a general fix), (3) pre-J1 defect: vendor/NumSim-mine/src/models/state.py:1306 set-iteration float sum depends on PYTHONHASHSEED (sort it), (4) pre-J1 defect: make_replay_state_v2.py:234-242 action_contract requires all VSL = 110 (change to 'member of the allowed set').
- Base: D:/VISSIM-merge/sim3-n31-v3c1 branch claude/repin-v3c1-20260928 (HEAD 9ed2ef0, pushed). The v3c1 repin is the template: D:/VISSIM_runs/20260927_v3c1/reports/REPIN_PLAN.md + repin_inventory.json (48 items), commit 5323faa (111 paths), freeze/preflight, R-obs run, P10 checks (${SP}/v3c1-p10). Worklog D:/VISSIM-merge/sim3-n31-v3c1/diagnostics/worklog_20260927_29/.
- Open items that the plan must address: adding DSD 81/91/101 definitions (and any VBS mapping) changes the network file -> decide whether they are folded into v3c2 before pinning (and how to prove NC trajectories are unaffected, e.g. one NC seed byte identity), or a v3c3; the VBS writes DesSpeedDistr(cls)=CLng(speed) today; where the mapping lives (adapter action CSV dsd_no vs VBS); keeping L1 selectable for distribution compliance; the ramp arrival forecast re-derivation on v3c2 fit seeds; beta/route sources; obs150 detector build sha; control_area_membership drift; the codex review's latent defects (state_response index order - only if needed; silent-ignore install check - propose). Also F10 (inlet speed boundary) is NOT part of this repin (separate decision pending) and batch-2 keys stay absent.
- After the code repin the plan must list the runs needed (R-obs v3c2 s31 no-control + obs150; RM arms s31/s41 + sealed s37 on v3c2; any NC identity run), the checks (T5 decision replay identity, L2 all-110 identity, P10-like pair checks, VSL < 110 write path via the single-value mapping), and the freeze/preflight/WMI launch steps (main session launches; at most 4 VISSIM).
- HARD RULES: PLAN ONLY - no code changes, no commits, no network edits, no VISSIM. Read-only everywhere; write only under ${OUT}. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results.
`
const PL = { type: 'object', properties: { plan_path: { type: 'string' }, inventory_path: { type: 'string' }, summary: { type: 'string' }, user_decisions: { type: 'array', items: { type: 'string' } } }, required: ['plan_path', 'inventory_path', 'summary', 'user_decisions'] }
const RV = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'blocking', 'nonblocking'] }

phase('Plan')
const plan = await agent(CTX + `
YOUR TASK: write ${OUT}/REPIN_V3C2_PLAN.md and ${OUT}/repin_v3c2_inventory.json (every pin/constant/derived artefact that references the network or VSL law, with file:line, current value, new value or derivation, and the test that proves it). Structure: 0 summary; 1 scope and what is NOT included; 2 network side (v3c2 + DSD question); 3 code side per item (repin constants, single-value VSL mapping + L2, 10490 fix generalised, state.py sort, replay action_contract); 4 derived evidence to regenerate on v3c2 fit seeds; 5 tests and identity gates (pre-declared); 6 runs and launch order; 7 risks; 8 user decisions. Estimate effort and wall time.`, { label: 'plan', phase: 'Plan', schema: PL })

phase('Review')
const rev = await agent(CTX + `
YOUR TASK: ADVERSARIAL REVIEW of ${plan ? plan.plan_path : '(plan failed)'} and its inventory. Grep the code base for every network sha, network-derived constant, VSL law parameter, DSD/VSL mapping and 110-only assumption and check the inventory is complete (compare with the v3c1 repin inventory and commit 5323faa). Check the 10490 fix generalisation does not change behaviour where tables are unique, the state.py sort changes numbers only in the last ulps (and what that does to T5 identity against the recorded v3c1 R-obs), and that the single-value mapping cannot silently fall back to distribution DSDs. Write ${OUT}/REPIN_V3C2_PLAN_REVIEW.md with blocking / nonblocking.`, { label: 'review', phase: 'Review', schema: RV })

return { plan, rev }
