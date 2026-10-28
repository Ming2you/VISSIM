export const meta = {
  name: 'sdmpc31-integrate',
  description: 'Integrate the six SDMPC-31 packages: apply patches, run the safe test suites and the v1 regression, review, fix, and prepare a local commit (no push) plus the G1 launch',
  phases: [
    { title: 'Integrate', detail: 'apply patches, tests, V1 regression, freeze dry-run, G1 recipe' },
    { title: 'Review', detail: 'independent integration review' },
    { title: 'Fix+Commit', detail: 'fixes, local commit prepared (no push)' },
  ],
}

const CONTEXT = `
## State
The six SDMPC-31 work packages are implemented, reviewed and fixed in the worktree W = D:\\VISSIM-merge\\sim3-n31 (branch claude/sdmpc-n31-20260924, based on f34b896). They are uncommitted; there are ~150 changed/new files.
- Plan: D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md (§7 verification ladder, §8 packages).
- Contract: W\\diagnostics\\sdmpc_n31_20260924\\CONTRACT.md.
- Package final reports: the "result" lines of C:\\Users\\TRLAB\\.claude\\projects\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\subagents\\workflows\\wf_5a6ec2d2-c55\\journal.jsonl. The last results are the final ones:
  - A: "## WP-A 검토 반영 결과"
  - B1: "WP-B1 리뷰의 필수 수정 3건은 모두 반영"
  - B2: "## WP-B2 리뷰 반영 최종 보고"
  - C: "WP-C 검토 반영을 끝냈습니다" (latest)
  - D: "# WP-D 리뷰 반영 최종 보고"
  - E: "WP-E(재핀) 최종 보고"
  Read their integration notes.

## Decisions (final)
- D10 / COM head delay = 1 s. Probe evidence: the head lags the SG readback by 10 steps after a COM write; the first departure is at 851.1 after a write at 850; this matches the old SimRes-1 frame advance. Apply B1's D10 patches. G1's D6 re-checks this against ground truth.
- Plant: the boundary family with the baseline FD. Decisions D-A..D-D as in the plan. VSL is wired; its zero derivative at 110 is known and deferred.

## Patches to apply, in this order (git apply --check each first)
All are in W\\diagnostics\\sdmpc_n31_20260924\\patches\\:
1. OC_B1.patch
2. OC_B1_D10.patch
3. AD_B1.patch
4. AD_C.patch
5. VBS_B1_SIGLOG.patch
6. VBS_B1_D10.patch
Preserve each file's line endings byte for byte. AD and LPR are CRLF; the VBS is LF.

## HARD SAFETY RULES
- Three stage-1 VISSIM runs are LIVE on this PC.
- NEVER run scripts\\tests\\test_b1a_watchdog_attempt_launch.py, the run_plant_fidelity_matrix tests, or anything that launches a run_real_world_single_watchdog*.ps1. Their Kill-Vissim kills EVERY VISSIM and cscript by name; it killed three live runs at 03:15. Before running any existing test file outside the new obs150/N31D/tools test folders, grep it for powershell/cscript/.ps1 launches and skip it if it has any.
- The WP-A VBS tests use a mock COM via cscript. They are allowed: they only start their own cscript.
- NEVER start VISSIM or create the Vissim COM object.
- NEVER touch D:\\VISSIM-merge\\sim3 (the live tree) or D:\\VISSIM_runs\\20260923_stage1.
- Do NOT push. A local commit is allowed only in the Fix+Commit phase, with:
  - GIT_AUTHOR_NAME/GIT_COMMITTER_NAME=Ming2you and GIT_AUTHOR_EMAIL/GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr, set as env vars only; no git config changes;
  - a message ending with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>".
- core.autocrlf=true on this PC. Stage files by explicit path. Never run git add -u --renormalize. Pinned inputs must stay byte-exact: check with the pinned-bytes tests, and by checking out the commit into a temporary git worktree and re-hashing every pin (then remove that temporary worktree).
- Python: C:\\Users\\TRLAB\\AppData\\Local\\Programs\\Python\\Python312\\python.exe with PYTHONUTF8=1 and PYTHONDONTWRITEBYTECODE=1. Run cscript from PowerShell.
`

phase('Integrate')
const integ = await agent(CONTEXT + `
## Your job: integrator
1. Apply the 6 patches in order and verify them. Resolve anything the package reports flagged for the integrator. For example:
   - the .gitattributes / nested .gitattributes for the C1 copies;
   - QUALIFICATION sentence + regenerate plant/config with make_plant_n31.py / make_config_n31.py and --check;
   - the stray untracked reports\\20260911_decision_runtime\\native_writer_pure_v1\\* files: find out which test produced them; do not commit them.
2. Run every safe test suite:
   - W\\diagnostics\\obs150_20260924\\tests
   - W\\diagnostics\\sdmpc_n31_20260924\\tests (also with N31_SLOW=1 where applicable)
   - W\\diagnostics\\sdmpc_n31_20260924\\tools\\tests
   - the WP-A runner tests
   - the SHO v1 regression files
   - the existing SDMPC unit tests that do not launch processes
   Report exact pass/fail counts. Pre-existing failures must be shown to fail at HEAD f34b896 too: use a temporary git worktree of HEAD for that, then remove it.
3. V1 regression (plan §7 V1): the old 21-cell path must reproduce objective 393.91612458424544 to the last digit on the saved 900 s state. Use the replay tooling in D:\\VISSIM-merge\\tools (replay_decision.ps1, make_replay_state.py) with -Root W. Find the saved state and tuning in D:\\VISSIM_runs\\20260923_sdmpc\\ and the handoff README D:\\VISSIM-merge\\sim3\\diagnostics\\sdmpc_native_20260923\\README.md (read-only).
4. The static safety check: no code path of the v2 launcher/PS1 can reach a name-based kill; the v2 path always passes NoGlobalKill / kills only its own PIDs.
5. Run the freeze tool and the launch plan in dry-run/plan-only form (no VISSIM). Write the exact G1 launch command:
   - dev seat, network sdmpc31_g1*.inpx, t=0..1350, ground-truth windows as the plan says;
   - expected wall time;
   - what the D6 comparator checks afterwards;
   - how D10 is re-checked.
   Also write the V5 9000 s launch command.
Return a precise report: patches, tests (counts), V1 result (digits), the safety check, the freeze dry-run, the G1 and V5 commands, and open issues.`, { label: 'integrate', phase: 'Integrate' })

phase('Review')
const review = await agent(CONTEXT + `
## Your job: independent integration review (read and run tests; do not edit W)
Integrator report:
${integ}

Verify the claims against the files:
- Patches applied cleanly, with line endings preserved.
- Tests pass: re-run the key suites.
- The V1 regression digits.
- The kill-safety of the v2 path.
- The v2 tuning/manifest/detectors/pins are self-consistent. Load the v2 config through the real loader.
- The G1 command matches the plan: seat rule, naming, env from the tuning only, ground-truth windows, NoGlobalKill.
- Anything that would make G1 fail on the first native run, e.g. the 5 kinds of native-only defects seen last time: JSON of ndarray; observation cadence mismatch; missing untracked pins; wrong reference files; stale pickles.
Return REQUIRED fixes (file:line, why) and optional notes, or "no required fixes".`, { label: 'review', phase: 'Review' })

phase('Fix+Commit')
const fin = await agent(CONTEXT + `
## Your job: apply the review, then prepare ONE local commit (no push)
Integrator report:
${integ}

Review:
${review}

1. Apply every correct REQUIRED fix (say which you reject and why) and rerun the affected tests.
2. Stage the implementation by explicit paths. Include:
   - the new modules and tests;
   - the N31D folder, including scenario/network/plant/config/receipts;
   - the C1 copies (only the files the plant pins);
   - the modified tracked files;
   - the tools under D:\\VISSIM-merge\\tools only if they live inside W. If they are outside W, list them in the report instead.
   Exclude:
   - files > 50 MB;
   - caches, __pycache__, run outputs;
   - the stray reports\\20260911_* files.
3. Commit locally with the identity env and the co-author line. Message: a concise summary of SDMPC-31 + obs150.
4. Verify:
   - git status is clean for everything staged;
   - a temporary worktree checkout of the new commit reproduces every pinned sha, then remove it;
   - the tests still pass from W.
Do NOT push.
5. Return:
   - the commit sha;
   - the file count;
   - excluded files with reasons;
   - the pin check;
   - the final test counts;
   - the final G1 and V5 launch commands;
   - the remaining open issues.`, { label: 'fix+commit', phase: 'Fix+Commit' })

return { integ, review, fin }
