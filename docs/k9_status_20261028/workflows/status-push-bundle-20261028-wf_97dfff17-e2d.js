export const meta = {
  name: 'status-push-bundle-20261028',
  description: 'Build a push bundle for the user: STATUS digest (diagnoses, code, decisions, future tasks) + selected scratch reports/predeclarations/tools/patches/workflow scripts with manifest and secrecy scan; adversarial verify. No git operations (main session commits and pushes)',
  phases: [
    { title: 'Build', detail: 'select+copy files, draft STATUS digest (parallel)' },
    { title: 'Verify', detail: 'digest numbers vs sources, secrecy and size scan, fixes' },
  ],
}

const S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const K8 = S + '/k8'
const WF = 'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/workflows/scripts'
const MEM = 'C:/Users/TRLAB/.claude/projects/C--Users-TRLAB-Desktop----/memory'
const B = S + '/push_bundle/docs/k9_status_20261028'

const RULES = `
HARD RULES:
- Korean output (files + return), plain words, short sentences, explain abbreviations first time. Tag claims [실행]/[읽음]/[추론]/[계산]. No verdict words (win/lose, 승/패, 개선 판정 등) — report numbers and signs.
- Write ONLY under ${S}/push_bundle/. Read-only everywhere else. NO git commands that change anything (no add/commit/branch/push) — the main session does git. No VISSIM, no heavy jobs, no lock needed (light reads only; never open FZP/npz).
- SECRECY: never include numeric results for sealed seeds 37/59/61/67 (any network), codex 64cf-s59/s61/s67, or v3c3-s47 / v3c3-s53 (blind samples). Files that contain such values (tables, json, logs) are EXCLUDED; text that only names them as excluded/sealed is fine. Never copy anything from sealed/ folders or nc_s47/nc_s53 caches. Never include credentials/tokens.
- Ω701 numbers always shown with ④ and Ω-outside when a result line is quoted; urban roads = codex partition; seeds with network prefix.
`

const CTX = `
CONTEXT
- Target repo (for layout only, do not modify): D:/VISSIM-merge/sim3-n31-k8 (GitHub Ming2you/VISSIM), current deploy commit c20aff1d on claude/k92-b1-20261016 (pushed); K8 branch b9734abe. The bundle will be committed under docs/k9_status_20261028/ on a new branch.
- Sources: decision log ${K8}/K9_1_J1_NOTES_20261013.md (sha 7a74ea9c…, D-K9-58..116), amendments ${K8}/K8_PREDECLARATION_AMENDMENT_*.md (24..34, C1, C1_2 and their FIXED files), work folders under ${K8}/ (k92/bundle1, k92/va, j1, rmcause, codex_handoff incl. a0/a1/b0/b/fo, c_port incl. c1 and c1/guard and c1/guard/general and c1/tools, fwe_decomp, vsl_v3c3 incl. o1o2, vsl_plant), workflow scripts ${WF}/*.js, memory files ${MEM}/*.md (project memory: use as an index of findings; copy only the files relevant to this project: those starting with vissim-, codex-, c-port-, fwe-, omega701-, freeway-, calibration-, feedback-minimize-; never other personal files).
- Latest results to cover in the digest (read the files): FO (codex SDMPC freeway-only arm on v3c3) ${K8}/codex_handoff/fo/FO_REPORT.md r2 + VERIFY_FO.md; C1 status ${K8}/K8_PREDECLARATION_AMENDMENT_C1_2.md (fixed dfe9809b…) and ${K8}/c_port/c1/ (P0_PROBE r2, C1_PROBE_RESULTS, LOG, latest stop at P0-17 with user questions Q-A..Q-F — find the P0-17 report/log in c_port/c1); general guard ${K8}/c_port/c1/guard/general/ (GENERAL_GUARD_DESIGN r1, DATA, INVENTORY); FW_E decomposition ${K8}/fwe_decomp/FWE_DECOMP.md r2 + VERIFY_FWE; VSL ${K8}/vsl_v3c3/VSL_RESULTS.md r2; our plant VSL ${K8}/vsl_plant/VP_RESULTS.md r2 + VERIFY_VP; codex handoff ${K8}/codex_handoff/ (HANDOFF_RESULTS r2, A1_B0_RESULTS r2, B_RESULTS r2, VERIFY_B); C prep ${K8}/c_port/ (C_PREP_RESULTS r2, C1_DESIGN_DRAFT r2, INPUT1099 r2, READBACK_METER, VSL_OFFLINE r2); meter cause ${K8}/rmcause/ (METER_CAUSE r2, METER_NEXT r2, r2c_n/METER_NEXT2 r2, K9_3_DESIGN_DRAFT r2); V-A ${K8}/k92/va/analysis/VA_REPORT.md (+ r4 correction), validity; J1 ${K8}/j1/analysis.
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

phase('Build')
const [sel, dig] = await parallel([
  () => agent(`${RULES}\n${CTX}\nTASK (Select and copy): copy into ${B}/ with this layout: decisions/ (decision log), predeclarations/ (amendments + their FIXED/sha files + PRE_*.md/COMPARE_RULE_*.md/GATE*_RULE.md from work folders), reports/<track>/ (all .md reports of each work folder, keeping r1/r2 files; tracks: k92_bundle1, va, j1, rmcause, codex_handoff, codex_fo, c_prep, c1, c1_guard, c1_guard_general, fwe_decomp, vsl_v3c3, vsl_plant), tools/<track>/ (all .py .ps1 .sh .vbs .patch .diff written by us in scratch, keeping subfolder names), small_data/<track>/ (only .json/.csv/.txt/.sha256 ≤ 200 KB that are results/pins/manifests and pass the secrecy rule), workflows/ (the .js scripts), memory/ (project memory files listed). Skip: files > 1 MB (list them), npz/fzp/att/lsa/err/log > 200 KB, anything under sealed/, any cache, any file failing the secrecy scan (grep each candidate for s47/s53/s37/s59/s61/s67 tokens and inspect hits: exclude if numeric results of those seeds appear; list exclusions with reason). Write ${B}/MANIFEST.tsv (repo-relative path, source path, bytes, sha256) and ${B}/EXCLUDED.tsv (source path, bytes, reason). Total bundle size target ≤ 80 MB; report the total. Return pass=true with counts/sizes.`, { label: 'select', phase: 'Build', schema: SCHEMA }),
  () => agent(`${RULES}\n${CTX}\nTASK (Digest): write ${B}/STATUS_20261028.md — the one document the user reads to know everything. Sections: 0 한눈에 (≤ 20 lines: where we are, what is known, what is next); 1 배경과 지표 정의 (networks v3c3/64cf, seeds, Ω635/Ω701, ④ ④a ④b, Ω 밖, ① ②, urban roads codex partition, integration forms, NC3/V-A/J1/B/FO/A1 arms); 2 진단 사항 — by topic, each finding with numbers, tag and source file (K8/J1 waiting transfer, K9-2 bundle 1 and V-A results, meter never asked (decision-layer causes), codex handoff 8 % definition and A1 reproduction, network/demand differences 64cf vs v3c3, B results and the SC1001 SG2 → 1099 chain, readback, VSL offline and v3c3 VSL-only runs, our plant VSL response and VSL-independent biases (cell 18, M1, B1/cell 12, VSb), FW_E decomposition (NC FW_E congestion, common cell 5–9 component, B meter timing on 10639, V-A FW_E ~0), FO results (FO − NC3, B − FO, ratio 0.86–1.06), Ω701 initial-state channel (29 connectors), storage-capacity guard data (user rule vs U), C1 P0 status and the P0-17 definitional conflicts; plus earlier known defects list D1–D5 and K-series); 3 코드 — what is committed where (repo, branches, commits c20aff1d/b9734abe etc.), frozen trees and runs (paths), what is only in scratch (tools, probe patches, guard evidence builder) and is included in this bundle (refer to tools/), what is NOT yet implemented (C1 branch not created); 4 결정 기록 요약 — table D-K9-58..116 one line each (question → answer → effect); 5 지금 상태 by track (C1, C1-G guard, FO, FW_E decomposition, VSL v3c3, our plant VSL/B1 bias, K9-3 on hold, cleanup items); 6 앞으로 할 일 — ordered list with owner (user decision vs work), including the open user questions verbatim in short form: C1 Q-A..Q-F, FO §9 decisions 1–3 + r2 acceptance, plant B1-bias work (D-K9-115 next), V2 C9 rerun, VSL items D4–D9, K9-3 D1/D2, correction memos, scratch tree cleanup, closed-loop C1 (3 seeds, asks before launch); 7 규칙과 교훈 (run rules, predeclaration discipline, VISSIM launch rules, lessons list incl. new ones: PowerShell Add-Content blocked by readers, response_token path-dependence, R1 2-ULP tolerance, circled-digit approval-dialog issue is not needed); 8 파일 지도 (where each report sits in this bundle: relative links to reports/ and predeclarations/). Use relative links into the bundle layout described (decisions/, predeclarations/, reports/<track>/, tools/<track>/, small_data/, workflows/, memory/). Return pass=true with sha256 and line count.`, { label: 'digest', phase: 'Build', schema: SCHEMA }),
])

phase('Verify')
const ver = await agent(`${RULES}\n${CTX}\nBuild results: ${JSON.stringify([sel, dig]).slice(0, 6000)}\nTASK (Verify and fix): (1) check every number in ${B}/STATUS_20261028.md against its cited source (sample at least 60 numbers across all sections, all of section 0 and the FO/FW_E/C1 parts); fix errors in place and list them; (2) check every relative link in STATUS resolves to a file in the bundle (fix links or add the file if it is in scratch and passes rules); (3) re-run the secrecy scan over the whole bundle (s47/s53/sealed seed numeric values, credentials) and remove offenders (update MANIFEST/EXCLUDED); (4) check sizes (no file > 1 MB, total ≤ 80 MB) and that no file under the bundle is binary except allowed patches; (5) regenerate MANIFEST.tsv sha256 after fixes. Write ${B}/VERIFY_BUNDLE.md. Return status, Korean summary (≤ 20 lines), artifacts (bundle root, file count, total MB, STATUS sha), open.`, { label: 'verify', phase: 'Verify', schema: SCHEMA })
return { sel, dig, ver }
