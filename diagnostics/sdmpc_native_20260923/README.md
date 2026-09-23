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
| e0164cc | `tools/` and `evidence/` below |
| c3799d3 | budget audit: the live budget is already an upper-bound inequality (`evidence/BUDGET_AUDIT_20260923.md`) |
| 20358cf | 215 tracked files kept byte-exact on checkout (a fresh worktree failed a sha256 pin) |
| 2bf00cf | 16 inputs the decision opens by hard-coded path, found by tracing file opens |
| 4b75fad | runner: lane frame built in linear time, state CSV reads the action JSON once (`evidence/STEP_COST_20260923.md`) |

## Running it

`tools/run_sdmpc_laneplant.ps1 -Name <run> -SimPeriod 9000 -Seed 13`. The lane plant is pinned by
sha256 to a 21-cell network, and the recording proof checks **absolute-path identity**, so the
network and proof come from the lane-plant worktree
(`...\.worktrees\sdmpc-lane-plant-20260921\diagnostics\lane_plant_20260921\native\`), not from a
copy. Env: clear every `RW_*`, then set only `RW_PYTHON` and `RW_OFFSET_WRITER=experiment`.
Gate map ver2 (not legs4b), mapping ver2n21, `-StallSec 2400`. The scripts carry this machine's
absolute paths (D:\VISSIM-merge\sim3, the .review-deps PYTHONPATH).

To check one decision without VISSIM, use `tools/replay_decision.ps1 -Dec <decisions dir> -Sec <t> -PrevSec <t-150>`.
It takes about 9 min, where a native run needs 15+ min to reach 900 s. It reads the run's saved
`state_<t>.json` and the previous action with its `.applied` marker, so it also exercises the
consecutive-decision price inheritance. Once a later decision has run in a folder, its
`lane_observations/observer_checkpoint.json` is ahead and an earlier replay is refused
("invalid/future cutoff"); `tools/make_replay_state.py` hard-links the frames into an isolated
folder and rewrites only the state's frame directory (pass it with `-StateJson`). Never replay in a
live run's folder: the replay writes that folder's checkpoint. `-Root <worktree>` replays another tree.

**Line endings.** Git on this machine checks out with `core.autocrlf=true`, which rewrote files
pinned by sha256. Every file whose bytes a checkout would change is `-text` in `.gitattributes`
(20358cf, 2bf00cf); a fresh worktree is byte-identical to the run tree for all 10,001 tracked files
and reproduces the 900 s objective exactly. `git add -u --renormalize` would restage ~427 files
committed with CRLF; add files by name.

## Status

- 900 s decision, native: completed. wall 508 s, obj 393.916, held 395.535. Meters all at ceiling,
  VSL all 120, so city signals only. Before congestion that is expected. `evidence/SQUEEZE_FINAL_20260923.md`.
- 1050 s decision (first consecutive one), native: died on the stock-debit tolerance, fixed in
  5a86363. The saved state now completes offline (obj 422.675 vs held 424.493). It inherits the
  900 s applied receipt (`committed: true`) and carries its prices forward.
  `evidence/FAIL_1050_20260923.md`.
- 9000 s run `sdmpc_lp_9000b` (13:32, 5a86363) passed 900 s and 1050 s with the offline
  objectives to the last digit (393.916, 422.675), then was stopped at ~1100 s for the runner fix:
  at 26 min per 150 sim-s it would have needed 23-45 h.
- 9000 s run `sdmpc_lp_9000c` launched 15:10 on 4b75fad. Its 0-900 s frames are checked against
  9000b's (deterministic warmup). Whether RM/VSL engage, and the TTT against no-control, come from
  its later decisions.

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
