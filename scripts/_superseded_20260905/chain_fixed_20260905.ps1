# 2026-09-05 미드블록 SG COM 적색 결함 수정 후 재발사 체인.
# RW_MAINLINE_SG_ONLY 는 러너가 config 로 세우지만, 여기서도 명시한다(옛 큐 스크립트와 같은 관례).
# 순서: base(uni1800+매핑v2) -> B(leg_split) -> cap -> lam0 -> lam0+cap -> ramplocal. 전부 시드 13.
[CmdletBinding(PositionalBinding=$false)]
param()
$env:RW_MAINLINE_SG_ONLY = "1"
$R = "C:\Users\TRLAB\Desktop\찐찐막\VISSIM"
$runner = "$R\scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$net = "$R\network\real_world_gaepo_modi\modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx"
$jobs = @(
  @("fx_uni1800_blindfix_x18_20260905",           "arm_satcap_uni1800_blindfix_20260905"),
  @("fx_uni1800_blindfix_legsplitB_x18_20260905", "arm_satcap_uni1800_blindfix_legsplitB_20260905"),
  @("fx_uni1800_blindfix_cap_x18_20260905",       "arm_satcap_uni1800_blindfix_cap_20260905"),
  @("fx_uni1800_blindfix_lam0_x18_20260905",      "arm_satcap_uni1800_blindfix_lam0_20260905"),
  @("fx_uni1800_blindfix_lam0_cap_x18_20260905",  "arm_satcap_uni1800_blindfix_lam0_cap_20260905"),
  @("fx_uni1800_blindfix_ramplocal_x18_20260905", "arm_satcap_uni1800_blindfix_ramplocal_20260905")
)
foreach ($j in $jobs) {
  $n = $j[0]; $cfg = $j[1]
  if (Test-Path "$R\evaluation\runs\$n") { Remove-Item -Recurse -Force "$R\evaluation\runs\$n" -ErrorAction SilentlyContinue }
  "=== START $n  $(Get-Date -Format 'HH:mm:ss')  RW_MAINLINE_SG_ONLY=$($env:RW_MAINLINE_SG_ONLY) ==="
  & $runner -Name $n -OutDir "$R\evaluation\runs\$n" -Network $net -Tuning "$R\evaluation\configs\$cfg.json" -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -Seed 13 -ControlStartSec 900 -WarmupController "no-control" -StateLogIntervalSec 30 -DemandScale 1.0
  "=== DONE $n exit=$LASTEXITCODE  $(Get-Date -Format 'HH:mm:ss') ==="
}
