#!/usr/bin/env bash
# B 사다리 드라이버: b0(canon_0905+RL+B0) → b1 +METER → b2 +SAT/SAT2 → b3 +PW25 → b4 +B5. 누적. 로그는 chain_lcd1000_20260906.log 에 이어 쓴다.
# 전제: VISSIM 유휴, 발사 전 검증(wf_ca192963) 통과. 시작 rung 을 첫 인자로 넘기면 그 단부터(앞 단은 완주 런 TTT 재사용).
cd "C:/Users/TRLAB/Desktop/찐찐막/VISSIM" || exit 1
START="${1:-0}"
python scripts/chain_b_ladder_20260907.py "$START" > "evaluation/runs/chain_b_ladder_launch_20260907.log" 2>&1
echo "$(date '+%m-%d %H:%M:%S')  B_SEQ_DONE exit=$?" >> evaluation/runs/chain_lcd1000_20260906.log
