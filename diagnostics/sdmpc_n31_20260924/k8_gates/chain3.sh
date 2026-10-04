#!/bin/sh
# K8 chain 3 (after chain 2): T+150 observation projections for the one-step fidelity check of S5/S9,
# and a REF rerun at 2700 with per-movement block-end stocks.
# Roots: env K8G_ROOT / K8G_OUT (defaults in k8common.py). Logs go where the caller redirects, by convention
#   OUT=$(python -B k8common.py --print-out); sh chainN.sh > "$OUT/out/chainN.log" 2>&1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(python -B "$HERE/k8common.py" --print-out) || exit 1
mkdir -p "$OUT/out" && cd "$OUT" || exit 1
export PYTHONHASHSEED=0
until grep -q CHAIN2_DONE out/chain2.log; do sleep 10; done
python -B "$HERE"/prep.py 2850 5100 1950
python -B "$HERE"/capture.py base 2850 5100 1950
python -B "$HERE"/jobs.py 2700 base REF_scalar2 scalar REF -
python -B "$HERE"/jobs.py 2700 s59 REF_scalar_cap_s59 scalar REF - 2>/dev/null || true
echo CHAIN3_DONE
