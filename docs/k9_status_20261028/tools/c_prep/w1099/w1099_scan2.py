# w1099_scan2.py — SC1001 둘레 FZP 스캔 (W1099_RULE_ADD1 A2, 데이터 뒤 선언; 읽기만)
# 사용: python -B w1099_scan2.py 이름=FZP경로 ...  → out/s2_<이름>.json. 꼴은 w1099_scan.py 와 같음(우리 꼴).
import sys, os, json, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
NET = json.load(open(os.path.join(OUT, 'net_links.json'), encoding='utf-8'))
CONN = np.array(sorted(int(k) for k, v in NET.items() if v['from']), dtype=np.int64)
W = 9000.0; TB = 300.0; NTB = 30; SLOW = 10.0
SERIES = [127, 2, 10481, 30, 38, 39, 10118, 10368, 10695, 129, 10777]
PAIRS = [(2, 127), (129, 127), (127, 30), (127, 38), (127, 39)]


def header_len(path):
    n = 0
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            n += 1
            if line.startswith('$VEHICLE:'):
                return n
    raise RuntimeError('no header')


def r5(a):
    return np.round(np.asarray(a, dtype=float), 5).tolist()


def scan(name, path):
    t0c = time.time()
    df = pd.read_csv(path, sep=';', skiprows=header_len(path), header=None, usecols=[0, 1, 2, 3, 4, 6],
                     names=['t', 'no', 'link', 'lane', 'pos', 'speed'],
                     dtype={'t': np.float64, 'no': np.int64, 'link': np.int64, 'lane': np.int64, 'pos': np.float64, 'speed': np.float64},
                     engine='c', encoding='latin-1')
    t = np.round(df['t'].to_numpy(), 1); no = df['no'].to_numpy(); link = df['link'].to_numpy()
    lane = df['lane'].to_numpy(); pos = df['pos'].to_numpy(); spd = df['speed'].to_numpy()
    del df
    frames = np.unique(t)
    fr = frames[(frames >= 1.0) & (frames <= W + 1e-9)]
    wf = np.zeros_like(fr); d = np.diff(fr); wf[:-1] += d / 2.0; wf[1:] += d / 2.0
    valid = (t >= 1.0) & (t <= W + 1e-9)
    fi = np.searchsorted(fr, t); fi[~valid] = 0
    w = np.where(valid, wf[fi] / 3600.0, 0.0)
    tb = np.minimum((t // TB).astype(np.int64), NTB - 1)
    slow = spd < SLOW
    nfr = len(fr)
    res = {'name': name, 'path': path, 'rows': int(len(t)), 'frames': [float(fr[0]), float(fr[-1]), int(nfr)]}
    # maps for 127 and 30 (50 m x lane x 300 s)
    for L, npb, nln in ((127, 13, 3), (30, 11, 4)):
        m = valid & (link == L)
        pb = np.clip((pos[m] // 50).astype(np.int64), 0, npb - 1); ln = np.clip(lane[m] - 1, 0, nln - 1)
        flat = (pb * nln + ln) * NTB + tb[m]; n = npb * nln * NTB
        res['m%d_occ' % L] = r5(np.bincount(flat, weights=w[m], minlength=n).reshape(npb, nln, NTB))
        res['m%d_slow' % L] = r5(np.bincount(flat, weights=w[m] * slow[m], minlength=n).reshape(npb, nln, NTB))
        res['m%d_spdw' % L] = r5(np.bincount(flat, weights=w[m] * spd[m], minlength=n).reshape(npb, nln, NTB))
    ls = {}
    for L in SERIES:
        m = valid & (link == L)
        ls[str(L)] = {'occ': r5(np.bincount(tb[m], weights=w[m], minlength=NTB)),
                      'slow': r5(np.bincount(tb[m], weights=w[m] * slow[m], minlength=NTB)),
                      'spdw': r5(np.bincount(tb[m], weights=w[m] * spd[m], minlength=NTB))}
    res['links'] = ls
    # main-link transitions
    order = np.lexsort((t, no))
    s_no = no[order]; s_link = link[order]; s_t = t[order]
    chg = np.ones(len(s_no), dtype=bool); chg[1:] = (s_no[1:] != s_no[:-1]) | (s_link[1:] != s_link[:-1])
    g_no = s_no[chg]; g_link = s_link[chg]; g_t0 = s_t[chg]
    mm = ~np.isin(g_link, CONN)
    m_no = g_no[mm]; m_link = g_link[mm]; m_t0 = g_t0[mm]
    keep = np.ones(len(m_no), dtype=bool); keep[1:] = (m_no[1:] != m_no[:-1]) | (m_link[1:] != m_link[:-1])
    m_no = m_no[keep]; m_link = m_link[keep]; m_t0 = m_t0[keep]
    same = np.zeros(len(m_no), dtype=bool); same[:-1] = m_no[1:] == m_no[:-1]
    nl = np.full(len(m_no), -1, dtype=np.int64); nl[:-1] = np.where(same[:-1], m_link[1:], -1)
    nt = np.full(len(m_no), np.nan); nt[:-1] = np.where(same[:-1], m_t0[1:], np.nan)
    fl = {}
    for a, b in PAIRS:
        m = (m_link == a) & (nl == b)
        fl['%d>%d' % (a, b)] = np.bincount(np.minimum((nt[m] // TB).astype(np.int64), NTB - 1), minlength=NTB).astype(int).tolist()
    res['flows'] = fl
    # frame series
    def cnt(mask):
        return np.bincount(fi[mask & valid], minlength=nfr)[:nfr].astype(int).tolist()
    fs = {}
    for ln in (1, 2, 3):
        fs['127_l%d_slow' % ln] = cnt((link == 127) & (lane == ln) & slow)
        fs['127_l%d_n' % ln] = cnt((link == 127) & (lane == ln))
    fs['30_0_100_slow'] = cnt((link == 30) & (pos < 100) & slow)
    fs['30_slow'] = cnt((link == 30) & slow)
    res['frame_series'] = fs
    res['scan_sec'] = round(time.time() - t0c, 1)
    with open(os.path.join(OUT, 's2_' + name + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh)
    print(name, res['rows'], nfr, res['scan_sec'], flush=True)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        nm, p = a.split('=', 1)
        scan(nm, p)
    print('ALL_DONE', flush=True)
