#!/bin/sh
# K8 chain 2 (after chain 1): AD jobs for S3, lane_group_kinds capture, full decision with passive hooks.
# Roots: env K8G_ROOT / K8G_OUT (defaults in k8common.py). Logs go where the caller redirects, by convention
#   OUT=$(python -B k8common.py --print-out); sh chainN.sh > "$OUT/out/chainN.log" 2>&1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(python -B "$HERE/k8common.py" --print-out) || exit 1
mkdir -p "$OUT/out" && cd "$OUT" || exit 1
export PYTHONHASHSEED=0
until grep -q CHAIN1_DONE out/chain1.log; do sleep 10; done
python -B "$HERE"/jobs.py 2700 base REF_ad ad REF -
python -B "$HERE"/jobs.py 2700 base REF_ad_s3 ad REF s3
python -B "$HERE"/capture.py lgk 2700
python -B "$HERE"/full.py 2700 hook
python -B "$HERE"/jobs.py 4950 base REF_ad ad REF -
python -B "$HERE"/jobs.py 4950 base REF_ad_s3 ad REF s3
echo CHAIN2_DONE
