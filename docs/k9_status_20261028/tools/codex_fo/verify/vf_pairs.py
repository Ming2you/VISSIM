# vf_pairs.py - VERIFY_FO pair values from the vf_scan outputs (2026-10-28 KST). New code, read only.
# usage: python -B vf_pairs.py <scan_dir> <out_json>
# sets are read from the original membership files (read only); the FO author outputs (V, O, P, M) are not read.
# also cross-checks vf_scan against the VERIFY_B scanner outputs for NC3 / B / V-A (same FZP files).
import sys, os, json

O701_FILE = 'D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json'
O635_FILE = 'D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json'
PART_FILE = 'D:/VISSIM_handoff/20261024/derived/reporting_partition.json'
VB_OUT = ('C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/'
          'scratchpad/k8/codex_handoff/work/verify_b/out')
SEEDS = ['31', '41', '43']
ARMS = ['fo', 'b', 'nc', 'va']
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
LOC19 = FWE7 | {'10484', '10490', '10639', '10681', '10481', '10483', '10643', '10682', '129', '31', '68', '70'}
FWW3 = {'26', '120', '10771'}
CELL59_BINS = range(26, 45)  # 100 m bins whose middle lies in 2,631-4,543 m
EXTRA_LINKS = ['26', '120', '10771', '74', '2', '66', '10639', '10681', '10490', '10484', '10480', '10482', '10646', '10644',
               '70', '68', '69', '31', '124', '129', '10643', '10481']


def jl(p):
    with open(p, encoding='utf-8-sig') as fh:
        return json.load(fh)


def main():
    scan_dir, out = sys.argv[1], sys.argv[2]
    O701 = set(jl(O701_FILE)['inside_links'])
    O635 = set(jl(O635_FILE)['inside_links'])
    part = jl(PART_FILE)
    ONR_E = {k for k, v in part['onramp_roads'].items() if v == 'FW_E'}
    ONR_W = {k for k, v in part['onramp_roads'].items() if v == 'FW_W'}
    OFF = set(part['offramp_links'])
    URB = O701 - FWE7 - FWW3 - ONR_E - ONR_W - (OFF & O701)
    sets_info = {'O701': len(O701), 'O635': len(O635), 'O635_subset_O701': O635 <= O701, 'LOC19': len(LOC19),
                 'URB': len(URB), 'ONR_E': sorted(ONR_E), 'ONR_W': sorted(ONR_W), 'OFF_in_O701': sorted(OFF & O701),
                 'ONR_in_O701': sorted((ONR_E | ONR_W) & O701), 'FWE7_in_O701': sorted(FWE7 & O701),
                 'FWW3_in_O701': sorted(FWW3 & O701)}
    S = {}
    for a in ARMS:
        for s in SEEDS:
            S[a + s] = jl(os.path.join(scan_dir, 'scan_%s%s.json' % (a, s)))

    def level(run, form):
        L = S[run]['links_' + form]
        fs = S[run]['first_seen']['9000' if form == 'ours' else '8100']
        sm = lambda st: sum(v for k, v in L.items() if k in st)
        d = {'O701': sm(O701), 'O635': sm(O635), 'A4a': sum(L.values()), 'FWE7': sm(FWE7), 'LOC19': sm(LOC19),
             'URB': sm(URB), 'FWW3': sm(FWW3), 'ONR_E': sm(ONR_E), 'ONR_W': sm(ONR_W),
             'S_all': fs['S_all'], 'S_in1098': fs['S_in1098'], 'S_in1099': fs['S_in1099'], 'S_urban': fs['S_urban']}
        for lk in EXTRA_LINKS:
            d['L' + lk] = L.get(lk, 0.0)
        return d

    def diff(x, y, form):
        A, B = level(x, form), level(y, form)
        d = {k: A[k] - B[k] for k in A if not k.startswith('S_')}
        d['O701mO635'] = d['O701'] - d['O635']
        d['U'] = B['S_all'] - A['S_all']
        d['u1098'] = B['S_in1098'] - A['S_in1098']
        d['u1099'] = B['S_in1099'] - A['S_in1099']
        d['ucity'] = B['S_urban'] - A['S_urban']
        d['A4'] = d['A4a'] + d['U']
        d['outa701'] = d['A4'] - d['O701']
        d['outa635'] = d['A4'] - d['O635']
        d['outb701'] = d['A4a'] - d['O701']
        d['outb635'] = d['A4a'] - d['O635']
        return d

    PAIRS = {'FO-NC3': ('fo', 'nc'), 'B-FO': ('b', 'fo'), 'FO-VA': ('fo', 'va'), 'B-NC3': ('b', 'nc'),
             'VA-NC3': ('va', 'nc'), 'B-VA': ('b', 'va')}
    res = {'sets': sets_info, 'levels': {}, 'pairs': {}, 'fwe': {}, 'ratios': {}, 'scanner_xcheck': {}, 'counts': {}}
    for run in S:
        res['levels'][run] = {f: level(run, f) for f in ('ours', 'codex')}
        sc = S[run]
        res['counts'][run] = {'rows': sc['rows'], 'n_frames': sc['n_frames'], 'frames_lt1': sc['frames_lt1'],
                              'rows_lt1': sc['rows_lt1'], 'n_vehicles': sc['n_vehicles'],
                              'first_seen_9000': {k: v for k, v in sc['first_seen']['9000'].items() if k.startswith('n_')},
                              'time_sorted': sc['time_sorted'], 'fzp_sha256': sc['fzp_sha256'], 'fzp': sc['fzp'],
                              'frames_ours': sc['frames_ours'], 'frames_codex': sc['frames_codex'],
                              'gap': sc['frame_gap_min_max']}
    for p, (x, y) in PAIRS.items():
        for form in ('ours', 'codex'):
            for s in SEEDS:
                res['pairs']['%s|%s|%s' % (p, form, s)] = diff(x + s, y + s, form)

    # FW_E bin-form cells (vehicle-frames x 5 s / 3600)
    def fwe(run, conv):
        win_all = [0.0] * 10
        win_59 = [0.0] * 10
        for w, b, c in S[run]['fwe_cells_' + conv]:
            if 0 <= w < 10:
                win_all[w] += c * 5.0 / 3600.0
                if b in CELL59_BINS:
                    win_59[w] += c * 5.0 / 3600.0
        b900 = S[run]['links_bin900']
        win_fwe7 = [sum(b900.get(k, [0.0] * 10)[w] for k in FWE7) * 5.0 / 3600.0 for w in range(10)]
        return {'chain_all': win_all, 'cell59': win_59, 'fwe7_bin': win_fwe7}

    for conv in ('cum', 'geom'):
        for run in S:
            res['fwe']['%s|%s' % (conv, run)] = fwe(run, conv)
    for p, (x, y) in PAIRS.items():
        for s in SEEDS:
            for conv in ('cum', 'geom'):
                A, B = res['fwe']['%s|%s' % (conv, x + s)], res['fwe']['%s|%s' % (conv, y + s)]
                d = {k: [A[k][i] - B[k][i] for i in range(10)] for k in A}
                d['cell59_900end'] = sum(d['cell59'][1:])
                d['cell59_all'] = sum(d['cell59'])
                d['fwe7_bin_900end'] = sum(d['fwe7_bin'][1:])
                d['rest_900end'] = d['fwe7_bin_900end'] - d['cell59_900end']
                res['fwe']['%s|%s|%s' % (p, conv, s)] = d
    for s in SEEDS:
        r = {}
        fo = res['pairs']['FO-NC3|ours|' + s]['FWE7']
        bb = res['pairs']['B-NC3|ours|' + s]['FWE7']
        foc = res['pairs']['FO-NC3|codex|' + s]['FWE7']
        bbc = res['pairs']['B-NC3|codex|' + s]['FWE7']
        r['ours'] = fo / bb
        r['codex'] = foc / bbc
        for conv in ('cum', 'geom'):
            f59 = res['fwe']['FO-NC3|%s|%s' % (conv, s)]
            b59 = res['fwe']['B-NC3|%s|%s' % (conv, s)]
            r['ours_minus_cell59_900end_' + conv] = (fo - f59['cell59_900end']) / (bb - b59['cell59_900end'])
            r['ours_minus_cell59_all_' + conv] = (fo - f59['cell59_all']) / (bb - b59['cell59_all'])
            r['bin900end_minus_cell59_' + conv] = f59['rest_900end'] / b59['rest_900end']
        res['ratios'][s] = r
    # scanner cross-check vs VERIFY_B outputs (same FZP files for b / nc / va)
    xmax = {}
    for a in ('b', 'nc', 'va'):
        for s in SEEDS:
            p = os.path.join(VB_OUT, '%s%s.json' % (a, s))
            if not os.path.exists(p):
                xmax[a + s] = 'missing'
                continue
            V = jl(p)
            mine = S[a + s]
            dl = {}
            for f_m, f_v in (('ours', 'ours_9000'), ('codex', 'codex_8100')):
                Lm, Lv = mine['links_' + f_m], V['links'][f_v]
                keys = set(Lm) | set(Lv)
                dl[f_m] = max(abs(Lm.get(k, 0.0) - Lv.get(k, 0.0)) for k in keys)
            ds = max(abs(mine['first_seen'][w][k] - V['first_seen'][w][k]) for w in ('9000', '8100')
                     for k in V['first_seen'][w])
            xmax[a + s] = {'link_max_abs_ours': dl['ours'], 'link_max_abs_codex': dl['codex'], 'first_seen_max_abs': ds,
                           'rows_equal': mine['rows'] == V['rows'], 'vehicles_equal': mine['n_vehicles'] == V['n_vehicles']}
    res['scanner_xcheck'] = xmax
    tmp = out + '.tmp' + str(os.getpid())
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1)
    os.replace(tmp, out)
    print('VF_PAIRS_DONE', flush=True)


if __name__ == '__main__':
    main()
