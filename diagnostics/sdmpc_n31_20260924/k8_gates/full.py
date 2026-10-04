"""Full deployed SDMPC decision (wu-link, tuning = <root> config_n31_v2.json) from the code root, passive hooks in
every process:

    python -B full.py [--root R] [--out O] [--robs D] [--dry-run] <T> <label>
        -> <out>/out/<T>/full_<label>/{action_T.*, adapter_log.txt, hook/, run.json}
Needs <out>/replays/<T> (prep.py)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402

ap = c.parser(__doc__)
ap.add_argument('T', type=int)
ap.add_argument('label')
ap.add_argument('--dry-run', action='store_true', help='print the adapter command line only (writes nothing)')
args = ap.parse_args()
c.apply(args)
T, label = args.T, args.label
replay = c.REPLAYS / f'{T:06d}'
out = c.RESULTS / f'{T:06d}' / f'full_{label}'
if args.dry_run:
    if not (replay / 'replay_manifest.json').is_file():
        print(f'DRY T={T}: replay missing {replay} (run prep.py first)')
        raise SystemExit(0)
    sec, a = c.adapter_args(replay, out)
    print(f'DRY full T={T} out={out}')
    print('  ' + ' '.join([c.PY, '-B', str(c.ADAPTER)] + a))
    raise SystemExit(0)
c.lower_priority()
out.mkdir(parents=True, exist_ok=True)
sec, a = c.adapter_args(replay, out)
code, wall = c.run([c.PY, '-B', str(c.ADAPTER)] + a, out / 'adapter_log.txt', c.base_env(hook_dir=out / 'hook'))
rec = {'T': T, 'exit': code, 'wall': wall}
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
            break
(out / 'run.json').write_text(json.dumps(rec, indent=1), encoding='utf-8')
print('FULL', json.dumps(rec), flush=True)
