# A1 detached launch via WMI (Win32_Process.Create) of a1_wrapper.ps1 under pwsh 7. Windows PowerShell 5.1 or pwsh.
# -Mode preflight : wrapper -PreflightOnly (no VISSIM).  -Mode run : the one declared A1 run (PRE_A1 r2), priority Normal.
# Refuses a run launch when any VISSIM process exists, when C:/D: < 8 GB, when a previous run launch receipt or
# a native runlog exists, or when STOP exists. Writes a receipt JSON (time, ReturnValue, ProcessId, command line).
param([Parameter(Mandatory = $true)][ValidateSet('preflight', 'run')][string]$Mode, [string]$Tag = '')
$ErrorActionPreference = 'Stop'
$LAUNCH = 'D:\VISSIM_runtime\20261025_codex_a1\launch'
$FRZ  = 'D:\VISSIM_runtime\20261025_codex_a1\frozen\sdmpc31_a49981ff_202610251820'
$RES  = 'D:\VISSIM_runs\20261025_codex_a1_s29'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$wrapper = Join-Path $LAUNCH 'a1_wrapper.ps1'
$rec = Join-Path $RES 'a1_launch'
New-Item -ItemType Directory -Force -Path $rec | Out-Null
$receipt = Join-Path $rec ("wmi_launch_" + $Mode + $Tag + ".json")
if (Test-Path -LiteralPath $receipt) { throw "launch receipt exists, no second launch: $receipt" }
if (Test-Path -LiteralPath (Join-Path $RES 'STOP')) { throw 'STOP exists' }
$c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
if ($c -lt 8 -or $d -lt 8) { throw "disk below 8 GB: C=$c D=$d" }
$vis = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' })
if ($Mode -eq 'run') {
  if ($vis.Count) { throw ('VISSIM running, no launch: ' + (($vis | ForEach-Object { $_.ProcessId }) -join ',')) }
  if (Test-Path -LiteralPath (Join-Path $RES 'sdmpc\runlog_sdmpc31_sdmpc8100_s29.txt')) { throw 'native runlog exists' }
  $pf = Join-Path $rec 'wrapper_preflight2_end.json'
  if (-not (Test-Path -LiteralPath $pf) -or (Get-Content -LiteralPath $pf -Raw | ConvertFrom-Json).runner_exit -ne 0) { throw 'preflight2 (corrected wrapper) not completed with exit 0' }
}
$cmd = '"' + $PWSH + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '"'
if ($Mode -eq 'preflight') { $cmd += ' -PreflightOnly' }
if ($Tag -ne '') { $cmd += (' -Tag ' + $Tag) }
$prio = [uint32]32   # NORMAL_PRIORITY_CLASS (PRE_A1 U5 (b))
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = $prio; ShowWindow = [uint16]0 }
$before = [DateTimeOffset]::Now.ToString('o')
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $FRZ; ProcessStartupInformation = $startup }
$o = [ordered]@{ mode = $Mode; tag = $Tag; time_before_create = $before; time_after_create = [DateTimeOffset]::Now.ToString('o');
  ReturnValue = [int]$r.ReturnValue; ProcessId = [int]$r.ProcessId; CommandLine = $cmd; CurrentDirectory = $FRZ;
  PriorityClass = $prio; launcher_pid = $PID; vissim_pids_at_launch = @($vis | ForEach-Object { [int]$_.ProcessId });
  disk_free_gb = [ordered]@{ C = $c; D = $d };
  wrapper_sha256 = (Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash.ToLowerInvariant();
  launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() }
($o | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $receipt
$o | ConvertTo-Json -Depth 5
