# fd_series.py — FACTS_DATA: 사슬(SC1001 SG2 → 127 → 129 → 10491 → 26 차로1 끝 → 입구 1099) 300 s 계열
# 읽기만. 새 FZP 스캔 없음. 입력 = 이미 있는 스캔 출력(w1099/out/*.json, sha 고정) + readback CSV + .err 남은 수.
# 사용: python -B fd_series.py  → ../out/fd_series.json
import os, sys, json, csv, glob, re, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.dirname(HERE)
OUTD = os.path.join(GUARD, 'out')
SP = os.path.normpath(os.path.join(GUARD, '..', '..', '..'))  # .../scratchpad/k8
W = os.path.join(SP, 'c_port', 'w1099', 'out')

RUNS = {}
for s in (31, 41, 43):
    RUNS['nc%d' % s] = {'arm': 'NC3', 'seed': s, 'dir': 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc' % s}
    RUNS['b%d' % s] = {'arm': 'B', 'seed': s, 'dir': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d' % s,
                       'rb': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc/decisions_sdmpc31_sdmpc9000_s%d/signal_readback.csv' % (s, s)}
    RUNS['va%d' % s] = {'arm': 'V-A', 'seed': s, 'dir': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d' % s,
                        'rb': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d/decisions_sdmpc31_v3c3_k92va_s%d/signal_readback.csv' % (s, s)}

TB = 300.0
NTB = 30
K0 = 3  # 900 s
BINS = list(range(K0, NTB))  # 900 .. 8700 start
DEMAND = [(0, 900, 4300), (900, 1800, 5600), (1800, 2700, 6000), (2700, 3600, 5200), (3600, 4500, 3900), (4500, 9001, 3450)]
T_END = 9001.0
NC3_SG2_GREEN = 45.0   # GREEN 만, 주기 150 s, offset 75 s (verify_c V2)
NC3_CYCLE = 150.0
NC3_OFFSET = 75.0


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def a_det(t):
    a = 0.0
    for lo, hi, q in DEMAND:
        if t > lo:
            a += (min(t, hi) - lo) * q / 3600.0
    return a


def err_remain(d):
    out = []
    for f in glob.glob(d + '/**/*.err', recursive=True):
        with open(f, 'rb') as fh:
            txt = fh.read().decode('latin-1')
        for m in re.finditer(r'Vehicle input 1099:.{0,60}?remain: (\d+) vehicles', txt):
            out.append((f.replace('\\', '/'), int(m.group(1))))
    return out


def sg2_from_readback(path):
    ev = []
    bad = 0
    with open(path, newline='', encoding='utf-8', errors='replace') as fh:
        for r in csv.DictReader(fh):
            if r['sc_no'] != '1001' or r['sg_no'] != '2':
                continue
            if r['ok'] != '1' or r['requested_state'] != r['readback_state']:
                bad += 1
            if r['stage'] == 'immediate':
                ev.append((int(float(r['sim_sec'])), r['readback_state']))
    ev.sort()
    greens = []
    for i, (t, st) in enumerate(ev):
        if st == 'GREEN':
            te = ev[i + 1][0] if i + 1 < len(ev) else 9000
            greens.append((t, min(te, 9000)))
    # per-second GREEN in 300 s bins
    gsec = np.zeros(NTB)
    for t0, t1 in greens:
        for s in range(t0, t1):
            gsec[min(s // 300, NTB - 1)] += 1
    starts = np.array([g[0] for g in greens], dtype=float)
    durs = np.array([g[1] - g[0] for g in greens], dtype=float)
    return {'greens': greens, 'gsec_bin': gsec.tolist(), 'starts': starts, 'durs': durs, 'bad': bad,
            'first_event': ev[0] if ev else None}


def nc3_sg2():
    gsec = np.zeros(NTB)
    starts, durs = [], []
    t = NC3_OFFSET
    while t < 9000:
        if t >= 900:
            starts.append(t); durs.append(NC3_SG2_GREEN)
        for s in range(int(t), int(min(t + NC3_SG2_GREEN, 9000))):
            gsec[min(s // 300, NTB - 1)] += 1
        t += NC3_CYCLE
    return {'gsec_bin': gsec.tolist(), 'starts': np.array(starts), 'durs': np.array(durs)}


def per_bin_frames(ft, vals):
    ft = np.asarray(ft); v = np.asarray(vals, dtype=float)
    b = np.minimum((ft // TB).astype(int), NTB - 1)
    mx = np.full(NTB, np.nan); p90 = np.full(NTB, np.nan); mean = np.full(NTB, np.nan)
    for k in range(NTB):
        m = b == k
        if m.any():
            mx[k] = v[m].max(); p90[k] = np.percentile(v[m], 90); mean[k] = v[m].mean()
    return mx, p90, mean


def snap(ft, vals, T):
    # frame at T+0.1 (decision instant)
    ft = np.asarray(ft)
    i = int(np.argmin(np.abs(ft - (T + 0.1))))
    if abs(ft[i] - (T + 0.1)) > 0.05:
        return None
    return int(vals[i])


def main():
    inputs = {}
    res = {'runs': {}, 'bins_start_s': [k * 300 for k in BINS]}
    sc_rb = json.load(open(os.path.join(W, 'sc_readback.json'), encoding='utf-8'))
    inputs['w1099/out/sc_readback.json'] = sha(os.path.join(W, 'sc_readback.json'))
    for rk, meta in RUNS.items():
        p1 = os.path.join(W, rk + '.json'); p2 = os.path.join(W, 's2_' + rk + '.json')
        d = json.load(open(p1, encoding='utf-8')); d2 = json.load(open(p2, encoding='utf-8'))
        inputs['w1099/out/%s.json' % rk] = sha(p1); inputs['w1099/out/s2_%s.json' % rk] = sha(p2)
        ft = d['frame_times']; fs = d['frame_series']; fs2 = d2['frame_series']
        L = d['links']
        r = {'arm': meta['arm'], 'seed': meta['seed'], 'fzp': d['path'], 'frames': d['frames']}
        # 1) 10491
        occ = np.array(L['10491']['occ']) * 12.0
        slow = np.array(L['10491']['slow']) * 12.0
        mx, p90, _ = per_bin_frames(ft, fs['10491_n'])
        r['c10491'] = {'mean': occ.tolist(), 'slow_mean': slow.tolist(), 'max5s': mx.tolist(), 'p90_5s': p90.tolist()}
        # 2) 129 lane 1, 100–302 m (50 m 칸 2..6) and whole link
        l129 = np.array(d['l129_occ']) * 12.0  # [pb][lane][t]
        l129s = np.array(d['l129_slow']) * 12.0
        l129v = np.array(d['l129_spdw']) * 12.0
        l1_end = l129[2:7, 0, :].sum(axis=0)
        l1_end_slow = l129s[2:7, 0, :].sum(axis=0)
        l1_end_spd = np.where(l1_end > 0, l129v[2:7, 0, :].sum(axis=0) / np.where(l1_end > 0, l1_end, 1), np.nan)
        l1_all = l129[:, 0, :].sum(axis=0)
        mxs, _, _ = per_bin_frames(ft, fs['l129_l1_slow150'])
        mxw, p90w, _ = per_bin_frames(ft, fs['l129_n'])
        r['l129'] = {'l1_100_302_mean': l1_end.tolist(), 'l1_100_302_slow_mean': l1_end_slow.tolist(),
                     'l1_100_302_speed': l1_end_spd.tolist(), 'l1_all_mean': l1_all.tolist(),
                     'link_mean': (np.array(L['129']['occ']) * 12.0).tolist(),
                     'link_max5s': mxw.tolist(), 'link_p90_5s': p90w.tolist(),
                     'l1_150_302_slow_max5s': mxs.tolist(),
                     'per50m_l1_mean': l129[:, 0, :].tolist()}
        # 3) 127
        occ127 = np.array(L['127']['occ']) * 12.0
        slow127 = np.array(L['127']['slow']) * 12.0
        spd127 = np.where(occ127 > 0, np.array(L['127']['spdw']) * 12.0 / np.where(occ127 > 0, occ127, 1), np.nan)
        mx7, p907, _ = per_bin_frames(ft, fs['127_n'])
        m127 = np.array(d2['m127_occ']) * 12.0; m127v = np.array(d2['m127_spdw']) * 12.0
        st = m127[0, 0:2, :].sum(axis=0)
        st_spd = np.where(st > 0, m127v[0, 0:2, :].sum(axis=0) / np.where(st > 0, st, 1), np.nan)
        r['l127'] = {'mean': occ127.tolist(), 'slow_mean': slow127.tolist(), 'speed': spd127.tolist(),
                     'max5s': mx7.tolist(), 'p90_5s': p907.tolist(),
                     'start0_50_l12_speed': st_spd.tolist()}
        # 4) 26 lane 1, 3,200–3,700 m (100 m 칸 32..36)
        o26 = np.array(d['l26_occ']) * 12.0; v26 = np.array(d['l26_spdw']) * 12.0; s26 = np.array(d['l26_slow']) * 12.0
        e = o26[32:37, 0, :].sum(axis=0)
        e_spd = np.where(e > 0, v26[32:37, 0, :].sum(axis=0) / np.where(e > 0, e, 1), np.nan)
        e_slow = s26[32:37, 0, :].sum(axis=0)
        # tail reach: per bin, the smallest 100 m bin index from which lane-1 speed < 40 continuously up to bin 36
        spd_pb = np.where(o26[:, 0, :] > 0, v26[:, 0, :] / np.where(o26[:, 0, :] > 0, o26[:, 0, :], 1), np.nan)
        tail = []
        for k in range(NTB):
            j = 36
            if not (spd_pb[36, k] < 40):
                tail.append(None); continue
            while j - 1 >= 0 and spd_pb[j - 1, k] < 40:
                j -= 1
            tail.append(j * 100)
        r['l26_l1_end'] = {'mean': e.tolist(), 'speed': e_spd.tolist(), 'slow_mean': e_slow.tolist(),
                           'tail_from_m': tail,
                           'l1_3700_3818_speed': np.where(o26[37:39, 0, :].sum(axis=0) > 0,
                                                          v26[37:39, 0, :].sum(axis=0) / np.where(o26[37:39, 0, :].sum(axis=0) > 0, o26[37:39, 0, :].sum(axis=0), 1), np.nan).tolist()}
        # 5) entrance
        nins = np.array(d['entrance']['n_ins_bin'], dtype=float)
        r['entrance'] = {'n_ins_bin': nins.astype(int).tolist(), 'n_first_le_W': d['in1099']['n_first_le_W'],
                         'n_first_lt1': d['in1099']['n_first_lt1'],
                         'first_speed_mean': (np.array(d['entrance']['first_speed_sum_bin']) / np.where(nins > 0, nins, 1)).tolist(),
                         'zero_frames_bin': d['entrance']['zero_frames_bin']}
        er = err_remain(meta['dir'])
        r['err_remain_1099'] = er
        # 6) SG2
        if meta['arm'] == 'NC3':
            g = nc3_sg2(); r['sg2_source'] = 'sig prog1 GREEN-only 45 s / 150 s, offset 75 (verify_c V2)'
        else:
            g = sg2_from_readback(meta['rb']); inputs[meta['rb']] = sha(meta['rb'])
            r['sg2_source'] = 'readback immediate rows, GREEN only'
            r['sg2_rows_bad'] = g['bad']
            # cross-check with sc_readback.json
            r['sg2_check_sc_readback'] = sc_rb[rk]['1001_2']['green_s_bin']
        starts = np.asarray(g['starts']); durs = np.asarray(g['durs'])
        nst = np.zeros(NTB); sd = np.zeros(NTB); cyc = np.full(NTB, np.nan)
        for k in range(NTB):
            m = (starts // TB).astype(int) == k
            nst[k] = m.sum(); sd[k] = durs[m].sum()
        gaps = np.diff(starts) if len(starts) > 1 else np.array([])
        for k in range(NTB):
            m = (starts[:-1] // TB).astype(int) == k if len(starts) > 1 else np.array([], bool)
            if len(gaps) and m.any():
                cyc[k] = gaps[m].mean()
        r['sg2'] = {'green_s_bin': g['gsec_bin'], 'n_green_starts_bin': nst.astype(int).tolist(),
                    'green_per_cycle_mean': np.where(nst > 0, sd / np.where(nst > 0, nst, 1), np.nan).tolist(),
                    'cycle_mean': cyc.tolist()}
        # decision-instant snapshots (online-like whole-link counts) at T = 150 k
        snaps = {}
        for T in range(900, 9000, 150):
            snaps[T] = {'10491': snap(ft, fs['10491_n'], T), '129': snap(ft, fs['l129_n'], T), '127': snap(ft, fs['127_n'], T)}
        r['snap_decision'] = snaps
        r['_n_cum_end'] = int(nins.sum())
        res['runs'][rk] = r

    # ---- unserved queue estimate per seed ----
    for s in (31, 41, 43):
        keys = ['nc%d' % s, 'b%d' % s, 'va%d' % s]
        AT = {}
        for k in keys:
            rem = [x[1] for x in res['runs'][k]['err_remain_1099']]
            R = rem[0] if rem else 0
            AT[k] = res['runs'][k]['_n_cum_end'] + R
            res['runs'][k]['A_T'] = AT[k]; res['runs'][k]['R_end'] = R
        A_T = float(np.mean(list(AT.values())))
        Ad_T = a_det(T_END)
        eps_T = A_T - Ad_T
        tends = [(k + 1) * TB for k in range(NTB)]
        Ncum = {k: np.cumsum(res['runs'][k]['entrance']['n_ins_bin']).astype(float) for k in keys}
        Ad = np.array([a_det(t) for t in tends])
        bridge = Ad + eps_T * Ad / Ad_T
        lower = np.max(np.vstack([Ncum[k] for k in keys]), axis=0)
        A_hat = np.maximum(bridge, lower)
        sd = np.sqrt(np.clip(Ad * (1 - Ad / Ad_T), 0, None))
        for k in keys:
            q = A_hat - Ncum[k]
            res['runs'][k]['entrance']['Q_hat_end_of_bin'] = q.tolist()
            res['runs'][k]['entrance']['Q_det_end_of_bin'] = (Ad - Ncum[k]).tolist()
            res['runs'][k]['entrance']['deficit_vs_nc3_cum'] = (Ncum['nc%d' % s] - Ncum[k]).tolist()
        res.setdefault('queue_est', {})[str(s)] = {'A_T_by_run': AT, 'A_T_used': A_T, 'A_det_T': Ad_T, 'eps_T': eps_T,
                                                    'bridge_sd': sd.tolist(), 'lift_by_lower_bound': (A_hat - bridge).tolist()}
    res['inputs_sha256'] = inputs
    res['tool_sha256'] = sha(os.path.abspath(__file__))
    os.makedirs(OUTD, exist_ok=True)
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return None if not np.isfinite(o) else round(float(o), 4)
        if isinstance(o, np.integer):
            return int(o)
        return o
    with open(os.path.join(OUTD, 'fd_series.json'), 'w', encoding='utf-8') as fh:
        json.dump(clean(res), fh, allow_nan=False)
    print('FD_DONE')


if __name__ == '__main__':
    main()
