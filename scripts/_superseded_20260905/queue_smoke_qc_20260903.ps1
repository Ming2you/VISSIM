<#
2026-09-03. 큐 카운터 스모크 — 값이 실제로 나오는지만 본다.

  망   ..._x18_rampbn_qc.inpx  (미터 커넥터 8개에 카운터 추가, 90 -> 98)
  env  RW_QUEUE_COUNTER=1
  길이 900초 (결정 6회) — 값 유무만 확인하는 용도

확인할 것
  state_*.json 의 local_observation.queue_counters 가 null 이 아니고 count=98
  램프 카운터 30001~30008 이 비영 값을 낸다
  QLen 이 -1 이 아니다 (-1 은 COM 읽기 실패)
  런로그에 QUEUE_COUNTER=1 ... counters=98
#>
param([int]$Seed = 13)
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_QUEUE_COUNTER = "1"
foreach ($v in @("RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG","RW_FORCE_STEPWISE")) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
for ($i=0; $i -lt 60; $i++) { if (@(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count -eq 0) { break }; Start-Sleep -Seconds 20 }
$name = "smoke_qc_20260903"
Write-Output ("[{0}] {1} 시작" -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_outflow_d00_x18_20260901.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 900 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 1
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
