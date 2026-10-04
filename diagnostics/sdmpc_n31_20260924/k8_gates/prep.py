"""Prepare replay states from the R-obs run (copies only; the run folder is only read).

    python -B prep.py [--root R] [--out O] [--robs D] [--dry-run] <T> [<T> ...]   -> <out>/replays/<T>/
Uses <root>/diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.prepare with link_or_copy forced to copy."""
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import k8common as c  # noqa: E402

ap = c.parser(__doc__)
ap.add_argument('T', nargs='+', type=int, help='decision times (s)')
ap.add_argument('--dry-run', action='store_true', help='print source and targets only')
args = ap.parse_args()
c.apply(args)
if args.dry_run:
    for T in args.T:
        out = c.REPLAYS / f'{T:06d}'
        print('DRY prep', T, 'from', c.DEC, '->', out, '(exists)' if out.exists() else '')
    raise SystemExit(0)
c.lower_priority()
sys.path.insert(0, str(c.R / 'diagnostics/sdmpc_n31_20260924/tools'))
import n31_common  # noqa: E402
import make_replay_state_v2 as m  # noqa: E402


def copy_only(source, target):
    source, target = Path(source), Path(target)
    n31_common.require(source.is_file(), f'Missing file to copy: {source}')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(n31_common.long_path(source), n31_common.long_path(target))
    return 'copy'


n31_common.link_or_copy = copy_only
m.link_or_copy = copy_only
for T in args.T:
    out = c.REPLAYS / f'{T:06d}'
    if out.exists():
        print('exists', out)
        continue
    m.prepare(str(c.DEC), T, str(out))
    print('prepared', T, out)
