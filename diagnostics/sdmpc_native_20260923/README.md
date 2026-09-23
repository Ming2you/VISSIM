# SDMPC in the native VISSIM closed loop (2026-09-23)

Branch `claude/sdmpc-native-20260923`. It merges the plant (00abbab, `codex/control-full-review-20260909`)
with the SDMPC controller (5fdfabd, `codex/sdmpc-tangent-20260921`) and records what it took to
get SDMPC deciding inside a live VISSIM run for the first time. Until now SDMPC had only been
replayed offline (`lane_native_nc2850_s13_v3` is `controller = no-control`).

## Commits

| commit | contents |
|---|---|
| 884d1d1 | snapshot of the controller worktree (was uncommitted) |
| f1dad0e | merge of the plant branch |
| 14a0002 | runtime inputs: config-referenced / lane-plant-pinned files the snapshot missed, restored model inputs, `.gitattributes -text` for all of them |
| cd87e76 | three native-only defects: JSON writers, `next_budget` numpy scalars, 1 s head observation (`config_candidate_obs1.json`) |
| 3561a25 | decision time 600 s → 505 s, bit-identical (central Jacobian pruning, fused Dual operators, no deep copy, marshal cache) |
| a5c2d64 | plant diagnostics runnable from a checkout (`--geometry-vbs`, `-AllowConcurrent`, evaluate_response D3-D5) |
| 5a86363 | urban stock debit tolerance floor. The first 9000 s run died at 1050 s on it |
| (this) | `tools/` and `evidence/` below |

## Running it

`tools/run_sdmpc_laneplant.ps1 -Name <run> -SimPeriod 9000 -Seed 13`. The lane plant is pinned by
sha256 to a 21-cell network, and the recording proof checks **absolute-path identity**, so the
network and proof come from the lane-plant worktree
(`...\.worktrees\sdmpc-lane-plant-20260921\diagnostics\lane_plant_20260921\native\`), not from a
copy. Env: clear every `RW_*`, then set only `RW_PYTHON` and `RW_OFFSET_WRITER=experiment`.
Gate map ver2 (not legs4b), mapping ver2n21, `-StallSec 2400`. The scripts carry this machine's
absolute paths (D:\VISSIM-merge\sim3, the .review-deps PYTHONPATH).

To check one decision without VISSIM, use `tools/replay_decision.ps1 -Dec <decisions dir> -Sec <t> -PrevSec <t-150>`.
It takes about 8.5 min, where a native run needs 60+ min to reach 900 s. It reads the run's saved
`state_<t>.json` and the previous action with its `.applied` marker, so it also exercises the
consecutive-decision price inheritance.

**Line endings.** Git on this machine checks out with `core.autocrlf=true`. Every pinned input
added here is marked `-text` in `.gitattributes`, so its bytes survive a checkout.

## Status

- 900 s decision, native: completed. wall 508 s, obj 393.916, held 395.535. Meters all at ceiling,
  VSL all 120, so city signals only. Before congestion that is expected. `evidence/SQUEEZE_FINAL_20260923.md`.
- 1050 s decision (first consecutive one), native: died on the stock-debit tolerance, fixed in
  5a86363. The saved state now completes offline (obj 422.675 vs held 424.493). It inherits the
  900 s applied receipt (`committed: true`) and carries its prices forward.
  `evidence/FAIL_1050_20260923.md`.
- 9000 s run `sdmpc_lp_9000b` relaunched 13:32 on 5a86363. Whether RM/VSL engage, and the TTT
  against no-control, come from its later decisions.

## tools/ and evidence/

`tools/` is a copy of `D:\VISSIM-merge\tools` (launchers, replay, verifiers, meter/omega analysis).
The verifiers behind the "bit-identical" claims are `verify_central_prune.py`, `verify_fused.py`
and `diff_decisions.py`. `evidence/` holds the write-ups (*.md) and their JSON results. Run logs
and pre-squeeze `.bak` copies are left out.

## Not in the branch

- **33 files over 50 MB (7.1 GB):** captured prediction/state pickles under `diagnostics/sdmpc_*`
  and `tangent_900_*`. They are local artefacts that GitHub would reject.
- **Generated caches:** `__tangentcache__/` (now gitignored), numba, pycache.
- **1,154 older untracked diagnostics** from the controller worktree. They were copied in only
  so the merged tree was complete on disk. Nothing the verified decision reads is among them:
  everything the config references or the plant pins is in 14a0002.
- Run outputs under `D:\VISSIM_runs\20260923_sdmpc\` (fzp, decisions, ~58 MB per action JSON).
