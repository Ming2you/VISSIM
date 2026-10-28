export const meta = {
  name: 'n1-tools-prep',
  description: 'Prepare the approved N1 native VSL step experiment: builder, detached launch queue, G0 prefix checker, extractor (byte-identity test), lane/DESSPEED pass, estimation scripts, analysis freeze receipt, and B1 arm folders; dry tests only, no VISSIM launch',
  phases: [
    { title: 'Build', detail: 'tools + dry tests' },
    { title: 'Verify', detail: 'independent checks of tools and dry tests' },
    { title: 'Fix', detail: 'repair if blocking' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = 'D:/VISSIM_runs/20260927_n1_vsl'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- USER DECISION 2026-09-27: N1 approved as designed in ${R}/fwe-struct/p0/N1_DESIGN.md (revision 3) with spec ${R}/fwe-struct/p0/n1/n1_plan_v3.json (sha 0db0d1c6...): core 16 runs = seeds 41/43/47/53 x {c90, c100, c80, S5-pulse control}, batches B1 c90 -> B2 c100 -> B3 c80 -> B4 control, per-arm network copy with the single edit <scDetRec writeFile="false" /> -> "true", 50-70 handled by option (a) later, B5 (s31) conditional per the declared rule, N1-R held, the revision-3 decision rules frozen BEFORE any N1 data is opened (analysis_freeze). Output root ${OUT}/<seed>_<arm>/{source, prepared, run, launch.log} (new folder).
- Read N1_DESIGN.md §2-§5 and §10 fully, and the plan JSON; tools listed in §3.2 (1 builder, 2 launch queue, 3 G0 checker, 4 extractor, 5 DESSPEED/lane FZP pass, 6 estimation/fit scripts M1-M7, L0-L4, LOSO/LOLO; 7 harness extension is for a later step - skip). Repo tools used read-only: D:/VISSIM-merge/sim3-n31/diagnostics/fast_fixed_profile.py (compile_profile, prepare), fast_fixed_profile_verify.py (prefix_digest, native_recording_grid), fast_nc_run.ps1, fast_nc_runner.vbs, fast_nc_prepare.py; extractor model: D:/VISSIM-merge/sim3/.../control_response_v2/e0_extract.py (find it). Import repo modules read-only (python -B, sys.dont_write_bytecode=True) or copy; NEVER write under D:/VISSIM-merge/* or any existing D:/VISSIM_runs/* folder; write only under ${OUT}/ (scripts/, reports/, arm folders) and ${R}/fwe-struct/p0/n1/tools_work/.
- SAFETY: NEVER launch VISSIM, cscript, or fast_nc_run.ps1 with -Execute. The v3c no-control runs (D:/VISSIM_runs/20260927_v3c/s{31,41,43}_v3cnc) have FINISHED; another offline job (v3c gate evaluation, FZP streaming) runs concurrently: never touch or write any D:/VISSIM_runs/20260927_v3c file, do not kill anything, keep CPU modest (BELOW_NORMAL via a priority function that actually works - set ctypes argtypes/restype and read back with GetPriorityClass), one heavy process at a time. Fit seeds only; never open s37, v3b RM arms or sealed seeds 59/61/67.
- The launch queue script must: be launched detached (WMI Win32_Process.Create) by the main session later; before each launch check the PC-wide VISSIM count and wait until a seat is free (max 4 PC-wide, including other jobs), space launches 30-60 s, run the 120 s ownership check (run.json vissim PID filled) and stop+report if missing (never kill unowned VISSIM), run the G0 check at progress >= 2750 s for each B1 run and stop the queue on any G0 failure (write a STOP marker), move to the next batch only after the previous batch completed and passed G1/G2, use ASCII forward-slash paths and an absolute -Python path, and log everything to ${OUT}/queue.log. Provide a --dry mode that simulates the queue without launching.
`
const B = { type: 'object', properties: { summary_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, dry_tests_ko: { type: 'string' }, launch_instructions_ko: { type: 'string' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'files', 'dry_tests_ko', 'launch_instructions_ko'] }
const V = { type: 'object', properties: { blocking: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, issue_ko: { type: 'string' } }, required: ['id', 'issue_ko'] } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] }
phase('Build')
let b = await agent(`${COMMON}
TASK: write tools 1-6 into ${OUT}/scripts/, run the dry tests of N1_DESIGN §7 "준비" (build + compile for all 16 arms into their prepared/ folders, G0 checker reproducing the v2 precedent from §2.1, extractor re-extraction of s31_v3bnc byte-identical to the existing EO files, queue --dry simulation), write ${OUT}/reports/dry_tests.json and the analysis-freeze receipt ${OUT}/reports/analysis_freeze.json (sha256 of tools 1-6 and of n1_plan_v3.json), and ${OUT}/README.md with the exact launch instruction for the main session (WMI command for the queue).`, { label: 'build', phase: 'Build', schema: B })
for (let round = 0; round < 3; round++) {
  phase('Verify')
  const vs = (await parallel([
    () => agent(`${COMMON}\nBuild report: ${JSON.stringify(b)}\nLENS arms/networks/profiles: independently verify each of the 16 arms: network copy differs from its v3b source (same seed) by exactly the one scDetRec attribute, sha as declared in n1_plan_v3.json, compiled profile events match the declared schedule (levels, zones/DSDs, times, S5 pulse DSD 51-54 2700-2850 s for control), prepared.json pins valid, file names unique per arm, fit seeds only. Report blocking issues only for things that would invalidate the experiment or crash the runs.`, { label: `verify:arms:r${round}`, phase: 'Verify', schema: V }),
    () => agent(`${COMMON}\nBuild report: ${JSON.stringify(b)}\nLENS queue/safety/analysis: independently review the queue script for seat counting, ownership check, G0 stop, no kill paths, detached launch, ASCII paths, restart-once rule after COM refusal; check the G0 checker and the extractor byte-identity evidence; check the estimation scripts implement the frozen revision-3 rules (L0 falsification on B2 only, exposure-weighted L0, kappa from WB/WC, SE floor, SAT selection rules) and that analysis_freeze hashes match the files. Report blocking issues only for things that would invalidate the experiment, crash the runs or break the safety rules.`, { label: `verify:queue:r${round}`, phase: 'Verify', schema: V }),
  ])).filter(Boolean)
  const blocking = vs.flatMap(v => v.blocking || [])
  log(`round ${round}: ${blocking.length} blocking`)
  if (!blocking.length) return { build: b, verify: vs }
  if (round === 2) return { build: b, verify: vs, stopped: true }
  phase('Fix')
  b = await agent(`${COMMON}\nBuild report: ${JSON.stringify(b)}\nBlocking issues: ${JSON.stringify(blocking)}\nTASK: fix what is real (re-run the affected dry tests, refresh analysis_freeze.json), explain rejected ones, return the updated report.`, { label: `fix:r${round}`, phase: 'Fix', schema: B })
}
