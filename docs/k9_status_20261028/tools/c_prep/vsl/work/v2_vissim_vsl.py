# V2b (VSL_OFFLINE, data-after declaration): FW_E VISSIM response around the VSL sign, from fwe_scan
# grids (read only). 64cf-s29, one seed, different network from v3c3. Pairs: VSL-only - NC, window - off,
# joint - off, A1 - joint (A1 VSL 100 decisions; trajectories already differ from 1,350 s).
# Usage: python -B v2_vissim_vsl.py <out_prefix>
import json, sys, os, importlib.util, hashlib
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
TAILS = SP + '/rmcause/o1o4/work/tails.py'   # pinned cb6c0bd4..., reused unchanged
spec = importlib.util.spec_from_file_location('tails', TAILS)
tails = importlib.util.module_from_spec(spec); spec.loader.exec_module(tails)
RUNS = {
    'nc': SP + '/rmcause/phys/scan/cf_s29_none.json',
    'vsl': SP + '/rmcause/o1o4/scan/vsl_s29.json',
    'joint': SP + '/c_port/vsl/out/scan/cx_joint_s29.json',
    'window': SP + '/c_port/vsl/out/scan/cx_window_s29.json',
    'off': SP + '/c_port/vsl/out/scan/cx_off_s29.json',
    'a1': SP + '/c_port/vsl/out/scan/a1_s29.json',
    'fwonly': SP + '/c_port/vsl/out/scan/cx_fwonly_s29.json',
}
PAIRS = [('vsl', 'nc'), ('window', 'off'), ('joint', 'off'), ('a1', 'joint'), ('fwonly', 'nc')]
SIGN_M, NEXT_DSD_M, LANE_DROP_M = 6341.7, 8090.8, 6841.743
ZONES = {'U_0_4200': (0, 4200), 'B1_4200_5300': (4200, 5300), 'M1_5300_6300': (5300, 6300),
         'VSa_6300_6800': (6300, 6800), 'VSb_6800_8100': (6800, 8100), 'D_8100_10800': (8100, 10800)}
WINDOWS = [(0, 900), (900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 5700), (5700, 8100),
           (900, 8100), (1800, 5700), (900, 1350), (1350, 1800), (1800, 2250), (2250, 2700), (5700, 6150),
           (1800, 1950), (1950, 2100), (3450, 4500), (4500, 4650)]
LINES = ['3700', '4600', '5300', '6300', '6800', '7300', '7700', '8500']
RAMPS = ['10681', '10490', '10484', '10639']
SEGS = [(a, a + 500) for a in range(3000, 9000, 500)]


def wins(t0, t1):
    return [w for w in range(151) if t0 <= w * 60 < t1]


def zone_stats(d, ws, a, e):
    bs = [b for b in range(d['nb']) if a <= (b + 0.5) * 100 < e]
    n = sum(d['gN'][w][b] for w in ws for b in bs)
    v = sum(d['gV'][w][b] for w in ws for b in bs)
    return (v / n if n else None), n * 5.0 / 3600.0


def metrics(d, t0, t1):
    ws = wins(t0, t1)
    hrs = (t1 - t0) / 3600.0
    out = {}
    for z, (a, e) in ZONES.items():
        s, vh = zone_stats(d, ws, a, e)
        out[z] = {'speed_kmh': s, 'veh_h': vh}
    out['seg_speed'] = {f'{a}_{e}': zone_stats(d, ws, a, e)[0] for a, e in SEGS}
    out['flow_vph'] = {x: sum(d['cross'][x][w] for w in ws) / hrs for x in LINES}
    out['merge_vph'] = {r: sum(d['merge'][r][w] for w in ws) / hrs for r in RAMPS}
    out['ramp_queued_veh_h'] = {r: (sum(d['conn_q'][r][w] for w in ws) + sum(d['from_q'][r][w] for w in ws)) * 5.0 / 3600.0 for r in RAMPS}
    out['ins_74_vph'] = sum(d['ins'][w] for w in ws) / hrs
    # lane speeds in the VSL span (lane grid 3800-8000 m, 100 m bins)
    lane = {}
    for g in range(4):
        n = v = 0.0
        for w in ws:
            for lb in range(len(d['lN'][0])):
                x = 3800 + (lb + 0.5) * 100
                if 6300 <= x < 8000:
                    n += d['lN'][w][lb][g]; v += d['lV'][w][lb][g]
        lane[str(g + 1)] = v / n if n else None
    out['lane_speed_6300_8000'] = lane
    t = tails.tails(d)
    b1 = [t['b1_tail_m'][w] for w in ws if t['b1_tail_m'][w] is not None]
    b2 = [t['b2_tail_m'][w] for w in ws if t['b2_tail_m'][w] is not None]
    out['b1_spill_min'] = sum(1 for x in b1 if x < 4500)
    out['m_spill_min'] = sum(1 for x in b2 if x < 6800)
    out['b1_tail_min_m'] = min(b1) if b1 else None
    out['b2_tail_min_m'] = min(b2) if b2 else None
    return out


def diff(a, b):
    if isinstance(a, dict):
        return {k: diff(a[k], b.get(k)) for k in a}
    if a is None or b is None:
        return None
    return a - b


def main():
    pre = sys.argv[1]
    data, meta = {}, {}
    for k, p in RUNS.items():
        if not os.path.exists(p):
            meta[k] = {'missing': p}
            continue
        d = json.load(open(p, encoding='utf-8'))
        data[k] = d
        meta[k] = {'path': p, 'scan_sha256': hashlib.sha256(open(p, 'rb').read()).hexdigest(), 'fzp_sha256': d['fzp_sha256'],
                   'fzp': d['fzp'], 'rows_used': d['rows_used']}
    res = {'schema': 'vsl_offline_v2b/1', 'meta': meta, 'windows': WINDOWS, 'zones': ZONES,
           'sign_m': SIGN_M, 'next_dsd_m': NEXT_DSD_M, 'lane_drop_m': LANE_DROP_M, 'runs': {}, 'pairs': {}}
    for k, d in data.items():
        res['runs'][k] = {f'{a}_{b}': metrics(d, a, b) for a, b in WINDOWS}
    for x, y in PAIRS:
        if x in data and y in data:
            res['pairs'][f'{x}-{y}'] = {w: diff(res['runs'][x][w], res['runs'][y][w]) for w in res['runs'][x]}
    json.dump(res, open(pre + '.json', 'w', encoding='utf-8'), indent=1)
    L = []
    for pk, pv in res['pairs'].items():
        L.append(f'## {pk}')
        for w, m in pv.items():
            z = ' '.join(f"{zn.split('_')[0]} {m[zn]['speed_kmh']:+.1f}/{m[zn]['veh_h']:+.1f}" if m[zn]['speed_kmh'] is not None else f"{zn} -" for zn in ZONES)
            fl = ' '.join(f"q{x} {m['flow_vph'][x]:+.0f}" for x in ('5300', '6300', '6800', '7700'))
            L.append(f"{w:>10s} | dv(km/h)/dvh {z} | {fl} | spill B1 {m['b1_spill_min']:+d} M {m['m_spill_min']:+d} | ins74 {m['ins_74_vph']:+.0f}")
    open(pre + '.txt', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L[:60]))


if __name__ == '__main__':
    main()
