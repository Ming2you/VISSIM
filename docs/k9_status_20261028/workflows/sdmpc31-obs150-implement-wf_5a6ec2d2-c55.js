export const meta = {
  name: 'sdmpc31-obs150-implement',
  description: 'Implement SDMPC-31 with exact 150 s observation on v2: contract first, then six work packages in parallel, each independently reviewed and fixed',
  phases: [
    { title: 'Contract', detail: 'WP-0: CONTRACT.md, obs150_contract.py, .gitattributes' },
    { title: 'Implement', detail: 'WP-A runner, WP-B1 capture/head, WP-B2 lane/detectors, WP-C 31-cell wiring, WP-E repin, WP-D tools' },
    { title: 'Review', detail: 'independent review per package' },
    { title: 'Fix', detail: 'apply required fixes, rerun tests' },
  ],
}

const CONTEXT = `
## What we are building
The plan is final and approved by the user. Implement it exactly:
- D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md — read §0, §1 (the contract), your package's section, §7 (the verification ladder) and §8 (work packages and file ownership).
Background, read as needed:
- D:\\VISSIM-merge\\evidence\\OBS150_DESIGN_20260923.md
- D:\\VISSIM-merge\\evidence\\OBS150_PROBE_20260924.md — COM facts from a real VISSIM run.
- D:\\VISSIM-merge\\evidence\\SDMPC_N31_PLAN_20260923.md
- D:\\VISSIM-merge\\evidence\\PLANT_CHOICE_20260924.md
The probe scripts and data are reusable:
- scripts: D:\\VISSIM-merge\\tools\\obs150_probe\\ — probe.vbs COM idioms, a mock COM for VBS tests in test\\mock_vissim.vbs, check_probe.py parsers;
- data: D:\\VISSIM_runs\\20260923_obs150\\probe\\run_20260924_000152\\ — .mer, gt_*.csv, snapshots, com_log.

## User decisions (final)
- Plant: the boundary family with the baseline FD, from B110\\train_s31_v2nc (fit_v1 + boundary_literature_v1). No FD refit.
- D-A: the 9000 s SDMPC run (V5) goes first. The paired no-control (V4) runs after it, or concurrently when a seat frees.
- D-B: carry the 7 prior-calibrated pack entries over with receipts, and mark prior_mismatch in provenance. Refit after the first 9000 s run.
- D-C: (b). The 10643 lane split uses the previous window's observed per-lane shares, held over the horizon.
- D-D: (a). Keep the Edie-average meaning of on-ramp far link_volume. Exact counts go to 'derived' for audit only.
- Exact over approximate. One read per 150 s decision; no per-second stepping.
- Supersede, don't flag: the new path is canonical. The old 21-cell/SimRes-1 path stays selectable by the ONE tuning key only (plan §1.1).

## Where to work
- Worktree W = D:\\VISSIM-merge\\sim3-n31 (git worktree, branch claude/sdmpc-n31-20260924). Edit ONLY the files your package owns (plan §8).
- The adapter vissim_stackelberg_adapter.py (AD) is shared. Do NOT edit it directly. Write your AD change as a unified diff at W\\diagnostics\\sdmpc_n31_20260924\\patches\\AD_<package>.patch, limited to your line range:
  - B1: :8053-8081
  - C: :9401-9424
  The integrator applies them.
- NEVER touch D:\\VISSIM-merge\\sim3; it is the live tree used by running stage-1 runs and calibration.
- Read-only: D:\\VISSIM_runs\\*, and the calibration workspace B110 = D:\\VISSIM-merge\\sim3\\diagnostics\\demand_sweep\\user_native_20260914\\metanet_calibration_v1\\res10_b110_20260923. Copy what you need INTO W as the plan says.
- NEVER start VISSIM or create the Vissim COM object. Four licensed runs are live, and the native G1 run is launched later by the main session.
- Do NOT git commit or push. Leave changes uncommitted.
- Python: C:\\Users\\TRLAB\\AppData\\Local\\Programs\\Python\\Python312\\python.exe, with PYTHONUTF8=1 and PYTHONDONTWRITEBYTECODE=1. Check whether pytest is installed; otherwise use unittest.
- cscript for VBS compile checks and mock tests: run it from PowerShell, never from Git Bash. The worktree path has no Korean, but keep the habit.
- This PC has core.autocrlf=true. Pinned inputs must stay byte-exact, which is why .gitattributes -text exists. Never run git add -u --renormalize.
- Match the surrounding code style. Cite file:line in your report.
`

const WP = [
  { key: 'A', title: 'WP-A runner (VBS, PS1): plan §2 A1-A9. Owned: the VBS, the PS1 and tools\\vbs_compile_check.ps1. Test with a compile check plus the probe mock COM (adapt test\\mock_vissim.vbs into W\\diagnostics\\obs150_20260924\\tests\\ if needed). The D10 frameAdvance value comes from V0-4. If B1 has not produced it yet, implement it as the single named constant the plan specifies, set from the probe facts: writes act at t; transitions only on integer seconds. ' +
    'HARD SAFETY RULE: NEVER run scripts\\tests\\test_b1a_watchdog_attempt_launch.py, the run_plant_fidelity_matrix tests, or any test or script that launches a run_real_world_single_watchdog*.ps1. Their Kill-Vissim runs Get-Process -Name VISSIM200,VISSIM200CL,cscript | Stop-Process and kills EVERY VISSIM and cscript on the machine; it killed three live runs at 03:15. Before running any existing test file, grep it for powershell/cscript/.ps1 launches and skip those. Run the PS1 only in its no-launch/parse-check form. ' +
    'REQUIRED IN WP-A as well: on the SDMPC-31 (v2) path, the PS1 must never kill by process name. It kills only the PIDs it launched itself (recorded at launch with their start time), and the v2 path always behaves as NoGlobalKill. Add a static test (grep) that asserts the v2 path cannot reach the name-based Kill-Vissim.' },
  { key: 'B1', title: 'WP-B1 Python capture and head window: plan §3 B2-B5, B7 (SHO part + AD :8053-8081 as a patch), V0-1..4, V0-10. Owned files per plan §8. Unit-test on the probe data (.mer, gt_*.csv, snapshots). The green-crossing counts must match the ground truth at vehicle level. The .mer lag and tail rule and the 0.005 s boundary rule are as in plan §1.2 / B3.' },
  { key: 'B2', title: 'WP-B2 Python lanes and detectors: plan §3 B1 (detector generator), B6 (lane observer incl. the 10643 lane×destination ledger and 10681 lane shares), B7 (obs150_observation.py), T10, V0-5..9. Owned files per plan §8. Unit-test on the probe data: the 10643 join must be checked against gt_veh trajectories at vehicle level.' },
  { key: 'C', title: 'WP-C 31-cell wiring: plan §4 C0-C12. Owned: LPR, lane_coupling.py, freeway_refined_geometry.py, source_boundary.py, RS, the N31D plant/reference/config/bench/tests/port_profile_v2, the C1 copies, plus the AD :9401-9424 change as a patch. Use the boundary family + baseline FD. Do C0 (early decision-time estimate) as far as possible offline, and report the cost ratio. Where you need B1/B2/E outputs, code against the contract signatures and mark the integration points.' },
  { key: 'E', title: 'WP-E repin: plan §5. Owned: N31D\\repin_scenario_v2.py, N31D\\scenario\\*, N31D\\network\\*, tools\\prepare_sdmpc31_network.py. Migrate the 21 pack files to the v2 network, with receipts and prior_mismatch for the 7 prior-calibrated entries (D-B). Network copy = .inpx + 42 .sig only. Verify every pin.' },
  { key: 'D', title: 'WP-D tools: plan §6 D1-D7. Owned: tools\\run_sdmpc_n31.ps1, tools\\freeze_worktree.ps1, N31D\\tools\\*. The launcher takes -Tuning only (plan §1.1), freezes a copy (NEW-14), names the network sdmpc31_*.inpx, and respects the seat rule (queue 3 + 1 dev; total <= 4; see D:\\VISSIM_runs\\20260923_stage1\\launch_reserved.ps1). Also: replay tools (make_replay_state/replay_decision for v2 state), watch_sdmpc, and the G1 ground-truth comparator (D6 after B2 interfaces).' },
]

phase('Contract')
const contract = await agent(CONTEXT + `
## Your package: WP-0 contract (plan §1, all of it).
Owned files: W\\diagnostics\\sdmpc_n31_20260924\\CONTRACT.md, W\\evaluation\\controllers\\obs150_contract.py (schema constants, validators, dataclasses, and the function signatures of §1.9), W\\.gitattributes (one edit).
Every other package codes against this, so be precise and complete:
- the switch;
- time rules;
- the counting identity;
- the obs150-raw/v1 fields;
- derived schemas;
- Obs150Context;
- detector CSV columns;
- Python interfaces.
Add unit tests for the validators under W\\diagnostics\\obs150_20260924\\tests\\. Return a summary of the contract (field names, signatures) for the other packages.`, { label: 'WP-0 contract', phase: 'Contract' })

const results = await pipeline(WP,
  (wp) => agent(CONTEXT + `
## Contract (WP-0) summary
${contract}

## Your package
${wp.title}

RESUME NOTE: a previous attempt at this package was cut off by a usage limit (about 02:45). Partial work may already exist.
- Look at your owned files (git diff for modified files, plus the new files) and at W\\diagnostics\\sdmpc_n31_20260924\\patches\\.
- Keep what is correct and complete the rest.
- Do not redo the parts that already work.
- Also check for stray files the previous attempt may have written outside your ownership, and report them. For example, untracked reports\\20260911_decision_runtime\\native_writer_pure_v1\\* newer than CONTRACT.md. Do not delete them.

Implement it fully, with unit tests. Stay inside your owned files.
Return:
- files created/changed;
- tests run and their results (paste the summary line);
- deviations from the plan, with reasons;
- integration points for other packages;
- open issues.`, { label: 'impl:' + wp.key, phase: 'Implement' }),
  (impl, wp) => agent(CONTEXT + `
## Contract (WP-0) summary
${contract}

## Independent review of ${wp.title}
Implementer report:
${impl}

Review the actual files, not the report.
- Check against: the plan section, the contract, the design doc, and the probe facts (writes act at t; integer transitions; .mer lag <= 0.81 s; .mer first column = point number; Vehs(Current,k,All) closes at t; removals from .err).
- Run the tests yourself.
- Hunt for anything that silently degrades exactness:
  - off-by-one windows;
  - wrong sign;
  - float/rounding at boundaries;
  - None==None passing;
  - IsNumeric(Empty) in VBS;
  - silent emptying;
  - writes to files outside ownership;
  - pins broken by CRLF.
Return a numbered list of REQUIRED fixes (file:line, why, how) and optional improvements, or "no required fixes".`, { label: 'review:' + wp.key, phase: 'Review' }).then(rev => ({ impl, rev })),
  (r, wp) => agent(CONTEXT + `
## Contract (WP-0) summary
${contract}

## Apply the review to ${wp.title}
Implementer report:
${r.impl}

Review:
${r.rev}

Apply every REQUIRED fix that is correct. If you reject one, say why with evidence. Rerun all tests of the package. Return the final package report:
- files;
- test results;
- fixes applied/rejected;
- remaining open issues;
- integration notes for the integrator.`, { label: 'fix:' + wp.key, phase: 'Fix' }).then(fin => ({ key: wp.key, final: fin, review: r.rev }))
)

return { contract, packages: results }
