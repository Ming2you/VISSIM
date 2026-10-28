# -*- coding: utf-8 -*-
"""Summarise fwe_scan outputs (read-only). 2026-10-24 rmcause INV_PHYSICS.
python -B fwe_analyze.py <scan_dir> <out_json> tag1 tag2 ...
"""
import json, sys, math, statistics as st

ZONES = {  # chain metres
    'U_0_4200': (0, 4200),
    'B1_4200_5300': (4200, 5300),
    'M_5300_6800': (5300, 6800),
    'B2_6800_7900': (6800, 7900),
    'D_7900_10784': (7900, 10800),
}
VCONG = 60.0
VFREE = 70.0
VREF = 108.0
RAMPS = ['10639', '10681', '10490', '10484']
OFFS = ['10643', '10682', '10481', '10483']
LANES_AT = lambda x: 4 if x < 6841.743 else 3
DEMAND_1098 = [(0, 900, 7096.32), (900, 1800, 10137.6), (1800, 2700, 10644.48), (2700, 3600, 9123.84),
               (3600, 4500, 7096.32), (4500, 9000, 5068.8)]
PERIODS = [(900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 6300), (6300, 9000)]


def load(scan_dir, tag):
    with open(f'{scan_dir}/{tag}.json', encoding='utf-8') as f:
        return json.load(f)


def cell(d, w, b):
    n = d['gN'][w][b]
    if n == 0:
        return None, 0.0
    fr = d['frames'][w] or 12
    x = (b + 0.5) * d['bin_m']
    dens = n / fr / (d['bin_m'] / 1000.0) / LANES_AT(x)
    return d['gV'][w][b] / n, dens


def rate(arr, w0, w1, frames=None):
    """veh/h over windows [w0,w1) given per-60s counts"""
    s = sum(arr[w0:w1])
    return s * 3600.0 / ((w1 - w0) * 60.0)


def analyse(d):
    nb, nw = d['nb'], d['nw']
    out = {'tag': d['tag'], 'fzp_sha256': d['fzp_sha256'], 'chain_veh_h_5s': round(d['chain_veh_h_5s'], 1)}
    # speed matrix
    V = [[None] * nb for _ in range(nw)]
    K = [[0.0] * nb for _ in range(nw)]
    for w in range(nw):
        for b in range(nb):
            v, k = cell(d, w, b)
            V[w][b] = v; K[w][b] = k
    cong = [[(V[w][b] is not None and V[w][b] < VCONG and K[w][b] > 15) for b in range(nb)] for w in range(nw)]
    # zone stats
    zs = {}
    for z, (a, e) in ZONES.items():
        bs = [b for b in range(nb) if a <= (b + 0.5) * 100 < e]
        cbm = sum(1 for w in range(nw) for b in bs if cong[w][b])  # bin-minutes
        wins = [w for w in range(nw) if any(cong[w][b] for b in bs)]
        # onset: first window with >=2 congested bins in zone in 2 consecutive windows
        onset = None
        for w in range(nw - 1):
            if sum(cong[w][b] for b in bs) >= 2 and sum(cong[w + 1][b] for b in bs) >= 2:
                onset = w * 60; break
        last = max(wins) * 60 + 60 if wins else None
        vh = sum(d['gN'][w][b] for w in range(nw) for b in bs) * 5.0 / 3600.0
        dl = sum(d['gN'][w][b] * max(0.0, 1.0 - (V[w][b] or 0.0) / VREF) for w in range(nw) for b in bs) * 5.0 / 3600.0
        dl_peak = sum(d['gN'][w][b] * max(0.0, 1.0 - (V[w][b] or 0.0) / VREF) for w in range(15, 75) for b in bs) * 5.0 / 3600.0
        zs[z] = {'cong_km_h': round(cbm * 0.1 / 60.0, 3), 'cong_minutes_any': len(wins), 'onset_s': onset,
                 'last_cong_end_s': last, 'veh_h': round(vh, 1), 'delay_veh_h_vref108': round(dl, 1),
                 'delay_900_4500': round(dl_peak, 1)}
    out['zones'] = zs
    out['delay_total_vref108'] = round(sum(v['delay_veh_h_vref108'] for v in zs.values()), 1)
    out['ramp_veh_h'] = {rm: round((sum(d['conn_stock'][rm]) + sum(d['from_stock'][rm])) * 5.0 / 3600.0, 1) for rm in RAMPS}
    out['ramp_queued_veh_h'] = {rm: round((sum(d['conn_q'][rm]) + sum(d['from_q'][rm])) * 5.0 / 3600.0, 1) for rm in RAMPS}
    out['offramp_queued_veh_h'] = {o: round(sum(d['off_q'][o]) * 5.0 / 3600.0, 1) for o in OFFS}
    out['ins_total'] = sum(d['ins'])
    # bottleneck heads: congested bin whose downstream 2 bins are free-ish (v>=VFREE)
    heads = {}
    head_first = {}
    for w in range(nw):
        for b in range(nb - 2):
            if cong[w][b] and V[w][b + 1] is not None and V[w][b + 2] is not None and V[w][b + 1] >= VFREE and V[w][b + 2] >= VFREE:
                x = int(b * 100)
                heads[x] = heads.get(x, 0) + 1
                head_first.setdefault(x, w * 60)
    out['bottleneck_heads_minutes'] = dict(sorted(heads.items(), key=lambda kv: -kv[1])[:12])
    out['bottleneck_heads_first_s'] = {k: head_first[k] for k in out['bottleneck_heads_minutes']}
    # queue tail: per window, upstream-most congested bin (contiguous from a head) -> extent
    ext = []
    for w in range(nw):
        cb = [b for b in range(nb) if cong[w][b]]
        ext.append((min(cb) * 100 if cb else None, max(cb) * 100 + 100 if cb else None, len(cb) * 0.1))
    out['cong_extent_by_15min'] = {}
    for w0 in range(0, 150, 15):
        sl = [e for e in ext[w0:w0 + 15] if e[0] is not None]
        out['cong_extent_by_15min'][w0 * 60] = {
            'min_upstream_m': min(e[0] for e in sl) if sl else None,
            'max_cong_km': round(max(e[2] for e in sl), 1) if sl else 0.0,
            'mean_cong_km': round(sum(e[2] for e in ext[w0:w0 + 15]) / 15, 2)}
    # speed profile by 15 min for key bins
    keyx = [1000, 3000, 3800, 4200, 4400, 4600, 4800, 5000, 5200, 5600, 6200, 6700, 6900, 7100, 7300, 7500, 7700, 8500]
    prof = {}
    for w0 in range(0, 150, 15):
        row = {}
        for x in keyx:
            b = x // 100
            n = sum(d['gN'][w][b] for w in range(w0, min(w0 + 15, nw)))
            s = sum(d['gV'][w][b] for w in range(w0, min(w0 + 15, nw)))
            row[x] = round(s / n, 1) if n else None
        prof[w0 * 60] = row
    out['speed_profile_15min'] = prof
    # flows by period
    fl = {}
    for (a, e) in PERIODS:
        w0, w1 = a // 60, e // 60
        r = {'ins_1098': round(rate(d['ins'], w0, w1))}
        dem = [v for (s0, s1, v) in DEMAND_1098 if s0 <= a < s1]
        r['dem_1098'] = dem[0] if dem else None
        for X in ['300', '3700', '4200', '4600', '5100', '5300', '6800', '7000', '7300', '7700', '8500']:
            r['q' + X] = round(rate(d['cross'][X], w0, w1))
        for rm in RAMPS:
            r['merge_' + rm] = round(rate(d['merge'][rm], w0, w1))
            r['arr_' + rm] = round(rate(d['conn_entry'][rm], w0, w1))
            fr = sum(d['frames'][w0:w1]) or 1
            r['stock_' + rm] = round((sum(d['conn_stock'][rm][w0:w1]) + sum(d['from_stock'][rm][w0:w1])) / fr, 1)
            r['qstock_' + rm] = round((sum(d['conn_q'][rm][w0:w1]) + sum(d['from_q'][rm][w0:w1])) / fr, 1)
            r['qmax_' + rm] = max(d['ramp_qmax'][rm][w0:w1])
        for o in OFFS:
            r['div_' + o] = round(rate(d['div'][o], w0, w1))
            fr = sum(d['frames'][w0:w1]) or 1
            r['offq_' + o] = round(sum(d['off_q'][o][w0:w1]) / fr, 1)
        fl[f'{a}-{e}'] = r
    out['flows'] = fl
    # 5-min max flows (capacity proxies)
    mx = {}
    for X in ['300', '4200', '4600', '5100', '5300', '6800', '7000', '7300', '7700']:
        arr = d['cross'][X]
        best = 0
        for w in range(0, nw - 5):
            best = max(best, sum(arr[w:w + 5]) * 12)
        mx['q' + X + '_max5min'] = best
    out['max5'] = mx
    # travel times
    tt = d['tt']
    def ttstat(a, b):
        res = {}
        for (p0, p1) in [(0, 900), (900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 6300), (6300, 8000)]:
            vals = [v[str(b)] - v[str(a)] for v in tt.values() if str(a) in v and str(b) in v and p0 <= v[str(a)] < p1]
            res[f'{p0}-{p1}'] = (round(st.mean(vals), 1), len(vals)) if vals else (None, 0)
        allv = [v[str(b)] - v[str(a)] for v in tt.values() if str(a) in v and str(b) in v]
        res['all'] = (round(st.mean(allv), 1), len(allv)) if allv else (None, 0)
        return res
    out['tt_300_10500'] = ttstat(300, 10500)
    out['tt_4200_7700'] = ttstat(4200, 7700)
    out['tt_300_4200'] = ttstat(300, 4200)
    out['tt_7700_10500'] = ttstat(7700, 10500)
    # ramp share at B1 and B2 in congested periods
    return out


def main():
    scan_dir, out_path = sys.argv[1], sys.argv[2]
    res = {}
    for tag in sys.argv[3:]:
        res[tag] = analyse(load(scan_dir, tag))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('ok', len(res))


if __name__ == '__main__':
    main()
