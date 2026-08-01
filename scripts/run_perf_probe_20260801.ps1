<#
2026-08-01 제어 인가 비용 분해용 계측 런처.

run_real_world_stackelberg_controller_perf.vbs (계측 사본) 를 RW_PERF=1 로 직접 띄운다.
watchdog 을 쓰지 않는다 - run_real_world_single_watchdog.ps1 의 Kill-Vissim 이
동시에 돌고 있는 FD 재추출 런까지 죽이기 때문이다.
#>
param(
  [string]$Name = "perf_pstack_300s_s13",
  [string]$OutDir = "evaluation\runs\perf_probe_20260801",
  [int]$SimPeriod = 300,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [string]$Controller = "pstack-flagship",
  [int]$StateLogIntervalSec = 5
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$runner      = Join-Path $repo "scripts\run_real_world_stackelberg_controller_perf.vbs"
$net         = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
$adapter     = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py"
$calibration = Join-Path $repo "evaluation\calibration\real_world_modi_control_v0_20260719.json"
$tuning      = Join-Path $repo "evaluation\configs\real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json"
$mapping     = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$vbsConfig   = Join-Path $repo "evaluation\generated\real_world_modi_control_config.vbs"
$roles       = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"

$stateCsv    = Join-Path $OutDir "state_$Name.csv"
$actionCsv   = Join-Path $OutDir "action_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log         = Join-Path $OutDir "runlog_$Name.txt"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null

function Q($s) { '"' + $s + '"' }

$argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
  " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $calibration) + " " + (Q $tuning) + " " + (Q $mapping) +
  " " + (Q $Controller) + " -1 " + (Q "no-control") + " " + (Q $vbsConfig) +
  " $StateLogIntervalSec 1.0 " + (Q "") + " " + (Q $roles) + " 0 0 -1 -1 -1 " + (Q "")

[Environment]::SetEnvironmentVariable("RW_PERF", "1", "Process")
[Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $null, "Process")
$cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
$t0 = Get-Date
Write-Host "PERF_PROBE_START $(Get-Date -Format 'HH:mm:ss') name=$Name"
$proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
  -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden -Wait
Write-Host "PERF_PROBE_DONE elapsed_sec=$([int]((Get-Date)-$t0).TotalSeconds) exit=$($proc.ExitCode)"
Write-Host "LOG=$log"
