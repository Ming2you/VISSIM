#!/bin/sh
# K8 scalar job chain (sequential, BELOW_NORMAL via jobs.py, PYTHONHASHSEED=0)
# Roots: env K8G_ROOT / K8G_OUT (defaults in k8common.py). Logs go where the caller redirects, by convention
#   OUT=$(python -B k8common.py --print-out); sh chainN.sh > "$OUT/out/chainN.log" 2>&1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(python -B "$HERE/k8common.py" --print-out) || exit 1
mkdir -p "$OUT/out" && cd "$OUT" || exit 1
export PYTHONHASHSEED=0
for T in 2700 4950 1800; do
  [ "$T" = 2700 ] || python -B "$HERE"/jobs.py $T base REF_scalar scalar REF -
  python -B "$HERE"/jobs.py $T base REF_scalar_s1 scalar REF s1
  python -B "$HERE"/jobs.py $T base M2ALL_scalar scalar M2ALL -
  python -B "$HERE"/jobs.py $T base M2ALL_scalar_s1 scalar M2ALL s1
  python -B "$HERE"/jobs.py $T s5 REF_scalar_cap_s5 scalar REF -
  python -B "$HERE"/jobs.py $T s9 REF_scalar_cap_s9 scalar REF -
done
echo CHAIN1_DONE
