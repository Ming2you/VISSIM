"""G-EB-11(a) wall-clock pairs with no VISSIM running (K8b-0; K8_PREDECLARATION_AMENDMENT_16 r2 section 5.3.1, user
decision D-K8b-2 Q8).  Diagnostics only; reads job folders, starts the same worker as sa_jobs.py for reruns.

    python -B sa_wallpairs.py [--root R] [--out O] --tree T status            (writes <out>/sa/wallpairs_<T>.json)
    python -B sa_wallpairs.py [...] --tree T rerun [--poll-min 10] [--max-wait-h 72]

Pairs (the declared G-EB-11(a) set, unchanged): FH 45 = seeds 31/41/43/47/53 x GRID9, H3 OBS; TL3 s31 18 = GRID9 x
{OBS, A1}, H3; each = (BASE label, SAF label) of sa_common.job_label.  Each started job writes vissim_counts.json
(sa_jobs.run_job: VISSIM process count right before the worker starts and right after it ends; Get-Process, read only).
Clean pair: the four counts BASE pre, BASE post, SAF pre, SAF post are all known and 0 (the declared three instants
"before BASE, between BASE and SAF, after SAF", the middle one read on both sides).
Value of a pair (fixed before any data, section 5.3.1 r2): the first run when it is clean; else the FIRST clean rerun
under jobs/<T>_wall/<label>/ (BASE then SAF, consecutive, started only when VISSIM count is 0, polled every
--poll-min minutes; a VISSIM process of another session is never touched).  A rerun that is not clean is moved aside
(<label>.stale_<k>) and the pair waits again; a clean pair is never rerun; the choice reads VISSIM counts only, never a
wall value.  A clean rerun must equal its first run in every numeric and string leaf except timing (sa_compare.flatten
/ compare_flat, H-4 method; label, tree and paths excluded) -- otherwise the pair is 'rerun_mismatch' (G-EB-11(a)
FAIL -> STOP, section 5.3.1).  Until all 63 pairs have a clean value G-EB-11(a) is INCOMPLETE (sa_gates.g11)."""
import json
import os
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c
H3 = 3
EXCLUDE_STRING_KEYS = ('/job/label', '/job/tree', '/job/template', '/job/forecast_long')


def pairs():
    """[(kind, seed, T, entry, base_label, saf_label)] of the declared 63 pairs (FH 45 then TL3 18)."""
    out = []
    for s in sc.FH_SEEDS:
        for T in sc.GRID9:
            out.append(('FH', s, T, 'OBS', sc.job_label('FH', T, 'BASE', 'OBS', H3, seed=s),
                        sc.job_label('FH', T, sc.JUDGING_ARM, 'OBS', H3, seed=s)))
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            out.append(('TL3', 31, T, entry, sc.job_label('TL3', T, 'BASE', entry, H3),
                        sc.job_label('TL3', T, sc.JUDGING_ARM, entry, H3)))
    return out


def wall_tree(tree):
    return f'{tree}_wall'


def counts(folder):
    rec = sc.read_json(Path(folder) / 'vissim_counts.json')
    return rec if isinstance(rec, dict) else None


def clean(base_dir, saf_dir):
    a, b = counts(base_dir), counts(saf_dir)
    if a is None or b is None:
        return False, 'no vissim_counts.json'
    vals = [a.get('vissim_count_pre'), a.get('vissim_count_post'), b.get('vissim_count_pre'),
            b.get('vissim_count_post')]
    if any(v is None for v in vals):
        return False, 'unknown VISSIM count'
    return all(v == 0 for v in vals), 'counts %s' % vals


def _ok_summary(folder):
    s = sc.read_json(Path(folder) / 'summary.json')
    return s if isinstance(s, dict) and s.get('ok') else None


def identical(first, again):
    """H-4 method: every numeric leaf (timing excluded) and every string leaf except label / tree / paths equal."""
    import sa_compare as cmp
    sa_, sb_ = {}, {}
    row = cmp.compare_flat(cmp.flatten(first, strings=sa_), cmp.flatten(again, strings=sb_))
    strings = sorted(k for k in set(sa_) | set(sb_)
                     if sa_.get(k) != sb_.get(k) and not any(k.startswith(x) for x in EXCLUDE_STRING_KEYS)
                     and not any(s in k.lower() for s in cmp.SKIP))
    ok = bool(row['equal'] and not strings and first.get('objective_repr') == again.get('objective_repr'))
    return ok, {'differ_excl_timing': row['differ_excl_timing'], 'only_a': row['only_a'], 'only_b': row['only_b'],
                'strings_differ': strings[:20], 'examples': row['examples'][:5]}


def select(tree):
    """Pair values by the section 5.3.1 rule: [{pair, source, clean, base_wall, saf_wall, ratio, identity}]."""
    rows = []
    for kind, seed, T, entry, bl, sl in pairs():
        row = {'kind': kind, 'seed': seed, 'T': T, 'entry': entry, 'base': bl, 'saf': sl, 'source': None,
               'ratio': None}
        bd, sd = sc.job_dir(tree, bl), sc.job_dir(tree, sl)
        a, b = _ok_summary(bd), _ok_summary(sd)
        row['first_present'] = a is not None and b is not None
        ok, why = clean(bd, sd)
        row['first_clean'], row['first_counts'] = ok, why
        if row['first_present'] and ok:
            row.update(source='first', base_wall=a['wall_sec'], saf_wall=b['wall_sec'],
                       ratio=b['wall_sec'] / a['wall_sec'])
            rows.append(row)
            continue
        wb, ws = sc.job_dir(wall_tree(tree), bl), sc.job_dir(wall_tree(tree), sl)
        ra, rb = _ok_summary(wb), _ok_summary(ws)
        rok, rwhy = clean(wb, ws)
        row['rerun_counts'] = rwhy
        if row['first_present'] and ra is not None and rb is not None and rok:
            ia, da = identical(a, ra)
            ib, db = identical(b, rb)
            row['identity'] = {'base': da, 'saf': db, 'ok': ia and ib}
            if ia and ib:
                row.update(source='rerun', base_wall=ra['wall_sec'], saf_wall=rb['wall_sec'],
                           ratio=rb['wall_sec'] / ra['wall_sec'])
            else:
                row['source'] = 'rerun_mismatch'
        rows.append(row)
    return rows


def write_status(tree):
    rows = select(tree)
    rec = {'schema': 'k8b-wallpairs/v1', 'tree': tree, 'n_pairs': len(rows),
           'n_clean_values': sum(1 for r in rows if r['source'] in ('first', 'rerun')),
           'n_rerun_mismatch': sum(1 for r in rows if r['source'] == 'rerun_mismatch'),
           'pairs': rows, 'rule': __doc__.split('Clean pair:', 1)[1]}
    sc.write_json(sc.sa_out() / f'wallpairs_{tree}.json', rec)
    print(f'SA_WALLPAIRS {tree}: clean values {rec["n_clean_values"]}/{len(rows)}, rerun mismatch '
          f'{rec["n_rerun_mismatch"]}', flush=True)
    return rec


def _set_aside(folder):
    folder = Path(folder)
    if not folder.exists():
        return
    k = 1
    while folder.with_name(f'{folder.name}.stale_{k}').exists():
        k += 1
    os.replace(folder, folder.with_name(f'{folder.name}.stale_{k}'))


def _run_one(tree, label, seq, invocation):
    """The first run's job dict (its job.pickle) rerun into jobs/<tree>_wall/<label>/ (same worker and env rule as
    sa_jobs.run_job; the capture inputs are those of the first run)."""
    src = sc.job_dir(tree, label)
    job = pickle.loads((src / 'job.pickle').read_bytes())
    out = sc.job_dir(wall_tree(tree), label)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'job.pickle').write_bytes(pickle.dumps(job, protocol=5))
    env = sc.base_env_for(job.get('seed') if job.get('harness') == 'TL3' else None)
    pre, t0 = sc.vissim_count(), time.time()
    code, wall = c.run([c.PY, '-B', str(HERE / 'sa_worker.py'), str(out / 'job.pickle'), str(out / 'result.pickle')],
                       out / 'log.txt', env)
    sc.write_json(out / 'vissim_counts.json', {'schema': 'k8b-vissim-counts/v1', 'label': label,
                                               'arm': job['arm'], 'invocation': invocation, 'seq': seq,
                                               'vissim_count_pre': pre, 'vissim_count_post': sc.vissim_count(),
                                               'start': t0, 'end': time.time(), 'exit': code, 'rerun_of': str(src)})
    print(f'SA_WALL_RERUN {label} exit={code} wall={wall}', flush=True)
    return code


def rerun(tree, poll_min, max_wait_h):
    invocation = '%s_%d' % (time.strftime('%Y%m%d_%H%M%S'), os.getpid())
    seq = 0
    deadline = time.time() + max_wait_h * 3600.0
    while True:
        todo = [r for r in select(tree) if r['source'] is None and r['first_present']]
        if not todo:
            break
        if time.time() > deadline:
            print(f'SA_WALL_DEADLINE {len(todo)} pairs still without a clean value', flush=True)
            break
        if sc.vissim_count() != 0:
            print(f'SA_WALL_WAIT VISSIM running ({time.strftime("%H:%M:%S")}); next check in {poll_min} min',
                  flush=True)
            time.sleep(poll_min * 60.0)
            continue
        r = todo[0]
        for lab in (r['base'], r['saf']):
            _set_aside(sc.job_dir(wall_tree(tree), lab))
        seq += 1
        _run_one(tree, r['base'], seq, invocation)
        seq += 1
        _run_one(tree, r['saf'], seq, invocation)
        ok, why = clean(sc.job_dir(wall_tree(tree), r['base']), sc.job_dir(wall_tree(tree), r['saf']))
        if not ok:
            print(f'SA_WALL_UNCLEAN {r["base"]} / {r["saf"]}: {why}; set aside, will retry', flush=True)
            for lab in (r['base'], r['saf']):
                _set_aside(sc.job_dir(wall_tree(tree), lab))
    return write_status(tree)


def main():
    ap = c.parser(__doc__)
    ap.add_argument('what', choices=('status', 'rerun'))
    ap.add_argument('--tree', required=True)
    ap.add_argument('--poll-min', type=float, default=10.0)
    ap.add_argument('--max-wait-h', type=float, default=72.0)
    args = ap.parse_args()
    c.apply(args)
    if args.what == 'status':
        write_status(args.tree)
        return 0
    c.lower_priority()
    rerun(args.tree, args.poll_min, args.max_wait_h)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
