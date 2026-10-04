"""Capture driver (one adapter process at a time, BELOW_NORMAL):

    python -B capture.py [--root R] [--out O] [--robs D] [--dry-run] [--cap-label L] <variant> <T> [<T> ...]
        -> <out>/out/<T>/cap_<variant>/{template.pickle, capture.json, capture_log.txt}   (cap_<L> with --cap-label,
           K8-0b: several code roots captured into one output root)

variant: base | s5 | s9 | s59  projection patch compiled in memory by cap_child.py (nothing on disk is edited)
         lgk                   base projection; tuning = <root> config_n31_v2.json + urban.capacity.lane_group_kinds
                               ["internal", "boundary_in", "boundary_out", "off_ramp"], written to
                               <out>/tuning/config_n31_v2_k8lgk.json (json indent 2, CRLF; byte-identical to the scratch
                               r/.../config_n31_v2_k8lgk.json for the bd39205 config). Config-relative paths resolve
                               against the adapter's workspace root, not the tuning file location.
Needs <out>/replays/<T> (prep.py)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402

LGK_KINDS = ['internal', 'boundary_in', 'boundary_out', 'off_ramp']


def lgk_tuning(write=True):
    path = c.OUT / 'tuning' / 'config_n31_v2_k8lgk.json'
    if write:
        d = json.loads(c.TUNING.read_text(encoding='utf-8-sig'))
        d['urban']['capacity']['lane_group_kinds'] = list(LGK_KINDS)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(d, indent=2, ensure_ascii=False).replace('\n', '\r\n').encode('utf-8'))
    return path


ap = c.parser(__doc__)
ap.add_argument('variant', choices=('base', 's5', 's9', 's59', 'lgk'))
ap.add_argument('T', nargs='+', type=int, help='decision times (s)')
ap.add_argument('--dry-run', action='store_true', help='print the capture command lines only (writes nothing)')
ap.add_argument('--cap-label', help='capture folder cap_<label> instead of cap_<variant>')
args = ap.parse_args()
c.apply(args)
if not args.dry_run:
    c.lower_priority()
variant = args.variant
for T in args.T:
    replay = c.REPLAYS / f'{T:06d}'
    out = c.RESULTS / f'{T:06d}' / f'cap_{args.cap_label or variant}'
    tuning = c.TUNING
    proj = variant
    if variant == 'lgk':
        tuning = lgk_tuning(write=not args.dry_run)
        proj = 'base'
    if args.dry_run:
        if not (replay / 'replay_manifest.json').is_file():
            print(f'DRY T={T} variant={variant}: replay missing {replay} (run prep.py first)')
            continue
        _, a = c.adapter_args(replay, out, tuning=tuning)
        print(f'DRY T={T} variant={variant} out={out}')
        print('  ' + ' '.join([c.PY, '-B', str(c.TOOLS / 'cap_child.py'), str(out), proj, str(c.ADAPTER)] + a))
        continue
    out.mkdir(parents=True, exist_ok=True)
    _, a = c.adapter_args(replay, out, tuning=tuning)
    cmd = [c.PY, '-B', str(c.TOOLS / 'cap_child.py'), str(out), proj, str(c.ADAPTER)] + a
    code, wall = c.run(cmd, out / 'capture_log.txt', c.base_env())
    print(f'CAPTURE T={T} variant={variant} exit={code} wall={wall}', flush=True)
