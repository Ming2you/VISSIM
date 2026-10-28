# -*- coding: utf-8 -*-
"""FW_E plant-cell and VSL-zone scan of one VISSIM FZP (read-only). 2026-10-27 KST, vsl_v3c3 (PRE_VSL.md section 7).

Usage: python -B vsl_cell_scan.py <tag> <fzp_path> <out_dir>

Writes <out_dir>/<tag>.json with, for the FW_E mainline chain (7 links, chain offsets = rmcause/phys/fwe_scan.py):
- cells: 31 plant cells (boundaries = cumulative geom.lengths_km of the plant probe, SP/c_port/vsl/out/v3_cx_T004500.json,
  equal to the v3c3 geometry per codex_handoff/R_NET.md:152) x 60 s windows x lane 1..4:
  N (vehicle-frames), SV (sum speed km/h), SD (sum desired speed km/h), NC (frames with desired speed 89..93 = the
  written distribution 91 = 90..92 km/h), SVC (sum speed of those frames)
- bins: 100 m bins on chain 6,000-8,600 m x 60 s x lane, same five sums
- zone (VSL zone = DSD 63-66 sign 6,733.2 m to next downstream DSD 67-69 at 8,090.8 m), per 450 s window:
  desired-speed histogram of vehicle-frames {lt89, 89_93, 93_98, 98_141, ge141}; realised-speed histogram of frames
  with desired 89..93 {0_60, 60_80, 80_88, 88_95, 95_100, ge100} and of the other frames;
  per vehicle (first frame of the vehicle inside the zone): count, count with desired 89..93, first-zone-link;
  zone_sums [N desired 89..93, sum speed of those, N other, sum speed of others]
- rows with t < 1.0 s are skipped (runner 0.1 s frame), like fwe_scan.py.
Frames are 5 s: veh-h = N*5/3600. Edie flow over a cell and window = SV*5/3600 / (L_km * T_h) (lane sum).
Reads only the FZP. Writes only the out file.
"""
import hashlib, json, math, os, sys, time

CHAIN = [(74, 0.0, 4), (10699, 2701.577, 4), (2, 2734.527, 4), (10613, 6841.743, 3),
         (119, 6847.981, 3), (10702, 7431.364, 3), (24, 7438.047, 3)]
OFF = {l: o for l, o, _ in CHAIN}
CELL_B = [0.0, 526.2879, 1052.5758, 1578.8638, 2105.1517, 2631.4396, 3157.7275, 3684.0155, 4210.3034, 4286.333,
          4542.5389, 4736.5913, 4894.3955, 5078.6373, 5262.8792, 5789.1672, 6315.4551, 6490.8844, 6666.3137, 6841.743,
          7041.7112, 7241.6793, 7334.5286, 7498.7905, 7663.0524, 7827.3143, 8320.0999, 8812.8855, 9305.6711, 9798.4567,
          10291.2424, 10784.028]
NCELL = len(CELL_B) - 1
SIGN_M, NEXT_DSD_M = 6733.2, 8090.8
WIN = 60.0
NW = 151
BX0, BX1, BM = 6000.0, 8600.0, 100.0
NB = int((BX1 - BX0) / BM)
ZWIN = 450.0
NZW = 21
DES_LO, DES_HI = 89.0, 93.0
DES_BINS = [('lt89', -1e9, 89.0), ('89_93', 89.0, 93.0), ('93_98', 93.0, 98.0), ('98_141', 98.0, 141.0), ('ge141', 141.0, 1e9)]
SPD_BINS = [('0_60', -1e9, 60.0), ('60_80', 60.0, 80.0), ('80_88', 80.0, 88.0), ('88_95', 88.0, 95.0), ('95_100', 95.0, 100.0), ('ge100', 100.0, 1e9)]


def cell_of(x):
    lo, hi = 0, NCELL - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if CELL_B[mid] <= x:
            lo = mid
        else:
            hi = mid - 1
    return lo


def hb(bins, v):
    for name, a, b in bins:
        if a <= v < b:
            return name
    return bins[-1][0]


def zeros5():
    return [0, 0.0, 0.0, 0, 0.0]


def main():
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    cells = [[[zeros5() for _ in range(4)] for _ in range(NCELL)] for _ in range(NW)]
    bins = [[[zeros5() for _ in range(4)] for _ in range(NB)] for _ in range(NW)]
    zdes = [{k: 0 for k, _, _ in DES_BINS} for _ in range(NZW)]
    zspd_c = [{k: 0 for k, _, _ in SPD_BINS} for _ in range(NZW)]
    zspd_o = [{k: 0 for k, _, _ in SPD_BINS} for _ in range(NZW)]
    zveh = [[0, 0] for _ in range(NZW)]
    zsum = [[0, 0.0, 0, 0.0] for _ in range(NZW)]
    zveh_link = [{} for _ in range(NZW)]
    seen_zone = set()
    frames = [0] * NW
    h = hashlib.sha256()
    col = None
    nrows = 0
    skipped = 0
    cur_t = None
    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            if col is None:
                if raw.startswith(b'$VEHICLE:'):
                    names = raw[len(b'$VEHICLE:'):].strip().decode('ascii').split(';')
                    col = {n: i for i, n in enumerate(names)}
                    ci = (col['SIMSEC'], col['NO'], col['LANE\\LINK\\NO'], col['LANE\\INDEX'], col['POS'], col['SPEED'], col['DESSPEED'])
                continue
            c0 = raw[:1]
            if not (b'0' <= c0 <= b'9'):
                continue
            p = raw.split(b';')
            t = float(p[ci[0]])
            if t < 1.0:
                skipped += 1
                continue
            link = int(p[ci[2]])
            if link not in OFF:
                if cur_t != t:
                    cur_t = t
                    w = int(t // WIN)
                    if w < NW:
                        frames[w] += 1
                continue
            if cur_t != t:
                cur_t = t
                w = int(t // WIN)
                if w < NW:
                    frames[w] += 1
            w = int(t // WIN)
            if w >= NW:
                continue
            nrows += 1
            lane = int(p[ci[3]])
            x = OFF[link] + float(p[ci[4]])
            v = float(p[ci[5]])
            d = float(p[ci[6]])
            cmd = DES_LO <= d < DES_HI
            li = min(max(lane, 1), 4) - 1
            a = cells[w][cell_of(min(x, CELL_B[-1] - 1e-9))][li]
            a[0] += 1; a[1] += v; a[2] += d
            if cmd:
                a[3] += 1; a[4] += v
            if BX0 <= x < BX1:
                b = bins[w][int((x - BX0) // BM)][li]
                b[0] += 1; b[1] += v; b[2] += d
                if cmd:
                    b[3] += 1; b[4] += v
            if SIGN_M <= x < NEXT_DSD_M:
                zw = min(int(t // ZWIN), NZW - 1)
                zdes[zw][hb(DES_BINS, d)] += 1
                (zspd_c if cmd else zspd_o)[zw][hb(SPD_BINS, v)] += 1
                zs = zsum[zw]
                if cmd:
                    zs[0] += 1; zs[1] += v
                else:
                    zs[2] += 1; zs[3] += v
                veh = int(p[ci[1]])
                if veh not in seen_zone:
                    seen_zone.add(veh)
                    zveh[zw][0] += 1
                    if cmd:
                        zveh[zw][1] += 1
                    zveh_link[zw][str(link)] = zveh_link[zw].get(str(link), 0) + 1
    out = {'tag': tag, 'fzp': path, 'fzp_sha256': h.hexdigest(), 'columns': col, 'rows_chain': nrows, 'rows_t_lt_1_skipped': skipped,
           'cell_bounds_m': CELL_B, 'win_s': WIN, 'nw': NW, 'bins_x0': BX0, 'bins_x1': BX1, 'bin_m': BM, 'zone_m': [SIGN_M, NEXT_DSD_M],
           'zone_win_s': ZWIN, 'des_cmd_range': [DES_LO, DES_HI], 'frames': frames,
           'cells': cells, 'bins': bins, 'zone_des_hist': zdes, 'zone_speed_hist_cmd': zspd_c, 'zone_speed_hist_other': zspd_o,
           'zone_sums': zsum, 'zone_sums_fields': '[N desired 89..93, sum speed of those, N other, sum speed of others]',
           'zone_vehicles_first_frame': zveh, 'zone_vehicles_first_link': zveh_link, 'elapsed_s': round(time.time() - t0, 1),
           'fields': 'per [win][cell or bin][lane0..3] = [N, sum speed, sum desired speed, N desired 89..93, sum speed of those]'}
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '.json'))
    print('done', tag, nrows, round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
