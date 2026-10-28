export const meta = {
  name: 'port-vsl-model-to-sdmpc31',
  description: 'Port the VSL-aware METANET model (Carlson speed-limit FD + VSL exposure transport) from codex/control-full-review-20260909@d80faf9 into the SDMPC-31 plant, verify, review, fix',
  phases: [
    { title: 'Understand', detail: 'branch VSL model; our SDMPC-31 VSL path' },
    { title: 'Port', detail: 'implement in sim3-n31 with tests' },
    { title: 'Review', detail: 'independent review' },
    { title: 'Fix', detail: 'apply review, final report in Korean' },
  ],
}

const CONTEXT = `
## Goal (user decision 2026-09-24)
Port the VSL model the user built on branch codex/control-full-review-20260909 (commit d80faf9, parent bef8a73, base 00abbab) into our SDMPC-31 plant FIRST. Then VSL will be run and, based on that, the user decides the 110 km/h speed-distribution question. Do NOT change any distribution or network now.

## Where things are
- Branch checkout (read-only reference): D:\\VISSIM-merge\\review-d80faf9 (detached at d80faf9). The model code changed vs 00abbab:
  - evaluation/controllers/freeway_fd.py (+100)
  - evaluation/controllers/area_freeway_accounting.py (+21)
  - evaluation/controllers/physical_lane_groups.py (+14)
  - evaluation/controllers/runtime_setup.py (+7)
  - diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py (+70)
  - tests/test_literature_vsl_fd.py (+55)
  - (the fast_fixed_profile / fast_nc_runner / compare changes are for native VISSIM runs; they are NOT part of this port)
- The handoff: review-d80faf9\\diagnostics\\vsl_handoff_20260924\\. Read README.md, candidate.json, manifest.json, evidence\\RESULTS.md, evidence\\training450_seed29\\REPORT.md (+ selection.json). The fitted candidate is A0.5_E4: Carlson speed-limit FD with A=0.5, E=4, alpha=0, base command 110; VSL exposure transport; plus local free-speed and anticipation corrections and ramp head-service curves. It was fitted on a DIFFERENT scenario from ours: seed 29, demand v1 (input 1099 over-demand), and a different "110 km/h" distribution curve.
- Our SDMPC-31 tree: D:\\VISSIM-merge\\sim3-n31 (branch claude/sdmpc-n31-20260924, HEAD 7216e25, pushed; base f34b896 is descended from 00abbab through a merge with the 5fdfabd controller line, so files may have diverged — check the merge base and diffs).
  - Plant manifest: diagnostics\\sdmpc_n31_20260924\\plant_n31_v2.json (built by make_plant_n31.py).
  - Tuning: config_n31_v2.json (built by make_config_n31.py; key freeway.lane_plant selects the v2 plant).
  - VSL actions: vsl_command_space "parent_21", vsl_set 60/80/110.
  - Known defect: the SDMPC plant's VSL derivative is exactly 0 at 110, so SDMPC never moves VSL (V5b runs keep all 44 VSL at 110).
  - Plan: D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md.
  - Integration record: D:\\VISSIM-merge\\evidence\\SDMPC31_INTEGRATION_20260924.md.
- Our calibrated plant (boundary family + baseline FD, fitted on v2 s31_v2nc): D:\\VISSIM-merge\\sim3\\diagnostics\\demand_sweep\\user_native_20260914\\metanet_calibration_v1\\res10_b110_20260923\\train_s31_v2nc; copies are pinned in sim3-n31 under the same relative path.

## HARD RULES
- A 9000 s SDMPC run (V5b, sdmpc31_v2_s31b) is LIVE. It runs from the frozen copy D:\\VISSIM-merge\\frozen\\sdmpc31_7216e253_*.
  - NEVER touch D:\\VISSIM-merge\\frozen\\*, D:\\VISSIM_runs\\* (read-only) or D:\\VISSIM-merge\\sim3.
  - Never start VISSIM. Never kill processes.
  - Never run tests that launch powershell/cscript watchdogs: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix tests, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, the real_watchdog tool test. Their Kill-Vissim kills every VISSIM.
- Keep CPU light: at most 2 concurrent Python processes; OMP_NUM_THREADS=1 and NUMBA_NUM_THREADS=1. At most ONE offline SDMPC decision replay at a time (~8 min each).
- Edit only D:\\VISSIM-merge\\sim3-n31. Do not commit or push.
- core.autocrlf=true: preserve each file's line endings byte for byte (check against HEAD). Never run git add --renormalize. Pinned inputs must stay byte-exact; regenerate generated artifacts with their --check.
- Python: C:\\Users\\TRLAB\\AppData\\Local\\Programs\\Python\\Python312\\python.exe with PYTHONUTF8=1 and PYTHONDONTWRITEBYTECODE=1.
- Supersede, don't flag: the VSL model becomes part of the canonical v2 plant through the config/manifest keys the branch already uses. No env-only gates. The 110-hold case must stay bit-identical to the current plant.
- Cite file:line.
`

const SPEC = { type: 'object', properties: {
  summary: { type: 'string' },
  items: { type: 'array', items: { type: 'object', properties: {
    what: { type: 'string' }, where: { type: 'string' }, detail: { type: 'string' } }, required: ['what', 'where', 'detail'] } },
  risks: { type: 'string' } }, required: ['summary', 'items', 'risks'] }

phase('Understand')
const [branch, ours] = await parallel([
  () => agent(CONTEXT + `
## Your part: the branch VSL model, exactly
From review-d80faf9 (diff 00abbab..d80faf9), describe precisely:
- the equations: Carlson speed-limit FD with A, E, alpha; how the command enters V(rho) and the speed dynamics; one-sided behaviour at 110;
- VSLExposure: the per-distribution stock transported with the conserved flow; who receives the new command (vehicles crossing the sign DSD cell boundary; ramp vehicles merging after the sign keep 110);
- the config keys: freeway.component_vsl_transport, physical_cell_fd, state_response, the FD keys, vsl sign/zone positions;
- where they hook into the adapter/runtime (area_freeway_accounting, physical_lane_groups, runtime_setup) and into canonical_harness;
- which parts belong to the VSL model and which are separate corrections (local v_free 108.16 for parents 14/15, anticipation 18.375, head-service curves);
- the candidate's exact parameter values and files (candidate.json, selection.json);
- the unit tests;
- the guard that refuses the new FD on the full follower/GNE path ("config check"): exactly what it forbids and why. This matters because SDMPC may run the full follower.`, { label: 'understand:branch', phase: 'Understand', schema: SPEC }),
  () => agent(CONTEXT + `
## Your part: our SDMPC-31 VSL path in sim3-n31
- Trace how SDMPC VSL actions (parent_21 command space, vsl_set) reach the 31-cell plant rollout: LaneFreewayRuntime, the adapter's freeway substep kernel, AFA, the zone heads.
- Find exactly why the tangent/derivative w.r.t. VSL is 0 at 110 (file:line).
- Map which of the branch's changed files have diverged in sim3-n31 relative to 00abbab: git merge-base, diff each file 00abbab..HEAD. List conflicts the port must handle.
- Find where the plant manifest/config would carry the VSL model keys (make_plant_n31.py, make_config_n31.py, CONTRACT.md, obs150_contract validators that may reject unknown keys).
- Check whether SDMPC uses the "full follower"/GNE path the branch guard forbids, and what that implies.
- Which tests cover the freeway plant (N31D tests, test_n31_vsl_binding.py, etc.)?`, { label: 'understand:ours', phase: 'Understand', schema: SPEC }),
])

phase('Port')
const port = await agent(CONTEXT + `
## Your job: implement the port in D:\\VISSIM-merge\\sim3-n31 (no commit)
Branch model:
${JSON.stringify(branch, null, 1)}

Our VSL path:
${JSON.stringify(ours, null, 1)}

Do:
1. Bring the VSL model into sim3-n31: the Carlson FD and VSLExposure transport, plus the hooks in AFA/lane groups/runtime_setup/harness as needed, resolving divergence with our tree.
   - Use the SAME config keys the branch uses.
   - Bring only the VSL model itself. The branch's separate local corrections (v_free/anticipation per cell, head-service curves) were fitted on a different scenario and would override our v2 calibration. Leave them out, and list them as candidates for a later v2 refit unless the VSL model cannot work without them. If so, explain.
   - Coefficients: use the branch candidate's A=0.5, E=4, alpha=0, base 110 as the initial values, and record provenance "fitted on seed29 demand-v1 with a different 110 curve; refit on v2 pending".
2. Make it canonical for the v2 plant through the tuning/manifest keys: regenerate config_n31_v2.json / plant_n31_v2.json with their generators and --check. Update CONTRACT/validators if they must accept the keys. Resolve the branch's full-follower guard for the SDMPC path explicitly: either the SDMPC path is the verified path, or explain what must change.
3. Tests (all must pass; report counts):
   (a) the ported tests/test_literature_vsl_fd.py;
   (b) the 110-hold identity: with every command at 110, the plant rollout is bit-identical to the pre-port plant on the G1b 900 state and on a synthetic state;
   (c) the derivative: the SDMPC tangent of the objective w.r.t. a VSL zone command is nonzero below 110 and one-sided at 110; show numbers;
   (d) the full N31D + obs150 safe suites and the existing SDMPC unit tests.
4. ONE offline SDMPC decision replay on the G1b 900 s state (D:\\VISSIM_runs\\20260924_sdmpc31\\sdmpc31_g1b, via make_replay_state_v2.py prepare into a NEW folder under D:\\VISSIM_runs\\20260924_sdmpc31\\ and replay_decision_n31.ps1 -Root D:\\VISSIM-merge\\sim3-n31 -SkipFreezeVerify). Report the VSL actions chosen, the objective vs the original 348.8017490611648, and the decision wall time.
Return a precise report: files changed, tests, derivative numbers, the replay outcome, deviations, open issues.`, { label: 'port', phase: 'Port' })

phase('Review')
const review = await agent(CONTEXT + `
## Your job: independent review of the port (read, and re-run the safe tests; do not edit)
Branch model:
${JSON.stringify(branch, null, 1)}

Port report:
${port}

Verify:
- the equations and transport match the branch exactly (compare the code side by side);
- the 110-hold bit-identity claim (re-run it);
- the derivative sign and magnitude are sensible (slower limit -> lower critical-speed branch);
- nothing from the branch's separate per-cell corrections leaked in silently;
- the config/manifest regeneration and pins;
- line endings;
- the full-follower guard resolution is sound;
- the replay result is plausible (VSL chosen where FW_E congests).
Return REQUIRED fixes (file:line, why) and optional notes, or "no required fixes".`, { label: 'review', phase: 'Review' })

phase('Fix')
const fin = await agent(CONTEXT + `
## Your job: apply the review, rerun what changed, and report IN KOREAN for the user
Port report:
${port}

Review:
${review}

Return:
(1) fixes applied/rejected;
(2) final test counts;
(3) a concise Korean summary for the user, max ~30 lines:
- what was ported, and what was deliberately left out and why;
- the proof that the 110-hold case is unchanged;
- the VSL derivative now;
- what the replayed SDMPC decision did with VSL;
- the decision time;
- the risks (coefficients from another scenario);
- the proposed "VSL 돌려보기" next step: e.g. a native VISSIM run of the branch's bottleneck VSL90 policy on our v2 network vs NC, and/or an SDMPC run with the VSL-capable plant. The user will use it to decide the 110 distribution.`, { label: 'fix+summary', phase: 'Fix' })

return { branch, ours, port, review, fin }
