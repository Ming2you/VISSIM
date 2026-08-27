<#
2026-08-27 주간 큐. **순차 실행** — 어젯밤 2개 동시로 fw12 두 개가 모두 EXIT_NO_DONE 했고
VISSIM200 프로세스 3개가 03:21 에 좀비로 남았다. 라이선스/COM 충돌로 보인다.

  1) nc_fw12_ramp1 · nc_fw12_ramp2   무제어 증량 기준선 (각 ~12분)
  2) bstoA_20260827                   (B) 회귀 원인 분리

분리 논리: tau(4d·저류X·수정X)=4688.4 · map4etau(4e·저류X·수정X)=4746.9 ·
plantfix(4f·저류O·수정O)=4848.0. bstoA(4f·저류O·수정X)를 채우면
경계저류 몫과 plant수정 몫이 갈린다. 어댑터는 plantfix 와 같은 qbind 를 써서 config 만 다르게 한다.
#>
$ErrorActionPreference = "Continue"
$repo = "C:/Users/TRLAB/Desktop/찐찐막/VISSIM"
$py = "C:/ProgramData/Anaconda3/python.exe"
$ncLaunch = Join-Path $repo "scripts/launch_nc_variant_20260827.ps1"
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"

function Kill-Vissim {
  Get-Process -Name 'vissim*','cscript','wscript' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 6
}

# ---- 1) fw12 무제어 2런 (순차) ----
$arms = @(
  @("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw12_ramp1.inpx","fw12_ramp1"),
  @("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw12_ramp2.inpx","fw12_ramp2")
)
foreach ($a in $arms) {
  Kill-Vissim
  $log = Join-Path $repo ("evaluation/runs/nc_" + $a[1] + "_seq.log")
  Write-Output ("[{0}] {1} 시작" -f (Get-Date -Format "HH:mm:ss"), $a[1])
  $p = Start-Process -FilePath "powershell.exe" -PassThru -WindowStyle Hidden -ArgumentList @(
    "-NoProfile","-ExecutionPolicy","Bypass","-File",$ncLaunch,"-Net",$a[0],"-Tag",$a[1]) `
    -RedirectStandardOutput $log -RedirectStandardError ($log + ".err")
  $p.WaitForExit()
  $n = (Get-ChildItem (Join-Path $repo ("evaluation/runs/nc_" + $a[1] + "_20260827/decisions_nc_" + $a[1] + "_20260827")) -Filter "state_*.json" -ErrorAction SilentlyContinue).Count
  Write-Output ("[{0}] {1} 종료 · state {2}개" -f (Get-Date -Format "HH:mm:ss"), $a[1], $n)
}

# ---- 2) bstoA 분리 팔 ----
Kill-Vissim
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}
$name = "bstoA_20260827"
Write-Output ("[{0}] {1} 시작 (4f 매핑 + 경계저류 · plant수정 없음)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo ("evaluation/runs/" + $name)) `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_bstoA_20260827.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed 13
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Write-Output "=========================================================="
& $py (Join-Path $repo 'scripts/compare_runs_ttt.py') `
    nocontrol_s13_20260824 tau_20260826 map4etau_20260826 bstoA_20260827 plantfix_20260827 `
    --base nocontrol_s13_20260824
