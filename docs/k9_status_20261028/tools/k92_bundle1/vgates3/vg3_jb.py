"""VerifyGates 2 — J-b recomputed (amendment 24 :326 J-b row, amendment 30 section 4.4).  No harness / driver / judge
import (vg3lib only).

  compare  judged items = every item of G-EB-2, 3, 4, 5, 6, 7, 8, 13, 14 in V4/sa/gates/gates_k91t.json (sha 4e59f61d)
           whose pass_ is not null; new = OUTK/jb/sa/gates/gates_k92t.json.  Same iff the item is present and the
           canonical JSON (sorted keys, float repr) of both values is equal.  PASS iff all 9 gates present and every
           judged item same; DIFF otherwise.  Then vs OUTK/judge/jb.json (verdict, counts, per item).
  raw      a declared subset recomputed from the jb job / capture files (amendment 24 section 5.4 'from raw outputs'),
           value compared with both gates files (canonical JSON):
           G-EB-4 per_state  GRID9 rows [T, model, VISSIM, model - VISSIM]: model = summary blocks[2].fw_w_stock of
                             TL3_<T>_SAF_OBS_H3 (ok true), VISSIM = jb/sa/vissim_ref.json seeds['31'].robs3[T+450].fw_w_stock
           G-EB-4 cell9_nonevent  {T: blocks[2].cell9_v} for T in 900 / 1200 / 1800 / 2250
           G-EB-3 a_bias / a_mae / b_G6_7  TL3m states (seeds 31, 43, 47 with an R-obs validity status 'valid', x
                             GRID9, in that order): model = blocks[0].w_ports.total, obs = vissim_ref
                             seeds[s].states[T].w_ports_T150.total, persistence = |w_ports_T.total - obs|; a = (bias =
                             fsum(m - o) / n, mae = fsum|m - o| / n), a_mae value = mae; b = bias of blocks[0].w_ready vs
                             stop127_T150 and Pearson r (statistics.mean centres, plain sums), n
           G-EB-14 i_init    per judged R-obs seed ROBS61 61 states: SAF capture ok and metadata
                             stopline_approach_install_check present; T = 1 / 150 failed SAF captures with a traceback
                             signature equal to the BASE capture of the same state leave the count; FH 45 (FH seeds x
                             GRID9) the same rule; value {ROBS61, ROBS61_s43, ROBS61_s47, FH: [ok, judged]}
           G-EB-14 ii_iii_posthead  the number of ok ROBS61 / FH captures with readable probes / metadata (value)
Output OUTV/jb.json."""
import math
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vg3lib as V  # noqa: E402

GATES = ('G-EB-2', 'G-EB-3', 'G-EB-4', 'G-EB-5', 'G-EB-6', 'G-EB-7', 'G-EB-8', 'G-EB-13', 'G-EB-14')
OLD = V.V4 / 'sa' / 'gates' / 'gates_k91t.json'
OLD_SHA = '4e59f61d6d1b18ad588e95eaf6f215f44f6c66c981921735073d91f1c6c59b9f'
JB = V.OUTK / 'jb'
NEW = JB / 'sa' / 'gates' / 'gates_k92t.json'
NONEVENT = (900, 1200, 1800, 2250)
FH_SEEDS = (31, 41, 43, 47, 53)


def judged(doc):
    out = {}
    for g in GATES:
        for k, it in ((((doc or {}).get('gates') or {}).get(g) or {}).get('items') or {}).items():
            out[(g, k)] = it
    return out


def summary(lab):
    s = V.rjson(JB / 'sa' / 'jobs' / V.LABEL / lab / 'summary.json')
    return s if isinstance(s, dict) and s.get('ok') else None


def block(s, k):
    b = (s or {}).get('blocks') or []
    return b[k - 1] if s and len(b) >= k else None


def mean(xs):
    xs = list(xs)
    return math.fsum(xs) / len(xs) if xs else None


def pearson(x, y):
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def pair(model, obs):
    xs, ys = [float(a) for a in model], [float(b) for b in obs]
    if not xs:
        return dict(n=0, bias=None, mae=None, r=None, model_mean=None, obs_mean=None)
    d = [a - b for a, b in zip(xs, ys)]
    return dict(n=len(xs), bias=mean(d), mae=mean(abs(v) for v in d), r=pearson(xs, ys), model_mean=mean(xs),
                obs_mean=mean(ys))


def cap(h, T, arm, seed):
    tag = '%06d' % T
    if (h in ('TL3', 'ROBS61') and seed not in (None, 31)) or h == 'FH':
        tag += '_s%d' % seed
    d = JB / 'sa' / 'cap' / V.LABEL / h / tag / arm
    ok = V.rjson(d / 'capture.json')
    if isinstance(ok, dict):
        ok.setdefault('ok', True)
        return d, ok
    fail = V.rjson(d / 'capture_failed.json')
    if isinstance(fail, dict):
        fail['ok'] = False
        return d, fail
    return d, None


def sig(d, T, rec):
    p = d / ('action_%06d.error.txt' % T)
    text = open(V.lp(p), encoding='utf-8', errors='replace').read() if p.is_file() else (rec or {}).get('error')
    return V.tb_signature(text)


def raw_subset():
    vref = V.rjson(JB / 'sa' / 'vissim_ref.json') or {}
    out = {}
    rows, cell9 = [], {}
    for T in V.GRID9:
        b3 = block(summary('TL3_%d_SAF_OBS_H3' % T), 3)
        r = (((vref.get('seeds') or {}).get('31') or {}).get('robs3') or {}).get(str(T + 450))
        if b3 is None or r is None:
            rows.append([T, None, None, None])
            continue
        rows.append([T, b3['fw_w_stock'], r['fw_w_stock'], b3['fw_w_stock'] - r['fw_w_stock']])
        if T in NONEVENT:
            cell9[str(T)] = b3['cell9_v']
    out[('G-EB-4', 'per_state')] = rows
    out[('G-EB-4', 'cell9_nonevent')] = cell9
    seeds = [s for s in (31, 43, 47)
             if (V.rjson(JB / 'sa' / 'tl3m' / ('robs_validity_s%d.json' % s)) or {}).get('status') == 'valid']
    model, obs, pers, ready, stop = [], [], [], [], []
    for s in seeds:
        for T in V.GRID9:
            lab = 'TL3_%d%s_SAF_OBS_H3' % (T, '' if s == 31 else '_s%d' % s)
            sm = summary(lab)
            job = (sm or {}).get('job') or {}
            if sm is not None and (job.get('seed') != s or job.get('harness') != 'TL3'):
                sm = None
            b1 = block(sm, 1)
            ref = (((vref.get('seeds') or {}).get(str(s)) or {}).get('states') or {}).get(str(T))
            if b1 is None or not ref or not ref.get('w_ports_T150') or not ref.get('w_ports_T') \
                    or ref.get('stop127_T150') is None:
                continue
            o = ref['w_ports_T150']['total']
            model.append(b1['w_ports']['total'])
            obs.append(o)
            pers.append(abs(ref['w_ports_T']['total'] - o))
            ready.append(b1['w_ready'])
            stop.append(ref['stop127_T150'])
    a, b = pair(model, obs), pair(ready, stop)
    out[('G-EB-3', 'a_bias')] = a['bias']
    out[('G-EB-3', 'a_mae')] = a['mae']
    out[('G-EB-3', 'b_G6_7')] = {'bias': b['bias'], 'r': b['r'], 'n': b['n']}
    # G-EB-14
    init, n_ii = {}, 0
    for s in seeds:
        key = 'ROBS61' if s == 31 else 'ROBS61_s%d' % s
        init[key] = [0, 0]
        for T in V.ROBS61_T:
            d, c = cap('ROBS61', T, 'SAF', s)
            if T in (1, 150) and not (c and c.get('ok')):
                db, cb = cap('ROBS61', T, 'BASE', s)
                sa_ = sig(d, T, c) if c is not None else None
                sb = sig(db, T, cb) if (cb is not None and not cb.get('ok')) else None
                if sa_ is not None and sa_ == sb and len(sa_[1]) > 0:
                    continue
            init[key][1] += 1
            if c and c.get('ok') and 'metadata' in c and (c.get('metadata') or {}).get(
                    'stopline_approach_install_check') is not None:
                init[key][0] += 1
            if c and c.get('ok') and readable(c):
                n_ii += 1
    init['FH'] = [0, 0]
    for s in FH_SEEDS:
        for T in V.GRID9:
            d, c = cap('FH', T, 'SAF', s)
            init['FH'][1] += 1
            if c and c.get('ok') and 'metadata' in c and (c.get('metadata') or {}).get(
                    'stopline_approach_install_check') is not None:
                init['FH'][0] += 1
                if readable(c):
                    n_ii += 1
    out[('G-EB-14', 'i_init')] = init
    out[('G-EB-14', 'ii_iii_posthead')] = n_ii
    return out, {'seeds_valid': seeds, 'tl3m_states_used': len(model)}


def readable(c):
    if c.get('probes_error'):
        return False
    pr = c.get('probes')
    if not isinstance(pr, dict) or not isinstance(pr.get('provenance'), dict) or \
            (pr.get('records') or {}).get('n10695') is None or 'metadata' not in c:
        return False
    init = (c.get('metadata') or {}).get('stopline_approach_initial') or {}
    return all(init.get(k) is not None for k in ('posthead_veh', 'posthead_receiver_shortfall_veh',
                                                  'posthead_rehome_shortfall_veh'))


def main():
    old_sha = V.sha_file(OLD)
    if old_sha != OLD_SHA:
        raise SystemExit('gates_k91t.json sha differs')
    old, new = V.rjson(OLD), V.rjson(NEW)
    out = {'schema': 'vg3-jb/v1', 'when': V.now(), 'tool_sha256': V.sha_file(Path(__file__)),
           'old_sha256': old_sha, 'new_file': str(NEW), 'new_sha256': V.sha_file(NEW) if NEW.is_file() else None}
    oi, ni = judged(old), judged(new)
    keys = sorted(k for k, it in oi.items() if it.get('pass_') is not None)
    rows, diff = {}, []
    for k in keys:
        n = ni.get(k)
        same = n is not None and V.canon(oi[k].get('value')) == V.canon(n.get('value'))
        rows['%s/%s' % k] = {'same': same, 'pass_old': oi[k].get('pass_'),
                             'pass_new': None if n is None else n.get('pass_')}
        if not same:
            diff.append('%s/%s' % k)
    present = [g for g in GATES if g in ((new or {}).get('gates') or {})]
    verdict = 'INCOMPLETE' if len(present) != len(GATES) else ('PASS' if not diff else 'DIFF')
    out.update(verdict=verdict, n_judged=len(keys), n_same=len(keys) - len(diff), differing=diff, rows=rows,
               gate_verdicts_new={g: (((new or {}).get('gates') or {}).get(g) or {}).get('verdict') for g in GATES},
               gate_verdicts_old={g: (((old or {}).get('gates') or {}).get(g) or {}).get('verdict') for g in GATES},
               pass_flags_equal=all(r['pass_old'] == r['pass_new'] for r in rows.values()))
    try:
        sub, info = raw_subset()
        rs = {}
        for k, v in sub.items():
            rs['%s/%s' % k] = {'equals_new': ni.get(k) is not None and V.canon(v) == V.canon(ni[k].get('value')),
                               'equals_k91t': V.canon(v) == V.canon(oi[k].get('value'))}
        out['raw_subset'] = {'items': rs, 'info': info, 'all_equal_new': all(x['equals_new'] for x in rs.values())}
    except Exception as exc:  # noqa: BLE001
        out['raw_subset'] = {'error': repr(exc)[:300], 'all_equal_new': False}
    rec = V.rjson(V.OUTK / 'judge' / 'jb.json') or {}
    rr = {('%s/%s' % (r.get('gate'), r.get('item'))): r for r in rec.get('rows') or []}
    mism = [k for k, r in rows.items() if (rr.get(k) or {}).get('same') != r['same']]
    out['recorded'] = {'sha256': V.sha_file(V.OUTK / 'judge' / 'jb.json'), 'verdict': rec.get('verdict'),
                       'n_judged_items': rec.get('n_judged_items'), 'n_same': rec.get('n_same'),
                       'new_sha256': rec.get('new_sha256')}
    out['agree_all'] = (rec.get('verdict') == verdict and rec.get('n_judged_items') == len(keys)
                        and rec.get('n_same') == out['n_same'] and not mism and set(rr) == set(rows)
                        and rec.get('new_sha256') == out['new_sha256'])
    out['row_mismatch'] = mism
    V.wjson(V.OUTV / 'jb.json', out)
    print('VG3_JB verdict=%s judged=%d same=%d diff=%s raw_subset_equal=%s agree=%s' % (
        verdict, len(keys), out['n_same'], diff, out['raw_subset'].get('all_equal_new'), out['agree_all']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
