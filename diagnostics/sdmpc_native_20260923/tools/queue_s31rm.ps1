# Concurrency ceiling is 4 (a 5th COM instance is refused). Wait for a free seat,
# then run s31_rm. Diagnose failures from run/stderr.txt, not from run.json's
# "Native identity was not established" which always fires under concurrency.
$ErrorActionPreference='Stop'
$root='D:\VISSIM_runs\20260922_seedvar'
$runner='D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
Write-Output "WAIT for a free VISSIM seat (ceiling 4) ..."
while (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count -ge 4) { Start-Sleep -Seconds 30 }
Write-Output ("SEAT FREE at {0}; launching s31_rm" -f (Get-Date -Format o))
& $runner -Prepared (Join-Path $root 's31_rm\prepared') -Output (Join-Path $root 's31_rm\run') `
          -Execute -MinimumFreeGiB 8 -AllowConcurrent *> (Join-Path $root 's31_rm\launch.log')
$rj = Join-Path $root 's31_rm\run\run.json'
if (Test-Path $rj) {
  $r = Get-Content $rj -Raw -Encoding UTF8 | ConvertFrom-Json
  Write-Output ("RESULT s31_rm completed={0} error={1}" -f $r.completed, $r.error)
  $se = Join-Path $root 's31_rm\run\stderr.txt'
  if (Test-Path $se -and (Get-Item $se).Length -gt 0) { Write-Output ("STDERR: " + (Get-Content $se -Raw)) }
}
Write-Output "S31RM_DONE"
