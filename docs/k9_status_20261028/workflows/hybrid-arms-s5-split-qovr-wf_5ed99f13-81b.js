export const meta = {
  name: 'hybrid-arms-s5-split-qovr',
  description: 'Design, review, implement, replay-verify and freeze three hybrid rule arms (VSL at S5, split-range, ALINEA queue override)',
  phases: [
    { title: 'Design' },
    { title: 'Review' },
    { title: 'Implement' },
    { title: 'Replay' },
    { title: 'Verify' },
    { title: 'Fix' },
    { title: 'Freeze' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/hybrid/arms'
const CTX = `
CONTEXT (read carefully; you are one stage of a multi-agent workflow; write all reports in KOREAN, concise, with [실행]/[읽음]/[추론] tags):
- Project: VISSIM SDMPC-31 traffic control. A TEST "hybrid" controller exists: freeway = rule layer (Carlson MTFC-VSL velocity-form PI + ALINEA on 8 physical ramp meters), urban = SDMPC. One config key: adapter.sdmpc_freeway_rule.
- Worktree W = D:/VISSIM-merge/sim3-n31-hybrid, branch claude/hybrid-rulefw-sdmpc-urban-20260929, HEAD 92fa4b8 (local only, NEVER push). Module: W/evaluation/controllers/freeway_rule_hybrid.py (557 lines). Wiring in W/evaluation/controllers/sdmpc.py, joint_owner_game.py, vissim_stackelberg_adapter.py. Tuning generator: W/diagnostics/sdmpc_n31_20260924/make_config_n31.py --hybrid-rule. Current hybrid tuning: W/diagnostics/sdmpc_n31_20260924/config_n31_v2_hybrid_carlson_alinea.json (sha256 9a55778f...). Tests: W/diagnostics/sdmpc_n31_20260924/tests/test_n31_hybrid_rule.py.
- Design/build docs: ${SP}/hybrid/HYBRID_DESIGN.md, ${SP}/hybrid/HYBRID_BUILD.md (sections 1-11: module, tests, offline replays, determinism, freeze/preflight, launch), ${SP}/hybrid/hybrid_parameters.json (stations, targets, zone layout). Replay tools: ${SP}/hybrid/tools/ (run_replay.py, make_hybrid_inputs.py, check_hybrid_replay.py, compare_replays.py, lowprio.py) and ${SP}/hybrid/fix_dup/ (section 11 replays incl. make_replay_state_v2.py prepare/compare usage).
- LIVE pilot run (read-only!): D:/VISSIM_runs/20260929_hybrid/sdmpc31_v3c1_hybrid_s31b (launched from FRZ D:/VISSIM-merge/frozen/sdmpc31_92fa4b8e_202609291737, seed 31, 9000 s, now ~decision 6750+). Its decisions_*/state_*.json and action_*.json are the replay inputs. No-control pair: D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31.
- Pilot finding that motivates this work (0-6450 s vs NC s31): FW_E mainline +77.6 veh.h, of which +71 on link 2, concentrated 2250-4650 s (exactly when VSL S4 was 80-100). By 513 m cell (FW_E chainage): cells 6-9 (3.1-5.1 km, upstream of the 10639 merge ~4.70 km and 10681 merge ~5.04 km) got slower (cell 6 98->70, cell 8 43.5->29.7 km/h; +53 veh.h); VSL application zone S4 (sign 5386.5 m, cells 10-12) +6; B2 cells 13-14 (6.7-7.7 km, 10484 merge ~7.60 km) UNCHANGED (51-53 km/h both). Downstream throughput within +-1%. Rule actions: VSL S4 90/100/80 from 2250 to 4650 s; ALINEA RM_C10639 stuck at the minimum green 2 s from 3600 s to at least 6600 s; 10681 5-8 s; 10490 4-8 s; RM_C10484 min 7 s (never reached its minimum); FW_W meters always 10 (open). Urban links 1220007401/1220007402 +56 veh.h and input 282 (link 1220011200) inserted -139 vehicles (possible 10639 ramp spillback, NOT verified).
- Earlier established facts: in this VISSIM network VSL does not raise bottleneck discharge (N1/N1F step experiments, +-2-3%); B2 capacity drop INCONCLUSIVE (3 events). J1: FW_E effects are judged only by >=3-seed paired comparisons, so every arm here is a single-seed exploratory run.
- USER REQUEST: try three changes, each as a SEPARATE arm vs the pilot (one change per arm, everything else identical to the pilot tuning):
  A "zoneS5": move the MTFC VSL application zone from S4 (head 10, sign cell 10, DSD 59-62) to S5 (head 12, sign cell 13, DSD 63-66, sign at 6733.2 m); S4 fixed 110. B2 then lies inside the application zone (no Carlson acceleration area) - this matches the location of the user's earlier handoff VSL90 experiment (DSD 63-66). Same station (910085-910087), target 18.5 %, gains, levels {80,90,100,110}, rate limit 20 km/h.
  B "split": split-range RM-first/VSL-second (Carlson et al. 2014 idea, primary text NOT available; do not download anything): the MTFC PI is active only while ALINEA RM_C10484 is saturated at its lower request bound; otherwise b is held/reset at 1 (VSL 110, releasing within the 20 km/h rate limit). Expected: in s31 10484 may never saturate, so arm B may be effectively ALINEA-only - acceptable and must be stated.
  C "qovr": ALINEA queue override + anti-windup on all 8 meters: ramp storage occupancy w(k) measured at the decision from the state snapshot on the meter's ramp storage links; if w >= 0.8*w_max the meter is released toward its maximum; hysteresis release at w <= 0.5*w_max; back-calculation: ALINEA integrator r~ reset to the service rate of the actually applied green. MTFC unchanged (S4).
- HARD RULES: never push; commit only with explicit paths; never git --renormalize; commit identity env GIT_AUTHOR_NAME=GIT_COMMITTER_NAME=Ming2you, GIT_AUTHOR_EMAIL=GIT_COMMITTER_EMAIL=alsrjsrb1915@snu.ac.kr, message ends with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Never modify anything under D:/VISSIM-merge/frozen/* (live runs read them) and never write into the live run folder. Do not start or kill VISSIM/cscript. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. Do not touch other worktrees (sim3-n31-v3c1, sim3-n31-urban-b2 has a concurrent workflow) or other branches. Do not read held-out seed 37 data or seeds 59/61/67. Do not download files or fetch PDFs. Offline replays: ONE AT A TIME, BELOW_NORMAL priority, PYTHONHASHSEED=0, NUMBA_CACHE_DIR as in HYBRID_BUILD. Key-absent paths must stay bit-identical. If the Write tool refuses a file, write it with a Bash heredoc or python.
- Output folder for this workflow: ${OUT} (create subfolders as needed). Launch of VISSIM runs is done later by the main session, not by you.
`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    design_path: { type: 'string' },
    arms: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, config: { type: 'string' }, summary: { type: 'string' } }, required: ['name', 'config', 'summary'] } },
    declared_parameters: { type: 'string' },
    replay_states: { type: 'string' },
    hard_blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['design_path', 'arms', 'declared_parameters', 'replay_states', 'hard_blockers'],
}
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    blocking: { type: 'array', items: { type: 'string' } },
    nonblocking: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'blocking', 'nonblocking'],
}
const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    tests: { type: 'string' },
    tunings: { type: 'array', items: { type: 'object', properties: { arm: { type: 'string' }, path: { type: 'string' }, sha256: { type: 'string' } }, required: ['arm', 'path', 'sha256'] } },
    stop: { type: 'boolean' },
    stop_reason: { type: 'string' },
  },
  required: ['report_path', 'files_changed', 'tests', 'tunings', 'stop', 'stop_reason'],
}
const REPLAY_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    replays: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, verdict: { type: 'string' }, detail: { type: 'string' } }, required: ['name', 'verdict', 'detail'] } },
    all_pass: { type: 'boolean' },
  },
  required: ['report_path', 'replays', 'all_pass'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    blocking: { type: 'array', items: { type: 'string' } },
    nonblocking: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'blocking', 'nonblocking'],
}
const FREEZE_SCHEMA = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    commit: { type: 'string' },
    frz: { type: 'string' },
    preflights: { type: 'array', items: { type: 'object', properties: { arm: { type: 'string' }, name: { type: 'string' }, verdict: { type: 'string' } }, required: ['arm', 'name', 'verdict'] } },
    launch_commands: { type: 'array', items: { type: 'string' } },
    stop: { type: 'boolean' },
    stop_reason: { type: 'string' },
  },
  required: ['report_path', 'commit', 'frz', 'preflights', 'launch_commands', 'stop', 'stop_reason'],
}

phase('Design')
const design = await agent(CTX + `
YOUR STAGE: DESIGN (no code changes in W; read-only except writing under ${OUT}).
Write ${OUT}/ARMS_DESIGN.md (Korean) that fully specifies arms A/B/C so an implementer can build them without guessing:
1. Config schema: new optional sub-keys under adapter.sdmpc_freeway_rule (e.g. mtfc.application_head / mtfc.split_range / alinea.queue_override). ABSENT sub-keys => exact current behaviour (bit-identical). Specify validation (validate_section/configure) changes, including how configure's current check "application head 10 + acceleration head 12" generalises for arm A (application head 12, no acceleration area, head 10 fixed 110), and how joint_owner_game.build_ownership / sign-cell mapping / VBS row contract (DSD 63-66 must accept 80..110) handle head 12 being commanded. Read the actual code paths and cite file:line.
2. Arm B exact law: define 'saturated' precisely in terms of the existing ALINEA state of RM_C10484 (request integrator at its lower bound in THIS decision? previous?), what b does when inactive (reset to 1 = anti-windup), how the 20 km/h rate limit applies on release, and what is recorded in metadata. State the expectation for s31 honestly.
3. Arm C exact law: which links form each meter's ramp storage (find the existing source of truth: physical_ramp_branches, scan region definitions onramp:RM_C*, east_link_sets_source.json, the SDMPC ramp config; cite it), how w(k) is counted from the state snapshot (vehicle records per link; include vehicles on the storage links upstream of the stop line; say whether urban approach links are excluded), w_max (lane-length / effective vehicle length - declare the value and its source), thresholds 0.8/0.5 hysteresis (history stored in next_history), what 'release toward maximum' means under the existing +-2 s per-decision box and the SDMPC moving-box contract (check whether a jump bigger than +-2 s would violate sdmpc.py Coordinates/apply/verify_applied; if the box is a hard contract, the override ramps +2 s per decision - state which), and back-calculation (r~ := service rate of the applied green whenever applied != ALINEA request).
4. Tunings: three new tuning files generated by make_config_n31.py (flags), each = pilot tuning + exactly one sub-key; names e.g. config_n31_v2_hybrid_zoneS5.json / _split.json / _qovr.json. Pilot tuning must remain byte-identical.
5. Verification plan: unit tests per arm (incl. mutation-style checks), key-absent bit identity (offline replay of a pilot state with the pilot tuning must reproduce the recorded pilot action byte-identically - choose T=3000 or 2850 using the section-11 method), and per-arm offline replays at pilot states where each arm should act (e.g. arm A at a VSL-active state, arm C at a state where some ramp exceeds 0.8*w_max - you may compute w(k) over the pilot states AFTER declaring the thresholds, to pick replay states; record that order). Synthetic history for arm replays as in HYBRID_BUILD section 2.2 (make_hybrid_inputs.py) since section sha differs.
6. PRE-DECLARED comparison for the future VISSIM runs (before any arm data exists): paired vs pilot s31b and vs NC s31, four metrics (fw_e_main, east local 19, Omega + urban_omega, all+uninserted), FW_E 513 m cell speed/TTT in cells 6-9 and 13-14 over 2250-4650 s, B2 downstream throughput, per-meter green traces and ramp queues, urban links 1220007401/1220007402 and input 282, VSL activity count. State explicitly: single seed, descriptive only, no adoption decision (J1).
7. Run names: sdmpc31_v3c1_hyb_zoneS5_s31, sdmpc31_v3c1_hyb_split_s31, sdmpc31_v3c1_hyb_qovr_s31; RunsRoot D:\\VISSIM_runs\\20260930_hybrid_arms.
Report hard_blockers only if an arm is impossible without violating a contract (then propose the closest feasible variant).`, { label: 'design', phase: 'Design', schema: DESIGN_SCHEMA })

if (!design) { return { stopped: 'design agent failed' } }
log('design: ' + design.design_path + ' | blockers ' + design.hard_blockers.length)

phase('Review')
const review = await agent(CTX + `
YOUR STAGE: ADVERSARIAL DESIGN REVIEW (read-only; write only ${OUT}/ARMS_REVIEW.md in Korean).
Read ${design.design_path}. Verify every code claim against the actual files in W (file:line), every network/geometry claim against the tuning/hybrid_parameters/inpx-derived sources, and every parameter's stated source. Try to REFUTE: (a) that key-absent behaviour stays bit-identical; (b) that arm A's head-12 command is really written to DSD 63-66 and read by the plant sign cell and not overwritten by fixed_recovery/ownership or the VBS contract; (c) that arm B's saturation definition can actually become true and what b does; (d) that arm C's ramp storage links/w_max are correct for all 8 meters (check at least 10639 and 10484 in detail), that the override does not break the SDMPC moving-box/verify_applied contract, and that back-calculation cannot produce a green outside the admissible/unique-service set (recall the RM_C10490 shared-service defect fixed in 92fa4b8); (e) that the pre-declared comparison is fixed before data and does not let pilot data tune thresholds; (f) that each arm changes exactly one thing vs the pilot. Blocking = would produce a wrong/unsafe run or break a contract; list concrete fixes.`, { label: 'design-review', phase: 'Review', schema: REVIEW_SCHEMA })

phase('Implement')
const impl = await agent(CTX + `
YOUR STAGE: IMPLEMENT in W (uncommitted working-tree changes; do NOT commit yet).
Inputs: design ${design.design_path}; review ${review ? review.report_path : '(review failed - proceed carefully)'} with blocking items: ${JSON.stringify(review ? review.blocking : [])}. Apply the design with ALL blocking review fixes (record in your report how each was addressed; if you disagree with a blocking item, explain with evidence instead of silently skipping).
Do: code changes under the new optional sub-keys only (key-absent = identical); unit tests in test_n31_hybrid_rule.py (new test classes per arm + key-absent identity + mutation checks as in section 11.3 style); make_config_n31.py flags that generate the three arm tunings (pilot tuning byte-identical, verify with --check); run the hybrid test bundle (test_n31_hybrid_rule, test_n31_generators, test_sdmpc_qp_fallback, diagnostics.test_sdmpc_sequence, test_joint_owner_addresses, test_joint_neighbor_callbacks, tests.test_diagnostic_rule_profile) and report counts. Preserve each file's line-ending style (check CRLF/LF before and after). Write ${OUT}/ARMS_IMPL.md (Korean): files/lines changed, tests, tuning paths + sha256, deviations from the design.
Set stop=true only if you cannot implement an arm without violating a contract.`, { label: 'implement', phase: 'Implement', schema: IMPL_SCHEMA })

if (!impl || impl.stop) { return { design, review, impl, stopped: 'implementation stopped' } }

phase('Replay')
const replay = await agent(CTX + `
YOUR STAGE: OFFLINE REPLAYS (no code edits in W except none; outputs under ${OUT}/replays). Follow the verification plan in ${design.design_path} section 5 and implementation notes ${impl.report_path}. Tunings: ${JSON.stringify(impl.tunings)}.
Required, ONE AT A TIME, BELOW_NORMAL, PYTHONHASHSEED=0:
R0 key-absent identity: pilot tuning, a pilot state (T=3000 with actual action_002850 + .applied, or T=2850 per section 11.4) -> must be IDENTICAL to the recorded pilot action (make_replay_state_v2.py compare: derived, CSV bytes, control fields, objective repr; normalise root paths as in section 11.4).
R-A, R-B, R-C: each arm tuning at the pilot states chosen in the design (at least one state where the arm must act; for arm B also a state where it must stay inactive). Check with check_hybrid_replay.py (adapt a copy under ${OUT}/tools if the DSD expectation differs: arm A expects DSD 63-66 = MTFC speed and DSD 59-62 = 110) plus arm-specific checks (A: head 12 commanded, plant/VBS rows consistent; B: activity flag and b logic; C: w(k), override state, applied green inside the +-2 s box and admissible unique-service set, back-calculated integrator). Also confirm SDMPC completed, freeway axes width 0, python_hash_seed "0".
Copy inputs from the live pilot folder read-only (never write there). Write ${OUT}/ARMS_REPLAY.md (Korean) with a table per replay (inputs, verdict, key numbers, wall time).`, { label: 'replays', phase: 'Replay', schema: REPLAY_SCHEMA })

phase('Verify')
const verify = await agent(CTX + `
YOUR STAGE: INDEPENDENT VERIFICATION (read-only; write only ${OUT}/ARMS_VERIFY.md in Korean).
Review the working-tree diff in W (git -C D:/VISSIM-merge/sim3-n31-hybrid diff), the design ${design.design_path}, review ${review ? review.report_path : '-'}, implementation report ${impl.report_path}, replay report ${replay ? replay.report_path : '(replay stage failed)'}. Independently re-derive: key-absent identity argument (every new branch guarded), arm A head-12 path end to end, arm B saturation/reset logic, arm C storage links, w_max arithmetic, hysteresis state round-trip through next_history/.applied receipts, box/admissibility of overridden greens, back-calculation, and that each tuning differs from the pilot tuning by exactly one sub-key (diff the JSON). Re-run the unit test bundle once. Blocking = wrong run or broken contract; give concrete fix instructions.`, { label: 'verify', phase: 'Verify', schema: VERIFY_SCHEMA })

let fixNote = 'none'
const blocking = [].concat(verify ? verify.blocking : ['verify stage failed'], replay && !replay.all_pass ? ['replay stage not all PASS: see ' + replay.report_path] : [], !replay ? ['replay stage failed'] : [])
if (blocking.length) {
  phase('Fix')
  const fix = await agent(CTX + `
YOUR STAGE: FIX + RE-CHECK. Blocking items: ${JSON.stringify(blocking)}. Reports: ${impl.report_path}, ${replay ? replay.report_path : '-'}, ${verify ? verify.report_path : '-'}.
Fix each blocking item in W (uncommitted), re-run the unit test bundle, and re-run ONLY the replays affected (one at a time, BELOW_NORMAL, PYTHONHASHSEED=0), always including R0 key-absent identity if any shared code changed. Append a section to ${OUT}/ARMS_REPLAY.md and write ${OUT}/ARMS_FIX.md (Korean). If a blocking item cannot be fixed safely, set stop=true.`, { label: 'fix', phase: 'Fix', schema: IMPL_SCHEMA })
  if (!fix || fix.stop) { return { design, review, impl, replay, verify, fix, stopped: 'fix stage stopped' } }
  fixNote = fix.report_path
}

phase('Freeze')
const freeze = await agent(CTX + `
YOUR STAGE: COMMIT + FREEZE + PREFLIGHT (no VISSIM start).
Preconditions: reports ${impl.report_path}, ${replay ? replay.report_path : '-'}, ${verify ? verify.report_path : '-'}, fix ${fixNote}. Re-run the unit test bundle once more; if anything fails, stop=true.
1. Commit in W with explicit paths only (code, tests, generator, the three new tuning files; NOT the pilot tuning, which must be unchanged), identity per HARD RULES, message describing the three arms. No push.
2. Freeze + preflight exactly as HYBRID_BUILD sections 10.8/11.5 (run_sdmpc_n31.ps1 -Freeze -PreflightOnly from W) for arm A tuning with -Name sdmpc31_v3c1_hyb_zoneS5_s31 -SimPeriod 9000 -Seed 31 -Controller wu-link -RunsRoot D:\\VISSIM_runs\\20260930_hybrid_arms; then preflight-only (no new freeze) from the new FRZ for arms B and C (names sdmpc31_v3c1_hyb_split_s31, sdmpc31_v3c1_hyb_qovr_s31) if the tool supports it; otherwise document how. Confirm FREEZE_VERIFIED, LAUNCH_PLAN_OK, RW_RULE_OBSERVATION=1, PROVENANCE_OK, tuning sha inside FRZ == worktree for all three.
3. Produce the exact WMI launch commands (Invoke-CimMethod Win32_Process Create, CommandLine starting with cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe ... run_sdmpc_n31.ps1 ..., CurrentDirectory = new FRZ, log to D:\\VISSIM_runs\\20260930_hybrid_arms\\wmi_<name>.log). Do NOT execute them.
Write ${OUT}/ARMS_FREEZE.md (Korean).`, { label: 'freeze', phase: 'Freeze', schema: FREEZE_SCHEMA })

return { design, review, impl, replay, verify, fixNote, freeze }
