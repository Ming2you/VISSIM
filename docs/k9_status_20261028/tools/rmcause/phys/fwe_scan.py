# -*- coding: utf-8 -*-
"""FW_E physics scan of one VISSIM FZP (read-only). 2026-10-24 rmcause INV_PHYSICS.

Usage: python -B fwe_scan.py <tag> <fzp_path> <out_dir>

Writes <out_dir>/<tag>.json with
- grid: 100 m x 60 s FW_E chain bins: vehicle-frames N, speed sum (all lanes)
- lane grid: 100 m x 60 s x lane (lanes 1..4) for chain 3800-8000 m
- crossings per 60 s at detector lines (chain metres)
- ramp merges / connector entries / connector and from-link stock (all, queued <15 km/h) per 60 s
- off-ramp diverges and connector stock per 60 s
- entry insertions (first appearance on link 74) per 60 s
- per-vehicle crossing times for lines 300 / 4200 / 5300 / 7700 / 10500 (for travel time)
- chain veh-h (5 s frames) for a cross-check with fw_e_main 7 links
Reads only the FZP. Writes only the out file.
"""
import json, sys, math, os, hashlib, time

CHAIN = [(74, 0.0, 4), (10699, 2701.577, 4), (2, 2734.527, 4), (10613, 6841.743, 3),
         (119, 6847.981, 3), (10702, 7431.364, 3), (24, 7438.047, 3)]
OFF = {l: o for l, o, _ in CHAIN}
CHAIN_END = 10784.028
# on-ramp connectors: id -> (merge chain pos, from link)
ONR = {10639: (4698.7, 70), 10681: (5041.9, 68), 10490: (7243.1, 129), 10484: (7603.7, 31)}
ONR_FROM = {v[1]: k for k, v in ONR.items()}
# off-ramp connectors: id -> (diverge chain pos, to link)
OFR = {10643: (4386.3, 126), 10682: (4746.9, 121), 10481: (6826.8, 127), 10483: (7240.3, 124)}
LINES = [300, 2000, 3000, 3700, 4200, 4380, 4600, 4690, 4740, 4900, 5030, 5100, 5300, 5800, 6300,
         6800, 6835, 7000, 7230, 7300, 7590, 7700, 8500, 10500]
TT_LINES = [300, 4200, 5300, 7700, 10500]
BIN_M = 100.0
WIN = 60.0
NB = int(math.ceil(CHAIN_END / BIN_M))
NW = 151
LANE_X0, LANE_X1 = 3800.0, 8000.0
NLB = int((LANE_X1 - LANE_X0) / BIN_M)
QSPEED = 15.0


def main():
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    gN = [[0] * NB for _ in range(NW)]
    gV = [[0.0] * NB for _ in range(NW)]
    lN = [[[0] * 4 for _ in range(NLB)] for _ in range(NW)]
    lV = [[[0.0] * 4 for _ in range(NLB)] for _ in range(NW)]
    cross = {x: [0] * NW for x in LINES}
    merge = {r: [0] * NW for r in ONR}
    conn_entry = {r: [0] * NW for r in ONR}
    conn_stock = {r: [0] * NW for r in ONR}      # vehicle-frames on connector
    conn_q = {r: [0] * NW for r in ONR}          # vehicle-frames speed<15
    from_stock = {r: [0] * NW for r in ONR}
    from_q = {r: [0] * NW for r in ONR}
    conn_qmax = {r: [0] * NW for r in ONR}       # max queued (connector+from link) in one frame
    div = {r: [0] * NW for r in OFR}
    off_stock = {r: [0] * NW for r in OFR}
    off_q = {r: [0] * NW for r in OFR}
    ins = [0] * NW
    frames = [0] * NW
    maxpos = {}
    last = {}  # veh -> (link, x or None)
    seen = set()
    tt = {}  # veh -> {line: t}
    chain_vf = 0
    cur_t = None
    frame_q = {r: 0 for r in ONR}
    nrows = 0
    skipped01 = 0
    h = hashlib.sha256()

    def flush_frame(t):
        w = int(t // WIN)
        if w >= NW:
            return
        frames[w] += 1
        for r in ONR:
            if frame_q[r] > conn_qmax[r][w]:
                conn_qmax[r][w] = frame_q[r]
            frame_q[r] = 0

    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            c0 = raw[:1]
            if c0 in (b'$', b'*', b'\r', b'\n') or not raw.strip():
                continue
            parts = raw.split(b';', 7)
            try:
                t = float(parts[0])
            except ValueError:
                continue
            if t < 1.0:
                skipped01 += 1
                continue
            nrows += 1
            if cur_t is None:
                cur_t = t
            elif t != cur_t:
                flush_frame(cur_t)
                cur_t = t
            veh = int(parts[1]); link = int(parts[2]); lane = int(parts[3])
            pos = float(parts[4]); spd = float(parts[6])
            w = int(t // WIN)
            if w >= NW:
                continue
            if link in OFF:
                x = OFF[link] + pos
                b = min(int(x // BIN_M), NB - 1)
                gN[w][b] += 1; gV[w][b] += spd
                chain_vf += 1
                if LANE_X0 <= x < LANE_X1 and 1 <= lane <= 4:
                    lb = int((x - LANE_X0) // BIN_M)
                    lN[w][lb][lane - 1] += 1; lV[w][lb][lane - 1] += spd
                pl = last.get(veh)
                if veh not in seen and link == 74:
                    ins[w] += 1
                    lo = -1.0
                elif pl is not None and pl[1] is not None:
                    lo = pl[1]
                elif pl is not None and pl[0] in ONR:
                    merge[pl[0]][w] += 1
                    lo = ONR[pl[0]][0]
                else:
                    lo = None
                if lo is not None and x > lo:
                    for X in LINES:
                        if lo < X <= x:
                            cross[X][w] += 1
                            if X in TT_LINES:
                                tt.setdefault(veh, {})[X] = t
                last[veh] = (link, x)
            else:
                pl = last.get(veh)
                if link in ONR:
                    if pl is None or pl[0] != link:
                        conn_entry[link][w] += 1
                    conn_stock[link][w] += 1
                    if spd < QSPEED:
                        conn_q[link][w] += 1; frame_q[link] += 1
                elif link in ONR_FROM:
                    r = ONR_FROM[link]
                    from_stock[r][w] += 1
                    if spd < QSPEED:
                        from_q[r][w] += 1; frame_q[r] += 1
                    maxpos[link] = max(maxpos.get(link, 0.0), pos)
                elif link in OFR:
                    if pl is not None and pl[1] is not None:
                        div[link][w] += 1
                        lo = pl[1]; x = OFR[link][0]
                        for X in LINES:
                            if lo < X <= x:
                                cross[X][w] += 1
                    off_stock[link][w] += 1
                    if spd < QSPEED:
                        off_q[link][w] += 1
                if link in ONR or link in OFR:
                    maxpos[link] = max(maxpos.get(link, 0.0), pos)
                last[veh] = (link, None)
            seen.add(veh)
    if cur_t is not None:
        flush_frame(cur_t)
    out = {
        'tag': tag, 'fzp': path, 'fzp_sha256': h.hexdigest(), 'rows_used': nrows, 'rows_t_lt_1_skipped': skipped01,
        'bin_m': BIN_M, 'win_s': WIN, 'nb': NB, 'nw': NW, 'lane_x0': LANE_X0, 'lane_x1': LANE_X1, 'qspeed': QSPEED,
        'frames': frames, 'gN': gN, 'gV': gV, 'lN': lN, 'lV': lV,
        'cross': {str(k): v for k, v in cross.items()},
        'merge': {str(k): v for k, v in merge.items()}, 'conn_entry': {str(k): v for k, v in conn_entry.items()},
        'conn_stock': {str(k): v for k, v in conn_stock.items()}, 'conn_q': {str(k): v for k, v in conn_q.items()},
        'from_stock': {str(k): v for k, v in from_stock.items()}, 'from_q': {str(k): v for k, v in from_q.items()},
        'ramp_qmax': {str(k): v for k, v in conn_qmax.items()},
        'div': {str(k): v for k, v in div.items()}, 'off_stock': {str(k): v for k, v in off_stock.items()},
        'off_q': {str(k): v for k, v in off_q.items()}, 'ins': ins, 'maxpos': {str(k): v for k, v in maxpos.items()},
        'tt': {str(k): v for k, v in tt.items()}, 'chain_veh_h_5s': chain_vf * 5.0 / 3600.0,
        'elapsed_s': time.time() - t0,
    }
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '.json'))
    print('done', tag, nrows, round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
