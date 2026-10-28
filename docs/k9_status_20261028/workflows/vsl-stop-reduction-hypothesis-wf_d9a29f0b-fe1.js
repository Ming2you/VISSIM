export const meta = {
  name: 'vsl-stop-reduction-hypothesis',
  description: 'Offline test of the hypothesis "VSL reduces stopped vehicles and thereby TTT" on existing N1/N1F paired VISSIM FZPs: predeclare, compute (stops, TTT incl. outside-Omega, merge/exit flows), verify',
  phases: [
    { title: 'Predeclare' },
    { title: 'Compute' },
    { title: 'Verify' },
  ],
}

const SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = SP + '/vsl_stops'
const CTX = `
CONTEXT (absolute paths; Korean prose, concise; tag [실행]/[읽음]/[추론]; cite paths). If the Write tool refuses a file, write it with Bash/python.
- USER QUESTION (2026-10-04): "VSL reduces stopped vehicles and therefore gains TTT" - test it OFFLINE with existing data (no new VISSIM runs). Queueing logic: fewer stops alone do not reduce total delay unless bottleneck discharge rises or blocking of other flows (merges/off-ramp access) falls. Test: (1) did VSL reduce stopped vehicle-time on FW_E? (2) did FW_E TTT and network all+uninserted (④, incl. outside-Omega delay) fall, or was the stop reduction offset by more slow moving time? (3) did merges (10681, 10484, 10490, 10639 accepted) or exits (off-ramps 10643, 10682, 10481, 10483) increase when stops fell (mechanism 3)?
- DATA (READ-ONLY): N1 native VSL step experiment D:/VISSIM_runs/20260927_n1_vsl (distribution DSD arms c100/c90/c80 and the S5 control/placebo, core seeds 41/43/47/53, optional B5 s31; plan, scripts, reports/N1_RESULTS.md, N1_README, stage0/ four-metric scripts and scans), N1F stage 1 D:/VISSIM_runs/20260928_n1f_vsl (single-value c90f, c90r; reports/N1F_RESULTS.md, reports/d5 scripts) and stage 2 D:/VISSIM_runs/20260928_n1f_vsl_stage2 (c100f, c80f). Paired no-control runs of the same seeds as used in those analyses (the v3b NC runs referenced in their scripts, e.g. s<seed>_v3bnc). Read the designs to get the VSL application zone, start time, and the placebo arm. These runs are on network v3b (freeway entry still DSD 40 - the v3c2 defect); state this limitation; results are conditional on that network.
- Reuse existing extraction tools where possible (N1 fzp_pass/moments, stage0 scan/metrics, d5 scripts) and existing scans; FZP re-streaming is allowed (read-only, BELOW_NORMAL, one at a time).
- HARD RULES: read-only on run folders; write only under ${OUT}. No code changes in worktrees, no commits, no VISSIM. No sealed seeds (37, 59, 61, 67) and no codex 64cf numbers. PYTHONHASHSEED=0, python -B.
`
const P = { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, summary: { type: 'string' } }, required: ['path', 'sha256', 'summary'] }
const C = { type: 'object', properties: { report_path: { type: 'string' }, verdict: { type: 'string' }, numbers: { type: 'string' }, deviations: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'verdict', 'numbers', 'deviations'] }
const V = { type: 'object', properties: { report_path: { type: 'string' }, confirmed: { type: 'array', items: { type: 'string' } }, problems: { type: 'array', items: { type: 'string' } } }, required: ['report_path', 'confirmed', 'problems'] }

phase('Predeclare')
const p = await agent(CTX + `
TASK: PREDECLARATION ONLY (check data availability; compute no outcome). Write ${OUT}/PREDECLARATION.md (+ .sha256): arms and pairs (arm vs same-seed NC, and arm vs placebo), seeds, time window (VSL active window and after), spatial scope (FW_E cells/sections: VSL zone, upstream queue area, bottlenecks B1/B2, merges, diverges), definitions: stopped vehicle-time (v < 5 km/h; secondary v < 10), moving slow time, TTT decomposition (Δtotal = Δstopped + Δmoving), FW_E main TTT, FW_E incl. ramps, Omega TTT, ④ all + uninserted (outside-Omega delay and deletions), merge accepted counts and exit counts per 150 s, bottleneck discharge (reuse the N1 B1/B2 definitions). Decision rules: SUPPORTED if stopped time falls (paired CI upper < 0, >= 3/4 seeds same sign) AND (FW_E TTT or ④) falls (CI upper < 0) for that arm; MECHANISM-3 evidence if merge or exit counts rise with CI lower > 0 in the same arm; NOT SUPPORTED if stops fall but TTT/④ do not (offset); INCONCLUSIVE otherwise. CI method (t across seeds, k=4; also report B5 s31 separately). State the v3b network limitation.`, { label: 'predeclare', phase: 'Predeclare', schema: P })
if (!p) { return { stopped: 'predeclaration failed' } }

phase('Compute')
const c = await agent(CTX + `
TASK: COMPUTE exactly as frozen in ${p.path} (sha ${p.sha256}; verify first, do not edit). Produce per-arm, per-seed tables and the verdict for each arm (c100, c90, c80 distribution; c90f, c90r, c100f, c80f single-value), the time-binned view (150 s) showing where stops fell and whether moving time rose, and the mechanism-3 check. Write ${OUT}/RESULTS.md (Korean; 6-line summary first) and raw tables under ${OUT}/tables.`, { label: 'compute', phase: 'Compute', schema: C })

phase('Verify')
const v = await agent(CTX + `
TASK: INDEPENDENT VERIFICATION (own code under ${OUT}/verify; write ${OUT}/VERIFY.md). Inputs: ${p.path}, ${c ? c.report_path : '(compute failed)'}. Check the predeclaration sha/timestamps precede outputs; recompute stopped time, FW_E TTT and ④ for two arms x two seeds from FZP; recompute one merge/exit count series; check verdicts follow the frozen rules.`, { label: 'verify', phase: 'Verify', schema: V })

return { p, c, v }
