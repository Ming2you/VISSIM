# Cap margin plan: SDMPC caps = PFO-achieved + margin (option (a) only)

## What I verified (all read-only)
- **The worktree matches the live tree.** `D:\VISSIM-merge\sim3-capmargin` (branch `claude/sdmpc-cap-margin-20260923` @ 673eece) has the same content as `sim3` for all 5 target files, and they use LF endings (0 CR characters).
- **The earlier prototype applies cleanly.** `git apply --check` of `$S\cap_margin_prototype.patch` passes on sim3-capmargin. Here `$S` = `C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\cap_margin`.
- **Both gate values replay exactly today:**
  - 900 s: `D:\VISSIM_runs\20260923_sdmpc\capmargin\wt_base_900` (unpatched sim3-capmargin, via replay_decision.ps1) gives objective 393.91612458424544 and next duals [2.3869628341616655, 0.1408151058737363]. total_rollouts is 9 and pfo_to_sdmpc_extra_rollouts is 0. Its CSV is byte-identical to the native `action_000900.csv`.
  - 1050 s: `replay_1050_fix` gives 422.6749131864695 and duals [1.2288206364115695, 0.12234512221207197], with total_rollouts 7. Its CSV is byte-identical to the native `action_001050.csv`.
- The only git commands I ran were `git worktree list` and `git apply --check` (in sim3-capmargin). Neither writes anything.

## 1. EDIT LIST
Make all edits in `D:\VISSIM-merge\sim3-capmargin` only. The line numbers below are from sim3 and are identical there. The fastest route is to `git apply` the LF patch `$S\cap_margin_prototype.patch`, then add the refinements marked (R).

**E1. `evaluation/parameters.json:21-24`**
- Add `"np_cap_margin_veh": 0.0` and `"nuf_cap_margin_veh_h": 0.0` to `sdmpc_pfo_cap`.
- Keep LF endings.
- Do not use `$S\apply_margin_patch.py`. It uses `Path.write_text`, which writes CRLF on Windows; its `base\`/`work\` copies are already CRLF (156/156 lines), while sim3 is LF.
- Do not put the margins in the tuning JSON. `configure` reads them only from parameters.json (`parameters.py:55-61`, and the no-fallback rule at `parameters.py:15-18`), so a tuning key would be silently ignored.

**E2. `evaluation/controllers/sdmpc_budget.py`**
- Add `import math`, plus:
  - `MARGIN_KEYS=('np_cap_margin_veh','nuf_cap_margin_veh_h')`
  - `PFO_CAP_KEYS=('max_iterations','nuf_tolerance_veh_h')+MARGIN_KEYS`
  - `checked_margin(v,name)`: `type(v) in (int,float)` (this rejects bool), finite and ≥0, else ValueError; returns `float(v)`.
  - `margins(policy)`: a strict `policy['pfo_cap_options'][key]` read with no fallback.
- In `initialize` (7-34), read the margins after the witness checks (:10-17) and the `nuf_definition` check (:22-23):
  - `np_m,nuf_m = margins(follower.cfg.network.sdmpc_options)`
  - `a_np,a_nuf = q['np']['actual'], q['nuf']['actual']`
  - `seed.N_P_star, seed.N_UF_star = a_np+np_m, a_nuf+nuf_m`, replacing :25.
  - Receipt (:26-34):
    - Set schema to `decision-pfo-budget-initialization/v2`.
    - Keep `np_cap_veh`/`nuf_cap_veh_h`, now the caps including the margin.
    - Add `achieved_np_veh`, `achieved_nuf_veh_h`, `np_cap_margin_veh`, `nuf_cap_margin_veh_h`, and `cap_rule='cap = PFO-achieved + configured nonnegative margin'`.
    - Leave `physical_commands_unchanged=True` as it is.
- (R) Reword the scope at :34 to "PFO-achieved quantities plus configured margin; not future VISSIM observations". Fix the docstring at :38, which says the center is the "achieved witness".
- **Why read from policy and not from `options`:**
  - `bind_warm_budget` re-derives `initialize` from the Query template follower's own policy (`sdmpc_tangent_surrogate.py:137-139,148-150`). That independently ties the margin to the configured policy.
  - The same dict is what gets hashed into `policy_sha256`.
  - Injecting the margin through `options` at `sdmpc.py:484` would also be consistent, but use only one of the two sources.
- **Margin 0 is bit-identical.** `x+0.0==x` bitwise except for -0.0. Both achieved values come from `math.fsum` (`area_leader_objective.py:785,791`), and on 3.12.2 fsum never returns -0.0 (mapper-verified).

**E3. `evaluation/controllers/sdmpc.py`**
- In `configure` :83-90, after the check at :88-89:
  - Require `set(pfo_cap_options)==set(sdmpc_budget.PFO_CAP_KEYS)`, else ValueError.
  - For each margin: `pfo_cap_options[key]=sdmpc_budget.checked_margin(...)`, so an int 50 and a float 50.0 hash the same.
  - The options then flow through :90 → :211 (`cfg.network.sdmpc_options`) → :480 `policy` → `token(policy)` at :464/:893.
  - That is the price-inheritance guard: `load_prices` refuses carried prices from a different margin (:461-465), and the carried duals load only after that check (:497-505).
- At :571-572, add `achieved_np`, `achieved_nuf`, `np_margin` and `nuf_margin` to the `sdmpc_pfo_budget_initialized` emit, taken from `initialization`.
- At :927, change `nuf_target_policy` to `'fresh_PFO_achieved_plus_margin_budget_each_interval_then_leader_search'`. Leave :926 `'NP <= cap; actual_merge_NUF <= cap'` unchanged; it stays literally true.
- Nothing else. The margin flows through the code that follows without edits:
  - targets (:618, :733-736)
  - `c=(vector-target)/scale`, which becomes −m/scale at iteration 0 (:741, :752)
  - the projection upper bound `eps-c` = eps+m/scale (:727; `sdmpc_central.py:31-33`)
  - the dual update (:764-769; `sdmpc_central.py:27-28`)
  - the gates (:546-559, :806)
  - the final gate (:874 → `area_follower_objective.py:1461-1469`)
  - the anchor feasibility check (:605)
  - the zero-rollout reuse through the binding (:599)

**E4. `evaluation/controllers/sdmpc_tangent_surrogate.py`**
- `validate_prediction`, warm branch (:78-94):
  - Require the binding schema `sdmpc-pfo-budget-binding/v2` and the init schema `.../v2` (:82-83).
  - Both `init` margins must be of type `float`, finite and ≥0.
  - Recompute `a_np=fsum(owners net_inflow sorted)` and `a_nuf=fsum(predicted_ramp_merge rates)` (the same expressions as :90-91). Require `a_np==init['achieved_np_veh']` and `a_nuf==init['achieved_nuf_veh_h']`.
  - Set `expected.N_P_star,N_UF_star = a_np+np_m, a_nuf+nuf_m`. This is the same `a+m` float operation as E2; never use `fsum([...,m])`.
  - Keep `token(expected)==token(action)` and the equalities of the caps with `init['np_cap_veh']`/`init['nuf_cap_veh_h']`.
  - New error message: "...changed physical inputs, achieved quantities or margins".
  - This runs on every cache read (:147, :156, :222, :257).
  - The "margin == configured" check stays at bind time (:148-150) because `validate_prediction` has no policy.
- `bind_warm_budget`:
  - Binding schema v2 (:151).
  - Error text "achieved-plus-margin budgets" (:150).
  - Scope "Only constraint budgets (PFO-achieved + configured margin) change; physical trajectory unchanged" (:152).
  - Docstring :130-134.
  - The logic is unchanged.

**E5. `diagnostics/test_sdmpc_pfo_caps.py`**: see section 2.

**Optional, not needed for (a):**
- A check in `scripts/verify_parameters.py`. It audits only network/mpc/leader/runtime (`parameters.py:171-208`) and never the sdmpc_* sections.
- The docs note `docs/HANDOFF_20260922_PFO_CAP_SDMPC.md`.

## 2. TESTS
**Existing assertions whose expected values change: none.**
- Only the fixture must change. At `test_sdmpc_pfo_caps.py:24`, `n.sdmpc_options` has no `pfo_cap_options`, so the strict read in `initialize` raises KeyError. That breaks the tests at :47-56, :58-67 and :69-79.
- Fix: give `warm_fixture` a `margins=(0.,0.)` argument and add `pfo_cap_options=dict(max_iterations=2,nuf_tolerance_veh_h=1e-7,np_cap_margin_veh=margins[0],nuf_cap_margin_veh_h=margins[1])`.
- The `options` dicts at :51/:60-61/:72/:75/:77-79/:84 need no change, because the margin comes from the policy.
- The test at :81-84 still raises ValueError, since the witness check runs before the margin read.
- Unaffected: OwnPfoTests (:116; `sdmpc_pfo.py:25` reads only `max_iterations`), CapsTests, and the other test_sdmpc*/test_shared_joint* files. No assertion there encodes cap == achieved.

**New tests.** The prototype already has these (patch lines 164-293):
- `MarginTests`:
  - margin 0 is token-identical to the old rule and still uses 1 rollout;
  - (50,1000), (26,0) and (0,24) raise only the caps, keep the physical token unchanged, still use total_rollouts 1 and give an equal bound objective;
  - invalid policy margins are rejected (−1, −1e-9, NaN, inf, True, "50", and a missing key giving KeyError);
  - the stale target (policy 50/1000, anchor at margin 0) is rejected;
  - 8 forged-receipt cases are rejected (margin only, margin+cap, achieved, cap record only, negative margin, int margin, v1 init schema, v1 binding schema).
- `MarginPolicyTests`:
  - the defaults are explicit 0.0 floats;
  - missing, unknown or invalid keys fail `configure`;
  - `load_prices` accepts the same token and refuses a different margin.

**(R) Add to the prototype:**
- **Float-exactness case.** Replace the prototype's `residual == (-m_np, -m_nuf)` assertion (patch line 206) with `cap == achieved + margin` plus `residual <= 0`. Add margins (0.1, 0.3): −68+0.1 is not exact, and in random floats `a-(a+m) != -m` about 17% of the time. The binding must still pass.
- **Reverse-stale case.** Anchor built with (50, 1000) while the template policy is (0, 0) must be rejected at `bind_warm_budget`.

**Command** (PowerShell; mirrors `tools/run_tests.ps1:3-13`, which hard-codes `Set-Location D:\VISSIM-merge\sim3` at :7, so do not use it). Run it once on the unpatched worktree first to record pre-existing failures, then again after patching:
```
$dep='C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'; $env:PYTHONPATH="$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:PYTHONUTF8='1'; $env:RW_OFFSET_WRITER='experiment'
Set-Location D:\VISSIM-merge\sim3-capmargin
& 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe' -B -m unittest diagnostics.test_sdmpc_pfo_caps diagnostics.test_sdmpc_central diagnostics.test_sdmpc_tangent diagnostics.test_sdmpc_reverse diagnostics.test_sdmpc_sequence diagnostics.test_sdmpc_surrogate_reuse diagnostics.test_sdmpc_initial_shared diagnostics.test_sdmpc_hotpath diagnostics.test_shared_joint_price_quantity diagnostics.test_validated_decision_hold
```
Uncertain: the prototype's 19/19 result came from system Python without numba (2 AD test errors on both copies). It has not been run with `sdmpc-numba` on the path.

## 3. OFFLINE CHECK
**Harness:** `sim3\diagnostics\sdmpc_native_20260923\tools\replay_decision.ps1`, with `-Root D:\VISSIM-merge\sim3-capmargin` (:8) and the default tuning `config_candidate_obs1.json` (:10). It is the only tool that reproduced both native decisions. `measure_sdmpc_pfo_decision.py` covers 900 s only, from the nc2850 anchor (:29-30).

**Inputs, all in `$S`, never in `D:\VISSIM_runs`:**
- **Isolated frames `in_900` and `in_1050`.** Build them with a copy variant of `make_replay_state.py`. Its `os.link` (:34) cannot cross from D: to C:, and the observer writes its checkpoint into that folder. Size is about 0.54 GB for 900 s.
  - The existing `D:\VISSIM_runs\20260923_sdmpc\capmargin\in_900` could be reused only if the lead accepts checkpoint writes there.
- **`dec_900`.** A copy of the native `action_000750.json`. It has no `sdmpc_state`, so the run starts from zero prices (`sdmpc.py:453-455`). Copy the `state_000750.json` sibling too.
- **`dec_1050_<arm>`.** Needed because `load_prices` rejects the native 900 action's `policy_sha256` 05c590bc… under any patched policy (:464), even at margin 0.
  1. Copy `action_000900.csv` (28213 B) and the `state_000900.json`/`state_000750.json` siblings. The siblings are read by `_bp_previous_state_paths`. That reader is a no-op now because obs1 has no `phase_price.mode`, but copy them anyway.
  2. Copy `action_000900.json` byte-for-byte, replacing only the `metadata.sdmpc_state.policy_sha256` occurrence (byte offset ~58.50 MB; the file contains exactly 2 occurrences, the other being `price_state`). Replace it with the arm's token, taken from that arm's own 900 output `selection/price_state/policy_sha256`.
  3. Write `action_000900.json.applied` as UTF-16 with 3 lines: `900`, the absolute path of the copied CSV, and `28213` (checked at `sdmpc.py:459-464`).
  4. Record the original token as provenance.

**Margin-0 gate (the patch is accepted only if every item holds):**
- **900 s:** `-Dec $S\dec_900 -Sec 900 -PrevSec 750 -StateJson $S\in_900\state_000900.json -Out $S\m0_900`
  - `sdmpc_completed` objective == 393.91612458424544
  - `next_central_duals_scaled` == [2.3869628341616655, 0.1408151058737363]
  - `cmp` of the CSV against the native CSV passes
  - total_rollouts 9, `pfo_to_sdmpc_extra_rollouts` 0
  - `budget_initialization` is schema v2 with margins 0.0 and `np_cap_veh == achieved_np_veh`
- **1050 s:** `-Sec 1050 -PrevSec 900 -Dec $S\dec_1050_m0`
  - objective == 422.6749131864695
  - duals == [1.2288206364115695, 0.12234512221207197]
  - CSV `cmp` passes; total_rollouts 7
- **Compare values, not hashes.** `Query.context_token` (`sdmpc_tangent_surrogate.py:117`) hashes the follower's cfg, so `policy_sha256`, `frozen_context_token` and every response token change even at margin 0.
  - If `diff_decisions.py` is used, run a scratch copy. Filter 64-hex strings and add the new keys to `ADDED` (:21). Its difference limit of 200 (`walk(..., limit=200)`) could otherwise fill up with token differences and hide real ones.
- **Timing:** about 556 s (900) + 455 s (1050) per arm.

**Sweep** (native units: NP in veh, NUF in veh/h).
- Run arms one at a time in the one worktree, editing only parameters.json between runs. A mid-run edit fails that run loudly (source-change guard, `vissim_stackelberg_adapter.py:12619-12631`; parameters.json is fingerprinted at :1258).
- Grid:
  - (0,0): the gate above.
  - (25,25): the first default.
  - (50,50) and (100,100).
  - Attribution: (25,0) and (0,25).
  - Only if (100,100) ≥ (50,50) at 900: also (200,100). The iteration-1 NP request was about +217 veh.
  - Already measured: (0,1000) at 900 ≈ 394.3169, the third candidate in mlc3. It is expected to equal that arm, but that is not verified.
- Record per arm:
  - both objectives, paired against m0;
  - accepted steps per iteration and trial objectives;
  - final actual NP/NUF minus achieved (how much margin was used);
  - `iteration_dual_updates` and `next_central_duals_scaled` (the price leak);
  - extra rollouts == 0.
- Optional "dual-chain" 1050 variant: seed `next_prices_scaled` = `next_central_duals_scaled` = the arm's own 900 output. They must be equal and ≥0, per `sdmpc.py:504`.

**Why (25,25) as the first default.** Evidence from maps 3 and 1, with corrections:
- It matches the only binding request: at 900 s, iteration 0 asked for A·p = +26.0 veh / +24.0 veh/h (scaled raw residual [0.2599, 0.0240] with c=0).
- In both recorded cases only the half step executed (ratios 0.488 and 0.498). So iteration 0 would use about 13 of the margin, and the rest still restrains the large iteration-1 step.
- That restraint is what separated bound (393.916) from +1000 (394.317). The +1000 iteration-1 trial scored 395.410 and was rejected as `no_improving_step`.
- It has the smallest price leak. First-order, at 1050 the carried duals go from [1.229, 0.122] to about [0.73, 0.072] at 25, about [0.23, 0.022] at 50, and [0, 0] at 100.
- The worst case at 900 is the PFO anchor fallback, 395.535 (+1.62), not the iteration-0 value.
- All of this rests on one binding state. Offline differences are about 0.1-0.5 veh·h per decision, while the native seed σ is 50.7 veh·h, so only a same-seed paired native comparison can confirm it.

## 4. RISKS
**Ways the margin could silently not apply:**
1. **Wrong tree.** `replay_decision.ps1` defaults `-Root` to sim3 (:8). `run_tests.ps1:7`, `replay_900.ps1:27` and `run_decision.ps1:8` hard-code sim3. Any of these runs the unpatched code at margin 0 without error. Gate every arm on: schema v2, the recorded `np_cap_margin_veh`/`nuf_cap_margin_veh_h`, and `metadata.policy.pfo_cap_options`.
2. **Margin placed in the tuning JSON.** It is ignored (see E1). The strict key set only catches unknown keys inside parameters.json.
3. **np_values grid.** Not a risk at mlc=1: `sdmpc.py:618` overrides the grid targets. The grid still feeds the next decision's leader domain through the previous `N_P_star` (vendor `leader.py:427-428`, clipped, dead at mlc=1) and `search_limits` (only when mlc>1, `sdmpc.py:860-866`).
4. **Sequence copies.** `sdmpc_sequence.py:42-43` copies the block-0 caps into the future rows (identity only). Trials are decoded from a copy of the template, so they carry the margin caps.
5. **Binding fallback.** There is none: a failed proof raises (`sdmpc_tangent_surrogate.py:92-94`, :149-150). Do not add one. A skipped binding still applies the margin but costs one extra AD rollout (~135-160 s). Gate on `pfo_to_sdmpc_extra_rollouts == 0`.
6. **Float types.** A numpy margin would fail `_joint_number` (`area_leader_objective.py:186-189`) with a misleading "finite number" message. `configure` widens margins to float.

**Things that break price inheritance:**
7. **Any margin keys, even 0.0, change `token(policy)`.** A pre-patch state cannot be resumed (`sdmpc.py:461-465`), so a patched native run must start fresh. Changing the margin mid-run fails loudly.
8. **Do not add the keys to `sim3\evaluation\parameters.json` while the live run is going.** The live run's next decision would then raise at `load_prices`.
9. **Dual leak (behavioural, not a bug).** c0 = −m/scale feeds every dual update (`sdmpc_central.py:27-28`). Carried duals come only from accepted steps (`sdmpc.py:829-831`, :899).
   - Around 142 veh/h of NUF margin zeroes the 0.14 NUF price at 1050.
   - So (a) partly enacts price decay (b). Tell the user; "everything else unchanged" is not literally true.
10. **The offline 1050 arms are open-loop.** Their entering duals come from the margin-0 900 run, and the 1050 plant state came from the margin-0 900 action. Only a native run captures the closed loop.

**Operational:**
11. sim3-capmargin is a worktree of `sim3\.git`, so a commit writes objects into `D:\VISSIM-merge\sim3\.git`. Hold commits until the live run ends, or get an explicit OK.
12. The mutation check has not been re-run.
13. The dual-leak thresholds in item 9 and the "Why (25,25)" bullets are first-order estimates with the player requests held fixed.

Scratch helpers I wrote (read-only extraction): `$S\plan_trace_check.py`, `$S\plan_extract.py`, `$S\plan_token_ctx.py`.