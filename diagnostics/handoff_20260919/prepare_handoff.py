"""Package the completed ramp-response work; no git staging or native runs."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCOPE = ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def gitpaths(*args):
    return set(filter(None, subprocess.check_output(['git', *args, '-z'], cwd=ROOT).decode('utf-8').split('\0')))


def main():
    if (HERE/'evidence_manifest.json').exists():
        raise FileExistsError('Preserve published evidence')
    eligible = set()
    excluded = []
    for dp, dirs, files in os.walk(SCOPE):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.mplconfig', '.plot-deps')]
        for name in files:
            p = Path(dp)/name
            rel = p.relative_to(ROOT).as_posix()
            if p.suffix.lower() in ('.fzp', '.db', '.knr', '.rsr', '.pkl', '.pickle', '.pyc', '.pstats'):
                excluded.append({'path': rel, 'bytes': p.stat().st_size,
                                 'reason': 'Raw native output or rebuildable cache; retained locally'})
            else:
                eligible.add(rel)
    tracked = gitpaths('ls-files')
    direct = gitpaths('diff', 'HEAD', '--name-only')
    direct.update(r for r in eligible if (ROOT/r).suffix.lower() in ('.py', '.ps1', '.vbs', '.md', '.png'))
    direct.add('docs/HANDOFF_20260919_cost_and_ramp_response.md')
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.suffix in ('.py', '.md', '.txt'))
    pending = list(direct)
    seen = set()
    while pending:
        rel = pending.pop()
        if rel in seen or not rel.endswith('.py'):
            continue
        seen.add(rel)
        tree = ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import) else
                     [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else [])
            for name in names:
                module = Path(*name.split('.'))
                for p in (ROOT/module.with_suffix('.py'), ROOT/module/'__init__.py', (ROOT/rel).parent/module.with_suffix('.py')):
                    if p.is_file():
                        r = p.relative_to(ROOT).as_posix()
                        if r not in tracked and r not in direct:
                            direct.add(r)
                            pending.append(r)
    records, objects = [], {}
    for rel in sorted(eligible-direct-tracked):
        p = ROOT/rel
        digest = sha(p)
        records.append({'path': rel, 'bytes': p.stat().st_size, 'sha256': digest})
        objects.setdefault(digest, p)
    archive = HERE/'evidence.build.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for digest, p in sorted(objects.items()):
            z.write(p, 'objects/'+digest)
    parts = []
    with archive.open('rb') as f:
        while data := f.read(48*1024*1024):
            name = f'evidence.part{len(parts)+1:03d}'
            (HERE/name).write_bytes(data)
            parts.append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = {'schema': 'deduplicated-git-handoff/v1',
                'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'requires_package': 'diagnostics/handoff_20260916',
                'scope': SCOPE.relative_to(ROOT).as_posix(), 'files': records, 'parts': parts,
                'unique_objects': len(objects), 'archive_bytes': archive.stat().st_size,
                'excluded_raw': excluded,
                'excluded_note': 'Raw FZP checksums are retained in original extraction evidence where available. This exclusion inventory records size, not a new raw-file checksum.'}
    (HERE/'evidence_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    assert archive.resolve().parent == HERE.resolve()
    archive.unlink()  # Only this invocation's temporary archive; published parts remain.
    direct.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file())
    direct.update(['.gitattributes', 'diagnostics/handoff_20260919/git_paths.txt', 'diagnostics/handoff_20260919/direct_files.json'])
    attrs = ROOT/'.gitattributes'
    marker = '# 2026-09-19 incremental handoff byte preservation'
    old = attrs.read_text(encoding='utf-8-sig')
    assert marker not in old
    rules = []
    for rel in sorted(direct):
        p = ROOT/rel
        data = p.read_bytes() if p.is_file() else b''
        crlf = b'\r\n' in data and b'\n' not in data.replace(b'\r\n', b'')
        rules.append('"'+rel+'" '+('text eol=crlf' if crlf else '-text')+' whitespace=cr-at-eol')
    attrs.write_text(old.rstrip()+'\n\n'+marker+'\n'+'\n'.join(rules)+'\n', encoding='utf-8')
    (HERE/'git_paths.txt').write_text('\n'.join(sorted(direct))+'\n', encoding='utf-8')
    refresh_direct()
    print(json.dumps({'direct_files': len(direct), 'artifacts': len(records), 'unique_objects': len(objects),
                      'archive_mb': manifest['archive_bytes']/1024**2, 'parts': len(parts)}))


def refresh_direct():
    paths = (HERE/'git_paths.txt').read_text(encoding='utf-8').splitlines()
    records = [{'path': r, 'bytes': (ROOT/r).stat().st_size, 'sha256': sha(ROOT/r)}
               for r in paths if r != 'diagnostics/handoff_20260919/direct_files.json']
    (HERE/'direct_files.json').write_text(json.dumps({'files': records}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
