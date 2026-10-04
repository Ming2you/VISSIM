"""Run one K8 worker job (fresh process, BELOW_NORMAL, passive hooks):

    python -B jobs.py [--root R] [--out O] [--robs D] [--dry-run] <T> <capvariant> <label> <mode> <action> <patches>
        -> <out>/out/<T>/jobs/<label>/{job.pickle, result.pickle, log.txt, hook/, brief.json}

capvariant: capture folder cap_<capvariant> (capture.py);  mode: scalar | ad | ad_full (non-surrogate, worker.py)
action: REF | M2ALL | M2E | M2W | M5ALL ;  patches: comma list of worker.py patches (s1, s3, s3f, own_off) or '-'"""
import json
import pickle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402

FW_E = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
FW_W = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
ACTIONS = {'REF': 'REFERENCE', 'M2ALL': {'meters': {m: 2 for m in FW_E + FW_W}},
           'M2E': {'meters': {m: 2 for m in FW_E}}, 'M2W': {'meters': {m: 2 for m in FW_W}},
           'M5ALL': {'meters': {m: 5 for m in FW_E + FW_W}}}
ap = c.parser(__doc__)
ap.add_argument('T', type=int)
ap.add_argument('capv')
ap.add_argument('label')
ap.add_argument('mode', choices=('scalar', 'ad', 'ad_full'))
ap.add_argument('act', choices=tuple(ACTIONS))
ap.add_argument('patches')
ap.add_argument('--dry-run', action='store_true', help='print the job and the worker command only (writes nothing)')
args = ap.parse_args()
c.apply(args)
T, capv, label, mode, act, patches = args.T, args.capv, args.label, args.mode, args.act, args.patches
base = c.RESULTS / f'{T:06d}'
tpl = base / f'cap_{capv}' / 'template.pickle'
out = base / 'jobs' / label
job = {'template': str(tpl), 'action': ACTIONS[act], 'mode': mode,
       'patches': [] if patches == '-' else patches.split(',')}
if args.dry_run:
    print('DRY job', json.dumps(job, default=str), 'template_exists' if tpl.is_file() else 'TEMPLATE_MISSING')
    print('  ' + ' '.join([c.PY, '-B', str(c.TOOLS / 'worker.py'), str(out / 'job.pickle'), str(out / 'result.pickle')]))
    raise SystemExit(0)
c.lower_priority()
out.mkdir(parents=True, exist_ok=True)
(out / 'job.pickle').write_bytes(pickle.dumps(job, protocol=5))
hook = out / 'hook'
code, wall = c.run([c.PY, '-B', str(c.TOOLS / 'worker.py'), str(out / 'job.pickle'), str(out / 'result.pickle')],
                   out / 'log.txt', c.base_env(hook_dir=hook))
res = pickle.loads((out / 'result.pickle').read_bytes()) if (out / 'result.pickle').is_file() else {'error': 'no result'}
brief = {k: res.get(k) for k in ('objective_veh_h', 'patched', 'wall_sec', 'out_keys', 'surrogate_keys')}
brief['error'] = (res.get('error') or '')[-1500:]
brief['costs_sum'] = sum(res.get('costs') or [])
(out / 'brief.json').write_text(json.dumps(brief, indent=1, default=str), encoding='utf-8')
print(f'JOB T={T} cap={capv} label={label} mode={mode} act={act} patches={patches} exit={code} wall={wall} '
      f'objective={res.get("objective_veh_h")!r} err={"yes" if res.get("error") else "no"}', flush=True)
