#!/bin/bash
cd "$(dirname "$0")"
export PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
while ! grep -q DONE out/run6.status 2>/dev/null; do sleep 5; done
python -B detail_check.py D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31 va_s31 3300 > out/detail_va_s31.log 2>&1; echo "va_s31 $?" >> out/detail.status
python -B detail_check.py D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41 va_s41 1950 > out/detail_va_s41.log 2>&1; echo "va_s41 $?" >> out/detail.status
python -B detail_check.py D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43 va_s43 2400 > out/detail_va_s43.log 2>&1; echo "va_s43 $?" >> out/detail.status
echo DONE >> out/detail.status
