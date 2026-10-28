r"""R2c step 2 (pre-declared, PRE_R2C.md): paired metrics for the 10681-only rule-RM arm (R1) against NC3, the full
rule-RM arm (RM) and V-A, same seed, seeds 31 and 41.
Definitions = O1 o1_metrics.py (= V-A va_metrics.py, amendment 34 sec.8):
  M1 = stage-1 region fw_e_main (FW_E mainline 7 links 74, 10699, 2, 10613, 119, 10702, 24 = codex
  east_link_sets_source.json mainline), M2 = east_link_sets mainline + on_connectors + off_connectors + on_approaches
  (19 links), M3 = Omega TTT (635 links), M3u = urban_omega, M4a = all-link TTT (1,236), M4b = uninserted delay over
  the union inputs with the NC3 anchor of the same seed, M4 = M4a + M4b, OUT_a = M4 - M3, OUT_b = M4a - M3,
  meterbound / onramp per meter and FW_E / FW_W sums, fw_w_main, offramp, outside, unins_1098 / unins_1099 / other.
Union (primary) UR2 = R1(31,41) + RM(31,41) + V-A(31,41,43) + NC3(31,41,43).  UC (= O1) recomputed for the
reproduction check only.
Windows on the 150 s bins (bin i = [150 i, 150 i + 150) s): pre 0-900, early 2700-4500, late 6300-8100,
whole 900-9000, full 0-9000; and 300 s bins over 900-9000.
'Meter share' rows (reported, no threshold): per seed, window sums of M1 for R1-NC3, RM-NC3, VA-NC3, R1-RM, R1-VA and
the ratios (R1-NC3)/(RM-NC3), (R1-NC3)/(VA-NC3) (None when |denominator| < 0.05 veh.h).
Validity rows: run.json / fixed_validation / 54 decisions / no failure file / no VSL event / R1 meters == [RM_C10681],
10681 green strings R1 vs RM, first RED, pairing (first divergent frame) R1 vs NC3 and R1 vs RM.
Reproduction checks: RM-NC3|UC and VA-NC3|UC full deltas == o1_metrics.json (1e-6); RM-NC3 s41 M1 early / late
== O1 bins and within 0.1 of VERIFY_NEXT vn_analysis (-69.75 / -59.29); VA-NC3 s41 (-1.64 / -58.58).
Usage: python -B r2c_metrics.py                 -> <r2c_n>/out/
       python -B r2c_metrics.py --standin-rm    -> <r2c_n>/selftest/ (R1 := RM scans and run dirs; tool test only)
Read only everywhere except the output folder."""
import csv
import glob
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
R2C = os.path.dirname(HERE)
SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
O1 = os.path.join(SP, 'rmcause', 'o1o4', 'o1')
AV = os.path.join(SP, 'k92', 'va', 'analysis')
VN = os.path.join(SP, 'rmcause', 'o1o4', 'vnext', 'out', 'vn_analysis.json')
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
LINK_SETS_SHA = '1f21247e'
O1_METRICS = os.path.join(O1, 'out', 'o1_metrics.json')
O1_METRICS_SHA = '0bc29a40d7925535d8279191d15da5a42e1b214c241da507c5dd01bfa3d2a7e'
J1_SCAN_SHA16 = {'nc3_s31': ('9419b0bc31e2ab18', '3490c88ccd16175a'), 'nc3_s41': ('fd103d4362a809ba', '94f93c9193aa7014'),
                 'nc3_s43': ('3d946a0fa489a46a', 'f2baaeddae324156')}
RM_SCAN_SHA = {'rm_s31': ('6167582a6877bcbb36d6d24c0128522c4a356385657f69ed2efe67301e732ba1',
                          '956c5fe6003c834e92aac13943bbcd91b3b137faad654337b9ef68275c71ac22'),
               'rm_s41': ('3081d2796822baadb1050058ec9d382f17c2b708a8b4775afea2f00d4566e895',
                          '2e6f56f374ebb7dd8e1b24f392b83cf097786cf72b771fa95d1d0e1e3272517a')}
NET_SHA = {31: '046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d',
           41: 'e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524'}
FWE_METERS = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FWW_METERS = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
SC_OF = {'RM_C10480': 9101, 'RM_C10482': 9102, 'RM_C10646': 9103, 'RM_C10644': 9104, 'RM_C10639': 9105,
         'RM_C10681': 9106, 'RM_C10490': 9107, 'RM_C10484': 9108}
LOCAL_KEYS = ['mainline', 'on_connectors', 'off_connectors', 'on_approaches']
T_ACT = 900.0
SEEDS2 = (31, 41)
SEEDS3 = (31, 41, 43)
UNIONS = {'UR2': (('r1', SEEDS2), ('rm', SEEDS2), ('va', SEEDS3), ('nc3', SEEDS3)),
          'UC': (('rm', SEEDS2), ('va', SEEDS3), ('nc3', SEEDS3))}
PAIRS = {'R1-NC3': ('r1', 'nc3'), 'RM-NC3': ('rm', 'nc3'), 'VA-NC3': ('va', 'nc3'),
         'R1-RM': ('r1', 'rm'), 'R1-VA': ('r1', 'va'), 'RM-VA': ('rm', 'va')}
UNION_DEP = ('M4', 'M4b', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
WINDOWS = {'pre_0_900': (0, 6), 'early_2700_4500': (18, 30), 'late_6300_8100': (42, 54), 'whole_900_9000': (6, 60),
           'full_0_9000': (0, 60)}
TABLE_ROWS = (('M1', '① FW_E 본선 7링크 (주 지표)'), ('meterbound_FWE', 'FW_E 미터 대기 4개 합'),
              ('meterbound:RM_C10681', ' 그중 RM_C10681 미터 대기'), ('onramp_FWE', 'FW_E 램프 구역 4개 합'),
              ('onramp:RM_C10681', ' 그중 RM_C10681 램프 구역'), ('M2', '② 동측 국소 19링크'),
              ('fw_w_main', 'FW_W 본선'), ('unins_1099', '입력 1099 미삽입 (FW_W 머리)'),
              ('unins_1098', '입력 1098 미삽입 (FW_E 머리)'), ('M3', '③ Ω (635링크)'), ('M3u', '③u Ω 안 도시'),
              ('offramp', '진출 램프 구역'), ('M4a', '④a 전체 링크'), ('M4b', '④b 미삽입 (UR2)'),
              ('M4', '④ 전체 + 미삽입'), ('OUT_a', 'Ω 밖 (a) ④ − ③'), ('OUT_b', 'Ω 밖 (b) ④a − ③'),
              ('meterbound_FWW', 'FW_W 미터 대기 4개 합'))
BIN_KEYS = tuple(k for k, _ in TABLE_ROWS) + ('meterbound:RM_C10490', 'meterbound:RM_C10484', 'meterbound:RM_C10639',
                                              'onramp_FWW', 'unins_other', 'outside')
ZONES = ('FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15')


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


def run_dir(arm, s, standin):
    if arm == 'r1':
        return os.path.join(RMROOT, ('s%d_v3c3rm' if standin else 's%d_v3c3rm10681') % s, 'run')
    if arm == 'rm':
        return os.path.join(RMROOT, 's%d_v3c3rm' % s, 'run')
    raise ValueError(arm)


def meter_record(rd, prepared):
    """Decision JSON / events / validation of one fixed-profile rule run (read only)."""
    rec = {'run_dir': rd}
    rj = jl(os.path.join(rd, 'run.json'))
    rec['run_json'] = {k: rj.get(k) for k in ('completed', 'exit_code', 'error', 'started', 'finished',
                                             'prepared_sha256', 'fixed_profile_validation_exit_code')}
    fv = jl(os.path.join(rd, 'fixed_validation.json'))
    rec['fixed_validation'] = {'passed': fv.get('passed'), 'event_readbacks': fv.get('event_readbacks'),
                               'actual_green_windows': len(fv.get('actual_green_windows', [])),
                               'error': fv.get('error')}
    rec['decision_failure_files'] = sorted(os.path.basename(p) for p in glob.glob(os.path.join(rd, 'decision_failure_*')))
    secs = list(range(900, 9000, 150))
    greens, meters_keys, vsl_events = {}, set(), 0
    missing = []
    for t in secs:
        p = os.path.join(rd, 'decision_%d.json' % t)
        if not os.path.exists(p):
            missing.append(t)
            continue
        d = jl(p)
        meters_keys.add(tuple(sorted(d['meters'])))
        for mid, row in d['meters'].items():
            greens.setdefault(mid, []).append(int(row['green_sec']))
        vsl_events += sum(1 for e in d['events'] if e[1] == 'vsl')
    rec['decisions'] = len(secs) - len(missing)
    rec['decisions_missing'] = missing
    rec['decision_meter_sets'] = [list(k) for k in sorted(meters_keys)]
    rec['vsl_events_in_decisions'] = vsl_events
    rec['green_string'] = {m: ''.join('A' if g == 10 else str(g) for g in v) for m, v in greens.items()}
    rec['restricting_decisions'] = {m: sum(1 for g in v if g < 10) for m, v in greens.items()}
    first_red = {}
    with io.open(os.path.join(rd, 'fixed_events.csv'), encoding='ascii') as f:
        for r in csv.DictReader(f):
            if r['kind'] == 'meter' and r['value'] == 'RED':
                first_red.setdefault(int(r['no']), int(r['time_s']))
            if r['kind'] == 'vsl':
                vsl_events += 1
    rec['first_red_sec_by_sc'] = {str(k): v for k, v in sorted(first_red.items())}
    rec['first_red_sec_any'] = min(first_red.values()) if first_red else None
    rec['vsl_events_total'] = vsl_events
    rec['prepared_rule_policy_meters'] = list(jl(os.path.join(prepared, 'rule_policy.json'))['meters'])
    return rec


def main():
    standin = '--standin-rm' in sys.argv
    OUT = os.path.join(R2C, 'selftest' if standin else 'out')
    prio = below_normal()
    for n, want in STAGE1_SHA.items():
        if sha(os.path.join(STAGE1, n)) != want:
            raise SystemExit('stage1 tool %s sha mismatch' % n)
    if not sha(LINK_SETS).startswith(LINK_SETS_SHA):
        raise SystemExit('link set file changed')
    sys.path.insert(0, STAGE1)
    import stage1_common as C
    C.find_rule_policy = lambda run_dir: None
    import stage1_report as R
    sets = jl(LINK_SETS)['link_sets']
    if sorted(int(x) for x in sets['mainline']) != sorted([74, 10699, 2, 10613, 119, 10702, 24]):
        raise SystemExit('mainline 7 links differ: %s' % sets['mainline'])
    inside, all_links, _ = C.membership_inside()
    checks = {}
    # ---- load scans
    va_rec = jl(os.path.join(AV, 'out', 'va_metrics.json'))['per_run']
    loaded, prov = {}, {}
    for arm, seeds in (('r1', SEEDS2), ('rm', SEEDS2), ('va', SEEDS3), ('nc3', SEEDS3)):
        for s in seeds:
            tag = '%s_s%d' % (arm, s)
            d = {'r1': os.path.join(O1, 'scans', 'rm_s%d' % s) if standin else os.path.join(R2C, 'scans', tag),
                 'rm': os.path.join(O1, 'scans', tag), 'va': os.path.join(AV, 'scans', tag),
                 'nc3': os.path.join(SP, 'j1', 'analysis', 'scans', tag)}[arm]
            hs, hu = sha(os.path.join(d, 'scan.json')), sha(os.path.join(d, 'uninserted.json'))
            if arm == 'nc3' and (hs[:16], hu[:16]) != J1_SCAN_SHA16[tag]:
                raise SystemExit('NC3 scan sha16 mismatch %s' % tag)
            if arm == 'rm' and (hs, hu) != RM_SCAN_SHA[tag]:
                raise SystemExit('RM scan differs from O1 %s' % tag)
            if arm == 'va':
                want = va_rec['U6VA|%s' % tag]
                if (want['scan_sha256'], want['uninserted_sha256']) != (hs, hu):
                    raise SystemExit('V-A scan differs from the V-A report record %s' % tag)
            loaded[tag] = {'scan': jl(os.path.join(d, 'scan.json')), 'un': jl(os.path.join(d, 'uninserted.json'))}
            sc = loaded[tag]['scan']
            if sc.get('seed') != s:
                raise SystemExit('seed mismatch %s' % tag)
            if arm == 'r1' and not standin:
                if sha(sc['inpx']) != NET_SHA[s] or 's%d_v3c3rm10681' % s not in sc['run_dir']:
                    raise SystemExit('R1 scan is not the rm10681 run / network %s' % tag)
            r1_err = sorted(glob.glob(os.path.join(sc['run_dir'], '*_001.err'))) if arm == 'r1' else [None]
            if len(r1_err) != 1:
                raise SystemExit('R1 run-end .err not unique: %s' % r1_err)
            errp = {'r1': r1_err[0], 'rm':os.path.join(RMROOT, 's%d_v3c3rm' % s, 'run', 'baseline_s%d_v3c3rm_001.err' % s),
                    'nc3': os.path.join(RMROOT, 's%d_v3c3nc' % s, 'run', 'baseline_s%d_v3c3nc_001.err' % s),
                    'va': os.path.join(VAROOT, 'sdmpc31_v3c3_k92va_s%d' % s, 'network',
                                       'sdmpc31_sdmpc31_v3c3_k92va_s%d_001.err' % s)}[arm]
            if not os.path.exists(errp):
                raise SystemExit('err missing %s' % errp)
            an = sc.get('an') or {}
            if arm in ('r1', 'rm') and an.get('err_sha256') and an['err_sha256'] != sha(errp):
                raise SystemExit('run-end .err differs from the one the scan read: %s' % tag)
            prov[tag] = {'dir': d, 'scan_sha256': hs, 'uninserted_sha256': hu, 'err': errp, 'err_sha256': sha(errp),
                         'scan_an_err_sha256': an.get('err_sha256'), 'fzp': sc['fzp'], 'inpx': sc['inpx'],
                         'run_dir': sc.get('run_dir'), 'zone_policy_match': sc['speed'].get('zone_policy_match')}
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
    checks['UR2_equals_UC'] = unions['UR2'] == unions['UC']
    sc0 = loaded['nc3_s31']['scan']
    nb, bs = sc0['n_bins'], sc0['bin_sec']
    if (nb, bs) != (60, 150):
        raise SystemExit('unexpected bins %s %s' % (nb, bs))
    # ---- removals
    rem = {}
    for tag, d in loaded.items():
        e = C.parse_err(prov[tag]['err'])
        links = [l for _, _, l in e['removals']]
        if len(links) != d['scan']['err']['removals']:
            raise SystemExit('removal count differs from scan: %s' % tag)
        rem[tag] = {'all': len(links), 'outside_omega': sum(1 for l in links if l not in inside),
                    'remains': {str(k): v for k, v in e['remains'].items()}}
    # ---- per run series
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
                    for i in ids:
                        a = lv.get(str(i))
                        if a is not None:
                            z = z + np.asarray(a, float)
                    return z
                b = {'M1': ser['region:fw_e_main'][0], 'M2': sum(lb(sets[k]) for k in LOCAL_KEYS),
                     'M3': ser['omega_ttt'][0], 'M3u': ser['region:urban_omega'][0], 'M4': ser['all_plus_unins'][0],
                     'M4a': ser['all_ttt'][0], 'M4b': ser['unins'][0], 'unins_1098': ser['unins_1098'][0],
                     'unins_1099': ser['unins_1099'][0], 'unins_other': ser['unins_other'][0],
                     'fw_w_main': ser['region:fw_w_main'][0], 'offramp': ser['region:offramp'][0],
                     'outside': ser['region:outside'][0],
                     'onramp_FWE': sum(ser['region:onramp:' + m][0] for m in FWE_METERS),
                     'onramp_FWW': sum(ser['region:onramp:' + m][0] for m in FWW_METERS),
                     'meterbound_FWE': sum(ser['meterbound:' + m][0] for m in FWE_METERS),
                     'meterbound_FWW': sum(ser['meterbound:' + m][0] for m in FWW_METERS)}
                for m in FWE_METERS + FWW_METERS:
                    b['onramp:' + m] = ser['region:onramp:' + m][0]
                    b['meterbound:' + m] = ser['meterbound:' + m][0]
                b['OUT_a'] = b['M4'] - b['M3']
                b['OUT_b'] = b['M4a'] - b['M3']
                if abs(float(lb(sets['mainline']).sum() - b['M1'].sum())) > 1e-3:  # link_vh is rounded (O1: 3e-5)
                    raise SystemExit('M1 links != region %s' % tag)
                bins_of[(u, tag)] = b
                per_run[(u, tag)] = {k: float(v.sum()) for k, v in b.items()}
    # ---- pairs, windows, 300 s bins (UR2)
    def wsum(arr, w):
        a, z = WINDOWS[w]
        return float(np.sum(arr[a:z]))
    pairs = {}
    for pk, (a, b0) in PAIRS.items():
        seeds = SEEDS2
        res = {'arm': a, 'base': b0, 'union': 'UR2', 'seeds': list(seeds), 'windows': {}, 'base_windows': {},
               'arm_windows': {}, 'bins300': {}}
        for s in seeds:
            A, B = bins_of[('UR2', '%s_s%d' % (a, s))], bins_of[('UR2', '%s_s%d' % (b0, s))]
            res['windows'][str(s)] = {k: {w: wsum(A[k] - B[k], w) for w in WINDOWS} for k in BIN_KEYS}
            res['base_windows'][str(s)] = {k: {w: wsum(B[k], w) for w in WINDOWS} for k in BIN_KEYS}
            res['arm_windows'][str(s)] = {k: {w: wsum(A[k], w) for w in WINDOWS} for k in BIN_KEYS}
            res['bins300'][str(s)] = {k: [round(float((A[k] - B[k])[i] + (A[k] - B[k])[i + 1]), 4) for i in range(6, 60, 2)]
                                      for k in BIN_KEYS}
            if b0 == 'nc3':
                p = R.pairing_check(s, loaded['nc3_s%d' % s]['scan'], loaded['%s_s%d' % (a, s)]['scan'], T_ACT)
            else:
                p = R.pairing_check(s, loaded['%s_s%d' % (b0, s)]['scan'], loaded['%s_s%d' % (a, s)]['scan'], T_ACT)
            res.setdefault('pairing', {})[str(s)] = p
        pairs[pk] = res
    # ---- meter share rows (M1 and the shifted rows; reported, no threshold)
    share = {}
    for s in SEEDS2:
        row = {}
        for w in ('early_2700_4500', 'late_6300_8100', 'whole_900_9000'):
            Lw = {pk: pairs[pk]['windows'][str(s)]['M1'][w] for pk in PAIRS}

            def ratio(x, y):
                return None if abs(y) < 0.05 else x / y
            row[w] = {'M1_' + pk: Lw[pk] for pk in PAIRS}
            row[w]['ratio_(R1-NC3)/(RM-NC3)'] = ratio(Lw['R1-NC3'], Lw['RM-NC3'])
            row[w]['ratio_(R1-NC3)/(VA-NC3)'] = ratio(Lw['R1-NC3'], Lw['VA-NC3'])
        share[str(s)] = row
    # ---- zone speeds per 300 s (space mean, veh-km / veh-h)
    zone300 = {}
    for tag in [t for t in loaded if t.split('_s')[1] in ('31', '41')]:
        zs = {}
        for z in ZONES:
            rec = loaded[tag]['scan']['speed']['zones'][z]
            vh, vk = np.asarray(rec['veh_h'], float), np.asarray(rec['veh_km'], float)
            zs[z] = [round(float((vk[i] + vk[i + 1]) / (vh[i] + vh[i + 1])), 1) if vh[i] + vh[i + 1] > 0 else None
                     for i in range(6, 60, 2)]
        zone300[tag] = zs
    # ---- meter records (decision JSON etc.), read only
    meters = {}
    for s in SEEDS2:
        r1d, rmd = loaded['r1_s%d' % s]['scan']['run_dir'], run_dir('rm', s, standin)
        if os.path.normcase(os.path.dirname(r1d)) != os.path.normcase(os.path.dirname(run_dir('r1', s, standin))):
            raise SystemExit('R1 scan run_dir is not under the rm10681 arm: %s' % r1d)
        mr1 = meter_record(r1d, os.path.join(os.path.dirname(r1d), 'prepared'))
        mrm = meter_record(rmd, os.path.join(os.path.dirname(rmd), 'prepared'))
        g1, g0 = mr1['green_string'].get('RM_C10681', ''), mrm['green_string'].get('RM_C10681', '')
        first_diff = next((900 + 150 * i for i, (x, y) in enumerate(zip(g1, g0)) if x != y), None)
        v = {'r1': mr1, 'rm': mrm, 'RM_C10681_green_r1': g1, 'RM_C10681_green_rm': g0,
             'RM_C10681_first_decision_T_where_r1_differs_from_rm': first_diff,
             'checks': {'r1_completed': mr1['run_json']['completed'] is True and mr1['run_json']['exit_code'] == 0,
                        'r1_fixed_validation_passed': mr1['fixed_validation']['passed'] is True,
                        'r1_54_decisions': mr1['decisions'] == 54 and not mr1['decisions_missing'],
                        'r1_no_decision_failure': not mr1['decision_failure_files'],
                        'r1_no_vsl_event': mr1['vsl_events_total'] == 0,
                        'r1_decision_meters_only_10681': mr1['decision_meter_sets'] == [['RM_C10681']],
                        'r1_policy_meters_only_10681': mr1['prepared_rule_policy_meters'] == ['RM_C10681'],
                        'r1_red_only_on_sc9106': set(mr1['first_red_sec_by_sc']) <= {'9106'}}}
        pr_nc = pairs['R1-NC3']['pairing'][str(s)]
        pr_rm = pairs['R1-RM']['pairing'][str(s)]
        r1_red = mr1['first_red_sec_by_sc'].get('9106')
        v['pairing_vs_first_red'] = {
            'R1_vs_NC3_first_divergent_frame_sec': pr_nc['first_divergent_frame_sec'],
            'R1_first_RED_sec_9106': r1_red,
            'R1_vs_NC3_not_before_R1_first_RED': (pr_nc['first_divergent_frame_sec'] is None or r1_red is None
                                                  or pr_nc['first_divergent_frame_sec'] >= r1_red),
            'R1_vs_RM_first_divergent_frame_sec': pr_rm['first_divergent_frame_sec'],
            'RM_first_RED_sec_any': mrm['first_red_sec_any'],
            'R1_vs_RM_not_before_RM_first_RED': (pr_rm['first_divergent_frame_sec'] is None
                                                 or mrm['first_red_sec_any'] is None
                                                 or pr_rm['first_divergent_frame_sec'] >= mrm['first_red_sec_any'])}
        meters[str(s)] = v
    # ---- reproduction checks
    o1 = jl(O1_METRICS)
    checks['o1_metrics_sha_pinned'] = sha(O1_METRICS) == O1_METRICS_SHA
    rep, rep_missing = {}, {}
    for pk_o1, (a, b0) in (('RM-NC3|UC', ('rm', 'nc3')), ('VA-NC3|UC', ('va', 'nc3'))):
        worst, miss, n = 0.0, [], 0
        for s in SEEDS2:
            for k, v in o1['pairs'][pk_o1]['delta'][str(s)].items():
                if k in ('REM', 'REM_B') or k.startswith('x_'):
                    continue
                if k not in per_run[('UC', '%s_s%d' % (a, s))]:
                    miss.append(k)
                    continue
                mine = per_run[('UC', '%s_s%d' % (a, s))][k] - per_run[('UC', '%s_s%d' % (b0, s))][k]
                worst = max(worst, abs(mine - v))
                n += 1
        rep[pk_o1] = {'max_abs_diff': worst, 'values_compared': n}
        rep_missing[pk_o1] = sorted(set(miss))
    checks['UC_full_deltas_vs_o1'] = rep
    checks['UC_full_deltas_keys_missing'] = rep_missing
    checks['UC_full_deltas_equal_o1'] = all(v['max_abs_diff'] < 1e-6 and v['values_compared'] > 0 for v in rep.values())
    vn_ref = {'RM-NC3': (-69.75, -59.29), 'VA-NC3': (-1.64, -58.58)}
    got = {pk: (pairs[pk]['windows']['41']['M1']['early_2700_4500'], pairs[pk]['windows']['41']['M1']['late_6300_8100'])
           for pk in vn_ref}
    o1b = {pk: (float(np.sum(o1['pairs'][pk + '|UC']['bins_delta']['M1']['41'][18:30])),
                float(np.sum(o1['pairs'][pk + '|UC']['bins_delta']['M1']['41'][42:54]))) for pk in vn_ref}
    checks['s41_M1_windows'] = {pk: {'r2c': got[pk], 'o1_bins': o1b[pk], 'vn_analysis': vn_ref[pk]} for pk in vn_ref}
    checks['s41_M1_windows_equal_o1_bins'] = all(abs(got[pk][i] - o1b[pk][i]) < 0.01 for pk in vn_ref for i in (0, 1))
    checks['s41_M1_windows_within_0.1_of_vn'] = all(abs(got[pk][i] - vn_ref[pk][i]) < 0.1 for pk in vn_ref for i in (0, 1))
    checks['zone_policy_match'] = {t: v['zone_policy_match'] for t, v in prov.items() if t.startswith(('r1', 'rm'))}
    res = {'schema': 'r2c-metrics/v1', 'standin_rm': standin, 'doc': __doc__,
           'script_sha256': sha(os.path.abspath(__file__)), 'priority': hex(prio),
           'link_sets': {'path': LINK_SETS, 'sha256': sha(LINK_SETS), 'mainline': sets['mainline']},
           'scan_provenance': prov, 'unions': unions, 'union_queued_in': union_src,
           'per_run': {'%s|%s' % k: v for k, v in per_run.items()}, 'pairs': pairs, 'meter_share_M1': share,
           'zone_speed_300s': zone300, 'meters': meters, 'removals': rem, 'checks': checks,
           'windows_bins': WINDOWS, 'bins300_start_sec': list(range(900, 9000, 300))}
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, 'r2c_metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    # ---- tables
    L = []
    L.append('# R2c 표 (자동 생성, r2c_metrics.py %s)' % res['script_sha256'][:12])
    L.append('')
    L.append('- 단위 veh·h. 합집합 UR2 (%s). UR2 = UC: %s. 같은 시드 짝, 시드 31·41 두 개, 신뢰구간 없음.'
             % (', '.join(unions['UR2']), checks['UR2_equals_UC']))
    L.append('- R1 = 10681 만 규칙 ALINEA, RM = 8미터 규칙 ALINEA, V-A = SDMPC(미터 늘 g10), NC3 = 무제어.')
    L.append('')
    for w in ('early_2700_4500', 'late_6300_8100', 'whole_900_9000', 'full_0_9000'):
        L.append('## 창 %s' % w)
        L.append('')
        hdr = '| 줄 | ' + ' | '.join('%s s%d' % (pk, s) for pk in ('R1-NC3', 'RM-NC3', 'VA-NC3', 'R1-RM', 'R1-VA')
                                   for s in SEEDS2) + ' |'
        L.append(hdr)
        L.append('|' + '---|' * (1 + 5 * len(SEEDS2)))
        for k, name in TABLE_ROWS:
            vals = ['%+.1f' % pairs[pk]['windows'][str(s)][k][w] for pk in ('R1-NC3', 'RM-NC3', 'VA-NC3', 'R1-RM', 'R1-VA')
                    for s in SEEDS2]
            L.append('| %s | %s |' % (name, ' | '.join(vals)))
        L.append('')
        L.append('NC3 수준(같은 창): ' + '; '.join('s%d M1 %.1f' % (s, pairs['R1-NC3']['base_windows'][str(s)]['M1'][w])
                                                for s in SEEDS2))
        L.append('')
    L.append('## 미터 몫 (M1, 보고만, 문턱 없음)')
    L.append('')
    for s in SEEDS2:
        for w, v in share[str(s)].items():
            L.append('- s%d %s: ' % (s, w) + ', '.join('%s %s' % (k, ('%+.2f' % x) if isinstance(x, float) else x)
                                                      for k, x in v.items()))
    L.append('')
    L.append('## 미터 기록')
    L.append('')
    for s in SEEDS2:
        v = meters[str(s)]
        L.append('- s%d RM_C10681 녹색 R1 `%s`' % (s, v['RM_C10681_green_r1']))
        L.append('- s%d RM_C10681 녹색 RM `%s` (처음 다른 결정 T = %s)' % (s, v['RM_C10681_green_rm'],
                                                                      v['RM_C10681_first_decision_T_where_r1_differs_from_rm']))
        L.append('- s%d 점검 %s' % (s, json.dumps(v['checks'], ensure_ascii=False)))
        L.append('- s%d 짝 %s' % (s, json.dumps(v['pairing_vs_first_red'], ensure_ascii=False)))
    L.append('')
    L.append('## 재현 점검')
    L.append('')
    L.append('```')
    L.append(json.dumps(checks, ensure_ascii=False, indent=1))
    L.append('```')
    with io.open(os.path.join(OUT, 'r2c_tables.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    with io.open(os.path.join(OUT, 'r2c_bins300.csv'), 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        cols = [(pk, s, k) for pk in PAIRS for s in SEEDS2 for k in BIN_KEYS]
        wr.writerow(['t_start_sec'] + ['%s|s%d|%s' % c for c in cols])
        for j, t in enumerate(range(900, 9000, 300)):
            wr.writerow([t] + ['%.4f' % pairs[pk]['bins300'][str(s)][k][j] for pk, s, k in cols])
    with io.open(os.path.join(OUT, 'r2c_zone300.csv'), 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        tags = sorted(zone300)
        wr.writerow(['t_start_sec'] + ['%s|%s' % (t, z) for t in tags for z in ZONES])
        for j, t in enumerate(range(900, 9000, 300)):
            wr.writerow([t] + ['' if zone300[g][z][j] is None else '%.1f' % zone300[g][z][j] for g in tags for z in ZONES])
    print(json.dumps({'out': OUT, 'UR2': unions['UR2'], 'UR2_equals_UC': checks['UR2_equals_UC'],
                      'UC_full_deltas_equal_o1': checks['UC_full_deltas_equal_o1'],
                      's41_M1_windows_equal_o1_bins': checks['s41_M1_windows_equal_o1_bins'],
                      's41_M1_windows_within_0.1_of_vn': checks['s41_M1_windows_within_0.1_of_vn'],
                      'late_M1': {s: {pk: round(pairs[pk]['windows'][s]['M1']['late_6300_8100'], 2) for pk in PAIRS}
                                  for s in ('31', '41')}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
