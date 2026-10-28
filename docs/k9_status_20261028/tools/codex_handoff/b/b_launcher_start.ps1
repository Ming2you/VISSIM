# Start b_launcher.ps1 -Mode run detached via WMI (Win32_Process.Create), Windows PowerShell 5.1, Normal priority (32), hidden.
# Refuses when a run-mode launcher process already exists (command line contains b_launcher.ps1 and not dryrun) or when the
# launcher / wrapper sha differs from the value given. Writes b/b_launcher_start_receipts.log (one line per start). ASCII only.
param([Parameter(Mandatory = $true)][string]$LauncherSha, [Parameter(Mandatory = $true)][string]$WrapperSha)
$ErrorActionPreference = 'Stop'
$SPB = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\b'
$L = Join-Path $SPB 'b_launcher.ps1'
$h = (Get-FileHash -LiteralPath $L -Algorithm SHA256).Hash.ToLowerInvariant(); if ($h -ne $LauncherSha) { throw "launcher sha $h != $LauncherSha" }
$hw = (Get-FileHash -LiteralPath (Join-Path $SPB 'b_wrapper_b1.ps1') -Algorithm SHA256).Hash.ToLowerInvariant(); if ($hw -ne $WrapperSha) { throw "wrapper sha $hw != $WrapperSha" }
$running = @(Get-CimInstance Win32_Process | Where-Object { [string]$_.CommandLine -like '*b_launcher.ps1*' -and [string]$_.CommandLine -notlike '*dryrun*' -and $_.ProcessId -ne $PID -and [string]$_.CommandLine -notlike '*b_launcher_start.ps1*' })
if ($running.Count) { throw ('a launcher is already running: ' + (($running | ForEach-Object { $_.ProcessId }) -join ',')) }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $L + '" -Mode run'
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]32; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $SPB; ProcessStartupInformation = $startup }
$cr = ''; try { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$r.ProcessId); if ($p) { $cr = $p.CreationDate.ToString('o') } } catch {}
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' created=' + $cr + ' Priority=32 launcher_sha=' + $h + ' wrapper_sha=' + $hw + ' Command=' + $cmd
[IO.File]::AppendAllText((Join-Path $SPB 'b_launcher_start_receipts.log'), $line + "`r`n", (New-Object System.Text.UTF8Encoding $false))
$line
