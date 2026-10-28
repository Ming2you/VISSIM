#!/bin/bash
cd "$(dirname "$0")"
export PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
for pair in "D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31 va_s31" "D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41 va_s41" "D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43 va_s43" "D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31 j1_s31" "D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41 j1_s41" "D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43 j1_s43"; do
  set -- $pair
  python -B recompute_meter.py "$1" "$2" > "out/recompute_$2.log" 2>&1
  echo "$2 exit $? $(date +%H:%M:%S)" >> out/run6.status
done
echo DONE >> out/run6.status
