# Dry runs of RVA\k92va_s43_watcher.ps1 before the first V-A launch (amendment 34 sec.6.2; J1_LAUNCH.md sec.5.2 T1-T8
# form, plus T9-T11).  No launch, no real lock, no record line, nothing written into RVA: every run gets -DryRun (except
# T7, which must be refused), -LogPath / -LockPath / -TargetsPath inside VA\launch\dryrun\, and the fake RunsRoot of
# T8-T11 is VA\launch\dryrun\fake_rva.  "Alive" test targets use THIS PowerShell process (PID + creation time).
$ErrorActionPreference = 'Stop'
$W = 'D:\VISSIM_runs\20261023_sdmpc31_k92\k92va_s43_watcher.ps1'
$D = Join-Path $PSScriptRoot 'dryrun'
New-Item -ItemType Directory -Force -Path $D | Out-Null
$me = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $PID)
$created = $me.CreationDate.ToString('yyyy-MM-ddTHH:mm:ss.ffffffzzz')
$deadPid = 4  # System process: wrong creation time -> never 'alive' for a target
function TJ([string]$path, [array]$items) {
  $o = @{ targets = @($items | ForEach-Object { [ordered]@{ key = $_[0]; name = $_[1]; cmdPid = $_[2]; created = $_[3] } }) }
  [IO.File]::WriteAllText($path, ($o | ConvertTo-Json -Depth 4))
}
$alive2 = Join-Path $D 'targets_alive2.json'
TJ $alive2 @(@('s31', 'sdmpc31_v3c3_k92va_s31', $PID, $created), @('s41', 'sdmpc31_v3c3_k92va_s41', $PID, $created))
$fake = Join-Path $D 'fake_rva'
New-Item -ItemType Directory -Force -Path (Join-Path $fake 'sdmpc31_v3c3_k92va_s41') | Out-Null
[IO.File]::WriteAllText((Join-Path $fake 'sdmpc31_v3c3_k92va_s41\launch_sdmpc31_v3c3_k92va_s41.log'), ("2026-10-23 12:00:00  EXIT sdmpc31_v3c3_k92va_s41 code=0`r`n"))
$deadT = Join-Path $D 'targets_dead_s31.json'
TJ $deadT @(@('s31', 'sdmpc31_v3c3_k92va_s31', $deadPid, $created), @('s41', 'sdmpc31_v3c3_k92va_s41', $PID, $created))
$lockDummy = Join-Path $D 'dummy_existing.lock'
[IO.File]::WriteAllText($lockDummy, 'dummy lock for T6')
$common = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $W, '-PollSec', '1', '-MaxPolls', '1', '-TargetsPath', $alive2)
$tests = @(
  @('T1', @('-DryRun', '-LogPath', (Join-Path $D 'T1.log'), '-LockPath', (Join-Path $D 'T1.lock'))),
  @('T2', @('-DryRun', '-TestFinished', 's31', '-TestSeat', '1,1', '-LogPath', (Join-Path $D 'T2.log'), '-LockPath', (Join-Path $D 'T2.lock'))),
  @('T3', @('-DryRun', '-TestFinished', 's31,s41', '-TestSeat', '0,0', '-LogPath', (Join-Path $D 'T3.log'), '-LockPath', (Join-Path $D 'T3.lock'))),
  @('T4', @('-DryRun', '-TestFinished', 's41', '-TestSeat', '3,1', '-LogPath', (Join-Path $D 'T4.log'), '-LockPath', (Join-Path $D 'T4.lock'))),
  @('T5', @('-DryRun', '-TestFinished', 's31,s41', '-TestSeat', '1,1', '-LogPath', (Join-Path $D 'T5.log'), '-LockPath', (Join-Path $D 'T5.lock'))),
  @('T6', @('-DryRun', '-LogPath', (Join-Path $D 'T6.log'), '-LockPath', $lockDummy)),
  @('T7', @('-TestSeat', '0,0', '-LogPath', (Join-Path $D 'T7.log'), '-LockPath', (Join-Path $D 'T7.lock'))),
  @('T8', @('-DryRun', '-RunsRoot', $fake, '-LogPath', (Join-Path $D 'T8.log'), '-LockPath', (Join-Path $D 'T8.lock'))),
  @('T9', @('-DryRun', '-RunsRoot', $fake, '-LogPath', (Join-Path $D 'T9.log'), '-LockPath', (Join-Path $D 'T9.lock'), '-STOPFILE')),
  @('T10', @('-DryRun', '-MaxHours', '0.0000001', '-LogPath', (Join-Path $D 'T10.log'), '-LockPath', (Join-Path $D 'T10.lock'))),
  @('T11', @('-DryRun', '-RunsRoot', $fake, '-TestSeat', '0,0', '-LogPath', (Join-Path $D 'T11.log'), '-LockPath', (Join-Path $D 'T11.lock'), '-DEADTARGETS'))
)
$sha0 = (Get-FileHash -Algorithm SHA256 -LiteralPath $W).Hash.ToLower()
$summary = @()
foreach ($t in $tests) {
  $name = $t[0]
  $extra = @($t[1] | Where-Object { $_ -ne '-STOPFILE' -and $_ -ne '-DEADTARGETS' })
  $args2 = @($common)
  if ($t[1] -contains '-DEADTARGETS') {
    # T11: s31 cmd dead without EXIT line (ABNORMAL), s41 alive with an EXIT line in the fake folder -> neither finished -> WAIT
    $args2[$args2.IndexOf('-TargetsPath') + 1] = $deadT
  }
  $stopFile = Join-Path $fake 'STOP_K92VA_S43'
  if ($t[1] -contains '-STOPFILE') { [IO.File]::WriteAllText($stopFile, 'dry run T9') }
  $out = & powershell @args2 @extra 2>&1 | ForEach-Object { "$_" }
  $code = $LASTEXITCODE
  if (Test-Path -LiteralPath $stopFile) { Remove-Item -LiteralPath $stopFile }
  $summary += ('{0} exit={1} | {2}' -f $name, $code, (($out | Where-Object { $_ -match 'POLL|RECHECK|WOULD_LAUNCH|REFUSED|STOP_FILE|GIVE_UP|EXIT|ABNORMAL' }) -join ' || '))
}
$sha1 = (Get-FileHash -Algorithm SHA256 -LiteralPath $W).Hash.ToLower()
$summary += ('WATCHER_SHA before={0} after={1} same={2}' -f $sha0, $sha1, ($sha0 -eq $sha1))
$summary += ('RVA_LISTING ' + ((Get-ChildItem -LiteralPath 'D:\VISSIM_runs\20261023_sdmpc31_k92' | ForEach-Object { $_.Name }) -join ','))
[IO.File]::WriteAllLines((Join-Path $D 'DRYRUN_SUMMARY.txt'), $summary)
$summary
