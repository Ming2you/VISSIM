#!/usr/bin/env bash
# Ver2 사다리(chain_ver2) 종료 뒤 v0(Ver2 무제어 기준선)를 돈다. VISSIM 유휴 확인.
cd "C:/Users/TRLAB/Desktop/찐찐막/VISSIM" || exit 1
L=evaluation/runs/chain_lcd1000_20260906.log
until grep -q "VER2_LADDER_DONE\|ERROR VER2_LADDER\|VER2_SEQ_DONE" "$L"; do sleep 60; done
sleep 20
while tasklist | grep -qiE "vissim200|cscript"; do sleep 20; done
rm -rf evaluation/runs/v0_nocontrol_ver2_x18_20260907
echo "$(date '+%m-%d %H:%M:%S')  [Claude] 사다리 종료 → v0(Ver2 무제어 기준선) 발사" >> "$L"
bash "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/363c7808-e973-4c3e-92d8-2d00dcc50f83/scratchpad/run_ver2_nocontrol.sh"
echo "$(date '+%m-%d %H:%M:%S')  V0_AFTER_LADDER_DONE" >> "$L"
