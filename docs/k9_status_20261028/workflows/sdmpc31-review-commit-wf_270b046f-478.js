export const meta = {
  name: 'sdmpc31-review-commit',
  description: 'Independent review of the SDMPC-31 integration (incl. the unreviewed D6 edits), apply fixes and two small decisions, and make one local commit (no push)',
  phases: [
    { title: 'Review', detail: 'independent integration review' },
    { title: 'Fix+Commit', detail: 'fixes + local commit, pin check' },
  ],
}

const CONTEXT = `
## State
The six SDMPC-31 work packages are implemented and integrated in the worktree W = D:\\VISSIM-merge\\sim3-n31 (branch claude/sdmpc-n31-20260924, HEAD f34b896). Nothing is committed yet.
The integrator's full report is in C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\integ\\INTEGRATOR_REPORT.md. READ IT FIRST: patches applied, test counts, V1 regression, kill-safety, freeze dry-run, G1/V5 commands, open issues.
- Plan: D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md
- Contract: W\\diagnostics\\sdmpc_n31_20260924\\CONTRACT.md
- Package reports: result lines in C:\\Users\\TRLAB\\.claude\\projects\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\subagents\\workflows\\wf_5a6ec2d2-c55\\journal.jsonl

## Decisions (final, from the user or following the recommended default)
- D10 / COM head delay = 1 s.
- Plant: the boundary family with the baseline FD. D-A..D-D as in the plan. VSL is wired; its zero derivative at 110 is known and deferred.
- C12 port_profile v2: select = interp. Off-ramp dwell times are reconstructed within the 5 s FZP interval, which matches b120 within ±5%.
- RW_ALLOWED_VSL_SPEEDS on the v2 path = {60, 80, 110}. Drop 115: the v2 network has no 115 distribution, and the plant/stage-1 VSL set is 60/80/110. Change it only in the v2 scenario runner config, re-pin whatever pins it, and regenerate with --check.
- V1 reference: record BOTH reproduced values in the evidence doc:
  - 393.9163955132781 at the HEAD default cap margin (100, 100);
  - 393.91612458424544 at margin 0 (== native action_000900.csv bytes).

## HARD SAFETY RULES
- Three stage-1 VISSIM runs are LIVE on this PC.
- NEVER run scripts\\tests\\test_b1a_watchdog_attempt_launch.py, the run_plant_fidelity_matrix tests, test_runner_ps1_obs150.py, test_tools_integration::...real_watchdog..., test_native_vbs_clock.py, or ANY test/script that launches powershell/cscript/.ps1 watchdogs. Their Kill-Vissim kills every VISSIM and cscript by name; one did at 03:15.
- The WP-A VBS mock tests (cscript on the mock) are allowed.
- NEVER start VISSIM or create the Vissim COM object.
- NEVER touch D:\\VISSIM-merge\\sim3 or D:\\VISSIM_runs\\20260923_stage1.
- Do NOT push.
- core.autocrlf=true here:
  - stage by explicit path;
  - never run git add -u --renormalize;
  - preserve line endings byte for byte (AD/VBS are LF; SHO is mixed; LPR is CRLF — check each against HEAD);
  - pinned inputs must stay byte-exact.
- Python: C:\\Users\\TRLAB\\AppData\\Local\\Programs\\Python\\Python312\\python.exe with PYTHONUTF8=1 and PYTHONDONTWRITEBYTECODE=1.
`

phase('Review')
const review = await agent(CONTEXT + `
## Your job: independent integration review (read, and re-run the safe tests; do not edit W)
Verify the integrator's claims against the files:
- patches applied, with line endings;
- the test counts: re-run the key suites;
- kill-safety of the v2 path;
- v2 tuning/manifest/detectors/pins self-consistency, through the real loader.
- The G1 command matches the plan: seat rule, naming, env from the tuning only, ground-truth windows 750:900,1050:1200, NoGlobalKill, MaxAttempts 1.
Review carefully the integrator's OWN edits to the D6 comparator, which nobody has reviewed yet: N31D\\tools\\obs150_verify_gt.py SignalTruth, D10Probe, the d10 item, and --com-head-delay. A wrong comparator would give a false PASS or FAIL at G1.
Look for anything that would break the first native G1 run. Last time five native-only defects appeared: JSON of ndarray; observation cadence mismatch; missing untracked pins; wrong reference files; stale pickles. Also check that the PreflightOnly path of the watchdog is exercised statically. Do NOT run it.
Return REQUIRED fixes (file:line, why, how) and optional notes, or "no required fixes".`, { label: 'review', phase: 'Review' })

phase('Fix+Commit')
const fin = await agent(CONTEXT + `
## Your job: apply the review and the two small decisions, then make ONE local commit (no push)
Review:
${review}

1. Apply every correct REQUIRED fix (list rejected ones with reasons). Apply the C12 = interp and VSL {60,80,110} decisions. Regenerate whatever those change, with --check. Rerun the affected tests and the full safe suites. Report exact counts.
2. Record the V1 values in D:\\VISSIM-merge\\evidence\\SDMPC31_INTEGRATION_20260924.md (new file). Put there a concise record of the integration: patches, tests, V1, kill-safety, decisions, open issues.
3. Stage by explicit paths: the implementation files listed in the integrator report §7.5, plus whatever the fixes add.
   Exclude:
   - files > 50 MB;
   - caches, __pycache__, __tangentcache__, .review-fixtures;
   - run outputs;
   - the stray reports\\20260911_* files.
   Commit with these env vars only:
   - GIT_AUTHOR_NAME=Ming2you, GIT_AUTHOR_EMAIL=alsrjsrb1915@snu.ac.kr
   - GIT_COMMITTER_NAME=Ming2you, GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr
   Message: a concise summary of SDMPC-31 + obs150 (exact 150 s observation, 31-cell plant on v2, runner event mode at SimRes 10, kill-safety), ending with the line "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
4. Verify:
   - git status is clean for the staged paths;
   - check out the new commit into a temporary git worktree and re-hash every pin of plant_n31_v2.json, config_n31_v2.json, the detector CSV, the scenario pack and the network copy (REPIN verify), then remove that worktree;
   - the safe tests still pass from W.
   Do NOT push.
5. Return:
   - the commit sha and file count;
   - excluded files with reasons;
   - the pin-check result;
   - the final test counts;
   - the final G1 and V5 launch commands;
   - open issues, split into ones that block G1 and ones that do not.`, { label: 'fix+commit', phase: 'Fix+Commit' })

return { review, fin }
