"""Incremental, deduplicated evidence package; no native run or git mutation."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCOPE = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def gitpaths(*args):
    return set(filter(None, subprocess.check_output(['git', *args, '-z'], cwd=ROOT).decode('utf-8').split('\0')))


def refresh_direct():
    records = []
    for rel in (HERE / 'git_paths.txt').read_text(encoding='utf-8').splitlines():
        if rel == 'diagnostics/handoff_20260921/direct_files.json':
            continue
        p = ROOT / rel
        records.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': sha(p)})
    (HERE / 'direct_files.json').write_text(json.dumps({'files': records}, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    if (HERE / 'evidence_manifest.json').exists():
        raise FileExistsError('Preserve the completed package')
    previous = {}
    for name in ['handoff_20260916', 'handoff_20260919']:
        data = json.loads((ROOT / 'diagnostics' / name / 'evidence_manifest.json').read_text(encoding='utf-8'))
        previous.update({row['path']: row for row in data['files']})
    tracked = gitpaths('ls-files')
    direct = gitpaths('diff', 'HEAD', '--name-only')
    direct.update(['evaluation/controllers/physical_lane_groups.py', 'evaluation/controllers/desired_speed_transport.py'])
    eligible, excluded = set(), []
    raw = {'.fzp', '.db', '.knr', '.rsr', '.pkl', '.pickle', '.pyc', '.pstats'}
    for dp, dirs, names in os.walk(SCOPE):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.mplconfig', '.plot-deps')]
        for name in names:
            p = Path(dp) / name
            rel = p.relative_to(ROOT).as_posix()
            if p.suffix.lower() in raw:
                excluded.append({'path': rel, 'bytes': p.stat().st_size, 'reason': 'Raw native output/cache retained locally; not included in Git'})
            elif p.suffix.lower() in {'.py', '.ps1', '.vbs', '.md', '.png'}:
                if rel not in tracked:
                    direct.add(rel)
            elif rel not in tracked:
                eligible.add(rel)
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file())
    direct.add('docs/HANDOFF_20260921_gain_prediction.md')
    pending, seen = list(direct), set()
    while pending:
        rel = pending.pop()
        if rel in seen or not rel.endswith('.py'):
            continue
        seen.add(rel)
        tree = ast.parse((ROOT / rel).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import) else
                     [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
            for name in names:
                module = Path(*name.split('.'))
                for p in [ROOT / module.with_suffix('.py'), ROOT / module / '__init__.py', (ROOT / rel).parent / module.with_suffix('.py')]:
                    if p.is_file():
                        path = p.relative_to(ROOT).as_posix()
                        if path not in tracked and path not in direct:
                            direct.add(path)
                            pending.append(path)
    records, objects, overrides = [], {}, []
    for rel in sorted(eligible - direct):
        p = ROOT / rel
        digest = sha(p)
        old = previous.get(rel)
        if old and old['sha256'] == digest:
            continue
        if old:
            overrides.append({'path': rel, 'previous_sha256': old['sha256'], 'sha256': digest})
        records.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': digest})
        objects.setdefault(digest, p)
    # Previous manifests are immutable. Changed derived artifacts need an
    # explicit migration, not a restore that silently overwrites them.
    if overrides:
        (HERE / 'overrides_to_review.json').write_text(json.dumps(overrides, indent=2), encoding='utf-8')
        raise RuntimeError(f'Review {len(overrides)} historical artifact conflicts before packaging')
    print(json.dumps({'new_evidence_files': len(records), 'unique_objects': len(objects), 'direct_files': len(direct),
                      'unique_bytes': sum(p.stat().st_size for p in objects.values())}), flush=True)
    archive = HERE / 'evidence.build.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for digest, p in sorted(objects.items()):
            z.write(p, 'objects/' + digest)
    parts = []
    with archive.open('rb') as f:
        while data := f.read(48 * 1024 * 1024):
            name = f'evidence.part{len(parts) + 1:03d}'
            (HERE / name).write_bytes(data)
            parts.append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = {'schema': 'deduplicated-git-handoff/v1',
                'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'requires_package': 'diagnostics/handoff_20260919', 'scope': SCOPE.relative_to(ROOT).as_posix(),
                'files': records, 'parts': parts, 'unique_objects': len(objects), 'archive_bytes': archive.stat().st_size,
                'excluded_raw': excluded, 'excluded_note': 'Size/location inventory, not newly computed raw FZP hashes.'}
    (HERE / 'evidence_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    assert archive.resolve().parent == HERE.resolve()
    archive.unlink()
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file())
    direct.update(['.gitattributes', 'diagnostics/handoff_20260921/git_paths.txt', 'diagnostics/handoff_20260921/direct_files.json'])
    attrs = ROOT / '.gitattributes'
    old = attrs.read_text(encoding='utf-8-sig')
    marker = '# 2026-09-21 model and evidence handoff byte preservation'
    assert marker not in old
    rules = []
    for rel in sorted(direct):
        p = ROOT / rel
        data = p.read_bytes() if p.is_file() else b''
        crlf = b'\r\n' in data and b'\n' not in data.replace(b'\r\n', b'')
        rules.append('"' + rel + '" ' + ('text eol=crlf' if crlf else '-text') + ' whitespace=cr-at-eol')
    attrs.write_text(old.rstrip() + '\n\n' + marker + '\n' + '\n'.join(rules) + '\n', encoding='utf-8')
    (HERE / 'git_paths.txt').write_text('\n'.join(sorted(direct)) + '\n', encoding='utf-8')
    refresh_direct()
    print(json.dumps({'archive_mb': manifest['archive_bytes'] / 1024**2, 'parts': len(parts), 'direct_files': len(direct)}), flush=True)


if __name__ == '__main__':
    main()
