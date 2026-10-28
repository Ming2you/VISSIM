export const meta = {
  name: 'v3c1-repin-implementation',
  description: 'Implement the user-approved v3c1 re-pin (REPIN_PLAN.md P3-P8: new worktree/branch, RA-1 extraction, repin tool enumeration + 1083 guard allowlist, urban re-derivations, plant chain incl. VSL L1 + {80..110}, tests, preflight/configure-check) and verify independently; commit/push/freeze/R-obs launch are done by the main session afterwards',
  phases: [
    { title: 'Implement', detail: 'P3-P8' },
    { title: 'Verify', detail: 'independent review, tests' },
    { title: 'Fix', detail: 'repair loop' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const V1 = 'D:/VISSIM_runs/20260927_v3c1'
const WT = 'D:/VISSIM-merge/sim3-n31-v3c1'
const COMMON = `
CONTEXT (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line.
- USER APPROVAL 2026-09-28 (binding): the full v3c1 re-pin of ${V1}/reports/REPIN_PLAN.md (§0 items (a)-(f), §3 (가)-(바), §5 VSL L1 A=0.94 E=1.44 alpha=0 + action set {80,90,100,110}, §6 steps P3-P8, and the §8 recommendations D1-D7: new beta source files movement_beta_routing_v3c1{,_2}_<date>.json with a new source key and the v3b key removed from the tree; 1083 guard allowlist = decision 1160 only; NA-3 explicit 1165 -> SC1|N_SC101; NA-9 optional completions 1162:1, 1164:1, 1165:1; U1 area-contract old copies left as is and recorded; new files named *_v3c1_*, v3b files removed from the tree (isolated, not flagged); L1 used as a carried-over prior with the qualification stated). Inventory: ${V1}/reports/repin_inventory.json; drift baseline and previews: ${R}/net-v3c/v3c1/repin_drift/. v3c1 passed the 5-seed gates (${V1}/reports/gates_5seed/GATES_5SEED.md): network shas s31 2577209b, s41 226baa37, s43 b8e7cf1f, s47 ec0cd81d, s53 385f40da, s37 3eb06c63 (held out: never use its FZP for any derivation).
- Worktree/branch: git -C D:/VISSIM-merge/sim3-n31-urban worktree add ${WT} -b claude/repin-v3c1-20260928 cf3ce37 (P3). Work only in ${WT}. DO NOT commit, push, freeze or launch anything — the main session does commit/push/freeze/preflight/R-obs launch after verification. Leave the changes uncommitted, and produce the exact list of files to add/remove (explicit paths; never --renormalize) and a proposed commit message.
- Never modify D:/VISSIM-merge/frozen/*, D:/VISSIM-merge/sim3-n31, D:/VISSIM-merge/sim3-n31-urban, D:/VISSIM-merge/sim3-n31-urban-b2 (another workflow implements urban batch 2 there) or any D:/VISSIM_runs folder except new outputs under ${V1}/repin/ if needed. No VISSIM/cscript/fast_nc_run -Execute; never run watchdog/cscript/ps1 *tests* (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). FZP extraction one at a time, BELOW_NORMAL (typed ctypes + read-back). Four VISSIM runs (N1 B5) and the batch-2 workflow run concurrently: keep CPU modest.
- Rules: every switch a config key; absent = bit-identical where applicable; superseded code isolated; no env/getattr gates.
`
const I = { type: 'object', properties: { summary_ko: { type: 'string' }, checks_ko: { type: 'string' }, files_add: { type: 'array', items: { type: 'string' } }, files_remove: { type: 'array', items: { type: 'string' } }, commit_message: { type: 'string' }, robs_launch_ko: { type: 'string' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'checks_ko', 'files_add', 'commit_message', 'robs_launch_ko'] }
phase('Implement')
let im = await agent(`${COMMON}\nTASK: execute REPIN_PLAN §6 P3-P8 in order (P3 worktree; P4 RA-1 extraction on v3c1 fit seeds; P5 C-4 enumeration table + NA-7 rule + VSL_SPEEDS, C-11 runtime guard allowlist, tests, repin_scenario_v2.py build + verify; P6 hand records and the urban derivation chain in the stated order, diffing against the v3b outputs and allowing only the §4.5 list; P7 the plant chain incl. reference (VSL L1), runner VBS vsl set {80..110}, plant manifest, configs x3, C-10; P8 the n31 test suites (except forbidden tests), scripts/preflight_tuning_paths.py, repin_scenario_v2.py configure-check in a temp folder, docs). Stop and report at the first failing check. Write ${WT}/diagnostics/sdmpc_n31_20260924/REPIN_V3C1_REPORT.md and return: checks, the explicit file lists to git add / git rm, a commit message, and the exact R-obs launch procedure (freeze_worktree.ps1, run_sdmpc_n31.ps1 -Freeze -PreflightOnly, then the WMI launch line for no-control + obs150 on v3c1 s31 into a new runs root, like the v3b R-obs-b run sdmpc31_v3b_nc_s31b).`, { label: 'implement', phase: 'Implement', schema: I })
for (let round = 0; round < 3; round++) {
  phase('Verify')
  const v = await agent(`${COMMON}\nImplementation report: ${JSON.stringify(im)}\nTASK (independent verifier): review git diff in ${WT} vs cf3ce37 against the inventory (every item done, nothing extra), re-run repin_scenario_v2.py verify, the preflight and configure-check, the n31 suites (allowed ones) and the VSL T9 checks yourself; check every v3b network sha is gone from live pins (grep), the new beta table reproduces the expected v3c1 beta of the v3c1 receipt (V1, V3-V7), the 1083 allowlist is exactly {1160}, s37 was never used, and the R-obs launch procedure matches the v3b R-obs-b recipe. Report blocking issues only for things that would break R-obs or later closed-loop runs or violate the approval.`, { label: `verify:r${round}`, phase: 'Verify', schema: { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
  const blocking = (v && v.blocking) || []
  log(`round ${round}: ${blocking.length} blocking`)
  if (!blocking.length) return { im, v }
  if (round === 2) return { im, v, stopped: true }
  phase('Fix')
  im = await agent(`${COMMON}\nImplementation report: ${JSON.stringify(im)}\nBlocking issues: ${JSON.stringify(blocking)}\nTASK: fix what is real in ${WT}, re-run the affected checks, explain rejected ones, return the updated report (same fields).`, { label: `fix:r${round}`, phase: 'Fix', schema: I })
}
