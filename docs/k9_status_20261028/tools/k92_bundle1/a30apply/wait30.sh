#!/bin/sh
# Gates A30 wait (<= 9 min): ends when the stage-record set or the STOP-file set changes, or the chain python (PID $1)
# is gone, or 540 s pass.  Looks at names and the process table only.
O='D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/k92t'
PID="$1"
s0="$(ls "$O/stages" 2>/dev/null | tr '\n' ' ')|$(ls "$O" | grep '^STOP_' | tr '\n' ' ')"
t=0
while [ $t -lt 540 ]; do
  sleep 15; t=$((t+15))
  s1="$(ls "$O/stages" 2>/dev/null | tr '\n' ' ')|$(ls "$O" | grep '^STOP_' | tr '\n' ' ')"
  if [ "$s1" != "$s0" ]; then echo "CHANGE after ${t}s: $s1"; exit 0; fi
  if ! tasklist //FI "PID eq $PID" 2>/dev/null | grep -q "$PID"; then echo "PROCESS_GONE after ${t}s: $s1"; exit 0; fi
done
echo "TIMEOUT 540s: $s1"
