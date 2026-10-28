# V4b (VSL_OFFLINE, data-after declaration): Omega701 / (4) / outside-Omega (a) for the three VISSIM pairs,
# with (4)b = FIRST-OBSERVATION difference (same seed, same arrival stream assumption; vhr_unins.py formula):
#   U_a - U_b = S(b) - S(a),  S(x) = sum over vehicles first seen at t <= W of (W - t)   (veh.h), W = 8100 s.
# window-off and joint-off: Omega701 and (4)a from RAW_CHECK final_table.json (codex trapezoid form, 0-8100 s).
# VSL-only - NC: Omega701 and (4)a from W264_READ linkbin scans (rectangle form, bins 0..53 = 0-8100 s),
#   Omega701 membership = D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json inside_links.
import json, sys
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FS = SP + '/codex_handoff/work/vhr/scan_out'
VS = SP + '/c_port/vsl/out'
W = 8100.0
F = {t: json.load(open(f'{FS}/first_{t}.json')) for t in ('joint', 'window', 'off', 'nc_raw')}
F['vsl'] = json.load(open(f'{VS}/first_vsl.json'))


def S(tag, cat=None):
    tot = 0.0; n = 0
    for c, d in F[tag]['by_cat'].items():
        if cat is not None and c not in cat:
            continue
        for tt, k in d.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t); n += k
    return tot / 3600.0, n


def dU(a, b, cat=None):
    return S(b, cat)[0] - S(a, cat)[0]


FT = json.load(open(SP + '/codex_handoff/work/rawcheck/final_table.json'))
inside = set(str(x) for x in json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))['inside_links'])
LB = {t: json.load(open(SP + f'/rmcause/o1o4/scan/lb_{t}_s29.json')) for t in ('vsl', 'nc')}


def lb_sum(d, links=None):
    tot = 0.0
    for link, arr in d['vf'].items():
        if links is not None and link not in links:
            continue
        tot += sum(arr[:54])
    return tot * 5.0 / 3600.0


R = {'W_sec': W, 'pairs': {}}
for a, b, src in (('window', 'off', 'final_table'), ('joint', 'off', 'final_table'), ('vsl', 'nc_raw', 'linkbin')):
    if src == 'final_table':
        dO = FT[a]['Omega701'] - FT[b]['Omega701']
        da4 = FT[a]['a4'] - FT[b]['a4']
        dFW = FT[a]['FW_E7'] - FT[b]['FW_E7']
    else:
        A, B = LB['vsl'], LB['nc']
        dO = lb_sum(A, inside) - lb_sum(B, inside)
        da4 = lb_sum(A) - lb_sum(B)
        fw7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
        dFW = lb_sum(A, fw7) - lb_sum(B, fw7)
    db = dU(a, b)
    R['pairs'][f'{a}-{b}'] = dict(source=src, d_Omega701=dO, d_4a=da4, d_4b_firstobs=db, d_4=da4 + db, d_out_a=da4 + db - dO,
                                  d_out_b=da4 - dO, d_FW_E7=dFW,
                                  d_4b_by_input={'1098_link74': dU(a, b, {'74'}), '1099_link26': dU(a, b, {'26'}), 'other': dU(a, b, {'other'})},
                                  inserted_by_W={a: S(a)[1], b: S(b)[1]})
R['first_vsl_vehicles'] = F['vsl']['vehicles']
json.dump(R, open(sys.argv[1], 'w'), indent=1)
print(json.dumps(R, indent=1))
