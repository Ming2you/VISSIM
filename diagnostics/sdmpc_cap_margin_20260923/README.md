# SDMPC budget caps: PFO-achieved + margin (2026-09-23)

Branch `claude/sdmpc-cap-margin-20260923`, on top of `claude/sdmpc-native-20260923` (673eece).

## What changed

Until now each control interval set the SDMPC budget caps to exactly what the PFO warm start
achieved (`N_P* = NP_PFO`, `N_UF* = NUF_PFO`). The caps were already one-sided (`NP <= cap`,
`NUF <= cap`, nonnegative prices; see `evidence/BUDGET_AUDIT_20260923.md` on the native
branch). But the start point sat exactly on both caps, and `max_leader_candidates=1` never moved
them, so the SDMPC could lower NP/NUF but never raise them.

Now `cap = PFO-achieved + margin`, with the margins in `evaluation/parameters.json`
(`sdmpc_pfo_cap.np_cap_margin_veh`, `nuf_cap_margin_veh_h`). **Default (100, 100)**, chosen
by the paired comparison below.

| file | change |
|---|---|
| `evaluation/parameters.json` | two margin keys (validated finite, >= 0, widened to float) |
| `evaluation/controllers/sdmpc.py` | `configure` requires exactly the four `sdmpc_pfo_cap` keys; margins enter the policy token, so prices carried from a run with a different margin are refused (`load_prices`) |
| `evaluation/controllers/sdmpc_budget.py` | caps = achieved + margin; receipt v2 records achieved, margin and cap separately |
| `evaluation/controllers/sdmpc_tangent_surrogate.py` | the PFO-to-SDMPC binding proof checks achieved == recomputed, and cap == achieved + margin (same float operation); schemas v2 |
| `diagnostics/test_sdmpc_pfo_caps.py` | 7 new tests: margin 0 token-identical to the old rule; positive and non-binary margins (0.1, 0.3) raise only the caps with zero extra rollouts; invalid margins rejected; stale / reverse-stale / 8 forged receipts rejected; prices refused across margins |

Tests: the SDMPC suite (10 modules) ran 111/111 OK before and 118/118 OK after.

A margin's key must go in `parameters.json`. The tuning JSON is not read for this section.

## Paired offline comparison

Replays of the native lane-plant run's saved 900 s and 1050 s states in this worktree
(`tools/cap_margin_sweep.py`, `tools/replay_decision.ps1 -Root <worktree> -StateJson ...`,
frames isolated by `tools/make_replay_state.py`). The 1050 s replays are open loop: the plant
state and the entering prices come from the native margin-0 900 s decision.

**Margin-0 gate passed:**
- objectives 393.91612458424544 and 422.6749131864695, to the last digit;
- carried and next prices identical;
- both action CSVs byte-identical to the native decisions;
- zero extra rollouts.

| margin (NP veh, NUF veh/h) | 900 s obj | Δ | 1050 s obj | Δ | 1050 next prices (scaled) |
|---|---|---|---|---|---|
| (0, 0) | 393.916 | 0 | 422.675 | 0 | [1.229, 0.122] |
| (25, 25) | 393.958 | +0.042 | 422.368 | −0.307 | [0.764, 0.072] |
| (50, 50) | 393.930 | +0.014 | 422.320 | −0.355 | [0.304, 0.023] |
| **(100, 100)** | **393.916** | **0.000** | **422.289** | **−0.386** | **[0, 0]** |

In every arm the final NP/NUF stayed below the caps, the budget binding needed 0 extra rollouts,
and no meter or VSL was restricted (both states are before congestion).

**How to read it:**
- The gains are ~0.1 % of one decision's predicted objective. They are open loop on the
  21-cell lane plant, before congestion. A same-seed paired native run is needed to confirm them.
- The trend had not saturated at 100.
- A margin also shrinks the carried dual prices, because the iteration-0 residual is now
  −margin/scale. At (100, 100) they reach zero. So (a) partly acts like a price reset (b); it is
  not "only the caps".

## Caveat on scope

These states come from the 21-cell lane plant scenario (100 % demand, seed 13, SimRes 1). They do
not come from the FW80/U90 scenario and the 31-cell METANET plant.
