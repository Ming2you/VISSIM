<#
2026-08-01 스캔 최적화 A/B 검증용 런처.

run_real_world_stackelberg_controller.vbs (본 러너) 를 지정한 출력 디렉터리로 직접 띄운다.
watchdog 을 쓰지 않는다 - run_real_world_single_watchdog.ps1 의 Kill-Vissim 이
동시에 돌고 있는 FD 재추출 런까지 죽이기 때문이다.
-Runner 로 계측 사본 등 다른 러너를 지정할 수 있다.
#>
param(
  [string]$Name = "ab_before",
  [string]$OutDir = "evaluation\runs\perf_ab_20260801",
  [int]$SimPeriod = 300,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [string]$Controller = "pstack-flagship",
  [int]$StateLogIntervalSec = 5,
  [string]$Runner = "scripts\run_real_world_stackelberg_controller.vbs",
  [string]$Perf = ""
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
if (-not [System.IO.Path]::IsPathRooted($Runner)) { $Runner = Join-Path $repo $Runner }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

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

$argline = "//nologo " + (Q $Runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
  " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $calibration) + " " + (Q $tuning) + " " + (Q $mapping) +
  " " + (Q $Controller) + " -1 " + (Q "no-control") + " " + (Q $vbsConfig) +
  " $StateLogIntervalSec 1.0 " + (Q "") + " " + (Q $roles) + " 0 0 -1 -1 -1 " + (Q "")

if ($Perf -ne "") { [Environment]::SetEnvironmentVariable("RW_PERF", $Perf, "Process") }
else { [Environment]::SetEnvironmentVariable("RW_PERF", $null, "Process") }
[Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $null, "Process")
$cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
$t0 = Get-Date
Write-Host "AB_START $(Get-Date -Format 'HH:mm:ss') name=$Name runner=$Runner"
$proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
  -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden -Wait
$elapsed = [int]((Get-Date)-$t0).TotalSeconds
Write-Host "AB_DONE name=$Name elapsed_sec=$elapsed exit=$($proc.ExitCode)"
"$Name elapsed_sec=$elapsed exit=$($proc.ExitCode)" | Out-File -FilePath (Join-Path $OutDir "wallclock_$Name.txt") -Encoding utf8
Write-Host "LOG=$log"
