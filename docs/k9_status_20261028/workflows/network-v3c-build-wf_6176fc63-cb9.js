export const meta = {
  name: 'network-v3c-build',
  description: 'Build network v3c (user-approved: V1-V7 cohort-specific new routing decisions with v3b NC realized splits, V8/V9 held), verify it independently (bytes/structure, geometry/route semantics, numbers/plant beta), fix, then prepare the no-control run folders and dry-run checks. No VISSIM launch.',
  phases: [
    { title: 'Build', detail: 'edit script, 6 seed networks, receipt, static checks' },
    { title: 'Verify', detail: 'three independent adversarial verifiers' },
    { title: 'Fix', detail: 'repair loop if blocking issues' },
    { title: 'Prepare', detail: 'run folders + dry-run checks, launch lines (not launched)' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = 'D:/VISSIM_runs/20260927_v3c'
const COMMON = `
CONTEXT (absolute paths). Korean text for prose; mark numbers [실행]/[읽음]/[추론]; cite file:line.
- USER DECISIONS 2026-09-27 (binding): build network v3c from v3b = fix the route-less "D-type" diverges V1-V7 of ${R}/net-v3c/V3C_PROPOSAL.md with the RECOMMENDED option (가) of each item after the adversarial review (appendix R): cohort-specific NEW routing decisions (existing decisions are NOT moved), split values P1 = realized split of the cohort in the v3b no-control fit seeds 31/41/43/47/53, window t >= 900 s (s37 is held out: never open its FZP), relFlow scaled per §3.3 when two or more multi-route decisions cross the same stop line; V7 (SC104 S_SC106) is re-opened (new decision at 1220001602@41.2-60 m, single-decision crossing, no scaling). V8 and V9 are HELD (no edit). V10, O1, X1: no edit. Read the whole proposal first (§3 common rules: positions §3.2, scaling §3.3, destinations §3.4, edit method/receipt §3.5; §4 V1-V7; §5 gates; appendix R).
- Base network v3b: D:/VISSIM_runs/20260925_v3b/source/baseline_s{31,37,41,43,47,53}_v3bnc.inpx (seed files differ only in the randSeed line). v3b method and templates: D:/VISSIM_runs/20260925_v3b/scripts/ (netv3_common.py, s2_realized_split.py, s3_shares.py, s4_apply.py byte-preserving edits + ET structural diff + receipt, s5_prepare.py, s7_extra_seeds.py seed derivation + prepare + verify), README.md, v3b_edit_receipt.json, extra_seeds_receipt.json. Audit artefacts with cohort counts and classifiers: ${R}/net-v3c/ (r1_*, s*_*.py, rv_fzp.py, rv_sum.py, rv_calc.py, v3cp_static*.py, *.pkl).
- WRITE RULES: write ONLY under ${OUT}/ (new folder: scripts/, source/, work/, s{seed}_v3cnc/prepared, receipts, reports) and ${R}/net-v3c/build/. NEVER write under D:/VISSIM_runs/20260925_v3b/ or D:/VISSIM-merge/ (import their python modules read-only: python -B and sys.dont_write_bytecode = True, or copy the module into ${OUT}/scripts). No git. NEVER launch VISSIM, cscript or fast_nc_run.ps1 with -Execute; fast_nc_run.ps1 WITHOUT -Execute (dry run) is allowed only in the Prepare phase. Heavy FZP streaming one process at a time, BELOW_NORMAL priority (another offline job is running).
- New decision numbers start at 1160 (current max 1159). Copy an existing decision element as the template; attributes such as combineStaRoutDec as the donor decision (the decision whose route destinations are borrowed); relFlow format "2 0:<int>"; new route destinations = the destinations of existing routes to the same exits (§3.4); linkSeq must be a valid connected path; decisions >= 5 m downstream of every landing/merge/destination of the cohort (§3.2).
`
const BUILD_OUT = { type: 'object', properties: { summary_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, edits_table_ko: { type: 'string' }, static_checks_ko: { type: 'string' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'files', 'edits_table_ko', 'static_checks_ko'] }
const VER = { type: 'object', properties: { blocking: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, issue_ko: { type: 'string' }, evidence: { type: 'string' } }, required: ['id', 'issue_ko'] } }, non_blocking_ko: { type: 'string' }, verified_ko: { type: 'string' } }, required: ['blocking', 'verified_ko'] }

phase('Build')
let build = await agent(`${COMMON}
TASK (implementer): write ${OUT}/scripts/v3c_build.py (plus helpers) that
 1. counts the cohort splits with ONE declared classifier (state it; reuse the audit's rv_fzp/rv_sum logic where sound) from the v3b NC fit-seed FZPs D:/VISSIM_runs/20260925_v3b/s{31,41,43,47,53}_v3bnc/run/vissim_eval/*.fzp (t_pass >= 900 s), and the old-decision cohorts needed for the §3.3 scaling (n_old, n_new, sum relFlow_old); writes ${OUT}/work/v3c_shares.json;
 2. inserts the new decisions/routes for V1-V7 (option 가) into the s31 v3b source byte-preservingly (insert new elements at the right place in the file, keep every other byte), writes ${OUT}/source/baseline_s31_v3cnc.inpx, then derives the other seeds 37/41/43/47/53 by the randSeed-only edit exactly like s7_extra_seeds.py build;
 3. static checks: ET structural diff = exactly the intended insertions; seed files differ only in the randSeed line; every new route's linkSeq is a connected path from the decision to its destination; destination rules; decision positions vs landings; no new A-type or C-type by a static walk; re-parse relFlows;
 4. writes ${OUT}/v3c_edit_receipt.json (inputs with sha256, v3b source sha per seed, classifier, counts, n_old/n_new, the edit list, output sha per seed, checks) and ${OUT}/README.md (short).
Run it. Report the edits table (item, decision no, link@pos, routes -> dest, relFlow, cohort split, expected plant beta after the edit) and the static-check results.`, { label: 'build', phase: 'Build', schema: BUILD_OUT })

const LENSES = [
  { key: 'bytes', prompt: 'LENS bytes/structure: independently verify (your own code, not the build script) that each v3c seed file equals its v3b source except the intended inserted elements (byte diff + ElementTree structural diff), that the seed files differ from each other only in randSeed, that the XML is well formed and re-parses, that decision/route numbers are unique and start at 1160, that attributes copied from donors are as declared, and that the receipt hashes match the files.' },
  { key: 'geometry', prompt: 'LENS geometry/route semantics: independently verify with the v3c .inpx (your own parser) for every new decision: position rules of V3C_PROPOSAL §3.2 (>= 5 m downstream of all landings/merges/route ends of its cohort, on the link where the preceding routes end when the proposal says so), that no existing decision was moved or changed, that each route linkSeq is a connected path and the destination rule §3.4 holds (downstream of the next diverge, upstream of the next decision), that every branch the cohort currently uses has a route (zero-flow routes allowed only where the proposal says so), and a static walk shows no new route-less diverge or A/C-type for the targeted cohorts. Check lane-change feasibility risks (lnChgDist 9999, landing lanes vs target connectors) and list any place where the new routing would force lane changes the cohort does not do today.' },
  { key: 'numbers', prompt: 'LENS numbers: independently recount the cohort splits from the fit-seed FZPs (t >= 900 s, s37 never opened) with a classifier you implement yourself, compare with ${OUT}/work/v3c_shares.json (tolerance: the proposal values and the audit rv_sum.py), check the §3.3 relFlow scaling arithmetic, and compute the plant beta the U1 derivation would produce on the v3c network: run a COPY of D:/VISSIM-merge/sim3-n31-urban/scripts/derive_routing_beta_physical.py against the v3c s31 .inpx with outputs redirected under ${R}/net-v3c/build/ (do not write into the repo), and compare the V1-V7 approaches with the expected values in the proposal table (e.g. SC109 W left 0.238 -> about 0.174).' },
]
let verdicts = []
for (let round = 0; round < 3; round++) {
  phase('Verify')
  const lensList = round === 0 ? LENSES : [{ key: 'recheck', prompt: 'LENS re-check after fixes: re-run all three lenses (bytes/structure, geometry/route semantics, numbers/plant beta) briefly but independently, focusing on the previously blocking issues: ' + JSON.stringify(verdicts.flatMap(v => (v && v.blocking) || [])) }]
  verdicts = (await parallel(lensList.map(l => () => agent(`${COMMON}
Build report: ${JSON.stringify(build)}
${l.prompt}
Report BLOCKING issues (must be fixed before running VISSIM) separately from non-blocking remarks. Do not modify any file under ${OUT} except your own notes under ${R}/net-v3c/build/verify_${l.key}_r${round}/.`, { label: `verify:${l.key}:r${round}`, phase: 'Verify', schema: VER })))).filter(Boolean)
  const blocking = verdicts.flatMap(v => v.blocking || [])
  log(`round ${round}: ${blocking.length} blocking issue(s)`)
  if (blocking.length === 0) break
  if (round === 2) { log('still blocking after 2 fix rounds — stopping before Prepare'); return { build, verdicts, prepared: null, stopped: true } }
  phase('Fix')
  build = await agent(`${COMMON}
Previous build report: ${JSON.stringify(build)}
Blocking issues from independent verifiers: ${JSON.stringify(blocking)}
TASK: re-check each issue; fix the build script and regenerate all outputs (sources, receipt, shares) if an issue is real; explain rejected ones with evidence. Return the updated report.`, { label: `fix:r${round}`, phase: 'Fix', schema: BUILD_OUT })
}

phase('Prepare')
const prepared = await agent(`${COMMON}
Final build report: ${JSON.stringify(build)}
Verifier results (no blocking issues left): ${JSON.stringify(verdicts)}
TASK: write ${OUT}/scripts/v3c_prepare.py modelled on D:/VISSIM_runs/20260925_v3b/scripts/s5_prepare.py and s7_extra_seeds.py prepare/verify: call D:/VISSIM-merge/sim3/diagnostics/fast_nc_prepare.prepare_native_preserve(net, out, 9000, recording_interval_sec=5, fzp_only=True) (imported read-only) for seeds 31/41/43/47/53/37 into ${OUT}/s{seed}_v3cnc/prepared, add the prepared.json keys network_variant (v3c, base v3b + receipt), demand_variant (copied from the v3b prepared.json) and concurrent_identity_network_stem, mirror-check against the v3b prepared.json of the same seed, then run the dry run powershell -NoProfile -ExecutionPolicy Bypass -File D:/VISSIM-merge/sim3/diagnostics/fast_nc_run.ps1 -Prepared <prepared> -Output <run> (WITHOUT -Execute) for each seed, save dryrun_check.txt, and compare with the v3b dry run. Write ${OUT}/launch_lines_nc_batch1.txt with the exact WMI command lines for s31/s41/s43 (same form as D:/VISSIM_runs/20260925_v3b/extra_seeds_wmi_launch_lines.txt: cmd.exe /c powershell ... fast_nc_run.ps1 -Prepared ... -Output ... -Execute -MinimumFreeGiB 8 -AllowConcurrent > launch.log 2>&1) but DO NOT launch anything.`, { label: 'prepare', phase: 'Prepare', schema: { type: 'object', properties: { summary_ko: { type: 'string' }, launch_file: { type: 'string' }, issues_ko: { type: 'string' } }, required: ['summary_ko', 'launch_file'] } })
return { build, verdicts, prepared }
