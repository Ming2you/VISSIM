export const meta = {
  name: 'network-v3c2-entry-dsd110',
  description: 'Build network v3c2 = v3c1 + freeway entry composition DSD110 on inputs 1098/1099 (as in 64cf), pre-declare NC gates, prepare launch lines, independent check',
  phases: [
    { title: 'Build' },
    { title: 'Check' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const ROOT = 'D:/VISSIM_runs/20260930_v3c2'
const CTX = `
CONTEXT (absolute paths; Korean prose in reports, concise; tag [실행]/[읽음]/[추론]; cite file:line). If the Write tool refuses a file, write it with Bash/python.
- USER DECISION (2026-09-30): freeway entry vehicles should be inserted with desired speed 110. Finding: in v3c1 the freeway inputs 1098 (link 74, FW_E) and 1099 (link 26, FW_W) use vehicle composition 1 'Default' (vehType 100 relFlow 0.806 DSD 40, 150 relFlow 0.1 DSD 40, 200 relFlow 0.094 DSD 30; DSD 40 = 40-45 km/h, DSD 30 = 30-35); the first desSpeedDecision on link 74 is at 11.5 m, on link 26 at 1.6 m. Vehicles are inserted at ~40 km/h, cell 0 is an acceleration zone, and the entry queue is non-empty 97.5 % (1098) / 99 % (1099) of the time. The user's 64cf network (D:/VISSIM_runs/vsl_repro_s29/source/vsl_seed29_none.inpx, sha 64cf5f55) has composition 14 'Freeway entry DSD110' = same three vehTypes and relFlows with desSpeedDistr 110 for all, used by inputs 1098 and 1099. Our DSD 110 = 98-140 km/h (v3c1).
- TASK: network v3c2 = v3c1 + that composition (copy the 64cf definition exactly; keep no=14 and the name if 14 is free in v3c1, otherwise the next free number and say so) + inputs 1098 and 1099 use it in ALL time intervals. NOTHING else changes (no demand, routing, geometry, signals, DSD, detectors, seeds).
- Reuse the v3c1 build/prepare pipeline: D:/VISSIM_runs/20260927_v3c1/scripts (v3c1_build.py, v3c1_prepare.py, v3c_lib), its receipts (v3c1_edit_receipt.json), reports (gate_predeclaration_nc_batch1.md, gates_batch1, gates_5seed, v3c1_build_checks.json, v3c1_prepare_checks.json) and launch_lines_nc_batch1.txt format. Seeds: fit seeds 31, 41, 43, 47, 53 plus 37 (37 = SEALED held-out: build and prepare it, but never open its results). Per-seed v3c1 network shas are in memory note C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory/vissim-network-v3c-20260927.md.
- Output root: ${ROOT} (new folder; same layout as 20260927_v3c1: scripts/, reports/, s<seed>_v3c2nc/prepared, launch_lines). Do NOT launch VISSIM; the main session launches via WMI.
- HARD RULES: read-only on D:/VISSIM_runs/20260927_v3c1, D:/VISSIM_runs/vsl_repro_s29 and every other run folder; do not modify any worktree or D:/VISSIM-merge/frozen/*; no commits. Do not start/kill VISSIM or cscript. Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog. No s37/59/61/67 results. Heavy Python at BELOW_NORMAL.
`
const B_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, predeclaration_path: { type: 'string' }, predeclaration_sha256: { type: 'string' }, launch_lines_path: { type: 'string' }, network_shas: { type: 'string' }, stop: { type: 'boolean' }, stop_reason: { type: 'string' } }, required: ['report_path', 'predeclaration_path', 'predeclaration_sha256', 'launch_lines_path', 'network_shas', 'stop', 'stop_reason'] }
const C_SCHEMA = { type: 'object', properties: { report_path: { type: 'string' }, blocking: { type: 'array', items: { type: 'string' } }, nonblocking: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'blocking', 'nonblocking'] }

phase('Build')
const build = await agent(CTX + `
YOUR STAGE: BUILD + PREPARE + PRE-DECLARE.
1. Write ${ROOT}/scripts/v3c2_build.py (derived from v3c1_build.py; byte-preserving text insertion/replacement, no XML re-serialisation) that creates v3c2 from each seed's v3c1 network and writes an edit receipt (${ROOT}/v3c2_edit_receipt.json: per seed input sha, output sha, exact inserted bytes, replaced attributes with line numbers). Verify by diff that the ONLY differences are the new composition block and the vehComp values of inputs 1098/1099 intervals; confirm the composition equals 64cf's comp 14 byte-for-byte except for unavoidable context; confirm DSD 110 exists and matches v3c1.
2. Prepare runs (v3c2_prepare.py derived from v3c1_prepare.py) for s31/41/43/47/53/37 with the same runner profile as the v3c1 NC runs (SimRes, FZP settings, 9000 s, same demand), dry-run checks as in v3c1_prepare_checks.json, and write ${ROOT}/launch_lines_nc.txt with exact WMI CommandLines (NOT launched). Order: s31, s41, s43, s47 first (4 seats), then s53, s37.
3. PRE-DECLARE (before any run exists) ${ROOT}/reports/gate_predeclaration_v3c2_nc.md and its sha256: G1 edit receipt only the declared change; G2 load .err identical to v3c1 apart from expected lines; G3 run completes 9000 s, EXIT 0; G4 entry behaviour: 0-40 m speed on links 74 and 26 (median over non-empty frames, t >= 900.1) >= 80 km/h in every fit seed; G5 no network breakdown artefacts: vehicles removed/deleted and 'waiting for lane change' timeouts not above v3c1 + declared tolerance per seed. DESCRIPTIVE (no pass/fail): uninserted delay and insertion rates at 1098/1099, FW_E/FW_W 31-cell speed profiles over time (B1/B2 breakdown times), off-ramp and on-ramp flows, urban Omega, Omega TTT, all + uninserted, per seed vs v3c1 NC. State that the 2a/2b static checks will then be re-run on v3c2 NC with the frozen method of ${SP}/static_checks/PREDECLARATION.md (sha a992341e...) to decide F10 (inlet) and F11 (FW_W upstream capacity).
Write ${ROOT}/reports/V3C2_BUILD.md. stop=true only if the change cannot be made cleanly.`, { label: 'build-v3c2', phase: 'Build', schema: B_SCHEMA })

if (!build || build.stop) { return { build, stopped: 'build stopped' } }

phase('Check')
const check = await agent(CTX + `
YOUR STAGE: INDEPENDENT CHECK (read-only; write only ${ROOT}/reports/V3C2_BUILD_CHECK.md). Inputs: ${build.report_path}, receipt ${ROOT}/v3c2_edit_receipt.json, predeclaration ${build.predeclaration_path} (sha ${build.predeclaration_sha256}), launch lines ${build.launch_lines_path}. With your own code: diff every seed's v3c2 inpx against its v3c1 inpx and confirm the only change is the composition + 1098/1099 vehComp in all intervals; compare the composition with 64cf comp 14; confirm per-seed random seed and all other settings unchanged; confirm prepared run folders reference the v3c2 networks and the same runner profile as v3c1 NC (diff the prepared configs); check the launch lines (cwd, paths, names, log files, no overwrite of existing folders); check the predeclaration is complete and timestamped before any run. Blocking = anything that would make the NC runs invalid.`, { label: 'check-v3c2', phase: 'Check', schema: C_SCHEMA })

return { build, check }
