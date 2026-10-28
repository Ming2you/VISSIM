# vhr_metrics.py - metrics from vhr_scan outputs (fresh; no authors' code).
import csv, json

S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/scan_out'
mem = json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))
O701 = set(map(str, mem['inside_links'])); OUT535 = set(map(str, mem['outside_links']))
O635p = set(map(str, mem['controlled_intersection_expansion']['previous_inside_links']))
ours = json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json', encoding='utf-8'))
O635 = set(map(str, ours['inside_links']))
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
UP_E = ['70', '68', '129', '31']; UP_W = ['124', '32', '121', '69']
R = {}
R['sets'] = dict(o701=len(O701), out535=len(OUT535), o701_and_out=len(O701 & OUT535), o635_prev=len(O635p), o635_ours=len(O635),
                 o635_ours_eq_prev=O635 == O635p, o635_subset_701=O635 <= O701, fwe7_in_701=FWE7 <= O701,
                 up8_in_701=all(l in O701 for l in UP_E + UP_W), link66_in_701=('66' in O701), link66_in_635=('66' in O635))
runs = {t: json.load(open(f'{S}/{t}.json')) for t in ['joint', 'nc_raw', 'lnc', 'va_s31', 'nc3_s31', 'j1_s31']}
R['hash'] = {t: {k: r[k] for k in ['rows_all', 'rows_le_8100', 'rows_le_895_1', 'lf_sha_all', 'lf_sha_le_8100', 'lf_sha_le_895_1',
                                    'n_frames', 'first_frame_s', 'last_frame_s', 'has_0p1_frame', 'rows_0p1', 'nondata_lines_after_header', 'file_sha256']}
             for t, r in runs.items()}


def m(run, form):
    I = runs[run]['integrals'][form]
    s = lambda ls: sum(v for l, v in I.items() if l in ls)
    allv = sum(I.values())
    d = dict(O701=s(O701), O635=s(O635), FWE7=s(FWE7), A4a=allv, outb701=allv - s(O701), outb635=allv - s(O635),
             link66=I.get('66', 0.0), not_in_1236=sum(v for l, v in I.items() if l not in O701 and l not in OUT535))
    for l in UP_E + UP_W:
        d['up_' + l] = I.get(l, 0.0)
    return d


R['levels'] = {f'{r}|{f}': m(r, f) for r in runs for f in ['codex_8100', 'ours_8100', 'codex_9000', 'ours_9000']}


def diff(a, b, f):
    A = R['levels'][f'{a}|{f}']; B = R['levels'][f'{b}|{f}']
    return {k: A[k] - B[k] for k in A}


R['pairs'] = {}
for a, b in [('joint', 'nc_raw'), ('joint', 'lnc'), ('va_s31', 'nc3_s31'), ('j1_s31', 'nc3_s31'), ('va_s31', 'j1_s31')]:
    for f in ['codex_8100', 'ours_9000', 'ours_8100', 'codex_9000']:
        R['pairs'][f'{a}-{b}|{f}'] = diff(a, b, f)
# codex reference values
ref = {}
for row in csv.DictReader(open('D:/VISSIM_handoff/20261024/derived/metrics_0_8100.csv', encoding='utf-8-sig')):
    ref[(row['condition'], row['metric'])] = float(row['veh_h'])
cmpd = {}
for cond, run in [('nc', 'nc_raw'), ('joint', 'joint'), ('nc', 'lnc')]:
    L = R['levels'][f'{run}|codex_8100']
    cmpd[f'{run}'] = dict(O701=L['O701'] - ref[(cond, 'Omega701')], FWE7=L['FWE7'] - ref[(cond, 'FW_E_7')],
                         A4a=L['A4a'] - ref[(cond, 'network_sampled_residence')], outb=L['outb701'] - ref[(cond, 'outside_Omega_residence')])
R['vs_codex_metrics_csv'] = cmpd
# alternative urban rule (move 8 upstream links to on-ramp side)
J = R['levels']['joint|codex_8100']; N = R['levels']['nc_raw|codex_8100']
urb_nc = ref[('nc', 'urban_roads')]; urb_j = ref[('joint', 'urban_roads')]
upE_d = sum(J['up_' + l] - N['up_' + l] for l in UP_E); upW_d = sum(J['up_' + l] - N['up_' + l] for l in UP_W)
up_nc = sum(N['up_' + l] for l in UP_E + UP_W)
onE_d = ref[('joint', 'onramps_E')] - ref[('nc', 'onramps_E')]; onW_d = ref[('joint', 'onramps_W')] - ref[('nc', 'onramps_W')]
R['alt_urban'] = dict(urban_d_codex=urb_j - urb_nc, upE_d=upE_d, upW_d=upW_d, up8_d=upE_d + upW_d,
                      per_link_d={l: J['up_' + l] - N['up_' + l] for l in UP_E + UP_W},
                      alt_urban_d=(urb_j - urb_nc) - (upE_d + upW_d), alt_urban_den=urb_nc - up_nc,
                      alt_urban_pct=100 * ((urb_j - urb_nc) - (upE_d + upW_d)) / (urb_nc - up_nc),
                      east_entry_alt_d=onE_d + upE_d, west_entry_alt_d=onW_d + upW_d, codex_pct=100 * (urb_j - urb_nc) / urb_nc)
json.dump(R, open(f'{S}/../metrics_out.json', 'w'), indent=1)
P = lambda d: {k: round(v, 3) for k, v in d.items() if not k.startswith('up_')}
print('sets', R['sets'])
for t, h in R['hash'].items():
    print(t, h['rows_all'], h['rows_le_8100'], h['rows_le_895_1'], h['lf_sha_le_895_1'][:8], h['lf_sha_le_895_1'][-4:], h['lf_sha_all'][:8], h['lf_sha_le_8100'][:8], h['first_frame_s'], h['last_frame_s'], h['has_0p1_frame'], h['nondata_lines_after_header'])
print('vs codex csv', {k: {kk: f'{vv:.2e}' for kk, vv in v.items()} for k, v in cmpd.items()})
for k in ['joint|codex_8100', 'nc_raw|codex_8100', 'lnc|codex_8100', 'va_s31|codex_8100', 'nc3_s31|codex_8100', 'j1_s31|codex_8100']:
    print('L', k, P(R['levels'][k]))
for k, v in R['pairs'].items():
    print('D', k, P(v))
print('alt', {k: (round(v, 3) if isinstance(v, float) else {kk: round(vv, 2) for kk, vv in v.items()}) for k, v in R['alt_urban'].items()})
