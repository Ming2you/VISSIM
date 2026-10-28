# vb_compare.py — vb_scan 출력으로 짝 차를 다시 내고 B_RESULTS / B_REPORT 주장값과 견줌 (읽기만)
import json, os
V = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(V, 'out')
O701 = set(json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))['inside_links'])
O635 = set(json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json', encoding='utf-8'))['inside_links'])
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
LOC19 = FWE7 | {'10484', '10490', '10639', '10681', '10481', '10483', '10643', '10682', '129', '31', '68', '70'}
assert len(O701) == 701 and len(O635) == 635 and O635 <= O701 and len(LOC19) == 19
SEEDS = ['31', '41', '43']
FORMS = {'ours_9000': '9000', 'codex_8100': '8100'}
R = {k: json.load(open(os.path.join(OUT, k + '.json'), encoding='utf-8')) for k in
     [p + s for p in ('b', 'nc', 'va') for s in SEEDS]}


def level(run, form):
    L = R[run]['links'][form]
    sm = lambda S: sum(v for k, v in L.items() if k in S)
    fs = R[run]['first_seen'][FORMS[form]]
    return {'O701': sm(O701), 'O635': sm(O635), 'A4a': sum(L.values()), 'FWE7': sm(FWE7), 'LOC19': sm(LOC19),
            'L66': L.get('66', 0.0), 'S_all': fs['S_all'], 'S_in1098': fs['S_in1098'], 'S_in1099': fs['S_in1099'],
            'S_urban': fs['S_urban'], 'links': L}


def diff(a, b, form):
    A, B = level(a, form), level(b, form)
    d = {k: A[k] - B[k] for k in ('O701', 'O635', 'A4a', 'FWE7', 'LOC19', 'L66')}
    # first-observation difference: d4b(a-b) = S_b - S_a
    d['U'] = B['S_all'] - A['S_all']
    d['u1098'] = B['S_in1098'] - A['S_in1098']
    d['u1099'] = B['S_in1099'] - A['S_in1099']
    d['ucity'] = B['S_urban'] - A['S_urban']
    d['A4'] = d['A4a'] + d['U']
    d['outa701'] = d['A4'] - d['O701']
    d['outa635'] = d['A4'] - d['O635']
    d['outb701'] = d['A4a'] - d['O701']
    return d


# claimed values (B_RESULTS T1 / B_REPORT T1·T2) — order s31, s41, s43
C = {
 ('ours_9000', 'B-NC3'): dict(O701=[-157.0, -523.4, -222.2], O635=[-159.6, -474.4, -257.4], A4a=[-128.3, -548.6, -219.1],
     U=[303.5, 318.0, -231.5], A4=[175.1, -230.6, -450.6], outa701=[332.1, 292.9, -228.4], outa635=[334.8, 243.8, -193.2],
     outb701=[28.7, -25.2, 3.1], FWE7=[-37.3, -178.1, -88.9], LOC19=[28.2, -245.2, -34.7], u1098=[-25.5, -19.3, -113.5],
     u1099=[490.0, 468.4, 84.0], ucity=[-161.0, -131.0, -202.0], L66=[28.0, -9.8, 61.1]),
 ('ours_9000', 'VA-NC3'): dict(O701=[-240.6, -421.7, -309.5], O635=[-489.3, -659.3, -616.5], A4a=[-199.6, -400.6, -294.4],
     U=[-174.3, -105.6, -62.0], A4=[-373.9, -506.2, -356.4], outa701=[-133.3, -84.5, -46.9], outa635=[115.4, 153.1, 260.1],
     outb701=[41.0, 21.1, 15.1], FWE7=[-12.3, -72.6, -5.3], LOC19=[-51.5, -187.1, -92.5], u1098=[214.1, -0.9, 63.8],
     u1099=[-329.6, -126.0, -55.9], ucity=[-58.8, 21.3, -69.8], L66=[180.7, 170.2, 206.0]),
 ('ours_9000', 'B-VA'): dict(O701=[83.6, -101.8, 87.3], O635=[329.7, 184.9, 359.1], A4a=[71.3, -148.0, 75.3],
     U=[477.8, 423.6, -169.5], A4=[549.1, 275.6, -94.3], outa701=[465.5, 377.3, -181.6], outa635=[219.4, 90.7, -453.3],
     outb701=[-12.3, -46.3, -12.0], FWE7=[-25.0, -105.5, -83.7], LOC19=[79.8, -58.1, 57.8], u1098=[-239.6, -18.4, -177.3],
     u1099=[819.6, 594.3, 140.0], ucity=[-102.2, -152.3, -132.2], L66=[-152.7, -180.0, -145.0]),
 ('codex_8100', 'B-NC3'): dict(O701=[-126.9, -464.0, -195.4], O635=[-129.8, -423.3, -232.6], A4a=[-93.0, -484.6, -194.0],
     U=[222.2, 226.7, -231.5], A4=[129.1, -258.0, -425.5], outa701=[256.1, 206.1, -230.1], outa635=[258.9, 165.3, -192.9],
     outb701=[33.9, -20.6, 1.4], FWE7=[-37.0, -172.5, -89.6], LOC19=[30.7, -227.2, -32.7], u1098=[-25.5, -19.3, -113.5],
     u1099=[408.8, 377.0, 84.0], ucity=[-161.1, -131.0, -202.0], L66=[27.1, -4.1, 61.5]),
 ('codex_8100', 'VA-NC3'): dict(O701=[-207.7, -391.3, -286.7], O635=[-437.6, -599.4, -570.9], U=[-111.2, -104.9, -70.9],
     A4=[-279.4, -474.3, -340.4], outa701=[-71.7, -83.0, -53.7], outa635=[158.2, 125.1, 230.5], FWE7=[-21.5, -66.7, -6.9],
     u1099=[-265.9, -113.1, -55.9]),
 ('codex_8100', 'B-VA'): dict(O701=[80.8, -72.7, 91.3], O635=[307.8, 176.1, 338.3], A4a=[75.1, -115.2, 75.5],
     U=[333.4, 331.5, -160.6], A4=[408.6, 216.3, -85.1], outa701=[327.8, 289.0, -176.4], outa635=[100.7, 40.2, -423.4],
     outb701=[-5.6, -42.5, -15.8], FWE7=[-15.5, -105.7, -82.7], LOC19=[90.1, -57.8, 59.4], u1098=[-239.6, -18.4, -177.3],
     u1099=[674.8, 490.0, 139.9], ucity=[-101.7, -140.1, -123.2], L66=[-142.0, -153.8, -131.1]),
}
PAIRS = {'B-NC3': ('b', 'nc'), 'VA-NC3': ('va', 'nc'), 'B-VA': ('b', 'va')}
rows = []
maxdev = 0.0
nchk = 0
for (form, pair), claims in C.items():
    a, b = PAIRS[pair]
    for i, s in enumerate(SEEDS):
        d = diff(a + s, b + s, form)
        for m, vals in claims.items():
            mine = d[m]
            dev = abs(mine - vals[i])
            nchk += 1
            maxdev = max(maxdev, dev)
            rows.append((form, pair, 'v3c3-s' + s, m, vals[i], round(mine, 3), round(dev, 3)))
# levels
lev_claims = {  # ours_9000 levels B / NC3 / V-A  (B_REPORT T0, B_RESULTS 1.7)
 'O635': {'b': [6693.3, 6654.3, 6746.0], 'nc': [6853.0, 7128.7, 7003.4], 'va': [6363.7, 6469.4, 6386.9]},
 'O701': {'b': [7379.0, 7374.8, 7489.1], 'nc': [7535.9, 7898.3, 7711.3], 'va': [7295.4, 7476.6, 7401.8]},
 'A4a': {'b': [9111.8, 9147.6, 9265.1], 'nc': [9240.2, 9696.2, 9484.2], 'va': [9040.5, 9295.7, 9189.8]},
 'FWE7': {'b': [1779.3, 1785.7, 1787.6], 'nc': [1816.6, 1963.8, 1876.5], 'va': [1804.3, 1891.2, 1871.2]},
 'L66': {'b': [282.4, 321.2, 334.3], 'nc': [254.4, 330.9, 273.3], 'va': [435.1, 501.2, 479.3]},
}
link_claims = {'124': {'b': [10.3, 10.5, 10.5], 'nc': [10.3, 10.6, 10.5], 'va': [10.6, 10.9, 10.4]},
               '10480': {'b': [3.6, 3.7, 2.6], 'nc': [2.1, 2.0, 1.8], 'va': [1.9, 1.9, 1.7]},
               '70': {'b': [22.9, 7.6, 38.1], 'nc': [7.9, 56.5, 24.7], 'va': [7.0, 12.4, 7.2]},
               '10639': {'b': [51.8, 19.6, 74.7], 'nc': [9.3, 8.7, 10.2], 'va': [9.2, 9.1, 10.0]},
               '26': {'b': [1070.4, 1029.5, 879.7], 'nc': [978.4, 917.9, 900.1], 'va': [871.6, 889.9, 817.5]},
               '120': {'b': [515.7, 511.6, 534.3], 'nc': [525.9, 522.0, 535.8], 'va': [530.9, 522.6, 534.0]}}
lrows = []
lmax = 0.0
for m, dd in lev_claims.items():
    for r, vals in dd.items():
        for i, s in enumerate(SEEDS):
            mine = level(r + s, 'ours_9000')[m]
            dev = abs(mine - vals[i]); lmax = max(lmax, dev)
            lrows.append(('level', m, r + s, vals[i], round(mine, 3), round(dev, 3)))
for lk, dd in link_claims.items():
    for r, vals in dd.items():
        for i, s in enumerate(SEEDS):
            mine = R[r + s]['links']['ours_9000'].get(lk, 0.0)
            dev = abs(mine - vals[i]); lmax = max(lmax, dev)
            lrows.append(('link', lk, r + s, vals[i], round(mine, 3), round(dev, 3)))
# X5 counts
x5 = {}
for r in ('b', 'nc', 'va'):
    for s in SEEDS:
        fs = R[r + s]['first_seen']['9000']
        x5[r + s] = dict(n_all=fs['n_all'], n74=fs['n_in1098'], n26=fs['n_in1099'], rows=R[r + s]['rows'],
                         frames=R[r + s]['n_frames'], lt1=R[r + s]['frames_lt1'], rows_lt1=R[r + s]['rows_lt1'],
                         gap=R[r + s]['frame_gap_min_max'], f_ours=R[r + s]['frames_ours_9000'], f_codex=R[r + s]['frames_codex_8100'])
# links in FZP not in membership universe
univ = set(json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))['outside_links']) | O701
stray = {}
for k in R:
    L = R[k]['links']['ours_9000']
    st = {lk: v for lk, v in L.items() if lk not in univ}
    stray[k] = (len(st), round(sum(st.values()), 3))
res = dict(n_checks=nchk, max_dev=maxdev, rows=rows, level_rows=lrows, level_max_dev=lmax, x5=x5, stray=stray)
json.dump(res, open(os.path.join(OUT, 'compare.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('pair checks', nchk, 'max |dev|', round(maxdev, 4))
big = [r for r in rows if r[-1] > 0.05]
print('pair cells > 0.05:', len(big))
for r in big[:60]:
    print(' ', r)
print('level/link checks', len(lrows), 'max |dev|', round(lmax, 4))
for r in lrows:
    if r[-1] > 0.05:
        print(' ', r)
print('x5', json.dumps(x5))
print('stray links (not in 1236 universe)', stray)
