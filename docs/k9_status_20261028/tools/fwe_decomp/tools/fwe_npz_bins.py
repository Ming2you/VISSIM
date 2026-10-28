# -*- coding: utf-8 -*-
"""fwe_npz_bins.py - D-K9-106 (PRE_FWE §7.2, §8.2): omega npz cache -> "bin form" link x 150 s vehicle-frames.

Bin form (PRE §7.2, = linkbin_scan.py:1-14 and fwe_scan.py:92-105): only frames with t >= 1.0 s; bin = int(t // 150);
bins 0..59 (t < 9000 s); vf[link][bin] = sum of that link's vehicle count over the frames in the bin;
veh*h = vf * 5 / 3600 (rectangle). The npz (omega701_recount.py scan_fzp) holds t (frame time), M (frame x link
counts, every data row of the frame incl. the 0.1 s frame), links.

Module use: bins_from_npz(path) -> {'vf': {link_str: [int]*60}, 'frames': [int]*60, ...}
            compare_vf(a_vf, b_vf) -> list of (link, bin, a, b) differences (missing link = zeros)
CLI (S-3 check only): python -B fwe_npz_bins.py s3 <lnc_npz> <lb_nc_s29.json> <out_json>
Reads only the given files. Writes only <out_json>.
"""
import json
import sys

import numpy as np

BIN_S = 150.0
NB = 60
T_MIN = 1.0


def bins_from_npz(path, bin_s=BIN_S, nb=NB, t_min=T_MIN):
    c = np.load(path)
    t = c['t']
    M = c['M']
    links = c['links']
    sel = t >= t_min
    b = np.floor(t / bin_s).astype(np.int64)
    sel &= b < nb
    vf = np.zeros((nb, M.shape[1]), dtype=np.int64)
    np.add.at(vf, b[sel], M[sel].astype(np.int64))
    frames = np.bincount(b[sel], minlength=nb)[:nb]
    out = {'vf': {}, 'frames': [int(x) for x in frames], 'bin_s': bin_s, 'nb': nb, 't_min': t_min,
           'first_t_used': float(t[sel][0]) if sel.any() else None, 'last_t_used': float(t[sel][-1]) if sel.any() else None}
    for j, lk in enumerate(links.tolist()):
        col = vf[:, j]
        if col.any():
            out['vf'][str(int(lk))] = [int(x) for x in col]
    return out


def compare_vf(a, b, nb=NB):
    diffs = []
    for lk in sorted(set(a) | set(b), key=lambda s: int(s)):
        x = a.get(lk, [0] * nb)
        y = b.get(lk, [0] * nb)
        for i in range(nb):
            xi = x[i] if i < len(x) else 0
            yi = y[i] if i < len(y) else 0
            if xi != yi:
                diffs.append((lk, i, xi, yi))
    return diffs


def main():
    if len(sys.argv) != 5 or sys.argv[1] != 's3':
        raise SystemExit(__doc__)
    npz, lbp, outp = sys.argv[2], sys.argv[3], sys.argv[4]
    nb = bins_from_npz(npz)
    lb = json.load(open(lbp, encoding='utf-8'))
    d = compare_vf(nb['vf'], lb['vf'])
    fr = [i for i in range(NB) if nb['frames'][i] != lb['frames'][i]]
    res = {'npz': npz, 'linkbin': lbp, 'links_npz': len(nb['vf']), 'links_lb': len(lb['vf']),
           'cells_compared': len(set(nb['vf']) | set(lb['vf'])) * NB, 'n_diff_cells': len(d), 'first_diffs': d[:20],
           'frame_count_diff_bins': fr, 'pass': (not d) and (not fr)}
    json.dump(res, open(outp, 'w', encoding='utf-8'), indent=1)
    print(json.dumps({k: res[k] for k in ('links_npz', 'links_lb', 'cells_compared', 'n_diff_cells', 'pass')}))


if __name__ == '__main__':
    main()
