# vsl_launcher_start.ps1 - start vsl_launcher.ps1 (-Mode run) detached via WMI Win32_Process.Create (PRE_VSL.md section 5).
# Windows PowerShell 5.1, ASCII only. Refuses when: the launcher sha differs from the pin, a launcher instance already
# runs, C: or D: has < 8 GB free. Writes one receipt line to <Root>\vsl_launcher_start_receipts.log. NOT run at declaration.
param([string]$ExpectSha = 'cbc37aff191ef1cf53c247a8b2c29f4b1686e10bd4aadeef6bf34fb8bdebff4e')
$ErrorActionPreference = 'Stop'
$VS = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3'
$Root = 'D:\VISSIM_runs\20261027_vsl_v3c3'
$L = Join-Path $VS 'tools\vsl_launcher.ps1'
$h = (Get-FileHash -LiteralPath $L -Algorithm SHA256).Hash.ToLowerInvariant()
if ($h -ne $ExpectSha) { throw ('launcher sha differs: ' + $h) }
$running = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -like '*vsl_launcher.ps1*-Mode run*' })
if ($running.Count) { throw ('launcher already running: ' + (($running | ForEach-Object { $_.ProcessId }) -join ',')) }
$c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
if ($c -lt 8 -or $d -lt 8) { throw ('disk below 8 GB: C=' + $c + ' D=' + $d) }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $L + '" -Mode run'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]32 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $Root; ProcessStartupInformation = $si }
$vis = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^VISSIM' }).Count
$line = (Get-Date).ToString('o') + '  vsl_launcher  RV=' + $r.ReturnValue + ' PID=' + $r.ProcessId + ' sha256=' + $h + ' VISSIM_now=' + $vis + ' freeC_GB=' + $c + ' freeD_GB=' + $d + ' | ' + $cmd
Add-Content -LiteralPath (Join-Path $Root 'vsl_launcher_start_receipts.log') -Value $line -Encoding UTF8
$line
