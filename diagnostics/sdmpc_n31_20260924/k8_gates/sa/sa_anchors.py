"""Re-anchor the K8-0b S3 31-site table onto a code root (G-EB-11 (d), amendment 2 N-A9; read-only git).

    python -B sa_anchors.py [--root R] [--out O] [--s3site PATH] [--table k82] --from-rev REV [--dry-run]
        -> <out>/sa/anchors/s3_table_<root HEAD short>.json  {schema, rows, from_rev, root_head, rows_detail}

The K8-0b hook (k8_gates/s3site/sitecustomize.py) carries two site tables keyed by line numbers (SITES_K81 for K7 /
K8-1, SITES_K82 for the K8-2 commit).  Later commits (K8-3..K8-6, this WIP's hooks in UFA/LOR) move lines.  This tool
maps every row of the chosen table from REV (the commit where those line numbers hold) to the code root's working
tree: difflib opcode mapping of `git show REV:<file>` onto the current file; the mapped line must still contain the
row's anchor text.  A row whose line was edited falls back to the anchor occurrence nearest to the mapped
neighbourhood, and is refused when that is ambiguous (two occurrences at the same distance) or absent.  Site ids keep
the K7 numbering, so the tables stay comparable row by row.  The output is read by sa_hooks/sitecustomize.py through
env K8_S3_TABLE_JSON (the s3site machinery itself is unchanged)."""
import ast
import difflib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402

c = sc.c


def site_table(path, name):
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return [tuple(r) for r in ast.literal_eval(node.value)]
    raise SystemExit(f'{name} not found in {path}')


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8',
                          errors='replace', check=True).stdout


def find_file(root, base):
    hits = [p for p in (root / 'evaluation' / 'controllers').glob(base)] or \
           [p for p in root.glob('**/' + base) if '.git' not in p.parts]
    if len(hits) != 1:
        raise SystemExit(f'{base}: {len(hits)} candidate files under {root}')
    return hits[0]


def line_map(old_lines, new_lines):
    m = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                m[i1 + k + 1] = j1 + k + 1
    return m


def project(old_line, mapping):
    """New-file position of an old line: exact when mapped, else the nearest mapped neighbour's offset."""
    if old_line in mapping:
        return mapping[old_line], 'mapped'
    keys = sorted(mapping)
    if not keys:
        return old_line, 'unmapped'
    nearest = min(keys, key=lambda k: (abs(k - old_line), k))
    return mapping[nearest] + (old_line - nearest), 'neighbour'


def reanchor(root, rows, rev):
    cache, out, detail = {}, [], []
    for row in rows:
        sid, base, line, anchor = row[0], row[1], int(row[2]), row[3]
        if base not in cache:
            path = find_file(root, base)
            rel = path.relative_to(root).as_posix()
            old = git(root, 'show', f'{rev}:{rel}').splitlines()
            new = path.read_text(encoding='utf-8').splitlines()
            cache[base] = (rel, old, new, line_map(old, new))
        rel, old, new, mapping = cache[base]
        if line > len(old) or anchor not in old[line - 1]:
            raise SystemExit(f'{sid}: anchor not on {rev}:{rel}:{line}')
        pos, how = project(line, mapping)
        if how == 'mapped' and 0 < pos <= len(new) and anchor in new[pos - 1]:
            new_line = pos
        else:
            cands = [j for j, t in enumerate(new, start=1) if anchor in t]
            if not cands:
                raise SystemExit(f'{sid}: anchor {anchor!r} absent from {rel}')
            dist = sorted((abs(j - pos), j) for j in cands)
            if len(dist) > 1 and dist[0][0] == dist[1][0]:
                raise SystemExit(f'{sid}: ambiguous anchor {anchor!r} in {rel} near {pos}: {dist[:3]}')
            new_line, how = dist[0][1], 'searched:' + how
        out.append((sid, base, new_line) + tuple(row[3:]))
        detail.append({'id': sid, 'file': rel, 'old_line': line, 'new_line': new_line, 'method': how})
    return out, detail


def main():
    ap = c.parser(__doc__)
    ap.add_argument('--s3site', default=str(sc.GATES_DIR / 's3site' / 'sitecustomize.py'))
    ap.add_argument('--table', default='k82', choices=('k81', 'k82'))
    ap.add_argument('--from-rev', required=True, help='commit where the table line numbers hold (K8-2 for k82)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    c.apply(args)
    root = c.R
    head = git(root, 'rev-parse', '--short=12', 'HEAD').strip() if (root / '.git').exists() else 'nogit'
    dest = sc.sa_out() / 'anchors' / f's3_table_{head}.json'
    if args.dry_run:
        print(f'DRY s3site={args.s3site} exists={Path(args.s3site).is_file()} table={args.table} '
              f'from={args.from_rev} root={root} head={head} -> {dest}')
        return 0
    rows = site_table(args.s3site, 'SITES_K82' if args.table == 'k82' else 'SITES_K81')
    out, detail = reanchor(root, rows, args.from_rev)
    sc.write_json(dest, {'schema': 'k8-sa-s3-table/v1', 'from_table': args.table, 'from_rev': args.from_rev,
                         'root': str(root), 'root_head': head, 's3site': args.s3site,
                         's3site_sha256': sc.sha256_file(args.s3site), 'rows': [list(r) for r in out],
                         'rows_detail': detail})
    moved = sum(1 for d in detail if d['old_line'] != d['new_line'])
    print(f'SA_ANCHORS rows={len(out)} moved={moved} searched={sum(1 for d in detail if d["method"].startswith("searched"))}'
          f' -> {dest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
