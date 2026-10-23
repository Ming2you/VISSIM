# Freeze an explicit runtime-input selection, sharing immutable file contents.
# Prepare the selection with tools/sdmpc31/runtime_package.py prepare first.
# Historical FREEZE.json verification remains supported without an input selection.
param(
  [string]$Source = 'D:\VISSIM-merge\sim3-n31',
  [string]$FrozenRoot = 'D:\VISSIM-merge\frozen',
  [string]$Verify = '',
  [string]$Python = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe',
  [string]$InputManifest = '',
  [string]$SharedStoreRoot = ''
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
$helperRel = 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py'
if ($Verify) {
  $frz = [IO.Path]::GetFullPath($Verify)
  & $Python -B (Join-Path $frz $helperRel) verify $frz
  exit $LASTEXITCODE
}
$src = [IO.Path]::GetFullPath($Source)
if (-not (Test-Path -LiteralPath (Join-Path $src $helperRel))) { throw "Not an SDMPC-31 source: $src" }
if (-not $InputManifest) {
  throw 'Whole-worktree copying is disabled. Prepare an explicit selection with tools/sdmpc31/runtime_package.py prepare --source <source> --config <relative-config> --out <inputs.json>, then pass -InputManifest.'
}
$inputs = [IO.Path]::GetFullPath($InputManifest)
if (-not (Test-Path -LiteralPath $inputs)) { throw "Input selection missing: $inputs" }
$head = @(& git -c "safe.directory=$src" -C $src rev-parse --verify 'HEAD^{commit}')
if ($LASTEXITCODE -ne 0 -or $head.Count -ne 1 -or $head[0] -notmatch '^[0-9a-f]{40}$') { throw "Cannot read git HEAD: $src" }
$frz = Join-Path ([IO.Path]::GetFullPath($FrozenRoot)) ('sdmpc31_{0}_{1}' -f $head[0].Substring(0,8),(Get-Date -Format 'yyyyMMddHHmmss'))
if (Test-Path -LiteralPath $frz) { throw "Frozen tree exists: $frz" }
if (-not $SharedStoreRoot) { $SharedStoreRoot = Join-Path ([IO.Path]::GetPathRoot($frz)) 'VISSIM_shared' }
$t0 = Get-Date
Write-Output "FREEZE_START source=$src target=$frz inputs=$inputs store=$SharedStoreRoot"
& $Python -B (Join-Path $src 'tools/sdmpc31/runtime_package.py') freeze --source $src --inputs $inputs --frozen $frz --store $SharedStoreRoot
if ($LASTEXITCODE -ne 0) { throw "Selected-input freeze failed; preserve diagnostics: $frz" }
& $Python -B (Join-Path $frz $helperRel) verify $frz
if ($LASTEXITCODE -ne 0) { throw "Canonical frozen manifest verification failed: $frz" }
Write-Output ('FREEZE_DONE wall_sec={0}' -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
Write-Output "FRZ=$frz"
