# 1-second FZP archive to E — 2026-09-22

User requested moving existing 1-second FZP result files to E and removing their C copies. This supersedes deletion-only cleanup for these files. No native run, model, simulation resolution, recording configuration, or existing result is changed.

Archive root: `E:/VISSIM_archive/20260922_fzp_1s/control-full-review/`

Original root: `C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/control-full-review/`

Append the same relative path to the archive root to find a moved file. `plan.json` lists all 134 inventoried FZPs, original/archive paths, sizes, original modification times, and sampled timestamps at start/middle/end. Only 118 old recordings with a consistent sampled 1-second interval are selected. Eleven 5-second recordings and five tiny diagnostic samples/header-only files stay in C. No other worktree or D-drive run is in scope.

`status.json` reports progress and, after completion, verified counts and free space. `moved.jsonl` records both verification-before-deletion and successful removal of each C source. Each source is locked against writing while it is copied, the copy is flushed, and full source/destination SHA-256 plus size must match before removal. Sources changed since inventory are rejected. Processing is sequential with idle CPU priority. All paths are checked for containment and reparse points. Existing destination files are never overwritten.

Historical reports, plots, cached observations, network files, logs, and code remain where they were. Historical scripts that hard-code moved C paths need the corresponding E path or a restored copy before raw-FZP reanalysis; the archive preserves the original bytes. This is a path relocation, not a claim that cached summaries replace raw trajectories. Prior cleanup reconstruction manifests referencing these original paths can use the archived files instead.

Initial inventory attempt hit an Int32 offset limit on a >2 GB file. It made no plan, copy, or deletion; the offset is explicitly Int64 in the completed inventory.
