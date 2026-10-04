"""Numeric-field comparisons for G-EB-1, G-EB-9, H-0 and H-4 (reads captures/job results; writes one JSON).

    python -B sa_compare.py [--root R] [--out O] [--tree k86] [--base-tree k85] [--dry-run] <what>

what
  g1   key absent = previous runtime commit (PREDECL §2 K8-6 row, G-EB-1):
         DP 17 BASE templates <tree> vs <base-tree>: every numeric field equal (timing excluded, p3_compare.py rule)
         TL3 9 x {OBS, A1} BASE H3 summaries: objective repr + every numeric field equal
         2700 full decision (full/<tree>/002700_BASE vs <base-tree>): objective / held_objective repr, CSV sha256
  g9   T11 (G-EB-9): DP templates BASE vs SAF (same tree): the 8 meters' service_by_green_veh_h, the capture's
       lane_ramp_head_service_normalisation, SC109's movements (spec + final capacity) byte-identical (canonical JSON)
  h0   H-0: FH captures with the transplant disabled (FH0_* jobs) vs the TL3 jobs (same T, arm, OBS, H3)
  h4   H-4: the two h4 repetitions (rep1, rep2): every numeric field and string field equal (timing excluded)
Output: <out>/sa/compare/<what>_<tree>[_vs_<base-tree>].json.  Templates are unpickled with the code root on sys.path
(the classes of both trees have the same module paths; pickle restores instance dicts).  A job summary whose run ended
on its own missing capture input is read as missing (sc.job_summary, review r4 B-r4-1).
g1 pairs (K8 amendment 7 §2): a pair is compared only when both runs finished ('ok'); a run absent, killed, without
its input or failed without a runtime traceback on either side -> {'missing': ...} (INCOMPLETE); both finished and
exactly one failed in runtime code -> equal False (FAIL); both failed -> {'missing': ...} (equality not readable)."""
import json
import math
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
SKIP = ('wall', 'sec', 'time', 'rss', 'elapsed')     # p3_compare.py timing rule (lower-case substring of the path)
MAX_DEPTH = 60


def flatten(obj, path='', out=None, seen=None, depth=0, strings=None):
    """path -> float for every int/float leaf (bool excluded, p3_compare) of dicts, lists, tuples and plain objects
    (__dict__ / __slots__); Dual-like leaves read .value; cycles and depth > MAX_DEPTH are cut and recorded."""
    out = {} if out is None else out
    seen = set() if seen is None else seen
    if depth > MAX_DEPTH:
        out[path + '#depth_cut'] = float('nan')
        return out
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        out[path] = float(obj)
        return out
    if isinstance(obj, str):
        if strings is not None:
            strings[path] = obj
        return out
    if isinstance(obj, (bytes, bytearray)):
        return out
    if hasattr(obj, 'value') and not callable(getattr(obj, 'value', None)) and not isinstance(obj, (dict, list, tuple)):
        try:
            out[path] = float(obj.value)
            return out
        except Exception:
            pass
    if id(obj) in seen:
        return out
    seen.add(id(obj))
    if isinstance(obj, dict):
        for k in sorted(obj, key=lambda x: (str(type(x)), str(x))):
            flatten(obj[k], f'{path}/{k}', out, seen, depth + 1, strings)
    elif isinstance(obj, (list, tuple)):
        for i, x in enumerate(obj):
            flatten(x, f'{path}[{i}]', out, seen, depth + 1, strings)
    elif isinstance(obj, (set, frozenset)):
        for i, x in enumerate(sorted(obj, key=repr)):
            flatten(x, f'{path}{{{i}}}', out, seen, depth + 1, strings)
    else:
        fields = {}
        if hasattr(obj, '__dict__'):
            fields.update(vars(obj))
        for name in getattr(type(obj), '__slots__', ()) or ():
            if hasattr(obj, name):
                fields[name] = getattr(obj, name)
        for k in sorted(fields):
            flatten(fields[k], f'{path}.{k}', out, seen, depth + 1, strings)
    return out


def compare_flat(fa, fb, *, skip=SKIP):
    common = sorted(set(fa) & set(fb))
    diff = [(k, fa[k], fb[k]) for k in common
            if not (fa[k] == fb[k] or (math.isnan(fa[k]) and math.isnan(fb[k])))]
    real = [d for d in diff if not any(s in d[0].lower() for s in skip)]
    only_a = sorted(k for k in set(fa) - set(fb) if not any(s in k.lower() for s in skip))
    only_b = sorted(k for k in set(fb) - set(fa) if not any(s in k.lower() for s in skip))
    return {'common': len(common), 'differ': len(diff), 'differ_excl_timing': len(real), 'only_a': len(only_a),
            'only_b': len(only_b), 'examples': real[:30], 'only_a_examples': only_a[:20],
            'only_b_examples': only_b[:20], 'equal': not real and not only_a and not only_b}


def load_pickle(path):
    for p in (str(c.R), str(c.R / 'vendor/NumSim-mine'), str(c.R / 'evaluation/controllers')):
        if p not in sys.path:
            sys.path.insert(0, p)
    return pickle.loads(Path(path).read_bytes())


def canon(x):
    return json.dumps(x, sort_keys=True, default=repr)


def pair_state(outcomes):
    """K8 amendment 7 §2 for one G-EB-1 pair {side: outcome}: None = both 'ok' (compare them); else a row --
    {'missing': ...} when a side did not finish (None, 'unfinished') or both failed, {'equal': False, ...} when both
    finished and exactly one failed (a runtime traceback)."""
    if all(o == 'ok' for o in outcomes.values()):
        return None
    row = {'outcome': dict(outcomes)}
    unfinished = [s for s, o in outcomes.items() if o not in ('ok', 'failed')]
    failed = [s for s, o in outcomes.items() if o == 'failed']
    if unfinished:
        row['missing'] = ['%s run not finished (%s)' % (s, outcomes[s]) for s in unfinished]
    elif len(failed) == len(outcomes):
        row['missing'] = ['both runs failed: key-absent equality not readable']
    else:
        row.update(equal=False, objective_equal=False, one_side_failed=failed)
    return row


def _log_text(folder):
    p = Path(folder) / 'adapter_log.txt'
    return p.read_text(encoding='utf-8', errors='replace')[-6000:] if p.is_file() else None


def g1(args):
    out = {'dp': {}, 'tl3': {}, 'full': {}}
    trees = {'tree': args.tree, 'base_tree': args.base_tree}
    for T in sc.DP_T:
        folders = {s: sc.cap_dir(t, 'DP', T, 'BASE') for s, t in trees.items()}
        row = pair_state({s: sc.capture_outcome(d) for s, d in folders.items()})
        if row is not None:
            out['dp'][str(T)] = row
            continue
        a, b = (folders[s] / 'template.pickle' for s in ('tree', 'base_tree'))
        out['dp'][str(T)] = compare_flat(flatten(load_pickle(a)), flatten(load_pickle(b)))
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            label = sc.job_label('TL3', T, 'BASE', entry, 3)
            raw = {s: sc.read_json(sc.job_dir(t, label) / 'summary.json') for s, t in trees.items()}
            row = pair_state({s: sc.job_outcome(raw[s], trees[s]) for s in trees})
            if row is not None:
                out['tl3'][label] = row
                continue
            a, b = raw['tree'], raw['base_tree']
            row = compare_flat(flatten(a), flatten(b))
            row['objective_repr'] = [a.get('objective_repr'), b.get('objective_repr')]
            row['objective_equal'] = a.get('objective_repr') == b.get('objective_repr') and a.get('ok') and b.get('ok')
            out['tl3'][label] = row
    for T in (2700,):
        dirs = {s: sc.full_dir(t, T, 'BASE') for s, t in trees.items()}
        runs = {s: sc.read_json(d / 'run.json') for s, d in dirs.items()}
        row = pair_state({s: sc.full_outcome(runs[s], _log_text(dirs[s])) for s in trees})
        if row is not None:
            out['full'][str(T)] = row
            continue
        ra, rb = runs['tree'], runs['base_tree']
        out['full'][str(T)] = {'objective': [repr(ra.get('objective')), repr(rb.get('objective'))],
                               'held_objective': [repr(ra.get('held_objective')), repr(rb.get('held_objective'))],
                               'csv_sha256': [ra.get('csv_sha256'), rb.get('csv_sha256')],
                               'equal': (repr(ra.get('objective')) == repr(rb.get('objective'))
                                         and repr(ra.get('held_objective')) == repr(rb.get('held_objective'))
                                         and ra.get('exit') == 0 and rb.get('exit') == 0),
                               'csv_equal': ra.get('csv_sha256') == rb.get('csv_sha256')}
    return out


def g9(args):
    out = {}
    for T in sc.DP_T:
        rows = {}
        for arm in ('BASE', 'SAF'):
            d = sc.cap_dir(args.tree, 'DP', T, arm)
            if not (d / 'template.pickle').is_file():
                rows[arm] = None
                continue
            t = load_pickle(d / 'template.pickle')
            net = t['owned'][0].cfg.network
            cap = sc.read_json(d / 'capture.json', {}) or {}
            meters = {r: row.get('service_by_green_veh_h') for r, row in net.physical_ramp_branches['ramps'].items()}
            sc109 = {m: {'spec': spec, 'capacity': net.movement_capacity_by_movement_veh_h.get(m)}
                     for m, spec in net.urban_movements.items() if spec.get('signal') == 'SC109'}
            rows[arm] = {'meters': canon(meters), 'normalisation': canon((cap.get('metadata') or {})
                                                                          .get('lane_ramp_head_service_normalisation')),
                         'sc109': canon(sc109), 'n_meters': len(meters), 'n_sc109': len(sc109)}
        if rows.get('BASE') is None or rows.get('SAF') is None:
            out[str(T)] = {'missing': [a for a, r in rows.items() if r is None]}
            continue
        out[str(T)] = {key: rows['BASE'][key] == rows['SAF'][key] for key in ('meters', 'normalisation', 'sc109')}
        out[str(T)].update(n_meters=rows['BASE']['n_meters'], n_sc109=rows['BASE']['n_sc109'])
    return out


def h0(args):
    out = {}
    for T in sc.GRID9:
        for arm in ('BASE', 'SAF'):
            fl = sc.job_label('FH0', T, arm, 'OBS', 3, seed=31)
            tl = sc.job_label('TL3', T, arm, 'OBS', 3)
            a = sc.job_summary(args.tree, fl)
            b = sc.job_summary(args.tree, tl)
            if not a or not b:
                out[fl] = {'missing': [x for x, y in ((fl, a), (tl, b)) if not y]}
                continue
            row = compare_flat(flatten(a), flatten(b))
            row['objective_repr'] = [a.get('objective_repr'), b.get('objective_repr')]
            row['ok'] = bool(a.get('ok') and b.get('ok'))
            out[fl] = row
    return out


def h4(args):
    labels = [sc.job_label('FH', 2700, sc.JUDGING_ARM, 'OBS', 3, seed=41, rep=r) for r in (1, 2)]
    a, b = (sc.job_summary(args.tree, x) for x in labels)
    if not a or not b:
        return {'missing': labels}
    sa_, sb_ = {}, {}
    row = compare_flat(flatten(a, strings=sa_), flatten(b, strings=sb_))
    strings_diff = sorted(k for k in set(sa_) | set(sb_)
                          if sa_.get(k) != sb_.get(k) and not k.endswith('/label') and not k.startswith('/job/label')
                          and not any(s in k.lower() for s in SKIP))
    row.update(objective_repr=[a.get('objective_repr'), b.get('objective_repr')], strings_differ=strings_diff[:20],
               ok=bool(a.get('ok') and b.get('ok')))
    row['bit_identical'] = row['equal'] and not strings_diff and row['objective_repr'][0] == row['objective_repr'][1]
    return row


def main():
    ap = c.parser(__doc__)
    ap.add_argument('what', choices=('g1', 'g9', 'h0', 'h4'))
    ap.add_argument('--tree', default='k86')
    ap.add_argument('--base-tree', default='k85')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    name = f'{args.what}_{args.tree}' + (f'_vs_{args.base_tree}' if args.what == 'g1' else '')
    dest = sc.sa_out() / 'compare' / f'{name}.json'
    if args.dry_run:
        print(f'DRY compare {args.what} tree={args.tree} base={args.base_tree} -> {dest}')
        return 0
    c.lower_priority()
    res = {'g1': g1, 'g9': g9, 'h0': h0, 'h4': h4}[args.what](args)
    sc.write_json(dest, {'schema': 'k8-sa-compare/v1', 'what': args.what, 'tree': args.tree,
                         'base_tree': args.base_tree, 'result': res})
    print('SA_COMPARE', args.what, '->', dest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
