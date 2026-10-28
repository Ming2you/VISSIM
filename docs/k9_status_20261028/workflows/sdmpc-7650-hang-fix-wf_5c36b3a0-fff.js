export const meta = {
  name: 'sdmpc-7650-hang-fix',
  description: 'Root-cause and fix the S0d 7650 s decision failure: roundoff-negative ramp stock rejected in a tangent worker, and the parent waiting forever on the dead worker',
  phases: [
    { title: 'Diagnose', detail: 'where the -8.9e-16 comes from; why the live run hung instead of failing' },
    { title: 'Fix', detail: 'minimal fixes + tests, uncommitted' },
    { title: 'Verify', detail: 'adversarial: no masking of real negatives, hang path closed, replays' },
    { title: 'Settle', detail: 'address verifier findings' },
  ],
}
const R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad'
const W = 'D:/VISSIM-merge/sim3-n31'
const COMMON = `
CONTEXT (absolute paths, forward slashes)
- SDMPC-31 on network v3b. Code: ${W}, branch claude/sdmpc-n31-20260924 @ 9152821 (clean tracked tree; do not touch untracked data). The failed live run used the frozen copy D:/VISSIM-merge/frozen/sdmpc31_91528210_202609251949 (identical code; READ-ONLY, never edit frozen trees).
- Failure: live run D:/VISSIM_runs/20260925_sdmpc31_v3b/sdmpc31_v3b_s31d (read-only). Decisions 900..7500 s all OK (4 used the Dykstra QP fallback). Decision 7650: state written 06:41:54; progress log (decisions_sdmpc31_v3b_s31d/action_007650.joint.progress.jsonl) shows sdmpc_pfo_start and sdmpc_surrogate_batch_start (1 prediction with derivatives, reverse_workers_per_prediction 8) at 3.5 s, then nothing; the watchdog killed the run after 2418 s idle (StallSec 2400). No traceback in the runlog.
- Offline replay of 7650 with the frozen code (${R}/hang7650/replay, made with D:/VISSIM-merge/sim3-n31/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py prepare + replay_decision_n31.ps1 -ReplayDir <dir> [-Root <tree> -SkipFreezeVerify] [-ExtraPythonPath <dir>]) did NOT hang: it failed after 32 s with, in a tangent worker (evaluation/controllers/sdmpc_tangent_worker.py main -> run -> predict -> rollout_endpoint.evaluate_price_point -> _rollout -> run_coupled_interval -> lane_coupling.run_interval:119 ledger.assert_stocks(model_inventory) -> control_area_objective.model_stock_values -> _nonnegative:76): ValueError: ramp:RM_C10681 must be finite and nonnegative: Dual(-8.881784197001252e-16, None). Full stderr: ${R}/hang7650/replay/replay/adapter_stderr.txt. A faulthandler sitecustomize (dumps stacks every 300 s per process) is in ${R}/hang7650/site; stacks go to ${R}/hang7650/stacks.
- Replay tools do not start VISSIM and are allowed. Python: C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe, env OMP/NUMBA/MKL/OPENBLAS threads 1, PYTHONUTF8=1, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH="C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc;C:/Users/TRLAB/Documents/ChatGPT/VISSIM/.review-deps/sdmpc-numba;${W}". The live runs use system Python 3.12 (C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe) via the VBS runner; check which interpreter/worker launch path the adapter and tangent workers use.
- Three VISSIM no-control runs are live now (D:/VISSIM_runs/20260925_v3b/s{43,47,53}_v3bnc): never start or kill VISSIM/cscript, never touch those folders or D:/VISSIM-merge/frozen/*. Never run watchdog/cscript/ps1 TESTS (forbidden: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog). Keep CPU modest (one replay at a time).
- Do NOT commit or push. Write scratch only under ${R}/hang7650/. Text fields in Korean; mark numbers [실행]/[읽음].
`
const DIAG = {
  type: 'object',
  properties: {
    negative_origin_ko: { type: 'string' },
    primal_negative: { type: 'boolean' },
    hang_mechanism_ko: { type: 'string' },
    hang_reproduced: { type: 'boolean' },
    other_sites_ko: { type: 'string' },
    fix_plan_ko: { type: 'string' },
  },
  required: ['negative_origin_ko', 'primal_negative', 'hang_mechanism_ko', 'hang_reproduced', 'other_sites_ko', 'fix_plan_ko'],
}
phase('Diagnose')
const diag = await agent(`${COMMON}
TASK (diagnose, read-only on code):
1. Find exactly where ramp:RM_C10681's stock becomes -8.9e-16 in the tangent (Dual) rollout at 7650: which update (lane ramp runtime / physical ramp boundary / freeway accounting / meter discharge), whether the primal (real part) is negative too or only a Dual artefact, and whether the non-Dual (primal-only) prediction of the same state stays nonnegative. Instrument via ExtraPythonPath sitecustomize or a scratch harness, not by editing repo files.
2. Explain why the live run hung for 40 minutes instead of failing like the replay: trace how sdmpc spawns and collects tangent/reverse workers (sdmpc_tangent_runtime, sdmpc_tangent_worker, prediction worker pools, pipes/queues/subprocess, timeouts) and how the adapter is invoked by the VBS runner (stdout/stderr handling, env, interpreter). Identify the concrete deadlock or waiting path (e.g. a parent waiting on a dead child, a full pipe, a pool that never returns on a worker exception). Try to reproduce the hang offline with the live runner's conditions (interpreter, env, stdio as pipes) - within a bounded time (kill your own replay after 12 minutes if it hangs, then read the faulthandler stacks).
3. List other places where the same roundoff could trigger the same check (other stocks under _nonnegative in Dual or primal).
4. Propose the minimal fixes: (a) the roundoff - preferably clamp at the source so the stock is exactly 0 in primal and tangent when the true value is 0 (not a global loosening of the ledger check); if a tolerance is unavoidable, the smallest defensible one and only for roundoff; (b) the hang - the parent must detect a failed/dead worker and raise promptly (seconds), with the worker's traceback surfaced.`, { label: 'diagnose', phase: 'Diagnose', schema: DIAG })

const FIX = {
  type: 'object',
  properties: {
    changes_ko: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    tests_ko: { type: 'string' },
    replay_7650_ko: { type: 'string' },
    replay_others_ko: { type: 'string' },
    hang_fix_evidence_ko: { type: 'string' },
  },
  required: ['changes_ko', 'files', 'tests_ko', 'replay_7650_ko', 'replay_others_ko', 'hang_fix_evidence_ko'],
}
phase('Fix')
const fix = await agent(`${COMMON}
Diagnosis: ${JSON.stringify(diag)}
TASK: implement the minimal fixes in ${W} (uncommitted):
(a) roundoff fix at the source per the diagnosis (bit-identical results wherever the stock was not in the roundoff regime - prove it);
(b) prompt failure instead of a hang when a worker fails or dies, surfacing its traceback; must not change successful decisions.
Add unit tests (small, fast) for both; run the N31D suite (as in ${R}/verify-v3b/run_tests.sh n31 - same env) and any existing tests of the touched modules (not the forbidden ones).
Verification replays (one at a time): 7650 with -Root ${W} -SkipFreezeVerify must complete (exit 0 or 2 = replay differs because the original failed; report the stage log); at least two earlier S0d decisions (e.g. 7500 and 3000: make_replay_state_v2.py prepare D:/VISSIM_runs/20260925_sdmpc31_v3b/sdmpc31_v3b_s31d/decisions_sdmpc31_v3b_s31d <T> <dir>) must replay IDENTICAL with -Root ${W} (compare verdict IDENTICAL). Show evidence that the hang path now fails fast (e.g. a test that kills or fails a worker and asserts the parent raises within a timeout).`, { label: 'fix', phase: 'Fix', schema: FIX })

const FINDINGS = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string' }, claim_ko: { type: 'string' }, evidence_ko: { type: 'string' } }, required: ['severity', 'claim_ko', 'evidence_ko'] } },
  },
  required: ['ok', 'findings'],
}
phase('Verify')
const verifs = await parallel([
  () => agent(`${COMMON}
Diagnosis: ${JSON.stringify(diag)}
Fix report: ${JSON.stringify(fix)}
You are an adversarial verifier (lens: numerical correctness). Try to break the roundoff fix: can it hide a genuinely negative stock (mass loss), change any successful prediction, or behave differently in primal vs Dual (tangent consistency, FD vs tangent)? Check every site the diagnosis listed. Read the diff (git -C ${W} diff) and run small checks. Default to ok=false if unsure.`, { label: 'verify:numerics', phase: 'Verify', schema: FINDINGS }),
  () => agent(`${COMMON}
Diagnosis: ${JSON.stringify(diag)}
Fix report: ${JSON.stringify(fix)}
You are an adversarial verifier (lens: process robustness). Try to break the hang fix: worker crash, worker killed, worker exception during pickling, partial output, slow but healthy worker (must NOT be killed or failed spuriously), Windows specifics (spawn, pipes, handle inheritance), the VBS runner's stdio. Confirm the 7650 replay result and the IDENTICAL replays yourself from their outputs. Default to ok=false if unsure.`, { label: 'verify:process', phase: 'Verify', schema: FINDINGS }),
])

phase('Settle')
const settle = await agent(`${COMMON}
Fix report: ${JSON.stringify(fix)}
Verifier results: ${JSON.stringify(verifs)}
TASK: address every verifier finding that holds up (re-check each yourself first; state which you rejected and why), re-run the affected tests and the 7650 replay if code changed. Then write the final Korean report: root cause (both layers), fixes (files/lines), tests, replays (7650 + identical ones), residual risks, and the exact file list for a commit.`, { label: 'settle', phase: 'Settle', schema: { type: 'object', properties: { report_ko: { type: 'string' }, commit_files: { type: 'array', items: { type: 'string' } }, ready: { type: 'boolean' } }, required: ['report_ko', 'commit_files', 'ready'] } })

return { diag, fix, verifs, settle }