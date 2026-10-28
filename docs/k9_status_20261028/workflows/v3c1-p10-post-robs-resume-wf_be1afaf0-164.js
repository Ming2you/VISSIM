export const meta = {
  name: 'v3c1-p10-post-robs-resume',
  description: 'Resume of the v3c1 P10 post-R-obs checks after a session-limit abort: T5 (G1 frame + decision replays), all-110 L0/L1 run-state identity, U1 T1 re-judgement (each continuing its partial work); pairing already done (PAIR_REPORT.md); independent verify',
  phases: [
    { title: 'Checks', detail: 'T5 / L0-L1 / U1 T1 (parallel, resumed)' },
    { title: 'Verify', detail: 'independent check' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const OUT = R + '/v3c1-p10'
const COMMON = `
CONTEXT (absolute paths). Korean prose; mark [실행]/[읽음]/[추론]; cite file:line. Write only under ${OUT}/<your task>/.
- v3c1 re-pin committed as 5323faa (branch claude/repin-v3c1-20260928), frozen tree FRZ = D:/VISSIM-merge/frozen/sdmpc31_5323faa4_202609281442 (READ-ONLY; never write inside it). Worktree D:/VISSIM-merge/sim3-n31-v3c1 must stay clean (git status empty before and after; no __pycache__/tangent caches left). Plan: D:/VISSIM_runs/20260927_v3c1/reports/REPIN_PLAN.md §5.5 (items 1 and 4) and RA-6; D:/VISSIM-merge/sim3-n31-v3c1/diagnostics/sdmpc_n31_20260924/REPIN_V3C1_REPORT.md; PLANT_PORTING_GUIDE.md:579.
- R-obs finished: D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31 (no-control + obs150, seed 31, 9000 s, EXIT 0, 61 decisions). Pairing already done: ${OUT}/pair/PAIR_REPORT.md — R-obs FZP is byte-identical to v3c1 NC s31 after dropping the SDMPC runner's extra 0.10 s frame; for SDMPC-runner runs pass network/*_001.err explicitly (stage1_common.run_files picks the wrong err/inpx there). Known tool issue: tools/make_replay_state_v2.py:234-242 action_contract demands all-VSL-110 when --tuning is used; judge replays with the compare that does NOT use --tuning and report the ps1's own verdict separately.
- RESUME: this task was started at 17:37 and aborted by a session limit (~18:05-18:40). Your task folder already holds partial scripts/results from that attempt. Treat them as untrusted scratch: reuse a result only after checking its provenance (tree/HEAD/tuning sha, completeness, no errors); continue from where it stopped rather than redoing finished pieces; say in your report what was reused and how it was checked.
- Allowed: replay_decision_n31.ps1 / make_replay_state_v2.py / xreplay alt_replay.ps1 (offline replays, ONE at a time, BELOW_NORMAL, NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_p10). Forbidden: starting/killing VISSIM or cscript; watchdog/cscript/ps1 *tests* (test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Four VISSIM runs (N1F queue) and an urban batch-2 workflow run now: keep CPU modest.
- DATA DISCIPLINE: never open seed 37 outputs, any RM arm run outputs (v3b or v3c1 *_rm*), or sealed seeds 59/61/67. v3c1 NC fit seeds 31/41/43/47/53 are allowed.
`
phase('Checks')
const RES = { type: 'object', properties: { verdict_ko: { type: 'string' }, details_ko: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, open_issues_ko: { type: 'string' } }, required: ['verdict_ko', 'details_ko'] }
const [t5, l01, u1] = await parallel([
  () => agent(`${COMMON}
TASK T5 (REPIN_PLAN §5.5-4), folder ${OUT}/t5: (1) test_g1_frame with N31_G1_STATE=<R-obs>/decisions_sdmpc31_v3c1_nc_s31/state_000900.json (partial: g1_frame_pytest.txt, g1_frame_numbers.json); (2) decision replays of all 61 R-obs decisions with the deployed default tuning (config_n31_v2.json of 5323faa), one at a time; verdict = non-tuning compare IDENTICAL for every decision plus deterministic counters equal (partial: t5_chain_a/b, A/chain.log); (3) replayed SDMPC VSL values all in {80,90,100,110} and block-0 allowed set {80..110} in decision metadata; (4) wall time per replay. If the full 61 would exceed ~3 h from now, do every state from 900 s at 150 s spacing but at least 20 spread over the horizon, and say which. Write ${OUT}/t5/T5_REPORT.md.`, { label: 't5', phase: 'Checks', schema: RES }),
  () => agent(`${COMMON}
TASK all-110 L0/L1 (REPIN_PLAN §5.5-1, run-state part), folder ${OUT}/l0l1: on at least three R-obs states (e.g. 900, 3600, 6300 s) run the plant rollout with the committed L1 reference and with an L0 reference variant (pre-repin Carlson A 0.5 / E 4 vsl_fd_response, scratch only) with all VSL commands 110: predicted values must be bit-identical; the FW_E VSL-axis derivatives must differ. Partial work: compare_l0l1.py, l0l1_scalar.py, l0l1_tangent.py, refs/, out/, logs/. Write ${OUT}/l0l1/L0L1_REPORT.md.`, { label: 'l0l1', phase: 'Checks', schema: RES }),
  () => agent(`${COMMON}
TASK U1 T1 re-judgement on v3c1 (RA-6), folder ${OUT}/u1t1: the urban batch-1 test T1 (${R}/urban-b1/t1_v2.py and its report in ${R}/urban-b1/) judged U1 beta by independent FZP vehicle trajectories on 119 approaches (+-0.05; default 48 -> U1 105 of 119 on v3b). Re-run for v3c1: plant beta = committed routing_v3c1 (default) and routing_v3c1_2 (U1) from 5323faa; FZP evidence = v3c1 NC fit seeds 31/41/43/47/53 plus the R-obs capture as t1_v2 requires (R-obs FZP = NC s31 FZP, see PAIR_REPORT). Partial work: capture_v3c1.py, capture/ (captures.log up to 18:39), cfg/, compare_v3b.py, fzp_identity*. Keep the rule identical; report pass counts default vs U1, the 7 stop lines of V1/V3-V7, and which v3b failures disappeared or remain. Write ${OUT}/u1t1/U1T1_REPORT.md.`, { label: 'u1t1', phase: 'Checks', schema: RES }),
])
phase('Verify')
const v = await agent(`${COMMON}
Reports: ${JSON.stringify({ t5, l01, u1 })}\nAlso read ${OUT}/pair/PAIR_REPORT.md.
TASK (independent verifier): re-check each verdict at the source: re-run at least 3 decision replays yourself (incl. one late state), re-run one L0/L1 state, recount the U1 T1 pass numbers from the output files, recheck the pairing claim on one 150 s window of the FZPs. Confirm the worktree is still clean and nothing was written into the FRZ or run folders, and no forbidden data/tests were touched. Report blocking issues (real defects only) and a Korean summary of what P10 established.`, { label: 'verify', phase: 'Verify', schema: { type: 'object', properties: { blocking: { type: 'array', items: { type: 'string' } }, notes_ko: { type: 'string' } }, required: ['blocking', 'notes_ko'] } })
return { t5, l01, u1, v }
