export const meta = {
  name: 'sdmpc31-plant-porting-guide',
  description: 'Write a Korean guide for plugging a separately calibrated plant into SDMPC-31 (code-accurate), with an independent accuracy review',
  phases: [
    { title: 'Map', detail: 'plant interface and verification path, read from the pushed commit' },
    { title: 'Write', detail: 'guide draft' },
    { title: 'Review', detail: 'accuracy check against code' },
    { title: 'Final', detail: 'apply review, write the file' },
  ],
}

const CONTEXT = `
## Purpose
The user calibrates a plant on ANOTHER computer. Their line is branch codex/control-full-review-20260909 (latest d80faf9): a METANET component with a Carlson speed-limit FD + VSL exposure transport; candidate A0.5_E4, local free-speed/anticipation corrections and head-service curves, in the same canonical_harness.py. They want to plug that separately calibrated plant into OUR SDMPC-31 controller. They asked for a Markdown guide explaining how to port a plant into SDMPC-31, in Korean, pushed with the SDMPC branch.

## Source of truth
- SDMPC-31 as pushed: Ming2you/VISSIM branch claude/sdmpc-n31-20260924 at 7216e25. It is checked out READ-ONLY at D:\\VISSIM-merge\\review-7216e25 (detached). READ FROM THERE.
- D:\\VISSIM-merge\\sim3-n31 is being edited by another job (a VSL-model port, uncommitted). Do NOT read it as the reference and do NOT edit it.
- The user's branch is checked out read-only at D:\\VISSIM-merge\\review-d80faf9. Use it to describe the mapping from their calibration artifacts to our plant inputs.
- Evidence docs:
  - D:\\VISSIM-merge\\evidence\\SDMPC31_OBS150_PLAN_20260924.md
  - SDMPC31_INTEGRATION_20260924.md
  - OBS150_DESIGN_20260923.md
  - OBS150_PROBE_20260924.md
  - PLANT_CHOICE_20260924.md
  - SDMPC_N31_PLAN_20260923.md
  - review-7216e25\\diagnostics\\sdmpc_n31_20260924\\CONTRACT.md
- Verified facts from native runs (09-24): see memory-like summary below.
  - G1b (1350 s, GT windows): D6 all boundaries/heads/sources exact; D10=1 (154/154); V3 replays IDENTICAL; V3b plant gate PASS (FW_E 21.4, FW_W 12.3 km/h).
  - V5b (9000 s, sdmpc31_v2_s31b) running from FRZ of 7216e25; decisions ~280-600 s.
  - Fixes found natively:
    - program-less meter SCs (ea14026);
    - verification tools (b5f1104);
    - 71-lane initial projection (7216e25).
  - Known limitation: the plant's VSL derivative is 0 at 110, so SDMPC never moves VSL. A port of the user's VSL model is in progress (uncommitted, separate job).

## HARD RULES
- Read-only everywhere except the scratchpad C:\\Users\\TRLAB\\AppData\\Local\\Temp\\claude\\C--Users-TRLAB-Desktop----\\491ef689-f002-4605-9dc5-e6d363495788\\scratchpad\\plant_guide\\. The final file is written there; the main session commits it.
- A 9000 s VISSIM run is live: never start VISSIM, never kill processes, never run tests that launch powershell/cscript watchdogs.
- Every statement about code must be checked in review-7216e25 (cite path:line in your notes). The guide itself may cite paths and function names.
`

const MAP = { type: 'object', properties: {
  summary: { type: 'string' },
  facts: { type: 'array', items: { type: 'object', properties: { topic: { type: 'string' }, fact: { type: 'string' }, where: { type: 'string' } }, required: ['topic', 'fact', 'where'] } } },
  required: ['summary', 'facts'] }

phase('Map')
const [iface, verify] = await parallel([
  () => agent(CONTEXT + `
## Map the PLANT INTERFACE of SDMPC-31 (in review-7216e25)
Cover:
- the switch: tuning key freeway.lane_plant -> plant manifest schema coupled-lane-plant/v2 vs v1;
- the v2 manifest fields and pins (sources: network, geometry, refined_partition, reference_config, parameters, port_profile, reference_protocol, runner_config, sig_manifest; membership, off_groups, observation, source_boundary, lane_groups, fw_e_terminal, vsl_command_space, qualification);
- how each source is produced: make_plant_n31.py, make_config_n31.py, make_reference_config.py, copy_b110.py (the C1 copies of the calibration workspace), port_profile_v2, repin_scenario_v2.py;
- which calibration artifacts the plant consumes (boundary family fit, fit_v1 parameters, segment_params.json grid, geometry.json refined partition with 31 cells, reference boundary config);
- where the plant is built and run at a decision (lane_plant_runtime.load_sources/initialize, freeway_refined_geometry.py, the adapter's freeway kernel, AFA, source_boundary.py (A1), lane_coupling);
- what must match between plant and runner: network sha, 31-cell partition, detector CSV, parent_21 VSL command space and zone heads, meters, the 1 s integration step;
- which contract validators enforce all this (obs150_contract.validate_plant_manifest_v2, validate_tuning_v2);
- how a DIFFERENT calibration drops in: which files change, which generators to rerun with --check, and what pins update.
Then map the user's branch artifacts onto these slots:
- canonical_harness keys component_vsl_transport, physical_cell_fd, state_response;
- candidate.json, parameters.json, segment_params.json from review-d80faf9\\diagnostics\\vsl_handoff_20260924;
- where they would go and what is missing, e.g. the SDMPC plant uses the adapter kernel, not canonical_harness directly. Check this.`, { label: 'map:interface', phase: 'Map', schema: MAP }),
  () => agent(CONTEXT + `
## Map the VERIFICATION + OPERATION path a ported plant must pass (in review-7216e25)
Cover, with exact commands:
- the unit test suites that are safe to run, and the ones never to run (the watchdog global-kill hazard);
- the v1 regression;
- the 110-hold identity idea;
- offline replay: make_replay_state_v2.py prepare + replay_decision_n31.ps1 (-Root, -SkipFreezeVerify), the IDENTICAL/DIFFERENT meaning;
- V3b plant gate: plant_gate.py extract/window/run and its bands;
- the native check run G1: run_sdmpc_n31.ps1 -Freeze -GroundTruthWindows, the sdmpc31_g* naming, the D6 comparator obs150_verify_gt.py and its exit codes;
- the 9000 s launch;
- operational rules:
  - seat rule, at most 4 VISSIM;
  - launch detached via WMI Win32_Process.Create, because a Claude session ending kills background shells;
  - freeze/FRZ, and __tangentcache__ excluded;
  - byte-exact pins: .gitattributes -text, autocrlf, never --renormalize;
  - failed run folders are never renamed;
  - decision fail-fast and replaying a failed decision.
Also list the native-only defects found so far and how each was diagnosed. They are the checklist for a new plant.`, { label: 'map:verify', phase: 'Map', schema: MAP }),
])

phase('Write')
const draft = await agent(CONTEXT + `
## Write the guide (Korean, Markdown)
Save it to ...\\scratchpad\\plant_guide\\PLANT_PORTING_GUIDE.md. It will live at diagnostics/sdmpc_n31_20260924/PLANT_PORTING_GUIDE.md in the repo.
Audience: the user on another computer, porting their separately calibrated plant into SDMPC-31. Clear, practical, ordered. Structure:
0. 요약: what SDMPC-31 is, what a "plant" means here, the switch, and the current verified state.
1. 받는 법: branch/commit, worktree, Python deps, the paths the guide assumes.
2. 플랜트 인터페이스: the manifest fields and what each carries; the invariants that must match the runner (network, 31 cells, detectors, VSL command space, meters, step).
3. 이식 절차, step by step:
   (a) put the calibration artifacts where the generators expect them;
   (b) regenerate reference/plant/config with --check;
   (c) repin;
   (d) the specific mapping for the user's A0.5_E4 VSL candidate and its caveats;
   (e) what NOT to change.
4. 검증 사다리 with exact commands and pass criteria: tests, 110-hold identity, replay, V3b gate, G1 native check with D6, then 9000 s.
5. 운영 수칙: detached launch, seat rule, freeze, pins, the global-kill hazard, never rename failed runs.
6. 지금까지 네이티브에서만 나온 결함과 교훈 (checklist).
7. 알려진 한계와 열린 문제: VSL derivative at 110 (port in progress), the scenario differences between the user's branch and v2 (demand 1099, the 110 curve, seeds), 7 prior-mismatch pack entries.
Keep it accurate and concise. Include file paths and commands. Mark anything uncertain as uncertain.

Interface map:
${JSON.stringify(iface, null, 1)}

Verification map:
${JSON.stringify(verify, null, 1)}`, { label: 'write', phase: 'Write' })

phase('Review')
const review = await agent(CONTEXT + `
## Review the guide for ACCURACY (read the file ...\\scratchpad\\plant_guide\\PLANT_PORTING_GUIDE.md)
Check every command, path, field name, flag, exit code and claim against review-7216e25 and the evidence docs. Check that the steps are complete and in a workable order for someone on another computer. Flag anything that would mislead or fail. Return a numbered list of REQUIRED corrections (quote the line, give the fix and the evidence), or "no required corrections".

Writer notes:
${draft}`, { label: 'review', phase: 'Review' })

phase('Final')
const fin = await agent(CONTEXT + `
## Apply every correct review item to ...\\scratchpad\\plant_guide\\PLANT_PORTING_GUIDE.md (overwrite).
Return a short list of what changed, and the final file path.

Review:
${review}`, { label: 'final', phase: 'Final' })

return { fin, review }
