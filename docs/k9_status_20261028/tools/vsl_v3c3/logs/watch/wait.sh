#!/bin/bash
# wait.sh MAXSEC : read-only watcher. Exits early when the launcher log grows or any run.json gets "finished"; else after MAXSEC.
R=/d/VISSIM_runs/20261027_vsl_v3c3
L=$R/vsl_launcher.log
MAX=${1:-540}
n0=$(wc -l < "$L" 2>/dev/null || echo 0)
f0=$(grep -l '"finished"' $R/s*/run*/run.json 2>/dev/null | wc -l)
t=0
status() {
  echo "== $(date '+%Y-%m-%d %H:%M:%S') KST  waited=${t}s"
  for s in 31 41 43; do for a in run run_retry1; do d=$R/s$s/$a; [ -d "$d" ] || continue
    last=$(tail -n1 "$d/progress.csv" 2>/dev/null); fin=$(grep -o '"finished": *"[^"]*"' "$d/run.json" 2>/dev/null); comp=$(grep -o '"completed": *[a-z]*' "$d/run.json" 2>/dev/null)
    vp=$(grep -A2 '"vissim"' "$d/run.json" 2>/dev/null | grep -o '"pid": *[0-9]*' | head -1)
    age=$(( $(date +%s) - $(stat -c %Y "$d/progress.csv" 2>/dev/null || date +%s) ))
    echo "s$s/$a last=[$last] progress_age=${age}s $vp $comp $fin"; done; done
  echo "VISSIM_pc=$(tasklist //FO CSV //NH 2>/dev/null | grep -ci '^"VISSIM')"
  echo "disk: $(df -BG /c /d | awk 'NR>1{print $6"="$4}' | tr '\n' ' ')"
}
while [ $t -lt $MAX ]; do
  n=$(wc -l < "$L" 2>/dev/null || echo 0)
  f=$(grep -l '"finished"' $R/s*/run*/run.json 2>/dev/null | wc -l)
  if [ "$n" -gt "$n0" ] || [ "$f" -gt "$f0" ]; then echo "EVENT"; tail -n +$((n0+1)) "$L"; status; exit 0; fi
  sleep 15; t=$((t+15))
done
echo "TIMEOUT"; status
