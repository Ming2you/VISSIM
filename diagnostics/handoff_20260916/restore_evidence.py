"""Restore byte-pinned handoff evidence. No VISSIM, git, or source rewrites."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, shutil, tempfile, zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def target(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe manifest path: '+relative)
    result = (root / Path(*p.parts)).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Manifest path escapes destination')
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--package', type=Path, default=HERE,
                    help='Directory containing an additional handoff manifest and parts')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    root = args.root.resolve()
    package = args.package.resolve()
    manifest = json.loads((package/'evidence_manifest.json').read_text(encoding='utf-8'))
    destinations=[target(root,row['path']) for row in manifest['files']]
    if len(set(destinations)) != len(destinations):
        raise ValueError('Duplicate manifest destination')
    for part in manifest['parts']:
        name=part['name']
        if not name or name in ('.','..') or any(c in name for c in ('/','\\',':')):
            raise ValueError('Unsafe archive part name: '+name)
    missing=[]; conflicts=[]
    for row in manifest['files']:
        p=target(root,row['path'])
        if not p.exists(): missing.append(row)
        elif not p.is_file() or p.stat().st_size != row['bytes'] or sha(p) != row['sha256']:
            conflicts.append(row['path'])
    if conflicts:
        raise ValueError('Existing files differ; nothing overwritten: '+repr(conflicts[:20]))
    restored=0
    if args.restore and missing:
        with tempfile.TemporaryFile() as merged:
            for part in manifest['parts']:
                p=package/part['name']
                if p.stat().st_size != part['bytes'] or sha(p) != part['sha256']:
                    raise ValueError('Archive part checksum differs: '+part['name'])
                with p.open('rb') as f: shutil.copyfileobj(f,merged)
            merged.seek(0)
            with zipfile.ZipFile(merged) as z:
                for row in missing:
                    data=z.read('objects/'+row['sha256'])
                    if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
                        raise ValueError('Archive object checksum differs: '+row['path'])
                    p=target(root,row['path']); p.parent.mkdir(parents=True,exist_ok=True)
                    with p.open('xb') as f: f.write(data)
                    restored+=1
    remaining=[r['path'] for r in manifest['files'] if not target(root,r['path']).is_file()]
    if args.verify:
        if remaining: raise ValueError('Restore first; missing '+repr(remaining[:12]))
        for row in manifest['files']:
            if sha(target(root,row['path']))!=row['sha256']:
                raise ValueError('Final checksum mismatch: '+row['path'])
    print(json.dumps({'schema':'handoff-restore-result/v1','root':str(root),
        'manifest_files':len(manifest['files']),'restored':restored,
        'missing':len(remaining),'verified':bool(args.verify),'native_started':False}))

if __name__=='__main__': main()
