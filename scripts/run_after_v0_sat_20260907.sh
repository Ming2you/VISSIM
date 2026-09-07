#!/usr/bin/env bash
# v0(Ver2 무제어) 완주 뒤: Ver2 씨앗(차로군 지속 방류·큐 링크 분류) 생성 → chain_ver2 start=7 (a7 +SATV2, a8 +SAT3).
cd "C:/Users/TRLAB/Desktop/찐찐막/VISSIM" || exit 1
L=evaluation/runs/chain_lcd1000_20260906.log
until grep -q "V0_AFTER_LADDER_DONE" "$L"; do sleep 60; done
sleep 10
while tasklist | grep -qiE "vissim200|cscript"; do sleep 20; done
echo "$(date '+%m-%d %H:%M:%S')  [Claude] v0 완주 → Ver2 씨앗 생성(lane_group_sustained_v0_ver2 · link_queue_class_v0_ver2)" >> "$L"
python scripts/derive_lane_group_sustained_ver2_20260907.py >> evaluation/runs/chain_ver2_seed_20260907.log 2>&1 && python scripts/derive_link_queue_class_ver2_20260907.py >> evaluation/runs/chain_ver2_seed_20260907.log 2>&1 \
  && echo "$(date '+%m-%d %H:%M:%S')  [Claude] 씨앗 생성 OK → a7(+SATV2)·a8(+SAT3) 발사" >> "$L" \
  || { echo "$(date '+%m-%d %H:%M:%S')  [Claude] 씨앗 생성 실패 — SAT 사다리 중단 (chain_ver2_seed_20260907.log 확인)" >> "$L"; echo "$(date '+%m-%d %H:%M:%S')  SAT_LADDER_DONE exit=SEED_FAIL" >> "$L"; exit 1; }
python scripts/chain_ver2_20260907.py 7 > evaluation/runs/chain_ver2_sat_launch_20260907.log 2>&1
echo "$(date '+%m-%d %H:%M:%S')  SAT_LADDER_DONE exit=$?" >> "$L"
