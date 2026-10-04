"""S3 31-site counting runs (K8-0b; port of the scratch amend1/s3/tools/run_s3.py). Same worker / adapter / env as
jobs.py and full.py; only the site hook differs (<k8_gates>/s3site instead of <k8_gates>/site), with the site table
chosen by --anchors (k81: K7/K8-1 lines, k82: the K8-2 commit's lines). One process at a time, BELOW_NORMAL.

    python -B s3run.py [--root R] [--out O] [--robs D] --anchors k81|k82 [--dry-run] job <T> <capv> <label> <act> <mode> [patches]
        -> <out>/out/<T>/jobs/<label>/{job.pickle, result.pickle, log.txt, hook/, brief.json}
    python -B s3run.py [--root R] [--out O] [--robs D] --anchors k81|k82 [--dry-run] full <T> <label>
        -> <out>/out/<T>/full_<label>/{action_T.*, adapter_log.txt, hook/, run.json}

capv: capture folder cap_<capv> (capture.py --cap-label);  act: REF | M2ALL;  mode: scalar | ad | ad_full;
patches: worker.py patches (comma list) or '-' (default).
"""
import json
import pickle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402

S3SITE = c.GATES / 's3site'
FW_E = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FW_W = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
ACTIONS = {'REF': 'REFERENCE', 'M2ALL': {'meters': {m: 2 for m in FW_E + FW_W}}}

ap = c.parser(__doc__)
ap.add_argument('--anchors', required=True, choices=('k81', 'k82'), help='S3 hook site table (K8_S3_ANCHORS)')
ap.add_argument('--dry-run', action='store_true', help='print the command line only (writes nothing)')
sub = ap.add_subparsers(dest='cmd', required=True)
j = sub.add_parser('job')
j.add_argument('T', type=int)
j.add_argument('capv')
j.add_argument('label')
j.add_argument('act', choices=tuple(ACTIONS))
j.add_argument('mode', choices=('scalar', 'ad', 'ad_full'))
j.add_argument('patches', nargs='?', default='-')
f = sub.add_parser('full')
f.add_argument('T', type=int)
f.add_argument('label')
args = ap.parse_args()
c.apply(args)


def env(hook_dir):
    e = c.base_env(hook_dir=hook_dir)
    parts = e['PYTHONPATH'].split(';')
    assert parts[0] == str(c.SITE), parts[0]
    parts[0] = str(S3SITE)
    e['PYTHONPATH'] = ';'.join(parts)
    e['K8_S3_ANCHORS'] = args.anchors
    return e


def _f(x):
    return float(getattr(x, 'value', x))


if args.cmd == 'job':
    T = args.T
    base = c.RESULTS / f'{T:06d}'
    tpl = base / f'cap_{args.capv}' / 'template.pickle'
    out = base / 'jobs' / args.label
    job = {'template': str(tpl), 'action': ACTIONS[args.act], 'mode': args.mode,
           'patches': [] if args.patches == '-' else args.patches.split(',')}
    cmd = [c.PY, '-B', str(c.TOOLS / 'worker.py'), str(out / 'job.pickle'), str(out / 'result.pickle')]
    if args.dry_run:
        print('DRY s3 job anchors=%s' % args.anchors, json.dumps(job, default=str),
              'template_exists' if tpl.is_file() else 'TEMPLATE_MISSING')
        print('  ' + ' '.join(cmd))
        raise SystemExit(0)
    c.lower_priority()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'job.pickle').write_bytes(pickle.dumps(job, protocol=5))
    code, wall = c.run(cmd, out / 'log.txt', env(out / 'hook'))
    res = pickle.loads((out / 'result.pickle').read_bytes()) if (out / 'result.pickle').is_file() else {'error': 'no result'}
    trace = res.get('trace') or {}
    brief = {'T': T, 'cap': args.capv, 'label': args.label, 'act': args.act, 'mode': args.mode, 'patches': job['patches'],
             'anchors': args.anchors, 'root': str(c.R), 'exit': code, 'wall': wall,
             'objective_repr': repr(res.get('objective_veh_h')),
             'costs_repr': [repr(x) for x in res.get('costs') or []],
             'resources_repr': [repr(_f(x)) for x in res.get('resources') or []],
             'max_primal_state_error': res.get('max_primal_state_error'),
             'complete_primal_state_match': res.get('complete_primal_state_match'),
             'trace_event_counts': trace.get('event_counts'),
             'kind_service_calls': len(res.get('kind_service') or []),
             'patched': res.get('patched'), 'worker_wall_sec': res.get('wall_sec'),
             'error': (res.get('error') or '')[-3000:]}
    (out / 'brief.json').write_text(json.dumps(brief, indent=1, default=str), encoding='utf-8')
    print(f'S3JOB T={T} cap={args.capv} label={args.label} act={args.act} mode={args.mode} anchors={args.anchors} '
          f'exit={code} wall={wall} objective={res.get("objective_veh_h")!r} '
          f'state_error={res.get("max_primal_state_error")!r} err={"yes" if res.get("error") else "no"}', flush=True)
    raise SystemExit(1 if code or res.get('error') else 0)

T = args.T
replay = c.REPLAYS / f'{T:06d}'
out = c.RESULTS / f'{T:06d}' / f'full_{args.label}'
if args.dry_run:
    if not (replay / 'replay_manifest.json').is_file():
        print(f'DRY T={T}: replay missing {replay} (run prep.py first)')
        raise SystemExit(0)
    sec, a = c.adapter_args(replay, out)
    print(f'DRY s3 full T={T} anchors={args.anchors} out={out}')
    print('  ' + ' '.join([c.PY, '-B', str(c.ADAPTER)] + a))
    raise SystemExit(0)
c.lower_priority()
out.mkdir(parents=True, exist_ok=True)
sec, a = c.adapter_args(replay, out)
code, wall = c.run([c.PY, '-B', str(c.ADAPTER)] + a, out / 'adapter_log.txt', env(out / 'hook'))
rec = {'T': T, 'label': args.label, 'anchors': args.anchors, 'root': str(c.R), 'exit': code, 'wall': wall}
try:
    d = json.loads((out / f'action_{T:06d}.json').read_text(encoding='utf-8'))
    m = d.get('metadata', {})
    rec['held_objective'] = (m.get('joint_leader_selection') or {}).get('held_objective')
except Exception as e:
    rec['read_error'] = repr(e)
prog = out / f'action_{T:06d}.joint.progress.jsonl'
if prog.is_file():
    last = [json.loads(x) for x in prog.read_text(encoding='utf-8').splitlines() if x.strip()]
    for r in reversed(last):
        if 'objective' in r or 'held_objective' in r:
            rec['progress_last'] = {k: r.get(k) for k in ('stage', 'objective', 'held_objective')}
            rec['progress_last_repr'] = {k: repr(r.get(k)) for k in ('objective', 'held_objective')}
            break
(out / 'run.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
print('S3FULL', json.dumps(rec), flush=True)
raise SystemExit(1 if code else 0)
