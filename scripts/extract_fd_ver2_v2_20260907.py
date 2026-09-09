# -*- coding: utf-8 -*-
"""Ver2 무제어(v0) .fzp 궤적에서 본선 세그먼트별 q-k 기본도(FD) 자료를 뽑는다 (2026-09-07).

한 프레임(5 s)마다 본선 사슬 위 차량을 세그먼트 셀에 넣어
  k_i = N_i / (L_i · lanes_i)            [veh/km/lane]
  v_i = 셀 안 순간속도 평균               [km/h]  (스냅샷 평균 = 공간평균속도)
  q_i^edge = 세그먼트 하류 경계 통과 대수 × 720 / lanes_i   [veh/h/lane]
를 잰다. q^kv = k·v 는 셀 내부 정의, q^edge 는 경계 실측이라 둘을 같이 낸다.
사용: python extract_fd_ver2_20260907.py <fzp> <mapping_json> <out_csv> [t_min]"""
import io, sys, json, math
from pathlib import Path

NSEG = 0

def main():
    fzp, mapj, outc = sys.argv[1], sys.argv[2], sys.argv[3]
    t_min = float(sys.argv[4]) if len(sys.argv) > 4 else 900.0
    global NSEG
    NSEG = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    M = json.load(io.open(mapj, encoding="utf-8"))
    fl = M["freeway_model_links"]
    chain = {}      # link -> (dir, offset)
    meta = {}
    for d, spec in fl.items():
        for lk, off in zip(spec["chain_links"], spec["chain_offsets_m"]):
            chain[str(lk)] = (d, float(off))
        old_lanes = [float(v) for v in spec["segment_lanes"]]
        total = float(spec["length_m"])
        nseg = NSEG if NSEG else len(old_lanes)
        seglen = total / nseg
        if NSEG:
            # 새 균등 격자의 차로수 = 새 셀 중점이 속한 **옛 격자 셀**의 차로수(중점 규칙 유지).
            old_len = total / len(old_lanes)
            lanes = [old_lanes[min(len(old_lanes) - 1, int(((i + 0.5) * seglen) // old_len))] for i in range(nseg)]
        else:
            lanes = old_lanes
        meta[d] = {"seglen_m": seglen, "lanes": lanes, "nseg": nseg, "length_m": total}
    # 누적기: (dir, seg, t) -> [N, sum_v, per-lane counts]
    acc = {}
    cross = {}      # (dir, seg, t) -> 하류 경계 통과 대수
    leave = {}      # (dir, seg, t) -> 그 셀에서 사슬을 벗어난 대수(off-ramp / 망 이탈)
    prev = {}       # veh -> (dir, chainpos)
    nline = 0; tcur = None; frames = 0
    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line[0] in "*$": continue
            p = line.rstrip("\n").split(";")
            if len(p) < 7: continue
            try:
                t = float(p[0])
            except ValueError:
                continue
            nline += 1
            if t != tcur:
                if tcur is not None: frames += 1
                # 프레임이 바뀌면 이전 프레임 위치를 확정한 뒤 교차 판정은 아래에서 누적된 cur 로 처리
                tcur = t
            lk = p[2]
            c = chain.get(lk)
            if c is None: continue
            d, off = c
            try:
                pos = float(p[4]); spd = float(p[6]); lane = int(p[3])
            except ValueError:
                continue
            cp = off + pos
            m = meta[d]
            si = int(cp // m["seglen_m"])
            if si < 0: si = 0
            if si >= m["nseg"]: si = m["nseg"] - 1
            if t >= t_min:
                key = (d, si, t)
                a = acc.get(key)
                if a is None: a = acc[key] = [0, 0.0, {}]
                a[0] += 1; a[1] += spd
                a[2][lane] = a[2].get(lane, 0) + 1
    # 교차 판정은 두 번째 패스가 필요 없도록 위에서 못했으니 여기서 다시 (메모리 절약 위해 별도 패스)
    print("1차 패스: %d 행, %d 프레임" % (nline, frames + 1))
    # 2차 패스 — 경계 통과
    prev = {}; prev_t = None
    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        cur = {}; tcur = None
        for line in f:
            if not line or line[0] in "*$": continue
            p = line.rstrip("\n").split(";")
            if len(p) < 7: continue
            try: t = float(p[0])
            except ValueError: continue
            if tcur is None: tcur = t
            if t != tcur:
                _flush(cur, prev, tcur, prev_t, meta, cross, leave, t_min)
                prev, prev_t = cur, tcur
                cur = {}; tcur = t
            c = chain.get(p[2])
            if c is None: continue
            d, off = c
            try: pos = float(p[4])
            except ValueError: continue
            cur[p[1]] = (d, off + pos)
        _flush(cur, prev, tcur, prev_t, meta, cross, leave, t_min)
    rows = []
    for (d, si, t), a in sorted(acc.items()):
        m = meta[d]
        lanes = m["lanes"][si]; Lkm = m["seglen_m"] / 1000.0
        k = a[0] / (Lkm * lanes)
        v = a[1] / a[0] if a[0] else float("nan")
        qkv = k * v
        cr = cross.get((d, si, t), 0)
        lv = leave.get((d, si, t), 0)
        qedge = cr * 720.0 / lanes
        qsend = (cr + lv) * 720.0 / lanes
        lanemix = ",".join("%d:%d" % (ln, n) for ln, n in sorted(a[2].items()))
        rows.append((d, si, t, a[0], lanes, round(k, 4), round(v, 3), round(qkv, 2), cr, lv,
                     round(qedge, 1), round(qsend, 1), lanemix))
    with io.open(outc, "w", encoding="utf-8", newline="") as g:
        g.write("dir,seg,t,n,lanes,k_veh_km_lane,v_kph,q_kv_veh_h_lane,cross,leave,"
                "q_edge_veh_h_lane,q_send_veh_h_lane,lane_mix" + chr(10))
        for r in rows:
            g.write(",".join(str(x) for x in r) + "\n")
    print("표본 %d 행 → %s" % (len(rows), outc))


def _flush(cur, prev, tcur, prev_t, meta, cross, leave, t_min):
    """prev(t-5) 위치와 cur(t) 위치를 대조해 (a) 경계 통과와 (b) 셀에서 사슬 이탈을 센다.

    이탈 = 직전에 셀 si 의 사슬 위에 있었는데 지금은 사슬 밖(램프 링크) 이거나 망에 없다. 마지막 셀의
    이탈은 본선 망이탈이고, 중간 셀의 이탈은 그 셀 안 off-ramp 진출이다. 둘 다 그 셀의 sending 이다."""
    if not prev or prev_t is None or tcur is None: return
    if tcur - prev_t > 5.001 or tcur < t_min: return
    for v, c1 in prev.items():
        if c1 is None: continue
        d, cp1 = c1
        L = meta[d]["seglen_m"]; n = meta[d]["nseg"]
        s1 = min(n - 1, int(cp1 // L))
        c2 = cur.get(v, "gone")
        if c2 == "gone" or c2 is None or c2[0] != d:
            leave[(d, s1, tcur)] = leave.get((d, s1, tcur), 0) + 1
            continue
        cp2 = c2[1]
        if cp2 <= cp1: continue
        s2 = min(n - 1, int(cp2 // L))
        for si in range(s1, s2):
            cross[(d, si, tcur)] = cross.get((d, si, tcur), 0) + 1


if __name__ == "__main__":
    main()
