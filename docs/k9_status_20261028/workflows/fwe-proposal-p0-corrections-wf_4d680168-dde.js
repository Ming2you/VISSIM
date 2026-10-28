export const meta = {
  name: 'fwe-proposal-p0-corrections',
  description: 'Apply the 17 user-approved P0 corrections (P0_REPORT.md §2) to FWE_STRUCT_PROPOSAL.md, keep the old version, then independently verify every correction and that nothing else changed',
  phases: [
    { title: 'Apply', detail: 'edit proposal' },
    { title: 'Verify', detail: 'independent diff check' },
  ],
}
const D = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/fwe-struct'
const COMMON = `
CONTEXT (absolute paths). Korean prose. Mark [읽음]/[실행]/[추론].
- Target document: ${D}/FWE_STRUCT_PROPOSAL.md (FW_E plant structure proposal, 2026-09-27).
- Corrections to apply: ${D}/p0/P0_REPORT.md §2 table (17 rows, "제안서 정정 목록"), user-approved on 2026-09-27 as part of the P0 bundle ("17 정정 반영"). Also read P0_REPORT.md 부록 R for any correction of these rows.
- Later facts that the document should point to (do NOT rewrite the proposal around them, add one short dated note where the proposal states the old VSL law or the old action set): N1 native VSL step experiment finished; user decision 2026-09-28: plant VSL law = L1 (Carlson A 0.94, E 1.44, alpha 0) and action set {80,90,100,110}; evidence D:/VISSIM_runs/20260927_n1_vsl/reports/N1_RESULTS.md. The FW_E bundle-1 (F1+F8) is not implemented yet.
- Scope: text/documentation only. Only the files named here may be written. Do not touch any repository, run folder, or memory file. Row 16 is a repository discrepancy outside the proposal: add a short note in the proposal's open-issues place pointing to it, do not edit the repository. Row 17 is a memory annotation that was already applied: record it as done, do not edit memory.
`
phase('Apply')
const a = await agent(`${COMMON}
TASK: 1) Copy the current proposal byte-for-byte to ${D}/FWE_STRUCT_PROPOSAL_v1_before_p0.md (verify sha256 equal). 2) Edit ${D}/FWE_STRUCT_PROPOSAL.md: apply each of the 17 corrections at the cited lines (line numbers refer to the v1 copy; find the passages by content if they drifted), tagging each changed passage with "(P0 정정 n)". Keep the author's structure, keep all other text unchanged. 3) Add a dated header line (2026-09-28 개정: P0 정정 17건 반영, N1 결과 주석) and an appendix "부록 P0: 정정 반영 기록" with one row per correction: number, location(s) changed, old wording (short), new wording (short), or why a row needed no text change. 4) Write the diff summary to ${D}/p0/PROPOSAL_P0_APPLY.md. Return a JSON with rows applied, rows with no change and why, and the sha256 of old/new files.`, { label: 'apply', phase: 'Apply', schema: { type: 'object', properties: { applied: { type: 'array', items: { type: 'string' } }, not_changed_ko: { type: 'string' }, sha_old: { type: 'string' }, sha_new: { type: 'string' }, summary_ko: { type: 'string' } }, required: ['applied', 'summary_ko'] } })
phase('Verify')
const v = await agent(`${COMMON}
Apply report: ${JSON.stringify(a)}
TASK (independent verifier; do not trust the report): diff ${D}/FWE_STRUCT_PROPOSAL_v1_before_p0.md against ${D}/FWE_STRUCT_PROPOSAL.md. For each of the 17 rows check that the new wording matches P0_REPORT.md §2 (and 부록 R) exactly in substance, cites the right file:line, and did not drop caveats. Check that every changed hunk belongs to a correction, the header, the appendix, or the N1/L1 note; flag any other change. If you find a real defect, fix it in the proposal and record the fix in ${D}/p0/PROPOSAL_P0_APPLY.md under a "검증" section. Return blocking issues left (should be empty after fixing) and a Korean note.`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { fixed: { type: 'array', items: { type: 'string' } }, blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
return { a, v }
