# Relaunch the two rm arms that died at ControlStartSec because prepared/rule_runtime.txt
# still carried the other workstation's python/helper paths. Paths are now repointed.
# Seat ceiling is 4; wait for a free seat before each launch.
$ErrorActionPreference='Stop'
$root='D:\VISSIM_runs\20260922_seedvar'
$runner='D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
foreach ($tag in 's37_rm','s41_rm') {
  Write-Output ("WAIT seat for {0} ..." -f $tag)
  while (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count -ge 4) { Start-Sleep -Seconds 30 }
  Write-Output ("LAUNCH {0} {1}" -f $tag,(Get-Date -Format o))
  & $runner -Prepared (Join-Path $root "$tag\prepared") -Output (Join-Path $root "$tag\run") `
            -Execute -MinimumFreeGiB 8 -AllowConcurrent *> (Join-Path $root "$tag\launch.log")
  $rj=Join-Path $root "$tag\run\run.json"
  if (Test-Path $rj) {
    $r=Get-Content $rj -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Output ("RESULT {0} completed={1}" -f $tag,$r.completed)
    $se=Join-Path $root "$tag\run\stderr.txt"
    if ((Test-Path $se) -and (Get-Item $se).Length -gt 0) { Write-Output ("STDERR: "+(Get-Content $se -Raw)) }
  }
}
Write-Output "RM_RETRY_DONE"
