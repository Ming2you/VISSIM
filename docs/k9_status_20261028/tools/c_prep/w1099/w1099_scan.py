# w1099_scan.py — 입력 1099 대기 분해용 FZP 스캔 (W1099_RULE.md, 데이터 뒤 선언; 읽기만)
# 사용: python -B w1099_scan.py 이름=FZP경로 [이름=FZP경로 ...]  → out/<이름>.json
# 꼴: 우리 꼴(프레임 1..9000 s 사다리꼴, 0.1 s 행 빼기). 첫 관측은 파일 첫 행(0.1 s 행 포함).
import sys, os, json, time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
NET = json.load(open(os.path.join(OUT, 'net_links.json'), encoding='utf-8'))
CONN = np.array(sorted(int(k) for k, v in NET.items() if v['from']), dtype=np.int64)

W = 9000.0
TB = 300.0
NTB = 30
SLOW = 10.0
LINK_SERIES = [26, 120, 10771, 124, 10480, 32, 10482, 125, 10479, 129, 10491, 10490, 10777, 10778, 127,
               121, 10646, 69, 10644, 119, 31, 10483, 10775, 10774]
PAIRS = [(26, 125), (26, 129), (26, 120), (124, 26), (124, 125), (119, 124), (31, 124), (32, 120), (32, 129),
         (129, 119), (129, 127), (121, 120), (69, 120)]
FRAME_LINKS = [10491, 10490, 10480, 124, 32, 10482, 127, 10479, 125, 10777]
DWELL_LINKS = [26, 10491, 129, 10490, 10480, 124, 10482, 32, 127]


def header_len(path):
    n = 0
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            n += 1
            if line.startswith('$VEHICLE:'):
                return n
    raise RuntimeError('no $VEHICLE header')


def r4(a):
    return np.round(np.asarray(a, dtype=float), 5).tolist()


def scan(name, path):
    t0c = time.time()
    hl = header_len(path)
    df = pd.read_csv(path, sep=';', skiprows=hl, header=None, usecols=[0, 1, 2, 3, 4, 6],
                     names=['t', 'no', 'link', 'lane', 'pos', 'speed'],
                     dtype={'t': np.float64, 'no': np.int64, 'link': np.int64, 'lane': np.int64,
                            'pos': np.float64, 'speed': np.float64}, engine='c', encoding='latin-1')
    t = np.round(df['t'].to_numpy(), 1)
    no = df['no'].to_numpy()
    link = df['link'].to_numpy()
    lane = df['lane'].to_numpy()
    pos = df['pos'].to_numpy()
    spd = df['speed'].to_numpy()
    del df
    nrows = int(len(t))
    res = {'name': name, 'path': path, 'rows': nrows}

    # ---- frames and weights (ours form) ----
    frames = np.unique(t)
    fr = frames[(frames >= 1.0) & (frames <= W + 1e-9)]
    wf = np.zeros_like(fr)
    d = np.diff(fr)
    wf[:-1] += d / 2.0
    wf[1:] += d / 2.0
    valid = (t >= 1.0) & (t <= W + 1e-9)
    fi = np.searchsorted(fr, t)
    fi[~valid] = 0
    w = np.where(valid, wf[fi] / 3600.0, 0.0)
    tb = np.minimum((t // TB).astype(np.int64), NTB - 1)
    nfr = len(fr)
    res['frames'] = [float(fr[0]), float(fr[-1]), int(nfr)]
    res['frames_lt1'] = [float(x) for x in frames[frames < 1.0]]
    slow = spd < SLOW

    # ---- first observation (file order = time order) ----
    _, fidx = np.unique(no, return_index=True)
    f_t = t[fidx]; f_link = link[fidx]; f_lane = lane[fidx]; f_pos = pos[fidx]; f_spd = spd[fidx]; f_no = no[fidx]
    is99 = f_link == 26
    t1 = f_t[is99 & (f_t <= W + 1e-9)]
    S_bins = np.zeros(NTB)
    for k in range(NTB):
        a = k * TB
        b = min((k + 1) * TB, W)
        S_bins[k] = np.clip(b - np.maximum(a, t1), 0.0, None).sum() / 3600.0
    res['in1099'] = {
        'n_first_le_W': int(len(t1)),
        'S_W': float(((W - t1)).sum() / 3600.0),
        'S_bins': r4(S_bins),
        'n_first_lt1': int((t1 < 1.0).sum()),
    }
    # per-frame new 1099 counts (frames >= 1); t1 < 1 counted separately
    t1f = t1[t1 >= 1.0]
    new_fr = np.bincount(np.searchsorted(fr, t1f), minlength=nfr)[:nfr]
    ftb = np.minimum((fr // TB).astype(np.int64), NTB - 1)
    zero = (new_fr == 0)
    zbin = np.bincount(ftb, weights=zero.astype(float), minlength=NTB)
    # longest zero run per bin (run assigned to bin of its start) and overall
    runs = []
    k = 0
    while k < nfr:
        if zero[k]:
            j = k
            while j < nfr and zero[j]:
                j += 1
            runs.append((float(fr[k]), j - k))
            k = j
        else:
            k += 1
    longest = np.zeros(NTB)
    for st, ln in runs:
        bb = min(int(st // TB), NTB - 1)
        longest[bb] = max(longest[bb], ln)
    runs_sorted = sorted(runs, key=lambda x: -x[1])[:15]
    f99_t = f_t[is99]; f99_tb = np.minimum((f99_t // TB).astype(np.int64), NTB - 1)
    f99_spd = f_spd[is99]; f99_lane = f_lane[is99]; f99_pos = f_pos[is99]
    res['entrance'] = {
        'new_per_frame': new_fr.astype(int).tolist(),
        'n_ins_bin': np.bincount(f99_tb, minlength=NTB).astype(int).tolist(),
        'zero_frames_bin': zbin.astype(int).tolist(),
        'longest_zero_run_frames_bin': longest.astype(int).tolist(),
        'top_zero_runs': runs_sorted,
        'first_speed_sum_bin': r4(np.bincount(f99_tb, weights=f99_spd, minlength=NTB)),
        'first_speed_lt20_bin': np.bincount(f99_tb, weights=(f99_spd < 20).astype(float), minlength=NTB).astype(int).tolist(),
        'first_pos_sum_bin': r4(np.bincount(f99_tb, weights=f99_pos, minlength=NTB)),
        'first_lane_bin': [np.bincount(f99_tb[f99_lane == L], minlength=NTB).astype(int).tolist() for L in (1, 2, 3)],
    }

    # ---- vehicle segments (sorted by vehicle, time) ----
    order = np.lexsort((t, no))
    s_no = no[order]; s_link = link[order]; s_t = t[order]; s_spd = spd[order]; s_lane = lane[order]; s_pos = pos[order]
    chg = np.ones(len(s_no), dtype=bool)
    chg[1:] = (s_no[1:] != s_no[:-1]) | (s_link[1:] != s_link[:-1])
    st_idx = np.flatnonzero(chg)
    en_idx = np.append(st_idx[1:] - 1, len(s_no) - 1)
    g_no = s_no[st_idx]; g_link = s_link[st_idx]; g_t0 = s_t[st_idx]; g_t1 = s_t[en_idx]
    g_spd0 = s_spd[st_idx]; g_lane0 = s_lane[st_idx]; g_pos0 = s_pos[st_idx]
    del order, s_no, s_link, s_t, s_spd, s_lane, s_pos
    # dwell (row-based) on selected links, by entry bin
    g_tb = np.minimum((g_t0 // TB).astype(np.int64), NTB - 1)
    dwell = {}
    for L in DWELL_LINKS:
        m = g_link == L
        dwell[str(L)] = {'n': np.bincount(g_tb[m], minlength=NTB).astype(int).tolist(),
                         'sum_s': r4(np.bincount(g_tb[m], weights=(g_t1[m] - g_t0[m]), minlength=NTB))}
    res['dwell_by_entry_bin'] = dwell
    # main-link sequence (connectors removed, re-compressed)
    mm = ~np.isin(g_link, CONN)
    m_no = g_no[mm]; m_link = g_link[mm]; m_t0 = g_t0[mm]; m_t1 = g_t1[mm]; m_spd0 = g_spd0[mm]
    keep = np.ones(len(m_no), dtype=bool)
    keep[1:] = (m_no[1:] != m_no[:-1]) | (m_link[1:] != m_link[:-1])
    # when re-compressing, the end time of a merged segment is the last piece's end; keep first piece start
    grp = np.cumsum(keep) - 1
    m_t1c = np.zeros(keep.sum()); np.maximum.at(m_t1c, grp, m_t1)
    m_no = m_no[keep]; m_link = m_link[keep]; m_t0 = m_t0[keep]; m_spd0 = m_spd0[keep]; m_t1 = m_t1c
    same_next = np.zeros(len(m_no), dtype=bool)
    same_next[:-1] = m_no[1:] == m_no[:-1]
    nxt_link = np.full(len(m_no), -1, dtype=np.int64)
    nxt_link[:-1] = np.where(same_next[:-1], m_link[1:], -1)
    nxt_t0 = np.full(len(m_no), np.nan)
    nxt_t0[:-1] = np.where(same_next[:-1], m_t0[1:], np.nan)
    prv_link = np.full(len(m_no), -1, dtype=np.int64)
    prv_link[1:] = np.where(m_no[1:] == m_no[:-1], m_link[:-1], -1)
    flows = {}
    for a, b in PAIRS:
        m = (m_link == a) & (nxt_link == b)
        tt = nxt_t0[m]
        flows['%d>%d' % (a, b)] = np.bincount(np.minimum((tt // TB).astype(np.int64), NTB - 1), minlength=NTB).astype(int).tolist()
    res['flows'] = flows
    # classes of vehicles that use link 26
    maxno = int(no.max()) + 1
    first_link_by_no = np.full(maxno, -1, dtype=np.int64)
    first_link_by_no[f_no] = f_link
    m26 = m_link == 26
    v26 = m_no[m26]
    ex = nxt_link[m26]
    exit_code = np.where(ex == 125, 0, np.where(ex == 129, 1, np.where(ex == 120, 2, 3)))
    pv = prv_link[m26]
    org_code = np.where(first_link_by_no[v26] == 26, 0, np.where(pv == 124, 1, 2))
    code_by_no = np.full(maxno, -1, dtype=np.int64)
    code_by_no[v26] = exit_code * 3 + org_code
    res['class_counts'] = np.bincount(exit_code * 3 + org_code, minlength=12).astype(int).tolist()
    res['class_names'] = [e + '|' + o for e in ('x125', 'x129', 'thru', 'none') for o in ('1099', 'ramp', 'other')]
    # 1099 vehicles: link-26 dwell by exit class and entry bin
    t0_26 = m_t0[m26]; t1_26 = m_t1[m26]
    e_tb = np.minimum((t0_26 // TB).astype(np.int64), NTB - 1)
    d26 = {}
    for e in range(4):
        m = (org_code == 0) & (exit_code == e)
        d26[('x125', 'x129', 'thru', 'none')[e]] = {
            'n': np.bincount(e_tb[m], minlength=NTB).astype(int).tolist(),
            'sum_s': r4(np.bincount(e_tb[m], weights=(t1_26[m] - t0_26[m]), minlength=NTB))}
    res['dwell26_1099_by_exit'] = d26
    # ramp vehicles (124 -> 26): first speed on 26, exit class, by entry bin
    mr = org_code == 1
    res['ramp_on26'] = {
        'n': np.bincount(e_tb[mr], minlength=NTB).astype(int).tolist(),
        'first_speed_sum': r4(np.bincount(e_tb[mr], weights=m_spd0[m26][mr], minlength=NTB)),
        'exit_counts': [int(((exit_code == e) & mr).sum()) for e in range(4)],
    }

    # ---- link 26 maps ----
    L26 = valid & (link == 26)
    pb = np.clip((pos[L26] // 100).astype(np.int64), 0, 38)
    ln = np.clip(lane[L26] - 1, 0, 2)
    tb26 = tb[L26]; w26 = w[L26]; sp26 = spd[L26]; sl26 = slow[L26]
    flat = (pb * 3 + ln) * NTB + tb26
    n = 39 * 3 * NTB
    res['l26_occ'] = r4(np.bincount(flat, weights=w26, minlength=n).reshape(39, 3, NTB))
    res['l26_spdw'] = r4(np.bincount(flat, weights=w26 * sp26, minlength=n).reshape(39, 3, NTB))
    res['l26_slow'] = r4(np.bincount(flat, weights=w26 * sl26, minlength=n).reshape(39, 3, NTB))
    cc = code_by_no[no[L26]]
    cc = np.where(cc < 0, 11, cc)  # vehicles not classified (should be none) -> none|other
    res['l26_cls_lane_time'] = r4(np.bincount((cc * 3 + ln) * NTB + tb26, weights=w26, minlength=12 * 3 * NTB).reshape(12, 3, NTB))
    res['l26_cls_pos_lane'] = r4(np.bincount((cc * 39 + pb) * 3 + ln, weights=w26, minlength=12 * 39 * 3).reshape(12, 39, 3))
    res['l26_unclassified_rows'] = int((code_by_no[no[L26]] < 0).sum())

    # ---- link 120 and 129 maps ----
    L120 = valid & (link == 120)
    pb = np.clip((pos[L120] // 250).astype(np.int64), 0, 27); ln = np.clip(lane[L120] - 1, 0, 3)
    flat = (pb * 4 + ln) * NTB + tb[L120]; n = 28 * 4 * NTB
    res['l120_occ'] = r4(np.bincount(flat, weights=w[L120], minlength=n).reshape(28, 4, NTB))
    res['l120_spdw'] = r4(np.bincount(flat, weights=w[L120] * spd[L120], minlength=n).reshape(28, 4, NTB))
    res['l120_slow'] = r4(np.bincount(flat, weights=w[L120] * slow[L120], minlength=n).reshape(28, 4, NTB))
    L129 = valid & (link == 129)
    pb = np.clip((pos[L129] // 50).astype(np.int64), 0, 6); ln = np.clip(lane[L129] - 1, 0, 2)
    flat = (pb * 3 + ln) * NTB + tb[L129]; n = 7 * 3 * NTB
    res['l129_occ'] = r4(np.bincount(flat, weights=w[L129], minlength=n).reshape(7, 3, NTB))
    res['l129_spdw'] = r4(np.bincount(flat, weights=w[L129] * spd[L129], minlength=n).reshape(7, 3, NTB))
    res['l129_slow'] = r4(np.bincount(flat, weights=w[L129] * slow[L129], minlength=n).reshape(7, 3, NTB))

    # ---- link series ----
    ls = {}
    for L in LINK_SERIES:
        m = valid & (link == L)
        ls[str(L)] = {'occ': r4(np.bincount(tb[m], weights=w[m], minlength=NTB)),
                      'spdw': r4(np.bincount(tb[m], weights=w[m] * spd[m], minlength=NTB)),
                      'slow': r4(np.bincount(tb[m], weights=w[m] * slow[m], minlength=NTB)),
                      'occ_lane': r4(np.bincount(np.clip(lane[m], 0, 5), weights=w[m], minlength=6)),
                      'total': float(w[m].sum())}
    res['links'] = ls

    # ---- per-frame series ----
    fs = {'new1099': new_fr.astype(int).tolist()}
    def cnt(mask):
        return np.bincount(fi[mask & valid], minlength=nfr)[:nfr].astype(int).tolist()
    is26 = link == 26
    fs['l26_entr_n'] = cnt(is26 & (pos < 150))
    fs['l26_entr_slow'] = cnt(is26 & (pos < 150) & slow)
    for k in range(8):
        lo = 500.0 * k; hi = 500.0 * (k + 1) if k < 7 else 1e9
        fs['l26_l1_slow_%d' % k] = cnt(is26 & (lane == 1) & (pos >= lo) & (pos < hi) & slow)
    fs['l26_l1_n'] = cnt(is26 & (lane == 1))
    fs['l26_l23_slow'] = cnt(is26 & (lane >= 2) & slow)
    is129 = link == 129
    fs['l129_l1_slow150'] = cnt(is129 & (lane == 1) & (pos >= 150) & slow)
    fs['l129_slow'] = cnt(is129 & slow)
    fs['l129_n'] = cnt(is129)
    for L in FRAME_LINKS:
        fs['%d_n' % L] = cnt(link == L)
        fs['%d_slow' % L] = cnt((link == L) & slow)
    fs['l120_0_500_slow'] = cnt((link == 120) & (pos < 500) & slow)
    fs['l120_0_500_n'] = cnt((link == 120) & (pos < 500))
    res['frame_series'] = fs
    res['frame_times'] = r4(fr)
    res['scan_sec'] = round(time.time() - t0c, 1)
    with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(res, fh)
    print(name, nrows, nfr, res['scan_sec'], flush=True)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        nm, p = a.split('=', 1)
        scan(nm, p)
    print('ALL_DONE', flush=True)
