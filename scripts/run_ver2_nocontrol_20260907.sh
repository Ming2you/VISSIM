#!/usr/bin/env bash
# Ver2 망 무제어 기준선 (b4 와 동시 실행:). 러너는 PowerShell 로만.
cd "C:/Users/TRLAB/Desktop/찐찐막/VISSIM" || exit 1
NAME="v0_nocontrol_ver2_x18_20260907"; OUT="evaluation/runs/$NAME"; D="evaluation/real_world_modi_control_ver2_20260907"
echo "$(date '+%m-%d %H:%M:%S')  START $NAME  (Ver2 망, no-control, canon_ver2_20260907, NoGlobalKill)" >> evaluation/runs/chain_lcd1000_20260906.log
powershell -NoProfile -ExecutionPolicy Bypass -Command "& 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1' -Name '$NAME' -OutDir '$OUT' -Network 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx' -Tuning 'evaluation/configs/canon_ver2_20260907.json' -Mapping '$D/control_mapping_ver2.json' -VbsConfig '$D/real_world_modi_control_config_ver2.vbs' -UrbanInputGateMap 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv' -Controller 'no-control' -ForceStepwise -SimPeriod 5400 -ControlIntervalSec 150 -Seed 13 -ControlStartSec 900 -WarmupController 'no-control' -StateLogIntervalSec 30 -DemandScale 1.0" > "evaluation/runs/$NAME.chainlog.txt" 2>&1
rc=$?
echo "$(date '+%m-%d %H:%M:%S')  DONE  $NAME  exit=$rc  결정 $(ls $OUT/decisions_*/action_*.json 2>/dev/null | wc -l)" >> evaluation/runs/chain_lcd1000_20260906.log
