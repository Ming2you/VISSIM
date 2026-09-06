<#
2026-09-04. 감사 후속 2팔 — ctlstart900 / meteroff.

## 팔 A: ctl_start900 — t=1 꼭짓점 락인 제거

감사 1번(오프라인)이 원인을 확정했다:

    t=1   GNE 산출        전 신호 34.000 / 34.667 (균등분할)
          정련 라운드      87회 (이후 중앙 35)
          현시가격         0.000 ~ 0.042 = 사실상 0
          이동량          SC1001/SC1004/SC105/SC5/SC6 각 72.3 s, SC109 87.0 s, 합 약 766 s
          이후 중앙 이동량  그 신호들 전부 0.000 -> 5,400 s 를 그 배분으로 산다

가격이 0인데 72초를 움직이는 이유: 국소비용이 평평하면 목적함수가 녹색에 대해 순수 선형이라
아무리 작은 가격이라도 꼭짓점으로 민다(메모리 vissim-flat-local-cost-vertex).
그 수정 local_cost_model:phased 는 **이미 켜져 있다**(local_cost_phased_signals=15/17).
그런데 phased 는 큐에 대한 2차항이고 t=1 은 빈 망(차량 8대, 전 현시 큐 0)이라 2차항이
사라져 다시 선형이 된다.

처방: 워밍업을 무제어로 돌리고 900 s 부터 제어를 넣는다. 큐가 실린 뒤 첫 결정을 내리면
phased 가 곡률을 갖는다. 러너에 이미 -ControlStartSec 이 있고 현재 런들은 기본 -1
(= 워밍업 없음, t=1 부터 제어)로 돌고 있었다.

  읽을 것  wu_phase_refine_rounds_used 첫값 87 -> 하락
           wu_phase_price_moved_sec_* 첫값 72.3 -> 이후 평균(약 205 s/전체) 수준으로
           corr(첫 결정 배분, 런평균 배분) 0.574 -> 하락
           corr(런평균 배분, 실측 큐) 0.171 -> 상승
           녹색/큐 Spearman 0.146, max-pressure 일치 25.8%(우연 27.5%) -> 상승
  판정선   TTT < 7,895.5 (= 7,946.2 - 1sigma) 면 추격. > 7,997 이면 되돌린다.
           주의: 900 s 무제어 워밍업 자체가 TTT 를 바꾸므로 무제어와의 짝비교가 흔들린다.
           그래서 nc 대비가 아니라 **ctl_canon(7946.2) 대비 짝비교**로 읽는다.

## 팔 B: meteroff_canon — 미터링 인과 귀속

감사가 두 차원에서 독립적으로 같은 결론에 왔다: 고속의 -499 는 미터링 성과가 아니다.
미터는 37결정 중 30에서 용량 개방이었고, 고속/도시 발산은 t=3000 에 완료되는데
첫 제한 명령은 t=4350 -- 1,350 s 뒤다. 이걸 2-arm 추론에서 직접 측정으로 바꾼다.

옛 arm_meteroff(2026-09-03)는 삭제 전 코드라 못 쓴다. 새 정본에서 다시 잰다.
램프만 물리적으로 못 조이게: leader.N_UF_star_range=[7200,7200] + min_green_sec=10.0.
도시 신호와 VSL 은 그대로.

  판정선   고속 성분이 ctl_canon 대비 얼마나 유지되나. 대부분 유지되면 미터링은
           이 망에서 포기하고 도시 녹색에 집중한다.

두 팔 모두 시드 13 · 망 x18_rampbn_qc · 5400 s · canon_default_20260904 기반.
#>

param([int]$Seed = 13)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_QUEUE_COUNTER = "1"
foreach ($v in @("RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG","RW_FORCE_STEPWISE",
                 "RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_MOVEMENT_PHASE_CORRECTION","RW_NARROW_AXIS_SG",
                 "RW_VALIDATION_FIXED_SIGNAL","RW_ARRIVAL_SEED","RW_QUEUE_CONTIGUOUS",
                 "RW_STORAGE_LANES_FZP","RW_RESTORE_RELEASE_BUFFERS","RW_WARMSTART_SEC",
                 "RW_QUEUE_BINS")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue }

$net = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx"
$vbs = "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$cal = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"
$map = "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json"
$adp = "evaluation/controllers/vissim_stackelberg_adapter.py"

function Wait-Vissim {
  for ($i=0; $i -lt 60; $i++) {
    $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
    if ($alive -eq 0) { return }
    Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
    Start-Sleep -Seconds 20
  }
}

Wait-Vissim
$name = "ctl_start900_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 워밍업 900s 무제어 후 제어" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter $adp -Tuning "evaluation/configs/canon_default_20260904.json" `
    -Network $net -VbsConfig $vbs -Calibration $cal -Mapping $map `
    -Controller "wu-link" -ControlStartSec 900 -WarmupController "no-control" `
    -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Wait-Vissim
$name = "meteroff_canon_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 램프 미터링 OFF, 도시신호/VSL 은 그대로" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter $adp -Tuning "evaluation/configs/arm_meteroff_canon_20260904.json" `
    -Network $net -VbsConfig $vbs -Calibration $cal -Mapping $map `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 `
    -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Output ("[{0}] 2팔 완료" -f (Get-Date -Format "HH:mm:ss"))
