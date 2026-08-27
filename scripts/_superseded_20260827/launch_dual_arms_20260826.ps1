<#
2026-08-26. 듀얼 λ_P 실런. **리플레이로 거래가 확인된 조합만** 태운다.

  dualg0p02     gain 수정(cap 0.02 · gain=cap/400). 리플레이에서 커밋 레버 13/10개 변화.
  npbandg0p02   위 + 상태의존 리더 상자.
  dualg0p1      포화 문턱 바로 위(0.1). 곡선의 반대쪽 끝.

## 왜 이 축인가 — 실측으로 좁힌 사슬

    (1) 리더 목적함수가 N_P 에 평평(1위-2위/목적함수 2.7e-06)  -> 상자 어디든 바닥을 고른다  [미해결]
    (2) 바닥 < Σnin 이라 잔차가 크다                            -> npband 로 상자는 고쳤으나 무효
    (3) gain_pd = 0.01 x np_pd_gain_mult(25) = 0.25 가 잔차를 cap 으로 튀김  -> **gain 수정으로 해결**
    (4) cap 이 포화 구간이면 λ 값이 무의미                      -> 반응 구간 0.01~0.05 로 재조준

리플레이 실측(t=002250): λ<=0.05 -> Σnin 956.07 -> 975.80, 커밋 레버 **13개** 변화.
λ=0.10 은 base 와 동일. t=004800 은 λ 가 0 으로 떨어지며 **10개** 변화.
cap 0.5 와 10 은 둘 다 포화라 같은 답이었다 — 첫 시도에서 상단을 골라 헛돌았다.

전부 default_20260825 에서 독립 분기. 어댑터는 npband 사본 하나를 공유한다(스위치는 config).
기준선: 무제어 4808.1(시드 13, sigma 50.7) · default_20260825 4723.9(-84.2, 현 최선)
#>
param(
  [string[]]$Only = @(),
  [int]$Seed = 13
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"

$common = @{
  Network            = "network\real_world_gaepo_modi\modi_eval_userfix_20260814e.inpx"
  VbsConfig          = "evaluation\generated\real_world_modi_control_config_distributed_core17legs4b_mainline_20260825.vbs"
  Calibration        = "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json"
  Mapping            = "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json"
  Controller         = "wu-link"
  SimPeriod          = 5400
  ControlIntervalSec = 150
  StateLogIntervalSec= 30
  Seed               = $Seed
}

# 정보량 순. 도중에 시간이 모자라도 앞의 것이 먼저 확보된다.
# npbandg0p02 는 뺐다 — 리플레이에서 G_gain 과 커밋 레버·Σnin 이 **완전히 동일**했다
# (다른 건 n_p_star -250 대 853.27 뿐이고 잔차가 122.83 대 122.53 이라 λ 가 양쪽 다 cap).
# 상자는 gain 위에 아무것도 못 얹는다. VISSIM 한 시간을 여기 쓰지 않는다.
$arms = @("dualg0p02_20260826","dualg0p1_20260826")
if ($Only.Count -gt 0) { $arms = $arms | Where-Object { $Only -contains $_ } }

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

foreach ($name in $arms) {
  $tuning = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_$name.json"
  if (-not (Test-Path (Join-Path $repo $tuning))) {
    Write-Output "!! config 없음, 건너뜀: $tuning"; continue
  }
  $outDir = Join-Path $repo "evaluation\runs\$name"
  Write-Output "=========================================================="
  Write-Output ("[{0}] {1} 시작" -f (Get-Date -Format "HH:mm:ss"), $name)
  & $runner -Name $name -OutDir $outDir -Adapter $adapter -Tuning $tuning `
      -Network $common.Network -VbsConfig $common.VbsConfig `
      -Calibration $common.Calibration -Mapping $common.Mapping `
      -Controller $common.Controller -SimPeriod $common.SimPeriod `
      -ControlIntervalSec $common.ControlIntervalSec `
      -StateLogIntervalSec $common.StateLogIntervalSec -Seed $common.Seed
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
}

Write-Output "=========================================================="
Write-Output "듀얼 TTT:"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 tauoff_20260826 `
    dualg0p02_20260826 dualg0p1_20260826 `
    --base nocontrol_s13_20260824
