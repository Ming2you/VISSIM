export const meta = {
  name: 'hybrid-alinea-duplicate-service-fix',
  description: 'Fix the hybrid test run failure at 3000 s (ALINEA commanded RM_C10490 green 3 whose measured service equals green 2 -> candidate_from_services non-unique): rule quantisation to unique-service greens within the +-2 s box, unit tests, replay of the failing 3000 s state, independent verify, local commit on the hybrid branch, re-freeze + PreflightOnly; no push, no launch',
  phases: [
    { title: 'Fix', detail: 'code + tests + replay + commit + freeze' },
    { title: 'Verify', detail: 'independent check' },
    { title: 'Fix2', detail: 'only if blocking' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = R + '/hybrid'
const WT = 'D:/VISSIM-merge/sim3-n31-hybrid'
const BR = 'claude/hybrid-rulefw-sdmpc-urban-20260929'
const RUN = 'D:/VISSIM_runs/20260929_hybrid/sdmpc31_v3c1_hybrid_s31'
const COMMON = `
CONTEXT (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line. Reports appended to ${OUT}/HYBRID_BUILD.md (§11 onwards); scratch under ${OUT}/fix_dup/. If the Write tool refuses a file, write it with Bash.
- The user's TEST run (hybrid: freeway Carlson PI VSL + ALINEA 8 meters as rule commands fixed inside SDMPC; urban SDMPC) was launched from FRZ D:/VISSIM-merge/frozen/sdmpc31_d34fd1aa_202609291357 (commit d34fd1a on ${BR}, worktree ${WT}) and FAILED at the 3000 s decision: ${RUN}/decisions_sdmpc31_v3c1_hybrid_s31/action_003000.error.txt -> physical_ramp_branches.py:360 candidate_from_services 'Service coordinate has no unique physical green: RM_C10490'. Cause: RM_C10490 uses the measured head-service table physical_ramp_head_service_veh_per_cycle {2:1.0, 3:1.0, 4:1.44, ...10:4.2}; ALINEA (rule, ±2 s box) moved 10490 from green 5 to 3; the SDMPC leader seed decodes services back to greens and green 3 has the same service as green 2. Offline builds only saw greens 6-9 for 10490.
- REQUIRED FIX (in the rule layer, evaluation/controllers/freeway_rule_hybrid.py or the ALINEA quantisation it reuses — do NOT change the shared decode in physical_ramp_branches.py): the rule must only command greens whose service value is unique in that meter's service table (for 10490: never 3), choosing within the ±2 s box the admissible green nearest to the ALINEA request (tie -> the higher green), and recording the substitution in metadata. Keep behaviour identical for every meter/green that was already unique (bit-identical decisions where no substitution happens). Key-absent path must stay bit-identical to 9ed2ef0 (the change must live only under the hybrid key).
- Tests: unit tests for duplicate-service greens (10490 at 5 -> request 3 => 4; at 4 -> request 2 => 2 allowed? (2 is unique only if 3 is excluded — define the admissible set as greens whose service is not shared with ANY other green except keep the lowest of a duplicate group? decide and justify: the physically meaningful choice is to keep the lowest green of a duplicate group (2) and drop the others (3)), history/receipt round-trip, and that all other meters are unchanged. Replay: offline hybrid decision replay of the failing state ${RUN}/decisions_sdmpc31_v3c1_hybrid_s31/state_003000.json with the real prior history (action_002850.json + .applied receipt) — must complete, 10490 green admissible, SDMPC completes; also re-replay the 2850 decision and check it is bit-identical to the recorded one (no substitution case).
- Then: local commit on ${BR} (explicit paths; GIT_AUTHOR_NAME/GIT_COMMITTER_NAME=Ming2you, GIT_AUTHOR_EMAIL/GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr; message ends with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"; never --renormalize; NO push), run D:/VISSIM-merge/tools/run_sdmpc_n31.ps1 -Freeze -PreflightOnly (starts no VISSIM) with the hybrid tuning, Name sdmpc31_v3c1_hybrid_s31b, Seed 31, SimPeriod 9000, Controller wu-link, RunsRoot D:/VISSIM_runs/20260929_hybrid, and return the new FRZ and the exact WMI launch command (same form as before with set "PYTHONHASHSEED=0"). Do not launch.
- SAFETY: user instruction: this is a TEST — do not damage any original material. Never modify D:/VISSIM-merge/tools/*, frozen/* (only the new FRZ is created by the freeze tool), sim3*, sim3-n31-v3c1, sim3-n31-urban-b2 or any existing run folder (the failed run folder is read-only evidence). Offline replays only, ONE at a time, BELOW_NORMAL, PYTHONHASHSEED=0, NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_hyb. Never start/kill VISSIM or cscript; never run watchdog/cscript/ps1 *tests*. Never open seed 37, RM arms, sealed seeds. An urban batch-2 workflow runs concurrently: keep CPU modest.
`
const RES = { type: 'object', properties: { summary_ko: { type: 'string' }, gates_ko: { type: 'string' }, commit: { type: 'string' }, frz: { type: 'string' }, launch_cmd: { type: 'string' }, stop: { type: 'boolean' } }, required: ['summary_ko', 'gates_ko'] }
phase('Fix')
const f = await agent(`${COMMON}\nTASK: implement the fix, tests, replays, commit, freeze + preflight as described.`, { label: 'fix', phase: 'Fix', schema: RES })
if (!f || f.stop) return { f }
phase('Verify')
const v = await agent(`${COMMON}\nFix report: ${JSON.stringify(f)}\nTASK (independent verifier): review the diff (new commit vs d34fd1a): the change is confined to the hybrid rule path; key-absent path untouched; the admissible-green rule is correct for 10490 and a no-op for all other meters (check every meter's service table for duplicates); re-run the failing 3000 s replay and the 2850 bit-identity replay yourself; check the commit (explicit paths, identity, no push), FREEZE/preflight lines (FREEZE_VERIFIED, network 2577209b, NETWORK_COPY_OK, PROVENANCE_OK, EXIT 0) and the launch command; confirm no original material changed (tools/*, other worktrees' HEAD/status, run folders). Report blocking issues (real defects only).`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
let f2 = null
if (v && v.blocking && v.blocking.length) {
  phase('Fix2')
  f2 = await agent(`${COMMON}\nVerifier blocking issues: ${JSON.stringify(v.blocking)}\nPrevious fix report: ${JSON.stringify(f)}\nTASK: fix what is real (new local commit, re-freeze + PreflightOnly), explain rejected items, return the final FRZ and launch command.`, { label: 'fix2', phase: 'Fix2', schema: RES })
}
return { f, v, f2 }
