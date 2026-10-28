r"""V-A analysis step 5 (amendment 34 sec.8.3-3 link 174 chain and input 1083, sec.8.3-6 SC109 east links; J1_REPORT
sec.5 form).  Runs after va_metrics.py and va_fzp_local.py (reads their outputs).
python -B va_followup.py --profile va|selftest  ->  <out>/va_followup.json
  (1) links 21, 10112, 174, 10280, 10281, 173: geometry / region / Omega, stage-1 link_vh full and from 4350 s
      (bins 29-59) for V-A, J1, NC3; link 174 FZP frame count mean / max / time of max (va_local.json).
  (2) input 1083: run-end remain, inserted count, reconstructed delay on the NC3 anchor (stage1 clipped_series), max
      queue (frame time value) and its time, the first 150 s sample (frames 29::30) where the 0-clipped queue
      difference exceeds 10 for (V-A - NC3) and (V-A - J1) (unclipped difference reported apart), entries per 150 s bin
      difference from bin 28 (4200 s) for both pairs, and the input-1083 share of d(4b) for pair A (union U6(V-A)) and
      pair B (union U9) (0 when 1083 is outside that union).
  (3) SC109 east: links 1220000704 / 1220000803 stage-1 link_vh full and 1800-7200 s (bins 12-47), FZP frame mean / max
      (va_local.json), d(V-A - NC3) and d(V-A - J1) with the J1 statistics.  Model SC109_E_out: none (no recorder in
      the closed-loop runs; not estimated)."""
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

ARMS = ('va', 'j1', 'nc3')


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    t0 = time.time()
    prio = V.set_below_normal()
    C = V.import_stage1()
    import numpy as np
    import stage1_report as R
    U = R.U
    M = V.jload(os.path.join(prof.out, 'va_metrics.json'))
    L = V.jload(os.path.join(prof.out, 'va_local.json'))
    scans, uns = {}, {}
    for s in V.SEEDS:
        for arm in ARMS:
            tag = '%s_s%d' % (arm, s)
            d = V.scan_dir(prof, tag)
            scans[tag] = V.jload(os.path.join(d, 'scan.json'))
            uns[tag] = V.jload(os.path.join(d, 'uninserted.json'))
    net = C.load_network(prof.va_run(31)['inpx'])
    inside, _, _ = C.membership_inside()
    reg_of = {}
    for r, ls in scans['va_s31']['regions']['links'].items():
        for l in ls:
            reg_of[l] = r

    def rinfo(l):
        x = net['links'][l]
        return {'link': l, 'length_m': round(x['length_m'], 1), 'lanes': x['lanes'], 'connector': x['connector'],
                'from_link': x.get('from_link'), 'to_link': x.get('to_link'), 'inside_omega': l in inside,
                'region': reg_of.get(l, 'urban_omega' if l in inside else 'outside')}
    res = {'schema': 'k92-va-followup/v1', 'profile': prof.name, 'pinned': pin, 'priority': hex(prio)}
    # (1) link 174 chain
    chain = {'links': [rinfo(l) for l in V.LINK174_CHAIN], 'link_vh': {}, 'fzp_174': {}}
    for l in V.LINK174_CHAIN:
        for s in V.SEEDS:
            for arm in ARMS:
                tag = '%s_s%d' % (arm, s)
                arr = scans[tag]['link_vh'].get(str(l), [0.0] * scans[tag]['n_bins'])
                chain['link_vh'].setdefault(str(l), {})[tag] = {'full': sum(arr), 'from_4350': sum(arr[29:])}
    for s in V.SEEDS:
        for arm in ARMS:
            tag = '%s_s%d' % (arm, s)
            chain['fzp_174'][tag] = L['runs'][tag]['occ_174']
    res['link174_chain'] = chain
    # (2) input 1083
    inp = [i for i in net['inputs'] if i['no'] == 1083][0]
    i1083 = {'input': {k: inp[k] for k in ('no', 'link', 'name')},
             'schedule_vph': [(r['start'], r['volume_vph']) for r in inp['intervals']], 'link': rinfo(inp['link']),
             'in_union': {u: ('1083' in M['unions'][u]) for u in M['unions']}, 'runs': {}, 'pairs': {}}
    q = {}
    for s in V.SEEDS:
        anchor = uns['nc3_s%d' % s]['inputs']['1083']['anchored_total_generated']
        for arm in ARMS:
            tag = '%s_s%d' % (arm, s)
            sc, un = scans[tag], uns[tag]
            rec = un['inputs']['1083']
            ent = sc['insertions']['1083']['entry_times']
            ft = np.asarray(sc['frame_series']['t'], float)
            bb, ff = U.clipped_series(rec['schedule'], ent, anchor, sc['frames']['first_sec'], sc['frames']['last_sec'],
                                      ft, sc['n_bins'], sc['bin_sec'])
            LT = float(U.cumulative(rec['schedule'], [U.C.T_END])[0])
            raw = (anchor / LT if LT > 0 else 0.0) * U.cumulative(rec['schedule'], ft) - np.searchsorted(
                np.asarray(ent, float), ft, side='right')
            k = int(np.argmax(ff))
            q[tag] = (ft, ff, raw)
            i1083['runs'][tag] = {'remain_err': int(sc['err']['remains'].get('1083', 0)),
                                  'inserted': int(sc['insertions']['1083']['count']),
                                  'delay_veh_h_nc3_anchor': float(bb.sum()), 'max_queue_frame': float(ff[k]),
                                  'max_queue_frame_t': float(ft[k]), 'own_queued': rec.get('queued'),
                                  'entries_per_bin': list(sc['insertions']['1083']['per_bin_by_entry'])}
        for pk, base in (('A', 'nc3'), ('B', 'j1')):
            fa, qa, ra = q['va_s%d' % s]
            fb, qb, rb = q['%s_s%d' % (base, s)]
            sel = np.arange(29, len(fa), 30)
            dq = qa[sel] - qb[sel]
            over = np.nonzero(dq > 10)[0]
            draw = ra[sel] - rb[sel]
            over_raw = np.nonzero(draw > 10)[0]
            eb = (np.asarray(i1083['runs']['va_s%d' % s]['entries_per_bin']) -
                  np.asarray(i1083['runs']['%s_s%d' % (base, s)]['entries_per_bin']))
            u = 'U6VA' if pk == 'A' else 'U9'
            ui = M['unins_by_input'][u].get('1083')
            share = (ui['va_s%d' % s]['veh_h_nc_anchor'] - ui['%s_s%d' % (base, s)]['veh_h_nc_anchor']) if ui else 0.0
            i1083['pairs'].setdefault(pk, {})['s%d' % s] = {
                'first_gt10_clipped_t': float(fa[sel][over[0]]) if over.size else None,
                'first_gt10_raw_t': float(fa[sel][over_raw[0]]) if over_raw.size else None,
                'entries_diff_from_bin28': [int(x) for x in eb[28:]], 'entries_diff_sum_bins_0_27': int(eb[:28].sum()),
                'entries_diff_sum_from_bin28': int(eb[28:].sum()),
                'd4b_share_1083': share, 'union': u, 'in_union': ui is not None}
    res['input_1083'] = i1083
    # (3) SC109 east links
    east = {'links': [rinfo(l) for l in V.EAST_LINKS], 'link_vh': {}, 'fzp': {}, 'paired': {},
            'model_SC109_E_out': '없음 (폐루프 런에 기록기가 없음, 추정하지 않음)'}
    for l in V.EAST_LINKS:
        for s in V.SEEDS:
            for arm in ARMS:
                tag = '%s_s%d' % (arm, s)
                arr = scans[tag]['link_vh'].get(str(l), [0.0] * scans[tag]['n_bins'])
                east['link_vh'].setdefault(str(l), {})[tag] = {'full': sum(arr), 'P_1800_7200': sum(arr[12:48])}
                east['fzp'].setdefault(str(l), {})[tag] = L['runs'][tag]['occ_%d' % l]
        for pk, base in (('A', 'nc3'), ('B', 'j1')):
            for win in ('full', 'P_1800_7200'):
                a = [east['link_vh'][str(l)]['va_s%d' % s][win] for s in V.SEEDS]
                b = [east['link_vh'][str(l)]['%s_s%d' % (base, s)][win] for s in V.SEEDS]
                nc = [east['link_vh'][str(l)]['nc3_s%d' % s][win] for s in V.SEEDS]
                st = V.stats([x - y for x, y in zip(a, b)], nc)
                st.update({'arm': a, 'base': b, 'per_seed': [x - y for x, y in zip(a, b)]})
                east['paired'].setdefault(pk, {})['%d.link_vh.%s' % (l, win)] = st
    res['sc109_east'] = east
    res['elapsed_sec'] = round(time.time() - t0, 1)
    V.jdump(res, os.path.join(prof.out, 'va_followup.json'))
    print('elapsed', res['elapsed_sec'])


if __name__ == '__main__':
    main()
