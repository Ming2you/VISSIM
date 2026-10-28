export const meta = {
  name: 'resume-b2-stage2-and-n1f-ladder',
  description: 'Resume two interrupted tracks: (A) urban batch 2 stage 2 (C6 starvation monitor, partly written) + independent verify + fix; (B) N1F stage-2 ladder build (c100f/c80f, partly built) + independent verify + fix; no commits, no VISSIM, queue not launched',
  phases: [
    { title: 'Work', detail: 'A: C6 stage 2 / B: ladder build (parallel)' },
    { title: 'Verify', detail: 'independent checks' },
    { title: 'Fix', detail: 'fix blocking issues' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const B = R + '/urban-b2'
const WT = 'D:/VISSIM-merge/sim3-n31-urban-b2'
const REV = R + '/vsl-fixed-dsd'
const S1 = 'D:/VISSIM_runs/20260928_n1f_vsl'
const S2 = 'D:/VISSIM_runs/20260928_n1f_vsl_stage2'
const N1 = 'D:/VISSIM_runs/20260927_n1_vsl'
const SAFE = `
SAFETY (both tracks): never start/kill VISSIM or cscript; never run watchdog/cscript/ps1 *tests* (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog); offline replays only, ONE at a time, BELOW_NORMAL; never open seed 37 outputs, RM arms (v3b/v3c1) or sealed seeds 59/61/67; no commits/pushes. If the Write tool refuses to write a report file, write it with Bash (heredoc/python) instead — the report file is required. RESUME: your task was started last night and aborted by a session limit; partial scripts/results/edits exist. Treat them as untrusted scratch: reuse only after checking provenance and completeness, continue rather than redo, and say what you reused and how you checked it.
`
const COMMON_A = `
CONTEXT A (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line.
- Approved plan ${B}/BATCH2_PLAN.md (§4.2 C6, §6.9 G-C6-0..4, §10-10 initial values, §2 common rules). User decisions: batch 2 = C3 (U4+U5+U6) + C2 (U2) + C6 starvation monitor. Worktree ${WT} (branch claude/urban-batch2-20260928 at cf3ce37, uncommitted). Stage 0 and stage 1 are DONE and verified by their own gates: ${B}/impl/STAGE0.md, STAGE1.md (G-ID (a)(b)(c) passed; diff sha 9d577731…; defaults lifted to required keys; converter u40_former_defaults.py confined to deliberate old-tuning replays via is_post_u40).
- Never modify D:/VISSIM-merge/frozen/*, sim3-n31, sim3-n31-urban, sim3-n31-v3c1 or any run folder. Harness under ${B}/harness (provenance incl. worktree_diff_sha256). NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2i.
- Every new switch is a config key (absent = bit-identical); no env/getattr gates.
`
const COMMON_B = `
CONTEXT B (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line.
- USER DECISIONS 2026-09-28: VSL compliance main model -> single-value desired speeds (SDMPC network/pins unchanged until N1F complete). N1F stage 1 (c90f DSD 91 = 90-92, c90r DSD 94 = 93-95; ${S1}, FROZEN — never write there) finished and was independently verified: D1 no meaningful discharge gain, harmonisation near-complete, D6 refit at one level only (L1 A 1.56 / E 0.56). APPROVED stage 2 ladder = 8 runs: c100f (DSD 101 = uniform 100-102) and c80f (DSD 81 = uniform 80-82) x seeds 41/43/47/53; schedules: c100f Z0+Z2 2700->101, 4500->110, 7500->101; Z1 5400->101. c80f Z0+Z2 2700->91, 2850->81, 4500->101, 4650->110, 7500->91, 7650->81; Z1 5400->91, 5550->81 (|Δid| <= 20 per 150 s). Width +-1 uniform; 110 = VSL off (NC 98-140); ramps/HGV unchanged; no s31.
- Build root ${S2} (partly built last night: plan/, scripts/, 8 arm folders, reports/{dry, dry_tests.json, devcheck, harmonise_ref, n1_ref_moments, nc_moments}). Review ${REV}/VSL_FIXED_DSD_REVIEW.md §4.3-4.6 (V5: G4 direct range check only where the commanded DSD range does not overlap 110 = 98-140; DSD 101 lies inside it). N1 (frozen): ${N1}.
- Required: plan ${S2}/plan/n1f_plan_stage2_v1.json with arms, DSD blocks 81/91/101 (stage-1 XML convention), schedules, gates G0 (2700 s prefix vs same-seed v3b NC refs), G1/G2, G3 (network = N1 c100/c80 arm network + declared blocks only), G4 (V5-restricted, declared exactly), rules D1-type (c100f-c100, c80f-c80, pair 2, +3 % threshold), D2, D3, D5 (four metrics; D5 tool included from the start), D6-ladder = fixed-regime law refit on c80f + c90f (stage-1 moments, read-only, sha pinned) + c100f with the N1 selection rule; prepared folders for 8 arms (G3 each, no foreign absolute paths, no RW_* leakage); dry tests (block audit tampering, step rule, compile_profile ids, G0 +/- controls, extract/fzp_pass/moments reproduce N1 c100/c80, fit self-test); analysis freeze receipt + PREDECLARATION.md written before any run; queue (max 4 VISSIM PC-wide, waits, never kills, G0 at >= 2750 s, STOP file) batch 'stage2' = 8 arms; exact WMI launch command in ${S2}/README.md. Do NOT launch.
`
const RES = { type: 'object', properties: { summary_ko: { type: 'string' }, gates_ko: { type: 'string' }, changed_files: { type: 'array', items: { type: 'string' } }, stop: { type: 'boolean' }, launch_ko: { type: 'string' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'gates_ko'] }
const V = { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] }

async function trackA() {
  const s2 = await agent(`${COMMON_A}${SAFE}
TASK STAGE 2 (plan §4.2, §6.9 G-C6-0..4). Partial state: ${WT}/evaluation/controllers/starvation_monitor.py exists (untracked), ${B}/impl/stage2/ holds c6_tests_block.py, explore_s1_3600, prev_reader_audit.json, s1/, smoke/, tunings/, suites_stdout.txt. Finish: starvation_monitor.py (read-only, called at the end of the decision where plan A:13981..:13991 was — re-locate in the edited adapter; output metadata['starvation_monitor'] + one stdout line 'starvation' capped at 512 bytes, VBS unchanged), config key urban.diagnostics.starvation_monitor {floor_tol_s, min_stopped_per_lane, n_consecutive, boundary_capacity_bound_k} with the §10-10 initial values (absent key = bit-identical), unit tests (settings validation, synthetic prior streak, error capture, name collision, stdout cap, state immutability), the previous-action reader static audit and the two-decision chain tool (G-C6-4), and the S1 check: it flags SC109 p3 in the lock-in window while actions stay bit-identical; suites no new failure vs stage 0/1. Write ${B}/impl/STAGE2.md; stop=true on failure.`, { label: 'A:stage2-C6', phase: 'Work', schema: RES })
  if (!s2 || s2.stop) return { s2 }
  const v = await agent(`${COMMON_A}${SAFE}
Stage 2 report: ${JSON.stringify(s2)} (and ${B}/impl/STAGE0.md, STAGE1.md, STAGE2.md)
TASK (independent verifier of stages 0-2): review git diff of ${WT} against cf3ce37 (+ untracked) for behaviour changes when keys are absent, env/getattr gates, dead-code removal that is actually live (trace call paths), the former-defaults converter scope, and any C6 path that can touch actions or state; re-run G-ID on a sample (10 R-obs-b states + one S1 SDMPC decision) and the C6 unit tests yourself; check STAGE*.md claims against outputs. Report blocking issues (real defects only).`, { label: 'A:verify', phase: 'Verify', schema: V })
  let fix = null
  if (v && v.blocking && v.blocking.length) {
    fix = await agent(`${COMMON_A}${SAFE}\nVerifier blocking issues: ${JSON.stringify(v.blocking)}\nTASK: fix what is real in ${WT}, re-run affected gates, explain rejected items. Write ${B}/impl/STAGE0-2_FIX.md.`, { label: 'A:fix', phase: 'Fix', schema: RES })
  }
  return { s2, v, fix }
}

async function trackB() {
  const b = await agent(`${COMMON_B}${SAFE}
TASK: finish the N1F stage-2 build under ${S2} to the Required list above (check every existing piece first, especially whether dry tests passed and whether the freeze/PREDECLARATION exist and were written before any run — no run folders may exist). Return the exact launch command.`, { label: 'B:build', phase: 'Work', schema: RES })
  if (!b) return { b }
  const v = await agent(`${COMMON_B}${SAFE}
Build report: ${JSON.stringify(b)}
TASK (independent verifier, adversarial): (a) G3 yourself on all 8 arm networks (only declared DSD blocks vs the N1 c100/c80 arm networks; XML form equal; no other byte changes); (b) fixed profiles differ from N1 c100/c80 only in the declared ids; step rule holds; ids exist; (c) plan rules and freeze cover plan + all tools + stage-1 inputs used by D6-ladder (sha pinned) + D5; G4 respects V5; (d) queue cannot exceed 4 VISSIM, never kills, stops on G0 failure; launch line correct; (e) stage 1 (${S1}) untouched since 21:19 yesterday; any defect found by ${S1}/reports/verify/ not inherited. Report blocking issues only for real defects.`, { label: 'B:verify', phase: 'Verify', schema: V })
  let fix = null
  if (v && v.blocking && v.blocking.length) {
    fix = await agent(`${COMMON_B}${SAFE}\nVerifier blocking issues: ${JSON.stringify(v.blocking)}\nBuild report: ${JSON.stringify(b)}\nTASK: fix what is real under ${S2} (re-freeze before any run if anything frozen changes), re-run affected checks, explain rejected items; append a fix section to ${S2}/README.md; return the final launch command.`, { label: 'B:fix', phase: 'Fix', schema: RES })
  }
  return { b, v, fix }
}

phase('Work')
const [A, Bt] = await parallel([() => trackA(), () => trackB()])
return { A, B: Bt }
