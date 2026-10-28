# VERIFY_NEXT analysis over vn_fzp_scan.py outputs (fresh; no O1/O4/W264 code reused).
import json, os, sys, math

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(V, 'out')
H = 5.0 / 3600.0
MAIN7 = [74, 10699, 2, 10613, 119, 10702, 24]
METERS_E = [10639, 10681, 10490, 10484]
APPR_E = [129, 31, 68, 70]
EXITS_E = [10481, 10483, 10643, 10682]
LOCAL19 = MAIN7 + METERS_E + EXITS_E + APPR_E
ONRAMP8 = METERS_E + APPR_E
FWW3 = [26, 10771, 120]
TAGS = ['nc3_s31', 'rm_s31', 'va_s31', 'nc3_s41', 'rm_s41', 'va_s41', 'nc_64cf_s29', 'w264_64cf_s29', 'vsl_64cf_s29']

runs = {}
for t in TAGS:
    p = os.path.join(OUT, t + '.json')
    if os.path.exists(p):
        runs[t] = json.load(open(p, encoding='utf-8'))
R = {'available': list(runs)}


def frames_t(k):
    return 5 * k + 0.1


def bin_sum(arr, lo, hi, conv='end'):
    # conv 'end': frame k counted in [lo,hi) if t=5k+0.1 in [lo,hi). conv 'mid': midpoint 5k-2.4 in [lo,hi)
    s = 0
    for k, n in enumerate(arr):
        if not n:
            continue
        x = frames_t(k) if conv == 'end' else frames_t(k) - 2.5
        if lo <= x < hi:
            s += n
    return s * H


def set_arr(run, links):
    a = [0] * len(run['sel']['2'])
    for L in links:
        for k, n in enumerate(run['sel'][str(L)]):
            a[k] += n
    return a


def tot(run, links):
    return sum(run['link_tot_frames'].get(str(L), 0) for L in links) * H


def all_links(run):
    return sum(run['link_tot_frames'].values()) * H


def cum_ins(run, links=None):
    nf = len(run['frame_rows'])
    a = [0] * nf
    for L, d in run['ins'].items():
        if links is not None and int(L) not in links:
            continue
        for k, n in d.items():
            a[int(k)] += n
    c = 0; out = []
    for x in a:
        c += x; out.append(c)
    return out


def latent_delta(ref, trt, links=None):
    a = cum_ins(ref, links); b = cum_ins(trt, links)
    # frames 1..kmax: (cumIns_ref - cumIns_trt) * 5 s, assumes identical generation streams
    d = sum((x - y) for x, y in zip(a, b)) * H
    return d, a[-1] - b[-1]


def first_diff(a, b, what='crc'):
    # from k=1 (t=5.1); V-A FZPs carry one extra row at t=0.1
    for k in range(1, min(len(a['frame_crc']), len(b['frame_crc']))):
        if what == 'crc':
            if a['frame_crc'][k] != b['frame_crc'][k] or a['frame_rows'][k] != b['frame_rows'][k]:
                return frames_t(k)
        elif a['frame_rows'][k] != b['frame_rows'][k]:
            return frames_t(k)
    return None


# 1. totals
R['totals'] = {}
for t, r in runs.items():
    m7 = tot(r, MAIN7)
    m7_sel = sum(set_arr(r, MAIN7)) * H
    R['totals'][t] = {
        'sha256': r['sha256'], 'rows': r['rows'], 't_max': r['t_max'],
        'main7': m7, 'main7_from_sel_check': m7_sel,
        'per_link_main7': {str(L): r['link_tot_frames'].get(str(L), 0) * H for L in MAIN7},
        'onramp8': tot(r, ONRAMP8), 'meterbound_e': sum(r['meterbound_e']) * H,
        'local19': tot(r, LOCAL19), 'fww3': tot(r, FWW3), 'all_links': all_links(r),
        'link2_lane_max': r['link2_lane_max'],
    }

pairs = [('rm_s31', 'nc3_s31'), ('va_s31', 'nc3_s31'), ('rm_s41', 'nc3_s41'), ('va_s41', 'nc3_s41'), ('rm_s31', 'va_s31'), ('rm_s41', 'va_s41'),
         ('w264_64cf_s29', 'nc_64cf_s29'), ('vsl_64cf_s29', 'nc_64cf_s29')]
R['pairs'] = {}
for a, b in pairs:
    if a not in runs or b not in runs:
        continue
    A, B = R['totals'][a], R['totals'][b]
    d = {k: A[k] - B[k] for k in ('main7', 'onramp8', 'meterbound_e', 'local19', 'fww3', 'all_links')}
    d['main7_pct'] = 100 * d['main7'] / B['main7']
    lat_all, rem_all = latent_delta(runs[b], runs[a])
    lat26, rem26 = latent_delta(runs[b], runs[a], {26})
    lat74, rem74 = latent_delta(runs[b], runs[a], {74})
    d['latent_proxy_all'] = lat_all; d['ins_end_gap_all'] = rem_all
    d['latent_proxy_1099_link26'] = lat26; d['ins_end_gap_link26'] = rem26
    d['latent_proxy_1098_link74'] = lat74; d['ins_end_gap_link74'] = rem74
    d['all_plus_latent'] = d['all_links'] + lat_all
    d['first_diff_frame_t'] = first_diff(runs[a], runs[b]); d['first_count_diff_frame_t'] = first_diff(runs[a], runs[b], 'count')
    d['per_link_main7'] = {L: A['per_link_main7'][L] - B['per_link_main7'][L] for L in A['per_link_main7']}
    # windows
    m7a, m7b = set_arr(runs[a], MAIN7), set_arr(runs[b], MAIN7)
    l2a, l2b = runs[a]['sel']['2'], runs[b]['sel']['2']
    mba, mbb = runs[a]['meterbound_e'], runs[b]['meterbound_e']
    win = {}
    for lo, hi in [(0, 900), (900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 5400), (5400, 6300), (6300, 7200), (7200, 8100), (8100, 9000),
                   (0, 1800), (1800, 5700), (5700, 9000), (3600, 5700), (4500, 5700), (5700, 7200), (7200, 9000), (2700, 4500), (6300, 8100), (0, 9000)]:
        key = f'{lo}-{hi}'
        win[key] = {'main7_end': bin_sum(m7a, lo, hi) - bin_sum(m7b, lo, hi),
                    'main7_mid': bin_sum(m7a, lo, hi, 'mid') - bin_sum(m7b, lo, hi, 'mid'),
                    'link2_end': bin_sum(l2a, lo, hi) - bin_sum(l2b, lo, hi),
                    'meterbound_end': bin_sum(mba, lo, hi) - bin_sum(mbb, lo, hi)}
    d['windows'] = win
    b150 = []
    for j in range(60):
        lo, hi = 150 * j, 150 * (j + 1)
        b150.append([lo, bin_sum(m7a, lo, hi) - bin_sum(m7b, lo, hi)])
    d['main7_150'] = b150
    R['pairs'][f'{a}-{b}'] = d


# 2. B1 spillback minutes on 64cf runs
def b1_minutes(run, off, thr_cell=44):
    lanes = run['link2_lane_max']
    cells = {}
    for m, b, n, s in run['link2_cells']:
        pos_mid = 5.0 * b + 2.5
        c = int(math.floor((off + pos_mid) / 100.0))
        x = cells.setdefault((m, c), [0, 0.0]); x[0] += n; x[1] += s
    minutes = sorted(set(m for m, _ in cells))
    cnt = 0; cnt45 = 0; tails = []
    for m in minutes:
        def cong(c):
            x = cells.get((m, c))
            if not x or x[0] == 0:
                return False
            spd = x[1] / x[0]
            dens = (x[0] / 12.0) / 0.1 / lanes
            return spd < 60.0 and dens > 15.0
        starts = [c for c in (49, 50) if cong(c)]
        if not starts:
            continue
        c = min(starts); tail = c; gap = 0; j = c - 1
        while j >= 28:
            if cong(j):
                tail = j; gap = 0
            else:
                gap += 1
                if gap > 1:
                    break
            j -= 1
        tails.append((m, tail))
        if tail <= thr_cell:
            cnt += 1
        if tail <= thr_cell + 1:
            cnt45 += 1
    up = min(tails, key=lambda x: x[1]) if tails else None
    return {'minutes_tail_lt_4500': cnt, 'minutes_tail_le_4500cell': cnt45, 'most_upstream_tail_cell_start_m': (up[1] * 100 if up else None),
            'at_minute': (up[0] if up else None), 'lanes': lanes}


R['b1'] = {}
for t in ('nc_64cf_s29', 'w264_64cf_s29', 'vsl_64cf_s29', 'nc3_s31', 'nc3_s41'):
    if t in runs:
        R['b1'][t] = {'off_sumlen_2734.5': b1_minutes(runs[t], 2734.5), 'off_geom_2719.7': b1_minutes(runs[t], 2719.7)}


# 3. meter connector merges by window (veh/h) for RM/NC3 s41 & s31
def leave_count(run, meter, to_link, lo, hi):
    ks = run['leave'][str(meter)].get(str(to_link), [])
    return sum(1 for k in ks if lo < frames_t(k) <= hi + 0.15)


R['meter_rates'] = {}
land = {10490: 119, 10484: 24, 10681: 2, 10639: 2}
wins = [(900, 2400), (2400, 4200), (4200, 6000), (6000, 7200), (7200, 9000)]
for t in ('nc3_s41', 'rm_s41', 'nc3_s31', 'rm_s31', 'va_s31', 'va_s41', 'nc_64cf_s29', 'w264_64cf_s29'):
    if t not in runs:
        continue
    R['meter_rates'][t] = {}
    for m, L in land.items():
        R['meter_rates'][t][str(m)] = [round(leave_count(runs[t], m, L, lo, hi) / ((hi - lo) / 3600.0), 1) for lo, hi in wins]
        R['meter_rates'][t][str(m) + '_total'] = sum(len(v) for v in runs[t]['leave'][str(m)].values())
        R['meter_rates'][t][str(m) + '_to'] = {k: len(v) for k, v in runs[t]['leave'][str(m)].items()}
    if t.endswith('64cf_s29'):
        R['meter_rates'][t]['10484_900s'] = [round(leave_count(runs[t], 10484, 24, lo, lo + 900) / 0.25, 1) for lo in range(0, 9000, 900)]

# 4. 10681 windows for model decisions
mp = os.path.join(OUT, 'model_va.json')
if os.path.exists(mp):
    M = json.load(open(mp, encoding='utf-8'))
    R['model_vs_vissim'] = {}
    for tag, m in M.items():
        run = runs.get('va_s31' if tag.startswith('va31') else 'va_s41')
        if run is None:
            continue
        T = int(m['start_sec']); k0 = T // 5; k1 = k0 + 90
        row = {'T': T, 'window': [m['start_sec'], m['end_sec']]}
        for ramp, L in (('RM_C10681', 10681), ('RM_C10490', 10490), ('RM_C10484', 10484), ('RM_C10639', 10639)):
            to = land[L]
            merges = sum(1 for k in run['leave'][str(L)].get(str(to), []) if k0 < k <= k1)
            allleave = sum(1 for v in run['leave'][str(L)].values() for k in v if k0 < k <= k1)
            arr = sum(1 for v in run['enter'][str(L)].values() for k in v if k0 < k <= k1) + sum(1 for k in run['first_on'][str(L)] if k0 < k <= k1)
            s0 = run['sel'][str(L)][k0]; s1 = run['sel'][str(L)][k1]
            mveh = m['final_veh'][ramp]
            stk = m['model_ramp_stock_lower'].get(ramp, {})
            end_key = [x for x in stk if x.startswith(str(T + 450) + '/')]
            mend = -sum(stk[x] for x in end_key) if end_key else None
            g = m['meter_grad_first_pass']
            row[ramp] = {
                'model_veh': mveh, 'model_rate': m['final_rate_veh_h'][ramp], 'vissim_merges': merges, 'vissim_all_leave': allleave,
                'ratio': (mveh / merges if merges else None), 'vissim_start_stock': s0, 'vissim_end_stock': s1, 'vissim_arrivals': arr,
                'vissim_mass_err': s0 + arr - allleave - s1, 'model_end_stock': mend,
                'model_arrival_implied': (mveh + mend - s0) if mend is not None else None,
                'arrival_ratio': ((mveh + mend - s0) / arr) if (mend is not None and arr) else None,
                'grad_total_b0_b1_b2': [g.get(f'{ramp}|b{b}', {}).get('total') for b in (0, 1, 2)],
                'dNUF_dz_b0_b1_b2': [(g.get(f'{ramp}|b{b}', {}).get('res_scaled') or [0, 0])[1] * 1000 for b in (0, 1, 2)],
                'green_cmd': m['meter_green_cmd'][ramp],
            }
        row['tangent_gap_10681'] = m['tangent_gap_10681_veh_h']; row['action_sha256'] = m['sha256']
        R['model_vs_vissim'][tag] = row

json.dump(R, open(os.path.join(OUT, 'vn_analysis.json'), 'w', encoding='utf-8'), indent=1)
print('written', list(runs))
