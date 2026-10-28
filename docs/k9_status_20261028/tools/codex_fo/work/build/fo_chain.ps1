# FO build chain (2026-10-27 KST, user decision D-K9-113 = O2). Windows PowerShell 5.1, started detached by WMI at BELOW_NORMAL.
# Derived from work/b1/b1_chain.ps1 (B1). No VISSIM, no cscript, no kill. Runs under the shared heavy lock
# D:\VISSIM-merge\k8_gate_trees\heavy.lock (exclusive create, retry every 30 s, give up after 60 min, delete only our own).
# Stops at the first failed step (writes chain_fo.stop) and launches nothing.
#  0) lock; disk C/D >= 8 GB; fo root must not exist
#  1) fo/source = new git repo (no commit, no branch): fetch HEAD of b1/source (read-only), require a49981ff, detached checkout
#  2) robocopy b1/source -> fo/source (same /XD /XF as B1)
#  3) file table of fo/source == FRZ_B1 FREEZE.json table (0 changed/missing/extra); git-state recorded
#  4) fo_overlay.py: the 17 codex solo files + the FO config (one added adapter key)
#  5) table again: vs FRZ_B1 only the 13 allowed changed + 5 allowed extra files; git-state; unified diff of the 13 files
#  6) codex freeze_worktree.ps1 (bytes = FRZ_B1's) -Source fo/source -FrozenRoot fo/frozen -> FREEZE_OK, FRZ_FO
#  7) FRZ_FO FREEZE.json vs FRZ_B1 FREEZE.json: the same 13 + 5 only; 8) freeze verify FRZ_FO
#  9) runner -PreflightOnly s31, s41, s43 (FO config) and s31b (B config on FRZ_FO, gate control input only), one at a time
# 10) freeze verify FRZ_FO again; 11) fo_summary.py; 12) release the lock
$ErrorActionPreference = 'Stop'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\work\build'
$FOR = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo'
$B1SRC = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\source'
$FRZ1 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b1\frozen\sdmpc31_a49981ff_202610261410'
$SRC = Join-Path $FOR 'source'
$FROOT = Join-Path $FOR 'frozen'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$HEADSHA = 'a49981ffb258707c9a5e837d56f8cad829dab0ac'
$FMREL = 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py'
$CTRL = 'evaluation/controllers/'
$CH13 = @('area_follower_objective.py', 'joint_owner_neighbors.py', 'runtime_setup.py', 'sdmpc.py', 'sdmpc_budget.py', 'sdmpc_central.py',
  'sdmpc_pfo.py', 'sdmpc_sequence.py', 'sdmpc_tangent.py', 'sdmpc_tangent_constraints.py', 'sdmpc_tangent_surrogate.py',
  'sdmpc_tangent_worker.py', 'vissim_stackelberg_adapter.py')
$EX5 = @(($CTRL + 'sdmpc_actuator_scope.py'), ($CTRL + 'sdmpc_regional_context.py'), ($CTRL + 'sdmpc_regional_contracts.py'),
  ($CTRL + 'sdmpc_regional_prototype.py'), 'diagnostics/b0_v3c3/config_fo_v3c3.json')
$allowArgs = @()
foreach ($n in $CH13) { $allowArgs += @('--allow-changed', ($CTRL + $n)) }
foreach ($e in $EX5) { $allowArgs += @('--allow-extra', $e) }
$stateFile = Join-Path $W 'chain_fo.state.txt'
$TOKEN = 'fo_chain-' + $PID + '-' + [guid]::NewGuid().ToString('N')
$script:haveLock = $false
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function Release-Lock {
  if (-not $script:haveLock) { return }
  try {
    $t = [IO.File]::ReadAllText($LOCK)
    if ($t -like ('*' + $TOKEN + '*')) { Remove-Item -LiteralPath $LOCK -Force; Note 'lock released (own token)' } else { Note 'lock NOT released: token differs (not ours)' }
  } catch { Note ('lock release error: ' + [string]$_) }
  $script:haveLock = $false
}
function Stop-Chain([string]$why) { Note ('STOP: ' + $why); $why | Set-Content -Encoding UTF8 (Join-Path $W 'chain_fo.stop'); Release-Lock; exit 2 }
function Acquire-Lock {
  $t0 = Get-Date
  while ($true) {
    try {
      $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
      $body = '{"owner": "fo_declare", "pid": ' + $PID + ', "token": "' + $TOKEN + '", "started_kst": "' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST", "job": "FO chain: build+freeze FRZ_FO, runner preflights"}'
      $b = (New-Object System.Text.UTF8Encoding $false).GetBytes($body); $fs.Write($b, 0, $b.Length); $fs.Dispose()
      $script:haveLock = $true; Note ('lock acquired after ' + [int]((Get-Date) - $t0).TotalSeconds + ' s'); return $true
    } catch {
      if (((Get-Date) - $t0).TotalMinutes -gt 60) { return $false }
      $holder = ''; try { $holder = [IO.File]::ReadAllText($LOCK) } catch {}
      Note ('lock busy, retry in 30 s; holder=' + $holder)
      Start-Sleep -Seconds 30
    }
  }
}
# Native call with stdout+stderr to a UTF-8 file; never throws on stderr text (PS 5.1 NativeCommandError).
function Run-Native([string]$exe, [string[]]$argList, [string]$outFile) {
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { & $exe @argList 2>&1 | ForEach-Object { "$_" } | Set-Content -Encoding UTF8 -LiteralPath $outFile; $code = $LASTEXITCODE }
  finally { $ErrorActionPreference = $old }
  return $code
}
function OutText([string]$p) { return ((Get-Content -LiteralPath $p -Encoding UTF8) -join ' | ') }
function DiskOk {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  Note "disk C=$c D=$d GB"
  return ($c -ge 8 -and $d -ge 8)
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
try {
  Note ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' token=' + $TOKEN)
  Note ('VISSIM now (not ours, untouched): ' + ((@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' }) | ForEach-Object { $_.ProcessId }) -join ','))
  # 0
  if (Test-Path -LiteralPath $FOR) { Stop-Chain "fo root exists: $FOR" }
  if (-not (Acquire-Lock)) { Stop-Chain 'heavy lock not acquired within 60 min' }
  if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
  New-Item -ItemType Directory -Path $SRC | Out-Null
  # 1
  $c = Run-Native 'git' @('-C', $SRC, 'init', '-q') (Join-Path $FOR 'git_init.txt'); if ($c) { Stop-Chain "git init exit $c" }
  foreach ($kv in @(@('core.autocrlf', 'false'), @('core.longpaths', 'true'), @('core.safecrlf', 'false'))) {
    $c = Run-Native 'git' @('-C', $SRC, 'config', $kv[0], $kv[1]) (Join-Path $FOR 'git_config.txt'); if ($c) { Stop-Chain "git config $($kv[0]) exit $c" }
  }
  $c = Run-Native 'git' @('-C', $SRC, 'fetch', '-q', '--no-tags', $B1SRC, 'HEAD') (Join-Path $FOR 'git_fetch.txt'); if ($c) { Stop-Chain "git fetch exit $c" }
  $fh = (& git -C $SRC rev-parse FETCH_HEAD).Trim()
  Note "FETCH_HEAD=$fh (from $B1SRC HEAD)"
  if ($fh -ne $HEADSHA) { Stop-Chain "unexpected FETCH_HEAD $fh" }
  $c = Run-Native 'git' @('-C', $SRC, '-c', 'advice.detachedHead=false', 'checkout', '-q', '--detach', $fh) (Join-Path $FOR 'git_checkout.txt'); if ($c) { Stop-Chain "git checkout exit $c" }
  # 2 (the /UNILOG argument is built first: PS 5.1 splits an inline (Join-Path ...) into two arguments)
  $unilog = '/UNILOG:' + (Join-Path $FOR 'robocopy_b1source_to_fosource.log')
  & robocopy.exe $B1SRC $SRC /E /XD __pycache__ .pytest_cache .git __tangentcache__ /XF *.pyc /R:2 /W:2 /NFL /NDL /NP $unilog | Out-Null
  $rc = $LASTEXITCODE
  Note "robocopy b1/source -> fo/source exit=$rc"
  if ($rc -ge 8) { Stop-Chain "robocopy exit $rc" }
  # 3
  $c = Run-Native $PY @('-B', (Join-Path $W 'fo_tree_check.py'), 'table', $SRC, (Join-Path $W 'table_src_preoverlay.json')) (Join-Path $W 'table_src_preoverlay.out.txt')
  Note ('table pre-overlay exit=' + $c + ' :: ' + (OutText (Join-Path $W 'table_src_preoverlay.out.txt')))
  if ($c) { Stop-Chain 'table pre-overlay failed' }
  $c = Run-Native $PY @('-B', (Join-Path $W 'fo_tree_check.py'), 'diff', (Join-Path $FRZ1 'FREEZE.json'), (Join-Path $W 'table_src_preoverlay.json'), (Join-Path $W 'diff_src_preoverlay_vs_frzb1.json')) (Join-Path $W 'diff_src_preoverlay.out.txt')
  Note ('diff pre-overlay vs FRZ_B1 exit=' + $c + ' :: ' + (OutText (Join-Path $W 'diff_src_preoverlay.out.txt')))
  if ($c) { Stop-Chain 'fo/source (pre-overlay) differs from FRZ_B1' }
  $c = Run-Native $PY @('-B', (Join-Path $FRZ1 $FMREL), 'git-state', $SRC, (Join-Path $W 'gitstate_src_preoverlay.json')) (Join-Path $W 'gitstate_src_preoverlay.out.txt')
  Note ('git-state pre-overlay exit=' + $c)
  if ($c) { Stop-Chain 'git-state pre-overlay failed' }
  # 4
  $c = Run-Native $PY @('-B', (Join-Path $W 'fo_overlay.py'), $SRC, (Join-Path $W 'overlay_record.json')) (Join-Path $W 'overlay.out.txt')
  Note ('overlay exit=' + $c + ' :: ' + (OutText (Join-Path $W 'overlay.out.txt')))
  if ($c) { Stop-Chain 'overlay failed' }
  # 5
  $c = Run-Native $PY @('-B', (Join-Path $W 'fo_tree_check.py'), 'table', $SRC, (Join-Path $W 'table_src_postoverlay.json')) (Join-Path $W 'table_src_postoverlay.out.txt')
  Note ('table post-overlay exit=' + $c + ' :: ' + (OutText (Join-Path $W 'table_src_postoverlay.out.txt')))
  if ($c) { Stop-Chain 'table post-overlay failed' }
  $c = Run-Native $PY (@('-B', (Join-Path $W 'fo_tree_check.py'), 'diff', (Join-Path $FRZ1 'FREEZE.json'), (Join-Path $W 'table_src_postoverlay.json'), (Join-Path $W 'diff_src_postoverlay_vs_frzb1.json')) + $allowArgs) (Join-Path $W 'diff_src_postoverlay.out.txt')
  Note ('diff post-overlay vs FRZ_B1 exit=' + $c + ' :: ' + (OutText (Join-Path $W 'diff_src_postoverlay.out.txt')))
  if ($c) { Stop-Chain 'post-overlay difference is not exactly the declared 13 changed + 5 extra' }
  $dl = New-Object System.Collections.ArrayList
  foreach ($n in $CH13) {
    $rel = ($CTRL + $n).Replace('/', '\')
    $tmp = Join-Path $W ('diff_tmp_' + $PID + '.txt')
    $null = Run-Native 'git' @('diff', '--no-index', '--', (Join-Path $FRZ1 $rel), (Join-Path $SRC $rel)) $tmp
    [void]$dl.Add([IO.File]::ReadAllText($tmp))
    Remove-Item -LiteralPath $tmp -Force
  }
  [IO.File]::WriteAllText((Join-Path $W 'frzb1_to_fo_13files.diff'), ($dl -join "`n"), (New-Object System.Text.UTF8Encoding $false))
  $c = Run-Native $PY @('-B', (Join-Path $FRZ1 $FMREL), 'git-state', $SRC, (Join-Path $W 'gitstate_src_postoverlay.json')) (Join-Path $W 'gitstate_src_postoverlay.out.txt')
  Note ('git-state post-overlay exit=' + $c)
  if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
  # 6
  $fw = Join-Path $SRC 'tools\sdmpc31\freeze_worktree.ps1'
  $fwSha = (Get-FileHash -LiteralPath $fw -Algorithm SHA256).Hash; $fw1Sha = (Get-FileHash -LiteralPath (Join-Path $FRZ1 'tools\sdmpc31\freeze_worktree.ps1') -Algorithm SHA256).Hash
  Note "freeze tool sha fo/source=$fwSha FRZ_B1=$fw1Sha"
  if ($fwSha -ne $fw1Sha) { Stop-Chain 'freeze tool differs from FRZ_B1' }
  $c = Run-Native 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $fw, '-Source', $SRC, '-FrozenRoot', $FROOT) (Join-Path $FOR 'freeze.log')
  $flog = @(Get-Content -LiteralPath (Join-Path $FOR 'freeze.log') -Encoding UTF8)
  foreach ($l in $flog) { Note ('freeze: ' + $l) }
  Note "freeze exit=$c"
  $frzLine = @($flog | Where-Object { $_ -match '^FRZ=' }) | Select-Object -Last 1
  if ($c -or -not $frzLine -or -not (@($flog | Where-Object { $_ -match 'FREEZE_OK' }).Count)) { Stop-Chain 'freeze failed (no FREEZE_OK/FRZ line)' }
  $FRZFO = "$frzLine".Substring(4).Trim()
  if (-not (Test-Path -LiteralPath (Join-Path $FRZFO 'FREEZE.json'))) { Stop-Chain "no FREEZE.json in $FRZFO" }
  Note "FRZ_FO=$FRZFO"
  $FRZFO | Set-Content -Encoding UTF8 (Join-Path $W 'frz_fo_path.txt')
  # 7
  $c = Run-Native $PY (@('-B', (Join-Path $W 'fo_tree_check.py'), 'diff', (Join-Path $FRZ1 'FREEZE.json'), (Join-Path $FRZFO 'FREEZE.json'), (Join-Path $W 'diff_frzfo_vs_frzb1.json')) + $allowArgs) (Join-Path $W 'diff_frzfo.out.txt')
  Note ('diff FRZ_FO vs FRZ_B1 exit=' + $c + ' :: ' + (OutText (Join-Path $W 'diff_frzfo.out.txt')))
  if ($c) { Stop-Chain 'FRZ_FO differs from FRZ_B1 beyond the declared 13 + 5' }
  # 8
  $c = Run-Native $PY @('-B', (Join-Path $FRZFO $FMREL), 'verify', $FRZFO) (Join-Path $FOR 'freeze_verify_1.txt')
  Note ('freeze verify 1 exit=' + $c + ' :: ' + (OutText (Join-Path $FOR 'freeze_verify_1.txt')))
  if ($c) { Stop-Chain 'freeze verify 1 failed' }
  # 9
  $pf = @(@{ seed = 31; tag = ''; tun = 'diagnostics/b0_v3c3/config_fo_v3c3.json' }, @{ seed = 41; tag = ''; tun = 'diagnostics/b0_v3c3/config_fo_v3c3.json' },
          @{ seed = 43; tag = ''; tun = 'diagnostics/b0_v3c3/config_fo_v3c3.json' }, @{ seed = 31; tag = 'b'; tun = 'diagnostics/b0_v3c3/config_b0_v3c3.json' })
  foreach ($x in $pf) {
    if (-not (DiskOk)) { Stop-Chain 'disk < 8 GB' }
    $a = @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'fo_preflight_wrapper.ps1'), '-Seed', [string]$x.seed, '-Frz', $FRZFO, '-TuningRel', $x.tun)
    if ($x.tag -ne '') { $a += @('-Tag', $x.tag) }
    Note ("preflight s" + $x.seed + $x.tag + " start; VISSIM now: " + ((@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' }) | ForEach-Object { $_.ProcessId }) -join ','))
    $p = Start-Process -FilePath $PWSH -ArgumentList $a -WindowStyle Hidden -PassThru
    $null = $p.Handle
    $p.WaitForExit()
    Note ("preflight s" + $x.seed + $x.tag + " end exit=" + $p.ExitCode)
  }
  # 10
  $c = Run-Native $PY @('-B', (Join-Path $FRZFO $FMREL), 'verify', $FRZFO) (Join-Path $FOR 'freeze_verify_2.txt')
  Note ('freeze verify 2 exit=' + $c + ' :: ' + (OutText (Join-Path $FOR 'freeze_verify_2.txt')))
  # 11
  $c = Run-Native $PY @('-B', (Join-Path $W 'fo_summary.py'), $FRZFO, (Join-Path $W 'fo_summary.json')) (Join-Path $W 'fo_summary.out.txt')
  Note ('summary exit=' + $c)
  foreach ($l in @(Get-Content -LiteralPath (Join-Path $W 'fo_summary.out.txt') -Encoding UTF8)) { Note ('summary: ' + $l) }
  Release-Lock
  'done' | Set-Content -Encoding UTF8 (Join-Path $W 'chain_fo.done')
  Note 'done'
} catch {
  Stop-Chain ('exception: ' + [string]$_)
}
