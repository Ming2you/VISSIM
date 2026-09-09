# -*- coding: utf-8 -*-
"""fzp 에서 **완료차량**과 완료당 통행시간을 정확히 센다 (2026-09-09).

왜 다시 쓰나. `fzp_completed_stats_20260907.py` 는 "TMINNETTOT 은 떠나기 직전 1초에만
기록된다"를 전제로 `TMINNETTOT>0` 인 행을 완료로 셌다. 이 망의 fzp 에서는 그 전제가 틀리다 —
**매 행에 누적 체류시간이 들어 있다**(실측: 완료 5,293,695 = 사실상 전 행). 그래서 그 스크립트의
`완료`·`총통행시간`·`평균`은 전부 행 통계이지 차량 통계가 아니다. `진입차량`(고유 NO)만 맞다.

여기서 세는 것:
  진입   = fzp 에 한 번이라도 나온 고유 차량 수 (원점에 붙잡혀 못 들어온 차는 안 잡힌다)
  잔류   = 마지막 SIMSEC 에 아직 망 안에 있는 차량
  완료   = 진입 - 잔류
  완료당 통행시간 = 그 차량이 마지막으로 기록한 TMINNETTOT 의 평균 (완료 차량만)
  완료당 지체     = 같은 방식의 DELAYTM 평균

열: SIMSEC;NO;LINK;LANEIDX;POS;POSLAT;SPEED;TMINNETTOT;DELAYTM

TTT 와 함께 봐야 하는 이유. TTT 는 망 안 차량-시간 적분이라 **진입이 늘면 같이 오른다**.
진입이 같은데 TTT 만 오르면 그건 같은 차를 더 오래 붙잡은 것이고, 진입이 늘어서 오른 것이면
제어가 방류를 개선한 부작용일 수 있다. 이 스크립트가 그 둘을 가른다.

사용: python fzp_completed_exact_20260909.py <run 이름> [run 이름...]
"""
import io
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def stats(fzp):
    last_t = {}          # veh -> (simsec, tminnettot, delaytm)
    max_sec = 0.0
    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line[0] in "*$":
                continue
            p = line.rstrip("\n").split(";")
            if len(p) < 9:
                continue
            try:
                sec = float(p[0])
                tin = float(p[7])
                dly = float(p[8])
            except ValueError:
                continue
            if sec > max_sec:
                max_sec = sec
            veh = p[1]
            prev = last_t.get(veh)
            if prev is None or sec >= prev[0]:
                last_t[veh] = (sec, tin, dly)
    entered = len(last_t)
    resident = [v for v in last_t.values() if v[0] >= max_sec - 1e-6]
    done = [v for v in last_t.values() if v[0] < max_sec - 1e-6]
    n_done = len(done)
    tt = sum(v[1] for v in done) / n_done if n_done else 0.0
    dl = sum(v[2] for v in done) / n_done if n_done else 0.0
    tt_h = sum(v[1] for v in done) / 3600.0
    return dict(entered=entered, resident=len(resident), done=n_done,
                mean_tt_s=tt, mean_delay_s=dl, done_tt_veh_h=tt_h, last_sec=max_sec)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("%-46s %8s %8s %8s %10s %10s %12s" %
          ("런", "진입", "완료", "잔류", "완료당TT", "완료당지체", "완료TT(veh·h)"))
    for run in sys.argv[1:]:
        cand = sorted((R / "evaluation/runs" / run / "vissim_eval").glob("*.fzp"))
        if not cand:
            print("%-46s  fzp 없음" % run[:46])
            continue
        s = stats(str(cand[0]))
        print("%-46s %8d %8d %8d %9.1fs %9.1fs %12.1f" %
              (run[:46], s["entered"], s["done"], s["resident"],
               s["mean_tt_s"], s["mean_delay_s"], s["done_tt_veh_h"]))


if __name__ == "__main__":
    main()
