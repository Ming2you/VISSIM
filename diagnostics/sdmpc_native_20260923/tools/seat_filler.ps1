# Keep the 4 VISSIM seats full with the remaining variants.
# Seat ceiling is 4 (a 5th COM instance is refused). Each job is started detached so a
# free seat is filled immediately instead of waiting for the previous job to finish.
$ErrorActionPreference='Stop'
$root='D:\VISSIM_runs\20260922_seedvar'
$runner='D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
$queue=@('s41_rm','s31_rm')
$jobs=@()
foreach ($tag in $queue) {
  while (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count -ge 4) { Start-Sleep -Seconds 30 }
  Write-Output ("LAUNCH {0} {1}" -f $tag,(Get-Date -Format o))
  $jobs += Start-Job -Name $tag -ScriptBlock {
    param($runner,$prep,$out,$log)
    & $runner -Prepared $prep -Output $out -Execute -MinimumFreeGiB 8 -AllowConcurrent *> $log
  } -ArgumentList $runner,(Join-Path $root "$tag\prepared"),(Join-Path $root "$tag\run"),(Join-Path $root "$tag\launch.log")
  Start-Sleep -Seconds 45   # let VISSIM appear so the seat count is accurate
}
Write-Output ("WAITING on {0} jobs" -f $jobs.Count)
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
  $rj=Join-Path $root ("{0}\run\run.json" -f $j.Name)
  if (Test-Path $rj) {
    $r=Get-Content $rj -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Output ("RESULT {0} completed={1}" -f $j.Name,$r.completed)
    $se=Join-Path $root ("{0}\run\stderr.txt" -f $j.Name)
    if ((Test-Path $se) -and (Get-Item $se).Length -gt 0) { Write-Output ("STDERR: "+(Get-Content $se -Raw)) }
  }
}
Write-Output "SEAT_FILLER_DONE"
