#!/bin/bash
cd "$(dirname "$0")"
export PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
while ! grep -q DONE out/detail.status 2>/dev/null; do sleep 5; done
python -B per_decision.py D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31 va_s31 > out/per_decision_va_s31.log 2>&1; echo "va_s31 $?" >> out/perdec.status
echo DONE >> out/perdec.status
