# Launch-stage preflight for one V-A seed (task step 1; J1_LAUNCH.md sec.3 / S31_RERUN_LAUNCH.md sec.2 form):
# run_sdmpc_n31.ps1 -PreflightOnly WITHOUT -Freeze, CurrentDirectory = FRZ_K92, WMI detached, BelowNormal,
# PYTHONHASHSEED=0.  -PreflightOnly starts no VISSIM and only creates RVA\_preflight\<Name>_<stamp> (the run name
# folder is not consumed).  Same line as the gate copy VA/gates/gh5_launch.ps1 (G-H5'), output here in VA/launch.
param([Parameter(Mandatory=$true)][ValidateSet(31, 41, 43)][int]$Seed)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$frz = 'D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833'
$rva = 'D:\VISSIM_runs\20261023_sdmpc31_k92'
$name = 'sdmpc31_v3c3_k92va_s{0}' -f $Seed
$out = Join-Path $here ('pre_k92va_s{0}.out' -f $Seed)
if (Test-Path -LiteralPath $out) { throw "output exists (never reused): $out" }
if (Test-Path -LiteralPath (Join-Path $rva $name)) { throw "run name folder already exists: STOP ($name)" }
$vissimNow = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like 'VISSIM*' }).Count
$cmd = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -SimPeriod 9000 -Seed {1} -Controller wu-link -RunsRoot {2} -Name {3} > "{0}" 2>&1' -f $out, $Seed, $rva, $name
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $frz; ProcessStartupInformation = $startup }
$line = '{0}  launch_preflight_s{6}  RV={1} PID={2} VISSIM_before={3} prio=BelowNormal cwd={4} | {5}' -f (Get-Date -Format o), $r.ReturnValue, $r.ProcessId, $vissimNow, $frz, $cmd, $Seed
Add-Content -LiteralPath (Join-Path $here 'wmi_preflight_lines.txt') -Value $line -Encoding UTF8
Write-Output $line
Write-Output ('PRE_LAUNCH seed={0} RV={1} PID={2} OUT={3}' -f $Seed, $r.ReturnValue, $r.ProcessId, $out)
