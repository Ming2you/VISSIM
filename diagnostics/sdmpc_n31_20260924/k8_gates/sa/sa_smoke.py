"""FH smoke checks H-0 ... H-5 (+ H-2b) on precomputed outputs (K8 PREDECL §3.1 table; AMENDMENT_1 §3.1 replaces H-2b
and H-5).  Pure function of files; writes JSON + markdown.

    python -B sa_smoke.py [--root R] [--out O] [--tree k86] [--dry-run]
        -> <out>/sa/gates/smoke_<tree>.{json,md}

ID    criterion (declared)                                                     inputs
H-0   transplant disabled (hook installed, BASE harness) = TL3: numeric        compare/h0_<tree>.json (sa_compare.py)
      fields differ 0
H-1   s31 FZP island vs R-obs3 raw at the same T: 10491/10481/127/129 counts   FH captures seed 31, frame T (record
      +-1, 127 per-lane contiguous queue +-2; >= 8 of 9 states                 before = R-obs3 merged, after = FZP)
H-2   after the transplant: capture completed (seed_from_projection and the    all FH captures (both arms)
      lane plant ran; LOR assert_mirrors ran), port mirror (storage
      occupancy = port stock), island stock = FZP target (sum provenance per
      island link / port = FZP count), all +-1e-9
H-2b  cross seed s41 @2700 -> s31 template: reservation sum = seeded residual  FH captures s41 T2700 (BASE, SAF)
      (BASE), FW_W/FW_E density = bin_frame target, exit share = FZP value,
      port mirror, SA lane stock sum = N_127 + N_10777 - |A| + N_tail129 +
      M_other + N_shortfall_kept (SA arm; K8 amendment 5 section 3 replaces
      "FZP 127+10777 - post-head", amendment 7 section 1 adds the post-head
      share kept on 127 for want of receiver room; the terms are recorded
      separately by the capture probe and must equal SA's own
      tail129_port_veh / other_link_ready_veh / posthead_veh /
      posthead_receiver_shortfall_veh / posthead_rehome_shortfall_veh, and
      N_shortfall_kept = |A| - the 127 receiver provenance + the W member
      queue on 10695; amendment 8 section 1: the 10695 share beyond its
      receiver's room is kept the same way, M_other read net of it), no
      in_SC1001_W share on 10695 (SA arm), SC1001_to_SC2002 10695 share +
      the kept 10695 share = FZP 10695 count (SA) / share = half (BASE);
      all +-1e-9
H-3   s31 self transplant: T+150 W+ports vs TL3 +-2 veh in >= 8 of 9 states   FH *_TLS jobs (seed 31) vs TL3 OBS H3
      (every arm with jobs must pass; sa_common OPERATIONALISATIONS)
H-4   the same job twice: bit identical                                        compare/h4_<tree>.json
H-5   same FZP island into the T-150, T, T+150 templates: T+150 W+ports range   h5 jobs (judging arm, H1)
      <= 5 veh in >= 40 of 45 states; G-EB-3 pre-exclusion of states whose W
      receiving-limited seconds exceed 10 % of green seconds (center frame,
      block 1); N5: <= 5 of 45 excluded, else G-EB-3 FAILS
Verdict: SMOKE_PASS when every H passes; else SMOKE_FAIL (one fix attempt, <= 3 h; then FH G-EB-3/6 go to report and
the judgement moves to TL3/DP, PREDECL §3.1 end - a human decision, not taken here)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402
import sa_inputs as si  # noqa: E402

c = sc.c
TOL = sc.MASS_TOL


def verdict(flags):
    if any(f is None for f in flags):
        return None
    return all(flags)


def h0(I):
    d = I.compare(f'h0_{I.tree}')
    if d is None:
        return {'pass': None, 'missing': ['compare h0']}
    rows, flags = [], []
    for label, r in d['result'].items():
        ok = None if 'missing' in r else (r['equal'] and r.get('ok', False))
        flags.append(ok)
        rows.append([label, r.get('differ_excl_timing'), r.get('only_a'), r.get('only_b'), ok])
    return {'pass': verdict(flags) if flags else None, 'rows': rows,
            'header': ['job', 'differ excl timing', 'only FH0', 'only TL3', 'pass']}


def _cap_any(I, T, seed=31, frame_T=None):
    for arm in ('BASE', 'SAF', 'SAG'):
        cap = I.cap('FH', T, arm, seed=seed, frame_T=frame_T)
        if cap and cap.get('transplant'):
            return arm, cap
    return None, None


def h1(I):
    rows, n_ok, n = [], 0, 0
    for T in sc.GRID9:
        arm, cap = _cap_any(I, T)
        if cap is None:
            rows.append([T, None, None, None, None])
            continue
        tr = cap['transplant']
        b, a = tr.get('before') or {}, tr.get('after') or {}
        dc = {k: abs(a['counts'][k] - b['counts'][k]) for k in ('10491', '10481', '127', '129')}
        qa, qb = a.get('contiguous_127_by_lane') or {}, b.get('contiguous_127_by_lane') or {}
        lanes = sorted(set(qa) | set(qb))
        dq = {k: abs(float(qa.get(k, 0.0)) - float(qb.get(k, 0.0))) for k in lanes
              if not isinstance(qa.get(k, 0.0), str) and not isinstance(qb.get(k, 0.0), str)}
        ok = all(v <= sc.H1_COUNT_TOL for v in dc.values()) and all(v <= sc.H1_LANE_Q_TOL for v in dq.values())
        n += 1
        n_ok += ok
        rows.append([T, arm, dc, dq, ok])
    return {'pass': (n_ok >= sc.H1_MIN_STATES) if n == len(sc.GRID9) else None, 'n_ok': n_ok, 'n': n, 'rows': rows,
            'header': ['T', 'arm', '|d count| 10491/10481/127/129', '|d 127 lane queue|', 'state ok']}


def _sum_prov(cap, link):
    return sum(float(v) for v in ((cap.get('probes') or {}).get('provenance') or {}).get(link, {}).values())


def h2(I):
    rows, flags = [], []
    for seed, T in I.fh_states():
        for arm in ('BASE', 'SAF'):
            cap = I.cap('FH', T, arm, seed=seed)
            if cap is None:
                flags.append(None)
                rows.append([seed, T, arm, None, None, None, None])
                continue
            if not cap.get('ok'):              # amendment 7 §2: FAIL only for a runtime traceback, else INCOMPLETE
                flags.append(False if sc.failed_in_runtime(cap) else None)
                rows.append([seed, T, arm, False, None, None, [sc.record_kind(cap), sc.record_site(cap)]])
                continue
            pr = cap.get('probes') or {}
            tr = cap.get('transplant') or {}
            added = tr.get('added_by_link') or {}
            mirror = all(abs(pr['occupancy'][sc.PORTS[off]] - pr['ports'][off]['stock']) <= TOL for off in sc.PORTS)
            island = {k: _sum_prov(cap, k) - float(added.get(k, 0)) for k in sc.ISLAND_LINKS + sc.PORT_LINKS}
            island_ok = all(abs(v) <= TOL for v in island.values())
            ok = mirror and island_ok
            flags.append(ok)
            rows.append([seed, T, arm, True, mirror, {k: v for k, v in island.items() if abs(v) > TOL}, ok])
    return {'pass': verdict(flags) if flags else None, 'rows': rows,
            'header': ['seed', 'T', 'arm', 'captured', 'port mirror', 'island stock - FZP (bad only)', 'ok']}


def h2b(I):
    out, flags = {}, []
    for arm in ('BASE', 'SAF'):
        cap = I.cap('FH', 2700, arm, seed=41)
        if cap is None or not cap.get('ok'):
            out[arm] = {'captured': None if cap is None else False}
            flags.append(None if cap is None else False)
            continue
        pr, tr = cap['probes'], cap['transplant']
        chk = {}
        if arm == 'BASE':
            split = pr.get('seed_split') or {}
            seed_sum = sum(float((row or {}).get(sc.GATE, {}).get('moving', 0.0))
                           + float((row or {}).get(sc.GATE, {}).get('stopped', 0.0))
                           for link, row in split.items() if link != 'unattributed')
            un = split.get('unattributed')
            if isinstance(un, dict):          # K8-4 ce8fe80 _split_seed_storage: {storage: {moving, stopped}}
                row = un.get(sc.GATE)
                if isinstance(row, dict):
                    seed_sum += float(row.get('moving', 0.0)) + float(row.get('stopped', 0.0))
                elif row is not None:
                    seed_sum += float(row)
            res = sum(pr['arrival'][sc.GATE].values())
            chk['reservation_eq_seeded_residual'] = (res, seed_sum, abs(res - seed_sum) <= TOL
                                                     if pr.get('seed_split_present') else None)
        exp = tr.get('expected_density') or {}
        for road in ('FW_W', 'FW_E'):
            e, a = exp.get(road), pr['freeway_density'].get(road)
            ok = (isinstance(e, list) and a is not None and len(e) == len(a)
                  and all(abs(x - y) <= TOL for x, y in zip(e, a)))
            chk['density_' + road] = (None, None, ok)
        ex = tr.get('exit_shares') or {}
        lfr = pr.get('lane_freeway_off_splits') or {}
        for off, row in ex.items():
            got = lfr.get(off)
            ok = bool(row.get('replaced')) and (got is None or abs(float(got) - float(row['ratio'])) <= TOL)
            chk['exit_share_' + off] = (row.get('ratio'), got, ok)
        chk['port_mirror'] = (None, None, all(abs(pr['occupancy'][sc.PORTS[o]] - pr['ports'][o]['stock']) <= TOL
                                              for o in sc.PORTS))
        rec = pr.get('records') or {}
        p10695 = (pr['provenance'].get('10695') or {})
        share = float(p10695.get('storage:SC1001_to_SC2002', 0.0))
        n10695 = float(rec.get('n10695', 0))
        if arm == 'SAF':
            lanes = sum(float(v) for v in (pr.get('sa') or {}).get('stock', {}).values())
            target = lane_stock_target(rec)
            chk['sa_lane_stock_eq_fzp'] = (lanes, target, None if target is None else abs(lanes - target) <= TOL)
            init = (cap.get('metadata') or {}).get('stopline_approach_initial')
            if target is None or not init:
                chk['sa_terms_eq_probe'] = (None, None, None)
            else:
                recv, on_c = rec.get('recv127'), rec.get('rehome_member')
                pairs = {'n_tail129': (init.get('tail129_port_veh'), rec['n_tail129']),
                         'm_other': (init.get('other_link_ready_veh'), rec['m_other']),
                         'posthead': (init.get('posthead_veh'), rec['posthead_127']),
                         'shortfall_kept': (init.get('posthead_receiver_shortfall_veh'), rec['n_shortfall_kept']),
                         # amendment 8 section 1: the (d) share SA reports = the W member queue read on 10695
                         'rehome_shortfall': (init.get('posthead_rehome_shortfall_veh'), on_c),
                         'shortfall_eq_posthead_minus_receivers_plus_10695':
                             (rec['n_shortfall_kept'],
                              None if recv is None or on_c is None
                              else float(rec['posthead_127']) - float(recv) + float(on_c))}
                chk['sa_terms_eq_probe'] = (pairs, None, all(a is not None and b is not None
                                                             and abs(float(a) - float(b)) <= TOL
                                                             for a, b in pairs.values()))
            chk['no_10695_gate_share'] = (p10695.get('storage:' + sc.GATE), 0.0,
                                          'storage:' + sc.GATE not in p10695)
            kept10695 = sum(float(v) for k, v in p10695.items()          # amendment 8 section 1: the kept share
                            if k.startswith('movement:') and k[len('movement:'):] in sc.W_MEMBERS)
            chk['10695_share_full'] = (share + kept10695, n10695, abs(share + kept10695 - n10695) <= TOL)
        else:
            chk['10695_share_half'] = (share, n10695 / 2.0, abs(share - n10695 / 2.0) <= TOL)
        # a check without its inputs (e.g. an identity term not recorded) is INCOMPLETE, a failed check FAILS
        ok = False if any(v[2] is False for v in chk.values()) else (
            None if any(v[2] is None for v in chk.values()) else True)
        flags.append(ok)
        out[arm] = {'checks': chk, 'pass': ok}
    return {'pass': verdict(flags), 'arms': out}


def lane_stock_target(rec):
    """K8 amendment 5 section 3 + amendment 7 section 1: N_127 + N_10777 - |A| + N_tail129 + M_other +
    N_shortfall_kept; None when a term was not recorded."""
    keys = ('n127', 'n10777', 'posthead_127', 'n_tail129', 'm_other', 'n_shortfall_kept')
    if not rec or any(rec.get(k) is None for k in keys):
        return None
    return (float(rec['n127']) + float(rec['n10777']) - float(rec['posthead_127']) + float(rec['n_tail129'])
            + float(rec['m_other']) + float(rec['n_shortfall_kept']))


def h3(I):
    res, flags = {}, []
    for arm in ('BASE', 'SAF'):
        rows, n_ok, n = [], 0, 0
        for T in sc.GRID9:
            fh = I.jobx('FH', T, arm, 'OBS', 3, seed=31, variant='TLS')
            tl = I.jobx('TL3', T, arm, 'OBS', 3)
            a, b = si.w_ports_total(fh), si.w_ports_total(tl)
            if a is None or b is None:
                rows.append([T, a, b, None])
                continue
            ok = abs(a - b) <= sc.H3_TOL
            n += 1
            n_ok += ok
            rows.append([T, a, b, ok])
        if n == 0:
            continue
        p = (n_ok >= sc.H3_MIN_STATES) if n == len(sc.GRID9) else None
        flags.append(p)
        res[arm] = {'n_ok': n_ok, 'n': n, 'pass': p, 'rows': rows}
    return {'pass': verdict(flags) if flags else None, 'arms': res,
            'header': ['T', 'FH self W+ports T+150', 'TL3 W+ports T+150', '|d| <= 2']}


def h4(I):
    d = I.compare(f'h4_{I.tree}')
    if d is None or 'missing' in d['result']:
        return {'pass': None, 'missing': ['compare h4']}
    r = d['result']
    return {'pass': bool(r.get('bit_identical')), 'differ_excl_timing': r.get('differ_excl_timing'),
            'strings_differ': r.get('strings_differ'), 'objective_repr': r.get('objective_repr')}


def h5(I, arm=sc.JUDGING_ARM):
    rows, n_ok, n, excluded, no_green = [], 0, 0, [], []
    for seed, T in I.fh_states():
        vals = []
        for f in (T - 150, T, T + 150):
            vals.append(si.w_ports_total(I.jobx('FH', T, arm, 'OBS', 1, seed=seed, frame_T=f)))
        center = si.block(I.jobx('FH', T, arm, 'OBS', 1, seed=seed, frame_T=T), 1)
        share = None
        if center is not None:
            g = sum(center['w_green_sec'].values())
            lim = sum(center['w_recv_limited_sec'].values())
            if g > 0:                      # no green second recorded = recorder missing (never a 0 share)
                share = lim / g
                if share > sc.H5_RECV_SHARE:
                    excluded.append([seed, T])
            else:
                no_green.append([seed, T])
        if any(v is None for v in vals):
            rows.append([seed, T, vals, None, share, None])
            continue
        rng = max(vals) - min(vals)
        ok = rng <= sc.H5_RANGE_MAX
        n += 1
        n_ok += ok
        rows.append([seed, T, vals, rng, share, ok])
    complete = n == len(I.fh_states()) and not no_green
    return {'pass': (n_ok >= sc.H5_MIN_STATES) if complete else None, 'n_ok': n_ok, 'n': n, 'rows': rows,
            'excluded_G_EB_3': excluded, 'n_excluded': len(excluded), 'no_green_recorded': no_green,
            'n5_exclusion_ok': len(excluded) <= sc.H5_EXCLUDE_MAX if complete else None,
            'header': ['seed', 'T', 'W+ports T+150 at frames T-150/T/T+150', 'range', 'recv-limited share', 'ok']}


def write_md(path, res):
    lines = [f'# FH smoke ({res["tree"]})', '', f'verdict: **{res["verdict"]}**', '']
    for key in ('H-0', 'H-1', 'H-2', 'H-2b', 'H-3', 'H-4', 'H-5'):
        r = res['checks'][key]
        lines.append(f'## {key}: {"PASS" if r.get("pass") else ("INCOMPLETE" if r.get("pass") is None else "FAIL")}')
        if r.get('header') and r.get('rows'):
            lines.append(sc.md_table(r['header'], r['rows']))
        elif key == 'H-3':
            for arm, row in (r.get('arms') or {}).items():
                lines.append(f'### {arm}: {row["n_ok"]}/{row["n"]}')
                lines.append(sc.md_table(r['header'], row['rows']))
        else:
            lines.append('```\n' + str({k: v for k, v in r.items() if k not in ('rows',)})[:3000] + '\n```')
        lines.append('')
    lines.append(f'G-EB-3 pre-exclusions (H-5): {res["checks"]["H-5"].get("excluded_G_EB_3")}')
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def run(tree):
    I = si.Inputs(tree)
    checks = {'H-0': h0(I), 'H-1': h1(I), 'H-2': h2(I), 'H-2b': h2b(I), 'H-3': h3(I), 'H-4': h4(I), 'H-5': h5(I)}
    flags = [r.get('pass') for r in checks.values()]
    v = 'SMOKE_PASS' if all(f is True for f in flags) else ('INCOMPLETE' if any(f is None for f in flags)
                                                            and not any(f is False for f in flags) else 'SMOKE_FAIL')
    return {'schema': 'k8-sa-smoke/v1', 'tree': tree, 'verdict': v, 'checks': checks,
            'missing_inputs': sorted(set(I.missing))}


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--tree', default='k86')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    dest = sc.sa_out() / 'gates' / f'smoke_{args.tree}.json'
    if args.dry_run:
        print('DRY smoke ->', dest)
        return 0
    res = run(args.tree)
    sc.write_json(dest, res)
    write_md(dest.with_suffix('.md'), res)
    print('SA_SMOKE', res['verdict'], '->', dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
