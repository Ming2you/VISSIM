export const meta = {
  name: 'urban-batch2-impl-stages0-2',
  description: 'Urban batch 2 implementation, stages 0-2 of BATCH2_PLAN.md: prep (new worktree from cf3ce37, harness parametrisation, suites, baseline reproduction), U4-0 bit-identical cleanup with G-ID, C6 starvation monitor with G-C6; independent verification; no commits, no VISSIM',
  phases: [
    { title: 'Prep', detail: 'stage 0' },
    { title: 'U4-0', detail: 'stage 1 bit-identical cleanup' },
    { title: 'C6', detail: 'stage 2 starvation monitor' },
    { title: 'Verify', detail: 'independent review + fix' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const B = R + '/urban-b2'
const WT = 'D:/VISSIM-merge/sim3-n31-urban-b2'
const COMMON = `
CONTEXT (absolute paths). Korean prose in reports; mark [실행]/[읽음]/[추론]; cite file:line.
- The approved plan is ${B}/BATCH2_PLAN.md (read §0-§7 fully, esp. §2 common rules, §3 worktree plan, §4.0-4.2, §5, §6.1, §6.2, §6.9, §8, §10). Data artefacts: ${B}/u4_saturation_table.json, u5_contract_draft.json, u6_diagnosis.md, code_map.md, c6_dryrun.py/json.
- USER DECISIONS (binding): batch 2 = C3 (U4+U5+U6, all-or-nothing) + C2 (U2) + C6; U5 covers ALL overcounted groups (v3b: 53) AND native groups (Q1 = apply U4 and U5 to native, 12 overcounted native groups); Q2 = fix the SC105/SC1 shared left-lane phase authority to p3 with an evidence file (like the U1 SC7 correction) and statically reduce SC7's serial-head group; interim static reduction until the evidence file exists; Q3 = no v3b closed-loop run; the plan's §10 author choices stand unless a verifier finds a defect. Development on the v3b-pinned trees; tables re-derived on v3c1 later.
- Worktree: create ${WT} as a git worktree of D:/VISSIM-merge/repo on a NEW branch claude/urban-batch2-20260928 starting at cf3ce37 (the urban batch-1 commit; D:/VISSIM-merge/sim3-n31-urban is on claude/urban-fix-v3b-20260925 at cf3ce37). Do NOT commit, push, rebase or touch other branches/worktrees; leave changes uncommitted in ${WT}. Never modify D:/VISSIM-merge/frozen/*, D:/VISSIM-merge/sim3-n31, D:/VISSIM-merge/sim3-n31-urban or any run folder under D:/VISSIM_runs.
- Replays: offline only (make_replay_state_v2.py prepare + replay_decision_n31.ps1 -Root ${WT} or ${R}/xreplay/alt_replay.ps1), ONE at a time, BELOW_NORMAL, NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2i. Never start/kill VISSIM or cscript; never run watchdog/cscript/ps1 *tests* (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Four VISSIM runs (N1 B5) and a gate-evaluation workflow run concurrently: keep CPU modest. Never open s37, RM arms or sealed seeds.
- Every new switch is a config key (absent = bit-identical); no env/getattr gates; superseded code isolated, not flagged. Harness scripts live under ${B}/harness (copies parametrised by tree path — never measure an old tree by accident). Write reports under ${B}/impl/.
`
const S = { type: 'object', properties: { summary_ko: { type: 'string' }, gates_ko: { type: 'string' }, changed_files: { type: 'array', items: { type: 'string' } }, stop: { type: 'boolean' }, open_issues_ko: { type: 'string' } }, required: ['summary_ko', 'gates_ko', 'stop'] }
phase('Prep')
const s0 = await agent(`${COMMON}\nTASK STAGE 0 (plan §4.0, §6.2, §7 row 0): create the worktree/branch, parametrise the harness copies by tree path, run the existing n31 suites (except the forbidden tests), reproduce the batch-1 baseline numbers (§6.2) and the S1 1800/6300 self-config decision reproduction, record fixture list and the timing baseline (deterministic counters + wall clock). Write ${B}/impl/STAGE0.md. Set stop=true if any stop rule of §7 fires.`, { label: 'stage0', phase: 'Prep', schema: S })
if (s0 && s0.stop) return { s0 }
phase('U4-0')
const s1 = await agent(`${COMMON}\nStage 0 report: ${JSON.stringify(s0)}\nTASK STAGE 1 (plan §4.1, §6.1 G-ID (a)(b)(c)): lift the code defaults to explicit config keys, split the _LG_KINDS/_LTO/_SUS_SIGS setup into its own install function, isolate dead branches and remove dead keys only where a grep of every config in the repo shows no use, flatten-diff check, then run G-ID: default tuning replay 61/61 IDENTICAL on R-obs-b states, and the S1/S0e SDMPC decision replays identical (deterministic counters too). Write ${B}/impl/STAGE1.md; stop=true on any G-ID failure.`, { label: 'stage1', phase: 'U4-0', schema: S })
if (s1 && s1.stop) return { s0, s1 }
phase('C6')
const s2 = await agent(`${COMMON}\nStage 0/1 reports: ${JSON.stringify([s0, s1])}\nTASK STAGE 2 (plan §4.2, §6.9 G-C6-0..4): implement evaluation/controllers/starvation_monitor.py (read-only, called at the end of the decision between A:13981 and :13991, output metadata['starvation_monitor'] + one stdout line 'starvation' capped at 512 bytes, VBS unchanged), config key urban.diagnostics.starvation_monitor {floor_tol_s, min_stopped_per_lane, n_consecutive, boundary_capacity_bound_k} with the §10-10 initial values, unit tests (settings validation, synthetic prior streak, error capture, name collision, stdout cap, state immutability), the previous-action reader static audit and two-decision chain tool (G-C6-4), and check on S1 states that it flags SC109 p3 in the lock-in window while actions stay bit-identical. Write ${B}/impl/STAGE2.md; stop=true on failure.`, { label: 'stage2', phase: 'C6', schema: S })
phase('Verify')
let v = await agent(`${COMMON}\nReports: ${JSON.stringify([s0, s1, s2])}\nTASK (independent verifier): review the diff in ${WT} (git diff against cf3ce37) for behaviour changes when keys are absent, env/getattr gates, dead-code removal that is actually live (trace call paths; the whose_code/resolve tools cannot judge SDMPC-31), and C6 paths that can touch actions; re-run G-ID on a sample (10 R-obs-b states + one S1 SDMPC decision) and the C6 unit tests yourself. Report blocking issues.`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
let fix = null
if (v && v.blocking && v.blocking.length) {
  fix = await agent(`${COMMON}\nVerifier blocking issues: ${JSON.stringify(v.blocking)}\nTASK: fix what is real in ${WT}, re-run the affected gates, explain rejected ones. Write ${B}/impl/STAGE0-2_FIX.md.`, { label: 'fix', phase: 'Verify', schema: S })
}
return { s0, s1, s2, v, fix }
