# SDMPC-31 launch tools (copies)

Byte copies of the launch tools the SDMPC-31 runs use. The runs execute them from `D:\VISSIM-merge\tools\` on the lab PC.

- `run_sdmpc_n31.ps1`: the launcher. It takes `-Tuning` only, freezes a copy with `-Freeze`, and checks the seat rule (at most 4 VISSIM in total; a dev
  run may take the 4th seat). It always passes `-MaxAttempts 1 -NoGlobalKill` to the watchdog.
- `freeze_worktree.ps1`: copies the worktree, including untracked runtime files, to `D:\VISSIM-merge\frozen\sdmpc31_<sha>_<stamp>\`.
- `prepare_sdmpc31_network.py`: copies the `.inpx` and its 42 `.sig` files to `sdmpc31_<Name>.inpx`.

Launch long runs outside the Claude Code session, with WMI `Win32_Process.Create`. A session ending kills its background shells.
See `D:\VISSIM-merge\evidence\SDMPC31_INTEGRATION_20260924.md`.
