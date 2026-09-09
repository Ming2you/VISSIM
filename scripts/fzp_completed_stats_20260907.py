# -*- coding: utf-8 -*-
"""fzp 에서 완료차량 수와 그 총 통행시간을 센다 (2026-09-07).
왜 — TTT 는 `total_vehicles` 적분이라 **원점에 붙잡힌 차량이 안 잡힌다.** 수요가 진입용량을 넘으면
제어가 방류를 개선할수록 차가 더 들어와 TTT 가 오르는 역인센티브가 생긴다. 완료차량당 통행시간은
그 왜곡이 없다. TmInNetTot 은 차량이 망을 떠나기 직전 1초에만 기록된다(그 외에는 0)."""
import io, sys

def main():
    fzp = sys.argv[1]
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    n_done = 0; t_sum = 0.0; d_sum = 0.0; seen = set()
    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line[0] in "*$":
                continue
            p = line.rstrip("\n").split(";")
            if len(p) < 9:
                continue
            seen.add(p[1])
            try:
                tin = float(p[7])
            except ValueError:
                continue
            if tin > 0.0:
                n_done += 1
                t_sum += tin
                try:
                    d_sum += float(p[8])
                except ValueError:
                    pass
    print("%s\t진입차량 %d\t완료 %d\t총통행시간 %.1f veh·h\t평균 %.1f s\t총지체 %.1f veh·h" % (
        fzp.split("/")[-3] if "/" in fzp else fzp, len(seen), n_done, t_sum / 3600.0,
        (t_sum / n_done) if n_done else 0.0, d_sum / 3600.0))

if __name__ == "__main__":
    main()
