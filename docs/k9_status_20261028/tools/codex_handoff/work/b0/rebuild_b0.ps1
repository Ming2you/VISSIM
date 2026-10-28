# B0 rebuild chain (no VISSIM): config generator -> code patches -> watchdog -PreflightOnly (new label, detached via WMI,
# BELOW_NORMAL) -> replay inputs with the provenance synthesized from that preflight.  usage: rebuild_b0.ps1 -Wd wd02 -Ts 3450,1800
param([Parameter(Mandatory=$true)][string]$Wd, [string]$Ts = '3450', [string]$Src = 'va_s31',
      [string]$TuningRel = 'diagnostics\b0_v3c3\config_b0_v3c3.json')
$ErrorActionPreference = 'Stop'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b0'
$B0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location (Join-Path $B0 'code')
& $PY -B (Join-Path $W 'b0_make_v3c3.py') | Select-String '^files'
if ($LASTEXITCODE -ne 0) { throw 'generator failed' }
Pop-Location
& $PY -B (Join-Path $W 'b0_code_patches.py')
if ($LASTEXITCODE -ne 0) { throw 'patches failed' }
& (Join-Path $W 'launch_wmi_b0.ps1') -Script (Join-Path $W 'wd_preflight_b0.ps1') -ArgString ('-Label ' + $Wd + ' -TuningRel "' + $TuningRel + '"') | Out-Null
$R = Join-Path $B0 ('preflight\' + $Wd)
$t0 = Get-Date; $j = $null
while (((Get-Date) - $t0).TotalSeconds -lt 600) { Start-Sleep 5; if (Test-Path (Join-Path $R 'wd_preflight.json')) { $j = Get-Content (Join-Path $R 'wd_preflight.json') -Raw | ConvertFrom-Json; if ($null -ne $j.exit) { break } } }
'preflight ' + $Wd + ' exit=' + $j.exit
Get-Content (Join-Path $R 'sdmpc\preflight_launch.log') -Tail 3
if ($j.exit -ne 0) { throw 'preflight failed' }
$prov = Join-Path $R ('sdmpc\preflight\run_provenance_sdmpc31_sdmpc9000_s31.json')
& $PY -B (Join-Path $W 'b0_build_inputs.py') ('--preflight=' + $prov.Replace('\', '/')) $Src @($Ts.Split(',')) | ForEach-Object { $_.Substring(0, [math]::Min(110, $_.Length)) }
