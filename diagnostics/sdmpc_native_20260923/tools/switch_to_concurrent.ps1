# Wait for the in-flight sequential run to finish, stop the sequential driver, then launch
# the remaining variants concurrently. Concurrency is safe: a second VISSIM COM instance
# writes Simulation attributes while a run is in flight (verified 2026-09-22); the only
# real constraint is that the watchdog identifies its process by window title, so each
# variant now carries a distinct network filename.
$ErrorActionPreference='Stop'
$root='D:\VISSIM_runs\20260922_seedvar'
$runner='D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
$inflight=Join-Path $root 's31_none\run\run.json'

Write-Output "WAIT s31_none ..."
while ($true) {
  if (Test-Path $inflight) {
    try { $r=Get-Content $inflight -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $r=$null }
    if ($r -and $r.finished) { Write-Output ("s31_none finished completed={0}" -f $r.completed); break }
  }
  Start-Sleep -Seconds 20
}

# stop the sequential driver (not VISSIM)
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
  Where-Object { $_.CommandLine -like '*run_seed_sweep.ps1*' } |
  ForEach-Object { Write-Output ("STOP driver pid {0}" -f $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 5
Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue | ForEach-Object {
  Write-Output ("leftover VISSIM pid {0} - stopping" -f $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 5

$jobs=@()
foreach ($tag in 's31_rm','s37_none','s37_rm','s41_none','s41_rm') {
  $prep=Join-Path $root "$tag\prepared"
  $out =Join-Path $root "$tag\run"
  if (Test-Path $out) { Write-Output "SKIP $tag"; continue }
  $log =Join-Path $root "$tag\launch.log"
  Write-Output ("LAUNCH {0} {1}" -f $tag,(Get-Date -Format o))
  $jobs += Start-Job -Name $tag -ScriptBlock {
    param($runner,$prep,$out,$log)
    & $runner -Prepared $prep -Output $out -Execute -MinimumFreeGiB 8 -AllowConcurrent *> $log
    $LASTEXITCODE
  } -ArgumentList $runner,$prep,$out,$log
  Start-Sleep -Seconds 20   # stagger so each instance can be attributed by start time
}
Write-Output ("RUNNING {0} concurrent jobs" -f $jobs.Count)
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
  $rj=Join-Path $root ("{0}\run\run.json" -f $j.Name)
  $ok=$false; $err=$null
  if (Test-Path $rj) { $r=Get-Content $rj -Raw -Encoding UTF8 | ConvertFrom-Json; $ok=$r.completed; $err=$r.error }
  Write-Output ("RESULT {0} completed={1} error={2}" -f $j.Name,$ok,$err)
}
Write-Output "CONCURRENT_COMPLETE"
