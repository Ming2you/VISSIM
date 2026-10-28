---
name: vissim-lcd-lineage-20260907
description: lcd200/lcd1000 의 정체 — 두 망의 유일한 차이는 램프미터 커넥터 8개의 lnChgDist(200↔1000 m). 원래 x18 망이 1000 이고 lcd200 이 09-03 의 수정. 망별 무제어/제어 TTT 대조표와 fzp 위치
metadata:
  type: project
---

# lcd200 ↔ lcd1000 계보와 대조표 (2026-09-07)

**유일한 차이** = 램프미터 커넥터 8개(10480·10482·10484·10490·10639·10644·10646·10681)의 `lnChgDist` 200 ↔ 1000 m. 다른 속성·기하 전부 동일(diff 8줄).
원래 `fwsweep_x18.inpx` 가 **1000**(450/768 분포)이고, 09-03 `_lcd200.inpx` 에서 200 으로 낮춘 것이 rampbn → rampbn_qc 에 이어졌다. `rampbn_qc_lcd1000` 은 원래값 복원.
무제어에 관해 rampbn ≡ rampbn_qc(lcd200), rampmax ≡ rampbn_qc_lcd1000: nc_rampmax(09-03) 8082.3 == h0(09-06) 8082.3 정확히 일치.

커넥터 기하(from 링크·L1·pos → 본선): 10482 32@1029→26 · 10490 32@1331→2 · 10480 31@735→26 · 10484 31@412→24 · 10646 68@352→26 · 10681 68@117→2 · 10644 69@1740→26 · 10639 70@180→2.
lnChgDist 1000 이면 램프행 차량이 링크 32 는 pos ~30/330 부터, 31·68 은 진입 전(상류 정지선)부터 L1 을 찾는다. 링크 길이: 32 1963 m(3차로) · 31 1959(3) · 68 1990(4) · 69 1797(4) · 70 338(2) · 66 2662(4).

| 망 | 무제어 | 제어(canon_0905) | 기타 |
|---|---|---|---|
| lcd200 (rampbn/_qc) | nc_rampbn·nc_out 7952.4 | g1 7741.5 (−210) · canon_0904 7803.8 | arm_meterfullopen 9083.7 |
| lcd1000 (_qc_lcd1000 ≡ rampmax) | h0·nc_rampmax 8082.3 | h11 8629.0 (+547) · b0(RL+B0) 8313.4 · h7 8356.4 | |
| pre-rampbn x18 | nc_base 6675.7 · nc_lcd200 6622.3 | | rampbn 편집이 무제어를 +1300 올림 |

fzp(5 s 궤적, ~310 MB, `evaluation/runs/<런>/vissim_eval/*.fzp`, 컬럼 SimSec;No;Link;Lane;Pos;PosLat;Speed;TmInNetTot;DelayTm)는 위 런 전부에 있다(러너 기본 RW_NATIVE_EVAL). h0 런의 `vissim_eval` 은 ls 로 0 처럼 보여도 4파일 323 MB.
fzp 진단 산출물: `outputs/lcd_fzp_analysis_20260907/{A,B,C,D}` (워크플로 wf_702951eb, 2026-09-07 12:xx).

**How to apply:** "lcd 바꿔서 뭐가 달라졌나" 는 램프행 차량의 차로변경 시작점(1 km vs 200 m) 하나다. lcd200 결과를 인용할 때 그것이 09-03 수정판임을 밝혀라. 무제어 비교는 같은 lcd 의 무제어(7952.4 / 8082.3)와만.

**Ver2 채택 함정 (2026-09-07 15:3x)**: VISSIM GUI 로 링크를 쪼개면 그 링크를 지나는 정적 경로의 linkSeq 가 새 커넥터를 빠뜨릴 수 있다 — 1131-1(2→24: [119] 만, 10613·10702 누락), 1131-3(10613 누락), 1132-3(26→120: 빈 seq, 10771 누락). VISSIM 은 망 `.err` 에 `Static Vehicle Route X - Y is not complete` 를 남기고 **시뮬이 시작되지 않는다**(cscript EXIT_NO_DONE, 런로그엔 ERROR 줄 없음 — STAGE=NET_LOADED 뒤 조용히 종료).
내 경로 걷기 검사는 "끊김 수 기준 22 vs Ver2 21" 만 비교해 놓쳤다 — **집합 차이**로 비교해야 한다(기준에도 24개 끊김이 있고 그건 정상). 수정: linkSeq 에 [10613,119,10702] / [10613,119,10483,124,10775] / [10771] 삽입(바이트 편집, CRLF 보존). 망 편집 뒤엔 `.err` 의 Error 델타를 먼저 봐라(CLAUDE.md 규칙 그대로).

**Ver2 함정 2 (16:0x)**: VBS 생성 config 의 `RW_EXPECTED_VSL_ACTION_ROWS`·`RW_EXPECTED_VSL_ACTION_KEYS` 는 DSD 수(66)와 정확히 맞아야 한다 — 하나라도 어긋나면 `ACTION_CSV_CONTRACT` 로 **매 결정 거부**되고 시뮬은 끝까지 돌지만 RUN_INTEGRITY_FAILURE(EXIT_NO_DONE). 런로그 `ERROR=ACTION_CSV_CONTRACT sim_sec=1 vsl=66/66 …` 가 지문(카운트는 맞아 보여도 ROWS 상수가 71 이면 실패). 정본 틀에서 config 를 재조립할 때 이전 수정(66)이 되살아난 71 로 덮였다. 키는 어댑터가 실제로 쓴 action_000900.csv 의 vsl 행(segment|dsd|link|lane)에서 뽑는 게 안전.
