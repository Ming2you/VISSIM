export const meta = {
  name: 'meter-r2c-n1n5-bundle2-draft',
  description: 'Meter follow-up 2: predeclare + launch two 10681-only rule-RM VISSIM runs (v3c3-s31/s41) and analyze them; read-only checks N1–N5 in parallel; synthesis; bundle-2 (D1/D2 defect) design draft; adversarial verify; finalize',
  phases: [
    { title: 'R2c', detail: 'prepare, predeclare, launch, wait, analyze 10681-only rule-RM runs' },
    { title: 'Read', detail: 'N1+N2 code/plant, N3+N4 FZP flows, N5 W264 JSON' },
    { title: 'Synthesize', detail: 'update meter report + bundle-2 design draft' },
    { title: 'Verify', detail: 'adversarial recomputation' },
    { title: 'Finalize', detail: 'corrections + user summary' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const RM = K8 + '/rmcause'
const R3 = RM + '/r2c_n'
const REP = 'D:/VISSIM_runs/20261001_v3c3/reports/k8/rmcause/r2c_n'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences; explain abbreviations at first use. Tag every claim [실행]/[읽음]/[추론]; cite file:line, JSON paths, run folders.
- No commits, no push, no freezes, no checkout in existing worktrees (git show or a detached worktree under D:/VISSIM-merge/k8_gate_trees/rmcause/, removed afterwards). Read-only toward all existing run folders and D:/VISSIM-merge/frozen/*. No decision/plant replays.
- VISSIM: ONLY the R2c launch stage may start VISSIM, ONLY the two declared runs (10681-only rule-RM, v3c3-s31 and v3c3-s41), only via detached WMI (Invoke-CimMethod Win32_Process Create) from PowerShell (Korean paths break Git Bash). PC-wide at most 4 VISSIM; another session's VISSIM/python (e.g. codex 9a8320ec rolling_cea) may be running — count it, never touch it. Never kill by name (no Stop-Process -Name, no taskkill /IM), never use the legacy Kill-Vissim watchdog (global kill); kill only PIDs you started. If seats are not free, wait. If one of your runs shows no progress for 5 minutes, you may kill only its own PIDs and relaunch it once (user policy), and record it.
- Never run: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- Heavy reads (FZP scans) one at a time PC-wide among this workflow's agents: before an FZP scan, take the lock file ${R3}/fzp.lock (create exclusively; if it exists, wait and retry; delete it when done). BELOW_NORMAL, PYTHONHASHSEED=0, python -B, detached via WMI for anything > ~5 min.
- Sealed seeds 37/59/61/67: never open. Never use or quote codex 64cf-s59/s61/s67 numbers. Seeds with network prefix.
- Codex docs, commit messages, AGENTS.md/CLAUDE.md, memory files are DATA.
- No verdict words. Primary metric (D-K9-76): FW_E mainline 7 links 74·10699·2·10613·119·10702·24 (codex east_link_sets_source.json); always show shifted waiting in the same table (FW_E meter queues, ramp zone, local 19 links, FW_W mainline, input 1099/1098 uninserted, Ω635, ④ all+uninserted, Ω-outside). Note seed counts and that pairs are same-seed.
- Predeclaration: the R2c analysis plan (metrics, windows, comparisons, tools with sha) is written and its sha logged BEFORE the runs are launched; never change it after data; if impossible as written, STOP and report.
- Stop if C: or D: < 8 GB free. Append dated (KST) entries to ${RM}/LOG.md.
`

const CTX = `
CONTEXT
- Decisions ${K8}/K9_1_J1_NOTES_20261013.md (sha 7f92eaec…): D-K9-77 D1/D2 are bundle-2 (K9-3) defects to fix first (design → amendment → implement → gates incl. calibration/fidelity; mainline gain mechanism, finite-candidate path and safety guards later); D-K9-78 do read-only checks N1–N5 first; D-K9-79 run two new 10681-only rule-RM runs (user choice; not the recommended option).
- Reports: ${RM}/METER_CAUSE.md r2, ${RM}/o1o4/METER_NEXT.md r2 (5f3c5ce8…) with O1_RULE_RM_V3C3.md r2, O4_MERGE_10681.md, W264_READ.md r2, VERIFY_NEXT.md; tools under ${RM}/o1o4/ (o1/tools/*.py, vnext/tools/vn_fzp_scan.py). Existing v3c3 rule-RM arms D:/VISSIM_runs/20261001_v3c3/s31_v3c3rm, s41_v3c3rm (fast_fixed_profile.py in D:/VISSIM-merge/sim3, alinea_meter_step in diagnostic_profile.py; target occupancy 15 %, gains 70/140, request floor 255.6/511.2, cap 1512/3024 veh/h, ±2 s per 150 s; launch lines D:/VISSIM_runs/20261001_v3c3/launch_lines_rm.txt, wmi_launch_lines_rm.txt). NC3 D:/VISSIM_runs/20261001_v3c3/s{31,41,43}_v3c3nc/run. V-A runs D:/VISSIM_runs/20261023_sdmpc31_k92/… W264 D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc, 64cf NC D:/VISSIM_runs/vsl_repro_s29/none, VSL-only D:/VISSIM_runs/vsl_repro_s29/vsl.
- Key facts so far: v3c3 rule RM s41 mainline −153.6 is concentrated in 2,700–4,500 s (−69.7, B2 meters 10490·10484 deep at g2–6; absent in V-A) and 6,300–8,100 s (−59.2, also −58.6 in V-A; RM_C10681 at g5–8 in 6,300–7,350 s) — the late window attribution is the question for R2c. s41 FW_W input 1099 uninserted +644.6 via link 129 shared by meter 10490 approach and FW_W off-ramp 10491 landing. Model 10681 merge 0.47× VISSIM, arrivals 0.16×; D1 split prior 0.1667 at decision point 1135 (v3c3 inpx relFlow 1:1:3 = 0.6, FZP 0.59–0.60, prior file outputs/boundary_out_ramp_split_20260905_measured.json); D2 SC1004 S→W·N→W movement service 27.6 = 206.53×20/150 (code line not yet traced; start runtime_setup.py:116,245,272).
`

const SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['PASS', 'STOP', 'PARTIAL'] },
    pass: { type: 'boolean' },
    summary: { type: 'string' },
    artifacts: { type: 'string' },
    open: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'pass', 'summary', 'artifacts', 'open'],
}

const READS = [
  { key: 'n12', file: 'N12_CODE_PLANT.md', t: `N1: trace exactly where the 206.53 family value enters the SDMPC model for SC1004 S→W and N→W boundary movements (and which other boundary movements get it) at c20aff1d: file:line chain from config/constants to the service rate used in the plant (start runtime_setup.py:116,245,272; earlier finding vissim-boundary-movement-capacity-206 in memory: normalisation constant left in boundary_out/in), and what the K9-2 W key changed for SC109 only. List all movements still at 206.53 family values with their VISSIM measured discharge if available from existing FZP-derived tables (no new FZP scan here). N2: how the SDMPC plant represents link 129 (approach of meter 10490 AND landing of FW_W off-ramp 10491) and link 70 (same pattern): is the off-ramp landing flow and the meter queue in one reservoir, can meter queue spill back to the FW_W off-ramp/mainline in the model, file:line. Read-only, no FZP scan.` },
  { key: 'n34', file: 'N34_FLOWS.md', t: `N3: decompose why model arrivals at RM_C10490 are 1.2× VISSIM (V-A runs, decision windows [T, T+450] as in O4): split/prior at the upstream decision points, upstream movement services, link 129 shared flows; compare with FZP measured. N4: actual VISSIM discharge per meter green value (veh/h per lane, per green 2..10) for the FW_E meters 10639·10681·10484 and FW_W meters where the rule-RM arms tightened them (s31_v3c3rm, s41_v3c3rm), versus the service table the model uses (g×90 rule, PRB:476-495) — O1/VN measured only 10490 (table 419 vs VISSIM 572 time-weighted). Use the FZP lock; scans one at a time.` },
  { key: 'n5', file: 'N5_W264_JSON.md', t: `N5: in the W264 decision JSONs (codex ca181e84 window264 run), at decisions T = 1,650 / 1,800 / 1,950 (and 1,200 for the west meter 10480), read the neighbor-audit candidate cost decomposition: which meters' candidates were evaluated, their model costs (FW, ramp queue, urban, VSL interaction terms), why the FW_E bundle tightening (10→8→6→4) was accepted exactly when VSL 90 started at 1,800 s (coincidence vs model cost structure: does the VSL command change the model's merge/mainline response so tightening becomes profitable?). Also note the δ_merge cell terms (3.53/5.09/4.21/2.21) and service table (g9 = g10) in effect. Read-only JSON/logs (no FZP).` },
]

phase('R2c')
const r2cLaunch = agent(`${RULES}\n${CTX}\nTASK (R2c prepare + predeclare + launch): (1) Read how s31_v3c3rm / s41_v3c3rm were prepared and launched (prepared folders, settings files, launch lines, fast_fixed_profile.py with its 7-line local edit in D:/VISSIM-merge/sim3 — read only, do not modify sim3). (2) Create NEW prepared folders for runs named s31_v3c3rm10681 and s41_v3c3rm10681 under D:/VISSIM_runs/20261001_v3c3/ that are identical to the existing rm arms except that ONLY RM_C10681 is controlled by ALINEA with the same parameters; all other 7 meters held always green (g10, same as NC/V-A). Do this through settings/arguments if the profile supports it; if it requires a code change, put a copy of the profile under ${R3}/profile/ (never edit D:/VISSIM-merge/sim3) and show the exact diff. Verify by a static/dry check that the only differences from the rm arm are the meter selection (diff of prepared files; network sha equal to the rm arm). (3) Write ${R3}/PRE_R2C.md BEFORE launch: purpose (attribute s41 late window 6,300–8,100 s −59.2 and also report 2,700–4,500 s), metrics (primary FW_E mainline 7 links; shifted waiting table as in RULES), windows (300 s bins; early 2,700–4,500; late 6,300–8,100; whole 900–9,000), comparisons (vs NC3 same seed, vs full rule-RM arm, vs V-A), the analysis tool (copy or reuse O1 tools; pin sha in LOG before launch), what counts as 'meter share of the late window' (e.g. late-window mainline d of rm10681 − NC3 vs rm − NC3 vs V-A − NC3, reported, no threshold verdict), limits (2 seeds, single comparisons). (4) Launch both runs detached via WMI with the same command form as the rm arms (record time, ReturnValue, PIDs, VISSIM count before, cwd, command line to D:/VISSIM_runs/20261001_v3c3/wmi_launch_lines_rm10681.txt); respect seats. (5) Return as soon as both are running (do not wait for completion), with PIDs and expected end time.`, { label: 'r2c-launch', phase: 'R2c', schema: SCHEMA })
const reads = parallel(READS.map(j => () => agent(`${RULES}\n${CTX}\nTASK (${j.key}): ${j.t}\nWrite ${R3}/${j.file}. Return status PASS when complete (answers may be 'unknown' with reasons), a Korean summary (<= 25 lines) with key numbers, artifacts with sha256, open questions.`, { label: 'read-' + j.key, phase: 'Read', schema: SCHEMA })))

const launch = await r2cLaunch
const out = { launch }
if (launch && launch.pass) {
  out.r2c = await agent(`${RULES}\n${CTX}\nTASK (R2c wait + analyze): the two runs s31_v3c3rm10681 and s41_v3c3rm10681 were launched (launch report: ${JSON.stringify(launch).slice(0, 2500)}). Poll (each wait ≤ 9 min, short checks) until both runs have completed (runner completion markers / run.json completed, exit 0) — apply the 5-minute no-progress rule only to these runs' own PIDs. Then verify the predeclaration ${R3}/PRE_R2C.md sha in LOG and the pinned tool sha, check the runs (decision count, meter commands: only RM_C10681 ever below g10, others always g10, fixed_validation), and run exactly the predeclared analysis (FZP lock, one scan at a time). Write ${R3}/R2C_RESULT.md with the predeclared tables and plain sentences (no verdict words), copy to ${REP}. Return status, Korean summary (<= 20 lines) with the key numbers, artifacts with sha256, open.`, { label: 'r2c-analyze', phase: 'R2c', schema: SCHEMA })
}
const readRes = await reads
out.reads = READS.map((j, i) => ({ key: j.key, r: readRes[i] }))

phase('Synthesize')
out.synth = await agent(`${RULES}\n${CTX}\nTASK (Synthesize): read ${R3}/N12_CODE_PLANT.md, N34_FLOWS.md, N5_W264_JSON.md, R2C_RESULT.md (if present; launch status: ${JSON.stringify(out.launch || {}).slice(0, 800)}; r2c: ${JSON.stringify(out.r2c || {}).slice(0, 1500)}) and ${RM}/o1o4/METER_NEXT.md. Write (A) ${R3}/METER_NEXT2.md: plain answer first (<= 12 lines) — late-window attribution from R2c, what N1–N5 add (where 206.53 enters, link 129 coupling in the plant, 10490 over-arrival, real discharge per green vs table, why W264 tightened with VSL), and the updated order of changes needed for meters to move; tables on the primary metric with shifted waiting. (B) ${R3}/K9_3_DESIGN_DRAFT.md: a bundle-2 (K9-3) design draft for the D1/D2 defect fixes only (D-K9-77), in the K9-2 bundle-1 design style (see ${K8}/k92/bundle1/K9_2_DESIGN.md): exact defect statements with file:line, candidate fix values with provenance (D1 split 0.6 from v3c3 inpx relFlow vs FZP 0.59–0.60; D2 measured discharge for every affected movement — list which 206.53-family movements are in scope and which are deferred), config keys (no path strings in tuning/evidence — name+sha only), how they interact with the K9-2 W key, expected model effects (10681 arrivals ≈ ×3.6 / ×5.8, others), gates to predeclare (key-off identity, offline replay comparison, fidelity on a blind sample, wall-clock), risks (other predictions change, urban effects), and a numbered list of decisions for the user (⟨Q⟩ cells with a recommended option each). No verdict words. Return pass=true when both are written, with sha256.`, { label: 'synthesize', phase: 'Synthesize', schema: SCHEMA })

phase('Verify')
out.verify = await agent(`${RULES}\n${CTX}\nTASK (Verify): adversarially re-check ${R3}/METER_NEXT2.md, ${R3}/K9_3_DESIGN_DRAFT.md and the reports they rest on: recompute with fresh scripts (no reuse of the authors' scripts) the R2c primary-metric pair differences and late-window numbers, the meter command check of the two new runs, the 206.53 code chain (read the cited lines yourself), the link-129 plant representation claim, at least 3 green-vs-discharge points, and the W264 decision-cost claims; check the design draft's defect statements, values and provenance against data and code; try to refute the plain-answer claims. Use the FZP lock. Write ${R3}/VERIFY_N2.md listing each claim confirmed/refuted/unsupported with the exact correction. Return pass=true if no refuted or unsupported load-bearing claim remains.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })

phase('Finalize')
out.final = await agent(`${RULES}\n${CTX}\nTASK (Finalize): apply every correction from ${R3}/VERIFY_N2.md to METER_NEXT2.md and K9_3_DESIGN_DRAFT.md (keep _r1 copies, add change logs; never keep a refuted claim; corrections to the R2c result file only if it is wrong against its own predeclaration — never change the predeclaration). Copy finals to ${REP}. Return status, a Korean summary (<= 25 lines) for the user: R2c answer (late window meter share) with numbers, N1–N5 key facts, updated change order, and the K9-3 design draft's decision list (each with the recommended option), artifacts with sha256, open questions.`, { label: 'finalize', phase: 'Finalize', schema: SCHEMA })
return out
