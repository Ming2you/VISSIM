r"""VERIFY_N2 fresh metric computation from v2_scan.py outputs (imports nothing from stage1 / r2c / o1 / n34 / vn tools).

Definitions written here from the reports' text (PRE_R2C sec.3, METER_NEXT r2 abbreviations), coded independently:
  M1  FW_E mainline 7 links 74 10699 2 10613 119 10702 24 (codex east_link_sets_source.json /link_sets/mainline)
  M2  local 19 = M1 + on_connectors + off_connectors + on_approaches (same codex file)
  FWW FW_W mainline 26 10771 120
  ONR FW_E on-ramp zone = connectors 10639 10681 10490 10484 + from-links 70 68 129 31 (whole links)
  MB  FW_E meter queue = vehicles on meter connector + vehicles on from-link with NEXTLINK = connector
  OM  Omega = control_area_membership.json inside_links (635)
  ALL all links in the FZP
  UNx uninserted delay of input x: Q(t) = N L(t)/L(T) - I(t), N = I(T) + R(.err), clipped at 0, 0.5 s grid
  M4  = ALL + sum UN over UR2 inputs (194 282 1064 1085 1086 1087 1093 1098 1099 1102); OUTa = M4 - OM
Integration: trapezoid over consecutive frames, each step into the 150 s bin of its midpoint.
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VN2 = os.path.dirname(HERE)
OUT = os.path.join(VN2, 'out')
NB = 60
UR2 = ['194', '282', '1064', '1085', '1086', '1087', '1093', '1098', '1099', '1102']
M1 = ['74', '10699', '2', '10613', '119', '10702', '24']
CODEX = r'D:\VISSIM-merge\review-d80faf9\diagnostics\vsl_handoff_20260924\evidence\accounting\east_link_sets_source.json'
MEMB = r'D:\VISSIM-merge\sim3\diagnostics\control_area_membership.json'
RUNS = {
    'nc_s31': (r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3nc\prepared\network\baseline_s31_v3c3nc.inpx', r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3nc\run\baseline_s31_v3c3nc_001.err'),
    'nc_s41': (r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3nc\prepared\network\baseline_s41_v3c3nc.inpx', r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3nc\run\baseline_s41_v3c3nc_001.err'),
    'rm_s31': (r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\prepared\network\baseline_s31_v3c3rm.inpx', r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\run\baseline_s31_v3c3rm_001.err'),
    'rm_s41': (r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm\prepared\network\baseline_s41_v3c3rm.inpx', r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm\run\baseline_s41_v3c3rm_001.err'),
    'r1_s31': (r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm10681\prepared\network\baseline_s31_v3c3rm10681.inpx', r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm10681\run\baseline_s31_v3c3rm10681_001.err'),
    'r1_s41': (r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm10681\prepared\network\baseline_s41_v3c3rm10681.inpx', r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm10681\run\baseline_s41_v3c3rm10681_001.err'),
    'va_s31': (r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31\network\sdmpc31_sdmpc31_v3c3_k92va_s31.inpx', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31\network\sdmpc31_sdmpc31_v3c3_k92va_s31_001.err'),
    'va_s41': (r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s41\network\sdmpc31_sdmpc31_v3c3_k92va_s41.inpx', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s41\network\sdmpc31_sdmpc31_v3c3_k92va_s41_001.err'),
}
METERS = ['10639', '10681', '10490', '10484']
FROM = {'10639': '70', '10681': '68', '10490': '129', '10484': '31'}


def trap_bins(t, v):
    """Trapezoid over consecutive frames; each step into the 150 s bin of its midpoint."""
    t = np.asarray(t, float)
    v = np.asarray(v, float)
    dt = np.diff(t)
    mid = (t[1:] + t[:-1]) / 2.0
    w = (v[1:] + v[:-1]) * dt / 7200.0
    b = np.clip((mid // 150).astype(int), 0, NB - 1)
    out = np.zeros(NB)
    np.add.at(out, b, w)
    return out


def parse_net(inpx):
    root = ET.parse(inpx).getroot()
    inputs = {}
    for vi in root.iter('vehicleInput'):
        vols = []
        for tv in vi.iter('timeIntervalVehVolume'):
            vols.append((int(tv.get('timeInt').split()[1]) / 1000.0, float(tv.get('volume'))))
        inputs[vi.get('no')] = (vi.get('link'), sorted(vols))
    parents = {}
    for lk in root.iter('link'):
        fe = lk.find('fromLinkEndPt')
        te = lk.find('toLinkEndPt')
        if fe is None or te is None:
            continue
        c = lk.get('no')
        f = fe.get('lane').split()[0]
        to = te.get('lane').split()[0]
        parents.setdefault(c, set()).add(f)
        parents.setdefault(to, set()).add(c)
    return inputs, parents


def err_remain(err):
    txt = io.open(err, 'rb').read().decode('utf-8', 'replace')
    rem = {}
    for m in re.finditer(r'Vehicle input (\d+):.*?\(remain: (\d+) vehicles\)', txt):
        rem[m.group(1)] = int(m.group(2))
    return rem


def uninserted(tag, z, inpx, err):
    inputs, parents = parse_net(inpx)
    input_links = {}
    for no, (lk, _) in inputs.items():
        input_links.setdefault(lk, []).append(no)
    rem = err_remain(err)
    entry = z['veh_t'] - z['veh_tmin']
    flink = z['veh_link']
    tmin = z['veh_tmin']
    attr = np.array([''] * len(flink), dtype=object)
    cache = {}
    amb = 0
    for i, lk in enumerate(flink):
        if lk not in cache:
            # BFS upstream up to 6 hops for the nearest input link
            found, frontier, seen, depth = None, {lk}, {lk}, 0
            while frontier and depth <= 6:
                hits = sorted(x for x in frontier if x in input_links)
                if hits:
                    found = hits if len(hits) > 1 or len(input_links[hits[0]]) > 1 else input_links[hits[0]][0]
                    break
                nxt = set()
                for x in frontier:
                    nxt |= parents.get(x, set())
                frontier = nxt - seen
                seen |= nxt
                depth += 1
            cache[lk] = found
        f = cache[lk]
        if isinstance(f, list):
            amb += 1
            continue
        if f is not None and tmin[i] <= 5.2:
            attr[i] = f
    t_first, t_last = float(z['frames_t'][0]), float(z['frames_t'][-1])
    grid_mid = np.arange(t_first + 0.25, t_last, 0.5)
    res = {}
    T = 9000.0
    for no in UR2:
        lk, vols = inputs[no]
        starts = [s for s, _ in vols] + [T]

        def L(t):
            t = np.asarray(t, float)
            out = np.zeros_like(t)
            for k, (s, q) in enumerate(vols):
                e = starts[k + 1]
                out += q / 3600.0 * np.clip(t - s, 0, e - s)
            return out
        ent = np.sort(entry[attr == no].astype(float))
        tail_rate = np.sum(ent > t_last - 300) / 300.0
        I_T = len(ent) + tail_rate * (T - t_last)
        R = rem.get(no, 0)
        N = I_T + R
        LT = float(L(np.array([T]))[0])
        Q = N * L(grid_mid) / LT - np.searchsorted(ent, grid_mid, side='right')
        Qc = np.maximum(Q, 0.0)
        b = np.clip((grid_mid // 150).astype(int), 0, NB - 1)
        bins = np.zeros(NB)
        np.add.at(bins, b, Qc * 0.5 / 3600.0)
        res[no] = dict(bins=bins, inserted=int(len(ent)), remain=R, N=float(N), LT=LT,
                       unanchored_end=float(LT - len(ent)), qmax=float(Q.max()), qmin=float(Q.min()), link=lk)
    return res, amb


def main():
    codex = json.load(io.open(CODEX, encoding='utf-8-sig'))['link_sets']
    M2 = sorted(set(codex['mainline']) | set(codex['on_connectors']) | set(codex['off_connectors']) | set(codex['on_approaches']))
    assert sorted(codex['mainline']) == sorted(M1) and len(M2) == 19
    omega = set(str(x) for x in json.load(io.open(MEMB, encoding='utf-8-sig'))['inside_links'])
    sets = {'M1': set(M1), 'M2': set(M2), 'FWW': {'26', '10771', '120'},
            'ONR': set(METERS) | set(FROM.values()), 'ONR10681': {'10681', '68'}}
    result = {'sets': {k: sorted(v) for k, v in sets.items()}, 'omega_n': len(omega), 'runs': {}}
    bins = {}
    for tag, (inpx, err) in RUNS.items():
        z = np.load(os.path.join(OUT, 'scan_%s.npz' % tag), allow_pickle=True)
        t = z['frames_t']
        links = list(z['links'])
        C = z['counts'].astype(np.int64)
        col = {l: i for i, l in enumerate(links)}

        def setsum(s):
            idx = [col[l] for l in s if l in col]
            return C[:, idx].sum(axis=1) if idx else np.zeros(len(t))
        b = {k: trap_bins(t, setsum(s)) for k, s in sets.items()}
        b['OM'] = trap_bins(t, setsum(omega))
        b['ALL'] = trap_bins(t, C.sum(axis=1))
        mbsum = np.zeros(len(t))
        for m in METERS:
            v = z['mb_' + m]
            b['MB_' + m] = trap_bins(t, v)
            mbsum = mbsum + v
        b['MB'] = trap_bins(t, mbsum)
        un, amb = uninserted(tag, z, inpx, err)
        for no, r in un.items():
            b['UN_' + no] = r['bins']
        b['UNALL'] = sum(un[no]['bins'] for no in UR2)
        b['M4'] = b['ALL'] + b['UNALL']
        b['OUTa'] = b['M4'] - b['OM']
        bins[tag] = b
        result['runs'][tag] = {'frames': int(len(t)), 'omega_links_seen': len(omega & set(links)),
                               'ambiguous_first_links': amb,
                               'uninserted': {no: {k: v for k, v in r.items() if k != 'bins'} for no, r in un.items()}}
    W = {'early_2700_4500': (18, 30), 'late_6300_8100': (42, 54), 'full_900_9000': (6, 60), 'pre_0_900': (0, 6)}
    keys = ['M1', 'MB', 'MB_10681', 'ONR', 'ONR10681', 'M2', 'FWW', 'UN_1099', 'UN_1098', 'OM', 'ALL', 'UNALL', 'M4', 'OUTa']
    tab = {}
    for s in ('31', '41'):
        for arm in ('r1', 'rm', 'va'):
            for wn, (a, e) in W.items():
                for k in keys:
                    d = bins['%s_s%s' % (arm, s)][k][a:e].sum() - bins['nc_s%s' % s][k][a:e].sum()
                    tab['%s-nc|s%s|%s|%s' % (arm, s, wn, k)] = round(float(d), 3)
        for wn, (a, e) in W.items():
            for arm in ('nc', 'r1'):
                tab['level|%s|s%s|%s|M1' % (arm, s, wn)] = round(float(bins['%s_s%s' % (arm, s)]['M1'][a:e].sum()), 3)
    # 300 s bins for M1 (s41) and 1099
    b300 = {}
    for s in ('31', '41'):
        for arm in ('r1', 'rm', 'va'):
            for k in ('M1', 'UN_1099', 'FWW', 'MB_10681'):
                x = bins['%s_s%s' % (arm, s)][k] - bins['nc_s%s' % s][k]
                b300['%s-nc|s%s|%s' % (arm, s, k)] = [round(float(x[i] + x[i + 1]), 2) for i in range(6, 60, 2)]
    result['diffs'] = tab
    result['bins300_from900'] = b300
    with io.open(os.path.join(OUT, 'v2_metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=1)
    np.savez(os.path.join(OUT, 'v2_bins150.npz'), **{'%s__%s' % (tag, k): v for tag, b in bins.items() for k, v in b.items()})
    print('ok')


if __name__ == '__main__':
    main()
