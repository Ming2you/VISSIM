"""VerifyGates 2 — J-0 recomputed (amendment 24 :324 J-0 row, amendment 30 section 5.1 reading).  No harness /
driver / judge import (vg3lib only; template.pickle read by a stub unpickler, no project module imported).

States: TL3 v3c3-s31 / s43 / s47 x GRID9 (27), DP 17 (DP_T, s31), ROBS61 of R-obs3 v3c3-s31 (61) = 105.
Sides: SAF-K91 = OUTK/ja/sa/cap/k92t/<H>/<tag>/SAF, SAF-K92b1 = OUTK/jb/sa/cap/k92t/<H>/<tag>/SAF
(tag = T as 6 digits, + _s<seed> for TL3 / ROBS61 of s43 / s47).
Per state:
  record    capture.json (ok unless its ok is false) else capture_failed.json (failed) else missing -> INCOMPLETE.
  failed    both failed, ROBS61, T in {1, 150}, equal traceback signature (exception line + runtime frames, >= 1
            runtime frame; action_<T>.error.txt else the record error text) -> PASS (identical failure, counted in
            61/61 per amendment 30 section 5.1); any other failure -> FAIL.
  ok        (a) metadata k8b_p1 k8b_p2 k8b_p2_init k8b_p4 k9_w1 k9_w2a k9_f17b canonical JSON equal;
            (b) SA state: metadata stopline_approach_install_check, stopline_approach_initial, probes sa, ports,
                records, provenance['127'], occupancy['SC1001_W_out'] canonical JSON equal;
            (c) template owned[0].cfg.network.movement_capacity_by_movement_veh_h: differing keys = {W} (+ L exactly when
                the SAF-K91 L value < s), SAF-K92b1 W repr 5209.8, L repr = s when L differs (amendment 24 4.3 G-K1);
            (d) install_check present with passed true on both sides.
  J-0 PASS iff 105 states, all PASS and initialized + identical failures over ROBS61 = 61.
Then per state verdict vs OUTK/judge/j0.json.  Output OUTV/j0.json."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402


def cdir(root, h, T, seed):
    tag = '%06d' % T
    if h in ('TL3', 'ROBS61') and seed not in (None, 31):
        tag += '_s%d' % seed
    return Path(root) / 'sa' / 'cap' / V.LABEL / h / tag / 'SAF'


def record(d):
    ok = V.rjson(d / 'capture.json')
    if isinstance(ok, dict):
        return ok, ('ok' if ok.get('ok') is not False else 'failed')
    fail = V.rjson(d / 'capture_failed.json')
    if isinstance(fail, dict):
        return fail, 'failed'
    return None, 'missing'


def signature(d, T, rec):
    p = d / ('action_%06d.error.txt' % int(T))
    if p.is_file():
        text = open(V.lp(p), encoding='utf-8', errors='replace').read()
    else:
        text = (rec or {}).get('error')
    return V.tb_signature(text)


def sa_state(rec):
    md, pr = rec.get('metadata') or {}, rec.get('probes') or {}
    return {'install_check': md.get('stopline_approach_install_check'), 'initial': md.get('stopline_approach_initial'),
            'sa': pr.get('sa'), 'ports': pr.get('ports'), 'records': pr.get('records'),
            'provenance_127': (pr.get('provenance') or {}).get('127'),
            'occupancy_SC1001_W_out': (pr.get('occupancy') or {}).get('SC1001_W_out')}


def state(h, T, seed):
    da, db = cdir(V.OUTK / 'ja', h, T, seed), cdir(V.OUTK / 'jb', h, T, seed)
    ra, ka = record(da)
    rb, kb = record(db)
    row = {'outcome': [ka, kb]}
    if 'missing' in (ka, kb):
        row['verdict'] = 'INCOMPLETE'
        return row
    if 'failed' in (ka, kb):
        if ka == kb == 'failed' and h == 'ROBS61' and int(T) in (1, 150):
            sa_, sb = signature(da, T, ra), signature(db, T, rb)
            same = sa_ is not None and sa_ == sb and len(sa_[1]) > 0
            row.update(identical_failure=same, exception=(sa_[0][:160] if sa_ else None),
                       runtime_frames=(len(sa_[1]) if sa_ else 0))
            row['verdict'] = 'PASS' if same else 'FAIL'
            row['init_count'] = 'identical_failure' if same else 'failure'
        else:
            row['verdict'] = 'FAIL'
        return row
    ma, mb = ra.get('metadata') or {}, rb.get('metadata') or {}
    row['meta7'] = {k: V.canon(ma.get(k)) == V.canon(mb.get(k)) for k in V.META7}
    row['meta7_present'] = {k: [k in ma, k in mb] for k in V.META7}
    a, b = sa_state(ra), sa_state(rb)
    row['sa_state'] = {k: V.canon(a[k]) == V.canon(b[k]) for k in a}
    ia, ib = a['install_check'] or {}, b['install_check'] or {}
    row['init'] = [bool(ia) and ia.get('passed') is True, bool(ib) and ib.get('passed') is True]
    try:
        ca, cb = V.template_caps(da / 'template.pickle'), V.template_caps(db / 'template.pickle')
        diff = sorted(k for k in set(ca) | set(cb) if V.canon(ca.get(k)) != V.canon(cb.get(k)))
        want = {V.W_KEY}
        la = ca.get(V.L_KEY)
        if la is not None and la < float(V.SEED_REPR):
            want.add(V.L_KEY)
        ok = (set(diff) == want and repr(cb.get(V.W_KEY)) == V.W_REPR
              and (V.L_KEY not in want or repr(cb.get(V.L_KEY)) == V.SEED_REPR))
        row['capacity'] = {'differing': diff, 'expected': sorted(want), 'ok': ok, 'n_keys': [len(ca), len(cb)]}
    except Exception as exc:  # noqa: BLE001
        row['capacity'] = {'ok': None, 'error': repr(exc)[:200]}
    good = (all(row['meta7'].values()) and all(row['sa_state'].values()) and row['init'] == [True, True]
            and row['capacity'].get('ok') is True)
    row['verdict'] = 'INCOMPLETE' if row['capacity'].get('ok') is None else ('PASS' if good else 'FAIL')
    row['init_count'] = 'initialized' if row['init'][1] else 'not_initialized'
    return row


def main():
    states = ([('TL3', T, s) for s in (31, 43, 47) for T in V.GRID9] + [('DP', T, None) for T in V.DP_T]
              + [('ROBS61', T, 31) for T in V.ROBS61_T])
    rows = {}
    for h, T, s in states:
        rows['%s_%d%s' % (h, T, '' if s in (None, 31) else '_s%d' % s)] = state(h, T, s)
    robs = [rows['ROBS61_%d' % T] for T in V.ROBS61_T]
    init61 = {'initialized': sum(1 for r in robs if r.get('init_count') == 'initialized'),
              'identical_failure': sum(1 for r in robs if r.get('init_count') == 'identical_failure')}
    init61['count'] = init61['initialized'] + init61['identical_failure']
    vs = [r['verdict'] for r in rows.values()]
    if 'INCOMPLETE' in vs or len(rows) != 105:
        verdict = 'INCOMPLETE'
    elif all(v == 'PASS' for v in vs) and init61['count'] == 61:
        verdict = 'PASS'
    else:
        verdict = 'FAIL'
    rec = V.rjson(V.OUTK / 'judge' / 'j0.json') or {}
    rrows = rec.get('rows') or {}
    mism = sorted(k for k in rows if (rrows.get(k) or {}).get('verdict') != rows[k]['verdict'])
    cap_mism = sorted(k for k in rows if 'capacity' in rows[k] and 'capacity' in (rrows.get(k) or {}) and
                      sorted((rrows[k]['capacity'] or {}).get('differing') or []) != rows[k]['capacity'].get('differing'))
    out = {'schema': 'vg3-j0/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)), 'verdict': verdict,
           'n_states': len(rows), 'counts': {x: vs.count(x) for x in ('PASS', 'FAIL', 'INCOMPLETE')},
           'robs61_init_61': init61,
           'seed_bound_states': sorted(k for k, r in rows.items() if V.L_KEY in ((r.get('capacity') or {}).get('expected') or [])),
           'identical_failure_states': sorted(k for k, r in rows.items() if r.get('init_count') == 'identical_failure'),
           'rows': rows,
           'recorded': {'sha256': V.sha_file(V.OUTK / 'judge' / 'j0.json'), 'verdict': rec.get('verdict'),
                        'robs61_init_61': rec.get('robs61_init_61'), 'n_states': rec.get('n_states')},
           'verdict_mismatch': mism, 'capacity_set_mismatch': cap_mism}
    out['agree_all'] = (not mism and not cap_mism and rec.get('verdict') == verdict and set(rrows) == set(rows)
                        and (rec.get('robs61_init_61') or {}).get('count') == init61['count'])
    V.wjson(V.OUTV / 'j0.json', out)
    print('VG3_J0 verdict=%s n=%d counts=%s init61=%s agree=%s' % (verdict, len(rows), out['counts'], init61,
                                                                    out['agree_all']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
