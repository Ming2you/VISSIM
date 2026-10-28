#!/bin/sh
# V-B poll (session helper, read only): wait up to 510 s for a new steps.jsonl line or a STOP file, then print status.
V=/d/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb
n0=$(wc -l < $V/steps.jsonl 2>/dev/null || echo 0)
for i in $(seq 1 51); do
  if ls $V/STOP_vb_* >/dev/null 2>&1; then break; fi
  n=$(wc -l < $V/steps.jsonl 2>/dev/null || echo 0)
  if [ "$n" != "$n0" ]; then break; fi
  if grep -q 'VB_CHAIN_DONE' /d/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/logs/vb_chain.txt 2>/dev/null; then break; fi
  sleep 10
done
date '+%H:%M:%S'
ls $V/STOP_vb_* 2>/dev/null
tail -4 $V/driver_log.txt
tail -2 $V/steps.jsonl | cut -c1-200
powershell -NoProfile -Command '"python=" + @(Get-Process -Name python -ErrorAction SilentlyContinue).Count + " vissim=" + @(Get-Process | Where-Object { $_.ProcessName -like "VISSIM*" }).Count'
