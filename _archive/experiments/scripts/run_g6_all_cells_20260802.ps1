# G6 순위 정합 측정용 VISSIM 전체 셀 배치 — 자유류 4셀 + 혼잡 2셀을 순차 실행한다.
#
# 왜 혼잡 셀이 필요한가.
#   자유류 t0(fw100/seed13, t=900)에서 14후보 H=3 목적함수를 미리 재 보니 램프 축이
#   c00 2462.460 / c10 2462.485 / c11 2462.522 / c12 2462.805 로 전체 폭 0.35(0.014%) 다.
#   모델이 램프 미터링에 사실상 무반응이라 그 축의 순위는 노이즈가 지배한다.
#   "병목 국소 용량 부재가 램프 액션 순위를 뒤집는가"는 혼잡 초기상태에서만 시험할 수 있다.
#
# 혼잡 셀 설계 — **수요 프로파일(-DemandProfile)을 쓰지 않는다.**
#   forced_response_grid_20260802.md §0.2 실측: 러너의 수요 경로는 `Volume(1)` 만 쓰고
#   이 네트워크의 VehicleInput 시간구간은 0/900/1800/2700/3600/4500 s 6개다.
#   즉 -DemandScale / -DemandProfile 은 **워밍업 0~900 s 만** 바꾼다.
#   그런데 어댑터가 보는 수요 예보(LoadInpxDemandSchedule, VBS:1500)는 배수를 **전 구간에**
#   곱한다. 혼잡 프로파일(본선 배수 1.90~2.65)을 쓰면 900 s 이후 모델 예보만 2배 넘게
#   부풀고 플랜트는 원본 수요로 돈다 — 모델·플랜트 수요 불일치가 순위 오차에 섞인다.
#
#   대신 파생망 fw125(`modi_eval_rw_fr_fw125_20260802.inpx`)를 쓴다. 이 망은 전 시간구간
#   volume 을 1.25 배 하고 900 s 이후를 peak 로 평탄화했으므로 **모델 예보와 플랜트가 일치**한다.
#   no-control 실측(forced_response_grid, seed13): t=3600 에 1534 veh / 65.8 kph
#   (rho 17.8 > rho_crit 16.354), t=4200 에 1746 veh / 58.4 kph (rho 20.3).
#   그래서 t0 를 3600 / 4200 으로 잡는다. 자유류 t0=900(565 veh / 104.5 kph)과 대조된다.

param(
  [switch]$SkipFreeflow,
  [switch]$SkipCongested
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$grid = Join-Path $repo "scripts\run_g6_branch_grid.ps1"
$profiles = Join-Path $repo "evaluation\configs\demand_profiles"
$baseNet = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_rw_control.inpx"

$t0all = Get-Date

if (-not $SkipFreeflow) {
  Write-Host "===== CELLSET=FREEFLOW t0=900 (fw100/fw125 x seed13/29) ====="
  & $grid -OutDir "evaluation\runs\g6_branch_grid_20260802" -WarmupSec 900 -HorizonSteps 5
}

if (-not $SkipCongested) {
  # t0 가 다르면 채점 시 --t0 도 달라야 하므로 런 디렉터리를 분리한다.
  # 더 혼잡한 t0=4200 을 먼저 돌린다(예산이 끊겨도 핵심 셀은 확보한다).
  Write-Host "===== CELLSET=CONGESTED fw125 t0=4200 (rho 20.3) ====="
  & $grid -OutDir "evaluation\runs\g6_cong4200_20260802" `
    -WarmupSec 4200 -HorizonSteps 5 -Seeds @(13) -Demands @("fw125")

  Write-Host "===== CELLSET=CONGESTED fw125 t0=3600 (rho 17.8) ====="
  & $grid -OutDir "evaluation\runs\g6_cong3600_20260802" `
    -WarmupSec 3600 -HorizonSteps 5 -Seeds @(13) -Demands @("fw125")
}

Write-Host "ALL_CELLS_DONE elapsed_sec=$([int]((Get-Date)-$t0all).TotalSeconds)"
