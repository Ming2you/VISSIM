# B0 launch rehearsal without VISSIM: (1) source worktree W_b0 = fresh git repo, codex a49981ff detached (fetched from the
# read-only handoff copy; no commit, no branch), b0/code copied over it; (2) codex freeze_worktree.ps1 -> FRZ_B0 under
# b0/frozen; (3) the patched runner run_closedloop3000.ps1 -PreflightOnly from FRZ_B0 on v3c3 (freeze verify, network sha,
# watchdog -PreflightOnly).  Nothing is launched.  Log: b0/freeze_preflight.log
$ErrorActionPreference = 'Stop'
$B0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0'
$SRC = Join-Path $B0 'source'
$FROOT = Join-Path $B0 'frozen'
$LOG = Join-Path $B0 'freeze_preflight.log'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 $LOG }
try {
  Note ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass)
  if (Test-Path -LiteralPath $SRC) { throw "source exists: $SRC" }
  New-Item -ItemType Directory -Path $SRC | Out-Null
  & git -C $SRC init -q; if ($LASTEXITCODE) { throw 'git init' }
  & git -C $SRC config core.autocrlf false
  & git -C $SRC config core.longpaths true
  & git -C $SRC config core.safecrlf false
  & git -C $SRC fetch -q --no-tags 'D:/VISSIM_handoff/20261024/code' 'codex/handoff-rmtsc-20261024'; if ($LASTEXITCODE) { throw 'git fetch' }
  $fh = (& git -C $SRC rev-parse FETCH_HEAD).Trim()
  Note "FETCH_HEAD=$fh"
  if ($fh -ne 'a49981ffb258707c9a5e837d56f8cad829dab0ac') { throw "unexpected FETCH_HEAD $fh" }
  & git -C $SRC -c advice.detachedHead=false checkout -q --detach $fh; if ($LASTEXITCODE) { throw 'git checkout' }
  & robocopy.exe (Join-Path $B0 'code') $SRC /E /XD __pycache__ .pytest_cache .git __tangentcache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy $LASTEXITCODE" }
  $st = @(& git -C $SRC status --porcelain=v1 --untracked-files=all)
  $mod = @($st | Where-Object { $_ -notmatch '^\?\? ' })
  Note ("git status lines=" + $st.Count + " non-untracked=" + $mod.Count + ' :: ' + (($mod | Select-Object -First 12) -join ' | '))
  $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $SRC 'tools\sdmpc31\freeze_worktree.ps1') -Source $SRC -FrozenRoot $FROOT 2>&1
  $out | ForEach-Object { Note ('freeze: ' + $_) }
  $frzLine = @($out | Where-Object { "$_" -match '^FRZ=' }) | Select-Object -Last 1
  $frz = if ($frzLine) { "$frzLine".Substring(4) } else { (Get-ChildItem -LiteralPath $FROOT -Directory | Sort-Object Name | Select-Object -Last 1).FullName }
  if (-not (Test-Path -LiteralPath (Join-Path $frz 'FREEZE.json'))) { throw 'no FREEZE.json' }
  Note "FRZ=$frz"
  $res = Join-Path $B0 'runner_preflight\s31'
  $runner = Join-Path $frz 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1'
  $env:PYTHONHASHSEED = '0'; $env:OPENBLAS_CORETYPE = 'Haswell'; $env:NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; $env:NUMBA_CPU_NAME = 'haswell'
  $rout = & $PWSH -NoProfile -NonInteractive -File $runner -PreflightOnly -FrozenTree $frz -ResultsRoot $res -StatusPath (Join-Path $B0 'runner_preflight\status_s31.json') `
    -SimPeriod 9000 -Seed 31 -Arms sdmpc -TuningRelativePath 'diagnostics\b0_v3c3\config_b0_v3c3.json' `
    -NetworkRelativePath 'diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx' -NetworkSha256 '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e' `
    -PythonExe $PY -PowerShellExe $PWSH -DependenciesPath 'D:\VISSIM-window264-deps' 2>&1
  $code = $LASTEXITCODE
  $rout | ForEach-Object { Note ('runner: ' + $_) }
  Note "runner preflight exit=$code"
} catch {
  Note ('ERROR ' + $_)
}
Note 'end'
