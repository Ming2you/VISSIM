r"""V-A analysis step 2 (amendment 34 sec.8.2, 8.3-1, 8.3-2, 8.3-11, 8.3-13, 8.4): four metrics, Omega split, Omega
outside (a)-(f), two paired differences with their uninserted unions, statistics, label rule, 150 s delta series.
python -B va_metrics.py --profile va|selftest
  reads <scans> va_s<S>, J1 / NC3 scans (sha16-checked), run-end .err (removal links), obs150 err_<T>.jsonl (S7),
  V-A action JSON vsl only (plot lines).  Writes <out>/va_metrics.json, va_per_run.csv, va_paired.csv,
  va_bins_delta.csv, va_bins_delta_A.png, va_bins_delta_B.png.
Pairs (amendment 34 sec.8.2):
  A   = V-A - NC3, union U6(V-A) = V-A 3 + NC3 3 runs
  B   = V-A - J1,  union U9 = V-A 3 + J1 3 + NC3 3 runs
  Bp  = J1 - NC3 re-done on U9 (same column as B)
  J1R = J1 - NC3 on U6(J1) (the "J1 보고 값", = J1_REPORT)
  NC3 anchors per seed in every union.  Union-free rows (1, 2, 3, 3u, 4a, Omega outside (b), split, removals,
  receivers) are the same in every union.  Definitions copied from J1 an_metrics.py (N1F stage0_metrics b1101969 /
  stage0_omega_split).  Removals: reading A = all run-end .err removals (scan err.removals), reading B = removals on
  links outside Omega by the membership file (stage1 membership_inside), both fixed before data."""
import csv
import glob
import io
import json
import os
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

LOCAL_KEYS = ['mainline', 'on_connectors', 'off_connectors', 'on_approaches']
METRICS = [
    ('M1', '① fw_e_main 7링크'), ('M2', '② 동측 국소 19링크'), ('M3', '③ Ω TTT (635)'), ('M3u', '③u urban_omega'),
    ('M4', '④ 전체 + 미삽입'), ('M4a', '④a 전체 링크 TTT (1,236)'), ('M4b', '④b 미삽입 (합집합, NC 앵커)'),
    ('OUT_a', 'Ω 밖 (a) ④ − ③'), ('OUT_b', 'Ω 밖 (b) ④a − ③ (링크만)'),
    ('REM', 'Ω 밖 (d) 차로변경 제거, 읽는 법 A (런 끝 .err 전체)'),
    ('REM_B', 'Ω 밖 (d) 차로변경 제거, 읽는 법 B (소속 파일 기준 Ω 밖 링크만)'),
    ('unins_1098', '④b 중 입력 1098'), ('unins_1099', '④b 중 입력 1099'), ('unins_other', '④b 중 그 밖 입력'),
    ('x_off_receivers_shared', '② 밖: 진출 수신 121/124/126/127'),
]
UNION_DEP = ('M4', 'M4b', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
SPLIT_KEYS = ['fw_e_main', 'fw_w_main', 'onramp', 'offramp_inside', 'urban_omega', 'outside_inside(=0)', 'unknown',
              'omega_total']
UNIONS = {'U6VA': ('va', 'nc3'), 'U9': ('va', 'j1', 'nc3'), 'U6J1': ('j1', 'nc3')}
PAIRS = {'A': ('va', 'nc3', 'U6VA'), 'B': ('va', 'j1', 'U9'), 'Bp': ('j1', 'nc3', 'U9'), 'J1R': ('j1', 'nc3', 'U6J1')}
SERIES_KEYS = ('M1', 'M3', 'M4', 'M4b', 'OUT_a')


def split(sc):
    ro = sc['region_omega_vh']
    out = {'fw_e_main': sum(ro['fw_e_main']), 'fw_w_main': sum(ro['fw_w_main']),
           'onramp': sum(sum(v) for k, v in ro.items() if k.startswith('onramp:')),
           'offramp_inside': sum(ro['offramp']), 'urban_omega': sum(ro['urban_omega']),
           'outside_inside(=0)': sum(ro['outside']), 'unknown': sum(ro.get('unknown', [0]))}
    out['omega_total'] = sc['totals']['omega_ttt_veh_h']
    return out


def s7_late(obs150):
    """S7 late-reported lane-change removals from obs150 err_<T>.jsonl (J1 an_metrics.s7_late, s7_links.py)."""
    first = {}
    rows_total = 0
    files = sorted(glob.glob(os.path.join(obs150, 'err_*.jsonl')))
    for f in files:
        T = int(os.path.basename(f)[4:10])
        with open(f, encoding='utf-8') as h:
            for line in h:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get('kind') != 'lane_change_removal':
                    continue
                rows_total += 1
                key = r.get('byte_offset')
                if key not in first or T < first[key][0]:
                    first[key] = (T, r)
    late = [(T, r) for T, r in first.values() if r['time_sec'] <= T - 150]
    delays = sorted(T - r['time_sec'] for T, r in first.values())
    dl_late = sorted(T - r['time_sec'] for T, r in late)
    return {'jsonl_rows': rows_total, 'unique_removals': len(first), 'duplicates': rows_total - len(first),
            'late': len(late), 'late_frac': len(late) / len(first) if first else None,
            'report_delay_sec_median': statistics.median(delays) if delays else None,
            'report_delay_sec_max': max(delays) if delays else None,
            'late_delay_sec_median': statistics.median(dl_late) if dl_late else None,
            'files': len(files)}


def vsl_times(dec):
    out = {'FW_E': [], 'FW_W': []}
    for T, p in V.action_files(dec):
        v = V.load_json_bytes(p).get('vsl') or {}
        for road in out:
            if any(float(x) < 110.0 for k, x in v.items() if k == road or k.startswith(road + '__')):
                out[road].append(T)
    return out


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    prio = V.set_below_normal()
    C = V.import_stage1()
    import numpy as np
    import stage1_report as R
    sets = C.jload(V.LINK_SETS)['link_sets']
    inside, all_links, _ = C.membership_inside()
    errpath = {}
    loaded = {}
    for s in V.SEEDS:
        for arm in ('va', 'j1', 'nc3'):
            tag = '%s_s%d' % (arm, s)
            d = V.scan_dir(prof, tag)
            loaded[tag] = {'scan': C.jload(os.path.join(d, 'scan.json')),
                           'un': C.jload(os.path.join(d, 'uninserted.json')),
                           'scan_sha256': V.sha(os.path.join(d, 'scan.json')),
                           'un_sha256': V.sha(os.path.join(d, 'uninserted.json')), 'dir': d}
            if loaded[tag]['scan'].get('seed') != s:
                raise SystemExit('seed mismatch %s' % tag)
            errpath[tag] = (prof.va_run(s)['err'] if arm == 'va' else V.j1_run(s)['err'] if arm == 'j1'
                            else V.nc3_run(s)['err'])
    # unions and NC3 anchors (amendment 34 sec.8.2)
    unions, union_src, anchors = {}, {}, {}
    for u, arms in UNIONS.items():
        src = {}
        for s in V.SEEDS:
            for arm in arms:
                tag = '%s_s%d' % (arm, s)
                for k, v in loaded[tag]['un']['inputs'].items():
                    if v.get('queued') or v.get('remain_err', 0) > 0:
                        src.setdefault(k, []).append(tag)
        unions[u] = sorted(src, key=int)
        union_src[u] = src
        anchors[u] = {s: {k: v['anchored_total_generated'] for k, v in loaded['nc3_s%d' % s]['un']['inputs'].items()
                          if k in unions[u]} for s in V.SEEDS}
    sc0 = loaded['nc3_s31']['scan']
    nb, bs = sc0['n_bins'], sc0['bin_sec']
    cut = int(V.T_ACT // bs)
    # removals by membership (reading B) from the run-end .err
    rem = {}
    for tag, p in errpath.items():
        e = C.parse_err(p)
        links = [l for _, _, l in e['removals']]
        err_sha = V.sha(p)
        an_sha = (loaded[tag]['scan'].get('an') or {}).get('err_sha256')
        rem[tag] = {'all': len(links), 'outside_omega': sum(1 for l in links if l not in inside),
                    'inside_omega': sum(1 for l in links if l in inside),
                    'not_in_membership': sum(1 for l in links if l not in all_links),
                    'scan_err_removals': loaded[tag]['scan']['err']['removals'],
                    'err_sha256': err_sha, 'scan_an_err_sha256': an_sha,
                    'err_same_as_scan': (an_sha is None or an_sha == err_sha),
                    'remains': {str(k): v for k, v in e['remains'].items()}}
        if rem[tag]['all'] != rem[tag]['scan_err_removals']:
            raise SystemExit('removal count differs from scan: %s' % tag)
    per_run, bins_of = {}, {}
    for u in UNIONS:
        for s in V.SEEDS:
            for arm in ('va', 'j1', 'nc3'):
                tag = '%s_s%d' % (arm, s)
                d = loaded[tag]
                sc = d['scan']
                series = R.arm_series(sc, d['un'], unions[u], anchors[u][s])
                lv = sc['link_vh']

                def lbins(ids):
                    z = np.zeros(nb)
                    miss = []
                    for i in ids:
                        arr = lv.get(str(i))
                        if arr is None:
                            miss.append(i)
                            continue
                        z = z + np.asarray(arr, float)
                    return z, miss
                parts, missing = {}, {}
                for k in LOCAL_KEYS + ['off_receivers_shared']:
                    parts[k], missing[k] = lbins(sets[k])
                b = {'M1': series['region:fw_e_main'][0], 'M2': sum(parts[k] for k in LOCAL_KEYS),
                     'M3': series['omega_ttt'][0], 'M3u': series['region:urban_omega'][0],
                     'M4': series['all_plus_unins'][0], 'M4a': series['all_ttt'][0], 'M4b': series['unins'][0],
                     'unins_1098': series['unins_1098'][0], 'unins_1099': series['unins_1099'][0],
                     'unins_other': series['unins_other'][0], 'x_off_receivers_shared': parts['off_receivers_shared']}
                b['OUT_a'] = b['M4'] - b['M3']
                b['OUT_b'] = b['M4a'] - b['M3']
                bins_of[(u, tag)] = b
                full = {k: float(v.sum()) for k, v in b.items()}
                full['REM'] = float(sc['err']['removals'])
                full['REM_B'] = float(rem[tag]['outside_omega'])
                fs = sc['frame_series']
                per_run[(u, tag)] = {
                    'union': u, 'tag': tag, 'seed': s, 'arm': arm, 'full': full,
                    'pre900': {k: float(v[:cut].sum()) for k, v in b.items()},
                    'omega_split': split(sc),
                    'checks': {
                        'M1_links_minus_region': float(parts['mainline'].sum() - b['M1'].sum()),
                        'omega_series_vs_totals': float(b['M3'].sum() - sc['totals']['omega_ttt_veh_h']),
                        'all_series_vs_totals': float(b['M4a'].sum() - sc['totals']['all_ttt_veh_h']),
                        'missing_links': {k: v for k, v in missing.items() if v},
                        'frames': sc['frames'], 'unknown_rows': sc['regions']['unknown_links_rows'],
                        'region_counts': sc['regions']['counts'], 'membership_check': sc['regions']['membership_check'],
                        'insertion_attribution': {k: v for k, v in sc['insertion_attribution'].items()
                                                  if k != 'examples_unattributed'}},
                    'end_state': {'in_network_last_frame': fs['all'][-1], 'omega_last_frame': fs['omega'][-1],
                                  'vehicles_seen': sc['vehicles_seen'], 'removals': sc['err']['removals'],
                                  'removals_by_region': sc['err']['removals_by_region'],
                                  'removals_membership': {k: rem[tag][k] for k in ('outside_omega', 'inside_omega',
                                                                                   'not_in_membership')},
                                  'remain_total': sum(sc['err']['remains'].values()), 'remains': sc['err']['remains'],
                                  'unins_own_anchor_total': d['un']['total_veh_h']},
                    'scan_sha256': d['scan_sha256'], 'uninserted_sha256': d['un_sha256'], 'scan_dir': d['dir']}
    # union-free rows must agree across unions (sanity)
    for s in V.SEEDS:
        for arm in ('va', 'j1', 'nc3'):
            tag = '%s_s%d' % (arm, s)
            for k, _ in METRICS:
                if k in UNION_DEP:
                    continue
                vals = [per_run[(u, tag)]['full'][k] for u in UNIONS]
                if max(vals) - min(vals) > 1e-9:
                    raise SystemExit('union-free row differs across unions: %s %s' % (tag, k))
    pairs = {}
    for pk, (a, b0, u) in PAIRS.items():
        deltas = {s: {k: per_run[(u, '%s_s%d' % (a, s))]['full'][k] - per_run[(u, '%s_s%d' % (b0, s))]['full'][k]
                      for k, _ in METRICS} for s in V.SEEDS}
        summary = {}
        for k, _ in METRICS:
            st = V.stats([deltas[s][k] for s in V.SEEDS], [per_run[(u, 'nc3_s%d' % s)]['full'][k] for s in V.SEEDS])
            st['per_seed'] = {str(s): deltas[s][k] for s in V.SEEDS}
            st['base'] = {str(s): per_run[(u, '%s_s%d' % (b0, s))]['full'][k] for s in V.SEEDS}
            st['arm'] = {str(s): per_run[(u, '%s_s%d' % (a, s))]['full'][k] for s in V.SEEDS}
            st['nc'] = {str(s): per_run[(u, 'nc3_s%d' % s)]['full'][k] for s in V.SEEDS}
            summary[k] = st
        split_d = {s: {k: per_run[(u, '%s_s%d' % (a, s))]['omega_split'][k] - per_run[(u, '%s_s%d' % (b0, s))]['omega_split'][k]
                       for k in SPLIT_KEYS} for s in V.SEEDS}
        split_summary = {}
        for k in SPLIT_KEYS:
            st = V.stats([split_d[s][k] for s in V.SEEDS], [per_run[(u, 'nc3_s%d' % s)]['omega_split'][k] for s in V.SEEDS])
            st['per_seed'] = {str(s): split_d[s][k] for s in V.SEEDS}
            st['base'] = {str(s): per_run[(u, '%s_s%d' % (b0, s))]['omega_split'][k] for s in V.SEEDS}
            st['arm'] = {str(s): per_run[(u, '%s_s%d' % (a, s))]['omega_split'][k] for s in V.SEEDS}
            split_summary[k] = st
        labels = {str(s): V.label(deltas[s]) for s in V.SEEDS}
        labels['mean'] = V.label({k: summary[k]['mean'] for k, _ in METRICS})
        pre = {}
        for s in V.SEEDS:
            ra, rb = per_run[(u, '%s_s%d' % (a, s))]['pre900'], per_run[(u, '%s_s%d' % (b0, s))]['pre900']
            pre[str(s)] = max(abs(ra[k] - rb[k]) for k in ra)
        pc = {}
        for s in V.SEEDS:
            p = R.pairing_check(s, loaded['%s_s%d' % (b0, s)]['scan'], loaded['%s_s%d' % (a, s)]['scan'], V.T_ACT)
            sa, sb = loaded['%s_s%d' % (a, s)]['scan'], loaded['%s_s%d' % (b0, s)]['scan']
            p['frames_equal'] = (sa['frames']['n'] == sb['frames']['n'] and sa['frames']['first_sec'] == sb['frames']['first_sec']
                                 and sa['frames']['last_sec'] == sb['frames']['last_sec'])
            p['max_abs_pre900_delta'] = pre[str(s)]
            pc[str(s)] = p
        bd = {}
        for k in SERIES_KEYS:
            bd[k] = {str(s): [round(float(x), 4) for x in (bins_of[(u, '%s_s%d' % (a, s))][k] - bins_of[(u, '%s_s%d' % (b0, s))][k])]
                     for s in V.SEEDS}
            bd[k]['mean'] = [round(float(x), 4) for x in np.mean([bins_of[(u, '%s_s%d' % (a, s))][k] - bins_of[(u, '%s_s%d' % (b0, s))][k]
                                                                   for s in V.SEEDS], axis=0)]
        pairs[pk] = {'arm': a, 'base': b0, 'union': u, 'deltas': {str(s): deltas[s] for s in V.SEEDS},
                     'summary': summary, 'omega_split_delta': {str(s): split_d[s] for s in V.SEEDS},
                     'omega_split_summary': split_summary, 'labels': labels, 'pairing': pc, 'bins_delta': bd}
    # per-input uninserted (NC3 anchor) for every union input, per union
    unins_by_input = {}
    for u in UNIONS:
        tab = {}
        for k in unions[u]:
            tab[k] = {'queued_in': union_src[u][k]}
            for s in V.SEEDS:
                for arm in UNIONS[u]:
                    tag = '%s_s%d' % (arm, s)
                    d = loaded[tag]
                    sc = d['scan']
                    rec = d['un']['inputs'].get(k)
                    if not rec or not rec.get('schedule'):
                        tab[k][tag] = None
                        continue
                    bb, ff = R.U.clipped_series(rec['schedule'], sc['insertions'][k]['entry_times'], anchors[u][s][k],
                                                sc['frames']['first_sec'], sc['frames']['last_sec'],
                                                sc['frame_series']['t'], nb, bs)
                    tab[k][tag] = {'veh_h_nc_anchor': float(bb.sum()), 'max_queue': float(ff.max()),
                                   'max_queue_sec': float(sc['frame_series']['t'][int(np.argmax(ff))]),
                                   'remain_err': rec.get('remain_err'), 'inserted_seen': rec.get('inserted_seen'),
                                   'own_anchor_total': rec.get('anchored_total_generated'), 'own_queued': rec.get('queued'),
                                   'link': rec.get('link'), 'name': rec.get('name')}
        unins_by_input[u] = tab
    s7 = {}
    for s in V.SEEDS:
        s7['va_s%d' % s] = s7_late(prof.va_run(s)['obs150'])
        s7['j1_s%d' % s] = s7_late(V.j1_run(s)['obs150'])
        for arm in ('va', 'j1'):
            s7['%s_s%d' % (arm, s)]['err_removals'] = rem['%s_s%d' % (arm, s)]['all']
    remains = {tag: rem[tag]['remains'] for tag in rem}
    vt = {s: vsl_times(prof.va_run(s)['dec']) for s in V.SEEDS}
    res = {'schema': 'k92-va-metrics/v1', 'profile': prof.name, 'pinned': pin, 'doc': __doc__,
           'script_sha256': V.sha(os.path.abspath(__file__)), 'common_sha256': V.sha(V.__file__),
           'priority': hex(prio), 'link_sets_source': {'path': V.LINK_SETS, 'sha256': V.sha(V.LINK_SETS)},
           'unions': unions, 'union_queued_in': union_src,
           'anchors_nc3': {u: {str(s): anchors[u][s] for s in V.SEEDS} for u in UNIONS},
           't2': V.T2, 'bins_before_900': cut, 'metrics': METRICS, 'union_dependent_rows': UNION_DEP,
           'per_run': {'%s|%s' % k: v for k, v in per_run.items()}, 'pairs': pairs,
           'removals_membership': rem, 'remains_by_run': remains, 's7_late': s7,
           'unins_by_input': unins_by_input, 'vsl_below110_T_va': {str(s): vt[s] for s in V.SEEDS}, 'noise_ref': V.NOISE}
    out = prof.out
    V.jdump(res, os.path.join(out, 'va_metrics.json'))
    with io.open(os.path.join(out, 'va_per_run.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['union', 'tag', 'seed', 'arm'] + [k for k, _ in METRICS] + ['split_' + k for k in SPLIT_KEYS])
        for (u, tag), r in sorted(per_run.items()):
            w.writerow([u, tag, r['seed'], r['arm']] + ['%.4f' % r['full'][k] for k, _ in METRICS] +
                       ['%.4f' % r['omega_split'][k] for k in SPLIT_KEYS])
    with io.open(os.path.join(out, 'va_paired.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pair', 'union', 'seed', 'metric', 'base', 'arm', 'd'])
        for pk, p in pairs.items():
            for s in V.SEEDS:
                for k, _ in METRICS:
                    st = p['summary'][k]
                    w.writerow([pk, p['union'], s, k, '%.4f' % st['base'][str(s)], '%.4f' % st['arm'][str(s)],
                                '%.4f' % st['per_seed'][str(s)]])
    with io.open(os.path.join(out, 'va_bins_delta.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        cols = [(pk, k, s) for pk in ('A', 'B') for k in SERIES_KEYS for s in ('31', '41', '43', 'mean')]
        w.writerow(['bin', 't_start_sec'] + ['%s_d_%s_%s' % (pk, k, ('s' + s) if s != 'mean' else s) for pk, k, s in cols])
        for i in range(nb):
            w.writerow([i, i * bs] + ['%.4f' % pairs[pk]['bins_delta'][k][s][i] for pk, k, s in cols])
    plot = {}
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        colors = {'31': '#1f77b4', '41': '#ff7f0e', '43': '#2ca02c', 'mean': '#000000'}
        t = np.arange(nb) * bs + bs / 2.0
        for pk, title in (('A', 'V-A - NC3, union U6(V-A)'), ('B', 'V-A - J1, union U9')):
            fig, axes = plt.subplots(4, 1, figsize=(11, 11), sharex=True)
            for ax, k, lab in zip(axes, ('M1', 'M3', 'M4', 'OUT_a'),
                                  ('d(1) fw_e_main', 'd(3) Omega TTT', 'd(4) all + uninserted', 'd Omega outside (a)')):
                for s in ('31', '41', '43', 'mean'):
                    ax.plot(t, pairs[pk]['bins_delta'][k][s], color=colors[s], lw=1.6 if s == 'mean' else 0.9,
                            label=('v3c3-s%s' % s) if s != 'mean' else '3-seed mean')
                for s in ('31', '41', '43'):
                    for T in vt[int(s)]['FW_E']:
                        ax.axvline(T, color=colors[s], alpha=0.25, lw=0.8, ls='--')
                    for T in vt[int(s)]['FW_W']:
                        ax.axvline(T, color=colors[s], alpha=0.25, lw=0.8, ls=':')
                ax.axhline(0, color='grey', lw=0.6)
                ax.axvline(900, color='grey', lw=0.6)
                ax.set_ylabel('%s\n(veh.h per 150 s)' % lab)
            axes[0].legend(fontsize=8, ncol=4)
            axes[-1].set_xlabel('simulation time (s); dashed = V-A decision T with FW_E VSL < 110, dotted = FW_W VSL < 110')
            fig.suptitle('%s per 150 s bin (report only, no verdict)' % title)
            fig.tight_layout()
            fig.savefig(os.path.join(out, 'va_bins_delta_%s.png' % pk), dpi=110)
            plt.close(fig)
            plot[pk] = 'ok'
    except Exception as e:  # noqa: BLE001
        plot['error'] = 'failed: %s' % e
    res['plot'] = plot
    V.jdump(res, os.path.join(out, 'va_metrics.json'))
    print('plot', plot)
    print('unions', {u: len(v) for u, v in unions.items()})
    for pk in PAIRS:
        print('pair', pk, 'pairing', {s: (p['ok'], p['max_abs_pre900_delta']) for s, p in pairs[pk]['pairing'].items()})
    print('done')


if __name__ == '__main__':
    main()
