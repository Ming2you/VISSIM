# [FO copy 2026-10-27 KST, PRE_FO s5: copy of codex_handoff/b/b_launcher_start.ps1 (sha256 9c818f1f4d5e6aadd338060e52e84b25f400e5741204cb41963cdf547b635c23) with names changed and the declared FO
# additions; full diff in codex_handoff/fo/work/run/launcher_b_to_fo.diff. The original header follows.]
# Start fo_launcher.ps1 -Mode run detached via WMI (Win32_Process.Create), Windows PowerShell 5.1, Normal priority (32), hidden.
# Refuses when a run-mode launcher process already exists (command line contains fo_launcher.ps1 and not dryrun) or when the
# launcher / wrapper sha differs from the value given. Writes fo/fo_launcher_start_receipts.log (one line per start). ASCII only.
param([Parameter(Mandatory = $true)][string]$LauncherSha, [Parameter(Mandatory = $true)][string]$WrapperSha,
      [Parameter(Mandatory = $true)][string]$PreSha, [Parameter(Mandatory = $true)][string]$RuleSha,
      [Parameter(Mandatory = $true)][string]$PinsSha, [Parameter(Mandatory = $true)][string]$GateSha)
$ErrorActionPreference = 'Stop'
$SPB = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo'
$L = Join-Path $SPB 'fo_launcher.ps1'
$h = (Get-FileHash -LiteralPath $L -Algorithm SHA256).Hash.ToLowerInvariant(); if ($h -ne $LauncherSha) { throw "launcher sha $h != $LauncherSha" }
$hw = (Get-FileHash -LiteralPath (Join-Path $SPB 'fo_wrapper.ps1') -Algorithm SHA256).Hash.ToLowerInvariant(); if ($hw -ne $WrapperSha) { throw "wrapper sha $hw != $WrapperSha" }
foreach ($q in @(@('PRE_FO.md', $PreSha), @('COMPARE_RULE_FO.md', $RuleSha), @('PINS_FO.sha256', $PinsSha), @('work\gate\fog_summary.json', $GateSha))) {
  $hq = (Get-FileHash -LiteralPath (Join-Path $SPB $q[0]) -Algorithm SHA256).Hash.ToLowerInvariant(); if ($hq -ne $q[1]) { throw ($q[0] + ' sha ' + $hq + ' != ' + $q[1]) }
}
$gate = Get-Content -LiteralPath (Join-Path $SPB 'work\gate\fog_summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($gate.pass -ne $true) { throw 'the T=900 gate summary does not say pass = true; no start (PRE_FO s4)' }
$running = @(Get-CimInstance Win32_Process | Where-Object { [string]$_.CommandLine -like '*fo_launcher.ps1*' -and [string]$_.CommandLine -notlike '*dryrun*' -and $_.ProcessId -ne $PID -and [string]$_.CommandLine -notlike '*fo_launcher_start.ps1*' })
if ($running.Count) { throw ('a launcher is already running: ' + (($running | ForEach-Object { $_.ProcessId }) -join ',')) }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $L + '" -Mode run -PreSha ' + $PreSha + ' -RuleSha ' + $RuleSha + ' -PinsSha ' + $PinsSha + ' -GateSha ' + $GateSha
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]32; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $SPB; ProcessStartupInformation = $startup }
$cr = ''; try { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$r.ProcessId); if ($p) { $cr = $p.CreationDate.ToString('o') } } catch {}
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' created=' + $cr + ' Priority=32 launcher_sha=' + $h + ' wrapper_sha=' + $hw + ' Command=' + $cmd
[IO.File]::AppendAllText((Join-Path $SPB 'fo_launcher_start_receipts.log'), $line + "`r`n", (New-Object System.Text.UTF8Encoding $false))
$line
