# -*- coding: utf-8 -*-
"""W264 vs paired NC (64cf-s29) time-resolved accounting (read-only). 2026-10-24 rmcause/o1o4.

Inputs (all read-only): o1o4/scan/lb_*.json (linkbin_scan), o1o4/scan/w264_s29.json and
phys/scan/cf_s29_none.json (fwe_scan), o1o4/work/decisions.json, W264 membership.json,
the 64cf inpx (vehicle inputs), native performance files of both runs.
Writes: o1o4/work/w264_bins150.csv, o1o4/work/w264_analysis.json
"""
import csv, json, math, sys, xml.etree.ElementTree as ET
sys.path.insert(0, 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/rmcause/o1o4/work')
import tails as TL

R = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/rmcause'
O = R + '/o1o4'
MEM = 'D:/VISSIM-runtime-window264-recovery/sdmpc31_ca181e84_202610070539/diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
INPX = 'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/network/sdmpc31_sdmpc9000_s29.inpx'
NB, BIN, DT = 60, 150.0, 5.0

A = {'W': json.load(open(O + '/scan/lb_w264_s29.json', encoding='utf-8')),
     'N': json.load(open(O + '/scan/lb_nc_s29.json', encoding='utf-8')),
     'V': json.load(open(O + '/scan/lb_vsl_s29.json', encoding='utf-8'))}
F = {'W': json.load(open(O + '/scan/w264_s29.json', encoding='utf-8')),
     'N': json.load(open(R + '/phys/scan/cf_s29_none.json', encoding='utf-8')),
     'V': json.load(open(O + '/scan/vsl_s29.json', encoding='utf-8'))}
DEC = json.load(open(O + '/work/decisions.json', encoding='utf-8'))
mem = json.load(open(MEM, encoding='utf-8'))
OM701 = set(mem['inside_links'])
OM635 = set(mem['controlled_intersection_expansion']['previous_inside_links'])

S = {
    'main7': {'74', '10699', '2', '10613', '119', '10702', '24'},
    'on_conn_e': {'10484', '10490', '10639', '10681'},
    'off_conn_e': {'10481', '10483', '10643', '10682'},
    'on_appr_e': {'129', '31', '68', '70'},
    'off_recv_shared': {'121', '124', '126', '127'},
    'fw_w_main': {'26', '120', '10771'},
    'w_ramp_conn': {'10480', '10482', '10644', '10646'},
}
S['local19'] = S['main7'] | S['on_conn_e'] | S['off_conn_e'] | S['on_appr_e']
NATIVE = {'W': dict(TravTmTot=33268335.101619, DelayLatent=68632177.4, DemandLatent=10847, VehAct=2566, VehArr=65131),
          'N': dict(TravTmTot=34757141.0238041, DelayLatent=69444031.2999984, DemandLatent=10857, VehAct=2619, VehArr=65068),
          'V': dict(TravTmTot=34188187.315326, DelayLatent=69729435.6999998, DemandLatent=10849, VehAct=2628, VehArr=65067)}


def vh_bins(d, links, key='vf'):
    out = [0.0] * NB
    for lk in links:
        a = d[key].get(lk)
        if a:
            for b in range(NB):
                out[b] += a[b] * DT / 3600.0
    return out


def all_links(d):
    return set(d['vf'])


res = {}
for arm, d in A.items():
    L = all_links(d)
    r = {k: vh_bins(d, v) for k, v in S.items()}
    r['om701'] = vh_bins(d, OM701)
    r['om635'] = vh_bins(d, OM635)
    r['all'] = vh_bins(d, L)
    fw = S['local19'] | S['fw_w_main'] | S['w_ramp_conn'] | S['off_recv_shared']
    r['om701_rest'] = vh_bins(d, OM701 - fw)
    r['outside_om701'] = vh_bins(d, L - OM701)
    # queued (speed < 15 km/h) vehicle-hours on ramps (connector + feeding link)
    for nm, links in {'q_on_e_conn': S['on_conn_e'], 'q_on_e_appr': S['on_appr_e'],
                      'q_10483': {'10483'}, 'q_124': {'124'}, 'q_10480': {'10480'},
                      'q_w_ramp_conn': S['w_ramp_conn'], 'q_off_conn_e': S['off_conn_e'],
                      'q_74': {'74'}}.items():
        r[nm] = vh_bins(d, links, 'qf')
    # per main7 link
    for lk in S['main7']:
        r['m_' + lk] = vh_bins(d, {lk})
    res[arm] = r

# ---- insertions and latent (uninserted) queue ----
root = ET.parse(INPX).getroot()
inputs = []
for v in root.find('vehicleInputs').findall('vehicleInput'):
    vols = [float(tv.get('volume')) for tv in v.iter('timeIntervalVehVolume')]
    inputs.append((v.get('no'), v.get('link'), vols))
IV = [0, 900, 1800, 2700, 3600, 4500, 9000]


def a_exp(vols, t):
    vs = vols + [vols[-1]] * (6 - len(vols))
    s = 0.0
    for i in range(6):
        a, e = IV[i], IV[i + 1]
        if t <= a:
            break
        s += vs[i] * (min(t, e) - a) / 3600.0
    return s


in_links = {}
for no, lk, vols in inputs:
    in_links.setdefault(lk, []).append((no, vols))
# connector graph: connector -> from link; link -> connectors ending on it
c_from, into = {}, {}
for c in root.find('links').findall('link'):
    fl, tl = c.find('fromLinkEndPt'), c.find('toLinkEndPt')
    if fl is not None and tl is not None:
        f0, t0 = fl.get('lane').split()[0], tl.get('lane').split()[0]
        c_from[c.get('no')] = f0
        into.setdefault(t0, []).append(c.get('no'))


def source_input(lk, depth=4):
    """Upstream input link of a first-seen link (vehicle crossed a short input link within 5 s)."""
    front = {lk}
    for _ in range(depth):
        nxt = set()
        for x in front:
            if x in c_from:
                nxt.add(c_from[x])
            else:
                nxt.update(into.get(x, []))
        hit = sorted(y for y in nxt if y in in_links)
        if hit:
            return hit[0] if len(hit) == 1 else None
        front = nxt
    return None


lat = {}
for arm, d in A.items():
    ins = d['ins']
    per = {lk: [0] * NB for lk in in_links}
    unattributed = {}
    attributed = {}
    for k, v in ins.items():
        tgt = k if k in in_links else source_input(k)
        if tgt is None:
            unattributed[k] = sum(v)
            continue
        if tgt != k:
            attributed[k + '->' + tgt] = sum(v)
        for b in range(NB):
            per[tgt][b] += v[b]
    cumd = {}
    for lk, a in per.items():
        cum = [0]
        for b in range(NB):
            cum.append(cum[-1] + a[b])
        cumd[lk] = cum
    lat[arm] = dict(non_input_first_seen=sum(sum(v) for k, v in ins.items() if k not in in_links),
                    attributed=attributed, unattributed=unattributed, cum=cumd,
                    total_inserted=sum(sum(v) for v in ins.values()))


def latent_bins(arm, links, clip):
    out = [0.0] * NB
    for lk in links:
        vols_sum = None
        cum = lat[arm]['cum'][lk]
        for b in range(NB):
            t0, t1 = b * BIN, (b + 1) * BIN
            A0 = sum(a_exp(v, t0) for _, v in in_links[lk])
            A1 = sum(a_exp(v, t1) for _, v in in_links[lk])
            L0, L1 = A0 - cum[b], A1 - cum[b + 1]
            if clip:
                L0, L1 = max(0.0, L0), max(0.0, L1)
            out[b] += 0.5 * (L0 + L1) * BIN / 3600.0
    return out


def dlatent_bins(links, arm='W'):
    """arm - N latent veh*h per bin assuming identical generated arrivals: dL = I_N - I_arm."""
    out = [0.0] * NB
    for lk in links:
        cw, cn = lat[arm]['cum'][lk], lat['N']['cum'][lk]
        for b in range(NB):
            d0 = cn[b] - cw[b]
            d1 = cn[b + 1] - cw[b + 1]
            out[b] += 0.5 * (d0 + d1) * BIN / 3600.0
    return out


ALLIN = list(in_links)
for arm in A:
    res[arm]['lat_all_clip'] = latent_bins(arm, ALLIN, True)
    res[arm]['lat_all_raw'] = latent_bins(arm, ALLIN, False)
    res[arm]['lat_1098'] = latent_bins(arm, ['74'], True)
    res[arm]['lat_1099'] = latent_bins(arm, ['26'], True)
dlat = {'all': dlatent_bins(ALLIN), '1098': dlatent_bins(['74']), '1099': dlatent_bins(['26']),
        'urban': dlatent_bins([l for l in ALLIN if l not in ('74', '26')])}
dlatV = {'all': dlatent_bins(ALLIN, 'V'), '1098': dlatent_bins(['74'], 'V'), '1099': dlatent_bins(['26'], 'V'),
         'urban': dlatent_bins([l for l in ALLIN if l not in ('74', '26')], 'V')}

# ---- physics (60 s windows) -> 150 s bins by window midpoint ----
phys = {}
for arm, d in F.items():
    s = TL.summary(d)
    cong = TL.grids(d)
    b1 = [0] * NB
    m = [0] * NB
    heads = {}
    for w in range(d['nw']):
        b = int((w * 60 + 30) // BIN)
        if b >= NB:
            continue
        x1 = s['b1_tail_m'][w]
        x2 = s['b2_tail_m'][w]
        if x1 is not None and x1 < 4500:
            b1[b] += 1
        if x2 is not None and x2 < 6800:
            m[b] += 1
    # zone delay (vref 108) per 900 s block
    def V(w, b):
        n = d['gN'][w][b]
        return d['gV'][w][b] / n if n else None
    zones = {'U': (0, 4200), 'B1': (4200, 5300), 'M': (5300, 6800), 'B2': (6800, 7900), 'D': (7900, 10800)}
    zd = {z: [0.0] * 10 for z in zones}
    for w in range(min(d['nw'], 150)):
        blk = (w * 60) // 900
        for b in range(d['nb']):
            n = d['gN'][w][b]
            if not n:
                continue
            x = (b + 0.5) * 100
            for z, (a, e) in zones.items():
                if a <= x < e:
                    zd[z][blk] += n * max(0.0, 1.0 - V(w, b) / 108.0) * DT / 3600.0
    # bottleneck heads (fwe_analyze rule) minutes per 900 s block for top heads
    hb = {}
    for w in range(d['nw']):
        for b in range(d['nb'] - 2):
            v1, v2 = V(w, b + 1), V(w, b + 2)
            if cong[w][b] and v1 is not None and v2 is not None and v1 >= 70 and v2 >= 70:
                hb.setdefault(b * 100, [0] * 10)
                if w * 60 // 900 < 10:
                    hb[b * 100][w * 60 // 900] += 1
    phys[arm] = dict(b1_spill_150=b1, m_spill_150=m, summary={k: v for k, v in s.items() if not k.endswith('_tail_m') or k.startswith('b')},
                     zone_delay_900=zd, heads_900=hb)

# ---- write 150 s table ----
cols = ['bin_start_s', 'main7_W', 'main7_N', 'main7_d', 'main7_cumd', 'local19_d', 'om701_d', 'om701_rest_d',
        'outside_om701_d', 'all_d', 'dlat_all', 'all_plus_lat_d', 'cum_all_plus_lat_d', 'dlat_1098', 'dlat_1099',
        'on_conn_e_d', 'on_appr_e_d', 'off_conn_e_d', 'qon_e_W', 'qon_e_N', 'q10483_W', 'q10483_N', 'q124_W', 'q124_N',
        'fw_w_main_d', 'b1spill_W', 'b1spill_N', 'mspill_W', 'mspill_N', 'vsl_dsd63_66',
        'V_main7_d', 'V_main7_cumd', 'V_local19_d', 'V_om701_d', 'V_all_plus_lat_d', 'b1spill_V', 'mspill_V'] + \
       ['g_' + m for m in DEC['meters']]
rows = []
cum = 0.0
cum2 = 0.0
cumV = 0.0
for b in range(NB):
    t = int(b * BIN)
    W, N = res['W'], res['N']
    d7 = W['main7'][b] - N['main7'][b]
    cum += d7
    dall = W['all'][b] - N['all'][b]
    dl = dlat['all'][b]
    cum2 += dall + dl
    vs = DEC['vsl_dsd63_66_readback_by_bin'].get(str(t))
    row = [t, W['main7'][b], N['main7'][b], d7, cum,
           W['local19'][b] - N['local19'][b], W['om701'][b] - N['om701'][b], W['om701_rest'][b] - N['om701_rest'][b],
           W['outside_om701'][b] - N['outside_om701'][b], dall, dl, dall + dl, cum2, dlat['1098'][b], dlat['1099'][b],
           W['on_conn_e'][b] - N['on_conn_e'][b], W['on_appr_e'][b] - N['on_appr_e'][b], W['off_conn_e'][b] - N['off_conn_e'][b],
           W['q_on_e_conn'][b] + W['q_on_e_appr'][b], N['q_on_e_conn'][b] + N['q_on_e_appr'][b],
           W['q_10483'][b], N['q_10483'][b], W['q_124'][b], N['q_124'][b],
           W['fw_w_main'][b] - N['fw_w_main'][b],
           phys['W']['b1_spill_150'][b], phys['N']['b1_spill_150'][b], phys['W']['m_spill_150'][b], phys['N']['m_spill_150'][b],
           '/'.join(str(int(x)) for x in vs) if vs else '']
    V = res['V']
    dV = V['main7'][b] - N['main7'][b]
    cumV += dV
    row += [dV, cumV, V['local19'][b] - N['local19'][b], V['om701'][b] - N['om701'][b],
            V['all'][b] - N['all'][b] + dlatV['all'][b], phys['V']['b1_spill_150'][b], phys['V']['m_spill_150'][b]]
    for m in DEC['meters']:
        g = DEC['green_by_decision'][m].get(str(t))
        row.append(int(g) if g is not None else '')
    rows.append(row)
with open(O + '/work/w264_bins150.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in rows:
        w.writerow([round(x, 3) if isinstance(x, float) else x for x in r])

# ---- period sums ----
PER = [(0, 900), (900, 1800), (1800, 2700), (2700, 3600), (3600, 4500), (4500, 5700), (5700, 7200), (7200, 9000)]
PER2 = [(0, 1800), (1800, 5700), (5700, 9000)]


def psum(arr, a, e):
    return sum(arr[int(a // BIN):int(e // BIN)])


keys = ['main7', 'local19', 'on_conn_e', 'on_appr_e', 'off_conn_e', 'off_recv_shared', 'fw_w_main', 'w_ramp_conn', 'om701', 'om635',
        'om701_rest', 'outside_om701', 'all', 'q_on_e_conn', 'q_on_e_appr', 'q_124', 'q_10483', 'q_10480', 'q_w_ramp_conn', 'q_74'] + ['m_' + l for l in S['main7']]
periods = {}
for (a, e) in PER + PER2 + [(0, 9000)]:
    k = f'{a}-{e}'
    periods[k] = {x: dict(W=round(psum(res['W'][x], a, e), 2), N=round(psum(res['N'][x], a, e), 2),
                          d=round(psum(res['W'][x], a, e) - psum(res['N'][x], a, e), 2)) for x in keys}
    periods[k]['dlat'] = {x: round(psum(v, a, e), 2) for x, v in dlat.items()}
    periods[k]['all_plus_lat_d'] = round(periods[k]['all']['d'] + periods[k]['dlat']['all'], 2)
    periods[k]['b1spill_min'] = dict(W=sum(phys['W']['b1_spill_150'][int(a // BIN):int(e // BIN)]), N=sum(phys['N']['b1_spill_150'][int(a // BIN):int(e // BIN)]))
    periods[k]['mspill_min'] = dict(W=sum(phys['W']['m_spill_150'][int(a // BIN):int(e // BIN)]), N=sum(phys['N']['m_spill_150'][int(a // BIN):int(e // BIN)]),
                                    V=sum(phys['V']['m_spill_150'][int(a // BIN):int(e // BIN)]))
    periods[k]['b1spill_min']['V'] = sum(phys['V']['b1_spill_150'][int(a // BIN):int(e // BIN)])
    periods[k]['V'] = {x: dict(V=round(psum(res['V'][x], a, e), 2), d=round(psum(res['V'][x], a, e) - psum(res['N'][x], a, e), 2)) for x in keys}
    periods[k]['V']['dlat'] = {x: round(psum(v, a, e), 2) for x, v in dlatV.items()}
    periods[k]['V']['all_plus_lat_d'] = round(periods[k]['V']['all']['d'] + periods[k]['V']['dlat']['all'], 2)

checks = {}
for arm in A:
    checks[arm] = dict(
        all_rect=round(sum(res[arm]['all']), 2), native_TravTmTot_h=round(NATIVE[arm]['TravTmTot'] / 3600, 2),
        main7_rect=round(sum(res[arm]['main7']), 3),
        latent_clip_h=round(sum(res[arm]['lat_all_clip']), 1), latent_raw_h=round(sum(res[arm]['lat_all_raw']), 1),
        native_DelayLatent_h=round(NATIVE[arm]['DelayLatent'] / 3600, 1),
        lat_1098_h=round(sum(res[arm]['lat_1098']), 1), lat_1099_h=round(sum(res[arm]['lat_1099']), 1),
        inserted_firstseen=lat[arm]['total_inserted'], non_input_first_seen=lat[arm]['non_input_first_seen'],
        attributed=lat[arm]['attributed'], unattributed=lat[arm]['unattributed'],
        generated_native=NATIVE[arm]['VehArr'] + NATIVE[arm]['VehAct'] + NATIVE[arm]['DemandLatent'],
        n_vehicles_fzp=A[arm]['n_vehicles'], fzp_sha256=A[arm]['fzp_sha256'], rows=A[arm]['rows_used'])
checks['dlat_total'] = round(sum(dlat['all']), 2)
checks['V_dlat_total'] = round(sum(dlatV['all']), 2)
checks['V_native_dDelayLatent_h'] = round((NATIVE['V']['DelayLatent'] - NATIVE['N']['DelayLatent']) / 3600, 2)
checks['V_native_dTravTmTot_h'] = round((NATIVE['V']['TravTmTot'] - NATIVE['N']['TravTmTot']) / 3600, 2)
checks['native_dDelayLatent_h'] = round((NATIVE['W']['DelayLatent'] - NATIVE['N']['DelayLatent']) / 3600, 2)
checks['native_dTravTmTot_h'] = round((NATIVE['W']['TravTmTot'] - NATIVE['N']['TravTmTot']) / 3600, 2)
checks['end_inserted_74'] = dict(W=lat['W']['cum']['74'][-1], N=lat['N']['cum']['74'][-1])
checks['end_inserted_26'] = dict(W=lat['W']['cum']['26'][-1], N=lat['N']['cum']['26'][-1])
checks['om701_sizes'] = dict(om701=len(OM701), om635=len(OM635), main7_in_om701=sorted(S['main7'] & OM701),
                             local19_in_om701=len(S['local19'] & OM701), w_ramp_in=sorted((S['w_ramp_conn'] | {'124', '32', '69', '121'}) & OM701))
out = dict(periods=periods, checks=checks,
           phys={a: dict(summary={k: v for k, v in p['summary'].items() if k not in ('b1_tail_m', 'b2_tail_m', 'b1_spill_windows', 'm_spill_windows')},
                         b1_spill_windows=p['summary']['b1_spill_windows'], m_spill_windows=p['summary']['m_spill_windows'],
                         zone_delay_900={z: [round(x, 1) for x in v] for z, v in p['zone_delay_900'].items()},
                         heads_900={str(k): v for k, v in sorted(p['heads_900'].items(), key=lambda kv: -sum(kv[1]))[:10]})
                 for a, p in phys.items()})
json.dump(out, open(O + '/work/w264_analysis.json', 'w', encoding='utf-8'), indent=1)
print(json.dumps(checks, indent=1))
for k in ['0-1800', '1800-5700', '5700-9000', '0-9000']:
    p = periods[k]
    print(k, 'main7', p['main7'], 'local19 d', p['local19']['d'], 'om701 d', p['om701']['d'], 'all d', p['all']['d'], 'dlat', p['dlat'], 'all+lat d', p['all_plus_lat_d'])
