export const meta = {
  name: 'v3c3-network-build',
  description: 'Build network v3c3 = v3c2 + DSD 81/91/101 blocks (from the N1F stage-2 networks), prepare 6 NC runs and launch lines, pre-declare GB-1 NC identity, independent check',
  phases: [
    { title: 'Build' },
    { title: 'Check' },
  ],
}

const PLAN = 'D:/VISSIM_runs/20260930_v3c2/reports/repin'
const ROOT = 'D:/VISSIM_runs/20261001_v3c3'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER APPROVED (2026-10-01) the repin plan ${PLAN}/REPIN_V3C2_PLAN.md (sha d4b70c02) with all recommended values (U1-U12) and the review fixes (${PLAN}/REPIN_V3C2_PLAN_REVIEW.md B1-B3 and nonblocking notes). Read both (network part: sections on U1/U2, GB-1, N8, N9, N12).
- TASK: network v3c3 = v3c2 + the three desSpeedDistribution blocks 81/91/101 exactly as used in the N1F stage-2 networks (D:/VISSIM_runs/20260928_n1f_vsl_stage2 and D:/VISSIM_runs/20260928_n1f_vsl; plan e3 evidence: +655 B, s31 expected sha 3de889f0..., only randSeed differs between seeds). NOTHING else changes. Seeds 31, 41, 43, 47, 53 + 37 (SEALED: build/prepare, never open its results; only run.json completed/exit_code later).
- Reuse D:/VISSIM_runs/20260930_v3c2/scripts (v3c2_build.py, v3c2_prepare.py) and its receipts/check layout; byte-preserving insertion, no XML re-serialisation; edit receipt with exact bytes; verify the per-seed sha against the plan's in-memory reproduction.
- Prepare 6 NC runs (same fast_nc_run profile as the v3c2 NC runs) and write ${ROOT}/launch_lines_nc.txt (batch A s31,s41,s43,s47; batch B s53,s37). NOT launched - the main session launches via WMI.
- Pre-declare GB-1 (before any run): v3c3 NC FZP payload byte-identical to v3c2 NC for each fit seed (define 'payload': the .fzp file excluding any header line that embeds the network path/name/time; state exactly what is excluded), the three .err files compared as in review N9, run.json runner_sha256 equal to v3c2 (bf07acda...), same VISSIM build; sealed s37: a hash-only identity tool is allowed (prints only equal/not-equal of the payload hash, never content). Write ${ROOT}/reports/gb1_predeclaration.md + .sha256.
- HARD RULES: read-only on existing run folders; write only under ${ROOT}. No code changes in any worktree, no commits, no VISSIM start/kill, never modify D:/VISSIM-merge/frozen/*. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results.
`
const BS = { type: 'object', properties: { report_path: { type: 'string' }, network_shas: { type: 'string' }, launch_lines_path: { type: 'string' }, gb1_sha256: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'network_shas', 'launch_lines_path', 'gb1_sha256', 'stop', 'stop_reason'] }
const CS = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'blocking', 'nonblocking'] }

phase('Build')
const b = await agent(CTX + 'YOUR STAGE: BUILD + PREPARE + GB-1 PREDECLARATION. Write ' + ROOT + '/reports/V3C3_BUILD.md.', { label: 'build-v3c3', phase: 'Build', schema: BS })
if (!b || b.stop) { return { b, stopped: 'build stopped' } }
phase('Check')
const c = await agent(CTX + 'YOUR STAGE: INDEPENDENT CHECK (read-only; write ' + ROOT + '/reports/V3C3_BUILD_CHECK.md). Inputs: ' + b.report_path + ', launch lines ' + b.launch_lines_path + '. With your own code: diff every v3c3 inpx vs its v3c2 inpx (only the three DSD blocks), compare the blocks with the N1F stage-2 network blocks byte for byte, check that DSD numbers 81/91/101 were free in v3c2 (no collision with desSpeedDecision numbers - note review N12), check prepared runs reference v3c3 and the same runner profile as v3c2 NC, launch lines (cwd, paths, logs, no overwrite), and the GB-1 predeclaration (complete, timestamped before runs). Blocking = anything that invalidates the NC runs.', { label: 'check-v3c3', phase: 'Check', schema: CS })
return { b, c }
