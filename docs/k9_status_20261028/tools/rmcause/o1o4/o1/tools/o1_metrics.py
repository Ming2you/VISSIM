r"""O1 step 2: paired metrics for the v3c3 rule-RM arms (RM) against NC3 (same seed), side by side with V-A.
python -B o1_metrics.py  ->  o1o4/o1/out/o1_metrics.json, o1_bins.csv, o1_toplinks.csv
Definitions copied from V-A va_metrics.py (amendment 34 sec.8 / J1 an_metrics):
  M1 = stage-1 region fw_e_main (FW_E mainline 7 links), M2 = east_link_sets_source.json mainline + on_connectors +
  off_connectors + on_approaches (19 links), M3 = Omega TTT (635 links), M3u = urban_omega, M4a = all-link TTT (1,236),
  M4b = uninserted delay over the union inputs, NC3 anchor of the same seed, M4 = M4a + M4b, OUT_a = M4 - M3,
  OUT_b = M4a - M3, REM = run-end .err lane-change removals (reading A), REM_B = those on links outside Omega (reading B).
Extra rows (O1): on-ramp regions (meter connector + whole from-link) and meterbound queues per meter, FW_E / FW_W
  sums, fw_w_main, offramp, outside region, FW_E zone space-mean speeds per 150 s bin.
Unions: URM = RM(31,41) + NC3(31,41); U6VA = V-A(31,41,43) + NC3(31,41,43) (reproduces the V-A report);
  UC = RM(31,41) + V-A(31,41,43) + NC3(31,41,43) (common column for the side-by-side table).
Scans: RM = o1o4/o1/scans (this workflow), NC3 = SP/j1/analysis/scans (sha16 checked, amendment 34 sec.8.1),
  V-A = SP/k92/va/analysis/scans (sha256 compared with the V-A va_metrics.json record).  Read only everywhere else."""
import csv
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
O1 = os.path.dirname(HERE)
OUT = os.path.join(O1, 'out')
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
AV = os.path.join(SP, 'k92', 'va', 'analysis')
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
RMROOT = r'D:\VISSIM_runs\20261001_v3c3'
VAROOT = r'D:\VISSIM_runs\20261023_sdmpc31_k92'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
LINK_SETS = (r'D:\VISSIM-merge\review-d80faf9\diagnostics\vsl_handoff_20260924\evidence\accounting'
             r'\east_link_sets_source.json')
J1_SCAN_SHA16 = {'nc3_s31': ('9419b0bc31e2ab18', '3490c88ccd16175a'), 'nc3_s41': ('fd103d4362a809ba', '94f93c9193aa7014'),
                 'nc3_s43': ('3d946a0fa489a46a', 'f2baaeddae324156')}
FWE_METERS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FWW_METERS = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
LOCAL_KEYS = ['mainline', 'on_connectors', 'off_connectors', 'on_approaches']
T_ACT = 900.0
SEEDS2 = (31, 41)
SEEDS3 = (31, 41, 43)
UNIONS = {'URM': (('rm', SEEDS2), ('nc3', SEEDS2)),
          'U6VA': (('va', SEEDS3), ('nc3', SEEDS3)),
          'UC': (('rm', SEEDS2), ('va', SEEDS3), ('nc3', SEEDS3))}
PAIRS = {'RM-NC3|URM': ('rm', 'nc3', 'URM', SEEDS2), 'RM-NC3|UC': ('rm', 'nc3', 'UC', SEEDS2),
         'VA-NC3|U6VA': ('va', 'nc3', 'U6VA', SEEDS3), 'VA-NC3|UC': ('va', 'nc3', 'UC', SEEDS3),
         'RM-VA|UC': ('rm', 'va', 'UC', SEEDS2)}
UNION_DEP = ('M4', 'M4b', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
BIN_KEYS = ('M1', 'M2', 'onramp_FWE', 'meterbound_FWE', 'onramp_FWW', 'meterbound_FWW', 'fw_w_main', 'M3', 'M3u',
            'M4a', 'M4b', 'M4', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other', 'outside')


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def below_normal():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, 0x00004000)
    return k.GetPriorityClass(h)


def jl(p):
    with io.open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    prio = below_normal()
    for n, want in STAGE1_SHA.items():
        if sha(os.path.join(STAGE1, n)) != want:
            raise SystemExit('stage1 tool %s sha mismatch' % n)
    sys.path.insert(0, STAGE1)
    import stage1_common as C
    C.find_rule_policy = lambda run_dir: None
    import stage1_report as R
    sets = jl(LINK_SETS)['link_sets']
    inside, all_links, _ = C.membership_inside()
    # ---- load scans
    va_rec = jl(os.path.join(AV, 'out', 'va_metrics.json'))['per_run']
    loaded, prov = {}, {}
    for arm, seeds in (('rm', SEEDS2), ('va', SEEDS3), ('nc3', SEEDS3)):
        for s in seeds:
            tag = '%s_s%d' % (arm, s)
            d = {'rm': os.path.join(O1, 'scans', tag), 'va': os.path.join(AV, 'scans', tag),
                 'nc3': os.path.join(SP, 'j1', 'analysis', 'scans', tag)}[arm]
            hs, hu = sha(os.path.join(d, 'scan.json')), sha(os.path.join(d, 'uninserted.json'))
            if arm == 'nc3' and (hs[:16], hu[:16]) != J1_SCAN_SHA16[tag]:
                raise SystemExit('NC3 scan sha16 mismatch %s' % tag)
            if arm == 'va':
                want = va_rec['U6VA|%s' % tag]
                if (want['scan_sha256'], want['uninserted_sha256']) != (hs, hu):
                    raise SystemExit('V-A scan differs from the V-A report record %s' % tag)
            loaded[tag] = {'scan': jl(os.path.join(d, 'scan.json')), 'un': jl(os.path.join(d, 'uninserted.json'))}
            if loaded[tag]['scan'].get('seed') != s:
                raise SystemExit('seed mismatch %s' % tag)
            errp = {'rm': os.path.join(RMROOT, 's%d_v3c3rm' % s, 'run', 'baseline_s%d_v3c3rm_001.err' % s),
                    'nc3': os.path.join(RMROOT, 's%d_v3c3nc' % s, 'run', 'baseline_s%d_v3c3nc_001.err' % s),
                    'va': os.path.join(VAROOT, 'sdmpc31_v3c3_k92va_s%d' % s, 'network',
                                       'sdmpc31_sdmpc31_v3c3_k92va_s%d_001.err' % s)}[arm]
            if not os.path.exists(errp):
                raise SystemExit('err missing %s' % errp)
            an = loaded[tag]['scan'].get('an') or {}
            prov[tag] = {'dir': d, 'scan_sha256': hs, 'uninserted_sha256': hu, 'err': errp, 'err_sha256': sha(errp),
                         'scan_an_err_sha256': an.get('err_sha256'),
                         'fzp': loaded[tag]['scan']['fzp'], 'inpx': loaded[tag]['scan']['inpx']}
    # ---- unions and NC3 anchors
    unions, union_src, anchors = {}, {}, {}
    for u, members in UNIONS.items():
        src = {}
        for arm, seeds in members:
            for s in seeds:
                tag = '%s_s%d' % (arm, s)
                for k, v in loaded[tag]['un']['inputs'].items():
                    if v.get('queued') or v.get('remain_err', 0) > 0:
                        src.setdefault(k, []).append(tag)
        unions[u] = sorted(src, key=int)
        union_src[u] = src
        anchors[u] = {s: {k: v['anchored_total_generated'] for k, v in loaded['nc3_s%d' % s]['un']['inputs'].items()
                          if k in unions[u]} for s in SEEDS3}
    sc0 = loaded['nc3_s31']['scan']
    nb, bs = sc0['n_bins'], sc0['bin_sec']
    cut = int(T_ACT // bs)
    # ---- removals (reading A / B) from the run-end .err the scan used
    rem = {}
    for tag, d in loaded.items():
        e = C.parse_err(prov[tag]['err'])
        links = [l for _, _, l in e['removals']]
        if len(links) != d['scan']['err']['removals']:
            raise SystemExit('removal count differs from scan: %s' % tag)
        rem[tag] = {'all': len(links), 'outside_omega': sum(1 for l in links if l not in inside),
                    'inside_omega': sum(1 for l in links if l in inside),
                    'scan_err_removals': d['scan']['err']['removals'],
                    'remains': {str(k): v for k, v in e['remains'].items()},
                    'removal_links_top': sorted(((l, links.count(l)) for l in set(links)), key=lambda x: -x[1])[:10]}
    # ---- per run, per union
    per_run, bins_of = {}, {}
    for u, members in UNIONS.items():
        for arm, seeds in members:
            for s in seeds:
                tag = '%s_s%d' % (arm, s)
                sc, un = loaded[tag]['scan'], loaded[tag]['un']
                ser = R.arm_series(sc, un, unions[u], anchors[u][s])
                lv = sc['link_vh']

                def lb(ids):
                    z = np.zeros(nb)
                    miss = []
                    for i in ids:
                        a = lv.get(str(i))
                        if a is None:
                            miss.append(i)
                            continue
                        z = z + np.asarray(a, float)
                    return z, miss
                parts, missing = {}, {}
                for k in LOCAL_KEYS + ['off_receivers_shared']:
                    parts[k], missing[k] = lb(sets[k])
                b = {'M1': ser['region:fw_e_main'][0], 'M2': sum(parts[k] for k in LOCAL_KEYS),
                     'M3': ser['omega_ttt'][0], 'M3u': ser['region:urban_omega'][0], 'M4': ser['all_plus_unins'][0],
                     'M4a': ser['all_ttt'][0], 'M4b': ser['unins'][0], 'unins_1098': ser['unins_1098'][0],
                     'unins_1099': ser['unins_1099'][0], 'unins_other': ser['unins_other'][0],
                     'fw_w_main': ser['region:fw_w_main'][0], 'offramp': ser['region:offramp'][0],
                     'outside': ser['region:outside'][0], 'x_off_receivers_shared': parts['off_receivers_shared'],
                     'onramp_FWE': sum(ser['region:onramp:' + m][0] for m in FWE_METERS),
                     'onramp_FWW': sum(ser['region:onramp:' + m][0] for m in FWW_METERS),
                     'meterbound_FWE': sum(ser['meterbound:' + m][0] for m in FWE_METERS),
                     'meterbound_FWW': sum(ser['meterbound:' + m][0] for m in FWW_METERS)}
                for m in FWE_METERS + FWW_METERS:
                    b['onramp:' + m] = ser['region:onramp:' + m][0]
                    b['meterbound:' + m] = ser['meterbound:' + m][0]
                b['OUT_a'] = b['M4'] - b['M3']
                b['OUT_b'] = b['M4a'] - b['M3']
                bins_of[(u, tag)] = b
                full = {k: float(v.sum()) for k, v in b.items()}
                full['REM'] = float(rem[tag]['all'])
                full['REM_B'] = float(rem[tag]['outside_omega'])
                fs = sc['frame_series']
                mbmax = {m: {'max_veh': float(np.max(fs['meterbound'][m])),
                             'max_sec': float(fs['t'][int(np.argmax(fs['meterbound'][m]))])} for m in FWE_METERS + FWW_METERS}
                per_run[(u, tag)] = {
                    'union': u, 'tag': tag, 'seed': s, 'arm': arm, 'full': full,
                    'pre900': {k: float(v[:cut].sum()) for k, v in b.items()},
                    'meterbound_max': mbmax,
                    'checks': {'M1_links_minus_region': float(parts['mainline'].sum() - b['M1'].sum()),
                               'omega_vs_totals': float(b['M3'].sum() - sc['totals']['omega_ttt_veh_h']),
                               'all_vs_totals': float(b['M4a'].sum() - sc['totals']['all_ttt_veh_h']),
                               'missing_links': {k: v for k, v in missing.items() if v},
                               'frames': sc['frames'], 'unknown_rows': sc['regions']['unknown_links_rows'],
                               'region_counts': sc['regions']['counts']},
                    'end_state': {'in_network_last_frame': fs['all'][-1], 'vehicles_seen': sc['vehicles_seen'],
                                  'remains': sc['err']['remains'], 'removals_by_region': sc['err']['removals_by_region']}}
    # union-free rows identical across unions
    for tag in loaded:
        us = [u for u in UNIONS if (u, tag) in per_run]
        for k in per_run[(us[0], tag)]['full']:
            if k in UNION_DEP:
                continue
            vals = [per_run[(u, tag)]['full'][k] for u in us]
            if max(vals) - min(vals) > 1e-9:
                raise SystemExit('union-free row differs: %s %s' % (tag, k))
    # ---- pairs
    pairs = {}
    for pk, (a, b0, u, seeds) in PAIRS.items():
        keys = list(per_run[(u, '%s_s%d' % (a, seeds[0]))]['full'])
        d = {str(s): {k: per_run[(u, '%s_s%d' % (a, s))]['full'][k] - per_run[(u, '%s_s%d' % (b0, s))]['full'][k]
                      for k in keys} for s in seeds}
        base = {str(s): {k: per_run[(u, '%s_s%d' % (b0, s))]['full'][k] for k in keys} for s in seeds}
        armv = {str(s): {k: per_run[(u, '%s_s%d' % (a, s))]['full'][k] for k in keys} for s in seeds}
        mean = {k: float(np.mean([d[str(s)][k] for s in seeds])) for k in keys}
        pct = {str(s): {k: (100.0 * d[str(s)][k] / base[str(s)][k] if base[str(s)][k] else None) for k in keys}
               for s in seeds}
        pre = {str(s): max(abs(per_run[(u, '%s_s%d' % (a, s))]['pre900'][k] - per_run[(u, '%s_s%d' % (b0, s))]['pre900'][k])
                           for k in per_run[(u, '%s_s%d' % (a, s))]['pre900']) for s in seeds}
        pc = {}
        for s in seeds:
            if b0 == 'nc3':
                p = R.pairing_check(s, loaded['nc3_s%d' % s]['scan'], loaded['%s_s%d' % (a, s)]['scan'], T_ACT)
            else:
                p = R.pairing_check(s, loaded['%s_s%d' % (b0, s)]['scan'], loaded['%s_s%d' % (a, s)]['scan'], T_ACT)
            p['max_abs_pre900_delta'] = pre[str(s)]
            pc[str(s)] = p
        bd = {k: {str(s): [round(float(x), 4) for x in (bins_of[(u, '%s_s%d' % (a, s))][k] - bins_of[(u, '%s_s%d' % (b0, s))][k])]
                  for s in seeds} for k in BIN_KEYS}
        pairs[pk] = {'arm': a, 'base': b0, 'union': u, 'seeds': list(seeds), 'delta': d, 'base_val': base,
                     'arm_val': armv, 'mean_delta': mean, 'pct_of_base': pct, 'pairing': pc, 'bins_delta': bd}
    # ---- per-input uninserted (NC3 anchor) for the UC union
    unins_by_input = {}
    for u in ('URM', 'UC'):
        tab = {}
        for k in unions[u]:
            tab[k] = {'queued_in': union_src[u][k]}
            for arm, seeds in UNIONS[u]:
                for s in seeds:
                    tag = '%s_s%d' % (arm, s)
                    sc = loaded[tag]['scan']
                    rec = loaded[tag]['un']['inputs'].get(k)
                    if not rec or not rec.get('schedule'):
                        tab[k][tag] = None
                        continue
                    bb, ff = R.U.clipped_series(rec['schedule'], sc['insertions'][k]['entry_times'], anchors[u][s][k],
                                                sc['frames']['first_sec'], sc['frames']['last_sec'],
                                                sc['frame_series']['t'], nb, bs)
                    tab[k][tag] = {'veh_h_nc_anchor': float(bb.sum()), 'max_queue': float(ff.max()),
                                   'max_queue_sec': float(sc['frame_series']['t'][int(np.argmax(ff))]),
                                   'remain_err': rec.get('remain_err'), 'link': rec.get('link'), 'name': rec.get('name'),
                                   'inserted_seen': rec.get('inserted_seen')}
        unins_by_input[u] = tab
    # ---- FW_E zone speeds per bin (space-mean, veh-km / veh-h)
    zone_speed = {}
    for tag, dd in loaded.items():
        zs = {}
        for z, rec in dd['scan']['speed']['zones'].items():
            if not z.startswith('FW_E'):
                continue
            vh, vk = np.asarray(rec['veh_h'], float), np.asarray(rec['veh_km'], float)
            zs[z] = [round(float(k / h), 2) if h > 0 else None for h, k in zip(vh, vk)]
            zs[z + '|extent'] = [rec['start_m'], rec['end_m']]
        cells = dd['scan']['speed']['cells']['FW_E']
        zone_speed[tag] = {'zones': zs, 'cell_bounds_m': cells['bounds_m'],
                           'cell_speed': [[round(float(k / h), 1) if h > 0 else None for h, k in zip(hh, kk)]
                                          for hh, kk in zip(cells['veh_h'], cells['veh_km'])]}
    # ---- top link deltas RM - NC3 (full run)
    region_named = {}
    for r, lks in loaded['rm_s31']['scan']['regions']['links'].items():
        for lk in lks:
            region_named[str(lk)] = r
    top = {}
    for s in SEEDS2:
        la, lb_ = loaded['rm_s%d' % s]['scan']['link_vh'], loaded['nc3_s%d' % s]['scan']['link_vh']
        rows = []
        for lk in set(la) | set(lb_):
            va_ = float(np.sum(la.get(lk, [0.0])))
            vb = float(np.sum(lb_.get(lk, [0.0])))
            reg = region_named.get(lk) or ('urban_omega' if int(lk) in inside else 'outside')
            rows.append((lk, reg, va_, vb, va_ - vb))
        rows.sort(key=lambda r: -abs(r[4]))
        top[str(s)] = rows[:40]
    res = {'schema': 'o1-rule-rm-metrics/v1', 'doc': __doc__, 'script_sha256': sha(os.path.abspath(__file__)),
           'priority': hex(prio), 'link_sets': {'path': LINK_SETS, 'sha256': sha(LINK_SETS), 'sets': sets},
           'scan_provenance': prov, 'unions': unions, 'union_queued_in': union_src,
           'anchors_nc3': {u: {str(s): anchors[u][s] for s in SEEDS3} for u in UNIONS},
           'per_run': {'%s|%s' % k: v for k, v in per_run.items()}, 'pairs': pairs, 'removals': rem,
           'unins_by_input': unins_by_input, 'zone_speed': zone_speed, 'top_links_rm_minus_nc3': top,
           'bins_before_900': cut, 'bin_sec': bs, 'n_bins': nb}
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, 'o1_metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with io.open(os.path.join(OUT, 'o1_bins.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        cols = [(tag, k) for tag in ('rm_s31', 'nc3_s31', 'va_s31', 'rm_s41', 'nc3_s41', 'va_s41') for k in BIN_KEYS]
        w.writerow(['bin', 't_start_sec'] + ['%s|%s' % c for c in cols])
        for i in range(nb):
            w.writerow([i, i * bs] + ['%.4f' % bins_of[('UC', tag)][k][i] for tag, k in cols])
    with io.open(os.path.join(OUT, 'o1_toplinks.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['seed', 'link', 'region', 'rm_veh_h', 'nc3_veh_h', 'd'])
        for s, rows in top.items():
            for r in rows:
                w.writerow([s, r[0], r[1], '%.3f' % r[2], '%.3f' % r[3], '%.3f' % r[4]])
    # short console summary
    for pk, p in pairs.items():
        print(pk, {k: ['%.1f' % p['delta'][s][k] for s in p['delta']] for k in ('M1', 'M2', 'M3', 'M4', 'OUT_a', 'M4b')})
        print('   pairing', {s: (v['ok'], v['first_divergent_frame_sec'], round(v['max_abs_pre900_delta'], 6)) for s, v in p['pairing'].items()})
    print('unions', unions)


if __name__ == '__main__':
    main()
