# -*- coding: utf-8 -*-
"""Ver2 v0 .fzp → 본선 사슬의 100 m 격자 시공간 자료(밀도·속도)와 차로별 점유. (2026-09-07)
세그먼트(1.35 km)보다 잘게 봐야 합류·차로수 변화의 영향이 국소인지 구간 전체인지 갈린다.
사용: python extract_fd_profile_ver2_20260907.py <fzp> <mapping_json> <out_npz> [bin_m] [t_min]"""
import io, sys, json
import numpy as np


def main():
    fzp, mapj, outn = sys.argv[1], sys.argv[2], sys.argv[3]
    BIN = float(sys.argv[4]) if len(sys.argv) > 4 else 100.0
    t_min = float(sys.argv[5]) if len(sys.argv) > 5 else 900.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    M = json.load(io.open(mapj, encoding="utf-8"))
    fl = M["freeway_model_links"]
    chain = {}
    dirs = sorted(fl)
    nb = {}
    for d in dirs:
        spec = fl[d]
        for lk, off in zip(spec["chain_links"], spec["chain_offsets_m"]):
            chain[str(lk)] = (d, float(off))
        nb[d] = int(np.ceil(float(spec["length_m"]) / BIN))
    T0, T1, DT = 900.0, 5400.0, 5.0
    nt = int((T1 - t_min) / DT) + 1
    cnt = {d: np.zeros((nt, nb[d])) for d in dirs}
    spd = {d: np.zeros((nt, nb[d])) for d in dirs}
    lane_cnt = {d: np.zeros((nb[d], 5)) for d in dirs}   # 차로 1..4
    nread = 0
    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line[0] in "*$":
                continue
            p = line.split(";")
            if len(p) < 7:
                continue
            try:
                t = float(p[0])
            except ValueError:
                continue
            if t < t_min or t > T1:
                continue
            c = chain.get(p[2])
            if c is None:
                continue
            d, off = c
            try:
                b = int((off + float(p[4])) // BIN)
                v = float(p[6]); ln = int(p[3])
            except ValueError:
                continue
            if b < 0 or b >= nb[d]:
                continue
            ti = int(round((t - t_min) / DT))
            if ti < 0 or ti >= nt:
                continue
            cnt[d][ti, b] += 1.0
            spd[d][ti, b] += v
            if 1 <= ln <= 4:
                lane_cnt[d][b, ln] += 1.0
            nread += 1
    np.savez_compressed(outn, dirs=np.array(dirs), bin_m=BIN, t_min=t_min, dt=DT,
                        **{("cnt_%s" % d): cnt[d] for d in dirs},
                        **{("spd_%s" % d): spd[d] for d in dirs},
                        **{("lane_%s" % d): lane_cnt[d] for d in dirs})
    print("본선 기록 %d 행 → %s (격자 %.0f m, %d 프레임)" % (nread, outn, BIN, nt))
    for d in dirs:
        print("  %s 격자 %d개" % (d, nb[d]))


if __name__ == "__main__":
    main()
