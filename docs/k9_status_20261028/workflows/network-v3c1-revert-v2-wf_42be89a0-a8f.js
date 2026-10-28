export const meta = {
  name: 'network-v3c1-revert-v2',
  description: 'Apply the pre-declared per-item revert to v3c: remove decision 1161 (V2, failed G4) to build network v3c1 = v3b + decisions 1160,1162-1168, verify bytes/structure, prepare the NC run folders + dry runs + batch-1 launch lines (no VISSIM launch)',
  phases: [
    { title: 'Build', detail: 'v3c1 sources, receipt, prepare, dry runs' },
    { title: 'Verify', detail: 'independent check' },
    { title: 'Fix', detail: 'repair if blocking' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const V3C = 'D:/VISSIM_runs/20260927_v3c'
const OUT = 'D:/VISSIM_runs/20260927_v3c1'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- v3c NC batch-1 gates (${V3C}/reports/gates_batch1/GATES_BATCH1.md, independently verified in ${R}/net-v3c/gates/VERIFY_BATCH1.md): V1, V3-V7 pass G1-G4; V2 (decision 1161 on link 217@5.0, routes 1161/1-3) FAILS G4 (lane-change removals on 1220012103 at 104.7 m, s43 3 > limit 2). The pre-declared per-item revert rule (V3C_PROPOSAL.md §5 :773-775, ${V3C}/reports/gate_predeclaration_nc_batch1.md) says: revert only V2 to the v3b state, record it as held, rerun NC batch 1 (31/41/43) and re-judge G1-G6. This is authorised by the user's approval of the v3c plan and its revert rule.
- TASK OF THIS WORKFLOW: build network v3c1 = v3c minus the decision 1161 element (and nothing else) for seeds 31/37/41/43/47/53, i.e. v3b + decisions 1160 and 1162-1168 exactly as in v3c (same bytes). Check both constructions agree byte for byte: (a) v3c file with the 1161 lines removed, (b) v3b file with the v3c inserted block minus the 1161 lines inserted at the same position. Keep every other byte. Receipt ${OUT}/v3c1_edit_receipt.json in the same schema as ${V3C}/v3c_edit_receipt.json (so the prepare logic can be reused), recording base v3b and parent v3c (sha per seed), the removed element (decision 1161 with its routes, line range, bytes, sha), the reason (G4 failure, gate report paths + sha) and output sha per seed. Note that V4's decision 1163 keeps its relFlow (its cohort at SC16 N is the v3b route-less cohort, which includes the 1092 chain again once 1161 is gone); state this with evidence from ${V3C}/work/v3c_shares.json and scripts/v3c_build.py:87-126.
- Then prepare exactly like ${V3C}/scripts/v3c_prepare.py (copy it to ${OUT}/scripts/v3c1_prepare.py and parameterise root/tags/receipt/variant name: run folders ${OUT}/s{seed}_v3c1nc/prepared, network file names baseline_s{seed}_v3c1nc.inpx, network_variant name v3c1 with base = v3b same seed and parent = v3c), dry runs WITHOUT -Execute, mirror checks against the v3b prepared.json of the same seed, and ${OUT}/launch_lines_nc_batch1.txt (s31/s41/s43, same form as ${V3C}/launch_lines_nc_batch1.txt). Also copy ${V3C}/reports/gate_predeclaration_nc_batch1.md unchanged to ${OUT}/reports/ with a short header note that the same pre-declared gates apply to the v3c1 rerun (V2 held; its gates no longer apply except G3/G4 on 1220012103 which must return to the v3b level).
- WRITE ONLY under ${OUT}/ (new folder) and ${R}/net-v3c/v3c1/. NEVER modify ${V3C} or D:/VISSIM_runs/20260925_v3b or D:/VISSIM-merge (import fast_nc_prepare read-only: python -B, sys.dont_write_bytecode). No git. NEVER launch VISSIM/cscript or fast_nc_run.ps1 with -Execute. BELOW_NORMAL priority with a working priority function (ctypes argtypes/restype + GetPriorityClass read-back). Another workflow (N1 tools) runs concurrently: keep CPU modest. Never open s37 FZPs, RM arms or sealed seeds.
`
const B = { type: 'object', properties: { summary_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, checks_ko: { type: 'string' }, launch_file: { type: 'string' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'files', 'checks_ko', 'launch_file'] }
const V = { type: 'object', properties: { blocking: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, issue_ko: { type: 'string' } }, required: ['id', 'issue_ko'] } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] }
phase('Build')
let b = await agent(`${COMMON}\nDo the whole task and return the report.`, { label: 'build', phase: 'Build', schema: B })
for (let round = 0; round < 3; round++) {
  phase('Verify')
  const v = await agent(`${COMMON}\nBuild report: ${JSON.stringify(b)}\nINDEPENDENT VERIFIER: with your own code, check every v3c1 seed file equals its v3c file minus exactly the 1161 element lines and equals its v3b file plus exactly the 8 kept decisions (byte and ElementTree level), seed files differ only in randSeed, receipt hashes match files, prepared folders pass the mirror checks (re-run them read-only), dry runs exit 0 without creating run folders, launch lines are exact. Report blocking issues only for things that would invalidate the rerun or crash it.`, { label: `verify:r${round}`, phase: 'Verify', schema: V })
  const blocking = (v && v.blocking) || []
  log(`round ${round}: ${blocking.length} blocking`)
  if (!blocking.length) return { build: b, verify: v }
  if (round === 2) return { build: b, verify: v, stopped: true }
  phase('Fix')
  b = await agent(`${COMMON}\nBuild report: ${JSON.stringify(b)}\nBlocking issues: ${JSON.stringify(blocking)}\nTASK: fix what is real and regenerate the affected outputs; explain rejected ones; return the updated report.`, { label: `fix:r${round}`, phase: 'Fix', schema: B })
}
