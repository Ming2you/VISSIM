# 2026-09-05. satcap 두 팔을 앞세우고 남은 시드 런을 뒤로 미룬다.
# 호출 전에 기존 체인(TaskStop)과 VISSIM/cscript 를 먼저 죽여야 한다.
[CmdletBinding(PositionalBinding=$false)]
param()
$R = "C:\Users\TRLAB\Desktop\찐찐막\VISSIM"
$runner = "$R\scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$net = "$R\network\real_world_gaepo_modi\modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx"
# (이름, config, seed, controller)
$jobs = @(
  @("arm_satcap_uni1800_x18_20260905", "arm_satcap_uni1800_20260905", 13, "wu-link"),
  @("arm_satcap_geo_x18_20260905",     "arm_satcap_geo_20260905",     13, "wu-link"),
  @("arm_satcap_uni900_x18_20260905",  "arm_satcap_uni900_20260905",  13, "wu-link"),
  @("arm_satcap_plant_x18_20260905",   "arm_satcap_plant_20260905",   13, "wu-link"),
  @("seed_base_s15_20260905",        "canon_default_20260904",    15, "wu-link"),
  @("seed_blind_s14_20260905",       "arm_blindfix_20260905",     14, "wu-link"),
  @("seed_blind_s15_20260905",       "arm_blindfix_20260905",     15, "wu-link"),
  @("seed_nc_s13_20260905",          "canon_default_20260904",    13, "no-control"),
  @("seed_nc_s14_20260905",          "canon_default_20260904",    14, "no-control"),
  @("seed_nc_s15_20260905",          "canon_default_20260904",    15, "no-control"),
  @("seed_base_s13_20260905",        "canon_default_20260904",    13, "wu-link"),
  @("seed_blind_s13_20260905",       "arm_blindfix_20260905",     13, "wu-link")
)
foreach ($j in $jobs) {
  $n = $j[0]; $cfg = $j[1]; $sd = [int]$j[2]; $ctl = $j[3]
  if (Test-Path "$R\evaluation\runs\$n") { Remove-Item -Recurse -Force "$R\evaluation\runs\$n" -ErrorAction SilentlyContinue }
  "=== START $n  $(Get-Date -Format 'HH:mm:ss') ==="
  if ($ctl -eq "no-control") {
    & $runner -Name $n -OutDir "$R\evaluation\runs\$n" -Network $net -Tuning "$R\evaluation\configs\$cfg.json" -Controller "no-control" -SimPeriod 5400 -ControlIntervalSec 150 -Seed $sd -StateLogIntervalSec 30 -DemandScale 1.0 -ForceStepwise:$true
  } else {
    & $runner -Name $n -OutDir "$R\evaluation\runs\$n" -Network $net -Tuning "$R\evaluation\configs\$cfg.json" -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -Seed $sd -ControlStartSec 900 -WarmupController "no-control" -StateLogIntervalSec 30 -DemandScale 1.0
  }
  "=== DONE $n exit=$LASTEXITCODE  $(Get-Date -Format 'HH:mm:ss') ==="
}
