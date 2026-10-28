# -*- coding: utf-8 -*-
"""O2: FW_E plant-cell counts per 5 s FZP frame (read-only). vsl_v3c3 o1o2, 2026-10-27 KST.

Usage: python -B o2_fzp_cells.py <tag> <fzp_path> <out_dir> <t_lo> <t_hi>
For every FZP frame time t with t_lo <= t <= t_hi: per FW_E plant cell (31 cells, bounds = vsl_v3c3/tools/vsl_cell_scan.py
CELL_B = cumulative geom.lengths_km of the plant probe; chain = 7 FW_E mainline links, offsets = rmcause/phys/fwe_scan.py)
N = vehicles on the chain inside the cell, SV = sum of their speeds (km/h). Rows with t < 1.0 s skipped (runner 0.1 s frame).
Output <out_dir>/<tag>.json: {frames: [t...], N: [[...31]...], SV: [[...31]...]} + sha of the whole FZP.
Edie (per window W of frames, cell length L km, frame step 5 s): stock = mean N; speed = sum SV / sum N;
flow (veh/h, lane sum) = sum SV * 5 / (L * W_sec).
"""
import hashlib, json, os, sys, time

CHAIN = [(74, 0.0, 4), (10699, 2701.577, 4), (2, 2734.527, 4), (10613, 6841.743, 3),
         (119, 6847.981, 3), (10702, 7431.364, 3), (24, 7438.047, 3)]
OFF = {l: o for l, o, _ in CHAIN}
CELL_B = [0.0, 526.2879, 1052.5758, 1578.8638, 2105.1517, 2631.4396, 3157.7275, 3684.0155, 4210.3034, 4286.333,
          4542.5389, 4736.5913, 4894.3955, 5078.6373, 5262.8792, 5789.1672, 6315.4551, 6490.8844, 6666.3137, 6841.743,
          7041.7112, 7241.6793, 7334.5286, 7498.7905, 7663.0524, 7827.3143, 8320.0999, 8812.8855, 9305.6711, 9798.4567,
          10291.2424, 10784.028]
NCELL = len(CELL_B) - 1


def cell_of(x):
    lo, hi = 0, NCELL - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if CELL_B[mid] <= x:
            lo = mid
        else:
            hi = mid - 1
    return lo


def main():
    tag, path, out_dir, t_lo, t_hi = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
    t0 = time.time()
    frames, N, SV = [], [], []
    idx = {}
    h = hashlib.sha256()
    col = None
    nrows = 0
    cur_t = None
    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            if col is None:
                if raw.startswith(b'$VEHICLE:'):
                    names = raw[len(b'$VEHICLE:'):].strip().decode('ascii').split(';')
                    col = {n: i for i, n in enumerate(names)}
                    ci = (col['SIMSEC'], col['LANE\\LINK\\NO'], col['POS'], col['SPEED'])
                continue
            c0 = raw[:1]
            if not (b'0' <= c0 <= b'9'):
                continue
            p = raw.split(b';')
            t = float(p[ci[0]])
            if t < 1.0 or t < t_lo or t > t_hi:
                continue
            if t != cur_t:
                cur_t = t
                if t not in idx:
                    idx[t] = len(frames)
                    frames.append(t)
                    N.append([0] * NCELL)
                    SV.append([0.0] * NCELL)
            link = int(p[ci[1]])
            if link not in OFF:
                continue
            x = OFF[link] + float(p[ci[2]])
            k = idx[t]
            c = cell_of(min(x, CELL_B[-1] - 1e-9))
            N[k][c] += 1
            SV[k][c] += float(p[ci[3]])
            nrows += 1
    out = {'tag': tag, 'fzp': path, 'fzp_sha256': h.hexdigest(), 'rows_chain': nrows, 't_lo': t_lo, 't_hi': t_hi,
           'cell_bounds_m': CELL_B, 'frames': frames, 'N': N, 'SV': [[round(v, 3) for v in r] for r in SV],
           'elapsed_s': round(time.time() - t0, 1)}
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '.json'))
    print('done', tag, nrows, len(frames), round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
