"""V-A OfflineGates report-only summary (amendment 34 section 5.1 rows 1-3 "보고만").  Not a judgement; it never changes a
gate status.  Written and fixed (sha) before any gate data.  Reads OUTVA judge results and the GB-9' replay action
metadata; writes OUTVA/judge/va_gates_report.json.  BLIND: paths, kinds, counts, booleans, the fixed seed-binding flag
(0.0 / 1.0) and key names only; no objective / prediction / capacity value is read out.
  row 1 GB-7': per item hits (A items and E1-E4 via gjudge hits_by_item), c7_declared_A count and failing T list,
        union of outside-A paths and of outside-(A or E_K92) paths (paths and kinds only), E_K92 per-entry check counts
        (true / false per condition over the decisions where that path differed).
  row 2 hash A/B: per run c7_declared_A, c7 (A or E_K92), control fields, E_K92 hit ids.
  row 3 GB-9': per T, metadata has k92_w / k92_hb, k92_hb_seed_binding repr, number of head_discharge_floor_173_p4_*
        keys and whether the name is the R-obs3 v3c3-s31 name."""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gcommon as c  # noqa: E402

J = c.OUTV / 'judge'
FLOOR_RE = re.compile(r'head_discharge_floor_173_p4_[0-9a-f]{16}')


def gb7_part():
    g = c.read_json(J / 'gb7_result.json')
    out_a, out_ae, ek_checks, ek_hits = {}, {}, {}, {}
    for r in g['rows']:
        for p, k in r.get('diff_outside_A') or []:
            out_a.setdefault(p, {'kinds': set(), 'T': []})
            out_a[p]['kinds'].add(k)
            out_a[p]['T'].append(r['T'])
        for p, k in r.get('diff_outside_A_EK92') or []:
            out_ae.setdefault(p, {'kinds': set(), 'T': []})
            out_ae[p]['kinds'].add(k)
            out_ae[p]['T'].append(r['T'])
        ek = r.get('ek92') or {}
        for p, x in (ek.get('checks') or {}).items():
            e = ek_checks.setdefault(x['entry'], {'path': p, 'decisions': 0, 'ok_decisions': 0, 'cond_true': {},
                                                  'cond_false': {}})
            e['decisions'] += 1
            e['ok_decisions'] += 1 if x['ok'] else 0
            for cn, v in x['checks'].items():
                d = e['cond_true'] if v else e['cond_false']
                d[cn] = d.get(cn, 0) + 1
        for p, eid in ek.get('hits') or []:
            ek_hits.setdefault(eid, []).append(r['T'])

    def fin(dct):
        return {p: {'kinds': sorted(v['kinds']), 'n_decisions': len(v['T']), 'T_first_last': [min(v['T']), max(v['T'])]}
                for p, v in sorted(dct.items())}
    return {'status': g['status'], 'pass_count': g['pass_count'], 'fails': g['fails'],
            'control_fields_equal_count': g['control_fields_equal_count'], 'csv_equal_count': g['csv_equal_count'],
            'c7_declared_A_count': g['c7_declared_A_count'],
            'c7_declared_A_false_T': [r['T'] for r in g['rows'] if r.get('c7_declared_A') is not True],
            'cond_true_counts': g['cond_true_counts'], 'hits_by_item': g['hits_by_item'],
            'outside_A': fin(out_a), 'outside_A_and_EK92': fin(out_ae), 'ek92_entry_checks': ek_checks,
            'ek92_hit_T': {k: {'n': len(v), 'T_first_last': [min(v), max(v)]} for k, v in sorted(ek_hits.items())},
            'allowed_list': g['allowed_list'], 'ek92_module_sha256': g.get('ek92_module_sha256'),
            'ek92_floor_key': g.get('ek92_floor_key'), 'ek92_root': g.get('ek92_root'),
            'wall_sec_range': g.get('wall_sec_range')}


def hash_part():
    h = c.read_json(J / 'hash_result.json')
    runs = {}
    for T, g in h['groups'].items():
        for seed, r in g['runs'].items():
            runs['%s_%s' % (T, seed)] = {'ok_h': r.get('ok_h'), 'c7_A_or_EK92': r.get('c7_diff_in_A'),
                                         'c7_declared_A': r.get('c7_declared_A'),
                                         'control_fields_equal': r.get('control_fields_equal'),
                                         'env_pythonhashseed': r.get('env_pythonhashseed'),
                                         'ek92_hit_ids': sorted(e for _p, e in (r.get('ek92_hits') or [])),
                                         'outside_A_and_EK92_paths': sorted({p for p, _k in (r.get('diff_outside_A_EK92')
                                                                                              or [])}),
                                         'adapter_wall_sec': r.get('adapter_wall_sec')}
        for k, v in g['pairs'].items():
            runs['%s_pair_%s' % (T, k)] = {'n_outside_V': v['n'], 'csv_same': v['csv_same']}
    return {'status': h['status'], 'runs': runs}


def gb9_part():
    rows = {}
    for T in (900, 2700, 4950, 6300):
        s6 = '%06d' % T
        p = c.OUTV / 'gb9' / 'B' / ('T%s_r1' % s6) / 'replay' / ('action_%s.json' % s6)
        if not p.is_file():
            rows[str(T)] = {'action_present': False}
            continue
        md = c.read_json(p).get('metadata') or {}
        floors = sorted(k for k in md if FLOOR_RE.fullmatch(str(k)))
        b = md.get('k92_hb_seed_binding')
        rows[str(T)] = {'action_present': True, 'has_k92_w': isinstance(md.get('k92_w'), dict),
                        'has_k92_hb': isinstance(md.get('k92_hb'), dict),
                        'k92_hb_seed_binding_repr': repr(b) if type(b) is float and b in (0.0, 1.0) else
                        ('other-type-or-value' if b is not None else None),
                        'floor_key_count': len(floors), 'floor_key_is_robs3_s31_name': floors == [c.FLOOR_KEY]}
    return rows


def main():
    rep = {'schema': 'k92-va-gates-report/v1', 'gb7': gb7_part(), 'hash': hash_part(), 'gb9_k92_metadata': gb9_part()}
    c.write_json(J / 'va_gates_report.json', rep)
    print('VA_GATES_REPORT gb7=%s c7_declared_A=%s/61 outsideA=%d outsideAE=%d hash=%s gb9_meta=%s' % (
        rep['gb7']['status'], rep['gb7']['c7_declared_A_count'], len(rep['gb7']['outside_A']),
        len(rep['gb7']['outside_A_and_EK92']), rep['hash']['status'],
        {k: (v.get('has_k92_w'), v.get('has_k92_hb'), v.get('k92_hb_seed_binding_repr'), v.get('floor_key_count'))
         for k, v in rep['gb9_k92_metadata'].items()}))


if __name__ == '__main__':
    main()
