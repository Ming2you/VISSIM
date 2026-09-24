# Freeze the SDMPC-31 worktree into a launch tree FRZ (plan D5, NEW-14). Run from PowerShell.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\freeze_worktree.ps1
#       [-Source D:\VISSIM-merge\sim3-n31] [-FrozenRoot D:\VISSIM-merge\frozen]
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\freeze_worktree.ps1 -Verify <FRZ>
#
# A git worktree is not a launch tree: runtime files are untracked (e.g. lane_native_sgplan.vbs is '??')
# and the worktree keeps changing while runs re-read it. This copies W with robocopy (no .git link file,
# no __pycache__/.pytest_cache, no *.pyc) to <FrozenRoot>\sdmpc31_<head8>_<yyyyMMddHHmm>\ and writes
# FREEZE.json there: git HEAD, the sha of `git status --porcelain=v1 --untracked-files=all -z`, and the
# sha256 of every copied file. The copy is accepted only when FRZ and W hash identical after the copy and
# the git state did not move meanwhile. Launches run only from FRZ (run_sdmpc_n31.ps1 verifies FREEZE.json).
# Never renames or deletes an existing FRZ; the last line is FRZ=<path> for the caller.
param(
  [string]$Source = 'D:\VISSIM-merge\sim3-n31',
  [string]$FrozenRoot = 'D:\VISSIM-merge\frozen',
  [string]$Verify = '',
  [string]$Python = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
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
if (-not (Test-Path -LiteralPath (Join-Path $src $helperRel))) { throw "Not an SDMPC-31 worktree (no $helperRel): $src" }
$head = @(& git -C $src rev-parse --verify 'HEAD^{commit}')
if ($LASTEXITCODE -ne 0 -or $head.Count -ne 1 -or $head[0] -notmatch '^[0-9a-f]{40}$') { throw "Cannot read git HEAD of $src" }
$stamp = Get-Date -Format 'yyyyMMddHHmm'
$frz = Join-Path ([IO.Path]::GetFullPath($FrozenRoot)) ('sdmpc31_{0}_{1}' -f $head[0].Substring(0, 8), $stamp)
if (Test-Path -LiteralPath $frz) { throw "Frozen tree already exists: $frz" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $frz) | Out-Null
$stateFile = Join-Path (Split-Path -Parent $frz) ('.gitstate_{0}.json' -f (Split-Path -Leaf $frz))

$t0 = Get-Date
Write-Output ("FREEZE_START source={0} target={1} head={2}" -f $src, $frz, $head[0])
& $Python -B (Join-Path $src $helperRel) git-state $src $stateFile
if ($LASTEXITCODE -ne 0) { throw 'git state capture failed' }

$robolog = Join-Path (Split-Path -Parent $frz) ('robocopy_{0}.log' -f (Split-Path -Leaf $frz))
# /XF matches names case-insensitively at every depth: FREEZE.json must NOT be listed here, because
# nested boundary_fit\freeze.json files are runtime inputs. The root .git is the only file named .git.
& robocopy $src $frz /E /COPY:DAT /DCOPY:T /XD __pycache__ .pytest_cache .git /XF .git *.pyc /R:2 /W:2 /MT:8 /NP /NFL /NDL /UNILOG:$robolog | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) { throw "robocopy failed with exit code $rc (see $robolog)" }
Write-Output ("ROBOCOPY exit={0} log={1}" -f $rc, $robolog)

& $Python -B (Join-Path $frz $helperRel) build $src $frz $stateFile
if ($LASTEXITCODE -ne 0) { throw "FREEZE.json build failed; $frz is NOT a launch tree (left in place for inspection)" }
Remove-Item -LiteralPath $stateFile -Force
Write-Output ("FREEZE_DONE wall_sec={0}" -f [math]::Round(((Get-Date) - $t0).TotalSeconds, 1))
Write-Output ("FRZ={0}" -f $frz)
