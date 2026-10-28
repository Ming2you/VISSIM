# v_compare.py — VERIFY_VSL (2026-10-27 KST). Fresh script. Reads v_scan.py outputs (VSL, NC3 of one seed).
# Main form: trapezoid over the 5 s frames (5.1 .. last frame). Codex form: [0, 8100] (frames <= 8095.1 trapezoid,
# start 0 at t=0, last stock held to 8100). 4b = first-observation difference S_NC3 - S_VSL, S(W) = sum (W - t1)/3600.
# Usage: python -B v_compare.py <scan_vsl.json> <scan_nc3.json> <out.json>
import sys, json
from collections import Counter

A, B, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
a, b = json.load(open(A, encoding='utf-8')), json.load(open(B, encoding='utf-8'))
assert a['frames'] == b['frames'], 'frame grids differ'
T = a['frames']


def trap_main(ser):
    return sum((T[i + 1] - T[i]) * (ser[i] + ser[i + 1]) / 2.0 for i in range(len(T) - 1)) / 3600.0


def trap_codex(ser, W=8100.0):
    idx = [i for i, t in enumerate(T) if t <= W]
    s = T[idx[0]] * ser[idx[0]] / 2.0  # 0 stock at t=0
    s += sum((T[i + 1] - T[i]) * (ser[i] + ser[i + 1]) / 2.0 for i in idx[:-1])
    s += (W - T[idx[-1]]) * ser[idx[-1]]
    return s / 3600.0


def S_of(scan, W):
    out = {'1098': 0.0, '1099': 0.0, 'urban': 0.0}
    cnt = {'1098': 0, '1099': 0, 'urban': 0}
    for no, r in scan['first'].items():
        t, link = r[0], r[1]
        if t <= W:
            k = '1098' if link == '74' else ('1099' if link == '26' else 'urban')
            out[k] += (W - t) / 3600.0
            cnt[k] += 1
    return out, cnt


res = {'vsl': A, 'nc3': B, 'fzp_sha_vsl': a['fzp_sha256'], 'fzp_sha_nc3': b['fzp_sha256'],
       'n_frames': len(T), 'first_frame': T[0], 'last_frame': T[-1]}
for form, fn, W in (('main_9000', trap_main, 9000.0), ('codex_8100', trap_codex, 8100.0)):
    lv = {g: fn(a['groups'][g]) for g in a['groups']}
    ln = {g: fn(b['groups'][g]) for g in b['groups']}
    Sv, cv = S_of(a, W)
    Sn, cn = S_of(b, W)
    d4b = {k: Sn[k] - Sv[k] for k in Sv}
    d4b_tot = sum(d4b.values())
    d = {g: lv[g] - ln[g] for g in lv}
    row = dict(level_vsl=lv, level_nc3=ln,
               O701=d['O701'], O635=d['O635'], A4a=d['ALL'], A4b=d4b_tot, A4=d['ALL'] + d4b_tot,
               out_a_701=d['ALL'] + d4b_tot - d['O701'], out_b_701=d['ALL'] - d['O701'],
               out_a_635=d['ALL'] + d4b_tot - d['O635'],
               M1=d['M1'], M2=d['M2'], A4b_1098=d4b['1098'], A4b_1099=d4b['1099'], A4b_urban=d4b['urban'],
               S_vsl=sum(Sv.values()), S_nc3=sum(Sn.values()), first_counts_vsl=cv, first_counts_nc3=cn)
    res[form] = row

# --- arrival-sequence check per first-observed link (assumption behind 4b) ---
def seqs(scan):
    g = {}
    for no, r in scan['first'].items():
        g.setdefault(r[1], []).append((r[0], int(no), r[2], r[3], r[4], r[5]))
    for k in g:
        g[k].sort()
    return g


ga, gb = seqs(a), seqs(b)
arr = {}
for key, sel in (('1098', lambda L: L == '74'), ('1099', lambda L: L == '26'), ('urban', lambda L: L not in ('74', '26'))):
    tot = dict(pre900=[0, 0, 0], post900=[0, 0, 0], post900_attr_order=[0, 0])
    for L in set(ga) | set(gb):
        if not sel(L):
            continue
        xa, xb = ga.get(L, []), gb.get(L, [])
        for ph, lo, hi in (('pre900', -1, 900.0), ('post900', 900.0, 1e9)):
            ta = Counter((round(x[0], 2), x[2], round(x[3], 2), x[4], x[5]) for x in xa if lo <= x[0] < hi)
            tb = Counter((round(x[0], 2), x[2], round(x[3], 2), x[4], x[5]) for x in xb if lo <= x[0] < hi)
            inter = sum((ta & tb).values())
            tot[ph][0] += sum(ta.values()); tot[ph][1] += sum(tb.values()); tot[ph][2] += inter
        # order-preserving attribute match after 900 s (desired speed, length), ignoring insertion time
        sa = [(x[4], x[5]) for x in xa if x[0] >= 900.0]
        sb = [(x[4], x[5]) for x in xb if x[0] >= 900.0]
        m = sum(1 for u, v in zip(sa, sb) if u == v)
        tot['post900_attr_order'][0] += m
        tot['post900_attr_order'][1] += min(len(sa), len(sb))
    arr[key] = tot
res['arrival_check'] = arr
res['arrival_check_note'] = ('pre900/post900 = [n_vsl, n_nc3, n_exact_match] on (t_first, lane, pos, desspeed, length) per first link; '
                             'post900_attr_order = [n_equal, n_compared] of (desspeed, length) sequences in first-seen order')

# --- VSL zone compliance and B2 ---
za, zb = a['zone'], b['zone']


def win(z, key, lo, hi):
    return sum(z[key][i] for i, t in enumerate(T) if lo <= t < hi)


comp = {}
for name, z in (('vsl', za), ('nc3', zb)):
    n = win(z, 'n', 900, 9000); c = win(z, 'comp', 900, 9000)
    n2 = win(z, 'n', 6300, 9000); v2 = win(z, 'vsum', 6300, 9000)
    comp[name] = dict(zone_frames_900_9000=n, comp_share_900_9000=c / n if n else None,
                      zone_speed_6300_9000=v2 / n2 if n2 else None,
                      comp_by_link={k: [v[0], v[1], v[1] / v[0] if v[0] else None] for k, v in z['comp_link'].items()})
res['vsl_zone'] = comp
b2 = {}
for lo, hi in ((8100, 9000), (900, 9000), (900, 1350)):
    sv = {}
    for name, z in (('vsl', za), ('nc3', zb)):
        n = win(z, 'b2_n', lo, hi); v = win(z, 'b2_vsum', lo, hi)
        sv[name] = dict(speed=v / n if n else None, veh_h=n * 5.0 / 3600.0)
    sv['diff'] = dict(speed=(sv['vsl']['speed'] - sv['nc3']['speed']) if sv['vsl']['speed'] is not None and sv['nc3']['speed'] is not None else None,
                      veh_h=sv['vsl']['veh_h'] - sv['nc3']['veh_h'])
    b2['%d_%d' % (lo, hi)] = sv
res['B2'] = b2
json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1)
for form in ('main_9000', 'codex_8100'):
    r = res[form]
    print(form, ' '.join('%s=%+.1f' % (k, r[k]) for k in ('O701', 'O635', 'A4a', 'A4b', 'A4', 'out_a_701', 'out_b_701', 'M1', 'M2',
                                                         'A4b_1098', 'A4b_1099', 'A4b_urban')))
    print('   firstcounts vsl', r['first_counts_vsl'], 'nc3', r['first_counts_nc3'])
print('arrival', json.dumps(arr))
print('zone', json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'comp_by_link'} for k, v in comp.items()}))
print('zone_by_link_vsl', json.dumps(comp['vsl']['comp_by_link']))
print('B2', json.dumps(b2))
