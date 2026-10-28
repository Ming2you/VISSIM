export const meta = {
  name: 'urban-b1-sc7-fix',
  description: 'Batch-1 follow-up: remove the stale non-existence declaration of SC7 E/E_SC16 -> N_SC11, serve it in the phase of its real head (p4), apply relFlow; regenerate pins, test, verify',
  phases: [
    { title: 'Implement', detail: 'declaration + phase + beta regeneration + tests + T1/T3 spot checks' },
    { title: 'Verify', detail: 'adversarial check' },
    { title: 'Settle', detail: 'address findings' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const W = 'D:/VISSIM-merge/sim3-n31-urban'
const COMMON = `
CONTEXT (absolute paths, forward slashes)
- Worktree ${W}, branch claude/urban-fix-v3b-20260925 (9152821 + UNCOMMITTED batch-1 work U1/U2/U3 that passed review; do not revert any of it). Batch-1 reports: ${R}/urban-b1/wf_result_part1.txt and wf_result_part2.txt; evidence ${R}/urban-b1d/ (t1_indep.py/json, t3_arms.py/json, capture/, paths/). Candidate S1 tuning: diagnostics/sdmpc_n31_20260924/config_n31_v2_urban_b1_u1u3.json produced by make_config_n31.py --urban-batch1 --components U1,U3 (sha pins in make_config_n31.py URBAN_B1_*).
- Problem (user decision 2026-09-26: fix it): SC7_E_to_N_SC11 and SC7_E_SC16_to_N_SC11 have a physical connector path (10332 -> 1220008701 -> 10334 -> SC11) and relFlow 63 (10333 carries 84), i.e. relFlow-rule value 0.429/0.571, FZP realised about 0.22 to N_SC11. The derivation (scripts/derive_routing_beta_physical.py DECLARED_NONEXISTENT_PENDING, status pending_user_decision) keeps them 0 because a runtime non-existence declaration lists them; the model serves this turn in SC7 p3 which has no green, while the real signal head 140101 is SG 7-1 which belongs to plan phase p4. User decision: correct the declaration to v3b, move the movement(s) to the phase of their real head (p4), and apply the relFlow value.
- Rules (binding): beta values = 0 only without a physical path, otherwise relFlow; every switch is a config key (no env/getattr gates); absent new keys -> bit-identical runtime to the base tuning; superseded paths isolated, not left behind flags; SC2001 corridor NC13 values and SC104 S_SC106 config defaults stay as they are (user decision) - just keep them documented.
- Python: C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe; env threads 1, PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, NUMBA_CACHE_DIR = a SHORT path (e.g. C:/Users/TRLAB/AppData/Local/Temp/nbc_sc7; long scratch paths broke tangent workers), PYTHONPATH="C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc;C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc-numba;${W}". Test suites: copy ${R}/urban-b1d/run_tests.sh (or the batch-1 runner used there) - suites n31, tools, obs, pyt; generator checks as in batch 1.
- Live VISSIM no-control runs (D:/VISSIM_runs/20260925_v3b/s{43,47,53}_v3bnc) and another agent editing D:/VISSIM-merge/sim3-n31 (main worktree): do not touch either, nor D:/VISSIM-merge/frozen/*. Never start VISSIM; never run watchdog/cscript/ps1 TESTS (forbidden: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). replay_decision_n31.ps1 is allowed. One heavy process at a time.
- Do not commit. Scratch under ${R}/urban-sc7/. Text in Korean; mark numbers [실행]/[읽음].
`
const IMPL = {
  type: 'object',
  properties: {
    where_declared_ko: { type: 'string' },
    changes_ko: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    new_pins_ko: { type: 'string' },
    t1_ko: { type: 'string' },
    t3_ko: { type: 'string' },
    tests_ko: { type: 'string' },
    bit_identity_ko: { type: 'string' },
    risks_ko: { type: 'string' },
  },
  required: ['where_declared_ko', 'changes_ko', 'files', 'new_pins_ko', 't1_ko', 't3_ko', 'tests_ko', 'bit_identity_ko', 'risks_ko'],
}
phase('Implement')
const impl = await agent(`${COMMON}
TASK:
1. Find every place that declares these two movements non-existent or assigns them to p3 (runtime declarations, config tables, phase authority / apply_movement_phase_correction, scenario declarations under N31D/scenario/, derivation lists). Verify from the v3b inpx: signal head 140101 (lane, SG 7-1), connector 10332 lanes, and SC7's signal program (.sig) to confirm SG 7-1 is served in plan phase p4 (and that no other movement's phase changes).
2. Implement the correction as a config-keyed change active in the batch-1 candidate tunings only (absent key -> bit-identical base): the two movements exist, belong to the phase of their real head, and get the relFlow value from the regenerated routing_v3b2 table (remove them from DECLARED_NONEXISTENT_PENDING; keep the derivation failing on any other declaration/physics mismatch).
3. Regenerate the beta table, the route-queue attribution and unsignalized evidence if affected, the candidate configs (--urban-batch1 and --components U1,U3), all sha pins; update tests (reproducibility, the SC7 case: values 0.429/0.571 in the table, phase p4 at runtime, no starving phase, p3/p4 green accounting unchanged for other movements) and the guide's batch-1 section.
4. Checks: T1 on SC7 E and E_SC16 with the independent judge (${R}/urban-b1d/t1_indep.py) - report before/after vs FZP (note: relFlow 0.429 vs FZP 0.22 may still fail +-0.05; that is accepted by the rule, report it); T3 one-step on the 61 R-obs-b states for the U1+U3 candidate vs the pre-fix U1+U3 (same method as ${R}/urban-b1d/t3_arms.py) - especially SC7 approaches and SC11; the three prediction paths equality at T2700; all suites + generator checks; base-tuning replays of a few R-obs-b states IDENTICAL.`, { label: 'implement', phase: 'Implement', schema: IMPL })

phase('Verify')
const verify = await agent(`${COMMON}
Implementer report: ${JSON.stringify(impl)}
You are an adversarial verifier. Try to refute: that SG 7-1 / head 140101 is really p4 in SC7's program at v3b (read the .sig and the phase mapping yourself); that nothing else moved phase or value (diff the regenerated table/configs against the pre-fix versions and list every changed movement); that the absent-key path is bit-identical; that no phase starves and green accounting of p3/p4 is consistent across the exact/continuous/route-bins paths; that pins and --check pass. Run what you need (read-only except scratch). Return findings (only those that hold) with evidence.`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { ok: { type: 'boolean' }, findings_ko: { type: 'string' } }, required: ['ok', 'findings_ko'] } })

phase('Settle')
const settle = await agent(`${COMMON}
Implementer report: ${JSON.stringify(impl)}
Verifier: ${JSON.stringify(verify)}
TASK: re-check each verifier finding; fix those that hold (say which you reject and why); re-run affected tests/checks. Final Korean report + the complete list of files a batch-1 commit must now contain (all batch-1 files, tracked + new, including this follow-up), and the S1 tuning file name + sha.`, { label: 'settle', phase: 'Settle', schema: { type: 'object', properties: { report_ko: { type: 'string' }, commit_files: { type: 'array', items: { type: 'string' } }, s1_tuning: { type: 'string' }, s1_tuning_sha: { type: 'string' }, ready: { type: 'boolean' } }, required: ['report_ko', 'commit_files', 's1_tuning', 's1_tuning_sha', 'ready'] } })

return { impl, verify, settle }