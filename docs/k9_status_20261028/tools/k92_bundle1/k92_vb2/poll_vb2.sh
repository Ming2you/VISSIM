#!/bin/sh
# V-B rerun poll (session helper, read only): wait up to 510 s for a new steps.jsonl line, a stage file or a STOP file,
# then print status (names, counts, driver log tail; no metric values).
V=/d/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/vb2
LG=/d/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/logs/vb2_chain.txt
n0=$(wc -l < $V/steps.jsonl 2>/dev/null || echo 0)
s0=$(ls $V/stages 2>/dev/null | wc -l)
for i in $(seq 1 51); do
  if ls $V/STOP_vb_* >/dev/null 2>&1; then break; fi
  n=$(wc -l < $V/steps.jsonl 2>/dev/null || echo 0)
  s=$(ls $V/stages 2>/dev/null | wc -l)
  if [ "$n" != "$n0" ] || [ "$s" != "$s0" ]; then break; fi
  if grep -q 'VB_CHAIN_DONE' $LG 2>/dev/null; then break; fi
  if ! powershell -NoProfile -Command 'if (@(Get-Process -Name python -ErrorAction SilentlyContinue).Count -gt 0) { exit 0 } else { exit 1 }'; then break; fi
  sleep 10
done
date '+%H:%M:%S'
ls $V/STOP_vb_* 2>/dev/null
echo "stages: $(ls $V/stages 2>/dev/null | tr '\n' ' ')"
echo "steps: $(wc -l < $V/steps.jsonl 2>/dev/null)"
tail -3 $V/driver_log.txt 2>/dev/null | cut -c1-220
tail -1 $V/steps.jsonl 2>/dev/null | cut -c1-220
tail -2 $LG 2>/dev/null | cut -c1-200
powershell -NoProfile -Command '"python=" + @(Get-Process -Name python -ErrorAction SilentlyContinue).Count + " vissim=" + @(Get-Process | Where-Object { $_.ProcessName -like "VISSIM*" }).Count'
df -h /c /d | tail -2 | awk '{print $1, $4}'
