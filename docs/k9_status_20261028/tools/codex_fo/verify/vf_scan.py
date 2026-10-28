# vf_scan.py - VERIFY_FO new FZP scanner (2026-10-28 KST). Written for this verification only.
# No code from the FO author tools (vhr_fo, omega_fo, rawcheck_fo, fwe_*) or from VERIFY_B (vb_*) is reused. Read only.
# usage: python -B vf_scan.py <label> <fzp> <inpx_for_chain_geometry> <out_json>
# outputs (veh*h unless noted):
#   links_ours   : per link, frames 1 s <= t <= 9000 s, trapezoid on the frame times (0.1 s frame dropped)
#   links_codex  : per link, empty network at t=0, all frames t <= 8100 (0.1 s frame kept), trapezoid on the
#                  frame times, last frame stock held until 8100 s
#   links_bin900 : per link, vehicle-frame counts (frames >= 1 s) in ten 900 s windows
#   first_seen   : first row of each vehicle number (time, link); S(W) = sum_{t1<=W} (W - t1)/3600 split
#                  link 74 / link 26 / other, for W = 9000 and 8100
#   fwe_cells    : FW_E mainline 7 links, chain position (from the inpx geometry) in 100 m bins x 900 s windows,
#                  vehicle-frame counts (frames >= 1 s)
import sys, os, json, time, math, hashlib
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET

CHAIN = ['74', '10699', '2', '10613', '119', '10702', '24']


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            blk = fh.read(1 << 22)
            if not blk:
                break
            h.update(blk)
    return h.hexdigest()


def chain_offsets(inpx):
    root = ET.parse(inpx).getroot()
    links = {e.get('no'): e for e in root.find('links').findall('link')}

    def pts(no):
        g = links[no].find('geometry').find('linkPolyPts')
        return [(float(p.get('x')), float(p.get('y'))) for p in g]

    def plen(P):
        return sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1))

    def point_at(P, s):
        acc = 0.0
        for i in range(len(P) - 1):
            d = math.dist(P[i], P[i + 1])
            if acc + d >= s or i == len(P) - 2:
                f = 0.0 if d == 0 else min(max((s - acc) / d, 0.0), 1.0)
                return (P[i][0] + f * (P[i + 1][0] - P[i][0]), P[i][1] + f * (P[i + 1][1] - P[i][1]))
            acc += d
        return P[-1]

    off = {CHAIN[0]: 0.0}
    conn = {}
    for i in range(1, len(CHAIN), 2):
        prev, c, nxt = CHAIN[i - 1], CHAIN[i], CHAIN[i + 1]
        e = links[c]
        fl = e.find('fromLinkEndPt')
        tl = e.find('toLinkEndPt')
        if fl.get('lane').split()[0] != prev or tl.get('lane').split()[0] != nxt:
            raise RuntimeError('chain connector mismatch ' + c)
        fp = float(fl.get('pos'))
        tp = float(tl.get('pos'))
        P = [point_at(pts(prev), fp)] + pts(c) + [point_at(pts(nxt), tp)]
        clen = plen(P)
        off[c] = off[prev] + fp
        off[nxt] = off[c] + clen - tp
        conn[c] = {'from_pos': fp, 'to_pos': tp, 'len_geom': clen, 'len_poly_only': plen(pts(c))}
    lens = {no: plen(pts(no)) for no in CHAIN}
    # second convention: cumulative full polyline lengths (connector from/to positions ignored)
    cum = {}
    acc = 0.0
    for no in CHAIN:
        cum[no] = acc
        acc += lens[no]
    return off, conn, lens, cum


def trap_weights(frames10, form):
    t_all = frames10 / 10.0
    if form == 'ours':
        sel = frames10[(frames10 >= 10) & (frames10 <= 90000)]
        t = sel / 10.0
        w = np.empty(len(t))
        w[0] = (t[1] - t[0]) / 2.0
        w[-1] = (t[-1] - t[-2]) / 2.0
        w[1:-1] = (t[2:] - t[:-2]) / 2.0
        return sel, w
    if form == 'codex':
        sel = frames10[frames10 <= 81000]
        t = sel / 10.0
        w = np.empty(len(t))
        w[0] = (t[1] - 0.0) / 2.0
        w[1:-1] = (t[2:] - t[:-2]) / 2.0
        w[-1] = (t[-1] - t[-2]) / 2.0 + (8100.0 - t[-1])
        return sel, w
    raise ValueError(form)


def main():
    label, fzp, inpx, out_json = sys.argv[1:5]
    t0 = time.time()
    hl = 0
    hdr = None
    with open(fzp, 'rb') as fh:
        for line in fh:
            hl += 1
            if line.startswith(b'$VEHICLE:'):
                hdr = line.decode('latin-1').strip()
                break
    if hdr is None:
        raise RuntimeError('no $VEHICLE line')
    cols = hdr.split(':', 1)[1].split(';')
    if cols[0] != 'SIMSEC' or cols[1] != 'NO' or cols[2] != 'LANE\\LINK\\NO' or cols[4] != 'POS':
        raise RuntimeError('unexpected columns ' + repr(cols[:5]))
    off, conn, lens, cum = chain_offsets(inpx)
    chain_ids = np.array([int(x) for x in CHAIN], dtype=np.int64)
    cnt_parts, first_parts = [], []
    cell_parts = {'geom': [], 'cum': []}
    nrows = 0
    last_t10 = -1
    sorted_ok = True
    reader = pd.read_csv(fzp, sep=';', skiprows=hl, header=None, usecols=[0, 1, 2, 4], chunksize=4000000,
                         engine='c', encoding='latin-1',
                         dtype={0: np.float64, 1: np.int64, 2: np.int64, 4: np.float64})
    for ch in reader:
        tt = ch[0].to_numpy()
        no = ch[1].to_numpy()
        lk = ch[2].to_numpy()
        ps = ch[4].to_numpy()
        nrows += len(tt)
        t10 = np.rint(tt * 10.0).astype(np.int64)
        if len(t10):
            if t10[0] < last_t10 or np.any(np.diff(t10) < 0):
                sorted_ok = False
            last_t10 = int(t10[-1])
        cnt_parts.append(pd.DataFrame({'f': t10, 'l': lk}).groupby(['f', 'l']).size())
        first_parts.append(pd.DataFrame({'no': no, 'f': t10, 'l': lk}).drop_duplicates('no', keep='first'))
        m = np.isin(lk, chain_ids) & (t10 >= 10)
        if m.any():
            lm = lk[m]
            pm = ps[m]
            w = t10[m] // 9000
            for conv, table in (('geom', off), ('cum', cum)):
                s = np.full(len(lm), np.nan)
                for k, v in table.items():
                    mk = lm == int(k)
                    s[mk] = v + pm[mk]
                b = np.floor(s / 100.0).astype(np.int64)
                cell_parts[conv].append(pd.DataFrame({'w': w, 'b': b}).groupby(['w', 'b']).size())
    cnt = pd.concat(cnt_parts).groupby(level=[0, 1]).sum()
    f_idx = cnt.index.get_level_values(0).to_numpy()
    l_idx = cnt.index.get_level_values(1).to_numpy()
    c_val = cnt.to_numpy().astype(np.float64)
    frames = np.unique(f_idx)
    res = {'label': label, 'fzp': fzp, 'fzp_bytes': os.path.getsize(fzp), 'inpx_chain': inpx,
           'rows': int(nrows), 'time_sorted': bool(sorted_ok), 'n_frames': int(len(frames)),
           'frames_lt1': [int(x) / 10.0 for x in frames[frames < 10]],
           'first_frame': int(frames[0]) / 10.0, 'last_frame': int(frames[-1]) / 10.0}
    fg = frames[frames >= 10] / 10.0
    res['frame_gap_min_max'] = [float(np.diff(fg).min()), float(np.diff(fg).max())]
    res['rows_lt1'] = int(c_val[f_idx < 10].sum())
    for form in ('ours', 'codex'):
        sel, w = trap_weights(frames, form)
        wv = np.zeros(int(frames.max()) + 1)
        wv[sel] = w
        rw = wv[f_idx] * c_val
        g = pd.Series(rw).groupby(l_idx).sum() / 3600.0
        res['links_' + form] = {str(int(k)): float(v) for k, v in g.items() if v != 0.0}
        res['frames_' + form] = [int(sel[0]) / 10.0, int(sel[-1]) / 10.0, int(len(sel))]
    mb = f_idx >= 10
    wb = f_idx[mb] // 9000
    gb = pd.Series(c_val[mb]).groupby([l_idx[mb], wb]).sum()
    bins = {}
    for (lnk, win), v in gb.items():
        bins.setdefault(str(int(lnk)), [0.0] * 10)
        if 0 <= int(win) < 10:
            bins[str(int(lnk))][int(win)] += float(v)
    res['links_bin900'] = bins
    fs = pd.concat(first_parts).drop_duplicates('no', keep='first')
    t1 = fs['f'].to_numpy() / 10.0
    l1 = fs['l'].to_numpy()
    res['n_vehicles'] = int(len(fs))
    res['first_seen'] = {}
    for W in (9000.0, 8100.0):
        inw = t1 <= W + 1e-9
        d = {'n_all': int(inw.sum()), 'S_all': float((W - t1[inw]).sum() / 3600.0)}
        for name, mk in (('in1098', l1 == 74), ('in1099', l1 == 26), ('urban', (l1 != 74) & (l1 != 26))):
            mm = inw & mk
            d['n_' + name] = int(mm.sum())
            d['S_' + name] = float((W - t1[mm]).sum() / 3600.0)
        res['first_seen'][str(int(W))] = d
    for conv in ('geom', 'cum'):
        if cell_parts[conv]:
            cc = pd.concat(cell_parts[conv]).groupby(level=[0, 1]).sum()
            res['fwe_cells_' + conv] = [[int(a), int(b), int(v)] for (a, b), v in cc.items()]
        else:
            res['fwe_cells_' + conv] = []
    res['chain_offsets'] = off
    res['chain_offsets_cum'] = cum
    res['chain_connectors'] = conn
    res['chain_link_lengths'] = lens
    res['scan_sec'] = round(time.time() - t0, 1)
    res['fzp_sha256'] = sha256_file(fzp)
    res['total_sec'] = round(time.time() - t0, 1)
    tmp = out_json + '.tmp' + str(os.getpid())
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(res, fh)
    os.replace(tmp, out_json)
    print('VF_SCAN_DONE', label, nrows, len(frames), res['total_sec'], flush=True)


if __name__ == '__main__':
    main()
