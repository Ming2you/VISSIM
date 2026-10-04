#!/bin/sh
# K8 chain 4 (after chain 3): S3 AD reruns with the fixed patcher, and S3 incl. AFA sites; M2ALL AD pair.
# Roots: env K8G_ROOT / K8G_OUT (defaults in k8common.py). Logs go where the caller redirects, by convention
#   OUT=$(python -B k8common.py --print-out); sh chainN.sh > "$OUT/out/chainN.log" 2>&1
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(python -B "$HERE/k8common.py" --print-out) || exit 1
mkdir -p "$OUT/out" && cd "$OUT" || exit 1
export PYTHONHASHSEED=0
until grep -q CHAIN3_DONE out/chain3.log; do sleep 10; done
rm -rf out/002700/jobs/REF_ad_s3
python -B "$HERE"/jobs.py 2700 base REF_ad_s3 ad REF s3
python -B "$HERE"/jobs.py 2700 base REF_ad_s3f ad REF s3,s3f
python -B "$HERE"/jobs.py 2700 base M2ALL_ad ad M2ALL -
python -B "$HERE"/jobs.py 2700 base M2ALL_ad_s3f ad M2ALL s3,s3f
echo CHAIN4_DONE
