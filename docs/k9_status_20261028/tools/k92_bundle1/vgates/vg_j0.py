"""VerifyGates: J-0 recomputed from the raw capture files with own code (no harness import; template.pickle read by
the vglib stub unpickler).  Definition = amendment 24 section 5.2 row J-0 (fixed text), with the K9-1 G-EB-14 record
form for T = 1 / 150 (gates_k91t.json G-EB-14 i_init counts 59 capturable states; T = 1 / 150 identical failures are
reported) shown next to the literal reading.

Per state (TL3m 27 = TL3 s31 / s43 / s47 x GRID9, DP 17, ROBS61 61 of s31), SAF-K91 = OUTK/ja, SAF-K92b1 = OUTK/jb:
  meta7    metadata k8b_p1, k8b_p2, k8b_p2_init, k8b_p4, k9_w1, k9_w2a, k9_f17b canonical JSON equal (present both)
  sa       members (install_check), ports, provenance 127, occupancy SC1001_W_out equal; also reported: the rest of
           install_check, stopline_approach_initial (posthead_veh incl.), probes.sa, probes.records
  cap      capacity dict of template.pickle: differing keys = {W} with new repr 5209.8, plus L only when old L < seed
           (then new repr = 1045.1612903225805); every other key bit-equal
  init     install_check.passed true both sides; posthead_veh equal
  failure  both capture_failed: identical iff exception line and runtime frame list (file tail from 'evaluation/',
           line, function) of the LAST traceback in action_<T>.error.txt are equal after the ja/jb root swap
Outputs counts, names and flags only.

    python -B vg_j0.py --dest <json>
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OUTK = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1/k92t')
GRID9 = (900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950)
DP_T = tuple(900 + 450 * k for k in range(17))
ROBS61_T = (1,) + tuple(range(150, 9001, 150))
META7 = ('k8b_p1', 'k8b_p2', 'k8b_p2_init', 'k8b_p4', 'k9_w1', 'k9_w2a', 'k9_f17b')
K92_META = {'k92_w', 'k92_hb', 'k92_hb_seed_binding'}
W_KEY, L_KEY = 'SC109_W_SC108_to_E', 'SC109_W_SC108_to_N_SC16'
W_REPR, SEED = '5209.8', 1045.1612903225805
FRAME = re.compile(r'^\s*File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>.+)$')


def cdir(root, h, T, seed):
    tag = '%06d' % T + ('' if seed in (None, 31) else '_s%d' % seed)
    return root / 'sa' / 'cap' / 'k92t' / h / tag / 'SAF'


def load(d):
    c = V.rjson(d / 'capture.json')
    if isinstance(c, dict):
        return c, ('failed' if c.get('ok') is False else 'ok')
    f = V.rjson(d / 'capture_failed.json')
    if isinstance(f, dict):
        return f, 'failed'
    return None, 'missing'


def signature(d, T):
    p = d / ('action_%06d.error.txt' % T)
    if not p.is_file():
        return None
    text = open(V.lp(p), 'rb').read().decode('utf-8', 'replace')
    text = text.replace('k92t\\ja\\', 'k92t\\<arm>\\').replace('k92t\\jb\\', 'k92t\\<arm>\\')
    at = text.rfind('Traceback (most recent call last):')
    if at < 0:
        return None
    frames, exc = [], None
    for ln in text[at:].splitlines()[1:]:
        m = FRAME.match(ln)
        if m:
            path = m.group('path').replace('\\', '/')
            i = path.find('/evaluation/')
            if i >= 0:
                frames.append((path[i + 1:], int(m.group('line')), m.group('func').strip()))
            continue
        if ln.strip() and ln[:1] not in (' ', '\t'):
            exc = ln.strip()
            break
    if exc is None:
        return None
    return [exc, frames], text


def state(h, T, s):
    da, db = cdir(OUTK / 'ja', h, T, s), cdir(OUTK / 'jb', h, T, s)
    ra, ka = load(da)
    rb, kb = load(db)
    row = {'outcome': [ka, kb]}
    if 'missing' in (ka, kb):
        row['verdict'] = 'INCOMPLETE'
        return row
    if ka == 'failed' or kb == 'failed':
        if ka == kb == 'failed':
            sa, sb = signature(da, T), signature(db, T)
            same_sig = sa is not None and sb is not None and sa[0] == sb[0] and bool(sa[0][1])
            row['identical_failure'] = same_sig
            row['identical_text_after_root_swap'] = sa is not None and sb is not None and sa[1] == sb[1]
            row['n_runtime_frames'] = len(sa[0][1]) if sa else None
            row['exception_head'] = (sa[0][0][:120] if sa else None)
            row['verdict'] = 'IDENTICAL_FAILURE' if same_sig else 'FAIL'
        else:
            row['verdict'] = 'FAIL'
        return row
    ma, mb = ra.get('metadata') or {}, rb.get('metadata') or {}
    row['meta7'] = all(k in ma and k in mb and V.canon(ma[k]) == V.canon(mb[k]) for k in META7)
    ica, icb = ma.get('stopline_approach_install_check') or {}, mb.get('stopline_approach_install_check') or {}
    pa, pb = ra.get('probes') or {}, rb.get('probes') or {}
    core = {'members': (ica.get('members'), icb.get('members')),
            'ports': (pa.get('ports'), pb.get('ports')),
            'provenance_127': ((pa.get('provenance') or {}).get('127'), (pb.get('provenance') or {}).get('127')),
            'occupancy_SC1001_W_out': ((pa.get('occupancy') or {}).get('SC1001_W_out'),
                                       (pb.get('occupancy') or {}).get('SC1001_W_out'))}
    row['sa_core'] = {k: (a is not None and V.canon(a) == V.canon(b)) for k, (a, b) in core.items()}
    more = {'install_check': (ica, icb), 'initial': (ma.get('stopline_approach_initial'),
                                                     mb.get('stopline_approach_initial')),
            'probes_sa': (pa.get('sa'), pb.get('sa')), 'probes_records': (pa.get('records'), pb.get('records'))}
    row['sa_more'] = {k: V.canon(a) == V.canon(b) for k, (a, b) in more.items()}
    ini_a = ma.get('stopline_approach_initial') or {}
    ini_b = mb.get('stopline_approach_initial') or {}
    row['init'] = [ica.get('passed') is True, icb.get('passed') is True]
    row['posthead_equal'] = ('posthead_veh' in ini_a and V.canon(ini_a.get('posthead_veh'))
                             == V.canon(ini_b.get('posthead_veh')))
    try:
        ca, cb = V.template_caps(da / 'template.pickle'), V.template_caps(db / 'template.pickle')
        diff = sorted(k for k in set(ca) | set(cb) if k not in ca or k not in cb or repr(ca[k]) != repr(cb[k]))
        want = {W_KEY}
        bound = ca.get(L_KEY) is not None and ca[L_KEY] < SEED
        if bound:
            want.add(L_KEY)
        row['cap'] = {'differing': diff, 'ok': set(diff) == want and repr(cb.get(W_KEY)) == W_REPR
                      and (not bound or repr(cb.get(L_KEY)) == repr(SEED)), 'seed_bound': bound,
                      'n_keys': [len(ca), len(cb)]}
    except Exception as exc:  # noqa: BLE001
        row['cap'] = {'ok': None, 'error': repr(exc)[:300]}
    row['meta_one_sided_on'] = sorted(set(mb) - set(ma))
    row['meta_one_sided_off'] = sorted(set(ma) - set(mb))
    row['meta_one_sided_ok'] = set(row['meta_one_sided_on']) <= K92_META and not row['meta_one_sided_off']
    row['meta_binding_flag'] = mb.get('k92_hb_seed_binding')
    good = (row['meta7'] and all(row['sa_core'].values()) and all(row['init']) and row['posthead_equal']
            and row['cap'].get('ok') is True)
    row['verdict'] = 'INCOMPLETE' if row['cap'].get('ok') is None else ('PASS' if good else 'FAIL')
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    states = ([('TL3', T, s) for s in (31, 43, 47) for T in GRID9] + [('DP', T, None) for T in DP_T]
              + [('ROBS61', T, 31) for T in ROBS61_T])
    rows = {}
    for h, T, s in states:
        rows['%s_%d%s' % (h, T, '' if s in (None, 31) else '_s%d' % s)] = state(h, T, s)
    v = [r['verdict'] for r in rows.values()]
    robs = {T: rows['ROBS61_%d' % T] for T in ROBS61_T}
    init_robs = sum(1 for r in robs.values() if r['verdict'] == 'PASS')
    ident = sorted(T for T, r in robs.items() if r['verdict'] == 'IDENTICAL_FAILURE')
    other_ok = all(x in ('PASS', 'IDENTICAL_FAILURE') for x in v)
    ident_only_at_1_150 = set(ident) <= {1, 150} and all(rows[k]['verdict'] == 'PASS' for k in rows
                                                         if not k.startswith('ROBS61_'))
    res = {'schema': 'vgates-j0/v1', 'n_states': len(rows),
           'counts': {x: v.count(x) for x in ('PASS', 'IDENTICAL_FAILURE', 'FAIL', 'INCOMPLETE')},
           'robs61': {'initialized': init_robs, 'identical_failure_T': ident},
           'verdict_operationalized': ('PASS' if len(rows) == 105 and other_ok and ident_only_at_1_150
                                       and init_robs + len(ident) == 61 else
                                       ('INCOMPLETE' if 'INCOMPLETE' in v else 'FAIL')),
           'verdict_literal_61_initialized': 'PASS' if init_robs == 61 and all(x == 'PASS' for x in v) else 'FAIL',
           'seed_bound_states': sorted(k for k, r in rows.items() if (r.get('cap') or {}).get('seed_bound')),
           'binding_flag_1_states': sorted(k for k, r in rows.items() if r.get('meta_binding_flag') == 1.0),
           'sa_more_differs': sorted(k for k, r in rows.items() if r.get('sa_more') and not all(r['sa_more'].values())),
           'meta_one_sided_not_k92': sorted(k for k, r in rows.items() if 'meta_one_sided_ok' in r
                                            and not r['meta_one_sided_ok']),
           'failed_states': sorted(k for k, r in rows.items() if r['verdict'] not in ('PASS', 'IDENTICAL_FAILURE')),
           'rows': rows}
    V.wjson(args.dest, res)
    print('VG_J0 op=%s literal=%s counts=%s robs=%s' % (res['verdict_operationalized'],
                                                        res['verdict_literal_61_initialized'], res['counts'],
                                                        res['robs61']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
