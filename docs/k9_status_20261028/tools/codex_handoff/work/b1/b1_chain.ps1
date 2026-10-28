# B1 prep chain (2026-10-26, user decision D-K9-90). Windows PowerShell 5.1, started detached by WMI at BELOW_NORMAL.
# No VISSIM, no cscript, no kill. Stops at the first failed step (writes chain_b1.stop) and launches nothing.
#  0) disk C/D >= 8 GB; b1 root must not exist
#  1) b1/source = new git repo (no commit, no branch): fetch HEAD of FRZ_B0's source tree b0/source (read-only), require
#     a49981ff, detached checkout (core.autocrlf false, longpaths, safecrlf false as in B0)
#  2) robocopy b0/source -> b1/source (same /XD /XF as the B0 rehearsal: __pycache__ .pytest_cache .git __tangentcache__ *.pyc)
#  3) file table of b1/source == FRZ_B0 FREEZE.json table (0 changed/missing/extra); git-state of b1/source recorded
#  4) b1_edit_runner.py: the two D-K9-90 edits in run_closedloop3000.ps1 only
#  5) table again: only the runner differs from FRZ_B0; full diff of the runner; seat-logic test on the edited runner; git-state
#  6) codex freeze_worktree.ps1 (bytes = FRZ_B0's) -Source b1/source -FrozenRoot b1/frozen -> FREEZE_OK, FRZ_B1
#  7) FRZ_B1 FREEZE.json vs FRZ_B0 FREEZE.json: only the runner; 8) freeze verify FRZ_B1
#  9) runner -PreflightOnly s31, s41, s43 on FRZ_B1 (pwsh 7 wrapper b1_preflight_wrapper.ps1), one at a time
# 10) freeze verify FRZ_B1 again; 11) b1_summary.py
$ErrorActionPreference = 'Stop'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b1'
$B1 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1'
$B0SRC = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\source'
$FRZ0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\frozen\sdmpc31_a49981ff_202610260258'
$SRC = Join-Path $B1 'source'
$FROOT = Join-Path $B1 'frozen'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$HEADSHA = 'a49981ffb258707c9a5e837d56f8cad829dab0ac'
$RUNREL = 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1'
$RUNFWD = 'diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1'
$FMREL = 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py'
$stateFile = Join-Path $W 'chain_b1.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function Stop-Chain([string]$why) { Note ('STOP: ' + $why); $why | Set-Content -Encoding UTF8 (Join-Path $W 'chain_b1.stop'); exit 2 }
# Native call with stdout+stderr to a UTF-8 file; never throws on stderr text (PS 5.1 NativeCommandError).
function Run-Native([string]$exe, [string[]]$argList, [string]$outFile) {
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { & $exe @argList 2>&1 | ForEach-Object { "$_" } | Set-Content -Encoding UTF8 -LiteralPath $outFile; $code = $LASTEXITCODE }
  finally { $ErrorActionPreference = $old }
  return $code
}
function DiskOk {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  Note "disk C=$c D=$d GB"
  return ($c -ge 8 -and $d -ge 8)
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
try {
  Note ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass)
  Note ('VISSIM now (not ours, untouched): ' + ((@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' }) | ForEach-Object { $_.ProcessId }) -join ','))
  # 0
  if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
  if (Test-Path -LiteralPath $B1) { Stop-Chain "b1 root exists: $B1" }
  New-Item -ItemType Directory -Path $SRC | Out-Null
  # 1
  $c = Run-Native 'git' @('-C', $SRC, 'init', '-q') (Join-Path $B1 'git_init.txt'); if ($c) { Stop-Chain "git init exit $c" }
  foreach ($kv in @(@('core.autocrlf', 'false'), @('core.longpaths', 'true'), @('core.safecrlf', 'false'))) {
    $c = Run-Native 'git' @('-C', $SRC, 'config', $kv[0], $kv[1]) (Join-Path $B1 'git_config.txt'); if ($c) { Stop-Chain "git config $($kv[0]) exit $c" }
  }
  $c = Run-Native 'git' @('-C', $SRC, 'fetch', '-q', '--no-tags', $B0SRC, 'HEAD') (Join-Path $B1 'git_fetch.txt'); if ($c) { Stop-Chain "git fetch exit $c" }
  $fh = (& git -C $SRC rev-parse FETCH_HEAD).Trim()
  Note "FETCH_HEAD=$fh (from $B0SRC HEAD)"
  if ($fh -ne $HEADSHA) { Stop-Chain "unexpected FETCH_HEAD $fh" }
  $c = Run-Native 'git' @('-C', $SRC, '-c', 'advice.detachedHead=false', 'checkout', '-q', '--detach', $fh) (Join-Path $B1 'git_checkout.txt'); if ($c) { Stop-Chain "git checkout exit $c" }
  # 2
  # attempt 1 (14:07) passed '/UNILOG:(Join-Path ...)', which PS 5.1 splits into two arguments -> robocopy exit 16, nothing copied
  $unilog = '/UNILOG:' + (Join-Path $B1 'robocopy_b0source_to_b1source.log')
  & robocopy.exe $B0SRC $SRC /E /XD __pycache__ .pytest_cache .git __tangentcache__ /XF *.pyc /R:2 /W:2 /NFL /NDL /NP $unilog | Out-Null
  $rc = $LASTEXITCODE
  Note "robocopy b0/source -> b1/source exit=$rc"
  if ($rc -ge 8) { Stop-Chain "robocopy exit $rc" }
  # 3
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_tree_check.py'), 'table', $SRC, (Join-Path $W 'table_src_preedit.json')) (Join-Path $W 'table_src_preedit.out.txt')
  Note ('table pre-edit exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'table_src_preedit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'table pre-edit failed' }
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_tree_check.py'), 'diff', (Join-Path $FRZ0 'FREEZE.json'), (Join-Path $W 'table_src_preedit.json'), (Join-Path $W 'diff_src_preedit_vs_frzb0.json')) (Join-Path $W 'diff_src_preedit.out.txt')
  Note ('diff pre-edit vs FRZ_B0 exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'diff_src_preedit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'b1/source (pre-edit) differs from FRZ_B0' }
  $c = Run-Native $PY @('-B', (Join-Path $FRZ0 $FMREL), 'git-state', $SRC, (Join-Path $W 'gitstate_src_preedit.json')) (Join-Path $W 'gitstate_src_preedit.out.txt')
  Note ('git-state pre-edit exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'gitstate_src_preedit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'git-state pre-edit failed' }
  # 4
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_edit_runner.py'), (Join-Path $SRC $RUNREL), (Join-Path $W 'edit_record.json')) (Join-Path $W 'edit.out.txt')
  Note ('edit exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'edit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'runner edit failed' }
  # 5
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_tree_check.py'), 'table', $SRC, (Join-Path $W 'table_src_postedit.json')) (Join-Path $W 'table_src_postedit.out.txt')
  Note ('table post-edit exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'table_src_postedit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'table post-edit failed' }
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_tree_check.py'), 'diff', (Join-Path $FRZ0 'FREEZE.json'), (Join-Path $W 'table_src_postedit.json'), (Join-Path $W 'diff_src_postedit_vs_frzb0.json'), '--allow', $RUNFWD) (Join-Path $W 'diff_src_postedit.out.txt')
  Note ('diff post-edit vs FRZ_B0 exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'diff_src_postedit.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'post-edit difference is not exactly the runner' }
  $null = Run-Native 'git' @('diff', '--no-index', '--', (Join-Path $FRZ0 $RUNREL), (Join-Path $SRC $RUNREL)) (Join-Path $W 'runner_b0_to_b1.diff')
  $c = Run-Native 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'b1_seat_logic_test.ps1'), '-Runner', (Join-Path $SRC $RUNREL), '-Out', (Join-Path $W 'seat_test_b1.json')) (Join-Path $W 'seat_test_b1.out.txt')
  Note ('seat logic test exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'seat_test_b1.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'seat logic test failed to run' }
  $c = Run-Native $PY @('-B', (Join-Path $FRZ0 $FMREL), 'git-state', $SRC, (Join-Path $W 'gitstate_src_postedit.json')) (Join-Path $W 'gitstate_src_postedit.out.txt')
  Note ('git-state post-edit exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'gitstate_src_postedit.out.txt') -Encoding UTF8) -join ' | '))
  if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
  # 6
  $fw = Join-Path $SRC 'tools\sdmpc31\freeze_worktree.ps1'
  $fwSha = (Get-FileHash -LiteralPath $fw -Algorithm SHA256).Hash; $fw0Sha = (Get-FileHash -LiteralPath (Join-Path $FRZ0 'tools\sdmpc31\freeze_worktree.ps1') -Algorithm SHA256).Hash
  Note "freeze tool sha b1/source=$fwSha FRZ_B0=$fw0Sha"
  if ($fwSha -ne $fw0Sha) { Stop-Chain 'freeze tool differs from FRZ_B0' }
  $c = Run-Native 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $fw, '-Source', $SRC, '-FrozenRoot', $FROOT) (Join-Path $B1 'freeze.log')
  $flog = @(Get-Content -LiteralPath (Join-Path $B1 'freeze.log') -Encoding UTF8)
  foreach ($l in $flog) { Note ('freeze: ' + $l) }
  Note "freeze exit=$c"
  $frzLine = @($flog | Where-Object { $_ -match '^FRZ=' }) | Select-Object -Last 1
  if ($c -or -not $frzLine -or -not (@($flog | Where-Object { $_ -match 'FREEZE_OK' }).Count)) { Stop-Chain 'freeze failed (no FREEZE_OK/FRZ line)' }
  $FRZ1 = "$frzLine".Substring(4).Trim()
  if (-not (Test-Path -LiteralPath (Join-Path $FRZ1 'FREEZE.json'))) { Stop-Chain "no FREEZE.json in $FRZ1" }
  Note "FRZ_B1=$FRZ1"
  $FRZ1 | Set-Content -Encoding UTF8 (Join-Path $W 'frz_b1_path.txt')
  # 7
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_tree_check.py'), 'diff', (Join-Path $FRZ0 'FREEZE.json'), (Join-Path $FRZ1 'FREEZE.json'), (Join-Path $W 'diff_frzb1_vs_frzb0.json'), '--allow', $RUNFWD) (Join-Path $W 'diff_frzb1.out.txt')
  Note ('diff FRZ_B1 vs FRZ_B0 exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $W 'diff_frzb1.out.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'FRZ_B1 differs from FRZ_B0 beyond the runner' }
  # 8
  $c = Run-Native $PY @('-B', (Join-Path $FRZ1 $FMREL), 'verify', $FRZ1) (Join-Path $B1 'freeze_verify_1.txt')
  Note ('freeze verify 1 exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $B1 'freeze_verify_1.txt') -Encoding UTF8) -join ' | '))
  if ($c) { Stop-Chain 'freeze verify 1 failed' }
  # 9
  foreach ($s in 31, 41, 43) {
    if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
    $a = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'b1_preflight_wrapper.ps1'), '-Seed', [string]$s, '-Frz', $FRZ1)
    Note ("preflight s$s start; VISSIM now: " + ((@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' }) | ForEach-Object { $_.ProcessId }) -join ','))
    $p = Start-Process -FilePath $PWSH -ArgumentList $a -WindowStyle Hidden -PassThru
    $null = $p.Handle
    $p.WaitForExit()
    Note ("preflight s$s end exit=" + $p.ExitCode)
  }
  # 10
  $c = Run-Native $PY @('-B', (Join-Path $FRZ1 $FMREL), 'verify', $FRZ1) (Join-Path $B1 'freeze_verify_2.txt')
  Note ('freeze verify 2 exit=' + $c + ' :: ' + ((Get-Content -LiteralPath (Join-Path $B1 'freeze_verify_2.txt') -Encoding UTF8) -join ' | '))
  # 11
  $c = Run-Native $PY @('-B', (Join-Path $W 'b1_summary.py'), $FRZ1, (Join-Path $W 'b1_summary.json')) (Join-Path $W 'b1_summary.out.txt')
  Note ('summary exit=' + $c)
  foreach ($l in @(Get-Content -LiteralPath (Join-Path $W 'b1_summary.out.txt') -Encoding UTF8)) { Note ('summary: ' + $l) }
  'done' | Set-Content -Encoding UTF8 (Join-Path $W 'chain_b1.done')
  Note 'done'
} catch {
  Stop-Chain ('exception: ' + [string]$_)
}
